"""draws.py - THE PRODUCT (Slate Kit module map: draws; the ground-up rewrite of Oct 7 2026, rules R1-R5).  One sampler for history and issue: every link of
THE ONE LINK CHAIN (link_chain.py) draws DRAW_COUNT values for each member of a slate from its own keyed substream (term|position|season|week|key|link chain), its parent's draw
in hand - a team's volume, each player's share of it, his conversions and yards of his own draws - so draw j of every row is one world: the identities of the
box score hold by construction (a catch needs a target, yards need a touch) and teammates share their team's volume.  F5 TDs is the sum of its two parts; F8
is dk's transform of the player's own draws.  DST: OLS on state's pregame DST inputs fit on seasons < s, measured residuals.
Batch 63: a count beside a yards link under the same parent draws given that yards draw (THE SIBLING LAW, link_chain.fit_sibling).
Batch 61: a player's share of his team's count draws by THE ROLE LAW (link_chain.fit_share); the share link's pooled overdispersion is deleted.
R3 ONE PRODUCT, ONE JUDGMENT (replay): the product is replayed whole at every cutoff and judged once, against the previous product's graded rows named by the
caller, on F8 at every position - a rise beyond chance refuses the product.  No law here reads a verdict, a judgment, a recorded forecast or a parameter file.
R4: the judgment is trinary against the season chance test, plus UNCHANGED, and is written before any reading is printed.
Engine root (2026-11-05, acceptance-criteria/engine-to-kit-handoff.md section 6): with SLATE_ROOT_SOURCE=engine the two root cells (F2 team attempts, F2 team
carries) are taken from an engine draw file (SLATE_ROOT_FILE, a .npz with its manifest beside it) instead of the link chain's own level draw: kit column j takes
engine source draw j mod K, both teams of a game from the same engine draw; the root center is the engine draws' mean; a missing file, a manifest hash that
differs from the file, a team with a game but no draws, or a declared draw count that differs from the arrays refuse the issue by name - never a fallback to the
kit's own root draw.  With SLATE_ROOT_SOURCE unset or 'kit' nothing here differs from before.
One quarterback per world (2026-11-10, acceptance-criteria/one-game-one-reality.md): column j of a team is one world in which exactly one of its quarterback
candidates starts (or a starter not on the card), drawn from P(starts) on the team's own substream; the frozen draws carry it as starts_keys / starts, and the
card names each quarterback line's world.  His lines stay 'given he plays'; what changes is that two of them are never one game."""
import os, glob, json, hashlib, numpy as np, pandas as pd
from scipy.stats import t as student_t
from ingest import PROJ_DIR, FROZEN_THRU, Report, sha
from facts import load, team_game, read_table, active_keys
from evaluate import crps, rank, atlas_cells, share_band, ALPHA_FAMILY
from state import issue_frames, dst_frame, DST_INPUTS, ISSUE_WEEKS, HISTORY_MINIMUM, RECEIVER_POSITIONS
from participation import week_participation, who_plays_inputs, who_plays_fit, who_plays_probability, model_rows_of
from dk import skill_dk, qb_dk, dnp_zero, F8_TERM, DK_TERM, DST_TERM, BONUS_YARDS
from link_chain import link_chain_history, fit_link_chain, link_rates, sibling_law, sibling_luck_of, LINKS, LINK_ORDER, SIBLINGS, TEAM_KEY
DRAW_COUNT = 2000
ROOT_SOURCE = os.environ.get("SLATE_ROOT_SOURCE", "kit")   # 'kit': the link chain's own root draw; 'engine': the root cells from an engine draw file (handoff section 6)
ROOT_FILE = os.environ.get("SLATE_ROOT_FILE")              # engine mode: the .npz; its manifest is <path without .npz>.manifest.json
if ROOT_SOURCE not in ("kit", "engine"): raise SystemExit(f"SLATE_ROOT_SOURCE={ROOT_SOURCE!r} is not a root source: unset, kit or engine - refused; nothing issued")
ROOT_TERMS = {"F2 team attempts": "attempts", "F2 team carries": "carries"}
ENGINE_ROOT = None
QUANTILE_LEVELS = [0.10, 0.25, 0.50, 0.75, 0.90]; QUANTILE_NAMES = ["quantile_10", "quantile_25", "quantile_50", "quantile_75", "quantile_90"]
LINK_CHAIN_STATE = "link chain"
FAMILIES = {"level": "team volume: the league level shrunk by reliability x a measured ratio", "share": "beta-binomial on the team draw by the role law (mean and concentration by maximum likelihood)",
            "proportion": "beta-binomial on the parent draw, overdispersion measured around its center", "sibling": "beta-binomial on the parent draw given the sibling's yards luck (the sibling law)",
            "per unit": "the parent draw x the shrunk rate + sqrt(draw) x measured per-unit residuals"}
ENGINE_FAMILY = "team volume: the engine's generated games (handoff section 6), both teams of a game in one world"
TD_PARTS = {("F5 TDs", position): (("F5 receiving TDs", position), ("F5 rushing TDs", position)) for position in RECEIVER_POSITIONS}
F8_PARTS = {**{position: ("F5 receptions", "F5 receiving yards", "F5 rushing yards", "F5 TDs") for position in RECEIVER_POSITIONS},
            "QB": ("Q3 passing yards", "Q4 passing TDs", "Q5 interceptions", "QB rushing yards", "QB rushing TDs")}
F8_TRANSFORM = {**{position: skill_dk for position in RECEIVER_POSITIONS}, "QB": qb_dk}
GRADED_COLUMNS = ["season", "week", "key", "term", "position", "state", "outcome", "draw_mean", "outcome_rank", "crps", "bias", "quantile_10", "quantile_50", "quantile_90", "p_bonus"]
QB_ATTEMPTS = ("Q1 attempts", "QB")
def full_game_share(player_rows, season):
    """The full-game share (the project owner's premise, 2026-11-08: a starter plays the whole game): over the team-games of seasons before `season` in which
    exactly one quarterback threw a pass, his attempts over his team's attempts (the rest are trick-play passes by other positions)."""
    rows = player_rows[player_rows.season < season]
    team_attempts = rows.groupby(["season", "week", "team"]).attempts.sum()
    qb = rows[(rows.position == "QB") & (rows.attempts > 0)].groupby(["season", "week", "team"]).attempts.agg(["size", "sum"])
    one = qb[qb["size"] == 1].join(team_attempts.rename("team_attempts"), how="inner"); one = one[one.team_attempts > 0]
    return float((one["sum"] / one.team_attempts).mean()) if len(one) else np.nan
