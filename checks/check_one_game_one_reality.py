"""One game, one reality (acceptance-criteria/one-game-one-reality.md): a simulated game holds one starting quarterback per team.
At most one quarterback can throw more than half of his team's passes in one game, so two quarterback lines on one team that each claim more than half of the
team's attempts (attempts if he plays, against the team-attempts draw) cannot both be the same game. Such lines must carry different world labels (the card's
`world` column: who starts), and nothing may add them up as one game. A card with no `world` column is one world.
python3 checks/check_one_game_one_reality.py FROZEN.npz CARD.csv TEAM.npz     the verdict
python3 checks/check_one_game_one_reality.py --self-test                       a starter and a full-game backup in one world must be NOT MET; in two worlds, or a
                                                                              backup in relief (a few attempts), must pass
Exit 0 when no team has two full-game quarterback lines in one world; exit 1 when one does (NOT MET: the card is not one game), an input is missing, or the
self-test fails. Reads only; writes nothing."""
import sys, os, numpy as np, pandas as pd
ONE_WORLD = "one world (the card carries no world label)"


def full_game_pairs(lines, team_att):
    """lines: (team, world, player, attempts if he plays); team_att: {team: mean team attempts}. Returns (team, world, [(player, attempts)], team attempts)
    for every team and world where two or more lines each exceed half the team's attempts."""
    out = []
    df = pd.DataFrame(lines, columns=["team", "world", "player", "att"])
    for (t, w), d in df.groupby(["team", "world"]):
        if t not in team_att: continue
        full = d[d["att"] > 0.5 * team_att[t]].sort_values("att", ascending=False)
        if len(full) >= 2: out.append((t, w, [(p, round(a, 2)) for p, a in zip(full["player"], full["att"])], round(team_att[t], 2)))
    return out


def self_test():
    T = {"AAA": 34.0, "BBB": 34.0, "CCC": 34.0}
    same = full_game_pairs([("AAA", ONE_WORLD, "starter", 30.0), ("AAA", ONE_WORLD, "backup", 22.0)], T)
    split = full_game_pairs([("BBB", "starter starts", "starter", 30.0), ("BBB", "backup starts", "backup", 22.0)], T)
    relief = full_game_pairs([("CCC", ONE_WORLD, "starter", 30.0), ("CCC", ONE_WORLD, "backup", 4.0)], T)
    ok = len(same) == 1 and not split and not relief
    print(f"self-test: starter + full-game backup in one world -> {'NOT MET' if same else 'met'} (want NOT MET) | in two worlds -> {'NOT MET' if split else 'met'} (want met) | "
          f"backup in relief -> {'NOT MET' if relief else 'met'} (want met) | {'PASS' if ok else 'FAIL, the check is blind'}")
    return ok


def main(frozen, card_path, team_path):
    for p in (frozen, card_path, team_path):
        if not os.path.exists(p): print(f"REFUSED: input missing: {p}"); sys.exit(1)
    z = np.load(frozen, allow_pickle=False); keys, terms, draws = z["keys"].astype(str), z["terms"].astype(str), z["draws"].astype(float)
    card = pd.read_csv(card_path); card["player_id"] = card["player_id"].astype(str)
    has_world = "world" in card.columns
    info = card.drop_duplicates("player_id").set_index("player_id")
    t = np.load(team_path, allow_pickle=False)
    team_att = {k: float(row.mean()) for k, term, row in zip(t["keys"].astype(str), t["terms"].astype(str), t["draws"].astype(float)) if term == "F2 team attempts"}
    lines = [(str(info.loc[k, "team"]), str(info.loc[k, "world"]) if has_world else ONE_WORLD, str(info.loc[k, "name"]), float(d.mean()))
             for k, term, d in zip(keys, terms, draws) if term == "Q1 attempts" and k in info.index]
    per_team = pd.Series([l[0] for l in lines]).value_counts()
    print(f"card: {len(lines)} quarterback attempt lines on {len(per_team)} teams | teams with two or more quarterback lines {int((per_team >= 2).sum())} | world label on the card: {has_world}")
    pairs = full_game_pairs(lines, team_att)
    for team, world, players, ta in pairs:
        print(f"  NOT ONE GAME: {team} ({world}): {' and '.join(f'{p} {a}' for p, a in players)} attempts if he plays, each more than half of the team's {ta}")
    print(f"ONE GAME, ONE REALITY: {'MET' if not pairs else 'NOT MET'} | teams with two full-game quarterbacks in one world {len(pairs)}")
    sys.exit(0 if not pairs else 1)


if __name__ == "__main__":
    if "--self-test" in sys.argv: sys.exit(0 if self_test() else 1)
    if len(sys.argv) != 4: print(__doc__); sys.exit(1)
    main(*sys.argv[1:4])
