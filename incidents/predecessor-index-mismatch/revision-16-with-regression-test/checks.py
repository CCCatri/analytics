"""checks: construction checks. The record against football's rules (identities and bounds), the record's credits replayed against the official
tally, the information boundary, tri-state finishing, the production reducer's conservation, and the contract's key and mask identities.
A check's decision counts only after it has failed its own injected fault. A gating check stops the chain; a printing check never does."""
import tempfile
import numpy as np, pandas as pd
import policy as K
import record, rules, product


class INEFFECTIVE_CHECK(RuntimeError):
    pass


class Check:
    def __init__(self, name, gates, run, injected):
        self.name, self.gates, self._run, self._planted = name, gates, run, injected

    def can_fail(self):
        ok, detail = self._planted()
        if ok: raise INEFFECTIVE_CHECK(f"check {self.name} passed its own injected fault: its decision would be vacuous ({detail})")
        return detail

    def run(self): return self._run()


def scrim(season):
    E, _ = record.events(season); return E[E.kind.isin(rules.SCRIMMAGE) & E.penalty.eq(0)]


# ----------------------------------------------------------------------------------------------------------------------------- rules
def points(season, scoring):
    """Rule 11-1-2: each side's final score equals its scoring plays' points; a safety is attributed through the running score."""
    E, _ = record.events(season); E = E.sort_values(["game_id", "seq"]); g = E.groupby("game_id")
    dh = E.total_home_score - g.total_home_score.shift(1).fillna(0); da = E.total_away_score - g.total_away_score.shift(1).fillna(0); saf = E.safety.eq(1)
    to_home = saf & dh.eq(scoring["safety"]) & da.eq(0); to_away = saf & da.eq(scoring["safety"]) & dh.eq(0)
    unattributed = set(E.game_id[saf & ~to_home & ~to_away])
    parts = [(E.any_td.eq(1), E.td_team, scoring["td"]), (E.extra_point_result.eq("good"), E.posteam, scoring["xp"]), (E.two_point_conv_result.eq("success"), E.posteam, scoring["two"]),
             (E.field_goal_result.eq("made"), E.posteam, scoring["fg"]), (to_home, E.home_team, scoring["safety"]), (to_away, E.away_team, scoring["safety"]),
             (E.def_two.eq(1), E.defteam, scoring["def_two"]), (E.def_xp.eq(1), E.defteam, scoring["def_xp"])]
    P = pd.concat([pd.DataFrame({"game_id": E.game_id[m], "team": who[m], "v": v}) for m, who, v in parts]).dropna(subset=["team"]).groupby(["game_id", "team"]).v.sum()
    G = record.games(season).set_index("game_id")
    pick = lambda side: P.reindex(pd.MultiIndex.from_arrays([G.index, G[side]])).fillna(0).to_numpy()
    bad = (pick("home_team") != G.home_score.to_numpy()) | (pick("away_team") != G.away_score.to_numpy())
    return set(G.index[bad]), unattributed, len(G)


def incomplete(season, extra):
    S = scrim(season); m = S.kind.eq(rules.PASS) & S.complete.eq(0) & S.interception.eq(0)
    return int(m.sum()), int((m & (S.yards_gained + extra).ne(0)).sum())


def td_yards(season, extra):
    S = scrim(season); m = S.touchdown.eq(1) & S.fumble_lost.eq(0) & S.interception.eq(0)
    return int(m.sum()), int((m & (S.yards_gained + extra).ne(S.yardline_100)).sum())


def bounds(season, extra):
    S = scrim(season); g = S.yards_gained + extra
    return len(S), int(((S.yardline_100 < 1) | (S.yardline_100 >= K.FIELD_YARDS) | (g > S.yardline_100) | (g < -(K.FIELD_YARDS - S.yardline_100))).sum())


def drive_end(season, injected_fault):
    S = scrim(season); edge = S.groupby(["game_id", "drive"]).seq.transform("min" if injected_fault else "max"); td = S.touchdown.eq(1)
    return int(td.sum()), int((td & S.seq.ne(edge)).sum())


