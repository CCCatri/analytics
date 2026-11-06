"""The résumé and the repository copy their claims from CLAIMS.md. This checks: every repo path named in CLAIMS.md exists; no first cell is still pending; and, if a
résumé text file is given, every first cell appears in it verbatim (quotes stripped), except cells marked "Repo only". python3 checks/check_claims.py [resume.txt]  — exit 1 on any failure."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); s = open(os.path.join(ROOT, "CLAIMS.md")).read(); ok = True
rows = [r for r in s.split("\n") if r.startswith("| ") and not r.startswith("| Responsibility") and not r.startswith("|---")]
for p in sorted(set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|py|sh|json|txt|csv)|cases/evidence/[A-Za-z0-9_./-]+/)`", s))):
    if not os.path.exists(os.path.join(ROOT, p)): ok = False; print(f"  MISSING path: {p}")
pending = [r.split("|")[1].strip() for r in rows if "pending" in r.split("|")[2]]
for name in pending: ok = False; print(f"  PENDING sentence: {name}")
if len(sys.argv) > 1:
    norm = lambda t: re.sub(r"\s+", " ", t.replace("’", "'").replace("‘", "'"))
    resume = norm(open(sys.argv[1]).read())
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]; claim = cells[1].strip().strip('"').strip("_[]")
        if "pending" in claim or claim.startswith("Repo only;"): continue
        if norm(claim) not in resume: ok = False; print(f"  NOT ON RESUME verbatim: {cells[0]}: {claim[:70]}…")
print(f"CLAIMS: {'PASS' if ok else 'FAIL'} ({len(rows)} rows, {len(pending)} pending)"); sys.exit(0 if ok else 1)
