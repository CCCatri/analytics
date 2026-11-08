"""The two-domain executor, first milestone. Runs one case per domain through one entry point and writes one experiment record each:
baseline, intervention, dependency, expected, actual, evidence, and three statuses kept apart — domain_verdict (what the product said),
check_result (what the check said against the expectation), release_status (always 'not a release decision' here; the ledger owns it).
Cases: healix tracked fixture (control), healix 65-row known-wrong variant, NFL slices vs team budget (executed), NFL handoff B2 (executed through checks/perturb_handoff.py, the same callable the adapter test uses), and the shared check 'only these IDs changed' (checks/changed_ids.py) on NFL kit columns and Healix labeled pairs, each with injected faults named by ID. Usage: python3 checks/experiment.py <healix repo path> [pinned proj dir with atlas.csv and ladder.csv] [frozen draws .npz] [card .csv] [team draws .npz] [partition scope label]"""
import json, os, re, subprocess, sys, datetime, hashlib
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
    pairs = re.findall(r"(A#\d+ x B#\d+)\s+current SUPPORTED", out)
    records.append(record(case=name, executed=True, baseline="the judge on the tables as given", intervention="none (65-row: five added customers, every address unique)" if expect_false else "none",
        dependency="within-table pairs -> chance bar -> verdict", expected=f"false confirmations {expect_false}, lost controls 0",
        actual=f"false confirmations {fc}, lost controls {lc}" + (f"; pairs {pairs}" if pairs else ""),
        domain_verdict=("SUPPORTED on " + ", ".join(pairs)) if pairs else "no wrong-by-construction pair SUPPORTED",
        check_result="PASS" if (fc == expect_false and lc == 0 and len(pairs) == expect_false) else "FAIL", evidence=f"{OUT}/{name.split()[1]}_separation.txt; {HEALIX}/{d}"))
# NFL: slices vs team budget, executed (self-test is the plant)
rc_t, out_t = sh([sys.executable, "checks/check_targets_partition.py", "--self-test"], "."); PARTITION_INPUTS = sys.argv[3:6] if len(sys.argv) > 5 else ["slate-kit/proj/frozen_draws_2025_w16.npz", "slate-kit/proj/card_2025_w16.csv", "slate-kit/proj/team_draws_2025_w16.npz"]   # frozen draws, card, team draws — named by the caller
PARTITION_SCOPE = sys.argv[6] if len(sys.argv) > 6 else "2025 w16"
rc_p, out_p = sh([sys.executable, "checks/check_targets_partition.py", *PARTITION_INPUTS], ".")
open(f"{OUT}/nfl_partition.txt", "w").write(out_t + out_p)
m = re.search(r"RECEIVER TARGETS vs PARENT: supported (\d+), refuted (\d+)", out_p)
records.append(record(case=f"NFL slices vs team budget ({PARTITION_SCOPE})", executed=True, baseline="team F2 attempts draw per team-draw", intervention="plant: a conserved synthetic slate and an independent one (self-test)",
    dependency="team draw -> player share draws -> summed receiver targets", expected="self-test PASS (conserved 0 refuted, planted > 0); product: refuted > 0 while slices are drawn apart",
    actual=f"self-test exit {rc_t}: {out_t.strip().splitlines()[-1] if out_t.strip() else ''}; product refuted {m.group(2) if m else None} of {int(m.group(1)) + int(m.group(2)) if m else None}",
    domain_verdict=f"FAIL: receivers over the team budget in {m.group(2)} team-draws" if m else "unreadable", check_result="PASS" if rc_t == 0 and m and int(m.group(2)) > 0 else "FAIL",
    evidence=f"{OUT}/nfl_partition.txt; WORK_ORDER.md 4"))
# NFL: handoff B2, executed through the callable concept
sys.path.insert(0, "checks"); from perturb_handoff import perturb_handoff
pinned = sys.argv[2] if len(sys.argv) > 2 else "slate-kit/proj"   # the pinned atlas.csv/ladder.csv the card grades against, named by the caller, never looked up
pinned_sha = {f: hashlib.sha256(open(os.path.join(pinned, f), "rb").read()).hexdigest()[:12] for f in ("atlas.csv", "ladder.csv")}
b2 = perturb_handoff(os.path.abspath("out/handoff/root_draws_2024_w15.npz"), "LV", 0, 24, os.path.abspath(f"{OUT}/nfl_b2"), os.path.abspath(pinned))
json.dump({k: v for k, v in b2.items() if k != "checks"} | {"checks": [[n, bool(c), d] for n, c, d in b2["checks"]]}, open(f"{OUT}/nfl_b2.json", "w"), indent=1)
records.append(record(case="NFL handoff B2 (executed via perturb_handoff)", executed=True, baseline="kit in engine mode on the 2024 w15 fixture", intervention=f"source draw 0 for LV changed {b2.get('source_before')} -> {b2.get('source_after')}",
    dependency="engine team draw -> draw_link -> QB Q1 attempts", expected="team root moves at all mapped columns and none unmapped; the QB's attempts move only at mapped columns; the changed value is what draw_link received",
    actual="; ".join(f"{n}: {'PASS' if c else 'FAIL'}" for n, c, d in b2["checks"]), domain_verdict=f"received {b2.get('received_before')} -> {b2.get('received_after')}; team moved {b2.get('team_moved_mapped')}/{b2.get('mapped_columns')} mapped, {b2.get('team_moved_unmapped')} unmapped; QB moved {b2.get('player_moved_mapped')} mapped, {b2.get('player_moved_unmapped')} unmapped",
    check_result="PASS" if b2["checks"] and all(c for n, c, d in b2["checks"]) else "FAIL", evidence=f"{OUT}/nfl_b2.json; {OUT}/nfl_b2/perturb_handoff.json; pinned inputs {pinned} {pinned_sha}"))
