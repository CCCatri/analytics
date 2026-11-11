import sys, pathlib
W5_OLD_START = "| W5 | Fits the listing applied to |"
W5_NEW = ("| W5 | Fits the listings applied to | Two rejections (a Mac power-user listing requiring a bachelor's or master's degree; a creative listing requiring design judgment and a portfolio) that no rubric criterion predicted; a page can be true and still miss what the listings pay for | "
 "Every round, delta or full, using the attached listings file. (a) One row per must-have code in the file: the résumé line that meets it (quote) or NONE, then three marks. WHERE: FIRST READ (inside the first-read fields: most recent title and the line under it, headline, first Summary sentence, skills line, first bullet of the most recent job) / BURIED (elsewhere on the page) / MISSING. SIZE: FULL / PARTIAL / SHORT, by whether the evidence matches the years, scale or level the must-have names (years count from every role whose work meets it once its terms are translated, per C15; one engagement against a plural ask is PARTIAL). PROOF: the line's C5 tier, and who relied on it (C17) or NONE. "
 "(b) Score each must-have as WHERE (1 / 0.5 / 0) x SIZE (1 / 0.5 / 0) x PROOF (tier 1 or 2 = 1, tier 3 = 0.85, tier 4 = 0.7, each less 0.1 when no one relied on it). Average the must-haves within each listing, multiply by its pay midpoint, and report each listing and the total as a share of the maximum. "
 "(c) Form items the file marks FORM (hours, location, equipment) are listed with the confirmed answer and not scored. A MISSING that no translation of his history can meet (a degree, a credential, years tied to a title) = do not apply to that listing |")
EDITS = [
 ("A context line that C4 marks CONTEXT (a scope line, a header line, the skills line) is exempt here too and marked CONTEXT |",
  "A context line that C4 marks CONTEXT (a header, scope or skills line) is exempt only for identity, dates, place, scale, who did the work and when it went public; any capability claim or figure in it is graded under C3 and C13. A header may hold at most one verified work clause, and only when that clause is the main proof of a listing must-have (C17) |", 1),
 ("Name its strength: define what should happen / test a known-good and known-bad case / find the discrepancy before acting / weigh what a change fixes and costs / turn a failure into a repeatable check / refuse to guess",
  "Name its strength: define what should happen / test a known-good and known-bad case / find the discrepancy before acting / weigh what a change fixes and costs / turn a failure into a repeatable check / refuse to guess / judge people against a standard set beforehand / coordinate people, schedules, money and suppliers / make a recommendation someone adopted / explain why a piece of work succeeds or fails", 1),
 ("Jargon a reader may not know but would not misread (CI, fixture) is noted, not failed |",
  "Jargon a reader may not know but would not misread (CI, fixture) is noted, not failed |\n| C17 | Serves a listing, and says who relied on it | Screener and Interviewer | A true line that proves nothing a listing asks for spends the screener's one read; the listings pay for work someone else acted on (\"analyses someone made a decision on\", \"the client-facing recommendation\") | Name the must-have code from the listings file that the bullet proves, and who relied on its result (quote the words) or NONE. A bullet that proves no must-have = CUT, unless it is the only support for a Summary clause. NONE for reliance is reported, not failed; it lowers the PROOF mark in W5 |", 1),
 ("C1-C16", "C1-C17", 3),
 ("CUT (fails C11 or C14, or proves nothing).", "CUT (fails C11 or C14, proves nothing, or proves no listing must-have under C17).", 1),
 ("5. Whole: W1-W5 results (W5 only when a listing is attached).", "5. Whole: W1-W4 results, then the W5 table and its score (every round).", 1),
 ("3. For terms: VOCABULARY.md in the cloned repositories; where terms conflict, it decides",
  "3. For terms: VOCABULARY.md in the cloned repositories; where terms conflict, it decides\n4. The listings file: the must-have codes, quoted requirements and pay of the listings applied to; W5 and C17 read it", 1),
 ("Section and whole-résumé criteria are re-scored only where a listed bullet changes them.",
  "Section and whole-résumé criteria are re-scored only where a listed bullet changes them; W5 is scored every round, delta or full.", 1),
]
def apply(t):
    for o, n, k in EDITS:
        if t.count(o) != k: sys.exit(f"REFUSED: {o[:60]!r} found {t.count(o)} times (want {k})")
        t = t.replace(o, n)
    L = t.split("\n"); h = [i for i, l in enumerate(L) if l.startswith(W5_OLD_START)]
    if len(h) != 1: sys.exit(f"REFUSED: W5 row found {len(h)} times")
    L[h[0]] = W5_NEW
    return "\n".join(L)
if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    pathlib.Path(dst).write_text(apply(pathlib.Path(src).read_text())); print(f"{dst}: {len(EDITS) + 1} rubric edits")
