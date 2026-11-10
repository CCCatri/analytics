"""Dropback rate by score state: the engine's generated games against the play-by-play record, same games, same definitions.

Question it answers: does the simulated offense pass more when behind and less when ahead, as real offenses do?
It checks a behavior R1b removed (the play kind keyed by score only in the last 2:00 of a half), not the clock behavior R1b targeted.

Rules it rests on (2026 NFL Rulebook; citations to be confirmed against the repo's rule text before commit):
  11-1-2  types of scoring plays: the score state is the offense's points minus the defense's before the snap.
  3-41    two-minute warning: the window inside it (last 2:00 of quarters 2 and 4) is reported apart, since R1b keys score there already.
  8-1-2   legal forward pass: a dropback is a snap recorded with pass = 1 (pass, sack, scramble); a run is play_type run with pass = 0.

Declared before any run:
  PASS when every score state's pooled gap (generated minus record, outside the last 2:00 of a half) is within +/-0.030.
  Injected fault 1 (identity: the record compared with itself) must PASS with every gap 0.000 and the width ratio 1.000.
  Injected fault 2 (score-blind: the record's dropback flags shuffled across score states within season and quarter) must FAIL.
  The current product is predicted to FAIL: about -0.10 behind 9+ and +0.12 ahead 9+ (the pool read measured +.106 and -.122 as record minus draw).
  A verdict on the product counts only when both injected faults behave as declared.

Usage (from the repo root): PYTHONPATH=product python3 checks/check_dropback_by_score.py out/engine_alone
"""
import glob, os, sys
import numpy as np
import pandas as pd
import record, policy

TOL = 0.030
SHUFFLE_SEED = 20261109   # injected fault 2 only; printed with its result
STATES = ["behind 9+", "behind 1-8", "tied", "ahead 1-8", "ahead 9+"]
COLS = ["game_id", "order_sequence", "posteam", "home_team", "qtr", "quarter_seconds_remaining",
        "play_type", "pass", "two_point_attempt", "total_home_score", "total_away_score"]
NUM = ["order_sequence", "qtr", "quarter_seconds_remaining", "pass", "two_point_attempt", "total_home_score", "total_away_score"]


def score_bin(d):
    return "behind 9+" if d <= -9 else ("behind 1-8" if d < 0 else ("tied" if d == 0 else ("ahead 1-8" if d <= 8 else "ahead 9+")))


def snaps(df):
    """One row per offensive snap (run or dropback) in regulation, with the offense's score state before the snap."""
    df = df.copy()
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
    th = df.groupby("game_id")["total_home_score"].transform(lambda s: s.ffill().shift().fillna(0))   # the score before the row; every game starts 0-0
    ta = df.groupby("game_id")["total_away_score"].transform(lambda s: s.ffill().shift().fillna(0))
    df["diff"] = np.where(df["posteam"] == df["home_team"], th - ta, ta - th)
    keep = df["play_type"].isin(["pass", "run"]) & (df["two_point_attempt"] != 1) & (df["qtr"] <= 4) & df["posteam"].notna() & (df["posteam"] != "")
    s = df[keep].copy()
    s["dropback"] = (s["pass"] == 1).astype(int)
    s["state"] = [score_bin(x) for x in s["diff"]]
    s["late"] = s["qtr"].isin([2, 4]) & (s["quarter_seconds_remaining"] <= 120)
    return s[["game_id", "posteam", "qtr", "late", "state", "dropback"]]


def rates(s):
    out = s[~s["late"]].groupby("state")["dropback"].agg(["mean", "size"])
    return {k: (float(out.loc[k, "mean"]) if k in out.index else np.nan, int(out.loc[k, "size"]) if k in out.index else 0) for k in STATES}


def width(s):
    """Spread of team-game dropbacks across all regulation snaps: the downstream width the score key protects."""
    return float(s.groupby(["game_id", "posteam"])["dropback"].sum().std(ddof=1))


