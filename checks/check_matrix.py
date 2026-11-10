"""matrix.tsv, the evidence records, is honest about where each record stands. Every tier is one of VOCABULARY.md's evidence tiers or work states; every
concept is an ID in VOCABULARY.md's concept table; a CI Passed record names its run; an Evidence pushed record points at a file that exists; an analytics
revision resolves (skipped, and said so, in a shallow clone). Self-test first: four injected faults must each be caught, else the check calls itself blind
and exits 1. Usage: python3 checks/check_matrix.py [--healix PATH] (with PATH, healix records' files are checked too)."""
import csv, io, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS = {"Someone else's record", "CI Passed", "Evidence pushed", "On Mac", "Account only", "Not built", "Test written"}
RUN = re.compile(r"actions/runs/\d+|\b(verify|demo) #\d+|CI run \d+|CI \d+")
def concept_ids():
    return set(re.findall(r"^\| [^|]+ \| `([a-z_]+)` \|", open(os.path.join(ROOT, "VOCABULARY.md"), encoding="utf-8").read(), re.M))
def shallow():
    return subprocess.run(["git", "-C", ROOT, "rev-parse", "--is-shallow-repository"], capture_output=True, text=True).stdout.strip() == "true"
def problems(rows, ids, healix=None, check_revisions=True):
    out = []
    for i, r in enumerate(rows, 2):
        if r["repo"] not in ("analytics", "healix"): out.append((i, f"repo {r['repo']!r}"))
        if r["tier"] not in TIERS: out.append((i, f"tier {r['tier']!r} is not on the scale"))
        if r["concept"] not in ids: out.append((i, f"concept {r['concept']!r} is not in VOCABULARY.md's concept table"))
        if r["tier"] == "CI Passed" and not RUN.search(r["run"] + " " + r["pointer"]): out.append((i, "CI Passed names no run"))
        root = ROOT if r["repo"] == "analytics" else healix
        if r["tier"] == "Evidence pushed" and root:
            toks = [p.strip().split(" ")[0] for p in r["pointer"].split(";")]
            if not any(os.path.exists(os.path.join(root, t.rstrip("/"))) for t in toks if t and not t.startswith("http")): out.append((i, f"Evidence pushed, but no file in {r['pointer']!r} exists"))
        if check_revisions and r["repo"] == "analytics" and subprocess.run(["git", "-C", ROOT, "cat-file", "-e", r["revision"] + "^{commit}"], capture_output=True).returncode != 0:
            out.append((i, f"revision {r['revision']} does not resolve"))
    return out
def self_test(rows, ids):
    good = next(r for r in rows if r["repo"] == "analytics" and r["tier"] == "CI Passed")
    faults = {"a CI Passed record with no run": dict(good, run="replay", pointer="checks/check_claims.py"),
              "an Evidence pushed record whose file is missing": dict(good, tier="Evidence pushed", pointer="cases/no_such_file.md"),
              "a tier off the scale": dict(good, tier="measured"),
              "a concept not in the table": dict(good, concept="no_such_concept")}
    missed = [name for name, bad in faults.items() if not problems([bad], ids, check_revisions=False)]
    for name in faults: print(f"  injected fault: {name} -> {'MISSED' if name in missed else 'caught'}")
    return not missed and not problems([good], ids, check_revisions=False)
if __name__ == "__main__":
    healix = sys.argv[sys.argv.index("--healix") + 1] if "--healix" in sys.argv else None
    rows = list(csv.DictReader(io.StringIO(open(os.path.join(ROOT, "matrix.tsv"), encoding="utf-8").read()), delimiter="\t")); ids = concept_ids()
    if not self_test(rows, ids): print("MATRIX self-test: FAIL (the check is blind)"); sys.exit(1)
    print("MATRIX self-test: PASS (four injected faults caught)")
    revs = not shallow(); print("revisions checked" if revs else "revisions not checked (shallow clone)")
    if not healix: print("healix records' files not checked (no --healix path)")
    found = problems(rows, ids, healix, revs)
    for t in sorted(TIERS): print(f"  {t:22s} {sum(r['tier'] == t for r in rows)}")
    for i, p in found: print(f"  row {i}: {p}")
    print(f"MATRIX: {'PASS' if not found else 'FAIL'} ({len(rows)} records, {len(found)} problems)"); sys.exit(0 if not found else 1)
