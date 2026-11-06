"""Step 4, the overall verdict for one run id: reads baseline/, components/ and replay/ record.json; requires the same run, the same candidate code in all three, the
baseline to be the pre-adapter code, the same run identity (git revision, kit code, resolved shared inputs) in baseline and replay, the components' pinned inputs and
A1 card to be the baseline's outputs, the replay copy to come from the baseline's live snapshot, and all three verdicts PASS. Writes HANDOFF_RUN_DIR/VERDICT.txt; exit 1 unless PASS."""
import os, sys, json
RUN = os.environ.get("HANDOFF_RUN_DIR")
if not RUN: sys.exit("HANDOFF_RUN_DIR unset - refused; use checks/run_handoff.sh")
recs = {part: (json.load(open(os.path.join(RUN, part, "record.json"))) if os.path.exists(os.path.join(RUN, part, "record.json")) else None) for part in ("baseline", "components", "replay")}
lines = [f"run {RUN}"]; ok = True
def line(name, cond, detail=""):
    global ok; ok &= bool(cond); lines.append(f"  {name}: {'PASS' if cond else 'FAIL'}" + (f" | {detail}" if detail else ""))
b, c, r = recs["baseline"], recs["components"], recs["replay"]; short = lambda d: {k: v[:12] for k, v in d.items()}
line("all three records present", all(recs.values()), ", ".join(f"{k} {'present' if v else 'MISSING'}" for k, v in recs.items()))
if all(recs.values()):
    line("same run id", b["run"] == c["run"] == r["run"] == RUN)
    line("same candidate code in all three", b["candidate"] == c["candidate"] == r["candidate"], f"{short(b['candidate'])}")
    line("baseline is the pre-adapter code", all(b["pre_code"][f] != b["candidate"][f] for f in b["pre_code"]), f"pre {short(b['pre_code'])}")
    line("same run identity in baseline and replay", b["identity"] == r["identity"], f"git {b['identity']['git_head'][:12]}, {len(b['identity']['git_dirty_paths'])} dirty paths, inputs {list(b['identity']['inputs'])}")
    line("components' pinned inputs and A1 card are the baseline's outputs", c["pinned_inputs"] == {f: b["outputs"][f] for f in c["pinned_inputs"]} and c["baseline_card_sha"] == b["outputs"]["card_2026_w4.csv"], f"{short(c['pinned_inputs'])}")
    line("replay copy taken from the baseline's live snapshot", r["live_proj_snapshot"] == b["live_proj_snapshot"])
    line("baseline step", b["verdict"] == "PASS", b["verdict"]); line("component checks A1, B, B2, C", c["verdict"] == "PASS", c["verdict"]); line("A2 paired replay", r["verdict"] == "PASS", r["verdict"])
lines.append(f"\nHANDOFF ADAPTER {os.path.basename(RUN)}: {'PASS' if ok else 'FAIL'}")
text = "\n".join(lines) + "\n"; open(os.path.join(RUN, "VERDICT.txt"), "w").write(text); print(text, end=""); sys.exit(0 if ok else 1)
