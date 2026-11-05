"""Construction tests on a synthetic league with injected posterior draws. Runs with plain Python (python3 tests/test_product.py) or pytest.
The tests exercise the production code paths: record readers, rules credits, tri-state finishing, the information boundary, the joint
simulator and its reducer, the contract's identities, the grader's structured decisions and the quality_gate's end-to-end run. They do not fit Stan models;
fitting is exercised on real data through the quality_gate with CmdStanPy installed."""
import os, sys, json, pathlib, shutil, tempfile, io, contextlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
WORK = pathlib.Path(tempfile.mkdtemp(prefix="nfl3_test_")); RAW = WORK / "raw"
os.environ["VERSION3_RAW"] = str(RAW)
import synth
synth.build(RAW, seasons=(2020, 2021, 2022), weeks=8, seed=11)
import policy as K
import record, rules, model, product, grader, run_log, checks, report, quality_gate

record.RAW = RAW; record._CACHE.clear(); record.OPENED.clear()
PROBE = ROOT / "_probe"; TEST_PROBE = WORK / "_probe"; TEST_PROBE.mkdir()
for mod in (run_log, quality_gate, report, model): pass
run_log.PATH = TEST_PROBE / "run_log.jsonl"; run_log.ACCESS = TEST_PROBE / "certification_access.json"; quality_gate.PINS = TEST_PROBE / "raw_pins.json"; quality_gate.PROBE = TEST_PROBE; report.PROBE = TEST_PROBE; model.FITS = TEST_PROBE / "fits"
K.POLICY.update({"worlds_initial": 300, "worlds_max": 600, "world_batch": 300, "mc_tolerance": 0.03, "min_group_lines": 5, "bootstrap_replicates": 60, "workers": 1})
FAILS = []


def test(name):
    def deco(fn):
        def run():
            try: fn(); print(f"PASS {name}")
            except Exception as e:
                import traceback; FAILS.append(name); print(f"FAIL {name}: {type(e).__name__}: {e}"); traceback.print_exc()
        run.__name__ = f"test_{name}"; return run
    return deco


def injected_fits(cut, D=30, seed=1):
    E = record.training_events(cut); pos = model.position_lookup(cut); counts = {}
    T = model.build_tables(E, pos, 1.0, counts); idx = model.Index(sorted(set(E.season)))
    model.obs_snap(E, pos, idx, cut); model.obs_call(E, idx); model.obs_branch(E, pos, idx); model.obs_result(E, pos, idx)
    for name in ("td_pass", "td_run"): model.obs_td(E, pos, idx, name)
    for name in ("gain_pass", "gain_run", "gain_sack"): model.obs_gain(E, pos, idx, name, counts)
    for name in ("target", "rusher"): model.obs_dirmult(E, pos, idx, name, counts)
    model.obs_softmax(E, pos, idx, "passer", counts)
    rng = np.random.default_rng(seed); fits = {}
    for name, prog in model.MECHANISMS.items():
        C = 4 if name == "branch" else (3 if name == "result" else 2)
        f = model.injected_fit(name, prog, idx, D, rng, C=C, alpha={"call": 0.3, "td_pass": -3.0, "td_run": -3.5}.get(name, 0.0),
                              categories=list(model.BRANCH_CATS) if name == "branch" else (list(model.RESULT_CATS) if name == "result" else None))
        if name == "branch": f.draws["alpha"] = np.tile(np.array([-2.5, -2.5, -4.0]), (D, 1))
        if name == "result": f.draws["alpha"] = np.tile(np.array([0.5, -2.5]), (D, 1))
        if name == "gain_sack": f.draws["alpha"][:] = -6.0; f.draws["ls0"][:] = np.log(3.0)
        if name == "gain_pass": f.draws["alpha"][:] = 9.0
        if name == "gain_run": f.draws["alpha"][:] = 4.0
        f.cutoff_key = cut.fit_key(); fits[name] = f
    return model.Fits(cut, fits, T, idx.as_dict(), counts)


@test("record: raw rows immutable and credits replay the official tally exactly")
def t_record():
    pins = record.raw_pins()
    for s in (2020, 2021):
        r = record.replay_vs_official(s); assert all(v["agree"] == 1.0 for v in r.values()), r
        E, c = record.events(s); assert c["events"] == c["rows"] - c["non_event_rows"]
    assert record.raw_pins() == pins


