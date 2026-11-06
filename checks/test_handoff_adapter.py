"""Step 2, the component checks, under HANDOFF_RUN_DIR/components/; the pinned inputs (atlas.csv, ladder.csv) and the A1 baseline card come from the baseline step's
kit_pre/proj (pre-adapter code on the same inputs). Reports only its own result; the overall verdict is issued by checks/test_handoff_final.py.
A1: kit mode reproduces the baseline card by key, column set and value (NaN as a value, no tolerance). B: engine mode on the 2024 w15 fixture - card with the
computed file hash and 30 -> 2,000; root columns 29, 30, 31 = source 29, 0, 1 for both teams of one game and both root terms. B2: the value the player calculation
received at the boundary (draw_link's parent array for the traced player's cell, bound to his team's root), then a controlled change of that source draw: the team root
must move at all mapped columns and nowhere else; the player at >= 1 mapped column and nowhere else. C: four isolated plants refusing by name with no card artifact;
a wrong week after a valid load in the same process; a source typo."""
import os, sys, json, shutil, hashlib, io, contextlib, numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); KIT = os.path.join(ROOT, "slate-kit"); sys.path.insert(0, KIT); os.chdir(KIT)
FIX = os.path.join(ROOT, "out", "handoff", "root_draws_2024_w15.npz")
RUN = os.environ.get("HANDOFF_RUN_DIR")
if not RUN: sys.exit("HANDOFF_RUN_DIR unset - refused; use checks/run_handoff.sh")
BREC = os.path.join(RUN, "baseline", "record.json")
if not os.path.exists(BREC): sys.exit("baseline/record.json missing - refused; run the baseline step first")
brec = json.load(open(BREC)); BASE_PROJ = os.path.join(RUN, "baseline", "kit_pre", "proj")
if brec["verdict"] != "PASS": sys.exit("baseline verdict is not PASS - refused")
OUT = os.path.join(RUN, "components")
if os.path.exists(OUT): sys.exit(f"{OUT} exists - refused; one run id holds one component record")
os.makedirs(OUT); LOG = open(os.path.join(OUT, "full_log.txt"), "w")
sha256 = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
PINNED = {f: sha256(os.path.join(BASE_PROJ, f)) for f in ("atlas.csv", "ladder.csv")}; CANDIDATE = {f: sha256(os.path.join(KIT, f)) for f in ("draws.py", "cards.py")}
BASE_CARD = os.path.join(BASE_PROJ, "card_2026_w4.csv")
import draws, cards
from chain import LINKS
LINES = []; ok = True
def say(line): LINES.append(line); print(line, flush=True); LOG.write(line + "\n"); LOG.flush()
def verdict(name, cond, detail=""):
    global ok; ok &= bool(cond); say(f"  {name}: {'PASS' if cond else 'FAIL'}" + (f" | {detail}" if detail else ""))
def quiet(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): result = fn(*args)
    LOG.write(buf.getvalue()); LOG.flush(); return result
def outdir(name):
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    for f in ("atlas.csv", "ladder.csv"): shutil.copy(os.path.join(BASE_PROJ, f), d)
    draws.PROJ_DIR = d; cards.PROJ_DIR = d; return d
def artifacts(d, season, week): return sorted(f for f in os.listdir(d) if f.startswith(f"card_{season}_w{week}") or f == f"frozen_draws_{season}_w{week}.npz")
def set_mode(source, path=None): draws.ROOT_SOURCE = source; draws.ROOT_FILE = path; draws.ENGINE_ROOT = None
say(f"run {RUN}\ncandidate draws.py {CANDIDATE['draws.py'][:12]} cards.py {CANDIDATE['cards.py'][:12]} | baseline (pre-adapter code) draws.py {brec['pre_code']['draws.py'][:12]} cards.py {brec['pre_code']['cards.py'][:12]}")
say(f"pinned inputs from kit_pre/proj: atlas.csv {PINNED['atlas.csv'][:12]} ladder.csv {PINNED['ladder.csv'][:12]} | baseline card {sha256(BASE_CARD)[:12]} | fixture {sha256(FIX)[:12]}")
verdict("candidate code is the code the baseline step recorded", CANDIDATE == brec["candidate"])
verdict("pinned inputs are the baseline step's outputs", PINNED == {f: brec["outputs"][f] for f in PINNED} and sha256(BASE_CARD) == brec["outputs"]["card_2026_w4.csv"])
boundary = []; pending = []; orig_substream, orig_draw_link, orig_week_draws = draws.substream, draws.draw_link, draws.week_draws; held = {}
def substream_logging(term, position, season, week, key, label):
    if label == draws.CHAIN_STATE: pending.append((term, position, key))
    return orig_substream(term, position, season, week, key, label)
