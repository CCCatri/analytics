"""rules: the one authority for football's accounting. Typed event classification from a raw play row, the official statistical credits
of an event (NFL Guide for Statisticians: passer/receiver linkage, laterals, sacks, kneels, spikes), legal gain support (Rules 1-1-1, 3-11-9),
and the state transition of a simulated play (Rules 3-8, 7-1, 7-3, 11, 16). No statistical fitting lives here."""
import dataclasses
import numpy as np
import policy as K

# event kinds (offensive scrimmage snaps first, then the state-only events)
PASS, SACK, SCRAMBLE, RUN, KNEEL, SPIKE = "pass", "sack", "scramble", "run", "kneel", "spike"
PUNT, FIELD_GOAL, KICKOFF, TRY, PENALTY, OTHER = "punt", "field_goal", "kickoff", "try", "penalty", "other"
SCRIMMAGE = (PASS, SACK, SCRAMBLE, RUN, KNEEL, SPIKE)          # a live offensive snap: a down from scrimmage the offense ran
DROPBACK = (PASS, SACK, SCRAMBLE, SPIKE)                        # the dropback branch (mutually exclusive)
CARRY_KINDS = (RUN, SCRAMBLE, KNEEL)                            # events credited as a carry
ATTEMPT_KINDS = (PASS, SPIKE)                                   # events credited as a pass attempt
POSITION_GROUP = {"QB": "QB", "RB": "RB", "HB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
                  "T": "OL", "G": "OL", "C": "OL", "OT": "OL", "OG": "OL", "OL": "OL", "LS": "OL"}   # the roster files carry coarse positions; FB/HB are backs
OFFENSE_GROUPS = ("QB", "RB", "WR", "TE", "OL", "OTHER")


def is_offensive_snap(kind, personnel):
    """The snap standard (Rule 5-2-2, narrowed by the claim to offensive downs from scrimmage): every live scrimmage down counts; a down nullified by a
    penalty (no-play) counts when the recorded personnel shows an offensive unit (a QB on the field, no K or P: not a kick formation); tries and kicks
    never count. A no-play without recorded personnel is unknown (False here, counted by the caller)."""
    if kind in SCRIMMAGE: return True
    if kind != PENALTY: return False
    g = personnel_counts(personnel)
    if g is None: return False
    raw = {b.strip().split()[1] for b in personnel.split(",") if len(b.strip().split()) == 2}
    return g["QB"] >= 1 and not ({"K", "P"} & raw)


def personnel_counts(text):
    """The recorded personnel string of the participation file ('1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR') as counts per OFFENSE_GROUPS; None when unparseable."""
    if not isinstance(text, str) or not text.strip(): return None
    out = {g: 0 for g in OFFENSE_GROUPS}
    for part in text.split(","):
        bits = part.strip().split()
        if len(bits) != 2 or not bits[0].isdigit(): return None
        out[position_group(bits[1])] += int(bits[0])
    return out


def position_group(position):
    return POSITION_GROUP.get(position, "OTHER") if isinstance(position, str) else "OTHER"


def classify(r):
    """The typed event of one raw play-by-play row (a dict-like with the nflverse columns). Returns None for rows that are no event
    (timeouts, end of period, missing play_type). A two-point try is TRY (its yards are not official, Rule 11-3-1); a flagged no-play is PENALTY."""
    pt = r.get("play_type")
    if not isinstance(pt, str): return None
    if r.get("two_point_attempt") == 1 or pt == "extra_point": return TRY
    if pt == "no_play": return PENALTY
    if pt == "qb_kneel": return KNEEL
    if pt == "qb_spike": return SPIKE
    if pt == "punt": return PUNT
    if pt == "field_goal": return FIELD_GOAL
    if pt == "kickoff": return KICKOFF
    if r.get("sack") == 1: return SACK
    if r.get("qb_scramble") == 1: return SCRAMBLE
    if r.get("rush") == 1 or pt == "run": return RUN
    if r.get("pass") == 1 or pt == "pass": return PASS
    return OTHER


