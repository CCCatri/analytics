"""test_clock_check.py - clock_check.py's own test (v19 f: 4-3-2e(3)'s stop located at the offense's own pre-snap foul). Each check names, before it
runs, the output that fails it; exit 0 only when every check passes.
1. known-right cases, each built by hand from the rule it names: an injury on the play (4-5-3, 4-5-4) against an 'Injury Update ... returned to the game'
   announcement; a no-play down (3-8-4: the down ran and its play was wiped by a foul) against a charged timeout row (4-5-1) and a foul before the snap
   (no play described); where the two-minute warning falls (3-41). FAILS: any case returning other than it must.
2. against the chain's copy (chain e2b_v17_1725d9c82df1's library, lib sha c1357bc133c2) on the whole record, every season e1.SIM_SEASONS names:
   FAILS if any failure or checked stretch differs where neither copy located its stop at the offensive pre-snap foul of 4-3-2e(3) (the fix reaches
   nothing else), or if the stretches failed rise (the no-rise gate: the fix may only locate the stop at the event r2 itself names).
3. the fix alone: this file's source with the one located line put back as v18 had it (the first foul row with no play) must be byte-identical to the
   chain's copy in all four results. FAILS: any difference (something else changed).
4. the comparison's own plant: the check run on the first season with no row read as a no-play down must differ from the chain's copy. FAILS: no difference.
The record's numbers print beside v18's (1,214 of 37,112 stamped stopped stretches failed; 14 with no stopping event; 22 partial failed)."""
import ast, hashlib, importlib, os, sys, tempfile, time
T0 = time.time()
sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
CHAIN, CHAIN_SHA, LIB_SHA = "e2b_v17_1725d9c82df1.py", "1725d9c82df1", "c1357bc133c2"
FAILED = []


def check(name, ok, detail):
    print(f"  [{time.time() - T0:6.1f} s] {name}: {detail} -> {'PASS' if ok else 'FAIL'}")
    if not ok: FAILED.append(name)


def chain_lib():
    """The chain's shared library, taken from the chain file's text (the one string that opens it), written to a temporary folder and imported."""
    if not os.path.exists(CHAIN) or sh(CHAIN) != CHAIN_SHA: sys.exit(f"STOPPED: {CHAIN} is missing or not sha {CHAIN_SHA}; nothing compared")
    hits = [n.value for n in ast.walk(ast.parse(open(CHAIN).read())) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith('"""E2b v17')]
    if len(hits) != 1 or hashlib.sha256(hits[0].encode()).hexdigest()[:12] != LIB_SHA: sys.exit(f"STOPPED: the chain's library is not one string of sha {LIB_SHA}")
    d_ = tempfile.mkdtemp(); open(os.path.join(d_, "e2b_v17_lib.py"), "w").write(hits[0]); sys.path.insert(1, d_)
    return importlib.import_module("e2b_v17_lib")


print(f"test_clock_check.py {sh('test_clock_check.py')} | clock_check.py {sh('clock_check.py')} | transition.py {sh('transition.py')}")
print("EXPECT: 1. 13 known-right cases, 0 fail | 2. every difference from the chain's copy a 4-3-2e(3) stretch, failures not above the copy's | 3. v18's line put back: 0 of 4 results differ | 4. the plant differs")
import clock_check as C
import e1

print("1. known-right cases (FAILS: any case returning other than it must)")
PLAY = "(5:12) (Shotgun) P.Mahomes pass short right to T.Kelce to KC 40 for 6 yards (J.Doe)."
CASES = [
    ("4-5-3/4-5-4 an injury on the play", C.injury_text, (PLAY + " BUF-J.Doe was injured during the play.",), True),
    ("an 'Injury Update ... returned to the game' announcement is not an injury on the play", C.injury_text, (PLAY + " Injury Update: KC-87-T.Kelce has returned to the game.",), False),
    ("an injury on the play, an announcement after it", C.injury_text, (PLAY + " BUF-J.Doe was injured during the play. Injury Update: KC-87-T.Kelce has returned to the game.",), True),
    ("no injury written", C.injury_text, (PLAY,), False),
    ("3-8-4 a no-play down: the play ran, a named foul wiped it", C.down_row, ("no_play", 0, "Defensive Holding", PLAY + " PENALTY on BUF-J.Doe, Defensive Holding, 5 yards, enforced at KC 34 - No Play."), True),
    ("3-8-4 a no-play down: the foul named only in the text", C.down_row, ("no_play", 0, None, PLAY + " PENALTY on BUF-J.Doe, Defensive Holding, 5 yards, enforced at KC 34 - No Play."), True),
    ("4-5-1 a charged timeout row is not a down", C.down_row, ("no_play", 1, None, "Timeout #1 by KC at 05:12."), False),
    ("14-4-9 a foul before the snap: no play described", C.down_row, ("no_play", 0, "False Start", "(5:12) (Shotgun) PENALTY on KC-71-J.Smith, False Start, 5 yards, enforced at KC 34 - No Play."), False),
    ("a play row is not a no-play down", C.down_row, ("pass", 0, None, PLAY), False),
    ("a no-play row with no foul named", C.down_row, ("no_play", 0, None, PLAY), False),
    ("3-41 the warning at the conclusion of a down that ran past 2:00 (snapped at 2:10, 15 s long)", C.warn_place, (130.0, 15.0), "at the conclusion of the down"),
    ("3-41 the warning between downs at 2:00 (snapped at 2:05, 3 s long)", C.warn_place, (125.0, 3.0), "between downs at 2:00"),
    ("an unstamped down: the warning's place unread", C.warn_place, (125.0, float("nan")), None),
]
bad_ = [(nm_, want, f(*a)) for nm_, f, a, want in CASES if f(*a) != want]
for b_ in bad_: print(f"    FAILED: {b_[0]}: must be {b_[1]!r}, came back {b_[2]!r}")
check("known-right cases", len(CASES) == 13 and not bad_, f"{len(CASES)} cases, {len(bad_)} failed")