WORLD_TERM = "who starts"
def quarterback_worlds(players, participation_rows, season, week):
    """{quarterback key: starts (bool, DRAW_COUNT)}: for each team, every column is one world with exactly one of its quarterback candidates starting, or none of
    them (the outside option, 1 - the sum of their P(starts)), drawn from P(starts) on the team's own substream; a team's columns are partitioned among them."""
    p_starts = participation_rows.dropna(subset=["probability_starts"]).set_index("player_id").probability_starts.to_dict(); worlds = {}
    for team, team_qbs in players[(players.position == "QB") & players.key.isin(p_starts)].groupby("team"):
        keys = list(team_qbs.key); weights = np.array([p_starts[k] for k in keys], float); weights = np.append(weights, max(0.0, 1.0 - weights.sum())); weights = weights / weights.sum()
        pick = substream(WORLD_TERM, "QB", season, week, team, "one quarterback per world").choice(len(weights), size=DRAW_COUNT, p=weights)
        for i, key in enumerate(keys): worlds[key] = pick == i
    return worlds
def substream(term, position, season, week, key, label):
    """A row's own generator, keyed by what the row is (SHA-256 of term|position|season|week|key|label): a row's draws never depend on which other rows are drawn."""
    return np.random.default_rng(int.from_bytes(hashlib.sha256("|".join(str(part) for part in (term, position, season, week, key, label)).encode()).digest()[:8], "little"))
def engine_root(season, week):
    """Engine mode: the root draws for (season, week) from ROOT_FILE, checked before any use and loaded once per process.  Refuses by name: file missing, manifest
    missing, the manifest's root_draws_sha (the first 12 hex of SHA-256, as handoff_root_draws.py writes it) differing from the file's computed hash, the
    manifest's season or week differing from the issue, or draw_count differing from the arrays' width.  Returns dict(draws={(team, term): DRAW_COUNT columns},
    center={(team, term): the engine draws' mean}, teams, source_draws K, sha (full computed SHA-256), file)."""
    global ENGINE_ROOT
    if ENGINE_ROOT is not None and ENGINE_ROOT["key"] == (ROOT_FILE, int(season), int(week)): return ENGINE_ROOT   # a cache hit is one for this file and this issue only
    ENGINE_ROOT = None
    if not ROOT_FILE: raise SystemExit("engine root: SLATE_ROOT_SOURCE=engine but SLATE_ROOT_FILE is not set - refused; nothing issued")
    path = ROOT_FILE; manifest_path = path[:-4] + ".manifest.json" if path.endswith(".npz") else path + ".manifest.json"
    if not os.path.exists(path): raise SystemExit(f"engine root: draw file missing: {path} - refused; nothing issued")
    if not os.path.exists(manifest_path): raise SystemExit(f"engine root: manifest missing: {manifest_path} - refused; nothing issued")
    manifest = json.load(open(manifest_path)); computed = sha(path); stated = str(manifest.get("root_draws_sha", ""))
    if len(stated) < 12 or not computed.startswith(stated): raise SystemExit(f"engine root: SHA mismatch: the manifest states {stated!r}, the file {os.path.basename(path)} computes {computed} - refused; nothing issued")
    data = np.load(path, allow_pickle=False); teams = data["team"].astype(str); attempts = data["attempts"]; carries = data["carries"]; draw_ids = data["draw_id"]
    declared = int(manifest.get("draw_count", -1)); actual = int(attempts.shape[1])
    if not (declared == actual == int(carries.shape[1]) == len(draw_ids)): raise SystemExit(f"engine root: draw_count mismatch: the manifest declares {declared}, the arrays hold attempts {attempts.shape[1]}, carries {carries.shape[1]}, draw_id {len(draw_ids)} - refused; nothing issued")
    if int(manifest.get("season", -1)) != int(season) or int(manifest.get("week", -1)) != int(week): raise SystemExit(f"engine root: the file is for {manifest.get('season')} w{manifest.get('week')}, the issue is {season} w{week} - refused; nothing issued")
    columns = np.arange(DRAW_COUNT) % actual
    draws = {}; center = {}
    for row, team in enumerate(teams):
        for term, array in (("F2 team attempts", attempts), ("F2 team carries", carries)):
            draws[(team, term)] = array[row][columns].astype(float); center[(team, term)] = float(array[row].mean())
    ENGINE_ROOT = dict(key=(ROOT_FILE, int(season), int(week)), draws=draws, center=center, teams=set(teams), source_draws=actual, columns=DRAW_COUNT, sha=computed, file=os.path.basename(path), manifest=manifest)
    return ENGINE_ROOT
def root_record():
    """What the issue's root was, for the card and its report: source, file, hash, source draws and emitted columns."""
    if ROOT_SOURCE == "engine" and ENGINE_ROOT is not None: return dict(root_source="engine", root_file=ENGINE_ROOT["file"], root_file_sha=ENGINE_ROOT["sha"], root_source_draws=ENGINE_ROOT["source_draws"], root_columns=ENGINE_ROOT["columns"])
    return dict(root_source="kit", root_file="", root_file_sha="", root_source_draws=DRAW_COUNT, root_columns=DRAW_COUNT)
def slate_members(player_rows, team_games, season, week):
    """A slate's members from state's issue frames (one producer of the information set and the issue domain): the eligible teams, every QB / RB / WR / TE
    candidate in the windows (routed by rule (b)) and every candidate with its routing.  Every window, routing and candidate state builds is season-to-date (its
    groups are team-season and player-season-team), so the season's own rows are the whole of what it reads.  Returns (teams: key, team; players: key, team,
    position; candidates)."""
    eligible_teams, skill_window, qb_window, candidate_rows = issue_frames(player_rows[player_rows.season == season], team_games[team_games.season == season], season, week)
    teams = eligible_teams[eligible_teams.is_pad.astype(bool)][["team"]].drop_duplicates().assign(key=lambda frame: frame.team).reset_index(drop=True).merge(team_games[(team_games.season == season) & (team_games.week == week)][["team", "opponent"]].drop_duplicates("team"), on="team", how="left")   # batch 82: this week's opponent
    players = pd.concat([skill_window[skill_window.is_pad.astype(bool)][["player_id", "team", "position"]], qb_window[qb_window.is_pad.astype(bool)][["player_id", "team"]].assign(position="QB")], ignore_index=True)
    return teams, players.rename(columns={"player_id": "key"}).drop_duplicates("key").reset_index(drop=True), candidate_rows
