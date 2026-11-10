# Method and rules

One file for how work is found, judged and accepted, in every product (the NFL engine, Healix, the résumé, operations evals). Words are defined in VOCABULARY.md; status lives on the rubric page. This file is byte-identical in CCCatri/analytics and CCCatri/healix.

## Five moves
1. Invariance: what stays true when the setting changes? What survives every rebuild and product is a trait; what appears once is a detail.
2. Triangulation: does it hold in independent examples (no shared product, data or year)? Two examples from one product count as one.
3. Inversion: how could this look right while being wrong? Each answer becomes a test. A cost paid again and again is a value held.
4. Three orders: what changes now, what that changes downstream, what it enables over time (defect caught, then regression test, then a shared capability).
5. Change the grain: zoom in (one record, one play) and out (fixture, product, hiring claim). A gap at one grain is often answered at another.

Then Theory of Constraints: find the single bottleneck holding back the goal and the smallest action that moves it. Nothing else gets effort until it moves. No new frameworks.

Inside the products: invariance = the rules file and metamorphic tests; triangulation = held-out seasons and independent views; inversion = injected faults and predictions that would fail; three orders = the map down (the split) and up (results to the next calls); change the grain = the levels, game to touch.

How the AI applies it: restate the ask as the claim sentence and blank it serves; run the five moves on the evidence; name the one constraint; give the smallest action.

## The rule under every claim
- When one number answers two questions, separate them and test each part on its own before judging the combined result: who is in it (the members), what each gets (the split), and whether the parts add up (the sum). A combined result is judged only after every part passes, and each part on the members it serves.
- Top-down: a level is measured only after the level above has its map. Slices add up exactly: every part of a claim has its support below it, and everything below serves a part of the claim.
- A blank is filled by a measured link, or left open with its reason ("its own average so far; nothing measured moves it").

## Who does what
- I hold the question and premise each product rests on, the acceptance criteria (written before any code), the rulings on what counts as right, the domain knowledge (football, operations, real records), and the call to stop, redirect or go deeper.
- The AI writes the code and the measurement scripts, proposes checks and the injected faults that must fail them, and runs the arithmetic, reporting misses as plainly as hits.

## Evidence: what may be stated
Honesty, then accuracy: a well-calibrated lie is a failure. Every lie, blatant or by omission, is resolved before anything is tested.
- Evidence tiers, strongest first: Someone else's record, CI Passed, Evidence pushed, On Mac, Account only (VOCABULARY.md). A claim's tier is the weakest record it cites; a number at Account only is never stated.
- Only a link closes, never a cause. A cause stated straight to an outcome, skipping the link, is reduced form: a diagnostic only.
- A number stated where its link was not measured is worse than no number.
- Acceptance criteria come first, with the output that would fail each.
- Never guess a name, a column or a date: read it from the source file. When it is not there, the answer is INSUFFICIENT_EVIDENCE: no decision, and it names the evidence that would settle it, which the next run collects.
- Remove an assumption; never register it as a caveat to keep a weak claim.
- State what the evidence covers beside the claim. Count each result once; credit it where it was earned; thin evidence stays thin.
- A number is used only if it can be explained out loud.
- A link must open for a signed-out stranger. Every figure on the résumé appears in CLAIMS.md. When two of my accounts disagree, use the version in the source file or leave it off.
- A clean clone is the test of "runs anywhere": local passes can hide missing dependencies.
- A figure measured on a product that has since changed is withdrawn until it is measured again.
- One authoritative data source per fact: a figure is sourced once, and every copy matches it.
- A measured NOT SHOWN is a result: recorded and closed, never forced; a retry at a finer grain says so first.
- Whose words: only lines I typed count as mine. Say what the AI did and what I did.
- Confidentiality (Mercor): never stated outside Mercor: the project name, scores (checker results, counts, approvals), reviewer quotes, pay and tier, task content. A method description with no task content is allowed.

## Checks and change: what gets accepted
- Product files are the files a product reads (code, the exported résumé PDF). Anything only in memory, a note or a page has not happened.
- Every run makes one accepted change to product files, or declares itself a read before it runs.
- Acceptance criteria name, before any work, the file a run may change and the checks that accept it. When they pass, the file is written in the same run.
- One cause, one change: change exactly what was asked; a pass means the asked change happened and nothing else moved.
- A change later found wrong is reverted or corrected by an accepted change, never held back for fear of it.
- A loop of revisions states its goal before its first run, as a count that must reach zero (for an evaluation item: a blind grader matches the key on every answer and names no reading that changes a score). A revision is accepted only when the next run shows that count lower and nothing new; otherwise it is reverted. Remove a choice before rewording (state the evidence in the task rather than add words to an anchor); a fix never restates another rule.
- Ceilings fall, never rise. Only the project owner adds a quality gate, and only before a run.
- Check only what the next step reads. Every counter prints or is deleted. Delete what nothing reads; never archive.
- A script's exit status agrees with its verdict: no stage fails silently.
- Verdicts by layer, never merged (VOCABULARY.md): a check's result PASS / FAIL; a link's verdict ESTABLISHED / NOT SHOWN / NOT TESTABLE; a change's verdict ACCEPTED / REARRANGED / PRINTED (Healix: BETTER accepted, WORSE closed); a claim's verdict SUPPORTED / REFUTED / INSUFFICIENT_EVIDENCE.
- Each check fails on an injected fault before its PASS counts, and again whenever its code changes. Injected faults test the subject (football, records, claims), not label wording.
- The judge and the product never read each other's evidence. Never tune and score on the same case.
- A falsifier who sees only the fixed points confirms each check can fail, approves each read before it runs, and confirms what moved after each change.
- Two sides that must agree are checked mechanically, not by rereading.

## Strength classes (one résumé bullet proves exactly one)
| Strength | The rule it names | Concepts (VOCABULARY.md) | Instances |
|---|---|---|---|
| Define what should happen | Acceptance criteria before the run, with the output that would fail | acceptance criteria; controlled perturbation | NFL: one team draw changed 36 to 60, its 67 mapped columns moved and no others; Healix prints its prediction first |
| Test a known-good and known-bad case | A check fails on an injected fault before its PASS counts | fault injection; regression testing; negative control | NFL budget self-test; engine stage 1 (11 of 11 injected faults caught); Healix judge; the Mercor grading tool (method only) |
| Find the discrepancy before acting | A second read from a different direction; INSUFFICIENT_EVIDENCE means no decision yet, and names what to collect | reconciliation; population-relative judgment; calibration | the concessions recount; 16 of 32 teams the average hid; rental guest photos and reviews; LeNoble merges reviewed with the client |
| Weigh what a change fixes and what it costs | Help somewhere without hurting anywhere else | regression testing; hold-out set | Healix stricter rule: false confirmations 3 to 0, 51 of 267 true copies lost, rejected; three allocation fixes rejected |
| Turn a failure into a repeatable check | Incident-derived rules; each failure kept as an injected fault | regression testing; fault injection | the Mercor fill-down rule (method only); the graded-line check after a green demo hid ungraded cards |
| Refuse to guess | INSUFFICIENT_EVIDENCE always names the evidence that would settle it, and the next run collects it | abstention; NOT SHOWN | Healix "can't tell" on 95 of 99 files; NFL frame test closed as NOT SHOWN, not forced |

Moved from system notes 02, 03 and 04 on 2026-11-10.
