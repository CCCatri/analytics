"""engine.py - engine v0 (v4: the season rules read from each season's rule book), to engine-legality.md. Games played out snap by snap on rules.py (snap kinds to the season rules) and league-wide rates, written in the record's columns.
Not product: the engine is the floor the engine-vs-record stage grades. Decision when it runs: NO_CHANGE.
Inputs (engine-legality.md section 1): rules.py; for season s, league-wide rates read from the five other unsealed seasons (never s, never 2022); the schedule
(teams, season, week, home side, game type). Bins: down, distance (1-3, 4-6, 7-10, 11+), field (own 1-20, own 21-50, opp 49-21, opp 20-1), time (normal,
last 2:00 of the first half, last 5:00 of the game, overtime), score (behind 9+, behind 1-8, tied, ahead 1-8, ahead 9+). A bin with fewer than MIN_BIN plays
is merged with the next coarser bin (score dropped, then time, then distance, then field, then down); every pool prints its merges.
Rates are drawn as whole recorded outcomes from the bin's plays (a recorded play's kind, yards, completion, interception, fumble lost, out of bounds).
Writes out/sim_games.csv (stamped on line 1 with this file's sha, the targets' sha, rules.py's sha, out/season_rules.csv's sha and the seed) and
out/engine_checks.csv (every check's count, stamped). The record checks (check_possessions, check_clock, check_downs) read the engine's games through record.raw_frame, the record's one reader,
pointed at the engine's rows: the only change is the input. v0's choices the targets do not fix are printed by choices()."""
import hashlib, os, re, sys, io, json, datetime
from collections import Counter, defaultdict
import numpy as np, pandas as pd
import record, policy, rules
import check_possessions, check_clock, check_downs
from rules import (SNAP_KINDS, PRESNAP_OFFENSE, OFF_DURING, LOSS_OF_DOWN, OFF_AFTER, DEF_AWARD, DEF_NEXT, next_down, next_possession, clock_class,
                   oob_window, foul_window, warns, beyond)

