"""estimate: the tendencies layer's estimator (NFL goal doc v3 R1, R2, R18). Every sub_model is a generalised linear mixed model whose unit effects
are integrated out by a sparse Laplace approximation along the exact Ornstein-Uhlenbeck period chain, and whose few spread hyperparameters are
estimated by maximum marginal likelihood (with the contract's priors as penalties). No sampler ever sees a unit effect.

Input: the serialised sub_model data `d` of model._stan_data (1-based codes, j_prev / j_dt / j_order, X, y ...), unchanged, so the preflight and the
round-trip test keep guarding the same object. Output: posterior draws in the layout product.py reads (alpha, beta, a_pos, s, v_def, ...): the
hyperparameters at their estimates (repeated), every unit's state from its conditional posterior given everything else (its own chain block of
the Hessian inverted), every other effect from its conditional normal. The unit constant m is absorbed into the stationary first state (R2):
m is zero, sigma_m is zero, tau is the stationary spread.

Latent vector z per category block: [alpha] [beta (K)] [a_pos (G-1)] [v_def (T-1)] [s (J-1)] [g (PG-1) | binomial] [m2 (P-1) | categorical].
Hyperparameters theta (log scale where positive): sigma_pos, sigma_def, tau, lambda, [sigma_g], [sigma_m2], [phi], [kappa], [ls0, ls_pos, nu]."""
import math, time
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy import optimize, special, stats

LOG2PI = math.log(2 * math.pi)


class EstimateError(RuntimeError):
    pass


# ----------------------------------------------------------------------------------------------------------------------------- layout
class Layout:
    """Column offsets of the latent blocks for one category, and the slot -> column maps of the serialised data."""
    def __init__(self, program, d):
        self.program = program; self.d = d
        self.C1 = (d["C"] - 1) if program == "categorical" else 1
        self.K = int(d.get("K", 0)); self.G = d["G"]; self.T = d["T"]; self.J = d["J"]; self.P = d["P"]; self.PG = int(d.get("PG", 1))
        self.has_alpha = program in ("binomial", "betabinomial", "categorical", "gain")
        self.has_def = program in ("binomial", "betabinomial", "categorical", "gain")      # dirmult / softmax carry no defence term (as the Stan programs)
        self.has_g = program == "binomial"; self.has_m2 = program == "categorical"
        blocks = []
        if self.has_alpha: blocks.append(("alpha", 1))
        if self.K: blocks.append(("beta", self.K))
        blocks.append(("a_pos", self.G - 1))
        if self.has_def: blocks.append(("v_def", self.T - 1))
        blocks.append(("s", self.J - 1))
        if self.has_g: blocks.append(("g", self.PG - 1))
        if self.has_m2: blocks.append(("m2", self.P - 1))
        self.blocks = blocks; self.off = {}; o = 0
        for name, size in blocks: self.off[name] = o; o += size
        self.dim_c = o; self.dim = o * self.C1
        # slots: rows of the linear predictor (one per observation row, member, or (row, category))
        if program in ("dirmult", "softmax"): self.n_slots = int(d["M"])
        else: self.n_slots = int(d["N"])
        self.pl = np.asarray(d["pl"], int); self.pos = np.asarray(d["pos"], int); self.ps = np.asarray(d["ps"], int); self.df = np.asarray(d["df"], int)
        self.pg = np.asarray(d["pg"], int) if self.has_g else None; self.pl2 = np.asarray(d["pl2"], int) if self.has_m2 else None
        self.X = np.asarray(d["X"], float).reshape(self.n_slots, self.K) if self.K else np.zeros((self.n_slots, 0))
        self.A = self.design()

    def design(self):
        """The sparse design: (slots x C1) rows by dim columns; category c of slot i is row i * C1 + c, using block c's columns."""
        n = self.n_slots; rows, cols, vals = [], [], []
        def add(name, ix, val=None):
            if name not in self.off: return
            ok = ix > 1; r = np.nonzero(ok)[0]; c = self.off[name] + ix[ok] - 2
            for cc in range(self.C1):
                rows.append(r * self.C1 + cc); cols.append(c + cc * self.dim_c); vals.append(np.ones(len(r)) if val is None else val[ok])
        if self.has_alpha:
            for cc in range(self.C1): rows.append(np.arange(n) * self.C1 + cc); cols.append(np.full(n, self.off["alpha"] + cc * self.dim_c)); vals.append(np.ones(n))
        for k in range(self.K):
            for cc in range(self.C1): rows.append(np.arange(n) * self.C1 + cc); cols.append(np.full(n, self.off["beta"] + k + cc * self.dim_c)); vals.append(self.X[:, k])
        add("a_pos", self.pos)
        if self.has_def: add("v_def", self.df)
        add("s", self.ps)
        if self.has_g: add("g", self.pg)
        if self.has_m2: add("m2", self.pl2)
        if not rows: return sp.csr_matrix((n * self.C1, self.dim))
        return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n * self.C1, self.dim))

    def cols(self, name, cc=0):
        return self.off[name] + cc * self.dim_c + np.arange(dict(self.blocks)[name])


