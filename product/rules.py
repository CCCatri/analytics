"""rules.py - the rules-module stage, one rules module, to rules-module.md. The rules the record reads (check_possessions.py, check_clock.py, check_downs.py) and the engine (the engine stage) play by, each with its article.
The book is rules/nfl_rulebook_2026.pdf (sha 144cec5bffd2). X1 snap kinds; X2 foul families; X3 next_down; X4 the clock (windows, clock_class, the play clock);
X5 next_possession; X6 season_rules, read from out/season_rules.csv (written by measure_season_rules.py from the record; 2022 is held_out and stays UNKNOWN). No record is read here."""
import csv, hashlib, io, re, sys

_ITEM5 = {}


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def _nan(x):
    return x is None or (isinstance(x, float) and x != x)


# X1 snap kinds (3-8-1a, 3-29); Tries are not snaps of a series (11-3-1)
SNAP_KINDS = ("pass", "run", "qb_kneel", "qb_spike", "punt", "field_goal")

# X2 foul families, by the record's foul name
PRESNAP_OFFENSE = ("False Start", "Delay of Game", "Illegal Formation", "Illegal Shift", "Illegal Motion", "Illegal Substitution")   # by the offense before the snap, the down replayed with yardage (14-4-9, 14-3)
OFF_DURING = ("Offensive Holding", "Illegal Block Above the Waist", "Illegal Blindside Block", "Low Block", "Illegal Crackback", "Clipping", "Chop Block",
              "Tripping", "Illegal Peelback", "Lowering the Head to Initiate Contact")   # by the offense during the play, the down replayed from the spot (14-1-2 Item 1, 3-8-4)
LOSS_OF_DOWN = ("Intentional Grounding", "Illegal Forward Pass", "Illegal Kick/Kicking Loose Ball", "Illegal Bat")   # loss of down (14-1-2 Item 2); the illegal touch pass is 8-1-8
OFF_AFTER = ("Taunting", "Unsportsmanlike Conduct", "Disqualification", "Delay of Game")   # by the offense after the whistle, the down counts (3-8-5); Unnecessary Roughness by rule
DEF_AWARD = ("Unnecessary Roughness", "Defensive Holding", "Roughing the Passer", "Face Mask", "Illegal Use of Hands", "Horse Collar Tackle",
             "Lowering the Head to Initiate Contact", "Lowering the Head to Make Forcible Contact", "Illegal Contact", "Taunting", "Disqualification", "Low Block",
             "Unsportsmanlike Conduct", "Tripping", "Hip Drop Tackle", "Illegal Blindside Block")   # by the defense, a first down (14-1-2 Item 5, 7-3-1(b))
DEF_NEXT, DEF_SAME = ("Defensive Delay of Game",), ("Defensive Too Many Men on Field",)   # by the defense with no award: the next down, the same down (14-1-2 Item 5 Exceptions)
BOOK, BSHA = "rules/nfl_rulebook_2026.pdf", "144cec5bffd2"   # Item 5's Exceptions are read from this book's Item 5 lines
TMM = "Defensive Too Many Men on Field"   # Exception (8) or (9): the record cannot tell the snap from before it (R4 v17 point 2)
TIE = True   # the tie holds while the measured count short of the line is 0; a read that re-measures it sets this False when it breaks
TIE_MEASURED = {"same down": 145, "1st down, the ball at or past the line": 58, "1st down short of the line": 0}   # R4 v17 point 2, 203 plays, 2026-10-26


def norm(x):
    return " ".join(w for w in re.findall(r"[a-z]+", str(x).lower()) if w not in ("the", "a", "an"))