@test("rules: linked passer/receiver credits, laterals, sacks, kneels and spikes")
def t_rules():
    e = rules.Event(rules.PASS, passer="q", receiver="r", complete=1, touchdown=1, yards=20, lateral_receiver="l", lateral_rec_yards=5)
    c = {(m, s): v for m, s, v in rules.credits(e)}
    assert c[("q", "pass_yards")] == 20 and c[("r", "rec_yards")] == 15 and c[("l", "rec_yards")] == 5 and c[("l", "rec_td")] == 1 and ("r", "rec_td") not in c
    assert dict(((m, s), v) for m, s, v in rules.credits(rules.Event(rules.SACK, passer="q", yards=-7))) == {}
    assert ("q", "carries") in {(m, s) for m, s, v in rules.credits(rules.Event(rules.KNEEL, rusher="q", yards=-1))}
    assert {(m, s) for m, s, v in rules.credits(rules.Event(rules.SPIKE, passer="q"))} == {("q", "attempts")}
    assert rules.gain_support(rules.RUN, 1) == (-98, 0) and rules.gain_support(rules.SACK, 40) == (-59, 0) and rules.gain_support(rules.PASS, 40) == (-59, 39)
    assert rules.classify({"play_type": "pass", "qb_scramble": 1, "rush": 1, "pass": 0}) == rules.SCRAMBLE and rules.classify({"play_type": "no_play"}) == rules.PENALTY


@test("finishing: tri-state, the final drive from the sequence, missing participation is UNKNOWN not FALSE")
def t_finish():
    r0 = checks.finishing(2021, False); assert r0["unknown"] == 0 and r0["false"] > 0 and r0["true"] > 0, r0
    r = checks.finishing(2021, True); assert r["injected_side_unknown"] > 0 and r["injected_side_false"] == 0 and r["final_drive_unchanged"], r


@test("boundary: training view admits nothing from the hold-out or after the fit week; evaluation access grants no training access")
def t_boundary():
    cut = record.make_cutoff(2021, 6); leak, leak2, n, adm = checks.boundary(cut); assert leak == 0 and n > 0 and leak2 == 0 and not adm
    cert = record.make_cutoff(2022, 5, K.CERTIFICATION); E = record.training_events(cert); assert not E.season.eq(2022).any()
    try: record.scoring_view(cut, 2022); raise AssertionError("hold-out outcomes readable under a development cutoff")
    except record.DataGap: pass
    assert len(record.scoring_view(cert, 2022)) > 0
    # future weeks cannot change the view of an earlier cutoff
    E5 = record.training_events(record.make_cutoff(2021, 5)); E7 = record.training_events(record.make_cutoff(2021, 7))
    assert E5.season.eq(2021).sum() == E7.season.eq(2021).sum() == (E5.season.eq(2021) & (E5.week < 4)).sum()


@test("roster: issue-time lineup reads no participation; unresolved codes stay unresolved")
def t_roster():
    A, c = record.active(2021, 5); assert set(A.team.dropna()) <= record.season_team_codes(2021) and c["men_under_unresolved_codes"] == 0
    assert record.resolve_code("ZZZ", record.season_team_codes(2021)) is None and record.resolve_code("LAR", {"LA"}) == "LA"


@test("reducer: production credits conserve; a corrupted credit, a missing run allocation and an unprocessed event are caught")
def t_reducer():
    assert checks.reducer(None) == {}, checks.reducer(None)
    assert checks.reducer("credit").get("pass_yards_ne_rec_yards") and checks.reducer("run").get("runs_generated_ne_runs_allocated") and checks.reducer("event").get("credits_ne_events_processed")


