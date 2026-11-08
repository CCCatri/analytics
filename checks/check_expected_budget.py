"""Do the card's players, in expectation, account for no more than the team's volume?

Football: every forward pass is one target, a throwaway or a spike (Rule 8, Forward Pass), so a team's receivers cannot be targeted more
often than the team throws, and its quarterbacks cannot attempt more passes than the team throws; every carry is one runner's (Rule 3,
Section 2, the ball carrier), so its runners and quarterbacks together cannot carry more than the team carries.
Every volume line on the card is priced given the player plays, and the card carries his P(plays) beside it. So two sums are printed per
team and budget: the card sum (every line added as printed, "if everyone on the card plays") and the expected sum (each line weighted by
its P(plays), what the card expects on the field). The verdict reads the expected sum: `Expected budget: PASS` (expected <= team) or
`FAIL` with the excess. The share of draws in which the card sum exceeds the team draw is printed beside it.
Usage:
  python3 checks/check_expected_budget.py FROZEN.npz CARD.csv TEAM.npz [--inject TEAM FACTOR]   readout; --inject multiplies that
      team's receiver-target rows by FACTOR before the check and requires the check to name the team, the budget and the excess; TEAM
      may be WORST: the passing team with the least headroom on targets. An injected overage smaller than a team's headroom is not an
      overage, so the readout prints each team's headroom and the fault is sized against it.
A team whose expected sum is under 0.75 of its budget is printed LOW COVERAGE: the card expects most of that volume to go to players it
does not price (a quarterback outside the history window, say) - a PASS on the budget, a hole in the card, named.
  python3 checks/check_expected_budget.py --self-test                                     synthetic slate: PASS unchanged, FAIL named once injected
Exit 0 when the readout ran (a FAIL is a measured property of the card, printed, not a refusal); exit 1 when an input is missing, a card
player has no P(plays), or an injected fault was not named."""
import sys, os, json, numpy as np, pandas as pd

BUDGETS = {"targets": (("F5 targets",), "F2 team targets", "Rule 8"), "attempts": (("Q1 attempts",), "F2 team attempts", "Rule 8"),
           "carries": (("F5 carries", "QB carries"), "F2 team carries", "Rule 3 Section 2")}
INJECTED_FACTOR = 1.1
LOW_COVERAGE = 0.75

def sums(keys, terms, draws, team_of, p_of, member_terms):
    """team -> (card sum of member draws, expected sum: each member's draws x his P(plays))."""
    card, expected = {}, {}
    for key, term, row in zip(keys, terms, draws):
        team = team_of.get(key)
        if team is None or term not in member_terms: continue
        card[team] = card.get(team, 0.0) + row; expected[team] = expected.get(team, 0.0) + p_of[key] * row
    return card, expected

def readout(card_sums, expected_sums, team_draws):
    """Per team: card sum, expected sum, team expected, both ratios, share of draws the card sum exceeds the team draw, verdict on the expected sum."""
    rows = []
    for team, parent in team_draws.items():
        t = float(parent.mean())
        if team not in card_sums: rows.append(dict(team=team, card=np.nan, expected=np.nan, team_expected=t, card_ratio=np.nan, ratio=np.nan, over_share=np.nan, verdict="INSUFFICIENT_EVIDENCE: no card rows")); continue
        c, e = float(card_sums[team].mean()), float(expected_sums[team].mean()); excess = e - t
        rows.append(dict(team=team, card=c, expected=e, team_expected=t, card_ratio=c / t if t > 0 else np.nan, ratio=e / t if t > 0 else np.nan,
                         over_share=float((card_sums[team] > parent).mean()), verdict="PASS" if excess <= 0 else f"FAIL: excess {excess:.2f}",
                         low_coverage=(excess <= 0 and t > 0 and e / t < LOW_COVERAGE)))
    return sorted(rows, key=lambda r: -(r["ratio"] if np.isfinite(r["ratio"]) else -1))

