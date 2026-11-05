"""E2b v19 aa's shared code (module e2b_v29_lib): one module for this process and every worker process, written out by the chain and imported by both: the counting function,
the estimators and the workers; the one transition (transition.py) and section 4's check (clock_check.py) are the product files it imports."""
import os, re, sys, io, time, json, pickle, hashlib, tempfile, shutil, threading, importlib.util
from collections import Counter, defaultdict
import numpy as np, pandas as pd
import record, contract, rules, r1, r2, r4, e1
from rules import next_down, next_possession
S = list(e1.SIM_SEASONS)
WARN_SEC = {}
RUNOFF_RESTART = {}
T_CAP = 40   # the pinned play clock (4-6-1), configured by the chain from rules/play_clock_pins.tsv
ENGINE_CONF = {}   # v19 part 2: the engine's module values its caller sets (PACE_SPLIT, RUNOFF_RESTART, SCRIM_TB, BOOKY), the same in every process
SCRIM_TB = {}   # season -> (the yard line a touchback that is not a free kick puts the ball in play on, the place it was read) | (None, why): Rule 11 Section 6
shs = lambda t: hashlib.sha256(t.encode()).hexdigest()[:12]
shb = lambda b: hashlib.sha256(b).hexdigest()[:12]


def configure(**kw):
    globals().update(kw)


def nanv(x):
    return x is None or (not isinstance(x, str) and pd.isna(x))


def one_(x):
    return (not nanv(x)) and x == 1


class SharedParse:
    """Inside the block, e1.load, r1.load, r2.load and r4.load each parse a season once per record.raw_frame and hand out copies."""
    def __enter__(self):
        self.saved = {}; self.memo = {}
        for mod, nm in ((e1, "load"), (r1, "load"), (r2, "load"), (r4, "load")):
            f = getattr(mod, nm); self.saved[(mod, nm)] = f
            def wrap(s, f=f, key=mod.__name__):
                k = (key, id(record.raw_frame), s)
                if k not in self.memo: self.memo[k] = f(s)
                v = self.memo[k]
                return tuple(x.copy() if isinstance(x, pd.DataFrame) else x for x in v) if isinstance(v, tuple) else v.copy()
            setattr(mod, nm, wrap)
        return self

    def __exit__(self, *a):
        for (mod, nm), f in self.saved.items(): setattr(mod, nm, f)


def gse2(v, g):
    """2SE of a mean, taken by game (games are the unit)."""
    v = np.asarray(v, float); g = np.asarray(g); n_ = len(v)
    if n_ < 2: return np.nan
    m = v.mean(); s_ = pd.Series((v - m) / n_).groupby(g).sum(); G = len(s_)
    return 2 * np.sqrt((s_ ** 2).sum() * G / (G - 1)) if G > 1 else np.nan


def share(k, n, nd=4):
    """A share over 0 rows is not a number."""
    return "NOT MEASURED (0 rows)" if not n else f"{k / n:.{nd}f} ({int(k)} of {int(n)})"


def per(k, n, unit):
    """A rate over its own population, the population named (d: every rate divides by its own population)."""
    return f"NOT MEASURED (0 {unit})" if not n else f"{k / n:.3f} a {unit[:-1] if unit.endswith('s') else unit} ({int(k)} over {int(n)} {unit})"


def plant_verdict(n_targets, failed):
    """d: a plant with nothing to plant into is VACUOUS, never 'did not fail'."""
    return "VACUOUS (nothing to plant into)" if not n_targets else ("FAILS as it must" if failed else "DID NOT FAIL")





# ---------------- the product files: the one transition (transition.py) and section 4's check (clock_check.py), imported from the project folder ----------------
# The library no longer carries its own copies: the record's rebuild, the engine (every worker) and section 4 call the landed files; their shas are in LIBSHA.
import transition as T, clock_check as CC
from transition import (TPARTS, series, kick_to_come, unknown, same, int_end, punt_end, kick_end, second, after, after_one, FIXTURES, run_fixtures, planted,
                        PLANTS, STAND_PLANTS, planted_stand, enforced_at, STAND_PREFIX, foul_yards, spot_foul_yards,
                        run_yard_cases, YARD_PLANTS, goal_half)
from clock_check import injury_text, _InjRead, down_row, STOP_AT_PLAY, warn_place, RUNOFF_RX, INJ_RX, INJ_UPD_RX


def tb_rules(season, x6cell):
    """transition.tb_rules with the Rule 11 Section 6 spots the chain read (SCRIM_TB, configured in every process)."""
    return T.tb_rules(season, x6cell, SCRIM_TB)


def check_clock2(seasons, keep_rows=False):
    """clock_check.check_clock2 with the warning's sections the chain read (WARN_SEC, configured in every process; a label only)."""
    return CC.check_clock2(seasons, keep_rows, WARN_SEC)

# ---------------- E2a: the shared counting function (one code, both sides) ----------------
SNAPK = set(rules.SNAP_KINDS)
OWN_FOULS = ("False Start", "Defensive Offside", "Offensive Holding", "Defensive Holding", "Intentional Grounding", "Unsportsmanlike Conduct")
KINDS = {"offensive touchdown": "pts_off_td", "kickers' touchdown": "pts_kick_td", "return touchdown": "pts_ret_td", "defensive touchdown": "pts_def_td",
         "field goal": "pts_fg", "try, kick": "pts_try_kick", "try, two-point": "pts_try_two", "try, defensive return": "pts_def_try", "safety": "pts_safety"}
