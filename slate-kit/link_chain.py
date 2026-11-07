"""link_chain.py - THE ONE LINK CHAIN (Slate Kit module map: link chain; the ground-up rewrite of Oct 7 2026, rules R1 and R2).  The one producer of every center, rate and spread.
R1 ONE PRODUCER PER CENTER: every center is made by one link chain from facts at the cutoff - the team's volume at the league's drifting level, each player's share of
his team's draw, his rate per unit of his parent's draw.  No recorded forecast, frozen atlas, recorded rank, verdict or parameter file is an input: this module
reads facts' played rows through state.team_volume and nothing else.
R2 ONE FIT, REFIT WHOLE: every parameter is fit at the cutoff season s on seasons < s (fit_link_chain), each link's spread around the very center it is fit with.
Batch 62: the luck map's moments of every player link and the role law are measured on the issue domain - the rows the product applies them to (R5).
The shrink of a pregame rate is THE LUCK MAP's (empirical Bayes, method of moments, nothing chosen): mu the population rate, s2 the per-unit sampling variance,
tau2 the between-key variance of the true rate; w = tau2 / (tau2 + s2 / units).  Moments read every training game with earlier units; a spread is measured on
the issue domain state defines (an issue week, HISTORY_MINIMUM earlier games this season), the rows it is applied to.  Spreads are measured, never a chosen family (R5): a team volume draws its
center times a measured ratio; a conversion is beta-binomial on its parent's draw with the overdispersion measured around its own center; a player's share
of his team's count is beta-binomial by THE ROLE LAW (batch 61, fit_share: the luck map's shrunk share moved by his share of his team's previous game, 0 when
he did not play in it - who the team's active player is now - mean and concentration by maximum likelihood; at zero role weight it is the luck map's share); yards
are the parent's draw times the rate plus the square root of the draw times measured per-unit residuals.  Batch 63: a count beside a yards link under the same
parent (TDs) is drawn given that yards draw's luck (THE SIBLING LAW, fit_sibling) - a long gain is both yards and a score."""
import numpy as np, pandas as pd
from scipy.optimize import minimize_scalar, minimize
from scipy.stats import betabinom
from scipy.special import expit
from state import team_volume, box_zero, skill_columns, qb_columns, count_columns, RECEIVER_POSITIONS, ISSUE_WEEKS, HISTORY_MINIMUM
TEAM_KEY = "TEAM"
LINKS = {("F2 team attempts", TEAM_KEY): (None, "attempts", None, "level"), ("F2 team carries", TEAM_KEY): (None, "carries", None, "level"),
         ("F2 team targets", TEAM_KEY): (("F2 team attempts", TEAM_KEY), "targets", "attempts", "proportion"),
         **{cell: link for position in RECEIVER_POSITIONS for cell, link in (
             (("F5 targets", position), (("F2 team targets", TEAM_KEY), "targets", "team_targets", "share")),
             (("F5 carries", position), (("F2 team carries", TEAM_KEY), "carries", "team_carries", "share")),
             (("F5 receptions", position), (("F5 targets", position), "receptions", "targets", "proportion")),
             (("F5 receiving yards", position), (("F5 receptions", position), "receiving_yards", "receptions", "per unit")),
             (("F5 rushing yards", position), (("F5 carries", position), "rushing_yards", "carries", "per unit")),
             (("F5 receiving TDs", position), (("F5 receptions", position), "receiving_tds", "receptions", "proportion")),
             (("F5 rushing TDs", position), (("F5 carries", position), "rushing_tds", "carries", "proportion")))},
         ("Q1 attempts", "QB"): (("F2 team attempts", TEAM_KEY), "attempts", "team_attempts", "share"), ("Q2 completions", "QB"): (("Q1 attempts", "QB"), "completions", "attempts", "proportion"),
         ("Q3 passing yards", "QB"): (("Q2 completions", "QB"), "passing_yards", "completions", "per unit"), ("Q4 passing TDs", "QB"): (("Q2 completions", "QB"), "passing_tds", "completions", "proportion"),
         ("Q5 interceptions", "QB"): (("Q1 attempts", "QB"), "passing_interceptions", "attempts", "proportion"), ("QB carries", "QB"): (("F2 team carries", TEAM_KEY), "carries", "team_carries", "share"),
         ("QB rushing yards", "QB"): (("QB carries", "QB"), "rushing_yards", "carries", "per unit"), ("QB rushing TDs", "QB"): (("QB carries", "QB"), "rushing_tds", "carries", "proportion")}
def siblings_of(links):
    """THE SIBLING (batch 63, composition_read): a count link (proportion) whose parent also has a per-unit link - TDs under receptions / carries / completions,
    beside the yards drawn on the same touches - is drawn given that sibling's draw.  Read from the graph, never named."""
    pairs = {}
    for cell, (parent, numerator, denominator, kind) in links.items():
        if kind != "proportion" or parent is None: continue
        found = [other for other, link in links.items() if link[0] == parent and link[3] == "per unit"]
        if len(found) > 1: raise SystemExit(f"siblings_of {cell}: {len(found)} per-unit links under {parent} - the graph is ambiguous, refused")
        if found: pairs[cell] = found[0]
    return pairs
SIBLINGS = siblings_of(LINKS)
def link_order(links):
    """The links with every parent - and every sibling a link is drawn given - before them (the dependency order every fit and every draw walks)."""
    ordered = []
    def visit(cell):
        if cell in ordered: return
        if links[cell][0] is not None: visit(links[cell][0])
        if cell in SIBLINGS: visit(SIBLINGS[cell])
        ordered.append(cell)
    for cell in sorted(links): visit(cell)
    return tuple(ordered)
