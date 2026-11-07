# the predecessor-index mismatch: a 0-based index handed to a 1-based program, silent for eight revisions

Record: the version-3 revision notes (revisions 9 to 13), summarized in sections 2 to 5; the code at revisions 12 and 16 is in this folder. Replay: `bash ../../run.sh` stage 3.

## 1. Task
"Every game is 60 minutes; the ball changes hands after every score or stop; four downs to gain ten. This game should have about P plays between both teams, more or fewer than these teams' usual, because ___." The goal, in my words from Oct 24: "find the goal for each layer, how the layers work together to accomplish the final product, against real NFL rule conservation. For each thing that looks like it's mostly chance, go a layer deeper and see what it's composed of. If we can eliminate the noise, like ensuring apples to apples for player health, and they all rest on the same rolling average, it makes it a lot easier to find where the variance is; then we can make progressively more complex by adding in one variable at a time." Not a player's over/under price. Not a score or winner pick.
The decision at revision 8: twelve sub-models had fitted and the construction tests passed. Do those passes justify treating the fitted season chain as a measurement?

## 2. Inputs (what was knowable at revision 8)
- Twelve construction tests on a generated league, all PASS; the quality gate end to end on injected draws.
- Revision 11 notes: the sampler had run without complaint on a mis-linked chain.
- The generated league's ids were season-prefixed, so 160 of 168 pairs had no predecessor (`revision-12-fix-without-regression-test/tests/synth.py`).
- No fit had reached grading. No forecast had been issued.

## 3. Reference answer
The passes justified one claim: the chain runs. They did not justify the product's claim that the chain was linked, because no check compared a predecessor code with the player and season it should point at. The grounded status at revision 8 was "unverified", not "passing". Acceptable alternative: stop at revision 8 and build the predecessor check before any further fit. Not acceptable: reading persistence estimates from those fits.

## 4. Rubric
| # | Criterion | Why (from the play-by-play record) |
|---|---|---|
| F1 | A check counts only where the test data can express the fault | revision 11 notes: the synthetic league could not see the defect, since a mis-linked pair's state there is just another draw from the same prior |
| F2 | A translated code is checked for meaning, not only range | revision 10 checked every index was in range and missed it; revision 11 added the check that each predecessor code resolves to the same player's earlier season |
| F3 | An unexplained failure gets a check before a fix | revision 10: the failing observation index named a row but not the term, so a preflight was built before any fix |
| F4 | A fix invalidates everything fitted under the defect | revision 11: every fit made under the earlier layout was declared unusable and deleted |
| F5 | The defect's class gets an injected fault that must fail before the suite counts | revision 13: an injected 0-based predecessor is refused by all six programs (the oracle test, run by stage 3) |
| F6 | The suite is hashed, locked, and runs before real data | revision 13: a quality-quality gate run whose test-suite hash differs from the lock is stopped before real data |

## 5. Graded examples
- **A. Plausible failure, the revision 8 decision.** "Twelve tests pass, the quality gate runs, the sampler converges: accept the chain." FAIL on F1, F2. This is the decision that was made, for eight revisions.
- **B. Insufficient evidence, the revision 9 nan.** Every sub-model failed at one observation; the failing index was the same across chains and starts, so the nan was data-determined. UNKNOWN: build the check. Passes F3.
- **C. Sound answer, revision 11.** The preflight named pair 996 and predecessor 497; 497 was the pair coded one before the true predecessor; the shift was found, the layout version stamped, the fits deleted, the meaning check added. PASS on F2, F3, F4.
- **D. Third order, revision 13.** The league rebuilt to carry every irregularity the code branches on; a zero on an unguarded branch refused; the injected fault for the predecessor-index mismatch's class; the suite locked. PASS on F1, F5, F6.
- **E. Plausible failure, the revision 16 handoff.** The revision 16 handoff did not run the suite or the quality gate and expected 16 of 16 unchanged. FAIL: two failures on first run (`sample_gain` signature; `gain_sack` INSUFFICIENT_DATA). A prediction is not a result until the run that tests it is in the play-by-play record.
- **Replay (2026-11-05):** revision 12 14/14 PASS, no injected fault present. revision 16: `PASS oracle: ... an injected 0-based predecessor is refused`; 2 failures unrelated to the predecessor-index mismatch, left as found.

How I knew the passes were wrong: "Over 8 revisions, 2 programs couldn't agree on if counting started at 0 or 1. Every check passed silently because the model was only compared to itself." The grain was the problem: "continuing separating the convolution into more granular data that composes the higher level grain that is smoothing the hidden errors." What was done first, and refused, by the standing rules: "Every lie, blatant or by omission, is resolved before a change is tested; never test an incomplete change. Fail = closed." Every fit made under the defect was deleted and no decision was read from them.

## 6. Revision record
- The fixture exposed the rubric gap: F1 did not exist before revision 13. incident-derived rules clause 7's second clause (a check compares the product against something other than itself) was added from this incident.
- Range checks were not enough: F2 split "finite and in range" from "resolves to the right thing".
- The before-fix state cannot be replayed: no copy of revisions 1 to 10 exists; the revision notes are summarized above.
- revision 16's two failures are open and are not claimed fixed.
- The oracle league did not carry into version 4; it lives here, in `revision-16-with-regression-test/tests/`.
- Calibration: not done. No reviewer other than the author has graded A–E against this rubric.
