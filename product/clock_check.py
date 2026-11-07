"""clock_check.py - section 4's stopped-clock check (4-3, 4-4, 4-5, 3-41, 15-5-2 runoff), its bound an explicit assumption, and the one definition
of a no-play down (down_row) and of an injury on a play (injury_text). Product code.
Accepted from run e2b_v17_1725d9c82df1's shared library (lib_check) as 124c6a39e406; the warning's section label is an argument (warn_sec).
v19 f: 4-3-2e(3)'s stop is located at the offense's own pre-snap foul (check_clock's definition of the event), not at the first foul row with no play. check_clock.py is not changed: its snap kinds and injury pattern are set for the call only.
test_clock_check.py runs its known-right cases and proves its answers on the play-by-play record byte-identical to the run's copy."""
import re
from collections import Counter
import numpy as np
import rules, check_clock, check_downs, engine
from transition import nanv, one_

RUNOFF_RX = re.compile(r"run[- ]?off", re.I)
INJ_RX = re.compile(r"injur", re.I)
INJ_UPD_RX = re.compile(r"Injury\s+Update\s*:.{0,160}?returned\s+to\s+the\s+game\.?", re.I | re.S)


def injury_text(t):
    """v16 e: an injury the play's text reports; an 'Injury Update: ... has returned to the game' announcement is not an injury on that play (one
    definition: the table, check_clock's stretches in section 4 and the check's own location of 4-5-4 all read it)."""
    return bool(INJ_RX.search(INJ_UPD_RX.sub(" ", str(t))))


class _InjRead:
    """check_clock's injury pattern as v16 e reads it (check_clock.py itself unchanged; set in its place only while section 4 runs on v16's definitions)."""
    def search(self, t):
        return INJ_RX.search(INJ_UPD_RX.sub(" ", str(t)))


def down_row(play_type, timeout, penalty_type, desc):
    """A no-play DOWN (c's category 1, one definition for the table, the race's rows and section 4, on the play-by-play record and on the engine's games alike): a
    no-play row that is not a timeout, whose foul is named (penalty_type or a 'PENALTY on' clause), and whose text describes a play before PENALTY."""
    return play_type == "no_play" and not one_(timeout) and (isinstance(penalty_type, str) or bool(check_downs.foul_clauses(desc))) and engine.has_play(desc)


STOP_AT_PLAY = ("incomplete 4-4f", "out of bounds late 4-3-2a", "score/touchback/try 4-4d", "change of possession 4-4i")


def warn_place(qa, la):
    """g, d (c): where the table places the warning: at the conclusion of a down that ran past 2:00 (its stamped length), else between downs at 2:00
    (the book silent: a declared assumption); None when the down is unstamped."""
    if nanv(la) or nanv(qa): return None
    return "at the conclusion of the down" if qa - la <= 120 else "between downs at 2:00"


