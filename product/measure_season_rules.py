"""measure_season_rules.py - R7 v2 inside the rules-module stage (rules-module.md section 2, R7 v2): each season's rule values read from the record before the engine uses them. A record read, not product.
For every season but 2022 (held_out: its values come from rule text only, never its record), each prediction prints before its number, and every measure prints
what it counted (games or kicks) beside its value; a measure with nothing to count reads 'no games' or 'no kicks' and no prediction is judged there (v2 a):
  M1 the most common drive-start spot after a kickoff touchback (the next snap's own yard line), counted over touchback kickoffs with a next snap;
  M2 the longest regular-season overtime in game seconds (the quarter clock at the period's first row), counted over regular-season overtime games;
  M3, M4 regular-season and postseason overtime games ended by a touchdown on the first possession (every overtime snap by one team, a touchdown in overtime),
     counted over overtime games with a snap;
  M5 (v2 b) every onside kick (a kickoff whose play text says 'onside'), by quarter (1-3, or 4th and overtime) and by the kicking team's score (ahead, tied,
     behind; the kicking team is the one not on offense on the kickoff row, the score the last one recorded before the kick), each with its play text.
     A kick whose kicking team cannot be read (no offense on its row) is counted 'unread'.
Writes out/season_rules.csv, stamped on line 1 with this file's sha and rules-module.md's sha: season, measure, value, counted, prediction, prediction_held,
rule_change_page; prediction_held is True, False or 'not judged'. rules.season_rules() reads it. Every season's rule-change page reads UNCHECKED until read."""
import hashlib, os, sys
from collections import Counter
import pandas as pd
import policy
from rules import SNAP_KINDS
import check_possessions, check_clock, check_downs

SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]
TARGETS = "acceptance-criteria/rules-module.md"
OUT = "out/season_rules.csv"
SEALED = 2022
PERIODS = ("1-3", "4th and overtime")
SCORES = ("ahead", "tied", "behind")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def predict(m, s):
    """The predictions of rules-module.md section 2 (R7 v2), as written: (text, test). M1-M4 test the value; M5 tests the season's onside kicks."""
    if m == "M1": v = 25 if s <= 2023 else (30 if s == 2024 else 35); return f"the {v}", lambda x: x == v
    if m == "M2": return "600 (a 10-minute period)", lambda x: x == 600
    if m == "M3": return ("some (above 0)", lambda x: x > 0) if s <= 2024 else ("0", lambda x: x == 0)
    if m == "M4": return ("some (above 0)", lambda x: x > 0) if s <= 2021 else ("0", lambda x: x == 0)
    if m == "M5":
        if s <= 2023: return ("a surprise onside kick could come at any time, from any team: kicks before the 4th quarter and kicks from teams not behind",
                              lambda K: any(k["period"] == "1-3" for k in K) and any(k["score"] in ("ahead", "tied") for k in K))
        if s == 2024: return ("every onside kick in the 4th quarter or overtime, by a team behind",
                              lambda K: all(k["period"] == "4th and overtime" and k["score"] == "behind" for k in K))
        return ("every onside kick by a team behind, in any quarter", lambda K: all(k["score"] == "behind" for k in K))


def breaking(s, K):
    """The kicks that break the season's M5 prediction, one by one (2024, 2025); through 2023 the prediction is about the season, so no single kick breaks it."""
    if s <= 2023: return []
    if s == 2024: return [k for k in K if not (k["period"] == "4th and overtime" and k["score"] == "behind")]
    return [k for k in K if k["score"] != "behind"]


def season_frame(s):
    a = check_possessions.load(s)
    b = check_downs.load(s)[["game_id", "play_id", "yardline_100", "desc", "touchdown"]]
    d = a.merge(b, on=["game_id", "play_id"], how="inner", validate="one_to_one")
    if len(d) != len(a):
        sys.exit(f"STOPPED: measure_season_rules {s}: check_possessions rows {len(a)} and check_downs rows {len(b)} do not join one-to-one")
    q, _, _ = check_clock.load(s)
    return d.sort_values(["game_id", "order_sequence"]).reset_index(drop=True), q


def measures(d, q):
    """{measure: (value, counted, note)}; value 'no games' or 'no kicks' when counted is 0."""
    out = {}
    starts = []
    for gid, g in d.groupby("game_id", sort=False):
        g = g.reset_index(drop=True)
        idx = g.index[(g["play_type"] == "kickoff") & (g["touchback"] == 1)]
        for k in idx:
            nx = next((x for x in range(k + 1, len(g)) if g.loc[x, "play_type"] in SNAP_KINDS and g.loc[x, "two_point_attempt"] != 1), None)
            if nx is not None and not pd.isna(g.loc[nx, "yardline_100"]): starts.append(int(100 - g.loc[nx, "yardline_100"]))
    c = Counter(starts)
    out["M1"] = (c.most_common(1)[0][0] if c else "no kicks", f"{len(starts)} touchback kickoffs with a next snap", f"top spots {c.most_common(3)}")
    ot = q[(q["qtr"] == 5) & (q["season_type"] == "REG")]
    per = ot.groupby("game_id")["quarter_seconds_remaining"].max()
    out["M2"] = (int(per.max()) if len(per) else "no games", f"{len(per)} regular-season overtime games", f"their period lengths {dict(Counter(per.dropna().astype(int)))}")
    for m, st, word in (("M3", "REG", "regular-season"), ("M4", "POST", "postseason")):
        n = games = 0
        for gid, g in d[(d["qtr"] == 5) & (d["season_type"] == st)].groupby("game_id", sort=False):
            sn = g[g["play_type"].isin(SNAP_KINDS) & (g["two_point_attempt"] != 1)]
            if not len(sn): continue
            games += 1
            if sn["posteam"].nunique() == 1 and (g["touchdown"] == 1).any(): n += 1
        out[m] = (n if games else "no games", f"{games} {word} overtime games with a snap", "")
    return out


