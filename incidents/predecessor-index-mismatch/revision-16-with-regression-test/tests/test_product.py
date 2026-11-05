"""Construction tests on a synthetic league with injected posterior draws. Runs with plain Python (python3 tests/test_product.py) or pytest.
The tests exercise the production code paths: record readers, rules credits, tri-state finishing, the information boundary, the joint
simulator and its reducer, the contract's identities, the grader's structured decisions and the quality_gate's end-to-end run. They do not fit Stan models;
fitting is exercised on real data through the quality_gate with CmdStanPy installed."""
import os, sys, json, pathlib, shutil, tempfile, io, contextlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
WORK = pathlib.Path(tempfile.mkdtemp(prefix="nfl3_test_")); RAW = WORK / "raw"
os.environ["VERSION3_RAW"] = str(RAW); os.environ["VERSION3_IN_SUITE"] = "1"
import synth
synth.build(RAW, seasons=(2019, 2020, 2021, 2022), weeks=8, seed=11)
import policy as K
import record, rules, model, product, grader, run_log, checks, report, quality_gate

record.RAW = RAW; record._CACHE.clear(); record.OPENED.clear()
PROBE = ROOT / "_probe"; TEST_PROBE = WORK / "_probe"; TEST_PROBE.mkdir()
for mod in (run_log, quality_gate, report, model): pass
quality_gate.LOCK = TEST_PROBE / "suite_lock.json"; run_log.PATH = TEST_PROBE / "run_log.jsonl"; run_log.ACCESS = TEST_PROBE / "certification_access.json"; quality_gate.PINS = TEST_PROBE / "raw_pins.json"; quality_gate.PROBE = TEST_PROBE; report.PROBE = TEST_PROBE; model.FITS = TEST_PROBE / "fits"
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
    """Planted posterior draws over the league's own shared index, each carrying the sha of the input the real fit would consume, so the quality_gate's
    input-keyed resume (R9) accepts them as that cutoff's sub_models."""
    E, pos, idx, T, counts, pending = model.build_observations(cut)
    shas = {name: model.input_hash(model._stan_data(prog, obs, idx)) for name, prog, obs, tr, n, extra in pending}
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
        f.cutoff_key = cut.fit_key(); f.input_sha = shas[name]; fits[name] = f
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
    assert model.judge_diagnostics({"converged": False, "log_marginal": 1.0, "message": "x"})[0].startswith("outer optimisation not converged")
    assert model.judge_diagnostics({"converged": True, "log_marginal": float("nan")}) == ["log marginal not finite"]
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
    S = record.schedule(); assert not (set(S.columns) & set(K.PROJECTION_INPUTS["excluded_permanently"]))
    import inspect
    for mod in (model, product): assert "spread" not in inspect.getsource(mod) and "moneyline" not in inspect.getsource(mod)


@test("oracle: the league exercises every declared branch; every program's reference arrays round-trip; an injected 0-based predecessor is refused")
def t_oracle():
    cut = record.make_cutoff(2021, 6); E, pos, idx, T, counts, pending = model.build_observations(cut)
    # every branch the builders count is declared, and every declared branch without a quality_gate guard is non-zero on the league (R6)
    undeclared = [k for k in counts if k not in model.BRANCHES and k not in ("training_events", "personnel_source")]
    assert not undeclared, f"counts not declared in model.BRANCHES: {undeclared}"
    zero = [k for k, guard in model.BRANCHES.items() if guard is None and not counts.get(k)]
    assert not zero, f"declared branches the league never exercises: {zero} (counts {counts})"
    # the league's irregularities, each proven by a record count
    c0 = record.counts(2019); c1 = record.counts(2021)
    assert c0["schedule"]["schedule_codes_resolved_to_pbp"] == {"OAK": "LV"}, c0["schedule"]
    assert c0["finished"]["finished_unknown"] > 0 and c1["finished"]["finished_unknown"] == 0, (c0["finished"], c1["finished"])
    assert c1["participation"]["penalty_snaps_with_offensive_unit"] > 0 and c1["participation"]["no_play_rows_with_file_side_disagreeing"] > 0, c1["participation"]
    assert c1["snaps"]["rows_without_gsis_id"] > 0 and c1["snaps"]["disagree_rows"] > 0, c1["snaps"]
    prev, dt, order = idx.chain(); chained = sum(1 for j in range(1, len(idx.pairs)) if prev[j]); gaps2 = sum(1 for j in range(1, len(idx.pairs)) if prev[j] and dt[j] >= 2)
    assert chained > 0.3 * len(idx.pairs) and gaps2 > 0, (chained, gaps2, len(idx.pairs))
    # a pair first coded by a sub_model other than snap (a player whose only known sets are missing) exists: encounter order differs from season order
    assert any(prev[j] > j for j in range(1, len(idx.pairs))), "no pair is coded after its successor: the league does not exercise encounter-order coding"
    # every program: the serialised data passes preflight and every predecessor code resolves to the same unit's earlier period (R4, R5)
    for name, program, obs, tr, n, extra in pending:
        d = model._stan_data(program, obs, idx); pre = model.preflight(program, d, obs, idx)
        for j in range(1, d["J"]):
            if d["j_prev"][j]: m0, se0 = idx.pairs[d["j_prev"][j] - 1]; assert m0 == idx.pairs[j][0] and se0 < idx.pairs[j][1], (name, j, idx.pairs[j], d["j_prev"][j])
        bad = dict(d); bad["j_prev"] = [max(p - 1, 0) for p in d["j_prev"]]   # the 0-based code of revision 1-revision 10 (the predecessor-index mismatch)
        try: model.preflight(program, bad, obs, idx); raise AssertionError(f"{name}: a 0-based predecessor code passed the preflight")
        except model.ModelError as e: assert "state nan" in str(e) or "chain" in str(e), (name, str(e))
        bad2 = dict(d); bad2["j_order"] = list(range(1, d["J"] + 1))   # evaluation in code order (the revision 1-revision 8 loop)
        try: model.preflight(program, bad2, obs, idx); assert all(d["j_prev"][j] < j + 1 for j in range(d["J"])), f"{name}: code-order evaluation passed although a predecessor is coded later"
        except model.ModelError: pass


