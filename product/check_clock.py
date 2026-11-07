"""check_clock.py - rules-level clause 1, the clock, to clock-check.md v16 (dfff5f9d7de8). A record read, not product.
Reads through record.raw_frame + record.typed (pinned file, betting refused, every column typed; empties counted, never filled).
Injected faults and negatives run first, row by row; any FAIL stops the run before a count is read or a file is written.
Writes out/clock_counts.csv, out/clock_faster.csv, out/clock_over40.csv and out/clock_reasons.csv, each stamped on line 1 with this file's sha and the targets sha.
out/clock_reasons.csv (N7): every count of out/clock_counts.csv split by its reason; the run stops if the split does not sum back to the counts.
Choices the targets do not fix, declared and printed:
 - no_play rows are rows between snaps, never snaps; their count is printed per season.
 - an empty flag on a row is read as not set (record.events convention); empty cells are counted per column and printed.
 - every event in an interval is placed at snap i's quarter clock (the record has no clock for the moment of a foul or an injury).
 - the offensive pre-snap fouls of 4-3-2e(3) are read from penalty_type by name (PRESNAP_OFFENSE), penalty_team = the next snap's offense; names met are counted and printed.
 - injury and Referee's timeouts are read from play text only (no column holds them); intervals classed that way are counted under their tags.
 - a window the record cannot place (an empty quarter clock) classes UNKNOWN (Interval rule class), reason printed.
 - postseason overtime: quarter 5 is its first period (all 7 postseason overtimes, 2019-2025); any interval past quarter 5 reads UNKNOWN, no quarter number assumed (Retired list).
 - the record logs no two-minute warning row (Retired list): the warning is placed by the quarter clock only; v5's text search (any mention) is kept only for the frozen 2023 reproduction (tmw_row_v5).
 - every 'line N' printed is looked up in the targets file at run time by the line's opening words, so it cannot go stale.
 - game level margin = coarser W stamp + G's 1 s (Instruments, v13); D3 compares real-time stamps only (W, E), so its margin carries no G second.
 - v12's game level word (margin without G's second) is computed beside v13's in the same run and written to out/clock_counts.csv as GAME_LEVEL_PRIOR.
 - the rules-module stage: the snap kinds, the pre-snap foul list, the clock windows, the clock class, the administrative stoppage and the play clock are read from rules.py (rules-module.md snap kinds, foul families, the clock rule)."""
import hashlib, os, re, sys, datetime
from collections import Counter
import numpy as np, pandas as pd
import record, policy
from rules import SNAP_KINDS, PRESNAP_OFFENSE, beyond, oob_window, foul_window, warning, before_warning, clock_class, play_clock, admin as admin_rule

SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]
TARGETS, TSHA = "acceptance-criteria/clock-check.md", "dfff5f9d7de8"
TLINES = open(TARGETS).read().split("\n")


def L(opening):
    """The targets line number whose text opens with these words; '?' if not exactly one."""
    hit = [i + 1 for i, l in enumerate(TLINES) if l.startswith(opening)]
    return hit[0] if len(hit) == 1 else "?"


G_RES = 1.0   # Instruments: the game clock is recorded in whole seconds (measured, six seasons)
EXPECTED_FASTER = {2019: 267, 2020: 238, 2021: 258, 2023: 356, 2024: 349, 2025: 321}   # targets: EXPECTED before the v13 run
OUT_COUNTS = "out/clock_counts.csv"
OUT_FASTER = "out/clock_faster.csv"
OUT_OVER40 = "out/clock_over40.csv"
OUT_REASONS = "out/clock_reasons.csv"
CLASS_EMPTY = {"RUN": "no stoppage on the stretch: the clock ran (4-3)"}   # a RUN stretch carries no stop or partial reason of its own
GAME_LEVEL_REASON = {"WITHIN REAL TIME": "the game clock fell no faster than real time",
             "WITHIN RESOLUTION": "the game clock fell faster by no more than the stamps can tell apart (the real-time stamp's resolution plus the game clock's whole second)",
             "FASTER not licensed": "the game clock fell faster than real time beyond what the stamps can tell apart; officials may correct the clock without the record logging it (4-1-4), so a correction and a record error cannot be told apart",
             "FASTER licensed (runoff)": "a 10-second runoff removed game time with no play (4-7-1, 4-7-4)",
             "UNCHECKED": "a real-time clock stamp or the game clock is missing on one of the two snaps"}
GAME_LEVEL_PRIOR_REASON = {"WITHIN REAL TIME": "v12 margin (the real-time stamp's resolution only), kept for comparison: within real time",
                "FASTER not licensed": "v12 margin (the real-time stamp's resolution only), kept for comparison: faster than real time",
                "FASTER licensed (runoff)": "v12 margin (the real-time stamp's resolution only), kept for comparison: a runoff (4-7-1, 4-7-4)",
                "UNCHECKED": "v12 margin (the real-time stamp's resolution only), kept for comparison: a stamp missing"}
D3_REASON = {"WITHIN 40": "the next snap came within 40 seconds of real time after the play ended (4-6-1)",
             "OVER 40": "the next snap came more than 40 seconds of real time after the play ended; the play clock stops for interruptions the record does not log (4-6-3)",
             "N/A (ADMIN)": "an administrative stoppage (a change of possession, a timeout, the two-minute warning, a foul or a review) resets the play clock (4-6-2)",
             "UNCHECKED": "an end-of-play stamp is missing or the two-minute warning cannot be placed (the record carries end stamps from 2023)"}
