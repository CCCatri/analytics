# Convergence rubric — claims, evidence records, concepts

Three layers joined by keys, never merged. The evidence layer is seeded from the two current cases (where measured records exist); the claim layer from the three claims a hiring reader meets first. Comparing two projects asks whether each demonstrated a practice, not how well it performed. Comparing versions within a product also needs the same fixture and acceptance rule, or an explicit account of what changed.

## A. Layers
| Layer | Row | File | Valid when | Guards against |
|---|---|---|---|---|
| Concept | one capability with a test that could separate it from its neighbors | concepts.tsv | its separating test is stated; identical columns across trees are a review flag, not a merge | two names for one concept; one name for two |
| Evidence record | revision (or frozen snapshot) x run x concept x scope: tier, verdict, pointer, intent_date | matrix.tsv | the pointer's contents and provenance support the tier | prose scored as measured; a local result scored as reproduced; a failing measurement dropped |
| Claim | a sentence a reader should remember | CLAIMS.md | its evidence is appropriate to the claim: repo result -> inspectable run; paid work -> scoped account the owner can explain; credential -> issuer | a claim written from a record without the owner's words; a record promoted to a claim because it exists |

Tiers: mentioned, specified, measured_locally, measured (run evidence inspectable), reproduced (clean checkout). Tier is graded by contents and provenance, not file type: a Markdown case carries measured when it links pinned inputs and the run; a log can carry only an assertion. intent_date earns "stated before the run" only when the dated text names the specific expectation that run tested.

## B. Joins
| Join | Rule | Automated | Human |
|---|---|---|---|
| claim -> records | every claim lists its records; one record per material clause where clauses rest on different runs | references resolve; tiers sufficient for the claim type; structured values agree where a comparison is defined | every material clause is supported |
| record -> claims | derived backlinks, for discovery | count of uncited measured records | which become claims, in the owner's words |
| concept -> records | an empty cell is a gap only when it blocks a product decision, a claim the owner wants, or a hiring requirement actually identified | gap list = empty cells ∩ blockers | nothing else is built |
| intent -> record | first dated statement in the owner's words, kept apart from tier | date precedes the named run | whether the text names that test |

## C. The three claims
| Claim | Concepts | Evidence type | Tier | Records | Limit |
|---|---|---|---|---|---|
| Mercor broken-take test | fault injection; regression verification | paid-work account, scoped, explainable in interview | stated | - | not publicly verifiable; a public analog (partition check self-test) corroborates the method, not the event; leads page one |
| NFL handoff: input trace 36->60 -> Ridder 6->10; refusals; switch-off replay | controlled perturbation; fault injection; regression verification; provenance | inspectable run | measured | four records at a79251c / run 20261106_082012, one per clause; vocabulary rerun as a further record | the rerun adds evidence at the new revision; it does not revise the verified one |
| Healix evaluation: 112 -> 5 / 107 / 0 / 0; one removed proposal moves one | accounting; abstention; fault injection | local run | measured_locally | README evaluation; scripts/evaluate.ts | stays measured_locally; a tracked synthetic evaluator run in CI is a separate reproduced record of the method, not of this result |

## D. Leads and uncited records
| Record | Status | What makes it measured / a claim |
|---|---|---|
| NFL slices vs team budget: 33,352 of 64,000 games over | lead | pin 64,000 = 32 teams x 2,000 draws, team scope, budget = F2 team attempts; then a measured FAIL the owner found and recorded |
| NFL foul abstention: 51,136 of 100,000 | lead | verify the generator and the recorded reasons |
| Healix population-relative judgment: 60 verdicts flip | measured, uncited | the judge's defining behavior; a claim in the owner's words |
| NFL acceptance ledger | measured, uncited | product-only unless a posting asks |