import transition as _T   # the one transition (transition.py, product), shared with the record's rebuild
_TRANS = _T.after
SCRIM_TB = {}   # season -> (Rule 11 Section 6's spot, where read): set by the caller from each season's book; a season missing reads the spot unread
_TBR = lambda season, X: _T.tb_rules(season, X, SCRIM_TB)
BOOKY = {}   # (season, foul name, side) -> (yards, an automatic first down, where read): the foul's Penalty: line in the season's book, set by the caller; a foul missing is UNSUPPORTED when drawn
ENF_CLOCK = {}   # v19 y1: season -> (the seconds the offense has to snap after a penalty enforcement, beginning with the Referee's whistle (Rule 4 Section 6 Article 2 (e)), where read): set by the caller from each season's book; a season missing has no restart rows (a restart drawn for it is UNSUPPORTED)
SELF_PATH = os.path.abspath(__file__)
SELF = hashlib.sha256(open(SELF_PATH, "rb").read()).hexdigest()[:12]
TARGETS = "acceptance-criteria/engine-legality.md"
OUT_SIM = "out/sim_games.csv"
OUT_CHECKS = "out/engine_checks.csv"
SEED = 20261026
MIN_BIN = 30
R1A = True        # the engine-vs-record stage R1a (engine-vs-record.md the engine-vs-record stage v2 d): how long each stretch lasts. False plays v0's clock exactly (checked byte for byte by the run)
PACE_SPLIT = {}   # the engine-vs-record stage v4 a: the clock classes whose stretches in the last 2:00 of a half are keyed by score state (one test per class, each keyed cell MIN_BIN or more)
PLAY_CLOCK = 40   # 4-6-1: the 40 seconds rules.play_clock reads; with this much game clock or less left after a play on a running clock, the offense decides whether to snap again before 0:00
QE_BAND = 10      # the engine-vs-record stage v4 e: the quarter-end cell's coarser width in seconds left (a chosen number, compared at 5, 10 and 20 by the run)
R1B = True        # the engine-vs-record stage R1b (engine-vs-record.md the engine-vs-record stage v4 c): how often the clock stops. False plays R1a's clock exactly
R1D = True        # the engine-vs-record stage v12-v13 (the race, v10 b): the seconds after a running-clock play, the stopped-clock timeouts and the pre-snap fouls from the fitted race; False plays the floor (R1a+R1b) exactly
RACE_CHUNK = 48    # computing only: the walk asks the race for this many seconds at a time
RACE_STOP_ACTS = ["snap STOP", "snap PARTIAL", "foul", "kickoff", "try", "timeout", "two-minute warning", "start of the quarter"]
RUNOFF_RESTART = {}   # the engine-vs-record stage v14 d: 15-5-2 per season's book: True when its printed article adds 'or a clock that would have otherwise restarted before the next snap'
SIM_SEASONS = [s for s in policy.SEASONS if s != policy.HOLD]
CALL = set(policy.CALL_KINDS)
HALF_TIMEOUTS = 3       # rule text (Rule 4, Section 5), not read from the book in this run (overtime's timeouts are the season rules's, quoted from Rule 16)
COLS = ["game_id", "play_id", "order_sequence", "season", "week", "season_type", "home_team", "away_team", "posteam", "defteam", "qtr",
        "quarter_seconds_remaining", "game_seconds_remaining", "time_of_day", "end_clock_time", "play_type", "down", "ydstogo", "yardline_100",
        "yards_gained", "desc", "fixed_drive", "pass", "rush", "sack", "qb_scramble", "complete_pass", "incomplete_pass", "interception", "fumble_lost",
        "out_of_bounds", "two_point_attempt", "touchdown", "pass_touchdown", "rush_touchdown", "td_team", "return_touchdown", "safety", "touchback",
        "penalty", "penalty_team", "penalty_type", "first_down", "first_down_penalty", "timeout", "replay_or_challenge", "own_kickoff_recovery",
        "fumble_recovery_1_team", "fumble_recovery_2_team", "field_goal_result", "extra_point_result", "two_point_conv_result",
        "defensive_two_point_conv", "defensive_extra_point_conv", "passer_player_id", "receiver_player_id", "rusher_player_id",
        "lateral_receiver_player_id", "lateral_rusher_player_id", "lateral_receiving_yards", "lateral_rushing_yards",
        "home_score", "away_score", "total_home_score", "total_away_score"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def nan(x):
    return x is None or (not isinstance(x, str) and pd.isna(x))


def one(x):
    return (not nan(x)) and x == 1


def choices():
    return [
        "MIN_BIN = 30 plays: the one number the targets leave open ('too few plays'); a bin under it draws from the next coarser bin.",
        "Fouls played (one per stretch between snaps, families of foul families by the record's foul name and side): F1 offense before the snap (False Start, 5 yards, the down replayed);"
        " F2 defense before the snap, a name outside DEF_AWARD (Defensive Offside, 5 yards, the down replayed unless the line is reached); F3 offense during the play,"
        " the play wiped (Offensive Holding, 10 yards from the previous spot); F4 defense during the play, DEF_AWARD, the play wiped (Defensive Holding, 5 yards and a first down);"
        " F5 loss of down (Intentional Grounding, 10 yards from the previous spot, the pass incomplete); F6 offense after the whistle on a play that stands"
        " (Unsportsmanlike Conduct, 15 yards from the end spot). Every yardage is cut to half the distance to the goal, in whole yards. Every other recorded foul is"
        " not played and is counted by name (fouls on kicks and Tries, defensive fouls that leave the play standing, pass interference, both-teams fouls).",
        "F6 is not played on a play that scores, turns the ball over, ends in a safety, or fails on 4th down; each such draw is counted.",
        "Turnovers, punts, missed field goals and kickoffs place the next snap at a spot drawn from the record's next snaps in the same field bin; returns for a"
        " touchdown, muffs kept by the kicking team and fumbles on returns are not played (counted). A kickoff touchback is placed at the season rules's rule spot (quoted from the"
        " season's book: the 25 through 2023, the 30 in 2024, the 35 in 2025); from 2024 the book's second spot, the 20 for a kick that first lands in the acceptance"
        " zone, is not played: every engine touchback is at the first spot (the record's touchbacks at the 20 are printed beside it).",
        "A kick is an onside try when its text says 'onside' (E1a v2 a: section 0's short kicks without it were squibs, played as kickoffs). When one may be tried is"
        " the season rules's rule, quoted from the season's book: 2019-2023 any free kick (no article names an onside kick), 2024 the 4th period by a team trailing, 2025 any"
        " period by a team trailing; within what the rule allows, how often one is tried is the five other seasons' rate in the (period, score) cell.",
        "Timeouts are drawn after a snap by (time, score), for the offense or the defense of the next snap, while the team has one left: three a half in regulation (rule text, Rule 4 Section 5, not read in this run);"
        " in overtime the season rules's quoted timeouts (two in the regular-season period, three in each postseason overtime half).",
        "Clock: the class after each play is rules.clock_class over the play's own events (the same events check_clock reads); STOP holds the clock to the next snap, PARTIAL"
        " restarts it after a stopped part drawn from the record's PARTIAL stretches, RUN runs it. After a foul outside the windows on a running clock (4-3-2e) the"
        " clock is stopped for the enforcement and starts on the Referee's whistle, the snap within the season's book's play clock of it (4-6-2e): the stopped part"
        " and the game seconds to the snap drawn together from the record's restarts after such fouls (v19 y1). A timeout, a foul in its window, or the two-minute warning stops a"
        " running clock at the moment it happens.",
        "Real time: each play's length (end stamp minus start stamp) and each gap between rows are drawn from the stamped seasons (2023-2025) other than s; after the"
        " two-minute warning the gap to the next snap is the record's warning-stretch gap less the clock that ran before the warning (redrawn while not positive, counted).",
        "Overtime is the season rules's rules, each quoted from the season's book's Rule 16 (2019 from the 2020 book; 2025 from the 2025 page): the period length (600 regular"
        " season, 900 postseason), the possession rule (a first-possession touchdown ends it, or both teams possess first), and the timeouts (two a team in the regular"
        " season's period; three a team in each postseason overtime half, a half being two periods). A third postseason overtime period starts with a kickoff by the"
        " team that received to start overtime (the choice is not in the record). R7's measured values sit beside the rules and are never read by the engine.",
        "E1a v2 c: these rates, from the five other seasons, are a look back used for the legality test only; from E1b on a forecast reads only what was known before kickoff.",
        "A field goal's distance is its yard line plus 17 (the end zone's 10 yards and a 7-yard snap); the record's text distance keys its make rate.",
        "The coin toss, the second-half choice and the overtime toss are not in the record: v0 draws the toss at even odds; the first half's receiver kicks the second half.",
        "Section 4 stopped clock, read as: on a STOP stretch the game clock falls by no more than the plays run on it (each its end stamp minus its start stamp: the snap,"
        " any no-play that ran a play, kickoffs and Tries) plus the real time before the first stopping row when the snap's own events do not stop the clock,"
        " plus 1 second; a STOP stretch with no stopping event found fails.",
        "R1a (when R1A is on): the gap to the next snap is the record's gap in the stretch's (class, time bin, score) cell, score only in the last 2:00 of a half and"
        " only for the classes PACE_SPLIT names; a PARTIAL stretch takes its gap and its stopped part from one recorded stretch (4-3-2a); after a play that leaves"
        " PLAY_CLOCK game seconds or fewer on a running clock in quarters 1-4, whether a snap comes before 0:00 and the seconds before it are drawn from the"
        " record's same moments (4-6-1), by the exact seconds left; a cell under MIN_BIN takes the next coarser cell, as every pool, and for the seconds left the coarser"
        " cell is its QE_BAND-second band (a chosen width).",
        "R1b (when R1B is on): a snap's kind and its clock flags (incomplete 4-4f, out of bounds 4-3-2a) are drawn first from the record's snaps in the same"
        " (time bin with the last 2:00 of the game apart, late score, down, distance) cell, merged coarser as score, distance, down, then time are dropped; the"
        " outcome is then drawn from the snaps of that kind and those flags in v0's bins. A timeout after a snap is drawn from the record's snaps in the same (time"
        " bin, late score, the clock class of the snap's own events, which teams have one left) cell (4-5-1), regulation only; overtime keeps v0's draw. The"
        " two-minute warning (3-41) is v0's, by rule.",
    ]


# ---------------- bins ----------------
def dist_bin(t):
    return "1-3" if t <= 3 else ("4-6" if t <= 6 else ("7-10" if t <= 10 else "11+"))


def field_bin(yl):
    return "own 1-20" if yl >= 80 else ("own 21-50" if yl >= 50 else ("opp 49-21" if yl >= 21 else "opp 20-1"))


MARK_INSIDE1 = None   # v34 ad0 (b): the yard line the record writes a spot inside the 1 as, set by the caller from the record's own count of snaps written below the 1 (None: the spot's floor)


def _ylk(yl):
    """v34 ad1: the whole yard a spot keys the yards-to-goal levels at: its floor; a spot inside the 1 at the yard line the record writes it as (MARK_INSIDE1). The spot itself stays exact."""
    y = float(yl); w = int(np.floor(y))
    return MARK_INSIDE1 if (0 < y < 1 and MARK_INSIDE1 is not None) else w


def yl20_bin(yl):
    """ab1: inside the opponent's 20, the yard line itself (the record's marking: whole yards toward the goal, as Game.mark writes it); outside, the field bin (today's cell)."""
    w = _ylk(yl)   # v34 ad1
    return w if 1 <= w <= 20 else field_bin(yl)


def yl5in_bin(yl):
    """v33 (ac addition 2): the 5-yard cell inside the opponent's 20 (1-5, 6-10, 11-15, 16-20), None outside it: a level keyed by it holds no bin outside the 20 (the rows there carry no key and pandas groups none), so no draw outside the 20 resolves at it."""
    w = _ylk(yl)   # v34 ad1
    return yl5_bin(yl) if 1 <= w <= 20 else None


def yl20in_bin(yl):
    """v36 af1: the yard line inside the opponent's 20, None outside it (as yl5in): a level keyed by it alone holds no bin outside the 20."""
    w = _ylk(yl)
    return w if 1 <= w <= 20 else None


def zone4_bin(yl):
    """v37 ag0: the fourth-down zone: the 1, 2-3, 4-5, 6-10, 11-20, opp 21-40, the 41-50, own side."""
    w = _ylk(yl)
    return "the 1" if w <= 1 else ("2-3" if w <= 3 else ("4-5" if w <= 5 else ("6-10" if w <= 10 else ("11-20" if w <= 20 else ("opp 21-40" if w <= 40 else ("the 41-50" if w <= 50 else "own side"))))))


def dist4_bin(t):
    """v37 ag0, ag1: the distance in four bins, 1, 2-3, 4-6, 7+ (a fraction to the bin above its whole yard: 1.5 is 2-3)."""
    t = float(t)
    return "1" if t <= 1 else ("2-3" if t <= 3 else ("4-6" if t <= 6 else "7+"))


def ylw_bin(yl):
    """v37 ag1: the yard line in whole yards, 1-99, as the record writes it (_ylk)."""
    return min(max(_ylk(yl), 1), 99)


def ycell_bin(yl):
    """v37 ag1: 5-yard cells inside the opponent's 20, 10-yard cells outside it (21-30 ... 91-99)."""
    w = ylw_bin(yl)
    if w <= 20: return "1-5" if w <= 5 else ("6-10" if w <= 10 else ("11-15" if w <= 15 else "16-20"))
    lo = (w - 1) // 10 * 10 + 1
    return f"{lo}-{min(lo + 9, 99)}"


def yl5_bin(yl):
    """ab1: inside the opponent's 20, the 5-yard cell (1-5, 6-10, 11-15, 16-20); outside, the field bin (today's cell)."""
    w = _ylk(yl)   # v34 ad1
    return ("1-5" if w <= 5 else ("6-10" if w <= 10 else ("11-15" if w <= 15 else "16-20"))) if 1 <= w <= 20 else field_bin(yl)


def time_bin(q, qs):
    if q >= 5: return "overtime"
    if q == 2 and qs <= 120: return "last 2:00 of the first half"
    if q == 4 and qs <= 300: return "last 5:00 of the game"
    return "normal"


def score_bin(d):
    return "behind 9+" if d <= -9 else ("behind 1-8" if d < 0 else ("tied" if d == 0 else ("ahead 1-8" if d <= 8 else "ahead 9+")))


def late_half(q, qa):
    """the engine-vs-record stage v2 a: the last 2:00 of a half (quarters 2 and 4)."""
    return q in (2, 4) and qa <= 120


def pace_score(cls, q, qa, diff):
    """R1a: a stretch's score key, the score state of the team with the ball in the last 2:00 of a half for a class PACE_SPLIT keys by it, else '-'."""
    return score_bin(diff) if PACE_SPLIT.get(cls) and late_half(q, qa) else "-"


def tb2(q, qa):
    """R1b: the time bins with the last 2:00 of the game apart from the rest of its last 5:00."""
    return "last 2:00 of the game" if q == 4 and qa <= 120 else time_bin(q, qa)


def late_score(q, qa, diff):
    """R1b: the score state of the team with the ball in the last 2:00 of a half, else '-'."""
    return score_bin(diff) if late_half(q, qa) else "-"


FULL = [("down", "dist", "field", "time", "score"), ("down", "dist", "field", "time"), ("down", "dist", "field"), ("down", "field"), ("down",), ()]
FULL_YL = [("down", "dist", "yl20", "time", "score"), ("down", "dist", "yl5", "time", "score"), ("down", "dist", "yl5", "time"), ("down", "dist", "yl5"), ("down", "yl5"), ("yl5in",)] + FULL   # v33 (ac and its additions 1, 2): inside the 20 the yards-to-goal key is the last key dropped: the yard line, then the 5-yard cell through the time, score, distance and down merges, then the 5-yard cell alone (yl5in: None outside the 20, so it holds no bin there and every draw outside the 20 resolves where it does today), then today's field-cell levels
PLAY2_LV = [("kind", "inc_k", "ob_k") + l for l in [("down", "dist", "yl20", "time", "score"), ("down", "dist", "yl20", "time"), ("down", "dist", "yl20"), ("down", "yl20"), ("yl20in",)] + FULL_YL[1:6]] + [("kind", "yl5in")] + [("kind", "inc_k", "ob_k") + l for l in FULL]   # v36 af1: inside the 20 the yard line kept ahead of time and score (then the yard line alone, yl20in: None outside the 20), then ac1's 5-yard-cell levels as accepted, (kind, 5-yard cell), the field-cell levels; outside the 20 each new level repeats a accepted one in the accepted order


def _hy(v):
    """v19 s1, t1: a yard count kept exactly: a whole number as an int, a fraction (1.5, 0.75, 0.375: halves of halves, exact in a float) as a float."""
    v = float(v)
    return int(v) if v == int(v) else v


def _yt(v):
    """v19 s1, t1: a yard count in a play's text: '15', or the exact fraction ('1.5', '0.75')."""
    return str(_hy(v))


class Pool:
    """Recorded outcomes by bin; a draw takes the finest level whose bin holds MIN_BIN or more, the coarsest level always."""
    def __init__(self, name, frame, cols, levels, last_any=False):
        self.name, self.cols, self.levels, self.last_any = name, cols, levels, last_any   # last_any: the last level is drawn from whatever its count (a drawn kind keeps its kind)
        frame = frame.reset_index(drop=True)
        self.vals = frame[cols].to_numpy(dtype=object) if len(frame) else np.empty((0, len(cols)), dtype=object)
        self.tab = []
        for lev in levels:
            if lev and len(frame):
                g = frame.groupby(list(lev), sort=False).indices
                self.tab.append({(k if isinstance(k, tuple) else (k,)): v for k, v in g.items()})
            else:
                self.tab.append({(): np.arange(len(frame))})
        self.n = len(frame); self.used = Counter()
        self.small = [sum(1 for v in t.values() if len(v) < MIN_BIN) for t in self.tab]; self.nbins = [len(t) for t in self.tab]

    def draw(self, rng, key, ok=None):
        for i, lev in enumerate(self.levels):
            idx = self.tab[i].get(tuple(key[d] for d in lev))
            if idx is not None and len(idx) and (len(idx) >= MIN_BIN or not lev or (self.last_any and i == len(self.levels) - 1)):
                if ok is not None:   # an impossible row has probability 0: the cell (chosen by its full count, as before) conditioned on its possible rows
                    idx = idx[ok(self.vals[idx])]
                    if not len(idx): continue
                self.used[i] += 1; self.last = i   # ac0: the level this draw resolved at (read by the caller's counters)
                v = self.vals[idx[rng.integers(len(idx))]]
                return dict(zip(self.cols, v))
        raise record.DataGap(f"engine pool {self.name}: no recorded outcome at any level for {key}")

    def merges(self):
        return (f"{self.name}: outcomes {self.n} | bins per level {self.nbins} | bins under {MIN_BIN} per level {self.small} | draws per level "
                f"{[self.used[i] for i in range(len(self.levels))]} (level 0 finest)")


# ---------------- the record, read for rates ----------------
EXTRA_T = {}
for _d in (check_possessions.EXTRA, check_downs.EXTRA):
    EXTRA_T.update(_d)
for _k in ("quarter_seconds_remaining", "out_of_bounds", "touchback", "time_of_day", "end_clock_time", "replay_or_challenge"):
    EXTRA_T[_k] = check_clock.TYPES[_k]
for _k in list(EXTRA_T):
    if _k in record.EVENT_COLUMNS and _k not in ("game_id", "play_id"):
        del EXTRA_T[_k]


def load(season):
    """One season of the record (or of the engine, when raw_frame points at it): record.events joined to the extra columns check_possessions, check_clock and check_downs read."""
    ev = record.events(season)
    ex = record.typed(record.raw_frame(policy.PBP_FILE.format(season=season), list(EXTRA_T), f"engine {season}"), EXTRA_T, f"engine {season}")
    d = ev.merge(ex, on=["game_id", "play_id"], how="inner", validate="one_to_one")
    if len(d) != len(ev) or len(d) != len(ex):
        raise record.DataGap(f"engine {season}: events {len(ev)} and extras {len(ex)} do not join one-to-one ({len(d)})")
    for c in d.columns:
        if str(d[c].dtype) == "Int64":
            d[c] = d[c].to_numpy(dtype=float, na_value=np.nan)
    d = d.sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
    for col, k in (("time_of_day", "W"), ("end_clock_time", "E")):
        p = [check_clock.parse(v) for v in d[col]]
        p = [(np.nan, np.nan, np.nan) if t is None else t for t in p]
        d[k + "_s"] = [t[0] for t in p]; d[k + "_r"] = [t[1] for t in p]; d[k + "_d"] = [t[2] for t in p]
        d[k] = [np.nan if nan(t[0]) else (t[0] + (0 if nan(t[2]) else t[2] * 86400)) for t in p]
    return d


PLAY_TEXT_RX = re.compile(r"^\s*(\(\s*\d*:\d{2}\s*\)\s*)?(\([^)]*\)\s*)*PENALTY", re.I)


def has_play(desc):
    """A no-play row ran a play when its text describes one before 'PENALTY' (after the clock and formation notes)."""
    return isinstance(desc, str) and not PLAY_TEXT_RX.match(desc)


KICK_RX = re.compile(r"kicks (?:onside )?(-?\d+) yards", re.I)
FG_RX = re.compile(r"(\d+) yard field goal", re.I)
TO_RX = re.compile(r"Timeout #\d+ by ([A-Z]{2,3})")


def kick_yards(desc):
    m = KICK_RX.search(desc) if isinstance(desc, str) else None
    return int(m.group(1)) if m else None


def is_onside(desc):
    """E1a v2 a: an onside try is a kick whose text says 'onside'; the short kicks without it (section 0) were squibs fielded by the receivers."""
    return isinstance(desc, str) and "onside" in desc.lower()


def row_kind(pt, kind, tp):
    if one(tp) or kind == "try": return "try"
    if pt in SNAP_KINDS: return "snap"
    if pt == "kickoff": return "kickoff"
    if kind == "timeout": return "timeout"
    if kind == "penalty": return "foul"
    return "other"


def family(pteam, off, ptype, wiped, text_play, desc):
    """The foul families family v0 plays for one recorded foul, or None (not played)."""
    if not isinstance(ptype, str) or not isinstance(pteam, str): return None
    o = pteam == off
    if wiped and not text_play:
        if o and ptype in PRESNAP_OFFENSE: return "F1"
        if (not o) and ptype not in DEF_AWARD and ptype not in DEF_NEXT: return "F2"
        return None
    if wiped:
        if o and ptype in OFF_DURING: return "F3"
        if (not o) and ptype in DEF_AWARD: return "F4"
        return None
    if o and ptype in LOSS_OF_DOWN: return "F5"
    if o and ptype in OFF_AFTER and "between downs" not in str(desc).lower(): return "F6"
    return None


def own_class(d, i, reg):
    """The clock after the record's snap i by its own events (rules.clock_class over the events v0 plays: 4-4f, 4-3-2a, 4-4d, 4-4i, 4-3-2e)."""
    q = d.at[i, "qtr"]; qa = d.at[i, "quarter_seconds_remaining"]
    ob = d.at[i, "out_of_bounds"]; ow = oob_window(q, qa, reg); fw = foul_window(q, qa, reg); pen = one(d.at[i, "penalty"])
    scored = one(d.at[i, "touchdown"]) or d.at[i, "field_goal_result"] == "made" or one(d.at[i, "safety"]) or one(d.at[i, "touchback"])
    poss = one(d.at[i, "interception"]) or one(d.at[i, "fumble_lost"]) or d.at[i, "kind"] in ("punt", "field_goal") or (d.at[i, "down"] == 4 and not one(d.at[i, "first_down"]))
    ev = [("incomplete 4-4f", one(d.at[i, "incomplete_pass"])), ("out of bounds late 4-3-2a", one(ob) and ow is True), ("score/touchback/try 4-4d", bool(scored)),
          ("change of possession 4-4i", bool(poss)), ("foul in window 4-3-2e", pen and fw is True), ("out of bounds early 4-3-2a", one(ob) and ow is False),
          ("foul outside windows 4-3-2e", pen and fw is False), ("out of bounds unread", nan(ob)), ("out of bounds, window unread", one(ob) and ow is None),
          ("foul, window unread", pen and fw is None)]
    return clock_class(ev, beyond(q, reg))[0]


def quarter_ends(d, X):
    """R1a, the quarter ends (4-6-1): after a regulation snap whose play leaves PLAY_CLOCK game seconds or fewer on a running clock (stamped plays only: the
    clock after the play is the clock at the snap less the play's end stamp minus its start stamp), whether the offense snaps again before 0:00 and, if it does,
    the game seconds that run first. A next snap counts when check_clock classes the stretch to it RUN with no row between; a quarter's last snap counts when its own
    events leave the clock running (own_class) and no timeout, foul, kick or Try follows it in the quarter."""
    rows = []
    W, E = d["W"].to_numpy(float), d["E"].to_numpy(float)
    for _, gd in d.groupby("game_id", sort=False):
        reg = gd["season_type"].iloc[0] == "REG"
        ivs = {iv["sa"]: iv for iv in check_clock.intervals(gd)}
        idx = gd.index.to_numpy()
        for p, i in enumerate(idx):
            q = d.at[i, "qtr"]; qa = d.at[i, "quarter_seconds_remaining"]
            if nan(q) or q > 4 or d.at[i, "rk"] != "snap" or nan(W[i]) or nan(E[i]) or nan(qa): continue
            C = int(round(qa - (E[i] - W[i])))
            if not 0 < C <= PLAY_CLOCK: continue
            qt = "1/3" if q in (1, 3) else "2/4"; ls = score_bin(d.at[i, "diff"]) if q in (2, 4) else "-"
            iv = ivs.get(int(d.at[i, "order_sequence"]))
            if iv is not None:
                if iv["cls"] != "RUN" or iv["nb"] != 0: continue
                r = C - iv["qb"]
                if nan(r) or r < 0: X["quarter end: the next snap's clock above the clock after the play (not used)"] += 1; continue
                rows.append((qt, ls, C, 1, int(round(r)))); continue
            after = [j for j in idx[p + 1:] if d.at[j, "qtr"] == q]
            if any(d.at[j, "rk"] in ("snap", "timeout", "foul", "kickoff", "try") or one(d.at[j, "penalty"]) or one(d.at[j, "timeout"]) for j in after): continue
            if own_class(d, i, reg) != "RUN": continue
            rows.append((qt, ls, C, 0, -1))
    return pd.DataFrame(rows, columns=["qt", "ls", "C", "snap", "run"])


def dur_whole(d, full, kind, pos, dn):
    """Every pass or run of the record with its down, distance, yard line and time (none removed for its foul), with the foul on it: 'none'; F5 and F6 as before (a play that stands); 'wiped', a down whose play a foul
    wiped, carrying its side, its enforced yards (penalty_yards) and its next down by rule: the offense's, 14-1-2 Item 1 and 3-8-4 (the down replayed from
    the previous spot) or Item 2 (loss of down) by name; the defense's, 14-1-2 Item 5's award for a name on its list (DEF_AWARD), else the row's own award
    mark where its yards fall short of its line to gain (the award shown), Item 5's Exceptions where the row shows no award, and 'the award or the line'
    where the row reached its line (the record cannot tell them apart: the engine plays it only where both readings give the same state); 'offsetting'
    (3-8-4, the down replayed); v18 c: 'stand', a foul on a play that stands (its side, penalty_yards, its award mark, its name) enforced by
    transition.stand() at the drawn play's end; 'unsupported: why' for a recorded foul the engine does not enforce (kept, at its own rate)."""
    if "penalty_yards" not in d.columns: raise record.DataGap("engine: penalty_yards not joined to the record: the fouls on the play cannot be drawn whole")
    U = lambda why: ("unsupported: " + why, None, np.nan, None, None, False)
    rows = []
    for i in np.where(d["db"] & full)[0]:
        k_ = kind[i]; off = pos[i]; wiped = k_ == "penalty" and bool(d.at[i, "textplay"])
        if not (wiped or k_ in CALL): continue
        base = (int(dn[i]), d.at[i, "dist"], d.at[i, "field"], d.at[i, "time"], d.at[i, "score"], "pass" if one(d.at[i, "pass"]) else "run")
        ob_i = d.at[i, "out_of_bounds"]; dep_i = dlo_i = np.nan
        if wiped and d.at[i, "penalty_type"] == "Defensive Pass Interference" and not nan(d.at[i, "penalty_yards"]) and isinstance(pos[i], str) and d.at[i, "penalty_team"] != pos[i]:
            # pass interference's depth, the row's penalty_yards from its line; where the ball went to the 1 (or half the distance inside the 2) the
            # depth is censored: only its lower bound (the line less one) is kept, never drawn as the depth
            yl_i = float(d.at[i, "yardline_100"]); py_i = float(d.at[i, "penalty_yards"])
            if py_i >= yl_i - 1: dlo_i = max(yl_i - 1, 0.0)
            else: dep_i = py_i
        R_ = lambda x_: rows.append(base + x_ + (ob_i, dep_i, dlo_i))   # v18 d: the row's own out_of_bounds mark; pass interference's depth (or its censored bound)
        pt, ptype, txt = d.at[i, "penalty_team"], d.at[i, "penalty_type"], d.at[i, "desc"]
        pen = one(d.at[i, "penalty"]) and isinstance(ptype, str)
        if not wiped:
            if not pen: R_(("none", None, np.nan, None, None, False)); continue
            fam = None if check_downs.flagged(pt, ptype, txt) else family(pt, off, ptype, False, True, txt)
            if fam: R_((fam, None, np.nan, None, None, False)); continue
            # v18 c: a foul on a play that stands, kept whole for transition.stand(): one accepted foul, its team and penalty_yards read, enforced at the play's end
            acc_ = [c_ for c_ in check_downs.foul_clauses(txt) if c_[1]]; py_s = d.at[i, "penalty_yards"]; why_ = None
            if check_downs.flagged(pt, ptype, txt): why_ = "the record's foul columns name none of the fouls its text accepts (check_downs v19)"
            elif len(acc_) != 1: why_ = f"{len(acc_)} accepted fouls on the play"
            elif not (isinstance(pt, str) and isinstance(off, str)) or nan(py_s): why_ = "the fouling team or penalty_yards empty"
            elif one(d.at[i, "interception"]) or one(d.at[i, "fumble_lost"]) or one(d.at[i, "touchdown"]) or one(d.at[i, "safety"]):
                case_ = "a touchdown" if one(d.at[i, "touchdown"]) else ("a safety" if one(d.at[i, "safety"]) else ("an interception" if one(d.at[i, "interception"]) else "a fumble lost"))
                why_ = f"a score or a change of possession on the play ({case_}; by the {'offense' if pt == off else 'defense'})"   # a read; the try, kickoff or succeeding spot not enforced
            else:
                sp_ = _T.enforced_at(str(txt)[acc_[0][2]:acc_[0][3]], off); end_ = float(d.at[i, "yardline_100"]) - float(d.at[i, "yards_gained"])
                if sp_ is None or abs(sp_ - end_) >= 0.5: why_ = "its enforcement spot is not the play's end (a spot foul or the previous spot)"
            if why_: R_(U(f"a foul on a play that stands: {why_}: {ptype}")); continue
            R_(("stand", "offense" if pt == off else "defense", float(py_s), "award" if one(d.at[i, "first_down_penalty"]) else "no award", ptype, False)); continue
        if nan(ob_i): R_(U(f"the wiped play's out_of_bounds mark empty: {ptype}")); continue
        if re.search(r"offsetting", str(txt), re.I): R_(("offsetting", None, 0.0, "cancelled", None, False)); continue
        if not pen: R_(U("a no-play foul the record does not name")); continue
        if check_downs.flagged(pt, ptype, txt): R_(U("the record's foul columns name none of the fouls its text accepts (check_downs v19)")); continue
        py, tg = d.at[i, "penalty_yards"], d.at[i, "ydstogo"]
        if not (isinstance(pt, str) and isinstance(off, str)) or nan(py) or nan(tg): R_(U(f"the fouling team, penalty_yards or ydstogo empty: {ptype}")); continue
        fdp = one(d.at[i, "first_down_penalty"])
        if pt == off:
            R_(("wiped", "offense", float(py), "loss_of_down" if ptype in LOSS_OF_DOWN else "off_during", ptype, bool(fdp))); continue
        oc = "def_award" if (ptype in DEF_AWARD or (fdp and py < tg)) else ("def_exception" if not fdp else "def_award_or_line")
        R_(("wiped", "defense", float(py), oc, ptype, bool(ptype in DEF_AWARD and not fdp)))
    return pd.DataFrame(rows, columns=["down", "dist", "field", "time", "score", "grp", "fam2", "side", "pyd", "oc", "ptype", "flag_differs", "ob", "dep", "dlo"])


def prep(d):
    """Per-row features and the tables the pools are fitted on, for one season of the record."""
    d = d.copy()
    n = len(d)
    d["rk"] = [row_kind(p, k, t) for p, k, t in zip(d["play_type"], d["kind"], d["two_point_attempt"])]
    th = d.groupby("game_id")["total_home_score"].transform(lambda s: s.ffill().shift().fillna(0))   # the score before the row; every game starts 0-0
    ta = d.groupby("game_id")["total_away_score"].transform(lambda s: s.ffill().shift().fillna(0))
    d["diff"] = np.where(d["posteam"] == d["home_team"], th - ta, ta - th)
    gid = d["game_id"].to_numpy(); pos = d["posteam"].to_numpy(object); rk = d["rk"].to_numpy(object); kind = d["kind"].to_numpy(object)
    dn = d["down"].to_numpy(float); tp = d["two_point_attempt"].to_numpy(float)
    db = np.array([(kind[i] in CALL or kind[i] in ("punt", "field_goal", "penalty")) and not nan(dn[i]) and tp[i] != 1 for i in range(n)])
    nxt = np.full(n, -1)
    last = -1
    for i in range(n - 1, -1, -1):
        if i + 1 < n and gid[i + 1] != gid[i]: last = -1
        nxt[i] = last
        if db[i]: last = i
    nko = np.full(n, -1); last = -1   # next kickoff row after i in the game, before the next down-carrying row
    for i in range(n - 1, -1, -1):
        if i + 1 < n and gid[i + 1] != gid[i]: last = -1
        nko[i] = last
        if rk[i] == "kickoff": last = i
        elif db[i]: last = -1
    d["db"] = db; d["nxt"] = nxt; d["nko"] = nko
    ok = d["down"].notna() & d["ydstogo"].notna() & d["yardline_100"].notna()
    d["dist"] = [dist_bin(t) if not nan(t) else None for t in d["ydstogo"]]
    d["field"] = [field_bin(y) if not nan(y) else None for y in d["yardline_100"]]
    d["yl20"] = [yl20_bin(y) if not nan(y) else None for y in d["yardline_100"]]; d["yl5"] = [yl5_bin(y) if not nan(y) else None for y in d["yardline_100"]]; d["yl5in"] = [yl5in_bin(y) if not nan(y) else None for y in d["yardline_100"]]; d["yl20in"] = np.array([yl20in_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object); d["ylw"] = np.array([ylw_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object); d["dist4"] = np.array([dist4_bin(t) if not nan(t) else None for t in d["ydstogo"]], dtype=object); d["ycell"] = np.array([ycell_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object)   # ab1, v33, v36 af1 (whole yards and None, kept as objects as yl5in is); v37 ag1: the yard line, the distance bin and the cell, before the comment
    d["time"] = [time_bin(q, s) if not nan(s) else None for q, s in zip(d["qtr"], d["quarter_seconds_remaining"])]
    d["score"] = [score_bin(x) for x in d["diff"]]
    d["textplay"] = [has_play(x) for x in d["desc"]]
    T, X = {}, Counter()
    full = ok & d["time"].notna()
    lat = d["lateral_receiver_player_id"].notna() | d["lateral_rusher_player_id"].notna()
    clean = d["kind"].isin(list(CALL)) & (d["penalty"] != 1) & (d["two_point_attempt"] != 1) & full
    X["plays with a lateral (not played)"] = int((clean & lat).sum())
    X["snaps with no out-of-bounds mark (not drawn)"] = int((clean & ~lat & d["out_of_bounds"].isna()).sum())
    T["play"] = d[clean & ~lat & d["out_of_bounds"].notna()][["kind", "yards_gained", "complete_pass", "incomplete_pass", "interception", "fumble_lost", "out_of_bounds", "down", "dist", "field", "time", "score", "yl20", "yl5", "yl5in", "yl20in"]].copy()
    T["play"]["down"] = T["play"]["down"].astype(int)
    T["play"]["inc_k"] = T["play"]["incomplete_pass"].fillna(0).astype(int); T["play"]["ob_k"] = T["play"]["out_of_bounds"].fillna(0).astype(int)
    _ds = d.loc[T["play"].index, "desc"].astype(str)   # the engine-vs-record stage v13 e, f: the drawn row carries its own review flag, decision and injury text (whole recorded plays)
    T["play"]["rv"] = (d.loc[T["play"].index, "replay_or_challenge"] == 1).astype(int)
    T["play"]["rv_rev"] = _ds.str.contains(r"play was REVERSED", case=False).astype(int)
    _ch = _ds.str.extract(r"\b([A-Z]{2,3}) challenged")[0]
    T["play"]["rv_chal"] = np.where(_ch.isna(), "", np.where(_ch == d.loc[T["play"].index, "posteam"], "offense", "defense"))
    T["play"]["inj"] = _ds.str.contains("injur", case=False).astype(int)
    # the engine-vs-record stage v14 d: the injured player's team from the drawn row's own text (4-5-4 charges it), the side of an accepted foul on the row (4-5-4's exception),
    # the on-field decision's own clock flags from the text before the review phrase (15-5-2 compares it with the decision that stands), the record row it came from
    _pos = d.loc[T["play"].index, "posteam"].astype(str); _dfn = d.loc[T["play"].index, "defteam"].astype(str)
    _it = _ds.str.extract(r"\b([A-Z]{2,3})-\d+-[^ ]+ was injured")[0]
    T["play"]["inj_side"] = np.where(_it.isna(), "", np.where(_it == _pos, "offense", np.where(_it == _dfn, "defense", "")))
    _pt = d.loc[T["play"].index, "penalty_team"].astype(str); _pen = (d.loc[T["play"].index, "penalty"] == 1) & ~_ds.str.contains("declined|offsetting", case=False)
    T["play"]["pen_side"] = np.where(~_pen, "", np.where(_pt == _pos, "offense", np.where(_pt == _dfn, "defense", "")))
    _of = _ds.str.split(r"The Replay Official reviewed|[A-Z]{2,3} challenged", n=1, regex=True).str[0]
    T["play"]["of_inc"] = _of.str.contains(r"\bincomplete\b", case=False).astype(int)
    T["play"]["of_ob"] = _of.str.contains(r"pushed ob|ran ob|out of bounds", case=False).astype(int)
    T["play"]["of_score"] = ((_of.str.contains("TOUCHDOWN") & ~_of.str.contains("NULLIFIED")) | _of.str.contains("SAFETY")).astype(int)
    _rc = _of.str.extract(r"RECOVERED by ([A-Z]{2,3})")[0]
    T["play"]["of_poss"] = (_of.str.contains("INTERCEPTED") | (_rc.notna() & (_rc != _pos))).astype(int)
    T["play"]["src"] = d.loc[T["play"].index, "game_id"].astype(str) + "|" + d.loc[T["play"].index, "order_sequence"].astype(int).astype(str)
    ix_ = T["play"].index
    T["kc"] = T["play"][["kind", "inc_k", "ob_k", "down", "dist"]].assign(
        tb2=[tb2(q_, s_) for q_, s_ in zip(d.loc[ix_, "qtr"], d.loc[ix_, "quarter_seconds_remaining"])],
        ls=[late_score(q_, s_, x_) for q_, s_, x_ in zip(d.loc[ix_, "qtr"], d.loc[ix_, "quarter_seconds_remaining"], d.loc[ix_, "diff"])])
    m_ = clean & ~lat & d["out_of_bounds"].isna()
    for (k_, i_), n_ in d[m_].groupby([d.loc[m_, "kind"], d.loc[m_, "incomplete_pass"].fillna(-1)]).size().items():
        X[f"R1b: snaps not drawn for no out-of-bounds mark, {k_}, incomplete {int(i_)}"] = int(n_)
    c4 = (d["down"] == 4) & (d["kind"].isin(list(CALL) + ["punt", "field_goal"])) & full
    T["call4"] = d[c4].assign(choice=lambda z: np.where(z["kind"] == "punt", "punt", np.where(z["kind"] == "field_goal", "field_goal", "go")))[["choice", "down", "dist", "field", "time", "score", "ylw", "dist4", "ycell"]]
    T["call4"]["down"] = 4
    yl = d["yardline_100"].to_numpy(float)

    def next_spot(i, team_should):
        j = nxt[i]
        if j < 0: return None, "no next snap"
        if nko[i] >= 0: return None, "a kickoff before the next snap (a return score)"
        if pos[j] != team_should: return None, "the next snap is not the receiving team's"
        return yl[j], None

    rows = []
    for i in np.where(d["kind"].isin(list(CALL)) & ((d["interception"] == 1) | (d["fumble_lost"] == 1)) & (d["penalty"] != 1) & full)[0]:
        other = d.at[i, "defteam"]; s_, why = next_spot(i, other)
        if s_ is None: X[f"turnover not placed: {why}"] += 1; continue
        rows.append(("interception" if d.at[i, "interception"] == 1 else "fumble lost", d.at[i, "field"], s_))
    T["turn"] = pd.DataFrame(rows, columns=["ttype", "field", "opp_yl"])
    rows = []
    for i in np.where((d["kind"] == "punt") & full)[0]:
        if nan(d.at[i, "touchback"]): X["punt with no touchback mark (not drawn)"] += 1; continue
        s_, why = next_spot(i, d.at[i, "defteam"])
        if s_ is None: X[f"punt not placed: {why}"] += 1; continue
        rows.append((d.at[i, "field"], s_, 1 if one(d.at[i, "touchback"]) else 0))
    T["punt"] = pd.DataFrame(rows, columns=["field", "opp_yl", "touchback"])
    rows, rows2 = [], []
    for i in np.where((d["kind"] == "field_goal") & full)[0]:
        m = FG_RX.search(str(d.at[i, "desc"])); made = d.at[i, "field_goal_result"] == "made"
        if m: rows.append((int(m.group(1)) // 5 * 5, 1 if made else 0))
        else: X["field goal with no distance in its text"] += 1
        if not made:
            s_, why = next_spot(i, d.at[i, "defteam"])
            if s_ is None: X[f"missed field goal not placed: {why}"] += 1
            else: rows2.append((d.at[i, "field"], s_))
    T["fg"] = pd.DataFrame(rows, columns=["dist5", "made"]); T["fgmiss"] = pd.DataFrame(rows2, columns=["field", "opp_yl"])
    rows, rows_s, rows_on, rows_cell = [], [], [], []
    for i in np.where(d["rk"] == "kickoff")[0]:
        recv = d.at[i, "posteam"]; desc = d.at[i, "desc"]; kick = d.at[i, "defteam"]
        k = i - 1
        while k >= 0 and gid[k] == gid[i] and rk[k] in ("timeout", "other", "try"): k -= 1
        after_safety = k >= 0 and gid[k] == gid[i] and one(d.at[k, "safety"])
        if after_safety:
            s_, why = next_spot(i, recv)
            if s_ is None: X[f"safety kick not placed: {why}"] += 1
            else: rows_s.append((s_,))
            continue
        q = d.at[i, "qtr"]; per = "1-3" if q <= 3 else "4th and overtime"
        kd = -d.at[i, "diff"] if isinstance(recv, str) else np.nan   # the kicking team's score, before the kick
        if nan(kd): X["kickoff with no receiving team"] += 1; continue
        cell = (per, "ahead" if kd > 0 else ("tied" if kd == 0 else "behind"))
        ons = is_onside(desc)
        rows_cell.append((cell[0], cell[1], 1 if ons else 0))
        if ons:
            j = nxt[i]
            if j < 0 or nko[i] >= 0: X["onside try not placed: no next snap"] += 1; continue
            rec = 1 if (one(d.at[i, "own_kickoff_recovery"]) or pos[j] == kick) else 0
            rows_on.append((cell[0], cell[1], rec, yl[j]))
            continue
        if nan(d.at[i, "touchback"]): X["kickoff with no touchback mark (not drawn)"] += 1; continue
        tb = 1 if one(d.at[i, "touchback"]) else 0
        s_, why = next_spot(i, recv)
        if s_ is None: X[f"kickoff not placed: {why}"] += 1; continue
        rows.append((tb, s_))
    T["ko"] = pd.DataFrame(rows, columns=["touchback", "opp_yl"]); T["safekick"] = pd.DataFrame(rows_s, columns=["opp_yl"])
    T["onside"] = pd.DataFrame(rows_on, columns=["per", "kscore", "recovered", "next_yl"]); T["kocell"] = pd.DataFrame(rows_cell, columns=["per", "kscore", "onside"])
    # fouls: before the snap (per snap opportunity) and during the play (per pass or run)
    rows_pre, rows_dur, notp = [], [], Counter()
    for i in np.where(d["db"] & full)[0]:
        k_ = kind[i]; off = pos[i]
        base = (int(dn[i]), d.at[i, "dist"], d.at[i, "field"], d.at[i, "time"], d.at[i, "score"])
        grp = "pass" if one(d.at[i, "pass"]) else "run"
        pen = one(d.at[i, "penalty"]) and isinstance(d.at[i, "penalty_type"], str)
        if k_ == "penalty":
            fam = family(d.at[i, "penalty_team"], off, d.at[i, "penalty_type"], True, d.at[i, "textplay"], d.at[i, "desc"]) if pen else None
            if check_downs.flagged(d.at[i, "penalty_team"], d.at[i, "penalty_type"], d.at[i, "desc"]): fam = None
            if not d.at[i, "textplay"]:
                if fam: rows_pre.append(base + (fam,))
                else: notp[f"before the snap: {d.at[i, 'penalty_type']} by the {'offense' if d.at[i, 'penalty_team'] == off else 'defense'}"] += 1
            else:
                if fam: rows_dur.append(base + (grp, fam))
                else: notp[f"during the play, the play wiped: {d.at[i, 'penalty_type']} by the {'offense' if d.at[i, 'penalty_team'] == off else 'defense'}"] += 1
            continue
        rows_pre.append(base + ("none",))
        if k_ in CALL:
            if pen:
                fam = family(d.at[i, "penalty_team"], off, d.at[i, "penalty_type"], False, True, d.at[i, "desc"])
                if check_downs.flagged(d.at[i, "penalty_team"], d.at[i, "penalty_type"], d.at[i, "desc"]): fam = None
                if fam: rows_dur.append(base + (grp, fam))
                else: notp[f"the play stands: {d.at[i, 'penalty_type']} by the {'offense' if d.at[i, 'penalty_team'] == off else 'defense'}"] += 1
            else:
                rows_dur.append(base + (grp, "none"))
        elif pen:
            notp[f"on a kick: {d.at[i, 'penalty_type']}"] += 1
    T["pre"] = pd.DataFrame(rows_pre, columns=["down", "dist", "field", "time", "score", "fam"])
    T["dur"] = pd.DataFrame(rows_dur, columns=["down", "dist", "field", "time", "score", "grp", "fam"])
    T["dur2"] = dur_whole(d, full, kind, pos, dn)
    # timeouts after a snap, by (time, score) of the next snap's offense
    rows = []
    sn = np.where(d["rk"] == "snap")[0]
    for a, b in zip(sn, sn[1:]):
        if gid[a] != gid[b] or d.at[a, "qtr"] != d.at[b, "qtr"] or nan(d.at[a, "quarter_seconds_remaining"]): continue
        team = None
        for x in range(a + 1, b):
            if rk[x] == "timeout":
                m = TO_RX.search(str(d.at[x, "desc"])); team = m.group(1) if m else "?"; break
        if team == "?": X["timeout with no team in its text"] += 1; continue
        df_ = d.at[a, "diff"] if pos[a] == pos[b] else -d.at[a, "diff"]
        rows.append((time_bin(d.at[a, "qtr"], d.at[a, "quarter_seconds_remaining"]), score_bin(df_), "none" if team is None else ("offense" if team == pos[b] else "defense")))
    T["to"] = pd.DataFrame(rows, columns=["time", "score", "caller"])
    # R1b: timeouts after a snap by situation (4-5-1: three a half), regulation only
    home_ = d["home_team"].to_numpy(object); qn = d["qtr"].to_numpy(float); used = {}; uh = np.zeros(n); ua = np.zeros(n); key_ = None
    for i in range(n):
        k2 = (gid[i], 1 if qn[i] <= 2 else (2 if qn[i] <= 4 else 2 + int(qn[i]) - 4))
        if k2 != key_: key_ = k2; used = Counter()
        if rk[i] == "timeout":
            m = TO_RX.search(str(d.at[i, "desc"]))
            if m: used[m.group(1)] += 1
        uh[i] = used[home_[i]]; ua[i] = used[d.at[i, "away_team"]]
    rows = []
    for a, b in zip(sn, sn[1:]):
        if gid[a] != gid[b] or d.at[a, "qtr"] != d.at[b, "qtr"] or nan(d.at[a, "quarter_seconds_remaining"]) or d.at[a, "qtr"] > 4: continue
        team = None
        for x in range(a + 1, b):
            if rk[x] == "timeout":
                m = TO_RX.search(str(d.at[x, "desc"])); team = m.group(1) if m else "?"; break
        if team == "?": continue
        off_, q_, qa_ = pos[b], d.at[a, "qtr"], d.at[a, "quarter_seconds_remaining"]
        df_ = d.at[a, "diff"] if pos[a] == pos[b] else -d.at[a, "diff"]
        uo, ud = (uh[a], ua[a]) if off_ == home_[a] else (ua[a], uh[a])
        av = ("O" if uo < HALF_TIMEOUTS else "-") + ("D" if ud < HALF_TIMEOUTS else "-")
        rows.append((tb2(q_, qa_), late_score(q_, qa_, df_), own_class(d, a, d.at[a, "season_type"] == "REG"), av,
                     "none" if team is None else ("offense" if team == pos[b] else "defense")))
    T["to1"] = pd.DataFrame(rows, columns=["tb2", "ls", "own", "avail", "caller"])
    # Tries after a touchdown
    rows = []
    for i in np.where((d["touchdown"] == 1) & d["td_team"].notna())[0]:
        j = i + 1
        while j < n and gid[j] == gid[i] and rk[j] in ("timeout", "other"): j += 1
        if j >= n or gid[j] != gid[i] or rk[j] != "try": X["touchdown with no Try after it"] += 1; continue
        sc = d.at[i, "td_team"]; h, a_ = d.at[i, "total_home_score"], d.at[i, "total_away_score"]
        df_ = (h - a_) if sc == d.at[i, "home_team"] else (a_ - h)
        two = one(d.at[j, "two_point_attempt"])
        good = (d.at[j, "two_point_conv_result"] == "success") if two else (d.at[j, "extra_point_result"] == "good")
        rows.append((time_bin(d.at[j, "qtr"], d.at[j, "quarter_seconds_remaining"] if not nan(d.at[j, "quarter_seconds_remaining"]) else 900), score_bin(df_),
                     "two" if two else "kick", 1 if good else 0))
    T["try"] = pd.DataFrame(rows, columns=["time", "score", "choice", "good"])
    # real time: play lengths and gaps (stamped rows only)
    W, E = d["W"].to_numpy(float), d["E"].to_numpy(float)
    rows = []
    for i in range(n):
        if nan(W[i]) or nan(E[i]) or E[i] < W[i]: continue
        if rk[i] == "snap": lk = kind[i]
        elif rk[i] == "kickoff": lk = "ko_onside" if is_onside(d.at[i, "desc"]) else ("ko_tb" if one(d.at[i, "touchback"]) else "ko_ret")
        elif rk[i] == "try": lk = "two" if one(tp[i]) else "xp"
        elif rk[i] == "foul" and d.at[i, "textplay"]: lk = "nopl"
        else: continue
        rows.append((lk, int(round(E[i] - W[i]))))
    T["len"] = pd.DataFrame(rows, columns=["lk", "sec"])
    rows = []
    for i in range(n - 1):
        j = i + 1
        if gid[j] != gid[i] or nan(W[j]): continue
        st = E[i] if not nan(E[i]) else W[i]
        if nan(st): continue
        g = W[j] - st
        if g < 0: X["gap between rows below 0 (not used)"] += 1; continue
        if rk[i] == "snap" and rk[j] == "snap": continue
        rows.append((rk[i], rk[j], int(round(g))))
    T["gap"] = pd.DataFrame(rows, columns=["ka", "kb", "sec"])
    rows_c, rows_w, rows_p, rows_c1, rows_pair = [], [], [], [], []
    by_seq = {(g_, int(s_)): k for k, (g_, s_) in enumerate(zip(d["game_id"], d["order_sequence"]))}
    for _, gd in d.groupby("game_id", sort=False):
        for iv in check_clock.intervals(gd):
            if nan(iv["x"]) or iv["x"] < 0: continue
            a = by_seq[(iv["game_id"], iv["sa"])]
            la = E[a] - W[a] if not (nan(E[a]) or nan(W[a])) else np.nan
            if iv["tmw"] is True and not nan(la):
                rest = iv["x"] - (iv["qa"] - la - 120)
                if rest > 0: rows_w.append((int(round(rest)),))
                else: X["warning stretch with no time left after the warning (not used)"] += 1
            if iv["nb"] != 0: continue
            rows_c.append((iv["cls"], int(round(iv["x"]))))
            tb_, ls_ = time_bin(iv["q"], iv["qa"]), pace_score(iv["cls"], iv["q"], iv["qa"], d.at[a, "diff"])
            rows_c1.append((iv["cls"], tb_, ls_, int(round(iv["x"]))))
            if iv["cls"] == "PARTIAL" and not nan(la):
                run = iv["dG"] - la
                stopped = iv["x"] - run
                if 0 <= stopped <= iv["x"]: rows_p.append((int(round(stopped)),)); rows_pair.append((tb_, ls_, int(round(iv["x"])), int(round(stopped))))
                else: X["PARTIAL stretch whose stopped part is outside 0 to its gap (not used)"] += 1
    T["gsnap"] = pd.DataFrame(rows_c, columns=["cls", "sec"]); T["gwarn"] = pd.DataFrame(rows_w, columns=["sec"]); T["gpart"] = pd.DataFrame(rows_p, columns=["sec"])
    T["gsnap1"] = pd.DataFrame(rows_c1, columns=["cls", "tb", "ls", "sec"]); T["gpair"] = pd.DataFrame(rows_pair, columns=["tb", "ls", "x", "stopped"])
    # v19 y1: the restart after a foul outside the windows. 4-3-2(e): following the enforcement the game clock starts as if the foul had not occurred (a running
    # clock starts again on the Referee's signal); 4-6-2(e): after a penalty enforcement the offense has ENF_CLOCK's seconds, beginning with the Referee's whistle,
    # to snap. Each recorded foul row outside the windows (the window read where the engine reads it: a wiped down's own snap clock, the previous snap's for a foul
    # before the snap) on a running clock (the previous row a snap whose own clock class is RUN; for a wiped down RUN or PARTIAL: the engine's clock ran into the
    # down), its next row the snap in the same quarter, every stamp read: the stopped part (real seconds less game seconds, the foul row's stamp to the snap's)
    # and the running part (the game seconds less the wiped play's own stamped seconds). A part the stamps make negative, or a running part over the season's
    # book's play clock (not a restart the article allows), is counted and not used.
    yrows = []; enf_ = ENF_CLOCK.get(int(d["season"].iloc[0]), (None, "not read"))[0] if n else None
    qs_ = d["quarter_seconds_remaining"].to_numpy(float); qq_ = d["qtr"].to_numpy(float); rg_ = (d["season_type"] == "REG").to_numpy()
    for i in np.where(rk == "foul")[0]:
        a, b = i - 1, i + 1
        if a < 0 or b >= n or gid[a] != gid[i] or gid[b] != gid[i] or qq_[a] != qq_[i] or qq_[b] != qq_[i] or qq_[i] > 4 or nan(qs_[i]) or nan(qs_[a]) or nan(qs_[b]): continue
        wiped = bool(d.at[i, "textplay"]); qa_ = qs_[i] if wiped else qs_[a]; q_ = int(qq_[i])
        if foul_window(q_, qa_, bool(rg_[i])) is not False: continue   # inside the windows (or unread) the engine stops the clock to the snap: not a restart
        if not wiped and q_ >= 4 and d.at[i, "penalty_team"] == pos[i]: continue   # 4-3-2e(3): the offense's foul before the snap from the 4th quarter: the clock starts on the snap
        if rk[b] != "snap": X["y1: a foul outside the windows whose next row is not a snap (not used)"] += 1; continue
        if rk[a] != "snap": X["y1: a foul outside the windows with no snap right before it (the clock's state unread; not used)"] += 1; continue
        oc_ = own_class(d, a, bool(rg_[a]))
        if oc_ != "RUN" and not (wiped and oc_ == "PARTIAL"):
            X["y1: a foul outside the windows on a stopped clock (it starts on the snap; not used)"] += 1; continue
        if nan(W[i]) or nan(W[b]) or (wiped and nan(E[i])): X["y1: a restart after a foul outside the windows unstamped (not used)"] += 1; continue
        if enf_ is None: X["y1: a restart after a foul outside the windows, the season's play clock after an enforcement unread (not used)"] += 1; continue
        dG = qs_[i] - qs_[b]; run_ = int(round(dG - ((E[i] - W[i]) if wiped else 0.0))); stp_ = int(round((W[b] - W[i]) - dG))
        if stp_ < 0: X["y1: a restart whose game seconds exceed its real seconds (not used)"] += 1; continue
        if run_ < 0: X["y1: a restart whose clock ran less than the wiped play's own seconds (not used)"] += 1; continue
        if run_ > enf_: X["y1: a restart whose running part exceeds the book's play clock after an enforcement (not used)"] += 1; continue
        yrows.append(("wiped" if wiped else "presnap", time_bin(q_, qa_), stp_, run_))
    T["gfoul"] = pd.DataFrame(yrows, columns=["kind", "tb", "stopped", "run"])
    T["qend"] = quarter_ends(d, X)
    return T, X, notp


class Rates:
    def __init__(self, season, tables):
        """Pools for season s from the tables of the five other unsealed seasons."""
        self.season = season
        c = {k: pd.concat([t[k] for t in tables], ignore_index=True) for k in tables[0]}
        self.n = {k: len(v) for k, v in c.items()}
        P = {}
        P["play"] = Pool("snap outcome", c["play"], ["kind", "yards_gained", "complete_pass", "incomplete_pass", "interception", "fumble_lost", "out_of_bounds"], FULL_YL)   # ab1
        P["call4"] = Pool("4th-down choice", c["call4"], ["choice"], [("down", "dist", "ylw", "time", "score"), ("dist", "ylw", "time"), ("dist", "ylw"), ("dist4", "ylw"), ("dist4", "ycell")] + FULL)   # v37 ag1: keyed by where the ball is, finest first, then the levels as before
        P["turn"] = Pool("turnover spot", c["turn"], ["opp_yl"], [("ttype", "field"), ("ttype",), ()])
        P["punt"] = Pool("punt spot", c["punt"], ["opp_yl", "touchback"], [("field",), ()])
        P["fg"] = Pool("field goal made", c["fg"], ["made"], [("dist5",), ()])
        P["fgmiss"] = Pool("missed field goal spot", c["fgmiss"], ["opp_yl"], [("field",), ()])
        P["ko"] = Pool("kickoff result", c["ko"], ["touchback", "opp_yl"], [()])
        P["safekick"] = Pool("free kick after a safety", c["safekick"], ["opp_yl"], [()])
        P["onside"] = Pool("onside result", c["onside"], ["recovered", "next_yl"], [("per", "kscore"), ("per",), ()])
        P["kocell"] = Pool("onside try per kickoff", c["kocell"], ["onside"], [("per", "kscore"), ("per",), ()])
        P["pre"] = Pool("foul before the snap", c["pre"], ["fam"], FULL)
        P["dur2"] = Pool("foul on the play, drawn whole", c["dur2"], ["fam2", "side", "pyd", "oc", "ptype", "ob", "dep", "dlo"], [("grp",) + l for l in FULL])
        self.DPI_DEP = np.sort(c["dur2"]["dep"].dropna().to_numpy(float))   # pass interference's uncensored depths (the other seasons' rows)
        P["to"] = Pool("timeout after a snap", c["to"], ["caller"], [("time", "score"), ("time",), ()])
        P["try"] = Pool("Try choice", c["try"], ["choice"], [("time", "score"), ("time",), ()])
        P["xp"] = Pool("extra point good", c["try"][c["try"]["choice"] == "kick"], ["good"], [()])
        P["two"] = Pool("two-point try good", c["try"][c["try"]["choice"] == "two"], ["good"], [()])
        P["len"] = Pool("play length", c["len"], ["sec"], [("lk",), ()])
        P["gap"] = Pool("gap between rows", c["gap"], ["sec"], [("ka", "kb"), ("kb",), ()])
        P["gsnap"] = Pool("gap between snaps", c["gsnap"], ["sec"], [("cls",), ()])
        P["gwarn"] = Pool("gap after the warning", c["gwarn"], ["sec"], [()])
        P["gpart"] = Pool("stopped part of a PARTIAL stretch", c["gpart"], ["sec"], [()])
        P["gsnap1"] = Pool("R1a gap between snaps", c["gsnap1"], ["sec"], [("cls", "tb", "ls"), ("cls", "tb"), ("cls",), ()])
        P["gpair"] = Pool("R1a PARTIAL stretch, gap and stopped part", c["gpair"], ["x", "stopped"], [("tb", "ls"), ("tb",), ()])
        P["gfoul"] = Pool("y1 restart after a foul outside the windows, stopped part and running part", c["gfoul"], ["stopped", "run"], [("kind", "tb"), ("kind",)], last_any=True)
        P["kc"] = Pool("R1b play kind and its clock flags", c["kc"], ["kind", "inc_k", "ob_k"], [("tb2", "ls", "down", "dist"), ("tb2", "down", "dist"), ("tb2", "down"), ("tb2",), ()])
        P["play2"] = Pool("R1b snap outcome given its kind and clock flags", c["play"], ["kind", "yards_gained", "complete_pass", "incomplete_pass", "interception", "fumble_lost", "out_of_bounds", "rv", "rv_rev", "rv_chal", "inj", "inj_side", "pen_side", "of_inc", "of_ob", "of_score", "of_poss", "src"],
                          PLAY2_LV, last_any=True)   # v33: PLAY2_LV, the 5-yard cell inside the 20 kept to (kind, 5-yard cell), then today's cells
        P["to1"] = Pool("R1b timeout after a snap", c["to1"], ["caller"], [("tb2", "ls", "own", "avail"), ("tb2", "own", "avail"), ("tb2", "avail"), ("avail",), ()])
        P["qend"] = Pool("R1a quarter end", c["qend"].assign(Cb=(c["qend"]["C"] - 1) // QE_BAND), ["snap", "run"], [("qt", "ls", "C"), ("qt", "C"), ("C",), ("qt", "Cb"), ("Cb",), ()])
        self.P = P


# ---------------- the engine ----------------
def clock_txt(qs):
    m, s = divmod(int(qs), 60)
    return f"(:{s:02d})" if m == 0 else f"({m}:{s:02d})"


class Game:
    def __init__(self, g, rates, season_rules, rng, season):
        self.g, self.R, self.P, self.rng, self.season = g, rates, rates.P, rng, season
        self.home, self.away = g["home_team"], g["away_team"]
        self.reg = g["game_type"] == "REG"
        self.rows = []; self.seq = 0; self.t = 0; self.q = 1; self.clock = 900; self.running = False; self.restart_at = None
        self.score = {self.home: 0, self.away: 0}; self.drive = 0
        self.off = None; self.yl = None; self.down = None; self.ltg = None
        self.prev_kind = "other"; self.foul_used = False; self.own_cls = None; self.qa = None; self.pair_x = None; self.race_gap = None; self.race_log = []; self.race_foul = None; self.last_rv = 0.0; self.last_inj = 0.0; self.excess = {}; self.foul_gap = None
        self.pending_kick = None; self.warned = set(); self.over = False; self.declared = None; self.stretch_stop = True
        self.to_left = {self.home: HALF_TIMEOUTS, self.away: HALF_TIMEOUTS}
        X = season_rules[season]; self.season_rules = season_rules
        self.tb_spot = int(X["touchback"]["value"])
        self.rb = _TBR(season, X)
        self.chg = []   # c: where this engine plays a rule or a draw differently from engine.py's own code (the comparison reads it)
        self.unsup = []   # rows from which the game is UNSUPPORTED (an unplayed stoppage drawn)
        self.ot_len = int(X["ot_reg_len" if self.reg else "ot_post_len"]["value"])
        self.ot_rule = X["ot_reg_rule" if self.reg else "ot_post_rule"]["value"]
        self.ot_to = int(X["ot_reg_timeouts" if self.reg else "ot_post_timeouts"]["value"])
        self.onside_rule = X["onside"]["value"]; self.ot_first_recv = None
        self.in_ot = False; self.ot_poss = Counter(); self.ot_first_td = False
        self.cnt = Counter()
        gt = g["gametime"] if isinstance(g["gametime"], str) and re.match(r"^\d{1,2}:\d{2}$", g["gametime"]) else None
        if gt is None: self.cnt["games with no kickoff time in the schedule (stamped from 13:00; only differences between stamps are read)"] += 1
        self.base = datetime.datetime.strptime(f"{g['gameday']} {gt or '13:00'}", "%Y-%m-%d %H:%M")

    # ---- helpers
    def other(self, t):
        return self.away if t == self.home else self.home

    def spot(self, team, yl):
        yl = int(yl)
        if yl == 50: return "50"
        return f"{team} {100 - yl}" if yl > 50 else f"{self.other(team)} {yl}"

    def stamp(self, t):
        return (self.base + datetime.timedelta(seconds=int(t))).strftime("%Y-%m-%dT%H:%M:%SZ")

    def gsr(self):
        return self.clock if self.q >= 5 else (4 - self.q) * 900 + self.clock

    def key(self):
        return dict(down=int(self.down), dist=dist_bin(self.yl - self.ltg), field=field_bin(self.yl), time=time_bin(self.q, self.clock),
                    score=score_bin(self.score[self.off] - self.score[self.other(self.off)]), yl20=yl20_bin(self.yl), yl5=yl5_bin(self.yl), yl5in=yl5in_bin(self.yl), yl20in=yl20in_bin(self.yl), ylw=ylw_bin(self.yl), dist4=dist4_bin(self.yl - self.ltg), ycell=ycell_bin(self.yl))   # ab1, v33, v36 af1, v37 ag1

    def length(self, lk):
        return int(self.P["len"].draw(self.rng, dict(lk=lk))["sec"])

    def gap(self, ka, kb, cls=None):
        if ka == "snap" and kb == "snap" and cls is not None and R1A:   # R1a: the record's gap in the stretch's (class, time bin, score) cell
            if cls == "PARTIAL" and self.pair_x is not None:
                x = self.pair_x; self.pair_x = None; return x
            qa = self.qa if self.qa is not None else self.clock
            k = dict(cls=cls, tb=time_bin(self.q, qa), ls=pace_score(cls, self.q, qa, self.score[self.off] - self.score[self.other(self.off)]))
            return int(self.P["gsnap1"].draw(self.rng, k)["sec"])
        if ka == "snap" and kb == "snap" and cls is not None:
            return int(self.P["gsnap"].draw(self.rng, dict(cls=cls))["sec"])
        return int(self.P["gap"].draw(self.rng, dict(ka=ka, kb=kb))["sec"])

    def row(self, **kw):
        self.seq += 1
        r = dict(game_id=self.g["game_id"], play_id=self.seq, order_sequence=self.seq, season=self.season, week=int(self.g["week"]),
                 season_type="REG" if self.reg else "POST", home_team=self.home, away_team=self.away, qtr=self.q,
                 quarter_seconds_remaining=self.clock, game_seconds_remaining=self.gsr(), fixed_drive=self.drive, timeout=0, penalty=0,
                 replay_or_challenge=0, return_touchdown=0, defensive_two_point_conv=0, defensive_extra_point_conv=0)
        r.update(kw)
        self.mark(r)   # a half-yard spot written in the record's marking (the state keeps the exact spot)
        qs_ = r["quarter_seconds_remaining"]; r["game_seconds_remaining"] = qs_ if self.q >= 5 else (4 - self.q) * 900 + qs_
        r["total_home_score"] = self.score[self.home]; r["total_away_score"] = self.score[self.away]
        self.rows.append(r)
        return r

    def mark(self, r):
        """v19 s1, t1: yardline_100, ydstogo and yards_gained hold whole yards in the record's columns (record.py reads them as integers). A row written from
        a state off a whole yard (any fraction) is written in the record's marking: each spot (the ball, the line to gain, the play's end) rounded toward the goal the offense
        attacks (the record's own marking at 0.871, measured by the s run; the other way 0.129)."""
        yl, tg, yg = r.get("yardline_100"), r.get("ydstogo"), r.get("yards_gained")
        nw = lambda v: v is not None and not isinstance(v, str) and not nan(v) and float(v) != int(float(v))
        if not (nw(yl) or nw(tg) or nw(yg)) or yl is None or nan(yl): return
        W_ = lambda v: MARK_INSIDE1 if (0 < v < 1 and MARK_INSIDE1 is not None) else int(np.floor(v))   # v34 ad0 (b): each spot (the ball, the line to gain, the play's end) inside the 1 written at the yard line the record writes it as, never 0
        y = float(yl); w = W_(y)
        if tg is not None and not nan(tg): r["ydstogo"] = w - int(np.floor(y - float(tg)))   # v35 (ad addition 2, 7-3-1): the line to gain by the floor: a first down's distance is the smaller of 10 and the written yard line (a line to gain inside the 1 is short of the goal: 1st and 10)
        if yg is not None and not nan(yg): r["yards_gained"] = w - W_(y - float(yg))
        r["yardline_100"] = w

    def advance(self, dt):
        """Real time passes with no play: the game clock runs only while running (after any partial restart); the two-minute warning and 0:00 stop it."""
        t1 = self.t + dt
        if not self.running and self.restart_at is not None and self.restart_at < t1:
            start = max(self.restart_at, self.t); self.running = True; self.restart_at = None
        elif self.running:
            start = self.t
        else:
            self.t = t1; return "ok"
        run = t1 - start
        if warns(self.q, self.reg) and self.q not in self.warned and self.clock > 120 and self.clock - run <= 120:
            self.t = start + (self.clock - 120); self.clock = 120; self.running = False; self.warn_row(); return "warning"
        if self.clock - run <= 0:
            self.t = start + self.clock; self.clock = 0; self.running = False; return "zero"
        self.clock -= run; self.t = t1; return "ok"

    def warn_row(self):
        self.warned.add(self.q); self.stretch_stop = True; self.running = False; self.restart_at = None
        self.row(play_type="", desc="Two-Minute Warning", time_of_day=self.stamp(self.t))
        self.prev_kind = "other"

    def play(self, lk, timed=True):
        """A play is run: its length in real time; the game clock runs during it when timed (from the snap)."""
        L = self.length(lk); W = self.t; c0 = self.clock; self.restart_at = None
        if timed and self.clock > 0: self.clock = max(self.clock - L, 0)
        self.t += L
        return W, self.t, c0

    def after_play_warning(self, c0):
        if warns(self.q, self.reg) and self.q not in self.warned and c0 > 120 and self.clock <= 120 and self.clock > 0:
            self.warn_row(); self.running = False

    def stop_after(self, events, pair=False):
        """The clock after a play or a foul, by rules.clock_class over its events (the clock rule)."""
        cls, _ = clock_class(events, beyond(self.q, self.reg))
        if cls == "STOP" or cls == "UNKNOWN":
            self.running = False; self.restart_at = None; self.stretch_stop = True
        elif cls == "PARTIAL" and R1A and pair:   # 4-3-2a: outside the windows the clock starts on the ready-for-play signal; stopped part and gap from one recorded stretch
            o = self.P["gpair"].draw(self.rng, dict(tb=time_bin(self.q, self.qa), ls=pace_score("PARTIAL", self.q, self.qa, self.score[self.off] - self.score[self.other(self.off)])))
            self.running = False; self.restart_at = self.t + int(o["stopped"]); self.pair_x = int(o["x"])
        elif cls == "PARTIAL":
            self.running = False; self.restart_at = self.t + int(self.P["gpart"].draw(self.rng, {})["sec"])
        else:
            self.running = self.clock > 0; self.restart_at = None
        return cls

    def state0(self):
        return dict(off=self.off, dfn=self.other(self.off) if self.off is not None else None, down=self.down,
                    togo=None if self.yl is None else self.yl - self.ltg, yl=self.yl)

    def commit(self, st):
        """The transition's state becomes the game's: a kick to come is pending; else the offense, the down, the yard line and the line to gain."""
        if st["unk"]: raise record.DataGap(f"engine: the transition left {'+'.join(st['unk'])} UNKNOWN ({st['how']})")
        if st["kick"]:
            self.pending_kick = (self.other(st["off"]), st["kick_kind"] or "normal"); return
        if st["off"] != self.off: self.drive += 1
        ltg_ = st["yl"] - st["togo"]   # v19 s1, t1: the yard line and the line to gain carried exactly as the transition placed them (any fraction half the distance makes)
        self.off = st["off"]; self.yl = _hy(st["yl"]); self.down = int(st["down"]); self.ltg = _hy(ltg_)

    def end_possession(self, how):
        if self.in_ot:
            self.ot_poss[self.off] += 1
            if how == "td" and sum(self.ot_poss.values()) == 1: self.ot_first_td = True
            self.check_ot_end(how)

    def check_ot_end(self, how):
        lead = self.score[self.home] != self.score[self.away]
        if not lead: return
        both = len([t for t in (self.home, self.away) if self.ot_poss[t] >= 1]) == 2
        if how == "safety" or both or (self.ot_rule == rules.TD_ENDS and self.ot_first_td):
            self.over = True

    # ---- kicks
    def kickoff(self):
        kicker, kind_ = self.pending_kick; self.pending_kick = None; recv = self.other(kicker)
        g = self.gap(self.prev_kind, "kickoff"); self.advance(g)
        diff = self.score[kicker] - self.score[recv]; per = "1-3" if self.q <= 3 else "4th and overtime"
        cell = (per, "ahead" if diff > 0 else ("tied" if diff == 0 else "behind"))
        ons = kind_ == "normal" and onside_allowed(self.onside_rule, self.q, diff) and self.P["kocell"].draw(self.rng, dict(per=cell[0], kscore=cell[1]))["onside"] == 1
        qs0 = self.clock
        common = dict(play_type="kickoff", posteam=recv, defteam=kicker, ydstogo=0)
        if kind_ == "safety":
            o = self.P["safekick"].draw(self.rng, {}); W, E, c0 = self.play("ko_ret")
            yl = int(o["opp_yl"]); y = 20
            self.row(**common, yardline_100=20, quarter_seconds_remaining=qs0, desc=f"SIM-K kicks from {kicker} 20. SIM-KR to {self.spot(recv, yl)}.",
                     time_of_day=self.stamp(W), end_clock_time=self.stamp(E), touchback=0, own_kickoff_recovery=0)
            self.after_play_warning(c0); self.commit(_TRANS({}, dict(kind="kickoff", recv=recv, kicker=kicker, end=yl), self.rb))
        elif ons:
            o = self.P["onside"].draw(self.rng, dict(per=cell[0], kscore=cell[1])); W, E, c0 = self.play("ko_onside")
            rec = int(o["recovered"]) == 1; yl = int(o["next_yl"])
            team = kicker if rec else recv
            self.row(**common, yardline_100=35, quarter_seconds_remaining=qs0, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), touchback=0,
                     own_kickoff_recovery=1 if rec else 0, fumble_recovery_1_team=kicker if rec else np.nan,
                     desc=f"SIM-K kicks onside 12 yards from {kicker} 35 to {kicker} 47. RECOVERED by {team}-SIM-ST at {self.spot(team, yl)}.")
            self.after_play_warning(c0)
            self.commit(_TRANS({}, dict(kind="kickoff", recv=recv, kicker=kicker, rec_by=kicker if rec else recv, end=yl), self.rb))
            self.cnt["onside tries"] += 1; self.cnt["onside recovered by the kickers"] += int(rec)
        else:
            o = self.P["ko"].draw(self.rng, {})
            if int(o["touchback"]) == 1:
                W, E, c0 = self.play("ko_tb", timed=False); yl = None   # the spot from the transition: the season rules, the in-the-air kind (engine plays no acceptance-zone touchback)
                self.row(**common, yardline_100=35, quarter_seconds_remaining=qs0, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), touchback=1,
                         own_kickoff_recovery=0, desc=f"SIM-K kicks 65 yards from {kicker} 35 to end zone, Touchback.")
            else:
                W, E, c0 = self.play("ko_ret"); yl = int(o["opp_yl"])
                self.row(**common, yardline_100=35, quarter_seconds_remaining=qs0, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), touchback=0,
                         own_kickoff_recovery=0, desc=f"SIM-K kicks 65 yards from {kicker} 35 to {recv} 0. SIM-KR to {self.spot(recv, yl)}.")
                self.after_play_warning(c0)
            self.commit(_TRANS({}, dict(kind="kickoff", recv=recv, kicker=kicker, end=yl, tb=yl is None, tb_cond="in the air"), self.rb))
        self.running = False; self.restart_at = None   # the kickoff ends with a change of possession: the clock waits for the snap (4-4i)
        self.stretch_stop = True; self.prev_kind = "kickoff"; self.foul_used = False; self.own_cls = None

    # ---- snaps
    def attempt(self):
        k = self.key()
        if R1D and self.q <= 4:   # the engine-vs-record stage v13 d, p: pre-snap fouls are drawn only by the race (the pool 'pre' is not drawn in regulation)
            pre = self.race_foul if self.race_foul else "none"; self.race_foul = None
        else:
            pre = "none" if self.foul_used else self.P["pre"].draw(self.rng, k)["fam"]
        kb = "foul" if pre != "none" else "snap"
        if R1D and self.race_gap is not None:   # the engine-vs-record stage v12: the race drew this snap's second (a pre-snap foul the engine plays takes it)
            g = self.race_gap; self.race_gap = None
        elif self.foul_gap is not None:   # v19 y1: after a restart drawn by foul_restart the snap (or a second foul before it) comes at its drawn second
            g = self.foul_gap; self.foul_gap = None
        elif R1A and kb == "snap" and self.prev_kind == "snap" and self.running and self.q <= 4 and 0 < self.clock <= PLAY_CLOCK:   # R1a, the quarter ends (4-6-1)
            o = self.P["qend"].draw(self.rng, dict(qt="1/3" if self.q in (1, 3) else "2/4", C=int(self.clock), Cb=(int(self.clock) - 1) // QE_BAND,
                                                   ls=score_bin(self.score[self.off] - self.score[self.other(self.off)]) if self.q in (2, 4) else "-"))
            if int(o["snap"]) == 1: g = int(o["run"]); self.cnt["R1a quarter end: a snap drawn"] += 1
            else: g = self.clock; self.cnt["R1a quarter end: the clock run out"] += 1
        else:
            g = self.gap(self.prev_kind, kb, self.own_cls if (self.prev_kind == "snap" and kb == "snap") else None)
        res = self.advance(g)
        if res == "warning":
            if R1D and self.q <= 4 and not self.over: self.race_moment()   # the engine-vs-record stage v12: the warning is a stopped-clock act (v10 b)
            rest = None
            for _ in range(1000):
                v = int(self.P["gwarn"].draw(self.rng, {})["sec"])
                if v > 0: rest = v; break
                self.cnt["gap after the warning redrawn"] += 1
            self.advance(rest)
        if self.clock == 0:
            return
        if pre != "none":
            self.presnap(pre)
            if R1D and self.q <= 4 and not self.over and self.clock > 0: self.race_moment()
            return
        choice = self.P["call4"].draw(self.rng, k)["choice"] if self.down == 4 else "go"
        if self.down == 4: self.cnt[f"ag0: fourth-down choice at {zone4_bin(self.yl)} {dist4_bin(self.yl - self.ltg)} drawn at level {self.P['call4'].last}: {choice}"] += 1   # v37 ag0: the level the choice resolved at
        if choice == "punt": self.punt(k)
        elif choice == "field_goal": self.field_goal(k)
        else: self.scrimmage(k)
        if R1D and self.q <= 4:
            if not self.over and self.clock > 0: self.race_moment()
        elif not self.over and self.clock > 0 and self.pending_kick is None and self.prev_kind == "snap":
            self.timeouts()

    def foul_text(self, team, name, yards, at):
        return f"PENALTY on {team}-99-S.Player, {name}, {_yt(yards)} yards, enforced at {at}"   # the exact yards (1.5 where the half is not whole)

    def foul_clock(self, offense_presnap, ran):
        """The clock after a foul between snaps (4-3-2e): a clock already stopped on the stretch waits for the snap; a running one stops in the windows
        (and for the offense's foul before the snap from the 4th quarter on), else restarts on the ready signal."""
        if self.stretch_stop or (not ran and not self.running):
            self.running = False; self.restart_at = None; return
        qa = self.qa if self.qa is not None else self.clock; fw = foul_window(self.q, qa, self.reg)
        ev = [("foul in window 4-3-2e", fw is True), ("offensive pre-snap foul q4/OT 4-3-2e(3)", offense_presnap and self.q >= 4),
              ("foul outside windows 4-3-2e", fw is False), ("foul, window unread", fw is None)]
        if fw is False and clock_class(ev, beyond(self.q, self.reg))[0] == "PARTIAL":   # v19 y1: a running clock after a foul outside the windows
            self.foul_restart("wiped" if ran else "presnap", qa); return
        self.stop_after(ev)

    def foul_restart(self, kind, qa):
        """v19 y1: a foul outside the windows on a running clock (4-3-2e: following the enforcement the clock starts as if the foul had not occurred): the game
        clock stopped for the enforcement and started on the Referee's whistle; the snap within the season's book's play clock of the whistle (4-6-2e, ENF_CLOCK).
        The stopped part and the game seconds to the snap are one recorded restart after such a foul (its kind, a wiped down or a foul before the snap, and its
        time bin; the record's restarts over the book's play clock are not in the pool)."""
        o = self.P["gfoul"].draw(self.rng, dict(kind=kind, tb=time_bin(self.q, qa)))
        s_, r_ = int(o["stopped"]), int(o["run"])
        self.running = False; self.restart_at = self.t + s_; self.foul_gap = s_ + r_
        self.cnt[f"y1: restarts after a foul outside the windows ({kind})"] += 1

    def presnap(self, fam):
        off, dfn = self.off, self.other(self.off); yl0, ltg0, down0, qs0 = self.yl, self.ltg, self.down, self.clock; at = self.spot(off, yl0); W = self.t
        if fam == "F1":
            y = _hy(min(5, (100 - yl0) / 2)); team, name = off, "False Start"; ev_f = dict(kind="foul", by="offense", yards=y, outcome="presnap_offense")
        else:
            y = _hy(min(5, yl0 / 2)); team, name = dfn, "Defensive Offside"; ev_f = dict(kind="foul", by="defense", yards=y, outcome="def_exception")
        st_f = _TRANS(self.state0(), ev_f, self.rb)
        reached = fam == "F2" and st_f["new_series"]
        self.row(play_type="no_play", posteam=off, defteam=dfn, down=down0, ydstogo=yl0 - ltg0, yardline_100=yl0, yards_gained=0, penalty=1, penalty_team=team,
                 penalty_type=name, quarter_seconds_remaining=qs0, time_of_day=self.stamp(W), end_clock_time=self.stamp(W),
                 desc=f"{clock_txt(qs0)} {self.foul_text(team, name, y, at)} - No Play.", first_down=0, first_down_penalty=1 if reached else 0)
        self.commit(st_f)
        self.foul_clock(fam == "F1", ran=False); self.prev_kind = "foul"; self.foul_used = True
        self.cnt[f"foul {fam}"] += 1

    def flags(self, kind, comp=0, inc=0, itc=0, fum=0, td=0):
        return {"pass": 1 if kind in ("pass", "sack", "scramble", "spike") else 0, "rush": 1 if kind in ("run", "kneel") else 0,
                "sack": 1 if kind == "sack" else 0, "qb_scramble": 1 if kind == "scramble" else 0, "complete_pass": comp, "incomplete_pass": inc,
                "interception": itc, "fumble_lost": fum, "two_point_attempt": 0, "touchdown": td,
                "pass_touchdown": 1 if td and kind == "pass" else 0, "rush_touchdown": 1 if td and kind in ("run", "scramble", "kneel") else 0}

    def scrimmage(self, k):
        off, dfn = self.off, self.other(self.off); yl0, down0, ltg0, qs0 = self.yl, self.down, self.ltg, self.clock; togo0 = yl0 - ltg0
        if R1B:   # R1b: the kind and its clock flags (4-4f, 4-3-2a) by time bin and late score first, then the outcome of that kind and those flags
            s1 = self.P["kc"].draw(self.rng, dict(tb2=tb2(self.q, self.clock), ls=late_score(self.q, self.clock, self.score[off] - self.score[dfn]), down=k["down"], dist=k["dist"]))
            nope = [sd for sd, tm in (("offense", off), ("defense", dfn)) if self.to_left[tm] <= 0] if (R1D and self.q <= 4) else []
            ok_ = (lambda V, nope=nope, j=self.P["play2"].cols.index("rv_chal"): ~np.isin(V[:, j], nope)) if nope else None   # 15-6-1: a coach's challenge needs a timeout
            o = self.P["play2"].draw(self.rng, dict(k, kind=s1["kind"], inc_k=s1["inc_k"], ob_k=s1["ob_k"]), ok=ok_)
            if self.yl <= 20: self.cnt[f"ac0: play2 draw from {'inside the 1' if self.yl < 1 else yl5_bin(self.yl)} resolved at level {self.P['play2'].last}"] += 1   # ac0: the level's key names whether yards to the goal were kept
            if ok_ is not None: self.chg.append((len(self.rows), "challenge masked", {}))
        else:
            o = self.P["play"].draw(self.rng, k)
        kind = o["kind"]
        grp = "pass" if kind in ("pass", "sack", "scramble", "spike") else "run"
        fw = None if self.foul_used else self.P["dur2"].draw(self.rng, dict(k, grp=grp))   # v19 part 2: every recorded foul at its own rate, none suppressed for its recorded yards
        fam = "none" if fw is None else fw["fam2"]
        ev_f = None
        if fam == "offsetting": ev_f = dict(kind="foul", offsetting=True)
        elif fam == "wiped":   # v19 part 2: its yards and its award by its article from this spot (transition.foul_yards, spot_foul_yards), never the record row's
            nm_, sd_ = fw["ptype"], fw["side"]; why_ = None; yd_ = None; aw_ = False
            if sd_ == "defense" and nm_ == "Defensive Pass Interference":   # a spot foul: first down at the spot of the foul, the foul's depth from this line (v19 r1)
                aw_ = True; dpt_ = None
                if not nan(fw["dep"]): dpt_ = float(fw["dep"]); self.cnt["pass interference's depth, the drawn row's own (uncensored)"] += 1
                elif nan(fw["dlo"]): why_ = "pass interference: the drawn row's depth unread"
                else:   # the drawn row's depth censored (the ball went to the 1): a depth drawn from the uncensored depths at least its bound
                    cd_ = self.R.DPI_DEP[self.R.DPI_DEP >= float(fw["dlo"])]
                    if not len(cd_): why_ = f"pass interference: no uncensored depth at least the drawn row's bound {float(fw['dlo']):.0f}"
                    else: dpt_ = float(cd_[self.rng.integers(len(cd_))]); self.cnt["pass interference's depth, censored: drawn from the uncensored depths at least its bound"] += 1
                if why_ is None:
                    yd_ = _T.spot_foul_yards(dpt_, float(yl0))
                    if yd_ is None: why_ = "pass interference: the depth not beyond the line"
            else:
                bk_ = BOOKY.get((self.season, nm_, sd_))
                if bk_ is None: why_ = f"its yards not found in the season's book: {nm_} by the {sd_}"
                else: yd_ = _T.foul_yards(bk_[0], sd_, float(yl0), "exact"); aw_ = bool(bk_[1])   # v19 r: half the distance exactly as the article sets it
            if why_: fam = "unsupported: " + why_
            else:
                oc_ = ("loss_of_down" if nm_ in LOSS_OF_DOWN else "off_during") if sd_ == "offense" else ("def_award" if aw_ else "def_exception")
                ev_f = dict(kind="foul", by=sd_, yards=_hy(yd_), outcome=oc_)
                self.cnt[f"foul on the play, the play wiped: yards by the article ({'the spot of the foul' if nm_ == 'Defensive Pass Interference' and sd_ == 'defense' else 'the book'})"] += 1
                if _TRANS(self.state0(), ev_f, self.rb)["off"] != off:
                    fam = "unsupported: a loss of down on 4th down with the play wiped (the change of possession on this path is not modeled)"
        if fam.startswith("unsupported"):   # drawn at its own rate, its effects not played: the game UNSUPPORTED from this row
            self.unsup.append((len(self.rows), "a foul on the play: " + fam.split(": ", 1)[1])); self.cnt["unsupported: a foul on the play drawn, not enforced"] += 1
            fam = "none"; ev_f = None
        at = self.spot(off, yl0)
        base = dict(posteam=off, defteam=dfn, down=down0, ydstogo=togo0, yardline_100=yl0, quarter_seconds_remaining=qs0)
        ids = dict(passer_player_id=f"SIM-{off}-QB" if kind in ("pass", "sack", "spike") else np.nan,
                   rusher_player_id=f"SIM-{off}-QB" if kind in ("scramble", "kneel") else (f"SIM-{off}-RB" if kind == "run" else np.nan),
                   receiver_player_id=f"SIM-{off}-WR" if kind == "pass" else np.nan)
        if fam in ("wiped", "offsetting"):   # the play is wiped: a no-play that ran a play (3-8-4); the foul as the record's row has it, enforced by the transition
            self.qa = qs0   # v18 d: this down's own snap clock: 4-3-2e's window is read at the engine's clock (engine left the previous snap's here)
            W, E, c0 = self.play("nopl")
            st_f = _TRANS(self.state0(), ev_f, self.rb)
            if fam == "offsetting":
                team = name = np.nan; fdp = 0
                txt = (f"{clock_txt(qs0)} SIM-{off} play for no gain. PENALTY on {off}-99-S.Player, Offsetting, 0 yards, offsetting."
                       f" PENALTY on {dfn}-98-S.Player, Offsetting, 0 yards, offsetting - No Play.")
            else:
                team = off if fw["side"] == "offense" else dfn; name = fw["ptype"]; fdp = 1 if (fw["side"] == "defense" and st_f["new_series"]) else 0
                txt = f"{clock_txt(qs0)} SIM-{off} play for no gain. {self.foul_text(team, name, ev_f['yards'], at)} - No Play."
            self.row(**base, play_type="no_play", yards_gained=0, penalty=1, penalty_team=team, penalty_type=name, time_of_day=self.stamp(W),
                     end_clock_time=self.stamp(E), desc=txt, first_down=0, first_down_penalty=fdp, out_of_bounds=int(float(fw["ob"])), **self.flags(kind), **ids)   # v18 d: the drawn record row's own out_of_bounds mark, never filled
            self.commit(st_f)
            self.after_play_warning(c0)
            self.foul_clock(False, ran=True); self.prev_kind = "foul"; self.foul_used = True
            self.cnt[f"foul on the play, the play wiped: {'offsetting' if fam == 'offsetting' else fw['side'] + ', ' + ev_f['outcome']}"] += 1
            return
        y = int(o["yards_gained"]); comp, inc, itc, fum, ob = (int(o[c]) if not nan(o[c]) else 0 for c in ("complete_pass", "incomplete_pass", "interception", "fumble_lost", "out_of_bounds"))
        if yl0 <= 20: self.cnt[f"ab1: snap draws from {yl5_bin(yl0)}"] += 1
        if fam == "F5":
            kind, y, comp, inc, itc, fum, ob = "pass", 0, 0, 1, 0, 0, 0
            ids = dict(passer_player_id=f"SIM-{off}-QB", rusher_player_id=np.nan, receiver_player_id=np.nan)
        if inc or itc: y = 0
        end = yl0 - y; td = 0; saf = 0
        if itc or fum:
            pass
        elif end <= 0:
            if end < 0: self.cnt[f"ab1: draws censored at the goal (the drawn gain past it), from {yl5_bin(yl0)}"] += 1   # ab1: counted before and after; the gain is censored as before
            y = yl0; end = 0; td = 1
        elif end >= 100:
            y = yl0 - 100; end = 100; saf = 1
        st0 = self.state0()
        ev_snap = dict(kind="snap", gain=y, td=bool(td), safety=bool(saf), scorer=off, turnover="interception" if itc else ("fumble" if fum else None), turn_team=dfn, turn_end=None)
        pv_snap = _TRANS(st0, ev_snap, self.rb)   # the result before the turnover's spot is drawn
        ev_st = None; fdp_st = 0
        if fam == "stand":   # v18 c: a foul on a play that stands, enforced by the transition at this play's end (the engine writes that spot); v19 part 2: its yards and award by its article from that end
            bk_ = BOOKY.get((self.season, fw["ptype"], fw["side"])); why_ = None; yd_s = None
            if td or saf or itc or fum: why_ = f"a score or a change of possession on the drawn play ({'a touchdown' if td else ('a safety' if saf else ('an interception' if itc else 'a fumble lost'))}; by the {fw['side']})"
            elif bk_ is None: why_ = f"its yards not found in the season's book: {fw['ptype']} by the {fw['side']}"
            else:   # v19 r: half the distance exactly as the article sets it; a half-yard spot is not one the engine places (no rounding rule assumed)
                yd_s = _T.foul_yards(bk_[0], fw["side"], float(end), "exact")   # a half yard enforced exactly
            if why_ is None:
                ev_st = dict(ev_snap, foul_stand=dict(by=fw["side"], yards=float(yd_s), name=fw["ptype"], award=bool(bk_[1]), spot=float(end)))
                pv_st = _TRANS(st0, ev_st, self.rb)
                if pv_st["unk"]: why_ = pv_st["how"]
            if why_ is not None:
                self.unsup.append((len(self.rows), f"a foul on the play: a foul on a play that stands ({fw['ptype']}): {why_}"))
                self.cnt["unsupported: a foul on the play drawn, not enforced"] += 1; fam = "none"; ev_st = None
            else:
                pv_snap = pv_st; fdp_st = 1 if (bk_[1] and fw["side"] == "defense") else 0; self.cnt[f"foul on a play that stands, enforced: {fw['side']}"] += 1
        reached = (not itc) and (not fum) and (not td) and (not saf) and pv_snap["new_series"] and pv_snap["off"] == off
        ev_f5 = ev_f6 = None
        f6 = fam == "F6" and not (td or saf or itc or fum or (down0 == 4 and not reached))
        if fam == "F6" and not f6: self.cnt["F6 drawn where v0 does not play it"] += 1
        self.qa = qs0; self.stretch_stop = False
        W, E, c0 = self.play(kind)
        pt = {"pass": "pass", "sack": "pass", "scramble": "run", "run": "run", "kneel": "qb_kneel", "spike": "qb_spike"}[kind]
        words = {"pass": "pass to SIM-WR" if comp else "pass incomplete to SIM-WR", "sack": "sacked", "scramble": "scrambles", "run": "up the middle",
                 "kneel": "kneels", "spike": "spiked the ball"}[kind]
        txt = f"{clock_txt(qs0)} SIM-{off} {words}"
        if itc: txt += f" INTERCEPTED by {dfn}-SIM-DB."
        elif inc: txt += "."
        else: txt += f"{' pushed ob' if ob else ''} to {self.spot(off, end) if 0 < end < 100 else (dfn + ' end zone' if end <= 0 else off + ' end zone')} for {y} yards."
        if fum: txt += f" FUMBLES, RECOVERED by {dfn}-SIM-DB."
        if td: txt += " TOUCHDOWN."
        if saf: txt += " SAFETY."
        pen = {}
        if ev_st is not None:
            team_st = off if fw["side"] == "offense" else dfn; yd_st = ev_st["foul_stand"]["yards"]
            txt += " " + self.foul_text(team_st, fw["ptype"], yd_st, self.spot(off, end)) + "."
            pen = dict(penalty=1, penalty_team=team_st, penalty_type=fw["ptype"])
        if fam == "F5":
            gy = _hy(min(10, (100 - yl0) / 2)); ev_f5 = dict(kind="foul", by="offense", yards=gy, outcome="loss_of_down")
            txt += " " + self.foul_text(off, "Intentional Grounding", gy, at) + "."
            pen = dict(penalty=1, penalty_team=off, penalty_type="Intentional Grounding")
        if f6:
            gy = _hy(min(15, (100 - end) / 2)); ev_f6 = dict(kind="foul", by="offense", yards=gy, outcome="off_between")
            txt += " " + self.foul_text(off, "Unsportsmanlike Conduct", gy, self.spot(off, end)) + "."
            pen = dict(penalty=1, penalty_team=off, penalty_type="Unsportsmanlike Conduct")
        if td: self.score[off] += 6
        if saf: self.score[dfn] += 2
        r_ad_ = self.row(**base, play_type=pt, yards_gained=y, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), desc=txt,
                 out_of_bounds=ob, td_team=off if td else np.nan, safety=saf, touchback=0, first_down=1 if (td or reached) else 0,
                 first_down_penalty=fdp_st, fumble_recovery_1_team=dfn if fum else np.nan, **self.flags(kind, comp, inc, itc, fum, td), **ids, **pen)
        if 1 <= r_ad_["yardline_100"] <= 5 and not pen and kind in CALL: self.cnt[f"ad addition item 4: a called snap, no foul, at the {r_ad_['yardline_100']} from a {'whole-yard' if float(yl0) == int(float(yl0)) else 'fractional'} spot: {'touchdown' if r_ad_['yards_gained'] >= r_ad_['yardline_100'] else 'no touchdown'}"] += 1   # v35 (ad addition item 4): the exact spot is not in the rows
        if R1B and 1 <= r_ad_["yardline_100"] <= 5 and not pen and kind in CALL: self.cnt[f"af0: a called snap, no foul, at the {r_ad_['yardline_100']} drawn at level {self.P['play2'].last}: {'touchdown' if r_ad_['yards_gained'] >= r_ad_['yardline_100'] else 'no touchdown'}"] += 1   # v36 af0: the level this snap's outcome resolved at (R1b: the model's snap pool, drawn on every such snap)
        if fam == "F5": self.cnt["foul F5"] += 1
        if f6: self.cnt["foul F6"] += 1
        # the clock after the play (the clock rule)
        ow = oob_window(self.q, qs0, self.reg); fw = foul_window(self.q, qs0, self.reg); pa = bool(pen)
        pv = _TRANS(st0, ev_f5, self.rb) if fam == "F5" else (_TRANS(dict(pv_snap, dfn=dfn), ev_f6, self.rb) if f6 else pv_snap)
        poss_change = bool(itc or fum or pv["kick"] or pv["off"] != off)
        ev = [("incomplete 4-4f", inc == 1), ("out of bounds late 4-3-2a", ob == 1 and ow is True), ("score/touchback/try 4-4d", bool(td or saf)),
              ("change of possession 4-4i", bool(poss_change)), ("foul in window 4-3-2e", pa and fw is True),
              ("out of bounds early 4-3-2a", ob == 1 and ow is False), ("foul outside windows 4-3-2e", pa and fw is False),
              ("out of bounds, window unread", ob == 1 and ow is None), ("foul, window unread", pa and fw is None)]
        runoff_ = False; inj_charge = None
        if R1D and self.q <= 4:   # the engine-vs-record stage v13-v14 e, f, d: the review and the injury are attributes of the drawn recorded play; their clock from the book's articles
            rv_ = int(o.get("rv", 0) or 0) == 1; inj_ = int(o.get("inj", 0) or 0) == 1; bw_ = rules.before_warning(self.q, qs0, self.reg); bw_ = None if bw_ is None else bool(bw_)
            iside = str(o.get("inj_side", "") or "")
            if inj_ and iside not in ("offense", "defense"):   # 4-5-4 charges the injured player's team: a drawn injury whose team its text does not name is not played
                inj_ = False; self.cnt["f: injury not played: the drawn row's text does not name the injured player's team"] += 1
            decision_cls = clock_class(ev, beyond(self.q, self.reg))[0]
            ev = ev + [("replay review 15-5-1", rv_), ("injury, from play text 4-5-3", inj_ and bw_ is True), ("injury after the warning 4-5-4", inj_ and bw_ is False),
                       ("injury, warning placement unread", inj_ and bw_ is None)]
            self.last_rv, self.last_inj = float(rv_), float(inj_)
            r_ = self.rows[-1]; r_["src"] = str(o.get("src", "") or "")
            if rv_:
                rev_ = int(o.get("rv_rev", 0) or 0) == 1
                r_["replay_or_challenge"] = 1; r_["desc"] = r_["desc"] + f" The Replay Official reviewed the decision, and the play was {'REVERSED' if rev_ else 'Upheld'}."
                self.cnt["e: reviewed plays (drawn)"] += 1
                if rev_ and self.q in self.warned:   # 15-5-2: a play begun after the warning, its decision changed
                    ow_ = oob_window(self.q, qs0, self.reg); fo_ = lambda c_: int(o.get(c_, 0) or 0) == 1
                    of_cls = clock_class([("incomplete 4-4f", fo_("of_inc")), ("out of bounds late 4-3-2a", fo_("of_ob") and ow_ is True), ("score/touchback/try 4-4d", fo_("of_score")),
                                          ("change of possession 4-4i", fo_("of_poss")), ("out of bounds early 4-3-2a", fo_("of_ob") and ow_ is False),
                                          ("out of bounds, window unread", fo_("of_ob") and ow_ is None)], beyond(self.q, self.reg))[0]
                    ok_std = decision_cls == "RUN" or (decision_cls == "PARTIAL" and RUNOFF_RESTART.get(self.season, False))
                    if of_cls == "STOP" and ok_std: runoff_ = True
                    else: self.cnt[f"e: 15-5-2 not applied after a reversal: on-field clock {of_cls}, standing {decision_cls}"] += 1
                side = str(o.get("rv_chal", "") or "")
                if side in ("offense", "defense") and not rev_:   # 15-6-1: a lost challenge charges the challenger a timeout (counted once: no timeout row is written)
                    tm_ = off if side == "offense" else dfn
                    if self.to_left[tm_] > 0: self.to_left[tm_] -= 1; self.cnt["e: a lost challenge charged a timeout (no row)"] += 1
                    else: raise record.DataGap("15-6-1: a lost challenge drawn for a team with no timeout left (excluded before the draw)")
            if inj_:
                team_ = off if iside == "offense" else dfn
                r_["desc"] = r_["desc"] + f" {team_}-00-SIM.P was injured during the play."; self.cnt["f: injury plays (drawn), unsupported: participation"] += 1
                if bw_ is False:   # 4-5-4 (a), (b) and their exceptions (1) a foul by an opponent, (2) a change of possession, touchdown, safety or field goal on the down
                    ps_ = str(o.get("pen_side", "") or "")
                    if ps_ in ("offense", "defense") and ps_ != iside: self.cnt["f: 4-5-4 exception (1): the injury on a foul by an opponent, no charge"] += 1
                    elif poss_change or td or saf: self.cnt["f: 4-5-4 exception (2): a change of possession, touchdown or safety on the down, no charge"] += 1
                    else: inj_charge = team_
        else:
            self.last_rv, self.last_inj = 0.0, 0.0
        self.own_cls = self.stop_after(ev, pair=True)
        if runoff_:   # 15-5-2: the clock reset to the play's end, 10 seconds run unless either team takes a charged timeout to avoid it
            rd = self.stop_draw("snap STOP", False) if getattr(self.R, "RACE", None) is not None else None
            tm_ = None
            if rd is not None and rd[0] == "unplayed": self.unsup.append((len(self.rows), "15-5-2's avoiding draw")); self.cnt["unsupported: an unplayed stoppage drawn (15-5-2's avoiding draw)"] += 1
            if rd is not None and rd[0] in ("offense", "defense"):
                tm_ = rd[1] if rd[0] == "offense" else rd[2]
                if self.to_left[tm_] <= 0: raise record.DataGap("15-5-2: an avoiding timeout drawn for a team with none left (its probability was 0)")
            if tm_ is not None:
                self.write_timeout(tm_); self.own_cls = "STOP"; self.cnt["e: 15-5-2 avoided by a charged timeout (the clock starts on the snap)"] += 1
            else:
                if self.clock <= 10: self.clock = 0; self.cnt["e: 15-5-2 runoff ended the half (under 10 s left)"] += 1
                else: self.clock = self.clock - 10
                self.rows[-1]["desc"] = self.rows[-1]["desc"] + " 10 second run-off."; self.cnt["e: 10-second runoff after a reversal (15-5-2)"] += 1
        self.after_play_warning(c0)
        if inj_charge is not None and not self.over and self.clock > 0:   # 4-5-4: the timeout written when the play ends (the clock stopped)
            if self.to_left[inj_charge] > 0: self.write_timeout(inj_charge); self.cnt["f: 4-5-4 charged team timeout (the injured player's team)"] += 1
            else:
                self.write_excess(inj_charge); self.cnt["f: 4-5-4 excess timeout called by the Referee"] += 1
                if inj_charge == off: self.cnt["f: 4-5-4 Note 3 not played: the defense's choice of a 10-second runoff after an excess timeout against the offense"] += 1
                if self.excess.get(inj_charge, 0) >= 2: self.cnt["f: 4-5-4 penalty not played: five yards for a second excess timeout"] += 1
            self.own_cls = "STOP"
        self.prev_kind = "snap"; self.foul_used = False
        # the result
        if td:
            self.end_possession("td")
            if not self.over and R1D and self.q <= 4 and self.clock > 0: self.race_moment(before_try=True)
            if not self.over: self.try_(off)
            return
        if saf:
            self.end_possession("safety")
            if not self.over: self.commit(pv_snap)
            return
        if itc or fum:
            self.end_possession("turnover")
            s_ = self.P["turn"].draw(self.rng, dict(ttype="interception" if itc else "fumble lost", field=field_bin(yl0)))["opp_yl"]
            self.commit(_TRANS(st0, dict(ev_snap, turn_end=int(s_)), self.rb)); return
        if pv["off"] != off: self.end_possession("downs")
        self.commit(pv)

    def punt(self, k):
        off, dfn = self.off, self.other(self.off); yl0, qs0 = self.yl, self.clock
        o = self.P["punt"].draw(self.rng, dict(field=field_bin(yl0))); s_ = int(o["opp_yl"]); tb = int(o["touchback"])
        self.qa = qs0; self.stretch_stop = False
        W, E, c0 = self.play("punt")
        self.row(**self.flags("punt"), play_type="punt", posteam=off, defteam=dfn, down=self.down, ydstogo=yl0 - self.ltg, yardline_100=yl0, yards_gained=0,
                 quarter_seconds_remaining=qs0, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), out_of_bounds=0, touchback=tb, safety=0,
                 first_down=0, first_down_penalty=0, desc=f"{clock_txt(qs0)} SIM-P punts to {'end zone, Touchback' if tb else self.spot(dfn, s_)}.")
        ev = [("score/touchback/try 4-4d", tb == 1), ("change of possession 4-4i", True)]
        self.own_cls = self.stop_after(ev); self.after_play_warning(c0); self.prev_kind = "snap"; self.foul_used = False
        self.end_possession("punt")
        st_p = _TRANS(self.state0(), dict(kind="punt", end=s_, tb=tb == 1), self.rb)
        if tb == 1 and st_p["yl"] != s_: self.chg.append((len(self.rows), "punt touchback", dict(team=dfn, new=int(st_p["yl"]), old=int(s_))))
        self.commit(st_p)

    def field_goal(self, k):
        off, dfn = self.off, self.other(self.off); yl0, qs0 = self.yl, self.clock; dist = yl0 + 17
        made = int(self.P["fg"].draw(self.rng, dict(dist5=dist // 5 * 5))["made"]) == 1
        self.qa = qs0; self.stretch_stop = False
        W, E, c0 = self.play("field_goal")
        if made: self.score[off] += 3
        self.row(**self.flags("field_goal"), play_type="field_goal", posteam=off, defteam=dfn, down=self.down, ydstogo=yl0 - self.ltg, yardline_100=yl0,
                 yards_gained=0, quarter_seconds_remaining=qs0, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), out_of_bounds=0, touchback=0, safety=0,
                 field_goal_result="made" if made else "missed", first_down=0, first_down_penalty=0,
                 desc=f"{clock_txt(qs0)} SIM-K {int(np.floor(dist))} yard field goal is {'GOOD' if made else 'No Good'}.")
        ev = [("score/touchback/try 4-4d", made), ("change of possession 4-4i", True)]
        self.own_cls = self.stop_after(ev); self.after_play_warning(c0); self.prev_kind = "snap"; self.foul_used = False
        self.end_possession("fg")
        if made:
            if not self.over: self.commit(_TRANS(self.state0(), dict(kind="field_goal", made=True), self.rb))
        else:
            s_ = int(self.P["fgmiss"].draw(self.rng, dict(field=field_bin(yl0)))["opp_yl"])
            self.commit(_TRANS(self.state0(), dict(kind="field_goal", made=False, end=s_), self.rb))

    def try_(self, team):
        dfn = self.other(team)
        h, a = self.score[team], self.score[dfn]
        ch = self.P["try"].draw(self.rng, dict(time=time_bin(self.q, self.clock), score=score_bin(h - a)))["choice"]
        g = self.gap("snap", "try"); self.advance(g)
        good = int(self.P["two" if ch == "two" else "xp"].draw(self.rng, {})["good"]) == 1
        W, E, _ = self.play("two" if ch == "two" else "xp", timed=False)
        if good: self.score[team] += 2 if ch == "two" else 1
        if ch == "two":
            self.row(play_type="pass", posteam=team, defteam=dfn, yardline_100=2, ydstogo=2, two_point_attempt=1, two_point_conv_result="success" if good else "failure",
                     desc=f"TWO-POINT CONVERSION ATTEMPT. SIM-{team} pass to SIM-WR. ATTEMPT {'SUCCEEDS' if good else 'FAILS'}.", time_of_day=self.stamp(W),
                     end_clock_time=self.stamp(E), passer_player_id=f"SIM-{team}-QB")
        else:
            self.row(play_type="extra_point", posteam=team, defteam=dfn, yardline_100=15, ydstogo=0, two_point_attempt=0, extra_point_result="good" if good else "failed",
                     desc=f"SIM-K extra point is {'GOOD' if good else 'No Good'}.", time_of_day=self.stamp(W), end_clock_time=self.stamp(E))
        self.prev_kind = "try"
        if self.in_ot:
            self.check_ot_end("try")
        if not self.over: self.commit(_TRANS({}, dict(kind="try", team=team, other=dfn), self.rb))

    def timeouts(self):
        nope = [sd for sd, tm in (("offense", self.off), ("defense", self.other(self.off))) if self.to_left[tm] <= 0]
        ok_ = (lambda V, nope=nope: ~np.isin(V[:, 0], nope)) if nope else None   # a timeout by a team with none left has probability 0 before the draw
        if nope: self.chg.append((len(self.rows), "timeout draw masked", dict(none_left=[self.off if sd == "offense" else self.other(self.off) for sd in nope])))
        if R1B and self.q <= 4:   # R1b: by situation (4-5-1)
            qa = self.qa if self.qa is not None else self.clock; dfn_ = self.other(self.off)
            av = ("O" if self.to_left[self.off] > 0 else "-") + ("D" if self.to_left[dfn_] > 0 else "-")
            c = self.P["to1"].draw(self.rng, dict(tb2=tb2(self.q, qa), ls=late_score(self.q, qa, self.score[self.off] - self.score[dfn_]), own=self.own_cls, avail=av), ok=ok_)["caller"]
        else:
            k = dict(time=time_bin(self.q, self.clock), score=score_bin(self.score[self.off] - self.score[self.other(self.off)]))
            c = self.P["to"].draw(self.rng, k, ok=ok_)["caller"]
        if c == "none": return
        team = self.off if c == "offense" else self.other(self.off)
        if self.to_left[team] <= 0: raise record.DataGap("a timeout drawn for a team with none left (its probability was 0)")
        g = self.gap("snap", "timeout"); res = self.advance(g)
        if self.clock == 0 or res == "warning": return
        self.to_left[team] -= 1; n_ = (HALF_TIMEOUTS if not self.in_ot else self.ot_to) - self.to_left[team]
        m, s = divmod(self.clock, 60)
        self.row(play_type="no_play", timeout=1, desc=f"Timeout #{n_} by {team} at {m:02d}:{s:02d}.", time_of_day=self.stamp(self.t))
        self.running = False; self.restart_at = None; self.stretch_stop = True; self.prev_kind = "timeout"
        self.cnt["timeouts"] += 1

    def race_moment(self, start=False, before_try=False):
        """the engine-vs-record stage v12: after a play that leaves the clock running (RUN), walk the race's seconds; at every stopped-clock act, the stopped part (v10 b)."""
        M = getattr(self.R, "RACE", None)
        if M is None or self.q > 4 or self.over or self.clock <= 0: return
        last = self.rows[-1] if self.rows else {}
        warned_now = str(last.get("desc", "")).startswith("Two-Minute")
        to_now = int(last.get("timeout", 0) or 0) == 1   # the engine-vs-record stage v14 d: a timeout written when the play ended (4-5-4, or one that avoids 15-5-2's runoff)
        if (not start and not before_try and not warned_now and not to_now and self.prev_kind == "snap" and self.own_cls == "RUN" and self.running
                and self.pending_kick is None):
            self.race_walk(); return
        if start: act = "start of the quarter"
        elif warned_now: act = "two-minute warning"
        elif to_now: act = "timeout"
        elif self.prev_kind == "snap": act = "snap PARTIAL" if self.own_cls == "PARTIAL" else "snap STOP"
        else: act = {"foul": "foul", "kickoff": "kickoff", "try": "try", "timeout": "timeout"}.get(self.prev_kind)
        if act is None: return
        self.race_stopped(act, before_try)

    def race_walk(self):
        M = self.R.RACE; off = self.off; dfn = self.other(off); ce = int(self.clock)
        base = [float(self.q), float(ce), float(self.score[off] - self.score[dfn]), float(self.down), float(self.yl - self.ltg), float(self.yl),
                float(self.to_left[off]), float(self.to_left[dfn]), float(self.last_rv), float(self.last_inj)]
        tw = ce - 120 if (warns(self.q, self.reg) and self.q not in self.warned and ce > 120) else None
        tb = min(ce, tw) if tw is not None else ce
        cls = M["run_cls"]; io, idf, isn = cls.index("offense"), cls.index("defense"), cls.index("snap")
        if1 = cls.index("F1") if "F1" in cls else None; if2 = cls.index("F2") if "F2" in cls else None
        z_ = lambda P, j: P[:, j] if j is not None else 0.0
        t0 = 0
        while t0 < tb:
            ts = np.arange(t0, min(t0 + RACE_CHUNK, tb))
            X = np.column_stack([np.tile(np.array(base), (len(ts), 1)), np.minimum(ts, M["t_cap"]).astype(float)])   # t read up to the pinned play clock, as fitted
            P = M["eval"]("run", X)
            gone = [j for j, tm in ((io, off), (idf, dfn)) if self.to_left[tm] <= 0]
            if gone:   # its probability 0 before the draw; each second's other outcomes rescaled to sum to one (one draw a second, as before)
                P = P.copy(); P[:, gone] = 0.0; P = P / P.sum(axis=1, keepdims=True); self.cnt["race: seconds with a team's timeout impossible (probability 0)"] += len(ts)
                self.chg.append((len(self.rows), "race timeout masked", {}))
            u = self.rng.random(len(ts)); c1 = P[:, io]; c2 = c1 + P[:, idf]; c3 = c2 + P[:, isn]; c4 = c3 + z_(P, if1); c5 = c4 + z_(P, if2)
            ev = np.where(u < c1, 1, np.where(u < c2, 2, np.where(u < c3, 3, np.where(u < c4, 4, np.where(u < c5, 5, 0)))))
            if "unplayed" in cls: ev = np.where((ev == 0) & (u < c5 + P[:, cls.index("unplayed")]), 6, ev)   # its own share of each second, as the race was fitted
            for k in np.where(ev > 0)[0]:
                t = int(ts[k]); self.cnt["g: race seconds at risk, a running clock"] += t + 1   # the event second included, as the record's race rows count it
                if ev[k] == 6:   # its defined transition: the clock stops at this second; its own effects are not played; the game UNSUPPORTED from here
                    self.advance(t); self.write_unplayed("the race, a running clock"); self.race_log.append((self.q, ce, "unplayed", t)); return
                if ev[k] == 3:
                    self.race_gap = t; self.race_log.append((self.q, ce, "snap", t)); self.cnt["race: snap drawn"] += 1; return
                if ev[k] in (4, 5):   # the engine-vs-record stage v13 d, p: a pre-snap foul the engine plays, at this second; Game.presnap enforces it, the race restarts from that state
                    fam_ = "F1" if ev[k] == 4 else "F2"
                    self.race_gap = t; self.race_foul = fam_; self.race_log.append((self.q, ce, fam_, t)); self.cnt[f"race: pre-snap foul {fam_} on a running clock"] += 1; return
                team = off if ev[k] == 1 else dfn
                if self.to_left[team] <= 0: raise record.DataGap("race: a timeout drawn for a team with none left (its probability was 0)")
                self.advance(t); self.write_timeout(team)
                self.race_log.append((self.q, ce, "offense" if team == off else "defense", t)); self.cnt["race: timeout drawn on a running clock"] += 1
                self.race_stopped("timeout", False); return
            t0 += len(ts)
        self.cnt["g: race seconds at risk, a running clock"] += tb   # every second walked to the boundary
        res = self.advance(tb)
        self.race_log.append((self.q, ce, "warning" if res == "warning" else "0:00", tb)); self.cnt[f"race: the clock ran to {'the warning' if res == 'warning' else '0:00'}"] += 1
        if res == "warning" and not self.over: self.race_stopped("two-minute warning", False)

    def write_unplayed(self, where):
        """An unplayed stoppage (a recorded stoppage kind the engine has no mechanics for) drawn: the clock stopped, a row written, the game UNSUPPORTED from it."""
        self.unsup.append((len(self.rows), where)); self.cnt[f"unsupported: an unplayed stoppage drawn ({where})"] += 1
        self.row(play_type="", desc=f"(an unplayed stoppage drawn by {where}: its own effects are not modeled; the game is unsupported from here)", time_of_day=self.stamp(self.t))
        self.running = False; self.restart_at = None; self.stretch_stop = True; self.prev_kind = "other"; self.foul_gap = None

    def write_timeout(self, team):
        self.to_left[team] -= 1; n_ = HALF_TIMEOUTS - self.to_left[team]
        m_, s_ = divmod(self.clock, 60)
        self.row(play_type="no_play", timeout=1, desc=f"Timeout #{n_} by {team} at {m_:02d}:{s_:02d}.", time_of_day=self.stamp(self.t))
        self.running = False; self.restart_at = None; self.stretch_stop = True; self.prev_kind = "timeout"; self.cnt["timeouts"] += 1

    def stop_draw(self, act, before_try):
        """The stopped part's draw at a stopped-clock act: (the class drawn, the offense, the defense), or None when no team holds the ball."""
        M = self.R.RACE; cls = M["stop_cls"]
        if before_try: off = self.other(self.off); kick = True
        elif self.pending_kick is not None: off = self.other(self.pending_kick[0]); kick = True
        else: off = self.off; kick = False
        if off is None: return None
        dfn = self.other(off)
        x = [float(self.q), float(self.clock), float(self.score[off] - self.score[dfn]), -1.0 if kick else float(self.down), -1.0 if kick else float(self.yl - self.ltg),
             -1.0 if kick else float(self.yl), float(self.to_left[off]), float(self.to_left[dfn]), float(RACE_STOP_ACTS.index(act)),
             float(self.last_rv) if act.startswith("snap") else 0.0, float(self.last_inj) if act.startswith("snap") else 0.0]
        p = M["eval"]("stop", np.array([x]))[0]
        gone = [cls.index(c_) for c_, tm in (("offense", off), ("defense", dfn)) if c_ in cls and self.to_left[tm] <= 0]
        if gone:   # its probability 0 before the draw; the draw below takes the others in proportion
            p = p.copy(); p[gone] = 0.0; self.cnt["race (stopped): draws with a team's timeout impossible (probability 0)"] += 1
            self.chg.append((len(self.rows), "stopped-part timeout masked", {}))
        c = cls[int(np.searchsorted(np.cumsum(p), self.rng.random() * p.sum(), side="right"))] if p.sum() > 0 else "none"
        return c, off, dfn

    def write_excess(self, team):
        """4-5-4 (b): a team with no charged timeout left: an excess team timeout called by the Referee (written, not charged against the three)."""
        self.excess[team] = self.excess.get(team, 0) + 1; n_ = HALF_TIMEOUTS + self.excess[team]
        m_, s_ = divmod(self.clock, 60)
        self.row(play_type="no_play", timeout=1, desc=f"Timeout #{n_} by {team} at {m_:02d}:{s_:02d}. Excess timeout called by the Referee (injury).", time_of_day=self.stamp(self.t))
        self.running = False; self.restart_at = None; self.stretch_stop = True; self.prev_kind = "timeout"; self.cnt["timeouts"] += 1

    def race_stopped(self, act, before_try):
        while True:
            if self.clock <= 0 or self.over: return
            r_ = self.stop_draw(act, before_try)
            if r_ is None: return
            c, off, dfn = r_
            if c == "unplayed": self.write_unplayed(f"the stopped part, after {act}"); return   # the clock already stopped; its own effects are not played; UNSUPPORTED from here
            if c == "none": return
            if c in ("F1", "F2"):   # the engine-vs-record stage v13 d, p: a pre-snap foul before the snap on a stopped clock; the floor's gap to it, then Game.presnap
                self.race_foul = c; self.cnt[f"race (stopped): pre-snap foul {c}"] += 1; return
            team = off if c == "offense" else dfn
            if self.to_left[team] <= 0: raise record.DataGap("race (stopped): a timeout drawn for a team with none left (its probability was 0)")
            if self.foul_gap is not None:   # v19 y1: a timeout called in place of the snap after a foul's restart, at its drawn second (within the play clock)
                g = self.foul_gap; self.foul_gap = None; self.cnt["y1: a timeout drawn at a foul restart's drawn second"] += 1
            else: g = int(self.gap(self.prev_kind, "timeout"))
            res = self.advance(g)
            if self.clock == 0: self.cnt["race (stopped): timeout drawn, 0:00 came first"] += 1; return
            if res == "warning": self.cnt["race (stopped): timeout drawn, the warning came first"] += 1; act = "two-minute warning"; before_try = False; continue
            self.write_timeout(team); self.cnt["race (stopped): timeout drawn"] += 1
            act = "timeout"; before_try = False

    # ---- the game
    def end_quarter(self):
        self.row(play_type="", desc="END QUARTER " + str(self.q) if not (self.q >= 4 and self.game_done()) else "END GAME")

    def game_done(self):
        if self.over: return True
        if self.q == 4: return self.score[self.home] != self.score[self.away]
        if self.q >= 5: return self.reg or self.score[self.home] != self.score[self.away]
        return False

    def run(self):
        self.row(play_type="", desc="GAME")
        first = self.home if self.rng.integers(2) else self.away   # the toss is not in the record
        self.pending_kick = (self.other(first), "normal")
        if R1D: self.race_moment(start=True)
        while True:
            if self.over:
                self.row(play_type="", desc="END GAME"); break
            if self.clock == 0:
                done = self.game_done()
                self.end_quarter()
                if done: break
                self.q += 1; self.clock = 900; self.running = False; self.restart_at = None; self.qa = None; self.own_cls = None; self.prev_kind = "other"
                self.foul_used = False; self.stretch_stop = True; self.pair_x = None; self.foul_gap = None
                if self.q == 3:
                    self.to_left = {self.home: HALF_TIMEOUTS, self.away: HALF_TIMEOUTS}; self.excess = {}
                    self.pending_kick = (first, "normal")   # the second half: the first half's receiver kicks (the choice is not in the record)
                if self.q >= 5:
                    self.in_ot = True; self.clock = self.ot_len
                    if self.reg or (self.q - 5) % 2 == 0:   # 16-1-3(e) / 16-1-4(g): the regular-season period, or each postseason overtime half
                        self.to_left = {self.home: self.ot_to, self.away: self.ot_to}
                    if self.q == 5:
                        r_ = self.home if self.rng.integers(2) else self.away
                        self.ot_first_recv = r_; self.pending_kick = (self.other(r_), "normal")
                    elif (self.q - 5) % 2 == 0:   # 16-1-4(e): a third (fifth...) postseason period starts like a half, with a kickoff
                        self.pending_kick = (self.ot_first_recv, "normal")
                if R1D and self.q <= 4: self.race_moment(start=True)
                continue
            if self.pending_kick is not None:
                self.kickoff()
                if R1D and self.q <= 4 and not self.over and self.clock > 0: self.race_moment()
                continue
            self.attempt()
        for r in self.rows:
            r["home_score"] = self.score[self.home]; r["away_score"] = self.score[self.away]
        return self.rows


def onside_allowed(rule, q, kick_diff):
    """the season rules's onside rule (quoted from the season's book) -> may the kicking team try one, in period q, with this score difference (kicking team minus receivers)."""
    if rule == "any free kick": return True
    if rule == "4th period, kicking team trailing, declared": return q == 4 and kick_diff < 0
    if rule == "any period, kicking team trailing, declared": return kick_diff < 0
    raise record.DataGap(f"engine: the season rules's onside rule {rule!r} is not one the engine plays")


def season_rules_rows():
    return {s: rules.season_rule_quotes(s) for s in SIM_SEASONS}


def play_season(season, sched, rates, season_rules, seed):
    rng = np.random.default_rng([seed, season])
    rows, dec, cnt = [], [], Counter()
    for _, g in sched.iterrows():
        G = Game(g, rates, season_rules, rng, season); rows += G.run(); cnt.update(G.cnt)
        if G.declared: dec.append((g["game_id"], G.declared))
    return rows, dec, cnt


def text_frame(rows):
    f = pd.DataFrame(rows)
    if "pass_" in f.columns: f = f.drop(columns=["pass_"])
    for c in COLS:
        if c not in f.columns: f[c] = np.nan
    f = f[COLS]
    out = pd.DataFrame(index=f.index)
    for c in COLS:
        v = f[c]
        out[c] = [("" if nan(x) else (str(int(x)) if isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, bool) else str(x))) for x in v]
    return out


# ---------------- the record checks, run on the engine's games ----------------
class OnSim:
    """record.raw_frame pointed at the engine's rows (season -> text frame): the only change; every read and every check runs unchanged."""
    def __init__(self, frames):
        self.frames = frames; self.saved = None

    def __enter__(self):
        self.saved = record.raw_frame
        def raw_frame(name, columns, where):
            m = re.fullmatch(r"pbp_(\d{4})\.csv\.gz", name)
            if not m or int(m.group(1)) not in self.frames:
                raise record.DataGap(f"{where}: the engine wrote no {name}")
            missing = [c for c in columns if c not in self.frames[int(m.group(1))].columns]
            if missing: raise record.DataGap(f"{where}: columns absent from the engine's {name}: {missing}")
            return self.frames[int(m.group(1))][list(columns)].copy()
        record.raw_frame = raw_frame
        return self

    def __exit__(self, *a):
        record.raw_frame = self.saved


def check_r4(seasons):
    items = []
    for s in seasons:
        D = check_downs.load(s)
        for _, gd in D.groupby("game_id", sort=False):
            it, _ = check_downs.checks(gd); items += it
    I = pd.DataFrame(items)
    words = Counter(I["word"]) if len(I) else Counter()
    bad = I[I["word"].isin(["OTHER", "UNCHECKED"])] if len(I) else I
    return words, bad


def check_r1(seasons):
    D = pd.concat([check_possessions.load(s) for s in seasons], ignore_index=True).sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
    P = check_possessions.possessions(D)
    G = {g: d.sort_values("order_sequence").reset_index(drop=True) for g, d in D.groupby("game_id")}
    b2b, oth, C = check_possessions.counts(P, G)
    left = oth[oth["word"].str.startswith(("UNEXPLAINED", "MULTIPLE"))] if len(oth) else oth
    return C, left, P


def stopping_rows(c, bt, q, qa, reg, posb):
    fw = foul_window(q, qa, reg)
    for k in bt:
        if one(c["timeout"][k]) or str(c["desc"][k] or "").startswith("Two-Minute Warning"): return k
        if one(c["penalty"][k]) and (fw is True or (q >= 4 and c["penalty_team"][k] == posb and c["penalty_type"][k] in PRESNAP_OFFENSE)): return k
    return None


def check_clock(seasons):
    """Section 4, the stopped clock, and check_clock's FASTER and classes."""
    out = Counter(); fails = []
    for s in seasons:
        d, _, _ = check_clock.load(s)
        for _, g in d.groupby("game_id", sort=False):
            g = g.reset_index(drop=True); c = {k: g[k].tolist() for k in g.columns}
            iv = check_clock.intervals(g)
            idx = {int(v): k for k, v in enumerate(c["order_sequence"])}
            for x in iv:
                out[f"check_clock class {x['cls']}"] += 1; out[f"check_clock game level {x['game_level']}"] += 1
                if x["cls"] == "UNKNOWN":
                    out[f"check_clock UNKNOWN: {x['why']}"] += 1; fails.append(("UNKNOWN", s, x["game_id"], x["sa"], x["sb"], x["q"], x["reg"], x["why"]))
                a, b = idx[x["sa"]], idx[x["sb"]]; bt = list(range(a + 1, b))
                if x["cls"] == "PARTIAL":
                    ok = x["dG"] <= x["dW"]
                    out["PARTIAL checked"] += 1
                    if not ok: out["PARTIAL failed"] += 1; fails.append(("PARTIAL", x["game_id"], x["sa"], x["sb"], x["dG"], x["dW"], x["why"]))
                if x["cls"] != "STOP": continue
                out["STOP checked"] += 1
                q, qa, reg = x["q"], x["qa"], x["reg"]
                plays = [a] + [k for k in bt if c["play_type"][k] in ("kickoff", "extra_point") or one(c["two_point_attempt"][k])
                               or (c["play_type"][k] == "no_play" and one(c["penalty"][k]) and has_play(c["desc"][k]))]
                ln = 0.0; miss = False
                for k in plays:
                    if nan(c["E_s"][k]) or nan(c["W_s"][k]): miss = True; break
                    ln += check_clock.diff(c["E_s"][k], c["E_d"][k], c["W_s"][k], c["W_d"][k])[0]
                if miss: out["STOP with a play unstamped (failed)"] += 1; fails.append(("STOP unstamped", x["game_id"], x["sa"], x["sb"])); continue
                ow = oob_window(q, qa, reg); fwa = foul_window(q, qa, reg)
                own = [("incomplete 4-4f", one(c["incomplete_pass"][a])), ("out of bounds late 4-3-2a", one(c["out_of_bounds"][a]) and ow is True),
                       ("score/touchback/try 4-4d", one(c["touchdown"][a]) or c["field_goal_result"][a] == "made" or one(c["safety"][a]) or one(c["touchback"][a])),
                       ("change of possession 4-4i", c["posteam"][b] != c["posteam"][a] or one(c["interception"][a]) or one(c["fumble_lost"][a])),
                       ("foul in window 4-3-2e", one(c["penalty"][a]) and fwa is True)]
                if any(f for _, f in own):
                    run_before = 0.0
                else:
                    k = stopping_rows(c, bt, q, qa, reg, c["posteam"][b])
                    if k is None:
                        out["STOP with no stopping event found (failed)"] += 1; fails.append(("STOP no stop event", x["game_id"], x["sa"], x["sb"], x["why"])); continue
                    run_before = check_clock.diff(c["W_s"][k], c["W_d"][k], c["E_s"][a], c["E_d"][a])[0]
                allowed = ln + run_before + 1
                if x["dG"] > allowed:
                    out["STOP failed"] += 1; fails.append(("STOP", x["game_id"], x["sa"], x["sb"], x["dG"], round(allowed, 1), x["why"]))
    return out, fails


def check_periods(frames, season_rules, seasons):
    out = Counter(); bad = []
    for s in seasons:
        f = frames[s]
        for gid, g in f.groupby("game_id", sort=False):
            q = g["qtr"].astype(int); qs = g["quarter_seconds_remaining"].replace("", np.nan).astype(float)
            reg = g["season_type"].iloc[0] == "REG"
            ok = all((q == k).any() and qs[q == k].max() == 900 and qs[q == k].min() == 0 for k in (1, 2, 3, 4))
            ends = g[g["desc"].isin(["END QUARTER 4", "END GAME"]) & (q == 4)]
            if not len(ends): ok = False; h4 = a4 = None
            else: h4, a4 = int(ends["total_home_score"].iloc[0]), int(ends["total_away_score"].iloc[0])
            has_ot = (q >= 5).any()
            tied4 = h4 == a4
            if has_ot != tied4: ok = False   # 16-1-1: overtime exactly when tied after regulation; no playoff game ends tied (the rules level)
            if has_ot:
                mx = qs[q == 5].max()
                if mx != int(season_rules[s]["ot_reg_len" if reg else "ot_post_len"]["value"]): ok = False
                if not reg and int(g["home_score"].iloc[0]) == int(g["away_score"].iloc[0]): ok = False
            out["games"] += 1; out["games with overtime"] += int(has_ot)
            if not ok: out["games failing the period check"] += 1; bad.append(gid)
    return out, bad


def season_rule_check(seasons, season_rules):
    import measure_season_rules
    out = {}
    for s in seasons:
        d, qf = measure_season_rules.season_frame(s); M = measure_season_rules.measures(d, qf)
        out[s] = {m: M[m][0] for m in ("M1", "M2", "M3", "M4")}
    return out


def main():
    print("main is run by the E1a run block")


if __name__ == "__main__":
    main()


# ---------------- engine alone (the engine-vs-record stage v19 q, r3): the model files in out/engine/, each sha checked on load; the games played from them, nothing else read ----------------
# out/engine/MANIFEST.json names every file with its sha (and the run and engine.py that wrote them): conf.pkl (the caller-set values: PACE_SPLIT,
# RUNOFF_RESTART, SCRIM_TB, BOOKY, ENF_CLOCK; the race's flags R1A, R1B, R1D, QE_BAND; the play clock T_CAP; the seasons), tables.pkl (each season's pools' rows,
# prep()), season_rules.pkl (each season's quoted rule cells), sched.pkl (the games to play, in the order their generators are numbered), race_<season>.pkl (the race and the
# stopped part fitted for that season: the race as its parts, the fitted logistic model, the numbers' means and spreads and the play clock, rebuilt here as
# _LRRace, the run's estimator's own design; the stopped part the fitted trees). A file missing, or not the sha its manifest names, stops the load.
import pickle as _pk, threading as _th
ENGINE_DIR = "out/engine"


def engine_load(d=ENGINE_DIR):
    """Every file the manifest names, its sha checked before it is read; the caller-set values set on this module. Returns what the games need."""
    mp = os.path.join(d, "MANIFEST.json")
    if not os.path.exists(mp): raise record.DataGap(f"engine alone: {mp} missing: no model files to play from")
    player = json.load(open(mp)); raw = {}
    for f, want in sorted(player["files"].items()):
        p = os.path.join(d, f)
        if not os.path.exists(p): raise record.DataGap(f"engine alone: {p} missing (the manifest names it)")
        b = open(p, "rb").read(); got = hashlib.sha256(b).hexdigest()[:12]
        print(f"engine alone: {f} {got} (manifest {want}) {'ok' if got == want else 'DIFFERS'}")
        if got != want: raise record.DataGap(f"engine alone: {f} is {got}, not the manifest's {want}: nothing played")
        raw[f] = b
    conf = _pk.loads(raw["conf.pkl"])
    for k, v in conf["module"].items(): globals()[k] = v
    return dict(conf=conf, tables=_pk.loads(raw["tables.pkl"]), season_rules=_pk.loads(raw["season_rules.pkl"]), sched=_pk.loads(raw["sched.pkl"]),
                race={s: raw[f"race_{s}.pkl"] for s in conf["seasons"]})


RACE_TBINS = ((0, 7), (8, 15), (16, 23), (24, 31), (32, 40))   # v19 w1: the seconds already run on the play clock, in 8-second bins, crossed with the time left in the half


def race_design(X, mu, sd, tcap):
    """v19 w1: the race's inputs (the same text in engine.py): the numbers standardised; t (the seconds since the play ended, read up to the play clock) one
    indicator a second; and the time left in the half crossed with t: the last two minutes of a half (quarters 2 and 4, the quarter's clock at the play's end
    less t at or under 120) and quarters 2 and 4 apart from 1 and 3, each times RACE_TBINS. X: q, the clock at the play's end, the score difference, down,
    distance, yard line, the timeouts each side has, review, injury, t."""
    t = np.clip(X[:, -1].astype(int), 0, tcap)
    I = np.zeros((len(X), tcap)); r = np.where(t > 0)[0]; I[r, t[r] - 1] = 1.0
    q = X[:, 0]; q24 = (q == 2) | (q == 4); late = q24 & ((X[:, 1] - X[:, -1]) <= 120)
    B = np.column_stack([(t >= a_) & (t <= b_) for a_, b_ in RACE_TBINS]).astype(float)
    return np.column_stack([(X[:, :-1] - mu) / sd, I, B * late[:, None], B * q24[:, None]])


class _LRRace:
    """The race as the run fitted it (its LRRace): its inputs by race_design (v19 w1), the fit's means and spreads, the play clock."""
    def __init__(self, m, mu, sd, tcap):
        self.m, self.mu, self.sd, self.tcap = m, mu, sd, tcap; self.classes_ = m.classes_

    def design(self, X):
        return race_design(X, self.mu, self.sd, self.tcap)

    def predict_proba(self, X):
        return self.m.predict_proba(self.design(X))


def race_models(b):
    """A season's race_<season>.pkl: None (the race off), or the race's parts and the stopped part's trees."""
    r = _pk.loads(b)
    return None if r is None else {"run": _LRRace(**r["run"]), "stop": r["stop"]}


class _Batcher:
    """The race's models evaluated for every game's thread at once (one batch when every live game waits)."""
    def __init__(self, parts, n):
        self.parts = parts; self.cv = _th.Condition(); self.active = n; self.req = {}; self.res = {}; self.err = None; self.batches = 0

    def eval(self, part, X):
        tid = _th.get_ident()
        with self.cv:
            self.req[tid] = (part, X); self._run()
            self.cv.wait_for(lambda: tid in self.res or self.err is not None)
            if self.err is not None and tid not in self.res: raise self.err
            return self.res.pop(tid)

    def done(self):
        with self.cv:
            self.active -= 1; self._run()

    def _run(self):
        if not self.req or len(self.req) < self.active: return
        try:
            for part in {p for p, _ in self.req.values()}:
                ids = [t for t, (p, _) in self.req.items() if p == part]; Xs = [self.req[t][1] for t in ids]
                P = self.parts[part].predict_proba(np.vstack(Xs)); k = 0
                for t, x in zip(ids, Xs): self.res[t] = P[k:k + len(x)]; k += len(x)
            self.batches += 1
        except Exception as ex_:
            self.err = ex_
        self.req.clear(); self.cv.notify_all()


def play_alone(d=ENGINE_DIR, games=None):
    """Each season's games from the model files in d, each game with its own generator ([SEED, season, its place in the season's schedule]); games: the
    game ids to play (None: every game in sched.pkl). Returns {season: the rows in the record's columns (text_frame)} and the games not played."""
    E = engine_load(d); seas = E["conf"]["seasons"]; out = {}; skipped = {}
    for s in seas:
        sch = [g for _, g in E["sched"][E["sched"]["season"] == s].iterrows()]
        todo = [(k, g) for k, g in enumerate(sch) if games is None or g["game_id"] in games]
        if not todo: continue
        Rs = Rates(s, [E["tables"][x][0] for x in seas if x != s]); Rs.RACE_MODELS = race_models(E["race"][s])   # None: the race off (the floor)
        MOD = Rs.RACE_MODELS; B = _Batcher(MOD, len(todo))
        Rs.RACE = dict(eval=B.eval, run_cls=list(MOD["run"].classes_), stop_cls=list(MOD["stop"].classes_), t_cap=E["conf"]["t_cap"]) if MOD is not None else None
        rows = [None] * len(todo); sk = [None] * len(todo)
        def work(j, k, g):
            try: rows[j] = Game(g, Rs, E["season_rules"], np.random.default_rng([SEED, s, k]), s).run()
            except record.DataGap as ex_: sk[j] = str(ex_)[:120]
            finally: B.done()
        th = [_th.Thread(target=work, args=(j, k, g)) for j, (k, g) in enumerate(todo)]
        for t_ in th: t_.start()
        for t_ in th: t_.join()
        if B.err is not None: raise B.err
        out[s] = text_frame([r_ for rr_ in rows if rr_ is not None for r_ in rr_]); skipped[s] = [x_ for x_ in sk if x_]
    return out, skipped


def alone_main(argv):
    """python3 -c 'import engine, sys; engine.alone_main(sys.argv[1:])' ENGINE_DIR OUT_DIR [GAMES.json]: each season's games written to OUT_DIR/alone_<season>.csv."""
    d, od = argv[0], argv[1]; games = set(json.load(open(argv[2]))) if len(argv) > 2 else None
    os.makedirs(od, exist_ok=True); out, sk = play_alone(d, games)
    for s, f in out.items():
        f.to_csv(os.path.join(od, f"alone_{s}.csv"), index=False)
        print(f"engine alone: season {s}: games {f['game_id'].nunique()} | rows {len(f)} | not played {len(sk[s])} | sha {hashlib.sha256(f.to_csv(index=False).encode()).hexdigest()[:12]}")
