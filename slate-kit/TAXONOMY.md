# Slate Kit taxonomy - one name per meaning (version 3)

Every term is at most two words and means one thing. Names join terms with one grammar. When shortening made two names collide, the data decided: identical values ->
one name; different values -> two names. Standing: **in use**; **new** (code moves in the one full pass); **registered** (source family, not yet in facts); **OPEN**.

| Kind | Group | Name | Retired spellings | Meaning | Standing |
|---|---|---|---|---|---|
| Rule | All | one meaning, one name | - | Each meaning has exactly one name; no abbreviation, synonym or second spelling. Raw files keep source spellings; old records are read through canon.plain(), split by file where one old name had two meanings; CHARTER prose is bridged by this matrix. | in use |
| Rule | All | terms of two words or fewer | - | Every term (quantity, aggregate, window, scope, qualifier) is at most two words; identifiers join terms. A collision from shortening is collapsed when the data shows identical values, otherwise each meaning keeps its own name. | new |
| Rule | All | grammar | - | `<scope><quantity>_<aggregate>_<window>`; a single past value is `<quantity>_<window>`. Example: snap_share_mean_season_pregame. | new |
| Rule | All | `_status` | - | Only a designation published by the league or a team (week N, outside the information set); bare status is retired. | in use |
| Rule | All | coverage | - | Only calibration coverage (share of outcomes at or below a quantile). Whether a player-week was forecast is `issued`. | in use |
| Rule | All | participation | - | Only availability (did he play); on-field presence is `on_field_*`. | in use |
| Rule | All | slot | - | Only the depth-chart slot (`depth_slot`). | in use |
| Rule | Sources | source shares stay out | - | Source-computed target_share / air_yards_share never enter facts; snap_share (PFR snaps) is not replaced by on-field data. | in use |
| Rule | All | domain acronyms | - | dk, dst, td, qb, rb, wr, te, epa, id, pbp kept as written (owner). ftn is a source name (FTN Data): raw file names only. | in use |
| Rule | Merge | merge suffix names its source | - | `_dk` / `_ours` (fetch.py:79); `_at_rows` (h7.py:68, was `_at`); `_st` (score_d / score_y) and the score_s `_prev` merge are named when those files move. | new |
| Word | Window | `season_pregame` | _season_avg, _season_mean, _ws, _std, _to_date (rename-map meaning), earlier_games_this_season | His played games this season before this game; nothing from this game (p.py:49 = retarget.py:21 = ystick.py:164 to 5.6e-17; avail.py / score_t.py through merge_asof allow_exact_matches=False) | new |
| Word | Window | `season_postgame` | _through_game, _thru, through_this_game_this_season, _to_date (j.py:27, retarget.py:62 before the merge) | His played games this season up to and including this game | new |
| Word | Window | `stint_pregame` | _to_date (alloc.py:42), earlier_games_this_season_with_team | His played games this season for his current team (his stint) before this game | new |
| Word | Window | `recent1` | _last_game, _w1, previous_game_this_season | His most recent played game this season before this game (empty in his first game of a season) | new |
| Word | Window | `recent3` | _last3_avg, _w3, previous_3_games_this_season | His 3 most recent played games this season before this game (all 3 required) | new |
| Word | Window | `previous_1`, `previous_2`, `previous_3` | _lag1, _lag2, _lag3, _l1, _l2, _l3, previous_game, second_previous_game, third_previous_game | His 1st / 2nd / 3rd previous played game; may cross seasons (differs from recent1 on 2,815 of 40,741 rows) | new |
| Word | Window | `team_season_pregame` | snap_share_season_mean_out_zero (window part) | The team's games this season before this game; a team-game he missed counts as 0 (p.py:75) | new |
| Word | Window | `team_recent1`, `team_recent2`, `team_recent3` | st1, st2, st3 (window part) | The team's 1st / 2nd / 3rd previous game this season; empty when he has no row there (p.py role_states) | new |
| Word | Window | `previous_season` | _prev (p.py:50) | The previous season | new |
| Word | Aggregate | `mean` | avg, average, std (as mean), _m | Arithmetic mean of observed values | new |
| Word | Aggregate | `median` | med, dmed | Median | new |
| Word | Aggregate | `standard_deviation` | sd, dsd, std (as deviation); never "spread" (betting term) | Standard deviation | new |
| Word | Aggregate | `standard_error` | se, std_err | Standard error | new |
| Word | Model output | `expected` | exp | A model's mean | new |
| Word | Model output | `prediction` | _pred, _hat | A model's point output | new |
| Word | Probability | `probability_` | p_ (not model file stems p_coef / p_walk / p_report) | A probability | new |
| Word | Forecast | `rank` | pit, pct | Where the result fell inside the forecast, 0 to 1, full precision | new |
| Word | Forecast | `percent` | pct (as 0-100) | A value on the 0-100 scale | new |
| Word | Ordered band | `tier` | state (snaps), rs, sstd | An ordered band; `state` is kept only for law state | new |
| Word | Comparison | `baseline` | base (as reference law) | The reference law in a comparison | new |
| Word | Comparison | `effect` | change (event minus control) | Event minus control | new |
| Word | Comparison | `change` | trend, t_ | Versus his own earlier mean | new |
| Word | Ordinal | `game_number` | number (as ordinal), no, tgi, team_game_no | Team's game number this season | new |
| Word | Shrinkage | `strength` | k, kb, kr, shrink, KGRID, KB, RGRID (spine) | How strongly a value is shrunk toward a group value | new |
| Word | Weights | `decay` | WGRID, w | Exponential decay weight per earlier game | new |
| Word | Other | opponent, opportunity / opportunities, defense, position, seconds, times, availability, fraction | opp, oppo, opps, def, pos, secs, x, avail, frac | Plain words | new |
| Prefix | Scope | `team_` | _team_ inside suffixes, _ts, _t3 | The team's own value | new |
| Prefix | Scope | `opponent_offense_` | oppo_, opp_offense_ | The opponent's own offense | new |
| Prefix | Scope | `defense_allowed_` | dal_, opp_def_allowed_, opponent_defense_allowed_ | What the opposing defense has allowed | new |
| Prefix | Scope | `position_defense_` | oppd_, opp_def_vs_pos_, opponent_defense_vs_position_ | Opposing defense against this position, vs league | new |
| Prefix | Scope | `teammate_`, `vacated_` | tm_, abs_ | A teammate's value; share left by absent role players | in use |
| Prefix | Field zone | `redzone_`, `goal_line_` | rz_, gl_ | Inside the 20; inside the 5 | in use |
| Prefix | Filter | `filter_` | f_ (contexts.py only) | Local-level filter forecast | in use |
| Column | Identity | `player_id`, `position`, `opponent`, `is_home` | gsis, pos, opp, home | Player ID; QB / RB / WR / TE; opposing team; home flag | in use |
| Column | Identity | `game_number` | tgi, team_game_no, team_game_number | Team's game number this season | new |
| Column | Outcome | `dk_points`, `steady_points`, `td_points`, `td_count`, `dst_points`, `beat_own_median` | dk, steady, tdpts, tde, dst_pts, beat | Points and counts | in use |
| Column | Outcome | `redzone_opportunities` | rzo, redzone_opps | Red-zone opportunities | new |
| Column | Outcome | `steady_change`, `td_change` | t_steady, t_td | Steady / TD points versus his own earlier mean | in use |
| Column | Role | `target_share`, `carry_share`, `air_yards_share`, `snap_share`, `opportunities` | tgt_sh, car_sh, air_sh, snap, opps | Shares of team volume; targets + carries + attempts | in use |
| Column | Role | `snap_change` | utr, snap_trend | recent1 snaps minus his season_pregame mean | new |
| Column | Role | `role_tier` | st | Role tier 0-3 from this game's snap share: 0 did not play, 1 under .35, 2 .35-.70, 3 .70 and over (p.py role_states) | new |
| Column | Role | `role_tier_team_season_pregame` | sstd, season_role_state | Role tier 0-3 from his team_season_pregame snap mean (absent = 0; under .05 = 0) | new |
| Column | Role | `role_tier_team_recent1`, `role_tier_team_recent2`, `role_tier_team_recent3` | st1, st2, st3; a.py last | role_tier at the team's 1st / 2nd / 3rd previous game (labels for printing only) | new |
| Column | Role | `snap_tier_season_pregame` | rs, snap_state | Snap tier 1-3 from his season_pregame snap mean (9 producers bin snap_share_season_avg) | new |
| Column | Role | `snap_share_mean_team_season_pregame` | snap_share_season_mean_out_zero | Mean snap share over the team's earlier games this season, absent = 0 (p.py:75; one producer) | new |
| Function | Calibration | `decile_deviation` | mad, ds_mad, rg_mad | Deviation of the decile histogram from uniform; one meaning, one name (canon SRC <- ystick.py) | new |
| Column | Opportunity | `share@{w}` | sh@{w} | Decay-weighted share at weight w (7 spine files build it locally) | new |
| Pointer | Names | TAXONOMY_short_names.tsv | 4847 short variable names | Variable names, one plain 1-2 word meaning per file (sha256 62ed2dbcb01c066a; CHARTER ONE FULL RENAME PASS) | new |
| Column | Role | `snap_tier_season_pregame` (low / mid / high is printing only) | rsb, snap_state_label; gatesim.py:22 string-valued snap_state | snap_state_label was snap_tier_season_pregame mapped {1: low, 2: mid, 3: high} (at_t.py:19, at_wall.py:35; one-to-one in at_rows): the column is dropped and labels are printed from snap_tier_season_pregame | new |
| Column | Role | `role_collapse` | collapse | Snaps fell well below his mean | in use |
| Column | Role | `games_season_pregame`, `games_season_postgame` | n_prior, games_before, n_thru, games_through_game | Count of his played games this season before / through this game | new |
| Column | Role | `team_previous_1`, `game_number_previous_1`, `week_previous_1` | prev_team, team_last, prev_played_team, last_played_team, tgi_last, last_played_team_game, last_wk, last_played_week | His team / team game number / week in his previous played game | new |
| Column | Role | `snap_share_mean_season_pregame`, `snap_share_mean_stint_pregame` | role, snap_share_to_date (j.py and retarget.py after the merge; alloc.py with team) | His snap share mean over the window | new |
| Column | Role | `depth_slot`, `has_depth_slot` | slot, in_slot, has_slot | Depth-chart slot; holds one | new |
| Column | Role | `plays_elasticity`, `elasticity_times_size_change`, `proportional_times_size_change` | elas, elas_x, prop_x | His response to team play volume | new |
| Column | Participation | `games_missed`, `games_missed_band`, `did_not_play` | gap, gapb, absent | Team games missed since he played; 0 / 1 / 2+; did not play | in use |
| Column | Participation | `played_team_recent1`, `missed_team_recent1` | gapg, played_last_or_missed, self_missed, missed_last_team_game | Played / missed the team's most recent game | new |
| Column | Participation | `probability_plays`, `probability_plays_availability`, `probability_plays_transition`, `probability_plays_transition_walkforward` | p_play, p_plays, p_a, p_plays_a, p_t1, p_plays_t1, p_T1, p_plays_t1_walkforward | Probability he plays: overall; availability model; transition model (issued / historical fit) | new |
| Column | Participation | `probability_absent_calibrated`, `probability_absent_logistic` | q_M, q_R, p_absent_calibrated, p_absent_logistic | Probability he is absent: calibrated history model; logistic with the week's tier | new |
| Column | Participation | `probability_absent_tier` | q_B, p_absent_base | Training absence rate of his snap tier (avail.py:64) | new |
| Column | Participation | `roster_status`, `report_status`, `practice_status` | status (facts) | Published designations (week N, outside the information set) | in use |
| Column | Distribution | `probability_near_zero`, `probability_near_zero_calibrated`, `probability_near_zero_raw` | pi (ystick family), near_zero_p, pi_cal, pi_raw, p_near_zero, p_near_zero_calibrated, p_near_zero_raw | Probability of a game at or below 1 DK point | new |
| Column | Distribution | `probability_nonzero` | pi (hurdle walls, native_laws.py, spine_compose.py), p_event, p_nonzero | P(Y > 0); p_event duplicated pi in f6_zero_history_hurdle.py:33 and is dropped | new |
| Column | Distribution | `probability_zero` | f0 (hurdle walls, spine_compose.py) | The negative binomial's probability of zero before truncation | new |
| Column | Distribution | `center_fifth`, `center_tenth`, `center_tier` | fifth, tenth, tier | Where his projection falls; projection tier | in use |
| Column | Distribution | `dk_points_median_season_pregame`, `dk_points_standard_deviation_season_pregame` | dmed, own_median_dk, dsd, own_dk_sd | Median / standard deviation of his DK points this season before this game (retarget.py:38) | new |
| Column | Distribution | `dk_points_mean_season_pregame` | dk_expected (j.py:31 only) | His DK points mean this season before this game | new |
| Column | Distribution | `dk_points_expected`, `dk_points_minus_expected` | exp, dk_expected (other producers), resid, dk_minus_expected | A model's expected DK points; actual minus expected | new |
| Column | Distribution | `dk_points_volatility`, `steady_points_per_opportunity`, `td_points_share_of_dk_points` | vol, dk_volatility, eff, steady_per_opp, tdshare, td_share_of_dk | Spread relative to mean; steady points per opportunity; TD share of points | new |
| Column | Law | `mean`, `negative_binomial_size`, `probability_per_trial`, `beta_binomial_concentration`, `standard_deviation`, `standard_deviation_form`, `standard_deviation_parameter`, `mean_yards_per_count`, `yards_variance_per_count`, `conditioned_on_draw`, `probability_nonzero`, `positive_part_untruncated_mean`, `positive_part_negative_binomial_size`, `support_prior_gamma_shape`, `support_prior_gamma_rate`, `support_event_sum`, `support_games` | p_per_trial, p_nonzero | Native law schema columns | new (two), in use (rest) |
| Column | Team + game | `quality_gap`, `blowout`, `game_plays_actual`, `short_rest`, `long_rest` | qgap, blow, gp, short, long | Team and game descriptors | in use |
| Column | Team + game | `neutral_seconds_per_play` | neutral_spp, neutral_secs_per_play | Pace in neutral situations | new |
| Column | Team + game | `team_result_recent1`, `team_margin_recent1`, `team_week_recent1` | res_last, last_result, margin_last, last_margin, pw, team_prev_week | The team's most recent game: result; margin; week | new |
| Column | Price + joint | `salary_thousands`, `log_likelihood_independent` | sal_k, l0 | Salary in $1,000s; fit if players were independent | in use |
| Column | Judging | `outcome_rank`, `outcome_rank_scored` | result, result_u, outcome_pit, outcome_pit_scored | Where the result fell in the forecast; scored after the game | new |
| Column | Judging | `outcome_percent` | result_pct, outcome_pit_pct | outcome_rank x 100 rounded to one decimal, display only, never tested (register.py) | new |
| Column | Judging | `composed_rank` | pit_comp | Where the result fell in the composed distribution | new |
| Column | Judging | `link_chain_class`, `tail_coverage_band` | stratum, status (calibration) | Link-chain study class; tail coverage against the +-2 slate standard error band | in use |
| Column | Judging | `snap_effect` | role, snap_share_to_date (link_chain.py key) | Event minus control change in snap share | new |
| Column | Judging | `finite_loss_baseline`, `finite_loss_candidate` | f0, f1 (loss masks) | Rows whose baseline / candidate loss is finite | new |
| Column | Judging | `probability_collapse`, `probability_role_collapse`, `probability_role_collapse_twin`, `collapse_rate` | pi (regime_test.py), p_col, p_col_twin, base_col | Collapse-state probability; role-collapse probability; its twin; observed collapse rate | new |
| Column | Judging | `cell_keys_train`, `cell_keys_test` | ka, kb (owner-map files) | Cell keys of the training / test rows | new |
| Column | Joint | `thinning_probability` | pi (jexpose.py) | Probability used to thin game draws | new |
| Column | Registry | `hypothesis_priority` | role, snap_share_to_date (register.py field) | PRIMARY / secondary confirmatory | new |
| Column | Issue | `issue_mode`, `issued`, `not_issued_reason` | status (issue files), "coverage status" | Prospective or dry run; issued or not; why not | in use / new |
| Column | Correlation panel | `pair_dependence` | "pair status" | EARNED POSITIVE / EARNED NEGATIVE / TESTED - NO MATERIAL IMPACT / UNRESOLVED / UNTESTED | new |
| Column | Source facts | `defense_box_count`, `pass_rusher_count`, `charted_qb_location`, `on_field_player_ids`, `on_field_offense_share` | raw source spellings | Registered source-family names | registered |
| Column | Raw | `Status` | - | DK DFS price file injury tag, raw only | in use (raw) |
| Column | Kept plain | attempts, carries, completions, passing_yards, passing_tds, passing_interceptions, receptions, receiving_yards, receiving_tds, receiving_air_yards, rushing_yards, rushing_tds, targets, sacks_suffered, season, week, team, game_id, salary, played, epa_play | - | Already plain | in use |
| File | Judging | `f8_tail_coverage_band.csv` | f8_tail_calibration_status.csv | Tail coverage band table | in use |
| Python | Constant | `SHRINKAGE_STRENGTH_GRID`, `TD_RATE_STRENGTH_GRID`, `RATE_STRENGTH_GRID` | KGRID, SHRINK_GRID, KB, RGRID (spine family) | Strengths tried: share / mean shrinkage; TD-rate shrinkage; rate shrinkage | new |
| Python | Name | `shrinkage_strength`, `td_rate_strength`, `rate_strength` | shrink_k, kb (spine family), kr | The chosen strengths | new |
| Python | Constant | `NEGATIVE_BINOMIAL_SIZE_GRID`, `DECAY_WEIGHT_GRID` | RGRID (f6 files), WGRID | Negative binomial sizes tried; exponential decay weights tried | new |
| Python | Function | `read_table`, `rank_of` | pd.read_csv (new reads), pit_of | Reader door; where a result falls in a forecast | in use / new |
| Python | Function | `position_mode_season_pregame` | position_to_date, position_most_frequent_earlier_games_this_season | Most frequent stats label over his played games this season before this game, ties to the most recent | new |
| Python | Function | `mean_season_pregame`, `mean_recent3` | std, w3 (retarget.py:21) | Window-mean helpers | new |
| Python | Function | `paired_by_slate`, `passes_quality_gate`, `log_loss` | paired, gate, ll | Paired slate difference; the gate; per-row log loss | in use |
| Python | Name | `log_likelihood`, `log_likelihood_model`, `spearman`, `standard_error`, `train`, `test` | loglik, ll (j.py), sp, se, std_err, tr, te | Joint log-likelihood; model's; rank correlation; standard error; rows | in use / new |
| Python | Constant | `SKILL_POSITIONS`, `RB_WR_TE`, `AVAILABILITY_INPUTS`, `NULL_DRAWS`, `TEST_BATTERY`, `NEAR_ZERO_DK`, `EXPECTED_POINTS`, `CENTER_TIERS`, `WINDOW_FRACTION` | SK, SCPOS, POS3, AVF, AVAIL_INPUTS, NNULL, BAT, ZERO, EXP, TIERS, WIN, WINDOW_FRAC | Shared constants | in use / new |
| Python | Name | `null_scores`, `null_95th`, `fails_noise_95th`, `peer_mean`, `shrunk_mean` | nul, p95, n95, peer, shrunk, shrunk_avg | Null results; shrinkage target and result | in use / new |
| Python | Name | `near_zero_rank`, `ordinary_rank`, `ordinary_rank_window`, `ordinary_scale` | f0 (ystick scope), ford, f_smo, near_zero_pit, ordinary_pit, ordinary_pit_window, so_te | Parts of the outcome rank; ordinary-game spread | new |
| Python | Name | `history_rows`, `coming_week_rows` | Hst, Nx, NX | Past rows; the coming week's rows | in use |
| Split | classe.py | `warning_tier` | tier (classe.py only) | Injury-report warning tier | in use |
| Split | ystick.py | `wr_rows` | WS (ystick.py only) | WR short-history rows | in use |
| Kept | All | single-letter loop names; st1-st3; h7_fail, ss_fail, ds_mad, rg_mad | - | Kept as is | in use |
| Column | Judging | `fail_rate_candidate`, `fail_rate_baseline` | f1, near_zero_pit (shorthist.py:107-111 only; v1 renamed f0 there by mistake) | Calibration fail rate of the candidate P1 / baseline P0 | new |
| Note | f6_zero_history.py | p (line 31) -> probability_nonzero | p, p_event | p = zeros: the zero-history law gives P(Y > 0) = 0 | new |
