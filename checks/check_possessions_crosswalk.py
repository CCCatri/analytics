"""Our possessions against nflfastR's drives (fixed_drive): an outside judge for product/check_possessions.py, six seasons. Reads only; writes nothing.
Two definitions, one equation. nflfastR starts a drive whenever the ball changes hands; a possession here is a drive with at least one snap
(pass, run, kneel, spike, punt, field goal), two-point tries excluded (11-3-1). So every nflfastR drive holds exactly one of our possessions, or is named:
  no snap      a drive with no snap (end of half with no play, a kickoff returned for a touchdown, a muffed kickoff, ...), counted by nflfastR's fixed_drive_result
  try only     a drive whose only snaps are two-point tries
  two offenses one drive number over snaps by both teams: nflfastR did not start a new drive (its numbering, not football); each listed and pinned in TWO_OFFENSES
and every one of our possessions sits inside exactly one drive. Anything else is UNEXPLAINED, listed by game and play, and the run exits 1.
Equation printed: drives = possessions - (possessions beyond the first in a two-offense drive) + no-snap drives + try-only drives.
Self-test first, on football faults injected in our possessions: one dropped, one split in two, and Carolina's two possessions around its muffed field goal
(2025_10_NO_CAR 2504) merged back as the old rule had them; each must be UNEXPLAINED, else the check is blind and exits 1.
Endings (acceptance-criteria/possession-ends.md, clause 3): every possession's (stop, score on the play), read by rules.possession_ends, names nflfastR's
fixed_drive_result under rules.nflfastr_result, except the possessions in the pinned two-offense drives and the cases in ENDING_NAMED (each with its play
and reason); four known-right cases are pinned in KNOWN_RIGHT; the first pick-six in the record with its points taken off the scoreboard must be UNEXPLAINED.
python3 checks/check_possessions_crosswalk.py [--injected-fault]  (the flag also injects a fault in the real run, which must then exit 1)"""
import os, sys
from collections import Counter
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "product"))
import record, policy
from rules import SNAP_KINDS, possession_ends, nflfastr_result
POSS = os.path.join(ROOT, "out", "possessions_possessions.csv")
COLS = ["game_id", "order_sequence", "fixed_drive", "fixed_drive_result", "play_type", "posteam", "two_point_attempt", "interception", "fumble_lost", "touchdown",
        "safety", "down", "ydstogo", "yards_gained", "home_team", "away_team", "total_home_score", "total_away_score", "td_team"]
# nflfastR numbering errors read play by play on 2026-11-09: a team change with a no-play row between (a lightning suspension; a timeout) kept the old drive number
TWO_OFFENSES = {("2019_02_TB_CAR", "2"): "a turnover on downs, then a lightning suspension", ("2023_12_PIT_CIN", "8"): "a punt, then a timeout"}
# endings nflfastR names otherwise, read play by play on 2026-11-09 (game, last snap): reason
ENDING_NAMED = {("2019_09_CHI_PHI", 4093.0): "a kneel at the end of the game (:23 left); nflfastR names the drive 'Turnover'; no change of possession follows it",
                ("2019_13_MIN_SEA", 4172.0): "a kneel at the end of the game (:14 left); nflfastR names the drive 'Turnover'; no change of possession follows it",
                ("2024_01_DEN_SEA", 1354.0): "an interception downed in the intercepting side's end zone, a safety for the passing team (11-5-1(b)); nflfastR names the turnover, not the score",
                ("2025_06_DEN_NYJ", 2604.0): "a punt, then a safety by the receivers before their own snap (11-5-1(b)); nflfastR names the punt, not the score"}
# known-right endings, one of each kind the old one-word reading hid (game, last snap): (stop, score)
KNOWN_RIGHT = {("2019_03_NO_SEA", 218.0): ("punt", "other side 6"), ("2020_13_NYG_SEA", 1914.0): ("punt", "other side 2"),
               ("2019_03_NYJ_NE", 3000.0): ("punt", "offense 6"), ("2025_05_TEN_ARI", 4224.0): ("interception", "offense 6")}


def load():
    P = pd.read_csv(POSS, skiprows=1)
    seasons = sorted({int(g[:4]) for g in P["game_id"]})
    R = []
    for y in seasons:
        r = record.raw_frame(policy.PBP_FILE.format(season=y), COLS, f"crosswalk {y}")
        r["seq"] = pd.to_numeric(r["order_sequence"], errors="coerce"); R.append(r)
    return P, pd.concat(R, ignore_index=True)