TYPES = {"game_id": ("str", False), "season_type": ("str", False), "order_sequence": ("int", False), "posteam": ("str", True), "qtr": ("int", False),
         "quarter_seconds_remaining": ("int", True), "game_seconds_remaining": ("int", True), "play_type": ("str", True), "two_point_attempt": ("int", True),
         "incomplete_pass": ("int", True), "out_of_bounds": ("int", True), "touchdown": ("int", True), "field_goal_result": ("str", True), "safety": ("int", True),
         "touchback": ("int", True), "interception": ("int", True), "fumble_lost": ("int", True), "penalty": ("int", True), "timeout": ("int", True),
         "replay_or_challenge": ("int", True), "time_of_day": ("str", True), "end_clock_time": ("str", True), "desc": ("str", True),
         "penalty_team": ("str", True), "penalty_type": ("str", True)}
RUNOFF = re.compile(r"run[- ]?off", re.I)
TMW = re.compile(r"two.minute warning", re.I)                      # v5 text match (any mention), kept for the frozen reproduction
INJ = re.compile(r"injur", re.I)
REFTO = re.compile(r"(referee|official)'?s? time", re.I)
RX = re.compile(r"(?:(\d{4}-\d{2}-\d{2})[T ])?(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?")
FROZEN_2023 = {"WITHIN 40": 23659, "OVER 40": 4060, "UNCHECKED": 564, "N/A (ADMIN)": 10019}   # targets: Seen before the injected faults passed


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def nan(x):
    return x is None or (not isinstance(x, str) and pd.isna(x))


def one(x):
    return (not nan(x)) and x == 1


def parse(v):
    """(seconds of day, resolution, day number); (nan, nan, nan) when empty; None when present but unparsed."""
    if nan(v) or not str(v).strip():
        return (np.nan, np.nan, np.nan)
    m = RX.search(str(v))
    if not m:
        return None
    dt, h, mi, s, fr = m.groups()
    sec = int(h) * 3600 + int(mi) * 60 + int(s) + (float("0." + fr) if fr else 0.0)
    return (sec, 10.0 ** -len(fr) if fr else 1.0, (datetime.date.fromisoformat(dt) - datetime.date(1970, 1, 1)).days if dt else np.nan)


def diff(s2, d2, s1, d1):
    if nan(s2) or nan(s1):
        return np.nan, False
    if not nan(d2) and not nan(d1):
        return (d2 - d1) * 86400 + (s2 - s1), False
    x = s2 - s1
    return (x + 86400, True) if x < -43200 else (x, False)


def load(season):
    record.held_out(season, "check_clock")
    name = policy.PBP_FILE.format(season=season)
    d = record.typed(record.raw_frame(name, list(TYPES), f"check_clock {season}"), TYPES, f"check_clock {season}")
    empt = {c: int(d[c].isna().sum()) for c in TYPES if d[c].isna().any()}
    for c, (k, _) in TYPES.items():
        if k == "int":
            d[c] = d[c].to_numpy(dtype=float, na_value=np.nan)
    d = d.sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
    unparsed = {}
    for col, k in (("time_of_day", "W"), ("end_clock_time", "E")):
        p = [parse(v) for v in d[col]]
        bad = [v for v, t in zip(d[col], p) if t is None]
        unparsed[col] = (len(bad), bad[:3])
        p = [(np.nan, np.nan, np.nan) if t is None else t for t in p]
        d[k + "_s"] = [t[0] for t in p]; d[k + "_r"] = [t[1] for t in p]; d[k + "_d"] = [t[2] for t in p]
    return d, empt, unparsed


