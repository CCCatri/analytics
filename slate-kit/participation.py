"""participation.py - participation (Slate Kit module map: participation; M5, rewritten in batch 71).  The one producer of P(he plays | the information set of week N):
THE WHO-PLAYS LAW (batch 71, R1 of handoff_team_game_worlds; r1_law_read_v1, who_plays_group_read_v1, r1_landing_premises_read_v1), a logistic fit by maximum
likelihood per position on every in-domain candidate of the seasons before the issue season whose injury report is stamped (never trained on an unstamped file):
the T1 cell (state's games-missed band x snap-state label, one indicator each), the exit in his team's previous game (DROP = his snap share there minus his own
season-to-date mean before it; undefined when he did not play it), log(1 + earlier played games this season), the cell's own played rate this season through
week N-1 (logit), the injury report's game designation as of the freeze (facts.game_status_as_of), and his team-position group - log(candidates in it this week)
and log(1 + its mean count of players who played per team-game this season through week N-1).  Every input is week N-1 results, week N's schedule, or the
report as of the freeze.  Inputs come from state.participation_frame; the fit rows are its in-domain rows, weeks 4-16.  week_participation() is the card's door.
participation_check() reads the law's walk-forward beside T1's recorded walk-forward witness (proj/at_t_rows.csv.gz)."""
import os, numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from ingest import PROJ_DIR, FROZEN_THRU, Report
from facts import load, team_game, read_table, plain, game_status_as_of
from state import participation_frame, ISSUE_WEEKS
PARTICIPATION_QUALIFICATION = "ISSUED - WHO-PLAYS LAW (batch 71): walk-forward log loss BETTER than T1 in every judged season; group sums are R2's (not yet drawn jointly)"
def model_rows_of(frame_rows):
    """The fit rows: in-domain participation rows, weeks 4-16."""
    return frame_rows[frame_rows.in_domain & frame_rows.week.isin(list(ISSUE_WEEKS))].reset_index(drop=True)
def week_frame(player_rows, team_games, issue_season, issue_week):
    """Week N's participation frame from results through week N-1 of the issue season only; the played label is week N's outcome and is dropped."""
    earlier_rows = player_rows[(player_rows.season == issue_season) & (player_rows.week < issue_week)]
    return participation_frame(earlier_rows, team_games, [issue_season], [issue_week]).drop(columns="played")
def who_plays_inputs(player_rows, team_games, seasons):
    """Every candidate of the seasons' issue weeks (state.participation_frame) with the law's inputs, each from results before his week (rows of week N carry no
    week-N outcome in any input): cell, DROP, the cell's played rate through N-1 (level_through), group_n, the group's played count per team-game through N-1
    (k_mean_through), the as-of game designation and the season's report construction (facts.game_status_as_of)."""
    frame = participation_frame(player_rows, team_games, list(seasons), ISSUE_WEEKS)
    frame = frame.assign(cell=frame.games_missed_band.astype(str) + " / " + frame.snap_state_label.astype(str))
    played = player_rows[player_rows.played == 1].drop_duplicates(["player_id", "season", "week"])
    snaps = played[["player_id", "season", "week", "snap_share"]].sort_values(["player_id", "season", "week"]).copy()
    snaps["own_mean_before"] = snaps.groupby(["player_id", "season"]).snap_share.transform(lambda shares: shares.shift(1).expanding().mean())
    team_weeks = team_games[["season", "week", "team"]].drop_duplicates().sort_values(["team", "season", "week"]); team_weeks["previous_week"] = team_weeks.groupby(["team", "season"]).week.shift(1)
    frame = frame.merge(team_weeks, on=["season", "week", "team"], how="left").merge(snaps.rename(columns={"week": "previous_week", "snap_share": "previous_snap"}), on=["player_id", "season", "previous_week"], how="left")
    frame["exit_drop"] = frame.previous_snap - frame.own_mean_before
    rates = frame[frame.in_domain].groupby(["season", "cell", "week"]).played.agg(["sum", "size"]).reset_index().sort_values("week")
    rates[["through_sum", "through_rows"]] = rates.groupby(["season", "cell"])[["sum", "size"]].cumsum(); rates["level_through"] = rates.through_sum / rates.through_rows
    frame = pd.merge_asof(frame.sort_values("week"), rates[["season", "cell", "week", "level_through"]].sort_values("week"), on="week", by=["season", "cell"], allow_exact_matches=False, direction="backward")
    group_keys = ["season", "week", "team", "position"]
    counts = frame.groupby(group_keys).agg(group_n=("player_id", "size"), group_played=("played", "sum")).reset_index().sort_values("week")
    counts["k_mean_through"] = counts.groupby(["season", "team", "position"]).group_played.transform(lambda played_counts: played_counts.shift(1).expanding().mean())
    frame = frame.merge(counts[group_keys + ["group_n", "k_mean_through"]], on=group_keys, how="left")
    designations, construction = game_status_as_of(sorted(set(frame.season.astype(int))))
    frame = frame.merge(designations[["player_id", "season", "week", "game_status_as_of"]], on=["player_id", "season", "week"], how="left")
    frame["game_status_as_of"] = frame.game_status_as_of.fillna("NOT LISTED"); frame["designation_construction"] = frame.season.map(construction)
    return frame.sort_values(["season", "week", "team", "player_id"], kind="stable").reset_index(drop=True)
