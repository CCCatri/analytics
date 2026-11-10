# Vocabulary — one meaning, one name, in every file

The same words in the README a hiring manager reads, the case pages, the acceptance criteria, the code identifiers, the check printouts, the harness record and the charter. No file is exempt. Rules from `slate-kit/TAXONOMY.md` (the kit's naming layer for columns and windows, which this file sits above): each meaning has exactly one name; a retired spelling appears only in a Retired column, so old text is read through the table and never guessed at. Where a record was protected by a digest of its old wording, the record is revised with a dated line saying so and the digest re-recorded; a digest protects wording that has been retired is not evidence, it is drift pinned in place. `checks/check_vocabulary.py` scans every text file in the repo and fails while any retired spelling remains outside a Retired column. This file is byte-identical in `CCCatri/analytics` and `CCCatri/healix`.

| Kind | Canonical | Retired | Meaning | Standing |
|---|---|---|---|---|
| Verdict | `SUPPORTED` | right, yes (as a judge ruling) | The claim fits its evidence: a slice fits its budget; a pair's agreement is distinctive in its population | OPEN — provisional in docs and code; not in the owner's map; the owner rules |
| Verdict | `REFUTED` | no (as a judge ruling) | The evidence contradicts the claim | in use |
| Verdict | `INSUFFICIENT_EVIDENCE` | UNKNOWN, unknown, can't tell (as a verdict) | The evidence reaches neither bar; the output names what is missing | new |
| Practice | fault injection | planting faults, planting | Introducing a known fault to prove a check detects it | new |
| Object | injected fault | plant, planted fault, plants | The fault so introduced; code `injected_fault` (object), `inject_fault` (action) | new |
| Evidence | Someone else's record | third-party record | A record kept by someone else: nflfastR's drives, DK DFS's recorded points, a grader's verdict (note 03 tier 1) | new |
| Evidence | CI Passed | reproduced, reproduced by CI, a run a stranger can repeat (as a tier) | Rerun on a clean copy by CI and passed (tier 2) | new |
| Evidence | Evidence pushed | In Repo, Code pushed, measured (as a tier) | Run, with its evidence files committed where a signed-out stranger can open them (tier 3, pushed) | new |
| Evidence | On Mac | measured_locally, measured locally, measured on my Mac | Run, with its evidence on one machine; a stranger cannot open it (tier 3, local) | new |
| Evidence | Account only | my account (as a tier) | No record; fine for a habit, never for a number (tier 4) | new |
| Work | Not built | mentioned, named (as a status) | Named only; no test written, nothing run | new |
| Work | Test written | specified, designed (as a status) | The pass test is stated before any run | new |
| Verdict | NOT SHOWN | closed by a read, inconclusive (as a link verdict) | A link measured and not distinguishable from no effect at the stated bound; recorded and closed, never forced | new |
| Object | executor | shared spine, trunk, shared engine, shared checker, runner (as the shared code) | The one piece of code that runs every product's cases and writes their evidence records (checks/experiment.py; acceptance-criteria/executor.md) | new |
| Object | product | project, domain, domains, tree, branch (as NFL, Healix or the résumé; the title Project Owner stays) | The NFL engine, Healix, the résumé: each judged through its own connector; product files are the files it reads | new |
| Practice | negative control | shuffle control | Breaking the link under test on purpose (shuffled, blinded); the result must vanish | new |
| Practice | calibration | chances come true | A stated chance or error rate compared with how often it came true, on held-out data | new |
| Practice | invariance check | permuted (as a test) | A change that must not matter (row or column order, relabeling) leaves the result unchanged | new |
| Practice | backward diagnosis | trace (as from a failure) | From a failed check, the record names the pair or draw, the stage, the pinned input and the expectation | new |
| Rule | the specific acceptance criterion or data validation rule | honesty rail | Name the rule itself, not a metaphor for it (note 05) | new |
| Practice | data leakage control | leakage prevention | Keeping data unavailable at prediction time out of a forecast's inputs (note 05) | new |
| Football | team-games | team-weeks (the 3,200 count) | One team's game in one week; a bye week holds none (note 05) | new |
| Practice | regression testing | — | Re-running known-right and known-wrong cases so a fixed fault cannot return | in use |
| Practice | reconciliation | two-source cross-check, record comparison, cross-check | Checking that two sources count the same thing | new |
| Practice | root cause analysis | recount ladder, cause investigation | Walking a discrepancy back to its cause before acting | new |
| Mechanism | quality gate | gate (as an acceptance mechanism); fail-closed gate | A check a change must pass to be accepted; the Healix harness folder becomes `.quality-gate/` | new |
| Definition | acceptance criteria | targets, DONE WHEN | What must be true for a change to be accepted, written before the run | in use |
| Verdict | accepted / not accepted | landed, LANDED, NOT LANDED, landing (as acceptance) | A change whose checks passed and whose files the product reads | new |
| Record | run log | ledger (recording a run) | The record of one run | new |
| Record | acceptance ledger | CHARTER ledger, ledger (bare, for this record) | The digest record of accepted charter lines | in use |
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
| Role | reviewer | owner (when the responsibility is review) | The person who reviews | new |
| Role | project owner | owner (bare, when it means ownership) | The person whose ruling binds; always written with "project" | new |
| People | player / players | man / men (as players); man-weeks → player-weeks, man-seasons → player-seasons | Players | new |
| People | team leadership | people management | Directing a crew | new |
| People | hiring and training | recruiting and training | Those activities | new |
| Process | standard operating procedure (SOP) | operating procedure | A written procedure | in use |
| Evaluation | golden set | gold labels, golden examples | Labeled cases a check is proved against | new |
| Evaluation | reference answer | expected response, model answer | The answer a rubric grades against | new |
| Evaluation | inter-annotator agreement | inter-rater agreement | Agreement between graders | new |
| Evaluation | flagging ambiguous cases | flag ambiguous cases | Marking cases the rubric cannot decide | new |
| Football | possession | — | A team's snaps from gaining the ball to losing it, two-point tries excluded (3-35, 11-3-1); counted by `check_possessions.py` | new |
| Football | drive | — | nflfastR's unit (`fixed_drive`): starts whenever the ball changes hands, with or without a snap; drives = possessions + named no-snap kinds (`check_possessions_crosswalk.py`) | new |
| Football | the stop | — | How the offense's last snap ended its possession, one of eight: punt, field-goal try, interception, lost fumble, touchdown, safety, turnover on downs, clock (3-35-3, 11-2, 11-5, 7-3-2, 4-1); `rules.possession_stop` | new |
| Product | DK DFS | DraftKings, fantasy, daily-fantasy | DraftKings daily fantasy sports (DFS), NFL Classic: the slates, salaries and scoring rules the product projects for, not betting lines. Its scoring rules live in `slate-kit/dk.py` (the transform) and `facts.dkpts` / `facts.dstpts` (checked against DK DFS recorded points). In code and term names "DK" means DK DFS: `DK dk_points` = DK DFS points with DNP = 0; `F8 dk_points` = DK DFS points given he plays the full game. The combined DK DFS projection is held until both of its parts pass on their own: whether he plays or starts, and what he does in a full game (the project owner's ruling, 2026-11-10) | new |
| Football | full game | — | A game a player plays from start to finish; for a quarterback, the only quarterback to throw a pass for his team that game (`draws.qb_games`); every projection is for a full game (acceptance-criteria/full-game-lines.md) | new |
| Football | kind of game | — | How a player's game went against the full-game premise: for a quarterback started and finished, started and left early, came in relief, did not throw; for a back, receiver or tight end full game, cut short (a regular's snaps under 0.6 of his usual), teammate cut short, no test (not a regular); a graded line uses only the games its condition names | new |
| Football | the score on the play | — | The first change on the scoreboard from the last snap to the next snap or kickoff, Tries left out: offense 6, 3 or 2, other side 6 or 2, or none (11-1-2); `rules.score_on_play` | new |

Keep distinct, never merged: data validation, data integrity, reconciliation, regression testing, fault injection, mutation testing, golden sets, hold-out sets, provenance, traceability, data lineage.

Verdicts by layer, never merged: a check's result (PASS / FAIL); a link's verdict (ESTABLISHED / NOT SHOWN / NOT TESTABLE); a change's verdict (ACCEPTED / REARRANGED / PRINTED; Healix: BETTER accepted, WORSE closed); a claim's verdict (SUPPORTED / REFUTED / INSUFFICIENT_EVIDENCE).

One evidence scale at two layers: an evidence record carries its tier; a claim's tier is the weakest record it cites. Strongest first: Someone else's record · CI Passed · Evidence pushed · On Mac · Account only. Before any evidence: Not built · Test written.
