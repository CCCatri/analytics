# analytics

**One sentence.** A structural model of one NFL game, read before kickoff: the rulebook fixes what can happen, habits measured from earlier games say what is likely, and the stats fall out of the plays. Every number it reports traces to a measured cause or says it doesn't.

**In my words.** Using open source play by play data from nflfastR, I was able to use raw data from real plays to determine how they are placed on top of the conservation of actual NFL rules to see how different teams performed within the rule set. If a rule had to be violated by the model to create a simulation beyond historical penalties then the model for that iteration failed. Always using honesty as the first class baseline, then tweaking accuracy in future passes. Without having unlimited NFL data available I wanted to be able to find realistic outcomes in each situation to figure out exactly how many times in a simulated game a certain outcome would happen and how that event cascades to overall game performance of other players, then the team, then the other team and the game.. this ultimately led to discovering that a defense is mostly reactive and the offense creates its own game within the game. Each team is playing a separate game against itself.. when a team performs poorly they create a negative compounding feedback loop. This is not for actual betting.

**What it is not.** Not a player's over/under price (an earlier version produced one; it is kept out of this repo as a diagnostic). Not a score or winner pick. Not a cause measured straight to a player's stat line. Earlier iterations of this work (2024–2025) built fantasy lineups from the same numbers; that use is history and is not here.

## Where it stands (Oct 31, 2026)

**The record obeys the rulebook: 0 unexplained.** Three reads of six seasons of play-by-play against the rules as written: possessions (`r1.py`: 36,348 possessions, 1,676 games, unexplained 0), the clock (`r2.py`: 223,724 stretches between snaps), downs (`r4.py`: 328,102 rule checks, 0 OTHER). Each rule cited to its article in the season's book; a plant per check that must fail before the check counts (46 of 46, 24 of 24, 21 of 21). Landed as `out/L0_rules.csv`, 1,719 rows.

**The engine plays games snap by snap on those rules.** Judged against real games it never fit on:

| Measure (v38, Oct 31) | Held | Missed |
|---|---|---|
| Timing cells within 2SE | 25 of 36 (prediction: at least 18) | |
| Pre-snap fouls per game | F1 2.667 vs record 2.694; F2 0.617 vs 0.643, within 2SE | |
| Fouls per second at risk, 2023–2025 | within 2SE each season | |
| Downs wiped by a foul, share marked out of bounds | 0.1000 vs 0.0993 | |
| Fourth-down choice, cells within 2SE | 66 of 102 (prior engine 58, before that 52) | 22 of 48 at the finest grain APART, each named |
| Reviewed plays rebuilt to the next snap | | 0.853 vs 0.918 unreviewed: UNSUPPORTED |
| Timeouts left at each half's end | | within 2SE in 1 of 10 cells |
| Plays, possessions, points per game (engine v0) | | 120.8 / 19.1 / 32.0 vs record 137.5 / 21.7 / 46.1: prediction did not hold |

Progress is counted as marks: 7 levels, 4 marks each, 28 in all; **earned: 1** (the rules in product). The score is printed with its range and never headlined.

**The standing rule, and the incident that made it.** Every check also runs on the record's own games, and its failure rate there prints before its pass on the engine counts, beside its planted fault. It came from one defect: the clock checks read a NumPy true/false that Python never treats as true or false; 15,773 plays and 7,279 foul rows were classed wrong before the check was run on real games and failed 4,982 of 88,023 stretches it had been allowed to fail 0 of. Fixed once; every result read under the defect was kept as history and excluded from measurement; a plant added that a NumPy input at a boundary must fail. It came back once (Oct 31, a read's own code) and was caught by the same rule.

**Banned as inputs:** market lines of any kind, and nflfastR's own model outputs fit on all seasons. One season (2022) is never read by any fit.

## Known defects, read from the code on Nov 3

- Helpers are copied into each script rather than shared: `sha` is defined in 7 files, `load` in 4, `nan` and `one` in 3. One shared module would remove them; the Healix harness refuses this pattern outright.
- `e1.py` is 1,822 lines and about 45 functions: the engine, its binning, its loader and its clock text in one file. It should be three or four.
- Two live files read documents that are not in this repo: `l0.py` takes its template words from `PROGRESS.md`, and `rules.py` reads the 2026 rulebook PDF (the NFL's text, not included). `contract.py` cites `RUBRIC.md`. Neither `l0.py` nor `rules.py` runs from a clone as it stands; the pins and the landed outputs in `out/` are what a reader verifies against.
- The engine's count is short (plays 120.8 vs 137.5 per game) and the record names the cause as open; nothing above L0 is in product.

## How the work is done

Three roles. The owner sets the sentences and rules and is never asked for a ruling a measurement can settle. A builder (an AI agent) writes and runs code, one chain per session; every block pins the files it reads and refuses if they moved, prints its predictions before its numbers, plants first. A falsifier, judging from printouts only, writes the targets before code and the verdict after: LANDED, REARRANGED or PRINTED. A read is honest about what it cannot say: empties are counted, never filled; a rule written from memory is a guess; an explanation written into a prediction is not a cause until it is measured.

## Running it

There is no standalone command in this repo, and the README does not pretend otherwise. `test_clock_check.py` and `test_transition.py` are the harness's own checks: each pins the chain script it verifies by sha and stops if that script is absent, and the chain scripts (one per landing, 300–500 KB each) are kept out of this repo as history. The record reads (`r1.py`, `r2.py`, `r4.py`) and the engine (`e1.py`) read the nflfastR season files (play-by-play, participation, snaps, rosters) pinned in `RAW_PINS.json`; those files are public and not included. `fixtures/real_games.csv.gz` holds 57 real games used for quick runs inside a chain. What a reader can verify here without running anything: every number in this README against `out/`, every rule cited in `targets/` against `rules/RULE_PINS.json`, and every check's planted fault in the targets files.

## Reading this repo

- `ASPIRATIONS.md` — the seven sentences the product is meant to state, with which are measured.
- `targets/` — the acceptance criteria written before each chain's code: checks, plants, predictions, done-when.
- `out/` — the landed product (`L0_rules.csv`) and the record reads' counts and reasons.
- `rules/` — the pins to the rulebook articles (the books themselves are the NFL's; not included).
- `rules.py`, `record.py`, `transition.py`, `clock_check.py` — the rules as code; `r1.py`, `r2.py`, `r4.py`, `r7.py` — the record reads; `l0.py` — the landed product; `e1.py` — the engine; `roots.py`, `contract.py` — the search for causes and the sentence contract.
