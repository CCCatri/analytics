# rules-module.md - one rules module (rules.py), written before code (2026-10-26)
Verdict when it runs: SAME ANSWERS (no product answer changes; no mark). Why now: the engine legality stage plays games from this module; nothing else may hold a rule the engine uses.

## 1. What rules.py exports (snap kinds-the season rules; not the plan's E-steps) (each item cites its article; the 2026 book rules/nfl_rulebook_2026.pdf, sha 144cec5bffd2)
snap kinds Snap kinds: pass, run, qb_kneel, qb_spike, punt, field_goal (one list; the possessions check's OFF and the clock check's SNAP are removed).
foul families Foul families, by record foul name, each with its next-down rule:
   pre-snap by the offense, the down replayed with yardage (14-4-9, 14-3); during the play by the offense, the down replayed from the spot (14-1-2 Item 1, 3-8-4);
   loss of down (14-1-2 Item 2); by the offense after the whistle, the down counts (3-8-5); by the offense between downs, the down unchanged (14-1-2 Item 7);
   by the defense, a first down (14-1-2 Item 5, 7-3-1(b)), except Item 5's Exceptions, read from the book's Item 5 lines at import, the down and line to gain unchanged unless the yardage reaches the line;
   the 12-players tie (R4 v17 point 2) as data with its measured counts; illegal touch pass (8-1-8(a), 8-1-8(b)).
   One list per family; the clock check's and the downs check's copies are removed.
the next-down rule next_down(state, outcome): the allowed next (team, down, distance) states with their article: the next down (3-8-5), a new series at or past the line (7-3-1(a)), turnover on downs (7-3-2a), the kickers' recovery (7-3-1(d), 7-3-1(e)), and the foul families of foul families.
the clock rule clock_class(play, state): RUN / STOP / PARTIAL, with its article: incomplete pass (4-4f), out of bounds with its windows (4-3-2a), fouls with their windows (4-3-2e), the two-minute warning (3-41), timeouts (4-5-1), injuries (4-5-3, 4-5-4), replay (15-5-1), the play clock (4-6-1, 4-6-2). the clock check's window functions move here.
the next-possession rule next_possession(ending): who snaps next, with its article: after a Try or a field goal, the team scored upon receives (11-3-4, 11-4-6, 6-1-1a); after a safety, the team scored upon free kicks (11-5-1(b), 11-5-2); turnover on downs (7-3-2a); the kickers' recovery (6-1-6, 6-1-4c, 9-3-2 Item 1, 7-3-1d, 7-3-1e); halftime (4-2-2); overtime (16-1-2, 16-1-3, 16-1-4).
the season rules Season rules, one row per season 2019-2025, the only per-season values the engine plays: the overtime period's length and whether both teams must possess (16-1-3, 16-1-4), the kickoff touchback spot, onside-kick availability. Each value carries its source: 'measured (R7)' or 'rule text'. 2022 is the held out season: its values come from rule text only, never its record; until read, UNKNOWN.

## 2. R7, inside the rules module: each season's values measured before the engine uses them
R7 v2 (2026-10-26, after the first run: predictions held 23 of 30):
   a. Every measure prints what it counted (games or kicks) beside its value. A measure with nothing to count reads 'no games' (or 'no kicks') and no prediction is judged (2020's postseason had no overtime game).
   b. M5 is replaced. Every onside kick each season (not only the odd ones), printed by quarter (1-3, or 4th and overtime) and by the kicking team's score (ahead, tied, behind), with each kick's play text for 2019-2021 and 2023, and every kick in 2024-2025.
      Prediction, written now from memory and to be measured (the first M5 rested on a wrong picture): through 2023 a surprise onside kick could come at any time, from any team, so kicks appear before the 4th quarter and from teams not behind; in 2024 every onside kick is in the 4th quarter or overtime by a team behind; in 2025 every onside kick is by a team behind, in any quarter.
      the season rules's onside row for each season is written from these counts, with the kicks that break the prediction read on their plays first.

For each season except 2022, read from the record, each with its prediction printed before the number:
   the most common drive-start spot after a kickoff touchback (predicted: the 25 through 2023, the 30 in 2024, the 35 in 2025);
   the longest regular-season overtime in game seconds (predicted: 600, a 10-minute period, every season);
   regular-season overtime games ended by a touchdown on the first possession (predicted: some each season through 2024, 0 in 2025);
   postseason overtime games ended that way (predicted: some in 2019-2021, 0 from 2023);
   onside kicks by a team not trailing, or before the 4th quarter (predicted: rare through 2024, more in 2025 if the any-time-when-trailing rule shows).
A season's rule-change page is cited once read, by its address and sha; until then the cite reads UNCHECKED. A measured value that breaks its prediction is read on its plays before it is written into E6.

## 3. What must stay identical (contents from line 2 on)
out/possessions_possessions.csv, out/possessions_classes.csv, out/clock_counts.csv, out/clock_faster.csv, out/clock_over40.csv, out/clock_reasons.csv, out/downs_counts.csv, out/downs_other.csv, out/downs_reasons.csv, out/rules_level.csv, out/product_lines.csv.

## 4. The injected faults that prove each read uses the module (each run in-process on a changed copy of rules.py, then put back)
P1 the downs check: 'Defensive Holding' taken out of the defense's award family: its 1st downs short of the line to gain lose their rule, so C1 must read OTHER above 0 (read 2026-10-26: 103). The first P1 could not fail: the downs check reads the award family only for fouls by the defense, and every False Start is by the offense.
P2 the clock check: an incomplete pass's clock class set to RUN: the clock check's class counts must change.
P3 the possessions check: after a field goal, the scoring team set to receive: back-to-back drives 'unexplained' must read above 0.
P4 A list or function defined both in rules.py and in a read script: the run lists every named constant and function in check_possessions.py, check_clock.py and check_downs.py that rules.py also defines; it must be 0. Article strings inside reason texts stay where they are and are not counted.

## 5. What stays in each read (the next-reader rule: no engine step reads it)
Ledgers (LEDGER_322, EXPECTED_FASTER, FROZEN_2023); reason texts; record loading (TYPES, EXTRA, FROM_EVENTS); WORDS, ORD; the v12 comparison; the 'fits one of the rules the record cannot tell apart' buckets; the v19 column flag; the tie's re-measure.
