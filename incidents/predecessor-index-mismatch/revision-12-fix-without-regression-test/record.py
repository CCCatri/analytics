"""record: the one reader of the raw files and the one authority for what was observed. Raw rows are immutable: every reader returns what the
files say, classified by rules, with the counts of what could not be placed and the fields the files lack. Nothing is filled or guessed.
Every raw file opened is fingerprinted in OPENED (the run_log's manifest reads it). Historical queries go through views that take a
policy.Cutoff; no reader hands out an unbounded pool to a fitter."""
import os, re, json, pathlib, hashlib
import numpy as np, pandas as pd
import policy as K
import rules


class DataGap(RuntimeError):
    """The record contradicts itself or something arrived that cannot be typed. Stop; never fill."""


RAW = pathlib.Path(os.environ.get("VERSION3_RAW", str(pathlib.Path(__file__).resolve().parent.parent / "nfl" / "data" / "raw")))
OPENED = {}
_CACHE = {}
REQUIRED = ["game_id", "season", "week", "home_team", "away_team", "posteam", "defteam", "play_id", "play_type", "two_point_attempt", "pass", "rush",
            "sack", "qb_scramble", "passer_player_id", "receiver_player_id", "rusher_player_id", "complete_pass", "incomplete_pass", "interception",
            "fumble_lost", "yards_gained", "pass_touchdown", "rush_touchdown", "touchdown", "td_team", "yardline_100", "down", "ydstogo", "qtr",
            "game_seconds_remaining", "fixed_drive", "penalty", "home_score", "away_score", "total_home_score", "total_away_score",
            "extra_point_result", "two_point_conv_result", "field_goal_result", "safety", "defensive_two_point_conv", "defensive_extra_point_conv"]
OPTIONAL = ["lateral_receiver_player_id", "lateral_receiving_yards", "lateral_rusher_player_id", "lateral_rushing_yards", "out_of_bounds",
            "posteam_timeouts_remaining", "defteam_timeouts_remaining", "kick_distance", "return_yards", "quarter_seconds_remaining"]
NEED = {rules.PASS: ["passer_player_id", "complete_pass", "interception", "pass_touchdown", "yards_gained", "yardline_100", "down", "ydstogo"],
        rules.SACK: ["passer_player_id", "yards_gained", "yardline_100", "down", "ydstogo"],
        rules.SCRAMBLE: ["rusher_player_id", "yards_gained", "rush_touchdown", "yardline_100", "down", "ydstogo"],
        rules.RUN: ["rusher_player_id", "yards_gained", "rush_touchdown", "yardline_100", "down", "ydstogo"],
        rules.KNEEL: ["rusher_player_id", "yards_gained", "yardline_100", "down", "ydstogo"],
        rules.SPIKE: ["passer_player_id", "yardline_100", "down", "ydstogo"]}
EVENT_COLS = ["game_id", "season", "week", "home_team", "away_team", "posteam", "defteam", "play_id", "seq", "drive", "kind", "qtr", "half", "seconds",
              "game_seconds_remaining", "down", "ydstogo", "yardline_100", "yards_gained", "passer", "receiver", "rusher", "lateral_receiver",
              "lateral_rec_yards", "lateral_rusher", "lateral_rush_yards", "complete", "interception", "fumble_lost", "touchdown", "penalty",
              "play_type", "extra_point_result", "two_point_conv_result", "field_goal_result", "safety", "score_diff", "clock_class", "elapsed_before",
              "any_td", "td_team", "total_home_score", "total_away_score", "def_two", "def_xp"]
# Team identity aliases: a roster or injury-report code -> the play-by-play code of the same franchise. Applied only when the source code is not
# itself a play-by-play code of the season and the target is. Anything else stays unresolved.
TEAM_ALIASES = {"LAR": "LA", "WSH": "WAS", "JAC": "JAX", "SD": "LAC", "STL": "LA", "OAK": "LV", "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU"}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(K.POLICY["read_chunk"]), b""): h.update(chunk)
    return h.hexdigest()


def _read(name, **kw):
    path = RAW / name
    if not path.exists(): raise DataGap(f"record: {name} is not in {RAW}")
    if name not in OPENED: OPENED[name] = sha(path)
    return pd.read_csv(path, low_memory=False, **kw)


def _cached(key, build):
    if key not in _CACHE: _CACHE[key] = build()
    return _CACHE[key]


def seasons_on_disk():
    return sorted(int(m.group(1)) for p in RAW.glob("pbp_*.csv.gz") if (m := re.fullmatch(r"pbp_(\d+)\.csv\.gz", p.name)))


def data_version():
    """sha over the names and shas of every raw file: the data identity every cutoff and cache key carries."""
    h = hashlib.sha256()
    for p in sorted(RAW.iterdir()):
        if p.is_file(): h.update(p.name.encode()); h.update(sha(p).encode())
    return h.hexdigest()[: K.POLICY["print_hex"]]


def raw_pins():
    return {p.name: sha(p) for p in sorted(RAW.iterdir()) if p.is_file()}


def _pbp(season):
    def build():
        want = set(REQUIRED) | set(OPTIONAL)
        d = _read(f"pbp_{season}.csv.gz", usecols=lambda c: c in want)
        missing = sorted(set(REQUIRED) - set(d.columns))
        if missing: raise DataGap(f"record: pbp_{season} lacks required columns {missing}")
        return d, {"optional_columns_absent": sorted(set(OPTIONAL) - set(d.columns))}
    return _cached(("pbp", season), build)


