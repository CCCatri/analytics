"""The attempt and carry reconciliation (acceptance-criteria/engine-to-kit-handoff.md section 1): for every regular-season team-week of 2019-2021 and 2023-2025,
the engine-side count of attempts and carries (record.events under the section-1 rule, ball-handlers QB/RB/WR/TE) must equal the kit's (slate-kit facts).
Prints the unequal count with every ball-handler and under the universe rule, the snaps outside the universe by position, and any kit-only team-week;
exit 0 only when every team-week is equal. --injected-fault adds one attempt to the first team-week's kit count, and the run must end NOT RECONCILED (exit 1).
Reads only; writes nothing."""
import sys, os, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "product")); sys.path.insert(0, os.path.join(ROOT, "slate-kit"))
import record, facts
FIX = {"OAK": "LV", "SD": "LAC", "LA": "LAR", "STL": "LAR"}; SEASONS = [2019, 2020, 2021, 2023, 2024, 2025]; UNIVERSE = {"QB", "RB", "WR", "TE"}
kit = facts.load(); kit = kit[kit.season.isin(SEASONS)]
print("kit positions in facts rows:", kit.position.value_counts(dropna=False).to_dict())
kit = kit.groupby(["season", "week", "team"])[["attempts", "carries"]].sum().reset_index().merge(facts.team_game()[["season", "week", "team"]].drop_duplicates(), on=["season", "week", "team"], how="inner")
rows = []
for s in SEASONS:
    pos = pd.read_csv(f"data/raw/stats_{s}.csv.gz", usecols=["player_id", "position"]).drop_duplicates("player_id").set_index("player_id").position
    ev = record.events(s); ev = ev[ev["posteam"].notna()]
    flags = pd.read_csv(f"data/raw/pbp_{s}.csv.gz", usecols=["game_id", "play_id", "pass_attempt", "rush_attempt"], low_memory=False)
    ev = ev.merge(flags, on=["game_id", "play_id"], how="left", validate="one_to_one")
    ev = ev[~ev["two_point_attempt"].fillna(0).eq(1)].assign(season=s, team=ev["posteam"].map(lambda t: FIX.get(t, t)))
    pen_pass = ev["kind"].eq("penalty") & ev["pass_attempt"].fillna(0).eq(1) & ~ev["sack"].fillna(0).eq(1); pen_rush = ev["kind"].eq("penalty") & ev["rush_attempt"].fillna(0).eq(1)
    att = ev[ev["kind"].isin(["pass", "spike"]) | pen_pass].assign(who=lambda d: d["passer_player_id"].map(pos).fillna("NONE"), what="attempts")
    car = ev[ev["kind"].isin(["run", "scramble", "kneel"]) | pen_rush].assign(who=lambda d: d["rusher_player_id"].map(pos).fillna("NONE"), what="carries")
    rows.append(pd.concat([att, car])[["season", "week", "team", "what", "who"]])
e = pd.concat(rows); e["in_universe"] = e["who"].isin(UNIVERSE)
tot = e.groupby(["season", "week", "team", "what"]).size().unstack(fill_value=0).reset_index()
uni = e[e.in_universe].groupby(["season", "week", "team", "what"]).size().unstack(fill_value=0).reset_index()
m = kit.merge(tot, on=["season", "week", "team"], suffixes=("", "_eng_all")).merge(uni, on=["season", "week", "team"], suffixes=("", "_eng_universe"))
if "--injected-fault" in sys.argv:
    m.loc[m.index[0], "attempts"] += 1; print(f"INJECTED FAULT: one attempt added to {m.loc[m.index[0], ['season', 'week', 'team']].tolist()}'s kit count; this run must end NOT RECONCILED")
bad_all = (m.attempts != m.attempts_eng_all) | (m.carries != m.carries_eng_all); bad_uni = (m.attempts != m.attempts_eng_universe) | (m.carries != m.carries_eng_universe)
print(f"team-games {len(m)} | unequal with every ball-handler {int(bad_all.sum())} | unequal with QB/RB/WR/TE only {int(bad_uni.sum())}")
print("snaps outside the universe, by position:", e[~e.in_universe].groupby(["what", "who"]).size().to_dict())
print(m[bad_uni][["season", "week", "team", "attempts", "attempts_eng_universe", "carries", "carries_eng_universe"]].head(20).to_string(index=False))
missing = kit.merge(tot[["season", "week", "team"]], on=["season", "week", "team"], how="left", indicator=True); print("kit-only team-games:"); print(missing[missing._merge == "left_only"][["season", "week", "team", "attempts", "carries"]].to_string(index=False))
print("RECONCILED under the universe definition" if bad_uni.sum() == 0 else "NOT RECONCILED under the universe definition either")
sys.exit(0 if bad_uni.sum() == 0 else 1)
