"""test_transition.py - transition.py's own test (v18: the foul on a play that stands added). Each check names, before it runs, the output that fails
it; exit 0 only when every check passes.
1. the known-right cases (transition.FIXTURES, each true by the article it names; 35 before v18, 8 for v18 c, 3 for v19 part 2, 2 for v19 r, 2 for v19 s, 3 for v19 t; v17's case
   'the enforced spot off the field' now reads half the distance by v19 r2) and the yards cases (YARD_CASES: a foul's yards by its article from its spot):
   FAILS if any case comes back other than it must.
2. the plants (transition.PLANTS, STAND_PLANTS, YARD_PLANTS): FAILS if a plant makes no case fail (the cases could not see that line).
3. byte-identical to the chain's copy (chain e2b_v17_1725d9c82df1's library, lib sha c1357bc133c2): the same known-right cases, and a fixed grid of
   generated events (seeded) through after(), after_one() and second(), and tb_rules over the seasons' X6 cells: FAILS on any answer that differs,
   or if a planted change to the first-down line (7-3-1(a)) differs on no event (the comparison blind). The events carry no foul on a play that stands:
   every answer outside v18 c's case must be the chain's, except v19 r2's: where the chain's answer is 'the enforced spot outside the field (UNKNOWN)'
   for a distance foul toward the fouling team's goal, this file's must be half the distance from the spot to that goal (counted apart, each checked).
4. v18 c on generated events with a foul on a play that stands: every answer either UNKNOWN with its reason, or the ball at the play's end less
   (the defense's foul) or plus (the offense's) penalty_yards (half the distance to the fouling team's goal where that would reach or pass it, v19 r2),
   the offense the same team or, after a loss of down past 4th down, the other. FAILS on any other."""
import ast, hashlib, importlib, inspect, os, random, sys, tempfile, time
import rules
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


print(f"test_transition.py {sh('test_transition.py')} | transition.py {sh('transition.py')}")
print("EXPECT: 1. 53 known-right cases and 10 yards cases, 0 fail | 2. each of 11 plants fails at least 1 case | 3. 0 answers differ from the chain's copy outside v19 r2's case (its 35 cases but the one v19 r2 changes, 200,000 generated events, the seasons' tb_rules); every v19 r2 answer half the distance; the comparison's plant differs on at least 1 event | 4. 0 of 100,000 stand answers off the rule")
import transition as T

print("1. the known-right cases (FAILS: any case returning other than it must)")
n_, bad_ = T.run_fixtures(T.after)
for b_ in bad_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")
check("known-right cases", n_ == 53 and not bad_, f"{n_} cases, {len(bad_)} failed")
ny_, bady_ = T.run_yard_cases()
for b_ in bady_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")
check("yards cases", ny_ == 10 and not bady_, f"{ny_} cases, {len(bady_)} failed")

print("2. the plants (FAILS: a plant that makes no case fail)")
SRC = inspect.getsource(T.after_one)
for nm_, (o_, w_) in T.PLANTS.items():
    _, bp_ = T.run_fixtures(T.planted(SRC, o_, w_))
    check(f"plant, {nm_}", bool(bp_), f"{len(bp_)} of {n_} cases fail")
for nm_, (o_, w_) in T.STAND_PLANTS.items():
    _, bp_ = T.run_fixtures(T.planted_stand(o_, w_))
    check(f"plant, {nm_}", bool(bp_), f"{len(bp_)} of {n_} cases fail")
for nm_, (fn_, f_) in T.YARD_PLANTS.items():
    _, bp_ = T.run_yard_cases({fn_: f_})
    check(f"plant, {nm_}", bool(bp_), f"{len(bp_)} of {ny_} yards cases fail")

print("3. byte-identical to the chain's copy (FAILS: any answer that differs)")
L = chain_lib()
R2_CASE = "a foul during the play, the enforced spot off the field"   # v17's case v19 r2 changes (UNKNOWN -> half the distance)
dcase_ = [L.FIXTURES[k_][0] for k_ in range(min(35, len(L.FIXTURES))) if repr(T.FIXTURES[k_]) != repr(L.FIXTURES[k_])]
check("the first 35 known-right cases are the chain's, but the one v19 r2 changes", len(L.FIXTURES) == 35 and dcase_ == [R2_CASE], f"35 here, {len(L.FIXTURES)} in the chain; differing {dcase_}")
rng = random.Random(0)
TEAMS = ["AAA", "BBB", None]; NUMS = [None, -12.0, -3.0, 0.0, 1.0, 2.0, 4.0, 5.0, 9.0, 10.0, 15.0, 20.0, 35.0, 50.0, 62.0, 75.0, 95.0, 99.0, 100.0, 120.0]
RBS = [T._RB, T._RB2, dict(T._RB, scrim=None), dict(T._RB, dead_counts=False), dict(T._RB, double_replay=False), dict(T._RB2, kick=None, kick_lz=None), {}]
KINDS = ["period start", "try", "kickoff", "snap", "punt", "field_goal", "foul"]
OUTCOMES = list(__import__("rules").NEXT_DOWN)
pick = lambda xs: xs[rng.randrange(len(xs))]


