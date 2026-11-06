"""evaluate.py - evaluation and governance (Slate Kit module map: evaluate).  Judges only; never produces a forecast.
Scores per row from draws (F7): crps, rank (randomized PIT), coverage80, bias, energy_score, energy_score_nd, pinball, joint_event, shuffled, rank_self.
Losses and gates: deviance (no floor), paired_by_slate, passes_gate; the calibration grid's decile_deviation and noise95.
Verdict provenance: slice_sha.  Procedure harness v2 / exact null B: harness(mode).  Governance: the CHARTER ledger, one definition per name, kit modules only,
decompressed content comparison."""
import os, ast, glob, gzip, hashlib, itertools, json, numpy as np, pandas as pd
from scipy.stats import norm as normal_law, beta as beta_law
from ingest import ROOT, PROJ_DIR, Report
from facts import read_table
# ---------------- scores per row from simulation draws (F7) ----------------
def crps(sample_draws, outcome):
    """Continuous ranked probability score per row: E|X - y| - 1/2 E|X - X'|, exact for the empirical distribution of the draws (rows x draws)."""
    sample_draws = np.sort(np.asarray(sample_draws, float), 1); draw_count = sample_draws.shape[1]; outcome = np.asarray(outcome, float)
    return np.abs(sample_draws - outcome[:, None]).mean(1) - ((2 * np.arange(1, draw_count + 1) - draw_count - 1) * sample_draws).sum(1) / draw_count ** 2
def rank(sample_draws, outcome, random_generator):
    sample_draws = np.asarray(sample_draws, float); outcome = np.asarray(outcome, float)[:, None]
    return (sample_draws < outcome).mean(1) + random_generator.random(sample_draws.shape[0]) * (sample_draws == outcome).mean(1)
def coverage80(sample_draws, outcome):
    lower_bound, upper_bound = np.quantile(sample_draws, 0.1, axis=1), np.quantile(sample_draws, 0.9, axis=1); outcome = np.asarray(outcome, float); return ((outcome >= lower_bound) & (outcome <= upper_bound)).astype(float)
def bias(sample_draws, outcome): return np.asarray(sample_draws, float).mean(1) - np.asarray(outcome, float)
def energy_score(draws_x, draws_y, outcome_1, outcome_2):
    """Energy score per row for paired draws X, Y (rows x draws) at realized (y1, y2): E||Z - z|| - 1/2 E||Z - Z'|| with Z' the next draw (circular)."""
    draws_x, draws_y = np.asarray(draws_x, float), np.asarray(draws_y, float)
    term_1 = np.sqrt((draws_x - np.asarray(outcome_1, float)[:, None]) ** 2 + (draws_y - np.asarray(outcome_2, float)[:, None]) ** 2).mean(1)
    term_2 = np.sqrt((draws_x - np.roll(draws_x, 1, 1)) ** 2 + (draws_y - np.roll(draws_y, 1, 1)) ** 2).mean(1)
    return term_1 - 0.5 * term_2
def energy_score_nd(draw_sets, outcome_sets):
    """Energy score per row for k >= 2 jointly drawn components (list of rows x draws arrays, each already on its declared scale) at realized values ys (list of row vectors):
    E||Z - z|| - 1/2 E||Z - Z'|| with Z' the next draw (circular), Euclidean over the k components.  With k = 2 it is energy_score."""
    draw_sets = [np.asarray(sample_draws, float) for sample_draws in draw_sets]; outcome_sets = [np.asarray(outcome, float) for outcome in outcome_sets]
    if len(draw_sets) < 2 or len(draw_sets) != len(outcome_sets) or len({sample_draws.shape for sample_draws in draw_sets}) != 1 or any(outcome.shape != (draw_sets[0].shape[0],) for outcome in outcome_sets):
        raise SystemExit("energy_score_nd: needs two or more draw arrays of one shape and one realized vector per array - refused")
    term_1 = np.sqrt(sum((sample_draws - outcome[:, None]) ** 2 for sample_draws, outcome in zip(draw_sets, outcome_sets))).mean(1)
    term_2 = np.sqrt(sum((sample_draws - np.roll(sample_draws, 1, 1)) ** 2 for sample_draws in draw_sets)).mean(1)
    return term_1 - 0.5 * term_2
def pinball(quantile_level, pred, outcome): pinball_error = outcome - pred; return np.maximum(quantile_level * pinball_error, (quantile_level - 1) * pinball_error)   # quantile score (pinball loss) per row - one producer
def shuffled(draws_y, random_generator): return np.take_along_axis(np.asarray(draws_y), random_generator.permuted(np.tile(np.arange(np.asarray(draws_y).shape[1]), (np.asarray(draws_y).shape[0], 1)), axis=1), 1)
def joint_event(draws_x, draws_y, outcome_1, outcome_2):
    median_x, median_y = np.median(draws_x, 1)[:, None], np.median(draws_y, 1)[:, None]
    return ((draws_x > median_x) & (draws_y > median_y)).mean(1), ((np.asarray(outcome_1, float) > median_x[:, 0]) & (np.asarray(outcome_2, float) > median_y[:, 0])).astype(float)
def rank_self(sample_draws, random_generator):
    """Randomized PIT of every draw against its own row's draws: pit's formula (D < d).mean + U (D == d).mean evaluated at each draw d, by sorting; one uniform per draw
    (F8 TAIL ATTRIBUTION - JOINT DOWNSIDE EXTENSION)."""
    sample_draws = np.asarray(sample_draws, float); draw_count = sample_draws.shape[1]; sorted_draws = np.sort(sample_draws, 1)
    lower_bound = np.stack([np.searchsorted(sorted_draws[row_number], sample_draws[row_number], "left") for row_number in range(len(sample_draws))]); upper_bound = np.stack([np.searchsorted(sorted_draws[row_number], sample_draws[row_number], "right") for row_number in range(len(sample_draws))])
    return lower_bound / draw_count + random_generator.random(sample_draws.shape) * ((upper_bound - lower_bound) / draw_count)
