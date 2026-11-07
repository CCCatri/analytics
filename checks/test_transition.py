"""test_transition.py: transition.py's own test. Each check names, before it runs, the output that fails it; exit 0 only when every check passes.
1. the known-right cases (transition.FIXTURES, each true by the article it names) and the yards cases: FAILS if any case comes back other than it must.
2. the injected faults (transition.INJECTED_FAULTS, STAND_INJECTED_FAULTS, YARD_INJECTED_FAULTS): FAILS if a fault makes no case fail (the cases could not see that line).
3. 100,000 generated events with a foul on a play that stands: every answer either UNKNOWN with its reason, or the ball at the play's end less (the
   defense's foul) or plus (the offense's) penalty_yards, half the distance where that would reach the goal; FAILS on any other.
The byte-identity comparison against a frozen copy of the version-4 run script lives in the archive with that script; it needs it and the full record."""
import sys, os, hashlib, inspect, random, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "product"))
T0 = time.time(); FAILED = []
sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
def check(name, ok, detail):
    print(f"  [{time.time() - T0:6.1f} s] {name}: {detail} -> {'PASS' if ok else 'FAIL'}")
    if not ok: FAILED.append(name)
import rules, transition as T
rng = random.Random(0)
print(f"test_transition.py {sh(__file__)} | transition.py {sh(inspect.getsourcefile(T))}")
print("EXPECT: 1. 53 known-right cases and 10 yards cases, 0 fail | 2. each of 11 injected faults fails at least 1 case | 3. 0 of 100,000 stand answers off the rule")
print("1. the known-right cases (FAILS: any case returning other than it must)")
n_, bad_ = T.run_fixtures(T.after)
for b_ in bad_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")
check("known-right cases", n_ == 53 and not bad_, f"{n_} cases, {len(bad_)} failed")
ny_, bady_ = T.run_yard_cases()
for b_ in bady_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")
check("yards cases", ny_ == 10 and not bady_, f"{ny_} cases, {len(bady_)} failed")

print("2. the injected faults (FAILS: an injected fault that makes no case fail)")
SRC = inspect.getsource(T.after_one)
for nm_, (o_, w_) in T.INJECTED_FAULTS.items():
    _, bp_ = T.run_fixtures(T.injected(SRC, o_, w_))
    check(f"injected_fault, {nm_}", bool(bp_), f"{len(bp_)} of {n_} cases fail")
for nm_, (o_, w_) in T.STAND_INJECTED_FAULTS.items():
    _, bp_ = T.run_fixtures(T.injected_fault_stand(o_, w_))
    check(f"injected_fault, {nm_}", bool(bp_), f"{len(bp_)} of {n_} cases fail")
for nm_, (fn_, f_) in T.YARD_INJECTED_FAULTS.items():
    _, bp_ = T.run_yard_cases({fn_: f_})
    check(f"injected_fault, {nm_}", bool(bp_), f"{len(bp_)} of {ny_} yards cases fail")

print("3. generated events with a foul on a play that stands (FAILS: an answer neither UNKNOWN nor at the play's end -/+ penalty_yards)")
NAMES = list(rules.OFF_DURING + rules.LOSS_OF_DOWN + rules.OFF_AFTER + rules.DEF_AWARD) + ["Illegal Use of Hands", "Neutral Zone Infraction", "Unnecessary Roughness"]
off_rule = []; n_res = n_unk = 0
for _ in range(100_000):
    dn_ = rng.choice([1, 2, 3, 4]); yl_ = float(rng.randrange(2, 99)); tg_ = float(min(yl_, rng.choice([1, 3, 5, 10, 15, 22]))); g_ = float(rng.randrange(-10, 40))
    by_ = rng.choice(["offense", "defense"]); yd_ = float(rng.choice([5, 10, 15])); end_ = yl_ - g_
    sp_ = end_ if rng.random() < 0.8 else end_ + rng.choice([-5.0, 5.0])
    st = dict(off="AAA", dfn="BBB", down=dn_, togo=tg_, yl=yl_)
    ev = dict(kind="snap", gain=g_, foul_stand=dict(by=by_, yards=yd_, name=rng.choice(NAMES), award=rng.random() < 0.5, spot=sp_))
    rb = dict(T._RB, dead_counts=rng.random() < 0.8, taunt_dead=rng.random() < 0.5)
    o = T.after(st, ev, rb)
    if o["unk"]:
        n_unk += 1
        if not o["how"].startswith(T.STAND_PREFIX): off_rule.append(("UNKNOWN without the reason", st, ev, o["how"]))
        continue
    n_res += 1; want_ = end_ - yd_ if by_ == "defense" else end_ + yd_
    if not (0 < want_ < 100) and 0 < end_ < 100: want_ = end_ / 2 if by_ == "defense" else end_ + (100 - end_) / 2   # the book's half-the-distance article
    yl_o = o["yl"] if o["off"] == "AAA" else 100 - o["yl"]
    if abs(yl_o - want_) > 1e-9 or o["off"] not in ("AAA", "BBB") or (o["off"] == "BBB" and not o["how"].endswith("(7-3-2a)") and "7-3-2a" not in o["how"]):
        off_rule.append(("placed off the rule", st, ev, o))
for x_ in off_rule[:5]: print(f"    OFF THE RULE: {x_}")
check("a foul on a play that stands, generated", not off_rule and n_res > 0, f"100000 events: resolved {n_res}, UNKNOWN {n_unk}, off the rule {len(off_rule)}")

print(f"TEST transition.py: {'PASS' if not FAILED else 'FAIL'} | failed: {FAILED if FAILED else 'none'} | {time.time() - T0:.0f} s")
sys.exit(1 if FAILED else 0)