def book():
    """14-1-2 Item 5's Exceptions, read once from BOOK (headings in capitals; an article heading's title ends in a period): its numbered lines (1) to (n).
    The run stops if the book's sha differs or Item 5 is not found once."""
    if _ITEM5: return _ITEM5
    if _sha(BOOK) != BSHA:
        sys.exit(f"STOPPED: {BOOK} is {_sha(BOOK)}, not {BSHA}")
    from pypdf import PdfReader
    T = "\n".join((pg.extract_text() or "") for pg in PdfReader(BOOK).pages).split("\n")
    H = []
    for i in range(len(T)):
        s = T[i].strip()
        if 0 < len(s) <= 4 and s.isalpha() and i + 1 < len(T): s = s + T[i + 1].strip()
        for kind, rx in (("RULE", r"^RULE\s+(\d+)\b"), ("SECTION", r"^SECTION\s+(\d+)\b"), ("ARTICLE", r"^ARTICLE\s+(\d+)\.\s+[A-Z][A-Z0-9 ,'’\-/()&]*?\s*\.")):
            m = re.match(rx, s)
            if m: H.append((i, kind, int(m.group(1))))
    nxt = lambda k, kinds: next((h for h in H if h[0] > k and h[1] in kinds), (len(T), "END", 0))
    r14 = next(h for h in H if h[1] == "RULE" and h[2] == 14); r15 = nxt(r14[0], ("RULE",))
    s1 = next(h for h in H if r14[0] < h[0] < r15[0] and h[1] == "SECTION" and h[2] == 1)
    a2 = [h for h in H if s1[0] < h[0] < nxt(s1[0], ("SECTION", "RULE"))[0] and h[1] == "ARTICLE" and h[2] == 2]
    if len(a2) != 1: sys.exit(f"STOPPED: 14-1-2 found {len(a2)} times in {BOOK}")
    a_end = nxt(a2[0][0], ("ARTICLE", "SECTION", "RULE"))[0]
    i5 = [i for i in range(a2[0][0], a_end) if re.match(r"^\s*Item\s+5\b", T[i])]
    if len(i5) != 1: sys.exit(f"STOPPED: 14-1-2 Item 5 found {len(i5)} times in {BOOK}")
    i5e = next((i for i in range(i5[0] + 1, a_end) if re.match(r"^\s*Item\s+\d+\b", T[i])), a_end)
    ex = next((k for k in range(i5[0], i5e) if "Exception" in T[k]), None)
    if ex is None: sys.exit("STOPPED: 14-1-2 Item 5 names no Exceptions")
    exc = [m.group(2).strip() for m in (re.match(r"^\s*\((\d+)\)\s*(.+)$", T[k]) for k in range(ex, i5e)) if m]
    _ITEM5.update(exc=exc, exc_lines=(ex + 1, i5e))
    return _ITEM5


def is_exc(name):
    """A foul name is an Item 5 Exception when its words match one of the book's numbered lines, or by the measured tie (TMM)."""
    nn = f" {norm(name)} "
    return any(norm(b) and (f" {norm(b)} " in nn or nn in f" {norm(b)} ") for b in book()["exc"]) or (TIE and name == TMM)


def touch_yards(text):
    """The illegal touch pass (8-1-8): the yardage the play text records ('Illegal Touch Pass, N yards'); None when it records none.
    No yardage on a play that counts: loss of down (8-1-8(b)); yardage on a no-play: the same down (8-1-8(a))."""
    m = re.search(r"Illegal Touch Pass,\s*(\d+)\s*yard", text if isinstance(text, str) else "", flags=re.I)
    return int(m.group(1)) if m else None


# X3 the next down: outcome -> (the next down from the fouled or played down, the rule with its article)
NEXT_DOWN = {
    "first_down": (lambda dn: 1, "a first down starts a new series (7-3-1(a))"),
    "cancelled": (lambda dn: dn, "a down cancelled by a foul is repeated (3-8-4)"),
    "next": (lambda dn: dn + 1, "the next down (3-8-5)"),
    "turnover_on_downs": (lambda dn: 1, "turnover on downs: the other team's 1st down (7-3-2a)"),
    "kickers_recovery_free_kick": (lambda dn: 1, "the kickers' next snap is a first down (7-3-1(e))"),
    "kickers_recovery_scrimmage_kick": (lambda dn: 1, "the kickers' next snap is a first down (7-3-1(d))"),
    "presnap_offense": (lambda dn: dn, "a foul by the offense before the snap, the down replayed with yardage (14-4-9, 14-3)"),
    "off_during": (lambda dn: dn, "a foul by the offense during the play, the down replayed from the spot (14-1-2 Item 1, 3-8-4)"),
    "loss_of_down": (lambda dn: dn + 1, "loss of down (14-1-2 Item 2)"),
    "off_after": (lambda dn: dn + 1, "a foul by the offense after the whistle, the down counts (3-8-5)"),
    "off_between": (lambda dn: dn, "a foul by the offense between downs, the down unchanged (14-1-2 Item 7)"),
    "def_award": (lambda dn: 1, "a foul by the defense that awards a first down (14-1-2 Item 5, 7-3-1(b))"),
    "def_exception": (lambda dn: dn, "a foul by the defense with no award (14-1-2 Item 5 Exceptions)"),
    "touch_no_yardage": (lambda dn: dn + 1, "an illegal touch pass with no yardage, loss of down (8-1-8(b))"),
    "touch_yardage_no_play": (lambda dn: dn, "an illegal touch pass with yardage on a no-play, the same down (8-1-8(a), 14-1-2 Item 1)"),
}


