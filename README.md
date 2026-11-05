# analytics

"Every game is 60 minutes; the ball changes hands after every score or stop; four downs to gain ten. This game should have about P plays between both teams, more or fewer than these teams' usual, because ___." The goal, in my words from Oct 24: "find the goal for each layer, how the layers work together to accomplish the final product, against real NFL rule conservation. For each thing that looks like it's mostly chance, go a layer deeper and see what it's composed of. If we can eliminate the noise, like ensuring apples to apples for player health, and they all rest on the same rolling average, it makes it a lot easier to find where the variance is; then we can make progressively more complex by adding in one variable at a time." Not a player's over/under price. Not a score or winner pick.

## What it demonstrates

| Practice here | Industry term | Where |
|---|---|---|
| Targets written before code, with predictions; outcomes recorded whether they held or not | Pre-registration, prediction logging | `acceptance-criteria/`, `evidence/candidate-engine-v38-full-run/manifest.json` (3 of 5 predictions failed; kept) |
| A check counts only after its injected fault fails | Fault injection, mutation testing, negative controls | `out/engine_checks.csv` P1–P4; `incidents/predecessor-index-mismatch/revision-16-with-regression-test` oracle |
| ACCEPTED / NOT ACCEPTED with named reasons; UNKNOWN printed where a check has no power | Fail-closed gating, abstention | `evidence/candidate-engine-v38-full-run/printout.txt`, last 60 lines |
| Every run pins its inputs by hash and freezes the code that ran | Provenance, reproducibility | `evidence/candidate-engine-v38-full-run/` (one of 51 such runs) |
| A rule is a sentence found in its pinned source document, or it reads UNKNOWN | Citation grounding | `product/rules.py` `season_x6`, `find_quote`; `rules/RULE_PINS.json` |
| The 2022 season refused at every read; "2022 certifies nothing: earlier iterations tested against it, their record was deleted 2026-10-26" (version-4 roadmap §5, 2026-10-26, file not kept) | Leakage control, temporal holdout | `product/record.py` `held_out()`; revision 16 tests `boundary` and `quality_gate: hold-out access is tracked by dataset identity` (stage 3) |
| An incident becomes a rule, with the row that caused it | Regression from incident | `policy/incident-derived-rules.md`; `checks/fixtures/regression_cases.csv` (9 cases) |

## Run it

    bash run.sh

Stages 1–4 run from a clone. Stage 5 needs the nflverse raw files (play-by-play, schedule, rosters, participation, 2019–2025); their hashes are in `product/RAW_PINS.json` and a file whose hash differs is refused.

## Current state

The accepted engine plays 126.99 plays a game against the record's 136.73. The v38 candidate in `evidence/candidate-engine-v38-full-run` plays 136.77 and is **not accepted**: one section-4 item reads UNCHECKED instead of 0, the fourth-and-1 prediction failed in most zones, and 648 of 1,676 games drew a continuation the engine does not support. The headline number matched and the candidate was refused on its own checks.

"The game-level gate judges the totals, never the landing. A landed change later found wrong is reverted or corrected by a landing, never held back for fear of it."

## Checks that lapsed

Each version of this project rewrote the product and the checks together. These checks existed and are not in the current code:

| Check | Last ran in | Where it is recorded |
|---|---|---|
| Schedule vs play-by-play agreement (`games_cross_check`) | version 3 revision 16, Oct 23 | `incidents/predecessor-index-mismatch/revision-16-with-regression-test/record.py` |
| Snap-count cross-check with an injected +1 | version 3 revision 7 | `history/version3_RELEASE_REPORT.md` revision 7 |
| Twelve offensive players on a snap refused (Rule 5-1-1) | version 3 revision 16 | `incidents/predecessor-index-mismatch/revision-16-with-regression-test/record.py` `participation` |
| Synthetic league with season chains and the predecessor oracle | version 3 revision 13–16 | `incidents/predecessor-index-mismatch/revision-16-with-regression-test/tests/` |

The working rule written on Oct 26 reads "History is deleted, not kept: no body/ copies; only files a live script reads stay." A check that no live script read went with the version that read it.

## History

Four versions in October 2026; `history/REBUILD.md` has the table. `incidents/predecessor-index-mismatch/INCIDENT.md` is the one incident written up in full.

## What this is not

No price for a player's line, no pick, no lineup. Market lines and model columns are banned as inputs (`product/policy.py`).

## Tooling

Built with Claude through MCP connectors and the terminal. The agents wrote code against acceptance criteria written first; the checks above are what accepted or refused it.

## Not shipped

out/sim_games.csv (73 MB), out/interval_table.csv (140 MB), out/product_lines.csv (19 MB), out/engine/*.pkl and MANIFEST.json are written by stage 5 of run.sh when data/raw is present; the acceptance criteria cite them by those names. The acceptance-criteria and history files name modules and outputs by the names they had when written.

## Qualifications

- Revision 16 is kept as frozen: two of its own tests fail (`sample_gain` signature; `gain_sack` INSUFFICIENT_DATA on the synthetic league), so its quality gate would refuse at SUITE. The incident regression test (`oracle`) passes. `run.sh` stage 3 expects exactly these two failures.
- `evidence/candidate-engine-v38-full-run/manifest.json` names code files and shas as they were when the run was made, before the rename to hiring terms; the renamed copies under `code/` do not hash to those values.
- Stage 5 is skipped without the raw files; the record-check results are the shipped `out/` tables and the engine numbers are the printout's, neither re-verified by a clone run.
- The two `evidence/*.log` files in each revision folder are the Oct 23 printouts the release report cites, kept as written (pre-rename vocabulary); `run.sh` writes today's runs to `out_revision12.log` and `out_revision16.log`.
