"""synth: a small synthetic league in the raw file layout the record reads (pbp, participation, weekly stats, rosters, injuries, schedule,
players, snap counts). The weekly stats are derived from rules.credits over the generated plays, so the replay check has an exact answer.

The league carries every irregularity the product branches on (NFL goal doc v3, R6): players persist across seasons with turnover, so (player, season)
pairs form chains; a player can skip a season (dt = 2); one franchise changes code between the schedule and the play-by-play (OAK -> LV in the
first season); the first season has no participation file (finishing UNKNOWN; players first met by a later sub_model); penalty no-plays exist,
some with the other side's code in the participation file; the snap-count file has unbridged rows and disagreeing rows first; the first season has
no participation file (every set unknown, as a held season). Used by the tests only.
IRREGULARITIES names each one and the record count or test that proves it is exercised."""
import gzip, pathlib, sys
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import policy as K
import rules

TEAMS = ["AAA", "BBB", "CCC", "LV"]
RELOCATED = {"LV": "OAK"}            # the schedule and the first season's roster name the franchise by its old code; the play-by-play by the current one
POS = ["QB", "QB", "RB", "RB", "RB", "WR", "WR", "WR", "WR", "WR", "TE", "TE", "FB", "T", "T", "G", "G", "C", "T", "G"]
TURNOVER = 0.2                       # share of a team's slots filled by a new player each season
SKIP = 1                             # players per team absent for one whole season (returning the season after: a dt = 2 transition)
PARTICIPATION_ABSENT_FIRST_SEASON = True   # the first season has no participation file at all (a held season: every on-field set unknown, finishing UNKNOWN)
NO_PLAYS_PER_GAME = 2                # penalty no-plays per game, half of them carrying the other side's code in the participation file
IRREGULARITIES = {
    "stable ids across seasons with turnover": "Index.chain: pairs with a predecessor > 0 on the league",
    "a player absent for a season": "a pair with j_dt == 2",
    "one franchise code change (schedule OAK, play-by-play LV)": "record.counts(season)['schedule']['schedule_codes_resolved_to_pbp'] == {'OAK': 'LV'} in the first season",
    "a season without a participation file": "record.counts(season)['finished']['finished_unknown'] > 0 in the first season; its pairs are coded by a later sub_model than snap",
    "penalty no-plays with an offensive unit": "record.counts(season)['participation']['penalty_snaps_with_offensive_unit'] > 0",
    "no-play rows whose file side disagrees": "record.counts(season)['participation']['no_play_rows_with_file_side_disagreeing'] > 0",
    "snap-count rows without a bridge, placed first": "record.counts(season)['snaps']['rows_without_gsis_id'] > 0",
    "snap-count rows disagreeing with participation, placed first": "record.counts(season)['snaps']['disagree_rows'] > 0",
    "participation rows without a personnel string": "model.BRANCHES personnel_roster_derived_snaps > 0",
    "personnel strings not summing to eleven": "model.BRANCHES personnel_sets_not_eleven > 0",
    "two quarterbacks on the field": "model.BRANCHES passer_rows > 0",
}


def rosters(seasons, rng):
    """Per season a roster frame; players persist across seasons with turnover, and SKIP players per team sit out one middle season."""
    counter = {t: 0 for t in TEAMS}; current = {t: [] for t in TEAMS}; out = {}
    for i_s, season in enumerate(seasons):
        rows = []
        for t in TEAMS:
            if not current[t]:
                for p in POS: counter[t] += 1; current[t].append([f"{t}-{counter[t]:03d}", p])
            else:
                for k in rng.choice(len(POS), int(TURNOVER * len(POS)), replace=False):
                    counter[t] += 1; current[t][k] = [f"{t}-{counter[t]:03d}", POS[k]]
            absent = set()   # a player who sits out this whole season stays in current[t] and returns next season (a dt = 2 transition)
            if i_s == 1:
                for k in rng.choice([k for k in range(len(POS)) if POS[k] in ("WR", "RB", "TE")], SKIP, replace=False): absent.add(current[t][k][0])
            code = RELOCATED.get(t, t) if i_s == 0 else t
            for m, p in current[t]:
                if m not in absent: rows.append((code, m, p, f"{t} player {m[-3:]}"))
        out[season] = pd.DataFrame(rows, columns=["team", "gsis_id", "position", "full_name"])
    return out