@dataclasses.dataclass(frozen=True)
class Event:
    """One generated or observed offensive event with its outcome. yards: the official yards of the play (gain from the previous spot).
    lateral_*: a backward pass after the catch or the handoff: the ball carrier after it gets the yards after it (Rules 8-7-1, 3-21-4)."""
    kind: str
    passer: object = None
    receiver: object = None
    rusher: object = None
    complete: int = 0
    interception: int = 0
    touchdown: int = 0
    yards: int = 0
    lateral_receiver: object = None
    lateral_rec_yards: int = 0
    lateral_rusher: object = None
    lateral_rush_yards: int = 0


def credits(e):
    """The official stat increments of an event: a list of (player, stat, increment). Passing and receiving are the same realized event:
    a completion's yards are the passer's passing yards and the receivers' receiving yards (split at a lateral); its touchdown is one
    pass_td and one rec_td. A sack is no passing stat. A kneel is a carry; a spike is an attempt."""
    out = []
    if e.kind in ATTEMPT_KINDS and e.passer is not None:
        out.append((e.passer, "attempts", 1))
    if e.kind == PASS:
        if e.receiver is not None: out.append((e.receiver, "targets", 1))
        if e.interception and e.passer is not None: out.append((e.passer, "interceptions", 1))
        if e.complete and e.passer is not None and e.receiver is not None:
            out.append((e.passer, "completions", 1)); out.append((e.receiver, "receptions", 1))
            own = e.yards - (e.lateral_rec_yards if e.lateral_receiver is not None else 0)
            out.append((e.passer, "pass_yards", e.yards)); out.append((e.receiver, "rec_yards", own))
            if e.lateral_receiver is not None: out.append((e.lateral_receiver, "rec_yards", e.lateral_rec_yards))
            if e.touchdown:
                out.append((e.passer, "pass_td", 1))
                scorer = e.lateral_receiver if e.lateral_receiver is not None else e.receiver
                out.append((scorer, "rec_td", 1)); out.append((scorer, "tds", 1))
    if e.kind in CARRY_KINDS and e.rusher is not None:
        own = e.yards - (e.lateral_rush_yards if e.lateral_rusher is not None else 0)
        out.append((e.rusher, "carries", 1)); out.append((e.rusher, "rush_yards", own))
        if e.lateral_rusher is not None: out.append((e.lateral_rusher, "rush_yards", e.lateral_rush_yards))
        if e.touchdown:
            scorer = e.lateral_rusher if e.lateral_rusher is not None else e.rusher
            out.append((scorer, "rush_td", 1)); out.append((scorer, "tds", 1))
    return out


def gain_support(kind, yardline):
    """Legal integer gains of a non-scoring play from yardline_100 = yardline (Rules 1-1-1, 3-11-9, 11-2-1, 11-5-1): the ball stays between the
    goal lines, so -(100 - yardline) < gain < yardline. A gain of yardline is a touchdown and a loss of (100 - yardline) a safety: their own
    branches. A sack (and a kneel) cannot gain: hi = 0."""
    lo = -(K.FIELD_YARDS - int(yardline)) + 1
    hi = int(yardline) - 1 if kind not in (SACK, KNEEL) else 0
    return lo, min(hi, int(yardline) - 1)


def fg_distance(yardline):
    """Kick distance in yards: the line of scrimmage to the goal post is yardline + 10 (end zone) + the hold 7 behind the line."""
    return int(yardline) + 10 + K.FG_SNAP_TO_HOLD


def fg_miss_spot(yardline):
    """Rule 11-4-2 / 11-6-2: after a missed field goal the defense takes over at the spot of the kick (the hold), or its 20 if beyond its 20."""
    spot_from_goal = int(yardline) + K.FG_SNAP_TO_HOLD                    # the hold's distance from the defending goal
    return min(K.FIELD_YARDS - spot_from_goal, 80) if spot_from_goal < K.FIELD_YARDS - 20 else 80


# ----------------------------------------------------------------------------------------------------------------------------- state
# Vectorised game state over worlds: every field is an array of length W. Possession is 0 (home) or 1 (away); yardline is yardline_100 for
# the team in possession; half is 1, 2 or 3 (overtime); seconds is the time remaining in the half (or the overtime period).
STATE_FIELDS = ("poss", "yardline", "down", "ydstogo", "half", "seconds", "score_home", "score_away", "done", "drive_no", "prior_class",
                "ot_first_poss_done", "ot_first_poss_team", "ot_first_score", "ot_sudden")