def judge(P, R):
    """(counts, unexplained rows): every drive and every possession classed."""
    R = R.copy(); R["drive"] = list(zip(R["game_id"], R["fixed_drive"]))
    snaps = R[R["play_type"].isin(SNAP_KINDS) & (R["posteam"] != "")].sort_values("seq")
    real = snaps[snaps["two_point_attempt"] != "1"].copy(); real["seq"] = real["seq"].astype(float)   # the two merge keys must share one type
    S = P.sort_values("s0")[["game_id", "pid", "team", "s0", "s1"]].copy(); S[["s0", "s1"]] = S[["s0", "s1"]].astype(float); S["sid"] = list(zip(S["game_id"], S["pid"]))
    m = pd.merge_asof(real, S, left_on="seq", right_on="s0", by="game_id", direction="backward")
    inside = m["seq"] <= m["s1"]
    bad = [("a snap in no possession of ours", g, d, int(s)) for g, d, s in zip(m.loc[~inside, "game_id"], m.loc[~inside, "fixed_drive"], m.loc[~inside, "seq"])]
    m = m[inside]
    s2d = m.groupby("sid")["drive"].unique(); d2s = m.groupby("drive")["sid"].unique()
    for sid, ds in s2d.items():
        if len(ds) > 1: bad.append(("one of our possessions over two nflfastR drives", sid[0], [d[1] for d in ds], int(S.loc[S["sid"] == sid, "s0"].iloc[0])))
    empty = set(S["sid"]) - set(s2d.index)
    for sid in sorted(empty): bad.append(("a possession of ours with no snap in the play-by-play record", sid[0], None, int(S.loc[S["sid"] == sid, "s0"].iloc[0])))
    team = dict(zip(S["sid"], S["team"])); two, extra = [], 0
    for d, ss in d2s.items():
        if len(ss) == 1: continue
        if d in TWO_OFFENSES and len(ss) == 2 and len({team[s] for s in ss}) == 2: two.append(d); extra += 1
        else: bad.append(("an nflfastR drive over several possessions of ours, not a pinned two-offense drive", d[0], d[1], int(m.loc[m["drive"] == d, "seq"].min())))
    try_d = set(snaps.loc[snaps["two_point_attempt"] == "1", "drive"]) - set(d2s.index)
    res = R.groupby("drive")["fixed_drive_result"].first()
    zero = [d for d in res.index if d not in d2s.index]
    kinds = Counter("try only" if d in try_d else f"no snap: {res[d]}" for d in zero)
    n_d, n_p = len(res), len(S)
    C = {"drives": n_d, "possessions": n_p, "matched one to one": int((d2s.map(len) == 1).sum()), "two offenses": len(two), "zero-possession drives": len(zero),
         "equation holds": n_d == n_p - extra + len(zero), "kinds": dict(kinds.most_common()), "pinned two-offense drives found": sorted(two)}
    if sorted(two) != sorted(TWO_OFFENSES): bad.append(("a pinned two-offense drive not found as pinned", None, sorted(set(TWO_OFFENSES) - set(two)), 0))
    return C, bad


def ends_judge(P, R):
    """(counts, unexplained rows) for the endings: each possession's (stop, score) against nflfastR's drive result."""
    X = possession_ends(P, R)
    k = list(zip(R["game_id"], R["seq"])); FD = dict(zip(k, R["fixed_drive"])); RES = dict(zip(zip(R["game_id"], R["fixed_drive"]), R["fixed_drive_result"]))
    X["drive"] = [FD[(g, s)] for g, s in zip(X["game_id"], X["s1"])]; X["theirs"] = [RES[(g, d)] for g, d in zip(X["game_id"], X["drive"])]
    X["expect"] = [nflfastr_result(a, b) for a, b in zip(X["stop"], X["score"])]
    pinned = [(g, d) in TWO_OFFENSES for g, d in zip(X["game_id"], X["drive"])]; named = [(g, s) in ENDING_NAMED for g, s in zip(X["game_id"], X["s1"])]
    bad = []
    for g, s, t, a, b, e, th, pn, nm in zip(X["game_id"], X["s1"], X["team"], X["stop"], X["score"], X["expect"], X["theirs"], pinned, named):
        if pn: continue
        if nm and e == th: bad.append(("a named ending that now agrees (the name is stale)", g, t, int(s)))
        elif not nm and e != th: bad.append((f"ending ({a}, {b}) names {e!r}, nflfastR {th!r}", g, t, int(s)))
    have = dict(zip(zip(X["game_id"], X["s1"]), zip(X["stop"], X["score"])))
    games = set(X["game_id"])
    for key, want in KNOWN_RIGHT.items():
        if key[0] in games and have.get(key) != want: bad.append((f"known-right ending reads {have.get(key)}, not {want}", key[0], None, int(key[1])))
    C = {"possessions with an ending": len(X), "agree": int((X["expect"] == X["theirs"]).sum()), "in pinned two-offense drives": int(sum(pinned)), "named": int(sum(named)),
         "endings": dict(sorted(Counter(zip(X["stop"], X["score"])).items(), key=lambda kv: -kv[1]))}
    return C, bad


