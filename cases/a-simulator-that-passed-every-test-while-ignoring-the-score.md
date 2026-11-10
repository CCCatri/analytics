# A simulator that passed every test while ignoring the score

## Wrong
Simulated coaches called plays as if the score didn't matter, except in the last two minutes.

## Caught
Simulated vs real dropback rate by score state, six seasons: trailing 9+ −0.116, leading 9+ +0.115, same sign in 6 of 6.

## Control
The play-by-play record compared with itself must pass; with its score shuffled away it must fail. Both did.

## Changed
Play calls keyed by the score all game; all five score states within 0.030. `da71fd3`, `checks/check_dropback_by_score.py`.

