## revision 16 — stage 4, the worlds (revision-stages/revision-stage4_worlds.expect.json) — UNGRADED: the reviewer runs the suite and the quality gate

- R12 count-based stopping: `contract.mc_worlds()` = ceil(0.25/tol²) (1112 finishing worlds at tol .015). `product.price` grows while any
  priceable player has fewer finishing worlds; it never reads a p. `lines_for` declares `insufficient_simulation` below n* and writes `mc_bound`
  (new CONTRACT column) on every line.
- R13 keyed streams: `model.Streams` (SplitMix64 over game key × global world id × per-world counter); all draws inverse transforms; every
  helper (`softmax_draw`, `gumbel_topk`, `categorical_draw`, `sample_gain`, `Table.draw`, `player_effects`, `defense_effect`) takes the world
  ids. `product.simulate(..., offset)` replaces the batch seed; a world's sample no longer depends on the batch it sits in.
- Not run here: the suite and the quality gate. Expected: 16/16 unchanged; a new `t_streams` batch-invariance oracle is still to be written (see HANDOFF).

## revision 15 — stage 3, the tendencies estimator (revision-stages/revision-stage3_tendencies.expect.json)

- `estimate.py` replaces Stan/CmdStanPy: sparse Laplace GLMM, same latent layout, same priors as contract terms; `model_version` =
  sha(MODEL + estimate.py bytes). `stan/` deleted; requirements are numpy/pandas/scipy only. Existing `_probe/fits` are stale: `rm -rf _probe/fits`.
- Synthetic: 12 sub-models fit in ~114 s total; fake-data recovery within 3·SE; coverage .93–.955; m == 0; audits zero (tests/test_product.py,
  t_estimator and t_estimated_pricing). Real-data cost is a prediction, not a measurement (expect.json).

## revision 14 — stage 2, the check (revision-stages/revision-stage2_instrument.expect.json)

Three incidents the Contract records (no per-stage timing on the run log, finished fits that never reached disk, a cache key that hashed less than the stage consumed) become product rules. Every quality gate stage records its seconds on the run log row (`timings`),
printed as `TIMINGS {...}` at the end of a run; every check's decision and its injected fault result land on the row as structured fields (`checks`), so the
"CAN FAIL" lines are evidence, not prose. A sub-model now carries `input_sha`, the sha256 of the serialised data it consumed; on resume a cached
sub-model is reused only when the freshly built input hashes identically (the observations are rebuilt every run, seconds), so a `record.py` change
can never resume a stale sub-model (a cache key that hashed less than the stage consumed). The preflight's checked counts and the sub-model's own seconds are in its sidecar and summarised under
`FITS ... sub-models`. No probability, count or decision changes.

## revision 13 — stage 1, the oracle (tests only; revision-stages/revision-stage1_oracle.expect.json)

The test league could not fail on the defect class that cost eight revisions (the predecessor-index mismatch, the out-of-order chain evaluation): its ids were season-prefixed, so no synthetic player had a
season chain. The league now carries every irregularity the builders branch on (tests/synth.py IRREGULARITIES, each proven by a record count):
players persist across seasons with 20% turnover; one player per team sits out a season and returns (dt = 2); the LV franchise is OAK in the first
season's schedule and roster; the first season has no participation file (finishing UNKNOWN; its pairs are first coded by a later sub-model than
snap, so prev[j] > j occurs); penalty no-plays, half with the other side's code; unbridged and disagreeing snap-count rows first; absent and
illegal personnel strings; two-quarterback snaps (the passer sub-model's informative risk set). model.BRANCHES declares every counted branch and the
quality gate check that guards the ones a passing record cannot reach; the oracle test refuses a zero on any unguarded branch and an undeclared count.
Every program's serialised data is round-tripped on the league (R4) and an injected 0-based predecessor is refused by all six (the predecessor-index mismatch's defect fails
in milliseconds now). tests/ is hashed into the manifest and locked by the reviewer (`--lock`, like `--pin`); a quality gate run whose suite hash differs is
STOPPED at LOCK, and the suite runs as the quality gate's own stage before anything touches real data (R16). model.build_observations factors the
observation loop out of fit_all so the test exercises the product's own builders; no numerical path changed.

