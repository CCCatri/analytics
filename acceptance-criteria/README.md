# acceptance-criteria/ — the reference layer; some files are pinned by code

| file | role | pinned? |
|---|---|---|
| `clock-check.md` | the clock record check's criteria | yes — `product/check_clock.py` pins v16 (`dfff5f9d7de8`); do not edit without `repin` |
| `downs-check.md` | the downs record check's criteria | yes — `product/check_downs.py` pins v19 (`7c579decd785`) |
| `rules-module.md`, `rules-level.md` | the rules module and the rules sentence | read by `measure_season_rules.py` / `rules_level.py` |
| `PROGRESS.md` | status, and the template line `rules_level.py` reads its words from | read by code — not a free-form status page |
| `engine-legality.md` | engine v0 acceptance: every generated game obeys the rules; quality gate 1 results | cited by the checks |
| `engine-vs-record.md` | the engine against the record; NOT ACCEPTED on plays per game | cited |
| `engine-to-kit-handoff.md` | the one interface between engine and kit; section 6 is the integration check | cited |
| `forward-window.md` | the forecast-value test, design only, project owner's rulings blank | — |

Readers start at `README.md` and `cases/`; this directory is what those point back to.