def game(season, week, home, away, R, rng, gid, injured, codes):
    """One synthetic game: drives of random plays respecting downs, scoring and the clock; returns pbp rows and participation rows.
    codes maps a roster code to the play-by-play code."""
    pbp, part = [], []; play_id = 1; drive = 1; sec = 3600; qtr = 1; score = {home: 0, away: 0}
    players = {t: R[R.team.map(lambda c: codes.get(c, c)).eq(t)] for t in (home, away)}
    poss = home if rng.random() < 0.5 else away; yardline = 75
    pbp.append(dict(game_id=gid, play_id=play_id, play_type="kickoff", posteam=poss, defteam=away if poss == home else home)); play_id += 1
    down, togo = 1, 10; no_plays = 0
    while sec > 0:
        off = players[poss]; opp = away if poss == home else home
        skip = {m for m in off.gsis_id if m in injured}
        qbs = off[off.position.eq("QB") & ~off.gsis_id.isin(skip)].gsis_id.tolist(); skill = off[off.position.isin(["RB", "WR", "TE", "FB"]) & ~off.gsis_id.isin(skip)].gsis_id.tolist()
        ol = off[off.position.isin(["T", "G", "C"]) & ~off.gsis_id.isin(skip)].gsis_id.tolist()
        qb = qbs[0] if rng.random() < 0.9 or len(qbs) == 1 else qbs[1]
        lineup = [qb] + list(rng.choice(skill, 5, replace=False)) + list(rng.choice(ol, 5, replace=False))
        if len(qbs) > 1 and rng.random() < 0.08: lineup[1] = [q for q in qbs if q != qb][0]   # two quarterbacks on the field: the passer sub_model's informative risk set
        pos_of = R.set_index("gsis_id").position; cnt = {}
        for m in lineup: cnt[pos_of.get(m, "RB")] = cnt.get(pos_of.get(m, "RB"), 0) + 1
        personnel = ", ".join(f"{v} {k}" for k, v in sorted(cnt.items()))
        if no_plays < NO_PLAYS_PER_GAME and rng.random() < 0.05:   # a penalty no-play: the down is replayed; the offensive unit was on the field
            no_plays += 1; disagree = no_plays % 2 == 0
            pbp.append(dict(game_id=gid, play_id=play_id, play_type="no_play", posteam=poss, defteam=opp, down=down, ydstogo=togo, yardline_100=yardline, qtr=qtr,
                            game_seconds_remaining=sec, fixed_drive=drive, penalty=1, two_point_attempt=0, total_home_score=score[home], total_away_score=score[away],
                            home_team=home, away_team=away, season=season, week=week))
            part.append(dict(nflverse_game_id=gid, play_id=play_id, possession_team=opp if disagree else poss, offense_players=";".join(lineup), n_offense=11, offense_personnel=personnel))
            play_id += 1; sec -= 5; continue
        r = rng.random(); kind = "pass" if r < 0.55 else ("run" if r < 0.9 else ("sack" if r < 0.95 else "scramble"))
        if down == 4:
            if yardline <= 35: kind = "fg"
            elif togo > 2: kind = "punt"
        if sec <= 60 and score[poss] > score[opp] and qtr == 4: kind = "kneel"
        row = dict(game_id=gid, play_id=play_id, posteam=poss, defteam=opp, down=down, ydstogo=togo, yardline_100=yardline, qtr=qtr, game_seconds_remaining=sec,
                   fixed_drive=drive, penalty=0, two_point_attempt=0, **{"pass": 0}, rush=0, sack=0, qb_scramble=0, complete_pass=0, incomplete_pass=0, interception=0,
                   fumble_lost=0, yards_gained=0, pass_touchdown=0, rush_touchdown=0, touchdown=0, td_team=np.nan, home_score=np.nan, away_score=np.nan,
                   total_home_score=score[home], total_away_score=score[away], extra_point_result=np.nan, two_point_conv_result=np.nan, field_goal_result=np.nan,
                   safety=0, defensive_two_point_conv=0, defensive_extra_point_conv=0, passer_player_id=np.nan, receiver_player_id=np.nan, rusher_player_id=np.nan,
                   lateral_receiver_player_id=np.nan, lateral_receiving_yards=np.nan, lateral_rusher_player_id=np.nan, lateral_rushing_yards=np.nan, out_of_bounds=0)
        lo, hi = rules.gain_support(kind if kind not in ("fg", "punt") else "run", yardline)
        gain = 0; td = False; turnover = False; score_play = False
        if kind == "pass":
            row.update({"pass": 1, "play_type": "pass", "passer_player_id": qb}); rec = rng.choice(lineup[1:6]); row["receiver_player_id"] = rec
            u = rng.random()
            if u < 0.62:
                row["complete_pass"] = 1; gain = int(np.clip(rng.standard_t(4) * 8 + 9, lo, hi)) if rng.random() > 0.04 * (1 + (yardline < 20)) else yardline
                if gain == yardline: td = True; row["pass_touchdown"] = 1
                row["yards_gained"] = gain
                if rng.random() < 0.02 and not td: row["fumble_lost"] = 1; turnover = True
            elif u < 0.95: row["incomplete_pass"] = 1
            else: row["interception"] = 1; turnover = True
        elif kind in ("run", "scramble", "kneel"):
            row.update({"rush": 1, "play_type": "qb_kneel" if kind == "kneel" else "run"})
            if kind == "run": ru = rng.choice(lineup[1:3])
            else: ru = qb
            if kind == "scramble": row["qb_scramble"] = 1
            row["rusher_player_id"] = ru
            if kind == "kneel": gain = -1 if yardline < 99 else 0   # a kneel from the own one loses nothing here (a safety is out of this league's scope)
            else:
                gain = int(np.clip(rng.standard_t(4) * 4 + 4, lo, hi)) if rng.random() > 0.03 * (1 + (yardline < 20)) else yardline
                if gain == yardline: td = True; row["rush_touchdown"] = 1
                if rng.random() < 0.015 and not td: row["fumble_lost"] = 1; turnover = True
            row["yards_gained"] = gain
        elif kind == "sack":
            row.update({"pass": 1, "sack": 1, "play_type": "pass", "passer_player_id": qb}); gain = int(np.clip(-rng.integers(1, 10), lo, 0)); row["yards_gained"] = gain
        elif kind == "fg":
            row.update({"play_type": "field_goal", "field_goal_result": "made" if rng.random() < 0.85 else "missed"})
            if row["field_goal_result"] == "made": score[poss] += 3; score_play = True
            else: turnover = True
        elif kind == "punt":
            row.update({"play_type": "punt"}); turnover = True
        if td: row["touchdown"] = 1; row["td_team"] = poss; score[poss] += 6; score_play = True
        pbp.append(row)
        if kind not in ("fg", "punt"):
            u = rng.random()   # the recorded personnel string: absent on a few rows (roster-derived group), not summing to eleven on a few (refused, counted)
            pers = np.nan if u < 0.05 else (personnel.replace("5 T", "4 T").replace("3 T", "2 T") if u < 0.07 else personnel)
            part.append(dict(nflverse_game_id=gid, play_id=play_id, possession_team=poss, offense_players=";".join(lineup), n_offense=11, offense_personnel=pers))
        play_id += 1
        if td:   # the try
            good = rng.random() < 0.94; score[poss] += 1 if good else 0
            pbp.append(dict(game_id=gid, play_id=play_id, play_type="extra_point", posteam=poss, defteam=opp, extra_point_result="good" if good else "failed",
                            total_home_score=score[home], total_away_score=score[away], qtr=qtr, game_seconds_remaining=sec, fixed_drive=drive, two_point_attempt=0)); play_id += 1
        sec -= int(rng.integers(5, 40)); qtr = 1 + (3600 - max(sec, 0)) // 900 if sec > 0 else 4
        if score_play or turnover:
            if score_play: pbp.append(dict(game_id=gid, play_id=play_id, play_type="kickoff", posteam=opp, defteam=poss, fixed_drive=drive + 1, qtr=qtr, game_seconds_remaining=sec,
                                           total_home_score=score[home], total_away_score=score[away])); play_id += 1
            poss = opp; drive += 1; down, togo = 1, 10
            yardline = 75 if score_play else (100 - (yardline - gain) if kind in ("pass", "run", "scramble") else (100 - yardline - 40 if kind == "punt" else min(100 - yardline - 7, 80)))
            yardline = int(np.clip(yardline, 1, 99))
        else:
            yardline -= gain
            if gain >= togo: down, togo = 1, min(10, yardline)
            else:
                down += 1; togo -= gain
                if down > 4: poss = opp; drive += 1; down, togo = 1, 10; yardline = 100 - yardline
    for r in pbp: r["home_team"], r["away_team"], r["season"], r["week"] = home, away, season, week; r["home_score"], r["away_score"] = score[home], score[away]
    return pbp, part


