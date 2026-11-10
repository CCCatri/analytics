"""check_possessions.py - rules-level clause 2, possessions: the R1 read of RUBRIC run_log line 322, saved as a script. A record read, not product.
Possession = the offensive plays (pass, run, kneel, spike, punt, field goal; Tries excluded, 11-3-1) one team runs, broken at a kickoff, a punt,
a change of offensive team, halftime or overtime start, an interception, a fumble first recovered by the other side (a fumble kept ends nothing, 3-35-3),
or a field-goal attempt the receivers muff and the kickers recover, which gives the kickers a new series as a muffed punt does (9-3-2 Item 1, 7-3-1d; the muff read from the play text).
Back-to-back possessions (one team twice in a row) are classed by the rule that hands the ball back:
  A11 halftime / overtime start; A8 the other side scored; A10 two changes in one down (incl. a touchback award);
  A9 the kicking team recovered; A7 a safety before the receiving side's own snap, the scored-on side read from the score change (11-5-1(b), 11-5-2).
Reads record.events (the columns it carries) joined one-to-one on (game_id, play_id) to record.raw_frame + record.typed for the rest:
order_sequence, season_type, return_touchdown, touchback, own_kickoff_recovery, fumble_recovery_1_team, fumble_recovery_2_team, desc (the muff on a field goal).
Injected faults run first, row by row; any FAIL, or any count off run_log line 322, stops the run before the file is written.
Writes out/possessions_possessions.csv and out/possessions_classes.csv, stamped on line 1 with this file's sha and rules-level.md's sha.
out/possessions_classes.csv (N7): possessions and back-to-back possessions per season and class, each class with the articles rules-level.md cites on its line
(A7-A11; halftime and overtime start are A11), read verbatim, and in a book column rules-level.md's Book line, read verbatim, on every row that carries articles;
the run stops if the classes do not sum back to the counts.
the rules-module stage: the snap kinds and the possession rules after a score and a safety (A8, A7) are read from rules.py (rules-module.md snap kinds, the next-possession rule)."""
import hashlib, os, re, sys
from collections import Counter
import numpy as np, pandas as pd
import record, policy
from rules import SNAP_KINDS, next_possession

SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]
RULES, RSHA = "acceptance-criteria/rules-level.md", "8fae1db04c0b"
OUT = "out/possessions_possessions.csv"
OUT_CLASSES = "out/possessions_classes.csv"
EXTRA = {"game_id": ("str", False), "play_id": ("int", False), "order_sequence": ("int", False), "season_type": ("str", False), "return_touchdown": ("int", True),
         "touchback": ("int", True), "own_kickoff_recovery": ("int", True), "fumble_recovery_1_team": ("str", True), "fumble_recovery_2_team": ("str", True), "desc": ("str", True)}
FROM_EVENTS = ["game_id", "play_id", "posteam", "home_team", "away_team", "total_home_score", "total_away_score", "qtr", "play_type", "two_point_attempt",
               "interception", "td_team", "safety"]
# run_log line 322, written before this script existed, corrected 2026-11-09 by one A9 possession: 2025_10_NO_CAR, a field goal muffed by the receivers and kept by the kickers
RUN_LOG_322 = {"possessions": 36349, "games": 1676, "gap": {0: 714, 1: 799, 2: 154, 3: 8, 4: 1}, "kinds": {"other": 645, "halftime": 824, "overtime start": 38},
              "classes": {"A8 other side scored": 428, "A9 kicking team recovered": 203, "A10 two changes in one down": 11, "A7 safety before the receiving side's own snap": 3}}


def articles(path):
    """{'A7': '11-3-4, 11-4-6; ...', ...}: every parenthesized citation on each A-line of rules-level.md, verbatim, in order; '' when the line cites none."""
    out = {}
    for l in open(path).read().split("\n"):
        m = re.match(r"(A\d+) ", l)
        if m:
            out[m.group(1)] = "; ".join(c for c in re.findall(r"\(((?:[^()]|\([^()]*\))*)\)", l) if re.search(r"\d+-\d+", c))
    return out


