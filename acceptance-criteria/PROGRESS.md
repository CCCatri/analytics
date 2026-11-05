# PROGRESS - the plan, and how close the product is (rewritten 2026-10-26 with the reframe; the single document both threads read)
This file is documentation, not product. A mark is earned only when the product files show it; reads, run log lines and chat earn nothing.

## What the product is not
- Not a player's over/under price. out/product_lines.csv still holds the old one as a diagnostic (diagnostic only).
- Not a score or winner pick. The score is printed with its range, never headlined.
- Not a cause measured straight to a player's stat line (diagnostic only, never progress).

## What the product is
A structural model of one NFL game, read before kickoff. The rule book fixes the pie. Each level splits the level above and asks two questions: how big is the pie (volume), and who gets which slice (share). A cause known before kickoff is traced down every level to where it lands.

## The finished product, as the user reads it (fixed order; only the reviewer restates the template's words)
the rules level Rules  Every game is 60 minutes; the ball changes hands after every score or stop; four downs to gain ten.
the game level Game   This game should have about P plays between both teams, more or fewer than these teams' usual, because ___.
the team level Team   His team gets about S of them, because ___.
the play-call level Calls  Of those, D are dropbacks, H handoffs and K kneel-downs; the D dropbacks are A throws, R sacks and C scrambles; he is hit on about Q of his dropbacks, because ___.
the position-group level Group  Of the A throws, the receivers get Y, the tight ends Z, the backs W, others O, and T are thrown away, because ___.
the player level Man    He gets N of his group's, because ___.
the touch level Touch  Each is worth about M yards against this defense, because ___.
Every count is a slice of the count above and the slices add up exactly. Every number carries its range (2SE). Every "because" names a measured link, or says "its own average so far; nothing measured moves it."

## THE REFRAME (2026-10-26): rules as conservation, volume and share, an ML lens with limits
R1 The rules are the conservation. The three record checks (clock check_clock.py, possessions check_possessions.py, downs check_downs.py) proved the record obeys the rule book: 0 unexplained. They become (a) the engine's transition rules: from any game state, the list of allowed next states, cited by article; and (b) the engine's test: simulated games are written in the record's own columns and the possessions check, the clock check and the downs check run on them unchanged; any OTHER is an engine fault.
R2 Two questions per level. Volume (how big each pie is) and share (who gets which slice). The chain multiplies: his touches = P x his team's share x the call share x his group's share x his share of his group. In logs each level's move from its own average so far is one term, and the terms add exactly; a root's effect on a player is traced to the term where it lands. A term where nothing moves is stated with its ceiling ("no change shows up; any change is under X").
R3 Feedback runs up. A call changes clock, field and score, which change the next calls and the game's plays (about 39 seconds after a running snap, about 6 after an incompletion: R2's D2). The engine plays this out snap by snap; it is in-game state, not a pregame cause.
R4 The ML lens has two jobs, never a third. (1) Candidate search: one boosted-tree model (xgboost 3.1.0, lightgbm 4.6.0, sklearn 1.7.2 installed) per term; target = the term's move from its own average so far, given the level above as it happened; it ranks candidate roots by help on a season it never saw. It never awards a word: each candidate goes through step 4 alone (fit on five seasons, stated for the sixth, 2SE, shuffled null). (2) Engine mechanics: the next call given game state (down, distance, field, clock, score, timeouts) and each unit's earlier-games rates.
R5 Banned as inputs: market lines (spread_line, total_line, vegas_wp, vegas_wpa, vegas_home_wp, vegas_home_wpa); nflfastR model outputs fit on all seasons (ep, epa, wp, wpa, cp, cpoe, xpass, pass_oe, xyac_*, and the 49 columns the 2026-10-26 header read listed); anything from the same game or later games.
R6 The yardstick every link must beat: the engine with no ESTABLISHED link, i.e. the rules plus each unit's averages so far, played out. If it reproduces real spreads of plays and possessions on seasons not fit on, and shuffled matchups flatten them, the game level's sentence is earned with "its own average so far".

