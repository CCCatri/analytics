"""The portable demonstration: from a simulated game to a player projection, from a clean checkout, with no raw play-by-play.
    python3 checks/demo_w15.py
Pins checks/fixtures/demo_w15 (PINS.json) and the engine fixture; if slate-kit/data is absent (a clean checkout) it is created with links to the fixture injuries
files, otherwise the existing one is used. Then, in a fresh out/demo_w15/<stamp>/: (1) the engine-mode card for 2024 week 15 with its provenance line; (2) the
trace - kit root columns 29, 30, 31 equal engine source draws 29, 0, 1 for both teams of ATL at LV, and the traced LV quarterback's Q1 attempts cell received LV's
root at the boundary; (3) the controlled change - LV source draw 0 raised 36 -> 60 in a copy of the fixture: the team root must move at every column mapped to
draw 0 and nowhere else, the player at mapped columns only, and the value received at column 30 must be 60; (4) one deliberately broken input (manifest SHA that
does not match) refused by name with no card artifact. RESULT.txt and full_log.txt in the output directory; exit 0 only if every line passed."""
import os, sys, json, time, shutil, hashlib, io, contextlib, numpy as np, pandas as pd
T0 = time.time(); ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); KIT = os.path.join(ROOT, "slate-kit"); FIXD = os.path.join(ROOT, "checks", "fixtures", "demo_w15")
FIX = os.path.join(ROOT, "out", "handoff", "root_draws_2024_w15.npz"); OUT = os.path.join(ROOT, "out", "demo_w15", time.strftime("%Y%m%d_%H%M%S")); os.makedirs(OUT)
LOG = open(os.path.join(OUT, "full_log.txt"), "w"); LINES = []; ok = True
sha256 = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def say(line): LINES.append(line); print(line, flush=True); LOG.write(line + "\n"); LOG.flush()
def verdict(name, cond, detail=""):
    global ok; ok &= bool(cond); say(f"  {name}: {'PASS' if cond else 'FAIL'}" + (f" | {detail}" if detail else ""))
def quiet(fn, *a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): r = fn(*a)
    LOG.write(buf.getvalue()); LOG.flush(); return r
say(f"demo_w15 | output {OUT}")
# --- pins
pins = json.load(open(os.path.join(FIXD, "PINS.json"))); moved = {n: h for n, h in pins.items() if sha256(os.path.normpath(os.path.join(FIXD, n))) != h}
if moved: sys.exit(f"fixtures moved since pinning: {sorted(moved)} - refused; nothing run")
say(f"  fixtures pinned: {len(pins)} files match PINS.json (engine fixture {pins['../../../out/handoff/root_draws_2024_w15.npz'][:12]})")
# --- data/ for the participation law
DATA = os.path.join(KIT, "data"); INJ = [f"injuries_{s}.csv" for s in (2019, 2020, 2021, 2023, 2024)]
if not os.path.isdir(DATA):
    os.makedirs(DATA); [os.symlink(os.path.join(FIXD, n), os.path.join(DATA, n)) for n in INJ]; say(f"  slate-kit/data was absent (clean checkout): created with links to the {len(INJ)} fixture injuries files")
else:
    missing = [n for n in INJ if not os.path.exists(os.path.join(DATA, n))]
    if missing: sys.exit(f"slate-kit/data exists but lacks {missing} - refused; link or copy them from {FIXD}")
    say("  slate-kit/data present: using it")
if not os.path.isdir(os.path.join(KIT, "facts")): sys.exit("slate-kit/facts missing - refused (it is tracked; the checkout is incomplete)")
# --- the kit, pointed at a fresh project directory holding only the pinned atlas and ladder
sys.path.insert(0, KIT); os.chdir(KIT); import draws, cards
from link_chain import LINKS
PROJ = os.path.join(OUT, "proj"); os.makedirs(PROJ); [shutil.copy(os.path.join(FIXD, n), PROJ) for n in ("atlas.csv", "ladder.csv")]; draws.PROJ_DIR = cards.PROJ_DIR = PROJ
def set_mode(source, path=None): draws.ROOT_SOURCE = source; draws.ROOT_FILE = path; draws.ENGINE_ROOT = None
artifacts = lambda d: sorted(f for f in os.listdir(d) if f.startswith("card_2024_w15") or f == "frozen_draws_2024_w15.npz")
boundary, pending, held = [], [], {}; o_sub, o_link, o_week = draws.substream, draws.draw_link, draws.week_draws
def sub_l(term, position, season, week, key, label):
    if label == draws.LINK_CHAIN_STATE: pending.append((term, position, key))
    return o_sub(term, position, season, week, key, label)
def link_l(cell, fit, rate, other, concentration, parent_draws, generator, sibling=None):
    out = o_link(cell, fit, rate, other, concentration, parent_draws, generator, sibling); who = pending.pop() if pending else None
    boundary.append(dict(cell=cell, who=who, ok=(who is not None and who[0] == cell[0] and who[1] == cell[1]), parent_cell=LINKS[cell][0], parent=None if parent_draws is None else parent_draws.copy(), out=out.copy())); return out
