"""transition.py - the one transition: possession, down, distance and yard line after one event (NFL rules: 3-8, 7-3, 11-3 to 11-6, 14-1-2, Rule 6).
Product code. The record's adapter (the rebuild of the record's states) and the engine both call after(); the record supplies an event's observed
attributes (its row's columns), the engine its generated ones (its draws); neither computes the resulting state itself. A part whose inputs are missing
comes back UNKNOWN with its reason, never filled.
Landed from chain e2b_v17_1725d9c82df1's shared library (lib_trans) as 96229f766489; tb_rules takes the Rule 11 Section 6 spots as an argument.
the engine-vs-record stage v18 c adds one case: a foul on a play that stands (stand(), the event's 'foul_stand'): the play's result kept and the foul enforced on it, by the
family rules.py's foul families lists name (rules.py 3d9b5a3b1985, each list citing its article) and the season's Dead Ball Foul article (rb: 'the down counts',
'a taunting foul that occurs at any time'), from the row's own columns (yards_gained, penalty_yards, penalty_team, first_down_penalty) and the spot its
text says the foul was enforced at; where those do not give a part, the parts are UNKNOWN with the reason. Every other answer is 96229f766489's.
the engine-vs-record stage v19 part 2: stand() reads the defense's foul with no award by rules.py's Item 5 Exceptions (DEF_NEXT the next down, DEF_SAME the same down); and the
yards of a foul are computed here, by its article, from the spot it is enforced at (foul_yards: the book's distance, half the distance to the
offender's goal where the book sets it; spot_foul_yards: pass interference by the defense, a spot foul), for the engine and the record check alike.
the engine-vs-record stage v19 r: a distance foul whose enforcement would carry the ball to or past the fouling team's goal line is placed half the distance from the
enforcement spot to that goal (goal_half: the book's half-the-distance article, printed by line in each chain), in after_one and stand() alike, never
UNKNOWN; pass interference by the defense takes the foul's depth (the record's penalty_yards on a wiped row) and, in the end zone, the 1-yard line or half
the distance from the previous spot, whichever is more beneficial (the season's book, printed by line).
the engine-vs-record stage v19 s, t: a fraction of a yard is a spot (s1, t1: kept exactly however many times half the distance halves it, never rounded; the engine writes the record's columns in the record's marking); the offense's
unnecessary roughness on a play that stands, enforced at the play's end (the succeeding spot), is a dead ball foul by the season's Dead Ball Foul article:
'enforced from the succeeding spot, and the down counts' (s3: OFF_DEAD_BOOK; a play whose result stands carries no accepted live-ball foul by the offense).
Its known-right cases (FIXTURES, each true by the article it names, built by hand) and its injected faults (PLANTS, each must fail a case) live here;
test_transition.py runs them and proves this file byte-identical in its answers to the chain's copy."""
import math, re
import pandas as pd
import rules, record
from rules import next_down, next_possession


def nanv(x):
    return x is None or (not isinstance(x, str) and pd.isna(x))


def one_(x):
    return (not nanv(x)) and x == 1


# yl: yards to the goal line the team with the ball attacks (yardline_100); togo: yards to the line to gain; a kick to come has no down, distance or yard line.
TPARTS = ("offense", "down", "distance", "yard line")


def _k(*v):
    return all(not nanv(x) for x in v)


def series(team, yl, how):
    """A new series (7-3-1): first and 10, or goal to go inside the 10."""
    return dict(off=team, down=1, togo=min(10, yl), yl=yl, kick=False, kick_kind=None, new_series=True, unk=() if isinstance(team, str) else ("offense",), how=how)


def kick_to_come(receiver, how, kind="normal"):
    return dict(off=receiver, down=None, togo=None, yl=None, kick=True, kick_kind=kind, new_series=False, unk=() if isinstance(receiver, str) else ("offense",), how=how)


def unknown(off, how, parts=("down", "distance", "yard line")):
    return dict(off=off, down=None, togo=None, yl=None, kick=False, kick_kind=None, new_series=False,
                unk=tuple(p for p in TPARTS if p in parts or (p == "offense" and not isinstance(off, str))), how=how)


def same(st, down, togo, yl, how):
    return dict(off=st.get("off"), down=down, togo=togo, yl=yl, kick=False, kick_kind=None, new_series=False, unk=() if isinstance(st.get("off"), str) else ("offense",), how=how)


def tb_rules(season, x6cell, scrim_tb):
    """A season's touchback spots, each from its pinned rule: a free kick's from the season rules (rules.season_x6, the season's book; from 2024 the book names a second
    spot for a kick that first lands in the landing zone), any other touchback's from Rule 11 Section 6 (scrim_tb: season -> (yard line, where it was read),
    read by the caller from the season's book; a season missing reads unread)."""
    v = lambda k: int(x6cell[k]["value"]) if (k in x6cell and str(x6cell[k]["value"]).isdigit()) else None
    return dict(kick=v("touchback"), kick_lz=v("touchback_landing_zone"), two_spots="touchback_landing_zone" in x6cell, scrim=scrim_tb.get(season, (None, "unread"))[0])


def goal_half(yl, yd, by):
    """A distance foul of yd yards (enforced yards, more than 0) from the offense's yard line yl, by 'offense' or 'defense', that would carry the ball to or
    past the fouling team's goal line: the ball half the distance from yl to that goal (the book's half-the-distance article). None where yl is not on
    the field or yd is not a distance toward the fouling team's goal (the spot stays UNKNOWN)."""
    if not (_k(yl, yd) and by in ("offense", "defense") and 0 < yl < 100 and yd > 0): return None
    if by == "offense": return yl + (100 - yl) / 2 if yl + yd >= 100 else None
    return yl / 2 if yl - yd <= 0 else None