def next_down(dn, outcome):
    f, why = NEXT_DOWN[outcome]
    return f(dn), why


# X4 the clock: the windows, the class of a stretch between snaps, the play clock
def beyond(q, reg):
    return bool((not reg) and q >= 6)             # Retired list: NOT TESTABLE, no quarter number assumed (v14 b: a Python bool for any scalar)


def oob_window(q, qa, reg):
    if q in (1, 3) or (q == 5 and not reg):
        return False                              # 16-1-4(h): no window in the first postseason overtime period
    if beyond(q, reg) or _nan(qa):
        return None
    if q == 2:
        return bool(qa <= 120)                    # 4-3-2a (v14 b: a Python bool for any scalar)
    return bool(qa <= 300)                        # 4-3-2a q4; 16-1-3e regular-season overtime (v14 b: a Python bool for any scalar)


def foul_window(q, qa, reg):
    if q in (1, 3):
        return False
    if beyond(q, reg) or _nan(qa):
        return None
    return bool(qa <= 120) if q == 2 else bool(qa <= 300)    # 4-3-2e(1)-(2): second half and overtime inside 5:00 (v14 b: a Python bool for any scalar)


def warns(q, reg):
    return bool(q in (2, 4) or (q >= 5 and reg))  # 3-41, 16-1-3e; postseason period 1 has none (16-1-4(h)) (v14 b: a Python bool for any scalar)


def warning(q, qa, qb, reg):
    if beyond(q, reg):
        return None
    if not warns(q, reg):
        return False
    if _nan(qa) or _nan(qb):
        return None
    return bool(qa > 120 and qb <= 120)          # 3-41, placed from the quarter clock (v14 b: a Python bool for any scalar)


def before_warning(q, qa, reg):
    if beyond(q, reg):
        return None
    if not warns(q, reg):
        return True
    if _nan(qa):
        return None
    return bool(qa > 120)                         # (v14 b: a Python bool for any scalar)


CLOCK_EVENTS = {   # what each event does to the game clock on the stretch it falls in, with its article
    "incomplete 4-4f": "STOP", "out of bounds late 4-3-2a": "STOP", "score/touchback/try 4-4d": "STOP", "change of possession 4-4i": "STOP",
    "foul in window 4-3-2e": "STOP", "offensive pre-snap foul q4/OT 4-3-2e(3)": "STOP", "charged timeout 4-5-1": "STOP",
    "injury after the warning 4-5-4": "STOP", "two-minute warning 3-41": "STOP",
    "out of bounds early 4-3-2a": "PARTIAL", "foul outside windows 4-3-2e": "PARTIAL", "injury, from play text 4-5-3": "PARTIAL",
    "referee timeout, from play text 4-5-5": "PARTIAL", "replay review 15-5-1": "PARTIAL",
    "postseason overtime past quarter 5: NOT TESTABLE (Retired list)": "UNKNOWN", "out of bounds unread": "UNKNOWN", "out of bounds, window unread": "UNKNOWN",
    "foul, window unread": "UNKNOWN", "warning placement unread": "UNKNOWN", "injury, warning placement unread": "UNKNOWN",
}


