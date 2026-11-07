# Vocabulary — one meaning, one name, in every file

The same words in the README a hiring manager reads, the case pages, the acceptance criteria, the code identifiers, the check printouts, the harness record and the charter. No file is exempt. Rules from `slate-kit/TAXONOMY.md` (the kit's naming layer for columns and windows, which this file sits above): each meaning has exactly one name; a retired spelling appears only in a Retired column, so old text is read through the table and never guessed at. Where a record was protected by a digest of its old wording, the record is revised with a dated line saying so and the digest re-recorded; a digest protects wording that has been retired is not evidence, it is drift pinned in place. `checks/check_vocabulary.py` scans every text file in the repo and fails while any retired spelling remains outside a Retired column. This file is byte-identical in `CCCatri/analytics` and `CCCatri/healix`.

| Kind | Canonical | Retired | Meaning | Standing |
|---|---|---|---|---|
| Verdict | `SUPPORTED` | right, yes (as a judge ruling) | The claim fits its evidence: a slice fits its budget; a pair's agreement is distinctive in its population | OPEN — proposed; not in the owner's map |
| Verdict | `REFUTED` | no (as a judge ruling) | The evidence contradicts the claim | in use |
| Verdict | `INSUFFICIENT_EVIDENCE` | UNKNOWN, unknown, can't tell (as a verdict) | The evidence reaches neither bar; the output names what is missing | new |
| Practice | fault injection | planting faults, planting | Introducing a known fault to prove a check detects it | new |
| Object | injected fault | plant, planted fault, plants | The fault so introduced; code `injected_fault` (object), `inject_fault` (action) | new |
| Practice | regression testing | — | Re-running known-right and known-wrong cases so a fixed fault cannot return | in use |
| Practice | reconciliation | two-source cross-check, record comparison, cross-check | Checking that two sources count the same thing | new |
| Practice | root cause analysis | recount ladder, cause investigation | Walking a discrepancy back to its cause before acting | new |
| Mechanism | quality gate | gate (as an acceptance mechanism); fail-closed gate | A check a change must pass to be accepted; the Healix harness folder becomes `.quality-gate/` | new |
| Definition | acceptance criteria | targets, DONE WHEN | What must be true for a change to be accepted, written before the run | in use |
| Verdict | accepted / not accepted | landed, LANDED, NOT LANDED, landing (as acceptance) | A change whose checks passed and whose files the product reads | new |
| Record | run log | ledger (recording a run) | The record of one run | new |
| Record | acceptance ledger | CHARTER ledger | The digest record of accepted charter lines | in use |
| Version | revision | wall | One revision of a model or kit; code `revision`, files `*_revision*` | new |
| Structure | link chain | chain (the kit's dependency chain); file `chain.py` → `link_chain.py` | The ordered links from team volume to a player's result | new |
| Execution | run | chain (as an execution) | One execution | new |
| Scope | the specific purpose | spine | Named for what it does; deleted where it is filler | new |
| Data | hold-out set | reserved evaluation data, heldset, held set, seal / sealed (as reserving data) | Data kept out of fitting for evaluation; `held out` / `hold out` as verb and adjective | new |
| Data | data available before kickoff | information time (for a kickoff forecast) | What was knowable when the forecast was issued | new |
| Data | authoritative data source | single producer per fact | The one source a fact is read from | new |
| Data | play-by-play record | the record | nflverse play-by-play | new |
| Rule | incident-derived rules | Contract (the rules document) | Rules written from incidents | in use |
| Event | incident | escape | A fault that reached a product file | in use |
| Role | reviewer | owner (when the responsibility is review) | The person who reviews; "project owner" when it means ownership | new |
| People | player / players | man / men (as players); man-weeks → player-weeks, man-seasons → player-seasons | Players | new |
| People | team leadership | people management | Directing a crew | new |
| People | hiring and training | recruiting and training | Those activities | new |
| Process | standard operating procedure (SOP) | operating procedure | A written procedure | in use |
| Evaluation | golden set | gold labels, golden examples | Labeled cases a check is proved against | new |
| Evaluation | reference answer | expected response, model answer | The answer a rubric grades against | new |
| Evaluation | inter-annotator agreement | inter-rater agreement | Agreement between graders | new |
| Evaluation | flagging ambiguous cases | flag ambiguous cases | Marking cases the rubric cannot decide | new |

Keep distinct, never merged: data validation, data integrity, reconciliation, regression testing, fault injection, mutation testing, golden sets, hold-out sets, provenance, traceability, data lineage.