LINK_ORDER = link_order(LINKS)
PLAYER_COUNTS = sorted(set(skill_columns + qb_columns) - {"redzone_targets", "redzone_carries", "redzone_attempts"})
def link_chain_history(player_rows):
    """The facts the link chain reads, one row per game: every played player-game (key = player_id, the box score made whole by state.box_zero for its own group, his
    team's counts that game as team_*) and every team-game (key = team, position TEAM, the counts of state.team_volume - one producer)."""
    played = player_rows[player_rows.played == 1].drop_duplicates(["player_id", "season", "week"])
    played = pd.concat([box_zero(played[played.position.isin(RECEIVER_POSITIONS)], skill_columns, "link chain receivers"), box_zero(played[played.position == "QB"], qb_columns, "link chain QB")], ignore_index=True)
    volume = team_volume(player_rows)
    players = played[["player_id", "season", "week", "team", "position", "opponent", "snap_share"] + PLAYER_COUNTS].rename(columns={"player_id": "key"})   # batch 82: the opponent, for the team environment
    players = players.assign(**{column: players[column].fillna(0.0) for column in PLAYER_COUNTS}).merge(volume.rename(columns={column: f"team_{column}" for column in count_columns}), on=["season", "week", "team"], how="left")
    return pd.concat([players, volume.assign(key=volume.team, position=TEAM_KEY)], ignore_index=True)
def history_of(history, cell):
    """The rows a cell's pregame state reads: the team-games for a team cell, every played game of the players for a player cell (a player's rate follows him across labels and teams)."""
    return history[(history.position == TEAM_KEY) == (cell[1] == TEAM_KEY)]
def pregame(history, rows, numerator, denominator):
    """Each target row's season-to-date state from its key's earlier games this season (weeks < N): the numerator summed, the denominator summed (games, for a
    link without one) and the games.  rows: key, season, week.  Returns (x, n, games) in row order, 0 where the key has no earlier game."""
    games = history[["key", "season", "week", numerator]].assign(unit=history[denominator].to_numpy(float) if denominator else 1.0).sort_values(["key", "season", "week"])
    groups = games.groupby(["key", "season"]); games = games.assign(x=groups[numerator].cumsum(), n=groups["unit"].cumsum(), games=groups.cumcount() + 1)
    target = rows[["key", "season", "week"]].reset_index(drop=True).assign(order=np.arange(len(rows)))
    joined = pd.merge_asof(target.sort_values("week"), games[["key", "season", "week", "x", "n", "games"]].sort_values("week"), on="week", by=["key", "season"], allow_exact_matches=False, direction="backward").sort_values("order")
    return tuple(joined[column].fillna(0.0).to_numpy(float) for column in ("x", "n", "games"))
def issue_domain(rows, games):
    """The rows a spread is measured on: an issue week with HISTORY_MINIMUM earlier games this season (state's domain, one producer)."""
    return rows.week.isin(list(ISSUE_WEEKS)).to_numpy() & (games >= HISTORY_MINIMUM)
def reliability_shrink(mu, s2, tau2, rate, units):
    """THE LUCK MAP's pregame rate: mu + w (rate - mu), w = tau2 / (tau2 + s2 / units); a key with no earlier units carries mu."""
    with np.errstate(divide="ignore", invalid="ignore"): weight = np.where(units > 0, tau2 / (tau2 + s2 / units), 0.0); shrunk = mu + weight * (np.nan_to_num(rate) - mu)
    return np.where(units > 0, shrunk, mu)
def moments(x, n, rate_prior, units_prior, s2_of):
    """The luck map's moments: mu over every row with a unit this game - the rows the law serves, those without earlier units carry mu itself (batch 76);
    over those that also have earlier units: s2 (s2_of(mu, x, n, rate)), tau2 = the units-weighted variance of the prior rates minus the mean sampling
    variance s2 / units, at least 0."""
    served = n > 0; mu = float(x[served].sum() / n[served].sum())   # batch 76: the center of the rows it serves, not of the rows with a prior only
    used = (units_prior > 0) & served; x, n, rate, units = x[used], n[used], rate_prior[used], units_prior[used]
    s2 = s2_of(mu, x, n, rate); weights = units / units.sum()
    return mu, s2, max(0.0, float((weights * (rate - (weights * rate).sum()) ** 2).sum()) - float((weights * s2 / units).sum()))
def level_after(sums, counts, delta):
    """The league's discounted level after each week in order: every earlier team-game weighted delta^(weeks back), seasons chained."""
    total, games, after = 0.0, 0.0, []
    for week_sum, week_count in zip(sums, counts): total, games = delta * total + week_sum, delta * games + week_count; after.append(total / games)
    return np.array(after)
def league_levels(team_history, rows, count, delta):
    """The league's level before each target (season, week): level_after over every team-game of an earlier week.  Returns the levels in row order (NaN where none)."""
    weekly = team_history.groupby(["season", "week"])[count].agg(["sum", "count"]).reset_index().sort_values(["season", "week"])
    weekly = weekly.assign(level=level_after(weekly["sum"].to_numpy(float), weekly["count"].to_numpy(float), delta), ordinal=weekly.season * 100 + weekly.week)
    target = rows[["season", "week"]].reset_index(drop=True).assign(order=np.arange(len(rows)), ordinal=lambda frame: frame.season * 100 + frame.week)
    return pd.merge_asof(target.sort_values("ordinal"), weekly[["ordinal", "level"]], on="ordinal", allow_exact_matches=False, direction="backward").sort_values("order").level.to_numpy(float)