def week_l(season, week): held["week"] = o_week(season, week); return held["week"]
draws.substream, draws.draw_link, cards.week_draws = sub_l, link_l, week_l
# --- (1) the card
say("\n=== 1. engine-mode card, 2024 week 15 ===")
set_mode("engine", FIX); rc = quiet(cards.card, 2024, 15); week = held["week"]; card = pd.read_csv(os.path.join(PROJ, "card_2024_w15.csv")); report = open(os.path.join(PROJ, "card_2024_w15_report.txt")).read().splitlines()
verdict("card issued (exit 0, artifacts written)", rc == 0 and len(artifacts(PROJ)) >= 4, f"{len(card)} stat rows; {artifacts(PROJ)}")
src = np.load(FIX); K = int(src["draw_id"].shape[0]); fsha = sha256(FIX)
verdict("card carries the engine provenance", (card.root_source == "engine").all() and (card.root_file_sha.astype(str) == fsha).all() and (card.root_source_draws == K).all() and (card.root_columns == 2000).all(), f"{K} source draws -> 2000 columns, file {fsha[:12]}")
atlas_d = pd.read_csv(os.path.join(PROJ, "atlas.csv")); ladder_d = pd.read_csv(os.path.join(PROJ, "ladder.csv")); graded_keys = set(zip(atlas_d.term, atlas_d.position, atlas_d.state))
def grading_gaps(card_frame):
    """Stat lines whose (term, position, state) has a cell in the pinned atlas but which the card left ungraded: a detached judge, partly or wholly."""
    has_cell = pd.Series([k in graded_keys for k in zip(card_frame.term, card_frame.position, card_frame.law_state)], index=card_frame.index)
    gaps = card_frame[has_cell & card_frame.atlas_qualification.eq("NO ATLAS CELL - not graded")]
    return int(has_cell.sum()), sorted(set(zip(gaps.term, gaps.position))), sorted(card_frame[~has_cell].term.unique())
eligible, gaps, no_cell_terms = grading_gaps(card)
verdict("every line with an atlas cell is graded (DK lines have no cell, by design)", eligible > 0 and not gaps, f"{eligible} of {len(card)} lines have a cell; ungraded among them: {gaps or 'none'}; terms without a cell: {no_cell_terms}")
say("  report: " + next((l.strip() for l in report if l.strip().startswith("root: engine")), "(no root line)")[:150])
# --- (2) the trace
say("\n=== 2. the trace: engine draws into the kit, into one player ===")
teams, games = src["team"].astype(str), src["game_id"].astype(str); HOME = "LV"; rh = int(np.where(teams == HOME)[0][0]); game = games[rh]; ra = int([i for i in np.where(games == game)[0] if i != rh][0]); AWAY = teams[ra]
for term, arr in (("F2 team attempts", src["attempts"]), ("F2 team carries", src["carries"])):
    for i, team in ((rh, HOME), (ra, AWAY)):
        verdict(f"{game} {team} {term}: kit columns 29,30,31 = source draws 29,0,1", np.array_equal(week["draws"][(team, term)][[29, 30, 31]], arr[i][[29, 0, 1]]), f"kit {week['draws'][(team, term)][[29, 30, 31]].tolist()} source {arr[i][[29, 0, 1]].tolist()}")
