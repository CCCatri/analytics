"""model: the one inference interface. Fits every conditional predictive sub_model of the joint environment from the training view of one cutoff,
through two backends: Stan (CmdStanPy; sources in stan/) for the hierarchical player sub_models, and conjugate Dirichlet/Beta posteriors for the
non-player game sub_models (personnel groups, fourth-down decisions, field goals, kicks, clock, penalties, fumbles, tries). Every fit returns a
typed FitResult: FIT_OK with its draws and diagnostics, INSUFFICIENT_DATA, INVALID_FIT or UNSUPPORTED_INPUT. A numerical failure is INVALID_FIT:
nothing here hands back a pooled answer in its place. No display or grader logic lives here."""
import dataclasses, hashlib, json, math, os, pathlib, time
import numpy as np, pandas as pd
from scipy import stats
import policy as K
import record, rules

HERE = pathlib.Path(__file__).resolve().parent
FITS = HERE / "_probe" / "fits"
PAD = ""                                # index 0 (Stan index 1) of every grouping: the "no such effect" element
DOWN_CLASS = ("early", "third", "fourth")
YARD_BIN = 5
PUNT_CTX_BIN = 10
FG_BINS = (29, 39, 49, 54, 999)
TOGO_BINS = (1, 3, 6, 10, 999)
ELAPSED_CAP = 45
HURRY_SECONDS = 120
KNEEL_SECONDS = 120
SAFETY_ZONE = 90                        # a scrimmage snap from inside the own 10: the safety sub_model's domain
RESULT_CATS = ("incomplete", "complete", "interception")
BRANCH_CATS = (rules.PASS, rules.SACK, rules.SCRAMBLE, rules.SPIKE)
FOURTH_CATS = ("go", rules.PUNT, rules.FIELD_GOAL)
PERSONNEL_GROUPS = rules.OFFENSE_GROUPS
RUSH_ELIGIBLE = ("QB", "RB", "FB", "WR", "TE")


class ModelError(RuntimeError):
    pass


@dataclasses.dataclass
class FitResult:
    name: str
    status: str
    program: str
    draws: dict
    index: dict
    transform: dict
    diagnostics: dict
    n_obs: int
    cutoff_key: str
    model_version: str
    provenance: str

    @property
    def D(self):
        return next(iter(self.draws.values())).shape[0] if self.draws else 0

    def ok(self):
        return self.status == K.FIT_OK


# ----------------------------------------------------------------------------------------------------------------------------- helpers
def down_class(down):
    d = np.asarray(down); return np.where(d >= 4, 2, np.where(d == 3, 1, 0))


