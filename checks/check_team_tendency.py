"""Team dropback tendency: the engine's generated games against the play-by-play record, same games, same definitions.

Question it answers: do simulated offenses differ in dropback share beyond their situations, as real offenses do?
Measured link it rests on (2026-11-09, held seasons): a team's tendency from its earlier games this season predicts its next game,
slope +1.04 +/-0.12 over six held seasons, team-shuffled control -0.17 +/-0.16: ESTABLISHED.

Rules it rests on: 8-1-2 legal forward pass (a dropback is a snap recorded with pass = 1: pass, sack, scramble; a run is play_type run with pass = 0).

Declared before any run:
  u = a team-game's dropback share minus its situation-expected share (the record's own rate that season by score state, down, distance and the late window).
  tendency = the spread of team-season means of u beyond game-to-game spread (one-way random effects), per season; pooled as a mean with 2SE across seasons.
  PASS when the engine's pooled tendency clears zero by more than 2SE and is no more than the record's pooled tendency plus its 2SE.
  Injected fault 1 (identity: the record as the generated side) must PASS.
  Injected fault 2 (the record with team labels shuffled within season, as the generated side) must FAIL.
  The engine at da71fd3 (no team input) is predicted to FAIL: tendency -0.001 +/-0.004 (width read v1).
  A verdict on the product counts only when both injected faults behave as declared.
  Printed, not judged: the width of team-game dropbacks split into its plays part (L2) and its dropback-share part (L3), generated / record.

Usage (from the repo root): PYTHONPATH=product python3 checks/check_team_tendency.py out/engine_alone
"""
import glob, os, sys
import numpy as np, pandas as pd
import record, policy

SEED = 20261109   # injected fault 2 only; printed with its result
COLS = ["game_id", "order_sequence", "posteam", "home_team", "qtr", "quarter_seconds_remaining", "play_type", "pass",
        "two_point_attempt", "total_home_score", "total_away_score", "down", "ydstogo"]
NUM = ["order_sequence", "qtr", "quarter_seconds_remaining", "pass", "two_point_attempt", "total_home_score", "total_away_score", "down", "ydstogo"]


def score_bin(d):
    return "behind 9+" if d <= -9 else ("behind 1-8" if d < 0 else ("tied" if d == 0 else ("ahead 1-8" if d <= 8 else "ahead 9+")))


def dist_bin(x):
    return "1-3" if x <= 3 else ("4-6" if x <= 6 else ("7-10" if x <= 10 else "11+"))


def snaps(df):
    df = df.copy()
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
    th = df.groupby("game_id")["total_home_score"].transform(lambda s: s.ffill().shift().fillna(0))
    ta = df.groupby("game_id")["total_away_score"].transform(lambda s: s.ffill().shift().fillna(0))
    df["diff"] = np.where(df["posteam"] == df["home_team"], th - ta, ta - th)
    keep = df["play_type"].isin(["pass", "run"]) & (df["two_point_attempt"] != 1) & (df["qtr"] <= 4) & df["posteam"].notna() & (df["posteam"] != "") & df["down"].between(1, 4)
    s = df[keep].copy()
    s["dropback"] = (s["pass"] == 1).astype(int)
    s["late"] = s["qtr"].isin([2, 4]) & (s["quarter_seconds_remaining"] <= 120)
    s["cell"] = [f"{score_bin(d)}|{int(dn)}|{dist_bin(t)}|{int(l)}" for d, dn, t, l in zip(s["diff"], s["down"], s["ydstogo"], s["late"])]
    return s[["game_id", "posteam", "cell", "dropback"]]


def team_games(s, cell_rate, overall):
    s = s.assign(e=s["cell"].map(cell_rate).fillna(overall))
    g = s.groupby(["game_id", "posteam"]).agg(n=("dropback", "size"), k=("dropback", "sum"), e=("e", "mean")).reset_index()
    g["rate"] = g["k"] / g["n"]; g["u"] = g["rate"] - g["e"]
    return g