def gen():
    st = dict(off=pick(TEAMS), dfn=pick(TEAMS), down=pick([None, 1, 2, 3, 4]), togo=pick(NUMS), yl=pick(NUMS))
    ev = dict(kind=pick(KINDS))
    for k_, xs in (("receiver", TEAMS), ("team", TEAMS), ("other", TEAMS), ("recv", TEAMS), ("kicker", TEAMS), ("scorer", TEAMS), ("rec_by", TEAMS), ("turn_team", TEAMS),
                   ("poss_after", TEAMS), ("by", ["offense", "defense", None]), ("outcome", OUTCOMES), ("tb_cond", [None, "in the air", "landing zone"]),
                   ("turnover", [None, None, "interception", "fumble"]), ("gain", NUMS), ("yards", NUMS), ("end", NUMS), ("turn_end", NUMS)):
        if rng.random() < 0.5: ev[k_] = pick(xs)
    for k_ in ("td", "made", "safety", "offsetting", "offsetting_dead", "foul_unread", "tb", "turn_tb"):
        if rng.random() < 0.25: ev[k_] = rng.random() < 0.5
    return st, ev, pick(RBS)


def ans(f, *a):
    try: return repr(f(*a))
    except Exception as ex_: return f"raised {type(ex_).__name__}: {ex_}"


OUTSIDE = "a foul: the enforced spot outside the field (UNKNOWN)"


def r2_ok(st, ev, a_new, a_old):
    """v19 r2's change, checked from the article by hand: the chain's answer UNKNOWN for the enforced spot outside the field, a distance foul (yards > 0)
    toward the fouling team's goal from a spot on the field, and this file's answer the ball half the distance to that goal (or 100 less it after a
    turnover on downs)."""
    if OUTSIDE not in a_old or ev.get("kind") != "foul" or ev.get("offsetting") or ev.get("by") not in ("offense", "defense"): return False
    yl, yd = st.get("yl"), ev.get("yards")
    if yl is None or yd is None or not (0 < yl < 100) or yd <= 0: return False
    want = yl + (100 - yl) / 2 if ev["by"] == "offense" else yl / 2
    return f"'yl': {want!r}" in a_new or f"'yl': {100 - want!r}" in a_new


N = 200_000; diff_ = []; pdiff_ = 0; r2_n = 0
P_AFTER = T.planted(SRC, "    if end <= yl - togo:", "    if end < yl - togo:")   # the comparison's own plant: a first down needing one yard more (7-3-1(a))
for _ in range(N):
    st, ev, rb = gen()
    pdiff_ += ans(P_AFTER, st, ev, rb) != ans(L.after, st, ev, rb)
    a1n, a1o = ans(T.after_one, st, ev, rb), ans(L.after_one, st, ev, rb)
    r2_ = a1n != a1o and r2_ok(st, ev, a1n, a1o)   # v19 r2's change in after_one; after() is second() of it (a later recovery the text names still applies)
    for nm_ in ("after", "after_one"):
        a_new, a_old = (a1n, a1o) if nm_ == "after_one" else (ans(T.after, st, ev, rb), ans(L.after, st, ev, rb))
        if a_new != a_old:
            if r2_ and (nm_ == "after_one" or a_new == ans(T.second, T.after_one(st, ev, rb), ev)): r2_n += 1
            else: diff_.append((nm_, st, ev, rb, a_new, a_old))
    r_ = T.after_one(st, ev, rb) if not ans(T.after_one, st, ev, rb).startswith("raised") else None
    if r_ is not None and ans(T.second, r_, ev) != ans(L.second, r_, ev): diff_.append(("second", st, ev, rb))
for x_ in diff_[:5]: print(f"    DIFFERS: {x_}")
check("generated events through after, after_one and second", not diff_, f"{N} events (seed 0), {len(diff_)} answers differ outside v19 r2's case")
check("v19 r2's answers (the chain's UNKNOWN past a goal line), each half the distance by the article", r2_n > 0, f"{r2_n} answers changed, each checked against the article")
check("the comparison sees a planted change (a first down needing one yard more than 7-3-1(a) says)", pdiff_ > 0, f"{pdiff_} of {N} events differ from the chain's copy")
import e1
X6 = e1.x6_rows(); SC = {s: (20, "Rule 11 Section 6") for s in list(X6)[:3]}
L.configure(SCRIM_TB=SC)
tdiff = [s for s in X6 if repr(T.tb_rules(s, X6[s], SC)) != repr(L.tb_rules(s, X6[s]))]
check("tb_rules over the seasons' X6 cells (e1.x6_rows), Rule 11 Section 6 read for some seasons and not others", not tdiff, f"{len(X6)} seasons, {len(tdiff)} differ")

print("4. v18 c on generated events with a foul on a play that stands (FAILS: an answer neither UNKNOWN nor at the play's end -/+ penalty_yards)")
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
    if not (0 < want_ < 100) and 0 < end_ < 100: want_ = end_ / 2 if by_ == "defense" else end_ + (100 - end_) / 2   # v19 r2: the book's half-the-distance article
    yl_o = o["yl"] if o["off"] == "AAA" else 100 - o["yl"]
    if abs(yl_o - want_) > 1e-9 or o["off"] not in ("AAA", "BBB") or (o["off"] == "BBB" and not o["how"].endswith("(7-3-2a)") and "7-3-2a" not in o["how"]):
        off_rule.append(("placed off the rule", st, ev, o))
for x_ in off_rule[:5]: print(f"    OFF THE RULE: {x_}")
check("a foul on a play that stands, generated", not off_rule and n_res > 0, f"100000 events: resolved {n_res}, UNKNOWN {n_unk}, off the rule {len(off_rule)}")

print(f"TEST transition.py {sh('transition.py')}: {'PASS' if not FAILED else 'FAIL'} | failed: {FAILED if FAILED else 'none'} | {time.time() - T0:.0f} s")
sys.exit(1 if FAILED else 0)
