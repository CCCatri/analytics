"""One vocabulary in every file (VOCABULARY.md). Scans every text file in the repo on disk — tracked or not, records included — and fails
while any retired spelling remains. Only VOCABULARY.md's own Retired column and TAXONOMY.md's Retired-spellings column are read as retired by design.
Run from the repo root: python3 checks/check_vocabulary.py"""
import os, re, sys, collections
TERMS = {"plant / planted / planting -> fault injection, injected fault": r"\bplant(ed|ing|s)?\b",
         "landed / landing / LANDED -> accepted": r"\blanded\b|\blanding\b|\bLANDED\b",
         "wall(s) -> revision": r"\bwalls?\b", "spine -> the specific purpose": r"\bspine\b",
         "heldset / held set -> hold-out set": r"\bheld ?set\b", "information time -> data available before kickoff": r"\binformation time\b",
         "escape(s) -> incident": r"\bescapes?\b", "cross-check -> reconciliation": r"\bcross-check",
         "DONE WHEN -> acceptance criteria": r"\bDONE WHEN\b", "single producer -> authoritative data source": r"\bsingle producer\b",
         "honesty rail -> the specific criterion": r"\bhonesty rail\b", "recount ladder -> root cause analysis": r"\brecount ladder\b",
         "gold/golden labels -> golden set": r"\bgold(en)? (label|example)s?\b", "expected response -> reference answer": r"\bexpected response\b",
         "people management -> team leadership": r"\bpeople management\b",
         "unknown / UNKNOWN (verdict) -> INSUFFICIENT_EVIDENCE": r"\bunknown\b", "\"right\" / \"yes\" (verdict) -> SUPPORTED": r'"(right|yes)"',
         "chain (dependency -> link chain; execution -> run)": r"\bchains?\b", "gate (acceptance) -> quality gate; .gate/ -> .quality-gate/": r"\bgates?\b|\.gate\b",
         "ledger (of a run) -> run log": r"\bledgers?\b", "owner (reviewing) -> reviewer": r"\bowner\b",
         "Contract (rules doc) -> incident-derived rules": r"\bContract\b", "the record -> play-by-play record": r"\bthe record\b",
         "man/men (players) -> player(s)": r"\b(man|men)\b"}
TEXT = (".md", ".py", ".ts", ".tsv", ".yml", ".yaml", ".sh", ".txt", ".json", ".csv", ".stan", ".toml", ".cfg")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist"}
RETIRED_COLUMNS = {"VOCABULARY.md", os.path.join("slate-kit", "TAXONOMY.md"), os.path.join("checks", "check_vocabulary.py")}
files = []; skipped = []
for root, dirs, names in os.walk("."):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for n in names:
        p = os.path.relpath(os.path.join(root, n), ".")
        if not os.path.isfile(p): skipped.append(p); continue   # broken symlinks and specials are not text
        if (n.endswith(TEXT) or "." not in n) and p not in RETIRED_COLUMNS and os.path.getsize(p) < 50_000_000: files.append(p)
texts = {}
for f in files:
    try: texts[f] = open(f, encoding="utf-8", errors="ignore").read()
    except OSError: pass
by_dir = collections.Counter(); total = 0
print(f"VOCABULARY: {len(texts)} text files scanned on disk, no exemptions; {len(skipped)} paths skipped as not regular files ({len([f for f in texts if f.startswith('.gate')])} under .gate/, {sum(1 for f in texts if 'CHARTER' in f)} charter)")
for label, rx in TERMS.items():
    pat = re.compile(rx, 0 if rx.isupper() or '"' in rx or "Contract" in rx else re.I); per = collections.Counter()
    for f, t in texts.items():
        n = len(pat.findall(t))
        if n: per[f] += n; by_dir[f.split(os.sep)[0]] += n
    s = sum(per.values()); total += s
    if s: print(f"  {s:6d}  {label}   e.g. {', '.join(f'{f} {n}' for f, n in per.most_common(3))}")
print("  by top-level folder: " + ", ".join(f"{d} {n}" for d, n in by_dir.most_common(8)))
print(f"VOCABULARY {'PASS' if total == 0 else 'FAIL'}: {total} retired spellings in {len(texts)} files")
sys.exit(0 if total == 0 else 1)
