"""facts.py - canonical facts (Slate Kit module map: facts).  Raw verified files in, three tables out, nothing modelled; and the one door every other module reads them through.
  facts/player_game.csv.gz  one row per player-week a player was priced, listed or recorded: what he did (stats, DK points, snap share, team-volume shares, red-zone /
                            goal-line opportunities, played or not) and what was published before kickoff (DK salary, final injury designation and practice status)
  facts/team_game.csv.gz    one row per team-game: closing line, rest, points for / against, plays, dropbacks, DST DK points, DST salary
  facts/game.csv.gz         one row per game: schedule, closing line, score, roof, surface, temperature, wind
  facts/facts_report.txt    coverage per season, join rates, the self-check against the canonical 2019-21 pools and the independent check against DraftKings' recorded points
The door: read_table (round-trip float parse), team_game() and load() - week N's publications outside the information set (WEEKN) are dropped there and nowhere else.
Identity: team_fixes and norm are the one definition of the keys that join every source.  plain() is the one map from retired spellings to canonical names.
Outcome columns are facts about the game; they are labels, never inputs to anything about the same week."""
import os, re, glob, numpy as np, pandas as pd
from ingest import ROOT, DATA_DIR, FACTS_DIR, DKW, Report, sealed_seasons, ET
# ---------------- the reader door ----------------
def read_table(path, **read_options):
    """pandas' default float parser does not recover the value a writer wrote; float_precision="round_trip" does."""
    return pd.read_csv(path, float_precision="round_trip", **read_options)
# ---------------- identity keys ----------------
team_fixes = {"OAK": "LV", "SD": "LAC", "LA": "LAR", "STL": "LAR"}
def norm(s): return s.astype(str).str.lower().str.replace(r"[^a-z ]", "", regex=True).str.replace(r"\s+(jr|sr|ii|iii|iv|v)$", "", regex=True).str.replace(" ", "")
def fix_names(series): return series.replace(team_fixes)
# ---------------- canonical names: retired spelling -> canonical (TAXONOMY translation) ----------------
PLAIN_COL = {'absent': 'did_not_play', 'air_sh': 'air_yards_share', 'beat': 'beat_own_median', 'blow': 'blowout', 'car_sh': 'carry_share', 'collapse': 'role_collapse', 'dk': 'dk_points', 'dmed': 'dk_points_median_season_pregame', 'dsd': 'dk_points_standard_deviation_season_pregame', 'dst_pts': 'dst_points', 'eff': 'steady_points_per_opportunity', 'elas': 'plays_elasticity', 'elas_x': 'elasticity_times_size_change', 'exp': 'dk_points_expected', 'fifth': 'center_fifth', 'gap': 'games_missed', 'gapb': 'games_missed_band', 'gapg': 'played_team_recent1', 'gp': 'game_plays_actual', 'gsis': 'player_id', 'home': 'is_home', 'in_slot': 'has_depth_slot', 'l0': 'log_likelihood_independent', 'last_wk': 'week_previous_1', 'long': 'long_rest', 'margin_last': 'team_margin_recent1', 'n_prior': 'games_before', 'n_thru': 'games_season_postgame', 'near_zero_p': 'probability_near_zero', 'neutral_spp': 'neutral_seconds_per_play', 'opp': 'opponent', 'opps': 'opportunities', 'p_T1': 'probability_plays_transition_walkforward', 'p_a': 'probability_plays_availability', 'p_play': 'probability_plays', 'p_t1': 'probability_plays_transition', 'pi': 'probability_near_zero', 'pi_cal': 'probability_near_zero_calibrated', 'pos': 'position', 'prev_team': 'team_previous_1', 'prop_x': 'proportional_times_size_change', 'pw': 'team_prev_week', 'q_B': 'probability_absent_tier', 'q_M': 'probability_absent_calibrated', 'q_R': 'probability_absent_logistic', 'qgap': 'quality_gap', 'res_last': 'team_result_recent1', 'resid': 'dk_points_minus_expected', 'result': 'outcome_rank', 'result_pct': 'outcome_percent', 'result_u': 'outcome_rank_scored', 'role': 'snap_share_to_date', 'rs': 'snap_tier_season_pregame', 'rsb': 'snap_state_label', 'rzo': 'redzone_opportunities', 'sal_k': 'salary_thousands', 'self_missed': 'missed_team_recent1', 'short': 'short_rest', 'slot': 'depth_slot', 'snap': 'snap_share', 'sstd': 'role_tier_team_season_pregame', 'steady': 'steady_points', 'stratum': 'link_chain_class', 't_steady': 'steady_change', 't_td': 'td_change', 'tde': 'td_count', 'tdpts': 'td_points', 'tdshare': 'td_points_share_of_dk_points', 'team_last': 'team_previous_1', 'tenth': 'center_tenth', 'tgi': 'team_game_no', 'tgi_last': 'game_number_previous_1', 'tgt_sh': 'target_share', 'tier': 'center_tier', 'utr': 'snap_change', 'vol': 'dk_points_volatility', 'p_plays': 'probability_plays', 'p_plays_a': 'probability_plays_availability', 'p_plays_t1': 'probability_plays_transition', 'p_plays_t1_walkforward': 'probability_plays_transition_walkforward', 'p_absent_base': 'probability_absent_tier', 'p_absent_calibrated': 'probability_absent_calibrated', 'p_absent_logistic': 'probability_absent_logistic', 'p_near_zero': 'probability_near_zero', 'p_near_zero_calibrated': 'probability_near_zero_calibrated', 'p_near_zero_raw': 'probability_near_zero_raw', 'p_per_trial': 'probability_per_trial', 'p_nonzero': 'probability_nonzero', 'p_event': 'probability_nonzero', 'pit': 'rank', 'pit_of': 'rank_of', 'outcome_pit': 'outcome_rank', 'outcome_pit_pct': 'outcome_percent', 'outcome_pit_scored': 'outcome_rank_scored', 'pit_comp': 'composed_rank', 'near_zero_pit': 'near_zero_rank', 'ordinary_pit': 'ordinary_rank', 'ordinary_pit_window': 'ordinary_rank_window', 'games_through_game': 'games_season_postgame', 'own_median_dk': 'dk_points_median_season_pregame', 'own_dk_sd': 'dk_points_standard_deviation_season_pregame', 'dk_points_prev': 'dk_points_mean_previous_season', 'prev_played_team': 'team_previous_1', 'last_played_team': 'team_previous_1', 'last_played_team_game': 'game_number_previous_1', 'last_played_week': 'week_previous_1', 'played_last_or_missed': 'played_team_recent1', 'missed_last_team_game': 'missed_team_recent1', 'last_result': 'team_result_recent1', 'last_margin': 'team_margin_recent1', 'game_no': 'game_number', 'std_err': 'standard_error', 'redzone_opps': 'redzone_opportunities', 'steady_per_opp': 'steady_points_per_opportunity', 'td_share_of_dk': 'td_points_share_of_dk_points', 'dk_expected': 'dk_points_expected', 'dk_minus_expected': 'dk_points_minus_expected', 'dk_volatility': 'dk_points_volatility', 'neutral_secs_per_play': 'neutral_seconds_per_play', 'elasticity_x_size_change': 'elasticity_times_size_change', 'proportional_x_size_change': 'proportional_times_size_change', 'has_slot': 'has_depth_slot', 'snap_state': 'snap_tier_season_pregame', 'season_role_state': 'role_tier_team_season_pregame', 'st1': 'role_tier_team_recent1', 'st2': 'role_tier_team_recent2', 'st3': 'role_tier_team_recent3', 'snap_trend': 'snap_change', 'AVAIL_INPUTS': 'AVAILABILITY_INPUTS', 'WINDOW_FRAC': 'WINDOW_FRACTION', 'SHRINK_GRID': 'SHRINKAGE_STRENGTH_GRID', 'KGRID': 'SHRINKAGE_STRENGTH_GRID', 'KB': 'TD_RATE_STRENGTH_GRID', 'WGRID': 'DECAY_WEIGHT_GRID', 'shrink_k': 'shrinkage_strength', 'shrunk_avg': 'shrunk_mean', 'snap_ws': 'snap_share_mean_season_pregame', 'snap_share_season_mean_out_zero': 'snap_share_mean_team_season_pregame'}
PLAIN_SUF = [['_ws', '_mean_season_pregame'], ['_w3', '_mean_recent3'], ['_w1', '_recent1'], ['_l1', '_previous_1'], ['_l2', '_previous_2'], ['_l3', '_previous_3'], ['_std', '_mean_season_pregame'], ['_thru', '_mean_season_postgame'], ['_hat', '_pred'], ['_m', '_to_date'], ['_dk', '_dk'], ['_ours', '_ours'], ['_at', '_at'], ['_st', '_st'], ['_prev', '_prev'], ['_season_avg', '_mean_season_pregame'], ['_season_mean', '_mean_season_pregame'], ['_last3_avg', '_mean_recent3'], ['_last_game', '_recent1'], ['_lag1', '_previous_1'], ['_lag2', '_previous_2'], ['_lag3', '_previous_3'], ['_through_game', '_mean_season_postgame']]
PLAIN_PRE = [['oppo_', 'opponent_offense_'], ['dal_', 'defense_allowed_'], ['oppd_', 'position_defense_'], ['tm_', 'teammate_'], ['abs_', 'vacated_'], ['rz_', 'redzone_'], ['gl_', 'goal_line_'], ['opp_offense_', 'opponent_offense_'], ['opp_def_allowed_', 'defense_allowed_'], ['opp_def_vs_pos_', 'position_defense_']]
PLAIN_KNOWN = set(['AVAILABILITY_INPUTS', 'DECAY_WEIGHT_GRID', 'SHRINKAGE_STRENGTH_GRID', 'TD_RATE_STRENGTH_GRID', 'WINDOW_FRACTION', 'absent', 'air_sh', 'air_yards_share', 'attempts', 'away_rest', 'away_score', 'away_team', 'beat', 'beat_own_median', 'blow', 'blowout', 'car_sh', 'carries', 'carry_share', 'center_fifth', 'center_tenth', 'center_tier', 'link_chain_class', 'collapse', 'completions', 'composed_rank', 'depth_slot', 'did_not_play', 'div_game', 'dk', 'dk_points', 'dk_points_expected', 'dk_points_mean_previous_season', 'dk_points_median_season_pregame', 'dk_points_minus_expected', 'dk_points_standard_deviation_season_pregame', 'dk_points_volatility', 'dmed', 'drives', 'dropbacks', 'dsd', 'dst_points', 'dst_pts', 'dst_salary', 'eff', 'elas', 'elas_x', 'elasticity_times_size_change', 'epa_play', 'exp', 'fav_by', 'fifth', 'game_id', 'game_number', 'game_number_previous_1', 'game_plays_actual', 'gameday', 'games_before', 'games_missed', 'games_missed_band', 'games_season_postgame', 'gametime', 'gap', 'gapb', 'gapg', 'giveaways', 'gl_carries', 'gl_targets', 'gp', 'gsis', 'has_depth_slot', 'home', 'home_rest', 'home_score', 'home_team', 'implied', 'in_slot', 'is_home', 'l0', 'last_wk', 'lead_pass_rate', 'lead_plays', 'lead_spp', 'log_likelihood_independent', 'long', 'long_rest', 'margin_last', 'missed_team_recent1', 'n_prior', 'n_thru', 'name', 'near_zero_p', 'near_zero_rank', 'neutral_pass_rate', 'neutral_seconds_per_play', 'neutral_spp', 'offense_snaps', 'opp', 'opponent', 'opportunities', 'opps', 'ordinary_rank', 'ordinary_rank_window', 'outcome_percent', 'outcome_rank', 'outcome_rank_scored', 'p_T1', 'p_a', 'p_play', 'p_t1', 'pass_rate', 'passing_interceptions', 'passing_tds', 'passing_yards', 'penalties', 'penalty_yards', 'pi', 'pi_cal', 'played', 'played_team_recent1', 'player_id', 'plays', 'plays_elasticity', 'pos', 'position', 'practice_status', 'prev_team', 'probability_absent_calibrated', 'probability_absent_logistic', 'probability_absent_tier', 'probability_near_zero', 'probability_near_zero_calibrated', 'probability_near_zero_raw', 'probability_nonzero', 'probability_per_trial', 'probability_plays', 'probability_plays_availability', 'probability_plays_transition', 'probability_plays_transition_walkforward', 'prop_x', 'proportional_times_size_change', 'pts_against', 'pts_for', 'pw', 'q_B', 'q_M', 'q_R', 'qgap', 'quality_gap', 'rank', 'rank_of', 'receiving_air_yards', 'receiving_tds', 'receiving_yards', 'receptions', 'recorded', 'redzone_opportunities', 'report_status', 'res_last', 'resid', 'rest', 'result', 'result_pct', 'result_u', 'role', 'role_collapse', 'role_tier_team_recent1', 'role_tier_team_recent2', 'role_tier_team_recent3', 'role_tier_team_season_pregame', 'roof', 'roster_status', 'rs', 'rsb', 'rushing_tds', 'rushing_yards', 'rz_attempts', 'rz_car_sh', 'rz_carries', 'rz_plays', 'rz_targets', 'rz_tgt_sh', 'rzo', 'sacks_suffered', 'sacks_taken', 'sal_k', 'salary', 'salary_thousands', 'season', 'self_missed', 'short', 'short_rest', 'shrinkage_strength', 'shrunk_mean', 'slot', 'snap', 'snap_change', 'snap_share', 'snap_share_mean_season_pregame', 'snap_share_mean_team_season_pregame', 'snap_share_to_date', 'snap_state_label', 'snap_tier_season_pregame', 'spread_line', 'sstd', 'standard_error', 'steady', 'steady_change', 'steady_points', 'steady_points_per_opportunity', 'stratum', 'surface', 't_steady', 't_td', 'target_share', 'targets', 'td', 'td_change', 'td_count', 'td_points', 'td_points_share_of_dk_points', 'tde', 'tdpts', 'tdshare', 'team', 'team_game_no', 'team_last', 'team_margin_recent1', 'team_prev_week', 'team_previous_1', 'team_result_recent1', 'temp', 'tenth', 'tgi', 'tgi_last', 'tgt_sh', 'tier', 'total_line', 'trail_pass_rate', 'trail_plays', 'trail_spp', 'utr', 'vol', 'week', 'week_previous_1', 'wind'])
def plain_name(t):
    """old kit name -> plain name, or None (same rules as the rename: exact map, then suffix, then prefix)."""
    if t in PLAIN_COL: return PLAIN_COL[t]
    for a, b in PLAIN_SUF:
        if t.endswith(a) and len(t) > len(a):
            c = t[:-len(a)]; n = plain_name(c)
            if n or c in PLAIN_KNOWN: return (n or c) + b
    for a, b in PLAIN_PRE:
        if t.startswith(a) and len(t) > len(a):
            c = t[len(a):]; n = plain_name(c)
            if n or c in PLAIN_KNOWN: return b + (n or c)
    return None
