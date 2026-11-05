"""product: the joint predictive environment. One game is simulated as a vectorised sequence of states and typed events over equal-weight
worlds: shared parameter draws per world, a legal 11-player lineup per snap from the fitted snap propensities and the team's personnel groups,
the play call, the dropback branch (pass / sack / scramble / spike), conditional allocation of the passer, receiver and rusher over the players on the
field, linked outcomes, and rule-based transitions (downs, clock, kicks, turnovers, scores, halves, overtime). Every official credit comes from
rules.credits applied to the generated events; the finishing mask is one per player and shared by all his stats. Nothing here weights worlds,
redistributes historical counts or substitutes a pool. price() / write_contract() are the public entry points the quality_gate and report read."""
import gzip, hashlib, pathlib, dataclasses
import numpy as np, pandas as pd
import policy as K
import record, rules, model

HERE = pathlib.Path(__file__).resolve().parent
NSTAT = len(K.STATS); I = {s: i for i, s in enumerate(K.STATS)}
EXTRA = ("rec_td_yds", "rush_td_yds", "pass_td_yds"); NCOL = NSTAT + len(EXTRA); X_ = {s: NSTAT + i for i, s in enumerate(EXTRA)}
EVENT_KINDS = (rules.PASS, rules.SACK, rules.SCRAMBLE, rules.RUN, rules.KNEEL, rules.SPIKE, rules.PENALTY, rules.PUNT, rules.FIELD_GOAL)
EK = {k: i for i, k in enumerate(EVENT_KINDS)}
AUDIT_KEYS = ("worlds", "runs_generated_ne_runs_allocated", "targets_ne_pass_events", "attempts_ne_pass_plus_spike_events", "completions_ne_receptions",
              "pass_yards_ne_rec_yards", "pass_td_ne_rec_td", "carries_ne_carry_events", "receptions_gt_targets", "tds_ne_rec_plus_rush", "yards_outside_support",
              "credits_ne_events_processed", "finishing_mask_differs_across_stats", "lineups_not_eleven", "no_eligible_receiver", "no_eligible_passer", "no_eligible_rusher")
COUNT_KEYS = ("games_simulated", "worlds", "snaps", "penalties", "punts", "field_goals", "kneels", "spikes", "sacks", "scrambles", "overtime_worlds", "ties",
              "lines_priced", "lines_declared", "worlds_grown")
CONTRACT = K.CONTRACT
_GAMES = {}


class DataGap(RuntimeError):
    pass


@dataclasses.dataclass
class Lines:
    frame: pd.DataFrame
    counts: dict = dataclasses.field(default_factory=dict)
    audit: dict = dataclasses.field(default_factory=dict)
    team_frame: pd.DataFrame = None     # the side's lens counts per world (record.LENSES), summarised: the pattern view the baselines are compared with


def seed(*parts):
    return int.from_bytes(hashlib.sha256("|".join(map(str, parts)).encode()).digest()[: K.POLICY["seed_bytes"]], "big")


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


# ----------------------------------------------------------------------------------------------------------------------------- rosters
@dataclasses.dataclass
class Side:
    team: str
    players: list                  # listed players (ACT minus Out, resolved team), roster order
    groups: list               # position group per player (rules.POSITION_GROUP)
    positions: list            # roster position string per player
    avg_sum: pd.DataFrame      # players x STATS, over prior finished games this season
    avg_n: pd.Series


def side(season, week, team, cutoff):
    A, c = record.active(season, week); A = A[A.team.eq(team)]
    pos, _ = record.positions(season); pw = pos[pos.week.eq(week)].set_index("player").position
    players = sorted(A.player.unique()); positions = [pw.get(m, None) for m in players]; groups = [rules.position_group(p) for p in positions]
    OG = record.scoring_view(cutoff, season) if season == cutoff.holdout else record.official_by_game(season)[0]
    prior = OG[(OG.week < week) & OG.finish.eq(K.FINISH_TRUE)]
    avg_sum = prior.groupby("player")[K.STATS].sum().reindex(players); avg_n = prior.groupby("player").size().reindex(players)
    return Side(team, players, groups, positions, avg_sum, avg_n)


