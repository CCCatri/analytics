# demo_w15 fixtures - origins

The smallest input set with which a clean checkout issues the 2024 week 15 engine-mode card (measured 2026-11-06 by recording every file the card opened).

| file | origin | role |
|---|---|---|
| `atlas.csv`, `ladder.csv` | slate kit replay output, 2026-11-05 (run 20261105_220733: produced by the pre-adapter code in `baseline/kit_pre`, byte-identical to the candidate's) | the card's grading basis (`cards.py:65-66`); labelled kit baseline evidence on engine-mode cards |
| `injuries_2019.csv` ... `injuries_2024.csv` (2019, 2020, 2021, 2023, 2024) | nflverse injuries data as held in `data/raw`, retrieved by `slate-kit/ingest.py`; copied here unchanged | the participation law's fit rows (`participation.py`: P(plays) for each candidate) |
| `out/handoff/root_draws_2024_w15.npz` + manifest (tracked separately) | engine output, `product/handoff_root_draws.py 2024 15 30` | the engine root draws the kit consumes in engine mode |
| `slate-kit/facts/` (tracked separately) | built by `facts.py` from the raw play-by-play; content-identical rebuild verified 2026-11-05 | every player's history the kit draws from |

SHA-256 of each file is in `PINS.json`; `checks/demo_w15.py` refuses if any moved. The raw play-by-play (45 files, pinned in the engine's RAW_PIN) is NOT needed for this demo and is not in the tree.

Redistribution: nflverse publishes its data releases under a permissive license (CC BY 4.0 to the best of this record's knowledge); confirm against the nflverse-data release page before the repository is made public, and keep the attribution line. The atlas, ladder and engine fixture are this project's own outputs.