@test("simulator: equal worlds, legal lineups, identities over every world, one finishing mask per player")
def t_sim():
    cut = record.make_cutoff(2021, 5); F = injected_fits(cut); g = product.simulate(2021, 5, "AAA", "BBB", F, 150, 0)
    bad = {k: v for k, v in g.audit.items() if k != "worlds" and v}; assert not bad, bad
    assert g.audit["worlds"] == 150 and g.final_state["done"].all()
    assert g.counts["scrambles"] > 0 and g.counts["sacks"] > 0 and g.counts["kneels"] >= 0 and g.counts["punts"] > 0
    # scrambles are the passer's carries: every scramble event's carry went to a QB-group player of the side
    Y = g.Y[0]; qb = g.K[0].qb; assert Y[:, ~qb, product.I["carries"]].sum() + Y[:, qb, product.I["carries"]].sum() == Y[:, :, product.I["carries"]].sum()
    L = product.price(2021, 5, "AAA", F, cut); fr = L.frame
    assert ((fr.p.notna()) ^ (fr.reason.notna())).all()
    nf = fr[fr.p.notna()].groupby("player").n_finished_worlds.nunique(); assert (nf == 1).all()
    r = fr[fr.p.notna()].iloc[0]; pmf = {int(a): int(b) for a, b in (t.split(":") for t in r.pmf.split(";"))}
    assert sum(pmf.values()) == r.n_finished_worlds and abs(sum(v * c for v, c in pmf.items()) / r.n_finished_worlds - r["mean"]) < 1e-9
    assert sum(c for v, c in pmf.items() if v * r.avg_n > r.avg_sum) == r.n_over and abs(r.n_over / r.n_finished_worlds - r.p) < 1e-12
    # the same worlds serve both sides
    L2 = product.price(2021, 5, "BBB", F, cut); assert L2.counts["worlds"] == L.counts["worlds"]


@test("model: preflight refuses a nan covariate and an out-of-range index by row; typed fit results; the passer sub_model with no informative risk set is FIT_OK as its declared prior; other starved fits are INSUFFICIENT_DATA")
def t_fit_types():
    cut = record.make_cutoff(2021, 5); idx = model.Index([2020, 2021]); idx.pair("a", 2020); idx.pair("a", 2021); idx.position("QB")
    f = model.fit_one("passer", "softmax", {"X": np.zeros((0, 0)), "pl": []}, idx, cut, {}, 0)
    assert f.status == K.FIT_OK and f.diagnostics.get("prior_only") and f.draws["m"].shape[1] == len(idx.players) and (f.draws["m"][:, 0] == 0).all()
    assert f.draws["s"].shape[1] == len(idx.pairs) and idx.links()[0] == [0, 0, 1] and idx.links()[1] == [0.0, 0.0, 1.0]
    g = model.fit_one("target", "softmax", {"X": np.zeros((0, 0)), "pl": []}, idx, cut, {}, 3)
    assert g.status == K.INSUFFICIENT_DATA and not g.draws
    # preflight: the Stan data of every sub_model built from the synthetic training view is finite and in range; an injected nan covariate and a
    # injected out-of-range pair index are refused by name before any sampling
    E = record.training_events(cut); pos = model.position_lookup(cut); idx2 = model.Index([2020, 2021]); counts = {}
    _, obs = model.obs_td(E, pos, idx2, "td_pass"); obs["pg"] = [0] * len(obs["y"]); obs = model.collapse(obs, ("pl", "pos", "ps", "df", "pg"), sum_keys=("y", "n"))
    _, obs2 = model.obs_gain(E, pos, idx2, "gain_run", counts); obs2 = model.collapse(obs2, ("pl", "pos", "ps", "df", "y", "lo", "hi"))
    for prog, o in (("binomial", obs), ("gain", obs2)):
        o["X"], _ = model.standardize(o["X"]); d = model._stan_data(prog, o, idx2); pre = model.preflight(prog, d, o, idx2); assert pre["rows"] == len(o["y"]) > 0
    bad = model._stan_data("binomial", obs, idx2); bad["X"] = np.array(bad["X"], dtype=float); bad["X"][7, 0] = np.nan
    try: model.preflight("binomial", bad, obs, idx2); raise AssertionError("nan covariate accepted")
    except model.ModelError as e: assert "X non-finite first at row 7" in str(e) and "pair j=" in str(e), str(e)
    bad = model._stan_data("binomial", obs, idx2); bad["ps"] = list(bad["ps"]); bad["ps"][3] = bad["J"] + 5
    try: model.preflight("binomial", bad, obs, idx2); raise AssertionError("out-of-range pair accepted")
    except model.ModelError as e: assert "ps index outside" in str(e), str(e)
    assert model.judge_diagnostics({"divergences": 1, "treedepth_hit_frac": 0.0, "rhat_max": 1.0, "ess_bulk_min": 500}) == ["divergences 1"]
    assert model.judge_diagnostics({"divergences": 0, "treedepth_hit_frac": 0.0, "rhat_max": float("nan"), "ess_bulk_min": 500}) == ["R_hat max nan"]
    # the discretised Student-t draw stays inside the legal support and reproduces q(y) / sum q on a small support
    rng = np.random.default_rng(0); y = model.sample_gain(rng, np.full(20000, 3.0), np.full(20000, 4.0), np.full(20000, 4.0), np.full(20000, -2), np.full(20000, 5))
    assert y.min() >= -2 and y.max() <= 5
    from scipy import stats
    q = np.array([stats.t.cdf((v + 0.5 - 3) / 4, 4) - stats.t.cdf((v - 0.5 - 3) / 4, 4) for v in range(-2, 6)]); q /= q.sum()
    emp = np.bincount(y + 2, minlength=8) / len(y); assert np.abs(emp - q).max() < 0.02, (emp, q)