## E. Moves
| Move | Action | Gate |
|---|---|---|
| Identify | repos: what deserves to survive; hiring: the strongest surviving evidence easy to recognize and verify | the three claims scored with source, scope, evidence type, limit |
| Exploit | résumé: Mercor test first in its entry; one measured NFL or Healix result on page one, owner's words | the PDF rebuilt; check_claims PASS |
| Subordinate | prose passes, Healix renames, workbook, credentials wait behind the gap list | gap list printed |
| Elevate | one missing proof: Healix fixture with a tracked never-proposed case + evaluate in CI | CI green gives the synthetic evaluator run its own reproduced record; the Fodors 5 / 107 / 0 / 0 result keeps measured_locally |
| Repeat | one verified older version when it answers a real carry-forward question | a revision on disk; same fixture or an explicit account of what changed |

## Conflation tests
Identical concept columns -> review, state the separating test. No record whose tier exceeds what its contents and provenance support. No claim without records appropriate to its type. No clause without a record. No intent_date read as a criterion unless the text names the test.

## F. The shared object and the three statuses
The experiment record: baseline, intervention, the dependency that carried the change, expected response, actual response, evidence, verdict at the declared scope. Forward execution writes it; diagnosis reads it backward. Adapters supply inputs and identities (team, draw, player; table, row); domain rules supply what a good result is; the shared code pins, intervenes, compares, records, replays.

Three statuses, never merged into one word:
| Status | Who issues it | Example from the 65-row case |
|---|---|---|
| domain verdict | the product's judge or kit | the judge said SUPPORTED |
| verification result | the check against the fixture's expectation | FAIL, because the label says the pair is wrong |
| release decision | the acceptance process (ledger) | accepted or not, recorded with the revision |

Definition of done for one engine: one entry point runs one real case from each repo, emits the experiment record, catches a planted failure in both; from a failed check, the trace names the pair or draw, the stage, the pinned input and the original expectation; a clean run reproduces the decision on the tracked fixtures. Verdict words: SUPPORTED is provisional (vocabulary row OPEN); older verdicts map at the boundary with their meaning intact.

## G. Status (2026-11-07, both repos pushed; CI green at healix 9b096bd, analytics 9a8558a)
| Thread | State | Last landed | Next |
|---|---|---|---|
| Vocabulary A–B4: file + check, analytics prose, identifiers, product words, regeneration, pruning | done | analytics 9a8558a | — |
| Vocabulary B5: Healix verdict words in code and docs | not landed (reverted with the fixture attempt) | — | rides with Healix WO2 |
| Vocabulary B6: `.gate` → `.quality-gate`, record rewritten, fresh point | not started | — | after B5 |
| Vocabulary B7: hand pass (CHARTER spine/chain/gate/ledger/owner; incidents; man/men) | not started; live remainder about 1,000 | — | low priority |
| Analytics WO1 plays gap; WO3 hold-out | open, unchanged | — | — |
| Analytics WO2 forward pilot | deferred; owner rules whether "2026 w10+" is history or plan | — | one line from the owner |
| Analytics WO4 slices vs team budget | measured FAIL (receivers 52%, passers 42% of team-draws); units pinned; check in repo | 3eba502 | the fix (joint draws) not started |
| Handoff harness | PASS run 20261107_153255 at 60ada8f; docs cite it | 81d74be | — |
| Healix WO1 judge limitation | measured and bounded; owner rules on a population-independent floor (cost 51 of 267 c2 copies) | 92dc904 | one line from the owner |
| Healix WO2 never-proposed case; evaluate in CI | refused: 3-field edited copies were proposed | — | measure which edits drop a copy; land with B5 |
| Healix harness ledger landings (landing 0, gateClean, demo/check/evaluate) | declared pending | — | after B6 |
| Concept matrix, RUBRIC A–F | landed and mirrored | both repos | claims↔cells join: CLAIMS.md cells column + check |
| Historical rows (healix6 on the five never-proposed pairs; NFL history) | not started | — | after the join |
| Lineage rubric; NFL extract scan | not started | — | — |
| Shared engine | definition of done (F); pilots (DraftKings join; two-case executor) not started | — | after Healix WO2 |
| Résumé v13 | pending the owner's words: Mercor test first; one measured result on page one; Healix sentence rescoped to the named false confirmation; People Management ruling | v12 master | CLAIMS rows, rebuild |
| Healix case page: three decisions (Apr 21 and Aug excerpts; October unverified) | not started | — | after v13 wording |