FAILP, BACK, SIDE, PLANT_X, PLANT_KIND = [], [], ["record"], [None], ["return touchdown"]


def credit(x, double=None):
    """E2a v3 a: one kind per score, decided by who scored on which play."""
    n = len(x); kind = [""] * n; hp = np.zeros(n); ap = np.zeros(n); home = x["home_team"].iloc[0]
    for i in range(n):
        pt = x.at[i, "play_type"]; tt = x.at[i, "td_team"]; pos = x.at[i, "posteam"]; dfn = x.at[i, "defteam"]; k = None
        if one_(x.at[i, "touchdown"]) and isinstance(tt, str):
            if pt in ("kickoff", "punt"):
                recv, kick = (pos, dfn) if pt == "kickoff" else (dfn, pos)
                k = "return touchdown" if tt == recv else ("kickers' touchdown" if tt == kick else f"touchdown on a {pt} by a team not on the field")
            elif pt in SNAPK: k = "offensive touchdown" if tt == pos else "defensive touchdown"
            else: k = f"touchdown on a {pt} row"
            who, p = tt, 6
        elif pt == "field_goal" and x.at[i, "field_goal_result"] == "made": k, who, p = "field goal", pos, 3
        elif pt == "extra_point" and x.at[i, "extra_point_result"] == "good": k, who, p = "try, kick", pos, 1
        elif one_(x.at[i, "two_point_attempt"]) and x.at[i, "two_point_conv_result"] == "success": k, who, p = "try, two-point", pos, 2
        elif one_(x.at[i, "defensive_two_point_conv"]) or one_(x.at[i, "defensive_extra_point_conv"]): k, who, p = "try, defensive return", dfn, 2
        elif one_(x.at[i, "safety"]):
            k, p = "safety", 2
            who = pos if (pt == "punt" and re.search(r"punts -?\d+ yards", str(x.at[i, "desc"])) and "BLOCKED" not in str(x.at[i, "desc"]).upper()) else dfn
        if k:
            kind[i] = k
            if who == home: hp[i] += p
            else: ap[i] += p
            if double == i:
                if who == home: hp[i] += p
                else: ap[i] += p
    return kind, hp, ap


def score_state(d):
    if d <= -9: return "behind 9+"
    if d < 0: return "behind 1-8"
    if d == 0: return "tied"
    if d <= 8: return "ahead 1-8"
    return "ahead 9+"