def root_center(team_history, fit, count, rows):
    """A team volume's pregame center: the league level + w (the team's rate this season - the level)."""
    x, n, games = pregame(team_history, rows, count, None); level = league_levels(team_history, rows, count, fit["delta"])
    with np.errstate(divide="ignore", invalid="ignore"): rate = x / games
    return reliability_shrink(level, fit["s2"], fit["tau2"], rate, games)
def fit_root(history, s, count):
    """A team volume on seasons < s: delta by least squares of each week's league mean on its pregame level (weighted by its team-games); the luck map's moments
    of the team rates around that level; the measured ratio outcome / center over every training team-game (the shape, R5).  Returns the fit."""
    teams = history[(history.position == TEAM_KEY) & (history.season < s)]; weekly = teams.groupby(["season", "week"])[count].agg(["sum", "count"]).reset_index().sort_values(["season", "week"])
    sums, counts = weekly["sum"].to_numpy(float), weekly["count"].to_numpy(float); pregame_level = lambda delta: np.concatenate([[np.nan], level_after(sums, counts, delta)[:-1]])
    delta = float(minimize_scalar(lambda delta: float(np.nansum(counts * (sums / counts - pregame_level(delta)) ** 2)), bounds=(0.0, 1.0), method="bounded").x)
    x, n, games = pregame(teams, teams, count, None); level = league_levels(teams, teams, count, delta); y = teams[count].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"): rate = x / games
    used = (games > 0) & np.isfinite(level); s2 = float(np.mean((y[used] - rate[used]) ** 2 / (1 + 1 / games[used]))); deviation = (rate - level)[used]; weights = games[used] / games[used].sum()
    tau2 = max(0.0, float((weights * (deviation - (weights * deviation).sum()) ** 2).sum()) - float((weights * s2 / games[used]).sum()))
    fit = dict(delta=delta, s2=s2, tau2=tau2); center = root_center(teams, fit, count, teams); measured = issue_domain(teams, games) & np.isfinite(center) & (center > 0)
    return {**fit, "ratio": y[measured] / center[measured], "rows": int(measured.sum())}
def fit_proportion(history, s, cell):
    """A share or conversion on seasons < s (the cell's own position): the luck map's mu, s2 = mu (1 - mu), tau2; then around each training row's own shrunk
    rate p the measured overdispersion rho = sum((x - n p)^2 - n p (1 - p)) / sum(n (n - 1) p (1 - p)), at least 0 (binomial at 0).  Returns the fit."""
    parent, numerator, denominator, kind = LINKS[cell]; train = history[(history.season < s) & (history.position == cell[1])]
    x_prior, n_prior, games = pregame(train, train, numerator, denominator); x, n = train[numerator].to_numpy(float), train[denominator].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"): rate_prior = x_prior / n_prior
    domain = issue_domain(train, games); mu, s2, tau2 = moments(x[domain], n[domain], rate_prior[domain], n_prior[domain], lambda mu, *unused: mu * (1 - mu)); p = reliability_shrink(mu, s2, tau2, rate_prior, n_prior)
    measured = issue_domain(train, games) & (n > 0); x, n, p = x[measured], n[measured], p[measured]; spread = float(np.sum(n * (n - 1) * p * (1 - p)))
    return dict(mu=mu, s2=s2, tau2=tau2, rho=max(0.0, float(np.sum((x - n * p) ** 2 - n * p * (1 - p))) / spread) if spread > 0 else 0.0, rows=int(measured.sum()))
def fit_per_unit(history, s, cell):
    """A yards rate on seasons < s (the cell's own position): the luck map's mu, s2 = mean((x - n rate)^2 / n), tau2; then around each training row's own shrunk
    rate r the measured per-unit residuals (x - n r) / sqrt(n) over every game with a unit (the shape, R5).  Returns the fit."""
    parent, numerator, denominator, kind = LINKS[cell]; train = history[(history.season < s) & (history.position == cell[1])]
    x_prior, n_prior, games = pregame(train, train, numerator, denominator); x, n = train[numerator].to_numpy(float), train[denominator].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"): rate_prior = x_prior / n_prior
    domain = issue_domain(train, games); mu, s2, tau2 = moments(x[domain], n[domain], rate_prior[domain], n_prior[domain], lambda mu, x, n, rate: float(np.mean((x - n * rate) ** 2 / n))); r = reliability_shrink(mu, s2, tau2, rate_prior, n_prior)
    measured = issue_domain(train, games) & (n > 0)
    return dict(mu=mu, s2=s2, tau2=tau2, residuals=(x[measured] - n[measured] * r[measured]) / np.sqrt(n[measured]), rows=int(measured.sum()))