def draw_link(cell, fit, rate, other, concentration, parent_draws, generator, sibling=None):
    """DRAW_COUNT draws of one link for one member: a team volume its center x measured ratios (whole counts); a share or conversion beta-binomial on its
    parent's draw at the row's concentration (binomial where it is infinite); a yards link the parent's draw x the rate + sqrt(draw) x measured per-unit
    residuals (whole yards)."""
    kind = LINKS[cell][3]
    if kind == "level": return np.rint(rate * fit["ratio"][generator.integers(0, len(fit["ratio"]), DRAW_COUNT)])
    if sibling is not None:   # THE SIBLING LAW: each draw's rate moves with its sibling's luck on the same trials
        sibling_draws, sibling_rate, sibling_fit = sibling; luck = sibling_luck_of(sibling_fit, sibling_draws, parent_draws, sibling_rate)
        mean = sibling_law(fit["theta"], rate, luck)
        return generator.binomial(parent_draws.astype(np.int64), generator.beta(mean * concentration, (1 - mean) * concentration) if np.isfinite(concentration) else mean).astype(float)
    if kind in ("share", "proportion"):
        share = generator.beta(rate * concentration, other * concentration, DRAW_COUNT) if np.isfinite(concentration) else rate   # batch 78: the complement link_rates carries
        return generator.binomial(parent_draws.astype(np.int64), share).astype(float)
    return np.rint(parent_draws * rate + np.sqrt(parent_draws) * fit["residuals"][generator.integers(0, len(fit["residuals"]), DRAW_COUNT)])
def depth(cell): return 0 if LINKS[cell][0] is None else 1 + depth(LINKS[cell][0])
def draw_slate(history, fits, season, week, teams, players, active, full_share=None):
    """Every member of one slate drawn link by link in dependency order: draws and centers keyed (key, term), the law rows, the rows that drew nothing and why,
    and the composed F8 per player (key, position, form, draws).  A link's center is its parent's center x its own pregame rate (a team volume: its level center;
    in engine mode the engine draws' mean)."""
    team_of = dict(zip(players.key, players.team)); draws, centers, rates_of, law_rows, undrawn = {}, {}, {}, [], []
    engine = engine_root(season, week) if ROOT_SOURCE == "engine" else None
    for cell in LINK_ORDER:
        term, position = cell; parent = LINKS[cell][0]; members = teams if position == TEAM_KEY else players[players.position == position]
        if not len(members): continue
        rates, others, units, concentrations = link_rates(history, fits, cell, members[["key", "team"]].assign(season=season, week=week, opponent=lambda frame: frame.team.map(dict(zip(teams.team, teams.opponent)))), active)
        for key, rate, other, earlier_units, concentration in zip(members.key, rates, others, units, concentrations):
            parent_key = None if parent is None else (key if parent[1] == position else team_of[key])
            if parent is not None and (parent_key, parent[0]) not in draws: undrawn.append((season, week, key, term, position, "parent law drew nothing")); continue
            if cell == QB_ATTEMPTS and full_share is not None and np.isfinite(full_share):   # the project owner's premise: if he starts he plays the whole game
                draws[(key, term)] = draw_link(cell, fits.get(cell), full_share, 1 - full_share, np.inf, draws[(parent_key, parent[0])], substream(term, position, season, week, key, LINK_CHAIN_STATE))   # through draw_link: the same binomial, traced like every other link
                rates_of[(key, term)] = full_share; centers[(key, term)] = centers[(parent_key, parent[0])] * full_share
                law_rows.append(dict(season=season, week=week, key=key, team=team_of[key], term=term, position=position, family="full game: binomial(team attempts, the full-game share)", state=LINK_CHAIN_STATE,
                                     layer=depth(cell), provenance=f"if he starts he plays the whole game (the project owner's premise, 2026-11-08): full-game share {full_share:.4f}, measured on seasons < {season}",
                                     conditioned_on_draw=f"{parent[0]} draw", rate=float(full_share), earlier_units=float(earlier_units)))
                continue
            if engine is not None and parent is None and term in ROOT_TERMS:
                if (key, term) not in engine["draws"]: raise SystemExit(f"engine root: team {key} has a game in {season} w{week} but no draws in {engine['file']} - refused; nothing issued (no fallback to the kit's root draw)")
                draws[(key, term)] = engine["draws"][(key, term)]; rates_of[(key, term)] = rate; centers[(key, term)] = engine["center"][(key, term)]
                law_rows.append(dict(season=season, week=week, key=key, team=key, term=term, position=position, family=ENGINE_FAMILY, state=LINK_CHAIN_STATE, layer=depth(cell),
                                     provenance=f"engine root: {engine['file']} sha {engine['sha'][:12]}, source draws {engine['source_draws']} -> {engine['columns']} columns (column j = source j mod {engine['source_draws']}); center = the engine draws' mean",
                                     conditioned_on_draw=np.nan, rate=float(rate), earlier_units=float(earlier_units)))
                continue
            if not np.isfinite(rate): undrawn.append((season, week, key, term, position, "pregame state undefined (his team has no earlier game this season)")); continue
            sibling = (draws[(key, SIBLINGS[cell][0])], rates_of[(key, SIBLINGS[cell][0])], fits[SIBLINGS[cell]]) if cell in SIBLINGS else None
            draws[(key, term)] = draw_link(cell, fits[cell], rate, other, concentration, None if parent is None else draws[(parent_key, parent[0])], substream(term, position, season, week, key, LINK_CHAIN_STATE), sibling)
            rates_of[(key, term)] = rate
            expected = float(sibling_law(fits[cell]["theta"], rate, 0.0)) if cell in SIBLINGS else rate
            centers[(key, term)] = expected if parent is None else centers[(parent_key, parent[0])] * expected
            law_rows.append(dict(season=season, week=week, key=key, team=key if position == TEAM_KEY else team_of[key], term=term, position=position, family=FAMILIES["sibling" if cell in SIBLINGS else LINKS[cell][3]], state=LINK_CHAIN_STATE,
                                 layer=depth(cell), provenance=f"the one link chain: {LINKS[cell][1]} per {LINKS[cell][2] or 'team-game'}, fit on seasons < {season}", conditioned_on_draw=f"{parent[0]} draw" if parent else np.nan,
                                 rate=float(rate), earlier_units=float(earlier_units)))
    for (term, position), parts in TD_PARTS.items():
        for key in players[players.position == position].key:
            if all((key, part[0]) in draws for part in parts):
                draws[(key, term)] = sum(draws[(key, part[0])] for part in parts); centers[(key, term)] = sum(centers[(key, part[0])] for part in parts)
                law_rows.append(dict(season=season, week=week, key=key, team=team_of[key], term=term, position=position, family="the sum of its parts' draws", state=LINK_CHAIN_STATE, layer=1 + max(depth(part) for part in parts),
                                     provenance="F5 receiving TDs + F5 rushing TDs, draw by draw", conditioned_on_draw=np.nan, rate=np.nan, earlier_units=np.nan))
    composed = [(key, position, LINK_CHAIN_STATE, F8_TRANSFORM[position](*[draws[(key, term)] for term in F8_PARTS[position]])) for key, position in zip(players.key, players.position) if all((key, term) in draws for term in F8_PARTS[position])]
    return dict(draws={**draws, **{(key, F8_TERM): f8_draws for key, position, form, f8_draws in composed}}, centers={**centers, **{(key, F8_TERM): float(f8_draws.mean()) for key, position, form, f8_draws in composed}},
                laws=pd.DataFrame(law_rows), undrawn=undrawn, composed=composed)
