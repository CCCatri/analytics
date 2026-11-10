#!/bin/bash
# One script for CI and for a local clean-clone rehearsal: bash checks/ci_verify.sh foundation | card
# foundation: fetch the pinned raw files (fingerprints checked), then the record checks on them.
# card: the demo card and its checks, then the replay against the committed baseline (the last accepted product) and the checks on its outputs.
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.." || exit 1
step() { echo ""; echo "== $1"; }
case "$1" in
foundation)
  step "fetch: the pinned raw files from their public sources"
  python3 checks/fetch_raw.py --self-test || exit 1
  python3 checks/fetch_raw.py || exit 1
  step "the record checks on the pinned files (possessions, nflfastR crosswalk with its injected faults, clock, downs, rules level)"
  export PYTHONPATH=product
  python3 product/check_possessions.py || exit 1
  python3 checks/check_possessions_crosswalk.py || exit 1
  python3 product/check_clock.py || exit 1
  python3 product/check_downs.py || exit 1
  python3 product/rules_level.py || exit 1
  step "the claims the resume copies, and the checks on the checks (catch and false-alarm rates)"
  python3 checks/check_claims.py || exit 1
  PYTHONPATH=product:slate-kit:checks python3 checks/validate_checks.py || exit 1
  ;;
card)
  step "the demo card"
  python3 checks/demo_w15.py || exit 1
  P=$(ls -d out/demo_w15/*/proj | sort | tail -1)
  step "self-tests"
  python3 checks/check_full_game_qb.py --self-test || exit 1
  python3 checks/check_one_game_one_reality.py --self-test || exit 1
  python3 checks/check_full_game_grading.py --self-test || exit 1
  python3 checks/check_dk_dfs_held.py --self-test || exit 1
  step "the card: full-game quarterbacks, one game one reality"
  python3 checks/check_full_game_qb.py "$P/frozen_draws_2024_w15.npz" "$P/card_2024_w15.csv" "$P/team_draws_2024_w15.npz" || exit 1
  python3 checks/check_one_game_one_reality.py "$P/frozen_draws_2024_w15.npz" "$P/card_2024_w15.csv" "$P/team_draws_2024_w15.npz" || exit 1
  step "who starts: walk-forward against P(plays)"
  python3 checks/check_who_starts.py || exit 1
  step "who plays: the law on the final active list"
  python3 checks/check_who_plays_active.py || exit 1
  step "the replay against the committed baseline (the last accepted product)"
  mkdir -p slate-kit/proj
  python3 slate-kit/kit.py replay checks/fixtures/replay_baseline/atlas_rows.csv.gz || exit 1
  step "the replay's outputs: full-game grading, DK DFS held"
  python3 checks/check_full_game_grading.py || exit 1
  python3 checks/check_dk_dfs_held.py "$P/card_2024_w15.csv" || exit 1
  ;;
*) echo "usage: bash checks/ci_verify.sh foundation|card"; exit 2 ;;
esac
echo ""; echo "CI VERIFY $1: PASS"
