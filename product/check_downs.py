"""check_downs.py - rules-level clause 3, downs ("four downs to gain ten"), to downs-check.md v19 (e6fb7875b651). A record read, not product.
Reads record.events (down, ydstogo, yardline_100, yards_gained, posteam, penalty, kind, two_point_attempt, qtr, game clock, scores and turnovers) joined one-to-one
on (game_id, play_id) to record.raw_frame + record.typed for: order_sequence, season_type, first_down, first_down_penalty, penalty_team, penalty_type,
desc, own_kickoff_recovery, fumble_recovery_1_team.
Plants run first, row by row; any FAIL stops the run before a count is read or a file is written.
Writes out/downs_counts.csv, out/downs_other.csv and out/downs_reasons.csv, stamped on line 1 with this file's sha and the targets sha.
out/downs_reasons.csv (N7): every count of out/downs_counts.csv split by its reason, plus C1's pairs not judged per season; the run stops if the split does not sum back.
Choices the targets do not fix, declared and printed:
 - play order is the record's order_sequence (targets line 6, v16); the number of
   adjacent down-carrying rows where the game clock runs backward under order_sequence is printed.
 - a down-carrying row is a snap (policy.CALL_KINDS, punt, field goal attempt) or a no_play row, with a down; Tries never are.
 - an accepted foul is the record's penalty flag set and the foul named; its side is the offense when penalty_team is the snapping team, else the defense.
 - a no-play keeps v4's rule (v5): repeated (3-8-4), unless a loss of down by name, or the next spot at or past the line to gain, or a defensive award (both 7-3-1(b), v11).
 - any other snap with an accepted foul is judged by v5/v6 C1 (a)-(c): S is the next snap's yardline_100, L the fouled down's yardline_100 minus its ydstogo.
   "The play itself reached L" is yards_gained on the fouled snap >= its ydstogo. Unnecessary Roughness by the offense is a foul after the whistle when its
   text says 'between downs' or yards_gained is 0 (the spot is the line of scrimmage with no gain); otherwise it is judged under (c).
 - one reason per item, one word; a reason never joins two reasons with ';' and never names a word; the count of such reasons is printed.
 - v7: on a snap not marked a no-play, accepted fouls by both teams (a 'PENALTY on' clause, any case, not followed within its clause by 'declined' or
   'offsetting', the team read before the first '-' or ',') are judged under (c) before (a).
 - v9/v10 C1 (c): a snap whose foul timing the record does not give (offensive Unnecessary Roughness enforced where the play ended, offensive Face
   Mask, accepted fouls by both teams) reads EXPLAINED when the next snap fits one or more of the outcomes its possible rules allow, every fitting rule
   named, else OTHER. A both-teams clause gives the team (before the first '-' or ','), the foul (the next comma field, a parenthesized note dropped)
   and the side (against the snapping team); a team that is neither side, or a foul on no list for its side, reads OTHER. 'Ball at or past L' is the
   next spot at or past L, or the play's own gain reaching L. C5 next: no snap after the Try in the game reads EXPLAINED, the game ran out.
 - v8: a no-play with an accepted defensive award foul (the v5 list) is followed by a 1st down; C1 also pairs kind 'other' rows that carry a down and an
   accepted, named foul (their count and rows print); Defensive Too Many Men on Field is the same down again (v7's (c) line withdrawn).
 - C2's foul is found by walking back from the first down through the same team's rows: a no-play carrying the same down and distance is passed over
   (it carried the distance unchanged, v3), the first row with a foul explains the distance, and a charged snap, the other team, a kickoff, a Try or a break stops the walk.
 - C1 pairs two down-carrying rows of one team in a row, with no kickoff or Try between, no half or overtime start between, and the first row not a punt,
   field goal attempt, score, safety or turnover; other pairs are not judged and their count is printed.
 - C3 'a kick' is a kickoff, or a punt or field goal attempt by the other team; a fourth down with no snap after it in the half is EXPLAINED by its period (v2).
 - v17: 14-1-2 Item 5's Exceptions are read from rules/nfl_rulebook_2026.pdf (its numbered lines), not typed; a foul name is an Exception when its words match
   a line, or, for Defensive Too Many Men on Field, by the tie the run re-measures (0 first downs short of the line to gain; else the tie breaks and items are
   recomputed). A receivers' foul on a punt the kickers downed, the down repeated, is named as a record error or an unread article, not told apart.
 - v19 3'': flag, do not resolve: a foul row whose (penalty_team, penalty_type) is none of the fouls its play text names as accepted (declined only when
   'declined' follows the name directly) is not judged by its columns; its C1 item reads the flag, word EXPLAINED. A text naming no foul is not flagged (its
   count prints). The targets' flag text joins two clauses with ';'; check_downs keeps one reason per item, so the two are joined with ','.
 - the rules-module stage: the foul families, Item 5's Exceptions and the tie, the illegal touch pass and the no-foul next down are read from rules.py (rules-module.md X2, X3).
Words: AS RULE / EXPLAINED (rule and article named) / OTHER (listed) / UNCHECKED (checker empty). No decision word."""
import hashlib, os, re, sys
from collections import Counter, defaultdict
import numpy as np, pandas as pd
import record, policy
import rules
from rules import PRESNAP_OFFENSE, LOSS_OF_DOWN, OFF_DURING, OFF_AFTER, DEF_AWARD, DEF_NEXT, DEF_SAME, BOOK, TMM, norm, book, is_exc, touch_yards, next_down

SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]
TARGETS, TSHA = "acceptance-criteria/downs-check.md", "e6fb7875b651"
OUT_COUNTS = "out/downs_counts.csv"
OUT_OTHER = "out/downs_other.csv"
OUT_REASONS = "out/downs_reasons.csv"
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
FLAG = "the record's foul columns disagree with its play text, which foul set the next down is not told apart"   # v19 3''
FROM_EVENTS = ["game_id", "play_id", "posteam", "qtr", "game_seconds_remaining", "kind", "down", "ydstogo", "yardline_100", "yards_gained", "penalty", "two_point_attempt",
               "touchdown", "safety", "interception", "fumble_lost", "defteam"]
EXTRA = {"game_id": ("str", False), "play_id": ("int", False), "order_sequence": ("int", False), "season_type": ("str", False), "first_down": ("int", True),
         "first_down_penalty": ("int", True), "penalty_team": ("str", True), "penalty_type": ("str", True), "desc": ("str", True),
         "own_kickoff_recovery": ("int", True), "fumble_recovery_1_team": ("str", True)}
CALL = set(policy.CALL_KINDS)
DBK = CALL | {"punt", "field_goal", "penalty"}
FITS = "fits one of the rules the record cannot tell apart"   # v9/v10 C1 (c)


def side_rules(name, side_def, dn):
    """v10 C1 (c): the outcomes one foul's rule allows, as (rule named, next down); None when the name is on no list for its side."""
    if not side_def:
        if name in ("Face Mask", "Unnecessary Roughness"): return [("during the play", dn), ("after the whistle", dn + 1)]
        if name in OFF_DURING: return [("the offense's foul during the play", dn)]
        if name in LOSS_OF_DOWN: return [("loss of down", dn + 1)]
        if name == "Illegal Touch Pass": return [("the same down (8-1-8(a))", dn), ("loss of down (8-1-8(b))", dn + 1)]
        if name in OFF_AFTER: return [("after the whistle", dn + 1)]
    else:
        if name in DEF_AWARD: return [("the defense's award", 1)]
        if name in DEF_NEXT: return [("the defense's foul, the next down", dn + 1)]
        if name in DEF_SAME: return [("the defense's foul, the same down", dn)]
    return None