def previous_share(history, rows, cell):
    """Each target row's share of his team's count in HIS TEAM'S previous game this season (rows: key, season, week, team): his count over the team's count in
    the latest team-game before week N, 0 when he did not play in it (the team's current role, pregame); NaN when his team has no earlier game this season."""
    parent, numerator, denominator, kind = LINKS[cell]
    team_weeks = history[history.position == TEAM_KEY][["key", "season", "week"]].rename(columns={"key": "team", "week": "previous_week"}).drop_duplicates().sort_values("previous_week")
    target = rows[["key", "season", "week", "team"]].reset_index(drop=True).assign(order=np.arange(len(rows)))
    joined = pd.merge_asof(target.sort_values("week"), team_weeks, left_on="week", right_on="previous_week", by=["team", "season"], allow_exact_matches=False, direction="backward")
    games = history[history.position == cell[1]][["key", "season", "week", numerator, denominator]].rename(columns={"week": "previous_week"})
    joined = joined.merge(games, on=["key", "season", "previous_week"], how="left").sort_values("order")
    with np.errstate(divide="ignore", invalid="ignore"): share = (joined[numerator] / joined[denominator].where(joined[denominator] > 0)).fillna(0.0).to_numpy(float)
    return np.where(joined.previous_week.isna().to_numpy(), np.nan, share)
def vacancy(history, cell, rows, active):
    """THE NEXT-UP VACANCY (batch 77; active_share_read_v1 / v2, absorption_read_v1, vacancy_next_up_read_v1): for each target row (key, team, season, week)
    the share vacated (out) or reclaimed (back) by the teammates he is next up to, measured against his own earlier games.  The members of a team-week: the
    cell's position's players with an earlier played game for the team this season, each with his season-to-date share before week N.  A member is active
    when he is in active[(season, week, team)] - the project owner's final active list (facts.active_keys), for training and issue rows alike (batch 78).  Teammate A's next up: the active members of his position with the largest share below his (ties share it).  A gives them rate_A x (p(A, B) -
    [A active]), p(A, B) = the fraction of B's earlier played games this season in which A played: out when positive, back when negative.  A routine absence
    (A out in all of B's earlier games) gives nothing - it is already in B's rate.  Returns (out, back) in row order, share units."""
    numerator, denominator = LINKS[cell][1], LINKS[cell][2]; rows = rows.reset_index(drop=True); keys = rows.key.to_numpy(); out, back = np.zeros(len(rows)), np.zeros(len(rows))
    games = history[(history.position == cell[1]) & history.season.isin(rows.season.unique())][["key", "team", "season", "week", numerator, denominator]].sort_values("week", kind="stable")
    ledgers = {(team, season): {key: (g.week.to_numpy(), g[numerator].cumsum().to_numpy(float), g[denominator].cumsum().to_numpy(float)) for key, g in team_rows.groupby("key")} for (team, season), team_rows in games.groupby(["team", "season"])}
    for (team, season, week), positions in rows.groupby(["team", "season", "week"]).indices.items():
        members = {}
        for key, (weeks, x, n) in ledgers.get((team, season), {}).items():
            last = int(np.searchsorted(weeks, week)) - 1
            if last >= 0 and n[last] > 0: members[key] = (x[last] / n[last], set(weeks[:last + 1].tolist()))
        listed = active.get((int(season), int(week), team), frozenset()); on = {key for key in members if key in listed}
        given_out, given_back = {}, {}
        for absent, (rate, absent_weeks) in members.items():
            below = [members[key][0] for key in on if key != absent and members[key][0] < rate]
            if not below: continue
            top = max(below); takers = [key for key in on if key != absent and members[key][0] == top]
            for taker in takers:
                given = rate * (len(absent_weeks & members[taker][1]) / len(members[taker][1]) - float(absent in on)) / len(takers)
                (given_out if given > 0 else given_back)[taker] = (given_out if given > 0 else given_back).get(taker, 0.0) + given
        for position_index in positions: out[position_index], back[position_index] = given_out.get(keys[position_index], 0.0), given_back.get(keys[position_index], 0.0)
    return out, back
def role_law(theta, shrunk, previous, vacated_out, vacated_back, edge, participation):
    """THE ROLE LAW (batch 61; nested_law_read): logit(mean) = logit(shrunk share) + t0 + t1 (previous share - shrunk share) + t5 vacated out + t6 vacated back
    (batch 77, link_chain.vacancy); log concentration = t2 + t3 previous + t4 shrunk.  t0 = t1 = t5 = t6 = 0 is the luck map's share.  Returns (mean, 1 - mean,
    concentration), the two sides computed apart so neither rounds to 0."""
    z = np.log(shrunk / (1 - shrunk)) + theta[0] + theta[1] * (previous - shrunk) + theta[5] * vacated_out + theta[6] * vacated_back + theta[7] * edge + participation @ theta[8:11]   # batch 81: work follows efficiency   # batch 83: participation
    return 1 / (1 + np.exp(-z)), 1 / (1 + np.exp(z)), np.exp(theta[2] + theta[3] * previous + theta[4] * shrunk)