def plain(o):
    """A record (DataFrame / dict / list / str) with retired names mapped to canonical ones; canonical names pass through unchanged."""
    if isinstance(o, pd.DataFrame): return o.rename(columns=lambda c: (plain_name(c) or c) if isinstance(c, str) else c)
    if isinstance(o, dict): return {((plain_name(k) or k) if isinstance(k, str) else k): plain(v) for k, v in o.items()}
    if isinstance(o, list): return [plain(x) for x in o]
    if isinstance(o, str): return plain_name(o) or o
    return o
# ---------------- DraftKings scoring of a box score (the reconstruction checked against DraftKings' recorded points) ----------------
def dkpts(weekly_stats):                                   # DraftKings classic scoring; return TDs, return fumbles lost, offensive fumble-recovery TDs identified Oct 2 2026
    filled_column = lambda column_name: weekly_stats[column_name].fillna(0) if column_name in weekly_stats else 0
    return (0.04 * filled_column("passing_yards") + 4 * filled_column("passing_tds") - filled_column("passing_interceptions") + 0.1 * filled_column("rushing_yards") + 6 * filled_column("rushing_tds") + filled_column("receptions")
            + 0.1 * filled_column("receiving_yards") + 6 * filled_column("receiving_tds") - filled_column("rushing_fumbles_lost") - filled_column("receiving_fumbles_lost") - filled_column("sack_fumbles_lost")
            + 2 * (filled_column("passing_2pt_conversions") + filled_column("rushing_2pt_conversions") + filled_column("receiving_2pt_conversions"))
            + 3 * (filled_column("passing_yards") >= 300) + 3 * (filled_column("rushing_yards") >= 100) + 3 * (filled_column("receiving_yards") >= 100)
            + 6 * filled_column("special_teams_tds") + 6 * filled_column("off_fr_td") - filled_column("st_fumbles_lost"))