def deficiencies(season):
    """Named input deficiencies of a season's raw files: fields the record would read but the file does not carry."""
    _, c = _pbp(season); out = dict(c)
    out["lateral_yards_absent"] = "lateral_receiving_yards" in c["optional_columns_absent"] or "lateral_rushing_yards" in c["optional_columns_absent"]
    out["out_of_bounds_absent"] = "out_of_bounds" in c["optional_columns_absent"]
    out["schedule_absent"] = schedule() is None; out["players_absent"] = players() is None
    out["participation_absent"] = not (RAW / f"pbp_participation_{season}.csv.gz").exists(); out["snaps_absent"] = not (RAW / f"snaps_{season}.csv.gz").exists()
    return out


SCHEDULE_COLS = list(K.PROJECTION_INPUTS["games.csv"])   # the allowlist: market columns are never read (policy.PROJECTION_INPUTS)


def schedule():
    """The canonical game record: raw/games.csv (one row per game, every season, pregame fields included). Absent: None (deficiency named)."""
    def build():
        if not (RAW / "games.csv").exists(): return None
        G = _read("games.csv", usecols=lambda c: c in set(SCHEDULE_COLS))
        if set(G.columns) & set(K.PROJECTION_INPUTS["excluded_permanently"]): raise DataGap("record: a permanently excluded market column was read")
        return G.copy()
    return _cached(("schedule",), build)


def games(season):
    """The season's games: the schedule's rows when the schedule exists (future games included, scores NaN until played), else the games the
    play-by-play holds. counts: games the play-by-play holds that the schedule lacks, and score disagreements between the two."""
    def build():
        S = schedule()
        if S is not None:
            G = S[S.season.eq(season)][["game_id", "season", "week", "home_team", "away_team", "home_score", "away_score"]].copy()
            if (RAW / f"pbp_{season}.csv.gz").exists():   # one franchise, one code: the play-by-play's (it carries relocated franchises under the current code)
                d, _ = _pbp(season); codes = set(d.home_team.dropna()) | set(d.away_team.dropna())
                for col in ("home_team", "away_team"): G[col] = G[col].map(lambda t: t if t in codes else TEAM_ALIASES.get(t, t))
            return G.sort_values(["week", "game_id"]).reset_index(drop=True)
        d, _ = _pbp(season)
        return d.drop_duplicates("game_id")[["game_id", "season", "week", "home_team", "away_team", "home_score", "away_score"]].sort_values(["week", "game_id"]).reset_index(drop=True)
    return _cached(("games", season), build)


def games_cross_check(season):
    d, _ = _pbp(season); pb = d.drop_duplicates("game_id")[["game_id", "home_score", "away_score"]]; S = schedule()
    if S is None: return {"schedule_absent": True}
    G = S[S.season.eq(season)]; j = pb.merge(G[["game_id", "home_score", "away_score"]], on="game_id", how="left", suffixes=("_pbp", "_sched"), indicator=True)
    codes = set(d.home_team.dropna()) | set(d.away_team.dropna()); recoded = sorted({t for t in set(G.home_team) | set(G.away_team) if t not in codes})
    return {"pbp_games_not_in_schedule": int(j._merge.ne("both").sum()), "schedule_games_without_pbp": int(len(G) - j._merge.eq("both").sum()),
            "score_disagreements": int(((j.home_score_pbp != j.home_score_sched) | (j.away_score_pbp != j.away_score_sched))[j._merge.eq("both")].sum()),
            "schedule_codes_resolved_to_pbp": {t: TEAM_ALIASES.get(t) for t in recoded}}


def season_team_codes(season):
    """The season's team identities: the schedule's home and away codes (known before any game), else the play-by-play's."""
    G = games(season); return set(G.home_team.dropna()) | set(G.away_team.dropna())


