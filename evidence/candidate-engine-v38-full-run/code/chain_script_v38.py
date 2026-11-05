import hashlib, os, io, re, sys, time, json, tempfile, shutil, pickle, atexit, inspect, signal, threading
from collections import Counter, defaultdict
import numpy as np, pandas as pd
import sklearn, platform   # imported here: an import inside the exit handler fails while the interpreter shuts down
sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:12] if os.path.exists(p) else "MISSING"
shs = lambda t: hashlib.sha256(t.encode()).hexdigest()[:12]
BUDGET = 600; RESERVE = 30   # the budget end to end; the last RESERVE seconds are kept for cleanup and writing the evidence
T0 = time.time(); DEADLINE = T0 + BUDGET - RESERVE; SECT = []; _ts = [time.time()]; PRINTED = set()
FIXTURE = "--fixture" in sys.argv
COLD = "--cold" in sys.argv   # n: a full run with no working table reused (its own empty work folder)
CHAIN_FILE = os.path.abspath(sys.argv[0]); CSHA = sh(CHAIN_FILE)
RUN_ID = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(T0)) + f"_{os.getpid()}_" + ("quick" if FIXTURE else ("full_cold" if COLD else "full"))
LOG = sys.argv[sys.argv.index("--log") + 1] if "--log" in sys.argv else f"v38_{RUN_ID}.txt"
EVD = os.path.join("evidence", f"e2b_v38_{CSHA}", RUN_ID)
STATE = dict(status="RUNNING", reason="", section="start", results={}, gates={}, land=None)
POOL = None


def _kill_pool():
    global POOL
    if POOL is not None:
        try: POOL.kill()
        except Exception: pass
        POOL = None
TERM = sys.__stdout__


class Overtime(BaseException):
    """The budget passed: the run stops where it is (its computed failures stay printed as evidence)."""


def progress(msg):
    """A line on the terminal while the run goes (the full printout goes to the log file)."""
    line = f"[{time.time() - T0:6.0f} s] {msg}"
    try: TERM.write(line + "\n"); TERM.flush()
    except Exception: pass
    print(line)


def stop(m):
    STATE.update(status="STOPPED", reason=m); print(f"\nSTOPPED: {m}"); progress(f"STOPPED: {m}"); _kill_pool(); sys.exit(1)


def over(where):
    STATE.update(status="INCOMPLETE", reason=f"over {BUDGET - RESERVE} s of computing at '{where}' ({time.time() - T0:.0f} s)")
    print(f"\nINCOMPLETE: the computing budget ({BUDGET - RESERVE} s; {RESERVE} s kept for the evidence) passed at '{where}'; what it computed above stays printed as evidence")
    progress(f"INCOMPLETE at '{where}'"); _kill_pool()
    raise Overtime()


def _alarm(sig_, frm_):
    over(STATE["section"] + " (the next section, while it ran)")


signal.signal(signal.SIGALRM, _alarm); signal.setitimer(signal.ITIMER_REAL, max(DEADLINE - time.time(), 1.0))   # the budget enforced while any section runs


def left():
    return DEADLINE - time.time()


def section(name):
    now = time.time(); SECT.append((name, now - _ts[0])); _ts[0] = now; PRINTED.add(name); STATE["section"] = name
    progress(f"{name} ({SECT[-1][1]:.1f} s)")
    if now > DEADLINE: over(name)


class _Tee:
    """Everything printed goes to the log file as it is printed and is kept for the evidence folder; the terminal gets the progress lines."""
    def __init__(self, path): self.f, self.buf = open(path, "w", buffering=1), io.StringIO()
    def write(self, s): self.f.write(s); self.buf.write(s)
    def flush(self): self.f.flush()


TEE = _Tee(LOG); sys.stdout = TEE; sys.stderr = TEE
TERM.write(f"E2b v19 ai {'quick' if FIXTURE else 'full'} run {RUN_ID}: the full printout goes to {LOG}; progress below\n"); TERM.flush()
_hook = sys.excepthook
def _excepthook(t, v, tb):
    if t is Overtime: return
    STATE.update(status="STOPPED", reason=f"raised {t.__name__}: {v}"); _hook(t, v, tb); progress(f"STOPPED: raised {t.__name__}: {v} (the traceback is in {LOG})")
sys.excepthook = _excepthook


def _evidence():
    """l: every run's own folder (its run id), written whether the run ends complete, stopped or over budget: the printout, a manifest, the code run.
    The run's status is decided after the evidence is written: over the budget end to end is INCOMPLETE; evidence that could not be written is FAILED."""
    signal.setitimer(signal.ITIMER_REAL, 0)
    _kill_pool()
    if STATE["status"] == "RUNNING": STATE.update(status="STOPPED", reason="the run ended before its last section")
    ok_ = False
    def man_():
        return dict(run_id=RUN_ID, chain=[CHAIN_FILE, CSHA], mode="quick" if FIXTURE else "full", status=STATE["status"], reason=STATE["reason"], last_section=STATE["section"],
                    inputs={p: sh(p) for p in list(globals().get("PIN", {})) + ["rules.py"]}, results=STATE["results"], gates=STATE["gates"], landable=STATE["land"],
                    working_tables=globals().get("CACHE_LOG", []), sections=SECT, log=LOG, seconds=round(time.time() - T0, 1),
                    versions={"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__})
    try:
        os.makedirs(os.path.join(EVD, "code"), exist_ok=True)
        for f_ in [CHAIN_FILE, "e1.py", "rules.py", "record.py", "contract.py", "r1.py", "r2.py", "r4.py", "r7.py", "l0.py", "transition.py", "clock_check.py", globals().get("LIB_FILE", "")]:
            if f_ and os.path.exists(f_): shutil.copy(f_, os.path.join(EVD, "code", os.path.basename(f_)))
        open(os.path.join(EVD, "printout.txt"), "w").write(TEE.buf.getvalue())
        json.dump(man_(), open(os.path.join(EVD, "manifest.json"), "w"), indent=1, default=str)
        ok_ = True
    except Exception as ex_:
        print(f"\nl: the evidence could not be written ({type(ex_).__name__}: {ex_})")
    tot = time.time() - T0
    STATE["gates"][f"{BUDGET} s end to end, the evidence written"] = bool(ok_ and tot <= BUDGET)
    if not ok_: STATE.update(status="FAILED", reason=(STATE["reason"] + "; " if STATE["reason"] else "") + "the evidence could not be written")
    elif STATE["status"] == "COMPLETE" and tot > BUDGET: STATE.update(status="INCOMPLETE", reason=f"{tot:.0f} s end to end with the evidence, over {BUDGET} s")
    last = (f"\nCHAIN E2b v19 ai {STATE['status']} | {tot:.0f} s end to end with the evidence (budget {BUDGET} s) | evidence {EVD if ok_ else 'NOT WRITTEN'}"
            + (f" | {STATE['reason']}" if STATE["reason"] else "")
            + " | " + STATE["results"].get("line", ""))
    print(last)
    if ok_:
        try:
            open(os.path.join(EVD, "printout.txt"), "a").write(last + "\n"); json.dump(man_(), open(os.path.join(EVD, "manifest.json"), "w"), indent=1, default=str)
        except Exception as ex_:
            STATE.update(status="FAILED"); print(f"l: the final manifest could not be written ({type(ex_).__name__}: {ex_}): FAILED")
    print("READ THIS: paste the whole printout to the falsifier.")
    try: TERM.write(last.strip() + f"\nthe full printout: {LOG}\n"); TERM.flush(); TEE.flush()
    except Exception: pass
    os._exit({"COMPLETE": 0, "INCOMPLETE": 3}.get(STATE["status"], 1))


atexit.register(_evidence)

print("CHAIN E2b v19 ai (E2_TARGETS.md '## E2b v19 ai' and '### v19 ai addition'; after e2b_v37_37db486d756e: LANDED e1.py 4f28bf6aa3cc, out/sim_games.csv d3d2dd1303de,")
print("out/e1_checks.csv f54577bfd3be, MANIFEST c539a85289bc): ai0 reads the fourth-down distance key; ai1, built unless ai0 closes ai, keys the choice by the whole-yard")
print("distance first. On those files it LANDS e1.py, out/engine/ (the same model files), out/sim_games.csv and out/e1_checks.csv in the same run when the landing checks")
print("pass; transition.py carried unchanged. A quick run never lands.")
print("BUILT AS (declared before any number; v38, from E2_TARGETS.md 165d9321da35, '## E2b v19 ai' with '### v19 ai addition' printed from disk below):")
print("  ai0 (a) as amended: z4's reader is kept (the corrected ah read 65984a512635 reproduced v36's 20 of 48 on v36's games); its label is corrected. ah1's reader (10")
print("     zones x 4 distances x 3 choices, the pool's population: a fourth-down snap with no foul whose kind is a called play, a punt or a field goal try; 2SE by game)")
print("     is printed beside it every run, on the candidate's games, v37's (out/sim_games.csv d3d2dd1303de, read before any landing) and v36's (298c5bc6a883, the")
print("     replaced file in v37's evidence); its plant: v36's games read fewer cells within than v37's.")
print("  ai0 (b) read from the landed e1.py by line: dist_bin and every distance key of the fourth-down pool's levels. If 4th and 1 shares a bin with 2-3 at the first")
print("     levels, ai1 is built; if 1 stands alone there, ai closes as a read.")
print("  ai1 the choice keyed by the whole-yard distance first: (distw, yard line, time, score) -> (distw, yard line, time) -> (distw, yard line) -> (1 | 2-3 | 4-6 | 7+,")
print("     yard line) -> ag1's levels as landed; distw is the distance as Game.mark writes it (the written yard line less the line to gain's floor; the record's own")
print("     written distance on its rows), 1 ... 10, 11+; MIN_BIN 30; no fitted model, no new input. Check: the share of fourth-and-1 draws at a level keyed by distw,")
print("     landed beside candidate, above at every one of ah1's ten zones. Case: 4th and 1 at the own 45, first quarter, tied: the go share within 2SE of the record's")
print("     own 41-49 at 1 (read from disk). Plant: ag1's levels on the candidate's tables must read APART on the case.")
print("  ai2 reads: ah1's grid on the candidate beside v37's; punts and field goal tries by zone (the pool's population), the punt gap split as ah2 split it; the make")
print("     share under 30 yards. ai3 (a read, nothing built): first- and second-down gains and third-down conversion by zone outside the red zone, and the level")
print("     each snap draw resolved at by zone and down (a new counter in the read engine and the candidate).")
print("  the standing rule: before-to-after checks are not carried (af0's and ag0's gates, ag1's check removed); state checks and plants are (af1's plant; ag1's case,")
print("     and ag1's plant as the levels before ag1 (FULL) on the candidate's tables).")
print("COST (declared before the run): the engine's tables rebuilt; v36's and v37's games read through the record reader (two sides more); ai1's plant's Rates (six")
print("  seasons); v37's run 538 s; over 600 s is INCOMPLETE.")
print("PREDICTIONS (ai as written, each HELD, NOT HELD or NOT MEASURED with its number): ai0 (b) 4th and 1 shares a bin with 2-3 (read); after ai1 the go share at 4th")
print("  and 1 within 2SE in at least 4 of the 5 zones above the 11-20 and in the 11-20; the go share at 4th and 2-3 within 2SE in the same zones; the punt share's part of")
print("  the punt gap below 0.2; plays within 2SE; points printed, no size (v37 41.08).")
PIN = {"r1.py": "684d8fed2311", "r2.py": "567e8946b4e0", "r4.py": "8532a090b885", "record.py": "a18b89fe7985", "contract.py": "c141f8d3086a",
       "r7.py": "944aef150c1b", "l0.py": "ede0aef941c2", "e1.py": "4f28bf6aa3cc", "out/sim_games.csv": "d3d2dd1303de", "out/r7_seasons.csv": "1d3606b8c099",
       "out/e1_checks.csv": "f54577bfd3be", "rules/RULE_PINS.json": "ca8b1060e3aa", "PROGRESS.md": "811fddf2ab32", "E2_TARGETS.md": "165d9321da35", "transition.py": "fcca26b4997f", "test_transition.py": "d47712aa9faa", "out/engine/MANIFEST.json": "c539a85289bc", "clock_check.py": "981facf94d61",
       "rules/play_clock_pins.tsv": "5b83ab1dda95", "rules/warning_pins.tsv": "3dc29875f627", "rules.py": "3d9b5a3b1985"}
bad = 0
for p, v in PIN.items():
    g = sh(p); bad += g != v; print(f"pin {p} {g} (expected {v}) {'ok' if g == v else 'DIFFERS'}")
print(f"the chain {CHAIN_FILE} sha {CSHA} | run {RUN_ID} | evidence {EVD}")
if bad: stop("a file is not at its lock; nothing run")
TT = open("E2_TARGETS.md").read()
HT_ = [l_ for l_ in TT.split("\n") if l_.startswith("## E2b v19 ai")]
print(f"targets: headings starting '## E2b v19 ai': {HT_} (must be one)")
if len(HT_) != 1: stop("E2b v19 ai is not as read; nothing run")
V19Y = TT[TT.index(HT_[0]):]
for n_ in ("ai0", "ai1", "ai2", "ai3"):
    c_ = sum(1 for l_ in V19Y.split("\n") if l_.startswith(n_ + ". ") or l_.startswith(n_ + " ("))
    print(f"targets: v19 ai lines starting '{n_}.' or '{n_} (' {c_} (must be 1 or more)")
    if not c_: stop("E2b v19 ai is not as read; nothing run")
print(f"E2b v19 ai as read from the file (sha {shs(V19Y)}; the owner's prints a84d1805f2cd for ai alone, 0f9957ed2492 for its addition):"); print(V19Y.strip())
c_ = sum(1 for l_ in V19Y.split("\n") if l_.startswith("### v19 ai addition"))
print(f"targets: lines starting '### v19 ai addition' {c_} (must be 1)")
if c_ != 1: stop("E2b v19 ai's addition is not as read; nothing run")
print("SERVED: each requirement of ai, and where this chain serves it, or that it does not:")
for r_ in ("ai0 (a) as amended: z4 kept (the corrected ah read reproduced 20 of 48), its label corrected; ah1's reader and its plant printed every run: served in 'ac2'",
           "ai0 (b) dist_bin and the pool's distance keys by line; the gate: served in 'ac2' and as a landing check",
           "ai1 the whole-yard distance first, ag1's levels after, MIN_BIN 30, no fitted model: served (the candidate e1.py); its check, case and plant: served and landing checks",
           "ai2 ah1's grid, the punt split, field goal tries by zone, the make share under 30: served in 'ac2'; ai3 gains, conversions and the snap levels by zone: served in 'ac2'",
           "  7-3-1, 7-3-2 and Rule 11's field goal article cited by line from each season's book: NOT SERVED by line (no book reader for them here; named, not hidden)",
           "the landing checks: the landed engine's state checks and every plant, plus ai1's: served; predictions as written: served; DONE WHEN, 600 s, quick first: served"):
    print("  " + r_)
sys.path.insert(0, os.getcwd())
import record, contract, rules, r1, r2, r4, e1
S = e1.SIM_SEASONS
if FIXTURE:
    FXP = "fixtures/real_games.csv.gz"
    if sh(FXP) != "bcdcac8081cf": stop(f"{FXP} is {sh(FXP)}, not bcdcac8081cf; nothing run")
    FX = pd.read_csv(FXP, dtype=str, keep_default_na=False)
    FXG = set(FX["game_id"])
    _raw = record.raw_frame
    def _raw_fx(name, columns, where):
        m = re.fullmatch(r"pbp_(\d{4})\.csv\.gz", name)
        if not m: return _raw(name, columns, where)
        bet = [c for c in contract.BETTING_EXCLUDED if c in columns]
        if bet: raise record.GAP(f"{where}: betting inputs requested {bet}")
        miss = [c for c in columns if c not in FX.columns]
        if miss:
            ex_ = _raw(name, ["game_id", "play_id"] + miss, where); ex_ = ex_[ex_["game_id"].isin(FXG)]
            base_ = FX[FX["season"] == m.group(1)][[c for c in columns if c in FX.columns] + (["play_id"] if "play_id" not in columns else [])]
            out_ = base_.merge(ex_, on=["game_id", "play_id"], how="left", validate="one_to_one")
            return out_[list(columns)].reset_index(drop=True).copy()
        return FX[FX["season"] == m.group(1)][list(columns)].reset_index(drop=True).copy()
    record.raw_frame = _raw_fx
    print(f"QUICK RUN on {FXP} (sha {sh(FXP)}): {len(FXG)} real games (columns the fixture lacks read from the pinned record files for its own games). the numbers here are not the engine's quality")
    print("not among them (each prints 'not in this run'); the table and the working tables go to a scratch folder; no fixture file is written; the run's evidence")
    print("is written to its own folder.")
OUT_TABLE = os.path.join(tempfile.mkdtemp(), "interval_table.csv") if FIXTURE else "out/interval_table.csv"
LIB_DIR = tempfile.mkdtemp(); LIB_FILE = os.path.join(LIB_DIR, "e2b_v29_lib.py"); open(LIB_FILE, "w").write('"""E2b v19 aa\'s shared code (module e2b_v29_lib): one module for this process and every worker process, written out by the chain and imported by both: the counting function,\nthe estimators and the workers; the one transition (transition.py) and section 4\'s check (clock_check.py) are the product files it imports."""\nimport os, re, sys, io, time, json, pickle, hashlib, tempfile, shutil, threading, importlib.util\nfrom collections import Counter, defaultdict\nimport numpy as np, pandas as pd\nimport record, contract, rules, r1, r2, r4, e1\nfrom rules import next_down, next_possession\nS = list(e1.SIM_SEASONS)\nWARN_SEC = {}\nRUNOFF_RESTART = {}\nT_CAP = 40   # the pinned play clock (4-6-1), configured by the chain from rules/play_clock_pins.tsv\nENGINE_CONF = {}   # v19 part 2: the engine\'s module values its caller sets (PACE_SPLIT, RUNOFF_RESTART, SCRIM_TB, BOOKY), the same in every process\nSCRIM_TB = {}   # season -> (the yard line a touchback that is not a free kick puts the ball in play on, the place it was read) | (None, why): Rule 11 Section 6\nshs = lambda t: hashlib.sha256(t.encode()).hexdigest()[:12]\nshb = lambda b: hashlib.sha256(b).hexdigest()[:12]\n\n\ndef configure(**kw):\n    globals().update(kw)\n\n\ndef nanv(x):\n    return x is None or (not isinstance(x, str) and pd.isna(x))\n\n\ndef one_(x):\n    return (not nanv(x)) and x == 1\n\n\nclass SharedParse:\n    """Inside the block, e1.load, r1.load, r2.load and r4.load each parse a season once per record.raw_frame and hand out copies."""\n    def __enter__(self):\n        self.saved = {}; self.memo = {}\n        for mod, nm in ((e1, "load"), (r1, "load"), (r2, "load"), (r4, "load")):\n            f = getattr(mod, nm); self.saved[(mod, nm)] = f\n            def wrap(s, f=f, key=mod.__name__):\n                k = (key, id(record.raw_frame), s)\n                if k not in self.memo: self.memo[k] = f(s)\n                v = self.memo[k]\n                return tuple(x.copy() if isinstance(x, pd.DataFrame) else x for x in v) if isinstance(v, tuple) else v.copy()\n            setattr(mod, nm, wrap)\n        return self\n\n    def __exit__(self, *a):\n        for (mod, nm), f in self.saved.items(): setattr(mod, nm, f)\n\n\ndef gse2(v, g):\n    """2SE of a mean, taken by game (games are the unit)."""\n    v = np.asarray(v, float); g = np.asarray(g); n_ = len(v)\n    if n_ < 2: return np.nan\n    m = v.mean(); s_ = pd.Series((v - m) / n_).groupby(g).sum(); G = len(s_)\n    return 2 * np.sqrt((s_ ** 2).sum() * G / (G - 1)) if G > 1 else np.nan\n\n\ndef share(k, n, nd=4):\n    """A share over 0 rows is not a number."""\n    return "NOT MEASURED (0 rows)" if not n else f"{k / n:.{nd}f} ({int(k)} of {int(n)})"\n\n\ndef per(k, n, unit):\n    """A rate over its own population, the population named (d: every rate divides by its own population)."""\n    return f"NOT MEASURED (0 {unit})" if not n else f"{k / n:.3f} a {unit[:-1] if unit.endswith(\'s\') else unit} ({int(k)} over {int(n)} {unit})"\n\n\ndef plant_verdict(n_targets, failed):\n    """d: a plant with nothing to plant into is VACUOUS, never \'did not fail\'."""\n    return "VACUOUS (nothing to plant into)" if not n_targets else ("FAILS as it must" if failed else "DID NOT FAIL")\n\n\n\n\n\n# ---------------- the product files: the one transition (transition.py) and section 4\'s check (clock_check.py), imported from the project folder ----------------\n# The library no longer carries its own copies: the record\'s rebuild, the engine (every worker) and section 4 call the landed files; their shas are in LIBSHA.\nimport transition as T, clock_check as CC\nfrom transition import (TPARTS, series, kick_to_come, unknown, same, int_end, punt_end, kick_end, second, after, after_one, FIXTURES, run_fixtures, planted,\n                        PLANTS, STAND_PLANTS, planted_stand, enforced_at, STAND_PREFIX, foul_yards, spot_foul_yards,\n                        run_yard_cases, YARD_PLANTS, goal_half)\nfrom clock_check import injury_text, _InjRead, down_row, STOP_AT_PLAY, warn_place, RUNOFF_RX, INJ_RX, INJ_UPD_RX\n\n\ndef tb_rules(season, x6cell):\n    """transition.tb_rules with the Rule 11 Section 6 spots the chain read (SCRIM_TB, configured in every process)."""\n    return T.tb_rules(season, x6cell, SCRIM_TB)\n\n\ndef check_clock2(seasons, keep_rows=False):\n    """clock_check.check_clock2 with the warning\'s sections the chain read (WARN_SEC, configured in every process; a label only)."""\n    return CC.check_clock2(seasons, keep_rows, WARN_SEC)\n\n# ---------------- E2a: the shared counting function (one code, both sides) ----------------\nSNAPK = set(rules.SNAP_KINDS)\nOWN_FOULS = ("False Start", "Defensive Offside", "Offensive Holding", "Defensive Holding", "Intentional Grounding", "Unsportsmanlike Conduct")\nKINDS = {"offensive touchdown": "pts_off_td", "kickers\' touchdown": "pts_kick_td", "return touchdown": "pts_ret_td", "defensive touchdown": "pts_def_td",\n         "field goal": "pts_fg", "try, kick": "pts_try_kick", "try, two-point": "pts_try_two", "try, defensive return": "pts_def_try", "safety": "pts_safety"}\nFAILP, BACK, SIDE, PLANT_X, PLANT_KIND = [], [], ["record"], [None], ["return touchdown"]\n\n\ndef credit(x, double=None):\n    """E2a v3 a: one kind per score, decided by who scored on which play."""\n    n = len(x); kind = [""] * n; hp = np.zeros(n); ap = np.zeros(n); home = x["home_team"].iloc[0]\n    for i in range(n):\n        pt = x.at[i, "play_type"]; tt = x.at[i, "td_team"]; pos = x.at[i, "posteam"]; dfn = x.at[i, "defteam"]; k = None\n        if one_(x.at[i, "touchdown"]) and isinstance(tt, str):\n            if pt in ("kickoff", "punt"):\n                recv, kick = (pos, dfn) if pt == "kickoff" else (dfn, pos)\n                k = "return touchdown" if tt == recv else ("kickers\' touchdown" if tt == kick else f"touchdown on a {pt} by a team not on the field")\n            elif pt in SNAPK: k = "offensive touchdown" if tt == pos else "defensive touchdown"\n            else: k = f"touchdown on a {pt} row"\n            who, p = tt, 6\n        elif pt == "field_goal" and x.at[i, "field_goal_result"] == "made": k, who, p = "field goal", pos, 3\n        elif pt == "extra_point" and x.at[i, "extra_point_result"] == "good": k, who, p = "try, kick", pos, 1\n        elif one_(x.at[i, "two_point_attempt"]) and x.at[i, "two_point_conv_result"] == "success": k, who, p = "try, two-point", pos, 2\n        elif one_(x.at[i, "defensive_two_point_conv"]) or one_(x.at[i, "defensive_extra_point_conv"]): k, who, p = "try, defensive return", dfn, 2\n        elif one_(x.at[i, "safety"]):\n            k, p = "safety", 2\n            who = pos if (pt == "punt" and re.search(r"punts -?\\d+ yards", str(x.at[i, "desc"])) and "BLOCKED" not in str(x.at[i, "desc"]).upper()) else dfn\n        if k:\n            kind[i] = k\n            if who == home: hp[i] += p\n            else: ap[i] += p\n            if double == i:\n                if who == home: hp[i] += p\n                else: ap[i] += p\n    return kind, hp, ap\n\n\ndef score_state(d):\n    if d <= -9: return "behind 9+"\n    if d < 0: return "behind 1-8"\n    if d == 0: return "tied"\n    if d <= 8: return "ahead 1-8"\n    return "ahead 9+"\n\n\ndef count_side(seasons):\n    """Per game and per possession tables for one side, every number from r1.possessions, r2.intervals and e1.load (record.raw_frame decides the side)."""\n    G, PO, ST = [], [], []\n    for s in seasons:\n        d = e1.load(s)\n        d2, _, _ = r2.load(s)\n        d1 = r1.load(s).sort_values(["game_id", "order_sequence"]).reset_index(drop=True)\n        P = r1.possessions(d1)\n        th = d.groupby("game_id")["total_home_score"].transform(lambda v: v.ffill().shift().fillna(0))\n        ta = d.groupby("game_id")["total_away_score"].transform(lambda v: v.ffill().shift().fillna(0))\n        d["h0"], d["a0"] = th, ta\n        d["h1"] = d.groupby("game_id")["total_home_score"].transform(lambda v: v.ffill().fillna(0))\n        d["a1"] = d.groupby("game_id")["total_away_score"].transform(lambda v: v.ffill().fillna(0))\n        d["pts_row"] = (d["h1"] - d["h0"]) + (d["a1"] - d["a0"])\n        GD = {g: x.reset_index(drop=True) for g, x in d.groupby("game_id", sort=False)}\n        PG = {g: x.reset_index(drop=True) for g, x in P.groupby("game_id", sort=False)}\n        for g, gd in d2.groupby("game_id", sort=False):\n            x = GD[g]; reg = gd["season_type"].iloc[0] == "REG"\n            seqi = {int(v): k for k, v in enumerate(x["order_sequence"])}\n            pt = x["play_type"].tolist(); q_ = x["qtr"].astype(int).tolist(); pos = x["posteam"].tolist(); qs = x["quarter_seconds_remaining"].tolist()\n            snap = [pt[k] in SNAPK and not one_(x.at[k, "two_point_attempt"]) for k in range(len(x))]\n            pp = PG.get(g, pd.DataFrame(columns=P.columns))\n            plist = list(pp.itertuples(index=False))\n            gsr = lambda k: (4 - q_[k]) * 900 + qs[k] if q_[k] <= 4 else qs[k]\n            prev_end = None\n            for j, p_ in enumerate(plist):\n                a = seqi[int(p_.s0)]; b = seqi[int(p_.s1)]\n                ks = [k for k in range(a, b + 1) if snap[k] and pos[k] == p_.team]\n                kl = b\n                r = x.loc[kl]\n                half = 1 if q_[a] <= 2 else (2 if q_[a] <= 4 else 3)\n                nxt = plist[j + 1] if j + 1 < len(plist) else None\n                nh = None if nxt is None else (1 if q_[seqi[int(nxt.s0)]] <= 2 else (2 if q_[seqi[int(nxt.s0)]] <= 4 else 3))\n                if one_(r["touchdown"]) and r["td_team"] == p_.team and r["play_type"] not in ("kickoff", "punt"): end = "touchdown"\n                elif r["play_type"] == "field_goal": end = "field goal try"\n                elif r["play_type"] == "punt": end = "punt"\n                elif one_(r["safety"]): end = "safety"\n                elif one_(r["interception"]) or one_(r["fumble_lost"]): end = "turnover"\n                elif nxt is not None and nh == half and nxt.team != p_.team and r["down"] == 4: end = "turnover on downs"\n                elif nxt is None or nh != half: end = "end of half"\n                else: end = "other"\n                lo = seqi[int(plist[j - 1].s1)] + 1 if j > 0 else 0\n                between = pt[lo:a]\n                if "kickoff" in between or j == 0 or (j > 0 and (1 if q_[seqi[int(plist[j - 1].s0)]] <= 2 else (2 if q_[seqi[int(plist[j - 1].s0)]] <= 4 else 3)) != half): beg = "kickoff"\n                elif prev_end == "punt": beg = "punt"\n                elif prev_end == "turnover": beg = "turnover"\n                elif prev_end == "turnover on downs": beg = "turnover on downs"\n                elif prev_end == "field goal try": beg = "missed field goal"\n                else: beg = "other"\n                prev_end = end\n                if half <= 2:\n                    end_g = 1800 if half == 1 else 0\n                    sec = gsr(a) - (gsr(seqi[int(nxt.s0)]) if nh == half else end_g)\n                else:\n                    sec = np.nan\n                yl = x["yardline_100"].iloc[ks].astype(float) if ks else pd.Series(dtype=float)\n                reached = lambda t: bool(len(yl) and (yl.min() <= t)) or end == "touchdown"\n                PO.append(dict(season=s, game_id=g, reg=reg, ot=half == 3, half=half, team=p_.team, end=end, begin=beg, snaps=len(ks), sec=sec,\n                               start_yl=float(x.at[a, "yardline_100"]) if not nanv(x.at[a, "yardline_100"]) else np.nan, r40=reached(40), r20=reached(20),\n                               fg_made=r["play_type"] == "field_goal" and r["field_goal_result"] == "made",\n                               score=score_state((r["h0"] - r["a0"]) * (1 if p_.team == x.at[a, "home_team"] else -1))))\n            iv = r2.intervals(gd)\n            for t in iv:\n                if t["q"] > 4: continue\n                ka, kb = seqi[t["sa"]], seqi[t["sb"]]\n                la = np.nan\n                if not (nanv(x.at[ka, "E"]) or nanv(x.at[ka, "W"])): la = float(x.at[ka, "E"] - x.at[ka, "W"])\n                dG = float(t["dG"]); on_play = np.nan if nanv(la) else min(max(la, 0.0), dG)\n                sc = score_state((x.at[ka, "h0"] - x.at[ka, "a0"]) * (1 if pos[ka] == x.at[ka, "home_team"] else -1))\n                ST.append(dict(season=s, game_id=g, reg=reg, sa=t["sa"], sb=t["sb"], half=1 if t["q"] <= 2 else 2, q=t["q"], tb=e1.time_bin(t["q"], t["qa"]), cls=t["cls"], dG=dG,\n                               on_play=on_play, between=bool(t["poss"]), score=sc, qa=float(t["qa"]), x=float(t["x"]) if not nanv(t["x"]) else np.nan, d3=t["d3"],\n                               inc=bool(t["inc"]), ob=one_(t["ob"]), tmo=bool(t["tmo"]), tmw=t["tmw"] is True,\n                               nopl=any(pt[k] == "no_play" and one_(x.at[k, "penalty"]) for k in range(ka + 1, kb)),\n                               tb2="last 2:00 of the game" if t["q"] == 4 and t["qa"] <= 120 else e1.time_bin(t["q"], t["qa"]),\n                               lsf=sc if (t["q"] in (2, 4) and t["qa"] <= 120) else "-"))\n            pre = post = 0.0; n_snaps_reg = 0\n            for qq in (1, 2, 3, 4):\n                ks = [k for k in range(len(x)) if snap[k] and q_[k] == qq]\n                if not ks: continue\n                pre += 900 - float(qs[ks[0]]); post += float(qs[ks[-1]]); n_snaps_reg += len(ks)\n            st_g = sum(t["dG"] for t in iv if t["q"] <= 4)\n            fam = {}\n            lat = x["lateral_receiver_player_id"].notna() | x["lateral_rusher_player_id"].notna()\n            desc = x["desc"].astype(str)\n            fam["laterals"] = lat\n            fam["fouls by both teams (offsetting)"] = desc.str.contains("offsetting", case=False)\n            fam["a foul and a turnover on one play"] = (x["penalty"] == 1) & ((x["interception"] == 1) | (x["fumble_lost"] == 1))\n            fam["fumbles kept by the side that lost them"] = x["fumble_recovery_1_team"].notna() & (x["fumble_recovery_1_team"] == x["posteam"]) & x["play_type"].isin(list(SNAPK))\n            fam["replay reviews"] = x["replay_or_challenge"] == 1\n            fam["injuries"] = desc.str.contains("injur", case=False)\n            fam["runoffs"] = desc.str.contains(r"run[- ]?off", case=False)\n            fam["return touchdowns (kickoff, punt)"] = (x["touchdown"] == 1) & x["play_type"].isin(["kickoff", "punt"])\n            fam["defensive touchdowns"] = (x["touchdown"] == 1) & x["play_type"].isin(list(SNAPK)) & x["td_team"].notna() & (x["td_team"] != x["posteam"])\n            fam["fouls v0 does not play"] = (x["penalty"] == 1) & x["penalty_type"].notna() & ~x["penalty_type"].isin(list(OWN_FOULS))\n            istry = ((x["play_type"] == "extra_point") | (x["two_point_attempt"] == 1)).to_numpy()\n            def with_try(m):\n                m = m.fillna(False).astype(bool).to_numpy().copy()\n                for k in np.where(m & (x["touchdown"] == 1).to_numpy())[0]:\n                    j = k + 1\n                    while j < len(x) and pt[j] in ("", "no_play", None) and not istry[j]: j += 1\n                    if j < len(x) and istry[j]: m[j] = True\n                return pd.Series(m, index=x.index)\n            fam = {k_: with_try(v) for k_, v in fam.items()}\n            anyfam = pd.Series(False, index=x.index)\n            for v in fam.values(): anyfam = anyfam | v\n            kind, hp, ap = credit(x)\n            dh = (x["h1"] - x["h0"]).to_numpy(); da = (x["a1"] - x["a0"]).to_numpy()\n            badp = np.where((hp != dh) | (ap != da))[0]\n            for i in badp:\n                FAILP.append((SIDE[0], s, g, int(x.at[i, "order_sequence"]), int(x.at[i, "qtr"]), x.at[i, "play_type"], kind[i] or "none", f"credited home {hp[i]:.0f} away {ap[i]:.0f}",\n                              f"board home {dh[i]:.0f} away {da[i]:.0f}", str(x.at[i, "desc"])[:200]))\n            total = float(max(x["h1"].max(), 0) + max(x["a1"].max(), 0))\n            qq = x["qtr"].to_numpy(); qsv = x["quarter_seconds_remaining"].to_numpy(dtype=float)\n            back, latest = [], -1.0\n            for i in range(len(x)):\n                if qq[i] > 4 or np.isnan(qsv[i]): continue\n                tnow = (qq[i] - 1) * 900 + (900 - qsv[i])\n                if tnow < latest: back.append(i)\n                latest = max(latest, tnow)\n            for i in back:\n                BACK.append((SIDE[0], s, g, int(x.at[i, "order_sequence"]), int(qq[i]), qsv[i - 1], qsv[i], str(x.at[i - 1, "desc"])[:120], str(x.at[i, "desc"])[:160]))\n            gr = dict(season=s, game_id=g, reg=reg, has_ot=bool((x["qtr"] >= 5).any()), points=total, snaps=int(sum(snap)), snaps_reg=n_snaps_reg,\n                      no_plays=int(((x["play_type"] == "no_play") & (x["timeout"] != 1)).sum()), rows=len(x),\n                      clock_pre=pre, clock_stretch=st_g, clock_post=post, bad_plays=len(badp), back_steps=len(back))\n            for k_, c_ in KINDS.items(): gr[c_] = float(sum(hp[i] + ap[i] for i in range(len(x)) if kind[i] == k_))\n            gr["pts_unclassed"] = float(sum(hp[i] + ap[i] for i in range(len(x)) if kind[i] and kind[i] not in KINDS))\n            for k_, v in fam.items(): gr["ub " + k_] = float(x.loc[v, "pts_row"].clip(lower=0).sum())\n            gr["ub any family (union)"] = float(x.loc[anyfam, "pts_row"].clip(lower=0).sum())\n            G.append(gr)\n    return pd.DataFrame(G), pd.DataFrame(PO), pd.DataFrame(ST)\n\n\n# ---------------- h: one shared parse per side and season (a cache of the readers\' results, copies handed out) ----------------\n# ---------------- helpers ----------------\nCLS = ["RUN", "STOP", "PARTIAL"]\nAH, BH = ("ahead 1-8", "ahead 9+"), ("behind 1-8", "behind 9+")\nLEV = [("cls", "tb", "ls"), ("cls", "tb"), ("cls",)]\nTB2 = ["normal", "last 2:00 of the first half", "last 5:00 of the game", "last 2:00 of the game"]\nTO_N = re.compile(r"Timeout #(\\d+) by ([A-Z]{2,3})")\n\n\ndef late(x):\n    return x["q"].isin([2, 4]) & (x["qa"] <= 120)\n\n\ndef keyed(x, split):\n    x = x.copy(); on = x["cls"].map(lambda c: bool(split.get(c))) & late(x)\n    x["ls"] = np.where(on, x["score"], "-"); return x\n\n\ndef kstr(x, L):\n    return x[list(L)].astype(str).agg(" | ".join, axis=1)\n\n\ndef cm(x, val="dG"):\n    n = len(x)\n    if n < 2 or x["game_id"].nunique() < 2: return (x[val].mean() if n else np.nan), np.nan, n\n    m = x[val].mean(); g = ((x[val] - m) / n).groupby(x["game_id"].values).sum(); G = len(g)\n    return m, 2 * np.sqrt((g ** 2).sum() * G / (G - 1)), n\n\n\ndef within(a, b):\n    d = b[0] - a[0]; s = np.sqrt(a[1] ** 2 + b[1] ** 2)\n    return d, s, (not np.isnan(s)) and abs(d) <= s\n\n\ndef mg(v):\n    v = pd.Series(v, dtype=float); n = len(v)\n    return v.mean(), (2 * v.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan)\n\n\ndef boot(df, val, q, B=200, seed=0):\n    if not len(df): return np.nan, np.nan\n    g = {k: v[val].to_numpy() for k, v in df.groupby("game_id")}; keys = list(g); rng = np.random.default_rng(seed)\n    est = float(np.percentile(df[val], q)); bs = []\n    for _ in range(B):\n        pick = rng.integers(len(keys), size=len(keys)); bs.append(np.percentile(np.concatenate([g[keys[i]] for i in pick]), q))\n    return est, 2 * float(np.std(bs, ddof=1))\n\n\ndef moments(d):\n    """Every charged timeout row in regulation with its moment, caller, number, the real seconds and the game seconds run since the act before it."""\n    out = []\n    for g, x in d.groupby("game_id", sort=False):\n        x = x.reset_index(drop=True); n = len(x)\n        rk = [e1.row_kind(p, k, t) for p, k, t in zip(x["play_type"], x["kind"], x["two_point_attempt"])]\n        desc = x["desc"].astype(str).tolist(); q = x["qtr"].tolist(); qs = x["quarter_seconds_remaining"].tolist(); pos = x["posteam"].tolist()\n        W = x["W"].tolist(); E = x["E"].tolist()\n        for i in range(n):\n            if not e1.one(x.at[i, "timeout"]) or q[i] > 4: continue\n            m = TO_N.search(desc[i])\n            j = i - 1; warn = False\n            while j >= 0 and q[j] == q[i] and rk[j] == "other":\n                if "two-minute warning" in desc[j].lower(): warn = True\n                j -= 1\n            if j < 0 or q[j] != q[i]: mom = "start of the quarter"\n            elif warn: mom = "after the two-minute warning"\n            elif rk[j] == "snap":\n                nx = next((k for k in range(i + 1, n) if rk[k] == "snap" and q[k] == q[i]), None)\n                same = nx is not None and pos[nx] == pos[j] and not (e1.one(x.at[j, "touchdown"]) or x.at[j, "field_goal_result"] == "made" or e1.one(x.at[j, "safety"]))\n                mom = "after a snap, the same team snaps next" if same else "after a snap that ended the possession or scored"\n            else: mom = {"kickoff": "after a kickoff", "try": "after a Try", "foul": "after a foul", "timeout": "right after another timeout"}.get(rk[j], f"after a row of kind {rk[j]}")\n            ns = next((k for k in range(i + 1, n) if rk[k] == "snap"), None)\n            caller = "not charged by its text" if not m else ("no next snap" if ns is None else ("offense" if m.group(2) == pos[ns] else "defense"))\n            st = E[j] if (j >= 0 and not e1.nan(E[j])) else (W[j] if j >= 0 else np.nan)\n            rs = W[i] - st if not (e1.nan(W[i]) or e1.nan(st)) else np.nan\n            after = (qs[j] - (E[j] - W[j])) if (j >= 0 and rk[j] in ("snap", "kickoff") and not (e1.nan(E[j]) or e1.nan(W[j]))) else (qs[j] if j >= 0 and rk[j] not in ("snap", "kickoff") else np.nan)\n            gr = max(after - qs[i], 0.0) if not e1.nan(after) else np.nan\n            sc = e1.score_bin(x.at[ns, "diff"]) if (ns is not None and "diff" in x.columns) else "-"\n            out.append(dict(game_id=g, season=x.at[i, "season"], q=q[i], qs=qs[i], tb2="last 2:00 of the game" if q[i] == 4 and qs[i] <= 120 else e1.time_bin(q[i], qs[i]),\n                            moment=mom, caller=caller, team=m.group(2) if m else None, num=int(m.group(1)) if m else -1, charged=bool(m), real_since=rs, game_run=gr, score=sc))\n    return pd.DataFrame(out)\n\n\ndef with_diff(d):\n    d = d.copy()\n    th = d.groupby("game_id")["total_home_score"].transform(lambda s: s.ffill().shift().fillna(0)); ta = d.groupby("game_id")["total_away_score"].transform(lambda s: s.ffill().shift().fillna(0))\n    d["diff"] = np.where(d["posteam"] == d["home_team"], th - ta, ta - th); return d\n\n\ndef left_at_half(TMx, games):\n    out = {}\n    T = TMx[TMx["charged"]].assign(half=lambda z: np.where(z["q"] <= 2, 1, 2))\n    cnt = T.groupby(["game_id", "half", "team"]).size()\n    for h in (1, 2):\n        for k in (3, 2, 1, 0, -1):\n            v = []\n            for g, home, away in games:\n                used = [int(cnt.get((g, h, t_), 0)) for t_ in (home, away)]\n                left = [3 - u for u in used]\n                v.append(np.mean([(l_ == k) if k >= 0 else (l_ < 0) for l_ in left]))\n            out[(h, k)] = mg(v)\n    return out\n\n\n\n# ---------------- the estimators (fixed as v12 ran them) ----------------\nTREE = dict(learning_rate=0.1, max_leaf_nodes=15, min_samples_leaf=e1.MIN_BIN, l2_regularization=0.0, early_stopping=False, random_state=0)\nCAP = {"run": 500, "stop": 500}\n\n\ndef fit_part(X, y, seasons, cap, inner_model=None):\n    from sklearn.ensemble import HistGradientBoostingClassifier as HGB\n    inner = max(set(seasons.tolist())); tr = seasons != inner; te = ~tr\n    if tr.sum() == 0 or te.sum() == 0 or len(np.unique(y[tr])) < 2: raise record.GAP("refused: no inner held-out season with two or more classes to choose rounds on")\n    m = inner_model if inner_model is not None else HGB(**dict(TREE, max_iter=cap)).fit(X[tr], y[tr])\n    idx = {c: k for k, c in enumerate(m.classes_)}; keep = np.array([v in idx for v in y[te]]); yi = np.array([idx[v] for v in y[te][keep]], dtype=int)\n    ll = [float(-np.mean(np.log(np.clip(p[np.arange(len(yi)), yi], 1e-300, None)))) for p in m.staged_predict_proba(X[te][keep])]\n    best = int(np.argmin(ll)) + 1\n    if best >= cap: raise record.GAP(f"refused: the lowest inner log loss is at the ceiling ({cap} rounds)")\n    final = HGB(**dict(TREE, max_iter=best)).fit(X, y)\n    return final, dict(inner=int(inner), best=best, cap=cap, ll_best=ll[best - 1], ll_first=ll[0], ll_cap=ll[-1], unseen=int((~keep).sum()), n=len(y))\n\n\nRACE_TBINS = ((0, 7), (8, 15), (16, 23), (24, 31), (32, 40))   # v19 w1: the seconds already run on the play clock, in 8-second bins, crossed with the time left in the half\n\n\ndef race_design(X, mu, sd, tcap):\n    """v19 w1: the race\'s inputs (the same text in e1.py): the numbers standardised; t (the seconds since the play ended, read up to the play clock) one\n    indicator a second; and the time left in the half crossed with t: the last two minutes of a half (quarters 2 and 4, the quarter\'s clock at the play\'s end\n    less t at or under 120) and quarters 2 and 4 apart from 1 and 3, each times RACE_TBINS. X: q, the clock at the play\'s end, the score difference, down,\n    distance, yard line, the timeouts each side has, review, injury, t."""\n    t = np.clip(X[:, -1].astype(int), 0, tcap)\n    I = np.zeros((len(X), tcap)); r = np.where(t > 0)[0]; I[r, t[r] - 1] = 1.0\n    q = X[:, 0]; q24 = (q == 2) | (q == 4); late = q24 & ((X[:, 1] - X[:, -1]) <= 120)\n    B = np.column_stack([(t >= a_) & (t <= b_) for a_, b_ in RACE_TBINS]).astype(float)\n    return np.column_stack([(X[:, :-1] - mu) / sd, I, B * late[:, None], B * q24[:, None]])\n\n\nclass LRRace:\n    """The race\'s estimator: a multinomial logistic race (v12\'s: no penalty; lbfgs, at most 1,000 iterations) on race_design\'s inputs (v19 w1: the time left\n    in the half crossed with the play clock\'s seconds added). shuffle: w1\'s plant only, the time-left columns permuted across moments before the fit."""\n    def __init__(self, X, y, shuffle=None):\n        from sklearn.linear_model import LogisticRegression\n        self.tcap = T_CAP\n        self.mu = X[:, :-1].mean(0); self.sd = X[:, :-1].std(0); self.sd[self.sd == 0] = 1.0\n        D_ = self.design(X)\n        if shuffle is not None:\n            k_ = 2 * len(RACE_TBINS); D_[:, -k_:] = D_[np.random.default_rng(shuffle).permutation(len(D_)), -k_:]\n        self.m = LogisticRegression(penalty=None, max_iter=1000).fit(D_, y)\n        self.classes_ = self.m.classes_; self.iters = int(np.max(self.m.n_iter_)); self.converged = self.iters < 1000\n\n    def design(self, X):\n        return race_design(X, self.mu, self.sd, self.tcap)\n\n    def predict_proba(self, X):\n        return self.m.predict_proba(self.design(X))\n\n\ndef lr_bytes(M_):\n    return pickle.dumps((M_.m, M_.mu, M_.sd))\n\n\ndef tree_bytes(M_):\n    """h: a fitted tree model\'s content as bytes (its classes, starting values, every tree\'s nodes, the bin edges, its rounds); the run settings it also\n    pickles (the thread count, object identity inside pickle) are not fitted content and are left out."""\n    return pickle.dumps(([str(c) for c in M_.classes_], np.asarray(M_._baseline_prediction).tobytes(), [[p.nodes.tobytes() for p in it] for it in M_._predictors],\n                         [np.asarray(b).tobytes() for b in M_._bin_mapper.bin_thresholds_], int(M_.n_iter_)))\n\n\nclass Batcher:\n    def __init__(self, parts, n):\n        self.parts = parts; self.cv = threading.Condition(); self.active = n; self.req = {}; self.res = {}; self.err = None; self.batches = 0\n\n    def eval(self, part, X):\n        tid = threading.get_ident()\n        with self.cv:\n            self.req[tid] = (part, X); self._run()\n            self.cv.wait_for(lambda: tid in self.res or self.err is not None)\n            if self.err is not None and tid not in self.res: raise self.err\n            return self.res.pop(tid)\n\n    def done(self):\n        with self.cv:\n            self.active -= 1; self._run()\n\n    def _run(self):\n        if not self.req or len(self.req) < self.active: return\n        try:\n            for part in {p for p, _ in self.req.values()}:\n                ids = [t for t, (p, _) in self.req.items() if p == part]; Xs = [self.req[t][1] for t in ids]\n                P = self.parts[part].predict_proba(np.vstack(Xs)); k = 0\n                for t, x in zip(ids, Xs): self.res[t] = P[k:k + len(x)]; k += len(x)\n            self.batches += 1\n        except Exception as ex_:\n            self.err = ex_\n        self.req.clear(); self.cv.notify_all()\n\n\ndef play_threaded(m, s, sched_s, Rs, X6):\n    """One season\'s games, each with its own generator ([SEED, season, game index]); the race\'s models batched across the games\' threads (none: the\n    race off). Returns the rows, declarations, counts, games not played, the race\'s log, batches, the drawn rows\' sources, each game\'s change log and the rows\n    from which each game is unsupported."""\n    games = [g for _, g in sched_s.iterrows()]; n_ = len(games)\n    MOD = getattr(Rs, "RACE_MODELS", None)\n    B = Batcher(None if MOD is None else dict(MOD, call4=getattr(Rs, "CALL4", None)), n_)   # aa1: the choice model batched with the race\'s parts\n    Rs.RACE = dict(eval=B.eval, run_cls=list(MOD["run"].classes_), stop_cls=list(MOD["stop"].classes_), t_cap=T_CAP) if MOD is not None else None\n    rows, logs, cnts, decs, sk, chg, uns = [None] * n_, [None] * n_, [None] * n_, [None] * n_, [None] * n_, [None] * n_, [None] * n_\n    def work(k, g):\n        try:\n            G = m.Game(g, Rs, X6, np.random.default_rng([m.SEED, s, k]), s)\n            rows[k] = G.run(); logs[k] = [(g["game_id"], s) + x for x in getattr(G, "race_log", [])]; cnts[k] = G.cnt; decs[k] = G.declared\n            chg[k] = list(getattr(G, "chg", [])); uns[k] = list(getattr(G, "unsup", []))\n        except record.GAP as ex_:\n            sk[k] = str(ex_)[:120]\n        finally:\n            B.done()\n    th_ = [threading.Thread(target=work, args=(k, g)) for k, g in enumerate(games)]\n    for t_ in th_: t_.start()\n    for t_ in th_: t_.join()\n    if B.err is not None: raise B.err\n    out, cnt, dec, SK, LG, SRC, CHG, UNS = [], Counter(), [], Counter(), [], [], {}, {}\n    for k in range(n_):\n        if rows[k] is not None:\n            out += rows[k]; cnt.update(cnts[k]); LG += logs[k]; CHG[games[k]["game_id"]] = chg[k]; UNS[games[k]["game_id"]] = uns[k]\n            SRC += [(r_["game_id"], r_["order_sequence"], r_["src"]) for r_ in rows[k] if r_.get("src")]\n        if decs[k]: dec.append((games[k]["game_id"], decs[k]))\n        if sk[k]: SK[sk[k]] += 1\n    return out, dec, cnt, SK, LG, B.batches, SRC, CHG, UNS\n\n\ndef cal_tests(p, obs, gidx, G, Wb):\n    dec = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False).to_numpy()\n    Sm = np.zeros((G, 10)); Nm = np.zeros((G, 10)); Pm = np.zeros((G, 10)); Om = np.zeros((G, 10))\n    np.add.at(Sm, (gidx, dec), obs - p); np.add.at(Nm, (gidx, dec), 1.0); np.add.at(Pm, (gidx, dec), p); np.add.at(Om, (gidx, dec), obs)\n    d = Sm.sum(0) / Nm.sum(0); db = (Wb @ Sm) / np.maximum(Wb @ Nm, 1e-12)\n    Vm = np.zeros(10); np.add.at(Vm, dec, p * (1 - p)); binom = 2 * np.sqrt(Vm) / Nm.sum(0)\n    se2 = np.maximum(2 * db.std(0, ddof=1), binom)\n    miss = np.abs(d) > se2; nullc = (np.abs(db - d) > se2).sum(1)\n    return [(k, Pm[:, k].sum() / Nm[:, k].sum(), Om[:, k].sum() / Nm[:, k].sum(), d[k], se2[k], bool(miss[k])) for k in range(10)], nullc\n\n\n\n# ---------------- the work each process does (the same functions run serially in this process for the byte comparison) ----------------\n_W = {}\n\n\ndef load_mod(text, name):\n    dd = tempfile.mkdtemp(); p = os.path.join(dd, name + ".py"); open(p, "w").write(text)\n    sp = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); shutil.rmtree(dd)\n    return m\n\n\ndef w_init(cwd, path, cfg, log, nthreads=None):\n    """A worker\'s start. nthreads: the threads each worker\'s numerical libraries (OpenMP for the trees, BLAS for the race) may use, capped by threadpoolctl\n    (a runtime setting only: no estimator, setting or check changes); None leaves them as the libraries choose (every core)."""\n    os.chdir(cwd); sys.path[:] = path\n    sys.stdout = sys.stderr = open(log, "a", buffering=1)   # the workers\' own printing goes to the run\'s log, not the terminal\n    configure(**cfg)\n    _W.clear()\n    if nthreads:   # set before the worker\'s OpenMP and BLAS libraries start (they read these once, when they load), then held by threadpoolctl once they are loaded\n        for v_ in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"): os.environ[v_] = str(int(nthreads))\n    from sklearn.ensemble import HistGradientBoostingClassifier   # loads the trees\' OpenMP library now, so the limit below reaches it\n    from sklearn.linear_model import LogisticRegression\n    if nthreads:\n        from threadpoolctl import threadpool_limits\n        _W["limits"] = threadpool_limits(limits=int(nthreads))\n\n\ndef _engine(text):\n    k = shs(text)\n    if _W.get(("e1n", k)) is None:\n        m_ = load_mod(text, "e1_v29aa_" + k)\n        for k_, v_ in ENGINE_CONF.items(): setattr(m_, k_, v_)   # v19 part 2: the engine\'s caller-set values (its landed form reads them)\n        _W[("e1n", k)] = m_\n    return _W[("e1n", k)]\n\n\ndef _tables(path):\n    if _W.get("tab_path") != path:\n        _W["tab"] = pickle.load(open(path, "rb")); _W["tab_path"] = path\n    return _W["tab"]\n\n\ndef w_play(text, s, sched_s, tab_path, models_bytes, x6, seasons, flags):\n    """One season\'s games played by the engine built from text (flags set on it), each game with its own generator; models_bytes None: the race off."""\n    m = _engine(text)\n    for k_, v_ in flags.items(): setattr(m, k_, v_)\n    TAB = _tables(tab_path)\n    Rs = m.Rates(s, [TAB[x][0] for x in seasons if x != s]); mb = pickle.loads(models_bytes) if models_bytes is not None else None\n    Rs.RACE_MODELS = None if mb is None else mb["race"]; Rs.CALL4 = None if mb is None else mb["call4"]; Rs.CALL4_SHARE = None if mb is None else mb.get("call4_share")   # aa1: the race\'s parts, the choice model and arm B\'s share table, or none (the floor)\n    t0 = time.time(); out = play_threaded(m, s, sched_s, Rs, x6)\n    return (m.text_frame(out[0]),) + out[1:] + (time.time() - t0,)\n\n\ndef eval_season(s, F, x6, shared=True, checks=True):\n    """One season\'s engine games: E2a\'s counts, the timeout moments and section 4\'s checks, from one parse (shared) or from separate parses."""\n    SIDE[0] = "engine"; FAILP.clear(); BACK.clear()\n    ctx = SharedParse() if shared else _Null()\n    with e1.OnSim({s: F}), ctx:\n        G_, PO_, ST_ = count_side([s])\n        dM = with_diff(e1.load(s)); TM = moments(dM)\n        sec4 = None\n        if checks:\n            w4, bad4 = e1.check_r4([s]); C1, left1, _ = e1.check_r1([s]); CK, FL, COST, _ = check_clock2([s]); PO, PB = e1.check_periods({s: F}, x6, [s]); SR = e1.season_rule_check([s], x6)\n            sec4 = dict(w4=w4, bad4=bad4, C1=C1, left1=left1, CK=CK, FL=FL, COST=COST, PO=PO, PB=PB, SR=SR)\n    return dict(G=G_, PO=PO_, ST=ST_, dM=dM, TM=TM, sec4=sec4, failp=list(FAILP), back=list(BACK))\n\n\nclass _Null:\n    def __enter__(self): return self\n    def __exit__(self, *a): pass\n\n\ndef w_eval(s, F, x6, shared=True, checks=True):\n    t0 = time.time(); r = eval_season(s, F, x6, shared, checks); r["sec"] = time.time() - t0; return r\n\n\ndef w_fit_stop(npz, s_out, cap):\n    z = np.load(npz, allow_pickle=True); X, y, ss = z["X"], z["y"], z["s"]; tr = ss != s_out\n    t0 = time.time()\n    try: m, inf = fit_part(X[tr], y[tr], ss[tr], cap)\n    except record.GAP as ex_: return s_out, None, str(ex_), time.time() - t0\n    return s_out, pickle.dumps(m), inf, time.time() - t0\n\n\ndef w_fit_race(npz, fs, key, shuffle=None):\n    z = np.load(npz, allow_pickle=True); X, y, ss = z["X"], z["y"], z["s"]; tr = np.isin(ss, fs)\n    t0 = time.time(); M = LRRace(X[tr], y[tr], shuffle)\n    return key, pickle.dumps(M), time.time() - t0\n\n\ndef w_fit_call4(npz, s_out, cap, shuffle=None):\n    """aa1: the fourth-down choice (go, field_goal, punt) fitted on every season but s_out (look-back; the rounds by fit_part\'s inner season, the trees as the\n    stopped part\'s). shuffle: the plant only, the yard line (column 0) permuted across the fitted rows before the fit (seed shuffle)."""\n    z = np.load(npz, allow_pickle=True); X, y, ss = z["X"].copy(), z["y"], z["s"]; tr = ss != s_out\n    if shuffle is not None: X[tr, 0] = X[tr, 0][np.random.default_rng(shuffle).permutation(int(tr.sum()))]\n    t0 = time.time()\n    try: m, inf = fit_part(X[tr], y[tr], ss[tr], cap)\n    except record.GAP as ex_: return s_out, None, str(ex_), time.time() - t0\n    return s_out, pickle.dumps(m), inf, time.time() - t0\n\n\ndef w_plant(name, text, s4, sched_s, tab_path, models_bytes, x6, seasons):\n    m = _engine(text); m.R1A = m.R1B = m.R1D = True; m.QE_BAND = 10\n    TAB = _tables(tab_path)\n    Rp = m.Rates(s4, [TAB[x][0] for x in seasons if x != s4]); mb = pickle.loads(models_bytes); Rp.RACE_MODELS = mb["race"]; Rp.CALL4 = mb["call4"]; Rp.CALL4_SHARE = mb.get("call4_share")\n    out_ = play_threaded(m, s4, sched_s, Rp, x6)\n    F = {s4: m.text_frame(out_[0])}   # every game (none removed for what it drew)\n    if not len(F[s4]): return name, None, "no game to plant into", "the plant"\n    with m.OnSim(F):\n        if name == "P1": _, lp, _ = m.check_r1([s4]); v = len(lp); ok = v > 0; what = "r1 unexplained"\n        elif name == "P2": w, _ = m.check_r4([s4]); v = w["OTHER"]; ok = v > 0; what = "r4 OTHER"\n        elif name == "P3": ck, _, _, _ = check_clock2([s4]); v = ck["STOP failed"]; ok = v > 0; what = "stopped clock failed (the check)"\n        else: sr = m.season_rule_check([s4], x6); v = sr[s4]["M1"]; ok = v != x6[s4]["touchback"]["value"]; what = f"R7 M1 against X6\'s {x6[s4][\'touchback\'][\'value\']}"\n    return name, ok, v, what\n\n')
TRANS_CAND = '"""transition.py - the one transition: possession, down, distance and yard line after one event (NFL rules: 3-8, 7-3, 11-3 to 11-6, 14-1-2, Rule 6).\nProduct code. The record\'s adapter (the rebuild of the record\'s states) and the engine both call after(); the record supplies an event\'s observed\nattributes (its row\'s columns), the engine its generated ones (its draws); neither computes the resulting state itself. A part whose inputs are missing\ncomes back UNKNOWN with its reason, never filled.\nLanded from chain e2b_v17_1725d9c82df1\'s shared library (lib_trans) as 96229f766489; tb_rules takes the Rule 11 Section 6 spots as an argument.\nE2b v18 c adds one case: a foul on a play that stands (stand(), the event\'s \'foul_stand\'): the play\'s result kept and the foul enforced on it, by the\nfamily rules.py\'s X2 lists name (rules.py 3d9b5a3b1985, each list citing its article) and the season\'s Dead Ball Foul article (rb: \'the down counts\',\n\'a taunting foul that occurs at any time\'), from the row\'s own columns (yards_gained, penalty_yards, penalty_team, first_down_penalty) and the spot its\ntext says the foul was enforced at; where those do not give a part, the parts are UNKNOWN with the reason. Every other answer is 96229f766489\'s.\nE2b v19 part 2: stand() reads the defense\'s foul with no award by rules.py\'s Item 5 Exceptions (DEF_NEXT the next down, DEF_SAME the same down); and the\nyards of a foul are computed here, by its article, from the spot it is enforced at (foul_yards: the book\'s distance, half the distance to the\noffender\'s goal where the book sets it; spot_foul_yards: pass interference by the defense, a spot foul), for the engine and the record check alike.\nE2b v19 r: a distance foul whose enforcement would carry the ball to or past the fouling team\'s goal line is placed half the distance from the\nenforcement spot to that goal (goal_half: the book\'s half-the-distance article, printed by line in each chain), in after_one and stand() alike, never\nUNKNOWN; pass interference by the defense takes the foul\'s depth (the record\'s penalty_yards on a wiped row) and, in the end zone, the 1-yard line or half\nthe distance from the previous spot, whichever is more beneficial (the season\'s book, printed by line).\nE2b v19 s, t: a fraction of a yard is a spot (s1, t1: kept exactly however many times half the distance halves it, never rounded; the engine writes the record\'s columns in the record\'s marking); the offense\'s\nunnecessary roughness on a play that stands, enforced at the play\'s end (the succeeding spot), is a dead ball foul by the season\'s Dead Ball Foul article:\n\'enforced from the succeeding spot, and the down counts\' (s3: OFF_DEAD_BOOK; a play whose result stands carries no accepted live-ball foul by the offense).\nIts known-right cases (FIXTURES, each true by the article it names, built by hand) and its plants (PLANTS, each must fail a case) live here;\ntest_transition.py runs them and proves this file byte-identical in its answers to the chain\'s copy."""\nimport math, re\nimport pandas as pd\nimport rules, record\nfrom rules import next_down, next_possession\n\n\ndef nanv(x):\n    return x is None or (not isinstance(x, str) and pd.isna(x))\n\n\ndef one_(x):\n    return (not nanv(x)) and x == 1\n\n\n# yl: yards to the goal line the team with the ball attacks (yardline_100); togo: yards to the line to gain; a kick to come has no down, distance or yard line.\nTPARTS = ("offense", "down", "distance", "yard line")\n\n\ndef _k(*v):\n    return all(not nanv(x) for x in v)\n\n\ndef series(team, yl, how):\n    """A new series (7-3-1): first and 10, or goal to go inside the 10."""\n    return dict(off=team, down=1, togo=min(10, yl), yl=yl, kick=False, kick_kind=None, new_series=True, unk=() if isinstance(team, str) else ("offense",), how=how)\n\n\ndef kick_to_come(receiver, how, kind="normal"):\n    return dict(off=receiver, down=None, togo=None, yl=None, kick=True, kick_kind=kind, new_series=False, unk=() if isinstance(receiver, str) else ("offense",), how=how)\n\n\ndef unknown(off, how, parts=("down", "distance", "yard line")):\n    return dict(off=off, down=None, togo=None, yl=None, kick=False, kick_kind=None, new_series=False,\n                unk=tuple(p for p in TPARTS if p in parts or (p == "offense" and not isinstance(off, str))), how=how)\n\n\ndef same(st, down, togo, yl, how):\n    return dict(off=st.get("off"), down=down, togo=togo, yl=yl, kick=False, kick_kind=None, new_series=False, unk=() if isinstance(st.get("off"), str) else ("offense",), how=how)\n\n\ndef tb_rules(season, x6cell, scrim_tb):\n    """A season\'s touchback spots, each from its pinned rule: a free kick\'s from X6 (rules.season_x6, the season\'s book; from 2024 the book names a second\n    spot for a kick that first lands in the landing zone), any other touchback\'s from Rule 11 Section 6 (scrim_tb: season -> (yard line, where it was read),\n    read by the caller from the season\'s book; a season missing reads unread)."""\n    v = lambda k: int(x6cell[k]["value"]) if (k in x6cell and str(x6cell[k]["value"]).isdigit()) else None\n    return dict(kick=v("touchback"), kick_lz=v("touchback_landing_zone"), two_spots="touchback_landing_zone" in x6cell, scrim=scrim_tb.get(season, (None, "unread"))[0])\n\n\ndef goal_half(yl, yd, by):\n    """A distance foul of yd yards (enforced yards, more than 0) from the offense\'s yard line yl, by \'offense\' or \'defense\', that would carry the ball to or\n    past the fouling team\'s goal line: the ball half the distance from yl to that goal (the book\'s half-the-distance article). None where yl is not on\n    the field or yd is not a distance toward the fouling team\'s goal (the spot stays UNKNOWN)."""\n    if not (_k(yl, yd) and by in ("offense", "defense") and 0 < yl < 100 and yd > 0): return None\n    if by == "offense": return yl + (100 - yl) / 2 if yl + yd >= 100 else None\n    return yl / 2 if yl - yd <= 0 else None\n\n\ndef int_end(y0, air, ret):\n    """An interception\'s dead-ball spot as the interceptors\' yard line: the catch at the passers\' yard line less air_yards, the return toward the passers\' goal."""\n    return 100.0 - (y0 - air) - ret if _k(y0, air, ret) else None\n\n\ndef punt_end(y0, kd, ret):\n    """A punt\'s dead-ball spot as the receivers\' yard line."""\n    return 100.0 - y0 + kd - ret if _k(y0, kd, ret) else None\n\n\ndef kick_end(y0, kd, ret):\n    """A kickoff\'s dead-ball spot as the receivers\' yard line (the kickoff row\'s yard line is the receivers\')."""\n    return y0 + kd - ret if _k(y0, kd, ret) else None\n\n\ndef _spot(team, end, how, miss):\n    return series(team, end, how) if (_k(end) and 0 < end < 100) else unknown(team, miss)\n\n\ndef second(r, ev):\n    """A combined event (v15 b): the play\'s text names a later recovery (its last \'RECOVERED by\') by a team other than the one the event\'s own columns give\n    the ball to: a second change of possession the row\'s yard columns do not place. The ball is that team\'s (the text\'s last recovery); the down, distance\n    and yard line are UNKNOWN. A kick to come, a turnover on downs (7-3-2a) and a result already UNKNOWN are not changed."""\n    pa = ev.get("poss_after")\n    if not isinstance(pa, str) or r["kick"] or r["unk"] or r["off"] == pa or r["how"].startswith("turnover on downs") or r["how"].startswith("a loss of down"): return r\n    return unknown(pa, "a second change of possession on the play (the text\'s last recovery): the spot is not in the row\'s yard columns (UNKNOWN)")\n\n\ndef after(st, ev, rb):\n    """The state after one event: the event\'s own result (one), then a second change of possession the text names (second)."""\n    return second(after_one(st, ev, rb), ev)\n\n\ndef after_one(st, ev, rb):\n    """The state after one event as its own columns give it. st: the state before it (off, dfn, down, togo, yl); ev: the event\'s attributes; rb: the\n    season\'s touchback spots (tb_rules). The order of the cases is the order of precedence."""\n    k = ev["kind"]; off = st.get("off"); dfn = st.get("dfn")\n    other = lambda t: dfn if t == off else (off if t == dfn else None)\n    if k == "period start":\n        return kick_to_come(ev.get("receiver"), "a period starts: a kickoff to come")\n    if k == "try":\n        recv = next_possession("try_or_field_goal", scorer=ev["team"], scored_on=ev["other"])[0]   # after a Try\n        return kick_to_come(recv, "Try: a kick to come")\n    if k == "kickoff":\n        recv, kicker = ev["recv"], ev["kicker"]\n        if ev.get("td"):\n            sc = ev.get("scorer") or recv\n            return kick_to_come(next_possession("try_or_field_goal", scorer=sc, scored_on=kicker if sc == recv else recv)[0], "kickoff returned for a touchdown: a Try and a kick to come")\n        if isinstance(ev.get("rec_by"), str) and ev["rec_by"] == kicker:\n            who = next_possession("kickers_recovery", team=kicker)[0]\n            return _spot(who, ev.get("end"), "a free kick recovered by the kickers: their first down (7-3-1(e))", "a free kick recovered by the kickers: the spot is not in the row (UNKNOWN)")\n        if ev.get("foul_unread"):\n            return unknown(recv, "a kickoff with a foul: the spot is not in the row (UNKNOWN)")\n        if ev.get("tb"):\n            if rb.get("two_spots"):\n                cond = ev.get("tb_cond"); spot = rb.get("kick") if cond == "in the air" else (rb.get("kick_lz") if cond == "landing zone" else None)\n                if spot is None:\n                    return unknown(recv, "kickoff touchback: the book names two spots and which one applies is not in the row (UNKNOWN)" if cond is None else "kickoff touchback: the spot unread from the book (UNKNOWN)")\n            else:\n                spot = rb.get("kick")\n                if spot is None: return unknown(recv, "kickoff touchback: X6\'s spot unread (UNKNOWN)")\n            return series(recv, 100 - spot, "kickoff touchback: X6\'s spot (the season\'s book)")\n        return _spot(recv, ev.get("end"), "kickoff: where the return ended", "kickoff: the return\'s spot is not in the row (UNKNOWN)")\n    # a snap: a scrimmage play, a punt or a field goal try\n    if ev.get("td"):\n        sc = ev.get("scorer") or off\n        return kick_to_come(next_possession("try_or_field_goal", scorer=sc, scored_on=other(sc))[0], "touchdown: a Try and a kick to come")\n    if k == "field_goal" and ev.get("made"):\n        recv = next_possession("try_or_field_goal", scorer=off, scored_on=dfn)[0]   # after a field goal\n        return kick_to_come(recv, "field goal: a kick to come")\n    if ev.get("safety"):\n        return kick_to_come(next_possession("safety", scorer=dfn, scored_on=off)[0], "safety: a free kick to come", "safety")\n    down, togo, yl = st.get("down"), st.get("togo"), st.get("yl")\n    if ev.get("offsetting_dead") and not rb.get("dead_counts", True):\n        return unknown(off, "fouls offsetting after the ball is dead: the season\'s book does not state that the down counts (UNKNOWN)")\n    if ev.get("offsetting"):   # v16 b: a double foul during a live ball (rb\'s double_replay: the season\'s book\'s article read and printed by the chain)\n        if not rb.get("double_replay", True): return unknown(off, "fouls offsetting during the down: the season\'s book\'s double-foul article not read (UNKNOWN)")\n        return same(st, down, togo, yl, "fouls offsetting during the down: the down replayed (3-8-4, the double-foul article)") if _k(down, togo, yl) else unknown(off, "fouls offsetting: the down\'s columns empty (UNKNOWN)")\n    # offsetting_dead (v16 b): fouls offsetting after the ball is dead leave the play\'s result standing (the Dead Ball Foul article: the down counts); the result follows\n    if k == "foul":\n        by, yd, oc = ev.get("by"), ev.get("yards"), ev.get("outcome")\n        if not (_k(yd, down, togo, yl) and by in ("offense", "defense") and isinstance(off, str)):\n            return unknown(off, "a foul: penalty_yards, penalty_team or the down\'s columns empty (UNKNOWN)")\n        why = rules.NEXT_DOWN[oc][1]\n        yl2 = yl + yd if by == "offense" else yl - yd; mv = yd\n        if not (0 < yl2 < 100):   # v19 r: the book\'s half-the-distance article where the ball would reach or pass the fouling team\'s goal line\n            yl2 = goal_half(yl, yd, by)\n            if yl2 is None: return unknown(off, "a foul: the enforced spot outside the field (UNKNOWN)")\n            mv = abs(yl2 - yl); why = why + "; half the distance to the goal (the book\'s half-the-distance article)"\n        if by == "offense":\n            tg2 = togo + mv\n            nd = next_down(down, oc)[0]\n            if nd > 4:   # 3-8-2: four downs (a loss of down on 4th down)\n                return series(dfn, 100 - yl2, "a loss of down on 4th down: turnover on downs (7-3-2a)")\n            return same(st, nd, tg2, yl2, f"a foul by the offense: {why}")\n        tg2 = togo - mv\n        if oc == "def_award" or tg2 <= 0:\n            return series(off, yl2, "a foul by the defense: a first down (7-3-1(b))")\n        return same(st, next_down(down, oc)[0], tg2, yl2, f"a foul by the defense: {why}")\n    if ev.get("foul_stand") is not None and k == "snap" and not ev.get("turnover"):   # v18 c: a foul on a play that stands\n        return stand(st, ev, rb)\n    if ev.get("foul_unread") and k in ("snap", "field_goal") and not ev.get("turnover"):\n        return unknown(off, "a foul on the play: its enforcement spot is not in the play\'s columns (UNKNOWN)")\n    if k == "snap" and ev.get("turnover"):\n        team = ev.get("turn_team") or dfn; what = ev["turnover"]\n        if ev.get("foul_unread"): return unknown(team, f"{what} with a foul: the spot is not in the row (UNKNOWN)")\n        if ev.get("turn_tb"):\n            sp = rb.get("scrim")\n            return series(team, 100 - sp, f"{what}, touchback: Rule 11 Section 6\'s spot (the season\'s book)") if sp else unknown(team, f"{what}, touchback: Rule 11 Section 6\'s spot unread (UNKNOWN)")\n        return _spot(team, ev.get("turn_end"), f"{what}: where the return ended", f"{what}: the spot is not in the row (UNKNOWN)")\n    if k == "punt":\n        recv = dfn\n        if isinstance(ev.get("rec_by"), str) and ev["rec_by"] == off:\n            return _spot(off, ev.get("end"), "a punt recovered by the kickers: their first down (7-3-1(d))", "a punt recovered by the kickers: the spot is not in the row (UNKNOWN)")\n        if ev.get("foul_unread"): return unknown(recv, "a punt with a foul: the spot is not in the row (UNKNOWN)")\n        if ev.get("tb"):\n            sp = rb.get("scrim")\n            return series(recv, 100 - sp, "punt, touchback: Rule 11 Section 6\'s spot (the season\'s book)") if sp else unknown(recv, "punt, touchback: Rule 11 Section 6\'s spot unread (UNKNOWN)")\n        return _spot(recv, ev.get("end"), "punt: where the return ended", "punt: the return\'s spot is not in the row (UNKNOWN)")\n    if k == "field_goal":\n        return _spot(dfn, ev.get("end"), "missed field goal: where the defense takes the ball", "missed field goal: the spot (11-4-3) is not in its columns (UNKNOWN)")\n    g = ev.get("gain")\n    if not (_k(g, down, togo, yl) and isinstance(off, str)):\n        return unknown(off, "the play\'s own columns empty (UNKNOWN)")\n    end = yl - g\n    if not (0 < end < 100):\n        return unknown(off, "the play\'s result off the field with no score marked (UNKNOWN)")\n    if end <= yl - togo:\n        return series(off, end, "a first down: the line to gain reached (7-3-1(a))")\n    nd = next_down(down, "next")[0]\n    if nd > 4:   # 3-8-2: four downs\n        return series(dfn, 100 - end, "turnover on downs (7-3-2a): 100 - the play\'s own result")\n    return same(st, nd, togo - g, end, "the next down (3-8-5): the yard line less the gain")\n\n\n# ---------------- v18 c: a foul on a play that stands ----------------\nENF_RX = re.compile(r"enforced at (?:the )?([A-Z]{2,3}) (\\d{1,2})\\b|enforced at (?:the )?(50)\\b")\n\n\ndef enforced_at(clause, holder):\n    """The spot one accepted foul\'s clause says it was enforced at (\'enforced at NYJ 35\'), as the yard line of the team holding the ball (holder);\n    None when the clause names no spot (one reading, shared by the record\'s adapter and the engine\'s pool)."""\n    m = ENF_RX.search(str(clause))\n    if not m or not isinstance(holder, str): return None\n    if m.group(3): return 50.0\n    return float(100 - int(m.group(2))) if m.group(1) == holder else float(int(m.group(2)))\n\n\nSTAND_PREFIX = "a foul on a play that stands"\nOFF_DEAD_BOOK = ("Unnecessary Roughness",)   # v19 s3: the offense\'s fouls rules.py\'s lists do not name, played by the season\'s Dead Ball Foul article where the\n                                             # play stands and the foul is enforced at its end (the succeeding spot): the down counts\n\n\ndef stand(st, ev, rb):\n    """The state after a scrimmage play that stands with one accepted foul on it (ev[\'foul_stand\']: by \'offense\'/\'defense\', yards (penalty_yards),\n    name (penalty_type), award (first_down_penalty), spot (enforced_at of the foul\'s clause)). The play\'s end is the yard line less yards_gained; the foul\n    is enforced from that end only where the text\'s own enforcement spot is that end (the two readings agree); a spot foul or a previous-spot enforcement\n    (the readings differ) is UNKNOWN. Then, by family:\n      the defense: a first down where first_down_penalty marks the award or the enforced spot reaches the line to gain (7-3-1(b), 14-1-2 Item 5); with\n        neither, the next down where the foul is a dead ball foul by the season\'s book (taunting, \'a taunting foul that occurs at any time\': the down\n        counts), else UNKNOWN (the row does not say whether the down counts or is replayed);\n      the offense: rules.LOSS_OF_DOWN, the next down (14-1-2 Item 2); rules.OFF_DURING, the down replayed from the enforced spot (14-1-2 Item 1,\n        3-8-4), a first down where the enforced spot still reaches the line; rules.OFF_AFTER, the down counts (the Dead Ball Foul article, read in the\n        season\'s book) from the succeeding spot, UNKNOWN after a down that made a first down (the article\'s Item 1 is not read); any other name UNKNOWN.\n    A loss of down past 4th down is a turnover on downs (7-3-2a). v19 r: an enforcement that would carry the ball to or past the fouling team\'s goal line\n    is placed half the distance from the play\'s end to that goal (goal_half)."""\n    fs = ev["foul_stand"]; off, dfn = st.get("off"), st.get("dfn"); down, togo, yl = st.get("down"), st.get("togo"), st.get("yl")\n    g, yd, by, name, sp = ev.get("gain"), fs.get("yards"), fs.get("by"), fs.get("name"), fs.get("spot")\n    P = STAND_PREFIX\n    if not (_k(g, down, togo, yl, yd) and isinstance(off, str) and by in ("offense", "defense")):\n        return unknown(off, f"{P}: penalty_yards, penalty_team or the play\'s own columns empty (UNKNOWN)")\n    end = yl - g; line = yl - togo\n    if not (0 < end < 100): return unknown(off, f"{P}: the play\'s end off the field (UNKNOWN)")\n    if not _k(sp): return unknown(off, f"{P}: its clause names no enforcement spot (UNKNOWN)")\n    if abs(sp - end) >= 0.5:\n        return unknown(off, f"{P}: the text\'s enforcement spot is not the play\'s end (a spot foul or the previous spot; UNKNOWN)")\n    yl2 = end - yd if by == "defense" else end + yd\n    if not (0 < yl2 < 100):   # v19 r: the book\'s half-the-distance article where the ball would reach or pass the fouling team\'s goal line\n        yl2 = goal_half(end, yd, by)\n        if yl2 is None: return unknown(off, f"{P}: the enforced spot outside the field (UNKNOWN)")\n    if by == "defense":\n        if fs.get("award") or yl2 <= line:\n            return series(off, yl2, f"{P}, the defense\'s: a first down (7-3-1(b), 14-1-2 Item 5)")\n        if name == "Taunting" and rb.get("taunt_dead") and rb.get("dead_counts", True):\n            nd = next_down(down, "next")[0]\n            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense\'s dead ball foul: the down counts, turnover on downs (7-3-2a)")\n            return same(st, nd, yl2 - line, yl2, f"{P}, the defense\'s dead ball foul (taunting): the down counts (the Dead Ball Foul article)")\n        if name in rules.DEF_NEXT:   # 14-1-2 Item 5 Exceptions (rules.py X2): the defense\'s foul with no award, the next down\n            nd = next_down(down, "next")[0]\n            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense\'s with no award (14-1-2 Item 5 Exceptions): the next down, turnover on downs (7-3-2a)")\n            return same(st, nd, yl2 - line, yl2, f"{P}, the defense\'s with no award (14-1-2 Item 5 Exceptions): the next down")\n        if name in rules.DEF_SAME:   # 14-1-2 Item 5 Exceptions (rules.py X2): the defense\'s foul with no award, the same down\n            return same(st, down, yl2 - line, yl2, f"{P}, the defense\'s with no award (14-1-2 Item 5 Exceptions): the same down")\n        return unknown(off, f"{P}, the defense\'s, no award and the line not reached: whether the down counts or is replayed is not in the row (UNKNOWN)")\n    if name in rules.LOSS_OF_DOWN:\n        nd = next_down(down, "loss_of_down")[0]\n        if nd > 4: return series(dfn, 100 - yl2, f"{P}, the offense\'s: a loss of down on 4th down, turnover on downs (14-1-2 Item 2, 7-3-2a)")\n        return same(st, nd, yl2 - line, yl2, f"{P}, the offense\'s: loss of down (14-1-2 Item 2)")\n    if name in rules.OFF_DURING:\n        if yl2 <= line: return series(off, yl2, f"{P}, the offense\'s during the down: the enforced spot reaches the line (7-3-1(a))")\n        return same(st, next_down(down, "off_during")[0], yl2 - line, yl2, f"{P}, the offense\'s during the down: the down replayed from the enforced spot (14-1-2 Item 1, 3-8-4)")\n    if name in rules.OFF_AFTER or name in OFF_DEAD_BOOK:   # v19 s3: OFF_DEAD_BOOK by the Dead Ball Foul article\n        if not rb.get("dead_counts", True): return unknown(off, f"{P}, the offense\'s after the down: the season\'s book does not state that the down counts (UNKNOWN)")\n        if end <= line: return unknown(off, f"{P}, the offense\'s after a down that made a first down: the Dead Ball Foul article\'s Item 1 not read (UNKNOWN)")\n        nd = next_down(down, "off_after")[0]\n        if nd > 4: return series(dfn, 100 - yl2, f"{P}, the offense\'s after the down: the down counts, turnover on downs (7-3-2a)")\n        return same(st, nd, yl2 - line, yl2, f"{P}, the offense\'s after the down: the down counts (the Dead Ball Foul article)")\n    return unknown(off, f"{P}, the offense\'s: its name is in none of rules.py\'s offense families (UNKNOWN)")\n\n\n# ---------------- v19 part 2: a foul\'s yards by its article, from the spot it is enforced at ----------------\ndef foul_yards(N, side, spot, rnd):\n    """The yards a foul moves the ball from its enforcement spot (the offense\'s yard line): N, its book\'s distance (\'Loss of N yards\'), or half the\n    distance to the fouling team\'s goal line where N is more than half (the book\'s half-the-distance sentence: the offense\'s goal 100 - spot behind it,\n    the defense\'s spot ahead); rnd: how the record marks a half that is not whole (\'floor\', \'ceil\' or \'exact\', measured by the caller). None where an\n    input is unread."""\n    if not (_k(N, spot) and side in ("offense", "defense") and rnd in ("floor", "ceil", "exact")): return None\n    half = (100 - spot) / 2 if side == "offense" else spot / 2\n    if N <= half: return float(N)\n    return float(math.floor(half)) if rnd == "floor" else (float(math.ceil(half)) if rnd == "ceil" else float(half))\n\n\ndef spot_foul_yards(depth, yl):\n    """Pass interference by the defense, a spot foul (\'first down for the offensive team at the spot of the foul\'): the spot is the foul\'s depth beyond the\n    line of scrimmage (the record\'s penalty_yards on a wiped row where the ball did not go to the 1, its uncensored rows); a spot in the end zone puts the\n    ball at the 1-yard line or half the distance to the goal from the previous spot, whichever is more beneficial (the season\'s book). None where the\n    depth is unread or not beyond the line."""\n    if not _k(depth, yl) or depth <= 0 or not (0 < yl < 100): return None\n    return float(max(yl - 1, yl / 2)) if depth >= yl else float(depth)\n\n\nYARD_CASES = [   # (case, the function, its inputs, what must come back)\n    ("offensive holding at the 30 (the offense\'s own 70): 10 yards", foul_yards, (10, "offense", 30.0, "floor"), 10.0),\n    ("offensive holding at the 95 (its own 5): half the distance, 2.5 marked down", foul_yards, (10, "offense", 95.0, "floor"), 2.0),\n    ("the defense\'s holding at the 6: 5 yards would leave 1, half the distance 3", foul_yards, (5, "defense", 6.0, "floor"), 3.0),\n    ("roughing the passer at the 20: 15 yards would pass half the distance, 10", foul_yards, (15, "defense", 20.0, "exact"), 10.0),\n    ("a half not whole, marked up", foul_yards, (15, "defense", 17.0, "ceil"), 9.0),\n    ("pass interference 25 yards downfield from the 60: the spot, 25 yards", spot_foul_yards, (25.0, 60.0), 25.0),\n    ("pass interference in the end zone from the 12: the ball at the 1, 11 yards", spot_foul_yards, (15.0, 12.0), 11.0),\n    ("pass interference with no depth read: unread", spot_foul_yards, (float("nan"), 40.0), None),\n    ("pass interference in the end zone from the 1 (inside the 2): half the distance, 0.5 (more beneficial than the 1)", spot_foul_yards, (12.0, 1.0), 0.5),\n    ("v19 s1: a 5-yard foul against the offense on its own 3: half the distance, 1.5, never rounded", foul_yards, (5, "offense", 97.0, "exact"), 1.5),\n]\n\n\ndef run_yard_cases(fns=None):\n    """Each yards case against the functions (or replacements by name): (cases, failures with what came back)."""\n    bad = []\n    for name, f, a, want in YARD_CASES:\n        f = (fns or {}).get(f.__name__, f); got = f(*a)\n        if got != want: bad.append((name, want, got))\n    return len(YARD_CASES), bad\n\n\nYARD_PLANTS = {"half the distance never applied": ("foul_yards", lambda N, side, spot, rnd: float(N) if _k(N) else None),\n               "pass interference in the end zone not brought to the 1": ("spot_foul_yards", lambda depth, yl: float(depth) if _k(depth, yl) and depth > 0 else None),\n               "v19 s1: the half yard rounded down": ("foul_yards", lambda N, side, spot, rnd: (lambda v: None if v is None else float(math.floor(v)))(foul_yards(N, side, spot, "exact")))}\n\n\n# known-right cases, true by the rules they cite (built by hand, independent of the record and of the engine); each (case, state before, event, season\'s\n# spots, the state that must come back: off, down, togo, yl, kick, the UNKNOWN parts)\n_RB = dict(kick=25, kick_lz=None, two_spots=False, scrim=20)\n_RB2 = dict(kick=30, kick_lz=20, two_spots=True, scrim=20)\n_S0 = lambda dn, tg, yl: dict(off="AAA", dfn="BBB", down=dn, togo=tg, yl=yl)\nFIXTURES = [\n    ("3-8-5 the next down: 1st and 10 at the 75, 4 yards", _S0(1, 10, 75), dict(kind="snap", gain=4), _RB, ("AAA", 2, 6, 71, False, ())),\n    ("7-3-1(a) a first down: 3rd and 2 at the 40, 3 yards", _S0(3, 2, 40), dict(kind="snap", gain=3), _RB, ("AAA", 1, 10, 37, False, ())),\n    ("7-3-1 goal to go: 3rd and 5 at the 9, 5 yards", _S0(3, 5, 9), dict(kind="snap", gain=5), _RB, ("AAA", 1, 4, 4, False, ())),\n    ("7-3-2a turnover on downs: 4th and 2 at the 40, 1 yard", _S0(4, 2, 40), dict(kind="snap", gain=1), _RB, ("BBB", 1, 10, 61, False, ())),\n    ("11-3-4 a touchdown: the scored-upon team receives", _S0(2, 8, 8), dict(kind="snap", gain=8, td=True, scorer="AAA"), _RB, ("BBB", None, None, None, True, ())),\n    ("11-5-1 a safety: the scoring team receives the free kick", _S0(2, 8, 98), dict(kind="snap", gain=-3, safety=True), _RB, ("BBB", None, None, None, True, ())),\n    ("11-4-6 a field goal: the scored-upon team receives", _S0(4, 6, 20), dict(kind="field_goal", made=True), _RB, ("BBB", None, None, None, True, ())),\n    ("11-6 a punt touchback: the receivers at their 20", _S0(4, 9, 45), dict(kind="punt", tb=True), _RB, ("BBB", 1, 10, 80, False, ())),\n    ("11-6 an interception touchback: the interceptors at their 20", _S0(2, 10, 30), dict(kind="snap", turnover="interception", turn_tb=True), _RB, ("BBB", 1, 10, 80, False, ())),\n    ("6 a kickoff touchback, one spot (the 25)", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", tb=True), _RB, ("BBB", 1, 10, 75, False, ())),\n    ("6 a kickoff touchback, two spots, in the air (the 30)", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", tb=True, tb_cond="in the air"), _RB2, ("BBB", 1, 10, 70, False, ())),\n    ("6 a kickoff touchback, two spots, which one unread", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", tb=True), _RB2, ("BBB", None, None, None, False, ("down", "distance", "yard line"))),\n    ("a kickoff return: the receivers\' 35 + 65 - 25", {}, dict(kind="kickoff", recv="BBB", kicker="AAA", end=kick_end(35.0, 65.0, 25.0)), _RB, ("BBB", 1, 10, 75.0, False, ())),\n    ("14-4-9 a false start: 2nd and 7 at the 60, 5 yards", _S0(2, 7, 60), dict(kind="foul", by="offense", yards=5, outcome="presnap_offense"), _RB, ("AAA", 2, 12, 65, False, ())),\n    ("14-1-2 Item 5 Exceptions, the line reached: 3rd and 3 at the 50, offside 5", _S0(3, 3, 50), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 1, 10, 45, False, ())),\n    ("14-1-2 Item 5 an award: 3rd and 9 at the 50, holding 5", _S0(3, 9, 50), dict(kind="foul", by="defense", yards=5, outcome="def_award"), _RB, ("AAA", 1, 10, 45, False, ())),\n    ("14-1-2 Item 2 loss of down: 3rd and 5 at the 50, grounding 10", _S0(3, 5, 50), dict(kind="foul", by="offense", yards=10, outcome="loss_of_down"), _RB, ("AAA", 4, 15, 60, False, ())),\n    ("14-1-2 Item 2 loss of down on 4th: turnover on downs", _S0(4, 5, 50), dict(kind="foul", by="offense", yards=10, outcome="loss_of_down"), _RB, ("BBB", 1, 10, 40, False, ())),\n    ("3-8-4 fouls offsetting: the down replayed", _S0(2, 6, 44), dict(kind="snap", gain=12, offsetting=True), _RB, ("AAA", 2, 6, 44, False, ())),\n    ("v16 b the Dead Ball Foul article: fouls offsetting after the ball is dead, the play stands: 2nd and 6 at the 44, 12 yards", _S0(2, 6, 44),\n     dict(kind="snap", gain=12, offsetting_dead=True), _RB, ("AAA", 1, 10, 32, False, ())),\n    ("v16 b fouls offsetting after a punt is dead: the punt stands (a touchback, Rule 11 Section 6)", _S0(4, 3, 42), dict(kind="punt", tb=True, offsetting_dead=True), _RB,\n     ("BBB", 1, 10, 80, False, ())),\n    ("v16 b the season\'s book not stating that the down counts: UNKNOWN", _S0(2, 6, 44), dict(kind="snap", gain=12, offsetting_dead=True), dict(_RB, dead_counts=False),\n     ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    ("v16 b the season\'s double-foul article not read: a live-ball double foul UNKNOWN", _S0(2, 6, 44), dict(kind="foul", offsetting=True), dict(_RB, double_replay=False),\n     ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    ("3-8-4 fouls offsetting on a down whose play they wiped: 3rd and 7 at the 35, replayed", _S0(3, 7, 35), dict(kind="foul", offsetting=True), _RB, ("AAA", 3, 7, 35, False, ())),\n    ("14-1-2 Item 1, 3-8-4 the offense\'s foul during the play: 2nd and 4 at the 30, 10 yards", _S0(2, 4, 30), dict(kind="foul", by="offense", yards=10, outcome="off_during"), _RB, ("AAA", 2, 14, 40, False, ())),\n    ("14-1-2 Item 5, 7-3-1(b) the defense\'s foul during the play with the award: 3rd and 8 at the 50, 23 yards", _S0(3, 8, 50), dict(kind="foul", by="defense", yards=23, outcome="def_award"), _RB, ("AAA", 1, 10, 27, False, ())),\n    ("14-1-2 Item 5 Exceptions, short of the line: 2nd and 9 at the 40, 5 yards on the play", _S0(2, 9, 40), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 2, 4, 35, False, ())),\n    ("a foul during the play, the enforced spot past the offense\'s goal line: half the distance, 96 to 98 (v19 r2: v17\'s case read UNKNOWN)", _S0(1, 10, 96), dict(kind="foul", by="offense", yards=10, outcome="off_during"), _RB, ("AAA", 1, 12.0, 98.0, False, ())),\n    ("a fumble lost, its spot not in the row", _S0(1, 10, 60), dict(kind="snap", gain=3, turnover="fumble", turn_team="BBB"), _RB, ("BBB", None, None, None, False, ("down", "distance", "yard line"))),\n    ("a foul on the play, its enforcement unread", _S0(1, 10, 60), dict(kind="snap", gain=3, foul_unread=True), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    ("11-6 a punt touchback with Rule 11-6 unread", _S0(4, 9, 45), dict(kind="punt", tb=True), dict(_RB, scrim=None), ("BBB", None, None, None, False, ("down", "distance", "yard line"))),\n    ("v15 b a combined event: an interception, the interceptor\'s fumble recovered by the passers", _S0(2, 10, 40), dict(kind="snap", turnover="interception", turn_team="BBB",\n     turn_end=55.0, poss_after="AAA"), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    ("v15 b a combined event: a punt return fumbled, recovered by the kickers (7-3-1(d))", _S0(4, 9, 45), dict(kind="punt", end=70.0, poss_after="AAA"), _RB,\n     ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    ("v15 b the text\'s last recovery by the team the columns give the ball to: unchanged", _S0(2, 10, 40), dict(kind="snap", turnover="fumble", turn_team="BBB", turn_end=62.0,\n     poss_after="BBB"), _RB, ("BBB", 1, 10, 62.0, False, ())),\n    ("7-3-2a a turnover on downs stands whoever recovers a fumble on the play", _S0(4, 5, 40), dict(kind="snap", gain=2, poss_after="AAA"), _RB, ("BBB", 1, 10, 62, False, ())),\n    # v18 c: a foul on a play that stands\n    ("7-3-1(b) the defense\'s face mask after a 6-yard run, 1st and 10 at the 70: 15 yards from the end, a first down", _S0(1, 10, 70),\n     dict(kind="snap", gain=6, foul_stand=dict(by="defense", yards=15, name="Face Mask", award=True, spot=64.0)), _RB, ("AAA", 1, 10, 49, False, ())),\n    ("the Dead Ball Foul article: the offense\'s taunting after a 4-yard gain, 2nd and 10 at the 60: the down counts", _S0(2, 10, 60),\n     dict(kind="snap", gain=4, foul_stand=dict(by="offense", yards=15, name="Taunting", award=False, spot=56.0)), dict(_RB, dead_counts=True), ("AAA", 3, 21, 71, False, ())),\n    ("14-1-2 Item 1, 3-8-4 offensive holding at the end of a 12-yard run, 2nd and 15 at the 50: the down replayed from the enforced spot", _S0(2, 15, 50),\n     dict(kind="snap", gain=12, foul_stand=dict(by="offense", yards=10, name="Offensive Holding", award=False, spot=38.0)), _RB, ("AAA", 2, 13, 48, False, ())),\n    ("7-3-1(a) offensive holding at the end of a 30-yard run, 2nd and 5 at the 60: the enforced spot still past the line, a first down", _S0(2, 5, 60),\n     dict(kind="snap", gain=30, foul_stand=dict(by="offense", yards=10, name="Offensive Holding", award=False, spot=30.0)), _RB, ("AAA", 1, 10, 40, False, ())),\n    ("14-1-2 Item 2 intentional grounding, 3rd and 7 at the 40, enforced at the previous spot: the next down", _S0(3, 7, 40),\n     dict(kind="snap", gain=0, foul_stand=dict(by="offense", yards=10, name="Intentional Grounding", award=False, spot=40.0)), _RB, ("AAA", 4, 17, 50, False, ())),\n    ("a spot foul: the text\'s enforcement spot not the play\'s end, UNKNOWN", _S0(1, 10, 70),\n     dict(kind="snap", gain=20, foul_stand=dict(by="offense", yards=10, name="Offensive Holding", award=False, spot=60.0)), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    ("the defense\'s foul with no award and the line not reached: UNKNOWN (counts or replayed not in the row)", _S0(3, 12, 50),\n     dict(kind="snap", gain=2, foul_stand=dict(by="defense", yards=5, name="Illegal Use of Hands", award=False, spot=48.0)), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    ("the offense\'s dead ball foul after a down that made a first down: Item 1 not read, UNKNOWN", _S0(3, 2, 40),\n     dict(kind="snap", gain=5, foul_stand=dict(by="offense", yards=15, name="Unsportsmanlike Conduct", award=False, spot=35.0)), _RB, ("AAA", None, None, None, False, ("down", "distance", "yard line"))),\n    # v19 part 2\n    ("14-1-2 Item 5 Exceptions: the defense\'s delay of game on a play that stands, 1st and 10 at the 92, 2 yards: the next down", _S0(1, 10, 92),\n     dict(kind="snap", gain=2, foul_stand=dict(by="defense", yards=5, name="Defensive Delay of Game", award=False, spot=90.0)), _RB, ("AAA", 2, 3, 85, False, ())),\n    ("14-1-2 Item 5 Exceptions: too many men on a play that stands, 3rd and 9 at the 50, 1 yard: the same down", _S0(3, 9, 50),\n     dict(kind="snap", gain=1, foul_stand=dict(by="defense", yards=5, name="Defensive Too Many Men on Field", award=False, spot=49.0)), _RB, ("AAA", 3, 3, 44, False, ())),\n    ("pass interference in the end zone from the 10 (a spot foul): first down at the 1, goal to go", _S0(3, 8, 10),\n     dict(kind="foul", by="defense", yards=9, outcome="def_award"), _RB, ("AAA", 1, 1, 1, False, ())),\n    # v19 r2: the book\'s half-the-distance article where the enforcement would carry the ball past a goal line\n    ("the book\'s half-the-distance article: a 15-yard foul against the offense on its own 10, 2nd and 10: the ball on its own 5, the down replayed",\n     _S0(2, 10, 90), dict(kind="foul", by="offense", yards=15, outcome="off_during"), _RB, ("AAA", 2, 15.0, 95.0, False, ())),\n    ("the book\'s half-the-distance article: the defense\'s 5-yard foul at its own 1, 3rd and goal: the ball at the half-yard line, the same down",\n     _S0(3, 1, 1), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 3, 0.5, 0.5, False, ())),\n    # v19 s1: a half-yard spot kept exactly; s3: the offense\'s unnecessary roughness on a play that stands, the Dead Ball Foul article\n    ("v19 s1 the book\'s half-the-distance article: a 5-yard foul against the offense on its own 3, 2nd and 10: the ball on its own 1.5, the down replayed from there",\n     _S0(2, 10, 97), dict(kind="foul", by="offense", yards=5, outcome="off_during"), _RB, ("AAA", 2, 11.5, 98.5, False, ())),\n    ("v19 t1 half the distance again: the defense\'s 5-yard foul at its own 1.5, 1st and goal: the ball at the 0.75, the same down",\n     _S0(1, 1.5, 1.5), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 1, 0.75, 0.75, False, ())),\n    ("v19 t1 and again: the defense\'s 5-yard foul at its own 0.75, 1st and goal: the ball at the 0.375, the same down",\n     _S0(1, 0.75, 0.75), dict(kind="foul", by="defense", yards=5, outcome="def_exception"), _RB, ("AAA", 1, 0.375, 0.375, False, ())),\n    ("v19 t1 the offense\'s own 1.5: a 5-yard foul against the offense on its own 1.5, 2nd and 10: the ball on its own 0.75, the down replayed",\n     _S0(2, 10, 98.5), dict(kind="foul", by="offense", yards=5, outcome="off_during"), _RB, ("AAA", 2, 10.75, 99.25, False, ())),\n    ("v19 s3 the Dead Ball Foul article: the offense\'s unnecessary roughness at the end of a 4-yard gain, 2nd and 10 at the 60, enforced at the end: the down counts",\n     _S0(2, 10, 60), dict(kind="snap", gain=4, foul_stand=dict(by="offense", yards=15, name="Unnecessary Roughness", award=False, spot=56.0)), dict(_RB, dead_counts=True),\n     ("AAA", 3, 21, 71, False, ())),\n]\n\n\ndef run_fixtures(fn):\n    """Each known-right case against a transition function: (cases, failures with what came back)."""\n    bad = []\n    for name, st, ev, rb, want in FIXTURES:\n        o = fn(st, ev, rb); got = (o["off"], o["down"], o["togo"], o["yl"], o["kick"], tuple(o["unk"]))\n        if got != want: bad.append((name, want, got))\n    return len(FIXTURES), bad\n\n\ndef planted_stand(old, new):\n    """A changed copy of stand() (v18 c\'s plant): stand() and after_one() run from a copy of this module\'s names with the one line replaced."""\n    import inspect\n    src = inspect.getsource(stand)\n    if src.count(old) != 1: raise record.GAP(f"a plant\'s anchor is in stand() {src.count(old)} times")\n    ns = dict(globals()); exec(src.replace(old, new), ns); exec(inspect.getsource(after_one), ns)\n    return lambda st, ev, rb: second(ns["after_one"](st, ev, rb), ev)\n\n\ndef planted(src, old, new):\n    """A changed copy of the transition (a plant): its source with one line replaced, run in a copy of this module\'s names."""\n    if src.count(old) != 1: raise record.GAP(f"a plant\'s anchor is in the transition {src.count(old)} times")\n    ns = dict(globals()); exec(src.replace(old, new), ns)\n    return lambda st, ev, rb: second(ns["after_one"](st, ev, rb), ev)\n\n\n# each plant: one line of after_one replaced; each must make a known-right case fail (a plant that fails none means the cases cannot see that line)\nPLANTS = {"the next down not counted (3-8-5)": (\'    nd = next_down(down, "next")[0]\\n    if nd > 4:   # 3-8-2: four downs\', \'    nd = down\\n    if nd > 4:   # 3-8-2: four downs\'),\n          "the yards copied whole past the goal line (no half-the-distance article; v19 r2)": ("            yl2 = goal_half(yl, yd, by)\\n", "            yl2 = None\\n"),\n          "v19 t1: a state that holds only half yards (the spot rounded to the nearest half)": ("            yl2 = goal_half(yl, yd, by)\\n", "            yl2 = goal_half(yl, yd, by); yl2 = None if yl2 is None else round(2 * yl2) / 2\\n"),\n          "v19 s1: the half yard rounded (the ball put on a whole yard)": ("            yl2 = goal_half(yl, yd, by)\\n", "            yl2 = goal_half(yl, yd, by); yl2 = None if yl2 is None else float(round(yl2))\\n"),\n          "a punt touchback at the 25 (Rule 11 Section 6 says the 20)": (\'return series(recv, 100 - sp, "punt, touchback\', \'return series(recv, 100 - 25, "punt, touchback\')}\n# v18 c\'s plant, in stand(): the defense\'s foul enforced toward the defense (the yards added, not taken)\nSTAND_PLANTS = {"the defense\'s foul on a play that stands enforced the wrong way": (\'    yl2 = end - yd if by == "defense" else end + yd\\n\', \'    yl2 = end + yd if by == "defense" else end + yd\\n\'),\n                "v19 s3: the offense\'s unnecessary roughness not read by the Dead Ball Foul article": ("    if name in rules.OFF_AFTER or name in OFF_DEAD_BOOK:", "    if name in rules.OFF_AFTER:"),\n                "14-1-2 Item 5 Exceptions\' next down read as the same down": (\'            nd = next_down(down, "next")[0]\\n            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense\\\'s with no award\',\n                                                                               \'            nd = down\\n            if nd > 4: return series(dfn, 100 - yl2, f"{P}, the defense\\\'s with no award\')}\n'   # v19 y: transition.py as landed (fcca26b4997f), carried unchanged, played from the run's own folder and landed when its checks pass
TEST_CAND = '"""test_transition.py - transition.py\'s own test (v18: the foul on a play that stands added). Each check names, before it runs, the output that fails\nit; exit 0 only when every check passes.\n1. the known-right cases (transition.FIXTURES, each true by the article it names; 35 before v18, 8 for v18 c, 3 for v19 part 2, 2 for v19 r, 2 for v19 s, 3 for v19 t; v17\'s case\n   \'the enforced spot off the field\' now reads half the distance by v19 r2) and the yards cases (YARD_CASES: a foul\'s yards by its article from its spot):\n   FAILS if any case comes back other than it must.\n2. the plants (transition.PLANTS, STAND_PLANTS, YARD_PLANTS): FAILS if a plant makes no case fail (the cases could not see that line).\n3. byte-identical to the chain\'s copy (chain e2b_v17_1725d9c82df1\'s library, lib sha c1357bc133c2): the same known-right cases, and a fixed grid of\n   generated events (seeded) through after(), after_one() and second(), and tb_rules over the seasons\' X6 cells: FAILS on any answer that differs,\n   or if a planted change to the first-down line (7-3-1(a)) differs on no event (the comparison blind). The events carry no foul on a play that stands:\n   every answer outside v18 c\'s case must be the chain\'s, except v19 r2\'s: where the chain\'s answer is \'the enforced spot outside the field (UNKNOWN)\'\n   for a distance foul toward the fouling team\'s goal, this file\'s must be half the distance from the spot to that goal (counted apart, each checked).\n4. v18 c on generated events with a foul on a play that stands: every answer either UNKNOWN with its reason, or the ball at the play\'s end less\n   (the defense\'s foul) or plus (the offense\'s) penalty_yards (half the distance to the fouling team\'s goal where that would reach or pass it, v19 r2),\n   the offense the same team or, after a loss of down past 4th down, the other. FAILS on any other."""\nimport ast, hashlib, importlib, inspect, os, random, sys, tempfile, time\nimport rules\nT0 = time.time()\nsh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]\nCHAIN, CHAIN_SHA, LIB_SHA = "e2b_v17_1725d9c82df1.py", "1725d9c82df1", "c1357bc133c2"\nFAILED = []\n\n\ndef check(name, ok, detail):\n    print(f"  [{time.time() - T0:6.1f} s] {name}: {detail} -> {\'PASS\' if ok else \'FAIL\'}")\n    if not ok: FAILED.append(name)\n\n\ndef chain_lib():\n    """The chain\'s shared library, taken from the chain file\'s text (the one string that opens it), written to a temporary folder and imported."""\n    if not os.path.exists(CHAIN) or sh(CHAIN) != CHAIN_SHA: sys.exit(f"STOPPED: {CHAIN} is missing or not sha {CHAIN_SHA}; nothing compared")\n    hits = [n.value for n in ast.walk(ast.parse(open(CHAIN).read())) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith(\'"""E2b v17\')]\n    if len(hits) != 1 or hashlib.sha256(hits[0].encode()).hexdigest()[:12] != LIB_SHA: sys.exit(f"STOPPED: the chain\'s library is not one string of sha {LIB_SHA}")\n    d_ = tempfile.mkdtemp(); open(os.path.join(d_, "e2b_v17_lib.py"), "w").write(hits[0]); sys.path.insert(1, d_)\n    return importlib.import_module("e2b_v17_lib")\n\n\nprint(f"test_transition.py {sh(\'test_transition.py\')} | transition.py {sh(\'transition.py\')}")\nprint("EXPECT: 1. 53 known-right cases and 10 yards cases, 0 fail | 2. each of 11 plants fails at least 1 case | 3. 0 answers differ from the chain\'s copy outside v19 r2\'s case (its 35 cases but the one v19 r2 changes, 200,000 generated events, the seasons\' tb_rules); every v19 r2 answer half the distance; the comparison\'s plant differs on at least 1 event | 4. 0 of 100,000 stand answers off the rule")\nimport transition as T\n\nprint("1. the known-right cases (FAILS: any case returning other than it must)")\nn_, bad_ = T.run_fixtures(T.after)\nfor b_ in bad_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")\ncheck("known-right cases", n_ == 53 and not bad_, f"{n_} cases, {len(bad_)} failed")\nny_, bady_ = T.run_yard_cases()\nfor b_ in bady_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")\ncheck("yards cases", ny_ == 10 and not bady_, f"{ny_} cases, {len(bady_)} failed")\n\nprint("2. the plants (FAILS: a plant that makes no case fail)")\nSRC = inspect.getsource(T.after_one)\nfor nm_, (o_, w_) in T.PLANTS.items():\n    _, bp_ = T.run_fixtures(T.planted(SRC, o_, w_))\n    check(f"plant, {nm_}", bool(bp_), f"{len(bp_)} of {n_} cases fail")\nfor nm_, (o_, w_) in T.STAND_PLANTS.items():\n    _, bp_ = T.run_fixtures(T.planted_stand(o_, w_))\n    check(f"plant, {nm_}", bool(bp_), f"{len(bp_)} of {n_} cases fail")\nfor nm_, (fn_, f_) in T.YARD_PLANTS.items():\n    _, bp_ = T.run_yard_cases({fn_: f_})\n    check(f"plant, {nm_}", bool(bp_), f"{len(bp_)} of {ny_} yards cases fail")\n\nprint("3. byte-identical to the chain\'s copy (FAILS: any answer that differs)")\nL = chain_lib()\nR2_CASE = "a foul during the play, the enforced spot off the field"   # v17\'s case v19 r2 changes (UNKNOWN -> half the distance)\ndcase_ = [L.FIXTURES[k_][0] for k_ in range(min(35, len(L.FIXTURES))) if repr(T.FIXTURES[k_]) != repr(L.FIXTURES[k_])]\ncheck("the first 35 known-right cases are the chain\'s, but the one v19 r2 changes", len(L.FIXTURES) == 35 and dcase_ == [R2_CASE], f"35 here, {len(L.FIXTURES)} in the chain; differing {dcase_}")\nrng = random.Random(0)\nTEAMS = ["AAA", "BBB", None]; NUMS = [None, -12.0, -3.0, 0.0, 1.0, 2.0, 4.0, 5.0, 9.0, 10.0, 15.0, 20.0, 35.0, 50.0, 62.0, 75.0, 95.0, 99.0, 100.0, 120.0]\nRBS = [T._RB, T._RB2, dict(T._RB, scrim=None), dict(T._RB, dead_counts=False), dict(T._RB, double_replay=False), dict(T._RB2, kick=None, kick_lz=None), {}]\nKINDS = ["period start", "try", "kickoff", "snap", "punt", "field_goal", "foul"]\nOUTCOMES = list(__import__("rules").NEXT_DOWN)\npick = lambda xs: xs[rng.randrange(len(xs))]\n\n\ndef gen():\n    st = dict(off=pick(TEAMS), dfn=pick(TEAMS), down=pick([None, 1, 2, 3, 4]), togo=pick(NUMS), yl=pick(NUMS))\n    ev = dict(kind=pick(KINDS))\n    for k_, xs in (("receiver", TEAMS), ("team", TEAMS), ("other", TEAMS), ("recv", TEAMS), ("kicker", TEAMS), ("scorer", TEAMS), ("rec_by", TEAMS), ("turn_team", TEAMS),\n                   ("poss_after", TEAMS), ("by", ["offense", "defense", None]), ("outcome", OUTCOMES), ("tb_cond", [None, "in the air", "landing zone"]),\n                   ("turnover", [None, None, "interception", "fumble"]), ("gain", NUMS), ("yards", NUMS), ("end", NUMS), ("turn_end", NUMS)):\n        if rng.random() < 0.5: ev[k_] = pick(xs)\n    for k_ in ("td", "made", "safety", "offsetting", "offsetting_dead", "foul_unread", "tb", "turn_tb"):\n        if rng.random() < 0.25: ev[k_] = rng.random() < 0.5\n    return st, ev, pick(RBS)\n\n\ndef ans(f, *a):\n    try: return repr(f(*a))\n    except Exception as ex_: return f"raised {type(ex_).__name__}: {ex_}"\n\n\nOUTSIDE = "a foul: the enforced spot outside the field (UNKNOWN)"\n\n\ndef r2_ok(st, ev, a_new, a_old):\n    """v19 r2\'s change, checked from the article by hand: the chain\'s answer UNKNOWN for the enforced spot outside the field, a distance foul (yards > 0)\n    toward the fouling team\'s goal from a spot on the field, and this file\'s answer the ball half the distance to that goal (or 100 less it after a\n    turnover on downs)."""\n    if OUTSIDE not in a_old or ev.get("kind") != "foul" or ev.get("offsetting") or ev.get("by") not in ("offense", "defense"): return False\n    yl, yd = st.get("yl"), ev.get("yards")\n    if yl is None or yd is None or not (0 < yl < 100) or yd <= 0: return False\n    want = yl + (100 - yl) / 2 if ev["by"] == "offense" else yl / 2\n    return f"\'yl\': {want!r}" in a_new or f"\'yl\': {100 - want!r}" in a_new\n\n\nN = 200_000; diff_ = []; pdiff_ = 0; r2_n = 0\nP_AFTER = T.planted(SRC, "    if end <= yl - togo:", "    if end < yl - togo:")   # the comparison\'s own plant: a first down needing one yard more (7-3-1(a))\nfor _ in range(N):\n    st, ev, rb = gen()\n    pdiff_ += ans(P_AFTER, st, ev, rb) != ans(L.after, st, ev, rb)\n    a1n, a1o = ans(T.after_one, st, ev, rb), ans(L.after_one, st, ev, rb)\n    r2_ = a1n != a1o and r2_ok(st, ev, a1n, a1o)   # v19 r2\'s change in after_one; after() is second() of it (a later recovery the text names still applies)\n    for nm_ in ("after", "after_one"):\n        a_new, a_old = (a1n, a1o) if nm_ == "after_one" else (ans(T.after, st, ev, rb), ans(L.after, st, ev, rb))\n        if a_new != a_old:\n            if r2_ and (nm_ == "after_one" or a_new == ans(T.second, T.after_one(st, ev, rb), ev)): r2_n += 1\n            else: diff_.append((nm_, st, ev, rb, a_new, a_old))\n    r_ = T.after_one(st, ev, rb) if not ans(T.after_one, st, ev, rb).startswith("raised") else None\n    if r_ is not None and ans(T.second, r_, ev) != ans(L.second, r_, ev): diff_.append(("second", st, ev, rb))\nfor x_ in diff_[:5]: print(f"    DIFFERS: {x_}")\ncheck("generated events through after, after_one and second", not diff_, f"{N} events (seed 0), {len(diff_)} answers differ outside v19 r2\'s case")\ncheck("v19 r2\'s answers (the chain\'s UNKNOWN past a goal line), each half the distance by the article", r2_n > 0, f"{r2_n} answers changed, each checked against the article")\ncheck("the comparison sees a planted change (a first down needing one yard more than 7-3-1(a) says)", pdiff_ > 0, f"{pdiff_} of {N} events differ from the chain\'s copy")\nimport e1\nX6 = e1.x6_rows(); SC = {s: (20, "Rule 11 Section 6") for s in list(X6)[:3]}\nL.configure(SCRIM_TB=SC)\ntdiff = [s for s in X6 if repr(T.tb_rules(s, X6[s], SC)) != repr(L.tb_rules(s, X6[s]))]\ncheck("tb_rules over the seasons\' X6 cells (e1.x6_rows), Rule 11 Section 6 read for some seasons and not others", not tdiff, f"{len(X6)} seasons, {len(tdiff)} differ")\n\nprint("4. v18 c on generated events with a foul on a play that stands (FAILS: an answer neither UNKNOWN nor at the play\'s end -/+ penalty_yards)")\nNAMES = list(rules.OFF_DURING + rules.LOSS_OF_DOWN + rules.OFF_AFTER + rules.DEF_AWARD) + ["Illegal Use of Hands", "Neutral Zone Infraction", "Unnecessary Roughness"]\noff_rule = []; n_res = n_unk = 0\nfor _ in range(100_000):\n    dn_ = rng.choice([1, 2, 3, 4]); yl_ = float(rng.randrange(2, 99)); tg_ = float(min(yl_, rng.choice([1, 3, 5, 10, 15, 22]))); g_ = float(rng.randrange(-10, 40))\n    by_ = rng.choice(["offense", "defense"]); yd_ = float(rng.choice([5, 10, 15])); end_ = yl_ - g_\n    sp_ = end_ if rng.random() < 0.8 else end_ + rng.choice([-5.0, 5.0])\n    st = dict(off="AAA", dfn="BBB", down=dn_, togo=tg_, yl=yl_)\n    ev = dict(kind="snap", gain=g_, foul_stand=dict(by=by_, yards=yd_, name=rng.choice(NAMES), award=rng.random() < 0.5, spot=sp_))\n    rb = dict(T._RB, dead_counts=rng.random() < 0.8, taunt_dead=rng.random() < 0.5)\n    o = T.after(st, ev, rb)\n    if o["unk"]:\n        n_unk += 1\n        if not o["how"].startswith(T.STAND_PREFIX): off_rule.append(("UNKNOWN without the reason", st, ev, o["how"]))\n        continue\n    n_res += 1; want_ = end_ - yd_ if by_ == "defense" else end_ + yd_\n    if not (0 < want_ < 100) and 0 < end_ < 100: want_ = end_ / 2 if by_ == "defense" else end_ + (100 - end_) / 2   # v19 r2: the book\'s half-the-distance article\n    yl_o = o["yl"] if o["off"] == "AAA" else 100 - o["yl"]\n    if abs(yl_o - want_) > 1e-9 or o["off"] not in ("AAA", "BBB") or (o["off"] == "BBB" and not o["how"].endswith("(7-3-2a)") and "7-3-2a" not in o["how"]):\n        off_rule.append(("placed off the rule", st, ev, o))\nfor x_ in off_rule[:5]: print(f"    OFF THE RULE: {x_}")\ncheck("a foul on a play that stands, generated", not off_rule and n_res > 0, f"100000 events: resolved {n_res}, UNKNOWN {n_unk}, off the rule {len(off_rule)}")\n\nprint(f"TEST transition.py {sh(\'transition.py\')}: {\'PASS\' if not FAILED else \'FAIL\'} | failed: {FAILED if FAILED else \'none\'} | {time.time() - T0:.0f} s")\nsys.exit(1 if FAILED else 0)\n'   # its test, written beside it on a landing
open(os.path.join(LIB_DIR, "transition.py"), "w").write(TRANS_CAND)
print(f"the candidate transition.py {shs(TRANS_CAND)} (the project's {sh('transition.py')}) | its test {shs(TEST_CAND)}")
sys.path.insert(0, LIB_DIR)
import e2b_v29_lib as L
from e2b_v29_lib import *
MODCHK = []   # y: (what, every module it names, the ones not allowed): every worker map's results and every reused working table, printed in the report
MOD_OK = {"e2b_v29_lib", "_loss", "numpy", "sklearn", "pandas", "pyarrow", "builtins", "collections"}   # y: what the product's model files ask for to load (out/engine/: race_*.pkl _loss, numpy, sklearn; tables.pkl and sched.pkl builtins, collections, numpy, pandas, pyarrow), and this chain's library


class _ModScan(pickle.Unpickler):
    """Reads a packed object (pickled bytes) recording every module it names; a module outside MOD_OK is recorded and never imported (the read stops there)."""
    def __init__(self, b): super().__init__(io.BytesIO(b)); self.mods = set()
    def find_class(self, mod, name):
        self.mods.add(mod.split(".")[0])
        if mod.split(".")[0] in MOD_OK: return super().find_class(mod, name)
        raise pickle.UnpicklingError(f"a module not allowed: {mod}")


def named_modules(obj, depth=0, out=None):
    """Every module (by its top name) an object names: its own type, the containers inside it, and the objects packed inside it as pickled bytes, read
    through _ModScan, to any depth of packing (a packed object's own contents read in turn)."""
    out = set() if out is None else out
    if depth > 16: return out
    out.add(type(obj).__module__.split(".")[0])
    if isinstance(obj, (bytes, bytearray)) and len(obj) > 2 and obj[:1] == b"\x80":
        sc_ = _ModScan(bytes(obj)); inner_ = None
        try: inner_ = sc_.load()
        except Exception: pass
        out |= sc_.mods
        if inner_ is not None: named_modules(inner_, depth + 1, out)
    elif isinstance(obj, dict):
        for k_, v_ in obj.items(): named_modules(k_, depth + 1, out); named_modules(v_, depth + 1, out)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for v_ in obj: named_modules(v_, depth + 1, out)
    return out


def mod_check(obj, what):
    """y: the modules an object names, printed by the report; one outside MOD_OK stops the run."""
    all_ = named_modules(obj); bad_ = sorted(m_ for m_ in all_ if m_ not in MOD_OK); MODCHK.append((what, sorted(all_), bad_))
    if bad_: stop(f"{what} names {bad_}: not this chain's library ({LIB_MOD}) or a module the product's model files load; nothing further run")


_PLANT_IN = b"\x80\x02ce2b_v24_lib\nLRRace\nq\x00)\x81q\x01."   # an object of the earlier chain's library, packed by hand (its module is never imported)
_PLANT = pickle.dumps({"race": [(2023, pickle.dumps({"model": _PLANT_IN}), 1.0)]})   # packed inside another packed object
MOD_PLANT = named_modules(_PLANT)
print(f"y: the module check's plant (an e2b_v24_lib object packed two deep): modules named {sorted(MOD_PLANT)} -> "
      f"{'REFUSED as it must (e2b_v24_lib found)' if 'e2b_v24_lib' in MOD_PLANT else 'NOT REFUSED'}")
if "e2b_v24_lib" not in MOD_PLANT: stop("the module check's plant was not refused: the check cannot fail; nothing run")


def within(a, b):
    """y0 (a): two measures (mean, 2SE[, rows]) side by side: (difference, 2SE of the difference, verdict). The verdict is None (NOT MEASURED) when a side has
    fewer than 2 rows or a mean or 2SE that is not a number; else True when the difference is within its 2SE. Replaces the library's within for every check in
    this chain (the library's own is not called by the library)."""
    d = b[0] - a[0]; s = float(np.sqrt(a[1] ** 2 + b[1] ** 2))
    few = any(len(x_) > 2 and x_[2] is not None and not (isinstance(x_[2], float) and np.isnan(x_[2])) and x_[2] < 2 for x_ in (a, b))
    if few or any(isinstance(v_, (float, np.floating)) and np.isnan(v_) for v_ in (a[0], b[0], a[1], b[1])) or np.isnan(s): return d, s, None
    return d, s, bool(abs(d) <= s)


def wd(ok):
    """y0 (a): a check's word."""
    return "NOT MEASURED" if ok is None else ("within" if ok else "APART")


def hv(ok):
    """y0 (a): a prediction's word."""
    return "NOT MEASURED" if ok is None else ("HELD" if ok else "NOT HELD")


LIB_MOD = "e2b_v29_lib"   # the module name every object this run's library defines is pickled under: part of every working table's key (y: w's fits, the same text under e2b_v24_lib, were reused and could not be read)
LIBSHA = shs(sh(LIB_FILE) + "|" + LIB_MOD + "|" + shs(TRANS_CAND) + "|" + sh("clock_check.py"))   # every working table keyed by the library and the product files it calls
print(f"the shared library e2b_v29_lib.py sha {sh(LIB_FILE)} | transition.py {sh('transition.py')} | clock_check.py {sh('clock_check.py')} | the key {LIBSHA} | transition as imported {L.T.__file__}")
if sh(LIB_FILE) != "6712d594fcd2": stop(f"(f) the written library is {sh(LIB_FILE)}, not 6712d594fcd2 (the text the header names); nothing run")
section("start: pins and targets")


E1_TXT = open("e1.py").read()   # the engine is built in memory from e1.py as it is on disk (pinned)

WORK = os.path.join(tempfile.mkdtemp(), "work") if (FIXTURE or COLD) else "out/work"   # n: --cold reuses nothing
os.makedirs(WORK, exist_ok=True)
CACHE_LOG = []


def cache_get(name, key, build):
    """A working table reused from a saved file when its key (the shas of every input it was built from) matches; else built in this run and saved."""
    p = os.path.join(WORK, f"{name}_{key}.pkl")
    if os.path.exists(p):
        out = pickle.load(open(p, "rb")); CACHE_LOG.append((name, key, "reused", sh(p)))
        mod_check(out, f"the working table {p} (reused)")   # y: an object from an earlier chain's library is never used
        return out
    t_ = time.time(); out = build()
    for f_ in os.listdir(WORK):
        if f_.startswith(name + "_") and f_.endswith(".pkl"): os.remove(os.path.join(WORK, f_))   # no older version kept
    pickle.dump(out, open(p, "wb")); CACHE_LOG.append((name, key, f"built ({time.time() - t_:.0f} s)", sh(p))); return out


RAWPINS = shs(json.dumps(record.raw_pins(), sort_keys=True))
NEW_SHA = sh("rules.py")   # the fixed readers, on disk (pinned above)
KEY_BASE = shs("|".join(sh(p) for p in ("e1.py", "r1.py", "r2.py", "r4.py", "record.py", "contract.py", "rules.py")) + "|" + RAWPINS + ("|fixture " + sh("fixtures/real_games.csv.gz") if FIXTURE else ""))


from rules import clock_class, PRESNAP_OFFENSE
TABLE_VERSION = "interval-table v18"
PIN_FILE = "rules/play_clock_pins.tsv"; WPIN_FILE = "rules/warning_pins.tsv"
SQ = lambda s: re.sub(r"\s+", "", str(s))
ART_RX = re.compile(r"^(ARTICLE|Article)\s+\d+")
SEC_RX = re.compile(r"^(SECTION|Section)\s+\d+|^(RULE|Rule)\s+\d+")
RULE_LINE = re.compile(r"^(RULE|Rule)\s+(\d+)\b")
def book_lines_raw(f_):
    from pypdf import PdfReader
    if f_.endswith(".pdf"): return [l.strip() for pg in PdfReader(f_).pages for l in (pg.extract_text() or "").split("\n")]
    return [l.strip() for l in re.sub(r"<[^>]+>", "\n", open(f_, encoding="utf-8", errors="replace").read()).split("\n") if l.strip()]


def book_lines(f_):
    return cache_get("book_" + os.path.basename(f_).replace(".", "_"), sh(f_), lambda: book_lines_raw(f_))


class Book:
    def __init__(self, f_):
        self.f = f_; self.L = book_lines(f_); q = [SQ(l) for l in self.L]
        self.start = np.cumsum([0] + [len(x) for x in q[:-1]]); self.txt = "".join(q)
        self.art = [k for k, l in enumerate(self.L) if ART_RX.match(l)]; self.sec = [k for k, l in enumerate(self.L) if SEC_RX.match(l)]
        self.sec_heads = sorted(set(self.sec) | {k for k in range(len(self.L) - 1) if self.L[k] == "SE" and self.L[k + 1].startswith("CTION")})

    def line_of(self, pos):
        return int(np.searchsorted(self.start, pos, side="right")) - 1

    def heading(self, h):
        hq = SQ(h); out = []; p = self.txt.find(hq)
        while p >= 0:
            k = self.line_of(p)
            if self.start[k] == p: out.append(k)
            p = self.txt.find(hq, p + 1)
        return out

    def follows(self, k, quote, ends):
        nxt = next((j for j in ends if j > k), len(self.L))
        a = self.start[k]; b = self.start[nxt] if nxt < len(self.L) else len(self.txt)
        p = self.txt.find(SQ(quote), a, b)
        return (p >= 0), (self.line_of(p) if p >= 0 else None), nxt


def check_pin(p, B):
    if not os.path.exists(p["file"]) or B is None or B.f != p["file"]: return False, "missing source"
    H = B.heading(p["article_heading"])
    if not H: return False, "the article heading is not a heading in this book"
    hits = [k for k in H if B.follows(k, p["quote"], B.art)[0]]
    if not hits: return False, "the quote does not follow the article heading"
    m = re.search(r"(\d+)\s*-?\s*second", p["article_heading"], re.I)
    if not m or int(m.group(1)) != int(p["value"]): return False, f"the value {p['value']} is not the article heading's"
    if SQ(p["start"]) not in SQ(p["quote"]): return False, "the start words are not in the quote"
    R_ = B.heading(p["reset_article_heading"])
    if not R_: return False, "the reset article heading is not a heading in this book"
    m2 = re.search(r"(\d+)\s*-?\s*second", p["reset_article_heading"], re.I)
    if not m2 or int(m2.group(1)) != int(p["reset_value"]): return False, f"the reset value {p['reset_value']} is not the reset article heading's"
    for rq in p["reset_quotes"].split(" || "):
        if not any(B.follows(k, rq, B.art)[0] for k in R_): return False, f"the reset condition '{rq}' does not follow the reset article heading"
    return True, f"pin holds (article heading at line {hits[0] + 1}, quote at line {B.follows(hits[0], p['quote'], B.art)[1] + 1})"


def check_wpin(p, B):
    """g: the warning's section pinned: refuses unless the section heading begins a line of that book, sits under a 'Rule 3' line, and the quote follows it
    before the next section heading."""
    if not os.path.exists(p["file"]) or B is None or B.f != p["file"]: return False, "missing source"
    H = B.heading(p["section_heading"])
    if not H: return False, "the section heading is not a heading in this book"
    if str(int(p["section"])) not in re.findall(r"\d+", p["section_heading"]): return False, "the section number is not the heading's"
    for k in H:
        rl = next((RULE_LINE.match(B.L[z]).group(2) for z in range(k, -1, -1) if RULE_LINE.match(B.L[z])), None)
        ok_, at_, _ = B.follows(k, p["quote"], B.sec_heads)
        if ok_ and rl == p["rule"]: return True, f"pin holds (section heading at line {k + 1}, under Rule {rl}, quote at line {at_ + 1})"
    return False, "the quote does not follow the section heading under its rule"


READY_QUOTE = {"2020": "A Dead Ball is Ready for Play while the 40-second Play Clock is running when the ball", "2021": "A Dead Ball is Ready for Play while the 40-second Play Clock is running when the ball",
               "2023": "A dead ball is ready for play while the 40 -second play clock is running when the ball is", "2024": "A dead ball is ready for play while the 40-second play clock is running when the ball is",
               "2025": "A dead ball is ready for play while the 40-second play clock is running when the ball is placed down by an official",
               "2026": "A dead ball is ready for play while the 40-second play clock is running when the ball is"}
ARTICLES = [("4-5-3 injury before the warning", r"INJURYTIMEOUTS?PRIORTOTWO-?MINUTEWARNING"), ("4-5-4 injury after the warning", r"INJURYTIMEOUTS?AFTERTWO-?MINUTEWARNING"),
            ("15-5-1 the clock after a review", r"RESETTINGGAMECLOCK"), ("15-5-2 the 10-second runoff after a review", r"10-SECONDRUNOFF")]
SECONLY_RX = re.compile(r"^(SECTION|Section)\s+\d+")
REVIEW_RX = re.compile(r"(?:Replay Official reviewed|challenged)(?P<what>[^.]*?)(?:,\s*and\s+the\s+play\s+was|and\s+the\s+play\s+was|,\s*and\s+the\s+ruling\s+on\s+the\s+field|the\s+ruling\s+on\s+the\s+field)\s+(?P<out>REVERSED|Upheld|upheld|UPHELD|stands|STANDS|confirmed|CONFIRMED)\.?", re.S)
REVIEW_ANY = re.compile(r"Replay Official reviewed|challenged", re.I)
CHAL_RX = re.compile(r"\b([A-Z]{2,3}) challenged")
INJ_RX = re.compile(r"injur", re.I); REF_RX = re.compile(r"(referee|official)'?s? time", re.I)
INJ_TEAM_RX = re.compile(r"\b([A-Z]{2,3})-\d+-[^ ]+ was injured")
PEN_RX = re.compile(r"\bPENALTY\b", re.I)
EXTRA_V15 = ["penalty_yards", "home_timeouts_remaining", "away_timeouts_remaining", "home_opening_kickoff", "timeout_team", "kick_distance", "return_yards", "air_yards"]
EXTRA_OPT = ["yrdln", "return_team", "fumbled_1_team", "fumble_recovery_2_team"]   # b's traces read these where the season's file has them (the header decides)
SPOT_RX = re.compile(r"\b(?:to|at)\s+(?:the\s+)?([A-Z]{2,3})\s+(\d{1,2})\b|\b(?:to|at)\s+(?:the\s+)?(50)\b")
REC_RX = re.compile(r"RECOVERED by ([A-Z]{2,3})")


def spot_yl(team_side, n, holder):
    """A field spot ('NYJ 25'; '50') as yardline_100 for the team holding the ball: its own side N is 100 - N, the other side N is N."""
    if n == 50: return 50.0
    if not (isinstance(team_side, str) and isinstance(holder, str)): return None
    return float(100 - n) if team_side == holder else float(n)


def text_spot(text):
    """The last field spot the play's text names before any PENALTY clause ('to NYJ 25', 'at the 50'): (side, yard) or None (b's test D; never an input)."""
    t_ = str(text); p_ = re.search(r"\bPENALTY\b", t_, re.I); t_ = t_[: p_.start()] if p_ else t_
    ms = list(SPOT_RX.finditer(t_))
    if not ms: return None
    m = ms[-1]
    return (None, 50) if m.group(3) else (m.group(1), int(m.group(2)))


def yrdln_yl(v, holder):
    """The record's yrdln column ('NYJ 25', '50', 'MID 50') as yardline_100 for the team holding the ball (b's test D; never an input)."""
    if not isinstance(v, str) or not v.strip(): return None
    m = re.fullmatch(r"\s*(?:([A-Z]{2,3})|MID(?:FIELD)?)?\s*(\d{1,2})\s*", v)
    if not m: return None
    return spot_yl(m.group(1), int(m.group(2)), holder)


REB_COLS = ["act", "play_type", "q", "posteam", "defteam", "home", "away", "down", "ydstogo", "yardline_100", "yards_gained", "first_down", "touchdown", "td_team",
            "interception", "fumble_lost", "fumble_recovery_1_team", "field_goal_result", "safety", "penalty", "own_kickoff_recovery", "home_after",
            "away_after", "home_opening_kickoff", "touchback", "kick_distance", "return_yards", "air_yards", "penalty_yards", "penalty_team", "penalty_type", "first_down_penalty", "ptext", "rev_rev"]
PARTS = ("offense", "down", "distance", "yard line", "score")



OWN_HOW = ["a first down: the line to gain reached (7-3-1(a))", "the next down (3-8-5): the yard line less the gain"]


def foul_read(flag, txt):
    """v15 b, repair A1: a row's foul read from both readings, the flag and the text's clauses (r4.foul_clauses: 'PENALTY on TEAM, ...', accepted unless
    'declined' or 'offsetting' is in the clause): 'accepted' (an accepted clause), 'offsetting' (offsetting clauses only), 'disagree' (the flag set and the
    text naming no foul, or a clause accepted with the flag unset), 'none'. Neither reading overrides the other (v11 c)."""
    cl = r4.foul_clauses(txt); acc = [c_ for c_ in cl if c_[1]]
    if acc: return "accepted" if flag == 1 else "disagree"
    if cl and re.search(r"offsetting", txt, re.I): return "offsetting"
    if flag == 1 and not cl: return "disagree"
    return "none"


def rebuild(G, rb, repairs=True):
    """c, the record's adapter: each row's observed attributes passed to the one transition (L.after) and nothing computed here about the result; the
    state after each row, each part known or UNKNOWN, and how. G: one game's columns (REB_COLS) as lists, in play order; rb: the season's touchback spots
    (L.tb_rules, with the season's double-foul and dead-ball readings). repairs: v15 b's A1 (the foul read from both readings) and B1 (the text's last
    recovery passed to the transition); v16 b's B2 (a play row's offsetting fouls after the ball is dead: the play stands) and f's F1 (a REVERSED ruling's
    touchback, and its spot, read after the review phrase); v18 c's C1 (a foul on a play that stands passed to the transition's stand(), its one
accepted clause read for its enforcement spot); False reads as v15's first chain did (the repairs' regression evidence). Also returns, for each scrimmage play the transition decided from its gain, the first down it
    derived (checked against the row's own first_down column, which the transition never reads), and the repairs that changed the row's event."""
    n_ = len(G["act"]); qprev = None
    v = lambda x: None if (x is None or (isinstance(x, float) and np.isnan(x))) else float(x)
    s_ = lambda x: x if isinstance(x, str) else None
    nn = lambda x: np.nan if x is None else float(x)
    cur = dict(off=None, down=None, togo=None, yl=None, kick=True, unk=("offense",), how="before the game")
    S_off, S_dn, S_tg, S_yl, S_kick, S_how, S_diff, Q_st, S_unk, S_fd, S_rep = [], [], [], [], [], [], [], [], [], [], []
    hk = G["home_opening_kickoff"][0] if n_ else np.nan
    first_recv = (G["away"][0] if hk == 1 else (G["home"][0] if hk == 0 else None)) if n_ else None
    other = lambda t: (G["away"][0] if t == G["home"][0] else G["home"][0]) if isinstance(t, str) else None
    fin = lambda *x: all(not (y is None or (isinstance(y, float) and np.isnan(y))) for y in x)
    for i in range(n_):
        a = G["act"][i]; q_ = G["q"][i]
        if q_ != qprev:
            if q_ in (1, 3):
                recv = first_recv if q_ == 1 else other(first_recv)
                cur = L.after({}, dict(kind="period start", receiver=recv), rb)
                cur["how"] = "quarter start: a kickoff to come (home_opening_kickoff)" if recv else "quarter start: the receiving team UNKNOWN (home_opening_kickoff empty)"
            qprev = q_
            Q_st.append((cur["off"], nn(cur["down"]), nn(cur["togo"]), nn(cur["yl"]), cur["kick"], "+".join(cur["unk"])))
        else:
            Q_st.append(None)
        pos = s_(G["posteam"][i]); dfn = s_(G["defteam"][i]); txt = str(G["ptext"][i])
        st0 = dict(off=pos, dfn=dfn, down=v(G["down"][i]), togo=v(G["ydstogo"][i]), yl=v(G["yardline_100"][i]))
        y0, kd, ret, air = v(G["yardline_100"][i]), v(G["kick_distance"][i]), v(G["return_yards"][i]), v(G["air_yards"][i])
        offs = bool(re.search(r"offsetting", txt, re.I)); declined = bool(re.search(r"declined", txt, re.I))
        pen0 = G["penalty"][i] == 1 and not declined; rep_ = []
        if repairs and a in ("snap", "kickoff"):
            fr_ = foul_read(G["penalty"][i], txt); pen = fr_ in ("accepted", "disagree", "offsetting"); offs = fr_ == "offsetting"
            if pen != pen0 or (pen and offs != bool(re.search(r"offsetting", txt, re.I))): rep_.append("A1")
        else:
            pen = pen0
        rl_ = REC_RX.findall(txt); pa_ = rl_[-1] if (repairs and rl_) else None
        fd = np.nan
        if a == "snap":
            pt = G["play_type"][i]; kind = "punt" if pt == "punt" else ("field_goal" if pt == "field_goal" else "snap")
            itc = G["interception"][i] == 1; fum = G["fumble_lost"][i] == 1; rec = s_(G["fumble_recovery_1_team"][i]); tb = G["touchback"][i] == 1
            ev = dict(kind=kind, td=G["touchdown"][i] == 1, scorer=s_(G["td_team"][i]) or pos, made=G["field_goal_result"][i] == "made", safety=G["safety"][i] == 1,
                      foul_unread=bool(pen and not offs), gain=v(G["yards_gained"][i]))
            acc_c = [c_ for c_ in r4.foul_clauses(txt) if c_[1]]
            if repairs and kind == "snap" and pen and not offs and fr_ == "accepted" and len(acc_c) == 1 and not (itc or fum):   # v18 c, repair C1: the foul on a play that stands
                ptm = s_(G["penalty_team"][i])
                ev.update(foul_unread=False, foul_stand=dict(by=None if (ptm is None or pos is None) else ("offense" if ptm == pos else "defense"), yards=v(G["penalty_yards"][i]),
                                                             name=s_(G["penalty_type"][i]), award=G["first_down_penalty"][i] == 1,
                                                             spot=L.enforced_at(txt[acc_c[0][2]:acc_c[0][3]], pos)))
                rep_.append("C1")
            if pen and offs:   # v16 b, repair B2: a play row (not a no-play) whose fouls offset: the record shows the down counted, the fouls after the ball was dead
                ev["offsetting_dead" if repairs else "offsetting"] = True
                if repairs: rep_.append("B2")
            rv_ = repairs and G.get("rev_rev", [0] * n_)[i] == 1
            tb_t = bool(re.search(r"\btouchback\b", txt, re.I)) if rv_ else bool(tb)   # v16 f, repair F1: a REVERSED ruling's touchback read after the review phrase
            if rv_ and tb_t != bool(tb): rep_.append("F1")
            ts_ = text_spot(txt) if (rv_ and tb_t != bool(tb) and not tb_t) else None   # the final ruling's own spot (the text after the phrase), else UNKNOWN
            if kind == "snap" and (itc or fum):
                tend_ = (spot_yl(ts_[0], ts_[1], rec if (fum and rec) else dfn) if ts_ else None) if "F1" in rep_ else (L.int_end(y0, air, ret) if itc else None)
                ev.update(turnover="interception" if itc else "fumble", turn_team=rec if (fum and rec) else dfn, turn_tb=tb_t, turn_end=tend_)
            if kind == "punt":
                pend_ = (spot_yl(ts_[0], ts_[1], dfn) if ts_ else None) if "F1" in rep_ else L.punt_end(y0, kd, ret)
                ev.update(rec_by=rec, tb=tb_t, end=None if (rec is not None and rec == pos) else pend_)
            ev["poss_after"] = pa_; c1_ = L.after_one(st0, ev, rb); cur = L.second(c1_, ev)
            if cur is not c1_: rep_.append("B1")
            if cur["how"] in OWN_HOW or cur["how"].startswith("turnover on downs"):
                fd = 1.0 if (cur["new_series"] and cur["off"] == pos) else 0.0
        elif a == "foul":
            if offs:
                ev = dict(kind="foul", offsetting=True)
            else:
                ptm = s_(G["penalty_team"][i]); by = None if (ptm is None or pos is None) else ("offense" if ptm == pos else "defense")
                oc = ("off_during" if e1.has_play(txt) else "presnap_offense") if by == "offense" else ("def_award" if G["first_down_penalty"][i] == 1 else "def_exception")
                ev = dict(kind="foul", by=by, yards=v(G["penalty_yards"][i]), outcome=oc)
            cur = L.after(st0, ev, rb)
        elif a == "kickoff":
            rec_by = dfn if G["own_kickoff_recovery"][i] == 1 else None
            rv_ = repairs and G.get("rev_rev", [0] * n_)[i] == 1; tbf_ = G["touchback"][i] == 1
            tb_t = bool(re.search(r"\btouchback\b", txt, re.I)) if rv_ else tbf_
            if rv_ and tb_t != tbf_: rep_.append("F1")
            ts_ = text_spot(txt) if ("F1" in rep_ and not tb_t) else None
            kend_ = (spot_yl(ts_[0], ts_[1], pos) if ts_ else None) if "F1" in rep_ else L.kick_end(y0, kd, ret)
            ev = dict(kind="kickoff", recv=pos, kicker=dfn, td=G["touchdown"][i] == 1, scorer=s_(G["td_team"][i]) or pos, rec_by=rec_by, foul_unread=bool(pen),
                      tb=tb_t, tb_cond=None, end=None if rec_by else kend_, poss_after=pa_)
            c1_ = L.after_one({}, ev, rb); cur = L.second(c1_, ev)
            if cur is not c1_: rep_.append("B1")
        elif a == "try":
            if pos is not None: cur = L.after({}, dict(kind="try", team=pos, other=other(pos)), rb)
            else: cur = dict(cur, how="Try: its team unread (the state carried)")
        else:
            cur = dict(cur, how="carried")
        ha, aa = G["home_after"][i], G["away_after"][i]
        u_ = set(cur["unk"])
        if not fin(ha, aa): u_.add("score")
        off = cur["off"]
        S_off.append(off); S_dn.append(nn(cur["down"])); S_tg.append(nn(cur["togo"])); S_yl.append(nn(cur["yl"])); S_kick.append(bool(cur["kick"])); S_how.append(cur["how"])
        S_diff.append((ha - aa) if off == G["home"][0] else ((aa - ha) if off == G["away"][0] else np.nan))
        S_unk.append("+".join(p_ for p_ in PARTS if p_ in u_ and not (cur["kick"] and p_ in ("down", "distance", "yard line"))))
        S_fd.append(fd); S_rep.append("+".join(rep_))
    return S_off, S_dn, S_tg, S_yl, S_kick, S_how, S_diff, Q_st, S_unk, S_fd, S_rep


# Rule 11 Section 6 Article 3 (Ball Next In Play), hand-written from each book's printed text (read 2026-10-27): the spot for a touchback that is not a free kick
TB11_QUOTES = {
    "2020": "After a touchback, the team that has been awarded the touchback next snaps the ball at its 20-yard line",
    "2021": "After a touchback, the team that has been awarded the touchback next snaps the ball at its 20-yard line",
    "2023": "After a touchback, the team that has been awarded the touchback next snaps the ball at its 20-yard line",
    "2024": "After a touchback, the team that has been awarded the touchback shall next snap the ball at its 20-yard line",
    "2025": "After a touchback, the team that has been awarded the touchback shall next snap the ball at its 20-yard line",
    "2026": "After a touchback, the team that has been awarded the touchback shall next snap the ball at its 20-yard line",
}
TB11_EXCEPT = "the touchback results from a free kick"   # the article's own exception: a free kick's spot is X6's (Rule 6)


def tb11_pin(bk, quote, exc=TB11_EXCEPT):
    """The pin holds when the quote is found (rules.find_quote, the book's articles, spaces ignored) in Rule 11's Article 3, Ball Next In Play, with the
    free-kick exception in the same article; its value is the yard line the quote names. Returns (the value or None, the places it was found, why)."""
    hits = rules.find_quote(bk, quote)
    ok_ = [h for h in hits if h.startswith("Rule 11,") and "article 3 (ball next in play" in h.lower()]
    if not ok_: return None, hits, "the quote is not in Rule 11's Article 3 (Ball Next In Play)"
    if not any(h in rules.find_quote(bk, exc) for h in ok_): return None, hits, "the free-kick exception is not in the same article"
    m = re.search(r"(\d+)-yard line", quote)
    return (int(m.group(1)) if m else None), ok_, "pin holds"



def rebuild_v14(G, tb_spot):
    """v14's rebuild, superseded by the shared transition (rebuild below): kept in this chain only as the other side of the old-against-new comparison on
    the record's rows (c); nothing else reads it."""
    n_ = len(G["act"]); off = None; dn = tg = yl = np.nan; kick = True; qprev = None; unk = set()
    S_off, S_dn, S_tg, S_yl, S_kick, S_how, S_diff, Q_st, S_unk = [], [], [], [], [], [], [], [], []
    hk = G["home_opening_kickoff"][0] if n_ else np.nan
    first_recv = (G["away"][0] if hk == 1 else (G["home"][0] if hk == 0 else None)) if n_ else None
    other = lambda t: (G["away"][0] if t == G["home"][0] else G["home"][0]) if isinstance(t, str) else None
    fin = lambda *v: all(not (x is None or (isinstance(x, float) and np.isnan(x))) for x in v)
    def series(team, y):   # a new series: first and 10, or goal to go inside the 10
        return team, 1.0, min(10.0, y), y
    for i in range(n_):
        a = G["act"][i]; q_ = G["q"][i]; how = "carried"
        if q_ != qprev:
            if q_ in (1, 3):
                kick = True; dn = tg = yl = np.nan; unk = set()
                off = first_recv if q_ == 1 else other(first_recv); how = "quarter start: a kickoff to come (home_opening_kickoff)"
                if off is None: unk = {"offense"}; how = "quarter start: the receiving team UNKNOWN (home_opening_kickoff empty)"
            qprev = q_
            Q_st.append((off, dn, tg, yl, kick, "+".join(sorted(unk))))
        else:
            Q_st.append(None)
        pos = G["posteam"][i]; dfn = G["defteam"][i]; txt = str(G["ptext"][i])
        y0, d0, t0, g0 = G["yardline_100"][i], G["down"][i], G["ydstogo"][i], G["yards_gained"][i]
        offs = bool(re.search(r"offsetting", txt, re.I)); declined = bool(re.search(r"declined", txt, re.I))
        pen = G["penalty"][i] == 1 and not declined
        if a == "snap":
            fgm = G["field_goal_result"][i] == "made"; pt = G["play_type"][i]
            if G["touchdown"][i] == 1:
                sc = G["td_team"][i] if isinstance(G["td_team"][i], str) else pos
                kick = True; dn = tg = yl = np.nan; unk = set(); off = next_possession("try_or_field_goal", scorer=sc, scored_on=other(sc))[0]; how = "touchdown: a Try and a kick to come"
            elif fgm:
                kick = True; dn = tg = yl = np.nan; unk = set(); off = next_possession("try_or_field_goal", scorer=pos, scored_on=dfn)[0]; how = "field goal: a kick to come"
            elif G["safety"][i] == 1:
                kick = True; dn = tg = yl = np.nan; unk = set(); off = next_possession("safety", scorer=dfn, scored_on=pos)[0]; how = "safety: a free kick to come"
            elif pen and offs:
                kick = False; off = pos; dn, tg, yl = d0, t0, y0; unk = set(); how = "fouls offsetting on the play: the down replayed"
            elif pen and not (G["interception"][i] == 1 or G["fumble_lost"][i] == 1 or pt == "punt"):
                kick = False; off = pos; dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}
                how = "foul on the play: its enforcement spot is not in the play's columns (UNKNOWN)"
            elif G["interception"][i] == 1:
                kick = False; off = dfn; air, ret = G["air_yards"][i], G["return_yards"][i]
                if G["touchback"][i] == 1: dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "interception, touchback: the spot (the 20) is not in its columns (UNKNOWN)"
                elif pen: dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "interception with a foul: the spot UNKNOWN"
                elif fin(y0, air, ret) and 0 < 100 - (y0 - air) - ret < 100:
                    off, dn, tg, yl = series(dfn, 100.0 - (y0 - air) - ret); unk = set(); how = "interception: 100 - (yard line - air_yards) - return_yards"
                else: dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "interception: air_yards or return_yards empty (UNKNOWN)"
            elif G["fumble_lost"][i] == 1:
                rec = G["fumble_recovery_1_team"][i]; kick = False; off = rec if isinstance(rec, str) else dfn
                dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "fumble lost: the recovery spot is not in the play's columns (UNKNOWN)"
            elif pt == "punt":
                kd, ret = G["kick_distance"][i], G["return_yards"][i]; rec = G["fumble_recovery_1_team"][i]; kick = False; off = dfn
                if isinstance(rec, str) and rec == pos: off = pos; dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "punt recovered by the kickers: the spot UNKNOWN"
                elif G["touchback"][i] == 1: dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "punt, touchback: the spot (the 20) is not in its columns (UNKNOWN)"
                elif pen: dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "punt with a foul: the spot UNKNOWN"
                elif fin(y0, kd, ret) and 0 < 100 - y0 + kd - ret < 100:
                    off, dn, tg, yl = series(dfn, 100.0 - y0 + kd - ret); unk = set(); how = "punt: 100 - yard line + kick_distance - return_yards"
                else: dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "punt: kick_distance or return_yards empty (UNKNOWN)"
            elif pt == "field_goal":
                kick = False; off = dfn; dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "field goal missed: the spot (11-4-3) is not in its columns (UNKNOWN)"
            elif d0 == 4 and G["first_down"][i] != 1 and pt in ("pass", "run", "qb_kneel", "qb_spike") and fin(y0, g0):
                kick = False; off, dn, tg, yl = series(dfn, 100.0 - (y0 - g0)); unk = set(); how = "turnover on downs: 100 - the play's own result"
            elif fin(y0, g0, d0, t0):
                kick = False; off = pos; yl = y0 - g0; ltg = y0 - t0; unk = set(); how = "the play's own result (yard line less the gain)"
                if G["first_down"][i] == 1: dn = 1.0; tg = min(10.0, yl)
                else: dn = d0 + 1; tg = yl - ltg
            else:
                kick = False; off = pos; dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "the play's own columns empty (UNKNOWN)"
        elif a == "foul":
            kick = False; off = pos if isinstance(pos, str) else None; py, ptm = G["penalty_yards"][i], G["penalty_team"][i]
            if off is None: dn = tg = yl = np.nan; unk = {"offense", "down", "distance", "yard line"}; how = "foul: the team with the ball UNKNOWN"
            elif offs: dn, tg, yl = d0, t0, y0; unk = set(); how = "foul, offsetting: the down replayed"
            elif not fin(py, y0, d0, t0) or not isinstance(ptm, str): dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "foul: penalty_yards or penalty_team empty (UNKNOWN)"
            elif ptm == pos:
                yl = y0 + py; dn = d0; tg = t0 + py; unk = set(); how = "foul by the offense: enforced from penalty_yards, the down replayed"
            else:
                yl = y0 - py; unk = set(); how = "foul by the defense: enforced from penalty_yards"
                if G["first_down_penalty"][i] == 1 or t0 - py <= 0: dn = 1.0; tg = min(10.0, yl); how += ", a first down"
                else: dn = d0; tg = t0 - py; how += ", the down replayed"
            if unk == set() and not (0 < yl < 100): dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "foul: the enforced spot outside the field (UNKNOWN)"
        elif a == "kickoff":
            if G["touchdown"][i] == 1:
                sc = G["td_team"][i] if isinstance(G["td_team"][i], str) else pos
                kick = True; dn = tg = yl = np.nan; unk = set(); off = next_possession("try_or_field_goal", scorer=sc, scored_on=other(sc))[0]; how = "kickoff returned for a touchdown: a kick to come"
            else:
                kick = False; kd, ret = G["kick_distance"][i], G["return_yards"][i]
                if G["own_kickoff_recovery"][i] == 1: off = dfn; dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "kickoff recovered by the kickers: the spot UNKNOWN"
                elif pen: off = pos; dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "kickoff with a foul: the spot UNKNOWN"
                elif G["touchback"][i] == 1 and tb_spot is not None: off, dn, tg, yl = series(pos, 100.0 - tb_spot); unk = set(); how = "kickoff, touchback: X6's spot (the season's book)"
                elif fin(y0, kd, ret) and 0 < y0 + kd - ret < 100:
                    off, dn, tg, yl = series(pos, y0 + kd - ret); unk = set(); how = "kickoff: yard line + kick_distance - return_yards"
                else: off = pos; dn = tg = yl = np.nan; unk = {"down", "distance", "yard line"}; how = "kickoff: kick_distance or return_yards empty (UNKNOWN)"
        elif a == "try":
            kick = True; unk = set(); how = "Try: a kick to come"
        ha, aa = G["home_after"][i], G["away_after"][i]
        u_ = set(unk)
        if not fin(ha, aa): u_.add("score")
        S_off.append(off); S_dn.append(dn); S_tg.append(tg); S_yl.append(yl); S_kick.append(kick); S_how.append(how)
        S_diff.append((ha - aa) if off == G["home"][0] else ((aa - ha) if off == G["away"][0] else np.nan))
        S_unk.append("+".join(p_ for p_ in PARTS if p_ in u_ and not (kick and p_ in ("down", "distance", "yard line"))))
    return S_off, S_dn, S_tg, S_yl, S_kick, S_how, S_diff, Q_st, S_unk


try:
    print("\n=== the play-clock pins, hand-written, checked against each book (books read once, cached by their sha) ===")
    PL = pd.read_csv(PIN_FILE, sep="\t", dtype=str, keep_default_na=False)
    print(f"  {PIN_FILE} sha {sh(PIN_FILE)} | lines {len(PL)}")
    BOOKS = {}
    for _, p in PL.iterrows():
        BOOKS[p["book"]] = Book(p["file"]) if os.path.exists(p["file"]) else None
        print(f"  book {p['book']}: {p['file']} sha {sh(p['file'])} | lines {len(BOOKS[p['book']].L) if BOOKS[p['book']] else 'MISSING'}")
    section("pins: books read")
    plants_ok, pins_ok = True, True
    for _, p in PL.iterrows():
        p = dict(p); B = BOOKS[p["book"]]; bk = p["book"]
        rq = READY_QUOTE.get(bk); where = [B.line_of(B.txt.find(SQ(rq))) + 1] if (B and rq and B.txt.find(SQ(rq)) >= 0) else []
        if not where: plants_ok = False
        res_ = []
        for nm, mut in (("wrong article", {"article_heading": p["reset_article_heading"]}), ("wrong duration", {"value": "45"}),
                        ("wrong reset condition", {"reset_quotes": "(c) the three-minute warning;"}), ("missing source", {"file": p["file"] + ".missing"}),
                        ("unaltered quote from the wrong article (rule 3)", {"quote": rq or ""})):
            q_ = dict(p); q_.update(mut); ok2, why2 = check_pin(q_, B if nm != "missing source" else None); plants_ok = plants_ok and not ok2
            res_.append(f"{nm}: {'REFUSED' if not ok2 else 'NOT REFUSED'}")
        ok, why = check_pin(p, B); pins_ok = pins_ok and ok
        print(f"  {bk}: plants (each must be refused): {' | '.join(res_)} | rule 3's quote at line {where} | the pin: {'HOLDS' if ok else 'REFUSED'} ({why})")
    print("\n=== g: the warning's section, hand-written pins (rules/warning_pins.tsv), each book's full section text printed first ===")
    WP = pd.read_csv(WPIN_FILE, sep="\t", dtype=str, keep_default_na=False)
    print(f"  {WPIN_FILE} sha {sh(WPIN_FILE)} | lines {len(WP)}")
    warn_ok = True; WARN_SEC = {}
    for _, p in WP.iterrows():
        p = dict(p); B = BOOKS.get(p["book"]); bk = p["book"]
        H = B.heading(p["section_heading"]) if B else []
        if H:
            k = H[0]; nxt = next((j for j in B.sec_heads if j > k), len(B.L))
            print(f"  {bk}: '{p['section_heading']}' at line {k + 1}; full section text:")
            for j in range(k, nxt): print(f"     L{j + 1}: {B.L[j]}")
        res_ = []
        for nm, mut in (("wrong section number", {"section": "43"}), ("missing source", {"file": p["file"] + ".missing"}),
                        ("unaltered quote from another section (rule 3's ball ready for play)", {"quote": READY_QUOTE.get(bk, "")}),
                        ("wrong rule", {"rule": "4"})):
            q_ = dict(p); q_.update(mut); ok2, _ = check_wpin(q_, B if nm != "missing source" else None); warn_ok = warn_ok and not ok2
            res_.append(f"{nm}: {'REFUSED' if not ok2 else 'NOT REFUSED'}")
        ok, why = check_wpin(p, B); warn_ok = warn_ok and ok
        WARN_SEC[bk] = f"Rule {p['rule']} Section {p['section']} ({bk} book)"
        print(f"     plants (each must be refused): {' | '.join(res_)} | the pin: {'HOLDS' if ok else 'REFUSED'} ({why}) | cited as {WARN_SEC[bk]}")
        print("     the case of the clock reaching 2:00 between downs: the section is silent (its one sentence names the conclusion of a down); placement at 2:00")
        print("     with no live down is a DECLARED ASSUMPTION (g, t); the record's next snap only checks it")
    print("\n=== e, f, d: the review, injury and runoff articles, read and printed from each book (each article to the next article or section heading) ===")
    ART_FOUND = Counter(); ART_TXT = {}; ART_HOW = {}
    def rule_heads(B):
        """v16 g: the book's Rule heading lines ('Rule N' starting a line); the body's run is the lines after the last 'Rule 1'. They read as a sequence
        only when the body's numbers rise one by one from 1; else the Rule an article sits under is not read from them (the article stands on its heading)."""
        hs = [(z, int(RULE_LINE.match(l).group(2))) for z, l in enumerate(B.L) if RULE_LINE.match(l)]
        last1 = max([k_ for k_, (z, r_) in enumerate(hs) if r_ == 1], default=None)
        body = hs[last1:] if last1 is not None else []
        ok_ = bool(body) and [r_ for _, r_ in body] == list(range(1, len(body) + 1))
        return hs, body, ok_
    RH = {bk: rule_heads(B) for bk, B in BOOKS.items() if B is not None}
    for bk, (hs, body, ok_) in RH.items():
        print(f"  g: {bk} book's Rule heading lines {len(hs)} | the body's run {[(z + 1, r_) for z, r_ in body][:24]} -> {'a sequence (each article placed under its Rule)' if ok_ else 'NOT a sequence: no article is placed under a Rule from them; each stands on its own heading'}")
    def rule_of(B, k):
        hs, body, ok_ = RH[[bk_ for bk_, B_ in BOOKS.items() if B_ is B][0]]
        if not ok_: return None
        return next((str(r_) for z, r_ in reversed(body) if z <= k), None)
    WANT_RULE = {"4-5-3 injury before the warning": "4", "4-5-4 injury after the warning": "4", "15-5-1 the clock after a review": "15", "15-5-2 the 10-second runoff after a review": "15",
                 "dead-ball and between-downs fouls": "14", "a double foul without a change of possession": "14"}
    BY_TEXT = {"4-5-3 injury before the warning": r"injur[a-z]{0,8}(time-?outs?)?(priorto|before)(the)?two-?minutewarning",
               "4-5-4 injury after the warning": r"injur[a-z]{0,8}(time-?outs?)?after(the)?two-?minutewarning",
               "a double foul without a change of possession": r"doublefoul[a-z]{0,6}(without|with ?no|withno)(a)?changeofpossession"}
    for bk, B in BOOKS.items():
        if B is None: continue
        sec_only = [k for k, l in enumerate(B.L) if SECONLY_RX.match(l)]
        for nm, rx in ARTICLES + [("dead-ball and between-downs fouls", r"DEADBALLFOULANDFOULBETWEENDOWNS"), ("a double foul without a change of possession", r"DOUBLEFOULWITHOUT(A)?CHANGEOFPOSSESSION")]:
            hits = [k for k, l in enumerate(B.L) if ART_RX.match(l) and re.search(rx, SQ(l), re.I)] or [k for k, l in enumerate(B.L) if re.search(rx, SQ(l), re.I) and len(l) < 60 and k > 0 and ART_RX.match(B.L[k - 1])]
            how_ = "by its heading"
            if not hits and nm in BY_TEXT:   # h: found by its text (the book's own words, spaces ignored), its line and Rule printed
                hits = sorted({B.line_of(m_.start()) for m_ in re.finditer(BY_TEXT[nm], B.txt, re.I)}); how_ = "by its text (no heading found)"
            ART_FOUND[(nm, how_ if hits else "NOT FOUND")] += 1
            if not hits: print(f"  {bk} | {nm}: NOT FOUND by its heading{' or by its text' if nm in BY_TEXT else ''}"); ART_HOW[(bk, nm)] = "NOT FOUND"; continue
            k = hits[0] if (ART_RX.match(B.L[hits[0]]) or how_ != "by its heading") else hits[0] - 1
            nxt = next((j for j in sorted(B.art + sec_only) if j > k), len(B.L)); end_ = min(nxt, k + 60)
            atx = " ".join(B.L[k:end_]); ART_TXT[(bk, nm)] = atx; cut_ = len(atx) > 3200 or end_ < nxt; ru_ = rule_of(B, k)
            ART_HOW[(bk, nm)] = (f"{how_}, under Rule {ru_}" + ("" if ru_ == WANT_RULE[nm] else f" (NOT Rule {WANT_RULE[nm]}: printed as the {bk} book's own text, cited for nothing)")) if ru_ is not None \
                                else f"{how_} (the book's Rule headings not a sequence: the article stands on its own heading)"
            print(f"  {bk} | {nm}: {ART_HOW[(bk, nm)]} | lines {k + 1}-{end_}: " + atx[:3200] + (f" [CUT: the article runs on to line {nxt}]" if cut_ else " [the whole article, to the next heading]"))
    print(f"  articles found: {dict(ART_FOUND)}")
    ART_OK = {(s, nm): ART_HOW.get((rules.RULE_BOOK_OF[s][0], nm), "NOT FOUND").startswith("by") and "NOT Rule" not in ART_HOW.get((rules.RULE_BOOK_OF[s][0], nm), "") for s in S for nm, _ in ARTICLES}
    print(f"  h, per played season: {dict((str(s) + ' ' + nm.split()[0], 'found' if v_ else 'NOT FOUND: its cases read UNKNOWN') for (s, nm), v_ in ART_OK.items())}")
    DEADBALL_CITE = {s: (f"the {rules.RULE_BOOK_OF[s][0]} book's Dead Ball Foul and Foul Between Downs article ({ART_HOW[(rules.RULE_BOOK_OF[s][0], 'dead-ball and between-downs fouls')]})"
                         if ART_HOW.get((rules.RULE_BOOK_OF[s][0], "dead-ball and between-downs fouls"), "NOT FOUND") != "NOT FOUND" else "the dead-ball article NOT FOUND in the season's book") for s in S}
    RESTART_Q = "or a clock that would have otherwise restarted before the next snap"
    RUNOFF_RESTART = {s: SQ(RESTART_Q).lower() in SQ(ART_TXT.get((rules.RULE_BOOK_OF[s][0], "15-5-2 the 10-second runoff after a review"), "")).lower() for s in S}
    print(f"  15-5-2 per season (the season's book): the article adds '{RESTART_Q}': {RUNOFF_RESTART} (the engine's runoff reads it)")
    L.configure(WARN_SEC=WARN_SEC, RUNOFF_RESTART=RUNOFF_RESTART)
    PCS, PCS_NOTE = {}, {}
    for s in S:
        bk = rules.RULE_BOOK_OF[s][0]; row = PL[PL["book"] == bk]
        PCS[s] = (int(row["value"].iloc[0]), int(row["reset_value"].iloc[0]), bk) if len(row) else None
        PCS_NOTE[s] = "pin: 2020 book; 2019 book not pinned" if s == 2019 else f"pin: {bk} book"
    print(f"  the play clock per season: {PCS} | {PCS_NOTE}")
    T_CAP_S = {PCS[s][0] for s in S if s >= 2023 and PCS.get(s)}
    if len(T_CAP_S) != 1: stop(f"the pinned play clock differs across 2023-2025 ({T_CAP_S})")
    T_CAP = T_CAP_S.pop(); L.configure(T_CAP=T_CAP)
    section("pins: plants, the pin checks, the articles")

    print("\n=== c: Rule 11 Section 6 Article 3 (Ball Next In Play): the spot a touchback that is not a free kick puts the ball in play on, pinned per book ===")
    print("  each book's sentence hand-written (TB11_QUOTES) and found in Rule 11's Article 3 by rules.find_quote, with the article's free-kick exception in the same article;")
    print("  the value is the yard line the quote names")
    SCRIM_OK = True; SCRIM = {}
    for bk in sorted(TB11_QUOTES):
        q_ = TB11_QUOTES[bk]; v_, at_, why_ = tb11_pin(bk, q_)
        p1_ = tb11_pin(bk, q_.replace("20-yard", "25-yard"))[0]; p2_ = tb11_pin(bk, "the team that has been awarded the touchback next snaps the ball at its 30-yard line")[0]
        p3_ = tb11_pin(bk, q_, exc="the touchback results from a scrimmage kick")[0]
        pl_ = p1_ is None and p2_ is None and p3_ is None
        print(f"  {bk}: '{q_}' -> {why_}: found in {at_} | value {v_}")
        print(f"     plants (each must be refused): the 20 read as 25: {'REFUSED' if p1_ is None else 'NOT REFUSED'} | a sentence not in the book: {'REFUSED' if p2_ is None else 'NOT REFUSED'}"
              f" | the exception changed: {'REFUSED' if p3_ is None else 'NOT REFUSED'}")
        SCRIM[bk] = (v_, f"Rule 11 Section 6 Article 3 ({bk} book)" if v_ else why_); SCRIM_OK = SCRIM_OK and v_ is not None and pl_
    SCRIM_TB = {s: SCRIM.get(rules.RULE_BOOK_OF[s][0], (None, "book not read")) for s in S}
    L.configure(SCRIM_TB=SCRIM_TB)
    print(f"  the spot per played season (its book): {SCRIM_TB}")
    section("c: Rule 11 Section 6 read")

    print("\n=== c (STATE): the interval table v15, the record read once and shared ===")
    rec_load_cache = {}
    def load_rec(s):
        k_ = (id(record.raw_frame), s)
        if k_ not in rec_load_cache: rec_load_cache[k_] = e1.load(s)
        return rec_load_cache[k_].copy()
    X6 = cache_get("x6", shs(NEW_SHA + "|" + sh("e1.py") + "|" + sh("rules/RULE_PINS.json")), e1.x6_rows)
    TB_SPOT = {s: (int(X6[s]["touchback"]["value"]) if str(X6[s]["touchback"]["value"]).isdigit() else None) for s in S}   # v14's rebuild reads this (the comparison only)
    TBR = {s: L.tb_rules(s, X6[s]) for s in S}
    print("  b (v16): fouls offsetting, each season's book: the Dead Ball Foul article's 'the down counts' (fouls after the ball is dead leave the play standing) and")
    print("  the double-foul article's replay (fouls during the down replay it); not read in a season's book, that season's cases read UNKNOWN:")
    for s in S:
        bk_ = rules.RULE_BOOK_OF[s][0]
        dtx_ = SQ(ART_TXT.get((bk_, "dead-ball and between-downs fouls"), "")).lower(); ftx_ = SQ(ART_TXT.get((bk_, "a double foul without a change of possession"), "")).lower()
        TBR[s].update(dead_counts="thedowncounts" in dtx_, double_replay=bool(re.search(r"replay|repeat", ftx_)), taunt_dead="atauntingfoulthatoccursatanytime" in dtx_)
        print(f"    {s} ({bk_} book): the down counts after dead-ball fouls {'READ' if TBR[s]['dead_counts'] else 'NOT READ'} ({ART_HOW.get((bk_, 'dead-ball and between-downs fouls'), 'NOT FOUND')})"
              f" | a double foul during the down replays it {'READ' if TBR[s]['double_replay'] else 'NOT READ'} ({ART_HOW.get((bk_, 'a double foul without a change of possession'), 'NOT FOUND')})"
              f" | v18 c: 'a taunting foul that occurs at any time' is a dead ball foul {'READ' if TBR[s]['taunt_dead'] else 'NOT READ (taunting by the defense with no award stays UNKNOWN)'}")
    print(f"  the touchback spots per season, each from its pinned rule (free kicks: X6 from each book by rules.season_x6; others: Rule 11 Section 6): {TBR}")
    EX = {}; OPT_HAVE = {}
    for s in S:
        nm_ = contract.PBP_FILE.format(season=s); hdr = record.header(nm_)
        OPT_HAVE[s] = [c_ for c_ in EXTRA_OPT if c_ in hdr]
        ex_ = record.raw_frame(nm_, ["game_id", "play_id"] + EXTRA_V15 + OPT_HAVE[s], f"v15 extras {s}")
        for c_ in [c_ for c_ in EXTRA_OPT if c_ not in OPT_HAVE[s]]: ex_[c_] = ""
        for c_ in ("penalty_yards", "home_timeouts_remaining", "away_timeouts_remaining", "home_opening_kickoff", "kick_distance", "return_yards", "air_yards"):
            ex_[c_] = pd.to_numeric(ex_[c_].replace("", np.nan), errors="coerce")
        ex_["play_id"] = pd.to_numeric(ex_["play_id"], errors="coerce"); EX[s] = ex_.rename(columns={"timeout_team": "timeout_team_col"})
    D = []
    for s in S:
        x = load_rec(s); x["play_id"] = pd.to_numeric(x["play_id"], errors="coerce")
        x = x.merge(EX[s], on=["game_id", "play_id"], how="left", validate="one_to_one"); x = x[x["qtr"] <= 4]; D.append(x)
    d = pd.concat(D, ignore_index=True).sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
    section("table: the record loaded (six seasons, with the rebuild's columns)")
    n = len(d); txt0 = d["desc"].astype(str)
    ruling = txt0.copy(); rev_kind = np.full(n, "", dtype=object)
    has_rev = txt0.str.contains(REVIEW_ANY).to_numpy()
    for i in np.where(has_rev)[0]:
        t_ = txt0.iat[i]; ms = list(REVIEW_RX.finditer(t_))
        if not ms: rev_kind[i] = "review, no outcome word (read whole)"; continue
        m_ = ms[-1]; o_ = m_.group("out").lower()
        if o_ == "reversed": ruling.iat[i] = t_[m_.end():]; rev_kind[i] = "REVERSED: read after the phrase"
        else:
            st_ = REVIEW_ANY.search(t_); ruling.iat[i] = t_[: st_.start()] if st_ else t_; rev_kind[i] = f"{o_}: read before the review phrase"
    print(f"  reviewed rows (text names a review): {int(has_rev.sum())} | {dict(Counter(rev_kind[has_rev]))}")
    txt = ruling
    rk = np.array([e1.row_kind(p, k, t) for p, k, t in zip(d["play_type"], d["kind"], d["two_point_attempt"])], dtype=object)
    warn_txt = txt0.str.contains("Two-Minute Warning", case=False).to_numpy(); endq = txt0.str.match(r"^\s*END (QUARTER|GAME)", case=False).to_numpy()
    act = np.where(rk == "other", np.where(warn_txt, "two-minute warning (written)", np.where(endq, "end of quarter", "other")), rk)
    one = lambda c: (d[c] == 1).to_numpy() if c in d.columns else np.zeros(n, bool)
    T = {"inc": (one("incomplete_pass"), txt.str.contains(r"\bincomplete\b|spiked the ball", case=False).to_numpy()),
         "ob": (one("out_of_bounds"), txt.str.contains(r"\bpushed ob\b|\bran ob\b|out of bounds", case=False).to_numpy()),
         "td": (one("touchdown"), (txt.str.contains("TOUCHDOWN") & ~txt.str.contains("NULLIFIED")).to_numpy()),
         "fgm": ((d["field_goal_result"] == "made").to_numpy(), txt.str.contains(r"field goal is GOOD", case=False).to_numpy()),
         "saf": (one("safety"), txt.str.contains(r"\bSAFETY\b").to_numpy()),
         "tb": (one("touchback"), txt.str.contains(r"\bTouchback\b", case=False).to_numpy()),
         "int": (one("interception"), txt.str.contains("INTERCEPTED").to_numpy()),
         "pen": (one("penalty"), txt.str.contains(PEN_RX).to_numpy()),
         "rev": (one("replay_or_challenge"), has_rev)}
    pen_caps = txt.str.contains(r"\bPENALTY\b").to_numpy()
    print(f"  rows read as a foul by text (any case) {int(T['pen'][1].sum())} | by flag {int(T['pen'][0].sum())}")
    rec = txt.str.extractall(r"RECOVERED by ([A-Z]{2,3})")
    fum_t = np.zeros(n, bool)
    if len(rec):
        rr = rec.reset_index().merge(d[["posteam"]].reset_index().rename(columns={"index": "level_0"}), on="level_0")
        fum_t[rr[rr[0] != rr["posteam"]]["level_0"].unique()] = True
    fum_t &= txt.str.contains("FUMBLES").to_numpy()
    T["fum"] = (one("fumble_lost"), fum_t)
    inj_v15 = txt0.str.contains(INJ_RX).to_numpy(); inj = np.array([injury_text(t_) for t_ in txt0], bool); refto = txt0.str.contains(REF_RX).to_numpy()
    print(f"  e (v16): rows read as an injury: v15's pattern {int(inj_v15.sum())} | v16's (an 'Injury Update: ... returned to the game' announcement is not one) {int(inj.sum())}"
          f" | read otherwise {int((inj_v15 != inj).sum())}")
    rvx_ = np.array([k_.startswith("REVERSED") for k_ in rev_kind], bool)
    for k_ in ("tb", "ob"):   # v16 f: on a REVERSED ruling, the flags the review can change are read from the text after the review phrase (the clock class already was)
        ch_ = rvx_ & (T[k_][0] != T[k_][1]); T[k_] = (np.where(rvx_, T[k_][1], T[k_][0]), T[k_][1])
        print(f"  f (v16): REVERSED rows {int(rvx_.sum())} | the {'touchback' if k_ == 'tb' else 'out-of-bounds'} flag read after the review phrase instead: {int(ch_.sum())} rows changed")
    d["rev_rev"] = rvx_.astype(float)
    ob_missing = d["out_of_bounds"].isna().to_numpy()
    q = d["qtr"].to_numpy(float); qs = d["quarter_seconds_remaining"].to_numpy(float); reg = (d["season_type"] == "REG").to_numpy()
    gid = d["game_id"].to_numpy(object); pos = d["posteam"].to_numpy(object); dfp = d["defteam"].to_numpy(object)
    dn = d["down"].to_numpy(float); fd = one("first_down"); seas = d["season"].to_numpy()
    def events(src, i, poss, RM):
        ow = RM.oob_window(q[i], qs[i], reg[i]); fw = RM.foul_window(q[i], qs[i], reg[i]); bw = RM.before_warning(q[i], qs[i], reg[i]); k = 0 if src == "flags" else 1
        inc_, ob, pen = T["inc"][k][i], T["ob"][k][i], T["pen"][k][i]
        sc = T["td"][k][i] or T["fgm"][k][i] or T["saf"][k][i] or T["tb"][k][i]
        ch = T["int"][k][i] or T["fum"][k][i] or poss
        ev = [("incomplete 4-4f", bool(inc_)), ("out of bounds late 4-3-2a", bool(ob) and ow is True), ("score/touchback/try 4-4d", bool(sc)), ("change of possession 4-4i", bool(ch)),
              ("foul in window 4-3-2e", bool(pen) and fw is True), ("injury after the warning 4-5-4", bool(inj[i]) and bw is False),
              ("out of bounds early 4-3-2a", bool(ob) and ow is False), ("foul outside windows 4-3-2e", bool(pen) and fw is False),
              ("injury, from play text 4-5-3", bool(inj[i]) and bw is True), ("referee timeout, from play text 4-5-5", bool(refto[i])), ("replay review 15-5-1", bool(T["rev"][k][i])),
              ("out of bounds, window unread", bool(ob) and ow is None), ("foul, window unread", bool(pen) and fw is None), ("injury, warning placement unread", bool(inj[i]) and bw is None)]
        if src == "flags" and ob_missing[i]: ev.append(("out of bounds unread", True))
        return ev
    kinds_call = set(contract.CALL_KINDS)
    UNK_NAME = "UNKNOWN_CLOCK_STATE"
    RM = rules   # the fixed readers, on disk (v14 b held)
    def classify_all():
        """The clock after each act from its two readings (flags, text); h: a season whose book does not hold 4-5-3 reads its 4-5-3 cases UNKNOWN."""
        state = np.full(n, "NA", dtype=object); prov = np.full(n, "", dtype=object)
        for i in np.where(act == "snap")[0]:
            poss = bool(d.at[i, "kind"] in ("punt", "field_goal") or (dn[i] == 4 and not fd[i] and d.at[i, "kind"] in kinds_call))
            evf_ = events("flags", i, poss, RM)
            cf, wf = clock_class(evf_, RM.beyond(q[i], reg[i])); ct, _ = clock_class(events("text", i, poss, RM), RM.beyond(q[i], reg[i]))
            if dict(evf_).get("injury, from play text 4-5-3") and not ART_OK.get((int(seas[i]), "4-5-3 injury before the warning"), False):
                state[i] = UNK_NAME; prov[i] = f"4-5-3 not found in the {rules.RULE_BOOK_OF[int(seas[i])][0]} book (h): the case reads UNKNOWN"
            elif cf == ct and cf != "UNKNOWN": state[i] = cf; prov[i] = wf
            else:
                state[i] = UNK_NAME
                dis = [k for k in T if T[k][0][i] != T[k][1][i]] + (["out_of_bounds flag missing"] if ob_missing[i] else [])
                prov[i] = f"flags {cf}, text {ct}; disagree on {'+'.join(dis) if dis else 'none (both unread)'}"
        for i in np.where(act == "foul")[0]:
            fw = RM.foul_window(q[i], qs[i], reg[i]); pre_off = d.at[i, "penalty_team"] == pos[i] and d.at[i, "penalty_type"] in PRESNAP_OFFENSE and q[i] >= 4
            vals = []
            for k in (0, 1):
                pen = bool(T["pen"][k][i])
                vals.append(clock_class([("foul in window 4-3-2e", pen and fw is True), ("offensive pre-snap foul q4/OT 4-3-2e(3)", pen and bool(pre_off)),
                                         ("foul outside windows 4-3-2e", pen and fw is False), ("foul, window unread", pen and fw is None)], RM.beyond(q[i], reg[i]))[0])
            if vals[0] == vals[1] and vals[0] != "UNKNOWN": state[i] = vals[0]
            else: state[i] = UNK_NAME; prov[i] = f"flags {vals[0]}, text {vals[1]}; foul"
        for a_, st_ in (("kickoff", "STOP (4-4i)"), ("try", "STOP (4-4d)"), ("timeout", "STOP (4-5-1)")):
            state[act == a_] = st_
        state[act == "end of quarter"] = "period end"
        return state, prov
    state, prov = classify_all()
    snm_ = act == "snap"; fo_ = act == "foul"
    print(f"  the clock after a snap, read by rules.clock_class (injuries 4-5-3, 4-5-4, reviews 15-5-1 and referee timeouts 4-5-5 included): {dict(Counter(state[snm_]))}"
          f" | snaps whose class comes from them: injury {int(sum(1 for i in np.where(snm_)[0] if 'injur' in prov[i]))}, review {int(sum(1 for i in np.where(snm_)[0] if 'replay' in prov[i]))},"
          f" referee {int(sum(1 for i in np.where(snm_)[0] if 'referee' in prov[i]))} | {UNK_NAME} after a snap {int((state[snm_] == UNK_NAME).sum())}, on foul rows {int((state[fo_] == UNK_NAME).sum())}")
    print(f"  h: 4-5-3 cases read UNKNOWN because the season's book does not hold the article: {int(sum(1 for p_ in prov if str(p_).startswith('4-5-3 not found')))} snaps"
          f" {dict(Counter(seas[k_] for k_, p_ in enumerate(prov) if str(p_).startswith('4-5-3 not found')))}")
    section("table: clock state after each act")

    # the rebuilt state after each row (b, q): from the row and the rows before it
    home = d["home_team"].to_numpy(object); away = d["away_team"].to_numpy(object)
    d["home_after"] = d.groupby("game_id")["total_home_score"].transform(lambda v: v.ffill().fillna(0)).to_numpy(float)
    d["away_after"] = d.groupby("game_id")["total_away_score"].transform(lambda v: v.ffill().fillna(0)).to_numpy(float)
    th = d.groupby("game_id")["total_home_score"].transform(lambda v: v.ffill().shift().fillna(0)).to_numpy(float)
    ta = d.groupby("game_id")["total_away_score"].transform(lambda v: v.ffill().shift().fillna(0)).to_numpy(float)
    d["act"] = act; d["q"] = q; d["home"] = home; d["away"] = away
    d["ptext"] = txt.to_numpy(object)   # the ruling that stands (after a reversal, the text after the review phrase)
    RB = {c_: d[c_].to_numpy(object) for c_ in REB_COLS}
    for c_ in ("q", "down", "ydstogo", "yardline_100", "yards_gained", "first_down", "touchdown", "interception", "fumble_lost", "safety", "penalty", "own_kickoff_recovery", "rev_rev",
               "home_after", "away_after", "home_opening_kickoff", "touchback", "kick_distance", "return_yards", "air_yards", "penalty_yards", "first_down_penalty"):
        RB[c_] = pd.to_numeric(d[c_], errors="coerce").to_numpy(float)
    gstart = np.r_[0, np.where(gid[1:] != gid[:-1])[0] + 1, n]
    def game_cols(a, b, src=RB): return {c_: list(src[c_][a:b]) for c_ in REB_COLS}
    SO, SD, ST, SY, SK, SH, SF, SQ_, SU, SFD, SREP = [], [], [], [], [], [], [], [], [], [], []
    OLDR = [[] for _ in range(9)]; PRER = [[] for _ in range(11)]
    for a, b in zip(gstart[:-1], gstart[1:]):
        G_ = game_cols(a, b)
        o_ = rebuild(G_, TBR[int(seas[a])]); SO += o_[0]; SD += o_[1]; ST += o_[2]; SY += o_[3]; SK += o_[4]; SH += o_[5]; SF += o_[6]; SQ_ += o_[7]; SU += o_[8]; SFD += o_[9]; SREP += o_[10]
        pr_ = rebuild(G_, TBR[int(seas[a])], repairs=False)
        for k_ in range(11): PRER[k_] += pr_[k_]
        ov_ = rebuild_v14(G_, TB_SPOT.get(int(seas[a])))
        for k_ in range(9): OLDR[k_] += ov_[k_]
    s_rep = np.array(SREP, dtype=object)
    qst = [x if x is not None else (None, np.nan, np.nan, np.nan, False, "") for x in SQ_]
    qs_unk = np.array([x[5] for x in qst], dtype=object)
    s_unk = np.array(SU, dtype=object)
    qs_off = np.array([x[0] for x in qst], dtype=object); qs_dn = np.array([x[1] for x in qst], float); qs_tg = np.array([x[2] for x in qst], float)
    qs_yl = np.array([x[3] for x in qst], float); qs_kick = np.array([x[4] for x in qst], bool); qs_first = np.array([x is not None for x in SQ_])
    qs_diff = np.where(qs_off == home, th - ta, np.where(qs_off == away, ta - th, np.nan))
    s_off = np.array(SO, dtype=object); s_dn = np.array(SD, float); s_tg = np.array(ST, float); s_yl = np.array(SY, float); s_kick = np.array(SK, bool); s_how = np.array(SH, dtype=object); s_diff = np.array(SF, float)
    to_m = d["timeout_team_col"].where(d["timeout_team_col"].astype(str).str.len() > 0, None).to_numpy(object)
    to_rx = d["desc"].astype(str).str.extract(r"Timeout #\d+ by ([A-Z]{2,3})")[0].to_numpy(object)
    to_m = np.where(act == "timeout", np.where(pd.notna(to_rx), to_rx, to_m), None)
    half = np.where(q <= 2, 1, 2)
    used_h = np.zeros(n); used_a = np.zeros(n); key_ = None; uh = ua = 0
    for i in range(n):
        k2 = (gid[i], half[i])
        if k2 != key_: key_ = k2; uh = ua = 0
        if act[i] == "timeout" and isinstance(to_m[i], str):
            if to_m[i] == home[i]: uh += 1
            elif to_m[i] == away[i]: ua += 1
        used_h[i] = uh; used_a[i] = ua            # after the row (history only)
    print("  c: each state's parts known or UNKNOWN, by how it was derived (rows; the parts UNKNOWN):")
    for hw, n_ in Counter(s_how).most_common():
        uu = Counter(s_unk[s_how == hw]); print(f"    {hw}: {n_} | {dict((k if k else 'all parts known', v) for k, v in uu.most_common(4))}")
    pk = Counter(p_ for u in s_unk for p_ in (u.split("+") if u else []))
    print(f"  states with an UNKNOWN part {int((s_unk != '').sum())} of {n} rows | by part {dict(pk)} | such a state never enters training as known (c)")
    section("table: the state after each row, rebuilt")

    print("\n=== e (CONSTRUCTION, the original population): the rebuilt state against the next snap (verification only, never an input) ===")
    nsp = np.full(n, -1); last_ = -1
    for i in range(n - 1, -1, -1):
        if i + 1 < n and (gid[i + 1] != gid[i] or half[i + 1] != half[i]): last_ = -1
        nsp[i] = last_
        if act[i] == "snap": last_ = i
    btw = np.full(n, "", dtype=object)
    for i in np.where((nsp >= 0) & np.isin(act, ["snap", "foul", "kickoff"]))[0]:
        kinds_ = [act[k] for k in range(i + 1, nsp[i])]
        btw[i] = "nothing between" if not kinds_ else "+".join(sorted(set(kinds_)))
    ylv0 = d["yardline_100"].to_numpy(float); tgv0 = d["ydstogo"].to_numpy(float)
    own_imm = (act == "snap") & np.isin(s_how, OWN_HOW) & (btw == "nothing between") & (s_unk == "")
    print("  the rebuilt state against the next snap in the half, by how it was rebuilt and what lies between (all four parts: offense, down, distance, yard line):")
    VER = {}; IMM = Counter()
    for hw in sorted(set(s_how)):
        for bw_ in ("nothing between", "an event between"):
            m_ = (s_how == hw) & (nsp >= 0) & ~s_kick & np.isin(act, ["snap", "foul", "kickoff"]) & (s_unk == "") & ((btw == "nothing between") if bw_ == "nothing between" else (btw != "nothing between") & (btw != ""))
            if not m_.any(): continue
            j_ = nsp[m_]; ok_o = s_off[m_] == pos[j_]
            ok_s = ok_o & (s_dn[m_] == dn[j_]) & (np.abs(s_tg[m_] - tgv0[j_]) < 0.5) & (np.abs(s_yl[m_] - ylv0[j_]) < 0.5)
            VER[(hw, bw_)] = (int(m_.sum()), ok_o.mean(), ok_s.mean())
            if bw_ == "nothing between": IMM["n"] += int(m_.sum()); IMM["ok"] += int(ok_s.sum())
            print(f"    {hw} | {bw_}: {int(m_.sum())} | offense agrees {ok_o.mean():.4f} | all four agree {share(int(ok_s.sum()), int(m_.sum()))}")
            if bw_ == "an event between":
                bb = Counter(); tot_ = Counter()
                for k_, ok__ in zip(np.where(m_)[0], ok_s): bb[btw[k_]] += int(ok__); tot_[btw[k_]] += 1
                print("      by what lies between: " + " | ".join(f"{k}: {share(bb[k], v)}" for k, v in tot_.most_common(6)))
    print(f"  immediate transitions (nothing between), every derivation with all parts known: all four agree {share(IMM['ok'], IMM['n'])} (v15 a: 0.9931 before b's repairs)")
    def _pool(bw_):
        v_ = [VER[(h_, bw_)] for h_ in OWN_HOW if (h_, bw_) in VER]; n__ = sum(x[0] for x in v_)
        return n__, (sum(x[0] * x[2] for x in v_) / n__ if n__ else float("nan"))
    own_n, own_b = _pool("nothing between"), _pool("an event between")
    print(f"  v13's 0.9343 located (the play's own result: the next down or a first down from the gain; all four agree): nothing between {own_n[1]:.4f} of {own_n[0]}"
          f" | an event between {own_b[1]:.4f} of {own_b[0]}")
    bad_imm = np.where(own_imm & (nsp >= 0) & ~((s_off == pos[np.maximum(nsp, 0)]) & (s_dn == dn[np.maximum(nsp, 0)]) & (np.abs(s_tg - tgv0[np.maximum(nsp, 0)]) < 0.5) & (np.abs(s_yl - ylv0[np.maximum(nsp, 0)]) < 0.5)))[0]
    for i in bad_imm[:8]:
        j = nsp[i]
        print(f"    e.g. not agreeing, nothing between: {gid[i]} seq {int(d.at[i, 'order_sequence'])}: rebuilt {s_off[i]} {s_dn[i]:.0f}&{s_tg[i]:.0f} at {s_yl[i]:.0f} | next snap {pos[j]} {dn[j]:.0f}&{tgv0[j]:.0f} at {ylv0[j]:.0f} | {txt0.iat[i][:110]}")
    section("e: the next-snap check")

    print("\n=== c (EVENT OWNERSHIP, before any fitting): every foul-related row sorted by its own text and flags ===")
    FSORT_TXT = {"1 down, play wiped": "(1) a foul during a down: a no-play whose text describes a play; the down cancelled and repeated (3-8-4)",
                 "1 down, play stands": "(1) a foul during a down: a penalty on a play row; the play stands, its enforcement modifies the result",
                 "1 down, offsetting": "(1) a foul during a down: fouls offsetting on a play row; the down replayed (3-8-4)",
                 "2 before the snap": "(2) a distinct dead-ball foul before the snap: no play described before PENALTY",
                 "2 between downs": "(2) a distinct dead-ball foul between downs: the text says 'between downs'",
                 "3 administrative": "(3) an administrative row: the same team's same foul accepted in the down just before it (the foul is that down's)",
                 "3 administrative: the game's opening header": "(3) an administrative row (v18 b): the game's opening header, act 'other' on the first row of the game; no event",
                 "UNKNOWN": "UNKNOWN: the foul unnamed (no clause in the text, no penalty_type) or its team unread"}
    fsort = np.full(n, "", dtype=object); fname = np.full(n, "", dtype=object); focc = np.zeros(n, int); fam = np.full(n, "", dtype=object)
    for i in np.where((act == "foul") | ((act == "snap") & (T["pen"][0] | T["pen"][1])))[0]:
        t_ = txt0.iat[i]; cl_ = r4.foul_clauses(t_); acc_ = [c_ for c_ in cl_ if c_[1]]; ptp_ = d.at[i, "penalty_type"]; ptm_ = d.at[i, "penalty_team"]
        nm_ = r4.text_named(t_); focc[i] = len(acc_); fname[i] = ptp_ if isinstance(ptp_, str) else (nm_[0][1] if nm_ else "")
        offs_ = bool(cl_) and not acc_ and bool(re.search(r"offsetting", t_, re.I))
        if act[i] == "snap":
            fsort[i] = "1 down, play stands" if acc_ else ("1 down, offsetting" if offs_ else ("UNKNOWN" if (T["pen"][0][i] and not cl_) else ""))
            continue
        if not cl_ and not isinstance(ptp_, str): fsort[i] = "UNKNOWN"; continue
        if down_row(d.at[i, "play_type"], d.at[i, "timeout"], ptp_, t_): fsort[i] = "1 down, play wiped"; continue   # d: one definition (lib down_row)
        p_ = i - 1
        if p_ >= 0 and gid[p_] == gid[i] and act[p_] in ("snap", "kickoff") and nm_ and set(nm_) & set(r4.text_named(txt0.iat[p_])): fsort[i] = "3 administrative"; continue
        if not isinstance(ptm_, str) and not cl_: fsort[i] = "UNKNOWN"; continue
        fsort[i] = "2 between downs" if re.search(r"between downs", t_, re.I) else "2 before the snap"
        f_ = e1.family(ptm_, pos[i], ptp_, d.at[i, "play_type"] == "no_play", False, t_)
        fam[i] = f_ if f_ in ("F1", "F2") else ""
    for k_, v_ in Counter(fsort[fsort != ""]).most_common():
        m_ = fsort == k_
        print(f"  {FSORT_TXT[k_]}: rows {v_} | occurrences (accepted fouls; several on one row kept apart) {int(focc[m_].sum())} | rows with two or more {int((focc[m_] >= 2).sum())}"
              f" | by name {dict(Counter(fname[m_]).most_common(10))}")
    first_g = np.r_[True, gid[1:] != gid[:-1]]; oth_ = act == "other"
    print(f"  b (v18): the record's rows read 'other' {int(oth_.sum())}: the first row of its game {int((oth_ & first_g).sum())} of {len(set(gid))} games | elsewhere {int((oth_ & ~first_g).sum())}")
    print(f"    the first rows' text: {dict(Counter(txt0[oth_ & first_g].str.slice(0, 40)).most_common(5))} | their clock {dict(Counter(np.where(np.isnan(qs[oth_ & first_g]), -1, qs[oth_ & first_g])).most_common(3))}")
    print(f"    elsewhere, their text: {dict(Counter(txt0[oth_ & ~first_g].str.slice(0, 40)).most_common(8))}")
    hdr_ = oth_ & first_g & ~txt0.str.contains(r"\(\d{1,2}:\d{2}\)").to_numpy()   # the header: the game's first row, 'other', no play clock written (no play)
    fsort[hdr_] = "3 administrative: the game's opening header"
    print(f"    made administrative (the game's first row, act 'other', no clock in its text): {int(hdr_.sum())} rows; the next real row decides what the moment before it ended in")
    wip_ = fsort == "1 down, play wiped"
    print(f"  d (v18): the record's no-play downs (category 1, the play wiped) by their out_of_bounds mark: {dict(Counter(d.loc[wip_, 'out_of_bounds'].astype(str)))}"
          f" (the engine's no-play downs written the same way)")
    OB_REC1 = (pd.to_numeric(d.loc[wip_, "out_of_bounds"], errors="coerce").to_numpy(float), d.loc[wip_, "game_id"].to_numpy(object))   # v19 r4: b's record side, kept for the engine's beside it
    print(f"  (2) by the engine's families: F1 {int((fam == 'F1').sum())} | F2 {int((fam == 'F2').sum())} | other names {int(((fsort == '2 before the snap') | (fsort == '2 between downs')).sum() - (fam != '').sum())}")
    print(f"  the dead-ball article each season cites: {DEADBALL_CITE}")
    rv_flag = T["rev"][0].astype(float); rv_rev = np.array([k.startswith("REVERSED") for k in rev_kind], float)
    chal_team = txt0.str.extract(CHAL_RX)[0].to_numpy(object)
    other_kind = np.where(act == "other", np.where(inj, "injury", np.where(has_rev | one("replay_or_challenge"), "review", "other")), "")
    Wst, Est = d["W"].to_numpy(float), d["E"].to_numpy(float)
    act_tab = np.where(fsort == "1 down, play wiped", "snap", act)   # v16 d: a no-play down is a snap in the table (its row's own event, enforced, kept in act_rec)
    print(f"  d (v16): no-play downs written as snaps in the table {int((act_tab != act).sum())} (their event, a foul enforced, kept as act_rec)")
    base = pd.DataFrame({"game_id": gid, "season": seas, "seq": d["order_sequence"].to_numpy(float), "q": q, "clock": qs, "act": act_tab, "act_rec": act, "state": state, "provenance": prov,
                         "review": rev_kind, "rv": rv_flag, "rv_rev": rv_rev, "chal_team": chal_team, "inj": inj.astype(float), "family": fam, "other_kind": other_kind,
                         "fsort": fsort, "fname": fname, "focc": focc, "kind": d["kind"].to_numpy(object),
                         "posteam": pos, "defteam": dfp, "home": home, "away": away, "timeout_team": to_m, "penalty_yards": d["penalty_yards"].to_numpy(float),
                         "home_to_rem": d["home_timeouts_remaining"].to_numpy(float), "away_to_rem": d["away_timeouts_remaining"].to_numpy(float),
                         "W": Wst, "E": Est, "W_r": d["W_r"].to_numpy(float), "E_r": d["E_r"].to_numpy(float),
                         "play_len": np.where(np.isin(act_tab, ["snap", "kickoff"]), Est - Wst, np.nan), "diff_before": np.where(pos == home, th - ta, np.where(pos == away, ta - th, np.nan)),
                         "used_home": used_h, "used_away": used_a, "s_off": s_off, "s_down": s_dn, "s_togo": s_tg, "s_yl": s_yl, "s_kick": s_kick, "s_how": s_how, "s_diff": s_diff, "s_unk": s_unk,
                         "down": dn, "ydstogo": d["ydstogo"].to_numpy(float), "yardline_100": d["yardline_100"].to_numpy(float),
                         "inc_flag": T["inc"][0], "inc_text": T["inc"][1], "pen_flag": T["pen"][0], "pen_text": T["pen"][1], "pen_caps": pen_caps,
                         "qs_first": qs_first, "qs_off": qs_off, "qs_down": qs_dn, "qs_togo": qs_tg, "qs_yl": qs_yl, "qs_kick": qs_kick, "qs_diff": qs_diff, "qs_unk": qs_unk,
                         "used_home_before": np.r_[0.0, used_h[:-1]] * (np.r_[False, gid[1:] == gid[:-1]] & np.r_[False, half[1:] == half[:-1]]),
                         "used_away_before": np.r_[0.0, used_a[:-1]] * (np.r_[False, gid[1:] == gid[:-1]] & np.r_[False, half[1:] == half[:-1]]),
                         "text": txt0.str.slice(0, 160)})

    section("c: the foul-related rows sorted")

    print("\n=== e (CONSTRUCTION): the one transition checked: its known-right cases, two plants, v14's rebuild against this one, b's repairs' effect ===")
    nfx_, badfx_ = L.run_fixtures(L.after)
    print(f"  known-right cases (each true by the article it names, built by hand; v15 b's combined events among them): {nfx_} | failed {len(badfx_)}")
    for b_ in badfx_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")
    SRC_AFTER = inspect.getsource(L.after_one)
    PL_T = L.PLANTS   # transition.py's own plants (v19 r2: the yards copied whole past the goal line among them)
    pl_ok = True
    for nm_, (o_, n_) in PL_T.items():
        _, bp_ = L.run_fixtures(L.planted(SRC_AFTER, o_, n_)); pl_ok = pl_ok and bool(bp_)
        print(f"  plant, {nm_}: {len(bp_)} of {nfx_} cases fail -> {plant_verdict(nfx_, bool(bp_))}")
    for nm_, (o_, n_) in L.STAND_PLANTS.items():   # v18 c: the foul on a play that stands
        _, bp_ = L.run_fixtures(L.planted_stand(o_, n_)); pl_ok = pl_ok and bool(bp_)
        print(f"  plant (v18 c), {nm_}: {len(bp_)} of {nfx_} cases fail -> {plant_verdict(nfx_, bool(bp_))}")
    nyc_, badyc_ = L.run_yard_cases()   # v19 part 2: a foul's yards by its article
    print(f"  yards cases (a foul's yards by its article from its spot; half the distance; pass interference's spot): {nyc_} | failed {len(badyc_)}")
    for b_ in badyc_: print(f"    FAILED: {b_[0]}: must be {b_[1]}, came back {b_[2]}")
    pl_ok = pl_ok and not badyc_
    for nm_, (fn_, f_) in L.YARD_PLANTS.items():
        _, bp_ = L.run_yard_cases({fn_: f_}); pl_ok = pl_ok and bool(bp_)
        print(f"  plant (v19 part 2), {nm_}: {len(bp_)} of {nyc_} yards cases fail -> {plant_verdict(nyc_, bool(bp_))}")
    TRANS_OK = (not badfx_) and pl_ok
    jn_ = np.maximum(nsp, 0)
    def agree4(off_, dn_, tg_, yl_, m_):
        return m_ & (nsp >= 0) & (off_ == pos[jn_]) & (dn_ == dn[jn_]) & (np.abs(tg_ - tgv0[jn_]) < 0.5) & (np.abs(yl_ - ylv0[jn_]) < 0.5)
    eqv = lambda a_, b_: (a_ == b_) | (np.isnan(a_) & np.isnan(b_))
    p_off, p_dn, p_tg, p_yl, p_kick, p_how = (np.array(PRER[0], dtype=object), np.array(PRER[1], float), np.array(PRER[2], float), np.array(PRER[3], float),
                                              np.array(PRER[4], bool), np.array(PRER[5], dtype=object))
    p_unk = np.array(PRER[8], dtype=object)
    wit_p = (btw == "nothing between") & np.isin(act, ["snap", "foul", "kickoff"]) & (nsp >= 0) & ~s_kick & ~p_kick
    print("  b's repairs, every row they change (the adapter as v15's first chain read it -> repaired), each against its immediate next snap:")
    REPV = Counter()
    REP_TXT = {"A1": "the foul read from both readings, v11 c", "B1": "a second change of possession, the text's last recovery",
               "B2": "a play row's fouls offsetting after the ball is dead: the play stands (the Dead Ball Foul article)", "F1": "a REVERSED ruling's touchback and spot read after the review phrase",
               "C1": "v18 c, a foul on a play that stands passed to transition.stand()"}
    for r_ in ("A1", "B1", "B2", "F1", "C1"):
        m_ = np.array([r_ in str(x_).split("+") for x_ in s_rep])
        ch_ = m_ & ~((p_off == s_off) & eqv(p_dn, s_dn) & eqv(p_tg, s_tg) & eqv(p_yl, s_yl) & (p_unk == s_unk))
        pa_ = agree4(p_off, p_dn, p_tg, p_yl, ch_ & wit_p & (p_unk == "")); na_ = agree4(s_off, s_dn, s_tg, s_yl, ch_ & wit_p & (s_unk == ""))
        mk_unk = ch_ & (p_unk == "") & (s_unk != "")
        REPV[(r_, "rows changed")] = int(ch_.sum()); REPV[(r_, "made UNKNOWN, agreeing before (a repair's cost)")] = int((mk_unk & pa_).sum())
        REPV[(r_, "made UNKNOWN, disagreeing before")] = int((mk_unk & wit_p & ~pa_).sum()); REPV[(r_, "made UNKNOWN, no immediate next snap")] = int((mk_unk & ~wit_p).sum())
        REPV[(r_, "known after, agrees")] = int(na_.sum()); REPV[(r_, "known after, disagrees")] = int((ch_ & wit_p & (s_unk == "") & ~na_).sum())
        print(f"    {r_} ({REP_TXT[r_]}): "
              + " | ".join(f"{k_[1]} {v_}" for k_, v_ in REPV.items() if k_[0] == r_))
    print("\n=== c (v18): a foul on a play that stands, the record's rows (repair C1), each against its immediate next snap (verification only, never an input) ===")
    mC = np.array(["C1" in str(x_).split("+") for x_ in s_rep])
    stand_how = np.array([str(h_).startswith(L.STAND_PREFIX) for h_ in s_how])
    OLD_UNREAD = "a foul on the play: its enforcement spot is not in the play's columns (UNKNOWN)"
    print(f"  rows with one accepted foul on a play that stands passed to stand(): {int(mC.sum())} (v17: 2,876 rows read '{OLD_UNREAD}'; rows left so now:"
          f" {int((s_how == OLD_UNREAD).sum())})")
    for hw_, v_ in Counter(s_how[mC]).most_common():
        m_ = mC & (s_how == hw_); kn_ = m_ & (s_unk == "") & wit_p
        ag_ = agree4(s_off, s_dn, s_tg, s_yl, kn_)
        print(f"    {hw_}: {v_}" + (f" | with an immediate next snap {int(kn_.sum())}, all four agree {share(int(ag_.sum()), int(kn_.sum()))}" if (s_unk[m_] == "").any() else ""))
    kC = mC & (s_unk == "") & wit_p; aC = agree4(s_off, s_dn, s_tg, s_yl, kC)
    C1_AGREE = (int(aC.sum()), int(kC.sum()))
    print(f"  resolved, with an immediate next snap: {C1_AGREE[1]} | all four agree {share(*C1_AGREE)} (prediction g: at least 0.99)")
    nm_c = d["penalty_type"].to_numpy(object)
    for nm__, v_ in Counter(nm_c[kC]).most_common(10):
        m_ = kC & (nm_c == nm__); print(f"    by name: {nm__}: {share(int(aC[m_].sum()), int(m_.sum()))}")
    for i in np.where(kC & ~aC)[0][:12]:
        j = nsp[i]
        print(f"    e.g. not agreeing: {gid[i]} seq {int(d.at[i, 'order_sequence'])}: {s_how[i]} -> {s_off[i]} {s_dn[i]:.0f}&{s_tg[i]:.0f} at {s_yl[i]:.0f} | next snap {pos[j]} {dn[j]:.0f}&{tgv0[j]:.0f}"
              f" at {ylv0[j]:.0f} | yards_gained {d.at[i, 'yards_gained']} penalty_yards {d.at[i, 'penalty_yards']} award {d.at[i, 'first_down_penalty']} | {txt0.iat[i][:150]}")
    print("  the record's rows, v14's rebuild (kept only for this comparison) against this one, each row sorted on its own (no row offsets another):")
    o_off, o_dn, o_tg, o_yl, o_kick, o_how = (np.array(OLDR[0], dtype=object), np.array(OLDR[1], float), np.array(OLDR[2], float), np.array(OLDR[3], float),
                                              np.array(OLDR[4], bool), np.array(OLDR[5], dtype=object))
    o_unk = np.array(OLDR[8], dtype=object)
    same_ = (o_off == s_off) & eqv(o_dn, s_dn) & eqv(o_tg, s_tg) & eqv(o_yl, s_yl) & (o_kick == s_kick) & (o_unk == s_unk)
    o_known = o_unk == ""; n_known = s_unk == ""
    wit_ = (btw == "nothing between") & np.isin(act, ["snap", "foul", "kickoff"]) & (nsp >= 0) & ~s_kick & ~o_kick   # an immediate next snap: the witness
    ao_ = agree4(o_off, o_dn, o_tg, o_yl, wit_ & o_known); an_ = agree4(s_off, s_dn, s_tg, s_yl, wit_ & n_known)
    KO_HOW = "kickoff touchback: the book names two spots and which one applies is not in the row (UNKNOWN)"
    rep_unk = np.array([bool(x_) for x_ in s_rep]) & ~n_known
    cat_ = np.full(n, "", dtype=object)
    cat_[same_] = "preserved"
    d_ = ~same_
    cat_[d_ & ~wit_] = "unresolved (no immediate next snap to judge it)"
    cat_[d_ & wit_ & an_ & ~ao_] = "corrected (the new agrees with the next snap, the old did not)"
    cat_[d_ & wit_ & ao_ & ~an_] = "regressed (the old agreed with the next snap, the new does not)"
    cat_[d_ & wit_ & ~ao_ & ~an_] = "unresolved (neither agrees with the next snap)"
    cat_[d_ & wit_ & ao_ & an_] = "differ, both agree with the next snap"
    cat_[d_ & o_known & ~n_known] = "COVERAGE LOSS: made UNKNOWN by the transition (a part its inputs or the season's book do not give; the reason printed)"
    cat_[d_ & o_known & ~n_known & rep_unk] = "COVERAGE LOSS: made UNKNOWN by a b repair (never counted as corrected)"
    cat_[d_ & o_known & ~n_known & (s_how == KO_HOW)] = "COVERAGE LOSS: a kickoff touchback, 6-1-5's two spots (2024-2025 books), the row not saying which"
    for c_, v_ in Counter(cat_).most_common():
        m_ = cat_ == c_
        print(f"    {c_}: {v_} rows" + ("" if c_ == "preserved" else " | by (old how -> new how): " + str(dict(Counter(zip(o_how[m_], s_how[m_])).most_common(6)))))
    reg_u = list(np.where(cat_ == "regressed (the old agreed with the next snap, the new does not)")[0])
    print(f"  regressions (the old agreed, the new is known and disagrees) {len(reg_u)} (v15: 66): each listed; v15's 66 offsetting rows now: "
          f"{dict(Counter(cat_[i_] for i_ in np.where(np.array(['B2' in str(x_) for x_ in s_rep]))[0]))}")
    for i in reg_u[:20]: print(f"    regression: {gid[i]} seq {int(d.at[i, 'order_sequence'])}: {o_how[i]} -> {s_how[i]} | {txt0.iat[i][:100]}")
    nk_ = np.where(~o_known & n_known & wit_)[0]; nk_bad = [i for i in nk_ if not an_[i]]
    nkp_ = np.where(~o_known & (p_unk == "") & wit_p)[0]
    NK_PRE = [i for i in nkp_ if not agree4(p_off, p_dn, p_tg, p_yl, wit_p & (p_unk == ""))[i]]
    print(f"  newly known states with an immediate next snap (against v14): before b's repairs {len(nkp_)}, disagreeing {len(NK_PRE)} | after {len(nk_)}, agree"
          f" {len(nk_) - len(nk_bad)}, DISAGREE {len(nk_bad)} (b traces the 9 v15 named; each one left is printed there)")
    for i in nk_bad[:20]: print(f"    newly known, disagrees: {gid[i]} seq {int(d.at[i, 'order_sequence'])}: {s_how[i]} -> {s_off[i]} {s_dn[i]:.0f}&{s_tg[i]:.0f} at {s_yl[i]:.0f} | next snap {pos[nsp[i]]} {dn[nsp[i]]:.0f}&{tgv0[nsp[i]]:.0f} at {ylv0[nsp[i]]:.0f}")
    PARITY_REC = dict(Counter(cat_)); PARITY_REC.update(regressions=len(reg_u), newly_known_disagree=len(nk_bad))
    PARITY_REC_OK = not reg_u
    print(f"  the record's comparison: no regression -> {PARITY_REC_OK}")
    sfd = np.array(SFD, float); fdc = d["first_down"].to_numpy(float); mfd = ~np.isnan(sfd) & ~np.isnan(fdc)
    print(f"  the first down the transition derived from the gain against the row's own first_down column (never read by it): agree {share(int((sfd[mfd] == fdc[mfd]).sum()), int(mfd.sum()))}")
    for i in np.where(mfd & (sfd != fdc))[0][:8]:
        print(f"    e.g. {gid[i]} seq {int(d.at[i, 'order_sequence'])}: {dn[i]:.0f}&{tgv0[i]:.0f} at {ylv0[i]:.0f}, gain {d.at[i, 'yards_gained']} -> derived {sfd[i]:.0f}, column {fdc[i]:.0f} | {txt0.iat[i][:100]}")
    section("e: the transition and the rebuild comparison")

    print("\n=== d, g, k: the warning and 0:00 placed by rule ===")
    downs = np.isin(act, ["snap", "kickoff", "try", "foul"])
    RULE_ROWS = []; WMISS = []; WCOUNT = Counter(); WCHK = Counter(); WMIS = []
    G_ = pd.Series(np.arange(n)).groupby([gid, q])
    for (g, qq), idx in G_:
        idx = idx.to_numpy()
        if qq not in (2, 4): continue
        cand = [i for i in idx if downs[i] and not np.isnan(qs[i]) and qs[i] > 120]
        after = [i for i in idx if not np.isnan(qs[i]) and qs[i] <= 120]
        if not cand or not after:
            WMISS.append((g, int(qq), "no row at 2:00 or less in the quarter" if not after else "no down above 2:00")); continue
        a = cand[-1]; j = next((k for k in idx if k > a and act[k] == "snap"), None)
        L_a = Est[a] - Wst[a] if act[a] in ("snap", "kickoff") else np.nan
        ce_a = qs[a] - L_a if not np.isnan(L_a) else np.nan
        if np.isnan(ce_a): clk, how_w = np.nan, "clock unread: the last down is unstamped"
        elif ce_a > 120 and str(state[a]) == "RUN": clk, how_w = 120.0, "between downs: at 2:00 (declared assumption, the book silent)"
        elif ce_a > 120: clk, how_w = np.nan, f"the clock stopped above 2:00 after the last down ({state[a]}): clock unread"
        else: clk, how_w = max(round(ce_a), 0.0), "at the conclusion of the down that ran past 2:00 (its stamped length)"
        nxt_clk = qs[j] if j is not None else np.nan
        verdict_w = "the next snap agrees" if (not np.isnan(clk) and nxt_clk == clk) else ("no next snap" if np.isnan(nxt_clk) else ("clock unread" if np.isnan(clk) else "MISMATCH: the next snap reads otherwise"))
        WCHK[(how_w, verdict_w)] += 1
        if verdict_w.startswith("MISMATCH"):
            betw_ = [act[k] for k in range(a + 1, j) if act[k] not in ("two-minute warning (written)",)]
            prec_ = 1.0 + (d.at[a, "E_r"] if not np.isnan(d.at[a, "E_r"]) else 1.0) + (d.at[a, "W_r"] if not np.isnan(d.at[a, "W_r"]) else 1.0)
            ref_ = ce_a if how_w.startswith("at the conclusion") else 120.0
            if betw_: cause_ = "rows between the down and the next snap (" + "+".join(sorted(set(betw_))) + ")"
            elif abs(nxt_clk - ref_) <= prec_: cause_ = "within the assumed quantization bound (the clock's whole second and the play's two stamps' stored resolutions)"
            elif how_w.startswith("between downs") and nxt_clk < 120: cause_ = "the clock read below 2:00 at the next snap: it ran past 2:00 between downs (no stop recorded at 2:00)"
            elif nxt_clk < ref_: cause_ = "unexplained beyond the bound: the clock fell more than the play's stamped length"
            else: cause_ = "unexplained beyond the bound: the clock fell less than the play's stamped length"
            WMIS.append((cause_, g, int(qq), int(d.at[a, "order_sequence"]), qs[a], L_a, ce_a, clk, nxt_clk, how_w, txt0.iat[a][:90]))
        bk = rules.RULE_BOOK_OF[int(seas[a])][0]
        RULE_ROWS.append(dict(game_id=g, season=seas[a], seq=float(d.at[a, "order_sequence"]) + 0.5, q=qq, clock=clk, act="two-minute warning", act_rec="two-minute warning", state="STOP (two-minute warning)",
                              provenance=f"rule: {WARN_SEC.get(bk, 'Rule 3 (book unread)')}; {how_w}", review="", rv=0.0, rv_rev=0.0, chal_team=None, inj=0.0, family="", other_kind="",
                              fsort="", fname="", focc=0, kind="",
                              posteam=None, defteam=None, home=home[a], away=away[a], timeout_team=None, penalty_yards=np.nan, home_to_rem=np.nan, away_to_rem=np.nan,
                              W=np.nan, E=np.nan, W_r=np.nan, E_r=np.nan, play_len=np.nan, diff_before=np.nan, used_home=used_h[a], used_away=used_a[a],
                              s_off=s_off[a], s_down=s_dn[a], s_togo=s_tg[a], s_yl=s_yl[a], s_kick=s_kick[a], s_how="carried", s_diff=s_diff[a], s_unk=s_unk[a],
                              down=np.nan, ydstogo=np.nan, yardline_100=np.nan, inc_flag=False, inc_text=False, pen_flag=False, pen_text=False, pen_caps=False, text="(placed by rule)",
                              qs_first=False, qs_off=None, qs_down=np.nan, qs_togo=np.nan, qs_yl=np.nan, qs_kick=False, qs_diff=np.nan, qs_unk="", used_home_before=used_h[a], used_away_before=used_a[a]))
        WCOUNT[(int(seas[a]), int(qq))] += 1
    print(f"  warnings placed {len(RULE_ROWS)} | quarters where none could be placed {len(WMISS)}")
    print("  placement and the record's next snap (a check only): " + " | ".join(f"{k[0]} / {k[1]}: {v}" for k, v in sorted(WCHK.items())))
    for w in WMISS[:20]: print(f"    not placed: {w[0]} q{w[1]}: {w[2]}")
    print(f"\n=== e: the placements the next snap reads otherwise ({len(WMIS)}), counted by cause (named from the rows before the placement is used) ===")
    for (hw_, c_), v_ in sorted(Counter((w[9].split(':')[0], w[0]) for w in WMIS).items(), key=lambda z: -z[1]): print(f"  {hw_} | {c_}: {v_}")
    print("  20 of them, row by row (game, quarter, the down's seq | the clock at its snap, its stamped length, the clock after it, the placed clock | the next snap's clock):")
    for w in WMIS[:20]:
        print(f"    {w[1]} q{w[2]} seq {w[3]} | snap {w[4]:.0f}, length {w[5]:.3f}, after {w[6]:.3f}, placed {w[7]:.0f} | next snap {w[8]:.0f} | {w[0][:70]} | {w[10]}")
    ended_early = sorted({w[0] for w in WMISS if w[1] == 4 and w[2].startswith("no row at 2:00")})
    print(f"  games the record ends before 2:00 of quarter 4: {len(ended_early)} {ended_early[:20]}")
    have0 = set(zip(gid[act == "end of quarter"], q[act == "end of quarter"])); ZROWS = []
    for (g, qq), idx in G_:
        if (g, qq) in have0: continue
        a = idx.to_numpy()[-1]
        zr = dict(RULE_ROWS[0]) if RULE_ROWS else {}
        zr.update(game_id=g, season=seas[a], seq=float(d.at[a, "order_sequence"]) + 0.75, q=qq, clock=0.0, act="end of quarter", act_rec="end of quarter", state="period end (0:00, rule)",
                  provenance="rule: 0:00 (4-1-1); no written row", home=home[a], away=away[a], used_home=used_h[a], used_away=used_a[a], s_off=s_off[a], s_down=s_dn[a],
                  s_togo=s_tg[a], s_yl=s_yl[a], s_kick=s_kick[a], s_diff=s_diff[a], s_unk=s_unk[a], text="(placed by rule; no written row)")
        ZROWS.append(zr)
    TAB = pd.concat([base, pd.DataFrame(RULE_ROWS), pd.DataFrame(ZROWS)], ignore_index=True).sort_values(["game_id", "seq"], kind="mergesort").reset_index(drop=True)
    eq = TAB["act"] == "end of quarter"
    TAB.loc[eq & (TAB["provenance"] == ""), "provenance"] = "rule: 0:00, the period's 15 minutes expire (4-1-1); written text attached"
    bad0 = TAB.loc[eq & (TAB["clock"] != 0), ["game_id", "q", "clock"]]
    TAB.loc[eq, "clock"] = 0.0; TAB.loc[eq, "state"] = "period end (0:00, rule)"
    allq = pd.MultiIndex.from_product([TAB["game_id"].unique(), [1.0, 2.0, 3.0, 4.0]])
    per_q = TAB[eq].groupby(["game_id", "q"]).size().reindex(allq, fill_value=0)
    print(f"  0:00: rows {int(eq.sum())} (placed where none written {len(ZROWS)}) | quarters with exactly one {int((per_q == 1).sum())} of {len(per_q)} | written clock not 0:00 {len(bad0)}")
    section("table: the warning and 0:00 placed")

    n2 = len(TAB); gid2 = TAB["game_id"].to_numpy(object); q2 = TAB["q"].to_numpy(float); c2 = TAB["clock"].to_numpy(float); act2 = TAB["act"].to_numpy(object)
    same_next = np.r_[gid2[1:] == gid2[:-1], False]
    nq = np.where(same_next, np.r_[q2[1:], np.nan], np.nan); nc = np.where(same_next, np.r_[c2[1:], np.nan], np.nan)
    W2, E2 = TAB["W"].to_numpy(float), TAB["E"].to_numpy(float); nW = np.where(same_next, np.r_[W2[1:], np.nan], np.nan)
    trans = np.where(~same_next, "end of game", np.where(nq != q2, "period end", np.where(np.isnan(c2) | np.isnan(nc), "clock missing", np.where(nc > c2, "clock correction", "same quarter"))))
    for c_ in ("act", "other_kind", "timeout_team", "family"): TAB["next_" + c_] = np.where(same_next, np.r_[TAB[c_].to_numpy(object)[1:], None], None)
    TAB["transition"] = trans; TAB["game_seconds"] = np.where(trans == "same quarter", c2 - nc, np.nan)
    real = np.where(~np.isnan(E2) & ~np.isnan(nW), nW - E2, np.nan); TAB["real_seconds"] = real
    TAB["real_status"] = np.where(~same_next, "no next row", np.where(np.isnan(E2), "unmeasured: this row has no end stamp", np.where(np.isnan(nW), "unmeasured: the next row has no start stamp",
                                  np.where(real < 0, "FAILURE: negative real seconds", "measured"))))
    TAB["tb2"] = [("last 2:00 of the game" if a_ == 4 and b_ <= 120 else e1.time_bin(a_, b_)) if not np.isnan(b_) else "clock missing" for a_, b_ in zip(q2, c2)]
    section("table: the three times")

    print("\n=== e (TABLE CHECKS that save first): saved, reloaded at its sha, the one-byte plant ===")
    TAB.to_csv(OUT_TABLE, index=False); TSHA = sh(OUT_TABLE)
    print(f"  {TABLE_VERSION} saved to {OUT_TABLE if not FIXTURE else '(a scratch folder: quick run)'} | file sha {TSHA} | rows {len(TAB)} | games {TAB['game_id'].nunique()} (the older table replaced: no older version kept)")
    STRCOLS = ["game_id", "act", "state", "provenance", "next_act", "posteam", "defteam", "timeout_team", "next_timeout_team", "home", "away", "review", "other_kind",
               "next_other_kind", "text", "tb2", "transition", "real_status", "family", "next_family", "s_off", "s_how", "chal_team", "qs_off", "s_unk", "qs_unk",
               "fsort", "fname", "kind", "act_rec"]
    def load_table(path, want):
        got = sh(path)
        if got != want: raise record.GAP(f"the table at {path} is {got}, not {want}: refused")
        return pd.read_csv(path, dtype={c_: str for c_ in STRCOLS}, keep_default_na=True, low_memory=False)
    pl_dir = tempfile.mkdtemp(); pl_path = os.path.join(pl_dir, "interval_table.csv"); raw_ = bytearray(open(OUT_TABLE, "rb").read())
    k_ = len(raw_) // 2; raw_[k_] = ord("7") if raw_[k_] != ord("7") else ord("8"); open(pl_path, "wb").write(bytes(raw_))
    try: load_table(pl_path, TSHA); plant_byte = False; print("  plant (one byte changed): NOT REFUSED")
    except record.GAP as ex_: plant_byte = True; print(f"  plant (one byte changed at byte {k_}): REFUSED as it must ({ex_})")
    shutil.rmtree(pl_dir)
    TB = load_table(OUT_TABLE, TSHA); reload_ok = len(TB) == len(TAB)
    for c_ in ("s_kick", "inc_flag", "inc_text", "pen_flag", "pen_text", "pen_caps", "qs_first", "qs_kick"): TB[c_] = TB[c_].astype(str).str.lower().eq("true")
    print(f"  reloaded at sha {TSHA}: rows {len(TB)} -> {'the race reads this' if reload_ok else 'ROW COUNT DIFFERS'}")
    section("table: saved, reloaded, plant")



    print("\n=== coverage (from the saved table) ===")
    print(f"  rows by act: {dict(Counter(TB['act']))}")
    snm = TB["act"] == "snap"; unk = TB["state"] == UNK_NAME
    print(f"  {UNK_NAME} (disagreement between two readings that share rules.clock_class): snaps {int((unk & snm).sum())} of {int(snm.sum())} | fouls {int((unk & (TB['act'] == 'foul')).sum())}")
    print(f"  what disagreed: {dict(Counter(p.split('; disagree on ')[-1] if 'disagree on' in str(p) else str(p) for p in TB.loc[unk, 'provenance']).most_common(12))}")
    print(f"  failures kept: negative real {int((TB['real_status'] == 'FAILURE: negative real seconds').sum())} | clock corrections {int((TB['transition'] == 'clock correction').sum())}"
          f" | clock missing {int((TB['transition'] == 'clock missing').sum())}")
    section("table: coverage")
    wq = TB[TB["act"] == "two-minute warning"]
    w_dup = int((wq.groupby(["game_id", "q"]).size() > 1).sum()); w_else = int((~wq["q"].isin([2, 4])).sum())
    CHECKS = {"every play-clock pin holds": pins_ok, "every play-clock pin plant refused": plants_ok, "every warning pin holds and its plants refused": warn_ok,
              "Rule 11 Section 6 read in every played season's book, its plants refused": SCRIM_OK, "the transition's known-right cases pass and its plants fail": TRANS_OK,
              "the saved file reloads at its sha": reload_ok, "the one-byte plant refused": plant_byte, "no quarter with two warnings": w_dup == 0, "no warning outside quarters 2 and 4": w_else == 0}
    print(f"\n=== TABLE CHECKS (any failing stops the chain: nothing below reads a table that fails them) ===\n  {CHECKS}")
    section("table checks")
    if not all(CHECKS.values()): stop("a table check failed; nothing below runs")
except SystemExit:
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; nothing written to the product")

try:
    import math, transition as T_
    print("\n=== v19 o: the books in rules/ (the full books the run reads), their line counts, and where Rule 14 and Rule 15 are found by heading ===")
    RULE_N = lambda B, n: [k for k, l in enumerate(B.L) if RULE_LINE.match(l) and RULE_LINE.match(l).group(2) == str(n)]
    for bk, B in sorted(BOOKS.items()):
        if B is None: print(f"  {bk}: MISSING"); continue
        r14, r15 = RULE_N(B, 14), RULE_N(B, 15)
        print(f"  {bk}: {B.f} | lines {len(B.L)} | Rule 14 heading lines {len(r14)} (first {[z + 1 for z in r14[:4]]}) | Rule 15 heading lines {len(r15)} (first {[z + 1 for z in r15[:4]]})"
              + ("" if (r14 and r15) else " | NOT FOUND: " + " and ".join(x_ for x_, h_ in (("Rule 14", r14), ("Rule 15", r15)) if not h_)))

    print("  (v19 part 2: c and d's articles were printed in full by part 1, chain e2b_v19_741675793183; not reprinted here)")
    NORM = lambda s_: re.sub(r"\s+", " ", str(s_)).strip()
    print("\n=== v19 k: every Penalty: line of each book, split into its 'For <foul>: <penalty>' parts; the yards each names (Loss of N yards); the half-the-")
    print("    distance sentences printed where found ===")
    YW = {"five": 5, "ten": 10, "fifteen": 15, "twenty": 20}
    def pen_parts(B):
        """Each Penalty: line with the lines after it up to the next Penalty, Note, Item, Exception, article or section line (at most 4 more), split at
        each 'For ': (line, the foul's words, the penalty's words, the yards named, an automatic first down named, the spot of the foul named)."""
        out = []
        for j, l in enumerate(B.L):
            if not re.match(r"^\s*Penalty\s*:", l, re.I): continue
            blk = [l]
            for z in range(j + 1, min(j + 5, len(B.L))):
                if re.match(r"^\s*(Penalty|Note|Item|Exception|ARTICLE|Article|SECTION|Section|RULE|Rule|\(\w\))", B.L[z]): break
                blk.append(B.L[z])
            txt_ = NORM(" ".join(blk)); txt_ = re.sub(r"^Penalty\s*:\s*", "", txt_, flags=re.I)
            for seg in re.split(r"(?<=[.;])\s+(?=For\s)", txt_):
                m = re.match(r"For\s+(.{2,220}?):\s*(.*)$", seg)
                if not m: out.append((j + 1, "", seg, [], False, False)); continue
                pw = m.group(2).lower()
                yds = [int(y_) if y_.isdigit() else YW[y_] for y_ in re.findall(r"loss of (\d+|five|ten|fifteen|twenty) yards?", pw)]
                out.append((j + 1, m.group(1), m.group(2), yds, "automatic first down" in pw, bool(re.search(r"spot of (the )?foul", pw))))
        return out
    PEN = {bk: pen_parts(B) for bk, B in BOOKS.items() if B is not None}
    for bk in sorted(PEN):
        B = BOOKS[bk]; hd_ = [z for z, l in enumerate(B.L) if re.search(r"half the distance", l, re.I)]
        print(f"  {bk}: Penalty: parts {len(PEN[bk])} | naming yards {sum(1 for x_ in PEN[bk] if x_[3])} | 'half the distance' lines {len(hd_)}: "
              + " || ".join(f"L{z + 1}: {NORM(B.L[z])[:150]}" for z in hd_[:4]))
    # the foul names on the record's standing and wiped rows, each with the words its Penalty: part is searched by (printed with every match); v19 part 2 (3):
    # the eight part 1 did not find searched again by the book's own wording, read from part 1's printed articles where it printed them
    KW = {"Offensive Holding": r"\bholding\b", "Defensive Holding": r"\bholding\b", "Offensive Pass Interference": r"pass interference",
          "Roughing the Passer": r"roughing (the )?passer", "Unnecessary Roughness": r"unnecessary roughness",
          "Face Mask": r"face ?mask|mask or helmet opening",   # part 1's printed article: 'For twisting, turning, pushing, pulling, or controlling the mask or helmet opening: Loss of 15 yards'
          "Illegal Block Above the Waist": r"block(ing)? above the waist|illegal block", "Illegal Use of Hands": r"use of hands", "Horse Collar Tackle": r"horse-? ?collar",
          "Intentional Grounding": r"grounding", "Illegal Contact": r"illegal contact", "Defensive Offside": r"\boffside\b", "Offensive Offside": r"\boffside\b|encroach",
          "Ineligible Downfield Pass": r"ineligible", "Illegal Formation": r"formation", "Unsportsmanlike Conduct": r"unsportsmanlike", "Taunting": r"taunt",
          "Lowering the Head to Initiate Contact": r"lower(s|ing)? (the|his) head|initiat(e|es|ing) contact with (the|his) helmet",
          "Illegal Blindside Block": r"blindside", "Low Block": r"low block|below the waist", "Chop Block": r"chop block", "Clipping": r"clipping", "Tripping": r"tripping",
          "Illegal Shift": r"\bshift\b", "Illegal Motion": r"\bmotion\b", "Neutral Zone Infraction": r"neutral zone", "Encroachment": r"encroach",
          "Defensive Too Many Men on Field": r"too many|12 (or more )?players|more than 11 players", "Offensive Too Many Men on Field": r"too many|12 (or more )?players|more than 11 players",
          "Delay of Game": r"delay", "Defensive Delay of Game": r"delay", "False Start": r"false start", "Disqualification": r"disqualif",
          "Illegal Forward Pass": r"forward pass", "Illegal Substitution": r"substitut", "Hip Drop Tackle": r"hip-? ?drop", "Roughing the Kicker": r"roughing (the )?(kicker|holder)",
          "Running Into the Kicker": r"running into", "Illegal Touch Pass": r"illegal touch|touch(es|ed|ing)? .{0,40}forward pass", "Leaping": r"leap", "Leverage": r"leverage"}
    OFFW = r"by (the |an? )?offen|offensive|team a\b"; DEFW = r"by (the |a )?defen|defensive|team b\b"
    _CC = {}
    def cands(bk, name, side):
        """The Penalty: parts for one foul by one side in one book: the parts its words match; where some name a side, those naming the other side dropped."""
        if (bk, name, side) not in _CC:
            rx = KW.get(name, re.escape(str(name).lower())); P_ = [x_ for x_ in PEN.get(bk, []) if re.search(rx, x_[1].lower())]
            own_, oth_ = (OFFW, DEFW) if side == "offense" else (DEFW, OFFW)
            if any(re.search(own_, x_[1].lower()) for x_ in P_): P_ = [x_ for x_ in P_ if not re.search(oth_, x_[1].lower()) or re.search(own_, x_[1].lower())]
            _CC[(bk, name, side)] = P_
        return _CC[(bk, name, side)]

    ART_RX = re.compile(r"^\s*ARTICLE\s+\d+", re.I); _AH = {}; _AC = {}; ART_USED = {}
    def art_cands(bk, name, side):
        """v19 s5: a family no Penalty: part names: the Penalty: parts of the articles whose text names it (its words, KW; Disqualification by an article's
        heading only, since 'disqualified' is written in many penalties), the side filter as cands; each article's naming line kept for the printout."""
        if (bk, name, side) in _AC: return _AC[(bk, name, side)]
        B = BOOKS.get(bk); out = []; hits = []
        if B is not None and bk in PEN:
            if bk not in _AH: _AH[bk] = [z for z, l in enumerate(B.L) if ART_RX.match(l)]
            H = _AH[bk]; rx = KW.get(name, re.escape(str(name).lower()))
            zs = [z for z, l in enumerate(B.L) if re.search(rx, l.lower()) and (name != "Disqualification" or ART_RX.match(l))]
            for z in zs:
                a = max([h for h in H if h <= z], default=None)
                if a is None: continue
                b = min([h for h in H if h > z], default=len(B.L))
                new_ = [x_ for x_ in PEN[bk] if a < x_[0] - 1 < b and x_[3] and x_ not in out]
                if new_: hits.append((z + 1, NORM(B.L[z])[:140], a + 1, [(x_[0], x_[2][:80]) for x_ in new_])); out += new_
            own_, oth_ = (OFFW, DEFW) if side == "offense" else (DEFW, OFFW)
            if any(re.search(own_, x_[1].lower()) for x_ in out): out = [x_ for x_ in out if not re.search(oth_, x_[1].lower()) or re.search(own_, x_[1].lower())]
        _AC[(bk, name, side)] = out; ART_USED[(bk, name, side)] = hits
        return out
    cands_all = lambda bk, name, side: cands(bk, name, side) or art_cands(bk, name, side)

    print("\n=== v19 k, part 2: the record check by family, its yards from each row's own enforcement spot; each family's Penalty: part chosen by the record ===")
    print("  (the part whose yards reproduce the most rows' penalty_yards, then whose automatic first down agrees with the most rows' first_down_penalty: a choice")
    print("   read from the record, declared; DPI by its own article below; a family no book part names stays NOT FOUND and its fouls are UNSUPPORTED when drawn)")
    kr_ = []
    ayv = d["air_yards"].to_numpy(float) if "air_yards" in d.columns else np.full(n, np.nan)
    for i in np.where(((act == "snap") & mC) | (fsort == "1 down, play wiped"))[0]:
        t_ = txt0.iat[i]; acc_ = [c_ for c_ in r4.foul_clauses(t_) if c_[1]]
        if len(acc_) != 1: continue
        nm_ = d.at[i, "penalty_type"]; ptm_ = d.at[i, "penalty_team"]; py_ = d.at[i, "penalty_yards"]
        if not (isinstance(nm_, str) and isinstance(ptm_, str) and isinstance(pos[i], str)): continue
        sp_ = L.enforced_at(t_[acc_[0][2]:acc_[0][3]], pos[i])
        kr_.append((i, nm_, "offense" if ptm_ == pos[i] else "defense", sp_, py_, rules.RULE_BOOK_OF[int(seas[i])][0], "standing" if fsort[i] != "1 down, play wiped" else "wiped",
                    d.at[i, "first_down_penalty"] == 1, int(seas[i]), ayv[i], ylv0[i]))
    fam_rows = defaultdict(list)
    for r_ in kr_: fam_rows[(r_[1], r_[2])].append(r_)
    print(f"  rows {len(kr_)} (standing {sum(1 for r_ in kr_ if r_[6] == 'standing')}, wiped {sum(1 for r_ in kr_ if r_[6] == 'wiped')}) | families {len(fam_rows)}")
    HALF_ROWS = []; CHOICE = {}; KREC = {}
    for (nm_, side_), R_ in sorted(fam_rows.items(), key=lambda z: -len(z[1])):
        if nm_ == "Defensive Pass Interference" and side_ == "defense": continue
        ok_rows = [r_ for r_ in R_ if r_[3] is not None and not nanv(r_[4])]
        score = defaultdict(lambda: [0, 0, 0, None])   # (N, first down) -> [rows its book holds, yards reproduced, award agreeing, a line]
        for r_ in ok_rows:
            for x_ in cands_all(r_[5], nm_, side_):   # v19 s5: the article that names the family where no Penalty: part does
                for N in set(x_[3]):
                    sc_ = score[(N, x_[4])]; sc_[0] += 1; sc_[3] = sc_[3] or f"{r_[5]} L{x_[0]}"
                    sc_[1] += int(any(abs(T_.foul_yards(N, side_, r_[3], m_) - r_[4]) < 0.5 for m_ in ("floor", "ceil", "exact")))   # the half marked any of the three ways
                    sc_[2] += int(bool(x_[4]) == bool(r_[7]))
        if not score:
            KREC[(nm_, side_)] = dict(rows=len(R_), found=False)
            print(f"  {nm_} | {side_}: rows {len(R_)} | NOT FOUND: no Penalty: part names its yards, and no article naming it holds one (searched '{KW.get(nm_, nm_.lower())}') -> UNSUPPORTED when drawn"); continue
        best = max(score.items(), key=lambda kv: (kv[1][1], kv[1][2]))
        (N, fd), (nb_, ny_, na_, ln_) = best
        CHOICE[(nm_, side_)] = (N, fd)
        exact_ = [r_ for r_ in ok_rows if abs(T_.foul_yards(N, side_, r_[3], "exact") - r_[4]) < 0.5]
        halfr_ = [r_ for r_ in ok_rows if N > ((100 - r_[3]) / 2 if side_ == "offense" else r_[3] / 2)]
        HALF_ROWS += [(r_, N, side_) for r_ in halfr_]
        miss_ = [r_ for r_ in ok_rows if r_ not in halfr_ and abs(N - r_[4]) >= 0.5]
        KREC[(nm_, side_)] = dict(rows=len(R_), found=True, N=N, fd=fd, exact=len(exact_), read=len(ok_rows), half=len(halfr_), miss=len(miss_))
        print(f"  {nm_} | {side_}: rows {len(R_)} (spot and yards read {len(ok_rows)}) | chosen: {N} yards{', an automatic first down' if fd else ''} ({ln_}) | its yards reproduce"
              f" {share(len(exact_), len(ok_rows))} exactly | rows past half the distance {len(halfr_)} | rows not past half the distance and not {N} yards {len(miss_)}"
              + (f" e.g. {[(gid[r_[0]], int(d.at[r_[0], 'order_sequence']), r_[3], r_[4]) for r_ in miss_[:3]]}" if miss_ else "")
              + f" | the award against first_down_penalty: agrees {share(na_, nb_)}" + (" | others: " + "; ".join(f"{k_[0]} yds{' +1st' if k_[1] else ''}: {v_[1]} of {v_[0]}" for k_, v_ in score.items() if k_ != (N, fd)) if len(score) > 1 else ""))
    print("  k, half the distance (14-1-1's rule, the book's sentences printed above): how the record marks a half that is not whole, on the rows where the")
    print("  chosen yards pass half the distance from the row's own spot (each family's chosen part):")
    HC = Counter()
    for r_, N, side_ in HALF_ROWS:
        hv_ = ((100 - r_[3]) if side_ == "offense" else r_[3]) / 2
        HC["rows"] += 1; HC["floor"] += int(abs(math.floor(hv_) - r_[4]) < 0.5); HC["ceil"] += int(abs(math.ceil(hv_) - r_[4]) < 0.5); HC["exact"] += int(abs(hv_ - r_[4]) < 0.01)
        HC["the half whole"] += int(hv_ == int(hv_))
    print(f"    rows {HC['rows']} (the half a whole yard on {HC['the half whole']}) | the record's penalty_yards equals: the half marked down {share(HC['floor'], HC['rows'])}"
          f" | marked up {share(HC['ceil'], HC['rows'])} | the exact half {share(HC['exact'], HC['rows'])}")
    nw_ = HC["rows"] - HC["the half whole"]
    if HC["rows"]:
        frac_ = [(r_, N, side_) for r_, N, side_ in HALF_ROWS if (((100 - r_[3]) if side_ == "offense" else r_[3]) / 2) % 1]
        fc_ = Counter()
        for r_, N, side_ in frac_:
            hv_ = ((100 - r_[3]) if side_ == "offense" else r_[3]) / 2
            fc_["floor"] += int(abs(math.floor(hv_) - r_[4]) < 0.5); fc_["ceil"] += int(abs(math.ceil(hv_) - r_[4]) < 0.5); fc_["exact"] += int(abs(hv_ - r_[4]) < 0.01)
        print(f"    where the half is not whole ({len(frac_)} rows): marked down {fc_['floor']} | marked up {fc_['ceil']} | the exact half {fc_['exact']} (a read of the record's marking:")
        print("    no one marking explains these rows, so v19 r removes part 2's rounding rule: the engine enforces half the distance exactly as the article sets it,")
        print("    and a half-yard spot, which the engine does not place, is UNSUPPORTED when drawn, counted)")
    print("\n=== v19 r1: pass interference by the defense, a spot foul ('First down for the offensive team at the spot of the foul'): its depth is each wiped")
    print("    row's penalty_yards from its line; where the ball went to the 1 (or half the distance inside the 2) the depth is censored, counted, never drawn as a depth ===")
    DPI_CITE = {}
    for bk in sorted(BOOKS):
        B = BOOKS[bk]
        if B is None: continue
        hz_ = [z for z in range(len(B.L)) if re.search(r"one.{0,2}yard line,? or half the dis", NORM(B.L[z] + " " + (B.L[z + 1] if z + 1 < len(B.L) else "")), re.I)]
        hz_ = [z for z in hz_ if re.search(r"pass interference|spot foul|end zone", NORM(" ".join(B.L[max(z - 4, 0):z + 2])), re.I)]
        DPI_CITE[bk] = hz_[0] + 1 if hz_ else None
        print(f"  {bk}: the end-zone sentence (the 1-yard line or half the distance, whichever is more beneficial) "
              + (f"L{hz_[0] + 1}: {NORM(' '.join(B.L[max(hz_[0] - 2, 0):hz_[0] + 2]))[:300]}" if hz_ else "NOT FOUND (no line names the 1-yard line or half the distance beside pass interference)"))
    HALF_CITE = {}
    for bk in sorted(BOOKS):
        B = BOOKS[bk]
        if B is None: continue
        hz_ = [z for z, l in enumerate(B.L) if re.search(r"half the distance (from the spot of enforcement )?to the offender|offender.{0,3}s goal line", NORM(l), re.I)]
        HALF_CITE[bk] = hz_[0] + 1 if hz_ else None
        print(f"  {bk}: v19 r2, the half-the-distance article (a distance penalty never carries the ball more than half the distance to the offender's goal) "
              + (f"L{hz_[0] + 1}: {NORM(' '.join(B.L[max(hz_[0] - 1, 0):hz_[0] + 2]))[:300]}" if hz_ else "NOT FOUND by its wording ('half the distance to the offender', 'offender's goal line')"))
    pdx_ = np.where((fsort == "1 down, play wiped") & (d["penalty_type"].to_numpy(object) == "Defensive Pass Interference")
                    & (d["penalty_team"].to_numpy(object) != pos))[0]
    pyv_ = pd.to_numeric(d["penalty_yards"], errors="coerce").to_numpy(float)
    rd_ = Counter()
    for i in pdx_:
        if nanv(pyv_[i]) or nanv(ylv0[i]): rd_["penalty_yards or the line unread"] += 1
        elif pyv_[i] >= ylv0[i] - 1: rd_["censored: the ball at the 1 or half the distance inside the 2 (depth at least the line less one)"] += 1
        else: rd_["uncensored: the depth read"] += 1
    print(f"  the record's wiped rows with pass interference by the defense: {len(pdx_)} | {dict(rd_)}")
    unc_ = [pyv_[i] for i in pdx_ if not nanv(pyv_[i]) and not nanv(ylv0[i]) and pyv_[i] < ylv0[i] - 1]
    if unc_: print(f"    the uncensored depths: median {np.median(unc_):.0f} | p10 {np.percentile(unc_, 10):.0f} | p90 {np.percentile(unc_, 90):.0f} | at most 0 (not beyond the line) {sum(1 for v_ in unc_ if v_ <= 0)}")
    both_ = [i for i in np.where(~np.isnan(ayv) & ~np.isnan(pyv_) & (d["penalty_type"].to_numpy(object) == "Defensive Pass Interference"))[0]]
    if not both_:
        print("  record check (the spot from penalty_yards against air_yards where both are read): NOT MEASURED: 0 rows with pass interference by the defense carry both"
              " (the record writes no pass length on these rows, so the depth cannot be checked against one)")
    else:
        ag_ = sum(1 for i in both_ if abs(min(ayv[i], max(ylv0[i] - 1, ylv0[i] / 2)) - pyv_[i]) < 0.5)
        print(f"  record check (the spot from air_yards, the end zone by the article, against penalty_yards, where both are read): {share(ag_, len(both_))}")
    BOOKY = {}
    for s in S:
        bk_ = rules.RULE_BOOK_OF[s][0]
        for (nm_, side_), (N, fd) in CHOICE.items():
            hit_ = [x_ for x_ in cands_all(bk_, nm_, side_) if N in x_[3] and bool(x_[4]) == bool(fd)]
            if hit_: BOOKY[(s, nm_, side_)] = (N, bool(fd), f"{bk_} book L{hit_[0][0]}: For {hit_[0][1][:60]}: {hit_[0][2][:60]}")
    nf_ = sorted({k_ for k_, v_ in KREC.items() if not v_["found"]}, key=lambda z: -KREC[z]["rows"])
    print(f"\n  k: the families built for the engine (BOOKY, by season's book): {len({(k_[1], k_[2]) for k_ in BOOKY})} families, {len(BOOKY)} season entries | NOT FOUND, UNSUPPORTED when drawn:"
          f" {[(k_, KREC[k_]['rows']) for k_ in nf_]}")
    for (nm_, side_) in sorted({(k_[1], k_[2]) for k_ in BOOKY}):
        ss_ = [s for s in S if (s, nm_, side_) in BOOKY]
        print(f"    {nm_} by the {side_}: {BOOKY[(ss_[0], nm_, side_)][0]} yards{' +an automatic first down' if BOOKY[(ss_[0], nm_, side_)][1] else ''} | seasons {ss_} | {BOOKY[(ss_[0], nm_, side_)][2]}")
    print("\n=== v19 s5: the families no Penalty: part names, searched in the articles that name them (each article's own Penalty: lines; the part chosen by the")
    print("    record as k chooses, declared), by season's book, cited by line ===")
    for (nm_, side_), v_ in sorted(KREC.items(), key=lambda z: -z[1]["rows"]):
        if any(cands(rules.RULE_BOOK_OF[s][0], nm_, side_) for s in S): continue   # named by a Penalty: part itself (k above)
        print(f"  {nm_} by the {side_} (rows {v_['rows']}): " + ("chosen " + f"{v_['N']} yards{', an automatic first down' if v_['fd'] else ''} | its yards reproduce {share(v_['exact'], v_['read'])}" if v_["found"] else "NOT FOUND in any season's book"))
        for bk in sorted({rules.RULE_BOOK_OF[s][0] for s in S}):
            art_cands(bk, nm_, side_); h_ = ART_USED.get((bk, nm_, side_), [])
            ss_ = [s for s in S if rules.RULE_BOOK_OF[s][0] == bk]
            print(f"    {bk} book (seasons {ss_}): " + (" || ".join(f"L{z_} '{tx_}' -> its article (from L{a_}): " + "; ".join(f"L{l_} {p_}" for l_, p_ in ps_) for z_, tx_, a_, ps_ in h_[:3])
                                                         if h_ else "NOT FOUND (no article naming it holds a Penalty: line with yards): UNSUPPORTED when drawn")
                  + (f" | built: {BOOKY[(ss_[0], nm_, side_)][2]}" if (ss_[0], nm_, side_) in BOOKY else " | not built for these seasons"))

    print("\n=== v19 s1: how the record marks a spot half the distance puts on a half yard (the next down's yard line, same offense; the owner's ruling (a): the")
    print("    engine keeps the exact spot and writes the record's columns rounded toward the goal the offense attacks) ===")
    HM = Counter()
    for r_ in kr_:
        i, sp_, py_ = r_[0], r_[3], r_[4]
        if sp_ is None or nanv(py_) or py_ <= 0: continue
        dist_ = (100 - sp_) if r_[2] == "offense" else sp_
        if dist_ % 2 != 1 or dist_ > 29 or abs(2 * py_ - dist_) > 1: continue
        j = nsp[i]
        if j < 0 or pos[j] != pos[i]: HM["no next down by the same offense"] += 1; continue
        ex_ = sp_ + dist_ / 2 if r_[2] == "offense" else sp_ - dist_ / 2
        HM["toward the attacked goal" if ylv0[j] == math.floor(ex_) else ("away from it" if ylv0[j] == math.ceil(ex_) else "neither")] += 1
    nh_ = HM["toward the attacked goal"] + HM["away from it"] + HM["neither"]
    HALF_MARK_SHARE = share(HM["toward the attacked goal"], nh_)
    print(f"  t2, both rounding shares side by side (the next down's yard line rounded toward the goal the offense attacks):")
    print(f"    the read before s (every penalty row with one accepted foul): 0.8706 (666 of 765) | away from it 99 | neither 0")
    print(f"    this run (the rows k reads: passes, runs and wiped downs with one accepted foul): {HALF_MARK_SHARE} | away from it {HM['away from it']} | neither"
          f" {HM['neither']} | no next down by the same offense {HM['no next down by the same offense']} (s's run printed 0.840, 489 of 582)")

    print("\n=== v19 s3: the Dead Ball Foul article (the offense's unnecessary roughness on a play that stands, enforced at its end: the down counts), by line ===")
    for bk in sorted(BOOKS):
        B = BOOKS[bk]
        if B is None: continue
        hz_ = [z for z, l in enumerate(B.L) if re.search(r"dead ball foul and foul between downs", l, re.I)]
        dc_ = [z for z in range(len(B.L)) if re.search(r"enforced from the succeeding spot,? and the down counts", NORM(B.L[z] + " " + (B.L[z + 1] if z + 1 < len(B.L) else "")), re.I)]
        print(f"  {bk}: the article's heading " + (f"L{hz_[0] + 1}" if hz_ else "NOT FOUND") + " | 'enforced from the succeeding spot, and the down counts' "
              + (f"L{dc_[0] + 1}: {NORM(' '.join(B.L[dc_[0]:dc_[0] + 2]))[:200]}" if dc_ else "NOT FOUND"))

    print("\n=== v19 s4 (a read, nothing enforced): a foul with a score or a change of possession: each season's articles by line, and the record's change-of-")
    print("    possession rows' next snap against the candidate articles ===")
    S4_RX = {"the succeeding spot after a touchdown is the next kickoff": r"succeeding spot for a foul that occurs after a touchdown",
             "enforced on the succeeding kickoff or Try": r"enforced on the (succeeding )?kickoff or (the )?try",
             "Item 1: after a dead ball foul by Team A, first-and-10": r"it will be first-and-10 for team a",
             "a foul between downs: first-and-25": r"first-and-25", "a change of possession (the article's words)": r"change of possession.{0,60}(foul|penalt)"}
    for bk in sorted(BOOKS):
        B = BOOKS[bk]
        if B is None: continue
        parts_ = []
        for k_, rx_ in S4_RX.items():
            hz_ = [z for z in range(len(B.L)) if re.search(rx_, NORM(B.L[z] + " " + (B.L[z + 1] if z + 1 < len(B.L) else "")), re.I)]
            parts_.append(f"{k_}: " + (", ".join(f"L{z + 1}" for z in hz_[:4]) if hz_ else "NOT FOUND"))
        print(f"  {bk}: " + " | ".join(parts_))
    int_, fum_, pen_ = one("interception"), one("fumble_lost"), one("penalty")
    S4C = Counter(); S4X = []
    for i in np.where(pen_ & (int_ | fum_) & (act == "snap"))[0]:
        acc_ = [c_ for c_ in r4.foul_clauses(txt0.iat[i]) if c_[1]]
        if len(acc_) != 1 or not isinstance(pos[i], str): S4C[("not one accepted foul", "")] += 1; continue
        who_ = "by the team that snapped" if d.at[i, "penalty_team"] == pos[i] else "by the other team"; j = nsp[i]
        if j < 0 or gid[j] != gid[i]: S4C[(who_, "no next snap")] += 1; continue
        k_ = ("1st and 10" if (dn[j] == 1 and tgv0[j] == 10) else ("1st and 25" if (dn[j] == 1 and tgv0[j] == 25) else ("1st and goal" if (dn[j] == 1 and tgv0[j] == ylv0[j]) else f"{'1st' if dn[j] == 1 else 'not 1st'} and {tgv0[j]:.0f}")))
        S4C[(who_, k_)] += 1
        if len(S4X) < 6 and k_ not in ("1st and 10", "1st and goal"): S4X.append((gid[i], int(d.at[i, "order_sequence"]), who_, k_, txt0.iat[i][:120]))
    print(f"  the record's passes and runs with a foul and an interception or a fumble lost: {int((pen_ & (int_ | fum_) & (act == 'snap')).sum())} | the next snap by"
          f" the team that fouled and its down and distance: {dict(sorted(S4C.items()))}")
    for x_ in S4X: print(f"    e.g. {x_}")
    section("v19 o, c, d, k: the books searched; k's record check")
except (SystemExit, Overtime):
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; the table is saved")

try:
    import csv
    print("\n=== y0 (b), y1: Rule 4's play-clock articles (Section 6 Articles 1 and 2) and the article that starts the game clock after a foul (Section 3 Article 2,")
    print("    the scrimmage down) printed whole for each played season's book, every line numbered, each found by its heading (the first heading line of Article 1")
    print("    with Article 2 of the 25-second clock within 40 lines after it; the scrimmage-down Article 2 the last before them); an article runs to the next")
    print("    article, section or rule heading (page numbers and page headers inside it printed as they stand) ===")
    RX40 = re.compile(r"(?i)^\s*article\s+1\.\s+40-second play clock"); RX25 = re.compile(r"(?i)^\s*article\s+2\.\s+25-second play clock")
    RXSD = re.compile(r"(?i)^\s*article\s+2\.\s+scrimmage down"); RXH = re.compile(r"(?i)^\s*(article\s+\d+\.|section\s+\d+\b|rule\s+\d+\s+[a-z]{3,}|se\s*$)")
    PCT = {r_["book"]: r_ for r_ in csv.DictReader(open("rules/play_clock_pins.tsv"), delimiter="\t")} if os.path.exists("rules/play_clock_pins.tsv") else {}
    def art_lines(Lb, z0, cap=80):
        """The article from its heading line z0 to the line before the next heading (at most cap lines): [(line number, text)]."""
        out = [(z0 + 1, Lb[z0])]
        for z in range(z0 + 1, min(z0 + cap, len(Lb))):
            if RXH.match(Lb[z]): break
            out.append((z + 1, Lb[z]))
        return out
    ARTS = {}
    for bk in sorted({rules.RULE_BOOK_OF[s][0] for s in S}):
        B = BOOKS.get(bk)
        if B is None: print(f"  the {bk} book: MISSING: its articles NOT FOUND"); ARTS[bk] = None; continue
        Lb = [str(l_) for l_ in B.L]
        a1 = [z for z, l_ in enumerate(Lb) if RX40.search(l_)]; a2 = [z for z, l_ in enumerate(Lb) if RX25.search(l_)]
        pr_ = [(x_, y_) for x_ in a1 for y_ in a2 if 0 < y_ - x_ <= 40]
        sd = [z for z, l_ in enumerate(Lb) if RXSD.search(l_)]
        pin_ = PCT.get(bk, {}).get("location", "no pin row"); m_ = re.search(r"L(\d+) article 1", pin_); tsv1_ = int(m_.group(1)) if m_ else None
        pick_ = [p_ for p_ in pr_ if p_[0] + 1 == tsv1_] or pr_[-1:]   # the pair the pinned tsv names; else the last (a contents page comes first)
        z40, z25 = pick_[0] if pick_ else (None, None); zsd = max([z for z in sd if z40 is not None and z < z40], default=None)
        print(f"\n  the {bk} book ({B.f}, {len(Lb)} lines; seasons {[s for s in S if rules.RULE_BOOK_OF[s][0] == bk]}): Article 1 headings at {[z + 1 for z in a1]}, Article 2 (25-second)"
              f" at {[z + 1 for z in a2]}, scrimmage-down Article 2 at {[z + 1 for z in sd]} | rules/play_clock_pins.tsv's lines for this book: {pin_}"
              f" | Article 1 printed from L{z40 + 1 if z40 is not None else '-'} ({'the line the tsv names' if (z40 is not None and z40 + 1 == tsv1_) else 'NOT the line the tsv names'})")
        ARTS[bk] = {}
        for nm_, z_ in (("Rule 4 Section 3 Article 2 (the scrimmage down; item (e): the game clock after a foul)", zsd), ("Rule 4 Section 6 Article 1 (the 40-second play clock)", z40),
                        ("Rule 4 Section 6 Article 2 (the 25-second play clock)", z25)):
            if z_ is None: print(f"  --- {nm_}: NOT FOUND by its heading ---"); ARTS[bk][nm_] = None; continue
            al_ = art_lines(Lb, z_); ARTS[bk][nm_] = al_
            print(f"  --- {nm_}: lines {al_[0][0]}-{al_[-1][0]} ---")
            for ln_, tx_ in al_: print(f"  L{ln_}: {tx_}")
    print("\n  y1, read from the articles above (each season; a sentence not found is NOT FOUND and the season's play clock after an enforcement is unread):")
    J_ = lambda al_: re.sub(r"\s+", " ", " ".join(tx_ for _, tx_ in al_)) if al_ else ""
    def where_(al_, rx):
        return [ln_ for ln_, tx_ in al_ if re.search(rx, tx_)] if al_ else []
    ENF_CLOCK = {}; Y1_READ = {}
    for s in S:
        bk = rules.RULE_BOOK_OF[s][0]; A_ = ARTS.get(bk) or {}
        sd_ = A_.get("Rule 4 Section 3 Article 2 (the scrimmage down; item (e): the game clock after a foul)"); a1_ = A_.get("Rule 4 Section 6 Article 1 (the 40-second play clock)")
        a2_ = A_.get("Rule 4 Section 6 Article 2 (the 25-second play clock)")
        e_ = re.search(r"(?:\(e\)\s*)?If the game clock is stopped.{0,200}?the game clock will start as if the foul had not occurred", J_(sd_), re.I)
        n25 = re.search(r"a team will have\s+(\d+)\s+seconds?,?\s+beginning with the Referee.s whistle", J_(a2_), re.I)
        pen_ = where_(a2_, r"(?i)penalty enforcement"); even_ = where_(a2_, r"(?i)even if the 40-second clock is already counting down")
        n40 = re.search(r"(\d+)-second interval starts when a play ends", J_(a1_), re.I)
        Y1_READ[s] = dict(e=bool(e_), e_lines=where_(sd_, r"(?i)as if the foul had not occurred|game clock is stopped (before or )?after a down"), n25=int(n25.group(1)) if n25 else None,
                          n25_lines=where_(a2_, r"(?i)beginning with the Referee"), pen=pen_, even=even_, n40=int(n40.group(1)) if n40 else None, n40_lines=where_(a1_, r"(?i)starts when a play ends"))
        r_ = Y1_READ[s]
        if r_["e"] and r_["n25"] is not None and r_["pen"]:
            ENF_CLOCK[s] = (r_["n25"], f"the {bk} book: 4-6-2 L{r_['n25_lines'][0] if r_['n25_lines'] else '?'} ({r_['n25']} seconds beginning with the Referee's whistle), its list L{r_['pen'][0]} (a penalty enforcement); 4-3-2(e) L{r_['e_lines'][0] if r_['e_lines'] else '?'}")
        else: ENF_CLOCK[s] = (None, f"the {bk} book: NOT FOUND: " + ", ".join(k_ for k_, v_ in (("4-3-2(e)'s start as if the foul had not occurred", r_["e"]), ("4-6-2's seconds from the whistle", r_["n25"] is not None), ("4-6-2's penalty enforcement", bool(r_["pen"]))) if not v_))
        print(f"  {s} ({bk} book): 4-3-2(e) 'following enforcement or declination of a penalty, the game clock will start as if the foul had not occurred' {'FOUND at L' + ', L'.join(map(str, r_['e_lines'])) if r_['e'] else 'NOT FOUND'}"
              f" | 4-6-2: {r_['n25'] if r_['n25'] is not None else 'NOT FOUND'} seconds beginning with the Referee's whistle (L{', L'.join(map(str, r_['n25_lines'])) or '-'}) after"
              f" 'a penalty enforcement' (L{', L'.join(map(str, pen_)) or ' NOT FOUND'}), 'even if the 40-second clock is already counting down' (L{', L'.join(map(str, even_)) or ' NOT FOUND'})"
              f" | 4-6-1: {r_['n40'] if r_['n40'] is not None else 'NOT FOUND'}-second interval from the play's end (L{', L'.join(map(str, r_['n40_lines'])) or '-'})")
    print("  the reading (y1): after a foul outside the windows the game clock is stopped for the enforcement and, a running clock, starts again on the Referee's signal")
    print("  (4-3-2(e): as if the foul had not occurred); the offense has the 25-second clock beginning with the Referee's whistle (4-6-2 (e), even if the 40-second")
    print("  clock was counting down): the game seconds from the restart to the snap are at most that play clock, not 4-6-1's 40 from the play's end.")
    print(f"  ENF_CLOCK (the engine's caller-set value, each season's book): {ENF_CLOCK}")
    section("y0 (b), y1: Rule 4's articles printed whole")
except (SystemExit, Overtime):
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; nothing written")

STAMPED = [s for s in S if s >= 2023]
STOP_ACTS = ["snap STOP", "snap PARTIAL", "foul", "kickoff", "try", "timeout", "two-minute warning", "start of the quarter"]
RUN_COLS = ["q", "ce", "diff", "down", "togo", "yl", "to_o", "to_d", "rv", "inj", "t"]
STOP_COLS = ["q", "clock", "diff", "down", "togo", "yl", "to_o", "to_d", "act", "rv", "inj"]


def make_ending(TBx, admin_hdr=True):
    """The corrected labels (v16 c, d; v17 b; v18 b) from a table: the ending a stretch's next row gives it. A no-play down is a snap (d); an administrative row
    (c's category 3) attaches to the foul it reports, so the next row after it decides; a distinct dead-ball foul (category 2) is F1 or F2 where the engine
    has them, else 'unplayed' by name; a kickoff or a Try is the engine's own act (c); UNKNOWN is never a training label. admin_hdr (v18 b): every row c
    sorts as category 3 is skipped, the game's opening header among them; False reads as v17 did (only the administrative foul rows skipped).
    Returns (ending, the next real row)."""
    A = TBx["act"].to_numpy(object); FS = TBx["fsort"].fillna("").to_numpy(object); FN = TBx["fname"].fillna("").to_numpy(object)
    FAM = TBx["family"].fillna("").to_numpy(object); OK_ = TBx["other_kind"].fillna("").to_numpy(object); TT_ = TBx["timeout_team"].to_numpy(object)
    GI = TBx["game_id"].to_numpy(object); nT = len(TBx)
    nxt_real = np.full(nT, -1); last_ = -1
    for i in range(nT - 1, -1, -1):
        if i + 1 < nT and GI[i + 1] != GI[i]: last_ = -1
        nxt_real[i] = last_
        if not (FS[i].startswith("3 ") if admin_hdr else FS[i] == "3 administrative"): last_ = i
    def ending(k, off):
        a_ = A[k]
        if a_ in ("kickoff", "try"): return "own act", f"the engine's own act: {a_}"
        if a_ == "snap": return "snap", "snap" + (": (1) a down whose play a foul wiped" if FS[k].startswith("1 ") else "")
        if a_ == "timeout":
            if not isinstance(TT_[k], str): return "unplayed", "unplayed: a timeout, its team unread"
            return ("offense", "offense timeout") if TT_[k] == off else ("defense", "defense timeout")
        if a_ in ("two-minute warning", "end of quarter", "two-minute warning (written)"): return "boundary", a_
        if a_ == "foul":
            if FS[k].startswith("2 "): return (FAM[k], f"pre-snap foul {FAM[k]}") if FAM[k] in ("F1", "F2") else ("unplayed", f"unplayed: (2) a dead-ball foul the engine does not play: {FN[k] or 'unnamed'}")
            return "UNKNOWN", "UNKNOWN: " + (FS[k] or "a foul row unsorted")
        return "unplayed", f"unplayed: (4) {OK_[k] or a_}"
    return ending, nxt_real


def race_rows(TBx):
    """The race's stretches and rows (v12 c: eligibility from the start state) from a table (the saved one, or a changed copy for leak test 3)."""
    A = TBx["act"].to_numpy(object); Q = TBx["q"].to_numpy(float); C = TBx["clock"].to_numpy(float); L_ = TBx["play_len"].to_numpy(float)
    GS = TBx["game_seconds"].to_numpy(float); TR = TBx["transition"].to_numpy(object); SE_ = TBx["season"].to_numpy(); GI = TBx["game_id"].to_numpy(object)
    ST_ = TBx["state"].to_numpy(object); hm = TBx["home"].to_numpy(object); soff = TBx["s_off"].to_numpy(object)
    def used_for(team, uh, ua): return np.where(team == hm, uh, np.where(pd.notna(team), ua, np.nan))
    uh_, ua_ = TBx["used_home"].to_numpy(float), TBx["used_away"].to_numpy(float)
    oppo = lambda team: np.where(team == hm, TBx["away"].to_numpy(object), np.where(pd.notna(team), hm, None))
    to_o_all = np.maximum(3 - used_for(soff, uh_, ua_), 0); to_d_all = np.maximum(3 - used_for(oppo(soff), uh_, ua_), 0)
    run = (A == "snap") & (ST_ == "RUN") & (Q <= 4)
    ce = C - L_; tau_i = np.round(GS - L_)
    why = np.full(len(TBx), "", dtype=object)
    why[run & np.isnan(L_)] = "unstamped (no end stamp or start stamp)"
    why[run & (why == "") & (L_ < 0)] = "FAILURE: negative stamped length"
    why[run & (why == "") & (TR != "same quarter")] = "the next row not in the quarter, or its clock missing or rising"
    why[run & (why == "") & (ce <= 0)] = "the play ran the quarter out"
    why[run & (why == "") & np.isin(Q, [2, 4]) & (C > 120) & (ce <= 120)] = "the play ran past 2:00: the warning at its end, clock stopped"
    why[run & (why == "") & (tau_i < 0)] = "FAILURE: negative time after the play"
    why[run & (why == "") & np.isnan(tau_i)] = "the time after the play unread (counted)"
    su_ = TBx["s_unk"].fillna("").astype(str).to_numpy(object)
    why[run & (why == "") & (su_ != "")] = "the state after the play has an UNKNOWN part"
    why[run & (why == "") & np.isnan(TBx["s_yl"].to_numpy(float))] = "the state after the play not rebuilt (counted)"
    ending, nxt_real = make_ending(TBx)
    E_ = [ending(nxt_real[i], soff[i]) if nxt_real[i] >= 0 else ("unplayed", "no next row") for i in np.where(run & (why == ""))[0]]
    why[np.where(run & (why == ""))[0][np.array([e_[0] == "UNKNOWN" for e_ in E_], bool)]] = "the ending UNKNOWN (never a training label)"
    elig = run & (why == "")
    EI = np.where(elig)[0]; ends = [ending(nxt_real[i], soff[i]) for i in EI]
    cls_ = ["boundary" if e_[0] == "own act" else e_[0] for e_ in ends]
    RS = pd.DataFrame({"i": EI, "season": SE_[EI], "game_id": GI[EI], "q": Q[EI], "ce": np.round(ce[EI]), "tau": tau_i[EI].astype(int), "cls": cls_, "kind": [e_[1] for e_ in ends],
                       "tb2": [("last 2:00 of the game" if a_ == 4 and b_ <= 120 else e1.time_bin(a_, b_)) for a_, b_ in zip(Q[EI], ce[EI])],
                       "diff": TBx["s_diff"].to_numpy(float)[EI], "down": TBx["s_down"].to_numpy(float)[EI], "togo": TBx["s_togo"].to_numpy(float)[EI], "yl": TBx["s_yl"].to_numpy(float)[EI],
                       "to_o": to_o_all[EI], "to_d": to_d_all[EI], "rv": TBx["rv"].to_numpy(float)[EI], "inj": TBx["inj"].to_numpy(float)[EI]})
    RS["diff"] = RS["diff"].fillna(0.0)
    R23 = RS[RS["season"].isin(STAMPED)].reset_index(drop=True)
    nrow = np.where(R23["cls"] == "boundary", R23["tau"], R23["tau"] + 1).astype(int)
    rid = np.repeat(np.arange(len(R23)), nrow); tt = np.concatenate([np.arange(k) for k in nrow]) if len(nrow) else np.zeros(0, int)
    last = np.cumsum(nrow) - 1
    yR = np.full(len(rid), "none", dtype=object); ev_ = (R23["cls"] != "boundary").to_numpy()
    yR[last[ev_ & (nrow > 0)]] = R23["cls"].to_numpy(object)[ev_ & (nrow > 0)]
    XR = np.column_stack([R23[c_].to_numpy(float)[rid] for c_ in RUN_COLS[:-1]] + [np.minimum(tt, T_CAP).astype(float)])
    return dict(RS=RS, R23=R23, XR=XR, yR=yR, sR=R23["season"].to_numpy()[rid], gR=R23["game_id"].to_numpy(object)[rid], tt=tt, run=run, elig=elig, why=why,
                A=A, Q=Q, C=C, L_=L_, GS=GS, TR=TR, SE_=SE_, GI=GI, ST_=ST_, hm=hm, soff=soff, to_o_all=to_o_all, to_d_all=to_d_all)


def stop_rows(TBx, RR, admin_hdr=True):
    """The stopped clock's moments (v10 b) from a table: each act after which the clock is stopped, and each quarter's start; the label from the next real
    row (make_ending); the act's code from the record's own row kind (a no-play down is coded 'foul', as the engine's act after it is). v18 b: a quarter
    whose first row is administrative (the game's opening header) takes its label from the next real row; admin_hdr False reads as v17 did. Also returns,
    for every moment labeled 'unplayed', the row that gave the label (b's trace)."""
    A, Q, C, L_, TR, SE_, GI, ST_, hm, soff = (RR[k_] for k_ in ("A", "Q", "C", "L_", "TR", "SE_", "GI", "ST_", "hm", "soff"))
    AR = TBx["act_rec"].fillna("").to_numpy(object)
    ending, nxt_real = make_ending(TBx, admin_hdr)
    FS = TBx["fsort"].fillna("").to_numpy(object); TXT = TBx["text"].fillna("").astype(str).to_numpy(object)
    FIRSTG = np.r_[True, GI[1:] != GI[:-1]]; UTR = Counter()
    code = np.full(len(TBx), "", dtype=object)
    stp = np.array([str(x).startswith("STOP") for x in ST_]); par = ST_ == "PARTIAL"
    code[(AR == "snap") & stp] = "snap STOP"; code[(AR == "snap") & par] = "snap PARTIAL"; code[(AR == "foul") & (stp | par)] = "foul"
    for a_ in ("kickoff", "try", "timeout", "two-minute warning"): code[A == a_] = a_
    first_q = TBx["qs_first"].to_numpy(bool)
    skick = TBx["s_kick"].to_numpy(bool); sdn, stg, syl, sdf = (TBx[c_].to_numpy(float) for c_ in ("s_down", "s_togo", "s_yl", "s_diff"))
    rvv, injv = TBx["rv"].to_numpy(float), TBx["inj"].to_numpy(float); sunk = TBx["s_unk"].fillna("").astype(str).to_numpy(object)
    def lab(k, off):
        if k < 0: return None, "no next row"
        c_, kind_ = ending(k, off)
        if c_ == "UNKNOWN": return None, kind_
        return ("none" if c_ in ("snap", "boundary", "own act") else c_), kind_
    SX = []; skipped = Counter(); KIND = Counter()
    for i in np.where((code != "") | first_q)[0]:
        if Q[i] > 4: continue
        if first_q[i]:
            off = TBx.at[i, "qs_off"]; kq = bool(TBx.at[i, "qs_kick"]); qu_ = str(TBx.at[i, "qs_unk"]) if isinstance(TBx.at[i, "qs_unk"], str) else ""
            if qu_: skipped[f"quarter start: an UNKNOWN part ({qu_})"] += 1
            elif isinstance(off, str):
                uo = TBx.at[i, "used_home_before"] if off == hm[i] else TBx.at[i, "used_away_before"]; ud = TBx.at[i, "used_away_before"] if off == hm[i] else TBx.at[i, "used_home_before"]
                k0_ = nxt_real[i] if (admin_hdr and FS[i].startswith("3 ")) else i   # the quarter's first real row is the ending of the moment before it (v18 b)
                y_, kd_ = lab(k0_, off)
                if y_ == "unplayed": UTR[("start of the quarter", A[k0_] if k0_ >= 0 else "none", bool(FIRSTG[k0_]) if k0_ >= 0 else None, TXT[k0_][:30] if k0_ >= 0 else "")] += 1
                if y_ is None: skipped[f"quarter start: {kd_}"] += 1
                else:
                    df_ = TBx.at[i, "qs_diff"]; KIND[(y_, kd_)] += 1
                    SX.append((SE_[i], GI[i], Q[i], 900.0, df_ if pd.notna(df_) else 0.0, -1.0 if kq else TBx.at[i, "qs_down"], -1.0 if kq else TBx.at[i, "qs_togo"],
                               -1.0 if kq else TBx.at[i, "qs_yl"], max(3 - uo, 0), max(3 - ud, 0), float(STOP_ACTS.index("start of the quarter")), 0.0, 0.0, y_))
            else: skipped["quarter start: the receiving team unread (home_opening_kickoff missing)"] += 1
        if code[i] == "" or ST_[i] == UNK_NAME: continue
        off = soff[i]
        if sunk[i]: skipped["the state after the act has an UNKNOWN part"] += 1; continue
        if not isinstance(off, str): skipped["the offense after the act not rebuilt"] += 1; continue
        if not skick[i] and np.isnan(syl[i]): skipped["the state after the act not rebuilt"] += 1; continue
        if TR[i] not in ("same quarter", "clock correction", "clock missing"): y_, kd_ = "none", "the quarter ends"
        else:
            y_, kd_ = lab(nxt_real[i], off)
            if y_ == "unplayed": k_ = nxt_real[i]; UTR[(code[i], A[k_] if k_ >= 0 else "none", bool(FIRSTG[k_]) if k_ >= 0 else None, TXT[k_][:30] if k_ >= 0 else "")] += 1
        if y_ is None: skipped[f"the ending: {kd_}"] += 1; continue
        KIND[(y_, kd_)] += 1
        clk = (C[i] - L_[i]) if (A[i] in ("snap", "kickoff") and not np.isnan(L_[i])) else C[i]
        SX.append((SE_[i], GI[i], Q[i], clk, sdf[i] if not np.isnan(sdf[i]) else 0.0, -1.0 if skick[i] else sdn[i], -1.0 if skick[i] else stg[i], -1.0 if skick[i] else syl[i],
                   RR["to_o_all"][i], RR["to_d_all"][i], float(STOP_ACTS.index(code[i])), rvv[i], injv[i], y_))
    return pd.DataFrame(SX, columns=["season", "game_id"] + STOP_COLS + ["y"]), skipped, KIND, UTR


try:
    print("\n=== c (EVENT OWNERSHIP): the race's and the stopped part's rows from the corrected labels (v16 c, d; the labels the fits read) ===")
    RR_ = race_rows(TB)
    for k_, v_ in RR_.items():
        if k_ not in ("XR", "yR", "sR", "gR", "tt"): globals()[k_] = v_
    XR, yR, sR, gR_, tt = RR_["XR"], RR_["yR"], RR_["sR"], RR_["gR"], RR_["tt"]
    nGr = int(TB.loc[np.isin(TB["season"], STAMPED), "game_id"].nunique()); nGs = int(TB["game_id"].nunique())
    print(f"  the race (2023-2025 running-clock stretches, eligible from the start state): {len(R23)} over {nGr} games | not eligible {dict(Counter(why[run & np.isin(SE_, STAMPED) & ~elig]))}")
    print(f"    ended by: {dict(Counter(R23['kind']).most_common(16))}")
    left_r = R23[R23["cls"] == "unplayed"]
    print(f"    endings left unplayed, {per(len(left_r), nGr, 'games')} (v16: 35 over 855): {dict(Counter(left_r['kind']).most_common(12))}")
    print(f"    race rows (one per game second after the play; v10 e) {len(yR)} | outcomes {dict(Counter(yR))} | t read up to the pinned play clock ({T_CAP} s, 4-6-1)")
    SX17, _, SKIND17, UTR17 = stop_rows(TB, RR_, admin_hdr=False)   # v17's reading: b's trace, and v19 e's refit on the same moments
    left17 = sum(v_ for (y_, _), v_ in SKIND17.items() if y_ == "unplayed")
    print(f"  b (v18): the stopped part as v17 read it: moments left unplayed {per(left17, int(TB['game_id'].nunique()), 'games')}; each traced to the row that gave the label"
          f" (the moment, that row's act, whether it is the first row of its game, its text):")
    for k_, v_ in UTR17.most_common(10): print(f"    {k_}: {v_}")
    SXf, skipped, SKIND, UTR18 = stop_rows(TB, RR_)
    left_s = sum(v_ for (y_, _), v_ in SKIND.items() if y_ == "unplayed")
    print(f"  the stopped part (every season): {len(SXf)} moments over {nGs} games | labels {dict(Counter(SXf['y']))} | not used {dict(skipped)}")
    print(f"    moments left unplayed, {per(left_s, nGs, 'games')} (v17 as read above: {left17}; v16: 72 over 1,676; prediction g b: at most 0.05 a game):"
          f" {dict((k_[1], v_) for k_, v_ in SKIND.most_common() if k_[0] == 'unplayed')}")
    for k_, v_ in UTR18.most_common(): print(f"      traced (v19 e: every unplayed moment, the row that gave its label): {k_}: {v_}")
    print(f"    the engine's own acts after a stopped moment (kickoffs, Tries): {dict((k_[1], v_) for k_, v_ in SKIND.items() if k_[1].startswith('the engine'))}")
    LAB = dict(race_left=len(left_r), games_race=nGr, stop_left=left_s, games_stop=nGs, stop_left17=left17)
    section("c: the race's and the stopped part's rows")
except (SystemExit, Overtime):
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; the table is saved")


try:
    print("\n=== section 4's stopped-clock check on the record first (the standing rule: its failure rate prints before its pass on the engine counts) ===")
    def _rec_check():
        with SharedParse():
            ck_n, fl_n, cost_n, _ = check_clock2(S)
            big = sorted([f_ for f_ in fl_n if f_[0] == "STOP" and not np.isnan(f_[7])], key=lambda z: -z[7])[:20]
            trace = []
            byg = defaultdict(list)
            for f_ in big: byg[(f_[8], f_[1])].append(f_)
            for (s_, g_), L_ in byg.items():
                d2, _, _ = r2.load(s_); x_ = d2[d2["game_id"] == g_].reset_index(drop=True)
                for f_ in L_:
                    rows_ = x_[(x_["order_sequence"] >= f_[2]) & (x_["order_sequence"] <= f_[3])]
                    trace.append((f_, [(int(r_["order_sequence"]), r_["quarter_seconds_remaining"], r_["time_of_day"], r_["end_clock_time"], str(r_["desc"])[:120]) for _, r_ in rows_.iterrows()]))
        return dict(ck_n=dict(ck_n), fl_n=fl_n, cost=dict(cost_n), trace=trace)
    REC4 = cache_get("d_record_check", shs(NEW_SHA + "|" + KEY_BASE + "|" + LIBSHA), _rec_check)
    kn = REC4["ck_n"]
    nd_tab = int((TB["fsort"].fillna("") == "1 down, play wiped").sum())
    print(f"  no-play downs made snaps by the check (lib down_row on r2's rows) {kn.get('no-play downs made snaps', 0)} | the table's category 1 (the same down_row) {nd_tab}"
          f" -> {'the same count' if kn.get('no-play downs made snaps', 0) == nd_tab else 'COUNTS DIFFER (printed: the two readers see different rows)'}")
    st_chk = kn.get("STOP checked", 0) - kn.get("STOP unchecked (a play unstamped)", 0)
    print(f"  STOP checked (stamped) {st_chk} | failed {share(kn.get('STOP failed', 0), st_chk)} | no stopping event {kn.get('STOP with no stopping event found (failed)', 0)}"
          f" | PARTIAL failed {kn.get('PARTIAL failed', 0)} of {kn.get('PARTIAL checked', 0)} | r2 UNKNOWN {kn.get('r2 class UNKNOWN', 0)} (v19 part 1: 1,213 of 37,112; 14; 22)")
    print(f"  what each part of the allowance passes (stretches that pass only because of it): {REC4['cost']}")
    FLN = [f_ for f_ in REC4["fl_n"] if f_[0] != "UNKNOWN"]
    print("  the record's stretches unexplained beyond the assumed quantization bound, by kind and the stretch's reason (no cause assigned: the bound is an assumption):")
    for (k_, w_), v_ in Counter((f_[0], f_[6]) for f_ in FLN).most_common(25): print(f"    {k_} | {w_}: {v_}")
    exc_ = np.array([f_[7] for f_ in FLN if f_[0] in ("STOP", "PARTIAL") and not np.isnan(f_[7])], float)
    if len(exc_): print(f"    the excess over the allowance (s): median {np.median(exc_):.1f} | 90th {np.percentile(exc_, 90):.1f} | max {exc_.max():.1f} | by season {dict(Counter(f_[8] for f_ in FLN))}")
    print("  the 20 largest, traced row by row (order_sequence, clock, start stamp, end stamp, text):")
    for f_, rows_ in REC4["trace"]:
        print(f"    {f_[1]} {f_[2]}->{f_[3]} q{f_[9]}: clock fell {f_[4]:.0f} s, allowed {f_[5]:.1f} ({f_[11]} at {f_[12]}) | excess {f_[7]:.1f} | {f_[6]}")
        for r_ in rows_: print(f"      {r_[0]} | {r_[1]} | {r_[2]} | {r_[3]} | {r_[4]}")
    NORISE = kn.get("STOP failed", 0) <= 1213
    print(f"  f (v19), the no-rise gate: stamped stopped stretches failed {kn.get('STOP failed', 0)} with clock_check.py {sh('clock_check.py')} (4-3-2e(3)'s stop at the offense's own"
          f" foul) against v19 part 1's 1,213 -> {'HELD' if NORISE else 'NOT HELD (the fix raised the record failures)'}")
    W3_ = [f_ for f_ in FLN if "4-3-2e(3)" in str(f_[6])]
    print(f"    the record's failures whose reason includes 4-3-2e(3): {len(W3_)} | located at {dict(Counter(str(f_[12]) if len(f_) > 12 else 'none' for f_ in W3_).most_common(5))}")
    REC_FAIL_RATE = (kn.get("STOP failed", 0) / st_chk) if st_chk else np.nan
    SEC4_REC = dict(STOP_failed=kn.get("STOP failed", 0), STOP_checked=st_chk, no_stop_event=kn.get("STOP with no stopping event found (failed)", 0))
    REC4_KEYS = {(f_[1], int(f_[2]), f_[0]) for f_ in FLN}
    section("section 4 on the record")
except SystemExit:
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; the table is saved")



# ---------------- v19 ac: the engine built from the landed e1.py (1b33ab1b1ae8, y's and ab's changes in it) by ac's replacement list, each replacement found once ----------------
Y1_RESTART = '''        self.running = False; self.restart_at = self.t + s_; self.foul_gap = s_ + r_'''   # y1: the line the plant changes (the clock started at the play's end)
PATCH_Y = [
("y1: the play clock after a penalty enforcement, set by the caller from each season's book",
 '''BOOKY = {}   # (season, foul name, side) -> (yards, an automatic first down, where read): the foul's Penalty: line in the season's book, set by the caller; a foul missing is UNSUPPORTED when drawn
''',
 '''BOOKY = {}   # (season, foul name, side) -> (yards, an automatic first down, where read): the foul's Penalty: line in the season's book, set by the caller; a foul missing is UNSUPPORTED when drawn
ENF_CLOCK = {}   # v19 y1: season -> (the seconds the offense has to snap after a penalty enforcement, beginning with the Referee's whistle (Rule 4 Section 6 Article 2 (e)), where read): set by the caller from each season's book; a season missing has no restart rows (a restart drawn for it is UNSUPPORTED)
'''),
("y1: the record's restarts after a foul outside the windows (prep)",
 '''    T["qend"] = quarter_ends(d, X)
    return T, X, notp
''',
 '''    # v19 y1: the restart after a foul outside the windows. 4-3-2(e): following the enforcement the game clock starts as if the foul had not occurred (a running
    # clock starts again on the Referee's signal); 4-6-2(e): after a penalty enforcement the offense has ENF_CLOCK's seconds, beginning with the Referee's whistle,
    # to snap. Each recorded foul row outside the windows (the window read where the engine reads it: a wiped down's own snap clock, the previous snap's for a foul
    # before the snap) on a running clock (the previous row a snap whose own clock class is RUN; for a wiped down RUN or PARTIAL: the engine's clock ran into the
    # down), its next row the snap in the same quarter, every stamp read: the stopped part (real seconds less game seconds, the foul row's stamp to the snap's)
    # and the running part (the game seconds less the wiped play's own stamped seconds). A part the stamps make negative, or a running part over the season's
    # book's play clock (not a restart the article allows), is counted and not used.
    yrows = []; enf_ = ENF_CLOCK.get(int(d["season"].iloc[0]), (None, "not read"))[0] if n else None
    qs_ = d["quarter_seconds_remaining"].to_numpy(float); qq_ = d["qtr"].to_numpy(float); rg_ = (d["season_type"] == "REG").to_numpy()
    for i in np.where(rk == "foul")[0]:
        a, b = i - 1, i + 1
        if a < 0 or b >= n or gid[a] != gid[i] or gid[b] != gid[i] or qq_[a] != qq_[i] or qq_[b] != qq_[i] or qq_[i] > 4 or nan(qs_[i]) or nan(qs_[a]) or nan(qs_[b]): continue
        wiped = bool(d.at[i, "textplay"]); qa_ = qs_[i] if wiped else qs_[a]; q_ = int(qq_[i])
        if foul_window(q_, qa_, bool(rg_[i])) is not False: continue   # inside the windows (or unread) the engine stops the clock to the snap: not a restart
        if not wiped and q_ >= 4 and d.at[i, "penalty_team"] == pos[i]: continue   # 4-3-2e(3): the offense's foul before the snap from the 4th quarter: the clock starts on the snap
        if rk[b] != "snap": X["y1: a foul outside the windows whose next row is not a snap (not used)"] += 1; continue
        if rk[a] != "snap": X["y1: a foul outside the windows with no snap right before it (the clock's state unread; not used)"] += 1; continue
        oc_ = own_class(d, a, bool(rg_[a]))
        if oc_ != "RUN" and not (wiped and oc_ == "PARTIAL"):
            X["y1: a foul outside the windows on a stopped clock (it starts on the snap; not used)"] += 1; continue
        if nan(W[i]) or nan(W[b]) or (wiped and nan(E[i])): X["y1: a restart after a foul outside the windows unstamped (not used)"] += 1; continue
        if enf_ is None: X["y1: a restart after a foul outside the windows, the season's play clock after an enforcement unread (not used)"] += 1; continue
        dG = qs_[i] - qs_[b]; run_ = int(round(dG - ((E[i] - W[i]) if wiped else 0.0))); stp_ = int(round((W[b] - W[i]) - dG))
        if stp_ < 0: X["y1: a restart whose game seconds exceed its real seconds (not used)"] += 1; continue
        if run_ < 0: X["y1: a restart whose clock ran less than the wiped play's own seconds (not used)"] += 1; continue
        if run_ > enf_: X["y1: a restart whose running part exceeds the book's play clock after an enforcement (not used)"] += 1; continue
        yrows.append(("wiped" if wiped else "presnap", time_bin(q_, qa_), stp_, run_))
    T["gfoul"] = pd.DataFrame(yrows, columns=["kind", "tb", "stopped", "run"])
    T["qend"] = quarter_ends(d, X)
    return T, X, notp
'''),
("y1: the pool of restarts after a foul outside the windows",
 '''        P["gpair"] = Pool("R1a PARTIAL stretch, gap and stopped part", c["gpair"], ["x", "stopped"], [("tb", "ls"), ("tb",), ()])
''',
 '''        P["gpair"] = Pool("R1a PARTIAL stretch, gap and stopped part", c["gpair"], ["x", "stopped"], [("tb", "ls"), ("tb",), ()])
        P["gfoul"] = Pool("y1 restart after a foul outside the windows, stopped part and running part", c["gfoul"], ["stopped", "run"], [("kind", "tb"), ("kind",)], last_any=True)
'''),
("y1: the game's restart second after a foul (none to start)",
 '''self.last_rv = 0.0; self.last_inj = 0.0; self.excess = {}
''',
 '''self.last_rv = 0.0; self.last_inj = 0.0; self.excess = {}; self.foul_gap = None
'''),
("y1: the snap after a foul's restart at the drawn second",
 '''        if R1D and self.race_gap is not None:   # E2b v12: the race drew this snap's second (a pre-snap foul the engine plays takes it)
            g = self.race_gap; self.race_gap = None
        elif R1A''',
 '''        if R1D and self.race_gap is not None:   # E2b v12: the race drew this snap's second (a pre-snap foul the engine plays takes it)
            g = self.race_gap; self.race_gap = None
        elif self.foul_gap is not None:   # v19 y1: after a restart drawn by foul_restart the snap (or a second foul before it) comes at its drawn second
            g = self.foul_gap; self.foul_gap = None
        elif R1A'''),
("y1: the clock after a foul outside the windows starts on the Referee's whistle, the snap within the book's play clock of it",
 '''        ev = [("foul in window 4-3-2e", fw is True), ("offensive pre-snap foul q4/OT 4-3-2e(3)", offense_presnap and self.q >= 4),
              ("foul outside windows 4-3-2e", fw is False), ("foul, window unread", fw is None)]
        self.stop_after(ev)
''',
 '''        ev = [("foul in window 4-3-2e", fw is True), ("offensive pre-snap foul q4/OT 4-3-2e(3)", offense_presnap and self.q >= 4),
              ("foul outside windows 4-3-2e", fw is False), ("foul, window unread", fw is None)]
        if fw is False and clock_class(ev, beyond(self.q, self.reg))[0] == "PARTIAL":   # v19 y1: a running clock after a foul outside the windows
            self.foul_restart("wiped" if ran else "presnap", qa); return
        self.stop_after(ev)

    def foul_restart(self, kind, qa):
        """v19 y1: a foul outside the windows on a running clock (4-3-2e: following the enforcement the clock starts as if the foul had not occurred): the game
        clock stopped for the enforcement and started on the Referee's whistle; the snap within the season's book's play clock of the whistle (4-6-2e, ENF_CLOCK).
        The stopped part and the game seconds to the snap are one recorded restart after such a foul (its kind, a wiped down or a foul before the snap, and its
        time bin; the record's restarts over the book's play clock are not in the pool)."""
        o = self.P["gfoul"].draw(self.rng, dict(kind=kind, tb=time_bin(self.q, qa)))
        s_, r_ = int(o["stopped"]), int(o["run"])
''' + Y1_RESTART + '''
        self.cnt[f"y1: restarts after a foul outside the windows ({kind})"] += 1
'''),
("y1: a timeout drawn after a foul's restart comes at the restart's drawn second",
 '''            g = int(self.gap(self.prev_kind, "timeout")); res = self.advance(g)
''',
 '''            if self.foul_gap is not None:   # v19 y1: a timeout called in place of the snap after a foul's restart, at its drawn second (within the play clock)
                g = self.foul_gap; self.foul_gap = None; self.cnt["y1: a timeout drawn at a foul restart's drawn second"] += 1
            else: g = int(self.gap(self.prev_kind, "timeout"))
            res = self.advance(g)
'''),
("y1: a stoppage written clears the restart's second (an unplayed stoppage)",
 '''        self.row(play_type="", desc=f"(an unplayed stoppage drawn by {where}: its own effects are not modeled; the game is unsupported from here)", time_of_day=self.stamp(self.t))
        self.running = False; self.restart_at = None; self.stretch_stop = True; self.prev_kind = "other"
''',
 '''        self.row(play_type="", desc=f"(an unplayed stoppage drawn by {where}: its own effects are not modeled; the game is unsupported from here)", time_of_day=self.stamp(self.t))
        self.running = False; self.restart_at = None; self.stretch_stop = True; self.prev_kind = "other"; self.foul_gap = None
'''),
("y1: a new quarter clears the restart's second",
 '''                self.foul_used = False; self.stretch_stop = True; self.pair_x = None
''',
 '''                self.foul_used = False; self.stretch_stop = True; self.pair_x = None; self.foul_gap = None
'''),
("y: t's counter deleted (x4: its rows did not sum to its recount)",
 '''        r["yardline_100"] = w; self.cnt["s1, t1: rows written from a state off a whole yard in the record's marking (rounded toward the attacked goal)"] += 1
''',
 '''        r["yardline_100"] = w
'''),
("y: t's counter deleted, its docstring",
 '''        attacks (the record's own marking at 0.871, measured in this chain; the other way 0.129), counted."""''',
 '''        attacks (the record's own marking at 0.871, measured by the s chain; the other way 0.129)."""'''),
("y1: the module's clock description",
 '''PARTIAL"
        " restarts it after a stopped part drawn from the record's PARTIAL stretches, RUN runs it.''',
 '''PARTIAL"
        " restarts it after a stopped part drawn from the record's PARTIAL stretches, RUN runs it. After a foul outside the windows on a running clock (4-3-2e) the"
        " clock is stopped for the enforcement and starts on the Referee's whistle, the snap within the season's book's play clock of it (4-6-2e): the stopped part"
        " and the game seconds to the snap drawn together from the record's restarts after such fouls (v19 y1).'''),
("y1: conf.pkl names the play clock after an enforcement",
 '''# RUNOFF_RESTART, SCRIM_TB, BOOKY; the race's flags''',
 '''# RUNOFF_RESTART, SCRIM_TB, BOOKY, ENF_CLOCK; the race's flags'''),
]
PATCH_Y = [(nm_, o_, n_) for nm_, o_, n_ in PATCH_Y if E1_TXT.count(o_) == 1 or E1_TXT.count(n_) != 1]   # y's replacements already in the landed e1.py (its text holds the new side once) are not applied again
for nm_, o_, n_ in PATCH_Y:   # y's changes are in the landed e1.py (1b33ab1b1ae8 holds y's and ab's): each new side present once, none applied again
    if E1_TXT.count(n_) != 1: stop(f"y's replacement '{nm_}' is not in the landed e1.py once ({E1_TXT.count(n_)}); nothing run")
V33_LANDED = ['''FULL_YL = [("down", "dist", "yl20", "time", "score"), ("down", "dist", "yl5", "time", "score"), ("down", "dist", "yl5", "time"), ("down", "dist", "yl5"), ("down", "yl5"), ("yl5in",)] + FULL   # v33 (ac and its additions 1, 2): inside the 20 the yards-to-goal key is the last key dropped: the yard line, then the 5-yard cell through the time, score, distance and down merges, then the 5-yard cell alone (yl5in: None outside the 20, so it holds no bin there and every draw outside the 20 resolves where it does today), then today's field-cell levels
PLAY2_LV = [("kind", "inc_k", "ob_k") + l for l in FULL_YL[:6]] + [("kind", "yl5in")] + [("kind", "inc_k", "ob_k") + l for l in FULL]   # v33: the model's snap outcome levels: (kind, flags) with each yards-to-goal level, then (kind, 5-yard cell), then (kind, flags) with today's field-cell levels; the last level is drawn whatever its count, as before''', "def yl5in_bin(yl):", "self.used[i] += 1; self.last = i", "ac0: play2 draw from {'inside the 1' if self.yl < 1 else yl5_bin(self.yl)} resolved at level"]   # v36: the counter as ad0 (a) landed it
for n_ in V33_LANDED[1:]:   # v37: v33's levels are replaced by af1's, checked with af's landed text below
    if E1_TXT.count(n_) != 1: stop(f"v33's landed text is not in e1.py once: {n_[:60]!r} ({E1_TXT.count(n_)}); nothing run")
print(f"  y's {len(PATCH_Y)} replacements and v33's {len(V33_LANDED)} landed pieces (ab's and ac's levels, the counters) each present once in the landed e1.py {shs(E1_TXT)}: not applied again; ad's replacements below build the candidate")
PATCH_AC_COUNT = []   # v36: set with af's definitions below
AC_LEVELS_OLD = V33_LANDED[0]
AC_LEVELS_NEW = AC_LEVELS_OLD   # v36: replaced with af1's levels below
AC_LEVELS_PLANT = '''FULL_YL = [("down", "dist", "yl20", "time", "score")] + FULL   # PLANT ac: the field cell in place of the 5-yard cell below the yard-line level
PLAY2_LV = [("kind", "inc_k", "ob_k") + l for l in FULL_YL]'''
AC_LEVELS_PRE = '''FULL_YL = FULL   # ab1's 'today': the pool before ab, the field cells alone
PLAY2_LV = [("kind", "inc_k", "ob_k") + l for l in FULL_YL]'''
AD1_OLD = '''def yl20_bin(yl):
'''
AD1_NEW = '''MARK_INSIDE1 = None   # v34 ad0 (b): the yard line the record writes a spot inside the 1 as, set by the caller from the record's own count of snaps written below the 1 (None: the spot's floor)


def _ylk(yl):
    """v34 ad1: the whole yard a spot keys the yards-to-goal levels at: its floor; a spot inside the 1 at the yard line the record writes it as (MARK_INSIDE1). The spot itself stays exact."""
    y = float(yl); w = int(np.floor(y))
    return MARK_INSIDE1 if (0 < y < 1 and MARK_INSIDE1 is not None) else w


def yl20_bin(yl):
'''
AD2_OLD = '''    w = int(np.floor(float(yl)))
    return w if 1 <= w <= 20 else field_bin(yl)'''
AD2_NEW = '''    w = _ylk(yl)   # v34 ad1
    return w if 1 <= w <= 20 else field_bin(yl)'''
AD3_OLD = '''    w = int(np.floor(float(yl)))
    return ("1-5" if w <= 5'''
AD3_NEW = '''    w = _ylk(yl)   # v34 ad1
    return ("1-5" if w <= 5'''
AD4_OLD = '''    w = int(np.floor(float(yl)))
    return yl5_bin(yl) if 1 <= w <= 20 else None'''
AD4_NEW = '''    w = _ylk(yl)   # v34 ad1
    return yl5_bin(yl) if 1 <= w <= 20 else None'''
AD5_OLD = '''        y = float(yl); w = int(np.floor(y))
        if tg is not None and not nan(tg): r["ydstogo"] = w - int(np.floor(y - float(tg)))
        if yg is not None and not nan(yg): r["yards_gained"] = w - int(np.floor(y - float(yg)))
'''
AD5_NEW = '''        W_ = lambda v: MARK_INSIDE1 if (0 < v < 1 and MARK_INSIDE1 is not None) else int(np.floor(v))   # v34 ad0 (b): each spot (the ball, the line to gain, the play's end) inside the 1 written at the yard line the record writes it as, never 0
        y = float(yl); w = W_(y)
        if tg is not None and not nan(tg): r["ydstogo"] = w - int(np.floor(y - float(tg)))   # v35 (ad addition 2, 7-3-1): the line to gain by the floor: a first down's distance is the smaller of 10 and the written yard line (a line to gain inside the 1 is short of the goal: 1st and 10)
        if yg is not None and not nan(yg): r["yards_gained"] = w - W_(y - float(yg))
'''
AD6_OLD = '''ac0: play2 draw from {yl5_bin(self.yl)} resolved at level'''
AD6_NEW = '''ac0: play2 draw from {'inside the 1' if self.yl < 1 else yl5_bin(self.yl)} resolved at level'''
AD7_OLD = '        self.row(**base, play_type=pt, yards_gained=y, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), desc=txt,\n'
AD7_NEW = '        r_ad_ = self.row(**base, play_type=pt, yards_gained=y, time_of_day=self.stamp(W), end_clock_time=self.stamp(E), desc=txt,\n'
AD8_OLD = '        if fam == "F5": self.cnt["foul F5"] += 1\n'
AD8_NEW = ('        if 1 <= r_ad_["yardline_100"] <= 5 and not pen and kind in CALL: self.cnt[f"ad addition item 4: a called snap, no foul, at the {r_ad_[\'yardline_100\']} from a {\'whole-yard\' if float(yl0) == int(float(yl0)) else \'fractional\'} spot: {\'touchdown\' if r_ad_[\'yards_gained\'] >= r_ad_[\'yardline_100\'] else \'no touchdown\'}"] += 1   # v35 (ad addition item 4): the exact spot is not in the rows\n'
           + AD8_OLD)
PATCH_AD = [("ad1: a spot inside the 1 keys the yards-to-goal levels at the yard line the record writes it as (MARK_INSIDE1, _ylk)", AD1_OLD, AD1_NEW),
            ("ad1: yl20_bin reads _ylk", AD2_OLD, AD2_NEW), ("ad1: yl5_bin reads _ylk", AD3_OLD, AD3_NEW), ("ad1: yl5in_bin reads _ylk", AD4_OLD, AD4_NEW),
            ("ad0 (b): Game.mark writes a spot inside the 1 as the record writes it", AD5_OLD, AD5_NEW),
            ("ad0 (a): the counter names a draw inside the 1 as its own cell", AD6_OLD, AD6_NEW),
            ("ad addition item 4: a called snap at the 1-5 kept for its counter", AD7_OLD, AD7_NEW), ("ad addition item 4: the counter by whole-yard or fractional spot", AD8_OLD, AD8_NEW)]
AD1P_OLD = '''    return MARK_INSIDE1 if (0 < y < 1 and MARK_INSIDE1 is not None) else w
'''
AD1P_NEW = '''    return w   # PLANT ad1: a spot inside the 1 keyed as the field cell
'''
AD0P_OLD = '''        W_ = lambda v: MARK_INSIDE1 if (0 < v < 1 and MARK_INSIDE1 is not None) else int(np.floor(v))'''
AD0P_NEW = '''        W_ = lambda v: int(np.floor(v))   # PLANT ad0 (b): a spot inside the 1 written as 0 again'''
AD3P_OLD = '        if tg is not None and not nan(tg): r["ydstogo"] = w - int(np.floor(y - float(tg)))   # v35 (ad addition 2, 7-3-1): the line to gain by the floor: a first down\'s distance is the smaller of 10 and the written yard line (a line to gain inside the 1 is short of the goal: 1st and 10)\n'
AD3P_NEW = '        if tg is not None and not nan(tg): r["ydstogo"] = w - W_(y - float(tg))   # PLANT ad addition 2: v34\'s marking on the line to gain (a line to gain inside the 1 written at the 1)\n'
AF_CNT_OLD = '   # v35 (ad addition item 4): the exact spot is not in the rows\n'
AF_CNT_NEW = ('   # v35 (ad addition item 4): the exact spot is not in the rows\n'
              '        if R1B and 1 <= r_ad_["yardline_100"] <= 5 and not pen and kind in CALL: self.cnt[f"af0: a called snap, no foul, at the {r_ad_[\'yardline_100\']} drawn at level {self.P[\'play2\'].last}: {\'touchdown\' if r_ad_[\'yards_gained\'] >= r_ad_[\'yardline_100\'] else \'no touchdown\'}"] += 1   # v36 af0: the level this snap\'s outcome resolved at (R1b: the model\'s snap pool, drawn on every such snap)\n')
AF1_OLD = 'def yl5_bin(yl):\n'
AF1_NEW = ('def yl20in_bin(yl):\n'
           '    """v36 af1: the yard line inside the opponent\'s 20, None outside it (as yl5in): a level keyed by it alone holds no bin outside the 20."""\n'
           '    w = _ylk(yl)\n'
           '    return w if 1 <= w <= 20 else None\n\n\n'
           'def yl5_bin(yl):\n')
AF2_OLD = 'd["yl5in"] = [yl5in_bin(y) if not nan(y) else None for y in d["yardline_100"]]   # ab1, v33'
AF2_NEW = 'd["yl5in"] = [yl5in_bin(y) if not nan(y) else None for y in d["yardline_100"]]; d["yl20in"] = np.array([yl20in_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object)   # ab1, v33, v36 af1 (whole yards and None, kept as objects as yl5in is)'
AF3_OLD = '"yl20", "yl5", "yl5in"]].copy()'
AF3_NEW = '"yl20", "yl5", "yl5in", "yl20in"]].copy()'
AF4_OLD = 'yl5in=yl5in_bin(self.yl))   # ab1, v33'
AF4_NEW = 'yl5in=yl5in_bin(self.yl), yl20in=yl20in_bin(self.yl))   # ab1, v33, v36 af1'
AF_PLAY2_NEW = ('PLAY2_LV = [("kind", "inc_k", "ob_k") + l for l in [("down", "dist", "yl20", "time", "score"), ("down", "dist", "yl20", "time"), ("down", "dist", "yl20"), ("down", "yl20"), ("yl20in",)] + FULL_YL[1:6]]'
                ' + [("kind", "yl5in")] + [("kind", "inc_k", "ob_k") + l for l in FULL]   # v36 af1: inside the 20 the yard line kept ahead of time and score (then the yard line alone, yl20in: None outside the 20), then ac1\'s 5-yard-cell levels as landed, (kind, 5-yard cell), the field-cell levels; outside the 20 each new level repeats a landed one in the landed order')
V33_LEVELS = V33_LANDED[0]   # v33's levels (the order before af1), kept for af1's plant
AF_LEVELS = V33_LEVELS.split("\n")[0] + "\n" + AF_PLAY2_NEW   # af1's levels, landed at v36
_first = lambda s_: [l_ for l_ in s_.split("\n") if l_.strip()][0]
for nm_, n_ in [("af1: yl20in_bin", AF1_NEW[:AF1_NEW.index("def yl5_bin")]), ("af1: the record's rows carry yl20in", 'd["yl20in"] = np.array([yl20in_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object)'),
                ("af1: the snap pool's rows carry yl20in", AF3_NEW), ("af1: the game's key carries yl20in", 'yl20in=yl20in_bin(self.yl)'),
                ("af1: the levels", AF_PLAY2_NEW), ("af0: the counter by level", AF_CNT_NEW.split("\n")[1])]:   # v38: each af piece by its own statement (ag inserted text beside them)
    if E1_TXT.count(n_) != 1: stop(f"af's landed text is not in e1.py once: {nm_} ({E1_TXT.count(n_)}); nothing run")
for nm_, o_, n_ in PATCH_AD:   # ad's item 4 counter line is followed in the landed text by af0's counter, so that piece is checked by its own line
    if not (E1_TXT.count(n_) == 1 or ("item 4" in nm_ and E1_TXT.count(_first(n_)) == 1)): stop(f"ad's landed text is not in e1.py once: {nm_}; nothing run")
print(f"  ad's {len(PATCH_AD)} and af's 6 landed pieces each present once in the landed e1.py {shs(E1_TXT)}: not applied again")
AC_LEVELS_OLD = AF_LEVELS; AC_LEVELS_NEW = AF_LEVELS   # v37: the snap pool's levels as landed (ag leaves them); ab1's 'today' and ac1's plant replace them on the read engine as before
AG_HELP = ('def zone4_bin(yl):\n'
           '    """v37 ag0: the fourth-down zone: the 1, 2-3, 4-5, 6-10, 11-20, opp 21-40, the 41-50, own side."""\n'
           '    w = _ylk(yl)\n'
           '    return "the 1" if w <= 1 else ("2-3" if w <= 3 else ("4-5" if w <= 5 else ("6-10" if w <= 10 else ("11-20" if w <= 20 else ("opp 21-40" if w <= 40 else ("the 41-50" if w <= 50 else "own side"))))))\n\n\n'
           'def dist4_bin(t):\n'
           '    """v37 ag0, ag1: the distance in four bins, 1, 2-3, 4-6, 7+ (a fraction to the bin above its whole yard: 1.5 is 2-3)."""\n'
           '    t = float(t)\n'
           '    return "1" if t <= 1 else ("2-3" if t <= 3 else ("4-6" if t <= 6 else "7+"))\n\n\n')
AG1_BINS = ('def ylw_bin(yl):\n'
            '    """v37 ag1: the yard line in whole yards, 1-99, as the record writes it (_ylk)."""\n'
            '    return min(max(_ylk(yl), 1), 99)\n\n\n'
            'def ycell_bin(yl):\n'
            '    """v37 ag1: 5-yard cells inside the opponent\'s 20, 10-yard cells outside it (21-30 ... 91-99)."""\n'
            '    w = ylw_bin(yl)\n'
            '    if w <= 20: return "1-5" if w <= 5 else ("6-10" if w <= 10 else ("11-15" if w <= 15 else "16-20"))\n'
            '    lo = (w - 1) // 10 * 10 + 1\n'
            '    return f"{lo}-{min(lo + 9, 99)}"\n\n\n')
AG_ANCHOR = 'def yl5_bin(yl):\n'
AG_C_OLD = '        choice = self.P["call4"].draw(self.rng, k)["choice"] if self.down == 4 else "go"\n'
AG_C_NEW = AG_C_OLD + '        if self.down == 4: self.cnt[f"ag0: fourth-down choice at {zone4_bin(self.yl)} {dist4_bin(self.yl - self.ltg)} drawn at level {self.P[\'call4\'].last}: {choice}"] += 1   # v37 ag0: the level the choice resolved at\n'
AG2_OLD = 'd["yl20in"] = np.array([yl20in_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object)   # ab1, v33, v36 af1 (whole yards and None, kept as objects as yl5in is)'
AG2_NEW = (AG2_OLD.split("   # ")[0] + '; d["ylw"] = np.array([ylw_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object)'
           '; d["dist4"] = np.array([dist4_bin(t) if not nan(t) else None for t in d["ydstogo"]], dtype=object); d["ycell"] = np.array([ycell_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object)'
           + "   # " + AG2_OLD.split("   # ")[1] + "; v37 ag1: the yard line, the distance bin and the cell, before the comment")   # v37 fix: the new columns ahead of the line's comment
AG3_OLD = '[["choice", "down", "dist", "field", "time", "score"]]'
AG3_NEW = '[["choice", "down", "dist", "field", "time", "score", "ylw", "dist4", "ycell"]]'
AG4_OLD = 'yl20in=yl20in_bin(self.yl))   # ab1, v33, v36 af1'
AG4_NEW = 'yl20in=yl20in_bin(self.yl), ylw=ylw_bin(self.yl), dist4=dist4_bin(self.yl - self.ltg), ycell=ycell_bin(self.yl))   # ab1, v33, v36 af1, v37 ag1'
AG5_OLD = 'P["call4"] = Pool("4th-down choice", c["call4"], ["choice"], FULL)'
AG5_NEW = 'P["call4"] = Pool("4th-down choice", c["call4"], ["choice"], [("down", "dist", "ylw", "time", "score"), ("dist", "ylw", "time"), ("dist", "ylw"), ("dist4", "ylw"), ("dist4", "ycell")] + FULL)   # v37 ag1: keyed by where the ball is, finest first, then the levels as before'
for nm_, n_ in (("ag0: the helpers", AG_HELP), ("ag1: the bins", AG1_BINS), ("ag0: the counter", AG_C_NEW), ("ag1: the record's rows", AG2_NEW), ("ag1: the table", AG3_NEW), ("ag1: the key", AG4_NEW), ("ag1: the levels", AG5_NEW)):
    if E1_TXT.count(n_) != 1: stop(f"ag's landed text is not in e1.py once: {nm_} ({E1_TXT.count(n_)}); nothing run")
print(f"  ag's 7 landed pieces each present once in the landed e1.py {shs(E1_TXT)}: not applied again; ai's build the candidate")
AI_HELP = ('def zone10_bin(yl):\n'
           '    """v38 ai: ah1\'s zones: the 1, 2-3, 4-5, 6-10, 11-20, opp 21-40, the 41-50, own 41-49, own 21-40, own 1-20."""\n'
           '    w = _ylk(yl)\n'
           '    return "the 1" if w <= 1 else ("2-3" if w <= 3 else ("4-5" if w <= 5 else ("6-10" if w <= 10 else ("11-20" if w <= 20 else ("opp 21-40" if w <= 40 else ("the 41-50" if w <= 50 else ("own 41-49" if w <= 59 else ("own 21-40" if w <= 79 else "own 1-20"))))))))\n\n\n')
AI1_BINS = ('def distw_bin(yl, ltg):\n'
            '    """v38 ai1: the distance to gain in whole yards as Game.mark writes it (the written yard line less the line to gain\'s floor), 1 ... 10, 11+."""\n'
            '    d = max(1, _ylk(yl) - int(np.floor(float(ltg))))\n'
            '    return str(d) if d <= 10 else "11+"\n\n\n'
            'def distw_rec(t):\n'
            '    """v38 ai1: the record\'s written distance in whole yards, 1 ... 10, 11+."""\n'
            '    d = max(1, int(round(float(t))))\n'
            '    return str(d) if d <= 10 else "11+"\n\n\n')
AI_C_ANCHOR = '   # v37 ag0: the level the choice resolved at\n'
AI_C_NEW = AI_C_ANCHOR + '        if self.down == 4: self.cnt[f"ai: fourth-down choice at {zone10_bin(self.yl)} {dist4_bin(self.yl - self.ltg)} drawn at level {self.P[\'call4\'].last}: {choice}"] += 1   # v38 ai1: by ah1\'s zones\n'
AI3_ANCHOR = "   # ac0: the level's key names whether yards to the goal were kept\n"
AI3_NEW = AI3_ANCHOR + "            self.cnt[f\"ai3: snap draw at {zone10_bin(self.yl)} down {int(self.down)} resolved at level {self.P['play2'].last}\"] += 1   # v38 ai3: the level each snap draw resolved at, by zone\n"
AI2_OLD = 'd["ycell"] = np.array([ycell_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object)   # ab1'
AI2_NEW = 'd["ycell"] = np.array([ycell_bin(y) if not nan(y) else None for y in d["yardline_100"]], dtype=object); d["distw"] = np.array([distw_rec(t) if not nan(t) else None for t in d["ydstogo"]], dtype=object)   # ab1'
AI3T_OLD = '"ylw", "dist4", "ycell"]]'
AI3T_NEW = '"ylw", "dist4", "ycell", "distw"]]'
AI4_OLD = 'ycell=ycell_bin(self.yl))   # ab1, v33, v36 af1, v37 ag1'
AI4_NEW = 'ycell=ycell_bin(self.yl), distw=distw_bin(self.yl, self.ltg))   # ab1, v33, v36 af1, v37 ag1, v38 ai1'
AI5_NEW = ('P["call4"] = Pool("4th-down choice", c["call4"], ["choice"], [("distw", "ylw", "time", "score"), ("distw", "ylw", "time"), ("distw", "ylw"), ("dist4", "ylw")]'
           ' + [("down", "dist", "ylw", "time", "score"), ("dist", "ylw", "time"), ("dist", "ylw"), ("dist4", "ylw"), ("dist4", "ycell")] + FULL)   # v38 ai1: the whole-yard distance first, then ag1\'s levels as landed')
PATCH_AC_COUNT = [("ai: the helper (ah1's zones)", AG_ANCHOR, AI_HELP + AG_ANCHOR), ("ai: the fourth-down counter by ah1's zones", AI_C_ANCHOR, AI_C_NEW), ("ai3: the snap draw counter", AI3_ANCHOR, AI3_NEW)]   # v38: the read engine is the landed e1.py with ai's counters alone
PATCH_AI = PATCH_AC_COUNT + [("ai1: the whole-yard distance", AG_ANCHOR, AI1_BINS + AG_ANCHOR), ("ai1: the record's rows carry it", AI2_OLD, AI2_NEW), ("ai1: the choice's rows carry it", AI3T_OLD, AI3T_NEW),
                             ("ai1: the game's key carries it", AI4_OLD, AI4_NEW), ("ai1: the choice's levels", AG5_NEW, AI5_NEW)]
PATCH_Y_LANDED = PATCH_Y; PATCH_Y = PATCH_AI   # build_e1 applies ai's list (the candidate); the read engine is the landed e1.py with ai's counters
AB_PLANT_ANCHOR = '''        c = {k: pd.concat([t[k] for t in tables], ignore_index=True) for k in tables[0]}
'''
AB_PLANT_NEW = AB_PLANT_ANCHOR + '''        _m = np.array([isinstance(v, (int, np.integer)) for v in c["play"]["yl20"]], bool); _p = np.random.default_rng(3).permutation(int(_m.sum())); c["play"] = c["play"].copy()   # PLANT ab: the yard line shuffled among the snaps inside the 20
        for _c in ("yl20", "yl5", "yl5in", "yl20in"): c["play"].loc[_m, _c] = c["play"].loc[_m, _c].to_numpy(object)[_p]
'''


def build_e1(split, runoff, stage):
    """The candidate e1.py: the landed e1.py (pinned) with PATCH_Y, each replacement found once in its text; its season values are set by its caller
    (run alone, read from out/engine/conf.pkl)."""
    t = E1_TXT
    for nm, o, n in PATCH_Y:
        c = t.count(o)
        if c != 1: stop(f"replacement '{nm}' is in e1.py {c} times, not once; nothing run")
        t = t.replace(o, n)
    return t


from concurrent.futures import ProcessPoolExecutor, TimeoutError as _FutTimeout
import multiprocessing as _mp
import __main__ as _MAIN


class Pool_:
    """Worker processes (spawn: each imports the shared library afresh; rules.py on disk holds the fixed readers); __main__'s file is hidden while they live so no
    worker reruns this chain. Every wait is bounded by the budget; kill() ends the workers at once."""
    def __init__(self, n, nthreads=None):
        self.n = n; self.nthreads = nthreads; self.mf = getattr(_MAIN, "__file__", None)
        if self.mf is not None: del _MAIN.__file__
        cfg = dict(T_CAP=T_CAP, S=list(S), WARN_SEC=WARN_SEC, RUNOFF_RESTART=RUNOFF_RESTART, SCRIM_TB=SCRIM_TB, ENGINE_CONF=ENGINE_CONF)
        self.ex = ProcessPoolExecutor(max_workers=n, mp_context=_mp.get_context("spawn"), initializer=L.w_init, initargs=(os.getcwd(), list(sys.path), cfg, os.path.abspath(LOG), nthreads))

    def map(self, fn, argl, what):
        return self.run([(fn, a_) for a_ in argl], what)

    def run(self, jobs, what):
        fs = [self.ex.submit(fn, *a_) for fn, a_ in jobs]
        progress(f"  ... {what}: {len(fs)} jobs on {self.n} workers")
        out = []
        for f_ in fs:
            try: out.append(f_.result(timeout=max(left(), 1.0)))
            except _FutTimeout: over(f"waiting on the workers: {what}")
        mod_check(out, f"the workers' results: {what}")   # y: an object naming a module outside MOD_OK stops the run
        return out

    def kill(self):
        for p_ in list(getattr(self.ex, "_processes", {}).values()):
            try: p_.terminate()
            except Exception: pass
        self.ex.shutdown(wait=False, cancel_futures=True)
        if self.mf is not None: _MAIN.__file__ = self.mf; self.mf = None


try:
    print("\n=== the record counted with E2a v3's shared function (k: built once, saved by the sha of every input) ===")
    CODE_KEY = shs("|".join(sh(p) for p in ("e1.py", "r1.py", "r2.py", "r4.py", "record.py", "contract.py")) + "|" + NEW_SHA + "|" + RAWPINS
                   + "|" + LIBSHA)   # the shared library's text (count_side lives there)
    KEY_REC = shs(CODE_KEY + ("|fixture " + sh("fixtures/real_games.csv.gz") if FIXTURE else ""))
    def _count_record():
        L.SIDE[0] = "record"; L.FAILP.clear()
        with SharedParse(): out = count_side(S)
        if L.FAILP: stop("E2a v3's points check fails; nothing run")
        return out
    GR, POR, STR = cache_get("record_counts", KEY_REC, _count_record)
    STAMP = [s for s in S if STR[STR["season"] == s]["x"].notna().mean() > 0.5]
    SPLIT = {}
    for c in CLS:
        x = STR[late(STR) & (STR["cls"] == c)].copy(); x["y"] = x["dG"] - x.groupby("tb")["dG"].transform("mean")
        A2 = x[x["score"].isin(AH)]; B2 = x[x["score"].isin(BH)]
        if len(A2) < 2 or len(B2) < 2 or x["game_id"].nunique() < 3: SPLIT[c] = False; continue
        mA, mB = A2["y"].mean(), B2["y"].mean(); dd = mA - mB
        infl = pd.concat([(A2["y"] - mA) / len(A2), -(B2["y"] - mB) / len(B2)]); gsum = infl.groupby(pd.concat([A2["game_id"], B2["game_id"]]).values).sum(); ng = len(gsum)
        se2 = 2 * np.sqrt((gsum ** 2).sum() * ng / (ng - 1))
        n6 = x.groupby(["tb", "score"]).size(); ns = x[x["season"].isin(STAMP)].groupby(["tb", "score"]).size()
        SPLIT[c] = bool(abs(dd) > se2 and not [k for k in n6.index if n6.get(k, 0) < e1.MIN_BIN or ns.get(k, 0) < e1.MIN_BIN])
    print(f"  stamped seasons {STAMP} | the floor's PACE_SPLIT (v4 a) {SPLIT}")
    section("record counted (count_side)")

    print("\n=== b: the engine, built in memory from e1.py (R1a, R1b, the race R1d, R1e; the shared transition; impossible events at probability 0; the foul")
    print("    during a down drawn whole with the play and enforced by the transition), written nowhere; e1.py on disk unchanged: a CANDIDATE, never a landed product ===")
    E1N = build_e1(SPLIT, RUNOFF_RESTART, "candidate")   # the landed form: the values below are set on the module by its caller
    def gtg_read(x):
        """ad addition 2 item 2: the written distance by down, one reader for the record and the engine (text columns; goal_to_go read where the frame carries it)."""
        n_ = lambda c: pd.to_numeric(x[c], errors="coerce").to_numpy(float) if c in x.columns else None
        sn_ = x["play_type"].isin(list(rules.SNAP_KINDS)).to_numpy(); dn_, tg_, yl_, gg_ = n_("down"), n_("ydstogo"), n_("yardline_100"), n_("goal_to_go")
        ok_ = sn_ & ~np.isnan(dn_) & ~np.isnan(tg_) & ~np.isnan(yl_); out_ = {}
        for d_ in (1, 2, 3, 4):
            m_ = ok_ & (dn_ == d_)
            out_[d_] = dict(snaps=int(m_.sum()), eq=int((m_ & (tg_ == yl_)).sum()), above=int((m_ & (tg_ > yl_)).sum()),
                            flag="no column" if gg_ is None else int((m_ & (gg_ == 1)).sum()), flag_eq="no column" if gg_ is None else int((m_ & (gg_ == 1) & (tg_ == yl_)).sum()))
        m1_ = ok_ & (dn_ == 1); out_["first_below"] = int((m1_ & (tg_ < np.minimum(10, yl_))).sum()); out_["first_above"] = int((m1_ & (tg_ > np.minimum(10, yl_))).sum())
        return out_
    REC_GTG = {}; GTG_WHY = {}
    YL0 = {}
    for s in S:   # ad0 (b): the record's snaps by written yard line below 1, from the pinned record files
        try: x_ = record.raw_frame(contract.PBP_FILE.format(season=s), ["play_type", "yardline_100", "down", "ydstogo", "goal_to_go"], "ad0 (b) and ad addition 2 item 2: the record's written yard lines and distances"); GTG_WHY[s] = "read"
        except Exception as ex_g:
            GTG_WHY[s] = f"goal_to_go not read: {type(ex_g).__name__}: {str(ex_g)[:90]}"
            x_ = record.raw_frame(contract.PBP_FILE.format(season=s), ["play_type", "yardline_100", "down", "ydstogo"], "ad0 (b) and ad addition 2 item 2: the record's written yard lines and distances (no goal_to_go)")
        REC_GTG[s] = gtg_read(x_)
        y_ = pd.to_numeric(x_["yardline_100"], errors="coerce"); sn_ = x_["play_type"].isin(list(rules.SNAP_KINDS)) & y_.notna()
        YL0[s] = (int((sn_ & (y_ < 1)).sum()), int(sn_.sum()), float(y_[sn_ & (y_ >= 1)].min()) if (sn_ & (y_ >= 1)).any() else np.nan)
    MARK_IN1 = int(min(v_[2] for v_ in YL0.values())) if all(v_[0] == 0 for v_ in YL0.values()) and not any(np.isnan(v_[2]) for v_ in YL0.values()) else None
    print(f"  ad0 (b): the record's snaps written below the 1, by season (below 1, of the snaps, the smallest written yard line at or above 1): {YL0}"
          f" -> MARK_INSIDE1 {MARK_IN1} ({'every season writes none below 1: a spot inside the 1 is written, and keyed, at the smallest yard line the record writes' if MARK_IN1 is not None else 'the record writes snaps below 1: the engine writes the floor, as v33'})")
    ENGINE_CONF = dict(PACE_SPLIT=SPLIT, RUNOFF_RESTART=RUNOFF_RESTART, SCRIM_TB=SCRIM_TB, BOOKY=BOOKY, ENF_CLOCK=ENF_CLOCK, MARK_INSIDE1=MARK_IN1)
    L.configure(ENGINE_CONF=ENGINE_CONF)
    print(f"  e1.py {shs(E1_TXT)} -> the candidate {shs(E1N)} (the file this chain lands as e1.py when its checks pass) | its caller-set values: PACE_SPLIT {SPLIT},"
          f" BOOKY {len(BOOKY)} (season, foul, side) entries, SCRIM_TB, ENF_CLOCK and RUNOFF_RESTART per season (run alone, it reads them from out/engine/conf.pkl)")
    e1n = load_mod(E1N, "e1_v29_cand")
    for k_, v_ in ENGINE_CONF.items(): setattr(e1n, k_, v_)
    KEY_TAB = shs(KEY_REC + "|" + shs(E1N) + "|" + repr(sorted((k_, repr(v_)) for k_, v_ in ENGINE_CONF.items())))
    def with_pyd(x, s):
        """The record's rows for the engine's pools with penalty_yards joined (the fouls on the play drawn whole read it; no other table reads it)."""
        for c_ in ("penalty_yards",):   # v19 r1: pass interference's depth is its penalty_yards (part 2 drew 1,544 wiped rows whose air_yards was empty)
            k_ = dict(zip(zip(EX[s]["game_id"], EX[s]["play_id"]), EX[s][c_]))
            x[c_] = [k_.get((g_, p_), np.nan) for g_, p_ in zip(x["game_id"], pd.to_numeric(x["play_id"], errors="coerce"))]
        return x
    TABP = cache_get("engine_tables", KEY_TAB, lambda: {s: e1n.prep(with_pyd(load_rec(s), s)) for s in S})
    TAB_PATH = os.path.join(WORK, f"engine_tables_{KEY_TAB}.pkl")
    D2 = pd.concat([TABP[s][0]["dur2"].assign(season=s) for s in S], ignore_index=True); nG_REC = TB["game_id"].nunique()
    print(f"  the fouls on the play, every recorded pass and run with its down, distance, yard line and time (none removed for its foul) {len(D2)} | by kind: "
          + " | ".join(f"{k_} {v_} ({v_ / nG_REC:.3f} a game)" for k_, v_ in Counter(D2["fam2"].where(~D2["fam2"].astype(str).str.startswith("unsupported"), "unsupported")).most_common()))
    print(f"    the play wiped, by side and next down: {dict(Counter(zip(D2.loc[D2['fam2'] == 'wiped', 'side'], D2.loc[D2['fam2'] == 'wiped', 'oc'])))} | the record's award mark against"
          f" 14-1-2 Item 5's list (the rule played): differs on {int(D2['flag_differs'].sum())} rows")
    stn_ = D2["fam2"] == "stand"
    print(f"    v18 c: a foul on a play that stands, drawn whole and enforced by transition.stand() at the drawn play's end: {int(stn_.sum())} rows | by side {dict(Counter(D2.loc[stn_, 'side']))}"
          f" | by name {dict(Counter(D2.loc[stn_, 'ptype']).most_common(8))} (one the transition leaves UNKNOWN at the drawn spot is UNSUPPORTED when drawn)")
    print(f"    unsupported (kept at their own rate; drawing one marks the game UNSUPPORTED): {dict(Counter(D2.loc[D2['fam2'].astype(str).str.startswith('unsupported'), 'fam2'].str.split(': ', n=1).str[1].str.split(':').str[0]).most_common(8))}")
    NOTP = Counter()
    for s in S: NOTP.update(TABP[s][2])
    print(f"    not in any pool (declared; no game counts them as unsupported): fouls on kicks {sum(v_ for k_, v_ in NOTP.items() if k_.startswith('on a kick'))}"
          f" ({sum(v_ for k_, v_ in NOTP.items() if k_.startswith('on a kick')) / nG_REC:.3f} a game)")
    sched = record.schedule(); sched = sched[sched["home_score"].notna()].reset_index(drop=True)
    if FIXTURE: sched = sched[sched["game_id"].isin(FXG)].reset_index(drop=True)
    R = {s: e1n.Rates(s, [TABP[x][0] for x in S if x != s]) for s in S}
    XP_ = Counter()
    for s in S: XP_.update(TABP[s][1])
    print(f"  e1.prep's own counts (every season's, summed; each a row the pools do not use, or a note; printed whole, {len(XP_)} counts):")
    for k_, v_ in sorted(XP_.items()): print(f"    {v_:7d}  {k_}")
    GF_ = pd.concat([TABP[s][0]["gfoul"].assign(season=s) for s in S], ignore_index=True)
    print(f"  y1: the record's restarts after a foul outside the windows (the pool 'gfoul'; the stopped part in real seconds, the running part in game seconds, the play clock"
          f" after an enforcement each season's book's {sorted({v_[0] for v_ in ENF_CLOCK.values()}, key=str)}): {len(GF_)} | by season {dict(sorted(Counter(GF_['season']).items()))}")
    for k_ in ("wiped", "presnap"):
        z_ = GF_[GF_["kind"] == k_]
        print(f"    {k_}: {len(z_)} | stopped part mean {z_['stopped'].mean() if len(z_) else float('nan'):.2f} s, running part mean {z_['run'].mean() if len(z_) else float('nan'):.2f} s"
              f" (max {z_['run'].max() if len(z_) else float('nan')}) | by time bin {dict(Counter(z_['tb']))}")
    NCPU = os.cpu_count() or 1; NW = max(1, min(NCPU, 8)); NTH = max(1, NCPU // NW); POOL = Pool_(NW, NTH)
    print(f"  worker processes {NW}, each worker's library threads capped at {NTH} (this machine's cores {NCPU} // {NW} workers; a runtime setting only) | games {len(sched)} (the original population)")
    section("engine: built, its pools")

    print("\n=== the floor: the same engine with the race off (R1a + R1b), every game with its own generator ([SEED, season, game]) ===")
    FLF = dict(R1A=True, R1B=True, R1D=False, QE_BAND=10)
    OUT_F = POOL.map(L.w_play, [(E1N, s, sched[sched["season"] == s], TAB_PATH, None, X6, list(S), FLF) for s in S], "the floor's games")
    FRF = {s: o_[0] for s, o_ in zip(S, OUT_F)}; FLOOR_SHA = shs(pd.concat([FRF[s] for s in S], ignore_index=True).to_csv(index=False))
    for s, o_ in zip(S, OUT_F):
        if o_[3]: print(f"  {s}, floor games not played: {dict(o_[3])}")
    EVF = cache_get("floor_evaluated", shs(KEY_TAB + "|" + FLOOR_SHA + "|" + LIBSHA), lambda: POOL.map(L.w_eval, [(s, FRF[s], X6, True, True) for s in S], "the floor counted and checked"))
    if any(e_["failp"] for e_ in EVF): stop("E2a v3's points check fails on the floor's games")
    GF = pd.concat([e_["G"] for e_ in EVF], ignore_index=True); POF = pd.concat([e_["PO"] for e_ in EVF], ignore_index=True); STF = pd.concat([e_["ST"] for e_ in EVF], ignore_index=True)
    if ((GF["clock_pre"] + GF["clock_stretch"] + GF["clock_post"]) != 3600).any(): stop("a floor game's regulation clock is not 3,600")
    dF = pd.concat([e_["dM"] for e_ in EVF], ignore_index=True); TM_F = pd.concat([e_["TM"] for e_ in EVF], ignore_index=True)
    print(f"  the floor {FLOOR_SHA}: games {GF['game_id'].nunique()}")
    dR = with_diff(pd.concat([load_rec(s) for s in S], ignore_index=True)); TM_R = cache_get("record_timeouts", KEY_REC, lambda: moments(dR))
    section("the floor played and counted")
    print("\n=== c: the stopped clock's part, trees (as v13 ran them), one fit per season on the five other seasons (look-back), rounds by v8 b; the race, as v13 ran it ===")
    print(f"  settings: {TREE} | ceiling {CAP['stop']} rounds | the race: LogisticRegression(penalty=None, max_iter=1000), t indicators 1..{T_CAP}")
    XS = SXf[STOP_COLS].to_numpy(float); yS = SXf["y"].to_numpy(object); sS = SXf["season"].to_numpy()
    NPZ_S = os.path.join(LIB_DIR, "stop_rows.npz"); np.savez(NPZ_S, X=XS, y=yS, s=sS)
    NPZ_R = os.path.join(LIB_DIR, "race_rows.npz"); np.savez(NPZ_R, X=XR, y=yR, s=sR)
    FITS = {2023: [2024, 2025], 2024: [2023, 2025], 2025: [2023, 2024], "2019-2021": [2023, 2024, 2025]}
    KEY_FIT = shs("|".join(L.shb(x_) for x_ in (XS.tobytes(), pickle.dumps(list(yS)), np.asarray(sS).tobytes(), XR.tobytes(), pickle.dumps(list(yR)), np.asarray(sR).tobytes()))
                  + repr(TREE) + repr(CAP) + repr(FITS) + LIBSHA)
    def _fits():
        t_f = time.time()
        o_ = POOL.run([(L.w_fit_stop, (NPZ_S, s, CAP["stop"])) for s in S] + [(L.w_fit_race, (NPZ_R, fs, ho)) for ho, fs in FITS.items()], "the fits")
        o_s, o_r = o_[:len(S)], o_[len(S):]
        return dict(stop=o_s, race=o_r, sec=time.time() - t_f)
    FITC = cache_get("fits", KEY_FIT, _fits)   # saved by the sha of the rows they are fitted on, the settings and the code
    outs = FITC["stop"] + [None] + FITC["race"]
    print(f"  {len(S) + len(FITS)} fits side by side in {FITC['sec']:.0f} s when built (each fit's own seconds: {[round(o_[-1]) for o_ in FITC['stop'] + FITC['race']]})")
    outs[len(S)] = POOL.map(L.w_fit_stop, [(NPZ_S, S[0], 1)], "the ceiling plant")[0]   # the plant is fitted in every run
    MS = {}; MSI = {}
    for o_ in outs[:len(S)]:
        s, mb, inf, _ = o_
        if mb is None: stop(f"stopped part, season {s}: {inf}")
        MS[s] = pickle.loads(mb); MSI[s] = inf
        print(f"  stopped part {s}: rows {inf['n']} | classes {list(MS[s].classes_)} | inner season {inf['inner']} | rounds {inf['best']} of {inf['cap']} | inner log loss round 1"
              f" {inf['ll_first']:.4f}, chosen {inf['ll_best']:.4f}, ceiling {inf['ll_cap']:.4f}")
    PCAP = outs[len(S)][1] is None
    print(f"  v8 b plant: a ceiling of 1 round {'refused as it must (' + str(outs[len(S)][2]) + ')' if PCAP else 'NOT REFUSED'}")
    RPLANT = POOL.map(L.w_fit_race, [(NPZ_R, FITS[2023], "w1 plant", 7)], "w1's plant: the race fitted with the time-left inputs shuffled across moments")[0]
    MR_PLANT = pickle.loads(RPLANT[1])   # fitted on 2024-2025 as the 2023 race is; judged on 2023's held-out rows below (report)
    if not PCAP: stop("the ceiling plant was not refused")
    MR = {}
    for o_ in outs[len(S) + 1:]:
        ho, mb, _ = o_; MR[ho] = pickle.loads(mb)
        print(f"  race held out {ho} (fit on {FITS[ho]}): rows {int(np.isin(sR, FITS[ho]).sum())} | classes {list(MR[ho].classes_)} | iterations {MR[ho].iters} {'(converged)' if MR[ho].converged else '(NOT CONVERGED at 1000)'}")
    print("\n=== ac0: the snap outcome pool as the landed e1.py (1b33ab1b1ae8, ab's) draws it today (the Pool lines, their keys, field_bin, the goal censor, each by line number) ===")
    E1L_ = E1_TXT.split("\n")
    for i_, l_ in enumerate(E1L_):
        if ('P["play"] = Pool' in l_ or 'P["play2"] = Pool' in l_ or '"play2"].draw' in l_ or '"play"].draw' in l_ or l_.startswith("FULL = ") or l_.startswith("MIN_BIN = ")
                or l_.startswith("def field_bin") or l_.strip() == "elif end <= 0:" or "self.P[\"kc\"].draw" in l_):
            print(f"  e1.py L{i_ + 1}: {l_.rstrip()[:240]}")
            if l_.startswith("def field_bin") or l_.strip() == "elif end <= 0:" or 'P["play2"] = Pool' in l_: print(f"  e1.py L{i_ + 2}: {E1L_[i_ + 1].rstrip()[:240]}")
    print("  read: P['play2'] is keyed by (kind, inc_k, ob_k) plus FULL_YL's levels: the yard line inside the 20 with (down, dist, time, score), then the 5-yard cell with them,")
    print("  then FULL's field-cell levels; a cell under MIN_BIN (30) falls to the next level, so a draw whose yard-line and 5-yard cells with time and score are both thin")
    print("  resolves at a field-cell level with no yards-to-goal key (ac0 counts those); the gain past the goal is censored at the lines above.")

    print("\n=== the record read by its own readers (record.events for each row's kind; the columns named, each checked against the record file's header): ab0's and ab2's reads ===")
    W_COLS = ["game_id", "play_id", "order_sequence", "season_type", "qtr", "quarter_seconds_remaining", "posteam", "home_team", "away_team", "total_home_score",
              "total_away_score", "play_type", "desc", "penalty", "fixed_drive", "touchdown", "interception", "fumble_lost", "fumble_recovery_1_team", "safety",
              "field_goal_result", "two_point_attempt", "timeout", "incomplete_pass", "out_of_bounds", "yardline_100", "time_of_day", "end_clock_time",
              "defteam", "td_team", "extra_point_result", "two_point_conv_result", "defensive_two_point_conv", "defensive_extra_point_conv", "down", "ydstogo", "yards_gained"]
    W_NUM = ("order_sequence", "qtr", "quarter_seconds_remaining", "total_home_score", "total_away_score", "penalty", "fixed_drive", "touchdown", "interception", "fumble_lost",
             "safety", "two_point_attempt", "timeout", "incomplete_pass", "out_of_bounds", "yardline_100", "defensive_two_point_conv", "defensive_extra_point_conv", "down", "ydstogo", "yards_gained")
    for s in S:   # never guess a column: each read column is in the season's record file header (the fixture reads the record files for the columns it lacks)
        hdr_ = record.header(contract.PBP_FILE.format(season=s)); miss_ = [c_ for c_ in W_COLS if c_ not in hdr_]
        if miss_: stop(f"UNKNOWN: the {s} record file lacks {miss_}; nothing read")
    def w_side(frames):
        """Every season's rows of one side (frames: the engine's text frames by season, read through e1.OnSim; None: the record), each row's kind by record.events."""
        out = []
        for s in S:
            if frames is not None and s not in frames: continue
            def rd():
                ev = record.events(s); return ev, record.raw_frame(f"pbp_{s}.csv.gz", W_COLS, "y read")
            if frames is not None:
                with e1.OnSim({s: frames[s]}): ev, raw = rd()
            else: ev, raw = rd()
            raw = raw.copy(); raw["play_id"] = pd.to_numeric(raw["play_id"], errors="coerce")
            k_ = dict(zip(zip(ev["game_id"], pd.to_numeric(ev["play_id"], errors="coerce")), ev["kind"]))
            raw["kind"] = [k_.get((g, p), "") for g, p in zip(raw["game_id"], raw["play_id"])]
            for c in W_NUM: raw[c] = pd.to_numeric(raw[c], errors="coerce")
            for c in ("posteam", "fumble_recovery_1_team", "defteam", "td_team"): raw[c] = [v if isinstance(v, str) and v.strip() else None for v in raw[c]]
            raw["season"] = s
            out.append(raw.sort_values(["game_id", "order_sequence"]).reset_index(drop=True))
        x = pd.concat(out, ignore_index=True)
        x["reg"] = x["qtr"] <= 4
        x["gsr"] = np.where(x["qtr"] <= 4, (4 - x["qtr"]) * 900 + x["quarter_seconds_remaining"], x["quarter_seconds_remaining"])
        x["snap"] = x["play_type"].isin(rules.SNAP_KINDS) & (x["two_point_attempt"] != 1)
        return x
    W_KEY_X = shs(KEY_REC + "|record side|" + shs(inspect.getsource(w_side)) + "|" + repr(W_COLS) + "|" + sh("rules.py") + "|" + LIBSHA)
    t_x = time.time(); XREC = cache_get("aa_record_side", W_KEY_X, lambda: w_side(None))
    print(f"  the record's rows {len(XREC)} in {XREC['game_id'].nunique()} games, read in {time.time() - t_x:.0f} s")

    def w_mean(v, g):
        """A share or mean with its 2SE by game (y0 a: fewer than 2 rows, or one game, is NOT MEASURED); the y2 block defines the same function later for its own reads."""
        v = np.asarray(v, float); g = np.asarray(g, object); ok = ~np.isnan(v); v, g = v[ok], g[ok]
        if len(v) < 2: return (np.nan, np.nan, len(v))
        m_ = v.mean(); r_ = pd.Series((v - m_) / len(v)).groupby(g).sum().to_numpy(); G_ = len(r_)
        return (m_, 2 * np.sqrt((r_ ** 2).sum() * G_ / (G_ - 1)) if G_ > 1 else np.nan, len(v))
    print("\n=== ac0: the record's snaps inside the opponent's 20 by yard line (ab0's read, reprinted) (the pool's rows: a called play with no foul, no Try, a yard line written): the count, the share")
    print("    scoring a touchdown (the gain at least the distance to the goal), and the gain in 5-yard bins, 2SE by game ===")
    POOLROWS = XREC["snap"].to_numpy() & XREC["kind"].isin(list(e1.CALL)).to_numpy() & (XREC["penalty"].to_numpy(float) != 1) & ~np.isnan(XREC["yardline_100"].to_numpy(float)) & ~np.isnan(XREC["yards_gained"].to_numpy(float))
    YB5 = [("a loss", lambda v: v < 0), ("0-4", lambda v: (v >= 0) & (v < 5)), ("5-9", lambda v: (v >= 5) & (v < 10)), ("10-14", lambda v: (v >= 10) & (v < 15)), ("15-19", lambda v: (v >= 15) & (v < 20)), ("20+", lambda v: v >= 20)]
    yl_r = XREC["yardline_100"].to_numpy(float); yg_r = XREC["yards_gained"].to_numpy(float); g_r = XREC["game_id"].to_numpy(object)
    for yl_ in range(1, 21):
        m_ = POOLROWS & (yl_r == yl_)
        td_ = w_mean((yg_r[m_] >= yl_).astype(float), g_r[m_])
        bins_ = " ".join(f"{lab_} {w_mean(f_(yg_r[m_]).astype(float), g_r[m_])[0]:.3f}" for lab_, f_ in YB5)
        print(f"  the {yl_:2d}: snaps {int(m_.sum())} | touchdown share {td_[0]:.3f} ±{td_[1]:.3f} | gain bins {bins_}")
    print("  by 5-yard cell (the merge's second level), the same figures:")
    for lab_, lo_, hi_ in (("1-5", 1, 5), ("6-10", 6, 10), ("11-15", 11, 15), ("16-20", 16, 20)):
        m_ = POOLROWS & (yl_r >= lo_) & (yl_r <= hi_); td_ = w_mean((yg_r[m_] >= yl_r[m_]).astype(float), g_r[m_])
        print(f"  the {lab_}: snaps {int(m_.sum())} | touchdown share {td_[0]:.3f} ±{td_[1]:.3f} | gain bins " + " ".join(f"{l2_} {w_mean(f_(yg_r[m_]).astype(float), g_r[m_])[0]:.3f} ±{w_mean(f_(yg_r[m_]).astype(float), g_r[m_])[1]:.3f}" for l2_, f_ in YB5))

    print("\n=== ab1: the case: first and 10 at the opponent's 18, normal time, tied: 2,000 draws (the kind and its flags from P['kc'], the snap from P['play2'], the gain censored")
    print("    at the goal as the engine does), the share gaining 15 yards or more against the record's share from the 16-20 at first and 10, 2SE by game; the candidate's pools")
    print("    (each season's from the five others), today's pools (e1.py on disk, the same tables) and the plant's (the yard line shuffled among the snaps inside the 20) ===")
    if E1N.count(AB_PLANT_ANCHOR) != 1: stop(f"ab's plant anchor is in the candidate {E1N.count(AB_PLANT_ANCHOR)} times; nothing run")
    for o_ in (AD1P_OLD, AD0P_OLD):
        if E1N.count(o_) != 1: stop(f"an ad plant's anchor is in the candidate {E1N.count(o_)} times; nothing run")
    E1_AD1PLANT = E1N.replace(AD1P_OLD, AD1P_NEW)   # ad1's plant: a spot inside the 1 keyed as the field cell
    if E1N.count(AD3P_OLD) != 1: stop(f"ad addition 2's plant anchor is in the candidate {E1N.count(AD3P_OLD)} times; nothing run")
    if E1N.count(AC_LEVELS_NEW) != 1: stop(f"af1's levels are in the candidate {E1N.count(AC_LEVELS_NEW)} times; nothing run")
    E1_AFPLANT = E1N.replace(AF_LEVELS, V33_LEVELS)   # af1's plant (a regression check): the order before af1 on the candidate's tables
    if E1N.count(AI5_NEW) != 1: stop(f"ai1's levels are in the candidate {E1N.count(AI5_NEW)} times; nothing run")
    E1_AGPLANT = E1N.replace(AI5_NEW, AG5_OLD)   # ag1's plant (a regression check): the levels before ag1 (FULL) on the candidate's tables
    E1_AIPLANT = E1N.replace(AI5_NEW, AG5_NEW)   # ai1's plant: ag1's levels as landed on the candidate's tables
    E1_AD3PLANT = E1N.replace(AD3P_OLD, AD3P_NEW)   # ad addition 2's plant: v34's marking on the line to gain
    E1_AD0PLANT = E1N.replace(AD0P_OLD, AD0P_NEW)   # ad0 (b)'s plant: v33's mark (the floor) writing a spot inside the 1 as 0
    E1_ABPLANT = E1N.replace(AB_PLANT_ANCHOR, AB_PLANT_NEW)   # ab1's plant as registered: the yard line shuffled among the snaps inside the 20 (on the candidate's pools)
    def with_counts(txt_):
        for nm_, o_, n_ in PATCH_AC_COUNT:
            if txt_.count(o_) != 1: stop(f"'{nm_}' is in the text {txt_.count(o_)} times; nothing run")
            txt_ = txt_.replace(o_, n_)
        return txt_
    E1_READ = with_counts(E1_TXT)   # ac0's read engine: the landed e1.py with the counters alone
    if E1_READ.count(AC_LEVELS_OLD) != 1: stop(f"the landed levels line is in e1.py {E1_READ.count(AC_LEVELS_OLD)} times; nothing run")
    E1_PRE = E1_READ.replace(AC_LEVELS_OLD, AC_LEVELS_PRE)   # ab1's 'today' as registered: the pool before ab (the field cells alone)
    E1_ACPLANT = E1_READ.replace(AC_LEVELS_OLD, AC_LEVELS_PLANT)   # ac1's plant: the field cell in place of the 5-yard cell below the yard-line level
    if E1N.count(AC_LEVELS_NEW) != 1 or E1_ACPLANT.count(AC_LEVELS_PLANT) != 1 or E1_PRE.count(AC_LEVELS_PRE) != 1: stop("a levels line is not in its engine once; nothing run")
    MODS_ = {}
    for nm_, tx_ in (("read", E1_READ), ("pre", E1_PRE), ("abplant", E1_ABPLANT), ("acplant", E1_ACPLANT), ("ad1plant", E1_AD1PLANT), ("agplant", E1_AGPLANT), ("aiplant", E1_AIPLANT)):
        m_ = load_mod(tx_, f"e1_v32_{nm_}")
        for k_, v_ in ENGINE_CONF.items(): setattr(m_, k_, v_)
        for k_, v_ in dict(R1A=True, R1B=True, R1D=True, QE_BAND=10).items(): setattr(m_, k_, v_)
        MODS_[nm_] = m_
    for k_, v_ in dict(R1A=True, R1B=True, R1D=True, QE_BAND=10).items(): setattr(e1n, k_, v_)
    RATES_ = {nm_: {s: m_.Rates(s, [TABP[x][0] for x in S if x != s]) for s in S} for nm_, m_ in MODS_.items()}
    print(f"  the engines: the candidate {shs(E1N)} (ac1's levels) | ac0's read engine {shs(E1_READ)} (the landed engine with the counters) | ab1's 'today' {shs(E1_PRE)} (the field cells alone)"
          f" | ab1's plant {shs(E1_ABPLANT)} (the yard line shuffled) | ac1's plant {shs(E1_ACPLANT)} (the field cell below the yard-line level)")
    print("  the levels (level 0 finest): candidate, the model's snap pool (PLAY2_LV) " + str(e1n.PLAY2_LV) + " | the candidate's FULL_YL (the floor's pool) " + str(e1n.FULL_YL) + " | the landed engine " + str(MODS_["read"].FULL_YL) + " | ac1's plant " + str(MODS_["acplant"].FULL_YL))
    m_cell = POOLROWS & (XREC["down"].to_numpy(float) == 1) & (XREC["ydstogo"].to_numpy(float) == 10) & (yl_r >= 16) & (yl_r <= 20)
    REC_CELL = w_mean((yg_r[m_cell] >= 15).astype(float), g_r[m_cell])   # the 16-20 cell: context (af addition item 1)
    m_c = POOLROWS & (XREC["down"].to_numpy(float) == 1) & (XREC["ydstogo"].to_numpy(float) == 10) & (yl_r == 18)   # af addition item 1: the case's own yard line
    REC_CASE = w_mean((yg_r[m_c] >= 15).astype(float), g_r[m_c])
    print(f"  the record: first and 10 from the 16-20 (context), {int(m_cell.sum())} snaps | the share gaining 15+ {REC_CELL[0]:.4f} ±{REC_CELL[1]:.4f}")
    print(f"  the record: first and 10 at the 18 (the case's comparison), {int(m_c.sum())} snaps | the share gaining 15+ {REC_CASE[0]:.4f} ±{REC_CASE[1]:.4f}")
    def case_draws(Rs, m_, s, n=2000):
        rng_ = np.random.default_rng([30, s]); k_ = dict(down=1, dist="7-10", field="opp 20-1", time="normal", score="tied", yl20=18, yl5="16-20", yl5in="16-20", yl20in=18); hit_ = 0
        for _ in range(n):
            s1 = Rs.P["kc"].draw(rng_, dict(tb2=m_.tb2(1, 600), ls=m_.late_score(1, 600, 0), down=1, dist="7-10"))
            o_ = Rs.P["play2"].draw(rng_, dict(k_, kind=s1["kind"], inc_k=s1["inc_k"], ob_k=s1["ob_k"]))
            y_ = int(o_["yards_gained"]); inc_ = int(o_["incomplete_pass"]) if not e1.nan(o_["incomplete_pass"]) else 0; itc_ = int(o_["interception"]) if not e1.nan(o_["interception"]) else 0
            if inc_ or itc_: y_ = 0
            hit_ += int(min(y_, 18) >= 15)
        p_ = hit_ / n; return (p_, 2 * np.sqrt(p_ * (1 - p_) / n), n)
    ARMS_ = (("candidate", lambda s: (R[s], e1n)), ("the landed engine (ab)", lambda s: (RATES_["read"][s], MODS_["read"])), ("today (the pool before ab)", lambda s: (RATES_["pre"][s], MODS_["pre"])),
             ("ab's plant", lambda s: (RATES_["abplant"][s], MODS_["abplant"])), ("ac's plant", lambda s: (RATES_["acplant"][s], MODS_["acplant"])))
    POOLED = {nm_: [0, 0] for nm_, _ in ARMS_}; CASE_BY = {nm_: {} for nm_, _ in ARMS_}
    for s in S:
        parts_ = []
        for nm_, f_ in ARMS_:
            Rs_, m_ = f_(s); v_ = case_draws(Rs_, m_, s); CASE_BY[nm_][s] = within(REC_CASE, v_)[2]; POOLED[nm_][0] += v_[0] * v_[2]; POOLED[nm_][1] += v_[2]
            parts_.append(f"{nm_} {v_[0]:.4f} -> {wd(CASE_BY[nm_][s])}")
        print(f"    season {s}'s pools: " + " | ".join(parts_))
    print("  ac0: the case's 2,000 draws by the level they resolved at (Pool.used after the case; v31 printed 1011, 831, 66, 92 for 2024's landed pools):")
    for s in S:
        lvL_ = [("kind", "inc_k", "ob_k") + l for l in MODS_["read"].FULL_YL]; lvC_ = list(e1n.PLAY2_LV)
        kl_ = lambda lv_, P_: sum(P_.used[i] for i, l in enumerate(lv_) if not ({"yl20", "yl5", "yl5in", "yl20in"} & set(l))) / 2000
        print(f"    {s}: the landed engine {[RATES_['read'][s].P['play2'].used[i] for i in range(len(lvL_))]} | the candidate {[R[s].P['play2'].used[i] for i in range(len(lvC_))]}"
              f" | the keyless share of the case's draws: landed {kl_(lvL_, RATES_['read'][s].P['play2']):.4f} | candidate {kl_(lvC_, R[s].P['play2']):.4f}")
    AB_S = 2024
    print("  ab1's checks as registered: one pooled test, the six seasons' 12,000 draws against the record's share, within 2SE (the record's by game, the draws' binomial); today's pool")
    print("  (the pool before ab) and ab's plant must read APART on it:")
    POOLED_V = {}
    for nm_, (hit_, n_) in POOLED.items():
        p_ = hit_ / n_ if n_ else np.nan; v_ = (p_, 2 * np.sqrt(p_ * (1 - p_) / n_) if n_ else np.nan, n_); POOLED_V[nm_] = (v_, within(REC_CASE, v_)[2])
        print(f"    {nm_}: {p_:.4f} ±{v_[1]:.4f} over {n_} draws | the record at the 18 {REC_CASE[0]:.4f} ±{REC_CASE[1]:.4f} ({int(m_c.sum())} snaps) -> {wd(POOLED_V[nm_][1])} | beside, the 16-20 cell {REC_CELL[0]:.4f} ±{REC_CELL[1]:.4f} -> {wd(within(REC_CELL, v_)[2])}")
    AB_CASE_OK = POOLED_V["candidate"][1] is True; AB_TODAY_APART = POOLED_V["today (the pool before ab)"][1] is False; AB_PLANT_CASE = POOLED_V["ab's plant"][1] is False
    CASE = CASE_BY["candidate"]
    print("\n=== ad0 (b)'s plant, ad1's case and plant ===")
    def mark_zero(m_):
        """ad0 (b): Game.mark on fixed spots inside the 1 (the ball, the line to gain at the goal, gains of 0, to the goal, and back): how many it writes at the 0."""
        n0_ = 0; n_ = 0
        for y0_ in (0.5, 0.75, 0.375, 0.25, 0.125):
            for yg_ in (0.0, y0_, -1.5, -3.0):
                r_ = dict(yardline_100=y0_, ydstogo=y0_, yards_gained=yg_); m_.Game.mark(None, r_); n_ += 1; n0_ += int(r_["yardline_100"] == 0)
        return n0_, n_
    _m0 = load_mod(E1_AD0PLANT, "e1_v34_ad0plant")
    for k_, v_ in ENGINE_CONF.items(): setattr(_m0, k_, v_)
    MZ_C, MZ_P = mark_zero(e1n), mark_zero(_m0)
    AD0_PLANT = MZ_P[0] > 0 and MZ_C[0] == 0
    print(f"  ad0 (b): fixed spots inside the 1 written at the 0: the candidate {MZ_C[0]} of {MZ_C[1]} | the plant (v33's mark) {MZ_P[0]} of {MZ_P[1]} -> {'the plant FAILS as it must' if AD0_PLANT else ('NOT MEASURED (MARK_INSIDE1 unset: the record writes a snap below 1)' if MARK_IN1 is None else 'DID NOT FAIL')}")
    m1r_ = POOLROWS & (yl_r == 1); REC_AT1 = w_mean((yg_r[m1r_] >= 1).astype(float), g_r[m1r_])
    print(f"  ad1: the record at the 1 (the pool's rows, all downs): {int(m1r_.sum())} snaps | touchdown share {REC_AT1[0]:.4f} ±{REC_AT1[1]:.4f} (context only, ad addition item 3)")
    m1g_ = m1r_ & (XREC["down"].to_numpy(float) == 1); REC_FG1 = w_mean((yg_r[m1g_] >= 1).astype(float), g_r[m1g_])
    print(f"  ad addition item 3: the record's first and goal at the 1 (down 1, the pool's rows): {int(m1g_.sum())} snaps | touchdown share {REC_FG1[0]:.4f} ±{REC_FG1[1]:.4f} (the case's comparison)")
    def case05(Rs, m_, s, n=2000):
        rng_ = np.random.default_rng([31, s]); y0_ = 0.5; hit_ = 0; lv_ = Counter()
        k_ = dict(down=1, dist=m_.dist_bin(y0_), field=m_.field_bin(y0_), time="normal", score="tied", yl20=m_.yl20_bin(y0_), yl5=m_.yl5_bin(y0_), yl5in=m_.yl5in_bin(y0_), yl20in=(m_.yl20in_bin(y0_) if hasattr(m_, "yl20in_bin") else None))
        for _ in range(n):
            s1 = Rs.P["kc"].draw(rng_, dict(tb2=m_.tb2(1, 600), ls=m_.late_score(1, 600, 0), down=1, dist=k_["dist"]))
            o_ = Rs.P["play2"].draw(rng_, dict(k_, kind=s1["kind"], inc_k=s1["inc_k"], ob_k=s1["ob_k"])); lv_[Rs.P["play2"].last] += 1
            y_ = float(o_["yards_gained"]) if not e1.nan(o_["yards_gained"]) else 0.0
            if (not e1.nan(o_["incomplete_pass"]) and int(o_["incomplete_pass"])) or (not e1.nan(o_["interception"]) and int(o_["interception"])): y_ = 0.0
            hit_ += int(y_ >= y0_)
        return hit_, n, lv_, k_
    C05 = {}
    for nm_, f_ in (("candidate", lambda s: (R[s], e1n)), ("v33's landed engine", lambda s: (RATES_["read"][s], MODS_["read"])), ("ad1's plant (the field cell)", lambda s: (RATES_["ad1plant"][s], MODS_["ad1plant"]))):
        H_ = N_ = 0; LV_ = Counter(); kk_ = None
        for s in S:
            Rs_, m_ = f_(s); h_, n_, lv_, kk_ = case05(Rs_, m_, s); H_ += h_; N_ += n_; LV_.update(lv_)
        p_ = H_ / N_; v_ = (p_, 2 * np.sqrt(p_ * (1 - p_) / N_), N_); C05[nm_] = (v_, within(REC_FG1, v_)[2])
        print(f"  ad1 case, {nm_}: the key {dict((k2_, kk_[k2_]) for k2_ in ('yl20', 'yl5', 'yl5in', 'field'))} | the touchdown share {p_:.4f} ±{v_[1]:.4f} over {N_} draws -> {wd(C05[nm_][1])}"
              f" | draws by level {dict(sorted(LV_.items()))}")
    AD1_CASE = C05["candidate"][1]; AD1_PLANT = C05["ad1's plant (the field cell)"][1] is False
    print(f"  ad1: the case on the candidate {wd(AD1_CASE)} | the plant {'APART as it must' if AD1_PLANT else 'NOT APART'}")
    print(f"  ab1 as registered: the candidate {'PASS' if AB_CASE_OK else 'FAIL'} | today's pool {'APART as it must' if AB_TODAY_APART else 'NOT APART'} | ab's plant {'FAILS as it must' if AB_PLANT_CASE else 'DID NOT FAIL'}")
    section("ac0, ab1: the pool read, the record inside the 20, the cases")
    if FIXTURE:   # every fit the capped workers made against the same fit uncapped and serial in this process (a tree by its fitted content; the race by its pickled model)
        ser_ = {}
        for s in S: ser_[f"stopped part {s}"] = tree_bytes(fit_part(XS[sS != s], yS[sS != s], sS[sS != s], CAP["stop"])[0]) == tree_bytes(MS[s])
        for ho, fs in FITS.items(): tr_ = np.isin(sR, fs); ser_[f"race held out {ho}"] = lr_bytes(LRRace(XR[tr_], yR[tr_])) == lr_bytes(MR[ho])
        print(f"  the capped workers' fits against uncapped serial fits (quick run): " + " | ".join(f"{k_} {'BYTE-IDENTICAL' if v_ else 'DIFFERENT'}" for k_, v_ in ser_.items()))
        H_FIT = all(ser_.values())
    else: H_FIT = None
    for s in S: R[s].RACE_MODELS = {"run": MR[s if s in STAMPED else "2019-2021"], "stop": MS[s]}
    MODELS_B = {s: pickle.dumps(dict(race=R[s].RACE_MODELS, call4=None, call4_share=None)) for s in S}   # the race's parts in the library's packed form (no choice model: ab carries nothing of aa)
    # v19 r3 (q): the model files the candidate e1.py draws from, staged in the run's own folder (out/engine/ is written only on a landing), each sha in a manifest
    STAGE = os.path.join(tempfile.mkdtemp(), "engine"); os.makedirs(STAGE)
    FLAGS_M = dict(R1A=True, R1B=True, R1D=True, QE_BAND=10)   # the model engine's flags (b), the same the chain's games are played with
    stg_ = {"conf.pkl": pickle.dumps(dict(module=dict(ENGINE_CONF, **FLAGS_M), t_cap=T_CAP, seasons=list(S))), "x6.pkl": pickle.dumps(X6), "sched.pkl": pickle.dumps(sched)}
    stg_.update({f"race_{s}.pkl": pickle.dumps(dict(run=dict(m=R[s].RACE_MODELS["run"].m, mu=R[s].RACE_MODELS["run"].mu, sd=R[s].RACE_MODELS["run"].sd, tcap=R[s].RACE_MODELS["run"].tcap),
                                                    stop=R[s].RACE_MODELS["stop"])) for s in S})   # the race as its parts (e1.py rebuilds it as _LRRace; no chain class pickled)
    for f_, b_ in stg_.items(): open(os.path.join(STAGE, f_), "wb").write(b_)
    shutil.copy(TAB_PATH, os.path.join(STAGE, "tables.pkl"))
    MANIF = dict(files={f_: sh(os.path.join(STAGE, f_)) for f_ in sorted(os.listdir(STAGE))}, chain=CSHA, e1=shs(E1N), transition=shs(TRANS_CAND), mode="quick" if FIXTURE else "full")
    json.dump(MANIF, open(os.path.join(STAGE, "MANIFEST.json"), "w"), indent=1)
    print(f"  q (v19 r3): the model files staged for e1.py alone ({STAGE}; out/engine/ is written only on a landing): " + " | ".join(f"{f_} {v_} ({os.path.getsize(os.path.join(STAGE, f_)) / 1e6:.1f} MB)" for f_, v_ in MANIF["files"].items()))
    section("race: the stopped part and the race fitted")

    print("\n=== c (CONSTRUCTION): the three leak tests ===")
    dkey = {(g, s_): k for k, (g, s_) in enumerate(zip(gid, d["order_sequence"].to_numpy(float)))}
    EXTRA_L = {"clock": qs, "E": Est, "W": Wst, "to_m": to_m, "rv": T["rev"][0].astype(float), "inj": inj.astype(float), "half": half, "seq": d["order_sequence"].to_numpy(float)}
    def game_all(a, b): G = game_cols(a, b); G.update({k_: list(v_[a:b]) for k_, v_ in EXTRA_L.items()}); return G
    def inputs_at(G, k, kind):
        o_ = rebuild(G, G["rb"]); off = o_[0][k]; hm0 = G["home"][0]
        uh = sum(1 for j in range(k + 1) if G["half"][j] == G["half"][k] and G["act"][j] == "timeout" and G["to_m"][j] == hm0)
        ua = sum(1 for j in range(k + 1) if G["half"][j] == G["half"][k] and G["act"][j] == "timeout" and isinstance(G["to_m"][j], str) and G["to_m"][j] != hm0)
        uo, ud = (uh, ua) if off == hm0 else (ua, uh)
        L0_ = G["E"][k] - G["W"][k]
        if kind == "run":
            return [G["q"][k], float(np.round(G["clock"][k] - L0_)), o_[6][k] if not np.isnan(o_[6][k]) else 0.0, o_[1][k], o_[2][k], o_[3][k], max(3 - uo, 0), max(3 - ud, 0), G["rv"][k], G["inj"][k]]
        clk = G["clock"][k] - L0_ if (G["act"][k] in ("snap", "kickoff") and not np.isnan(L0_)) else G["clock"][k]; kk = o_[4][k]
        return [G["q"][k], clk, o_[6][k] if not np.isnan(o_[6][k]) else 0.0, -1.0 if kk else o_[1][k], -1.0 if kk else o_[2][k], -1.0 if kk else o_[3][k], max(3 - uo, 0), max(3 - ud, 0)]
    def plant_col(G, k):
        j = next((j for j in range(k + 1, len(G["act"])) if G["act"][j] == "snap"), None)
        return G["yardline_100"][j] if j is not None else -1.0
    def mutate(G, k):
        M_ = {}
        for c_, v_ in G.items():
            if c_ in ("home", "away", "rb"): M_[c_] = v_ if c_ == "rb" else list(v_); continue
            fut = list(v_[k + 1:])[::-1]
            fut = [(x + 7 if isinstance(x, (int, float, np.floating)) and not (isinstance(x, float) and np.isnan(x)) and c_ not in ("q", "half") else x) for x in fut]
            M_[c_] = list(v_[:k + 1]) + fut
        return M_
    def game_at(k_abs):
        gi = np.searchsorted(gstart, k_abs, side="right") - 1; a, b = gstart[gi], gstart[gi + 1]
        G = game_all(a, b); G["rb"] = TBR[int(seas[a])]; return G, k_abs - a
    rng_l = np.random.default_rng(13)
    pts_run = R23.sample(min(200, len(R23)), random_state=13)
    same = consist = plant_changed = pred_same = 0; nt = 0
    for _, r in pts_run.iterrows():
        i_tb = int(r["i"]); key = (TB.at[i_tb, "game_id"], float(TB.at[i_tb, "seq"]))
        if key not in dkey: continue
        G, k = game_at(dkey[key]); x0 = inputs_at(G, k, "run"); Gm = mutate(G, k); x1 = inputs_at(Gm, k, "run"); nt += 1
        xt = [r[c_] for c_ in RUN_COLS[:-1]]
        consist += int(np.allclose(np.array(x0, float), np.array(xt, float), equal_nan=True))
        same += int(np.allclose(np.array(x0, float), np.array(x1, float), equal_nan=True))
        plant_changed += int(plant_col(G, k) != plant_col(Gm, k))
        M_ = MR[int(r["season"])]
        pred_same += int(np.array_equal(M_.predict_proba(np.array([x0 + [0.0]])), M_.predict_proba(np.array([x1 + [0.0]]))))
    print(f"  test 2 (running clock): {nt} decision points sampled (seed 13); every record after each point changed (the later rows reversed, numbers moved by 7),")
    print(f"    the history up to it held: inputs identical at {same} of {nt}; predictions (the fitted race, frozen) identical at {pred_same} of {nt};")
    print(f"    the table's inputs are the rebuild function's at {consist} of {nt}")
    print(f"  test 1, the plant on test 2: a column copied from the next snap (its yard line) changes at {plant_changed} of {nt} -> {'REFUSED as it must' if plant_changed > 0 else 'NOT REFUSED'}")
    stopi = np.where((act == "snap") & np.isin(state, ["STOP", "PARTIAL"]) & np.isin(seas, STAMPED) & (s_unk == ""))[0]
    stopi = rng_l.choice(stopi, size=min(100, len(stopi)), replace=False) if len(stopi) else stopi
    s_same = s_pred = 0
    for k_abs in stopi:
        G, k = game_at(k_abs); Gm = mutate(G, k); x0 = inputs_at(G, k, "stop"); x1 = inputs_at(Gm, k, "stop")
        s_same += int(np.allclose(np.array(x0, float), np.array(x1, float), equal_nan=True))
        ac_ = float(STOP_ACTS.index("snap STOP" if state[k_abs] == "STOP" else "snap PARTIAL"))
        M_ = MS[int(seas[k_abs])]
        s_pred += int(np.array_equal(M_.predict_proba(np.array([x0 + [ac_, G["rv"][k], G["inj"][k]]])), M_.predict_proba(np.array([x1 + [ac_, Gm["rv"][k], Gm["inj"][k]]]))))
    print(f"  test 2 (stopped clock): {len(stopi)} plays after which the clock stops: inputs identical at {s_same}; predictions identical at {s_pred}")
    LEAK2 = nt > 0 and same == nt and pred_same == nt and s_same == len(stopi) and s_pred == len(stopi) and plant_changed > 0
    print("  test 3 (training cutoff): the held-out-2025 race and the stopped part's 2025 fit, refit on unchanged records (control), then on records where every 2025 row is changed")
    TBm = TB.copy(); m25 = (TBm["season"] == 2025).to_numpy()
    for c_ in ("clock", "play_len", "game_seconds", "s_yl", "s_down", "s_togo", "s_diff", "used_home", "used_away"):
        v_ = TBm.loc[m25, c_].to_numpy(float); TBm.loc[m25, c_] = v_[::-1] + 3
    TBm.loc[m25, "act"] = TBm.loc[m25, "act"].to_numpy(object)[::-1]   # the labels read the next row's act (make_ending)
    RRm = race_rows(TBm)
    SXm, _, _, _ = stop_rows(TBm, RRm)
    NPZ_RM = os.path.join(LIB_DIR, "race_rows_m.npz"); np.savez(NPZ_RM, X=RRm["XR"], y=RRm["yR"], s=RRm["sR"])
    NPZ_SM = os.path.join(LIB_DIR, "stop_rows_m.npz"); np.savez(NPZ_SM, X=SXm[STOP_COLS].to_numpy(float), y=SXm["y"].to_numpy(object), s=SXm["season"].to_numpy())
    o3_ = POOL.run([(L.w_fit_race, (NPZ_R, FITS[2025], "control")), (L.w_fit_race, (NPZ_RM, FITS[2025], "changed")),
                    (L.w_fit_stop, (NPZ_S, 2025, CAP["stop"])), (L.w_fit_stop, (NPZ_SM, 2025, CAP["stop"]))], "leak test 3")   # the controls refitted in every run
    o3, o3s = o3_[:2], o3_[2:]
    b_orig = lr_bytes(MR[2025]); b_ctrl = lr_bytes(pickle.loads(o3[0][1])); b_mut = lr_bytes(pickle.loads(o3[1][1]))
    sb_orig = tree_bytes(MS[2025]); sb_ctrl = tree_bytes(pickle.loads(o3s[0][1])); sb_mut = tree_bytes(pickle.loads(o3s[1][1]))
    print(f"    race: control {'IDENTICAL' if b_ctrl == b_orig else 'DIFFERENT'} (sha {hashlib.sha256(b_orig).hexdigest()[:12]} vs {hashlib.sha256(b_ctrl).hexdigest()[:12]}) | 2025 changed: "
          f"{'IDENTICAL' if b_mut == b_orig else 'DIFFERENT'} (sha {hashlib.sha256(b_mut).hexdigest()[:12]}); the 2025 rows changed {int((RRm['sR'] == 2025).sum())}")
    print(f"    stopped part (compared by fitted content): control {'IDENTICAL' if sb_ctrl == sb_orig else 'DIFFERENT'} | 2025 changed: {'IDENTICAL' if sb_mut == sb_orig else 'DIFFERENT'}")
    LEAK3 = (b_ctrl == b_orig) and (b_mut == b_orig) and (sb_ctrl == sb_orig) and (sb_mut == sb_orig)
    print(f"  leak tests: 1 and 2 {'PASS' if LEAK2 else 'FAIL'} | 3 {'PASS' if LEAK3 else ('NOT JUDGED: a control differs' if (b_ctrl != b_orig or sb_ctrl != sb_orig) else 'FAIL')}")
    section("construction: leak tests")

    print("\n=== v10 d (LOCAL TIMING, CALIBRATION): every eligible held-out row scored; calibration by decile, the miss count judged by game resampling ===")
    for s in STAMPED:
        mm = sR == s; M_ = MR[s]; P = M_.predict_proba(XR[mm]); cl = list(M_.classes_); idx_ = np.array([cl.index(v) if v in cl else -1 for v in yR[mm]]); ok_ = idx_ >= 0
        print(f"  race {s}: rows {int(mm.sum())} | log loss {-np.mean(np.log(np.clip(P[np.where(ok_)[0], idx_[ok_]], 1e-300, None))):.4f} | rows of a class unseen in its fit {int((~ok_).sum())}")
    for s in S:
        mm = sS == s; P = MS[s].predict_proba(XS[mm]); cl = list(MS[s].classes_); idx_ = np.array([cl.index(v) if v in cl else -1 for v in yS[mm]]); ok_ = idx_ >= 0
        print(f"  stopped part {s}: rows {int(mm.sum())} | log loss {-np.mean(np.log(np.clip(P[np.where(ok_)[0], idx_[ok_]], 1e-300, None))):.4f}")
    B_ = 200; CALR = {}
    for plant in (False, True):
        tot = {"race": [0, None, 0], "stopped": [0, None, 0]}; miss_lines = []
        for part, seasons_, Xp, yp, sp, gp, models, hz in (("race", STAMPED, XR, yR, sR, gR_, MR, ("offense", "defense", "snap", "F1", "F2")),
                                                             ("stopped", S, XS, yS, sS, SXf["game_id"].to_numpy(object), MS, ("offense", "defense", "F1", "F2"))):
            for s in seasons_:
                mm = sp == s
                if mm.sum() < 20: continue
                gm = pd.factorize(gp[mm])[0]; G = gm.max() + 1; rg = np.random.default_rng([7, s])
                Wb = np.stack([np.bincount(rg.integers(G, size=G), minlength=G) for _ in range(B_)]).astype(float)
                P = models[s].predict_proba(Xp[mm]); cl = list(models[s].classes_)
                for k in hz:
                    if k not in cl: continue
                    p = np.minimum(P[:, cl.index(k)] * (1.3 if plant else 1.0), 1.0)
                    tests, nullc = cal_tests(p, (yp[mm] == k).astype(float), gm, G, Wb)
                    tot[part][0] += sum(t_[-1] for t_ in tests); tot[part][2] += len(tests); tot[part][1] = nullc if tot[part][1] is None else tot[part][1] + nullc
                    for t_ in tests:
                        if t_[-1] and not plant: miss_lines.append(f"     miss: {part} {s} {k} decile {t_[0]}: predicted {t_[1]:.5f}, observed {t_[2]:.5f} ({t_[3]:+.5f} ±{t_[4]:.5f})")
        for part in ("race", "stopped"):
            nc = tot[part][1]; lim = (nc.mean() + 2 * nc.std(ddof=1)) if nc is not None else np.nan; fail = None if (np.isnan(lim) or not tot[part][2]) else bool(tot[part][0] > lim)   # y0 (a): no allowance or no test: NOT MEASURED
            CALR[(plant, part)] = (tot[part][0], lim, fail)
            print(f"  {'PLANT (x1.3)' if plant else 'fitted'} | {part}: deciles missed {tot[part][0]} of {tot[part][2]} | the bootstrap allows {lim:.1f} -> {'NOT MEASURED' if fail is None else ('FAILS' if fail else 'passes')}")
        if not plant:
            for l_ in miss_lines[:24]: print(l_)
    for part in ("race", "stopped"):
        if not CALR[(True, part)][2] and not FIXTURE: stop(f"the calibration plant did not fail for the {part} part; the check cannot fail")
    print("  the unplayed stoppages: fitted rate (sum of held-out probabilities) against the record's count, and their cost:")
    for s in STAMPED:
        mm = sR == s; cl = list(MR[s].classes_)
        fit_u = MR[s].predict_proba(XR[mm])[:, cl.index("unplayed")].sum() if "unplayed" in cl else 0.0
        z = R23[R23["season"] == s]; gn = z["game_id"].nunique(); u_ = z[z["cls"] == "unplayed"]
        print(f"    {s}: fitted {fit_u:.1f} | record {len(u_)} | a game {len(u_) / max(gn, 1):.3f}, their game seconds after the play a game {u_['tau'].sum() / max(gn, 1):.1f} | kinds {dict(Counter(u_['kind']).most_common(6))}")
    section("race: validation")

    print("\n=== v19 e: consumed by y's landing run (e2b_v25_18a581d0674d: labelling named as the cause); not rerun here (ac's budget) ===")

except (SystemExit, Overtime):
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; the table and the working tables are saved; nothing else written")

try:
    print("\n=== b: the model engine (the race on the floor) plays every game of the original population, each with its own generator, each season in its own process ===")
    FLAGS = dict(R1A=True, R1B=True, R1D=True, QE_BAND=10)
    t_m = time.time()
    # v19 y1's plant (the game clock started at the play's end, through the enforcement) plays 2024's games beside the model's, in the same map
    Y1_PLANT_NEW = Y1_RESTART.replace("self.restart_at = self.t + s_", "self.restart_at = self.t")
    if E1N.count(Y1_RESTART) != 1 or Y1_PLANT_NEW == Y1_RESTART: stop(f"y1's plant anchor is in the candidate {E1N.count(Y1_RESTART)} times; nothing run")
    E1_Y1P = E1N.replace(Y1_RESTART, Y1_PLANT_NEW + "   # PLANT y1: the game clock started at the play's end")
    Y1P_S = 2024
    OUTA = POOL.map(L.w_play, [(E1N, s, sched[sched["season"] == s], TAB_PATH, MODELS_B[s], X6, list(S), FLAGS) for s in S]
                    + [(E1_ACPLANT, AB_S, sched[sched["season"] == AB_S], TAB_PATH, MODELS_B[AB_S], X6, list(S), FLAGS)]
                    + [(E1_READ, s, sched[sched["season"] == s], TAB_PATH, MODELS_B[s], X6, list(S), FLAGS) for s in S]
                    + [(E1_AFPLANT, AB_S, sched[sched["season"] == AB_S], TAB_PATH, MODELS_B[AB_S], X6, list(S), FLAGS)], "the model engine's games (ac1's plant on 2024, the landed engine every season, af1's plant on 2024)")
    OUTM, OUT_PL, OUT_TDS, OUT_AF = OUTA[:len(S)], OUTA[len(S)], OUTA[len(S) + 1:2 * len(S) + 1], OUTA[2 * len(S) + 1]; OUT_TD = OUT_TDS[S.index(AB_S)]
    FRM, CNTM, DECM, SKM, LOGM, SRCM, UNSM = {}, Counter(), [], Counter(), [], {}, {}; nb = 0
    for s, o_ in zip(S, OUTM):
        FRM[s] = o_[0]; DECM += o_[1]; CNTM.update(o_[2]); SKM.update(o_[3]); LOGM += o_[4]; nb += o_[5]; UNSM.update(o_[8])
        for g_, sq_, src_ in o_[6]: SRCM[(g_, int(sq_))] = src_
    print(f"  played side by side in {time.time() - t_m:.0f} s (each season's own seconds {[round(o_[-1]) for o_ in OUTM]}; ac1's plant, {AB_S}: {round(OUT_PL[-1])} s; the landed engine, {AB_S}: {round(OUT_TD[-1])} s)")
    if FIXTURE:
        for k_, v_ in FLAGS.items(): setattr(e1n, k_, v_)
        same_ = True
        for s in S:
            rows_ = play_threaded(e1n, s, sched[sched["season"] == s], R[s], X6)[0]
            same_ = same_ and e1n.text_frame(rows_).to_csv(index=False) == FRM[s].to_csv(index=False)   # (FRM is every game here: the scope applies below)
        print(f"  h, serial against parallel (quick run): every season's engine games {'BYTE-IDENTICAL' if same_ else 'DIFFERENT'}"); H_PLAY = same_
    else: H_PLAY = None
    # ---- v19 r3 (q): e1.py alone, in a folder with no out/work/, plays the quick-run games from the staged model files; byte-identical to this run's? ----
    import subprocess
    ALONE_DIR = tempfile.mkdtemp(); SKIP_ = {"out", "e1.py", "transition.py", "test_transition.py", "__pycache__", "evidence"}
    for f_ in os.listdir("."):
        if f_ not in SKIP_ and not f_.startswith("."): os.symlink(os.path.abspath(f_), os.path.join(ALONE_DIR, f_))
    open(os.path.join(ALONE_DIR, "e1.py"), "w").write(E1N); open(os.path.join(ALONE_DIR, "transition.py"), "w").write(TRANS_CAND)
    os.makedirs(os.path.join(ALONE_DIR, "out")); os.symlink(STAGE, os.path.join(ALONE_DIR, "out", "engine"))
    if FIXTURE: G_AL = sorted(set(sched["game_id"]))
    else:
        FXP_ = "fixtures/real_games.csv.gz"
        G_AL = sorted(set(pd.read_csv(FXP_, usecols=["game_id"], dtype=str)["game_id"])) if sh(FXP_) == "bcdcac8081cf" else []
    GJ_ = os.path.join(ALONE_DIR, "alone_games.json"); json.dump(G_AL, open(GJ_, "w")); OD_ = os.path.join(ALONE_DIR, "alone_out")
    env_ = dict(os.environ, PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
    t_al = time.time()
    try:
        pr_ = subprocess.run([sys.executable, "-c", "import sys, e1; e1.alone_main(sys.argv[1:])", "out/engine", OD_, GJ_], cwd=ALONE_DIR, env=env_,
                             capture_output=True, text=True, timeout=max(min(left() - 60, 300), 30))
        AL_OUT = (pr_.returncode, pr_.stdout[-4000:], pr_.stderr[-3000:])
    except subprocess.TimeoutExpired:
        AL_OUT = (None, "", "timed out")
    print(f"  q (v19 r3): e1.py {shs(E1N)} alone (its own folder {ALONE_DIR}: the project's files linked but out/, no out/work/; transition.py the candidate"
          f" {shs(TRANS_CAND)}; out/engine/ the staged model files) on the quick-run games ({len(G_AL)}): exit {AL_OUT[0]} in {time.time() - t_al:.0f} s")
    for l_ in AL_OUT[1].strip().split("\n"): print(f"    {l_}")
    if AL_OUT[2].strip(): print("    its errors: " + AL_OUT[2].strip().replace("\n", "\n    "))
    al_cmp = []
    if AL_OUT[0] == 0 and G_AL:
        for s in S:
            ch_ = FRM[s][FRM[s]["game_id"].isin(G_AL)].reset_index(drop=True)
            pf_ = os.path.join(OD_, f"alone_{s}.csv")
            if not len(ch_) and not os.path.exists(pf_): continue
            al_ = open(pf_).read() if os.path.exists(pf_) else None
            al_cmp.append((s, ch_["game_id"].nunique(), al_ is not None and al_ == ch_.to_csv(index=False)))
    AL_SAME = bool(al_cmp) and all(x_[2] for x_ in al_cmp)
    print(f"  q: e1.py alone against this run's games, season by season: {al_cmp} -> {'BYTE-IDENTICAL' if AL_SAME else 'NOT IDENTICAL (or not run)'}"
          f" (fails: any season different, missing, or e1.py alone not exiting 0)")
    # the sha check's own plant: the staged files with conf.pkl changed by one byte after the manifest; e1.py alone must refuse to play (exit not 0, 'DIFFERS')
    STAGE_P = os.path.join(tempfile.mkdtemp(), "engine"); os.makedirs(STAGE_P)
    for f_ in os.listdir(STAGE):
        if f_ == "conf.pkl": open(os.path.join(STAGE_P, f_), "wb").write(open(os.path.join(STAGE, f_), "rb").read() + b"\x00")
        else: os.symlink(os.path.join(STAGE, f_), os.path.join(STAGE_P, f_))
    try:
        pp_ = subprocess.run([sys.executable, "-c", "import sys, e1; e1.alone_main(sys.argv[1:])", STAGE_P, OD_ + "_plant", GJ_], cwd=ALONE_DIR, env=env_,
                             capture_output=True, text=True, timeout=max(min(left() - 30, 120), 10))
        AL_PLANT = pp_.returncode != 0 and "DIFFERS" in pp_.stdout and not (os.path.isdir(OD_ + "_plant") and os.listdir(OD_ + "_plant"))
        print(f"  q, the sha check's plant (conf.pkl changed by one byte after the manifest): exit {pp_.returncode} | {[l_ for l_ in pp_.stdout.split(chr(10)) if 'DIFFERS' in l_]}"
              f" -> {'REFUSED as it must (nothing played)' if AL_PLANT else 'NOT REFUSED'}")
    except subprocess.TimeoutExpired:
        AL_PLANT = False; print("  q, the sha check's plant: timed out -> NOT REFUSED")
    E1_ALONE = AL_SAME and AL_PLANT
    nG_ALL = sum(f["game_id"].nunique() for f in FRM.values())
    UNSG = {g for g, v in UNSM.items() if v}; N_UNS = sum(len(v) for v in UNSM.values())
    print(f"  coverage: games {nG_ALL} | games with an UNSUPPORTED continuation drawn {len(UNSG)} ({share(len(UNSG), nG_ALL)}) | unsupported continuations drawn {N_UNS}"
          f" ({N_UNS / max(nG_ALL, 1):.3f} a game; the record's 'unplayed' labels before the continuation, v15's read: 5.59 on a stopped clock and 0.09 on a running one a game) | by kind: {dict(Counter(w_.split(': ')[0] if w_.startswith('a foul on the play') else w_ for v in UNSM.values() for _, w_ in v).most_common(8))}")
    WHY_ALL = Counter(w_.split(": ", 1)[1] for v in UNSM.values() for _, w_ in v if w_.startswith("a foul on the play"))
    N_FOUL_U = sum(1 for v in UNSM.values() for _, w_ in v if w_.startswith("a foul on the play"))
    print(f"  s2: the unsupported fouls on the play, every reason with its count ({len(WHY_ALL)} reasons; none cut):")
    for k_, v_ in WHY_ALL.most_common(): print(f"    {v_:5d}  {k_}")
    print(f"    the reasons sum to {sum(WHY_ALL.values())} | the total {N_FOUL_U} -> {'EQUAL' if sum(WHY_ALL.values()) == N_FOUL_U else 'NOT EQUAL'} (fails: any difference)")
    S4D = Counter()
    for k_, v_ in WHY_ALL.items():
        m_ = re.search(r"a score or a change of possession on the (?:drawn )?play \((a touchdown|a safety|an interception|a fumble lost); by the (offense|defense)\)", k_)
        if m_: S4D[(m_.group(1), "by the team that snapped" if m_.group(2) == "offense" else "by the other team")] += v_
    print(f"  s4 (a read): the drawn fouls with a score or a change of possession, by case and by the team that fouled, UNSUPPORTED (the try's, the kickoff's and"
          f" the succeeding spot's enforcement not played; the owner's ruling): {dict(sorted(S4D.items()))} | total {sum(S4D.values())}")
    print("  every game stays in every count and check below (no game removed for what it drew); FULL-GAME ACCEPTANCE IS BLOCKED while any unsupported continuation is drawn:"
          " a supported path tests construction locally, never an unconditional game result")
    nG = nG_ALL
    print(f"  games {nG} | batches {nb} | " + " | ".join(f"{k} {v} ({v / max(nG, 1):.3f} a game)" for k, v in sorted(CNTM.items()) if any(w in k for w in ("race", "e:", "f:", "foul")) or k == "timeouts"))
    if SKM: print(f"  games not played: {dict(SKM)}")
    UNSUP_PART = CNTM.get("f: injury plays (drawn), unsupported: participation", 0)
    section("model engine: played")
    print("\n=== h: the engine's games counted (E2a's function) and section 4's checks, one shared parse a season, each season in its own process ===")
    t_e = time.time()
    S_SUP = [s for s in S if len(FRM[s])]
    EV = POOL.map(L.w_eval, [(s, FRM[s], X6, True, True) for s in S_SUP], "the engine's games counted and checked")
    print(f"  evaluated side by side in {time.time() - t_e:.0f} s (each season's own seconds {[round(e_['sec']) for e_ in EV]})")
    def _same_ev(a_, b_):
        ok_ = all(a_[k].reset_index(drop=True).equals(b_[k].reset_index(drop=True)) for k in ("G", "PO", "ST", "TM"))
        x_, y_ = a_["sec4"], b_["sec4"]
        ok_ = ok_ and x_["w4"] == y_["w4"] and x_["C1"] == y_["C1"] and dict(x_["CK"]) == dict(y_["CK"]) and sorted(map(str, x_["FL"])) == sorted(map(str, y_["FL"])) and dict(x_["PO"]) == dict(y_["PO"]) and x_["SR"] == y_["SR"]
        return ok_
    chk_s = S_SUP if FIXTURE else ([2024] if 2024 in S_SUP else S_SUP[:1])
    H_SHARED = all(_same_ev(EV[S_SUP.index(s)], eval_season(s, FRM[s], X6, shared=False, checks=True)) for s in chk_s)
    print(f"  h: the shared parse against separate parses ({'every season, quick run' if FIXTURE else 'season 2024'}): {'EQUAL' if H_SHARED else 'DIFFERENT'}"
          + (" | serial (this process) against parallel: the same comparison" if FIXTURE else ""))
    FAILPM = [x for e_ in EV for x in e_["failp"]]
    if FAILPM: stop("E2a v3's points check fails on an engine run")
    GM = pd.concat([e_["G"] for e_ in EV], ignore_index=True); POM = pd.concat([e_["PO"] for e_ in EV], ignore_index=True); STM = pd.concat([e_["ST"] for e_ in EV], ignore_index=True)
    rc_ = GM["clock_pre"] + GM["clock_stretch"] + GM["clock_post"]
    if (rc_ != 3600).any(): stop("an engine game's regulation clock is not 3,600")
    dM = pd.concat([e_["dM"] for e_ in EV], ignore_index=True); TM_M = pd.concat([e_["TM"] for e_ in EV], ignore_index=True)
    section("model engine: counted")

    print("\n=== v10 d, j (LOCAL TIMING): percentiles of the time after the play, by end and time bin, record 2023-2025 | model engine 2023-2025 (2SE by game) ===")
    LG = pd.DataFrame(LOGM, columns=["game_id", "season", "q", "ce", "end", "t"])
    LG["tb2"] = [("last 2:00 of the game" if a_ == 4 and b_ <= 120 else e1.time_bin(a_, b_)) for a_, b_ in zip(LG["q"], LG["ce"])]
    REC_T = R23.rename(columns={"tau": "t", "cls": "end"}); tim = Counter(); MED = {}
    for en in ("snap", "offense", "defense"):
        for b in TB2:
            a_ = REC_T[(REC_T["end"] == en) & (REC_T["tb2"] == b)]; m_ = LG[(LG["end"] == en) & (LG["tb2"] == b) & LG["season"].isin(STAMPED)]
            if len(a_) < 2 or len(m_) < 2: print(f"  {en} | {b}: rows {len(a_)} | {len(m_)}: fewer than 2 on a side: its 3 cells NOT MEASURED (y0 a)"); tim[None] += 3; continue
            parts = []
            for qq in (10, 50, 90):
                ra, rb_ = boot(a_, "t", qq), boot(m_, "t", qq); dd_, s_, ok = within(ra, rb_); tim[ok] += 1
                if qq == 50: MED[(en, b)] = (ra, rb_, ok)
                parts.append(f"p{qq} {ra[0]:.0f}±{ra[1]:.1f} | {rb_[0]:.0f} ({wd(ok)})")
            print(f"  {en} | {b} (rows {len(a_)} | {len(m_)}): " + " || ".join(parts))
    TIM_N = (tim[True], tim[True] + tim[False], tim[None])
    print(f"  timing cells within 2SE: {TIM_N[0]} of {TIM_N[1]} measured | NOT MEASURED {TIM_N[2]} (prediction m: at least 18 of 36)")
    print("  j, hurry-up: the median wait to the snap by time bin (record | engine), re-measured after b-h:")
    for b in TB2:
        if ("snap", b) in MED: ra, rb_, ok = MED[("snap", b)]; print(f"    {b}: record {ra[0]:.0f} s | engine {rb_[0]:.0f} s -> {wd(ok)}")
    late_miss = [b for b in ("last 2:00 of the first half", "last 2:00 of the game") if ("snap", b) in MED and MED[("snap", b)][2] is False]
    if late_miss:
        print("  j: the late-half cells still miss, so the race's fitted hazard of the snap by elapsed second against the record's empirical hazard there (held-out rows):")
        tbr = np.array([("last 2:00 of the game" if a_ == 4 and b_ <= 120 else e1.time_bin(a_, b_)) for a_, b_ in zip(R23["q"], R23["ce"])], dtype=object)[np.repeat(np.arange(len(R23)), np.where(R23["cls"] == "boundary", R23["tau"], R23["tau"] + 1).astype(int))]
        for b in late_miss:
            parts = []
            for t_ in range(0, T_CAP + 1, 4):
                m_ = (tbr == b) & (np.minimum(tt, T_CAP) == t_)
                if m_.sum() < 5: continue
                fit_h = np.mean([MR[s].predict_proba(XR[m_ & (sR == s)])[:, list(MR[s].classes_).index("snap")].mean() for s in STAMPED if (m_ & (sR == s)).any()])
                parts.append(f"t{t_}: {np.mean(yR[m_] == 'snap'):.3f}/{fit_h:.3f}")
            print(f"    {b} (record/fitted, at risk n by t): " + " ".join(parts))
    section("validation: timing percentiles")

    print("\n=== p, f, e, h (CONSTRUCTION and DOWNSTREAM checks of the engine's mechanisms) ===")
    def fam_counts(dx):
        out = Counter()
        f_ = dx[(dx["play_type"] == "no_play") & (dx["penalty"] == 1)]
        for _, r in f_.iterrows():
            fm = e1.family(r["penalty_team"], r["posteam"], r["penalty_type"], True, e1.has_play(str(r["desc"])), str(r["desc"]))
            if fm in ("F1", "F2"): out[(r["game_id"], fm)] += 1
        return out
    FCR, FCF, FCM = fam_counts(dR), fam_counts(dF), fam_counts(dM)
    for fm in ("F1", "F2"):
        vals = []
        for nm_, FC, gs_ in (("record", FCR, GR["game_id"]), ("floor (the removed pool 'pre')", FCF, GF["game_id"]), ("model", FCM, GM["game_id"])):
            vals.append((nm_, mg([FC.get((g, fm), 0) for g in gs_])))
        dd_ = within(vals[0][1], vals[2][1])
        print(f"  p: pre-snap fouls {fm} a game: " + " | ".join(f"{nm_} {v[0]:.3f} ±{v[1]:.3f}" for nm_, v in vals) + f" -> model {wd(dd_[2])} 2SE of the record")
    P_OK = all(within(mg([FCR.get((g, fm), 0) for g in GR["game_id"]]), mg([FCM.get((g, fm), 0) for g in GM["game_id"]]))[2] for fm in ("F1", "F2"))
    # e (v18): v13's and v17's printed values (their full runs; v16 played no game), and where this run drew each family
    PREV_F = {"F1": dict(v13=(2.768, 0.081, 2387, 2249, 1086, "1718 of 109,197"), v17=(2.517, 0.078, 2046, 2159, 1103, "2255 of 150,455")),
              "F2": dict(v13=(0.624, 0.038, 516, 526, 207, "394 of 109,197"), v17=(0.622, 0.039, 500, 546, 211, "529 of 150,455"))}
    print("  e (v18): F1 and F2 a game against v13's and v17's full runs (printed values; v16 played no game), and where each was drawn (the race on a running")
    print("    clock, the stopped part after a stopped moment) with the labels each was fitted on (the race's rows labeled F1/F2; the stopped part's moments):")
    for fm in ("F1", "F2"):
        now_ = mg([FCM.get((g, fm), 0) for g in GM["game_id"]]); rr_ = CNTM.get(f"race: pre-snap foul {fm} on a running clock", 0); rs_ = CNTM.get(f"race (stopped): pre-snap foul {fm}", 0)
        print(f"    {fm}: this run {now_[0]:.3f} ±{now_[1]:.3f} | drawn on a running clock {rr_} ({rr_ / max(nG, 1):.3f} a game), after a stopped moment {rs_} ({rs_ / max(nG, 1):.3f})"
              f" | labels: race {int((yR == fm).sum())}, stopped part {int((SXf['y'] == fm).sum())} of {len(SXf):,}")
        for k_, v_ in PREV_F[fm].items():
            print(f"      {k_}: {v_[0]:.3f} ±{v_[1]:.3f} | drawn on a running clock {v_[2]} ({v_[2] / 1676:.3f} a game), after a stopped moment {v_[3]} ({v_[3] / 1676:.3f}) | labels: race {v_[4]}, stopped part {v_[5]}")
    print(f"    the model's plays a game this run {GM['snaps_reg'].astype(float).mean():.2f} (v13 and v17 printed theirs in their own runs); fewer snaps give the race fewer stretches to draw F1 in")
    def wiped_pg(dx, games):
        m_ = (dx["play_type"] == "no_play") & (dx["penalty"] == 1) & dx["desc"].astype(str).map(e1.has_play)
        return mg(dx[m_].groupby("game_id").size().reindex(games, fill_value=0).astype(float))
    WIP = (wiped_pg(dR, GR["game_id"]), wiped_pg(dM, GM["game_id"]))
    print(f"  p (the continuation, DOWNSTREAM): downs whose play a foul wiped, a game: record {WIP[0][0]:.3f} ±{WIP[0][1]:.3f} | model {WIP[1][0]:.3f} ±{WIP[1][1]:.3f}"
          f" -> {wd(within(WIP[0], WIP[1])[2])} 2SE (every game; the unsupported fouls drawn are played without their foul, so the model's count is short by them)")
    inj_r = SXf[SXf["inj"] == 1]; to_r = inj_r["y"].isin(["offense", "defense"])
    dMs = dM.reset_index(drop=True); inj_m = dMs["desc"].astype(str).str.contains("injur", case=False).to_numpy()
    nxt_to = np.r_[(dMs["timeout"].to_numpy() == 1)[1:], False] & np.r_[dMs["game_id"].to_numpy()[1:] == dMs["game_id"].to_numpy()[:-1], False]
    print(f"  f: a timeout right after an injury play: record {to_r.mean() if len(inj_r) else float('nan'):.4f} of {len(inj_r)} | engine {nxt_to[inj_m].mean() if inj_m.any() else float('nan'):.4f} of {int(inj_m.sum())}")
    lk = inj_r[(inj_r["q"].isin([2, 4])) & (inj_r["clock"] <= 120) & to_r]
    print(f"  f, counted once: the record's timeouts after an injury play after the warning {len(lk)} (4-5-4's charge or a team's own call: the record does not separate them;"
          f" UNRESOLVED, counted; the engine charges none from the injury itself, the stopped part's timeout hazard (injury an input) is the one path)")
    print(f"  f: 'unsupported: participation' (who is on the field after an injury is not played): {UNSUP_PART} injury plays in the engine, {int(SXf['inj'].sum())} in the record's stopped moments")
    rvm = TB["rv"].to_numpy(float) == 1; sn_ = TB["act"].to_numpy(object) == "snap"
    print("  e: the parts of a review, each printed supported or unsupported against the record's reviewed plays:")
    vr = [(hw, v) for hw, v in VER.items()]
    rv_d = (act == "snap") & (T["rev"][0] == 1); nr_d = (act == "snap") & (T["rev"][0] != 1) & ~s_kick
    def agree(m_):
        m_ = m_ & (nsp >= 0) & ~s_kick
        if not m_.any(): return np.nan, 0
        j_ = nsp[m_]; ok_ = (s_off[m_] == pos[j_]) & (s_dn[m_] == dn[j_]) & (np.abs(s_yl[m_] - d["yardline_100"].to_numpy(float)[j_]) < 0.5)
        return ok_.mean(), int(m_.sum())
    a_rv, n_rv = agree(rv_d); a_nr, n_nr = agree(nr_d)
    sup = lambda ok: "NOT MEASURED" if ok is None else ("SUPPORTED" if ok else "UNSUPPORTED")
    ok_ddp = None if (np.isnan(a_rv) or np.isnan(a_nr)) else (n_rv >= 20 and abs(a_rv - a_nr) <= 2 * np.sqrt(max(a_rv * (1 - a_rv), 1e-9) / max(n_rv, 1)))   # y0 (a): a share not a number is NOT MEASURED
    print(f"    down, distance, possession, score (the drawn post-review outcome; the rebuilt state against the next snap): reviewed {a_rv:.4f} of {n_rv} | not reviewed {a_nr:.4f}"
          f" -> {sup(ok_ddp)} ({'fewer than 20 reviewed plays: nothing to judge' if n_rv < 20 else 'supported when the reviewed plays agree as often as the others, within 2SE'})")
    # clock and restart after a reviewed play: the record's reviewed snaps against the engine's drawn reviewed plays (each can fail)
    rsel = sn_ & rvm & TB["season"].isin([2023, 2024, 2025]).to_numpy() & TB["play_len"].notna().to_numpy() & (TB["transition"] == "same quarter").to_numpy()
    ra_r = (TB["game_seconds"] - TB["play_len"]).to_numpy(float)[rsel]; rg_r = TB["game_id"].to_numpy(object)[rsel]
    e_ = dMs.copy(); e_["L"] = (pd.to_datetime(e_["end_clock_time"], errors="coerce") - pd.to_datetime(e_["time_of_day"], errors="coerce")).dt.total_seconds()
    e_["clk"] = e_["quarter_seconds_remaining"].astype(float)
    same_ = (e_["game_id"].shift(-1) == e_["game_id"]) & (e_["qtr"].shift(-1) == e_["qtr"])
    e_["run_after"] = np.where(same_, e_["clk"] - e_["clk"].shift(-1) - e_["L"], np.nan)
    rvcol = e_["replay_or_challenge"].fillna(0).astype(float) if "replay_or_challenge" in e_.columns else pd.Series(0.0, index=e_.index)
    esel = e_["play_type"].isin(list(rules.SNAP_KINDS)) & (rvcol == 1) & (e_["qtr"] <= 4) & e_["run_after"].notna()
    ra_e = e_.loc[esel, "run_after"].to_numpy(float); rg_e = e_.loc[esel, "game_id"].to_numpy(object)
    def two(vr, gr, ve, ge, nm_):
        if len(vr) < 20 or len(ve) < 20:
            print(f"    {nm_}: record {np.mean(vr) if len(vr) else float('nan'):.3f} of {len(vr)} | engine {np.mean(ve) if len(ve) else float('nan'):.3f} of {len(ve)} -> UNSUPPORTED (fewer than 20 on a side: nothing to judge)"); return False
        a_ = (vr.mean(), gse2(vr, gr)); b_ = (ve.mean(), gse2(ve, ge)); d_, s_, ok_ = within(a_, b_)
        print(f"    {nm_}: record {a_[0]:.3f} ±{a_[1]:.3f} of {len(vr)} | engine {b_[0]:.3f} ±{b_[1]:.3f} of {len(ve)} | {d_:+.3f} ±{s_:.3f} -> {sup(ok_)}"); return ok_
    print(f"    clock (15-5-1: the ruling that stands sets it, by 4-3; rules.clock_class reads a review as {rules.CLOCK_EVENTS['replay review 15-5-1']}); the record's reviewed snaps by class {dict(Counter(state[rv_d]))}:")
    two(ra_r, rg_r, ra_e, rg_e, "clock run from a reviewed play's end to the next row (s; 2023-2025 stamped)")
    print("    restart (the clock starting on the ready signal or the snap, by the class of the ruling that stands):")
    two((ra_r > 1).astype(float), rg_r, (ra_e > 1).astype(float), rg_e, "share of reviewed plays after which the clock ran more than 1 s before the next row")
    print("    15-5-2 as the engine plays it: every condition its season's printed article names (a reversal; a play begun after the warning; the on-field ruling's clock")
    print("      stopped, read from the drawn row's text before the review phrase; the standing ruling's clock running, or restarting where the article says so; a charged")
    print("      timeout that avoids it, drawn by the stopped part; under 10 s ends the half) -> the transition implemented completely for the played seasons (2026's play")
    print("      clock reset reads no played season)")
    rr2 = TB[sn_ & rvm & (TB["review"].astype(str).str.startswith("REVERSED")) & TB["q"].isin([2, 4]) & (TB["clock"] <= 120) & TB["play_len"].notna() & (TB["transition"] == "same quarter")]
    run_after = (rr2["game_seconds"] - rr2["play_len"]).to_numpy(float)
    print(f"    the clock run after reversed reviews inside the last 2:00 (the record, stamped): {len(rr2)} plays | median {np.median(run_after) if len(rr2) else float('nan'):.1f} s"
          f" | the engine's 15-5-2 runoffs {CNTM.get('e: 10-second runoff after a reversal (15-5-2)', 0)} -> {'printed (too few to judge)' if len(rr2) < 20 else 'printed'}")
    ch_ = TB[sn_ & rvm & TB["chal_team"].notna() & ~TB["review"].astype(str).str.startswith("REVERSED")].copy()
    drop_ = []
    for i in ch_.index:
        if i + 1 >= len(TB) or TB.at[i + 1, "game_id"] != TB.at[i, "game_id"]: continue
        side = "home_to_rem" if TB.at[i, "chal_team"] == TB.at[i, "home"] else "away_to_rem"
        b_, a2 = TB.at[i, side], TB.at[i + 1, side]
        if pd.notna(b_) and pd.notna(a2): drop_.append(b_ - a2)
    dr_ = np.array(drop_, float)
    print(f"    timeout charged for a lost challenge (15-6-1; the record's text separates a coach's challenge, 'XX challenged', from a booth review): {len(ch_)} lost challenges |"
          f" the challenger's timeouts remaining fell by one on the next row in {np.mean(dr_ == 1) if len(dr_) else float('nan'):.4f} of {len(dr_)}"
          f" -> {sup(None if not len(dr_) else (len(dr_) >= 20 and np.mean(dr_ == 1) >= 0.5))} | the engine charged {CNTM.get('e: a lost challenge charged a timeout (no row)', 0)} (no row written: counted once)")
    eng_sn = dMs[dMs["play_type"].isin(list(rules.SNAP_KINDS)) & (dMs["qtr"].isin([2, 4]))].copy()
    eng_sn["L"] = (pd.to_datetime(eng_sn["end_clock_time"]) - pd.to_datetime(eng_sn["time_of_day"])).dt.total_seconds()
    nxt_w = dMs["desc"].astype(str).shift(-1).fillna("").str.startswith("Two-Minute")
    c0 = eng_sn["quarter_seconds_remaining"].astype(float); cross = (c0 > 120) & (c0 - eng_sn["L"] <= 120) & (c0 - eng_sn["L"] > 0)
    agree_w = (cross == nxt_w.loc[eng_sn.index]).mean() if len(eng_sn) else np.nan
    print(f"  h: one drawn length per play drives the clock and the warning: engine snaps in quarters 2 and 4 where 'the play's own stamped length ran past 2:00'"
          f" and 'a warning row follows' agree: {agree_w:.4f} of {len(eng_sn)}")
    c454 = {k_: v_ for k_, v_ in CNTM.items() if k_.startswith("f: 4-5-4") or k_.startswith("f: injury not played")}
    print(f"  d, 4-5-4 in the engine: {c454 if c454 else 'no injury after the warning drawn'}")
    c1552 = {k_: v_ for k_, v_ in CNTM.items() if "15-5-2" in k_}
    print(f"  d, 15-5-2 in the engine: {c1552 if c1552 else 'no reversal of a play begun after the warning drawn'}")
    # ---- v19 b: the engine's no-play downs by their out_of_bounds mark against the record's ----
    def ob_share(dx):
        m_ = ((dx["play_type"] == "no_play") & (dx["penalty"] == 1) & dx["desc"].astype(str).map(e1.has_play)).to_numpy()
        v_ = pd.to_numeric(dx.loc[m_, "out_of_bounds"], errors="coerce").to_numpy(float); g_ = dx.loc[m_, "game_id"].to_numpy(object); ok_ = ~np.isnan(v_)
        return (float(v_[ok_].mean()) if ok_.any() else np.nan, gse2(v_[ok_], g_[ok_]) if ok_.sum() > 1 else np.nan, int(ok_.sum()), int((v_[ok_] == 1).sum()), int((~ok_).sum()))
    OBR, OBM = ob_share(dR), ob_share(dM)
    v1_, g1_ = OB_REC1; k1_ = ~np.isnan(v1_); OB1 = (float(v1_[k1_].mean()), gse2(v1_[k1_], g1_[k1_]))
    print(f"  r4 (v19 b): the no-play downs whose play a foul wiped, by out_of_bounds mark (2SE by game): record (category 1, the rebuild's sort) marked {int((v1_[k1_] == 1).sum())},"
          f" not marked {int((v1_[k1_] == 0).sum())}, empty {int((~k1_).sum())}: share {OB1[0]:.4f} ±{OB1[1]:.4f} | engine (its wiped downs, every game) marked {OBM[3]},"
          f" not marked {OBM[2] - OBM[3]}, empty {OBM[4]}: share {OBM[0]:.4f} ±{OBM[1]:.4f} -> {wd(within((OB1[0], OB1[1], int(k1_.sum())), (OBM[0], OBM[1], OBM[2]))[2])} 2SE")
    print(f"    (the record read as part 2 read it, no-play rows with a foul and a play in the text: {OBR[3]} of {OBR[2]}, {OBR[0]:.4f} ±{OBR[1]:.4f}; the falsifier's 959 and 8,703 are category 1's)")
    print("    the clock rules that read the mark: r2's stretch classes read it on the stretch's first row (4-3-2a: out of bounds late STOP inside the windows,")
    print("    early outside them); the engine's clock after a wiped down is 4-3-2e's (foul_clock), which does not read it; inside the windows both stop the clock")

    # ---- v19 g: the race's F1 on a running clock: the rate a second and the exposure (seconds a game), the engine against the record, 2023-2025 ----
    print("  g (v19): v13 is not testable (its games were not saved); the engine against the record, 2023-2025, the race's F1 on a running clock:")
    for s in STAMPED:
        c_ = OUTM[S.index(s)][2]; ng_ = FRM[s]["game_id"].nunique(); sec_ = c_.get("g (v19): race seconds at risk, a running clock", 0); f1_ = c_.get("race: pre-snap foul F1 on a running clock", 0)
        mm_ = sR == s; rsec_ = int(mm_.sum()); rf1_ = int((yR[mm_] == "F1").sum()); rg_ = R23.loc[R23["season"] == s, "game_id"].nunique()
        rr_, re_ = (rf1_ / rsec_ if rsec_ else np.nan), (f1_ / sec_ if sec_ else np.nan)
        se_ = 2 * np.hypot(np.sqrt(rf1_) / max(rsec_, 1), np.sqrt(f1_) / max(sec_, 1))   # a count's 2SE (Poisson), not by game: declared
        print(f"    {s}: rate (F1 a second at risk) record {rr_:.6f} ({rf1_} of {rsec_}) | engine {re_:.6f} ({f1_} of {sec_}) -> {'NOT MEASURED' if (not rsec_ or not sec_) else ('within' if abs(rr_ - re_) <= se_ else 'APART')} 2SE (a count's)"
              f" | exposure (seconds at risk a game) record {rsec_ / max(rg_, 1):.1f} over {rg_} games | engine {sec_ / max(ng_, 1):.1f} over {ng_} games")
    print("    (the record's seconds are the race's eligible stretches only; the engine's every stretch it walks: declared, not adjusted)")

    # ---- v19 part 2 (1), (2): the fouls on the play by their article; no draw given probability 0 for its recorded yards ----
    UWHY = Counter(w_.split(": ", 1)[1] for v in UNSM.values() for _, w_ in v if w_.startswith("a foul on the play"))
    print(f"  k: wiped downs enforced by the book's yards {CNTM.get('foul on the play, the play wiped: yards by the article (the book)', 0)} | by the spot of the foul (pass interference)"
          f" {CNTM.get('foul on the play, the play wiped: yards by the article (the spot of the foul)', 0)}")
    K_OWN = "v19 r1: pass interference's depth, the drawn row's own (uncensored)"; K_CEN = "v19 r1: pass interference's depth, censored: drawn from the uncensored depths at least its bound"
    print(f"  r1: pass interference's depth: the drawn row's own {CNTM.get(K_OWN, 0)} | censored, drawn from the uncensored depths at least its bound {CNTM.get(K_CEN, 0)}"
          f" | unsupported for 'the pass's length unread' {sum(v_ for k_, v_ in UWHY.items() if 'length' in k_ and 'unread' in k_)} (prediction 0; part 2: 1,544)"
          f" | other pass interference draws unsupported: {dict((k_, v_) for k_, v_ in UWHY.items() if k_.startswith('pass interference'))}")
    N_HALF_U = sum(v_ for k_, v_ in UWHY.items() if "half-yard spot" in k_)
    print(f"  s1: half-yard spots unsupported {N_HALF_U} (prediction 0; r: 429) | a spot off a whole yard written in the record's marking (rounded toward the attacked goal;"
          f" the record's own shares 0.871 (666 of 765) and {HALF_MARK_SHARE} here, the owner's ruling; t's counter of those rows deleted, x4) | games not played {sum(SKM.values())}")
    def dpi_pg(dx, games):
        m_ = (dx["play_type"] == "no_play") & (dx["penalty"] == 1) & (dx["penalty_type"] == "Defensive Pass Interference") & dx["desc"].astype(str).map(e1.has_play)
        return mg(dx[m_].groupby("game_id").size().reindex(games, fill_value=0).astype(float))
    DPI = (dpi_pg(dR, GR["game_id"]), dpi_pg(dM, GM["game_id"]))
    print(f"  p (1): pass interference by the defense on a wiped down, a game: record {DPI[0][0]:.3f} ±{DPI[0][1]:.3f} | model {DPI[1][0]:.3f} ±{DPI[1][1]:.3f}"
          f" -> {wd(within(DPI[0], DPI[1])[2])} 2SE (v18: effectively never played, its draws given probability 0)")
    # ---- v19 j: coverage named exactly ----
    NOTP_ = Counter()
    for s in S: NOTP_.update(TABP[s][2])
    nGr_ = TB["game_id"].nunique()
    IN_DUR2 = lambda k_: str(k_).startswith(("during the play", "the play stands"))   # e1.prep's own count; v15's dur2 pool holds every pass and run's foul (drawn whole)
    print("  j (v19): coverage, three counts apart ('supported' means no tracked unsupported draw, never a complete game):")
    print(f"    1 event families outside every pool (the record's, a game; the engine never draws them): " + " | ".join(f"{k_} {v_} ({v_ / nGr_:.3f})" for k_, v_ in NOTP_.most_common() if not IN_DUR2(k_))
          + f" (e1.prep counts {sum(v_ for k_, v_ in NOTP_.items() if IN_DUR2(k_))} more outside its own pools, fouls during a pass or run: the dur2 pool draws those whole; part 2 listed them here: a reporting fault)")
    print(f"    2 unsupported continuations drawn (the engine, a game): " + " | ".join(f"{k_} {v_} ({v_ / max(nG, 1):.3f})" for k_, v_ in Counter(w_.split(': ')[0] if w_.startswith('a foul on the play') else w_ for v in UNSM.values() for _, w_ in v).most_common()))
    print(f"    3 unsupported participation (injury plays drawn; who is on the field after them is not played): {UNSUP_PART} ({UNSUP_PART / max(nG, 1):.3f} a game)")
    print("    the unsupported parts of reviews (e, printed above): the down, distance, possession and score after a reviewed play; its clock run; its restart; the")
    print("    lost challenge's timeout. Of injuries' clock effects (f): " + " | ".join(f"{k_} {v_}" for k_, v_ in sorted(CNTM.items()) if k_.startswith("f:") and ("not played" in k_ or "unsupported" in k_)))
    section("checks: p, f, e, h")

    print("\n=== section 0's tables (DOWNSTREAM), charged timeouts a game (2SE by game) | record | floor | model engine ===")
    gR, gF = GR["game_id"], GF["game_id"]
    def per_game(TMx, games, mask): return TMx[mask(TMx)].groupby("game_id").size().reindex(games, fill_value=0).astype(float)
    TMS = {"record": (TM_R, gR), "floor": (TM_F, gF), "model": (TM_M, GM["game_id"])}; E1C = {}
    def line(name, mask, key=None):
        v = {k: mg(per_game(T_, g_, mask)) for k, (T_, g_) in TMS.items()}
        parts = [f"record {v['record'][0]:.3f} ±{v['record'][1]:.3f}"]
        for k in ("floor", "model"):
            d_, s_, ok = within(v["record"], v[k]); parts.append(f"{k} {v[k][0]:.3f} ({d_:+.3f} ±{s_:.3f} {wd(ok)})")
            if key and k == "model": E1C[key] = ok
        print(f"  {name}: " + " | ".join(parts)); return v
    VALL = line("charged timeouts", lambda z: z["charged"], "all")
    for mo in ["after a snap, the same team snaps next", "after a snap that ended the possession or scored", "right after another timeout", "after a foul", "after a kickoff",
               "after a Try", "start of the quarter", "after the two-minute warning"]:
        line(f"  {mo}", lambda z, mo=mo: z["charged"] & (z["moment"] == mo), "moment: " + mo)
    for b in TB2: line(f"  {b}", lambda z, b=b: z["charged"] & (z["tb2"] == b), "bin: " + b)
    def gaps_def(TMx, seasons=None):
        z = TMx[TMx["charged"] & (TMx["caller"] == "defense") & (TMx["tb2"] == "last 2:00 of the game") & TMx["moment"].str.startswith("after a snap") & (TMx["score"] == "ahead 1-8")]
        return z if seasons is None else z[z["season"].isin(seasons)]
    gr_ = gaps_def(TM_R, STAMP).dropna(subset=["game_run"]); gm_ = gaps_def(TM_M).dropna(subset=["game_run"])
    m_r, m_m = boot(gr_, "game_run", 50), boot(gm_, "game_run", 50)
    print(f"  the defense's clock run before its timeout, last 2:00, offense ahead 1-8: record {m_r[0]:.1f} ±{m_r[1]:.1f} | model {m_m[0]:.1f} ±{m_m[1]:.1f}")
    def cell(ST_): return ST_[(ST_["cls"] == "STOP") & (ST_["q"] == 4) & (ST_["qa"] <= 120) & (ST_["score"] == "ahead 1-8")]
    cR, cM = cm(cell(STR[STR["season"].isin(STAMP)])), cm(cell(STM))
    print(f"  v5 b's cell: record 2023-25 {cR[0]:.2f} ±{cR[1]:.2f} | model {cM[0]:.2f} ±{cM[1]:.2f}")
    GAMES_R = list(GR[["game_id"]].merge(dR.groupby("game_id")[["home_team", "away_team"]].first().reset_index(), on="game_id").itertuples(index=False, name=None))
    LR_ = left_at_half(TM_R, GAMES_R)
    gm_games = lambda G_, d_: list(G_[["game_id"]].merge(d_.groupby("game_id")[["home_team", "away_team"]].first().reset_index(), on="game_id").itertuples(index=False, name=None))
    LM = left_at_half(TM_M, gm_games(GM, dM)); gok = Counter()
    for h_ in (1, 2):
        for k in (3, 2, 1, 0, -1):
            gok[within(LR_[(h_, k)], LM[(h_, k)])[2]] += 1
    print(f"  timeouts left at each half's end within 2SE: model {gok[True]} of {gok[True] + gok[False]} measured | NOT MEASURED {gok[None]}")
    K = [keyed(x, SPLIT) for x in (STR[STR["season"].isin(STAMP)], STF, STM)]; KK = [kstr(x, LEV[0]) for x in K]; met = Counter(); metrun = Counter()
    for k_ in sorted(set(KK[0]) | set(KK[2])):
        st_, f_, m_ = [cm(K[i][KK[i] == k_]) for i in range(3)]; d1, d2_ = within(st_, f_), within(st_, m_)
        met[("floor", d1[2])] += 1; met[("model", d2_[2])] += 1
        if k_.startswith("RUN"): metrun[("model", d2_[2])] += 1
    print(f"  job (3)'s length cells met: floor {met[('floor', True)]} | model {met[('model', True)]} of {met[('model', True)] + met[('model', False)]} measured (NOT MEASURED: floor {met[('floor', None)]}, model {met[('model', None)]})"
          f" | RUN cells (the snap side) model {metrun[('model', True)]}")
    def sel(G_, s): return G_ if s is None else G_[G_["season"] == s]
    def pg(PO_, G_, s): return PO_[PO_["half"] <= 2].groupby("game_id").size().reindex(sel(G_, s)["game_id"], fill_value=0).astype(float)
    SIDES = (("record", GR, POR, STR), ("floor", GF, POF, STF), ("model", GM, POM, STM)); TRI = {}
    def tri(name, f, slot=None):
        m = [mg(f(G_, PO_, ST_, None)) for _, G_, PO_, ST_ in SIDES]; parts = [f"record {m[0][0]:.3f} ±{m[0][1]:.3f}"]
        for k, lab in ((1, "floor"), (2, "model")):
            dd, s2, ok_ = within(m[0], m[k]); parts.append(f"{lab} {m[k][0]:.3f} ({dd:+.3f} ±{s2:.3f} {wd(ok_)})")
        print(f"  {name}: " + " | ".join(parts))
        if slot: TRI[slot] = m
    tri("possessions a game", lambda G_, PO_, ST_, s: pg(PO_, G_, s), "possessions")
    tri("plays (snaps) a game, regulation", lambda G_, PO_, ST_, s: sel(G_, s)["snaps_reg"].astype(float), "plays")
    tri("points a game (overtime in)", lambda G_, PO_, ST_, s: sel(G_, s)["points"].astype(float), "points")
    print(f"  every game-level result above is printed with this omitted mechanism (f): 'unsupported: participation', {UNSUP_PART} injury plays ({UNSUP_PART / max(nG, 1):.3f} a game);"
          f" no use above the game level (L4-L6) rests on these games")
    section("game figures: record | floor | model")

    print("\n=== E1 SECTION 4 on the model engine (per season, from the shared parse; the stopped clock by the check; every failure counts, none exempted) ===")
    w4 = Counter(); C1 = dict(possessions=0, games=0); bad4 = []; left1 = []; CK = Counter(); FL = []; COST4 = Counter(); PO = Counter(); SR = {}
    for e_ in EV:
        x_ = e_["sec4"]; w4.update(x_["w4"]); bad4.append(x_["bad4"]); left1.append(x_["left1"]); CK.update(x_["CK"]); FL += x_["FL"]; COST4.update(x_["COST"]); PO.update(x_["PO"]); SR.update(x_["SR"])
        C1["possessions"] += x_["C1"]["possessions"]; C1["games"] += x_["C1"]["games"]
    bad4 = pd.concat(bad4, ignore_index=True) if bad4 else pd.DataFrame(); left1 = pd.concat(left1, ignore_index=True) if left1 else pd.DataFrame()
    print(f"  r4 words {dict(w4)} | r1 possessions {C1['possessions']} games {C1['games']} unexplained {len(left1)}")
    for _, r in bad4.head(10).iterrows(): print(f"    {r['word']} {r['check']} {r['game_id']} seq {r['seq']} | {r['why']}")
    UNK = [f_ for f_ in FL if f_[0] == "UNKNOWN"]; UNK_V5 = [u for u in UNK if (not u[10]) and u[9] >= 6]; UNK_OTHER = [u for u in UNK if u not in UNK_V5]
    REC_FAILKEY = {(f_[1], int(f_[2]), f_[0]) for f_ in REC4["fl_n"]}
    OWN = [f_ for f_ in FL if f_[0] != "UNKNOWN"]   # every failure of the engine's games; a copied record row's own failure does not license one
    PROV = {}
    for f_ in OWN:
        src_ = SRCM.get((f_[1], int(f_[2])))
        PROV[id(f_)] = (src_, bool(src_) and (src_.split("|")[0], int(src_.split("|")[1]), f_[0]) in REC_FAILKEY)
    print(f"  the stopped clock, the corrected check: STOP checked {CK['STOP checked']} failed {CK['STOP failed']} | no stopping event {CK['STOP with no stopping event found (failed)']}"
          f" | UNCHECKED {CK['STOP unchecked (a play unstamped)']} | PARTIAL checked {CK['PARTIAL checked']} failed {CK['PARTIAL failed']} UNCHECKED {CK['PARTIAL unchecked (a stamp missing)']}"
          f" | what each part of the allowance passes {dict(COST4)} | unclassed: v5 a's case {len(UNK_V5)}, other {len(UNK_OTHER)}")
    print(f"  d (v18): the unclassed stretches outside v5 a's case, by r2's reason (UNKNOWN stretches; v17: 6,645): {dict(Counter(u[6] for u in UNK_OTHER).most_common(8))}")
    for u in UNK_OTHER[:4]:
        s_ = int(str(u[1])[:4]); fr_ = FRM[s_][FRM[s_]["game_id"] == u[1]]; sq_ = fr_["order_sequence"].astype(int)
        print(f"    unclassed {u[1]} {u[2]}->{u[3]} q{u[9]}: {u[6]}")
        for _, r_ in fr_[(sq_ >= int(u[2])) & (sq_ <= int(u[3]))].iterrows(): print(f"      {r_['order_sequence']} | {r_['play_type']} | ob {r_.get('out_of_bounds')} | {str(r_['desc'])[:110]}")
    print(f"  the engine's failures: {len(OWN)} (all counted) | by kind and reason {dict(Counter((f_[0], f_[6]) for f_ in OWN).most_common(10))}"
          f" | of them on a drawn row whose own record stretch also fails the check (provenance, printed, still failures): {sum(1 for f_ in OWN if PROV[id(f_)][1])}")
    for f_ in OWN[:12]:
        s_ = int(str(f_[1])[:4]); fr_ = FRM[s_][FRM[s_]["game_id"] == f_[1]]; sq_ = fr_["order_sequence"].astype(int)
        rows_ = fr_[(sq_ >= int(f_[2])) & (sq_ <= int(f_[3]))]
        print(f"    {f_[0]} {f_[1]} {f_[2]}->{f_[3]}: clock fell {f_[4]} | allowed {f_[5]} | excess {f_[7]} | {f_[6]}{(' | stopped by ' + str(f_[11]) + ' at ' + str(f_[12])) if len(f_) > 12 else ''}"
              f" | drawn from the record row {PROV[id(f_)][0] or 'none'}{' (which fails the check on the record too)' if PROV[id(f_)][1] else ''}")
        for _, r_ in rows_.iterrows(): print(f"      {r_['order_sequence']} | q{r_['qtr']} {r_['quarter_seconds_remaining']} | {r_['time_of_day'][11:19] if isinstance(r_['time_of_day'], str) else ''}-{r_['end_clock_time'][11:19] if isinstance(r_['end_clock_time'], str) else ''} | {str(r_['desc'])[:120]}")
    srbad = []
    for s in S_SUP:
        x = X6[s]; m = SR[s]
        if m["M1"] != x["touchback"]["value"]: srbad.append((s, "M1"))
        if not isinstance(m["M2"], str) and m["M2"] != x["ot_reg_len"]["value"]: srbad.append((s, "M2"))
        if x["ot_reg_rule"]["value"] == rules.BOTH_POSSESS and m["M3"] not in (0, "no games"): srbad.append((s, "M3"))
        if x["ot_post_rule"]["value"] == rules.BOTH_POSSESS and m["M4"] not in (0, "no games"): srbad.append((s, "M4"))
    pt = sum(int((lambda g_: (g_["home_score"] == g_["away_score"]).sum())(FRM[s][FRM[s]["season_type"] == "POST"].groupby("game_id")[["home_score", "away_score"]].first())) for s in S)
    done = {"playoff games tied 0": pt == 0, "no game declared": len(DECM) == 0, "r4 OTHER 0": w4["OTHER"] == 0, "r4 UNCHECKED 0": w4["UNCHECKED"] == 0, "r1 unexplained 0": len(left1) == 0,
            "no unclassed stretch outside v5 a's case": len(UNK_OTHER) == 0,
            "stopped clock 0 failed (every failure, none exempted)": len(OWN) == 0, "stopped clock 0 with no stopping event": CK["STOP with no stopping event found (failed)"] == 0,
            "stopped clock 0 UNCHECKED (the engine stamps every play)": CK["STOP unchecked (a play unstamped)"] + CK["PARTIAL unchecked (a stamp missing)"] == 0,
            "periods 0 failed": PO["games failing the period check"] == 0, "season rules agree": not srbad,
            "one game per played game": nG_ALL == len(sched[sched["season"].isin(S)]) - (sum(SKM.values()) if FIXTURE else 0)}
    DONE_NUM = {"playoff games tied 0": pt, "no game declared": len(DECM), "r4 OTHER 0": w4["OTHER"], "r4 UNCHECKED 0": w4["UNCHECKED"], "r1 unexplained 0": len(left1),
                "no unclassed stretch outside v5 a's case": len(UNK_OTHER), "stopped clock 0 failed (every failure, none exempted)": len(OWN),
                "stopped clock 0 with no stopping event": CK["STOP with no stopping event found (failed)"],
                "stopped clock 0 UNCHECKED (the engine stamps every play)": CK["STOP unchecked (a play unstamped)"] + CK["PARTIAL unchecked (a stamp missing)"],
                "periods 0 failed": PO["games failing the period check"], "season rules agree": srbad,
                "one game per played game": f"{nG_ALL} played of {len(sched[sched['season'].isin(S)])}"}   # each item's own number (r: the summary names it)
    print(f"  DONE WHEN (section 4): {done}"); SEC4 = all(done.values())
    print("  l (v19): the two construction failures as fixtures, traced state by state (the engine's rows; the play is v18's, the same seeds):")
    for g_, lo_, hi_ in (("2019_14_PIT_ARI", 136, 143), ("2024_12_TB_NYG", 75, 82)):
        s_ = int(g_[:4]); fr_ = FRM[s_][FRM[s_]["game_id"] == g_]
        if not len(fr_): print(f"    {g_}: not in this run"); continue
        sq_ = fr_["order_sequence"].astype(int)
        for _, r_ in fr_[(sq_ >= lo_) & (sq_ <= hi_)].iterrows():
            print(f"    {g_} {r_['order_sequence']} | q{r_['qtr']} {r_['quarter_seconds_remaining']} | {r_['posteam']} {r_['down']}&{r_['ydstogo']} at {r_['yardline_100']} | {r_['play_type']}"
                  f" | foul {r_.get('penalty_team')} {r_.get('penalty_type')} award {r_.get('first_down_penalty')} | {str(r_['desc'])[:110]}")
    fx_ = [f_ for f_ in OWN if f_[1] == "2019_14_PIT_ARI"]
    print(f"    2019_14_PIT_ARI 139->142 with clock_check.py {sh('clock_check.py')} (4-3-2e(3)'s stop at the offense's own foul): {'still a failure: ' + str(fx_) if fx_ else 'no failure'}")
    print("  ad addition 2 item 2 (7-3-1): the written distance by down, the record beside the engine, one reader (snaps; the distance equal to the written yard line;")
    print("  the distance above it; goal_to_go flagged and, of those, the distance equal to the yard line, where the frame carries the column):")
    for s in S:
        e_ = gtg_read(FRM[s]); r_ = REC_GTG.get(s)
        if r_ is None: print(f"    {s}: the record not read in this run"); continue
        for d_ in (1, 2, 3, 4):
            a_, b_ = r_[d_], e_[d_]
            print(f"    {s} down {d_}: record {a_['snaps']} snaps | distance = yard line {a_['eq']} | above {a_['above']} | goal_to_go {a_['flag']} (distance = yard line {a_['flag_eq']})"
                  f" || engine {b_['snaps']} snaps | distance = yard line {b_['eq']} | above {b_['above']} | goal_to_go {b_['flag']} (distance = yard line {b_['flag_eq']})")
        print(f"    {s} first downs whose distance is not the smaller of 10 and the written yard line: record below {r_['first_below']}, above {r_['first_above']} | engine below {e_['first_below']}, above {e_['first_above']} | the record's goal_to_go column: {GTG_WHY.get(s)}")
    def mark_grid(m_):
        """Every first down from an exact spot on a 1/8-yard grid 1.0 to 20.0, the line to gain at max(0, spot - 10) (7-3-1), through Game.mark: the spots written off the rule."""
        bad_ = []
        for k_ in range(8, 161):
            y_ = k_ / 8; r_ = dict(yardline_100=y_, ydstogo=min(10.0, y_), yards_gained=0.0); m_.Game.mark(None, r_)
            if float(r_["ydstogo"]) != min(10.0, float(r_["yardline_100"])): bad_.append(y_)
        return bad_
    _m3 = load_mod(E1_AD3PLANT, "e1_v35_ad3plant")
    for k_, v_ in ENGINE_CONF.items(): setattr(_m3, k_, v_)
    GRID_C, GRID_P = mark_grid(e1n), mark_grid(_m3)
    print(f"  the grid (153 first-down spots): off the rule, the candidate {len(GRID_C)} {GRID_C[:8]} | the plant (v34's marking on the line to gain) {len(GRID_P)} {GRID_P[:8]} (expected 0 and 7, every plant spot between the 10 and the 11)")
    # af addition item 3: the replay of v34's three games retired as VACUOUS (under af1 the games no longer reach those snaps)
    print(f"  ad addition 2's replay of v34's three games: retired as VACUOUS (af addition item 3) | the grid stays: off the rule, the candidate {len(GRID_C)}, the plant {len(GRID_P)} (expected 0 and 7)")
    section("E1 section 4")
    print("\n=== E1 SECTION 5: plants P1-P4 on changed copies of the model engine, 2024's games (each must FAIL; P3 judged by the check); the race's fits reused ===")
    def _trans_plant(o, n_):   # P1, P2: the shared transition changed in the engine's copy only (its module's _TRANS)
        if SRC_AFTER.count(o) != 1: stop(f"a plant's anchor is in the transition {SRC_AFTER.count(o)} times")
        return E1N + f"\nimport transition as _T0\n_ns_ = dict(vars(_T0)); exec({SRC_AFTER.replace(o, n_)!r}, _ns_); _TRANS = lambda st, ev, rb: _ns_['second'](_ns_['after_one'](st, ev, rb), ev)   # PLANT\n"
    PLANT = {"P1": _trans_plant('recv = next_possession("try_or_field_goal", scorer=off, scored_on=dfn)[0]   # after a field goal',
                                'recv = next_possession("try_or_field_goal", scorer=off, scored_on=off)[0]   # after a field goal'),
             "P2": _trans_plant("    if nd > 4:   # 3-8-2: four downs\n        return series(dfn, 100 - end", "    if nd > 5:   # 3-8-2: four downs\n        return series(dfn, 100 - end")}
    for name, (o, n_) in {"P3": ('("incomplete 4-4f", inc == 1)', '("incomplete 4-4f", False)'),
                          "P4": ('        self.rb = _TBR(season, X)\n', '        self.rb = dict(_TBR(season, X), kick=25) if season == 2024 else _TBR(season, X)\n')}.items():
        if E1N.count(o) != 1: stop(f"plant {name} anchor found {E1N.count(o)} times")
        PLANT[name] = E1N.replace(o, n_)
    s4 = 2024; res = {}
    for name, ok, v, what in POOL.map(L.w_plant, [(name, txt_, s4, sched[sched["season"] == s4], TAB_PATH, MODELS_B[s4], X6, list(S)) for name, txt_ in PLANT.items()], "the plants"):
        res[name] = ok; print(f"  {name}: {what} {v} -> {plant_verdict(0 if ok is None else 1, bool(ok))}")
    PLANTS_OK = all(v_ is True for v_ in res.values())
    print(f"  plants failed as they must {sum(1 for v_ in res.values() if v_ is True)} of 4 | VACUOUS {sum(1 for v_ in res.values() if v_ is None)}{' (a quick run does not judge them)' if FIXTURE else ''}")
    section("E1 plants P1-P4")
except (SystemExit, Overtime):
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; the table and the working tables are saved; nothing else written")


try:
    import contextlib
    print("\n=== y0 (a): the one rule for every 2SE check (within, wd, hv; head of this chain), and its plant ===")
    _pb = io.StringIO()
    with contextlib.redirect_stdout(_pb):
        _pa = within((np.nan, np.nan, 1), (1.0, 0.1, 50)); _pb2 = within((5.0, np.nan, 40), (5.1, 0.2, 40)); _pc = within((5.0, 0.2, 40), (5.1, 0.2, 40))
        print(f"plant line: {wd(_pa[2])} | {wd(_pb2[2])} | {hv(_pa[2])} | the control {wd(_pc[2])}")
    Y0A_PLANT = (_pa[2] is None and _pb2[2] is None and _pc[2] is True and "plant line: NOT MEASURED | NOT MEASURED | NOT MEASURED | the control within" in _pb.getvalue())
    print(f"  the plant: a side with one row and a NaN 2SE, and a side with a NaN 2SE, fed to the check and to a prediction: '{_pb.getvalue().strip()}'"
          f" -> {'NOT MEASURED as it must (the control, two measured sides, prints within)' if Y0A_PLANT else 'FAILED: a NaN printed a verdict'}")

    print("\n=== y2, y1: the possessions (both measures), the seconds snap to snap by what the clock did between the snaps, and the running seconds after each foul,")
    print("    read from the engine's games and the record by the record's own readers (record.events, r1.possessions, rules.clock_class: the same functions on")
    print("    both sides; w's read with the clock_class reason kept) ===")
    # W_COLS, W_NUM and w_side are defined before aa1's fit (the record's frame XREC is read there and reused here)
    def w_tables(x):
        """The side's tables: possessions by r1.possessions with the seconds each uses (count_side's: its first snap to the next one's, or the half's end), the
        drives by fixed_drive (u's), the stretches snap to snap with rules.clock_class (its class and its reason), the charged timeouts; every game listed."""
        P = r1.possessions(x[["game_id", "order_sequence", "posteam", "qtr", "play_type", "two_point_attempt", "interception", "fumble_recovery_1_team"]])
        idx = {(g, s_): i for i, (g, s_) in enumerate(zip(x["game_id"], x["order_sequence"]))}
        gsr, q, qs = x["gsr"].to_numpy(float), x["qtr"].to_numpy(float), x["quarter_seconds_remaining"].to_numpy(float); po = []
        for g, pp in P.groupby("game_id", sort=False):
            pl = list(pp.itertuples(index=False))
            for j, p_ in enumerate(pl):
                a = idx[(g, p_.s0)]; half = 1 if q[a] <= 2 else (2 if q[a] <= 4 else 3)
                if half > 2: continue
                b = idx[(g, pl[j + 1].s0)] if j + 1 < len(pl) else None; nh = None if b is None else (1 if q[b] <= 2 else (2 if q[b] <= 4 else 3))
                po.append((g, int(q[a]), bool(q[a] in (2, 4) and qs[a] <= 120), gsr[a] - (gsr[b] if nh == half else (1800 if half == 1 else 0))))
        dr = x[x["reg"] & x["posteam"].notna() & x["fixed_drive"].notna() & ~x["kind"].isin(["try", "kickoff", "timeout"])].groupby("game_id")["fixed_drive"].nunique()
        sn = np.where(x["snap"] & x["reg"])[0]; g_ = x["game_id"].to_numpy(object); pos = x["posteam"].to_numpy(object); reg = (x["season_type"] == "REG").to_numpy(); st = []
        cs = lambda m: np.cumsum(np.asarray(m, bool).astype(int))   # counts up to each row: the rows between two snaps by difference
        c_to, c_pen, c_try = cs(x["timeout"] == 1), cs(x["penalty"] == 1), cs(x["kind"] == "try"); c_tmw = cs(x["desc"].astype(str).str.startswith("Two-Minute"))
        inc_, ob_, pen_, td_, sf_, fg_ = (x["incomplete_pass"] == 1).to_numpy(), (x["out_of_bounds"] == 1).to_numpy(), (x["penalty"] == 1).to_numpy(), (x["touchdown"] == 1).to_numpy(), \
            (x["safety"] == 1).to_numpy(), (x["field_goal_result"] == "made").to_numpy()
        it_, fl_, pu_ = (x["interception"] == 1).to_numpy(), (x["fumble_lost"] == 1).to_numpy(), (x["play_type"] == "punt").to_numpy()
        for a, b in zip(sn[:-1], sn[1:]):
            if g_[a] != g_[b] or q[a] != q[b]: continue
            btw = lambda c: c[b - 1] - c[a] > 0
            ow = rules.oob_window(int(q[a]), qs[a], bool(reg[a])); fw = rules.foul_window(int(q[a]), qs[a], bool(reg[a])); ob = bool(ob_[a]); pen = bool(pen_[a]) or btw(c_pen)
            ev = [("incomplete 4-4f", bool(inc_[a])), ("out of bounds late 4-3-2a", ob and ow is True), ("out of bounds early 4-3-2a", ob and ow is False),
                  ("out of bounds, window unread", ob and ow is None), ("score/touchback/try 4-4d", bool(td_[a] or sf_[a] or fg_[a]) or btw(c_try)),
                  ("change of possession 4-4i", pos[a] != pos[b] or bool(it_[a] or fl_[a] or pu_[a])), ("charged timeout 4-5-1", btw(c_to)), ("two-minute warning 3-41", btw(c_tmw)),
                  ("foul in window 4-3-2e", pen and fw is True), ("foul outside windows 4-3-2e", pen and fw is False), ("foul, window unread", pen and fw is None)]
            cls_, why_ = rules.clock_class(ev, False)
            st.append((g_[a], int(q[a]), cls_, why_, qs[a] - qs[b]))
        m = x["desc"].astype(str).str.extract(r"Timeout #(\d+) by ([A-Z]{2,3})")[1]; ch = ((x["timeout"] == 1) & m.notna() & x["reg"]).to_numpy()
        to = pd.DataFrame({"game_id": x.loc[ch, "game_id"].to_numpy(object), "half": np.where(x.loc[ch, "qtr"].to_numpy(float) <= 2, 1, 2)})
        return dict(games=sorted(x["game_id"].unique()), po=pd.DataFrame(po, columns=["game_id", "q", "late", "sec"]), dr=dr,
                    st=pd.DataFrame(st, columns=["game_id", "q", "cls", "why", "sec"]), to=to)
    def y1_split(x):
        """y1, read back from written games: after every regulation foul row (a no-play with a foul), the game seconds the clock ran to the next row in the quarter
        (the foul row's clock less the next row's, less a wiped play's own stamped seconds: the running part) and the real seconds less them (the stopped part),
        each against the season's book's play clock after an enforcement (ENF_CLOCK). A row whose stamps do not parse is UNREAD, never filled."""
        g_ = x["game_id"].to_numpy(object); q = x["qtr"].to_numpy(float); qs = x["quarter_seconds_remaining"].to_numpy(float); ds = x["desc"].astype(str).to_numpy(object)
        W_ = pd.to_datetime(x["time_of_day"], errors="coerce", utc=True); E_ = pd.to_datetime(x["end_clock_time"], errors="coerce", utc=True)
        Wn = (W_ - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds().to_numpy(float); En = (E_ - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds().to_numpy(float)
        pt_ = x["play_type"].to_numpy(object); to_ = (x["timeout"] == 1).to_numpy(); pen = ((x["penalty"] == 1) & (x["play_type"] == "no_play") & x["reg"]).to_numpy(); out = []
        for i in np.where(pen)[0]:
            j = i + 1
            if j >= len(x) or g_[j] != g_[i] or q[j] != q[i]: out.append((g_[i], int(g_[i][:4]), "?", "the quarter's last row", np.nan, np.nan)); continue
            wiped = e1.has_play(ds[i]); L_ = (En[i] - Wn[i]) if wiped else 0.0
            run_ = qs[i] - qs[j] - L_; real_ = Wn[j] - (En[i] if wiped else Wn[i])
            nk_ = "a timeout" if to_[j] else ("a snap" if pt_[j] in rules.SNAP_KINDS else ("a foul" if pt_[j] == "no_play" and x["penalty"].iat[j] == 1 else "another row"))
            out.append((g_[i], int(g_[i][:4]), "wiped" if wiped else "presnap", nk_, run_, real_ - run_))
        z = pd.DataFrame(out, columns=["game_id", "season", "kind", "next", "run", "stopped"])
        z["enf"] = [ENF_CLOCK.get(s_, (None,))[0] for s_ in z["season"]]
        z["over"] = [(r_ > e_) if (e_ is not None and not np.isnan(r_)) else None for r_, e_ in zip(z["run"], z["enf"])]
        return z
    def y1_print(nm, z):
        rd_ = z[z["over"].notna()]; rs_ = rd_[rd_["run"] > 0]
        n_over = int(sum(1 for v_ in rd_["over"] if bool(v_)))
        print(f"  {nm}: foul rows {len(z)} | read {len(rd_)} | UNREAD {len(z) - len(rd_)} ({dict(Counter(z.loc[z['over'].isna(), 'next']))}) | the clock ran after the foul {len(rs_)}"
              f" | running seconds over the book's play clock {n_over} (max {rd_['run'].max() if len(rd_) else float('nan'):.0f}) | by kind and next row: {dict(Counter(zip(rs_['kind'], rs_['next'])))}")
        for k_ in ("wiped", "presnap"):
            zz = rs_[rs_["kind"] == k_]
            if len(zz): print(f"    {k_}, the clock ran after it ({len(zz)}): stopped {zz['stopped'].mean():.2f} s (real) then running {zz['run'].mean():.2f} s (game) to the next row"
                              f" | running over 25: {int((zz['run'] > 25).sum())}, 21-25: {int(((zz['run'] > 20) & (zz['run'] <= 25)).sum())}")
        return n_over, len(rd_), len(rs_)
    W_KEY = shs(KEY_REC + "|y read|" + shs(inspect.getsource(w_side) + inspect.getsource(w_tables)) + "|" + sh("r1.py") + sh("rules.py") + "|" + repr(W_COLS) + "|" + LIBSHA)
    t_w = time.time()
    WT = {"record": cache_get("y_record_read", W_KEY, lambda: w_tables(XREC))}   # XREC: the record's rows, read before aa1's fit
    XE = w_side(FRM); WT["engine"] = w_tables(XE)
    XAF = w_side({AB_S: OUT_AF[0]})   # af1's plant's games (2024)
    XPL = w_side({AB_S: OUT_PL[0]}); XTD = w_side({AB_S: OUT_TD[0]})   # ac1's plant's games and the landed engine's games (2024), read the same way
    print(f"  read in {time.time() - t_w:.0f} s | games: record {len(WT['record']['games'])}, engine {len(WT['engine']['games'])}")
    def w_mean(v, g):
        v = np.asarray(v, float); g = np.asarray(g, object); ok = ~np.isnan(v); v, g = v[ok], g[ok]
        if len(v) < 2: return (np.nan, np.nan, len(v))
        m_ = v.mean(); r_ = pd.Series((v - m_) / len(v)).groupby(g).sum().to_numpy(); G_ = len(r_)
        return (m_, 2 * np.sqrt((r_ ** 2).sum() * G_ / (G_ - 1)) if G_ > 1 else np.nan, len(v))
    def w_pg(nm, ser, games=None):
        gl_ = WT[nm]["games"] if games is None else games
        v = ser.reindex(gl_, fill_value=0).to_numpy(float); return (v.mean() if len(v) else np.nan, 2 * v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan, len(v))
    VERD = {}   # ab: every w_line verdict by label (the list of y's within figures moved outside reads it)
    def w_line(label, a, b, unit=""):
        d, s2, ok = within(a, b); VERD[label] = ok
        if ok is None:
            print(f"  {label}: record {a[0]:.3f} ±{a[1]:.3f} (n {a[2]}) | engine {b[0]:.3f} ±{b[1]:.3f} (n {b[2]}) -> NOT MEASURED (fewer than 2 on a side, or not a number)"); return d, s2, None
        print(f"  {label}: record {a[0]:.3f} ±{a[1]:.3f} (n {a[2]}) | engine {b[0]:.3f} ±{b[1]:.3f} (n {b[2]}) | {d:+.3f} ±{s2:.3f}{unit} -> {wd(ok)}")
        return d, s2, ok
    print("  y2: possessions a game, two measures of one count, both printed; the gap (record less engine):")
    PFD = w_line("by fixed_drive (u's)", w_pg("record", WT["record"]["dr"]), w_pg("engine", WT["engine"]["dr"]))
    PR1 = w_line("by r1.possessions (v's; count_side's)", w_pg("record", WT["record"]["po"].groupby("game_id").size()), w_pg("engine", WT["engine"]["po"].groupby("game_id").size()))
    print(f"    the gap: fixed_drive {-PFD[0]:.3f} | r1.possessions {-PR1[0]:.3f} (w: 0.681 to 1.239, the two measures' range)")
    print("  y2: game seconds a possession uses (r1.possessions; its first snap to the next possession's first snap, or the half's end), 2SE by game:")
    W_SEC = {}
    for nm_, f_ in (("every possession", lambda z: z["q"] > 0), ("starting in quarter 2", lambda z: z["q"] == 2), ("starting in quarter 4", lambda z: z["q"] == 4),
                    ("starting in the last two minutes of a half", lambda z: z["late"])):
        W_SEC[nm_] = w_line(nm_, *(w_mean(WT[k]["po"].loc[f_(WT[k]["po"]), "sec"], WT[k]["po"].loc[f_(WT[k]["po"]), "game_id"]) for k in ("record", "engine")), " s")
    print("  y2: game seconds snap to snap by what the clock did between the snaps (rules.clock_class over Rule 4's events as rules.py names them, their articles in the names):")
    W_CLS = {}
    for c_ in ("RUN", "STOP", "PARTIAL"):
        W_CLS[c_] = w_line(f"{c_}", *(w_mean(WT[k]["st"].loc[WT[k]["st"]["cls"] == c_, "sec"], WT[k]["st"].loc[WT[k]["st"]["cls"] == c_, "game_id"]) for k in ("record", "engine")), " s")
    Y_F = "foul outside windows 4-3-2e"; Y_OF = "out of bounds early 4-3-2a+foul outside windows 4-3-2e"
    print("  y2: the PARTIAL stretches by their reason (rules.clock_class's), snap to snap and how many a game:")
    W_WHY = {}
    for c_, x_ in ((Y_F, "record 48.393; x 71.262"), (Y_OF, "record 41.620; x 67.130"), ("out of bounds early 4-3-2a", "record 33.548; x 32.774")):
        mk_ = {k: (WT[k]["st"]["cls"] == "PARTIAL") & (WT[k]["st"]["why"] == c_) for k in WT}
        W_WHY[c_] = w_line(f"{c_} ({x_})", *(w_mean(WT[k]["st"].loc[mk_[k], "sec"], WT[k]["st"].loc[mk_[k], "game_id"]) for k in ("record", "engine")), " s")
        w_line("    stretches a game", *(w_pg(k, WT[k]["st"][mk_[k]].groupby("game_id").size()) for k in ("record", "engine")))
    print("  charged timeouts by half (printed, not predicted):")
    for h_ in (1, 2): w_line(f"half {h_}", *(w_pg(k, WT[k]["to"][WT[k]["to"]["half"] == h_].groupby("game_id").size()) for k in ("record", "engine")))

    print("\n  y1, the engine's games read back: the running seconds after each foul against the season's book's play clock after an enforcement (ENF_CLOCK), and the")
    print("  engine's own split, the clock stopped then running (x: stopped 30.8 s, then 41.7 game seconds, which a 25-second clock cannot hold):")
    Y1S = y1_split(XE); Y1N = y1_print("the engine (every season)", Y1S)
    print(f"  the engine's own count of restarts drawn: {dict((k_, v_) for k_, v_ in CNTM.items() if k_.startswith('y1:'))}")

    print("\n  y1, the case (a foul outside the windows, 1st quarter at 10:00, on a play that kept the clock running) on the candidate and on the plant (the game clock")
    print("  started at the play's end, through the enforcement); the restart drawn from a one-row pool (stopped 12 s, running 9 s), so the case reads the rule, not a draw:")
    e1yp = load_mod(E1_Y1P, "e1_v29_y1plant")
    for k_, v_ in ENGINE_CONF.items(): setattr(e1yp, k_, v_)
    def y1_case(m_, kind_):
        s_ = S[0]; g_ = sched[sched["season"] == s_].iloc[0]
        G = m_.Game(g_, R[s_], X6, np.random.default_rng(0), s_)
        G.P = dict(G.P); G.P["gfoul"] = m_.Pool("y1 case", pd.DataFrame([(kind_, m_.time_bin(1, 600), 12, 9)], columns=["kind", "tb", "stopped", "run"]), ["stopped", "run"],
                                             [("kind", "tb"), ("kind",)], last_any=True)
        G.q = 1; G.clock = 600; G.running = True; G.stretch_stop = False; G.qa = 600; G.off = G.home; G.t = 1000; G.restart_at = None; G.foul_gap = None
        G.foul_clock(False, ran=(kind_ == "wiped"))
        st0 = (G.running, None if G.restart_at is None else G.restart_at - 1000, G.foul_gap)
        G.advance(12); c_whistle = G.clock
        G.advance(G.foul_gap - 12 if G.foul_gap is not None else 9); c_snap = G.clock
        run_ = 600 - c_snap; enf_ = ENF_CLOCK.get(s_, (None,))[0]
        ok_ = st0[0] is False and st0[1] == 12 and c_whistle == 600 and run_ == 9 and enf_ is not None and run_ <= enf_
        return ok_, f"running after the foul {st0[0]}, restart {st0[1]} s after it, the clock at the whistle {c_whistle} (must be 600), at the snap {c_snap} (600 less 9 = 591), running {run_} s (play clock {enf_})"
    Y1_CASE = {}
    for nm_, m_ in (("candidate", e1n), ("plant", e1yp)):
        for kind_ in ("wiped", "presnap"):
            ok_, txt_ = y1_case(m_, kind_); Y1_CASE[(nm_, kind_)] = ok_
            print(f"    {nm_}, {kind_}: {txt_} -> {'PASS' if ok_ else 'FAIL'}{' (the plant must FAIL)' if nm_ == 'plant' else ''}")
    Y1_CASE_OK = Y1_CASE[("candidate", "wiped")] and Y1_CASE[("candidate", "presnap")]
    Y1_PLANT_CASE = (not Y1_CASE[("plant", "wiped")]) and (not Y1_CASE[("plant", "presnap")])

    print("  y1's plant's games: printed by y's landing run (e2b_v25_18a581d0674d: the plant exceeded the play clock and missed y2's check); not replayed here (ab's budget)")
    section("y2, y1: possessions, seconds, the clock read; the case and the plant")
except (SystemExit, Overtime):
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; the table and the working tables are saved; nothing else written")


try:
    print("\n=== ac2 (ab2's and ab3's reads as written, engine beside record): the record and the engine's games read by the record's readers (w_side: record.events for each row's kind, the columns named, both sides the same way),")
    print("    engine beside record, 2SE by game (y0 a's rule for every verdict); aa3's lines as v26 printed them, with touchdowns, field goal tries, the red-zone fourth downs and the points ===")
    def aa_prep(x):
        x = x.copy(); pt_ = x["play_type"].to_numpy(object)
        x["choice"] = np.where(pt_ == "punt", "punt", np.where(pt_ == "field_goal", "field_goal", "go"))
        return x
    AA = {"record": aa_prep(XREC), "engine": aa_prep(XE)}; AAP = aa_prep(XPL); AAT = aa_prep(XTD)   # AAP: ac1's plant (2024); AAT: the landed engine (ac0's read, 2024)
    GAMES_AA = {nm: sorted(AA[nm]["game_id"].unique()) for nm in AA}
    print(f"  rows: record {len(AA['record'])} in {len(GAMES_AA['record'])} games | engine {len(AA['engine'])} in {len(GAMES_AA['engine'])} games | ac1's plant ({AB_S}) {len(AAP)} in {AAP['game_id'].nunique()} games | the landed engine ({AB_S}) {len(AAT)} in {AAT['game_id'].nunique()} games")
    def pg_aa(vals, g, games):
        s_ = pd.Series(np.asarray(vals, float)).groupby(np.asarray(g, object)).sum().reindex(games, fill_value=0.0).to_numpy(float)
        return (s_.mean(), 2 * s_.std(ddof=1) / np.sqrt(len(s_)), len(s_)) if len(s_) >= 2 else (np.nan, np.nan, len(s_))

    print("  ac0: the in-game snap draws inside the 20 by the pool level they resolved at and by 5-yard cell (the landed engine and the candidate, every season and 2024 beside);")
    print("  a level whose key holds no yards-to-goal cell (yl20 or yl5) is 'keyless'; the share keyless is the check (below 0.02 lands ac1; the landed engine's below 0.02 closes ac as a read):")
    def level_shares(cnt_, levels_):
        keyed_ = [i for i, lv_ in enumerate(levels_) if "yl20" in lv_ or "yl5" in lv_ or "yl5in" in lv_ or "yl20in" in lv_]
        tot_ = 0; keyless_ = 0; by_cell = {}
        for cell_ in ("inside the 1", "opp 20-1", "1-5", "6-10", "11-15", "16-20"):   # v34 ad0 (a): every draw inside the 20 (the landed engine names a draw inside the 1 by its field cell, 'opp 20-1')
            c_tot = 0; c_kl = 0; parts_ = []
            for i_ in range(len(levels_)):
                n_ = cnt_.get(f"ac0: play2 draw from {cell_} resolved at level {i_}", 0); c_tot += n_
                if i_ not in keyed_: c_kl += n_
                if n_: parts_.append(f"L{i_} {n_}")
            by_cell[cell_] = (c_tot, c_kl, " ".join(parts_)); tot_ += c_tot; keyless_ += c_kl
        return tot_, keyless_, by_cell
    CELLS_ = {}
    def level_lines(label_, cnt_, levels_):
        tot_, kl_, by_ = level_shares(cnt_, levels_); CELLS_[label_] = by_
        print(f"    {label_}: draws inside the 20 {tot_} | keyless {kl_} ({kl_ / tot_ if tot_ else float('nan'):.4f}) | by cell: " + " | ".join(f"{c_}: {v_[0]} draws, keyless {v_[1]} ({v_[1] / v_[0] if v_[0] else float('nan'):.3f}) [{v_[2]}]" for c_, v_ in by_.items()))
        return (kl_ / tot_) if tot_ else np.nan
    LV2 = lambda m_: list(getattr(m_, "PLAY2_LV", None) or [("kind", "inc_k", "ob_k") + l for l in m_.FULL_YL])   # v33: the levels the model's snap pool draws at (the counter's level i is this list's i)
    CNT_TD = Counter()
    for o_ in OUT_TDS: CNT_TD.update(o_[2])
    print("  the levels each engine's snap pool draws at, by index (a level is keyless when its key holds none of yl20, yl5, yl5in):")
    for nm_, m_ in (("the landed engine", MODS_["read"]), ("the candidate", e1n), ("ac1's plant", MODS_["acplant"])):
        print(f"    {nm_}: " + " | ".join(f"L{i_} {lv_}{'' if ({'yl20', 'yl5', 'yl5in', 'yl20in'} & set(lv_)) else ' (keyless)'}" for i_, lv_ in enumerate(LV2(m_))))
    print("  ad0 (a): the keyless share over every draw inside the 20, every season and 2024 beside; a draw inside the 1 is its own cell (the candidate's 'inside the 1', the landed engine's 'opp 20-1'); v33 printed 0.0019 over the four cells, the bound about 0.009:")
    AC0_SHARE = level_lines("the landed engine, every season", CNT_TD, LV2(MODS_["read"]))
    AC0_SHARE_24 = level_lines(f"the landed engine, {AB_S}", OUT_TD[2], LV2(MODS_["read"]))
    AC1_SHARE = level_lines("the candidate, every season", CNTM, LV2(e1n))
    AC1_SHARE_24 = level_lines(f"the candidate, {AB_S}", OUTM[S.index(AB_S)][2], LV2(e1n))
    level_lines(f"ac1's plant, {AB_S}", OUT_PL[2], LV2(MODS_["acplant"]))
    L6_ = [i_ for i_, lv_ in enumerate(LV2(e1n)) if lv_ == ("kind", "yl5in")]
    print(f"    DECLARED (the flags dropped): the candidate's draws at (kind, 5-yard cell), every season, by cell: " + (" | ".join(f"{c_} {CNTM.get(f'ac0: play2 draw from {c_} resolved at level {L6_[0]}', 0)}" for c_ in ("1-5", "6-10", "11-15", "16-20")) if L6_ else "the level is not in the candidate's levels"))
    AC1_CHECK = None if np.isnan(AC1_SHARE) else bool(AC1_SHARE < 0.02)
    print(f"  the landed engine's keyless share {AC0_SHARE:.4f} (printed; ac0's gate removed from the landing checks by '### v19 ad addition' item 1)"
          f" | ac1's check: the candidate's keyless share {AC1_SHARE:.4f} -> {'below 0.02: PASS' if AC1_CHECK else ('NOT MEASURED' if AC1_CHECK is None else 'FAIL')}")
    print("  the draws censored at the goal by cell (the landed engine 2024 | the candidate 2024 | the candidate, every season):")
    def cen_lines(cnt_, label_):
        tot_c = 0; tot_d = 0; parts_ = []
        for cell_ in ("1-5", "6-10", "11-15", "16-20"):
            c_ = cnt_.get(f"ab1: draws censored at the goal (the drawn gain past it), from {cell_}", 0); d_ = cnt_.get(f"ab1: snap draws from {cell_}", 0); tot_c += c_; tot_d += d_
            parts_.append(f"{cell_}: {c_} of {d_} ({c_ / d_ if d_ else float('nan'):.3f})")
        print(f"    {label_}: censored {tot_c} of {tot_d} draws inside the 20 ({tot_c / tot_d if tot_d else float('nan'):.3f}) | " + " | ".join(parts_))
    cen_lines(CNT_TD, "the landed engine, every season"); cen_lines(OUT_TD[2], f"the landed engine, {AB_S}"); cen_lines(OUTM[S.index(AB_S)][2], f"the candidate, {AB_S}"); cen_lines(CNTM, "the candidate, every season")

    print("  aa3's lines: snaps from the opponent's 11-20 by kind (the reader's kind) and their gain in 5-yard bins; the touchdown share of those snaps:")
    YB = [("a loss", lambda v: v < 0), ("0-4", lambda v: (v >= 0) & (v < 5)), ("5-9", lambda v: (v >= 5) & (v < 10)), ("10-14", lambda v: (v >= 10) & (v < 15)), ("15-19", lambda v: (v >= 15) & (v < 20)), ("20+", lambda v: v >= 20), ("no yards", lambda v: np.isnan(v))]
    def sn1120(x):
        yl_ = x["yardline_100"].to_numpy(float); m_ = x["snap"].to_numpy() & (yl_ >= 11) & (yl_ <= 20) & (x["qtr"].to_numpy(float) <= 4) & x["kind"].isin(list(e1.CALL)).to_numpy()
        return (m_, x["kind"].to_numpy(object), x["yards_gained"].to_numpy(float), x["game_id"].to_numpy(object), (x["touchdown"] == 1).to_numpy() & (x["td_team"].to_numpy(object) == x["posteam"].to_numpy(object)))
    SN = {nm: sn1120(AA[nm]) for nm in AA}; SNP = sn1120(AAP); SNT = sn1120(AAT)
    w_line("snaps from the 11-20 a game (regulation, a called play)", pg_aa(SN["record"][0].astype(float), SN["record"][3], GAMES_AA["record"]), pg_aa(SN["engine"][0].astype(float), SN["engine"][3], GAMES_AA["engine"]))
    BIN1120 = {}
    KINDS_ = sorted(set(SN["record"][1][SN["record"][0]]) | set(SN["engine"][1][SN["engine"][0]]), key=str)
    for k_ in KINDS_:
        w_line(f"  share {k_}", *(w_mean((SN[nm][1][SN[nm][0]] == k_).astype(float), SN[nm][3][SN[nm][0]]) for nm in ("record", "engine")))
        if k_ in ("pass", "run"):
            for lab_, f_ in YB:
                BIN1120[(k_, lab_)] = w_line(f"      yards {lab_}" + (" (record 0.080; v26 0.035)" if (k_, lab_) == ("pass", "15-19") else ""), *(w_mean(f_(SN[nm][2][SN[nm][0] & (SN[nm][1] == k_)]).astype(float), SN[nm][3][SN[nm][0] & (SN[nm][1] == k_)]) for nm in ("record", "engine")))
    TD1120 = w_line("  the share of those snaps that score a touchdown (record 0.081; v26 0.042)", *(w_mean(SN[nm][4][SN[nm][0]].astype(float), SN[nm][3][SN[nm][0]]) for nm in ("record", "engine")))
    # ac1's plant on 2024: the 16-20 touchdown share against the record's 2024; the candidate's 2024 beside (the plant must read APART where the candidate reads within)
    r24 = AA["record"][AA["record"]["season"] == AB_S]; e24 = AA["engine"][AA["engine"]["season"] == AB_S]
    def td_share(x, lo_, hi_):
        pr_ = x["snap"].to_numpy() & x["kind"].isin(list(e1.CALL)).to_numpy() & (x["penalty"].to_numpy(float) != 1) & ~np.isnan(x["yardline_100"].to_numpy(float)) & ~np.isnan(x["yards_gained"].to_numpy(float))
        yl_ = x["yardline_100"].to_numpy(float); m_ = pr_ & (yl_ >= lo_) & (yl_ <= hi_)
        return w_mean((x["yards_gained"].to_numpy(float)[m_] >= yl_[m_]).astype(float), x["game_id"].to_numpy(object)[m_])
    TD24 = {"record": td_share(r24, 16, 20), "candidate": td_share(e24, 16, 20), "plant": td_share(AAP, 16, 20), "landed": td_share(AAT, 16, 20)}
    AC_PL_C = within(TD24["record"], TD24["candidate"])[2]; AC_PL_P = within(TD24["record"], TD24["plant"])[2]; AC_PL_L = within(TD24["record"], TD24["landed"])[2]
    print(f"  ac1's plant on {AB_S}, the 16-20 touchdown share: the record {TD24['record'][0]:.4f} ±{TD24['record'][1]:.4f} | the candidate {TD24['candidate'][0]:.4f} ±{TD24['candidate'][1]:.4f} -> {wd(AC_PL_C)}"
          f" | the plant {TD24['plant'][0]:.4f} ±{TD24['plant'][1]:.4f} -> {wd(AC_PL_P)} | the landed engine {TD24['landed'][0]:.4f} ±{TD24['landed'][1]:.4f} -> {wd(AC_PL_L)}")
    AC_PLANT_OK = None if (AC_PL_C is None or AC_PL_P is None) else bool(AC_PL_C and not AC_PL_P)
    print(f"  ac1's plant: {'APART where the candidate is within, as it must' if AC_PLANT_OK else ('NOT MEASURED' if AC_PLANT_OK is None else ('the candidate itself is APART on 2024' if not AC_PL_C else 'the plant DID NOT read APART'))}")

    print("  possessions (r1.possessions) by how they end, and where drives stall (z2, z3):")
    HALF = lambda q: 1 if q <= 2 else (2 if q <= 4 else 3)
    def endings(x):
        d = x[["game_id", "order_sequence", "posteam", "qtr", "play_type", "two_point_attempt", "interception", "fumble_recovery_1_team"]].copy()
        d["fumble_recovery_1_team"] = [v if isinstance(v, str) else np.nan for v in d["fumble_recovery_1_team"]]
        P = r1.possessions(d)
        g = x["game_id"].to_numpy(object); seq = x["order_sequence"].to_numpy(float); idx = {(a, b): i for i, (a, b) in enumerate(zip(g, seq))}
        pt = x["play_type"].to_numpy(object); yl = x["yardline_100"].to_numpy(float); dn = x["down"].to_numpy(float); q = x["qtr"].to_numpy(float)
        td = (x["touchdown"] == 1).to_numpy() & (x["two_point_attempt"] != 1).to_numpy(); tdt = x["td_team"].to_numpy(object); sf = (x["safety"] == 1).to_numpy()
        fgr = x["field_goal_result"].to_numpy(object); itc = (x["interception"] == 1).to_numpy(); fl = (x["fumble_lost"] == 1).to_numpy(); r1t = x["fumble_recovery_1_team"].to_numpy(object)
        snap = x["snap"].to_numpy(); pos = x["posteam"].to_numpy(object)
        Pg = P["game_id"].to_numpy(object); Pt = P["team"].to_numpy(object); Ps0 = P["s0"].to_numpy(float); Ps1 = P["s1"].to_numpy(float); Pq = P["q"].to_numpy(float)
        E = []; DEEP = []; FGA = []; TDE = []
        for k in range(len(P)):
            i0, i1 = idx[(Pg[k], Ps0[k])], idx[(Pg[k], Ps1[k])]; t = Pt[k]
            sn = [i for i in range(i0, i1 + 1) if snap[i] and pos[i] == t]
            yls = yl[sn]; yls = yls[~np.isnan(yls)]; DEEP.append(yls.min() if len(yls) else np.nan)
            fga = pt[i1] == "field_goal"; FGA.append(fga)
            if sf[i1]: e = "safety"
            elif td[i1] and tdt[i1] == t: e = "touchdown"
            elif td[i1] and tdt[i1] is not None and tdt[i1] != t: e = "turnover returned for a touchdown"
            elif fga: e = "field goal" if fgr[i1] == "made" else "missed field goal"
            elif pt[i1] == "punt": e = "punt"
            elif itc[i1] or fl[i1] or (isinstance(r1t[i1], str) and r1t[i1] != t): e = "turnover"
            else:
                nxt = k + 1 < len(P) and Pg[k + 1] == Pg[k]
                if not nxt or HALF(Pq[k + 1]) != HALF(q[i1]): e = "end of half"
                elif dn[i1] == 4: e = "downs"
                else: e = "other"
            E.append(e); TDE.append(e == "touchdown")
        P["end"] = E; P["deep"] = DEEP; P["fga"] = FGA; P["tde"] = TDE
        return P
    PO = {nm: endings(AA[nm]) for nm in AA}
    ENDS = ["touchdown", "field goal", "missed field goal", "punt", "turnover", "turnover returned for a touchdown", "downs", "end of half", "safety", "other"]
    w_line("possessions a game (r1.possessions)", pg_aa(np.ones(len(PO["record"])), PO["record"]["game_id"], GAMES_AA["record"]), pg_aa(np.ones(len(PO["engine"])), PO["engine"]["game_id"], GAMES_AA["engine"]))
    Z2E = {e_: w_line(f"{e_} a game", pg_aa((PO["record"]["end"] == e_).astype(float), PO["record"]["game_id"], GAMES_AA["record"]), pg_aa((PO["engine"]["end"] == e_).astype(float), PO["engine"]["game_id"], GAMES_AA["engine"])) for e_ in ENDS}
    TD_S = {nm: pg_aa(PO[nm]["tde"].astype(float), PO[nm]["game_id"], GAMES_AA[nm]) for nm in PO}; TDG = w_line("touchdowns a game, on possessions (record 4.933; v26 4.287)", TD_S["record"], TD_S["engine"]); TD_ENG, TD_REC = TD_S["engine"][0], TD_S["record"][0]
    FG_S = {nm: pg_aa(PO[nm]["fga"].astype(float), PO[nm]["game_id"], GAMES_AA[nm]) for nm in PO}; FGG = w_line("field goal tries a game (the last snap a field goal; record 3.891; v26 3.498)", FG_S["record"], FG_S["engine"]); FG_ENG, FG_REC = FG_S["engine"][0], FG_S["record"][0]
    mk4 = {nm: PO[nm][PO[nm]["fga"]] for nm in PO}
    MKR = w_line("of the tries, the share made", w_mean((mk4["record"]["end"] == "field goal").astype(float), mk4["record"]["game_id"]), w_mean((mk4["engine"]["end"] == "field goal").astype(float), mk4["engine"]["game_id"]))
    r20 = {nm: (PO[nm]["deep"] <= 20).to_numpy() for nm in PO}
    TD20 = w_line("the touchdown share of possessions reaching the 20 (record 0.571; v26 0.552)", *(w_mean(PO[nm]["tde"].to_numpy()[r20[nm]].astype(float), PO[nm]["game_id"].to_numpy(object)[r20[nm]]) for nm in ("record", "engine")))
    print("  how the rest end (possessions reaching the 20 with no touchdown), shares of them:")
    for e_ in ENDS:
        sel_ = {nm: r20[nm] & ~PO[nm]["tde"].to_numpy() for nm in PO}
        if any((PO[nm]["end"].to_numpy(object)[sel_[nm]] == e_).any() for nm in PO):
            w_line(f"    {e_}" + (" (record 0.297; v26 0.388)" if e_ == "downs" else ""), *(w_mean((PO[nm]["end"].to_numpy(object)[sel_[nm]] == e_).astype(float), PO[nm]["game_id"].to_numpy(object)[sel_[nm]]) for nm in ("record", "engine")))

    print("  the red-zone fourth downs by distance to gain (snaps a game; record 679, 817, 1149, 1445 snaps; v26 810, 1046, 1028, 1314):")
    DB4 = [("1", lambda v: v <= 1), ("2-3", lambda v: (v >= 2) & (v <= 3)), ("4-6", lambda v: (v >= 4) & (v <= 6)), ("7+", lambda v: v >= 7)]
    ZB4 = [("own side (51+)", lambda y: y >= 51), ("the 41-50", lambda y: (y >= 41) & (y <= 50)), ("opponent 40-21", lambda y: (y >= 21) & (y <= 40)), ("the red zone (20-1)", lambda y: y <= 20)]
    def f4(x):
        m_ = (x["down"].to_numpy(float) == 4) & x["snap"].to_numpy()
        return m_, x["ydstogo"].to_numpy(float), x["yardline_100"].to_numpy(float), x["choice"].to_numpy(object), x["game_id"].to_numpy(object)
    FZ = {nm: f4(AA[nm]) for nm in AA}; RZ4 = {}
    for dl, df_ in DB4:
        RZ4[dl] = w_line(f"  4th and {dl} inside the 20, a game (snaps record {int((FZ['record'][0] & df_(FZ['record'][1]) & (FZ['record'][2] <= 20)).sum())} | engine {int((FZ['engine'][0] & df_(FZ['engine'][1]) & (FZ['engine'][2] <= 20)).sum())})",
                        *(pg_aa((FZ[nm][0] & df_(FZ[nm][1]) & (FZ[nm][2] <= 20)).astype(float), FZ[nm][4], GAMES_AA[nm]) for nm in ("record", "engine")))

    print("  points a game by how they were scored (the library's credit, vectorised: touchdown 6 to td_team; the Try by kick 1 and by run or pass 2 to the offense; field goal 3;")
    print("  the safety 2 to the kicking team on a punt whose text says 'punts N yards' and is not BLOCKED, else to the defense; the defense's Try return 2):")
    def pts_kind(x):
        n = len(x); pos = x["posteam"].to_numpy(object); de = x["defteam"].to_numpy(object); tdt = x["td_team"].to_numpy(object); pt = x["play_type"].to_numpy(object); ds = x["desc"].astype(str).to_numpy(object)
        tp = x["two_point_attempt"].to_numpy(float); g = x["game_id"].to_numpy(object)
        punt_k = np.array([pt[i] == "punt" and bool(re.search(r"punts -?\d+ yards", ds[i])) and "BLOCKED" not in ds[i].upper() for i in range(n)], bool)
        M = {"touchdown": ((x["touchdown"] == 1).to_numpy() & (tp != 1), 6.0), "try, kick": ((x["extra_point_result"] == "good").to_numpy(), 1.0), "try, two-point": ((x["two_point_conv_result"] == "success").to_numpy(), 2.0),
             "field goal": ((x["field_goal_result"] == "made").to_numpy(), 3.0), "safety": ((x["safety"] == 1).to_numpy(), 2.0),
             "try, defensive return": (((x["defensive_two_point_conv"] == 1) | (x["defensive_extra_point_conv"] == 1)).to_numpy(), 2.0)}
        return {k_: (m_.astype(float) * v_, g) for k_, (m_, v_) in M.items()}
    PK = {nm: pts_kind(AA[nm]) for nm in AA}
    for k_ in PK["record"]:
        w_line(f"  {k_}", *(pg_aa(PK[nm][k_][0], PK[nm][k_][1], GAMES_AA[nm]) for nm in ("record", "engine")))
    PTS_SIDE = {nm: pg_aa(sum(v_[0] for v_ in PK[nm].values()), AA[nm]["game_id"], GAMES_AA[nm]) for nm in AA}
    PTS = w_line("points a game, every kind (record 46.15; v26 38.96)", PTS_SIDE["record"], PTS_SIDE["engine"]); PTS_ENG = PTS_SIDE["engine"][0]
    print("\n=== ab3 (a read): the engine's snaps inside the opponent's 20 beside the record's, by yard line and by 5-yard cell; the first-and-10 share by cell; the in-game share gaining")
    print("    15+ at first and 10 from the 16-20; possessions entering the 20 by the cell first reached and by how (a gain from outside, a penalty, a kickoff or turnover spot) ===")
    def pool_rows(x):
        return x["snap"].to_numpy() & x["kind"].isin(list(e1.CALL)).to_numpy() & (x["penalty"].to_numpy(float) != 1) & ~np.isnan(x["yardline_100"].to_numpy(float)) & ~np.isnan(x["yards_gained"].to_numpy(float))
    PR = {nm: pool_rows(AA[nm]) for nm in AA}
    YL = {nm: AA[nm]["yardline_100"].to_numpy(float) for nm in AA}; YG = {nm: AA[nm]["yards_gained"].to_numpy(float) for nm in AA}; GI = {nm: AA[nm]["game_id"].to_numpy(object) for nm in AA}
    DN = {nm: AA[nm]["down"].to_numpy(float) for nm in AA}; TG = {nm: AA[nm]["ydstogo"].to_numpy(float) for nm in AA}
    SNYL = {}
    for yl_ in range(1, 21):
        SNYL[yl_] = w_line(f"  the {yl_:2d}: snaps a game", *(pg_aa((PR[nm] & (YL[nm] == yl_)).astype(float), GI[nm], GAMES_AA[nm]) for nm in ("record", "engine")))
    CELL = (("1-5", 1, 5), ("6-10", 6, 10), ("11-15", 11, 15), ("16-20", 16, 20)); AB3 = {}
    for lab_, lo_, hi_ in CELL:
        m_ = {nm: PR[nm] & (YL[nm] >= lo_) & (YL[nm] <= hi_) for nm in AA}
        AB3[("snaps", lab_)] = w_line(f"  the {lab_}: snaps a game", *(pg_aa(m_[nm].astype(float), GI[nm], GAMES_AA[nm]) for nm in ("record", "engine")))
        AB3[("1st10", lab_)] = w_line(f"      first-and-10 share of them", *(w_mean(((DN[nm] == 1) & (TG[nm] == 10))[m_[nm]].astype(float), GI[nm][m_[nm]]) for nm in ("record", "engine")))
        AB3[("td", lab_)] = w_line(f"      touchdown share (the gain at least the distance; v31: APART in every cell, the 16-20 0.037 against 0.072)", *(w_mean((YG[nm][m_[nm]] >= YL[nm][m_[nm]]).astype(float), GI[nm][m_[nm]]) for nm in ("record", "engine")))
    m1_ = {nm: PR[nm] & (YL[nm] >= 16) & (YL[nm] <= 20) & (DN[nm] == 1) & (TG[nm] == 10) for nm in AA}
    AB3["case"] = w_line("  first and 10 from the 16-20, the share gaining 15+ in the games (the record 0.1012; v31's engine 0.086; the case's draw printed above)", *(w_mean((YG[nm][m1_[nm]] >= 15).astype(float), GI[nm][m1_[nm]]) for nm in ("record", "engine")))
    def entries(x, P_):
        """Each possession reaching the 20: the cell of its first snap inside, and how the ball got there: the row before it in the possession a snap outside (a gain from
        outside), a no-play with a foul (a penalty), none (the possession started inside: a kickoff or turnover spot), else other."""
        g = x["game_id"].to_numpy(object); seq = x["order_sequence"].to_numpy(float); idx = {(a, b): i for i, (a, b) in enumerate(zip(g, seq))}
        snap = x["snap"].to_numpy(); pos = x["posteam"].to_numpy(object); yl = x["yardline_100"].to_numpy(float); pt = x["play_type"].to_numpy(object); pen = (x["penalty"] == 1).to_numpy()
        out_ = []
        for g_, t_, s0, s1 in zip(P_["game_id"], P_["team"], P_["s0"], P_["s1"]):
            i0, i1 = idx[(g_, float(s0))], idx[(g_, float(s1))]; rows_ = [i for i in range(i0, i1 + 1) if pos[i] == t_]
            first_ = next((i for i in rows_ if snap[i] and not np.isnan(yl[i]) and yl[i] <= 20), None)
            if first_ is None: continue
            w_ = int(np.floor(yl[first_])); cell_ = "1-5" if w_ <= 5 else ("6-10" if w_ <= 10 else ("11-15" if w_ <= 15 else "16-20"))   # the yard line's cell by its whole yards toward the goal (a fraction or 0 falls in the nearest cell, never unbinned)
            prev_ = [i for i in rows_ if i < first_ and (snap[i] or (pt[i] == "no_play" and pen[i]))]
            if not prev_: how_ = "a kickoff or turnover spot (the possession began inside)"
            elif pt[prev_[-1]] == "no_play" and pen[prev_[-1]]: how_ = "a penalty"
            elif snap[prev_[-1]]: how_ = "a gain from outside"
            else: how_ = "other"
            out_.append((g_, cell_, how_))
        return pd.DataFrame(out_, columns=["game_id", "cell", "how"])
    EN = {nm: entries(AA[nm], PO[nm]) for nm in AA}
    w_line("  possessions entering the 20 a game", *(pg_aa(np.ones(len(EN[nm])), EN[nm]["game_id"], GAMES_AA[nm]) for nm in ("record", "engine")))
    for lab_, _, _ in CELL:
        w_line(f"    first reached the {lab_}, a game", *(pg_aa((EN[nm]["cell"] == lab_).astype(float), EN[nm]["game_id"], GAMES_AA[nm]) for nm in ("record", "engine")))
    for how_ in ("a gain from outside", "a penalty", "a kickoff or turnover spot (the possession began inside)", "other"):
        w_line(f"    by {how_}, a game", *(pg_aa((EN[nm]["how"] == how_).astype(float), EN[nm]["game_id"], GAMES_AA[nm]) for nm in ("record", "engine")))
        for lab_, _, _ in CELL:
            w_line(f"        into the {lab_}", *(pg_aa(((EN[nm]["how"] == how_) & (EN[nm]["cell"] == lab_)).astype(float), EN[nm]["game_id"], GAMES_AA[nm]) for nm in ("record", "engine")))

    print("\n=== ad2 (reads, nothing built from them), engine beside record, 2SE by game (the called plays with no foul, as ab3) ===")
    print("  (a) the 1-5 by yard line: snaps a game and the touchdown share; each line's gap times its engine count over the cell's, summed against the cell's gap:")
    m15_ = {nm: PR[nm] & (YL[nm] >= 1) & (YL[nm] <= 5) for nm in AA}
    tdc_ = {nm: w_mean((YG[nm][m15_[nm]] >= YL[nm][m15_[nm]]).astype(float), GI[nm][m15_[nm]]) for nm in AA}
    Ne_ = int(m15_["engine"].sum()); part_ = 0.0
    for yl_ in range(1, 6):
        ml_ = {nm: PR[nm] & (YL[nm] == yl_) for nm in AA}
        w_line(f"    the {yl_}: snaps a game", *(pg_aa(ml_[nm].astype(float), GI[nm], GAMES_AA[nm]) for nm in ("record", "engine")))
        tl_ = {nm: w_mean((YG[nm][ml_[nm]] >= yl_).astype(float), GI[nm][ml_[nm]]) for nm in AA}
        w_line(f"      the touchdown share at the {yl_}", tl_["record"], tl_["engine"])
        c_ = (tl_["engine"][0] - tl_["record"][0]) * int(ml_["engine"].sum()) / max(Ne_, 1)
        part_ += c_; print(f"      its gap times its engine share of the cell's snaps: {c_:+.4f}")
    cg_ = tdc_["engine"][0] - tdc_["record"][0]
    print(f"    the cell's gap {cg_:+.4f} | the lines' gaps summed {part_:+.4f} | the rest, where the snaps sit (composition) {cg_ - part_:+.4f}")
    print("  ad addition item 4 (a read, nothing built from it): the touchdown share at each written yard line 1-5, the engine's called snaps with no foul split by the exact")
    print("  spot (a whole yard or a fraction: the candidate's counter, the rows keep only the written spot), the record's share at the line beside; the line's gap (the")
    print("  counter's engine share less the record's) = the whole-yard part (its snaps over the line's, times its share less the record's) + the fractional part:")
    def i4_(cell_, yl_, td_):
        return CNTM.get(f"ad addition item 4: a called snap, no foul, at the {yl_} from a {cell_} spot: {td_}", 0)
    bs_ = lambda t, n: (t / n, 2 * np.sqrt((t / n) * (1 - t / n) / n)) if n >= 2 else (np.nan, np.nan)
    I4 = {}
    for yl_ in range(1, 6):
        ml_ = {nm: PR[nm] & (YL[nm] == yl_) for nm in AA}; r_ = w_mean((YG["record"][ml_["record"]] >= yl_).astype(float), GI["record"][ml_["record"]])
        tw_, nw_ = i4_("whole-yard", yl_, "touchdown"), i4_("whole-yard", yl_, "touchdown") + i4_("whole-yard", yl_, "no touchdown")
        tf_, nf_ = i4_("fractional", yl_, "touchdown"), i4_("fractional", yl_, "touchdown") + i4_("fractional", yl_, "no touchdown")
        n_ = nw_ + nf_; fe_ = int(ml_["engine"].sum()); fte_ = int((YG["engine"][ml_["engine"]] >= yl_).sum())
        pw_, pf_, pl_ = bs_(tw_, nw_), bs_(tf_, nf_), bs_(tw_ + tf_, n_)
        ok_ = nw_ >= 2 and nf_ >= 2 and not np.isnan(r_[0])
        gw_ = nw_ / n_ * (pw_[0] - r_[0]) if ok_ else np.nan; gf_ = nf_ / n_ * (pf_[0] - r_[0]) if ok_ else np.nan; gl_ = pl_[0] - r_[0] if ok_ else np.nan
        I4[yl_] = (nw_, tw_, nf_, tf_, gw_, gf_, gl_)
        print(f"    the {yl_}: record {r_[0]:.3f} ±{r_[1]:.3f} (n {int(ml_['record'].sum())}) | engine from a whole yard {pw_[0]:.3f} ±{pw_[1]:.3f} ({tw_} of {nw_}) | from a fraction {pf_[0]:.3f} ±{pf_[1]:.3f} ({tf_} of {nf_})"
              f" | the counter's line {pl_[0]:.3f} ({tw_ + tf_} of {n_}) | the rows' line {fte_} of {fe_}{'' if (n_ == fe_ and tw_ + tf_ == fte_) else ' DIFFERENT: the counter and the rows do not count the same snaps'}")
        print(f"      the line's gap {gl_:+.4f} = the whole-yard part {gw_:+.4f} + the fractional part {gf_:+.4f} (summed {gw_ + gf_:+.4f})" if ok_ else "      the split NOT MEASURED (a part under 2 snaps or a NaN)")
    print("\n=== af0 (a read on the landed engine, before any change) and af1: each line 1-5 by the level its draws resolved at (af0's counter: called snaps with no foul) ===")
    def af_cnt(cnt_, L_, i_, td_):
        return cnt_.get(f"af0: a called snap, no foul, at the {L_} drawn at level {i_}: {td_}", 0)
    def af_split(cnt_, levels_, L_):
        yk_ = [i_ for i_, l_ in enumerate(levels_) if ({"yl20", "yl20in"} & set(l_))]; ck_ = [i_ for i_ in range(len(levels_)) if i_ not in yk_]
        ty_ = sum(af_cnt(cnt_, L_, i_, "touchdown") for i_ in yk_); ny_ = ty_ + sum(af_cnt(cnt_, L_, i_, "no touchdown") for i_ in yk_)
        tc_ = sum(af_cnt(cnt_, L_, i_, "touchdown") for i_ in ck_); nc_ = tc_ + sum(af_cnt(cnt_, L_, i_, "no touchdown") for i_ in ck_)
        return ny_, ty_, nc_, tc_
    bsw_ = lambda t, n: (t / n, 2 * np.sqrt((t / n) * (1 - t / n) / n), n) if n >= 2 else (np.nan, np.nan, n)
    PR_ALL = {nm: AA[nm]["snap"].to_numpy() & (AA[nm]["penalty"].to_numpy(float) != 1) & ~np.isnan(AA[nm]["yardline_100"].to_numpy(float)) for nm in AA}   # every snap with no foul (ae1's rows, its seven kinds selected below)
    REC_L = {}
    for L_ in range(1, 6):
        mr_ = PR["record"] & (YL["record"] == L_); REC_L[L_] = w_mean((YG["record"][mr_] >= L_).astype(float), GI["record"][mr_])
    AF0 = {}; AFSH = {}
    for nm_, cnt_, lv_ in (("the landed engine (af0)", CNT_TD, LV2(MODS_["read"])), ("the candidate (af1)", CNTM, LV2(e1n))):
        print(f"  {nm_}: its levels keyed by the yard line {[i_ for i_, l_ in enumerate(lv_) if ({'yl20', 'yl20in'} & set(l_))]} of {len(lv_)} | counted draws at the 1-5 {sum(sum(af_split(cnt_, lv_, L_)[0::2]) for L_ in range(1, 6))}")
        for L_ in range(1, 6):
            ny_, ty_, nc_, tc_ = af_split(cnt_, lv_, L_); n_ = ny_ + nc_; r_ = REC_L[L_]
            py_, pc_, pl_ = bsw_(ty_, ny_), bsw_(tc_, nc_), bsw_(ty_ + tc_, n_)
            ok_ = ny_ >= 2 and nc_ >= 2 and not np.isnan(r_[0])
            gy_ = ny_ / n_ * (py_[0] - r_[0]) if ok_ else np.nan; gc_ = nc_ / n_ * (pc_[0] - r_[0]) if ok_ else np.nan; gl_ = (pl_[0] - r_[0]) if (n_ >= 2 and not np.isnan(r_[0])) else np.nan
            wy_ = within(r_, py_)[2] if (ny_ >= 2 and not np.isnan(r_[0])) else None
            AFSH[(nm_, L_)] = ny_ / n_ if n_ else np.nan
            if nm_.startswith("the landed"): AF0[L_] = (ny_, ty_, nc_, tc_, gy_, gc_, gl_, wy_)
            print(f"    the {L_}: record {r_[0]:.3f} ±{r_[1]:.3f} (n {r_[2]}) | at a yard-line level {py_[0]:.3f} ±{py_[1]:.3f} ({ty_} of {ny_}) -> {wd(wy_)} | the 5-yard cell or coarser {pc_[0]:.3f} ±{pc_[1]:.3f} ({tc_} of {nc_})"
                  f" | the share at a yard-line level {AFSH[(nm_, L_)]:.3f}")
            print(f"      the line's gap {gl_:+.4f} = the yard-line-level part {gy_:+.4f} + the coarser part {gc_:+.4f} (summed {gy_ + gc_:+.4f})" if ok_ else "      the split NOT MEASURED (a part under 2 draws or a NaN)")
    AF_BUILD = None if any(AF0[L_][7] is None for L_ in (2, 3, 5)) else (not all(AF0[L_][7] is False for L_ in (2, 3, 5)))
    print(f"  af0's gate: the landed engine's yard-line-level draws APART from the record at every line 2, 3 and 5: "
          + ('NOT MEASURED' if AF_BUILD is None else ('no: af1 is built' if AF_BUILD else 'yes: af closes as a read; af1 is printed and does not land')))
    AF1_CHECK = all((not np.isnan(AFSH[("the candidate (af1)", L_)])) and (not np.isnan(AFSH[("the landed engine (af0)", L_)])) and AFSH[("the candidate (af1)", L_)] > AFSH[("the landed engine (af0)", L_)] for L_ in range(1, 6))
    print("  the share of the counted draws at a yard-line level (af1's check, consumed at af's landing: printed, not a check), the landed engine -> the candidate: " + " | ".join(f"the {L_} {AFSH[('the landed engine (af0)', L_)]:.3f} -> {AFSH[('the candidate (af1)', L_)]:.3f}" for L_ in range(1, 6))
          + "")
    TD3 = {"record": td_share(r24, 3, 3), "candidate": td_share(e24, 3, 3), "plant": td_share(XAF, 3, 3), "landed": td_share(AAT, 3, 3)}
    AF_PL_C = within(TD3["record"], TD3["candidate"])[2]; AF_PL_P = within(TD3["record"], TD3["plant"])[2]
    AF_PLANT_OK = None if any(np.isnan(TD3[k_][1]) for k_ in ("record", "candidate", "plant")) else bool(AF_PL_C and not AF_PL_P)
    print(f"  af1's plant (the landed order on the candidate's tables), {AB_S}, the 3's touchdown share: the record {TD3['record'][0]:.4f} ±{TD3['record'][1]:.4f} (n {TD3['record'][2]}) | the candidate {TD3['candidate'][0]:.4f} ±{TD3['candidate'][1]:.4f} -> {wd(AF_PL_C)}"
          f" | the plant {TD3['plant'][0]:.4f} ±{TD3['plant'][1]:.4f} -> {wd(AF_PL_P)} | the landed engine {TD3['landed'][0]:.4f} ±{TD3['landed'][1]:.4f} -> {wd(within(TD3['record'], TD3['landed'])[2])}"
          f" -> {'APART where the candidate is within, as it must' if AF_PLANT_OK else ('NOT MEASURED' if AF_PLANT_OK is None else ('the candidate itself is APART on ' + str(AB_S) if not AF_PL_C else 'the plant DID NOT read APART'))}")
    print("  the touchdown share at each line 1-5 as ae1 read it (field goal tries counted, none a touchdown; the predictions are scored on it), engine beside record:")
    TDL_AE1 = {}
    for L_ in range(1, 6):
        v_ = {}
        for nm in AA:
            k_ = AA[nm]["kind"].to_numpy(object); m_ = PR_ALL[nm] & (YL[nm] == L_) & np.isin(k_, list(e1.CALL) + ["field_goal"]) & ~np.isnan(DN[nm])
            v_[nm] = w_mean((np.nan_to_num(YG[nm][m_], nan=0.0) >= L_).astype(float), GI[nm][m_])
        TDL_AE1[L_] = v_; w_line(f"    the {L_}", v_["record"], v_["engine"])
    print("  the fourth-down call at the 1 (printed, not built: the fourth-down call's link, aa): of fourth-down snaps with no foul at the 1, the share that are field goal tries:")
    m4_ = {nm: PR_ALL[nm] & (YL[nm] == 1) & (DN[nm] == 4) for nm in AA}
    w_line("    field goal tries at the 1 on fourth down", *(w_mean((AA[nm]["kind"].to_numpy(object)[m4_[nm]] == "field_goal").astype(float), GI[nm][m4_[nm]]) for nm in ("record", "engine")))
    print("\n=== ag0 (a read on the landed engine, before any change) and ag1: the fourth-down choice (go, field goal try, punt) ===")
    LV4R = RATES_["read"][S[0]].P["call4"].levels; LV4C = R[S[0]].P["call4"].levels; YLK4 = {"ylw", "yl20", "yl20in", "yl5", "yl5in"}
    print("  ag0 (a) the landed e1.py by line:")
    for n_, l_ in enumerate(E1_TXT.split("\n"), 1):
        if l_.startswith("MIN_BIN = ") or l_.startswith("FULL = ") or 'T["call4"] = ' in l_ or 'P["call4"] = Pool' in l_ or 'self.P["call4"].draw' in l_: print(f"    e1.py:{n_}: {l_.strip()[:170]}")
    print(f"  the landed engine's fourth-down levels {LV4R}")
    print(f"  the candidate's fourth-down levels {LV4C}")
    AG0_CARRIES = any(YLK4 & set(l_) for l_ in LV4R[:1])
    ZON4 = ("the 1", "2-3", "4-5", "6-10", "11-20", "opp 21-40", "the 41-50", "own side"); D4 = ("1", "2-3", "4-6", "7+"); CH3 = ("go", "field_goal", "punt")
    def zone4_v(y):
        return np.select([y <= 1, y <= 3, y <= 5, y <= 10, y <= 20, y <= 40, y <= 50], list(ZON4[:7]), ZON4[7])
    def d4_v(t):
        return np.select([t <= 1, t <= 3, t <= 6], ["1", "2-3", "4-6"], "7+")
    M4 = {nm: (DN[nm] == 4) & AA[nm]["snap"].to_numpy() & (AA[nm]["penalty"].to_numpy(float) != 1) & np.isin(AA[nm]["kind"].to_numpy(object), list(e1.CALL) + ["punt", "field_goal"]) & ~np.isnan(YL[nm]) & ~np.isnan(TG[nm]) for nm in AA}
    Z4R = zone4_v(YL["record"]); D4R = d4_v(TG["record"]); CHR = AA["record"]["choice"].to_numpy(object)
    def ag_cnt(cnt_, z_, d_, lev_, ch_):
        return cnt_.get(f"ag0: fourth-down choice at {z_} {d_} drawn at level {lev_}: {ch_}", 0)
    def ag_cell(cnt_, levels_, z_, d_):
        n_ = {ch_: sum(ag_cnt(cnt_, z_, d_, i_, ch_) for i_ in range(len(levels_))) for ch_ in CH3}
        ny_ = sum(ag_cnt(cnt_, z_, d_, i_, ch_) for i_, l_ in enumerate(levels_) if YLK4 & set(l_) for ch_ in CH3)
        return n_, ny_
    bin_ = lambda k, n: (k / n, 2 * np.sqrt((k / n) * (1 - k / n) / n), n) if n >= 2 else (np.nan, np.nan, n)
    AGW = {"landed": [0, 0], "candidate": [0, 0]}; AGZ = {}; AGREC = {}
    print("  by zone and distance bin: the record's shares go / field goal / punt (2SE by game) | the landed engine's | the candidate's (binomial) | the share drawn at a yard-line level, landed -> candidate:")
    for z_ in ZON4:
        for d_ in D4:
            mr_ = M4["record"] & (Z4R == z_) & (D4R == d_)
            rv_ = {ch_: w_mean((CHR[mr_] == ch_).astype(float), GI["record"][mr_]) for ch_ in CH3}; AGREC[(z_, d_)] = rv_
            nl_, yl_ = ag_cell(CNT_TD, LV4R, z_, d_); nc_, yc_ = ag_cell(CNTM, LV4C, z_, d_); tl_, tc_ = sum(nl_.values()), sum(nc_.values())
            for nm_, n__, y__ in (("landed", tl_, yl_), ("candidate", tc_, yc_)):
                AGZ[(nm_, z_)] = (AGZ.get((nm_, z_), (0, 0))[0] + n__, AGZ.get((nm_, z_), (0, 0))[1] + y__)
            wl_ = sum(1 for ch_ in CH3 if tl_ >= 2 and not np.isnan(rv_[ch_][0]) and within(rv_[ch_], bin_(nl_[ch_], tl_))[2]); wc_ = sum(1 for ch_ in CH3 if tc_ >= 2 and not np.isnan(rv_[ch_][0]) and within(rv_[ch_], bin_(nc_[ch_], tc_))[2])
            AGW["landed"][0] += wl_; AGW["candidate"][0] += wc_; AGW["landed"][1] += 3 * int(tl_ >= 2 and rv_["go"][2] >= 2); AGW["candidate"][1] += 3 * int(tc_ >= 2 and rv_["go"][2] >= 2)
            print(f"    {z_:10s} {d_:4s} record " + " / ".join(f"{rv_[ch_][0]:.3f}" for ch_ in CH3) + f" (n {rv_['go'][2]}) | landed " + (" / ".join(f"{nl_[ch_] / tl_:.3f}" for ch_ in CH3) if tl_ else "-") + f" (n {tl_}, within {wl_} of 3)"
                  f" | candidate " + (" / ".join(f"{nc_[ch_] / tc_:.3f}" for ch_ in CH3) if tc_ else "-") + f" (n {tc_}, within {wc_} of 3) | at a yard-line level {(yl_ / tl_ if tl_ else np.nan):.3f} -> {(yc_ / tc_ if tc_ else np.nan):.3f}")
    print(f"  the shares within 2SE of the record's (zone x distance x choice, cells with 2 rows or more on both sides): landed {AGW['landed'][0]} of {AGW['landed'][1]} | candidate {AGW['candidate'][0]} of {AGW['candidate'][1]}")
    AG_BUILD = True if not AG0_CARRIES else (AGW["landed"][0] * 2 >= AGW["landed"][1])
    print(f"  ag0's gate: the landed pool carries the yard line at its first level: {'yes' if AG0_CARRIES else 'no'} -> " + ("ag1 is built" if AG_BUILD else "the yard-line draws are APART in most cells: ag closes as a read; ag1 is printed and does not land"))
    AG1_CHECK = all(AGZ.get(("candidate", z_), (0, 0))[0] > 0 and AGZ[("candidate", z_)][1] / AGZ[("candidate", z_)][0] > (AGZ[("landed", z_)][1] / AGZ[("landed", z_)][0] if AGZ.get(("landed", z_), (0, 0))[0] else 0.0) for z_ in ZON4)
    print("  the share of fourth-down draws at a level keyed by the yard line by zone (ag1's check, consumed at ag's landing: printed, not a check), landed -> candidate: " + " | ".join(
        f"{z_} {(AGZ[('landed', z_)][1] / AGZ[('landed', z_)][0] if AGZ.get(('landed', z_), (0, 0))[0] else float('nan')):.3f} -> {(AGZ[('candidate', z_)][1] / AGZ[('candidate', z_)][0] if AGZ.get(('candidate', z_), (0, 0))[0] else float('nan')):.3f}" for z_ in ZON4)
          + "")
    def case4(Rs, m_, s, n=2000):
        rng_ = np.random.default_rng([40, s]); c_ = Counter()
        k_ = dict(down=4, dist=m_.dist_bin(7), field=m_.field_bin(45), time=m_.time_bin(1, 600), score=m_.score_bin(0), ylw=45, dist4="7+", ycell="41-50", distw="7")
        for _ in range(n): c_[Rs.P["call4"].draw(rng_, k_)["choice"]] += 1
        return c_
    rc_ = AGREC[("the 41-50", "7+")]; REC_MARGIN = rc_["punt"][0] - rc_["field_goal"][0]
    AGC = {}
    for nm_, f_ in (("candidate", lambda s: (R[s], e1n)), ("the landed engine", lambda s: (RATES_["read"][s], MODS_["read"])), ("ag1's plant (the landed levels on the candidate's tables)", lambda s: (RATES_["agplant"][s], MODS_["agplant"]))):
        c_ = Counter()
        for s in S: c_.update(case4(*f_(s), s))
        n_ = sum(c_.values()); AGC[nm_] = (c_["punt"] / n_ - c_["field_goal"] / n_, c_, n_)
        print(f"  ag1 case (4th and 7 at the 45, first quarter, tied), {nm_}: punt {c_['punt'] / n_:.3f} | field goal {c_['field_goal'] / n_:.3f} | go {c_['go'] / n_:.3f} over {n_} draws | the margin {AGC[nm_][0]:+.3f}")
    AG_PLANT_M = AGC["ag1's plant (the landed levels on the candidate's tables)"][0]
    AG_CASE_OK = AGC["candidate"][0] >= REC_MARGIN; AG_PLANT_OK = AG_PLANT_M < REC_MARGIN
    print(f"  the record, the 41-50 at 7+: punt {rc_['punt'][0]:.3f} | field goal {rc_['field_goal'][0]:.3f} (n {rc_['go'][2]}) | the margin {REC_MARGIN:+.3f} -> the candidate {'at or above it: PASS' if AG_CASE_OK else 'below it: FAIL'} | the plant {'below it: FAILS as it must' if AG_PLANT_OK else 'at or above it: DID NOT FAIL'}")
    print("  ag2: the make share by kick distance (field goal tries with no foul; the kick's distance the yard line + 17), engine beside record:")
    for lab_, lo_, hi_ in (("under 30", 0, 29), ("30-39", 30, 39), ("40-49", 40, 49), ("50+", 50, 99)):
        v_ = {}
        for nm in AA:
            mf_ = (AA[nm]["kind"].to_numpy(object) == "field_goal") & (AA[nm]["penalty"].to_numpy(float) != 1) & (YL[nm] + 17 >= lo_) & (YL[nm] + 17 <= hi_)
            v_[nm] = w_mean((AA[nm]["field_goal_result"].to_numpy(object)[mf_] == "made").astype(float), GI[nm][mf_])
        w_line(f"    {lab_} yards", v_["record"], v_["engine"])
    FG1 = w_line("  ag2: field goal tries of fourth downs with no foul at the 1", *(w_mean((AA[nm]["kind"].to_numpy(object)[M4[nm] & (YL[nm] == 1)] == "field_goal").astype(float), GI[nm][M4[nm] & (YL[nm] == 1)]) for nm in ("record", "engine")))
    print("\n=== ai0 (b), ai0 (a)'s second reader, ai1, ai2, ai3: the fourth-down distance; ah1's reader; the punt split; drive progress outside the red zone ===")
    print("  ai0 (b) the landed e1.py by line (the distance bin and the fourth-down pool):")
    for n_, l_ in enumerate(E1_TXT.split("\n"), 1):
        if l_.startswith("def dist_bin") or 'return "1-3" if t <= 3' in l_ or l_.startswith("def dist4_bin") or 'return "1" if t <= 1 else ("2-3"' in l_ or 'P["call4"] = Pool' in l_: print(f"    e1.py:{n_}: {l_.strip()[:220]}")
    AI_SHARES_BIN = (e1n.dist_bin(1) == e1n.dist_bin(2)) or (e1n.dist_bin(1) == e1n.dist_bin(3))
    print(f"  the landed fourth-down levels' distance keys: {[[k_ for k_ in l_ if k_ in ('dist', 'dist4', 'distw')] for l_ in LV4R]} | dist_bin(1) {e1n.dist_bin(1)!r}, dist_bin(2) {e1n.dist_bin(2)!r}, dist_bin(3) {e1n.dist_bin(3)!r}"
          f" -> 4th and 1 {'shares a bin with 2-3 at the first levels: ai1 is built' if AI_SHARES_BIN else 'stands alone: ai closes as a read'}")
    AI_BUILD = bool(AI_SHARES_BIN)
    ZON10 = [("the 1", 1, 1), ("2-3", 2, 3), ("4-5", 4, 5), ("6-10", 6, 10), ("11-20", 11, 20), ("opponent 21-40", 21, 40), ("the 41-50", 41, 50), ("own 41-49", 51, 59), ("own 21-40", 60, 79), ("own 1-20", 80, 99)]
    D4H = [("1", 0, 1), ("2-3", 1.0001, 3), ("4-6", 3.0001, 6), ("7+", 6.0001, 999)]
    def p4_(x):
        return (x["down"].to_numpy(float) == 4) & x["snap"].to_numpy() & (x["penalty"].to_numpy(float) != 1) & np.isin(x["kind"].to_numpy(object), list(e1.CALL) + ["punt", "field_goal"]) & ~np.isnan(x["yardline_100"].to_numpy(float)) & ~np.isnan(x["ydstogo"].to_numpy(float))
    def cell_(x, m0, lo, hi, dlo, dhi):
        y_ = x["yardline_100"].to_numpy(float); t_ = x["ydstogo"].to_numpy(float); return m0 & (y_ >= lo) & (y_ <= hi) & (t_ >= dlo) & (t_ <= dhi)
    def ah1_(xr, xe):
        out = {}; mr0, me0 = p4_(xr), p4_(xe)
        for zl, lo, hi in ZON10:
            for dl, dlo, dhi in D4H:
                ma, mb = cell_(xr, mr0, lo, hi, dlo, dhi), cell_(xe, me0, lo, hi, dlo, dhi)
                for ch in ("go", "field_goal", "punt"):
                    a_ = w_mean((xr["choice"].to_numpy(object)[ma] == ch).astype(float), xr["game_id"].to_numpy(object)[ma]); b_ = w_mean((xe["choice"].to_numpy(object)[mb] == ch).astype(float), xe["game_id"].to_numpy(object)[mb])
                    ok_ = None if any(np.isnan([a_[0], a_[1], b_[0], b_[1]])) else bool(abs(b_[0] - a_[0]) <= np.sqrt(a_[1] ** 2 + b_[1] ** 2))
                    out[(zl, dl, ch)] = (ok_, a_, b_, int(ma.sum()), int(mb.sum()))
        return out
    def file_side_(p_):
        g_ = pd.read_csv(p_, dtype=str, keep_default_na=False, skiprows=1); return aa_prep(w_side({s: g_[g_["season"] == str(s)].reset_index(drop=True) for s in S}))
    V36G = os.path.join("evidence", "e2b_v37_37db486d756e", "20261031T011933Z_60773_full", "replaced", "sim_games.csv"); V37G = "out/sim_games.csv"
    print(f"  ah1's reader reads v36's games {V36G} ({sh(V36G)}; expected 298c5bc6a883) and v37's {V37G} ({sh(V37G)}; expected d3d2dd1303de), before any landing")
    X36 = file_side_(V36G) if sh(V36G) == "298c5bc6a883" else None; X37 = file_side_(V37G) if sh(V37G) == "d3d2dd1303de" else None
    H1 = {"candidate": ah1_(AA["record"], AA["engine"])}
    if X37 is not None: H1["v37 (the landed engine's games)"] = ah1_(AA["record"], X37)
    if X36 is not None: H1["v36"] = ah1_(AA["record"], X36)
    HN = {nm_: (sum(1 for v_ in h_.values() if v_[0] is True), sum(1 for v_ in h_.values() if v_[0] is not None)) for nm_, h_ in H1.items()}
    print("  ah1's reader, within 2SE of the record's (zone x distance x choice): " + " | ".join(f"{nm_} {a_} of {b_}" for nm_, (a_, b_) in HN.items()))
    AH1_PLANT_OK = None if ("v36" not in HN or "v37 (the landed engine's games)" not in HN) else bool(HN["v36"][0] < HN["v37 (the landed engine's games)"][0])
    print(f"  ah1's reader's plant (v36's games read fewer cells within than v37's): {'NOT MEASURED (a file not as pinned)' if AH1_PLANT_OK is None else ('PASS' if AH1_PLANT_OK else 'FAIL')}")
    print("  ai2: ah1's grid, the record | v37 | the candidate, go / field goal / punt, fourth downs (the six seasons' count) per cell:")
    for zl, lo, hi in ZON10:
        for dl, dlo, dhi in D4H:
            c_ = H1["candidate"]; r_ = c_[(zl, dl, "go")]
            if r_[3] == 0 and r_[4] == 0: continue
            v37_ = H1.get("v37 (the landed engine's games)", {})
            print(f"    {zl:15s} {dl:4s} record " + " / ".join(f"{c_[(zl, dl, ch)][1][0]:.3f}" for ch in ("go", "field_goal", "punt")) + f" (n {r_[3]})"
                  + (" | v37 " + " / ".join(f"{v37_[(zl, dl, ch)][2][0]:.3f}" for ch in ("go", "field_goal", "punt")) if v37_ else "")
                  + " | candidate " + " / ".join(f"{c_[(zl, dl, ch)][2][0]:.3f}{'' if c_[(zl, dl, ch)][0] else ('*' if c_[(zl, dl, ch)][0] is False else '?')}" for ch in ("go", "field_goal", "punt")) + f" (n {r_[4]}; * APART, ? NOT MEASURED)")
    def ai_cnt(cnt_, z_, d_, i_, ch_):
        return cnt_.get(f"ai: fourth-down choice at {z_} {d_} drawn at level {i_}: {ch_}", 0)
    Z10N = ("the 1", "2-3", "4-5", "6-10", "11-20", "opp 21-40", "the 41-50", "own 41-49", "own 21-40", "own 1-20")
    AISH = {}
    for nm_, cnt_, lv_ in (("landed", CNT_TD, LV4R), ("candidate", CNTM, LV4C)):
        for z_ in Z10N:
            n_ = sum(ai_cnt(cnt_, z_, "1", i_, ch_) for i_ in range(len(lv_)) for ch_ in ("go", "field_goal", "punt"))
            y_ = sum(ai_cnt(cnt_, z_, "1", i_, ch_) for i_, l_ in enumerate(lv_) if "distw" in l_ for ch_ in ("go", "field_goal", "punt"))
            AISH[(nm_, z_)] = (y_ / n_ if n_ else np.nan, n_)
    AI1_CHECK = all((not np.isnan(AISH[("candidate", z_)][0])) and AISH[("candidate", z_)][0] > (0.0 if np.isnan(AISH[("landed", z_)][0]) else AISH[("landed", z_)][0]) for z_ in Z10N)
    print("  ai1's check, the share of fourth-and-1 draws at a level keyed by the whole-yard distance, landed -> candidate (draws): " + " | ".join(
        f"{z_} {AISH[('landed', z_)][0]:.3f} -> {AISH[('candidate', z_)][0]:.3f} ({AISH[('candidate', z_)][1]})" for z_ in Z10N) + f" -> {'PASS (above at every zone)' if AI1_CHECK else 'FAIL'}")
    def case41(Rs, m_, s, n=2000):
        rng_ = np.random.default_rng([41, s]); c_ = Counter()
        k_ = dict(down=4, dist=m_.dist_bin(1), field=m_.field_bin(55), time=m_.time_bin(1, 600), score=m_.score_bin(0), ylw=55, dist4="1", ycell="51-60", distw="1")
        for _ in range(n): c_[Rs.P["call4"].draw(rng_, k_)["choice"]] += 1
        return c_
    mr_ = cell_(AA["record"], p4_(AA["record"]), 51, 59, 0, 1)
    AI_REC = w_mean((AA["record"]["choice"].to_numpy(object)[mr_] == "go").astype(float), AA["record"]["game_id"].to_numpy(object)[mr_])
    AIC = {}
    for nm_, f_ in (("candidate", lambda s: (R[s], e1n)), ("the landed engine", lambda s: (RATES_["read"][s], MODS_["read"])), ("ai1's plant (ag1's levels on the candidate's tables)", lambda s: (RATES_["aiplant"][s], MODS_["aiplant"]))):
        c_ = Counter()
        for s in S: c_.update(case41(*f_(s), s))
        n_ = sum(c_.values()); p_ = c_["go"] / n_; v_ = (p_, 2 * np.sqrt(p_ * (1 - p_) / n_), n_)
        ok_ = None if np.isnan(AI_REC[1]) else bool(abs(v_[0] - AI_REC[0]) <= np.sqrt(v_[1] ** 2 + AI_REC[1] ** 2)); AIC[nm_] = (v_, ok_)
        print(f"  ai1 case (4th and 1 at the own 45, first quarter, tied), {nm_}: go {p_:.3f} ±{v_[1]:.3f} | field goal {c_['field_goal'] / n_:.3f} | punt {c_['punt'] / n_:.3f} over {n_} draws -> {'within' if ok_ else ('APART' if ok_ is False else 'NOT MEASURED')}")
    print(f"  the record, the own 41-49 at 4th and 1: go {AI_REC[0]:.3f} ±{AI_REC[1]:.3f} (n {AI_REC[2]})")
    AI_CASE_OK = AIC["candidate"][1] is True; AI_PLANT_OK = AIC["ai1's plant (ag1's levels on the candidate's tables)"][1] is False; AI_PLANT_V = AIC["ai1's plant (ag1's levels on the candidate's tables)"][0][0]
    print("  ai2: punts (the pool's population) by the zone kicked from, the record beside the candidate; each zone's gap = more fourth downs + a higher punt share:")
    PTOT = {"gap": 0.0, "more": 0.0, "share": 0.0}; P4A = {nm: p4_(AA[nm]) for nm in AA}
    for zl, lo, hi in ZON10:
        m_ = {nm: P4A[nm] & (YL[nm] >= lo) & (YL[nm] <= hi) for nm in AA}
        F_ = {nm: pg_aa(m_[nm].astype(float), GI[nm], GAMES_AA[nm]) for nm in AA}; Pn_ = {nm: pg_aa((m_[nm] & (AA[nm]["choice"].to_numpy(object) == "punt")).astype(float), GI[nm], GAMES_AA[nm]) for nm in AA}
        p_ = {nm: (Pn_[nm][0] / F_[nm][0] if F_[nm][0] > 0 else np.nan) for nm in AA}
        g_ = Pn_["engine"][0] - Pn_["record"][0]; mo_ = (F_["engine"][0] - F_["record"][0]) * (0.0 if np.isnan(p_["record"]) else p_["record"]); sh__ = F_["engine"][0] * (0.0 if (np.isnan(p_["engine"]) or np.isnan(p_["record"])) else p_["engine"] - p_["record"])
        PTOT["gap"] += g_; PTOT["more"] += mo_; PTOT["share"] += sh__
        print(f"    {zl:15s} punts a game record {Pn_['record'][0]:.3f} candidate {Pn_['engine'][0]:.3f} | fourth downs a game record {F_['record'][0]:.3f} candidate {F_['engine'][0]:.3f} | the gap {g_:+.4f} = more fourth downs {mo_:+.4f} + a higher share {sh__:+.4f}")
    AI_SHARE_FR = PTOT["share"] / PTOT["gap"] if PTOT["gap"] else np.nan
    print(f"    summed: the gap {PTOT['gap']:+.4f} = more fourth downs {PTOT['more']:+.4f} + a higher punt share {PTOT['share']:+.4f} (summed {PTOT['more'] + PTOT['share']:+.4f}; the share's part {AI_SHARE_FR:.2f} of the gap)")
    print("  ai2: field goal tries (the pool's population) by the zone kicked from, the record beside the candidate:")
    FGS = 0.0
    for zl, lo, hi in ZON10:
        v_ = {nm: pg_aa((P4A[nm] & (YL[nm] >= lo) & (YL[nm] <= hi) & (AA[nm]["choice"].to_numpy(object) == "field_goal")).astype(float), GI[nm], GAMES_AA[nm]) for nm in AA}; FGS += v_["engine"][0] - v_["record"][0]
        print(f"    {zl:15s} tries a game record {v_['record'][0]:.3f} candidate {v_['engine'][0]:.3f} | the gap {v_['engine'][0] - v_['record'][0]:+.4f}")
    print(f"    the zones' gaps summed {FGS:+.4f}")
    mfu_ = {nm: P4A[nm] & (AA[nm]["choice"].to_numpy(object) == "field_goal") & (YL[nm] + 17 <= 29) for nm in AA}
    w_line("  ai2: the make share under 30 yards", *(w_mean((AA[nm]["field_goal_result"].to_numpy(object)[mfu_[nm]] == "made").astype(float), GI[nm][mfu_[nm]]) for nm in ("record", "engine")))
    print("  ai3 (a read, nothing built): drive progress outside the red zone by zone, the record beside the candidate (called plays with no foul):")
    Z5 = [("own 1-20", 80, 99), ("own 21-40", 60, 79), ("own 41-49", 51, 59), ("the 41-50", 41, 50), ("opponent 21-40", 21, 40)]
    for zl, lo, hi in Z5:
        for dn_, lab_ in ((1, "first-down gain"), (2, "second-down gain")):
            w_line(f"    {zl}: {lab_}", *(w_mean(YG[nm][PR[nm] & (DN[nm] == dn_) & (YL[nm] >= lo) & (YL[nm] <= hi)], GI[nm][PR[nm] & (DN[nm] == dn_) & (YL[nm] >= lo) & (YL[nm] <= hi)]) for nm in ("record", "engine")))
        for dl, dlo, dhi in D4H:
            m3_ = {nm: PR[nm] & (DN[nm] == 3) & (YL[nm] >= lo) & (YL[nm] <= hi) & (TG[nm] >= dlo) & (TG[nm] <= dhi) for nm in AA}
            w_line(f"    {zl}: third-down conversion at {dl}", *(w_mean((YG[nm][m3_[nm]] >= TG[nm][m3_[nm]]).astype(float), GI[nm][m3_[nm]]) for nm in ("record", "engine")))
    LVP = LV2(e1n); LVPR = LV2(MODS_["read"])
    print(f"  ai3: the snap outcome's levels (the candidate's, index: key) {[(i_, l_) for i_, l_ in enumerate(LVP)]}")
    for nm_, cnt_, lv_ in (("the landed engine", CNT_TD, LVPR), ("the candidate", CNTM, LVP)):
        for z_ in ("own 1-20", "own 21-40", "own 41-49", "the 41-50", "opp 21-40"):
            for d_ in (1, 2, 3):
                c_ = [cnt_.get(f"ai3: snap draw at {z_} down {d_} resolved at level {i2_}", 0) for i2_ in range(len(lv_))]; t_ = sum(c_)
                if t_: print(f"    {nm_}, {z_}, down {d_}: draws {t_} | by level " + " ".join(f"L{i_} {c__ / t_:.3f}" for i_, c__ in enumerate(c_) if c__))
    print("  (b) the 16-20 by yard line: snaps a game, the gain bins (a gain of 20 or more is possible only from the 20), the touchdown share:")
    for yl_ in range(16, 21):
        ml_ = {nm: PR[nm] & (YL[nm] == yl_) for nm in AA}
        w_line(f"    the {yl_}: snaps a game", *(pg_aa(ml_[nm].astype(float), GI[nm], GAMES_AA[nm]) for nm in ("record", "engine")))
        w_line(f"      the touchdown share at the {yl_}", *(w_mean((YG[nm][ml_[nm]] >= yl_).astype(float), GI[nm][ml_[nm]]) for nm in ("record", "engine")))
        for lab_, f_ in YB5:
            w_line(f"      gain {lab_}", *(w_mean(f_(YG[nm][ml_[nm]]).astype(float), GI[nm][ml_[nm]]) for nm in ("record", "engine")))
    s16_ = {nm: AA[nm]["snap"].to_numpy() & (YL[nm] >= 16) & (YL[nm] <= 20) & (AA[nm]["qtr"].to_numpy(float) <= 4) for nm in AA}
    print("  (c) field goal tries from the 16-20, the fourth-down call's link (aa; z4's cells), printed, not built here:")
    w_line("    the share of every 16-20 snap that is a field goal try", *(w_mean((AA[nm]["play_type"].to_numpy(object)[s16_[nm]] == "field_goal").astype(float), GI[nm][s16_[nm]]) for nm in ("record", "engine")))
    print("  z4's cells (the fourth-down call: every fourth-down snap, a foul included; drawn by the yard line since ag1, by the whole-yard distance first in the candidate; printed, not predicted):")
    def cells4(A, B, games_a, games_b):
        FA, FB = f4(A), f4(B); out_ = {}
        for zl, zf in ZB4:
            for dl, df_ in DB4:
                ma = FA[0] & df_(FA[1]) & zf(FA[2]); mb = FB[0] & df_(FB[1]) & zf(FB[2])
                for ch in ("go", "field_goal", "punt"):
                    out_[(zl, dl, ch)] = within(w_mean((FA[3][ma] == ch).astype(float), FA[4][ma]), w_mean((FB[3][mb] == ch).astype(float), FB[4][mb]))[2]
        return out_
    C48 = cells4(AA["record"], AA["engine"], GAMES_AA["record"], GAMES_AA["engine"])
    N48_IN = sum(1 for v_ in C48.values() if v_ is True); N48_M = sum(1 for v_ in C48.values() if v_ is not None)
    print(f"    within 2SE {N48_IN} of {N48_M} measured ({len(C48)} cells; y: 18 of 48) | APART: " + (", ".join(f"{k_[0]} {k_[1]} {k_[2]}" for k_, v_ in C48.items() if v_ is False) or "none"))
    section("ac2: the reads")
except (SystemExit, Overtime):
    raise
except Exception as ex_:
    import traceback; traceback.print_exc()
    stop(f"the chain raised {type(ex_).__name__}: {ex_}; the table and the working tables are saved; nothing else written")


TOT = time.time() - T0
if FIXTURE:
    H_PIN = (H_PLAY, H_FIT, "this run")
else:
    H_PIN = (None, None, "no quick run of this chain's sha with its evidence found")
    base_ = os.path.join("evidence", f"e2b_v38_{CSHA}")   # this chain's own quick runs
    for r_ in sorted(os.listdir(base_)) if os.path.isdir(base_) else []:
        mp_ = os.path.join(base_, r_, "manifest.json")
        if not (r_.endswith("_quick") and os.path.exists(mp_)): continue
        m_ = json.load(open(mp_))
        if m_.get("status") == "COMPLETE" and m_.get("chain", [None, None])[1] == CSHA: H_PIN = (m_["results"].get("h_play"), m_["results"].get("h_fit"), f"{mp_} (status {m_['status']})")
# the late-half snap hazard at 8-24 s after the play, the record's against the fitted race (held-out rows)
tbr_ = np.repeat(R23["tb2"].to_numpy(object), np.where(R23["cls"] == "boundary", R23["tau"], R23["tau"] + 1).astype(int))
mh_ = (tbr_ == "last 2:00 of the first half") & (np.minimum(tt, T_CAP) >= 8) & (np.minimum(tt, T_CAP) <= 24)
HZ_R = float(np.mean(yR[mh_] == "snap")) if mh_.any() else np.nan
HZ_F = float(np.mean(np.concatenate([MR[s].predict_proba(XR[mh_ & (sR == s)])[:, list(MR[s].classes_).index("snap")] for s in STAMPED if (mh_ & (sR == s)).any()]))) if mh_.any() else np.nan
HZ_N = int(mh_.sum()); HZ_SE = 2 * np.sqrt(HZ_R * (1 - HZ_R) / HZ_N) if HZ_N else np.nan
HZ_OK = within((HZ_R, HZ_SE, HZ_N), (HZ_F, 0.0, HZ_N))[2]   # y0 (a): no seconds at risk, or not a number: NOT MEASURED
m23_ = mh_ & (sR == 2023); n23_ = int(m23_.sum()); r23_ = float(np.mean(yR[m23_] == "snap")) if n23_ else np.nan; se23_ = 2 * np.sqrt(r23_ * (1 - r23_) / n23_) if n23_ else np.nan
f23_ = float(MR[2023].predict_proba(XR[m23_])[:, list(MR[2023].classes_).index("snap")].mean()) if n23_ else np.nan
p23_ = float(MR_PLANT.predict_proba(XR[m23_])[:, list(MR_PLANT.classes_).index("snap")].mean()) if n23_ else np.nan
HZ_PLANT_FAILS = None if (n23_ < 2 or np.isnan(p23_) or np.isnan(r23_) or np.isnan(se23_)) else bool(abs(p23_ - r23_) > se23_)   # y0 (a)
print("\n=== w1, w2: the race's snap hazard 8-24 s after the play in the last 2:00 of the first half, each season's rows scored by the race not fitted on it ===")
print(f"  every stamped season: record {HZ_R:.4f} ±{HZ_SE:.4f} (2SE, {HZ_N} seconds at risk) | fitted {HZ_F:.4f} (r: 0.0058) -> {wd(HZ_OK)}")
print(f"  2023 alone: record {r23_:.4f} ±{se23_:.4f} ({n23_}) | the race fitted on 2024-2025 {f23_:.4f} | the plant (the same fit, the time-left inputs shuffled across moments) {p23_:.4f}"
      f" -> the plant {'NOT MEASURED' if HZ_PLANT_FAILS is None else ('FAILS as it must' if HZ_PLANT_FAILS else 'DID NOT FAIL')}")
for tb_ in ("last 2:00 of the game",):
    mg_ = (tbr_ == tb_) & (np.minimum(tt, T_CAP) >= 8) & (np.minimum(tt, T_CAP) <= 24)
    if mg_.any():
        print(f"  {tb_} (printed): record {float(np.mean(yR[mg_] == 'snap')):.4f} ({int(mg_.sum())}) | fitted {float(np.mean(np.concatenate([MR[s].predict_proba(XR[mg_ & (sR == s)])[:, list(MR[s].classes_).index('snap')] for s in STAMPED if (mg_ & (sR == s)).any()]))):.4f}")
print(f"  the races' fits: " + " | ".join(f"{ho} iterations {MR[ho].iters} {'(converged)' if MR[ho].converged else '(NOT CONVERGED at 1000)'}" for ho in MR) + f" | the plant {MR_PLANT.iters}")
nUNS = len(UNSG)
import glob
AB_PR = os.path.join("evidence", "e2b_v37_37db486d756e", "20261031T011933Z_60773_full", "printout.txt")   # v37's landing run, by its path (the run this chain compares to)
AB_NAMES = ["games played", "unsupported games", "plays a game", "possessions a game", "charged timeouts a game", "points a game", "timing cells within 2SE", "section 4 on the record, failures"]


def ab_read(path, names):
    """each figure of v37's 'v19 m' block ('  <name>: <earlier run> <its value> [(line N)] | this run <v37's value>') with the line it was read from; only an absent file is NOT FOUND."""
    if not os.path.exists(path): return {n_: (None, f"NOT FOUND: file absent: {path}") for n_ in names}, ""
    tx_ = open(path, errors="replace").read(); out_ = {}
    for n_ in names:
        pat_ = r"^\s+" + re.escape(n_) + r": \S+ \S+(?: \([^)]*\))? \| this run (\S+?)(?:\s|$)"
        m_ = re.search(pat_, tx_, re.M)
        out_[n_] = (m_.group(1), f"line {tx_.count(chr(10), 0, m_.start()) + 1}") if m_ else (None, f"the read failed: the file is present, no line matches {pat_!r}")
    return out_, tx_


ABF, WTX = ab_read(AB_PR, AB_NAMES)
WPR = [AB_PR] if WTX else []
LAND_AB = [l_ for l_ in WTX.split("\n") if l_.startswith("  LANDED: ")]
print(f"\n=== v19 m: every figure beside v37's landing run, {AB_PR} (sha {sh(AB_PR)}) | its LANDED line: {LAND_AB[0][:170] if LAND_AB else ('the read failed: no line starts with LANDED:' if WTX else 'NOT FOUND: file absent')} ===")
_pd = tempfile.mkdtemp(); _pp = os.path.join(_pd, "printout.txt")
open(_pp, "w").write("\n".join(l_ for l_ in WTX.split("\n") if not re.match(r"^\s+plays a game: ", l_)))
ABP, _ = ab_read(_pp, AB_NAMES); shutil.rmtree(_pd)
_others = all(ABP[n_][0] == ABF[n_][0] for n_ in AB_NAMES if n_ != "plays a game")
AB_READ_PLANT = ABF["plays a game"][0] is not None and ABP["plays a game"][0] is None and ABP["plays a game"][1].startswith("the read failed") and _others
print(f"  the reader's plant (a copy of v37's printout with its 'plays a game' line removed): plays a game -> {ABP['plays a game'][1][:70]} | the other seven as read"
      f" from v37's file: {_others} -> {'FAILS as it must' if AB_READ_PLANT else ('VACUOUS (the figure is not on the file)' if ABF['plays a game'][0] is None else 'DID NOT FAIL')}")
GSHA = shs("".join(FRM[s].to_csv(index=False) for s in S))
RF = [("games played", nG_ALL), ("unsupported games", len(UNSG)), ("plays a game", round(TRI["plays"][2][0], 2)), ("possessions a game", round(TRI["possessions"][2][0], 2)),
      ("charged timeouts a game", round(VALL["model"][0], 2)), ("points a game", round(TRI["points"][2][0], 2)), ("timing cells within 2SE", TIM_N[0]),
      ("section 4 on the record, failures", SEC4_REC["STOP_failed"])]
for nm_, b_ in RF:
    a_, w_ = ABF.get(nm_, (None, "not among the names read"))
    print(f"  {nm_}: v37 {a_ if a_ is not None else '-'} ({w_}) | this run {b_}{'  <- moved' if (a_ is not None and str(a_) != str(b_)) else ''}")
m_ = re.search(r"the engine's games \(every season, as text\) sha (\w+)", WTX)
print(f"  the engine's games (every season, as text) sha {GSHA} (v37: {m_.group(1) if m_ else 'NOT FOUND'})")
def w_gap(lab_):
    m_ = re.search(re.escape(lab_) + r": record ([\d.]+) ±[\d.]+ \(n \d+\) \| engine ([\d.]+)", WTX); return (float(m_.group(1)) - float(m_.group(2))) if m_ else None
W_GAPS = {"fixed_drive": w_gap("by fixed_drive (u's)"), "r1.possessions": w_gap("by r1.possessions (v's; count_side's)")}
print(f"  v37's possessions gaps (record less engine), read from its printout: {W_GAPS}")

print("\n=== the predictions (ai), each scored against this run: HELD, NOT HELD or NOT MEASURED (y0 a); y's figures printed beside, not predicted ===")
L0F = ("r1.py", "r2.py", "r4.py", "record.py", "rules.py", "contract.py", "r7.py", "l0.py")
L0_OK = all(sh(p_) == PIN[p_] for p_ in L0F)
NPLAYED = len(sched[sched["season"].isin(S)])
GAPS_Y = {"fixed_drive": (-PFD[0], PFD[2]), "r1.possessions": (-PR1[0], PR1[2])}
PRED = {}
PRED["ai0 (b): 4th and 1 shares a bin with 2-3 at the first levels (read)"] = (f"dist_bin(1) {e1n.dist_bin(1)!r}, dist_bin(2) {e1n.dist_bin(2)!r}", AI_SHARES_BIN)
Z5U = ("opponent 21-40", "the 41-50", "own 41-49", "own 21-40", "own 1-20")
for dl_ in ("1", "2-3"):
    w5_ = [H1["candidate"][(z_, dl_, "go")][0] for z_ in Z5U]; w11_ = H1["candidate"][("11-20", dl_, "go")][0]
    PRED[f"after ai1 the go share at 4th and {dl_} within 2SE in at least 4 of the 5 zones above the 11-20, and in the 11-20"] = (
        f"within in {sum(1 for v_ in w5_ if v_ is True)} of 5 ({', '.join(f'{z_} {wd(v_)}' for z_, v_ in zip(Z5U, w5_))}) | the 11-20 {wd(w11_)}", (sum(1 for v_ in w5_ if v_ is True) >= 4 and w11_ is True))
PRED["the punt share's part of the punt gap below 0.2 (ah2 0.29 on v37)"] = (f"{AI_SHARE_FR:.2f} of {PTOT['gap']:+.4f}", None if np.isnan(AI_SHARE_FR) else bool(AI_SHARE_FR < 0.2))
PRED["plays a game within 2SE of the record's 136.73 (v37 136.60)"] = (f"engine {TRI['plays'][2][0]:.2f} ±{TRI['plays'][2][1]:.2f} | record {TRI['plays'][0][0]:.2f} ±{TRI['plays'][0][1]:.2f}", within(TRI["plays"][0], TRI["plays"][2])[2])
for k_, (v_, ok_) in PRED.items(): print(f"  {k_}: {v_} -> {hv(ok_)}{' (a quick run: the fixture games)' if FIXTURE else ''}")
print(f"  points a game (no size, printed): engine {PTS_ENG:.2f} | record {PTS_SIDE['record'][0]:.2f} | v37 41.08")
print(f"  ad0 (b)'s plant: {'FAILS as it must' if AD0_PLANT else 'DID NOT FAIL or NOT MEASURED'} | ad1's plant on the case: {'APART as it must' if AD1_PLANT else 'NOT APART'} | ad addition 2's replay: retired as VACUOUS (the grid {len(GRID_C)} and {len(GRID_P)}) | the v37 reader's plant: {'FAILS as it must' if AB_READ_PLANT else 'DID NOT FAIL or VACUOUS'} (printed: ad adds no gate)")
print(f"  y's figures (printed, not predicted here): snap to snap after a foul outside the windows {W_WHY[Y_F][0]:+.3f} ±{W_WHY[Y_F][1]:.3f} -> {wd(W_WHY[Y_F][2])} | PARTIAL {W_CLS['PARTIAL'][0]:+.3f} ±{W_CLS['PARTIAL'][1]:.3f}"
      f" -> {wd(W_CLS['PARTIAL'][2])} | possessions gaps {GAPS_Y} (y's {W_GAPS}) | restarts over the play clock {Y1N[0]} of {Y1N[1]}")
Y_WITHIN = {m_.group(1).strip(): m_.group(2) for m_ in re.finditer(r"^\s+(.+?): record [-\d.]+ ±[\d.na]+ \(n \d+\) \| engine .*?-> (within|APART|NOT MEASURED)", WTX, re.M)}
MOVED_ = [(k_, wd(VERD[k_])) for k_, v_ in Y_WITHIN.items() if v_ == "within" and k_ in VERD and VERD[k_] is False]
print(f"  the figures within 2SE at v37 ({AB_PR}: {len([v_ for v_ in Y_WITHIN.values() if v_ == 'within'])} 'within' lines of {len(Y_WITHIN)} read; {len([k_ for k_ in Y_WITHIN if k_ in VERD])} re-measured here) that moved outside it: "
      + (", ".join(f"{k_} ({v_})" for k_, v_ in MOVED_) if MOVED_ else "none") + " (printed as a list, not a gate)")
ABM = re.search(r"that moved outside it: (.*?) \(printed as a list, not a gate\)", WTX)
print(f"  v37's own movers, read from {AB_PR} (chain 37db486d756e, printout sha {sh(AB_PR)}): {ABM.group(1) if ABM else ('the read failed: no line matches the movers pattern' if WTX else 'NOT FOUND: file absent')}"
      f" | this run's: " + (", ".join(f"{k_} ({v_})" for k_, v_ in MOVED_) if MOVED_ else "none"))
print(f"  y, no size predicted: plays a game {TRI['plays'][2][0]:.2f} (record {TRI['plays'][0][0]:.2f}) | possessions {TRI['possessions'][2][0]:.2f} (record {TRI['possessions'][0][0]:.2f})"
      f" | points {TRI['points'][2][0]:.2f} (record {TRI['points'][0][0]:.2f})")
YCHK = {"y0 (a): the plant (a check fed a NaN) prints NOT MEASURED": Y0A_PLANT, "y1: the case on the candidate (wiped and before the snap)": Y1_CASE_OK,
        "y1: the plant fails the case": Y1_PLANT_CASE,
        "y0 (b): each played season's play clock after an enforcement read from its book": all(v_[0] is not None for v_ in ENF_CLOCK.values())}
YCHK["y: every worker's results and every reused working table name only the modules the product's model files load and this chain's library"] = (all(not b_ for _, _, b_ in MODCHK) if MODCHK else None)
YCHK["y: the module check's plant (an e2b_v24_lib object packed two deep) refused"] = "e2b_v24_lib" in MOD_PLANT
print(f"  y: the module check (allowed: {sorted(MOD_OK)}), {len(MODCHK)} reads; not allowed found in {sum(1 for _, _, b_ in MODCHK if b_)}; its plant named {sorted(MOD_PLANT)}:")
for w_, a_, b_ in MODCHK: print(f"    {w_}: names {a_} | not allowed {b_ or 'none'}")
print("  y's checks (printed beside the landing checks, which are w's, unchanged):")
for k_, v_ in YCHK.items(): print(f"    {k_}: {'NOT MEASURED' if v_ is None else ('PASS' if v_ else 'FAIL')}")

print("\n=== the landing (the spine: transition.py, e1.py, out/engine/, out/sim_games.csv and out/e1_checks.csv land in this run when their own checks pass) ===")
DONE_FAIL = [f"{k_} ({DONE_NUM[k_]})" for k_, v_ in done.items() if not v_]
LAND_CHECKS = {"transition.py's known-right cases, yards cases and plants": (bool(TRANS_OK), "the transition's cases and plants as printed in e"),
               "section 4 on the engine, every DONE WHEN item true": (bool(SEC4), "; ".join(DONE_FAIL) or "every item true"),
               "P1-P4 failing as they must, none VACUOUS": (bool(PLANTS_OK), str(res)), "leak tests 1-3": (bool(LEAK2 and LEAK3), f"1 and 2 {LEAK2}, 3 {LEAK3}"),
               "the record's section 4 not above 1,213 (the no-rise gate)": (bool(NORISE), f"{SEC4_REC['STOP_failed']}"),
               "L0's product files unchanged": (bool(L0_OK), "as printed in the predictions"),
               "this chain's quick run byte-identical to serial (games and fits)": (H_PIN[0] is True and H_PIN[1] is True, f"games {H_PIN[0]}, fits {H_PIN[1]} ({H_PIN[2]})"),
               "w1: the plant (the time-left inputs shuffled) fails the late-half hazard": (bool(HZ_PLANT_FAILS), f"plant {p23_:.4f} against the record's 2023 {r23_:.4f} ±{se23_:.4f}"),
               "q: e1.py alone plays the quick-run games byte-identical to this run's": (bool(E1_ALONE), (str(al_cmp) if al_cmp else f"e1.py alone exit {AL_OUT[0]}") + f"; the sha check's plant {'refused' if AL_PLANT else 'NOT REFUSED'}"),
               "ab1: the case (first and 10 at the 18: the six seasons' 12,000 draws pooled, the share of 15+ within 2SE of the record's at the 18; af addition item 1)": (bool(AB_CASE_OK), f"pooled {POOLED_V['candidate'][0][0]:.4f} ±{POOLED_V['candidate'][0][1]:.4f} | the record at the 18 {REC_CASE[0]:.4f} ±{REC_CASE[1]:.4f} | the 16-20 cell beside {REC_CELL[0]:.4f}"),
               "ab1: today's pool (the pool before ab, the field cells alone) APART on the same pooled test": (bool(AB_TODAY_APART), f"{POOLED_V['today (the pool before ab)'][0][0]:.4f} ±{POOLED_V['today (the pool before ab)'][0][1]:.4f}"),
               "ab1: the plant (the yard line shuffled among the snaps inside the 20) fails the pooled case": (bool(AB_PLANT_CASE), f"{POOLED_V["ab's plant"][0][0]:.4f} ±{POOLED_V["ab's plant"][0][1]:.4f}"),
               "ac1 (ad0 (a)): the candidate's in-game draws inside the 20, inside the 1 included, reaching a keyless level below 0.02": (bool(AC1_CHECK), f"{AC1_SHARE:.4f} every season, 2024 {AC1_SHARE_24:.4f} (the landed engine: every season {AC0_SHARE:.4f}, 2024 {AC0_SHARE_24:.4f})"),
               "ac1: the plant (the field cell below the yard-line level) APART on the 16-20 touchdown share where the candidate is within (2024)": (bool(AC_PLANT_OK), f"record {TD24['record'][0]:.4f} | candidate {TD24['candidate'][0]:.4f} -> {wd(AC_PL_C)} | plant {TD24['plant'][0]:.4f} -> {wd(AC_PL_P)}"),   # v35: ac0's gate removed ('### v19 ad addition' item 1)
               "af1: the plant (the landed order on the candidate's tables) APART on the 3's touchdown share where the candidate is within (2024)": (bool(AF_PLANT_OK), f"record {TD3['record'][0]:.4f} | candidate {TD3['candidate'][0]:.4f} -> {wd(AF_PL_C)} | plant {TD3['plant'][0]:.4f} -> {wd(AF_PL_P)}"),
               "ag1: the case (4th and 7 at the 45: the punt share above the field goal share by at least the record's margin in the 41-50 at 7+)": (bool(AG_CASE_OK), f"candidate {AGC['candidate'][0]:+.3f} against the record's {REC_MARGIN:+.3f}"),
               "ag1: the plant (the levels before ag1, FULL, on the candidate's tables) fails the case": (bool(AG_PLANT_OK), f"plant {AG_PLANT_M:+.3f} against the record's {REC_MARGIN:+.3f}"),
               "ai0 (a): ah1's reader's plant (v36's games read fewer cells within than v37's)": (bool(AH1_PLANT_OK), " | ".join(f"{nm_} {a_} of {b_}" for nm_, (a_, b_) in HN.items())),
               "ai0 (b): ai is built (4th and 1 shares a bin with 2-3 at the landed first levels)": (bool(AI_BUILD), f"dist_bin(1) {e1n.dist_bin(1)!r}, dist_bin(2) {e1n.dist_bin(2)!r}"),
               "ai1: the share of fourth-and-1 draws at a level keyed by the whole-yard distance above the landed engine's at every zone": (bool(AI1_CHECK), " | ".join(f"{z_} {AISH[('candidate', z_)][0]:.3f}" for z_ in Z10N)),
               "ai1: the case (4th and 1 at the own 45: the go share within 2SE of the record's own 41-49 at 1)": (bool(AI_CASE_OK), f"candidate {AIC['candidate'][0][0]:.3f} ±{AIC['candidate'][0][1]:.3f} | the record {AI_REC[0]:.3f} ±{AI_REC[1]:.3f}"),
               "ai1: the plant (ag1's levels on the candidate's tables) APART on the case": (bool(AI_PLANT_OK), f"plant {AI_PLANT_V:.3f} against the record's {AI_REC[0]:.3f}")}
for k_, (v_, n_) in LAND_CHECKS.items(): print(f"  {k_}: {'PASS' if v_ else 'FAIL'} | {n_}")
print(f"  section 4's DONE WHEN items failing: {DONE_FAIL or 'none'} | quick run evidence read: {H_PIN[2]}")
FAILING = [f"{k_} ({n_})" for k_, (v_, n_) in LAND_CHECKS.items() if not v_]
if FIXTURE: LANDED = "NOT LANDED: a quick run does not land" + (" (and these fail: " + "; ".join(FAILING) + ")" if FAILING else "")
elif FAILING: LANDED = "NOT LANDED: failing " + "; ".join(FAILING)
else:
    rp_ = os.path.join(EVD, "replaced"); os.makedirs(rp_, exist_ok=True)
    for f_ in ("transition.py", "test_transition.py", "e1.py"): shutil.copy(f_, os.path.join(rp_, f_))
    if os.path.isdir("out/engine"):   # the model files the previous e1.py read (none before r): kept beside the replaced files, then removed from out/engine/
        os.makedirs(os.path.join(rp_, "engine"), exist_ok=True)
        for f_ in os.listdir("out/engine"): shutil.copy(os.path.join("out/engine", f_), os.path.join(rp_, "engine", f_)); os.remove(os.path.join("out/engine", f_))
    old_ = {f_: sh(os.path.join(rp_, f_)) for f_ in ("transition.py", "test_transition.py", "e1.py")}
    for f_, tx_ in (("transition.py", TRANS_CAND), ("test_transition.py", TEST_CAND), ("e1.py", E1N)):
        if sh(f_) != shs(tx_): open(f_, "w").write(tx_)   # v19 w, y: a file whose text this chain does not change is left as it is
    os.makedirs("out/engine", exist_ok=True)
    for f_ in os.listdir(STAGE): shutil.copy(os.path.join(STAGE, f_), os.path.join("out/engine", f_))
    # v19 s6: the engine's games and section 4's counts, written from the games this run played with the candidate e1.py, stamped with its sha
    for f_ in ("out/sim_games.csv", "out/e1_checks.csv"): shutil.copy(f_, os.path.join(rp_, os.path.basename(f_)))
    STAMP_S6 = (f"# e1.py {shs(E1N)} | E1_TARGETS.md {sh('E1_TARGETS.md')} | rules.py {sh('rules.py')} | rules/RULE_PINS.json {sh('rules/RULE_PINS.json')}"
                f" | out/r7_seasons.csv {sh('out/r7_seasons.csv')} | seed {e1n.SEED} | the snap outcome inside the 20 by yards to the goal, the key kept through the merge (ab1, ac1, ad1, af1, ag1, ai1) | engine games (E2b v19 ai chain {CSHA}, the landed e1.py's games as this run played them), not the record")
    with open("out/sim_games.csv", "w") as f_:
        f_.write(STAMP_S6 + "\n"); pd.concat([FRM[s] for s in S], ignore_index=True).to_csv(f_, index=False)
    CHK_ROWS = [("section 4", k_, v_) for k_, v_ in sorted(w4.items())] + [("section 4", "r1 possessions", C1["possessions"]), ("section 4", "r1 games", C1["games"]),
                ("section 4", "r1 unexplained", len(left1))] + [("section 4", k_, v_) for k_, v_ in sorted(CK.items())] + [("section 4", k_, v_) for k_, v_ in sorted(PO.items())] \
               + [("DONE WHEN", k_, int(bool(v_))) for k_, v_ in done.items()] + [("plants", k_, int(bool(v_))) for k_, v_ in sorted(res.items())] \
               + [("games", "played", nG_ALL), ("games", "not played", sum(SKM.values())), ("games", "with an unsupported continuation", len(UNSG)), ("games", "unsupported continuations", N_UNS)]
    with open("out/e1_checks.csv", "w") as f_:
        f_.write(STAMP_S6 + "\n"); pd.DataFrame(CHK_ROWS, columns=["section", "check", "count"]).to_csv(f_, index=False)
    S6_SH = {f_: sh(f_) for f_ in ("out/sim_games.csv", "out/e1_checks.csv", "out/r7_seasons.csv")}
    new_ = {"transition.py": shs(TRANS_CAND), "test_transition.py": shs(TEST_CAND), "e1.py": shs(E1N)}
    bad_ = [f_ for f_, v_ in new_.items() if sh(f_) != v_] + [f"out/engine/{f_}" for f_, v_ in MANIF["files"].items() if sh(os.path.join("out/engine", f_)) != v_]
    LANDED = ("NOT LANDED: a written file is not its text: " + str(bad_)) if bad_ else ("LANDED: " + " | ".join(f"{f_} {old_[f_]} -> {sh(f_)}" for f_ in new_)
                                                                                       + f" | out/engine/ {len(MANIF['files'])} model files, MANIFEST.json {sh('out/engine/MANIFEST.json')}"
                                                                                       + f" | s6: out/sim_games.csv {S6_SH['out/sim_games.csv']} and out/e1_checks.csv {S6_SH['out/e1_checks.csv']} written by e1.py {shs(E1N)};"
                                                                                       + f" out/r7_seasons.csv {S6_SH['out/r7_seasons.csv']} (r7.py's record read, unchanged: {'yes' if S6_SH['out/r7_seasons.csv'] == '1d3606b8c099' else 'NO'})"
                                                                                       + f" (the previous versions in {rp_})")
print(f"  {LANDED}")
if LANDED.startswith("LANDED"):
    print("  declared: e1.py run alone reads its season values and models from out/engine/ (engine_load checks each file's sha against MANIFEST.json;")
    print("  e1.alone_main plays the games). s6: out/sim_games.csv and out/e1_checks.csv are this run's games and section 4's counts from the landed e1.py,")
    print(f"  stamped with its sha {shs(E1N)}; out/r7_seasons.csv is r7.py's read of the record, not e1.py's, left as it is.")
GATES = {"section 4 on the engine: every DONE WHEN item": SEC4, "q: e1.py alone byte-identical": E1_ALONE, "section 4 on the record: the no-rise gate": NORISE, "LANDED": LANDED.startswith("LANDED"), "P1-P4 fail as they must (none VACUOUS)": PLANTS_OK, "leak tests 1-3 pass": bool(LEAK2 and LEAK3),
         "parallel byte-identical to serial (the quick run's games and fits)": H_PIN[0] is True and H_PIN[1] is True, "the shared parse equal to separate parses": bool(H_SHARED),
         "both calibration plants fail": bool(CALR[(True, "race")][2] and CALR[(True, "stopped")][2]), "the ceiling plant refused": bool(PCAP),
         "FULL-GAME ACCEPTANCE: no unsupported continuation drawn in any game": nUNS == 0, **{k_: v_ for k_, v_ in YCHK.items()}}
print(f"  the gates (each printed, None NOT MEASURED; what this run did: {LANDED.split(' (the previous')[0][:160]}): {GATES}")
print(f"\n=== FIVE RESULTS, printed separately ===")
print(f"  1 MEASUREMENT (record side, kept from v16): section 4 on the record {share(SEC4_REC['STOP_failed'], SEC4_REC['STOP_checked'])} of stamped STOP stretches, no stopping event"
      f" {SEC4_REC['no_stop_event']}; the identity and f's clock offset not rerun here (v16's kept); the offset stays out of the engine")
print(f"  2 CONSTRUCTION: the transition's cases {'pass, its plants fail' if TRANS_OK else 'FAIL'}; v14's rebuild against this one: regressions {len(reg_u)}; section 4 on the engine"
      f" {'met' if SEC4 else 'NOT MET: ' + '; '.join(DONE_FAIL)} (stopped-clock failures {len(OWN)}, none exempted); P1-P4 {res}; leak tests {'PASS' if (LEAK2 and LEAK3) else 'FAIL'}; F1/F2 a game within 2SE {P_OK};"
      f" downs whose play a foul wiped a game record {WIP[0][0]:.3f} | model {WIP[1][0]:.3f}")
print(f"  3 LOCAL TIMING: timing cells {TIM_N[0]} of {TIM_N[1]}; calibration race {CALR[(False, 'race')][0]} missed (allowed {CALR[(False, 'race')][1]:.1f}), stopped"
      f" {CALR[(False, 'stopped')][0]} missed (allowed {CALR[(False, 'stopped')][1]:.1f}); the late-half hazard 8-24 s fitted {HZ_F:.4f} | record {HZ_R:.4f}")
print(f"  4 DOWNSTREAM (record / floor / model, every game; {share(nG_ALL - nUNS, nG_ALL)} of the model's games supported): plays {TRI['plays'][0][0]:.2f} / {TRI['plays'][1][0]:.2f} /"
      f" {TRI['plays'][2][0]:.2f} | possessions {TRI['possessions'][0][0]:.2f} / {TRI['possessions'][1][0]:.2f} / {TRI['possessions'][2][0]:.2f} | charged timeouts {VALL['record'][0]:.2f} /"
      f" {VALL['floor'][0]:.2f} / {VALL['model'][0]:.2f} | points {TRI['points'][0][0]:.2f} / {TRI['points'][1][0]:.2f} / {TRI['points'][2][0]:.2f} | unsupported continuations"
      f" {N_UNS} ({N_UNS / max(nG_ALL, 1):.3f} a game) in {nUNS} games; full-game acceptance {'open' if not nUNS else 'BLOCKED'}")
print(f"  5 RUNTIME: {TOT:.0f} s before the evidence (budget {BUDGET} s, enforced) | workers {NW} of {NCPU} cores | parallel against serial (the quick run): games {H_PIN[0]}, fits {H_PIN[1]}"
      f" ({H_PIN[2]}) | working tables: " + " | ".join(f"{n_} {st_} ({sha_})" for n_, k_, st_, sha_ in CACHE_LOG if not n_.startswith("book_")))
print(f"  the tally: PROGRESS.md {sh('PROGRESS.md')} (pinned 811fddf2ab32) -> {'unchanged' if sh('PROGRESS.md') == '811fddf2ab32' else 'CHANGED'}")
MANIFEST = ["start: pins and targets", "pins: books read", "pins: plants, the pin checks, the articles", "c: Rule 11 Section 6 read",
            "table: the record loaded (six seasons, with the rebuild's columns)", "table: clock state after each act", "table: the state after each row, rebuilt",
            "e: the next-snap check", "c: the foul-related rows sorted", "e: the transition and the rebuild comparison", "table: the warning and 0:00 placed",
            "table: the three times", "table: saved, reloaded, plant", "table: coverage", "table checks", "c: the race's and the stopped part's rows", "section 4 on the record",
            "record counted (count_side)", "engine: built, its pools", "the floor played and counted", "race: the stopped part and the race fitted", "construction: leak tests",
            "race: validation", "model engine: played", "model engine: counted", "validation: timing percentiles", "checks: p, f, e, h", "game figures: record | floor | model",
            "E1 section 4", "E1 plants P1-P4", "v19 o, c, d, k: the books searched; k's record check",
            "y0 (b), y1: Rule 4's articles printed whole", "y2, y1: possessions, seconds, the clock read; the case and the plant",
            "ac0, ab1: the pool read, the record inside the 20, the cases", "ac2: the reads"]
missing = [m_ for m_ in MANIFEST if m_ not in PRINTED]
print(f"\n=== the section manifest: {len(MANIFEST)} required, {len(MANIFEST) - len(missing)} printed | missing: {missing if missing else 'none'} ===")
print("\n=== timing, every section ===")
for nm, v in SECT: print(f"  {nm}: {v:.1f} s")
STATE["results"].update(h_play=H_PLAY if FIXTURE else None, h_fit=H_FIT if FIXTURE else None, section4=SEC4, failures=len(OWN), unsupported_games=nUNS, games=nG_ALL,
                        timing=list(TIM_N), plays=TRI["plays"][2][0], possessions=TRI["possessions"][2][0], timeouts=VALL["model"][0], points=TRI["points"][2][0], table=TSHA, missing=missing,
                        gates={k_: (None if v_ is None else bool(v_)) for k_, v_ in GATES.items()}, predictions={k_: ok_ for k_, (_, ok_) in PRED.items()},
                        line=(f"{'quick run' if FIXTURE else ('full run, cold' if COLD else 'full run')} | {TABLE_VERSION} {TSHA} | {LANDED.split(' (the previous')[0]} | record section 4 {SEC4_REC['STOP_failed']} | games {GSHA} | section 4 engine {'met' if SEC4 else 'NOT MET: ' + '; '.join(DONE_FAIL)} | e1 alone {'byte-identical' if E1_ALONE else 'NOT IDENTICAL'} | unsupported games"
                              f" {share(nUNS, nG_ALL)} | timing {TIM_N[0]}/{TIM_N[1]} | y: foul {wd(W_WHY[Y_F][2])}, PARTIAL {wd(W_CLS['PARTIAL'][2])}, over the play clock {Y1N[0]} | plays {TRI['plays'][2][0]:.2f} | possessions {TRI['possessions'][2][0]:.2f} | timeouts {VALL['model'][0]:.2f}"
                              f" | points {TRI['points'][2][0]:.2f} | {TOT:.0f} s | PROGRESS.md unchanged"))
STATE.update(status="COMPLETE" if not missing else "STOPPED", reason="" if not missing else f"sections missing: {missing}")