def intervals(g, gres=G_RES):
    g = g.reset_index(drop=True); c = {k: g[k].tolist() for k in g.columns}; out = []
    if not len(g):
        return out
    reg = c["season_type"][0] == "REG"
    snaps = [k for k in range(len(g)) if c["play_type"][k] in SNAP_KINDS and not one(c["two_point_attempt"][k])]
    for a, b in zip(snaps, snaps[1:]):
        if c["qtr"][a] != c["qtr"][b]:
            continue
        bt = list(range(a + 1, b)); ab = [a] + bt
        q = int(c["qtr"][a]); qa = c["quarter_seconds_remaining"][a]; qb = c["quarter_seconds_remaining"][b]; ob = c["out_of_bounds"][a]
        txt = [str(c["desc"][k] or "") for k in ab]
        inc = one(c["incomplete_pass"][a])
        poss = c["posteam"][b] != c["posteam"][a] or one(c["interception"][a]) or one(c["fumble_lost"][a])
        score = one(c["touchdown"][a]) or c["field_goal_result"][a] == "made" or one(c["safety"][a]) or one(c["touchback"][a]) or any(c["play_type"][k] == "extra_point" or one(c["two_point_attempt"][k]) for k in bt)
        pen = any(one(c["penalty"][k]) for k in ab)
        pen_a = one(c["penalty"][a])
        presnap = [c["penalty_type"][k] for k in bt if one(c["penalty"][k]) and c["penalty_team"][k] == c["posteam"][b] and c["penalty_type"][k] in PRESNAP_OFFENSE]
        tmo = any(one(c["timeout"][k]) for k in bt)
        tmw = warning(q, qa, qb, reg); tmw_row_v5 = any(TMW.search(t) for t in txt[1:])
        inj = any(INJ.search(t) for t in txt); ref = any(REFTO.search(t) for t in txt)
        rep = any(one(c["replay_or_challenge"][k]) for k in ab)
        runoff = any(RUNOFF.search(t) for t in txt)
        ow = oob_window(q, qa, reg); fw = foul_window(q, qa, reg); bw = before_warning(q, qa, reg)
        events = [("incomplete 4-4f", inc), ("out of bounds late 4-3-2a", one(ob) and ow is True), ("score/touchback/try 4-4d", score),
                               ("change of possession 4-4i", poss), ("foul in window 4-3-2e", pen and fw is True),
                               ("offensive pre-snap foul q4/OT 4-3-2e(3)", bool(presnap) and q >= 4), ("charged timeout 4-5-1", tmo),
                               ("injury after the warning 4-5-4", inj and bw is False), ("two-minute warning 3-41", tmw is True),
                  ("out of bounds early 4-3-2a", one(ob) and ow is False), ("foul outside windows 4-3-2e", pen and fw is False),
                               ("injury, from play text 4-5-3", inj and bw is True), ("referee timeout, from play text 4-5-5", ref),
                               ("replay review 15-5-1", rep),
                  ("postseason overtime past quarter 5: NOT TESTABLE (Retired list)", beyond(q, reg)), ("out of bounds unread", nan(ob)), ("out of bounds, window unread", one(ob) and ow is None),
                              ("foul, window unread", pen and fw is None), ("warning placement unread", tmw is None),
                              ("injury, warning placement unread", inj and bw is None)]
        cls, why = clock_class(events, beyond(q, reg))   # the rules module the clock rule
        admin = admin_rule(poss, tmo, tmw, pen, rep)      # ADMIN (4-6-2, the rules module the clock rule)
        admin_v5 = bool(poss or tmo or tmw_row_v5 or pen or rep)                      # v5: warning from row text (any mention)
        dW, w1 = diff(c["W_s"][b], c["W_d"][b], c["W_s"][a], c["W_d"][a])
        rW = np.nan if nan(c["W_r"][a]) or nan(c["W_r"][b]) else max(c["W_r"][a], c["W_r"][b])
        dG = c["game_seconds_remaining"][a] - c["game_seconds_remaining"][b]
        res = np.nan if nan(rW) else rW + gres                                          # Instruments
        fast = "FASTER licensed (runoff)" if runoff else "FASTER not licensed"
        game_level = "UNCHECKED" if nan(dW) or nan(dG) or nan(res) else ("WITHIN REAL TIME" if dG <= dW else ("WITHIN RESOLUTION" if dG - dW <= res else fast))   # Laws: the game level
        game_level_prior = "UNCHECKED" if nan(dW) or nan(dG) or nan(rW) else ("WITHIN REAL TIME" if dG <= dW + rW else fast)
        x, w2 = diff(c["W_s"][b], c["W_d"][b], c["E_s"][a], c["E_d"][a])
        rx = np.nan if nan(c["W_r"][b]) or nan(c["E_r"][a]) else max(c["W_r"][b], c["E_r"][a])

        out.append(dict(game_id=c["game_id"][a], sa=int(c["order_sequence"][a]), sb=int(c["order_sequence"][b]), pt=c["play_type"][a], q=q, qa=qa, qb=qb, ob=ob,
                        nb=len(bt), same=c["posteam"][a] == c["posteam"][b], reg=reg, inc=inc, pen=pen, pen_a=pen_a, tmo=tmo, bw=bw,
                        accepted=pen_a and not re.search(r"declined|offsetting", txt[0], re.I), presnap="+".join(presnap), score=score, poss=poss,
                        inj=inj, ref=ref, rep=rep, cls=cls, why=why, admin=admin, tmw=tmw, tmw_row_v5=tmw_row_v5, runoff=runoff,
                        dG=dG, dW=dW, rW=rW, res=res, x=x, rx=rx, game_level=game_level, game_level_prior=game_level_prior, d3=play_clock(admin, x, rx), d3_v5=play_clock(admin_v5, x, rx), wrap=w1 or w2))
    return out


