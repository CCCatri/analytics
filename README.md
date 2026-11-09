# analytics

[![demo](https://github.com/CCCatri/analytics/actions/workflows/demo.yml/badge.svg)](https://github.com/CCCatri/analytics/actions/workflows/demo.yml) — `checks/demo_w15.py` run on a clean Ubuntu runner on every push: dependencies from `requirements.txt`, fixtures from the tree, the Week 15 trace and controlled change reproduced.

## The result

With AI agents, I own the requirements, acceptance criteria and test strategy, and I rule on what ships; the agents write the code.

One saved simulated game was changed by hand: Las Vegas's pass attempts in engine draw 0 raised from **36 to 60**. The slate kit's projection for Desmond Ridder's attempts moved from **6 to 10** at the traced column; all 67 kit columns mapped to that draw moved and none of the others did, in his attempt calculation and in the team root. With the adapter switched off, the kit is unchanged against its own pre-adapter code (card equal; 192,330 and 26,722 graded rows equal by key and value). Saved verdicts: [`cases/evidence/`](cases/evidence/). The engine's simulated team volume reaches a named player's projection; whether that improves the forecast is a separate, unrun test (`acceptance-criteria/forward-window.md`).

Two ways to see it: the **short demo** (`python3 checks/demo_w15.py`, clean checkout, saved engine output) reproduces the trace and the controlled change; the **full replay** (`checks/run_handoff.sh`, needs the raw files and the saved pre-adapter kit) regenerates the upstream evidence and the switch-off comparison.

Each document has one job: `README.md` directs; `cases/` explain decisions; `acceptance-criteria/` define acceptance; `checks/` produce verdicts; each directory's `README.md` says what its files are and what reads them.


## Start here

The directories, in one line each: `cases/` the stories and their saved evidence · `checks/` every check and the one-command demo · `product/` the engine · `slate-kit/` the player-projection component · `acceptance-criteria/` the reference layer (some files pinned by code) · `out/` stamped outputs the product reads back and the Week 15 fixture · `rules/` the pinned rule books · `incidents/` the two revision snapshots behind the regression case · `WORK_ORDER.md` what remains open. Each directory has a README saying what writes and reads it.

The lead case is [From a simulated game to a player projection](cases/from-a-simulated-game-to-a-player-projection.md): what the engine and the slate kit each do, where they meet, what the join had to preserve, and what one combined run produced (run `20261107_153255`, PASS; evidence under `cases/evidence/`). Everything below is a part of that case:

- the engine's acceptance criteria and their limits: `acceptance-criteria/engine-vs-record.md`, `engine-legality.md`, `rules-level.md`, `PROGRESS.md`
- the handoff and its quality gates: `acceptance-criteria/engine-to-kit-handoff.md` (section 6 is the integration check the lead case reports)
- the three earlier cases, each one part of the lead case: `cases/clock-check-passed-a-corrupted-game.md`, `cases/regression-test-needed-data-that-could-trigger-the-bug.md`, `cases/two-components-had-to-agree-on-what-counts-as-an-attempt.md`
- the sentences the résumé and this repository both copy from, one row per responsibility: `CLAIMS.md` (checked by `checks/check_claims.py`)
- the two ways to verify it, below
- the fields that carry the claim, and every column on disk: `DATA.md`
- what remains open, as a work order with done-criteria: `WORK_ORDER.md`
- the test that would decide whether the join forecasts better, designed and frozen before any outcome is read, not yet run: `acceptance-criteria/forward-window.md`

### Two ways to verify

**The short demo — from a clean checkout.** `python3 checks/demo_w15.py` starts from saved engine output (the 2024 week 15 root draws, tracked) and reproduces how that output reaches a player projection: the engine-mode card with its provenance line, the trace (kit columns 29/30/31 = engine draws 29/0/1 for both teams of ATL at LV; the LV quarterback's attempts cell receiving the team root), the controlled change (LV draw 0 raised 36 → 60; the 67 mapped columns move and nothing else; his drawn attempts at that column move), and one broken input refused by name. Prerequisites: Python 3 and the packages in `requirements.txt` (numpy, pandas, scipy), nothing else — the fixtures are in `checks/fixtures/demo_w15/` (origins and hashes in `ORIGINS.md`); no raw play-by-play. Output: `out/demo_w15/<stamp>/RESULT.txt`; exit status agrees with the verdict.

**The full run — on a machine that holds the inputs.** `checks/run_handoff.sh` regenerates the upstream evidence: a baseline from the saved pre-adapter kit code in an isolated copy (replay and card), the component checks, the candidate's isolated paired replay, and a final verdict from the three records. Prerequisites beyond the short demo: the raw play-by-play files under `data/raw` (pinned by the engine), the kit's `proj/` state, and the saved pre-adapter `draws.py`/`cards.py`. Its latest result is in `cases/evidence/handoff_20261107_153255/` (PASS, 2026-11-07); the earlier `handoff_20261105_220733/` (PASS) also keeps the `20261105_210053` FAIL that preceded it.


## The goal

"Every game is 60 minutes; the ball changes hands after every score or stop; four downs to gain ten. This game should have about P plays between both teams, more or fewer than these teams' usual, because ___." The goal, in my words from Oct 24: "find the goal for each layer, how the layers work together to accomplish the final product, against real NFL rule conservation. For each thing that looks like it's mostly chance, go a layer deeper and see what it's composed of. If we can eliminate the noise, like ensuring apples to apples for player health, and they all rest on the same rolling average, it makes it a lot easier to find where the variance is; then we can make progressively more complex by adding in one variable at a time." Not a player's over/under price. Not a score or winner pick.

## What it demonstrates

Cases a reviewer can read on their own: `cases/clock-check-passed-a-corrupted-game.md` (a passing check gave an incomplete answer; the stopped-clock check caught the injected fault) · `cases/regression-test-needed-data-that-could-trigger-the-bug.md` (twelve tests passed for eight revisions on a fixture that could not express the fault) · `cases/two-components-had-to-agree-on-what-counts-as-an-attempt.md` (467 disagreeing team-games traced to a definition, then 0 of 3,200).

| Practice here | Industry term | Where |
|---|---|---|
| Acceptance criteria written before code, with expected counts; outcomes recorded whether they held or not | Pre-registration, prediction logging | `acceptance-criteria/clock-check.md` line 72 (FASTER counts expected before the run, met in all six seasons today); `acceptance-criteria/downs-check.md` (OTHER expected 0, met) |
| A check counts only after its injected fault fails | Fault injection, mutation testing, negative controls | `run.sh` stage 1 (11 injected faults in `checks/test_transition.py`) and stage 4 (24, 21 and 46 in the three record checks), each failing as it must before a count is read; `incidents/.../revision-16-with-regression-test` oracle |
| ACCEPTED / NOT ACCEPTED with named reasons; UNKNOWN printed where a check has no power | Fail-closed quality gates, abstention | revision 16 `quality_gate.py` (PASSED / FAILED_REQUIREMENTS / INSUFFICIENT / STOPPED / CRASHED, run by stage 3); the play-by-play record checks refuse at a changed criteria sha or raw-file pin before reading a count |
| Every read pins its inputs by hash | Provenance, reproducibility | `product/RAW_PINS.json` (45 raw files), the criteria sha in each record check, `out/engine/MANIFEST.json` checked file by file when the engine loads (stage 4) |
| A rule is a sentence found in its pinned source document, or it reads UNKNOWN | Citation grounding | `product/rules.py` `season_rule_quotes`, `find_quote`; `rules/RULE_PINS.json` |
| The 2022 season refused at every read; earlier iterations had tested against it and their records were deleted on 2026-10-26, so it certifies nothing (the version-4 plan of that date) | Leakage control, temporal holdout | `product/record.py` `held_out()`; revision 16 tests `boundary` and `quality_gate: hold-out access is tracked by dataset identity` (stage 3) |
| An incident becomes a rule, with the row that caused it | Regression from incident | `incidents/predecessor-index-mismatch/incident-derived-rules.md`; `checks/fixtures/regression_cases.csv` (9 cases) |

## Run it

    bash run.sh

Stages 1–3 run from a clone. Stage 4 needs the nflverse raw files (play-by-play, schedule, rosters, participation, 2019–2025); their hashes are in `product/RAW_PINS.json` and a file whose hash differs is refused.

## Current state

The accepted engine plays 126.99 plays a game against the play-by-play record's 136.73. On 2026-10-31 a candidate engine played 136.77 and was **not accepted**: one engine-legality section-4 item read UNCHECKED instead of 0, the fourth-and-1 prediction failed in most field zones, and 648 of 1,676 games drew a continuation the engine does not support; 3 of its 5 pre-registered predictions failed. The headline number matched and the candidate was refused on its own checks. That run's printout and manifest are not kept: they were written in the project's earlier vocabulary and the run cannot be regenerated here without rebuilding the experiment against different inputs, so the refusal stands as this dated summary and its evidence is lost. Separately, `run.sh` stage 5 (2026-11-05) is a new demonstration on the accepted engine: the same checks on its generated games, with four injected rule violations each rejected on its own line. It does not reproduce the Oct 31 refusal.

My rule, stated Oct 2026 and applied here: the game-level quality gate judges the totals, never whether a change is accepted; an accepted change later found wrong is corrected by another acceptance, never held back for fear of it.

## Checks that lapsed

Each version of this project rewrote the product and the checks together. These checks existed and are not in the current code:

| Check | Last ran in | Where it is recorded |
|---|---|---|
| Schedule vs play-by-play agreement (`games_cross_check`) | version 3 revision 16, Oct 23 | `incidents/predecessor-index-mismatch/revision-16-with-regression-test/record.py` |
| Snap-count reconciliation with an injected +1 | version 3 revision 7 | `incidents/predecessor-index-mismatch/revision-12-fix-without-regression-test/record.py` `snaps_cross_check` |
| Twelve offensive players on a snap refused (Rule 5-1-1) | version 3 revision 16 | `incidents/predecessor-index-mismatch/revision-16-with-regression-test/record.py` `participation` |
| Synthetic league with season chains and the predecessor oracle | version 3 revision 13–16 | `incidents/predecessor-index-mismatch/revision-16-with-regression-test/tests/` |

My working rule of Oct 26 (in `acceptance-criteria/PROGRESS.md`): history is deleted, not kept; only files a live script reads stay. A check that no live script read went with the version that read it.

## History

Four versions in October 2026. Earlier NFL analysis from Sep 2025 is not in this repository. Only `main` is defined in all four; the play-by-play record reader was rewritten three times and improved each time, and the checks around it were rewritten three times and did not accumulate (the table above). `incidents/predecessor-index-mismatch/INCIDENT.md` is the one incident written up in full.

| Version | Dates | What it was | Why it ended | What carried forward |
|---|---|---|---|---|
| 1 | Oct 12–16 | worlds drawn as real past games; a player's stat the sum of plays credited to him; no number not read from the play-by-play record | the handoff required the checker, grader and record reader to be reused verbatim in a rebuild from the rules; the next version rewrote them | nothing |
| 2 | Oct 17–22 | the grader's charter: it grades and never builds; known-right and known-wrong cases must fail before a decision counts; predictions closed before the run | my questions at the time: whether the acceptances were real in the product files, and whether a gap near the threshold was noise that could flip | the decision vocabulary and predictions-before-the-run, as rules; no code |
| 3 | Oct 22–23 | fitted hierarchical sub-models, a full simulator, a data preflight, the synthetic league with season chains; the predecessor-index incident found and fixed | my decision to order the work as a chain of constraints toward reliability on a held-out season and to define each layer as enforceable code | the reader's function names and credits; the ban on market inputs; the 2022 decision |
| 4 → this repo | Oct 24– | two days of root search, then the Oct 26 reframe: rules first; the three record checks at 0 unexplained become the engine's transition rules and its test | current | |

## What this is not

The engine prices nothing: no player line, no pick, no lineup; market lines and model columns are banned as its inputs (`product/policy.py`). The slate kit in `slate-kit/` is the pricing layer, a separate component with its own entry point; the two are joined only through the handoff described below. Since 2026-11-07 (run `20261107_153255`, PASS) the kit's two team-volume root cells can be drawn from engine output; the one card issued that way (2024 week 15, the demo) is a dry run, and no forecast has been scored from it.

## Tooling

Built with Claude through MCP connectors and the terminal. The agents wrote code against acceptance criteria written first; the checks above are what accepted or refused it.

## Not shipped

The acceptance criteria name out/sim_games.csv, out/interval_table.csv and out/product_lines.csv, outputs of earlier candidate runs that are not kept (73, 140 and 19 MB). Stage 4 writes the engine's games to out/engine_alone/; the model files under out/engine/ (183 MB) are copied in beside the raw files and are not in git.

## Qualifications

- Revision 16 is kept as frozen: two of its own tests fail (`sample_gain` signature; `gain_sack` INSUFFICIENT_DATA on the synthetic league), so its quality gate would refuse at SUITE. The incident regression test (`oracle`) passes. `run.sh` stage 3 expects exactly these two failures.

## Where the engine and the slate kit meet

The slate kit's current historical card: `python3 kit.py card 2025 16`, run from `analytics/slate-kit/`. The public demo is 2024 week 15 (`checks/demo_w15.py`).

### Data partitions the kit reads (the folder names do not say this)
- Fit window: every law fits on seasons <= 2025 (`ingest.FROZEN_THRU`); within it the replay refits at each cutoff s on seasons < s.
- Held in facts (readable, fit on): 2019, 2020, 2021, 2023, 2024, 2025. 2026 is history for an issue inside it, never fit on.
- `data/corpus/discovery/` (readable, not in facts): 2016, 2017, 2018 and **2022**.
- `data/corpus/lockbox/` (2012-2015) and `data/corpus/deep_lockbox/` (1999-2011): held out, read only by a registered judgment; `facts.lockbox_check` refuses a kit module that names them.
- **Divergence to resolve before evaluating the joined forecast on a hold-out window:** the engine holds 2022 out of everything; the kit lists 2022 as readable discovery data. The fixture already exercised the join; the joined forecast must declare one hold-out, and 2022 cannot be both.

### Reconciliation report: where the engine can connect
- Consumer: EXISTING CONSUMER OF DRAWS. The card path is `cards.card -> draws.week_draws -> draws.draw_slate -> draws.draw_link`, one cell at a time in dependency order. The chain's two roots, `("F2 team attempts", TEAM)` and `("F2 team carries", TEAM)`, are the only cells drawn without a parent: `draw_link` returns `rint(center x a bootstrapped ratio)`, 2,000 draws per (season, week, team), keyed by `team`; every other cell draws from its parent's draw, so draw j across all rows is one world. Units: pass attempts with sacks excluded, rush attempts (`facts.py`), whole counts, two-point tries excluded; available at issue from the information set through week N-1. The handoff is an adapter at that one branch (acceptance-criteria/engine-to-kit-handoff.md), not a new layer; the engine also supplies what the kit lists as not modelled: both teams of a game in the same world.
- Scoring evidence: the replay (`proj/replay_report.txt`) is walk-forward inside the fit window - seasons 2020, 2021, 2023, 2024, 2025, 65 slates, 192,330 graded rows - and reads PRODUCT ISSUED against the previous product (QB BETTER at p = .024; RB UNCHANGED; TE, WR and team total UNKNOWN); the two root cells are DECISION-QUALIFIED with CRPSS +0.10 against the season-to-date reference. The separate root quality gate against the batch-56 atlas reads FAIL or UNRESOLVED on all 19 chain cells; participation's walk-forward quality gate recorded FAIL. Cards 2026 w4 and w5 were issued as dry runs; `proj/` holds no forward score for either (0 frozen weeks scored).
- Next code change: (1) DONE 2026-11-05 - the section-1 reconciliation (`checks/reconcile_root_counts_by_position.py`, 3,200 of 3,200 team-games equal); (3) DONE 2026-11-05 - quality gate 1 (`run.sh` stage 5). (2) DONE 2026-11-07 - the `ROOT_SOURCE` switch in `draw_link`'s level branch; adapter off, the replay's paired rows equal by key and value (run `20261107_153255`, PASS). (4) DONE 2026-11-06 - one card traced to an engine draw file by its manifest (`checks/demo_w15.py`, 2024 week 15). Open: the walk-forward comparison (quality gate 2), with the engine refit per cutoff and the hold-out declared (`WORK_ORDER.md` items 2 and 3).

## Product statement (six fields, 2026-11-05)

1. **What it is.** A rules-legal NFL game engine: it plays a game snap by snap from the rule book and league-wide rates and writes it in the play-by-play record's own columns, so the play-by-play record's checks can be run on it unchanged. Beside it, a slate kit that prices players from team volume downward. The engine is the generative core the kit never had; the kit is the layer that would price what the engine generates.
2. **What is demonstrated, and its scope.** The play-by-play record of 2019-2021 and 2023-2025 meets three rule-based acceptance criteria with pre-registered counts (`run.sh` stage 4). The engine's generated games of 2024 week 15 (30 draws) meet the same criteria through the same checks, and four injected violations are each rejected on the named line (stage 5). An incident is replayed with its regression test, the two known failures of its later revision are checked exactly, and a third, measured defect (its estimator's intervals under-cover) is printed, not judged (stage 3). The engine's attempts and carries equal the kit's root definition on 3,200 of 3,200 team-games (`checks/reconcile_root_counts_by_position.py`).
3. **What is not demonstrated.** Any forecast: the engine's fits are look-back (each season reads the five others) and judge legality only; the kit's cards are dry runs with no forward score; the one engine-rooted card (2024 week 15) is a dry run, not a scored slate. The engine plays position placeholders, not named players, so it hands over team volume and nothing finer. The kit's vocabulary is its own, not this repo's.
4. **What was lost.** The Oct 31 candidate's refusal printout and manifest were deleted in the cleanup and cannot be regenerated; that refusal survives only as the dated summary under Current state. Stage 5 is a separate, new demonstration on the accepted engine, not a replacement for that evidence.
5. **Next milestone.** The 2026-11-05 milestone is done as of 2026-11-07: `draws.draw_link`'s root drawn from `out/handoff/root_draws_2024_w15.npz` behind a switch whose off position matched the pre-adapter baseline by key and value in the tested card and replay (run `20261107_153255`), and one card carrying the draw file's manifest (`checks/demo_w15.py`). Next: the walk-forward comparison with the engine refit per cutoff and one declared hold-out (`WORK_ORDER.md` items 2 and 3).
6. **Limits that bind every number here.** 2022 is held out of everything on the engine side and readable on the kit side, unresolved; the plays gap (126.99 vs 136.73 a game) stands; 16 postseason stretches are unchecked; the handoff counts omit attempts and carries on nullified plays (2 of 3,200 team-games on the play-by-play record) because the engine writes no flags on its foul rows.

## Role-to-evidence mapping

`CLAIMS.md` owns this mapping, one row per responsibility, checked by `checks/check_claims.py`; it is not repeated here.