CLOCK_CLASSES = ("run_inbounds", "complete_inbounds", "stopped", "scoring", "change", "kick")   # what stopped or ran the clock after a play (Rules 4-3, 4-4)


def new_state(W, receiving_team):
    """Kickoff state: the receiving team starts its first drive after the opening kickoff (field position drawn by the caller)."""
    s = {"poss": np.array(receiving_team, dtype=np.int8) if np.ndim(receiving_team) else np.full(W, receiving_team, dtype=np.int8),
         "yardline": np.full(W, K.KICKOFF_TOUCHBACK_YARDLINE_100, dtype=np.int16), "down": np.ones(W, dtype=np.int8),
         "ydstogo": np.full(W, K.LINE_TO_GAIN, dtype=np.int8), "half": np.ones(W, dtype=np.int8), "seconds": np.full(W, K.HALF_SECONDS, dtype=np.int32),
         "score_home": np.zeros(W, dtype=np.int16), "score_away": np.zeros(W, dtype=np.int16), "done": np.zeros(W, dtype=bool),
         "drive_no": np.zeros(W, dtype=np.int16), "prior_class": np.full(W, CLOCK_CLASSES.index("kick"), dtype=np.int8),
         "ot_first_poss_done": np.zeros(W, dtype=bool), "ot_first_poss_team": np.full(W, -1, dtype=np.int8),
         "ot_first_score": np.zeros(W, dtype=np.int16), "ot_sudden": np.zeros(W, dtype=bool)}
    return s


def first_and_ten(s, m, yardline):
    """A new series at yardline for the worlds in m: first down, line to gain 10 or the goal line (Rule 7-1-1)."""
    y = np.asarray(yardline); s["yardline"][m] = y[m] if y.shape == m.shape else y
    s["down"][m] = 1; s["ydstogo"][m] = np.minimum(K.LINE_TO_GAIN, s["yardline"][m])


def change_possession(s, m, new_yardline_for_defense):
    """The defense takes the ball at new_yardline_for_defense (its yardline_100) in the worlds m; a new drive begins."""
    s["poss"][m] = 1 - s["poss"][m]; s["drive_no"][m] += 1
    first_and_ten(s, m, new_yardline_for_defense)


def add_points(s, m, team, pts):
    """team: array of 0/1 (home/away) per world; pts: scalar or array."""
    home = m & (team == 0); away = m & (team == 1)
    p = np.broadcast_to(np.asarray(pts), s["poss"].shape)
    s["score_home"][home] += p[home]; s["score_away"][away] += p[away]


def advance(s, m, gain):
    """A non-scoring scrimmage play that keeps possession: the ball moves gain yards (Rule 3-11-9 keeps it between the goal lines by the
    caller's support); a new series when the line to gain is reached, else the next down (Rule 7-1-1). Returns the mask of fourth-down failures
    (down would become 5), which hand the ball over at the spot (Rule 7-1-1(b))."""
    g = np.asarray(gain)
    s["yardline"][m] -= g[m] if g.shape == m.shape else g
    made = m & (g >= s["ydstogo"]) if g.shape == m.shape else m & (g >= s["ydstogo"])
    first_and_ten(s, made, s["yardline"])
    nxt = m & ~made
    s["down"][nxt] += 1; s["ydstogo"][nxt] -= g[nxt] if g.shape == m.shape else g
    turnover = nxt & (s["down"] > K.DOWNS)
    if turnover.any(): change_possession(s, turnover, K.FIELD_YARDS - s["yardline"][turnover])
    return turnover


def run_clock(s, m, elapsed):
    """Seconds come off the half (or the overtime period) in the worlds m; the half or game ends at 0 (Rule 4-1-1; 16-1-3)."""
    e = np.asarray(elapsed)
    s["seconds"][m] = np.maximum(0, s["seconds"][m] - (e[m] if e.shape == m.shape else e))


def tied(s):
    return s["score_home"] == s["score_away"]