def clock_class(events, past_q5):
    """RUN / STOP / PARTIAL / UNKNOWN for a stretch, and its reasons joined by '+': events is [(name, happened)] in the read's order; a stretch past the
    first postseason overtime period is UNKNOWN."""
    hit = [n for n, f in events if f]
    stop = [n for n in hit if CLOCK_EVENTS[n] == "STOP"]; part = [n for n in hit if CLOCK_EVENTS[n] == "PARTIAL"]; unk = [n for n in hit if CLOCK_EVENTS[n] == "UNKNOWN"]
    cls = "UNKNOWN" if past_q5 else ("STOP" if stop else ("UNKNOWN" if unk else ("PARTIAL" if part else "RUN")))
    return cls, "+".join(unk if past_q5 else (stop if stop else (unk if unk else part)))


def admin(poss, tmo, tmw, pen, rep):
    """An administrative stoppage resets the play clock (4-6-2): a change of possession, a timeout, the two-minute warning, a foul or a review; None when the
    warning cannot be placed."""
    return None if tmw is None else bool(poss or tmo or tmw or pen or rep)


def play_clock(adm, x, rx):
    """The play clock (4-6-1, 4-6-2): the next snap within 40 seconds of real time after the play ended, within the stamps' resolution rx."""
    if adm is None:
        return "UNCHECKED"
    if adm:
        return "N/A (ADMIN)"
    return "UNCHECKED" if _nan(x) or _nan(rx) else ("WITHIN 40" if x <= 40 + rx else "OVER 40")


# X5 the next possession: ending -> (who receives or snaps next, the rule with its article)
POSSESSION = {
    "try_or_field_goal": ("scored upon", "after a Try or a field goal, the team scored upon receives (11-3-4, 11-4-6, 6-1-1a)"),
    "safety": ("scoring team", "after a safety, the team scored upon free kicks (11-5-1(b), 11-5-2)"),
    "turnover_on_downs": ("other team", "turnover on downs (7-3-2a)"),
    "kickers_recovery": ("kicking team", "the kickers' recovery (6-1-6, 6-1-4c, 9-3-2 Item 1, 7-3-1d, 7-3-1e)"),
    "halftime": ("the second-half choice", "halftime (4-2-2)"),
    "overtime": ("the toss", "overtime (16-1-2, 16-1-3, 16-1-4)"),
}


def next_possession(ending, scorer=None, scored_on=None, team=None, other=None):
    """Who has the ball next after an ending, and the rule: the receiving team after a score, the other team after a turnover on downs, the kickers after
    their recovery; halftime and overtime return the rule only (the choice and the toss are not in the record)."""
    who, why = POSSESSION[ending]
    return {"scored upon": scored_on, "scoring team": scorer, "other team": other, "kicking team": team}.get(who), why


# the season rules season rules, 2019-2025: measured by measure_season_rules.py into out/season_rules.csv; 2022 is the held_out season, its values from rule text only, UNKNOWN until read
R7_FILE = "out/season_rules.csv"


def season_rules(season):
    """{measure: (value, source)} for a season; a value is written where its prediction held, or where there was nothing to count ('no games', 'no kicks');
    a broken prediction reads UNKNOWN until its plays are read."""
    if season == 2022:
        return {"all": ("UNKNOWN", "rule text, not read; the held_out season's record is never read")}
    L = open(R7_FILE).read().split("\n")
    out = {}
    SRC = {"True": "measured (R7)", "not judged": "measured (R7): nothing to count, no prediction judged"}   # R7 v2 a
    for r in csv.DictReader(io.StringIO("\n".join(L[1:]))):
        if int(r["season"]) == season:
            h = r["prediction_held"]
            out[r["measure"]] = (r["value"], SRC[h]) if h in SRC else ("UNKNOWN", "measured, prediction broken: read on its plays first")
    return out


# the season rules rules (engine-legality.md E1a v4): each season's rule quoted from that season's book in rules/ (pinned in rules/RULE_PINS.json), the quote found inside its
# article by the heading finder; R7's measured value sits beside it (season_rules above). A measured value supports a rule; it never stands in for one (v3 a).
RULE_PINS_FILE = "rules/RULE_PINS.json"
RULE_BOOK_OF = {2019: ("2020", "the 2020 book; 2019 book not read"), 2020: ("2020", ""), 2021: ("2021", ""), 2023: ("2023", ""), 2024: ("2024", ""),
                2025: ("2025", "the 2025 rulebook page (its own 2025 Rule Changes list and rules); the 2026 book is not cited (2026 changed the onside article)")}