# ----------------------------------------------------------------------------------------------------------------------------- hyperparameters
class Theta:
    """Named hyperparameters on the unconstrained scale, with the contract's priors as log-density penalties (Jacobians included)."""
    def __init__(self, program, d, C1, G):
        self.names = []
        for cc in range(C1): self.names += [f"log_sigma_pos{cc}", f"log_tau{cc}"]
        self.names.append("log_lambda")
        self.has_def = program in ("binomial", "betabinomial", "categorical", "gain")
        if self.has_def:
            for cc in range(C1): self.names.append(f"log_sigma_def{cc}")
        if program == "binomial": self.names.append("log_sigma_g")
        if program == "categorical":
            for cc in range(C1): self.names.append(f"log_sigma_m2{cc}")
        if program == "betabinomial": self.names.append("log_phi")
        if program == "dirmult": self.names.append("log_kappa")
        if program == "gain":
            self.names += ["ls0"] + [f"ls_pos{g}" for g in range(1, G)] + ["log_nu_excess"]
        self.program, self.d, self.C1, self.G = program, d, C1, G
        self.i = {n: k for k, n in enumerate(self.names)}

    def init(self, d):
        th = np.zeros(len(self.names))
        for n in self.names:
            if n.startswith("log_sigma") or n.startswith("log_tau"): th[self.i[n]] = math.log(0.3)
            elif n == "log_lambda": th[self.i[n]] = math.log(0.5)
            elif n == "log_phi": th[self.i[n]] = d["log_phi_mean"]
            elif n == "log_kappa": th[self.i[n]] = d["log_kappa_mean"]
            elif n == "ls0": th[self.i[n]] = math.log(max(float(np.std(np.asarray(d["y"], float))), 1.0))
            elif n == "log_nu_excess": th[self.i[n]] = math.log(2.0)
        return th

    def logprior(self, th):
        d = self.d; lp = 0.0
        def half_normal(v, scale): return -0.5 * (math.exp(v) / scale) ** 2 + v      # half-normal on exp(v), with the log Jacobian
        for n in self.names:
            v = th[self.i[n]]
            if n.startswith("log_sigma_pos"): lp += half_normal(v, d["group_sd_scale"])
            elif n.startswith("log_tau"): lp += half_normal(v, d["season_sd_scale"])
            elif n == "log_lambda": lp += -d["lambda_rate"] * math.exp(v) + v
            elif n.startswith("log_sigma_def"): lp += half_normal(v, d["defense_sd_scale"])
            elif n == "log_sigma_g": lp += half_normal(v, d["game_sd_scale"])
            elif n.startswith("log_sigma_m2"): lp += half_normal(v, d["player_sd_scale"])
            elif n == "log_phi": lp += -0.5 * ((v - d["log_phi_mean"]) / d["log_phi_sd"]) ** 2
            elif n == "log_kappa": lp += -0.5 * ((v - d["log_kappa_mean"]) / d["log_kappa_sd"]) ** 2
            elif n == "ls0": lp += -0.5 * ((v - 1.0) / d["log_sigma_sd"]) ** 2
            elif n.startswith("ls_pos"): lp += -0.5 * (v / d["log_sigma_sd"]) ** 2
            elif n == "log_nu_excess": lp += (d["nu_shape"] - 1) * v - d["nu_rate"] * math.exp(v) + v
        return lp

    def get(self, th, name): return th[self.i[name]]