def ends_plant(P, R):
    """The first pick-six in the record with its points taken off the scoreboard, in its own game: (name, possessions, rows as recorded, rows injected)."""
    n = lambda c: pd.to_numeric(R[c], errors="coerce") == 1
    c = R[n("interception") & n("touchdown") & (R["td_team"] != R["posteam"])]
    if not len(c): return None
    g, s6 = c["game_id"].iloc[0], c["seq"].iloc[0]
    Pg, Rg = P[P["game_id"] == g], R[R["game_id"] == g]
    prev = Rg[Rg["seq"] < s6].sort_values("seq").iloc[-1]
    Rf = Rg.copy(); m = Rf["seq"] >= s6; Rf.loc[m, "total_home_score"] = prev["total_home_score"]; Rf.loc[m, "total_away_score"] = prev["total_away_score"]
    return f"the pick-six at {g} seq {s6:.0f} with its points taken off the scoreboard", Pg, Rg, Rf


def injected_copies(P):
    """Football faults in our possessions, each a copy: (name, possessions)."""
    P = P.astype({"s0": float, "s1": float})
    c = P[P["back_to_back"].isna() & (P["s1"] > P["s0"])]; one = c.iloc[len(c) // 2]
    drop = P.drop(index=one.name)
    split = P.copy(); r = split.loc[one.name]; mid = r["s0"] + (r["s1"] - r["s0"]) / 2
    if r["s1"] > r["s0"]:
        split.loc[one.name, "s1"] = mid; split = pd.concat([split, pd.DataFrame([{**r.to_dict(), "pid": 10_000, "s0": mid + 0.5}])], ignore_index=True)
    car = P[(P["game_id"] == "2025_10_NO_CAR") & (P["team"] == "CAR") & ((P["s1"] == 2504) | (P["s0"] > 2504))].sort_values("s0").head(2)
    merged = P.copy()
    if len(car) == 2:
        merged.loc[car.index[0], "s1"] = car["s1"].iloc[1]; merged = merged.drop(index=car.index[1])
    return [(f"one possession dropped ({one['game_id']} {one['team']} {one['s0']:.0f})", drop),
            (f"one possession split in two ({one['game_id']} {one['team']} at {mid:.0f})", split),
            ("Carolina's two possessions around its muffed field goal merged (the old rule)", merged)]


def main():
    P, R = load()
    blind = []
    for name, Pf in injected_copies(P):
        _, b = judge(Pf, R); print(f"  self-test, injected: {name} -> {len(b)} unexplained {'(seen)' if b else '(UNSEEN)'}")
        if not b: blind.append(name)
    if blind:
        print("CROSSWALK self-test: FAIL, the check is blind to:", "; ".join(blind)); sys.exit(1)
    ep = ends_plant(P, R)
    if ep is None: blind.append("no pick-six found for the endings self-test")
    else:
        name, Pg, Rg, Rf = ep; _, b0 = ends_judge(Pg, Rg); _, b1 = ends_judge(Pg, Rf)
        print(f"  self-test, endings: {Pg['game_id'].iloc[0]} as recorded -> {len(b0)} unexplained | injected: {name} -> {len(b1)} unexplained {'(seen)' if b1 else '(UNSEEN)'}")
        if b0 or not b1: blind.append("the endings check on " + name)
    if blind:
        print("CROSSWALK self-test: FAIL, the check is blind to:", "; ".join(blind)); sys.exit(1)
    print("CROSSWALK self-test: PASS (every injected fault is seen)")
    if "--injected-fault" in sys.argv:
        name, P = injected_copies(P)[2]; print(f"INJECTED FAULT in the real run: {name}; this run must end FAIL")
    C, bad = judge(P, R)
    for k, v in C.items(): print(f"  {k}: {v}")
    for d in TWO_OFFENSES: print(f"  two offenses, nflfastR numbering: {d[0]} drive {d[1]}: {TWO_OFFENSES[d]}")
    for why, g, d, s in bad[:20]: print(f"  UNEXPLAINED: {why}: {g} drive {d} seq {s}")
    C2, bad2 = ends_judge(P, R)
    for k, v in C2.items(): print(f"  endings {k}: {v}")
    for key, why in ENDING_NAMED.items(): print(f"  ending named: {key[0]} seq {key[1]:.0f}: {why}")
    for why, g, d, s in bad2[:20]: print(f"  UNEXPLAINED ending: {why}: {g} {d} seq {s}")
    bad = bad + bad2
    ok = not bad and C["equation holds"]
    print(f"CROSSWALK: {'PASS' if ok else 'FAIL'} | endings agree {C2['agree']} named {C2['named']} | drives {C['drives']} = possessions {C['possessions']} - two-offense {C['two offenses']} + zero-possession {C['zero-possession drives']} | unexplained {len(bad)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
