"""N2b, first landing: the who-plays law is fit and scored on the final active list (facts.active_keys).  Known-right: an inactive player's chance equals the rate
inactive players of his position played in the fit rows.  Plants: the old law (fit on every candidate) must read MISCALIBRATED on active RB, WR and TE; active RB
chances shifted down 0.10 must not read COMES TRUE.  Target: on active rows the walk-forward gap (how often he played minus the chance) COMES TRUE within +-0.03 at
2SE at QB, RB, WR and TE, and inactive chances sit below 0.05."""
import sys, numpy as np, pandas as pd; sys.path.insert(0, "slate-kit")
import participation
from facts import load, team_game
from ingest import FROZEN_THRU
from participation import who_plays_inputs, who_plays_fit, who_plays_probability, model_rows_of, is_active
BOUND, INACTIVE_CEILING, POSITIONS = 0.03, 0.05, ("QB", "RB", "WR", "TE")
player_rows, team_games = load(), team_game()
rows = model_rows_of(who_plays_inputs(player_rows, team_games, sorted(set(player_rows.season[player_rows.season <= FROZEN_THRU]))))
rows = rows.assign(on_list=is_active(rows).to_numpy())
snaps = player_rows[["player_id", "season", "week", "offense_snaps"]].groupby(["player_id", "season", "week"], as_index=False).offense_snaps.max()
def walk():
    out, known = [], []
    for season in sorted(set(rows.season.astype(int))):
        laws, unused = who_plays_fit(rows[rows.season < season])
        if not laws: continue
        test = rows[rows.season == season].copy(); test["p"] = who_plays_probability(laws, test); out.append(test)
        prior = rows[(rows.season < season) & (rows.designation_construction == "as of the freeze") & ~rows.on_list]
        for pos, law in laws.items():
            expect = prior.played[prior.position == pos].mean(); got = test.p[(test.position == pos) & ~test.on_list]
            known.append((season, pos, law[3], expect, bool(np.isclose(law[3], expect, equal_nan=True)) and (len(got) == 0 or bool(np.allclose(got, expect)))))
        print(f"  {season}: fit and scored", flush=True)
    return pd.concat(out, ignore_index=True), known
def gap(y, p): d = (y - p).to_numpy(float); return d.mean(), 2 * d.std(ddof=1) / np.sqrt(len(d))
def verdict(m, s): lo, hi = m - s, m + s; return "COMES TRUE" if (-BOUND <= lo and hi <= BOUND) else ("MISCALIBRATED" if (lo > BOUND or hi < -BOUND) else "INCONCLUSIVE")
fails = []
print("walk-forward, the law on the final active list:")
t, known = walk(); t = t[t.p.notna()].merge(snaps, on=["player_id", "season", "week"], how="left"); t["used"] = (t.offense_snaps.fillna(0) > 0).astype(float)
bad = [k for k in known if not k[4]]
print(f"KNOWN-RIGHT: inactive chance equals the earlier inactive play rate in {len(known) - len(bad)} of {len(known)} season-positions" + ("" if not bad else f"; off: {bad}"))
if bad: fails.append("known-right")
print("PLANT 1: the old law, fit on every candidate, scored on active rows")
real = participation.is_active; participation.is_active = lambda r: pd.Series(True, index=r.index); old, unused = walk(); participation.is_active = real
old = old[old.p.notna() & old.on_list]
for pos in ("RB", "WR", "TE"):
    m, s = gap(old.played[old.position == pos], old.p[old.position == pos]); v = verdict(m, s)
    print(f"  {pos}: gap {m:+.3f} (2SE {s:.3f}) {v} -> {'PLANT CAUGHT' if v == 'MISCALIBRATED' else 'PLANT MISSED'}")
    if v != "MISCALIBRATED": fails.append(f"plant 1 {pos}")
a = t[t.on_list]; r = a[a.position == "RB"]; m, s = gap(r.played, (r.p - 0.10).clip(0, 1)); v = verdict(m, s)
print(f"PLANT 2: active RB chances down 0.10 -> gap {m:+.3f} (2SE {s:.3f}) {v} -> {'PLANT CAUGHT' if v != 'COMES TRUE' else 'PLANT MISSED'}")
if v == "COMES TRUE": fails.append("plant 2")
print("TARGET: active rows, played; inactive chance below 0.05")
for pos in POSITIONS:
    r = a[a.position == pos]; ina = t[(t.position == pos) & ~t.on_list]
    m, s = gap(r.played, r.p); v = verdict(m, s); mu, su = gap(r.used, r.p)
    print(f"  {pos}: active {len(r)}; played {r.played.mean():.3f} vs chance {r.p.mean():.3f} -> gap {m:+.3f} (2SE {s:.3f}) {v}; inactive {len(ina)} at chance {ina.p.mean():.3f} (played {ina.played.mean():.3f}); used on offense gap {mu:+.3f} (2SE {su:.3f}, printed for chain 2)")
    if v != "COMES TRUE": fails.append(f"target {pos}")
    if len(ina) and ina.p.mean() >= INACTIVE_CEILING: fails.append(f"inactive {pos}")
    low = r[r.p <= r.p.quantile(0.1)]; ml, sl = gap(low.played, low.p)
    print(f"     lowest tenth: {len(low)} rows, chance {low.p.mean():.3f}, played {low.played.mean():.3f}, gap {ml:+.3f} (2SE {sl:.3f}) {verdict(ml, sl)} (printed for chain 2)")
print("CHECK PASSED" if not fails else f"CHECK FAILED: {fails}")
sys.exit(0 if not fails else 1)
