# engine-legality.md - engine v0, written before code (2026-10-26)
Verdict when it runs: NO CHANGE (an engine exists; no product answer changes; no mark). It is the floor the engine-vs-record stage graders and the search stage searches on.
the engine legality stage lands in two parts, one chain each: the engine legality stage, part a (league-wide rates; this file's sections 1-6) proves every simulated game obeys the rules; the engine legality stage, part b (each unit's earlier-games rates per chance, PROGRESS UNITS AND BRANCHES) is written after the engine legality stage, part a lands.

## 0. First read in the chain (folded in from R7 v2, question 2)
Kickoffs whose play text lacks 'onside' and that travel under 20 yards, or that the kicking team recovers: count by season (2022 not read), with play text. Prediction: a handful a season, each a squib or a muffed deep kick, not an onside try. Any onside try among them is added to the onside rate in the season rules's rows before the engine reads them.

## 1. What the engine plays from (no other input)
- rules.py (snap kinds-the season rules): snap kinds, foul families and their next-down rules, next_down, clock_class and its windows, next_possession, each season's rules (touchback spot, overtime length and possession rule, onside availability). 2022 is never simulated (held out).
- League-wide rates for season s, read from the five other unsealed seasons (never s itself, never 2022): in bins of down, distance (1-3, 4-6, 7-10, 11+), field (own 1-20, 21-50, opp 49-21, opp 20-1), time (normal, last 2:00 of a half, last 5:00 of the game, overtime) and score (behind 9+, behind 1-8, tied, ahead 1-8, ahead 9+):
  the snap kind; yards by kind; incompletion, sack, interception and fumble-lost rates; fouls by family per chance (per snap, per pass, per run, per kick); 4th-down choice (go, punt, field goal); field goal make rate by distance; punt and kickoff distance and return; onside tries and recoveries by situation (the season rules); timeouts by situation; real seconds between snaps by clock class (R2's D1 and D2 reads).
  Bins with too few plays are merged with the next coarser bin; the merges are printed.
- Banned: market lines, nflfastR model columns, anything from the same game or later (PROGRESS R5).

## 2. What it writes
out/sim_games.csv: one simulated game for every real game of 2019-2021 and 2023-2025 (same teams, season, week, home side), seed printed on line 1 beside the stamp. Every column check_possessions.py, check_clock.py and check_downs.py read, in the record's own form, including play text in the record's wording for every foul ('PENALTY on TEAM, Name, N yards, enforced at X' with '- No Play' when it is one), score, timeout, two-minute warning and end-of-quarter rows, the game clock, and wall-clock stamps (start and end of each play) that keep real time no slower than the game clock.

## 3. What v0 does not play (each stated, so the engine-vs-record stage reads its cost, never hidden)
Fouls by both teams on one play; a foul and a turnover on one play; laterals; fumbles recovered by the side that did not lose them except as a turnover; replay reviews; injuries; runoffs. Each is a branch real games take and the engine does not; the engine-vs-record stage prints how many real plays fall in each.

## 4. Done when (the record checks run on the engine's games unchanged; only the input file differs)
- check_downs.py on out/sim_games.csv: OTHER 0, UNCHECKED 0.
- check_possessions.py: unexplained back-to-back 0; every possession ending by a rule class.
- check_clock.py: FASTER not licensed 0; no clock stretch without a class.
- The stopped clock, graded on the engine's games (the clock check does not grade it): on every stretch whose class is STOP, the game clock falls by no more than the play's own length (its end stamp minus its start stamp) plus 1 second; the clock starts again only at the next snap (4-3, 4-4f). PARTIAL stretches may run no longer than the time to the next snap.
- Every game 3600 seconds of regulation, plus overtime only when tied, by the season rules's season rule.

## 5. Plants (each on a changed copy of the engine, then put back; each must FAIL)
P1 after a field goal, the scoring team receives: the possessions check unexplained above 0.
P2 a 5th down allowed: the downs check OTHER above 0.
P3 the game clock kept running after an incomplete pass: the stopped-clock check above fails (the clock check alone would pass it: both clocks move together).
P4 2024's touchback spot set to the 25: the season-rule check (R7 M1 on the engine's games) reads 25, not 30, and fails.

## 6. Printed, not judged (the engine-vs-record stage graders): per season, the engine's mean and spread of plays, possessions and points per game beside the real ones.

