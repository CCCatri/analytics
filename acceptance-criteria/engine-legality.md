# engine-legality.md - engine v0: every simulated game obeys the rules (written before code, 2026-10-26; consolidated 2026-11-05)

## 1. What the engine plays from (no other input)
- rules.py: snap kinds, foul families and their next-down rules, next_down, clock_class and its windows, next_possession, and each season's rules (touchback spot, overtime length and possession rule, onside availability), each quoted from that season's pinned book. 2022 is never simulated (held out).
- League-wide rates for season s from the five other seasons (never s itself, never 2022), a look back used for the legality test only: snap kind; yards by kind; incompletion, sack, interception and fumble-lost rates; fouls by family per chance; 4th-down choice; field goal make rate by distance; punt and kickoff distance and return; onside tries and recoveries; timeouts by situation; real seconds between snaps by clock class. Bins: down, distance (1-3, 4-6, 7-10, 11+), field (own 1-20, 21-50, opp 49-21, opp 20-1), time (normal, last 2:00 of a half, last 5:00 of the game, overtime), score (behind 9+, behind 1-8, tied, ahead 1-8, ahead 9+); bins too thin are merged with the next coarser and the merges print.
- Banned: market lines, nflfastR model columns, anything from the same game or later (PROGRESS.md, banned inputs).

## 2. What it writes
One simulated game for every real game of 2019-2021 and 2023-2025 (same teams, season, week, home side), seed fixed and printed, in the play-by-play record's own columns: every column the three record checks read, play text in the play-by-play record's wording for every foul, score, timeout, two-minute warning and end-of-quarter rows, the game clock, and revision-clock stamps that keep real time no slower than the game clock. run.sh stage 4 writes them to out/engine_alone/.

## 3. Season rules, read from each season's book
Books pinned in rules/RULE_PINS.json by sha (2020, 2021, 2023, 2024 from the Internet Archive's copies of operations.nfl.com; the 2025 changes page; the 2026 book). For each season and each rule the engine plays (postseason and regular-season overtime, the kickoff touchback spot, when an onside kick may be tried), the rule cell quotes the book's sentence and the quote must be found inside its article by the heading finder; a season without its own book cites the nearest book and says so (2019: the 2020 book). The measured value (measure_season_rules.py, out/season_rules.csv) sits beside the rule and never stands in for it. Injected fault: one quoted phrase changed by one word must read 'not found in the article'. Short kicks without 'onside' in their text (2020: 3, 2021: 1) were squibs and are out of the onside rates. A tied playoff game goes to overtime; no playoff game ends tied.

## 4. Acceptance criteria (the play-by-play record checks run on the engine's games unchanged; only the input file differs)
- check_downs.py on the engine's games: OTHER 0, UNCHECKED 0.
- check_possessions.py: unexplained back-to-back 0; every possession ending by a rule class.
- check_clock.py: FASTER not licensed 0; no clock stretch without a class, except postseason periods past the first overtime, counted and printed with their reason.
- The stopped clock, graded on the engine's games: on every STOP stretch the game clock falls by no more than the play's own length plus 1 second, and starts again only at the next snap (4-3, 4-4f); PARTIAL stretches run no longer than the time to the next snap.
- Every game 3,600 seconds of regulation, plus overtime only when tied, by that season's rule.

## 5. Injected faults (each on a changed copy of the engine, then put back; each must FAIL)
P1 after a field goal, the scoring team receives: the possessions check unexplained above 0.
P2 a 5th down allowed: the downs check OTHER above 0.
P3 the game clock kept running after an incomplete pass: the stopped-clock check fails (the clock check alone would pass it: both clocks move together).
P4 2024's touchback spot set to the 25: the season-rule check on the engine's games reads 25, not 30, and fails.

## 6. Printed, not judged
Per season, the engine's mean and spread of plays, possessions and points per game beside the play-by-play record's.

## Status (2026-11-05)
Section 4 and P1-P4 run in run.sh stage 5 (checks/check_generated.py, checks/inject_generated.py, checks/test_gate1_plants.py) on the engine's generated games of 2024 week 15
(out/handoff/games_2024_w15.csv.gz, 30 draws of 16 games). Result: every draw meets section 4 with coverage printed (draw 0: 340 possessions, 0 unexplained; 2,101 clock
stretches all WITHIN REAL TIME, 0 UNCHECKED; 3,104 down items, OTHER 0, UNCHECKED 0, 324 pairs not judged; stopped clock 809 STOP and 299 PARTIAL stretches, 0
violations; 81 kickoff touchbacks all at the quoted 30). Each of P1-P4, injected on a changed copy of the engine made at run time (one function or one season-rule
value replaced, named in the output), turns exactly its own line to FAIL: P1 possessions unexplained; P2 downs OTHER; P3 the stopped-clock check, the clock check
still passing it; P4 the touchback spot read 25 against the quoted 30. The play-by-play record-only sections (pinned record cases, run-log line 322, EXPECTED_FASTER, FROZEN_2023)
are NOT APPLICABLE on generated input and do not run there. Not shown by this: anything about forecast accuracy.
