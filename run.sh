#!/bin/bash
export PYTHONDONTWRITEBYTECODE=1
set -o pipefail
# One command. Each stage prints PASS, FAIL or SKIPPED with its reason; nothing is hidden by an early exit.
cd "$(dirname "$0")"; export PYTHONPATH=product
stage() { echo ""; echo "== $1"; }
stage "1. construction tests (transition, clock)"
for f in checks/test_transition.py checks/test_clock_check.py; do out=$(python3 $f 2>&1); echo "$out" | grep -E "FAIL|TEST|EXPECT|cases|events"; echo "$out" | grep -q "^TEST .*: PASS" || { echo "FAIL: $f did not print TEST ...: PASS"; exit 1; }; done
stage "2. rule grounding: each season's rule found in its pinned book, else UNKNOWN"
python3 - <<'PY' || exit 1
import rules
for s in (2020, 2021, 2023, 2024, 2025):
    x = rules.season_rule_quotes(s)
    bad = [k for k, c in x.items() if c["value"] == "UNKNOWN"]
    print(f"{s}: {len(x)} rules, UNKNOWN {len(bad)} {bad}")
PY
stage "3. incident the predecessor-index mismatch: revision 12 (before the oracle) and revision 16 (injected 0-based predecessor refused)"
( cd incidents/predecessor-index-mismatch/revision-12-fix-without-regression-test && python3 tests/test_product.py > ../../../out_revision12.log 2>&1; echo "  revision 12 exit $?"; grep -E '^(PASS|FAIL)|failures|Error' ../../../out_revision12.log | sed 's/^/  revision 12 /' )
( cd incidents/predecessor-index-mismatch/revision-16-with-regression-test && python3 tests/test_product.py > ../../../out_revision16.log 2>&1; echo "  revision 16 exit $?"; grep -E 'oracle|failures|Error' ../../../out_revision16.log | sed 's/^/  revision 16 /' )
python3 checks/test_incident_baseline.py || exit 1
stage "4. record checks and the engine (need the nflverse raw files; see README)"
if [[ -d data/raw ]]; then python3 product/check_possessions.py && python3 checks/check_possessions_crosswalk.py && python3 product/check_clock.py && python3 product/check_downs.py && python3 product/rules_level.py && PYTHONPATH=product python3 -c "import sys, engine; engine.alone_main(sys.argv[1:])" out/engine out/engine_alone || { echo "FAIL: stage 4 stopped (a record check or the engine failed above)"; exit 1; }; else echo "SKIPPED: data/raw absent"; fi

echo
echo "== 5. generated-game acceptance (gate 1 of the handoff): the record checks on the engine's generated games, then the four injected violations"
if [ -f out/handoff/games_2024_w15.csv.gz ]; then
  python3 checks/check_generated.py 2024 15 0 | grep -E "^(check_generated|  possessions|  intervals|  game level|  items|  checked|  kickoff touchbacks|  [a-z].*: (PASS|FAIL)|GATE 1)" || exit 1
  python3 checks/test_quality_gate1_injected_faults.py || exit 1
else
  echo "  out/handoff/games_2024_w15.csv.gz missing: run 'PYTHONPATH=product python3 product/handoff_root_draws.py 2024 15 30' first (about 10 minutes); gate 1 NOT RUN"
fi
