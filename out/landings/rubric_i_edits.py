import sys, pathlib
EDITS = [
 ("| All three present? (Mercor bullets: the result may be stated at summary level, per C11) |",
  "| All three present? (Mercor bullets: the result may be stated at summary level, per C11.) A context line that C4 marks CONTEXT (a scope line, a header line, the skills line) is exempt here too and marked CONTEXT |"),
 ("NFL and Healix = expected behavior, and in each a bullet stating a decision made after weighing what a choice gains against what it costs (finding or fixing a defect is not that decision)",
  "NFL and Healix = expected behavior checked against a standard, and across the two sections at least one bullet stating a decision made after weighing what a choice gains against what it costs (finding or fixing a defect is not that decision; a second such bullet from the same kind of project is a repeat, not a requirement)"),
 ("Operations Evals = an evaluation item tested against known answers, and the decision it led to",
  "Operations Evals = an evaluation item tested against known answers (a decision the test led to may appear in the same bullet as its outcome; it is not a second strength under C4)"),
]
def apply(t):
    for o, n in EDITS:
        if t.count(o) != 1: sys.exit(f"REFUSED: {o[:60]!r} found {t.count(o)} times")
        t = t.replace(o, n)
    return t
if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    pathlib.Path(dst).write_text(apply(pathlib.Path(src).read_text())); print(f"{dst}: {len(EDITS)} rubric edits")
