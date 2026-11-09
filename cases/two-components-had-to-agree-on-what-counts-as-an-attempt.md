# Two components had to agree on what counts as an attempt

**The surprising result.** The game engine and the slate kit both count a team's pass attempts and carries per game from the same nflverse data, and on first comparison they disagreed on 467 of 3,352 team-games. Neither was wrong. They were counting different things, and no one had written down which.

**Finding the definition, in three steps, each measured (2026-11-05).**
1. *Universe.* The kit's facts are built from the weekly stats file for the positions it prices - QB, RB, WR, TE (`facts.load` filters to `SKILL_POSITIONS`). The engine counts every snap the team ran. Restricting the engine side to the kit's universe took the disagreement from 467 to 154 team-games; the difference was 289 fullback carries, 51 punter passes and a scatter of defenders', linemen's and kickers' snaps across six seasons.
2. *Season type.* The kit's facts are regular season only; the engine's record includes the postseason. Restricting to the kit's own team-games took 154 to 2.
3. *The last two rows.* 2024 week 15, HOU, one carry; 2025 week 2, PIT, one attempt. Both were read at the play level. HOU's is a fake-punt run by Ogunbowale on a play nullified by a foul (`no_play`, `rush_attempt = 1`); PIT's is the Rodgers intentional-grounding row (`no_play`, `pass_attempt = 1`) - the same play the downs check pins as case P9. The stats file counts an attempt or a carry on a nullified play when nflverse flags one; the engine's events type those rows as fouls. Adding that clause took 2 to 0: 3,200 of 3,200 regular-season team-games equal.

**The definition, as it now stands in the acceptance criteria** (`acceptance-criteria/engine-to-kit-handoff.md`, section 1): attempts = snaps of kind pass or spike, plus accepted-foul rows carrying `pass_attempt = 1` that are not sacks; carries = snaps of kind run, scramble or kneel, plus accepted-foul rows carrying `rush_attempt = 1`; two-point tries excluded; counted only where the ball-handler's stats-file position is QB, RB, WR or TE; regular season; team codes normalized. `checks/reconcile_root_counts_by_position.py` exits 1 unless every team-week is equal.

**Why it matters for the join.** The kit's root draws are the quantity its player shares are shares of. If the engine handed over whole-team volume, every share below it would be shrunk by the fullback's and the punter's snaps - a bias no downstream check would name. Agreeing on the definition before any draw crosses is what makes the later comparison a comparison.

**A limit found by the same work.** The engine writes no `pass_attempt`/`rush_attempt` on its own foul rows, so the handoff file built from generated games cannot apply the nullified-play clause; it says so in its manifest, and on the play-by-play record that clause moved 2 team-games in 3,200. Giving the engine those two flags is recorded as the engine's own change.

**What this shows and what it does not.** It shows a metric mismatch traced to its definition rather than tuned away, with the residue read at the row until it was zero. It does not show that the engine's volumes are *right* - only that they are counted the same way the kit counts them; the engine's generated attempts and carries (33.0 and 27.2 per team, 30 draws of 2024 week 15) have not been judged against anything yet.

**Roles.** I set the rule that one unequal row stops the handoff until its definition is reconciled in writing, and ran each step; the agents wrote the comparison and the play-level reads against that rule.

**Artifacts.** `acceptance-criteria/engine-to-kit-handoff.md` section 1 · `checks/reconcile_root_counts_by_position.py` · `slate-kit/facts.py` (lines 161, 289: the stats file as source of record; `pbp_box_crosscheck`) · `product/record.py` `events()` (the snap kinds) · `out/handoff/root_draws_2024_w15.manifest.json` (the counting rule and its omitted clause).
