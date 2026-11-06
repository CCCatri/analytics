# out/ — stamped outputs the product reads back, and the integration fixture

Every file here is written by one script and stamped on its first line with that script's sha; nothing is edited by hand.

| file | written by | read by |
|---|---|---|
| `clock_counts.csv`, `clock_faster.csv`, `clock_over40.csv`, `clock_reasons.csv` | `product/check_clock.py` (the clock record check, to `acceptance-criteria/clock-check.md`) | `clock_reasons.csv` by `product/rules_level.py`; the others cited by the criteria |
| `downs_counts.csv`, `downs_other.csv`, `downs_reasons.csv` | `product/check_downs.py` (downs, to `downs-check.md`) | `downs_reasons.csv` by `rules_level.py` |
| `possessions_possessions.csv`, `possessions_classes.csv` | `product/check_possessions.py` | `possessions_classes.csv` by `rules_level.py` |
| `season_rules.csv` | `product/measure_season_rules.py` (each season's rule from its book in `rules/`) | `product/rules.py`, `product/engine.py` |
| `rules_level.csv` | `product/rules_level.py` (the rules sentence built from the three reads above) | the product line; cited by `PROGRESS.md` |
| `handoff/root_draws_2024_w15.npz` + `.manifest.json` | `product/handoff_root_draws.py 2024 15 30` | the slate kit in engine mode; `checks/demo_w15.py`; the handoff harness |
| `handoff/games_2024_w15.csv.gz` | the same run: the 30 generated games | `run.sh` stage 5 (gate 1) via `checks/check_generated.py` |

Not tracked (regenerated or run output, in `.gitignore`): `handoff/stage/` (the staging directory `check_generated.py` builds from `data/raw`), `handoff/games_2024_w15_P*.csv.gz` (planted-fault games `checks/inject_generated.py` writes each run), `handoff/runs/` (handoff harness runs), `demo_w15/` (demo runs), `engine/`, `engine_alone/`. Saved results that readers need are under `cases/evidence/`.