SCRIM = ("pass", "run", "qb_kneel", "qb_spike")
def dst_lines(game_plays, team_name):
    """Each DraftKings DST line for one team-game (batch 70: the lines, not only their total - dst_points_of sums them; one producer).  DraftKings DST scoring, identified Oct 2 2026 against DraftKings' recorded points 2016-21 (97.8% of 3090 games exact):
    sack 1, interception 2, fumble recovery 2 (any recovered opponent fumble, kicks included), safety 2, D/ST touchdown 6, blocked kick 2
    (punt, field goal, extra point), defensive 2pt/XP return 2, points-allowed tier on (final score - 6 per opponent DEFENSIVE touchdown -
    2 per safety); return touchdowns allowed and every try stay in."""
    fix_team = lambda line_text: team_fixes.get(line_text, line_text)
    get_column = lambda column_name: game_plays[column_name] if column_name in game_plays else pd.Series(np.nan, index=game_plays.index)
    team_column = lambda column_name: get_column(column_name).map(fix_team)
    zero_filled = lambda column_name: get_column(column_name).fillna(0)
    offense_team, defense_team, td_team, home_team = team_column("posteam"), team_column("defteam"), team_column("td_team"), fix_team(game_plays.home_team.iloc[0])
    opponent = fix_team(game_plays.away_team.iloc[0]) if home_team == team_name else home_team; on_defense = defense_team == team_name
    fumble_recoveries = (((team_column("fumble_recovery_1_team") == team_name) & (team_column("fumbled_1_team") != team_name)).sum() + ((team_column("fumble_recovery_2_team") == team_name) & (team_column("fumbled_2_team") != team_name)).sum())
    td_count = game_plays.loc[(td_team == team_name) & ((offense_team != team_name) | (zero_filled("return_touchdown") == 1)), "play_id"].nunique()
    blocked_kicks = zero_filled("punt_blocked")[on_defense].sum() + ((get_column("field_goal_result") == "blocked") & on_defense).sum() + ((get_column("extra_point_result") == "blocked") & on_defense).sum()
    defensive_conversions = ((get_column("defensive_two_point_conv") == 1) & on_defense).sum() + ((get_column("defensive_extra_point_conv") == 1) & on_defense).sum()
    last = game_plays.iloc[-1]; points_allowed = last.away_score if home_team == team_name else last.home_score
    points_allowed = max(points_allowed - 6 * game_plays.loc[(td_team == opponent) & (offense_team == team_name) & get_column("play_type").isin(SCRIM), "play_id"].nunique() - 2 * game_plays.loc[(zero_filled("safety") == 1) & (offense_team == team_name), "play_id"].nunique(), 0)
    tier = 10 if points_allowed == 0 else 7 if points_allowed <= 6 else 4 if points_allowed <= 13 else 1 if points_allowed <= 20 else 0 if points_allowed <= 27 else -1 if points_allowed <= 34 else -4
    return dict(dst_sacks=float(zero_filled("sack")[on_defense].sum()), dst_interceptions=float(zero_filled("interception")[on_defense].sum()), dst_fumble_recoveries=float(fumble_recoveries),
                dst_safeties=float(zero_filled("safety")[on_defense].sum()), dst_tds=float(td_count), dst_blocked_kicks=float(blocked_kicks), dst_defensive_conversions=float(defensive_conversions),
                dst_points_allowed=float(points_allowed), dst_points_allowed_tier=float(tier))
DST_SCORING = {"dst_sacks": 1, "dst_interceptions": 2, "dst_fumble_recoveries": 2, "dst_safeties": 2, "dst_tds": 6, "dst_blocked_kicks": 2, "dst_defensive_conversions": 2, "dst_points_allowed_tier": 1}   # DraftKings Classic DST (dst_lines' docstring)
def dst_points_of(lines):
    """DST points = the sum of the DraftKings DST lines (DST_SCORING) - the one producer of facts' DST total."""
    return sum(weight * lines[name] for name, weight in DST_SCORING.items())
def read_data(name, **read_options):
    path = os.path.join(DATA_DIR, name); return read_table(path, low_memory=False, **read_options) if os.path.exists(path) else None
def complete(season_year):   # a season counts only if every raw kind exists for it, game-day roster status included (like for like)
    if not all(os.path.exists(os.path.join(DATA_DIR, file_name)) for file_name in (f"stats_{season_year}.csv.gz", f"pbp_{season_year}.csv.gz", f"injuries_{season_year}.csv", f"rosters_{season_year}.csv.gz")): return False
    if not any(os.path.exists(os.path.join(DATA_DIR, file_name)) for file_name in (f"snaps_{season_year}.csv.gz", f"snap_counts_{season_year}.csv.gz")): return False
    return {"week", "status", "gsis_id"} <= set(read_table(os.path.join(DATA_DIR, f"rosters_{season_year}.csv.gz"), nrows=0).columns)
