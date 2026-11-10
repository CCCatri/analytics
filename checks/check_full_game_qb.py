"""Full-game quarterbacks on the card (the project owner's premise, 2026-11-08: if he starts he plays the whole game; acceptance-criteria/one-game-one-reality.md).
On a card built from its frozen draws: (1) every quarterback with a world draws his attempts at the full-game share of his team's attempts (the share named in his
line's provenance, within 0.01); (2) his DK draws equal his F8 draws in the worlds he starts and 0 everywhere else, draw by draw; (3) his passing lines say they are
given he starts and plays the full game.
python3 checks/check_full_game_qb.py FROZEN.npz CARD.csv TEAM.npz   |   --self-test (a quarterback at a relief share, and DK scored outside his worlds, must both FAIL)
Exit 0 when all hold; 1 otherwise. Reads only; writes nothing."""
import re, sys, os, numpy as np, pandas as pd
FULL_LABEL = "given he starts and plays the full game (the project owner's premise, 2026-11-08)"
PASSING = ("Q1 attempts", "Q2 completions", "Q3 passing yards", "Q4 passing TDs", "Q5 interceptions")


def judge(qb_att, team_att, share, dk, f8, starts, labels):
    """qb_att {key: (team, attempts draws)}; team_att {team: draws}; dk / f8 / starts {key: draws}; labels {key: [conditioning of his passing lines]}. Returns failures."""
    bad = []
    for k, (team, a) in qb_att.items():
        r = a.mean() / team_att[team].mean()
        if abs(r - share) > 0.01: bad.append(f"{k} ({team}): attempts {a.mean():.2f} are {r:.3f} of the team's, not the full-game share {share:.4f}")
    for k, s in starts.items():
        if k in dk and k in f8 and not np.array_equal(dk[k], np.where(s, f8[k], 0.0)): bad.append(f"{k}: DK draws are not his F8 in the worlds he starts and 0 elsewhere")
    for k, ls in labels.items():
        if any(l != FULL_LABEL for l in ls): bad.append(f"{k}: a passing line is not labelled '{FULL_LABEL}'")
    return bad


def self_test():
    rng = np.random.default_rng(0); team = rng.poisson(34, 2000).astype(float); s = rng.random(2000) < 0.9; f8 = rng.normal(18, 6, 2000)
    good = judge({"q": ("T", np.round(team * 0.997))}, {"T": team}, 0.997, {"q": np.where(s, f8, 0.0)}, {"q": f8}, {"q": s}, {"q": [FULL_LABEL] * 5})
    relief = judge({"q": ("T", np.round(team * 0.12))}, {"T": team}, 0.997, {"q": np.where(s, f8, 0.0)}, {"q": f8}, {"q": s}, {"q": [FULL_LABEL] * 5})
    leak = judge({"q": ("T", np.round(team * 0.997))}, {"T": team}, 0.997, {"q": f8}, {"q": f8}, {"q": s}, {"q": [FULL_LABEL] * 5})
    ok = not good and bool(relief) and bool(leak)
    print(f"self-test: full-game quarterback -> {len(good)} failures (want 0) | relief share -> {len(relief)} (want 1+) | DK outside his worlds -> {len(leak)} (want 1+) | {'PASS' if ok else 'FAIL, the check is blind'}")
    return ok


def main(frozen, card_path, team_path):
    for p in (frozen, card_path, team_path):
        if not os.path.exists(p): print(f"REFUSED: input missing: {p}"); sys.exit(1)
    z = np.load(frozen, allow_pickle=False); keys, terms, draws = z["keys"].astype(str), z["terms"].astype(str), z["draws"].astype(float)
    if "starts_keys" not in z.files: print("REFUSED: the frozen draws carry no worlds (starts_keys)"); sys.exit(1)
    starts = dict(zip(z["starts_keys"].astype(str), z["starts"]))
    card = pd.read_csv(card_path); card["player_id"] = card["player_id"].astype(str)
    q = card[(card["position"] == "QB") & card["player_id"].isin(starts)]
    prov = q.loc[q["term"] == "Q1 attempts", "provenance"].astype(str)
    found = {float(m.group(1)) for m in (re.search(r"full-game share ([0-9.]+)", p) for p in prov) if m}
    if len(found) != 1: print(f"REFUSED: the quarterback attempts lines name {len(found)} full-game shares ({sorted(found)}), not one"); sys.exit(1)
    share = found.pop()
    t = np.load(team_path, allow_pickle=False)
    team_att = {k: r for k, term, r in zip(t["keys"].astype(str), t["terms"].astype(str), t["draws"].astype(float)) if term == "F2 team attempts"}
    team_of = dict(zip(q["player_id"], q["team"].astype(str)))
    row = {(k, term): d for k, term, d in zip(keys, terms, draws)}
    qb_att = {k: (team_of[k], row[(k, "Q1 attempts")]) for k in starts if (k, "Q1 attempts") in row and k in team_of}
    dk = {k: row[(k, "DK dk_points")] for k in starts if (k, "DK dk_points") in row}; f8 = {k: row[(k, "F8 dk_points")] for k in starts if (k, "F8 dk_points") in row}
    labels = {k: list(d.loc[d["term"].isin(PASSING), "conditioning"].astype(str)) for k, d in q.groupby("player_id")}
    bad = judge(qb_att, team_att, share, dk, f8, starts, labels)
    ratios = [a.mean() / team_att[tm].mean() for tm, a in qb_att.values()]
    print(f"card: quarterbacks with a world {len(starts)} | attempts lines {len(qb_att)} | full-game share {share:.4f} | their share of the team: min {min(ratios):.4f} max {max(ratios):.4f} | DK rows checked {len(dk)}")
    for b in bad[:20]: print("  FAIL:", b)
    print(f"FULL-GAME QUARTERBACKS: {'PASS' if not bad else 'FAIL'} | failures {len(bad)}")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    if "--self-test" in sys.argv: sys.exit(0 if self_test() else 1)
    if len(sys.argv) != 4: print(__doc__); sys.exit(1)
    main(*sys.argv[1:4])
