"""The quality gate of acceptance-criteria/possession-ends.md, clause 4: the engine's possession ends against the play-by-play record's, every cell.
One definition (rules.possession_ends) on both sides: the record's six seasons (out/possessions_possessions.csv and the raw play-by-play) and the engine's
generated games (out/handoff/games_2024_w15.csv.gz, every draw; possessions by check_possessions.possessions, as on the record).
Every (stop, score on the play) cell prints per game, record beside engine, with 2SE (over games); a cell zero on one side prints as 0, never dropped (clause 2).
A cell is MET when |engine - record| <= 2 * sqrt(SE_record^2 + SE_engine^2); NOT MET otherwise, marked 'never plays' when the engine has none.
Points per game by side (offense; the side without the ball) are judged the same way.
Self-test first, each must hold or the check is blind and exits 1:
  - the record against itself, 200 random halvings of its games (seeds 0-199): the share of cells read NOT MET is the check's false-alarm rate; it must be
    0.08 or less (2SE expects about 0.05), printed with the worst cell;
  - the record as 'engine' with every pick-six's points taken off: the cell (interception, other side 6) reads NOT MET;
  - a table with one cell dropped fails the completeness rule.
Exit 0 only when every cell is MET; exit 1 otherwise (the engine's scores are then not accepted as forecasts). Reads only; writes nothing.
python3 checks/check_possession_ends.py"""
import os, sys
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "product"))
import record, policy
from rules import possession_ends, STOP_ORDER
import check_possessions as cp
POSS = os.path.join(ROOT, "out", "possessions_possessions.csv"); GAMES = os.path.join(ROOT, "out", "handoff", "games_2024_w15.csv.gz")
COLS = ["game_id", "order_sequence", "play_type", "posteam", "two_point_attempt", "interception", "fumble_lost", "touchdown", "safety", "down", "ydstogo",
        "yards_gained", "home_team", "away_team", "total_home_score", "total_away_score"]


def record_ends():
    P = pd.read_csv(POSS, skiprows=1); out = []
    for y in sorted({int(g[:4]) for g in P["game_id"]}):
        r = record.raw_frame(policy.PBP_FILE.format(season=y), COLS, f"possession ends {y}")
        r["seq"] = pd.to_numeric(r["order_sequence"], errors="coerce").astype(float)
        out.append(possession_ends(P[P["game_id"].str[:4].astype(int) == y], r))
    return pd.concat(out, ignore_index=True), sorted(P["game_id"].unique())


def engine_ends():
    e = pd.read_csv(GAMES, dtype=str, keep_default_na=False)
    e["game_id"] = e["game_id"] + "#" + e["draw_id"]
    for c in ("order_sequence", "qtr", "two_point_attempt", "interception"): e[c] = pd.to_numeric(e[c], errors="coerce")
    for c in ("posteam", "fumble_recovery_1_team"): e[c] = e[c].replace("", np.nan)
    e["seq"] = e["order_sequence"].astype(float)
    P = cp.possessions(e.sort_values(["game_id", "order_sequence"]).reset_index(drop=True))
    X = possession_ends(P, e.assign(two_point_attempt=e["two_point_attempt"].fillna(0).astype(str)))
    return X, sorted(P["game_id"].unique()), e["draw_id"].nunique()


def per_game(X, games):
    """{cell: (mean per game, SE over games)} plus {side: (points mean, SE)}; every game counts, a game without the cell counts 0."""
    g = pd.Index(games, name="game_id")
    X = X.assign(cell=list(zip(X["stop"], X["score"])))
    cells = {}
    for cell, x in X.groupby("cell"):
        v = x.groupby("game_id").size().reindex(g, fill_value=0).to_numpy(float)
        cells[cell] = (v.mean(), v.std(ddof=1) / np.sqrt(len(v)))
    pts = {}
    for side in ("offense", "other side"):
        x = X[X["score"].str.startswith(side)].assign(p=lambda d: d["score"].str.split().str[-1].astype(int))
        v = x.groupby("game_id")["p"].sum().reindex(g, fill_value=0).to_numpy(float)
        pts[side] = (v.mean(), v.std(ddof=1) / np.sqrt(len(v)))
    return cells, pts