ROLE_TERMS_HELD = {("Q1 attempts", "QB"): (8,), ("F5 targets", "WR"): (1,), ("F5 targets", "TE"): (1,)}   # batch 85 (masked_gate_read_v2, the quality gate's ruler): t8 in QB attempts BETTER held at 0 (F8 QB p .028, DK QB p .020); t1 in WR / TE targets carries nothing (all INSUFFICIENT_EVIDENCE)
def fit_share(history, s, cell, active, fits):
    """A player's share of his team's count on seasons < s (the cell's own position): the luck map's moments of the season-to-date share (mu, s2 = mu (1 - mu),
    tau2), then THE ROLE LAW by maximum likelihood (beta-binomial of his count in his team's count) - both measured on the training games of the issue domain
    (batch 62: every estimate on the rows it is applied to, R5).
    Returns the fit; a fit that does not converge is refused by name."""
    parent, numerator, denominator, kind = LINKS[cell]; train = history[(history.season < s) & (history.position == cell[1])]
    x_prior, n_prior, games = pregame(train, train, numerator, denominator); x, n = train[numerator].to_numpy(float), train[denominator].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"): rate_prior = x_prior / n_prior
    domain = issue_domain(train, games); mu, s2, tau2 = moments(x[domain], n[domain], rate_prior[domain], n_prior[domain], lambda mu, *unused: mu * (1 - mu)); shrunk = reliability_shrink(mu, s2, tau2, rate_prior, n_prior); previous = previous_share(history, train, cell)
    edge = efficiency_edge(history[history.season < s], fits, cell, train, active)   # batch 81
    played_part = participation(history[history.season < s], train, cell[1], active)   # batch 83: how much of the game he is about to play
    vacated_out, vacated_back = vacancy(history[history.season < s], cell, train, active)   # batch 78: the same final active list as the issue
    used = np.isfinite(previous) & np.isfinite(edge) & (n > 0) & domain; x, n, shrunk, previous, vacated_out, vacated_back, edge, played_part = x[used], n[used], shrunk[used], previous[used], vacated_out[used], vacated_back[used], edge[used], played_part[used]
    def loss(theta):
        mean, other, concentration = role_law(theta, shrunk, previous, vacated_out, vacated_back, edge, played_part); return -float(betabinom.logpmf(x, n, mean * concentration, other * concentration).sum())
    result = minimize(loss, np.array([0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), method="L-BFGS-B", bounds=[(0.0, 0.0) if index in ROLE_TERMS_HELD.get(cell, ()) else (None, None) for index in range(11)])   # batch 83: momentum, vacated, returning on the field   # batch 85: terms the quality gate holds at 0
    if not result.success: raise SystemExit(f"fit_share {cell[0]} {cell[1]}: seasons < {s} did not converge ({result.message}) - refused")
    return dict(mu=mu, s2=s2, tau2=tau2, theta=result.x, rows=int(used.sum()))
def sibling_luck_of(sibling_fit, values, trials, rate):
    """THE SIBLING'S LUCK, one producer for the fit and the draw (batch 63b): (yards - n x rate) / sqrt(n), in units of the sibling's own measured per-unit
    residual sd - dimensionless, so its weight means the same for every pair; 0 where n = 0."""
    trials = np.asarray(trials, float); scale = float(np.std(sibling_fit["residuals"]))
    return np.where(trials > 0, (np.asarray(values, float) - trials * rate) / np.sqrt(np.where(trials > 0, trials, 1.0)) / scale, 0.0)
def sibling_luck(rows, fits, cell):
    """Each training row's sibling luck that game (rows of one position), at the sibling's own shrunk pregame rate."""
    sibling = SIBLINGS[cell]; parent, numerator, denominator, kind = LINKS[sibling]; fit = fits[sibling]
    x_prior, n_prior, games = pregame(rows, rows, numerator, denominator)
    with np.errstate(divide="ignore", invalid="ignore"): rate = reliability_shrink(fit["mu"], fit["s2"], fit["tau2"], x_prior / n_prior, n_prior)
    return sibling_luck_of(fit, rows[numerator].to_numpy(float), rows[denominator].to_numpy(float), rate)
def sibling_logit(theta, rate, luck):
    """THE SIBLING LAW's center (batch 63): logit(mean) = logit(rate) + t0 + t1 luck.  t0 = t1 = 0 is the unconditioned rate."""
    return np.log(rate / (1 - rate)) + theta[0] + theta[1] * luck
def sibling_law(theta, rate, luck): return expit(sibling_logit(theta, rate, luck))
def fit_sibling(history, s, cell, fits, active):
    """A count with a sibling on seasons < s: the luck map's moments on the issue domain (fit_proportion's state), then THE SIBLING LAW by maximum likelihood
    center (binomial maximum likelihood of the count in its trials given the sibling's luck that game) on the issue domain's training games, then its
    overdispersion measured around that center by moments (R5, as fit_proportion).  Refused by name when it does not converge."""
    parent, numerator, denominator, kind = LINKS[cell]; train = history[(history.season < s) & (history.position == cell[1])]
    x_prior, n_prior, games = pregame(train, train, numerator, denominator); x, n = train[numerator].to_numpy(float), train[denominator].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"): rate_prior = x_prior / n_prior
    domain = issue_domain(train, games); mu, s2, tau2 = moments(x[domain], n[domain], rate_prior[domain], n_prior[domain], lambda mu, *unused: mu * (1 - mu)); rate = reliability_shrink(mu, s2, tau2, rate_prior, n_prior)
    env = team_environment(history[history.season < s], fits, train, active); env_mu, env_sd = np.nanmean(env, axis=0), np.nanstd(env, axis=0); env = (env - env_mu) / env_sd   # batch 82
    luck = sibling_luck(train, fits, cell); used = domain & (n > 0) & np.isfinite(env).all(axis=1); x, n, rate, luck, env = x[used], n[used], rate[used], luck[used], env[used]
    def loss(theta):   # binomial log-likelihood in log-expit form: a logistic regression with offset - convex, one optimum
        z = sibling_logit(theta, rate, luck) + env @ theta[2:]; return float(np.sum(x * np.logaddexp(0.0, -z) + (n - x) * np.logaddexp(0.0, z)))
    result = minimize(loss, np.zeros(5), method="L-BFGS-B")   # batch 82: the sibling law's two and the environment's three
    if not result.success: raise SystemExit(f"fit_sibling {cell[0]} {cell[1]}: seasons < {s} did not converge ({result.message}) - refused")
    p = expit(sibling_logit(result.x, rate, luck) + env @ result.x[2:]); spread = float(np.sum(n * (n - 1) * p * (1 - p)))   # the overdispersion measured around the law's own center (fit_proportion's moment)
    rho = max(0.0, float(np.sum((x - n * p) ** 2 - n * p * (1 - p))) / spread) if spread > 0 else 0.0
    return dict(mu=mu, s2=s2, tau2=tau2, theta=result.x, rho=rho, sibling=SIBLINGS[cell], rows=int(used.sum()), env_mu=env_mu, env_sd=env_sd)
def career_rate(history, cell, rows):
    """Batch 79: each target row's own career rate on the cell's link - his numerator / denominator over every season of history before the row's season
    (NaN where he has none).  rows: key, season."""
    numerator, denominator = LINKS[cell][1], LINKS[cell][2]
    seasons = history[history.position == cell[1]].groupby(["key", "season"])[[numerator, denominator]].sum().reset_index().sort_values(["key", "season"])
    seasons[["career_x", "career_n"]] = seasons.groupby("key")[[numerator, denominator]].cumsum().to_numpy(float)
    target = rows[["key", "season"]].reset_index(drop=True).assign(order=np.arange(len(rows)))
    joined = pd.merge_asof(target.sort_values("season"), seasons[["key", "season", "career_x", "career_n"]].sort_values("season"), on="season", by="key", allow_exact_matches=False, direction="backward").sort_values("order")
    with np.errstate(divide="ignore", invalid="ignore"): return (joined.career_x / joined.career_n).to_numpy(float)
def efficiency_rate(history, cell, rows, shrunk, rate, n, weights, active):
    """Batch 79: the luck map's rate moved toward the player's career rate and this season's raw rate by the fitted weights (fit_efficiency); a term with no
    career / no earlier game this season is 0."""
    career = career_rate(history, cell, rows)
    with np.errstate(invalid="ignore"): return shrunk + weights[0] * np.where(np.isfinite(career), career - shrunk, 0.0) + weights[1] * np.where(n > 0, rate - shrunk, 0.0) + (weights[2] * cast_vacancy(history, cell, rows, active) if len(weights) > 2 else 0.0)
def fit_efficiency(history, s, cell, fit, active):
    """Batch 79 (efficiency_prior_read_v2, career_prior_read_v1): how far a player's rate moves from the luck map's toward his career rate and this season's
    raw rate - weights >= 0 by nonnegative least squares of the per-unit residual (count / units - shrunk rate), weighted by units, on the issue domain's
    training games of seasons < s.  Returns (w_career, w_season)."""
    from scipy.optimize import nnls
    parent, numerator, denominator, kind = LINKS[cell]; train = history[(history.season < s) & (history.position == cell[1])]
    x_prior, n_prior, games = pregame(train, train, numerator, denominator); x, n = train[numerator].to_numpy(float), train[denominator].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"): rate_prior = x_prior / n_prior
    shrunk = reliability_shrink(fit["mu"], fit["s2"], fit["tau2"], rate_prior, n_prior); career = career_rate(history[history.season < s], cell, train)
    used = issue_domain(train, games) & (n > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        x_career = np.where(np.isfinite(career), career - shrunk, 0.0); x_season = np.where(n_prior > 0, rate_prior - shrunk, 0.0); y = x / n - shrunk
    weight = np.sqrt(n[used])
    if cell in CAST_CELLS:   # batch 80: his usual receivers' vacated share; its sign is the data's
        from scipy.optimize import lsq_linear
        x_cast = cast_vacancy(history[history.season < s], cell, train, active)
        return lsq_linear(np.column_stack([x_career[used], x_season[used], x_cast[used]]) * weight[:, None], y[used] * weight, bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf])).x
    weights, unused = nnls(np.column_stack([x_career[used], x_season[used]]) * weight[:, None], y[used] * weight)
    return weights