# ----------------------------------------------------------------------------------------------------------------------------- sub_models
class SubModels:
    """Per-world, per-player sub_model parameters of one side from the fits (one posterior draw per world, shared across every mechanism)."""
    def __init__(self, F, S, dsel, season, rng, opp):
        f = F.fits; players, groups = S.players, S.groups; self.M = len(players); W = len(dsel); self.W = W
        # the opponent's defence effect per world in every opponent-aware sub_model (policy.MODEL["opponent"])
        self.vdef = {n: model.defense_effect(f[n], dsel % f[n].D, opp, season, rng) for n in ("call", "branch", "result", "td_pass", "td_run", "gain_pass", "gain_run", "gain_sack")}
        self.group = np.array(groups, dtype=object)
        self.qb = self.group == "QB"; self.rec_ok = np.isin(self.group, ("QB", "RB", "FB", "WR", "TE")); self.rush_ok = np.isin(self.group, model.RUSH_ELIGIBLE)
        # snap rate: mean from the fit, the game's rate drawn once per world and player from Beta(mu phi, (1 - mu) phi) (policy.MODEL["game_variation"])
        d_s = dsel % f["snap"].D; mu = sigmoid(model.intercept(f["snap"], d_s)[:, None] + model.player_effects(f["snap"], d_s, players, groups, season, rng, with_game=False)["eta"])
        mu = np.clip(mu, 1e-6, 1 - 1e-6); phi = f["snap"].draws["phi"][d_s][:, None]
        self.snap_rate = np.clip(rng.beta(np.arange(W), mu * phi, (1 - mu) * phi), 1e-9, 1 - 1e-9); self.snap_logit = np.log(self.snap_rate / (1 - self.snap_rate))
        # allocation: per-snap rates from the fit; the game's weights drawn once per world from Dirichlet(kappa pi) over the eligible listed players
        self.eta_target = self.game_weights(f["target"], dsel % f["target"].D, players, groups, season, rng, self.rec_ok)
        self.eta_rusher = self.game_weights(f["rusher"], dsel % f["rusher"].D, players, groups, season, rng, self.rush_ok)
        self.eta_passer = model.player_effects(f["passer"], dsel % f["passer"].D, players, groups, season, rng)["eta"]
        self.branch = model.player_effects(f["branch"], dsel % f["branch"].D, players, groups, season, rng)["eta"] + model.intercept(f["branch"], dsel % f["branch"].D)[:, None, :]
        pr = model.player_effects(f["result"], dsel % f["result"].D, players, groups, season, rng)["eta"]
        self.result_rec = pr + model.intercept(f["result"], dsel % f["result"].D)[:, None, :]
        m2 = f["result"].draws.get("m2"); pl = {(tuple(m) if isinstance(m, list) else m): i for i, m in enumerate(f["result"].index["players"])}
        self.result_passer = np.stack([m2[dsel % f["result"].D, pl[m]] if (m2 is not None and m2.size and m in pl) else np.zeros((W, pr.shape[2])) for m in players], axis=1)
        self.td_pass = model.intercept(f["td_pass"], dsel % f["td_pass"].D)[:, None] + model.player_effects(f["td_pass"], dsel % f["td_pass"].D, players, groups, season, rng, with_game=False)["eta"]
        self.td_run = model.intercept(f["td_run"], dsel % f["td_run"].D)[:, None] + model.player_effects(f["td_run"], dsel % f["td_run"].D, players, groups, season, rng, with_game=False)["eta"]
        self.g_pass = model.gain_params(f["gain_pass"], dsel % f["gain_pass"].D, players, groups, season, rng)
        self.g_run = model.gain_params(f["gain_run"], dsel % f["gain_run"].D, players, groups, season, rng)
        self.g_sack = model.gain_params(f["gain_sack"], dsel % f["gain_sack"].D, players, groups, season, rng)
        tk = ("team", S.team); self.call = model.intercept(f["call"], dsel % f["call"].D) + model.player_effects(f["call"], dsel % f["call"].D, [tk], [model.PAD], season, rng)["eta"][:, 0]
        self.fits = f; self.dsel = dsel
        T = F.tables["personnel"]; self.pers = T.draw(rng, np.arange(W)); self.pers_ctx = T.contexts
        counts = {g: int((self.group == g).sum()) for g in model.PERSONNEL_GROUPS}
        self.pers_counts = np.array([[int(part[len(g):]) for g, part in zip(model.PERSONNEL_GROUPS, c.split("-"))] for c in T.categories]) if len(T.categories) else np.zeros((0, len(model.PERSONNEL_GROUPS)), int)
        feasible = np.array([all(counts[g] >= row[i] for i, g in enumerate(model.PERSONNEL_GROUPS)) for row in self.pers_counts], dtype=bool)
        if not feasible.any(): raise DataGap(f"product: no personnel group of the record is feasible with the listed players of {S.team} ({counts})")
        self.pers[:, :, ~feasible] = 0; self.pers /= self.pers.sum(axis=2, keepdims=True)
        self.drive_stamp = np.full(W, -1, dtype=np.int32); self.on_drive = np.zeros((W, self.M), dtype=bool)

    @staticmethod
    def game_weights(f, dsel, players, groups, season, rng, eligible):
        """log of the game's Dirichlet(kappa pi) allocation weights per world over the eligible listed players (-inf elsewhere); per snap the choice among the
        players on the field is proportional to these weights, so game-level role variation is drawn once per game (the Dirichlet-multinomial's generative form)."""
        eta = model.player_effects(f, dsel, players, groups, season, rng, with_game=False)["eta"]; eta = np.where(eligible[None, :], eta, -np.inf)
        mx = np.max(np.where(np.isfinite(eta), eta, -np.inf), axis=1, keepdims=True); mx = np.where(np.isfinite(mx), mx, 0.0)
        pi = np.where(np.isfinite(eta), np.exp(eta - mx), 0.0); pi = pi / np.maximum(pi.sum(axis=1, keepdims=True), 1e-300)
        kappa = f.draws["kappa"][dsel][:, None] if "kappa" in f.draws else None
        if kappa is None: return np.log(np.maximum(pi, 1e-300))
        g = rng.gamma(np.arange(len(dsel)), np.maximum(kappa * pi, 1e-12)); g = np.where(eligible[None, :], g, 0.0)
        return np.log(np.maximum(g / np.maximum(g.sum(axis=1, keepdims=True), 1e-300), 1e-300))

    def covariate_x(self, fit_name, s, w):
        E = pd.DataFrame({"yardline_100": s["yardline"][w], "down": s["down"][w], "ydstogo": s["ydstogo"][w], "score_diff": self.diff[w], "half": s["half"][w],
                          "seconds": s["seconds"][w], "kind": np.full(len(w), rules.RUN, dtype=object)})
        return model.covariates(fit_name, E)


