# the rules level RULES AUDIT - what the model assumes vs what the 2026 rule book says
Source: 2026 Official Playing Rules (pasted by reviewer 2026-10-26). The book covers 2026 only; the data is 2019-2025.
Any rule the book shows as changed (marked 2026 change, or a format that may differ by season) is a RECORD CHECK per season, never a fact for older seasons.
Verdicts: HOLDS = the model's assumption is the rule. REPLACE = the rule is different; the model must carry the rule.

## Clause 1: "Every game is 60 minutes"
A1 60 minutes of game clock, four 15-minute quarters (4-1-1) ........................ HOLDS for regulation
A2 No time after 60:00 ........ REPLACE: regular-season overtime, one 10-minute period, can end tied (16-1-3); 2 timeouts each (16-1-3e)
A3 Every play uses clock ...... REPLACE: untimed downs: Try after every touchdown (11-3-1), quarter extended by an accepted defensive foul or a double foul (4-8-2), fair catch kick (10-2-5). Plays happen at 0:00.
A4 Clock time is all spent on snaps .. REPLACE: clock runs on kick returns once the ball is touched (4-3-1); 10-second runoffs remove time with no play (4-7-1, 4-7-4, 15-5-2); replay can restore time (15-3-9)
A5 Clock runs the same all game ...... REPLACE: after the two-minute warning of the first half and inside the last 5:00 of the game, the clock waits for the snap after out-of-bounds (4-3-2a); the two-minute warning is a stoppage (3-41). These windows are drawn from the rules, not chosen by fit.
A6 Pace has a floor .................. HOLDS as a bound: 40-second play clock after a play, 25 after stoppages (4-6-1, 4-6-2)

## Clause 2: "The ball changes hands after every score or stop"
A7 After a score the other team gets the ball .. REPLACE: kickoff to the team scored on after a Try or field goal (11-3-4, 11-4-6); after a safety the team scored on kicks to the scorer (11-5-2); when the safety is scored against the side that just gained the ball on a return or interception, before its own snap, that kick returns the ball to the side that just had it (11-5-1(b))
A8 Every change of hands comes with an offensive drive .. REPLACE: an interception, fumble or kick returned for a touchdown scores with no snap by the scorer, then the scorer kicks off (11-3-4, 6-1-1a), so the team that lost the ball gets back-to-back drives
A9 The kicking team never keeps the ball .. REPLACE: onside kick recovered by the kickers (6-1-6, 7-3-1e); kickers recover a free kick in the landing zone (6-1-4c, 7-3-1e); kickers recover a muffed punt beyond the line after the receivers touched it (9-3-2 Item 1, 7-3-1d)
A10 One change of hands per down .. REPLACE: two or more changes of possession inside one down (3-35-3, 14-5-2): a turnover fumbled or intercepted back returns the ball to the team that lost it, or a turnover whose return ends in a touchback awards it back (8-7-3 Item 4(a), 11-6-1)
A11 Halves and overtime alternate .. REPLACE: second-half kickoff goes by the pregame toss choice (4-2-2), overtime by a new toss (16-1-2): back-to-back drives across halftime and into overtime are by rule. A drive continues across the end of the 1st and 3rd quarters (4-2-3), so no possession is split at a quarter.

## Clause 3: "Four downs to gain ten"
A12 Ten yards, four downs, every series .. REPLACE:
  - line to gain is the goal line when it is under 10 yards away ("and goal") (3-8-3)
  - a down cancelled by a penalty is not charged (3-8-4); defensive fouls give automatic first downs (14-1-2 Item 5); loss-of-down fouls (14-1-2 Item 2); first-and-25 after a dead-ball foul by an offense that just made a first down (14-4-9 Item 1)
  - the kickers get a new series by recovering a free kick or a punt touched by the receivers (7-3-1d,e)
  - a punt blocked and recovered behind the line keeps the same series (9-3-1 Item 1)
  - a Try is one untimed scrimmage down outside any series (3-40)
  - a spike is a legal forward pass to stop the clock (8-2-1 Item 3), so it is a charged down and a throw

