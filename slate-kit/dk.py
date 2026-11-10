"""dk.py - the DK DFS transform (Slate Kit module map: dk).  Mechanical: native stat draws (or values) -> DK DFS Classic points under the project owner's offense rules;
fits nothing.  Omits fumbles lost, 2-point conversions and return / recovery TDs.  DST points are DK DFS points already (facts.dstpts scores them; the DST law draws
them), so DST needs no transform here.  DNP = 0 (M8b): a player's DK draw is his F8 draw where his participation draw says he plays, else 0.  The realized-points
reconstruction that checks this transform is facts.dkpts / facts.dstpts (DK DFS recorded points, guard's independent check)."""
import numpy as np
F8_TERM = "F8 dk_points"; DK_TERM = "DK dk_points"; DST_TERM = "DST dk_points"
BONUS_YARDS = {"receiving_yards": 100, "rushing_yards": 100, "passing_yards": 300}   # DK DFS Classic: +3 at 100 receiving / 100 rushing / 300 passing yards (batch 69: one producer for the transform and the graded tail)
def skill_dk(receptions, receiving_yards, rushing_yards, touchdowns): return receptions + 0.1 * receiving_yards + 3 * (receiving_yards >= BONUS_YARDS["receiving_yards"]) + 0.1 * rushing_yards + 3 * (rushing_yards >= BONUS_YARDS["rushing_yards"]) + 6 * touchdowns
def qb_dk(passing_yards, passing_tds, interceptions, rushing_yards, rushing_tds): return 0.04 * passing_yards + 3 * (passing_yards >= BONUS_YARDS["passing_yards"]) + 4 * passing_tds - interceptions + 0.1 * rushing_yards + 3 * (rushing_yards >= BONUS_YARDS["rushing_yards"]) + 6 * rushing_tds
def dnp_zero(points_draws, uniform_draws, probability_plays):
    """DK points with a non-participant scored 0: each draw keeps its F8 value where its uniform falls below P(plays), else 0 (a Bernoulli(P(plays)) per draw)."""
    return np.where(uniform_draws < probability_plays, points_draws, 0.0)
