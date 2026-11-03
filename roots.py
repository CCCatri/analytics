"""nfl4 roots.py - S3 game-scale root map (RUBRIC section 2). A read: it earns nothing; each (root, link) cell gets one of
CANDIDATE / MECHANISM / NOISE. Fits are printed with parameters, rows and SE; no number here gates anything."""
import hashlib, time
import numpy as np
import pandas as pd
import contract, record

SEED = 0                      # printed on every line (M4); an identity, not a threshold
LINKS = ("snaps", "pass_share", "sack_rate", "scramble_rate")
ROOT_VARS = {"AVAIL": ("qb_out", "ol_out", "top2_out", "opp_def_out"),
             "SCHEME": ("own_snaps_td", "own_pass_td", "opp_snaps_td", "opp_pass_td"),
             "MATCH": ("opp_sackrate_allowed_td", "opp_ypa_allowed_td", "opp_ypc_allowed_td"),
             "ENV": ("indoors", "grass", "rest", "div_game", "hour"),
             "SCRIPT": ("own_pd_td", "opp_pd_td")}
ALL_VARS = [v for g in ROOT_VARS.values() for v in g]
OFFENSE_POS = set(contract.POSITION_GROUP) | {"K", "P"}
INJ_COLUMNS = ("season", "week", "team", "gsis_id", "position", "report_status")
INJ_TYPES = {"season": ("int", False), "week": ("int", False), "team": ("str", False), "gsis_id": ("str", True),
             "position": ("str", True), "report_status": ("str", True)}


def team_game_table(season):
    """One row per (game, team): this game's offensive counts (the links), its pregame columns (the roots' raw material)."""
    ev = record.events(season)
    sched = record.games(season)
    part = record.participation(season); sets = record.on_field_sets(ev, part, f"{season}"); pos = record.positions(season)
    codes = frozenset(sched["home_team"]) | frozenset(sched["away_team"])
    inj = record.read(contract.INJURIES_FILE.format(season=season), INJ_COLUMNS, INJ_TYPES, f"injuries {season}")
    is_out = inj["report_status"].notna() & (inj["report_status"] == "Out") & inj["gsis_id"].notna()
    out_rows = inj[is_out.to_numpy(dtype=bool)]
    unresolved = 0; out_by = {}; def_out_by = {}
    for team, week, gid, p in zip(out_rows["team"], out_rows["week"], out_rows["gsis_id"], out_rows["position"]):
        t = record.resolve_code(team, codes)
        if t is None:
            unresolved += 1; continue
        out_by.setdefault((t, int(week)), set()).add(gid)
        if p not in OFFENSE_POS:
            def_out_by[(t, int(week))] = def_out_by.get((t, int(week)), 0) + 1
    print(f"injuries {season} rows {len(inj)} Out rows {len(out_rows)} unresolved team codes {unresolved} team-weeks with an Out {len(out_by)}")
    sc = ev[ev["kind"].isin(contract.CALL_KINDS) & ev["posteam"].notna()]
    pbp_codes = frozenset(sc["posteam"].unique())
    code_map = {}
    for c in codes:
        rc = record.resolve_code(c, pbp_codes)
        if rc is None:
            raise record.GAP(f"team_games {season}: schedule code {c} has no pbp posteam code (TEAM_ALIASES)")
        code_map[c] = rc
    remapped = {c: rc for c, rc in code_map.items() if c != rc}
    print(f"team_games {season} schedule codes {len(codes)} pbp codes {len(pbp_codes)} remapped via TEAM_ALIASES {remapped}")
    rows = []; unknown_total = 0
    for _, g in sched.iterrows():
        gid = g["game_id"]
        for team, opp, rest, pf, pa in ((g["home_team"], g["away_team"], g["home_rest"], g["home_score"], g["away_score"]),
                                        (g["away_team"], g["home_team"], g["away_rest"], g["away_score"], g["home_score"])):
            s = sc[(sc["game_id"] == gid) & (sc["posteam"] == code_map[team])]
            if len(s) == 0:
                raise record.GAP(f"team_games {season}: played team-game {gid} {team} has no scrimmage row (R2)")
            k = s["kind"].to_numpy(dtype=object)
            yg = s["yards_gained"].to_numpy(dtype=float)
            drop = np.isin(k, contract.DROPBACK); carry = np.isin(k, contract.CARRY_KINDS)
            comp = record.flag(s, "complete_pass") & (k == "pass")
            pm = drop & s["passer_player_id"].notna().to_numpy()
            qb = s["passer_player_id"][pm].value_counts().index[0] if pm.any() else None
            rm = (k == "pass") & s["receiver_player_id"].notna().to_numpy()
            top2 = frozenset(s["receiver_player_id"][rm].value_counts().index[:2]) if rm.any() else None
            cnt = {}; unknown = 0
            for p in s["play_id"]:
                st = sets.get((gid, p))
                if st:
                    for m in st:
                        cnt[m] = cnt.get(m, 0) + 1
                else:
                    unknown += 1
            unknown_total += unknown
            ol = sorted((m for m in cnt if contract.position_group(pos.get(m)) == "OL"), key=lambda m: -cnt[m])[:5]
            rows.append(dict(season=season, game_id=gid, team=team, opp=opp, week=int(g["week"]), gameday=g["gameday"],
                             gametime=g["gametime"], roof=g["roof"], surface=g["surface"], rest=int(rest), div_game=int(g["div_game"]),
                             pts_for=int(pf), pts_against=int(pa), snaps=len(s), dropbacks=int(drop.sum()),
                             sacks=int((k == "sack").sum()), scrambles=int((k == "scramble").sum()),
                             attempts=int(np.isin(k, contract.ATTEMPT_KINDS).sum()), pass_yards=float(yg[comp].sum()),
                             carries=int(carry.sum()), carry_yards=float(yg[carry].sum()),
                             qb=qb, top2=top2, ol=frozenset(ol) if ol else None, ol_known=len(ol), unknown_sets=unknown))
    tg = pd.DataFrame(rows)
    tg["out_by"] = [out_by.get((t, w), frozenset()) for t, w in zip(tg["team"], tg["week"])]
    tg["opp_def_out"] = [float(def_out_by.get((o, w), 0)) for o, w in zip(tg["opp"], tg["week"])]
    print(f"team_games {season} rows {len(tg)} zero-dropback team-games {int((tg['dropbacks'] == 0).sum())} scrimmage plays with unknown set {unknown_total} "
          f"OL starters known 5 {int((tg['ol_known'] == 5).sum())} fewer {int((tg['ol_known'] < 5).sum())}")
    return tg