def build():
    """Raw verified files -> facts/player_game.csv.gz, facts/team_game.csv.gz, facts/game.csv.gz, facts/facts_report.txt."""
    os.makedirs(FACTS_DIR, exist_ok=True); report = Report()
    ALLS = sorted(int(re.search(r"stats_(\d{4})", p)[1]) for p in glob.glob(os.path.join(DATA_DIR, "stats_*.csv.gz"))); SEASONS = [season_year for season_year in ALLS if complete(season_year)]
    report.say(f"facts.py  seasons with weekly stats on disk: {ALLS};  complete (stats, play-by-play, snaps, injuries, game-day roster status): {SEASONS}")
    # ---------------- game ----------------
    games = pd.concat([read_data("games.csv")] + [read_data(os.path.basename(filled_column)) for filled_column in sorted(glob.glob(os.path.join(DATA_DIR, "games_20*.csv.gz")))]).drop_duplicates("game_id")   # later seasons enter as their own schedule file
    games = games[(games.game_type == "REG") & games.season.isin(SEASONS)].copy()
    for column_name in ("home_team", "away_team"): games[column_name] = fix_names(games[column_name])
    gcols = [column_name for column_name in ["game_id", "season", "week", "gameday", "gametime", "home_team", "away_team", "home_score", "away_score", "spread_line", "total_line",
                         "home_rest", "away_rest", "div_game", "roof", "surface", "temp", "wind"] if column_name in games]
    GAME = games[gcols].copy(); plain(GAME).to_csv(os.path.join(FACTS_DIR, "game.csv.gz"), index=False)
    # ---------------- team_game ----------------
    side = lambda home: pd.DataFrame(dict(game_id=games.game_id, season=games.season, week=games.week, team=games.home_team if home else games.away_team,
                                          opp=games.away_team if home else games.home_team, home=int(home),
                                          implied=(games.total_line + games.spread_line) / 2 if home else (games.total_line - games.spread_line) / 2,
                                          fav_by=games.spread_line if home else -games.spread_line, total_line=games.total_line,
                                          rest=games.get("home_rest" if home else "away_rest"),
                                          pts_for=games.home_score if home else games.away_score, pts_against=games.away_score if home else games.home_score))
    team_games = pd.concat([side(True), side(False)], ignore_index=True)
    pbp_rows, dst_rows, px_rows, rz_rows = [], [], [], []
    for season_year in SEASONS:
        p = os.path.join(DATA_DIR, f"pbp_{season_year}.csv.gz")
        if not os.path.exists(p): report.say(f"  {season_year}: no play-by-play file - team plays and DST points missing"); continue
        header_columns = read_table(p, nrows=0).columns
        want = ["game_id", "week", "season_type", "play_id", "home_team", "away_team", "defteam", "posteam", "td_team", "return_touchdown", "sack", "interception",
                "fumble_lost", "safety", "punt_blocked", "home_score", "away_score", "pass", "rush", "qb_dropback", "play_type", "field_goal_result",
                "extra_point_result", "defensive_two_point_conv", "defensive_extra_point_conv", "fumble_recovery_1_team", "fumbled_1_team",
                "fumble_recovery_2_team", "fumbled_2_team", "fumbled_1_player_id", "fumble_recovery_1_player_id", "td_player_id",
                "epa", "penalty", "penalty_team", "penalty_yards", "score_differential", "qtr", "yardline_100", "drive", "game_seconds_remaining", "passer_player_id", "receiver_player_id", "rusher_player_id", "pass_attempt", "two_point_attempt"]
        pbp_season = read_table(p, usecols=[column_name for column_name in want if column_name in header_columns], low_memory=False); pbp_season = pbp_season[pbp_season.season_type == "REG"]
        pbp_season["posteam"] = pbp_season.posteam.map(lambda team_name: team_fixes.get(team_name, team_name))
        team_totals = pbp_season[pbp_season.posteam.notna()].groupby(["game_id", "posteam"]).agg(plays=("play_id", "size"), dropbacks=("qb_dropback", "sum") if "qb_dropback" in pbp_season else ("play_id", "size")).reset_index()
        scrimmage_plays = pbp_season[pbp_season.posteam.notna() & ((pbp_season["pass"] == 1) | (pbp_season["rush"] == 1))].copy(); scrimmage_plays["give"] = scrimmage_plays.interception.fillna(0) + scrimmage_plays.fumble_lost.fillna(0)
        extra = {"pass_rate": ("pass", "mean"), "sacks_taken": ("sack", "sum"), "giveaways": ("give", "sum")}
        if "epa" in scrimmage_plays: extra["epa_play"] = ("epa", "mean")
        if "yardline_100" in scrimmage_plays: scrimmage_plays["rz"] = (scrimmage_plays.yardline_100 <= 20).astype(int); extra["rz_plays"] = ("rz", "sum")
        team_totals = team_totals.merge(scrimmage_plays.groupby(["game_id", "posteam"]).agg(**extra).reset_index(), on=["game_id", "posteam"], how="left")
        if {"qtr", "score_differential"} <= set(scrimmage_plays.columns):   # neutral situations: quarters 1-3, within a touchdown
            neutral_pass = scrimmage_plays[(scrimmage_plays.qtr <= 3) & (scrimmage_plays.score_differential.abs() <= 7)].groupby(["game_id", "posteam"])["pass"].mean().rename("neutral_pass_rate").reset_index()
            team_totals = team_totals.merge(neutral_pass, on=["game_id", "posteam"], how="left")
        if {"penalty", "penalty_team", "penalty_yards"} <= set(pbp_season.columns):   # penalties committed by the team (either side of the ball)
            penalty_rows = pbp_season[pbp_season.penalty == 1].assign(pt=lambda on_defense: on_defense.penalty_team.map(lambda team_name: team_fixes.get(team_name, team_name))).groupby(["game_id", "pt"]).agg(penalties=("play_id", "size"), penalty_yards=("penalty_yards", "sum")).reset_index()
            team_totals = team_totals.merge(penalty_rows.rename(columns={"pt": "posteam"}), on=["game_id", "posteam"], how="left").fillna({"penalties": 0, "penalty_yards": 0})
        if "drive" in pbp_season: team_totals = team_totals.merge(pbp_season[pbp_season.posteam.notna()].groupby(["game_id", "posteam"]).drive.nunique().rename("drives").reset_index(), on=["game_id", "posteam"], how="left")
        if {"game_seconds_remaining", "qtr", "score_differential", "drive"} <= set(scrimmage_plays.columns):   # pace: seconds to the next snap in the same drive, neutral situations
            zero_filled = scrimmage_plays.sort_values(["game_id", "play_id"]).copy(); zero_filled["dt"] = zero_filled.game_seconds_remaining - zero_filled.groupby(["game_id", "posteam", "drive"]).game_seconds_remaining.shift(-1)
            zero_filled = zero_filled[(zero_filled.qtr <= 3) & (zero_filled.score_differential.abs() <= 7) & zero_filled.dt.between(1, 60)]
            team_totals = team_totals.merge(zero_filled.groupby(["game_id", "posteam"]).dt.median().rename("neutral_spp").reset_index(), on=["game_id", "posteam"], how="left")
        if {"game_seconds_remaining", "score_differential", "drive"} <= set(scrimmage_plays.columns):   # script response: pass rate, pace and plays when trailing / leading by more than one score
            sorted_plays = scrimmage_plays.sort_values(["game_id", "play_id"]).copy(); sorted_plays["dt"] = sorted_plays.game_seconds_remaining - sorted_plays.groupby(["game_id", "posteam", "drive"]).game_seconds_remaining.shift(-1)
            for label, row_mask in (("trail", sorted_plays.score_differential <= -9), ("lead", sorted_plays.score_differential >= 9)):
                state_plays = sorted_plays[row_mask]; state_groups = state_plays.groupby(["game_id", "posteam"])
                state_stats = pd.concat([state_groups["pass"].mean().rename(f"{label}_pass_rate"), state_groups.size().rename(f"{label}_plays"), state_plays[state_plays.dt.between(1, 60)].groupby(["game_id", "posteam"]).dt.median().rename(f"{label}_spp")], axis=1).reset_index()
                team_totals = team_totals.merge(state_stats, on=["game_id", "posteam"], how="left").fillna({f"{label}_plays": 0})   # never trailed / led = 0 such plays; rates and pace stay undefined
        pbp_rows.append(team_totals.rename(columns={"posteam": "team"}))
        safe_column = lambda column_name: pbp_season[column_name] if column_name in pbp_season else pd.Series(np.nan, index=pbp_season.index)
        return_fumbles = pbp_season[safe_column("play_type").isin(["kickoff", "punt"]) & (safe_column("fumble_lost") == 1) & safe_column("fumbled_1_player_id").notna()].groupby(["week", "fumbled_1_player_id"]).size().rename("st_fumbles_lost")
        offense_tds = pbp_season[(safe_column("td_team").map(lambda team_name: team_fixes.get(team_name, team_name)) == pbp_season.posteam) & safe_column("play_type").isin(SCRIM) & safe_column("td_player_id").notna() & (safe_column("fumble_recovery_1_player_id") == safe_column("td_player_id"))]
        recovery_tds = offense_tds.groupby(["week", "td_player_id"]).size().rename("off_fr_td")
        return_rows = pd.concat([return_fumbles.rename_axis(["week", "player_id"]), recovery_tds.rename_axis(["week", "player_id"])], axis=1).reset_index(); return_rows["season"] = season_year; px_rows.append(return_rows)
        if {"yardline_100", "receiver_player_id", "rusher_player_id", "passer_player_id", "pass_attempt"} <= set(pbp_season.columns):   # red-zone (<= 20) / goal-line (<= 5) opportunities
            scrimmage_rows = pbp_season[(safe_column("two_point_attempt").fillna(0) == 0) & pbp_season.yardline_100.notna()]
            target_plays = scrimmage_rows[(scrimmage_rows.play_type == "pass") & scrimmage_rows.receiver_player_id.notna()]; carry_plays = scrimmage_rows[(scrimmage_rows.play_type == "run") & scrimmage_rows.rusher_player_id.notna()]
            attempt_plays = scrimmage_rows[(scrimmage_rows.play_type == "pass") & (scrimmage_rows.pass_attempt.fillna(0) == 1) & (scrimmage_rows.sack.fillna(0) == 0) & scrimmage_rows.passer_player_id.notna()]
            redzone_parts = [play_subset[play_subset.yardline_100 <= yard_limit].groupby(["week", player_column]).size().rename(label).rename_axis(["week", "player_id"]) for label, play_subset, player_column, yard_limit in
                  (("rz_targets", target_plays, "receiver_player_id", 20), ("gl_targets", target_plays, "receiver_player_id", 5), ("rz_carries", carry_plays, "rusher_player_id", 20),
                   ("gl_carries", carry_plays, "rusher_player_id", 5), ("rz_attempts", attempt_plays, "passer_player_id", 20))]
            redzone_rows = pd.concat(redzone_parts, axis=1).reset_index(); redzone_rows["season"] = season_year; rz_rows.append(redzone_rows)
        for game_id, game_plays in pbp_season.groupby("game_id", sort=False):
            for team_name in {team_fixes.get(game_plays.home_team.iloc[0], game_plays.home_team.iloc[0]), team_fixes.get(game_plays.away_team.iloc[0], game_plays.away_team.iloc[0])}: dst_rows.append(dict(game_id=game_id, team=team_name, **dst_lines(game_plays, team_name)))
    if pbp_rows: team_games = team_games.merge(pd.concat(pbp_rows), on=["game_id", "team"], how="left")
    if dst_rows: team_games = team_games.merge(pd.DataFrame(dst_rows).assign(dst_pts=lambda lines: dst_points_of(lines)), on=["game_id", "team"], how="left")   # batch 70: the DST lines and their sum
    salary_rows = read_table(os.path.join(ROOT, "sources/tidy/salaries.csv.gz"), low_memory=False); salary_rows["team"] = fix_names(salary_rows.team); salary_rows = salary_rows[salary_rows.season.isin(SEASONS)]
    dsal = salary_rows[salary_rows.pos == "DST"].groupby(["season", "week", "team"]).salary.max().rename("dst_salary").reset_index()
    team_games = team_games.merge(dsal, on=["season", "week", "team"], how="left")
    # ---------------- player_game ----------------
    stat_rows = pd.concat([read_data(f"stats_{season_year}.csv.gz") for season_year in SEASONS]); stat_rows = stat_rows[stat_rows.season_type == "REG"].copy(); stat_rows["team"] = fix_names(stat_rows.team)
    if px_rows:                                     # play-by-play events the weekly stats do not carry (return fumbles lost, offensive fumble-recovery TDs)
        play_extras = pd.concat(px_rows).groupby(["season", "week", "player_id"]).sum().reset_index(); stat_rows = stat_rows.merge(play_extras, on=["season", "week", "player_id"], how="left")
    redzone_columns = ["rz_targets", "gl_targets", "rz_carries", "gl_carries", "rz_attempts"]
    if rz_rows:                                     # red-zone / goal-line opportunities from play-by-play (outcomes: history only for later weeks)
        redzone_totals = pd.concat(rz_rows).groupby(["season", "week", "player_id"]).sum().reset_index(); stat_rows = stat_rows.merge(redzone_totals, on=["season", "week", "player_id"], how="left")
        stat_rows[redzone_columns] = stat_rows[redzone_columns].fillna(0)                 # a recorded player with no red-zone play had none
    stat_rows["dk"] = dkpts(stat_rows)
    team_volume = stat_rows.groupby(["season", "week", "team"])[[column_name for column_name in ["carries", "targets", "receiving_air_yards", "rz_targets", "rz_carries"] if column_name in stat_rows]].sum().rename(columns=lambda column_name: "team_" + column_name).reset_index()
    stat_rows = stat_rows.merge(team_volume, on=["season", "week", "team"], how="left")
    stat_rows["car_sh"] = stat_rows.carries / stat_rows.team_carries.replace(0, np.nan); stat_rows["tgt_sh"] = stat_rows.targets / stat_rows.team_targets.replace(0, np.nan)
    stat_rows["air_sh"] = stat_rows.receiving_air_yards / stat_rows.team_receiving_air_yards.replace(0, np.nan)
    if "rz_targets" in stat_rows: stat_rows["rz_tgt_sh"] = stat_rows.rz_targets / stat_rows.team_rz_targets.replace(0, np.nan); stat_rows["rz_car_sh"] = stat_rows.rz_carries / stat_rows.team_rz_carries.replace(0, np.nan)   # no team red-zone play = undefined, not 0
    keep = ["player_id", "player_display_name", "position", "season", "week", "game_id", "team", "opponent_team", "dk", "attempts", "completions", "passing_yards",
            "passing_tds", "passing_interceptions", "sacks_suffered", "carries", "rushing_yards", "rushing_tds", "targets", "receptions", "receiving_yards", "receiving_tds",
            "rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost", "passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions",
            "special_teams_tds", "off_fr_td", "st_fumbles_lost",   # batch 70: the rare DraftKings lines dkpts already scores
            "receiving_air_yards", "car_sh", "tgt_sh", "air_sh", "rz_targets", "gl_targets", "rz_carries", "gl_carries", "rz_attempts", "rz_tgt_sh", "rz_car_sh"]
    player_games = stat_rows[[column_name for column_name in keep if column_name in stat_rows]].rename(columns={"player_id": "player_id", "player_display_name": "name", "position": "pos", "opponent_team": "opp"})
    player_games["opp"] = fix_names(player_games.opp); player_games["recorded"] = 1
    # id maps: pfr -> gsis from every roster season on disk (ids are stable across seasons); names from stats and rosters
    roster_frames = [roster_frame for roster_frame in (read_data(f"rosters_{season_year}.csv.gz") for season_year in range(2010, 2030)) if roster_frame is not None]
    rosters = pd.concat(roster_frames) if roster_frames else pd.DataFrame(columns=["pfr_id", "gsis_id", "full_name", "team", "season"])
    roster_weeks = rosters[rosters.season.isin(SEASONS) & rosters.position.isin(["QB", "RB", "WR", "TE"])].dropna(subset=["gsis_id", "week"])   # game-day roster status, weekly
    roster_weeks = roster_weeks.rename(columns={"gsis_id": "player_id", "status": "roster_status"}).assign(team=lambda on_defense: fix_names(on_defense.team), week=lambda on_defense: on_defense.week.astype(int)).drop_duplicates(["player_id", "season", "week"], keep="last")[["player_id", "season", "week", "team", "roster_status"]]
    gsis_lookup = rosters[["pfr_id", "gsis_id"]].dropna().drop_duplicates("pfr_id").set_index("pfr_id").gsis_id
    name_rows = pd.concat([player_games[["player_id", "name", "team", "season"]].rename(columns={"name": "nm"}),
                    rosters[["gsis_id", "full_name", "team", "season"]].rename(columns={"gsis_id": "player_id", "full_name": "nm"})]).dropna()
    name_rows["team"] = fix_names(name_rows.team); name_rows["k"] = norm(name_rows.nm); name_rows = name_rows.drop_duplicates(["k", "team", "season", "player_id"])
    name_rows = name_rows[~name_rows.duplicated(["k", "team", "season"], keep=False)][["k", "team", "season", "player_id"]]
    # snaps
    snap_frames = []
    for season_year in SEASONS:
        filled_column = next((line_text for line_text in (f"snaps_{season_year}.csv.gz", f"snap_counts_{season_year}.csv.gz") if os.path.exists(os.path.join(DATA_DIR, line_text))), None)
        if filled_column: s = read_data(filled_column); snap_frames.append(s[s.game_type == "REG"])
    snap_rows = pd.concat(snap_frames) if snap_frames else pd.DataFrame()
    if len(snap_rows):
        snap_rows["team"] = fix_names(snap_rows.team); snap_rows["player_id"] = snap_rows.pfr_player_id.map(gsis_lookup); snap_rows["k"] = norm(snap_rows.player)
        miss = snap_rows.player_id.isna(); snap_rows.loc[miss, "player_id"] = snap_rows[miss].drop(columns="player_id").merge(name_rows, on=["k", "team", "season"], how="left").player_id.values
        snap_rows["snap"] = snap_rows.offense_pct.where(snap_rows.offense_pct <= 1, snap_rows.offense_pct / 100)
        snap_rows = snap_rows.dropna(subset=["player_id"]).drop_duplicates(["player_id", "season", "week"])[["player_id", "season", "week", "team", "snap", "offense_snaps"]]
    # salary rows (2016-21) and injury rows join the universe: a priced or listed player who recorded nothing still has a row
    SALp = salary_rows[salary_rows.pos.isin(["QB", "RB", "WR", "TE"])].copy(); SALp["k"] = norm(SALp.name)
    SALp = SALp.merge(name_rows, on=["k", "team", "season"], how="left")
    injury_frames = []
    for season_year in SEASONS:
        j = read_data(f"injuries_{season_year}.csv")
        if j is not None:
            j = j[(j.game_type == "REG") if "game_type" in j else slice(None)]; j["team"] = fix_names(j.team); injury_frames.append(j)
    injury_rows = pd.concat(injury_frames).dropna(subset=["gsis_id"]) if injury_frames else pd.DataFrame(columns=["season", "week", "gsis_id"])
    if len(injury_rows): injury_rows = (injury_rows.assign(_t=pd.to_datetime(injury_rows.date_modified, errors="coerce", utc=True)).sort_values("_t", kind="stable", na_position="first")
                      .drop_duplicates(["season", "week", "gsis_id"], keep="last").drop(columns="_t"))   # the newest report by its own timestamp, not file order
    union_rows = pd.concat([player_games[["player_id", "season", "week", "team"]], SALp.dropna(subset=["player_id"])[["player_id", "season", "week", "team"]],
                   injury_rows.rename(columns={"gsis_id": "player_id"})[["player_id", "season", "week", "team"]], roster_weeks[roster_weeks.roster_status.isin(["ACT", "INA"])][["player_id", "season", "week", "team"]]]).drop_duplicates(["player_id", "season", "week"])
    player_games = union_rows.merge(player_games.drop(columns=["team"]), on=["player_id", "season", "week"], how="left")
    player_games["recorded"] = player_games.recorded.fillna(0).astype(int)
    if len(snap_rows): player_games = player_games.merge(snap_rows.drop(columns=["team"]), on=["player_id", "season", "week"], how="left")
    player_games["played"] = ((player_games.recorded == 1) | (player_games.get("offense_snaps", pd.Series(0, index=player_games.index)).fillna(0) > 0)).astype(float)
    player_games = player_games.merge(team_games.loc[team_games.plays.isna(), ["season", "week", "team"]].assign(_unplayed=1), on=["season", "week", "team"], how="left")
    player_games.loc[player_games._unplayed == 1, "played"] = np.nan; player_games = player_games.drop(columns="_unplayed")
    for column_name in ("car_sh", "tgt_sh", "air_sh"): player_games.loc[(player_games.played == 1) & player_games[column_name].isna(), column_name] = 0.0   # played with no stat line = no carries, targets or air yards   # a game not yet played has no outcome, not a "did not play"
    box_columns = [column_name for column_name in ("attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions", "sacks_suffered", "carries", "rushing_yards", "rushing_tds", "targets", "receptions", "receiving_yards", "receiving_tds",
                   "receiving_air_yards", "rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost", "passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions", "special_teams_tds", "off_fr_td", "st_fumbles_lost") if column_name in player_games]
    no_line = (player_games.played == 1) & (player_games.recorded == 0); player_games.loc[no_line, box_columns] = player_games.loc[no_line, box_columns].fillna(0.0)   # V16 (batch 70): played with no stat line = no plays - measured: door_identity_read_v1 found no play-by-play play behind any such blank
    if "rz_targets" in player_games:                          # played with no stat line = no red-zone plays; share 0 only where the team had red-zone plays
        for column_name in redzone_columns: player_games.loc[(player_games.played == 1) & player_games[column_name].isna(), column_name] = 0.0
        for column_name, team_name in (("rz_tgt_sh", "rz_targets"), ("rz_car_sh", "rz_carries")): player_games.loc[(player_games.played == 1) & player_games[column_name].isna() & (player_games.groupby(["season", "week", "team"])[team_name].transform("sum") > 0), column_name] = 0.0
    player_games = player_games.merge(SALp.dropna(subset=["player_id"]).drop_duplicates(["player_id", "season", "week"])[["player_id", "season", "week", "salary"]], on=["player_id", "season", "week"], how="left")
    if len(injury_rows): player_games = player_games.merge(injury_rows.rename(columns={"gsis_id": "player_id"})[["player_id", "season", "week", "report_status", "practice_status"]], on=["player_id", "season", "week"], how="left")
    player_games = player_games.merge(roster_weeks[["player_id", "season", "week", "roster_status"]], on=["player_id", "season", "week"], how="left")
    # batch 75: a missing position / name comes from the player's own roster row that week, else from his roster rows that season when they agree on one value,
    # else it stays undefined - never from another season (facts_shift_read_v1: the first-row fill let an added season rewrite old rows)
    roster_fill = rosters.dropna(subset=["gsis_id"]).assign(week=lambda frame: pd.to_numeric(frame.week, errors="coerce")).rename(columns={"gsis_id": "player_id"})
    weekly_fill = roster_fill.dropna(subset=["week"]).assign(week=lambda frame: frame.week.astype(int)).drop_duplicates(["player_id", "season", "week"], keep="last")
    for column_name, source_name in (("pos", "position"), ("name", "full_name")):
        if source_name not in roster_fill: continue
        player_games[column_name] = player_games[column_name].fillna(pd.Series(player_games[["player_id", "season", "week"]].merge(weekly_fill[["player_id", "season", "week", source_name]], on=["player_id", "season", "week"], how="left")[source_name].values, index=player_games.index))
        season_values = roster_fill.dropna(subset=[source_name]).groupby(["player_id", "season"])[source_name].agg(lambda values: values.iloc[0] if values.nunique() == 1 else np.nan).reset_index()
        player_games[column_name] = player_games[column_name].fillna(pd.Series(player_games[["player_id", "season"]].merge(season_values, on=["player_id", "season"], how="left")[source_name].values, index=player_games.index))
    player_games["dk"] = np.where(player_games.played == 1, player_games.dk.fillna(0), np.nan)            # a player who did not play has no DK score, not a zero
    game_id = team_games[["season", "week", "team", "game_id", "opp"]]
    player_games = player_games.drop(columns=[column_name for column_name in ("game_id", "opp") if column_name in player_games]).merge(game_id, on=["season", "week", "team"], how="left")
    player_games = player_games.sort_values(["season", "week", "team", "pos", "player_id"]).reset_index(drop=True)
    plain(player_games).to_csv(os.path.join(FACTS_DIR, "player_game.csv.gz"), index=False); plain(team_games).to_csv(os.path.join(FACTS_DIR, "team_game.csv.gz"), index=False)
    # ---------------- report + self-check ----------------
    report.say(f"\n{'season':<7}{'player rows':>12}{'played':>8}{'snap matched':>14}{'priced':>8}{'salary matched':>16}{'listed':>8}{'team-games':>11}{'with plays':>11}{'dst pts':>8}")
    for season_year in SEASONS:
        p = player_games[player_games.season == season_year]; team_name = team_games[team_games.season == season_year]; played_rows = p[p.played == 1]
        sal_rows = SALp[SALp.season == season_year]; match_rate = sal_rows.player_id.notna().mean() if len(sal_rows) else np.nan
        report.say(f"{season_year:<7}{len(p):>12}{int(played_rows.shape[0]):>8}{played_rows.snap.notna().mean() if 'snap' in played_rows and len(played_rows) else np.nan:>14.1%}{int(p.salary.notna().sum()):>8}{match_rate:>16.1%}"
            f"{int(p.report_status.notna().sum()) if 'report_status' in p else 0:>8}{len(team_name):>11}{team_name.plays.notna().mean() if 'plays' in team_name and len(team_name) else 0:>11.0%}{team_name.dst_pts.notna().mean() if 'dst_pts' in team_name and len(team_name) else 0:>8.0%}")
    played_skill = player_games[(player_games.played == 1) & player_games.pos.isin(["QB", "RB", "WR", "TE"])]; report.say("\ngame-day roster status among skill players who played: " + "  ".join(f"{season_year} {(home_team.roster_status == 'ACT').mean():.1%} ACT" for season_year, home_team in played_skill.groupby("season")))
    scored_files = sorted(glob.glob(os.path.join(ROOT, "research", "slate_20*_w*_scored.csv")))
    if scored_files:
        mismatch_count = file_name = 0; dbad = dst_count = 0
        for filled_column in scored_files:
            row_mask = re.search(r"slate_(\d{4})_w(\d+)_scored\.csv$", filled_column)
            if not row_mask: continue
            season_year, weekly_stats = int(row_mask[1]), int(row_mask[2]); s = read_table(filled_column, usecols=lambda column_name: column_name in ("player_id", "pos", "team", "actual"), low_memory=False)
            a = s[s.player_id.notna() & s.pos.isin(["QB", "RB", "WR", "TE"])].merge(player_games[(player_games.season == season_year) & (player_games.week == weekly_stats)][["player_id", "dk", "played"]], on="player_id", how="left")
            a = a[a.actual.fillna(0) != 0]; file_name += len(a); mismatch_count += int((~np.isclose(a.actual, a.dk, atol=1e-6)).sum())
            play_subset = s[s.pos == "DST"].merge(team_games[(team_games.season == season_year) & (team_games.week == weekly_stats)][["team", "dst_pts"]], on="team", how="left"); dst_count += len(play_subset)
            dbad += int((~np.isclose(play_subset.actual, play_subset.dst_pts, atol=1e-6, equal_nan=True)).sum())
        report.say(f"\nSELF-CHECK vs canonical pools ({len(scored_files)} slates): skill players who scored {file_name}, DK points differing {mismatch_count};  DSTs {dst_count}, differing {dbad}")
        report.say(f"  skill: {mismatch_count} differ - the pools carry the pre-Oct-2 scoring (no return TDs, return fumbles lost or offensive fumble-recovery TDs); differences there are expected")
        report.say("  DST: the pools carry the pre-Oct-2 DST formula; differences there are expected and mark those pools stale for DST")
    if "dk_points" in salary_rows:                                   # independent: DraftKings' own recorded points (2016-21)
        dst_salary = salary_rows[(salary_rows.pos == "DST") & salary_rows.dk_points.notna()].merge(team_games[["season", "week", "team", "dst_pts"]], on=["season", "week", "team"])
        salary_matches = SALp.dropna(subset=["player_id"]).merge(player_games[player_games.played == 1][["player_id", "season", "week", "dk"]], on=["player_id", "season", "week"]).dropna(subset=["dk_points"])
        report.say(f"\nINDEPENDENT CHECK vs DraftKings' recorded points: DST {len(dst_salary)} games, exact {np.isclose(dst_salary.dk_points, dst_salary.dst_pts, atol=0.05).mean():.1%};  "
            f"skill {len(salary_matches)} player-games, exact {np.isclose(salary_matches.dk_points, salary_matches.dk, atol=0.05).mean():.1%}")
    pbp_box_crosscheck(SEASONS, report)
    report.write(os.path.join(FACTS_DIR, "facts_report.txt"))
    report.say(f"\nwrote facts/player_game.csv.gz ({len(player_games)} rows), facts/team_game.csv.gz ({len(team_games)}), facts/game.csv.gz ({len(GAME)}), facts/facts_report.txt")
    return 0