def count_side(seasons):
    """Per game and per possession tables for one side, every number from r1.possessions, r2.intervals and e1.load (record.raw_frame decides the side)."""
    G, PO, ST = [], [], []
    for s in seasons:
        d = e1.load(s)
        d2, _, _ = r2.load(s)
        d1 = r1.load(s).sort_values(["game_id", "order_sequence"]).reset_index(drop=True)
        P = r1.possessions(d1)
        th = d.groupby("game_id")["total_home_score"].transform(lambda v: v.ffill().shift().fillna(0))
        ta = d.groupby("game_id")["total_away_score"].transform(lambda v: v.ffill().shift().fillna(0))
        d["h0"], d["a0"] = th, ta
        d["h1"] = d.groupby("game_id")["total_home_score"].transform(lambda v: v.ffill().fillna(0))
        d["a1"] = d.groupby("game_id")["total_away_score"].transform(lambda v: v.ffill().fillna(0))
        d["pts_row"] = (d["h1"] - d["h0"]) + (d["a1"] - d["a0"])
        GD = {g: x.reset_index(drop=True) for g, x in d.groupby("game_id", sort=False)}
        PG = {g: x.reset_index(drop=True) for g, x in P.groupby("game_id", sort=False)}
        for g, gd in d2.groupby("game_id", sort=False):
            x = GD[g]; reg = gd["season_type"].iloc[0] == "REG"
            seqi = {int(v): k for k, v in enumerate(x["order_sequence"])}
            pt = x["play_type"].tolist(); q_ = x["qtr"].astype(int).tolist(); pos = x["posteam"].tolist(); qs = x["quarter_seconds_remaining"].tolist()
            snap = [pt[k] in SNAPK and not one_(x.at[k, "two_point_attempt"]) for k in range(len(x))]
            pp = PG.get(g, pd.DataFrame(columns=P.columns))
            plist = list(pp.itertuples(index=False))
            gsr = lambda k: (4 - q_[k]) * 900 + qs[k] if q_[k] <= 4 else qs[k]
            prev_end = None
            for j, p_ in enumerate(plist):
                a = seqi[int(p_.s0)]; b = seqi[int(p_.s1)]
                ks = [k for k in range(a, b + 1) if snap[k] and pos[k] == p_.team]
                kl = b
                r = x.loc[kl]
                half = 1 if q_[a] <= 2 else (2 if q_[a] <= 4 else 3)
                nxt = plist[j + 1] if j + 1 < len(plist) else None
                nh = None if nxt is None else (1 if q_[seqi[int(nxt.s0)]] <= 2 else (2 if q_[seqi[int(nxt.s0)]] <= 4 else 3))
                if one_(r["touchdown"]) and r["td_team"] == p_.team and r["play_type"] not in ("kickoff", "punt"): end = "touchdown"
                elif r["play_type"] == "field_goal": end = "field goal try"
                elif r["play_type"] == "punt": end = "punt"
                elif one_(r["safety"]): end = "safety"
                elif one_(r["interception"]) or one_(r["fumble_lost"]): end = "turnover"
                elif nxt is not None and nh == half and nxt.team != p_.team and r["down"] == 4: end = "turnover on downs"
                elif nxt is None or nh != half: end = "end of half"
                else: end = "other"
                lo = seqi[int(plist[j - 1].s1)] + 1 if j > 0 else 0
                between = pt[lo:a]
                if "kickoff" in between or j == 0 or (j > 0 and (1 if q_[seqi[int(plist[j - 1].s0)]] <= 2 else (2 if q_[seqi[int(plist[j - 1].s0)]] <= 4 else 3)) != half): beg = "kickoff"
                elif prev_end == "punt": beg = "punt"
                elif prev_end == "turnover": beg = "turnover"
                elif prev_end == "turnover on downs": beg = "turnover on downs"
                elif prev_end == "field goal try": beg = "missed field goal"
                else: beg = "other"
                prev_end = end
                if half <= 2:
                    end_g = 1800 if half == 1 else 0
                    sec = gsr(a) - (gsr(seqi[int(nxt.s0)]) if nh == half else end_g)
                else:
                    sec = np.nan
                yl = x["yardline_100"].iloc[ks].astype(float) if ks else pd.Series(dtype=float)
                reached = lambda t: bool(len(yl) and (yl.min() <= t)) or end == "touchdown"
                PO.append(dict(season=s, game_id=g, reg=reg, ot=half == 3, half=half, team=p_.team, end=end, begin=beg, snaps=len(ks), sec=sec,
                               start_yl=float(x.at[a, "yardline_100"]) if not nanv(x.at[a, "yardline_100"]) else np.nan, r40=reached(40), r20=reached(20),
                               fg_made=r["play_type"] == "field_goal" and r["field_goal_result"] == "made",
                               score=score_state((r["h0"] - r["a0"]) * (1 if p_.team == x.at[a, "home_team"] else -1))))
            iv = r2.intervals(gd)
            for t in iv:
                if t["q"] > 4: continue
                ka, kb = seqi[t["sa"]], seqi[t["sb"]]
                la = np.nan
                if not (nanv(x.at[ka, "E"]) or nanv(x.at[ka, "W"])): la = float(x.at[ka, "E"] - x.at[ka, "W"])
                dG = float(t["dG"]); on_play = np.nan if nanv(la) else min(max(la, 0.0), dG)
                sc = score_state((x.at[ka, "h0"] - x.at[ka, "a0"]) * (1 if pos[ka] == x.at[ka, "home_team"] else -1))
                ST.append(dict(season=s, game_id=g, reg=reg, sa=t["sa"], sb=t["sb"], half=1 if t["q"] <= 2 else 2, q=t["q"], tb=e1.time_bin(t["q"], t["qa"]), cls=t["cls"], dG=dG,
                               on_play=on_play, between=bool(t["poss"]), score=sc, qa=float(t["qa"]), x=float(t["x"]) if not nanv(t["x"]) else np.nan, d3=t["d3"],
                               inc=bool(t["inc"]), ob=one_(t["ob"]), tmo=bool(t["tmo"]), tmw=t["tmw"] is True,
                               nopl=any(pt[k] == "no_play" and one_(x.at[k, "penalty"]) for k in range(ka + 1, kb)),
                               tb2="last 2:00 of the game" if t["q"] == 4 and t["qa"] <= 120 else e1.time_bin(t["q"], t["qa"]),
                               lsf=sc if (t["q"] in (2, 4) and t["qa"] <= 120) else "-"))
            pre = post = 0.0; n_snaps_reg = 0
            for qq in (1, 2, 3, 4):
                ks = [k for k in range(len(x)) if snap[k] and q_[k] == qq]
                if not ks: continue
                pre += 900 - float(qs[ks[0]]); post += float(qs[ks[-1]]); n_snaps_reg += len(ks)
            st_g = sum(t["dG"] for t in iv if t["q"] <= 4)
            fam = {}
            lat = x["lateral_receiver_player_id"].notna() | x["lateral_rusher_player_id"].notna()
            desc = x["desc"].astype(str)
            fam["laterals"] = lat
            fam["fouls by both teams (offsetting)"] = desc.str.contains("offsetting", case=False)
            fam["a foul and a turnover on one play"] = (x["penalty"] == 1) & ((x["interception"] == 1) | (x["fumble_lost"] == 1))
            fam["fumbles kept by the side that lost them"] = x["fumble_recovery_1_team"].notna() & (x["fumble_recovery_1_team"] == x["posteam"]) & x["play_type"].isin(list(SNAPK))
            fam["replay reviews"] = x["replay_or_challenge"] == 1
            fam["injuries"] = desc.str.contains("injur", case=False)
            fam["runoffs"] = desc.str.contains(r"run[- ]?off", case=False)
            fam["return touchdowns (kickoff, punt)"] = (x["touchdown"] == 1) & x["play_type"].isin(["kickoff", "punt"])
            fam["defensive touchdowns"] = (x["touchdown"] == 1) & x["play_type"].isin(list(SNAPK)) & x["td_team"].notna() & (x["td_team"] != x["posteam"])
            fam["fouls v0 does not play"] = (x["penalty"] == 1) & x["penalty_type"].notna() & ~x["penalty_type"].isin(list(OWN_FOULS))
            istry = ((x["play_type"] == "extra_point") | (x["two_point_attempt"] == 1)).to_numpy()
            def with_try(m):
                m = m.fillna(False).astype(bool).to_numpy().copy()
                for k in np.where(m & (x["touchdown"] == 1).to_numpy())[0]:
                    j = k + 1
                    while j < len(x) and pt[j] in ("", "no_play", None) and not istry[j]: j += 1
                    if j < len(x) and istry[j]: m[j] = True
                return pd.Series(m, index=x.index)
            fam = {k_: with_try(v) for k_, v in fam.items()}
            anyfam = pd.Series(False, index=x.index)
            for v in fam.values(): anyfam = anyfam | v
            kind, hp, ap = credit(x)
            dh = (x["h1"] - x["h0"]).to_numpy(); da = (x["a1"] - x["a0"]).to_numpy()
            badp = np.where((hp != dh) | (ap != da))[0]
            for i in badp:
                FAILP.append((SIDE[0], s, g, int(x.at[i, "order_sequence"]), int(x.at[i, "qtr"]), x.at[i, "play_type"], kind[i] or "none", f"credited home {hp[i]:.0f} away {ap[i]:.0f}",
                              f"board home {dh[i]:.0f} away {da[i]:.0f}", str(x.at[i, "desc"])[:200]))
            total = float(max(x["h1"].max(), 0) + max(x["a1"].max(), 0))
            qq = x["qtr"].to_numpy(); qsv = x["quarter_seconds_remaining"].to_numpy(dtype=float)
            back, latest = [], -1.0
            for i in range(len(x)):
                if qq[i] > 4 or np.isnan(qsv[i]): continue
                tnow = (qq[i] - 1) * 900 + (900 - qsv[i])
                if tnow < latest: back.append(i)
                latest = max(latest, tnow)
            for i in back:
                BACK.append((SIDE[0], s, g, int(x.at[i, "order_sequence"]), int(qq[i]), qsv[i - 1], qsv[i], str(x.at[i - 1, "desc"])[:120], str(x.at[i, "desc"])[:160]))
            gr = dict(season=s, game_id=g, reg=reg, has_ot=bool((x["qtr"] >= 5).any()), points=total, snaps=int(sum(snap)), snaps_reg=n_snaps_reg,
                      no_plays=int(((x["play_type"] == "no_play") & (x["timeout"] != 1)).sum()), rows=len(x),
                      clock_pre=pre, clock_stretch=st_g, clock_post=post, bad_plays=len(badp), back_steps=len(back))
            for k_, c_ in KINDS.items(): gr[c_] = float(sum(hp[i] + ap[i] for i in range(len(x)) if kind[i] == k_))
            gr["pts_unclassed"] = float(sum(hp[i] + ap[i] for i in range(len(x)) if kind[i] and kind[i] not in KINDS))
            for k_, v in fam.items(): gr["ub " + k_] = float(x.loc[v, "pts_row"].clip(lower=0).sum())
            gr["ub any family (union)"] = float(x.loc[anyfam, "pts_row"].clip(lower=0).sum())
            G.append(gr)
    return pd.DataFrame(G), pd.DataFrame(PO), pd.DataFrame(ST)


