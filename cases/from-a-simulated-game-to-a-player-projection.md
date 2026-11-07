# From a simulated game to a player projection

The lead case. Two components that were built separately, the point where they met, what the join had to preserve, and what one combined run produced. The three earlier cases are parts of this one and are linked where they belong.

## The question

Start where an argument on Sunday starts: *if Las Vegas throws more in this game, where does that show up in the quarterback's projection?* To answer it you need three things to be inspectable: how many times the team throws (team attempts), what share of those throws this quarterback gets (player attempts), and which simulated version of the game you are looking at (the source draw). This case follows one such change — Las Vegas's attempts in one simulated game raised from 36 to 60 by hand — from the simulated game to Desmond Ridder's projected attempts, and ends with the command that reproduces it from a clean checkout. The pieces were built separately; the question is what joining them had to preserve, and what the join does and does not yet show.

The design came out of pushing back on the simulation until it could be checked against the real pool. Three asks from the chat on 2026-09-30, five weeks before the adapter existed, in Cameron's words, spelling corrected and nothing else:

> I'm not worried about week 4 I'm worried about creating the appropriate models. With the data on my local slate_kit, what connections can I simulate realistically? Where when one thing happens another thing usually does too, and another thing does not happen.. kind of like anchoring for inferences and counterfactuals
>
> Ok but you just spent 20+ minutes simulating - can we save that to my current slate kit script suite and run the selections the slate kit makes against the realistic pool of players? I'd download the script to the same folder I have, and it would create a new section of information for each proposed line up to show if it's realistically profitable vs the pool of data
>
> Ok so I just want to get back to first principles. Do we have apples to apples data sets across the different seasons? what data is simulated and what isn't? Are they using realistic information by attaching to averages and both extremes within the granularities relevant to the rule book? if anything was normalized, did we normalized stats from early seasons to fit later variation/numbers that show in later seasons, possibly from trend differences or rule changes? and anything else

These questions led to three checks in the repo. One traces a simulated team total into a player projection, one tests the rules the simulator is supposed to follow, and one checks that both sides count the same thing.

| Original ask (2026-09-30) | What the repo demonstrates today | What remains open |
|---|---|---|
| *Run the selections the slate kit makes against the realistic pool of players* | The kit used the engine's team-volume draws in a named player's calculation on the Week 15 fixture. The card could have named the correct source file while the player calculation silently used its old input, so one source draw was changed by hand: LV draw 0 went 36 → 60 attempts, Ridder's traced draw went 6 → 10, and no unmapped column of his attempt calculation changed. The full replay separately verified kit-mode parity against the pre-adapter code. `checks/demo_w15.py` (clean checkout, ~100 s); `checks/run_handoff.sh`; `cases/evidence/`. | Whether the joined forecasts improve, and whether the lineups the kit selects perform better against the field or prove profitable — the ambition in the original ask. `acceptance-criteria/forward-window.md`, design only. |
| *What connections can I simulate realistically?* | All 30 fixture draws (16 games each) passed the applicable structural checks — possession changes, downs, the clock, the kickoff spot — and four injected violations failed on the checks named before the run. `checks/check_generated.py`, `checks/test_gate1_plants.py`; `acceptance-criteria/engine-legality.md`. | Whether the simulator gets game volume and the relationships between outcomes right; the checks cover the rules they name, not "breaks no rule". The engine's own acceptance still reads NOT ACCEPTED on plays per game. `acceptance-criteria/engine-vs-record.md`. |
| *What data is simulated and what isn't? Apples to apples across seasons?* | Attempts and carries reconciled across 3,200 team-weeks under the documented counting rules before anything crossed the boundary. Every engine-mode card names the draw file and its SHA. `cases/two-components-had-to-agree-on-what-counts-as-an-attempt.md`; the card's `root_*` columns. | Whether the seasons are comparable after rule and trend changes, and what the joined system's hold-out is — the engine and the kit treat 2022 differently. |

The transcript is the evidence of how the standard was set; the code is the evidence that it was met where it says it was met, and the third column is the work order (`WORK_ORDER.md`).

### Terms

- **Team attempts** — a team's pass attempts in one game. In the engine: dropbacks that ended as a throw, plus accepted-penalty plays recorded as a pass attempt, never sacks (the counting rule both components were reconciled to, 3,200 of 3,200 team-weeks). In the kit: the root cell `("F2 team attempts", TEAM)`.
- **Player attempts** — one quarterback's pass attempts in that game: the kit's `Q1 attempts` cell, drawn as his share of his team's attempts from his own history.
- **Source draw** — one simulated playing of the game by the engine. The Week 15 fixture holds 30 of them (`draw_id` 0–29); kit column *j* reads source draw *j* mod 30, so column 30 is source draw 0, and a change to source draw 0 is expected at the 67 kit columns 0, 30, 60, … and nowhere else.

## What each project could do

**The engine** (`product/`, `checks/`, `run.sh`) plays a game out play by play under the rules: sixty minutes, the ball changing hands after every score or stop, four downs to gain ten. For a given week it produces, per draw, how many plays each team ran, how many possessions, how many pass attempts and carries. Its ball-handlers are placeholders (`SIM-<team>-QB`): it forecasts the environment, not the people. Its acceptance is rule-based: a generated game that breaks a rule fails, and each rule check had to fail on a injected fault before its pass counted ([the clock check that passed a corrupted game](clock-check-passed-a-corrupted-game.md); [the regression test that needed data able to trigger the bug](regression-test-needed-data-that-could-trigger-the-bug.md)). Quality quality gate 1 of the handoff: 30 of 30 generated 2024 week 15 games passed every verdict line, and four injected violations (possession, downs, clock, touchback spot) were each caught on their own line.