## Root families and what the record holds (header read 2026-10-26; empties counted, never filled)
Rules: fixed; the engine, not a root.
Environment: roof, surface, temp, wind, weather, stadium, game_stadium, location, div_game, home_coach, away_coach in the play-by-play. temp and wind are empty in 71-127 games a season; before use, cross-check the empties against roof (an indoor game has no weather; an empty outdoor game is UNKNOWN, never filled). Rest days in games.csv.
Matchup: each offense's and defense's earlier-games rates this season, built from the play-by-play.
Availability: injuries_{season}.csv, rosters_{season}.csv.gz; snap counts per player per game in snaps_{season}.csv.gz (the player level inputs).
Personnel and formation: measured 2026-10-26 (the engine legality stage, part a v2 e): pbp_participation holds offense_formation, offense_personnel, defense_personnel, defenders_in_box, number_of_pass_rushers, players_on_play, offense_players, defense_players, n_offense, n_defense, route, defense_coverage_type; personnel about 24% empty in 2019-2021 and 0% from 2023, offense_formation about 27% then 20%, route and coverage 50-63% empty every season; the play-by-play holds shotgun and no_huddle (0% empty). A play's own personnel is not known before kickoff: as an input it is a unit's rate from earlier games, or engine mechanics. Empties are counted, never filled.
Game state: in the play-by-play; engine mechanics only.

UNITS AND BRANCHES (the reviewer's view, 2026-10-26; explored in the engine legality stage and the search stage, not yet measured):
- Roots are units: each offensive line, pass rush, secondary, receiver group, backs, quarterback and play-caller. A label (a foul, a clock stop, a change of hands) is where a unit's trait shows up, never the root itself.
- The rules say where each branch can happen: its chance. Rates are per chance, never per game: holding per pass-block snap, pass interference per pass thrown, a false start per snap, out of bounds per carry. the possessions check, the clock check and the downs check's labels name the branches; the cited articles name the chances.
- A branch has three causes, each its own link: the unit's trait, the matchup (the other side's unit), the setting (environment).
- Clean and fouled snaps are read together. A unit's foul rate and its results on its clean snaps are two halves of one style (aggressive or safe); a unit that never fouls may be losing the matchup without a flag. Neither half is read alone.
- A foul costs twice: by rule (yards, the down) and by the cascade (drive length, snaps, points), measured against drives from the same down, distance and field without it.
- A root can start at any level. It enters at the link where its unit acts, and the engine carries it up the sentences (the play-call level calls to the game level snaps) and around the game (result to score, clock and field, to the next calls).
- The record names who fouled (the play text) and who played (the snaps files); formation and personnel are NOT TESTABLE.

## How progress is counted: four marks per level, 28 in all
MAPPED      the level's links are drawn from the rules and the units, volume and share, down and up.
MEASURED    each link on the map carries a word under step 4 (ESTABLISHED / NOT SHOWN / NOT TESTABLE), measured on the level above as it happened.
IN PRODUCT  a product file states the level's sentence for real games, with its range and its because.
SCORED      the grader scores that sentence on seasons not fit on: its numbers happen at 2SE and its slices add up.
Owner's call, open: MAPPED and MEASURED are defined on links; the rules level has record checks, not links, and under line 2 neither mark is shown by a product file as defined.

## Tally
Levels 7 | marks 28 | earned 1 | sentences in product 1 | product complete: no.
Next: the rules module (one rules module), then the engine legality stage.

## Status of the rules level (record reads, stamped, never product)
Clock: check_clock.py a3ddf36dcc4a to clock-check.md v16 b23041601078. Of 223,724 stretches between snaps, 223,408 have both clocks stamped (316 lack a revision stage stamp: 206 in 2019, 110 in 2020). Wall stamps are whole seconds through 2021 and mostly thousandths from 2023 (game clock whole seconds throughout), so the line between WITHIN REAL TIME and WITHIN RESOLUTION moves with the stamps; together they hold 99.3% of stamped stretches each season 2019-2021 and 99.1% 2023-2025 (35,606 / 36,202 / 37,932 / 37,946 / 37,194 / 36,739). FASTER beyond resolution 267 / 238 / 258 (2-second margin) and 356 / 349 / 321 (mostly a 1-second margin): the two eras are not compared. Each FASTER is an officials' correction (4-1-4, not logged) or a record error; the record cannot tell which. 40-second check from 2023 only (end stamps): 3,580 to 4,057 snaps a season over, none a called violation (4-6-3). The stamp reading is from the gap distributions; N7 prints the direct test.
Possessions: check_possessions.py 5b813aeb2da5 to rules-level.md ee8e43953310; 36,348 possessions, 1,676 games (76 postseason, printed apart); back-to-back 1,506, unexplained 0.
Downs: check_downs.py 1eacd0231810 to downs-check.md v15 f0f237034490; injected faults 46/46; 328,102 rule checks (a snap is checked by up to five rules), OTHER 0, UNCHECKED 0. Down to down (C1): 209,437 judged pairs, 191,675 by the basic rule and 17,762 by a named exception; 90 of those fit a rule-allowed outcome where the record does not say which of two rules applied. Not judged: 34,675 pairs (a change of team, a break, or a possession ending on its first snap): 5,694 / 5,571 / 5,877 / 6,009 / 5,811 / 5,713.
Articles: every article clock-check.md and downs-check.md cite is checked against the 2026 rule book's text (sha 144cec5bffd2). The data is 2019-2025: a rule that changed by season is a per-season record check (rules-level.md R7, not run).
One label rides with N7 (no count moves): 136 defensive pass interference calls on 1st down read 'down replayed (3-8-4)'; the award (14-1-2 Item 5) gives the same 1st down and should be named.

