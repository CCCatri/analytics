"""contract: the one authority for what the product says, how a forecast is identified, where the information boundary lies, and which
policy parameters, model assumptions and acceptance limits apply. Every module reads these definitions; none recreates them.

Replaces claim.py and decisions.py (2026-10-22, reviewer-admitted replacement). Earlier decisions are kept as text in HISTORY for the record."""
import math, dataclasses, hashlib, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent

# ----------------------------------------------------------------------------------------------------------------------------- meaning
SENTENCE = ("For every listed player (the week's ACT roster minus players the injury report rules Out) at QB, RB, WR or TE: P(his official stat this "
            "game > his per-game average over his prior FINISHED games this season | he FINISHES this game), issued before the game from "
            "information available then. FINISHED = on the field for at least one offensive snap of his side's actual final offensive drive; "
            "TRUE needs one observed snap, FALSE needs every snap of that drive observed, otherwise UNKNOWN. The average is over prior games "
            "finished TRUE (UNKNOWN games are excluded and counted), kept as integer sum and count; the event is Y * avg_n > avg_sum. "
            "Official = the nflverse weekly player-stats definitions: a kneel is a carry, a spike is an attempt, sack yards are not passing yards. "
            "Right when, among lines said at p, the share that come true is p.")
BENCHMARK = "per-game average over prior games this season the player finished (finished = TRUE); integer avg_sum / avg_n"

POSITIONS_CLAIMED = ("QB", "RB", "WR", "TE")
CELLS = {"QB": ["attempts", "completions", "pass_yards", "pass_td", "interceptions", "carries", "rush_yards"],
         "RB": ["targets", "receptions", "rec_yards", "tds", "carries", "rush_yards"],
         "WR": ["targets", "receptions", "rec_yards", "tds", "carries", "rush_yards"],
         "TE": ["targets", "receptions", "rec_yards", "tds", "carries", "rush_yards"]}
STATS = ["targets", "receptions", "rec_yards", "rec_td", "carries", "rush_yards", "rush_td", "tds",
         "attempts", "completions", "pass_yards", "pass_td", "interceptions"]
KIND = {"targets": "targets", "receptions": "targets", "rec_yards": "targets", "rec_td": "targets",
        "carries": "carries", "rush_yards": "carries", "rush_td": "carries", "tds": "tds",
        "attempts": "attempts", "completions": "attempts", "pass_yards": "attempts", "pass_td": "attempts", "interceptions": "attempts"}
COUNT_STATS = ("targets", "carries", "attempts")
OFFICIAL = {"targets": ["targets"], "receptions": ["receptions"], "rec_yards": ["receiving_yards"], "rec_td": ["receiving_tds"],
            "carries": ["carries"], "rush_yards": ["rushing_yards"], "rush_td": ["rushing_tds"],
            "attempts": ["attempts", "passing_attempts"], "completions": ["completions", "passing_completions"],
            "pass_yards": ["passing_yards"], "pass_td": ["passing_tds"], "interceptions": ["interceptions", "passing_interceptions"]}
WORDS = {"targets": "targets", "receptions": "receptions", "rec_yards": "receiving yards", "rec_td": "receiving TDs", "carries": "carries",
         "rush_yards": "rushing yards", "rush_td": "rushing TDs", "tds": "touchdowns", "attempts": "pass attempts", "completions": "completions",
         "pass_yards": "passing yards", "pass_td": "passing TDs", "interceptions": "interceptions"}
DISPLAY_PERCENTILES = (10, 25, 50, 75, 90)
if set(KIND) != set(STATS) or set(OFFICIAL) | {"tds"} != set(STATS):
    raise RuntimeError("contract: KIND and OFFICIAL must name every stat")

