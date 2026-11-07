# PROGRESS - what the product is, and how close it is (rewritten 2026-10-26; consolidated 2026-11-05)
This file is documentation, not product. A mark is earned only when the product files show it.

## What the product is not
- Not a player's over/under price. Not a score or winner pick. Not a cause measured straight to a player's stat line.

## What the product is
A structural model of one NFL game, read before kickoff. The rule book fixes the pie. Each level splits the level above and asks two questions: how big is the pie (volume), and who gets which slice (share). A cause known before kickoff is traced down every level to where it lands.

## The finished product, as the user reads it (fixed order; only the reviewer restates the template's words)
the rules level  Every game is 60 minutes; the ball changes hands after every score or stop; four downs to gain ten.
the game level  This game should have about P plays between both teams, more or fewer than these teams' usual, because ___.
the team level  His team gets about S of them, because ___.
the play-call level  Of those, D are dropbacks, H handoffs and K kneel-downs; the D dropbacks are A throws, R sacks and C scrambles; he is hit on about Q of his dropbacks, because ___.
the position-group level  Of the A throws, the receivers get Y, the tight ends Z, the backs W, others O, and T are thrown away, because ___.
the player level  He gets N of his group's, because ___.
the touch level  Each is worth about M yards against this defense, because ___.
Every count is a slice of the count above and the slices add up exactly. Every number carries its range (2SE). Every "because" names a measured link, or says "its own average so far; nothing measured moves it."

## The reframe (2026-10-26): rules as conservation, volume and share, an ML lens with limits
- The rules are the conservation. The three record checks (check_clock.py, check_possessions.py, check_downs.py) proved the play-by-play record obeys the rule book: 0 unexplained. They become the engine's transition rules and the engine's test: simulated games are written in the play-by-play record's own columns and the same checks run on them unchanged; any OTHER is an engine fault.
- Two questions per level. Volume and share. The chain multiplies: his touches = P x his team's share x the call share x his group's share x his share of his group. Each level's move from its own average so far is one term; a root's effect on a player is traced to the term where it lands. A term where nothing moves is stated with its ceiling.
- Feedback runs up. A call changes clock, field and score, which change the next calls and the game's plays. The engine plays this out snap by snap; it is in-game state, not a pregame cause.
- The ML lens has two jobs, never a third. (1) Candidate search: one boosted-tree model per term ranks candidate roots by help on a season it never saw; it never awards a word. (2) Engine mechanics: the next call given game state and each unit's earlier-games rates.
- Banned as inputs: market lines (spread_line, total_line, vegas_wp, vegas_wpa, vegas_home_wp, vegas_home_wpa); nflfastR model outputs fit on all seasons (ep, epa, wp, wpa, cp, cpoe, xpass, pass_oe, xyac_*); anything from the same game or later.
- The yardstick every link must beat: the engine with no established link, i.e. the rules plus each unit's averages so far, played out. If it reproduces real spreads of plays and possessions on seasons not fit on, and shuffled matchups flatten them, the game level's sentence is earned with "its own average so far".

## Root families and what the play-by-play record holds (empties counted, never filled)
Rules: fixed; the engine, not a root. Environment: roof, surface, temp, wind, weather, stadium, location, div_game, coaches in the play-by-play (temp and wind empty in 71-127 games a season; an indoor game has no weather; an empty outdoor game is UNKNOWN); rest days in games.csv. Matchup: each offense's and defense's earlier-games rates this season. Availability: injuries, rosters, snap counts per player per game. Personnel and formation: in pbp_participation, about 24% empty in 2019-2021 and 0% from 2023 for personnel, route and coverage 50-63% empty every season; a play's own personnel is not known before kickoff, so as an input it is a unit's rate from earlier games. Game state: engine mechanics only.
Units and branches: roots are units (each offensive line, pass rush, secondary, receiver group, backs, quarterback, play-caller); a label (a foul, a clock stop, a change of hands) is where a unit's trait shows up, never the root. Rates are per chance, never per game. A branch has three causes, each its own link: the unit's trait, the matchup, the setting. Clean and fouled snaps are read together. A foul costs twice: by rule and by the cascade. Formation and personnel are NOT TESTABLE as pregame inputs.

