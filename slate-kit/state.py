"""state.py - pregame state (Slate Kit module map: state).  Everything a law may condition on at a cutoff, built from facts through week N-1 only: the candidate
universe, played-game windows (season-to-date, recency-weighted shares), constructor states (undefined / zero / nonzero, set where an estimate is formed)
and sufficient statistics.  No fitting, no week-N outcome.  purity() is the producer's non-anticipation test."""
import numpy as np, pandas as pd
from ingest import FROZEN_THRU
from facts import load, team_game, outside, OUTC, SKILL_POSITIONS
ISSUE_WEEKS = range(4, 17)          # the weeks a law, a draw, a participation probability or a card is issued for (and the weeks every fit and atlas row comes from)
HISTORY_MINIMUM = 3                 # earlier played games on this team this season before a player's stat laws issue; earlier games before a team's series issues
PARTICIPATION_WR_MINIMUM = 1        # participation's one recorded exception (avail.py, mirroring Y): a WR issues P(plays) from 1 earlier played game this season
RECEIVER_POSITIONS = ["RB", "WR", "TE"]; count_columns = ["targets", "carries", "attempts"]
skill_columns = ["targets", "carries", "receptions", "receiving_yards", "rushing_yards", "rushing_tds", "receiving_tds", "redzone_targets", "redzone_carries"]
qb_columns = ["attempts", "completions", "passing_yards", "passing_tds", "redzone_attempts", "passing_interceptions", "carries", "rushing_yards", "rushing_tds", "redzone_carries"]
DECAY_WEIGHT_GRID = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
ROLE = ["dk_points", "snap_share", "target_share", "carry_share", "air_yards_share"]
# ---------------- played-game windows ----------------
def features(player_rows):
    """Windows over games PLAYED before this one: x_previous_k = k-th previous appearance (may cross seasons); x_mean_season_pregame = earlier games this season."""
    history_rows = player_rows[player_rows.played == 1].sort_values(["player_id", "season", "week"]).copy(); player_groups = history_rows.groupby("player_id")
    for column_name in ROLE:
        for lag_number in (1, 2, 3): history_rows[f"{column_name}_previous_{lag_number}"] = player_groups[column_name].shift(lag_number)
        group_keys = [history_rows.player_id, history_rows.season]                  # earlier games only: the current value never enters the arithmetic
        prior_sum = history_rows[column_name].fillna(0).groupby(group_keys).shift(1).fillna(0); prior_count = history_rows[column_name].notna().astype(float).groupby(group_keys).shift(1).fillna(0)
        history_rows[f"{column_name}_mean_season_pregame"] = prior_sum.groupby(group_keys).cumsum() / prior_count.groupby(group_keys).cumsum().replace(0, np.nan)
    previous = history_rows.groupby(["player_id", "season"]).dk_points.mean().rename("dk_points_mean_previous_season").reset_index(); previous["season"] += 1
    history_rows = history_rows.merge(previous, on=["player_id", "season"], how="left")
    return history_rows
def candidates(player_rows, team_games):
    """Each team's pregame candidates for week N: the players with a row in its previous team-game (priced, rostered, listed or recorded then)."""
    previous_weeks = team_games[["season", "team", "team_game_no", "week"]].rename(columns={"week": "team_prev_week"}); previous_weeks["team_game_no"] += 1
    team_lagged = team_games.merge(previous_weeks, on=["season", "team", "team_game_no"], how="left").dropna(subset=["team_prev_week"]); team_lagged["team_prev_week"] = team_lagged.team_prev_week.astype(int)
    candidate_rows = team_lagged[["season", "team", "week", "team_prev_week"]].merge(player_rows[["player_id", "season", "week", "team", "position"]].rename(columns={"week": "team_prev_week"}), on=["season", "team", "team_prev_week"])
    return candidate_rows[["player_id", "season", "week", "team", "position"]].drop_duplicates(["player_id", "season", "week"])