def clock(season, reverse):
    E, _ = record.events(season); E = E.sort_values(["game_id", "seq"]); E = E.iloc[::-1] if reverse else E
    return len(E), int((E.game_seconds_remaining > E.groupby("game_id").game_seconds_remaining.shift(1)).sum())


def eligible(season, elig):
    S = scrim(season); S = S[S.kind.eq(rules.PASS) & S.receiver.notna()]; pos, _ = record.positions(season)
    tg = S.merge(pos, left_on=["week", "receiver"], right_on=["week", "player"], how="left"); bad = tg[~tg.position.isin(elig)]
    return len(tg), bad.position.fillna("(no position)").value_counts().to_dict()


# ----------------------------------------------------------------------------------------------------------------------------- record
def replay(season, injected_fault):
    """The record's credits per player-week against the official file; injected_fault: one credit's yards + 1."""
    agree = record.replay_vs_official(season)
    if not injected_fault: return agree
    C = record.credits(season).copy(); i = C.index[C.stat.eq("rec_yards")][0]; C.loc[i, "inc"] += 1
    T = C.groupby(["week", "player", "stat"]).inc.sum().unstack(fill_value=0).reindex(columns=K.STATS, fill_value=0)
    S = record.official(season).set_index(["week", "player"])[K.STATS]; M = T.join(S, how="inner", rsuffix="_official")
    return {st: {"agree": float((M[st] == M[f"{st}_official"]).mean()), "disagree_rows": int((M[st] != M[f"{st}_official"]).sum()), "n": len(M)} for st in K.STATS}


def snaps_check(season, injected_fault):
    """SNAPS: participation-derived offense snaps against the snap-count file per player-game; injected_fault: one compared, agreeing row's file count + 1
    (a row outside the comparison, or one already disagreeing, would leave the disagreement count unchanged and the check vacuous)."""
    r, j = record.snaps_cross_check(season, frame=True)
    if not injected_fault or not r.get("compared"): return r
    agree = j[j.part_snaps == j.offense_snaps]
    if not len(agree): return r | {"injected_fault_impossible": "no agreeing row to injected_fault on"}
    g, m = agree.iloc[0][["game_id", "player"]]
    Sn, c = record.snaps(season); Sn = Sn.copy(); hit = Sn.game_id.eq(g) & Sn.player.eq(m); Sn.loc[hit, "offense_snaps"] += 1
    saved = record._CACHE.get(("snaps", season))
    try:
        record._CACHE[("snaps", season)] = (Sn, c); return record.snaps_cross_check(season)
    finally: record._CACHE[("snaps", season)] = saved


def finishing(season, injected_fault):
    """Tri-state finishing on the record: with every final-drive snap known, no player is UNKNOWN; with one side's final-drive participation rows
    removed (injected_fault), that side's unseen players read UNKNOWN (never FALSE) and its final drive id is unchanged (it comes from the play sequence)."""
    fd, _ = record.final_drive(season); Fn, c = record.finished(season)
    if not injected_fault: return {"unknown": c["finished_unknown"], "false": c["finished_false"], "true": c["finished_true"], "sides_full_coverage": c["sides_with_full_final_drive_coverage"], "sides": c["sides"]}
    g, t, d = fd.iloc[0][["game_id", "posteam", "final_drive"]]
    P, pc = record.participation(season); S = record.scrimmage(season)
    drop = S[S.game_id.eq(g) & S.posteam.eq(t) & S.drive.eq(d)][["game_id", "play_id"]]
    P2 = P.merge(drop.assign(_d=True), on=["game_id", "play_id"], how="left"); P2 = P2[P2._d.isna()].drop(columns="_d").reset_index(drop=True)
    saved = {k: record._CACHE.get(k) for k in [("part", season), ("final_drive", season), ("finished", season), ("played", season), ("ogame", season)]}
    try:
        record._CACHE[("part", season)] = (P2, pc)
        for k in list(saved)[1:]: record._CACHE.pop(k, None)
        fd2, _ = record.final_drive(season); Fn2, c2 = record.finished(season)
        side2 = Fn2[Fn2.game_id.eq(g) & Fn2.posteam.eq(t)]; same_drive = float(fd2[fd2.game_id.eq(g) & fd2.posteam.eq(t)].final_drive.iloc[0]) == float(d)
        return {"injected_side_unknown": int(side2.finish.eq(K.FINISH_UNKNOWN).sum()), "injected_side_false": int(side2.finish.eq(K.FINISH_FALSE).sum()),
                "injected_side_true": int(side2.finish.eq(K.FINISH_TRUE).sum()), "final_drive_unchanged": same_drive}
    finally:
        for k, v in saved.items():
            if v is None: record._CACHE.pop(k, None)
            else: record._CACHE[k] = v