def load(frozen_path, card_path, team_path, inject=None, factor=INJECTED_FACTOR):
    for p in (frozen_path, card_path, team_path):
        if not os.path.exists(p): print(f"REFUSED: input missing: {p}"); sys.exit(1)
    z = np.load(frozen_path, allow_pickle=False); keys, terms, draws = z["keys"].astype(str), z["terms"].astype(str), z["draws"].astype(float)
    card = pd.read_csv(card_path, usecols=["player_id", "team", "probability_plays"]); card["player_id"] = card.player_id.astype(str); card["team"] = card.team.astype(str)
    team_of = dict(zip(card.player_id, card.team))
    p_rows = card.dropna(subset=["probability_plays"]).drop_duplicates("player_id"); p_of = dict(zip(p_rows.player_id, p_rows.probability_plays.astype(float)))
    members = sorted({k for k, t in zip(keys, terms) if k in team_of and any(t in mt for mt, _, _ in BUDGETS.values())})
    without = [k for k in members if k not in p_of]
    if without: print(f"REFUSED: {len(without)} card players on a volume line have no P(plays): {without[:10]}"); sys.exit(1)
    t = np.load(team_path, allow_pickle=False); tk, tt, td = t["keys"].astype(str), t["terms"].astype(str), t["draws"].astype(float)
    team_draws = {name: {k: row for k, term, row in zip(tk, tt, td) if term == parent} for name, (_, parent, _) in BUDGETS.items()}
    if inject:
        if inject == "WORST":
            c0, e0 = sums(keys, terms, draws, team_of, p_of, BUDGETS["targets"][0]); passing = [r for r in readout(c0, e0, team_draws["targets"]) if r["verdict"] == "PASS"]
            if not passing: print("REFUSED: --inject WORST: no passing team on targets to inject into"); sys.exit(1)
            inject = passing[0]["team"]; print(f"INJECTED FAULT TARGET: {inject}, the passing team with the least headroom on targets (expected/team {passing[0]['ratio']:.3f})")
        team_members = {k for k, t in team_of.items() if t == inject}; mask = np.array([(t == "F5 targets") and (k in team_members) for k, t in zip(keys, terms)])
        if not mask.any(): print(f"REFUSED: --inject {inject}: no receiver-target rows for that team on the card"); sys.exit(1)
        draws = draws.copy(); draws[mask] *= factor; print(f"INJECTED FAULT: {inject} receiver targets x {factor} on {int(mask.sum())} rows")
    both = {name: sums(keys, terms, draws, team_of, p_of, member_terms) for name, (member_terms, _, _) in BUDGETS.items()}
    return {n: both[n][0] for n in both}, {n: both[n][1] for n in both}, team_draws, inject

def print_readout(card_sums, expected_sums, team_draws, inject=None):
    named, summary = False, {}
    for name, (member_terms, parent, article) in BUDGETS.items():
        rows = readout(card_sums[name], expected_sums[name], team_draws[name]); fails = [r for r in rows if r["verdict"].startswith("FAIL")]; absent = [r["team"] for r in rows if r["verdict"].startswith("INSUFFICIENT")]
        ratios = np.array([r["ratio"] for r in rows if np.isfinite(r["ratio"])]); card_ratios = np.array([r["card_ratio"] for r in rows if np.isfinite(r["card_ratio"])]); overs = np.array([r["over_share"] for r in rows if np.isfinite(r["over_share"])])
        print(f"\nEXPECTED BUDGET - {name} ({' + '.join(member_terms)} vs {parent}; {article}): {len(rows) - len(fails) - len(absent)} of {len(rows)} teams PASS"
              f"{'; no card rows: ' + ', '.join(absent) if absent else ''}; expected / team {ratios.mean():.3f} (min {ratios.min():.3f}, max {ratios.max():.3f}); "
              f"card sum / team if everyone plays {card_ratios.mean():.3f}; draws where the card sum exceeds the team draw {overs.mean():.1%}")
        low = [r["team"] for r in rows if r.get("low_coverage")]
        for r in rows: print(f"   {r['team']:<4} card {r['card']:7.2f}  expected {r['expected']:7.2f}  team {r['team_expected']:7.2f}  expected/team {r['ratio']:.3f}  card/team {r['card_ratio']:.3f}  draws over {r['over_share']:5.1%}  Expected budget: {r['verdict']}"
                            + (f"  | LOW COVERAGE: the card expects {1 - r['ratio']:.0%} of this budget to go to players it does not price" if r.get("low_coverage") else ""))
        if low: print(f"   LOW COVERAGE (expected under {LOW_COVERAGE:.0%} of the budget): {', '.join(low)}")
        summary[name] = dict(teams=len(rows), fail=[r["team"] for r in fails], no_card_rows=absent, low_coverage=low, ratio_mean=float(ratios.mean()), card_ratio_mean=float(card_ratios.mean()), over_share_mean=float(overs.mean()))
        if inject and name == "targets": named = any(r["team"] == inject and r["verdict"].startswith("FAIL: excess") for r in rows)
    return summary, named