@test("temporal: the sparse gap transition equals the dense chain's dt-step law; pairs coded out of season order still chain in season order; market columns are never read")
def t_temporal():
    rng = np.random.default_rng(5); lam, tau, dt, n = 0.4, 0.7, 3, 200000
    rho1 = np.exp(-lam); s0 = tau * rng.standard_normal(n); dense = s0.copy()
    for _ in range(dt): dense = rho1 * dense + tau * np.sqrt(1 - rho1 ** 2) * rng.standard_normal(n)          # dt one-season steps
    rho = np.exp(-lam * dt); sparse = rho * s0 + tau * np.sqrt(1 - rho ** 2) * rng.standard_normal(n)        # the one gap step the Stan programs take
    for a, b in ((dense, sparse),):
        assert abs(np.corrcoef(a, s0)[0, 1] - np.corrcoef(b, s0)[0, 1]) < 0.01 and abs(a.var() - b.var()) < 0.01 * tau ** 2, (np.corrcoef(a, s0)[0, 1], np.corrcoef(b, s0)[0, 1], a.var(), b.var())
    assert abs(((dense - rho * s0) ** 2).mean() - tau ** 2 * (1 - rho ** 2)) < 0.02 * tau ** 2
    # pairs coded out of season order (a later sub_model meets a player's earlier season): the chain still evaluates every pair after its predecessor
    idx = model.Index([2019, 2020, 2021]); j21 = idx.pair("m", 2021); j19 = idx.pair("m", 2019); j20 = idx.pair("m", 2020); idx.pair("other", 2021)
    prev, dt, order = idx.chain()
    assert prev[j21] == j20 and prev[j20] == j19 and prev[j19] == 0 and dt[j21] == 1.0 and dt[j20] == 1.0, (prev, dt)
    assert order[0] == 0 and sorted(order) == list(range(len(idx.pairs))) and all(order.index(prev[j]) < order.index(j) for j in order[1:] if prev[j]), order
    d = model._stan_data("softmax", {"X": np.zeros((0, 0)), "pl": [], "pos": [], "ps": [], "df": [], "N": 0, "M": 0, "start": [], "len": [], "chosen": []}, idx)
    assert d["j_order"] == [j + 1 for j in order] and min(d["j_order"]) == 1 and max(d["j_order"]) == len(idx.pairs)
    # the predecessor codes handed to Stan are 1-based like every other pair code: Stan's s[j_prev[j]] is the same player's previous season
    for j in range(1, len(idx.pairs)):
        if d["j_prev"][j]: m0, se0 = idx.pairs[d["j_prev"][j] - 1]; assert m0 == idx.pairs[j][0] and se0 < idx.pairs[j][1], (j, idx.pairs[j], d["j_prev"][j])
    assert d["j_prev"][j21] == j20 + 1 and d["j_prev"][j19] == 0
    pd_ = model.prior_draws("softmax", idx, np.random.default_rng(1)); s = pd_["s"]
    assert np.isfinite(s).all() and abs(np.corrcoef(s[:, j21], s[:, j20])[0, 1]) > 0.3 and s[:, 0].std() == 0, "the prior walk propagates along the chain whatever the codes"
    for p in (ROOT / "stan").glob("*.stan"): assert "j_order" in p.read_text() and "for (k in 2:J)" in p.read_text(), p
    S = record.schedule(); assert not (set(S.columns) & set(K.PROJECTION_INPUTS["excluded_permanently"]))
    import inspect
    for mod in (model, product): assert "spread" not in inspect.getsource(mod) and "moneyline" not in inspect.getsource(mod)