PBP_BOX_COLUMNS = {"carries": "carries", "rushing_yards": "rushing_yards", "rushing_tds": "rushing_tds", "targets": "targets", "receptions": "receptions", "receiving_yards": "receiving_yards",
                   "receiving_tds": "receiving_tds", "attempts": "attempts", "completions": "completions", "passing_yards": "passing_yards", "passing_tds": "passing_tds", "interceptions": "passing_interceptions"}   # play-by-play aggregate -> stats file column
def pbp_box_crosscheck(seasons, report):
    """The box scores' independent check (project owner's ruling, Oct 6 2026: the stats file is the source of record; play-by-play reconciliations).  Each season's player-games
    rebuilt from its plays - rushes; targets as pass attempts with a receiver, sacks excluded; passes, sacks excluded; two-point tries excluded; lateral yards credited
    to the player who gained them - against the stats file, column by column.  Every disagreeing value is written to facts/pbp_crosscheck.csv and counted here.  A
    reading, not a quality gate: the measured disagreements (23 of 34,460 player-games, Oct 6 2026) read as corrections that reached one file and not the other."""
    needed = ["week", "two_point_attempt", "rush_attempt", "pass_attempt", "sack", "complete_pass", "rusher_player_id", "receiver_player_id", "passer_player_id", "rushing_yards",
              "receiving_yards", "passing_yards", "rush_touchdown", "pass_touchdown", "interception", "lateral_rusher_player_id", "lateral_rushing_yards", "lateral_receiver_player_id", "lateral_receiving_yards"]
    disagreements = []
    for season_year in seasons:
        plays = read_table(os.path.join(DATA_DIR, f"pbp_{season_year}.csv.gz"), usecols=lambda column_name: column_name in needed, low_memory=False); plays = plays[plays.two_point_attempt != 1]
        stats = read_table(os.path.join(DATA_DIR, f"stats_{season_year}.csv.gz"), low_memory=False)
        targeted = plays[(plays.pass_attempt == 1) & plays.receiver_player_id.notna() & (plays.sack != 1)]; passes = plays[(plays.pass_attempt == 1) & (plays.sack != 1)]
        parts = [plays[plays.rush_attempt == 1].groupby(["rusher_player_id", "week"]).agg(carries=("rush_attempt", "size"), rushing_yards=("rushing_yards", "sum"), rushing_tds=("rush_touchdown", "sum")),
                 plays[plays.lateral_rusher_player_id.notna()].groupby(["lateral_rusher_player_id", "week"]).agg(rushing_yards=("lateral_rushing_yards", "sum")),
                 targeted.groupby(["receiver_player_id", "week"]).agg(targets=("pass_attempt", "size"), receptions=("complete_pass", "sum"), receiving_yards=("receiving_yards", "sum"), receiving_tds=("pass_touchdown", "sum")),
                 plays[plays.lateral_receiver_player_id.notna()].groupby(["lateral_receiver_player_id", "week"]).agg(receiving_yards=("lateral_receiving_yards", "sum")),
                 passes.groupby(["passer_player_id", "week"]).agg(attempts=("pass_attempt", "size"), completions=("complete_pass", "sum"), passing_yards=("passing_yards", "sum"), passing_tds=("pass_touchdown", "sum"), interceptions=("interception", "sum"))]
        for part in parts: part.index.names = ["player_id", "week"]
        built = pd.concat([part.reset_index() for part in parts]).groupby(["player_id", "week"], as_index=False).sum(min_count=1)
        joined = built.rename(columns={column_name: "pbp_" + column_name for column_name in PBP_BOX_COLUMNS}).merge(stats, on=["player_id", "week"], how="inner"); season_disagreements = 0
        for pbp_column, stats_column in PBP_BOX_COLUMNS.items():
            differing = joined[joined["pbp_" + pbp_column].fillna(0).round(6) != joined[stats_column].fillna(0).round(6)]
            disagreements += [(season_year, row.player_id, row.week, stats_column, getattr(row, stats_column), getattr(row, "pbp_" + pbp_column)) for row in differing.itertuples(index=False)]; season_disagreements += len(differing)
        report.say(f"  play-by-play reconciliation {season_year}: player-games {len(joined)}, values differing {season_disagreements}")
    pd.DataFrame(disagreements, columns=["season", "player_id", "week", "column", "stats_value", "pbp_value"]).to_csv(os.path.join(FACTS_DIR, "pbp_crosscheck.csv"), index=False)
    report.say(f"PLAY-BY-PLAY reconciliation (a reading; the stats file is the source of record): {len(disagreements)} differing values written to facts/pbp_crosscheck.csv")
