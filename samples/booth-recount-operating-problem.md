# Operating problem: the night count doesn't match the day's revenue

A work sample in the shape the Business Operations listing describes: an operating problem from work I have run, with the process and the constraint; the reference answer a model's attempt is graded against; a model's attempt; the grade. Figures are withheld on purpose — the process and the grading are exact, the numbers are not the point. Text in quotation blocks is mine as typed, spelling corrected; the headings and the grading scaffold are structure.

## The task (what the model is asked)

You run a carnival game booth with a crew of several people on a multi-week stand. Cash is picked up from the booth every hour. Stock (the prizes) is counted once in the morning and once at night. Tonight's stock count, set against the day's gross revenue, does not line up: more prizes are gone than the day's sales account for. Recommend what to do tomorrow.

## Allowed evidence

The operating procedure below, as written by the person who ran the booth, including the routine recount and the two ways the booth can narrow a gap (counting at the cadence of the cash pickups; counting each side of the booth separately). No other data. A good answer reasons from this; it does not invent figures, time windows or motives.

## The operating procedure (the constraint the answer has to survive)

> Count inventory every morning as standard practice so no red flags go up to the crew. Count again at night and compare to gross revenue for the day to check alignment of the numbers. If off, then escalation happens.

## Reference answer (what escalation is, in order)

> Cash pickups per hour are standard, but stock count per hour isn't. Checking the count more often in the booth to match pickups instead of per day, then narrow it down to whose side of the booth was short, then check them more often.

In plain terms, the order is: (1) the routine recount first — a daily comparison can flag a discrepancy but cannot locate it, and it can be a counting error; (2) if the gap remains, align the stock count with the hourly cash pickups and record each side of the booth separately, which is what lets a confirmed gap narrow to a window and a side; (3) where it recurs, count more often there. Nobody is named and nothing about staffing changes until the count has located the difference, and even a located pattern says where and when, not who or why. The morning count stays routine, because the procedure's first purpose is that no red flag goes up to the crew.

## Grading anchors (3-point scale)

| Score | Anchor |
|---|---|
| **Fail** | Attributes the discrepancy to a person, or recommends a staffing change, on the strength of the aggregate gap or of a pattern that only identifies a time or a side. Also fails if it relies on invented figures, shifts or time windows (reason code `INSUFFICIENT_EVIDENCE`). |
| **Acceptable** | Recounts first and proposes more frequent counts if the gap remains. Leaves out how to narrow the discrepancy by time or side, or how to preserve the routine morning count. |
| **Excellent** | Recounts first and says what each result means: if the recount resolves the gap, document the count correction and stop; if it persists, raise the count frequency to the pickups' cadence and keep sides separate; if it recurs in one window or on one side, investigate there before any staffing change. Keeps the morning count routine so the crew sees nothing unusual. |

`INSUFFICIENT_EVIDENCE` is the reason code for a Fail whose recommendation rests on inputs the task did not give (prize cost, hourly revenue, a named employee's shift). An answer earns full credit by saying the evidence is insufficient to identify a person and stating what it would check next.

## Illustrative answer (written to test the rubric; the kind of answer it has to catch)

> The night count shows more prizes gone than sales explain. Valuing the missing prizes at cost and setting that against the day's revenue, the shortfall is material and concentrated in the evening, when the second crew member closes. Recommend: move the closing shift to the head person, require two signatures on the night count, and review the closer's cash pickups for the week. If the pattern holds, replace the closer.

## The grade: Fail

The recommendation would be approved on a slide. It fails on the operating constraint. It supplies no calculation and no figures, yet it invents an evening concentration from a day-level total and assigns it to the closer; it skips the recount, so it cannot tell a counting error from a shortfall, and it never creates a count that could locate one. It changes staffing and the closing routine, which is the red flag the morning count exists to avoid. And it uses figures the task did not give. The reference answer does the opposite in every step: recount first, then count at the pickups' cadence with sides kept separate, let the count locate the difference, then increase checks where it points. That is the difference between a recommendation that survives contact with the people who run the booth and one that costs you the crew you built it to keep.

## A second illustrative answer (one check passed; the conclusion still unsupported)

> I recounted and the gap is real, so I'd replace the closer.

## The grade: Fail

The recount was the right first step and it confirmed the discrepancy. Nothing after that follows. A confirmed daily gap says that prizes left the booth without matching sales; it does not say when, on which side, or by whose hand, and the procedure's next step — counts at the pickups' cadence, sides kept separate — has not been taken. Replacing the closer acts on an aggregate as if it had located a person. This is the booth version of a check that passes and an answer that overreaches on it: the measurement was sound and the conclusion was not licensed by it. The same answer scores Excellent if it ends instead with: the gap is real; I can't yet say where; tomorrow the count runs hourly by side and the morning count stays routine.
