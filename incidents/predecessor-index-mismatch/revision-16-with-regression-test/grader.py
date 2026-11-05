"""grader: measures the serialized contract against the official record and returns structured decisions the quality_gate enforces. It reads record and
contract, never product (quality_gate.lint refuses the import). Truth = official stats of finished (TRUE) player-games; baseline B1 = the cell's hit rate in
earlier read seasons. Terms: CONSTRUCTION (every graded line priced or declared exactly once, averages identical), INFORMATION (enough lines per
required group), RELIABLE (simultaneous game-clustered calibration intervals inside the declared group tolerance), USEFUL (pooled paired Brier gain
over B1 beyond the simultaneous bound), HARM (no material paired-Brier degradation in any required group), CERTIFIABLE (all of the above).
Missing groups, undefined uncertainty and undeclared tolerances are INSUFFICIENT, never exceptions and never passes."""
import hashlib
import numpy as np, pandas as pd
import policy as K
import record

TERCILES = ("low", "mid", "high")


def lines(seasons, cutoff):
    """Graded lines: a listed player (ACT minus Out, resolved team) at a claimed position, finished TRUE in the game, with a prior finished game
    this season (avg_n > 0); hit = actual * avg_n > avg_sum; in_claim_weeks. attrs count the player-games the condition excludes."""
    lo, hi = K.POLICY["claim_weeks"]; out = []; excluded = {"finish_FALSE": 0, "finish_UNKNOWN": 0, "no_avg": 0, "unresolved_team": 0}
    for s in seasons:
        OG = record.scoring_view(cutoff, s); pos, _ = record.positions(s)
        F = OG[OG.finish.eq(K.FINISH_TRUE)].sort_values(["player", "week", "game_id"]).reset_index(drop=True); g = F.groupby("player")
        F["avg_n"] = g.cumcount()
        for st in K.STATS: F[f"sum_{st}"] = g[st].cumsum() - F[st]
        for week in sorted(OG.week.unique()):
            A, c = record.active(s, int(week)); excluded["unresolved_team"] += c["men_under_unresolved_codes"]
            A = A.dropna(subset=["team"]).rename(columns={"team": "posteam"})
            X = OG[OG.week.eq(week)].merge(pos[pos.week.eq(week)][["player", "position"]], on="player", how="inner").merge(A[["posteam", "player"]].assign(listed=True), on=["posteam", "player"], how="inner")
            X = X[X.position.isin(K.CELLS)]
            excluded["finish_FALSE"] += int(X.finish.eq(K.FINISH_FALSE).sum()); excluded["finish_UNKNOWN"] += int(X.finish.eq(K.FINISH_UNKNOWN).sum())
            Xf = X[X.finish.eq(K.FINISH_TRUE)].merge(F[["game_id", "player", "avg_n"] + [f"sum_{st}" for st in K.STATS]], on=["game_id", "player"], how="left")
            excluded["no_avg"] += int((Xf.avg_n.fillna(0) == 0).sum()); Xf = Xf[Xf.avg_n > 0]
            for pos_, stats in K.CELLS.items():
                k = Xf.position.eq(pos_)
                for st in stats:
                    out.append(pd.DataFrame({"season": s, "week": int(week), "game_id": Xf.game_id[k], "posteam": Xf.posteam[k], "player": Xf.player[k], "stat": st,
                                             "cell": f"{pos_}/{st}", "actual": Xf[st][k].astype(int), "avg_sum": Xf[f"sum_{st}"][k].astype(int), "avg_n": Xf.avg_n[k].astype(int)}))
    L = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["season", "week", "game_id", "posteam", "player", "stat", "cell", "actual", "avg_sum", "avg_n"])
    L["hit"] = (L.actual * L.avg_n > L.avg_sum).astype(int); L["in_claim_weeks"] = L.week.between(lo, hi); L.attrs["excluded"] = excluded
    return L


