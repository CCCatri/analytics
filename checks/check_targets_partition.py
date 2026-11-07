"""Do the kit's receiver slices add up to the quarterback total they were drawn from, game by game?

Football: every forward pass is one target, a throwaway or a spike (Rule 8, Forward Pass). So in any one game a team's
receivers cannot be targeted more times than its quarterbacks throw. The check sums each team's `F5 targets` draws and
compares them, draw by draw, with the team's summed `Q1 attempts` draws. FAIL while any game breaks the rule.

Reads the local preflight artifacts (out/preflight_2025_w16/frozen_draws_2025_w16.npz and card_2025_w16.csv), or two
paths given on the command line. `--self-test` runs the check on a conserved synthetic slate (must PASS) and on a planted
independent slate (must FAIL) before any PASS on real data counts."""
import sys, numpy as np, pandas as pd

def impossible_cells(qb, tg):
    """qb, tg: teams x draws. Returns (count of cells with targets > attempts, cells, teams over on average)."""
    gap = tg - qb
    return int((gap > 0).sum()), int(gap.size), int(((tg.mean(1) - qb.mean(1)) > 0).sum())

def load(npz_path, card_path):
    z = np.load(npz_path, allow_pickle=False)
    keys, terms, draws = z["keys"].astype(str), z["terms"].astype(str), z["draws"]
    card = pd.read_csv(card_path)
    team_of = dict(zip(card.player_id.astype(str), card.team.astype(str)))
    teams = sorted(set(team_of.values())); index = {t: i for i, t in enumerate(teams)}
    qb = np.zeros((len(teams), draws.shape[1])); tg = np.zeros_like(qb)
    for key, term, row in zip(keys, terms, draws):
        team = team_of.get(key)
        if team is None: continue
        if term == "Q1 attempts": qb[index[team]] += row
        if term == "F5 targets": tg[index[team]] += row
    has = (qb.sum(1) > 0) & (tg.sum(1) > 0)
    return qb[has], tg[has], [t for t, h in zip(teams, has) if h]

def self_test():
    rng = np.random.default_rng(20261107)
    attempts = rng.integers(20, 45, size=(31, 2000)).astype(float)
    conserved = attempts - rng.integers(0, 4, size=attempts.shape)          # every target is one of the attempts; the rest thrown away
    over, cells, teams_over = impossible_cells(attempts, conserved)
    assert over == 0 and teams_over == 0, f"self-test: conserved slate must PASS, got {over} of {cells}"
    planted = np.stack([rng.binomial(attempts.astype(int), 0.95) + rng.binomial(attempts.astype(int), 0.10) for _ in range(1)])[0]  # drawn apart from the whole
    over, cells, _ = impossible_cells(attempts, planted)
    assert over > 0, "self-test: planted independent slate must FAIL"
    print(f"SELF-TEST PASS: conserved slate 0 impossible games; planted independent slate {over} of {cells}")

if __name__ == "__main__":
    if "--self-test" in sys.argv: self_test(); sys.exit(0)
    npz, card = (sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else ("out/preflight_2025_w16/frozen_draws_2025_w16.npz", "out/preflight_2025_w16/card_2025_w16.csv")
    qb, tg, teams = load(npz, card)
    over, cells, teams_over = impossible_cells(qb, tg)
    share = (tg - qb > 0).mean(1)
    worst = ", ".join(f"{teams[i]} {share[i]:.0%}" for i in np.argsort(-share)[:3])
    status = "PASS" if over == 0 else "FAIL"
    print(f"TARGETS PARTITION {status}: {over} of {cells} simulated games have receivers targeted more than the quarterbacks threw ({over/cells:.1%}); {teams_over} of {len(teams)} teams over on average; worst {worst}")
    sys.exit(0 if over == 0 else 1)
