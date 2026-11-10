# The shared checker

One piece of code judges every product (NFL, Healix) by the same rules. It was not designed first: it was found by building two products, pulled out of both, and is proven only by a third product that needs no change to it.

## Who supplies what
| Part | Supplies |
|---|---|
| A product's connector | its inputs and identities: team, draw, player; table, row |
| A product's own rules | what a good result is |
| The shared checker | pins the inputs, makes the change, compares, records, replays |

## The evidence record
Every case writes one: baseline, change made, the path the change travels, expected result, actual result, evidence files, and three statuses that are never merged into one word:

| Status | Who issues it | Example |
|---|---|---|
| The product's answer | the product | Healix said SUPPORTED |
| The check's answer | the check, against the expected result | FAIL: the label says the pair is wrong |
| Accepted or not | the owner, recorded with the revision | accepted at a named commit |

## Done means
1. One entry point runs one real case from each product and writes the evidence record.
2. It catches a planted failure in both products.
3. From a failed check, the trace names the pair or draw, the stage, the pinned input and the original expectation.
4. A clean copy reproduces the decision on the tracked fixtures.
5. The checker holds no product's rules: each product's code lives in its connector.
6. A third product is judged with no change to the checker.

| Step | Clauses | Status (2026-11-10, at 0320305) |
|---|---|---|
| E1 One checker, two products | 1, 2, 4 | met in CI; clause 3 (the trace) not yet built |
| E2 The checker holds no product's rules | 5 | not met: checks/experiment.py names a product on about 40 of its 84 lines |
| E4 A third product, no checker change | 6 | not built |

## Where evidence stands
| Tier | Means |
|---|---|
| named | mentioned, no test written |
| test written | its pass test is stated before any run |
| measured on my Mac | run, evidence on one machine only |
| evidence pushed | run, and its evidence files are committed |
| reproduced by CI | rerun on a clean copy and passed |

A tier is judged by what its evidence holds and where it came from, not by its file type. Evidence records live in matrix.tsv.

## Rules that join claims to evidence
- Every claim names one evidence record for each clause that rests on a different run.
- Measured records that no claim cites are counted, so a strong result is not left unused.
- A prediction counts as stated before the run only when its dated text names that run's test.
- Two names for one idea, or one name for two: state the test that separates them before treating them as the same.

Moved from RUBRIC.md sections A, B and F on 2026-11-10; RUBRIC.md's status table was stale and is deleted.