WORDS = ("AS RULE", "EXPLAINED", "OTHER", "UNCHECKED")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def text_named(text):
    """v19 3'': the fouls a play text names as accepted, (team, name): each 'PENALTY on TEAM[-player], Name, ...' clause, any case; a foul is declined only when
    'declined' follows its name directly ('Name, declined'); a parenthesized note in the name is dropped."""
    t = text if isinstance(text, str) else ""; out = []
    st = [m.start() for m in re.finditer(r"penalty on ", t, flags=re.I)]
    for a, b in zip(st, st[1:] + [len(t)]):
        f = t[a + len("penalty on "):b].split(",")
        if len(f) < 2: continue
        if len(f) > 2 and f[2].strip().lower().startswith("declined"): continue
        out.append((f[0].split("-")[0].strip().upper(), norm(re.sub(r"\s*\([^)]*\)", "", f[1]))))
    return out


def flagged(pt, ptype, text):
    """v19 3'': the record's (penalty_team, penalty_type) is none of the fouls the text names as accepted (a text naming none is not flagged)."""
    named = text_named(text)
    return bool(named) and (str(pt).upper(), norm(ptype)) not in named


def foul_clauses(text):
    """Each 'PENALTY on' clause in a play's text, any case: (team, accepted, start, end). Accepted: no 'declined' or 'offsetting' in the clause (v7)."""
    t = text if isinstance(text, str) else ""
    st = [m.start() for m in re.finditer(r"penalty on ", t, flags=re.I)]
    out = []
    for a, b in zip(st, st[1:] + [len(t)]):
        seg = t[a:b]; who = seg[len("penalty on "):].split(",")[0].split("-")[0].strip(); low = seg.lower()
        out.append((who, "declined" not in low and "offsetting" not in low, a, b))
    return out


def tie_counts(items):
    """v17 2: Defensive Too Many Men on Field on C1 pairs whose foul is by the side not snapping, by what the next snap did."""
    c = Counter({k: 0 for k in ("same down", "1st down, the ball at or past the line", "1st down short of the line", "other")})
    for d in items:
        if d["check"] != "C1" or d.get("foul_name") != TMM or not d.get("foul_defense"): continue
        reach = not (nan(d["S"]) or nan(d["L"])) and d["S"] <= d["L"]
        c["1st down, the ball at or past the line" if d["down"] == 1 and reach else ("same down" if d["down"] == d["prev_down"] else ("1st down short of the line" if d["down"] == 1 else "other"))] += 1
    return c


def nan(x):
    return x is None or (not isinstance(x, str) and pd.isna(x))


def one(x):
    return (not nan(x)) and x == 1


def load(season):
    ev = record.events(season)[FROM_EVENTS]
    ex = record.typed(record.raw_frame(policy.PBP_FILE.format(season=season), list(EXTRA), f"downs check {season}"), EXTRA, f"downs check {season}")
    d = ev.merge(ex, on=["game_id", "play_id"], how="inner", validate="one_to_one")
    if len(d) != len(ev) or len(d) != len(ex):
        raise record.DataGap(f"downs check {season}: events {len(ev)} and raw extras {len(ex)} do not join one-to-one ({len(d)})")
    for c in d.columns:
        if str(d[c].dtype) == "Int64":
            d[c] = d[c].to_numpy(dtype=float, na_value=np.nan)
    d["season"] = season
    print(f"downs check {season}: rows {len(d)} joined one-to-one (events {len(ev)}, raw extras {len(ex)})")
    return d.sort_values(["game_id", "order_sequence"]).reset_index(drop=True)


def half_break(qa, qb):
    return (qa in (1, 2) and qb in (3, 4)) or (qb >= 5 and qa != qb)


