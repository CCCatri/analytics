# Work order — what remains open, from the lead case

Each item is a question a reader of the lead case can still ask; each has a milestone with a done-criterion. Order is top-down: the simulator's own acceptance before the join is judged on forecasts.

| # | Open question (from the lead case) | Milestone | Done when |
|---|---|---|---|
| 1 | Does the simulator get game volume and the relationships between outcomes right? | Engine acceptance (`acceptance-criteria/engine-vs-record.md`) | Plays per game inside the stated criterion (today 126.99 generated vs 136.73 recorded) or the gap explained and declared; real spreads of plays, possessions, scores and shares reproduced, and shuffled matchups flattening them. |
| 2 | Do the joined forecasts improve, and do the kit's selections beat the field? | Forward window (`acceptance-criteria/forward-window.md`), then a scored selection layer | The four project owner's rulings filled before kickoff of the first eligible slate; paired forecasts recorded before the games and scored after, same player model, baseline vs engine root, result reported whichever way it goes; then lineup selections scored on the same slates. |
| 3 | Are the seasons comparable, and what is the joined system's hold-out? | Data partitions and hold-out (`README.md` data partitions; handoff criteria) | One declared hold-out for the joined system; the 2022 difference between engine and kit reconciled or declared; era and rule-change effects measured or declared. |

Smaller items, already written where they belong: `raw_pin_sha` None in `checks/handoff_identity.py`; the deleted `nfl4` folder's historical completeness unverified; engine-side vocabulary leftovers; CI, a `pytest` entry point and a reformat of the dense check scripts (credibility, not correctness).
