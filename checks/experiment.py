"""The two-domain executor, first milestone. Runs one case per domain through one entry point and writes one experiment record each:
baseline, intervention, dependency, expected, actual, evidence, and three statuses kept apart — domain_verdict (what the product said),
check_result (what the check said against the expectation), release_status (always 'not a release decision' here; the ledger owns it).
Cases: healix tracked fixture (control), healix 65-row known-wrong variant, NFL slices vs team budget (executed), NFL handoff B2 (read from its run record,
not re-executed: B2 lives inside the adapter test and writes into the run it belongs to). Usage: python3 checks/experiment.py <healix repo path>"""
import json, os, re, subprocess, sys, datetime
HEALIX = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/LocalWork/healix7")
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S"); OUT = os.path.join("out", "experiments", stamp); os.makedirs(OUT, exist_ok=True)
def sh(cmd, cwd): p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True); return p.returncode, p.stdout + p.stderr
def record(**k): k.setdefault("release_status", "not a release decision (the acceptance ledger decides)"); return k
records = []
# healix: control and known-wrong, both executed through the separation instrument
for name, d, expect_false in (("healix tracked fixture (control)", "tests", 0), ("healix 65-row known-wrong variant", "tests/negative/own_copy_65", 3)):
    if d != "tests":  # separation.ts expects a tests-like layout
        scratch = os.path.join(OUT, "hx65"); os.makedirs(f"{scratch}/positive/own_copy", exist_ok=True)
        for f in ("tableA.csv", "tableB.csv"): subprocess.run(["cp", f"{HEALIX}/{d}/{f}", f"{scratch}/positive/own_copy/{f}"], check=True)
        subprocess.run(["cp", f"{HEALIX}/tests/positive/own_copy/expected.tsv", f"{scratch}/positive/own_copy/expected.tsv"], check=True); target = os.path.abspath(scratch)
    else: target = "tests"
    rc, out = sh(["npx", "tsx", "scripts/separation.ts", target], HEALIX); open(f"{OUT}/{name.split()[1]}_separation.txt", "w").write(out)
    m = re.search(r"current rule: false confirmations (\d+), lost controls (\d+)", out); fc, lc = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    pairs = re.findall(r"FALSE CONFIRMATION (A#\d+ x B#\d+)", out)
    records.append(record(case=name, executed=True, baseline="the judge on the tables as given", intervention="none (65-row: five added customers, every address unique)" if expect_false else "none",
        dependency="within-table pairs -> chance bar -> verdict", expected=f"false confirmations {expect_false}, lost controls 0",
        actual=f"false confirmations {fc}, lost controls {lc}" + (f"; pairs {pairs}" if pairs else ""),
        domain_verdict=("SUPPORTED on " + ", ".join(pairs)) if pairs else "no wrong-by-construction pair SUPPORTED",
        check_result="PASS" if (fc == expect_false and lc == 0) else "FAIL", evidence=f"{OUT}/{name.split()[1]}_separation.txt; {HEALIX}/{d}"))
# NFL: slices vs team budget, executed (self-test is the plant)
rc_t, out_t = sh([sys.executable, "checks/check_targets_partition.py", "--self-test"], "."); rc_p, out_p = sh([sys.executable, "checks/check_targets_partition.py", "slate-kit/proj/frozen_draws_2025_w16.npz", "slate-kit/proj/card_2025_w16.csv", "slate-kit/proj/team_draws_2025_w16.npz"], ".")
open(f"{OUT}/nfl_partition.txt", "w").write(out_t + out_p)
m = re.search(r"RECEIVER TARGETS vs PARENT: supported (\d+), refuted (\d+)", out_p)
records.append(record(case="NFL slices vs team budget (2025 w16)", executed=True, baseline="team F2 attempts draw per team-draw", intervention="plant: a conserved synthetic slate and an independent one (self-test)",
    dependency="team draw -> player share draws -> summed receiver targets", expected="self-test PASS (conserved 0 refuted, planted > 0); product: refuted > 0 while slices are drawn apart",
    actual=f"self-test exit {rc_t}: {out_t.strip().splitlines()[-1] if out_t.strip() else ''}; product refuted {m.group(2) if m else None} of {int(m.group(1)) + int(m.group(2)) if m else None}",
    domain_verdict=f"FAIL: receivers over the team budget in {m.group(2)} team-draws" if m else "unreadable", check_result="PASS" if rc_t == 0 and m and int(m.group(2)) > 0 else "FAIL",
    evidence=f"{OUT}/nfl_partition.txt; WORK_ORDER.md 4"))
# NFL: handoff B2, read from the run record
runs = sorted(d for d in os.listdir("out/handoff/runs")) if os.path.isdir("out/handoff/runs") else []
b2 = []; src = None
for r in reversed(runs):
    p = f"out/handoff/runs/{r}/components/record.json"
    if os.path.exists(p): src = p; b2 = [l for l in json.load(open(p))["lines"] if l.strip().startswith("B2")]; break
records.append(record(case=f"NFL handoff B2 (read from run {src.split('/')[3] if src else 'none'})", executed=False, baseline="kit in engine mode on the 2024 w15 fixture", intervention="source draw 0 for LV changed 36 -> 60",
    dependency="engine team draw -> draw_link -> QB Q1 attempts", expected="team root moves at all mapped columns and none unmapped; the QB's attempts move only at mapped columns; the changed value is what draw_link received",
    actual="; ".join(l.strip()[:90] for l in b2) if b2 else "no record", domain_verdict="mapped movement observed" if b2 else "unreadable",
    check_result="PASS" if b2 and all(": PASS" in l for l in b2) else "FAIL", evidence=src or "none"))
json.dump(records, open(f"{OUT}/records.json", "w"), indent=1)
print(f"{'case':46s} {'executed':8s} {'domain verdict':52s} check")
for r in records: print(f"{r['case'][:46]:46s} {str(r['executed']):8s} {r['domain_verdict'][:52]:52s} {r['check_result']}")
print(f"records: {OUT}/records.json")
sys.exit(0 if all(r["check_result"] == "PASS" for r in records) else 1)