def check_clock2(seasons, keep_rows=False, warn_sec=None):
    """Section 4's stopped-clock check (v14 l, Q1): (a) the allowance is an ASSUMED QUANTIZATION BOUND, worst case and convention-free: each whole-second
    game-clock reading assumed within 1 s of the true clock, each stamp within its own stored resolution (check_clock.parse); a stored resolution is a printed
    precision, not a measured accuracy, so a stretch inside the bound is 'within the assumed quantization bound' and one outside it 'unexplained beyond the
    bound' (no cause is assigned by the check); (b) a stretch with a play unstamped prints UNCHECKED; (c) the two-minute warning found where the table places
    it (warn_place, cited per book), at the down that ran past 2:00, the downs played after it running the clock from their snaps; (d) the stopping events
    are check_clock's own (rules.clock_class's definition, the stretch's 'why'), each located at the play's end or at its own row; a 10-second runoff (15-5-2, 4-7-1)
    licensed by check_clock's runoff text, 10 s each. A no-play down (down_row) is a snap: check_clock's stretches end and start at it; an injury is read by injury_text
    (check_clock.py unchanged: its snap kinds and injury pattern set for the call only).
    warn_sec: book -> the warning's section as the caller read it (a label only; missing reads 'Rule 3 (book unread)').
    Returns counts, failures (each with its excess over the allowance) and what each part of the allowance passes."""
    out = Counter(); fails = []; cost = Counter(); rows_kept = []
    keep_sk, keep_inj = check_clock.SNAP_KINDS, check_clock.INJ
    for s in seasons:
        d, _, _ = check_clock.load(s)
        d = d.copy(); m_ = np.array([down_row(p_, to_, pt_, t_) for p_, to_, pt_, t_ in zip(d["play_type"], d["timeout"], d["penalty_type"], d["desc"])], bool)
        d.loc[m_, "play_type"] = "no_play_down"; out["no-play downs made snaps"] += int(m_.sum())
        check_clock.SNAP_KINDS = tuple(keep_sk) + ("no_play_down",); check_clock.INJ = _InjRead()
        bk = rules.RULE_BOOK_OF[s][0]
        try:
            gl_ = list(d.groupby("game_id", sort=False))
            ivs = [(g.reset_index(drop=True), check_clock.intervals(g)) for _, g in gl_]
        finally:
            check_clock.SNAP_KINDS, check_clock.INJ = keep_sk, keep_inj
        ijr = injury_text
        for g, iv in ivs:
            c = {k: g[k].tolist() for k in g.columns}
            idx = {int(v): k for k, v in enumerate(c["order_sequence"])}
            for x in iv:
                if x["cls"] == "INSUFFICIENT_EVIDENCE":
                    out["check_clock class INSUFFICIENT_EVIDENCE"] += 1; fails.append(("INSUFFICIENT_EVIDENCE", x["game_id"], x["sa"], x["sb"], np.nan, np.nan, x["why"], np.nan, s, x["q"], x["reg"])); continue
                if x["cls"] not in ("STOP", "PARTIAL"): continue
                a, b = idx[x["sa"]], idx[x["sb"]]; bt = list(range(a + 1, b)); ab = [a] + bt
                nro = sum(1 for k in ab if RUNOFF_RX.search(str(c["desc"][k] or "")))
                lic = 10.0 * nro
                if x["cls"] == "PARTIAL":
                    if nanv(x["dW"]) or nanv(c["W_r"][a]) or nanv(c["W_r"][b]):
                        out["PARTIAL unchecked (a stamp missing)"] += 1; continue
                    prec = 2.0 + c["W_r"][a] + c["W_r"][b]
                    allowed = x["dW"] + prec + lic; out["PARTIAL checked"] += 1
                    if x["dG"] > allowed:
                        out["PARTIAL failed"] += 1; fails.append(("PARTIAL", x["game_id"], x["sa"], x["sb"], x["dG"], round(allowed, 3), x["why"], round(x["dG"] - allowed, 3), s, x["q"], x["reg"]))
                    else:
                        if x["dG"] > x["dW"] + lic: cost["PARTIAL passing only by the assumed quantization bound"] += 1
                        if lic and x["dG"] > x["dW"] + prec: cost["PARTIAL passing only by the runoff license"] += 1
                    continue
                out["STOP checked"] += 1
                plays = [a] + [k for k in bt if c["play_type"][k] in ("kickoff", "extra_point") or one_(c["two_point_attempt"][k])
                               or (c["play_type"][k] == "no_play" and one_(c["penalty"][k]) and engine.has_play(c["desc"][k]))]
                if any(nanv(c["E_s"][k]) or nanv(c["W_s"][k]) for k in plays):
                    out["STOP unchecked (a play unstamped)"] += 1; continue
                ln = sum(check_clock.diff(c["E_s"][k], c["E_d"][k], c["W_s"][k], c["W_d"][k])[0] for k in plays)
                pln = sum(c["E_r"][k] + c["W_r"][k] for k in plays)
                why = str(x["why"]).split("+"); cands = []
                txt = {k: str(c["desc"][k] or "") for k in ab}
                pen_k = [k for k in bt if one_(c["penalty"][k])]; to_k = [k for k in bt if one_(c["timeout"][k])]
                for w in why:
                    if w in STOP_AT_PLAY: cands.append((w, "the play's end", ln + pln))
                    elif w == "foul in window 4-3-2e":
                        if one_(c["penalty"][a]): cands.append((w, "the play's end", ln + pln))
                        for k in pen_k[:1]: cands.append((w, f"its row ({k - a} after)", None, k))
                    elif w == "offensive pre-snap foul q4/OT 4-3-2e(3)":   # located at the offense's own pre-snap foul (v19 f): check_clock's definition of the event, a foul row with no
                        # play whose team is the next snap's offense and whose name is a pre-snap foul (check_clock.PRESNAP_OFFENSE); another team's foul in the stretch is not it
                        for k in [k for k in pen_k if not engine.has_play(txt[k]) and c["penalty_team"][k] == c["posteam"][b] and c["penalty_type"][k] in check_clock.PRESNAP_OFFENSE][:1]:
                            cands.append((w, f"its row ({k - a} after)", None, k))
                    elif w == "charged timeout 4-5-1":
                        for k in to_k[:1]: cands.append((w, f"its row ({k - a} after)", None, k))
                    elif w == "injury after the warning 4-5-4":
                        if ijr(txt[a]): cands.append((w, "the play's end", ln + pln))
                        else:
                            for k in [k for k in bt if ijr(txt[k])][:1]: cands.append((w, f"its row ({k - a} after)", None, k))
                    elif w == "two-minute warning 3-41":
                        # the warning at the down that ran past 2:00 (each down in the stretch in order, its clock at its row, its stamped length), else between downs at 2:00;
                        # the downs played after it run the clock from their snaps (their stamped lengths and precision added)
                        cite = (warn_sec or {}).get(bk, 'Rule 3 (book unread)'); kx = None; pl = None
                        for k in plays:
                            qk = x["qa"] if k == a else c["quarter_seconds_remaining"][k]
                            if nanv(qk) or qk <= 120: break
                            pl = warn_place(qk, check_clock.diff(c["E_s"][k], c["E_d"][k], c["W_s"][k], c["W_d"][k])[0])
                            if pl == "at the conclusion of the down": kx = k; break
                        if kx == a: cands.append((w, f"at the conclusion of the down ({cite})", ln + pln))
                        elif kx is not None: cands.append((w, f"at the conclusion of the down {kx - a} after ({cite})", None, kx))
                        elif pl is not None:
                            aft = [k for k in plays if k != a and not nanv(c["quarter_seconds_remaining"][k]) and c["quarter_seconds_remaining"][k] <= 120]
                            ext = sum(check_clock.diff(c["E_s"][k], c["E_d"][k], c["W_s"][k], c["W_d"][k])[0] + c["E_r"][k] + c["W_r"][k] for k in aft)
                            cands.append((w, f"between downs at 2:00 ({cite})" + (f", then {len(aft)} down(s) played" if aft else ""), "clock", x["qa"] - 120.0 + ext))
                allowed_l = []
                for cd in cands:
                    if len(cd) == 4 and cd[2] is None:
                        k = cd[3]
                        if nanv(c["W_s"][k]) or nanv(c["E_s"][a]): continue
                        rb = check_clock.diff(c["W_s"][k], c["W_d"][k], c["E_s"][a], c["E_d"][a])[0]
                        allowed_l.append((cd[0], cd[1], ln + rb + pln + c["W_r"][k] + c["E_r"][a]))
                    elif len(cd) == 4 and cd[2] == "clock":
                        allowed_l.append((cd[0], cd[1], cd[3]))
                    else:
                        allowed_l.append((cd[0], cd[1], cd[2]))
                if not allowed_l:
                    out["STOP with no stopping event found (failed)"] += 1; fails.append(("STOP no stop event", x["game_id"], x["sa"], x["sb"], x["dG"], np.nan, x["why"], np.nan, s, x["q"], x["reg"])); continue
                ev_, at_, base_ = min(allowed_l, key=lambda z: z[2])
                allowed = base_ + 2.0 + lic
                if keep_rows: rows_kept.append((x["game_id"], x["sa"], x["sb"], ev_, at_, x["dG"], allowed))
                if x["dG"] > allowed:
                    out["STOP failed"] += 1; fails.append(("STOP", x["game_id"], x["sa"], x["sb"], x["dG"], round(allowed, 3), x["why"], round(x["dG"] - allowed, 3), s, x["q"], x["reg"], ev_, at_))
                else:
                    raw_ = base_ - (pln if at_ == "the play's end" else 0)
                    if x["dG"] > raw_ + lic: cost["STOP passing only by the assumed quantization bound"] += 1
                    if lic and x["dG"] > base_ + 2.0: cost["STOP passing only by the runoff license"] += 1
                    if ev_ == "two-minute warning 3-41": cost["STOP stopped by the warning, " + re.sub(r" \d+ after", " after the first", at_.split(" (")[0]) + (", then downs played" if "then" in at_ else "")] += 1
    return out, fails, cost, rows_kept