def outcome_frame(history, player_rows):
    """Every played game's outcome per (key, season, week): the box score of link_chain_history (whole, by state.box_zero), F5 TDs, and dk_points - the team-games' counts on the team rows."""
    outcomes = history.assign(**{"F5 TDs": history.receiving_tds + history.rushing_tds}).merge(player_rows[player_rows.played == 1].drop_duplicates(["player_id", "season", "week"])[["player_id", "season", "week", "dk_points"]].rename(columns={"player_id": "key"}), on=["key", "season", "week"], how="left")
    return outcomes.drop_duplicates(["key", "season", "week", "position"]).set_index(["key", "season", "week"])
DK_TEAM_TERM = "DK team total"
def dk_draws_of(composed, probability_of, season, week, worlds=None):
    """DK draws (batch 73: one producer for week_draws and the replay): F8 draws x Bernoulli(P(plays)), DNP = 0 (dk.dnp_zero), for every composed F8 whose
    player has a P(plays); each row's participation uniforms come from its own substream."""
    worlds = worlds or {}   # a quarterback with a world scores in the worlds he starts and nowhere else (acceptance-criteria/one-game-one-reality.md)
    return {(key, DK_TERM): (np.where(worlds[key], f8_draws, 0.0) if key in worlds else dnp_zero(f8_draws, substream(DK_TERM, position, season, week, key, "participation").random(DRAW_COUNT), probability_of[key]))
            for key, position, form, f8_draws in composed if key in probability_of or key in worlds}
def grade_dk(dk_draws, players, outcomes, season, week):
    """The score users consume, graded (batch 73): each DK row against DraftKings' recorded points, 0 for a member who did not play (his team-game was played:
    a replay season); each team's DK total - the sum of its members' DK draws, draw by draw - against the sum of their points.  Randomized PIT from its own
    keyed generator, CRPS, bias and quantiles, in the graded schema."""
    if not dk_draws: return pd.DataFrame(columns=GRADED_COLUMNS)
    position_of, team_of = dict(zip(players.key, players.position)), dict(zip(players.key, players.team)); keys = [key for key, term in dk_draws]
    points = np.array([float(outcomes.loc[(key, season, week), "dk_points"]) if (key, season, week) in outcomes.index else 0.0 for key in keys])
    matrix = np.vstack([dk_draws[(key, DK_TERM)] for key in keys]); teams = sorted(set(team_of[key] for key in keys))
    team_matrix = np.vstack([matrix[[team_of[key] == team for key in keys]].sum(0) for team in teams]); team_points = np.array([points[[team_of[key] == team for key in keys]].sum() for team in teams])
    rows = pd.DataFrame(dict(key=keys + teams, term=[DK_TERM] * len(keys) + [DK_TEAM_TERM] * len(teams), position=[position_of[key] for key in keys] + [TEAM_KEY] * len(teams)))
    matrix, outcome = np.vstack([matrix, team_matrix]), np.concatenate([points, team_points]); finite = np.isfinite(outcome); rows, matrix, outcome = rows[finite].reset_index(drop=True), matrix[finite], outcome[finite]
    quantiles = np.quantile(matrix, [0.10, 0.50, 0.90], axis=1)
    return rows.assign(season=season, week=week, state=LINK_CHAIN_STATE, outcome=outcome, draw_mean=matrix.mean(1), outcome_rank=rank(matrix, outcome, substream("dk rank", "slate", season, week, "", LINK_CHAIN_STATE)),
                       crps=crps(matrix, outcome), bias=matrix.mean(1) - outcome, quantile_10=quantiles[0], quantile_50=quantiles[1], quantile_90=quantiles[2], p_bonus=np.nan)[GRADED_COLUMNS]
def outcome_column(term, position):
    """The facts column a term is graded against: a link its numerator, F5 TDs its sum, F8 dk_points (DraftKings' recorded points)."""
    return {F8_TERM: "dk_points", "F5 TDs": "F5 TDs"}.get(term) or LINKS[(term, position)][1]