def events(season):
    """Every typed event of the season in play order, with its state fields, participants, outcome and clock class (rules.CLOCK_CLASSES),
    and the seconds elapsed before it (from the previous snap in the same half; NaN at a half's first snap). A scrimmage event with a null in a
    field its credits read is a DataGap: nothing is filled. Rows that are no event are counted, not kept."""
    def build():
        d, c = _pbp(season); d = d.sort_values(["game_id", "play_id"], kind="stable").reset_index(drop=True)
        kinds = np.array([rules.classify(r) for r in d.to_dict("records")], dtype=object)
        keep = np.array([k is not None for k in kinds]); e = d[keep].copy(); e["kind"] = kinds[keep]
        for col in OPTIONAL:
            if col not in e.columns: e[col] = np.nan
        for kind, cols in NEED.items():
            k = e[e.kind.eq(kind)]; bad = {c_: int(k[c_].isna().sum()) for c_ in cols if k[c_].isna().any()}
            if bad: raise DataGap(f"record: {season} {kind} events carry nulls {bad}; nothing is filled")
        e = e.rename(columns={"fixed_drive": "drive", "passer_player_id": "passer", "receiver_player_id": "receiver", "rusher_player_id": "rusher",
                              "lateral_receiver_player_id": "lateral_receiver", "lateral_receiving_yards": "lateral_rec_yards",
                              "lateral_rusher_player_id": "lateral_rusher", "lateral_rushing_yards": "lateral_rush_yards", "complete_pass": "complete"})
        e["seq"] = e.groupby("game_id").cumcount()
        e["half"] = np.where(e.qtr <= 2, 1, np.where(e.qtr <= 4, 2, 3))
        e["seconds"] = np.where(e.half.eq(1), e.game_seconds_remaining - K.HALF_SECONDS, e.game_seconds_remaining)   # seconds left in the half
        ot = e.half.eq(3); qsr = e.quarter_seconds_remaining if "quarter_seconds_remaining" in e.columns else e.game_seconds_remaining
        e.loc[ot, "seconds"] = qsr[ot].fillna(0).to_numpy()                                                    # OT: seconds left in the period
        off_td = e.touchdown.eq(1) & e.td_team.eq(e.posteam) & (e.pass_touchdown.eq(1) | e.rush_touchdown.eq(1))
        e["any_td"] = e.touchdown.fillna(0).astype(int); e["touchdown"] = off_td.astype(int)
        e["def_two"] = e.defensive_two_point_conv.fillna(0).astype(int); e["def_xp"] = e.defensive_extra_point_conv.fillna(0).astype(int)
        for col in ("complete", "interception", "fumble_lost", "penalty", "safety", "lateral_rec_yards", "lateral_rush_yards"):
            e[col] = e[col].fillna(0).astype(int)
        is_home = e.posteam.eq(e.home_team)
        e["score_diff"] = np.where(is_home, e.total_home_score - e.total_away_score, e.total_away_score - e.total_home_score)
        pre_home = e.groupby("game_id").total_home_score.shift(1).fillna(0); pre_away = e.groupby("game_id").total_away_score.shift(1).fillna(0)
        e["score_diff"] = np.where(is_home, pre_home - pre_away, pre_away - pre_home).astype(int)      # the score before the snap
        made_fg = e.field_goal_result.eq("made"); kick = e.kind.isin([rules.PUNT, rules.KICKOFF, rules.FIELD_GOAL, rules.TRY])
        change = e.interception.eq(1) | e.fumble_lost.eq(1)
        stopped = e.kind.eq(rules.PASS) & e.complete.eq(0) | e.kind.isin([rules.SPIKE, rules.PENALTY]) | e.out_of_bounds.fillna(0).eq(1)
        scoring = e.touchdown.eq(1) | made_fg | e.safety.eq(1)
        cls = np.select([scoring, change, kick, stopped, e.kind.eq(rules.PASS)], ["scoring", "change", "kick", "stopped", "complete_inbounds"], default="run_inbounds")
        e["clock_class"] = cls
        prev_sec = e.groupby(["game_id", "half"]).seconds.shift(1)
        e["elapsed_before"] = prev_sec - e.seconds
        e["prior_class"] = e.groupby(["game_id", "half"]).clock_class.shift(1)
        counts = {"rows": len(d), "events": len(e), "non_event_rows": int((~keep).sum()), "by_kind": e.kind.value_counts().to_dict(),
                  "tries": int(e.kind.eq(rules.TRY).sum()), **c}
        return e[EVENT_COLS + ["prior_class"]].reset_index(drop=True), counts
    return _cached(("events", season), build)


def snap_events(season):
    """Every event that is an offensive snap by the standard: the live scrimmage downs and the penalty no-plays the participation file shows an offensive unit on."""
    E, _ = events(season); P, _ = participation(season)
    pen = E[E.kind.eq(rules.PENALTY)].merge(P[["game_id", "play_id"]], on=["game_id", "play_id"], how="inner")
    return pd.concat([E[E.kind.isin(rules.SCRIMMAGE)], pen], ignore_index=True).sort_values(["game_id", "seq"]).reset_index(drop=True)


def scrimmage(season):
    E, _ = events(season); return E[E.kind.isin(rules.SCRIMMAGE)]


def event_objects(E):
    """rules.Event per row of an events frame, for the credit mapping."""
    out = []
    for r in E.itertuples(index=False):
        out.append(rules.Event(kind=r.kind, passer=r.passer if isinstance(r.passer, str) else None, receiver=r.receiver if isinstance(r.receiver, str) else None,
                               rusher=r.rusher if isinstance(r.rusher, str) else None, complete=int(r.complete), interception=int(r.interception),
                               touchdown=int(r.touchdown), yards=int(r.yards_gained) if pd.notna(r.yards_gained) else 0,
                               lateral_receiver=r.lateral_receiver if isinstance(r.lateral_receiver, str) else None, lateral_rec_yards=int(r.lateral_rec_yards),
                               lateral_rusher=r.lateral_rusher if isinstance(r.lateral_rusher, str) else None, lateral_rush_yards=int(r.lateral_rush_yards)))
    return out


def credits(season):
    """The official credits of every scrimmage event (rules.credits), one row per (game, play, player, stat)."""
    def build():
        S = scrimmage(season); rows = []
        for r, ev in zip(S[["game_id", "week", "posteam", "play_id"]].itertuples(index=False), event_objects(S)):
            for player, stat, inc in rules.credits(ev): rows.append((r.game_id, r.week, r.posteam, r.play_id, player, stat, inc))
        return pd.DataFrame(rows, columns=["game_id", "week", "posteam", "play_id", "player", "stat", "inc"])
    return _cached(("credits", season), build)


