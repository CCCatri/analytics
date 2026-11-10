"""Validate the validators: each check's false-alarm rate on known-good copies and its catch rate on injected faults of graded strength, over many seeds.

Known-good: one half of a season's real games, chosen at random, compared with the other half. Both are real, so a reliable check passes.
Faults are injected into the first half only and compared with the untouched second half, at full, half and quarter strength.
Checks under test, each by its own passes() function, imported from the check so the rule is written in one place:
  check_dropback_by_score: every score state's pooled gap within TOL. Fault: dropback flags shuffled across score states within quarter, on that share of snaps.
  check_team_tendency: generated tendency clears zero by its 2SE and sits within the two 2SEs of its reference (here the other half). Fault: team labels shuffled on that share of team-games.
Battery self-test, required before any verdict counts: a blind check (always PASS) must read BLIND; a jumpy check (always FAIL) must read NOISY.
Labels: RELIABLE = false alarms at most 5% and full-strength catch at least 95%; BLIND = full-strength catch at most 5%; NOISY = false alarms 50% or more; else WEAK.
Half-season samples are noisier than the full-season comparisons the checks make, so these rates are conservative.

Usage (from the repo root): PYTHONPATH=product python3 checks/validate_checks.py [trials]
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import record, policy
import check_dropback_by_score as D
import check_team_tendency as T

SEED = 20261109
SEASONS = (2019, 2020, 2021, 2023, 2024, 2025)
STRENGTHS = (1.0, 0.5, 0.25)


def load():
    out = {}
    for y in SEASONS:
        r = record.raw_frame(policy.PBP_FILE.format(season=y), T.COLS, f"validate checks {y}")
        d, t = D.snaps(r), T.snaps(r)
        out[y] = (d, t, t.groupby("cell")["dropback"].mean(), float(t["dropback"].mean()), np.array(sorted(set(d["game_id"]))))
        print(f"  season {y}: snaps {len(d)} | games {len(out[y][4])}", flush=True)
    return out


def dropback_pass(pairs):
    return D.passes(pairs)


def tendency_pass(pairs):
    return T.passes([T.tendency(g) for g, _ in pairs], [T.tendency(r) for _, r in pairs])


def score_blind(d, s, rng):
    b = d.copy(); idx = b.index[~b["late"].to_numpy()]; pick = idx[rng.random(len(idx)) < s]
    for _, ix in b.loc[pick].groupby("qtr").groups.items():
        b.loc[ix, "dropback"] = rng.permutation(b.loc[ix, "dropback"].to_numpy())
    return b


def team_blind(g, s, rng):
    b = g.copy(); pick = np.flatnonzero(rng.random(len(b)) < s); col = b.columns.get_loc("posteam")
    b.iloc[pick, col] = rng.permutation(b["posteam"].to_numpy()[pick])
    return b


def rate(fails):
    p = float(np.mean(fails)); return p, 2 * np.sqrt(p * (1 - p) / len(fails))


def label(fa, catch):
    if catch <= 0.05: return "BLIND"
    if fa >= 0.50: return "NOISY"
    return "RELIABLE" if fa <= 0.05 and catch >= 0.95 else "WEAK"


def main(trials):
    print(f"validate_checks: {trials} trials, seed {SEED}; loading seasons ...", flush=True)
    data = load(); rng = np.random.default_rng(SEED)
    res = {c: {"good": [], **{s: [] for s in STRENGTHS}} for c in ("dropback", "tendency", "blind", "jumpy")}
    for i in range(trials):
        good_d, good_t, fd, ft = [], [], {s: [] for s in STRENGTHS}, {s: [] for s in STRENGTHS}
        for y in SEASONS:
            d, t, cr, ov, games = data[y]
            a = set(rng.permutation(games)[: len(games) // 2])
            dA, dB = d[d["game_id"].isin(a)], d[~d["game_id"].isin(a)]
            gA, gB = T.team_games(t[t["game_id"].isin(a)], cr, ov), T.team_games(t[~t["game_id"].isin(a)], cr, ov)
            good_d.append((dA, dB)); good_t.append((gA, gB))
            for s in STRENGTHS:
                fd[s].append((score_blind(dA, s, rng), dB)); ft[s].append((team_blind(gA, s, rng), gB))
        res["dropback"]["good"].append(not dropback_pass(good_d)); res["tendency"]["good"].append(not tendency_pass(good_t))
        res["blind"]["good"].append(False); res["jumpy"]["good"].append(True)
        for s in STRENGTHS:
            res["dropback"][s].append(not dropback_pass(fd[s])); res["tendency"][s].append(not tendency_pass(ft[s]))
            res["blind"][s].append(False); res["jumpy"][s].append(True)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  trial {i + 1}/{trials}", flush=True)
    print("\ncheck | false alarms on real-vs-real (2SE) | catch at full strength | half | quarter | label")
    labels = {}
    for c in ("dropback", "tendency", "blind", "jumpy"):
        fa, fae = rate(res[c]["good"]); cs = [rate(res[c][s]) for s in STRENGTHS]
        labels[c] = label(fa, cs[0][0])
        print(f"{c:<9} | {fa:.2f} +/-{fae:.2f} | " + " | ".join(f"{p:.2f} +/-{e:.2f}" for p, e in cs) + f" | {labels[c]}")
    selftest = labels["blind"] == "BLIND" and labels["jumpy"] == "NOISY"
    print(f"\nbattery self-test: {'PASS' if selftest else 'FAIL: the battery cannot tell a blind or jumpy check; no verdict below counts'}")
    print(f"validate_checks: check_dropback_by_score {labels['dropback']} | check_team_tendency {labels['tendency']} | battery self-test {'PASS' if selftest else 'FAIL'}")
    print("Paste this whole printout back to Claude.")
    return 0 if selftest else 1


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
