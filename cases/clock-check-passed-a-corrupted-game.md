# A passing check gave an incomplete answer

**The surprising result.** On 2026-11-05 a copy of the game engine was changed so that the game clock keeps running after an incomplete pass (Rule 4-4f says it stops). Sixteen games were generated from that copy. The clock check - the check that classifies every stretch between snaps and compares the game clock against the wall clock - accepted all of them: every stretch read WITHIN REAL TIME, zero UNCHECKED. The stopped-clock check refused them. One check passed a game that broke a rule; a second check, written for a different question, caught it.

**Why the first check passed.** The clock check asks whether the game clock moved no faster than real time, stretch by stretch, within the stamps' resolution. The changed engine moves both clocks together: when it wrongly runs the game clock, it runs the wall clock with it. Against that fault the comparison is blind by construction. The acceptance criteria had said so in advance, on 2026-10-26, before the generated-game test was run (2026-11-05): "P3 the game clock kept running after an incomplete pass: the stopped-clock check fails (the clock check alone would pass it: both clocks move together)" (`acceptance-criteria/engine-legality.md`, section 5).

**Why the second check caught it.** The stopped-clock check asks a narrower question with a bound: on a stretch the rules say is stopped (an incomplete pass, out of bounds late, a score), the game clock may fall by no more than the plays run on it plus one second. On the corrupted games it checked 663 STOP stretches and 246 fell by more, the first at 2024_15_ATL_LV after an incomplete pass; the clock check read all 1,777 stretches of the same games WITHIN REAL TIME and its verdict line stayed PASS.

**The acceptance decision.** Quality gate 1 of the generated-game acceptance (`run.sh` stage 5) requires two things on the same path: unmodified generated games must pass every line, and each injected violation must turn exactly its own line to FAIL. A violation that crashes the run, or that fails a different line, is NOT DETECTED. On the 2024 week 15 fixture (30 draws of 16 games, the accepted engine):
- acceptance: all seven required verdict lines passed on every control draw (30 of 30);
- coverage, draw 0, printed beside the zeros and not part of the pass: 2,101 clock stretches, 0 UNCHECKED; 809 STOP and 299 PARTIAL stretches checked by the stopped-clock check; 340 possessions; 3,104 down items judged and 324 pairs not judged (a change of team, a break, or a possession ending on its first snap);
- P3 failed the stopped-clock line and only that line; P1, P2 and P4 each failed their own line and no other.

**The two verdicts, from the P3 run's log (`out/handoff/stage/gate1_P3.log`, 2026-11-05; the last line reads FAIL because a injected run must fail its named line):**

```
clock check, all stretches:     game level {'WITHIN REAL TIME': 1777}
stopped-clock check:            checked {'no-play downs made snaps': 80, 'STOP checked': 663, 'STOP failed': 246, 'PARTIAL checked': 246} | violations 246 [('STOP', '2024_15_ATL_LV', 5, 6, 41.0, 9.0, 'incomplete 4-4f', 32.0, 2024, 1, True, 'incomplete 
=== verdict (engine-legality.md section 4; coverage above) ===
  possessions unexplained 0: PASS
  clock FASTER not licensed 0: PASS
  clock UNCHECKED 0 (engine stamps every snap): PASS
  downs OTHER 0: PASS
  downs UNCHECKED 0: PASS
  stopped clock: no STOP stretch falls more than the play plus 1 s: FAIL
  season rule: kickoff touchback spot == quoted (30): PASS
GATE 1 ALL LINES PASS: FAIL
```

**What this shows and what it does not.** It shows that acceptance here rests on more than one check, that the checks' blind spots were written down before they were tested, and that the test is the detection of a known fault through the real acceptance path - not the absence of failures. It was verified in the consolidated repository on 2026-11-05 (the full `run.sh`, stages 1-5). It does not show reproduction from a clean clone (not yet run), anything about the engine's forecast accuracy (no claim is made), or anything about the October 31 candidate engine whose refusal record was deleted in the cleanup; this is a separate demonstration on the accepted engine.

**Roles.** I set the acceptance criteria and the rule that a detection counts only on its named line, ruled on what could be deleted and what had to stay, and ran every verification on my machine; the agents wrote the scripts against those criteria. The checks accepted or refused the result, not the agents.

**Artifacts.** `acceptance-criteria/engine-legality.md` (sections 4-5 written 2026-10-26; Status 2026-11-05) · `checks/inject_generated.py` (the four run-time changes, each printed) · `checks/check_generated.py` (the record checks' rule functions on a generated draw; record-only sections printed NOT APPLICABLE) · `checks/test_gate1_plants.py` (the standing test) · `product/check_clock.py`, `product/clock_check.py` (the two checks) · `out/handoff/stage/gate1_P3.log` (the P3 verdict) · `run.sh` stage 5 · README, "Two components, two entry points".