@test("estimator oracle: on data generated from known spreads and a known chain, the estimates land inside their standard errors and the unit states' conditional intervals cover at nominal; an injected broken chain is not recovered")
def t_estimator():
    import estimate
    cut = record.make_cutoff(2021, 6); E, pos, idx, T, counts, pending = model.build_observations(cut)
    name, prog, obs, tr, n, extra = next(p_ for p_ in pending if p_[0] == "td_pass"); d = model._stan_data(prog, obs, idx)
    d = dict(d); d["n"] = [int(v) * 20 + 5 for v in d["n"]]   # more trials per row: the oracle measures recovery, not the league's thinness
    lay = estimate.Layout(prog, d); rng = np.random.default_rng(7)
    truth = {"log_sigma_pos0": np.log(0.6), "log_tau0": np.log(0.5), "log_lambda": np.log(0.4), "log_sigma_def0": np.log(0.3)}
    th = estimate.Theta(prog, d, 1, lay.G); tv = th.init(d)
    for k, v in truth.items(): tv[th.i[k]] = v
    # the latent truth: scalar effects from their priors, the states along the chain in evaluation order
    z = np.zeros(lay.dim); z[lay.cols("alpha")] = -2.5
    z[lay.cols("a_pos")] = 0.6 * rng.standard_normal(lay.G - 1); z[lay.cols("v_def")] = 0.3 * rng.standard_normal(lay.T - 1)
    prev = np.asarray(d["j_prev"]); dt = np.asarray(d["j_dt"], float); s_ = np.zeros(d["J"]); tau, lam = 0.5, 0.4
    for j in [jj - 1 for jj in d["j_order"]][1:]:
        if prev[j]: rho = np.exp(-lam * dt[j]); s_[j] = rho * s_[prev[j] - 1] + tau * np.sqrt(1 - rho ** 2) * rng.standard_normal()
        else: s_[j] = tau * rng.standard_normal()
    z[lay.cols("s")] = s_[1:]
    eta = (lay.A @ z); p = 1 / (1 + np.exp(-eta)); nn = np.asarray(d["n"]); d["y"] = [int(v) for v in rng.binomial(nn, p)]
    draws, diag = estimate.fit(prog, d, K.MODEL["estimator"], np.random.default_rng(1), with_se=True)
    assert diag["converged"], diag
    off = []
    for k, v in truth.items():
        est, se = diag["theta"][k], diag["hyper_se"][k]; off.append((k, round(est, 3), round(v, 3), round(se, 3)))
        assert np.isfinite(se) and abs(est - v) < 3 * max(se, 0.05), (k, est, v, se)
    # unit-state coverage at nominal: the true state inside the conditional 95% interval for about 95% of pairs
    S = draws["s"][:, 1:]; lo, hi = np.percentile(S, [2.5, 97.5], axis=0); cover = np.mean((s_[1:] >= lo) & (s_[1:] <= hi))
    assert 0.88 <= cover <= 0.995, (cover, off)
    print(f"      recovery (name, estimate, truth, se): {off}; unit-state 95% coverage {cover:.3f}; {diag['seconds']}s, {diag['evaluations']} evaluations")
    # an injected broken chain (every predecessor code shifted) must not recover the persistence: it is refused by the preflight before any fit
    bad = dict(d); bad["j_prev"] = [max(pp - 1, 0) for pp in d["j_prev"]]
    try: model.preflight(prog, bad, obs, idx); raise AssertionError("a broken chain passed the preflight")
    except model.ModelError: pass