# ---------------- h: one shared parse per side and season (a cache of the readers' results, copies handed out) ----------------
# ---------------- helpers ----------------
CLS = ["RUN", "STOP", "PARTIAL"]
AH, BH = ("ahead 1-8", "ahead 9+"), ("behind 1-8", "behind 9+")
LEV = [("cls", "tb", "ls"), ("cls", "tb"), ("cls",)]
TB2 = ["normal", "last 2:00 of the first half", "last 5:00 of the game", "last 2:00 of the game"]
TO_N = re.compile(r"Timeout #(\d+) by ([A-Z]{2,3})")


def late(x):
    return x["q"].isin([2, 4]) & (x["qa"] <= 120)


def keyed(x, split):
    x = x.copy(); on = x["cls"].map(lambda c: bool(split.get(c))) & late(x)
    x["ls"] = np.where(on, x["score"], "-"); return x


def kstr(x, L):
    return x[list(L)].astype(str).agg(" | ".join, axis=1)


def cm(x, val="dG"):
    n = len(x)
    if n < 2 or x["game_id"].nunique() < 2: return (x[val].mean() if n else np.nan), np.nan, n
    m = x[val].mean(); g = ((x[val] - m) / n).groupby(x["game_id"].values).sum(); G = len(g)
    return m, 2 * np.sqrt((g ** 2).sum() * G / (G - 1)), n


def within(a, b):
    d = b[0] - a[0]; s = np.sqrt(a[1] ** 2 + b[1] ** 2)
    return d, s, (not np.isnan(s)) and abs(d) <= s


def mg(v):
    v = pd.Series(v, dtype=float); n = len(v)
    return v.mean(), (2 * v.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan)


def boot(df, val, q, B=200, seed=0):
    if not len(df): return np.nan, np.nan
    g = {k: v[val].to_numpy() for k, v in df.groupby("game_id")}; keys = list(g); rng = np.random.default_rng(seed)
    est = float(np.percentile(df[val], q)); bs = []
    for _ in range(B):
        pick = rng.integers(len(keys), size=len(keys)); bs.append(np.percentile(np.concatenate([g[keys[i]] for i in pick]), q))
    return est, 2 * float(np.std(bs, ddof=1))


