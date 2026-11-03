# R2 TARGETS v16 - clock (L0 clause 1; L1 P's clock), set by the falsifier before any R2 code. Supersedes 7166ab748789 (v15), aa2b34dca092 (v13), fabe2e2bc91a (v12), 0faae8913144 (v11), c6b5d696910c (v10), 49e0af3f888d (v9), 0fe215ec05d0 (v8), c02e5f4ccc07 (v7), e733cf9b12d7 (v6), 63bf80068c13 (v5), 8490a5dee69e (v4), 00745daf5cce (v3), 90949d61217f (v2), 7a2325413f82 (v1).
Every target rests on an article of the 2026 rule book, named on its line; none is graded as an exact law (see Laws). Seasons 2019-2025 read per season (R7).
No cutoff, pass rate or tolerance is set in advance: v1-v4's 95%, 99%, 99.5% and +2 s had no rule or measurement behind them and are withdrawn.

## Retired
v1 C1-vs-C2 -> NOT TESTABLE: drive clock == play stamps (99.8% of drives; time of possession == start - end clock on every same-quarter drive, 2019).
v2 PC, P4, P5 -> NOT TESTABLE: play_clock is 0 on every scrimmage snap in all six seasons (measured 2026-10-26); a filled default, not a reading.
Warning-row check (PL1b's 'a warning row must sit inside the placed interval'; READ1) -> NOT TESTABLE 2019-2025: no row is the warning itself (measured 2026-10-26, case-insensitive search: 2 mentions, both inside other plays' text, 2019_08_NYJ_JAX seq 1906 and 2019_14_BAL_BUF seq 1941); placement by the quarter clock (3-41) is the only source.
16-1-4(h) second and fourth postseason overtime periods -> NOT TESTABLE 2019-2025: no game reached them (7 postseason overtimes, all quarter 5); a row past quarter 5 reads UNKNOWN; no quarter number is assumed for them.
Not a check: summing game-clock changes into parts equals the total by construction.

## Instruments (names read from the header before use)
G = game clock at each snap (game_seconds_remaining), recorded in whole seconds (measured, every value, six seasons): each dG carries 1 s of resolution.
Scrimmage snap = every down that starts with a snap (3-8-1a, 3-29): pass, run, kneel, spike, punt, field goal attempt. Tries are excluded (untimed, 11-3-1).
W = wall-clock time at the start of each play (time_of_day). Both recorded formats parsed; an interval's resolution is the coarser of its two W stamps plus G's 1 s (v13).
E = wall-clock time the play ended (end_clock_time).

## Counting: three counts, never merged, never a range
Every check runs on every season where its instrument is present at all, and reports per season its counts under the names its own line gives (L1: WITHIN REAL TIME / WITHIN RESOLUTION / FASTER / UNCHECKED; D3: WITHIN 40 / OVER 40 / UNCHECKED):
  the intervals checked that stay inside the rule's bound;
  the intervals checked that fall outside it, each listed with its size and its rule-licensed cause where the record names one;
  UNCHECKED, intervals missing an instrument, with counts by play type and by class, so the gap is described, not guessed.
No count is folded into another, and no verdict word is attached.
Plant and negative runs print only the change they cause, never season totals.
v9 holds no law the record can grade exactly (see Laws), so every check reports its three counts and no verdict word.
FROZEN at v10: no further edit before R2 runs, unless a plant fails or a rule article contradicts a line; either reason is printed with the edit. v13 adds a third ground, stated as an addition: a measured instrument property (a resolution read from disk), labeled when found after counts were seen.
v11 edit, reason printed: plants PL6 and PL1b failed in the v10 run (2026-10-26); frozen again at v11 on the same terms.
v12 edit, reason printed: 4-3-2e, 4-5-3, 4-5-5 and 15-5-1 contradicted line 28's STOP list (fouls outside the late windows, injury and Referee's timeouts, replay review restart the clock as if they had not occurred); found by reading the articles before any class-based count; frozen again at v12 on the same terms.
v13 edit, reasons printed: (1) instrument: the game clock is recorded in whole seconds (measured 2026-10-26, share 1.0000 in six seasons), so every dG carries 1 s that v12 left out of L1's margin; found after the v12 L1 counts were seen; those counts stay on record (r2.py 51fc3bd2fe8e, out/r2_faster.csv ac10e6e09b28). The falsifier's 2 s split prediction missed in 2019 and 2020 and is closed; the margin rests only on the two measured resolutions. (2) the v12 run printed UNKNOWN for an injury after the two-minute warning and for out of bounds in a postseason overtime; 4-5-4 and 16-1-4(h) cover both. Frozen again at v13 on the same three grounds.
v15 edit, reason printed: plants PL9 and NEG9 failed in the v13 run; PL9 pinned to a real case (13 postseason-overtime out-of-bounds snaps, all passes, 12 clean); NEG9 tests that no period number is assumed; READ1 closed as a text match. Frozen again at v15 on the same three grounds.
v16 edit, reason printed (third ground, a measured property of the record): the record logs no two-minute warning row; the warning-row check is retired. The falsifier's prediction that only seq 1906 would match missed (seq 1941 also mentions it) and is recorded. Frozen again at v16 on the same three grounds.