def boundary(cutoff):
    """The information boundary: no training row from the hold-out or from this season at or after the fit week; the hold-out is refused even when
    named in admitted_seasons (injected_fault)."""
    E = record.training_events(cutoff)
    leak = int((E.season.eq(cutoff.holdout) | (E.season.eq(cutoff.season) & (E.week >= cutoff.fit_week)) | (E.season > cutoff.season)).sum()) if len(E) else 0
    injected = K.Cutoff(**{**cutoff.__dict__, "admitted_seasons": tuple(sorted(set(cutoff.admitted_seasons) | {cutoff.holdout}))})
    E_next_start = record.training_events(injected); leak2 = int(E_next_start.season.eq(cutoff.holdout).sum()) if len(E_next_start) else 0
    return leak, leak2, len(E), injected.admits(cutoff.holdout, 1)


# ----------------------------------------------------------------------------------------------------------------------------- reducer
def reducer(injected_fault):
    """The production reducer (product.Game.apply_events + check_identities) on injected events: a pass with linked passer and receiver credits, a
    scramble, a kneel, a sack and a spike conserve; injected_fault 'credit': one receiving-yards credit altered after the event; injected_fault 'run': a generated
    designed run whose allocation is missing; injected_fault 'event': an event generated but never processed."""
    g = object.__new__(product.Game); W = 3; g.W = W; g.Y = [np.zeros((W, 4, product.NCOL), dtype=np.int32), np.zeros((W, 2, product.NCOL), dtype=np.int32)]
    g.ev = np.zeros((W, 2, len(product.EVENT_KINDS)), dtype=np.int32); g.alloc_runs = np.zeros((W, 2), dtype=np.int32)
    g.processed = np.zeros(W, dtype=np.int64); g.generated = np.zeros(W, dtype=np.int64); g.audit = {k: 0 for k in product.AUDIT_KEYS}
    w = np.arange(W)
    evs = [rules.Event(rules.PASS, passer=0, receiver=1, complete=1, yards=12), rules.Event(rules.PASS, passer=0, receiver=2, complete=1, touchdown=1, yards=30),
           rules.Event(rules.PASS, passer=0, receiver=1, interception=1)]
    g.generated[w] += 1; g.apply_events(0, w, evs)
    g.generated[w] += 1; g.apply_events(0, w, [rules.Event(rules.SCRAMBLE, rusher=0, yards=7)] * W)
    g.generated[w] += 1; g.apply_events(0, w, [rules.Event(rules.KNEEL, rusher=0, yards=-1)] * W)
    g.generated[w] += 1; g.apply_events(0, w, [rules.Event(rules.SACK, passer=0, yards=-6)] * W)
    g.generated[w] += 1; g.apply_events(0, w, [rules.Event(rules.SPIKE, passer=0)] * W)
    g.generated[w] += 1; g.alloc_runs[w, 0] += 1; g.apply_events(0, w, [rules.Event(rules.RUN, rusher=3, yards=4)] * W)
    if injected_fault == "credit": g.Y[0][0, 1, product.I["rec_yards"]] += 3
    if injected_fault == "run": g.ev[1, 0, product.EK[rules.RUN]] += 1
    if injected_fault == "event": g.generated[2] += 1
    g.check_identities()
    return {k: v for k, v in g.audit.items() if v}