def judge(rec, eng):
    """Rows (label, record mean, record 2SE, engine mean, engine 2SE, verdict) over the union of cells; the table is complete by construction."""
    rows = []
    for cell in sorted(set(rec) | set(eng), key=lambda c: (STOP_ORDER.index(c[0]), c[1])):
        (rm, rs), (em, es) = rec.get(cell, (0.0, 0.0)), eng.get(cell, (0.0, 0.0))
        ok = abs(em - rm) <= 2 * np.hypot(rs, es)
        rows.append((cell, rm, 2 * rs, em, 2 * es, "MET" if ok else ("NOT MET, never plays" if em == 0 else "NOT MET")))
    return rows


def complete(rows, rec, eng):
    return {r[0] for r in rows} == set(rec) | set(eng)


def main():
    R, rg = record_ends(); E, eg, nd = engine_ends()
    rec, rpts = per_game(R, rg); eng, epts = per_game(E, eg)
    blind = []
    from collections import Counter
    alarms, trials, per_cell = 0, 0, Counter()
    gid = R["game_id"].to_numpy()
    for seed in range(200):
        half = set(np.random.default_rng(seed).choice(rg, len(rg) // 2, replace=False)); m = np.array([g in half for g in gid])
        a = [g for g in rg if g in half]; b = [g for g in rg if g not in half]
        for r in judge(per_game(R[m], a)[0], per_game(R[~m], b)[0]):
            trials += 1
            if r[5] != "MET": alarms += 1; per_cell[r[0]] += 1
    rate = alarms / trials; worst = per_cell.most_common(1)[0] if per_cell else (None, 0)
    print(f"  self-test, the record against itself, 200 random halvings: false-alarm rate {rate:.3f} over {trials} cell judgments (want 0.08 or less; 2SE expects about 0.05) | worst cell {worst[0]} {worst[1] / 200:.3f}")
    if rate > 0.08: blind.append(f"the record against itself reads NOT MET at rate {rate:.3f}")
    F = R.copy(); F.loc[(F["stop"] == "interception") & (F["score"] == "other side 6"), "score"] = "none"
    rows_f = judge(rec, per_game(F, rg)[0]); v = {r[0]: r[5] for r in rows_f}.get(("interception", "other side 6"))
    print(f"  self-test, the record with every pick-six's points taken off: (interception, other side 6) -> {v} (want NOT MET)")
    if not (v or "").startswith("NOT MET"): blind.append("pick-sixes removed read MET")
    rows = judge(rec, eng); dropped = rows[:-1]
    print(f"  self-test, a table with one cell dropped: complete {complete(dropped, rec, eng)} (want False)")
    if complete(dropped, rec, eng): blind.append("a dropped cell went unseen")
    if blind:
        print("POSSESSION ENDS self-test: FAIL, the check is blind:", "; ".join(blind)); sys.exit(1)
    print("POSSESSION ENDS self-test: PASS")
    print(f"\n  record: {len(R)} possessions, {len(rg)} games | engine: {len(E)} possessions, {len(eg)} games ({nd} draws of 2024 week 15)")
    print("  stop               | score on the play | record per game (2SE) | engine per game (2SE) | verdict")
    for cell, rm, r2, em, e2, w in rows: print(f"    {cell[0]:18s} | {cell[1]:13s} | {rm:.4f} ({r2:.4f}) | {em:.4f} ({e2:.4f}) | {w}")
    prow = []
    for side in ("offense", "other side"):
        (rm, rs), (em, es) = rpts[side], epts[side]; ok = abs(em - rm) <= 2 * np.hypot(rs, es)
        prow.append(ok); print(f"  points a game, {side:10s}: record {rm:.3f} (2SE {2 * rs:.3f}) | engine {em:.3f} (2SE {2 * es:.3f}) | {'MET' if ok else 'NOT MET'}")
    nm = [r for r in rows if r[5] != "MET"]
    print(f"  table complete (law clause 2): {complete(rows, rec, eng)}")
    met = not nm and all(prow) and complete(rows, rec, eng)
    print(f"QUALITY GATE possession ends: {'MET' if met else 'NOT MET'} | cells not met {len(nm)} of {len(rows)} | points sides not met {prow.count(False)} of 2 | the engine's scores are {'accepted' if met else 'not accepted'} as forecasts")
    sys.exit(0 if met else 1)


if __name__ == "__main__":
    main()