def int_end(y0, air, ret):
    """An interception's dead-ball spot as the interceptors' yard line: the catch at the passers' yard line less air_yards, the return toward the passers' goal."""
    return 100.0 - (y0 - air) - ret if _k(y0, air, ret) else None


def punt_end(y0, kd, ret):
    """A punt's dead-ball spot as the receivers' yard line."""
    return 100.0 - y0 + kd - ret if _k(y0, kd, ret) else None


def kick_end(y0, kd, ret):
    """A kickoff's dead-ball spot as the receivers' yard line (the kickoff row's yard line is the receivers')."""
    return y0 + kd - ret if _k(y0, kd, ret) else None


def _spot(team, end, how, miss):
    return series(team, end, how) if (_k(end) and 0 < end < 100) else unknown(team, miss)


def second(r, ev):
    """A combined event (v15 b): the play's text names a later recovery (its last 'RECOVERED by') by a team other than the one the event's own columns give
    the ball to: a second change of possession the row's yard columns do not place. The ball is that team's (the text's last recovery); the down, distance
    and yard line are UNKNOWN. A kick to come, a turnover on downs (7-3-2a) and a result already UNKNOWN are not changed."""
    pa = ev.get("poss_after")
    if not isinstance(pa, str) or r["kick"] or r["unk"] or r["off"] == pa or r["how"].startswith("turnover on downs") or r["how"].startswith("a loss of down"): return r
    return unknown(pa, "a second change of possession on the play (the text's last recovery): the spot is not in the row's yard columns (UNKNOWN)")


def after(st, ev, rb):
    """The state after one event: the event's own result (one), then a second change of possession the text names (second)."""
    return second(after_one(st, ev, rb), ev)