RULE_MEASURE = {"touchback": "M1", "ot_reg_len": "M2", "ot_reg_rule": "M3", "ot_post_rule": "M4", "onside": "M5"}
TD_ENDS = "first-possession touchdown ends"
BOTH_POSSESS = "both teams possess first"
_RECV_TD = "unless the team that receives the opening kickoff scores a touchdown on its initial possession, in which case it is the winner"
_BOTH_POST = "Both teams must have the opportunity to possess the ball at least once during the extra period"
_TO_REG = "Each team shall be entitled to two timeouts"
_TO_POST = "Each team is entitled to three timeouts during a half."
_NO_ONSIDE = None   # no sentence: the book's rules name no onside kick (counted, must be 0)
# (book, rule) -> (value, quote, predicted place: the rule number in the book, or the page's '2025 Rule Changes' list)
RULE_QUOTES = {
    ("2020", "touchback"): (25, "The dead-ball spot for free kicks that result in a touchback is the 25-yard line.", "Rule 6"),
    ("2020", "ot_reg_rule"): (TD_ENDS, _RECV_TD, "Rule 16"),
    ("2020", "ot_post_rule"): (TD_ENDS, _RECV_TD, "Rule 16"),
    ("2020", "ot_reg_len"): (600, "There shall be a maximum of one 10-minute period", "Rule 16"),
    ("2020", "ot_post_len"): (900, "If the score is tied at the end of a 15-minute overtime period", "Rule 16"),
    ("2020", "ot_reg_timeouts"): (2, _TO_REG, "Rule 16"),
    ("2020", "ot_post_timeouts"): (3, _TO_POST, "Rule 16"),
    ("2020", "onside"): ("any free kick", _NO_ONSIDE, ""),
    ("2021", "touchback"): (25, "The dead-ball spot for free kicks that result in a touchback is the 25-yard line.", "Rule 6"),
    ("2021", "ot_reg_rule"): (TD_ENDS, _RECV_TD, "Rule 16"),
    ("2021", "ot_post_rule"): (TD_ENDS, _RECV_TD, "Rule 16"),
    ("2021", "ot_reg_len"): (600, "There shall be a maximum of one 10-minute period", "Rule 16"),
    ("2021", "ot_post_len"): (900, "If the score is tied at the end of a 15-minute overtime period", "Rule 16"),
    ("2021", "ot_reg_timeouts"): (2, _TO_REG, "Rule 16"),
    ("2021", "ot_post_timeouts"): (3, _TO_POST, "Rule 16"),
    ("2021", "onside"): ("any free kick", _NO_ONSIDE, ""),
    ("2023", "touchback"): (25, "It is a touchback and the dead ball spot is the 25-yard line if a free kick", "Rule 6"),
    ("2023", "ot_reg_rule"): (TD_ENDS, _RECV_TD, "Rule 16"),
    ("2023", "ot_post_rule"): (BOTH_POSSESS, _BOTH_POST, "Rule 16"),
    ("2023", "ot_reg_len"): (600, "an extra period of 10 minutes shall commence", "Rule 16"),
    ("2023", "ot_post_len"): (900, "an extra period of 15 minutes shall commence", "Rule 16"),
    ("2023", "ot_reg_timeouts"): (2, _TO_REG, "Rule 16"),
    ("2023", "ot_post_timeouts"): (3, _TO_POST, "Rule 16"),
    ("2023", "onside"): ("any free kick", _NO_ONSIDE, ""),
    ("2024", "touchback"): (30, "The dead ball spot is the 30-yard line if, without first touching the ground or a player in the landing zone, a kickoff or safety kick", "Rule 6"),
    ("2024", "touchback_landing_zone"): (20, "It is a touchback and the dead ball spot is the 20-yard line if a kickoff or a safety kick", "Rule 6"),
    ("2024", "ot_reg_rule"): (TD_ENDS, _RECV_TD, "Rule 16"),
    ("2024", "ot_post_rule"): (BOTH_POSSESS, _BOTH_POST, "Rule 16"),
    ("2024", "ot_reg_len"): (600, "an extra period of 10 minutes shall commence", "Rule 16"),
    ("2024", "ot_post_len"): (900, "an extra period of 15 minutes shall commence", "Rule 16"),
    ("2024", "ot_reg_timeouts"): (2, _TO_REG, "Rule 16"),
    ("2024", "ot_post_timeouts"): (3, _TO_POST, "Rule 16"),
    ("2024", "onside"): ("4th period, kicking team trailing, declared", "At any time during the fourth period, the kicking team, if trailing its opponent, may declare an onside kick", "Rule 6"),
    ("2025", "touchback"): (35, "The dead ball spot for free kicks that result in a touchback is the 20-yard line or 35-yard line", "Rule 6"),
    ("2025", "touchback_landing_zone"): (20, "It is a touchback and the dead ball spot is the 20-yard line if a kickoff or a safety kick", "Rule 6"),
    ("2025", "ot_reg_rule"): (BOTH_POSSESS, "Both teams must have the opportunity to possess the ball once during the extra period, unless the team kicking off to start the overtime period scores a safety", "Rule 16"),
    ("2025", "ot_post_rule"): (BOTH_POSSESS, _BOTH_POST, "Rule 16"),
    ("2025", "ot_reg_len"): (600, "subject to a 10-minute overtime period", "2025 Rule Changes"),
    ("2025", "ot_post_len"): (900, "If the score is tied at the end of a 15-minute overtime period", "Rule 16"),
    ("2025", "ot_reg_timeouts"): (2, _TO_REG, "Rule 16"),
    ("2025", "ot_post_timeouts"): (3, _TO_POST, "Rule 16"),
    ("2025", "onside"): ("any period, kicking team trailing, declared", "permits the kicking team to declare an onside kick at any time during the game if trailing its opponent", "2025 Rule Changes"),
}
_BOOK_CACHE = {}
_PDF_RULE = re.compile(r"^RULE\s+(\d+)\b")
_PDF_SECTION = re.compile(r"^SECTION\s+(\d+)\b")
_PDF_ARTICLE = re.compile(r"^ARTICLE\s+(\d+)\s*\.\s*(.*)$")
_PDF_TITLE = re.compile(r"^([A-Z][A-Z0-9 ,’'\-/()&]*?)\s*\.(\s|$)")   # headings in capitals ending in a period (v4 b)
_PAGE_RULE = re.compile(r"^Rule\s+(\d+)\.\s")
_PAGE_SECTION = re.compile(r"^Section\s+(\d+)\b")
_PAGE_ARTICLE = re.compile(r"^Article\s+(\d+)\.\s*(.*)$")
_CASEBOOK = re.compile(r"^A\.R\.\s*\d+\.\d+")