# ---------------- participation inputs (the candidate frame of avail.py and score_t.py, one producer now) ----------------
PARTICIPATION_INPUTS = ["snap_share_mean_season_pregame", "snap_share_recent1", "games_before", "games_missed", "miss_share"]
def participation_frame(player_rows, team_games, seasons, weeks):
    """Every skill candidate of the given seasons and weeks with participation inputs from his earlier played games of the season (games_before, the season-to-date
    snap share, last game's snap share, games_missed = team-games missed since his last played game on the same team, miss_share), the T1 grid (games_missed_band,
    snap_state_label), the domain (3+ earlier played games, or a WR with 1-2, and every input defined) with the reason a row is outside it, and played (a label: a
    played row that week; no row = 0).  The construction is avail.py's and score_t.py's, line for line."""
    key_columns = ["player_id", "season", "week"]
    candidate_rows = candidates(player_rows, team_games); candidate_rows = candidate_rows[candidate_rows.position.isin(SKILL_POSITIONS) & candidate_rows.season.isin(list(seasons)) & candidate_rows.week.isin(list(weeks))]
    candidate_rows = candidate_rows.sort_values(key_columns + ["team"], kind="stable").drop_duplicates(key_columns).merge(team_games[["season", "team", "week", "team_game_no"]], on=["season", "team", "week"], how="left")
    played_rows = player_rows[player_rows.played == 1][key_columns + ["team", "snap_share"]].drop_duplicates(key_columns).merge(team_games[["season", "team", "week", "team_game_no"]], on=["season", "team", "week"], how="left")
    played_rows = played_rows.sort_values(key_columns, kind="stable").copy(); group_keys = [played_rows.player_id, played_rows.season]
    played_rows["games_season_postgame"] = played_rows.groupby(["player_id", "season"]).cumcount() + 1
    played_rows["snap_share_mean_season_postgame"] = played_rows.snap_share.fillna(0).groupby(group_keys).cumsum() / played_rows.snap_share.notna().astype(float).groupby(group_keys).cumsum().replace(0, np.nan)
    played_rows = played_rows.rename(columns={"snap_share": "snap_share_recent1", "team_game_no": "game_number_previous_1", "team": "team_previous_1"})
    candidate_rows = pd.merge_asof(candidate_rows.sort_values("week", kind="stable"), played_rows[key_columns + ["games_season_postgame", "snap_share_mean_season_postgame", "snap_share_recent1", "game_number_previous_1", "team_previous_1"]].sort_values("week", kind="stable"),
                                   on="week", by=["player_id", "season"], allow_exact_matches=False)
    candidate_rows["games_before"] = candidate_rows.games_season_postgame.fillna(0); candidate_rows["snap_share_mean_season_pregame"] = candidate_rows.snap_share_mean_season_postgame
    candidate_rows["games_missed"] = np.where(candidate_rows.team_previous_1 == candidate_rows.team, (candidate_rows.team_game_no - 1 - candidate_rows.game_number_previous_1).clip(lower=0), np.nan)
    candidate_rows["miss_share"] = np.where(candidate_rows.team_game_no > 1, ((candidate_rows.team_game_no - 1) - candidate_rows.games_before).clip(lower=0) / (candidate_rows.team_game_no - 1), np.nan)
    candidate_rows = candidate_rows.merge(player_rows[key_columns + ["played"]].drop_duplicates(key_columns), on=key_columns, how="left"); candidate_rows["played"] = (candidate_rows.played == 1).astype(float)
    enough_history = (candidate_rows.games_before >= HISTORY_MINIMUM) | ((candidate_rows.position == "WR") & candidate_rows.games_before.between(PARTICIPATION_WR_MINIMUM, HISTORY_MINIMUM - 1))
    undefined_inputs = candidate_rows[PARTICIPATION_INPUTS].isna()
    undefined_names = pd.Series([", ".join(name for name, undefined in zip(PARTICIPATION_INPUTS, row) if undefined) for row in undefined_inputs.itertuples(index=False)], index=candidate_rows.index, dtype=object)
    candidate_rows["domain_reason"] = np.where(candidate_rows.games_before == 0, "no earlier played game this season", np.where(~enough_history, f"fewer than {HISTORY_MINIMUM} earlier played games (a WR: none)",
        np.where(undefined_inputs.games_missed, "team change since his last played game", np.where(undefined_inputs.any(axis=1), "input undefined: " + undefined_names, ""))))
    candidate_rows["in_domain"] = candidate_rows.domain_reason == ""
    candidate_rows["games_missed_band"] = np.select([candidate_rows.games_missed == 0, candidate_rows.games_missed == 1], ["gap 0", "gap 1"], "gap 2+")
    candidate_rows["snap_state_label"] = np.select([candidate_rows.snap_share_mean_season_pregame < .35, candidate_rows.snap_share_mean_season_pregame < .70], ["low", "mid"], "high")
    return candidate_rows.reset_index(drop=True)