def self_test():
    rng = np.random.default_rng(20261108); teams = [f"T{i:02d}" for i in range(31)]
    team_draws = {name: {t: rng.poisson(lam, 2000).astype(float) for t in teams} for name, lam in (("targets", 34), ("attempts", 36), ("carries", 26))}
    card_sums = {name: {t: team_draws[name][t] * 1.05 for t in teams} for name in team_draws}   # lines priced given they play add to 1.05 of the team
    expected_sums = {name: {t: card_sums[name][t] * 0.90 for t in teams} for name in team_draws}   # at P(plays) 0.90 the expected sum is 0.945 of the team
    s, _ = print_readout(card_sums, expected_sums, team_draws); assert all(not s[n]["fail"] for n in s), f"self-test: a 0.945 expected slate must PASS every team, got {[(n, s[n]['fail']) for n in s]}"
    card_sums["targets"]["T07"] = card_sums["targets"]["T07"] * INJECTED_FACTOR; expected_sums["targets"]["T07"] = expected_sums["targets"]["T07"] * INJECTED_FACTOR
    rows = readout(card_sums["targets"], expected_sums["targets"], team_draws["targets"]); hit = [r for r in rows if r["team"] == "T07"][0]
    assert hit["verdict"].startswith("FAIL: excess"), f"self-test: injected x{INJECTED_FACTOR} on T07 targets must be named FAIL with its excess, got {hit['verdict']}"
    others = [r["team"] for r in rows if r["verdict"].startswith("FAIL") and r["team"] != "T07"]; assert not others, f"self-test: only T07 may FAIL after the injected fault, got {others}"
    print(f"\nSELF-TEST PASS: 0.945 expected slate PASS on 31 x 3 (card sum 1.05 if everyone plays); injected x{INJECTED_FACTOR} named: T07 targets {hit['verdict']} (expected/team {hit['ratio']:.3f})")

if __name__ == "__main__":
    if "--self-test" in sys.argv: self_test(); sys.exit(0)
    inject, factor = None, INJECTED_FACTOR
    if "--inject" in sys.argv:
        i = sys.argv.index("--inject"); inject = sys.argv[i + 1]; factor = float(sys.argv[i + 2]) if len(sys.argv) > i + 2 else INJECTED_FACTOR
        args = sys.argv[1:i] + sys.argv[i + 3 if len(sys.argv) > i + 2 else i + 2:]
    else: args = sys.argv[1:]
    args = [a for a in args if not a.startswith("--")]
    if len(args) < 3: print(__doc__); sys.exit(2)
    card_sums, expected_sums, team_draws, inject = load(args[0], args[1], args[2], inject, factor)
    summary, named = print_readout(card_sums, expected_sums, team_draws, inject)
    print("\nSUMMARY " + json.dumps(summary))
    if inject: print(f"INJECTED FAULT {'NAMED' if named else 'NOT NAMED'}: {inject} targets x {factor}"); sys.exit(0 if named else 1)
    sys.exit(0)