def official(season):
    """The official per-player-week stats (stats_<season>), columns named as policy.STATS; tds = receiving + rushing TDs."""
    def build():
        st = _read(f"stats_{season}.csv.gz")
        cols = {k: next((c for c in v if c in st.columns), None) for k, v in K.OFFICIAL.items()}
        miss = [k for k, v in cols.items() if v is None] + [c for c in ("player_id", "week") if c not in st.columns]
        if miss: raise DataGap(f"record: stats_{season} cannot name {miss}")
        S = st.groupby(["week", "player_id"])[list(cols.values())].sum().rename(columns={v: k for k, v in cols.items()})
        S["tds"] = S.rec_td + S.rush_td; S.index.names = ["week", "player"]
        return S.reset_index()
    return _cached(("official", season), build)


def replay_vs_official(season):
    """Historical replay: the record's credits summed per player-week against the official file, per stat: share of player-weeks agreeing, and
    the count of disagreeing player-weeks. A construction check of rules.credits against nflverse's own derivation; not a forecast measure."""
    C = credits(season); T = C.groupby(["week", "player", "stat"]).inc.sum().unstack(fill_value=0).reindex(columns=K.STATS, fill_value=0)
    S = official(season).set_index(["week", "player"])[K.STATS]
    M = T.join(S, how="inner", lsuffix="", rsuffix="_official")
    return {st: {"agree": float((M[st] == M[f"{st}_official"]).mean()), "disagree_rows": int((M[st] != M[f"{st}_official"]).sum()), "n": len(M)} for st in K.STATS}


def participation(season):
    """The participation file's offense players (and recorded personnel) on each scrimmage event, the side the play-by-play names. A row with more
    than 11 offensive players on a snap with no foul contradicts Rule 5-1-1 and is refused (counted); a file team code naming two sides is a DataGap.
    An absent file (held seasons) yields no rows and the deficiency participation_absent: every on-field set is unknown, never guessed."""
    def build():
        E, _ = events(season); S = E[E.kind.isin(list(rules.SCRIMMAGE) + [rules.PENALTY])][["game_id", "play_id", "posteam", "penalty", "kind"]]
        if not (RAW / f"pbp_participation_{season}.csv.gz").exists():
            return (pd.DataFrame(columns=["game_id", "play_id", "posteam", "kind", "offense_players", "offense_personnel", "n_offense"]),
                    {"participation_absent": True, "file_rows": 0, "rows_on_scrimmage_events": 0, "rows_refused_more_than_eleven_no_foul": 0, "rows_more_than_eleven_with_foul": 0,
                     "rows_fewer_than_eleven_legal": 0, "scrimmage_events_without_a_row": len(S), "rows_without_men": 0})
        P = _read(f"pbp_participation_{season}.csv.gz", usecols=lambda c: c in {"nflverse_game_id", "play_id", "possession_team", "offense_players", "offense_personnel", "n_offense"})
        if "offense_personnel" not in P.columns: P["offense_personnel"] = np.nan
        P = P.rename(columns={"nflverse_game_id": "game_id", "possession_team": "file_side"})
        j = P.merge(S, on=["game_id", "play_id"], how="inner"); live = j.kind.ne(rules.PENALTY)
        alias = j[live].dropna(subset=["file_side"]).groupby("file_side").posteam.unique(); two = {k: sorted(v) for k, v in alias.items() if len(v) != 1}
        if two: raise DataGap(f"record: participation {season}: a file team code names two play-by-play sides on live snaps {two}")
        # a no-play whose file side disagrees with the play-by-play's possession names the wrong unit: its participants are unknown, never guessed
        side_ok = live | j.file_side.isna() | j.file_side.eq(j.posteam); c_side = int((~side_ok).sum())
        j["snap"] = np.array([rules.is_offensive_snap(k, pr) for k, pr in zip(j.kind, j.offense_personnel)], dtype=bool) & side_ok.to_numpy()
        j = j[j.snap]   # the snap standard: live scrimmage downs and penalty no-plays with an offensive unit on the field; kick-formation no-plays are not offensive snaps
        false = (j.n_offense > K.ON_FIELD) & ~j.penalty.eq(1) & j.kind.ne(rules.PENALTY)
        dup = j.duplicated(["game_id", "play_id"], keep=False)
        if dup.any(): raise DataGap(f"record: participation {season} holds {int(dup.sum())} duplicated rows for one snap")
        c = {"participation_absent": False, "file_rows": len(P), "rows_on_scrimmage_events": len(j), "penalty_snaps_with_offensive_unit": int(j.kind.eq(rules.PENALTY).sum()),
             "no_play_rows_not_offensive_snaps": int(len(S[S.kind.eq(rules.PENALTY)]) - j.kind.eq(rules.PENALTY).sum()), "no_play_rows_with_file_side_disagreeing": c_side,
             "rows_refused_more_than_eleven_no_foul": int(false.sum()),
             "rows_more_than_eleven_with_foul": int(((j.n_offense > K.ON_FIELD) & j.penalty.eq(1)).sum()), "rows_fewer_than_eleven_legal": int((j.n_offense < K.ON_FIELD).sum()),
             "scrimmage_events_without_a_row": int(len(S[S.kind.ne(rules.PENALTY)]) - j.kind.ne(rules.PENALTY).sum()), "rows_without_men": int(j.offense_players.isna().sum()),
             "rows_without_personnel": int(j.offense_personnel.isna().sum())}
        return j[~false][["game_id", "play_id", "posteam", "kind", "offense_players", "offense_personnel", "n_offense"]].reset_index(drop=True), c
    return _cached(("part", season), build)