def with_roots(tg):
    """Pregame columns from prior games only; a missing prior is NaN and counted, never filled."""
    tg = tg.sort_values(["season", "team", "gameday", "gametime", "game_id"]).reset_index(drop=True)
    tg["pass_share"] = tg["dropbacks"] / tg["snaps"]
    tg["sack_rate"] = tg["sacks"] / tg["dropbacks"]
    tg["scramble_rate"] = tg["scrambles"] / tg["dropbacks"]
    tg["pd"] = tg["pts_for"] - tg["pts_against"]
    tg["ypa"] = tg["pass_yards"] / tg["attempts"]
    tg["ypc"] = tg["carry_yards"] / tg["carries"]
    grp = tg.groupby(["season", "team"], sort=False)
    def todate(col):
        return grp[col].transform(lambda x: x.shift(1).expanding().mean())
    tg["own_snaps_td"] = todate("snaps"); tg["own_pass_td"] = todate("pass_share"); tg["own_pd_td"] = todate("pd")
    # what this team's defense allowed in each game = the opponent's offense in that game
    key = {(g, t): i for i, (g, t) in enumerate(zip(tg["game_id"], tg["team"]))}
    oi = np.array([key[(g, o)] for g, o in zip(tg["game_id"], tg["opp"])])
    tg["sackrate_allowed"] = tg["sack_rate"].to_numpy()[oi]
    tg["ypa_allowed"] = tg["ypa"].to_numpy()[oi]
    tg["ypc_allowed"] = tg["ypc"].to_numpy()[oi]
    tg["sackrate_allowed_td"] = todate("sackrate_allowed"); tg["ypa_allowed_td"] = todate("ypa_allowed"); tg["ypc_allowed_td"] = todate("ypc_allowed")
    for src, dst in (("own_snaps_td", "opp_snaps_td"), ("own_pass_td", "opp_pass_td"), ("own_pd_td", "opp_pd_td"),
                     ("sackrate_allowed_td", "opp_sackrate_allowed_td"), ("ypa_allowed_td", "opp_ypa_allowed_td"), ("ypc_allowed_td", "opp_ypc_allowed_td")):
        tg[dst] = tg[src].to_numpy()[oi]
    prev_qb = grp["qb"].shift(1); prev_ol = grp["ol"].shift(1); prev_top2 = grp["top2"].shift(1)
    tg["qb_out"] = [np.nan if q is None or (isinstance(q, float)) else float(q in ob) for q, ob in zip(prev_qb, tg["out_by"])]
    tg["ol_out"] = [np.nan if not isinstance(o, frozenset) else float(len(o & ob)) for o, ob in zip(prev_ol, tg["out_by"])]
    tg["top2_out"] = [np.nan if not isinstance(o, frozenset) else float(len(o & ob)) for o, ob in zip(prev_top2, tg["out_by"])]
    tg["indoors"] = [np.nan if r is None else float(r in ("dome", "closed")) for r in tg["roof"]]
    tg["grass"] = [np.nan if s is None else float(s == "grass") for s in tg["surface"]]
    tg["hour"] = [np.nan if (t is None or ":" not in str(t)) else float(str(t).split(":")[0]) for t in tg["gametime"]]
    tg["rest"] = tg["rest"].astype(float); tg["div_game"] = tg["div_game"].astype(float)
    return tg


