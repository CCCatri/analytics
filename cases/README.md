# cases/ — the stories, each standing on a check

Start with `from-a-simulated-game-to-a-player-projection.md`. The three it links: `clock-check-passed-a-corrupted-game.md`, `regression-test-needed-data-that-could-trigger-the-bug.md`, `two-components-had-to-agree-on-what-counts-as-an-attempt.md`. `evidence/` holds the saved results the cases cite, so a reader can see the lines without running anything.

## Short cases
Each names what went wrong or was at risk, how it was caught, the control that proves the check could fail, and what changed. Status lives on the rubric page; figures come from their named runs.

- [A simulator that passed every test while ignoring the score](a-simulator-that-passed-every-test-while-ignoring-the-score.md)
- [The remainder traced, then built only once proven knowable in advance](the-remainder-traced-then-built-only-once-proven-knowable-in-advance.md)
- [A quality gate that passed by luck, guarding a claim that was false](a-quality-gate-that-passed-by-luck-guarding-a-claim-that-was-false.md)
- [A green demo hiding a card with no grades](a-green-demo-hiding-a-card-with-no-grades.md)
- [Deciding not to build, by measurement](deciding-not-to-build-by-measurement.md)
- [A stricter rule that looked better and wasn't](a-stricter-rule-that-looked-better-and-wasn-t.md)
- [Flags that must beat a shuffle](flags-that-must-beat-a-shuffle.md)
- [One executor, two products](one-executor-two-products.md)
- [My validation battery graded one of my own checks weak](my-validation-battery-graded-one-of-my-own-checks-weak.md)
- [A one-word ending that hid 1.6 points a game](a-one-word-ending-that-hid-1-6-points-a-game.md)
- [One forecast answering two questions](one-forecast-answering-two-questions.md)
- [Testing the frame before building on it](testing-the-frame-before-building-on-it.md)
- [A chance that was right on everyone and wrong on the players it is for](a-chance-that-was-right-on-everyone-and-wrong-on-the-players-it-is-for.md)

## Calls by the project owner that changed the result
- **Standardize the play types and drop the version proven weak.** The key-order read that followed found the simulator ignored the score outside the last two minutes (case 1).
- **Delete the checks that test form and replace them with checks of meaning.** Found a quality gate that passed by hash-order luck and a coverage claim that measured false (case 3).
- **Don't overlook the prop and NBA concepts from the capstone.** The five-factor link chain and the luck map now frame the machine-learning plan (production, engine track: models one level at a time).
- **I want the two-step story.** The remainder after the first fix was traced and fixed too, from earlier games only (case 2).
- **The projections assume the starter plays the full game.** Gave the team-budget quality gate a testable acceptance and closed an unbuildable rule by measurement (case 5).

## Rejected changes and failed candidates
- Backs', receivers' and tight ends' shares measured on full games only (2026-11-10). The replay read WORSE for receivers (p 0.032) and tight ends (p 0.017), and the targets budget fell from 16 to 11 of 32 teams: the share law had already absorbed the full-game gap, so the change counted it twice. Not accepted; recorded in `acceptance-criteria/full-game-lines.md`. The grading half was accepted (`9390fa6`); N2a stays open for those positions.
- Full-game grading, first version (2026-11-10). The DK DFS quarterback cell read WORSE (CRPS 4.00 to 4.10): it graded games the premise excludes and treated the chance of playing as the chance of starting in 2020. Not accepted; the corrected version accepted (`c107d2f`).
- Full-game quarterback lines, first version (2026-11-10). The demo's trace could not see the team total reach the quarterback, because the new draw skipped the shared drawing step. Not accepted; redrawn through it with identical numbers (`25bc9c1`).

Moved from the rubric page's Evidence tab on 2026-11-10.