# ----------------------------------------------------------------------------------------------------------------------------- prior precision
def chain_precision(d, J, tau, lam):
    """The OU chain's precision over the J-1 non-pad pairs (tridiagonal after ordering), its log-determinant, and per-pair (prev, dt) for the
    conditional blocks. s_j = rho^dt s_prev + N(0, tau^2 (1 - rho^(2 dt))); a chain root is stationary N(0, tau^2)."""
    prev = np.asarray(d["j_prev"], int); dt = np.asarray(d["j_dt"], float)
    rows, cols, vals = [], [], []; logdet = 0.0
    for j in range(1, J):
        p = prev[j]
        if p > 0:
            rho = math.exp(-lam * dt[j]); v = tau ** 2 * (1 - rho ** 2); a, b = p - 2, j - 1   # p is a 1-based code; column = 0-based code - 1
            rows += [a, a, b, b]; cols += [a, b, a, b]; vals += [rho ** 2 / v, -rho / v, -rho / v, 1 / v]; logdet += -math.log(v)
        else:
            rows.append(j - 1); cols.append(j - 1); vals.append(1 / tau ** 2); logdet += -2 * math.log(tau)
    return sp.csr_matrix((vals, (rows, cols)), shape=(J - 1, J - 1)), logdet


def prior_precision(lay, theta, th):
    """Block-diagonal Q over the whole latent vector and its log-determinant."""
    d = lay.d; parts = []; logdet = 0.0
    for cc in range(lay.C1):
        for name, size in lay.blocks:
            if size == 0: continue
            if name == "alpha": q = 1 / d["intercept_sd"] ** 2; parts.append(sp.identity(1) * q); logdet += math.log(q)
            elif name == "beta": q = 1 / d["beta_sd"] ** 2; parts.append(sp.identity(size) * q); logdet += size * math.log(q)
            elif name == "a_pos": q = math.exp(-2 * theta.get(th, f"log_sigma_pos{cc}")); parts.append(sp.identity(size) * q); logdet += size * math.log(q)
            elif name == "v_def": q = math.exp(-2 * theta.get(th, f"log_sigma_def{cc}")); parts.append(sp.identity(size) * q); logdet += size * math.log(q)
            elif name == "g": q = math.exp(-2 * theta.get(th, "log_sigma_g")); parts.append(sp.identity(size) * q); logdet += size * math.log(q)
            elif name == "m2": q = math.exp(-2 * theta.get(th, f"log_sigma_m2{cc}")); parts.append(sp.identity(size) * q); logdet += size * math.log(q)
            elif name == "s":
                Qs, ld = chain_precision(d, lay.J, math.exp(theta.get(th, f"log_tau{cc}")), math.exp(theta.get(th, "log_lambda"))); parts.append(Qs); logdet += ld
    return sp.block_diag(parts, format="csc"), logdet


# ----------------------------------------------------------------------------------------------------------------------------- likelihoods
def lik_binomial(lay, eta, th, theta):
    y = np.asarray(lay.d["y"], float); n = np.asarray(lay.d["n"], float); e = eta[:, 0]
    p = special.expit(e); ll = float(np.sum(y * e - n * np.logaddexp(0, e)))
    grad = y - n * p; W = np.maximum(n * p * (1 - p), 1e-10)
    return ll, grad[:, None], sp.diags(W)


def lik_betabinomial(lay, eta, th, theta):
    y = np.asarray(lay.d["y"], float); n = np.asarray(lay.d["n"], float); e = eta[:, 0]; phi = math.exp(theta.get(th, "log_phi"))
    mu = special.expit(e); a = mu * phi; b = (1 - mu) * phi
    ll = float(np.sum(special.gammaln(y + a) + special.gammaln(n - y + b) - special.gammaln(a) - special.gammaln(b)) + len(y) * (special.gammaln(phi)) - np.sum(special.gammaln(n + phi)))
    Lmu = phi * (special.digamma(y + a) - special.digamma(a) - special.digamma(n - y + b) + special.digamma(b))
    Lmumu = phi ** 2 * (special.polygamma(1, y + a) - special.polygamma(1, a) + special.polygamma(1, n - y + b) - special.polygamma(1, b))
    dmu = mu * (1 - mu); d2mu = dmu * (1 - 2 * mu)
    grad = Lmu * dmu; hess = Lmumu * dmu ** 2 + Lmu * d2mu
    return ll, grad[:, None], sp.diags(np.maximum(-hess, 1e-10))


