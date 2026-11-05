"""test_clock_check.py: clock_check.py's own test. 13 known-right cases, each built by hand from the rule it names: an injury on the play (4-5-3, 4-5-4)
against an 'Injury Update ... returned to the game' announcement; a no-play down (3-8-4) against a charged timeout row (4-5-1) and a foul before the snap;
where the two-minute warning falls (3-41). FAILS: any case returning other than it must.
The comparison against a frozen copy of the version-4 run script on the full record lives in the archive with that script."""
import sys, os, hashlib, inspect, random, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "product"))
T0 = time.time(); FAILED = []
sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
def check(name, ok, detail):
    print(f"  [{time.time() - T0:6.1f} s] {name}: {detail} -> {'PASS' if ok else 'FAIL'}")
    if not ok: FAILED.append(name)
import clock_check as C
print(f"test_clock_check.py {sh(__file__)} | clock_check.py {sh(inspect.getsourcefile(C))}")
print("EXPECT: 13 known-right cases, 0 fail")
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

print(f"TEST clock_check.py: {'PASS' if not FAILED else 'FAIL'} | failed: {FAILED if FAILED else 'none'} | {time.time() - T0:.0f} s")
sys.exit(1 if FAILED else 0)
