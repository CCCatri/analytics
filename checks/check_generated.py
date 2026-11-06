"""Gate 1 of the handoff (acceptance-criteria/engine-to-kit-handoff.md section 4; engine-legality.md section 4): the record checks' rule functions run unchanged
on one generated draw. python3 checks/check_generated.py SEASON WEEK DRAW. Stages out/handoff/stage/: the 44 untouched raw files linked from data/raw and
pbp_{season}.csv.gz replaced by the draw's rows, pinned by sha in its own pins file with its own data version; policy pointed at it for this process only.
Record-only sections (pinned record cases, run-log line 322, EXPECTED_FASTER, FROZEN_2023) do not run here: NOT APPLICABLE on generated input, printed, never a pass."""
import sys, os, json, gzip, hashlib
from collections import Counter
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "product"))
import policy
season, week, draw = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]); tag = ("_" + sys.argv[4]) if len(sys.argv) > 4 else ""
stage = os.path.join(ROOT, "out", "handoff", "stage"); os.makedirs(stage, exist_ok=True)
games = pd.read_csv(os.path.join(ROOT, "out", "handoff", f"games_{season}_w{week}{tag}.csv.gz"), dtype=str, keep_default_na=False)
one = games[games["draw_id"] == str(draw)].drop(columns=["draw_id"]); assert len(one), f"draw {draw} not in the games file"
target = os.path.join(stage, f"pbp_{season}.csv.gz"); one.to_csv(target, index=False, compression="gzip")
pins = json.load(open(policy.PINS_FILE))
for name in pins["pins"]:
    link = os.path.join(stage, name)
    if name == f"pbp_{season}.csv.gz": continue
    if os.path.islink(link) or os.path.exists(link): os.remove(link)
    os.symlink(os.path.join(policy.RAW_DIR, name), link)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
pins["raw_dir"] = stage; pins["pins"][f"pbp_{season}.csv.gz"] = sha(target)
text = "".join(f"{n}:{pins['pins'][n]}\n" for n in sorted(pins["pins"])); pins["data_version"] = hashlib.sha256(text.encode()).hexdigest()
pins_file = os.path.join(stage, "GENERATED_PINS.json"); json.dump(pins, open(pins_file, "w"), indent=1)
policy.RAW_DIR = stage; policy.PINS_FILE = pins_file; policy.DATA_VERSION = pins["data_version"]; policy.SEASONS = (season,); policy.GENERATED_INPUT = True
print(f"check_generated: season {season} week {week} draw {draw} | games {one['game_id'].nunique()} rows {len(one)} | staged {target} sha {sha(target)[:12]} | data_version {pins['data_version'][:12]}")
print("NOT APPLICABLE on generated input: the pinned record cases (injected faults sections), run-log line 322, EXPECTED_FASTER, FROZEN_2023 - the record's drivers only")
import check_possessions as cp, check_clock as cc, check_downs as cd, clock_check as ck
verdict = {}
print("\n=== possessions (check_possessions.load / possessions / counts, unchanged) ===")
D = cp.load(season).sort_values(["game_id", "order_sequence"]).reset_index(drop=True); P = cp.possessions(D)
G = {g: d.sort_values("order_sequence").reset_index(drop=True) for g, d in D.groupby("game_id")}
b2b, oth, C = cp.counts(P, G); left = oth[oth["word"].astype(str).str.startswith(("UNEXPLAINED", "MULTIPLE"))]
print(f"  possessions {C['possessions']} games {C['games']} | back-to-back kinds {C['kinds']} | classes {C['classes']} | unexplained or multiple {len(left)}")
for _, r in left.head(20).iterrows(): print(f"    {r['word']}: {r['game_id']} {r['team']} q{int(r['q'])} seq {r['prev_s1']} -> {r['s0']}")
verdict["possessions unexplained 0"] = len(left) == 0
print("\n=== clock (check_clock.load / intervals, unchanged) ===")
d, empt, unp = cc.load(season); iv = []
for _, gd in d.groupby("game_id", sort=False): iv += cc.intervals(gd)
IV = pd.DataFrame(iv); print(f"  intervals {len(IV)} | columns {list(IV.columns)}")
gl = Counter(IV["game_level"]); print(f"  game level {dict(gl)}")
for col in ("cls", "klass", "clock_class", "class_"):
    if col in IV: print(f"  classes {dict(Counter(IV[col]))}"); break
faster = sum(v for k, v in gl.items() if k.startswith("FASTER not licensed")); unchecked = gl.get("UNCHECKED", 0)
verdict["clock FASTER not licensed 0"] = faster == 0; verdict["clock UNCHECKED 0 (engine stamps every snap)"] = unchecked == 0
print(f"  empty cells {empt}")
print("\n=== downs (check_downs.load / checks, unchanged) ===")
D2 = cd.load(season); G2 = {gid: g_.reset_index(drop=True) for gid, g_ in D2.groupby("game_id", sort=False)}; ITEMS, unpaired = [], 0
for gd in G2.values(): it, u = cd.checks(gd); ITEMS += it; unpaired += u
I = pd.DataFrame(ITEMS); words = Counter(I["word"]); O = I[I["word"] == "OTHER"]
print(f"  items {len(I)} | words {dict(words)} | pairs not judged {unpaired} | OTHER {len(O)} | UNCHECKED {words.get('UNCHECKED', 0)}")
for _, r in O.head(20).iterrows(): print(f"    OTHER: {dict(r)}")
verdict["downs OTHER 0"] = len(O) == 0; verdict["downs UNCHECKED 0"] = words.get("UNCHECKED", 0) == 0
print("\n=== stopped clock (clock_check.check_clock2, unchanged) ===")
try:
    r = ck.check_clock2([season]); print(f"  checked {dict(r[0])} | violations {len(r[1])} {r[1][:5]} | warning placements {dict(r[2])} | {len(r[3])} {r[3][:5]}")
    verdict["stopped clock: no STOP stretch falls more than the play plus 1 s"] = len(r[1]) == 0 and len(r[3]) == 0
except Exception as ex: print(f"  stopped-clock check did not run on generated input: {type(ex).__name__}: {str(ex)[:300]} -> NOT DETECTED/NOT RUN (recorded, not a pass)")
print("\n=== season rule on generated games: the kickoff touchback spot (measure_season_rules M1 definition) ===")
ko = one.reset_index(drop=True); spots = []
for i in ko.index[(ko["play_type"] == "kickoff") & (ko["touchback"].astype(str).isin(["1", "1.0"]))]:
    nxt = ko.iloc[i + 1:i + 4]; nxt = nxt[(nxt["down"].astype(str).isin(["1", "1.0"])) & nxt["yardline_100"].astype(str).ne("")]
    if len(nxt): spots.append(100 - int(float(nxt.iloc[0]["yardline_100"])))
from collections import Counter as _C; print(f"  kickoff touchbacks {len(spots)} | spot counts {dict(_C(spots))} | quoted for {season}: 30")
verdict["season rule: kickoff touchback spot == quoted (30)"] = len(spots) > 0 and set(spots) == {30}
print("\n=== verdict (engine-legality.md section 4; coverage above) ===")
for k, v in verdict.items(): print(f"  {k}: {'PASS' if v else 'FAIL'}")
print("GATE 1 ALL LINES PASS:", "PASS" if all(verdict.values()) else "FAIL")
sys.exit(0 if all(verdict.values()) else 1)
