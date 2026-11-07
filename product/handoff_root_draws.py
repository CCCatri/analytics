"""handoff_root_draws.py - acceptance-criteria/engine-to-kit-handoff.md section 2: K engine draws of one issue week's regular-season games, counted into the slate kit's
root units (attempts, carries by QB/RB/WR/TE; section 1's rule without the accepted-foul clause, whose candidate rows are counted and printed), written to
out/handoff/root_draws_{season}_w{week}.npz with its manifest beside it. draw_id j is the same engine game for both teams.
python3 product/handoff_root_draws.py SEASON WEEK K"""
import sys, os, json, time, hashlib, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import engine
SEEN = set(); POS = None
FIX = {"OAK": "LV", "SD": "LAC", "LA": "LAR", "STL": "LAR"}; UNIVERSE = {"QB", "RB", "WR", "TE"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
def sim_pos(ids):
    """The engine's ball-handlers are per-team position placeholders (SIM-<team>-<POS>); the position is the suffix. A real id maps through the stats file."""
    s = ids.astype(str); return np.where(s.str.startswith("SIM-"), s.str.rsplit("-", n=1).str[-1], s.map(POS).astype(object))
def counts(rows, pos):
    """One draw's rows (a text frame) -> per team: attempts, carries under the universe rule; plus the accepted-foul rows that would be candidates for section 1's penalty clause."""
    global POS; POS = pos
    r = rows[rows["posteam"].astype(str).ne("") & ~rows["two_point_attempt"].astype(str).eq("1")].copy(); r["team"] = r["posteam"].map(lambda t: FIX.get(t, t))
    pt = r["play_type"].astype(str); who_p = pd.Series(sim_pos(r["passer_player_id"]), index=r.index); who_r = pd.Series(sim_pos(r["rusher_player_id"]), index=r.index)
    att = (pt.isin(["pass", "qb_spike"]) & ~r["sack"].astype(str).eq("1") & who_p.isin(UNIVERSE))
    car = (pt.isin(["run", "qb_kneel"]) & who_r.isin(UNIVERSE))
    pen = pt.eq("no_play") & r["penalty"].astype(str).eq("1") & (who_p.isin(UNIVERSE) | who_r.isin(UNIVERSE))
    SEEN.update(set(who_p[pt.eq("pass")].dropna()) | set(who_r[pt.eq("run")].dropna()))
    g = pd.DataFrame(dict(team=r["team"], att=att.astype(int), car=car.astype(int), pen=pen.astype(int))).groupby("team")[["att", "car", "pen"]].sum()
    return g
def main(argv):
    season, week, K = int(argv[0]), int(argv[1]), int(argv[2])
    games = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv")); wk = games[(games.season == season) & (games.week == week) & (games.game_type == "REG")]
    ids = sorted(wk.game_id); teams = sorted(set(wk.home_team.map(lambda t: FIX.get(t, t))) | set(wk.away_team.map(lambda t: FIX.get(t, t))))
    pos = pd.read_csv(os.path.join(ROOT, f"data/raw/stats_{season}.csv.gz"), usecols=["player_id", "position"]).drop_duplicates("player_id").set_index("player_id").position
    man = json.load(open(os.path.join(engine.ENGINE_DIR, "MANIFEST.json")))
    att = np.zeros((len(ids), 2, K), int); car = np.zeros_like(att); pen = 0; kept = []; t0 = time.time(); seed0 = engine.SEED
    sides = [(g.game_id, FIX.get(g.home_team, g.home_team), FIX.get(g.away_team, g.away_team)) for g in wk.sort_values("game_id").itertuples()]
    E_cached = engine.engine_load(engine.ENGINE_DIR); engine.engine_load = lambda d=None: E_cached   # the model load once; play_alone unchanged otherwise
    for k in range(K):
        engine.SEED = seed0 + 1000 + k; out, skipped = engine.play_alone(engine.ENGINE_DIR, set(ids)); rows = out[season]
        kept.append(rows.assign(draw_id=k))
        if skipped.get(season): raise SystemExit(f"handoff: games not played in draw {k}: {skipped[season]} - refused")
        for gi, (gid, home, away) in enumerate(sides):
            c = counts(rows[rows.game_id == gid], pos)
            for si, team in enumerate((home, away)): att[gi, si, k] = c.att.get(team, 0); car[gi, si, k] = c.car.get(team, 0); pen += int(c.pen.get(team, 0))
        if k % 10 == 9 or k == K - 1 or k < 3: print(f"  draw {k + 1}/{K}: {time.time() - t0:.1f} s elapsed ({(time.time() - t0) / (k + 1):.2f} s per draw)", flush=True)
    engine.SEED = seed0
    od = os.path.join(ROOT, "out/handoff"); os.makedirs(od, exist_ok=True); path = os.path.join(od, f"root_draws_{season}_w{week}.npz")
    game_id = np.array([s[0] for s in sides for _ in range(2)]); team = np.array([t for s in sides for t in (s[1], s[2])]); opp = np.array([t for s in sides for t in (s[2], s[1])])
    np.savez_compressed(path, game_id=game_id, team=team, opponent=opp, season=np.full(len(team), season), week=np.full(len(team), week), draw_id=np.arange(K),
                        attempts=att.reshape(-1, K), carries=car.reshape(-1, K))
    manifest = dict(season=season, week=week, draw_count=K, games=ids, teams=list(team), teams_without_game=[t for t in teams if t not in set(team)],
                    engine_py_sha=sha(os.path.join(HERE, "engine.py")), model_files=man, fit_mode="look-back: each season's race fit on the five other seasons, later ones included - legality judging only, not a forecast",
                    information_set="the engine's model files as staged; no week-N information enters", counting_rule="section 1 without the accepted-foul clause: engine foul rows carry no pass_attempt/rush_attempt, so attempts and carries on nullified plays are not counted (2 of 3,200 team-weeks on the play-by-play record)",
                    accepted_foul_rows_with_a_ball_handler=pen, root_draws_sha=sha(path), written=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    gp = os.path.join(od, f"games_{season}_w{week}.csv.gz"); pd.concat(kept, ignore_index=True).to_csv(gp, index=False); manifest["games_file"] = os.path.basename(gp); manifest["games_file_sha"] = sha(gp)
    json.dump(manifest, open(path.replace(".npz", ".manifest.json"), "w"), indent=1)
    print("ball-handler positions seen on pass and run rows:", sorted(SEEN))
    print(f"handoff: {path} | games {len(ids)} teams {len(team)} draws {K} | attempts mean {att.mean():.1f} sd {att.std():.1f} | carries mean {car.mean():.1f} sd {car.std():.1f} | accepted-foul rows with a ball-handler (not all would count) {pen} | sha {manifest['root_draws_sha']}")

def play_many(season, games, seeds):
    """play_alone's body with the model load, the rates and the race models done once and the game batch run once per seed. Yields (seed, text frame of that
    draw's rows) in seed order; a game that raises DataGap in any draw stops the run (no draw is written with a game missing)."""
    import threading as _th
    E = engine.engine_load(engine.ENGINE_DIR); seas = E["conf"]["seasons"]
    sch = [g for _, g in E["sched"][E["sched"]["season"] == season].iterrows()]; todo = [(k, g) for k, g in enumerate(sch) if g["game_id"] in games]
    if len(todo) != len(games): raise SystemExit(f"handoff: {len(games)} games asked, {len(todo)} in the schedule - refused")
    Rs = engine.Rates(season, [E["tables"][x][0] for x in seas if x != season]); Rs.RACE_MODELS = engine.race_models(E["race"][season]); MOD = Rs.RACE_MODELS
    for seed in seeds:
        B = engine._Batcher(MOD, len(todo))
        Rs.RACE = dict(eval=B.eval, run_cls=list(MOD["run"].classes_), stop_cls=list(MOD["stop"].classes_), t_cap=E["conf"]["t_cap"]) if MOD is not None else None
        rows = [None] * len(todo); bad = [None] * len(todo)
        def work(j, k, g):
            try: rows[j] = engine.Game(g, Rs, E["season_rules"], np.random.default_rng([seed, season, k]), season).run()
            except engine.record.DataGap as ex_: bad[j] = str(ex_)[:120]
            finally: B.done()
        th = [_th.Thread(target=work, args=(j, k, g)) for j, (k, g) in enumerate(todo)]
        for t_ in th: t_.start()
        for t_ in th: t_.join()
        if B.err is not None: raise B.err
        if any(bad): raise SystemExit(f"handoff: draw seed {seed} did not play {[b for b in bad if b]} - refused")
        yield seed, engine.text_frame([r_ for rr_ in rows if rr_ is not None for r_ in rr_])
if __name__ == "__main__": main(sys.argv[1:])
