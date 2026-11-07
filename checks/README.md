# checks/ — every check the repository makes, and what each proves

- `test_transition.py`, `test_clock_check.py` — the product's own unit checks (each names, before it runs, the output that fails it).
- `test_incident_baseline.py` — `run.sh` stage 3: revision 12 reports exactly its two known failures, revision 16 none.
- `check_generated.py`, `inject_generated.py`, `test_gate1_plants.py` — quality gate 1: generated games against the play-by-play record checks, and four injected violations each caught on the line named before the run.
- `reconcile_root_counts_by_position.py` — the attempt/carry reconciliation (3,200 of 3,200).
- `run_handoff.sh` → `test_handoff_baseline.py`, `test_handoff_adapter.py`, `test_handoff_replay.py`, `test_handoff_final.py`, with `handoff_identity.py` — the adapter harness: a baseline from the saved pre-adapter code, A1/B/B2/C, the isolated paired replay, one verdict per run id.
- `demo_w15.py` — the portable demonstration from a clean checkout (`fixtures/demo_w15/`, origins and pins beside it); `fixtures/regression_cases.csv` serves the unit checks.
- `check_targets_partition.py` — do receiver target draws and quarterback attempt draws fit inside the team attempts draw they were drawn from, game by game; three declared verdicts (supported / refuted / unknown); FAIL until the kit draws group slices jointly; `--self-test` proves it on a conserved slate, a injected independent slate and a missing parent.