def moments(d):
    """Every charged timeout row in regulation with its moment, caller, number, the real seconds and the game seconds run since the act before it."""
    out = []
    for g, x in d.groupby("game_id", sort=False):
        x = x.reset_index(drop=True); n = len(x)
        rk = [e1.row_kind(p, k, t) for p, k, t in zip(x["play_type"], x["kind"], x["two_point_attempt"])]
        desc = x["desc"].astype(str).tolist(); q = x["qtr"].tolist(); qs = x["quarter_seconds_remaining"].tolist(); pos = x["posteam"].tolist()
        W = x["W"].tolist(); E = x["E"].tolist()
        for i in range(n):
            if not e1.one(x.at[i, "timeout"]) or q[i] > 4: continue
            m = TO_N.search(desc[i])
            j = i - 1; warn = False
            while j >= 0 and q[j] == q[i] and rk[j] == "other":
                if "two-minute warning" in desc[j].lower(): warn = True
                j -= 1
            if j < 0 or q[j] != q[i]: mom = "start of the quarter"
            elif warn: mom = "after the two-minute warning"
            elif rk[j] == "snap":
                nx = next((k for k in range(i + 1, n) if rk[k] == "snap" and q[k] == q[i]), None)
                same = nx is not None and pos[nx] == pos[j] and not (e1.one(x.at[j, "touchdown"]) or x.at[j, "field_goal_result"] == "made" or e1.one(x.at[j, "safety"]))
                mom = "after a snap, the same team snaps next" if same else "after a snap that ended the possession or scored"
            else: mom = {"kickoff": "after a kickoff", "try": "after a Try", "foul": "after a foul", "timeout": "right after another timeout"}.get(rk[j], f"after a row of kind {rk[j]}")
            ns = next((k for k in range(i + 1, n) if rk[k] == "snap"), None)
            caller = "not charged by its text" if not m else ("no next snap" if ns is None else ("offense" if m.group(2) == pos[ns] else "defense"))
            st = E[j] if (j >= 0 and not e1.nan(E[j])) else (W[j] if j >= 0 else np.nan)
            rs = W[i] - st if not (e1.nan(W[i]) or e1.nan(st)) else np.nan
            after = (qs[j] - (E[j] - W[j])) if (j >= 0 and rk[j] in ("snap", "kickoff") and not (e1.nan(E[j]) or e1.nan(W[j]))) else (qs[j] if j >= 0 and rk[j] not in ("snap", "kickoff") else np.nan)
            gr = max(after - qs[i], 0.0) if not e1.nan(after) else np.nan
            sc = e1.score_bin(x.at[ns, "diff"]) if (ns is not None and "diff" in x.columns) else "-"
            out.append(dict(game_id=g, season=x.at[i, "season"], q=q[i], qs=qs[i], tb2="last 2:00 of the game" if q[i] == 4 and qs[i] <= 120 else e1.time_bin(q[i], qs[i]),
                            moment=mom, caller=caller, team=m.group(2) if m else None, num=int(m.group(1)) if m else -1, charged=bool(m), real_since=rs, game_run=gr, score=sc))
    return pd.DataFrame(out)


def with_diff(d):
    d = d.copy()
    th = d.groupby("game_id")["total_home_score"].transform(lambda s: s.ffill().shift().fillna(0)); ta = d.groupby("game_id")["total_away_score"].transform(lambda s: s.ffill().shift().fillna(0))
    d["diff"] = np.where(d["posteam"] == d["home_team"], th - ta, ta - th); return d


def left_at_half(TMx, games):
    out = {}
    T = TMx[TMx["charged"]].assign(half=lambda z: np.where(z["q"] <= 2, 1, 2))
    cnt = T.groupby(["game_id", "half", "team"]).size()
    for h in (1, 2):
        for k in (3, 2, 1, 0, -1):
            v = []
            for g, home, away in games:
                used = [int(cnt.get((g, h, t_), 0)) for t_ in (home, away)]
                left = [3 - u for u in used]
                v.append(np.mean([(l_ == k) if k >= 0 else (l_ < 0) for l_ in left]))
            out[(h, k)] = mg(v)
    return out



# ---------------- the estimators (fixed as v12 ran them) ----------------
TREE = dict(learning_rate=0.1, max_leaf_nodes=15, min_samples_leaf=e1.MIN_BIN, l2_regularization=0.0, early_stopping=False, random_state=0)
CAP = {"run": 500, "stop": 500}