# ---------------- the DST frame (dstick.py's rows via retarget.py, one producer now) ----------------
DST_OPPONENT_INPUTS = ["opponent_offense_pts_for_mean_season_pregame", "opponent_offense_giveaways_mean_season_pregame", "opponent_offense_sacks_taken_mean_season_pregame"]
DST_INPUTS = ["team_dst_points_mean_season_pregame", "team_games_season_pregame"] + DST_OPPONENT_INPUTS
def dst_frame(team_games):
    """Every team-game with its DST inputs from the team's earlier games of the season: team_games_season_pregame (earlier team-games), the season-to-date DST points
    mean, and the opponent offense's season-to-date points scored, giveaways and sacks taken (from the opponent's own earlier games).  retarget.py's construction."""
    team_rows = team_games.sort_values(["team", "season", "week"]).reset_index(drop=True); season_groups = team_rows.groupby(["team", "season"])
    for column_name in ("dst_points", "pts_for", "giveaways", "sacks_taken"): team_rows["team_" + column_name + "_mean_season_pregame"] = season_groups[column_name].transform(lambda series: series.shift(1).expanding().mean())
    team_rows["team_games_season_pregame"] = season_groups.cumcount()
    opponent_rows = team_rows[["season", "week", "team", "team_pts_for_mean_season_pregame", "team_giveaways_mean_season_pregame", "team_sacks_taken_mean_season_pregame"]].rename(columns={"team": "opponent",
        "team_pts_for_mean_season_pregame": "opponent_offense_pts_for_mean_season_pregame", "team_giveaways_mean_season_pregame": "opponent_offense_giveaways_mean_season_pregame", "team_sacks_taken_mean_season_pregame": "opponent_offense_sacks_taken_mean_season_pregame"})
    return team_rows.merge(opponent_rows, on=["season", "week", "opponent"], how="left")
# ---------------- the law-table frames: team series, skill and QB windows (history, or padded with week-N candidate rows carrying no outcomes) ----------------
def weighted_mean(line_text, decay_weight):
    weighted_values = np.full(len(line_text), np.nan); s = weight_total = 0.0
    for row_number, current_value in enumerate(line_text):
        if weight_total > 0: weighted_values[row_number] = s / weight_total
        s = decay_weight * s + current_value; weight_total = decay_weight * weight_total + 1.0
    return weighted_values
def box_zero(box_rows, cols, what):
    """Played rows with no box-score record are recorded zeros only when the record is wholly absent, the player was on the field (offense_snaps > 0), dk_points == 0
    and the red-zone columns are 0; anything else refuses (BOX-SCORE ZEROS UNDER D)."""
    box_columns = [column_name for column_name in cols if not column_name.startswith("redzone")]; redzone_columns = [column_name for column_name in cols if column_name.startswith("redzone")]; missing_mask = box_rows[box_columns].isna()
    if box_rows[redzone_columns].isna().any().any(): raise SystemExit(f"box_zero: {what} red-zone column missing on {int(box_rows[redzone_columns].isna().any(axis=1).sum())} played rows - refused")
    part = missing_mask.any(axis=1) & ~missing_mask.all(axis=1)
    if part.any(): raise SystemExit(f"box_zero: {what} {int(part.sum())} played rows with a partly missing box score - refused")
    decay_weight = missing_mask.all(axis=1); invalid_rows = decay_weight & ~((box_rows.offense_snaps > 0) & (box_rows.dk_points == 0) & (box_rows[redzone_columns] == 0).all(axis=1))
    if invalid_rows.any(): raise SystemExit(f"box_zero: {what} {int(invalid_rows.sum())} played rows missing a box score without on-field zero evidence - refused")
    box_rows = box_rows.copy(); box_rows.loc[decay_weight, box_columns] = 0.0; return box_rows
def history_frames(player_rows, team_games):
    """Every season <= FROZEN_THRU, outcomes present: team frame, skill window, QB window."""
    return build_frames(player_rows[player_rows.season <= FROZEN_THRU], team_games, team_games.season <= FROZEN_THRU, [], [])
def route_rule_b(player_rows, candidate_rows):
    """B POSITION RULE (project owner ruling (b), Oct 4 2026): a week-N candidate's position = the most frequent stats label over his earlier played games of the season
    (weeks < N), ties to the most recent tied label; domain = the door's played rows (QB / RB / WR / TE).  No earlier played labelled game this season ->
    UNRESOLVED POSITION (not routed, counted).  The rule changes routing, never membership or the historical law keys.  Returns the candidates with previous_label
    (the previous team-game label), label_sequence (earlier played labels in week order) and position (the routed label, or UNRESOLVED POSITION)."""
    candidate_keys = ["player_id", "season", "week"]; played = player_rows[player_rows.played == 1].drop_duplicates(candidate_keys)[candidate_keys + ["position"]].rename(columns={"week": "label_week", "position": "label"})
    earlier = candidate_rows[candidate_keys].merge(played, on=["player_id", "season"]); earlier = earlier[earlier.label_week < earlier.week].sort_values(candidate_keys + ["label_week"], kind="stable")
    sequences = earlier.groupby(candidate_keys).label.agg(",".join).rename("label_sequence")
    tallies = earlier.groupby(candidate_keys + ["label"]).agg(label_count=("label", "size"), last_week=("label_week", "max")).reset_index()
    routed = tallies.sort_values(candidate_keys + ["label_count", "last_week"], kind="stable").drop_duplicates(candidate_keys, keep="last").set_index(candidate_keys).label.rename("routed_label")
    routed_rows = candidate_rows.rename(columns={"position": "previous_label"}).merge(sequences.reset_index(), on=candidate_keys, how="left").merge(routed.reset_index(), on=candidate_keys, how="left")
    routed_rows["position"] = routed_rows.routed_label.fillna("UNRESOLVED POSITION"); routed_rows["label_sequence"] = routed_rows.label_sequence.fillna("")
    return routed_rows.drop(columns="routed_label")
