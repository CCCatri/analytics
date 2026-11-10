"""The who-starts law's check (slate-kit/participation.py: who_starts_training, who_starts_fit, who_starts_probability), walk-forward as the card issues it.
Each judged season's law is fit on the seasons before it, its inputs the P(plays) the who-plays law fit before each season would have issued. The law must name
the starter (the quarterback with the most attempts in his team's game) with lower log loss than P(plays) itself in every judged season; calibration printed.
Injected fault, every season: the judged season's P(plays) shuffled among its quarterback rows (the signal removed) must NOT beat P(plays), else the check is blind.
python3 checks/check_who_starts.py  -> exit 0 on PASS, 1 otherwise. Reads only; writes nothing."""
import os, sys
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "slate-kit"))
from participation import who_starts_training, who_starts_fit, who_starts_probability
from facts import load, team_game
from ingest import FROZEN_THRU


def log_loss(y, p):
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))))


def main():
    T = who_starts_training(load(), team_game(), FROZEN_THRU); seasons = sorted(T.season.unique())
    print(f"quarterback candidate rows {len(T)} | seasons {seasons} | team-weeks {T.groupby(['season', 'week', 'team']).ngroups} | started labels {int(T.started.sum())}")
    better, blind, judged = [], [], []
    for s in seasons[1:]:
        theta = who_starts_fit(T[T.season < s]); d = T[T.season == s]
        p = who_starts_probability(theta, d); raw, law = log_loss(d.started, d.probability_plays), log_loss(d.started, p)
        shuffled = d.assign(probability_plays=np.random.default_rng(int(s)).permutation(d.probability_plays.to_numpy()))
        fault = log_loss(d.started, who_starts_probability(theta, shuffled))
        better.append(law < raw); blind.append(fault < raw); judged.append(d.assign(p_starts=p))
        print(f"  {s}: fit on {[x for x in seasons if x < s]} | b0 {theta[0]:+.2f} b1 {theta[1]:+.2f} | naming the starter, log loss: P(plays) {raw:.4f} | who-starts law {law:.4f} -> "
              f"{'BETTER' if law < raw else 'NOT BETTER'} | injected fault (P(plays) shuffled) {fault:.4f} -> {'blind: beat P(plays)' if fault < raw else 'seen'}")
    J = pd.concat(judged); J = J.assign(bin=pd.cut(J.p_starts, [0, .05, .1, .3, .5, .7, .9, 1.0]))
    print("  calibration (bin | quarterbacks | mean P(starts) | share who started):")
    for b, d in J.groupby("bin", observed=True): print(f"     {str(b):12s} | {len(d):5d} | {d.p_starts.mean():.3f} | {d.started.mean():.3f}")
    tw = J.groupby(["season", "week", "team"]).agg(total=("p_starts", "sum"), hit=("started", "max"))
    print(f"  outside option (a starter not among the candidates): law {1 - tw.total.mean():.3f} | actual {1 - tw.hit.mean():.3f}")
    ok = all(better) and not any(blind) and len(better) > 0
    print(f"WHO STARTS: {'PASS' if ok else 'FAIL'} | judged seasons {len(better)} | better {sum(better)} | injected faults seen {len(blind) - sum(blind)} of {len(blind)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
