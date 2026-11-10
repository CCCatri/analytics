# My validation battery graded one of my own checks weak

## Question
How often does each check cry wolf, and how small a defect can it see?

## Measured
100 seeds of real-vs-real halves and injected faults: score check 0% false alarms, catches 100% / 100% / 71% at full, half and quarter strength (RELIABLE); team-tendency check catches a missing tendency 93% but a half-strength one 17% (WEAK).

## Control
The battery's own self-test: an always-pass check must read BLIND and an always-fail check NOISY. Both did.

## Changed
A size rule set from a measured target (engine 0.026 vs the walk-forward target 0.025), not by eye; rerun: half-strength catch 17% → 93%, both checks RELIABLE. `fa698c3`, `dd9f3f9`.