# ---------------- the door: the information set (results through week N-1 + week N's price file) ----------------
SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]
WEEKN = ["report_status", "practice_status", "roster_status", "implied", "fav_by", "total_line"]; WEEKN_PREFIX = ("report_", "practice_")   # week N's publications outside the information set
game_context = ["rest", "is_home"]                     # week N's schedule, also in the price file's Game Info
OUTC = ["dk_points", "attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions", "sacks_suffered", "carries", "rushing_yards",
        "rushing_tds", "targets", "receptions", "receiving_yards", "receiving_tds", "receiving_air_yards", "carry_share", "target_share", "air_yards_share", "snap_share",
        "offense_snaps", "recorded", "redzone_targets", "goal_line_targets", "redzone_carries", "goal_line_carries", "redzone_attempts", "redzone_target_share", "redzone_carry_share"]                     # outcome columns: labels, never inputs about the same week
def outside(cols): return [column_name for column_name in cols if column_name in WEEKN or str(column_name).startswith(WEEKN_PREFIX)]
def team_game():
    """The ONE reader of facts/team_game.csv.gz: week N's publications outside the information set are dropped here."""
    team_games = pd.read_csv(os.path.join(FACTS_DIR, "team_game.csv.gz"), low_memory=False).rename(columns={'neutral_secs_per_play': 'neutral_seconds_per_play'}); team_games = team_games.drop(columns=outside(team_games.columns))
    team_games["team_game_no"] = team_games.groupby(["season", "team"]).week.rank(method="first")        # team-game order inside a season, byes skipped
    return team_games
