"""Incident suite baseline, exact. Reads the two logs run.sh stage 3 just wrote. Revision 12 must report 0 failures; revision 16 must report exactly the two known defects (a missing sample_gain() argument; the end-to-end assertion with gain_sack INSUFFICIENT_DATA) and PASS the predecessor-index oracle. A missing log, a log with no 'N failures:' summary line, a new failure, or a known failure that vanished -> FAIL (exit 1)."""
import ast, os, re, sys
KNOWN16 = ["model: preflight refuses a nan covariate and an out-of-range index by row; typed fit results; the passer sub_model with no informative risk set is FIT_OK as its declared prior; other starved fits are INSUFFICIENT_DATA",
           "end to end: every sub_model estimated on the league prices a slate through the simulator with every identity at zero"]
def failures(path, name):
    if not os.path.exists(path):
        print(f"incident baseline: {name}: {path} missing -> FAIL"); sys.exit(1)
    txt = open(path).read()
    m = re.search(r"^(\d+) failures: (\[.*\])$", txt, re.M)
    if not m:
        print(f"incident baseline: {name}: no 'N failures:' summary line in {path} (run incomplete) -> FAIL"); sys.exit(1)
    n, names = int(m.group(1)), ast.literal_eval(m.group(2)); fail_lines = len(re.findall(r"^FAIL ", txt, re.M))
    if n != len(names) or n != fail_lines:
        print(f"incident baseline: {name}: summary says {n}, list holds {len(names)}, FAIL lines {fail_lines} -> FAIL"); sys.exit(1)
    return names, txt
f12, t12 = failures("out_revision12.log", "revision 12"); f16, t16 = failures("out_revision16.log", "revision 16")
new16 = [f for f in f16 if f not in KNOWN16]; gone16 = [k for k in KNOWN16 if k not in f16]
ok = f12 == [] and new16 == [] and gone16 == [] and bool(re.search(r"^PASS oracle:", t16, re.M))
print(f"incident baseline: revision 12 failures {len(f12)} (expected 0) | revision 16 failures {len(f16)} (expected the 2 known) | new {new16} | vanished {gone16} | oracle PASS {bool(re.search(r'^PASS oracle:', t16, re.M))} -> {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