def after_one(st, ev, rb):
    """The state after one event as its own columns give it. st: the state before it (off, dfn, down, togo, yl); ev: the event's attributes; rb: the
    season's touchback spots (tb_rules). The order of the cases is the order of precedence."""
    k = ev["kind"]; off = st.get("off"); dfn = st.get("dfn")
    other = lambda t: dfn if t == off else (off if t == dfn else None)
    if k == "period start":
        return kick_to_come(ev.get("receiver"), "a period starts: a kickoff to come")
    if k == "try":
        recv = next_possession("try_or_field_goal", scorer=ev["team"], scored_on=ev["other"])[0]   # after a Try
        return kick_to_come(recv, "Try: a kick to come")
    if k == "kickoff":
        recv, kicker = ev["recv"], ev["kicker"]
        if ev.get("td"):
            sc = ev.get("scorer") or recv
            return kick_to_come(next_possession("try_or_field_goal", scorer=sc, scored_on=kicker if sc == recv else recv)[0], "kickoff returned for a touchdown: a Try and a kick to come")
        if isinstance(ev.get("rec_by"), str) and ev["rec_by"] == kicker:
            who = next_possession("kickers_recovery", team=kicker)[0]
            return _spot(who, ev.get("end"), "a free kick recovered by the kickers: their first down (7-3-1(e))", "a free kick recovered by the kickers: the spot is not in the row (UNKNOWN)")
        if ev.get("foul_unread"):
            return unknown(recv, "a kickoff with a foul: the spot is not in the row (UNKNOWN)")
        if ev.get("tb"):
            if rb.get("two_spots"):
                cond = ev.get("tb_cond"); spot = rb.get("kick") if cond == "in the air" else (rb.get("kick_lz") if cond == "landing zone" else None)
                if spot is None:
                    return unknown(recv, "kickoff touchback: the book names two spots and which one applies is not in the row (UNKNOWN)" if cond is None else "kickoff touchback: the spot unread from the book (UNKNOWN)")
            else:
                spot = rb.get("kick")
                if spot is None: return unknown(recv, "kickoff touchback: the season rules's spot unread (UNKNOWN)")
            return series(recv, 100 - spot, "kickoff touchback: the season rules's spot (the season's book)")
        return _spot(recv, ev.get("end"), "kickoff: where the return ended", "kickoff: the return's spot is not in the row (UNKNOWN)")
    # a snap: a scrimmage play, a punt or a field goal try
    if ev.get("td"):
        sc = ev.get("scorer") or off
        return kick_to_come(next_possession("try_or_field_goal", scorer=sc, scored_on=other(sc))[0], "touchdown: a Try and a kick to come")
    if k == "field_goal" and ev.get("made"):
        recv = next_possession("try_or_field_goal", scorer=off, scored_on=dfn)[0]   # after a field goal
        return kick_to_come(recv, "field goal: a kick to come")
    if ev.get("safety"):
        return kick_to_come(next_possession("safety", scorer=dfn, scored_on=off)[0], "safety: a free kick to come", "safety")
    down, togo, yl = st.get("down"), st.get("togo"), st.get("yl")
    if ev.get("offsetting_dead") and not rb.get("dead_counts", True):
        return unknown(off, "fouls offsetting after the ball is dead: the season's book does not state that the down counts (UNKNOWN)")
    if ev.get("offsetting"):   # v16 b: a double foul during a live ball (rb's double_replay: the season's book's article read and printed by the chain)
        if not rb.get("double_replay", True): return unknown(off, "fouls offsetting during the down: the season's book's double-foul article not read (UNKNOWN)")
        return same(st, down, togo, yl, "fouls offsetting during the down: the down replayed (3-8-4, the double-foul article)") if _k(down, togo, yl) else unknown(off, "fouls offsetting: the down's columns empty (UNKNOWN)")
    # offsetting_dead (v16 b): fouls offsetting after the ball is dead leave the play's result standing (the Dead Ball Foul article: the down counts); the result follows
    if k == "foul":
        by, yd, oc = ev.get("by"), ev.get("yards"), ev.get("outcome")
        if not (_k(yd, down, togo, yl) and by in ("offense", "defense") and isinstance(off, str)):
            return unknown(off, "a foul: penalty_yards, penalty_team or the down's columns empty (UNKNOWN)")
        why = rules.NEXT_DOWN[oc][1]
        yl2 = yl + yd if by == "offense" else yl - yd; mv = yd
        if not (0 < yl2 < 100):   # v19 r: the book's half-the-distance article where the ball would reach or pass the fouling team's goal line
            yl2 = goal_half(yl, yd, by)
            if yl2 is None: return unknown(off, "a foul: the enforced spot outside the field (UNKNOWN)")
            mv = abs(yl2 - yl); why = why + "; half the distance to the goal (the book's half-the-distance article)"
        if by == "offense":
            tg2 = togo + mv
            nd = next_down(down, oc)[0]
            if nd > 4:   # 3-8-2: four downs (a loss of down on 4th down)
                return series(dfn, 100 - yl2, "a loss of down on 4th down: turnover on downs (7-3-2a)")
            return same(st, nd, tg2, yl2, f"a foul by the offense: {why}")
        tg2 = togo - mv
        if oc == "def_award" or tg2 <= 0:
            return series(off, yl2, "a foul by the defense: a first down (7-3-1(b))")
        return same(st, next_down(down, oc)[0], tg2, yl2, f"a foul by the defense: {why}")
    if ev.get("foul_stand") is not None and k == "snap" and not ev.get("turnover"):   # v18 c: a foul on a play that stands
        return stand(st, ev, rb)
    if ev.get("foul_unread") and k in ("snap", "field_goal") and not ev.get("turnover"):
        return unknown(off, "a foul on the play: its enforcement spot is not in the play's columns (UNKNOWN)")
    if k == "snap" and ev.get("turnover"):
        team = ev.get("turn_team") or dfn; what = ev["turnover"]
        if ev.get("foul_unread"): return unknown(team, f"{what} with a foul: the spot is not in the row (UNKNOWN)")
        if ev.get("turn_tb"):
            sp = rb.get("scrim")
            return series(team, 100 - sp, f"{what}, touchback: Rule 11 Section 6's spot (the season's book)") if sp else unknown(team, f"{what}, touchback: Rule 11 Section 6's spot unread (UNKNOWN)")
        return _spot(team, ev.get("turn_end"), f"{what}: where the return ended", f"{what}: the spot is not in the row (UNKNOWN)")
    if k == "punt":
        recv = dfn
        if isinstance(ev.get("rec_by"), str) and ev["rec_by"] == off:
            return _spot(off, ev.get("end"), "a punt recovered by the kickers: their first down (7-3-1(d))", "a punt recovered by the kickers: the spot is not in the row (UNKNOWN)")
        if ev.get("foul_unread"): return unknown(recv, "a punt with a foul: the spot is not in the row (UNKNOWN)")
        if ev.get("tb"):
            sp = rb.get("scrim")
            return series(recv, 100 - sp, "punt, touchback: Rule 11 Section 6's spot (the season's book)") if sp else unknown(recv, "punt, touchback: Rule 11 Section 6's spot unread (UNKNOWN)")
        return _spot(recv, ev.get("end"), "punt: where the return ended", "punt: the return's spot is not in the row (UNKNOWN)")
    if k == "field_goal":
        return _spot(dfn, ev.get("end"), "missed field goal: where the defense takes the ball", "missed field goal: the spot (11-4-3) is not in its columns (UNKNOWN)")
    g = ev.get("gain")
    if not (_k(g, down, togo, yl) and isinstance(off, str)):
        return unknown(off, "the play's own columns empty (UNKNOWN)")
    end = yl - g
    if not (0 < end < 100):
        return unknown(off, "the play's result off the field with no score marked (UNKNOWN)")
    if end <= yl - togo:
        return series(off, end, "a first down: the line to gain reached (7-3-1(a))")
    nd = next_down(down, "next")[0]
    if nd > 4:   # 3-8-2: four downs
        return series(dfn, 100 - end, "turnover on downs (7-3-2a): 100 - the play's own result")
    return same(st, nd, togo - g, end, "the next down (3-8-5): the yard line less the gain")


# ---------------- v18 c: a foul on a play that stands ----------------
ENF_RX = re.compile(r"enforced at (?:the )?([A-Z]{2,3}) (\d{1,2})\b|enforced at (?:the )?(50)\b")


def enforced_at(clause, holder):
    """The spot one accepted foul's clause says it was enforced at ('enforced at NYJ 35'), as the yard line of the team holding the ball (holder);
    None when the clause names no spot (one reading, shared by the record's adapter and the engine's pool)."""
    m = ENF_RX.search(str(clause))
    if not m or not isinstance(holder, str): return None
    if m.group(3): return 50.0
    return float(100 - int(m.group(2))) if m.group(1) == holder else float(int(m.group(2)))


STAND_PREFIX = "a foul on a play that stands"
OFF_DEAD_BOOK = ("Unnecessary Roughness",)   # the offense's fouls rules.py's lists do not name, played by the season's Dead Ball Foul article where the
                                             # play stands and the foul is enforced at its end (the succeeding spot): the down counts