def fit_part(X, y, seasons, cap, inner_model=None):
    from sklearn.ensemble import HistGradientBoostingClassifier as HGB
    inner = max(set(seasons.tolist())); tr = seasons != inner; te = ~tr
    if tr.sum() == 0 or te.sum() == 0 or len(np.unique(y[tr])) < 2: raise record.GAP("refused: no inner held-out season with two or more classes to choose rounds on")
    m = inner_model if inner_model is not None else HGB(**dict(TREE, max_iter=cap)).fit(X[tr], y[tr])
    idx = {c: k for k, c in enumerate(m.classes_)}; keep = np.array([v in idx for v in y[te]]); yi = np.array([idx[v] for v in y[te][keep]], dtype=int)
    ll = [float(-np.mean(np.log(np.clip(p[np.arange(len(yi)), yi], 1e-300, None)))) for p in m.staged_predict_proba(X[te][keep])]
    best = int(np.argmin(ll)) + 1
    if best >= cap: raise record.GAP(f"refused: the lowest inner log loss is at the ceiling ({cap} rounds)")
    final = HGB(**dict(TREE, max_iter=best)).fit(X, y)
    return final, dict(inner=int(inner), best=best, cap=cap, ll_best=ll[best - 1], ll_first=ll[0], ll_cap=ll[-1], unseen=int((~keep).sum()), n=len(y))


RACE_TBINS = ((0, 7), (8, 15), (16, 23), (24, 31), (32, 40))   # v19 w1: the seconds already run on the play clock, in 8-second bins, crossed with the time left in the half


def race_design(X, mu, sd, tcap):
    """v19 w1: the race's inputs (the same text in e1.py): the numbers standardised; t (the seconds since the play ended, read up to the play clock) one
    indicator a second; and the time left in the half crossed with t: the last two minutes of a half (quarters 2 and 4, the quarter's clock at the play's end
    less t at or under 120) and quarters 2 and 4 apart from 1 and 3, each times RACE_TBINS. X: q, the clock at the play's end, the score difference, down,
    distance, yard line, the timeouts each side has, review, injury, t."""
    t = np.clip(X[:, -1].astype(int), 0, tcap)
    I = np.zeros((len(X), tcap)); r = np.where(t > 0)[0]; I[r, t[r] - 1] = 1.0
    q = X[:, 0]; q24 = (q == 2) | (q == 4); late = q24 & ((X[:, 1] - X[:, -1]) <= 120)
    B = np.column_stack([(t >= a_) & (t <= b_) for a_, b_ in RACE_TBINS]).astype(float)
    return np.column_stack([(X[:, :-1] - mu) / sd, I, B * late[:, None], B * q24[:, None]])


class LRRace:
    """The race's estimator: a multinomial logistic race (v12's: no penalty; lbfgs, at most 1,000 iterations) on race_design's inputs (v19 w1: the time left
    in the half crossed with the play clock's seconds added). shuffle: w1's plant only, the time-left columns permuted across moments before the fit."""
    def __init__(self, X, y, shuffle=None):
        from sklearn.linear_model import LogisticRegression
        self.tcap = T_CAP
        self.mu = X[:, :-1].mean(0); self.sd = X[:, :-1].std(0); self.sd[self.sd == 0] = 1.0
        D_ = self.design(X)
        if shuffle is not None:
            k_ = 2 * len(RACE_TBINS); D_[:, -k_:] = D_[np.random.default_rng(shuffle).permutation(len(D_)), -k_:]
        self.m = LogisticRegression(penalty=None, max_iter=1000).fit(D_, y)
        self.classes_ = self.m.classes_; self.iters = int(np.max(self.m.n_iter_)); self.converged = self.iters < 1000

    def design(self, X):
        return race_design(X, self.mu, self.sd, self.tcap)

    def predict_proba(self, X):
        return self.m.predict_proba(self.design(X))


def lr_bytes(M_):
    return pickle.dumps((M_.m, M_.mu, M_.sd))


def tree_bytes(M_):
    """h: a fitted tree model's content as bytes (its classes, starting values, every tree's nodes, the bin edges, its rounds); the run settings it also
    pickles (the thread count, object identity inside pickle) are not fitted content and are left out."""
    return pickle.dumps(([str(c) for c in M_.classes_], np.asarray(M_._baseline_prediction).tobytes(), [[p.nodes.tobytes() for p in it] for it in M_._predictors],
                         [np.asarray(b).tobytes() for b in M_._bin_mapper.bin_thresholds_], int(M_.n_iter_)))


class Batcher:
    def __init__(self, parts, n):
        self.parts = parts; self.cv = threading.Condition(); self.active = n; self.req = {}; self.res = {}; self.err = None; self.batches = 0

    def eval(self, part, X):
        tid = threading.get_ident()
        with self.cv:
            self.req[tid] = (part, X); self._run()
            self.cv.wait_for(lambda: tid in self.res or self.err is not None)
            if self.err is not None and tid not in self.res: raise self.err
            return self.res.pop(tid)

    def done(self):
        with self.cv:
            self.active -= 1; self._run()

    def _run(self):
        if not self.req or len(self.req) < self.active: return
        try:
            for part in {p for p, _ in self.req.values()}:
                ids = [t for t, (p, _) in self.req.items() if p == part]; Xs = [self.req[t][1] for t in ids]
                P = self.parts[part].predict_proba(np.vstack(Xs)); k = 0
                for t, x in zip(ids, Xs): self.res[t] = P[k:k + len(x)]; k += len(x)
            self.batches += 1
        except Exception as ex_:
            self.err = ex_
        self.req.clear(); self.cv.notify_all()