def grade_slate(slate, outcomes, season, week):
    """Every drawn row of a slate with a played outcome, graded: randomized PIT (one keyed generator per slate), CRPS, bias (draw mean - y) and quantiles."""
    keys = [(row.key, row.term, row.position) for row in slate["laws"].itertuples(index=False)] + [(key, F8_TERM, position) for key, position, form, f8_draws in slate["composed"]]
    graded = [(key, term, position, float(outcomes.loc[(key, season, week), outcome_column(term, position)])) for key, term, position in keys if (key, season, week) in outcomes.index]
    graded = [row for row in graded if np.isfinite(row[3])]
    if not graded: return pd.DataFrame(columns=GRADED_COLUMNS)
    matrix = np.vstack([slate["draws"][(key, term)] for key, term, position, outcome in graded]); outcome = np.array([row[3] for row in graded]); quantiles = np.quantile(matrix, [0.10, 0.50, 0.90], axis=1)
    threshold = np.array([float(BONUS_YARDS.get(outcome_column(term, position), np.nan)) for key, term, position, unused in graded])   # batch 69: the tail a yardage bonus is paid on (dk.BONUS_YARDS)
    p_bonus = np.where(np.isfinite(threshold), (matrix >= np.nan_to_num(threshold)[:, None]).mean(1), np.nan)
    return pd.DataFrame(dict(season=season, week=week, key=[row[0] for row in graded], term=[row[1] for row in graded], position=[row[2] for row in graded], state=LINK_CHAIN_STATE, outcome=outcome,
                             draw_mean=matrix.mean(1), outcome_rank=rank(matrix, outcome, substream("atlas rank", "slate", season, week, "", LINK_CHAIN_STATE)), crps=crps(matrix, outcome),
                             bias=matrix.mean(1) - outcome, quantile_10=quantiles[0], quantile_50=quantiles[1], quantile_90=quantiles[2], p_bonus=p_bonus))[GRADED_COLUMNS]
def season_chance(season_gains):
    """THE SEASON QUALITY GATE's chance test (project owner ruling Oct 7 2026; quality_gate_proof_read: false pass .037-.051): one-sided t on the season mean gains, df = seasons - 1.
    Returns p = P(T >= t) under a zero mean gain (NaN with fewer than two seasons)."""
    gains = np.asarray(season_gains, float)
    if len(gains) < 2: return np.nan
    with np.errstate(divide="ignore", invalid="ignore"): return float(student_t.sf(gains.mean() / (gains.std(ddof=1) / np.sqrt(len(gains))), len(gains) - 1))
def chance_label(differences, season_gains):
    """The one door of a judgment (R4): UNCHANGED when every paired difference is 0; BETTER or WORSE when the season chance test puts the mean season gain beyond
    ALPHA_FAMILY on that side; INSUFFICIENT_EVIDENCE otherwise (never measured is unknown, never no).  Returns (label, p better, p worse)."""
    better, worse = season_chance(season_gains), season_chance(-np.asarray(season_gains, float))
    if len(differences) and not np.any(differences): return "UNCHANGED", better, worse
    return ("BETTER" if better <= ALPHA_FAMILY else "WORSE" if worse <= ALPHA_FAMILY else "INSUFFICIENT_EVIDENCE"), better, worse
def season_gains_of(paired, before, after):
    """Per season the mean over slates of before - after (the season quality gate's gains), seasons in order."""
    slates = (paired[before] - paired[after]).groupby([paired.season, paired.week]).mean()
    return slates.groupby(level=0).mean().sort_index()
def product_judgment(graded_rows, previous_rows, terms=(F8_TERM,)):
    """R3 THE ONE JUDGMENT: the product against the previous product's graded rows - every F8 cell the previous product graded (position, state; its cells are
    read from its rows, never listed here), each against the new product's F8 at that position on the rows both graded (season, week, key): CRPS previous - new
    by season, chance_label.  ISSUED iff every previous F8 cell is paired and none is WORSE."""
    rows = []   # batch 73: every judged term (default F8; the DK cells and the team total when a previous product's DK rows are given)
    for (term, position, state), old in previous_rows[previous_rows.term.isin(terms)].groupby(["term", "position", "state"], sort=True):
        new_f8 = graded_rows[graded_rows.term == term]; new = new_f8[new_f8.position == position][["season", "week", "key", "crps"]]
        paired = new.merge(old[["season", "week", "key", "crps"]], on=["season", "week", "key"], suffixes=("_new", "_previous")); gains = season_gains_of(paired, "crps_previous", "crps_new")
        label, better, worse = chance_label((paired.crps_previous - paired.crps_new).to_numpy(), gains.to_numpy())
        rows.append(dict(term=term, position=position, previous_state=state, previous_rows=len(old), new_rows=len(new), paired_rows=len(paired), crps_previous=paired.crps_previous.mean(), crps_new=paired.crps_new.mean(),
                         bias_previous=old.merge(new[["season", "week", "key"]], on=["season", "week", "key"]).bias.mean(), bias_new=new_f8[new_f8.position == position].merge(old[["season", "week", "key"]], on=["season", "week", "key"]).bias.mean(),
                         season_gains="; ".join(f"{int(season)} {gain:+.4f}" for season, gain in gains.items()), p_better=better, p_worse=worse, verdict=label))
    judged = pd.DataFrame(rows); issued = bool(len(judged) and (judged.paired_rows > 0).all() and (judged.verdict != "WORSE").all())
    return judged.assign(product="ISSUED" if issued else "REFUSED"), issued
def reference_crps(graded_rows, outcomes):
    """Per graded row, the CRPS of the season-to-date reference at its outcome: the empirical law of the same key's earlier played outcomes of the same term this
    season (weeks < N); NaN with no earlier played game."""
    games = {key: group.sort_values("week") for key, group in outcomes.reset_index().groupby(["key", "season"], sort=False)}; scores = np.full(len(graded_rows), np.nan)
    for row_number, row in enumerate(graded_rows[["term", "position", "key", "season", "week", "outcome"]].itertuples(index=False)):
        season_games = games.get((row.key, row.season))
        if season_games is None: continue
        earlier = season_games[season_games.week < row.week][outcome_column(row.term, row.position)].to_numpy(float); earlier = earlier[np.isfinite(earlier)]
        if len(earlier): scores[row_number] = float(crps(earlier[None, :], np.array([float(row.outcome)]))[0])
    return scores
