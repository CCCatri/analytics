"""One vocabulary in every file (VOCABULARY.md). Scans every text file in the repo on disk - tracked or not, records included - and fails
while any retired spelling remains. Only VOCABULARY.md's Retired column, TAXONOMY.md's Retired-spellings column and this file are read as retired by design.
Run from the repo root: python3 checks/check_vocabulary.py          (the verdict: everything)
                        python3 checks/check_vocabulary.py --live   (the work list: generated outputs under out/ and slate-kit/proj/ left out)"""
import os, re, sys, collections
TERMS = {  # label: pattern.  Canonical phrases that contain a retired word (quality gate, link chain, acceptance ledger, project owner) are excluded by lookbehind.
    "plant / planted / planting -> fault injection, injected fault": r"\bplant(ed|ing|s)?\b",
    "landed / landing / LANDED -> accepted": r"\blanded\b|\blanding\b(?!_zone| zone)|\bLANDED\b",
    "wall(s) -> revision": r"\bwalls?\b",
    "spine -> the specific purpose": r"\bspine\b",
    "heldset / held set -> hold-out set": r"\bheld ?set\b",
    "information time -> data available before kickoff": r"\binformation time\b",
    "escape(s) -> incident": r"(?<!re\.)(?<!un)\bescapes?\b",
    "cross-check -> reconciliation": r"\bcross-check",
    "DONE WHEN -> acceptance criteria": r"\bDONE WHEN\b",
    "single producer -> authoritative data source": r"\bsingle producer\b",
    "honesty rail -> the specific criterion": r"\bhonesty rail\b",
    "recount ladder -> root cause analysis": r"\brecount ladder\b",
    "gold/golden labels -> golden set": r"\bgold(en)? (label|example)s?\b",
    "expected response -> reference answer": r"\bexpected response\b",
    "people management -> team leadership": r"\bpeople management\b",
    "unknown / UNKNOWN (verdict) -> INSUFFICIENT_EVIDENCE": r"\bunknown\b",
    "\"right\" / \"yes\" (verdict) -> SUPPORTED": r'"(right|yes)"',
    "chain (dependency -> link chain; execution -> run)": r"(?<!link )(?<!Link )(?<!LINK )(?<!link_)\bchains?\b",
    "gate (acceptance -> quality gate; .gate/ -> .quality-gate/)": r"(?<!quality )(?<!Quality )(?<!QUALITY )(?<!quality_)(?<!quality-)\bgates?\b|\.gate\b",
    "ledger (of a run -> run log; of the charter -> acceptance ledger)": r"(?<!acceptance )(?<!Acceptance )(?<!acceptance-)(?<!acceptance_)\bledgers?\b",
    "owner (reviewing -> reviewer; owning -> project owner)": r"(?<!project )(?<!Project )(?<!PROJECT_)\bowner\b",
    "Contract (rules doc) -> incident-derived rules": r"\bContract\b",
    "the record -> play-by-play record": r"\bthe record\b",
    "man/men (players) -> player(s)": r"\b(man|men)\b",
}
CASE_SENSITIVE = {"Contract (rules doc) -> incident-derived rules", "\"right\" / \"yes\" (verdict) -> SUPPORTED", "DONE WHEN -> acceptance criteria"}
TEXT = (".md", ".py", ".ts", ".tsv", ".yml", ".yaml", ".sh", ".txt", ".json", ".csv", ".stan", ".toml", ".cfg")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist"}
LIVE = "--live" in sys.argv
GENERATED = {os.path.join(".", "out"), os.path.join(".", "slate-kit", "proj")}
RETIRED_COLUMNS = {"VOCABULARY.md", os.path.join("slate-kit", "TAXONOMY.md"), os.path.join("slate-kit", "TAXONOMY_short_names.tsv"), os.path.join("checks", "check_vocabulary.py")}
SOURCE_DATA = (os.path.join(".", "data"), os.path.join(".", "slate-kit", "data"), os.path.join(".", "slate-kit", "archive"))   # files other people wrote (nflverse, DraftKings caches): raw files keep source spellings (TAXONOMY rule); player surnames are not our vocabulary
files, skipped = [], []
for root, dirs, names in os.walk("."):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (LIVE and os.path.join(root, d) in GENERATED) and os.path.join(root, d) not in SOURCE_DATA]
    for n in names:
        p = os.path.relpath(os.path.join(root, n), ".")
        if not os.path.isfile(p): skipped.append(p); continue
        if (n.endswith(TEXT) or "." not in n) and p not in RETIRED_COLUMNS and os.path.getsize(p) < 50_000_000: files.append(p)
texts = {}
for f in files:
    try: texts[f] = open(f, encoding="utf-8", errors="ignore").read()
    except OSError: pass
by_dir = collections.Counter(); total = 0
print(f"VOCABULARY{' (live view: out/ and slate-kit/proj/ left out)' if LIVE else ''}: {len(texts)} text files scanned; {len(skipped)} paths skipped as not regular files")
for label, rx in TERMS.items():
    pat = re.compile(rx, 0 if label in CASE_SENSITIVE else re.I); per = collections.Counter()
    for f, t in texts.items():
        n = len(pat.findall(t))
        if n: per[f] += n; by_dir[f.split(os.sep)[0]] += n
    s = sum(per.values()); total += s
    if s: print(f"  {s:7d}  {label}   e.g. {', '.join(f'{f} {n}' for f, n in per.most_common(3))}")
print("  by top-level folder: " + ", ".join(f"{d} {n}" for d, n in by_dir.most_common(10)))
print(f"VOCABULARY {'PASS' if total == 0 else 'FAIL'}: {total} retired spellings in {len(texts)} files")
sys.exit(0 if total == 0 else 1)