## revision 12 (fit orchestration: worker-side writes, uncompressed float32 draws; model_version unchanged 4ad90b75f9b6)

The revision 11 run sampled for real: the first three sub-models started 07:13:29 and one finished its four chains at 07:31:52 (about 18 minutes with
three sub-models sharing the cores), another in 1.5 minutes. What the terminal did *not* show was the `MODEL <sub-model> … -> FIT_OK` line, because the
parent process received the finished sub-model's draws through the pool pipe (hundreds of MB for the snap sub-model) and then compressed them with
`np.savez_compressed` before printing; the next sub-model had already started in the freed worker. Now each worker writes its own sub-model
(`np.savez`, float32: seconds, not minutes), prints `MODEL <name> sampling started` / `sampling done … -> status; writing draws` itself so the
blocks of CmdStan chain lines can be attributed, and returns only status and provenance; the parent reloads the sub-model from disk. Draws are float32
in memory and on disk, so a fresh fit and a resumed one are identical. `save_fits` no longer rewrites sub-models that are already on disk.

Expected revision stage time for the fit phase on the real record, 3 workers: roughly 40–60 minutes; the large sub-models (snap, call, branch, result, the
three gain sub-models) take 15–25 minutes each while sharing the machine.

## revision 11 (defect: predecessor pair codes handed to Stan were 0-based; model_version 4ad90b75f9b6)

