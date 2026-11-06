# From a simulated game to a player projection

The lead case. Two components that were built separately, the point where they met, what the join had to preserve, and what one combined run produced. The three earlier cases are parts of this one and are linked where they belong.

## The question

Start where an argument on Sunday starts: *if Las Vegas throws more in this game, where does that show up in the quarterback's projection?* To answer it you need three things to be inspectable: how many times the team throws (team attempts), what share of those throws this quarterback gets (player attempts), and which simulated version of the game you are looking at (the source draw). This case follows one such change — Las Vegas's attempts in one simulated game raised from 36 to 60 by hand — from the simulated game to Desmond Ridder's projected attempts, and ends with the command that reproduces it from a clean checkout. The pieces were built separately; the question is what joining them had to preserve, and what the join does and does not yet show.

### Terms

- **Team attempts** — a team's pass attempts in one game. In the engine: dropbacks that ended as a throw, plus accepted-penalty plays recorded as a pass attempt, never sacks (the counting rule both components were reconciled to, 3,200 of 3,200 team-games). In the kit: the root cell `("F2 team attempts", TEAM)`.
- **Player attempts** — one quarterback's pass attempts in that game: the kit's `Q1 attempts` cell, drawn as his share of his team's attempts from his own history.
- **Source draw** — one simulated playing of the game by the engine. The Week 15 fixture holds 30 of them (`draw_id` 0–29); kit column *j* reads source draw *j* mod 30, so column 30 is source draw 0, and a change to source draw 0 is expected at the 67 kit columns 0, 30, 60, … and nowhere else.

## What each project could do

**The engine** (`product/`, `checks/`, `run.sh`) plays a game out play by play under the rules: sixty minutes, the ball changing hands after every score or stop, four downs to gain ten. For a given week it produces, per draw, how many plays each team ran, how many possessions, how many pass attempts and carries. Its ball-handlers are placeholders (`SIM-<team>-QB`): it forecasts the environment, not the people. Its acceptance is rule-based: a generated game that breaks a rule fails, and each rule check had to fail on a planted fault before its pass counted ([the clock check that passed a corrupted game](clock-check-passed-a-corrupted-game.md); [the regression test that needed data able to trigger the bug](regression-test-needed-data-that-could-trigger-the-bug.md)). Gate 1 of the handoff: 30 of 30 generated 2024 week 15 games passed every verdict line, and four planted violations (possession, downs, clock, touchback spot) were each caught on their own line.

**The slate kit** (`slate-kit/`) projects players for daily-fantasy pricing, from the team down: a team's attempts and carries, then each player's share of them from his own history, then yards per touch against the defense, down to a fantasy-point distribution. Its top-of-ladder number — team volume — came from the kit's own rate and a bootstrapped ratio. Its own grader scores every cell against five seasons of outcomes, and it is plain about what it finds: on the 2026-11-05 replay 24 of 39 cells were decision-qualified and 0 of 4 fantasy-points cells were.

## Where they met

The kit's root cells are `("F2 team attempts", TEAM)` and `("F2 team carries", TEAM)`. The engine produces exactly those two numbers per team per draw. So the handoff is one file per week — `out/handoff/root_draws_<season>_w<week>.npz` with its manifest — and one rule: in engine mode the kit's root draws are the engine's, expanded from K source draws to the kit's 2,000 columns by `j mod K`, and every other cell is drawn as before.

Before anything could be handed over, both sides had to mean the same thing by "attempt" and "carry". They didn't, until a definition was written down and measured: [two components had to agree on what counts as an attempt](two-components-had-to-agree-on-what-counts-as-an-attempt.md) — 3,200 of 3,200 team-games reconciled.

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
- **C, the refusals.** Four isolated plants plus the cached-wrong-week and typo cases, each refused by name with no card artifact.

Run `20261105_210053`, the attempt before it, is kept as it ended: FAIL on two assertions that required the replay to *change* the bytes of `atlas.csv` and `ladder.csv`. The files are replay outputs (`draws.py:260–261`) that the copies already held with identical bytes, so a correct rewrite was invisible to a hash comparison. The harness's error, corrected by starting from absent files; everything else in that run had already passed. Earlier the same evening, a sequence of mine ran the replay inside the live kit and then deleted its own saved copies, overwriting the live atlas and ladder that the 19:47 card baseline had been issued against. That loss is why the baseline is now generated from saved code rather than read from a saved file.

## What this does not show

The joined model has not demonstrated forecast improvement on predictions recorded before kickoff. The engine's acceptance is still NOT ACCEPTED on plays per game (126.99 generated against 136.73 recorded); the handoff carries 30 engine draws, repeated, into 2,000 kit columns; the engine's players are placeholders. The forward window — engine-rooted cards recorded before the games and scored after them on a declared hold-out, with the player model held fixed — is the test that would settle it, and it has not been run.

## Role

Cameron Catri set the acceptance criteria and the order of the gates, decided what counted as a pass and what had to fail first, ran every command on his machine, and read every result; the code and the harness were written by AI assistants under that direction, including the mistakes recorded above. The repo is arranged so that a reader can run the same command and get the same lines.

## Run it yourself

From a clean checkout, with Python 3, numpy and pandas and nothing else: `python3 checks/demo_w15.py`. It issues the engine-mode card for 2024 week 15, shows the trace above, makes the 36 → 60 change and reports where it did and did not reach, and refuses one broken input — about 100 seconds; result in `out/demo_w15/<stamp>/RESULT.txt`, exit status equal to the verdict. The inputs it needs are in `checks/fixtures/demo_w15/` with their origins and hashes (`ORIGINS.md`, `PINS.json`); the raw play-by-play is not required. The saved result of that run from a fresh clone on 2026-11-06 is [here](evidence/demo_w15_clean_checkout_20261106.txt). The full regeneration (`checks/run_handoff.sh`) and what it additionally needs are described in the README under "Two ways to verify".