# ----------------------------------------------------------------------------------------------------------------------------- football
SCORING = {"td": 6, "xp": 1, "two": 2, "fg": 3, "safety": 2, "def_two": 2, "def_xp": 2}   # Rule 11-1-2 (and 11-3-2 defensive tries)
FIELD_YARDS = 100            # Rule 1-1-1
ON_FIELD = 11                # Rule 5-1-1
DOWNS = 4                    # Rule 7-1-1
LINE_TO_GAIN = 10            # Rule 7-1-1
HALF_SECONDS = 1800          # Rule 4-1-1: two 15-minute periods per half
OT_SECONDS = 600             # Rule 16-1-3: one 10-minute regular-season overtime period; a tie is possible
KICKOFF_TOUCHBACK_YARDLINE_100 = 65   # Rule 6-1-5 (2024+): the 35
SAFETY_KICK_FROM = 20                 # Rule 11-5-2
FG_SNAP_TO_HOLD = 7                   # customary hold 7 yards behind the line; the kick distance is yardline_100 + 17 (10-yard end zone + 7)
RECEIVER_POSITIONS = ("QB", "RB", "FB", "HB", "WR", "TE")   # Rule 8-1-5: ends and backs; their roster positions stand for them unless reported

# ----------------------------------------------------------------------------------------------------------------------------- identity
KEY = ["season", "week", "posteam", "player", "stat", "issue_time", "model_version"]
GRADE_KEY = ["season", "week", "posteam", "player", "stat"]   # the official record carries no issue_time or model_version
CONTRACT = KEY + ["avg_sum", "avg_n", "p", "n_over", "n_finished_worlds", "n_worlds", "mc_se", "mc_bound", "q10", "q25", "q50", "q75", "q90", "mean",
                  "pmf", "reason", "reason_words", "exp_nontd_yds", "exp_td_yds", "exp_takes", "exp_comp"]
REASONS = {"no_avg": "no prior finished game this season: no average to price over",
           "not_finished_in_any_world": "he finished in no simulated world: the conditioning event was never observed (INSUFFICIENT_SIMULATION)",
           "insufficient_simulation": "fewer finishing worlds than the declared count at the world budget: the Monte Carlo bound exceeds the tolerance (INSUFFICIENT_SIMULATION)",
           "unresolved_team": "his roster team code resolves to no team identity of the season",
           "construction_failure": "the joint simulation could not be constructed for this game (see the run record)"}
FINISH_TRUE, FINISH_FALSE, FINISH_UNKNOWN = "TRUE", "FALSE", "UNKNOWN"

# ----------------------------------------------------------------------------------------------------------------------------- inputs
# The projection-input allowlist: the only columns of each source a fit, prior, table or world may read. Betting markets (spread, total, moneyline,
# odds and anything derived from them) are excluded permanently from projections, not pending admission.
PROJECTION_INPUTS = {
    "games.csv": ["game_id", "season", "game_type", "week", "gameday", "gametime", "away_team", "home_team", "away_score", "home_score", "roof", "surface", "away_rest", "home_rest", "div_game"],
    "excluded_permanently": ["spread_line", "total_line", "away_moneyline", "home_moneyline", "away_spread_odds", "home_spread_odds", "under_odds", "over_odds"],
}
ISSUE_TIME = ("kickoff: the listed population is the week's gameday ACT roster (the inactive list is published about 90 minutes before kickoff) minus players the injury "
              "report rules Out. An earlier issue time (Tuesday to Friday) is not supported until a roster snapshot taken at that time exists in the record; "
              "ACT + INA - Out would be a retrospective reconstruction, not an issue-time observation.")

# ----------------------------------------------------------------------------------------------------------------------------- statuses
FIT_OK, INSUFFICIENT_DATA, INVALID_FIT, UNSUPPORTED_INPUT = "FIT_OK", "INSUFFICIENT_DATA", "INVALID_FIT", "UNSUPPORTED_INPUT"
PASSED, FAILED_REQUIREMENTS, INSUFFICIENT, STOPPED, CRASHED = "PASSED", "FAILED_REQUIREMENTS", "INSUFFICIENT", "STOPPED", "CRASHED"
PASS, FAIL = "PASS", "FAIL"
DEVELOPMENT, CERTIFICATION = "development", "certification"