def baseline(L, seasons):
    L = L.assign(b1=np.nan)
    for s in seasons:
        fit = L[(L.season < s) & L.in_claim_weeks]
        if len(fit): L.loc[L.season.eq(s), "b1"] = L.loc[L.season.eq(s), "cell"].map(fit.groupby("cell").hit.mean())
    return L


# ----------------------------------------------------------------------------------------------------------------------------- measurement
def cluster_se(x, g):
    """Standard error of the mean of x with g as the cluster (game) label."""
    n = len(x); m = float(np.mean(x)); G = pd.DataFrame({"d": np.asarray(x, float), "g": np.asarray(g)}).groupby("g").d.agg(["sum", "size"])
    return float(np.sqrt(np.square(G["sum"] - G["size"] * m).sum()) / n) if n else float("nan")


def group_stats(J, groups, value):
    """Per group: n, games, mean of value, cluster SE."""
    rows = {}
    for name, m in groups.items():
        d = J[m]; v = d[value].to_numpy(float)
        rows[name] = {"n": len(d), "games": int(d.game_id.nunique()), "mean": float(v.mean()) if len(d) else float("nan"), "se": cluster_se(v, d.game_id) if d.game_id.nunique() > 1 else float("nan")}
    return rows


def simultaneous_c(J, groups, value, B, alpha, seed):
    """The max-statistic critical value: bootstrap games (clusters) B times, standardise each group's mean shift by its cluster SE, take the
    maximum |z| over groups per replicate, return its (1 - alpha) quantile. Dependence across groups is carried by the joint resampling."""
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(seed.encode()).digest()[: K.POLICY["seed_bytes"]], "big"))
    base = group_stats(J, groups, value); names = [k for k, v in base.items() if v["n"] and np.isfinite(v["se"]) and v["se"] > 0]
    if not names: return float("nan"), base
    games = J.game_id.unique(); gi = {g: i for i, g in enumerate(games)}; gidx = J.game_id.map(gi).to_numpy()
    v = J[value].to_numpy(float); masks = {k: groups[k].to_numpy() for k in names}
    sums = {k: np.bincount(gidx, weights=v * masks[k], minlength=len(games)) for k in names}; cnts = {k: np.bincount(gidx, weights=masks[k].astype(float), minlength=len(games)) for k in names}
    zmax = np.empty(B)
    for b in range(B):
        w = np.bincount(rng.integers(0, len(games), len(games)), minlength=len(games)).astype(float)
        z = []
        for k in names:
            n_b = (w * cnts[k]).sum()
            if n_b <= 0: continue
            z.append(abs((w * sums[k]).sum() / n_b - base[k]["mean"]) / base[k]["se"])
        zmax[b] = max(z) if z else 0.0
    return float(np.quantile(zmax, 1 - alpha)), base