def f7_check():
    """F7 self-checks: exact CRPS, sorted vs brute-force CRPS, PIT uniformity, 80% coverage, energy score and pinball properties."""
    from scipy.stats import norm
    random_generator = np.random.default_rng(20261003); passed = True
    def check(name, cond, detail): nonlocal passed; passed &= bool(cond); print(f"   {'PASS' if cond else 'FAIL'}  {name}: {detail}")
    crps_value = crps(random_generator.normal(0, 1, (1, 20000)), np.array([0.0]))[0]; expected_crps = 2 * norm.pdf(0) - 1 / np.sqrt(np.pi)
    check("CRPS N(0,1) at 0", abs(crps_value - expected_crps) < 0.005, f"draws {crps_value:.5f} vs exact {expected_crps:.5f}")
    sample_draws = random_generator.poisson(3, (50, 300)).astype(float); outcome = random_generator.poisson(3, 50).astype(float)
    brute = np.array([np.abs(pinball_error - truth_value).mean() - 0.5 * np.abs(pinball_error[:, None] - pinball_error[None, :]).mean() for pinball_error, truth_value in zip(sample_draws, outcome)])
    check("sorted vs brute-force CRPS", np.max(np.abs(crps(sample_draws, outcome) - brute)) < 1e-10, f"max |diff| {np.max(np.abs(crps(sample_draws, outcome) - brute)):.2e}")
    sample_draws = random_generator.poisson(3, (5000, 2000)).astype(float); outcome = random_generator.poisson(3, 5000).astype(float); quantile_level = rank(sample_draws, outcome, random_generator)
    check("PIT uniform, correctly specified Poisson(3)", abs(quantile_level.mean() - 0.5) < 0.01 and abs(quantile_level.std() - 0.2887) < 0.01, f"mean {quantile_level.mean():.4f}, sd {quantile_level.std():.4f}")
    sample_draws = random_generator.normal(10, 3, (5000, 2000)); outcome = random_generator.normal(10, 3, 5000); coverage_rate = coverage80(sample_draws, outcome).mean()
    check("80% coverage, correctly specified Normal", abs(coverage_rate - 0.8) < 0.02, f"{coverage_rate:.4f}")
    draw_count, sample_count = 3000, 1000; latent_1 = random_generator.normal(0, 1, (draw_count, sample_count)); latent_2 = 0.8 * latent_1 + 0.6 * random_generator.normal(0, 1, (draw_count, sample_count))
    term_1 = random_generator.normal(0, 1, draw_count); term_2 = 0.8 * term_1 + 0.6 * random_generator.normal(0, 1, draw_count)
    energy_joint, energy_independent = energy_score(latent_1, latent_2, term_1, term_2).mean(), energy_score(latent_1, shuffled(latent_2, random_generator), term_1, term_2).mean()
    check("energy score prefers true joint over shuffled independence (rho .8)", energy_joint < energy_independent, f"joint {energy_joint:.4f} vs shuffled {energy_independent:.4f}")
    predicted_probability, realized_rate = joint_event(latent_1, latent_2, term_1, term_2); check("joint event calibrated under the true joint", abs(predicted_probability.mean() - realized_rate.mean()) < 0.02, f"simulated {predicted_probability.mean():.4f} vs realized {realized_rate.mean():.4f}")
    max_difference = float(np.max(np.abs(energy_score_nd([latent_1, latent_2], [term_1, term_2]) - energy_score(latent_1, latent_2, term_1, term_2))))
    check("energy_score_nd with 2 components equals energy_score", max_difference <= 1e-12, f"max |diff| {max_difference:.2e}")
    case4_rows, case4_draws, case4_correlation = 2000, 500, 0.5; case4_factor, case4_truth = random_generator.normal(0, 1, (case4_rows, case4_draws)), random_generator.normal(0, 1, case4_rows)
    case4_latents = [np.sqrt(case4_correlation) * case4_factor + np.sqrt(1 - case4_correlation) * random_generator.normal(0, 1, (case4_rows, case4_draws)) for _ in range(4)]; case4_targets = [np.sqrt(case4_correlation) * case4_truth + np.sqrt(1 - case4_correlation) * random_generator.normal(0, 1, case4_rows) for _ in range(4)]
    case4_joint, case4_independent = energy_score_nd(case4_latents, case4_targets).mean(), energy_score_nd([shuffled(latent_matrix, random_generator) for latent_matrix in case4_latents], case4_targets).mean()
    check("4-component energy score prefers true one-factor joint over shuffled independence (rho .5)", case4_joint < case4_independent, f"joint {case4_joint:.4f} vs shuffled {case4_independent:.4f}")
    pinball_prediction, pinball_outcome = np.array([0.0, 1.0, 2.0]), np.array([1.0, 1.0, 0.0]); pinball_passed = (np.array_equal(pinball(0.5, pinball_prediction, pinball_outcome), np.abs(pinball_prediction - pinball_outcome) / 2) and np.isclose(pinball(0.9, 0.0, 1.0), 0.9) and np.isclose(pinball(0.9, 1.0, 0.0), 0.1))
    check("pinball: q .5 is half the absolute error; q .9 under / over", pinball_passed, "exact values")
    print(f"F7 SELF-CHECK: {'ALL PASS' if passed else 'FAILED'}"); return 0 if passed else 1
# ---------------- losses, gates, calibration grid ----------------
def deviance(outcome, mean_value):
    """Poisson deviance with no floor (DEVIANCE FLOOR UNDER D): mean 0 with y > 0 is +inf (a point mass that cannot produce y)."""
    with np.errstate(divide="ignore", invalid="ignore"): return 2 * (np.where(outcome > 0, outcome * np.log(np.where(outcome > 0, outcome, 1) / mean_value), 0.0) - (outcome - mean_value))
def paired_by_slate(baseline_by_slate, candidate_by_slate):
    """Per-slate gain of the candidate over the baseline: mean, standard error, seasons with a positive mean gain, seasons."""
    slate_gains = (baseline_by_slate - candidate_by_slate).dropna(); return slate_gains.mean(), slate_gains.std() / np.sqrt(len(slate_gains)), int((slate_gains.groupby(level=0).mean() > 0).sum()), slate_gains.index.get_level_values(0).nunique()
def passes_gate(mean_gain, standard_error, positive_seasons, season_count): return mean_gain > resolution_z(1) * standard_error and positive_seasons >= season_count - 1   # the observed statistic resolved above 0 at ALPHA_FAMILY
def decile_deviation(p): return np.abs(np.bincount(np.minimum((np.asarray(p) * 10).astype(int), 9), minlength=10) / len(p) - .1).mean()
noise95_memo = {}
def noise95(pool_count):
    """The (1 - ALPHA_FAMILY) quantile of decile_deviation over 200 calibrated uniform samples of pool_count rows (seeded by pool_count; the 200 is a simulation size, its
    own transaction in the ORDER)."""
    if pool_count not in noise95_memo:
        pool_generator = np.random.default_rng(pool_count); noise95_memo[pool_count] = np.percentile([decile_deviation(pool_generator.random(pool_count)) for _ in range(200)], 100 * (1 - ALPHA_FAMILY))
    return noise95_memo[pool_count]
# ---------------- verdict provenance (work order 32) ----------------
def slice_sha(season, week, l_base, l_cand):
    """Content hash of the rows a verdict judged: season, week, l_base, l_cand in file order, written as CSV with 17 significant digits, SHA-256."""
    slate_rows = pd.DataFrame({"season": np.asarray(season), "week": np.asarray(week), "l_base": np.asarray(l_base, float), "l_cand": np.asarray(l_cand, float)})
    return hashlib.sha256(slate_rows.to_csv(index=False, float_format="%.17g").encode()).hexdigest()
# ---------------- procedure harness v2 (HARNESS PROCEDURE v2; exact null B for rows declaring null_b = exact) ----------------
# Per slice: observed gate; tau / sigma; null A (row sign swaps) and null B (season-block sign flips of the centred gain) false-pass rates; power at 25 / 50 / 100% of the
# observed gain; ladder L.  Every random draw for a slice comes from its own generator seeded by sha256("term|position").
# PASS = observed gate AND FP null B <= t (t = min(.05, 1 - .9^(1/L))) AND not resolution-boundary.
NDRAW = 10000
LADDER = {("Q1 attempts", "QB"): 3, ("Q2 completions", "QB"): 2, ("Q3 passing yards", "QB"): 2,
          ("Q2 completions (Q1 season-to-date parent)", "QB"): 2, ("Q3 passing yards (Q1 season-to-date parent)", "QB"): 2}