## Plan - one list, worked top to bottom; nothing off this list is worked on
Rule 1: every chain's block updates this file in the same run (its mark or its status).
Rule 2: old debt is fixed only when it blocks the next mark; the rest waits below with its reason.
Rule 3: a chain that changes no product answer is SAME ANSWERS or NO CHANGE and earns no mark.

N1 R2 run -> the rules level MEASURED (clock, part). RAN 2026-10-26: check_clock.py a3ddf36dcc4a to clock-check.md b23041601078 (v16); injected faults 21/21 | out/clock_counts.csv 0540d1bc0698 | out/clock_faster.csv defefc703e9c | out/clock_over40.csv 697356648181. Record reads, stamped, never product.
N2 record loads its columns -> SAME ANSWERS 2026-10-26: record.py events() carries the 13 score, scoring-side and try-result columns; product byte-identical caa87dd412e4. record.py now a18b89fe7985 (timeout label, 15-1).
N3 possession read as a script -> RAN 2026-10-26: check_possessions.py 5b813aeb2da5 to rules-level.md ee8e43953310; injected faults 24/24 | possessions 36348 games 1676 | unexplained 0 | out/possessions_possessions.csv 878c263d0054. Record read, stamped, never product.
N4 downs read -> the rules level MEASURED (downs, part). RAN 2026-10-26: check_downs.py 1eacd0231810 to downs-check.md f0f237034490 (v15) with record.py a18b89fe7985; exit 0; injected faults 46/46 | OTHER 0 (expected 0) | items {'AS RULE': 305986, 'EXPLAINED': 22116} | OTHER 0 listed in out/downs_other.csv b26dd02b7893 | out/downs_counts.csv 50274c70d67d. Record read, stamped, never product.
N5 merged into N7: the sentence is built from measurement; no reviewer decision.
N6 every writer stamps its own sha and the file's label on line 1; product_lines.csv says 'diagnostic only, diagnostic' on its own rows; the recipe written and proven by rebuild. NO CHANGE.
N7 the rules level IN PRODUCT -> ACCEPTED 2026-10-26: rules_level.py ede0aef941c2 writes out/rules_level.csv 8a2acf3219a8 (1719 rows: template 3, exception 1500, as rule 124, unsettled 54, diagnostic 14, total 12, not judged 12; line 1 stamps the 'the rules level Rules' line's own sha; every label, article, book and count from out/clock_reasons.csv, out/possessions_classes.csv and out/downs_reasons.csv 93e8a38112fa; verify PASS; an injected count, template word and stamp each FAIL). check_downs.py 555cd7a10c5f to downs-check.md v19 aedf16a4ca8c: 14-1-2 Item 5's Exceptions read from the book; the 12-players tie re-measured (same down 145, 1st down at or past the line 58, short 0); five foul rows whose columns disagree with their play text flagged as unsettled (four C1 items); the receivers' foul on a downed punt (2024_18_LAC_LV) named as unsettled; counts unchanged against v16, 5 reasons moved. check_possessions.py re-locked to rules-level.md 72ae1dc9b61f (A8 11-3-4, 6-1-1a).
the rules module one rules module -> SAME ANSWERS 2026-10-26: rules.py bb2b3aab5b68 exports snap kinds-the season rules to rules-module.md bc49229ab150 (snap kinds; the foul families with Item 5's Exceptions read from the book and the 12-players tie as data; next_down; the clock windows, clock_class and the play clock; next_possession; season_rules); check_possessions.py 684d8fed2311, check_clock.py 567e8946b4e0, check_downs.py 8532a090b885 import it, their copies removed (check_possessions.py's own book() renamed book_line); section 3 files identical from line 2; P1-P4 each failed as written. R7 v2: measure_season_rules.py 944aef150c1b writes out/season_rules.csv 1d3606b8c099 (each measure with what it counted; predictions {'True': 28, 'not judged': 2}; M5 every onside kick by quarter and score; 2022 UNKNOWN; every rule-change page UNCHECKED).
  the rules module also holds one rule set per season, 2019-2025. Kickoff touchback spot and alignment (dynamic kickoff 2024, touchback to the 35 in 2025), onside kick availability (any time when trailing from 2025), the overtime possession rule (both teams: postseason from 2022, regular season from 2025) and replay assist (widened 2025) are each cited to that season's NFL rule-changes page, read and pinned before use. rules-level.md R7 runs before the engine legality stage: per season, the kickoff touchback rate, where drives start after kickoffs, onside tries and recoveries, and overtime possessions. A link fit across a season break is tested season by season.
the engine legality stage engine v0: games played out snap by snap on the rules and each unit's earlier-games averages, written in the record's columns. Each unit's averages are its branch rates per chance (UNITS AND BRANCHES), read from the possessions check, the clock check and the downs check's labels on its earlier games. Done when the possessions check, the clock check and the downs check on simulated games read 0 OTHER and an injected broken rule reads OTHER. NO CHANGE. | the engine legality stage, part a v4 -> NO CHANGE 2026-10-26: engine.py 23ff047b9b54 to engine-legality.md 997c850141ac (the engine legality stage, part a v4 a-e, v5 a-d, v2 a and e) plays 1676 games on rules.py 6476384d849d, whose the season rules quotes each season's rules from its book, found inside the article (rules/RULE_PINS.json ca8b1060e3aa: the Internet Archive's raw copies of the 2020, 2021, 2023 and 2024 books, whose league addresses answer 404, and its one copy of the 2025 rulebook page; 2019 from the 2020 book), R7's measured values beside each rule; each season's league-wide rates from the five other seasons (a look back, for legality only), the four 2020-2021 squibs out of the onside rates; out/sim_games.csv 5e6a929dca94 (seed 20261026). On them, the transitions tested pass within the event families v0 plays (the downs check OTHER 0, UNCHECKED 0, the possessions check unexplained 0, the clock check FASTER 0); 16 stretches unchecked (postseason period 6, 2020_20_BUF_KC); the stopped clock 0 failed of 70600 STOP and 18648 PARTIAL stretches, no playoff game tied, every game's periods by the season rules; P1-P4 and the the season rules injected fault each failed as written. Section 6: the engine legality stage, part a predicted plays and possessions per game within 10% of the record's; the engine plays 120.8 plays, 19.1 possessions and 32.0 points a game against the record's 137.5, 21.7 and 46.1 (all six seasons), within 10% in 2 of 12 season cells: the prediction did not hold. Counts in out/engine_checks.csv ffb78d3b3e9f. the engine-vs-record stage's acceptance criteria next.
the engine-vs-record stage the grader on the engine legality stage: the engine's spreads of plays and possessions against the real spreads, on seasons not fit on; shuffled matchups must flatten them. This measures the game level's first links (the yardstick, R6).
the search stage the engine's odds and the search for roots. The engine is E ~ P(E | state, knowable inputs); next state = T_rules(state, E); a player's stats = the sum of his credits over the snaps. Trees learn P per snap over the rule-allowed branches only, inputs known before kickoff (earlier seasons and earlier weeks) plus the game state; candidates start with the units' branch rates per chance, each read with the same unit's clean-snap results (UNITS AND BRANCHES), then knowable pregame factors (injury status, rest, roof and weather). Ranges are taken by game, or by stretch of absence, never by snap. Each claim names its kind: accounting (the rules), predictive improvement (a conditional association, given the level above as it happened; or a simulated difference between scenarios, composed through the engine), or a causal effect, stated only with its identifying assumptions written beside it. A candidate on and off in the fitted engine is the model's counterfactual, not a causal effect. Every candidate tried is kept in a search log; the held-out seasons screen; 2022 certifies nothing (its access history was deleted); 2026's games still to be played certify, each forecast stamped before kickoff. The checks at each step stay: snap odds, drives, team, player shares and probability bands, not the game total alone. Each accepted link is ACCEPTED. Together with the engine-vs-record stage -> the game level MAPPED, then the game level MEASURED, then the game level IN PRODUCT.
N9 then the team level to the touch level in order, each MAPPED -> MEASURED -> IN PRODUCT -> SCORED, one term at a time, each given the level above as it happened; old measurements re-measured when their level is reached (W6-W9).

