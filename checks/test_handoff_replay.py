"""Step 3, A2: the candidate's paired replay in kit mode, isolated, against the baseline step's outputs. Under HANDOFF_RUN_DIR/replay/: kit_new/ is a copy of the live
kit (candidate code; the six replay outputs removed from its proj/), taken from the same live proj/ snapshot the baseline copy was (hashes compared), with the same run
identity; kit.py replay runs there with the SLATE variables removed and 'previous' = the baseline rows. Judged: live proj/ untouched; every output freshly emitted;
the grader's product_judgment.csv (every cell paired == previous == new, every verdict UNCHANGED) reported as what the kit decided; and, separately, the new rows,
atlas.csv and ladder.csv compared with the baseline's directly - same sha, or else same key set on the key columns found on disk and every column identical by value
after sorting (NaN as a value, no tolerance). Raw values are kept: the compared files stay in kit_new/proj and baseline/kit_pre/proj."""
import os, sys, json, shutil, subprocess, time, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from handoff_identity import identity, copy_kit, OUTPUTS, sha256
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); KIT = os.path.join(ROOT, "slate-kit")
RUN = os.environ.get("HANDOFF_RUN_DIR")
if not RUN: sys.exit("HANDOFF_RUN_DIR unset - refused; use checks/run_handoff.sh")
BREC = os.path.join(RUN, "baseline", "record.json")
if not os.path.exists(BREC): sys.exit("baseline/record.json missing - refused; run the baseline step first")
brec = json.load(open(BREC)); BASE_PROJ = os.path.join(RUN, "baseline", "kit_pre", "proj")
OUT = os.path.join(RUN, "replay")
if os.path.exists(OUT): sys.exit(f"{OUT} exists - refused; one run id holds one replay record")
os.makedirs(OUT); LOG = open(os.path.join(OUT, "full_log.txt"), "w"); LINES = []; ok = True
def say(line): LINES.append(line); print(line, flush=True); LOG.write(line + "\n"); LOG.flush()
def verdict(name, cond, detail=""):
    global ok; ok &= bool(cond); say(f"  {name}: {'PASS' if cond else 'FAIL'}" + (f" | {detail}" if detail else ""))
def files_of(d): return {n: sha256(os.path.join(d, n)) for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))}
CANDIDATE = {f: sha256(os.path.join(KIT, f)) for f in ("draws.py", "cards.py")}
say(f"run {RUN}\ncandidate draws.py {CANDIDATE['draws.py'][:12]} cards.py {CANDIDATE['cards.py'][:12]} | baseline (pre-adapter code) draws.py {brec['pre_code']['draws.py'][:12]} cards.py {brec['pre_code']['cards.py'][:12]}")
verdict("candidate code is the code the baseline step recorded", CANDIDATE == brec["candidate"])
ident = identity(ROOT, KIT); verdict("same run identity as the baseline step (git revision, kit code, resolved shared inputs, RAW_PIN)", ident == brec["identity"], f"git {ident['git_head'][:12]}, {len(ident['git_dirty_paths'])} dirty paths")
live_before = files_of(os.path.join(KIT, "proj")); verdict("live proj/ is the snapshot the baseline copy was taken from", live_before == brec["live_proj_snapshot"], f"differs {[n for n in set(live_before) | set(brec['live_proj_snapshot']) if live_before.get(n) != brec['live_proj_snapshot'].get(n)]}")
ROWS = ("atlas_rows.csv.gz", "dk_rows.csv.gz"); BASE = os.path.join(OUT, "baseline_rows"); os.makedirs(BASE)
for n in ROWS: shutil.copy2(os.path.join(BASE_PROJ, n), BASE)
verdict("baseline rows are the baseline step's outputs", all(sha256(os.path.join(BASE, n)) == brec["outputs"][n] for n in ROWS), " ".join(f"{n} {brec['outputs'][n][:12]}" for n in ROWS))
COPY = os.path.join(OUT, "kit_new"); say(f"\n=== kit_new at {COPY} ==="); removed = copy_kit(KIT, COPY, say)
verdict("kit_new holds the candidate code", all(sha256(os.path.join(COPY, f)) == CANDIDATE[f] for f in CANDIDATE))
verdict("replay outputs absent in kit_new/proj before the run", not any(os.path.exists(os.path.join(COPY, "proj", n)) for n in OUTPUTS))
env = {k: v for k, v in os.environ.items() if k not in ("SLATE_ROOT_SOURCE", "SLATE_ROOT_FILE")}
cmd = [sys.executable, "-u", "kit.py", "replay", os.path.join(BASE, ROWS[0]), os.path.join(BASE, ROWS[1])]
say(f"\n=== A2 candidate replay (kit mode: SLATE variables removed; previous = the baseline rows) ===\n  cwd {COPY}\n  {' '.join(cmd)}\n"); t0 = time.time()
p = subprocess.Popen(cmd, cwd=COPY, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in p.stdout: print(line, end="", flush=True); LOG.write(line)
rc = p.wait(); LOG.flush(); say(f"\n  replay finished in {time.time() - t0:.0f} s")
verdict("A2 replay exit 0", rc == 0, f"exit {rc}")
live_after = files_of(os.path.join(KIT, "proj")); verdict("A2 live proj/ untouched by the replay", live_before == live_after, f"changed {[n for n in set(live_before) | set(live_after) if live_before.get(n) != live_after.get(n)]}")
emitted = {n: os.path.exists(os.path.join(COPY, "proj", n)) for n in OUTPUTS}; verdict("A2 replay freshly emitted all six outputs (absent before, present after)", all(emitted.values()), f"{emitted}")
say("\n=== A2 grader verdict (product_judgment.csv in kit_new/proj/, previous = baseline rows) - what the kit decided ===")
jp = os.path.join(COPY, "proj", "product_judgment.csv"); grader = None
if os.path.exists(jp):
    j = pd.read_csv(jp); need = {"paired_rows", "previous_rows", "new_rows", "verdict"}
    if need <= set(j.columns):
        paired = bool((j.paired_rows == j.previous_rows).all() and (j.paired_rows == j.new_rows).all() and (j.paired_rows > 0).all()); unchanged = bool((j.verdict == "UNCHANGED").all())
        grader = dict(cells=int(len(j)), paired=paired, verdicts=j.verdict.value_counts().to_dict())
        verdict("A2 grader: every cell paired == previous == new, > 0", paired, f"cells {len(j)}"); verdict("A2 grader: every verdict UNCHANGED", unchanged, f"{grader['verdicts']}")
    else: verdict("A2 grader columns as expected", False, f"columns on disk {list(j.columns)}")
else: verdict("A2 grader wrote product_judgment.csv", False, "absent after the replay")
say("\n=== A2 direct comparison: candidate outputs against the baseline's (same inputs, code before vs after) - independent of the grader ===")
KEYS = ("season", "week", "player_id", "term", "rung", "book", "line", "team", "position", "key", "cell")
def same_by_value(a, b):
    out = {}
    for c in a.columns:
        x, y = a[c].reset_index(drop=True), b[c].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y): n = int((~((x.astype(float) == y.astype(float)) | (x.isna() & y.isna()))).sum())
        else: n = int((x.fillna("").astype(str) != y.fillna("").astype(str)).sum())
        if n: out[c] = n
    return out