def play_threaded(m, s, sched_s, Rs, X6):
    """One season's games, each with its own generator ([SEED, season, game index]); the race's models batched across the games' threads (none: the
    race off). Returns the rows, declarations, counts, games not played, the race's log, batches, the drawn rows' sources, each game's change log and the rows
    from which each game is unsupported."""
    games = [g for _, g in sched_s.iterrows()]; n_ = len(games)
    MOD = getattr(Rs, "RACE_MODELS", None)
    B = Batcher(None if MOD is None else dict(MOD, call4=getattr(Rs, "CALL4", None)), n_)   # aa1: the choice model batched with the race's parts
    Rs.RACE = dict(eval=B.eval, run_cls=list(MOD["run"].classes_), stop_cls=list(MOD["stop"].classes_), t_cap=T_CAP) if MOD is not None else None
    rows, logs, cnts, decs, sk, chg, uns = [None] * n_, [None] * n_, [None] * n_, [None] * n_, [None] * n_, [None] * n_, [None] * n_
    def work(k, g):
        try:
            G = m.Game(g, Rs, X6, np.random.default_rng([m.SEED, s, k]), s)
            rows[k] = G.run(); logs[k] = [(g["game_id"], s) + x for x in getattr(G, "race_log", [])]; cnts[k] = G.cnt; decs[k] = G.declared
            chg[k] = list(getattr(G, "chg", [])); uns[k] = list(getattr(G, "unsup", []))
        except record.GAP as ex_:
            sk[k] = str(ex_)[:120]
        finally:
            B.done()
    th_ = [threading.Thread(target=work, args=(k, g)) for k, g in enumerate(games)]
    for t_ in th_: t_.start()
    for t_ in th_: t_.join()
    if B.err is not None: raise B.err
    out, cnt, dec, SK, LG, SRC, CHG, UNS = [], Counter(), [], Counter(), [], [], {}, {}
    for k in range(n_):
        if rows[k] is not None:
            out += rows[k]; cnt.update(cnts[k]); LG += logs[k]; CHG[games[k]["game_id"]] = chg[k]; UNS[games[k]["game_id"]] = uns[k]
            SRC += [(r_["game_id"], r_["order_sequence"], r_["src"]) for r_ in rows[k] if r_.get("src")]
        if decs[k]: dec.append((games[k]["game_id"], decs[k]))
        if sk[k]: SK[sk[k]] += 1
    return out, dec, cnt, SK, LG, B.batches, SRC, CHG, UNS


def cal_tests(p, obs, gidx, G, Wb):
    dec = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False).to_numpy()
    Sm = np.zeros((G, 10)); Nm = np.zeros((G, 10)); Pm = np.zeros((G, 10)); Om = np.zeros((G, 10))
    np.add.at(Sm, (gidx, dec), obs - p); np.add.at(Nm, (gidx, dec), 1.0); np.add.at(Pm, (gidx, dec), p); np.add.at(Om, (gidx, dec), obs)
    d = Sm.sum(0) / Nm.sum(0); db = (Wb @ Sm) / np.maximum(Wb @ Nm, 1e-12)
    Vm = np.zeros(10); np.add.at(Vm, dec, p * (1 - p)); binom = 2 * np.sqrt(Vm) / Nm.sum(0)
    se2 = np.maximum(2 * db.std(0, ddof=1), binom)
    miss = np.abs(d) > se2; nullc = (np.abs(db - d) > se2).sum(1)
    return [(k, Pm[:, k].sum() / Nm[:, k].sum(), Om[:, k].sum() / Nm[:, k].sum(), d[k], se2[k], bool(miss[k])) for k in range(10)], nullc



# ---------------- the work each process does (the same functions run serially in this process for the byte comparison) ----------------
_W = {}


def load_mod(text, name):
    dd = tempfile.mkdtemp(); p = os.path.join(dd, name + ".py"); open(p, "w").write(text)
    sp = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); shutil.rmtree(dd)
    return m


def w_init(cwd, path, cfg, log, nthreads=None):
    """A worker's start. nthreads: the threads each worker's numerical libraries (OpenMP for the trees, BLAS for the race) may use, capped by threadpoolctl
    (a runtime setting only: no estimator, setting or check changes); None leaves them as the libraries choose (every core)."""
    os.chdir(cwd); sys.path[:] = path
    sys.stdout = sys.stderr = open(log, "a", buffering=1)   # the workers' own printing goes to the run's log, not the terminal
    configure(**cfg)
    _W.clear()
    if nthreads:   # set before the worker's OpenMP and BLAS libraries start (they read these once, when they load), then held by threadpoolctl once they are loaded
        for v_ in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"): os.environ[v_] = str(int(nthreads))
    from sklearn.ensemble import HistGradientBoostingClassifier   # loads the trees' OpenMP library now, so the limit below reaches it
    from sklearn.linear_model import LogisticRegression
    if nthreads:
        from threadpoolctl import threadpool_limits
        _W["limits"] = threadpool_limits(limits=int(nthreads))


def _engine(text):
    k = shs(text)
    if _W.get(("e1n", k)) is None:
        m_ = load_mod(text, "e1_v29aa_" + k)
        for k_, v_ in ENGINE_CONF.items(): setattr(m_, k_, v_)   # v19 part 2: the engine's caller-set values (its landed form reads them)
        _W[("e1n", k)] = m_
    return _W[("e1n", k)]


def _tables(path):
    if _W.get("tab_path") != path:
        _W["tab"] = pickle.load(open(path, "rb")); _W["tab_path"] = path
    return _W["tab"]