@test("end to end: every sub_model estimated on the league prices a slate through the simulator with every identity at zero")
def t_estimated_pricing():
    cut = record.make_cutoff(2021, 4); model.FITS = TEST_PROBE / "fits_estimated"; saved = dict(K.MODEL["min_obs"]); K.MODEL["min_obs"]["gain"] = 100   # the league is small; the floor is the reviewer's for the record
    try:
        with contextlib.redirect_stdout(io.StringIO()): F = model.fit_all(cut, log=lambda *a: None)
    finally: K.MODEL["min_obs"].update(saved)
    st = F.status(); assert all(v == K.FIT_OK for v in st.values()), st
    assert all((f.draws["m"] == 0).all() and (f.draws["sigma_m"] == 0).all() for f in F.fits.values() if f.ok()), "the unit constant is absorbed into the first state (R2)"
    g = product.simulate(2021, 4, "AAA", "BBB", F, 120, 0); bad = {k: v for k, v in g.audit.items() if k != "worlds" and v}; assert not bad, bad
    L = product.price(2021, 4, "AAA", F, cut); fr = L.frame; assert ((fr.p.notna()) ^ (fr.reason.notna())).all() and fr.p.notna().sum() > 0
    print(f"      sub_models: { {k: (v, F.fits[k].diagnostics.get('seconds')) for k, v in st.items()} }")
    model.FITS = TEST_PROBE / "fits"


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
    sys.argv = ["quality_gate.py", "--pin", "--lock", "--seasons", "2021", "--weeks", "4-5", "--rerun"]
    for s in (2021,):
        for w in (4, 5):
            cut = record.make_cutoff(s, w); F = injected_fits(cut); model.save_fits(F)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try: quality_gate.main()
        except SystemExit: pass
    out = buf.getvalue(); rows = run_log.rows()
    assert rows and rows[-1]["status"] in (K.FAILED_REQUIREMENTS, K.INSUFFICIENT, K.PASSED), (rows[-1].get("status"), rows[-1].get("why"), out[-3000:])
    assert "DISPLAY" in out and "KEY" in out and "GROUP" in out and "DataGap   LOCK" in out, out[-3000:]
    assert rows[-1]["decisions"]["reliable"] == K.INSUFFICIENT  # tolerance not declared by the reviewer
    # the checker revision_stage (R9, R11): every stage's seconds and every check's injected_fault result are on the row; a sub_model names the input it consumed
    r = rows[-1]; assert {"LINT", "RAW", "LOCK", "CHECKS", "FIT", "PRICE", "JUDGE"} <= set(r["timings"]) and all(v >= 0 for v in r["timings"].values()), r["timings"]
    assert r["checks"] and all({"name", "ok", "can_fail", "seconds"} <= set(c) for c in r["checks"]), r["checks"][:2]
    k = next(iter(r["fits"].values()))["sub_models"]; assert all(len(v["input_sha"]) == 12 for v in k.values()), k
    # a one-byte change in a sub_model's input invalidates the cached sub_model: the resume path refits it (here: refuses, since no sampler is installed)
    cut = record.make_cutoff(2021, 4); E, pos, idx, T, counts, pending = model.build_observations(cut)
    name, prog, obs, tr, n, extra = next(p_ for p_ in pending if p_[0] == "td_pass"); d = model._stan_data(prog, obs, idx)
    d2 = dict(d); d2["y"] = list(d["y"]); d2["y"][0] += 1; assert model.input_hash(d) != model.input_hash(d2)
    assert model.load_sub_model(cut, "td_pass", input_sha=model.input_hash(d)) is not None and model.load_sub_model(cut, "td_pass", input_sha=model.input_hash(d2)) is None
    # the report selects the run from the current state
    with contextlib.redirect_stdout(io.StringIO()): row, path = report.proven_contract()
    assert row["row_hash"] == rows[-2]["row_hash"] or row["row_hash"] == rows[-1]["row_hash"]
    # a changed suite is refused at LOCK until the reviewer re-locks
    (ROOT / "tests" / "_planted.py").write_text("# injected\n")
    try:
        sys.argv = ["quality_gate.py", "--seasons", "2021", "--weeks", "4-5", "--rerun"]
        with contextlib.redirect_stdout(io.StringIO()):
            try: quality_gate.main()
            except SystemExit: pass
        assert run_log.rows()[-1]["status"] == K.STOPPED and run_log.rows()[-1]["why"].startswith("LOCK"), run_log.rows()[-1]
    finally: (ROOT / "tests" / "_planted.py").unlink()
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
    sys.argv = ["quality_gate.py", "--seasons", "2021", "--weeks", "4-4", "--rerun"]; saved = model.build_observations
    model.build_observations = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected crash in FIT"))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            try: quality_gate.main()
            except SystemExit: pass
    finally: model.build_observations = saved
    r = run_log.rows()[-1]; assert r["status"] == K.CRASHED and r["phase"] == "FIT" and "injected crash" in r["exception"], r


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("t_") and callable(fn): fn()
    print(f"\n{len(FAILS)} failures: {FAILS}"); shutil.rmtree(WORK, ignore_errors=True); sys.exit(1 if FAILS else 0)