def personnel(season, E):
    """For each event of E (its order) the recorded personnel string of the participation file, or None."""
    P, _ = participation(season)
    j = E[["game_id", "play_id"]].merge(P[["game_id", "play_id", "offense_personnel"]], on=["game_id", "play_id"], how="left")
    return np.array([x if isinstance(x, str) else None for x in j.offense_personnel], dtype=object)


def on_field_sets(season, E):
    """For each event of E (its order) the frozenset of offense players the record names on it, or None where no legal row exists: unknown, never guessed."""
    P, _ = participation(season)
    j = E[["game_id", "play_id"]].merge(P[["game_id", "play_id", "offense_players"]], on=["game_id", "play_id"], how="left")
    if len(j) != len(E): raise DataGap(f"record: {season} participation holds duplicated rows for the events given")
    return np.array([frozenset(x for x in s.split(";") if x) if isinstance(s, str) else None for s in j.offense_players], dtype=object)


def final_drive(season):
    """Per (game_id, posteam): the team's actual final offensive drive, read from the play sequence alone: the drive id of its last scrimmage
    event; its scrimmage snaps; how many have a participation row (coverage). Identified before any participation join."""
    def build():
        S = scrimmage(season); last = S.groupby(["game_id", "posteam"]).seq.idxmax()
        fd = S.loc[last.to_numpy(), ["game_id", "posteam", "drive"]].rename(columns={"drive": "final_drive"})
        SN = snap_events(season); snaps = SN.merge(fd, on=["game_id", "posteam"]); snaps = snaps[snaps.drive.eq(snaps.final_drive)]
        sets = on_field_sets(season, snaps); snaps = snaps.assign(known=[s is not None for s in sets])
        cov = snaps.groupby(["game_id", "posteam"]).agg(snaps=("play_id", "size"), known=("known", "sum")).reset_index()
        return fd.merge(cov, on=["game_id", "posteam"]), snaps.assign(onf=list(sets))
    return _cached(("final_drive", season), build)


def finished(season):
    """(game_id, week, posteam, player, finish): TRUE if the player appears on a known snap of his side's actual final offensive drive; FALSE if every
    snap of that drive is known and he appears on none; UNKNOWN otherwise. Men considered: the week's roster of the team (any status) plus every
    player who appears in a participation set or a credit for that side in that game."""
    def build():
        fd, snaps = final_drive(season); C = credits(season); P, _ = participation(season); R = roster_raw(season); G = games(season)[["game_id", "week"]]
        seen = {}
        for r in snaps.itertuples(index=False):
            if r.onf is not None:
                for m in r.onf: seen.setdefault((r.game_id, r.posteam), set()).add(m)
        players = C[["game_id", "posteam", "player"]].drop_duplicates()
        e = P.dropna(subset=["offense_players"]); e = e.assign(player=e.offense_players.str.split(";")).explode("player"); e = e[e.player.str.len() > 0]
        players = pd.concat([players, e[["game_id", "posteam", "player"]]]).drop_duplicates().merge(G, on="game_id")
        codes = season_team_codes(season); Rr = R[R.gsis_id.notna()].assign(team=lambda x: x.team.map(lambda t: resolve_code(t, codes)))
        roster_men = Rr.dropna(subset=["team"])[["week", "team", "gsis_id"]].drop_duplicates().rename(columns={"team": "posteam", "gsis_id": "player"})
        sides = fd.merge(G, on="game_id")[["game_id", "week", "posteam", "snaps", "known"]]
        roster_men = roster_men.merge(sides[["game_id", "week", "posteam"]], on=["week", "posteam"])
        players = pd.concat([players, roster_men[["game_id", "posteam", "player", "week"]]]).drop_duplicates(["game_id", "posteam", "player"])
        players = players.merge(sides, on=["game_id", "week", "posteam"], how="left")
        on = np.array([m in seen.get((g, t), ()) for g, t, m in zip(players.game_id, players.posteam, players.player)])
        full = players.snaps.notna() & (players.known == players.snaps)
        players["finish"] = np.where(on, K.FINISH_TRUE, np.where(full, K.FINISH_FALSE, K.FINISH_UNKNOWN))
        c = {"finished_true": int(on.sum()), "finished_false": int((~on & full).sum()), "finished_unknown": int((~on & ~full).sum()),
             "sides": len(fd), "sides_with_full_final_drive_coverage": int((fd.known == fd.snaps).sum())}
        return players[["game_id", "week", "posteam", "player", "finish"]].reset_index(drop=True), c
    return _cached(("finished", season), build)


def played(season):
    """(game_id, week, posteam, player) for every player on the field on a scrimmage event or credited with one, in a game of the record."""
    def build():
        P, _ = participation(season); P = P.dropna(subset=["offense_players"])
        e = P.assign(player=P.offense_players.str.split(";")).explode("player"); e = e[e.player.str.len() > 0]
        C = credits(season)
        both = pd.concat([e[["game_id", "posteam", "player"]], C[["game_id", "posteam", "player"]]]).dropna().drop_duplicates()
        out = both.merge(games(season)[["game_id", "week"]], on="game_id", how="inner")
        return out[["game_id", "week", "posteam", "player"]].reset_index(drop=True), {"man_games_outside_record_games": len(both) - len(out)}
    return _cached(("played", season), build)