# ----------------------------------------------------------------------------------------------------------------------------- build
def build(seasons, cutoff):
    rule_s = sorted(set(seasons) | {K.POLICY["holdout_season"]} & set(record.seasons_on_disk())); last = rule_s[-1:]

    def total(fn, arg, over):
        a = b = 0
        for s in over:
            x, y = fn(s, arg); a += x; b += y
        return a, b

    def run_points(scoring):
        bad, unattr, n = set(), set(), 0
        for s in rule_s:
            b, u, k = points(s, scoring); bad |= b; unattr |= u; n += k
        return bad <= unattr, f"games={n} mismatching={len(bad)} declared (a safety the running score does not attribute)={len(unattr)} unexplained={len(bad - unattr)}"

    def rule_gate(name, fn, ratio_ok):
        def run():
            n, v = total(fn, 0, rule_s); return ratio_ok(n, v), f"{name}: plays={n} violations={v}"
        def injected_fault():
            n, v = total(fn, 1, last); n0, v0 = total(fn, 0, last); return v <= v0, f"injected shift: {v} violations against {v0}"
        return run, injected_fault

    inc_run, inc_plant = rule_gate("8-1-4 incomplete pass gains 0", incomplete, lambda n, v: v == 0)
    tdy_run, tdy_plant = rule_gate("11-2-1 offensive TD gains its yards to goal", td_yards, lambda n, v: v == 0)
    bnd_run, bnd_plant = rule_gate("3-11-9 field bounds", bounds, lambda n, v: v == 0)

    def run_drive():
        n, v = total(drive_end, False, rule_s); return True, f"7-2-1(m): offensive TDs={n} followed by a scrimmage snap under the same drive id={v}"

    def injected_drive():
        n, v = total(drive_end, True, last); n0, v0 = total(drive_end, False, last); return v <= v0, f"TD required first in drive: {v} against {v0}"

    def run_clock():
        n, v = total(clock, False, rule_s); return True, f"4-1-1: events={n} clock rises within a game={v}"

    def injected_clock():
        n, v = total(clock, True, last); n0, v0 = total(clock, False, last); return v <= v0, f"reversed order: {v} rises against {v0}"

    def run_elig():
        n = 0; by = {}
        for s in seasons:
            k, d = eligible(s, K.RECEIVER_POSITIONS); n += k
            for a, b in d.items(): by[a] = by.get(a, 0) + b
        return True, f"8-1-5: targets={n} to a roster position outside the ends and backs (a report or a violation; counted, never a DataGap)={sum(by.values())} {by}"

    def injected_elig():
        n, d = eligible(last[0], ("QB",)); n0, d0 = eligible(last[0], K.RECEIVER_POSITIONS); return sum(d.values()) <= sum(d0.values()), f"eligible set shrunk to QB: {sum(d.values())} against {sum(d0.values())}"

    def run_replay():
        rows = {s: replay(s, False) for s in seasons}
        return True, "credits replayed against the official tally, share of player-weeks agreeing by stat:\n" + pd.DataFrame({s: {k: v["agree"] for k, v in r.items()} for s, r in rows.items()}).T.to_string(float_format="{:.4f}".format) \
            + "\nnamed deficiencies: " + str({s: record.deficiencies(s) for s in seasons})

    def injected_replay():
        a = replay(last[0], True); a0 = replay(last[0], False); return a["rec_yards"]["disagree_rows"] <= a0["rec_yards"]["disagree_rows"], f"one credit's yards + 1: rec_yards disagreeing {a['rec_yards']['disagree_rows']} against {a0['rec_yards']['disagree_rows']}"

    def run_snaps():
        rows = {s: snaps_check(s, False) for s in seasons}
        return True, "participation-derived offense snaps vs the snap-count file (players.csv as the identity bridge), by season: " + str(rows)

    def injected_snaps():
        r = snaps_check(last[0], True); r0 = snaps_check(last[0], False)
        if not r0.get("compared"): return False, "no snap file or no identity bridge: nothing to compare (named deficiency)"
        if "injected_fault_impossible" in r: return False, r["injected_fault_impossible"]
        seen = r["disagree_rows"] == r0["disagree_rows"] + 1 and r["sum_abs_diff"] == r0["sum_abs_diff"] + 1
        return (not seen), f"one agreeing row's file count + 1: disagreeing {r['disagree_rows']} against {r0['disagree_rows']}, abs diff {r['sum_abs_diff']} against {r0['sum_abs_diff']}"

    def run_finish():
        rows = {s: finishing(s, False) for s in seasons}
        return True, "finish states (TRUE / FALSE / UNKNOWN) and final-drive coverage by season: " + str(rows)

    def injected_finish():
        r = finishing(last[0], True); r0 = finishing(last[0], False)
        return not (r["injected_side_unknown"] > 0 and r["injected_side_false"] == 0 and r["final_drive_unchanged"]), f"final-drive participation removed for one side: {r} (unplanted unknown={r0['unknown']})"

    def run_boundary():
        leak, leak2, n, adm = boundary(cutoff); return leak == 0, f"training view of {cutoff.issue_time()} (fit week {cutoff.fit_week}): rows={n} rows past the boundary or from the hold-out={leak}"

    def injected_boundary():
        leak, leak2, n, adm = boundary(cutoff); return (leak2 > 0 or adm), f"hold-out injected into admitted_seasons: hold-out rows in the training view={leak2}, admits(hold-out)={adm}"

    def run_reducer():
        a = reducer(None); return not a, f"production reducer on injected pass/scramble/kneel/sack/spike/run events: nonzero audits={a or 'none'}"

    def injected_reducer():
        a = reducer("credit"); b = reducer("run"); c = reducer("event")
        caught = bool(a.get("pass_yards_ne_rec_yards")) and bool(b.get("runs_generated_ne_runs_allocated")) and bool(c.get("credits_ne_events_processed"))
        return not caught, f"altered credit caught {bool(a.get('pass_yards_ne_rec_yards'))}; missing run allocation caught {bool(b.get('runs_generated_ne_runs_allocated'))}; unprocessed event caught {bool(c.get('credits_ne_events_processed'))}"

    def run_key():
        F = pd.DataFrame([{**{k: "x" for k in K.KEY}, "p": 0.5, "reason": None}, {**{k: "x" for k in K.KEY}, "stat": "y", "p": None, "reason": "no_avg"}])
        try: product.write_contract(F, tempfile.gettempdir()); return True, "a contract with distinct keys and p-xor-reason rows is written"
        except product.DataGap as e: return False, str(e)

    def injected_key():
        F = pd.DataFrame([{**{k: "x" for k in K.KEY}, "p": 0.5, "reason": None}] * 2)
        try: product.write_contract(F, tempfile.gettempdir()); return True, "a duplicated key was accepted"
        except product.DataGap as e: return False, f"a duplicated key is refused: {str(e)[:60]}"

    wrong_scoring = dict(K.SCORING, td=K.SCORING["td"] + 1)
    return [Check("POINTS", True, lambda: run_points(K.SCORING), lambda: run_points(wrong_scoring)),
            Check("INCOMPLETE", True, inc_run, inc_plant), Check("TD-YARDS", True, tdy_run, tdy_plant), Check("BOUNDS", True, bnd_run, bnd_plant),
            Check("DRIVE-END", False, run_drive, injected_drive), Check("CLOCK", False, run_clock, injected_clock), Check("ELIGIBLE", False, run_elig, injected_elig),
            Check("REPLAY", False, run_replay, injected_replay), Check("SNAPS", False, run_snaps, injected_snaps), Check("FINISHING", True, run_finish, injected_finish), Check("BOUNDARY", True, run_boundary, injected_boundary),
            Check("REDUCER", True, run_reducer, injected_reducer), Check("KEY", True, run_key, injected_key)]