def terciles(J, by):
    """Part within cell by rank of `by` (ties at their lowest rank): low / mid / high."""
    r = J[by].groupby(J.cell).rank(method="min") - 1; n = J.cell.map(J.cell.value_counts())
    return pd.Series(np.array(TERCILES, dtype=object)[(r * len(TERCILES) // n).astype(int)], index=J.index)


def required_groups(J):
    """The required groups as boolean masks over J: cell, said tercile x cell, share (exp_takes) tercile x cell."""
    g = {}
    for c in sorted(J.cell.unique()): g[f"cell:{c}"] = J.cell.eq(c)
    sd = terciles(J, "p"); sh = terciles(J.assign(_s=J.exp_takes.fillna(0)), "_s")
    for c in sorted(J.cell.unique()):
        for t in TERCILES: g[f"said:{c}:{t}"] = J.cell.eq(c) & sd.eq(t); g[f"share:{c}:{t}"] = J.cell.eq(c) & sh.eq(t)
    return g, sd, sh


def crps_pmf(pmf, actual):
    """CRPS of an integer pmf string 'v:count;...' against the actual integer: sum over v of (F(v) - 1[v >= actual])^2 over the pmf's support hull."""
    vc = np.array([[float(x) for x in t.split(":")] for t in pmf.split(";")]); vals = vc[:, 0].astype(int); mass = vc[:, 1] / vc[:, 1].sum()
    a = int(actual); lo, hi = min(vals.min(), a), max(vals.max(), a); grid = np.arange(lo, hi + 1)
    pm = np.zeros(len(grid)); np.add.at(pm, vals - lo, mass); F = np.cumsum(pm)
    return float(np.square(F - (grid >= a).astype(float)).sum())


def decision(ok, why, insufficient=False):
    return {"status": K.INSUFFICIENT if insufficient else (K.PASS if ok else K.FAIL), "why": why}


# ----------------------------------------------------------------------------------------------------------------------------- score
def score(L, C, seasons, weeks=None, log=print):
    """L: graded lines with b1; C: the contract; seasons: scored seasons; weeks: the issue weeks in scope (None: every claim week).
    Returns (decisions, summary, user_table, trace)."""
    G = L[L.in_claim_weeks & L.season.isin(seasons) & L.b1.notna()].copy()
    if weeks is not None: G = G[G.week.isin(list(weeks))]
    Cs = C[C.season.isin(seasons)]
    dup = Cs.duplicated(K.GRADE_KEY, keep=False)
    J = G.merge(Cs, on=K.GRADE_KEY, how="left", suffixes=("", "_said"), indicator="joined")
    nothing = J.joined.eq("left_only"); declared = J.reason.notna(); priced = J.p.notna()
    avg_mm = int((~nothing & ((J.avg_sum != J.avg_sum_said) | (J.avg_n != J.avg_n_said))).sum()); contra = int((priced & declared).sum())
    extra = Cs.merge(G[K.GRADE_KEY], on=K.GRADE_KEY, how="left", indicator="j"); extra = extra[extra.j.eq("left_only")]
    con_why = {"graded": len(G), "priced": int(priced.sum()), "declared": int(declared.sum()), "said_nothing": int(nothing.sum()), "avg_mismatch": avg_mm,
               "p_and_reason": contra, "duplicate_keys_in_contract": int(dup.sum()), "said_not_graded": len(extra), "join_cardinality_ok": len(J) == len(G),
               "excluded_man_games": L.attrs.get("excluded"), "declared_by_reason": J.loc[declared, "reason"].value_counts().to_dict()}
    D = {"construction": decision(nothing.sum() == 0 and avg_mm == 0 and contra == 0 and dup.sum() == 0 and len(J) == len(G), con_why)}
    log(f"JUDGE construction: {D['construction']}")
    Jm = J[priced].copy()
    if not len(Jm):
        for k in ("information", "reliable", "useful", "harm"): D[k] = decision(False, "no priced graded lines", insufficient=True)
        D["certifiable"] = decision(False, "no priced graded lines", insufficient=True)
        return D, {"decisions": D, "construction": con_why}, pd.DataFrame(), Jm
    Jm["gap"] = Jm.hit - Jm.p; Jm["bp"] = np.square(Jm.p - Jm.hit); Jm["bb"] = np.square(Jm.b1 - Jm.hit); Jm["dbrier"] = Jm.bp - Jm.bb
    Jm["crps"] = [crps_pmf(pm, a) if isinstance(pm, str) else np.nan for pm, a in zip(Jm.pmf, Jm.actual)]
    groups, sd, sh = required_groups(Jm); Jm["said_part"] = sd; Jm["share_part"] = sh
    # INFORMATION
    thin = {k: int(m.sum()) for k, m in groups.items() if m.sum() < K.POLICY["min_group_lines"]}
    D["information"] = decision(not thin, {"groups": len(groups), "thin_groups": thin, "min_group_lines": K.POLICY["min_group_lines"]}, insufficient=bool(thin))
    # RELIABLE: simultaneous intervals of gap = hit - said
    alpha = K.POLICY["alpha_family"]; B = K.POLICY["bootstrap_replicates"]; tol = K.POLICY["group_tolerance"]
    c_cal, base_cal = simultaneous_c(Jm, groups, "gap", B, alpha, "grader-calibration")
    rows = []
    for k, st in base_cal.items():
        half = c_cal * st["se"] if np.isfinite(st["se"]) else float("nan"); lo_, hi_ = st["mean"] - half, st["mean"] + half
        inside = (abs(st["mean"]) + half <= tol) if (tol is not None and np.isfinite(half)) else None
        rows.append({"group": k, "n": st["n"], "games": st["games"], "gap": st["mean"], "se": st["se"], "lo": lo_, "hi": hi_, "zero_in": bool(np.isfinite(half) and lo_ <= 0 <= hi_),
                     "tolerance": tol, "inside_tolerance": inside})
    cal = pd.DataFrame(rows)
    undefined = int(cal.se.isna().sum())
    if tol is None: D["reliable"] = decision(False, {"policy": "group_tolerance not declared by the reviewer", "c": c_cal, "groups_zero_outside_interval": int((~cal.zero_in).sum())}, insufficient=True)
    elif undefined or thin: D["reliable"] = decision(False, {"undefined_se_groups": undefined, "thin_groups": thin, "c": c_cal}, insufficient=True)
    else: D["reliable"] = decision(bool(cal.inside_tolerance.all()), {"c": c_cal, "groups_outside_tolerance": cal.group[~cal.inside_tolerance.astype(bool)].tolist()})
    # USEFUL: pooled paired Brier against B1, simultaneous with the group deltas
    pooled = {"pooled": pd.Series(True, index=Jm.index)}; c_use, base_use = simultaneous_c(Jm, pooled | groups, "dbrier", B, alpha, "grader-usefulness")
    pd_ = base_use["pooled"]; upper = pd_["mean"] + c_use * pd_["se"] if np.isfinite(pd_["se"]) else float("nan")
    if not np.isfinite(upper): D["useful"] = decision(False, {"pooled_delta": pd_["mean"], "se": pd_["se"]}, insufficient=True)
    else: D["useful"] = decision(upper < 0, {"pooled_delta": pd_["mean"], "se": pd_["se"], "c": c_use, "upper": upper, "statement": None if upper < 0 else "No demonstrated improvement over baseline."})
    # HARM: per required group, paired delta's upper bound against the declared material harm
    harm = K.POLICY["material_harm"]; hrows = {k: {"delta": v["mean"], "se": v["se"], "upper": v["mean"] + c_use * v["se"] if np.isfinite(v["se"]) else float("nan")} for k, v in base_use.items() if k != "pooled"}
    if harm is None: D["harm"] = decision(False, {"policy": "material_harm not declared by the reviewer", "groups_worse_beyond_bound": [k for k, v in hrows.items() if np.isfinite(v["upper"]) and v["delta"] - c_use * v["se"] > 0]}, insufficient=True)
    else:
        bad = [k for k, v in hrows.items() if not np.isfinite(v["upper"]) or v["upper"] > harm]
        D["harm"] = decision(not bad, {"groups_beyond_material_harm": bad, "c": c_use}, insufficient=any(not np.isfinite(v["upper"]) for v in hrows.values()))
    # regression cases of the checker
    fp = regression_cases(Jm, groups, log)
    D["checker"] = decision(all(fp.values()), fp)
    statuses = [D[k]["status"] for k in ("construction", "information", "reliable", "useful", "harm", "checker")]
    cert = K.PASS if all(s == K.PASS for s in statuses) else (K.FAIL if K.FAIL in statuses else K.INSUFFICIENT)
    D["certifiable"] = {"status": cert, "why": {k: D[k]["status"] for k in ("construction", "information", "reliable", "useful", "harm", "checker")}}
    # user table per required group
    user = cal.merge(pd.DataFrame([{"group": k, "paired_brier_delta": v["delta"], "delta_upper": v["upper"]} for k, v in hrows.items()]), on="group", how="left")
    user["said"] = [float(Jm.p[groups[k]].mean()) for k in user.group]; user["observed"] = [float(Jm.hit[groups[k]].mean()) for k in user.group]
    user["crps"] = [float(Jm.crps[groups[k]].mean()) for k in user.group]
    user["status"] = np.where(user.inside_tolerance.isna(), K.INSUFFICIENT, np.where(user.inside_tolerance.astype(bool), K.PASS, K.FAIL))
    by_season = {int(s): {"n": int(len(d)), "gap": float(d.gap.mean()), "brier": float(d.bp.mean()), "b1_brier": float(d.bb.mean())} for s, d in Jm.groupby("season")}
    summary = {"decisions": D, "construction": con_why, "n_priced_graded": len(Jm), "brier": float(Jm.bp.mean()), "b1_brier": float(Jm.bb.mean()), "crps": float(Jm.crps.mean()),
               "by_season": by_season, "calibration_c": c_cal, "usefulness_c": c_use, "user_table": user.to_dict("records"), "mc_se_mean": float(Jm.mc_se.mean())}
    for r in user.itertuples(index=False):
        log(f"GROUP {r.group:32s} n={r.n:5d} said={r.said:.3f} obs={r.observed:.3f} gap={r.gap:+.4f} [{r.lo:+.4f},{r.hi:+.4f}] tol={r.tolerance} {r.status:12s} dBrier={r.paired_brier_delta:+.5f} (upper {r.delta_upper:+.5f}) crps={r.crps:.3f}")
    for k in ("information", "reliable", "useful", "harm", "checker", "certifiable"): log(f"JUDGE {k}: {D[k]['status']} {D[k]['why'] if k != 'checker' else ''}")
    return D, summary, user, Jm


def regression_cases(Jm, groups, log):
    """The checker's injected cases: the oracle reads BETTER than B1; a within-cell shuffle of an informative injected arm reads WORSE than the arm
    (pooled paired Brier); a group whose gap is injected to (c + 1) SE reads zero outside its simultaneous interval; unchanged inputs read identically."""
    out = {}; rng = np.random.default_rng(int.from_bytes(hashlib.sha256(b"grader-shuffle").digest()[: K.POLICY["seed_bytes"]], "big"))
    d = lambda P: float(np.mean(np.square(P - Jm.hit) - Jm.bb))
    out["oracle_better"] = d(Jm.hit.astype(float)) < 0
    info = 0.6 * Jm.hit.astype(float) + 0.4 * Jm.b1   # an informative injected arm: its within-cell shuffle must read WORSE than itself
    sh = info.groupby(Jm.cell).transform(lambda x: rng.permutation(x.to_numpy())); out["shuffle_worse"] = d(sh) > d(info)
    c, base = simultaneous_c(Jm, groups, "gap", 50, K.POLICY["alpha_family"], "grader-fixed")
    k0 = next((k for k, v in base.items() if v["n"] >= K.POLICY["min_group_lines"] and np.isfinite(v["se"]) and v["se"] > 0), None)
    if k0 is None: out["injected_shift_reads_out"] = False
    else:
        P = Jm.copy(); P.loc[groups[k0], "p"] = P.loc[groups[k0], "p"] + base[k0]["mean"] - (c + 1) * base[k0]["se"]   # the group's gap injected to +(c+1) SE
        P["gap"] = P.hit - P.p; st = group_stats(P, {k0: groups[k0]}, "gap")[k0]; out["injected_shift_reads_out"] = bool(st["mean"] - c * st["se"] > 0)
    out["unchanged_reads_identically"] = repr(group_stats(Jm, groups, "gap")) == repr(group_stats(Jm.copy(), groups, "gap"))
    log(f"JUDGE regression cases: {out}")
    return out


# ----------------------------------------------------------------------------------------------------------------------------- patterns
def patterns(team_frames, log=print):
    """The pattern view (aims; it does not grade): for every priced side and lens, the simulated per-game mean against the team's season-to-date
    baseline per game at the issue cutoff (record.team_baselines: numerator / games, offense = what it did, defense = what it allowed), and whether
    the baseline lies inside the simulated 10-90 band. Pooled per lens and side: mean simulated, mean baseline, their ratio, share of sides covered."""
    if team_frames is None or not len(team_frames): return pd.DataFrame()
    T = team_frames.copy(); rows = []
    for (season, week), d in T.groupby(["season", "week"]):
        cut = record.make_cutoff(int(season), int(week)); B = record.team_baselines(cut, int(season))
        if not len(B): continue
        B = B.set_index(["team", "side"])
        for r in d.itertuples(index=False):
            if (r.team, r.side) not in B.index: continue
            b = B.loc[(r.team, r.side)]; base = float(b[r.lens]) / float(b["games"]) if b["games"] else float("nan")
            rows.append({"season": season, "week": week, "team": r.team, "side": r.side, "lens": r.lens, "simulated": r.mean, "baseline": base, "games": int(b["games"]),
                         "inside_band": bool(r.q10 <= base <= r.q90) if np.isfinite(base) else None})
    P = pd.DataFrame(rows)
    if not len(P): return P
    pooled = P.groupby(["side", "lens"]).agg(sides=("team", "size"), simulated=("simulated", "mean"), baseline=("baseline", "mean"), covered=("inside_band", "mean")).reset_index()
    pooled["ratio"] = pooled.simulated / pooled.baseline.replace(0, np.nan)
    log("PATTERNS (aims; does not grade): simulated per-game mean vs the season-to-date baseline per game, pooled over priced sides; covered = share of sides whose baseline lies in the simulated 10-90 band")
    for r in pooled.itertuples(index=False):
        log(f"PATTERN {r.side:8s} {r.lens:16s} sides={r.sides:3d} simulated={r.simulated:8.2f} baseline={r.baseline:8.2f} ratio={r.ratio:6.3f} covered={r.covered:.2f}")
    return P


def gameflow(team_frames, log=print):
    """Held-out game-flow check (reports; the reviewer may promote it to a release requirement): for the priced games, the realized team-game lenses of
    the record against the simulated distributions, same cutoff and population as the player lines. Per lens and side: coverage of the simulated
    10-90 band (nominal 0.80), mean error (realized - simulated mean) with game-clustered SE, and the share of games above the simulated mean."""
    if team_frames is None or not len(team_frames): return pd.DataFrame(), {}
    rows = []
    for season, d in team_frames.groupby("season"):
        try: TG = record.team_game_facts(int(season))
        except record.DataGap: continue
        G = record.games(int(season)); key = TG.set_index(["week", "team", "side"])
        for r in d.itertuples(index=False):
            k = (int(r.week), r.team, r.side)
            if k not in key.index: continue
            real = key.loc[k]; real = real.iloc[0] if isinstance(real, pd.DataFrame) else real
            rows.append({"season": int(season), "week": int(r.week), "team": r.team, "side": r.side, "lens": r.lens, "game_id": real["game_id"], "realized": float(real[r.lens]),
                         "simulated": r.mean, "q10": r.q10, "q90": r.q90, "covered": bool(r.q10 <= real[r.lens] <= r.q90), "above": bool(real[r.lens] > r.mean)})
    R = pd.DataFrame(rows)
    if not len(R): return R, {}
    out = {}
    log("GAMEFLOW (held-out; reports): realized team-game lenses vs the simulated distributions of the priced games; coverage of the 10-90 band (nominal 0.80), mean error = realized - simulated")
    for (side, lens), d in R.groupby(["side", "lens"]):
        e = (d.realized - d.simulated).to_numpy(float); se = cluster_se(e, d.game_id) if d.game_id.nunique() > 1 else float("nan")
        out[f"{side}:{lens}"] = {"games": int(d.game_id.nunique()), "coverage": float(d.covered.mean()), "mean_error": float(e.mean()), "se": se, "above": float(d.above.mean())}
        log(f"GAMEFLOW {side:8s} {lens:16s} games={d.game_id.nunique():3d} coverage={d.covered.mean():.2f} mean_error={e.mean():+8.2f} (se {se:6.2f}) above={d.above.mean():.2f}")
    return R, out