# ----------------------------------------------------------------------------------------------------------------------------- policy
POLICY = {
    "holdout_season": 2022,                 # R3: the unseen season, scored once; access is tracked by dataset identity in the run_log
    "claim_weeks": (4, 17),                 # R-weeks: lines are issued for weeks 4-17
    "k_se": 2.0,                            # R-2SE: single-group decisions at 2 SE (kept for per-cell print-outs)
    "alpha_family": 0.05,                   # multiplicity: max-statistic simultaneous intervals over the required groups at this level
    "bootstrap_replicates": 400,            # game-cluster bootstrap replicates for the simultaneous intervals
    "group_tolerance": None,                # OWNER: maximum acceptable |P(hit) - said| per required group. Not declared -> RELIABLE is INSUFFICIENT
    "material_harm": None,                  # OWNER: largest acceptable paired-Brier degradation per required group. Not declared -> harm term INSUFFICIENT
    "baseline_gain": "any demonstrated gain",   # USEFUL: pooled paired Brier better than B1 beyond the simultaneous bound
    "min_group_lines": 50,                  # fewer graded lines than this in a required group -> INSUFFICIENT information for that group
    "refit_weeks": (4,),                    # a fit per issue season at each of these weeks; a forecast uses the latest fit with fit_week <= issue week
    "worlds_initial": 1000, "worlds_max": 6000, "world_batch": 250,   # equal-weight worlds; grown in batches until every line has mc_worlds() finishing worlds or worlds_max
    "mc_tolerance": 0.015,                  # largest acceptable Monte Carlo bound 0.5 / sqrt(finishing worlds) of a published p (NFL goal doc v3 R12)
    "memory_budget_mb": 1500, "workers": None,   # None: os.cpu_count() - 1
    "seed_bytes": 8, "print_hex": 12, "read_chunk": 1 << 20,
}
def mc_worlds():
    """Finishing worlds a line needs before its p is published: the smallest m with 0.5 / sqrt(m) <= mc_tolerance (the Monte Carlo bound at p = 1/2),
    fixed before any world is read, so stopping never reads the estimate it stops (R12)."""
    return int(math.ceil(0.25 / POLICY["mc_tolerance"] ** 2))


REQUIRED_GROUPS = {"cell": "position/stat", "said": "said tercile within cell", "share": "exposure tercile within cell (exp_takes)"}

# ----------------------------------------------------------------------------------------------------------------------------- model
# Modeling assumptions. Prior scales are assumptions declared here, not quantities read from the record.
MODEL = {
    "estimator": {"draws": 1200, "seed": 20261022,     # draws per sub_model from the conditional posteriors (the same count the sampler produced)
                  "newton_max": 60, "newton_tol": 1e-5, "outer_max": 80, "outer_ftol": 1e-9, "outer_eps": 1e-3, "outer_gtol": 1e-2,
                  "method": "sparse Laplace along the exact OU period chain; spread hyperparameters by maximum marginal likelihood with the priors below as penalties; "
                            "unit states from their conditional posteriors (NFL goal doc v3 R1, R2, R18); no sampler over unit effects"},
    "priors": {"intercept_sd": 2.0, "beta_sd": 1.0, "group_sd_scale": 1.0, "player_sd_scale": 1.0, "season_sd_scale": 0.5,
               "game_sd_scale": 0.5, "lambda_rate": 1.0, "log_sigma_sd": 1.0, "nu_shape": 2.0, "nu_rate": 0.1, "nu_min": 2.0,
               "log_phi_mean": 3.0, "log_phi_sd": 1.5,       # beta-binomial precision of a player's game snap rate (phi ~ 20 a priori, wide)
               "log_kappa_mean": 3.0, "log_kappa_sd": 1.5,   # Dirichlet-multinomial concentration of a game's allocation (kappa ~ 20 a priori, wide)
               "defense_sd_scale": 0.5},                      # hierarchical defence team-season effect v_def (opponent-aware sub_models, proposal §4)
    "tables": {"pseudo_count": 1.0},     # conjugate Dirichlet / Beta posteriors for the non-player sub_models: one pseudo-observation per legal category
    "time_unit": "season",               # b[i,t] = m[i] + rho (b[i,t-1] - m[i]) + eps, rho = exp(-lambda * dt), dt in seasons
    "min_obs": {"softmax": 200, "binomial": 100, "categorical": 200, "gain": 300, "betabinomial": 100, "dirmult": 50},   # below these, a fit is INSUFFICIENT_DATA
    "data_layout": 3,   # 3: the serialised sub_model data (1-based codes, j_prev, j_dt, j_order) consumed by estimate.py; the unit constant m is absorbed into the stationary first state (R2)
    "programs": {"softmax": "estimate.lik_softmax", "binomial": "estimate.lik_binomial", "categorical": "estimate.lik_categorical", "gain": "estimate.lik_gain",
                 "betabinomial": "estimate.lik_betabinomial", "dirmult": "estimate.lik_dirmult"},
    "opponent": "v_def: one hierarchical effect per defence team-season in each of the call, branch, result, touchdown and gain sub_models (g(E[X]) = alpha + u_off + v_def + beta context), "
                "drawn once per world and reused for every play of that world; the sub_models' effects are separate, never one defensive summary applied to volume, efficiency and totals; "
                "fitted coefficients are conditional predictive associations, not causal effects. Betting markets are excluded permanently (policy.PROJECTION_INPUTS)",
    "season_state": "sparse: one OU state per (player, season) pair observed in the training view; over a gap of dt seasons the transition is rho^dt with variance tau^2 (1 - rho^(2 dt)), "
                    "the stationary chain's exact dt-step law (a hold-out season is an unobserved node with a larger gap; the previous period is the most recent admitted period on disk); "
                    "the unit constant is absorbed into the stationary first state; an annual state does not carry within-season role change "
                    "(promotion, return, lineup change between weeks): that variation is the game-level Beta / Dirichlet draw only",
    "game_variation": "snap rate: Beta(mu phi, (1-mu) phi) drawn once per game and player; allocation: Dirichlet(kappa pi) over the side's listed players drawn once per game; "
                      "the branch, result and touchdown sub_models carry no game-level effect (2026-10-22 re-parameterisation: the per-player-game effects of the first "
                      "version were unidentified and made the fits cost days)",
}