def issue_frames(player_rows, team_games, issue_season, issue_week):
    """Results through week N-1 (and seasons <= FROZEN_THRU before the issue season), padded with week N's team rows and candidate rows carrying no outcomes; candidates
    routed by rule (b).  Returns the frames and every candidate with its routing (UNRESOLVED POSITION candidates are counted, not padded)."""
    player_keep = ((player_rows.season < issue_season) & (player_rows.season <= FROZEN_THRU)) | ((player_rows.season == issue_season) & (player_rows.week < issue_week)); team_keep = ((team_games.season < issue_season) & (team_games.season <= FROZEN_THRU)) | ((team_games.season == issue_season) & (team_games.week < issue_week))
    player_rows = player_rows[player_keep]
    pad_teams = team_games[(team_games.season == issue_season) & (team_games.week == issue_week)][["season", "week", "team"]].drop_duplicates().assign(is_pad=True)
    candidate_rows = candidates(player_rows, team_games); candidate_rows = route_rule_b(player_rows, candidate_rows[(candidate_rows.season == issue_season) & (candidate_rows.week == issue_week)])
    padded_candidates = candidate_rows[candidate_rows.position.isin(["QB"] + RECEIVER_POSITIONS)][["player_id", "season", "week", "team", "position"]].assign(is_pad=True)
    return build_frames(player_rows, team_games, team_keep, [pad_teams], [padded_candidates]) + (candidate_rows,)
def team_volume(player_rows):
    """Team count volume per team-game: the played rows' count_columns summed by (season, week, team) - one producer for the frames and the ladder's team reference."""
    return player_rows[player_rows.played == 1].groupby(["season", "week", "team"])[count_columns].sum().reset_index()
