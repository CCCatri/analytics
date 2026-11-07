"""Injected violations P1-P4 (engine-legality.md section 5) on a changed copy of the engine made at run time: one function or one season-rule value replaced,
named in the output; engine.py untouched. Plays one draw of 2024 w15 and writes out/handoff/games_2024_w15_{FAULT}.csv.gz for check_generated.py, which
runs in its own process with the unchanged rules. python3 checks/inject_generated.py P1|P2|P3|P4"""
import sys, os, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "product"))
import engine, rules, transition
fault = sys.argv[1]; season, week = 2024, 15
if fault == "P1":
    orig = transition.next_possession
    def injected_fault(ending, scorer=None, scored_on=None, team=None, other=None):
        return (scorer, "INJECTED FAULT P1: after a field goal the scoring team receives") if ending == "try_or_field_goal" else orig(ending, scorer, scored_on, team, other)
    transition.next_possession = injected_fault; print("INJECTED FAULT P1: transition.next_possession replaced - after a Try or field goal the scoring team receives")
elif fault == "P3":
    rules.CLOCK_EVENTS["incomplete 4-4f"] = "RUN"; print("INJECTED FAULT P3: rules.CLOCK_EVENTS['incomplete 4-4f'] = RUN - the game clock keeps running after an incomplete pass (engine side only)")
elif fault == "P4":
    E0 = engine.engine_load
    def loaded(d=None):
        E = E0(d if d is not None else engine.ENGINE_DIR); E["season_rules"][season]["touchback"]["value"] = 25; print(f"INJECTED FAULT P4: season_rules[{season}]['touchback'] = 25 (the book says 30)"); return E
    engine.engine_load = loaded
elif fault == "P2":
    orig_nd = rules.next_down
    def injected_nd(dn, outcome):
        nd, why = orig_nd(dn, outcome)
        return (4, "INJECTED FAULT P2: a fifth down, numbered 4") if (dn == 4 and nd is not None and nd > 4) else (nd, why)
    rules.next_down = injected_nd; transition.next_down = injected_nd; engine.next_down = injected_nd
    print("INJECTED FAULT P2: next_down on a 4th down that would be a 5th returns 4 again - the offense snaps a fifth time (3-8-2 defeated)")
else: raise SystemExit(f"unknown fault {fault}")
games = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv")); wk = games[(games.season == season) & (games.week == week) & (games.game_type == "REG")]
out, skipped = engine.play_alone(engine.ENGINE_DIR, set(wk.game_id))
if skipped.get(season): raise SystemExit(f"injected {fault}: games not played {skipped[season]} - NOT DETECTED (a crash or a missing game is not a detection)")
rows = out[season].assign(draw_id=0); path = os.path.join(ROOT, "out/handoff", f"games_{season}_w{week}_{fault}.csv.gz"); rows.to_csv(path, index=False)
print(f"injected {fault}: {rows.game_id.nunique()} games, {len(rows)} rows -> {path}")