CAST_CELLS = (("Q2 completions", "QB"), ("Q3 passing yards", "QB"), ("Q4 passing TDs", "QB"))
def cast_vacancy(history, cell, rows, active):
    """Batch 80 (qb_cast_read_v1): for each QB row (key, team, season, week) the target share his usual receivers leave vacant, measured against his own
    earlier games as link_chain.vacancy measures a teammate: receiver A (RB / WR / TE with an earlier played game for the team this season) holds share_A = his
    targets / the team's receivers' targets over weeks < N and gives share_A x (p(A, QB) - [A active]), p = the fraction of the QB's earlier played games this
    season in which A played; active = the project owner's final active list.  A routine absence gives nothing; a return gives back.  Returns the sum in row order."""
    rows = rows.reset_index(drop=True); out = np.zeros(len(rows)); seasons = rows.season.unique()
    receivers = history[history.position.isin(["RB", "WR", "TE"]) & history.season.isin(seasons)][["key", "team", "season", "week", "targets"]]
    passers = history[(history.position == "QB") & history.season.isin(seasons)][["key", "team", "season", "week"]]
    receivers_of = {k: g for k, g in receivers.groupby(["team", "season"])}; weeks_of = {k: set(g.week) for k, g in passers.groupby(["key", "team", "season"])}
    for i, (key, team, season, week) in enumerate(rows[["key", "team", "season", "week"]].itertuples(index=False, name=None)):
        g = receivers_of.get((team, season)); mine = {w for w in weeks_of.get((key, team, season), set()) if w < week}
        if g is None or not mine: continue
        earlier = g[g.week < week]; total = float(earlier.targets.sum())
        if total <= 0: continue
        listed = active.get((int(season), int(week), team), frozenset())
        for receiver, h in earlier.groupby("key"): out[i] += float(h.targets.sum()) / total * (len(set(h.week) & mine) / len(mine) - float(receiver in listed))
    return out
