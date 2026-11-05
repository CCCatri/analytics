# Candidate engine v38, full run (2026-10-31): the pinned evidence behind the refusal

What this is: one full run of the chain script on all 1,676 games of 2019–2021 and 2023–2025, with every input pinned by sha before the run, five predictions written before the run, seventeen quality gates, and one decision. The decision was NOT ACCEPTED. The files here are the run's own, byte-for-byte (the manifest's shas check against them); only the file names are the portfolio's.

## Decision

NOT ACCEPTED. Plays per game 136.77 against the record's 136.73 (inside 2SE, prediction held); refused on the engine-legality stage's section 4 (the downs check UNCHECKED), on the fourth-and-1 go share above the accepted engine's at every field zone, and on unsupported continuations drawn in 648 of 1,676 games. Full line: manifest.json → results.line.

## Predictions written before the run (manifest.json → results.predictions)

| Prediction | Held |
|---|---|
| 4th-and-1 shares a bin with 2–3 at the first levels (a read) | yes |
| After the change, the 4th-and-1 go share within 2SE in 4 of 5 zones above the 11–20, and in the 11–20 | no |
| The same for 4th-and-2–3 | no |
| The punt share's part of the punt gap below 0.2 | no |
| Plays per game within 2SE of the record's 136.73 | yes |

## Inputs pinned before the run (manifest.json → inputs)

| Portfolio file | Name in the run | sha (first 12) |
|---|---|---|
| product/check_possessions.py | r1.py | 684d8fed2311 |
| product/check_clock.py | r2.py | 567e8946b4e0 |
| product/check_downs.py | r4.py | 8532a090b885 |
| product/record.py | record.py | a18b89fe7985 |
| product/policy.py | contract.py | c141f8d3086a |
| product/measure_season_rules.py | r7.py | 944aef150c1b |
| product/rules_level.py | l0.py | ede0aef941c2 |
| product/engine.py | e1.py | 4f28bf6aa3cc |
| product/rules.py | rules.py | 3d9b5a3b1985 |
| product/transition.py | transition.py | fcca26b4997f |
| product/clock_check.py | clock_check.py | 981facf94d61 |
| checks/test_transition.py | test_transition.py | d47712aa9faa |
| out/season_rules.csv | out/r7_seasons.csv | 1d3606b8c099 |
| out/engine_checks.csv | out/e1_checks.csv | f54577bfd3be |
| out/sim_games.csv (not shipped, 73 MB) | out/sim_games.csv | d3d2dd1303de |
| out/engine/MANIFEST.json (model files, not shipped) | same | c539a85289bc |
| rules/RULE_PINS.json, play_clock_pins.tsv, warning_pins.tsv | same | ca8b1060e3aa, 5b83ab1dda95, 3dc29875f627 |
| acceptance-criteria/PROGRESS.md | PROGRESS.md | 811fddf2ab32 |
| acceptance-criteria/engine-vs-record.md (a later revision; the pinned text is not kept) | E2_TARGETS.md | 165d9321da35 |

The product files have since been renamed and re-pinned to the renamed criteria (git history shows the wording-only diffs), so their current shas differ from these; the copies under code/ are the pinned ones.

## Files

- manifest.json: the run's record as written (inputs, predictions, quality gates, timings, versions).
- printout.txt: the run's full printed output (508 KB); its section codes (ai1, ah2, y0 …) are named in full where each section starts.
- code/: the chain script (chain_script_v38.py, sha 7f5379dd7ce2) and the product files as they ran, renamed to the portfolio's names, contents unchanged.