def ols_cluster(X, y, groups):
    """OLS with an intercept; SE clustered by team-season (Liang-Zeger with the usual small-sample factor). A formula, not a number."""
    n = len(y)
    X1 = np.column_stack([np.ones(n), X])
    k = X1.shape[1]
    XtX_inv = np.linalg.inv(X1.T @ X1)
    beta = XtX_inv @ X1.T @ y
    e = y - X1 @ beta
    meat = np.zeros((k, k))
    codes, inv = np.unique(groups, return_inverse=True)
    G = len(codes)
    for g in range(G):
        m = inv == g
        s = X1[m].T @ e[m]
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    ssr = float(e @ e); sst = float(((y - y.mean()) ** 2).sum())
    return beta[1:], np.sqrt(np.diag(V))[1:], ssr, sst


ROOTS = [v for g, vs in ROOT_VARS.items() for v in vs if g != "SCHEME"] + ["opp_snaps_td", "opp_pass_td"]
OWN_TD = {"snaps": "own_snaps_td", "pass_share": "own_pass_td", "sack_rate": "own_sackrate_td", "scramble_rate": "own_scramblerate_td"}


def words(d, link, X_override=None):
    """Link = today's rate minus own to-date mean, team-season means removed from both sides. Per root, with the others held:
    pooled slope and clustered SE; six leave-one-season-out slopes and SEs; swing share; word.
    CANDIDATE = pooled |slope| > k_se x SE and the same sign in every fold. MECHANISM is assigned by run() from the own-history-held test.
    IRREDUCIBLE = the partial slope (other roots held) excludes zero at k_se SE, i.e. the same test as the pooled one."""
    k = contract.POLICY["k_se"]
    groups = (d["season"].astype(str) + "_" + d["team"]).to_numpy()
    y_raw = (d[link] - d[OWN_TD[link]]).to_numpy(dtype=float)
    X_raw = d[ROOTS].to_numpy(dtype=float) if X_override is None else X_override
    gf = pd.DataFrame(np.column_stack([y_raw, X_raw]))
    gm = gf.groupby(groups).transform("mean").to_numpy()
    y = y_raw - gm[:, 0]; X = X_raw - gm[:, 1:]
    beta, se, ssr, sst = ols_cluster(X, y, groups)
    seasons = sorted(d["season"].unique())
    folds = []
    for s in seasons:
        m = (d["season"] != s).to_numpy()
        bb, ss, _, _ = ols_cluster(X[m], y[m], groups[m])
        folds.append((bb, ss))
    out = []
    for j, v in enumerate(ROOTS):
        keep = [i for i in range(len(ROOTS)) if i != j]
        _, _, ssr_j, _ = ols_cluster(X[:, keep], y, groups)
        share = (ssr_j - ssr) / sst if sst > 0 else np.nan
        fb = [f[0][j] for f in folds]; fs = [f[1][j] for f in folds]
        pooled = int(np.sign(beta[j]))
        excl = abs(beta[j]) > k * se[j]
        stable = pooled != 0 and all(int(np.sign(x)) == pooled for x in fb)
        word = "CANDIDATE" if (excl and stable) else "NOISE"
        held = None
        if word == "CANDIDATE":
            mb, ms = mechanism_test(d, link, v, X_override=X_override, col=j)
            held = (mb, ms)
            if abs(mb) <= k * ms or int(np.sign(mb)) != pooled:
                word = "MECHANISM"
        out.append(dict(var=v, link=link, n=len(d), slope=beta[j], se=se[j], share=share, irreducible=excl, pooled_excl=excl and stable,
                        folds=list(zip(fb, fs)), signs="".join("+" if x > 0 else "-" if x < 0 else "0" for x in fb), word=word, held=held))
    return out