## Stale lines in locked files (fixed in N7's run)
- rules-level.md line 37 (R1 'Open: ...'): closed. Overtime start has an injected case (check_possessions.py, 24/24); record.py loads the safety column; own-kickoff recovery is read through record.raw_frame by check_possessions.py.
- rules-level.md line 38 (R2 'clock identity'): not a check; it equals the total by construction (clock-check.md v16, Retired).
- rules-level.md lines 45-52 (Roadmap): R1, R2 and R4 have run; R3 is R2's D2 read; R5, R6, R7 have not run.
- downs-check.md line 6 ('quarter and game clock for order'): plays are ordered by order_sequence; check_downs.py sorts by it.
- Names: R1-R7 in rules-level.md (record checks), R1 in downs-check.md (the series read) and R1-R6 in this file's reframe are three different things under one letter.

## Working rules learned on the rules level (each cost runs to learn)
CONSTRAINT (2026-10-26): name what limits acceptances now, and its measure. Now: the cross-check of a acceptance criteria edit, then code, then a printout carried back, spent on the rules level labels; measure: round trips per acceptance. Restated when it moves; the next chain is chosen to relieve it.
DONE IS BOUNDED (2026-10-26): a chain lands when every count in its sentence is sourced and every article it cites is checked against the book. Rows that move no count are printed as unsettled with their reason, and not resolved further.
SHAS (2026-10-26): a sha is kept only where code checks it:
  - the rule book's sha: a download that differs is refused;
  - the stamp on line 1 of each output file: the code and acceptance criteria that wrote it;
  - pins on the files a block reads to compute counts: the block refuses if one moved.
  PROGRESS.md is never pinned; an edit to it finds its anchor text exactly once instead.
  No sha is written into PROGRESS.md lines or quoted in replies unless it moved or a pin refused (shas already in old lines are left as they are).
  'Unchanged' is proven by comparing contents from line 2 on, never by sha.