**The preflight's answer** (real record, cutoff 2025w04): `season state nan at pair j=996 ('00-0030564', 2021) (j_prev 497 …): the chain reads a
state before it is set`, and the same for ('00-0034457', 2020) in gain_run and call. Pair 497 is not that player's 2020 pair; it is the pair coded
one *before* it. `_stan_data` shifted every pair code to Stan's 1-based indexing (`ps`, `j_order`) except `j_prev`, which went across as the
0-based code. So in every revision to date Stan's `s[j_prev[j]]` read the state of the pair coded immediately before the true predecessor — a
different player's pair in general. In revision 1–revision 8 the loop ran in code order, so that wrong state was always already set and the sampler ran without
complaint on a mis-linked chain (the synthetic league could not see it: there the mis-linked pair's state is just another N(0, tau) draw). revision 9's
j_order evaluates true predecessors first, which left the wrong one unset and surfaced the defect as a nan.

**Fix.** `_stan_data` passes `j_prev` as `code + 1` (0 = none stays 0). The temporal test now checks, for every pair, that the Stan-side predecessor
code resolves to the same player's earlier season. `contract.MODEL["stan_data_layout"] = 2` stamps the layout so model_version changes with it;
nothing on disk under the previous versions is reusable, so `rm -rf _probe/fits` again.

**What this means for earlier readings.** No real-data fit has yet completed under a correctly linked season chain. Every sub-model's season
persistence (tau, lambda) in any earlier run would have been estimated against mis-linked predecessors; none of those runs reached grading, so no
decision is affected.

## revision 10 (check: Stan data preflight; no model change)

revision 9's run still failed every sub-model with a nan at one observation (`binomial … parameter[28912] is nan`, `student_t_lcdf: Random variable is nan`),
so the out-of-order chain was one defect, not the only one. The failing index is fixed across all initial-value attempts and all chains, so the nan
is data-determined; a nan covariate would make every row nan after standardisation (Stan would name observation 1), so it is an indexed term —
but which one, Stan's observation number does not say.

`model.preflight(program, data, obs, idx)` now runs before every sampler call: every real field finite, every index array within its declared
range, `j_order` a permutation with no negative gap, the season-state recursion evaluated in numpy on finite random inputs, and the Stan linear
predictor mirrored in numpy on finite random parameters. A failure is an INVALID_FIT whose provenance names the field, the row, the row's player,
(player, season) pair with its j_prev and dt, position group and defence, and the X row. The test suite injected faults a nan covariate and an out-of-range
pair index and checks they are refused by row; the synthetic td_pass and gain_run data pass. model_version is unchanged from revision 9 (9c559db97845):
the preflight is Python, not Stan.

## revision 9 (defect: sparse season states evaluated out of order; model_version 9c559db97845)

**What the log said.** Every sub-model went INVALID_FIT within 2–4 s. Two messages per chain: `error: code '1' Operation not permitted` and
`<lpmf>: ... parameter[30283] is nan`. The first is not a permissions problem: cmdstanpy prints `os.strerror(exit code)` and errno 1 is
"Operation not permitted"; it only says the chain exited 1. The second is the cause: the same observation index failed on all 100 initial-value
attempts of all four chains, so a *data-determined* quantity was nan, not a random initial value.

**Where it was.** Every Stan program built the (player, season) AR(1) states with `for (j in 2:J) s[j] = rho * s[j_prev[j]] + ...`. `Index.pair`
codes pairs in the order sub-models meet them, and `links()` chains each player's pairs in *season* order, so when a later sub-model meets a player's earlier
season (a player with no known on-field set in 2019 is first coded by `snap` at (m, 2020) and only later by `gain_pass` at (m, 2019)), `j_prev[j] > j`
and `s[j]` read a state not yet assigned: nan in Stan (locals start nan), silently zero in `prior_draws`. On the synthetic league every player is on a
full set every season, so pairs always arrived in season order and the defect was invisible; on the real record it is routine. Running the twelve
sub-models against one shared index (revision 8) exposed it in every sub-model; sequentially it would have hit every sub-model after `snap`.

**Fix.** `Index.chain()` returns `j_prev`, `j_dt` and `j_order` (every pair listed after its predecessor); `_stan_data` passes `j_order`; all six
programs loop `for (k in 2:J) { int j = j_order[k]; ... }`; `prior_draws` walks the same order. The transition law is unchanged; only its evaluation
order. The temporal test now codes a player's 2021 pair before his 2019 and 2020 pairs and checks the chain, the Stan data and the prior walk.

**Housekeeping.** The Stan sources changed, so model_version is new; the INVALID_FIT results under `_probe/fits/cc60511b77f9/` are dead weight and
should be deleted (`rm -rf _probe/fits`). The compiled executables in `stan/` are rebuilt automatically from the changed sources.

## revision 8 (fit orchestration; no model change, model_version unchanged)

- Progress: CmdStan refreshes its console output every 100 iterations by default, so the per-chain bar sat at 1/700 for the first ~40 seconds
  of each fit and then jumped; the sampler was running the whole time (its own ETA read ~5 minutes per chain). `refresh=10` now moves it every
  10 iterations. `refresh` is a console setting, not part of `contract.MODEL`, so model_version is unchanged.
- Concurrency: the twelve sub-models are independent given the training view, so `fit_all` builds every sub-model's observations in the parent,
  compiles each program once, then fits sub-models in a process pool (`VERSION3_FIT_WORKERS`, default cores // chains). Each sub-model still runs its four
  chains in parallel; the gain sub-model's reduce_sum threads are divided by the worker count so the machine is not oversubscribed. Seeds and
  data are unchanged, so draws are identical to the sequential run. With more than one worker the log shows one line per sub-model (queued,
  then finished with elapsed seconds and status) instead of interleaved bars; `VERSION3_FIT_WORKERS=1` restores the bars.
- Resume: each sub-model's draws and metadata are written the moment it finishes (`_probe/fits/<model_version>/<fit_key>/<sub-model>.npz|.json`).
  A re-run after an interruption loads every finished FIT_OK / INSUFFICIENT_DATA sub-model for the same fit key and model version and fits only
  the rest; INVALID_FIT sub-models (sampler or environment failures) are refitted. `fits.json` still marks the complete set.

## revision 7 (check fix, no product-model change)

The revision 6 real-data run reached CHECKS and crashed as INEFFECTIVE_CHECK on SNAPS: the injected fault added 1 to the first row of the snap-count file,
and that row was either outside the comparison (no gsis bridge / no participation row) or already disagreeing, so the disagreement count
was unchanged (7355 against 7355) and the check correctly refused to vouch for itself. The injected fault now lands on a compared row that
agrees, and detection requires both the disagreement count and the sum of absolute differences to rise by exactly one. `record.snaps_cross_check`
gains `frame=True` (returns the joined per-player-game frame) and a `sum_abs_diff` count. No model, record or contract semantics change;
model_version is unchanged.

Everything before CHECKS in that run passed: RAW 45/45 pinned, POINTS 1960 games with the one declared exception, INCOMPLETE/TD-YARDS/BOUNDS 0
violations, REPLAY ≥ 0.998 on every stat, 2019 schedule codes resolved {OAK: LV}, 2019 participation no longer crashes (64 no-play rows with a
disagreeing side are excluded and counted). SNAPS agreement on the file's own convention is 0.26–0.32 with mean |diff| 1.7–2.5: the
snap-count file and the participation file do not share a snap definition; this is printed, not gated.

# Release report — version 3 replacement (2026-10-22/23, revision 5)

## Status: NOT RELEASED. Candidate delivered; no predictive decision on the real record yet.

Terminal status of the delivered candidate on the real nflverse record: **not run** (see "What was executed"). On the synthetic league with
injected posterior draws the end-to-end quality gate recorded `FAILED_REQUIREMENTS` (construction PASS; information INSUFFICIENT; reliable INSUFFICIENT
because `group_tolerance` is undeclared; useful FAIL — "No demonstrated improvement over baseline." — as expected of a posterior that contains no
information; harm INSUFFICIENT because `material_harm` is undeclared; check PASS). That run is evidence that the chain works, not that the
product forecasts well.

## Revision 5: two findings from the first real-data run of revision 4

**POINTS stopped the chain on 16 games, all the 2019 Raiders.** The play-by-play carries a relocated franchise under its current code (`LV`) in every
season; `games.csv` keeps the code of the season (`OAK`). Revision 3 had made the schedule the identity source without reconciling the two, so the
scoring plays (credited to `LV`) never met the schedule's final score (`OAK`). Fix: the schedule's codes are resolved to the play-by-play's franchise
codes through the alias table (OAK -> LV, SD -> LAC, STL -> LA) and the re-codings are counted in the RECORD line (`schedule_codes_resolved_to_pbp`).
Before the play-by-play of a season exists (a forward season) the schedule's codes stand.

**The snap standard.** The SNAPS cross-check agreed on only ~30% of player-games (mean gap ~1.8 snaps) because the record counted live scrimmage downs
while the snap-count file counts every offensive snap. The standard is now declared in `rules.is_offensive_snap` from Rule 5-2-2 narrowed by the
claim: every live scrimmage down counts; a down nullified by a penalty counts when the recorded personnel shows an offensive unit (a QB, no K or P);
tries and kicks never count; a no-play without recorded personnel is unknown. Participation, finishing, snap propensity and the SNAPS cross-check
use this standard; opportunity denominators and credits use live events only (a nullified down credits nothing).

## Revision 4: the reviewer's required corrections to revision 3

| requirement | done |
|---|---|
| No betting inputs, permanently | `contract.PROJECTION_INPUTS` is the allowlist; the schedule reader refuses market columns at the read (`spread_line`, `total_line`, moneylines, odds); a test asserts no fit, table or world source mentions them |
| Sparse season states preserve the temporal model | the gap step is `rho^dt` with variance `tau^2 (1 - rho^(2dt))`, the stationary chain's exact dt-step law; a test compares it with the dt one-step chain. Correction of my wording: the implementation is *intended* to preserve the model; dense-vs-sparse agreement on the real fits is still to be observed. An annual state does not carry within-season role change; that is the game-level draw only (`contract.MODEL["season_state"]`) |
| Personnel = composition, with provenance | recorded personnel and roster-derived composition are two tables (`personnel_recorded`, `personnel_roster`); the recorded one is the measurement, the fallback is used only when no recorded personnel exists; the counts name the source. The chain personnel group -> named participants (snap propensity per slot) -> on-field risk set -> Dirichlet-weighted allocation exists in the simulator; routes are not modelled, allocation is per on-field snap |
| Coherent opponent vector per world | each sub-model's `v_def` is drawn once per world and reused for every play; the sub-models' effects are separate, never one summary applied to volume, efficiency and totals. Correction: a defence allowing 4.5 vs 3.8 yards per rush does not mechanically raise a forecast; the coefficients are conditional associations |
| Game-flow validation beyond description | `grader.gameflow`: realized team-game lenses of the priced games against the simulated distributions (same cutoff and population as the player lines): 10-90 coverage, mean error with game-clustered SE, share above. Reported in the run log row; the reviewer may promote it to a release requirement. The 1.86x simulated drives on the synthetic run is traced through possession changes, drive endings and the clock before any real-data reading; nothing is rescaled |
| Issue-time population | `contract.ISSUE_TIME`: kickoff; the listed population is the gameday ACT list minus Out; an earlier issue time is unsupported until an issue-time roster snapshot exists (ACT + INA - Out would be a retrospective reconstruction) |
| Forecast vs evaluation availability | `record.availability(season)` reports both, with the reason; printed by the quality gate and stored in the row |
| Dataset identity | identity = the evaluation population (`holdout-<season>`); file hashes are attributes of each access; copies, re-hashing and later file revisions cannot re-open it |

## Revision 3: cost fix inside the reviewers' and proposals' scope

Scope taken only from the review, the "one authority per fact" handoff, the CSV-architecture proposal and the lens document.

**Cost (reviewer).** Rev 2's beta-binomial still built a 170k-row loop and a dense player × season state matrix. Rev 3 gathers effects with
vectorised indexing (`a_pos[pos] + m[pl] + s[ps] + v_def[df]`), keeps one AR(1) season state per (player, season) pair actually observed (`J`
sparse pairs with `j_prev`/`j_dt`), and drops the dense `P x S` matrix. Same model, same priors; the parameter count falls to about one state per
player-season that exists.

**Proposal §1 / CSV content.** `games.csv` is the canonical schedule and the source of team identities (issue-time; the play-by-play games are
cross-checked against it and disagreements counted). `players.csv` bridges gsis and pfr ids, so `snaps_*` cross-checks the participation-derived
snaps per player-game (SNAPS print check, injected fault). The participation file's recorded `offense_personnel` is the personnel table's source;
roster-derived counts are the fallback and are counted. Roster positions in these files are coarse (QB/RB/WR/TE/OL/DB/DL/LB/K/P/LS), so FB folds
into RB.

**Proposal §4 (opponent).** Every opponent-aware sub-model (call, branch, result, touchdowns, gains) carries a hierarchical defence team-season
effect `v_def`; the simulator draws the opponent's effect per world. The schedule's `spread_line`/`total_line` are pregame context the reviewer has
not admitted: nflverse lines are closing lines, and their issue-time status needs a decision (`contract.MODEL["opponent"]`).

**Proposal §3 and the lens document.** `record.team_game_facts` / `team_baselines(cutoff)` give season-to-date numerators and denominators per
team and side (opportunity, play selection, efficiency, continuation, scoring). The simulator counts the same lenses per world, and
`grader.patterns` prints simulated per-game means against the baselines with the share of sides whose baseline lies in the simulated 10–90 band.
It aims; it does not grade.

**Proposal §2/§8.** `record.materialize` writes the four fact tables (game, plays, team_game, player_game) once per data version under
`_probe/facts/<data_version>/` with a source-hash manifest. `version 1/facts` from the old product is not read: its play kinds (pass/run/sack) are
coarser than `rules.py` and its team codes differ (LAR vs LA).

**Proposal §7.** 2022 in `discovery/` and `raw/` are identical bytes; the dataset identity is content-based, so one status. `held_2026` has no
participation file: `record.participation` names the deficiency and every finish state is UNKNOWN, so 2026 lines can be priced but not graded
under the product's claim's condition. **Finding from the real files:** the weekly roster file's `status` is the gameday active list (`INA` = inactive,
announced ~90 minutes before kickoff): 34 of 42 week-1 2024 "Out" players are already `INA`, not `ACT`. "ACT minus Out" is therefore a kickoff-time
population. A forecast issued earlier in the week would need `ACT + INA minus Out` (and a Doubtful policy). Owner decision; unchanged here.

## Revision 2 (same evening): why the first fit took hours, and what changed

The first quality gate run on the real record compiled `binom_hier.stan` (the Stan sources are valid) and stalled on the snap-propensity fit: that
sub-model carried one random effect per player-game (~56,000 parameters informed by one count each), and the allocation sub-models were built the same
way. Unidentified high-dimensional posteriors push NUTS to its tree-depth cap; the full scope was days. Revision 2 integrates the game-level
effect out analytically (a registered model change, new `model_version`):

| sub-model | revision 1 | revision 2 |
|---|---|---|
| snap propensity | binomial-logit + player-game effects | beta-binomial (`betabinom_hier.stan`): mean from player/position/season effects, one precision `phi`; the simulation draws each player's game rate once per world from Beta(mu phi, (1-mu) phi) |
| target / rusher allocation | per-snap softmax + player-game effects | Dirichlet-multinomial per team-game (`dirmult_alloc.stan`) over the players on the field for the kind, exposure offset = log on-field snaps, one concentration `kappa`; the simulation draws the game's weights once per world from Dirichlet(kappa pi) and allocates each snap among the players on the field in proportion |
| branch, result, TD | per-player-game effects | no game-level effect (declared in `contract.MODEL["game_variation"]`); identical rows collapsed into weighted rows |
| call | per-snap rows | identical rows collapsed; team-game effect kept |
| gains | one row per play | identical rows collapsed; `reduce_sum` with threads |

Covariates are binned (5-yard field position, down class, score difference in scores, yards-to-go bins) so rows collapse. Parameter counts fall
from ~10^5 to ~10^4 per sub-model; the categorical sub-models shrink ~10x in rows. The gain sub-models remain the slowest (every play keeps its own legal
support). Revision 2 fitted on the real record (betabinom_hier compiled; see the reviewer's quality gate log) before revision 3 superseded it.

## What changed in the predictive product

- **One joint environment.** A game is simulated as a vectorised state sequence over equal-weight worlds: shared parameter draw per world, a legal
  11-player lineup per snap (personnel group × fitted snap propensities, sampled without replacement), play call, dropback branch (pass / sack /
  scramble / spike) with the passer chosen first, conditional allocation of receiver and rusher over the players on the field, linked outcomes
  (completion / interception / TD branch, discretised Student-t gains on the legal support), rule-based transitions (downs, line to gain, clock,
  penalties with half-the-distance enforcement, punts, field goals, turnovers, safeties, tries, kickoffs, halves, regular-season overtime).
  `w_targets / w_carries / w_attempts / w_tds`, the share-game deal, `role_counts`, `outcome_pool`, FIELD substitution and the undealt-run exemption
  are gone.
- **One finishing mask per player** (on the field for a snap of his side's simulated final offensive drive), shared by every stat; `n_over`,
  `n_finished_worlds`, `n_worlds` are integers; PMF, mean, quantiles come from the same draws; Monte Carlo SE per line, worlds grown to the budget
  and `insufficient_simulation` declared beyond it.
- **Tri-state finishing** in the record: the final drive is read from the play sequence first; TRUE needs one observed snap, FALSE needs full
  coverage, otherwise UNKNOWN. The benchmark is the player's prior games finished TRUE this season (integer sum and count, event `Y*avg_n > avg_sum`).
- **Issue-time rosters** read no participation: team identities are the season's play-by-play codes plus a versioned alias table; unresolved stays
  unresolved.
- **Typed events and linked credits** in `rules.py`: passer/receiver share one event; laterals split yards; sacks carry no passing stat; kneels are
  carries; spikes are attempts. Record credits replayed against the official weekly file per stat (REPLAY check, with an injected fault).
- **Hierarchical sub-models in Stan** (CmdStanPy): softmax allocation over the observed risk set (target, rusher, passer), binomial-logit (snap
  propensity, play call, TD given event), categorical (dropback branch, pass result with linked receiver and passer effects), discretised Student-t
  gains (completions, runs and scrambles, sacks). Persistent player effect + AR(1) season state (`rho = exp(-lambda*dt)`, dt in seasons) + position
  effect + player-game effect, all non-centered, all priors proper and declared in `contract.MODEL`. Non-player game sub-models are conjugate
  Dirichlet/Beta posteriors. Typed results: FIT_OK / INSUFFICIENT_DATA / INVALID_FIT / UNSUPPORTED_INPUT; sampler diagnostics quality gate FIT_OK.
- **Structured decisions** (`grader.py`): construction, information, reliable (game-cluster bootstrap max-statistic simultaneous intervals over
  cell × said-tercile × exposure-tercile groups, family level 0.05), useful (pooled paired Brier vs B1 beyond the simultaneous bound), harm, check
  regression cases, certifiable. The quality gate turns them into PASSED / FAILED_REQUIREMENTS / INSUFFICIENT; STOPPED and CRASHED are recorded with phase and
  exception. Certification access is tracked by dataset identity and marked before outcomes are read; a second opening is refused.
- **Manifest** generated once by `run log.manifest()` (code, Stan sources, data, model version, dependencies, fit keys) and used identically by the
  guard, its injected test and the report's selection.

## What was actually executed (this delivery)

Environment: Linux sandbox, Python 3.13, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1. **No network to PyPI → CmdStanPy / CmdStan could not be installed,
and the real nflverse raw files are not here.** Therefore:

1. `tests/test_product.py` — 12 construction tests on a generated league (3 seasons × 8 weeks × 4 teams), all PASS (`evidence/tests_synthetic.log`):
   immutable raw rows and exact replay of credits against the official tally; linked credits and laterals; tri-state finishing with the injected
   final-drive removal reading UNKNOWN never FALSE; the information boundary (no hold-out, no post-fit-week rows; evaluation access ≠ training access;
   future weeks do not change an earlier view); issue-time rosters; the production reducer with injected corruptions caught; the simulator's identities
   over every world; one mask per player; PMF ↔ p ↔ mean reconciliation; contract key uniqueness; typed fits; the discretised-t sampler reproducing
   `q(y)/Σq`; grader decisions and regression cases; the end-to-end quality gate (DISPLAY, KEY, NO WRITE refusal, certification access, CRASHED record).
2. `quality quality_gate.py` end to end on the synthetic league with **injected posterior draws** (not fitted): `evidence/gate_synthetic_injected_posterior.log`.
   4,800 worlds, every construction audit 0, 580 lines priced, grader decisions as above.
3. **Not executed:** any Stan fit (the `.stan` programs are untested by a compiler here), any run on the real record, any chronological
   development evaluation against the frozen version 2 reference, any certification. The reference-to-candidate comparison on real data is therefore
   **not available**; nothing here claims predictive improvement.

## Remaining limitations and inputs

- Owner declarations missing: `contract.POLICY["group_tolerance"]`, `["material_harm"]`. Without them RELIABLE and HARM are INSUFFICIENT by design.
- Stan programs must compile on your machine (`cmdstanpy.CmdStanModel(stan_file=...)` compiles on first use). Fit cost on real data is large
  (player-game effects on tens of thousands of opportunities per season); `contract.MODEL["stan"]` holds chains/iterations.
- Defensive opponent effects are not modelled; game effects across mechanisms are independent draws (no joint Stan fit supplies a correlation).
- Participation covariates (on-field sets) are retrospective nflverse data; the replay is retrospective, not a live-deployment equivalence.
- Reported eligibility (5-3-1) has no column: a lineman's target is kept as an observation of his eligibility that play; otherwise receivers are
  the on-field players at QB/RB/FB/WR/TE.
- Lateral yardage columns are read when present and named as a deficiency when absent.
- Historical evidence of version 2 (`_probe` logs, run log, `map.json`) is untouched in `version 2/`; this package starts a new `_probe/` and run log.

## Next steps for the reviewer

1. `pip install -r requirements.txt`, install CmdStan, copy the raw files or set `VERSION3_RAW`.
2. `python3 tests/test_product.py`; `python3 quality quality_gate.py --pin` (development run); read the GROUP table and decisions in the run log row.
3. Declare the two tolerances in `contract.POLICY`; re-run; only then consider `VERSION3_SCORE_HOLDOUT=2022 python3 quality quality_gate.py` — once.