print("2. against the chain's copy on the record (FAILS: a difference outside 4-3-2e(3)'s located stop, or the stretches failed rising)")
L = chain_lib()
S = list(e1.SIM_SEASONS)
print(f"  seasons {S}; each check runs once per copy")
mine = C.check_clock2(S, keep_rows=True); print(f"  [{time.time() - T0:6.1f} s] clock_check.py done")
theirs = L.check_clock2(S, keep_rows=True); print(f"  [{time.time() - T0:6.1f} s] the chain's copy done")
W3 = "offensive pre-snap foul q4/OT 4-3-2e(3)"
fm_ = {(f_[0], f_[1], f_[2], f_[3]): f_ for f_ in mine[1]}; ft_ = {(f_[0], f_[1], f_[2], f_[3]): f_ for f_ in theirs[1]}
fdiff = [k_ for k_ in set(fm_) | set(ft_) if repr(fm_.get(k_)) != repr(ft_.get(k_))]
f_out = [k_ for k_ in fdiff if W3 not in str((fm_.get(k_) or ft_.get(k_))[6])]
rm_ = {(r_[0], r_[1], r_[2]): r_ for r_ in mine[3]}; rt_ = {(r_[0], r_[1], r_[2]): r_ for r_ in theirs[3]}
rdiff = [k_ for k_ in set(rm_) | set(rt_) if repr(rm_.get(k_)) != repr(rt_.get(k_))]
r_out = [k_ for k_ in rdiff if not ((rm_.get(k_) or (None,) * 4)[3] == W3 or (rt_.get(k_) or (None,) * 4)[3] == W3)]
for k_ in (f_out + r_out)[:5]: print(f"    OUTSIDE THE FIX: {k_}: here {fm_.get(k_) or rm_.get(k_)} | chain {ft_.get(k_) or rt_.get(k_)}")
check("every difference is a stretch whose stop the chain's copy or this file located at 4-3-2e(3)'s foul", not f_out and not r_out,
      f"failures differing {len(fdiff)} (outside the fix {len(f_out)}) | checked stretches differing {len(rdiff)} (outside the fix {len(r_out)})")
fa_m, fa_t = mine[0].get("STOP failed", 0), theirs[0].get("STOP failed", 0)
check("the no-rise gate: stamped stopped stretches failed", fa_m <= fa_t, f"{fa_m} here, {fa_t} in the chain's copy (v18 printed 1,214)")
print(f"    counts here {dict(mine[0])}")
print(f"    counts in the chain's copy {dict(theirs[0])}")
for k_ in fdiff[:8]: print(f"    differs: {k_}: here {fm_.get(k_)} | chain {ft_.get(k_)}")

print("3. the fix alone (FAILS: the source with v18's located line put back differs from the chain's copy)")
import inspect
src_ = inspect.getsource(C)
NEW_L = 'for k in [k for k in pen_k if not e1.has_play(txt[k]) and c["penalty_team"][k] == c["posteam"][b] and c["penalty_type"][k] in r2.PRESNAP_OFFENSE][:1]:'
OLD_L = 'for k in [k for k in pen_k if not e1.has_play(txt[k])][:1]:'
ns_ = {"__name__": "clock_check_v18_line"}
if src_.count(NEW_L) != 1: check("the fixed line found once in clock_check.py", False, f"found {src_.count(NEW_L)} times")
else:
    exec(compile(src_.replace(NEW_L, OLD_L), "clock_check_v18_line", "exec"), ns_)
    back_ = ns_["check_clock2"](S, keep_rows=True)
    nd_ = sum(repr(sorted(back_[k_].items()) if k_ in (0, 2) else back_[k_]) != repr(sorted(theirs[k_].items()) if k_ in (0, 2) else theirs[k_]) for k_ in range(4))
    check("v18's located line put back: byte-identical to the chain's copy", nd_ == 0, f"{nd_} of 4 results differ")

print("4. the comparison's own plant (FAILS: no difference)")
keep_ = C.down_row; C.down_row = lambda *a: False
try: pl_ = C.check_clock2(S[:1], keep_rows=True)
finally: C.down_row = keep_
one_ = L.check_clock2(S[:1], keep_rows=True)
pd_ = sum(repr(pl_[k_]) != repr(one_[k_]) for k_ in range(4))
check(f"no row read as a no-play down, season {S[0]}", pd_ > 0, f"{pd_} of 4 results differ from the chain's copy (no-play downs made snaps here {pl_[0].get('no-play downs made snaps', 0)}, there {one_[0].get('no-play downs made snaps', 0)})")

kn = mine[0]; st_ = kn.get("STOP checked", 0) - kn.get("STOP unchecked (a play unstamped)", 0)
print(f"the record (printed, not a check): stamped stopped stretches failed {kn.get('STOP failed', 0)} of {st_}"
      f" ({kn.get('STOP failed', 0) / st_:.4f}) | no stopping event {kn.get('STOP with no stopping event found (failed)', 0)} | partial failed {kn.get('PARTIAL failed', 0)}"
      f" | no-play downs made snaps {kn.get('no-play downs made snaps', 0)} | v18: 1214 of 37112 (0.0327), 14, 22" if st_ else "the record: 0 stamped stopped stretches checked")
print(f"TEST clock_check.py {sh('clock_check.py')}: {'PASS' if not FAILED else 'FAIL'} | failed: {FAILED if FAILED else 'none'} | {time.time() - T0:.0f} s")
sys.exit(1 if FAILED else 0)