def checks(g):
    """Every judged item of C1-C5 in one game, plus the pairs C1 did not grader."""
    g = g.reset_index(drop=True); c = {k: g[k].tolist() for k in g.columns}; n = len(g); items = []; unpaired = 0
    kind, team, q, dn = c["kind"], c["posteam"], c["qtr"], c["down"]
    def item(check, word, why, k, **kw):
        d = dict(check=check, word=word, why=why, game_id=c["game_id"][k], season=c["season"][k], season_type=c["season_type"][k], seq=int(c["order_sequence"][k]),
                 team=team[k], down=dn[k], ydstogo=c["ydstogo"][k], yardline_100=c["yardline_100"][k]); d.update(kw); items.append(d)
    def cancelled(k): return kind[k] == "penalty"                      # v3: the record's no-play mark only
    def between(a, b, kinds): return any(kind[x] in kinds for x in range(a + 1, b))
    DB = [k for k in range(n) if kind[k] in DBK and not one(c["two_point_attempt"][k]) and not nan(dn[k])]
    DB1 = [k for k in range(n) if (kind[k] in DBK or (kind[k] == "other" and one(c["penalty"][k]) and not nan(c["penalty_type"][k])))
           and not one(c["two_point_attempt"][k]) and not nan(dn[k])]   # v8: C1 pairs a kind-other row with a down and an accepted, named foul
    # C1 range (3-8-2)
    for k in DB:
        if dn[k] not in (1, 2, 3, 4):
            item("C1", "OTHER", "down outside 1-4 (3-8-2)", k)
    # C1 pairs (3-8-5, 3-8-4, 7-3-1; v5/v6 C1 (a)-(c))
    def accepted(k): return one(c["penalty"][k]) and not nan(c["penalty_type"][k])   # the record's penalty flag set and the foul named
    def fits(out, foul, j, kw):   # v9/v10 C1 (c): every fitting rule named, in the order given
        f = list(dict.fromkeys(lab for lab, d in out if d == dn[j]))
        if f: item("C1", "EXPLAINED", f"{FITS} ({' or '.join(f)}): {foul}", j, **kw)
        else: item("C1", "OTHER", f"fits none of the rules the record cannot tell apart, next snap down {dn[j]}: {foul}", j, **kw)
    yl, yt, yg = c["yardline_100"], c["ydstogo"], c["yards_gained"]
    for i, j in zip(DB1, DB1[1:]):
        if team[i] != team[j] or half_break(q[i], q[j]) or between(i, j, ("kickoff", "try")) or kind[i] in ("punt", "field_goal") \
                or one(c["touchdown"][i]) or one(c["safety"][i]) or one(c["interception"][i]) or one(c["fumble_lost"][i]):
            unpaired += 1; continue
        if dn[i] not in (1, 2, 3, 4) or dn[j] not in (1, 2, 3, 4):
            continue
        cx = cancelled(i)
        fx = i if accepted(i) else next((x for x in range(i + 1, j) if accepted(x)), None)
        F = c["penalty_type"][fx] if fx is not None else None
        fdef = fx is not None and isinstance(c["penalty_team"][fx], str) and c["penalty_team"][fx] != team[i]
        S, L = yl[j], (yl[i] - yt[i]) if not (nan(yl[i]) or nan(yt[i])) else np.nan
        kw = dict(prev_seq=int(c["order_sequence"][i]), prev_kind=kind[i], prev_down=dn[i], prev_ptype=c["penalty_type"][i], prev_pen_team=c["penalty_team"][i],
                  foul_seq=int(c["order_sequence"][fx]) if fx is not None else None, foul_name=F, foul_defense=fdef, S=S, L=L, next_togo=yt[j])
        if fx is not None and flagged(c["penalty_team"][fx], F, c["desc"][fx]):   # v19 3'': flag, do not resolve
            item("C1", "EXPLAINED", FLAG, j, **kw); continue
        if fx is None:   # no accepted foul on the snap or between: AS RULE or OTHER
            exp, rule = next_down(dn[i], "first_down" if (one(c["first_down"][i]) or one(c["first_down_penalty"][i])) else ("cancelled" if cx else "next"))   # the rules module X3
            if dn[j] == exp: item("C1", "AS RULE", rule, j, expected=exp, **kw)
            else: item("C1", "OTHER", f"expected down {exp}, got {dn[j]}", j, expected=exp, **kw)
            continue
        reach = not (nan(S) or nan(L)) and S <= L
        if F == "Illegal Touch Pass":   # v15: 8-1-8 by the recorded penalty, (b) no yardage on a play that counts, (a) yardage on a no-play
            yd = touch_yards(c["desc"][fx]); case = "b" if (yd == 0 and not cx) else "a" if (yd is not None and yd > 0 and cx) else None
            exp = None if case is None else (dn[i] + 1 if case == "b" else dn[i])
            if case is None: item("C1", "OTHER", f"an illegal touch pass fitting neither case of 8-1-8 ({yd} yards, {'a no-play' if cx else 'not a no-play'}): {F}", j, **kw)
            elif dn[j] == exp: item("C1", "EXPLAINED", f"an illegal touch pass with no yardage, loss of down (8-1-8(b)): {F}" if case == "b" else f"an illegal touch pass with yardage on a no-play, the same down (8-1-8(a), 14-1-2 Item 1): {F}", j, **kw)
            else: item("C1", "OTHER", f"an illegal touch pass, 8-1-8({case}) gives down {exp}, the next snap is down {dn[j]}: {F}", j, **kw)
            continue
        if cx:   # a no-play keeps v4's rule (v5)
            if F in LOSS_OF_DOWN and dn[j] == dn[i] + 1: item("C1", "EXPLAINED", f"loss of down (14-1-2 Item 2): {F}", j, **kw)
            elif dn[j] == 1 and reach: item("C1", "EXPLAINED", f"the ball placed at or past the line to gain ({'14-1-2 Item 5, 7-3-1(b)' if fdef else '14-1-2 Item 4'}): {F}", j, **kw)
            elif fdef and F in DEF_AWARD:   # v8: the award list applies to no-plays
                if dn[j] == 1: item("C1", "EXPLAINED", f"a foul by the defense that awards a first down (14-1-2 Item 5, 7-3-1(b)): {F}", j, **kw)
                else: item("C1", "OTHER", f"a no-play with a defensive award foul, next snap down {dn[j]}: {F}", j, **kw)
            elif dn[i] == 1 and dn[j] == 1 and fdef and not is_exc(F): item("C1", "EXPLAINED", f"a foul by the defense that awards a first down (14-1-2 Item 5, 7-3-1(b)): {F}", j, **kw)   # v16, v17 1
            elif fdef and dn[j] == dn[i] and not is_exc(F) and re.search(r"\bpunts\b", str(c["desc"][fx])) and "downed by" in str(c["desc"][fx]):   # v17 4
                item("C1", "EXPLAINED", f"a receivers' foul on a punt the kickers downed, enforced at the previous spot, the {ORD.get(dn[i], dn[i])} down repeated: 14-1-2 Item 5 does not give it, "
                     f"and no article was found in Rules 9 or 14 that does (14-4-7 replays a down for kickoffs and safety kicks only), a record error or an unread article, not told apart: {F}", j, **kw)
            elif dn[j] == dn[i]: item("C1", "EXPLAINED", f"a down cancelled by a foul is repeated (3-8-4): {F}", j, **kw)
            elif dn[j] == 1 and fdef: item("C1", "EXPLAINED", f"a foul by the defense that awards a first down (14-1-2 Item 5, 7-3-1(b)): {F}", j, **kw)
            else: item("C1", "OTHER", f"a no-play with a foul, next snap down {dn[j]}: {F}", j, **kw)
            continue
        past = (not (nan(S) or nan(L)) and S <= L) or ((not nan(yg[i])) and (not nan(yt[i])) and yg[i] >= yt[i])   # v9: the play or the ball at or past L
        acc_cl = [(w, a0, b0) for w, ok, a0, b0 in foul_clauses(c["desc"][fx]) if ok]
        if len({w for w, _, _ in acc_cl}) >= 2:   # v9/v10 C1 (c): accepted fouls by both teams
            out, bad, parts = [], None, []
            for w, a0, b0 in acc_cl:
                fld = c["desc"][fx][a0:b0].split(",")
                nmx = re.sub(r"\s*\([^)]*\)", "", fld[1]).strip() if len(fld) > 1 else ""
                parts.append(f"{nmx} by {w}")
                if w not in (team[i], c["defteam"][i]): bad = bad or f"a foul by a team that is neither side ({w}): {nmx}"; continue
                r_ = side_rules(nmx, w != team[i], dn[i])
                if r_ is None: bad = bad or f"a foul on no list for its side ({'offense' if w == team[i] else 'defense'}): {nmx} by {w}"; continue
                out += [(f"{nmx} by {w}, {lab}", d) for lab, d in r_]
            if bad: item("C1", "OTHER", bad, j, **kw); continue
            if past: out.append(("ball at or past L", 1))
            out.append(("the two fouls offsetting (14-1-2 Item 8, 14-5-1)", dn[i]))
            fits(out, " and ".join(parts), j, kw); continue
        if nan(S) or nan(L): item("C1", "UNCHECKED", f"the line to gain or the next spot is empty: {F}", j, **kw); continue
        if reach:   # (a)
            if dn[j] == 1: item("C1", "EXPLAINED", f"the ball placed at or past the line to gain ({'14-1-2 Item 5, 7-3-1(b)' if fdef else '14-1-2 Item 4'}): {F}", j, **kw)
            else: item("C1", "OTHER", f"the ball placed at or past the line to gain, next snap down {dn[j]}: {F}", j, **kw)
            continue
        txt = str(c["desc"][fx] or "").lower()
        ur_after = F == "Unnecessary Roughness" and ("between downs" in txt or (not nan(yg[i]) and yg[i] == 0))
        if not fdef and (F == "Face Mask" or (F == "Unnecessary Roughness" and not ur_after)):   # v9/v10 C1 (c): the record does not give the foul's timing
            fits([("during the play", dn[i]), ("after the whistle", dn[i] + 1)] + ([("ball at or past L", 1)] if past else []), F, j, kw)
        elif not fdef and F in OFF_DURING:
            ok = dn[j] == dn[i] and not nan(yt[j]) and yt[j] == S - L
            item("C1", "EXPLAINED" if ok else "OTHER", f"a foul by the offense during the play, the down replayed from the spot (14-1-2 Item 1, 3-8-4): {F}" if ok else f"a foul by the offense during the play, next snap {dn[j]} and {yt[j]} (expected {dn[i]} and {S - L}): {F}", j, **kw)
        elif not fdef and F in LOSS_OF_DOWN:
            ok = dn[j] == dn[i] + 1
            item("C1", "EXPLAINED" if ok else "OTHER", f"loss of down (14-1-2 Item 2): {F}" if ok else f"a loss-of-down foul, next snap down {dn[j]}: {F}", j, **kw)
        elif not fdef and (F in OFF_AFTER or ur_after):
            got = (not nan(yg[i])) and yg[i] >= yt[i]
            ok = dn[j] == (1 if got else dn[i] + 1)
            rule = "a foul by the offense between downs, the down unchanged (14-1-2 Item 7)" if "between downs" in txt else ("a foul by the offense after the whistle, the play reached the line to gain (14-1-2 Item 4, 7-3-1(a))" if got else "a foul by the offense after the whistle, the down counts (3-8-5)")
            item("C1", "EXPLAINED" if ok else "OTHER", f"{rule}: {F}" if ok else f"a foul by the offense after the whistle, next snap down {dn[j]}: {F}", j, **kw)
        elif fdef and F in DEF_AWARD:
            ok = dn[j] == 1 and not nan(yt[j]) and ((yt[j] == 10 and S >= 10) or (yt[j] == S and S <= 10))
            item("C1", "EXPLAINED" if ok else "OTHER", f"a foul by the defense that awards a first down (14-1-2 Item 5, 7-3-1(b)): {F}" if ok else f"a defensive award foul, next snap {dn[j]} and {yt[j]} from the {S}: {F}", j, **kw)
        elif fdef and F in DEF_NEXT + DEF_SAME:
            ok = dn[j] == (dn[i] + 1 if F in DEF_NEXT else dn[i])
            item("C1", "EXPLAINED" if ok else "OTHER", f"a foul by the defense with no award (14-1-2 Item 5 Exceptions): {F}" if ok else f"a defensive foul with no award, next snap down {dn[j]}: {F}", j, **kw)
        else:
            item("C1", "OTHER", f"a foul on no list for its side ({'defense' if fdef else 'offense'}): {F}", j, **kw)
    # C2 line to gain (3-8-3)
    for idx, k in enumerate(DB):
        if dn[k] != 1: continue
        yt, yl = c["ydstogo"][k], c["yardline_100"][k]
        p = DB[idx - 1] if idx else None
        same = p is not None and team[p] == team[k] and not half_break(q[p], q[k]) and not between(p, k, ("kickoff", "try"))
        p2 = DB[idx - 2] if idx >= 2 else None
        kw = dict(prev_seq=int(c["order_sequence"][p]) if same else None, prev_kind=kind[p] if same else None, prev_ptype=c["penalty_type"][p] if same else None,
                  prev_pen=bool(same and one(c["penalty"][p])), prev_pen_team=c["penalty_team"][p] if same else None,
                  prev2_pen=bool(same and p2 is not None and team[p2] == team[k] and one(c["penalty"][p2])))
        if nan(yt) or nan(yl): item("C2", "UNCHECKED", "ydstogo or yardline empty", k, **kw)
        elif (yt == 10 and yl >= 10) or (yt == yl and yl <= 10): item("C2", "AS RULE", "1st and 10, or and goal (3-8-3)", k, **kw)
        else:
            fx = None
            for x in range(k - 1, -1, -1):
                if kind[x] in ("kickoff", "try") or half_break(q[x], q[k]) or (isinstance(team[x], str) and team[x] != team[k]): break
                if kind[x] == "penalty" and dn[x] == dn[k] and c["ydstogo"][x] == yt and not nan(dn[x]): continue   # carried the distance unchanged (v3)
                if one(c["penalty"][x]): fx = x; break
                if kind[x] in CALL | {"punt", "field_goal"}: break
            if fx is not None:
                item("C2", "EXPLAINED", f"a foul enforced before the snap (14-4-9, 14-3): {c['penalty_type'][fx]}", k, foul_seq=int(c["order_sequence"][fx]), **kw)
            else: item("C2", "OTHER", f"1st and {yt} at the {yl}", k, **kw)
    # C3 four downs (3-8-2, 7-3-2a)
    for k in DB:
        if dn[k] != 4 or kind[k] not in CALL or cancelled(k) or one(c["first_down"][k]) or one(c["touchdown"][k]) or one(c["interception"][k]) \
                or one(c["fumble_lost"][k]) or one(c["safety"][k]):
            continue
        nx = next((x for x in range(k + 1, n) if (kind[x] in DBK or kind[x] == "kickoff") and not one(c["two_point_attempt"][x]) and kind[x] != "try"), None)
        kw = dict(next_seq=int(c["order_sequence"][nx]) if nx is not None else None, next_team=team[nx] if nx is not None else None, next_kind=kind[nx] if nx is not None else None)
        if nx is None or half_break(q[k], q[nx]):
            per = "the first half ran out (4-1-1, 4-8-1)" if q[k] in (1, 2) else ("the game ran out (4-1-1, 4-8-1)" if q[k] in (3, 4) else ("the overtime ran out (16-1-4)" if c["season_type"][k] == "POST" else "the overtime ran out (16-1-3)"))
            item("C3", "EXPLAINED", per, k, **kw)
        elif kind[nx] == "kickoff" or (kind[nx] in ("punt", "field_goal") and team[nx] != team[k]): item("C3", "AS RULE", "followed by a kick (7-3-2a)", k, **kw)
        elif not nan(team[nx]) and team[nx] != team[k]: item("C3", "AS RULE", "turnover on downs: the other team's snap (7-3-2a)", k, **kw)
        elif one(c["penalty"][k]) or any(one(c["penalty"][x]) for x in range(k + 1, nx)):   # v12: split by the fouling side
            f3 = k if one(c["penalty"][k]) else next(x for x in range(k + 1, nx) if one(c["penalty"][x])); pt3 = c["penalty_team"][f3]; nm3 = c["penalty_type"][f3]
            if isinstance(pt3, str) and pt3 != team[k]: item("C3", "EXPLAINED", f"a foul by the defense gave the offense a new series (7-3-1(b)): {nm3}", k, **kw)
            elif isinstance(pt3, str): item("C3", "EXPLAINED", f"a foul by the offense on 4th down, the 4th down replayed (3-8-4): {nm3}", k, **kw)
            else: item("C3", "EXPLAINED", f"a foul by a side the record does not name, followed by the same team's snap: {nm3}", k, **kw)
        else: item("C3", "OTHER", f"followed by {kind[nx]} of {team[nx]}", k, **kw)
    # C4 kicking-team recovery (7-3-1d, 7-3-1e)
    for k in range(n):
        if kind[k] in ("kickoff", "punt") and (one(c["own_kickoff_recovery"][k]) or (kind[k] == "punt" and isinstance(c["fumble_recovery_1_team"][k], str) and c["fumble_recovery_1_team"][k] == team[k])):
            nx = next((x for x in DB if x > k), None)
            kw = dict(kick_seq=int(c["order_sequence"][k]), kick_kind=kind[k], next_seq=int(c["order_sequence"][nx]) if nx is not None else None)
            if nx is None: item("C4", "UNCHECKED", "no snap after the recovery", k, **kw)
            elif dn[nx] == 1: item("C4", "AS RULE", f"the kickers' next snap is a first down ({'7-3-1(e)' if kind[k] == 'kickoff' else '7-3-1(d)'})", nx, **kw)
            else: item("C4", "OTHER", f"the next snap carries down {dn[nx]}", nx, **kw)
    # C5 Tries (3-40, 11-3-1)
    for k in range(n):
        if kind[k] == "try" or one(c["two_point_attempt"][k]):
            item("C5 try", "AS RULE" if nan(dn[k]) else "OTHER", "a Try carries no down (3-40)" if nan(dn[k]) else f"a Try carries down {dn[k]}", k)
            kk = next((x for x in range(k + 1, n) if kind[x] == "kickoff"), None)
            nx = next((x for x in DB if kk is not None and x > kk), None)
            if not any(x > k for x in DB): item("C5 next", "EXPLAINED", "the game ran out after the Try (4-1-1 and 4-8-1)" if q[k] < 5 else ("the game ran out after the Try (16-1-4)" if c["season_type"][k] == "POST" else "the game ran out after the Try (16-1-3)"), k)   # v9
            elif kk is None or nx is None: item("C5 next", "OTHER", "a snap followed the Try with no kickoff before it", k)
            else: item("C5 next", "AS RULE" if dn[nx] == 1 else "OTHER", "the first snap after the kickoff is a first down (11-3-1)" if dn[nx] == 1 else f"first snap after the kickoff carries down {dn[nx]}", nx, try_seq=int(c["order_sequence"][k]))
    return items, unpaired