def main():
    t = sha(TARGETS)
    if t != TSHA:
        sys.exit(f"STOPPED: {TARGETS} is {t}, not the frozen {TSHA}")
    seasons = [s for s in policy.SEASONS if s != policy.HOLD]
    tag = f"check_clock.py {SELF} | clock-check.md {TSHA} | record read (rules-level clause 1), not product"
    print(f"{tag} | seasons {seasons} (hold-out {policy.HOLD} held_out)")
    refs = {k: L(k) for k in ("PL1 ", "PL1b ", "PL2 ", "PL3 ", "PL4 ", "PL5 ", "PL6 ", "PL7 ", "PL8 ", "PL9 ", "PL10 ", "NEG9 ", "EXPECTED before", "2023 the team level")}
    print(f"targets lines found by their opening words: {refs}")
    if "?" in refs.values():
        sys.exit("STOPPED: a targets line is missing or not unique; code and text cannot be matched")
    DATA, IV = {}, {}
    print("\n=== 1. READ: coverage, empties, unparsed stamps ===")
    for s in seasons:
        d, empt, unp = load(s); DATA[s] = d
        sn = d[d["play_type"].isin(SNAP_KINDS) & ~(d["two_point_attempt"] == 1)]
        print(f"{s}: rows {len(d)} | snaps {len(sn)} | no_play rows (between snaps, never snaps) {int((d['play_type'] == 'no_play').sum())} | snaps with no posteam {int(sn['posteam'].isna().sum())} | snaps with no quarter clock {int(sn['quarter_seconds_remaining'].isna().sum())}")
        print(f"   empty cells (counted, never filled) {empt}")
        for col, k in (("time_of_day", "W"), ("end_clock_time", "E")):
            print(f"   {k} {col}: present on snaps {sn[col].notna().mean():.4f} | parsed on snaps {sn[k + '_s'].notna().mean():.4f} | unparsed (all rows) {unp[col][0]} {unp[col][1]}")
        iv = []
        for _, gd in d.groupby("game_id", sort=False):
            iv += intervals(gd)
        IV[s] = pd.DataFrame(iv)
        ps = Counter(p for v in IV[s]["presnap"] if v for p in v.split("+"))
        print(f"   intervals {len(IV[s])} | offensive pre-snap fouls read by name, any quarter {dict(ps)}")

    print("\n=== 2. INJECTED FAULTS and NEGATIVES, row by row (negatives print changes only; any FAIL stops the run) ===")
    res = []

    def injected_fault(name, cond):
        res.append((name, bool(cond))); print(f"  {name} -> {'PASS' if cond else 'FAIL'}")

    def rows(g, s0, s1):
        for _, r in g[(g["order_sequence"] >= s0) & (g["order_sequence"] <= s1)].iterrows():
            print(f"      seq {int(r['order_sequence'])} q{int(r['qtr'])} {r['quarter_seconds_remaining']}s G {r['game_seconds_remaining']} W {r['time_of_day']} E {r['end_clock_time']} "
                  f"{r['play_type']} pos {r['posteam']} ob {r['out_of_bounds']} pen {r['penalty']} {r['penalty_type'] or ''} | {str(r['desc'])[:110]}")

    def find(iv, gid, sa, sb):
        x = iv[(iv["game_id"] == gid) & (iv["sa"] == sa) & (iv["sb"] == sb)]
        return x.iloc[0] if len(x) == 1 else None

    def game(s, gid):
        return DATA[s][DATA[s]["game_id"] == gid]

    def again(F, gres=G_RES):
        return pd.DataFrame(intervals(F, gres))
    T, F_ = (True,), (False,)
    G19 = game(2019, "2019_01_IND_LAC"); I19 = again(G19)
    print(f"  PL1 2019_01_IND_LAC 3209 -> 3230 (line {L('PL1 ')}):"); rows(G19, 3209, 3230); r = find(I19, "2019_01_IND_LAC", 3209, 3230)
    injected_fault(f"PL1 RUN, no ADMIN, dG = dW = 26 (got {None if r is None else (r['cls'], r['admin'], r['dG'], r['dW'], r['rW'])})",
          r is not None and r["cls"] == "RUN" and r["admin"] in F_ and r["dG"] == 26 and abs(r["dW"] - 26) <= r["rW"])
    pl = I19[(I19["q"] == 4) & (I19["tmw"] == True)]
    r1b = pl.iloc[0] if len(pl) == 1 else None
    print(f"  PL1b intervals the quarter clock places the warning in, 2019_01_IND_LAC q4: {len(pl)}")
    if r1b is not None:
        rows(G19, r1b["sa"], r1b["sb"])
    injected_fault(f"PL1b STOP, ADMIN, ending at seq 3209 (got {None if r1b is None else (r1b['sa'], r1b['sb'], r1b['cls'], r1b['admin'], r1b['qa'], r1b['qb'])})",
          r1b is not None and r1b["sb"] == 3209 and r1b["cls"] == "STOP" and r1b["admin"] in T)
    print(f"  PL2 2019_01_IND_LAC 3230 -> 3251 (line {L('PL2 ')}):"); rows(G19, 3230, 3251); row_pl2 = find(I19, "2019_01_IND_LAC", 3230, 3251)
    injected_fault(f"PL2 RUN, no ADMIN, dG 24 (got {None if row_pl2 is None else (row_pl2['cls'], row_pl2['admin'], row_pl2['dG'])})", row_pl2 is not None and row_pl2["cls"] == "RUN" and row_pl2["admin"] in F_ and row_pl2["dG"] == 24)
    print(f"  PL3 2019_01_IND_LAC 3297 -> 3340 (line {L('PL3 ')}):"); rows(G19, 3297, 3340); r = find(I19, "2019_01_IND_LAC", 3297, 3340)
    injected_fault(f"PL3 STOP, ADMIN (got {None if r is None else (r['cls'], r['admin'], r['why'])})", r is not None and r["cls"] == "STOP" and r["admin"] in T)
    I = IV[2019]
    c4 = I[(I["pt"] == "run") & (I["ob"] == 1) & (I["q"] == 2) & (I["qa"] > 120) & (I["nb"] == 0) & I["same"] & ~I["pen"] & ~I["inj"] & ~I["ref"] & ~I["rep"] & ~I["score"] & ~I["poss"]]
    row_pl4 = c4.iloc[0] if len(c4) else None
    if row_pl4 is not None:
        print(f"  PL4 found and pinned: 2019 {row_pl4['game_id']} seq {row_pl4['sa']} -> {row_pl4['sb']} (line {L('PL4 ')}):"); rows(game(2019, row_pl4["game_id"]), row_pl4["sa"], row_pl4["sb"])
    injected_fault(f"PL4 PARTIAL (got {None if row_pl4 is None else (row_pl4['cls'], row_pl4['why'])})", row_pl4 is not None and row_pl4["cls"] == "PARTIAL")
    I = IV[2023]
    c5 = I[(I["pt"] == "pass") & I["inc"] & (I["nb"] == 0) & I["same"] & ~I["pen"] & ~I["rep"] & I["x"].notna() & (I["admin"] == False)]
    r5 = c5.iloc[0] if len(c5) else None
    if r5 is not None:
        print(f"  PL5 found and pinned: 2023 {r5['game_id']} seq {r5['sa']} -> {r5['sb']} (line {L('PL5 ')}):"); rows(game(2023, r5["game_id"]), r5["sa"], r5["sb"])
    injected_fault(f"PL5 STOP, no ADMIN; W(i+1) - E(i) = {None if r5 is None else round(r5['x'], 3)} (got {None if r5 is None else (r5['cls'], r5['admin'], r5['d3'])})",
          r5 is not None and r5["cls"] == "STOP" and r5["admin"] in F_)
    ro = pd.concat([IV[s].assign(season=s) for s in seasons]); ro = ro[ro["runoff"]]
    print(f"  PL6 intervals whose play text names a runoff: {len(ro)} (the frozen count was 16) | game level {dict(Counter(ro['game_level']))} (line {L('PL6 ')}):")
    for _, r in ro.iterrows():
        print(f"    {r['season']} {r['game_id']} seq {r['sa']} -> {r['sb']} q{r['q']} {r['cls']} dG {r['dG']} dW {round(r['dW'], 3) if not nan(r['dW']) else r['dW']} -> {r['game_level']}")
        rows(game(int(r["season"]), r["game_id"]), r["sa"], r["sb"])
    injected_fault(f"PL6 16 runoff intervals, all WITHIN REAL TIME (got {len(ro)}, FASTER {int(ro['game_level'].str.startswith('FASTER').sum())}, UNCHECKED {int((ro['game_level'] == 'UNCHECKED').sum())})",
          len(ro) == 16 and bool((ro["game_level"] == "WITHIN REAL TIME").all()))
    I = IV[2023]
    c7 = I[(I["pt"] == "run") & (I["q"] == 1) & (I["ob"] == 0) & I["accepted"] & (I["nb"] == 0) & I["same"] & ~I["inc"] & ~I["score"] & ~I["poss"] & ~I["inj"] & ~I["ref"] & ~I["rep"]]
    row_pl7 = c7.iloc[0] if len(c7) else None
    if row_pl7 is not None:
        print(f"  PL7 found and pinned: 2023 {row_pl7['game_id']} seq {row_pl7['sa']} -> {row_pl7['sb']} (line {L('PL7 ')}):"); rows(game(2023, row_pl7["game_id"]), row_pl7["sa"], row_pl7["sb"])
    injected_fault(f"PL7 PARTIAL (4-3-2e) (got {None if row_pl7 is None else (row_pl7['cls'], row_pl7['why'])})", row_pl7 is not None and row_pl7["cls"] == "PARTIAL")
    # negatives: changes only
    F = G19.copy(); F.loc[F["order_sequence"] == 3251, "W_s"] -= 30; r = find(again(F), "2019_01_IND_LAC", 3230, 3251)
    injected_fault(f"NEG1 PL2 W moved 30 s earlier: game level {None if row_pl2 is None else row_pl2['game_level']} -> {None if r is None else r['game_level']}", r is not None and r["game_level"] == "FASTER not licensed")
    F = G19.copy(); F.loc[F["order_sequence"] == 3230, "incomplete_pass"] = 1.0; r = find(again(F), "2019_01_IND_LAC", 3230, 3251)
    injected_fault(f"NEG2 PL2 relabeled incomplete: {None if row_pl2 is None else row_pl2['cls']} -> {None if r is None else r['cls']}", r is not None and r["cls"] == "STOP")
    if r5 is not None:
        G23 = game(2023, r5["game_id"])
        F = G23.copy(); F.loc[F["order_sequence"] == r5["sa"], "E_s"] -= 30; r = find(again(F), r5["game_id"], r5["sa"], r5["sb"])
        injected_fault(f"NEG3 PL5 E moved 30 s earlier: D3 {r5['d3']} -> {None if r is None else r['d3']}", r is not None and r["d3"] == "OVER 40")
        og = Counter(again(G23)["d3"]); F = G23.copy(); F.loc[F["order_sequence"] == r5["sa"], ["E_s", "E_r", "E_d"]] = np.nan; ng = Counter(again(F)["d3"])
        ch = {k: ng[k] - og[k] for k in ("WITHIN 40", "OVER 40", "UNCHECKED")}
        injected_fault(f"NEG4 PL5 E deleted: D3 changes {ch}", ch["UNCHECKED"] == 1 and ch["WITHIN 40"] + ch["OVER 40"] == -1)
    else:
        injected_fault("NEG3 (no PL5 to injected_fault on)", False); injected_fault("NEG4 (no PL5 to injected_fault on)", False)
    if r1b is not None:
        F = G19.copy(); F.loc[F["order_sequence"] == r1b["sb"], "quarter_seconds_remaining"] = 121.0; r = find(again(F), "2019_01_IND_LAC", r1b["sa"], r1b["sb"])
        injected_fault(f"NEG5 PL1b next snap at 2:01: warning True -> {None if r is None else r['tmw']}", r is not None and r["tmw"] in F_)
    else:
        injected_fault("NEG5 (no PL1b to injected_fault on)", False)
    if len(ro):
        r6 = ro.iloc[0]; s6 = int(r6["season"]); F = game(s6, r6["game_id"]).copy()
        wa = F.loc[F["order_sequence"] == r6["sa"], "W_s"].iloc[0]; wd = F.loc[F["order_sequence"] == r6["sa"], "W_d"].iloc[0]
        F.loc[F["order_sequence"] == r6["sb"], "W_s"] = wa + r6["dG"] - 5; F.loc[F["order_sequence"] == r6["sb"], "W_d"] = wd
        ra = find(again(F), r6["game_id"], r6["sa"], r6["sb"])
        m = (F["order_sequence"] >= r6["sa"]) & (F["order_sequence"] < r6["sb"])
        F.loc[m, "desc"] = F.loc[m, "desc"].map(lambda v: RUNOFF.sub("", v) if isinstance(v, str) else v); rb = find(again(F), r6["game_id"], r6["sa"], r6["sb"])
        injected_fault(f"NEG6 {r6['game_id']} {r6['sa']} -> {r6['sb']} real time shortened to dG - 5: {r6['game_level']} -> {None if ra is None else ra['game_level']}; runoff text removed -> {None if rb is None else rb['game_level']}",
              ra is not None and rb is not None and ra["game_level"] == "FASTER licensed (runoff)" and rb["game_level"] == "FASTER not licensed")
    else:
        injected_fault("NEG6 (no PL6 to injected_fault on)", False)
    if row_pl7 is not None:
        F = game(2023, row_pl7["game_id"]).copy(); m = F["order_sequence"].isin([row_pl7["sa"], row_pl7["sb"]])
        F.loc[m, "qtr"] = 4.0; F.loc[F["order_sequence"] == row_pl7["sa"], "quarter_seconds_remaining"] = 200.0; F.loc[F["order_sequence"] == row_pl7["sb"], "quarter_seconds_remaining"] = 180.0
        r = find(again(F), row_pl7["game_id"], row_pl7["sa"], row_pl7["sb"])
        injected_fault(f"NEG7 PL7 moved to q4 at 3:20: {row_pl7['cls']} -> {None if r is None else (r['cls'], r['why'])}", r is not None and r["cls"] == "STOP")
    else:
        injected_fault("NEG7 (no PL7 to injected_fault on)", False)
    c8 = pd.concat([IV[s].assign(season=s) for s in seasons])
    c8 = c8[c8["inj"] & (c8["bw"] == False) & ~c8["inc"] & ~c8["score"] & ~c8["poss"] & ~c8["tmo"] & ~c8["pen"] & ~c8["rep"] & ~c8["ref"] & (c8["ob"] == 0) & (c8["tmw"] == False) & (c8["presnap"] == "")]
    r8 = c8.iloc[0] if len(c8) else None
    print(f"  PL8 candidates (injury in play text after the warning, no other stoppage event): {len(c8)}")
    if r8 is not None:
        print(f"  PL8 found and pinned: {r8['season']} {r8['game_id']} seq {r8['sa']} -> {r8['sb']} (line {L('PL8 ')}):"); rows(game(int(r8["season"]), r8["game_id"]), r8["sa"], r8["sb"])
    injected_fault(f"PL8 STOP (4-5-4) (got {None if r8 is None else (r8['cls'], r8['why'])})", r8 is not None and r8["cls"] == "STOP")
    if r8 is not None:
        F = game(int(r8["season"]), r8["game_id"]).copy()
        F.loc[F["order_sequence"] == r8["sa"], "quarter_seconds_remaining"] = 300.0; F.loc[F["order_sequence"] == r8["sb"], "quarter_seconds_remaining"] = 280.0
        r = find(again(F), r8["game_id"], r8["sa"], r8["sb"])
        injected_fault(f"NEG8 PL8 snap clocks moved to 5:00 and 4:40: {r8['cls']} -> {None if r is None else (r['cls'], r['why'])}", r is not None and r["cls"] == "PARTIAL")
    else:
        injected_fault("NEG8 (no PL8 to injected_fault on)", False)
    G9 = game(2019, "2019_18_BUF_HOU"); r9 = find(again(G9), "2019_18_BUF_HOU", 4363, 4392)
    print(f"  PL9 2019_18_BUF_HOU 4363 -> 4392 (line {L('PL9 ')}):"); rows(G9, 4363, 4392)
    injected_fault(f"PL9 PARTIAL (4-3-2a; 16-1-4(h) no window in period 1) (got {None if r9 is None else (r9['q'], r9['pt'], r9['cls'], r9['why'])})", r9 is not None and r9["cls"] == "PARTIAL")
    F = G9.copy(); F.loc[F["order_sequence"].isin([4363, 4392]), "qtr"] = 6.0; r = find(again(F), "2019_18_BUF_HOU", 4363, 4392)
    injected_fault(f"NEG9 PL9 quarter set to 6: {None if r9 is None else r9['cls']} -> {None if r is None else (r['cls'], r['why'])}", r is not None and r["cls"] == "UNKNOWN")
    G10 = game(2023, "2023_01_ARI_WAS"); r10 = find(again(G10), "2023_01_ARI_WAS", 77, 102)
    print(f"  PL10 2023_01_ARI_WAS seq 77 -> 102 (line {L('PL10 ')}; FASTER by +0.330 s in the frozen run):"); rows(G10, 77, 102)
    injected_fault(f"PL10 WITHIN RESOLUTION (got {None if r10 is None else (r10['game_level'], round(r10['dG'] - r10['dW'], 3), r10['res'])})", r10 is not None and r10["game_level"] == "WITHIN RESOLUTION")
    r = find(again(G10, 0.0), "2023_01_ARI_WAS", 77, 102)
    injected_fault(f"NEG10 G's 1 s removed from the margin: PL10 {None if r10 is None else r10['game_level']} -> {None if r is None else r['game_level']}", r is not None and r["game_level"].startswith("FASTER"))
    npass = sum(ok for _, ok in res)
    if npass != len(res) or len(res) != 21:
        print(f"\nCLOCK SUMMARY injected faults {npass}/{len(res)} FAILED: {[n.split(' ')[0] for n, ok in res if not ok]} | no count read, no file written")
        sys.exit(1)

    print(f"\n=== 3. FROZEN 2023 D3 COUNTS (line {L('2023 the team level')}) ===")
    v5 = Counter(IV[2023]["d3_v5"]); v16 = Counter(IV[2023]["d3"]); repro = all(v5[k] == FROZEN_2023[k] for k in FROZEN_2023)
    for k in FROZEN_2023:
        print(f"  {k:12s} frozen {FROZEN_2023[k]} | frozen definition (warning from rows) {v5[k]} {'REPRODUCED' if v5[k] == FROZEN_2023[k] else 'NOT REPRODUCED'} | v16 {v16[k]} change {v16[k] - v5[k]:+d}")
    mv = IV[2023][IV[2023]["d3"] != IV[2023]["d3_v5"]]
    by_edit = Counter("warning placed by the quarter clock" if (r["tmw"] is not None and bool(r["tmw"]) != bool(r["tmw_row_v5"])) else
                      ("reader: warning placement unread (quarter clock empty)" if r["tmw"] is None else "unattributed") for _, r in mv.iterrows())
    print(f"  intervals whose D3 word moved between the frozen and current definitions: {len(mv)} | by edit {dict(by_edit)}")

    got = {s: int(IV[s]["game_level"].str.startswith("FASTER").sum()) for s in seasons}
    print(f"\n=== FASTER against line {L('EXPECTED before')} (expected before the run): got {got} | expected {EXPECTED_FASTER} -> {'AGREE' if got == EXPECTED_FASTER else 'DISAGREE'}")
    if got != EXPECTED_FASTER:
        print(f"CLOCK SUMMARY injected faults {npass}/{len(res)} | FASTER {got} DISAGREES with line {L('EXPECTED before')} {EXPECTED_FASTER}: code and text disagree | no file written")
        sys.exit(1)

    print("\n=== 4. PER SEASON: classes, game level (four counts, resolution margin) beside GAME_LEVEL_PRIOR, D3 as three counts (no decision word) ===")
    crow, fa, ov = [], [], []
    for s in seasons:
        iv = IV[s]
        cl = Counter(iv["cls"]); tags = Counter(w for v in iv.loc[iv["cls"] != "STOP", "why"] for w in v.split("+") if w)
        print(f"\n{s}: intervals {len(iv)} | classes {dict(cl)} | ADMIN {int((iv['admin'] == True).sum())} | midnight wraps {int(iv['wrap'].sum())}")
        print(f"   non-STOP reasons (PARTIAL and UNKNOWN), tagged: {dict(tags)}")
        for k, n in cl.items(): crow.append((s, "CLASS", k, n))
        for k, n in tags.items(): crow.append((s, "TAG", k, n))
        for law in ("game_level", "game_level_prior", "d3"):
            cnt = Counter(iv[law]); print(f"  {law.upper()}: {dict(cnt)}")
            for k, n in cnt.items(): crow.append((s, law.upper(), k, n))
            un = iv[iv[law] == "UNCHECKED"]
            if len(un):
                print(f"    UNCHECKED by play type {dict(Counter(un['pt']))} | by class {dict(Counter(un['cls']))}")
        f_ = iv[iv["game_level"].str.startswith("FASTER")].assign(season=s, size=lambda z: z["dG"] - z["dW"]); fa.append(f_)
        o_ = iv[iv["d3"] == "OVER 40"].assign(season=s, size=lambda z: z["x"] - 40); ov.append(o_)
        for _, r in f_.head(10).iterrows(): print(f"      {r['game_level']}: {r['game_id']} {r['sa']}->{r['sb']} q{r['q']} {r['cls']} dG - dW {r['size']:+.3f} s")
        for _, r in o_.head(10).iterrows(): print(f"      OVER 40: {r['game_id']} {r['sa']}->{r['sb']} q{r['q']} {r['cls']} by {r['size']:+.3f} s")
    rrow = []   # N7: each count split by its reason
    for s in seasons:
        iv = IV[s]
        for (k, w), n in Counter(zip(iv["cls"], iv["why"])).items(): rrow.append((s, "CLASS", k, w if w else CLASS_EMPTY.get(k), n))
        for k, n in Counter(w for v in iv.loc[iv["cls"] != "STOP", "why"] for w in v.split("+") if w).items(): rrow.append((s, "TAG", k, k, n))
        for law, RS in (("game_level", GAME_LEVEL_REASON), ("game_level_prior", GAME_LEVEL_PRIOR_REASON), ("d3", D3_REASON)):
            for k, n in Counter(iv[law]).items(): rrow.append((s, law.upper(), k, RS.get(k), n))
    RR = pd.DataFrame(rrow, columns=["season", "check", "word", "reason", "count"])
    nore = RR[RR["reason"].isna()]
    back_ = RR.groupby(["season", "check", "word"])["count"].sum().to_dict(); ct_ = {(a, b, c_): n for a, b, c_, n in crow}
    print(f"\nreasons table: rows {len(RR)} | rows with no reason {len(nore)} | the split sums back to the counts: {back_ == ct_}")
    if len(nore) or back_ != ct_:
        print(f"CLOCK SUMMARY injected faults {npass}/{len(res)} | the reason split is incomplete or does not sum to the counts | no file written"); sys.exit(1)
    KEEP = ["season", "game_id", "sa", "sb", "q", "pt", "cls", "why", "runoff", "dG", "dW", "rW", "res", "x", "rx", "size", "game_level", "game_level_prior", "d3"]
    with open(OUT_COUNTS, "w") as f:
        f.write(f"# {tag}\n"); pd.DataFrame(crow, columns=["season", "check", "word", "count"]).to_csv(f, index=False)
    with open(OUT_FASTER, "w") as f:
        f.write(f"# {tag}\n"); pd.concat(fa)[KEEP].to_csv(f, index=False)
    with open(OUT_OVER40, "w") as f:
        f.write(f"# {tag}\n"); pd.concat(ov)[KEEP].to_csv(f, index=False)
    with open(OUT_REASONS, "w") as f:
        f.write(f"# {tag}\n"); RR.to_csv(f, index=False)
    print(f"written, stamped on line 1: {OUT_REASONS} rows {len(RR)} sha {sha(OUT_REASONS)}")
    nf, no = len(pd.concat(fa)), len(pd.concat(ov))
    print(f"\nwritten, stamped on line 1: {OUT_COUNTS} sha {sha(OUT_COUNTS)} | {OUT_FASTER} rows {nf} sha {sha(OUT_FASTER)} | {OUT_OVER40} rows {no} sha {sha(OUT_OVER40)}")

    print("\n=== 5. READS (distributions, not graded) ===")
    for s in seasons:
        iv = IV[s]; ck = iv[iv["game_level"] != "UNCHECKED"].copy(); ck["lag"] = ck["dW"] - ck["dG"]; st = {}
        for cl in ("RUN", "PARTIAL", "STOP"):
            v = ck.loc[ck["cls"] == cl, "lag"]; st[cl] = v
            if len(v):
                print(f"  D1 {s} {cl:7s} n {len(v)} median {v.median():.1f} p90 {v.quantile(.9):.1f} p99 {v.quantile(.99):.1f}")
        if len(st["RUN"]) and len(st["STOP"]):
            print(f"  D1 {s} separation: RUN above the STOP median {(st['RUN'] > st['STOP'].median()).mean():.3f} | STOP below the RUN p90 {(st['STOP'] < st['RUN'].quantile(.9)).mean():.3f}")
        win = ["last 2:00 of the first half" if q == 2 and not nan(qa) and qa <= 120 else ("last 5:00 of the game" if q == 4 and not nan(qa) and qa <= 300 else ("overtime" if q >= 5 else "rest"))
               for q, qa in zip(iv["q"], iv["qa"])]
        for (cl, w), v in iv.assign(win=win).groupby(["cls", "win"])["dG"]:
            print(f"  D2 {s} {cl:7s} {w:28s} n {len(v)} median game seconds per snap {v.median():.1f}")
    print(f"\nCLOCK SUMMARY injected faults {npass}/{len(res)} | FASTER {got} = line {L('EXPECTED before')} | 2023 D3 frozen: {'reproduced' if repro else 'NOT reproduced'}; moved by edit {dict(by_edit)} | "
          f"{OUT_COUNTS} {sha(OUT_COUNTS)} | {OUT_FASTER} {nf} rows {sha(OUT_FASTER)} | {OUT_OVER40} {no} rows {sha(OUT_OVER40)}")


if __name__ == "__main__":
    main()