def draw_link_logging(cell, fit, rate, other, concentration, parent_draws, generator, sibling=None):
    out = orig_draw_link(cell, fit, rate, other, concentration, parent_draws, generator, sibling); who = pending.pop() if pending else None
    boundary.append(dict(cell=cell, who=who, matches=(who is not None and who[0] == cell[0] and who[1] == cell[1]), parent_cell=LINKS[cell][0],
                         parent=None if parent_draws is None else parent_draws.copy(), out=out.copy()))
    return out
def capturing_week_draws(season, week): held["week"] = orig_week_draws(season, week); return held["week"]
draws.substream, draws.draw_link = substream_logging, draw_link_logging; cards.week_draws = capturing_week_draws
plants = os.path.join(OUT, "plants"); os.makedirs(plants); src = np.load(FIX); man = json.load(open(FIX[:-4] + ".manifest.json"))
def fixture(name, manifest_edit=None, arrays_edit=None, absent=False):
    p = os.path.join(plants, f"{name}.npz"); m = dict(man)
    if arrays_edit is not None: data = arrays_edit({k: src[k].copy() for k in src.files}); np.savez_compressed(p, **data); m["root_draws_sha"] = sha256(p)[:12]
    elif not absent: shutil.copy(FIX, p)
    if manifest_edit is not None: m = manifest_edit(m)
    json.dump(m, open(p[:-4] + ".manifest.json", "w"), indent=1); return p
# ---------------- A1 ----------------
say("\n=== A1: kit mode against the baseline card (pre-adapter code, same inputs), isolated output ===")
set_mode("kit"); d = outdir("A_kit"); rc = quiet(cards.card, 2026, 4)
base = pd.read_csv(BASE_CARD); new = pd.read_csv(os.path.join(d, "card_2026_w4.csv")); key = ["season", "week", "player_id", "term"]
m = base.merge(new, on=key, how="outer", suffixes=("_b", "_n"), indicator=True)
def differs(c):
    b, n = m[c + "_b"], m[c + "_n"]
    if pd.api.types.is_numeric_dtype(b) and pd.api.types.is_numeric_dtype(n): return int((~((b.astype(float) == n.astype(float)) | (b.isna() & n.isna()))).sum())
    return int((b.fillna("").astype(str) != n.fillna("").astype(str)).sum())