def official_by_game(season):
    """Every played player-game with his official stats for that week and his finish state (TRUE/FALSE/UNKNOWN). A played player the official file
    lists no row for recorded none (a count of no rows)."""
    def build():
        Pl, _ = played(season); S = official(season); Fn, _ = finished(season)
        dup = Pl.duplicated(["week", "player"], keep=False)
        if dup.any(): raise DataGap(f"record: {season} {int(dup.sum())} played rows put one player in two rows of one week; the weekly official stat cannot be split")
        j = Pl.merge(S, on=["week", "player"], how="left")
        for st in K.STATS: j[st] = j[st].fillna(0).astype(int)
        j = j.merge(Fn, on=["game_id", "week", "posteam", "player"], how="left"); j["finish"] = j.finish.fillna(K.FINISH_UNKNOWN)
        nz = (S[K.STATS].abs() > 0).any(axis=1)
        unplayed = S[nz][["week", "player"]].merge(Pl[["week", "player"]], how="left", indicator=True)._merge.eq("left_only")
        out = j.assign(season=season).sort_values(["player", "week", "game_id"]).reset_index(drop=True)
        return out, {"official_rows_for_men_not_played": int(unplayed.sum()), "played_man_games_by_finish": out.finish.value_counts().to_dict()}
    return _cached(("ogame", season), build)


def roster_raw(season):
    return _cached(("roster", season), lambda: _read(f"rosters_{season}.csv.gz",
                   usecols=lambda c: c in {"week", "team", "status", "gsis_id", "position", "full_name", "pfr_id"}))


def players():
    """players.csv: the identity bridge (gsis_id <-> pfr_id, position group). None when absent (deficiency named)."""
    def build():
        if not (RAW / "players.csv").exists(): return None
        return _read("players.csv", usecols=lambda c: c in {"gsis_id", "pfr_id", "position", "position_group", "display_name"})
    return _cached(("players",), build)


def snaps(season):
    """snaps_<season>: offense snaps per (game_id, player) from the snap-count file, keyed to gsis ids through players.csv. Both absent files are named."""
    def build():
        if not (RAW / f"snaps_{season}.csv.gz").exists(): return pd.DataFrame(columns=["game_id", "player", "offense_snaps"]), {"snaps_absent": True}
        S = _read(f"snaps_{season}.csv.gz", usecols=["game_id", "pfr_player_id", "team", "offense_snaps"]); PL = players()
        if PL is None: return pd.DataFrame(columns=["game_id", "player", "offense_snaps"]), {"snaps_absent": False, "players_absent": True, "rows": len(S)}
        j = S.merge(PL[["gsis_id", "pfr_id"]].dropna().drop_duplicates("pfr_id"), left_on="pfr_player_id", right_on="pfr_id", how="left")
        out = j.dropna(subset=["gsis_id"]).rename(columns={"gsis_id": "player"})[["game_id", "player", "offense_snaps"]].drop_duplicates(["game_id", "player"])
        return out.reset_index(drop=True), {"snaps_absent": False, "players_absent": False, "rows": len(S), "rows_without_gsis_id": int(j.gsis_id.isna().sum())}
    return _cached(("snaps", season), build)


def snaps_cross_check(season, frame=False):
    """Participation-derived offense snaps against the snap-count file, per player-game, on the file's own convention (live downs; nullified downs wiped):
    agreement share and disagreements. Participation and finishing use the rule standard (nullified downs count); this comparison does not.
    frame=True also returns the joined per-player-game frame (game_id, player, part_snaps, offense_snaps) so a check can injected_fault on a compared row."""
    Sn, c = snaps(season)
    if not len(Sn): return ({"compared": 0} | c, Sn.iloc[0:0]) if frame else {"compared": 0} | c
    P, _ = participation(season); P = P[P.kind.ne(rules.PENALTY)].dropna(subset=["offense_players"])   # the file's convention: live downs only (a nullified down is wiped)
    e = P.assign(player=P.offense_players.str.split(";")).explode("player"); e = e[e.player.str.len() > 0]
    mine = e.groupby(["game_id", "player"]).size().rename("part_snaps").reset_index()
    j = mine.merge(Sn, on=["game_id", "player"], how="inner")
    r = {"compared": len(j), "agree": float((j.part_snaps == j.offense_snaps).mean()) if len(j) else float("nan"), "disagree_rows": int((j.part_snaps != j.offense_snaps).sum()),
         "sum_abs_diff": int((j.part_snaps - j.offense_snaps).abs().sum()),
         "mean_abs_diff": float((j.part_snaps - j.offense_snaps).abs().mean()) if len(j) else float("nan")} | c
    return (r, j) if frame else r


LENSES = ("plays", "dropbacks", "designed_runs", "scrambles", "kneels", "attempts", "completions", "sacks", "interceptions", "fumbles_lost", "pass_yards", "rush_yards",
          "third_down_att", "third_down_conv", "drives", "red_zone_drives", "red_zone_tds", "touchdowns", "punts", "field_goals", "points")