def ladder_cells(graded_rows, atlas):
    """The trust ladder per atlas cell (the card's contract): CENTER - PIT <= .50 within band of .50; WIDTH - PIT <= .10 or > .90 within band of .20, its tails L / U
    each against .10 (share_band, the atlas's band rule); SKILL against the season-to-date reference by chance_label on its season gains (PASS = BETTER, FAIL =
    WORSE, else INSUFFICIENT_EVIDENCE); CRPSS = 1 - mean kit / mean reference; RUNG 1 issued, 2 center and width, 3 and skill PASS."""
    cells, frozen_weeks = [], len(glob.glob(os.path.join(PROJ_DIR, "score_*_w*.csv")))
    for (term, position, state), cell_rows in graded_rows.groupby(["term", "position", "state"], sort=True):
        slates = [cell_rows.season.values, cell_rows.week.values]; center = share_band(cell_rows.outcome_rank <= 0.50, slates, 0.50); width = share_band((cell_rows.outcome_rank <= 0.10) | (cell_rows.outcome_rank > 0.90), slates, 0.20)
        lower, upper = share_band(cell_rows.outcome_rank <= 0.10, slates, 0.10), share_band(cell_rows.outcome_rank > 0.90, slates, 0.10); scored = cell_rows[np.isfinite(cell_rows.crps_reference)]
        skill = {"BETTER": "PASS", "WORSE": "FAIL"}.get(chance_label((scored.crps_reference - scored.crps).to_numpy(), season_gains_of(scored, "crps_reference", "crps").to_numpy())[0], "INSUFFICIENT_EVIDENCE")
        rung_two = center[2] == "within band" and width[2] == "within band"
        cells.append(dict(term=term, position=position, state=state, rows=len(cell_rows), center_share=center[0], center_band=center[2], tail_share=width[0], width_band=width[2], lower_share=lower[0], lower_band=lower[2],
                          upper_share=upper[0], upper_band=upper[2], tail_balance="balanced" if lower[2] == "within band" and upper[2] == "within band" else "unresolved", reference_rows=len(scored),
                          crpss=float(1 - scored.crps.mean() / scored.crps_reference.mean()) if len(scored) else np.nan, skill=skill, rung=3 if rung_two and skill == "PASS" else (2 if rung_two else 1),
                          prospective_evidence=f"{frozen_weeks} frozen weeks scored"))
    return pd.DataFrame(cells).merge(atlas[["term", "position", "state", "qualification"]], on=["term", "position", "state"], how="left")
def replay(previous_path, previous_dk_path=None):
    """python3 kit.py replay PREVIOUS_ATLAS_ROWS: THE ONE REPLAY and THE ONE JUDGMENT (R3, R4).  The product at every cutoff - each season s <= FROZEN_THRU with an
    earlier season, fit once on seasons < s (fit_link_chain), every issue week drawn from its own information set - graded on played rows; judged against the previous
    product's graded rows at PREVIOUS_ATLAS_ROWS (product_judgment), the judgment written (proj/product_judgment.csv) before any reading; then the readings:
    proj/atlas_rows.csv.gz, atlas.csv, ladder.csv and replay_report.txt.  Exit 0 iff the product is ISSUED."""
    report = Report(); player_rows, team_games = load(), team_game(); history = link_chain_history(player_rows); outcomes = outcome_frame(history, player_rows); previous_rows = read_table(previous_path); active = active_keys()
    seasons = sorted(int(season) for season in history.season.unique() if season <= FROZEN_THRU and (history.season < season).any()); graded, fit_lines, coverage = [], [], []
    who_rows = model_rows_of(who_plays_inputs(player_rows, team_games, sorted(int(season) for season in history.season.unique() if season <= FROZEN_THRU))); dk_graded = []   # batch 73: who plays, fit once per season
    for season in seasons:
        fits = fit_link_chain(history, season, active); who_laws, unused = who_plays_fit(who_rows[who_rows.season < season]); season_rows = who_rows[who_rows.season == season]
        season_rows = season_rows.assign(probability_plays=who_plays_probability(who_laws, season_rows))
        fit_lines.append(f"   s {season}: " + "; ".join(f"{term} {position} " + (f"delta {fit['delta']:.3f} w-ratio sd {np.std(fit['ratio']):.3f}" if "delta" in fit else (f"sibling law t {np.round(fit['theta'], 3).tolist()} rho {fit['rho']:.4f}" if "sibling" in fit else f"role law t {np.round(fit['theta'], 3).tolist()}") if "theta" in fit else f"rho {fit['rho']:.4f}" if "rho" in fit else f"residual sd {np.std(fit['residuals']):.3f}") + f" mu {fit.get('mu', np.nan):.4f}"
                                             for (term, position), fit in fits.items()))
        for week in sorted(set(team_games[team_games.season == season].week) & set(ISSUE_WEEKS)):
            teams, players, candidate_rows = slate_members(player_rows, team_games, season, week)
            if not len(teams): continue
            slate = draw_slate(history, fits, season, week, teams, players, active, full_game_share(player_rows, season)); graded.append(grade_slate(slate, outcomes, season, week))
            probability_of = season_rows[season_rows.week == week].set_index("player_id").probability_plays.to_dict()
            dk_graded.append(grade_dk(dk_draws_of(slate["composed"], probability_of, season, week), players, outcomes, season, week))
            coverage.append((season, week, len(candidate_rows), len(teams), len(players), len(slate["laws"]), len(slate["composed"]), len(slate["undrawn"])))
    pd.concat(graded, ignore_index=True).to_csv(os.path.join(PROJ_DIR, "atlas_rows.csv.gz"), index=False); graded_rows = read_table(os.path.join(PROJ_DIR, "atlas_rows.csv.gz"))   # both sides judged as records through the one reader (facts.read_table: round-trip floats)
    pd.concat(dk_graded, ignore_index=True).to_csv(os.path.join(PROJ_DIR, "dk_rows.csv.gz"), index=False); dk_rows = read_table(os.path.join(PROJ_DIR, "dk_rows.csv.gz"))   # batch 73: the score users consume
    judged, issued = product_judgment(graded_rows, previous_rows)
    if previous_dk_path:
        dk_judged, dk_issued = product_judgment(dk_rows, read_table(previous_dk_path), (DK_TERM, DK_TEAM_TERM)); judged = pd.concat([judged, dk_judged], ignore_index=True); issued = issued and dk_issued
        judged["product"] = "ISSUED" if issued else "REFUSED"
    judged.to_csv(os.path.join(PROJ_DIR, "product_judgment.csv"), index=False)   # R4: written before any reading
    report.say(f"kit.py replay - THE ONE JUDGMENT (R3): the rewritten product vs {previous_path}, F8 CRPS on rows both graded; season chance test, ALPHA_FAMILY {ALPHA_FAMILY}")
    for row in judged.itertuples(index=False):
        report.say(f"   {row.term} {row.position:<4} vs previous {row.previous_state:<12} paired {row.paired_rows:>6} (previous {row.previous_rows}, new {row.new_rows})  CRPS {row.crps_previous:.4f} -> {row.crps_new:.4f}  bias {row.bias_previous:+.3f} -> {row.bias_new:+.3f}  season gains {row.season_gains}  p better {row.p_better:.4f} worse {row.p_worse:.4f} -> {row.verdict}")
    report.say(f"PRODUCT {judged['product'].iloc[0]} - written to proj/product_judgment.csv before the readings below" + ("" if previous_dk_path else f";  DK cells and the team total: baseline written (proj/dk_rows.csv.gz, {len(dk_rows)} rows) - no previous DK rows to judge against"))
    atlas = atlas_cells(graded_rows); atlas.to_csv(os.path.join(PROJ_DIR, "atlas.csv"), index=False)
    ladder = ladder_cells(graded_rows.assign(crps_reference=reference_crps(graded_rows, outcomes)), atlas); ladder.to_csv(os.path.join(PROJ_DIR, "ladder.csv"), index=False)
    coverage = pd.DataFrame(coverage, columns=["season", "week", "candidates", "teams", "players", "law_rows", "f8_rows", "undrawn"])
    report.say(f"\nREADINGS - seasons {seasons}, slates {len(coverage)}: candidates {int(coverage.candidates.sum())}, teams {int(coverage.teams.sum())}, players {int(coverage.players.sum())}, law rows {int(coverage.law_rows.sum())}, F8 {int(coverage.f8_rows.sum())}, drew nothing {int(coverage.undrawn.sum())}; graded rows {len(graded_rows)}")
    report.say("FITS (seasons < s):")
    for line in fit_lines: report.say(line)
    paired_cells = graded_rows.merge(previous_rows[["season", "week", "key", "term", "position", "crps", "bias"]], on=["season", "week", "key", "term", "position"], suffixes=("", "_previous"))
    report.say("\nCELLS - rows | CRPS | bias | on rows the previous product also graded: rows, CRPS previous -> new, bias previous -> new | atlas qualification | ladder rung, skill, CRPSS")
    for cell in atlas.merge(ladder[["term", "position", "state", "rung", "skill", "crpss"]], on=["term", "position", "state"]).itertuples(index=False):
        both = paired_cells[(paired_cells.term == cell.term) & (paired_cells.position == cell.position)]
        report.say(f"   {cell.term:<18} {cell.position:<4} rows {cell.rows:>6} | CRPS {cell.crps_mean:8.4f} | bias {cell.bias_mean:+8.3f} | paired {len(both):>6}" + (f" CRPS {both.crps_previous.mean():8.4f} -> {both.crps.mean():8.4f}, bias {both.bias_previous.mean():+.3f} -> {both.bias.mean():+.3f}" if len(both) else "")
                   + f" | {cell.qualification} | rung {cell.rung}, skill {cell.skill}, CRPSS {cell.crpss:+.3f}")
    f8 = atlas[atlas.term == F8_TERM]
    report.say(f"\nDONE READINGS: F8 cells DECISION-QUALIFIED {int((f8.qualification == 'DECISION-QUALIFIED').sum())} of {len(f8)}; QB F8 CRPS {float(f8[f8.position == 'QB'].crps_mean.iloc[0]) if (f8.position == 'QB').any() else np.nan:.4f} (witness_v4 4.7247); qualification counts: "
               + "; ".join(f"{label} {count}" for label, count in atlas.qualification.value_counts().items()))
    report.write(os.path.join(PROJ_DIR, "replay_report.txt")); return 0 if issued else 1