def _squeeze(s):
    return re.sub(r"\s+", "", s)


def rule_book(book):
    """One pinned book's articles: {'file', 'sha', 'pinned', 'spans': [(rule, section, article, title, text)], 'cut', 'onside', 'untitled'}.
    A PDF's articles are found by its headings in capitals ending in a period (RULE n, SECTION n, ARTICLE n. TITLE.); the page's by its own 'Rule n.',
    'Section n', 'Article n. Title' lines and its '2025 Rule Changes' list. A book whose sha differs from its pin reads no articles."""
    if book in _BOOK_CACHE: return _BOOK_CACHE[book]
    import json, os
    pins = json.load(open(RULE_PINS_FILE))
    pin = pins.get(book, {}); path = pin.get("file", ""); out = {"file": path, "pinned": pin.get("sha"), "spans": [], "cut": None, "onside": None, "untitled": 0}
    if not path or not os.path.exists(path):
        out["sha"] = "MISSING"; _BOOK_CACHE[book] = out; return out
    out["sha"] = hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]
    if out["sha"] != out["pinned"]:
        _BOOK_CACHE[book] = out; return out
    if path.endswith(".pdf"):
        from pypdf import PdfReader
        L = [l.strip() for pg in PdfReader(path).pages for l in (pg.extract_text() or "").split("\n")]
        cut = next((i for i, l in enumerate(L) if _CASEBOOK.match(l)), len(L))
        out["cut"] = (cut + 1, L[cut] if cut < len(L) else "end of the book")
        L = L[:cut]
        out["onside"] = sum(len(re.findall(r"\bonside\b", l, re.I)) for l in L)
        R, S_, rows = None, None, []
        cur = None
        for l in L:
            mr, ms, ma = _PDF_RULE.match(l), _PDF_SECTION.match(l), _PDF_ARTICLE.match(l)
            if mr or ms or ma:
                if cur: rows.append(cur)
                cur = None
                if mr: R, S_ = int(mr.group(1)), None
                elif ms: S_ = int(ms.group(1))
                else:
                    mt = _PDF_TITLE.match(ma.group(2))
                    if not mt: out["untitled"] += 1
                    cur = [R, S_, int(ma.group(1)), mt.group(1).strip() if mt else "", [l]]
                continue
            if cur: cur[4].append(l)
        if cur: rows.append(cur)
    else:
        import html as _html
        raw = open(path, encoding="utf-8", errors="replace").read()
        txt = _html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?is)<(script|style).*?</\1>", "", raw)))
        L = [l.strip() for l in txt.split("\n") if l.strip()]
        R, S_, rows, cur = None, None, [], None
        for l in L:
            mr, ms, ma = _PAGE_RULE.match(l), _PAGE_SECTION.match(l), _PAGE_ARTICLE.match(l)
            if l == "2025 Rule Changes" or mr or ms or ma:
                if cur: rows.append(cur)
                cur = None
                if l == "2025 Rule Changes": cur = [None, None, None, "2025 Rule Changes", [l]]
                elif mr: R, S_ = int(mr.group(1)), None
                elif ms: S_ = int(ms.group(1))
                else: cur = [R, S_, int(ma.group(1)), ma.group(2).strip(), [l]]
                continue
            if cur: cur[4].append(l)
        if cur: rows.append(cur)
    out["spans"] = [(r_, s_, a_, t_, _squeeze(" ".join(x))) for r_, s_, a_, t_, x in rows]
    _BOOK_CACHE[book] = out
    return out