def stand(st, ev, rb):
    """The state after a scrimmage play that stands with one accepted foul on it (ev['foul_stand']: by 'offense'/'defense', yards (penalty_yards),
    name (penalty_type), award (first_down_penalty), spot (enforced_at of the foul's clause)). The play's end is the yard line less yards_gained; the foul
    is enforced from that end only where the text's own enforcement spot is that end (the two readings agree); a spot foul or a previous-spot enforcement
    (the readings differ) is UNKNOWN. Then, by family:
      the defense: a first down where first_down_penalty marks the award or the enforced spot reaches the line to gain (7-3-1(b), 14-1-2 Item 5); with
        neither, the next down where the foul is a dead ball foul by the season's book (taunting, 'a taunting foul that occurs at any time': the down
        counts), else UNKNOWN (the row does not say whether the down counts or is replayed);
      the offense: rules.LOSS_OF_DOWN, the next down (14-1-2 Item 2); rules.OFF_DURING, the down replayed from the enforced spot (14-1-2 Item 1,
        3-8-4), a first down where the enforced spot still reaches the line; rules.OFF_AFTER, the down counts (the Dead Ball Foul article, read in the
        season's book) from the succeeding spot, UNKNOWN after a down that made a first down (the article's Item 1 is not read); any other name UNKNOWN.
    A loss of down past 4th down is a turnover on downs (7-3-2a). v19 r: an enforcement that would carry the ball to or past the fouling team's goal line
    is placed half the distance from the play's end to that goal (goal_half)."""
    fs = ev["foul_stand"]; off, dfn = st.get("off"), st.get("dfn"); down, togo, yl = st.get("down"), st.get("togo"), st.get("yl")
    g, yd, by, name, sp = ev.get("gain"), fs.get("yards"), fs.get("by"), fs.get("name"), fs.get("spot")
    P = STAND_PREFIX
    if not (_k(g, down, togo, yl, yd) and isinstance(off, str) and by in ("offense", "defense")):
        return unknown(off, f"{P}: penalty_yards, penalty_team or the play's own columns empty (UNKNOWN)")
    end = yl - g; line = yl - togo
    if not (0 < end < 100): return unknown(off, f"{P}: the play's end off the field (UNKNOWN)")
    if not _k(sp): return unknown(off, f"{P}: its clause names no enforcement spot (UNKNOWN)")
    if abs(sp - end) >= 0.5:
        return unknown(off, f"{P}: the text's enforcement spot is not the play's end (a spot foul or the previous spot; UNKNOWN)")
    yl2 = end - yd if by == "defense" else end + yd
    if not (0 < yl2 < 100):   # v19 r: the book's half-the-distance article where the ball would reach or pass the fouling team's goal line
        yl2 = goal_half(end, yd, by)
        if yl2 is None: return unknown(off, f"{P}: the enforced spot outside the field (UNKNOWN)")
    if by == "defense":
        if fs.get("award") or yl2 <= line:
            return series(off, yl2, f"{P}, the defense's: a first down (7-3-1(b), 14-1-2 Item 5)")
        if name == "Taunting" and rb.get("taunt_dead") and rb.get("dead_counts", True):
            nd = next_down(down, "next")[0]
            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense's dead ball foul: the down counts, turnover on downs (7-3-2a)")
            return same(st, nd, yl2 - line, yl2, f"{P}, the defense's dead ball foul (taunting): the down counts (the Dead Ball Foul article)")
        if name in rules.DEF_NEXT:   # 14-1-2 Item 5 Exceptions (rules.py foul families): the defense's foul with no award, the next down
            nd = next_down(down, "next")[0]
            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense's with no award (14-1-2 Item 5 Exceptions): the next down, turnover on downs (7-3-2a)")
            return same(st, nd, yl2 - line, yl2, f"{P}, the defense's with no award (14-1-2 Item 5 Exceptions): the next down")
        if name in rules.DEF_SAME:   # 14-1-2 Item 5 Exceptions (rules.py foul families): the defense's foul with no award, the same down
            return same(st, down, yl2 - line, yl2, f"{P}, the defense's with no award (14-1-2 Item 5 Exceptions): the same down")
        return unknown(off, f"{P}, the defense's, no award and the line not reached: whether the down counts or is replayed is not in the row (UNKNOWN)")
    if name in rules.LOSS_OF_DOWN:
        nd = next_down(down, "loss_of_down")[0]
        if nd > 4: return series(dfn, 100 - yl2, f"{P}, the offense's: a loss of down on 4th down, turnover on downs (14-1-2 Item 2, 7-3-2a)")
        return same(st, nd, yl2 - line, yl2, f"{P}, the offense's: loss of down (14-1-2 Item 2)")
    if name in rules.OFF_DURING:
        if yl2 <= line: return series(off, yl2, f"{P}, the offense's during the down: the enforced spot reaches the line (7-3-1(a))")
        return same(st, next_down(down, "off_during")[0], yl2 - line, yl2, f"{P}, the offense's during the down: the down replayed from the enforced spot (14-1-2 Item 1, 3-8-4)")
    if name in rules.OFF_AFTER or name in OFF_DEAD_BOOK:   # OFF_DEAD_BOOK by the Dead Ball Foul article
        if not rb.get("dead_counts", True): return unknown(off, f"{P}, the offense's after the down: the season's book does not state that the down counts (UNKNOWN)")
        if end <= line: return unknown(off, f"{P}, the offense's after a down that made a first down: the Dead Ball Foul article's Item 1 not read (UNKNOWN)")
        nd = next_down(down, "off_after")[0]
        if nd > 4: return series(dfn, 100 - yl2, f"{P}, the offense's after the down: the down counts, turnover on downs (7-3-2a)")
        return same(st, nd, yl2 - line, yl2, f"{P}, the offense's after the down: the down counts (the Dead Ball Foul article)")
    return unknown(off, f"{P}, the offense's: its name is in none of rules.py's offense families (UNKNOWN)")