def onside(d):
    """Every onside kick: game, play, quarter, period, kicking team, the score before the kick, ahead/tied/behind, play text."""
    K = []
    ko = d[(d["play_type"] == "kickoff") & d["desc"].fillna("").str.contains("onside", case=False)]
    for i, r in ko.iterrows():
        prev = d.loc[:i - 1]; prev = prev[prev["game_id"] == r["game_id"]][["total_home_score", "total_away_score"]].dropna()
        h, a = (int(prev.iloc[-1]["total_home_score"]), int(prev.iloc[-1]["total_away_score"])) if len(prev) else (0, 0)
        if pd.isna(r["posteam"]):
            kick, ks, rs, sc = None, None, None, "unread"
        else:
            kick = r["away_team"] if r["posteam"] == r["home_team"] else r["home_team"]
            ks, rs = (h, a) if kick == r["home_team"] else (a, h)
            sc = "ahead" if ks > rs else ("tied" if ks == rs else "behind")
        K.append(dict(game_id=r["game_id"], play_id=r["play_id"], qtr=int(r["qtr"]), period="1-3" if r["qtr"] <= 3 else "4th and overtime",
                      kick=kick, ks=ks, rs=rs, score=sc, desc=str(r["desc"])))
    return K


def grid(K):
    c = Counter((k["period"], k["score"]) for k in K)
    unread = sum(1 for k in K if k["score"] == "unread")
    return f"kicks {len(K)} | " + " | ".join(f"{p}: " + " ".join(f"{s_} {c[(p, s_)]}" for s_ in SCORES) for p in PERIODS) + f" | unread {unread}"


def main():
    seasons = [s for s in policy.SEASONS if s != policy.HOLD]
    tag = f"measure_season_rules.py {SELF} | {TARGETS} {sha(TARGETS)} | record read (the rules-module stage R7 v2), not product"
    print(f"{tag} | seasons {seasons}; {SEALED} held_out: rule text only, UNKNOWN until read")
    rows, BR = [], {}
    for s in seasons:
        print(f"\n=== {s}: predictions, before the numbers ===")
        for m in ("M1", "M2", "M3", "M4", "M5"): print(f"  {m} predicted: {predict(m, s)[0]}")
        d, q = season_frame(s); M = measures(d, q); K = onside(d)
        for m in ("M1", "M2", "M3", "M4"):
            v, counted, note = M[m]
            held = "not judged" if isinstance(v, str) else predict(m, s)[1](v)
            word = "nothing to count: no prediction judged" if held == "not judged" else ("holds" if held else "BREAKS")
            print(f"  {m} measured: {v} (counted: {counted}) -> {word}{' | ' + note if note else ''}")
            rows.append((s, m, v, counted, predict(m, s)[0], held))
        if K:
            held5 = predict("M5", s)[1](K)
            if s >= 2024 and any(k["score"] == "unread" for k in K): held5 = False
        else:
            held5 = "not judged"
        v5 = grid(K) if K else "no kicks"
        word = "nothing to count: no prediction judged" if held5 == "not judged" else ("holds" if held5 else "BREAKS")
        print(f"  M5 measured: {v5} (counted: {len(K)} onside kicks) -> {word}")
        for k in K:
            print(f"    {k['game_id']} play {k['play_id']} q{k['qtr']} | kicking {k['kick']} {k['ks']}-{k['rs']} {k['score']} | {k['desc']}")
        BR[s] = breaking(s, K)
        if s <= 2023 and held5 is False:
            miss = [w for w, f in (("no kick before the 4th quarter", not any(k["period"] == "1-3" for k in K)),
                                    ("no kick from a team not behind", not any(k["score"] in ("ahead", "tied") for k in K))) if f]
            print(f"  M5 breaks for the season: {miss}")
        rows.append((s, "M5", v5, f"{len(K)} onside kicks", predict("M5", s)[0], held5))
    print("\n=== the kicks that break the M5 prediction, on their plays (2024, 2025) ===")
    for s in seasons:
        if s <= 2023: continue
        print(f"  {s}: {len(BR[s])} kicks")
        for k in BR[s]:
            print(f"    {k['game_id']} play {k['play_id']} q{k['qtr']} ({k['period']}) | kicking {k['kick']} {k['ks']}-{k['rs']} {k['score']} | {k['desc']}")
    rows += [(SEALED, m, "UNKNOWN", "not read", "rule text only (held_out season)", "") for m in ("M1", "M2", "M3", "M4", "M5")]
    R = pd.DataFrame(sorted(rows, key=lambda z: (z[0], z[1])), columns=["season", "measure", "value", "counted", "prediction", "prediction_held"])
    R["rule_change_page"] = "UNCHECKED"
    with open(OUT, "w") as f:
        f.write(f"# {tag}\n"); R.to_csv(f, index=False)
    held = R[R["season"] != SEALED]["prediction_held"].astype(str).value_counts().to_dict()
    print(f"\nwritten, stamped on line 1: {OUT} rows {len(R)} sha {sha(OUT)} | predictions {held} | {SEALED} UNKNOWN")


if __name__ == "__main__":
    main()