def build_frames(player_rows, team_games, team_keep, pad_team_frames, candidate_frames):
    team_volumes = team_volume(player_rows)
    team_frame = team_games[team_games.plays.notna() & team_keep][["season", "week", "team"]].drop_duplicates().merge(team_volumes, on=["season", "week", "team"], how="inner").assign(is_pad=False)
    team_frame = pd.concat([team_frame] + pad_team_frames, ignore_index=True)
    team_frame = team_frame.sort_values(["team", "season", "week"]).reset_index(drop=True); team_groups = team_frame.groupby(["team", "season"]); team_frame["tn"] = team_groups.cumcount()
    for column_name in count_columns: team_frame[column_name + "_tb"] = team_groups[column_name].transform(lambda current_value: current_value.shift(1).expanding().mean())
    for column_name in count_columns:   # THE LEAGUE TO DATE (sprint 30): the league's mean per team-game over the season's weeks < N, every team-game played - pregame only
        weekly = team_frame.groupby(["season", "week"])[column_name].agg(["sum", "count"]).reset_index().sort_values(["season", "week"]); by_season = weekly.groupby("season")
        weekly[column_name + "_lb"] = (by_season["sum"].cumsum() - weekly["sum"]) / (by_season["count"].cumsum() - weekly["count"]).where(lambda games: games > 0)
        team_frame = team_frame.merge(weekly[["season", "week", column_name + "_lb"]], on=["season", "week"], how="left")
    team_frame = team_frame.sort_values(["team", "season", "week"]).reset_index(drop=True)
    eligible_teams = team_frame[team_frame.week.isin(list(ISSUE_WEEKS)) & (team_frame.tn >= HISTORY_MINIMUM)].dropna(subset=[column_name + "_tb" for column_name in count_columns]).reset_index(drop=True)
    skill_rows = box_zero(player_rows[(player_rows.played == 1) & player_rows.position.isin(RECEIVER_POSITIONS)], skill_columns, "skill")[["player_id", "season", "week", "team", "position", "target_share", "carry_share"] + skill_columns].copy().assign(is_pad=False)
    skill_rows = skill_rows.dropna(subset=["target_share", "carry_share"])
    skill_rows = pd.concat([skill_rows] + [candidate_rows[candidate_rows.position.isin(RECEIVER_POSITIONS)] for candidate_rows in candidate_frames], ignore_index=True)
    skill_rows = skill_rows.sort_values(["player_id", "season", "team", "week"]).reset_index(drop=True)
    skill_rows["td"] = skill_rows.rushing_tds + skill_rows.receiving_tds; skill_rows["rz"] = skill_rows.redzone_targets + skill_rows.redzone_carries
    player_groups = skill_rows.groupby(["player_id", "season", "team"]); skill_rows["n"] = player_groups.cumcount()
    for column_name in ("targets", "carries", "td", "receptions", "receiving_yards", "rushing_yards"): skill_rows[column_name + "_pb"] = player_groups[column_name].transform(lambda current_value: current_value.shift(1).expanding().mean())
    for column_name in ("targets", "carries", "receptions", "receiving_yards", "rushing_yards"): skill_rows[column_name + "_ps"] = player_groups[column_name].transform(lambda current_value: current_value.shift(1).cumsum())   # CONSTRUCTOR STATE step 2
    skill_rows["td_ps"] = player_groups.td.transform(lambda current_value: current_value.shift(1).cumsum()); skill_rows["rz_ps"] = player_groups.rz.transform(lambda current_value: current_value.shift(1).cumsum()); skill_rows["rz_pg"] = player_groups.rz.transform(lambda current_value: current_value.shift(1).expanding().mean())
    for share in ("target_share", "carry_share"):
        for decay_weight in DECAY_WEIGHT_GRID: skill_rows[f"{share}@{decay_weight}"] = player_groups[share].transform(lambda current_value, decay_weight=decay_weight: weighted_mean(current_value.values, decay_weight))
    skill_window = skill_rows[skill_rows.week.isin(list(ISSUE_WEEKS)) & (skill_rows.n >= HISTORY_MINIMUM)].merge(eligible_teams[["season", "week", "team", "tn", "targets_tb", "carries_tb", "targets_lb", "carries_lb"]], on=["season", "week", "team"], how="inner").reset_index(drop=True)
    qb_rows = box_zero(player_rows[(player_rows.played == 1) & (player_rows.position == "QB")], qb_columns, "QB")[["player_id", "season", "week", "team"] + qb_columns].copy().assign(is_pad=False)
    qb_rows = pd.concat([qb_rows] + [candidate_rows[candidate_rows.position == "QB"].drop(columns="position") for candidate_rows in candidate_frames], ignore_index=True)
    qb_rows = qb_rows.merge(team_frame[["season", "week", "team", "attempts"]].rename(columns={"attempts": "team_att"}), on=["season", "week", "team"], how="inner")
    qb_rows["att_share"] = qb_rows.attempts / qb_rows.team_att.replace(0, np.nan)
    qb_rows = qb_rows[qb_rows["is_pad"].astype(bool) | qb_rows.att_share.notna()].sort_values(["player_id", "season", "team", "week"]).reset_index(drop=True)
    player_groups = qb_rows.groupby(["player_id", "season", "team"]); qb_rows["n"] = player_groups.cumcount()
    for column_name in qb_columns: qb_rows[column_name + "_pb"] = player_groups[column_name].transform(lambda current_value: current_value.shift(1).expanding().mean()); qb_rows[column_name + "_ps"] = player_groups[column_name].transform(lambda current_value: current_value.shift(1).cumsum())
    for decay_weight in DECAY_WEIGHT_GRID: qb_rows[f"share@{decay_weight}"] = player_groups.att_share.transform(lambda current_value, decay_weight=decay_weight: weighted_mean(current_value.values, decay_weight))
    qb_window = qb_rows[qb_rows.week.isin(list(ISSUE_WEEKS)) & (qb_rows.n >= HISTORY_MINIMUM)].merge(eligible_teams[["season", "week", "team", "tn", "attempts_tb", "attempts_lb"]], on=["season", "week", "team"], how="inner").reset_index(drop=True)
    return eligible_teams, skill_window, qb_window
# ---------------- constructor states and sufficient statistics (CONSTRUCTOR STATE) ----------------
def constructor_state(line_text):
    """CONSTRUCTOR STATE: undefined (estimator not formed) / zero (formed, exactly 0) / nonzero (formed, != 0); set where the estimate is constructed."""
    line_text = np.asarray(line_text, float); s = np.where(np.isnan(line_text), "undefined", np.where(line_text == 0, "zero", np.where(np.isfinite(line_text), "nonzero", "invalid")))
    if (s == "invalid").any(): raise SystemExit(f"CONSTRUCTOR STATE: {int((s == 'invalid').sum())} values neither undefined, zero nor finite nonzero")
    return s
RATE_PAIRS = [("catch rate", "receptions_ps", "targets_ps", ("RB", "TE")), ("TDs per reception", "td_ps", "receptions_ps", ("WR",)),
              ("receiving yards per reception", "receiving_yards_ps", "receptions_ps", ("RB", "WR", "TE"))]
def rate_state(s, games_count):
    """CONSTRUCTOR STATE for a rate from sufficient statistics: exposure 0 -> undefined, successes 0 -> zero, else nonzero."""
    s, games_count = np.asarray(s, float), np.asarray(games_count, float)
    if np.isnan(s).any() or np.isnan(games_count).any() or (games_count < 0).any(): raise SystemExit("CONSTRUCTOR STATE: invalid sufficient statistic")
    return np.where(games_count == 0, "undefined", np.where(s == 0, "zero", "nonzero"))