# ---------------- v19 part 2: a foul's yards by its article, from the spot it is enforced at ----------------
def foul_yards(N, side, spot, rnd):
    """The yards a foul moves the ball from its enforcement spot (the offense's yard line): N, its book's distance ('Loss of N yards'), or half the
    distance to the fouling team's goal line where N is more than half (the book's half-the-distance sentence: the offense's goal 100 - spot behind it,
    the defense's spot ahead); rnd: how the record marks a half that is not whole ('floor', 'ceil' or 'exact', measured by the caller). None where an
    input is unread."""
    if not (_k(N, spot) and side in ("offense", "defense") and rnd in ("floor", "ceil", "exact")): return None
    half = (100 - spot) / 2 if side == "offense" else spot / 2
    if N <= half: return float(N)
    return float(math.floor(half)) if rnd == "floor" else (float(math.ceil(half)) if rnd == "ceil" else float(half))


def spot_foul_yards(depth, yl):
    """Pass interference by the defense, a spot foul ('first down for the offensive team at the spot of the foul'): the spot is the foul's depth beyond the
    line of scrimmage (the record's penalty_yards on a wiped row where the ball did not go to the 1, its uncensored rows); a spot in the end zone puts the
    ball at the 1-yard line or half the distance to the goal from the previous spot, whichever is more beneficial (the season's book). None where the
    depth is unread or not beyond the line."""
    if not _k(depth, yl) or depth <= 0 or not (0 < yl < 100): return None
    return float(max(yl - 1, yl / 2)) if depth >= yl else float(depth)


YARD_CASES = [   # (case, the function, its inputs, what must come back)
    ("offensive holding at the 30 (the offense's own 70): 10 yards", foul_yards, (10, "offense", 30.0, "floor"), 10.0),
    ("offensive holding at the 95 (its own 5): half the distance, 2.5 marked down", foul_yards, (10, "offense", 95.0, "floor"), 2.0),
    ("the defense's holding at the 6: 5 yards would leave 1, half the distance 3", foul_yards, (5, "defense", 6.0, "floor"), 3.0),
    ("roughing the passer at the 20: 15 yards would pass half the distance, 10", foul_yards, (15, "defense", 20.0, "exact"), 10.0),
    ("a half not whole, marked up", foul_yards, (15, "defense", 17.0, "ceil"), 9.0),
    ("pass interference 25 yards downfield from the 60: the spot, 25 yards", spot_foul_yards, (25.0, 60.0), 25.0),
    ("pass interference in the end zone from the 12: the ball at the 1, 11 yards", spot_foul_yards, (15.0, 12.0), 11.0),
    ("pass interference with no depth read: unread", spot_foul_yards, (float("nan"), 40.0), None),
    ("pass interference in the end zone from the 1 (inside the 2): half the distance, 0.5 (more beneficial than the 1)", spot_foul_yards, (12.0, 1.0), 0.5),
    ("a 5-yard foul against the offense on its own 3: half the distance, 1.5, never rounded", foul_yards, (5, "offense", 97.0, "exact"), 1.5),
]


def run_yard_cases(fns=None):
    """Each yards case against the functions (or replacements by name): (cases, failures with what came back)."""
    bad = []
    for name, f, a, want in YARD_CASES:
        f = (fns or {}).get(f.__name__, f); got = f(*a)
        if got != want: bad.append((name, want, got))
    return len(YARD_CASES), bad


YARD_PLANTS = {"half the distance never applied": ("foul_yards", lambda N, side, spot, rnd: float(N) if _k(N) else None),
               "pass interference in the end zone not brought to the 1": ("spot_foul_yards", lambda depth, yl: float(depth) if _k(depth, yl) and depth > 0 else None),
               "the half yard rounded down": ("foul_yards", lambda N, side, spot, rnd: (lambda v: None if v is None else float(math.floor(v)))(foul_yards(N, side, spot, "exact")))}