def team_game_facts(season):
    """Per (game_id, team, side): the lens counts of one team in one game, from the events alone: offense = what the team did, defense = what it allowed.
    Third-down conversion: a third-down snap followed by a first down of the same drive, or a touchdown. Red zone: a drive with a snap inside the 20."""
    def build():
        E, _ = events(season); S = E[E.kind.isin(rules.SCRIMMAGE)].copy(); key = ["game_id", "posteam"]
        nxt_down = S.groupby(key).down.shift(-1); nxt_drive = S.groupby(key).drive.shift(-1)
        S["conv"] = (S.down.eq(3) & ((nxt_down.eq(1) & nxt_drive.eq(S.drive)) | S.touchdown.eq(1))).astype(int); S["third"] = S.down.eq(3).astype(int)
        S["py"] = S.yards_gained * S.complete * S.kind.eq(rules.PASS); S["ry"] = S.yards_gained * S.kind.isin(rules.CARRY_KINDS)
        for k_, nm in ((rules.DROPBACK, "dropbacks"), ((rules.RUN,), "designed_runs"), ((rules.SCRAMBLE,), "scrambles"), ((rules.KNEEL,), "kneels"), (rules.ATTEMPT_KINDS, "attempts"), ((rules.SACK,), "sacks")):
            S[nm] = S.kind.isin(list(k_)).astype(int)
        g = S.groupby(key)
        T = g.agg(plays=("play_id", "size"), dropbacks=("dropbacks", "sum"), designed_runs=("designed_runs", "sum"), scrambles=("scrambles", "sum"), kneels=("kneels", "sum"),
                  attempts=("attempts", "sum"), completions=("complete", "sum"), sacks=("sacks", "sum"), interceptions=("interception", "sum"), fumbles_lost=("fumble_lost", "sum"),
                  pass_yards=("py", "sum"), rush_yards=("ry", "sum"), third_down_att=("third", "sum"), third_down_conv=("conv", "sum"), drives=("drive", "nunique"),
                  touchdowns=("touchdown", "sum")).reset_index()
        rz = S[S.yardline_100 <= 20].groupby(key).drive.nunique().rename("red_zone_drives").reset_index()
        rztd = S[S.touchdown.eq(1) & S.yardline_100.le(20)].groupby(key).drive.nunique().rename("red_zone_tds").reset_index()
        kk = E.assign(punts=E.kind.eq(rules.PUNT).astype(int), field_goals=E.kind.eq(rules.FIELD_GOAL).astype(int)).groupby(key)[["punts", "field_goals"]].sum().reset_index()
        T = T.merge(rz, on=key, how="left").merge(rztd, on=key, how="left").merge(kk, on=key, how="left").rename(columns={"posteam": "team"})
        G = games(season); pts = pd.concat([G[["game_id", "home_team", "home_score"]].rename(columns={"home_team": "team", "home_score": "points"}),
                                            G[["game_id", "away_team", "away_score"]].rename(columns={"away_team": "team", "away_score": "points"})])
        T = T.merge(pts, on=["game_id", "team"], how="left").merge(G[["game_id", "week", "home_team", "away_team"]], on="game_id", how="left")
        T["opponent"] = np.where(T.team.eq(T.home_team), T.away_team, T.home_team); T = T.fillna({c: 0 for c in LENSES}).assign(season=season)
        cols = ["game_id", "season", "week", "team", "opponent", "side"] + list(LENSES)
        off = T.assign(side="offense")[cols]; de = T.assign(side="defense", team=T.opponent, opponent=T.team)[cols]
        return pd.concat([off, de], ignore_index=True)
    return _cached(("team_game", season), build)


def team_baselines(cutoff, season):
    """Season-to-date lens numerators and denominators per team and side, from games before the cutoff's issue week: the pregame baseline the user
    sees and the simulator must reproduce (numerator, denominator, value kept separately; game-level ratios are never averaged)."""
    T = team_game_facts(season); T = T[T.week < cutoff.week]
    g = T.groupby(["team", "side"])[list(LENSES)].sum(); n = T.groupby(["team", "side"]).size().rename("games")
    return g.join(n).reset_index()


FACTS = ("game", "plays", "team_game", "player_game")


def materialize(directory, seasons):
    """The four fact tables, written once per data version with a manifest of source hashes (proposal §2, §8): game (the schedule rows of the
    seasons), plays (the typed events), team_game (lens counts per team-game and side), player_game (official stats with finish state)."""
    directory = pathlib.Path(directory) / data_version(); directory.mkdir(parents=True, exist_ok=True)
    if (directory / "manifest.json").exists(): return directory, False
    pd.concat([games(s) for s in seasons]).to_csv(directory / "game.csv.gz", index=False)
    pd.concat([events(s)[0] for s in seasons]).to_csv(directory / "plays.csv.gz", index=False)
    pd.concat([team_game_facts(s) for s in seasons]).to_csv(directory / "team_game.csv.gz", index=False)
    pd.concat([official_by_game(s)[0] for s in seasons]).to_csv(directory / "player_game.csv.gz", index=False)
    (directory / "manifest.json").write_text(json.dumps({"data_version": data_version(), "seasons": seasons, "sources": dict(sorted(OPENED.items())),
                                                         "tables": {t: sha(directory / f"{t}.csv.gz") for t in FACTS}}, indent=1))
    return directory, True


def resolve_code(code, codes):
    """A source team code resolved to the season's team identity: itself when it is one, its alias when the alias is one and it is not; else None."""
    if not isinstance(code, str): return None
    if code in codes: return code
    a = TEAM_ALIASES.get(code)
    return a if a in codes else None