def lik_categorical(lay, eta, th, theta):
    """eta (N, C1); category 0 is the baseline with logit 0; y in 1..C (1 = baseline); rows weighted by w."""
    d = lay.d; y = np.asarray(d["y"], int) - 1; w = np.asarray(d["w"], float); N, C1 = eta.shape
    full = np.concatenate([np.zeros((N, 1)), eta], axis=1); lse = special.logsumexp(full, axis=1); p = np.exp(full - lse[:, None])
    ll = float(np.sum(w * (full[np.arange(N), y] - lse)))
    ind = np.zeros((N, C1)); hit = y >= 1; ind[np.nonzero(hit)[0], y[hit] - 1] = 1.0
    grad = w[:, None] * (ind - p[:, 1:])
    pc = p[:, 1:]; blocks = w[:, None, None] * (np.einsum("ic,cd->icd", pc, np.eye(C1)) - np.einsum("ic,id->icd", pc, pc))   # (N, C1, C1), PSD
    rows = (np.arange(N)[:, None, None] * C1 + np.arange(C1)[None, :, None]).repeat(C1, axis=2); cols = (np.arange(N)[:, None, None] * C1 + np.arange(C1)[None, None, :]).repeat(C1, axis=1)
    W = sp.csr_matrix((blocks.ravel() + 0.0, (rows.ravel(), cols.ravel())), shape=(N * C1, N * C1)) + sp.identity(N * C1) * 1e-10
    return ll, grad, W


def padded_groups(d, M):
    """Ragged groups (1-based start, len) as padded (Ng, L) index arrays with a mask; cached on the data dict."""
    key = "_padded"
    if key in d: return d[key]
    start = np.asarray(d["start"], int) - 1; ln = np.asarray(d["len"], int); L = int(ln.max()) if len(ln) else 1; Ng = len(ln)
    idx = start[:, None] + np.arange(L)[None, :]; mask = np.arange(L)[None, :] < ln[:, None]; idx = np.where(mask, idx, 0)
    d[key] = (idx, mask, Ng, L); return d[key]


def group_W(M, idx, mask, blocks):
    """A block-diagonal sparse W over members from padded per-group dense blocks (Ng, L, L); masked entries dropped."""
    m2 = mask[:, :, None] & mask[:, None, :]
    rows = np.broadcast_to(idx[:, :, None], m2.shape)[m2]; cols = np.broadcast_to(idx[:, None, :], m2.shape)[m2]
    return sp.csr_matrix((blocks[m2], (rows, cols)), shape=(M, M)) + sp.identity(M) * 1e-10


def lik_dirmult(lay, eta, th, theta):
    d = lay.d; kappa = math.exp(theta.get(th, "log_kappa")); y = np.asarray(d["y"], float); off = np.asarray(d["off"], float); e = eta[:, 0] + off
    idx, mask, Ng, L = padded_groups(d, lay.n_slots)
    E = np.where(mask, e[idx], -np.inf); Y = np.where(mask, y[idx], 0.0)
    P = np.exp(E - special.logsumexp(E, axis=1, keepdims=True)); P = np.where(mask, P, 0.0); a = kappa * P; S = Y.sum(axis=1)
    ll = float(Ng * special.gammaln(kappa) - np.sum(special.gammaln(S + kappa)) + np.sum(np.where(mask, special.gammaln(Y + a) - special.gammaln(np.where(mask, a, 1.0)), 0.0)))
    dd = np.where(mask, special.digamma(Y + a) - special.digamma(np.where(mask, a, 1.0)), 0.0)
    B = kappa * (np.einsum("gi,ij->gij", P, np.eye(L)) - np.einsum("gi,gj->gij", P, P))
    G = np.einsum("gij,gj->gi", B, dd); grad = np.zeros(len(e)); np.add.at(grad, idx[mask], G[mask])
    D2 = np.where(mask, special.polygamma(1, Y + a) - special.polygamma(1, np.where(mask, a, 1.0)), 0.0)   # <= 0
    W = np.einsum("gij,gj,gjk->gik", B, -D2, B)
    return ll, grad[:, None], group_W(lay.n_slots, idx, mask, W)