def sufficient(skill_forecast, qb_forecast):
    skill_table = skill_forecast[["player_id", "season", "week", "position", "n", "targets_ps", "carries_ps", "receptions_ps", "receiving_yards_ps", "rushing_yards_ps", "td_ps"]].rename(columns={"player_id": "key", "n": "games"})
    for label, success_column, attempt_column, poss in RATE_PAIRS:
        row_mask = skill_table.position.isin(poss).values; rate_states = np.full(len(skill_table), "not a registered pair", dtype=object); rate_states[row_mask] = rate_state(skill_table.loc[row_mask, success_column], skill_table.loc[row_mask, attempt_column]); skill_table[f"state {label}"] = rate_states
    qb_table = qb_forecast[["player_id", "season", "week", "n", "attempts_ps", "completions_ps", "passing_yards_ps", "passing_tds_ps", "passing_interceptions_ps", "carries_ps", "rushing_yards_ps",
            "rushing_tds_ps"]].rename(columns={"player_id": "key", "n": "games"}).assign(position="QB")
    qb_table["state rushing yards per carry"] = rate_state(qb_table.rushing_yards_ps, qb_table.carries_ps)
    return pd.concat([skill_table, qb_table], ignore_index=True)
# ---------------- THE BOX-SCORE GRAPH AND THE THREE ZEROS (CHARTER THE THREE ZEROS, Oct 6 2026: one constructor, one graph, for facts, laws and draws) ----------------
TERM_COLUMNS = {"F5 targets": ("targets",), "F5 carries": ("carries",), "F5 receptions": ("receptions",), "F5 receiving yards": ("receiving_yards",), "F5 rushing yards": ("rushing_yards",),
                "F5 TDs": ("rushing_tds", "receiving_tds"), "Q1 attempts": ("attempts",), "Q2 completions": ("completions",), "Q3 passing yards": ("passing_yards",), "Q4 passing TDs": ("passing_tds",),
                "Q5 interceptions": ("passing_interceptions",), "QB carries": ("carries",), "QB rushing yards": ("rushing_yards",), "QB rushing TDs": ("rushing_tds",)}   # each term's facts columns, witnessed against the recorded law table by score-week
HISTORY_SUMS = {"F5 targets": "targets_ps", "F5 carries": "carries_ps", "F5 receptions": "receptions_ps", "F5 receiving yards": "receiving_yards_ps", "F5 rushing yards": "rushing_yards_ps", "F5 TDs": "td_ps",
                "Q1 attempts": "attempts_ps", "Q2 completions": "completions_ps", "Q3 passing yards": "passing_yards_ps", "Q4 passing TDs": "passing_tds_ps", "Q5 interceptions": "passing_interceptions_ps",
                "QB carries": "carries_ps", "QB rushing yards": "rushing_yards_ps", "QB rushing TDs": "rushing_tds_ps"}   # each term's season-to-date sum among the sufficient statistics (sufficient)
STRUCTURAL_PARENTS = {"F5 receptions": ("F5 targets",), "F5 receiving yards": ("F5 receptions",), "F5 rushing yards": ("F5 carries",), "F5 TDs": ("F5 receptions", "F5 carries"),
                      "Q2 completions": ("Q1 attempts",), "Q3 passing yards": ("Q2 completions",), "Q4 passing TDs": ("Q2 completions",), "Q5 interceptions": ("Q1 attempts",),
                      "QB rushing yards": ("QB carries",), "QB rushing TDs": ("QB carries",)}   # THE BOX-SCORE GRAPH, one table for facts, laws and draws: a term is 0 whenever the sum of its parent terms is 0; a term absent here is a root
