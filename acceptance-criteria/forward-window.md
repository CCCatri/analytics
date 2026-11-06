# Forward window — does the join forecast better? (design frozen before any outcome is read)

Status: DESIGN. No forecast in this comparison has been recorded or scored. This file exists so that the baseline, the candidate, the scoring rule and the decision threshold are fixed before kickoff of the first eligible slate; a result is admissible only if it was produced under this file's pinned sha.

## The two versions
- **Baseline** — the slate kit in kit mode: team volume from the kit's own rate and bootstrapped ratio. Player model as of the pinned kit sha.
- **Candidate** — the same kit in engine mode: team attempts and carries from the engine's root draws for that week (`out/handoff/root_draws_<season>_w<week>.npz`, K draws expanded by j mod K). Same player model, same sha. The only difference between the two versions is the root.

## What is held fixed
The player model (shares, efficiencies, participation) is identical in both versions — the join is the only variable. Both versions issue for the same slates, the same candidates, the same terms. Cards are issued and hashed before the first game of the slate kicks off; the issue time is on the card.

## Scoring
The kit's own grader: CRPS per stat row on the recorded outcome, paired by (season, week, player, term); the paired difference summarised per cell with the season-chance test the replay already uses (ALPHA_FAMILY as pinned). Reported for every cell, with coverage (rows issued, rows graded, rows declared) beside it, whichever version wins.

## Project owner's rulings — blank until ruled, nothing runs before they are filled
- Eligible slates: season ____, weeks ____ to ____ (within the kit's ISSUE_WEEKS 4–16). 
- Engine draws per week: K = ____ (the fixture used 30; the repetition j mod K is a known limitation to be stated with the result).
- Decision threshold: the candidate replaces the baseline for a cell only if its paired CRPS is better by at least ____ with the season-chance test below ALPHA_FAMILY; otherwise the baseline stands and the result is recorded as it is.
- Upstream gate: the engine's plays-per-game gap (126.99 generated vs 136.73 recorded, `engine-vs-record.md`) is measured against the existing game-volume criterion before the first eligible slate; if it fails, the comparison still runs and the result is reported with that failure beside it.

## What a result earns
A better candidate earns one sentence: "on these slates, rooting the player model in simulated team volume improved the paired CRPS on these cells by this much." A worse or inconclusive result completes the experiment just the same, keeps the baseline, and gives the engine-mode card a specific thing to explain. Neither outcome changes anything in the lead case, which claims only that the join works and is inspectable.