qbs = card[(card.team == HOME) & (card.position == "QB") & (card.term == "Q1 attempts")]; pid = qbs.player_id.iloc[0] if len(qbs) else None; name = qbs.name.iloc[0] if pid else "?"
verdict(f"a {HOME} quarterback with a Q1 attempts row", pid is not None, f"{name} ({pid})")
rec = [b for b in boundary if pid and b["who"] == ("Q1 attempts", "QB", pid) and b["cell"] == ("Q1 attempts", "QB") and b["ok"]]
bound = len(rec) == 1 and rec[0]["parent_cell"] == ("F2 team attempts", "TEAM") and np.array_equal(rec[0]["parent"], week["draws"][(HOME, "F2 team attempts")])
src0, src29 = float(src["attempts"][rh][0]), float(src["attempts"][rh][29])
verdict(f"{name}'s Q1 attempts received {HOME}'s root at the boundary: column 30 = source draw 0 ({src0:.0f}), column 29 = source draw 29 ({src29:.0f})", bound and rec[0]["parent"][30] == src0 and rec[0]["parent"][29] == src29, f"received [30] {rec[0]['parent'][30] if rec else None}, [29] {rec[0]['parent'][29] if rec else None}; his drawn attempts at column 30: {rec[0]['out'][30] if rec else None}")
verdict("his card row's mean equals the mean of the draws he consumed", pid is not None and abs(float(qbs.draw_mean.iloc[0]) - float(week["draws"][(pid, "Q1 attempts")].mean())) < 1e-9)
# --- (3) the controlled change
say(f"\n=== 3. the controlled change: {HOME} source draw 0, {src0:.0f} -> {src0 + 24:.0f}, in a copy of the fixture ===")
mapped = (np.arange(2000) % K) == 0; say(f"  expected to move, named before the run: the {int(mapped.sum())} kit columns j with j mod {K} = 0; nothing else")
before, team_before = week["draws"][(pid, "Q1 attempts")].copy(), week["draws"][(HOME, "F2 team attempts")].copy()
data = {k: src[k].copy() for k in src.files}; data["attempts"][rh, 0] += 24; bump = os.path.join(OUT, "bumped.npz"); np.savez_compressed(bump, **data)
man = json.load(open(FIX[:-4] + ".manifest.json")); man["root_draws_sha"] = sha256(bump)[:12]; json.dump(man, open(bump[:-4] + ".manifest.json", "w"), indent=1)
set_mode("engine", bump); boundary.clear(); pending.clear(); week2 = quiet(o_week, 2024, 15); after, team_after = week2["draws"][(pid, "Q1 attempts")], week2["draws"][(HOME, "F2 team attempts")]
mt, mp = team_after != team_before, after != before
verdict(f"team root moved at all {int(mapped.sum())} mapped columns and nowhere else", mt[mapped].all() and not mt[~mapped].any(), f"mapped moved {int(mt[mapped].sum())}; unmapped moved {int(mt[~mapped].sum())}")
verdict(f"{name}'s attempts moved at mapped columns only", mp[mapped].any() and not mp[~mapped].any(), f"mapped moved {int(mp[mapped].sum())} of {int(mapped.sum())}; unmapped moved {int(mp[~mapped].sum())}")
rec2 = [b for b in boundary if b["who"] == ("Q1 attempts", "QB", pid) and b["cell"] == ("Q1 attempts", "QB") and b["ok"]]
verdict(f"the changed value ({src0 + 24:.0f}) is what his calculation received at column 30", len(rec2) == 1 and rec2[0]["parent"][30] == src0 + 24, f"received {rec2[0]['parent'][30] if rec2 else None}; his drawn attempts at column 30: before {rec[0]['out'][30] if rec else None}, after {rec2[0]['out'][30] if rec2 else None}")
# --- (4) one broken input
say("\n=== 4. a deliberately broken input: manifest SHA that does not match the file ===")
bad = os.path.join(OUT, "bad_sha.npz"); shutil.copy(FIX, bad); m = dict(json.load(open(FIX[:-4] + ".manifest.json"))); m["root_draws_sha"] = "000000000000"; json.dump(m, open(bad[:-4] + ".manifest.json", "w"))
P2 = os.path.join(OUT, "proj_refusal"); os.makedirs(P2); [shutil.copy(os.path.join(FIXD, n), P2) for n in ("atlas.csv", "ladder.csv")]; draws.PROJ_DIR = cards.PROJ_DIR = P2; set_mode("engine", bad); msg = "NO REFUSAL"
try: quiet(cards.card, 2024, 15)
except SystemExit as stop: msg = str(stop.code)
verdict("refused by name, no card artifact", "SHA mismatch" in msg and not artifacts(P2), msg[:140])
# --- result
say("\n=== 5. a deliberately detached judge: one cell re-spelled in the atlas and the ladder, card re-issued ===")
import shutil
apath, lpath = os.path.join(PROJ, "atlas.csv"), os.path.join(PROJ, "ladder.csv"); keep = {f: open(os.path.join(PROJ, f), "rb").read() for f in os.listdir(PROJ) if f.startswith("card_2024_w15")}
a_good, l_good = open(apath).read(), open(lpath).read(); on_card = set(zip(card.term, card.position)); victim = next((t, q) for t, q in zip(atlas_d.term, atlas_d.position) if (t, q) in on_card)   # a cell the player card actually carries
a_bad, l_bad = atlas_d.copy(), ladder_d.copy(); a_bad.loc[(a_bad.term == victim[0]) & (a_bad.position == victim[1]), "state"] = "detached"; l_bad.loc[(l_bad.term == victim[0]) & (l_bad.position == victim[1]), "state"] = "detached"
a_bad.to_csv(apath, index=False); l_bad.to_csv(lpath, index=False); draws.PROJ_DIR = PROJ; cards.PROJ_DIR = PROJ; set_mode("engine", FIX); rc5 = quiet(cards.card, 2024, 15)
card5 = pd.read_csv(os.path.join(PROJ, "card_2024_w15.csv")); _, gaps5, _ = grading_gaps(card5)
open(apath, "w").write(a_good); open(lpath, "w").write(l_good)
for f, b in keep.items(): open(os.path.join(PROJ, f), "wb").write(b)
verdict("the partial detachment is caught and named (the card issued; the demo refuses it)", rc5 == 0 and victim in gaps5, f"re-spelled {victim}; ungraded cells found: {gaps5}; card exit {rc5}; real card files restored")
say(f"\nDEMO W15 (from a simulated game to a player projection): {'PASS' if ok else 'FAIL'} | {time.time() - T0:.0f} s | {OUT}/RESULT.txt")
open(os.path.join(OUT, "RESULT.txt"), "w").write("\n".join(LINES) + "\n"); LOG.close(); sys.exit(0 if ok else 1)