def dst_week(issue_season, issue_week):
    """Week N's DST laws: OLS of DST points on [1, state's DST_INPUTS] fit on every issue-week team-game of seasons < N's season (and <= FROZEN_THRU) with HISTORY_MINIMUM
    earlier team-games and every input defined; the law is the center + the measured training residuals, whole points.  Returns (rows, draws keyed (team, DST),
    the team-games without a law and why)."""
    frame = dst_frame(team_game()); defined = frame[DST_INPUTS].notna().all(axis=1); history_enough = frame.team_games_season_pregame >= HISTORY_MINIMUM
    fit_rows = frame[(frame.season < issue_season) & (frame.season <= FROZEN_THRU) & frame.week.isin(list(ISSUE_WEEKS)) & history_enough & defined & frame.dst_points.notna()]
    week_mask = (frame.season == issue_season) & (frame.week == issue_week); week_rows = frame[week_mask & history_enough & defined].reset_index(drop=True)
    without_law = frame[week_mask & ~(history_enough & defined)].assign(reason=lambda rows: np.where(rows.team_games_season_pregame >= HISTORY_MINIMUM, "DST input undefined", f"fewer than {HISTORY_MINIMUM} earlier team-games"))[["team", "reason"]]
    design = lambda rows: np.column_stack([np.ones(len(rows))] + [rows[column].to_numpy(float) for column in DST_INPUTS]); coefficients = np.linalg.lstsq(design(fit_rows), fit_rows.dst_points.to_numpy(float), rcond=None)[0]
    residuals = fit_rows.dst_points.to_numpy(float) - design(fit_rows) @ coefficients; week_rows = week_rows[["season", "week", "team", "opponent", "is_home"]].assign(center=design(week_rows) @ coefficients)
    draws = {(row.team, DST_TERM): np.rint(row.center + residuals[substream(DST_TERM, "DST", issue_season, issue_week, row.team, "dst").integers(0, len(residuals), DRAW_COUNT)]) for row in week_rows.itertuples(index=False)}
    return week_rows, draws, without_law
def summary_frame(rows):
    """Summary rows in the card's schema from (season, week, key, term, position, family, state, center, center_source, draws)."""
    return pd.DataFrame([(season, week, key, term, position, family, state, float(center), source, float(values.mean()), *np.quantile(values, QUANTILE_LEVELS)) for season, week, key, term, position, family, state, center, source, values in rows],
                        columns=["season", "week", "key", "term", "position", "family", "state", "center", "center_source", "draw_mean"] + QUANTILE_NAMES)