changed = {c: differs(c) for c in base.columns if c not in key and c + "_b" in m}; changed = {c: v for c, v in changed.items() if v}
verdict("A1 exit 0", rc == 0); verdict("A1 column set identical", list(base.columns) == list(new.columns), f"extra {sorted(set(new.columns) - set(base.columns))} missing {sorted(set(base.columns) - set(new.columns))}")
verdict("A1 key set identical", int((m._merge != "both").sum()) == 0, f"baseline only {int((m._merge == 'left_only').sum())}, new only {int((m._merge == 'right_only').sum())}")
verdict("A1 values identical by key (equality by value, NaN as a value, no tolerance)", not changed, f"changed columns {changed}")
# ---------------- B ----------------
say("\n=== B: engine mode on the valid 2024 w15 fixture, isolated output ===")
set_mode("engine", FIX); d = outdir("B_engine"); boundary.clear(); pending.clear(); rc = quiet(cards.card, 2024, 15); week = held["week"]; card = pd.read_csv(os.path.join(d, "card_2024_w15.csv"))
verdict("B exit 0 and card artifacts written", rc == 0 and len(artifacts(d, 2024, 15)) >= 4, f"{artifacts(d, 2024, 15)}")
teams = src["team"].astype(str); games = src["game_id"].astype(str); K = int(src["draw_id"].shape[0]); computed = sha256(FIX)
verdict("B card carries the computed file hash and 30 -> 2,000", (card.root_file_sha.astype(str) == computed).all() and (card.root_source_draws == K).all() and (card.root_columns == 2000).all() and (card.root_source == "engine").all(), f"{K} -> {int(card.root_columns.iloc[0])}, sha {computed[:12]}")
verdict("B grading_basis labels atlas/ladder as kit baseline evidence", "grading_basis" in card and card.grading_basis.str.startswith("kit baseline evidence").all())
manifest = json.load(open(os.path.join(d, "card_2024_w15_root.manifest.json"))); verdict("B root manifest beside the card", manifest["root_file_sha"] == computed and manifest["root_source_draws"] == K)
HOME = "LV"; row_home = int(np.where(teams == HOME)[0][0]); game = games[row_home]; row_away = int([i for i in np.where(games == game)[0] if i != row_home][0]); AWAY = teams[row_away]
say(f"  game {game}: {HOME} is source row {row_home}, {AWAY} is source row {row_away}; one engine game per draw_id")
for term, arr in (("F2 team attempts", src["attempts"]), ("F2 team carries", src["carries"])):
    for i, team in ((row_home, HOME), (row_away, AWAY)):
        kit_cols = week["draws"][(team, term)][[29, 30, 31]]; src_cols = arr[i][[29, 0, 1]]; distinct = len(set(arr[i][[0, 1, 29]].tolist())) == 3
        verdict(f"B {team} {term}: kit columns 29,30,31 = source 29,0,1", np.array_equal(kit_cols, src_cols), f"kit {kit_cols.tolist()} source {src_cols.tolist()} | source 0,1,29 distinct {distinct}")
qbs = card[(card.team == HOME) & (card.position == "QB") & (card.term == "Q1 attempts")]; pid = qbs.player_id.iloc[0] if len(qbs) else None
verdict(f"B a {HOME} QB with Q1 attempts on the card", pid is not None, f"{qbs.name.iloc[0] if pid else ''} ({pid})")
if pid:
    mine = week["draws"][(pid, "Q1 attempts")]; verdict("B his card row draw_mean equals the mean of the consumed draws", abs(float(qbs.draw_mean.iloc[0]) - float(mine.mean())) < 1e-9, f"card {float(qbs.draw_mean.iloc[0]):.4f} draws {float(mine.mean()):.4f}")
    root_row = week["laws"][(week["laws"].key == HOME) & (week["laws"].term == "F2 team attempts")]; verdict("B root law row names the engine file", root_row.provenance.str.contains("engine root").all() and root_row.family.str.startswith("team volume: the engine").all())
# ---------------- B2 ----------------
say("\n=== B2: the value received at the boundary, and a controlled change of one source draw ===")
if pid:
    rec = [b for b in boundary if b["who"] == ("Q1 attempts", "QB", pid) and b["cell"] == ("Q1 attempts", "QB") and b["matches"]]
    bound = len(rec) == 1 and rec[0]["parent_cell"] == ("F2 team attempts", "TEAM") and np.array_equal(rec[0]["parent"], week["draws"][(HOME, "F2 team attempts")])
    verdict(f"B2 draw_link for {pid} Q1 attempts: one call, cell matched, parent is {HOME}'s F2 team attempts root", bound)
    src0, src29 = float(src["attempts"][row_home][0]), float(src["attempts"][row_home][29])
    verdict(f"B2 received column 30 = {HOME} source draw 0 ({src0:.0f}) and column 29 = source draw 29 ({src29:.0f})", bound and rec[0]["parent"][30] == src0 and rec[0]["parent"][29] == src29, f"received [30] {rec[0]['parent'][30] if rec else None}, [29] {rec[0]['parent'][29] if rec else None}; returned column 30 {rec[0]['out'][30] if rec else None}")
    before, team_before = mine.copy(), week["draws"][(HOME, "F2 team attempts")].copy()
    def bump(data): data["attempts"][row_home, 0] = data["attempts"][row_home, 0] + 24; return data
    bumped = fixture("bumped", arrays_edit=bump); set_mode("engine", bumped); outdir("B2_bumped"); boundary.clear(); pending.clear()
    week2 = quiet(orig_week_draws, 2024, 15); after, team_after = week2["draws"][(pid, "Q1 attempts")], week2["draws"][(HOME, "F2 team attempts")]
    mapped = (np.arange(2000) % K) == 0; moved_team, moved = team_after != team_before, after != before
    verdict(f"B2 team root moved at all {int(mapped.sum())} columns mapped to source 0 and nowhere else", moved_team[mapped].all() and not moved_team[~mapped].any(), f"mapped moved {int(moved_team[mapped].sum())} of {int(mapped.sum())}; unmapped moved {int(moved_team[~mapped].sum())}")
    verdict(f"B2 {pid} Q1 attempts moved at >= 1 mapped column and at no unmapped column", moved[mapped].any() and not moved[~mapped].any(), f"mapped moved {int(moved[mapped].sum())} of {int(mapped.sum())} (a binomial can land on the same value); unmapped moved {int(moved[~mapped].sum())}")
    rec2 = [b for b in boundary if b["who"] == ("Q1 attempts", "QB", pid) and b["cell"] == ("Q1 attempts", "QB") and b["matches"]]
    verdict(f"B2 the changed source ({src0:.0f} -> {src0 + 24:.0f}) is what draw_link received at column 30", len(rec2) == 1 and rec2[0]["parent"][30] == src0 + 24, f"received {rec2[0]['parent'][30] if rec2 else None}; returned column 30 before {rec[0]['out'][30] if rec else None} after {rec2[0]['out'][30] if rec2 else None}")