def lik_softmax(lay, eta, th, theta):
    d = lay.d; e = eta[:, 0]; chosen = np.asarray(d["chosen"], int) - 1
    idx, mask, Ng, L = padded_groups(d, lay.n_slots)
    E = np.where(mask, e[idx], -np.inf); lse = special.logsumexp(E, axis=1); P = np.where(mask, np.exp(E - lse[:, None]), 0.0)
    start = np.asarray(d["start"], int) - 1; ll = float(np.sum(e[start + chosen] - lse))
    G = -P; G[np.arange(Ng), chosen] += 1.0; grad = np.zeros(len(e)); np.add.at(grad, idx[mask], G[mask])
    W = np.einsum("gi,ij->gij", P, np.eye(L)) - np.einsum("gi,gj->gij", P, P)
    return ll, grad[:, None], group_W(lay.n_slots, idx, mask, W)


def lik_gain(lay, eta, th, theta):
    """Discretised Student-t restricted to [lo, hi]: log[T(z1) - T(z0)] - log[T(zh) - T(zl)], z = (c - mu) / sig; analytic first and second
    derivatives in mu (sig and nu are hyperparameters)."""
    d = lay.d; y = np.asarray(d["y"], float); w = np.asarray(d["w"], float); lo = np.asarray(d["lo"], float); hi = np.asarray(d["hi"], float)
    nu = d["nu_min"] + math.exp(theta.get(th, "log_nu_excess")); ls0 = theta.get(th, "ls0")
    lsp = np.array([0.0] + [theta.get(th, f"ls_pos{g}") for g in range(1, lay.G)]); sig = np.exp(ls0 + lsp[lay.pos - 1]); mu = eta[:, 0]
    lognorm = special.gammaln((nu + 1) / 2) - special.gammaln(nu / 2) - 0.5 * math.log(nu * math.pi)
    tpdf = lambda x: np.exp(lognorm - (nu + 1) / 2 * np.log1p(x * x / nu))
    def logdiff(b, a):
        zb = (b - mu) / sig; za = (a - mu) / sig; Fb = special.stdtr(nu, zb); Fa = special.stdtr(nu, za); D = np.maximum(Fb - Fa, 1e-300)
        fb = tpdf(zb); fa = tpdf(za); fpb = fb * (-(nu + 1) * zb / (nu + zb ** 2)); fpa = fa * (-(nu + 1) * za / (nu + za ** 2))
        Nn = fa - fb; g1 = Nn / (sig * D); g2 = (fpb - fpa) / (sig ** 2 * D) - Nn ** 2 / (sig ** 2 * D ** 2)
        return np.log(D), g1, g2
    l1, g1a, g2a = logdiff(y + 0.5, y - 0.5); l2, g1b, g2b = logdiff(hi + 0.5, lo - 0.5)
    ll = float(np.sum(w * (l1 - l2))); grad = w * (g1a - g1b); hess = w * (g2a - g2b)
    return ll, grad[:, None], sp.diags(np.maximum(-hess, 1e-8))


LIK = {"binomial": lik_binomial, "betabinomial": lik_betabinomial, "categorical": lik_categorical, "dirmult": lik_dirmult, "softmax": lik_softmax, "gain": lik_gain}


