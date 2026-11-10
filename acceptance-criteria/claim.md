# The NFL claim: what the product says, in fixed order

This file is the claim, not its status: status lives on the rubric page, the method in `METHOD.md`, the words in `VOCABULARY.md`. `product/rules_level.py` reads its words from the line starting "the rules level"; that line changes only with a rerun of `rules_level.py`.

## What the product is not
- Not a player's over/under price. Not a score or winner pick. Not a cause measured straight to a player's stat line.

## What the product is
A structural model of one NFL game, read before kickoff. The rule book fixes the pie. Each level splits the level above and asks two questions: how big is the pie (volume), and who gets which slice (share). A cause known before kickoff is traced down every level to where it lands.

## The seven sentences (fixed order; only the project owner restates them; restating a sentence to fit results changes the measure)
the rules level  Every game is 60 minutes; the ball changes hands after every score or stop; four downs to gain ten.
the game level  This game should have about P plays between both teams, more or fewer than these teams' usual, because ___.
the team level  His team gets about S of them, because ___.
the play-call level  Of those, D are dropbacks, H handoffs and K kneel-downs; the D dropbacks are A throws, R sacks and C scrambles; he is hit on about Q of his dropbacks, because ___.
the position-group level  Of the A throws, the receivers get Y, the tight ends Z, the backs W, others O, and T are thrown away, because ___.
the player level  He gets N of his group's, because ___.
the touch level  Each is worth about M yards against this defense, because ___.

Every count is a slice of the count above and the slices add up exactly. Each rate is per the count it names. Every number carries its range (2SE); where two measures of one link can't be told apart on held-out seasons, the range spans both. Every "because" names a measured link, or says "its own average so far; nothing measured moves it."

## How the levels connect
- The rules are the conservation. The three record checks (`check_clock.py`, `check_possessions.py`, `check_downs.py`) prove the play-by-play record obeys the rule book. The engine's games are written in the play-by-play record's own columns and the same checks run on them unchanged.
- The link chain multiplies: his touches = P x his team's share x the call share x his group's share x his share of his group. A root's effect on a player is traced to the term where it lands; a term where nothing moves is stated with its ceiling.
- Feedback runs up: a call changes clock, field and score, which change the next calls and the game's plays. The engine plays this out snap by snap; it is in-game state, not a pregame cause.
- Machine learning has two jobs, never a third: ranking candidate roots by help on a season it never saw (it never awards a verdict), and the engine's next call given game state and each unit's earlier-games rates.

## Banned as inputs
Market lines (spread_line, total_line, vegas_wp, vegas_wpa, vegas_home_wp, vegas_home_wpa); nflfastR model outputs fit on all seasons (ep, epa, wp, wpa, cp, cpoe, xpass, pass_oe, xyac_*); anything from the same game or later.

## The yardstick every link must beat
The engine with no established link: the rules plus each unit's averages so far, played out. If it reproduces real spreads of plays and possessions on seasons not fit on, and shuffled matchups flatten them, the game level's sentence is earned with "its own average so far".

## What the play-by-play record holds (empties counted, never filled)
- Rules: fixed; the engine, not a root.
- Environment: roof, surface, temp, wind, weather, stadium, location, div_game, coaches; temp and wind empty in 71-127 games a season; an indoor game has no weather; an empty outdoor game is counted as missing. Rest days in games.csv.
- Matchup: each offense's and defense's earlier-games rates this season.
- Availability: injuries, rosters, snap counts per player per game.
- Personnel and formation: in pbp_participation, personnel about 24% empty in 2019-2021 and 0% from 2023; route and coverage 50-63% empty every season. A play's own personnel is not known before kickoff, so as an input it is a unit's rate from earlier games; formation and personnel are NOT TESTABLE as pregame inputs.
- Units are the roots (each offensive line, pass rush, secondary, receiver group, backs, quarterback, play-caller); a label (a foul, a clock stop, a change of hands) is where a unit's trait shows up, never the root. Rates are per chance, never per game. A branch has three causes, each its own link: the unit's trait, the matchup, the setting.

## Open in the claim
- Which count the game level's "plays" means: charged downs, all snaps, or snaps plus Tries (O2 in `rules-level.md`).
- Where QB hits come from (the play-call level's Q): no column holds them.
- The play-call level's slices: spikes (a forward pass by rule) and aborted snaps have no slice (O3 in `rules-level.md`).