# ---------------- C ----------------
say("\n=== C: four isolated plants, each refusing for its own reason, no card artifact ===")
def drop_team(data):
    keep = data["team"].astype(str) != HOME; return {k: (v[keep] if k in ("game_id", "team", "opponent", "season", "week", "attempts", "carries") else v) for k, v in data.items()}
cases = [("missing file", fixture("missing", absent=True), "draw file missing"), ("SHA mismatch", fixture("sha", manifest_edit=lambda m: {**m, "root_draws_sha": "000000000000"}), "SHA mismatch"),
         (f"missing team {HOME}", fixture("team", arrays_edit=drop_team), f"team {HOME} has a game"), ("draw_count 31 vs 30", fixture("count", manifest_edit=lambda m: {**m, "draw_count": 31}), "draw_count mismatch")]
for name, path, expect in cases:
    set_mode("engine", path); d = outdir("C_" + name.replace(" ", "_")); msg = None
    try: rc = quiet(cards.card, 2024, 15); msg = f"NO REFUSAL (exit {rc})"
    except SystemExit as stop: msg = str(stop.code)
    verdict(f"C {name}: refused by name, no artifact", (expect in msg) and not artifacts(d, 2024, 15), f"{msg[:150]} | artifacts {artifacts(d, 2024, 15)}")
say("\n=== C: same process - a wrong week after a valid load; a source typo ===")
set_mode("engine", FIX); draws.engine_root(2024, 15); msg = None
try: draws.engine_root(2024, 16); msg = "NO REFUSAL"
except SystemExit as stop: msg = str(stop.code)
verdict("C cached W15 then W16 requested: issue mismatch refused", "the issue is 2024 w16" in msg, msg[:150])
import subprocess; p = subprocess.run([sys.executable, "-c", "import draws"], env=dict(os.environ, SLATE_ROOT_SOURCE="engin"), capture_output=True, text=True, cwd=KIT)
verdict("C SLATE_ROOT_SOURCE=engin refused by name", p.returncode != 0 and "is not a root source" in (p.stdout + p.stderr), (p.stdout + p.stderr).strip()[:150])
say(f"\nCOMPONENT CHECKS (A1, B, B2, C): {'PASS' if ok else 'FAIL'} | the overall verdict is issued by checks/test_handoff_final.py")
json.dump(dict(run=RUN, candidate=CANDIDATE, pinned_inputs=PINNED, baseline_card_sha=sha256(BASE_CARD), fixture_sha=sha256(FIX), verdict="PASS" if ok else "FAIL", lines=LINES), open(os.path.join(OUT, "record.json"), "w"), indent=1)
open(os.path.join(OUT, "RESULT.txt"), "w").write("\n".join(LINES) + "\n"); LOG.close(); print(f"written {OUT}/RESULT.txt, full_log.txt, record.json"); sys.exit(0 if ok else 1)