def who_plays_design(rows, cells, designations):
    """The law's columns for rows of one position: one indicator per T1 cell, DROP (0 where undefined) and its undefined indicator, log(1 + earlier games), the
    logit of the cell's rate through N-1 (rates clipped to [.001, .999] so the logit is finite) and its undefined indicator, one indicator per designation, log(group
    size), log(1 + the group's played count through N-1) and its undefined indicator."""
    columns = [(rows.cell == cell).to_numpy(float) for cell in cells] + [rows.exit_drop.fillna(0.0).to_numpy(), rows.exit_drop.isna().to_numpy(float), np.log1p(rows.games_before.to_numpy(float))]
    columns += [logit(rows.level_through.clip(1e-3, 1 - 1e-3)).fillna(0.0).to_numpy(), rows.level_through.isna().to_numpy(float)]
    columns += [(rows.game_status_as_of == designation).to_numpy(float) for designation in designations]
    columns += [np.log(rows.group_n.to_numpy(float)), np.log1p(rows.k_mean_through.fillna(0.0).to_numpy(float)), rows.k_mean_through.isna().to_numpy(float)]
    return np.column_stack(columns)
def who_plays_fit(fit_rows):
    """The law per position by maximum likelihood on fit rows (in-domain, played labelled) of seasons whose report is stamped as of the freeze - never an
    unstamped file (it would teach the law the post-freeze leak).  Returns {position: (cells, designations, coefficients)} and the rows fit."""
    rows = fit_rows[fit_rows.designation_construction == "as of the freeze"]; laws = {}
    for position, position_rows in rows.groupby("position"):
        cells = sorted(set(rows.cell)); designations = sorted(set(position_rows.game_status_as_of) - {"NOT LISTED"}); design = who_plays_design(position_rows, cells, designations); labels = position_rows.played.to_numpy(float)
        def negative_log_likelihood(coefficients): z = design @ coefficients; return float(np.sum(np.logaddexp(0, z) - labels * z) + 1e-6 * coefficients @ coefficients)
        laws[position] = (cells, designations, minimize(negative_log_likelihood, np.zeros(design.shape[1]), method="L-BFGS-B").x)
    return laws, rows
def who_plays_probability(laws, rows):
    """P(plays) of each row from its position's law (NaN for a position the law has no fit for)."""
    probability = np.full(len(rows), np.nan)
    for position, (cells, designations, coefficients) in laws.items():
        at = (rows.position == position).to_numpy()
        if at.any(): probability[at] = expit(who_plays_design(rows[at], cells, designations) @ coefficients)
    return probability