# ----------------------------------------------------------------------------------------------------------------------------- Laplace
class Laplace:
    def __init__(self, program, d, cfg):
        self.program, self.d, self.cfg = program, d, cfg
        self.lay = Layout(program, d); self.theta = Theta(program, d, self.lay.C1, self.lay.G); self.lik = LIK[program]
        self.z = np.zeros(self.lay.dim); self.newton_iters = 0; self.evals = 0

    def eta(self, z):
        return (self.lay.A @ z).reshape(self.lay.n_slots, self.lay.C1)

    def inner(self, th, Q, z0):
        """Newton on the joint log-density in z for fixed hyperparameters; returns (z_hat, H (csc), ll at the mode, iterations)."""
        A = self.lay.A; z = z0.copy(); last = None
        for it in range(self.cfg["newton_max"]):
            ll, g_eta, W = self.lik(self.lay, self.eta(z), th, self.theta)
            obj = ll - 0.5 * float(z @ (Q @ z))
            grad = A.T @ g_eta.ravel() - Q @ z
            H = (A.T @ W @ A + Q).tocsc()
            lu = spla.splu(H); step = lu.solve(grad)
            t = 1.0; z_new = z + step
            for _ in range(20):   # backtracking on the joint density
                ll_n, _, _ = self.lik(self.lay, self.eta(z_new), th, self.theta); obj_n = ll_n - 0.5 * float(z_new @ (Q @ z_new))
                if np.isfinite(obj_n) and obj_n >= obj - 1e-9: break
                t *= 0.5; z_new = z + t * step
            z = z_new; self.newton_iters += 1
            if np.max(np.abs(t * step)) < self.cfg["newton_tol"]: break
        ll, g_eta, W = self.lik(self.lay, self.eta(z), th, self.theta); H = (A.T @ W @ A + Q).tocsc()
        return z, H, ll, it + 1

    def logml(self, th, warm=True):
        """Laplace log marginal likelihood plus the hyperparameter log prior; -inf when the Hessian is not positive definite."""
        Q, logdetQ = prior_precision(self.lay, self.theta, th)
        z, H, ll, its = self.inner(th, Q, self.z if warm else np.zeros(self.lay.dim))
        lu = spla.splu(H); du = np.abs(lu.U.diagonal())   # H = A'WA + Q is positive definite by construction; splu pivots, so signs carry no information
        if np.any(du <= 0) or not np.all(np.isfinite(du)): return -np.inf, z, H
        logdetH = float(np.sum(np.log(du)))
        val = ll - 0.5 * float(z @ (Q @ z)) + 0.5 * logdetQ - 0.5 * logdetH + self.theta.logprior(th)
        self.evals += 1
        return val, z, H

    def fit(self, log=lambda *a: None):
        t0 = time.time(); th0 = self.theta.init(self.d); best = {"val": -np.inf}
        def f(th):
            val, z, H = self.logml(th)
            if np.isfinite(val):
                self.z = z
                if val > best["val"]: best.update({"val": val, "th": th.copy(), "z": z, "H": H})
            return -val if np.isfinite(val) else 1e30
        res = optimize.minimize(f, th0, method="L-BFGS-B", options={"maxiter": self.cfg["outer_max"], "ftol": self.cfg["outer_ftol"], "eps": self.cfg["outer_eps"]})
        if "th" not in best: raise EstimateError("no finite marginal likelihood evaluation (the Hessian was never positive definite)")
        self.th, self.zhat, self.H = best["th"], best["z"], best["H"]
        gnorm = float(np.max(np.abs(res.jac))) if res.jac is not None else float("nan")
        self.diag = {"converged": bool(res.success or gnorm < self.cfg["outer_gtol"]), "message": str(res.message), "outer_iterations": int(res.nit), "evaluations": self.evals,
                     "newton_iterations": self.newton_iters, "projected_gradient_max": gnorm, "log_marginal": float(best["val"]), "seconds": round(time.time() - t0, 1),
                     "theta": {n: float(v) for n, v in zip(self.theta.names, self.th)}, "latent_dim": self.lay.dim}
        return self.diag

    def hyper_se(self):
        """Standard errors of the hyperparameters from a finite-difference Hessian of the marginal at the optimum (for the fake-data oracle)."""
        p = len(self.th); h = 1e-2; Hm = np.zeros((p, p)); f0 = self.logml(self.th)[0]
        for i in range(p):
            for j in range(i, p):
                ei = np.zeros(p); ej = np.zeros(p); ei[i] = h; ej[j] = h
                fpp = self.logml(self.th + ei + ej)[0]; fpm = self.logml(self.th + ei - ej)[0]; fmp = self.logml(self.th - ei + ej)[0]; fmm = self.logml(self.th - ei - ej)[0]
                Hm[i, j] = Hm[j, i] = (fpp - fpm - fmp + fmm) / (4 * h * h)
        try: cov = np.linalg.inv(-Hm); se = np.sqrt(np.maximum(np.diag(cov), 0))
        except np.linalg.LinAlgError: se = np.full(p, np.nan)
        return {n: float(v) for n, v in zip(self.theta.names, se)}

    # ------------------------------------------------------------------------------------------------------------------------- draws
    def conditional_sd(self):
        """Conditional posterior spread of every latent given all others: 1/sqrt(H_ii) for scalar effects; for a unit's chain, the inverse of its
        own block (states of one unit are drawn jointly)."""
        H = self.H.tocsr(); dg = H.diagonal(); sd = 1 / np.sqrt(dg); blocks = {}
        prev = np.asarray(self.d["j_prev"], int); unit_of = {}
        for j in range(1, self.lay.J):
            root = j
            while prev[root] > 0: root = prev[root] - 1   # j_prev holds 1-based codes
            unit_of.setdefault(root, []).append(j)
        for cc in range(self.lay.C1):
            base = self.lay.off["s"] + cc * self.lay.dim_c
            for root, js in unit_of.items():
                if len(js) == 1: continue
                cols = base + np.array(js) - 1; sub = H[cols][:, cols].toarray()
                try: L = np.linalg.cholesky(np.linalg.inv(sub)); blocks[(cc, root)] = (cols, L)
                except np.linalg.LinAlgError: pass
        return sd, blocks

    def draws(self, D, rng):
        lay = self.lay; C1 = lay.C1; th = self.th; z = self.zhat; sd, blocks = self.conditional_sd()
        Z = z[None, :] + sd[None, :] * rng.standard_normal((D, lay.dim))
        for (cc, root), (cols, L) in blocks.items(): Z[:, cols] = z[cols][None, :] + rng.standard_normal((D, len(cols))) @ L.T
        def block(name, pad_rows):
            """(D, pad_rows + size[, C1]) with the pad at index 0 fixed at zero."""
            out = np.zeros((D, pad_rows + dict(lay.blocks)[name], C1))
            for cc in range(C1): out[:, pad_rows:, cc] = Z[:, lay.cols(name, cc)]
            return out if C1 > 1 else out[:, :, 0]
        g = lambda n: np.array([math.exp(self.theta.get(th, f"{n}{cc}")) for cc in range(C1)])
        vec = lambda v: np.tile(v, (D, 1)) if C1 > 1 else np.full(D, float(v[0]))
        out = {"sigma_pos": vec(g("log_sigma_pos")), "tau": vec(g("log_tau")), "lambda": np.full(D, math.exp(self.theta.get(th, "log_lambda"))),
               "sigma_m": vec(np.zeros(C1)), "m": np.zeros((D, lay.P, C1)) if C1 > 1 else np.zeros((D, lay.P)),
               "a_pos": block("a_pos", 1), "s": block("s", 1)}
        out["sigma_def"] = vec(g("log_sigma_def")) if lay.has_def else vec(np.zeros(C1))
        out["v_def"] = block("v_def", 1) if lay.has_def else (np.zeros((D, lay.T, C1)) if C1 > 1 else np.zeros((D, lay.T)))
        if lay.has_alpha: a = block("alpha", 0); out["alpha"] = a[:, 0] if C1 == 1 else a[:, 0, :]
        out["beta"] = block("beta", 0) if lay.K else (np.zeros((D, 0, C1)) if C1 > 1 else np.zeros((D, 0)))
        if lay.has_g: out["sigma_g"] = np.full(D, math.exp(self.theta.get(th, "log_sigma_g"))); out["g"] = block("g", 1)
        if lay.has_m2: out["sigma_m2"] = vec(g("log_sigma_m2")); out["m2"] = block("m2", 1)
        if self.program == "betabinomial": out["phi"] = np.full(D, math.exp(self.theta.get(th, "log_phi")))
        if self.program == "dirmult": out["kappa"] = np.full(D, math.exp(self.theta.get(th, "log_kappa")))
        if self.program == "gain":
            out["ls0"] = np.full(D, self.theta.get(th, "ls0")); out["ls_pos"] = np.tile(np.array([0.0] + [self.theta.get(th, f"ls_pos{g_}") for g_ in range(1, lay.G)]), (D, 1))
            out["nu"] = np.full(D, self.d["nu_min"] + math.exp(self.theta.get(th, "log_nu_excess")))
        return {k: np.asarray(v, dtype=np.float32) for k, v in out.items()}


def fit(program, d, cfg, rng, log=lambda *a: None, with_se=False):
    """Fit one sub_model: returns (draws, diagnostics). Raises EstimateError when no finite marginal exists."""
    lap = Laplace(program, d, cfg); diag = lap.fit(log)
    if with_se: diag["hyper_se"] = lap.hyper_se()
    draws = lap.draws(cfg["draws"], rng)
    diag["conditional_sd_median"] = float(np.median(1 / np.sqrt(lap.H.diagonal())))
    return draws, diag