def w_play(text, s, sched_s, tab_path, models_bytes, x6, seasons, flags):
    """One season's games played by the engine built from text (flags set on it), each game with its own generator; models_bytes None: the race off."""
    m = _engine(text)
    for k_, v_ in flags.items(): setattr(m, k_, v_)
    TAB = _tables(tab_path)
    Rs = m.Rates(s, [TAB[x][0] for x in seasons if x != s]); mb = pickle.loads(models_bytes) if models_bytes is not None else None
    Rs.RACE_MODELS = None if mb is None else mb["race"]; Rs.CALL4 = None if mb is None else mb["call4"]; Rs.CALL4_SHARE = None if mb is None else mb.get("call4_share")   # aa1: the race's parts, the choice model and arm B's share table, or none (the floor)
    t0 = time.time(); out = play_threaded(m, s, sched_s, Rs, x6)
    return (m.text_frame(out[0]),) + out[1:] + (time.time() - t0,)


def eval_season(s, F, x6, shared=True, checks=True):
    """One season's engine games: E2a's counts, the timeout moments and section 4's checks, from one parse (shared) or from separate parses."""
    SIDE[0] = "engine"; FAILP.clear(); BACK.clear()
    ctx = SharedParse() if shared else _Null()
    with e1.OnSim({s: F}), ctx:
        G_, PO_, ST_ = count_side([s])
        dM = with_diff(e1.load(s)); TM = moments(dM)
        sec4 = None
        if checks:
            w4, bad4 = e1.check_r4([s]); C1, left1, _ = e1.check_r1([s]); CK, FL, COST, _ = check_clock2([s]); PO, PB = e1.check_periods({s: F}, x6, [s]); SR = e1.season_rule_check([s], x6)
            sec4 = dict(w4=w4, bad4=bad4, C1=C1, left1=left1, CK=CK, FL=FL, COST=COST, PO=PO, PB=PB, SR=SR)
    return dict(G=G_, PO=PO_, ST=ST_, dM=dM, TM=TM, sec4=sec4, failp=list(FAILP), back=list(BACK))


class _Null:
    def __enter__(self): return self
    def __exit__(self, *a): pass


def w_eval(s, F, x6, shared=True, checks=True):
    t0 = time.time(); r = eval_season(s, F, x6, shared, checks); r["sec"] = time.time() - t0; return r


def w_fit_stop(npz, s_out, cap):
    z = np.load(npz, allow_pickle=True); X, y, ss = z["X"], z["y"], z["s"]; tr = ss != s_out
    t0 = time.time()
    try: m, inf = fit_part(X[tr], y[tr], ss[tr], cap)
    except record.GAP as ex_: return s_out, None, str(ex_), time.time() - t0
    return s_out, pickle.dumps(m), inf, time.time() - t0


def w_fit_race(npz, fs, key, shuffle=None):
    z = np.load(npz, allow_pickle=True); X, y, ss = z["X"], z["y"], z["s"]; tr = np.isin(ss, fs)
    t0 = time.time(); M = LRRace(X[tr], y[tr], shuffle)
    return key, pickle.dumps(M), time.time() - t0


def w_fit_call4(npz, s_out, cap, shuffle=None):
    """aa1: the fourth-down choice (go, field_goal, punt) fitted on every season but s_out (look-back; the rounds by fit_part's inner season, the trees as the
    stopped part's). shuffle: the plant only, the yard line (column 0) permuted across the fitted rows before the fit (seed shuffle)."""
    z = np.load(npz, allow_pickle=True); X, y, ss = z["X"].copy(), z["y"], z["s"]; tr = ss != s_out
    if shuffle is not None: X[tr, 0] = X[tr, 0][np.random.default_rng(shuffle).permutation(int(tr.sum()))]
    t0 = time.time()
    try: m, inf = fit_part(X[tr], y[tr], ss[tr], cap)
    except record.GAP as ex_: return s_out, None, str(ex_), time.time() - t0
    return s_out, pickle.dumps(m), inf, time.time() - t0


def w_plant(name, text, s4, sched_s, tab_path, models_bytes, x6, seasons):
    m = _engine(text); m.R1A = m.R1B = m.R1D = True; m.QE_BAND = 10
    TAB = _tables(tab_path)
    Rp = m.Rates(s4, [TAB[x][0] for x in seasons if x != s4]); mb = pickle.loads(models_bytes); Rp.RACE_MODELS = mb["race"]; Rp.CALL4 = mb["call4"]; Rp.CALL4_SHARE = mb.get("call4_share")
    out_ = play_threaded(m, s4, sched_s, Rp, x6)
    F = {s4: m.text_frame(out_[0])}   # every game (none removed for what it drew)
    if not len(F[s4]): return name, None, "no game to plant into", "the plant"
    with m.OnSim(F):
        if name == "P1": _, lp, _ = m.check_r1([s4]); v = len(lp); ok = v > 0; what = "r1 unexplained"
        elif name == "P2": w, _ = m.check_r4([s4]); v = w["OTHER"]; ok = v > 0; what = "r4 OTHER"
        elif name == "P3": ck, _, _, _ = check_clock2([s4]); v = ck["STOP failed"]; ok = v > 0; what = "stopped clock failed (the check)"
        else: sr = m.season_rule_check([s4], x6); v = sr[s4]["M1"]; ok = v != x6[s4]["touchback"]["value"]; what = f"R7 M1 against X6's {x6[s4]['touchback']['value']}"
    return name, ok, v, what