def yards_path(cell):
    """Batch 81: the cells from a share cell down to its yards link - each step the child (LINKS parent = the step) that is not a sibling count, until a
    per-unit link; the path a unit of this share becomes yards along.  Derived from LINKS."""
    path, step = [], cell
    while True:
        children = [c for c, spec in LINKS.items() if spec[0] == step and c not in SIBLINGS and any(d == c or LINKS[d][0] == c for d in LINKS if d not in SIBLINGS)]
        reach = [c for c in children if LINKS[c][3] == "per unit" or any(LINKS[d][0] == c and LINKS[d][3] == "per unit" for d in LINKS)]
        if not reach: return path
        step = reach[0]; path.append(step)
        if LINKS[step][3] == "per unit": return path
def efficiency_edge(history, fits, cell, rows, active):
    """Batch 81 (share_eff_read_v1 / v3): per target row (key, team, season, week), the product's own yards per unit of this share (the rates of the
    yards_path cells multiplied - the conversion law's estimate, one producer) minus the position's league yards per unit this season through week N-1."""
    path = yards_path(cell); rows = rows.reset_index(drop=True)
    own = np.prod([link_rates(history, fits, step, rows, active)[0] for step in path], axis=0)
    numerator, denominator = LINKS[path[-1]][1], LINKS[cell][1]
    weekly = history[(history.position == cell[1]) & history.season.isin(rows.season.unique())].groupby(["season", "week"])[[numerator, denominator]].sum().groupby(level=0).cumsum().reset_index()
    target = rows[["season", "week"]].assign(order=np.arange(len(rows)))
    joined = pd.merge_asof(target.sort_values("week"), weekly.sort_values("week"), on="week", by="season", allow_exact_matches=False, direction="backward").sort_values("order")
    with np.errstate(divide="ignore", invalid="ignore"): return own - (joined[numerator] / joined[denominator]).to_numpy(float)
def team_environment(history, fits, rows, active):
    """Batch 82 (team_td_revision_read_v2): per target row (key, team, season, week, opponent) - its team's TD margin going in (the team's receiving + rushing
    TDs minus its opponents' in the same games, mean over this season's earlier games), the conversion law's efficiency edge of its usual starter (the QB
    with the most attempts this season before week N; efficiency_edge on Q1 attempts), its opponent's TD margin going in.  Returns an (n, 3) array."""
    rows = rows.reset_index(drop=True); players = history[history.position != TEAM_KEY]
    games = players.assign(tds=players.receiving_tds + players.rushing_tds).groupby(["team", "season", "week"]).agg(tds=("tds", "sum"), opponent=("opponent", "first")).reset_index()
    games = games.merge(games[["team", "season", "week", "tds"]].rename(columns={"team": "opponent", "tds": "against"}), on=["opponent", "season", "week"], how="left")
    games = games.assign(margin=games.tds - games.against).sort_values("week")
    games = games.assign(total=games.groupby(["team", "season"]).margin.cumsum(), count=games.groupby(["team", "season"]).margin.cumcount() + 1)
    def going_in(team_column):
        target = rows[[team_column, "season", "week"]].rename(columns={team_column: "team"}).assign(order=np.arange(len(rows)))
        joined = pd.merge_asof(target.sort_values("week"), games[["team", "season", "week", "total", "count"]].sort_values("week"), on="week", by=["team", "season"], allow_exact_matches=False, direction="backward").sort_values("order")
        return (joined.total / joined["count"]).to_numpy(float)
    passers = history[history.position == "QB"].sort_values("week")
    passers = passers.assign(cum=passers.groupby(["key", "team", "season"]).attempts.cumsum())
    weeks = rows[["team", "season", "week"]].drop_duplicates().assign(order=lambda f: np.arange(len(f)))
    latest = passers[["key", "team", "season", "week", "cum"]]
    usual = weeks.merge(latest, on=["team", "season"], suffixes=("", "_game")).query("week_game < week").sort_values("cum").drop_duplicates(["team", "season", "week"], keep="last")[["team", "season", "week", "key"]]
    edge = usual.assign(value=efficiency_edge(history, fits, ("Q1 attempts", "QB"), usual[["key", "team", "season", "week"]], active))
    own_edge = rows[["team", "season", "week"]].merge(edge[["team", "season", "week", "value"]], on=["team", "season", "week"], how="left").value.to_numpy(float)
    return np.column_stack([going_in("team"), own_edge, going_in("opponent")])