- Read the record before writing a rule; a rule written from memory is a guess.
- Check only what the next sentence or the engine reads; the rest is listed UNCHECKED or unsettled with its reason, never chased row by row (2026-10-26: about fifteen round trips on six rows that no count reads).
- A injected fault tests football (the down, the clock, who has the ball), never a label's wording.
- Where the record cannot tell two rules apart, grader the next state against every rule-allowed outcome; one fitting is EXPLAINED with all fitting rules named; none fitting is OTHER. Never pick the rule from the outcome.
- Empties are counted, never filled. History is deleted, not kept: no body/ copies; only files a live script reads stay.
- An explanation written into a prediction is not a cause until it is measured (2026-10-26: the 2023 stamps were predicted coarser and measured finer).

## Waiting (gaps from old iterations), each with why it waits
W2 land.py dependent-stack guard: touches the diagnostic only.
W3 players' shares add up to the team: becomes the player level's own add-up check.
W4 baseline.py's hard-coded 0.40-0.50 prediction: diagnostic only.
W5 grader.py's FAIL print: fixed before the first SCORED mark.
W6 the 15 team links measured cause -> count: re-measured as shares given the team level when the play-call level is reached.
W7 the two WR-room target links: re-measured given the play-call level when the position-group level is reached.
W8 the shares-on-the-field map (players.py): re-measured as 'share of his group's' at the player level.
W9 the per-touch map (plays.py): tested on seasons not fit on at the touch level.
W10 product_lines.csv (diagnostic only): a labeled diagnostic (N6) until the player level and the touch level sentences replace it.

## Open questions
Q2 Which count the game level's "plays" means: charged downs, all snaps, or snaps plus Tries (reviewer restates; O2 in rules-level.md).
Q3 Where QB hits come from (the play-call level's Q): no column holds them.
Q4 the play-call level's slices: spikes (a forward pass by rule) and aborted snaps have no slice (O3 in rules-level.md).

## Roles and conventions (both threads)
Owner (Cameron): restates sentences and rules; never asked for a decision a measurement can settle.
Builder thread: writes and runs code, one chain per paste; every block pins the shas it reads and refuses if they moved, prints its predictions before the numbers, injected faults and negatives first, and ends with questions for the reviewer.
Falsifier thread: graders from pasted printouts only; writes acceptance criteria files before code; decision per chain: ACCEPTED / SAME ANSWERS / NO CHANGE.
Every check or target cites the rule-book article it rests on. Football words in every sentence a reader sees. Only product files count.
