"""Controlled perturbation at the engine -> kit handoff, as one callable concept (the matrix's controlled_perturbation for NFL).
perturb_handoff(fixture, team, source_draw, delta, scratch, pinned_from, state=None, quiet=None) -> dict
  fixture: the engine root draws .npz (its manifest beside it); team: the team whose root draw is changed; source_draw: which of its K draws;
  delta: added to that draw; scratch: a folder for isolated kit outputs; pinned_from: a proj folder holding atlas.csv and ladder.csv the card grades against.
  state (optional): the first run already done by a caller — dict(week, boundary, pid, mine); without it the function runs the card itself and captures
  the week draws from inside that run (one draw_link call per cell).
Returns raw values (source before/after, what draw_link received, mapped and unmapped movement counts) and `checks`: the five B2 verdicts as
(name, condition, detail), worded as the handoff record words them. Installs boundary logging around the current draws functions and restores them."""
import os, sys, json, shutil, hashlib, io, contextlib, numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); KIT = os.path.join(ROOT, "slate-kit")
if KIT not in sys.path: sys.path.insert(0, KIT)
sha256 = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

def perturb_handoff(fixture, team, source_draw, delta, scratch, pinned_from, state=None, quiet=None):
    cwd = os.getcwd(); os.chdir(KIT)
    import draws, cards
    from link_chain import LINKS
    def run_quiet(fn, *args):
        if quiet is not None: return quiet(fn, *args)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): return fn(*args)
    def outdir(name):
        d = os.path.join(scratch, name); os.makedirs(d, exist_ok=True)
        for f in ("atlas.csv", "ladder.csv"): shutil.copy(os.path.join(pinned_from, f), d)
        draws.PROJ_DIR = d; cards.PROJ_DIR = d; return d
    def set_mode(source, path=None): draws.ROOT_SOURCE = source; draws.ROOT_FILE = path; draws.ENGINE_ROOT = None
    boundary, pending, held = [], [], {}
    cur_substream, cur_draw_link, cur_week_draws, cur_cards_week_draws = draws.substream, draws.draw_link, draws.week_draws, cards.week_draws
    def substream_logging(term, position, season, week, key, label):
        if label == draws.LINK_CHAIN_STATE: pending.append((term, position, key))
        return cur_substream(term, position, season, week, key, label)
    def draw_link_logging(cell, fit, rate, other, concentration, parent_draws, generator, sibling=None):
        out = cur_draw_link(cell, fit, rate, other, concentration, parent_draws, generator, sibling); who = pending.pop() if pending else None
        boundary.append(dict(cell=cell, who=who, matches=(who is not None and who[0] == cell[0] and who[1] == cell[1]), parent_cell=LINKS[cell][0], parent=None if parent_draws is None else parent_draws.copy(), out=out.copy()))
        return out
    def capturing_week_draws(season, week): held["week"] = cur_cards_week_draws(season, week); return held["week"]
    draws.substream, draws.draw_link, cards.week_draws = substream_logging, draw_link_logging, capturing_week_draws
    try:
        src = np.load(fixture); man = json.load(open(fixture[:-4] + ".manifest.json")); teams = src["team"].astype(str); K = int(src["draw_id"].shape[0])
        row_home = int(np.where(teams == team)[0][0]); season, week_no = int(man["season"]), int(man["week"])
        if state is None:
            set_mode("engine", fixture); d = outdir("B_engine"); run_quiet(cards.card, season, week_no); week = held["week"]
            card = pd.read_csv(os.path.join(d, f"card_{season}_w{week_no}.csv")); qbs = card[(card.team == team) & (card.position == "QB") & (card.term == "Q1 attempts")]
            pid = qbs.player_id.iloc[0] if len(qbs) else None; mine = week["draws"][(pid, "Q1 attempts")] if pid else None
            first_boundary = list(boundary)
        else:
            week, first_boundary, pid, mine = state["week"], list(state["boundary"]), state["pid"], state["mine"]
        if not pid: return dict(pid=None, checks=[("B2 a QB with Q1 attempts on the card", False, f"none for {team}")])
        rec = [b for b in first_boundary if b["who"] == ("Q1 attempts", "QB", pid) and b["cell"] == ("Q1 attempts", "QB") and b["matches"]]
        bound = len(rec) == 1 and rec[0]["parent_cell"] == ("F2 team attempts", "TEAM") and np.array_equal(rec[0]["parent"], week["draws"][(team, "F2 team attempts")])
        src0, src29 = float(src["attempts"][row_home][source_draw]), float(src["attempts"][row_home][29])
        col0 = 30 if source_draw == 0 else None
        checks = [(f"B2 draw_link for {pid} Q1 attempts: one call, cell matched, parent is {team}'s F2 team attempts root", bound, f"{len(rec)} matching call(s)")]
        if col0 is not None: checks.append((f"B2 received column 30 = {team} source draw 0 ({src0:.0f}) and column 29 = source draw 29 ({src29:.0f})", bound and rec[0]["parent"][30] == src0 and rec[0]["parent"][29] == src29, f"received [30] {rec[0]['parent'][30] if rec else None}, [29] {rec[0]['parent'][29] if rec else None}; returned column 30 {rec[0]['out'][30] if rec else None}"))
        before, team_before = mine.copy(), week["draws"][(team, "F2 team attempts")].copy()
        bumped_dir = os.path.join(scratch, "injected_faults"); os.makedirs(bumped_dir, exist_ok=True); bumped = os.path.join(bumped_dir, "bumped.npz")
        data = {k: src[k].copy() for k in src.files}; data["attempts"][row_home, source_draw] = data["attempts"][row_home, source_draw] + delta
        np.savez_compressed(bumped, **data); m = dict(man); m["root_draws_sha"] = sha256(bumped)[:12]; json.dump(m, open(bumped[:-4] + ".manifest.json", "w"), indent=1)
        set_mode("engine", bumped); outdir("B2_bumped"); boundary.clear(); pending.clear()
        week2 = run_quiet(cur_week_draws, season, week_no); after, team_after = week2["draws"][(pid, "Q1 attempts")], week2["draws"][(team, "F2 team attempts")]
        mapped = (np.arange(team_after.shape[0]) % K) == source_draw; moved_team, moved = team_after != team_before, after != before
        checks.append((f"B2 team root moved at all {int(mapped.sum())} columns mapped to source {source_draw} and nowhere else", bool(moved_team[mapped].all() and not moved_team[~mapped].any()), f"mapped moved {int(moved_team[mapped].sum())} of {int(mapped.sum())}; unmapped moved {int(moved_team[~mapped].sum())}"))
        checks.append((f"B2 {pid} Q1 attempts moved at >= 1 mapped column and at no unmapped column", bool(moved[mapped].any() and not moved[~mapped].any()), f"mapped moved {int(moved[mapped].sum())} of {int(mapped.sum())} (a binomial can land on the same value); unmapped moved {int(moved[~mapped].sum())}"))
        rec2 = [b for b in boundary if b["who"] == ("Q1 attempts", "QB", pid) and b["cell"] == ("Q1 attempts", "QB") and b["matches"]]
        if col0 is not None: checks.append((f"B2 the changed source ({src0:.0f} -> {src0 + delta:.0f}) is what draw_link received at column 30", len(rec2) == 1 and rec2[0]["parent"][30] == src0 + delta, f"received {rec2[0]['parent'][30] if rec2 else None}; returned column 30 before {rec[0]['out'][30] if rec else None} after {rec2[0]['out'][30] if rec2 else None}"))
        return dict(pid=pid, team=team, source_draw=source_draw, source_before=src0, source_after=src0 + delta, received_before=(rec[0]["parent"][30] if rec and col0 else None), received_after=(rec2[0]["parent"][30] if rec2 and col0 else None),
                    mapped_columns=int(mapped.sum()), team_moved_mapped=int(moved_team[mapped].sum()), team_moved_unmapped=int(moved_team[~mapped].sum()), player_moved_mapped=int(moved[mapped].sum()), player_moved_unmapped=int(moved[~mapped].sum()), checks=checks)
    finally:
        draws.substream, draws.draw_link, cards.week_draws = cur_substream, cur_draw_link, cur_cards_week_draws; os.chdir(cwd)