def week_draws(issue_season, issue_week):
    """Week N issued (one producer for kit.py draws, the card and the market): the information set through week N-1 (refused while a scheduled team-game before
    week N has no plays on disk), the link chain fit on seasons < N's season, the slate drawn, F8, P(plays) and DK draws with DNP = 0, DST laws, and per-row summaries.
    In engine mode the root cells come from the engine draw file (engine_root) and the issue carries root_record()."""
    player_rows, team_games = load(), team_game(); unplayed = team_games[(team_games.season == issue_season) & (team_games.week < issue_week) & team_games.plays.isna()]
    if len(unplayed): raise SystemExit(f"week_draws {issue_season} w{issue_week}: {len(unplayed)} scheduled team-games before week {issue_week} have no plays on disk - fetch them first; nothing issued")
    if ROOT_SOURCE == "engine": engine_root(issue_season, issue_week)   # the engine file is checked before any fit: a broken input refuses here, nothing issued
    known = player_rows[(player_rows.season < issue_season) | ((player_rows.season == issue_season) & (player_rows.week < issue_week))]; history = link_chain_history(known)
    teams, players, candidate_rows = slate_members(player_rows, team_games, issue_season, issue_week); active = active_keys(); slate = draw_slate(history, fit_link_chain(history, issue_season, active), issue_season, issue_week, teams, players, active, full_game_share(known, issue_season))
    participation_rows, participation_cells = week_participation(issue_season, issue_week); probability_of = participation_rows.dropna(subset=["probability_plays"]).set_index("player_id").probability_plays.to_dict()
    worlds = quarterback_worlds(players, participation_rows, issue_season, issue_week); dk_draws = dk_draws_of(slate["composed"], probability_of, issue_season, issue_week, worlds)
    dst_rows, dst_draws, dst_without = dst_week(issue_season, issue_week); laws = slate["laws"]
    root_center_source = {law.key + "|" + law.term: ("the engine draws' mean" if str(law.family) == ENGINE_FAMILY else "the one link chain: the parent's center x the pregame rate") for law in laws.itertuples(index=False)}
    summaries = summary_frame([(issue_season, issue_week, law.key, law.term, law.position, law.family, law.state, slate["centers"][(law.key, law.term)], root_center_source[law.key + "|" + law.term], slate["draws"][(law.key, law.term)]) for law in laws.itertuples(index=False)]
                              + [(issue_season, issue_week, key, F8_TERM, position, "dk transform of the player's own draws", form, f8_draws.mean(), "mean of the F8 transform's draws", f8_draws) for key, position, form, f8_draws in slate["composed"]]
                              + [(issue_season, issue_week, row.team, DST_TERM, "DST", "DST: OLS center + measured residuals (whole points)", LINK_CHAIN_STATE, row.center, "law center", dst_draws[(row.team, DST_TERM)]) for row in dst_rows.itertuples(index=False)]
                              + [(issue_season, issue_week, key, DK_TERM, position, "F8 x Bernoulli(P(plays)), DNP = 0", form, dk_draws[(key, DK_TERM)].mean(), "mean of the DK draws", dk_draws[(key, DK_TERM)]) for key, position, form, f8_draws in slate["composed"] if (key, DK_TERM) in dk_draws])
    return dict(issued=dict(candidates=candidate_rows, teams=teams, players=players), laws=laws, draws={**slate["draws"], **dk_draws, **dst_draws}, undrawn=slate["undrawn"], composed=slate["composed"],
                participation=(participation_rows, participation_cells), dst=dict(rows=dst_rows, without=dst_without, draws=dst_draws), dk=dict(draws=dk_draws, without=[key for key, position, form, f8_draws in slate["composed"] if key not in probability_of]), summaries=summaries,
                root=root_record(), worlds=worlds)
def frozen_draws_path(issue_season, issue_week): return os.path.join(PROJ_DIR, f"frozen_draws_{issue_season}_w{issue_week}.npz")
def player_draw_matrix(week):
    """Every issued player and DST row of week N (TEAM rows excluded), in summary order: key, term and position arrays and the draw matrix (DRAW_COUNT draws per row)."""
    player_rows = week["summaries"][week["summaries"].position != TEAM_KEY]; worlds = week.get("worlds", {}); starters = sorted(worlds)
    return dict(keys=player_rows.key.to_numpy(dtype=str), terms=player_rows.term.to_numpy(dtype=str), positions=player_rows.position.to_numpy(dtype=str), draws=np.vstack([week["draws"][(row.key, row.term)] for row in player_rows.itertuples(index=False)]),
                starts_keys=np.array(starters, dtype=str), starts=np.vstack([worlds[k] for k in starters]) if starters else np.zeros((0, DRAW_COUNT), dtype=bool))
def team_draws_path(issue_season, issue_week): return os.path.join(PROJ_DIR, f"team_draws_{issue_season}_w{issue_week}.npz")
def team_draw_matrix(week):
    """Every TEAM row of week N (the parents the player slices are drawn from), in summary order: key, term and position arrays and the draw matrix.
    Written beside the frozen player draws so a check can hold each slice against its own budget; the market does not read it."""
    team_rows = week["summaries"][week["summaries"].position == TEAM_KEY]
    return dict(keys=team_rows.key.to_numpy(dtype=str), terms=team_rows.term.to_numpy(dtype=str), positions=team_rows.position.to_numpy(dtype=str), draws=np.vstack([week["draws"][(row.key, row.term)] for row in team_rows.itertuples(index=False)]))
def freeze_draws(week, issue_season, issue_week):
    """Write week N's player draw matrix to proj/frozen_draws_{SEASON}_w{WEEK}.npz, the only draws the market reads; returns (path, SHA-256)."""
    path = frozen_draws_path(issue_season, issue_week); np.savez_compressed(path, **player_draw_matrix(week)); np.savez_compressed(team_draws_path(issue_season, issue_week), **team_draw_matrix(week)); return path, sha(path)
def draw_issue(issue_season, issue_week):
    """python3 kit.py draws SEASON WEEK: week N drawn -> proj/native_draw_week_{SEASON}_w{WEEK}.csv.gz and the frozen draws (DRY RUN)."""
    report = Report(); week = week_draws(issue_season, issue_week); path = os.path.join(PROJ_DIR, f"native_draw_week_{issue_season}_w{issue_week}.csv.gz"); week["summaries"].to_csv(path, index=False)
    frozen_path, frozen_sha = freeze_draws(week, issue_season, issue_week)
    report.say(f"kit.py draws {issue_season} w{issue_week} (DRY RUN; {DRAW_COUNT} keyed draws per row): law rows {len(week['laws'])}, F8 {len(week['composed'])}, DK {len(week['dk']['draws'])} (without P(plays) {len(week['dk']['without'])}), DST {len(week['dst']['rows'])}, drew nothing {len(week['undrawn'])}")
    report.say(f"   wrote {path}, {frozen_path} (SHA-256 {frozen_sha})"); return 0