STRUCTURAL_ORDERS = ("F5 receptions", "F5 TDs", "Q2 completions", "Q4 passing TDs", "Q5 interceptions", "QB rushing TDs")   # the counts bounded by their parent sum (a catch needs a target, a TD a touch); yards are not bounded
ZERO_KINDS = ("absent", "structural", "measured")
def parent_columns(term): return [column for parent_term in STRUCTURAL_PARENTS[term] for column in TERM_COLUMNS[parent_term]]   # a term's parent as facts columns (TERM_COLUMNS of each parent term)
def zero_kind_of(term, observed, value, parent):
    """THE ZERO CONSTRUCTOR: the kind of every value of one term, decided once, by three facts read in the order the facts exist - observation, then parent, then value -
    each kind reading exactly one fact the others do not: absent - not observed (reads only the observation; a non-measurement, never a 0 a law learns); structural -
    observed and the parent sum 0 (reads only the parent; the graph forces the value to 0); measured - observed, a positive parent or a root term, and the value 0 (reads
    only the value; the only zero a law learns).  Beside them nonzero, and violation (parent 0, value != 0: the facts contradict the graph; a consumer refuses it, a
    read counts it).  parent is the parent sum, given exactly when the term has STRUCTURAL_PARENTS (refused otherwise).  Refused if an observed row lacks a value or a parent."""
    observed = np.asarray(observed, bool); value = np.asarray(value, float)
    if (parent is None) != (term not in STRUCTURAL_PARENTS): raise SystemExit(f"zero_kind_of {term}: a parent is given exactly when the term has one in STRUCTURAL_PARENTS - refused")
    if np.isnan(value[observed]).any(): raise SystemExit(f"zero_kind_of {term}: {int(np.isnan(value[observed]).sum())} observed rows without a value - refused")
    parent_zero = np.zeros(len(value), bool)
    if parent is not None:
        parent = np.asarray(parent, float)
        if np.isnan(parent[observed]).any(): raise SystemExit(f"zero_kind_of {term}: {int(np.isnan(parent[observed]).sum())} observed rows without a parent value - refused")
        parent_zero = observed & (parent == 0)
    masks = {"absent": ~observed, "violation": parent_zero & (value != 0), "structural": parent_zero & (value == 0), "measured": observed & ~parent_zero & (value == 0), "nonzero": observed & ~parent_zero & (value != 0)}
    return np.select(list(masks.values()), list(masks), "unclassified")
def zero_kinds(term, rows, observed):
    """zero_kind_of over facts columns (TERM_COLUMNS for the value, parent_columns for the parent) - a game's values or a history's sums.  Returns (kinds, values)."""
    value = rows[list(TERM_COLUMNS[term])].sum(axis=1, min_count=len(TERM_COLUMNS[term])).to_numpy(float)
    parent = rows[parent_columns(term)].sum(axis=1, min_count=len(parent_columns(term))).to_numpy(float) if term in STRUCTURAL_PARENTS else None
    return zero_kind_of(term, observed, value, parent), value
def history_kinds(sufficient_rows):
    """The history kind of every term of every sufficient-statistics row (sufficient: the season-to-date sums before week N, games = earlier played games on the team this
    season) - zero_kind_of on HISTORY_SUMS, observed iff games > 0; skill terms on RB / WR / TE rows, QB terms on QB rows.  Long frame: term, position, key, season,
    week, history_kind.  One producer for the laws' routing on the recorded law table and on the issue path."""
    parts = []
    for term, column in HISTORY_SUMS.items():
        rows = sufficient_rows[sufficient_rows.position.isin(["QB"] if term.startswith(("Q", "QB")) else RECEIVER_POSITIONS)]
        if column not in rows or len(rows) == 0: continue
        parent = sum(rows[HISTORY_SUMS[parent_term]].to_numpy(float) for parent_term in STRUCTURAL_PARENTS[term]) if term in STRUCTURAL_PARENTS else None
        parts.append(pd.DataFrame(dict(term=term, position=rows.position.values, key=rows.key.values, season=rows.season.values, week=rows.week.values,
                                       history_kind=zero_kind_of(term, rows.games.to_numpy(float) > 0, rows[column].to_numpy(float), parent))))
    return pd.concat(parts, ignore_index=True).drop_duplicates(["term", "position", "key", "season", "week"])
def box_outcomes(player_rows):
    """Played rows' box scores under box_zero (a played row with a wholly absent record is recorded zeros, anything partial refuses) - the law table's own rule - one row
    per player-week: the skill columns for RB / WR / TE, the QB columns for QB."""
    played_rows = player_rows[player_rows.played == 1].drop_duplicates(["player_id", "season", "week"])
    skill = box_zero(played_rows[played_rows.position.isin(RECEIVER_POSITIONS)], skill_columns, "skill")[["player_id", "season", "week", "dk_points"] + skill_columns]
    quarterbacks = box_zero(played_rows[played_rows.position == "QB"], qb_columns, "QB")[["player_id", "season", "week", "dk_points"] + qb_columns]
    return pd.concat([skill, quarterbacks], ignore_index=True)