## What this breaks in the seven sentences (the sentence is built from measurement in N7; no reviewer decision)
O1 the rules level sentence: clause 1 needs overtime and untimed downs; clause 2 needs the five licensed exceptions A8-A11; clause 3 needs "and goal", penalty series and kicking-team recoveries.
O2 the game level "plays": the rules give three different counts (charged downs, all snaps including those cancelled by penalty, and Tries). the game level must name one, and the team level's S must be the same count split by offense.
O3 the play-call level slices: "D dropbacks, H handoffs, K kneel-downs" has no slice for spikes (a forward pass by rule) or for snaps that never become a pass or handoff (a muffed snap, a fumble before the throw). As written, D + H + K does not add up to S. Either spikes join A (and the position-group level's T) or a slice is added.

## Record checks (each reads its columns from disk first; each check shown to fail on an injected fault before its PASS counts)
R1 Possessions: count back-to-back possessions by licensed cause (halftime, overtime start, return or defensive touchdown, kicking-team recovery, two changes in one down incl. touchback award, safety against the side that just gained the ball before its own snap); "other" listed one by one, never filled. [blocks O1 clause 2]
   READ 2026-10-26 (raw files, outside record.py): 36348 possessions, 1676 games; back-to-back 1506 = halftime 824 + overtime start 38 + other side scored 428 + kicking team recovered 202 + two changes in one down 11 + safety on the side that just gained the ball 3; unexplained 0. Closed 2026-10-26: overtime start has an injected case (check_possessions.py, 24/24); record.py loads the safety column; own-kickoff recovery is read through record.raw_frame by check_possessions.py.
R2 Clock: runs as clock-check.md (v16, check_clock.py). The clock identity first written here is retired: summing clock changes into parts equals the total by construction, so it cannot fail. [O1 clause 1; the game level's because]
R3 Rule windows: snaps and seconds per snap inside vs outside the last 2:00 of the first half and the last 5:00 of the game, per season. [the game level map split]
R4 Series: share of series that are "and goal", started by penalty, or started by a kicking-team recovery; snaps cancelled by penalty; Tries. [O1 clause 3; O2]
R5 Plays definition: three counts per game (charged downs, all snaps, Tries) and how far apart they are. [O2]
R6 Slices: per team-game, (dropbacks + handoffs + kneels) vs snaps, with spikes and aborted snaps counted separately; the gap must be printed, never folded. [O3]
R7 Rule changes across 2019-2025: per season, kickoff touchback rate and average drive start after kickoffs, onside tries and recoveries, overtime games and possessions per overtime. Any season break means links fit across those seasons are tested by season before use. [every level that uses field position or overtime]

## Roadmap (status 2026-10-26), one chain each, sentence and blank named
DONE  the rules level clause 2 (check_possessions.py: 1,506 of 1,506 back-to-back possessions by rule)
DONE  the rules level clause 1 (runs as clock-check.md v16, check_clock.py)
DONE  the rules level clause 3 (runs as downs-check.md, check_downs.py)
OPEN  the game level P (rule windows: R2's D2 read, printed, not graded)
OPEN  R5 + O2 -> the game level P (which count "plays" means: settled at the game level by measuring all three counts)
OPEN  R6 + O3 -> the play-call level D,H,K (slices add up: measured at the play-call level)
DONE  per-season rule values measured (measure_season_rules.py to rules-module.md; out/season_rules.csv)
Book: every article cited here is the 2026 rule book's (rules/nfl_rulebook_2026.pdf, sha 144cec5bffd2, from https://static.www.nfl.com/image/upload/fl_attachment/league/tqivdkzt9mu6wdgsh1ku.pdf); each season's own book is read by measure_season_rules.py, so a 2019-2025 count cites the 2026 numbering; measure_season_rules.py has measured each season's values beside the quoted rules.