YARDS_STAGES = ("[rung 3 variance = phi x max(mean, 1)]", "[rung 3z zero-hurdle]")
ROW_FILES = {"f6": "f6_rows_*.csv.gz", "dependence": "f6_dependence*_rows.csv.gz"}
def wall_rows(pattern):
    spine_rows = pd.concat([pd.read_csv(file_name) for file_name in sorted(glob.glob(os.path.join(PROJ_DIR, pattern)))], ignore_index=True)
    spine_rows["term"] = spine_rows.term + " [" + spine_rows.stage + "]"; spine_rows = spine_rows.rename(columns={"l_cand": "l_v1"}); spine_rows["base"], spine_rows["v1"] = 0.0, 1.0; return spine_rows
def load_rows(mode):
    if mode == "spine":
        spine_rows = pd.read_csv(os.path.join(PROJ_DIR, "spine_rows.csv.gz"))
        spine_rows["l_base"] = np.where(spine_rows.loss == "mae", np.abs(spine_rows.y - spine_rows.base), deviance(spine_rows.y.values, spine_rows.base.values)); spine_rows["l_v1"] = np.where(spine_rows.loss == "mae", np.abs(spine_rows.y - spine_rows.v1), deviance(spine_rows.y.values, spine_rows.v1.values))
        return spine_rows
    return wall_rows(ROW_FILES[mode])
def ladder(mode, term, position): return (2 if term.endswith(YARDS_STAGES) else 1) if mode == "f6" else 1 if mode == "dependence" else LADDER.get((term, position), 1)
def seed(term, position): return int.from_bytes(hashlib.sha256(f"{term}|{position}".encode()).digest()[:8], "little")
def stats(input_frame, slate_seasons, seasons):
    draw_mean = input_frame.mean(1); standard_error = input_frame.std(1, ddof=1) / np.sqrt(input_frame.shape[1]); season_means = np.stack([input_frame[:, slate_seasons == s].mean(1) for s in seasons], 1); return draw_mean, standard_error, (season_means > 0).sum(1), len(seasons)
def gate_v(draw_mean, standard_error, positive_seasons, needed_seasons): return (draw_mean > resolution_z(1) * standard_error) & (positive_seasons >= needed_seasons - 1)   # passes_gate, vectorized over null draws
def run_slice(mode, term, position, slice_rows):
    if mode == "spine" and np.allclose(slice_rows.base.values, slice_rows.v1.values): return None
    finite_loss_baseline, finite_loss_candidate = np.isfinite(slice_rows.l_base.values), np.isfinite(slice_rows.l_v1.values); strata = (int((~finite_loss_baseline & ~finite_loss_candidate).sum()), int((~finite_loss_baseline & finite_loss_candidate).sum()), int((finite_loss_baseline & ~finite_loss_candidate).sum()))   # DEVIANCE FLOOR UNDER D
    if strata[2] > 0: return dict(blocked=True, strata=strata)
    slice_rows = slice_rows[finite_loss_baseline & finite_loss_candidate]
    random_generator = np.random.default_rng(seed(term, position))
    slice_rows = slice_rows.sort_values(["season", "week"]).reset_index(drop=True); slate_index = pd.MultiIndex.from_frame(slice_rows[["season", "week"]])
    reference_result = paired_by_slate(slice_rows.groupby(["season", "week"]).l_base.mean(), slice_rows.groupby(["season", "week"]).l_v1.mean())
    codes, uniq = pd.factorize(slate_index); slate_count = len(uniq); slate_seasons = np.array([unique_slate[0] for unique_slate in uniq]); seasons = sorted(set(slate_seasons))
    slate_sizes = np.bincount(codes, minlength=slate_count); row_differences = (slice_rows.l_base - slice_rows.l_v1).values; slate_differences = np.bincount(codes, weights=row_differences, minlength=slate_count) / slate_sizes
    draw_mean, standard_error, positive_seasons, needed_seasons = stats(slate_differences[None, :], slate_seasons, seasons)
    if not (np.isclose(draw_mean[0], reference_result[0]) and np.isclose(standard_error[0], reference_result[1]) and positive_seasons[0] == reference_result[2] and needed_seasons == reference_result[3]): raise SystemExit("harness: fast stats differ from paired_by_slate - refused")
    observed_pass = bool(passes_gate(*reference_result))
    season_differences = np.array([slate_differences[slate_seasons == s].mean() for s in seasons]); within_variance = np.array([slate_differences[slate_seasons == s].var(ddof=1) for s in seasons]); season_sizes = np.array([(slate_seasons == s).sum() for s in seasons])
    sig2 = within_variance.mean(); tau2 = max(0.0, season_differences.var(ddof=1) - (within_variance / season_sizes).mean()); tau_ratio = np.sqrt(tau2 / sig2) if sig2 > 0 else np.nan
    sign_draws = np.empty((NDRAW, slate_count))
    for row_number in range(NDRAW): sign_draws[row_number] = np.bincount(codes, weights=row_differences * random_generator.choice([-1.0, 1.0], size=len(row_differences)), minlength=slate_count) / slate_sizes
    rate_a = float(gate_v(*stats(sign_draws, slate_seasons, seasons)).mean())
    centered_differences = slate_differences - slate_differences.mean(); season_slots = np.array([seasons.index(s) for s in slate_seasons]); sign_flips = random_generator.choice([-1.0, 1.0], size=(NDRAW, len(seasons)))[:, season_slots]
    rate_b = float(gate_v(*stats(centered_differences[None, :] * sign_flips, slate_seasons, seasons)).mean())
    sign_patterns = np.array(list(itertools.product([-1.0, 1.0], repeat=len(seasons))))[:, season_slots]; fpBx = float(gate_v(*stats(centered_differences[None, :] * sign_patterns, slate_seasons, seasons)).mean())   # EXACT NULL B INSTRUMENT
    null_values = slice_rows["null_b"].dropna().unique().tolist() if "null_b" in slice_rows else []
    if null_values and (null_values != ["exact"] or slice_rows["null_b"].isna().any()): raise SystemExit(f"harness: {term} {position} null_b declaration mixed or unknown {null_values} - refused")
    exact = null_values == ["exact"]   # HARNESS v3: declared slices use the exact value, no band
    power_rates = {file_name: float(gate_v(*stats(centered_differences[None, :] * sign_flips + file_name * slate_differences.mean(), slate_seasons, seasons)).mean()) for file_name in (0.25, 0.5, 1.0)}
    ladder_length = ladder(mode, term, position); alpha_level = 1 - (1 - ALPHA_FAMILY) ** (1 / ladder_length); band = 0.0 if exact else resolution_z(1) * np.sqrt(alpha_level * (1 - alpha_level) / NDRAW); rate_v = fpBx if exact else rate_b; boundary = (not exact) and abs(rate_b - alpha_level) < band
    verdict = "HARNESS PASS" if (observed_pass and rate_v <= alpha_level and not boundary) else ("RESOLUTION-BOUNDARY - baseline enters the freeze" if observed_pass and boundary else "HARNESS FAIL - enters the freeze at its baseline")
    return dict(nsl=slate_count, ref=reference_result, obs=observed_pass, ts=tau_ratio, fpA=rate_a, fpB=rate_b, pw=power_rates, L=ladder_length, t=alpha_level, band=band, lad=1 - (1 - rate_v) ** ladder_length, verdict=verdict, strata=strata, fpBx=fpBx, nS=len(seasons), exact=exact)