## How progress is counted: four marks per level, 28 in all
MAPPED the level's links are drawn from the rules and the units, volume and share, down and up. MEASURED each link carries a word (ESTABLISHED / NOT SHOWN / NOT TESTABLE), measured on the level above as it happened. IN PRODUCT a product file states the level's sentence for real games, with its range and its because. SCORED the grader scores that sentence on seasons not fit on.
Tally: levels 7 | marks 28 | earned 1 (the rules level IN PRODUCT: out/rules_level.csv, 1,719 rows, built from the three checks' reason tables and verified by rules_level.py) | product complete: no.

## Status of the rules level (record reads, stamped, never product; run by run.sh stage 4)
Clock (check_clock.py to clock-check.md): of 223,724 stretches between snaps, 316 lack a real-time clock stamp (206 in 2019, 110 in 2020). Revision stamps are whole seconds through 2021 and mostly thousandths from 2023, so WITHIN REAL TIME and WITHIN RESOLUTION together hold about 99% of stamped stretches each season; FASTER beyond resolution 267 / 238 / 258 / 356 / 349 / 321, each an officials' correction (4-1-4, not logged) or a record error, which the play-by-play record cannot tell apart; the counts were written before the run and met. 40-second check from 2023 only (end stamps): 3,580 to 4,057 snaps a season over, none a called violation (4-6-3).
Possessions (check_possessions.py to rules-level.md): 36,348 possessions, 1,676 games (76 postseason, printed apart); back-to-back 1,506, unexplained 0; counts equal the run-log line written before the script existed.
Downs (check_downs.py to downs-check.md): 328,102 rule checks, OTHER 0 (expected 0), UNCHECKED 0; 191,675 pairs by the basic rule and 17,762 by a named exception; 34,675 pairs not judged (a change of team, a break, or a possession ending on its first snap).
Season rules (measure_season_rules.py to rules-module.md): each season's values measured before the engine uses them; 2022 UNKNOWN; every rule quoted from its pinned book (run.sh stage 2: UNKNOWN 0 in all five seasons).
Engine (engine.py, run.sh stage 4): plays 1,676 games from the pinned model files; its games are not yet checked by the play-by-play record checks in run.sh (engine-legality.md, Status).

## Working rules (each cost runs to learn)
- Name what limits acceptances now, and its measure; restate it when it moves; choose the next chain to relieve it.
- Done is bounded: a chain is accepted when every count in its sentence is sourced and every article it cites is checked against the book. Rows that move no count are printed as unsettled with their reason.
- A sha is kept only where code checks it: the rule book's (a differing download is refused), the stamp on line 1 of each output file, the pins a block reads. 'Unchanged' is proven by comparing contents from line 2 on, never by sha.
- Read the play-by-play record before writing a rule; a rule written from memory is a guess.
- Check only what the next sentence or the engine reads; the rest is listed UNCHECKED or unsettled with its reason.
- An injected fault tests football (the down, the clock, who has the ball), never a label's wording.
- Where the play-by-play record cannot tell two rules apart, grade the next state against every rule-allowed outcome; one fitting is EXPLAINED with all fitting rules named; none fitting is OTHER. Never pick the rule from the outcome.
- Empties are counted, never filled. History is deleted, not kept; only files a live script reads stay.
- An explanation written into a prediction is not a cause until it is measured.

## Open questions
- Which count the game level's "plays" means: charged downs, all snaps, or snaps plus Tries (O2 in rules-level.md).
- Where QB hits come from (the play-call level's Q): no column holds them.
- The play-call level's slices: spikes (a forward pass by rule) and aborted snaps have no slice (O3 in rules-level.md).

## Roles
Reviewer (Cameron): restates sentences and rules; never asked for a decision a measurement can settle. Author thread: writes and runs code, one chain per paste; every block pins the shas it reads and refuses if they moved, prints its predictions before the numbers, injected faults and negatives first. Reviewer thread: grades from pasted printouts only; writes acceptance criteria before code; decision per chain: ACCEPTED / SAME ANSWERS / NO CHANGE. Every check cites the rule-book article it rests on. Only product files count.

## Coverage limits (printed by every run; a zero stands beside its denominator)
- transition.py generated foul events: 100,000 drawn; 48,864 resolved to a spot, 51,136 UNKNOWN (the rule gives no spot the play-by-play record could verify); 0 off the rule among the resolved.
- Downs: 328,102 rule checks judged; 34,675 pairs not judged (a change of team, a break, or a possession ending on its first snap); OTHER 0 among the judged.
- Clock: 316 stretches lack a real-time clock stamp (UNCHECKED); the 40-second check reads end stamps, present from 2023 only; 16 postseason stretches past the first overtime are unchecked.
- Possessions: 36,348 possessions; back-to-back 1,506, all explained by a rule class; 0 unexplained.
- Incident suite: revision 12 passes 13 of 13; revision 16 passes the predecessor-index oracle and the estimator oracle and still fails two (model preflight: sample_gain() missing 'w'; end to end: gain_sack INSUFFICIENT_DATA). Those two are known defects, reproduced, not detections.