def book_line(path):
    """rules-level.md's Book line, verbatim: the rule book the articles are read from; the run stops unless exactly one line starts with 'Book'."""
    b = [l.rstrip() for l in open(path).read().split("\n") if l.startswith("Book")]
    if len(b) != 1:
        sys.exit(f"STOPPED: {path} has {len(b)} lines starting 'Book' (must be 1)")
    return b[0]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def load(season):
    ev = record.events(season)[FROM_EVENTS]
    ex = record.typed(record.raw_frame(policy.PBP_FILE.format(season=season), list(EXTRA), f"check_possessions {season}"), EXTRA, f"check_possessions {season}")
    d = ev.merge(ex, on=["game_id", "play_id"], how="inner", validate="one_to_one")
    if len(d) != len(ev) or len(d) != len(ex):
        raise record.DataGap(f"check_possessions {season}: events {len(ev)} and raw extras {len(ex)} do not join one-to-one ({len(d)})")
    for c in d.columns:
        if str(d[c].dtype) == "Int64":
            d[c] = d[c].to_numpy(dtype=float, na_value=np.nan)
    print(f"check_possessions {season}: rows {len(d)} joined one-to-one (events {len(ev)}, raw extras {len(ex)})")
    return d


def fg_muff_kept(pt, team, r1, desc):
    """A field-goal attempt the receivers muffed and the kickers recovered: the kickers' ball and a new series (9-3-2 Item 1, 7-3-1d), as for a punt."""
    return pt == "field_goal" and isinstance(r1, str) and r1 == team and isinstance(desc, str) and "MUFF" in desc.upper()


def possessions(D):
    rows = []
    for g, d in D.groupby("game_id", sort=False):
        cur = None; pid = 0; brk = True; lastq = None
        for seq, team, q, pt, tp, itc, r1, ds in zip(d["order_sequence"], d["posteam"], d["qtr"], d["play_type"], d["two_point_attempt"], d["interception"], d["fumble_recovery_1_team"], d["desc"]):
            if lastq is not None and ((lastq in (1, 2) and q in (3, 4)) or (q == 5 and lastq != 5)):
                brk = True                                   # halftime, overtime start (4-1-2, 16-1)
            lastq = q
            if pt == "kickoff":
                brk = True; continue                          # a kickoff starts a new series (6-1)
            if pt not in SNAP_KINDS or tp == 1 or not isinstance(team, str):
                continue
            if brk or team != cur:
                pid += 1; cur = team; brk = False; rows.append([g, pid, team, q, seq, seq])
            else:
                rows[-1][5] = seq
            if pt == "punt" or itc == 1 or (isinstance(r1, str) and r1 != team) or fg_muff_kept(pt, team, r1, ds):
                brk = True                                    # punt, interception, fumble first recovered by the other side, field goal muffed by the receivers and kept by the kickers
    P = pd.DataFrame(rows, columns=["game_id", "pid", "team", "q", "s0", "s1"])
    for c in ("team", "q", "s1"):
        P["prev_" + c] = P.groupby("game_id")[c].shift()
    return P


def kind(pq, q):
    return "halftime" if pq in (1, 2) and q in (3, 4) else ("overtime start" if q == 5 and pq != 5 else "other")


def scored_on(full, seq):
    i = full.index[full["order_sequence"] == seq][0]; prev = full.loc[:i - 1, ["total_home_score", "total_away_score"]].dropna()
    h0, a0 = (prev.iloc[-1] if len(prev) else (0, 0)); h1, a1 = full.loc[i, "total_home_score"], full.loc[i, "total_away_score"]
    if h1 - h0 == 2 and a1 == a0: return full.loc[i, "away_team"]
    if a1 - a0 == 2 and h1 == h0: return full.loc[i, "home_team"]
    return None