# shared check: only these IDs changed — the same function names an unexpected change in both domains (checks/changed_ids.py)
from changed_ids import changed_ids, status_changes
def ids_record(case, domain, expected, changed, injected=None):
    r = changed_ids(expected, changed); named = r["extras"] + r["misses"]
    ok = (not named) if injected is None else (sorted(named) == sorted(injected))
    return record(case=case, executed=True, baseline=f"{len(expected)} IDs expected to change", intervention="none" if injected is None else f"injected fault: {injected}", dependency=domain,
        expected="extras [] misses []" if injected is None else f"the injected fault named by ID: {sorted(injected)}", actual=f"changed {len(r['changed'])}; extras {r['extras']}; misses {r['misses']}",
        domain_verdict=f"{len(r['extras'])} unexpected, {len(r['misses'])} missing", check_result="PASS" if ok else "FAIL", evidence="checks/changed_ids.py")
# NFL: the callable's team root columns (expected = the mapped columns)
exp_cols, chg_cols = list(b2["expected_columns"]), list(b2["team_changed_columns"])
unmapped = next(c for c in range(len(exp_cols) * 30) if c not in set(exp_cols))
records.append(ids_record("NFL only these IDs changed (team root columns)", "engine team draw -> kit columns", exp_cols, chg_cols))
records.append(ids_record("NFL injected fault: an unmapped column also changed", "engine team draw -> kit columns", exp_cols, chg_cols + [unmapped], injected=[unmapped]))
records.append(ids_record("NFL injected fault: a mapped column did not change", "engine team draw -> kit columns", exp_cols, [c for c in chg_cols if c != exp_cols[0]], injected=[exp_cols[0]]))
# Healix: per-label evaluator outcome before and after removing one pinned pair from the pairs export (the WORK_ORDER 2a case)
rc_demo, out_demo = sh(["npm", "run", "-s", "demo", "--", "tests"], HEALIX)
export = os.path.join(HEALIX, "out", "demo_pairs.tsv")
label_ids = [tuple(f"{side}#{v}" for side, v in zip("AB", l.strip().split(","))) for l in open(os.path.join(HEALIX, "tests/positive/own_copy/labels.csv")).read().splitlines()[1:] if l.strip()]
def outcomes(path):
    proposed = {}
    for line in open(path).read().splitlines()[1:]:
        if line: t, a, b, ruling = line.split("\t"); proposed.update({(a, b): ruling} if t == "own_copy" else {})
    return {k: proposed.get(k, "never proposed") for k in label_ids}
def export_without(removed):
    q = f"{OUT}/healix_export_without_{len(removed)}.tsv"
    open(q, "w").write("\n".join(l for l in open(export).read().splitlines() if not any(l.split("\t")[:3] == ["own_copy", a, b] for a, b in removed)) + "\n"); return q
one = [("A#1000", "B#11000")]; second = ("A#1001", "B#11001")
if rc_demo == 0:
    base = outcomes(export)
    records.append(ids_record("Healix only these IDs changed (per-label outcome)", "pairs export -> evaluator outcome per label", one, status_changes(base, outcomes(export_without(one)))))
    records.append(ids_record("Healix injected fault: a second pair also removed", "pairs export -> evaluator outcome per label", one, status_changes(base, outcomes(export_without(one + [second]))), injected=[second]))
else:
    records.append(record(case="Healix only these IDs changed (per-label outcome)", executed=False, baseline="demo on the tracked fixture", intervention="none", dependency="pairs export", expected="demo exit 0", actual=f"demo exit {rc_demo}", domain_verdict="not run", check_result="FAIL", evidence=f"{OUT}/healix_demo.txt")); open(f"{OUT}/healix_demo.txt", "w").write(out_demo)
json.dump(records, open(f"{OUT}/records.json", "w"), indent=1)
print(f"{'case':46s} {'executed':8s} {'domain verdict':52s} check")
for r in records: print(f"{r['case'][:46]:46s} {str(r['executed']):8s} {r['domain_verdict'][:52]:52s} {r['check_result']}")
print(f"records: {OUT}/records.json")
sys.exit(0 if all(r["check_result"] == "PASS" for r in records) else 1)