def schedule():
    """The ONE reader of facts/game.csv.gz, schedule columns only (published before the season, inside the information set): game_id, season, week, gameday,
    gametime (nflverse: US Eastern), home_team, away_team.  Scores, lines and weather are not read here."""
    return pd.read_csv(os.path.join(FACTS_DIR, "game.csv.gz"), low_memory=False)[["game_id", "season", "week", "gameday", "gametime", "home_team", "away_team"]]
GAME_STATUSES = ("Out", "Doubtful", "Questionable")   # the injury report's game designations as its file records them (batch 71; a listing without one carries none)
def game_status_as_of(seasons):
    """THE INJURY REPORT AS OF THE FREEZE (project owner, Oct 8 2026; batch 71): the one door through which week N's report enters the information set.  One row per
    player-week of the given seasons with a game designation (GAME_STATUSES): player_id, season, week, game_status_as_of; and each season's construction
    (a season with a file has one, whether or not any designation survives).  Returns (rows, {season: construction}).
    A season whose file stamps its rows (date_modified): the latest row stamped at or before the boundary - the earlier of the freeze (Saturday 03:00 ET: the
    week's first Sunday kickoff date less 21 hours) and the team's kickoff (schedule, US Eastern) - 'as of the freeze'.  A row last changed after the boundary
    is not read: its pre-freeze value was overwritten in the file (injury_leak_read_v2: 390 of 4,652 listings, 8.4%).  A season whose file carries no stamp
    (2025 and 2026 as fetched): the file's row, 'latest - unstamped' (injury_leak_read_v2: leak against the as-of view .0063 per slate, largest .0079).
    A season without a file returns no row."""
    games = schedule(); games = games.assign(kickoff=pd.to_datetime(games.gameday.astype(str) + " " + games.gametime.astype(str), errors="coerce").dt.tz_localize(str(ET), ambiguous="NaT", nonexistent="NaT"))
    sundays = games[games.kickoff.dt.dayofweek == 6].groupby(["season", "week"]).kickoff.min().dt.normalize().rename("sunday").reset_index(); sundays["freeze"] = sundays.sunday - pd.Timedelta(hours=21)
    kicks = pd.concat([games[["season", "week", "home_team", "kickoff"]].rename(columns={"home_team": "team"}), games[["season", "week", "away_team", "kickoff"]].rename(columns={"away_team": "team"})])
    kicks = kicks.assign(team=fix_names(kicks.team)).merge(sundays[["season", "week", "freeze"]], on=["season", "week"], how="left"); kicks["boundary"] = kicks[["kickoff", "freeze"]].min(axis=1)
    frames, constructions = [], {}
    for season_year in seasons:
        report_rows = read_data(f"injuries_{season_year}.csv")
        if report_rows is None: continue
        report_rows = report_rows[report_rows.game_type == "REG"] if "game_type" in report_rows else report_rows
        report_rows = report_rows.dropna(subset=["gsis_id"]); report_rows = report_rows.assign(team=fix_names(report_rows.team))
        if "date_modified" in report_rows:
            report_rows = report_rows.assign(stamp=pd.to_datetime(report_rows.date_modified, errors="coerce", utc=True)).merge(kicks[["season", "week", "team", "boundary"]], on=["season", "week", "team"], how="left")
            report_rows = report_rows[report_rows.stamp <= report_rows.boundary].sort_values("stamp", kind="stable").drop_duplicates(["season", "week", "gsis_id"], keep="last"); constructions[season_year] = "as of the freeze"
        else:
            fetch_record = read_data(f"injuries_{season_year}_fetched.csv")   # batch 72: ingest's fetch time is the stamp of a file that carries none - no row in it is newer
            if fetch_record is not None:
                report_rows = report_rows.assign(stamp=pd.to_datetime(fetch_record.fetched_at, utc=True).max()).merge(kicks[["season", "week", "team", "boundary"]], on=["season", "week", "team"], how="left")
                report_rows = report_rows[report_rows.stamp <= report_rows.boundary].drop_duplicates(["season", "week", "gsis_id"], keep="last"); constructions[season_year] = "as of the freeze"
            else: report_rows = report_rows.drop_duplicates(["season", "week", "gsis_id"], keep="last"); constructions[season_year] = "latest - unstamped"
        frames.append(report_rows[report_rows.report_status.isin(GAME_STATUSES)].rename(columns={"gsis_id": "player_id", "report_status": "game_status_as_of"})[["player_id", "season", "week", "game_status_as_of"]])
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["player_id", "season", "week", "game_status_as_of"])), constructions
def active_keys():
    """THE FINAL ACTIVE LIST (project owner, Oct 8 2026: at decision time the active / inactive list published about 90 minutes before kickoff is known; batch 77):
    {(season, week, team): frozenset of player_ids whose game-day roster status is ACT}.  The one door through which week N's roster status enters the
    information set; a player with no status row that week is not active (status_door_read_v1: no non-ACT player played, 0 of 3,103)."""
    rows = pd.read_csv(os.path.join(FACTS_DIR, "player_game.csv.gz"), usecols=["player_id", "season", "week", "team", "roster_status"], low_memory=False)
    rows = rows[rows.roster_status == "ACT"]
    return {(int(season), int(week), team): frozenset(group.player_id) for (season, week, team), group in rows.groupby(["season", "week", "team"])}