def show(report, term, position, slice_result):
    if slice_result is None: report.say(f"\n   {term} {position}: v1 = baseline - nothing to test"); return
    if slice_result.get("blocked"): report.say(f"\n   {term} {position}: BLOCKED under D - v1 assigns zero probability to {slice_result['strata'][2]} realized rows the baseline does not (both impossible {slice_result['strata'][0]}, baseline-only {slice_result['strata'][1]}) -> enters at its baseline"); return
    if sum(slice_result["strata"]): report.say(f"\n   [D strata] {term} {position}: both impossible {slice_result['strata'][0]}, baseline-only impossible {slice_result['strata'][1]} excluded from the gate")
    report.say(f"\n   {term} {position}: slates {slice_result['nsl']}, observed {slice_result['ref'][0]:+.5f}+-{slice_result['ref'][1]:.5f} ({slice_result['ref'][2]}/{slice_result['ref'][3]}) gate {'pass' if slice_result['obs'] else 'fail'};  tau/sigma {slice_result['ts']:.2f}")
    exact_note = (f"FP null B exact {int(round(slice_result['fpBx'] * 2 ** slice_result['nS']))}/{2 ** slice_result['nS']} = {slice_result['fpBx']:.5f} (t {slice_result['t']:.4f}; registered exact null B, no band)" if slice_result["exact"]
          else f"FP null B {slice_result['fpB']:.4f} (t {slice_result['t']:.4f}, boundary +-{slice_result['band']:.4f})")
    report.say(f"      FP null A {slice_result['fpA']:.4f};  {exact_note};  power at 25 / 50 / 100% of gain {slice_result['pw'][0.25]:.2f} / {slice_result['pw'][0.5]:.2f} / "
        f"{slice_result['pw'][1.0]:.2f};  ladder L {slice_result['L']} -> {slice_result['lad']:.4f}  -> {slice_result['verdict']}")
def harness(mode):
    """python3 kit.py harness spine | f6 | dependence | invariance | exact"""
    report = Report()
    if mode == "invariance":
        spine_rows = load_rows("dependence"); keys = list(spine_rows.groupby(["term", "position"], sort=False).groups.keys())
        forward_results = {slice_key: run_slice("dependence", slice_key[0], slice_key[1], spine_rows[(spine_rows.term == slice_key[0]) & (spine_rows.position == slice_key[1])]) for slice_key in keys}
        reverse_results = {slice_key: run_slice("dependence", slice_key[0], slice_key[1], spine_rows[(spine_rows.term == slice_key[0]) & (spine_rows.position == slice_key[1])]) for slice_key in reversed(keys)}
        efficiency_rows = wall_rows("f6_dependence_efficiency_rows.csv.gz"); efficiency_keys = list(efficiency_rows.groupby(["term", "position"], sort=False).groups.keys())
        efficiency_results = {slice_key: run_slice("dependence", slice_key[0], slice_key[1], efficiency_rows[(efficiency_rows.term == slice_key[0]) & (efficiency_rows.position == slice_key[1])]) for slice_key in efficiency_keys}
        file_name = lambda slice_result: (slice_result["fpA"], slice_result["fpB"], tuple(slice_result["pw"].values()), slice_result["verdict"])
        order_passed = all(file_name(forward_results[slice_key]) == file_name(reverse_results[slice_key]) for slice_key in keys); subset_passed = all(file_name(efficiency_results[slice_key]) == file_name(forward_results[slice_key]) for slice_key in efficiency_keys)
        report.say(f"kit.py harness invariance (draws {NDRAW}): order invariance {'PASS' if order_passed else 'FAIL'} over {len(keys)} dependence slices;  subset invariance {'PASS' if subset_passed else 'FAIL'} over {len(efficiency_keys)} wall 7 slices")
        return 0 if order_passed and subset_passed else 1
    if mode == "exact":
        report.say("kit.py harness exact null B - enumeration of all 2^S season sign patterns (instrument only; recorded verdicts unchanged)")
        for mode_name in ("spine", "f6", "dependence"):
            spine_rows = load_rows(mode_name); report.say(f"\n===== mode {mode_name}")
            for (term, position), slice_rows in spine_rows.groupby(["term", "position"], sort=False):
                slice_result = run_slice(mode_name, term, position, slice_rows)
                if slice_result is None or slice_result.get("blocked"): continue
                slice_key = int(round(slice_result["fpBx"] * 2 ** slice_result["nS"])); recorded_verdict = slice_result["verdict"].split(" - ")[0]
                expected_verdict = ("PASS" if slice_result["fpBx"] <= slice_result["t"] else "FAIL") if slice_result["obs"] else "gate fail"
                verdict_differs = slice_result["obs"] and ((expected_verdict == "PASS") != (recorded_verdict == "HARNESS PASS"))
                report.say(f"   {term} {position}: seasons {slice_result['nS']}; FP null B Monte Carlo {slice_result['fpB']:.4f}, exact {slice_key}/{2 ** slice_result['nS']} = {slice_result['fpBx']:.5f}; t {slice_result['t']:.4f}; recorded {recorded_verdict}; exact-null-B reading {expected_verdict}" + ("   <- DIFFERS" if verdict_differs else ""))
        report.write(os.path.join(PROJ_DIR, "harness_exact_report.txt")); print("\nwrote proj/harness_exact_report.txt"); return 0
    spine_rows = load_rows(mode)
    report.say(f"kit.py harness {mode} (v2)  rows {len(spine_rows)}; draws {NDRAW}; per-slice seeds; PASS = observed gate AND FP null B <= t AND not resolution-boundary")
    verdict_rows = []
    VFILE = os.path.join(PROJ_DIR, "harness_dependence_verdicts.csv")   # WORK ORDER 47 - DEPENDENCE VERDICT PROVENANCE: a recorded verdict is frozen for the rows it judged
    has_recorded = mode == "dependence" and os.path.exists(VFILE); FROZEN = set()
    OLDV = pd.read_csv(VFILE, dtype=str) if has_recorded else pd.DataFrame(columns=["term", "position", "verdict", "rows_sha256"])
    if OLDV.duplicated(["term", "position"]).any(): raise SystemExit("harness: duplicate recorded dependence verdicts - refused (work order 47)")
    OLDK = {(alpha_level, p): (old_verdict, old_hash) for alpha_level, p, old_verdict, old_hash in OLDV[["term", "position", "verdict", "rows_sha256"]].itertuples(index=False)}
    def merged_verdicts(verdict_rows):
        """WORK ORDER 47: recorded rows first, in their order (frozen ones and ones without rows on disk as recorded; matching ones as re-judged, identical); new slices appended."""
        new_verdicts = pd.DataFrame(verdict_rows, columns=["term", "position", "verdict", "rows_sha256"])
        if not has_recorded: return new_verdicts
        season_sizes = {(alpha_level, p): row_number for row_number, (alpha_level, p) in enumerate(zip(new_verdicts.term, new_verdicts.position))}; merged_rows = []
        for alpha_level, p, old_verdict, old_hash in OLDV[["term", "position", "verdict", "rows_sha256"]].itertuples(index=False):
            if (alpha_level, p) in season_sizes: merged_rows.append(new_verdicts.iloc[season_sizes[(alpha_level, p)]].tolist())
            else:
                if (alpha_level, p) not in FROZEN: print(f"   {alpha_level} {p}: no rows on disk - recorded verdict kept (work order 47)")
                merged_rows.append([alpha_level, p, old_verdict, old_hash])
        for slice_result in new_verdicts.values.tolist():
            if (slice_result[0], slice_result[1]) not in OLDK: merged_rows.append(slice_result); print(f"   {slice_result[0]} {slice_result[1]}: newly judged - {slice_result[2]} (work order 47)")
        return pd.DataFrame(merged_rows, columns=new_verdicts.columns)
    for (term, position), slice_rows in spine_rows.groupby(["term", "position"], sort=False):
        slice_hash = slice_sha(slice_rows.season, slice_rows.week, slice_rows.l_base, slice_rows.l_v1)
        if (term, position) in OLDK and OLDK[(term, position)][1] != slice_hash:
            FROZEN.add((term, position)); report.say(f"\n{term} {position}: FROZEN - recorded verdict '{OLDK[(term, position)][0]}' judged rows {OLDK[(term, position)][1][:12]}; rows on disk {slice_hash[:12]} - not re-judged, recorded verdict kept (verdict policy; work order 47)"); continue
        slice_result = run_slice(mode, term, position, slice_rows); show(report, term, position, slice_result); verdict_rows.append((term, position, "nothing to test" if slice_result is None else ("BLOCKED under D" if slice_result.get("blocked") else slice_result["verdict"]), slice_hash))
        if (term, position) in OLDK and verdict_rows[-1][2] != OLDK[(term, position)][0]: raise SystemExit(f"harness: {term} {position} re-judged on its recorded rows gives '{verdict_rows[-1][2]}', recorded '{OLDK[(term, position)][0]}' - refused (work order 47)")
    report_name = {"spine": "harness_report.txt", "f6": "harness_f6_report.txt", "dependence": "harness_dependence_report.txt"}[mode]
    os.makedirs(PROJ_DIR, exist_ok=True); report.write(os.path.join(PROJ_DIR, report_name)); report.say(f"\nwrote proj/{report_name}")
    verdict_file = report_name.replace("_report.txt", "_verdicts.csv"); merged_verdicts(verdict_rows).to_csv(os.path.join(PROJ_DIR, verdict_file), index=False); print(f"wrote proj/{verdict_file}")
    return 0