# known-right cases, true by the rules they cite (built by hand, independent of the record and of the engine); each (case, state before, event, season's
# spots, the state that must come back: off, down, togo, yl, kick, the UNKNOWN parts)
_RB = dict(kick=25, kick_lz=None, two_spots=False, scrim=20)
_RB2 = dict(kick=30, kick_lz=20, two_spots=True, scrim=20)
_S0 = lambda dn, tg, yl: dict(off="AAA", dfn="BBB", down=dn, togo=tg, yl=yl)
FIXTURES = [
    ("3-8-5 the next down: 1st and 10 at the 75, 4 yards", _S0(1, 10, 75), dict(kind="snap", gain=4), _RB, ("AAA", 2, 6, 71, False, ())),
    ("7-3-1(a) a first down: 3rd and 2 at the 40, 3 yards", _S0(3, 2, 40), dict(kind="snap", gain=3), _RB, ("AAA", 1, 10, 37, False, ())),
    ("7-3-1 goal to go: 3rd and 5 at the 9, 5 yards", _S0(3, 5, 9), dict(kind="snap", gain=5), _RB, ("AAA", 1, 4, 4, False, ())),
    ("7-3-2a turnover on downs: 4th and 2 at the 40, 1 yard", _S0(4, 2, 40), dict(kind="snap", gain=1), _RB, ("BBB", 1, 10, 61, False, ())),
    ("11-3-4 a touchdown: the scored-upon team receives", _S0(2, 8, 8), dict(kind="snap", gain=8, td=True, scorer="AAA"), _RB, ("BBB", None, None, None, True, ())),
    ("11-5-1 a safety: the scoring team receives the free kick", _S0(2, 8, 98), dict(kind="snap", gain=-3, safety=True), _RB, ("BBB", None, None, None, True, ())),
    ("11-4-6 a field goal: the scored-upon team receives", _S0(4, 6, 20), dict(kind="field_goal", made=True), _RB, ("BBB", None, None, None, True, ())),
    ("11-6 a punt touchback: the receivers at their 20", _S0(4, 9, 45), dict(kind="punt", tb=True), _RB, ("BBB", 1, 10, 80, False, ())),
    ("11-6 an interception touchback: the interceptors at their 20", _S0(2, 10, 30), dict(kind="snap", turnover="interception", turn_tb=True), _RB, ("BBB", 1, 10, 80, False, ())),
    ("6 a kickoff touchback, one spot (the 25)", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", tb=True), _RB, ("BBB", 1, 10, 75, False, ())),
    ("6 a kickoff touchback, two spots, in the air (the 30)", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", tb=True, tb_cond="in the air"), _RB2, ("BBB", 1, 10, 70, False, ())),
    ("6 a kickoff touchback, two spots, which one unread", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", tb=True), _RB2, ("BBB", None, None, None, False, ("down", "distance", "yard line"))),
    ("a kickoff return: the receivers' 35 + 65 - 25", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", end=kick_end(35.0, 65.0, 25.0)), _RB, ("BBB", 1, 10, 75.0, False, ())),
    ("14-4-9 a false start: 2nd and 7 at the 60, 5 yards", _S0(2, 7, 60), dict(kind="foul", by="offense", yards=5, outcome="presnap_offense"), _RB, ("AAA", 2, 12, 65, False, ())),
    ("14-1-2 Item 5 Exceptions, the line reached: 3rd and 3 at the 50, offside 5", _S0(3, 3, 50), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 1, 10, 45, False, ())),
    ("14-1-2 Item 5 an award: 3rd and 9 at the 50, holding 5", _S0(3, 9, 50), dict(kind="foul", by="defense", yards=5, outcome="def_award"), _RB, ("AAA", 1, 10, 45, False, ())),
    ("14-1-2 Item 2 loss of down: 3rd and 5 at the 50, grounding 10", _S0(3, 5, 50), dict(kind="foul", by="offense", yards=10, outcome="loss_of_down"), _RB, ("AAA", 4, 15, 60, False, ())),
    ("14-1-2 Item 2 loss of down on 4th: turnover on downs", _S0(4, 5, 50), dict(kind="foul", by="offense", yards=10, outcome="loss_of_down"), _RB, ("BBB", 1, 10, 40, False, ())),
    ("3-8-4 fouls offsetting: the down replayed", _S0(2, 6, 44), dict(kind="snap", gain=12, offsetting=True), _RB, ("AAA", 2, 6, 44, False, ())),
    ("v16 b the Dead Ball Foul article: fouls offsetting after the ball is dead, the play stands: 2nd and 6 at the 44, 12 yards", _S0(2, 6, 44),
     dict(kind="snap", gain=12, offsetting_dead=True), _RB, ("AAA", 1, 10, 32, False, ())),
    ("v16 b fouls offsetting after a punt is dead: the punt stands (a touchback, Rule 11 Section 6)", _S0(4, 3, 42), dict(kind="punt", tb=True, offsetting_dead=True), _RB,
     ("BBB", 1, 10, 80, False, ())),
    ("v16 b the season's book not stating that the down counts: UNKNOWN", _S0(2, 6, 44), dict(kind="snap", gain=12, offsetting_dead=True), dict(_RB, dead_counts=False),
     ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    ("v16 b the season's double-foul article not read: a live-ball double foul UNKNOWN", _S0(2, 6, 44), dict(kind="foul", offsetting=True), dict(_RB, double_replay=False),
     ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    ("3-8-4 fouls offsetting on a down whose play they wiped: 3rd and 7 at the 35, replayed", _S0(3, 7, 35), dict(kind="foul", offsetting=True), _RB, ("AAA", 3, 7, 35, False, ())),
    ("14-1-2 Item 1, 3-8-4 the offense's foul during the play: 2nd and 4 at the 30, 10 yards", _S0(2, 4, 30), dict(kind="foul", by="offense", yards=10, outcome="off_during"), _RB, ("AAA", 2, 14, 40, False, ())),
    ("14-1-2 Item 5, 7-3-1(b) the defense's foul during the play with the award: 3rd and 8 at the 50, 23 yards", _S0(3, 8, 50), dict(kind="foul", by="defense", yards=23, outcome="def_award"), _RB, ("AAA", 1, 10, 27, False, ())),
    ("14-1-2 Item 5 Exceptions, short of the line: 2nd and 9 at the 40, 5 yards on the play", _S0(2, 9, 40), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 2, 4, 35, False, ())),
    ("a foul during the play, the enforced spot past the offense's goal line: half the distance, 96 to 98 (v17's case read UNKNOWN)", _S0(1, 10, 96), dict(kind="foul", by="offense", yards=10, outcome="off_during"), _RB, ("AAA", 1, 12.0, 98.0, False, ())),
    ("a fumble lost, its spot not in the row", _S0(1, 10, 60), dict(kind="snap", gain=3, turnover="fumble", turn_team="BBB"), _RB, ("BBB", None, None, None, False, ("down", "distance", "yard line"))),
    ("a foul on the play, its enforcement unread", _S0(1, 10, 60), dict(kind="snap", gain=3, foul_unread=True), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    ("11-6 a punt touchback with Rule 11-6 unread", _S0(4, 9, 45), dict(kind="punt", tb=True), dict(_RB, scrim=None), ("BBB", None, None, None, False, ("down", "distance", "yard line"))),
    ("v15 b a combined event: an interception, the interceptor's fumble recovered by the passers", _S0(2, 10, 40), dict(kind="snap", turnover="interception", turn_team="BBB",
     turn_end=55.0, poss_after="AAA"), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    ("v15 b a combined event: a punt return fumbled, recovered by the kickers (7-3-1(d))", _S0(4, 9, 45), dict(kind="punt", end=70.0, poss_after="AAA"), _RB,
     ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    ("v15 b the text's last recovery by the team the columns give the ball to: unchanged", _S0(2, 10, 40), dict(kind="snap", turnover="fumble", turn_team="BBB", turn_end=62.0,
     poss_after="BBB"), _RB, ("BBB", 1, 10, 62.0, False, ())),
    ("7-3-2a a turnover on downs stands whoever recovers a fumble on the play", _S0(4, 5, 40), dict(kind="snap", gain=2, poss_after="AAA"), _RB, ("BBB", 1, 10, 62, False, ())),
    # v18 c: a foul on a play that stands
    ("7-3-1(b) the defense's report mask after a 6-yard run, 1st and 10 at the 70: 15 yards from the end, a first down", _S0(1, 10, 70),
     dict(kind="snap", gain=6, foul_stand=dict(by="defense", yards=15, name="Face Mask", award=True, spot=64.0)), _RB, ("AAA", 1, 10, 49, False, ())),
    ("the Dead Ball Foul article: the offense's taunting after a 4-yard gain, 2nd and 10 at the 60: the down counts", _S0(2, 10, 60),
     dict(kind="snap", gain=4, foul_stand=dict(by="offense", yards=15, name="Taunting", award=False, spot=56.0)), dict(_RB, dead_counts=True), ("AAA", 3, 21, 71, False, ())),
    ("14-1-2 Item 1, 3-8-4 offensive holding at the end of a 12-yard run, 2nd and 15 at the 50: the down replayed from the enforced spot", _S0(2, 15, 50),
     dict(kind="snap", gain=12, foul_stand=dict(by="offense", yards=10, name="Offensive Holding", award=False, spot=38.0)), _RB, ("AAA", 2, 13, 48, False, ())),
    ("7-3-1(a) offensive holding at the end of a 30-yard run, 2nd and 5 at the 60: the enforced spot still past the line, a first down", _S0(2, 5, 60),
     dict(kind="snap", gain=30, foul_stand=dict(by="offense", yards=10, name="Offensive Holding", award=False, spot=30.0)), _RB, ("AAA", 1, 10, 40, False, ())),
    ("14-1-2 Item 2 intentional grounding, 3rd and 7 at the 40, enforced at the previous spot: the next down", _S0(3, 7, 40),
     dict(kind="snap", gain=0, foul_stand=dict(by="offense", yards=10, name="Intentional Grounding", award=False, spot=40.0)), _RB, ("AAA", 4, 17, 50, False, ())),
    ("a spot foul: the text's enforcement spot not the play's end, UNKNOWN", _S0(1, 10, 70),
     dict(kind="snap", gain=20, foul_stand=dict(by="offense", yards=10, name="Offensive Holding", award=False, spot=60.0)), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    ("the defense's foul with no award and the line not reached: UNKNOWN (counts or replayed not in the row)", _S0(3, 12, 50),
     dict(kind="snap", gain=2, foul_stand=dict(by="defense", yards=5, name="Illegal Use of Hands", award=False, spot=48.0)), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    ("the offense's dead ball foul after a down that made a first down: Item 1 not read, UNKNOWN", _S0(3, 2, 40),
     dict(kind="snap", gain=5, foul_stand=dict(by="offense", yards=15, name="Unsportsmanlike Conduct", award=False, spot=35.0)), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),
    # v19 part 2
    ("14-1-2 Item 5 Exceptions: the defense's delay of game on a play that stands, 1st and 10 at the 92, 2 yards: the next down", _S0(1, 10, 92),
     dict(kind="snap", gain=2, foul_stand=dict(by="defense", yards=5, name="Defensive Delay of Game", award=False, spot=90.0)), _RB, ("AAA", 2, 3, 85, False, ())),
    ("14-1-2 Item 5 Exceptions: too many players on a play that stands, 3rd and 9 at the 50, 1 yard: the same down", _S0(3, 9, 50),
     dict(kind="snap", gain=1, foul_stand=dict(by="defense", yards=5, name="Defensive Too Many Men on Field", award=False, spot=49.0)), _RB, ("AAA", 3, 3, 44, False, ())),
    ("pass interference in the end zone from the 10 (a spot foul): first down at the 1, goal to go", _S0(3, 8, 10),
     dict(kind="foul", by="defense", yards=9, outcome="def_award"), _RB, ("AAA", 1, 1, 1, False, ())),
    # the book's half-the-distance article where the enforcement would carry the ball past a goal line
    ("the book's half-the-distance article: a 15-yard foul against the offense on its own 10, 2nd and 10: the ball on its own 5, the down replayed",
     _S0(2, 10, 90), dict(kind="foul", by="offense", yards=15, outcome="off_during"), _RB, ("AAA", 2, 15.0, 95.0, False, ())),
    ("the book's half-the-distance article: the defense's 5-yard foul at its own 1, 3rd and goal: the ball at the half-yard line, the same down",
     _S0(3, 1, 1), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 3, 0.5, 0.5, False, ())),
    # a half-yard spot kept exactly; s3: the offense's unnecessary roughness on a play that stands, the Dead Ball Foul article
    ("v19 s1 the book's half-the-distance article: a 5-yard foul against the offense on its own 3, 2nd and 10: the ball on its own 1.5, the down replayed from there",
     _S0(2, 10, 97), dict(kind="foul", by="offense", yards=5, outcome="off_during"), _RB, ("AAA", 2, 11.5, 98.5, False, ())),
    ("v19 t1 half the distance again: the defense's 5-yard foul at its own 1.5, 1st and goal: the ball at the 0.75, the same down",
     _S0(1, 1.5, 1.5), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 1, 0.75, 0.75, False, ())),
    ("v19 t1 and again: the defense's 5-yard foul at its own 0.75, 1st and goal: the ball at the 0.375, the same down",
     _S0(1, 0.75, 0.75), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 1, 0.375, 0.375, False, ())),
    ("v19 t1 the offense's own 1.5: a 5-yard foul against the offense on its own 1.5, 2nd and 10: the ball on its own 0.75, the down replayed",
     _S0(2, 10, 98.5), dict(kind="foul", by="offense", yards=5, outcome="off_during"), _RB, ("AAA", 2, 10.75, 99.25, False, ())),
    ("v19 s3 the Dead Ball Foul article: the offense's unnecessary roughness at the end of a 4-yard gain, 2nd and 10 at the 60, enforced at the end: the down counts",
     _S0(2, 10, 60), dict(kind="snap", gain=4, foul_stand=dict(by="offense", yards=15, name="Unnecessary Roughness", award=False, spot=56.0)), dict(_RB, dead_counts=True),
     ("AAA", 3, 21, 71, False, ())),
]


def run_fixtures(fn):
    """Each known-right case against a transition function: (cases, failures with what came back)."""
    bad = []
    for name, st, ev, rb, want in FIXTURES:
        o = fn(st, ev, rb); got = (o["off"], o["down"], o["togo"], o["yl"], o["kick"], tuple(o["unk"]))
        if got != want: bad.append((name, want, got))
    return len(FIXTURES), bad


def injected_fault_stand(old, new):
    """A changed copy of stand() (v18 c's injected_fault): stand() and after_one() run from a copy of this module's names with the one line replaced."""
    import inspect
    src = inspect.getsource(stand)
    if src.count(old) != 1: raise record.DataGap(f"an injected fault's anchor is in stand() {src.count(old)} times")
    ns = dict(globals()); exec(src.replace(old, new), ns); exec(inspect.getsource(after_one), ns)
    return lambda st, ev, rb: second(ns["after_one"](st, ev, rb), ev)


def injected(src, old, new):
    """A changed copy of the transition (an injected fault): its source with one line replaced, run in a copy of this module's names."""
    if src.count(old) != 1: raise record.DataGap(f"an injected fault's anchor is in the transition {src.count(old)} times")
    ns = dict(globals()); exec(src.replace(old, new), ns)
    return lambda st, ev, rb: second(ns["after_one"](st, ev, rb), ev)


# each injected_fault: one line of after_one replaced; each must make a known-right case fail (an injected fault that fails none means the cases cannot see that line)
PLANTS = {"the next down not counted (3-8-5)": ('    nd = next_down(down, "next")[0]\n    if nd > 4:   # 3-8-2: four downs', '    nd = down\n    if nd > 4:   # 3-8-2: four downs'),
          "the yards copied whole past the goal line (no half-the-distance article)": ("            yl2 = goal_half(yl, yd, by)\n", "            yl2 = None\n"),
          "a state that holds only half yards (the spot rounded to the nearest half)": ("            yl2 = goal_half(yl, yd, by)\n", "            yl2 = goal_half(yl, yd, by); yl2 = None if yl2 is None else round(2 * yl2) / 2\n"),
          "the half yard rounded (the ball put on a whole yard)": ("            yl2 = goal_half(yl, yd, by)\n", "            yl2 = goal_half(yl, yd, by); yl2 = None if yl2 is None else float(round(yl2))\n"),
          "a punt touchback at the 25 (Rule 11 Section 6 says the 20)": ('return series(recv, 100 - sp, "punt, touchback', 'return series(recv, 100 - 25, "punt, touchback')}
# v18 c's injected_fault, in stand(): the defense's foul enforced toward the defense (the yards added, not taken)
STAND_PLANTS = {"the defense's foul on a play that stands enforced the wrong way": ('    yl2 = end - yd if by == "defense" else end + yd\n', '    yl2 = end + yd if by == "defense" else end + yd\n'),
                "the offense's unnecessary roughness not read by the Dead Ball Foul article": ("    if name in rules.OFF_AFTER or name in OFF_DEAD_BOOK:", "    if name in rules.OFF_AFTER:"),
                "14-1-2 Item 5 Exceptions' next down read as the same down": ('            nd = next_down(down, "next")[0]\n            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense\'s with no award',
                                                                               '            nd = down\n            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense\'s with no award')}
