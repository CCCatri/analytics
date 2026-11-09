"""Incident suite baseline. Reads the two logs run.sh stage 3 just wrote (or the two paths given: revision 12, then revision 16).
The incident's claim (INCIDENT.md F5): revision 16's regression test refuses an injected 0-based predecessor ('PASS oracle:'); revision 12, which has no such test, passes its own suite (0 failures).
Revision 16's defects, left as found:
  known, on every run: the sample_gain() signature; the end-to-end gain_sack INSUFFICIENT_DATA.
  measured: the estimator oracle's unit-state intervals under-cover: mean coverage .921, 2SE .020, over hash orders 0-9 (2026-11-09), with the spread of position effects
  estimated below the truth in 10 of 10. Its single-dataset band (.88-.995) passes or fails by hash order, so its outcome is printed and never judged.
FAIL (exit 1): a missing or incomplete log; revision 12 with any failure; revision 16 without 'PASS oracle:'; a revision-16 failure outside the three named; a known defect that vanished.
--injected-faults: rebuilds the logs with one fault each and requires each verdict (exit 1 if any is misjudged)."""
import ast, os, re, sys

KNOWN16 = [
    "model: preflight refuses a nan covariate and an out-of-range index by row; typed fit results; the passer sub_model with no informative risk set is FIT_OK as its declared prior; other starved fits are INSUFFICIENT_DATA",
    "end to end: every sub_model estimated on the league prices a slate through the simulator with every identity at zero",
]
MEASURED16 = "estimator oracle: on data generated from known spreads and a known chain, the estimates land inside their standard errors and the unit states' conditional intervals cover at nominal; an injected broken chain is not recovered"
ORACLE = "oracle: the league exercises every declared branch; every program's reference arrays round-trip; an injected 0-based predecessor is refused"
SUMMARY = re.compile(r"^(\d+) failures: (\[.*\])$", re.M)


def parse(txt, name):
    m = SUMMARY.search(txt)
    if not m:
        return None, f"{name}: no 'N failures:' summary line (run incomplete)"
    n, names = int(m.group(1)), ast.literal_eval(m.group(2))
    lines = len(re.findall(r"^FAIL ", txt, re.M))
    if n != len(names) or n != lines:
        return None, f"{name}: summary says {n}, list holds {len(names)}, FAIL lines {lines}"
    return names, None


def judge(t12, t16):
    f12, e12 = parse(t12, "revision 12")
    f16, e16 = parse(t16, "revision 16")
    if e12 or e16:
        return False, e12 or e16
    oracle = bool(re.search(r"^PASS oracle:", t16, re.M))
    new = [f for f in f16 if f not in KNOWN16 and f != MEASURED16]
    gone = [k for k in KNOWN16 if k not in f16]
    cov = re.search(r"unit-state 95% coverage (0\.\d+)", t16) or re.search(r"AssertionError: \(np\.float64\((0\.\d+)\)", t16)
    ok = f12 == [] and oracle and not new and not gone
    return ok, (f"revision 12 failures {len(f12)} (expected 0) | revision 16 regression test refuses the injected predecessor: {oracle} | "
                f"known defects present {len(KNOWN16) - len(gone)}/{len(KNOWN16)} | new {new} | vanished {gone} | "
                f"estimator oracle (measured defect, printed not judged): {'FAIL' if MEASURED16 in f16 else 'PASS'}, coverage {cov.group(1) if cov else 'unread'}")


def rebuild(txt, names, oracle_pass=True):
    body = [l for l in txt.splitlines() if not l.startswith("FAIL ") and not SUMMARY.match(l)]
    names = list(names)
    fails = [f"FAIL {n}: injected" for n in names]
    if not oracle_pass:
        body = [("FAIL" + l[4:] if l.startswith("PASS oracle:") else l) for l in body]
        names.append(ORACLE)
    return "\n".join(body + fails + [f"{len(names)} failures: {names!r}"]) + "\n"


def injected_faults(t12, t16):
    k = list(KNOWN16)
    cases = [
        ("IF0 the logs as run", t12, t16, True),
        ("IF1 estimator oracle fails (the measured defect)", t12, rebuild(t16, k + [MEASURED16]), True),
        ("IF2 estimator oracle passes", t12, rebuild(t16, k), True),
        ("IF3 the regression test no longer refuses the injected predecessor", t12, rebuild(t16, k, oracle_pass=False), False),
        ("IF4 a new failure in revision 16", t12, rebuild(t16, k + ["rules: linked passer/receiver credits, laterals, sacks, kneels and spikes"]), False),
        ("IF5 a known defect vanished", t12, rebuild(t16, k[:1]), False),
        ("IF6 revision 12 fails a test", rebuild(t12, ["record: raw rows immutable and credits replay the official tally exactly"]), t16, False),
        ("IF7 revision 16 cut off before its summary", t12, SUMMARY.sub("", t16), False),
    ]
    right = 0
    for name, a, b, want in cases:
        got, line = judge(a, b)
        right += got == want
        print(f"  {name}: judged {'PASS' if got else 'FAIL'}, required {'PASS' if want else 'FAIL'} -> {'OK' if got == want else 'MISJUDGED'} | {line}")
    print(f"incident baseline injected faults: {right}/{len(cases)} judged as required")
    return right == len(cases)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--injected-faults"]
    p12 = args[0] if len(args) > 0 else "out_revision12.log"
    p16 = args[1] if len(args) > 1 else "out_revision16.log"
    for p in (p12, p16):
        if not os.path.exists(p):
            print(f"incident baseline: {p} missing -> FAIL"); sys.exit(1)
    t12, t16 = open(p12).read(), open(p16).read()
    if "--injected-faults" in sys.argv:
        sys.exit(0 if injected_faults(t12, t16) else 1)
    ok, line = judge(t12, t16)
    print(f"incident baseline ({p12}, {p16}): {line} -> {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
