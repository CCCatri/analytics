"""DK DFS held (the project owner's ruling, 2026-11-10; acceptance-criteria/full-game-lines.md, clause 6). On a card: every DK DFS row (DK dk_points) is marked
NOT ISSUED - HELD and no other row is; on the replay's judgment (proj/product_judgment.csv): no DK DFS cell (DK dk_points, DK team total) is judged.
python3 checks/check_dk_dfs_held.py CARD.csv   |   --self-test (an issued DK DFS row, a held F8 row, and a judged DK DFS cell must each FAIL)
Exit 0 when all hold; 1 otherwise. Reads only; writes nothing."""
import os, sys, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "slate-kit"))
from dk import DK_TERM
from cards import DK_DFS_HELD
from draws import DK_TEAM_TERM


def judge(card, judged):
    bad = []
    dk, other = card[card.term == DK_TERM], card[card.term != DK_TERM]
    bad += [f"DK DFS row issued: {p} ({s})" for p, s in zip(dk.player_id, dk.issuable) if s != DK_DFS_HELD]
    bad += [f"{t} row held: {p}" for p, t, s in zip(other.player_id, other.term, other.issuable) if s == DK_DFS_HELD]
    bad += [f"DK DFS cell judged: {t} {p} -> {v}" for t, p, v in zip(judged.term, judged.position, judged.verdict) if t in (DK_TERM, DK_TEAM_TERM)]
    return bad


def self_test():
    card = pd.DataFrame(dict(player_id=["a", "a", "b"], term=[DK_TERM, "F8 dk_points", DK_TERM], issuable=[DK_DFS_HELD, "ISSUABLE", DK_DFS_HELD]))
    judged = pd.DataFrame(dict(term=["F8 dk_points"], position=["WR"], verdict=["UNCHANGED"]))
    good = judge(card, judged)
    issued = judge(card.assign(issuable=["ISSUABLE", "ISSUABLE", DK_DFS_HELD]), judged)
    held_f8 = judge(card.assign(issuable=[DK_DFS_HELD, DK_DFS_HELD, DK_DFS_HELD]), judged)
    judged_dk = judge(card, pd.concat([judged, pd.DataFrame(dict(term=[DK_TERM], position=["QB"], verdict=["WORSE"]))]))
    ok = not good and bool(issued) and bool(held_f8) and bool(judged_dk)
    print(f"self-test: as built -> {len(good)} failures (want 0) | an issued DK DFS row -> {len(issued)} (want 1+) | a held F8 row -> {len(held_f8)} (want 1+) | a judged DK DFS cell -> {len(judged_dk)} (want 1+) | {'PASS' if ok else 'FAIL, the check is blind'}")
    return ok


def main(card_path):
    from ingest import PROJ_DIR
    judgment = os.path.join(PROJ_DIR, "product_judgment.csv")
    for p in (card_path, judgment):
        if not os.path.exists(p): print(f"REFUSED: input missing: {p}"); sys.exit(1)
    card, judged = pd.read_csv(card_path), pd.read_csv(judgment); card["player_id"] = card.player_id.astype(str)
    bad = judge(card, judged)
    print(f"card: DK DFS rows {int((card.term == DK_TERM).sum())}, held {int((card.issuable == DK_DFS_HELD).sum())} | judgment cells {len(judged)}, DK DFS among them {int(judged.term.isin([DK_TERM, DK_TEAM_TERM]).sum())}")
    for b in bad[:20]: print("  FAIL:", b)
    print(f"DK DFS HELD: {'PASS' if not bad else 'FAIL'} | failures {len(bad)}")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    if "--self-test" in sys.argv: sys.exit(0 if self_test() else 1)
    if len(sys.argv) != 2: print(__doc__); sys.exit(1)
    main(sys.argv[1])