def _place(r_, s_, a_, t_):
    return t_ if a_ is None else f"Rule {r_}, Section {s_}, Article {a_} ({t_})"


def find_quote(book, quote):
    """Every article of the book whose text holds the quote (spaces ignored: the books' extracted text breaks words with stray spaces)."""
    B = rule_book(book); q = _squeeze(quote)
    return [_place(r_, s_, a_, t_) for r_, s_, a_, t_, x in B["spans"] if q in x]


def season_x6(season, quotes=None):
    """X6 for a season: {rule: {'value', 'quote', 'book', 'sha', 'note', 'found_in', 'predicted', 'held', 'measured'}}; a rule whose quote is not found in an
    article (or whose book reads no onside article where none is predicted, or whose book's sha differs from its pin) has value UNKNOWN."""
    Q = RULE_QUOTES if quotes is None else quotes
    book, note = RULE_BOOK_OF[season]
    B = rule_book(book); meas = season_rules(season)
    out = {}
    for (bk, rule), (val, quote, pred) in Q.items():
        if bk != book: continue
        cell = {"book": B["file"], "sha": B["sha"], "note": note, "quote": quote, "predicted": pred, "measured": meas.get(RULE_MEASURE.get(rule, ""), None)}
        if B["sha"] != B["pinned"]:
            cell.update(value="UNKNOWN", found_in=[], held=False, why=f"book sha {B['sha']} is not its pin {B['pinned']}")
        elif quote is None:
            n = B["onside"]
            cell.update(value=val if n == 0 else "UNKNOWN", found_in=[], held=n == 0,
                        why=f"no sentence: the word 'onside' in the book's rules {n} times (must be 0)" if n is not None else "not a PDF: no count")
        else:
            hits = find_quote(book, quote)
            cell.update(value=val if hits else "UNKNOWN", found_in=hits, held=any(pred and h.startswith(pred + ",") or h == pred for h in hits),
                        why="found" if hits else "not found in the article")
        out[rule] = cell
    return out