def mechanism_test(d, link, var, X_override=None, col=None):
    """Today's level of the link within team-season on the root with the own to-date mean held (clustered SE).
    A CANDIDATE whose slope here is inside k_se SE, or of the opposite sign, moved only the contaminated deviation: MECHANISM."""
    groups = (d["season"].astype(str) + "_" + d["team"]).to_numpy()
    y = d[link].to_numpy(dtype=float)
    xv = d[var].to_numpy(dtype=float) if X_override is None else X_override[:, col]
    Xb = np.column_stack([xv, d[OWN_TD[link]].to_numpy(dtype=float)])
    gf = pd.DataFrame(np.column_stack([y, Xb])); gm = gf.groupby(groups).transform("mean").to_numpy()
    b, se, _, _ = ols_cluster(Xb - gm[:, 1:], y - gm[:, 0], groups)
    return b[0], se[0]


def run():
    t0 = time.time()
    sha = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
    pins = record.raw_pins()
    k = contract.POLICY["k_se"]
    print("S3 GAME-SCALE ROOT MAP v5 (read; X2). Link = today's rate minus own to-date mean, team-season means removed from both sides. WALL: which pregame roots move the forecast error of snaps, pass share, sacks per dropback, scrambles per dropback, stably across seasons?")
    print("IF YES (CANDIDATE cells): they queue for S8 in order of swing share, the null count printed beside them (M8). IF NO: the root closes at this scale with its n, SE and ceiling k_se x SE. FAILS WHEN FIXED POINTS < 2/2; the table is then not counted.")
    parts = []
    for s in (2019, 2020, 2021, 2023, 2024, 2025):
        tg = with_roots(team_game_table(s))
        grp = tg.groupby(["season", "team"], sort=False)
        tg["own_sackrate_td"] = grp["sack_rate"].transform(lambda x: x.shift(1).expanding().mean())
        tg["own_scramblerate_td"] = grp["scramble_rate"].transform(lambda x: x.shift(1).expanding().mean())
        parts.append(tg)
    tg = pd.concat(parts, ignore_index=True)
    need = ROOTS + list(LINKS) + list(OWN_TD.values())
    full = tg.dropna(subset=need).reset_index(drop=True)
    rem = tg[tg[need].isna().any(axis=1)]
    reasons = {"first game of team-season (own to-date missing)": int(rem["own_snaps_td"].isna().sum()),
               "opponent's first game (opp to-date missing)": int((rem["own_snaps_td"].notna() & rem["opp_snaps_td"].isna()).sum()),
               "zero dropbacks (rate undefined)": int((rem["own_snaps_td"].notna() & rem["opp_snaps_td"].notna() & (rem["dropbacks"] == 0)).sum()),
               "env null (roof/surface/gametime)": int((rem["own_snaps_td"].notna() & rem["opp_snaps_td"].notna() & (rem["dropbacks"] > 0) & rem[["indoors", "grass", "hour"]].isna().any(axis=1)).sum()),
               "AVAIL unknown (no prior starters)": int((rem["own_snaps_td"].notna() & rem["opp_snaps_td"].notna() & (rem["dropbacks"] > 0) & rem[["indoors", "grass", "hour"]].notna().all(axis=1) & rem[["qb_out", "ol_out", "top2_out"]].isna().any(axis=1)).sum())}
    print(f"team-games {len(tg)} with every root, link and own to-date mean known {len(full)} remainder {len(rem)}")
    for rname, cnt in reasons.items():
        print(f"  REMAINDER {rname}: {cnt}")
    print(f"  REMAINDER sum of reasons {sum(reasons.values())} (want {len(rem)}; any difference is a row with two reasons or none, listed next)")
    other = rem[~(rem["own_snaps_td"].isna() | rem["opp_snaps_td"].isna() | (rem["dropbacks"] == 0) | rem[["indoors", "grass", "hour"]].isna().any(axis=1) | rem[["qb_out", "ol_out", "top2_out"]].isna().any(axis=1))]
    for _, rr in other.iterrows():
        print(f"  REMAINDER unclassified {rr['game_id']} {rr['team']}: " + " ".join(f"{c}=NaN" for c in need if pd.isna(rr[c])))
    tag = f"mode full rows {len(full)} fits {ROOTS} sha {sha[:12]} data_version {pins['data_version'][:12]} seed {SEED} k_se {k}"
    print("TAG", tag)
    groups = (full["season"].astype(str) + "_" + full["team"]).to_numpy()
    X = full[ROOTS].to_numpy(dtype=float)
    C = np.corrcoef(X, rowvar=False); n = len(full)
    print(f"DEPENDENCE among roots (raw, pooled), n {n}, SE of r ~ (1-r^2)/sqrt(n-2): pairs with |r| >= {k} SE listed")
    for i in range(len(ROOTS)):
        for j in range(i + 1, len(ROOTS)):
            r = C[i, j]; se = (1 - r * r) / np.sqrt(n - 2)
            if abs(r) >= k * se:
                print(f"  {ROOTS[i]} x {ROOTS[j]}: r {r:+.3f} SE {se:.3f}")
    seasons = sorted(full["season"].unique())
    kr_ok = True
    for link in LINKS:
        xo = full[[OWN_TD[link]]].to_numpy(dtype=float); yo = full[link].to_numpy(dtype=float)
        b, se, _, _ = ols_cluster(xo, yo, groups)
        signs = []
        for s in seasons:
            m = (full["season"] != s).to_numpy()
            bb, _, _, _ = ols_cluster(xo[m], yo[m], groups[m])
            signs.append(int(np.sign(bb[0])))
        ok = b[0] > k * se[0] and all(sg > 0 for sg in signs)
        kr_ok = kr_ok and ok
        print(f"KNOWN-RIGHT persistence {link} on {OWN_TD[link]}: slope {b[0]:+.4f} SE {se[0]:.4f} folds {''.join('+' if x > 0 else '-' for x in signs)} {'PASS' if ok else 'FAIL'}")
    real = {link: words(full, link) for link in LINKS}
    rng = np.random.default_rng(SEED)
    Xs = X.copy()
    for gname in np.unique(groups):
        idx = np.flatnonzero(groups == gname)
        Xs[idx] = Xs[rng.permutation(idx)]
    null_c = 0; null_pooled = 0; cells = 0
    for link in LINKS:
        ws = words(full, link, X_override=Xs)
        cells += len(ws); null_c += sum(1 for w in ws if w["word"] == "CANDIDATE"); null_pooled += sum(1 for w in ws if w["irreducible"])
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(k / sqrt(2))))
    expect = cells * p; sd = sqrt(cells * p * (1 - p))
    kw_ok = null_pooled <= expect + k * sd
    print(f"KNOWN-WRONG shuffled roots within team-season: pooled-k_se cells {null_pooled} of {cells} against nominal {expect:.2f} +- {k} x {sd:.2f} (tests the clustered SE; seed {SEED}) {'PASS' if kw_ok else 'FAIL'} | under the full word rule the null reads CANDIDATE {null_c} of {cells} (M8; read beside the table's CANDIDATE count)")
    print(f"FIXED POINTS {int(kr_ok) + int(kw_ok)}/2")
    if not (kr_ok and kw_ok):
        print("FIXED POINTS FAIL: the table below is NOT COUNTED (M3); it prints for the record only.")
    print("ROOT MAP v5 (game scale) | root | var | link | n | pooled slope | clustered SE | ceiling k_se x SE | swing share | IRREDUCIBLE | per-fold slope (SE) 2019,20,21,23,24,25 | word")
    summary = {}
    for link in LINKS:
        for c in real[link]:
            root = next((g for g, vs in ROOT_VARS.items() if c["var"] in vs), "SCHEME")
            word = c["word"]
            mech = "" if c["held"] is None else f" | today's level with own history held: slope {c['held'][0]:+.5f} SE {c['held'][1]:.5f}"
            folds = " ".join(f"{fb:+.4f}({fs:.4f})" for fb, fs in c["folds"])
            print(f"  {root:6s} {c['var']:24s} {link:13s} n {c['n']} slope {c['slope']:+.5f} SE {c['se']:.5f} ceiling {k * c['se']:.5f} share {c['share']:.4f} {'IRREDUCIBLE' if c['irreducible'] else 'reducible'} folds {folds} {word}{mech}")
            summary[word] = summary.get(word, 0) + 1
    print(f"WORDS {summary} | null CANDIDATE {null_c} of {cells} | {tag} | wall {time.time() - t0:.0f}s")
    print("READ THIS: paste the whole printout back. The word rule is the one in RUBRIC section 2 after this landing's edit; the null count is read beside the CANDIDATE count; MECHANISM is assigned by the printed own-history-held test.")


if __name__ == "__main__":
    run()
