#!/bin/bash
export PYTHONDONTWRITEBYTECODE=1
# One command. Each stage prints PASS, FAIL or SKIPPED with its reason; nothing is hidden by an early exit.
cd "$(dirname "$0")"; export PYTHONPATH=product
stage() { echo ""; echo "== $1"; }
stage "1. construction tests (transition, clock)"
for f in checks/test_transition.py checks/test_clock_check.py; do python3 $f 2>&1 | grep -E "FAIL|TEST|EXPECT|cases|events"; done
stage "2. rule grounding: each season's rule found in its pinned book, else UNKNOWN"
python3 - <<'PY'
import rules
for s in (2020, 2021, 2023, 2024, 2025):
    x = rules.season_x6(s)
    bad = [k for k, c in x.items() if c["value"] == "UNKNOWN"]
    print(f"{s}: {len(x)} rules, UNKNOWN {len(bad)} {bad}")
PY
stage "3. incident the predecessor-index mismatch: revision 12 (before the oracle) and revision 16 (injected 0-based predecessor refused)"
( cd incidents/predecessor-index-mismatch/revision-12-fix-without-regression-test && python3 tests/test_product.py > ../../../out_revision12.log 2>&1; echo "  revision 12 exit $?"; grep -E '^(PASS|FAIL)|failures|Error' ../../../out_revision12.log | sed 's/^/  revision 12 /' )
( cd incidents/predecessor-index-mismatch/revision-16-with-regression-test && python3 tests/test_product.py > ../../../out_revision16.log 2>&1; echo "  revision 16 exit $?"; grep -E 'oracle|failures|Error' ../../../out_revision16.log | sed 's/^/  revision 16 /' )
stage "4. the pinned evidence run: predictions written before the run, and the decision"
python3 - <<'PY'
import json; m = json.load(open("evidence/candidate-engine-v38-full-run/manifest.json")); r = m["results"]
print("inputs pinned:", len(m["inputs"]), "| status:", m["status"])
for k, v in r["predictions"].items(): print(f"  prediction {'held ' if v else 'FAILED'}: {k}")
for k, v in r["gates"].items(): print(f"  quality gate {'true ' if v else 'FALSE'}: {k}")
print("  plays", round(r["plays"], 2), "possessions", round(r["possessions"], 2), "points", round(r["points"], 2))
print("  decision:", r["line"].split("|")[2].strip())
PY
stage "5. record checks and the engine (need the nflverse raw files; see README)"
if [[ -d data/raw ]]; then python3 product/check_possessions.py && python3 product/check_clock.py && python3 product/check_downs.py && PYTHONPATH=product python3 -c "import sys, engine; engine.alone_main(sys.argv[1:])" out/engine out/engine_alone; else echo "SKIPPED: data/raw absent"; fi