## Interval rule class (consecutive scrimmage snaps i -> i+1, same quarter), from play i AND every row recorded before snap i+1
STOP (the clock waits for the snap, 4-3-2): incomplete pass (4-4f); out of bounds after the two-minute warning of the first half, inside the last 5:00 of the game, or inside the last 5:00 of a regular-season overtime period (4-3-2a, 4-4c; overtime runs on fourth-period timing, 16-1-3e), or in postseason overtime inside the last 2:00 of the second period or the last 5:00 of the fourth (16-1-4(h)); score, touchback or try (4-4d, 4-4a); change of possession (4-4i, 4-3-2a(1)); a foul after the two-minute warning of the first half or inside the last 5:00 of the second half or overtime, or an offensive foul before the snap in the fourth period or overtime (4-3-2e(1)-(3)); a charged team timeout (4-5-1); an injury timeout after the two-minute warning, charged to a team or excess (4-5-4); the two-minute warning (3-41, 4-4h), placed by the rule from the quarter clock: snap i with more than 2:00 left in the second or fourth quarter, a regular-season overtime period (16-1-3e), or the second or fourth postseason overtime period (16-1-4(h)) and snap i+1 at 2:00 or less, whether or not a row records it.
PARTIAL (the clock stops, then starts as if the stoppage had not occurred): out of bounds before those windows (4-3-2a); a foul outside the windows in STOP (4-3-2e); an injury timeout before the two-minute warning (4-5-3); a Referee's timeout (4-5-5; the record does not log these); a replay review, after which the clock follows Rule 4-3 (15-5-1). Where play i or a row before snap i+1 carries a STOP event, STOP stands.
RUN: none of the above (4-3-2).
ADMIN (4-6-2), a flag independent of the class: change of possession, charged timeout, two-minute warning (placed as above), period end, penalty enforcement, replay. Intervals without ADMIN carry the 40-second play clock (4-6-1).
Every interval gets exactly one class; none matching prints UNKNOWN.

## Laws: none the record can grade exactly (v9). Both clock relations carry rule-licensed exceptions the record does not always log.
L1 read, not a law (v9): the game clock can fall faster than real time by rule: a 10-second runoff takes 10 s off with no play (4-7-1 Item 1, 4-5-1 penalty, 4-5-4 Note 3, 4-7-2, 4-7-4, 15-5-2), and the officials may correct the game clock before the next snap (4-1-4), which the record does not log. Four counts, never merged (v13): WITHIN REAL TIME (dG <= dW); WITHIN RESOLUTION (0 < dG - dW <= resolution: the two clocks cannot tell these apart); FASTER (dG - dW > resolution), each listed with dG - dW and whether play text between the snaps names a runoff (licensed) or not (a correction by the officials or a record error, not told apart; none is called a violation); UNCHECKED.
L2 withdrawn as a law (v7): 4-6-1 limits the play clock, not the wall clock, and the play clock stops and keeps its time for any interruption before the snap, including Referee's timeouts for a measurement, a pileup, spotting the ball, a conference or equipment (4-6-3, 4-5-5), which the record does not log. A wall-clock gap over 40 s after the play ends keeps the rules whenever such an interruption occurred. Corrected after the frozen 2023 counts were seen; grounded only in 4-6-3 and 4-5-5; the counts stay frozen.

## Reads (distributions printed, not graded)
D1 (4-3-2, 4-4) dW - dG for RUN, PARTIAL and STOP intervals, per season: count, median, 90th and 99th percentile. The rules say RUN sits at the clock operator's lag (4-1-4) and STOP above it; the read is how far the classes separate (share of RUN intervals above the STOP median, share of STOP intervals below the RUN 90th percentile). The RUN distribution is the measured operator lag; nothing is assumed for it.
D2 Seconds per snap by class and by rule window (last 2:00 of the first half, last 5:00 of the game; A5), per season (R7).
D3 (4-6-1, 4-6-3) Intervals without ADMIN, in seasons where E is present: W(i+1) - E(i), three counts: WITHIN 40 (<= 40 + resolution); OVER 40, each listed with its size (an unlogged play-clock interruption or a record error; the record does not tell them apart, so none is called a violation); UNCHECKED, by play type and class.

