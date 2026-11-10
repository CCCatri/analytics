# The executor

One piece of code (checks/experiment.py) runs every product's cases by the same rules and writes their evidence records. It was not designed first: it was found by building two products, the NFL engine and Healix, pulled out of both, and is proven only by a third product that needs no change to it.

## Who supplies what
| Part | Supplies |
|---|---|
| A product's connector | its inputs and identities: team, draw, player; table, row |
| A product's own rules | what a good result is |
| The executor | pins the inputs, makes the change, compares, records, replays |

## The evidence record
Every case writes one: baseline, change made, the path the change travels, expected result, actual result, evidence files, and three statuses that are never merged into one word:

| Status | Who issues it | Example |
|---|---|---|
| The product's answer | the product | Healix said SUPPORTED |
| The check's result | the check, against the expected result | FAIL: the label says the pair is wrong |
| The change's verdict | the owner, recorded with the revision | ACCEPTED at a named commit |

## Done means
1. One entry point runs one real case from each product and writes the evidence record.
2. It catches an injected fault in both products.
3. Backward diagnosis: from a failed check, the record names the pair or draw, the stage, the pinned input and the original expectation.
4. A clean copy reproduces the decision on the tracked fixtures.
5. The executor holds no product's rules: each product's code lives in its connector.
6. A third product is judged with no change to the executor.

| Step | Proves clauses |
|---|---|
| E1 One executor, two products | 1, 2, 3, 4 |
| E2 The executor holds no product's rules | 5 |
| E4 A third product, no executor change | 6 |

Status lives on the rubric page, never here. Evidence tiers and verdict words are defined in VOCABULARY.md; evidence records live in matrix.tsv.

## Rules that join claims to evidence
- Every claim names one evidence record for each clause that rests on a different run.
- Measured records that no claim cites are counted, so a strong result is not left unused.
- A prediction counts as stated before the run only when its dated text names that run's test.
- Two names for one idea, or one name for two: state the test that separates them before treating them as the same.

Replaces acceptance-criteria/shared-checker.md (2026-11-10); first written as RUBRIC.md sections A, B and F.