def model_version():
    """sha256 over the estimator's source and the MODEL specification: part of every forecast's key."""
    h = hashlib.sha256(json.dumps(MODEL, sort_keys=True).encode())
    p = HERE / "estimate.py"
    if p.exists(): h.update(p.read_bytes())
    return h.hexdigest()[: POLICY["print_hex"]]


MODEL_VERSION = model_version()


# ----------------------------------------------------------------------------------------------------------------------------- cutoff
@dataclasses.dataclass(frozen=True)
class Cutoff:
    """The one information boundary. season/week: the issue point (information strictly before this week of this season); fit_week: the
    refit cutoff the forecast's fit used (<= week); admitted_seasons: seasons readable for fitting, never the hold-out unless this cutoff is
    a certification cutoff *for scoring only* (the training view never includes hold-out outcomes); data_version: sha of the raw pins;
    partition: development or certification."""
    season: int
    week: int
    fit_week: int
    admitted_seasons: tuple
    holdout: int
    data_version: str
    partition: str

    def issue_time(self):
        return f"{self.season}w{self.week:02d}"

    def admits(self, season, week):
        """Whether an observation at (season, week) is inside the fit's information boundary."""
        if season == self.holdout: return False
        if season not in self.admitted_seasons: return False
        return season < self.season or (season == self.season and week < self.fit_week)

    def key(self):
        return hashlib.sha256(json.dumps(dataclasses.asdict(self), sort_keys=True, default=str).encode()).hexdigest()[: POLICY["print_hex"]]

    def fit_key(self):
        """The fit's identity: the information boundary (season, fit_week, admitted seasons, hold-out, data version) without the issue week, so
        every issue week served by one fit shares it."""
        d = dataclasses.asdict(self); d["week"] = self.fit_week; d["partition"] = DEVELOPMENT
        return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[: POLICY["print_hex"]]


HISTORY = (
    "R3 HOLDOUT 2022 (reviewer): the unseen season; scored once. Access is now tracked by dataset identity and access history (run_log.certification_access), not by product.py sha.",
    "R-weeks (4,17); R-2SE k=2 (reviewer).",
    "R-prior POOLED-LEVEL (reviewer, 2026-10-22): replaced by this contract's joint simulation; the stat-specific world weights are removed.",
    "R-c1c, R-layer, R-fitted, R-grounding, R-tweedie, I-boot, I-tilt-*: closed arms of the superseded construction; preserved in the run_log and _probe logs.",
    "2026-10-22 replacement (reviewer-admitted contract change, recorded once): one joint predictive environment, one finishing mask per player, tri-state finishing, "
    "conditional allocation over eligible risk sets, no redistribution of historical counts, structured release decisions. The grading set no longer requires a "
    "prior finished game for this team (the benchmark is the player's prior finished games this season, any team).",
)
