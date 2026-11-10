"""Full-game grading (the project owner's law, 2026-11-10; acceptance-criteria/full-game-lines.md). On the replay's outputs: every quarterback full-game line
(passing and F8) in proj/atlas_rows.csv.gz is from a game he started and finished; every quarterback DK line in proj/dk_rows.csv.gz is from a game with no
quarterback change during it; every row in proj/qb_other_games_rows.csv.gz is one of those lines from another kind of game, labelled with that kind; no row is in both.
python3 checks/check_full_game_grading.py   |   --self-test (a relief game among the graded rows, a finished game set apart, and a DK line from a game he left
graded, must each FAIL)
Exit 0 when all hold; 1 otherwise. Reads only; writes nothing."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "slate-kit"))
from draws import qb_games, split_full_game, QB_FULL_GAME_TERMS, FULL_GAME, EXIT_GAMES, DK_TERM


def judge(graded, apart, kinds):
    bad = []; k_of = lambda k, s, w: kinds.get((k, int(s), int(w)), "no record")
    q = graded[(graded.position == "QB") & graded.term.isin(QB_FULL_GAME_TERMS)]; d = graded[(graded.position == "QB") & (graded.term == DK_TERM)]
    for k, s, w, t in zip(q.key, q.season, q.week, q.term):
        if k_of(k, s, w) != FULL_GAME: bad.append(f"graded: {k} {s} w{w} {t} is a game of kind {k_of(k, s, w)!r}, not {FULL_GAME!r}")
    for k, s, w in zip(d.key, d.season, d.week):
        if k_of(k, s, w) in EXIT_GAMES: bad.append(f"graded: {k} {s} w{w} DK is from a game of kind {k_of(k, s, w)!r}")
    for k, s, w, t, g, p in zip(apart.key, apart.season, apart.week, apart.term, apart.game, apart.position):
        if p != "QB" or (t not in QB_FULL_GAME_TERMS and t != DK_TERM): bad.append(f"apart: {k} {s} w{w} {t} {p} is not a quarterback full-game or DK line")
        elif k_of(k, s, w) != g or g == FULL_GAME or (t == DK_TERM and g not in EXIT_GAMES): bad.append(f"apart: {k} {s} w{w} {t} labelled {g!r}, the record says {k_of(k, s, w)!r}")
    keys = lambda f: set(zip(f.key, f.season, f.week, f.term))
    both = keys(pd.concat([q, d])) & keys(apart)
    if both: bad.append(f"{len(both)} rows are both graded and apart")
    return bad


def self_test():
    rows = pd.DataFrame(dict(player_id=["a", "b1", "b2", "c1", "c2", "r"], season=2024, week=5, team=["A", "B", "B", "C", "C", "A"], position=["QB"] * 5 + ["RB"], attempts=[30, 25, 5, 0, 31, 1]))
    kinds = qb_games(rows); want = {("a", 2024, 5): FULL_GAME, ("b1", 2024, 5): "started, left early", ("b2", 2024, 5): "came in relief", ("c1", 2024, 5): "did not throw", ("c2", 2024, 5): FULL_GAME}
    g = pd.DataFrame(dict(season=2024, week=5, key=["a", "b1", "b2", "c2", "r", "a", "b1", "c1"], term=["Q1 attempts"] * 5 + [DK_TERM] * 3, position=["QB"] * 4 + ["RB"] + ["QB"] * 3, crps=1.0))
    graded, apart = split_full_game(g, kinds)
    ok_kinds = kinds == want; good = judge(graded, apart, kinds); kept = list(zip(graded.key, graded.term))
    relief = judge(pd.concat([graded, g[(g.key == "b2") & (g.term != DK_TERM)]]), apart[apart.key != "b2"], kinds)
    finished = judge(graded[graded.key != "a"], pd.concat([apart, g[g.key == "a"].assign(game="came in relief")]), kinds)
    left_dk = judge(pd.concat([graded, g[(g.key == "b1") & (g.term == DK_TERM)]]), apart[~((apart.key == "b1") & (apart.term == DK_TERM))], kinds)
    want_kept = [("a", "Q1 attempts"), ("c2", "Q1 attempts"), ("r", "Q1 attempts"), ("a", DK_TERM), ("c1", DK_TERM)]
    ok = ok_kinds and kept == want_kept and not good and bool(relief) and bool(finished) and bool(left_dk)
    print(f"self-test: kinds of game {'right' if ok_kinds else 'WRONG: ' + str(kinds)} | split keeps {kept == want_kept} (want a, c2, r passing; a, c1 DK) | as split -> {len(good)} failures (want 0) | a relief game graded -> {len(relief)} (want 1+) | a finished game set apart -> {len(finished)} (want 1+) | DK from a game he left graded -> {len(left_dk)} (want 1+) | {'PASS' if ok else 'FAIL, the check is blind'}")
    return ok


def main():
    from facts import load, read_table
    from ingest import PROJ_DIR
    paths = [os.path.join(PROJ_DIR, n) for n in ("atlas_rows.csv.gz", "dk_rows.csv.gz", "qb_other_games_rows.csv.gz")]
    for p in paths:
        if not os.path.exists(p): print(f"REFUSED: replay output missing: {p}"); sys.exit(1)
    graded, apart = pd.concat([read_table(paths[0]), read_table(paths[1])], ignore_index=True), read_table(paths[2]); graded["key"] = graded.key.astype(str); apart["key"] = apart.key.astype(str)
    bad = judge(graded, apart, qb_games(load()))
    q = graded[(graded.position == "QB") & graded.term.isin(QB_FULL_GAME_TERMS + (DK_TERM,))]
    print(f"replay: quarterback full-game and DK rows graded {len(q)} | apart {len(apart)} ({'; '.join(f'{t} {k} {v}' for (t, k), v in apart.groupby(['term', 'game']).size().items() if t in ('Q1 attempts', DK_TERM))})")
    for b in bad[:20]: print("  FAIL:", b)
    print(f"FULL-GAME GRADING: {'PASS' if not bad else 'FAIL'} | failures {len(bad)}")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    if "--self-test" in sys.argv: sys.exit(0 if self_test() else 1)
    main()