# ---------------- governance ----------------
CHARTER = ROOT / "CHARTER.md"; CHARTER_LEDGER = PROJ_DIR / "charter_ledger.json"
def charter_lines(path):
    content_lines = open(path, "rb").read().split(b"\n"); return content_lines[:-1] if content_lines and content_lines[-1] == b"" else content_lines
def lines_digest(content_lines): return hashlib.sha256(b"\n".join(content_lines)).hexdigest()
def ledger_check():
    """(passed, message): CHARTER.md is append-only - it still begins with exactly the lines the ledger accepted."""
    if not CHARTER_LEDGER.exists(): return False, "CHARTER ledger missing - run: python3 kit.py ledger-advance"
    accepted = json.load(open(CHARTER_LEDGER)); content_lines = charter_lines(CHARTER)
    if len(content_lines) < accepted["lines"]: return False, f"CHARTER has {len(content_lines)} lines, ledger accepted {accepted['lines']} - accepted lines lost (revert?)"
    if lines_digest(content_lines[:accepted["lines"]]) != accepted["sha"]: return False, f"CHARTER's first {accepted['lines']} accepted lines changed"
    return True, f"CHARTER append-only: {accepted['lines']} accepted lines intact, {len(content_lines) - accepted['lines']} new"
def ledger_command():
    """python3 kit.py ledger-check: the CHARTER ledger check alone."""
    passed, message = ledger_check(); print(("ok    " if passed else "FAIL  ") + message); return 0 if passed else 1
def ledger_advance():
    """After an append: the ledger accepts every CHARTER line now on disk (refused when accepted lines changed)."""
    if CHARTER_LEDGER.exists():
        passed, message = ledger_check()
        if not passed: print("FAIL  " + message + " - not advanced"); return 1
    content_lines = charter_lines(CHARTER); os.makedirs(PROJ_DIR, exist_ok=True); json.dump(dict(lines=len(content_lines), sha=lines_digest(content_lines)), open(CHARTER_LEDGER, "w"))
    print(f"advanced: ledger accepts {len(content_lines)} CHARTER lines"); return 0
def kit_modules():
    """The kit's module files, read from the roster kit.py declares (MODULES) plus kit.py itself."""
    roster = next(node.value for node in ast.parse(open(ROOT / "kit.py").read()).body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "MODULES" for target in node.targets))
    return sorted(["kit.py"] + [f"{element.value}.py" for element in roster.elts])
def kit_modules_check():
    """(passed, message): every .py file in the folder is a kit module - no retired or one-off script is back."""
    stray = sorted(set(os.path.basename(path) for path in glob.glob(os.path.join(ROOT, "*.py"))) - set(kit_modules()))
    return (False, f"files outside the kit: {stray}") if stray else (True, f"kit modules only: {', '.join(kit_modules())}")
def bound_everywhere(tree):
    """Every name a module binds in any scope: definitions, arguments, assignment and loop targets, imports, exception and global names."""
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): bound.add(node.name)
        elif isinstance(node, ast.arg): bound.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)): bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)): bound.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name: bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)): bound.update(node.names)
    return bound
def module_level_names(tree):
    """The names a module offers to others: its top-level definitions, assignment targets and imports."""
    offered = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): offered.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)): offered.update(target.id for target in (node.targets if isinstance(node, ast.Assign) else [node.target]) for target in ast.walk(target) if isinstance(target, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)): offered.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
    return offered
