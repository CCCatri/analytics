"""Do the kit's slices fit inside the team budget they were drawn from, game by game?

Football: every forward pass is one target, a throwaway or a spike (Rule 8, Forward Pass), so in one game a team's receivers
cannot be targeted more times than the team throws, and its quarterbacks cannot throw more than the team throws.
Three verdicts, declared in advance for each (team, draw) cell:
  SUPPORTED  the slice total fits its parent draw;  REFUTED  the slice total exceeds it;  INSUFFICIENT_EVIDENCE  no parent draw for that team.
Usage:
  python3 checks/check_targets_partition.py FROZEN.npz CARD.csv [TEAM.npz]
With TEAM.npz the parent is the team's own `F2 team attempts` draw (the budget). Without it the parent is the summed
quarterback draws, which are themselves slices; the printout says which scope it used. `--self-test` must print PASS
(conserved slate 0 refuted; injected independent slate refuted > 0) before any real PASS counts. Exit 1 while any cell is refuted."""
import sys, numpy as np, pandas as pd

def verdicts(parent, child):
    """parent, child: teams x draws; rows with no parent (all nan) are INSUFFICIENT_EVIDENCE. Returns counts (supported, refuted, INSUFFICIENT_EVIDENCE)."""
    INSUFFICIENT_EVIDENCE = np.isnan(parent).all(1)
    gap = (child - parent)[~INSUFFICIENT_EVIDENCE]
    return int((gap <= 0).sum()), int((gap > 0).sum()), int(INSUFFICIENT_EVIDENCE.sum() * parent.shape[1])

def load(frozen_path, card_path, team_path=None):
    z = np.load(frozen_path, allow_pickle=False)
    keys, terms, draws = z["keys"].astype(str), z["terms"].astype(str), z["draws"]
    card = pd.read_csv(card_path)
    team_of = dict(zip(card.player_id.astype(str), card.team.astype(str)))
    teams = sorted(set(team_of.values())); index = {t: i for i, t in enumerate(teams)}
    n = draws.shape[1]
    qb, tg = np.zeros((len(teams), n)), np.zeros((len(teams), n))
    for key, term, row in zip(keys, terms, draws):
        team = team_of.get(key)
        if team is None: continue
        if term == "Q1 attempts": qb[index[team]] += row
        if term == "F5 targets": tg[index[team]] += row
    parent = np.full((len(teams), n), np.nan); scope = "summed quarterback draws (slices, not the budget)"
    if team_path:
        t = np.load(team_path, allow_pickle=False)
        for key, term, row in zip(t["keys"].astype(str), t["terms"].astype(str), t["draws"]):
            if term == "F2 team attempts" and key in index: parent[index[key]] = row
        scope = "team's own F2 team attempts draw (the budget)"
    else: parent = np.where(qb > 0, qb, np.nan)
    has = (tg.sum(1) > 0)
    return parent[has], qb[has], tg[has], [t for t, h in zip(teams, has) if h], scope

def self_test():
    rng = np.random.default_rng(20261107)
    budget = rng.integers(20, 45, size=(31, 2000)).astype(float)
    conserved = budget - rng.integers(0, 4, size=budget.shape)
    s, r, u = verdicts(budget, conserved); assert r == 0 and u == 0, f"self-test: conserved slate must have 0 refuted, got {r}"
    injected = rng.binomial(budget.astype(int), 0.95) + rng.binomial(budget.astype(int), 0.10)
    s, injected_refuted, u = verdicts(budget, injected.astype(float)); assert injected_refuted > 0, "self-test: injected independent slate must be refuted"
    missing = budget.copy(); missing[0] = np.nan
    s, r, u = verdicts(missing, conserved); assert u == 2000, f"self-test: a team without a parent must be INSUFFICIENT_EVIDENCE for all its draws, got {u}"
    print(f"SELF-TEST PASS: conserved 0 refuted; injected {injected_refuted} refuted; missing parent -> {u} INSUFFICIENT_EVIDENCE")

if __name__ == "__main__":
    if "--self-test" in sys.argv: self_test(); sys.exit(0)
    if len(sys.argv) < 3: print(__doc__); sys.exit(2)
    frozen, card, team = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else None)
    parent, qb, tg, teams, scope = load(frozen, card, team)
    s, r, u = verdicts(parent, tg)
    cells = s + r
    print(f"PARENT SCOPE: {scope}")
    print(f"RECEIVER TARGETS vs PARENT: supported {s}, refuted {r} ({r/max(cells,1):.1%} of {cells} games), INSUFFICIENT_EVIDENCE {u}")
    if team:
        s2, r2, u2 = verdicts(parent, qb); print(f"QUARTERBACK ATTEMPTS vs PARENT: supported {s2}, refuted {r2} ({r2/max(s2+r2,1):.1%}), INSUFFICIENT_EVIDENCE {u2}")
        over = ((tg.mean(1) - np.nanmean(parent, 1)) > 0).sum(); print(f"teams whose average receiver targets exceed the average team budget: {int(over)} of {len(teams)}")
    share = np.nan_to_num((tg - parent > 0).mean(1)); worst = ", ".join(f"{teams[i]} {share[i]:.0%}" for i in np.argsort(-share)[:3])
    print(f"TARGETS PARTITION {'PASS' if r == 0 else 'FAIL'}: worst {worst}")
    sys.exit(0 if r == 0 else 1)