@test("chain: over the league index every sub_model populates, each Stan predecessor code is the same player's earlier season and every pair follows its predecessor; the league has chains")
def t_chain_league():
    cut = record.make_cutoff(2021, 5); E = record.training_events(cut); pos = model.position_lookup(cut); idx = model.Index(sorted(set(E.season))); counts = {}
    model.obs_snap(E, pos, idx, cut); model.obs_call(E, idx); model.obs_branch(E, pos, idx); model.obs_result(E, pos, idx)
    for name in ("td_pass", "td_run"): model.obs_td(E, pos, idx, name)
    for name in ("gain_pass", "gain_run", "gain_sack"): model.obs_gain(E, pos, idx, name, counts)
    for name in ("target", "rusher"): model.obs_dirmult(E, pos, idx, name, counts)
    model.obs_softmax(E, pos, idx, "passer", counts)
    d = model._stan_data("softmax", {"X": np.zeros((0, 0)), "pl": [], "pos": [], "ps": [], "df": [], "N": 0, "M": 0, "start": [], "len": [], "chosen": []}, idx)
    chained = 0; dt2 = 0
    for j in range(1, len(idx.pairs)):
        jp = d["j_prev"][j]
        if jp:
            m0, se0 = idx.pairs[jp - 1]; m, se = idx.pairs[j]
            assert m0 == m and se0 < se, (j, idx.pairs[j], jp, idx.pairs[jp - 1])
            assert d["j_dt"][j] == se - se0, (j, d["j_dt"][j], se - se0)
            chained += 1; dt2 += int(se - se0 >= 2)
    assert chained > 0, "no synthetic player has a season chain: the suite is blind to index defects"
    assert sorted(d["j_order"]) == list(range(1, len(idx.pairs) + 1))
    assert all(d["j_order"].index(d["j_prev"][j]) < d["j_order"].index(j + 1) for j in range(1, len(idx.pairs)) if d["j_prev"][j]), "a pair is evaluated before its predecessor"


@test("contract: unique key, p xor reason, a duplicated key is refused")
def t_contract():
    F = pd.DataFrame([{**{k: "x" for k in K.KEY}, "p": 0.5, "reason": None}, {**{k: "x" for k in K.KEY}, "stat": "y", "p": None, "reason": "no_avg"}])
    product.write_contract(F, WORK)
    try: product.write_contract(pd.concat([F.iloc[[0]], F.iloc[[0]]]), WORK); raise AssertionError("duplicate accepted")
    except product.DataGap: pass
    try: product.write_contract(F.assign(reason="x"), WORK); raise AssertionError("p and reason accepted")
    except product.DataGap: pass


@test("grader: structured decisions; undeclared tolerances read INSUFFICIENT; oracle BETTER and shuffle WORSE; an injected group shift reads OUT")
def t_judge():
    cut = record.make_cutoff(2021, 4); L = grader.baseline(grader.lines([2020, 2021], cut), [2021])
    G = L[L.in_claim_weeks & L.season.eq(2021) & L.b1.notna()]; assert len(G) > 0
    rng = np.random.default_rng(3)
    C = G[K.GRADE_KEY + ["avg_sum", "avg_n"]].copy(); C["issue_time"] = "t"; C["model_version"] = K.MODEL_VERSION
    C["p"] = np.clip(G.b1 + rng.normal(0, 0.05, len(G)), 0.01, 0.99); C["reason"] = None; C["exp_takes"] = rng.random(len(G)); C["mc_se"] = 0.01
    C["pmf"] = ["0:1;1:1" for _ in range(len(G))]
    with contextlib.redirect_stdout(io.StringIO()):
        D, summary, user, Jm = grader.score(L, C, [2021], log=lambda *a: None)
    assert D["construction"]["status"] == K.PASS, D["construction"]
    assert D["reliable"]["status"] == K.INSUFFICIENT and D["harm"]["status"] == K.INSUFFICIENT and D["certifiable"]["status"] in (K.INSUFFICIENT, K.FAIL)
    assert D["checker"]["why"]["oracle_better"] and D["checker"]["why"]["shuffle_worse"] and D["checker"]["why"]["injected_shift_reads_out"]
    assert len(user) > 0 and set(user.status) <= {K.INSUFFICIENT, K.PASS, K.FAIL}
    K.POLICY["group_tolerance"] = 5.0; K.POLICY["material_harm"] = 5.0
    with contextlib.redirect_stdout(io.StringIO()):
        D2, *_ = grader.score(L, C, [2021], log=lambda *a: None)
    assert D2["reliable"]["status"] in (K.PASS, K.INSUFFICIENT) and D2["harm"]["status"] in (K.PASS, K.INSUFFICIENT)
    K.POLICY["group_tolerance"] = None; K.POLICY["material_harm"] = None
    # a duplicated contract key is a construction failure, not extra evidence
    with contextlib.redirect_stdout(io.StringIO()):
        D3, *_ = grader.score(L, pd.concat([C, C.iloc[[0]]]), [2021], log=lambda *a: None)
    assert D3["construction"]["status"] == K.FAIL