def build(root, seasons=(2020, 2021, 2022), weeks=8, seed=7):
    root = pathlib.Path(root); root.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng(seed); sched = []; snaps_rows = {}
    ROS = rosters(seasons, rng)
    for i_s, season in enumerate(seasons):
        R = ROS[season]; codes = {RELOCATED[t]: t for t in RELOCATED} if i_s == 0 else {}
        sched_code = (lambda t: RELOCATED.get(t, t)) if i_s == 0 else (lambda t: t)
        pbp, part, ros, inj = [], [], [], []
        for week in range(1, weeks + 1):
            order = rng.permutation(TEAMS); pairs = [(order[0], order[1]), (order[2], order[3])]
            injured = set(rng.choice(R.gsis_id, 2, replace=False))
            for home, away in pairs:
                gid = f"{season}_{week:02d}_{sched_code(away)}_{sched_code(home)}"; p, q = game(season, week, home, away, R, rng, gid, injured, codes); pbp += p; part += q
            for r in R.itertuples(index=False):
                ros.append(dict(season=season, week=week, team=r.team, status="ACT" if r.gsis_id not in injured or rng.random() < 0.5 else "RES", gsis_id=r.gsis_id, position=r.position, full_name=r.full_name))
                if r.gsis_id in injured: inj.append(dict(season=season, week=week, team=r.team, gsis_id=r.gsis_id, report_status="Out"))
        P = pd.DataFrame(pbp)
        for gid, g in P.groupby("game_id"):
            r = g.iloc[0]; sched.append(dict(game_id=gid, season=season, game_type="REG", week=int(r.week), gameday="", gametime="", away_team=sched_code(r.away_team), home_team=sched_code(r.home_team),
                                             away_score=r.away_score, home_score=r.home_score, spread_line=0.0, total_line=40.0, roof="outdoors", surface="grass", away_rest=7, home_rest=7, div_game=0))
        PP = pd.DataFrame(part); e = PP.assign(player=PP.offense_players.str.split(";")).explode("player")
        snaps_rows[season] = e.groupby(["nflverse_game_id", "player"]).size().rename("offense_snaps").reset_index().rename(columns={"nflverse_game_id": "game_id"})
        for c in ["pass", "rush", "sack", "qb_scramble", "two_point_attempt", "penalty", "complete_pass", "incomplete_pass", "interception", "fumble_lost", "yards_gained",
                  "pass_touchdown", "rush_touchdown", "touchdown", "safety", "defensive_two_point_conv", "defensive_extra_point_conv", "down", "ydstogo", "yardline_100", "out_of_bounds"]:
            if c not in P.columns: P[c] = np.nan
        for c in ["passer_player_id", "receiver_player_id", "rusher_player_id", "td_team", "extra_point_result", "two_point_conv_result", "field_goal_result",
                  "lateral_receiver_player_id", "lateral_receiving_yards", "lateral_rusher_player_id", "lateral_rushing_yards"]:
            if c not in P.columns: P[c] = np.nan
        with gzip.open(root / f"pbp_{season}.csv.gz", "wt") as f: P.to_csv(f, index=False)
        if not (i_s == 0 and PARTICIPATION_ABSENT_FIRST_SEASON):
            with gzip.open(root / f"pbp_participation_{season}.csv.gz", "wt") as f: PP.to_csv(f, index=False)
        with gzip.open(root / f"rosters_{season}.csv.gz", "wt") as f: pd.DataFrame(ros).to_csv(f, index=False)
        pd.DataFrame(inj, columns=["season", "week", "team", "gsis_id", "report_status"]).to_csv(root / f"injuries_{season}.csv", index=False)
        # weekly official stats from the credits (nflverse's own derivation stands in for itself here)
        import record
        record.RAW = root; record._CACHE.clear(); record.OPENED.clear()
        C = record.credits(season); T = C.groupby(["week", "player", "stat"]).inc.sum().unstack(fill_value=0).reindex(columns=K.STATS, fill_value=0).reset_index()
        T = T.rename(columns={"player": "player_id", "rec_yards": "receiving_yards", "rec_td": "receiving_tds", "rush_yards": "rushing_yards", "rush_td": "rushing_tds",
                              "pass_yards": "passing_yards", "pass_td": "passing_tds"}).drop(columns=["tds"])
        with gzip.open(root / f"stats_{season}.csv.gz", "wt") as f: T.to_csv(f, index=False)
    pd.DataFrame(sched).to_csv(root / "games.csv", index=False)
    allmen = sorted({m for s_ in snaps_rows for m in snaps_rows[s_].player})
    pd.DataFrame({"gsis_id": allmen, "pfr_id": ["pfr-" + m for m in allmen], "position": "", "position_group": "", "display_name": allmen}).to_csv(root / "players.csv", index=False)
    for s_, S in snaps_rows.items():
        S = S.assign(pfr_player_id="pfr-" + S.player, team="", season=s_, week=0)[["game_id", "pfr_player_id", "team", "offense_snaps"]].copy()
        S.loc[S.index[:3], "offense_snaps"] += 1   # the file's convention differs on a few rows, placed first
        unbridged = pd.DataFrame({"game_id": S.game_id.iloc[:2].tolist(), "pfr_player_id": ["pfr-nobody-1", "pfr-nobody-2"], "team": "", "offense_snaps": [5, 7]})
        with gzip.open(root / f"snaps_{s_}.csv.gz", "wt") as f: pd.concat([unbridged, S], ignore_index=True).to_csv(f, index=False)
    return root


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "/tmp/nfl3_synth"))