def series(g):
    """Series lengths in charged snaps by how each series ended (read, not graded)."""
    g = g.reset_index(drop=True); c = {k: g[k].tolist() for k in g.columns}; out = []
    S = [k for k in range(len(g)) if c["kind"][k] in (CALL | {"punt", "field_goal"}) and not nan(c["down"][k])]
    cnt = 0
    def end(p, k):
        if one(c["touchdown"][p]) or one(c["safety"][p]): return "score"
        if c["kind"][p] == "field_goal": return "field goal attempt"
        if c["kind"][p] == "punt": return "punt"
        if one(c["interception"][p]) or one(c["fumble_lost"][p]): return "turnover"
        if k is not None and c["posteam"][k] != c["posteam"][p] and c["down"][p] == 4: return "turnover on downs"
        if k is not None and c["posteam"][k] == c["posteam"][p] and c["down"][k] == 1: return "first down"
        return "end of half or other"
    for idx, k in enumerate(S):
        p = S[idx - 1] if idx else None
        new = p is None or c["posteam"][k] != c["posteam"][p] or c["down"][k] == 1 or half_break(c["qtr"][p], c["qtr"][k]) or any(c["kind"][x] in ("kickoff", "try") for x in range(p + 1, k))
        if new and p is not None: out.append((end(p, k), cnt))
        cnt = 1 if new else cnt + 1
    if S: out.append((end(S[-1], None), cnt))
    return out