def zero_kind_frame(player_rows, cells):
    """Every (term, position) cell's rows - QB / RB / WR / TE player-weeks of facts, played or not - with two kinds from zero_kinds: the game's (observed: played; values:
    the box score under box_zero) and the history's (observed: an earlier played game on the team this season; values: sums over those games, the empty sum 0 at the
    first).  Long frame: term, position, key, season, week, team, played, value, kind, history_games, history_value, history_kind."""
    row_keys = ["player_id", "season", "week"]; columns = sorted(set(skill_columns) | set(qb_columns))
    rows = player_rows[player_rows.position.isin(["QB"] + RECEIVER_POSITIONS)].drop_duplicates(row_keys)[row_keys + ["team", "position", "played"]]
    rows = rows.merge(box_outcomes(player_rows).drop(columns="dk_points"), on=row_keys, how="left").sort_values(["player_id", "season", "team", "week"], kind="stable").reset_index(drop=True)
    played = (rows.played == 1).to_numpy(); counted = rows[columns].where(np.repeat(played[:, None], len(columns), axis=1), 0.0).assign(games=played.astype(float))
    history = counted.groupby([rows.player_id, rows.season, rows.team], dropna=False).cumsum() - counted   # sums over the earlier rows of the player's team-season (the row's own game removed)
    parts = []
    for term, position in cells:
        in_cell = (rows.position == position).to_numpy(); kind, value = zero_kinds(term, rows[in_cell], played[in_cell])
        history_kind, history_value = zero_kinds(term, history[in_cell], history.games[in_cell].to_numpy() > 0)
        parts.append(pd.DataFrame(dict(term=term, position=position, key=rows.player_id[in_cell].values, season=rows.season[in_cell].values, week=rows.week[in_cell].values, team=rows.team[in_cell].values,
                                       played=played[in_cell], value=value, kind=kind, history_games=history.games[in_cell].values, history_value=history_value, history_kind=history_kind)))
    return pd.concat(parts, ignore_index=True)
# ---------------- non-anticipation (CHARTER rule 1) ----------------
def purity():
    """For each cutoff (season, week): keep every row before that week, keep that week's rows with every outcome blanked, delete every later row; rebuild; the cutoff
    week's windows and participation inputs (state.participation_frame: inputs, T1 grid, domain reason) must equal the full build's, cell for cell; and
    no week-N publication outside the information set passes facts' door."""
    window_columns = [f"{column_name}_previous_{lag_number}" for column_name in ROLE for lag_number in (1, 2, 3)] + [f"{column_name}_mean_season_pregame" for column_name in ROLE] + ["dk_points_mean_previous_season"]
    participation_columns = PARTICIPATION_INPUTS + ["games_missed_band", "snap_state_label", "domain_reason"]
    player_rows = load(); team_games = team_game(); window_rows = features(player_rows); mismatch_total = 0
    cutoffs = [(season_value, week_value) for season_value in sorted(set(player_rows.season.unique()) & {2019, 2021, 2024}) for week_value in (4, 9, 15)]
    if len(cutoffs) != 9: raise SystemExit(f"purity: cutoff seasons missing {cutoffs} - an empty cutoff week would pass hollowly; refused")
    for cutoff_season, cutoff_week in cutoffs:
        cut_rows = player_rows[(player_rows.season < cutoff_season) | ((player_rows.season == cutoff_season) & (player_rows.week <= cutoff_week))].copy(); current_mask = (cut_rows.season == cutoff_season) & (cut_rows.week == cutoff_week)
        cut_rows.loc[current_mask, [column_name for column_name in OUTC if column_name in cut_rows]] = np.nan; cut_rows.loc[current_mask, "played"] = 1
        cut_windows = features(cut_rows)
        full_windows = window_rows[(window_rows.season == cutoff_season) & (window_rows.week == cutoff_week)].set_index("player_id")[window_columns]; cut_window_slice = cut_windows[(cut_windows.season == cutoff_season) & (cut_windows.week == cutoff_week)].set_index("player_id")[window_columns].reindex(full_windows.index)
        window_mismatches = int((~np.isclose(full_windows.values.astype(float), cut_window_slice.values.astype(float), rtol=0, atol=0, equal_nan=True)).sum())
        full_participation = participation_frame(player_rows, team_games, [cutoff_season], [cutoff_week]).set_index("player_id")[participation_columns].sort_index()
        cut_participation = participation_frame(cut_rows, team_games, [cutoff_season], [cutoff_week]).set_index("player_id")[participation_columns].reindex(full_participation.index)
        participation_mismatches = int(sum(((full_participation[column] != cut_participation[column]) & ~(full_participation[column].isna() & cut_participation[column].isna())).sum() for column in participation_columns))
        mismatch_total += window_mismatches + participation_mismatches
        print(f"  {cutoff_season} w{cutoff_week:>2}: windows {len(full_windows)} players x {len(window_columns)} -> {window_mismatches} differ;  participation {len(full_participation)} candidates x {len(participation_columns)} -> {participation_mismatches} differ")
    leak = sorted(set(outside(player_rows.columns)) | set(outside(team_games.columns)))
    print("PURE: every cutoff week's windows and participation inputs are identical with that week's outcomes and every later row deleted" if mismatch_total == 0 else f"IMPURE: {mismatch_total} cells differ")
    print("INFO SET PURE: nothing of week N but the price file passes facts' door" if not leak else f"INFO SET IMPURE: {leak}")
    return 0 if mismatch_total == 0 and not leak else 1
