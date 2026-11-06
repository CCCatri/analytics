# Forward window — does the join forecast better? (prospective pilot; design pinned before any outcome is read)

Status: PILOT DESIGN, pinned; **deferred by ruling of 2026-11-06** — the 2026 season's inputs were removed from the repository rather than brought up to date, so no slate of 2026 is issuable here. The first eligible season is the first one ingested after this design, under the same rulings. No forecast in this comparison has been recorded or scored. The pilot collects evidence that can only be collected before kickoff; it does not decide whether the candidate replaces the baseline. A result is admissible only if the issued cards, their hashes and the issuance record were produced under this file's pinned sha.

## The two versions
- **Baseline** — the slate kit in kit mode: team volume from the kit's own rate and bootstrapped ratio.
- **Candidate** — the same kit in engine mode: team attempts and carries from the engine's root draws for that week (`out/handoff/root_draws_<season>_w<week>.npz`, K source draws expanded by j mod K). The only intended difference between the two versions is the root.

## "The only difference is the root" — made checkable
Held fixed across both modes, and recorded per slate: the kit code revision (git sha), the pregame inputs and their information-time cutoff, the candidate rules, and the downstream random-number policy (the keyed substreams, so a player's draws differ between modes only through the root they consume). A row that appears on one card and not the other is an **unmatched row**: it is reported beside the paired scores, by cell, so the common rows cannot hide a coverage loss. Both cards are issued for the same slate, the same candidates, the same terms.

## Preserving what existed before kickoff
For each eligible slate the Builder saves: both issued cards and their SHA-256; the root artifact and its SHA-256 (candidate); the kit sha and this file's sha; the raw-input pins in force; and an issuance record stating when the pair existed (the card's issue time, the commit that holds the hashes, pushed before the slate's first kickoff). The Falsifier scores those saved cards after the games, never a reissue. A hash identifies the file; the issuance record establishes when it existed.

## Scoring (report only, in the pilot)
The kit's own grader: CRPS per stat row on the recorded outcome, paired by (season, week, player, term). Reported per cell: baseline CRPS, candidate CRPS, the paired difference with its spread, rows issued, rows graded, rows declared, unmatched rows. The replay's season-chance test treats seasons as units; a one-season window gives it one unit, so it is **not** applied in the pilot. Before any promotion window opens, the Falsifier shows what the current test returns for a one-season input, and a test suited to the window is chosen and pinned then.

## Project owner's rulings (pilot)
- **Eligible slates**: the first season ingested after this design (2026 was removed on 2026-11-06), from the first slate for which both cards can be issued before its first kickoff, through week 16 (within the kit's ISSUE_WEEKS 4–16). The actual start week is pinned by the first issuance record. Every eligible slate is logged, including a missed issue or a failed card, with the reason.
- **Engine draws per week**: K = 30 for the pilot, the fixture's count, if its runtime stays representative. A larger K is adopted only after a preflight on development data shows whether team-volume summaries and player projections settle as K rises, and is pinned before the first issue it applies to. Thirty source draws reused across 2,000 columns remain thirty game scenarios; player draws vary within them.
- **Decision threshold**: none in the pilot. No replacement of the baseline. The minimum worthwhile improvement and the test suited to the window are set before a later promotion window, not during the pilot.
- **Upstream quality gate**: the engine's plays-per-game gap (126.99 generated vs 136.73 recorded, `engine-vs-record.md`) is measured against the existing game-volume criterion; the pilot runs and reports whether or not it passes, with the gate's status beside every result. A pass is required for promotion, not for the pilot.

## Division of work
The owner rules on what the pilot can earn (this file). The Builder issues the two cards per slate and saves the evidence above. The Falsifier checks the issuance record, grades the frozen pair after the games, and reports what the window can support — including UNKNOWN where it cannot.

## What a result earns
Evidence, not a decision: per cell, where the candidate helped, hurt, or could not be told apart, with coverage and the gate's status beside it. A worse or inconclusive pilot completes the pilot just the same. Nothing here changes the lead case, which claims only that the join works and is inspectable.