def week_participation(issue_season, issue_week):
    """P(plays) for every skill candidate of week N with its participation status: the law fit on every stamped season from the first season in facts through
    min(FROZEN_THRU, N's season - 1), applied to week N's inputs built from results through week N-1.  Returns (candidate rows, the fit summary)."""
    player_rows, team_games = load(), team_game(); last_fit_season = min(FROZEN_THRU, issue_season - 1); first_season = int(player_rows.season.min())
    laws, fit_rows = who_plays_fit(model_rows_of(who_plays_inputs(player_rows[player_rows.season <= last_fit_season], team_games, range(first_season, last_fit_season + 1))))
    known = player_rows[(player_rows.season < issue_season) | ((player_rows.season == issue_season) & (player_rows.week < issue_week))]
    season_rows = who_plays_inputs(known, team_games, [issue_season]); week_rows = season_rows[season_rows.week == issue_week].drop(columns="played").reset_index(drop=True)
    if issue_week not in ISSUE_WEEKS: week_rows["domain_reason"] = np.where(week_rows.domain_reason == "", f"week outside {ISSUE_WEEKS.start}-{ISSUE_WEEKS.stop - 1}", week_rows.domain_reason); week_rows["in_domain"] = False
    week_rows["probability_plays"] = np.where(week_rows.in_domain, who_plays_probability(laws, week_rows), np.nan)
    week_rows["participation_status"] = np.where(week_rows.in_domain, PARTICIPATION_QUALIFICATION, "NOT ISSUED - " + week_rows.domain_reason)
    week_rows["participation_cell"] = np.where(week_rows.in_domain, week_rows.cell, "")
    return week_rows, {"seasons": sorted(int(season) for season in set(fit_rows.season)), "rows": int(len(fit_rows)), "positions": sorted(laws)}
def participation_check():
    """python3 kit.py participation-check: the law's walk-forward (each season fit on the stamped seasons before it) beside T1's recorded walk-forward witness
    (proj/at_t_rows.csv.gz) on the rows both cover: per season, rows, mean P / played and log loss of each.  A reading; the verdict is the landing's (draws.chance_label)."""
    report = Report(); player_rows, team_games = load(), team_game(); rows = model_rows_of(who_plays_inputs(player_rows, team_games, sorted(set(player_rows.season[player_rows.season <= FROZEN_THRU]))))
    recorded_walk = plain(read_table(os.path.join(PROJ_DIR, "at_t_rows.csv.gz")))[["player_id", "season", "week", "probability_plays_transition_walkforward"]]
    report.say(f"kit.py participation-check (batch 71): the who-plays law's walk-forward vs T1's recorded walk-forward (at_t_rows, {len(recorded_walk)} rows)")
    for season in sorted(set(rows.season))[1:]:
        laws, fit_rows = who_plays_fit(rows[rows.season < season]); test_rows = rows[rows.season == season].copy(); test_rows["probability_plays"] = who_plays_probability(laws, test_rows)
        both = test_rows.merge(recorded_walk, on=["player_id", "season", "week"])
        if not len(both): report.say(f"   {season}: no recorded T1 row"); continue
        log_loss = lambda probability: float(np.mean(-(both.played * np.log(np.clip(probability, 1e-12, 1 - 1e-12)) + (1 - both.played) * np.log(np.clip(1 - probability, 1e-12, 1)))))
        report.say(f"   {season}: rows {len(both)}; played {both.played.mean():.3f}; law P {both.probability_plays.mean():.3f} log loss {log_loss(both.probability_plays):.4f}; T1 P {both.probability_plays_transition_walkforward.mean():.3f} log loss {log_loss(both.probability_plays_transition_walkforward):.4f}")
    report.write(os.path.join(PROJ_DIR, "participation_check_report.txt")); return 0