def classes(r, full):
    w = full[(full["order_sequence"] >= r["prev_s1"]) & (full["order_sequence"] < r["s0"])].sort_values("order_sequence"); t = r["team"]; found = set()
    sc = [s for s in w["td_team"].dropna() if s != t] + (["the other side"] if (w["return_touchdown"] == 1).any() else [])
    if any(next_possession("try_or_field_goal", scorer=s, scored_on=t)[0] == t for s in sc): found.add("A8 other side scored")   # the rules module the next-possession rule
    mine = w["posteam"] == t; r1 = w["fumble_recovery_1_team"]; r2 = w["fumble_recovery_2_team"]
    lost = mine & ((w["interception"] == 1) | (r1.notna() & (r1 != t)))
    back = mine & ((r1.notna() & (r1 != t) & (r2 == t)) | ((w["interception"] == 1) & (r1 == t)))
    if back.any() or (lost & (w["touchback"] == 1)).any(): found.add("A10 two changes in one down")
    kick = w["play_type"].isin(["kickoff", "punt"])
    fgm = pd.Series([fg_muff_kept(a, b, c, e) for a, b, c, e in zip(w["play_type"], w["posteam"], r1, w["desc"])], index=w.index, dtype=bool)
    if (w["own_kickoff_recovery"] == 1).any() or (kick & (r1 == t)).any() or fgm.any(): found.add("A9 kicking team recovered")
    for sseq in w.loc[w["safety"] == 1, "order_sequence"]:
        so = scored_on(full.sort_values("order_sequence").reset_index(drop=True), sseq)
        if so is None or next_possession("safety", scorer=(t if so != t else None), scored_on=so)[0] != t: continue   # the rules module the next-possession rule
        ran = w[(w["order_sequence"] < sseq) & (w["posteam"] == so) & w["play_type"].isin(["pass", "run"]) & (w["two_point_attempt"] != 1)]
        if ran.empty: found.add("A7 safety before the receiving side's own snap")
    return found


def word(f):
    return "UNEXPLAINED" if not f else (next(iter(f)) if len(f) == 1 else "MULTIPLE: " + " + ".join(sorted(f)))


def counts(P, G):
    b2b = P[P["team"] == P["prev_team"]].copy()
    b2b["kind"] = [kind(pq, q) for pq, q in zip(b2b["prev_q"], b2b["q"])]
    oth = b2b[b2b["kind"] == "other"].copy()
    oth["word"] = [word(classes(r, G[r["game_id"]])) for _, r in oth.iterrows()]
    gaps = P.groupby(["game_id", "team"]).size().unstack().apply(lambda v: int(v.dropna().max() - v.dropna().min()), axis=1)
    return b2b, oth, {"possessions": len(P), "games": int(P["game_id"].nunique()), "gap": dict(sorted(Counter(gaps).items())),
                      "kinds": dict(Counter(b2b["kind"])), "classes": dict(Counter(oth["word"]))}


