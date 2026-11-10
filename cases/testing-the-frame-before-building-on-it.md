# Testing the frame before building on it

## Risk
Every level below the team total assumes a player's share and his team's volume can be judged apart, and that the share law's absorbed full-game gap holds when exits change. If either failed, N2b and the lineup work would build on a crack.

## Tested
Three reads at `d92c935` on the replay baseline CI passed on, the decision written before each. Share vs team total: receivers −0.05 ± 0.05 and tight ends +0.01 ± 0.09 hold; backs −0.09 ± 0.04, real but at the bound. Error vs exits by team-season: ranges ±0.26–0.39, wider than the bound. Within each player's season, per 10 percentage points of earlier games cut short: ranges ±0.24–1.15, still crossing it.

## Missed
I predicted the finer read would tighten under 0.15; it didn't. Few games follow an exit (316 for backs) and the share barely moves within a season. A tight end's sign also came out opposite.

## Changed
Nothing in the product: no measured link moves the share rule, so it stays its own average. The frame test is closed as NOT SHOWN, not as proof the effect is zero; N2b starts.