def passes(pairs):
    """The pass rule, written only here: every score state's pooled gap (generated minus record, outside the last 2:00 of a half) within TOL.
    pairs: {season: (generated snaps, record snaps)} or a list of such pairs."""
    items = pairs.values() if isinstance(pairs, dict) else pairs
    gaps = {k: [] for k in STATES}
    for g, r in items:
        rg, rr = rates(g), rates(r)
        for k in STATES:
            gaps[k].append(rg[k][0] - rr[k][0])
    return all(abs(np.array(gaps[k], float).mean()) <= TOL for k in STATES)


def score(pairs, label):
    """pairs: {season: (generated snaps, record snaps)}. Prints the table and returns PASS or FAIL."""
    seasons = sorted(pairs)
    gaps = {k: [] for k in STATES}; wr = []
    print(f"\n----- {label} -----")
    print("season | " + " | ".join(f"{k}: gen-rec (n gen)" for k in STATES) + " | width gen/rec")
    for y in seasons:
        g, r = pairs[y]; rg, rr = rates(g), rates(r)
        cells = []
        for k in STATES:
            gp = rg[k][0] - rr[k][0]; gaps[k].append(gp); cells.append(f"{gp:+.3f} ({rg[k][1]})")
        w = width(g) / width(r); wr.append(w)
        print(f"{y} | " + " | ".join(cells) + f" | {w:.3f}")
    verdict = "PASS" if passes(pairs) else "FAIL"
    print("pooled over seasons (mean, 2SE across seasons, seasons with the same sign as the pool):")
    for k in STATES:
        a = np.array(gaps[k], float); m = a.mean(); se2 = 2 * a.std(ddof=1) / np.sqrt(len(a))
        same = int(np.sum(np.sign(a) == np.sign(m))) if m != 0 else 0
        ok = abs(m) <= TOL
        print(f"  {k:<11} gap {m:+.3f}  2SE {se2:.3f}  same sign {same} of {len(a)}  {'within' if ok else 'OUTSIDE'} +/-{TOL:.3f}")
    print(f"  width of team-game dropbacks, generated / record: mean {np.mean(wr):.3f} over {len(wr)} seasons (1.000 = right width; below 1 = too narrow)")
    print(f"{label}: {verdict}")
    return verdict


def main(gen_dir):
    files = sorted(glob.glob(os.path.join(gen_dir, "alone_*.csv")))
    if not files:
        print(f"check_dropback_by_score: no alone_*.csv in {gen_dir}: NOT RUN"); return 2
    real, gen = {}, {}
    for f in files:
        y = int(os.path.basename(f)[6:10])
        print(f"reading season {y}: generated {os.path.basename(f)}, record {policy.PBP_FILE.format(season=y)} ...", flush=True)
        g = pd.read_csv(f, usecols=COLS, dtype=str, keep_default_na=False)
        r = record.raw_frame(policy.PBP_FILE.format(season=y), COLS, f"dropback by score {y}")
        common = set(g["game_id"]) & set(r["game_id"])
        gen[y] = snaps(g[g["game_id"].isin(common)]); real[y] = snaps(r[r["game_id"].isin(common)])
        print(f"  games in both {len(common)} | snaps generated {len(gen[y])} record {len(real[y])}", flush=True)

    v1 = score({y: (real[y], real[y]) for y in real}, "injected fault 1, identity (must PASS)")
    rng = np.random.default_rng(SHUFFLE_SEED); blind = {}
    for y, r in real.items():
        b = r.copy(); m = ~b["late"]
        for _, ix in b[m].groupby("qtr").groups.items():
            b.loc[ix, "dropback"] = rng.permutation(b.loc[ix, "dropback"].to_numpy())
        blind[y] = b
    print(f"(injected fault 2 shuffle seed {SHUFFLE_SEED})")
    v2 = score({y: (blind[y], real[y]) for y in real}, "injected fault 2, score-blind (must FAIL)")
    faults_ok = (v1 == "PASS" and v2 == "FAIL")
    print(f"\ninjected faults behaved as declared: {'YES' if faults_ok else 'NO: the product verdict below does not count'}")
    vp = score({y: (gen[y], real[y]) for y in real}, "current product: generated games vs the record")
    print("\n===== VERDICT =====")
    print(f"check_dropback_by_score: product {vp} | injected faults {'counted' if faults_ok else 'REFUSED'}")
    print("Paste this whole printout back to Claude.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "out/engine_alone"))
