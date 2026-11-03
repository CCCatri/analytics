# analytics — where it is going

The current state is in README.md. This is the finished product as the reader would see it, and how much of each line is measured today.

## The seven sentences (fixed order; only the owner restates them)

| | Sentence | Measured today |
|---|---|---|
| L0 Rules | Every game is 60 minutes; the ball changes hands after every score or stop; four downs to gain ten. | **In product.** `out/L0_rules.csv`, 1,719 rows; 0 unexplained in six seasons. |
| L1 Game | This game should have about P plays between both teams, more or fewer than these teams' usual, because ___. | Partly. Plays and possessions per game printed against the record; the engine reads short (120.8 vs 137.5). |
| L2 Team | His team gets about S of them, because ___. | Partly. Fourth-down choice measured by zone and distance (66 of 102 cells within 2SE). |
| L3 Calls | Of those, D are dropbacks, H handoffs and K kneel-downs; the D dropbacks are A throws, R sacks and C scrambles; he is hit on about Q of his dropbacks, because ___. | Mapped, not measured. Where QB hits come from is an open question: no column holds them. |
| L4 Group | Of the A throws, the receivers get Y, the tight ends Z, the backs W, others O, and T are thrown away, because ___. | Not measured. |
| L5 Man | He gets N of his group's, because ___. | Not measured. |
| L6 Touch | Each is worth about M yards against this defense, because ___. | Not measured. |

Slices add up exactly; each number carries its range (2SE); each "because" names a measured link or says "its own average so far; nothing measured moves it." Marks: 28 possible, 1 earned.

## The order

1. Explain the engine's short count: plays and possessions against the record, by the mechanism that writes them.
2. Retire the hand checks behind the commit instrument (it runs beside them; 86 of 86 agree).
3. L1's sentence in product, with its range.
4. Then L2 to L6 in order, each MAPPED → MEASURED → IN PRODUCT → SCORED, one term at a time, each given the level above as it happened.

## Hypotheses carried, not yet measured

Each team plays against itself: a side that performs poorly creates a compounding feedback loop against its own next calls. A defense is mostly reactive; the offense creates the game within the game. An injured offensive line shows up in the quarterback's pressure, throws and interceptions before it shows up anywhere else. Each is a link to measure at its level, against the same-season average known before kickoff, on five seasons and stated for the sixth.

## What will not be built

A price for a player's line, a score or winner pick, a lineup. Market lines and model outputs fit on all seasons stay banned as inputs.