## Plants, pinned to plays, read row by row before any count
PL1 2019_01_IND_LAC seq 3209 -> 3230 -> RUN, no ADMIN, dG = dW = 26 s: the wall clock shows no stoppage. (v5's 'the two-minute warning follows' was the falsifier's unread guess; withdrawn.)
PL1b the rule places the two-minute warning of 2019_01_IND_LAC q4 from the quarter clock (3-41): the interval whose first snap has more than 2:00 left and whose next snap has 2:00 or less, here the interval ending at seq 3209 (snapped at 2:00) -> STOP, ADMIN (4-6-2c), rows printed. The record has no warning row in this quarter (read in the v10 run); placement does not wait for one. The record logs no warning row (v16); the quarter clock is the only source.
PL2 2019_01_IND_LAC seq 3230 -> 3251: run in bounds, no stoppage -> RUN, no ADMIN, dG = 24 s.
PL3 2019_01_IND_LAC seq 3297 -> 3340: incomplete pass, then the LAC timeout row before the next snap -> STOP, ADMIN (the timeout row is read).
PL4 builder finds and pins an out-of-bounds run before 2:00 of the second quarter -> PARTIAL, rows printed.
PL5 builder finds and pins a 2023 incomplete pass followed by a snap with no ADMIN row -> STOP, no ADMIN, W(i+1) - E(i) printed.
PL6 the 16 intervals whose play text names a runoff (counted in the v10 run), rows printed -> WITHIN REAL TIME: the runoff takes off time the clock would have run but for the offense's act (4-7-1 Item 1), and the stoppage around it costs real time, so it does not make the interval faster than real time; any that read FASTER are listed.
NEG1 a copy with one W stamp moved 30 s earlier: L1 lists that interval under FASTER, not licensed.
NEG2 a copy with PL2's play relabeled incomplete: it reads STOP, not RUN.
NEG3 a copy with PL5's E moved 30 s earlier: D3 lists it under OVER 40.
NEG4 a copy with one interval's E deleted: D3 moves it from WITHIN 40 or OVER 40 to UNCHECKED, and those two counts drop by exactly one between them (printed as changes only).
NEG5 a copy with PL1b's next snap set to 2:01 on the quarter clock: that interval no longer carries the two-minute warning.
NEG6 a copy with one PL6 interval's real time shortened until dG > dW: it reads FASTER, licensed by runoff; the same copy with the runoff text removed reads FASTER, not licensed.
PL7 builder finds and pins a 2023 first-quarter run in bounds carrying an accepted foul, followed by a snap with no other stoppage row -> PARTIAL (4-3-2e), rows printed.
NEG7 a copy with PL7's quarter set to 4 and its clock inside 5:00 -> STOP (4-3-2e(2)).
PL8 builder finds and pins an interval whose play text names an injury after the two-minute warning -> STOP (4-5-4), rows printed.
NEG8 a copy with PL8's snap clocks moved above 2:00 in the same quarter -> PARTIAL (4-5-3).
PL9 2019_18_BUF_HOU seq 4363 -> 4392: a pass ending out of bounds in the first period of a postseason overtime, no other event -> PARTIAL (4-3-2a; 16-1-4(h) sets no window in that period), rows printed. 12 clean cases exist; all 13 such snaps are passes.
NEG9 a copy with PL9's quarter set to 6 -> UNKNOWN: no game in 2019-2025 reached a second postseason overtime period (every overtime is quarter 5), so the record cannot show which quarter number marks it; none is assumed.
PL10 2023_01_ARI_WAS seq 77 -> 102 (FASTER by +0.330 s in the v12 run) -> WITHIN RESOLUTION.
NEG10 a copy with G's 1 s removed from the margin: PL10 reads FASTER.
READ1 closed: the record logs no two-minute warning row (see Retired); there is nothing to search.
EXPECTED before the v13 run (the builder's 'still FASTER' column, same margin): FASTER 2019 267 | 2020 238 | 2021 258 | 2023 356 | 2024 349 | 2025 321; any difference means code and text disagree.

## Seen before the plants passed (2026-10-26, failed plant run, R2_TARGETS.md 63bf80068c13)
2023 L2 (now D3: HELD reads WITHIN 40, BROKE reads OVER 40): HELD 23659, BROKE 4060, UNCHECKED 564, N/A (ADMIN) 10019. Frozen: the L2 definition is not changed after this sight; the rerun must reproduce these four exactly, or print which edit in v6, v7 or v8 moved each one (v8's rule placement of the two-minute warning adds ADMIN intervals and is expected to move them).