def active(season, week):
    """Issue-time roster for one week: (team, player) for the week's ACT roster minus the players the injury report rules Out, team codes resolved by
    the versioned alias table against the season's identities. Reads no participation. Men under an unresolved code are listed with team None."""
    def build():
        R = roster_raw(season); codes = season_team_codes(season)
        A = R[R.week.eq(week) & R.status.eq("ACT") & R.gsis_id.notna()][["team", "gsis_id"]].drop_duplicates()
        A = A.assign(team_raw=A.team, team=A.team.map(lambda t: resolve_code(t, codes)))
        I = _read(f"injuries_{season}.csv", usecols=["week", "team", "gsis_id", "report_status"])
        O = I[I.week.eq(week) & I.report_status.eq("Out") & I.gsis_id.notna()][["team", "gsis_id"]].drop_duplicates()
        O = O.assign(team=O.team.map(lambda t: resolve_code(t, codes))).dropna(subset=["team"])
        m = A.merge(O, on=["team", "gsis_id"], how="left", indicator=True)
        out = m[m._merge.eq("left_only")].drop(columns="_merge").rename(columns={"gsis_id": "player"})
        c = {"act_rows_without_id": int((R.week.eq(week) & R.status.eq("ACT") & R.gsis_id.isna()).sum()), "out_removed": int(m._merge.eq("both").sum()),
             "unresolved_codes": sorted(set(out.team_raw[out.team.isna()])), "men_under_unresolved_codes": int(out.team.isna().sum())}
        return out[["team", "team_raw", "player"]].reset_index(drop=True), c
    return _cached(("active", season, week), build)


def positions(season):
    """(week, player, position): a player's roster position that week; a player listed at two positions in one week is excluded (counted)."""
    def build():
        R = roster_raw(season); R = R[R.gsis_id.notna() & R.position.notna()][["week", "gsis_id", "position"]].drop_duplicates()
        dup = R.duplicated(["week", "gsis_id"], keep=False)
        return R[~dup].rename(columns={"gsis_id": "player"}).reset_index(drop=True), {"man_weeks_at_two_positions_excluded": int(R[dup][["week", "gsis_id"]].drop_duplicates().shape[0])}
    return _cached(("pos", season), build)


def names(season):
    R = roster_raw(season); return dict(zip(R.gsis_id, R.full_name)) if "full_name" in R.columns else {}


# ----------------------------------------------------------------------------------------------------------------------------- views
def make_cutoff(season, week, partition=K.DEVELOPMENT):
    """The cutoff for forecasts issued at (season, week): the fit's week is the latest refit week <= week (or the season's first refit week when
    week precedes it); admitted seasons are every season on disk except the hold-out, before or equal to this one."""
    rw = sorted(K.POLICY["refit_weeks"]); fit_week = max([w for w in rw if w <= week] or [rw[0]])
    admitted = tuple(s for s in seasons_on_disk() if s != K.POLICY["holdout_season"] and s <= season)
    return K.Cutoff(season=season, week=week, fit_week=fit_week, admitted_seasons=admitted, holdout=K.POLICY["holdout_season"],
                    data_version=data_version(), partition=partition)


def admitted(cutoff, frame, season):
    """The rows of a season frame (with a week column) inside the cutoff's fit boundary."""
    if season == cutoff.holdout or season not in cutoff.admitted_seasons: return frame.iloc[0:0]
    if season < cutoff.season: return frame
    return frame[frame.week < cutoff.fit_week]


def training_events(cutoff):
    """Every scrimmage and state event inside the fit boundary, all admitted seasons, with on-field sets (None = unknown)."""
    parts = []
    for s in cutoff.admitted_seasons:
        if s > cutoff.season: continue
        E, _ = events(s); E = admitted(cutoff, E, s)
        if len(E):
            pers = list(personnel(s, E)); snap = [rules.is_offensive_snap(k, pr) for k, pr in zip(E.kind, pers)]
            parts.append(E.assign(onf=list(on_field_sets(s, E)), pers=pers, snap=snap))
    if not parts: return pd.DataFrame(columns=EVENT_COLS + ["prior_class", "onf", "pers", "snap"])
    return pd.concat(parts, ignore_index=True)


def training_positions(cutoff):
    parts = [positions(s)[0].assign(season=s) for s in cutoff.admitted_seasons if s <= cutoff.season]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["week", "player", "position", "season"])


def scoring_view(cutoff, season):
    """Outcomes for grading: the official player-games of a season. The hold-out is readable only under a certification cutoff (and the caller marks
    the access in the run_log first); this view never feeds a fit."""
    if season == cutoff.holdout and cutoff.partition != K.CERTIFICATION:
        raise DataGap(f"record: hold-out {season} outcomes requested under a {cutoff.partition} cutoff")
    return official_by_game(season)[0]


def availability(season):
    """Forecast availability (schedule, rosters and injuries exist for the season) and grading availability (play-by-play, stats and participation exist, so
    finishing can be TRUE) are different questions; both are answered here, with the reason."""
    have = lambda n: (RAW / n).exists()
    fc = (schedule() is not None and have(f"rosters_{season}.csv.gz") and have(f"injuries_{season}.csv"))
    gr = have(f"pbp_{season}.csv.gz") and have(f"stats_{season}.csv.gz") and have(f"pbp_participation_{season}.csv.gz")
    return {"forecast": fc, "grading": gr, "why": ("" if gr else "no participation file: finishing is UNKNOWN for every player, so lines are not graded under the claim's condition")
            + ("" if fc else " no schedule, roster or injury file: no issue-time population")}


def counts(season):
    return {"events": events(season)[1], "participation": participation(season)[1], "played": played(season)[1], "finished": finished(season)[1],
            "official": official_by_game(season)[1], "positions": positions(season)[1], "deficiencies": deficiencies(season), "schedule": games_cross_check(season),
            "snaps": snaps_cross_check(season)}