def tendency(g):
    grp = g.groupby("posteam")["u"]
    comp = grp.mean().var(ddof=1) - (grp.var(ddof=1) / grp.size()).mean()
    return float(np.sign(comp) * np.sqrt(abs(comp)))


def parts(g):
    rbar, nbar = g["rate"].mean(), g["n"].mean()
    return g["k"].std(ddof=1), (g["n"] * rbar).std(ddof=1), (nbar * g["rate"]).std(ddof=1)


def pooled(a):
    a = np.array(a, float)
    return a.mean(), 2 * a.std(ddof=1) / np.sqrt(len(a))


def score(pairs, label):
    """pairs: {season: (generated team-games, record team-games)}."""
    tg, tr, w = [], [], []
    print(f"\n----- {label} -----")
    print("season | tendency generated | tendency record | width gen/rec | plays part gen/rec | dropback-share part gen/rec")
    for y in sorted(pairs):
        g, r = pairs[y]; a, b = tendency(g), tendency(r); pg, pr = parts(g), parts(r)
        tg.append(a); tr.append(b); w.append([pg[i] / pr[i] for i in range(3)])
        print(f"{y} | {a:+.3f} | {b:+.3f} | {w[-1][0]:.3f} | {w[-1][1]:.3f} | {w[-1][2]:.3f}")
    mg, sg = pooled(tg); mr, sr = pooled(tr); wm = np.mean(w, axis=0)
    ok = (mg - sg > 0) and (mg <= mr + sr)
    print(f"pooled: tendency generated {mg:+.3f} +/-{sg:.3f} | record {mr:+.3f} +/-{sr:.3f} | clears zero: {mg - sg > 0} | not above the record: {mg <= mr + sr}")
    print(f"pooled width parts (printed, not judged): width {wm[0]:.3f} | plays part {wm[1]:.3f} | dropback-share part {wm[2]:.3f}")
    v = "PASS" if ok else "FAIL"
    print(f"{label}: {v}")
    return v


def main(gen_dir):
    files = sorted(glob.glob(os.path.join(gen_dir, "alone_*.csv")))
    if not files:
        print(f"check_team_tendency: no alone_*.csv in {gen_dir}: NOT RUN"); return 2
    rng = np.random.default_rng(SEED); real, gen, shuf = {}, {}, {}
    for f in files:
        y = int(os.path.basename(f)[6:10])
        print(f"reading season {y}: generated {os.path.basename(f)}, record {policy.PBP_FILE.format(season=y)} ...", flush=True)
        g0 = pd.read_csv(f, usecols=COLS, dtype=str, keep_default_na=False)
        r0 = record.raw_frame(policy.PBP_FILE.format(season=y), COLS, f"team tendency {y}")
        common = set(g0["game_id"]) & set(r0["game_id"])
        rs, gs = snaps(r0[r0["game_id"].isin(common)]), snaps(g0[g0["game_id"].isin(common)])
        cell_rate = rs.groupby("cell")["dropback"].mean(); overall = rs["dropback"].mean()
        real[y], gen[y] = team_games(rs, cell_rate, overall), team_games(gs, cell_rate, overall)
        sh = real[y].copy(); sh["posteam"] = rng.permutation(sh["posteam"].to_numpy()); shuf[y] = sh
        print(f"  games in both {len(common)} | team-games generated {len(gen[y])} record {len(real[y])}", flush=True)
    v1 = score({y: (real[y], real[y]) for y in real}, "injected fault 1, identity (must PASS)")
    print(f"(injected fault 2 shuffle seed {SEED})")
    v2 = score({y: (shuf[y], real[y]) for y in real}, "injected fault 2, teams shuffled (must FAIL)")
    faults_ok = (v1 == "PASS" and v2 == "FAIL")
    print(f"\ninjected faults behaved as declared: {'YES' if faults_ok else 'NO: the product verdict below does not count'}")
    vp = score({y: (gen[y], real[y]) for y in real}, "current product: generated games vs the record")
    print("\n===== VERDICT =====")
    print(f"check_team_tendency: product {vp} | injected faults {'counted' if faults_ok else 'REFUSED'}")
    print("Paste this whole printout back to Claude.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "out/engine_alone"))
