# A quality gate that passed by luck, guarding a claim that was false

## Wrong
A regression quality gate failed about 1 run in 10 for reasons unrelated to the change under test.

## Caught
Python's hash order acted as a hidden seed. Across 10 orders the claimed 95% intervals covered 0.921 (2SE 0.020); the spread was estimated low in 10 of 10.

## Control
The quality gate's real claim (an injected 0-based predecessor is refused) passed in 10 of 10; 8 injected faults judged as required.

## Changed
The quality gate judges the claim it exists for; the false coverage is recorded as a measured defect. `c4aa9c7`.