def main():
    if sha(RULES) != RSHA:
        sys.exit(f"STOPPED: {RULES} is {sha(RULES)}, not {RSHA} (the version R1 ran against); the definition and the text cannot be matched")
    seasons = [s for s in policy.SEASONS if s != policy.HOLD]
    tag = f"check_possessions.py {SELF} | {RULES} {RSHA} | record read (rules-level clause 2), not product"
    print(f"{tag} | seasons {seasons} (hold-out {policy.HOLD} held_out)")
    D = pd.concat([load(s) for s in seasons], ignore_index=True).sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
    P = possessions(D)
    G = {g: d.sort_values("order_sequence").reset_index(drop=True) for g, d in D.groupby("game_id")}
    b2b, oth, C = counts(P, G)

    print("\n=== INJECTED FAULTS, row by row (any FAIL stops the run) ===")
    res = []

    def injected_fault(name, cond):
        res.append(bool(cond)); print(f"  INJECTED FAULT {name} -> {'PASS' if cond else 'FAIL'}")

    def cl(r, frame=None):
        return classes(r, frame if frame is not None else G[r["game_id"]])

    def after(g, t, seq): return b2b[(b2b["game_id"] == g) & (b2b["team"] == t) & (b2b["prev_s1"] == seq)]
    def around(g, t, seq): return b2b[(b2b["game_id"] == g) & (b2b["team"] == t) & (b2b["prev_s1"] <= seq) & (b2b["s0"] > seq)]
    def sel(g, t, q): x = b2b[(b2b["game_id"] == g) & (b2b["team"] == t) & (b2b["kind"] == "other")]; return x[x["q"] == q]
    def show(x): return [word(cl(r)) for _, r in x.iterrows()]
    x = sel("2019_01_BUF_NYJ", "BUF", 1); injected_fault(f"A8 BUF-NYJ BUF q1 ({len(x)}): {show(x)}", len(x) > 0 and all(word(cl(r)) == "A8 other side scored" for _, r in x.iterrows()))
    F = G["2019_01_BUF_NYJ"].copy(); F["td_team"] = F["td_team"].where(F["td_team"].isna(), "BUF"); F["return_touchdown"] = 0.0
    injected_fault("A8 negative: BUF-NYJ touchdown relabeled to BUF", len(x) > 0 and "A8 other side scored" not in cl(x.iloc[0], F))
    x = after("2019_12_OAK_NYJ", "LV", 2660); injected_fault(f"A8 OAK-NYJ after 2660 ({len(x)}): {show(x)}", len(x) == 1 and word(cl(x.iloc[0])) == "A8 other side scored")
    for g, t, q in (("2019_01_SF_TB", "TB", 4), ("2019_04_TB_LA", "TB", 4)):
        x = sel(g, t, q); injected_fault(f"A8 {g} {t} q{q} ({len(x)}): {show(x)}", len(x) > 0 and all(word(cl(r)) == "A8 other side scored" for _, r in x.iterrows()))
    x = after("2019_12_OAK_NYJ", "LV", 2994); injected_fault(f"A10 OAK-NYJ after 2994 ({len(x)}): {show(x)}", len(x) == 1 and word(cl(x.iloc[0])) == "A10 two changes in one down")
    F = G["2019_12_OAK_NYJ"].copy(); F["fumble_recovery_2_team"] = F["fumble_recovery_2_team"].where(F["fumble_recovery_2_team"].isna(), "NYJ")
    injected_fault("A10 negative: OAK-NYJ second recovery relabeled to NYJ", len(x) == 1 and "A10 two changes in one down" not in cl(x.iloc[0], F))
    x = after("2024_15_CIN_TEN", "TEN", 3191); injected_fault(f"A10 award CIN-TEN after 3191 ({len(x)}): {show(x)}", len(x) == 1 and word(cl(x.iloc[0])) == "A10 two changes in one down")
    F = G["2024_15_CIN_TEN"].copy(); F["touchback"] = 0.0
    injected_fault("A10 award negative: CIN-TEN with the touchback column cleared", len(x) == 1 and "A10 two changes in one down" not in cl(x.iloc[0], F))
    for g, t, seq in (("2019_09_IND_PIT", "PIT", 2734), ("2025_08_CLE_NE", "CLE", 3742), ("2025_18_KC_LV", "KC", 3537)):
        x = around(g, t, seq); injected_fault(f"A9 exact {g} {t} around {seq} ({len(x)}): {show(x)}", len(x) == 1 and word(cl(x.iloc[0])) == "A9 kicking team recovered")
    x = around("2025_08_CLE_NE", "CLE", 3742); F = G["2025_08_CLE_NE"].copy(); F["own_kickoff_recovery"] = 0.0; F["fumble_recovery_1_team"] = None
    injected_fault("A9 negative: CLE-NE with the recovery cleared", len(x) == 1 and "A9 kicking team recovered" not in cl(x.iloc[0], F))
    x = around("2025_10_NO_CAR", "CAR", 2504); injected_fault(f"A9 field goal muffed by the receivers, kept by the kickers: NO-CAR CAR around 2504 ({len(x)}): {show(x)}", len(x) == 1 and word(cl(x.iloc[0])) == "A9 kicking team recovered")
    F = D[D["game_id"] == "2025_10_NO_CAR"].copy(); F.loc[F["order_sequence"] == 2504, "desc"] = "field goal is BLOCKED, recovered by CAR at NO 30"
    injected_fault(f"A9 field goal negative: no muff in the play text (the kickers recover their own block), so 2504 ends no possession ({int((possessions(F)['s1'] == 2504).sum())})", int((possessions(F)["s1"] == 2504).sum()) == 0)
    for g, t, seq in (("2021_17_ATL_BUF", "ATL", 203), ("2024_01_DEN_SEA", "DEN", 1354), ("2025_06_DEN_NYJ", "NYJ", 2604)):
        x = after(g, t, seq); injected_fault(f"A7 {g} {t} after {seq} ({len(x)}): {show(x)}", len(x) == 1 and word(cl(x.iloc[0])) == "A7 safety before the receiving side's own snap")
    x = after("2024_01_DEN_SEA", "DEN", 1354)
    row = {c: None for c in G["2024_01_DEN_SEA"].columns}; row.update({"game_id": "2024_01_DEN_SEA", "order_sequence": 1370.0, "posteam": "SEA", "qtr": 2.0, "play_type": "run", "two_point_attempt": 0.0})
    F = pd.concat([G["2024_01_DEN_SEA"], pd.DataFrame([row])], ignore_index=True).sort_values("order_sequence").reset_index(drop=True)
    F[["total_home_score", "total_away_score"]] = F[["total_home_score", "total_away_score"]].astype(float).ffill()
    injected_fault("A7 negative: DEN-SEA with a SEA run inserted at seq 1370", len(x) == 1 and "A7 safety before the receiving side's own snap" not in cl(x.iloc[0], F))
    h = b2b[b2b["kind"] == "halftime"]; r = h.iloc[0] if len(h) else None
    injected_fault(f"A11 halftime: {len(h)} found", r is not None and kind(r["prev_q"], r["q"]) == "halftime")
    injected_fault("A11 halftime negative: the later possession moved to q2", r is not None and kind(r["prev_q"], 2) != "halftime")
    o = b2b[b2b["kind"] == "overtime start"]; r = o.iloc[0] if len(o) else None
    injected_fault(f"A11 overtime start: {len(o)} found, first {r['game_id'] if r is not None else None}", r is not None and kind(r["prev_q"], r["q"]) == "overtime start")
    injected_fault("A11 overtime negative: the later possession moved to q4", r is not None and kind(r["prev_q"], 4) != "overtime start")
    oak = P[P["game_id"] == "2019_12_OAK_NYJ"]
    injected_fault(f"no break at OAK-NYJ seq 3062 (ending there {int((oak['s1'] == 3062).sum())}, containing it {int(((oak['s0'] < 3062) & (oak['s1'] > 3062)).sum())})",
          int((oak["s1"] == 3062).sum()) == 0 and int(((oak["s0"] < 3062) & (oak["s1"] > 3062)).sum()) == 1)
    injected_fault("A3: no SF back-to-back in SF-TB q4", sel("2019_01_SF_TB", "SF", 4).empty)
    injected_fault("no CAR back-to-back in TB-CAR q1", sel("2019_02_TB_CAR", "CAR", 1).empty)
    npass = sum(res)
    if npass != len(res) or len(res) != 26:
        print(f"\nPOSSESSIONS SUMMARY injected faults {npass}/{len(res)} FAILED | no count read, no file written"); sys.exit(1)

    print("\n=== COUNTS against run_log line 322 (written before this script existed), corrected 2026-11-09 by one A9 possession (NO-CAR, a field goal muffed and kept) ===")
    agree = {k: C[k] == RUN_LOG_322[k] for k in RUN_LOG_322}
    for k in RUN_LOG_322:
        print(f"  {k}: {C[k]} | run_log 322 {RUN_LOG_322[k]} -> {'AGREE' if agree[k] else 'DISAGREE'}")
    left = oth[oth["word"].str.startswith(("UNEXPLAINED", "MULTIPLE"))]
    print(f"  unexplained or multiple back-to-back: {len(left)}")
    for _, r in left.iterrows(): print(f"    {r['word']}: {r['game_id']} {r['team']} q{int(r['q'])} seq {r['prev_s1']} -> {r['s0']}")
    if not all(agree.values()) or len(left):
        print(f"\nPOSSESSIONS SUMMARY injected faults {npass}/{len(res)} | counts DISAGREE with run_log line 322 or unexplained {len(left)}: code and record disagree | no file written"); sys.exit(1)

    print("\n=== POSTSEASON: the same counts with and without the 76 postseason games ===")
    post = set(D.loc[D["season_type"] != "REG", "game_id"])
    Pr = P[~P["game_id"].isin(post)].reset_index(drop=True)
    for c in ("team", "q", "s1"): Pr["prev_" + c] = Pr.groupby("game_id")[c].shift()
    _, othr, Cr = counts(Pr, G)
    print(f"  postseason games {len(post)}")
    print(f"  with them:    possessions {C['possessions']} games {C['games']} back-to-back {C['kinds']} classes {C['classes']}")
    print(f"  without them: possessions {Cr['possessions']} games {Cr['games']} back-to-back {Cr['kinds']} classes {Cr['classes']}")
    print(f"  per game: {C['possessions'] / C['games']:.3f} with, {Cr['possessions'] / Cr['games']:.3f} without, postseason alone {(C['possessions'] - Cr['possessions']) / max(len(post), 1):.3f}")

    W = P.merge(b2b[["game_id", "pid", "kind"]], on=["game_id", "pid"], how="left").merge(oth[["game_id", "pid", "word"]], on=["game_id", "pid"], how="left")
    W["season_type"] = np.where(W["game_id"].isin(post), "POST", "REG")
    with open(OUT, "w") as f:
        f.write(f"# {tag}\n"); W[["game_id", "season_type", "pid", "team", "q", "s0", "s1", "kind", "word"]].rename(columns={"kind": "back_to_back", "word": "rule_class"}).to_csv(f, index=False)
    print(f"\nwritten, stamped on line 1: {OUT} rows {len(W)} sha {sha(OUT)}")
    ART, BOOK = articles(RULES), book_line(RULES); crow = []
    W2 = W.assign(season=W["game_id"].astype(str).str[:4].astype(int))
    for (s, st), g in W2.groupby(["season", "season_type"]):
        crow.append((s, st, "possessions", "possessions", "", "", len(g)))
        b = g[g["kind"].notna()]
        for (k, w), n in Counter(zip(b["kind"], b["word"].fillna(""))).items():
            a = "A11" if k in ("halftime", "overtime start") else w.split(" ")[0]
            crow.append((s, st, "back_to_back", w if w else k, ART.get(a, ""), BOOK if ART.get(a, "") else "", n))
        crow.append((s, st, "unexplained", "unexplained or multiple", "", "", int(left["game_id"].isin(g["game_id"]).sum())))
    CC = pd.DataFrame(crow, columns=["season", "season_type", "check", "rule_class", "articles", "book", "count"])
    bb = CC[CC["check"] == "back_to_back"]
    ok_ = int(CC.loc[CC["check"] == "possessions", "count"].sum()) == C["possessions"] and int(bb["count"].sum()) == sum(C["kinds"].values()) \
          and all(int(bb.loc[bb["rule_class"] == k, "count"].sum()) == v for k, v in list(C["classes"].items()) + [(k, v) for k, v in C["kinds"].items() if k != "other"])
    print(f"classes table: rows {len(CC)} | sums back to the counts: {ok_} | articles per A-line {ART} | book {BOOK}")
    if not ok_:
        print(f"\nPOSSESSIONS SUMMARY injected faults {npass}/{len(res)} | the class split does not sum to the counts | no classes file written"); sys.exit(1)
    with open(OUT_CLASSES, "w") as f:
        f.write(f"# {tag}\n"); CC.to_csv(f, index=False)
    print(f"written, stamped on line 1: {OUT_CLASSES} rows {len(CC)} sha {sha(OUT_CLASSES)}")
    print(f"\nPOSSESSIONS SUMMARY injected faults {npass}/{len(res)} | possessions {C['possessions']} games {C['games']} = run_log 322 as corrected | unexplained 0 | without the {len(post)} postseason games: possessions {Cr['possessions']} games {Cr['games']} back-to-back {Cr['kinds']} | {OUT} {sha(OUT)}")


if __name__ == "__main__":
    main()