def name_resolution_check():
    """(passed, message): every name a kit module reads is bound in it or a builtin; every name imported from a kit module, and every attribute read off an imported kit
    module, is defined at that module's top level - a deleted definition shows every place that still reads it, before anything runs (the kit's static map)."""
    import builtins
    trees = {name: ast.parse(open(os.path.join(ROOT, name)).read()) for name in kit_modules()}; offered = {name[:-3]: module_level_names(tree) for name, tree in trees.items()}; problems = []
    for name, tree in trees.items():
        bound = bound_everywhere(tree) | set(dir(builtins)) | {"__file__", "__name__", "__doc__"}; kit_aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in bound: problems.append(f"{name}:{node.lineno} {node.id} unbound")
            elif isinstance(node, ast.ImportFrom) and node.module in offered: problems += [f"{name}:{node.lineno} {alias.name} not defined in {node.module}" for alias in node.names if alias.name not in offered[node.module]]
            elif isinstance(node, ast.Import): kit_aliases.update({(alias.asname or alias.name): alias.name for alias in node.names if alias.name in offered})
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in kit_aliases and node.attr not in offered[kit_aliases[node.value.id]]:
                problems.append(f"{name}:{node.lineno} {node.value.id}.{node.attr} not defined in {kit_aliases[node.value.id]}")
    return (False, f"name resolution: {len(problems)} unresolved - " + "; ".join(sorted(set(problems)))) if problems else (True, f"name resolution: every name read in {len(trees)} modules resolves")
def one_definition_check():
    """(passed, message): every module-level name (function, class, assignment target) is defined exactly once across the kit."""
    definitions = {}
    for name in kit_modules():
        for node in ast.parse(open(ROOT / name).read()).body:
            names = [node.name] if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else [element.id for target in node.targets for element in ast.walk(target) if isinstance(element, ast.Name)] if isinstance(node, ast.Assign) else []
            for defined in names: definitions.setdefault(defined, []).append(name)
    repeated = {defined: modules for defined, modules in definitions.items() if len(modules) > 1}
    return (False, "defined more than once: " + "; ".join(f"{defined} in {modules}" for defined, modules in sorted(repeated.items()))) if repeated else (True, f"one definition per name: {len(definitions)} names across {len(kit_modules())} modules")
def kit_size():
    """(True, message): the kit's total AST node count over its modules and kit.py - the operational gate's reading at integration (CHARTER, Oct 6 2026)."""
    return True, f"kit size: {sum(sum(1 for _ in ast.walk(ast.parse(open(ROOT / name).read()))) for name in kit_modules())} AST nodes"
ALPHA_FAMILY = 0.05   # OWNER RULING (Oct 6 2026): the one human-set statistical number - the probability of at least one false scientific promotion in a family
def resolution_z(checks):
    """The z that resolves a family of checks (estimation-precision gates, CHARTER FOUR KINDS OF GATE): the two-sided normal quantile at ALPHA_FAMILY split over the
    measured number of checks - a deviation inside it is unresolved from zero.  The count is the caller's, measured; nothing here is chosen per gate."""
    return float(normal_law.ppf(1 - ALPHA_FAMILY / (2 * checks)))
def resolved_share(successes, trials):
    """The exact (Clopper-Pearson) interval of a binomial share at ALPHA_FAMILY: (share, lower, upper)."""
    return successes / trials, (float(beta_law.ppf(ALPHA_FAMILY / 2, successes, trials - successes + 1)) if successes > 0 else 0.0), (float(beta_law.ppf(1 - ALPHA_FAMILY / 2, successes + 1, trials - successes)) if successes < trials else 1.0)
def instrument_state(premises, gate_passed):
    """The one producer of an instrument's state (CHARTER INSTRUMENT STATES, Oct 6 2026).  premises: (name, held, measurement) - each premise the instrument rests on,
    measured by the instrument itself.  INVALID (naming every premise that failed, with its measurement) when any premise fails; otherwise VALID PASS or VALID FAIL by
    the gate.  An instrument states what it measured; the consequence of a state lives in the CHARTER, never in the instrument's output."""
    failed = [f"{name} ({measurement})" for name, held, measurement in premises if not held]
    return ("INVALID - " + "; ".join(failed)) if failed else ("VALID PASS" if gate_passed else "VALID FAIL")
def r_gate_earned(season_gains):
    """CHARTER R-GATE, scientific gate (owner ruling Oct 6 2026): a genuinely new wall's cell is EARNED iff its mean held-out season gain is positive (the posterior
    mean of mu under the reference prior 1 / sigma).  Code size is the operational gate's reading at integration, never evidence for promotion."""
    return float(np.mean(season_gains)) > 0
def file_content(path):
    """A file's content as its writer meant it: gzip decompressed (gzip stamps wall-clock time); an .npz as its arrays' names, dtypes, shapes and bytes in name order
    (the zip container stamps time); any other file its bytes."""
    if str(path).endswith(".gz"): return gzip.decompress(open(path, "rb").read())
    if str(path).endswith(".npz"):
        with np.load(path, allow_pickle=False) as arrays: return b"".join(f"{name}|{arrays[name].dtype.str}|{arrays[name].shape}|".encode() + np.ascontiguousarray(arrays[name]).tobytes() for name in sorted(arrays.files))
    return open(path, "rb").read()
def same_content(first_path, second_path):
    """Content of two files compared byte for byte (file_content)."""
    contents = [file_content(path) for path in (first_path, second_path)]
    if contents[0] == contents[1]: print(f"IDENTICAL  {first_path} == {second_path} ({len(contents[0])} bytes)"); return 0
    first_lines, second_lines = contents[0].split(b"\n"), contents[1].split(b"\n"); line_number = next((number for number, (first_line, second_line) in enumerate(zip(first_lines, second_lines)) if first_line != second_line), min(len(first_lines), len(second_lines)))
    print(f"DIFFER  {first_path} vs {second_path}: {len(first_lines)} vs {len(second_lines)} lines; first difference at line {line_number}"); return 1
# ---------------- freezes: the current-product witness and the prospective issue (CHARTER, Oct 6 2026) ----------------
FROZEN_DIR = PROJ_DIR / "frozen"
def product_files(season, week):
    """What the product is at an issue week: the M3 replay graded into the atlas (the qualification labels the card carries), the trust ladder (the rung and reference
    status the card carries), week N's law rows, the card (players,
    candidates, DST), the frozen draws the market reads, the slate pool and the BASE lineup."""
    return ["atlas_rows.csv.gz", "atlas.csv", "atlas_coverage.csv", "ladder.csv", f"native_law_week_{season}_w{week}.csv.gz", f"card_{season}_w{week}.csv", f"card_{season}_w{week}_candidates.csv",
            f"card_{season}_w{week}_dst.csv", f"frozen_draws_{season}_w{week}.npz", f"slate_pool_{season}_w{week}.csv", f"lineup_base_{season}_w{week}.csv"]