compared = {}
for n in ROWS + ("atlas.csv", "ladder.csv"):
    newp, basep = os.path.join(COPY, "proj", n), os.path.join(BASE_PROJ, n)
    if not os.path.exists(newp) or not os.path.exists(basep): verdict(f"A2 {n}: present in both copies", False, f"candidate {os.path.exists(newp)}, baseline {os.path.exists(basep)}"); continue
    hn, hb = sha256(newp), sha256(basep)
    if hn == hb: verdict(f"A2 {n}: identical to the baseline output (same sha256)", True, hn[:12]); compared[n] = dict(sha_equal=True, sha256=hn); continue
    b, nw = pd.read_csv(basep), pd.read_csv(newp); key = [c for c in KEYS if c in b.columns and c in nw.columns]
    say(f"  {n}: sha differs ({hb[:12]} vs {hn[:12]}); baseline {b.shape} new {nw.shape}; key columns on disk {key}; columns {list(b.columns)}")
    verdict(f"A2 {n}: nonempty, same columns, same row count", len(b) > 0 and list(b.columns) == list(nw.columns) and len(b) == len(nw))
    if len(key) >= 2 and list(b.columns) == list(nw.columns):
        kb, kn = set(map(tuple, b[key].astype(str).values)), set(map(tuple, nw[key].astype(str).values))
        verdict(f"A2 {n}: paired key set identical on {key}", kb == kn and len(kb) > 0, f"baseline keys {len(kb)}, new keys {len(kn)}, baseline only {len(kb - kn)}, new only {len(kn - kb)}")
        cols = list(b.columns); sb, sn = b.sort_values(cols, kind="mergesort"), nw.sort_values(cols, kind="mergesort")
        diff = same_by_value(sb, sn) if len(sb) == len(sn) else {"row count": abs(len(sb) - len(sn))}
        verdict(f"A2 {n}: every column identical by value after sorting (NaN as a value, no tolerance)", not diff, f"differing columns {diff}")
        compared[n] = dict(sha_equal=False, key=key, keys=len(kb), key_set_equal=(kb == kn), rows=len(b), differing_columns=diff)
    else: verdict(f"A2 {n}: key columns found on disk", False, "fewer than two of the candidate key columns present - refused")
say(f"\nA2 PAIRED REPLAY (kit mode): {'PASS' if ok else 'FAIL'} | the overall verdict is issued by checks/test_handoff_final.py")
json.dump(dict(run=RUN, candidate=CANDIDATE, identity=ident, live_proj_snapshot=live_before, baseline_outputs=brec["outputs"], removed_before_run=removed, emitted=emitted, replay_exit=rc, grader=grader, compared=compared, verdict="PASS" if ok else "FAIL", lines=LINES), open(os.path.join(OUT, "record.json"), "w"), indent=1)
open(os.path.join(OUT, "A2.txt"), "w").write("\n".join(LINES) + "\n"); LOG.close(); print(f"written {OUT}/A2.txt, full_log.txt, record.json"); sys.exit(0 if ok else 1)