**The slate kit** (`slate-kit/`) projects players for daily-fantasy pricing, from the team down: a team's attempts and carries, then each player's share of them from his own history, then yards per touch against the defense, down to a fantasy-point distribution. Its top-of-ladder number — team volume — came from the kit's own rate and a bootstrapped ratio. Its own grader scores every cell against five seasons of outcomes, and it is plain about what it finds: on the 2026-11-05 replay 24 of 39 cells were decision-qualified and 0 of 4 fantasy-points cells were.

## Where they met

The kit's root cells are `("F2 team attempts", TEAM)` and `("F2 team carries", TEAM)`. The engine produces exactly those two numbers per team per draw. So the handoff is one file per week — `out/handoff/root_draws_<season>_w<week>.npz` with its manifest — and one rule: in engine mode the kit's root draws are the engine's, expanded from K source draws to the kit's 2,000 columns by `j mod K`, and every other cell is drawn as before.

Before anything could be handed over, both sides had to mean the same thing by "attempt" and "carry". They didn't, until a definition was written down and measured: [two components had to agree on what counts as an attempt](two-components-had-to-agree-on-what-counts-as-an-attempt.md) — 3,200 of 3,200 team-weeks reconciled.

## What the adapter had to preserve

1. **The kit, when the switch is off.** With `SLATE_ROOT_SOURCE` unset or `kit`, nothing may change: not the card, not the graded rows, not the atlas or ladder.
2. **Provenance to the issued artifact.** In engine mode the card carries the source file, its computed SHA, the source draw count, the column count and the grading basis, with a root manifest beside it.
3. **Refusal by name.** A missing file, a SHA that doesn't match the manifest, a team with a game but no draws, a draw count the manifest and arrays disagree on, a file for the wrong week after a valid one was cached, a misspelled source — each refuses with its reason and issues nothing. No fallback to the kit's own root.
4. **The draw-count contract.** Column 30 of the kit is source draw 0; column 29 is source draw 29; both teams of a game, both terms.

## What the combined run produced

The harness is one command, `checks/run_handoff.sh`, writing a fresh run directory with a readable result and a full log per step. Run `20261105_220733`, verdict PASS ([evidence](evidence/handoff_20261105_220733/)):

- **Baseline, freshly made.** The pre-adapter kit code (`draws.py`, `cards.py` as saved at the rewrite) was run in an isolated copy on the same inputs the candidate sees, with the six replay outputs removed first so their presence afterwards proved fresh emission. The live project directory was hashed before and after and untouched.
- **A1, the card.** The candidate's kit-mode card for 2026 week 4 equals the pre-adapter card by column set, key set and value, NaN as a value, no tolerance.
- **A2, the replay.** The candidate's kit-mode replay in a second isolated copy, from the same snapshot, with the same recorded identity (git revision, kit code, resolved shared inputs): 192,330 atlas rows and 26,722 DK rows equal by key and value; `atlas.csv` and `ladder.csv` byte-identical; the kit's own grader, judged separately, nine cells UNCHANGED.
- **B, the trace.** Engine mode on the 2024 week 15 fixture, game ATL at LV. Kit columns 29, 30, 31 equal source draws 29, 0, 1 for both teams and both terms. Desmond Ridder's Q1 attempts cell received LV's root at the boundary — column 30 = 36 attempts, the engine's draw 0 — and his card row's mean equals the mean of the draws he consumed.
- **B2, the controlled change.** A deliberate change to one simulated input: the engine's LV draw 0 raised from 36 to 60 in a copy of the fixture, with the columns expected to move (every kit column j with j mod 30 = 0, 67 of them) named before the run. The team root moved at all 67 and nowhere else; Ridder's attempts moved at mapped columns only; the value received at column 30 was 60, and his drawn attempts at that column went from 6 to 10. That is the environment reaching the player.
- **C, the refusals.** Four isolated injected faults plus the cached-wrong-week and typo cases, each refused by name with no card artifact.

Run `20261105_210053`, the attempt before it, is kept as it ended: FAIL on two assertions that required the replay to *change* the bytes of `atlas.csv` and `ladder.csv`. The files are replay outputs (`draws.py:260–261`) that the copies already held with identical bytes, so a correct rewrite was invisible to a hash comparison. The harness's error, corrected by starting from absent files; everything else in that run had already passed. Earlier the same evening, a sequence of mine ran the replay inside the live kit and then deleted its own saved copies, overwriting the live atlas and ladder that the 19:47 card baseline had been issued against. That loss is why the baseline is now generated from saved code rather than read from a saved file.

## What this does not show

The joined model has not demonstrated forecast improvement on predictions recorded before kickoff. The engine's acceptance is still NOT ACCEPTED on plays per game (126.99 generated against 136.73 recorded); the handoff carries 30 engine draws, repeated, into 2,000 kit columns; the engine's players are placeholders. The forward window — engine-rooted cards recorded before the games and scored after them on a declared hold-out, with the player model held fixed — is the test that would settle it, and it has not been run.

## Role

In Cameron's words, spelling corrected and nothing else:

> I propose an idea to the agent, they propose an action, I say if they can predefine what would prove them wrong. I confirm the action to be coded by them. Then make them check their work against the predefined pass/fail. To strengthen this over time I split the builder from the judge. The judge sits in a new thread so it can prove the builder wrong.
>
> If the model had to break a rule to create a simulation, like a fifth down, that iteration failed.

The code and the harness in this repository were written by AI assistants under that procedure, including the mistakes recorded above; the checks named in this case are the predefined pass/fail. The short demo and its verdict were reproduced from a fresh clone and a fresh environment on this machine and on a GitHub runner; the full replay has its own prerequisites, stated in the README.
