"""Step 1, the baseline: the pre-adapter kit code (draws.py.before and cards.py.before, saved at the adapter rewrite, in checks/fixtures/pre_adapter/) run on the same inputs the candidate will see.
Under HANDOFF_RUN_DIR/baseline/: kit_pre/ is a copy of the live kit with the two saved files in place of draws.py and cards.py and the six replay outputs removed;
kit.py replay runs there (its 'previous' is a copy of the live rows, only because the command wants one; that judgment is not evidence), then the kit-mode card for
2025 w16. Records the pre-adapter and candidate code shas, the run identity (git revision, resolved shared inputs), the live proj/ snapshot, which outputs were
freshly emitted and their shas. The live proj/ is hashed before and after and must be untouched."""
import os, sys, json, shutil, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from handoff_identity import identity, copy_kit, OUTPUTS, sha256
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); KIT = os.path.join(ROOT, "slate-kit")
RUN = os.environ.get("HANDOFF_RUN_DIR")
if not RUN: sys.exit("HANDOFF_RUN_DIR unset - refused; use checks/run_handoff.sh")
OUT = os.path.join(RUN, "baseline")
if os.path.exists(OUT): sys.exit(f"{OUT} exists - refused; one run id holds one baseline")
os.makedirs(OUT); LOG = open(os.path.join(OUT, "full_log.txt"), "w"); LINES = []; ok = True
def say(line): LINES.append(line); print(line, flush=True); LOG.write(line + "\n"); LOG.flush()
def verdict(name, cond, detail=""):
    global ok; ok &= bool(cond); say(f"  {name}: {'PASS' if cond else 'FAIL'}" + (f" | {detail}" if detail else ""))
def files_of(d): return {n: sha256(os.path.join(d, n)) for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))}
def stream(cmd, cwd, env):
    say(f"  cwd {cwd}\n  {' '.join(cmd)}\n"); t0 = time.time(); p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout: print(line, end="", flush=True); LOG.write(line)
    rc = p.wait(); LOG.flush(); say(f"\n  finished in {time.time() - t0:.0f} s, exit {rc}"); return rc
SAVED = os.path.join(ROOT, "checks", "fixtures", "pre_adapter"); PRE_FILES = {f: os.path.join(SAVED, f + ".before") for f in ("draws.py", "cards.py")}
for f, p in PRE_FILES.items():
    if not os.path.exists(p): sys.exit(f"{p} missing - refused; the pre-adapter code is not on disk")
PRE = {f: sha256(p) for f, p in PRE_FILES.items()}; CANDIDATE = {f: sha256(os.path.join(KIT, f)) for f in PRE_FILES}
say(f"run {RUN}\npre-adapter code  draws.py {PRE['draws.py'][:12]} cards.py {PRE['cards.py'][:12]}  (from {SAVED})\ncandidate code    draws.py {CANDIDATE['draws.py'][:12]} cards.py {CANDIDATE['cards.py'][:12]}")
verdict("pre-adapter and candidate code differ in both files", all(PRE[f] != CANDIDATE[f] for f in PRE))
ident = identity(ROOT, KIT); say(f"identity: git {ident['git_head'][:12]} with {len(ident['git_dirty_paths'])} dirty paths; inputs " + ", ".join(f"{d} -> {v['resolved']} ({len(v['files'])} files)" for d, v in ident["inputs"].items()) + f"; RAW_PIN {ident['raw_pin_sha'][:12] if ident['raw_pin_sha'] else None}")
say("\n=== live proj/ snapshot (the inputs both copies start from) ===")
live_before = files_of(os.path.join(KIT, "proj")); say(f"  {len(live_before)} files hashed")
COPY = os.path.join(OUT, "kit_pre"); say(f"\n=== kit_pre at {COPY} ==="); removed = copy_kit(KIT, COPY, say)
for f, p in PRE_FILES.items(): shutil.copy2(p, os.path.join(COPY, f))
say("  draws.py and cards.py replaced by the saved pre-adapter files")
verdict("kit_pre holds the pre-adapter code", all(sha256(os.path.join(COPY, f)) == PRE[f] for f in PRE))
verdict("replay outputs absent in kit_pre/proj before the run", not any(os.path.exists(os.path.join(COPY, "proj", n)) for n in OUTPUTS))
PREV = os.path.join(OUT, "previous_for_command"); os.makedirs(PREV)
for n in ("atlas_rows.csv.gz", "dk_rows.csv.gz"): shutil.copy2(os.path.join(KIT, "proj", n), PREV)
env = {k: v for k, v in os.environ.items() if k not in ("SLATE_ROOT_SOURCE", "SLATE_ROOT_FILE")}
say("\n=== baseline replay (pre-adapter code, kit mode) ===")
rc = stream([sys.executable, "-u", "kit.py", "replay", os.path.join(PREV, "atlas_rows.csv.gz"), os.path.join(PREV, "dk_rows.csv.gz")], COPY, env); verdict("baseline replay exit 0", rc == 0)
emitted = {n: os.path.exists(os.path.join(COPY, "proj", n)) for n in OUTPUTS}; verdict("replay freshly emitted all six outputs (absent before, present after)", all(emitted.values()), f"{emitted}")
say("\n=== baseline card 2025 w16 (pre-adapter code, kit mode) ===")
rc = stream([sys.executable, "-u", "-c", "import sys, cards; sys.exit(cards.card(2025, 16))"], COPY, env); verdict("baseline card exit 0", rc == 0)
NAMES = OUTPUTS + ("card_2025_w16.csv",); outputs = {n: (sha256(os.path.join(COPY, "proj", n)) if os.path.exists(os.path.join(COPY, "proj", n)) else None) for n in NAMES}
for n, h in outputs.items(): say(f"  kit_pre/proj/{n}: {h[:12] if h else 'MISSING'}")
verdict("baseline outputs present", all(outputs.values()))
live_after = files_of(os.path.join(KIT, "proj")); verdict("live proj/ untouched", live_before == live_after, f"changed {[n for n in set(live_before) | set(live_after) if live_before.get(n) != live_after.get(n)]}")
say(f"\nBASELINE (pre-adapter code on the same inputs): {'PASS' if ok else 'FAIL'}")
json.dump(dict(run=RUN, pre_code=PRE, candidate=CANDIDATE, identity=ident, live_proj_snapshot=live_before, removed_before_run=removed, emitted=emitted, outputs=outputs, verdict="PASS" if ok else "FAIL", lines=LINES), open(os.path.join(OUT, "record.json"), "w"), indent=1)
open(os.path.join(OUT, "RESULT.txt"), "w").write("\n".join(LINES) + "\n"); LOG.close(); print(f"written {OUT}/RESULT.txt, full_log.txt, record.json"); sys.exit(0 if ok else 1)