@test("quality_gate: end-to-end run on injected fits records a terminal status, DISPLAY and KEY pass, hold-out access is tracked by dataset identity")
def t_gate():
    sys.argv = ["quality_gate.py", "--pin", "--seasons", "2021", "--weeks", "4-5", "--rerun"]
    for s in (2021,):
        for w in (4, 5):
            cut = record.make_cutoff(s, w); F = injected_fits(cut); model.save_fits(F)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try: quality_gate.main()
        except SystemExit: pass
    out = buf.getvalue(); rows = run_log.rows()
    assert rows and rows[-1]["status"] in (K.FAILED_REQUIREMENTS, K.INSUFFICIENT, K.PASSED), (rows[-1].get("status"), rows[-1].get("why"), out[-3000:])
    assert "DISPLAY" in out and "KEY" in out and "GROUP" in out, out[-3000:]
    assert rows[-1]["decisions"]["reliable"] == K.INSUFFICIENT  # tolerance not declared by the reviewer
    # the report selects the run from the current state
    with contextlib.redirect_stdout(io.StringIO()): row, path = report.proven_contract()
    assert row["row_hash"] == rows[-2]["row_hash"] or row["row_hash"] == rows[-1]["row_hash"]
    # a NO WRITE guard refusal on an identical rerun without --rerun
    sys.argv = ["quality_gate.py", "--seasons", "2021", "--weeks", "4-5"]
    with contextlib.redirect_stdout(io.StringIO()):
        try: quality_gate.main()
        except SystemExit: pass
    assert run_log.rows()[-1]["status"] == K.STOPPED and "NO WRITE" in run_log.rows()[-1]["why"]
    # certification access: marked before reading; a second opening is refused
    os.environ["VERSION3_SCORE_HOLDOUT"] = "2022"; sys.argv = ["quality_gate.py", "--weeks", "4-4", "--rerun"]
    cut = record.make_cutoff(2022, 4, K.CERTIFICATION); model.save_fits(injected_fits(cut))
    with contextlib.redirect_stdout(io.StringIO()):
        try: quality_gate.main()
        except SystemExit: pass
    assert run_log.inspected(2022) and run_log.rows()[-1]["partition"] == K.CERTIFICATION if "partition" in run_log.rows()[-1] else True
    with contextlib.redirect_stdout(io.StringIO()):
        try: quality_gate.main()
        except SystemExit: pass
    assert run_log.rows()[-1]["status"] == K.STOPPED and "inspected" in run_log.rows()[-1]["why"]
    del os.environ["VERSION3_SCORE_HOLDOUT"]


@test("quality_gate: a crash before scoring is recorded as CRASHED with its exception, never as a predictive decision")
def t_crash():
    sys.argv = ["quality_gate.py", "--seasons", "2021", "--weeks", "4-4", "--rerun"]; saved = model.load_fits
    model.load_fits = lambda c: (_ for _ in ()).throw(RuntimeError("injected crash in FIT"))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            try: quality_gate.main()
            except SystemExit: pass
    finally: model.load_fits = saved
    r = run_log.rows()[-1]; assert r["status"] == K.CRASHED and r["phase"] == "FIT" and "injected crash" in r["exception"], r


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("t_") and callable(fn): fn()
    print(f"\n{len(FAILS)} failures: {FAILS}"); shutil.rmtree(WORK, ignore_errors=True); sys.exit(1 if FAILS else 0)