def participation(history, rows, position, active):
    """Batch 83 (snap_predict_read_v1, participation_premises_read_v1): per target row (key, team, season, week) of a share cell at this position - (1) his
    last game's snap share this season minus his season-to-date mean (momentum), (2) the season-to-date snap share of teammates at his position who stood
    above him and are not on this week's final active list (vacated), (3) 1 when his team played a game this season before week N that he did not
    (returning).  Only games before week N are read.  A player with no earlier game this season carries no momentum: no change is measured.  Returns (n, 3)."""
    target = rows.reset_index(drop=True)[["key", "team", "season", "week"]].assign(order=lambda frame: np.arange(len(frame)))
    games = history[(history.position == position) & history.season.isin(target.season.unique())][["key", "team", "season", "week", "snap_share"]].rename(columns={"week": "game_week"}).sort_values("game_week")
    games = games.assign(through=games.groupby(["key", "season"]).snap_share.transform(lambda shares: shares.expanding().mean()))
    own = pd.merge_asof(target.sort_values("week"), games[["key", "season", "game_week", "through", "snap_share"]], left_on="week", right_on="game_week", by=["key", "season"], allow_exact_matches=False, direction="backward").sort_values("order")
    pre = np.nan_to_num(own.through.to_numpy(float)); momentum = np.nan_to_num(own.snap_share.to_numpy(float) - own.through.to_numpy(float))
    roster = games[["key", "team", "season"]].drop_duplicates().rename(columns={"key": "mate"})
    pairs = target.merge(roster, on=["team", "season"]).query("mate != key").sort_values("week")
    pairs = pd.merge_asof(pairs, games[["key", "season", "game_week", "through"]].rename(columns={"key": "mate"}), left_on="week", right_on="game_week", by=["mate", "season"], allow_exact_matches=False, direction="backward")
    pairs = pairs[(pairs.through.to_numpy(float) > pre[pairs.order.to_numpy()]) & ~np.array([mate in active.get((season, week, team), frozenset()) for mate, season, week, team in zip(pairs.mate, pairs.season, pairs.week, pairs.team)], dtype=bool)]
    vacated = pairs.groupby("order").through.sum().reindex(target.order, fill_value=0.0).to_numpy(float)
    team_games = history[(history.position == TEAM_KEY) & history.season.isin(target.season.unique())][["team", "season", "week"]].rename(columns={"week": "game_week"}).sort_values("game_week")
    previous = pd.merge_asof(target.sort_values("week"), team_games, left_on="week", right_on="game_week", by=["team", "season"], allow_exact_matches=False, direction="backward").sort_values("order")
    played = set(zip(games.key, games.season, games.game_week))
    returning = np.array([float(week == week and (key, season, week) not in played) for key, season, week in zip(previous.key, previous.season, previous.game_week)])
    return np.column_stack([momentum, vacated, returning])
def fit_link_chain(history, s, active):
    """Every link fit at the cutoff s on seasons < s, in dependency order (R2) - the only parameters the product draws from.  A count with a sibling is fit given it."""
    fits = {}
    for cell in [c for c in LINK_ORDER if LINKS[c][3] != "share" and c not in SIBLINGS] + [c for c in LINK_ORDER if c in SIBLINGS] + [c for c in LINK_ORDER if LINKS[c][3] == "share"]:   # batch 82: TD links read the QB fits   # batch 81: a share's edge reads the conversion fits
        kind = LINKS[cell][3]
        fits[cell] = (fit_root(history, s, LINKS[cell][1]) if kind == "level" else fit_share(history, s, cell, active, fits) if kind == "share" else fit_sibling(history, s, cell, fits, active) if cell in SIBLINGS
                      else fit_proportion(history, s, cell) if kind == "proportion" else fit_per_unit(history, s, cell))
        if kind not in ("level", "share"): fits[cell]["efficiency"] = fit_efficiency(history, s, cell, fits[cell], active)   # batch 79: every conversion / per-unit / sibling link
    return fits
def link_rates(history, fits, cell, rows, active):
    """A cell's pregame law for target rows (key, season, week, team): a team volume its center; a share its role-law mean and concentration; a conversion its
    shrunk rate and the concentration of its measured overdispersion; a yards link its shrunk rate per parent unit.  Returns (rates, their complements - a share's from the role law, computed apart (batch 78) - earlier units,
    concentrations) in row order (concentration NaN where the link has none)."""
    parent, numerator, denominator, kind = LINKS[cell]; cell_history = history_of(history, cell); season_history = cell_history[cell_history.season.isin(rows.season.unique())]   # a pregame state is season-to-date
    if kind == "level": x, n, games = pregame(season_history, rows, numerator, None); return root_center(cell_history, fits[cell], numerator, rows), np.full(len(rows), np.nan), games, np.full(len(rows), np.nan)
    x, n, games = pregame(season_history, rows, numerator, denominator)
    with np.errstate(divide="ignore", invalid="ignore"): rate = x / n
    fit = fits[cell]; shrunk = reliability_shrink(fit["mu"], fit["s2"], fit["tau2"], rate, n)
    if kind == "share": mean, other, concentration = role_law(fit["theta"], shrunk, previous_share(history, rows, cell), *vacancy(history, cell, rows, active), efficiency_edge(history, fits, cell, rows, active), participation(history, rows, cell[1], active)); return mean, other, n, concentration   # batch 83
    shrunk = efficiency_rate(history, cell, rows, shrunk, rate, n, fit["efficiency"], active)   # batch 79: his career and this season's own rate   # batch 77: active = the final active list
    if cell in SIBLINGS: shrunk = expit(np.log(shrunk / (1 - shrunk)) + ((team_environment(history, fits, rows, active) - fit["env_mu"]) / fit["env_sd"]) @ fit["theta"][2:])   # batch 82: the team scoring environment
    if cell in SIBLINGS: return shrunk, 1 - shrunk, n, np.full(len(rows), (1 - fit["rho"]) / fit["rho"] if fit["rho"] > 0 else np.inf)
    if kind == "proportion": return shrunk, 1 - shrunk, n, np.full(len(rows), (1 - fit["rho"]) / fit["rho"] if fit["rho"] > 0 else np.inf)
    return shrunk, np.full(len(rows), np.nan), n, np.full(len(rows), np.nan)
