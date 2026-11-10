"""The résumé and the repository copy their claims from CLAIMS.md. This checks: every repo path named in CLAIMS.md exists; no first cell is still pending; and, if a
résumé text file is given, every first cell appears in it verbatim (quotes stripped), except cells marked "Repo only". python3 checks/check_claims.py [resume.txt]  — exit 1 on any failure.
Self-test, run first on every call: a path that does not exist must be flagged MISSING, and (when a résumé is given) a copy of it with one word in the middle of a
quoted sentence altered must be flagged NOT ON RESUME. If either goes unflagged the check is blind: it says so and exits 1 before its own verdict."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); s = open(os.path.join(ROOT, "CLAIMS.md"), encoding="utf-8").read()
rows = [r for r in s.split("\n") if r.startswith("| ") and not r.startswith("| Responsibility") and not r.startswith("|---")]
PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|py|sh|json|txt|csv)|cases/evidence/[A-Za-z0-9_./-]+/)`")
norm = lambda t: re.sub(r"\s+", " ", t.replace("’", "'").replace("‘", "'"))


def missing_paths(text):
    return [p for p in sorted(set(PATH_RE.findall(text))) if not os.path.exists(os.path.join(ROOT, p))]


def claims():
    out = []
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]; claim = cells[1].strip().strip('"').strip("_[]")
        if "pending" in claim or claim.startswith("Repo only;"): continue
        out.append((cells[0], claim))
    return out


def not_on(resume_text):
    R = norm(resume_text)
    return [(n, c) for n, c in claims() if norm(c) not in R]


def self_test(resume_text):
    blind = []
    if not missing_paths("`checks/no_such_file_for_the_self_test.py`"):
        blind.append("a path that does not exist went unflagged")
    if resume_text is not None:
        on = [(n, c) for n, c in claims() if norm(c) in norm(resume_text)]
        if on:
            name, c = on[0]; w = c.split(); i = len(w) // 2
            altered = " ".join(w[:i] + ["X" + w[i]] + w[i + 1:])   # a word in the middle changed, so the original no longer appears inside the copy
            mutated = norm(resume_text).replace(norm(c), norm(altered))
            if name not in [n for n, _ in not_on(mutated)]:
                blind.append(f"an altered sentence ({name}) went unflagged")
    return blind


resume_text = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else None
blind = self_test(resume_text)
if blind:
    print("CLAIMS self-test: FAIL, the check is blind:", "; ".join(blind)); sys.exit(1)
print(f"CLAIMS self-test: PASS (a missing path is flagged{'; an altered sentence is flagged' if resume_text is not None else ''})")
ok = True
for p in missing_paths(s): ok = False; print(f"  MISSING path: {p}")
pending = [r.split("|")[1].strip() for r in rows if "pending" in r.split("|")[2]]
for name in pending: ok = False; print(f"  PENDING sentence: {name}")
if resume_text is not None:
    for n, c in not_on(resume_text): ok = False; print(f"  NOT ON RESUME verbatim: {n}: {c[:70]}…")
print(f"CLAIMS: {'PASS' if ok else 'FAIL'} ({len(rows)} rows, {len(pending)} pending)"); sys.exit(0 if ok else 1)
