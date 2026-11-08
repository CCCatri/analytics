"""Does the card's EXCEL / STRUGGLE flag separate outcomes on a held-out season, and does it need the player's own projection to do so?

Football: a player projected above his own baseline by more than his usual game-to-game swing should finish above that baseline more often than a
player projected near it, and below it more often when projected below. The lift is the flagged lines' rate of finishing on the flagged side of the
baseline, minus the same rate for lines projected near it (|z| < 0.25). The flag is cards.excel_struggle, the same function the card calls.
Usage:
  python3 checks/check_excel_struggle.py ATLAS_ROWS.csv.gz [SEASON]
PASS when every flagged cell's lift on SEASON (default 2025) is at least 10 points and within 8 of the lift recorded in cards.FLAG_CELLS, and when
the injected fault - each cell's projections shuffled across its players within the week, so a projection no longer belongs to the player who gets
it - earns no positive lift: at most +5 points, and at least 15 below the real lift. Exit 1 otherwise."""
import sys, os, numpy as np, pandas as pd
ROWS_PATH = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None   # resolved before the move into slate-kit/
KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "slate-kit"); os.chdir(KIT); sys.path.insert(0, KIT)
import cards; from draws import load

def lift(f):
    rated = f[f.flag.isin(["EXCEL", "STRUGGLE", "WITHIN NOISE"])]; hi, lo, near = rated[rated.flag == "EXCEL"], rated[rated.flag == "STRUGGLE"], rated[rated.z.abs() < 0.25]
    if len(hi) + len(lo) == 0 or len(near) == 0: return np.nan, 0.0, 0
    correct = ((hi.outcome > hi.baseline).sum() + (lo.outcome < lo.baseline).sum()) / (len(hi) + len(lo))
    base_rate = ((near.outcome > near.baseline).mean() * len(hi) + (near.outcome < near.baseline).mean() * len(lo)) / (len(hi) + len(lo))
    return 100 * (correct - base_rate), (len(hi) + len(lo)) / len(rated), len(rated)

def run(rows, history, season, shuffle=False):
    rng = np.random.default_rng(20261108); out = []
    for week, w in rows.groupby("week"):
        w = w.copy()
        if shuffle:
            for _, idx in w.groupby(["term", "position"]).groups.items(): w.loc[idx, "draw_mean"] = rng.permutation(w.loc[idx, "draw_mean"].to_numpy())
        out.append(pd.concat([w[["term", "position", "outcome"]], cards.excel_struggle(w, history, season, int(week))], axis=1))
    return pd.concat(out)

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    rows = pd.read_csv(ROWS_PATH); rows = rows[(rows.season == season) & rows.set_index(["term", "position"]).index.isin(list(cards.FLAG_CELLS))]
    history = load(); history = history[history.season == season]
    real, shuffled = run(rows, history, season), run(rows, history, season, shuffle=True); ok = True
    print(f"EXCEL / STRUGGLE on {season} held out: lift in points (recorded on {season} | measured now | shuffled projections), flagged share, rated lines")
    for (term, position), (col, t, dev_lift, hold_lift) in cards.FLAG_CELLS.items():
        r, s = real[(real.term == term) & (real.position == position)], shuffled[(shuffled.term == term) & (shuffled.position == position)]
        lr, share, n = lift(r); ls, _, _ = lift(s)
        good = np.isfinite(lr) and lr >= 10 and abs(lr - hold_lift) <= 8 and np.isfinite(ls) and ls <= 5 and lr - ls >= 15; ok &= bool(good)
        print(f"   {term:20s} {position:3s} t {t:4.2f}  recorded {hold_lift:+4d} | now {lr:+6.1f} | shuffled {ls:+6.1f}   flagged {share:5.1%} of {n:5d}   {'PASS' if good else 'FAIL'}")
    print(f"EXCEL / STRUGGLE CHECK {'PASS' if ok else 'FAIL'}"); sys.exit(0 if ok else 1)