## the engine legality stage, part a v2 (2026-10-26, after the first the engine legality stage, part a run)
a. Section 0's four short kicks without 'onside' (2020: 3, 2021: 1) were squibs fielded by the receivers, as predicted: they are not onside tries. They come out of the onside rates, and 2020's added cell (4th and overtime, kicking team ahead) comes out of the season rules.
b. 2020's postseason overtime row in the season rules is filled from its measured neighbors: 2019 and 2021 both measured the same rule (a postseason game could end on the first possession's touchdown); the both-teams rule begins 2022. Source written as 'neighbors 2019 and 2021 measured; 2020 had no overtime game'. No playoff game may end tied: a tie at the end of regulation goes to overtime (the rules level).
c. the engine legality stage, part a's rates from the five other seasons are a look back, used for the legality test only. From the engine legality stage, part b on, every forecast reads only what was known before kickoff: earlier seasons and earlier weeks of the same season.
d. Before the engine-vs-record stage reads any gap, the engine's games and the record's games are counted by the same code (the possessions check, the clock check and the downs check's counts), so that 'plays', 'possessions' and 'points' mean the same thing on both sides.
e. Read, nothing written: every raw file's column names, listed by file, with any column naming personnel, formation or participation, and its share of empty cells by season. PROGRESS's 'Personnel and formation: NOT TESTABLE' stands only if this finds none.
the engine legality stage, part a stands when the rerun with a and b reads 0 OTHER, 0 unexplained and 0 FASTER, the stopped-clock check passes, and P1-P4 fail as written.

## the engine legality stage, part a v3 (2026-10-26, from the outside critique)
a. the season rules keeps two things apart: the rule (what the rules allow, with its source: that season's rule book or the league's published change) and the measured value (what the record showed, from R7). A measured value supports a rule; it never stands in for one.
b. 2020's postseason overtime: the rule is modified sudden death in 15-minute periods (a touchdown on the first possession ends the game; a field goal gives the other team a possession), to be cited from the 2020 rule book's Rule 16 once read, its address and sha pinned. Until it is read, the source reads 'neighbors 2019 and 2021 measured; the 2022 change approved March 2022 (news reports); 2020 rule book not read'. v2 b's neighbor reading is support, not the source.
c. 2022 is not eligible to certify: earlier iterations used it as a hold-out, and their record (body/) was deleted 2026-10-26, so its access history cannot be shown. It stays out of every fit and screen, and it certifies nothing. Certification moves to 2026's games still to be played: each forecast is written before kickoff, stamped, and scored after.

## the engine legality stage, part a v4 (2026-10-26): each season's rules read from that season's book
a. Rule books, downloaded to rules/, each refused unless it opens as a PDF, its sha printed and pinned at first download:
   2020 https://operations.version 1.com/media/4693/2020-version 1-rulebook.pdf
   2021 https://operations.version 1.com/media/5427/2021-version 1-rulebook.pdf
   2023 https://operations.version 1.com/media/gsaaatbb/2023-rulebook.pdf
   2024 https://operations.version 1.com/media/24emxacq/2024-version 1-rulebook.pdf
   2025 changes page https://edge-operations.version 1.com/the-rules/version 1-rulebook/ (read as text, saved with its sha)
   2026 rules/nfl_rulebook_2026.pdf (on disk)
b. For each season 2019-2021 and 2023-2025 and each rule the season rules plays (postseason overtime, regular-season overtime, the kickoff touchback spot, when an onside kick may be tried), the rule cell quotes the book's own sentence, with book, sha and article; the quoted phrase must be found inside that article by the heading finder (headings in capitals ending in a period). A season without its own book cites the nearest book read and says so beside it: 2019 'the 2020 book; 2019 book not read'. 2025 cites the changes page, not the 2026 book (2026 changed the onside article). The measured value from R7 sits in its own cell beside the rule.
c. Plant: one rule cell's quoted phrase changed by one word must read 'not found in the article' (FAIL).
d. 2024's and 2020's postseason overtime come from their own books' Rule 16; v2 b's and v3 b's neighbor reading becomes support only.
e. The v2 a-e check reads only inside the v2 section. PROGRESS.md's the engine legality stage line says '0 OTHER within the event families v0 plays' and records section 6's miss: its predictions, the engine's plays, possessions and points per game against the record's, and that they did not hold.

## the engine legality stage, part a v5 (2026-10-26, after the v4 rerun stopped at section 4 on 16 stretches)
a. Section 4's 'no clock stretch without a class' excepts one case, counted and printed by season and game: postseason periods past the first overtime, which the clock check does not grade because no record game reached one. Their reason reads 'unchecked: the clock check does not grade postseason periods past the first overtime (no record game reached one)', not NOT TESTABLE: the rule text exists (16-1-4(h)). Grading them in the clock check is listed UNCHECKED with that reason, and goes in when a chain reads those stretches. Any other unclassed stretch still stops the chain.
b. The seed is fixed and printed; it is never changed to pass a check.
c. An archive copy stands as a rule source when it carries the league's original address, the archive address and capture date, its sha, and the quoted rule found in its article. The 2025 changes page (saved 2026-05-15) stands only if its text names 2025 and its onside line is not the 2026 wording ('at any time during the game'); the run prints both.
d. On a run that stands, the books stay in rules/ (the season rules cites them); files are put back only when a chain stops.
