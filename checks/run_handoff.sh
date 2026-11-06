#!/bin/zsh
# One command for the handoff adapter evidence under a fresh run id in out/handoff/runs/: the pre-adapter baseline (isolated replay + card, ~10 min), the component
# checks (~3 min), the candidate's isolated paired replay (~8 min), then the final verdict. Readable results: <run>/baseline/RESULT.txt, <run>/components/RESULT.txt,
# <run>/replay/A2.txt, <run>/VERDICT.txt; full logs and record.json beside each. The shell result is the final verifier's exit status.
cd "$(dirname "$0")/.." || exit 1
RUN="out/handoff/runs/$(date +%Y%m%d_%H%M%S)"; mkdir -p "$RUN" || exit 1
export HANDOFF_RUN_DIR="$PWD/$RUN" PYTHONDONTWRITEBYTECODE=1
echo "run $RUN"
python3 -u checks/test_handoff_baseline.py; echo "baseline exit $?"
python3 -u checks/test_handoff_adapter.py;  echo "components exit $?"
python3 -u checks/test_handoff_replay.py;   echo "replay exit $?"
python3 -u checks/test_handoff_final.py; FINAL=$?; echo "final exit $FINAL"
echo "results: $RUN/baseline/RESULT.txt  $RUN/components/RESULT.txt  $RUN/replay/A2.txt  $RUN/VERDICT.txt"
exit $FINAL