def content_sha(path): return hashlib.sha256(file_content(path)).hexdigest()
def kit_sha(): return hashlib.sha256(b"".join(module_name.encode() + b"|" + open(os.path.join(ROOT, module_name), "rb").read() for module_name in kit_modules())).hexdigest()
def freeze(name, season, week):
    """python3 kit.py freeze NAME SEASON WEEK: copies week N's product_files to proj/frozen/NAME/ with manifest.csv (file, content_sha256) and meta.json (season, week,
    kit_sha256 over the kit modules, the CHARTER's accepted lines and digest, the CHARTER's lines on disk, frozen_at in UTC).  Refused if NAME exists (a freeze is
    never rewritten), if a product file is missing, if the CHARTER carries lines the ledger has not accepted, or if any file is not, as it is now,
    the output of an accepted event (exit 0) of the current code and the current raw manifest (proj/events.jsonl, written by kit.py's main)."""
    from datetime import datetime, timezone
    import shutil
    target = FROZEN_DIR / name; files = product_files(season, week); missing = [file_name for file_name in files if not (PROJ_DIR / file_name).exists()]
    if target.exists(): raise SystemExit(f"{target} exists - a freeze is never rewritten; nothing changed")
    if missing: raise SystemExit(f"freeze {name}: product files missing {missing} - nothing frozen")
    from ingest import read_events, manifest_sha, ROOT as KIT_ROOT
    code_now, manifest_now = kit_sha(), manifest_sha(); accepted_outputs = set()
    for event in read_events():
        if event["exit"] == 0 and event["kit_sha"] == code_now and event["raw_manifest"] == manifest_now: accepted_outputs.update(event["outputs"].items())
    unproduced = [file_name for file_name in files if (os.path.relpath(PROJ_DIR / file_name, KIT_ROOT), content_sha(PROJ_DIR / file_name)) not in accepted_outputs]
    if unproduced: raise SystemExit(f"freeze {name}: no accepted event of the current code ({code_now[:16]}) and raw manifest ({manifest_now[:16]}) wrote these files as they are now: {unproduced} - nothing frozen")
    accepted = json.load(open(CHARTER_LEDGER)); on_disk = len(charter_lines(CHARTER))
    if on_disk != accepted["lines"]: raise SystemExit(f"freeze {name}: the CHARTER has {on_disk - accepted['lines']} lines the ledger has not accepted - advance first; nothing frozen")
    target.mkdir(parents=True); manifest = []
    for file_name in files: shutil.copyfile(PROJ_DIR / file_name, target / file_name); manifest.append((file_name, content_sha(target / file_name)))
    pd.DataFrame(manifest, columns=["file", "content_sha256"]).to_csv(target / "manifest.csv", index=False)
    meta = dict(name=name, season=int(season), week=int(week), kit_sha256=kit_sha(), charter_accepted_lines=accepted["lines"], charter_accepted_sha=accepted["sha"], frozen_at=datetime.now(timezone.utc).isoformat())
    json.dump(meta, open(target / "meta.json", "w"), indent=1)
    print(f"kit.py freeze {name} {season} w{week}: {len(files)} files -> {target}; kit {meta['kit_sha256'][:16]}; CHARTER {meta['charter_accepted_lines']} lines {meta['charter_accepted_sha'][:16]}; frozen at {meta['frozen_at']}")
    for file_name, digest in manifest: print(f"   {digest[:16]}  {file_name}")
    return 0
def cell_differences(frozen_path, current_path):
    """Where two versions of a product file differ: the differing rows by cell - term, position, state where the table has them; frozen draws by term."""
    if str(frozen_path).endswith(".npz"):
        with np.load(frozen_path, allow_pickle=False) as frozen_arrays, np.load(current_path, allow_pickle=False) as current_arrays:
            frozen, current = {name: frozen_arrays[name] for name in frozen_arrays.files}, {name: current_arrays[name] for name in current_arrays.files}
        if sorted(frozen) != sorted(current) or any(frozen[name].shape != current[name].shape for name in frozen): return f"arrays or shapes differ: {[(name, frozen[name].shape) for name in sorted(frozen)]} vs {[(name, current[name].shape) for name in sorted(current)]}"
        differing = (frozen["draws"] != current["draws"]).any(1) | (frozen["keys"] != current["keys"]) | (frozen["terms"] != current["terms"])
        return f"draw rows differing {int(differing.sum())} of {len(differing)}: {pd.Series(frozen['terms'][differing]).value_counts().to_dict()}"
    frozen, current = read_table(frozen_path), read_table(current_path)
    if list(frozen.columns) != list(current.columns) or len(frozen) != len(current): return f"shape differs: {len(frozen)} rows {list(frozen.columns)} vs {len(current)} rows {list(current.columns)}"
    differing = ~(frozen.eq(current) | (frozen.isna() & current.isna())).all(axis=1); cell_columns = [column_name for column_name in ["term", "position", "state"] if column_name in frozen.columns]
    by_cell = frozen[differing].groupby(cell_columns).size().to_dict() if cell_columns else {}
    return f"rows differing {int(differing.sum())} of {len(differing)}" + (f" by {'/'.join(cell_columns)}: {by_cell}" if cell_columns else "")
def witness_check(name, declared_files):
    """python3 kit.py witness-check NAME [FILE ...]: the product files now against proj/frozen/NAME/, content file by file (file_content); a differing file is read by
    cell (cell_differences).  ACCEPTED iff every differing file is one the transaction declared it changes (none declared: every file equal).  The kit's code digest
    against the freeze's is a reading (code may change; undeclared product may not)."""
    target = FROZEN_DIR / name; meta = json.load(open(target / "meta.json")); manifest = read_table(target / "manifest.csv"); differing_files = 0
    undeclared = sorted(set(declared_files) - set(manifest.file))
    if undeclared: raise SystemExit(f"witness-check {name}: declared files not in the freeze {undeclared} - refused")
    print(f"kit.py witness-check {name} ({meta['season']} w{meta['week']}, frozen at {meta['frozen_at']}): kit code {'unchanged' if kit_sha() == meta['kit_sha256'] else 'changed since the freeze'}")
    for row in manifest.itertuples(index=False):
        current_path = PROJ_DIR / row.file
        declared = row.file in declared_files
        if content_sha(current_path) == row.content_sha256: print(f"   IDENTICAL  {row.file}" + ("  (declared changed - unchanged)" if declared else "")); continue
        differing_files += int(not declared); print(f"   {'CHANGED ' if declared else 'DIFFER  '}   {row.file}: {cell_differences(target / row.file, current_path)}" + ("  (declared)" if declared else ""))
    print(f"\n{'WITNESS ' + name + ' ACCEPTED - every undeclared product file equals the freeze' if differing_files == 0 else f'WITNESS {name} REFUSED: {differing_files} undeclared file(s) differ'}"); return 0 if differing_files == 0 else 1
# ---------------- the calibration atlas (M3): grades of the issued product per stat x position x state ----------------
COVERAGE_LEVELS = (0.10, 0.25, 0.75, 0.90)   # the questions the card answers (the product's definition, not an estimate)
def share_band(indicator, slates, target):
    """Mean over slates of the slate share of a 0 / 1 indicator, its slate standard error, and the band status against target (within resolution_z(1) slate SE - unresolved
    from target; else too low / too high) - the atlas's band rule, one producer for the coverage bands and the ladder's center and width rungs."""
    slate_share = indicator.astype(float).groupby(slates).mean(); share_mean = float(slate_share.mean())
    standard_error = float(slate_share.std(ddof=1) / np.sqrt(len(slate_share))) if len(slate_share) > 1 else np.nan; gap = share_mean - target
    return share_mean, standard_error, ("within band" if abs(gap) <= resolution_z(1) * standard_error else ("too low" if gap < 0 else "too high"))
def coverage_band(outcome_ranks, slates, level):
    """Mean over slates of the slate share with PIT <= level, its slate standard error, and the band status (share_band)."""
    return share_band(outcome_ranks <= level, slates, level)