def yard_bin(y):
    return np.clip(np.asarray(y, dtype=int) // YARD_BIN, 0, K.FIELD_YARDS // YARD_BIN - 1)


def togo_bin(t):
    return np.searchsorted(np.array(TOGO_BINS), np.asarray(t, dtype=int), side="left")


def fg_bin(yardline):
    return np.searchsorted(np.array(FG_BINS), np.asarray([rules.fg_distance(y) for y in np.atleast_1d(yardline)]), side="left")


def hurry(half, seconds, score_diff):
    return (np.asarray(seconds) <= HURRY_SECONDS) & (np.asarray(score_diff) <= 0) & (np.asarray(half) >= 2)


def kneel_state(half, seconds, score_diff):
    """The state in which a kneel is a decision the record shows: inside the last two minutes of a half, leading (second half or OT) or any
    score (first half)."""
    s = np.asarray(seconds) <= KNEEL_SECONDS
    return s & ((np.asarray(half) == 1) | (np.asarray(score_diff) > 0))


def covariates(name, E):
    """Covariate columns of a mechanism from an events frame (raw, before standardisation)."""
    yl = (E.yardline_100.to_numpy(float) // YARD_BIN) * YARD_BIN / K.FIELD_YARDS   # 5-yard bins, so identical rows collapse
    down = E.down.to_numpy(float); diff = np.clip(np.rint(E.score_diff.to_numpy(float) / 7.0), -3, 3)
    hu = hurry(E.half, E.seconds, E.score_diff).astype(float); togo = np.log1p(np.array(TOGO_BINS, dtype=float)[np.minimum(togo_bin(E.ydstogo.to_numpy(int)), len(TOGO_BINS) - 1)])
    if name == "call": return np.column_stack([down == 2, down == 3, down >= 4, togo, diff, hu, yl])
    if name == "branch": return np.column_stack([hu, down == 3, diff])
    if name == "result": return np.column_stack([yl, down == 3, hu])
    if name in ("td_pass", "td_run"): return np.column_stack([yl, yl <= 0.05, yl <= 0.10] + ([E.kind.eq(rules.SCRAMBLE).to_numpy(float)] if name == "td_run" else []))
    if name == "gain_pass": return np.column_stack([yl, yl <= 0.10, down == 3])
    if name == "gain_run": return np.column_stack([yl, yl <= 0.10, E.kind.eq(rules.SCRAMBLE).to_numpy(float)])
    if name == "gain_sack": return np.column_stack([yl])
    return np.zeros((len(E), 0))


def standardize(X, transform=None):
    """Training-only standardisation: means and sds from the fit's observations, reused at prediction."""
    X = np.asarray(X, dtype=float)
    if transform is None:
        mu = X.mean(axis=0) if len(X) else np.zeros(X.shape[1]); sd = X.std(axis=0) if len(X) else np.ones(X.shape[1]); sd = np.where(sd > 0, sd, 1.0)
        transform = {"mean": mu.tolist(), "sd": sd.tolist()}
    return (X - np.array(transform["mean"])) / np.array(transform["sd"]), transform


class Index:
    """Integer codes, index 0 = PAD: players; position groups; (player, season) pairs (the sparse season states); defence team-seasons; team-games."""
    def __init__(self, seasons=()):
        self.players = [PAD]; self.pl = {PAD: 0}; self.positions = [PAD]; self.ps = {PAD: 0}; self.pgs = [PAD]; self.pg = {PAD: 0}
        self.pairs = [(PAD, 0)]; self.pr = {(PAD, 0): 0}; self.defs = [(PAD, 0)]; self.df = {(PAD, 0): 0}
        self.seasons = sorted(set(int(x) for x in seasons))

    def player(self, m):
        if m not in self.pl: self.pl[m] = len(self.players); self.players.append(m)
        return self.pl[m]

    def position(self, g):
        if g not in self.ps: self.ps[g] = len(self.positions); self.positions.append(g)
        return self.ps[g]

    def pair(self, m, season):
        k = (m, int(season)); self.player(m)
        if k not in self.pr: self.pr[k] = len(self.pairs); self.pairs.append(k)
        return self.pr[k]

    def defense(self, team, season):
        k = (team, int(season))
        if k not in self.df: self.df[k] = len(self.defs); self.defs.append(k)
        return self.df[k]

    def game(self, key):
        if key not in self.pg: self.pg[key] = len(self.pgs); self.pgs.append(key)
        return self.pg[key]

    def links(self):
        """j_prev (0 = none) and j_dt (seasons) per pair: each player's pairs chained in season order."""
        prev, dt, _ = self.chain(); return prev, dt

    def chain(self):
        """j_prev, j_dt and the evaluation order: pairs are coded in encounter order across sub_models (a player's 2020 pair may be coded before his
        2019 pair), so the AR(1) state of a pair is computed only after its predecessor's; order lists every pair after its j_prev."""
        by = {}
        for j, (m, se) in enumerate(self.pairs):
            if j: by.setdefault(m, []).append((se, j))
        prev = [0] * len(self.pairs); dt = [0.0] * len(self.pairs); order = [0]
        for m, lst in by.items():
            lst.sort()
            for (se0, j0), (se1, j1) in zip(lst[:-1], lst[1:]): prev[j1] = j0; dt[j1] = float(se1 - se0)
            order.extend(j for _, j in lst)
        return prev, dt, order

    def as_dict(self):
        prev, dt, order = self.chain()
        return {"players": list(self.players), "positions": list(self.positions), "seasons": list(self.seasons), "pairs": [list(x) for x in self.pairs],
                "j_prev": prev, "j_dt": dt, "j_order": order, "defenses": [list(x) for x in self.defs], "n_player_games": len(self.pgs)}


def position_lookup(cutoff):
    P = record.training_positions(cutoff)
    return {(int(s), int(w), m): rules.position_group(p) for s, w, m, p in zip(P.season, P.week, P.player, P.position)}


def group_of(pos, season, week, player):
    return pos.get((int(season), int(week), player), "OTHER")


# ----------------------------------------------------------------------------------------------------------------------------- observations
def obs_snap(E, pos, idx, cutoff):
    """Snap propensity: per (season, game, team, player) with known on-field sets: y = snaps on the field, n = the team's known scrimmage snaps.
    Men: every player on any known set of the team's game plus the week's ACT roster of the team (resolved code), y = 0 when never on the field."""
    S = E[E.snap & E.onf.notna()]; rows = []   # the snap standard (rules.is_offensive_snap): live downs plus penalty no-plays with an offensive unit
    for (season, gid, team, week), d in S.groupby(["season", "game_id", "posteam", "week"]):
        n = len(d); cnt = {}
        for s in d.onf:
            for m in s: cnt[m] = cnt.get(m, 0) + 1
        players = set(cnt)
        if season in cutoff.admitted_seasons:
            R = record.roster_raw(int(season)); codes = record.season_team_codes(int(season))
            A = R[R.week.eq(week) & R.status.eq("ACT") & R.gsis_id.notna()]
            players |= {m for t, m in zip(A.team, A.gsis_id) if record.resolve_code(t, codes) == team}
        opp = d.defteam.iloc[0]
        for m in players:
            rows.append((int(season), gid, team, int(week), m, cnt.get(m, 0), n, group_of(pos, season, week, m), opp))
    O = pd.DataFrame(rows, columns=["season", "game_id", "posteam", "week", "player", "y", "n", "group", "opp"])
    return O, {"y": O.y.to_numpy(int), "n": O.n.to_numpy(int), "X": np.zeros((len(O), 0)), "pl": [idx.player(m) for m in O.player], "pos": [idx.position(g) for g in O.group],
               "ps": [idx.pair(m, se) for m, se in zip(O.player, O.season)], "df": [idx.defense(t, se) for t, se in zip(O.opp, O.season)], "pg": [0] * len(O)}


def obs_call(E, idx):
    """Pass (dropback) versus designed run on every scrimmage snap outside the kneel state, grouped by team (persistent + season AR) with a
    team-game effect."""
    S = E[E.kind.isin(rules.SCRIMMAGE) & E.kind.ne(rules.KNEEL) & ~kneel_state(E.half, E.seconds, E.score_diff)]
    return S, {"y": S.kind.isin(rules.DROPBACK).to_numpy(int), "n": np.ones(len(S), int), "X": covariates("call", S), "pl": [idx.player(("team", t)) for t in S.posteam],
               "pos": [0] * len(S), "ps": [idx.pair(("team", t), se) for t, se in zip(S.posteam, S.season)], "df": [idx.defense(t, se) for t, se in zip(S.defteam, S.season)],
               "pg": [idx.game((g, "team")) for g in S.game_id]}


def obs_branch(E, pos, idx):
    S = E[E.kind.isin(rules.DROPBACK) & E.passer.notna()]
    return S, {"y": [BRANCH_CATS.index(k) + 1 for k in S.kind], "X": covariates("branch", S), "pl": [idx.player(m) for m in S.passer], "pl2": [0] * len(S),
               "pos": [0] * len(S), "ps": [idx.pair(m, se) for m, se in zip(S.passer, S.season)], "df": [idx.defense(t, se) for t, se in zip(S.defteam, S.season)], "pg": [0] * len(S)}


def obs_result(E, pos, idx):
    S = E[E.kind.eq(rules.PASS) & E.receiver.notna() & E.passer.notna()]
    y = np.where(S.interception.eq(1), 3, np.where(S.complete.eq(1), 2, 1))
    return S, {"y": y, "X": covariates("result", S), "pl": [idx.player(m) for m in S.receiver], "pl2": [idx.player(m) for m in S.passer],
               "pos": [idx.position(group_of(pos, s, w, m)) for s, w, m in zip(S.season, S.week, S.receiver)], "ps": [idx.pair(m, se) for m, se in zip(S.receiver, S.season)],
               "df": [idx.defense(t, se) for t, se in zip(S.defteam, S.season)], "pg": [0] * len(S)}


def obs_td(E, pos, idx, name):
    if name == "td_pass": S = E[E.kind.eq(rules.PASS) & E.complete.eq(1) & E.receiver.notna()]; who = S.receiver
    else: S = E[E.kind.isin([rules.RUN, rules.SCRAMBLE]) & E.rusher.notna()]; who = S.rusher
    return S, {"y": S.touchdown.to_numpy(int), "n": np.ones(len(S), int), "X": covariates(name, S), "pl": [idx.player(m) for m in who],
               "pos": [idx.position(group_of(pos, s, w, m)) for s, w, m in zip(S.season, S.week, who)], "ps": [idx.pair(m, se) for m, se in zip(who, S.season)],
               "df": [idx.defense(t, se) for t, se in zip(S.defteam, S.season)], "pg": [0] * len(S)}


def obs_gain(E, pos, idx, name, counts):
    if name == "gain_pass": S = E[E.kind.eq(rules.PASS) & E.complete.eq(1) & E.touchdown.eq(0) & E.receiver.notna()]; who = S.receiver
    elif name == "gain_run": S = E[E.kind.isin([rules.RUN, rules.SCRAMBLE]) & E.touchdown.eq(0) & E.safety.eq(0) & E.rusher.notna()]; who = S.rusher
    else: S = E[E.kind.eq(rules.SACK) & E.safety.eq(0) & E.passer.notna()]; who = S.passer
    sup = np.array([rules.gain_support(k, y) for k, y in zip(S.kind, S.yardline_100)]).reshape(-1, 2) if len(S) else np.zeros((0, 2), int)
    y = S.yards_gained.to_numpy(int) if len(S) else np.zeros(0, int)
    ok = (y >= sup[:, 0]) & (y <= sup[:, 1]) if len(S) else np.zeros(0, bool)
    counts[f"{name}_outside_legal_support_dropped"] = int((~ok).sum())
    S = S[ok]; who = who[ok]
    return S, {"y": y[ok], "lo": sup[ok, 0], "hi": sup[ok, 1], "X": covariates(name, S), "pl": [idx.player(m) for m in who],
               "pos": [idx.position(group_of(pos, s, w, m)) for s, w, m in zip(S.season, S.week, who)], "ps": [idx.pair(m, se) for m, se in zip(who, S.season)],
               "df": [idx.defense(t, se) for t, se in zip(S.defteam, S.season)]}


def eligible_receivers(onf, passer, pos, season, week, receiver):
    E_ = [m for m in onf if m != passer and group_of(pos, season, week, m) in ("QB", "RB", "FB", "WR", "TE")]
    if receiver is not None and receiver not in E_: E_.append(receiver)   # a reported-eligible lineman: his report has no column; his target says he was eligible
    return E_


def eligible_rushers(onf, pos, season, week, rusher):
    E_ = [m for m in onf if group_of(pos, season, week, m) in RUSH_ELIGIBLE]
    if rusher is not None and rusher not in E_: E_.append(rusher)
    return E_


def collapse(obs, keys, sum_keys=()):
    """Collapse identical observation rows: rows equal on every key (and every covariate column) become one row with weight w (and summed sum_keys)."""
    n = len(obs["y"]); X = np.asarray(obs["X"], dtype=float).reshape(n, -1)
    cols = {k: np.asarray(obs[k]) for k in keys} | {f"x{j}": X[:, j] for j in range(X.shape[1])}
    df = pd.DataFrame(cols); df["w"] = 1.0
    for k in sum_keys: df[k] = np.asarray(obs[k])
    g = df.groupby(list(cols), sort=False, dropna=False)
    agg = g.agg({"w": "sum", **{k: "sum" for k in sum_keys}}).reset_index()
    out = {k: agg[k].to_numpy() for k in keys} | {k: agg[k].to_numpy() for k in sum_keys} | {"w": agg.w.to_numpy(float), "X": agg[[f"x{j}" for j in range(X.shape[1])]].to_numpy(float).reshape(len(agg), -1)}
    for k in ("pl", "pl2", "pos", "ps", "df", "pg", "y", "lo", "hi", "n"):
        if k in out: out[k] = out[k].astype(int)
    return out


def obs_dirmult(E, pos, idx, name, counts):
    """One group per team-game for an allocation kind: the players on the field for at least one of the kind's snaps (eligible groups) plus every
    actual taker, each with his takes y and his exposure off = log(on-field snaps of the kind, at least one). Snaps with an unknown on-field set
    add to the takes but not to the exposure (counted)."""
    if name == "target": S = E[E.kind.eq(rules.PASS) & E.receiver.notna()]; who = "receiver"; ok_groups = ("QB", "RB", "FB", "WR", "TE")
    else: S = E[E.kind.eq(rules.RUN) & E.rusher.notna()]; who = "rusher"; ok_groups = RUSH_ELIGIBLE
    counts[f"{name}_snaps_with_unknown_on_field_set"] = int(S.onf.isna().sum())
    start, ln, y, off, pl, ps, pr, df = [], [], [], [], [], [], [], []; n_groups = 0
    for (season, gid, team, week), d in S.groupby(["season", "game_id", "posteam", "week"], sort=False):
        onf = {}; takes = {}
        for st, m in zip(d.onf, d[who]):
            takes[m] = takes.get(m, 0) + 1
            if st is not None:
                for x in st:
                    if m == x or group_of(pos, season, week, x) in ok_groups: onf[x] = onf.get(x, 0) + 1
        players = sorted(set(onf) | set(takes)); opp = d.defteam.iloc[0]
        if len(players) <= 1: continue
        start.append(len(pl) + 1); ln.append(len(players)); n_groups += 1
        for m in players:
            y.append(takes.get(m, 0)); off.append(float(np.log(max(onf.get(m, 0), 1)))); pl.append(idx.player(m)); ps.append(idx.position(group_of(pos, season, week, m)))
            pr.append(idx.pair(m, season)); df.append(idx.defense(opp, season))
    return n_groups, {"N": n_groups, "M": len(pl), "start": start, "len": ln, "y": y, "off": off, "X": np.zeros((len(pl), 0)), "pl": pl, "pos": ps, "ps": pr, "df": df}


def obs_softmax(E, pos, idx, name, counts):
    """Ragged candidate rows for one allocation: target (eligible receivers on the field, minus the passer), rusher (eligible players on the field),
    passer (players at QB on the field). Snaps with an unknown on-field set carry no risk set and are counted, not used."""
    if name == "target": S = E[E.kind.eq(rules.PASS) & E.receiver.notna()]
    elif name == "rusher": S = E[E.kind.eq(rules.RUN) & E.rusher.notna()]
    else: S = E[E.kind.isin(rules.DROPBACK) & E.passer.notna()]
    unknown = int(S.onf.isna().sum()); counts[f"{name}_snaps_with_unknown_on_field_set"] = unknown; S = S[S.onf.notna()]
    start, ln, chosen, pl, ps, pr, df, pg = [], [], [], [], [], [], [], []; n_used = 0; singletons = 0
    for r in S.itertuples(index=False):
        if name == "target": cand = eligible_receivers(r.onf, r.passer, pos, r.season, r.week, r.receiver); who = r.receiver
        elif name == "rusher": cand = eligible_rushers(r.onf, pos, r.season, r.week, r.rusher); who = r.rusher
        else:
            cand = [m for m in r.onf if group_of(pos, r.season, r.week, m) == "QB"]; who = r.passer
            if who not in cand: cand.append(who)
        if len(cand) <= 1: singletons += 1; continue
        start.append(len(pl) + 1); ln.append(len(cand)); chosen.append(len(pl) + 1 + cand.index(who)); n_used += 1
        for m in cand:
            pl.append(idx.player(m)); ps.append(idx.position(group_of(pos, r.season, r.week, m))); pr.append(idx.pair(m, r.season)); df.append(idx.defense(r.defteam, r.season)); pg.append(0)
    counts[f"{name}_snaps_with_one_candidate"] = singletons
    return n_used, {"N": n_used, "M": len(pl), "start": start, "len": ln, "chosen": chosen, "X": np.zeros((len(pl), 0)), "pl": pl, "pos": ps, "ps": pr, "df": df, "pg": pg}


# ----------------------------------------------------------------------------------------------------------------------------- tables
@dataclasses.dataclass
class Table:
    """A conjugate posterior over categories per context: Dirichlet(alpha) with alpha = prior pseudo-count + counts (a Beta when C = 2)."""
    name: str
    categories: list
    contexts: list
    alpha: np.ndarray        # (n_ctx, C)
    n_obs: int

    def draw(self, rng, W):
        """(W, n_ctx, C) probability vectors: one posterior draw per world (parameter uncertainty carried into the worlds)."""
        out = np.empty((W, len(self.contexts), len(self.categories)))
        for c in range(len(self.contexts)): out[:, c, :] = rng.dirichlet(self.alpha[c], size=W)
        return out

    def ctx(self, key):
        return self.contexts.index(key)


def make_table(name, cats, ctxs, pairs, pseudo):
    """pairs: iterable of (context, category) observations. Categories outside cats are counted and dropped by the caller."""
    cats = list(cats); ctxs = list(ctxs); A = np.full((len(ctxs), len(cats)), float(pseudo)); n = 0
    ci = {c: i for i, c in enumerate(cats)}; xi = {c: i for i, c in enumerate(ctxs)}
    for x, c in pairs:
        if x in xi and c in ci: A[xi[x], ci[c]] += 1; n += 1
    return Table(name, cats, ctxs, A, n)


def next_start(E):
    """For each event, the yardline_100 of the other side's next scrimmage snap in the game (NaN when none): where a kick or turnover put the ball."""
    out = np.full(len(E), np.nan); gids = E.game_id.to_numpy(); kinds = E.kind.to_numpy(); teams = E.posteam.to_numpy(); yl = E.yardline_100.to_numpy(float)
    nxt = {}; nxt_any = np.nan; cur = None
    for i in range(len(E) - 1, -1, -1):   # backward scan: nxt[team] = yardline of the nearest following scrimmage snap by team (per game)
        if gids[i] != cur: nxt = {}; nxt_any = np.nan; cur = gids[i]
        if kinds[i] == rules.KICKOFF: out[i] = nxt_any                     # the receiving side is whoever snaps next (the file's posteam convention is not relied on)
        else: out[i] = next((v for t, v in nxt.items() if t != teams[i]), np.nan)
        if kinds[i] in rules.SCRIMMAGE: nxt[teams[i]] = yl[i]; nxt_any = yl[i]
    return out


def build_tables(E, pos, pseudo, counts):
    """Every non-player sub_model as a conjugate table from the admitted events."""
    T = {}; S = E[E.kind.isin(rules.SCRIMMAGE)]
    dc = down_class(S.down)
    # personnel groups: the participation file's recorded personnel string (rules.personnel_counts); where absent or unparseable, the roster positions
    # of the known on-field set (counted); legal only when they sum to 11 (Rule 5-1-1)
    pairs = {"recorded": [], "roster": []}; names = {"recorded": [], "roster": []}; illegal = 0
    for r in S[S.onf.notna() | S.pers.notna()].itertuples(index=False):
        g = rules.personnel_counts(r.pers) if r.pers is not None else None; src = "recorded"
        if g is None:
            if r.onf is None: continue
            g = {k: 0 for k in PERSONNEL_GROUPS}; src = "roster"
            for m in r.onf: g[group_of(pos, r.season, r.week, m)] += 1
        if sum(g.values()) != K.ON_FIELD: illegal += 1; continue
        name = "-".join(f"{k}{g[k]}" for k in PERSONNEL_GROUPS); names[src].append(name); pairs[src].append((DOWN_CLASS[down_class(r.down)], name))
    counts["personnel_sets_not_eleven"] = illegal; counts["personnel_recorded_snaps"] = len(pairs["recorded"]); counts["personnel_roster_derived_snaps"] = len(pairs["roster"])
    # two tables, two sources: the recorded personnel string is the measurement; the roster-derived composition is a different, weaker measurement and
    # is used only when the record holds no recorded personnel at all (counts["personnel_source"] names which)
    T["personnel_recorded"] = make_table("personnel_recorded", sorted(set(names["recorded"])), DOWN_CLASS, pairs["recorded"], pseudo)
    T["personnel_roster"] = make_table("personnel_roster", sorted(set(names["roster"])), DOWN_CLASS, pairs["roster"], pseudo)
    src = "recorded" if T["personnel_recorded"].n_obs else "roster"; counts["personnel_source"] = src
    T["personnel"] = T[f"personnel_{src}"]
    # fourth down: go / punt / field goal
    F = E[E.down.eq(4) & E.kind.isin(list(rules.SCRIMMAGE) + [rules.PUNT, rules.FIELD_GOAL])]
    ctxs = [(a, b) for a in range(K.FIELD_YARDS // YARD_BIN) for b in range(len(TOGO_BINS))]
    T["fourth"] = make_table("fourth", FOURTH_CATS, ctxs, zip(zip(yard_bin(F.yardline_100), togo_bin(F.ydstogo)), np.where(F.kind.isin(rules.SCRIMMAGE), "go", F.kind)), pseudo)
    # field goals by distance bin
    G = E[E.kind.eq(rules.FIELD_GOAL) & E.field_goal_result.notna()]
    T["fg_make"] = make_table("fg_make", ["made", "missed"], list(range(len(FG_BINS))), zip(fg_bin(G.yardline_100), np.where(G.field_goal_result.eq("made"), "made", "missed")), pseudo)
    # kicks and turnovers: where the other side's next drive starts (its yardline_100, 5-yard bins)
    ns = next_start(E); E_next_start = E.assign(ns=ns); bins = list(range(K.FIELD_YARDS // YARD_BIN))
    ko = E_next_start[E_next_start.kind.eq(rules.KICKOFF) & E_next_start.ns.notna()]
    prev_safety = E_next_start.groupby("game_id").safety.shift(1).fillna(0)
    ko_ctx = np.where(prev_safety[ko.index].eq(1), "safety_kick", "kickoff")
    T["kick_start"] = make_table("kick_start", bins, ["kickoff", "safety_kick"], zip(ko_ctx, yard_bin(ko.ns)), pseudo)
    pu = E_next_start[E_next_start.kind.eq(rules.PUNT) & E_next_start.ns.notna()]
    T["punt_start"] = make_table("punt_start", bins, list(range(K.FIELD_YARDS // PUNT_CTX_BIN)), zip(np.clip(pu.yardline_100.to_numpy(int) // PUNT_CTX_BIN, 0, 9), yard_bin(pu.ns)), pseudo)
    to = E_next_start[(E_next_start.interception.eq(1) | E_next_start.fumble_lost.eq(1)) & E_next_start.ns.notna() & E_next_start.kind.isin(rules.SCRIMMAGE)]
    T["turnover_start"] = make_table("turnover_start", bins, ["interception", "fumble"], zip(np.where(to.interception.eq(1), "interception", "fumble"), yard_bin(to.ns)), pseudo)
    # clock: seconds elapsed before a snap by the previous play's class and the hurry state
    C_ = S[S.elapsed_before.notna() & S.prior_class.notna() & (S.elapsed_before >= 0)]
    hu = hurry(C_.half, C_.seconds, C_.score_diff)
    ctxs = [(c, h) for c in rules.CLOCK_CLASSES for h in (False, True)]
    T["elapsed"] = make_table("elapsed", list(range(ELAPSED_CAP + 1)), ctxs, zip(zip(C_.prior_class, hu), np.minimum(C_.elapsed_before.to_numpy(int), ELAPSED_CAP)), pseudo)
    # penalties: a flagged no-play among snaps, by down class; its enforcement from the next same-team snap
    N_ = E[E.kind.isin(list(rules.SCRIMMAGE) + [rules.PENALTY])]
    T["penalty"] = make_table("penalty", ["play", "penalty"], DOWN_CLASS, zip([DOWN_CLASS[i] for i in down_class(N_.down.fillna(1))], np.where(N_.kind.eq(rules.PENALTY), "penalty", "play")), pseudo)
    pen = E[E.kind.eq(rules.PENALTY)]; nxt_yl = E.groupby(["game_id", "posteam"]).yardline_100.shift(-1); nxt_dn = E.groupby(["game_id", "posteam"]).down.shift(-1)
    kinds = []
    for i in pen.index:
        if pd.isna(nxt_yl.get(i)) or pd.isna(pen.yardline_100[i]): continue
        dy = int(nxt_yl[i] - pen.yardline_100[i])
        if dy in (5, 10, 15): kinds.append(("any", f"off:{dy}"))
        elif -dy in (5, 10, 15): kinds.append(("any", f"def:{-dy}:{'first' if nxt_dn.get(i) == 1 else 'repeat'}"))
    pen_cats = ["off:5", "off:10", "off:15", "def:5:repeat", "def:5:first", "def:10:first", "def:10:repeat", "def:15:first", "def:15:repeat"]
    T["penalty_kind"] = make_table("penalty_kind", pen_cats, ["any"], kinds, pseudo)
    # fumbles lost by event kind (a completion counts as the pass kind)
    FL = S[S.kind.isin([rules.RUN, rules.SCRAMBLE, rules.SACK]) | (S.kind.eq(rules.PASS) & S.complete.eq(1))]
    T["fumble"] = make_table("fumble", ["kept", "lost"], [rules.RUN, rules.SCRAMBLE, rules.SACK, rules.PASS], zip(FL.kind, np.where(FL.fumble_lost.eq(1), "lost", "kept")), pseudo)
    # safety on snaps from inside the own ten
    Z = S[S.yardline_100 >= SAFETY_ZONE]
    T["safety"] = make_table("safety", ["no", "safety"], ["zone"], zip(["zone"] * len(Z), np.where(Z.safety.eq(1), "safety", "no")), pseudo)
    # tries after a touchdown: two-point attempt or kick; the kick's result; the try's result
    TR = E[E.kind.eq(rules.TRY)]
    two = TR.two_point_conv_result.notna()
    T["two_attempt"] = make_table("two_attempt", ["kick", "two"], ["any"], zip(["any"] * len(TR), np.where(two, "two", "kick")), pseudo)
    T["xp_make"] = make_table("xp_make", ["good", "missed"], ["any"], zip(["any"] * int((~two).sum()), np.where(TR[~two].extra_point_result.eq("good"), "good", "missed")), pseudo)
    T["two_success"] = make_table("two_success", ["failure", "success"], ["any"], zip(["any"] * int(two.sum()), np.where(TR[two].two_point_conv_result.eq("success"), "success", "failure")), pseudo)
    # kneel decision inside the kneel state, by down class; kneel yards
    KS = S[kneel_state(S.half, S.seconds, S.score_diff)]
    T["kneel"] = make_table("kneel", ["play", "kneel"], DOWN_CLASS, zip([DOWN_CLASS[i] for i in down_class(KS.down)], np.where(KS.kind.eq(rules.KNEEL), "kneel", "play")), pseudo)
    KN = S[S.kind.eq(rules.KNEEL)]
    T["kneel_yards"] = make_table("kneel_yards", list(range(-5, 1)), ["any"], zip(["any"] * len(KN), np.clip(KN.yards_gained.to_numpy(int), -5, 0)), pseudo)
    # who receives the opening kickoff (home = 1)
    first = S.sort_values(["game_id", "seq"]).drop_duplicates("game_id")
    T["home_receives"] = make_table("home_receives", ["away", "home"], ["any"], zip(["any"] * len(first), np.where(first.posteam.eq(first.home_team), "home", "away")), pseudo)
    return T


# ----------------------------------------------------------------------------------------------------------------------------- stan backend
def _stan_data(program, obs, idx):
    pr = K.MODEL["priors"]; prev, dt, order = idx.chain()
    # Stan indexes pairs from 1: every 0-based pair code shifts by one, including the predecessor codes (0 = none stays 0)
    d = {"P": len(idx.players), "G": len(idx.positions), "J": len(idx.pairs), "j_prev": [p + 1 if p else 0 for p in prev], "j_dt": dt, "j_order": [j + 1 for j in order], "T": len(idx.defs),
         "group_sd_scale": pr["group_sd_scale"], "player_sd_scale": pr["player_sd_scale"], "season_sd_scale": pr["season_sd_scale"], "lambda_rate": pr["lambda_rate"],
         "defense_sd_scale": pr["defense_sd_scale"]}
    one = lambda a: [int(x) + 1 for x in a]
    rows = {"pl": one(obs["pl"]), "pos": one(obs["pos"]), "ps": one(obs["ps"]), "df": one(obs["df"])}
    if program == "softmax":
        d.update(rows | {"N": obs["N"], "M": obs["M"], "start": obs["start"], "len": obs["len"], "chosen": obs["chosen"], "K": obs["X"].shape[1], "X": np.asarray(obs["X"], dtype=float), "beta_sd": pr["beta_sd"]})
    elif program == "dirmult":
        d.update(rows | {"N": obs["N"], "M": obs["M"], "start": obs["start"], "len": obs["len"], "y": [int(v) for v in obs["y"]], "off": [float(v) for v in obs["off"]],
                         "log_kappa_mean": pr["log_kappa_mean"], "log_kappa_sd": pr["log_kappa_sd"]})
    else:
        d.update(rows | {"N": len(obs["y"]), "K": obs["X"].shape[1], "X": np.asarray(obs["X"], dtype=float), "intercept_sd": pr["intercept_sd"], "beta_sd": pr["beta_sd"], "y": [int(v) for v in obs["y"]]})
        w = [float(v) for v in obs.get("w", np.ones(len(obs["y"])))]
        if program == "binomial": d.update({"n": [int(v) for v in obs["n"]], "PG": len(idx.pgs), "pg": one(obs["pg"]), "game_sd_scale": pr["game_sd_scale"]})
        if program == "betabinomial": d.update({"n": [int(v) for v in obs["n"]], "log_phi_mean": pr["log_phi_mean"], "log_phi_sd": pr["log_phi_sd"]})
        if program == "categorical": d.update({"w": w, "C": obs["C"], "pl2": one(obs["pl2"])})
        if program == "gain": d.update({"w": w, "grainsize": K.MODEL["stan"]["grainsize"], "lo": [int(v) for v in obs["lo"]], "hi": [int(v) for v in obs["hi"]],
                                        "log_sigma_sd": pr["log_sigma_sd"], "nu_shape": pr["nu_shape"], "nu_rate": pr["nu_rate"], "nu_min": pr["nu_min"]})
    return d


def preflight(program, d, obs, idx):
    """Before sampling: every real field finite, every index in range, and the Stan linear predictor mirrored in numpy with finite random
    parameters is finite on every row. A failure names the field, the row and the row's (player, season) pair, so an INVALID_FIT says where
    the nan came from instead of Stan's observation number. Returns the counts it checked."""
    def pair_of(i):
        j = d["ps"][i] - 1; m, se = idx.pairs[j] if j < len(idx.pairs) else ("?", "?")
        prev, dt, order = idx.chain()
        return f"row {i} (Stan {i + 1}): player {idx.players[d['pl'][i] - 1]!r}, pair j={j} {(m, se)!r}, j_prev={prev[j]} dt={dt[j]}, position {idx.positions[d['pos'][i] - 1]!r}, defence {idx.defs[d['df'][i] - 1]!r}"
    bad = []
    for k, v in d.items():
        a = np.asarray(v, dtype=float) if k in ("X", "w", "off", "j_dt") and not isinstance(v, (int, float)) else None
        if a is not None and a.size and not np.isfinite(a).all():
            i = int(np.argwhere(~np.isfinite(a))[0][0]); bad.append(f"{k} non-finite first at row {i}: {np.asarray(v)[i]!r}; " + (pair_of(i) if k != "j_dt" else f"pair j={i} {idx.pairs[i]!r}"))
    ranges = {"pl": d["P"], "pos": d["G"], "ps": d["J"], "df": d["T"]} | ({"pg": d["PG"]} if "pg" in d else {}) | ({"pl2": d["P"]} if "pl2" in d else {})
    for k, hi in ranges.items():
        a = np.asarray(d[k], dtype=int)
        if a.size and (a.min() < 1 or a.max() > hi): bad.append(f"{k} index outside 1..{hi}: min {a.min()} max {a.max()}")
    prev, dt = np.asarray(d["j_prev"]), np.asarray(d["j_dt"], dtype=float); order = np.asarray(d["j_order"]) - 1
    if sorted(order.tolist()) != list(range(d["J"])): bad.append("j_order is not a permutation of the pairs")
    if (dt < 0).any(): bad.append(f"j_dt negative at pair {int(np.argwhere(dt < 0)[0][0])}")
    rng = np.random.default_rng(0); s = np.full(d["J"], np.nan); s[0] = 0.0; lam, tau = 0.7, 0.5
    for j in order[1:]:
        p = prev[j] - 1
        s[j] = (np.exp(-lam * dt[j]) * s[p] + tau * np.sqrt(1 - np.exp(-2 * lam * dt[j])) * rng.standard_normal()) if prev[j] > 0 else tau * rng.standard_normal()
    if not np.isfinite(s).all():
        j = int(np.argwhere(~np.isfinite(s))[0][0]); bad.append(f"season state nan at pair j={j} {idx.pairs[j]!r} (j_prev {prev[j]}, in order position {int(np.argwhere(order == j)[0][0])}): the chain reads a state before it is set")
    n_rows = len(d["pl"])
    if n_rows and not bad:
        eta = rng.standard_normal(d["G"])[np.asarray(d["pos"]) - 1] + rng.standard_normal(d["P"])[np.asarray(d["pl"]) - 1] + s[np.asarray(d["ps"]) - 1] + rng.standard_normal(d["T"])[np.asarray(d["df"]) - 1]
        if "X" in d and d["K"]: eta = eta + np.asarray(d["X"], dtype=float) @ rng.standard_normal(d["K"])
        if "pg" in d: eta = eta + rng.standard_normal(d["PG"])[np.asarray(d["pg"]) - 1]
        if not np.isfinite(eta).all():
            i = int(np.argwhere(~np.isfinite(eta))[0][0]); bad.append(f"linear predictor non-finite at {pair_of(i)}; X row {np.asarray(d['X'])[i].tolist() if d.get('K') else []}")
    if bad: raise ModelError(f"Stan {program} preflight: " + " | ".join(bad))
    return {"rows": n_rows, "pairs": d["J"], "players": d["P"], "defenses": d["T"]}


def fit_workers():
    """SubModels fitted concurrently: VERSION3_FIT_WORKERS, else cores // chains (each sub_model runs its chains in parallel already)."""
    w = os.environ.get("VERSION3_FIT_WORKERS")
    return max(1, int(w)) if w else max(1, (os.cpu_count() or 1) // K.MODEL["stan"]["chains"])


def compile_programs(programs):
    """Compile each Stan program once in the parent, so concurrent sub_model workers never race on the same executable."""
    import cmdstanpy
    for program in sorted(set(programs)):
        cmdstanpy.CmdStanModel(stan_file=str(HERE / K.MODEL["stan_dir"] / K.MODEL["programs"][program]), cpp_options={"STAN_THREADS": True} if program == "gain" else None)


def sample_stan(program, data, progress=True, workers=1):
    """One Stan run through CmdStanPy. Returns (draws, diagnostics). Raises ModelError when the sampler itself fails.
    progress: the per-chain bar (refreshed every 10 iterations; CmdStan's default of 100 leaves it at 1/N for most of a short fit).
    workers: how many sub_models share the machine, so the gain sub_model's reduce_sum threads do not oversubscribe it."""
    try:
        import cmdstanpy
    except ImportError as e:
        raise ModelError(f"cmdstanpy is not installed: {e}")
    cfg = K.MODEL["stan"]; stan_file = HERE / K.MODEL["stan_dir"] / K.MODEL["programs"][program]
    threads = cfg["threads_per_chain"] or max(1, (os.cpu_count() or 1) // (cfg["chains"] * max(1, workers)))
    try:
        mdl = cmdstanpy.CmdStanModel(stan_file=str(stan_file), cpp_options={"STAN_THREADS": True} if program == "gain" else None)
        fit = mdl.sample(data=data, chains=cfg["chains"], iter_warmup=cfg["warmup"], iter_sampling=cfg["sampling"], adapt_delta=cfg["adapt_delta"],
                         max_treedepth=cfg["max_treedepth"], seed=cfg["seed"], show_progress=progress and cfg.get("show_progress", True), show_console=False,
                         refresh=10, threads_per_chain=threads if program == "gain" else None)
    except Exception as e:
        raise ModelError(f"Stan {program}: {type(e).__name__}: {e}")
    draws = {}
    for v in VARIABLES[program]:
        try: draws[v] = np.asarray(fit.stan_variable(v))
        except Exception: draws[v] = np.zeros((cfg["chains"] * cfg["sampling"], 0))
    mv = fit.method_variables(); summ = fit.summary()
    div = int(np.asarray(mv["divergent__"]).sum()); td = float((np.asarray(mv["treedepth__"]) >= cfg["max_treedepth"]).mean())
    rhat = float(np.nanmax(summ["R_hat"].to_numpy())) if "R_hat" in summ.columns else float("nan")
    ess = float(np.nanmin(summ["ESS_bulk"].to_numpy())) if "ESS_bulk" in summ.columns else float("nan")
    # recorded, never gated: the sampler's geometry in its own numbers (iterations x chains arrays from method_variables)
    ess_tail = float(np.nanmin(summ["ESS_tail"].to_numpy())) if "ESS_tail" in summ.columns else float("nan")
    step = np.atleast_2d(np.asarray(mv["stepsize__"], dtype=float)); leap = np.atleast_2d(np.asarray(mv["n_leapfrog__"], dtype=float)); en = np.atleast_2d(np.asarray(mv["energy__"], dtype=float))
    if step.shape[0] == 1 and step.shape[1] != cfg["chains"]: step, leap, en = step.T, leap.T, en.T
    ebfmi = [float(np.var(np.diff(en[:, c])) / np.var(en[:, c])) if np.var(en[:, c]) > 0 else float("nan") for c in range(en.shape[1])]
    return draws, {"divergences": div, "treedepth_hit_frac": td, "rhat_max": rhat, "ess_bulk_min": ess, "cmdstanpy": cmdstanpy.__version__,
                   "cmdstan": cmdstanpy.cmdstan_version() if hasattr(cmdstanpy, "cmdstan_version") else None,
                   "stepsize_by_chain": [float(np.median(step[:, c])) for c in range(step.shape[1])], "n_leapfrog_mean": float(np.mean(leap)),
                   "ebfmi_by_chain": ebfmi, "ess_tail_min": ess_tail}


def judge_diagnostics(diag):
    cfg = K.MODEL["stan"]; why = []
    if diag["divergences"] > cfg["divergences_max"]: why.append(f"divergences {diag['divergences']}")
    if diag["treedepth_hit_frac"] > cfg["treedepth_hits_max_frac"]: why.append(f"treedepth hits {diag['treedepth_hit_frac']:.3f}")
    if not np.isfinite(diag["rhat_max"]) or diag["rhat_max"] > cfg["rhat_max"]: why.append(f"R_hat max {diag['rhat_max']}")
    if not np.isfinite(diag["ess_bulk_min"]) or diag["ess_bulk_min"] < cfg["ess_bulk_min"]: why.append(f"ESS_bulk min {diag['ess_bulk_min']}")
    return why


PRIOR_ONLY_OK = ("passer",)   # the passer's risk set is almost always one player: with no informative opportunity the posterior is the declared prior


def prior_draws(program, idx, rng):
    """Draws from the declared priors of a softmax program (the posterior when no opportunity informs it): the prior is proper and dimensioned."""
    pr = K.MODEL["priors"]; cfg = K.MODEL["stan"]; D = cfg["chains"] * cfg["sampling"]; P, G, J, T = len(idx.players), len(idx.positions), len(idx.pairs), len(idx.defs)
    half = lambda sd, *shape: np.abs(rng.normal(0, sd, shape))
    sigma_pos, sigma_m, tau = half(pr["group_sd_scale"], D), half(pr["player_sd_scale"], D), half(pr["season_sd_scale"], D)
    lam = rng.exponential(1 / pr["lambda_rate"], D); sigma_def = half(pr["defense_sd_scale"], D)
    a_pos = sigma_pos[:, None] * rng.standard_normal((D, G)); m = sigma_m[:, None] * rng.standard_normal((D, P)); a_pos[:, 0] = 0; m[:, 0] = 0
    prev, dt, order = idx.chain(); s = np.zeros((D, J))
    for j in order[1:]:   # every pair after its predecessor, whatever its code
        if prev[j]: rho = np.exp(-lam * dt[j]); s[:, j] = rho * s[:, prev[j]] + tau * np.sqrt(1 - rho ** 2) * rng.standard_normal(D)
        else: s[:, j] = tau * rng.standard_normal(D)
    v_def = sigma_def[:, None] * rng.standard_normal((D, T)); v_def[:, 0] = 0
    return {"beta": np.zeros((D, 0)), "sigma_pos": sigma_pos, "sigma_m": sigma_m, "tau": tau, "lambda": lam, "sigma_def": sigma_def, "a_pos": a_pos, "m": m, "s": s, "v_def": v_def}


def fit_one(name, program, obs, idx, cutoff, transform, n_obs, extra_index=None, progress=True, workers=1):
    """One typed fit of a mechanism."""
    index = idx.as_dict() | {"covariates": obs["X"].shape[1]} | (extra_index or {})
    base = dict(name=name, program=program, draws={}, index=index, transform=transform, diagnostics={}, n_obs=int(n_obs), cutoff_key=cutoff.fit_key(),
                model_version=K.MODEL_VERSION, provenance="")
    if n_obs < K.MODEL["min_obs"][program]:
        if name in PRIOR_ONLY_OK and program == "softmax":
            rng = np.random.default_rng(K.MODEL["stan"]["seed"])
            return FitResult(status=K.FIT_OK, **(base | {"draws": prior_draws(program, idx, rng), "diagnostics": {"prior_only": True},
                                                     "provenance": f"prior only: {n_obs} informative opportunities (risk sets of more than one player) < min_obs {K.MODEL['min_obs'][program]}; the posterior equals the declared prior"}))
        return FitResult(status=K.INSUFFICIENT_DATA, **(base | {"provenance": f"{n_obs} observations < min_obs {K.MODEL['min_obs'][program]}"}))
    try:
        d = _stan_data(program, obs, idx); pre = preflight(program, d, obs, idx)
        draws, diag = sample_stan(program, d, progress=progress, workers=workers)
    except ModelError as e:
        return FitResult(status=K.INVALID_FIT, **(base | {"provenance": str(e)}))
    why = judge_diagnostics(diag)
    return FitResult(status=K.INVALID_FIT if why else K.FIT_OK, **(base | {"draws": draws, "diagnostics": diag, "provenance": "; ".join(why) if why else f"Stan {program}, {n_obs} observations"}))


# ----------------------------------------------------------------------------------------------------------------------------- fit all
MECHANISMS = {"snap": "betabinomial", "call": "binomial", "branch": "categorical", "passer": "softmax", "target": "dirmult", "rusher": "dirmult",
              "result": "categorical", "td_pass": "binomial", "td_run": "binomial", "gain_pass": "gain", "gain_run": "gain", "gain_sack": "gain"}
NO_GAME_EFFECT = ("branch", "result", "td_pass", "td_run")   # pg = padding: no game-level effect in these sub_models (policy.MODEL["game_variation"])


@dataclasses.dataclass
class Fits:
    cutoff: K.Cutoff
    fits: dict
    tables: dict
    index: dict
    counts: dict

    def status(self):
        return {n: f.status for n, f in self.fits.items()}

    def all_ok(self):
        return all(f.ok() for f in self.fits.values())


def fit_all(cutoff, log=print):
    """Every mechanism from the cutoff's training view; persisted under _probe/fits/<model_version>/<cutoff key>/."""
    t0 = time.time(); E = record.training_events(cutoff); pos = position_lookup(cutoff); counts = {"training_events": len(E)}
    seasons = sorted(set(E.season.astype(int))) if len(E) else list(cutoff.admitted_seasons)
    idx = Index(seasons); fits = {}
    log(f"MODEL fit cutoff {cutoff.issue_time()} fit_week {cutoff.fit_week} seasons {seasons} events {len(E)}")
    pseudo = K.MODEL["tables"]["pseudo_count"]
    tables = build_tables(E, pos, pseudo, counts) if len(E) else {}
    done = load_sub_models(cutoff)   # sub_models this fit key already holds on disk: a resumed run refits nothing it finished
    if done: log(f"MODEL sub_models resumed from disk: {sorted(done)}")
    pending = []   # (name, program, obs, transform, n, extra) built in the parent, fitted concurrently below
    for name, program in MECHANISMS.items():
        if name in done: fits[name] = done[name]; continue
        if not len(E):
            fits[name] = fit_one(name, program, {"X": np.zeros((0, 0)), "y": []}, idx, cutoff, {}, 0); save_sub_model(cutoff, fits[name]); continue
        if name == "snap": _, obs = obs_snap(E, pos, idx, cutoff); n = len(obs["y"])
        elif name == "call": _, obs = obs_call(E, idx); n = len(obs["y"]); obs = collapse(obs, ("pl", "pos", "ps", "df", "pg"), sum_keys=("y", "n"))
        elif name == "branch": _, obs = obs_branch(E, pos, idx); obs["C"] = len(BRANCH_CATS); n = len(obs["y"])
        elif name == "result": _, obs = obs_result(E, pos, idx); obs["C"] = len(RESULT_CATS); n = len(obs["y"])
        elif name in ("td_pass", "td_run"): _, obs = obs_td(E, pos, idx, name); n = len(obs["y"])
        elif name.startswith("gain"): _, obs = obs_gain(E, pos, idx, name, counts); n = len(obs["y"])
        elif name == "passer": n, obs = obs_softmax(E, pos, idx, name, counts)
        else: n, obs = obs_dirmult(E, pos, idx, name, counts)
        if name in NO_GAME_EFFECT: obs["pg"] = [0] * len(obs["y"])
        if name in ("branch", "result"): C_ = obs.pop("C"); obs = collapse(obs, ("pl", "pl2", "pos", "ps", "df", "pg", "y")); obs["C"] = C_
        if name in ("td_pass", "td_run"): obs = collapse(obs, ("pl", "pos", "ps", "df", "pg"), sum_keys=("y", "n"))
        if name.startswith("gain"): obs = collapse(obs, ("pl", "pos", "ps", "df", "y", "lo", "hi"))
        counts[f"{name}_rows"] = len(obs["y"]) if "y" in obs else obs.get("M", 0); counts[f"{name}_observations"] = int(n)
        Xs, tr = standardize(obs["X"]); obs["X"] = Xs
        extra = {"categories": list(BRANCH_CATS) if name == "branch" else (list(RESULT_CATS) if name == "result" else None)}
        pending.append((name, program, obs, tr, n, extra))
    workers = min(fit_workers(), len(pending)) if pending else 1
    if pending:
        if workers > 1:
            try: compile_programs([p for _, p, *_ in pending])
            except ImportError as e: raise ModelError(f"cmdstanpy is not installed: {e}")
        log(f"MODEL fitting {len(pending)} sub_models, {workers} at a time ({'per-chain progress bars' if workers == 1 else 'one line per sub_model; VERSION3_FIT_WORKERS=1 for progress bars'})")
    if workers == 1:
        for name, program, obs, tr, n, extra in pending:
            t1 = time.time(); fits[name] = fit_one(name, program, obs, idx, cutoff, tr, n, extra); save_sub_model(cutoff, fits[name])
            log(f"MODEL {name:9s} {program:11s} n={n} {time.time() - t1:6.0f}s -> {fits[name].status} ({fits[name].provenance})")
    else:
        import concurrent.futures as cf
        started = {}
        with cf.ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {}
            for name, program, obs, tr, n, extra in pending:
                started[name] = time.time(); log(f"MODEL {name:9s} {program:11s} n={n} queued")
                futs[pool.submit(_fit_worker, name, program, obs, idx, cutoff, tr, n, extra, workers)] = name
            for fu in cf.as_completed(futs):
                name = futs[fu]; status, provenance = fu.result(); fits[name] = load_sub_model(cutoff, name, any_status=True)
                if fits[name] is None: raise ModelError(f"sub_model {name} reported {status} but is not on disk under {fits_dir(cutoff)}")
                log(f"MODEL {name:9s} {fits[name].program:11s} {time.time() - started[name]:6.0f}s -> {status} ({provenance})")
    out = Fits(cutoff, fits, tables, idx.as_dict(), counts | {"seconds": round(time.time() - t0, 1), "fit_workers": workers, "sub_models_resumed": sorted(done)})
    save_fits(out); return out


def fits_dir(cutoff):
    return FITS / K.MODEL_VERSION / cutoff.fit_key()


def _fit_worker(name, program, obs, idx, cutoff, tr, n, extra, workers):
    """One sub_model in a pool process: fits, writes its own result to disk (the draws never travel back through a pipe) and returns only
    (status, provenance). Prints its own start so the terminal shows which sub_model each block of CmdStan lines belongs to."""
    print(f"MODEL {name:9s} sampling started (pid {os.getpid()})", flush=True)
    f = fit_one(name, program, obs, idx, cutoff, tr, n, extra, False, workers)
    save_sub_model(cutoff, f); return f.status, f.provenance


def load_sub_model(cutoff, name, any_status=False):
    """One sub_model from disk for this fit key and model version, or None. Without any_status only FIT_OK / INSUFFICIENT_DATA count as done
    (an INVALID_FIT, a sampler or environment failure, is refitted)."""
    d = fits_dir(cutoff)
    if not ((d / f"{name}.json").exists() and (d / f"{name}.npz").exists()): return None
    m = json.loads((d / f"{name}.json").read_text())
    if m.get("model_version") != K.MODEL_VERSION or m.get("cutoff_key") != cutoff.fit_key(): return None
    if not any_status and m.get("status") not in (K.FIT_OK, K.INSUFFICIENT_DATA): return None
    z = np.load(d / f"{name}.npz"); return FitResult(draws={k: z[k] for k in z.files}, **m)


def save_sub_model(cutoff, f):
    """One sub_model's typed result, written the moment it finishes (draws + metadata); fits.json marks the set complete."""
    d = fits_dir(cutoff); d.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(d / f"{f.name}.npz", **{k: v for k, v in f.draws.items()})
    (d / f"{f.name}.json").write_text(json.dumps({k: v for k, v in dataclasses.asdict(f).items() if k != "draws"}, default=str))


def load_sub_models(cutoff):
    """SubModels already on disk for this fit key and model version (an interrupted fit_all resumes from them)."""
    d = fits_dir(cutoff); out = {}
    for name in MECHANISMS:
        if (d / f"{name}.json").exists() and (d / f"{name}.npz").exists():
            m = json.loads((d / f"{name}.json").read_text())
            if m.get("model_version") == K.MODEL_VERSION and m.get("cutoff_key") == cutoff.fit_key() and m.get("status") in (K.FIT_OK, K.INSUFFICIENT_DATA):   # an INVALID_FIT (sampler or environment failure) is refitted
                z = np.load(d / f"{name}.npz"); out[name] = FitResult(draws={k: z[k] for k in z.files}, **m)
    return out


def save_fits(F):
    d = fits_dir(F.cutoff); d.mkdir(parents=True, exist_ok=True)
    for f in F.fits.values(): save_sub_model(F.cutoff, f)
    for name, t in F.tables.items():
        np.savez_compressed(d / f"table_{name}.npz", alpha=t.alpha)
        (d / f"table_{name}.json").write_text(json.dumps({"categories": t.categories, "contexts": t.contexts, "n_obs": t.n_obs}, default=str))
    (d / "fits.json").write_text(json.dumps({"cutoff": dataclasses.asdict(F.cutoff), "index": F.index, "counts": F.counts, "status": F.status()}, default=str))


def load_fits(cutoff):
    d = fits_dir(cutoff)
    if not (d / "fits.json").exists(): return None
    meta = json.loads((d / "fits.json").read_text()); fits = {}; tables = {}
    for name in MECHANISMS:
        m = json.loads((d / f"{name}.json").read_text()); z = np.load(d / f"{name}.npz")
        fits[name] = FitResult(draws={k: z[k] for k in z.files}, **m)
    for p in d.glob("table_*.json"):
        name = p.stem[len("table_"):]; m = json.loads(p.read_text()); z = np.load(d / f"table_{name}.npz")
        cats = [tuple(c) if isinstance(c, list) else c for c in m["categories"]]; ctxs = [tuple(c) if isinstance(c, list) else c for c in m["contexts"]]
        tables[name] = Table(name, cats, ctxs, z["alpha"], m["n_obs"])
    return Fits(cutoff, fits, tables, meta["index"], meta["counts"])


def load_or_fit(cutoff, log=print):
    F = load_fits(cutoff)
    if F is not None:
        log(f"MODEL fits loaded for {cutoff.issue_time()} ({fits_dir(cutoff).name})"); return F
    return fit_all(cutoff, log)


# ----------------------------------------------------------------------------------------------------------------------------- prediction
def player_effects(f, dsel, players, groups, season, rng, with_game=True):
    """Per-world effects of a fit for the listed players: (W, M) for a scalar sub_model or (W, M, C-1) for a categorical one.
    m: the player's persistent effect (a newcomer draws from the population N(0, sigma_m)); s: his season state from the fit's sparse (player, season)
    pairs, propagated by the AR(1) with fresh noise from his latest earlier pair when this season holds no pair (stationary N(0, tau) with none);
    a_pos by his position group; g: a fresh per-world game effect N(0, sigma_g) when the fit carries one (with_game)."""
    D = f.D; W = len(dsel); M = len(players); cat = f.draws["m"].ndim == 3; C1 = f.draws["m"].shape[2] if cat else 1; sh = (W, M, C1)
    key_of = lambda x: tuple(x) if isinstance(x, list) else x
    pl_idx = {key_of(m_): i for i, m_ in enumerate(f.index["players"])}; ps_idx = {g: i for i, g in enumerate(f.index["positions"])}
    pairs = {(key_of(x[0]), int(x[1])): j for j, x in enumerate(f.index["pairs"])}
    by_player = {}
    for (m_, se_), j in pairs.items():
        if j: by_player.setdefault(m_, []).append((se_, j))
    m_d = f.draws["m"].reshape(D, -1, C1); s_d = f.draws["s"].reshape(D, -1, C1); a_d = f.draws["a_pos"].reshape(D, -1, C1)
    sigma_m = f.draws["sigma_m"].reshape(D, C1); tau = f.draws["tau"].reshape(D, C1); lam = f.draws["lambda"].reshape(D)
    meff = np.zeros(sh); seff = np.zeros(sh); aeff = np.zeros(sh); pos_i = np.array([ps_idx.get(g, 0) for g in groups])
    for j, player in enumerate(players):
        key = player if not isinstance(player, tuple) else player
        aeff[:, j] = a_d[dsel, pos_i[j]]; k = pl_idx.get(key, 0)
        if k > 0:
            meff[:, j] = m_d[dsel, k]
            if (key, season) in pairs: seff[:, j] = s_d[dsel, pairs[(key, season)]]
            else:
                earlier = [(se_, jj) for se_, jj in by_player.get(key, []) if se_ < season]
                if earlier:
                    se0, j0 = max(earlier); rho = np.exp(-lam[dsel] * (season - se0))[:, None]
                    seff[:, j] = rho * s_d[dsel, j0] + tau[dsel] * np.sqrt(1 - rho ** 2) * rng.standard_normal((W, C1))
                else: seff[:, j] = tau[dsel] * rng.standard_normal((W, C1))
        else:
            meff[:, j] = sigma_m[dsel] * rng.standard_normal((W, C1)); seff[:, j] = tau[dsel] * rng.standard_normal((W, C1))
    geff = np.zeros(sh)
    if with_game and "sigma_g" in f.draws and f.draws["sigma_g"].size: geff = f.draws["sigma_g"].reshape(D, C1)[dsel][:, None, :] * rng.standard_normal(sh)
    eta = meff + seff + aeff + geff
    return {"eta": eta if cat else eta[:, :, 0], "m": meff, "s": seff, "a": aeff, "g": geff}


def defense_effect(f, dsel, team, season, rng):
    """Per-world v_def of the opponent's defence team-season: (W,) or (W, C-1); an unseen team-season draws from N(0, sigma_def)."""
    W = len(dsel); cat = f.draws["m"].ndim == 3; C1 = f.draws["m"].shape[2] if cat else 1
    v = f.draws.get("v_def"); sd = f.draws.get("sigma_def")
    if v is None or v.size == 0: return np.zeros((W, C1)) if cat else np.zeros(W)
    v = v.reshape(f.D, -1, C1); defs = {(x[0], int(x[1])): j for j, x in enumerate(f.index["defenses"])}; j = defs.get((team, int(season)), 0)
    out = v[dsel, j] if j else sd.reshape(f.D, C1)[dsel] * rng.standard_normal((W, C1))
    return out if cat else out[:, 0]


def intercept(f, dsel):
    a = f.draws.get("alpha"); return np.zeros(len(dsel)) if a is None or a.size == 0 else (a[dsel] if a.ndim == 1 else a[dsel])


def beta(f, dsel):
    b = f.draws.get("beta"); return b[dsel] if b is not None and b.size else None


def xb(f, dsel, Xraw):
    """X beta per world for raw covariate rows (standardised with the fit's training transform). Xraw: (W, K) -> (W,) or (W, C-1)."""
    b = beta(f, dsel); cat = f.draws["m"].ndim == 3
    if b is None or b.size == 0 or Xraw.shape[1] == 0: return np.zeros((len(dsel), f.draws["m"].shape[2])) if cat else np.zeros(len(dsel))
    Xs, _ = standardize(Xraw, f.transform)
    return np.einsum("wk,wk->w", Xs, b) if b.ndim == 2 else np.einsum("wk,wkc->wc", Xs, b)


def sample_gain(rng, mu, sigma, nu, lo, hi):
    """Vectorised draw from the discretised Student-t restricted to [lo, hi]: the continuous variable truncated to [lo - 0.5, hi + 0.5) then
    rounded, which is exactly q(y) / sum_L q(v). Where lo > hi the support is empty and the caller must not ask."""
    mu = np.asarray(mu, float); sigma = np.asarray(sigma, float); nu = np.asarray(nu, float); lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    a = stats.t.cdf((lo - 0.5 - mu) / sigma, nu); b = stats.t.cdf((hi + 0.5 - mu) / sigma, nu)
    u = a + rng.random(mu.shape) * np.maximum(b - a, 1e-300)
    y = np.rint(mu + sigma * stats.t.ppf(np.clip(u, 1e-15, 1 - 1e-15), nu))
    return np.clip(y, lo, hi).astype(int)


def gain_params(f, dsel, players, groups, season, rng):
    """Per world per player (mu without covariates, sigma, nu) for a gain fit."""
    pe = player_effects(f, dsel, players, groups, season, rng, with_game=False)
    ps_idx = {g: i for i, g in enumerate(f.index["positions"])}; pos_i = np.array([ps_idx.get(g, 0) for g in groups])
    ls = f.draws["ls0"][dsel][:, None] + f.draws["ls_pos"][dsel][:, pos_i]
    return {"mu0": intercept(f, dsel)[:, None] + pe["eta"], "sigma": np.exp(ls), "nu": f.draws["nu"][dsel]}


def softmax_draw(rng, eta, mask):
    """One choice per row of eta (W, M) among mask (W, M) True entries by the Gumbel-max trick; rows with no eligible entry return -1."""
    g = eta + rng.gumbel(size=eta.shape); g = np.where(mask, g, -np.inf)
    out = g.argmax(axis=1); out[~mask.any(axis=1)] = -1
    return out


def gumbel_topk(rng, logw, mask, k):
    """(W, M) boolean: for each row, the k[w] highest logw + Gumbel among mask (sampling without replacement proportional to exp(logw))."""
    g = np.where(mask, logw + rng.gumbel(size=logw.shape), -np.inf)
    order = np.argsort(-g, axis=1); rank = np.empty_like(order); W, M = logw.shape
    rank[np.arange(W)[:, None], order] = np.arange(M)[None, :]
    return (rank < np.asarray(k)[:, None]) & mask


def categorical_draw(rng, probs):
    """probs (W, C) rows summing to 1 -> category index per row."""
    c = np.cumsum(probs, axis=1); u = rng.random(len(probs))[:, None]
    return np.minimum((u > c).sum(axis=1), probs.shape[1] - 1)


def injected_fit(name, program, idx, D, rng, C=2, sigma_m=0.5, tau=0.3, sigma_g=0.3, alpha=None, extra=None, categories=None):
    """A FitResult with declared posterior draws over an Index, for construction tests of the simulator and the reducer (not a fit of any record)."""
    P, G, J, T = len(idx.players), len(idx.positions), len(idx.pairs), len(idx.defs); C1 = (C - 1) if program == "categorical" else 1
    sq = lambda *s: rng.standard_normal(s); vec = lambda v: np.full((D, C1), v).squeeze() if C1 > 1 else np.full(D, v)
    draws = {"sigma_m": vec(sigma_m), "tau": vec(tau), "lambda": np.full(D, 0.5), "sigma_def": vec(0.2),
             "a_pos": sigma_m * (sq(D, G, C1) if C1 > 1 else sq(D, G)), "m": sigma_m * (sq(D, P, C1) if C1 > 1 else sq(D, P)),
             "s": tau * (sq(D, J, C1) if C1 > 1 else sq(D, J)), "v_def": 0.2 * (sq(D, T, C1) if C1 > 1 else sq(D, T)), "beta": np.zeros((D, 0)) if C1 == 1 else np.zeros((D, 0, C1))}
    for k in ("m", "a_pos", "s", "v_def"): draws[k][:, 0] = 0
    if program == "binomial": draws["sigma_g"] = vec(sigma_g)
    if program in ("binomial", "categorical", "gain", "betabinomial"): draws["alpha"] = vec(0.0 if alpha is None else alpha)
    if program == "betabinomial": draws["phi"] = np.full(D, 20.0)
    if program == "dirmult": draws["kappa"] = np.full(D, 20.0)
    if program == "categorical": draws["m2"] = np.zeros((D, P, C1)); draws["sigma_m2"] = np.zeros((D, C1))
    if program == "gain": draws["ls0"] = np.full(D, math.log(5.0)); draws["ls_pos"] = np.zeros((D, G)); draws["nu"] = np.full(D, 4.0)
    for k, v in (extra or {}).items(): draws[k] = v
    index = idx.as_dict() | {"covariates": 0, "categories": categories}
    return FitResult(name, K.FIT_OK, program, draws, index, {"mean": [], "sd": []}, {"injected": True}, 0, "injected", K.MODEL_VERSION, "injected draws for a construction test")
