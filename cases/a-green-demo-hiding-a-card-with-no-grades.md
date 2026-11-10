# A green demo hiding a card with no grades

## Wrong
After a rename, every card line printed with no grade, and the demo still passed.

## Caught
The join on the renamed state matched nothing and no refusal fired.

## Control
One card cell re-spelled in both reference tables; the demo names it and fails.

## Changed
4,005 of 4,450 lines graded (the rest have no grade by design); runs on every push. `376f664`, CI run 42522162564.