def main():
    if sha(TARGETS) != TSHA:
        sys.exit(f"STOPPED: {TARGETS} is {sha(TARGETS)}, not the frozen {TSHA}")
    seasons = [s for s in policy.SEASONS if s != policy.HOLD]
    tag = f"check_downs.py {SELF} | {TARGETS} {TSHA} | record read (rules-level clause 3), not product"
    print(f"{tag} | seasons {seasons} (hold-out {policy.HOLD} held_out)")
    D = pd.concat([load(s) for s in seasons], ignore_index=True)
    G = {gid: d.reset_index(drop=True) for gid, d in D.groupby("game_id", sort=False)}
    back = 0
    for gd in G.values():
        m = gd[gd["kind"].isin(DBK) & gd["down"].notna()]
        back += int(((m["qtr"].diff() == 0) & (m["game_seconds_remaining"].diff() > 0)).sum())
    print(f"adjacent down-carrying rows where the game clock runs backward under order_sequence: {back}")
    ITEMS, unpaired, UNP = [], 0, Counter()
    for gd in G.values():
        it, u = checks(gd); ITEMS += it; unpaired += u; UNP[(gd["season"].iloc[0], gd["season_type"].iloc[0])] += u
    tc = tie_counts(ITEMS)
    print(f"v17 2 tie re-measured: {TMM} on C1 pairs by the side not snapping {sum(tc.values())} | {dict(tc)} | the tie holds: {tc['1st down short of the line'] == 0}")
    if tc["1st down short of the line"]:
        rules.TIE = False; ITEMS, unpaired, UNP = [], 0, Counter()
        for gd in G.values():
            it, u = checks(gd); ITEMS += it; unpaired += u; UNP[(gd["season"].iloc[0], gd["season_type"].iloc[0])] += u
        print(f"v17 2 the tie broke: {TMM} is not an Exception; items recomputed")
    I = pd.DataFrame(ITEMS)
    print(f"items {len(I)} | C1 pairs not judged (a change of team, a break or a possession-ending first row) {unpaired}")
    ko = D[(D["kind"] == "other") & D["down"].notna() & (D["penalty"] == 1) & D["penalty_type"].notna() & (D["two_point_attempt"] != 1)]
    print(f"kind 'other' rows with a down and an accepted, named foul, now paired by C1 (v8): {len(ko)}")
    for _, x in ko.iterrows():
        print(f"   {x['game_id']} seq {int(x['order_sequence'])} {x['posteam']} down {x['down']} togo {x['ydstogo']} at {x['yardline_100']} | {x['penalty_type']} by {x['penalty_team']} | {x['desc']}")

    B_ = book()
    print(f"v17 1 Item 5 Exceptions read from {BOOK} (book lines {B_['exc_lines'][0]} to {B_['exc_lines'][1]}): {B_['exc']}")
    A_ = D[(D["penalty"] == 1) & D["penalty_type"].notna()]
    FL = [(g_, int(s_), t_, p_, text_named(d_)) for g_, s_, t_, p_, d_ in zip(A_["game_id"], A_["order_sequence"], A_["penalty_team"], A_["penalty_type"], A_["desc"]) if flagged(t_, p_, d_)]
    none_ = sum(1 for d_ in A_["desc"] if not text_named(d_))
    print(f"v19 3'' accepted penalty rows {len(A_)} | flagged (columns name none of the text's accepted fouls): {len(FL)} | rows whose text names no foul (not flagged): {none_}")
    for g_, s_, t_, p_, tf_ in FL: print(f"   {g_} seq {s_} | columns ({t_}, {p_}) | text names {tf_}")

    print("\n=== PLANTS, row by row (each negative must read OTHER; any FAIL stops the run) ===")
    res = []

    def injected_fault(name, cond):
        res.append(bool(cond)); print(f"  {name} -> {'PASS' if cond else 'FAIL'}")

    def rows(gid, s0, s1):
        g = G[gid]
        for _, r in g[(g["order_sequence"] >= s0) & (g["order_sequence"] <= s1)].iterrows():
            print(f"      seq {int(r['order_sequence'])} q{int(r['qtr'])} {r['posteam']} {r['kind']} down {r['down']} togo {r['ydstogo']} at {r['yardline_100']} pen {r['penalty']} {r['penalty_type'] or ''} 1st {r['first_down']} | {str(r['desc'])[:100]}")

    def grader(gcopy, check, seq):
        it, _ = checks(gcopy); x = [d for d in it if d["check"] == check and d["seq"] == seq]
        return x[0]["word"] if len(x) == 1 else f"{len(x)} items"
    C2 = I[I["check"] == "C2"]
    p1 = C2[(C2["word"] == "AS RULE") & (C2["yardline_100"] < 10) & (C2["ydstogo"] == C2["yardline_100"]) & (C2["prev_pen"] == False)]
    r = p1.iloc[0] if len(p1) else None
    if r is not None: print(f"  P1 found and pinned: {r['game_id']} seq {r['seq']} (1st and goal at the {r['yardline_100']}):"); rows(r["game_id"], r["seq"], r["seq"])
    injected_fault(f"P1 1st and goal (C2) -> {None if r is None else r['word']}", r is not None and r["word"] == "AS RULE")
    if r is not None:
        F = G[r["game_id"]].copy(); F.loc[F["order_sequence"] == r["seq"], "ydstogo"] = 10.0
        w = grader(F, "C2", r["seq"]); injected_fault(f"NEG1 its ydstogo set to 10: AS RULE -> {w}", w == "OTHER")
    else: injected_fault("NEG1 (no P1 to injected_fault on)", False)
    p2 = C2[(C2["word"] == "EXPLAINED") & (C2["ydstogo"] == 15) & (C2["prev_kind"] == "penalty") & C2["prev_ptype"].isin(PRESNAP_OFFENSE) & (C2["prev_pen_team"] == C2["team"]) & (C2["prev2_pen"] == False)]
    r = p2.iloc[0] if len(p2) else None
    if r is not None: print(f"  P2 found and pinned: {r['game_id']} seq {r['prev_seq']} -> {r['seq']} ({r['prev_ptype']}):"); rows(r["game_id"], r["prev_seq"], r["seq"])
    injected_fault(f"P2 1st and 15 after a pre-snap offensive foul (C2) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED")
    if r is not None:
        F = G[r["game_id"]]; F = F[F["order_sequence"] != r["prev_seq"]].reset_index(drop=True)
        w = grader(F, "C2", r["seq"]); injected_fault(f"NEG2 the foul row removed: EXPLAINED -> {w}", w == "OTHER")
    else: injected_fault("NEG2 (no P2 to injected_fault on)", False)
    C1 = I[I["check"] == "C1"]
    p3 = C1[(C1["word"] == "AS RULE") & (C1["prev_kind"] == "penalty") & C1["why"].str.startswith("a down cancelled") & (C1["down"] < 4)]
    r = p3.iloc[0] if len(p3) else None
    if r is not None: print(f"  P3 found and pinned: {r['game_id']} seq {r['prev_seq']} -> {r['seq']}:"); rows(r["game_id"], r["prev_seq"], r["seq"])
    injected_fault(f"P3 a down repeated after a play cancelled by a foul (C1) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "AS RULE")
    if r is not None:
        F = G[r["game_id"]].copy(); F.loc[F["order_sequence"] == r["seq"], "down"] = r["down"] + 1
        w = grader(F, "C1", r["seq"]); injected_fault(f"NEG3 the repeated snap's down raised by one: AS RULE -> {w}", w == "OTHER")
    else: injected_fault("NEG3 (no P3 to injected_fault on)", False)
    C3 = I[I["check"] == "C3"]
    p4 = C3[(C3["word"] == "AS RULE") & C3["why"].str.startswith("turnover on downs")]
    p4 = p4[[not one(G[a].loc[G[a]["order_sequence"] == b, "penalty"].iloc[0]) for a, b in zip(p4["game_id"], p4["seq"])]] if len(p4) else p4
    r = p4.iloc[0] if len(p4) else None
    if r is not None: print(f"  P4 found and pinned: {r['game_id']} seq {r['seq']} -> {r['next_seq']}:"); rows(r["game_id"], r["seq"], r["next_seq"])
    injected_fault(f"P4 a turnover on downs (C3) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "AS RULE")
    if r is not None:
        F = G[r["game_id"]].copy(); F.loc[F["order_sequence"] == r["next_seq"], "posteam"] = r["team"]
        w = grader(F, "C3", r["seq"]); injected_fault(f"NEG4 the next snap relabeled to the same team: AS RULE -> {w}", w == "OTHER")
    else: injected_fault("NEG4 (no P4 to injected_fault on)", False)
    C4 = I[(I["check"] == "C4") & (I["game_id"] == "2025_08_CLE_NE")]
    C4 = C4[C4["kick_seq"] <= 3742]
    r = C4.loc[C4["kick_seq"].idxmax()] if len(C4) else None
    if r is not None: print(f"  P5 2025_08_CLE_NE kick seq {r['kick_seq']} ({r['kick_kind']}) -> next snap seq {r['next_seq']}:"); rows("2025_08_CLE_NE", r["kick_seq"], r["next_seq"])
    injected_fault(f"P5 the kicking-team recovery around seq 3742, next snap a first down (C4) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "AS RULE")
    if r is not None:
        F = G["2025_08_CLE_NE"].copy(); F.loc[F["order_sequence"] == r["next_seq"], "down"] = 2.0
        w = grader(F, "C4", int(r["next_seq"])); injected_fault(f"NEG5 that snap's down set to 2: AS RULE -> {w}", w == "OTHER")
    else: injected_fault("NEG5 (no P5 to injected_fault on)", False)
    C5 = I[(I["check"] == "C5 try") & (I["word"] == "AS RULE")]
    r = C5.iloc[0] if len(C5) else None
    if r is not None: print(f"  P6 found and pinned: {r['game_id']} seq {r['seq']}:"); rows(r["game_id"], r["seq"], r["seq"])
    injected_fault(f"P6 a Try (C5) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "AS RULE")
    if r is not None:
        F = G[r["game_id"]].copy(); F.loc[F["order_sequence"] == r["seq"], "down"] = 1.0
        w = grader(F, "C5 try", r["seq"]); injected_fault(f"NEG6 a down written onto it: AS RULE -> {w}", w == "OTHER")
    else: injected_fault("NEG6 (no P6 to injected_fault on)", False)
    gid = I[I["check"] == "C1"].iloc[0]["game_id"]; F = G[gid].copy()
    k = F.index[F["kind"].isin(CALL) & F["down"].notna()][0]; s7 = int(F.loc[k, "order_sequence"]); F.loc[k, "down"] = 5.0
    it, _ = checks(F); hit = [d for d in it if d["check"] == "C1" and d["seq"] == s7 and d["why"].startswith("down outside")]
    injected_fault(f"NEG7 {gid} seq {s7} down set to 5 -> C1 {'OTHER' if hit else 'not flagged'}", len(hit) == 1)
    def pin(label, gid, check, seq, s0, s1, want):
        print(f"  {label} {gid} seq {s0} -> {s1} (pinned in the targets):"); rows(gid, s0, s1)
        x = I[(I["game_id"] == gid) & (I["check"] == check) & (I["seq"] == seq)]
        got = (x.iloc[0]["word"], x.iloc[0]["why"]) if len(x) == 1 else (f"{len(x)} items", "")
        injected_fault(f"{label} ({check} {want}) -> {got}", got[0] == want); return x.iloc[0] if len(x) == 1 else None
    r = pin("P7", "2020_05_PHI_PIT", "C1", 94, 62, 94, "AS RULE")
    F = G["2020_05_PHI_PIT"].copy(); F.loc[F["order_sequence"] == 62, "kind"] = "penalty"
    w = grader(F, "C1", 94); injected_fault(f"NEG7b seq 62 marked a no-play: AS RULE -> {w}", w == "OTHER")
    r = pin("P8", "2020_09_DEN_ATL", "C1", 1784, 1713, 1784, "AS RULE")
    F = G["2020_09_DEN_ATL"].copy(); F.loc[F["order_sequence"] == 1784, "down"] = 2.0
    w = grader(F, "C1", 1784); injected_fault(f"NEG8 seq 1784's down set to 2: AS RULE -> {w}", w == "OTHER")
    r = pin("P9", "2025_02_SEA_PIT", "C1", 3709, 3686, 3709, "EXPLAINED")
    F = G["2025_02_SEA_PIT"].copy(); F.loc[F["order_sequence"] == 3686, "penalty_type"] = None
    w = grader(F, "C1", 3709); injected_fault(f"NEG9 the foul name cleared: EXPLAINED -> {w}", w == "OTHER")
    r = pin("P10", "2019_07_OAK_GB", "C2", 481, 446, 481, "EXPLAINED")
    F = G["2019_07_OAK_GB"]; F = F[F["order_sequence"] != 446].reset_index(drop=True)
    w = grader(F, "C2", 481); injected_fault(f"NEG10 the foul row removed: EXPLAINED -> {w}", w == "OTHER")
    r = pin("P11", "2019_18_TEN_NE", "C2", 547, 479, 547, "EXPLAINED")
    F = G["2019_18_TEN_NE"]; F = F[F["order_sequence"] != 479].reset_index(drop=True)
    w = grader(F, "C2", 547); injected_fault(f"NEG11 the false start row removed: EXPLAINED -> {w}", w == "OTHER")
    r = pin("P12", "2019_01_NYG_DAL", "C3", 2134, 2134, 2134, "EXPLAINED")
    F = G["2019_01_NYG_DAL"].copy(); add = F[F["order_sequence"] == 2134].copy()
    add["order_sequence"] = 2134.5; add["kind"] = "run"; add["down"] = 1.0; add["penalty"] = 0.0; add["penalty_type"] = None
    F = pd.concat([F, add], ignore_index=True).sort_values("order_sequence").reset_index(drop=True)
    w = grader(F, "C3", 2134); injected_fault(f"NEG12 a {add['posteam'].iloc[0]} snap inserted after it in the same half: EXPLAINED -> {w}", w == "OTHER")
    C1 = I[I["check"] == "C1"]
    p13 = C1[(C1["word"] == "EXPLAINED") & C1["why"].str.startswith("a foul by the offense during the play, the down replayed from the spot (14-1-2 Item 1, 3-8-4): Offensive Holding") & (C1["prev_kind"] == "run")]
    r = p13.iloc[0] if len(p13) else None
    if r is not None: print(f"  P13 found and pinned: {r['game_id']} seq {r['prev_seq']} -> {r['seq']}:"); rows(r["game_id"], r["prev_seq"], r["seq"])
    injected_fault(f"P13 an offensive holding on a run, not a no-play, the down repeated (C1 EXPLAINED 3-8-4) -> {None if r is None else (r['word'], r['why'])}", r is not None)
    if r is not None:
        F = G[r["game_id"]].copy(); F.loc[F["order_sequence"] == r["prev_seq"], "penalty"] = 0.0
        w = grader(F, "C1", r["seq"]); injected_fault(f"NEG13 its penalty flag cleared: EXPLAINED -> {w}", w == "OTHER")
    else: injected_fault("NEG13 (no P13 to injected_fault on)", False)
    def at(gid, s):
        x = C1[(C1["game_id"] == gid) & (C1["prev_seq"] == s)]
        if len(x) == 1:
            r = x.iloc[0]; print(f"  pinned {gid} seq {s} -> {r['seq']} | S {r['S']} L {r['L']} | {r['word']} | {r['why']}"); rows(gid, s, r["seq"]); return r
        print(f"  {gid} seq {s}: {len(x)} C1 items with it as the fouled snap"); return None
    def neg(label, r, col, val, on_next=True):
        if r is None: injected_fault(f"{label} (nothing pinned)", False); return
        F = G[r["game_id"]].copy(); F.loc[F["order_sequence"] == (r["seq"] if on_next else r["prev_seq"]), col] = val
        w = grader(F, "C1", r["seq"]); injected_fault(f"{label}: {r['word']} -> {w}", w == "OTHER")
    r = at("2019_14_CIN_CLE", 3338)
    injected_fault(f"P14b offensive holding, the ball placed past L, next snap 1st and 10 (C1 (a)) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"].startswith("the ball placed at or past the line to gain (14-1-2 Item 4)"))
    neg("NEG14b the next snap's down set to 3", r, "down", 3.0)
    r = at("2019_01_BUF_NYJ", 610)
    injected_fault(f"P15 taunting by the offense after a 3rd-down scramble, next snap a 4th down (C1 (b) after the whistle) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"].startswith("a foul by the offense after the whistle, the down counts"))
    neg("NEG15 the next snap's down set to 3", r, "down", 3.0)
    r = at("2021_11_DET_CLE", 2863)
    injected_fault(f"P16 unsportsmanlike conduct by the offense 'between downs' after a 13-yard gain, next snap 1st and 25 (C1 (b)) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"].startswith("a foul by the offense between downs, the down unchanged (14-1-2 Item 7)"))
    neg("NEG16 (v6) the next snap's down set to 2", r, "down", 2.0)
    p18 = C1[(C1["word"] == "EXPLAINED") & (C1["why"] == "a foul by the defense that awards a first down (14-1-2 Item 5, 7-3-1(b)): Defensive Holding") & (C1["foul_seq"] == C1["prev_seq"])
             & (C1["L"] > 0) & (C1["S"] > C1["L"]) & (C1["S"] >= 10) & (C1["next_togo"] == 10) & (C1["prev_down"] == 3)]
    r = p18.iloc[0] if len(p18) else None
    if r is not None: print(f"  P18 found and pinned: {r['game_id']} seq {r['prev_seq']} -> {r['seq']} | S {r['S']} L {r['L']}:"); rows(r["game_id"], r["prev_seq"], r["seq"])
    injected_fault(f"P18 a defensive holding short of L outside goal-to-go, next snap 1st and 10 from S (C1 (b) award) -> {None if r is None else (r['word'], r['why'])}", r is not None)
    neg("NEG18 (v7) the next snap's down set to 3, the fouled down replayed", r, "down", 3.0)
    r = at("2021_09_ARI_SF", 1586)
    injected_fault(f"P19 (v19) SF's Taunting and ARI's Unsportsmanlike Conduct, the columns naming ARI's Taunting: the flag -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"] == FLAG)
    if r is not None:
        F = G[r["game_id"]].copy(); m = F["order_sequence"] == r["prev_seq"]; t0 = str(F.loc[m, "desc"].iloc[0])
        t1 = "".join(t0[a:b] for w, ok, a, b in foul_clauses(t0) if not (ok and w == "ARI")); t1 = t0[:foul_clauses(t0)[0][2]] + t1 if foul_clauses(t0) else t0
        print(f"      NEG19 text after the ARI clause is removed: {t1}")
        F.loc[m, "desc"] = t1; F.loc[m, "penalty_team"] = "SF"; F.loc[F["order_sequence"] == r["seq"], "down"] = 4.0
        w = grader(F, "C1", r["seq"]); injected_fault(f"NEG19 (v8) the ARI clause removed, penalty_team set to SF, the next snap's down set to 4: {r['word']} -> {w}", w == "OTHER")
    else: injected_fault("NEG19 (nothing pinned)", False)
    r = at("2023_10_DEN_BUF", 4471)
    injected_fault(f"P20 (v8) Defensive Too Many Men on Field on a kind-other row, the same down (C1 (b), defense, no award) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"] == "a foul by the defense with no award (14-1-2 Item 5 Exceptions): Defensive Too Many Men on Field")
    neg("NEG20 (v8) the next snap's down set to 1", r, "down", 1.0)
    r = at("2019_01_PIT_NE", 3917)
    injected_fault(f"P21 offensive Unnecessary Roughness, the next snap fits after the whistle (C1 (c)) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"] == f"{FITS} (after the whistle): Unnecessary Roughness")
    neg("NEG21 the next snap's down set to 3", r, "down", 3.0)
    if r is not None:   # v19: the foul name changes in the columns and the text together; a column-only change is a disagreement the flag reads
        F = G[r["game_id"]].copy(); m = F["order_sequence"] == r["prev_seq"]
        F.loc[m, "penalty_type"] = "Offensive Holding"; F.loc[m, "desc"] = F.loc[m, "desc"].map(lambda t: t.replace("Unnecessary Roughness", "Offensive Holding"))
        w = grader(F, "C1", r["seq"]); injected_fault(f"NEG17 (under P21, v19) the foul name set to Offensive Holding in the columns and the play text: {r['word']} -> {w}", w == "OTHER")
    else: injected_fault("NEG17 (nothing pinned)", False)
    x = I[(I["check"] == "C5 next") & (I["game_id"] == "2020_07_DET_ATL") & (I["seq"] == 4362)]
    r = x.iloc[0] if len(x) == 1 else None
    print(f"  P22 2020_07_DET_ATL seq 4362: {len(x)} C5 next item(s)"); rows("2020_07_DET_ATL", 4362, 99999)
    injected_fault(f"P22 an extra point with no snap after it (C5 next, the game ran out) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"].startswith("the game ran out after the Try"))
    if r is not None:
        F = G["2020_07_DET_ATL"].copy(); add = F[F["order_sequence"] == 4362].copy()
        add["order_sequence"] = 4362.5; add["kind"] = "pass"; add["down"] = 2.0; add["posteam"] = "ATL"; add["two_point_attempt"] = 0.0; add["penalty"] = 0.0; add["penalty_type"] = None
        F = pd.concat([F, add], ignore_index=True).sort_values("order_sequence").reset_index(drop=True)
        w = grader(F, "C5 next", 4362); injected_fault(f"NEG22 a 2nd-down ATL snap inserted after it in the same quarter: EXPLAINED -> {w}", w == "OTHER")
    else: injected_fault("NEG22 (nothing pinned)", False)
    r = at("2020_16_NYG_BAL", 1821)
    injected_fault(f"P23 (v15) an Illegal Touch Pass, 0 yards, 2nd down then 3rd (8-1-8(b)) -> {None if r is None else (r['word'], r['why'])}", r is not None and r["word"] == "EXPLAINED" and r["why"].startswith("an illegal touch pass with no yardage, loss of down (8-1-8(b))"))
    if r is not None:
        F = G[r["game_id"]].copy(); m = F["order_sequence"] == r["prev_seq"]
        F.loc[m, "desc"] = F.loc[m, "desc"].map(lambda t: re.sub(r"(Illegal Touch Pass,\s*)\d+(\s*yard)", r"\g<1>5\g<2>", t, flags=re.I))
        print(f"      NEG23 text with the penalty's yardage set to 5: {F.loc[m, 'desc'].iloc[0]}")
        w = grader(F, "C1", r["seq"]); injected_fault(f"NEG23 (v15) the penalty's yardage set to 5 yards (case (a) requires a no-play and the same down): EXPLAINED -> {w}", w == "OTHER")
    else: injected_fault("NEG23 (nothing pinned)", False)
    npass = sum(res)
    if npass != len(res) or len(res) != 46:
        print(f"\nR4 SUMMARY injected_faults {npass}/{len(res)} FAILED | no count read, no file written"); sys.exit(1)

    print("\n=== COUNTS per season, regular season and postseason apart (AS RULE / EXPLAINED / OTHER / UNCHECKED; no decision word) ===")
    crow = []
    for (s, st, ch), x in I.groupby(["season", "season_type", "check"]):
        w = Counter(x["word"]); crow += [(s, st, ch, k, n) for k, n in w.items()]
    CT = pd.DataFrame(crow, columns=["season", "season_type", "check", "word", "count"])
    for s in seasons:
        for st in ("REG", "POST"):
            x = CT[(CT["season"] == s) & (CT["season_type"] == st)]
            print(f"\n{s} {st}: " + " | ".join(f"{ch} {dict(zip(y['word'], y['count']))}" for ch, y in x.groupby("check")))
    for ch in ("C1", "C2", "C3", "C4", "C5 try", "C5 next"):
        x = I[I["check"] == ch]
        print(f"\n{ch} all seasons: {dict(Counter(x['word']))}")
        for k, v in Counter(x.loc[x["word"] == "EXPLAINED", "why"]).most_common(6): print(f"   EXPLAINED {v}: {k}")
        for k, v in Counter(x.loc[x["word"] == "OTHER", "why"]).most_common(6): print(f"   OTHER {v}: {k}")
        for _, r in x[x["word"] == "OTHER"].head(5).iterrows(): print(f"      e.g. {r['game_id']} seq {r['seq']} {r['team']} down {r['down']} togo {r['ydstogo']} at {r['yardline_100']} | {r['why']}")
    x = I[I["check"] == "C1"]
    for word in ("EXPLAINED", "UNCHECKED"):
        y = x[x["word"] == word]
        fam = Counter(y["why"].str.rsplit(": ", n=1).str[0])
        for f, n in fam.most_common():
            z = y[y["why"].str.rsplit(": ", n=1).str[0] == f]
            print(f"\nC1 {word} {f}: {n} | by foul name {dict(Counter(z['foul_name'].fillna('none')).most_common())}")
    two = I[I["why"].str.contains(";") | I["why"].map(lambda s: any(w in s for w in WORDS))]
    print(f"\nreasons joining two reasons (';') or naming a word: {len(two)} (expected 0)")
    for _, r in two.iterrows(): print(f"   {r['check']} {r['game_id']} seq {r['seq']} {r['word']} | {r['why']}")
    O = I[I["word"] == "OTHER"]
    with open(OUT_COUNTS, "w") as f:
        f.write(f"# {tag}\n"); CT.to_csv(f, index=False)
    with open(OUT_OTHER, "w") as f:
        f.write(f"# {tag}\n"); O.to_csv(f, index=False)
    RR = I.groupby(["season", "season_type", "check", "word", "why"]).size().reset_index(name="count")
    back_ = RR.groupby(["season", "season_type", "check", "word"])["count"].sum().to_dict(); ct_ = CT.set_index(["season", "season_type", "check", "word"])["count"].to_dict()
    nj = pd.DataFrame([(s, st, "C1 not judged", "NOT JUDGED", "a change of team, a break, or a possession ending on its first snap", u) for (s, st), u in sorted(UNP.items())], columns=RR.columns)
    print(f"N7 reasons: rows {len(RR)} | the split sums back to the counts: {back_ == ct_} | C1 pairs not judged {int(nj['count'].sum())} (printed total {unpaired})")
    if back_ != ct_ or int(nj["count"].sum()) != unpaired:
        print(f"\nR4 SUMMARY injected_faults {npass}/{len(res)} | the reason split does not sum to the counts | no reasons file written"); sys.exit(1)
    with open(OUT_REASONS, "w") as f:
        f.write(f"# {tag}\n"); pd.concat([RR, nj], ignore_index=True).to_csv(f, index=False)
    print(f"\nwritten, stamped on line 1: {OUT_COUNTS} sha {sha(OUT_COUNTS)} | {OUT_OTHER} rows {len(O)} sha {sha(OUT_OTHER)} | {OUT_REASONS} sha {sha(OUT_REASONS)}")

    print("\n=== READ: series length in snaps by how the series ended (not graded) ===")
    for s in seasons:
        L = defaultdict(list)
        for gd in G.values():
            if gd["season"].iloc[0] == s:
                for e, nsn in series(gd): L[e].append(nsn)
        print(f"  {s}: " + " | ".join(f"{e} n {len(v)} mean {np.mean(v):.2f} median {np.median(v):.0f}" for e, v in sorted(L.items())))
    tot = dict(Counter(I["word"]))
    print(f"\nOTHER {len(O)} (the reviewer's expectation before the run: 0) -> {'holds' if len(O) == 0 else 'MISSED'} | loss-of-down fouls read by name: {dict(Counter(I.loc[I['why'].str.startswith('loss of down'), 'why']))}")
    print(f"\nR4 SUMMARY injected_faults {npass}/{len(res)} | OTHER {len(O)} (expected 0) | items {tot} | OTHER {len(O)} listed in {OUT_OTHER} {sha(OUT_OTHER)} | {OUT_COUNTS} {sha(OUT_COUNTS)}")


if __name__ == "__main__":
    main()