def qualification(bands, decile_value, noise_value):
    """The M3 rule (row floor replaced by resolution, CHARTER FOUR KINDS OF GATE): UNRESOLVED when a tail's interval (share +- resolution_z(1) slate SE) reaches its bound -
    the cell cannot tell an empty tail from the nominal one (q .10 reaching 0, q .90 reaching 1, or one slate); every coverage band within and the PIT decile deviation
    at or below its noise quantile -> DECISION-QUALIFIED; else the miss is named from the q .10 / .90 bands (TOO NARROW, TOO WIDE, CENTER TOO HIGH, CENTER TOO LOW) or
    MISCALIBRATED (shape).  bands: level -> (share, slate SE, status)."""
    statuses = {level: band[2] for level, band in bands.items()}; z_value = resolution_z(1)
    if not (np.isfinite(bands[0.10][1]) and np.isfinite(bands[0.90][1])) or bands[0.10][0] - z_value * bands[0.10][1] <= 0 or bands[0.90][0] + z_value * bands[0.90][1] >= 1:
        return "UNRESOLVED - a tail interval reaches its bound (an empty tail is not told from the nominal one)"
    if all(status == "within band" for status in statuses.values()) and decile_value <= noise_value: return "DECISION-QUALIFIED"
    lower, upper = statuses[0.10], statuses[0.90]
    if lower == "too high" and upper == "too low": return "NOT QUALIFIED - TOO NARROW"
    if lower == "too low" and upper == "too high": return "NOT QUALIFIED - TOO WIDE"
    if lower == "too high" or upper == "too high": return "NOT QUALIFIED - CENTER TOO HIGH"
    if lower == "too low" or upper == "too low": return "NOT QUALIFIED - CENTER TOO LOW"
    return "NOT QUALIFIED - MISCALIBRATED (shape)"
def atlas_cells(graded_rows):
    """One row per (term, position, state) of the graded issued rows: rows, slates, PIT mean / sd, coverage and band at q .10 / .25 / .75 / .90, CRPS, bias (draw mean - y),
    PIT decile deviation against its noise 95th, ISSUABLE and the qualification."""
    cells = []
    for (term, position, state), cell_rows in graded_rows.groupby(["term", "position", "state"], sort=True):
        slates = [cell_rows.season.values, cell_rows.week.values]; bands = {level: coverage_band(cell_rows.outcome_rank, slates, level) for level in COVERAGE_LEVELS}
        decile_value, noise_value = float(decile_deviation(cell_rows.outcome_rank.values)), float(noise95(len(cell_rows)))
        cells.append(dict(term=term, position=position, state=state, rows=len(cell_rows), slates=cell_rows.groupby(["season", "week"]).ngroups, outcome_rank_mean=float(cell_rows.outcome_rank.mean()),
                          outcome_rank_standard_deviation=float(cell_rows.outcome_rank.std()), **{f"coverage_{int(level * 100)}": bands[level][0] for level in COVERAGE_LEVELS},
                          **{f"coverage_{int(level * 100)}_band": bands[level][2] for level in COVERAGE_LEVELS}, crps_mean=float(cell_rows.crps.mean()), bias_mean=float(cell_rows.bias.mean()),
                          decile_deviation=decile_value, noise_95th=noise_value, issuable="ISSUABLE", qualification=qualification(bands, decile_value, noise_value)))
    return pd.DataFrame(cells)
Y_COLUMNS = {"player_id": "key", "p10": "quantile_10", "p50": "quantile_50", "p90": "quantile_90"}   # the one read site of the frozen Y rows (retired spellings -> canonical)
Y_LOSSES = ["center_absolute_error", "pinball_10", "pinball_50", "pinball_90"]
def y_benchmark(graded_rows, report):
    """Y (frozen benchmark, writes no card) scored beside the served F8 on the same played player-weeks: absolute error of the center (Y center vs F8 draw mean) and
    pinball loss at q .10 / .50 / .90, against facts' dk_points (the F8 graded outcome).  Y's walk-forward rows only ("fit on seasons < ..."); outcome_percent is display
    only and never read.  Per position: means, the per-slate gain of F8 over Y (positive = F8 better) and coverage at q .10 / .90 for both - a reading, no verdict.
    Writes proj/atlas_y_benchmark.csv."""
    y_rows = read_table(os.path.join(PROJ_DIR, "ystick_rows.csv.gz"))[list(Y_COLUMNS) + ["season", "week", "center", "model", "asof"]].rename(columns=Y_COLUMNS)
    y_rows = y_rows[y_rows["asof"].astype(str).str.startswith("fit on seasons <")]   # "asof" is a pandas method name: read with brackets only (TAXONOMY collision rule)
    if y_rows.duplicated(["key", "season", "week"]).any(): raise SystemExit(f"Y benchmark: {int(y_rows.duplicated(['key', 'season', 'week']).sum())} player-weeks with more than one Y row - refused")
    f8_rows = graded_rows[graded_rows.term == "F8 dk_points"][["season", "week", "key", "position", "state", "outcome", "draw_mean", "quantile_10", "quantile_50", "quantile_90"]]
    paired = f8_rows.merge(y_rows.drop(columns=["asof"]), on=["key", "season", "week"], suffixes=("_f8", "_y"))
    for engine, center_column in (("f8", "draw_mean"), ("y", "center")):
        paired[f"center_absolute_error_{engine}"] = np.abs(paired[center_column] - paired.outcome)
        for level in (10, 50, 90): paired[f"pinball_{level}_{engine}"] = pinball(level / 100, paired[f"quantile_{level}_{engine}"].values, paired.outcome.values)
    paired.to_csv(os.path.join(PROJ_DIR, "atlas_y_benchmark.csv"), index=False)
    report.say(f"\nY BENCHMARK - frozen Y vs served F8 on the same played player-weeks: F8 graded {len(f8_rows)}, Y walk-forward rows {len(y_rows)}, paired {len(paired)}; gain = Y loss - F8 loss per slate (positive = F8 better); a reading, no verdict")
    for position, position_rows in paired.groupby("position", sort=True):
        slates = [position_rows.season, position_rows.week]; parts = []
        for loss in Y_LOSSES:
            gain = paired_by_slate(position_rows[f"{loss}_y"].groupby(slates).mean(), position_rows[f"{loss}_f8"].groupby(slates).mean())
            parts.append(f"{loss} F8 {position_rows[f'{loss}_f8'].mean():.3f} Y {position_rows[f'{loss}_y'].mean():.3f} gain {gain[0]:+.4f}+-{gain[1]:.4f} ({gain[2]}/{gain[3]})")
        coverage_text = "; ".join(f"q .{level} coverage F8 {(position_rows.outcome <= position_rows[f'quantile_{level}_f8']).mean():.3f} Y {(position_rows.outcome <= position_rows[f'quantile_{level}_y']).mean():.3f}" for level in (10, 90))
        report.say(f"   {position} rows {len(position_rows)} (Y models {sorted(position_rows.model.astype(str).unique())}):  " + ";  ".join(parts) + f";  {coverage_text}")