class Game:
    """The vectorised simulation of one game over W worlds."""
    def __init__(self, season, week, home, away, F, W, rng, cutoff):
        self.season, self.week, self.F, self.W, self.rng, self.cutoff = season, week, F, W, rng, cutoff
        self.sides = [side(season, week, home, cutoff), side(season, week, away, cutoff)]
        D = min(f.D for f in F.fits.values()); self.dsel = rng.integers(np.arange(W), D)
        self.K = [SubModels(F, S, self.dsel, season, rng, self.sides[1 - i].team) for i, S in enumerate(self.sides)]
        self.T = {n: t.draw(rng, np.arange(W)) for n, t in F.tables.items() if n != "personnel"}
        self.Y = [np.zeros((W, len(S.players), NCOL), dtype=np.int32) for S in self.sides]
        self.ev = np.zeros((W, 2, len(EVENT_KINDS)), dtype=np.int32); self.alloc_runs = np.zeros((W, 2), dtype=np.int32)
        self.LZ = {k: i for i, k in enumerate(record.LENSES)}; self.team_stats = np.zeros((W, 2, len(record.LENSES)), dtype=np.int32); self.rz_flag = np.zeros((W, 2), dtype=bool)
        self.processed = np.zeros(W, dtype=np.int64); self.generated = np.zeros(W, dtype=np.int64); self.audit = {k: 0 for k in AUDIT_KEYS}; self.counts = {k: 0 for k in COUNT_KEYS}
        self.tbl = F.tables

    def table(self, name, ctx, w):
        """A categorical draw from table `name` in context ctx (scalar or per-world array) for worlds w; returns category indices."""
        T = self.tbl[name]; P = self.T[name]
        ci = np.full(len(w), T.ctx(ctx)) if not isinstance(ctx, np.ndarray) else ctx
        return model.categorical_draw(self.rng, P[w, ci, :], w)

    def bin_yardline(self, name, ctx, w):
        """A start yardline from a 5-yard-bin table: the bin's centre (Rule 1-1-1 keeps it between 1 and 99)."""
        b = np.array(self.tbl[name].categories)[self.table(name, ctx, w)]
        return np.clip(b * model.YARD_BIN + model.YARD_BIN // 2, 1, K.FIELD_YARDS - 1)

    # ---------------------------------------------------------------------------------------------------------------------------- lineup
    def lineup(self, t, s, w):
        Kt = self.K[t]; S = self.sides[t]; M = Kt.M
        ctx = model.down_class(s["down"][w]); probs = Kt.pers[w, ctx, :]
        gi = model.categorical_draw(self.rng, probs, w); need = Kt.pers_counts[gi]           # (len(w), groups)
        on = np.zeros((len(w), M), dtype=bool); logw = np.log(np.clip(sigmoid(Kt.snap_logit[w]), 1e-9, 1))
        for gidx, g in enumerate(model.PERSONNEL_GROUPS):
            mask = np.broadcast_to(Kt.group == g, (len(w), M)); k = need[:, gidx]
            if k.max() == 0: continue
            on |= model.gumbel_topk(self.rng, logw, mask, k, w)
        self.audit["lineups_not_eleven"] += int((on.sum(axis=1) != K.ON_FIELD).sum())
        new = Kt.drive_stamp[w] != s["drive_no"][w]
        Kt.on_drive[w[new]] = False; Kt.drive_stamp[w] = s["drive_no"][w]; self.team_stats[w[new], t, self.LZ["drives"]] += 1; self.rz_flag[w[new], t] = False
        Kt.on_drive[w] |= on
        return on

    # ---------------------------------------------------------------------------------------------------------------------------- credits
    def credit(self, t, w, player, stat, inc):
        """Apply increments inc (array over w) of stat to player (array of player indices over w) of side t; -1 player = none."""
        ok = player >= 0
        if ok.any(): np.add.at(self.Y[t], (w[ok], player[ok], np.full(ok.sum(), stat)), np.asarray(inc, dtype=np.int32)[ok] if np.ndim(inc) else int(inc))

    def apply_events(self, t, w, evs):
        """evs: list of rules.Event per world in w with integer player indices as participants; credits via rules.credits (the one mapping)."""
        for wi, e in zip(w, evs):
            self.ev[wi, t, EK[e.kind]] += 1; self.processed[wi] += 1
            for player, stat, inc in rules.credits(e):
                col = I.get(stat)
                if col is not None: self.Y[t][wi, player, col] += inc
            if e.touchdown and e.kind == rules.PASS: self.Y[t][wi, e.receiver, X_["rec_td_yds"]] += e.yards; self.Y[t][wi, e.passer, X_["pass_td_yds"]] += e.yards
            if e.touchdown and e.kind in rules.CARRY_KINDS: self.Y[t][wi, e.rusher, X_["rush_td_yds"]] += e.yards

    # ---------------------------------------------------------------------------------------------------------------------------- one snap
    def snap(self, t, s, w):
        """One offensive snap of side t in worlds w (down < 5, clock > 0). Generates the event, credits it, moves the state."""
        Kt = self.K[t]; S = self.sides[t]; rng = self.rng; n = len(w); yl = s["yardline"][w].astype(int); dn = s["down"][w]
        team = s["poss"][w]; diff = np.where(team == 0, s["score_home"][w] - s["score_away"][w], s["score_away"][w] - s["score_home"][w]); Kt.diff = np.zeros(self.W, int); Kt.diff[w] = diff
        self.counts["snaps"] += n
        on = self.lineup(t, s, w)
        # kneel decision (Rule 7-2-1(c) kneel: a carry) inside the kneel state
        kn = np.zeros(n, bool); ks = model.kneel_state(s["half"][w], s["seconds"][w], diff)
        if ks.any():
            dc = np.array(model.DOWN_CLASS)[model.down_class(dn[ks])]
            ci = np.array([self.tbl["kneel"].ctx(c) for c in dc]); kn[ks] = model.categorical_draw(rng, self.T["kneel"][w[ks], ci, :], w[ks]) == 1
        # penalty: a flagged no-play (counted as a snap the players were on the field for)
        pen = np.zeros(n, bool); dc_all = np.array([self.tbl["penalty"].ctx(c) for c in np.array(model.DOWN_CLASS)[model.down_class(dn)]])
        pen[~kn] = model.categorical_draw(rng, self.T["penalty"][w[~kn], dc_all[~kn], :], w[~kn]) == 1
        if pen.any():
            wp = w[pen]; cats = np.array(self.tbl["penalty_kind"].categories)[self.table("penalty_kind", "any", wp)]
            for wi, cat, y0 in zip(wp, cats, yl[pen]):
                parts = cat.split(":"); yds = int(parts[1])
                if parts[0] == "off":
                    yds = min(yds, (K.FIELD_YARDS - y0) // 2)                      # Rule 14-2-1 half the distance to the goal
                    s["yardline"][wi] += yds; s["ydstogo"][wi] += yds
                else:
                    yds = min(yds, y0 // 2); s["yardline"][wi] -= yds
                    if parts[2] == "first" or yds >= s["ydstogo"][wi]: s["down"][wi] = 1; s["ydstogo"][wi] = min(K.LINE_TO_GAIN, s["yardline"][wi])
                    else: s["ydstogo"][wi] -= yds
                self.ev[wi, t, EK[rules.PENALTY]] += 1; self.processed[wi] += 1
            self.generated[wp] += 1
            s["prior_class"][wp] = rules.CLOCK_CLASSES.index("stopped"); self.counts["penalties"] += int(pen.sum())
        live = ~pen; wl = w[live]; onl = on[live]; yl_l = yl[live]; kn_l = kn[live]; n_l = len(wl)
        if n_l == 0: return
        self.generated[wl] += 1
        # participants: the passer/ball handler is chosen inside the lineup context before any branch
        qb_mask = onl & Kt.qb[None, :]; qb_mask = np.where(qb_mask.any(axis=1)[:, None], qb_mask, onl)
        passer = model.softmax_draw(rng, Kt.eta_passer[wl], qb_mask, wl); self.audit["no_eligible_passer"] += int((passer < 0).sum())
        X_call = Kt.covariate_x("call", s, wl); p_pass = sigmoid(Kt.call[wl] + Kt.vdef["call"][wl] + model.xb(Kt.fits["call"], Kt.dsel[wl] % Kt.fits["call"].D, X_call))
        drop = (rng.u(wl)[:, 0] < p_pass) & ~kn_l; run = ~drop & ~kn_l
        kind = np.full(n_l, rules.RUN, dtype=object); kind[kn_l] = rules.KNEEL
        if drop.any():
            Xb = Kt.covariate_x("branch", s, wl[drop]); eta = Kt.branch[wl[drop], passer[drop]] + Kt.vdef["branch"][wl[drop]] + model.xb(Kt.fits["branch"], Kt.dsel[wl[drop]] % Kt.fits["branch"].D, Xb)
            logits = np.concatenate([np.zeros((drop.sum(), 1)), eta], axis=1); pr = np.exp(logits - logits.max(axis=1, keepdims=True)); pr /= pr.sum(axis=1, keepdims=True)
            kind[drop] = np.array(model.BRANCH_CATS, dtype=object)[model.categorical_draw(rng, pr, wl[drop])]
        receiver = np.full(n_l, -1); rusher = np.full(n_l, -1)
        is_pass = kind == rules.PASS; is_run = kind == rules.RUN; is_scr = kind == rules.SCRAMBLE; is_sack = kind == rules.SACK; is_spike = kind == rules.SPIKE
        if is_pass.any():
            m = onl[is_pass] & Kt.rec_ok[None, :]; m[np.arange(is_pass.sum()), passer[is_pass]] = False
            receiver[is_pass] = model.softmax_draw(rng, Kt.eta_target[wl[is_pass]], m, wl[is_pass]); self.audit["no_eligible_receiver"] += int((receiver[is_pass] < 0).sum())
        if is_run.any():
            m = onl[is_run] & Kt.rush_ok[None, :]; rusher[is_run] = model.softmax_draw(rng, Kt.eta_rusher[wl[is_run]], m, wl[is_run]); self.audit["no_eligible_rusher"] += int((rusher[is_run] < 0).sum())
        rusher[is_scr | kn_l] = passer[is_scr | kn_l]
        self.alloc_runs[wl[is_run & (rusher >= 0)], t] += 1
        # outcomes
        complete = np.zeros(n_l, int); intc = np.zeros(n_l, int); td = np.zeros(n_l, int); yards = np.zeros(n_l, int); fumble = np.zeros(n_l, bool); safety = np.zeros(n_l, bool)
        lo = np.array([rules.gain_support(k, y)[0] for k, y in zip(kind, yl_l)]); hi = np.array([rules.gain_support(k, y)[1] for k, y in zip(kind, yl_l)])
        if is_pass.any():
            wp = wl[is_pass]; Xr = Kt.covariate_x("result", s, wp); d_r = Kt.dsel[wp] % Kt.fits["result"].D
            eta = Kt.result_rec[wp, receiver[is_pass]] + Kt.result_passer[wp, passer[is_pass]] + Kt.vdef["result"][wp] + model.xb(Kt.fits["result"], d_r, Xr)
            logits = np.concatenate([np.zeros((len(wp), 1)), eta], axis=1); pr = np.exp(logits - logits.max(axis=1, keepdims=True)); pr /= pr.sum(axis=1, keepdims=True)
            res = model.categorical_draw(rng, pr, wp); complete[is_pass] = res == 1; intc[is_pass] = res == 2
            cp = is_pass.copy(); cp[is_pass] = res == 1
            if cp.any():
                wc = wl[cp]; Xt = Kt.covariate_x("td_pass", s, wc); p_td = sigmoid(Kt.td_pass[wc, receiver[cp]] + Kt.vdef["td_pass"][wc] + model.xb(Kt.fits["td_pass"], Kt.dsel[wc] % Kt.fits["td_pass"].D, Xt))
                td[cp] = rng.u(wc)[:, 0] < p_td
                g = Kt.g_pass; Xg = Kt.covariate_x("gain_pass", s, wc); mu = g["mu0"][wc, receiver[cp]] + Kt.vdef["gain_pass"][wc] + model.xb(Kt.fits["gain_pass"], Kt.dsel[wc] % Kt.fits["gain_pass"].D, Xg)
                yards[cp] = np.where(td[cp] == 1, yl_l[cp], model.sample_gain(rng, mu, g["sigma"][wc, receiver[cp]], g["nu"][wc], lo[cp], hi[cp], wc))
        rs = is_run | is_scr
        if rs.any():
            wr = wl[rs]; E = pd.DataFrame({"yardline_100": yl_l[rs], "down": s["down"][wr], "ydstogo": s["ydstogo"][wr], "score_diff": diff[live][rs], "half": s["half"][wr],
                                           "seconds": s["seconds"][wr], "kind": kind[rs]})
            p_td = sigmoid(Kt.td_run[wr, rusher[rs]] + Kt.vdef["td_run"][wr] + model.xb(Kt.fits["td_run"], Kt.dsel[wr] % Kt.fits["td_run"].D, model.covariates("td_run", E)))
            td[rs] = rng.u(wr)[:, 0] < p_td
            g = Kt.g_run; mu = g["mu0"][wr, rusher[rs]] + Kt.vdef["gain_run"][wr] + model.xb(Kt.fits["gain_run"], Kt.dsel[wr] % Kt.fits["gain_run"].D, model.covariates("gain_run", E))
            yards[rs] = np.where(td[rs] == 1, yl_l[rs], model.sample_gain(rng, mu, g["sigma"][wr, rusher[rs]], g["nu"][wr], lo[rs], hi[rs], wr))
        if is_sack.any():
            ws = wl[is_sack]; g = Kt.g_sack; Xs = Kt.covariate_x("gain_sack", s, ws)
            mu = g["mu0"][ws, passer[is_sack]] + Kt.vdef["gain_sack"][ws] + model.xb(Kt.fits["gain_sack"], Kt.dsel[ws] % Kt.fits["gain_sack"].D, Xs)
            yards[is_sack] = model.sample_gain(rng, mu, g["sigma"][ws, passer[is_sack]], g["nu"][ws], lo[is_sack], hi[is_sack], ws)
        if kn_l.any():
            yards[kn_l] = np.array(self.tbl["kneel_yards"].categories)[self.table("kneel_yards", "any", wl[kn_l])]; yards[kn_l] = np.maximum(yards[kn_l], lo[kn_l])
        # safety from inside the own ten (Rule 11-5-1): the ball is dead in the own end zone; the play's yards are the whole distance
        zone = (yl_l >= model.SAFETY_ZONE) & (td == 0) & (intc == 0) & ~(is_pass & (complete == 0)) & ~is_spike
        if zone.any():
            safety[zone] = self.table("safety", "zone", wl[zone]) == 1; yards[safety] = -(K.FIELD_YARDS - yl_l[safety])
        # fumbles lost on runs, scrambles, sacks and completions (the credits stand; possession changes at the spot)
        fk = rs | is_sack | ((kind == rules.PASS) & (complete == 1)); fk &= ~safety & (td == 0)
        if fk.any():
            ci = np.array([self.tbl["fumble"].ctx(k) for k in kind[fk]]); fumble[fk] = model.categorical_draw(rng, self.T["fumble"][wl[fk], ci, :], wl[fk]) == 1
        inside = (yards >= lo) & (yards <= hi) | (td == 1) | safety | is_spike | (is_pass & (complete == 0))
        self.audit["yards_outside_support"] += int((~inside).sum())
        # events and credits (rules.credits is the one mapping)
        evs = []
        for i in range(n_l):
            k = kind[i]
            if k == rules.PASS: evs.append(rules.Event(k, passer=passer[i], receiver=receiver[i] if receiver[i] >= 0 else None, complete=int(complete[i]), interception=int(intc[i]), touchdown=int(td[i]), yards=int(yards[i]) if complete[i] else 0))
            elif k == rules.SPIKE: evs.append(rules.Event(k, passer=passer[i]))
            elif k == rules.SACK: evs.append(rules.Event(k, passer=passer[i], yards=int(yards[i])))
            else: evs.append(rules.Event(k, rusher=rusher[i] if rusher[i] >= 0 else None, touchdown=int(td[i]), yards=int(yards[i])))
        self.apply_events(t, wl, evs)
        self.counts["kneels"] += int(kn_l.sum()); self.counts["spikes"] += int(is_spike.sum()); self.counts["sacks"] += int(is_sack.sum()); self.counts["scrambles"] += int(is_scr.sum())
        # lens counts per world (record.LENSES): the pattern view compared with the pregame baselines
        TS = self.team_stats; L = self.LZ; dn_l = s["down"][wl]
        TS[wl, t, L["plays"]] += 1; TS[wl[drop], t, L["dropbacks"]] += 1; TS[wl[is_run], t, L["designed_runs"]] += 1; TS[wl[is_scr], t, L["scrambles"]] += 1; TS[wl[kn_l], t, L["kneels"]] += 1
        TS[wl[is_pass | is_spike], t, L["attempts"]] += 1; TS[wl[is_pass & (complete == 1)], t, L["completions"]] += 1; TS[wl[is_sack], t, L["sacks"]] += 1
        TS[wl[intc == 1], t, L["interceptions"]] += 1; TS[wl[fumble], t, L["fumbles_lost"]] += 1
        np.add.at(TS, (wl[is_pass & (complete == 1)], t, L["pass_yards"]), yards[is_pass & (complete == 1)]); np.add.at(TS, (wl[rs | kn_l], t, L["rush_yards"]), yards[rs | kn_l])
        third = dn_l == 3; TS[wl[third], t, L["third_down_att"]] += 1; made = third & ((yards >= s["ydstogo"][wl]) & ~(is_pass & (complete == 0)) & ~is_spike & (intc == 0) & ~fumble | (td == 1))
        TS[wl[made], t, L["third_down_conv"]] += 1; TS[wl[td == 1], t, L["touchdowns"]] += 1
        rz = (yl_l <= 20) & ~self.rz_flag[wl, t]; TS[wl[rz], t, L["red_zone_drives"]] += 1; self.rz_flag[wl[yl_l <= 20], t] = True
        TS[wl[(td == 1) & (yl_l <= 20)], t, L["red_zone_tds"]] += 1
        # transitions
        cls = np.full(n_l, rules.CLOCK_CLASSES.index("run_inbounds")); cls[is_pass & (complete == 1)] = rules.CLOCK_CLASSES.index("complete_inbounds")
        cls[(is_pass & (complete == 0)) | is_spike] = rules.CLOCK_CLASSES.index("stopped"); cls[(td == 1) | safety] = rules.CLOCK_CLASSES.index("scoring")
        cls[(intc == 1) | fumble] = rules.CLOCK_CLASSES.index("change"); s["prior_class"][wl] = cls
        m_td = td == 1
        if m_td.any(): self.touchdown(s, wl[m_td])
        m_saf = safety & ~m_td
        if m_saf.any():
            opp = 1 - s["poss"][wl[m_saf]]; rules.add_points(s, np.isin(np.arange(self.W), wl[m_saf]), np.where(np.isin(np.arange(self.W), wl[m_saf]), s["poss"] ^ 1, 0), K.SCORING["safety"])
            start = self.bin_yardline("kick_start", "safety_kick", wl[m_saf]); rules.change_possession(s, np.isin(np.arange(self.W), wl[m_saf]), self._full(wl[m_saf], start))
        m_int = (intc == 1) & ~m_td
        if m_int.any():
            start = self.bin_yardline("turnover_start", "interception", wl[m_int]); mk = np.isin(np.arange(self.W), wl[m_int]); rules.change_possession(s, mk, self._full(wl[m_int], start))
        m_fum = fumble & ~m_td & ~m_int & ~m_saf
        if m_fum.any():
            spot = np.clip(yl_l[m_fum] - yards[m_fum], 1, K.FIELD_YARDS - 1); mk = np.isin(np.arange(self.W), wl[m_fum])
            rules.change_possession(s, mk, self._full(wl[m_fum], K.FIELD_YARDS - spot))
        m_adv = ~m_td & ~m_saf & ~m_int & ~m_fum
        if m_adv.any():
            gain = np.zeros(self.W, int); gain[wl[m_adv]] = np.where(is_pass[m_adv] & (complete[m_adv] == 0) | is_spike[m_adv], 0, yards[m_adv])
            rules.advance(s, np.isin(np.arange(self.W), wl[m_adv]), gain)

    def _full(self, w, vals):
        out = np.zeros(self.W, dtype=int); out[w] = vals; return out

    def touchdown(self, s, w):
        """Six points, then the try (a kick or a two-point attempt; the try carries no claimed stat), then a kickoff to the other side."""
        mk = np.isin(np.arange(self.W), w); team = s["poss"]
        rules.add_points(s, mk, team, K.SCORING["td"])
        two = self.table("two_attempt", "any", w) == 1
        pts = np.zeros(len(w), int)
        if two.any(): pts[two] = np.where(self.table("two_success", "any", w[two]) == 1, K.SCORING["two"], 0)
        if (~two).any(): pts[~two] = np.where(self.table("xp_make", "any", w[~two]) == 0, K.SCORING["xp"], 0)
        rules.add_points(s, mk, team, self._full(w, pts))
        self.kickoff(s, w, receiving=1 - s["poss"][w])

    def kickoff(self, s, w, receiving):
        start = self.bin_yardline("kick_start", "kickoff", w); mk = np.isin(np.arange(self.W), w)
        s["poss"][w] = receiving; s["drive_no"][w] += 1; rules.first_and_ten(s, mk, self._full(w, start)); s["prior_class"][w] = rules.CLOCK_CLASSES.index("kick")

    def fourth(self, t, s, w):
        """Fourth-down decision: go (a snap), punt or field goal (Rules 9, 11-4); returns the worlds that go for it."""
        ctx = np.array([self.tbl["fourth"].ctx((int(a), int(b))) for a, b in zip(model.yard_bin(s["yardline"][w]), model.togo_bin(s["ydstogo"][w]))])
        dec = np.array(model.FOURTH_CATS, dtype=object)[model.categorical_draw(self.rng, self.T["fourth"][w, ctx, :], w)]
        punt = dec == rules.PUNT; fg = dec == rules.FIELD_GOAL
        if punt.any():
            wp = w[punt]; ctx_p = np.clip(s["yardline"][wp] // model.PUNT_CTX_BIN, 0, 9).astype(int); P = self.T["punt_start"]
            b = np.array(self.tbl["punt_start"].categories)[model.categorical_draw(self.rng, P[wp, ctx_p, :], wp)]
            start = np.clip(b * model.YARD_BIN + model.YARD_BIN // 2, 1, K.FIELD_YARDS - 1)
            rules.change_possession(s, np.isin(np.arange(self.W), wp), self._full(wp, start)); s["prior_class"][wp] = rules.CLOCK_CLASSES.index("kick")
            self.ev[wp, t, EK[rules.PUNT]] += 1; self.processed[wp] += 1; self.generated[wp] += 1; self.counts["punts"] += len(wp); self.team_stats[wp, t, self.LZ["punts"]] += 1
        if fg.any():
            wf = w[fg]; ctx_f = model.fg_bin(s["yardline"][wf]).astype(int); made = model.categorical_draw(self.rng, self.T["fg_make"][wf, ctx_f, :], wf) == 0
            if made.any():
                mk = np.isin(np.arange(self.W), wf[made]); rules.add_points(s, mk, s["poss"], K.SCORING["fg"]); self.kickoff(s, wf[made], receiving=1 - s["poss"][wf[made]])
            if (~made).any():
                spot = np.array([rules.fg_miss_spot(y) for y in s["yardline"][wf[~made]]])
                rules.change_possession(s, np.isin(np.arange(self.W), wf[~made]), self._full(wf[~made], spot)); s["prior_class"][wf[~made]] = rules.CLOCK_CLASSES.index("kick")
            self.ev[wf, t, EK[rules.FIELD_GOAL]] += 1; self.processed[wf] += 1; self.generated[wf] += 1; self.counts["field_goals"] += len(wf); self.team_stats[wf, t, self.LZ["field_goals"]] += 1
        return w[dec == "go"]

    # ---------------------------------------------------------------------------------------------------------------------------- clock and halves
    def clock(self, s, w):
        """Seconds elapsed before this snap by the previous play's clock class and the hurry state (Rules 4-3, 4-4)."""
        diff = np.where(s["poss"][w] == 0, s["score_home"][w] - s["score_away"][w], s["score_away"][w] - s["score_home"][w])
        hu = model.hurry(s["half"][w], s["seconds"][w], diff)
        ctx = np.array([self.tbl["elapsed"].ctx((rules.CLOCK_CLASSES[c], bool(h))) for c, h in zip(s["prior_class"][w], hu)])
        el = np.array(self.tbl["elapsed"].categories)[model.categorical_draw(self.rng, self.T["elapsed"][w, ctx, :], w)]
        rules.run_clock(s, np.isin(np.arange(self.W), w), self._full(w, el))

    def end_of_half(self, s, w):
        """Half 1 -> half 2 (the side that kicked off first receives, Rule 4-2); half 2 at a tie -> overtime; else the game ends. Overtime (Rule
        16-1-3, regular season): a first-possession TD wins; otherwise each side gets a possession, then sudden death; expiry is a tie."""
        h1 = w[s["half"][w] == 1]; h2 = w[s["half"][w] == 2]; h3 = w[s["half"][w] == 3]
        if len(h1):
            s["half"][h1] = 2; s["seconds"][h1] = K.HALF_SECONDS; self.kickoff(s, h1, receiving=1 - self.opened[h1])
        if len(h2):
            tie = rules.tied(s)[h2]
            s["done"][h2[~tie]] = True
            ot = h2[tie]
            if len(ot):
                s["half"][ot] = 3; s["seconds"][ot] = K.OT_SECONDS; self.counts["overtime_worlds"] += len(ot)
                recv = model.categorical_draw(self.rng, self.T["home_receives"][ot, 0, :], ot)          # 1 = home receives
                s["ot_first_poss_team"][ot] = np.where(recv == 1, 0, 1); self.kickoff(s, ot, receiving=np.where(recv == 1, 0, 1))
        if len(h3): s["done"][h3] = True; self.counts["ties"] += int(rules.tied(s)[h3].sum())

    def overtime_rules(self, s, w, before_poss, before_scores):
        """After a snap in overtime: resolve the game by the possession rules (Rule 16-1-3)."""
        ot = w[s["half"][w] == 3]
        if not len(ot): return
        sh, sa = before_scores; changed = (s["poss"][ot] != before_poss[ot])
        scored_home = s["score_home"][ot] - sh[ot]; scored_away = s["score_away"][ot] - sa[ot]
        first_team = s["ot_first_poss_team"][ot]; first_done = s["ot_first_poss_done"][ot]
        pts_first = np.where(first_team == 0, scored_home, scored_away); pts_other = np.where(first_team == 0, scored_away, scored_home)
        # a touchdown on the first possession ends the game
        win_td = ~first_done & (pts_first >= K.SCORING["td"]); s["done"][ot[win_td]] = True
        # the first possession ends when possession changes or it scores
        ends = ~first_done & (changed | (pts_first > 0)); s["ot_first_poss_done"][ot[ends]] = True; s["ot_first_score"][ot[ends]] = pts_first[ends]
        # second possession: TD wins; if it ends with the game not tied the leader wins; tied -> sudden death
        second = first_done & ~s["ot_sudden"][ot]
        sec_end = second & (changed | (pts_other > 0) | (pts_first > 0))
        now_tied = rules.tied(s)[ot]
        s["done"][ot[sec_end & ~now_tied]] = True; s["ot_sudden"][ot[sec_end & now_tied]] = True
        sudden = s["ot_sudden"][ot] & ((scored_home != 0) | (scored_away != 0)); s["done"][ot[sudden]] = True

    # ---------------------------------------------------------------------------------------------------------------------------- run
    def run(self):
        W = self.W; s = rules.new_state(W, 0)
        recv = model.categorical_draw(self.rng, self.T["home_receives"][:, 0, :], np.arange(W)); self.opened = np.where(recv == 1, 0, 1)
        self.kickoff(s, np.arange(W), receiving=self.opened)
        steps = 0
        while not s["done"].all():
            steps += 1
            if steps > 600: raise DataGap("product: a world ran more than 600 steps; the clock does not advance")
            w = np.flatnonzero(~s["done"]); self.clock(s, w)
            ended = w[s["seconds"][w] <= 0]
            if len(ended): self.end_of_half(s, ended)
            w = np.flatnonzero(~s["done"] & (s["seconds"] > 0)); bp = s["poss"].copy(); bs = (s["score_home"].copy(), s["score_away"].copy())
            for t in (0, 1):
                wt = w[s["poss"][w] == t]
                if not len(wt): continue
                f4 = wt[s["down"][wt] >= K.DOWNS]
                go = self.fourth(t, s, f4) if len(f4) else np.array([], dtype=int)
                wt = np.concatenate([wt[s["down"][wt] < K.DOWNS], go])
                if len(wt): self.snap(t, s, np.sort(wt))
            self.overtime_rules(s, w, bp, bs)
        self.audit["worlds"] += W; self.counts["worlds"] += W; self.final_state = s
        self.team_stats[:, 0, self.LZ["points"]] = s["score_home"]; self.team_stats[:, 1, self.LZ["points"]] = s["score_away"]
        self.check_identities()
        return self

    def check_identities(self):
        """Construction identities over every world (an unconditional check; it is not evidence of predictive accuracy)."""
        for t in (0, 1):
            Y = self.Y[t]; ev = self.ev[:, t, :]
            tot = lambda st: Y[:, :, I[st]].sum(axis=1)
            self.audit["runs_generated_ne_runs_allocated"] += int((ev[:, EK[rules.RUN]] != self.alloc_runs[:, t]).sum())
            self.audit["targets_ne_pass_events"] += int((tot("targets") != ev[:, EK[rules.PASS]]).sum())
            self.audit["attempts_ne_pass_plus_spike_events"] += int((tot("attempts") != ev[:, EK[rules.PASS]] + ev[:, EK[rules.SPIKE]]).sum())
            self.audit["completions_ne_receptions"] += int((tot("completions") != tot("receptions")).sum())
            self.audit["pass_yards_ne_rec_yards"] += int((tot("pass_yards") != tot("rec_yards")).sum())
            self.audit["pass_td_ne_rec_td"] += int((tot("pass_td") != tot("rec_td")).sum())
            self.audit["carries_ne_carry_events"] += int((tot("carries") != ev[:, EK[rules.RUN]] + ev[:, EK[rules.SCRAMBLE]] + ev[:, EK[rules.KNEEL]]).sum())
            self.audit["receptions_gt_targets"] += int((Y[:, :, I["receptions"]] > Y[:, :, I["targets"]]).sum())
            self.audit["tds_ne_rec_plus_rush"] += int((Y[:, :, I["tds"]] != Y[:, :, I["rec_td"]] + Y[:, :, I["rush_td"]]).sum())
        self.audit["credits_ne_events_processed"] += int((self.processed != self.generated).sum() + (self.processed != self.ev.sum(axis=(1, 2))).sum())


def simulate(season, week, home, away, F, W, offset, cutoff=None):
    """Worlds offset .. offset + W - 1 of the game: every draw of world g is a function of the game key, g and the world's own draw counter alone
    (model.Streams), so the worlds a batch produces do not depend on the batch size, the batch boundary or how many worlds ran beside them (R13)."""
    cutoff = cutoff or record.make_cutoff(season, week)
    rng = model.Streams(seed("game", season, week, home, away, cutoff.key()), offset, W)
    return Game(season, week, home, away, F, W, rng, cutoff).run()


def game_of(season, week, team):
    G = record.games(season); this = G[G.week.eq(week) & (G.home_team.eq(team) | G.away_team.eq(team))]
    if len(this) != 1: raise DataGap(f"product: the record holds {len(this)} games for {team} {season} week {week}")
    r = this.iloc[0]; return r.home_team, r.away_team


# ----------------------------------------------------------------------------------------------------------------------------- lines
def lines_for(side_, t, Ys, Fs, nF_needed, cutoff, counts, audit):
    """Equal-world summaries for every listed player at a claimed position: one finishing mask per player, shared by all his stats."""
    rows = []; Y = np.concatenate(Ys); Fm = np.concatenate(Fs); fr = np.array(K.DISPLAY_PERCENTILES) / 100.0
    for i, m in enumerate(side_.players):
        pos = side_.positions[i]; cell = K.CELLS.get(pos)
        if not cell: continue
        n_i = side_.avg_n.iloc[i]; mask = Fm[:, i]; nF = int(mask.sum()); Yi = Y[mask, i, :]
        for st in cell:
            r = {"season": cutoff.season, "week": cutoff.week, "posteam": side_.team, "player": m, "stat": st, "issue_time": cutoff.issue_time(), "model_version": K.MODEL_VERSION,
                 "avg_sum": int(side_.avg_sum.iloc[i][st]) if pd.notna(n_i) else np.nan, "avg_n": int(n_i) if pd.notna(n_i) else np.nan, "n_worlds": len(Y), "n_finished_worlds": nF}
            code = None
            if pd.isna(n_i): code = "no_avg"
            elif nF == 0: code = "not_finished_in_any_world"
            if code is None:
                x = Yi[:, I[st]]; over = int((x * int(n_i) > int(side_.avg_sum.iloc[i][st])).sum()); p = over / nF; se = float(np.sqrt(p * (1 - p) / nF))
                bound = 0.5 / np.sqrt(nF); r["mc_bound"] = float(bound)        # the count-only bound the stopping rule read (R12)
                if nF < K.mc_worlds(): code = "insufficient_simulation"
                else:
                    o = np.sort(x); q = o[np.minimum((fr * nF).astype(int), nF - 1)]
                    vals, cnt = np.unique(x, return_counts=True)
                    kind = K.KIND[st]; takes = Yi[:, I["targets"]] + Yi[:, I["carries"]] if kind == "tds" else Yi[:, I[kind]]
                    r.update({"p": p, "n_over": over, "mc_se": se, **{f"q{pp}": int(v) for pp, v in zip(K.DISPLAY_PERCENTILES, q)}, "mean": float(x.mean()),
                              "pmf": ";".join(f"{int(v)}:{int(c)}" for v, c in zip(vals, cnt)), "exp_takes": float(takes.mean())})
                    if st in ("rec_yards", "rush_yards", "pass_yards"):
                        tdy = Yi[:, X_[{"rec_yards": "rec_td_yds", "rush_yards": "rush_td_yds", "pass_yards": "pass_td_yds"}[st]]]
                        r["exp_td_yds"] = float(tdy.mean()); r["exp_nontd_yds"] = float((x - tdy).mean())
                        r["exp_comp"] = float(Yi[:, I["receptions" if st == "rec_yards" else "completions"]].mean()) if st != "rush_yards" else np.nan
            r["reason"] = code; r["reason_words"] = K.REASONS[code] if code else None
            rows.append(r)
    F_ = pd.DataFrame(rows).reindex(columns=CONTRACT)
    counts["lines_priced"] += int(F_.p.notna().sum()); counts["lines_declared"] += int(F_.reason.notna().sum())
    return F_


def price(season, week, team, F=None, cutoff=None, log=lambda *a: None):
    """Every line of one listed side for one game. The game is simulated once (both sides) and both slates read the same worlds."""
    cutoff = cutoff or record.make_cutoff(season, week); F = F or model.load_or_fit(cutoff, log)
    if not F.all_ok(): raise DataGap(f"product: fits not FIT_OK: { {n: f.status for n, f in F.fits.items() if not f.ok()} }")
    home, away = game_of(season, week, team); key = (season, week, home, away, cutoff.key())
    counts = {k: 0 for k in COUNT_KEYS}; audit = {k: 0 for k in AUDIT_KEYS}
    if key not in _GAMES:
        Ys = [[], []]; Fs = [[], []]; TSs = []; W = 0; grown = 0; n_star = K.mc_worlds()
        while True:
            n = K.POLICY["worlds_initial"] if W == 0 else min(K.POLICY["world_batch"], K.POLICY["worlds_max"] - W)
            if n <= 0: break
            g = simulate(season, week, home, away, F, n, W, cutoff); W += n
            for t in (0, 1): Ys[t].append(g.Y[t]); Fs[t].append(g.K[t].on_drive)
            TSs.append(g.team_stats)
            for k, v in g.counts.items(): counts[k] += v
            for k, v in g.audit.items(): audit[k] += v
            counts["games_simulated"] = 1
            # grow while any priceable player has fewer than n_star finishing worlds: the rule reads finishing counts only, never a p (R12)
            need = any(int(np.concatenate(Fs[t])[:, i].sum()) < n_star
                       for t in (0, 1) for i, _ in enumerate(g.sides[t].players) if K.CELLS.get(g.sides[t].positions[i]) and pd.notna(g.sides[t].avg_n.iloc[i]))
            if not need or W >= K.POLICY["worlds_max"]: break
            grown += 1
        counts["worlds_grown"] = grown
        _GAMES[key] = (g.sides, Ys, Fs, counts, audit, np.concatenate(TSs))
    sides, Ys, Fs, counts, audit, TS = _GAMES[key]
    t = 0 if sides[0].team == team else 1
    lc = {k: 0 for k in COUNT_KEYS}; fr = lines_for(sides[t], t, Ys[t], Fs[t], None, cutoff, lc, audit)
    out_counts = dict(counts); out_counts["lines_priced"] = lc["lines_priced"]; out_counts["lines_declared"] = lc["lines_declared"]
    tf = team_frame(TS, t, sides, season, week)
    return Lines(fr, out_counts, dict(audit), tf)


def team_frame(TS, t, sides, season, week):
    """The side's lens counts over worlds, offense (what it did) and defense (what the opponent did): mean, q10, q90 per lens."""
    rows = []
    for side_, tt in (("offense", t), ("defense", 1 - t)):
        for k, i in zip(record.LENSES, range(len(record.LENSES))):
            x = TS[:, tt, i]; rows.append({"season": season, "week": week, "team": sides[t].team, "opponent": sides[1 - t].team, "side": side_, "lens": k,
                                           "mean": float(x.mean()), "q10": float(np.quantile(x, 0.1)), "q90": float(np.quantile(x, 0.9)), "worlds": len(x)})
    return pd.DataFrame(rows)


def write_contract(F_, directory):
    """The one serialized forecast the grader and report read. Every row carries a p or a reason, never both and never neither; the key is unique."""
    bad = F_.p.notna() == F_.reason.notna()
    if bad.any(): raise DataGap(f"contract: {int(bad.sum())} rows carry both or neither of p and reason; first: {F_[bad].head(1).to_dict('records')}")
    dup = F_.duplicated(K.KEY, keep=False)
    if dup.any(): raise DataGap(f"contract: {int(dup.sum())} rows share a key; first: {F_[dup].head(1)[K.KEY].to_dict('records')}")
    out = F_.sort_values(K.KEY).to_csv(index=False, float_format="%.10g").encode()
    h = hashlib.sha256(out).hexdigest(); path = pathlib.Path(directory) / f"contract_{h[: K.POLICY['print_hex']]}.csv.gz"
    with gzip.open(path, "wb") as f: f.write(out)
    return path, h


def read_contract(path):
    C = pd.read_csv(path)
    dup = C.duplicated(K.KEY, keep=False)
    if dup.any(): raise DataGap(f"contract {pathlib.Path(path).name}: {int(dup.sum())} rows share a key")
    return C