def load():
    player_games = pd.read_csv(os.path.join(FACTS_DIR, "player_game.csv.gz"), low_memory=False); player_games = player_games.drop(columns=outside(player_games.columns)); team_games = team_game()
    return player_games[player_games.position.isin(SKILL_POSITIONS)].merge(team_games[["season", "week", "team"] + game_context + ["team_game_no"]], on=["season", "week", "team"], how="left")
def load_as_of(season, week):
    """The information set before week N: facts' player rows of earlier seasons and of the season's weeks < N - the one cut issue-path consumers read (CHARTER
    PROVENANCE ROOT, Oct 6 2026; consumers move onto it one by one, each witnessed)."""
    player_rows = load(); return player_rows[(player_rows.season < season) | ((player_rows.season == season) & (player_rows.week < week))]
def price_file(season, week):
    """The ONE reader of week N's DraftKings Classic price file (written by ingest's fetch to its dk_weekly folder): the only week-N publication inside the information
    set.  DraftKings' Status (week N's roster status) and AvgPointsPerGame are dropped here, unread.  Returns one row per DraftKings player with dk_position, dk_name,
    dk_id, salary, team (canonical), name_key (norm) and game (away@home)."""
    price_rows = read_table(DKW / f"DK_{season}_w{week}.csv").drop(columns=["Status", "AvgPointsPerGame"])
    price_rows = price_rows.rename(columns={"Position": "dk_position", "Name": "dk_name", "ID": "dk_id", "Salary": "salary"})
    price_rows["team"] = fix_names(price_rows.TeamAbbrev); price_rows["name_key"] = norm(price_rows.dk_name); price_rows["game"] = price_rows["Game Info"].str.split(" ").str[0]
    return price_rows
# ---------------- checks owned by facts ----------------
def independent_check():
    """(passed, message): facts' independent check against DraftKings' recorded points at or above its floor (DST 97.5%, skill 99.5%)."""
    report_path = os.path.join(FACTS_DIR, "facts_report.txt"); report_text = open(report_path).read() if os.path.exists(report_path) else ""
    match = re.search(r"DST (\d+) games, exact ([\d.]+)%;\s+skill (\d+) player-games, exact ([\d.]+)%", report_text)
    if not match: return False, "facts_report.txt has no independent check line - run: python3 kit.py facts"
    if float(match.group(2)) < 97.5 or float(match.group(4)) < 99.5: return False, f"independent check below floor: DST {match.group(2)}% (floor 97.5), skill {match.group(4)}% (floor 99.5)"
    return True, f"facts vs DraftKings: DST {match.group(2)}%, skill {match.group(4)}% exact"
def freshness_check():
    """(passed, message): every facts table is newer than facts.py, its producer."""
    tables = glob.glob(os.path.join(FACTS_DIR, "*.csv.gz")); producer_time = os.path.getmtime(os.path.join(ROOT, "facts.py"))
    if not tables: return False, "no facts tables - run: python3 kit.py facts"
    if min(os.path.getmtime(path) for path in tables) < producer_time: return False, "facts/ is older than facts.py - run: python3 kit.py facts"
    return True, f"facts: {len(tables)} tables newer than facts.py"
def lockbox_check(paths):
    """(passed, message): the sealed corpus tiers stay sealed (CHARTER FINAL CORPUS) - no sealed season in facts' player table, and no kit module but ingest.py names the
    corpus folder (its name, its incoming folder or a path under it)."""
    sealed = set(sealed_seasons()); in_facts = sorted(int(season) for season in set(pd.read_csv(os.path.join(FACTS_DIR, "player_game.csv.gz"), usecols=["season"]).season.unique()) & sealed)
    pattern = re.compile("|".join(["CORPUS" + "_DIR", "corpus" + "_incoming", "corpus" + "/"]))   # assembled from parts so this check does not name the folder itself
    named = [os.path.basename(path) for path in paths if os.path.basename(path) != "ingest.py" and pattern.search(open(path, errors="ignore").read())]
    problems = ([f"sealed seasons in facts: {in_facts}"] if in_facts else []) + ([f"the corpus folder named outside ingest.py: {named}"] if named else [])
    return (False, "lockbox: " + "; ".join(problems)) if problems else (True, f"lockbox sealed: {len(sealed)} sealed seasons outside facts; the corpus folder named only by ingest.py")
def information_set_check(paths):
    """(passed, message): only facts.py reads facts' tables and names week N's report, roster status or line; odds data is named only by its fetcher; no bare status."""
    table_pattern = re.compile(r"(player_game|team_game)\.csv"); weekn_pattern = re.compile(r"report_status|practice_status|\bimplied\b|\bfav_by\b|total_line|\broster_status\b")
    odds_pattern = re.compile(r"line_history|line_snapshots|prop_snapshots|odds_api|prop_backtest"); status_pattern = re.compile(r"[\"']status[\"']|\.status\b|\bstatus=")
    texts = {os.path.basename(path): open(path, errors="ignore").read() for path in paths}; problems = []
    problems += [f"facts' tables read outside facts.py: {name}" for name, text in texts.items() if name != "facts.py" and table_pattern.search(text)]
    problems += [f"week-N report / roster status / line named outside facts.py: {name}:{number}" for name, text in texts.items() if name != "facts.py" for number, line in enumerate(text.splitlines(), 1) if weekn_pattern.search(line)]
    problems += [f"odds data named outside its fetcher: {name}" for name, text in texts.items() if name not in ("ingest.py", "facts.py") and odds_pattern.search(text)]
    problems += [f"bare status (TAXONOMY: roster_status / tail_coverage_band / issue_mode): {name}:{number}" for name, text in texts.items() if name not in ("ingest.py", "facts.py") for number, line in enumerate(text.splitlines(), 1) if status_pattern.search(line)]
    return (False, "; ".join(problems[:8])) if problems else (True, f"information set: only facts.py reads facts' tables; week N's report, roster status and line appear in no other module ({len(texts)} checked)")
