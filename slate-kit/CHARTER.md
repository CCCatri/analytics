# Slate kit charter (Oct 2 2026)

## The one goal
Find where DraftKings' price is wrong, using only information that existed before kickoff, and prove it on seasons the
method never saw.  Everything the kit computes serves one generative model of a slate:

  causal roots -> each player's role (with uncertainty) -> how role and availability move week to week
  -> shared game factors that make teammates and opponents move together -> Monte Carlo of games, slates, contests

## The honest limits, used as the rules
1. Pregame only.  A feature may use only what was published before kickoff.  Proven for the builder (purity test,
   Oct 2: deleting all game-week-onward rows leaves every column identical).  Every new producer carries the same test.
2. Value, not points.  Value is judged within each slate: partial rank correlation given salary (predicted and actual
   points each residualized on that slate's own salaries).  Accuracy that does not change value vs price is not an edge.
3. Causes only from natural experiments.  A causal claim needs a shock nobody chose: injuries and absences, inactives,
   rest and schedule, weather, line moves after DK pricing.  Everything else is association: usable for prediction,
   never written as a lever.  Game script is not randomly assigned, so it shapes the joint simulation, never a pregame rule.
4. Walk-forward only.  Fit on earlier seasons, judge on the next.  Real DK salaries: 2016-21, listing only players who took part
   (membership is post-game; see Findings).  No clean historical pools exist.
5. Ownership is not identifiable from this data.  No crowd layer acts on lineups; crowd results are sensitivity only.
6. Mirror twins.  Every claim must predict its opposite: the reverse tail, the mechanism switched off, labels shuffled,
   time reversed.  The whole search is also run on shuffled outcomes; findings count only above that line.
7. Necessity.  An input stays only if removing it hurts walk-forward value vs price.  Anything that exists only to
   feed a removed input goes with it.

## Anchors (natural information we build on)
DK salary (the price), the closing line (the market's forecast), role share history, the injury report and inactives,
the schedule.  Outcomes (stats, snaps, scores, DK points) are labels, never inputs about the same week.

## One producer per fact
| layer | question | reads | producer |
|---|---|---|---|
| F facts | what happened, what was published pregame | raw nflverse files, tidy salaries | facts.py -> facts/*.csv.gz |
| P projection and price | who beats price | F | one walk-forward fitter (replaces models.json, blend.json, honest, fit_blend, compare_on, audit, construct) |
| A availability | who plays, how much | F | one availability model (replaces absencechain, the injury tests) |
| J joint outcomes | how players move together, game shapes | F | one joint estimator (replaces stacks, piechain, chain55, chainstress, tails, offdef, gamepair, gamescript, gamesim, shapelens, shapeodds, defense, layers, teamchain, reframe, reopen, grenade) |
| M market timing | prices and lines over time | data/line_history, tidy salaries, F | one line/price table (replaces pricetime, slates; history_clocks and snapshot stay as fetchers) |
| R props | what prop lines know | raw prop lines + actuals, F | one props table (replaces proptests, propthreads, pick6_devig) |
| S simulation | what our lineups score on a real pool | P, A, J, a real DraftKings file | one simulator over the real pool; no contest field (rule 5); takes over the builder's internals (dkpts/dstpts copies, models.json) |
| L evaluation | which rules hold on weeks never seen | S, P, A, J, accepted forward weeks | one harness, frozen before the weeks arrive; twins: shuffled projections, random valid lineups |

Order: F -> P, A, J, M, R -> S -> L.  A replaced script is deleted when its producer is verified.

## Findings that bind (Oct 2 2026)
- MEMBERSHIP: the 2016-21 salary source lists players who took part in the game (Out players: 0-4 priced per season of 157-264 listed;
  QBs 1.21 per team-week vs 1.20 who played). DraftKings' real pool (sources/raw/dk_weekly/DK_2026_w4.csv) lists 2.4-2.7x as many skill
  players per team, 61-74% at the position minimum. Pools and backtests built from the source never contain a player who sat: optimistic
  by an amount this data cannot measure. P (which conditions on playing) stands; its domain is "priced players who played".
- METRIC: value is judged by partial rank correlation given salary within each slate (predicted and actual DK points each residualized on
  that slate's own salaries). Subtracting one fitted price curve from both sides correlates the curve's error with itself.
- NULLS: two twins - value shuffled within slate (keeps slate means) and across all rows; the bar is the higher 95th percentile.
- DOMAIN: an input joins a producer only if defined on every row it already covers; a hole would need a fallback.
- GATE: a group is kept or added iff its paired gain > 2 s.e. and positive in >= all-but-one test season.
- P verdicts: QB season usage axis; RB last-week role; WR season usage axis + last-week role; TE season usage axis.
  Out everywhere: dk lags, prior season (rookie hole), game line.
- A: availability is estimable only for injury-listed players.
- OPEN: DraftKings' RB minimum is 4000 in 2026 vs 2500-3000 in 2016-21; whether the rest of the salary scale carries over is unknown.
  A first game of a season in weeks 4-16 has no season-to-date usage; those rows are unprojected where inputs need it.
- organize_sources.py is retired (guarded): a rerun would fold sources/raw/dk_weekly into the 2016-21 tidy salaries.
- SCORING (identified against DraftKings' recorded points 2016-21; today's rules page agrees; 2022-25 untestable):
  skill adds return TDs +6, return fumbles lost -1, offensive fumble-recovery TDs +6 (from play-by-play).
  DST: points allowed = final - 6 per opponent defensive TD - 2 per safety (tries and return TDs stay in); any recovered opponent fumble;
  every blocked kick; defensive 2pt/XP returns. Exact: DST 97.8%. The remaining DST games are provider-level play differences
  (e.g. a muffed punt with no recovering team in play-by-play; a 2021 missed-FG return TD DraftKings did not score). They are recorded, not patched.
- build_slate.py keeps old copies of dkpts()/dstpts(): a second producer, retired when S/L replace the builder's internals.
- J (Oct 2 2026): slots fixed pregame (previous team-game + injury list, ranked by season-to-date snap share); Gaussian copula, full
  correlation (home/away symmetric) beats 1-2 factors; +0.50 nats/game vs independence, every season; shuffled pairing -0.89; reverse
  time +0.51; pure. OPEN for S: (1) teammates' shift when a slot player does not play - an absence is a natural experiment, measure it
  before simulating absences; (2) tail dependence beyond the Gaussian copula is untested.
- M (Oct 2 2026): proj/m_lines.csv.gz (open / Tuesday / close implied totals, 2020-2025). The post-pricing move adds no value beyond P on
  2020-21 (pooled -0.004 +- 0.004, 0/2; pre-pricing twin null; shuffled null 95th +0.004). Salary release time is not on disk.
- DELETED: player_availability.parquet - its ids came from abbreviated names (J.Williams, J.Hill, D.Johnson), wrong team in 98.9% of
  its disagreements with facts.
- DATA RULE: facts is the only producer of outcomes. Any third-party derived file is checked against facts once and deleted if dirty or
  redundant (deleted so far: player_availability.parquet, player_props_actuals.parquet - player_team wrong in 43% of rows).
- R (Oct 2 2026): proj/r_props.csv.gz (consensus pregame lines, 2024 only - the file holds one season). Prop index adds information about DK
  points beyond P inputs: pooled +0.066 +- 0.025, both halves positive, shuffled null 95th +0.002; RB +0.167, WR +0.054, QB/TE ~0.
  Accuracy only - no salaries for 2024, so value vs price is not identifiable. Live use would need weekly prop fetches.
- GUARD (Oct 2 2026): guard.py must pass before any result is trusted - raw manifest (facts/raw_manifest.json; changes need --accept after
  verification), one reader per raw source, one definition per core function, facts' independent-check floors, output freshness, purity,
  replaced scripts stay deleted. First run deleted: organize_sources, funnel (third dkpts copy), season_sim, sim_calib2, reglaw, simcheck,
  stacks, promote_laws (raw reads outside producers; inputs invalid).

## S and L, derived from the invariants (Oct 2 2026)
- Membership pregame -> S runs only on real DraftKings files; no historical lineup simulation exists that can be honest.
- Unseen data -> L judges only weeks after the code is frozen (2026 w4 onward); every week enters through guard.py --accept, adding 2026 files only.
- No fill -> players without P inputs are unprojected and counted; lineups use projected players only.
- Rule 5 -> no contest field; the lineup null is random valid lineups from the same pool under the same cap.
- Rule 2 -> P is scored on the real pool by within-slate partial correlation, players who sat counted at their real 0.
- Gate -> paired gain > 2 s.e., positive in >= all-but-one 4-week block; rules fixed before outcomes exist.
- One producer -> the builder becomes a thin reader of proj/; its dkpts/dstpts copies and models.json retire with S.
- Forward inputs = the DraftKings file already downloaded + the weekly nflverse refresh live building already needs; no historical fetching.
- L v1 (frozen Oct 2 2026, record proj/l_weeks_v1.csv) judged 2026 w3: P RB +0.194 and WR +0.174 above their shuffled 95th, QB +0.144 inside
  noise, TE -0.020; A gain +0.394; lineup 107.0 vs expected 138.8. Its lineup null (random valid lineups) was too weak. L v2 starts 2026 w4:
  the lineup is judged against the price-alone lineup (rule 2); S's expected - actual is tracked under the 2016-21 salary scale.
- DELETED: threads.py and the canonical pools (post-game membership, old scoring). refresh.py replaces the builder's nflverse download;
  build_slate.py, models.json, laws.json and field_check.py retire after refresh.py has run successfully once.
- SEASONS (Oct 2 2026): a season counts only if every raw kind exists for it, game-day roster status included - 2019-21, 2023-25, 2026.
  Deleted: 2016-18 and 2022 per-season raw files, 2016-18 salary files, era copies, lagged NGS; tidy salaries rewritten to 2019-21.
  Multi-season raw files (games.csv, line history, odds caches) stay whole; facts excludes other seasons in code.
- INFORMATION TIME: after inactives (game-day roster status, ~90 min before kickoff), for backtests and live play alike. Live S must run
  after the inactive list is published; the weekly roster file cannot prove that timing itself. Unlisted active regulars (70%+ snaps the
  game before) hide 1.3-2.4% sitters per season in the participants-only salary source - the bound for historical backtests.
- L v2's freeze reset (no week judged); start stays 2026 w4.
- INFORMATION TIME, corrected (Oct 2 2026): BEFORE inactives. nflverse updates weekly rosters and injuries daily at 7am UTC, so Sunday's
  inactive list is not available before lock; schedules/lines update every 5 minutes. Backtests and live play share the Saturday 3am ET
  data: A's status input is rostered (ACT or INA) / RES / DEV / CUT / none; unlisted regulars hide ~3.0% sitters (1.7-4.9% per season).
  The 2016-18 and 2022 deletions were made for the after-inactives frame and cannot be undone without refetching.
- L should judge each week on Thursday's refresh (nflverse: cleanest after the NFL's Monday-Wednesday stat corrections).
- LENSES (Oct 2 2026): walk-forward = every producer; eigen = lens.py s1 + J factors; Markov = lens.py s2, P last-week role, A last state;
  Bayes = A's partial pooling; Monte Carlo = S; counterfactual = P's vacated share (teammates ruled Out / Doubtful, a shock nobody chose).
- RULE 2 amended (owner, Oct 2 2026: "accuracy sounds great though, thats what I want"): inputs are chosen for accuracy on all complete
  seasons (2019-21, 2023-25); value vs price (2019-21, and L on live weeks) is still reported every time as the evidence of an edge.
- discover.py v2: features generated by rule in families (self, teammates, absence, state, team offense / defense, opponent offense /
  defense, matchup, script, discipline, game); lasso + gradient boosting; importance by family; whole-search null on shuffled outcomes.
- DISCOVERY (Oct 2 2026; discover.py v2, discover3.py, anchors.py; accuracy on 2019-21 + 2023-25, whole-search nulls):
  confident, every season: season-to-date points/yards/TDs regress (top 10% UNDER -1.6 to -4.0; TDs strongest); usage persists;
  same-position absences shift VOLUME not efficiency (RB1 out: other RBs +3.5 +- 0.4, beat 60.7% vs 40.9%; RB2 +6.2 opportunities);
  facing a high-scoring offense raises a team's pass rate beyond the spread (+0.13 to +0.20). Anchor counts far above noise
  (QB 38 vs 0.7, RB 33 vs 0.2, WR 31 vs 0.5, TE 8 vs 0.2). Pie type (pass rate) predictable, pie size (plays) not.
  covered and empty: team/opponent identity rates, matchup, profile x defense interactions (boosting), slot defense,
  predicted-volume beneficiaries, discipline. Do not rerun these roots without a new form of them.
- CLOSED (Oct 2 2026): similar player x projected situation x similar opponent - nearest-neighbour analogs lose to the lasso in every
  position (-0.07 to -0.12, 0/5 seasons) and the blend does not help; with v2's boosting, the profile x situation x opponent root is closed.
  Top-down allocation of group totals loses for RB/WR/TE; QB blended with its team passing total gains +0.042 +- 0.011 (4/5).
  Pace (neutral seconds per snap) is the most stable team trait (+0.33); game total plays (+0.18) beats one side (+0.11); the split is
  decided in the game (+0.06). LEAD to confirm on new seasons, not acted on: analogs rank the coldest 10% of QBs +0.233 vs lasso +0.069 (n 198).

## Slices across pies / size from richer inputs / co-movement by volume (2026-10-02, 2019-21 + 2023-25)
- Slices vs pie size: no share moves with game plays (realized or pregame).
- Slices vs type (realized): pass-heavier -> WR1 tgt share -0.56pp, RB1 tgt share +0.56pp, QB1 carry share +1.75pp per SD.
- Pregame slice shifts (small, <=4% relative): QB1 carry share favored -0.52 / total +0.51; WR3 tgt share favored -0.36 (6/6); RB1 tgt share favored -0.24.
- Efficiency vs realized margin: tautological (margin is built from the same TDs). Pregame efficiency shifts <= 0.10 DK/opp.
- Size forecast with pace/drives/ppd/epa/pass mix/allowed: game plays +0.159 vs own +0.183 (d -0.024, 3/5); team plays -0.011; split d +0.033 (2/5). CLOSED: size = own average.
- Pass rate +0.288 vs +0.229 (d +0.059+-0.016, 4/5) - same as discover3; richer inputs add nothing.
- Co-movement: WR1~TE1 by total line +0.08 low -> -0.14 high (z -3.9, 6/6); WR1~WR2 by predicted plays +0.09 -> -0.04 (z -2.1, 5/5, borderline).
  DST~opp QB1 weakens with realized plays only (mechanism, not pregame). No whole-search null on this scan.
- Not yet tested: total-conditioned J on held-out log-likelihood; pregame slice shifts as P features.

## Information set (owner, 2026-10-02): "only week 3 results plus prices, keep all data apples to apples when comparing"
- Live and in every backtest: results through week N-1 + week N's DraftKings price file (Game Info: opponent, home, kickoff). Nothing else about week N.
- Outside it: week N's injury report, practice report, roster status, game line (implied, spread, total), props, a price-file injury tag.
- One definition: p.WEEKN, dropped by p.team_game() / p.load() (the only readers of facts' tables); p.frame() builds week N; guard check 10 + purity "INFO SET PURE".
- Deleted: vacated share (P), rep/prac/status (A), injury-list slot candidates (J), absence/game/script/opponent-implied families (discover), m.py, r.py, discover3.py, anchors.py.
- Every finding above that used week-N facts was measured under the old information set and does not describe this one: discover's lasso numbers,
  absence anchors, absence decomposition, implied-total and DST-from-opponent-implied results, the pie model with lines, the slice-vs-line rows.
- Apples to apples: history has prices for 2019-21 only - any model with price, and any comparison against one, runs on 2019-21 rows; A's domain is priced rows.
- L v2 start stays 2026 w4 (no week-4 game judged; Thursday's teams are not in the Sun-Mon price file); freeze reset for the method change.

## One fetcher (owner, 2026-10-02): fetch.py replaces refresh.py, studies/dk_watch.py, studies/snapshot.py, studies/history_clocks.py
- Default: nflverse (results) + week N's DraftKings price file (--dk-group). Opt-in, never a projection input: --odds-lines, --odds-props, --odds-history.
- One fetch per call; nothing enters until guard.py --accept.  Guard: check 2 limits raw reads to fetch.py; check 10 fails if a model script names odds data.
- Weekly: python3 fetch.py 2026 N --dk-group <id>  ->  guard.py  ->  guard.py --accept  ->  facts.py  ->  s.py 2026 N

## DNP and statuses (owner, 2026-10-02)
- A player who did not play is in no P analysis (P trains on played rows; L's P test excludes DNP and counts them). Whether he plays is A's question.
- The lineup score keeps a DNP at its real 0 (what the contest pays); that is where A's accuracy shows.
- Statuses (Q / D / OUT, practice, roster, DraftKings' tag) are descriptors for after-the-fact study through p.descriptors() only; never inputs (guard check 10).

## Certainty + boom + beat/fall-short (2026-10-02; history only, no price; walk-forward tests 2020-25; 10-draw whole-search null)
- facts: red-zone / goal-line targets, carries, attempts and shares from play-by-play (outcomes); player rz opps vs team rz plays corr 0.971.
- Certainty (steady points = yards + receptions): beats season-to-date on steady and total DK points - RB +0.013/+0.014, WR +0.017/+0.017, TE +0.016/+0.016 (5/5).
  QB: steady-only loses on total points (-0.033, 1/5) - passing TDs are too large a share; QB ranks by season points.
- Beat median (falls short = 1 - p): all positions above null, calibrated both directions (low fifth ~30% -> 29-34%, high fifth 62-70% -> 60-68%).
- Boom (>= 1.5x own median and +5): QB +0.028, WR +0.013, TE +0.011 log-loss gain, calibrated; RB +0.001 - probabilities near base, ordering still separates.
- Within certainty quintiles the boom score separates booms: WR every quintile (e.g. Q3 17% -> 28%), TE top quintiles, RB low-mid, QB low certainty.

## Deep rules (2026-10-02; find 2019-21, refine 2023, confirm 2024 + 2025; whole-pipeline null)
- Slices: role momentum (last-game snaps minus season snaps) moves next-game share - RB carry +5.7 to +7.4 pp up / -4.5 to -11 down, WR target +2.6 to +3.3 / -2.8,
  TE target +1.2 to +1.5 / -1.0 to -1.4; high season shares regress. Confirmed 18-30 per slice vs null 95th 0-1.
- Pie type: pass rate regresses to the league (+1.2 to +3.2 run-heavy, -3.5 to -7.9 pass-heavy); script from opponent history - pass-heavy vs weak offense -6.2 to -8.2,
  run-leaning + good defense vs decent offense +4.6 to +4.7; pass-funnel defense +1.9, run-funnel -2.2. Confirmed 28 vs null 0.
- RB boom: low median + usage up >= .15 -> +17 pp; mid median + usage falling -> -12; high median + TD-heavy -> -6 to -11. All three bands above null.
- TE beat median: mid median + last-3 snaps > .63 -> +24 pp, TE1 slot +11; high band not above null; median-0 band largely definitional.
- QB beat median: none confirmed (about 380 find rows per band).
- Caveat: targets are deviations from season rates, so season-level splits include regression to the mean; usage-trend rules are not mechanical.

## Stress test of the six empty roots (2026-10-02; plot points as coordinates / residualizers / chain links; twins + nulls)
- A1 pie size LEVEL: shrink team plays toward the league (training strength 0.20-0.30 of the season deviation); level error cut at every position
  (QB opps -0.154 5/5*, RB/WR/TE opps *, steady levels QB/RB/TE *). Rank of plays still unpredictable.
- R7 trajectory analogs blended with logistic on transition rows: boom RB +0.0064*, WR +0.0081*; beat RB / TE 4/5 just under the gate. Analogs alone lose.
- R2 script elasticity: only QB carry share responds to expected margin (+0.063 5/5, above shuffled refit); slice forest gains nothing.
- R1 expected vacated share: availability of last game's roster predictable (+0.10-0.13 log loss/season); shares rise +0.04-0.06 (5/5) but nothing beyond role momentum.
- Retired for good: pace / plays shifts (inconsistent, forest worse), discipline (stability +0.076 < 0.1 pre-set), situation (5-6/72 vs 2.2 chance,
  contradictory), dead roots on the leftover (nothing at any position). R8 co-movement flat by expected margin and usage.

## Grid (grid.py): exhaustive target x shrink x regime x position
- 26,928 cells; 4,594 confirmed vs null mean 6.9 / 95th 18.2. ~39% are level targets (DK 902, steady 892) that mirror player level; red zone and volatility hit rates are mostly this mirror.
- Stage 2 against the plot-point model with twins: QB qgap +0.010, QB lead_plays +0.007, QB slot_boom +0.005, RB t_steady block II +0.0065. QB returning flagged ADDS but beats its twin by only +0.004 (s.e. 0.015): not counted. WR adds nothing.
- Stage 3 confirmed rules with variants: QB 11, RB 63, WR 32, TE 22; ~1/3 distinct after threshold twins.
- High-median bands at every position: no beat rules; only boom-down via TD regression.
- Untested: price file; interactions deeper than the stage-3 trees.

## Class A (who is on the field) - results, Oct 2 2026
- synergy.py: stubborn topics give no whole > parts (whole 0/21, chains 0/16, matrix 8/672 ~ chance); additive beats deeper interaction.
  Only coherent cells: teammates / absence x plot points on WR TD change.
- causal_a.py (clean onsets, ~45 episodes per outcome): TE target share passes every gate (k=0 +.019, k=+1 +.0125, pre clean, 4/4 seasons);
  WR targets and RB carries rise BEFORE the absence (role holder fading - the partial-game gap); target conservation .76, carries .18 (unresolved);
  no player-level absorption trait (A6).
- alloc.py (pre-registered, all rows 2019-25): general vacancy-bounded positive correction to target share CLOSED for the producer
  (beyond twin +.00002; residual fails).  TE: mechanism real but already inside momentum.  RB: negative.  WR: +.00018 share beyond twin
  (~0.01 DK pts) - not pursued.  Version B (a.py weighting) dropped: domain covers ~1/3 of absences.
- Open: carry balance sheet (A-C).  Stated for 2026 evaluation, not searched further: vacancy moves WR TD / red-zone opportunity rather than target share.

## Center of gravity (Oct 2 2026)
"Keep turning one vague ceiling into smaller falsifiable walls until only irreducible uncertainty remains."
Every test is written as ONE wall:  claim -> observable implication -> intervention -> pre-registered success condition -> next wall if it fails.
Account for the mass before inventing a model (balance sheets first).  A wall that passes is frozen; a wall that fails names the next one.
Data already looked at may diagnose or adjudicate only under a rule frozen beforehand; it never counts as clean confirmation. 2026 weeks are the final judge.

## Yardstick walls so far
- v1 universal shape: failed (bust 0% bottom tiers, ~20% elite; WR runs carried).
- v2 shrunk + recency center, per-center-fifth shape: fail 64% -> 31%; boom calibrated (off 7% dev / 4% 2024-25); WR runs flat;
  RANGE bands were an artifact (spread from the center alone wins).
- ceiling.py: remaining wall = floor geometry INSIDE the fifths for RB / WR / TE (bust sawtooth +4.1 / +5.0 / +3.0 pp; bottom center tenth busts ~0.3%).
  QB: no sawtooth; 2025 bust 14.8% recorded as a drift hypothesis for 2026, not fitted.
- floor_test.py: floor-relative downside coordinate erased the sawtooth but broke calibration (fail 42.9% -> 57.1%) - V3 not earned.
- regime_test.py: role-collapse wall FAILS (ordinary-game sawtooth barely moves).  Role collapse itself is real and predictable pregame
  (log-loss beyond twin RB +.044, WR +.069, TE +.033, calibrated) - recorded for availability / opportunity, not the yardstick.
  Pooled ordinary distributions fail 64-71%: the miss distribution depends on level - settled.  Near-zero oracle split: fail 16.7%.
- Canonical sawtooth: fold training cuts, per season.  2024-25 is no longer used to invent or modify yardstick architecture; it may be used only for
  the pre-registered S-vs-SC adjudication already specified.
- smooth_test.py: S EARNED (pre-registered; diagnosis pointed to the ordinary distribution first): moving-fifth ordinary distribution (nearest 20% of
  training centers) - sawtooth RB 1.2 / WR -0.1 / TE 2.4 (TE reduced below the threshold, not eliminated); bust off 11.9%, boom off 9.5%.  WIN = 20% frozen.
  C (isotonic pi) fail 9.5% but missed the sawtooth gate; seen on dev - challenger for 2026 at most.
- STOP RULE (owner): when remaining calibration failures are noise-like (fail rate within a perfectly calibrated yardstick's 95th on the same rows and
  subgroups), stop optimizing calibration; the question becomes "among sufficiently calibrated distributions, which is sharpest?" (CRPS).
- residual_s.py (dev): calibrated-yardstick fail-rate null mean 5.4%, 95th 14.3% (THIS grid and row count only - recompute per evaluation).
  S 26.2% (structural; 11 fails: Ford 5, pi 2, both 1, neither 3; 8 repeat every season).  C / SC 9.5% noise-like.
  CRPS: S best by 0.003-0.007 DK pts over SC / C (~0.1%), all far better than v2 (+0.044).  Architectural ceiling broken:
  P(near-zero) + ordinary distribution moving with the center.  Remaining question is calibration at the data's resolution, not structure.
- Frozen: S (reference), SC (calibration challenger), C (diagnostic only).  adjudicate.py selected SC on the partially used 2024-25 holdout
  under the pre-written rule; 2026 weeks 4-16 confirm.  No Ford changes built on 2019-23.

## YARDSTICK - frozen Oct 2 2026 (calibration research on 2019-25 STOPS)
- RB / WR / TE = SC:  F(y) = pi* F0(y) + (1 - pi*) Ford(y | c)
    center c: shrunk mean (toward position x role-state peers, strength fit in training) + recency (last game, last 3, snap swing), OLS in training
    near-zero state: DK <= 1;  pi = logistic on [center, season / last-game / last-3 snap, |snap swing|, season / last-game / last-3 opportunities,
        games, missed last game];  pi* = isotonic map fit on season-cross-fit training predictions
    F0 = training DK scores of near-zero games (per position);  Ford = misses / spread (spread from the center) of the nearest 20% of training centers
    RESULT: near-zero game = pi* x F0-percentile; otherwise pi* + (1 - pi*) x Ford-percentile (randomized ties).  bust < 10, boom >= 90.
- QB = v2 (shrunk + recency center, per-center-fifth shape): no sawtooth; 2025 bust excess recorded as a drift hypothesis.
- adjudicate.py (2024-25, partially used holdout): SC fail 10.3% = null 95th 10.3% (noise-like, at the boundary); S 15.4%; CRPS SC - S +0.0012 +- 0.0014.
- 2026 CONFIRMATION RULE (weeks 4-16, nothing changed before then): recompute the calibrated-yardstick null on those rows and the same subgroup grid;
    SC noise-like -> confirmed (if S also noise-like, CRPS decides; no difference -> SC stays);  only S noise-like -> S;
    neither -> reopen the ordinary distribution / calibration research.
- Frozen with it: DK <= 1, the logistic inputs, isotonic procedure, WIN = 20%, subgroup grid (tier, role state, week block, season), null procedure, CRPS rule.

## Y - performance distribution (Oct 2 2026): ystick.py is the ONE producer of the history-only predictive distribution and RESULT
- F -> Y -> P;  Y feeds studies B / C / D / E, J diagnostics and the pick card; L consumes RESULT, never creates it.
- proj/ystick_rows.csv.gz: history (walk-forward) and coming-week rows in one schema; RESULT only once the game is history; no fill (unprojected counted).
- Self-check: 2024-25 RB / WR / TE reproduces adjudicate.py's SC fail rate (10.3%).
- Pick card = thin reader of Y + P: CENTER | TIER | NEAR-ZERO % | P50 | P90 | VALUE (from P) | WHY (descriptors only, never a second vote).
  No boom % (10% for everyone by construction).  No labels (Attack / Trap) until a frozen label rule is judged by L on 2026 weeks.
- Class D note: dependence on RESULT uses z = Phi^-1(RESULT) if J's Gaussian copula is the consumer.

## CLASS B - short history (1-2 earlier games this season), closed
Balance sheet (classb.py): QB outside Y 19.5% of games / 7.8% of points; 2026 w4 188 unprojected, 24 real-role (QB 11, WR 10, TE 3, RB 0).
Wall (shorthist.py): P0 peer-only vs P1 (n*own + k*peer)/(n+k); gates: center error gain, fail rate <= calibrated 95th, CRPS not worse; dev AND 2024-25.
Team changes excluded (29 rows); folds below 80 training rows skipped (QB 2020, TE 2020).
WR  - EARNED (dev boundary pass 20.0% = 20.0%; 2024-25 pass) -> ystick.py model "WR-short".
TE  - PROVISIONAL: passed, but dev coverage 2 of 3 seasons after the declared floor; held back as a judgment beyond the literal rule.
QB, RB - NOT EARNED (dev fail 28.6% vs 15.0%, 46.2% vs 23.1%); stay unprojected at 1-2 games.
Frozen: the training k-selection procedure, not a numeric k.  2024-25 here is a same-rule consistency check (classb.py had shown outcome summaries), not clean confirmation; 2026 w4-16 judges.

## CLASS C - scoring-composition persistence, closed
classc.py: does last game's split (steady = yards + receptions vs season-to-date; TD points vs season-to-date) predict z = Phi^-1(Y RESULT)
beyond the frozen Y center (which already holds dk_ws and dk_w1)?  Walk-forward, no intercept, gates: > 2 s.e., positive every test season,
above the whole-pipeline twin 95th; dev AND 2024-25.
Balance sheet (share of last-game surprise): QB steady 35% / TD 53% / other 11%; RB 53 / 41 / 6; WR 63 / 29 / 8; TE 59 / 36 / 5.
Z of Y: mean |.| <= .010, sd .985-1.028 at every position.
Result: 0 of 12 earned (Q1 steady, Q2 TD, Q3 both x 4 positions); none above twin 95th in either period; steady part harmful on dev for QB and RB.
Signs inconsistent with "steady persists, TD regresses" except a faint WR pattern.  No composition correction enters Y.
Untested: persistence beyond one game back (no wall opened).

## CLASS D - shared-game dependence on the Y scale, closed (player side)
jy.py: same games, slots (j.build), cells and folds; J's pooled per-slot conversion vs z = Phi^-1(Y RESULT) for player slots (DST on J's scale both
times: Y has no DST).  Cells used only where J has a residual AND Y a RESULT: 11,728 of 11,908 (98.5%); Y seasons 2020+ (not J's 2016+ window).
Spec chosen on dev (2021, 2023), carried to 2024-25.  Both scales choose FULL correlation; gain vs independence per game:
J dev +0.466 +- 0.045, 2024-25 +0.504 +- 0.060;  Y dev +0.484 +- 0.051, 2024-25 +0.522 +- 0.065; twins 95th -0.47..-0.67.  Artifact share -3.8% / -3.6%.
Verdict: J's dependence is shared-game co-movement, not a pooled-marginal artifact.  Key pairs (Y [J]): QB1~opp DST -0.38 [-0.33], QB1~own WR1 +0.35 [+0.37],
QB1~own WR2 +0.31 [+0.33], QB1~own TE1 +0.26 [+0.27], RB1~opp DST -0.24 [-0.21], QB1~opp QB1 +0.21 [+0.20].
Limits: dependence, not causation (rule 3 - J shapes the joint simulation only); DST pairs are mixed-scale until a DST yardstick exists;
factor compression not reopened (efficiency, not validity).

## Y SCOPE - a distribution GIVEN he plays (Class E (a), classe_bal.py)
Y history is played games only (rt.H, rt.X: played = 1 on every row): Y's calibration and near-zero % are conditional on playing.
Candidates weeks 4-16, 2020-25: 30,732; played 74.5%, did not play 20.8%, no player_game row 4.7%.
Absent share of candidates Y would price (dev / 2024-25):  all priced QB 27.1 / 26.4%, RB 21.6 / 15.2%, WR 17.6 / 17.2%, TE 12.8 / 11.7%;
real role (season snap >= .50) QB 17.4 / 18.6%, RB 12.4 / 8.1%, WR 10.5 / 10.8%, TE 9.0 / 7.0%.  WR-short real role 28.7 / 32.4% (n 122 / 68).
Consequences: the pick card's NEAR-ZERO % excludes absence and must say "if he plays"; 2026 confirmation of SC scores played games only (consistent).
Eligibility here mirrors ystick.py by earlier played games, not its missing-input drops (approximation).

## R1 - history-only absence component q, NOT EARNED (avail.py); Y stays a distribution given he plays this cycle
Priced candidates weeks 4-16, 2019-25: 31,071 (71 dropped: team change / first team-game); absent 17.6%.
Absent by team-games missed since last played: 0 -> 10.7% (n 26,964), 1 -> 59.1% (2,074), 2+ -> 67.5% (2,033).
M (logistic on snap_ws, snap_w1, n_prior, gap, miss_share + isotonic) ranks well: log-loss gain over role-state base rate +0.080 +- .004 dev,
+0.083 +- .003 2024-25; extreme fifths 2-6% vs 36-72% absent.  Calibration STRUCTURAL: M 20.8% vs 12.5% (dev), 40.9% vs 11.4% (2024-25);
B 56.2% / 56.8%.  As probability mass q must calibrate, so R2 (F_real = q atom at 0 + (1 - q) F_Y) is blocked.  No rescue variant on these seasons.
Class E (b): guard.py declares STUDY = {classe.py} - the only script that may call p.descriptors(); it writes only proj/study_*, which no other
script may name; p.py stays frozen.

## CLASS E (b) - week-N announcements vs history-only absence (classe.py, the declared study), own-player side closed
Descriptor coverage 96.7% of 26,003 priced-candidate rows (2020-25).  Played last game: T1 (Out/Doubtful) ~3% of rows, absent 99.5-100% (history q_M 16-18%);
T2 (Questionable / DNP / Limited) 6-8%, absent 20-22%; T3 (no warning) ~90%, absent 6.3-7.5% - the surprise rate even with the report.
Announced share of played-last absences (dev / 2024-25): QB 32 / 28%, RB 42 / 43%, WR 39 / 42%, TE 51 / 51%; missed-1+: QB 15 / 16%, others 30-45%.
Information value of the report beyond history: log-loss gain +0.073 +- .004 (dev), +0.089 +- .003 (2024-25) per slate; calibration still STRUCTURAL
(q_R 48% vs 12%, 50% vs 12%).  Reading: the information boundary costs much of the sharpness; it does not by itself explain R1's calibration failure.
Limit: R = pooled regularized logistic on [logit q_M, T1, T2] without an isotonic step - shows coarse tiers in that form do not calibrate, not that
the report cannot.  Game-day roster status (INA / RES / no row ~100% absent; ACT 4.5%) is near-outcome and stays descriptive.  Nothing enters Y.

## CLASS E (b) - teammate side: information-boundary cost MEASURED (classe.py section 5)
After a NEW absence (played last game) of a real-role player (season snap >= .50), same-position teammates exceed Y's p90 (RESULT >= 90) far above 10%,
beating 200 within-week shuffles, on dev AND 2024-25:  RB 26.7% / 36.2% (control 9.0 / 9.6%, n 135 / 58);  WR 14.6% / 17.1% (8.3 / 8.7%, n 843 / 550);
TE 14.9% / 22.2% (9.0 / 8.9%, n 161 / 81).  QB new absence -> WR+TE bust: dev 12.2% miss, 2024-25 10.6% absorbed - not earned.
OLD absences (also missed the game before) are absorbed: 7.0-15.1%, none beyond the twin - Y already sees them through the teammate's last game.
Reading: the miss exists only when the absence is new in week N, which the information set cannot see (the week's report and game-day roster are
excluded).  A conditional teammate shift has no pregame trigger under this charter, and a simulated-absence route needs a calibrated q (R1 failed).
So this is the measured cost of the information boundary, not a Y defect.  WR announced 14.5% vs surprise 14.9% (dev): the realized absence, not the
report, moves teammates.  Nothing enters Y.

## CLASS E - CLOSED for the current track (owner decision, 2026-10-03)
Current Y is the distribution under the restricted information set (results through N-1 + week N's price file), given he plays.  Class E measured the
price of excluding week-N availability information: own-player absence (R1 not calibrated; report adds sharpness, not calibration) and teammate tails
after a NEW real-role absence (RB / WR / TE beyond p90, both periods).  No correction enters Y: no legal pregame trigger, no calibrated history-only q.
2026 weeks 4-16 judge the frozen current architecture only; they are not used to decide whether to reopen Class E.
Optional, after the 2026 cycle: a SEPARATE late-information track (Y_late = restricted Y + week-N availability) with its own information timestamp,
backtest, freeze and confirmation - a new forecasting problem, never an amendment to this Y.

## DST YARDSTICK - V1 EARNED (dstick.py)
Rows rt.DT (weeks 4-16, 3+ earlier team-games), 2,304; DST points integers (-4..35), randomized discrete PIT.  V1 center = own season-to-date DST mean shrunk
toward the training league mean (k chosen in training by MAE: 8 dev, 12 2024-25) + OLS on oppo_pts_for_ts, oppo_giveaways_ts, oppo_sacks_taken_ts;
spread from the center; shape = nearest-20% training centers; no near-zero state.  Calibration fail V1 0.0% vs 15.4% (dev), 0.0% vs 17.1% (2024-25);
V0 (own history only) 23.1% vs 23.1% boundary.  CRPS V1 over V0 +0.043 +- .018 (3/3), +0.090 +- .025 (2/2).  Bust 10.0-10.2%, boom 8.5-9.0%.
Frozen: the candidate family and the training rule for k, not a numeric k.  Grid is coarse (12-13 subgroups).  Recency not tested (rt.DT has no DST w1/w3).
Does not alter s.py (DST price alone) or the L v2 path.  Coming-week DST rows = integration step, still to do.

## CLASS D - CLOSED including DST (jy.py dst mode)
DST cells limited to dstick V1 rows (1,920 of 1,920 kept).  Scale YD = players on Y, DST on dstick V1 (every slot on its own calibrated scale).
Spec chosen on dev = full on J, Y and YD; gain vs independence per game: J +0.466 / +0.504, Y +0.484 / +0.522, YD +0.579 / +0.590 (dev / 2024-25);
all pass p.gate and the shuffled twins (95th <= -0.47).  YD DST pairs: opp QB1 -0.41, opp RB1 -0.30, opp WR1 -0.15, opp DST -0.21; own offense |r| <= .09.
Verdict: J's dependence is shared-game co-movement on a fully single-scale setup.  Cross-scale gain ratios (YD -24% / -17% vs J) are description only.
jy.py default run unchanged (byte-identical); dst mode is a validation path - j.py, j_model.json and s.py untouched.

## DST INTEGRATION - dstick.py is the DST marginal producer (coming week)
python3 dstick.py SEASON WEEK: V1 fit on every season <= FROZEN_THRU (k chosen in training: 20 on 2019-25), inputs from rt.TG / rt.OPPO dated before week N;
writes center, p10 / p50 / p90, tier (RESULT empty until played).  2026 w4: 32 of 32 team-games projected.  History rows unchanged (verified identical).
Consumers: the pick card and validation (jy.py dst mode).  s.py keeps DST price alone (frozen for L v2).

## CARRY BALANCE SHEET - accounted (carries.py), Class A-C open item closed
Episodes: a real-role RB (season carry share >= .40, 3+ games) newly absent; 111 team-games 2020-25 (dev 80, 2024-25 31); exact identity (max error 5e-15).
Shares of vacated carries (~14 per game), dev / 2024-25: baseline RBs 65.6 +- 5.0 / 87.1 +- 10.9%; new RBs 9.3 / 10.2%; QB -1.2 / +3.9%; WR+TE 2.0 / 0.9%;
net vanished (team ran less, net of control drift) 29.3 +- 5.9 / 0.7 +- 11.4% (difference ~2.2 s.e., 31 late episodes - possible regime change, not settled).
causal_a's .18 is NOT reconciled to a component: the two differ in scale (share vs count), episodes (clean onsets vs all new absences), baseline and population
at once.  Settled: .18 is not total absorption - the carries go mostly to other RBs.  Accounting, not a projection coefficient; no pregame trigger exists.

## CARD READER - thin integration, frozen (card.py)
python3 card.py SEASON WEEK joins s.py's slate rows (base; every slate row kept), Y (players, by gsis) and dstick V1 (DST, by team).  Fits, ranks and labels
nothing; order = position then salary.  Y / dstick columns are distributions given he plays (NEAR-ZERO IF PLAYS; "<0.1%" below 0.05%; blank for QB / DST);
P PROJ, S EXP, S P_PLAY, S BASIS are the frozen projection track shown beside Y, never merged.  No VALUE column: no producer writes a coming-week value
(p.py change, frozen for L v2).  WHY = descriptors only (short history, unprojected + position-specific reason, S basis, P - Y center gap).
No sorting by P - Y, p90 or tier and no Attack / Trap labels until a frozen label rule is judged by L.

## A AVAILABILITY AUDIT - strong, subgroup-STRUCTURAL, not reopened during L v2 (aaudit.py)
a_walk (a.py out-of-sample p_play): 9,469 priced rows, 2020-21 only (no 2024-25 priced walk - no contemporary confirmation possible).  Aggregate: mean
p_play 96.7% = played 96.7%, Brier .0277, deciles close.  R1's subgroup check: 16.4% vs null 95th 10.9% -> STRUCTURAL; missed-1+ players p_play 93.5% vs
played 87.3%; played-last 97.9% vs 98.4%.  Same rows as R1 (8,489): log-loss p_play .0825 vs 1 - q_M .1919.  R1's verdict (no availability atom in Y)
stands; A stays as the frozen participation input S multiplies into exp.  Card column renamed "A P_PLAY".  Revisit A only after the 2026 cycle.
Open: the historical priced universe played 96.7% vs 74.5% of candidates - possible outcome-selection of historical salary rows (being read).

## HISTORICAL PRICED ROWS ARE OUTCOME-SELECTED (read, Oct 3 2026)
Candidates weeks 4-16 (QB / RB / WR / TE) with a historical salary in load(): played 97.5-97.9%, did not play 9.5-11.3%, no row 0% (2019-21; no salaries
2023-26).  A priced history row nearly implies the player played; the mechanism (source construction vs pre-lock removal) is not measured.
Implications (inferred, untested): A's p_play was fit and audited where absence is rare (3.3%); P's projection is effectively conditional on playing;
on the live pre-lock slate S's exp = pred x p_play is closer to "if he plays" than to an unconditional expectation.  Nothing changes during L v2
(L judges the frozen method by realized points).  First live-universe test of A: week-4 slate p_play vs realized played, after the games.

## S NAME MATCHING - no projectable player lost (read, Oct 3 2026)
2026 w4: 231 slate rows without a gsis (s.py matches names.norm + team against this season's earlier rows).  Same normalized name with 3+ played 2026
games before week 4, on any team: 0.  Every unmatched row is a player Y could not project (< 3 games); no loss to spelling or trades.
Week-4 WR-short: 50 rows, 8 with season snap share >= .50, 42 below.

## GATE OPERATING CHARACTERISTICS (gatesim.py) - the calibration gate's resolution
Same rows and grid as Y's SC verdict (42 / 39 subgroups), 200 simulated outcome sets per scenario.  False alarm (calibrated): 1.5% dev, 2.0% 2024-25 -
conservative.  Power: too narrow x1.05 (tails ~11.1%) 74% / 46%; x1.10 (~12.2%) 100%; shift +0.05 51% / 25%; +0.10 ~100%; one tier x1.30 97-100%;
one-season drift +0.15 82-86%.  The gate reliably catches miscalibration that moves boom / bust to >= ~12%; errors of ~1 point in tail rate pass about
half the time.  Each subgroup is ~2.5 points of fail rate, so 4 vs 6 failing subgroups flips a verdict, and the null 95th itself moves by a subgroup
between draws.  On the published Y file's tiers (re-ranked after WR-short rows were inserted) observed fail = 14.3% vs 12.0% (dev), 15.4% vs 15.4%
(2024-25) - SC's verdicts were 9.5% / 10.3% on its own tiers; mechanism being read.  Nothing reopens before the 2026 cycle.

## PIT SERIALIZATION + SALARY FRAME (reads, Oct 3 2026)
result_pct is rounded to 0.1; 1.13% of 2024-25 SC rows sit exactly on a decile edge after rounding.  Recomputed from the file: 6/39 = 15.4%; with edge values
nudged below the edge: 4/39 = 10.3% = ystick.py's in-memory check.  SC's verdict (in-memory PIT) stands; result_pct is a display field, never a test input.
Data-contract fix pending: a full-precision result column beside result_pct.  Dev on SC-only tiers 5/42 = 11.9% (boundary pass at 12.0%).
2016-21 salary source lists participants, information time after inactives (CHARTER scoring notes); measured: priced 97.5-97.9% of players who played vs
9.5-11.3% of those who did not (2019-21).  P / A history = the after-inactives frame; the current information set is stricter (pre-lock).  Domain mismatch recorded.
2022: used in earlier development (e.g. "learned from 2016-2022"), deleted as dirty - not a lockbox.  2026 weeks 4-16 remain the only fresh judge.

## 2026 PROSPECTIVE REGISTRATION (register.py -> proj/register_2026.json, read-only, stamped before the first eligible week-4 kickoff)
H1 SC confirmation (PRIMARY, per the CHARTER 2026 section embedded verbatim); H2 DST-V1, H3 WR-short, H4 A p_play live (audit), H6 week-N salary change as a
role trigger (secondary); H5 new-absence teammate tail (descriptive).  Power stored with it.  Nothing else is confirmatory in 2026; post-kickoff findings ->
POST-2026 WALLS.  No statistical test consumes result_pct.  Method for every blocker: BLOCKER -> LEGAL OBSERVABLE -> FROZEN TEST -> PASS / CLOSE; never rescue
a failed branch except for a mechanical / accounting bug; calibration first, sharpness second.

## 2026 REGISTRATION - witness and power (stamped 2026-10-03 11:21:38 UTC, before the first eligible kickoff)
proj/register_2026.json SHA-256 9e16b3f019010740036546c82b3641f9994d1a30b979a31ac46e3fd5526d6d78 (read-only).
Power, fixed before any result: H1 SC (3,939 rows) tails ~12% 64%, ~11% 4%; H2 DST (416) 15% / 5%; H3 WR-short (650) 27% / 10%; H4 A absence x1.5 100%;
H6 salary trigger (~424 rows) boom 15% 89%, 20% 100%; H5 teammate WR 75% at 15%, RB 23%, TE 26%.  Reading: H1-H3 passes mean only "no gross miscalibration";
fails are informative.  H4 and H6 are this season's sharp tests.
Registered producer hashes freeze ystick.py / dstick.py for the cycle: the full-precision PIT fix moves into the scorers (they compute PIT; never result_pct).

## 2026 REGISTRATION ADDENDUM - H1 pointer corrected (mechanical; stamped before the first eligible kickoff)
register.py embedded the wrong section for H1 ("Deep rules ... confirm 2024 + 2025", matched on heading words).  proj/register_2026_addendum.json
(read-only) embeds the correct text: the YARDSTICK section with the 2026 CONFIRMATION RULE (fixed Oct 2).  No rule changes; the original file and its witness stand.

## 2026 ISSUANCE - week 4 forecasts frozen before kickoff
H1 clarified (proj/register_2026_addendum2.json, read-only): SC only; S has no 2026 issuer and is not evaluable; SC noise-like -> confirmed, structural -> reopen
after the cycle.  score_y.py validate: witness OK, addendum present, scorer grid reproduces 4/39 = 10.3%.  Issued (read-only pickles, scored later from these only):
proj/issued_y_2026_w4.pkl (379 rows identical to stored, SHA b1949a8d...eea4) and proj/issued_d_2026_w4.pkl.  Scoring refuses if the producer or its training
frames changed since issue.  Weekly before kickoff: ystick.py / dstick.py 2026 N, then score_y.py issue 2026 N and score_d.py issue 2026 N.
Still to write before the first judgment: H1 / H3 judge, H2 score + judge, H4, H5, H6 scorers - all hashed before use.

## 2026 WITNESSES (before kickoff, Oct 3 2026)
register_2026.json 9e16b3f0...6d78 | addendum (H1 pointer) 7b6b4bbd...9747 | addendum2 (H1 = SC only) c46a9a88...645a7b (stamped 11:36:55 UTC) |
issued_y_2026_w4.pkl b1949a8d...eea4 | issued_d_2026_w4.pkl 89afd19e...38fd.  score_y.py judge: H1 / H3 decide only when weeks 4-16 are all scored (INTERIM before).

## 2026 SCORER WITNESS (all validated on history before any 2026 outcome was scored)
score_y.py d74cbb495c9ef986 | score_d.py a37886d3489b40ef | score_s.py e95b449806d205c7 | score_t.py ffdf5de705b0a9d5 |
score_y validate 4/39; score_d validate 0/12 + 0/13; score_s validate 9/55; score_t reproduces classe 2024-25 cells.  Issued slate w4: issued_s_2026_w4.csv 0ad5baf5...f6be.
A scorer changed after this entry scores nothing until re-validated and re-witnessed.

## GATE OPERATING CHARACTERISTICS 2 (gatesim2.py) - what the other verdicts are worth
DST-V1 grid (13 / 12 subgroups, 7.7-8.3% each): false alarm 3-5%; tails ~12% (x1.10) caught 41-53%, ~14% (x1.20) 96-99%; shift +.10 33-36%.
  V1's 0/13, 0/12 exclude only gross miscalibration; V1 was chosen on CRPS.
WR-short grid (7 / 6 subgroups, 14-17% each): x1.10 caught 5-9%, x1.20 30-49%, shifts <= 3% - calibration essentially UNTESTED at useful resolution;
  WR-short rests on center error gain + CRPS.  (2026 H3 power already recorded as weak.)
A binomial grid (36 subgroups): absence x1.25 caught 96.5%, false alarm 5% - A's STRUCTURAL verdict is informative.
p.gate (3 x 13 / 2 x 13 slates, gains N(delta, 1)): no season effects - false pass 2-2.5%, delta .3 passes 29-41%, .5 69-86%;
  season effects sd .5 - FALSE PASS 14-19% (p.paired's s.e. treats slates as independent; "all but one season" with 2-3 seasons barely protects).
  Readings: p.gate passes may be false where gains vary by season; p.gate closures exclude only effects >= ~.5 slate-sd.
  2026 registration uses no p.gate.  POST-2026 procedure wall: season-clustered or season-permutation gate.

## P.GATE AUDIT (pgate_audit.py; 12 scripts re-run unchanged, writes blocked, 0 files changed)
183 gate calls, 47 passes; season effect tau/sigma (slate-sd units) per pass.  ONE season-sensitive pass: shorthist QB 2024-25 center gain +0.874 +- .234
(seasons +1.40 / +0.35, tau/sigma .62) - QB short history was never earned (dev calibration failed), so no binding verdict rests on it.
Robust: DST-V1 CRPS gain (margin 2.4 / 3.5, tau 0, cluster t 5.3 / 7.4), Class D jy gains (margin 2.1-10.4, tau 0), J factors (5.3-8.8), WR-short center
gain (5.6, tau 0), A inputs (4.5-10.8), avail / classe sharpness (18-31), zero_test / regime_test (5.6-22).  alloc passes tiny (~.0003 share) - closure stands.
Reading: gatesim2's p.gate weakness does not touch any binding verdict.  Season-clustered gate stays a POST-2026 procedure item for future walls.

## CHAIN OUTCOME - Oct 3 2026 (chain.py, run once as pre-registered; proj/chain_report.txt)
W1 timing threshold FAILED: r* (2023-25 isotonic P(absent | r1) crossing base 5.3%, starters n 5177) = 0.873 [0.802, 0.901]; per season 2023 0.901,
   2024 1.000 (outside), 2025 0.878 -> timing NOT separable; A + B pooled; PRIMARY NOT JUDGED.  First NO = the ceiling.  Not rescued.
DESCRIPTIVE ONLY (downstream of the failed wall; AB = non-fading new real-role absence, not "in-game exit"), 2019-21, team-season bootstrap:
   pooled AB (429 event backups vs 3380 control): price +153.1 [+110.8, +199.1]; placebo (one team-game earlier) +3.4 [-18.1, +24.5];
   role +0.194 [+0.168, +0.217]; +$300 tail boom +0.129 [+0.015, +0.234] (n 58, mdd 0.160 - below detectable).
   C fading (98): price +68.7 [+8.7, +146.9]; role +0.177 [+0.135, +0.225].  Price by position: RB +444, TE +95, WR +82; role +0.18-0.22 in all.
CONVENTION: chain snap_before = mean snap over the backup's earlier PLAYED games this season on this team (absences not zero) - not snap_ws.
NOT A BUG: a relayed "CTRL stratum collision" is false - STEP 3 merges EV[TK + pos] (keys only); the run reached every d.stratum cell.
POST-2026 WALL (designed on seen 2019-25 data, so confirmable only prospectively): W0 timing signal in pre-declared coarse r1 bins; monotonicity
   before any threshold; W1 crossing stability; then W2 price, W3 role, W4 tail, read sequentially (first NO stops); tail companion = A&dsal>=300
   vs control&dsal>=300 (descriptive).  Timing state from pbp last involvement replaces snap ratios when that facts column exists.  H6 unchanged.

## J TAIL DIAGNOSTIC - Oct 3 2026 (jtails2.py; proj/jtails2_report.txt) - residual shape miss, no earned replacement; J unchanged
FIXES of jtails.py: full-precision PITs (Y in-memory result, DST file result); Gaussian benchmark re-evaluated per bootstrap resample; family null of
   200 Gaussian-copula twins with W's correlation and missingness; primary on per-pair rank normal scores (copula only), PIT scale beside it.
T2 rank-scale co-moving misses 3/16 vs twins mean 0.28, 95th 1.0, max 3 -> PASS.  T3 all three season-stable 5/5, all DEFICITS vs Gaussian:
   QB1~WR1 ll -0.0080 [-0.0137, -0.0018];  QB1~opp QB1 ll -0.0099 [-0.0159, -0.0026];  RB1~opp DST lu -0.0102 [-0.0146, -0.0051].
T4 own-team QB1 exp tier (same season's earlier-weeks median): no corner state-specific.
T5 walk-forward rotated Gumbel vs Gaussian (held-out log copula density): QB1~WR1 pooled +0.0072 [-0.0012, +0.0161] (3/4 seasons +);
   QB1~opp QB1 +0.0057 [-0.0024, +0.0146] (4/4 seasons +; fails on the pooled interval - not rescued); RB1~opp DST -0.0026 [-0.0090, +0.0048] -> none earns.
SUPERSEDES the tail reading in "J JOINT TAILS + SALARY TIMING": the QB1~WR1 upper-tail excess was marginal, not copula (rank-scale uu +0.0049
   [-0.0027, +0.0132]); likewise QB1~opp QB1 uu and WR1~opp DST lu.  Slot PIT tail rates (descriptive, no null): WR1 11.1% / 8.9%, QB1 10.0% / 11.0%,
   RB1 10.1% / 8.9%, WR2 8.7% / 10.0%, TE1 10.5% / 10.1%, DST 8.8% / 10.2%.
POST-2026 WALLS: corner-deficit copula family chosen from structure, not from these three corners; slot-conditioned Y tail calibration (needs its own null).

## J TAIL POWER - Oct 3 2026 (jtail_power.py; proj/jtail_power_report.txt) - procedure characteristics under a known thinned-corner deficit
WORLD jtails2 geometry (960 games, real mask, rank-scale corr); TRUTH Gaussian with QB1~WR1 ll, QB1~opp QB1 ll, RB1~opp DST lu thinned by rejection,
   calibrated to dose x historical d (pi cap .98); 200 worlds per dose.
CALIBRATION: dose 1 reached QB1~WR1 -0.0080 and RB1~opp DST -0.0102 on target; QB1~opp QB1 capped at -0.0072 (target -0.0099), and FALLS to -0.0063 at
   doses 1.5-2 (shared QB1 rejections) -> the historical QB1~opp QB1 deficit is larger than thinning can produce: the real shape is not pure thinning.
DETECTION (dose 1): P(T2) .52; per corner P(miss & T3) QB1~WR1 .72, QB1~opp QB1 .45 (under-dosed), RB1~opp DST .95; all three .30.  Dose-0 T2 95th = 2.0
   (jtails2 twins 1.0: same null, discrete edge; historical count 3 exceeds both).
REGISTERED READING: P(Gumbel earns | T3) 0/89, 0/76, 0/101 -> MODEL FAMILY: rotated Gumbel cannot represent a PURE thinned-corner deficit even when true.
   Scope: not shown for the real shape (historical rank-scale uu +0.0049 / +0.0095 beside the ll deficits; Gumbel season d positive 3/4 and 4/4 historically).
OPEN (POST-2026, in order): (1) lineup relevance of the corners, G vs corrected-J, no outcomes; (2) oracle - does the TRUE local-correction model earn T5
   at this sample size; (3) only if (1) matters and (2) has power: a local family (corner reweighting / checkerboard / Gaussian + empirical tail mixture).

## J CORNERS - LINEUP RELEVANCE - Oct 3 2026 (read of s.py run, lines 22-70) - structurally zero in L v2
s.run selects the lineup by best9 on K.exp = pred x p_play (line 30); J (j_model.json) enters only after selection (lines 35-49), as a Monte Carlo of
   the chosen lineup's total -> dist (mean, p10, p50, p90, outside_slots).  Corner deficits therefore cannot change lineup identity, stack choice or
   regret in any frame (historical, issued 2026 w4, salary-shuffled) - the three-frame comparison is not run (it would print zero by construction).
   Only the displayed distribution of the chosen lineup can move, and only for lineup pairs that map to J slots.
Also read: sources/raw/dk_weekly holds DK_2026_w3 and DK_2026_w4 only - historical weeks cannot run through s.run; proj/s_2026_w4.csv = issued_s (cmp SAME).
POST-2026: corner relevance becomes a question only if a lineup objective that USES J (e.g. P(top 1%)) is designed and gated - then G vs corrected-J
   on that objective is its first wall.

## J CORNERS - DISPLAY (F2) - Oct 3 2026 (jdisp.py; proj/jdisp_report.txt)
G re-statement of s.run's Monte Carlo = s.run's own dist exactly (mean 140.222, p10 110.454, p50 139.247, p90 171.005, outside_slots 1).
Issued lineup holds no full target pair (one end only: Allen H_QB1; Addison H_WR1, Meyers A_WR1; Walker A_RB1, Jeanty H_RB1).
C raw (thinned z through J's fixed margins) moved mean +1.70 - entirely MARGINAL distortion (E[total] is margin-only; per player Allen +.63, Addison +.36,
   Meyers +.35, Walker +.21, Jeanty +.20, Dolphins -.32) - a defect of the intervention, not a dependence effect.
C margin-preserved (rank re-mapped; copula-only, as jtails2 measured), dose 1, 200k draws: mean -0.03 +- .02 (rank-vs-ndtr offset, identical at every
   dose), p10 -0.12 +- .06, p50 +0.01 +- .04, p90 +0.09 +- .07 -> copula-only display effect on the issued lineup ~0.1 DK.
REGISTERED NEXT (before code) - J CORNERS - EXPOSED LINEUPS (F2 slate, no outcomes, display only):
   lineups: for each slate game and target pair whose two players both map to J slots and are projected (QB1~WR1 per team, QB1~opp QB1 per game,
      RB1~opp DST per team), best9 on exp with the pair forced (score +1e4, asserted both chosen), everything else optimal.
   worlds: G vs C margin-preserved, dose 1, 100,000 draws, common random numbers.
   per lineup: delta p10, p90, p95, P(total > G's own p99) (proxy - no contest field data); across lineups: Spearman of p90 and p95 ranks, G vs C.
   READING: operationally CLOSED iff for every exposed lineup |delta p90| and |delta p95| < half the median adjacent gap of G's sorted p90 (resp. p95)
      across the exposed lineups; else LOCALLY RELEVANT -> POST-2026 local correction for those pair structures only (never "replace J").

## J CORNERS - EXPOSED LINEUPS - AMENDED REGISTRATION - Oct 3 2026 (supersedes the REGISTERED NEXT block in J CORNERS - DISPLAY; no code yet, nothing seen)
WHY: s.run yields one lineup per slate (line 30) and only 2026 w3/w4 price files exist - no frozen candidate set exists, so it is generated pair-blind;
   a bare sign-reversal count is decided by Monte Carlo noise among near-ties, so reversals must be resolved.
CANDIDATES (F2 slate, exp only, before any exposure label): L0 = best9 on exp; ban-one tree to depth 2 (ban each L0 player -> re-solve; from each, ban
   each of its players, bans cumulative -> re-solve); dedupe.  Exposure labelled afterwards from J slots: none / QB1+WR1 same team / QB1+opp QB1 /
   RB1+opp DST / multiple.
WORLDS (100,000 draws; game latent draws, outside-slot draws and play/no-play draws fixed per game / per player, shared by every lineup and world):
   C0 margin-preserved pi = 0;  C1 margin-preserved dose 1 (pi from jtail_power_report);  C1' = C1 with an independent redraw stream (noise twin).
STATISTICS per ordering quantity (mean, p50, p90): resolved reversal = sign(D_ij) differs between worlds AND |D_ij| > 2 batch-means s.e. (20 batches) in
   both; reported for C1 vs C0 and C1 vs C1', by stratum of the pair (both unexposed / at least one exposed); Kendall tau; top-10 membership changes.
CHECKS: mean ordering C1 vs C0 has no resolved reversal (margins preserved); C1 vs C1' resolved reversals ~0 (noise floor).
READING: CLOSED iff C1 vs C0 has no resolved p50 or p90 reversal involving an exposed lineup beyond the C1 vs C1' count; LOCALLY RELEVANT iff such
   reversals exist and occur at a higher rate among exposed-involving pairs than among unexposed pairs; anything else (reversals spread evenly) ->
   the intervention is too global, recorded, not acted on.  Exposed lineups < 5 in the candidate set -> reported as "the optimizer's neighbourhood
   rarely holds these pairs" (itself the operational answer), not judged.

## J CORNERS - EXPOSED LINEUPS OUTCOME - Oct 3 2026 (jexpose.py; proj/jexpose_report.txt) - operational exposure CLOSES at W1
W0 pair-blind candidates from exp: 39 (sha256 883a05358ae2cacd...; L0 = issued lineup asserted); saturation depth-1 unique 8, depth-2 new unique 30,
   exp span 141.72 -> 138.32 (3.40).  Exposure labelled after the hash: target structures 0 / 39 (QB1+WR1 0, QB1+opp QB1 0, RB1+opp DST 0);
   negative control QB1+WR2 2.  W1 NO -> W2-W5 not judged (first NO is the ceiling; the tree is NOT deepened to manufacture exposure).
READING: J's three stable corner deficits do not intersect the lineups this optimizer considers.  Structural cause: s.run selects by best9 on exp with
   no dependence term, so pair structures enter only incidentally.  J tail branch CLOSED for the current architecture.
PROSPECTIVE (descriptive, no model change): each weekly issue may append jexpose's W0/W1 line (candidates, exposure counts) - an accumulating count of
   how often the frozen optimizer's neighbourhood naturally holds target exposure.  Reopens only with a selector that uses J (POST-2026 wall).

## SELECTOR ARCHITECTURE LADDER - H0 FEASIBILITY - Oct 3 2026 (reads: proj/p_coef.json, a_cells.json, j_model.json; CHARTER line 371)
Ladder (POST-2026 design): A0 best9(exp) -> A1 Gaussian-J reranker (argmax p90 over pair-blind candidates) -> A2 corner-corrected -> A3 direct scenario.
H0: frozen P train_seasons 2019-21 (all positions), A train_seasons 2019-21 (14,001 rows), J seasons 2019-21 + 2023-25 -> a historical A0-A3 test with
   frozen fits is fully IN-SAMPLE.  Salaries exist 2019-21 only (DST 510 / 508 / 544 rows), so honest walk-forward refits reach 2020-21 (~26 slates)
   at most, on pools that are OUTCOME-SELECTED (priced: played 97.5-97.9%, not played 9.5-11.3%).
Power (estimate, not a wall): lineup total sd ~24 DK (issued lineup p10/p90 110/171); paired difference sd ~24 -> MDD ~13 DK on 26 slates, ~19 DK on 12.
READING: realized-outcome walls W1-W3 are blocked for this cycle (in-sample or underpowered, and selected).  Open: W0 (outcome-free) - how often A1's
   choice differs from A0 (historical pools with the caveat; F2 descriptive).  Realized comparison only as a POST-2026 registration with a power wall first.

## HISTORICAL CAUSAL-BOUNDARY AUDIT - CLOSED - Oct 3 2026 (order_keys.py, purity2.py; proj/order_keys_report.txt, purity2_report.txt)
O0 representation order: keys behind every order-dependent step are unique - p.load 55,692 rows / played 40,741 on (gsis, season, week): 0 repeats;
   team_game 3,744 on (season, week, team): 0; rt.X 25,177: 0; rt.DT 2,304: 0.  Scorers draw u in issued (pickled) order (code read).  Within the audited
   frozen paths, facts-row order cannot create an alternative result through duplicate-key ambiguity or positional draw reassignment (cross-environment
   unstable-sort tie order not covered).  O1-O3 have no live branch - not run.
P1-P3 non-anticipation (purity.py's grid, 2019/2021/2024 x weeks 4/9/15; retarget.py's own source on full vs cutoff-truncated worlds, cutoff outcomes
   blanked): J (slot, role, exp, rk; DST exp), Y (12 NEED inputs), DST (26 season-to-date inputs) -> 0 differing cells at every cutoff.  With purity.py
   (P features, A states) every frozen producer's inputs are non-anticipation-checked.

## SELECTOR LADDER W0 - REGISTRATION - Oct 3 2026 (before code; nothing seen)
QUESTION: does J's DEPENDENCE change the lineup a tail objective would choose?  (A p90 reranker moves lineups even with independent players - variance
   alone - so A1 vs A0 is not the dependence question.)
FRAMES: H = 2019-21 weeks 4-16 (pool = priced p.load rows + TG.dst_salary; participants-only, recorded; P / A / J in-sample per H0 - no outcomes used);
   F2 = issued 2026 w4 (descriptive).
CANDIDATES: pair-blind ban-one tree, depth 2, from best9(exp) (jexpose W0).
SELECTORS: A0 = L0;  A1-J = argmax p90 under Gaussian J;  A1-ind = argmax p90 with independent draws;  A1-J' = A1-J with an independent seed.
   s.py's Monte Carlo recipe (pred + J margin quantile; play draw from p_play), keyed streams, 20,000 draws; a selector leaves L0 only if its p90 beats
   L0's by > 2 batch-means s.e. (20 batches).
PRIMARY: per slate, d_dep = [A1-J != A1-ind], d_noise = [A1-J != A1-J']; exact binomial on slates where exactly one is 1: DEPENDENCE MATTERS iff
   d_dep-only slates exceed d_noise-only slates at p < .05 (one-sided).  Else CLOSED: the tail objective's choice does not depend on J's dependence.
DESCRIPTIVE: P(A1-J != A0), players changed, p90 gain, exp given up, target-pair exposure of A1-J; F2 reported alone.
NEXT only if PRIMARY passes: A2 (margin-preserved corner-corrected J) vs A1-J on the same candidates.

## SELECTOR LADDER W0 - AMENDED REGISTRATION - Oct 3 2026 (supersedes SELECTORS / PRIMARY of "SELECTOR LADDER W0 - REGISTRATION"; no code yet, nothing seen)
SCORES: per slate one keyed Gaussian-J matrix (players x 20,000; s.py recipe incl. the play draw).  A1-ind = the SAME per-player score vectors, each
   independently permuted across draws (identical marginals sample for sample; only cross-player alignment destroyed); A1-ind' = a second permutation;
   A1-J' = a fresh-seed J matrix.
LABEL: a selector's label = its p90 winner iff winner - runner-up > 2 batch-means s.e. of that difference (20 batches), else UNRESOLVED (L0 is a candidate,
   so this replaces the "beats L0" rule).  UNRESOLVED is a label like any other.
PRIMARY: d_dep = [label A1-J != label A1-ind];  d_noise = max([A1-J != A1-J'], [A1-ind != A1-ind']);  exact paired binomial (McNemar) on slates where
   exactly one is 1: DEPENDENCE MATTERS iff dep-only > noise-only at one-sided p < .05; else CLOSED.
REPORTED: per-season dep-only / noise-only (2019, 2020, 2021) - "fragile" if one season carries the pooled result (no second gate); discordance breakdown
   (both resolved and different / one resolved / both unresolved); descriptive A0 comparisons as registered; F2 alone.

## SELECTOR LADDER W0 - AMENDMENT 2 - Oct 3 2026 (before code; nothing seen) - single source, exact estimand, power; F2 removed
W-1 SINGLE SOURCE: historical slates are built by the FROZEN s.run itself: s.py reaches pandas only as module-level pd and reads its pool once
   (line 25, DK_{season}_w{week}.csv); a proxy pd serves that one read with a DK-format frame from the slate's priced p.load rows (Position, Salary,
   TeamAbbrev, Name, ID) + TG.dst_salary rows (Position DST, Name = team), every other call passed to pandas.  names.FIX is a no-op on 2019-21 codes
   (keys OAK / SD / LA / STL; data uses LV / LAC / LAR); P names non-null.  Per-slate join rate printed (min, median); a slate where s.run cannot form
   9 is skipped and counted.  No re-implemented formula.
W0a ESTIMAND: independence = the whole copula removed, every player / DST score vector kept exactly; check sort(Y_J) == sort(Y_ind) for every vector,
   failures printed - any failure stops the run.
PW0 POWER (computed before the primary is read, from noise outcomes only): n = slates; nu = mean single-pair noise rate ([J != J'], [I != I']);
   simulate the registered McNemar rule with d_noise ~ Bernoulli(observed max-noise rate) and d_dep ~ Bernoulli(nu + delta (1 - nu)), slates independent,
   10,000 replications, delta in {0, .05, .10, .20, .30, .50}.  MATERIALITY delta = .20 (fixed here).
READING: primary p < .05 -> DEPENDENCE MATTERS;  else CLOSED ABOVE delta = .20 iff PW0 power at .20 >= .80;  else INCONCLUSIVE.
F2 (issued 2026 w4) is removed from W0 - no 2026 object enters it.

## SELECTOR LADDER W0 - OUTCOME - Oct 3 2026 (selw0.py; proj/selw0_rows.csv, selw0_report.txt) - INCONCLUSIVE (registered reading)
W-1: 39 / 39 historical slates (2019-21 w4-16) built by the frozen s.run via the price-file adapter, 0 skipped; join rate 94.0-100% (median 97.7%).
W0a: 0 marginal-sample failures (permutation twins exact).
PW0: n 39, single-pair noise 12.8%, max-noise 20.5% -> power delta .05 .01, .10 .04, .20 .19, .30 .46, .50 .93.
PRIMARY: d_dep 5/39, d_noise 8/39; dep-only 2 vs noise-only 5; one-sided exact p .94 (2019 0/2, 2020 1/1, 2021 1/2) -> not significant; power(.20) .19
   < .80 -> INCONCLUSIVE.  Not rescued.
BENEATH IT (descriptive): A1-J resolved on 3 / 39 slates; all 5 J-vs-I discordances are resolved-vs-UNRESOLVED (0 both-resolved-and-different) ->
   near-optimal exp candidates are mostly indistinguishable on p90 at 20,000 draws; there is rarely a winner for dependence to change.  On the 3
   resolved slates A1-J differs from A0, holds a target pair (3 / 3), p90 gain median 1.88, exp given up median 0.11, 3 players changed - n = 3, no reading.
NEXT (only as a new registration, not a rerun of W0): W0-R resolution - the winner-vs-runner-up p90 gap in DK points across slates and the draws needed
   to resolve it; if the gaps are fractions of a point, reranking inside the exp neighbourhood is operationally immaterial whatever J does.

## A TRANSITION WALL (AT) - REGISTRATION - Oct 3 2026 (before code; nothing seen; diagnostic - A stays frozen in L v2)
QUESTION: in the LIVE-LIKE candidate universe (not the outcome-selected priced rows A was fit on), in which transition states is A's p_play wrong, by
   how much in probability and in DK points, and how variable is the error?
ROWS: proj/avail_rows.csv.gz (candidates Y would price, incl. absent; weeks 4-16; tests 2020-25).  PRIMARY 2023-25 (outside A's fit seasons and the
   priced domain); 2020-21 reported (A's fit seasons - in-sample-adjacent).  played = 1 - absent.
A p_play: frozen proj/a_cells.json via A's own path per (season, week): p.frame (the week's candidate gsis + teams) -> p.role_states -> a.categories ->
   a.predict (s.run lines 41-44).
STATES (fixed): gap {0, 1, 2+} x rs {1 low, 2 mid, 3 high} (avail.py definitions) = 9 cells; per-position view descriptive.
PER CELL: n, observed play rate, mean p_play, dp = observed - predicted, binomial s.e. sqrt(sum p(1-p)) / n; impact = dp x mean dk_ws (season-to-date DK
   mean of earlier played games); deviation = p10 / p50 / p90 of per-row (played - p_play) x dk_ws.
GATE: cell fails iff |dp| > 2 s.e.; family fail rate vs the 95th of 200 outcome sets simulated from p_play on the same rows (H4's construction).
PW-A: the gate's power on these rows with true absence scaled by k in {1.25, 1.5, 2} within each cell (200 sets each).
READING: noise-like on 2023-25 -> the availability lever is closed in the live-like universe;  STRUCTURAL -> lever map (flagged cells, dp, DK impact,
   deviation) recorded as POST-2026 candidates.  Nothing in A / S changes during L v2.

## A TRANSITION WALL (AT) - OUTCOME - Oct 3 2026 (at_wall.py; proj/at_rows.csv.gz, at_report.txt) - STRUCTURAL in the live-like universe
Candidate universe (avail_rows, incl. absent; 26,003 rows, 2020-25), A's frozen p_play by A's own path (0 rows without A).
PRIMARY 2023-25 (15,536 rows): p_play 97.4% vs played 83.7%; 9 / 9 cells fail vs null 95th 11.1% -> STRUCTURAL.  PW-A x1.25 78%, x1.5 100%, x2 100%.
   gap 0 / low 84.5% vs 94.5%, mid 93.0% vs 99.6%, high 94.3% vs 100.0%;  gap 1: low 43.2% vs 91.7%, mid 39.3% vs 99.1%, high 38.6% vs 99.9%;
   gap 2+: low 29.5% vs 90.9%, mid 40.9% vs 98.6%, high 38.8% vs 99.5%.  Impact (dp x dk_ws): gap 1 high -7.52, gap 2+ high -7.59, gap 1 mid -4.10,
   gap 2+ mid -3.40, gap 0 high -0.79 DK per row; deviation gap 1 high p10/p50/p90 -16.71 / -8.36 / +0.02.  Position after absence: QB -67% / -74%,
   WR -53% / -57%, TE -54% / -56%, RB -47% / -57% (gap 1 / 2+).
2020-21 (A's fit seasons): same pattern (p_play 97.2% vs played 80.6%, 9 / 9) -> a DOMAIN defect, not drift.
MECHANISM (read, not tested): A was fit on outcome-selected priced rows (HISTORICAL PRICED ROWS, line 372), where "out last game" almost always meant
   "played"; in the candidate universe it does not.  "A predicts participation well overall" held on priced rows only.
OPERATIONAL: s.run selects on exp = pred x p_play -> real-role players returning from absence enter the live slate with exp overstated by about half
   their projection; the frozen selector is drawn toward them.  Nothing changes in L v2.
FORECAST, recorded before any 2026 scoring: H4 (A p_play on the live DK pool) is expected to fail, chiefly in players who missed the previous team-game.
NOT A FUTURE WALL (owner, Oct 3 2026): the candidate-universe availability model is built and validated NOW on 2019-25 history (pbp filtered to
   games before the week where absence information is needed).  Only deployment into the frozen live s.run is tied to the L v2 freeze - the owner's decision.

## A TRANSITION WALL - STEP 3 OUTCOME - Oct 3 2026 (at_q.py, at_t.py; proj/at_q_report.txt, at_t_report.txt)
Step 2: no existing model passes the AT gate on 2023-25 - A 9/9, 1 - q_B 9/9, 1 - q_M 66.7% vs 22.2% (q_M log loss .3348, but too optimistic at gap 1).
Step 3 (walk-forward, partial pooling M = 10): T1 gap x role G1 33.3% vs 11.1%, G2 44.0% vs 12.0%; T2 (+ position) G1 33.3% vs 22.2%, G2 20.0% vs 12.0%
   -> FAIL as registered.  The 3 failing G1 cells are exactly the gap-0 cells (T1 under by 1.0-2.2 points at n 3,800-5,200); every gap >= 1 cell is inside
   its interval (frozen A missed them by ~60 points).
LEVER (all candidate rows 2020-25, played, 95% team-season bootstrap): gap 0 high 93.8% [93.0, 94.5], mid 92.0% [91.4, 92.7], low 83.4% [82.2, 84.4];
   gap 1 high 40.8% [35.2, 46.5], mid 39.7% [35.5, 44.1], low 41.9% [38.6, 44.9]; gap 2+ high 38.2% [32.5, 44.1], mid 38.2% [32.5, 44.9], low 30.5% [27.6, 33.4].
RESIDUAL = ERA LEVEL at gap 0: played 2020 88.4%, 2021 86.9%, 2023 90.4%, 2024 90.0%, 2025 90.0%; gap 1 / 2+ stable.  Consistent with 2020-21-specific
   absences (not shown).  ~0.15-0.3 DK per gap-0 player.  Not validatable on history (no 2022 in the candidate universe; 2024-25 rates already seen) ->
   any era handling is judged prospectively only.
REGISTERED NEXT (before code) - CONDITIONAL TAIL BY TRANSITION (review direction: P(boom) = P(plays) x P(boom | plays), within tier):
   rows: ystick history rows with full-precision result (Y = given he plays), RB / WR / TE, joined to at_rows' gap state (gap 0 / 1 / 2+) by
   (gsis, season, week); tier = Y's own center tier within position-week.
   Q1 calibration: Y's frozen gate (decile MAD vs flat 95th, fail rate vs 200 simulated calibrated sets) on the grid position x gap state x tier
      (n >= 60) - does Y stay calibrated for players returning from absence?
   Q2 tilt (descriptive with intervals): boom (result >= .9) and bust (< .1) rates by position x tier x gap state, team-season bootstrap; plus the
      unconditional view P(plays) x P(boom | plays) from the T1 lever table.
   READING: Q1 noise-like -> Y already prices the transition given he plays, and the lever is P(plays) alone;  Q1 STRUCTURAL -> the transition also
      tilts the conditional tail (Y's gap) - recorded with Q2's direction and size.  Y unchanged in L v2.

## 2026 ADDENDUM 3 - H7 T1 AVAILABILITY CHALLENGER - Oct 3 2026 (owner decision (a): L v2 frozen; A incumbent, T1 challenger; registered before week 5)
PRODUCER: T1 cells = pooled played rate by gap {0, 1, 2+} x role state {low, mid, high}; partial pooling M = 10 (parent role state, then overall); fit ONCE on
   all candidate-universe rows 2020-25 (proj/at_rows.csv.gz) -> proj/t1_cells.json, hash witnessed before the first issue.
LIVE INPUTS (week N, earlier played games only; avail.py / score_t definitions): gap = team-games missed since the last played game on the same team;
   role state from snap_ws (< .35 low, < .70 mid, else high).  DOMAIN: issued DK slate skill rows that are candidates with 3+ earlier played games (or WR
   with 1-2); others no H7 value (counted).
ISSUE: weeks 5-16, before each week's first kickoff -> proj/issued_t1_2026_wN.csv (read-only, SHA-256 printed).
OUTCOME: played = a played row in p.load that week (no row = 0), as H4.
JUDGE: H4's construction (|played - mean p| > 2 binomial s.e., n >= 60, vs the 95th of 200 sets simulated from p) on TWO grids: H4's (position / salary
   band / week block) and AT's (gap x role state).  PASS iff noise-like on both.  FINAL only when weeks 5-16 are all scored, else INTERIM.
HEAD-TO-HEAD (descriptive): rows priced by both A and T1 - log loss paired by week.  Nothing in L v2 changes either way.

## 2026 H7 WITNESSES - Oct 3 2026
h7.py validate: V1 T1 walk-forward via at_t's own at_pool, 20,764 rows, max |diff| 1.11e-16 -> PASS;  V2 live-input path vs at_rows (2024-25), 10,363 rows,
   gap + role state match 100.00% -> PASS.
T1 cells (all candidate rows 2020-25, n 26,003): gap 0 high 93.7% / mid 92.0% / low 83.3%; gap 1 high 42.4% / mid 40.8% / low 42.2%; gap 2+ high 39.9% /
   mid 39.4% / low 31.0%.
SHA-256: proj/t1_cells.json cbee6702d3a3c96eab7c8dda0c110b2afba0872058c081986414f4edac0261b1;  h7.py 2f308c515d9ff4444bdd61ade36c795783b47e8b30c88c4feb353fda98bce27b;
   proj/register_2026_addendum3.json 516b3d24020a257d828d45e12876ba4311c30321bc8c09ce9fc65260bbb23c06.

## CONDITIONAL TAIL BY TRANSITION - OUTCOME - Oct 3 2026 (ctail.py, ctail_attr.py; proj/ctail_report.txt, ctail_attr_report.txt)
Q1 family (position x gap x tier, n >= 60): 5 / 20 cells fail = 25.0% vs null 95th 15.0% -> family STRUCTURAL.
ATTRIBUTION (reading of Q1, not a new test): all 5 failures at gap 0 - RB below / bottom / elite / middle and TE below; gap 1 0/3, gap 2+ 0/2 ->
   transition-specific conditional tail NOT ESTABLISHED.  The registered reading "STRUCTURAL -> transition tilts the tail" was too broad (family failure
   does not name the lever) - corrected here.  Availability's validated lever is P(plays) (T1).
Q2 (descriptive): RB gap 1 boom | plays 17.6% [12.6, 23.9] vs gap 0 9.6% (unconditional 41.9% x 17.6% = 7.3% vs 8.4%); its one gateable cell (bottom, n 84)
   passes.  WR / TE gap >= 1 intervals contain 10%.
OBSERVATION: Y RB at gap 0 miscalibrated in 4 / 5 tiers (2020-25, position x tier) - a different grid and span from SC's frozen 2024-25 verdict (4/39);
   H1 judges SC prospectively; recorded, nothing changes.

## SSOT INVENTORY - Oct 3 2026 (ssot_check.py, clip_recompute.py; proj/ssot_report.txt, clip_recompute_report.txt)
Canonical sources (owning frozen / registered producers): decile MAD, flat 95th, randomized PIT -> ystick.py (mad, noise95, pit_of); binomial subgroup gate ->
   score_s.py (ss_fail); log loss -> a.py (ll); CRPS -> adjudicate.py (crps_mix).  Copies compared from source (no module run) on a fixed battery.
RESULT (70 scripts): IDENTICAL 40 (incl. the NOISE-parameterized noise95 copies at their declared default 200, and register.py rg_mad / rg_n95);
   DIFFERENT 4 - at_t.at_fail (a distinct gate: cells of one column) and the 1e-4-clip log losses aaudit.aa_ll / avail.av_ll / classe.ce_ll;
   NOT COMPARABLE 9 - distinct gates / signatures (aa_fails, av_fails, ce_fails, aq_fail, at_wall.at_fail, g2_bfail, shorthist.fails, sd_fail) and a name
   collision (lens.ll).
CLIP IMPACT (stored predictions, no refit): band rows (min(p, 1-p) < 1e-4) A p_play 3,286 / 9,469, 1 - q_M 74 / 26,003, 1 - q_B 0.  A audit log loss A .0825 ->
   .0826 vs q_M .1919 (A lower under both); R1 SHARP dev +0.0799 +- .0044 (3/3), 2024-25 +0.0828 +- .0029 (2/2) -> passes under both.  No recorded decision
   changes.  Class E (ce_ll, q_M vs q_R) unchecked - q_R predictions not on screen; low risk.
POLICY: frozen / witnessed files keep their copies until the cycle ends (their hashes stand); new and non-frozen code executes the canonical source
   (as h7.py does); duplicates retire after the cycle; a guard rule against new copies follows a read of guard.py.

## RB GAP-0 ANCHOR - STEP 1 - Oct 3 2026 (rb_anchor.py; proj/rb_anchor_report.txt) - reading of the located Y miss
Per season (decile MAD vs flat 95th): 2020 FAIL .0113/.0109, 2021 ok, 2023 FAIL .0114/.0110, 2024 ok, 2025 FAIL .0120/.0109 (3 / 5; ~.001 if each were an
   independent 5% false fail).  2024-25 pooled FAIL .0087/.0076; 2020-21 + 2023 pooled ok .0063/.0065 -> not early-era; inside SC's frozen window on a
   different grid (position x tier).
Per tier: bottom FAIL .0224/.0119 (d1-d5 .105-.126, d6-d8 .056-.077, d9 .126 - misplaced mass, not a tilt); middle FAIL (d1 light, bust 6.5%); below FAIL
   (high-heavy); elite FAIL (flat-ish); good ok.  Directions differ by tier -> not one uniform shift.
NEXT (smaller wall first): RB near-zero component by tier - observed P(DK <= 1 | plays) vs Y's mean near_zero_p on Y's own history frame - before any
   carry-share / target-share lever axis.  Y unchanged in L v2.

## REGISTRATION CHAIN - register.py WITNESS - Oct 3 2026
register.py (wrote proj/register_2026.json, witness 9e16b3f0...) SHA-256 c75464a067d7514be60ea9f529bbd83ca630c3427dc11ee28e4961a1db92b068 - recorded so the SSOT law protects it (never edited).

## SSOT INVENTORY - CLOSURE (2026-10-03)
Step 3 (ssot_fix.py apply): every copy / variant of a canonical function in a non-recorded file was replaced by "from canon import <key> as <name>";
each converted file compiled.  Apply output: aaudit (1), adjudicate (3), at_q (1), at_t (1), avail (1), classe (1), floor_test (3), gatesim (2),
gatesim2 (2), mass_zero (1), regime_test (4), residual_s (4), shorthist (4), smooth_test (3), standard (2), synergy (1), zero_test (4);
protected (recorded): dstick.py, h7.py, register.py - their copies stay until the cycle ends.
Step 4 (guard.py check 11): a top-level def outside the canonical source that reproduces a canonical on canon.BAT (copy), or shares its stem and
arity (variant), fails the guard unless the file's SHA is on record.
ssot_check.py single-sourced on canon (extract / BAT / out / canonical functions / violations); its own extractor and battery deleted.
CLIP: aaudit, avail, classe used a 1e-4 log-loss clip and now use a.py ll (1e-6).  clip_recompute.py: A AUDIT and R1 SHARP unchanged.
classe.py's recorded verdict was NOT recomputed by clip_recompute.py - open work-order line.
Instrument state at closure (ssot_check.py, verbatim):
   DOOR: 20 files read through canon: aaudit.py [ll as aa_ll];  adjudicate.py [noise95, mad, pit_of];  at_q.py [ll as aq_ll];  at_t.py [ll as at_ll];  avail.py [ll as av_ll];  classe.py [ll as ce_ll];  floor_test.py [noise95, mad, pit_of];  gatesim.py [mad as gs_mad, noise95 as gs_n95];  gatesim2.py [mad as g2_mad, noise95 as g2_n95];  guard.py [import canon];  mass_zero.py [pit_of];  regime_test.py [noise95, mad, pit_of, ll];  residual_s.py [noise95, mad, pit_of, crps_mix];  shorthist.py [pit_of, crps_mix, mad, noise95];  smooth_test.py [noise95, mad, pit_of];  ssot_check.py [import canon];  ssot_fix.py [import canon];  standard.py [noise95, mad];  synergy.py [ll];  zero_test.py [noise95, mad, pit_of, ll]
   REMAINING: 5 violations, 0 in non-recorded files: dstick.py:ds_mad->mad (copy, recorded), dstick.py:ds_n95->noise95 (copy, recorded), h7.py:h7_fail->ss_fail (copy, recorded), register.py:rg_mad->mad (copy, recorded), register.py:rg_n95->noise95 (copy, recorded)
SHA-256 at closure (canonical sources adjudicate.py / score_s.py witnessed here; canon / guard / ssot tools):
   62cf3a2d8c5f58b120853b7a0c849f6166b88f4ca24b1594adf3c72a536ebba3  canon.py
   65901c9d7ca4cca1c43062fe3dca6348a73b576774f788a88d82c4069702881f  guard.py
   57db99601c93dc02fe8e0adddbf9650499bcd0dbb258a1a907321363c7678b13  ssot_check.py
   0771b9ddc7aa90c94ae0b284c3ad2d4f2760aa852efbef5dee676176f1348ae4  ssot_fix.py
   57bdc9257a6f98afad0715c9a157b0c726fedd6b575b23fd40954d7fd1d392b1  adjudicate.py
   e95b449806d205c7f309e44a04089feafcb6d62a084ada41ea32be462dd3c3aa  score_s.py

## SSOT RESIDUE CLEANUP (2026-10-03)
ssot_residue.py (consumer-scoped, fixed point) deleted the module-level names the SSOT conversion left unread and no consumer reaches: the deleted
copies' caches (_noise, _n95, _nz), the NOISE argv knob, DEV_BEFORE, and the then-unread sys import; split 'from canon import' lines merged into one.
NOISE: floor_test / regime_test / smooth_test / zero_test read the noise-draw count from argv (default 200) into their own noise95; since the conversion
canon.noise95 (ystick's, equal to the copies at 200) governs and the knob was dead - a recorded run that passed an argv value other than 200 is not
reproducible through canon.  adjudicate.py: see the amendment below.  adjudicate.py line 94 fifth_samples (nested, unread) not deleted - work order.
ssot_residue.py helper renamed outside -> rs_reached (guard: duplicate definition with p.py).   Apply output (verbatim):
   adjudicate.py    PROTECTED (SHA on record) - not edited
   floor_test.py    deleted ['NOISE', '_noise', 'sys']  canon lines 3->1
   gatesim.py       deleted ['_n95']  canon lines 2->1
   gatesim2.py      deleted ['_n95']  canon lines 2->1
   regime_test.py   deleted ['NOISE', '_noise', 'sys']  canon lines 4->1
   residual_s.py    deleted ['_noise']  canon lines 4->1
   shorthist.py     deleted ['_nz']  canon lines 4->1
   smooth_test.py   deleted ['NOISE', '_noise', 'sys']  canon lines 3->1
   standard.py      deleted ['_noise']  canon lines 2->1
   zero_test.py     deleted ['NOISE', '_noise', 'sys']  canon lines 4->1

## SSOT CLOSURE AMENDMENT - adjudicate.py RE-WITNESS (2026-10-03)
User decision (b).  ssot_residue.py --rewitness verified adjudicate.py's SHA was on record ONLY in the SSOT INVENTORY - CLOSURE snapshot (no proj/*.json,
no issued pickle).  Its residue (DEV_BEFORE, _noise) deleted and its canon lines merged; canon.crps_mix (owned by adjudicate.py) verified unchanged on
canon.BAT before vs after.  The closure line "57bdc9257a6f...  adjudicate.py" is SUPERSEDED by the SHA below.   Apply output (verbatim):
   adjudicate.py    SHA 57bdc925 on record at: ['CHARTER [SSOT INVENTORY - CLOSURE (2026-10-03)]'] -> re-witness allowed (closure snapshot only)
   adjudicate.py    deleted ['DEV_BEFORE', '_noise']  canon lines 3->1
   RESIDUE names total 0;  files with canon import lines > 1: []
   crps_mix unchanged on canon.BAT
   53ed3499a4689b813202b1d580a85cc956b63e2196ddd5ef19ca5563a97b1c56  adjudicate.py
   207ceaea9bd0780387a8b6a7a97558c6b60b108ccdb6c621419f6e28cc9c417f  ssot_residue.py

## CLASS E (b) - CLIP RECOMPUTE (2026-10-03)
classe.py rerun with canon.ll (1e-6 clip) against its recorded proj/study_classe.txt (1e-4 clip): exactly one line differs - q_R log-loss 0.2925 -> 0.2926;
every other line identical (sections 1-5, calibration verdicts, teammate cells).  Gates: R over q_M gain +0.0733 +- 0.0036 (2/2) and +0.0893 +- 0.0029 (2/2)
-> passes, as recorded (+0.073 / +0.089).  VERDICT teammates unchanged.  No Class E decision is clip-dependent; the SSOT clip line is closed.

## SSOT CLOSURE AMENDMENT 2 - adjudicate.py FOSSILS (2026-10-03)
Owner: "theres no reason to keep the fossil".  Deleted the dead locals of the binned ordinary distribution adjudicate.py no longer scores:
fifth_samples (built, never read here; residual_s.py keeps its own) and f_bin (np.full + per-fifth pit_of fill loop, never read; ssot_residue.py
counted its subscript store as a read - instrument defect on the work order).  Gate: SHA was 53ed3499; consumers canon / pgate_audit / ystick name
neither; adjudicate.py run before vs after the edit: proj/adjudicate_report.txt IDENTICAL.  SHA 53ed3499... (AMENDMENT 1) is SUPERSEDED by:
   fc6c8877d22c49f063f67f24f1ae48ad0554dc67ae915fa562ec929839e9edc8  adjudicate.py

## LEVER ATLAS + SUPERSESSION INDEX (2026-10-03)
Owner: collapse each discovery class to its superseding record; the process stays out.  atlas.py holds one row per class (type, status, and
conclusion / magnitude / limitation / next state as CHARTER line + exact excerpt, lines superseded, producers); every excerpt verified; proj/atlas.txt
is its print.  Rows 26 (anti-pattern 4, boundary 2, implementation 2, neutral 6, positive 9, problem 1, resolution 2); open 6.
SUPERSESSION INDEX - stale line -> superseding line [note]; earlier lines stand as history and are read through this index:
   L18 -> L99  [salaries are 2019-21]
   L27 -> L141  [anchors narrowed by the information set]
   L37 -> L144  [M producer deleted]
   L38 -> L144  [R producer deleted]
   L40 -> L94  [L v2 judges against the price-alone lineup]
   L56 -> L628  [A's domain defect; T1 lever (L643)]
   L68 -> L317  [answered by Class E]
   L69 -> L533  [answered by the J tail branch]
   L70 -> L142  [lines are outside the information set]
   L76 -> L142  [props are outside the information set]
   L101 -> L105  [superseded]
   L107 -> L141  [A's week-N status input deleted (L144)]
   L111 -> L144  [lens input deleted]
   L138 -> L142  [now outside the information set]
   L192 -> L400  [price-file trigger registered prospectively (H6); history untested]
   L203 -> L350  [closed]
   L318 -> L400  [NARROWED, not reversed: the DK price file carries a partial pregame trigger for a new absence (backup price +153, L454), registered as H6 (score_s judge_6)]
   L336 -> L345  [done]
   L369 -> L371  [read]
   L421 -> L428  [H4 + H6 = score_s.py (judge_6, code read); H5 = score_t.py]
   L471 -> NONE  [DANGLING: no section of that name exists in CHARTER]
   L698 -> L717  [done]
   L721 -> L765  [closed]
   L738 -> L768  [closed]
atlas.py SHA-256 70e74c13d0570ad28259d6db436a77771fa4c128c1cb5ccc8a9ef6304ce30827

## CLEANUP - CLOSED PROCESS DELETED (2026-10-03)
Owner: delete what the ledger already covers; no archive.  Rule (atlas.py PLAN): every atlas row naming the file is CLOSED with conclusion / magnitude /
limitation / next state verified in CHARTER, the file is not RECORDED, and no kept file names it; pre-check: no remaining script imports or names a deleted file.
Deleted root (24): at_q, ceiling, classb, classc, classe_bal, clip_recompute, ctail_attr, discover, field_check, floor_test, grid, jdisp, jtail_power,
jtails, jtails2, lens, mass_zero, order_keys, purity2, residual_s, smooth_test, standard, stress, synergy (.py).  proj (27): their reports, rows and cell dumps.
Folders: archive (backups of retired code), studies (compiled files only), __pycache__, research/__pycache__.  kit_inventory.py deleted earlier (spent).
Held: research/ (named by facts.py / adjudicate.py - read first; holds a link into data/), README.md, README.txt, WEEKLY.txt, compose.py, contexts.py (unmapped).
The findings live in atlas rows R01-R26 and the CHARTER lines they cite.

## GAP-0 NEAR-ZERO SPLIT - RB STEP 2 + WR / TE CONTRAST - Oct 3 2026 (nz_split.py; proj/nz_split_RB.txt, nz_split_WR.txt, nz_split_TE.txt)
Rows gap 0, model SC: RB 4,677 (near-zero 20.4%), WR 8,210 (26.9%), TE 5,033 (37.5%).  RB CHECK reproduces step 1 (bottom .0224/.0119).
(1) pi* calibration noise-like at all three (canon.ss_fail tier + season: 2/10 = 20.0% vs null 95th 20.0% each - at the boundary).  Descriptive, not gated:
   the bottom tier is under-predicted at every position (observed - mean pi*: RB +2.74%, WR +4.01%, TE +3.29%).
(2) F0 shape: RB STRUCTURAL 4/8 vs 25.0% (by tier: below / bottom / middle); WR 0/9 vs 22.2%; TE 1/9 vs 22.2% -> the near-zero shape defect is RB-specific.
   Materiality bound: F0's support is DK <= 1 (L238) - gate-visible, value-immaterial.
(3) Ford shape: RB STRUCTURAL 4/10 vs 20.0%; TE STRUCTURAL 5/10 vs 20.0%; WR noise-like 2/10 vs 20.0% (boundary).  The bottom tier is humped at every
   position (d4-d7: RB .563, WR .576, TE .591 vs .40) -> Ford too WIDE at low centers, a cross-position form (WR crosses the cell gate, not the family).
READING (registered): RB F0 + Ford; TE Ford; WR none; pi* nowhere.  Positive anchors RB / TE, neutral control WR.  Y unchanged in L v2 (frozen).
NEXT (registered before code; nothing seen) - FORD WIDTH IN DK (materiality only, no fitting):
   rows: gap-0 SC ordinary games (Y's Z = 0), RB / WR / TE x tier, Y's in-memory history; Ford exactly as ystick builds it, unchanged.
   PRIMARY: dW = W_Ford - W_obs in DK; W_obs = the cell's mean |DK - center|; W_Ford = the cell mean of each row's Ford expectation E|X - center|;
      95% team-season bootstrap (500).  SECONDARY (description): p10-p90 width, observed vs Ford.
   READING: MATERIAL iff a low tier (bottom or below) of RB or TE has its dW interval above +1 DK; IMMATERIAL iff every RB / TE low-tier interval lies
      below +1 DK; else UNRESOLVED.  WR = control, same computation, not gated.  1 DK = the bound used for F0.  Y unchanged in L v2.
   rb_anchor.py / rb_nearzero.py and their reports deleted after this record, the atlas and guard passed (superseded by nz_split.py).

## FORD WIDTH MATERIALITY - CLOSED - Oct 3 2026 (ford_width.py; proj/ford_width.txt) - registered reading IMMATERIAL
ystick executed from source with three read-only taps (row Ford E|X - c|, Ford p10 / p90); CHECK reproduces nz_split RB per tier exactly (bottom .0224/.0119).
Gap-0 SC ordinary games: RB 3,723, WR 6,005, TE 3,147 (160 team-seasons each).  PRIMARY dW = W_Ford - W_obs (mean |DK - center|), 95% team-season bootstrap:
   RB bottom +0.22 [-0.34, +0.69], below -0.06 [-0.37, +0.24];  TE bottom -0.00 [-0.39, +0.34], below +0.21 [-0.08, +0.47] -> every RB / TE low-tier
   interval below +1 DK -> IMMATERIAL.  Control WR bottom +0.19 [-0.24, +0.55], below +0.16 [-0.08, +0.38].
   Intervals excluding 0, all < +1 DK: RB elite +0.34 [+0.03, +0.64], WR elite +0.25 [+0.02, +0.48], TE middle +0.35 [+0.14, +0.56] - small-effect anchors, not walls.
SECONDARY (description, not gated): Ford p10-p90 wider than observed at the bottom tier (RB 9.19 vs 8.20, WR 9.51 vs 7.80, TE 7.26 vs 6.16) and TE middle (10.08 vs 8.44).
READING: the low-center Ford hump is real in PIT geometry and a few tenths of a DK in mean absolute width - statistically visible, operationally immaterial.
   R14 closes: RB gap-0 miss -> not transition -> not pi* -> F0 (bounded <= 1 DK) + Ford shape -> Ford width < 1 DK.  No Y architecture change.
PROCEDURE (from this wall): a structural calibration failure earns architecture work only after its size is measured in the decision's units (DK points,
   probability points, lineup points) against a materiality bound fixed before the numbers.
   R14 process deleted after closure: ctail.py, ford_width.py, nz_split.py; proj/ctail_report.txt, ford_width.txt, nz_split_RB/WR/TE.txt (numbers above).

## AT END-TO-END - REGISTRATION - Oct 3 2026 (before code; nothing seen; work order 8) - outcome-free materiality of A's availability defect
QUESTION: on the FROZEN selector, how many expected DK does A's p_play give up if T1's P(plays) is right?  Diagnostic only - A stays in L v2; deploying T1 is
   the owner's decision.
FRAMES: H = the historical slates selw0 builds (2019-21 weeks 4-16; frozen s.run through the price-file adapter; priced pools outcome-selected, P / A
   in-sample - recorded; priced pools rarely hold a returner, so H likely understates the live exposure).  2019 lies outside T1's fit seasons (2020-25).
   F2 = the issued 2026 w4 slate, descriptive only.  No outcome is read.
POOL: rows with pred and (DST, or both A and T1 p_play) - identical in both worlds; no fill.  exp_A = pred x p_A, exp_T = pred x p_T1; DST = pred.
PRIMARY: regret = exp_T(best9(exp_T)) - exp_T(best9(exp_A)) per slate (DK, >= 0); mean over H slates, 95% slate bootstrap (2000).
READING: MATERIAL iff the lower bound > 1 DK; IMMATERIAL iff the upper bound < 1 DK; else UNRESOLVED.  1 DK = the kit's materiality unit (PROCEDURE above).
DESCRIPTIVE: share of slates where the lineups differ, players changed, A's view exp_A(L_A) - exp_A(L_T), per season, rows dropped for a missing T1 value,
   L_A = s.run's lineup check; F2 alone.

## AT END-TO-END - OUTCOME - Oct 3 2026 (at_e2e.py; proj/at_e2e.txt) - registered reading UNRESOLVED; frozen-selector pool not instantiated
H 39 slates (0 skipped).  PRIMARY (registered common pool): mean regret 2.10 DK [0.97, 3.28] -> UNRESOLVED (straddles 1 DK); median 0.13, max 12.74.
   2019 (outside T1 fit) 1.08, 2020 2.50, 2021 2.73.  Lineups differ 25/39 (players changed median 3).  A's own view of the switch: mean 0.34 DK.
WITNESS: the common pool drops rows without a T1 value (mean 25.4 per H slate; 89 on F2); best9(exp_A) on it equals frozen s.run's lineup on 30/39 H slates
   and not on F2 - the registered pool is not the frozen selector's pool.  The interval describes the common pool only.  Not rescued, not re-read.
DESCRIPTIVE: the 10 slates with regret > 4 DK (4.66-12.74) are exactly those whose L_A holds a returner (gap >= 1); every other slate <= 0.33 DK -> sparse,
   event-driven: large only when a returner sits near the optimum.  F2: regret 0.27, no returner in L_A.
NEXT: T1 COVERAGE on the frozen pool - S-selectable non-DST rows without a T1 value, by reason (not in T1's input frame / gap / role / cell), position,
   earlier played games, team change, and how many enter s.run's lineup; no fallback, no refit.  Inside T1's frozen rule -> mechanical restore and the same
   registered wall rerun;  outside it -> BLOCKED BY DOMAIN (a separate domain-extension wall).

## T1 COVERAGE ON THE FROZEN POOL - Oct 3 2026 (at_cover.py; proj/at_cover.txt) - AT END-TO-END BLOCKED BY DOMAIN
S-selectable non-DST rows: H 13,640 on 39 slates - T1 defined 12,648 (92.7%), missing 992;  F2 415 - defined 326 (78.6%), missing 89.  Every missing row's
   reason is "not in T1 frame" (no gap / role / cell hole).  Missing by earlier played games: H 0: 20, 1: 362, 2: 440, 3+: 170 (team change 22);  F2 0: 4,
   1: 39, 2: 46, 3+: 0.  Missing rows in s.run's lineup: H 10 of 312 lineup skill slots - exactly the 9 slates where L_A != s.run;  F2 1 of 8 (a TE, 1 game).
RULE (code read): T1's frame = score_t.st_new_absences' candidate rows - p.candidates (a row in the team's previous team-game: priced, rostered, listed or
   recorded), n_prior >= 3 or WR with 1-2, AVF inputs present, gap defined on the same team - the live-input path H7 registered (L661: "others no H7 value
   (counted)").  Every hole is OUTSIDE T1's frozen rule; the split of the 3+ rows among no previous-game row / missing input / team change is not measured.
READING: no mechanical restore exists without changing T1's rule -> AT END-TO-END (frozen selector) is BLOCKED BY DOMAIN, not statistically unresolved.
   T1 is not a drop-in availability replacement for frozen S: it prices 92.7% of the selectable historical pool and 78.6% of the live w4 pool.
   H7 is unaffected (it judges T1 on its declared domain).  The descriptive returner pattern (AT END-TO-END - OUTCOME) stays descriptive.
NEXT (owner decision, not registered): a separate T1 domain-extension wall (short history, no previous-game row, team change), built and validated on
   history, then AT end-to-end rerun as registered;  or AT end-to-end stays blocked this cycle while H7 judges T1 on its declared domain.

## AT END-TO-END - OWNER DECISION (b) - Oct 3 2026 - BLOCKED BY DOMAIN for this cycle
Owner: leave AT end-to-end blocked; no T1 domain extension before the 2026 confirmation; H7 proceeds on its registered domain.  H7 answers "is T1 good where
   T1 is defined?"; R27 answered "can T1 replace A everywhere S needs availability?" structurally: no, not without extending the domain.
POST-CYCLE (not a wall now): domain map of the rows outside T1's frame - split of the 170 historical 3+-game rows (no previous-game row / missing input /
   team change) - then a domain-extension wall only after H7's prospective verdict.  AT end-to-end reruns from its registration above if that wall earns.
   R27 process deleted after the decision, atlas and guard: at_e2e.py, at_cover.py, proj/at_e2e.txt, proj/at_cover.txt (registrations and outcomes above).

## NULL-TRUTHINESS SCAN - Oct 3 2026 (code read; pandas 2.3.3 / numpy 1.26.4) - work order 9 closed
Environment is pandas 2.3.3, not 3 - the earlier "pandas-3" label was wrong; the hazard is Python's own: bool(NaN) is True and NaN.astype(str) is "nan".
P1 truthiness on a possibly-NaN value: one site left in the scanned patterns - jexpose.py:107 "if col and ..." -> "if isinstance(col, str) and ..." (as
   selw0).  On the recorded run col was a slot string or None (a NaN col would have raised KeyError at CI[col], not mis-slotted), so the edit is
   behavior-identical there and the recorded jexpose outcome stands; not rerun.  s.py:60-61 takes col from dict.get (None, never NaN) - safe; frozen.
P2 astype(str) on a possibly-null column: 28 sites read - guarded by fillna (classe, fetch), non-null by construction (team / season keys, j's slot rank,
   names from the price file and P with duplicate keys dropped), or pd.cut bands whose NaN input would print as a visible "nan" subgroup.  No silent merge
   key found; classification by code read, not measured row by row.

## WORK ORDER 10a / 10b - CLOSED - Oct 3 2026 (ledger citation; code read of l.py, guard.py, register.py, j.py, s.py)
10a MISSING 2022: by design - L98-99 (a season counts only if every raw kind exists; 2022 per-season raw files deleted), L108 (cannot be undone without
   refetching), L397 (deleted as dirty - not a lockbox), L646 (no 2022 in the candidate universe); the owner's no-new-fetch rule stands.  Not a gap to repair.
10b CONSUMERS OF proj/j_model.json: j.py writes it (games with season <= FROZEN_THRU); s.run reads it only after best9 (display Monte Carlo -> dist);
   l.py hashes it into the L v2 freeze and uses run()'s dist only as sim_mean in the reported, ungated "S calibration" row - L's two gates (P partial rho;
   lineup minus price-alone) never read J; guard checks its freshness (check 5), its training seasons <= FROZEN_THRU (check 8) and the L freeze hash
   (check 9); register.py witnesses its SHA; selw0 / jexpose read it as diagnostics.  -> J has no decision-bearing consumer in L v2 (a J-using selector is
   the POST-2026 wall at L535).
WEEKLY NOTE (code read, guard L54-59 / L84-87): after facts.py reruns on a new week, guard check 5 fails until the p.py / a.py / j.py outputs are rerun;
   j.py's fit filters seasons <= FROZEN_THRU, so j_model.json is expected byte-identical - guard check 9 (L freeze: j_model, p_coef, a_cells) is the witness;
   a mismatch makes L refuse, which is the intended stop.

## R10 CARRY BALANCE SHEET - CLOSED - Oct 3 2026 (owner decision (b); carries.py read) - descriptive accounting only
New real-role RB absence reallocates most vacated carries to other RBs (baseline RB 65.6% dev / 87.1% 2024-25 of V; new RB 9.3% / 10.2%; L352).  The
   dev / late difference in net vanished carries (29.3% +- 5.9 vs 0.7% +- 11.4; 31 late episodes) remains UNSETTLED: a recency-window baseline (the absent
   RB's last 1-3 games instead of his season mean) could diagnose it but cannot confirm it on seen 2020-25 data, and no legal pregame consumer exists (L355;
   a new week-N absence is outside the information set, L142 / L325) - PROCEDURE: no decision value this cycle.  No further work this cycle.
Kept anchor: new RB absence -> carries mainly to other RBs.  Unknown residue: how much team rushing volume contracts (episode team carries dev 24.8 vs
   control 26.7; 2024-25 27.1 vs 26.8).  FILTER for every further wall: can it change a legal pregame decision?  If not, close it before building it.
   R10 process deleted after the record, atlas and guard: carries.py, causal_a.py and their proj reports (numbers above and in L197 / L350-355).

## WORK ORDER 10d / 10e - CLOSED BEFORE BUILDING - Oct 3 2026 (decision-value filter, L912)
10d PERSISTENCE BEYOND ONE GAME BACK (L274, Class C): a finding would act through Y's center or P - both frozen for the cycle (registered producer hashes
   freeze ystick.py / dstick.py, L410; P's coefficients in the L v2 freeze).  Class C's one-game test is 0/12 (L272), a neutral anchor.  No legal decision
   this cycle can change -> closed before building; a post-cycle question for a Y / P revision only.
10e DST RECENCY (L335): dstick V1 is frozen and judged by H2 (L400); s.py selects DST on price alone (L348) - a DST recency term reaches no lineup this
   cycle -> closed before building; a post-cycle question for a DST yardstick revision only.

## WORK ORDER 11 / 12 - CLOSED - Oct 3 2026 (pyflakes 3.4.0, read-only scan of every root .py)
11 DEAD BINDINGS: pyflakes reports no local variable assigned and never used anywhere in the kit; 7 unused imports - removed where the file is not recorded
   (contexts.py FROZEN_THRU, deep.py FROZEN_THRU, pgate_audit.py traceback, purity.py pandas), listed where it is (facts.py sys, l.py FROZEN_THRU, score_y.py
   json - frozen / witnessed, kept until the cycle ends).  Limit: pyflakes, like ssot_residue, counts X[...] = as a use (the f_bin pattern stays invisible).
12 COPIED PROCEDURE BLOCKS: the one known instance (residual_s.py:87 = adjudicate.py:91) is gone - residual_s.py deleted in the cleanup, fifth_samples deleted
   from adjudicate.py (AMENDMENT 2).  Function copies stay under guard check 11; block-level extent is not measured.

## CLEANUP 2 - HELD FILES RESOLVED - Oct 3 2026 (code read of facts.py, adjudicate.py, guard.py, research/README.md, README.md, README.txt, WEEKLY.txt)
research/: facts.py reads research/slate_20*_w*_scored.csv only for its self-check against the old canonical pools (facts.py L204) - no such file exists
   (the pools were deleted earlier), so that block already skips; adjudicate.py names "research" in prose only.  research/ holds outputs of retired studies
   (its own index lists studies in guard's REPLACED list), 2019-21 lineup simulations (L85: none can be honest), upload files, lens text and links to the
   deleted funnel.py / laws.json -> deleted; its data link removed as a link (data/ untouched).
README.md, README.txt, WEEKLY.txt: describe the retired builder workflow (build_slate.py, funnel.py, threads.py, organize_sources.py, models.json, blend.json,
   laws.json; WEEKLY's inactives timing contradicts L105) -> deleted; the weekly procedure is CHARTER L153.
build_slate.py, models.json, laws.json: retired by L97 (refresh.py was replaced by fetch.py, L150) and L91 (the builder's copies and models.json retire with S);
   guard.py names build_slate.py only in its allow / known / exemption lists (check targets, not reads) - deleting needs no guard edit -> deleted.
Still held: compose.py, contexts.py (unmapped; a read next); manifest items (data/dk_watch 46 files, get_period_lines.py) need guard --accept; the atlas's
   f-string blind spot.

## SKILL MAP - contexts.py / compose.py, AUDITED - Oct 3 2026 (code read of alloc.py, retarget.py, pgate_audit.py, compose.py, contexts.py, j.build, deep.py L81, p.py gate sites; proj/c_report.txt, proj/compose_report.txt, proj/compose_rules.csv)
OWNER DIRECTION: statistical skill against history is first class - the causal drivers everything else is derived from.  Edge against the DK price and
   decision-unit materiality are derived quantities measured later by their own walls; a skill result is recorded on its own terms, not discounted for lacking them.
UNITS: within-week rank corr (rho) or log-loss gain per slate, paired vs the named baseline; * = p.gate (> 2 s.e., all-but-one season).  Walk-forward tests 2020-25
   (2022 absent by design); compose's composed slices are tested 2023-25 and its composed certainty / beat / boom 2024-25 only.
LABELS: [R] replicated in both scripts on different rows  [W] walk-forward *, one script  [F] fragile (contradicted by the other script)  [C] confounded by the
   target's own reference  [S] selection made on the test seasons  [E] empty - never tested  [N] no skill shown.
SKILL SHOWN
 slice (share) beyond season-to-date [R]: forest vs season - RB carry +0.0121* (c L224) / +0.0117* (compose L29); RB target +0.0169* / +0.0205* (c L225 / compose L31);
   WR target +0.0208* / +0.0199* (c L226 / compose L47); TE target +0.0086* / +0.0068 (3/3) (c L227 / compose L62).  Local-level filter * on all four slices [W].
 steady points (yards + receptions), certainty Lasso vs season [W]: QB +0.0287*, RB +0.0168*, WR +0.0183*, TE +0.0112* (c L24 / L78 / L131 / L184); the filter
   adds nothing on top (-0.0012 to +0.0004).
 TD rank, hierarchical rate x red-zone volume vs raw TD history [W]: RB +0.0331*, WR +0.0154*, TE +0.0558*, QB +0.0152 (4/5) (c L72 / L125 / L178 / L18); inside
   beat / boom logistic it adds <= +0.0002 - no skill through those targets.
 ceiling, p90 quantile boosting vs median x position spread, pinball cut [W]: QB +0.6532*, RB +0.7851*, WR +0.5235*, TE +0.4361* (c L28 / L82 / L135 / L188);
   floor p10: RB +0.0664* only (c L81).
 nonlinearity vs logistic [W]: QB beat boosting +0.0116* (c L6); RB boom boosting +0.0111*, forest +0.0122* (c L65-66); TE beat forest +0.0130* (c L167).
 level skill invisible to rank metrics [W]: deep team rules confirm in 2024-25 the shrinkage of season averages toward the league - team plays (plays_ts <= 79.2 ->
   +2.62 plays, compose_rules.csv; 18 of 19 kept, null 95th 0.0, compose L77) and pass rate (pass_rate_ts <= 0.615 -> +1.4 pts, > 0.66 -> -2.2; compose L105, L111).
   Uniform shrinkage keeps the order within a week, so every rho above scores it zero.  compose prints plays x 100 as "pp" (deep.py L81 labels every target pp).
NO SKILL SHOWN, OR NOT VALID AS SKILL
 team pass rate, forest vs season [F]: +0.0387* (c L221) vs -0.0029 (2/5) (compose L4).
 team plays, game plays, margin, blowout [N]: season / quality gap stands in both scripts; forest worse on game plays (-0.0543 c L223; -0.0725 compose L10).
 composition [N]: the team layer adds negative skill to every slice (compose L14 / L30 / L32 / L48 / L63); composed layers ~0 on certainty / beat / boom;
   script response adds +0.0106 (3/5) to pass rate (compose L5); elasticity loses to proportional opportunity for QB / RB / WR (compose L24 / L42 / L57).
 archetypes, hierarchical TD inside beat / boom, three-way bust / normal / boom [N]: |gain| <= 0.0004, except three-way RB -0.0016 and TE -0.0030.
 pairwise family interactions [N][S]: negative or ~0 except WR boom +0.0012* (c L147); carry sets come from r_families.csv, judged on the same test seasons.
 invariants [S] (descriptive): self volume/role INVARIANT for beat at every position and for boom at QB / WR / TE (not a carrying family for RB boom); slot defense
   INVARIANT for WR boom, TE beat, TE boom (c L144 / L193 / L198); WR boom self scoring INVARIANT and negative (-5.4 pts, c L143).
 rules [C]: ABOVE the shuffled null for every position and target, but beat / boom are defined against dmed and dmed is a split (contexts RULEF L73) - low dmed
   anchors, high dmed anti-patterns (regression of a noisy median).  Rules without dmed: 1 anchor (TE boom, snap_w3 > 0.455 & utr > 0.204, +13.3, c L212) and
   12 anti-patterns (RB boom 1, WR beat 3, WR boom 2, TE beat 2, TE boom 4), all low or falling role; their own count against the null is unmeasured.
 deep player rules with composed layers [E]: FIND = [2020, 2021] holds 0 composed rows (compose L115-142) - "NOT ABOVE" there is an empty test, not a negative.
INSTRUMENTS (same read)
 retarget slot_resid: j.build resid = DK - mean of strictly earlier games (j.build as-of join, allow_exact_matches=False; resid = dk - exp) - no fitted model, no leak.
 pgate_audit: p.py defines gate (p L116) and calls it at 5 sites (L128-146); exec as __main__ binds p's own gate, so none are recorded (its report names p.py only in
   the status line).  Its write block misses pathlib / os.replace / shutil, but none of the 12 targets uses them (grep, 0 hits).  NaN tau/sigma is flagged "robust" (L69).
 alloc: an absence with no row two team-games back is filed "continuing" (alloc L37, L43); verdict unaffected.
Still held: compose.py, contexts.py (atlas rows next); deep.py L81 unit label; pgate_audit p.py blind spot.

## PLAIN-LANGUAGE GLOSSARY - Oct 3 2026 (from code: definition lines of 979 kit terms over 46 files; inventory + definition reads this turn)
One map for any use - a plain read view, a rename, or a re-freeze (owner decision open).  Grouped by what the term forecasts or does.  "code -> plain  [source]".
NAMING PATTERNS (apply by rule; they compose: tgt_sh_ws -> target_share_season_avg)
 _ws -> _season_avg (earlier games, this season) [retarget L21]   _w3 -> _last3_avg   _w1, _l1 -> _last_game   _m -> _to_date [alloc L35]   _thru -> _through_game [avail L35]
 _ts -> _team_season_avg [retarget L47]   _t3 -> _team_last3_avg   _hat -> _pred [compose]   oppo_ -> opp_offense_   dal_ -> opp_def_allowed_   oppd_ -> opp_def_vs_pos_
 tm_ -> teammate_   abs_ -> vacated_   f_ -> filter_ [contexts L42]   rz_ -> redzone_   gl_ -> goal_line_
IDENTITY + INFORMATION SET
 gsis -> player_id [facts L140]   tgi -> team_game_no [j.build]   pos -> position   opp -> opponent   home -> is_home   K -> PLAYER_KEYS   TK -> TEAM_KEYS
 SK -> SKILL_POSITIONS   SCPOS, POS3 -> RB_WR_TE   FROZEN_THRU (last season producers fit on, 2025) [p L16]   DEV_BEFORE (dev seasons end before 2024) [avail L26]
 asof, frame, candidates, outside, descriptors - already plain [p L28-69]
OUTCOMES (labels - never inputs for the same week)
 dk -> dk_points   steady -> steady_points (yards + receptions) [retarget L32]   tdpts -> td_points   tde -> td_count   rzo -> redzone_opps [contexts L62-63]
 beat -> beat_own_median   boom (>= 1.5x own median and +5)   bust [contexts L68]   t_steady -> steady_change   t_td -> td_change   dst_pts -> dst_points
OPPORTUNITY + ROLE
 tgt_sh -> target_share   car_sh -> carry_share   air_sh -> air_yards_share   snap -> snap_share   opps -> opportunities   utr -> snap_trend [retarget L105]
 sstd -> season_role_state (0-3 by snap .05/.35/.70) [p L86]   st1 -> last_role_state (a L16 use)   rs -> snap_state (1/2/3)   rsb -> snap_state_label [at_t L19]
 role_states (0 out, 1 <.35, 2 .35-.70, 3 >=.70, -1 snap unknown) [p L75]   collapse -> role_collapse [regime_test L50]   n_prior -> games_before
 n_thru -> games_through_game   prev_team -> prev_played_team [shorthist L32]   tgi_last / team_last -> last_played_team_game / last_played_team (avail L42 use)
 role (j.build) -> snap_share_to_date   slot -> depth_slot   in_slot -> has_slot   elas -> plays_elasticity [compose L90]
PARTICIPATION
 gap -> games_missed (team-games since his last played, same team) [avail L42]   gapb -> games_missed_band (0/1/2+)   gapg -> played_last_or_missed [aaudit L26]
 absent -> did_not_play [avail L44]   self_missed -> missed_last_team_game   AVF -> AVAIL_INPUTS   p_play, p_a -> p_plays [h7 L84]   p_T1, p_t1 -> p_plays_t1
 q_B -> p_absent_base [avail L64]   q_M -> p_absent_calibrated [avail L70]   q_R -> p_absent_logistic [classe L66]
CENTER / FLOOR / CEILING (Y, DST)
 c (Y files) -> center   pi, near_zero_p -> p_near_zero (one meaning) [ystick L80, adjudicate L76]   ZERO -> NEAR_ZERO_DK   f0 -> near_zero_pit   ford -> ordinary_pit
 f_smo -> ordinary_pit_window   so_te -> ordinary_scale   fifth / tenth -> center_fifth / center_tenth   kb -> shrink_k   peer -> peer_mean   KGRID -> SHRINK_GRID
 WIN -> WINDOW_FRAC   dmed -> own_median_dk   dsd -> own_dk_sd   vol -> dk_volatility   eff -> steady_per_opp   tdshare -> td_share_of_dk
 exp (j.build) -> dk_expected   resid (j.build) -> dk_minus_expected   EXP -> EXPECTED_POINTS [jexpose L40]   Hst -> history_rows   Nx, NX -> coming_week_rows
 fit_apply / short_apply / ds_center / ds_dist - already descriptive [ystick L44, L83; dstick L28, L34]
TEAM + GAME
 qgap -> quality_gap   blow -> blowout   gp -> game_plays   neutral_spp -> neutral_secs_per_play   res_last -> last_result   margin_last -> last_margin
 short / long -> short_rest / long_rest
JOINT + LINEUP + PRICE
 best9 (exact salary-capped lineup) [lineups9 L6]   in_lineup [s L50]   sal_k -> salary_thousands [p L51]   price_act -> price_lineup_actual_points [l L67]
 l0 -> loglik_independent [j L91]   ll (j / jy column) -> loglik_model
JUDGING + CALIBRATION
 result, result_pct, result_u -> outcome_pit, outcome_pit_pct [ystick L80, L115; score_d L60]   ds_mad, rg_mad -> pit_decile_mad [dstick L53, register L43]
 h7_fail, ss_fail, sd_fail, at_fail, aa_fails -> subgroup_calib_fails [h7 L46, score_s L20]   n95 -> fails_noise_95th [aaudit L43]   BAT -> TEST_BATTERY [canon L30]
 paired -> paired_by_slate   gate -> passes_gate [p L116]   se -> std_err   sp -> spearman   ll (function) -> log_loss [retarget L22]   NNULL -> NULL_DRAWS
 nul -> null_scores   p95 -> null_95th   tr / te -> train / test   stratum -> chain_class (A/B/C) [chain L60]
SAME NAME, TWO MEANINGS (split on any use)
 tier: center_tier [adjudicate L99, ystick L30] vs warning_tier [classe L34]     TIERS: CENTER_TIERS vs WARNING_TIERS [classe L26]
 ll: log_loss (function) vs loglik_model (column)     recorded: is_on_record [canon L52] vs had_stat_line [facts L141]     asof: function [p L65] vs fit_basis label [dstick L82]
 WS: jy L57 vs wr_rows [ystick L145]     J, CJ: per-file (atlas L11 path join; contexts L98 family index; h7 L16 path; jy L119 fit)
NOT MAPPED: generic locals (w x k r f g v s d c n a m p t y and similar - meaning changes by file; per file or left as is); meaning not shown in code: POW, marg_fail,
 d_noise, partial, TEXP, CEXP, LV, WJ, WY.

## SKILL ATLAS - contexts.py / compose.py claims in fixed fields - Oct 3 2026 (rows from SKILL MAP above; owner review this turn)
TERMS: a VALIDATED PREDICTIVE DRIVER shows walk-forward skill against history; a CAUSAL DRIVER is reserved for the natural-experiment layer.  Every claim names
   its CONSUMER - the one term of the forecast it improves: role/volume | conditional center | conditional floor | conditional ceiling | participation |
   dependence | price/value | evaluation | none.
FORECAST: P(Y_i | info before kickoff) = (1 - p_i) delta_0 + p_i F_i(y | role, context); joint = J coupling of the F_i; lineup chosen from that joint under salary;
   price is the benchmark the forecast is compared with, not an input unless earned.
DELETION GATE: a script that produces skill is deleted only when every claim it makes carries metric, unit, baseline, season / fold structure, gate-recorded status and
   evidence label below.
FIELDS: id | driver | target | metric (unit) | gain | baseline | positions | test span | evidence | causal | price edge | consumer | gate recorded
S01 | history families, random forest | carry_sh RB; tgt_sh RB WR TE | within-week rank corr, paired by slate (rho) | RB carry +0.0121* / +0.0117*, RB tgt +0.0169* /
   +0.0205*, WR tgt +0.0208* / +0.0199*, TE tgt +0.0086* / +0.0068 | share season-to-date | RB WR TE | contexts 2020-25 walk-forward; compose 2021-25 fit, 2023-25 test |
   R (TE: W) | predictive only | not measured | role/volume | no
S02 | local-level filter of own share | same slices | rho | RB carry +0.0174*, RB tgt +0.0028*, WR +0.0090*, TE +0.0038* | share season-to-date | RB WR TE |
   contexts 2020-25 | W | predictive only | not measured | role/volume | no
S03 | certainty Lasso on history families | steady points | rho | QB +0.0287*, RB +0.0168*, WR +0.0183*, TE +0.0112*; filter on top -0.0012 to +0.0004 |
   steady season-to-date | QB RB WR TE | contexts 2020-25 | W | predictive only | not measured | conditional center | no
S04 | hierarchical TD rate x red-zone volume | TD count next game | rho | RB +0.0331*, WR +0.0154*, TE +0.0558*, QB +0.0152 (4/5) | raw TD points season-to-date |
   QB RB WR TE | contexts 2020-25 | W (QB: none starred) | predictive only | not measured | conditional ceiling | no
S05 | quantile boosting (tau .9) | DK points | pinball loss cut (DK pts) | QB +0.6532*, RB +0.7851*, WR +0.5235*, TE +0.4361* | dmed x position ratio quantile |
   QB RB WR TE | contexts 2020-25 | W | predictive only | not measured | conditional ceiling | no
S06 | quantile boosting (tau .1) | DK points | pinball loss cut (DK pts) | RB +0.0664*; QB -0.0256, WR +0.0181, TE +0.0002 not starred | same | QB RB WR TE |
   contexts 2020-25 | W (RB only) | predictive only | not measured | conditional floor | no
S07 | boosting / forest vs logistic | beat median; boom | log-loss gain per slate (nats) | QB beat boosting +0.0116*; RB boom boosting +0.0111*, forest +0.0122*;
   TE beat forest +0.0130* | logistic, same features | QB RB WR TE | contexts 2020-25 | W | predictive only | not measured | conditional center (beat), conditional
   ceiling (boom) | no
S08 | shrinkage of team season averages (deep rules) | team plays; pass rate | level (plays; pass-rate pts) | plays_ts <= 79.2 -> +2.62 plays (18 of 19 kept);
   pass_rate_ts <= 0.615 -> +1.4, > 0.66 -> -2.2 | team season-to-date | team | find 2020-21, refine 2023, confirm 2024-25; shuffled null 95th 0.0 | W |
   predictive only | not measured | role/volume | no (rank corr scores uniform shrinkage zero)
N01 | random forest | team pass rate | rho | +0.0387* (contexts) vs -0.0029 (2/5) (compose) | season | team | 2020-25 / 2021-25 | F | - | - | none | no
N02 | forest / composed | team plays, game plays, margin, blowout | rho | season or quality gap stands; game plays forest -0.0543 / -0.0725 | season / quality gap |
   team | 2020-25 / 2021-25 | N | - | - | none | no
N03 | composed team layer | slices; certainty / beat / boom | rho; log-loss | slices -0.0030 to -0.0198; composed ~0 | same model without | QB RB WR TE |
   compose 2023-25 / 2024-25 | N | - | - | none | no
N04 | elasticity x expected size change | opportunity change | rho | QB -0.0309, RB -0.0263, WR -0.0052, TE +0.0151 | proportional | QB RB WR TE | compose 2023-25 | N |
   - | - | none | no
N05 | archetypes; hierarchical TD inside beat / boom; three-way | beat; boom | log-loss | |gain| <= 0.0004; three-way RB -0.0016, TE -0.0030 | logistic |
   QB RB WR TE | contexts 2020-25 | N | - | - | none | no
N06 | pairwise family interactions | beat; boom | log-loss | negative or ~0; WR boom +0.0012* | additive families | QB RB WR TE | contexts 2020-25 | N, S | - | - |
   none | no
N07 | carrying-family effect by context | beat; boom | rate gap top vs bottom third (pts) | self volume/role INVARIANT (all beat; QB WR TE boom); slot defense
   INVARIANT WR boom, TE beat, TE boom | - | QB RB WR TE | contexts 2020-25 | S (descriptive) | - | - | none | no
N08 | shallow-tree rules | beat; boom | holdout rules vs shuffled null (count) | ABOVE everywhere; dmed-split rules confounded; dmed-free: 1 anchor, 12 anti-patterns |
   holdout base rate | QB RB WR TE | fit 2019-21, judged 2023-25 | C | - | - | none | no
N09 | deep rules on composed player layers | beat / boom bands; slices | rules confirmed | 0 rows in FIND 2020-21 | - | QB RB WR TE | none | E | - | - | none | no

## RENAME REHASH - Oct 3 2026 (owner: the rename is first class, hashes second; new hashes accepted)
L freeze: start [2026, 4] unchanged; hashes rewritten for 9 files changed by the rename (s.py, l.py, p.py, a.py, j.py, facts.py, lineups9.py, proj/p_coef.json, proj/a_cells.json); frozen_at kept, rehashed_at added.
Recorded after the rename (SSOT check 11): dstick.py f527f2cf, h7.py 2c54fa56, register.py 40072739, ystick.py 63243000.
Issued week-4 records (issued_y / issued_d_2026_w4.pkl) untouched: they carry the pre-rename code hashes they were issued with.

## CONSUMPTION MAP - which measured skill the forecast uses - Oct 3 2026 (reads: p_coef.json inputs; ystick.py docstring L31-34, NEED, PF; p.py walk L71-75; retarget FAM0)
P (fit 2019-21; value relative to salary): QB / TE usage axis (dk_points_season_mean + snap / target / carry / air-yards share season means); RB usage axis +
   last-game shares; WR last-game shares only.  Salary cubic inside every prediction (value = pred_dk - sal_pts).  Tested, not kept: prior season, rest + home, dk lag 1.
Y (walk-forward 2020-25; history-only distribution): center = shrunk dk_points_season_avg + last game + last 3 + snap_trend; near-zero = center, snap season /
   last game / last 3, |snap swing|, opportunities season / last game / last 3, games_before, missed_last_team_game; p10 / p90 = nearest 20% of training centers.
retarget families vs consumers (P | Y | validated skill | forecast term):
   self volume/role, shares          | yes | no  | S01 [R], S02 [W] beat the season-average shares P uses | role/volume
   self volume/role, snaps / opps    | no  | yes | invariant (N07, S) | center, floor
   self volume/role, steady / counts | no  | no  | S03 [W] | center
   self scoring, DK points           | yes | yes | - | center
   self scoring, own_median_dk, dk_volatility, steady_per_opp, td_share_of_dk, td_points | no | no | inside S03 / S05 | center, ceiling
   self red zone                     | no  | no  | S04 [W] | ceiling
   self returning                    | no  | yes | - | floor
   teammates; absence (history); team size/pace; team type; team quality; discipline; opponent defense; opponent offense; situation | no | no |
      none valid (N01 F, N02 N; Class A closed R11; rest + home not kept by P) | -
   slot defense                      | no  | no  | invariant WR boom, TE beat, TE boom (S, descriptive) | ceiling
   distribution shape                | -   | center-window only | S05 [W] p90, S06 [W] RB p10 | ceiling, floor
   nonlinearity                      | linear | logistic / OLS | S07 [W] | center, ceiling
READING: P and Y split the usage information (P shares, Y snaps / opportunities); every validated driver (S01, S03-S07) is consumed by neither; P is the only
   consumer of price.  Gate for stranded skill: TERM SKILL (registered above).  Unifying P and Y usage is a method change - a later L start week (owner).
UNKNOWN: which of P / Y supplies the center s.py simulates (s.py not read here).

## S CONSUMPTION + WALL RULE - Oct 3 2026 (code read of s.py, lineups9.py, card.py; grep of center / p10 / p90 / p_near_zero / p_plays / ystick / p_coef / j_model over *.py)
WHAT REACHES THE LINEUP (s.py): projection pred = P's frozen coefficients on p.asof inputs, salary cubic included (s L32-37); DST pred = DST salary curve alone (L38-39);
   p_plays = A's frozen cells (L44); lineup = lineups9.best9 on dk_expected = pred x p_plays (L46-47); lineup distribution = Monte Carlo of pred + J's margin quantile per
   depth slot through J's copula, x Bernoulli(p_plays) (L56-65).
WHAT DOES NOT: Y (center, p10, p50, p90, p_near_zero) and dstick V1 are read only by card.py (display, "never merged", card L6-7) and by scorers / studies (score_y,
   score_t, register, gatesim, jy, classe).  H7's T1 p_plays is issued beside A (h7 L83-85), not used by s.py.
OPERATIONAL TERMS: center = P pred (relative to salary); participation = A; shape / floor / ceiling / dependence = J margins + copula (residuals vs season-to-date mean added
   to P's pred - declared mismatch, s.py docstring L7-8); price / value = inside P.  Y is the history-only yardstick: display and evaluation.
CONSEQUENCE FOR TERM SKILL: a driver that earns a Y term improves the yardstick and the card, not the lineup; reaching the lineup means P (center), A (participation) or
   J margins (shape).  TERM SKILL's target is an owner decision (work order).
AMENDMENT to CONSUMPTION MAP: "every validated driver (S01, S03-S07) is consumed by neither" reads: every validated FORM S01 / S03-S07 is not consumed as validated;
   some underlying variables already appear in P or Y (e.g. S01's shares in P).
WALL RULE (owner review): no wall opens without four lines - FORECAST TERM | CURRENT BASELINE (exact producer / output) | CANDIDATE SKILL (exact atlas row) |
   SUCCESS CONSEQUENCE (which output changes if it earns).  P and Y are not unified for duplication alone.

## TERM-SKILL LADDER - Oct 3 2026 (owner decision (c): both, Y first)
RULE: predictive skill is first adjudicated against the forecast term it claims to improve, using Y's five-season walk-forward history where applicable.  Only an earned
   term advances to the narrower live-chain test against the quantity consumed by S (center -> P under P's add rule; shape / dependence -> J margins and copula).
   Failure at either wall closes the branch.  Any integration into the frozen live method requires a new prospective L start week.
CORRECTION: CONSUMPTION MAP's "TERM SKILL (registered above)" was premature - the registration below is its first appearance.

## TERM SKILL - STAGE 1 (Y) - REGISTRATION - Oct 3 2026 (reads: ystick_rows walk-forward "fit on seasons < s", 2020-25; ystick.py docstring; p.py paired_by_slate / passes_gate; retarget names)
ROWS: ystick history rows, models SC (RB WR TE) and QB-v2, seasons <= FROZEN_THRU, inner-joined on player_id / season / week to retarget's player rows with every
   history-family feature; tests 2020, 2021, 2023, 2024, 2025; each season predicted by models fit on retarget rows of earlier seasons.  Gate: passes_gate on paired_by_slate.
   Script term_skill.py, report proj/term_skill_report.txt; hyperparameters exactly as contexts.py; coverage and MAE reported, not gated.  First NO is the ceiling.
T1 CEILING  term: conditional ceiling | baseline: ystick p90 | candidate: S05 quantile boosting tau .9 on the history families | consequence if earned: S05 advances to
   stage 2 against J's margin upper tail (the live shape), else S05 closed for the forecast.  Metric: pinball loss (DK pts), per slate.
T2 FLOOR    term: conditional floor | baseline: ystick p10 | candidate: S06 quantile boosting tau .1 | consequence: as T1, against J's lower tail.
T3 CENTER   term: conditional center | baseline: ystick center | candidate: S03 certainty Lasso steady-points prediction, stacked M1 = OLS on earlier seasons' joined rows of
   DK on [center, S03] | consequence: S03 advances to stage 2 under P's add rule (2020-21), else closed.  Metric: within-slate rank corr with DK (rho); tests 2021-25.
T4 TD       term: conditional center (TD component; atlas consumer ceiling) | baseline: M1 | candidate: S04 hierarchical TD rate x red-zone volume, M2 = M1 + S04 |
   consequence: as T3.
DECLARED NOT IN THIS RUN: S01 / S02 (share forms feeding the center) and S07 (needs Y's full predictive CDF, available only inside ystick's in-memory run) - later lines.

## TERM SKILL - STAGE 1 (Y) - OUTCOME - Oct 3 2026 (proj/term_skill_report.txt; tests 2020-25, center stack 2021-25)
S03 certainty -> Y center: RB +0.0108+-0.0023 (4/4) *, WR +0.0083+-0.0013 (4/4) *, TE +0.0100+-0.0020 (4/4) * -> EARNED, advances to stage 2; QB +0.0118+-0.0083 (3/4)
   -> CLOSED.  MAE (DK pts) center -> M1: RB 4.854 -> 4.825, WR 4.692 -> 4.658, TE 3.466 -> 3.393 (reported, not gated).
S05 quantile boosting p90 vs ystick p90: QB -0.0171 (1/5), RB -0.0447 (0/5), WR -0.0259 (0/5), TE -0.0476 (0/5) -> CLOSED.
S06 quantile boosting p10 vs ystick p10: QB -0.0309 (2/5), RB -0.0171 (1/5), WR -0.0509 (0/5), TE -0.0303 (0/5) -> CLOSED.
S04 TD rate over M1: QB +0.0016 (2/4), RB -0.0001, WR -0.0003, TE +0.0000 -> CLOSED.
LEDGER STATE: S04 / S05 / S06 / S03-QB - standalone historical skill yes; incremental forecast-term skill no; CLOSED for the current forecast (not reopened on coverage).
   Frozen Y ceiling and floor stand.  Surviving: S03 for RB / WR / TE -> center.

## TERM SKILL - STAGE 2 (P) S03 - REGISTRATION - Oct 3 2026 (reads: p.py walk / FULLC / ADD rule L104-116; p_coef.json inputs; P domain 2019-21)
term: center used by the lineup | baseline: P with its current inputs (p_coef.json), P's walk and partial rank corr given salary | candidate: S03 certainty Lasso
   steady-points prediction as ONE added input, RB / WR / TE | consequence if earned: candidate method change (P + S03) requiring a later L start week (owner);
   else S03 stays Y-center skill only and is CLOSED for the lineup chain.
DOMAIN: P's priced, played rows weeks 4-16, seasons <= FROZEN_THRU.  Facts begin 2019, so S03 cannot be walk-forward on 2019 rows: TEST 2021 ONLY (P trains on
   2019-20, as its walk); S03 on training rows is season-cross-fit without the test season (2019 <- fit on 2020, 2020 <- fit on 2019), test rows <- fit on 2019-20.
   One test season makes "all-but-one season" trivial; the gate rests on > 2 s.e. across 2021 slates (declared, low power).
RULE (P's own): eligible iff S03 is defined on every row P projects (hole = 0); EARNED iff eligible and paired gain passes p.passes_gate.  Rows where S03 exists:
   gain reported, not gated.  Script term_skill_p.py, report proj/term_skill_p_report.txt.  First NO is the ceiling.

## TERM SKILL - STAGE 2 (P) S03 - OUTCOME - Oct 3 2026 (proj/term_skill_p_report.txt; test 2021; P add-test rows = S03 defined + FULLC; first recorded in LEDGER RESTORE)
RB: undefined on 463 of 3356 rows P projects; where defined (1596 rows) P rho +0.1801 -> +0.1766, gain -0.0035+-0.0049, MAE 5.337 -> 5.348 -> CLOSED for the lineup chain.
TE: undefined on 443 of 3159; where defined (1624) +0.2801 -> +0.2743, gain -0.0059+-0.0104, MAE 3.699 -> 3.685 -> CLOSED for the lineup chain.
WR: undefined on 617 of 5466; where defined (2624; 2021: 1381) +0.1408 -> +0.1693, gain +0.0285+-0.0074 *, MAE 5.173 -> 5.125 -> DOMAIN-BOUNDARY LEAD: not eligible under
   P's no-hole rule; no fallback this cycle; extending S03 to the uncovered rows is a separately registered wall and any integration needs a later L start week.
STATE: no method change.  S03 stands as Y-center skill for RB / WR / TE; lineup-chain skill shown only for WR on its covered rows (one test season).

## FORECAST HIERARCHY + STAT-SPINE RULES - Oct 3 2026 (owner decisions this session)
DELIVERABLE: using only information knowable before game N (N >= 4), forecast the game / team / player stat distribution as accurately as possible.  Fantasy points are
   derived from it (F8); DK price and lineups are compared afterwards (F9).  Salary is not an input to the primary forecast (the price file may still supply opponent /
   home / kickoff).  Order: football truth -> fantasy consequence -> market consequence.
HIERARCHY: F0 information | F1 game state | F2 team volume | F3 participation | F4 role allocation | F5 player stats | F6 uncertainty / dependence | F7 primary evaluation
   (stat units) | F8 fantasy transform | F9 market / lineup.  Current producers: F3 A / T1; F6 J; F8 Y; F9 P (salary inside every prediction) and S, judged by L.
   F2, F4, F5 have no canonical producer and F7 no evaluator.  F2 has evidence: season-level plays / pass rate stand as baseline and extremes shrink (N01, N02, S08), so
   its first wall starts from that historical level baseline.
WALL RULE (six fields; replaces the four-line rule for new walls): primary target (the statistic or state) | information time (before game N, N >= 4) | current baseline
   for that exact quantity | one candidate improvement | metric in the quantity's own units | consumer (next layer).  No wall opens with target or consumer empty.
INDEX STATES: every F-row records evidence exists -> producer exists -> evaluator exists.  Demonstrated skill is not an earned producer (S01 share and S04 TD rank are skill
   against their historical baselines only; S01 has not faced a recency-weighted share baseline).
STAT-SPINE PROSPECTIVE START RULE (owner option d): the F2 -> F4 -> F5 -> F7 spine is built and validated on historical data only - every legal football season, not limited
   to priced seasons; strict walk-forward chronology, no random CV as judge - plus simulations derived from historical structure that test procedures (power, false
   positives, early-season bias, whether a metric can separate candidates), never mechanisms, and never select among candidates.  Once the full spine passes its
   pre-registered walk-forward and procedure gates, every producer / evaluator is frozen; the first prospective test is the next NFL week whose games have not begun at
   the moment of freeze.  No earlier 2026 week is claimed.  L v2 (DK track, start 2026 week 4) is unchanged.
VERSION RULE: stat spine v1 contains only components earned before its freeze (the freeze record lists each component's CHARTER outcome line).  Any later improvement
   (S01 / S02 / context candidates / others) is a challenger architecture and, if adopted, starts a new prospective clock from the next untouched week.
SPINE v1 SCOPE: minimal - team pass attempts x target share = targets; team rush attempts x carry share = carries; receptions / yards / TDs added one wall at a time.
WITHDRAWN: TERM SKILL STAGE 1 (Y) S01 (block never run; it would have judged an F4 share claim by an F8 metric).
CORRECTION to CONSUMPTION MAP: "opponent defense ... none valid" is wrong - c_report lists opponent defense (components) as carrying for QB boom, RB beat median and RB boom
   (c_report L39, L90, L93; descriptive, selection S).  Opponent defense and slot defense are context candidates feeding F5 (from F1 / F2 / opponent state), untested
   against stats.

## FUNNEL INDEX - F0-F9 - Oct 3 2026 (reads: atlas.py rows R01-R27; CHARTER L14, L112-113; facts_report header: complete seasons 2019-21, 2023-26)
COLUMNS: F-row | target | evidence | producer | evaluator | status | bottom-up trace | limitation / next.  "missing" = no canonical pregame producer / no evaluator in the
   quantity's own units.  A research script or historical report is evidence, not a producer or an F7 evaluator.  History for every F2-F7 wall: 2019-21, 2023-25
   (no complete season before 2019; 2022 absent); 2026 live (FROZEN_THRU 2025).  RULE 2 amended (L112-113) already separates accuracy from value vs price.
F0 | legal pregame frame, N >= 4 | yes | p.frame / p.asof, WEEKN exclusion | guard checks; R23 causal-boundary audits | live | R07, R08, R23 | -
F1 | margin / blowout | yes: season quality gap stands, forest no (N02) | missing | missing | evidence only | N02 | consumer F2 / F6 not yet named
F1 | game total | none | missing | missing | UNKNOWN | - | opens only when a stat term needs it
F1 | pace / game plays | yes: season average stands (N02) | missing | missing | evidence only | N02 | folds into F2
F2 | team plays, pass attempts, rush attempts | yes: season level stands (N02), forest pass rate fragile (N01), extremes shrink (S08 W) | missing | missing | OPEN - spine
   wall 1 | N01, N02, S08 | baseline = team season level with earned shrinkage; metric = attempts / plays error; consumer F4 / F5
F3 | P(plays) | yes: T1 lever (R12), boundaries (R07, R08), tail by transition null (R13), A on priced domain (R26 anti-pattern), A vs T1 (R27 boundary) | A (live in S);
   T1 issued via H7 | A scorer (score_s); H7 prospective | live | R07 R08 R12 R13 R26 R27 | -
F4 | target / carry / snap share | yes: S01 [R] and S02 [W] vs season share; role collapse predictable (R03, open); vacancy correction closed (R11); carries go to other
   RBs (R10, descriptive); team layer adds nothing (N03); elasticity no (N04) | missing (P consumes shares as inputs, forecasts none) | missing | OPEN - spine wall 2 |
   R03 R10 R11 S01 S02 N03 N04 | S01 not yet vs a recency-weighted share; enters v1 only if earned before the freeze
F5 | targets, carries, receptions, yards, TDs | yes: TD rank (S04 W vs raw TD history); steady points (S03: earned on Y center RB / WR / TE, closed for the lineup, WR
   boundary); opponent / slot defense context candidates (S, untested vs stats); rules confounded (N08); composition persistence null (R05); deep rules (R19 open);
   absence chain (R17 open) | missing | missing | OPEN - spine walls 3+ | R05 R17 R19 S03 S04 N08 | counting identities first (attempts x share), then
   receptions / yards / TDs one wall at a time
F6 | stat uncertainty / dependence | fantasy-level only: J co-movement (R06), tail corners closed (R15), selector W0 inconclusive (R16) | missing in stat units (J and Y
   work in DK points) | missing | OPEN after F5 | R06 R15 R16 | -
F7 | stat-unit evaluation of the canonical forecast | procedure findings only: exhaustive grid (R20), empty-root stress test (R21), gate resolution (R22), log-loss clip
   (R24) | n/a | missing | OPEN - built with each spine wall; procedure harness line 38 | R20 R21 R22 R24 | each layer scoreable before the next consumes it
F8 | DK-point distribution | yes: SC architecture (R01), anti-patterns (R02), WR-short (R04), DST V1 (R09), gap-0 shape immaterial (R14); S05 / S06 / S04 closed vs Y;
   S07 open | Y, dstick | Y / dstick scorers (H1-H3) | live | R01 R02 R04 R09 R14 S03-S07 | later: F8 = g(F3, F4, F5, F6)
F9 | value vs price, lineup | yes: P (salary inside), S, old information set (R18 neutral), retired builder (R25 anti-pattern), price reaction (R17 open), H6, WR S03 lead
   | P, S | L v2 (from 2026 week 4) | live, frozen | R17 R18 R25 | -
STRUCTURE (confirmed by the reads): no atlas row is a stat producer or stat evaluator - F2, F4, F5, F6 (stat units) and F7 are the missing machinery (line 36).
PROCESS RULES (added): every layer is scoreable in its own units before the next layer may depend on it; historical seasons may not be re-mined until an architecture
   passes - each spine wall is registered once and judged once; closed walls, boundaries and resolution limits are recorded as findings; every transaction states which
   piece of F2 -> F4 -> F5 -> F7 uncertainty it reduces, or is deferred.

## STAT SPINE - WALL 1 (F2 team volume) - REGISTRATION - Oct 3 2026 (reads: facts.py L132-134 share denominators; p.py load / team_game / paired_by_slate / passes_gate; FUNNEL INDEX)
primary target: team targets, team carries, team pass attempts per team-game (sums over players who played; targets / carries are the denominators of F4's shares, facts
   L132-134) | information time: results through week N-1, N >= 4 (weeks 4-16, >= 3 earlier team-games this season) | current baseline: team season-to-date mean (N02 season
   level) | candidate: that mean shrunk toward the training seasons' league mean, strength k chosen on training seasons by MAE (grid 0-40; k = 0 equals the baseline) |
   metric: MAE in counts per team-game, paired by slate; reported: league-mean MAE (does the season level carry skill), chosen k | consumer: F4 shares -> F5 counts.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025 (history 2019-21, 2023-25).  GATE: passes_gate on paired MAE reduction, per target.  EARNED -> the shrunk level is F2 v1 for
   that target; else the season-to-date mean is F2 v1 (the baseline stands).  Either way F2 v1 is fixed for the spine; procedure check (line 38) before any freeze.
   Script spine_f2.py, report proj/spine_f2_report.txt.  Registered once, judged once.

## STAT SPINE - WALL 1 (F2) - OUTCOME - Oct 3 2026 (proj/spine_f2_report.txt; tests 2020-21, 2023-25; 384 team-games per season)
targets: MAE league mean 6.292, season-to-date 6.237 (+0.060+-0.078, 3/5), shrunk 6.022 - cut over season-to-date +0.2113+-0.0461 (5/5) *, k 5 every season.
carries: 6.110 / 6.192 (-0.084, 1/5) / 5.994 - cut +0.1981+-0.0513 (5/5) *, k 8-12.   attempts: 6.498 / 6.527 (-0.022, 2/5) / 6.283 - cut +0.2383+-0.0546 (5/5) *, k 5-8.
F2 v1 = shrunk team level (team season-to-date mean shrunk toward the training league mean, k chosen on training seasons) for targets, carries, pass attempts.
RESOLUTION LIMIT: the season level alone does not beat the league mean; the shrunk level beats it by only 2-4% (MAE ~6 on means 27-34) - most team-game volume variation
   is not forecastable from team history.  Recorded as a finding.

## STAT SPINE - WALL 2 (F4 shares) - REGISTRATION - Oct 3 2026 (reads: p.py OUTC share columns; facts L182 played-with-no-stat = 0)
primary target: next-game share given he plays - RB carry_share, RB / WR / TE target_share | information time: through week N-1, weeks 4-16, >= 3 earlier played games for
   this team this season | current baseline: season-to-date share (the form P consumes; S01's baseline) | candidate: recency-weighted share, weight w^lag on earlier games,
   w chosen on training seasons by MAE from {1.0, 0.9, 0.8, 0.7, 0.6, 0.5} (1.0 = baseline) | metric: share MAE, paired by slate | consumer: F5 counts = F2 v1 x F4.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate per slice.  EARNED -> recency share is F4 v1 for that slice; else season-to-date share is F4 v1.  The
   winner is the bar for S01 / S02 as challengers.  Declared: players with < 3 earlier games on the team are not covered (shares need not sum to 1); team change restarts
   history.  Script spine_f4.py, report proj/spine_f4_report.txt.  Registered once, judged once.

## STAT SPINE - WALL 2 (F4) - OUTCOME - Oct 3 2026 (proj/spine_f4_report.txt; tests 2020-21, 2023-25)
RB carry_share: MAE 0.10978 -> 0.10491, cut +0.00473+-0.00072 (5/5) *, w 0.6 every season -> recency share is F4 v1.
RB target_share: 0.03852 -> 0.03855, -0.00004+-0.00008 (1/5) -> season-to-date share is F4 v1.
WR target_share: 0.05468 -> 0.05401, +0.00066+-0.00015 (5/5) *, w 0.8 -> recency.   TE target_share: 0.03930 -> 0.03911, +0.00018+-0.00006 (5/5) *, w 0.9 -> recency.
F4 v1: recency-weighted share (w chosen on training seasons) for RB carry / WR target / TE target; season-to-date share for RB target.  This is the bar for S01 / S02.

## STAT SPINE - WALL 3 (F5 counts: targets, carries) - REGISTRATION - Oct 3 2026 (reads: walls 1-2 outcomes; spine_f2.py / spine_f4.py procedures)
primary target: player targets (RB / WR / TE) and RB carries per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the
   team | current baseline: his season-to-date mean count on the team | candidate: F2 v1 team count x F4 v1 share, each re-fit on training seasons inside each fold by its
   registered procedure (form per slice fixed by walls 1-2) | metric: count MAE, paired by slate | consumer: later F5 walls (receptions, yards, TDs) and F8.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate per slice.  EARNED -> the identity is F5 v1 for that count; else his season-to-date count is F5 v1.
   Script spine_f5.py, report proj/spine_f5_report.txt.  Registered once, judged once.

## STAT SPINE - WALL 3 (F5 targets / carries) - OUTCOME - Oct 3 2026 (proj/spine_f5_report.txt; tests 2020-21, 2023-25)
RB carries: MAE 3.4463 -> 3.3293, cut +0.1187+-0.0217 (5/5) * -> F5 v1 = F2 v1 x F4 v1.   WR targets: 1.9049 -> 1.8788, +0.0258+-0.0054 (5/5) * -> F5 v1 = identity.
RB targets: 1.3061 -> 1.3000, +0.0059+-0.0030 (4/5) -> F5 v1 = his season-to-date count.   TE targets: 1.3393 -> 1.3332, +0.0060+-0.0036 (3/5) -> F5 v1 = season-to-date.
The identity earns exactly where wall 2's recency gain was large (RB carry w 0.6, WR target w 0.8); near misses are not re-tried on these seasons.

## STAT SPINE - WALL 4 (F5 receptions) - REGISTRATION - Oct 3 2026 (reads: wall 3 outcome; p.py OUTC receptions)
primary target: player receptions (RB / WR / TE) per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team |
   current baseline: his season-to-date mean receptions | candidate: F5 v1 targets x his season-to-date catch rate (earlier receptions / earlier targets) | metric:
   reception MAE, paired by slate | consumer: yards walls; F8 (1 DK point per reception).
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate per position.  EARNED -> targets x catch rate is F5 v1 receptions; else his season-to-date receptions.
   Declared: rows with no earlier targets (catch rate undefined) are dropped from both arms and counted.  Script spine_rec.py.  Registered once, judged once.

## STAT SPINE - WALL 4 (F5 receptions) - OUTCOME - Oct 3 2026 (proj/spine_rec_report.txt; 1474 rows without earlier targets dropped: RB 479, WR 472, TE 523)
WR: MAE 1.4400 -> 1.4328, cut +0.0064+-0.0034 (5/5) - below 2 s.e. -> NOT SHOWN.
RB, TE: cut exactly 0 - NO TEST: with F5 v1 targets = season-to-date, mean targets x (receptions / targets so far) = mean receptions by construction (registration error).
F5 v1 receptions = his season-to-date mean receptions (all positions).
RULE (added): a candidate identical to the baseline by construction on a slice is declared NO TEST at registration and not run.

## STAT SPINE - WALL 5 (F5 yards) - REGISTRATION - Oct 3 2026 (reads: walls 3-4 outcomes; p.py OUTC rushing_yards / receiving_yards)
primary target: RB rushing yards, WR receiving yards per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team |
   current baseline: his season-to-date mean yards | candidate: F5 v1 count (RB carries / WR targets = F2 v1 x F4 v1, re-fit per fold) x his season-to-date yards per
   carry / per target | metric: yards MAE, paired by slate | consumer: TD walls; F8 (0.1 DK per yard + 100-yard bonus).
NO TEST (declared): RB and TE receiving yards (F5 v1 targets = season-to-date, so the identity equals the baseline).  QB passing is not yet in the spine.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate per slice.  Rows with an undefined rate (no earlier carries / targets) dropped from both arms and counted.
   Script spine_yds.py.  Registered once, judged once.

## STAT SPINE - WALL 5 (F5 yards) - OUTCOME - Oct 3 2026 (proj/spine_yds_report.txt; dropped for undefined rate: RB 404, WR 472)
RB rushing yards: MAE 20.484 -> 20.350, cut +0.1397+-0.1038 (4/5) -> NOT SHOWN.   WR receiving yards: 21.571 -> 21.683, -0.1185+-0.0468 (0/5) -> NOT SHOWN (worse).
F5 v1 yards = his season-to-date mean yards.  Pattern across walls 3-5: volume terms earn (RB carries, WR targets); unshrunk efficiency rates (catch rate, yards per
   opportunity) add nothing over his own average.  Rate shrinkage stays a post-freeze challenger (listed before this wall ran) - not a rescue on these seasons.

## STAT SPINE - WALL 6 (F5 TDs) - REGISTRATION - Oct 3 2026 (reads: term_skill.py S04 construction; p.py OUTC TD / red-zone columns)
primary target: player TDs (rushing + receiving), RB / WR / TE, per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the
   team | current baseline: his season-to-date mean TDs | candidate: S04 - (TDs so far + kb x league rate) / (red-zone opportunities so far + kb) x his red-zone
   opportunities per game so far; kb (grid 2-80, by squared error) and league rate fit on training seasons; grouping player-season-team | metric: Poisson deviance per
   player-game (both forecasts floored at 0.01), paired by slate; reported: TD MAE, Brier on P(TD >= 1) = 1 - exp(-mu) | consumer: F8 (6 DK per TD).
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate per position on deviance.  EARNED -> S04 is F5 v1 TDs; else his season-to-date TDs.  First test of S04
   in TD units (its earlier closure was as an F8 increment).  Script spine_td.py.  Registered once, judged once.

## STAT SPINE - WALL 6 (F5 TDs) - OUTCOME - Oct 3 2026 (proj/spine_td_report.txt; tests 2020-21, 2023-25)
RB: deviance 0.9415 -> 0.7865, cut +0.16251+-0.01905 (5/5) *, kb 20-40; Brier P(TD>=1) 0.1716 -> 0.1631; MAE 0.3814 -> 0.3867 (MAE rewards the median, 0).
WR: 0.7642 -> 0.6715, +0.09497+-0.01269 (5/5) *, kb 10-40; Brier 0.1403 -> 0.1354; MAE 0.2888 -> 0.2941.
TE: 0.6703 -> 0.5542, +0.11933+-0.01537 (5/5) *, kb 20-40; Brier 0.1115 -> 0.1050; MAE 0.2168 -> 0.2209.
F5 v1 TDs = S04 (hierarchical TD rate x red-zone opportunities per game, kb and league rate fit on training seasons) for RB / WR / TE.

## LEDGER RESTORE - Oct 3 2026 (wc -l CHARTER.md 1091; grep of "^## " headings; ls: one copy, modified 18:50)
Between the 18:49 run (headings through STAT SPINE WALL 5 REGISTRATION at L1267) and the 18:50 append, CHARTER.md was replaced by a copy ending at RENAME REHASH
   (L1075-1078); the 18:50 block appended WALL 5 OUTCOME and WALL 6 REGISTRATION after it.  Restored verbatim from this session's heredocs, in original order, before those
   two entries: CONSUMPTION MAP; S CONSUMPTION + WALL RULE; TERM-SKILL LADDER; TERM SKILL STAGE 1 REGISTRATION / OUTCOME; STAGE 2 (P) S03 REGISTRATION; STAGE 2 (P) S03
   OUTCOME (first recorded here - its block never ran); FORECAST HIERARCHY + STAT-SPINE RULES; FUNNEL INDEX; STAT SPINE WALL 1-4 REGISTRATION / OUTCOME; WALL 5
   REGISTRATION.  Source of the overwrite: unknown (the stale copy ends at the entry written outside this session).

## LENS LADDER - governing workflow for every stubborn quantity - Oct 3 2026 (owner)
PRINCIPLE: when a target hits a ceiling, split it into level, share, rate, state and uncertainty, then attack only the piece that is still wrong.  Different quantities get
   different tools; no monolithic model.  Earlier discoveries are a library of lenses and decompositions, not features to stuff into one model.
RUNGS (in order, per quantity): 1 identity (exact count / rate decomposition) | 2 simplest baseline (season-to-date or league mean) | 3 shrinkage (partial pooling,
   n theta_own + k theta_population over n + k) | 4 recency (exponential weights / local filter) | 5 additive ML (Lasso / ridge as a skill detector, then distilled to a
   smaller structural form if one reproduces the gain) | 6 nonlinear (boosting / forest only if additive plateaus; a discovery lens, not a default producer) | 7 state split
   (transition / role state where the error remains) | 8 residual / local model (condition only where the miss remains) | 9 null + power (gain beyond search noise and
   detectable) | 10 promote or close (only the smallest earned form becomes the producer).
LENSES: level (absolute level even when rank is unchanged); share / composition (team total x share x efficiency); state / transition; residual (baseline removed first);
   tail (center / floor / ceiling / near-zero separately); natural experiment (causal claims only); null / twin (shuffled, reversed, mirrored, switched-off); resolution
   (can the instrument detect the effect before a null is read as "no effect").
DO NOT PAY (closed classes, not reopened): broad team / opponent feature soup; nearest-neighbour analogs; deeper interaction trees after the additive structure; raw pace /
   plays shifts; generic situation families; top-down group allocation; unshrunk individual efficiency rates; exotic tail models without selector exposure; vacancy
   corrections without a legal trigger.
RECONCILIATION with "registered once, judged once / first NO is the ceiling": a quantity's full ladder (its rungs and their order) is declared before its first rung runs;
   each rung is its own wall, and its baseline is the earned form so far.  For quantities whose earlier rungs are already seen (F2, F4, F5 counts, TDs), the remaining
   rungs run before the freeze only after the procedure harness (line 38) has measured the false-pass rate of a ladder of that length on that quantity's structure;
   otherwise they wait as challengers.  Rungs recorded as post-freeze challengers before their wall ran (rate shrinkage for receptions / yards) stay challengers.
LADDER STATE: F2 rungs 1-3 done (shrinkage earned), 5-6 closed by N01 / N02, open 4 / 7 / 9.  F3 rung 7 earned (T1).  F4 rungs 2 / 4 done (recency earned RB carry, WR, TE
   target), open 3 / 7 (role collapse R03 as state evidence); S01 / S02 are rung 5-6 challengers.  F5 counts rung 1 earned (RB carries, WR targets).  F5 receptions /
   yards rung 1 with raw rates not shown; rate shrinkage is a challenger.  F5 TDs rung 3 earned (S04), open 4 / 7 / 9.  F6 stat units and QB passing: ladder not started.
NEXT: line 38 procedure harness (rung 9 machinery) - it gates every remaining rung on a touched quantity.

## CHARTER APPEND INTEGRITY - Oct 3 2026 (after LEDGER RESTORE; owner review)
RULE: CHARTER.md is append-only.  proj/charter_ledger.json holds the line count and SHA-256 of the last accepted CHARTER; ledger.py check passes iff the file still begins
   with exactly those lines (appends allowed; lost or edited accepted lines fail).  ledger.py advance accepts the current file and refuses if check already fails.
   guard.py check 12 calls ledger.check (one source).  Every append block runs "python3 ledger.py check || exit 1" first and "python3 ledger.py advance" after guard passes.
   A deliberate correction is a new appended entry, never an edit of accepted lines.
TEST (this transaction): advance on the restored 1329-line CHARTER plus this entry; check must pass on CHARTER.md and fail on a truncated copy and on an edited copy.

## CHARTER APPEND INTEGRITY - OUTCOME - Oct 3 2026
ledger.py advance accepted 1336 lines; guard check 12 "1336 accepted lines intact"; check FAILED on a truncated copy (lines lost) and on an edited copy (accepted lines
   changed); passed on CHARTER.md.  Append blocks now start with ledger check and end with ledger advance.

## QB LADDER - declared before any QB rung runs - Oct 3 2026 (owner (b): QB passing before the freeze; LENS LADDER rules)
Q1 pass attempts: rung 1 identity F2 v1 team pass attempts x his season-to-date attempt share | 4 recency-weighted share | 7 state (starter change) | 9 null + power.
Q2 completions: rung 1 Q1 v1 x raw season completion rate | 3 shrunk completion rate | 9.
Q3 passing yards: rung 1 Q1 v1 x raw yards per attempt | 3 shrunk yards per attempt | 9.
Q4 passing TDs: rung 2 his season-to-date mean (baseline) | 3 hierarchical TD rate x red-zone attempts (S04 form) | 9.
Q5 interceptions: rung 2 season-to-date mean (baseline) | 3 shrunk interception rate x Q1 v1 | 9.
Q6 rushing: carries rung 1 F2 v1 team carries x QB carry share, 4 recency; yards / TDs as the RB walls - after Q1-Q5.
Each rung is its own wall; its baseline is the earned form so far (rung 2, his season-to-date mean, is the starting baseline for every quantity).

## STAT SPINE - QB Q1 RUNG 1 (pass attempts) - REGISTRATION - Oct 3 2026 (reads: wall 1 construction; p.py OUTC attempts)
primary target: QB pass attempts per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | current baseline: his
   season-to-date mean attempts | candidate: F2 v1 team attempts (shrunk, k re-fit per fold on training seasons) x his season-to-date attempt share (attempts / team
   attempts per game, mean over earlier games) | metric: attempts MAE, paired by slate | consumer: Q2 / Q3 / Q5, F8.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate.  EARNED -> identity is Q1 v1; else his season-to-date attempts.  Not identical to the baseline by
   construction (shrunk team level; per-game share mean).  Script spine_qb_att.py.  Registered once, judged once.

## STAT SPINE - QB Q1 RUNG 1 - OUTCOME - Oct 3 2026 (proj/spine_qb_att_report.txt; 1919 rows, tests 2020-21, 2023-25; part-time rows 173 of 2288)
QB attempts: MAE his season-to-date 7.8105 -> F2 v1 x attempt share 7.5994, cut +0.2228+-0.0563 (5/5) *, k 5-8 -> EARNED: Q1 v1 = F2 v1 team attempts x his season-to-date
   attempt share.  Starters (share >= .5, 1759 rows, reported): 7.6800 -> 7.4486, +0.2330+-0.0577 (5/5).

## STAT SPINE - QB Q1 RUNG 4 (recency share) - REGISTRATION - Oct 3 2026 (QB LADDER)
primary target: QB pass attempts per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | current baseline: Q1 v1
   (F2 v1 team attempts x season-to-date attempt share) | candidate: F2 v1 x recency-weighted attempt share, weight w^lag, w chosen on training seasons by MAE from
   {1.0, 0.9, 0.8, 0.7, 0.6, 0.5} (1.0 = baseline) | metric: attempts MAE, paired by slate | consumer: Q2 / Q3 / Q5, F8.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate.  EARNED -> recency share replaces the season share in Q1 v1; else Q1 v1 stands.  Script spine_qb_r4.py.

## STAT SPINE - QB Q1 RUNG 4 - OUTCOME - Oct 3 2026 (proj/spine_qb_r4_report.txt; 1919 rows)
QB attempts: MAE Q1 v1 (season share) 7.5994 -> recency share 7.3947, cut +0.1996+-0.0554 (4/5) *, w 0.5-0.7 -> EARNED: Q1 v1 = F2 v1 team attempts x recency-weighted
   attempt share.  Cumulative vs his season-to-date attempts: 7.81 -> 7.39 MAE.  The low w likely carries starter changes - checked at Q1 rung 7.

## STAT SPINE - QB Q2 / Q3 RUNG 1 (completions, passing yards) - REGISTRATION - Oct 3 2026 (QB LADDER; p.py OUTC completions / passing_yards)
Q2 primary target: QB completions per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | current baseline: his
   season-to-date mean completions | candidate: Q1 v1 attempts x his season-to-date completion rate (earlier completions / earlier attempts) | metric: completions MAE,
   paired by slate | consumer: yards / dependence, F8.
Q3 primary target: QB passing yards per game given he plays | same information time | baseline: his season-to-date mean passing yards | candidate: Q1 v1 attempts x his
   season-to-date yards per attempt | metric: yards MAE, paired by slate | consumer: F8 (0.04 DK per yard + 300-yard bonus).
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025; Q1 v1 (k, w) re-fit per fold.  GATE: passes_gate per quantity.  Rows with no earlier attempts dropped from both arms and
   counted.  Not identical to the baselines by construction (Q1 v1 differs from season attempts).  Rung 3 (shrunk rate) is declared next for both.  Script spine_qb_rate.py.

## STAT SPINE - QB Q2 / Q3 RUNG 1 - OUTCOME - Oct 3 2026 (proj/spine_qb_rate_report.txt; 1895 rows, 24 without earlier attempts dropped)
Q2 completions: MAE his season-to-date 5.5053 -> Q1 v1 x raw completion rate 5.2651, cut +0.2389+-0.0475 (5/5) * -> EARNED (Q2 v1).
Q3 passing yards: 66.9775 -> 64.5342, cut +2.4921+-0.4333 (5/5) * -> EARNED (Q3 v1 = Q1 v1 x raw yards per attempt).
Pattern: a volume x rate identity earns where its volume term earned materially (QB attempts); for WR (target gain -1.4%) it did not (walls 4-5).

## STAT SPINE - QB Q2 / Q3 RUNG 3 (shrunk rates) - REGISTRATION - Oct 3 2026 (QB LADDER)
primary target: QB completions; QB passing yards per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | current
   baseline: Q2 v1 / Q3 v1 (Q1 v1 x raw season-to-date rate) | candidate: Q1 v1 x shrunk rate = (earlier completions or yards + k x training league rate) / (earlier
   attempts + k), k chosen on training seasons by MAE from {0, 25, 50, 100, 200, 400, 800} attempts (0 = baseline) | metric: completions MAE; yards MAE, paired by slate |
   consumer: F8.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025; Q1 v1 (k, w) re-fit per fold.  GATE: passes_gate per quantity.  EARNED -> shrunk rate replaces the raw rate in Q2 / Q3 v1.
   Script spine_qb_shr.py.

## STAT SPINE - QB Q2 / Q3 RUNG 3 - OUTCOME - Oct 3 2026 (proj/spine_qb_shr_report.txt; 1895 rows)
Q2 completions: MAE raw rate 5.2651 -> shrunk 5.1997, cut +0.0671+-0.0219 (5/5) *, k 200-400 attempts -> EARNED: Q2 v1 = Q1 v1 x shrunk completion rate.
Q3 passing yards: 64.5342 -> 63.2734, cut +1.2748+-0.3813 (5/5) *, k 100-200 -> EARNED: Q3 v1 = Q1 v1 x shrunk yards per attempt.
Cumulative vs his season-to-date mean: completions 5.51 -> 5.20, yards 66.98 -> 63.27 (about -5.5% each).  Rate shrinkage works for QB; for RB / WR / TE receptions and
   yards it remains a post-freeze challenger (recorded before wall 5 ran) - not re-run on these seasons.

## STAT SPINE - QB Q4 / Q5 RUNG 3 (passing TDs, interceptions) - REGISTRATION - Oct 3 2026 (QB LADDER; p.py OUTC passing_tds, redzone_attempts, passing_interceptions)
Q4 primary target: QB passing TDs per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | current baseline: his
   season-to-date mean passing TDs | candidate: (passing TDs so far + kb x training league rate) / (red-zone attempts so far + kb) x his red-zone attempts per game so far,
   kb from 2-80 by squared error | metric: Poisson deviance (floor 0.01), paired by slate; reported: MAE, Brier P(TD >= 1) | consumer: F8 (4 DK per passing TD).
Q5 primary target: interceptions per game given he plays | same information time | baseline: his season-to-date mean interceptions | candidate: Q1 v1 attempts x (ints so
   far + k x training league rate) / (attempts so far + k), k from {0, 25, 50, 100, 200, 400, 800} | metric: Poisson deviance (floor 0.01), paired by slate; MAE reported |
   consumer: F8 (-1 DK per interception).
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025; Q1 v1 re-fit per fold.  GATE: passes_gate per quantity.  Script spine_qb_td.py.

## STAT SPINE - QB Q4 / Q5 RUNG 3 - OUTCOME - Oct 3 2026 (proj/spine_qb_td_report.txt; 1919 rows)
Q4 passing TDs (mean 1.395): deviance his season-to-date 1.2517 -> hierarchical rate x red-zone attempts 1.1613, cut +0.08736+-0.03023 (4/5) *, kb 20-40; MAE 0.9169 ->
   0.8975; Brier P(TD >= 1) 0.1840 -> 0.1781 -> EARNED: Q4 v1.
Q5 interceptions (mean 0.656): deviance 1.4253 -> Q1 v1 x shrunk interception rate 1.1207, cut +0.30819+-0.04433 (5/5) *; MAE 0.6934 -> 0.6686 -> EARNED: Q5 v1.
   LIMITATION: k = 800 (the grid's top) in 4 of 5 seasons - the optimum may lie beyond the grid; a wider grid is a post-freeze challenger, not re-run here.
QB PASSING v1 complete: Q1 F2 v1 x recency share; Q2 / Q3 Q1 v1 x shrunk rate; Q4 hierarchical TD rate x red-zone attempts; Q5 Q1 v1 x shrunk interception rate.

## STAT SPINE - QB Q6 RUNG 1 (QB carries) - REGISTRATION - Oct 3 2026 (QB LADDER; p.py OUTC carries / carry_share)
primary target: QB carries per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | current baseline: his
   season-to-date mean carries | candidate: F2 v1 team carries (shrunk, k re-fit per fold) x his season-to-date carry share | metric: carries MAE, paired by slate |
   consumer: QB rushing yards / TDs, F8.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate.  EARNED -> identity is Q6 v1 carries; else his season-to-date carries.  Rung 4 (recency share) declared
   next.  Script spine_qb_rush.py.

## STAT SPINE - QB Q6 RUNG 1 - OUTCOME - Oct 3 2026 (proj/spine_qb_rush_report.txt; 1919 rows, mean 3.58 carries)
QB carries: MAE his season-to-date 1.8266 -> F2 v1 x carry share 1.8180, cut +0.0094+-0.0095 (4/5) -> NOT SHOWN: Q6 v1 carries = his season-to-date mean.  First QB term
   where team volume x share does not help (scramble-dominated carries).

## STAT SPINE - QB Q6 RUNG 4 (carries, recency share) + QB RUSH TD RUNG 3 - REGISTRATION - Oct 3 2026 (QB LADDER; p.py OUTC rushing_tds / redzone_carries)
Q6 carries rung 4: target QB carries per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | baseline: Q6 v1 (his
   season-to-date carries) | candidate: F2 v1 team carries x recency-weighted carry share, w by MAE on training seasons from {1.0 ... 0.5} | metric: carries MAE, paired by
   slate | consumer: QB rushing yards, F8.
QB rushing TDs rung 3: target QB rushing TDs per game given he plays | same information time | baseline: his season-to-date mean rushing TDs | candidate: (rush TDs so far
   + kb x training league rate) / (red-zone carries so far + kb) x red-zone carries per game so far, kb from 2-80 by squared error | metric: Poisson deviance (floor
   0.01), paired by slate; MAE, Brier reported | consumer: F8.
NO TEST: QB rushing yards rung 1 while Q6 v1 carries = season-to-date (carries x his yards per carry = his season-to-date yards by construction); registered only if rung 4
   earns.  TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate per quantity.  Script spine_qb_rush2.py.

## STAT SPINE - QB Q6 RUNG 4 + QB RUSH TD RUNG 3 - OUTCOME - Oct 3 2026 (proj/spine_qb_rush2_report.txt; 1919 rows)
Q6 carries rung 4: MAE 1.8266 -> 1.8148, cut +0.01297+-0.01097 (4/5), w 0.8-0.9 -> NOT SHOWN: Q6 v1 carries = season-to-date.  QB rushing yards: NO TEST as declared ->
   v1 = his season-to-date mean rushing yards.
QB rushing TDs rung 3 (mean 0.179): deviance 0.7651 -> 0.6532, cut +0.11673+-0.02356 (5/5) *, kb 40-80; MAE 0.2669 -> 0.2784; Brier 0.1293 -> 0.1224 -> EARNED: v1 =
   hierarchical rush-TD rate x red-zone carries.  LIMITATION: kb = 80 (grid top) in 2 of 5 seasons.
PATTERN: TD terms earn at every position (RB, WR, TE, QB passing, QB rushing); volume terms earn where team volume drives the opportunity, not for scramble-driven QB carries.

## STAT SPINE - QB Q1 RUNG 7 (state split) - REGISTRATION - Oct 3 2026 (QB LADDER)
primary target: QB pass attempts per game given he plays | information time: through week N-1, weeks 4-16, >= 3 earlier played games on the team | current baseline: Q1 v1
   (F2 v1 x recency share, one w) | candidate: the same with w chosen per state on training seasons - state 1: he played the team's previous game with attempt share >= .5;
   state 0: otherwise (new / returning starter, backup, gap) | metric: attempts MAE, paired by slate; reported: Q1 v1 MAE by state, rows per state | consumer: Q2 / Q3 /
   Q5, F8.
TESTS: walk-forward 2020, 2021, 2023, 2024, 2025.  GATE: passes_gate.  Equal w in both states makes the gain 0 by construction.  Script spine_qb_state.py.

## STAT SPINE - QB Q1 RUNG 7 - OUTCOME - Oct 3 2026 (proj/spine_qb_state_report.txt; 1919 rows; state 1 1665, state 0 254)
State-split w (state 0 mostly 1.0, state 1 0.5): MAE 7.3947 -> 7.3803, cut +0.0200+-0.0294 (4/5) -> NOT SHOWN: Q1 v1 stands.  Q1 v1 MAE state 1 7.1062, state 0 9.2856 -
   the remaining attempts error sits at new / returning starters, backups and gaps; no rung 8 was declared for Q1, so this is recorded as the location of the residual.
QB LADDER: every declared rung but 9 (procedure harness) is complete.

## STAT SPINE CONSOLIDATION (line 39a) - REGISTRATION - Oct 3 2026 (reads: spine_f2 / f4 / f5 / rec / yds / td, spine_qb_* procedures)
spine.py is the single source of every earned spine v1 term and its baseline (history mode; coming-week issue mode is 39b).  It writes proj/spine_rows.csv.gz (term,
   position, season, week, key, y, base, v1, loss) for the procedure harness (line 38).  ACCEPTANCE: spine.py reproduces each recorded figure at its recorded precision -
   F2 targets 6.237 / 6.022, carries 6.192 / 5.994, attempts 6.527 / 6.283; F4 RB carry 0.10978 / 0.10491, RB target 0.03852 / 0.03852, WR 0.05468 / 0.05401, TE 0.03930 /
   0.03911; F5 RB carries 3.4463 / 3.3293, WR targets 1.9049 / 1.8788, RB targets 1.3061 / 1.3061, TE targets 1.3393 / 1.3393; TD deviance RB 0.9415 / 0.7865, WR 0.7642 /
   0.6715, TE 0.6703 / 0.5542; QB Q1 7.8105 / 7.3947, Q2 5.5053 / 5.1997, Q3 66.9775 / 63.2734, Q4 1.2517 / 1.1613, Q5 1.4253 / 1.1207, QB rush TD 0.7651 / 0.6532.
   Any mismatch -> spine.py not accepted; the wall scripts stay; the mismatch is located before anything else.

## STAT SPINE CONSOLIDATION (line 39a) - OUTCOME - Oct 3 2026 (proj/spine_report.txt; proj/spine_rows.csv.gz 84333 rows, 14 terms)
SELF-CHECK 20 of 20 recorded figures reproduced at recorded precision -> ACCEPTED: spine.py is the single source of spine v1 (history mode).

## PROCEDURE HARNESS (line 38; rung 9 of every ladder) - REGISTRATION - Oct 3 2026 (reads: proj/spine_rows.csv.gz; p.paired_by_slate / passes_gate; pgate_audit tau/sigma)
SCOPE: every spine term whose v1 differs from its baseline (17 of 20; RB target share, RB / TE targets keep the baseline).  Per term: observed paired per-slate loss gain
   (baseline - v1) and gate; tau/sigma (season-effect sd / within-season slate sd); NULL A - per-row random swap of baseline and v1, 1000 draws, gate false-pass rate;
   NULL B - observed gain removed, season blocks sign-flipped (keeps the term's own season heterogeneity), 1000 draws, false-pass rate; POWER - null-B structure plus 25 /
   50 / 100% of the observed gain; LADDER - 1 - (1 - FP_B)^L, L = rungs run on the quantity (Q1 3; Q2, Q3 2; all others 1).
HARNESS PASS: observed gate passes AND FP_B <= .05 AND ladder rate <= .10.  CONSEQUENCE (fixed now): a term failing the harness enters the freeze at its baseline.
Script harness.py, report proj/harness_report.txt.  Seeds fixed.  Registered once, judged once.

## PROCEDURE HARNESS (line 38) - OUTCOME - Oct 3 2026 (proj/harness_report.txt; 1000 draws; 65 slates per term)
NULL A false-pass 0.015-0.038 (consistent with gatesim2's 2%).  NULL B: 0.000 for 13 terms (tau/sigma 0.00-0.04); Q1 attempts 0.034 (ladder L 3 -> 0.099, passes at the edge);
   Q4 passing TDs 0.048 (passes; power at the observed gain 0.67 - resolution-limited); WR TDs 0.067 (tau/sigma 0.23) and Q5 interceptions 0.066 (tau/sigma 0.26) -> HARNESS
   FAIL: both enter the freeze at their baseline (registered consequence).  Power at the observed gain 1.00 for most terms; TE target share 0.86.
LIMITATION: FP_B measures the gate's false-pass rate at a term's season heterogeneity regardless of margin (WR TDs 7.5 s.e., Q5 7.0 s.e.).  A margin-aware harness is a
   separately registered v2; WR TDs and Q5 return only as challengers with their own clock.
SPINE v1 FOR THE FREEZE: F2 shrunk team targets / carries / attempts; F4 recency share RB carry (w 0.6), WR target (0.8), TE target (0.9), RB target season-to-date; F5 RB
   carries and WR targets = F2 x F4; RB / TE targets, receptions, yards season-to-date; TDs hierarchical rate x red-zone opportunities for RB and TE, WR season-to-date;
   QB Q1 F2 x recency attempt share; Q2 / Q3 Q1 x shrunk rate; Q4 hierarchical passing-TD rate; Q5 season-to-date; QB carries / rushing yards season-to-date; QB rushing TDs
   hierarchical rate.  Next: spine.py coming-week issue mode (line 39b), then F6, F7, freeze.

## STAT SPINE COMING-WEEK MODE (line 39b) - REGISTRATION - Oct 3 2026 (reads: p.candidates, p.frame source; team_game 2026: weeks 1-3 played, week 4 unplayed)
spine.py rebuilt as frames / forecast / history / issue on one code path.  Issue mode (python3 spine.py SEASON WEEK): pool = p.candidates for week N at QB / RB / WR / TE;
   history through week N-1 only; each candidate gets a week-N row with empty outcomes (as p.frame); every choice (k, w, rate k, kb) fit on seasons <= FROZEN_THRU;
   eligible = >= 3 earlier played games on the team this season (others unprojected, counted, never filled); output uses the freeze forms (WR TDs, QB interceptions at
   season-to-date - HARNESS OUTCOME); writes proj/spine_week_{SEASON}_w{WEEK}.csv.
ACCEPTANCE: (1) history mode still reproduces the 20 recorded figures; (2) issue-path check - the coming-week path for 2025 week 10 with choices fit on seasons < 2025 equals
   the history rows for that week, every term, max |difference| < 1e-9, rows compared > 0.  Then a DRY RUN for 2026 week 4 (labelled not prospective; the freeze follows
   F6 / F7).  Any failure -> the rebuild is not accepted.
NOTE (39b, same day): first run crashed before any check - the padding column was named "pad", which is the pandas DataFrame.pad method (B.pad returned the method).
   Mechanical; nothing computed or judged.  The crash had already overwritten the accepted 39a spine.py; spine_rows.csv.gz untouched.  Rewritten with column is_pad;
   issue output adds unprojected candidates with their reason and a per-position path label.  Acceptance unchanged.
ORDER (owner review): live-safe issue mode -> F6 marginal uncertainty per native stat term (team volume, share, count residuals, TD dispersion) -> F6 dependence only after
   the marginals pass -> F7 native evaluator -> stat composition -> F8 vs Y -> price / lineup.  F2 / F4 / F5 v1 are fixed inputs; only a registered challenger replaces them.
NOTE (39b, second run): history self-check 20 / 20; issue-path check 0 / 20 - the issue truncation kept every season <= FROZEN_THRU, so for S = 2025 (= FROZEN_THRU) it kept
   all of 2025 beside the padded week-10 rows.  Mechanical: truncation corrected to (season < S and season <= FROZEN_THRU) or (season == S and week < N); identical for
   S = 2026.  Acceptance unchanged; re-run.

## STAT SPINE COMING-WEEK MODE (line 39b) - OUTCOME - Oct 3 2026 (proj/spine_report.txt; proj/spine_week_2026_w4.csv)
History self-check 20 / 20; issue-path check 20 / 20 terms equal (2025 week 10, choices fit on seasons < 2025, max |diff| 0.00e+00) -> ACCEPTED: spine.py issues week N from
   results through N-1 on the scored code path.  DRY RUN 2026 week 4 (not prospective): candidates 517 (QB 89, RB 112, WR 193, TE 123), projected 329 (QB 26, RB 77, WR 136,
   TE 90), unprojected 188 with reason (fewer than 3 earlier played games on the team); 32 teams.  Coverage is thinnest at week 4 by construction; 6 teams' passers
   unprojected (new / changed starters - the Q1 state-0 residual).  A short-history branch is a later, separate wall.

## F6 TEAM VOLUME LADDER - declared before any rung runs - Oct 3 2026 (owner order: F6 marginals per native term)
rung 2 Poisson around the F2 v1 mean | rung 3 negative binomial, one dispersion fit on training seasons | rung 7 dispersion by state | rung 9 harness.

## F6 TEAM VOLUME RUNG 3 (dispersion) - REGISTRATION - Oct 3 2026 (reads: proj/spine_rows.csv.gz F2 rows)
primary target: calibrated predictive distribution of team targets, carries, pass attempts per team-game | information time: through week N-1 (F2 v1 means, walk-forward) |
   current baseline: Poisson(F2 v1 mean) | candidate: negative binomial with that mean and dispersion r chosen on training seasons by maximum likelihood from a log grid
   1 .. 10^4 plus the Poisson limit | metric: log score (negative log-likelihood per team-game), paired by slate; reported: 80% central-interval coverage, randomized PIT
   mean / sd for both arms | consumer: F6 composition.
TESTS: 2021, 2023, 2024, 2025 (spine_rows starts 2020; 2020 trains only).  GATE: passes_gate per count.  Script f6_team.py.  Registered once, judged once.

## F6 TEAM VOLUME RUNG 3 - OUTCOME - Oct 3 2026 (proj/f6_team_report.txt; tests 2021, 2023-25; 1536 team-games each)
targets: log score Poisson 3.5015 -> NB 3.4143, gain +0.08632+-0.01511 (4/4) *, r 32-40; 80% coverage 70.6% -> 84.6%; PIT sd 0.329 -> 0.281.
carries: 3.5673 -> 3.4080, +0.15932+-0.01944 (4/4) *, r 20-25; coverage 65.3% -> 82.2%; PIT sd 0.348 -> 0.291.
attempts: 3.5567 -> 3.4576, +0.09814+-0.01538 (4/4) *, r 32-40; coverage 69.9% -> 84.9%; PIT sd 0.332 -> 0.282.
F6 team v1 = negative binomial around the F2 v1 mean, r fit on training seasons.  RESIDUAL: coverage slightly high (82-85% vs 80%); F2 v1 mean above actual by 0.56 targets
   and 0.63 attempts (league mean from earlier, higher-passing seasons) - an F2 challenger, F2 being a fixed input.
RUNG 7 (dispersion by state): its state was not specified at declaration; defining it after rung 3 would be post-hoc -> challenger.

## F6 SHARE LADDER - declared before any rung runs - Oct 3 2026
rung 2 binomial(team total, F4 v1 share) | rung 3 beta-binomial, one precision phi fit on training seasons | rung 9 harness.

## F6 SHARE RUNG 3 (overdispersion) - REGISTRATION - Oct 3 2026 (reads: proj/spine_rows.csv.gz F4 rows; p.load counts)
primary target: player count given the realized team total - RB carries of team carries; RB / WR / TE targets of team targets | information time: F4 v1 share forecast
   (walk-forward) | current baseline: binomial(team total, F4 v1 share) | candidate: beta-binomial with that mean and precision phi chosen on training seasons by maximum
   likelihood from a log grid 1 .. 10^4 plus the binomial limit | metric: log score per player-game, paired by slate; reported: 80% coverage, randomized PIT | consumer:
   F6 composition (count = team NB x share).
TESTS: 2021, 2023, 2024, 2025.  GATE: passes_gate per slice.  Shares clipped to [1e-4, 1 - 1e-4].  Script f6_share.py.  Registered once, judged once.

## F6 SHARE RUNG 3 - OUTCOME - Oct 3 2026 (proj/f6_share_report.txt; tests 2021, 2023-25)
RB carry share: log score binomial 3.1725 -> beta-binomial 2.4591, gain +0.73409+-0.06389 (4/4) *, phi 7.9-10; coverage 67.3% -> 86.8%; PIT sd 0.359 -> 0.283.
RB target share: 1.7949 -> 1.6991, +0.09769+-0.01463 (4/4) *, phi 50-79.   WR target share: 2.1684 -> 2.0330, +0.13807+-0.01664 (4/4) *, phi 40.
TE target share: 1.7782 -> 1.7131, +0.06575+-0.00951 (4/4) *, phi 79.
F6 share v1 = beta-binomial around the F4 v1 share, phi fit on training seasons.  Coverage 87-89% is the expected inclusive-interval excess for small discrete counts;
   PIT means 0.52-0.54 (outcomes slightly above the forecast share) - an F4 level challenger.

## F6 COUNT LADDER - declared before any rung runs - Oct 3 2026
rung 2 Poisson around the F5 v1 mean | rung 3 negative binomial, one dispersion per slice fit on training seasons | rung 9 harness.

## F6 COUNT RUNG 3 (dispersion) - REGISTRATION - Oct 3 2026 (reads: proj/spine_rows.csv.gz F5 count and Q1 / Q2 rows)
primary target: calibrated predictive distribution of RB carries, RB / WR / TE targets, QB attempts, QB completions per game given he plays | information time: F5 v1 means
   (walk-forward) | current baseline: Poisson(F5 v1 mean) | candidate: negative binomial with that mean, r chosen on training seasons by maximum likelihood from a log grid
   1 .. 10^4 plus the Poisson limit | metric: log score, paired by slate; reported: 80% coverage, randomized PIT | consumer: F6 composition, F8.
NOT IN THIS RUNG: QB passing yards (own rung); receptions / yards / QB rushing (season-to-date v1 forms join spine.py history rows before their rungs).
TESTS: 2021, 2023, 2024, 2025.  GATE: passes_gate per slice.  Script f6_count.py.  Registered once, judged once.

## F6 COUNT RUNG 3 - OUTCOME - Oct 3 2026 (proj/f6_count_report.txt; tests 2021, 2023-25; log score paired by slate)
EARNED 6 / 6, 4 / 4 seasons each: RB carries +0.36014+-0.03041 (r 2.0-2.5; cover 66.8 -> 88.6%); RB targets +0.05096+-0.00663 (r 3.2-4.0; 83.7 -> 89.0%);
   WR targets +0.05752+-0.00681 (r 5.0-6.3; 79.3 -> 87.7%); TE targets +0.03145+-0.00439 (r 6.3-7.9; 83.5 -> 87.4%); QB attempts +0.71776+-0.07973 (r 7.9-10;
   62.2 -> 86.5%); QB completions +0.30852+-0.04025 (r 10-12.6; 66.2 -> 84.9%).
F6 COUNT v1: NB around the F5 v1 mean, r per slice fit on training seasons.
CHALLENGERS (own clock, not v1): PIT mean RB carries 0.537, TE targets 0.540 -> joins the F4 level-shift challenger; QB attempts PIT sd 0.260 (< 0.289) -> starter /
   backup mixture, joins the Q1 state-0 residual challenger.

## F6 TD LADDER - declared Oct 3 2026, before any rung runs
Quantities: F5 TDs RB / TE (hierarchical v1), F5 TDs WR (freeze form = baseline), Q4 passing TDs (hierarchical v1), Q5 interceptions (freeze form = baseline),
   QB rushing TDs (hierarchical v1).  Rung 2: Poisson around the freeze-form mean.  Rung 3: NB dispersion, r per slice on training seasons.  Rung 9: harness.
   No other rung is declared; any other is a challenger.  Mean = the freeze form: v1 where v1 entered the freeze, base for WR TDs and Q5.
## F6 TD RUNG 3 - REGISTRATION - Oct 3 2026
Candidate NB vs baseline Poisson, same mean.  Metric: log score paired by slate; tests 2021, 2023-25; gate p.passes_gate.  Reported: coverage 80%, randomized PIT
   mean / sd.  A slice failing the gate keeps Poisson (a tie at low means is the expected NO, not a mechanical bug).  Consumer: F7 native scorer, F8 composition.
   Reduces: F5 TD predictive-interval uncertainty.
NOTE (F6 TD RUNG 3, before run): freeze-form mean per slice = v1 for F5 TDs RB / TE, Q4 passing TDs, QB rushing TDs; base for F5 TDs WR (base = v1 on 18.8% of rows) and
   Q5 interceptions (1.3%).  Seasons 2020-21, 2023-25; r fit on seasons before each test season (f6_count.py pattern).  Poisson calibration reported first.
QUEUE (reviewer, Oct 3 2026): 1 F6 count (done) -> 2 remaining F6 marginals (TDs, receptions, yards, QB rush) -> 3 F6 MARGINAL PROCEDURE HARNESS (only harness-safe
   distributions become F6 v1) -> 4 F6 dependence, null = independent calibrated marginals, structural pairs first -> 5 dependence harness -> 6 F7 native evaluator
   (marginal + joint calibration) -> 7 historical stat composition -> 8 F8 mechanical DK transform -> 9 F8 vs frozen Y -> 10 freeze v1; the stat-spine prospective clock starts
   at the next entirely untouched week (week 5 if frozen before its first game), separate from the DK track's week-4 clock -> 11 challengers -> 12 F9.  Deferred until 11:
   S01 / S02, rate shrinkage, F2 level bias, F4 PIT level, short history, margin-aware harness, Q5 wider k, opponent / slot context, P / Y unification, price.

## F6 TD RUNG 3 - OUTCOME - Oct 3 2026 (proj/f6_td_report.txt; tests 2021, 2023-25)
Poisson calibration first (PIT mean / sd; uniform 0.500 / 0.289): RB 0.509 / 0.295, WR 0.510 / 0.298, TE 0.504 / 0.295, Q4 0.518 / 0.292, Q5 0.511 / 0.304, QB rush TD
   0.483 / 0.288.  NB vs Poisson: RB -0.00082+-0.00065 (1/4), WR +0.00119+-0.00080 (3/4), TE +0.00011+-0.00026 (3/4), Q4 0 (r inf every season), QB rush TD
   +0.00091+-0.00066 (2/4) -> NOT SHOWN, Poisson is F6 TD v1 for these five.  Q5 interceptions +0.01242+-0.00361 (4/4) -> EARNED, NB (r 2.5-5.0); NB PIT mean 0.533 vs
   Poisson 0.511 - for the F6 marginal procedure harness to adjudicate.  All F6 v1 choices remain pending that harness.
NOTES: 80% coverage (90-96%) is uninformative at means 0.13-1.4 (discrete interval) - F7 scores low-mean counts by log score and randomized PIT, not coverage.
   QB rushing TD PIT mean 0.483 (mu 0.197 vs y 0.169) -> deferred mean challenger.

## SPINE ROWS EXTENSION (line 39c) - REGISTRATION - Oct 3 2026
spine.py history() adds rows for v1 terms the issue path already emits: F5 receptions / receiving yards / rushing yards (RB, WR, TE) and QB carries / QB rushing yards,
   v1 = base = season-to-date (NO TEST on the mean; rows exist to feed F6).  Issue-path MAP extended to these terms.  ACCEPTED iff self-check 20 / 20 unchanged and
   issue-path check equal on every MAP term.  Reduces: none at F5 (no mean change); unblocks F6 marginals for receptions / yards / QB rushing.
## SPINE ROWS EXTENSION (line 39c) - OUTCOME - Oct 3 2026: ACCEPTED.  spine_rows 145168 rows / 19 terms; self-check 20 / 20; issue-path 31 / 31 equal (11 new, max |diff| 0).
   Shape (y mean / var / share 0 / share < 0): receptions RB 1.614 / 3.377 / .364 / 0, TE 1.776 / 4.568 / .377 / 0, WR 2.532 / 6.622 / .277 / 0; QB carries 3.583 / 9.100 /
   .117 / 0; receiving yards RB 12.08 / .375 / .025, TE 18.67 / .381 / .003, WR 31.97 / .279 / .006; rushing yards RB 33.32 / .198 / .015, WR .924 / .885, TE .290 / .975;
   QB rushing yards 16.09 / .150 / .102.

## F6 RECEPTIONS / QB CARRIES LADDER - declared Oct 3 2026: rung 2 Poisson around the frozen mean (v1 = season-to-date); rung 3 NB, r per slice on earlier seasons;
   rung 9 harness.  Conditioning on targets is dependence (queue step 4), not this ladder.
## F6 YARDS LADDER - declared Oct 3 2026 (receiving yards RB / WR / TE, rushing yards RB / WR / TE, QB rushing yards): rung 2 Normal(frozen mean, constant sigma per
   slice, earlier seasons); rung 3 Normal with variance = phi x max(mean, 1); rung 3z zero-hurdle (P(0) per slice x positive part of the rung 2-3 winner) runs ONLY IF that
   winner's PIT mass in the lowest decile lies outside 0.07-0.13; rung 9 harness.  Metric: log density at integer y, paired by slate; PIT and 80% coverage reported.
## F6 RECEPTIONS / QB CARRIES RUNG 3 - REGISTRATION: NB vs Poisson, same mean; tests 2021, 2023-25; gate p.passes_gate; failing slice keeps Poisson.
   Consumer F7, F8.  Reduces: F5 receptions / QB carries predictive-interval uncertainty.

## F6 RECEPTIONS / QB CARRIES RUNG 3 - OUTCOME - Oct 3 2026 (proj/f6_rec_report.txt): EARNED 4 / 4, each 4 / 4 seasons.  RB +0.03659+-0.00509 (r 3.2-4.0), WR
   +0.02672+-0.00512 (5.0-6.3), TE +0.02057+-0.00321 (6.3-7.9), QB carries +0.05350+-0.01236 (4.0-5.0).  Poisson PIT sd 0.314-0.323 -> NB 0.283-0.299.  NB is F6 v1
   pending the harness.  TE PIT mean 0.533 (mu 1.670 vs y 1.796) -> deferred F4 / F5 level challenger.
## F6 YARDS RUNGS 2-3 - REGISTRATION - Oct 3 2026: rung 2 Normal(mean, sigma = RMS residual on earlier seasons) vs rung 3 Normal(mean, phi x max(mean, 1)), phi = mean
   (y - mean)^2 / max(mean, 1) on earlier seasons.  Mean = v1 (season-to-date).  Gain = rung 2 minus rung 3 negative log density, paired by slate; tests 2021, 2023-25.
   Winner = rung 3 iff gate.  Reported: 80% coverage, PIT mean / sd, PIT mass in lowest / highest decile; rung 3z registered to run iff the winner's lowest-decile mass is
   outside 0.07-0.13.

## F6 YARDS RUNGS 2-3 - OUTCOME - Oct 3 2026 (proj/f6_yds_report.txt): rung 3 (var = phi x mean) EARNED for receiving yards RB +0.06931+-0.03058 (3/4), TE
   +0.22305+-0.02305 (4/4), rushing yards WR +0.22017+-0.02618 (4/4), TE +0.84542+-0.24893 (3/4), QB +0.09005+-0.01963 (4/4); rung 2 kept for rushing yards RB
   -0.01065+-0.05619 (2/4) and receiving yards WR +0.04010+-0.02132 (3/4, fails 2 se).  Winner lowest-decile PIT mass 0.001-0.062 -> rung 3z condition met on all 7.
NOTE (3z, before run): mechanical reading of "P(0) per slice x positive part of the rung 2-3 winner": p0 = share of y == 0 per slice on earlier seasons; non-zero part
   (y != 0; negative yards stay continuous) = the winner's form with mean m = mu / (1 - p0) (frozen mean preserved) and its sigma or phi refit on y != 0 rows of earlier
   seasons.  Score: -log p0 at 0, else -log(1 - p0) - log N(y; m, s) (unit-bin convention of rungs 2-3).  Gain = winner minus hurdle, paired by slate; gate; PIT randomized
   at 0.  A player-level P(0) is not this rung (challenger).

## F6 YARDS RUNG 3z - OUTCOME - Oct 3 2026 (proj/f6_hurdle_report.txt): hurdle EARNED 7 / 7, each 4 / 4: receiving yards RB +0.59448+-0.02597, WR +0.59051+-0.02116,
   TE +0.57778+-0.01982; rushing yards RB +0.29021+-0.01712, WR +1.77275+-0.03472, TE +1.42638+-0.27529; QB rushing yards +0.05995+-0.01959.  Hurdle is F6 yards v1
   pending the harness.  Residual: PIT sd 0.193-0.217 and lowest-decile mass 0.003-0.010 for RB / WR / TE receiving, RB rushing, QB rushing - the Normal non-zero part
   puts excess mass below 0 (zeros land above F_below), spread too wide; PIT mean 0.511-0.576.  TE rushing m up to 1651 (mu / (1 - 0.975)).  Non-zero-part shape and
   player-level P(0) -> challengers (outside the declared ladder).
## F6 Q3 PASSING YARDS - REGISTRATION - Oct 3 2026: the F6 YARDS LADDER applied to Q3 passing yards (mean = v1, Q1 x shrunk rate): rung 2 vs rung 3 as registered for yards;
   rung 3z (as in NOTE (3z, before run)) runs iff the winner's lowest-decile PIT mass is outside 0.07-0.13.  Tests 2021, 2023-25.  Consumer F7, F8.

## F6 Q3 PASSING YARDS - OUTCOME - Oct 3 2026 (proj/f6_q3_report.txt): rung 3 -0.14872+-0.02786 (0/4) -> rung 2 (constant sigma) is F6 Q3 v1 pending the harness.
   Rung 2 PIT mean / sd 0.475 / 0.284, in [.1,.9] 81.1%, lowest-decile mass 0.110 -> 3z not triggered.  PIT mean 0.475 -> deferred Q3 mean challenger.
   F6 marginals complete for every spine term; next: F6 MARGINAL PROCEDURE HARNESS (ladder L: yards slices 2, every other slice 1).

## F6 MARGINAL PROCEDURE HARNESS (rung 9 of every F6 ladder) - REGISTRATION - Oct 3 2026
Same procedure and pass rule as line 38 (observed gate AND FP null B <= .05 AND ladder 1-(1-FP_B)^L <= .10; 1000 draws; seed 20261003), applied to per-row paired log
   scores (l_base = baseline distribution, l_cand = candidate) persisted by f6_team / f6_share / f6_count / f6_td / f6_rec / f6_yds / f6_hurdle (proj/f6rows_*.csv.gz;
   mechanical: the scripts gain a row dump only, their reports must reproduce byte-identical).  L = 2 for yards stages (rung3, 3z), 1 otherwise.  Consequence: a failing
   stage enters F6 v1 at its baseline; a 3z whose rung3 predecessor fails enters at rung 2 (a rung-2 hurdle is a challenger).  harness.py spine mode must reproduce
   proj/harness_report.txt byte-identical.  Reduces: false promotion of F6 distributions into the freeze.
NOTE (F6 MARGINAL PROCEDURE HARNESS, before run): first attempt wrote nothing (f6_yds.py anchor line continues past paired_by_slate; insert now goes after the full line).
   Naming per the established taxonomy, superseding the registration's shorthand: stage labels "negative binomial" (f6_team, f6_count, f6_td, f6_rec), "beta-binomial"
   (f6_share), "rung 3 variance = phi x max(mean, 1)" (f6_yds), "rung 3z zero-hurdle" (f6_hurdle); row files proj/f6_rows_<team|share|count|td|rec|yds|hurdle>.csv.gz;
   ladder L = 2 for the two yards stages, 1 otherwise.  Procedure and pass rule unchanged.
NOTE (F6 MARGINAL PROCEDURE HARNESS, second attempt): the 7 F6 scripts reproduced their reports byte-identical; harness_report.txt DIFFERS because the reference copy was
   the line 38 run on 84333 spine rows and spine_rows is now 145168 rows (line 39c) - not a like-for-like check (acceptance-design error).  Corrected check: original
   harness.py, reconstructed by reversing the four anchored replacements, and the patched harness.py in spine mode, both on the current spine_rows, must write
   byte-identical reports; else harness.py is restored to the original and the run stops.

## F6 MARGINAL PROCEDURE HARNESS - OUTCOME - Oct 3 2026 (proj/harness_f6_report.txt; 52 slates, tests 2021, 2023-25; spine-mode harness reproduced byte-identical on 145168 rows)
HARNESS PASS: negative binomial for F2 team targets, F2 team attempts, F5 targets WR, Q1 attempts, Q2 completions, F5 receptions WR, QB carries, Q5 interceptions;
   beta-binomial for F4 target_share WR and TE; rung 3 variance = phi x max(mean, 1) for F5 rushing yards WR, F5 receiving yards TE, QB rushing yards; rung 3z
   zero-hurdle for F5 receiving yards RB, F5 rushing yards TE, QB rushing yards.
HARNESS FAIL (FP null B; tau/sigma): negative binomial F2 team carries .057 (.26), F5 carries RB .129 (.63), F5 targets RB .240 (.76), F5 targets TE .115 (.38), F5
   receptions RB .246 (.95), F5 receptions TE .066 (.37); beta-binomial F4 carry_share RB .127 (.39), F4 target_share RB .110 (.42); rung 3 F5 receiving yards RB .124
   (ladder .233), F5 rushing yards TE .126 (ladder .236); rung 3z F5 rushing yards RB .131, F5 receiving yards WR .195, F5 rushing yards WR .121, F5 receiving yards TE
   .059 (ladder .115).  TD negative binomial (RB, WR, TE, Q4, QB rushing TDs) failed the observed gate as recorded.
F6 v1 (registered consequences applied): F2 team targets / attempts negative binomial, team carries Poisson.  F4 share given team total: beta-binomial WR / TE target
   share, binomial RB carry / target share.  F5 counts: negative binomial WR targets, Q1 attempts, Q2 completions, WR receptions, QB carries; Poisson RB carries, RB / TE
   targets, RB / TE receptions.  TDs: Poisson for F5 TDs RB / WR / TE, Q4, QB rushing TDs; negative binomial Q5 interceptions (around the season-to-date freeze form).
   Yards: rung 3z zero-hurdle QB rushing yards; rung 3 F5 rushing yards WR, F5 receiving yards TE; rung 2 F5 receiving yards RB and F5 rushing yards TE (their 3z sat on a
   failed rung 3), F5 rushing yards RB, F5 receiving yards WR; Q3 passing yards rung 2.
PATTERN: 5 of 6 RB count / share stages and RB rushing-yards 3z fail with tau/sigma .37-.95 (RB dispersion gain varies by season); WR count / share stages pass at
   tau/sigma .00.  LIMITATION as line 38: FP null B is margin-blind (F5 rushing yards RB 3z at 17 s.e. fails); the margin-aware harness challenger now covers these F6
   stages.  Known cost carried into the freeze: Poisson RB carries had 80% coverage 66.8%.

## F6 DEPENDENCE LADDER - declared Oct 3 2026, before any dependence wall runs
Null: independent F6 v1 marginals (CHARTER "F6 MARGINAL PROCEDURE HARNESS - OUTCOME").  One football identity per wall, in order: dependence wall 1, bounded counts
   (F5 receptions given F5 targets RB / WR / TE; Q2 completions given Q1 attempts) as Binomial(bounded count; bounding count, ratio of frozen means), nothing fitted;
   dependence wall 2, beta-binomial precision on that conditional, runs only if wall 1 earns and the bounded count's PIT sd under wall 1 is below 0.27; dependence
   wall 3, player count with team total (F2 team total x F4 share given team total, F6 v1 forms); dependence wall 4, QB passing yards with receiver yards; dependence
   wall 5, QB passing TDs with receiver TDs; dependence wall 6, opposing team volumes; then the dependence harness (line 38 procedure).  Metric: joint negative log
   score per player-game (or team-game), paired by slate, tests 2021, 2023-25; gate p.passes_gate.  Any other structure is a challenger.
## F6 DEPENDENCE WALL 1 - REGISTRATION - Oct 3 2026
Keys unique; targets x receptions matched 5055 / 8661 / 5283 (RB / WR / TE), Q1 x Q2 matched 1895; bounded count never exceeds bounding count (0 rows).  Null:
   marginal(bounding) x marginal(bounded), F6 v1 forms (negative binomial WR targets / WR receptions / Q1 / Q2, Poisson RB / TE targets and receptions; r on earlier
   seasons).  Candidate: marginal(bounding) x Binomial(bounded; bounding, mean_bounded / mean_bounding).  Reported: randomized-PIT Spearman (bounding, bounded) under
   the null; bounded-count PIT mean / sd under both.  Consumer F7, F8.  Reduces: joint uncertainty of player volume and conversion.

## F6 DEPENDENCE WALL 1 - OUTCOME - Oct 3 2026 (proj/f6_dependence_report.txt): EARNED 4 / 4, each 4 / 4 seasons, pending the dependence harness.
   F5 receptions given F5 targets RB +0.80468+-0.03354, WR +0.53249+-0.02605, TE +0.64045+-0.03209; Q2 completions given Q1 attempts +1.16989+-0.05671.  Randomized-PIT
   Spearman under independent marginals +0.764 / +0.713 / +0.729 / +0.883.  Bounded-count PIT mean / sd under wall 1: .486 / .307, .492 / .314, .490 / .307, .495 / .299.
NOTE: the dependence wall 2 condition ("PIT sd below 0.27") is inverted relative to what a beta-binomial precision can repair (a too-narrow conditional, PIT sd above
   0.289).  As registered the condition is not met; wall 2 does not run.  Observed: all four conditionals have PIT sd .299-.314 (too narrow).  Owner decision pending
   on whether the inversion is mechanical.

NOTE (F6 DEPENDENCE LADDER order): dependence wall 3 runs while the wall 2 decision is open; wall 3 pairs different quantities (F2 team total with player count) and
   neither its null nor its candidate uses the wall 1 / wall 2 conditional, so the wall 2 outcome cannot change it.  Wall 2 remains not run as registered.
## F6 DEPENDENCE WALL 3 - REGISTRATION - Oct 3 2026
Slices: F5 targets RB / WR / TE with F2 team targets; F5 carries RB with F2 team carries.  Team from load() (player_id, season, week); team total = F2 spine row (key team).
   Null: F6 v1 team marginal (negative binomial team targets, Poisson team carries) x F6 v1 player marginal (negative binomial WR targets; Poisson RB / TE targets, RB
   carries).  Candidate: same team marginal x F6 v1 share given team total (beta-binomial WR / TE targets, binomial RB targets / carries) with p = frozen F5 mean / frozen
   F2 mean (frozen player mean preserved).  Team r fit on team-game rows, player r and beta-binomial precision on player rows, earlier seasons.  Joint negative log score
   per player-game, paired by slate, tests 2021, 2023-25; gate.  Reported: randomized-PIT Spearman (team total, player count) under the null; player PIT mean / sd
   under both.  Consumer F7, F8.  Reduces: joint uncertainty of team volume and player volume.

## F6 DEPENDENCE WALL 3 - OUTCOME - Oct 3 2026 (proj/f6_dependence_team_report.txt): EARNED 4 / 4, pending the dependence harness.  F5 targets given F2 team targets
   RB +0.13248+-0.01549 (4/4), WR +0.19683+-0.01584 (4/4), TE +0.18011+-0.01724 (4/4); F5 carries given F2 team carries RB +0.07259+-0.03323 (3/4).  Randomized-PIT
   Spearman under independent marginals +.241 / +.297 / +.206 / +.409.  Player PIT sd under wall 3 .320 / .292 / .299 / .359 (RB too narrow: binomial / Poisson v1 cost);
   TE player PIT mean .549 (TE level challenger).  Share forms = F6 v1 (beta-binomial WR / TE, binomial RB).
DECISION (reviewer, Oct 3 2026): dependence wall 2 stays closed as registered; beta-binomial conditional precision -> challenger.
GOVERNING RULE (F6, reviewer Oct 3 2026): prefer a conditional football identity over generic dependence whenever an identity exists; residual (copula / shared-game)
   dependence is tested only after identities are enforced.  Category A structural: wall 1 (conversion: receptions given targets, completions given attempts), wall 3
   (allocation: player count given team total); category B residual: what co-moves after A.  Composition target: team opportunities -> player opportunities ->
   successful opportunities -> yards / scoring, player marginals implied by the hierarchy rather than sampled separately.

## TEAM-GAME IDENTITIES - read Oct 3 2026 (seasons <= 2025, 3200 team-games): passing yards - sum receiving yards exact .888, |diff| <= 5 .929, mean +1.16, p1 / p99
   -1 / +27; passing TDs - sum receiving TDs exact .983, mean +.02; completions - sum receptions exact .887, mean +.15, p99 +3 (positive skew: catches without a player
   row).  Team-games with 1 / 2 / 3 passers 2720 / 465 / 15.  Receiving-yards share WR .639, TE .216, RB .145, QB .0002.
NOTE (dependence wall 5): spine "F5 TDs" = rushing TDs + receiving TDs, so the passing-TD identity has no spine term; wall 5 needs a receiving-TD term and its own
   registration.
## F6 DEPENDENCE WALL 4 - REGISTRATION - Oct 3 2026 (category A, allocation of passing yards)
Team-games with exactly one Q3 passing yards spine row; each F5 receiving yards row (RB / WR / TE) of that team-game paired with it (team from load()).  Null:
   Normal(Y_Q; Q3 mean, sigma_Q) x receiver F6 v1 form at its frozen mean (rung 2 RB / WR, rung 3 TE).  Candidate: same QB term x receiver F6 v1 form at frozen mean x
   Y_Q / max(Q3 mean, 1); nothing fitted (spreads fit on earlier seasons around the frozen means, identical in null and candidate).  Joint negative log score per
   receiver-game, paired by slate, tests 2021, 2023-25; gate.  Reported: pairs used / dropped, randomized-PIT Spearman (QB yards, receiver yards) under the null,
   receiver PIT mean / sd under both.  Consumer F7, F8.  Reduces: joint uncertainty of QB passing yards and receiver yards.

## F6 DEPENDENCE WALL 4 - OUTCOME - Oct 3 2026 (proj/f6_dependence_yards_report.txt): NOT SHOWN 3 / 3.  F5 receiving yards given Q3 passing yards RB -0.03488+-0.03836
   (1/4), WR -0.11390+-0.10350 (1/4), TE -0.10339+-0.04699 (1/4); pairs from 1649 single-passer team-games (123 dropped).  Randomized-PIT Spearman under independent
   marginals +.179 / +.276 / +.182 - co-movement exists, but one-for-one scaling of the receiver mean by realized / frozen QB yards scores worse than independence.
   Independent marginals stay.  Fitted-elasticity or residual (category B) form -> challenger.
## F6 DEPENDENCE WALL 5 - STATUS: not runnable in v1 (spine "F5 TDs" = rushing + receiving TDs; a receiving-TD term would be a new F5 term after the F5 set was fixed).
   Passing-TD allocation -> challenger.

CHALLENGER SPEC (reviewer, Oct 3 2026; dependence wall 4): receiver mean x (realized / frozen QB passing yards)^beta, beta fit on training seasons only (wall 4 hard-coded
   beta = 1); runs on the challenger clock, and is relevant only if F8 shows a receiving-yard covariance miss.  Wall 4 recorded as a boundary: PIT co-movement present,
   registered usable mechanism not demonstrated.
## F6 DEPENDENCE WALL 6 - REGISTRATION - Oct 3 2026 (category B, opposing team volumes)
team_game() opponent non-null 1.0 (seasons <= 2025).  Pairs: F2 team rows of both teams in the same game (home row joined to its opponent's row; both must have F2
   rows).  One quantity at a time: F2 team targets (negative binomial), team carries (Poisson), team attempts (negative binomial), F6 v1 forms, r on earlier seasons.
   Null: independent marginals.  Candidate: Gaussian copula on the same marginals, one correlation rho on grid -0.60..0.60 step 0.05, fit by likelihood on earlier
   seasons' pairs; joint pmf = copula rectangle.  Joint negative log score per game, paired by slate, tests 2021, 2023-25; gate.  Bivariate normal CDF (Owen's T) must
   match scipy multivariate_normal.cdf within 1e-6 at 2000 random points or the run refuses.  Reported: pairs, rho per test season, randomized-PIT Spearman home x away
   under the null, share of rectangles floored.  Consumer F7, F8.  Reduces: joint uncertainty of the two teams' volumes in one game.

## F6 DEPENDENCE WALL 6 - OUTCOME - Oct 3 2026 (proj/f6_dependence_opponent_report.txt; 768 games; bivariate normal self-check 2.22e-16; 0 rectangles floored)
   F2 team carries home with away: rho -0.35 / -0.40 / -0.40 / -0.40, randomized-PIT Spearman -.555, gain +0.22849+-0.02548 (4/4) -> EARNED (pending dependence harness).
   F2 team targets: rho -0.15, Spearman -.103, +0.00390+-0.00490 (3/4) -> NOT SHOWN; F2 team attempts: rho -0.15 / -0.20, Spearman -.117, +0.00449+-0.00561 (3/4) -> NOT
   SHOWN.  Independent marginals stay for team targets and attempts.  Every declared dependence wall now has an outcome.
## F6 DEPENDENCE HARNESS - REGISTRATION - Oct 3 2026
Line 38 procedure and pass rule (observed gate AND FP null B <= .05 AND ladder <= .10; 1000 draws; seed 20261003) on per-row paired joint log scores in
   proj/f6_dependence*_rows.csv.gz (walls 1, 3, 4, 6); L = 1 per slice (each dependence slice tested once; wall 2 never ran).  Consequence: a failing slice enters F6 v1
   as independent marginals.  harness.py gains a "dependence" mode only; spine mode and F6 mode must reproduce their current reports byte-identical (inputs unchanged
   since written).  Reduces: false promotion of dependence structure into the freeze.

## F6 DEPENDENCE HARNESS - OUTCOME - Oct 3 2026 (proj/harness_dependence_report.txt; spine and F6 mode reports reproduced byte-identical)
HARNESS PASS (FP null B .000 each): wall 1 F5 receptions given F5 targets WR, TE; Q2 completions given Q1 attempts; wall 3 F5 targets given F2 team targets RB, WR, TE;
   F5 carries given F2 team carries RB.  HARNESS FAIL: wall 1 F5 receptions given F5 targets RB (FP null B .077, tau/sigma .38; gain +0.80468 4/4); wall 6 F2 team
   carries home with away (FP null B .055, tau/sigma .28).  Walls 4 and wall 6 targets / attempts failed the observed gate as recorded.
F6 v1 JOINT: conditional binomial for WR / TE receptions given targets and Q2 completions given Q1 attempts; share given team total for all four wall 3 slices;
   independent otherwise (RB receptions with RB targets - known cost: simulated receptions can exceed targets, 0 such rows in data; the two teams' carries in one game).
## F7 NATIVE STAT EVALUATOR - CONTRACT - Oct 3 2026 (f7.py, a library; scores composed stat forecasts in native units, independent of DK scoring)
Input: per row (season, week, entity, stat) a vector of simulation draws (historical composition: 2000 draws per row) and the realized value.  Marginal, per row:
   continuous ranked probability score (CRPS, sample form E|X-y| - 1/2 E|X-X'|, exact on sorted draws), randomized PIT from draws, 80% central-interval coverage
   (reported only for stats with mean >= 2), mean bias.  Joint, per registered pair: energy score of the joint draws vs the same marginals with the second coordinate
   shuffled within row (independence; comparison within a pair only), and the joint event "both above their own draw medians" (simulated probability vs realized
   frequency).  Comparisons between forecasts: per-row score differences paired by slate, p.passes_gate.  Self-checks with known answers must pass before any scoring:
   CRPS of N(0,1) at 0 vs 2 phi(0) - 1/sqrt(pi); sorted vs brute-force CRPS; PIT uniform on correctly specified Poisson; 80% coverage on correctly specified Normal;
   energy score prefers the true joint over shuffled independence on correlated data.

## F7 NATIVE STAT EVALUATOR - OUTCOME - Oct 3 2026: self-check ALL PASS (CRPS N(0,1) at 0 .23500 vs .23369; sorted vs brute-force CRPS diff 0; PIT Poisson(3) .5063 /
   .2837; 80% coverage .8004; energy score true joint .8447 < shuffled .8695; joint event .3974 vs .3980).  f7.py is the native-stat referee.
NOTE: the work-order item "rule for team-games with two or more passers" was needed only by dependence wall 4 (closed); in v1 QB stats are generated per QB row.
## STAT SPINE COMPOSITION - REGISTRATION - Oct 3 2026 (spine_compose.py; report-only)
Walk-forward over tests 2021, 2023-25; every F6 v1 parameter refit on earlier seasons; 2000 draws per row; seed 20261003.  Composed per F6 v1: team targets negative
   binomial, team carries Poisson (teams independent); F5 targets = share given team-targets draw (beta-binomial WR / TE, binomial RB, p = frozen F5 mean / frozen F2
   mean); F5 carries RB = binomial given team-carries draw; F5 receptions WR / TE = binomial given targets draw at ratio of frozen means, RB independent Poisson;
   Q2 completions = binomial given Q1 attempts draw; every other stat its independent F6 v1 marginal.  F7: CRPS composed vs independent F6 v1 marginals (paired by slate,
   gate) only for F5 targets, F5 receptions, F5 carries RB, Q2 completions (other stats identical by construction - NO TEST, descriptive calibration only); energy score
   composed vs independent for the four hierarchy pairs; joint event calibration.  Mechanical acceptance: summed composed draw means within 1% of summed frozen means
   for every composed stat, else no rows written.  Nothing promoted or demoted by this report; disagreements with the wall verdicts go to the work order.  Known v1
   costs carried: teammates' allocations independent given the team draw; yards independent of receptions; RB receptions independent of RB targets.

## STAT SPINE COMPOSITION - OUTCOME - Oct 3 2026 (proj/spine_compose_report.txt; report-only): mechanical check PASS 8 / 8 (max rel +.0016).  CRPS composed vs
   independent F6 v1 marginals: targets RB +0.00420 (4/4), WR +0.00788 (4/4), TE +0.00530 (4/4); receptions WR +0.00463 (4/4), TE +0.00285 (4/4), RB -0.00034 (2/4);
   F5 carries RB +0.00092 (3/4); Q2 completions -0.03267+-0.00619 (0/4).  Energy score composed better on all 8 pairs (4/4 each; Q1 attempts with Q2 completions
   +0.26448).  Joint event simulated vs realized: RB targets with receptions .114 vs .285 (independence cost), TE .267 vs .329, every other pair within .025.
NODES LOCATED BY F7 (reviewer classification; challengers, not repaired on these seasons): (1) Q2 completions given Q1 attempts - joint good, fixed conditional rate
   distorts the Q2 marginal -> marginal-preserving conditional; (2) F5 carries given F2 team carries RB - mean and joint good, PIT sd .357, coverage 66.7% -> conditional
   share dispersion; (3) TE targets PIT .542 / bias -.203 propagating to TE receptions .536 / -.124 -> F4 / F5 TE level; (4) Q3 passing yards PIT .475 / bias +7.138
   with sd .284 / coverage 81.0% -> Q3 mean level; (5) RB targets with receptions joint event -> known wall 1 RB cost.  Next: F8 mechanical DK transform, F8 vs Y;
   walk backward only from F8 failures.

## F8 MECHANICAL DK TRANSFORM + F8 VS Y - REGISTRATION - Oct 3 2026 (DK is downstream of the stat spine; one mechanical step, no DK feature work)
Rules (owner-supplied, offense only): passing TD +4, passing yards +.04 / yd, 300+ passing yards +3, interception -1; rushing TD +6, rushing yards +.1 / yd, 100+ +3;
   receiving TD +6, receiving yards +.1 / yd, 100+ +3, reception +1.  Not spine terms, omitted: fumble lost, 2-point conversion, return / recovery TDs (F5 TDs = rushing
   + receiving TDs, both +6).  F8 = rules applied to each composed draw (spine_compose.py, its own generator for F8 PIT so the composition streams are unchanged; its
   report and rows must reproduce byte-identical).  Realized = load() dk_points; box-score reconstruction with the same rules reported against it.  F8 vs frozen Y
   (proj/ystick_rows.csv.gz, walk-forward) on matched rows, tests 2021, 2023-25, per position and overall: center absolute error and mean quantile score (pinball at .1 /
   .5 / .9), each paired by slate with the gate; share below p10 / above p90; PIT.  F8 CRPS reported (Y has quantiles only).  Near-zero comparison omitted (Y threshold
   not on screen).  Consequence: F8 losses are walked backward to the smallest native node; nothing replaces Y in the DK track before the stat-spine prospective clock.

NOTE (F8 acceptance): the first rows / pairs comparison used zcat, which on macOS looks for a .Z file and failed, so it compared empty streams (false "reproduced");
   only spine_compose_report.txt had reproduced.  Re-verified: original spine_compose.py rebuilt by reversing the anchored edits, rows / pairs compared with gzip -dc
   against the patched script, and f8_vs_y_report.txt reproduced.  Future decompression in checks uses gzip -dc.
## F8 VS Y - OUTCOME - Oct 3 2026 (proj/f8_vs_y_report.txt; 16713 matched rows, tests 2021, 2023-25)
Rules check: box-score reconstruction = dk_points exact .940, within 2 pts .995, mean -.019 (omitted items negligible).  Center absolute error, F8 vs Y: ALL +0.0608+-
   0.0104 (4/4) F8 better; RB +0.0979 (4/4), TE +0.1261 (4/4) better; WR +0.0336+-0.0209 (3/4) not shown; QB -0.0962+-0.0511 (0/4) worse.  Quantile score (.1 / .5 / .9):
   F8 worse at every position (ALL -0.0975+-0.0050, 0/4).  Tails: above p90 F8 .131-.160 (ALL .147) vs Y .096; below p10 F8 .106 vs Y .050; PIT sd F8 .302, Y .285.
   Reading: the stat spine's center beats Y overall, RB, TE; its fantasy distribution is too narrow, mainly a thin upper tail.  QB center: F8 mean 17.22 vs realized
   16.62 (Q3 / Q1 level nodes).  Walk backward next: measure within-player co-movement of components that v1 draws independently (yards, TDs vs receptions).

## F8 ACCEPTANCE - re-verified Oct 3 2026: original spine_compose.py (reverse of the anchored edits) and the patched one write identical rows (92130 lines) and pairs
   (35929 lines) under gzip -dc; spine_compose_report.txt and f8_vs_y_report.txt reproduced.  F8 VS Y OUTCOME stands.
## F8 WALK-BACK - read Oct 3 2026 (realized Spearman of per-stat PITs within player-game, pairs v1 draws independently)
Receiving yards x receptions RB +.669 / WR +.701 / TE +.753; x targets +.609 / +.576 / +.665; rushing yards x carries RB +.694, QB +.521; passing yards x completions
   +.780, x attempts +.694; TDs x yards RB +.112 / +.228, WR +.188, TE +.153, passing TDs x passing yards +.460.  Node located: conversion of opportunities into
   yards (yards given receptions / carries / completions), drawn independently in v1 - consistent with F8's thin upper tail.  The F6 DEPENDENCE LADDER as declared
   ends "Any other structure is a challenger"; timing (pre-freeze wall vs challenger) is an owner decision.

## ZERO-OPPORTUNITY IDENTITIES - read Oct 3 2026 (played rows, seasons <= 2025): receptions == 0 -> receiving yards != 0 in 7 of 12869; carries == 0 -> rushing yards
   != 0 in 5 of 26509; completions == 0 -> passing yards != 0 in 0 of 367.  Positive opportunities with zero yards: 203 / 22692, 346 / 13011, 3 / 3592.
DECISION (reviewer, Oct 3 2026): option (b) - the F6 DEPENDENCE LADDER is extended before the freeze.
## F6 DEPENDENCE LADDER - EXTENSION - declared Oct 3 2026, before wall 7 runs
Dependence wall 7: yards given realized opportunities (receiving yards given receptions RB / WR / TE; rushing yards given carries RB; Q3 passing yards given Q2
   completions; QB rushing yards given QB carries).  Dependence wall 8: TDs given volume - runs only if, after wall 7 enters composition, F8 above-p90 share stays above
   .12 overall.  Each earned wall goes through the dependence harness; composition and F8 vs Y are re-run after each.  FREEZE RULE: freeze v1 when the F8 quantile-score
   gain over the previous composition fails the gate.  Any other structure is a challenger.
## F6 DEPENDENCE WALL 7 - REGISTRATION - Oct 3 2026 (category A, conversion of opportunities into yards)
Null: opportunity F6 v1 marginal (negative binomial F5 receptions WR, Q2 completions, QB carries; Poisson F5 receptions RB / TE, F5 carries RB; r on earlier seasons) x
   yards F6 v1 marginal (rung 2 receiving yards RB / WR, rushing yards RB, Q3; rung 3 receiving yards TE; rung 3z zero-hurdle QB rushing yards).  Candidate: same
   opportunity marginal x yards given realized count n: n > 0 -> Normal(n e, n v), e = frozen yards mean / frozen opportunity mean (frozen yards mean preserved), v =
   per-opportunity variance fit on earlier seasons (rows n > 0); n = 0 -> point mass at 0 with leak 0.001 (observed .0005), leak density Normal(0, v).  Joint negative log
   score per player-game (unit-bin), paired by slate, tests 2021, 2023-25; gate.  Reported: gain split n = 0 / n > 0 rows; conditional PIT mean / sd on n > 0 rows.
   Rows to proj/f6_dependence_efficiency_rows.csv.gz.  Consumer F7, F8.  Reduces: within-player joint uncertainty of opportunities and yards (F8 thin upper tail).

## F6 DEPENDENCE WALL 7 - OUTCOME - Oct 3 2026 (proj/f6_dependence_efficiency_report.txt): EARNED 6 / 6, each 4 / 4 (pending the dependence harness).
   Receiving yards given receptions RB +1.65709+-0.03589, WR +1.61270+-0.02416, TE +1.66325+-0.02662; rushing yards given carries RB +1.08777+-0.05256; Q3 passing yards
   given Q2 completions +0.72892+-0.04191; QB rushing yards given QB carries +0.59666+-0.02505.  Mean gain per row n = 0 / n > 0: RB +3.87 / +.38, WR +4.48 / +.49, TE +3.34 /
   +.65, RB rushing +4.31 / +.35, Q3 +6.27 / +.57, QB rushing +1.73 / +.46.  Conditional PIT (n > 0) mean .481-.511, sd .256-.280.
NOTE (dependence harness scope): harness.py dependence mode consumes one random stream across files in sorted order; adding the wall 7 rows file would re-draw the
   recorded wall 1 / 3 / 4 / 6 outcomes.  harness.py gains an optional rows-file argument; wall 7 is harnessed alone (fresh stream, seed 20261003);
   harness_dependence_report.txt remains the record for walls 1, 3, 4, 6.  Spine and F6 modes must reproduce byte-identical.

## F6 DEPENDENCE WALL 7 HARNESS - OUTCOME - Oct 3 2026 (proj/harness_dependence_efficiency_report.txt; spine and F6 modes reproduced byte-identical)
HARNESS PASS: F5 receiving yards given F5 receptions TE (FP null B .000), F5 rushing yards given F5 carries RB (.000), Q3 passing yards given Q2 completions (.000), QB
   rushing yards given QB carries (.000).  HARNESS FAIL: F5 receiving yards given F5 receptions RB (.056, tau/sigma .26), WR (.204, tau/sigma .58).
DISCLOSURE (harness procedure defect, not yet corrected): harness.py draws every slice of a run from one random stream in order, so each slice's FP null B depends on the
   slices and files before it.  The wall 7 scoping kept recorded outcomes from being re-drawn but does not remove the order dependence, which affects every recorded
   harness outcome.  Monte Carlo sd at 1000 draws near .05 is about .007; outcomes within about 2 sd of the line: Q4 passing TDs .048 (pass), F2 team carries negative
   binomial .057, F5 receiving yards TE rung 3z .059, wall 6 team carries .055, wall 7 receiving yards RB .056 (fail).  Correction (per-slice seeds) re-draws every
   recorded outcome - owner decision pending; composition with wall 7 waits on it.

## HARNESS PROCEDURE v1 SUPERSEDED / HARNESS PROCEDURE v2 - REGISTRATION - Oct 3 2026 (reviewer option (d))
Recorded v1 outcomes used one sequential random stream per run, so they were not slice-order invariant; they stay above as provenance and are superseded for freeze
   eligibility.  No model wall is re-run or retuned; inputs, losses, null A / null B / power procedure and ladder L are unchanged.  v2 changes measurement only: seed per
   slice = first 8 bytes of sha256("term|position"); 10000 draws; null A signs generated per draw from the slice's generator (memory).  Pass rule unchanged in substance:
   observed gate AND FP null B <= t, t = min(.05, 1 - .9^(1/L)).  RESOLUTION-BOUNDARY: |FP null B - t| < 2 sqrt(t(1-t)/10000) (about +-.0044 at .05, +-.0037 at .0345) ->
   baseline enters the freeze, either side of t; no second re-run.  Witnesses before any verdict is read: order invariance (dependence slices in order vs reversed) and
   subset invariance (wall 7 file alone vs inside all dependence files) must give identical per-slice results.  Every harness family re-run once (spine, F6 marginal,
   dependence incl. wall 7); every verdict change accepted in both directions.  Reports overwrite harness_report.txt, harness_f6_report.txt,
   harness_dependence_report.txt; harness_dependence_efficiency_report.txt deleted (subsumed).

## HARNESS v2 - OUTCOME - Oct 3 2026 (harness_report.txt, harness_f6_report.txt, harness_dependence_report.txt; 10000 draws; per-slice seeds)
Witnesses: order invariance PASS (20 dependence slices); subset invariance PASS (6 wall 7 slices).  Verdict changes vs v1: Q1 attempts RESOLUTION-BOUNDARY (FP null B
   .0312, t .0345 +- .0037) -> season-to-date enters; Q4 passing TDs FAIL (.0630) -> season-to-date enters.  Every other verdict unchanged: spine WR TDs FAIL .0674, Q5
   FAIL .0624; F6 marginal passes / fails as recorded (F2 team carries .0625, F5 receptions TE .0656, F5 receiving yards TE rung 3z .0587 fail); dependence wall 1 RB
   FAIL .0590, wall 6 team carries FAIL .0614, wall 7 RB .0634 / WR .1861 FAIL, wall 7 TE receiving, RB rushing, Q3 given Q2, QB rushing PASS; walls 1 WR / TE / QB and
   wall 3 (4 slices) PASS.  Harness v2 outcomes supersede v1 for freeze eligibility.  The F8 VS Y OUTCOME is superseded as a diagnostic (its composition used Q1 v1,
   Q4 v1, and Q2 / Q3 built on Q1 v1); it does not decide dependence wall 8.
## FREEZE DEPENDENCY PROPAGATION - REGISTRATION - Oct 3 2026 (reviewer)
Every term consuming a parent that now enters at baseline is recomputed with that baseline parent under its original registered test, gate and harness; no new
   features, grids, models, states or hyperparameters; every changed result accepted.  Descendants: Q1 -> Q2, Q3 (Q5 already enters at season-to-date); Q4 -> F6 Q4
   marginal, composition.  Step 1 (this transaction): spine.py emits "Q2 completions (Q1 season-to-date parent)" and "Q3 passing yards (Q1 season-to-date parent)" =
   season-to-date attempts x shrunk rate (kr refit against season-to-date attempts, same grid), baseline season-to-date, MAE; harness v2 with L = 2 (as Q2 / Q3).
   Acceptance: spine self-check 20 / 20, issue path equal on every term, every existing harness spine-report line unchanged.  Step 2: F6 terms and dependence walls whose
   means change (Q1 attempts, Q2, Q3, Q4 marginals; wall 1 QB; wall 7 Q3 given Q2) re-run on the freeze-form means.  Step 3: composition from the corrected table, F7,
   F8 vs Y.

## FREEZE DEPENDENCY PROPAGATION STEP 1 - OUTCOME - Oct 3 2026: spine 148958 rows / 21 terms; self-check 20 / 20; issue path 33 / 33 equal; 79 / 79 existing harness spine
   lines unchanged.  Q2 completions (Q1 season-to-date parent) +0.05133+-0.02066 (5/5), FP null B .0000, power at 100% .75 -> HARNESS PASS; Q3 passing yards (Q1
   season-to-date parent) +0.78842+-0.33843 (5/5), FP null B .0000, power .63 -> HARNESS PASS.  Freeze-form means: Q1, Q4, Q5, WR TDs season-to-date; Q2, Q3 =
   season-to-date attempts x shrunk rate; every other term v1.
## FREEZE DEPENDENCY PROPAGATION STEP 2 - REGISTRATION - Oct 3 2026
freeze.py apply_freeze(spine rows) replaces v1 by the freeze-form mean (above; Q2 / Q3 joined from the parent terms by season, week, player, refusing on any missing join).
   Consumers whose means change get apply_freeze at their spine_rows read and nothing else: f6_count (Q1 attempts, Q2 completions), f6_td (Q4; season-to-date set gains
   Q4), f6_q3 (Q3), f6_dependence (Q2 completions given Q1 attempts), f6_dependence_efficiency (Q3 given Q2).  Each re-run under its registered test; harness v2 F6 and
   dependence modes re-run.  Acceptance: report diffs confined to those slices; any other changed line is a defect.  Every changed result accepted.

## FREEZE DEPENDENCY PROPAGATION STEP 2 - OUTCOME - Oct 3 2026: report diffs confined to the registered slices (no other line changed).  On freeze-form means: F6 Q1
   attempts negative binomial +0.93499+-0.08941 (4/4) but HARNESS FAIL (FP null B .0637, tau/sigma .32) -> Q1 attempts Poisson around season-to-date (Poisson 80% coverage
   58.2%, known cost); Q2 completions negative binomial +0.41918+-0.04557 (4/4) HARNESS PASS; Q4 Poisson around season-to-date (PIT .523 / .298; negative binomial not
   shown); Q3 rung 2 (rung 3 -0.17753, 0/4; PIT .498 / .286; 3z not triggered); wall 1 Q2 completions given Q1 attempts +1.25817+-0.05772 HARNESS PASS; wall 7 Q3 given
   Q2 completions +0.78056+-0.03993 HARNESS PASS.
CORRECTED ARCHITECTURE (harness v2 + propagation): team targets negative binomial -> player targets (beta-binomial WR / TE, binomial RB); team carries Poisson -> RB
   carries binomial; WR / TE receptions binomial given targets, RB receptions Poisson; wall 7 yards given opportunities for TE receiving, RB rushing, Q3 given Q2, QB
   rushing given QB carries; other yards independent F6 v1 marginals; Q1 attempts Poisson (season-to-date) -> Q2 binomial; TDs Poisson on freeze-form means; Q5
   negative binomial (season-to-date).
## FREEZE DEPENDENCY PROPAGATION STEP 3 - REGISTRATION - Oct 3 2026 (report-only)
spine_compose.py rebuilt on the corrected architecture: apply_freeze means; Q1 attempts Poisson; wall 7 links draw yards given the composed opportunity draw, Normal(n e,
   n v), e = ratio of frozen means, v refit on earlier seasons, n = 0 point mass with leak .001.  F7: CRPS composed vs independent F6 v1 marginals for every stat whose
   form differs (adds TE receiving yards, RB rushing yards, Q3, QB rushing yards); energy score for the hierarchy pairs (adds the four wall 7 pairs).  Mechanical
   acceptance: summed composed draw means within 1% of summed frozen means for every composed stat (adds the four yards stats), else no rows written.  F8 per row; then
   f8_vs_y.py unchanged.  Outputs supersede the earlier composition / F8 files.  Dependence wall 8 opens only if F8 above-p90 share stays above .12 overall.

## FREEZE DEPENDENCY PROPAGATION STEP 3 - OUTCOME - Oct 3 2026 (spine_compose_report.txt, f8_vs_y_report.txt): mechanical check PASS 12 / 12 (max rel -.0018).
   Wall 7 in composition, CRPS composed vs independent: RB rushing yards +1.29469 (4/4), TE receiving yards +0.55252 (4/4), QB rushing yards +0.55483 (4/4), Q3 passing
   yards -0.70368+-0.16557 (0/4); energy score RB carries with rushing yards +1.31977, TE receptions with receiving yards +0.58225, QB carries with rushing yards
   +0.57028 (4/4 each), Q2 completions with Q3 -0.56310 (0/4).  QB chain: Q1 attempts Poisson PIT sd .369, coverage 58.1% -> composed Q2 sd .350, coverage 64.5%, CRPS
   -0.04987 vs independent (0/4) -> Q3 coverage 70.5% (registered cost of the Q1 negative binomial harness fail; Q1 dispersion -> challenger).
   F8 vs Y (16713 rows): center ALL +0.0513+-0.0104 (4/4), RB +0.0930 (4/4), TE +0.1295 (4/4), WR +0.0344 (3/4) not shown, QB -0.2003 (0/4); quantile score worse at every
   position (ALL -0.0946, 0/4); above p90 ALL .147 (RB .151, WR .145, TE .141, QB .164); below p10 .112.  Dependence wall 8 condition (.147 > .12) MET.  Freeze rule not
   applicable yet (first composition on the corrected architecture).
## F6 DEPENDENCE WALL 8 - REGISTRATION - Oct 3 2026 (TDs given volume)
TD count given realized volume n ~ Poisson((n + .001) tau), tau = frozen TD mean / frozen volume mean (freeze-form means; nothing fitted).  Volume: F5 TDs RB = F5 carries +
   F5 receptions; F5 TDs WR / TE = F5 receptions; Q4 passing TDs = Q2 completions; QB rushing TDs = QB carries.  Null: TD F6 v1 Poisson marginal.  The volume term is
   identical in null and candidate and cancels.  Negative log score per player-game, paired by slate, tests 2021, 2023-25; gate; then harness v2 on its rows file alone.
   Reported: rows with n = 0 and TD > 0; conditional PIT.  Rows to proj/f6_dependence_touchdowns_rows.csv.gz.  Consumer: composition, F8.

## F6 DEPENDENCE WALL 8 - OUTCOME - Oct 3 2026 (f6_dependence_touchdowns_report.txt; harness v2)
F5 TDs given F5 receptions WR +0.03560+-0.00582 (4/4) HARNESS PASS (.0000); Q4 passing TDs given Q2 completions +0.09210+-0.01434 (4/4) HARNESS PASS (.0000), conditional
   PIT mean .530; QB rushing TDs given QB carries +0.03675+-0.00809 (4/4) HARNESS PASS (.0000); F5 TDs given F5 carries + F5 receptions RB +0.04472+-0.00612 (4/4) HARNESS
   FAIL (.0629); F5 TDs given F5 receptions TE -0.46934+-0.26864 (0/4) gate fail, under examination: suspected near-zero frozen-receptions denominator in tau (TE TD v1
   hierarchical with red-zone targets; TE receptions season-to-date), unconfirmed.
DISCLOSURE: the harness v2 rewrite omitted the optional rows-file argument, so the wall 8 harness ran over every dependence rows file; with per-slice seeds every
   previously recorded slice reproduced its v2 values exactly and wall 8's values do not depend on the other files; harness_dependence_report.txt now includes wall 8.

## RATIO-OF-FROZEN-MEANS DENOMINATOR - read Oct 3 2026: wall 8 TE rows with frozen receptions mean < .05: 491, carrying -2177.2 of the total -2029.2 (tau up to 594.5);
   every other TE bin gains (+.006 to +.056 per row).  WR (< .05: 449 rows, -42.9; tau max 1.00) and RB (186 rows, -55.3; tau max 2.29) also lose in that bin.  Wall 1 TE
   (376) and wall 7 TE (491) zero-denominator rows have numerators <= .05 (no blow-up, ratio undefined 0/0).  Frozen means are season-to-date over 3-13 prior games,
   so any value < .05 is exactly 0.
## DEFINEDNESS RULE - REGISTRATION - Oct 3 2026 (mechanical defect correction, applied uniformly before any re-run)
Where the frozen mean of the conditioning count is exactly zero (no volume so far this season), a ratio-of-frozen-means conditional is undefined; that row uses the
   independent F6 v1 marginal.  Applies to dependence wall 1 (p = receptions / targets, completions / attempts), wall 7 (e = yards / opportunities), wall 8 (tau = TDs /
   volume); wall 3 (denominator = team mean, never zero) unaffected.  Walls 1, 7, 8 re-run; harness v2 dependence re-run; every outcome accepted in either direction.  Counts
   of affected rows printed and must equal the read's sub-.05 counts.  Composition applies the same rule next.

NOTE (DEFINEDNESS RULE acceptance): the registered witness "frozen means below .05 are exactly zero" was false - not every frozen mean is season-to-date.  Wall 8 RB:
   186 rows below .05 = 175 exact zeros + 11 positive frozen F5 carries RB means (.0080-.0474; F2 x recency share, season-to-date base .125-.200).  The exact-zero rule
   was implemented correctly (script count 175); the 186 witness is superseded and the re-run (walls 1, 7, 8 and harness v2 dependence) is accepted as run.
   Verdicts recorded, not yet consumed by composition.
## TINY POSITIVE DENOMINATORS - read Oct 3 2026 (rows with 0 < frozen denominator < .077; largest ratio among them): wall 7 rushing yards / carries RB 47 (105.73),
   receiving yards / receptions WR 5 (24.0), TE 14 (21.0), RB 6 (7.0); wall 1 receptions / targets WR 19 (4.00), RB 4 (1.00), TE 11 (1.00); wall 8 TDs / volume RB 19
   (2.29), WR 5 (1.00), TE 14 (.75); QB slices 0.
## TINY-POSITIVE INFLUENCE DIAGNOSTIC - REGISTRATION - Oct 3 2026 (diagnostic only; no verdict changes; .077 = 1/13 is a diagnostic reference, not a remedy)
Wall scripts 1, 7, 8 add output columns only (key, frozen numerator, frozen denominator); their reports must reproduce byte-identical.  Per wall / slice, test rows grouped by
   frozen denominator (0 / (0, .077) / >= .077): rows, summed and mean gain l_base - l_cand, share of the slice's total gain, ratio max / p95 / p99.  Negligible influence
   -> the definedness-rule verdicts are consumed and composition proceeds; material concentration -> a near-zero stability wall is registered before composition.

## TINY-POSITIVE INFLUENCE DIAGNOSTIC - OUTCOME - Oct 3 2026 (reports reproduced byte-identical; zero-denominator group gain exactly 0 in every slice)
Rows with 0 < frozen denominator < .077, share of slice gain: wall 7 F5 rushing yards given F5 carries RB 47 rows, -226.91 (-6.7%; mean -4.83; ratio max 105.73) while the
   3725 rows >= .077 gain +3632.76; wall 8 RB TDs 19 rows -1.1%; every other slice between -0.1% and +0.6%.
OWNER DIRECTION (Oct 3 2026): no fallbacks - they create inconsistency in the data and make it hard to trace; honesty instead.  The DEFINEDNESS RULE substituted the
   independent marginal where the conditional was undefined - a fallback; its verdicts (walls 1, 7, 8 re-run and harness) are NOT consumed.
ROOT (from the reads): ratio-of-frozen-means conditionals divide one term's frozen mean by another's when the two come from different estimators - TE TDs (hierarchical,
   red-zone targets count without catches) over TE receptions (season-to-date); RB rushing yards (season-to-date) over RB carries (F2 x recency share).  Zero and tiny
   denominators are instances of this inconsistency, not of small numbers.  Related class, recorded not changed: clip(lower=1e-3) mean floors in the F6 scripts and the
   .01 deviance floor are silent substitutions at zero.  Owner decision pending on how walls 1, 7, 8 treat these rows.

## DECISION (reviewer, Oct 3 2026): D - coherent estimator pairs + explicit mathematical domain + no semantic fallback / floor.  Undefined state != small positive state.
COHERENCE (mechanical reading of D from spine.py estimator forms): a ratio of frozen means mu_Y / mu_N is coherent iff it equals a per-opportunity rate from one information
   set: (i) both season-to-date means over the same games (ratio = sum y / sum n); (ii) both season-to-date attempts x a registered shrunk rate; (iii) denominator =
   season-to-date base of a numerator built as that base x a registered rate.  Coherent: wall 1 RB, TE receptions / targets, Q2 / Q1; wall 7 receiving yards / receptions
   RB, WR, TE, Q3 / Q2, QB rushing yards / QB carries; wall 8 WR TDs / receptions.  Incoherent (the wall does not apply; the stat keeps its F6 v1 independent marginal for
   every row of the slice): wall 1 WR (targets F2 x recency share); wall 7 RB rushing yards / carries (F2 x recency share); wall 8 RB, TE, QB rushing TDs (hierarchical
   TD v1), Q4 / Q2 (season-to-date count over shrunk-rate product).
DOMAIN (coherent slices): mu_N > 0 defined; mu_N = 0 and mu_Y = 0 undefined; mu_N = 0 and mu_Y > 0 inconsistent; undefined / inconsistent rows are named strata outside the
   gate, counted and reported; composition gives them an explicit path label (no silent substitution).  The exact-zero independent-marginal implementation is withdrawn.
INVENTORY (silent-substitution read): semantic substitutions to remove - mean clip(lower=1e-3) in f6_count, f6_td, f6_rec, f6_dependence, f6_dependence_team,
   f6_dependence_opponent, f6_dependence_efficiency, f6_dependence_touchdowns, spine_compose cl(); LEAK = .001; f6_share share clip(1e-4, 1-1e-4).  Unclear, own line:
   spine.py max(sum, 1) in TD-rate priors, fillna(league rate) for interceptions, fillna(0) on box-score columns.  Own wall: deviance FLOOR .01 (spine.py, harness.py).
   Kept as numerical protection: copula u, v clip and h, k guard; 1e-300 density floor after the law assigns probability.  Kept as declared model forms: max(mean, 1) in
   the yards variance law; hurdle mixtures; max(n, 1) where n = 0 has its own point mass.

## THREE STATES (reviewer, Oct 3 2026): undefined ratio (0/0; D domain) != defined zero rate (positive exposure, zero successes so far; a law with zero support for the
   first success) != positive rate.  The 1e-3 floors were silently supplying first-event support; they stay removed and are replaced by a probabilistic law.
CLASSIFICATION: wall 1 RB / TE receptions blocked by first-event support (16 / 31 defined rows); wall 8 WR TDs materially blocked (219-223); wall 1 QB, wall 7 RB / TE
   receiving yards and Q3 clean on support; wall 7 WR receiving yards (2 rows) and QB rushing yards (1 row) small identity-exception residue.  Walls 1 / 8 gates are not
   re-run under raw zero-rate laws.
NOTE: the coming FIRST-EVENT SUPPORT WALL (pooled rate law fit on earlier seasons, the same law for zero and nonzero histories, no branch, no floor) is a new wall; closed
   dependence wall 2 (extra conditional dispersion) is not reopened.  Identity exceptions (realized n = 0 with Y != 0) are not reached by a shrunk rate; their handling
   remains an owner decision.

## FIRST-EVENT SUPPORT AUDIT - read Oct 3 2026 (count terms, test seasons, freeze-form means; frozen mean exactly 0 / of those realized > 0): F5 TDs WR 2864 / 229 (3.3%),
   TE 1275 / 55, RB 521 / 25; F5 receptions RB 417 / 64, WR 449 / 81, TE 491 / 83; F5 targets RB 350 / 58, WR 334 / 63, TE 376 / 69; F5 carries RB 240 / 27; Q5 120 / 40;
   Q4 81 / 21; QB rushing TDs 199 / 14; Q1 17 / 4; QB carries 12 / 4; F2 team totals and Q2 0.  Zero-support laws arise in every estimator family (season-to-date, F2 x
   recency share, hierarchical).
## CONSTRUCTOR STATE (owner idea, Oct 3 2026) - REGISTRATION, step 1
A three-state label is set where each spine estimate is constructed and travels with it; consumers dispatch on the label and never re-infer state from a value or a
   threshold.  States: undefined (estimator not formed, NaN), zero (formed, exactly 0), nonzero (formed, != 0; positive for counts; yards may be negative); any other
   value refuses the run.  undefined is a domain boundary; zero and nonzero go through the same law (no zero branch).  Step 1: spine.py mk() emits state_base and state_v1;
   freeze.py carries the state with the freeze-form mean.  No consumer reads the labels yet.  Acceptance: spine self-check 20 / 20 and issue path 33 / 33 unchanged; label
   counts on freeze-form means equal the audit's zero counts for every count term.  Step 2 (next): coherent rates built in spine.py from the same history sums with labels
   from their inputs (exposure 0 -> undefined, successes 0 -> zero), replacing downstream ratio-of-frozen-means.

## CONSTRUCTOR STATE step 1 - OUTCOME - Oct 3 2026: spine self-check 20 / 20; issue path 33 / 33; label witness 19 / 19 count terms (zero == v1 == 0 on every row).
DECISION (reviewer, Oct 3 2026): C - identity exceptions (realized n = 0, realized Y != 0) are labelled identity_exception: outside the gate and the harness, reported
   separately (count, seasons, keys, null loss); composition gives them no law.  An exception-component challenger opens only if the stratum appears in several seasons with
   material size or materially changes F8.  States in walls 7 / 8: n > 0 scored by the conditional; n = 0 and Y = 0 scored by the identity point mass; n = 0 and Y != 0
   identity_exception.
## CONSTRUCTOR STATE step 2 - REGISTRATION - Oct 3 2026
spine.py emits proj/spine_sufficient.csv.gz per test player-game: prior games, prior sums (targets, carries, receptions, receiving yards, rushing yards, TDs; every QB
   column), and a label per registered coherent rate pair set from its inputs (exposure 0 -> undefined, successes 0 -> zero, else nonzero): catch rate RB / TE; TDs per
   reception WR; receiving yards per reception RB / WR / TE; QB rushing yards per carry.  Q2 / Q1, Q3 / Q2 (shrunk-rate coherence) not included; incoherent pairs not built
   from sums (option b stays a challenger).  Acceptance: spine self-check 20 / 20, issue path 33 / 33 unchanged; every season-to-date base = prior sum / prior games (max
   |diff| < 1e-9); undefined counts per pair equal the D read (350, 376; 417, 449, 491; 449; 12).

## CONSTRUCTOR STATE step 2 - OUTCOME - Oct 3 2026: self-check 20 / 20; issue path 33 / 33; season-to-date base = prior sum / prior games for 20 terms (max |diff|
   1.42e-14); undefined per pair = D read (350, 376; 417, 449, 491; 449; 12).  Zero states: catch rate RB 67, TE 115; receiving yards per reception RB 12, WR 5, TE 13; TDs
   per reception WR 2415; QB rushing yards per carry 6.  proj/spine_sufficient.csv.gz covers every history season (2020 on).
## FIRST-EVENT SUPPORT WALL - REGISTRATION - Oct 3 2026 (new wall; not dependence wall 2)
Slices: catch rate RB, TE (conditional receptions given realized targets); TDs per reception WR (conditional TDs given realized receptions).  Sufficient statistics from
   spine_sufficient (prior successes s, prior exposure n, constructor label); realized k, y from spine_rows.  Baseline: raw-rate law (Binomial(k, s/n); Poisson(k s/n)),
   defined for n > 0.  Candidate: conjugate pooled law, the same for every history - Beta(a, b) prior -> Beta-binomial(k, a + s, b + n - s); Gamma(a, b) prior -> negative
   binomial(r = a + s, p = (b + n) / (b + n + k)); prior fit by maximum likelihood on earlier seasons (catch-rate mean .30-.90 step .01; TD-per-reception mean .010-.150 step
   .002; concentration logspace(0, 3, 31)).  Strata: undefined (n = 0; candidate scored descriptively), identity_exception (k = 0, y > 0; decision C), baseline-impossible
   with candidate finite (counted).  Gate: rows with both forms finite, paired by slate, tests 2021, 2023-25.  Acceptance: candidate finite on every non-exception row; no
   floor; no branch.  Reported: fitted prior per test season, candidate conditional PIT.  Gate rows to proj/f6_rows_support.csv.gz; harness v2 F6 mode re-run (earlier
   slices must be unchanged).  Consumer: dependence walls 1 and 8, composition.

## FIRST-EVENT SUPPORT WALL - OUTCOME - Oct 3 2026 (f6_support_report.txt; harness v2 F6 mode, earlier slices unchanged)
Catch rate RB Beta-binomial +0.02923+-0.00627 (4/4) HARNESS PASS (.0000), acceptance PASS, raw rate impossible on 127 rows, prior mean .77-.78 conc 126-251, PIT .501 /
   .290; catch rate TE +0.04395+-0.00988 (4/4) HARNESS PASS (.0000), acceptance PASS, 126 rows, prior .67-.70 conc 100-126, PIT .514 / .286; TDs per reception WR
   Gamma-Poisson -0.00947+-0.00288 (0/4) NOT SHOWN (acceptance PASS; raw rate impossible on 218 rows; prior .078-.080 conc 126) -> wall 8 WR keeps the raw-rate law.
LIMITATION (registered design, not a rescue): the gate uses rows where both forms are finite, so it excludes exactly the rows where the baseline fails and favours the
   baseline; the candidate's advantage on those rows is counted (218 WR), not gated.
## DEPENDENCE WALLS 1, 7, 8 UNDER D - REGISTRATION - Oct 3 2026 (f6_dependence_domain.py, consolidated; dispatches on constructor labels)
Slices (coherent only): wall 1 RB / TE receptions given targets, conditional = support law (Beta-binomial, prior refit by the support wall's procedure - must equal
   f6_support_report.txt), QB Q2 given Q1, Binomial(realized attempts, Q2 mean / Q1 mean); wall 7 receiving yards given receptions RB / WR / TE and QB rushing yards given
   QB carries (e = prior yards sum / prior opportunity sum, constructor labels), Q3 given Q2 (e = Q3 mean / Q2 mean), conditional Normal(n e, n v), v on earlier seasons;
   wall 8 WR TDs given receptions, raw rate Poisson(k s / n) (support not shown).  Null: the dependent stat's F6 v1 marginal (bounding-count marginal identical in both,
   cancels).  Dispersion r fit on rows with positive mean only (point mass otherwise).  Strata: undefined (label), identity_exception (realized n = 0, Y != 0; decision C),
   both forms impossible, only null impossible, only candidate impossible.  Gate on both-finite rows, paired by slate, tests 2021, 2023-25; EARNED iff gate AND candidate
   impossible on 0 non-exception defined rows; then harness v2 dependence.  The fallback-run outputs (f6_dependence / f6_dependence_efficiency / f6_dependence_touchdowns
   rows files and reports) and their three scripts are deleted after the new script succeeds (dirty data, not archived); wall 3 / 4 / 6 harness lines must be unchanged.

## DEPENDENCE WALLS 1, 7, 8 UNDER D - OUTCOME - Oct 3 2026 (f6_dependence_domain_report.txt; harness v2 dependence; wall 3 / 4 / 6 harness lines unchanged; wall 1 priors
   equal the support wall's; fallback-run outputs and scripts deleted)
Gate EARNED 8 / 8 (4 / 4 each; candidate impossible on 0 non-exception rows).  HARNESS PASS: wall 1 Q2 given Q1 +1.25817 (.0000); wall 7 Q3 given Q2 +0.78059 (.0000);
   wall 7 QB rushing yards given QB carries +0.59710 (.0000; 1 identity_exception).  HARNESS FAIL: wall 1 RB support law +0.98582+-0.01971 (FP null B .1825, tau/sigma
   .68; 16 null-impossible rows), TE +0.80074 (.1832, .46); wall 7 receiving yards RB +1.48746 (.1239), WR +1.47733 (.1290; 2 identity_exception), TE +1.55235 (.0676); wall
   8 WR +0.03154 (.0638; 218 both-impossible rows).
F6 v1 JOINT UNDER D: team targets -> player targets (wall 3 RB / WR / TE); team carries -> RB carries (wall 3); QB attempts -> completions (wall 1); completions -> passing
   yards, QB carries -> QB rushing yards (wall 7).  Independent: receptions RB / WR / TE, receiving yards RB / WR / TE, RB rushing yards, all TDs, the two teams' carries.
OBSERVATION: every harness failure above has 4 / 4 seasons and margins up to 50 s.e.; FP null B measures the gate's false-pass rate at the slice's season heterogeneity,
   not the observed margin against it (limitation recorded at line 38 and at the F6 harness).  It now decides most of the architecture.  Owner decision pending: compose
   under harness v2, or register a margin-aware harness first.

DECISION (reviewer, Oct 3 2026): (a) compose under harness v2.  Settled for v1: RB / TE catch dependence closed; RB / WR / TE receiving-yard dependence closed; WR TD
   dependence closed; QB completion, QB passing-yard, QB rushing-yard dependence earned.  Large native gain does not imply a stable mechanism.  The support law earned as a
   rate model but its dependence wall failed - receptions are drawn from their surviving marginal, not conditionally on realized targets.
## COMPOSITION UNDER D - REGISTRATION - Oct 3 2026 (report-only; first composition under D - the earlier composition used clipped ratios and the leak and is not a valid
   "previous composition" for the freeze rule)
Minimal graph: team targets -> player targets (share given team total; beta-binomial WR / TE, binomial RB); team carries -> RB carries (binomial); Q1 attempts (Poisson)
   -> Q2 binomial (p = Q2 mean / Q1 mean) -> Q3 Normal(n e, n v); QB carries -> QB rushing yards Normal(n e, n v); every other stat its F6 v1 independent marginal.  No
   floors, no leak: mean 0 -> point mass at 0; share and conditional laws dispatch on constructor labels (zero state -> point mass; QB carries zero -> 0 yards by identity);
   share p > 1 refuses the run; dispersion / precision fit on positive-mean rows.  Mechanical acceptance: summed composed means within 1% of frozen means for every composed
   stat.  F7 composed vs independent where forms differ; zero-state (point-mass) counts printed; F8; f8_vs_y.  Reading (reviewer): thin F8 tails after this -> boundary
   result (simple player-level structural dependence does not explain the fantasy-tail deficit); only then a residual / shared-state challenger.

## COMPOSITION UNDER D - OUTCOME - Oct 3 2026 (spine_compose_report.txt, f8_vs_y_report.txt): mechanical check PASS 7 / 7 (max rel -.0003).  Zero-state point masses
   (test rows): WR TDs 2864 / 6954, TE TDs 1275 / 4235, RB TDs 521, receptions RB 417 / WR 449 / TE 491, targets RB 350 / WR 334 / TE 376, QB rushing TDs 187, Q5 103, Q4 64,
   QB carries 8, Q1 0.  F7: targets CRPS composed vs independent RB +0.00254, WR +0.00837, TE +0.00325 (4/4); team -> player energy 4 / 4 pairs (4/4); RB carries +0.00018
   (1/4); QB rushing yards CRPS +0.55187, energy +0.57934 (4/4); Q2 CRPS -0.04267 (0/4), Q3 given Q2 CRPS -0.84903, energy -0.72729 (0/4) - chained on simulated completions
   that inherit Q1 Poisson narrowness (PIT sd .369 / coverage 58.0% -> .351 / 64.3% -> Q3 coverage 70.0%).
   F8 vs Y (16713 rows): center ALL +0.0510+-0.0108 (4/4), RB +0.0980 (4/4), TE +0.1292 (4/4), WR +0.0324 (3/4) not shown, QB -0.2071 (0/4); quantile score worse at every
   position (ALL -0.1045, 0/4); above p90 .150 (RB .140, WR .146, TE .164, QB .161), below p10 .110, PIT sd .304.
BOUNDARY RESULT (reviewer reading, registered before the run): after D, first-event support and harness v2, surviving player-level structural dependence does not explain
   the fantasy-tail deficit.  Stat-spine center beats Y overall, RB, TE; Y remains the better fantasy distribution.  A residual / shared-state challenger is now justified
   (not v1).  Stat-spine prospective clock: next untouched week = week 5 if frozen before its first game (Thu Oct 8 2026).  Owner decision pending: freeze now vs finish
   pre-freeze items (marginal first-event support, deviance FLOOR, spine.py unclear substitutions) first.

OWNER DIRECTION (Oct 3 2026): no freeze now - forecasting refinements continue using all data available.  DEFINITION (for the record): a freeze locks the recipe (terms,
   forms, links, fitting procedures), not the data - a frozen forecaster still refits each week on everything available; its purpose is a clean prospective test on games
   not yet played, since every wall chose forms by scoring the same historical seasons (historical scores are somewhat optimistic).  The prospective test starts only when
   the owner calls it; refinements can be scored on those future weeks alongside it.  The week-5 deadline framing is withdrawn.
NEXT: MARGINAL FIRST-EVENT SUPPORT for season-to-date count terms (RB / TE targets, receptions RB / WR / TE, WR TDs, Q1, Q4, Q5, QB carries): Gamma-Poisson predictive
   negative binomial(a + s, (b + g) / (b + g + 1)) from constructor sufficient statistics vs current F6 v1 marginal; non-sum zero sources (WR targets, RB carries: F2 x
   recency share; RB / TE / QB rushing TDs: hierarchical) listed separately.  The prior moves the mean (rate shrinkage) - scored and harnessed as a model change.

## MARGINAL FIRST-EVENT SUPPORT WALL - REGISTRATION - Oct 3 2026
Slices: F5 targets RB, TE; F5 receptions RB, WR, TE; F5 TDs WR; Q1 attempts; Q4 passing TDs; Q5 interceptions; QB carries (season-to-date terms; sufficient statistics s =
   prior sum, g = prior games from spine_sufficient).  Baseline: F6 v1 marginal around s / g (negative binomial for F5 receptions WR, Q5, QB carries with r on earlier seasons'
   positive-mean rows; Poisson otherwise).  Candidate: Gamma(a, b) prior on the per-game rate -> one-game predictive negative binomial(a + s, (b + g) / (b + g + 1)); prior
   mean on a geometric grid .5-2 x the pooled per-game rate of earlier seasons (41 points), b on logspace(-1, 2.5, 36) games; maximum likelihood on earlier seasons; grid
   edges flagged.  Gate: both-finite rows, paired by slate, tests 2021, 2023-25; baseline-impossible rows counted.  Acceptance: candidate finite on every row.  Reported:
   mean bias of both forms (the prior moves the mean), candidate PIT.  Rows to proj/f6_rows_marginal_support.csv.gz; harness v2 F6 mode re-run, earlier slices unchanged.
   Consumer: composition.  Out of scope (non-sum zero sources): F5 targets WR, F5 carries RB (F2 x recency share), F5 TDs RB / TE, QB rushing TDs (hierarchical).

## MARGINAL FIRST-EVENT SUPPORT WALL - OUTCOME - Oct 3 2026 (f6_marginal_support_report.txt; harness v2 F6 mode, earlier slices unchanged; candidate finite on every row of
   all 10 slices).  HARNESS PASS: F5 targets TE +0.02827+-0.00497 (4/4; .0000; bias -.206 -> -.109; prior mean 4.5-4.7, b .32); Q5 interceptions +0.02824+-0.01149 (4/4;
   .0000; bias -.024 -> -.013; b 25-63).  HARNESS FAIL: Q1 attempts +0.45231+-0.06236 (4/4; .0673), F5 targets RB +0.03205 (.1259), F5 receptions RB +0.02073 (.1297), TE
   +0.01111 (.0645).  NOT SHOWN: F5 receptions WR (2/4), F5 TDs WR -0.02781 (0/4), Q4 (2/4), QB carries (3/4).  First-event support matters selectively, not universally.
CORRECTIONS (to the reviewer summary, from the numbers): (1) the earned Gamma-Poisson predictive has mean (a + s) / (b + g), not s / g - promotion changes the mean (TE
   targets, Q5); pairing its shape with the old mean would be an untested hybrid.  (2) TE targets are composed through wall 3 (share given team total, p = frozen F5 mean /
   F2 mean); the TE marginal promotion changes only the independent comparison arm unless wall 3's p is changed (untested).  Q5 is drawn from its marginal - its promotion
   enters composition.
GAP UNDER D: verdicts underneath the composition were reached with semantic floors still in place - wall 3 (f6_dependence_team: clip on player / team means and p), F6
   marginal walls (f6_count, f6_td, f6_rec, f6_share), wall 6 (f6_dependence_opponent).  Their re-runs under D have not been done.  Owner decision pending: compose now
   (floor-free composition step, floored verdicts beneath) vs re-run those walls under D first.

DECISION (reviewer, Oct 3 2026): (b) re-run every still-active floored verdict under D before composition.  RULE: an earned child cannot silently consume a newly promoted
   parent unless that exact combination was tested (TE targets support is an earned marginal law, not a wall 3 input; Q5 enters composition through its full earned
   predictive, mean included).  Order: re-runs -> corrected verdict table -> ownership conflicts resolved -> first genuinely floor-free composition -> F7 -> F8 vs Y ->
   freeze vs challenger clock.
## FLOORED VERDICTS UNDER D - REGISTRATION - Oct 3 2026
Scripts: f6_count, f6_td, f6_rec (mean clip removed; r fit on positive-mean rows), f6_share (share clip removed; p = 0 / 1 evaluated as a point mass; phi fit on interior
   shares), f6_dependence_team / wall 3 (player-mean, team-mean and p clips removed; p > 1 refuses; zero share -> point mass; r / phi on positive-mean / interior rows),
   f6_dependence_opponent / wall 6 (team-mean clips removed - inert, report must reproduce byte-identical).  Per slice: strata both impossible / only baseline impossible /
   only candidate impossible; gate on both-finite rows; any candidate-only-impossible row blocks earning (slice omitted from the harness rows, marked BLOCKED).  Harness v2
   F6 and dependence modes re-run (per-slice seeds; only re-run slices can change).  Every changed verdict accepted.

## FLOORED VERDICTS UNDER D - OUTCOME - Oct 3 2026: report diffs confined to the re-run slices; wall 6 reproduced byte-identical (team-mean floors inert); no slice BLOCKED
   (every previously floored zero-mean row landed in both-impossible: targets RB 58 / WR 63 / TE 69, WR TDs 229, ...).  Changed verdicts: wall 3 F5 targets given team
   targets RB PASS -> FAIL (+0.05072, FP null B .0652), TE PASS -> FAIL (+0.09647, .1248), F5 carries given team carries RB PASS -> NOT SHOWN (-0.00490, 2/4); F4 target_share
   TE beta-binomial PASS -> FAIL (+0.04360, .0646).  Unchanged direction: wall 3 WR PASS (+0.12380, .0000); F4 target_share WR beta-binomial PASS; negative binomial PASS for
   F5 targets WR, F5 receptions WR, QB carries, Q2, Q5 (+0.00918); FAIL for F5 carries RB, F5 targets RB / TE, Q1 (.0632), F5 receptions RB / TE (TE .1207); F4 RB shares FAIL;
   TD negative binomials NOT SHOWN except Q5.
## CORRECTED VERDICT TABLE (all under D, harness v2) - Oct 3 2026
Team: targets, attempts negative binomial; carries Poisson.  Targets: RB Poisson; WR via wall 3 (beta-binomial share of the team-targets draw, p = frozen F5 mean / F2 mean);
   TE Gamma-Poisson support law (earned marginal; owns TE targets since wall 3 TE failed).  F5 carries RB Poisson.  Receptions: RB Poisson, WR negative binomial, TE Poisson.
   TDs Poisson (F5 TDs RB / WR / TE, Q4, QB rushing TDs).  Q5 Gamma-Poisson support law (predictive mean included).  QB chain: Q1 Poisson -> Q2 binomial (wall 1) -> Q3 given
   Q2 (wall 7); QB carries negative binomial -> QB rushing yards given QB carries (wall 7).  Yards: F6 v1 forms.  Ownership: TE targets drawn from their marginal (support law;
   no hybrid); WR targets by wall 3 as tested (WR negative binomial is the comparison arm only); Q5 full support predictive; wall 1 consumes Q1's standing Poisson (not a
   newly promoted parent).
## FLOOR-FREE COMPOSITION - REGISTRATION - Oct 3 2026 (report-only): spine_compose.py rebuilt from the corrected verdict table; support-law priors fit by the marginal support
   wall's procedure on its frame (printed as witness); mechanical check (1%) on composed WR targets, Q2, Q3, QB rushing yards; support-law mean shift reported; F7 composed vs
   independent where forms differ (TE targets, Q5 vs previous F6 v1 baseline); F8 vs Y against the last corrected F8 (above p90 .150, below p10 .110, PIT sd .304).

## FLOOR-FREE COMPOSITION - OUTCOME - Oct 3 2026: support priors equal the marginal support wall's; mechanical check PASS 4 / 4 (max rel +.0005); support-law mean shift TE
   targets +4.19%, Q5 +.75% (intended).  F7 vs comparison form: WR targets +0.00838, TE targets (support) +0.01243, Q5 (support) +0.03769, QB rushing yards +0.57066 (4/4
   each); Q2 -0.04139, Q3 -0.71287 (0/4); energy Q2 with Q3 -0.59129 (0/4).  F8 vs Y: center ALL +0.0498+-0.0105 (4/4), RB +0.0972, TE +0.1305 (4/4), WR +0.0331 (3/4), QB
   -0.2249 (0/4); quantile score ALL -0.1048 (0/4); above p90 .150, below p10 .110, PIT sd .304 - unchanged from the last corrected F8 (.150 / .110 / .304).
BOUNDARY CONFIRMED: the fantasy-tail miss does not come from zero-support handling or the tested structural identities.  COMPOSITION-LEVEL BOUNDARY: conditionals earned on
   the realized parent (wall 1 Q2 given Q1, wall 7 Q3 given Q2) degrade when chained on a miscalibrated simulated parent (Q1 Poisson PIT sd .369, coverage 58.3% -> Q2 64.2%
   -> Q3 70.3%); the chained combination was never tested as such; root Q1 dispersion (negative binomial .0632, support .0673 - both just over the line).
NEXT (D, owner direction to keep refining): deviance FLOOR .01 in spine.py / harness.py dev() - every TD-type spine verdict (F5 TDs RB / WR / TE, Q4, Q5, QB rushing TDs)
   was scored with it.

## DEVIANCE FLOOR - read Oct 3 2026 (spine harness rows, five test seasons; base 0 & y > 0 / v1 0 & y > 0 / both / v1-only): F5 TDs RB 179 / 30 / 30 / 0; WR 283 / 96 / 75 /
   21; TE 201 / 67 / 64 / 3; Q4 24 / 12 / 9 / 3; Q5 46 / 0 / 0 / 0; QB rushing TDs 74 / 19 / 18 / 1.  Under D: TE TDs (hierarchical, currently PASS) and QB rushing TDs
   (PASS) BLOCKED (v1-only impossible: hierarchical mean 0 with zero red-zone opportunities so far, TD scored, season-to-date base positive); WR TDs and Q4 blocked
   (already season-to-date); RB TDs and Q5 re-scored on finite rows.
## DEVIANCE FLOOR UNDER D - REGISTRATION - Oct 3 2026 (step 1 of 2)
harness.py: dev() without floor; run_slice strata first - any v1-only-impossible row -> BLOCKED; otherwise the slice runs on both-finite rows; strata line printed only when
   rows were excluded (MAE-term lines must stay byte-identical; seeds unchanged).  spine.py: dev() without floor (also changes Q5 v1 kr selection - Q5 v1 is not a freeze
   form); self-check re-scores the six deviance terms on both-finite rows with strata, labelled D RE-SCORE, outside the count.  Acceptance: 14 / 14 MAE figures reproduce;
   issue path 33 / 33; harness spine diff confined to the six deviance terms and the header.  Step 2: re-record the six REC figures, record verdicts, propagate freeze forms.

## DEVIANCE FLOOR UNDER D step 1 - OUTCOME - Oct 3 2026: 14 / 14 MAE figures reproduced; issue path 33 / 33; harness spine diff confined to the six deviance terms.  Re-scores
   on both-finite rows (base / v1): F5 TDs RB .6511 / .6594, WR .5014 / .5267, TE .3720 / .3924; Q4 1.1188 / 1.0735; Q5 1.1936 / 1.0898; QB rushing TDs .4640 / .5001.  Harness:
   F5 TDs RB -0.00988+-0.00622 (1/5) gate fail; WR BLOCKED (21), TE BLOCKED (3), Q4 BLOCKED (3), QB rushing TDs BLOCKED (1); Q5 +0.10365+-0.01949 (5/5) HARNESS PASS.
ANTI-PATTERN: every TD-rate mechanism (hierarchical RB / TE / QB rushing TDs, Q4) collapsed once the .01 deviance floor was removed - the floor manufactured those verdicts.
Q5: v1 = Q1 v1 attempts x shrunk interception rate - its Q1 parent now enters at season-to-date, so Q5 is recomputed on the Q1 season-to-date parent and tested; and its kr
   selection without the floor can be degenerate (one +inf row makes every candidate's nanmean inf) - selection moves to rows with positive prediction (mechanical; v1 and
   parent alike).  Q5 re-score stays pending.  The Q5 support law keeps owning Q5 in composition until a registered comparison with any earned Q5 mean.
## DEVIANCE FLOOR UNDER D step 2 - REGISTRATION - Oct 3 2026: spine.py REC re-recorded for F5 TDs RB / WR / TE, Q4, QB rushing TDs (both-finite means above); self-check
   compares deviance terms on both-finite rows, Q5 pending; kr selected on positive-prediction rows; new term "Q5 interceptions (Q1 season-to-date parent)".  freeze.py:
   season-to-date adds F5 TDs RB, TE, QB rushing TDs.  Acceptance: self-check 19 / 19 + 1 pending; issue path 34 / 34; harness spine diff confined to Q5, the new term, header;
   f6_td and harness F6 diffs confined to the RB / TE / QB rushing TD slices.

## DEVIANCE FLOOR UNDER D step 2 - OUTCOME - Oct 4 2026: spine 150,877 rows over 22 terms; self-check 19 / 19 + Q5 pending; issue path 34 / 34 ("Q5 interceptions (Q1
   season-to-date parent)" max |diff| 0).  Q5 D re-score with kr selected on positive-prediction rows 1.1936 / 1.0898 - unchanged, the selection was not degenerate.
   Harness spine: "Q5 interceptions (Q1 season-to-date parent)" +0.10139+-0.01847 (5/5), FP null B 0.0000, HARNESS PASS (baseline-only impossible 46 excluded); no other
   line changed.  f6_td around season-to-date: F5 TDs RB -0.00012 (1/4) and QB rushing TDs +0.00213 (3/4) not earned; F5 TDs TE negative binomial +0.00121+-0.00059 (4/4)
   earned, harness F6 PASS (FP null B 0.0000); QB rushing TDs harness F6 FAIL (0.1233).  The Q5 support law keeps owning Q5 in composition until the registered comparison.
MECHANICAL: f6_td printed "mean = v1" for F5 TDs RB / TE and QB rushing TDs while apply_freeze supplied season-to-date - FREEZE_BASE was a second hand-kept list beside
   freeze.SEASON_TO_DATE.
## DEVIANCE FLOOR UNDER D step 3 - REGISTRATION - Oct 4 2026: spine.py REC Q5 re-recorded 1.1936 / 1.0898; PENDING_RERECORD, its pending branch and the nre counter
   deleted (no term remains pending).  f6_td.py: FREEZE_BASE deleted; the slice mean is v1 after apply_freeze; the label is derived from freeze.SEASON_TO_DATE.
   Acceptance: self-check 20 / 20; issue path 34 / 34; spine_rows and f6_rows_td content identical; f6_td report differs only in "(mean = ...)" labels; zero uses of
   FREEZE_BASE, PENDING_RERECORD, nre, f6_td col.
WORK ORDER (appended): spine.py issue path disagrees with freeze.py - the week file writes season-to-date only for WR TDs (td_pb) and interceptions (passing_interceptions_pb)
   while freeze.SEASON_TO_DATE also holds F5 TDs RB / TE, QB rushing TDs, Q1, Q4 and freeze.PARENT holds Q2 / Q3 (spine.py lines 177, 179, 190 label).

## DEVIANCE FLOOR UNDER D step 3 - OUTCOME - Oct 4 2026: self-check 20 / 20 (Q5 interceptions QB 1.1936 / 1.0898 PASS on 1873 both-finite rows); issue path 34 / 34;
   spine_rows and f6_rows_td content identical; f6_td report changed only in six "(mean = ...)" labels, all now season-to-date; zero uses of FREEZE_BASE, PENDING_RERECORD,
   nre, f6_td col.
## Q5 EARNED MEAN COMPATIBILITY WALL - REGISTRATION - Oct 4 2026: f6_q5_mean.py.  Owner: the Q5 Gamma-Poisson support law, the procedure of f6_marginal_support.py on its
   frame (spine_sufficient QB rows x spine "Q5 interceptions" y), prior fit on earlier seasons.  Candidate: negative binomial around "Q5 interceptions (Q1 season-to-date
   parent)" (harness spine PASS +0.10139), r over the F6 grid including Poisson, fit on earlier-season rows with positive mean.  "Q5 interceptions" v1 is not a candidate:
   it consumes Q1 v1 attempts and Q1 did not pass harness v2 (propagation rule); it stays a spine record.  Rows: the owner's frame, test seasons 2021, 2023-25; the
   candidate mean joined on season / week / key, never filled - any row the owner forecasts and the candidate does not (undefined, or zero probability on the realized
   count) BLOCKS the candidate.  Reported stratum: rows with zero season-to-date attempts (where spine.py line 105 fillna(attempts_pb x li) could act).  Witness: the
   owner's per-slate scores and row counts reproduce proj/f6_rows_marginal_support.csv.gz Q5 within 1e-9, else no verdict.  Gate p.passes_gate on per-slate owner minus
   candidate -log score; harness f6 at ladder L 1 through proj/f6_rows_q5_mean.csv.gz; no existing harness verdict line may change.  Decision: the candidate earns only
   with gate and harness pass, after which composition may pair Q5 with the negative binomial around the parent mean (recompose, work order); otherwise the support law
   keeps Q5.
WORK ORDER (appended): the support-law procedure exists in three copies (f6_marginal_support.py, spine_compose.py support_fit, f6_q5_mean.py) - one producer.

## Q5 EARNED MEAN COMPATIBILITY WALL - OUTCOME - Oct 4 2026: witness PASS (52 slates, 1491 / 1491 rows, max |slate-mean diff| 2.22e-16).  Strata: rows 1531, gate 1531,
   no impossible or undefined row on either side; 17 zero season-to-date attempt rows, candidate state zero on all 17 with finite loss - spine.py fillna(attempts_pb x li)
   did not act on this frame.  Gate: support law -log score 1.0932, negative binomial around the Q1 season-to-date parent mean 1.1000; gain -0.00692+-0.00839 (1/4) NOT
   SHOWN; candidate r 2021 inf, 2023 20.0, 2024 15.8, 2025 7.9; mean bias support law -0.013, parent mean -0.027.  Harness F6: gate fail, FP null B 0.0000, HARNESS FAIL;
   no existing verdict line changed (header rows 194574 -> 196105).  Registered decision: the support law keeps Q5.
## SUPPORT-LAW ONE PRODUCER - REGISTRATION - Oct 4 2026: support.py owns the Gamma-Poisson support law under the tree's established names - FACTOR, B_GRID,
   support_frame (constructor sufficient statistics x unfrozen spine y), support_fit (grid maximum likelihood, edge flag; pooled rate from what the caller passes),
   support_predictive, support_mean, support_draws.  f6_marginal_support.py, f6_q5_mean.py and spine_compose.py import it; their copies (FACTOR, B_GRID, prior loops,
   support_fit, support_frame, support_draws, inline predictive / mean, f6_marginal_support K) are deleted.  A first attempt named the frame "frame" - guard refused it
   (p.py owns frame) and the snapshot was restored whole; its before / after outputs were identical 8 / 8.  Acceptance: each script run before and after on the same
   inputs - f6_marginal_support report and rows, f6_q5_mean report and rows, spine_compose report, rows, pairs, f8_rows content identical; no definition or bare call of
   the deleted names in the three importers; guard passes.
WORK ORDER (appended): the negative binomial fit (nb, nb_fit, GRID / RGRID / PGRID = logspace(0, 4, 41) + inf) is repeated in f6_count, f6_td, f6_rec, f6_team, f6_share,
   f6_dependence_team, f6_dependence_opponent, f6_dependence_domain, f6_marginal_support, f6_q5_mean, spine_compose - one producer.

## SUPPORT-LAW ONE PRODUCER - OUTCOME - Oct 4 2026: support.py (support_frame, support_fit, support_predictive, support_mean, support_draws) imported by
   f6_marginal_support, f6_q5_mean, spine_compose; before / after on the same inputs 8 / 8 outputs identical; no definition or bare call of the deleted names in the
   importers; guard PASS (the first attempt's name "frame" collided with p.py and was restored whole).
## ISSUE PATH FREEZE FORMS - REGISTRATION - Oct 4 2026: spine.py issue mode wrote season-to-date only for WR TDs (td_pb) and interceptions (passing_interceptions_pb)
   while freeze.py SEASON_TO_DATE also holds F5 TDs RB / TE, QB rushing TDs, Q1, Q4 and PARENT holds Q2 / Q3 - the dry-run week file carried means the harness had not
   passed, and the issue-path check compared raw v1 so it could not see it.  Remedy: TERM_COLUMNS (base / v1 columns of history()'s mk rows); freeze_column(term,
   position) derived from freeze.SEASON_TO_DATE and freeze.PARENT; week_rows(T, U) the one producer of the week file's player values; issue mode writes week_rows; the
   self-check adds FREEZE-FORM ISSUE CHECK - week_rows at 2025 w10 against apply_freeze of the history rows for F5 TDs RB / WR / TE and the eight QB outputs - inside
   ACCEPTED.  PATH labels and docstring corrected.  Acceptance: self-check 20 / 20; issue path 34 / 34; freeze-form issue check 11 / 11; spine_rows content identical;
   week file before / after shown column by column.
WORK ORDER (appended): the term -> column mapping is written three times in spine.py (history mk rows, self-check MAP, TERM_COLUMNS) - one table; PATH labels are prose
   beside freeze.py - derive them.

## ISSUE PATH FREEZE FORMS - OUTCOME - Oct 4 2026: self-check 20 / 20; freeze-form issue check 11 / 11 (F5 TDs RB 77, WR 121, TE 77 rows; eight QB outputs 28 rows each;
   max |diff| 0); issue path 34 / 34 ACCEPTED; spine_rows content identical.  Week file 2025 w10 (453 rows) before / after: tds changed 136 of 332 (mean .196 -> .197),
   attempts 36 of 37 (27.587 -> 26.184), completions 36 of 36 (18.568 -> 17.580), passing yards 36 of 36 (204.122 -> 193.641), passing TDs 35 of 37 (1.254 -> 1.313),
   rushing TDs 31 of 37 (.180 -> .178); interceptions, carries, rushing yards, targets, receptions, receiving yards, team targets unchanged.
## MARGINAL FIRST-EVENT SUPPORT, TD TERMS - REGISTRATION - Oct 4 2026: f6_marginal_support.py SLICES append F5 TDs RB (td_ps), F5 TDs TE (td_ps), QB rushing TDs QB
   (rushing_tds_ps) - season-to-date sum terms since DEVIANCE FLOOR UNDER D step 2.  Baseline = F6 v1 marginal around s / g: RB Poisson, TE negative binomial (earned,
   now in BASE_NEGATIVE_BINOMIAL), QB rushing TDs Poisson (negative binomial harness FAIL 0.1233).  The TE slice is the registered comparison of the earned negative
   binomial with the support law.  Existing slices must reproduce (rows content and report lines identical; new slices appended).  Harness F6 at L 1; no existing verdict
   line may change.  Decision: the support law replaces a slice's v1 marginal only with gate pass, harness pass and ACCEPTANCE (candidate finite on every row) PASS;
   otherwise the v1 marginal stays.  Composition follows at the recompose (work order).

## MARGINAL FIRST-EVENT SUPPORT, TD TERMS - OUTCOME - Oct 4 2026: existing slices reproduced (35,873 rows identical; report lines appended only); new rows 9,418.
   F5 TDs RB: baseline Poisson -log score .5647, Gamma-Poisson .5964, gain -0.03270+-0.00247 (0/4) NOT SHOWN, harness FAIL (FP null B 0.0000); gate 3874, zero
   history 1353, baseline impossible 138.  F5 TDs TE: negative binomial .2677 vs .3028, gain -0.03599+-0.00259 (0/4) NOT SHOWN, harness FAIL (0.0000); gate 4067, zero
   history 2250, baseline impossible 168.  QB rushing TDs: Poisson .3426 vs .3784, gain -0.03531+-0.00429 (0/4) NOT SHOWN, harness FAIL (0.0619); gate 1477, zero
   history 684, baseline impossible 54.  ACCEPTANCE PASS on all three; no existing harness verdict changed.  Registered decision: the v1 marginals stay.
GAP: the gate excludes baseline-only-impossible rows by construction - the v1 marginal is point mass 0 on zero-history rows where TDs occurred (RB 138, TE 168, QB 54).
## DECISION B - ZERO-HISTORY TD CALIBRATION WALL - REGISTRATION - Oct 4 2026 (owner / reviewer: a support defect, a native-stat question ahead of F8):
   f6_zero_history_td.py, diagnostic only.  Population: per term / position (F5 TDs RB, F5 TDs TE, QB rushing TDs QB), test-season rows (2021, 2023-25) of the support
   frame with season-to-date TD sum s = 0.  Forecast: what the frozen producer emits - F6 v1 marginal around s / g (RB Poisson; TE negative binomial, r fit on earlier
   seasons; QB rushing TDs Poisson).  Rows with g = 0 (undefined mean) reported separately, never treated as zero.  Report: rows, Y > 0 count and share, predicted
   aggregate P(Y > 0), calibration gap, standard error sqrt(sum p(1 - p)) / n, exact support violations (P(Y > 0) = 0 and Y > 0), per-season shares, randomized PIT
   F(y - 1) + U pmf(y) (defined on every row with a forecast; no epsilon), share of PIT = 1.  Labels: SUPPORT-MISS if any exact support violation; else COHERENT if
   |gap| <= 2 SE (gap 0 when SE 0); else UNRESOLVED.  Witness: zero-history and baseline non-finite counts reproduce the marginal support wall (RB 1353 / 138,
   TE 2250 / 168, QB 684 / 54), else no verdict.  The wall cannot revise recorded TD verdicts and promotes nothing; a replacement law (Gamma-Poisson, hurdle, other)
   needs its own preregistered wall.  The recompose's F8 result carries the annotation "TD zero-history support unresolved" until a later wall resolves it.

## DECISION B - ZERO-HISTORY TD CALIBRATION WALL - OUTCOME - Oct 4 2026: witness 3 / 3 (RB 1353 / 138, TE 2250 / 168, QB 684 / 54); no g = 0 rows.  F5 TDs RB:
   predicted P(Y > 0) 0 on 1353 of 1353, realized 138 (.1020), support violations 138, PIT = 1 on 138 -> SUPPORT-MISS; per season .126 / .088 / .107 / .090.  F5 TDs
   TE: 0 on 2250, realized 168 (.0747), violations 168 -> SUPPORT-MISS; .075 / .076 / .075 / .073.  QB rushing TDs: 0 on 684, realized 54 (.0789), violations 54 ->
   SUPPORT-MISS; .118 / .059 / .065 / .085.  Recorded TD verdicts stand; nothing promoted; a replacement law needs its own preregistered wall.
## RECOMPOSE - REGISTRATION - Oct 4 2026: spine_compose.py F5 TDs TE draws from its earned F6 v1 negative binomial around season-to-date (f6_td, harness PASS; r refit on
   earlier seasons of the composition frame), Poisson kept as its F7 comparison form - parent / child rule (an earned distribution is used only as tested); F5 TDs RB / WR,
   Q4, QB rushing TDs stay Poisson.  ZERO-STATE section adds, per point-mass-0 component, realized > 0 on those rows (support violations).  f8_vs_y.py carries the TD
   ZERO-HISTORY SUPPORT annotation computed from code: per TD component of F8 (F5 TDs RB / WR / TE, Q4 passing TDs, QB rushing TDs) the Decision B label from
   proj/f6_zero_history_td_rows.csv.gz or "not diagnosed", point-mass-0 rows and support violations from apply_freeze state labels, per position the above-p90 share on
   violation rows vs the rest; status "unresolved" while any component is SUPPORT-MISS or not diagnosed.  Baseline: original spine_compose / f8_vs_y on today's inputs.
   Acceptance: mechanical check PASS; every F8 row joins its TD spine rows (else refused); reports shown before / after.  Draw streams shift after the first TE draw, so
   other composed lines move by Monte Carlo noise.
WORK ORDER (appended): Decision B did not diagnose F5 TDs WR or Q4 passing TDs - also season-to-date point masses at s = 0.

## RECOMPOSE - OUTCOME - Oct 4 2026: mechanical check PASS (WR targets +.0002, Q2 +.0002, Q3 -.0000, QB rushing yards -.0001); F5 TDs TE composed negative binomial
   CRPS .1249 vs Poisson comparison .1256, gain +0.00068+-0.00016 (4/4); other lines move by Monte Carlo noise.  ZERO-STATE support violations (point-mass-0 rows
   with realized > 0): F5 targets RB 58 / 350, receptions RB 64 / 417, carries RB 27 / 240, TDs RB 138 / 1353; targets WR 63 / 334, receptions WR 81 / 449, TDs WR
   229 / 2864; targets TE 69 / 376, receptions TE 83 / 491, TDs TE 168 / 2250; Q4 20 / 64; QB carries 4 / 8; QB rushing TDs 53 / 670.  F8 vs Y: center ALL
   +0.0327+-0.0108 (4/4), RB +0.0467 (3/4), TE +0.0976 (4/4), WR +0.0328 (3/4), QB -0.1882 (0/4); quantile score ALL -0.1156 (0/4); below p10 / above p90 .109 / .155;
   PIT sd .306.  Annotation: TD zero-history support unresolved (RB, TE, QB rushing SUPPORT-MISS; WR, Q4 not diagnosed); F8 rows with a point-mass-0 TD component and a
   realized TD: QB 73, RB 138, WR 229, TE 168, ALL 608; above F8 p90 on those .507 / .891 / .843 / .893 / .827 vs rest .142 / .126 / .121 / .143 / .130 (the rest mixes
   rows with and without a realized TD - confounded).
LABEL DEFECT: the ZERO-STATE section counts the frozen mean's state, not the composed law - F5 targets TE is drawn from the support law (positive mass at s = 0), so its
   69 / 376 are not point masses of the composed forecast.
## TAIL CONTRAST - REGISTRATION - Oct 4 2026: f8_vs_y.py adds, per position, among rows with a realized TD on any TD component: above-F8-p90 share on point-mass-0 TD rows
   vs positive-forecast TD rows; the share on rows with no realized TD; and the count of above-p90 rows that are point-mass-0 TD rows.  Descriptive; re-examines "BOUNDARY
   CONFIRMED" (recorded Oct 3, before Decision B); promotes nothing.  Acceptance: existing report lines unchanged.
WORK ORDER (appended): ZERO-STATE label measures the frozen mean, not the composed law (F5 targets TE); point-mass-0 support violations also occur for targets,
   receptions, carries (RB, WR, TE) and QB carries - beyond Decision B's TD scope.

## TAIL CONTRAST - OUTCOME - Oct 4 2026: above F8 p90 among rows with a realized TD on a point-mass-0 component / a realized TD with positive forecast / no realized TD:
   QB 73 .507 / 1081 .180 / 360 .028; RB 138 .891 / 872 .393 / 3002 .048; WR 229 .843 / 971 .471 / 5754 .062; TE 168 .893 / 352 .523 / 3713 .107; ALL 608 .827 /
   3276 .360 / 12829 .071.  Above-p90 rows that are point-mass-0 TD rows: QB 37 / 242, RB 123 / 611, WR 193 / 1008, TE 150 / 733, ALL 503 / 2594.
CORRECTION: "BOUNDARY CONFIRMED" (Oct 3) does not hold.  The F8 upper-tail miss is TD-event-driven (no-TD rows .071 above p90); point-mass-0 TD rows carry 503 of 2594
   exceedances at .827 vs .360 for positive-forecast TD rows - the zero-history support defect is a part of the miss, not the whole (residual: positive-forecast TD rows,
   tail challenger).
## SPINE SUBSTITUTIONS UNDER D - REGISTRATION - Oct 4 2026: spine.py max(sum, 1) in the three pooled red-zone TD rates (lines 87, 98, 107) and the unguarded pooled
   interception rate li (line 100) become pooled_rate(numerator, denominator, what), refusing a non-positive denominator instead of substituting 1; fillna(attempts x li)
   on the Q5 kr selections and means (lines 102, 103, 105, 106) is deleted - an undefined interception rate stays undefined (constructor state).  Acceptance: self-check
   20 / 20, freeze-form issue check 11 / 11, issue path 34 / 34, spine_rows content identical (the substitutions never acted); if spine_rows changes, the changed rows
   are printed per term and the snapshot restored - the substitutions acted and the change is not mechanical.  Box-score fillna(0.0) (lines 48, 59) is measured
   (missing-value census of played rows), not changed.

## SPINE SUBSTITUTIONS UNDER D - OUTCOME - Oct 4 2026: spine_rows content identical (the floors and the league-rate fallback never acted); self-check 20 / 20,
   freeze-form issue check 11 / 11, issue path 34 / 34 ACCEPTED.  Census of played rows: skill 5037 of 36,668 and QB 104 of 4073 have the whole box score missing at
   once (no partly missing row); red-zone columns never missing.
## BOX-SCORE ZEROS - EVIDENCE - Oct 4 2026: on every whole-row-missing played row (skill 5037, QB 104): offense_snaps > 0 and snap_share > 0 (on the field), red-zone
   columns 0, dk_points exactly 0 (complete rows: dk_points 0 on 5524 skill / 65 QB, > 0 on 25,889 / 3723); 694 - 914 skill rows per season (2026: 141 / 1107).
   Reading: on the field with no recorded event - a recorded zero, not a missing record.
## BOX-SCORE ZEROS UNDER D - REGISTRATION - Oct 4 2026: spine.py lines 47 - 48 / 59 fillna(0.0) is replaced by box_zero(rows, columns, what): a played row's box score
   is set to 0 only when it is wholly absent, offense_snaps > 0, dk_points == 0 and the red-zone columns are 0; a partly missing box score, a missing box score without
   that on-field evidence, or a missing red-zone column refuses.  Acceptance: self-check 20 / 20, freeze-form issue check 11 / 11, issue path 34 / 34, spine_rows
   content identical.

## BOX-SCORE ZEROS UNDER D - OUTCOME - Oct 4 2026: spine_rows content identical; self-check 20 / 20, freeze-form issue check 11 / 11, issue path 34 / 34 ACCEPTED.
## ZERO-HISTORY STATE EQUIVALENCE - READ - Oct 4 2026 (spine rows, all seasons, after apply_freeze): state_v1 zero <=> constructor sum 0 on every row - F5 targets WR 400
   zero rows (realized > 0 on 81), F5 carries RB 329 (36), F5 targets RB 415 (70), F5 targets TE 464 (87); no zero-state row with a positive sum, no zero sum without
   zero state.  The non-sum means (F2 x recency share) are zero exactly when the player's prior count is zero.
## ZERO-HISTORY CALIBRATION, COUNT TERMS - REGISTRATION - Oct 4 2026: Decision B's diagnostic extended; one producer f6_zero_history.py replaces f6_zero_history_td.py
   (deleted with its report and rows; f8_vs_y reads proj/f6_zero_history_rows.csv.gz).  Slices: F5 TDs RB / WR / TE, Q4 passing TDs, QB rushing TDs, F5 targets RB / WR,
   F5 carries RB, F5 receptions RB / WR / TE, QB carries - every point-mass-0 component of the composition's ZERO-STATE section except F5 targets TE (support law).
   Forecast: the frozen producer - apply_freeze state_v1 zero with v1 = 0; at mean 0 every registered form (Poisson, negative binomial, binomial / beta-binomial share)
   is a point mass at 0.  s = 0 <=> state_v1 zero (v1 = 0) is checked per slice on test-season rows (mismatch -> no verdict).  Report fields and label rule as Decision B;
   PIT for a point mass at 0 is U on Y = 0 and 1 on Y > 0.  Witness: the three Decision B slices reproduce rows / violations (RB 1353 / 138, TE 2250 / 168, QB rushing
   684 / 54).  f8_vs_y report may change only in its annotation header (WR TDs and Q4 become diagnosed).  Diagnostic only - the diagnosis part of work order lines 9
   (non-sum first-event support), 14 and 16; replacement laws remain separate preregistered walls.

## ZERO-HISTORY CALIBRATION, COUNT TERMS - OUTCOME - Oct 4 2026: witness 3 / 3 (Decision B slices reproduced); state equivalence held on every test row of all 12
   slices; all 12 SUPPORT-MISS (predicted P(Y > 0) = 0 on every s = 0 row) - rows / violations / share: F5 TDs RB 1353 / 138 / .1020, WR 2864 / 229 / .0800, TE 2250 /
   168 / .0747; Q4 81 / 21 / .2593; QB rushing TDs 684 / 54 / .0789; F5 targets RB 350 / 58 / .1657, WR 334 / 63 / .1886; F5 carries RB 240 / 27 / .1125; F5 receptions
   RB 417 / 64 / .1535, WR 449 / 81 / .1804, TE 491 / 83 / .1690; QB carries 12 / 4 / .3333.  f8_vs_y changed only its annotation header (WR TDs, Q4 now SUPPORT-MISS);
   f6_zero_history_td.py and its outputs deleted.
## ORDER DECISION B - Oct 4 2026 (owner / reviewer): the zero-history replacement wall (work order line 13) advances ahead of Q1 dispersion because SUPPORT-MISS holds for
   all 12 point-mass-0 components; after it, Q1 dispersion, then the tail challenger; nothing else reordered.
## ZERO-HISTORY REPLACEMENT WALL - REGISTRATION - Oct 4 2026: f6_zero_history_replacement.py, one procedure, 12 per-component verdicts.  Domain: s = 0 rows of the 12
   components (the population of proj/f6_zero_history_rows.csv.gz; witness: identical component set and per-component test-row and event counts, else no verdict).
   Candidate: negative binomial predictive, mean = mean of Y over earlier seasons' s = 0 rows of the component, r by maximum likelihood over logspace(0, 4, 41) + Poisson
   on those rows; strict walk-forward per test season (2021, 2023 - 25); no covariates.  A component with no earlier-season s = 0 rows or a training mean of 0 is
   UNRESOLVED (no substitute).  Primary gate: |realized share of Y > 0 - mean predicted P(Y > 0)| <= 2 SE, SE = sqrt(sum p(1 - p)) / n, pooled test rows.  Secondary:
   randomized PIT F(y - 1) + U pmf(y), mean within 0.5 +- 2 sqrt(1 / (12 n)) and variance within 1/12 +- 2 sqrt((1/80 - 1/144) / n).  PASS iff both, per component.
   Reported per component (and per season): n, events, mean predicted P(Y > 0), observed share, gap, SE, PIT mean / variance with tolerances, support violations.  No
   log-score comparison with the point mass (infinite loss on violations).  No rescue: a FAIL stays unresolved; no second family in this transaction.  s > 0 rows are not
   touched; a PASS enters composition only through an integration transaction in which every s > 0 row's composed law parameters are identical before / after.

## ZERO-HISTORY REPLACEMENT WALL - OUTCOME - Oct 4 2026: witness 12 / 12 (rows and events = f6_zero_history).  PASS: F5 TDs WR (n 2864; share .0800 vs predicted
   .0829, gap -.0029, 2 SE .0103; PIT .501 / .0848), F5 TDs TE (2250; .0747 vs .0743), Q4 passing TDs (81; .2593 vs .1797, gap +.0795 within 2 SE .0848), QB rushing
   TDs (684; .0789 vs .1018, gap -.0228 within .0231), F5 receptions TE (491; .1690 vs .1859), QB carries (12; .3333 vs .5212, gap -.1879 within .2868).  FAIL: F5 TDs RB
   (.1020 vs .1205, gap -.0185 beyond .0177; PIT pass), F5 targets RB (.1657 vs .2435; PIT pass), F5 targets WR (.1886 vs .3193; PIT fail), F5 carries RB (.1125 vs
   .2757; PIT fail), F5 receptions RB (.1535 vs .1931; PIT pass), F5 receptions WR (.1804 vs .2635; PIT fail).  Every FAIL over-predicts first-event probability.  r sits
   at the registered grid's lower edge (1.0) in most fits, PASS components included (WR TDs 2023 - 25, Q4, TE receptions, QB carries).  Reviewer: Q4 (n 81) and QB
   carries (n 12) are procedural PASSes with weak evidence.  FAILs stay unresolved; no rescue.
## ZERO-HISTORY INTEGRATION - REGISTRATION - Oct 4 2026: the wall writes proj/f6_zero_history_replacement_verdicts.csv (its report must reproduce byte-identical);
   spine_compose.py draws the s = 0 rows of PASS components from the wall's own parameters (proj/f6_zero_history_replacement_rows.csv.gz, exactly one (mean, r) per
   component and test season, else refused).  Every other row keeps its law and its draw call; per-row base / used law parameters are written to
   proj/spine_compose_params.csv.gz and every s > 0 row must have identical base / used parameters, else no rows are written.  QB carries (PASS) is not integrated: it is
   the parent of QB rushing yards given QB carries (wall 7), and that combination on s = 0 rows is untested - parent / child rule.  ZERO-STATE lines of integrated
   components are marked "not a point mass"; f8_vs_y derives integration from the params file and counts point-mass-0 TD rows only for non-integrated components.
   Composition, F7, F8 are measured; their results cannot revoke or rescue any wall verdict.  Next: Q1 dispersion.
WORK ORDER (appended): QB carries zero-history law with QB rushing yards given QB carries - a registered combination test before integration.  The six FAIL components
   over-predict first events (hurdle / zero-inflated mechanism) - a separate preregistered wall if pursued.  r at the registered grid's lower edge.

## ZERO-HISTORY INTEGRATION - OUTCOME - Oct 4 2026: wall verdicts CSV written (wall report and rows byte-identical); s > 0 invariance 24,872 rows, 0 law-parameter
   differences; integrated F5 TDs WR / TE, Q4, QB rushing TDs, F5 receptions TE; QB carries blocked (parent / child); six FAIL components unchanged.  F7: F5 TDs WR CRPS
   .1649 -> .1621 (bias -.000 -> +.037), TE TDs .1249 -> .1219 (vs Poisson +0.00379+-0.00054, 4/4), TE receptions .7556 -> .7514, Q4 .6291 -> .6265, QB rushing TDs
   .1508 -> .1482 (bias +.011 -> +.058).  F8 vs Y ALL: F8 mean 7.42 -> 7.61 (realized 7.61), above p90 .155 -> .142, quantile score gain -0.1156 -> -0.1103 (0/4),
   center absolute error gain +0.0327 (4/4) -> -0.0153 (1/4); WR center +0.0328 -> -0.0273, TE +0.0976 -> +0.0139.  Point-mass-0 TD rows remain for RB only (138
   realized; 123 of 2365 above-p90 rows).  Reading: the earlier near-zero TD bias was the point masses offsetting an upward bias of season-to-date means on s > 0 rows;
   center absolute error favors the median while the F8 center is a mean.
## NULL B LATTICE - READ - Oct 4 2026 (harness.py lines 48 - 51): null B draws one sign per season and flips that season's rows together, so FP null B is a Monte Carlo
   estimate of k / 2^S (k = season sign patterns passing the gate).  Reported values sit on that lattice: 4 seasons (f6, dependence) 0, .0587 - .0676 (1/16), .1207 -
   .1297 (2/16), .1825 - .1960 (3/16), .2440 / .2479 (4/16); spine 5 seasons 0 or .0312 (1/32).  With 4 seasons t = .05 is met only at k = 0 (Q1 negative binomial:
   one pattern of 16 - FAIL either way).  Spine Q1 v1 FP .0312 = 1/32 < t .0345 was labelled RESOLUTION-BOUNDARY by the Monte Carlo band (+-.0037), not by the value.
## EXACT NULL B INSTRUMENT - REGISTRATION - Oct 4 2026: harness.py run_slice also computes FP null B exactly by enumerating all 2^S season sign patterns (no random draws;
   used in no verdict); new mode "exact" runs the spine, f6 and dependence rows and writes proj/harness_exact_report.txt - per slice the Monte Carlo and exact values, t,
   the recorded verdict and the exact-null-B reading, marking slices where they differ.  Acceptance: harness_report, harness_f6_report, harness_dependence_report
   byte-identical after the change.  Instrument only: no recorded verdict changes here; whether exact enumeration replaces the Monte Carlo null B, and for which tests,
   is a separate decision.
WORK ORDER (appended): harness.py invariance mode reads f6_dependence_efficiency_rows.csv.gz, which the dependence cleanup deleted - the mode cannot run.

## EXACT NULL B INSTRUMENT - OUTCOME - Oct 4 2026: the three harness reports byte-identical; every recorded FP null B sits on k / 2^S (Q1 negative binomial .0632 -> 1/16,
   F5 targets RB negative binomial .2479 -> 4/16, WR receiving yards 3z .1960 -> 3/16); one slice differs: spine Q1 attempts v1, exact 1/32 = .03125 < t .0345
   (recorded RESOLUTION-BOUNDARY).  Ten gate-passing 4-season slices are recorded FAIL at exactly 1/16 (Q1 negative binomial and support law; TE receiving yards 3z;
   TE receptions support law; TE target share beta-binomial; F2 team carries negative binomial; dependence TE receiving yards wall 7, WR TDs wall 8, F2 team carries
   wall 6, RB targets wall 3) - with 4 seasons t = .05 passes only k = 0.
## SCOPE DECISION A - EXACT NULL B - Oct 4 2026 (owner / reviewer): exact season-sign enumeration replaces the Monte Carlo null B, with no resolution band, for tests
   registered from this point forward.  All recorded verdicts stand; exact readings of historical slices are audit diagnostics only.  Q1 v1 stays RESOLUTION-BOUNDARY
   (exact 1/32 = .03125 < .0345 retained as evidence the verdict was resolution-limited, not as a promotion); Q1 stays season-to-date; Q2 / Q3 / Q5 parent rebasing
   intact; no Q1 child reopened; the next Q1 dispersion wall is tested around the season-to-date Q1 mean.
## HARNESS v3 (EXACT NULL B, PROSPECTIVE) - REGISTRATION - Oct 4 2026: a rows file declares its procedure with column null_b = "exact" on every row of a slice (mixed or
   unknown declarations refuse).  Declared slices use the exact enumeration for FP null B, no band, and the exact value in the verdict and ladder line; undeclared
   (historical) slices are untouched.  Every wall registered from now on writes null_b = "exact" in its rows file.  Acceptance: the three harness reports byte-identical;
   a self-test slice (Q1 negative binomial rows copied with null_b = exact) reads exact 1/16 -> HARNESS FAIL, then is removed and the f6 report reproduces byte-identical.

## HARNESS v3 (EXACT NULL B, PROSPECTIVE) - OUTCOME - Oct 4 2026: the three harness reports byte-identical (historical slices on Monte Carlo); self-test slice (Q1 negative
   binomial rows declared exact) read exact 1/16 = .0625 (t .05, no band) -> HARNESS FAIL; after removal the f6 report reproduced byte-identical.
## F9 SHADOW OPTIMIZER - REGISTRATION - Oct 4 2026 (owner-directed; F9 consumes F1 - F8 and feeds nothing back): dk_classic.py SEASON WEEK.  Week from the schedule: the DK
   file's 14 games are all 2026 week-4 pairings in team_game (history through week 3); file prices/dk_salaries_2026_w04.csv (duplicate removed after a byte comparison).
   Forecasts: spine.py issue-mode week means (freeze forms, week_rows); zero-history PASS components (F5 TDs WR / TE, Q4, QB rushing TDs, F5 receptions TE) take, on
   rows whose season-to-date value is 0, the wall's law mean for SEASON = mean Y over earlier seasons' s = 0 rows of the support frame; FAIL components keep 0.  Expected
   DK points = linear scoring of those means (skill: receptions + .1 receiving yards + .1 rushing yards + 6 TDs; QB: .04 passing yards + 4 passing TDs - interceptions
   + .1 rushing yards + 6 rushing TDs); 300 / 100-yard bonuses withheld (no week-mode distribution); fumbles lost, 2-point conversions, return / recovery TDs unmodeled;
   DST unmodeled (score 0 for every DST - the cheapest is taken).  Salary and DK AvgPointsPerGame never enter a forecast.  Identity: names.norm + team (names.py, the one
   key), one-to-one or refused; unmatched and unprojected players ineligible with reasons; DK Status other than Q ineligible, Q flagged (participation marks, never
   adjusts a mean).  Optimizer: lineups9.best9 (exact DP: 1 QB, 2 - 3 RB, 3 - 4 WR, 1 - 2 TE, 1 DST, $50,000); the result is re-checked for slots, cap and >= 2 games,
   else refused; alternatives re-solve excluding each lineup player.  Shadow status: Q1 dispersion, participation, six zero-history components, tail calibration and DST
   remain open upstream; F8 center absolute error vs Y is -0.0153 (1/4).

## F9 SHADOW OPTIMIZER - OUTCOME - Oct 4 2026 (2026 week 4): spine issue mode projected 329 of 517 candidates (QB 26, RB 77, WR 136, TE 90); DK eligible QB 22 / RB 64 /
   WR 112 / TE 75 / DST 28; zero-history law applied WR TDs .0891 (84 rows), TE TDs .0797 (58), QB rushing TDs .0938 (14), TE receptions .2285 (12), Q4 .3063 (0).  Lineup
   E[DK] 180.12 at $49,900, 6 games: Shough, Gibbs, Swift, Smith-Njigba, Watson, Raymond, Juwan Johnson, Waller (FLEX), Dolphins (cheapest DST, unmodeled).  Limits:
   season-to-date means after 3 games (upward bias on s > 0 recorded), coverage (players with 3 earlier games only), bonuses withheld, DST unmodeled; F8 center not
   better than Y.
## Q1 DISPERSION MECHANISM - DECISION - Oct 4 2026 (owner / reviewer): football identity first, contingent on a frame-validity read without outcomes (no clipping, floors or
   normalization); if the identity cannot keep Q1 as dispersion around the frozen season-to-date mean, refuse it and register the single-QB family; F9 does not select
   the upstream model.
## Q1 IDENTITY FRAME - READ - Oct 4 2026: joins complete (1919 frame rows, none missing, multiplicity 0); witness rebuilt season-to-date attempts = spine Q1 base (max |diff|
   5.6e-17); prior team attempts in the QB's games > 0 on every row; coherent share p in [0, 1] with no clipping.  p x the earned F2 team-attempts mean (v1) moves the mean
   off the frozen Q1 mean: |ratio - 1| > 1% on 1599 of 1895 rows, > 5% on 812; ratio quantiles .851 / .938 / 1.009 / 1.127 / 1.291 (1 / 10 / 50 / 90 / 99%); mean ratio
   1.0235.  Only p x the team's season-to-date attempts in the QB's games reproduces the frozen mean (max |diff| 7.1e-15), and the earned team negative binomial is centered
   on F2 v1, not on that (untested pairing).  Per the decision the identity is refused as a Q1 dispersion wall.
## Q1 DISPERSION, SINGLE-QB FAMILY - REGISTRATION - Oct 4 2026: f6_q1_dispersion.py.  Frame: Q1 attempts QB spine rows after apply_freeze (mean mu = frozen season-to-date);
   test seasons 2021, 2023 - 25.  Baseline: Poisson(mu), the current composed law.  Candidate: discretized normal P(Y = k) = Phi((k + .5 - mu) / s) - Phi((k - .5 - mu) / s)
   for k >= 1, P(Y = 0) = Phi((.5 - mu) / s), s^2 = phi x max(mu, 1); phi by maximum likelihood on earlier seasons over logspace(-1, 1.5, 51), edge flagged.  D strata as the
   harness (candidate-only impossible -> BLOCKED; baseline-only impossible excluded from the gate).  Gate p.passes_gate on per-slate Poisson minus candidate -log score;
   harness f6 at L 1 with null_b = exact (HARNESS v3; k = 0 of 16 required); no existing harness verdict line may change.  Reported: phi per season, law mean minus mu
   (truncation at 0), randomized PIT mean / sd.  Decision: the candidate becomes Q1's composed law only with gate and harness pass, through an integration transaction;
   Q2 given Q1 (wall 1, earned on realized Q1) chained on a new Q1 law remains the composition-level question.
WORK ORDER (appended): the team-share identity changes the Q1 mean - available later only as a registered Q1 mean challenger, not as a dispersion wall.

## Q1 DISPERSION - CLOSED - Oct 4 2026 (owner / reviewer)
Negative binomial, Gamma-Poisson support and discretized normal each reached exact null B 1/16 against season-to-date.  No fourth dispersion family will be tried.
   Q1 v1 stays RESOLUTION-BOUNDARY (SCOPE DECISION A).  The team-share mean challenger is a separate future question (work order 26).
## TAIL CHALLENGER MECHANISM - DECISION - Oct 4 2026 (owner / reviewer)
(a) one-factor Gaussian copula within a skill player's F8 components, one rho per position, independent composition the null, F8 consequences downstream diagnostics
   only.  Reviewer read: no walk-forward 4-component PIT exists before 2021 (spine begins 2020; yards spreads are fit on earlier seasons), so the wall starts at 2023;
   positive shared-state dependence only (0 <= rho < 1); no P10 / P25 / P75 / P90 coverage in this wall (work order 27); f7 energy_score_nd enters in the registration
   transaction.  Scaling: stat units (F7 = stat-unit evaluation; every existing compose energy score is in stat units).
## F6 DEPENDENCE WALL 9 - REGISTRATION - Oct 4 2026 (tail challenger; one-factor Gaussian copula within a skill player's F8 components)
Term "F5 receptions with F5 receiving yards with F5 rushing yards with F5 TDs", stage "dependence wall 9 one-factor Gaussian copula"; RB, WR, TE separately.
   Components exactly those passed to dk() in spine_compose.py (Rc, RYD, UYD, TDd), through one producer skill_dk.  Null: the composed independent draws.
   Candidate: the same draws rank-reordered per row by Z_j = sqrt(rho) F + sqrt(1 - rho) e_j from rng_copula = default_rng(20261005), stable argsort; values never
   redrawn.  Invariant: sorted draws identical for every row and component, else refused and nothing written.  rho per position per test season = mean of the 6
   pairwise Pearson correlations of z = Phi^-1(u), u = REC pit_comp of seasons < s, copula u, v clip 1e-12 (wall 6's bound; numerical protection).  Domain
   0 <= rho < 1; rho < 0 in any test season -> that position FAIL - outside the registered domain, no rows.  Tests 2023, 2024, 2025 (nS 3; exact null B k/8; only
   k = 0 passes at t .05 - known before results).  Score: f7.energy_score_nd in stat units, paired by slate; null_b exact; one verdict per position (harness.py
   dependence).  Reported: rho per position per season, training rows and seasons, clipped-u counts, constant-draw test rows; diagnostic without gate: F5 receptions
   with F5 TDs 2-D energy score.  Compose outputs byte-identical (decompressed) or restore whole.  Downstream: F8 mean invariance and the F8 tail diagnostic (realized
   DK above P90) only.  No richer covariance, team state or TD-conditioned rescue.  Registered once, judged once.
## F6 DEPENDENCE WALL 9 - OUTCOME - Oct 4 2026 (proj/f6_dependence_tail_copula_report.txt, proj/harness_dependence_report.txt; first run Oct 4, reproduced exactly on re-application)
rho 2023 / 2024 / 2025 (from earlier test seasons): RB +.2135 / +.1983 / +.1968; WR +.1633 / +.1577 / +.1606; TE +.1911 / +.1761 / +.1731 - all inside 0 <= rho < 1.
   RB: gain +0.00346+-0.00542 (3/3), gate fail, FP null B exact 0/8 -> HARNESS FAIL - independent composition stays.
   WR: gain +0.00458+-0.00423 (2/3), gate fail, FP null B exact 0/8 -> HARNESS FAIL - independent composition stays.
   TE: gain +0.00962+-0.00400 (3/3), gate pass, FP null B exact 0/8 -> HARNESS PASS - one-factor positive shared-state copula EARNED.
   Diagnostics without gate: F5 receptions with F5 TDs 2-D energy score gain RB +0.00028 (2/3), WR +0.00116 (3/3), TE +0.00097 (3/3).  F8 means invariant (max |diff|
   7.11e-15 over 11,486 rows).  Realized DK above P90, independent -> copula: RB .146 -> .121, WR .133 -> .119, TE .143 -> .125 (mean P90 RB 14.14 -> 15.26, WR 13.21 ->
   13.96, TE 8.69 -> 9.25).  Only TE may consume the copula; RB / WR tail movement is diagnostic only.  Clipped u RB 97 / 156 / 236, WR 69 / 149 / 206, TE 23 / 58 / 84;
   constant-draw test rows RB 35-36%, WR 6-8%, TE 0.
## F6 DEPENDENCE WALL 9 - INTEGRATION - Oct 4 2026 (owner / reviewer: persistence of the observed deterministic transaction; no redesign)
spine_compose.py: TE F8 draws use the wall 9 copula order in 2023-2025; TE 2021 has no rho (no earlier composed PIT) and keeps the independent order; RB and WR keep
   the independent order.  Earned positions are read from proj/harness_dependence_verdicts.csv (harness.py now writes proj/harness_<mode>_verdicts.csv; reports
   unchanged), never listed by hand.  Checks passed: compose rows / pairs / params / report byte-identical; wall 9 rows identical before and after integration; every
   TE draw multiset identical (wall invariant); harness report and verdicts identical on a second run (fixed point).  Line 27 evaluates TE on the copula-composed DK
   distribution and RB / WR on the independent composition.  F8 consequence (spine_compose run 2 vs baseline):
   f8_rows: 13529 rows outside TE 2023-2025 byte-identical; TE 2023-2025 rows 3186: f8_mean max |diff| 5.33e-15; integrated P90 = wall copula P90 exactly
   TE 2023-2025 F8, independent -> copula: CRPS 2.2435 -> 2.2271;  realized DK above P90 0.143 -> 0.125;  mean P90 8.69 -> 9.25;  mean P10 0.65 -> 0.27
## LINE 27a - PER-TAIL CALIBRATION OF COMPOSED F8 - REGISTRATION - Oct 4 2026 (owner / reviewer: BOTH; absolute band slate-clustered)
Levels q = .10, .25, .75, .90, each judged separately; skill positions RB, WR, TE; realized dk_points (the join inside spine_compose dk()); Q_q = np.quantile of the live
   composed F8 draws (TE 2023-2025 the wall 9 copula order; TE 2021, RB, WR independent); producer check: Q_.10 / Q_.90 equal f8_rows f8_p10 / f8_p90 exactly, else refused.
(1) TE COMPARATIVE - the only promotion-style judgment.  Term "F8 DK quantile score at q <q>", stage "dependence wall 9 one-factor Gaussian copula", TE rows on the copula
   order (2023-2025); l_base = quantile score (pinball loss, f7.pinball) of the independent composition's Q_q, l_cand = the copula's; paired by slate; null_b exact
   (nS 3, k/8; only k = 0 passes at t .05); harness.py dependence; four verdicts, one per q; no family correction.
(2) ABSOLUTE STATUS - descriptive eligibility metadata for 27c, no promotion effect, never rewrites (1) or wall 9.  Per position and q over all test seasons: c = 1{y <= Q_q};
   c_qs = slate share; coverage = mean of c_qs over slates; slate SE = sd(c_qs) / sqrt(S); gap = coverage - q; status "within band" if |gap| <= 2 slate SE, else
   "too low" / "too high" (coverage relative to q).  Fields position, nominal, coverage, gap, slate_se, status, slates, rows, ties (y = Q_q), forms ->
   proj/f8_tail_calibration_status.csv.  27c may expose a tail only where its status is "within band"; floor / ceiling wording is 27c's.  QB not registered.
f7.pinball becomes the one producer of the quantile score (f8_vs_y imports it; its report byte-identical).  All existing compose and wall 9 outputs byte-identical.
   Registered once, judged once.
## LINE 27a - OUTCOME - Oct 4 2026 (proj/f8_tail_calibration_report.txt, proj/f8_tail_calibration_status.csv, proj/harness_dependence_report.txt)
Gates: f7 self-check 9 / 9; f8_vs_y report byte-identical with f7.pinball; 9 existing outputs byte-identical; Q .10 / .90 = f8_rows exactly; fixed point on a second run.
(2) ABSOLUTE STATUS (15,201 rows, 52 slates; coverage = P(y <= Q_q); ties 0 everywhere):
   RB  .10 .1134 too high | .25 .2573 within band | .75 .7419 within band | .90 .8448 too low
   WR  .10 .1202 too high | .25 .2780 too high    | .75 .7748 too high    | .90 .8655 too low
   TE  .10 .0494 too low  | .25 .2218 too low     | .75 .7424 within band | .90 .8718 too low   (forms copula + independent)
   Eligible for 27c: RB P25, RB P75, TE P75.  No position has an eligible P10 or P90: P10 / P90-based swings, 80% width and floor / ceiling objectives have no
   eligible tail.  Every position under-covers at .90 (more outcomes above P90 than nominal).
(1) TE COMPARATIVE (3,186 rows, 39 slates, exact null B): q .10 -0.00156+-0.00279 (1/3) HARNESS FAIL; q .25 +0.01188+-0.00274 (3/3) HARNESS PASS;
   q .75 +0.00217+-0.00193 (2/3) HARNESS FAIL; q .90 +0.01706+-0.00433 (3/3) HARNESS PASS.  Consequence of a per-q FAIL for the integrated TE copula: not stated at
   registration - owner decision pending (no effect on 27c eligibility as of this outcome: TE .10 / .25 are not within band; TE .75 is within band and FAIL).
## F8 TAIL ATTRIBUTION - DIAGNOSTIC REGISTRATION - Oct 4 2026 (owner / reviewer: a failed tail is closed for its formulation and read as an error signature; diagnosis only)
Per skill position (RB, WR, TE) and q in .10 / .25 / .75 / .90 on the live composed F8 (proj/f8_quantile_rows.csv.gz, written by spine_compose's LINE 27a section from the
   rows it already checks against f8_rows): tail rows = y <= Q_q (q < .5) or y > Q_q (q > .5).  Each F8 component (F5 receptions, F5 receiving yards, F5 rushing yards,
   F5 TDs) is beyond its own tail when its composed PIT (spine_compose_rows pit_comp) is <= q (q < .5) or > q (q > .5).  Patterns: none / exactly one (named) / two or more;
   shares among tail rows and among all rows (reference).  Volume not in F8, reported beside: F5 targets (all), F5 carries (RB).  State split: zero-history state of
   F5 receptions and F5 TDs (zero / nonzero; spine_compose_params): rows and coverage P(y <= Q_q) per state.  States with no producer (participation, role continuity,
   vacancy, hot start, team volume) not reported.  Co-occurrence, not causation.  No gate, no verdict, no forecast change; every existing output byte-identical.
   Script f8_tail_attribution.py; proj/f8_tail_attribution_rows.csv, proj/f8_tail_attribution_report.txt.
## F8 TAIL ATTRIBUTION - OUTCOME - Oct 4 2026 (proj/f8_tail_attribution_report.txt; diagnosis only; 11 existing outputs byte-identical; f8_quantile_rows 15,201 rows)
STATE MIXTURE (coverage P(y <= Q_.10), nonzero vs zero zero-history state): F5 TDs RB .162 / .017, WR .175 / .041, TE .086 / .018; F5 receptions RB .126 / .005,
   WR .128 / .000, TE .056 / .002.  At .25 by F5 TDs: RB .340 / .095, WR .358 / .164, TE .303 / .152.  The aggregate lower-tail statuses mix two oppositely
   miscalibrated states: s > 0 TD rows sit too high (work order 20), zero-history rows sit too low (work orders 19, 15).
UPPER TAIL (q .90, share of tail rows vs all rows): two or more components beyond their own tail RB .589 / .113, WR .535 / .078, TE .642 / .091; F5 targets beyond
   own tail RB .384 / .157, WR .380 / .118, TE .553 / .133 (F5 carries RB .522 / .213); F5 TDs only RB .146 / .073, WR .154 / .051, TE .187 / .056; none RB .052,
   WR .067, TE .028.  Misses co-occur with several component surprises and volume surprise (work order 9 has no producer yet; 28 later).
TE LOWER TAIL (q .10, coverage .050): F5 receptions only .744 of tail rows vs .102 of all rows; F5 targets beyond own tail .545 vs .113 (TE receptions Poisson,
   drawn independently of targets - work order 31).  Single-component excess at both ends: WR F5 receiving yards (.10: .204 vs .031; .90: .140 vs .031);
   RB F5 rushing yards (.10: .174 vs .041; .90: .138 vs .051).  Co-occurrence, not causation; no forecast changed.
## F5 TDs VOLUME-ANCHORED MEAN (work order 20 (a)) - REGISTRATION - Oct 4 2026 (owner / reviewer)
Domain: F5 TDs RB / WR / TE rows with TD history (the season-to-date mean's state nonzero, s > 0); test seasons 2021, 2023, 2024, 2025; s = 0 untouched (work order 19).
Baseline: the season-to-date TD mean (freeze form) under the F6 v1 count law (RB / WR Poisson, TE negative binomial with r on earlier seasons).  Candidate: projected volume
   mean x earlier-season pooled positional TD rate.  Volume: RB F5 carries v1 + F5 receptions v1; WR / TE F5 receptions v1 (the composition's own means).  Rate per test season s
   = sum of TDs / sum of realized volume over every row of the position in seasons < s (spine.pooled_rate; non-positive denominator refused).  Same count family around the
   candidate mean (TE r refit around it by the same procedure).  No player TD rate, no red-zone term, no calibration multiplier.
CLOSED-FAMILY DISTINCTION: unlike dependence wall 8 and the TDs-per-reception WR conditional support law, this candidate does not condition TDs on realized volume and uses no
   player-specific TD ratio; unlike spine v1 (CHARTER line 2138) it uses no red-zone opportunities and no player rate; unlike the Gamma-Poisson support law it is no player
   posterior.  It is a marginal forecast mean from projected volume x an earlier-season positional pooled TD rate.
Judgment: negative log score per row, paired by slate; term "F5 TDs", stage "volume-anchored mean (projected volume x earlier-season pooled positional TD rate)"; null_b exact
   (nS 4, k/16; only k = 0 passes at t .05); harness.py f6; one verdict per position.  Witness: the baseline over all test rows reproduces f6_td.py (RB .5647, WR .3976,
   TE .2677) or no rows are written.  Downstream F8 / tail effects diagnostic only, after integration of PASS positions (work order 32 first).  Registered once, judged once.
## F5 TDs VOLUME-ANCHORED MEAN (work order 20 (a)) - OUTCOME - Oct 4 2026 (proj/f6_td_volume_report.txt, proj/harness_f6_report.txt; exact null B, nS 4)
   RB: +0.02947+-0.00648 (4/4) gate pass, FP null B exact 0/16 -> HARNESS PASS - eligible for integration on s > 0 rows (after work order 32).
   WR: +0.02707+-0.00640 (4/4) gate pass, FP null B exact 0/16 -> HARNESS PASS - eligible for integration on s > 0 rows (after work order 32).
   TE: BLOCKED under D - the candidate assigns zero probability to 1 realized row (projected receptions 0 with a TD) -> enters at its baseline; closed for this formulation
   (no floor, no row exclusion).  Existing F6 slices unchanged (header rows 207050 -> 215784).  Wall report lines (instrument output, verbatim):
   f6_td_volume.py - work order 20 (a); domain F5 TDs rows with TD history (s > 0); baseline season-to-date under the F6 v1 count law; candidate projected volume x pooled positional TD rate
   RB: WITNESS baseline over all test rows 0.5647 (f6_td.py 0.5647) -> PASS;  per season: 2021 rate 0.0348;  2023 rate 0.0347;  2024 rate 0.0330;  2025 rate 0.0334
      domain s > 0: rows 2659;  strata both impossible 0, baseline-only impossible 0, candidate-only impossible 0
      realized mean 0.4205;  baseline mean 0.4537 (bias +0.0333);  candidate mean 0.4169 (bias -0.0036)
      negative log score baseline 0.8227, candidate 0.7948;  gain +0.02947+-0.00648 (4/4) *  (verdict: harness.py f6, exact null B)
   WR: WITNESS baseline over all test rows 0.3976 (f6_td.py 0.3976) -> PASS;  per season: 2021 rate 0.0811;  2023 rate 0.0786;  2024 rate 0.0787;  2025 rate 0.0800
      domain s > 0: rows 4090;  strata both impossible 0, baseline-only impossible 0, candidate-only impossible 0
      realized mean 0.2760;  baseline mean 0.3363 (bias +0.0603);  candidate mean 0.2707 (bias -0.0053)
      negative log score baseline 0.6538, candidate 0.6321;  gain +0.02707+-0.00640 (4/4) *  (verdict: harness.py f6, exact null B)
   TE: WITNESS baseline over all test rows 0.2677 (f6_td.py 0.2677) -> PASS;  per season: 2021 rate 0.0968 r base 7.9 cand inf;  2023 rate 0.0906 r base 3.2 cand inf;  2024 rate 0.0842 r base 2.0 cand 63.1;  2025 rate 0.0807 r base 2.0 cand 15.8
      domain s > 0: rows 1985;  strata both impossible 0, baseline-only impossible 0, candidate-only impossible 1
      realized mean 0.2051;  baseline mean 0.2608 (bias +0.0557);  candidate mean 0.2186 (bias +0.0134)
      negative log score baseline 0.5471, candidate 0.5234;  gain +0.02744+-0.00804 (4/4) *  (verdict: harness.py f6, exact null B)
## VERDICT PROVENANCE (work order 32) - REGISTRATION - Oct 4 2026
provenance.slice_sha is the one producer of a judged slice's content hash: season, week, l_base, l_cand of the slice's rows as read from its rows file by pandas.read_csv,
   in file order, written as CSV with 17 significant digits, SHA-256.  harness.py writes rows_sha256 beside every verdict in proj/harness_<mode>_verdicts.csv (reports
   unchanged).  spine_compose.py consumes a PASS verdict only if its rows_sha256 equals the hash of that slice in the rows file on disk before drawing, and again after
   writing it (else refused / exit 1); a verdicts file without rows_sha256 is refused.  Policy-neutral: until the owner sets the policy for verdicts whose inputs change
   with an upstream law (frozen vs re-judged), no harness re-run follows an integration.  Every forecast output byte-identical; negative test: an altered hash is refused
   before anything is written.
RNG ISOLATION (work order 39, owner): numpy 1.26.4 Poisson consumes generator state that depends on the mean (same seed, means .42 vs .40 and .30 vs .27: next draw
   differs), so a law change on a shared stream moves every later draw.  An integrated component law draws from its own keyed substream after the baseline draw consumed
   the existing stream unchanged; existing streams are not refactored.
## F5 TDs VOLUME-ANCHORED MEAN (work order 20 (a)) - INTEGRATION - Oct 4 2026 (owner / reviewer; work orders 32 and 39 in place)
spine_compose.py: rows with TD history (s_td nonzero) of positions whose work order 20 (a) verdict is HARNESS PASS in proj/harness_f6_verdicts.csv (rows hash verified
   against proj/f6_rows_td_volume.csv.gz; never listed by hand) take the wall's own volume-anchored mean (proj/f6_td_volume_means.csv.gz, written by f6_td_volume.py - one
   producer) under Poisson (the F6 v1 law for RB / WR), drawn from per-row keyed substreams (sha256 of "F5 TDs|position|season|week|key|work order 20 (a)") after the
   baseline draw consumed rng unchanged.  TE (BLOCKED), s = 0 rows, every non-TD component, QB: unchanged.  Invariants: f6_td_volume rows and report byte-identical;
   spine_compose_rows differ only on F5 TDs RB / WR rows with TD history; pairs and params byte-identical; f8_rows TE / QB identical; wall 9 TE slice and the 27a TE
   comparative rows identical (TE PASS still consumed under work order 32).  No harness re-run after integration while the verdict policy for changed inputs is open;
   wall 9 RB / WR verdicts and hashes describe the pre-20 (a) composition.  27a status, f8_vs_y and tail attribution re-measured as consequences, not gates.
## F5 TDs VOLUME-ANCHORED MEAN (work order 20 (a)) - INTEGRATION OUTCOME - Oct 4 2026 (proj/spine_compose_report.txt, f8_tail_calibration_report.txt, f8_vs_y_report.txt, f8_tail_attribution_report.txt)
Invariants: wall rows / report byte-identical (means file 8,734 rows); spine_compose_rows 85,380 rows identical outside F5 TDs RB / WR rows with TD history, 6,749 of 6,749
   inside changed (RNG isolation confirmed); pairs, params, 27a TE comparative rows identical; f8_rows TE / QB 5,749 identical, RB / WR 6,749 of 10,966 changed (exactly the
   scope); wall 9 TE slice identical (TE PASS consumed under work order 32).  Means on rows with TD history (season-to-date -> volume-anchored): RB 2021 .4483 -> .4184,
   2023 .4243 -> .4266, 2024 .4750 -> .3965; WR 2021 .3513 -> .2877, 2023 .3171 -> .2738, 2024 .3445 -> .2652 (2025 in the compose report).
CONSEQUENCES (measured, not gated): 27a coverage RB .10 .1134 -> .1128 (too high), .25 .2573 -> .2490, .75 .7419 -> .7426 (within band), .90 .8448 -> .8462 (too low);
   WR .10 .1202 -> .1156, .25 .2780 -> .2700, .75 .7748 -> .7645 (too high), .90 .8655 -> .8572 (too low, farther).  f8_vs_y center gain F8 vs Y RB +0.0471 (3/4) ->
   +0.1426 (4/4), WR -0.0273 (1/4) -> +0.0409 (3/4), ALL -0.0153 (1/4) -> +0.0359 (4/4); F8 CRPS RB 3.447 -> 3.389, WR 3.296 -> 3.272, ALL 3.204 -> 3.180; quantile score
   still behind Y (0/4); WR above p90 .134 -> .142.
FINDING: the TD-history state's lower-tail excess barely moved (coverage .10 RB .162 -> .161, WR .175 -> .168; .25 RB .340 -> .328, WR .358 -> .345): the TD mean was a
   small part of it; the state marks a miscalibration whose larger owner is not the TD mean (work order 40, hypothesis: season-to-date receptions / yards means in the same
   hot-start state; beside work order 35).  Upper tails are not a mean problem (WR P90 farther after the mean fell; work orders 9 / 28).
   Wall 9 RB / WR verdicts and hashes describe the pre-20 (a) rows (verdict policy for changed inputs open).
## WORK ORDER 40 - STATE MEAN DIAGNOSTIC - REGISTRATION - Oct 4 2026 (owner / reviewer: a diagnostic read before any model wall; diagnosis only)
Skill positions; components F5 targets, F5 receptions, F5 receiving yards, F5 rushing yards (+ F5 carries RB) from the live composition (spine_compose_rows: y, mean_comp,
   bias_comp = forecast mean - realized).  Split by the F5 TDs zero-history state (spine_compose_params).  Per state: rows, realized and forecast means, bias, relative bias,
   calibration slope of realized on forecast mean (OLS), bias per season (positive seasons k / 4).  Within the TD-history state: bias by prior TDs (td_ps 1 / 2 / 3+) and by
   earlier games (3-4 / 5-7 / 8+; spine_sufficient).  Selected on the outcome (mechanically negative; reported only as a state contrast): bias on rows at or below the live
   F8 P10 (f8_quantile_rows).  Reading: stable positive bias and slope below the zero-history reference across seasons -> a location defect earns a structural mean challenger
   (closed-family read first); otherwise work order 40 closes and the residual stays with scale / dependence / state.  No gate, no verdict, no forecast change.
   Script f8_state_mean_diagnostic.py; proj/f8_state_mean_diagnostic_rows.csv, proj/f8_state_mean_diagnostic_report.txt.
## WORK ORDER 40 - STATE MEAN DIAGNOSTIC - OUTCOME - Oct 4 2026 (proj/f8_state_mean_diagnostic_report.txt; bias = forecast mean - realized; seasons with positive bias k / 4)
TD-HISTORY STATE (s > 0): small positive bias - RB receptions +1.9% (4/4, slope .725 vs zero-state .751), RB receiving yards +2.4% (3/4, .631 vs .695), RB targets +0.8% (3/4),
   carries +0.4% (2/4), rushing yards -0.3% (2/4); WR receptions +2.5% (3/4, slope .845 above .787), receiving yards +2.4% (3/4, .802 above .759), targets +1.5% (2/4);
   TE targets -3.7% (1/4), receiving yards -3.8% (1/4).  Prior-TD gradient in receiving yards (1 / 2 / 3+): RB -0.81 / +0.25 / +1.11, WR -0.44 / -1.70 / +4.05.  No consistent
   earlier-games concentration.  The registered reading (stable positive bias and slope below the zero-state reference) holds only weakly, for RB receptions / receiving yards.
ZERO TD-HISTORY STATE (s = 0): large under-forecast, 0/4 positive seasons almost everywhere - RB rushing yards -26.6%, carries -17.0%, receiving yards -15.6%, receptions
   -10.2%; WR receiving yards -11.6%, receptions -7.4%, targets -5.2%; TE receiving yards -22.1%, receptions -14.3%, targets -5.4%: a stable location defect of non-TD
   season-to-date means, consistent with these rows' near-zero P10 coverage.  Calibration slopes below 1 in both states for RB / WR (.63-.89), TE near 1 (.90-1.05):
   the season-to-date means regress toward the mean (high over, low under); the TD state partly proxies level (attenuation from forecast noise also lowers slopes).
   Selected-on-outcome bias at or below P10 mechanically positive, not read.  Reading of the opposite-signed zero-state defect: owner decision pending.
## WORK ORDER 40 - CLOSED - Oct 4 2026 (owner / reviewer): the broad TD-history-state (s > 0) mean challenger for receptions / yards is closed - the registered signal was
   too weak (about 2%; slope criterion fails for WR).  No TD-state multiplier is registered.  The zero TD-history under-forecast (work order 41) is read next against level.
## WORK ORDER 41 - LEVEL-MATCHED TD-STATE DIAGNOSTIC - REGISTRATION - Oct 4 2026 (owner / reviewer; diagnosis only)
Question: does zero TD history add information after controlling for the existing forecast level?  Skill positions; components F5 targets, F5 receptions, F5 receiving yards,
   F5 rushing yards (+ F5 carries RB); residual r = realized - forecast mean (spine_compose_rows y - mean_comp; positive = under-forecast).  Cells: earlier games (3-4 / 5-7 /
   8+; spine_sufficient) x forecast-mean quintile within position and component (pandas qcut on values, duplicate edges dropped; bins used printed).  Cells with >= 20 rows in
   each F5 TDs state (spine_compose_params) enter; matched difference = precision-weighted (n0 n1 / (n0 + n1)) mean over cells of mean r (zero state) - mean r (TD history);
   raw difference = the same without cells; ratio = matched / raw; per season matched differences (k / 4 with the raw sign); rows outside entering cells counted.
Reading, fixed before results: matched difference with the raw sign in >= 3 / 4 seasons AND ratio >= 0.5 -> residual state signal (a state-split challenger is eligible,
   closed-family read first); otherwise -> the defect is level / shrinkage (a partial-pooling mean wall is eligible: mu* = w mu_season-to-date + (1 - w) mu_pool, w from prior
   games or opportunities only, fit on earlier seasons; closed-family read first).  Kept separate from work order 19 (component zero-history support).  No gate, no verdict,
   no forecast change.  Script f8_state_level_diagnostic.py; proj/f8_state_level_diagnostic_rows.csv, proj/f8_state_level_diagnostic_report.txt.
## WORK ORDER 41 - LEVEL-MATCHED TD-STATE DIAGNOSTIC - OUTCOME - Oct 4 2026 (proj/f8_state_level_diagnostic_report.txt; difference = zero TD history - TD history, r = realized - forecast)
RB / WR - every component reads level / shrinkage: raw -> matched (ratio, seasons with the raw sign) RB targets +0.102 -> -0.225 (-2.20, 1/4), carries +0.576 -> -0.061
   (-0.11, 2/4), receptions +0.116 -> -0.174 (-1.49, 1/4), receiving yards +1.258 -> -2.122 (-1.69, 0/4), rushing yards +3.497 -> -0.432 (-0.12, 3/4); WR targets +0.183 ->
   -0.247 (-1.35, 0/4), receptions +0.176 -> -0.171 (-0.97, 1/4), receiving yards +2.768 -> -2.715 (-0.98, 1/4), rushing yards +0.003 -> -0.148 (2/4).  At matched level the
   sign reverses: the zero-state under-forecast is level (regression toward the mean of season-to-date means), not TD state.
TE - receptions +0.142 -> +0.118 (+0.83, 3/4) RESIDUAL STATE SIGNAL; rushing yards -0.181 -> -0.173 (+0.96, 4/4) residual state signal, about 0.17 yards (negligible in DK);
   targets -0.045 -> +0.047 (-1.03, 3/4) and receiving yards +1.530 -> +0.910 (+0.59, 2/4) level / shrinkage.  Rows in entering cells: RB 2,293-2,957 of 4,012; WR
   6,257-6,954 of 6,954; TE 3,664-4,235 of 4,235.
Eligible under the registered reading: a partial-pooling mean wall for RB / WR season-to-date components; a TE receptions state-split challenger.  Each needs a closed-family
   read first (TE receptions support law recorded FAIL 1/16; TE targets already composed from the earned support law; WR targets / RB carries are F2 x share, not season-to-date).
## WORK ORDER 41 (a) - RB / WR YARDS PARTIAL POOLING - REGISTRATION - Oct 4 2026 (owner / reviewer: yards only; receptions stay closed - the Gamma-Poisson support law,
   same posterior-mean form, FAIL / NOT SHOWN, CHARTER lines 2079-2080)
Slices: F5 receiving yards RB, F5 rushing yards RB, F5 receiving yards WR, F5 rushing yards WR; every test row (2021, 2023, 2024, 2025).  Baseline: the live composed yards law -
   Normal(mu, sd) with mu = season-to-date mean (spine v1 = _ps / games, checked to 1e-9) and the live form (spine_compose RECEIVING_YARDS_FORM / RUSHING_YARDS_FORM: RB 2,
   WR receiving 2, WR rushing 3; form 2 sigma = RMS residual, form 3 var = phi x max(mean, 1), fit on earlier seasons).  Candidate: mu* = (g mu + k mu_pool) / (g + k), g = prior
   games (spine_sufficient games), mu_pool = earlier-season positional mean of the component, k from spine.KGRID (0-40; k = 0 is the baseline) by MAE on earlier seasons
   (the earned F2 shrinkage procedure, CHARTER line 1222); the same live variance rule evaluated at the candidate mean (form 3 couples center and spread for WR rushing
   yards; forms 2 are center-only), its sigma / phi refit around the candidate mean on earlier seasons.  No TD-state covariate, no tail metric in the gate.
CLOSED-FAMILY DISTINCTION: the yards ladder (CHARTER lines 1597-1623) varied variance / zero structure at a fixed season-to-date mean; the declared rate-shrinkage challenger
   shrinks efficiency rates (catch rate, yards per opportunity); this candidate pools the per-game yards level itself - untested.
Judgment: negative log density at y (f6_yds / f6_hurdle convention), paired by slate; stage "partial pooling of the season-to-date mean toward the earlier-season positional
   mean"; null_b exact (nS 4, k / 16; only k = 0 passes); harness.py f6; one verdict per slice.  The wall writes its candidate means and spread parameters
   (proj/f6_yards_pooling_means.csv.gz - one producer for any integration; keyed RNG isolation per work order 39).  F8 / tail movement consequence-only.
WORK ORDER 42 CLEARED: rung 3z EARNED 7 / 7 (line 1619) was the gate outcome pending the harness; the harness failed the skill hurdles (lines 1650-1652) and the corrected
   architecture keeps rung 3z for QB rushing yards only (line 1657) - spine_compose's skill normals and QB p0 hurdle match it.  Registered once, judged once.
DISCLOSURE (re-registration, verbatim above): this registration was first appended, the wall ran and printed its per-slice results (RB receiving yards gain +0.00654+-0.00221
   2/4, k 1 / 1 / 0 / 0; RB rushing yards and WR receiving yards k = 0 every season, gain 0; WR rushing yards -0.00402+-0.00412 0/4, k 3 / 0 / 0 / 0); harness.py f6 then
   refused on its fast-stats assertion because mu* = (g mu + 0) / g is not bit-identical to mu at k = 0 (row differences ~1e-16, positive-season count decided by rounding);
   the transaction restore removed the registration.  Re-registered with no change; mechanical fix only: mu* computed as mu + k (mu_pool - mu) / (g + k) (algebraically the
   registered formula; exactly mu at k = 0); the re-run must reproduce the printed report lines or no harness runs.  Restores no longer remove registrations (work order 43).
## WORK ORDER 41 (a) - RB / WR YARDS PARTIAL POOLING - OUTCOME - Oct 4 2026 (proj/f6_yards_pooling_report.txt, proj/harness_f6_report.txt; exact null B, nS 4)
Re-run reproduced the first run's 12 printed lines.  Candidate rows differing from the baseline: RB receiving yards 1,955 of 4,012 (k 1 / 1 / 0 / 0); WR rushing yards
   1,704 of 6,954 (k 3 / 0 / 0 / 0); RB rushing yards and WR receiving yards 0 (k = 0 every fold - candidate is the baseline).
   RB receiving yards +0.00654+-0.00221 (2/4), exact null B 2/16 = .125 -> HARNESS FAIL.  RB rushing yards 0 (0/4) -> HARNESS FAIL.  WR receiving yards 0 (0/4) ->
   HARNESS FAIL.  WR rushing yards -0.00402+-0.00412 (0/4) -> HARNESS FAIL.  Existing F6 report lines and verdict rows (with hashes) identical (header 215784 -> 237716).
Closed for RB / WR under this formulation: season-to-date yards level partial pooling toward the earlier-season positional mean.  The training folds mostly chose k = 0.
   No wider k grid, nonlinear or state-conditioned shrinkage follows (rescue).  Nothing integrated; the live composition is unchanged; no recompose.
   Line 41's regression-toward-the-mean reading was descriptive; the simplest legal pooling mechanism does not exploit it prospectively.
## CORRECTION - WORK ORDER 42 CLEARANCE TEXT (line 2593) - Oct 4 2026: the F6 MARGINAL PROCEDURE HARNESS OUTCOME lists HARNESS PASS for rung 3z on F5 receiving yards RB,
   F5 rushing yards TE and QB rushing yards; the harness failed rung 3z for F5 rushing yards RB, F5 receiving yards WR, F5 rushing yards WR and F5 receiving yards TE.  RB
   receiving yards and TE rushing yards stay at rung 2 because "their 3z sat on a failed rung 3" (rung 3 harness FAIL .124 / .126) - parent / child.  "The harness failed the
   skill hurdles" was inaccurate; the conclusion stands: spine_compose's yards forms equal the registered F6 v1 yards law.  Gap recorded (work order 45): a zero-hurdle on
   the live rung 2 for F5 receiving yards RB and F5 rushing yards TE was never tested.
## WORK ORDER 19 - ZERO-HISTORY HURDLE, RUNG 1 - REGISTRATION - Oct 4 2026 (owner / reviewer: separate the first-event probability from the positive-count magnitude)
Domain: s = 0 rows of the components recorded FAIL in proj/f6_zero_history_replacement_verdicts.csv - F5 TDs RB, F5 targets RB, F5 targets WR, F5 carries RB, F5 receptions
   RB, F5 receptions WR (the script refuses if that set differs); frame, walk-forward and witness of the replacement wall (support.support_frame; tests 2021, 2023 - 25;
   per-component test rows and events = proj/f6_zero_history_rows.csv.gz, else no verdict).  Candidate (rung 1 of the first-event ladder): P(Y = 0) = 1 - pi, pi = share of
   Y > 0 over earlier seasons' s = 0 rows of the component (constant positional first-event probability); Y | Y > 0 = zero-truncated negative binomial (Poisson at r = inf),
   (m, r) by maximum likelihood on earlier seasons' s = 0 rows with Y > 0, r over logspace(0, 4, 41) + inf, m by bounded scalar search per r (bounds are search limits,
   not a floor; boundary hits printed).  pi = 0 or no earlier positive rows -> UNRESOLVED (no substitute).  No covariates.
CLOSED-FAMILY DISTINCTION: the point mass, the Gamma-Poisson support law and the replacement negative binomial all tie P(Y > 0) to the count mean / rate; the hurdle sets
   P(Y > 0) and E[Y | Y > 0] separately - untested for count components (CHARTER line 2332 names it as a separate wall; the yards rung 3z is a different, continuous law).
Gate (the replacement wall's, unchanged): primary |share of Y > 0 - mean pi| <= 2 SE, SE = sqrt(sum p (1 - p)) / n; secondary randomized PIT F_h(y - 1) + U pmf_h(y) (wall's own
   default_rng(20261006)), mean within 0.5 +- 2 sqrt(1 / (12 n)), variance within 1/12 +- 2 sqrt((1/80 - 1/144) / n); PASS iff both, per component.  Diagnostic, no gate:
   negative log score hurdle vs the replacement negative binomial (its per-row m, r), paired by slate.  Ladder after rung 1: opportunity-conditioned pi, then pooling /
   recency, then additive ML - each its own wall, only if the simpler rung fails.  s > 0 rows untouched; a PASS enters composition only through an integration transaction
   (s > 0 rows identical, keyed RNG isolation).  Script f6_zero_history_hurdle.py; proj/f6_zero_history_hurdle_verdicts.csv, _rows.csv.gz, _report.txt.  Registered once, judged once.
## WORK ORDER 19 - ZERO-HISTORY HURDLE, RUNG 1 - OUTCOME - Oct 4 2026 (proj/f6_zero_history_hurdle_report.txt; gate unchanged from the replacement wall)
PASS: F5 TDs RB (n 1353; share .1020 vs .1191, gap -.0171 within 2 SE .0176; PIT pass; diagnostic log-score gain +0.00049 3/4), F5 targets RB (350; .1657 vs .1977;
   +0.02557 4/4), F5 carries RB (240; .1125 vs .1192; +0.19016 4/4), F5 receptions RB (417; .1535 vs .1819; +0.00797 3/4), F5 receptions WR (449; .1804 vs .2177;
   +0.02692 4/4).  FAIL: F5 targets WR (334; .1886 vs .2369, gap -.0483 beyond .0465; PIT fail; diagnostic +0.05950 4/4) - the remaining defect is the first-event
   probability; the pre-declared next rung (opportunity-conditioned pi) applies to WR targets only.  Positive-part r at the grid's lower edge (1.0) for WR targets,
   RB carries, WR receptions: diagnostic only, no grid widening, passing slices not reopened.
## WORK ORDER 19 - ZERO-HISTORY HURDLE - INTEGRATION - Oct 4 2026 (owner / reviewer)
spine_compose.py: s = 0 rows of components whose verdict is PASS in proj/f6_zero_history_hurdle_verdicts.csv (never listed by hand) are redrawn from the wall's own
   per-season (pi, m_pos, r_pos) in proj/f6_zero_history_hurdle_rows.csv.gz (exactly one per component and season, else refused): event = U1 < pi, positive part =
   zero-truncated negative binomial inverse CDF at U2, per-row keyed substreams (sha256 "term|position|season|week|key|work order 19 hurdle"; work order 39) after the
   baseline draw consumed rng unchanged.  Refused if the component's replacement-wall verdict is also PASS (one law per row set).  Parent / child: RB targets and RB
   carries feed no composed child; RB / WR receptions and RB TDs feed skill_dk (F8, wall 9 - wall 9 RB / WR verdicts FAIL, not consumed; TE untouched, its PASS still
   consumed under work order 32); work order 20 (a) touches TD-history rows only (disjoint).  Compose writes proj/f6_zero_history_hurdle_integration.csv.gz (every
   redrawn row); the ZERO-STATE labels and f8_vs_y read it.  Invariants: spine_compose_rows differ only on recorded rows; pairs, params, 27a TE comparative rows
   identical; f8_rows differ only on rows with integrated receptions / TDs; TE / QB rows identical; wall 9 TE slice identical.  27a, f8_vs_y, attribution as consequences.
## WORK ORDER 19 - ZERO-HISTORY HURDLE - INTEGRATION OUTCOME - Oct 4 2026 (re-measured read-only against /tmp/slate_ypool2/proj_all, the post-20 (a) pre-hurdle snapshot; the
   integration run's own snapshot was deleted by a re-run's block 1 - work order 46)
Baseline valid: pairs, params, 27a TE comparative rows, 20 (a) means identical snapshot vs live.  Invariants: spine_compose_rows 89,320 rows identical outside the integration
   record, 2,809 of 2,809 recorded rows changed; f8_rows identical outside rows with integrated receptions / TDs (TE / QB included), 1,845 of 1,845 inside changed; wall 9 TE
   slice identical.  Integration record 2,809 rows (F5 TDs RB 1353, carries RB 240, receptions RB 417, receptions WR 449, targets RB 350).
CONSEQUENCES (measured, not gated): 27a RB .10 .1128 -> .1138 (too high), .25 .2490 -> .2590, .75 .7426 -> .7580 (within band), .90 .8462 -> .8620 (too low, closer);
   WR .75 .7645 -> .7655, .90 .8572 -> .8575.  f8_vs_y RB F8 mean 7.86 -> 8.16 (realized 8.30), above p90 .152 -> .137, center gain vs Y +0.1426 (4/4) -> +0.0577 (4/4);
   ALL +0.0359 (4/4, gate) -> +0.0092 (4/4, no gate); WR +0.0409 -> +0.0265 (3/4, no gate); CRPS RB 3.389 -> 3.383, ALL 3.180 -> 3.179.  TD zero-history annotation
   unresolved -> resolved (RB point-mass rows 1353 -> 0).  Zero-history lower tail survives: P10 coverage RB receptions-zero .005, TD-zero .017 -> .020.
READING: first-event support semantics fixed; the RB lower tail is not owned by the TD mean (20 a), simple yards shrinkage (41 a) or first-event support (19).  Next lead:
   joint downside state (post-repair co-movement diagnostic).
## VERDICT POLICY FOR CHANGED INPUTS - DECISION - Oct 4 2026 (owner / reviewer): a dependence verdict is frozen for the marginal laws it was judged on; materially changed
   marginals require a new dependence wall rather than reusing or re-adjudicating the old verdict.  Historical verdicts are preserved exactly.  Applied: wall 9 RB / WR stay
   HARNESS FAIL as recorded, judged on the pre-20 (a) / pre-19 marginals; a new RB / WR dependence wall is its own registration.  Wall 9 TE (marginals unchanged; rows hash
   verified under work order 32) stays consumed.
## WORK ORDER 19 - ZERO-HISTORY HURDLE, RUNG 2 (WR TARGETS) - REGISTRATION - Oct 4 2026 (owner / reviewer: persistence-conditioned first-event probability)
Domain: s = 0 rows of F5 targets WR only (rung 1 FAIL; the script refuses unless proj/f6_zero_history_hurdle_verdicts.csv still records it FAIL); frame, walk-forward,
   witness and gate of rung 1 unchanged.  Candidate: logit(pi_i) = alpha + beta g_i, beta <= 0, g = prior games this season without a target (support_frame g), fit by
   maximum likelihood on earlier seasons' s = 0 rows (Bernoulli Y > 0; L-BFGS-B with the bound; beta at 0 is rung 1's constant pi and is printed).  Positive part exactly
   unchanged: rung 1's zero-truncated negative binomial fit, (m, r) per season equal to rung 1's m_pos / r_pos or no verdict.  The live projected opportunity is 0 on every
   such row (spine.py: WR targets = F2 x recency share, share 0 without history) and cannot condition pi.  PIT draws from the wall's own default_rng(20261007).  Diagnostic, no
   gate: negative log score vs rung 1 and vs the replacement negative binomial, paired by slate.  Ladder: if this rung fails, team-volume-conditioned pi (rung 3); an additive
   combination only if both earn it.  One producer: hurdle.py holds GRID, nb, ztnb_fit; f6_zero_history_hurdle.py imports them and its verdicts, rows and report must
   reproduce byte-identical.  Script f6_zero_history_hurdle_r2.py; proj/f6_zero_history_hurdle_r2_verdicts.csv, _rows.csv.gz, _report.txt.  Registered once, judged once.
## WORK ORDER 19 - ZERO-HISTORY HURDLE, RUNG 2 (WR TARGETS) - OUTCOME - Oct 4 2026 (proj/f6_zero_history_hurdle_r2_report.txt)
One producer: hurdle.py (GRID, nb, ztnb_fit); rung 1 re-run byte-identical (verdicts, rows, report).  Fits (alpha / beta): 2021 +0.389 / -0.2877, 2023 -0.527 / -0.1415,
   2024 -0.692 / -0.1083, 2025 -0.711 / -0.1107 - beta negative every season, never at its bound; positive part equal to rung 1 every season.  Primary: share .1886 vs
   predicted .2378, gap -.0491 beyond 2 SE .0460 -> FAIL; secondary PIT mean .4878, variance .07974 -> PASS.  Per season predicted / share: 2021 .293 / .190, 2023 .231 /
   .225, 2024 .232 / .212, 2025 .216 / .144.  Diagnostic: log score vs rung 1 +0.00017+-0.00809 (3/4), vs replacement +0.05967+-0.02417 (4/4).  VERDICT FAIL: persistence
   reshapes pi across g but does not fix its level.  Next pre-declared rung: team-volume-conditioned pi (rung 3), WR targets only; positive part unchanged.
## WORK ORDER 19 - ZERO-HISTORY HURDLE, RUNG 3 (WR TARGETS) - REGISTRATION - Oct 4 2026 (owner / reviewer: team-volume-conditioned first-event probability)
Domain: s = 0 rows of F5 targets WR only (support_frame targets_ps == 0); the script refuses unless rung 1 and rung 2 verdicts both record FAIL; frame, walk-forward,
   witness (rows / events equal f6_zero_history) and gate of rung 1 unchanged.  Candidate: logit(pi_i) = alpha + gamma m_T,i, gamma >= 0, m_T = live F2 v1 projected
   team-target mean (spine_rows term "F2 team targets", column v1; never realized team targets), joined player -> team exactly as spine_compose.py line 179 (load() played
   rows, first row per player-week) then team-week; any row without a team or m_T, or a duplicated team-week, refuses (no default).  Fit by maximum likelihood on earlier
   seasons' s = 0 rows (Bernoulli Y > 0; L-BFGS-B with the bound); a non-converged fit refuses (no verdict); gamma at 0 is rung 1's constant pi and is printed.  g is not
   used.  Positive part exactly unchanged: rung 1's zero-truncated negative binomial, (m, r) per season equal to rung 1's m_pos / r_pos or no verdict.  PIT draws from the
   wall's own default_rng(20261008).  Diagnostic, no gate: negative log score vs rung 1 and vs the replacement negative binomial, paired by slate; a positive gamma is
   mechanism evidence, not promotion evidence.  No F8 consequence gate.  If this rung fails: no combination with g; the pooling / recency rung only on its own terms.
   Script f6_zero_history_hurdle_r3.py; proj/f6_zero_history_hurdle_r3_verdicts.csv, _rows.csv.gz, _report.txt.  Registered once, judged once.
## WORK ORDER 19 - ZERO-HISTORY HURDLE, RUNG 3 (WR TARGETS) - OUTCOME - Oct 4 2026 (proj/f6_zero_history_hurdle_r3_report.txt)
Join: 400 s = 0 rows, every row with a team and F2 v1 m_T; positive part equal to rung 1 every season.  Fits (alpha / gamma): 2021 -16.083 / +0.45821 (one training season),
   2023 -5.246 / +0.12258, 2024 -3.707 / +0.07607, 2025 -1.673 / +0.01344 - gamma positive, never at its bound, shrinking as training seasons accrue.  Primary: share .1886
   vs predicted .2423, gap -.0537 beyond 2 SE .0456 -> FAIL; secondary PIT mean .4519 (outside 0.5 +- .0316), variance .08419 -> FAIL.  Per season predicted / share: 2021
   .341 / .190, 2023 .223 / .225, 2024 .212 / .212, 2025 .222 / .144.  Diagnostic: log score vs rung 1 -0.05049+-0.01995 (1/4, worse), vs replacement +0.00901+-0.03060 (3/4).
   VERDICT FAIL.  Rungs 1-3 all over-predict 2021 and 2025 and are close in 2023 / 2024.  Per the registration: no combination with g; the pooling / recency rung only on its
   own terms, by owner decision.  WR targets s = 0 rows keep their current law (no hurdle verdict consumable).
## WORK ORDER 19 - ZERO-HISTORY HURDLE (WR TARGETS) - LADDER CLOSED - Oct 4 2026 (owner / reviewer decision (b))
F5 targets WR, s = 0: first-event probability UNRESOLVED.  Three structurally distinct preregistered rungs failed (constant pi; pi(g), beta <= 0; pi(F2 v1 projected team
   targets), gamma >= 0).  No pooling / recency rung and no additive ML rung: a recency weight would repair the level after the mechanism covariates failed (a calibration
   patch, not a mechanism), and the miss is not a smooth drift (2021 and 2025 over-predicted; 2023 / 2024 close).  These rows stay on their current frozen law; no hurdle
   verdict for this component is consumable.  Reopening requires a new mechanism registered on its own terms, never a further rung of this ladder.  Work order 19 is closed:
   five components earned and integrated (rung 1), WR targets the residual NO.  Next: the joint downside co-movement diagnostic.
## F8 TAIL ATTRIBUTION - JOINT DOWNSIDE EXTENSION (MODEL-IMPLIED PATTERN) - REGISTRATION - Oct 4 2026 (owner / reviewer; diagnosis only, no gate, no forecast change)
Question: do real components fall in the F8 tail together more than the live composition's own draws do inside its own F8 tail?  Observed side: f8_tail_attribution.py's
   existing pattern (component beyond its own tail when pit_comp <= q / > q; tail rows y_dk <= Q_q / > Q_q).  Model side, in spine_compose.py where the draws exist: RB / WR rows
   on the independent form (draws independent within a row; TE excluded - copula law); per draw, a component is beyond its own tail when its randomized self-PIT (f7.pit_self:
   pit's formula at each draw, one producer; witness: equal to f7.pit column by column under the same uniforms) is <= q / > q, and the draw is in the F8 tail when its skill_dk
   value is <= / > the row's Q_q (q27's np.quantile call); per row and q: tail draws and tail draws with none / one / two or more components.  Own stream default_rng(20261009);
   rng, rng8, rng_copula untouched; every existing compose output byte-identical; proj/f8_tail_pattern_model_rows.csv.gz.  Statistic: Delta_q = observed share of two or more
   among tail rows - model share among tail draws, per slate (slates with an observed tail row), mean +- slate SE; also per season, pooled.  Reading ("material" = 27a's band,
   season rule of the harness gate): Delta > 2 SE and positive in >= nS - 1 seasons -> shared downside state / dependence eligible for its own wall; |Delta| <= 2 SE -> the
   enrichment is conditioning arithmetic, no dependence wall; Delta < -2 SE and negative in >= nS - 1 seasons -> back to marginal shape / state; otherwise mixed, recorded.
   Primary readings: RB q .10, WR q .10, WR q .25; RB q .25 and upper tails printed as context, no reading.  WR rows include the unresolved WR-targets s = 0 rows (not separable:
   targets is not an F8 component).  Existing attribution report lines (prefix) and rows file byte-identical; the extension appends to the report and writes
   proj/f8_tail_joint_downside_rows.csv.  Registered once, read once.
## F8 TAIL ATTRIBUTION - JOINT DOWNSIDE EXTENSION (MODEL-IMPLIED PATTERN) - OUTCOME - Oct 4 2026 (proj/f8_tail_attribution_report.txt, proj/f8_tail_joint_downside_rows.csv)
Witness: f7.pit_self equals f7.pit column by column (same uniforms).  Compose outputs 13 of 13 byte-identical; model rows 10966 (RB 4012, WR 6954), tail draws per row exactly
   200 / 500 / 500 / 200, pattern counts sum to tail draws on every row; attribution rows byte-identical, existing report lines (73) an identical prefix.  PRIMARY (two or
   more components beyond their own tail among F8-tail rows; observed vs model; Delta per slate, 52 slates): RB q .10 .319 vs .253, Delta +.0608 +- .0222, seasons 2021
   +.168 / 2023 -.002 / 2024 +.050 / 2025 +.026 (3/4) -> POSITIVE: a fresh RB within-player state / dependence wall is eligible (wall 9's RB FAIL is frozen on the earlier
   marginals; a new wall on the current marginals).  WR q .10 .271 vs .245, +.0275 +- .0158 (4/4) -> APPROXIMATELY ZERO: conditioning arithmetic, no dependence wall.  WR q
   .25 .542 vs .567, -.0256 +- .0127 (0/4) -> NEGATIVE: back to marginal shape / state.  Context, no reading: RB q .25 +.0299 +- .0162 (3/4); RB q .75 +.0749 +- .0156
   (4/4); RB q .90 .576 vs .344, +.2223 +- .0272 (4/4); WR q .75 +.1057 +- .0102 (4/4); WR q .90 .524 vs .331, +.1964 +- .0160 (4/4) - an upper-tail excess larger than the
   lower-tail one, a lead for work order 34, not promotable from this diagnostic.  The RB q .10 reading leans on 2021 (+.168); the registered rule is met and stands.
## F6 DEPENDENCE - RB WITHIN-PLAYER WALL ON CURRENT MARGINALS - CANDIDATE (a) NOT REGISTRABLE - Oct 4 2026 (owner / reviewer decision (b))
Candidate (a) - wall 9's one-factor exchangeable Gaussian copula, rho >= 0 from earlier-season current-composition PITs - cannot supply a verdict on the current marginals:
   compose computes its RB slice every run and the current result was on screen before any registration (proj/f6_dependence_tail_copula_report.txt: RB rho +.2237 / +.2026 /
   +.2016; energy score gain +0.00322+-0.00553 (2/3)).  Diagnostic context only - not a wall outcome, not a FAIL; the frozen RB wall 9 verdict (judged rows 10e1d017...) is
   unchanged.  The blind wall chosen: lower-tail Clayton copula, theta >= 0, fit only from earlier-season current-composition PITs, rank-reordering the four marginal draw
   multisets; four-component energy score, exact null B; P10 consequence only.  Registered after work order 47.
## WORK ORDER 47 - DEPENDENCE VERDICT PROVENANCE - REGISTRATION - Oct 4 2026 (hazard C; owner / reviewer: before any dependence harness run)
Hazard: harness.py dependence judges every f6_dependence*_rows slice on disk and rewrites proj/harness_dependence_verdicts.csv; compose rewrites wall 9 RB / WR rows on the
   current marginals every run, so a run would replace the frozen RB / WR verdicts (judged rows 10e1d017..., e40aa99f..., no longer on disk).  Remedy, harness.py dependence
   mode only: a recorded verdict whose rows_sha256 differs from its slice on disk is FROZEN - not re-judged, recorded row kept, printed; a recorded verdict whose rows still
   match is re-judged and must reproduce its recorded verdict exactly, else refused; a recorded verdict with no rows on disk is kept and printed; only slices with no recorded
   verdict are judged anew and appended; recorded rows keep their order; duplicate recorded keys refuse.  Witness: with no new slice, harness.py dependence rewrites
   proj/harness_dependence_verdicts.csv byte-identical, FROZEN list printed.  Spine / f6 modes unchanged (whether they carry the same hazard: work order).
## WORK ORDER 47 - DEPENDENCE VERDICT PROVENANCE - OUTCOME - Oct 4 2026 (harness.py dependence after the edit)
proj/harness_dependence_verdicts.csv byte-identical (26 rows).  FROZEN 2: wall 9 RB (recorded rows 10e1d0177268, rows on disk c08933ba29f0) and wall 9 WR (e40aa99f42ac,
   56def60444eb), recorded FAIL kept, not re-judged; the other 24 re-judged on matching rows and reproduced exactly; no recorded verdict without rows; no new slice.  Closed.
## F6 DEPENDENCE WALL 10 - RB LOWER-TAIL CLAYTON COPULA ON CURRENT MARGINALS - REGISTRATION - Oct 4 2026 (owner / reviewer; blind)
Domain: RB, test seasons after the first (2023, 2024, 2025 - earlier composed PITs required, as wall 9), current marginals (work order 19 hurdle, work order 20 (a)); never
   consumed by compose without its own integration transaction.  Candidate: exchangeable four-dimensional Clayton copula on F5 receptions, F5 receiving yards, F5 rushing
   yards, F5 TDs; theta = 2 tau / (1 - tau), tau = mean of the 6 pairwise Kendall tau of the earlier-season composed PITs (REC pit_comp through earlier_pits, one producer
   shared with wall 9, whose outputs must stay byte-identical); registered domain theta >= 0 - any season with theta < 0: FAIL outside the domain, no rows.  Draws:
   Marshall-Olkin, V ~ Gamma(1 / theta, 1), E_j ~ Exp(1), U_j = (1 + E_j / V)^(-1 / theta), own stream default_rng(20261010); each component's 2000 draws rank-reordered by
   U_j per row, multiset unchanged or refused.  Gate: energy score over the four components, independent (l_base) vs Clayton order (l_cand), harness.py dependence, exact null
   B, ladder 1; one RB verdict under "F5 receptions with F5 receiving yards with F5 rushing yards with F5 TDs [dependence wall 10 lower-tail Clayton copula]", appended
   under work order 47.  P10 / P90 coverage independent vs Clayton: consequence only, printed after the verdict.  Every existing compose output byte-identical; the 26
   recorded verdict rows an identical prefix.  Files: proj/f6_dependence_lower_tail_copula_rows.csv.gz, proj/f8_lower_tail_copula_rows.csv.gz,
   proj/f6_dependence_lower_tail_copula_report.txt.  Candidate (a)'s seen numbers are not reused.  Registered once, judged once.
## F6 DEPENDENCE WALL 10 - RB LOWER-TAIL CLAYTON COPULA ON CURRENT MARGINALS - OUTCOME - Oct 4 2026 (proj/harness_dependence_report.txt, proj/f6_dependence_lower_tail_copula_report.txt)
Compose 13 of 13 outputs byte-identical (earlier_pits reproduces wall 9).  theta: 2023 +.3840 (tau .1611), 2024 +.3481 (.1483), 2025 +.3422 (.1461) - inside the domain;
   3050 rows, keys and l_base equal to wall 9 RB.  Harness (work order 47): 26 recorded rows an identical prefix, RB / WR wall 9 FROZEN, one row appended.  RB: slates 39,
   observed -0.01206+-0.00705 (0/3), gate fail; FP null B exact 0/8 -> HARNESS FAIL (rows 1ff148fb4a06...).  Consequence only: below P10 .1059 -> .0616, above P90 .1311 ->
   .1095, mean P10 2.21 -> 1.09 (every season the same direction) - generic lower-tail rank dependence over-states RB downside.  Owner / reviewer: the simple RB within-player
   copula remedies are CLOSED (wall 9 family seen weak on the current marginals, not a verdict; wall 10 FAIL); the RB q .10 joint-downside evidence stays recorded; the
   shared latent state is held in reserve, reopened only if a state diagnostic identifies a pregame or latent-regime mechanism.  Next: WR lower-tail marginal shape / state.
## WORK ORDER - ROOT GROUPING (FIVE WHYS) - Oct 4 2026 (owner / reviewer; a premise-request map, not a measurement; the walk-down order is unchanged)
Four scientific roots.  (1) Conditional marginal location / shape by state: A1 location of season-to-date means by history state - WR lower tails, line 35, line 20
   remainder (TE TDs blocked under D; QB rushing TDs); A2 support, zero vs positive - 45 (kept separate from shape); A3 positive-part shape / scale of native yards - 37, 38;
   A4 QB tails - 33.  (2) Structural links within a player - 31 (targets -> receptions), the cheapest discriminator for 34.  (3) Shared team / game state across players -
   28, 26, 18 (parent / child chain), the RB q .10 joint-downside evidence.  34 is stated as "upper-tail joint amplification: structural link (2) vs shared game state (3)
   vs residual marginal shape (1)" until 31 and the team / game read; no owner assigned.  (4) Prospective production of the same laws - 27b, 24, 27c, 29, 10 (prospective
   part).  Premise layer: line 9 participation / role state (under the TE receptions residual and the latent-state reserve).  Instrument (E, batched, the subject untouched):
   47a, 22, 23, 11, 12, 15, 17, 25, 30, 10 (housekeeping), 43 / 44 / 46, 36.  Policy: the 27a TE per-q decision.  Rule: when a task comes up, its read requests every premise
   its data grouping holds at once.  Amended by the A1 read below: the WR lower tails and line 35 are two state-specific defects, not one.
## A1 READ - WR / TE F8 AND COMPONENTS BY HISTORY STATE - FINDING - Oct 4 2026 (read only; uniform PIT sd .2887; no gate, no forecast change)
WR TD-history rows (4090): F8 bias +.10 (seasons +.25 / +.57 / -.53 / +.09), PIT mean .465, PIT sd .328 (F8 too narrow), coverage q .10 / .25 / .75 / .90 .168 / .345 /
   .739 / .843 - both tails thin; components individually near uniform (PIT sd targets .282, receptions .282, receiving yards .286, TDs .295) -> width owner is co-movement
   among components (root 2), not the marginals; receiving yards over-forecast +1.04 (PIT .472; .466 / .457 / .492 / .472, 4/4 below .5) - location (A1), about +0.1 DK.
   WR zero TD-history rows (2864): F8 bias -.24, PIT sd .258 (F8 too wide), coverage .041 / .165 / .805 / .879; receiving yards PIT sd .196 - the constant-sd form (WR
   form 2) too wide at low means (A3, 37's heteroskedastic-scale rung); targets PIT .535 (4/4 above .5).  Line 35: pooled q .75 over-coverage comes from zero TD-history
   rows (.805; TD-history .739), pooled q .25 from TD-history rows (.345; zero .165) - two state-specific defects.  TE: copula TD-history rows near calibrated (q .10 .082,
   q .90 .888, PIT sd .293); zero TD-history rows q .10 .018 / .017 (copula / independent), q .25 .147 / .166, F8 bias -.41 / -.53; receiving yards -2.56 (PIT .533, 4/4
   above .5, PIT sd .216 too wide), receptions PIT .524 (4/4 above .5) - work order 40's opposite-signed zero-state defect (its reading still an open owner decision) plus
   A3 scale; a location remedy already failed (41(a), all four slices).  Order note: a dependence verdict is frozen for the marginals it was judged on.
## ROOT 1 OWNER MAP - RECEIVING YARDS (WR, TE) - REGISTRATION - Oct 4 2026 (owner / reviewer decision (d); diagnosis only, no gate, no promotion, no forecast change)
Rows: F5 receiving yards, WR and TE, live composition (spine_compose_rows).  Targets, law-relative: z = Phi^-1(pit_comp clipped to [0.5 / N, 1 - 0.5 / N]), N = compose draws
   (spine_compose.py "N = "); location z (law null 0), scale z^2 (null 1), asymmetry sign(z) z^2 (null 0) - the owner's sign(e)|e| read as asymmetric scale.  Legal pregame
   features: mu (frozen F6 v1 receiving-yards mean), games (spine_sufficient), projected targets (F5 targets v1), projected team targets (F2 team targets v1, joined as compose
   line 179 / 184), receiving-yards history state, TD history state; season / week diagnostics only; participation absent until line 9.  Any row without every feature
   refuses.  Lens ladder, cross-fit leaving one season out: L0 training constant; L1 mu deciles x receiving-yards state; L2 one numeric feature (training deciles,
   inverted_cdf); L3 one state; L4 additive (bin effects of all six features, 20 backfitting sweeps).  A fold whose test row falls in a cell with no training rows makes that
   lens not estimable there - reported, not read; no default.  L5 nonlinear not run here (its own registration, only if L4 shows structure).  Reading per lens vs L0:
   p.paired_by_slate on per-slate squared error, p.passes_gate; context: law null vs L0, and L1 vs L2 mu (state after mean level).  Registered map: scale explained by L2 mu ->
   A3 scale owned by mean level (smallest new scale family next, not a variance-proportional-to-mean rerun); L1 beats L2 mu on scale -> state-dependent scale (common
   mechanism for 37 / 38 / TE); location explained, scale not -> A1 location; asymmetry explained -> shape / skew owner; only L4 explains -> multi-feature owner; nothing
   explained for a position -> Root 1 closes there for receiving yards and 31 (targets -> receptions) is next.  Script f6_root1_owner_map.py; proj/f6_root1_owner_map_rows.csv,
   proj/f6_root1_owner_map_report.txt.  Registered once, read once.
## ROOT 1 OWNER MAP - RECEIVING YARDS (WR, TE) - INSTRUMENT CORRECTION - Oct 4 2026 (disclosure; the registered design unchanged)
First run stopped before any lens was read: code() returned object-dtype keys for states and unicode keys for bins, and np.char.add refused at L1 (TypeError).  Printed
   before the stop: N 2000, PIT clip [0.00025, 0.99975], rows WR 6954 / TE 4235 with a complete feature join, WR states, mu check max |mean_comp - m_ryd| 3.607 yards (draw-mean
   noise).  Restore removed the script.  Correction: both key paths np.asarray(..., dtype=str); targets, features, lenses, folds, readings and outputs unchanged.  No lens result
   was seen; the run that follows is the registered read.
## ROOT 1 OWNER MAP - RECEIVING YARDS (WR, TE) - OUTCOME - Oct 4 2026 (proj/f6_root1_owner_map_report.txt; diagnosis only)
WR (6954 rows, held out 2021 / 2023 / 2024 / 2025): scale z^2 mean .877 (law too wide; law null vs L0 +.01424, 4/4); L2 mu +0.32701+-0.03428 (4/4), skill +.110; state after
   mean level +0.00021+-0.00033 (nothing beyond level); projected targets +0.29995 and TD state +0.11146 alone - proxies of level; L4 +0.32362 (no gain over mu).  Location
   z: L2 mu +0.01936 (4/4), L4 +0.03281.  Asymmetry: L2 mu +0.05606, L4 +0.08143.  READING: A3 - WR receiving-yard scale owned by the forecast level (location and asymmetry
   also tied to mu).  TE (4235 rows): location z mean +.149 (law null vs L0 +.02282, 4/4), L2 mu +0.01000, L4 +0.02096; scale - no lens passes (L2 mu -0.00507); asymmetry
   mean +.510 (law null vs L0 +0.26418+-0.03220), L2 mu +0.05679, projected targets +0.03691, TD state +0.02899, L4 +0.08766.  READING: A1 location + shape / skew; scale not
   the owner.  Owner / reviewer: WR -> a level-dependent scale wall (WR only); TE on its own location / skew ladder; 31 after Root 1 closes.  Mean check: max |mean_comp -
   m_ryd| 3.607 yards is draw-mean noise; walls fit and score on the registered mean v1, never mean_comp.
## WR RECEIVING YARDS LEVEL-DEPENDENT SCALE - REGISTRATION - Oct 4 2026 (owner / reviewer; blind; Root 1, A3-WR)
Rows: F5 receiving yards WR, frozen spine rows (apply_freeze), test seasons after the first (2021, 2023, 2024, 2025), y and the registered mean v1 (never mean_comp); any
   negative v1 refuses (no clamp).  Baseline: the live law, Normal(v1, sd), form 2, sd = spread(2) = RMS of (y - v1) on earlier seasons (compose's live form line must match).
   Candidate: Normal(v1, sigma_i), log sigma_i = alpha + beta log(1 + v1_i), alpha and beta by maximum likelihood on earlier seasons (L-BFGS-B, unbounded; a non-converged fit
   refuses); the mean exactly v1; beta = 0 is the baseline family.  No TD-state, targets or additive term.  Score: negative log density at y, paired by slate, rows null_b
   exact; verdict harness.py f6 (exact null B).  Work order 47a guard for this run: every recorded harness_f6_verdicts row identical after the run and exactly one row added
   (this wall's WR slice), else restored.  Diagnostic, no gate: mean z^2 by test-mu quintile, baseline vs candidate.  F8 consequence only after an integration transaction.
   Script f6_wr_receiving_yards_scale.py; proj/f6_rows_wr_receiving_yards_scale.csv.gz, proj/f6_wr_receiving_yards_scale_params.csv, proj/f6_wr_receiving_yards_scale_report.txt.
   Registered once, judged once.
## WR RECEIVING YARDS LEVEL-DEPENDENT SCALE - DISCLOSURE AND DOMAIN AMENDMENT - Oct 4 2026 (owner / reviewer decision (b); no wall result seen)
Disclosure: (1) the first block 3 found the script absent after block 2 had compiled it (cause not observable); restore ran; nothing judged.  (2) The re-created script
   (sha256 3a3a30f2...) refused under its registered guard: 19 WR rows with negative v1 (range -1.000 to -0.143; one at exactly -1.000, 2021 week 4; 16 in test seasons) -
   legitimate season-to-date means of three WRs with negative receiving yards to date; log(1 + mu) is undefined at -1.  Amendment (the smallest change the domain fact
   requires): log sigma_i = alpha + beta asinh(mu_i / 1 yard) - defined for every real mu, all 8661 WR rows in one family; the negative-v1 refusal removed; beta unconstrained
   (the owner-map registration fixed no direction); new guard: every training and test sigma finite and strictly positive, else refused, no clipping.  Rejected: log(1 + |mu|)
   (erases sign), a shifted log (shift chosen from the seen minimum), a clamp (a floor), a separate law for negative mu (a 19-row exception), splines / additive now (skips the
   smallest lens).  Everything else as registered: baseline live Normal(v1, sd form 2), mean exactly v1, ML on earlier seasons, negative log density, harness.py f6 exact null B,
   work order 47a guard, diagnostic z^2 by mu quintile.  Registered once, judged once.
## WR RECEIVING YARDS LEVEL-DEPENDENT SCALE - OUTCOME - Oct 4 2026 (proj/f6_wr_receiving_yards_scale_report.txt, proj/harness_f6_report.txt)
Script sha256 4b11959f..., presence and hash checked before the run; 8661 rows, 19 negative v1 in domain.  Fits (alpha / beta): 2021 +2.7862 / +.1645, 2023 +2.5848 / +.2070,
   2024 +2.4682 / +.2328, 2025 +2.4241 / +.2424; sigma finite and positive everywhere; sigma at test mu P10 / P50 / P90 about 15-21 / 29-31 / 37 vs live sd 30-32.
   Negative log density 4.7907 -> 4.6668, gain +0.12312+-0.00704 (4/4), observed gate pass, tau/sigma .42, FP null A .0235, power 1.00 at 25 / 50 / 100%; FP null B exact
   2/16 = .125 > t .05 -> HARNESS FAIL.  VERDICT FAIL (first NO is the ceiling; not re-judged).  Diagnostic, no gate - mean z^2 by mu quintile baseline / candidate: Q1 (mu 2.0)
   .215 / .702, Q2 (11.0) .473 / .715, Q3 (24.8) .729 / .771, Q4 (44.3) 1.220 / 1.011, Q5 (73.6) 1.854 / 1.244.  Work order 47a, f6 mode: 62 recorded verdict rows reproduced
   unchanged by a full f6 re-judge, 1 added.  Open question (instrument, not this verdict): an all-positive, roughly 17-SE gain failing the exact null B at nS = 4 suggests
   the null may count sign-flip patterns that still pass the gate rather than patterns at least as extreme; harness.py's computation to be read before any finding.
## EXACT NULL B - CORRECTION OF THE OPEN QUESTION - Oct 4 2026 (harness.py run_slice lines 45, 53-55 read)
The WR scale OUTCOME's open question is withdrawn: exact null B does not count sign-flip patterns of the raw gains.  It centers the per-slate gains (dc = d - mean d), assigns
   one sign per season to all of its slates, enumerates all 2^S patterns and reports the share passing gate_v - the probability that between-season heterogeneity alone, under
   a zero mean, produces a gate pass (SCOPE DECISION A, CHARTER line 2357).  The WR scale wall's 2/16 reflects season heterogeneity of its gain (tau/sigma .42), not its size.
   The instrument behaves as registered; the WR scale verdict FAIL stands.
## DATA INTEGRITY READ - 2020 / 2021 - FINDING - Oct 4 2026 (owner question: is 2021 clean; COVID; read only, files on disk, nothing fetched)
Structure (load(), played rows): 2019 / 2020 weeks 1-17, 16 games per team (min = max); 2021 / 2023 / 2024 / 2025 weeks 1-18, 17 per team; 32 teams every season; 0 duplicate
   player-weeks; 0 null dk_points; teams per week show bye patterns only; F2 team targets 32 x 13 every season.  2022 absent by design (lines 99, 108, 397, 897-898).  No dirt
   found.  WR receiving yards: RMS(y - v1) 2020 31.69, 2021 29.60, 2023 29.60, 2024 28.99, 2025 28.00; by mean band 2020 is the outlier at low mu (mu <= 5: 18.44 vs 13.03-15.42;
   5-15: 23.82 vs 18.38-22.25), similar above; early-2020 WR rows per week fewer (weeks 4-6: 111-116 vs about 125-133); mean WR yards per row 35.0 -> 29.2 and zero share
   .254 -> .320 from 2020 to 2025.  Reading: 2020 is atypical (consistent in timing with COVID disruption; cause not measurable here), not unclean; the WR scale wall's 2021
   fold trains on 2020 alone - flatter beta (.1645), larger sigma at low mu (21.3 at test P10), the smallest gain (+.089) and the season deviation behind exact null B 2/16.
   The WR scale verdict FAIL stands; its 2023-25 per-season gains are seen and cannot be re-judged under any new training window.  Side finding: TE 2021 DK vs box differs
   more often (.0334 vs .017-.023) and by more (mean |diff| 2.49 vs 1.36-1.54); cause not measured.
## WORK ORDER 9 - PARTICIPATION STATE - ONE PRODUCER EXPOSED - REGISTRATION - Oct 4 2026 (owner / reviewer decision (e); reuse, not a second producer)
p.role_states already computes the season-to-date mean snap share over earlier team-games with a team-game the player did not play counted as 0 (sv, binned into
   season_role_state; CHARTER line 998) but does not return it; five callers (a, alloc, at_wall, purity, s) consume its frame and three write files.  Remedy: the three lines
   computing sv move into p.snap_share_season_mean_out_zero(P2) (P2 = role_states' sorted frame); role_states calls it; its return value unchanged.  Name: the played-games
   family is features()' snap_share_season_mean; this is its out-zero variant.  Consumers call role_states(P) and then the function on that frame.  Witness: sha256 of
   role_states(load()).to_csv() identical before / after; np.select bins of the new output equal season_role_state on every row; leakage - recomputed from earlier rows of the
   same player-season (did-not-play = 0) on 300 sampled rows, zero mismatches.  No fetch: snap_share is per game (published to two decimals); team snap totals are not derived.
   Side note: nflfastR receiving_yards excludes yards on plays with laterals (lateral_receiving_yards separate) - a candidate for the TE 2021 DK-vs-box difference, untested.
## WORK ORDER 9 - PARTICIPATION STATE - ONE PRODUCER EXPOSED - OUTCOME - Oct 4 2026
role_states(load()) sha256 identical before / after (89b1377c...); bins of snap_share_season_mean_out_zero equal season_role_state on 53154 of 53154 rows; leakage witness 0 of
   300 mismatches (max |diff| 2.2e-16); 48486 rows with a value, mean .371, range 0-1.  Closed.
## ROOT 1 OWNER MAP - PARTICIPATION EXTENSION (WR RECEIVING YARDS) - REGISTRATION - Oct 4 2026 (owner / reviewer; diagnosis only, no gate, no promotion, no forecast change)
Rows, targets, clip, folds: as the registered owner map (spine_compose_rows WR F5 receiving yards; z = Phi^-1(pit_comp clipped to the draw resolution); location z, scale z^2,
   asymmetry sign(z) z^2; leave one season out over 2021 / 2023 / 2024 / 2025 - 2020 is not in these rows, so every reading is already outside 2020).  Features: mu (frozen
   v1); snap_share_season_mean_out_zero (p.role_states then p.snap_share_season_mean_out_zero; work order 9); target_share_season_mean (p.features, played games only); any
   missing value refuses.  Lenses: L0 training constant; L2 mu, L2 snap, L2 target share (training deciles); A mu + snap, A mu + target share (two-feature backfitted bin
   effects, 20 sweeps).  Readings by p.paired_by_slate / p.passes_gate: each lens vs L0; snap after mu (A mu + snap vs L2 mu), mu after snap (A mu + snap vs L2 snap), the same
   pair for target share.  Registered map, scale primary: participation after mu passes and mu after participation fails -> role stability owns scale (a participation-
   conditioned variance wall next); both pass -> a two-feature additive scale law; participation after mu fails and mu after participation passes -> mean level owns scale (A3
   stands; the next scale lens or close); neither passes -> redundant proxies, owner not separable on these lenses.  One producer for the lens machinery: owner_map.py (edges,
   code, cells, keyed, additive); f6_root1_owner_map.py imports it and must reproduce its rows and report byte-identical.  Script f6_root1_owner_map_participation.py;
   proj/f6_root1_owner_map_participation_rows.csv, proj/f6_root1_owner_map_participation_report.txt.  Registered once, read once.
## ROOT 1 OWNER MAP - PARTICIPATION EXTENSION (WR RECEIVING YARDS) - OUTCOME - Oct 4 2026 (proj/f6_root1_owner_map_participation_report.txt; diagnosis only)
owner_map.py: the original owner map reproduced its rows and report byte-identical.  WR 6954 rows, held out 2021 / 2023 / 2024 / 2025 (no 2020 rows); correlations mu x snap
   .795, mu x target share .925, snap x target share .854.  SCALE (primary): vs L0 - L2 mu +0.32701 (4/4), L2 snap +0.24454 (4/4), L2 target share +0.29793 (4/4), A mu + snap
   +0.32553, A mu + target share +0.32056; snap after mu -0.00147+-0.00339 (2/4), mu after snap +0.08100+-0.02007 (4/4) -> mean level owns scale; target share after mu
   -0.00645+-0.00403 (1/4), mu after target share +0.02263+-0.01269 (3/4) -> redundant proxy.  READING: WR receiving-yard scale is owned by the forecast level, not role
   stability; the participation branch for WR scale closes.  Context, other targets (own lenses later): location - snap after mu +0.00450+-0.00220 (3/4) and target share
   after mu +0.01379+-0.00312 (4/4) pass, mu after each passes (both retain); asymmetry - target share after mu +0.03279+-0.01155 (4/4) and mu after it pass (both retain),
   snap after mu does not.
## WR RECEIVING YARDS FLEXIBLE ONE-DIMENSIONAL SCALE - REGISTRATION - Oct 4 2026 (owner / reviewer; blind; Root 1, A3-WR, the next lens after the log-linear FAIL)
Rows, baseline, score, harness and guard as the WR level-dependent scale wall: F5 receiving yards WR, frozen spine rows, test seasons 2021 / 2023 / 2024 / 2025, mean exactly v1
   (never mean_comp); baseline live Normal(v1, sd form 2); negative log density at y paired by slate; harness.py f6 exact null B; work order 47a guard (every recorded f6
   row identical, exactly one row added).  Candidate: Normal(v1, sigma_i), log sigma_i = alpha + f(u_i), u = asinh(v1 / 1 yard); f a continuous piecewise-linear spline with 3
   interior knots at the training seasons' quartiles of u (basis 1, u, (u - k1)+, (u - k2)+, (u - k3)+; 5 parameters); ML on earlier seasons (L-BFGS-B, unconstrained; no
   monotonicity imposed - the only direction evidence is a seen result); a non-converged fit refuses; every training / test sigma finite and > 0, else refused, no clipping.
   One dimension only: no snap, target-share or other term.  Diagnostic, no gate: mean z^2 by test-mu quintile, baseline / candidate.  Declared exposure: the 2021 fold trains
   on 2020 alone (the season behind the log-linear wall's exact null B 2/16).  PASS -> integration, then WR F8 tails and line 35 as consequence; FAIL -> the WR receiving-yard
   scale branch closes (constant, log-linear, participation, flexible one-dimensional all tested).  Script f6_wr_receiving_yards_scale_spline.py;
   proj/f6_rows_wr_receiving_yards_scale_spline.csv.gz, _params.csv, _report.txt.  Registered once, judged once.
## WR RECEIVING YARDS FLEXIBLE ONE-DIMENSIONAL SCALE - OUTCOME - Oct 4 2026 (proj/f6_wr_receiving_yards_scale_spline_report.txt, proj/harness_f6_report.txt)
Script sha256 401da9b4..., checked before the run; work order 47a guard: 63 recorded f6 rows unchanged, 1 added.  Knots (mu) per fold 12.8 / 33.7 / 53.0 (2021) ... 9.3 / 27.2 /
   51.5 (2025); sigma finite and positive everywhere; sigma at test mu P10 / P50 / P90 about 16-21 / 26-28 / 40-42.  Negative log density 4.7907 -> 4.6620, gain
   +0.12785+-0.00798 (4/4; per season 2021 +.08922, 2023 +.16302, 2024 +.13229, 2025 +.12829), observed gate pass, FP null A .0275, power .75 / 1.00 / 1.00; FP null B exact
   3/16 = .1875 > t .05 -> HARNESS FAIL.  VERDICT FAIL.  Diagnostic, no gate - mean z^2 by mu quintile baseline / candidate: Q1 .215 / .660, Q2 .473 / .966, Q3 .729 / .924,
   Q4 1.220 / 1.043, Q5 1.854 / .979.  As registered, the WR receiving-yard scale branch CLOSES (constant, log-linear, participation, flexible one-dimensional all tested).
   Structural observation (no action): both WR scale walls had large all-positive gains whose season heterogeneity comes chiefly from the 2021 fold, which trains on 2020 alone
   (atypical low-mu noise; data-integrity finding); the season-sign exact null B counts it (2/16, 3/16).  Any change to the training window is an owner decision for walls
   registered after it; neither WR scale family can be re-judged (their gains are seen).  Next on Root 1: TE receiving yards, location / skew.
## ROOT 1 OWNER MAP - TE RECEIVING YARDS LOCATION / ASYMMETRY OWNER DISCRIMINATION - REGISTRATION - Oct 4 2026 (owner / reviewer decision (a); diagnosis only, no gate, no promotion)
Rows: spine_compose_rows TE F5 receiving yards (component marginal PIT), held out 2021 / 2023 / 2024 / 2025 (no 2020 rows); z = Phi^-1(pit_comp clipped to the draw
   resolution).  Targets: location z (law null 0) and asymmetry sign(z) z^2 (null 0); scale excluded (no owner in the first map).  Axes: mu (frozen F6 v1 receiving-yards mean);
   snap_share_season_mean_out_zero (work order 9); target_share_season_mean (p.features); projected targets (frozen F5 targets v1); TD-history state (F5 TDs state_v1); any
   missing value refuses.  Lenses (owner_map.py; leave one season out): L0 training constant; L2 each axis alone (training deciles / categories); A mu + candidate for each of
   the four candidates (two-feature backfitted bin effects, 20 sweeps).  Primary readings by p.paired_by_slate / p.passes_gate: candidate after mu (A mu + c vs L2 mu) and mu
   after candidate (A mu + c vs L2 c) for each candidate; a comparison with any not-estimable fold is not read and does not count as adding.  Registered tree, per target: no
   candidate adds beyond mu -> mu owns it; exactly one adds -> projected targets: opportunity-conditioned; snap or target share: role-state mechanism; TD state: TD-history
   state split earned; two or more add -> a two-feature additive law justified only among those.  Ordering: if mu owns location, the first TE wall is the smallest location
   (mean recalibration) wall and asymmetry is re-scored after it - center before shape.  Script f6_root1_owner_map_te.py; proj/f6_root1_owner_map_te_rows.csv,
   proj/f6_root1_owner_map_te_report.txt.  Registered once, read once.
## ROOT 1 OWNER MAP - TE RECEIVING YARDS LOCATION / ASYMMETRY OWNER DISCRIMINATION - OUTCOME - Oct 4 2026 (proj/f6_root1_owner_map_te_report.txt; diagnosis only)
TE 4235 rows, held out 2021 / 2023 / 2024 / 2025.  Correlations: target share x projected targets .982, mu x projected targets .955, mu x target share .947, snap .77-.82.
   LOCATION (z mean +.149): target share after mu +0.01287+-0.00265 (4/4), projected targets after mu +0.01072+-0.00267 (4/4) - both pass, mu after each passes; snap after mu
   +0.00643+-0.00357 (4/4, below 2 SE); TD state after mu -0.00051.  ASYMMETRY (mean +.510): target share after mu +0.04690+-0.01744 (4/4), projected targets after mu
   +0.04341+-0.01652 (4/4) - both pass, mu after each passes; snap +0.00101, TD state -0.00035 do not.  READING (both targets): several add beyond mu (target share,
   projected targets); TD-history state and snap share do not own TE receiving-yard location or asymmetry.  Registered order: location first, asymmetry re-scored after.
## TE RECEIVING YARDS OPPORTUNITY DECOMPOSITION - REGISTRATION - Oct 4 2026 (owner / reviewer; diagnosis only, no gate, no promotion; location primary, asymmetry context)
Rows, targets, clip, folds and machinery as the TE owner map (owner_map.py).  Axes: mu; target share (target_share_season_mean); projected team targets (F2 team targets v1,
   joined player -> team as spine_compose.py line 179, team-week as line 184); projected targets (frozen F5 targets v1).  Lenses: L2 mu; A mu + target share; A mu + projected
   team targets; A mu + target share + projected team targets; A mu + projected targets.  Comparisons (p.paired_by_slate / p.passes_gate): team after mu (A mu + team vs L2 mu);
   team after mu + share (A mu + share + team vs A mu + share); share after mu + team (A mu + share + team vs A mu + team); product over decomposition (A mu + projected targets
   vs A mu + share + team).  Witness: A mu + target share and A mu + projected targets reproduce the TE map's per-season errors exactly, else refused.  Registered tree
   (location): product over decomposition passes -> opportunity-conditioned mean (the spine's projected targets); else share after mu + team passes and team after mu + share
   fails -> role-share correction; both pass -> team volume + role; team after mu + share passes and share after fails -> team-volume correction; neither passes -> share and
   team volume not separable here (proxy overlap).  Script f6_root1_owner_map_te_opportunity.py; proj/f6_root1_owner_map_te_opportunity_rows.csv, _report.txt.  Registered once,
   read once.
## TE RECEIVING YARDS OPPORTUNITY DECOMPOSITION - OUTCOME - Oct 4 2026 (proj/f6_root1_owner_map_te_opportunity_report.txt; diagnosis only)
Witness: A mu + target share and A mu + projected targets reproduced the TE map's per-season errors exactly (both targets).  Correlations: projected team targets vs mu .063,
   vs target share -.005; projected targets vs target share .982.  LOCATION (primary): team after mu -0.00009+-0.00147 (2/4); team after mu + share -0.00096+-0.00125 (2/4);
   share after mu + team +0.01200+-0.00255 (4/4); product over decomposition -0.00119+-0.00312 (1/4) -> READING: ROLE-SHARE CORRECTION.  Asymmetry (context): share after mu +
   team +0.04326+-0.01720 (4/4), team after mu + share -0.01286+-0.00636, product over decomposition +0.00937+-0.01336 (2/4) -> role-share correction.  Team passing volume does
   not own TE receiving-yard location or asymmetry; the spine's projected targets carries nothing beyond season-to-date target share.  Location magnitudes (two maps): training
   constant vs law null +0.02282 (z mean +.149, under-forecast), mu over the constant +0.01000, share beyond mu +0.01287.  Next: the smallest TE location wall, mean + role-share
   correction (form by owner decision), then recompose, re-score PITs, re-read asymmetry.
## TE RECEIVING YARDS LOCATION - LINEAR RECALIBRATION WITH ROLE SHARE - REGISTRATION - Oct 4 2026 (owner / reviewer decision (a); blind; Root 1, A1-TE)
Rows: F5 receiving yards TE, frozen spine rows (apply_freeze), y and the registered mean v1; target share s = p.features target_share_season_mean (earlier played games);
   any missing value refuses.  Test seasons after the first (2021, 2023, 2024, 2025); 2020 training only (declared exposure: the 2021 fold trains on 2020 alone).  Baseline:
   the live law, Normal(v1, sqrt(phi_b max(v1, 1))), form 3, phi_b = mean((y - v1)^2 / max(v1, 1)) on earlier seasons (compose's live form line must match).  Candidate:
   mu* = a + b v1 + c s, a / b / c by ordinary least squares on earlier-season realized receiving yards; Normal(mu*, sqrt(phi_c max(mu*, 1))), phi_c refit on the same training
   rows around mu* (41(a) precedent); no sign constraints, no floor on mu* (max(mu*, 1) is the registered form-3 variance law, not a mean floor).  Identical held-out rows.
   Score: negative log density at y, paired by slate; rows null_b exact; verdict harness.py f6 (exact null B); work order 47a guard (every recorded f6 row identical, exactly
   one row added).  Diagnostic, no gate: mean z by target-share quintile, baseline / candidate; rows with mu* < 0.  PASS -> integration (compose TE receiving yards take mu*
   and phi_c), recompose, regenerate PITs, re-run the TE asymmetry diagnostic from scratch on the changed marginals (the old asymmetry magnitude not carried forward); FAIL
   -> the simple TE location mechanism closes (residualized / nonlinear share is the next lens, its own registration).  Script f6_te_receiving_yards_location.py;
   proj/f6_rows_te_receiving_yards_location.csv.gz, _params.csv, _report.txt.  Registered once, judged once.
## TE RECEIVING YARDS LOCATION - LINEAR RECALIBRATION WITH ROLE SHARE - OUTCOME - Oct 4 2026 (proj/f6_te_receiving_yards_location_report.txt, proj/harness_f6_report.txt)
47a guard: 64 recorded f6 rows unchanged, 1 added.  Fits: a +1.4 to +2.0, b +.39 to +.52, c +103 to +148; phi 32-37 -> about 20; no mu* < 0.  Gain +0.07014+-0.01201 (4/4;
   2021 +.074, 2023 +.110, 2024 +.052, 2025 +.038), observed gate pass, FP null A .0224, power .31 / .75 / 1.00; FP null B exact 1/16 = .0625 > t .05 -> HARNESS FAIL.  VERDICT
   FAIL; the live TE law unchanged; not re-run under any changed null, window or parametrization.  Diagnostic: mean z +.1619 -> -.0005, every target-share quintile near zero.
   The simple TE location branch CLOSES (strong diagnostically, not promoted).  Observation (no action): three walls with strong all-positive gains failed exact null B at nS 4
   (2/16, 3/16, 1/16); here the season heterogeneity is 2023 high / 2025 low, not the 2021 fold.
## TE RECEIVING YARDS MEAN- AND VARIANCE-PRESERVING SKEW - REGISTRATION - Oct 4 2026 (owner / reviewer; blind; Root 1, TE shape - independently diagnosed on the live marginals)
Rows: F5 receiving yards TE, frozen spine rows, y and v1; s = target_share_season_mean (p.features); any missing value refuses; tests 2021 / 2023 / 2024 / 2025.  Baseline: live
   Normal(v1, sigma), sigma = sqrt(phi_b max(v1, 1)), form 3, phi_b on earlier seasons.  Candidate: skew-normal with shape alpha_i = a + c s_i, parameterized so its mean is
   exactly v1 and its sd exactly sigma (delta = alpha / sqrt(1 + alpha^2), omega = sigma / sqrt(1 - 2 delta^2 / pi), xi = v1 - omega delta sqrt(2 / pi)); alpha = 0 is the
   baseline; a and c by maximum likelihood on earlier seasons (L-BFGS-B, unconstrained); a non-converged fit refuses.  Witness on every test row: candidate mean = v1 and sd
   = sigma (max |diff| <= 1e-8), else refused - the skew cannot carry the failed location correction.  Family limit stated: skew-normal |skewness| < .995.  Score: negative log
   density at y, paired by slate; rows null_b exact; harness.py f6 exact null B; 47a guard.  Diagnostic, no gate: mean sign(z) z^2 of the PIT normal score (clip 0.00025),
   baseline vs candidate; alpha by share quintile.  PASS -> integration, then F8 tails as consequence; FAIL -> the TE receiving-yard location / shape branch closes.  Script
   f6_te_receiving_yards_skew.py; proj/f6_rows_te_receiving_yards_skew.csv.gz, _params.csv, _report.txt.  Registered once, judged once.
## TE RECEIVING YARDS MEAN- AND VARIANCE-PRESERVING SKEW - OUTCOME - Oct 4 2026 (proj/f6_te_receiving_yards_skew_report.txt, proj/harness_f6_report.txt; consequence pending owner decision)
Harness: gain +0.01960+-0.00579 (1/4), gate fail, FP null B exact 4/16 -> HARNESS FAIL; 47a guard 65 unchanged, 1 added.  Fits: 2021 a +2.8690, c +22.059 (alpha on test rows
   +2.87 to +8.38, gain +.07804); 2023 / 2024 / 2025 a = c = 0.0000 exactly - the baseline, gains 0.00000 - the optimizer reported success at its registered start.  Mean / sd
   witness held (<= 2.1e-14).  INSTRUMENT DEFECT (disclosed): in the registered mean- and variance-preserving parameterization the log-likelihood's slope in alpha is
   exactly zero at alpha = 0 for every row (shape term 2 phi(0) z = sqrt(2/pi) z cancels the location term (z / sigma) d xi / d alpha = -sqrt(2/pi) z; d omega / d alpha = 0) -
   the centred skew-normal singularity; L-BFGS-B started at (0, 0) cannot leave it, and the convergence guard did not fire.  The candidate was not fitted in 3 of 4 folds;
   2021's fitted gain is seen.  Whether this verdict stands (branch closes) or is treated as an instrument failure (identical family re-run from a non-stationary start, with
   2021's seen gain disclosed): owner decision.
## TE RECEIVING YARDS MEAN- AND VARIANCE-PRESERVING SKEW - OWNER DECISION - Oct 4 2026 (owner / reviewer decision (c))
The HARNESS FAIL stands for this family and implementation (defect disclosed); it is not re-run from another start.  The TE skew hypothesis stays open only for a different,
   properly initialized skewed family registered later on its own terms (non-stationary start or profile / grid over the shape parameter built in from the outset).
## PROSPECTIVE FRAMEWORK - LAYERS A-D - REGISTRATION OF DIRECTION - Oct 4 2026 (owner / reviewer; forward-only; no historical verdict changes)
Principle: simulation calibrates the judge; reality supplies the verdict.  Layer A - historical real-data walk-forward: mechanism discovery; every recorded verdict frozen,
   never re-judged under a new rule.  Layer B - training-conditional simulation of whole games / slates (team volume, participation / role, native marginals, earned
   dependence only), running the full candidate-fit and judging pipeline: false-positive rate, power at injected effects, gain distributions, probability the season-sign
   rule passes, parameter variability, one-odd-season sensitivity; zero votes in any verdict.  Layer C - 2026 prequential shadow trials: for each 2026 week, baseline and
   candidate fit only on information before that week, predictions frozen and hashed before kickoff, scored after; weekly paired losses accumulate under a sequential rule
   registered and Layer-B-calibrated before any 2026 week is scored; states PROSPECTIVE PASS / FAIL / INCONCLUSIVE.  Layer D - promotion: only real evidence changes a live law.
   SHADOW ELIGIBLE: strong historical observed gain, consistent signs, failed only exact-null-B resolution, no governance defect - runs in Layer C beside the live law without
   altering it; a family that FAILed historically may enter a shadow trial only as prospective evidence on data that did not exist at its discovery - its historical verdict
   unchanged.  Training contract: one procedure for every fold and week (strictly-earlier data, eligibility, features, loss, optimizer and start rule, selection, any season
   weighting as one fixed forward-only formula - no COVID exception, minimum history, random streams, refit from scratch); a manifest per fit (candidate, cutoff, training
   seasons, n, feature hashes, parameter hash).  Open premises before Layer C: 2026 outcomes for weeks 4+ (the standing no-new-fetch rule applies - ingestion is an owner
   decision), prospective means from week mode, and the sequential rule itself.
## PROSPECTIVE FRAMEWORK - INGESTION FACT - CORRECTION - Oct 4 2026 (read of fetch.py and CHARTER lines 92, 150-153)
The framework's "open premise" calling 2026 ingestion an owner decision under the no-new-fetch rule is withdrawn: the owner's rule covers history; 2026 live weeks are already
   ingested by the one fetcher (line 150, owner 2026-10-02: fetch.py, seasons > FROZEN_THRU only; weekly cycle line 153: fetch.py 2026 N -> guard.py -> guard.py --accept ->
   facts.py -> s.py 2026 N; line 92: the weekly nflverse refresh live building already needs, no historical fetching).  Layer C attaches to the existing 2026 prospective
   machinery (register_2026.json and addenda, l_weeks, weekly issues; lines 209, 1177, 1180) - one prospective clock, not a second.
## PROSPECTIVE FRAMEWORK - OWNER DIRECTIVE (WEEK 4) AND REVIEWER AMENDMENT - Oct 4 2026 (owner: "pretend week 4 never started"; reviewer note on the read below)
Owner directive: 2026 week 4 is treated as not started (incomplete).  At the read: team_game 2026 plays non-null weeks 1-3 32 each, week 4 0; player_game week 4 680 rows,
   played null 680; issued_y / issued_d / issued_s 2026 w4 present read-only (Oct 3 07:35 / 07:37 / 07:43 local).  No week-4 outcome enters any fit, score or simulation.
   Real clock: recorded Oct 4 16:23 EDT, after week-4 kickoffs.  L1177 ("next NFL week whose games have not begun") and L1180 (a challenger starts from the next untouched
   week) are not reconciled with the directive here; reconciliation precedes any Layer C issue (work order 48 (5)).
Read facts (harness.py sha256 4aefa950...; ledger 2974): no script imports harness.py or calls stats / gate_v / run_slice outside it; harness.py executes its mode code at
   import; every exact-null-B f6 slice has 13 slates in each of 2021, 2023, 2024, 2025; FP null B exact is computed from the centred gain only (harness.py L49, L51).
Reviewer amendment (supersedes the unapplied design that extracted functions from harness.py): harness.py stays unmodified as Layer A, historical only.  Layer B estimates
   operating characteristics only and supplies no inferential observation; a stopping boundary chosen on simulated seasons is not an exact test.  Prospective verdicts live in
   their own append-only file (proj/prospective_verdicts.csv), never in harness_*_verdicts.csv; a historical HARNESS FAIL row is never replaced.  Shadow states: REGISTERED ->
   SHADOW ACTIVE -> PROSPECTIVE PASS / PROSPECTIVE FAIL / PROSPECTIVE INCONCLUSIVE; no shadow changes a live forecast.  Reviewer preference, recorded, not registered: fixed
   interim looks after weeks 7, 10, 13, 16 with alpha spending summing to <= .05; the sequential rule is registered on its own, before its first look.
## WORK ORDER 48 - PROSPECTIVE TRAINING CONTRACT + HISTORICAL REPLAY - REGISTRATION - Oct 4 2026 (reviewer; precedes the Layer B simulator)
(1) fit_contract.py: one fit_at(cutoff) for baseline and candidate.  Frozen: eligible seasons and rows; evaluated weeks 4-16; feature producers and their sha256; missing-data
   rules; expanding or rolling window rule; season weighting; optimizer; initialization; hyperparameter search; RNG construction; convergence rules; baseline and candidate
   refit rules; score definition.  Season weighting is one universal law (or equal weight per training season), never a named-season exclusion.
(2) prospective_manifest.py: per fit {cutoff, training rows sha256, producer sha256s, parameters, prediction sha256}.
(3) Acceptance - historical replay: every historical cutoff replayed through fit_at reproduces the existing baseline / candidate predictions and per-row scores byte-identically
   where the law is unchanged.  First targets: the rows files of the SHADOW ELIGIBLE nominations (WR scale log-linear, WR scale spline, TE location).  Any difference -> refused,
   reported.  Their scripts are read (decls, whole) before the build.
(4) Then, in order: simulate_prospective.py (Layer B: whole path fit -> freeze -> slate -> score -> update -> refit across weeks; null regime and 0.25 / 0.5 / 1.0 x observed
   effect; unearned dependence stays independent), prospective_score.py, prospective_judge.py (the separately registered sequential rule only).
(5) Open before Layer C: the week-4 directive against L1177 / L1180; SHADOW ELIGIBLE confirmed per nomination (TE skew excluded - defect, owner decision (c)).
Instrument note: p.py passes_gate not read (the def-extraction sed failed on the last def in p.py); not a premise of this registration.
## HISTORICAL STRUCTURAL FORECASTING PROGRAM - OWNER BAN ON WAITING FOR 2026 WEEKS - REGISTRATION OF SCOPE - Oct 4 2026 (owner: "ban the idea of waiting for week 4 +, thats not going to happen"; reviewer note)
Owner ban: no work waits on 2026 week 4 or any later week; no 2026 week >= 4 outcome enters discovery, fitting, calibration, simulation or adjudication.  In force now:
   register_2026.json H1-H6, register_2026_addendum.json and addendum2 (H1) and register_2026_addendum3.json (H7): WITHDRAWN - not awaited (owner ban); the files stay read-only
   and unedited; no result of them is computed.  issued_y / issued_d / issued_s 2026 w4 stay on disk, never scored.  L209, L233, L326, L397 no longer name a judge.  Layer C
   (2026 shadow trials), the sequential prospective rule, SHADOW ELIGIBLE and the shadow states recorded in the owner directive and reviewer amendment above: withdrawn.
Program scope (reviewer; adopted by the owner ban): learn pregame-observable mechanisms from the fixed historical corpus.  Cross-fitting supplies empirical evidence; simulation
   supplies generative and counterfactual diagnostics only.  Rule: simulated outcomes can test a model's implications but never increase its empirical sample size - Monte Carlo
   draws reduce Monte Carlo error only; n stays the number of observed held-out games / slates.  A forecast for a held-out game uses drawn mediators (drawn targets, drawn
   receptions), never that game's realized in-game values.  "Causal" only for mechanisms with stated identification assumptions; otherwise "structural / predictive".
Layer A unchanged: harness.py and every recorded harness verdict stay frozen; no re-judgment; exact null B stays the gate of every existing registration.
Work order 48 amended.  (1)-(3) unchanged: one fit_at engine reproducing history is the cross-fitting engine.  (4) replaced: structural posterior predictive checks - per
   held-out historical pregame state, M draws from the out-of-fold fitted law; statistics compared observed vs simulated: P10 / P90 coverage, PIT variance, zero rate,
   component co-failure and co-exceedance, target / reception / yard association, team concentration, cross-player association, lineup variance; mechanism ladders
   (independent components -> targets -> receptions -> shared role / game state -> shared team passing environment) read by how much each step shrinks the observed-minus-
   implied gap; null and injected-effect simulations measure a procedure's false-promotion rate and power.  (5) replaced: forward-only promotion standard for newly registered
   mechanisms - cross-fitted score gain, calibration gain, the targeted defect shrinks, stability across seasons / teams / weeks, null calibration, power - direction only;
   thresholds and any hierarchical or block-resampling gate on held-out loss differences are registered on their own, with operating characteristics from (4), before first
   use.  Until then no new mechanism is promoted.
Not addressed by this entry: the live issue path (L150-153 weekly flow; spine.py issue mode).  Open: 2026 weeks 1-3 (in facts: player_game rows 1345 / 1344 / 1366, team_game
   32 / 32 / 32) - status in the program corpus undecided.  At the read no exact-null-B slice uses 2026 (all 2021, 2023, 2024, 2025, 13 slates each).
## FORECASTABLE RESIDUE PROGRAM - OPERATING LOOP - REGISTRATION OF DIRECTION - Oct 4 2026 (reviewer note; owner: "reframe around the previous ban")
Inside the Historical Structural Forecasting Program every wall is forecastable structure plus residue.  Descend in information order: available -> participation -> team
   opportunity -> player share -> player opportunities -> conversions -> yards / TDs -> DK points.  Per statistic: support -> location -> scale -> shape -> structural
   dependence -> residual dependence (no copula repairs a marginal, no skew repairs a center, no latent state repairs an explicit component link).  A NO closes that
   formulation only; the next wall is the next distinct owner one level down, never a retune of the failed formulation.
Loop per blocker: state the decision failure; define the observed discrepancy Delta on held-out historical rows; list owners in causal order; test only the first unresolved
   owner; recompose the full simulation; fraction explained = 1 - |Delta after| / |Delta before|; repeat on the residue.  Stop at calibration-noise size, at exhausted
   owners, or when the residue cannot change BASE / FLOOR / CEILING lineup ordering (operational relevance is a wall).
Failure classes for every new NO: (1) no signal - closed; (2) signal, wrong family - verdict frozen, pursued only through a different family earned by a lower diagnosis;
   (3) signal, insufficient resolution - not promoted, recorded as unresolved mechanism evidence; (4) operationally irrelevant - closed for the current optimizer.
   Recorded verdicts unchanged; read in these classes: WR scale log-linear, WR scale spline, TE location (harness_f6_report L161, L164, L146: observed gate pass 4/4,
   exact null B 2/16, 3/16, 1/16) are class (3); TE skew stays as recorded (implementation defect, owner decision (c)).
Simulation boundary (reconciles L1175-1176 "procedures ..., never mechanisms, and never select among candidates"): a simulation is the reference distribution for a
   statistic computed on observed held-out rows; Delta and fraction explained are observed-minus-implied quantities; no candidate is selected or promoted by a simulated
   outcome.
Work order 31 reframed: the question is the fraction of the observed RB / WR q.90 joint-exceedance gap (recorded +.22 / +.20, 4/4; proj/f8_tail_joint_downside_rows.csv)
   removed by drawn targets -> drawn receptions given drawn targets in the recomposed simulation - work order 48 (4), first ladder.
## 2026 DEPENDENCE REFRAMED - Oct 4 2026 (owner: "anything that currently depends on 2026 should reframe"; read of CHARTER L86-100, L140-175, L255-295, L399-430, L455-548, L612-624, L655-680, L868-890, L1172-1185, register_2026.json, addendum3, facts coverage)
Facts: FROZEN_THRU 2025; salary non-null 2019 6040 / 2020 6232 / 2021 6762, 2023-2026 0; dst_salary 510 / 508 / 544, 2023-2026 0; candidates 2019-25 7550 / 7828 / 8183 /
   8116 / 8100 / 8213.  Names reused: whole-pipeline null (L168), whole-pipeline twin (L269).  Status words: HISTORICAL STRUCTURAL PASS / FAIL / NOT EVALUABLE (missing input,
   or no clean held-out route); "confirmed" is not used for these.  A design chosen on the seasons that judge it carries the whole-pipeline null of its recorded design
   procedure; without a recorded procedure it is a same-rule consistency check (L265 wording), not clean.
L86, L94, L104, L148, L1178, L1213 (L v2, DK lineup judge from 2026 w4): judge withdrawn.  Realized-lineup judgment on history NOT EVALUABLE as clean - prices 2019-21 only,
   P and A fit on 2019-21 (H0, L539-540), pools outcome-selected, MDD ~13 DK on 26 slates (L542).  Lineup questions go to decision residue: outcome-free ordering effects
   (as jexpose); realized comparison only after a registered power wall (L544).
L93 (L v1 judged 2026 w3): provenance, unchanged.
H2 (DST-V1 calibration): H2's rule and grid on held-out seasons with V1 refit through fit_at (work order 48); design condition above.
H3 and L265 (WR-short; frozen k-selection procedure): the frozen procedure replayed walk-forward through fit_at on held-out seasons, H3's grid and rule; design condition above.
H4 (A p_play calibration): answered outside A's fit seasons by AT (L623: 2023-25, 9 / 9 cells fail vs null 95th 11.1% -> STRUCTURAL); no new test.
H5 (teammate tail after a new real-role absence; descriptive): posterior predictive check - observed teammate boom rate vs the rate implied by the current law at the same
   historical pregame states (classe.py section 5 definitions); no gate.
H6 (week-N salary change trigger): inputs 2019-21 only, Y RESULT from 2020 -> rows 2020-21; the trigger came from the seen salary-timing study (L455-456) -> route only with the
   whole-pipeline null of that study's search; otherwise NOT EVALUABLE.
H7 (T1 availability): T1 cells fit on all 2020-25 rows (L658-659, in-sample); route: h7.py V1's walk-forward T1 (at_t's at_pool, 20,764 rows; L670) judged by H7's
   construction on held-out seasons, both grids.
L881 (no T1 domain extension before the 2026 confirmation): condition removed; the domain map (170 historical 3+-game rows, L883) and a domain-extension wall may be
   registered on history; AT end-to-end reruns from its registration if that wall earns.
L459 (W0-W4 timing / price / role / tail; designed on seen 2019-25 data): route only with the whole-pipeline null of the design search; W2 (price) rows 2019-21 only.
L474 corner family, L485, L494, L510, L535 (J corners): J tail branch CLOSED for the current architecture (L531-533, W1 NO) - failure class (4); reopens only when a selector
   that uses J is registered, no date.  L485 (1) answered by jexpose; (2) and (3) moot while (1) is closed.
L474 slot-conditioned Y tail calibration: Root 1 (shape) wall candidate under cross-fitting, with its own null.
L538, L544 (selector ladder A0-A3): decision residue; W0 (outcome-free) open; realized walls NOT EVALUABLE (in-sample / underpowered, L539-544) until a power wall says otherwise.
L619 (AT lever map "POST-2026 candidates"): Root 1 support-layer (availability) wall candidates under cross-fitting; Y stays a distribution given he plays (L287).
L1177, L1180 (spine prospective start; challenger clock): "first prospective test" and "new prospective clock" withdrawn; a challenger is a new historical wall under work
   order 48 (5); the walk-forward and procedure-gate parts stand.
Pending a whole read (work order): L225-254 (H1 YARDSTICK and 2026 CONFIRMATION RULE L244, Ford L233, labels judged by L L254), L320-330 (Class E, L326), L436-450
   (season-clustered gate as a POST-2026 procedure item - input to work order 48 (5)), L900-905.
## 2026 DEPENDENCE REFRAMED - ADDENDUM - Oct 4 2026 (read whole: CHARTER L225-254, L318-332, L434-452, L898-906)
H1, L232-233, L244-246 (SC yardstick; 2026 CONFIRMATION RULE): NOT EVALUABLE as clean - the yardstick was designed on every corpus season (L236 "calibration research on
   2019-25 STOPS") and SC was selected on a partially used 2024-25 holdout (L232).  The recorded reading stands as a same-rule consistency check: SC 10.3% = null 95th
   10.3%, noise-like at the boundary (L243).  SC stays frozen as the yardstick with the L248 frozen list.  Its calibration becomes a Root 1 posterior predictive check under
   fit_at refits on held-out seasons, same subgroup grid and null procedure - a diagnostic, never a confirmation.  "Neither -> reopen" is replaced: a structural miss in that
   check is a residue blocker in the loop.
L225 (C isotonic pi, "challenger for 2026 at most"): withdrawn; C stays diagnostic only (L232).
L254 (labels judged by L on 2026 weeks): no route; no labels.  A label rule exists only if registered as a decision-residue wall.
L326-328 (Class E): no 2026 judge; the timing condition "after the 2026 cycle" removed.  The late-information track (Y_late) stays optional and a separate forecasting
   problem with its own information timestamp; whether its week-N availability inputs exist in the historical corpus is not read (work order).
L441, L448 (season-clustered or season-permutation gate, "POST-2026 procedure item"): input to work order 48 (5); measured motive L436-440 (p.gate false pass 14-19% at
   season-effect sd .5).
L903 (J-using selector, "the POST-2026 wall at L535"): covered by the L535 row of the reframe table.
Not classified (fragments, no judge named): L2369, L2380 (F9 shadow optimizer, 2026 week 4).
## WORK ORDER 48 - FIT CONTRACT v1 AND HISTORICAL REPLAY - REGISTRATION - Oct 4 2026 (read whole: the three replay targets, p.py decls, freeze.py decls, p.descriptors)
Corpus: p.py L16 FROZEN_THRU = 2025 ("every producer fits on seasons <= this"); the replay targets' test seasons are 2021, 2023, 2024, 2025 - 2026 weeks 1-3 enter no fit at
   current law; a change is an owner registration.  The open 2026 weeks 1-3 line closes at current law.
CONTRACT v1 = the current behaviour of the replay targets, nothing new: rows proj/spine_rows.csv.gz after freeze.apply_freeze, one (term, position) slice; cutoff = a season;
   training = season < cutoff (expanding window, every row weight 1, no season weighting, no named-season exclusion); held out = season == cutoff; cutoffs = every slice
   season after the first; scipy L-BFGS-B default tolerances, start per law (log live spread; zeros for spline terms); OLS for the location law; no hyperparameter search;
   no random draws; refusal (no verdict, no clipping, floor or fallback) on missing inputs, duplicated keys (now every target), empty folds, non-convergence, non-finite or
   non-positive sd or mean; score = negative normal log density at y.
fit_contract.py: TARGETS (wr_receiving_yards_scale, wr_receiving_yards_scale_spline, te_receiving_yards_location; recorded stage strings and params columns), slice_rows,
   fit_at(target, cutoff) -> predictions, params row, manifest {cutoff, training rows sha256, producer sha256s (spine_rows.csv.gz, freeze.py, p.py, fit_contract.py),
   parameters, prediction sha256}.  Work order 48 (2) is folded into fit_contract.py (one producer; the name prospective_manifest.py retired with the withdrawn wording).
ACCEPTANCE (registered once, judged once): python3 fit_contract.py replay; for each target the rows file's decompressed CSV payload and the params file's text equal the
   replay's to_csv text exactly -> REPLAY ACCEPTED; any difference or refusal -> REPLAY REFUSED, reported with the first differing line, nothing rescued.  fit_contract.py
   writes only proj/fit_contract_replay_report.txt and proj/fit_contract_manifest.csv; no rows, params, harness or verdict file changes (witness hashes before and after).
Reframe rows: Class E late-information inputs exist historically (p.descriptors report_status / practice_status / status non-null 2019-25, e.g. report_status 2460 / 2453 /
   2494 / 2670 / 2749 / 2678); guard check 10 forbids them as inputs, so Y_late needs its own information-set registration.  L2369, L2380 (F9 shadow optimizer, 2026 w4):
   issue records on the live issue path, no judge, never scored.
## WORK ORDER 48 - FIT CONTRACT v1 AND HISTORICAL REPLAY - OUTCOME - Oct 4 2026 (proj/fit_contract_replay_report.txt, proj/fit_contract_manifest.csv)
fit_contract.py sha256 36fc03b3d0fbedccc09c133cc16b74ce102f1493d64ed60db61701cd879eccad; producers spine_rows.csv.gz 7b939592..., freeze.py 415a378d..., p.py 551886a5....
Replay (first run, the verdict): wr_receiving_yards_scale 6954 held-out rows, cutoffs 2021 / 2023 / 2024 / 2025, rows payload IDENTICAL, params text IDENTICAL;
   wr_receiving_yards_scale_spline 6954, IDENTICAL / IDENTICAL; te_receiving_yards_location 4235, IDENTICAL / IDENTICAL -> REPLAY ACCEPTED (exit 0); 8 witness files
   unchanged (harness.py, harness_f6_verdicts.csv, the three rows files, the three params files).  Manifest 2021 cutoff WR scale: train 1707, held out 1704, alpha
   2.78620, beta .16447 = the recorded fit (WR scale OUTCOME 2021 +2.7862 / +.1645).
Procedure note: the restore block was run after acceptance (instruction defect - it was not marked failure-only) and removed fit_contract.py and both outputs;
   fit_contract.py was recreated byte-identical (sha256 checked) and the replay reproduced: three IDENTICAL / IDENTICAL, REPLAY ACCEPTED, harness and verdict witnesses
   unchanged.  The verdict is the first run's; the reproduction is a witness.  Restore blocks are marked failure-only from here on.
Consequence: one fit_at engine reproduces the three recorded targets; it is the cross-fitting engine for work order 48 (4).  The three f6 scripts stay as recorded
   producers of their rows files; moving them onto fit_at is a separate transaction.
## WORK ORDER 31 - OPPORTUNITY-CHAIN LADDER - REGISTRATION - Oct 4 2026 (owner / reviewer decision (b); work order 48 (4) first ladder)
Structural fact (code read, spine_compose.py L77, L145-161): the q .90 pattern statistic counts F5 receptions, F5 receiving yards, F5 rushing yards, F5 TDs; receiving yards,
   rushing yards and TDs are drawn independently of targets and receptions; targets are not counted.  Recoupling receptions to targets with the reception multiset unchanged
   leaves the joint law of the counted components unchanged: L1's upper-tail attribution is 0 by construction, not by empirical failure.
Ladder (RB, WR; cumulative): L1 targets -> receptions; L2 receptions -> receiving yards; L3 volume -> TDs (WR: receptions; RB: carries + receptions); L4 residual shared
   state owns what the explicit links leave (RB rushing yards reachable only through carries -> rushing yards or shared state).  Each rung has its own native wall and
   verdict; only an earned rung enters the cumulative chain; a failed rung does not.  Attribution is consequence-only, never a gate.
Attribution: Delta(k) = observed share of two or more components beyond their own tail among q .90 F8-tail rows - the cumulative model share after the earned rungs <= k
   (f8_tail_attribution.py definitions, per slate, mean +- slate SE, per season); Delta(0) = recorded RB +.2223, WR +.1964 (L2715).  E2 = 1 - |Delta(2)| / |Delta(0)|;
   E3|2 = (|Delta(2)| - |Delta(3)|) / |Delta(0)|; overshoot or sign reversal reported as such.  Stop rule: explicit-chain work continues only while an unresolved direct
   football mechanism can move another counted component; then the residue R = |Delta| is the shared-state candidate (Root 3 earned, not assumed).
Construction (every rung): rank-reorder of the existing draw multisets per row (the walls 9 / 10 construction; multiset unchanged or refused, nothing written); the ordering
   comes from an auxiliary draw of a structural law fit on earlier seasons only; every marginal exactly unchanged; no ratio of frozen means (coherence ruling L1957-1963
   not engaged).  Verdict policy L2653: wall 1 (under D) verdicts stay as recorded for the marginals they judged; this is a new wall on the current marginals.
L1 SPECIFICATION: auxiliary A = Binomial(T_draw, p_pos) per draw, T_draw = the composition's own F5 targets draws (WR share of the team draw; RB work order 19 hurdle draws),
   p_pos = sum realized receptions / sum realized targets over earlier-season rows of the position; reception draws reordered per row to the ranks of A (stable argsort;
   ties by draw index).  Own stream default_rng(20261011); rng, rng8, rng_copula, rng_clayton, rng_pattern untouched; every existing compose output byte-identical (decompressed)
   or restore whole.  Rows RB / WR, tests 2021, 2023, 2024, 2025.  Native score: energy score of the (targets, receptions) draws against realized (targets, receptions),
   independent order (l_base) vs L1 order (l_cand), per player-game, paired by slate.  Rows file proj/f6_dependence_opportunity_chain_rows.csv.gz: term "F5 receptions given
   F5 targets", stage "work order 31 L1 rank-coupled binomial order (reception multiset unchanged)", null_b exact.  Verdict: harness.py dependence, exact null B, work order 47
   provenance (every recorded row identical, exactly two added).  Printed consequence: "upper-tail attribution: structurally zero because targets are not an F8 counted
   component and no second F8 component changes".  Registered once, judged once.
## WORK ORDER 31 L1 - INSTRUMENT AMENDMENT BEFORE ANY RUN - Oct 4 2026 (read of f7.energy_score L14-19; nothing has run)
f7.energy_score estimates E||Z - Z'|| from consecutive draws (np.roll).  With a binomial auxiliary, ties broken by draw index assign ascending reception values to consecutive
   draws inside a tie group (a row whose target draws are all zero would carry its receptions in sorted order), biasing the second term down and l_cand up - a defect of the
   registered tie rule, not a choice of law (walls 9 / 10 order by continuous variables).  Amended: ties in A are broken in random order by an independent uniform from
   rng_chain (ordering key A + U, U ~ Uniform(0, 1)); reception multiset unchanged or refused; everything else as registered.  Outputs: the rows file and
   proj/f6_dependence_opportunity_chain_report.txt.  Acceptance: every existing compose output (17 files) identical (decompressed) or restore whole; harness dependence
   work order 47a guard - the 27 recorded verdict rows an identical prefix, exactly two added.
## WORK ORDER 31 L1 - OUTCOME - Oct 4 2026 (proj/f6_dependence_opportunity_chain_report.txt, proj/harness_dependence_report.txt)
spine_compose.py sha256 3c8cf606... (L1 block, call, outputs; syntax checked); 17 of 17 existing compose outputs identical (decompressed).  p_pos RB .7670 / .7697 / .7709 /
   .7779, WR .6537 / .6428 / .6375 / .6350 (2021 / 2023 / 2024 / 2025).  Energy score (targets, receptions) independent order vs L1 order: RB 1.2887 -> 1.2328, gain
   +0.05580+-0.00087 (4/4), tau/sigma 0.00, FP null A .0264, exact null B 0/16, power 1.00 -> HARNESS PASS;  WR 1.7397 -> 1.6865, gain +0.05337+-0.00147 (4/4), tau/sigma
   0.04, FP null A .0266, exact null B 0/16, power 1.00 -> HARNESS PASS.  Work order 47a: 27 recorded rows an identical prefix, exactly two added (RB / WR wall 9 FROZEN as
   recorded).  Upper-tail attribution: structurally zero (targets are not an F8 counted component).  L1 EARNED for RB and WR - enters the work order 31 cumulative chain
   (not the live composition; integration is its own registration).  First exact-null-B passes of a skill-position dependence at nS = 4: tau/sigma ~ 0 (no season
   variation), the condition under which no season sign pattern of the centred gain passes the gate.
## WORK ORDER 31 L2 - RECEPTIONS -> RECEIVING YARDS - REGISTRATION - Oct 4 2026 (cumulative on the earned L1 order; RB, WR; tests 2021, 2023, 2024, 2025)
Auxiliary B = Rn x e_pos + sqrt(max(Rn, 1) x v_pos) x Z per draw, Rn = the L1 reception order, Z standard normal from rng_chain; e_pos = sum realized receiving yards / sum
   realized receptions, v_pos = sum (y_ryd - y_rec x e_pos)^2 / sum max(y_rec, 1), both over earlier-season rows of the position (realized counts, one information set; no
   ratio of frozen means).  The composition's receiving-yards draws (RYD) are reordered per row to the ranks of B (continuous; stable argsort); multiset unchanged or
   refused.  rng, rng8, rng_copula, rng_clayton, rng_pattern untouched; every existing compose output identical (decompressed) and the L1 rows reproduced exactly.
Native score: energy score of the (receptions, receiving yards) draws against realized, L1 order with the independent receiving-yards order (l_base) vs L1 + L2 order
   (l_cand), stat units (L2409), per player-game, paired by slate; rows appended to proj/f6_dependence_opportunity_chain_rows.csv.gz with stage "work order 31 L2
   rank-coupled per-reception yards order (receiving-yards multiset unchanged)", term "F5 receiving yards given F5 receptions", null_b exact.  Verdict: harness.py
   dependence, exact null B; work order 47a: 29 recorded rows an identical prefix, exactly two added.
Attribution (consequence only; printed whatever the verdict; E2 is a reading only if L2 earns): spine_compose.py writes per row, for the chain draws C2 = [Rn, RYn, UYD,
   TDd]: the chain F8 draws' own quantiles at .10 / .25 / .75 / .90 and the tail-draw pattern counts (pattern() definitions; f7.pit_self randomization from rng_chain) ->
   proj/f8_tail_pattern_chain_rows.csv.gz.  f8_tail_attribution.py gains a WORK ORDER 31 ATTRIBUTION section: observed tail rows y_dk beyond the row's chain quantile;
   components beyond their own tail by the live composed PITs (marginals unchanged); Delta(2) per slate, mean +- slate SE, per season; E2 = 1 - |Delta(2)| / |Delta(0)|;
   q .90 the reading, q .10 / .25 / .75 context.  Witness: the same section run on the live pattern rows and live quantiles reproduces the recorded Delta(0) (RB +.2223,
   WR +.1964 and every recorded season value) exactly, or nothing is written.  Existing attribution outputs (rows, report prefix, joint downside rows) byte-identical.
   Registered once, judged once.
## WORK ORDER 31 L2 - INSTRUMENT AMENDMENT BEFORE ANY RUN - Oct 4 2026 (read of the L1 code path; nothing has run)
The registration draws L2's Z and pit_self randomization from rng_chain; rng_chain is consumed in loop order, so L2 draws would shift every later L1 draw and break the
   registered "L1 rows reproduced exactly".  Amended: L2 uses its own stream default_rng(20261012) (rng_chain2) for Z and the pit_self randomization; wo31_l1 returns its
   reception order (no value change).  Attribution outputs go to their own files - proj/f8_tail_chain_attribution_rows.csv, proj/f8_tail_chain_attribution_report.txt - so
   every existing f8_tail_attribution.py output (attribution rows, report, joint downside rows) stays byte-identical in full.  Acceptance: 17 compose outputs identical
   (decompressed); the L1 rows and L1 report an exact prefix of the rewritten rows file and report; the attribution witness reproduces the recorded joint-downside Delta
   (slate mean, slate SE, every season value) exactly or nothing is written; harness dependence work order 47a - 29 recorded rows an identical prefix, exactly two added.
## WORK ORDER 31 L2 - OUTCOME - Oct 4 2026 (proj/f6_dependence_opportunity_chain_report.txt, proj/f8_tail_chain_attribution_report.txt, proj/harness_dependence_report.txt)
spine_compose.py 5dfe3dfc..., f8_tail_attribution.py 8c9699b4...; 17 of 17 compose outputs identical; L1 rows and report exact prefixes; 3 existing attribution outputs identical;
   witness reproduced the recorded Delta(0) at every level and season; work order 47a: 29 recorded rows an identical prefix, exactly two added.  e_pos / v_pos per fold RB
   7.187 / 38.1 ... 7.429 / 50.4, WR 12.529 / 119.4 ... 12.585 / 120.9.
Native (energy score receptions, receiving yards): RB +0.01294+-0.00282 (4/4), tau/sigma 0.13, exact null B 0/16 -> HARNESS PASS;  WR +0.01667+-0.00350 (4/4), tau/sigma 0.37,
   exact null B 1/16 = .0625 > .05 -> HARNESS FAIL (first NO is the ceiling; not re-judged).
Attribution q .90 (reading level): RB Delta +.2223 -> +.1913 +- .0297, E2 +0.140 - a reading (L2 earned); RB remains in the chain with L1 + L2.  WR Delta +.1964 -> -.0070
   +- .0180 (seasons +.013 / -.052 / -.006 / +.004), E2 +0.965 - NOT a reading (L2 failed); failure class (3), signal with insufficient resolution: not promoted, recorded as
   unresolved mechanism evidence (same shape as WR scale: tau/sigma > 0, 4/4 positive, exact null B 1/16).  WR L2 does not enter the chain; the WR chain stays at L1.
   Context: RB q .10 / .25 / .75 E2 +.300 / +.476 / +.147; WR q .10 +.543, q .75 +.875, q .25 -1.775 (Delta -.0256 -> -.0709: overshoot at the lower-middle level).
## WORK ORDER 31 L3 - VOLUME -> TDs - REGISTRATION - Oct 4 2026 (cumulative on each position's earned chain: RB L1 + L2, WR L1; tests 2021, 2023, 2024, 2025)
Volume (wall 8 definition, L1901-1905): WR = the L1 reception order R31; RB = the composition's F5 carries draws + R31.  Auxiliary A3 = Poisson(V_draw x tau_pos) + U per draw,
   tau_pos = sum realized F5 TDs / sum realized volume (WR receptions; RB carries + receptions) over earlier-season rows of the position; U ~ Uniform(0, 1) (random tie order).
   The composition's final F5 TDs draws (after the work order 19 hurdle and work order 20 (a) integrations) reordered per row to the ranks of A3; multiset unchanged or
   refused.  Own stream default_rng(20261013) (rng_chain3) for the Poisson, U and the pit_self randomization; every other stream untouched; 17 compose outputs identical,
   L1 + L2 rows and report exact prefixes, the L2 chain pattern rows and chain attribution outputs identical.
Native score: energy score of the (volume, TDs) draws against realized (volume, TDs), earned-chain order with the independent TD order (l_base) vs with the L3 TD order (l_cand),
   stat units, per player-game, paired by slate; rows appended to proj/f6_dependence_opportunity_chain_rows.csv.gz, term "F5 TDs given volume", stage "work order 31 L3
   rank-coupled Poisson TD order (TD multiset unchanged)", null_b exact; harness.py dependence, exact null B; work order 47a: 31 recorded rows an identical prefix, exactly two added.
Attribution (consequence only; a reading only where L3 earns): chain draws C3 = [R31, RY_chain, F5 rushing yards, TDn] with RY_chain = the L2 order (RB) or the independent
   order (WR); own F8 quantiles and tail-draw pattern counts -> proj/f8_tail_pattern_chain3_rows.csv.gz; f8_tail_attribution.py WORK ORDER 31 L3 ATTRIBUTION section: Delta(3)
   per slate / season; RB E3|2 = (|Delta(2)| - |Delta(3)|) / |Delta(0)|; WR E3|1 = (|Delta(0)| - |Delta(3)|) / |Delta(0)| (the WR chain base is L1, whose attribution is 0).
   Witness: the section's RB Delta(2) from the L2 chain rows equals the recorded L2 attribution exactly, or nothing is written; own files
   proj/f8_tail_chain3_attribution_rows.csv, proj/f8_tail_chain3_attribution_report.txt.  Registered once, judged once.
## WORK ORDER 31 L3 - OUTCOME - Oct 4 2026 (proj/f6_dependence_opportunity_chain_report.txt, proj/f8_tail_chain3_attribution_report.txt, proj/harness_dependence_report.txt)
spine_compose.py ae1192f7..., f8_tail_attribution.py 4325f6f6...; 17 compose outputs + L2 chain pattern rows identical; L1 + L2 rows and report exact prefixes; 5 existing
   attribution outputs identical; witness reproduced the recorded Delta(2); work order 47a: 31 recorded rows an identical prefix, exactly two added.  tau_pos RB .0348 / .0347 /
   .0331 / .0334, WR .0811 / .0786 / .0787 / .0800.  One volume array per row in both energy scores (RB carries draws + L1 reception order).
Native (energy score volume, TDs): RB +0.00147+-0.00015 (4/4), tau/sigma 0.00, exact null B 0/16, power .75 / 1.00 / 1.00 -> HARNESS PASS;  WR +0.00153+-0.00023 (4/4),
   tau/sigma 0.14, exact null B 0/16, power .38 / .94 / 1.00 -> HARNESS PASS.  L3 EARNED for RB and WR - enters each chain (RB L1 + L2 + L3; WR L1 + L3).
Attribution q .90 (readings): RB Delta +.1913 -> +.1622 +- .0283, E3|2 +0.131 (cumulative 1 - .1622 / .2223 = .270 of the RB defect removed);  WR Delta +.1964 -> +.1401 +- .0174,
   E3|1 +0.287.  Context: RB q .10 / .25 / .75 +.097 / +.183 / +.142; WR q .25 +.292, q .75 +.378, q .10 -.392 (Delta +.0275 -> +.0383: L3 widens the WR lower-tail joint excess).
STOP RULE: RB - one direct mechanism remains (carries -> rushing yards; rushing yards drawn independently of carries, spine_compose.py L148): rung L3R below.  WR - every explicit
   link to a counted component is judged (T -> R earned, V -> TD earned, R -> RY failed class (3); WR draws no carries).  The WR residue +.1401 meets the stop rule's
   shared-state candidate definition but is CONTESTED: the class (3) R -> RY evidence (L2 OUTCOME: Delta -> -.0070 had it been consumable) ties it to an explicit link.  It is
   not assigned to Root 3 until work order 48 (5) rules on class (3) evidence.
## WORK ORDER 31 L3R - CARRIES -> RUSHING YARDS (RB) - REGISTRATION - Oct 4 2026 (explicit rung of the ladder's "carries -> rushing yards" route; cumulative on RB L1 + L2 + L3)
Auxiliary B = C_draw x e_c + sqrt(max(C_draw, 1) x v_c) x Z per draw, C_draw = the composition's RB F5 carries draws (the same array L3's volume used), Z standard normal from
   rng_chain4 = default_rng(20261014); e_c = sum realized rushing yards / sum realized carries, v_c = sum (y_uyd - y_car x e_c)^2 / sum max(y_car, 1), both over earlier-season RB
   rows (realized counts; no ratio of frozen means - the coherence ruling L1957-1963 not engaged).  The composition's RB F5 rushing yards draws reordered per row to the ranks
   of B (continuous; stable argsort); multiset unchanged or refused.  Every other stream untouched; 17 compose outputs, the L2 and L3 chain pattern rows identical; L1 + L2 + L3
   rows and report exact prefixes; every existing attribution output identical.
Native score: energy score of the (carries, rushing yards) draws against realized, one carries array on both sides: chain order with independent rushing yards (l_base) vs
   with the L3R order (l_cand), stat units, per player-game, paired by slate; rows appended, term "F5 rushing yards given F5 carries", stage "work order 31 L3R rank-coupled
   per-carry rushing yards order (rushing-yards multiset unchanged)", null_b exact; harness.py dependence, exact null B; work order 47a: 33 recorded rows an identical prefix,
   exactly one added (RB).  Verdict policy L2653: no recorded wall judged this pair (wall 7 RB rushing did not apply, incoherent).
Attribution (consequence only; a reading only if L3R earns): chain draws C4 = [L1 reception order, L2 receiving-yards order, L3R rushing-yards order, L3 TD order];
   own F8 quantiles and tail-draw pattern counts -> proj/f8_tail_pattern_chain4_rows.csv.gz; f8_tail_attribution.py WORK ORDER 31 L3R ATTRIBUTION section: Delta(3R) per
   slate / season; E3R|3 = (|Delta(3)| - |Delta(3R)|) / |Delta(0)|; witness: RB Delta(3) from the chain-3 rows equals the recorded L3 attribution exactly, or nothing is
   written; own files proj/f8_tail_chain4_attribution_rows.csv, proj/f8_tail_chain4_attribution_report.txt.  After L3R the RB residue is the Root 3 (shared-state) candidate.
   Registered once, judged once.
## WORK ORDER 31 L3R - OUTCOME - Oct 4 2026 (proj/f6_dependence_opportunity_chain_report.txt, proj/f8_tail_chain4_attribution_report.txt, proj/harness_dependence_report.txt)
spine_compose.py d0e1ba12..., f8_tail_attribution.py 993cea4f...; 19 of 19 required outputs identical; L1-L3 rows and report exact prefixes; 7 existing attribution outputs
   identical; witness reproduced the recorded Delta(3); work order 47a: 33 recorded rows an identical prefix, exactly one added.  e_c / v_c RB 4.356 / 40.5, 4.327 / 37.3,
   4.263 / 36.1, 4.297 / 36.8.  One carries array in the L3 volume and both L3R energy scores.
Native (energy score carries, rushing yards): RB +0.05130+-0.00417 (4/4), tau/sigma 0.30, power .81 / 1.00 / 1.00, exact null B 1/16 = .0625 > .05 -> HARNESS FAIL (first NO is the
   ceiling).  Failure class (3), signal with insufficient resolution: not promoted; L3R does not enter the chain.
Attribution (not a reading): q .90 Delta(3) +.1622 -> +.1589, E3R|3 +0.015 (about 1.5 points of the original +.2223 even if consumable); q .75 +.185; q .10 -.075, q .25 -.200.
END OF THE WITHIN-PLAYER EXPLICIT CHAIN (stop rule): RB - every explicit link to a counted component judged (T -> R, R -> RY, V -> TD earned; C -> UY failed class (3), consequence
   +.015): the RB q .90 residue +.1622 (cumulative .270 of +.2223 removed by earned rungs) is the shared-state (Root 3) CANDIDATE, not materially contested; not earned as shared
   state until a shared-state wall earns it.  WR - residue +.1401 (cumulative .287 removed), CONTESTED by the class (3) R -> RY (L2 OUTCOME), pending work order 48 (5).
   Closed families for an RB within-player shared state: wall 9 one-factor Gaussian and wall 10 lower-tail Clayton (recorded verdicts; verdict policy L2653 allows a new wall
   on the current chain, failure class (2) requires a different family earned by a lower diagnosis).  Class (3) evidence now: WR L2 R -> RY, RB L3R C -> UY, WR scale
   log-linear, WR scale spline, TE location - every one tau/sigma > 0, 4/4 positive, exact null B the only failure; input to work order 48 (5), never a re-judgment.
## ROOT 3 - CROSS-PLAYER DEPENDENCE - OWNER DECISION (c) AND STOP RULES - Oct 4 2026 (owner / reviewer, after the work order 31 chain)
Decision (c): the next target is Root 3, cross-player and game-state dependence on the earned player laws.  Not now: (a) an RB within-player shared-state family, (b) carries <->
   targets coupling (reopened only if Root 3 finds a player-level role factor that owns both); (d) work order 48 (5) does not block - historical verdicts stay frozen, a
   forward rule is set once, as a governance task, never a research branch.
STOP RULES: Root 1 stops when remaining marginal errors fail their mechanism walls or do not materially alter lineup objectives (class (3) items parked; reopened only if one
   proves material to lineup ordering).  Root 2 stops when every direct football link into a DK component is judged - reached for RB and WR (work order 31 L3R OUTCOME).
   Root 3 stops when an earned dependence removes the material lineup-tail discrepancy, or the remaining dependence changes no FLOOR / CEILING ordering materially - the
   residual dependence need not reach zero.  Root 4 stops when one candidate pool yields stable objective-specific selections: BASE = argmax E[DK], FLOOR = argmax Q10 (or
   CVaR), CEILING = argmax Q90.  Only residuals that can change the lineup decision are explained.
WORK PACKAGES (in order): WP1 integrate the earned chain (RB L1 + L2 + L3, WR L1 + L3) into the live composition - orderings only, marginals unchanged, its own registration and
   witnesses; WP2 Root 3 cross-player / game-state wall on the integrated marginals, marginal-preserving (rank-reorder of each player's draws), first pair classes QB <-> WR / TE,
   QB team A <-> QB team B, RB <-> same-game passing environment, other opponent / teammate relations only where they appear in candidate lineups; WP3 lineup relevance;
   WP4 27b -> 27c -> 29 (future-week distributions, player cards, BASE / FLOOR / CEILING lineups).
TWO GATES FOR ROOT 3: scientific - the joint score improves on held-out historical games (harness, exact null B, as every dependence wall); decision - the dependence changes
   lineup-tail ordering: a resolved reversal (L513-527 definition: sign of D_ij = Q_q(L_i) - Q_q(L_j) differs between worlds AND |D_ij| > 2 batch-means s.e. in both, beyond the
   noise-twin count) at q .10 or q .90 among candidate lineups.  Scientifically real but no resolved reversal -> CLOSED OPERATIONALLY.
FACTS FOR WP2 / WP3 (read, earlier this cycle): shared-game co-movement on the Y scale is earned (Class D, L278-286); s.run selects by best9 on exp with no dependence term (L489-491,
   L532-533), so under the current selector any dependence has structurally zero effect on lineup identity - WP3's decision gate therefore needs a candidate set generated for the
   tail objectives (selector ladder L538: A0 best9(exp) -> A1 reranker over pair-blind candidates; W0 outcome-free), never the best9-only set.
## WP1 - EARNED CHAIN INTEGRATION - REGISTRATION - Oct 4 2026 (ROOT 3 decision (c) work package 1; precedent F6 DEPENDENCE WALL 9 - INTEGRATION)
The live composed F8 for RB / WR (wall 9 not earned, work order 31 L1 earned) uses the earned chain order [L1 reception order, L2 receiving-yards order if L2 earned else the
   independent order, rushing yards independent (L3R failed), L3 TD order if L3 earned else the independent order]; earned rungs read from proj/harness_dependence_verdicts.csv,
   never listed by hand.  Orderings only: every component's draw multiset per row is the composition's (asserted in each rung); F8 mean invariant (skill_dk additive per
   component) - max |f8_mean difference| < 1e-9.  The chain rung calls move before the F8 line (own streams; values unchanged).  q27 writes form "chain" with the independent
   composition's quantiles in the *_independent columns (wall 9 TE precedent); f8_tail_attribution.py reads those for chain rows, so every recorded diagnosis of the independent
   composition (attribution matrix, joint downside, work order 31 sections and witnesses) reproduces.
ACCEPTANCE: identical (decompressed) - spine_compose_rows, pairs, params, report, wall 9 / wall 10 / TE quantile files, hurdle integration, f8_tail_pattern_model_rows, the
   chain rows / report / three chain pattern files; f8_rows TE / QB rows identical, RB / WR rows f8_mean within 1e-9; f8_quantile_rows TE / QB rows identical, RB / WR rows
   *_independent = the previous live quantiles exactly; f8_tail_attribution.py outputs identical in every number (rows with the status column dropped; reports with bracketed
   labels stripped).  Changed by design: f8_rows RB / WR quantiles, CRPS, PIT; f8_quantile_rows RB / WR; 27a status / report.  No harness run; no verdict changes.
   Consequence printed: 27a coverage RB / WR at .10 / .25 / .75 / .90 before vs after.  Recorded diagnostics that read the pre-integration F8 (owner maps, f8_state_*, f8_vs_y)
   stay as provenance of the independent composition; not rerun.  Registered once, judged once.
## WP1 - EARNED CHAIN INTEGRATION - INSTRUMENT CORRECTION - Oct 4 2026 (first attempt: acceptance FAILED on one check; restored whole)
First attempt (spine_compose.py 129deb91..., f8_tail_attribution.py e27f4517...): 17 of 18 identical outputs; f8_rows TE / QB identical, RB / WR max |f8_mean diff| 1.07e-14;
   f8_quantile_rows TE / QB identical, RB / WR *_independent = previous live quantiles.  FAILED: f8_tail_pattern_model_rows differs.  Cause (patch defect, not a law outcome):
   the live line pattern(pos, te, [Rc, RYD, UYD, TDd], Dl) takes Dl as the F8 draws that define the tail; after integration Dl is the chain F8, so the joint-downside model side
   (the recorded Delta(0) baseline) was recomputed on the wrong draws - contrary to the registration ("every recorded diagnosis of the independent composition reproduces").
   Correction: pattern receives skill_dk(Rc, RYD, UYD, TDd) where the chain order is live (rng_pattern's draw count depends on shape only; the independent F8 equals the
   previous Dl exactly).  Same acceptance, re-run once.  Printed by the failed attempt, not accepted (f8_rows / 27a do not depend on pattern): RB mean P90 14.640 -> 15.088,
   P10 2.300 -> 1.890; WR P90 13.068 -> 13.474, P10 1.513 -> 1.316; 27a RB q .10 .1138 too high -> .0924 within band, q .90 .862 -> .873 too low; WR q .10 .1156 -> .1037
   within band, q .25 .2700 -> .2536 within band, q .75 too high, q .90 .8575 -> .866 too low.
## PROP WORKFLOW - STAT-LEVEL CARD AS THE CANONICAL OUTPUT - REGISTRATION OF DIRECTION - Oct 4 2026 (reviewer note; owner attachment)
Objective: for every prop-relevant player statistic, a pregame distribution whose center comes from earned structure, whose width is the unresolved residue, whose held-out
   calibration record is explicit, and whose links to other statistics exist only where earned.  DK points and lineups become consumers of the same native-stat draws (one
   forecasting engine).  Steps (named PROP WORKFLOW STEP 1-10 - the recorded "WP1"-"WP4" names stay): STEP 1 earned center with provenance (no volatility work moves a center
   unless a center wall earns it); STEP 2 residual marginal law (support, scale, skew, tails, earned state width); STEP 3 earned within-player links (orderings only); STEP 4
   week-mode per-stat draw distributions with the frozen laws (27b) - E[Y], P10 / P25 / P50 / P75 / P90; STEP 5 per-stat calibration grade from held-out behaviour by state
   (CALIBRATED / CENTER BIAS / TOO WIDE / TOO NARROW / TAIL UNCERTAIN / SHORT HISTORY / UNRESOLVED); STEP 6 structure vs residue shown per stat; STEP 7 stat card (27c at the
   native-stat level); STEP 8 market-last comparison - a posted line is evaluated against the frozen distribution, P(over) / P(under), never a forecast input (guard check 10
   unchanged); STEP 9 cross-player dependence only for multi-player products (Root 3); STEP 10 DK transform and BASE / FLOOR / CEILING.
Map to recorded names: STEP 3 delivery into the live composition = WP1 (EARNED CHAIN INTEGRATION); STEP 9 = Root 3 WP2; STEP 10 = Root 3 WP3 + the lineup part of WP4; STEPS
   4-7 = WP4's 27b / 27c expanded to the native-stat level.  Stop rule for a stat card: center from an earned law, distribution from the current frozen law, calibration status
   known, unresolved defects disclosed, nothing shown as calibrated that is not.  Order relative to Root 3 WP2: owner decision pending.
## WP1 - EARNED CHAIN INTEGRATION - OUTCOME - Oct 4 2026 (corrected run; proj/wp1_integration_report.txt, proj/f8_tail_calibration_report.txt)
spine_compose.py 68e0a418eddfd561..., f8_tail_attribution.py e27f4517989f0f1b... (the INSTRUMENT CORRECTION patch).  ACCEPTED: 18 of 18 must-be-identical outputs identical (f8_tail_pattern_model_rows
   included - the correction holds); f8_rows TE / QB rows identical, RB / WR max |f8_mean diff| 1.07e-14; f8_quantile_rows TE / QB identical, RB / WR *_independent = the previous
   live quantiles exactly; every recorded attribution number reproduced (status labels changed on 18 of 72 rows, by design).  Live RB / WR F8 now on the earned chain order:
   RB [L1 receptions, L2 receiving yards, independent rushing yards, L3 TDs], WR [L1 receptions, independent receiving yards, independent rushing yards, L3 TDs], every season.
Consequence (27a, coverage before -> after): RB q .10 .1138 too high -> .0924 within band; q .25 .2590 -> .2398 within band; q .75 .7580 -> .7640 within band; q .90 .8620 -> .8729
   too low (gap -.0380 -> -.0271).  WR q .10 .1156 too high -> .1037 within band; q .25 .2700 too high -> .2536 within band; q .75 .7655 -> .7666 too high; q .90 .8575 -> .8660 too
   low (gap -.0425 -> -.0340).  Mean P90 RB 14.640 -> 15.088, WR 13.068 -> 13.474; mean P10 RB 2.300 -> 1.890, WR 1.513 -> 1.316.  Reading: the earned chain repairs the lower
   and lower-middle tails for both positions; the q .90 ceiling stays too low for both (gap narrowed ~29% RB, ~20% WR) - consistent with the work order 31 residues (RB +.1622
   shared-state candidate; WR +.1401 contested).  Prop workflow STEP 3 delivered into the live composition.
## ROOT-CASCADE EXECUTION DOCTRINE - REGISTRATION OF DIRECTION - Oct 4 2026 (reviewer note; owner attachment; settles the order left open after WP1)
Principle: deepest shared root -> repair once -> propagate through every consumer -> measure the new residue.  Before every wall: which unresolved root contaminates the most outputs?
CASCADE PRIORITY (named so; the existing Root 1 marginal / Root 2 within-player / Root 3 shared state names stay; the attachment's "Root 0" and "Root 4-9" are recorded as cascade
   layers, not roots): 1 - one canonical native-stat distribution producer callable at any pregame cutoff, the same producer for historical replay and week mode (prop workflow STEP
   4 / 27b, a root infrastructure wall; acceptance: at a historical cutoff it reproduces the frozen historical law - only inputs change with the cutoff); 2 - the complete per-stat /
   per-state calibration map from that producer (no repairs first); 3 - Root 3 shared-state diagnosis of the remaining joint-tail error after the earned chain (before further small
   marginal refinements unless the map shows a larger native defect); 4 - prop cards (single-player props do not wait for Root 3); 5 - cross-player decision wall (joint relevance AND
   decision relevance, else operationally closed); 6 - BASE / FLOOR / CEILING on the same issued draws (no parallel engine).  Calibration grades, the structure / residue display and
   cards are consumers of the producer's laws and provenance: they own no statistical logic; a defect seen in one is traced to the earliest owner, never patched in place.  Root 2 is
   parked (reopened only when a downstream residual attributes to a missing within-player link).  Market data stays a post-freeze query, never an input.
WORK-ORDER FILTER (before any new work order): 1 the earliest mechanism that owns the defect; 2 how many downstream consumers it affects; 3 the outputs that improve if it is fixed,
   named before registration; 4 the stop condition - earned / failed-closed / unresolved but disclosed / operationally irrelevant; no branch stays open because another family exists.
This supersedes the open order question (prop STEPS 4-7 first vs Root 3 WP2 first): cascade priority 1 is next.  Program end: every decision-relevant residual has an earned owner or an
   explicit unresolved / noise label.
## CASCADE PRIORITY 1 - NATIVE LAW PRODUCER - REGISTRATION - Oct 4 2026 (read: spine_compose.py 68e0a418... season loop L328-396, wall parameter files, spine_sufficient, spine.py issue)
Facts: every native law is fitted inside the composition's season loop from training rows (season < s) and drawn on one shared stream; per-row parameters are recorded only for the
   zero-history terms (spine_compose_params: F5 receptions, F5 TDs, Q4, QB rushing TDs); zero-history (m, r), hurdle (pi, m_pos, r_pos) and work order 20 (a) (mu_c) parameters exist
   for 2021 / 2023 / 2024 / 2025 only, produced by f6_zero_history_replacement.py, f6_zero_history_hurdle*.py, f6_td_volume.py; spine_sufficient covers 2020-2025 (history mode);
   the week file carries means only (no state, no sufficient statistics).  A week's draws cannot reproduce a season run draw for draw (shared stream): the law is reproduced at the
   parameter level, draws for a single row come from keyed per-row substreams (work orders 19 / 20 (a) precedent).
Work-order filter: owner - no per-row native law outside a full-season composition run; consumers - calibration map, prop cards, over / under queries, DK distributions, Root 3
   simulation, optimizer; improvement - all become computable at any cutoff from one producer; stop - exact replay of the recorded laws, or refused.
STAGES: A1 the composition records its full law table at the sites where it computes each law - per row and stat: family and parameters (team targets NB(m, r_T); WR targets share
   of the team draw p, phi; TE targets support a, b, s, g; RB targets Poisson / hurdle; receptions NB(m, r) or Poisson / zero-history (m, r) / hurdle (pi, m_pos, r_pos); RB carries
   Poisson / hurdle; receiving and rushing yards Normal(m, sd) with form and spread; TDs Poisson or NB(m, r) / zero-history / hurdle / work order 20 (a) Poisson(mu_c); Q1 Poisson;
   Q2 Binomial(A, p); Q3 yards_given(e, v); Q4 Poisson / zero-history; Q5 support a, b, s, g; QB carries NB(m, r); QB rushing yards yards_given(e, v) by state; QB rushing TDs Poisson /
   zero-history) and the season-level fits including the earned chain rates (p_pos, e_pos, tau_pos); no draw call added, removed or reordered; every existing output byte-identical
   (decompressed); new outputs proj/native_law_rows.csv.gz, proj/native_law_season.csv.  A2 native_laws.py refits every law from scratch at a season cutoff - including the
   zero-history, hurdle and work order 20 (a) fitting procedures and the chain rates - and reproduces the A1 tables and the three wall parameter files exactly (fit_contract replay
   precedent; the wall scripts read whole before the build).  A3 the composition calls native_laws instead of fitting inline; every output byte-identical.  B week mode: the issue
   frame gains states and sufficient statistics; live laws from native_laws at a cutoff on seasons <= FROZEN_THRU; keyed per-row draws; per stat E, P10 / P25 / P50 / P75 / P90;
   acceptance - the issue-path cutoff (2025 week 10, fit on seasons < 2025) reproduces the A2 law rows for that week exactly.  Verdicts (earned / not earned) stay frozen from history;
   only parameters are refit, by the walk-forward rule.  Each stage registered acceptance is judged once; a stage that does not reproduce is refused and reported.
## CASCADE PRIORITY 1 - A1 SPECIFICATION AND REFINEMENTS - Oct 4 2026 (reviewer note on the registration; before any code)
Refinements (part of the acceptance): A1 is instrumentation only - it learns nothing; every pre-existing output unchanged.  One canonical law schema: season, week, key, term,
   position, layer, family, state, provenance, mu, r, n_parent, p, phi, sd, form, spread, e, v, parent, pi, m_pos, r_pos, a, b, s_suff, g (parameters nullable by family); provenance
   names the source (F6 v1 marginal / earned wall / zero-history law / work order 19 hurdle / work order 20 (a) mean / support law / unresolved).  A2 reproduces the fitting
   procedures from historical inputs; wall artifacts are acceptance witnesses only, never production inputs.  A3 retires every inline fit (no second implementation).  B asserts
   information time - a week-w row's state uses outcomes through week w - 1 only - and is compared with A2 at the law-parameter level.  Stop: when A1, A2, A3 and B hold,
   infrastructure work stops and cascade priority 2 (the calibration atlas over the production laws) runs.
A1: helpers nlaw / nfit append witness rows from values the composition has already computed (no generator call; QB carries r recomputed by the deterministic nb_fit).  Layers:
   0 base law at the call site; 1 recorded inside zero_history where it replaces s = 0 rows; 2 inside zh_hurdle; 3 inside td20; final = the highest layer per (row, term).  Sites:
   F2 team targets; F5 targets (WR share of the team draw, TE support, RB Poisson); F5 receptions; RB F5 carries; F5 receiving / rushing yards (form, spread); F5 TDs; Q1; Q2; Q3;
   Q4; Q5; QB carries; QB rushing yards; QB rushing TDs; season table adds the earned chain rates (L1 p_pos, L2 e_pos / v_pos, L3 tau_pos for the earned positions).  Outputs
   proj/native_law_rows.csv.gz, proj/native_law_season.csv.  Coverage witness: every (season, week, key, stat, position) the composition scores has exactly one final law row,
   else exit 1.  Acceptance: every composition output (23 files) identical (decompressed).  Judged once.
## CASCADE PRIORITY 1 - A1 - OUTCOME - Oct 4 2026 (proj/native_law_rows.csv.gz, proj/native_law_season.csv)
spine_compose.py 15091830... (helpers + 20 recording lines + A1 output block).  ACCEPTED: every existing composition output identical (decompressed) 23 of 23; law rows 109,562 (final
   93,665); coverage - 92,129 of 92,129 scored (row, term) pairs carry exactly one final law; season fits 108 (including the earned chain rates).  Final laws in use (term, position,
   family / provenance, rows): RB TDs work order 20 (a) Poisson 2,659 / hurdle 1,353; WR TDs work order 20 (a) Poisson 4,090 / zero-history negative binomial 2,864; TE TDs F6 v1
   negative binomial 1,985 / zero-history Poisson 535 + negative binomial 1,715; receptions RB Poisson 3,595 + hurdle 417, WR negative binomial 6,505 + hurdle 449, TE Poisson 3,744 +
   zero-history negative binomial 491; targets RB Poisson 3,662 + hurdle 350, TE support 4,235, WR beta-binomial share of the team draw 6,954; RB carries Poisson 3,772 + hurdle 240;
   yards Normal (form 2 / 3 per position); Q1 Poisson; Q2 binomial of the attempts draw; Q3 and QB rushing yards yards-given-count; Q4 Poisson 1,450 + zero-history 64; Q5 support;
   QB carries negative binomial; QB rushing TDs Poisson 844 + zero-history 670; F2 team targets negative binomial 1,536 team-weeks.
A2 ACCEPTANCE REFINEMENTS (reviewer): the A1 files are the oracle; native_laws.py returns fit_state (cutoff-level fits) and row_laws(fit_state, rows) (the applicable law per row and
   stat); exact reproduction, at full precision wherever the computation is deterministic, of the final family, provenance, every numeric parameter, the season fits, chain rates,
   states, hurdle / support / zero-history parameters and work order 20 (a) means; the override precedence (base < zero-history < hurdle < work order 20 (a)) is part of the law and
   is reproduced per row.  Scope: A2 does not simulate, change generators, families or states, improve calibration, alter verdicts or clean code; wall artifacts are witnesses only.
## CASCADE PRIORITY 1 - A2 - BUILD - Oct 4 2026 (read whole: f6_zero_history_replacement.py c618271d..., f6_zero_history_hurdle.py 202b7dd4... (+ rungs 2 / 3, both FAIL), f6_td_volume.py ee853282..., hurdle.py, support.py)
native_laws.py: build_inputs (spine_rows, apply_freeze, spine_sufficient, p.load team map, the composition's row frames rebuilt with the same merges, support frames, verdict sets from
   the verdict files - zero-history PASS minus the blocked QB carries, hurdle PASS, work order 20 (a) PASS with the rows-hash provenance check, earned chain rungs); fit_state (team r,
   WR share phi, receptions / TD r, yards spreads, support (a, b), QB variances and carries r, zero-history (m, r) by the replacement wall's procedure, hurdle (pi, m_pos, r_pos) by rung 1's
   procedure with hurdle.ztnb_fit, work order 20 (a) rate by spine.pooled_rate, chain rates); row_laws (layers 0-3 and the final flag, the A1 schema and strings).  Single producers
   imported (hurdle.ztnb_fit, support, spine.pooled_rate, provenance.slice_sha, freeze.apply_freeze, p.load); nb_fit, bb_fit, spread exist inline in spine_compose.py (no __main__ guard,
   not importable) and in native_laws.py until A3 retires the inline copies.
ACCEPTANCE (judged once): python3 native_laws.py replay; exact equality on round-trip CSV values with the A1 law rows (every column, every layer, final flag) and the A1 season fits; and,
   as witnesses only, the zero-history (m, r) per component / season, hurdle (pi, m_pos, r_pos) per component / season and work order 20 (a) mu_c per row in the wall files.  Any
   difference -> REFUSED, reported per column; no rescue.  Writes only proj/native_laws_report.txt.
## CASCADE PRIORITY 1 - A2 - OUTCOME - Oct 4 2026 (python3 native_laws.py replay)
A2 REPLAY REFUSED.  Law rows 109562 x 28: differing columns mu (8372 rows; first QB rushing TDs QB layer 1, A1 0.1183431952662721 vs A2 0.11834319526627218), pi (1747; A1
   0.1269349845201238 vs A2 0.12693498452012383), m_pos (581; A1 2.333333460897125 vs A2 2.3333334608971246), r_pos (301; A1 1.9952623149688795 vs A2 1.9952623149688797); all other
   columns and the final flag exact.  Season fits 108 vs 108 identical.  Witnesses exact: zero-history (m, r) 47 component-seasons, hurdle (pi, m_pos, r_pos) 24, work order 20 (a) mu_c 8734.
   Inputs and oracle files unchanged.  Failure-only restore removed native_laws.py and proj/native_laws_report.txt.  No rescue.
Cause unknown.  Unmeasured hypothesis: the composition takes these parameters from the wall files through pd.read_csv's default float parser (ZHR, HR, T20M), while A2 computes them.
   The A1 tables remain the composition's witness; A3 does not start on this registration.
## CASCADE PRIORITY 1 - LAW SCHEMA PLAIN NAMES - REGISTRATION - Oct 4 2026 (read: spine_compose.py 15091830... lines 42-51, 20 nlaw / 13 nfit call sites, 303-328, 590-599; hurdle.py; support.py)
Glossary bridge for proj/native_law_rows.csv.gz and proj/native_law_season.csv, "code -> plain [source]"; earlier CASCADE PRIORITY 1 entries keep the old words.
 mu -> mean [17 sites]   r -> negative_binomial_size (inf = Poisson) [79, 348, 365, 374, 413]   p -> p_per_trial (probability of each trial of the parent draw) [354, 398]
 phi -> beta_binomial_concentration (inf = binomial) [354]   sd -> standard_deviation   form -> standard_deviation_form   spread -> standard_deviation_parameter [370, 372]
 e -> mean_yards_per_count   v -> yards_variance_per_count [404, 419]   parent -> conditioned_on_draw [354, 398, 404, 419]
 pi -> p_nonzero (zh_hurdle draws a positive count when U1 < pi) [318, 321]; distinct from p_near_zero (the DK near-zero probability)
 m_pos -> positive_part_untruncated_mean   r_pos -> positive_part_negative_binomial_size (hurdle.ztnb_fit) [318]
 a -> support_prior_gamma_shape   b -> support_prior_gamma_rate   s_suff -> support_event_sum   g -> support_games (support.support_predictive) [358, 410]
 n_parent: no writer (empty on every row) - deleted.
 Season names: r, phi, spread, v as above; support a -> support_prior_gamma_shape; support b -> support_prior_gamma_rate; p_pos -> receptions_per_target;
   e_pos -> mean_yards_per_reception; v_pos -> yards_variance_per_reception; tau_pos -> tds_per_volume.  Work order 31 report text keeps its words (pre-existing output).
 Unchanged: wall files (f6_zero_history_hurdle_rows pi, m_pos, r_pos); canon.py (canon.plain() is never applied to the law tables; its pi -> p_near_zero is the DK meaning).
ACCEPTANCE (judged once): spine_compose.py exits 0 with the A1 coverage witness; the 23 composition outputs identical (decompressed); native_law_rows identical as text to the
   pre-rename table with n_parent (all empty) removed and columns renamed; native_law_season identical as text with names mapped.  Any difference -> restore; no rescue.
## CASCADE PRIORITY 1 - LAW SCHEMA PLAIN NAMES - OUTCOME - Oct 4 2026 (python3 spine_compose.py; acceptance as registered)
ACCEPTED.  spine_compose.py exit 0; A1 coverage: law rows 109562 (final 93665), scored (row, term) pairs covered 92129 of 92129, season fits 108.  Existing composition outputs
   identical (decompressed) 23 of 23.  native_law_rows 109562 x 27: n_parent empty on every row, deleted; identical as text to the pre-rename table under the mapping.
   native_law_season 108: identical with names mapped.  read uses n_parent across *.py: 0.  The A2 OUTCOME's column names map through the registration's bridge
   (mu -> mean, pi -> p_nonzero, m_pos -> positive_part_untruncated_mean, r_pos -> positive_part_negative_binomial_size).
   Files now: spine_compose.py 4582effa040ea9bb..., proj/native_law_rows.csv.gz 1390b5cafba1ee65..., proj/native_law_season.csv f7a68399f9a6bd31...
## CASCADE PRIORITY 1 - A2 - CAUSE MEASURED - Oct 4 2026 (read: spine_compose.py 4582effa... whole; wall headers; A1 law values vs wall files parsed default / round_trip)
The A2 refusal is wholly a parse difference.  spine_compose.py reads the wall files with pd.read_csv's default float parser (ZHR line 67, T20M line 290, HR line 304) and uses
   the parsed values as production law parameters (zero_history line 78, td20 line 302, zh_hurdle lines 316-321).  A1 equals the default parse on every joined row (0 unjoined):
   layer 1 mean <- ZHR.m 6339 rows, default != round_trip 5133; layer 1 negative_binomial_size <- ZHR.r 6339, 0; layer 2 p_nonzero <- HR.pi 2809, 1747;
   positive_part_untruncated_mean <- HR.m_pos 2809, 581; positive_part_negative_binomial_size <- HR.r_pos 2809, 301; layer 3 mean <- T20M.mu_c 6749, 3239.
   5133 + 3239 = 8372, 1747, 581, 301 = the refused counts exactly.  GRID: HR round_trip 7 of 7 distinct r_pos values on GRID; A1 oracle and default parse 6 of 7.
   The composition takes law parameters from wall artifacts (forbidden by the A1 refinement: witnesses only).  A2's computed values equal the wall's exact text.
   Not measured: whether the parse differences change any draw or cross a threshold (line 299 allclose, line 321 U1 < pi).
## READER DOOR - REGISTRATION - Oct 4 2026 (reads: read_csv( 159 calls in 61 files, float_precision none; proj tables 93, 296 float columns in 82 tables differ default vs round_trip, 515824 values)
Root: no reader door - every table read in the kit uses pd.read_csv's default float parser, which does not recover the written value; writers are exact (round_trip recovers the
   wall text, = A2's computed values).  Door: tables.py, one producer, read_table(path, **kw) = pd.read_csv(path, float_precision="round_trip", **kw).
This transaction: spine_compose.py's three wall reads move onto the door - ZHR (f6_zero_history_replacement_rows, line 67), T20M (f6_td_volume_means, line 290), HR
   (f6_zero_history_hurdle_rows, line 304).  ZHV, HV and the other 156 calls stay; they are work order lines, one consumer group per transaction.
ACCEPTANCE (judged once): spine_compose.py exit 0 (mechanical, invariance, wall 9 provenance, A1 coverage); native_law_rows differs from the pre-run table only in mean
   (layer 1 5133 + layer 3 3239 = 8372 rows), p_nonzero (1747), positive_part_untruncated_mean (581), positive_part_negative_binomial_size (301), each now equal to the wall
   value parsed round_trip on every joined row, every other cell identical as text; native_law_season identical; spine_compose_params differs only in mean_used, on exactly
   5133 rows; the harness-judged rows files (f6_dependence_tail_copula_rows, f6_dependence_tail_copula_quantile_rows, f6_dependence_lower_tail_copula_rows,
   f6_dependence_opportunity_chain_rows) identical (decompressed) - a changed judged row refuses (verdict provenance), no rescue.  Every other composition output reported
   per file (identical, or changed lines counted).
## READER DOOR - OUTCOME - Oct 4 2026 (python3 spine_compose.py; acceptance as registered)
ACCEPTED.  spine_compose.py exit 0; A1 coverage: law rows 109562 (final 93665), scored (row, term) pairs covered 92129 of 92129, season fits 108.  Harness-judged rows files
   identical 4 of 4 (verdict provenance holds); the 18 other composition outputs identical - the parse correction moved no draw.  spine_compose_params: only mean_used changed,
   5133 rows (registered 5133).  native_law_rows: mean 8372, p_nonzero 1747, positive_part_untruncated_mean 581, positive_part_negative_binomial_size 301 changed in-mask, 0
   outside; every changed value equals the wall value parsed round_trip (unjoined 0, unequal 0 in all five checks); native_law_season identical.  The four columns that refused
   A2 now hold the wall's exact text (= A2's computed values).  Door in use: spine_compose.py reads ZHR, T20M, HR through tables.read_table; 156 read_csv calls remain.
   Files now: tables.py 2082dff569830810..., spine_compose.py 50c660bdf71104a6..., proj/native_law_rows.csv.gz aed1d61b0333a7c2...
## READER DOOR - FACTS READS - REGISTRATION - Oct 4 2026 (reads: facts.py whole; raw tables 47, differing default vs round_trip: pbp 54-57 columns / season, stats 3-6, all others 0)
Group 1 (most upstream): facts.py's six pd.read_csv calls (lines 19 rd, 50 and 72 header-only, 78 play-by-play, 121 salaries, 211 research pools) move onto tables.read_table.
   Of the differing raw columns facts.py names only play-by-play epa (1970 values); stats differing columns (air_yards_share, passing_cpoe, passing_epa, receiving_epa, rushing_epa,
   wopr) are not used.  So the only written value that can change is team_game.epa_play (mean of epa, line 83); its consumers are retarget.py and, through it, compose.py,
   contexts.py, deep.py - no forecast consumer (p.load takes no epa_play).  Rebuild from the files on disk; nothing fetched.
ACCEPTANCE (judged once): facts.py exit 0; facts/game.csv.gz and facts/player_game.csv.gz identical (decompressed); facts/team_game.csv.gz identical as text in every column
   except epa_play (rows changed reported); facts_report.txt reported.  Any change outside epa_play -> restore; no rescue.  Research outputs computed from epa_play are a work
   order line, not this transaction.
## READER DOOR - FACTS READS - OUTCOME - Oct 4 2026 (python3 facts.py; acceptance as registered)
ACCEPTED.  facts.py exit 0 (independent check vs DraftKings' recorded points: DST 1562 games 98.4% exact, skill 18773 player-games 99.6% exact).  facts/game.csv.gz,
   facts/player_game.csv.gz, facts_report.txt identical (decompressed); facts/team_game.csv.gz changed only in epa_play, 50 of 3744 rows.  Group 1 closed: facts.py reads
   through tables.read_table (6 calls).  Consumers of epa_play (retarget.py; compose.py, contexts.py, deep.py through it) not rerun - work order line.
   Files now: facts.py 61a896d094661704..., facts/team_game.csv.gz d402611c2fc0a423...
## READER NOISE GOVERNANCE - FROZEN EVIDENCE / CANONICAL FUTURE - Oct 4 2026 (owner ruling (d); supersedes options (a) / (b) / (c) for reader group 2)
Classification: the group-2 difference is a representation change, not a demonstrated data change.  Witness (in-memory spine.history, nothing written): control (default
   parser) reproduces spine_rows 150877 rows and spine_sufficient exactly; through the door six slices change - F4 carry_share RB, F4 target_share RB / TE / WR (y 11380, base
   16916, v1 24527 in total with F5 carries RB 1993 and F5 targets WR 6016 v1 rows), max |change| 7.1e-15; keys, row eligibility, state_base, state_v1, spine_sufficient unchanged.
D1 historical judged artifacts frozen as computed: spine rows -> wall rows -> rows_sha256 -> verdicts -> consumed composition are not rerun, rehashed, rejudged, promoted or
   demoted for representation-only differences; their provenance means "produced from the recorded historical spine representation".
D2 the door (tables.read_table) is the canonical reader for new facts consumption; the default-parser representation is legacy historical only; no wall chooses a parser by result.
D3 the historical spine is not rebuilt in place.
D4 non-adjudicative equivalence witness across the boundary: same keys, row eligibility, states, discrete family choices, shrinkage / grid selections, threshold side; numeric
   difference within the registered representation bound (observed 7.1e-15).  Any discrete change is not reader noise -> owner ruling.  Shadow outputs never replace official
   artifacts.  The group-2 witness above measured keys, eligibility, states and spine_sufficient; grid selections (WGRID, KGRID, KB, RGRID) are inferred from the bound, not
   yet printed - measured when the witness is formalized for B.
D5 A1 / A2' / A3 replay the recorded spine through the legacy read the composition used (spine_compose.py line 326) - A2' reproduces the laws actually used; B issues
   through the door: facts through week w - 1 -> door -> issue state -> native_laws -> week w distributions.  p.py's three reads move onto the door inside B's registration;
   until then every replay reads the legacy representation.
D6 byte identity holds within a representation version where registered; across the reader boundary acceptance is the registered equivalence witness (same family, state,
   provenance, discrete selections; numeric equality up to the reader representation), frozen before judgment, never chosen from performance.
D7 reader groups 1, 3 and below are infrastructure audits; they proceed only on the active production path or when they block cascade priority 1, and never outrank
   A2' -> A3 -> B -> calibration atlas.
## CASCADE PRIORITY 1 - A2' - BUILD - Oct 4 2026 (A2's procedure, re-registered after the READER DOOR, LAW SCHEMA PLAIN NAMES and READER NOISE GOVERNANCE outcomes)
native_laws.py: build_inputs / fit_state(I, s) / row_laws(I, F, s) as in "A2 - BUILD", with the plain law schema and season names.  Historical side per D5: spine_rows,
   spine_sufficient and p.load through the legacy read the composition uses (spine_compose.py line 326); the A1 oracle and the wall witnesses through tables.read_table
   (the value written).  Single producers imported: hurdle.ztnb_fit, support, spine.pooled_rate, provenance.slice_sha, freeze.apply_freeze, p.load, tables.read_table.
ACCEPTANCE (judged once): python3 native_laws.py replay; exact equality with native_law_rows (every column, every layer, final flag) and native_law_season, and, as
   witnesses only, zero-history (m, r), hurdle (pi, m_pos, r_pos) per component / season and work order 20 (a) mu_c per row in the wall files.  Any difference -> REFUSED,
   reported per column; no rescue.  Writes only proj/native_laws_report.txt.
## CASCADE PRIORITY 1 - A2' - OUTCOME - Oct 4 2026 (python3 native_laws.py replay; native_laws.py 8571e8ca...)
ACCEPTED.  Tests 2021, 2023, 2024, 2025; zero-history PASS F5 TDs TE / WR, F5 receptions TE, Q4 passing TDs, QB rushing TDs; hurdle PASS F5 TDs / carries / receptions /
   targets RB, F5 receptions WR; work order 20 (a) RB, WR; chain L1 RB / WR, L2 RB, L3 RB / WR.  Law rows 109562 x 27: no differing column (every layer, final flag); season
   fits 108 = 108 identical; witnesses exact - zero-history (m, r) 47 component-seasons, hurdle (pi, m_pos, r_pos) 24, work order 20 (a) mu_c 8734 rows.  Inputs and oracle
   files unchanged.  One producer of the native laws from the recorded historical inputs (legacy read, D5); wall files witnesses only.  Next: A3.
## CASCADE PRIORITY 1 - A3 - BUILD - Oct 4 2026 (read: spine_compose.py whole; native_laws.py 8571e8ca... accepted as A2')
spine_compose.py consumes native_laws: frames from build_inputs() (retires pick, wide_skill, wide_qb, the SUP / TEAM builders); every production law parameter from
   fit_state(I, s) - support priors, team-target / WR-reception / TE-TD / QB-carries negative binomial size, WR beta-binomial concentration, receiving / rushing yards
   standard deviation parameter, QB passing / rushing yards variance per count, zero-history (m, r), hurdle (pi, m_pos, r_pos), work order 20 (a) volume x TDs per volume,
   work order 31 L1 receptions per target, L2 yards per reception mean / variance, L3 TDs per volume.  The wall parameter files (ZHR, HR, T20M) are no longer read by the
   composition; the work order 20 (a) wall-mean consistency check retires with T20M.  nb, nb_fit, bb_fit, spread, sd, ci, fl, GRID and the form tables are imported from
   native_laws (one implementation).  Unchanged: comparator forms (WR independent targets, Q2 independent completions, Q3 independent yards, Q5 independent interceptions,
   QB rushing yards independent), the unearned L3R rates, the A1 recording, every draw and every stream.
ACCEPTANCE (judged once): spine_compose.py exit 0 with the A1 coverage witness; the 23 composition outputs and native_law_rows / native_law_season identical (decompressed)
   within the legacy representation (D6); spine_compose.py reads none of f6_zero_history_replacement_rows, f6_zero_history_hurdle_rows, f6_td_volume_means.  Any difference
   -> restore; no rescue.
## CASCADE PRIORITY 1 - A3 - OUTCOME - Oct 4 2026 (python3 spine_compose.py; acceptance as registered)
ACCEPTED.  spine_compose.py exit 0; A1 coverage: law rows 109562 (final 93665), scored (row, term) pairs covered 92129 of 92129, season fits 108.  Wall parameter files named
   in spine_compose.py: 0.  The 23 composition outputs and native_law_rows / native_law_season identical (decompressed): 25 of 25.  The composition's frames and every
   production law parameter now come from native_laws (build_inputs, fit_state); the inline fits and the wall parameter reads are retired; every draw unchanged.
   Cascade priority 1 historical side complete (A1, A2', A3).  Next: B.
   Files now: spine_compose.py a9155963fc803abe..., native_laws.py 8571e8ca9036ba4d...
## CASCADE PRIORITY 1 - B PARITY RULE - Oct 4 2026 (owner ruling C; recorded before any B judgment)
Descriptive read (judges nothing): spine.issue(2025, N, fit_lt=2025), N = 4..16, legacy read, against history rows - compared 30123 row-terms over 35 term / position
   slices, state differences 0, values unequal 6785 with max |difference| 2.842e-14, history-only rows 210 (skill positions), issue-only rows 5899; grid selections not printed.
Rule for B issue-path vs history-path parity: exact - keys / domain, state columns, family, provenance, zero vs nonzero, KGRID / WGRID / KB / RGRID selections (printed,
   never inferred), eligibility on rows expected in both paths; continuous floating parameters |x_h - x_i| <= 16 * eps64 * max(1, |x_h|, |x_i|), eps64 =
   np.finfo(np.float64).eps; ULP distance printed as a diagnostic, not a gate.  Any failure stops for investigation; the bound is never widened after it is seen.
Parity universe H intersect I; history-only and issue-only domains accounted separately.  Order: 210-row history-only classification -> B1 shared row function (first gate:
   history old path = history shared-function path exactly) -> exact discrete parity -> 16 eps numeric parity.  B is not complete until the 210 rows are classified.
## CASCADE PRIORITY 1 - B COVERAGE CLASSIFICATION - Oct 4 2026 (reads: spine.issue(2025, N, fit_lt=2025), N = 4..16, legacy read; facts/player_game; data/rosters_2025)
History rows without an issue-path row at the same position: 32 player-weeks (RB 9, WR 8, TE 15; = the parity read's 210 history-only row-terms).  Two roots:
Root A - position is a per-week stats label (facts.py line 141, roster fallback line 191), not stable across weeks: 17 player-weeks - projected under another position 9
   (00-0038488 TE / RB 6, 00-0038590 TE / WR 2, 00-0039686 TE / RB 1); routed to the QB frame 2 (00-0036825, previous label QB); previous-week label FB, dropped by p.load's
   skill filter 5 (00-0035125 x2, 00-0034959 x2, 00-0036727; raw roster RB / ACT); previous-week raw roster position DB, no facts row 1 (00-0037091).  History keys the law
   slice by the week-N label (an outcome-week fact) - recorded as an information-time finding in the frozen history (D1, D3); the issue path keys by the previous
   team-game label (information-time valid, equally unstable).  B needs one information-time position rule.
Root B - outside the historical information set: 15 player-weeks whose previous-week raw roster status was RES 9, DEV 5, CUT 1 - outside the facts universe (facts.py line
   176: ACT / INA), so not p.candidates; 2023-25 have no price files in facts (SAL 2016-21).  Outside H intersect I for historical cutoffs.
Issue-only rows 5899 (candidates without a history row) are outside H intersect I by construction.
## CASCADE PRIORITY 1 - B POSITION RULE - Oct 4 2026 (owner ruling (b); recorded before any B judgment)
Issue-path routing: a week-N candidate's position = the most frequent stats label over his earlier played games of the season (weeks < N), ties to the most recent tied
   label; domain = p.load's played rows (skill labels QB / RB / WR / TE only).  A candidate with no earlier played labelled game -> UNRESOLVED POSITION (not routed, counted).
Invariant: the position rule may change routing, never the historical law definitions (laws stay keyed by the stats-position taxonomy they were fitted and judged on).
B1 prints, per candidate: earlier played-label sequence, selected position, differs-from-previous-game flag, law slice applied.  The 17 root-A player-weeks are classified
   under this rule before parity is judged.
Limit (code: p.py lines 41, 69-74): the rule changes routing, not candidate membership - p.candidates draws on p.load rows, which drop non-skill labels; the 6 root-A
   membership rows (previous-week label FB 5, raw roster DB 1) stay outside the candidate set under this rule as worded.
Stop: if the rule closes routing without new unexplained H intersect I omissions or discrete law mismatches, position routing is closed; a genuinely ambiguous hybrid case is
   labelled UNRESOLVED POSITION - no mapping rule is invented after seeing it.
## CASCADE PRIORITY 1 - B POSITION RULE - CLASSIFICATION - Oct 4 2026 (read: 2025 weeks 4-16 history rows, skill + QB, p.load / p.candidates, in memory)
History rows 4213; candidates 4192; not candidates 21 (= root B 15 + root A membership 6).  Candidates: previous label = history 4181; rule (b) = history 4184; fixed by (b) 7;
   broken by (b) 4 (00-0039686 w10 RB -> TE; 00-0035726 w11 TE -> RB; 00-0038488 w5 TE -> RB; 00-0038488 w14 TE -> RB); unmatched under both 4 (00-0038590 w7 history WR,
   rules TE; 00-0038488 w4, w9, w13 history TE, rules RB); UNRESOLVED POSITION 0.  Root A: the 11 routing rows all route under (b); the 6 membership rows stay non-candidates.
Stop rule applied ("without new unexplained H intersect I omissions or discrete law mismatches"): each of the 8 residual mismatches is a row whose week-N stats label (the
   frozen history's key) differs from the season-to-date label - the recorded root-A finding; the 21 non-candidates are root B and the recorded membership limit.  Position
   routing closed under the rule as recorded.
Outside the stop rule: rule (b) changes routing for 391 of 6149 candidates in weeks 4-16 (mostly issue-only, no history row); cause unknown - B1 prints every candidate's sequence.
## CASCADE PRIORITY 1 - B1a - SHARED ROW FUNCTION - BUILD - Oct 4 2026 (read: spine.py whole; mechanical extraction only)
spine.py: the per-cutoff spine-schema row list in history() (lines 152-170: F2 team terms, F4 / F5 by SL, F5 TDs, F5 receptions / yards, the eleven QB terms) moves verbatim
   (dedent only) into term_rows(kp, T, U, G2), called by history() per season; issue mode unchanged in this step.  One producer of spine-schema rows for B1's issue path.
ACCEPTANCE (judged once): in memory, nothing written - spine.history(p.load(), p.team_game()) under the legacy read reproduces the text of proj/spine_rows.csv.gz and
   proj/spine_sufficient.csv.gz byte for byte (decompressed).  Any difference -> restore; no rescue.  The recorded spine is not rebuilt (D3).
## CASCADE PRIORITY 1 - B1a - SHARED ROW FUNCTION - OUTCOME - Oct 4 2026 (in-memory spine.history, legacy read; nothing written)
ACCEPTED.  spine.history through term_rows reproduces proj/spine_rows.csv.gz (150877 rows) and proj/spine_sufficient.csv.gz (20918 rows) byte for byte.  spine.py has one
   producer of spine-schema rows; the recorded spine is untouched (D3).  Next: B1b (issue path through term_rows under rule (b), native_laws, parity).
   Files now: spine.py 038a4c0e6ac0cc5d...
## CASCADE PRIORITY 1 - B1b-1 - LAW FRAMES EXTRACTION - BUILD - Oct 4 2026 (native_laws.py 8571e8ca...; mechanical extraction only)
native_laws.py: build_inputs' frame builder (pick, TT, wide_skill, wide_qb, the work order 20 (a) TDW loop) moves verbatim into law_frames(A, S, M) - spine-schema rows A
   (freeze applied), sufficient statistics S, team map M (key, season, week, team) -> TT, SK, QB, TDW; build_inputs calls it.  One frame producer for the history path and
   B1b's issue path.  SUP, Z0, verdict sets and provenance stay in build_inputs (history-only fitting inputs).
ACCEPTANCE (judged once): the text fingerprint of every frame (TT, SK per position, QB, TDW per position, SUP, Z0) identical before and after; python3 native_laws.py replay
   ACCEPTED (exact).  Any difference -> restore; no rescue.
## CASCADE PRIORITY 1 - B1b-1 - LAW FRAMES EXTRACTION - OUTCOME - Oct 4 2026 (native_laws.py 93da6d38...)
ACCEPTED.  law_frames(A, S, M) extracted (13 frame lines + 7 TDW lines moved verbatim); frame fingerprints identical before and after, 29 entries (TT, QB, SK and TDW per
   position, SUP, Z0, verdict and test sets), both read from the kit's own native_laws.py; native_laws.py replay ACCEPTED exactly (law rows 109562 x 27, no differing column;
   season fits 108 = 108; witnesses exact).  The composition's frames are unchanged (it imports build_inputs).  One frame producer for the history and issue paths.
## PRODUCT FINISH LINES - REVISED - Oct 5 2026 (owner red-team: props benefit from within-game dependence; supersedes any "PRODUCT FINISH LINES - OWNER RULING")
Dependence has three places, kept separate: (1) within-player chain - earned and in place (work order 31 L1-L3 RB / WR, wall 9 TE copula); (2) shared state acting on one
   player's marginal (Root 3) - inside the prop product: an atlas cell with a state-specific tail miss that shared state can explain routes to Root 3 as a marginal fix
   (recorded residue: q.90 RB +.1622, WR +.1401 contested); (3) cross-player joint (teammates, QB <-> receivers, opponents) - drives each card's correlation panel and SGP /
   FLOOR / CEILING.  Current joint draws (spine_compose.py): WR targets share one team-target draw (positive link through team volume; competition for share not modelled);
   RB / TE targets independent of it; QB draws independent of every skill player; opponents unlinked.
Correlation panel: every pair carries a status - earned (with sign), tested near zero (registered test), or not modelled; "no impact" is never printed for a pair the engine
   did not test.
Prop product done: issue SEASON WEEK -> native distributions (B1, B2) -> calibration by stat x position x law state -> marginal fixes the atlas routes to Root 3 -> cards
   (center, P10 / P50 / P90, grade, law provenance, structure vs residue from a registered producer on the same draws, coverage status, correlation panel with pair
   statuses) -> P(over / under) at a line entered on the card (never a fit, law or score input; guard check 10; nothing fetched).
Full Slate Kit done: prop product + cross-player joint dependence earned for the pairs the panel lists + SGP / FLOOR / CEILING + DK transform and lineup objectives.
## DESCRIPTIVE READS - FORMATION, EFFICIENCY AND EXPLOSIVE PROPENSITY - Oct 5 2026 (read only; data on disk; 2026 weeks 1-3 descriptive only; nothing adjudicated)
League (pbp 2019-21, 2023-25): rush EPA -0.058 to -0.104 every season; dropback EPA peaked 2020 (+0.077); completed 20+ per dropback 0.0847 (2019) -> ~0.078-0.080 after;
   rush 20+ rate 0.0239 / 0.0244 (2019-20) -> 0.021-0.022; under-center dropback EPA above shotgun every season by ~0.08-0.11 (situational, confounded); shotgun share 0.86
   (2023) -> 0.82 (2025) -> 0.77 (2026 w1-3).  Fullback >= 25% of offensive snaps: 3-6 teams 2019-25, 7 in 2026 w1-3.  RB yards per carry (>= 50 carries): team-season R2
   0.501 vs label-shuffle null mean 0.432, 95th 0.495.
Composition calibration by prior explosive (20+) rate tertile, information-time rates, rows with >= 20 prior touches, spine_compose_rows 2021-25 (cut points pooled - binning
   look-ahead; diagnostic only): RB rushing yards - PIT > .9 flat (.120 / .140 / .125), PIT < .1 .027 / .097 / .148, mean PIT .522 / .495 / .451, PIT sd .260 / .300 / .309,
   y - center +4.52 / +1.78 / -2.89; WR receiving yards - PIT > .9 .131 / .129 / .123, PIT < .1 .075 / .097 / .172, mean PIT .508 / .472 / .430, PIT sd .291 / .301 / .318,
   y - center +2.77 / -0.16 / -5.97.  Reading: season-to-date yards centers carry non-persistent explosive yardage (high-explosive over-centred, low under-centred);
   pooled spread too narrow for high, too wide for low RB; the ceiling miss is not explosive-concentrated (Root 3 candidacy unchanged).  A law change needs a registered
   wall (earlier-season cut points, harness verdict).
Not on disk: participation (personnel, coverage shell, box) and FTN charting (play-action, motion) - pbp carries only shotgun, no_huddle.  On disk: prop_snapshots,
   line_snapshots, dk_watch (market) - never a fit, law or score input (guard check 10).
## SOURCE FAMILIES - PARTICIPATION AND FTN - REGISTRATION - Oct 5 2026 (owner ruling (b); probe: all seasons available, no market columns, join to pbp 1.000)
Acquisition is not eligibility: fetch -> canonical facts -> availability witness -> diagnosis -> registered wall -> earned use.
Eligibility (information-set contract): a source value is forecast-eligible iff its availability is proven no later than the issue cutoff.  Participation: source season <
   forecast season, no exceptions (2026 file absent; released after the postseason).  FTN live: our fetch / accept timestamp < issue timestamp.  FTN historical same-season:
   only with a historical availability witness; otherwise source season < forecast season.  2026 FTN probe (descriptive): weeks 1-3 complete, week 3 present by Sep 30;
   date_pulled shows presence by a pull, not first availability.
Naming (facts, when first read): one owner and one plain name per fact - defense_box_count, pass_rusher_count, charted_qb_location, on_field_player_ids; on-field presence is
   never called participation (project meaning: availability); receiver alignment is never called slot (depth_slot = depth rank); source target_share / air_yards_share stay
   out of facts (facts owns its count-derived producers); snap_share is not replaced - an on-field metric starts as on_field_offense_share.  Raw files keep source names.
This transaction: fetch.py opt-in --sources participation,ftn for completed seasons (<= FROZEN_THRU) - participation 2019-21, 2023-25; FTN 2023-25.  data/_incoming,
   checked (rows > 0, required columns, game ids in season, join to pbp regular-season pass / run plays >= 0.999), downloaded bytes gzipped unchanged, moved into data/ only if
   every file passes, never re-fetching a file in data/; counts only after guard.py --accept.  Live 2026 FTN (timestamp witness) is a separate transaction.
## SOURCE FAMILIES - PARTICIPATION AND FTN - OUTCOME - Oct 5 2026 (fetch.py 6f72b76e81e2bfbe; facts/raw_manifest.json 761 files)
Fetched through the fetch.py sources section (opt-in --sources; refuses seasons after FROZEN_THRU and before the family's first season; never re-fetches a file in data/;
   checks rows, required columns, game ids in season and the join to pbp >= 0.999; stores the downloaded bytes gzipped unchanged; moves files only if every file passes).
   pbp_participation 2019 / 2020 / 2021 / 2023 / 2024 / 2025: rows 48034 / 48513 / 50714 / 46168 / 45919 / 45184.  ftn_charting 2023 / 2024 / 2025: rows 48225 / 48031 / 47316.
   Join to pbp 1.0000 for all 9 files.
The first fetch succeeded but was restored by mistake: the full guard report's unrelated FAIL lines read as a fetch failure.  The re-fetch printed the raw manifest difference
   on its own: added 9, changed 0, removed 0.  The acceptance step refused unless the additions were exactly these 9; it accepted (761 raw files), and the difference after
   acceptance is 0 / 0 / 0.
Guard FAIL lines classified as unrelated to the fetch: check 3 (fit_contract.py defines features - pre-existing); check 5 (p_walk / a_walk / j_model older than the facts rebuild's
   timestamps); check 9 (L freeze, p.py / facts.py - open in the rename map); check 10 (spine_compose.py:486 calibration "status" column - a false positive).
Acquisition is not eligibility.  Nothing enters facts or any forecast.  Order under the registration: facts transaction (plain names, eligibility columns, availability witness)
   -> live FTN timestamp witness design -> diagnosis reads -> registered wall -> earned use.  Participation for season S is eligible only for forecast seasons after S; FTN
   same-season data needs a witness.
## GUARD CHECK 5 - REGENERATION - OUTCOME - Oct 5 2026 (p.py 551886a5d38a9627, a.py 4657f63e20145ee9, j.py 1db6ce6aa3b70909, facts.py 61a896d094661704)
Cause: proj/p_walk.csv.gz, a_walk.csv.gz and j_model.json (Oct 3 16:04) were older than p.py (Oct 4 15:33) and facts/*.csv.gz (rebuilt through the reader door Oct 4).
   Check 5 compares facts/*.csv.gz only; the raw manifest is not counted.
Rerun p.py, a.py, j.py (exit 0 each).  Gate: .gz files identical apart from gzip header bytes 4-7 (MTIME), and decompressed content identical; every other file byte-identical.
   a_cells.json, a_report.txt, j_model.json, j_report.txt, p_coef.json, p_report.txt byte-identical; a_walk.csv.gz (mtime 1791057846 -> 1791199221) and p_walk.csv.gz
   (1791057845 -> 1791199220) identical apart from MTIME.  GATE PASS; guard check 5 ok.  The default-parser epa_play read (team_game, 50 of 3,744 rows) reaches no
   p / a / j output.
First whole-file comparison refused on the gzip MTIME alone (probe: bytes after the 10-byte header identical, decompressed identical); a second pass was undone by a
   standalone failure-only restore run after the gate passed.  Both were instrument defects.
Work order: C-gz - gzip writers stamp wall-clock time into outputs (fix touches p.py and a.py, frozen in l.py, check 9; other .csv.gz writers unread).  C-door - restores
   live only inside the gated block, blocked by a pass marker; no standalone restore.
## GUARD CHECK 3 - FEATURES SINGLE DEFINITION - OUTCOME - Oct 5 2026 (fit_contract.py 36fc03b3d0fbedcc -> b3683a8e3afb36a7)
Cause: fit_contract.py:41-43 defined features(), a cache wrapper around p.features(p.load()) - a second definition of a core name with the same semantic goal.  Its only caller
   was slice_rows; nothing outside fit_contract.py named fit_contract.  PROD (producer sha256s) is recorded in manifests and the report header only, never compared.
Edit: wrapper deleted; the same cache (_CACHE["H"] = p.features(p.load()) on first use) inlined at its single call site.  No importers; the name is no longer read.
Gate (in-process, no file written; the WORK ORDER 48 artifacts are judged and frozen): replay of wr_receiving_yards_scale (6954 held-out rows), wr_receiving_yards_scale_spline
   (6954) and te_receiving_yards_location (4235) - rows payload and params text IDENTICAL for all three.  GATE PASS; guard check 3 ok ("each core function has one definition").
The WORK ORDER 48 OUTCOME keeps fit_contract.py 36fc03b3...; any future replay manifest records b3683a8e....
## CORRELATION PANEL - OWNER RULING D1 - Oct 5 2026 (D1 = (b); amends PRODUCT FINISH LINES - REVISED for the panel's definition of done)
Prop product done: the correlation panel reports an honest pair status; individual cards stay valid whatever the pair status.  SGP product done: every dependence term
   that alters an SGP combined probability is earned by a registered joint test.  No earned relationship -> no dependence-adjusted SGP probability (never a silently
   assumed correlation; never P(A and B) = P(A) P(B) unless TESTED - NO MATERIAL IMPACT for that relationship).
Pair statuses (one per panel cell): EARNED POSITIVE - supported positive dependence, may raise the joint probability; EARNED NEGATIVE - supported negative dependence, may
   lower it; TESTED - NO MATERIAL IMPACT - only after a registered test, independence usable for that decision; UNRESOLVED - evidence exists, gate not earned, never used
   numerically; UNTESTED - no claim, never used numerically.
Test quantity: event relationships P(A > line A, B > line B) against what the marginals imply, tails first - not Pearson correlation of raw stats.  Joint probabilities come
   from joint draws under the earned mechanism, never from multiplying marginal probabilities.
Root: shared game / player state -> joint native-stat draws -> pair dependence -> SGP combined likelihood.  The panel is a display and owns no statistical logic; the
   same earned dependence feeds the panel, SGP probabilities, DK stacks, lineup FLOOR and lineup CEILING.
Candidate order for joint walls (not every pair): 1 QB - own WR / TE; 2 QB - opposing QB / passing environment; 3 RB - own passing game where role competition matters;
   4 same-team target competitors; 5 opposing correlated scoring environments; 6 rarer structures.
## TAXONOMY - ONE SPELLING PER MEANING - OWNER RULING - Oct 5 2026 (TAXONOMY.md ; builds on the Oct 3 plain-language rename map)
Owner: eliminate alternative spellings so all future data routes through one name per meaning; one matrix kept as the reference (TAXONOMY.md).  Rules: one meaning, one
   spelling in code, facts, proj and cards (raw keeps source spellings; old records through canon.plain(), split by file; CHARTER prose bridged by the matrix); _status =
   a designation published by the league or a team only, bare status retired; coverage = calibration coverage only, issued = whether a player-week was forecast;
   participation = availability only, on-field presence = on_field_*; slot = depth slot only.
New names: roster_status (facts status), tail_coverage_band (calibration status), issue_mode (issue-file status), issued / not_issued_reason (card coverage status),
   pair_dependence (D1 pair status), f8_tail_coverage_band.csv, position_to_date.  Registered source names: defense_box_count, pass_rusher_count, charted_qb_location,
   on_field_player_ids, on_field_offense_share.
OPEN (owner decision after a read): _season_avg / _season_mean / _to_date may carry one meaning in two or three spellings.
Code moves onto the matrix in gated transactions (first: C10 - roster_status, tail_coverage_band, issue_mode).  Work order: a guard check that canon.py and TAXONOMY.md agree.
## TAXONOMY - ONE SPELLING PER MEANING - SHA CORRECTION - Oct 5 2026 (TAXONOMY.md ac24ca8cb5a6b099; 139 table lines)
Line 3613's header records "TAXONOMY.md ;" with the sha blank: the block was split by hand and the CHARTER heredoc ran in a shell without the sha variable.  The ruling at
   line 3613 refers to TAXONOMY.md ac24ca8cb5a6b099 (139 table lines, last row "Kept").  Instrument rule from here: short standalone blocks, no variable shared between
   blocks, quoted heredocs with literal values.
## C10a - TAIL COVERAGE BAND RENAME - OUTCOME - Oct 5 2026 (spine_compose.py a9155963fc803abe -> d5113e0bb59d18b1; f8_tail_attribution.py e27f4517989f0f1b -> 3ba009ca50a1c4d3; TAXONOMY.md ac24ca8cb5a6b099)
Taxonomy: the calibration column "status" (within band / too low / too high) is tail_coverage_band; proj/f8_tail_calibration_status.csv is proj/f8_tail_coverage_band.csv.
   Edits: spine_compose.py column and file name (lines 486, 497); f8_tail_attribution.py file name (lines 3, 19) and whole-word status (lines 19, 29, 61, 68).
Rerun: spine_compose.py exit 0 in 103 s; f8_tail_attribution.py exit 0.  Gate over all of proj/ against a snapshot: 211 of 211 files pass (gzip files identical apart from
   header MTIME; f8_tail_attribution_rows.csv header only); the only added file is f8_tail_coverage_band.csv, equal to the old file apart from the header.  GATE PASS.
   The old file was deleted (no archive).  Guard check 10 ok (75 scripts checked).
Finding: guard check 10's pattern does not see a status= keyword (spine.py:222, C10b) or the capitalised DraftKings Status (dk_classic.py:46, C-M4); the pattern is
   redefined with C10c (roster_status).  CHARTER prose naming the old file (LINE 27a, lines 2447 / 2450) is bridged by TAXONOMY.md.
## C10b - ISSUE MODE RENAME - OUTCOME - Oct 5 2026 (spine.py 038a4c0e6ac0cc5d -> 31644f3b9675f816; canon.py 0a987fd7d9014f93 -> 32b243571a290cd2; TAXONOMY.md ac24ca8cb5a6b099)
Taxonomy: the issue files' column "status" (DRY RUN before the stat-spine freeze - not prospective) is issue_mode.  spine.py:222 writes issue_mode.  No code read the old
   column (dk_classic.py reads the issue file but not that column).
canon.py: PLAIN_FILE = [("spine_week_", {"status": "issue_mode"})] and plain(o, path=None) - the split by file the rename map requires for records; with a path, file-set
   names map first; without a path every existing caller is unchanged.  proj/spine_week_2026_w4.csv (judged, line 39b OUTCOME) stays on disk and reads as issue_mode
   through canon.plain(d, path).
Gate: python3 spine.py 2025 10 exit 0 in 4 s (candidates 453, projected 369, unprojected 84, teams 28); spine_week_2025_w10.csv body identical, header differs only
   status -> issue_mode; the other 210 proj files identical; canon.plain without path keeps status, with the record's path reads issue_mode.  GATE PASS.
## C10c - ROSTER STATUS RENAME - OUTCOME - Oct 5 2026 (facts.py 61a896d094661704 -> 4aa7635c2e58b5ab; p.py 551886a5d38a9627 -> 45d16a1a3782a769; classe.py e948ed656995143a -> 519cb9c93c9a92fc; guard.py 40eda3fabbdc20ac -> 1690934a82d81079; canon.py 32b243571a290cd2 -> 4886c89d5a8b7236; TAXONOMY.md ac24ca8cb5a6b099)
Taxonomy: the game-day roster designation (ACT / INA / RES ...) is roster_status in facts and below; raw rosters keep the source spelling status at the read (facts.py
   line 51, and the rename at line 148).  Edits: facts.py lines 148 / 177 / 190 / 205; p.py WEEKN; classe.py line 35; canon.py PLAIN_KNOWN; guard.py check 10 pattern names
   roster_status (drops the quoted and attribute status forms) and a new rule rejects bare status (quoted, attribute or keyword) outside facts.py, fetch.py, canon.py, guard.py.
Reruns: facts.py 13 s, p.py 3 s, a.py 1 s, j.py 2 s, classe.py 5 s (exit 0 each).  Gate: facts/player_game.csv.gz body identical, header differs only status -> roster_status;
   facts 5 of 5 and proj 211 of 211 pass (gzip MTIME aside); proj/study_classe.txt equals the original classe.py's output on the same state (reference taken before the edit);
   p.descriptors() carries roster_status.  GATE PASS.  Guard: check 4 ok (DST 98.4%, skill 99.6%), check 5 ok, check 10 ok (75 scripts), no retired-spelling line.
First attempt refused on proj/study_classe.txt and restored: the recorded file (Oct 3 12:25) predated the rename and classe.py (Oct 3 16:03) - the original code also differs
   from it (labels q_M / q_R -> p_absent_calibrated / p_absent_logistic; two null 95th values, because classe.py:77 seeds its null with len(Z) + len(col)).  The study file
   is now current (no archive).
Work order: C-classe-seed (null seed depends on a column name's length); C-classe-labels (q_M / q_R in report text, the roster label); C-M4 (capitalised DraftKings Status).
## TAXONOMY VERSION 2 - ONE PLAIN WORD PER CONCEPT - OWNER DIRECTIVE - Oct 5 2026 (TAXONOMY.md ac24ca8cb5a6b099 -> 99b1a17fda3b03ac; 127 table lines; version 1 replaced, no archive)
Owner: collapse every alternative spelling of each orthogonal concept into its plain-language meaning.  Grammar: <scope prefix><quantity>_<aggregate>_<window>.  One word per
   concept: mean (avg, std as mean), median, standard_deviation (sd, std), standard_error (se, std_err), previous (last, prev, lag), number (no), opponent (opp, oppo),
   opportunity / opportunities (opp, opps), defense (def), probability_ (p_), _prediction (_pred, _hat), percent (pct), seconds (secs), times (x), availability, fraction,
   shrinkage.
Windows read from code: earlier_games_this_season (p.py:49, retarget.py:21/34/37, ystick.py:158-164, avail.py / score_t.py merge_asof allow_exact_matches=False - no
   look-ahead; retires _season_avg, _season_mean, _to_date's rename-map meaning); through_this_game_this_season (avail.py:36, j.py:27, retarget.py:62; retires _through_game
   and those _to_date uses); earlier_games_this_season_with_team (alloc.py:42); previous_3_games_this_season; previous_game_this_season; previous_game / second_ / third_
   (cross seasons); previous_season (p.py:50); team_ prefix for the team's own value.
OPEN: domain acronyms (dk, dst, td, qb, rb, wr, te, epa, pit, id, pbp, ftn); snap_share_to_date's window; the windows of own_median_dk / own_dk_sd; merge suffixes
   _dk / _ours / _at / _st / _prev.  Code moves onto version 2 in gated transactions, one concept at a time; old records through canon.plain().
## TAXONOMY - DOMAIN ACRONYMS AND PCT - OWNER RULING - Oct 5 2026 (TAXONOMY.md 99b1a17fda3b03ac -> 431e4cc2e91973cf; 129 table lines)
Owner: dk, dst, td, qb, rb, wr, te, epa, id, pbp kept as written.  ftn is a source name (FTN Data) - raw file names only, under the source-spelling rule.  pit = pct: pct is the
   word for where the result landed inside the forecast distribution (0 to 1); percent keeps "a value on the 0-100 scale".  Renamed in the matrix: outcome_pit -> outcome_pct,
   outcome_pit_scored -> outcome_pct_scored, outcome_pit_percent -> outcome_pct_percent, near_zero_pit / ordinary_pit / ordinary_pit_window -> near_zero_pct / ordinary_pct /
   ordinary_pct_window; added composed_pct (pit_comp, spine_compose rows).  Work order: C-pct-scale - one concept on two scales (0-1 and 0-100) in recorded files.
## TAXONOMY - OPEN MEANINGS READ FROM CODE - OUTCOME - Oct 5 2026 (TAXONOMY.md 431e4cc2e91973cf -> 2247d19f2dea3de4; 132 table lines)
snap_share_to_date carried three meanings: the earlier-games window at the row (j.py:27-31, retarget.py:62-64, merge_asof allow_exact_matches=False), the with-team window
   (alloc.py:41-42), and two non-snap meanings left by the Oct 3 role -> snap_share_to_date rename: chain.py:116 / 123 key (event minus control snap change -> snap_share_change)
   and register.py:32-41 field (PRIMARY / secondary confirmatory -> hypothesis_role; recorded in register.py's JSON, read through canon.plain() when it migrates).
own_median_dk / own_dk_sd = earlier-games window (retarget.py:38) -> dk_points_median_ / dk_points_standard_deviation_earlier_games_this_season.  Merge suffixes: rule - a
   merge suffix names its source; _dk / _ours (fetch.py:79); _at -> _at_rows (h7.py:68); _st (score_d / score_y) and the score_s _prev merge named at their migration; _prev as
   a window retired (p.py:50 previous season; chain.py:81 previous game).  j.py:31 dk_expected is the earlier-games mean.  pit_of -> pct_of.  frozen_at / fit_at are plain English.
## TAXONOMY VERSION 3 - ONE NAME PER MEANING - OWNER RULINGS - Oct 5 2026 (TAXONOMY.md 2247d19f2dea3de4 -> 4dc13d00c76da43c; 109 table lines; version 2 replaced, no archive)
Owner rulings: D3 - nothing is frozen until the final spellings are in, then one freeze; the migration is one full pass (no drift between partial passes); every term is
   at most two words, and a collision from shortening is collapsed when the data shows one meaning; one name per meaning; pct removed - rank (where the result fell in the
   forecast, 0 to 1, full precision) and percent (0-100) kept separate because they differ.
Data that decided collisions: outcome_pit_pct is not 100 x outcome_pit (exact or whole-number rounding) on 3,840 dstick rows - sample fits one-decimal rounding -> separate
   outcome_percent (display only); window A from p.py:49 equals the retarget.py / ystick.py formula on 40,741 played rows (snap_share max difference 5.551e-17, target_share 0)
   -> one name season_pregame now, one producer later in its own transaction (values move at 1e-17); recent1 (within season) differs from previous_1 (across seasons) on 2,815
   of 40,741 rows -> two names; p_event duplicates pi in f6_zero_history_hurdle.py:33 -> one column probability_nonzero.
Red team (ambiguity for a reader or for Claude): pct read as percent; last (final or most recent); prior / previous synonyms; state, role, base, change, event and number each
   carried two meanings; expected / mean / prediction now fixed apart; hypothesis_rank -> hypothesis_priority (rank is the forecast word).
OPEN: snap_tier_label (may be snap_tier in a second encoding); the q_B absence model's qualifier; shorthist.py f1; f6_zero_history.py:31 p.  Next: rename_pass.py (table,
   per-file overrides, line edits, attribute and collision guards), registration of the pass, one edit, rebuild in producer order, value-identity gate, one freeze.
## TAXONOMY VERSION 3 - OPEN ITEMS READ FROM CODE - OUTCOME - Oct 5 2026 (TAXONOMY.md 4dc13d00c76da43c -> b7cc35a5e2f7a693; 109 table lines; no OPEN rows)
snap_state_label = snap_tier mapped {1: low, 2: mid, 3: high} (at_t.py:19, at_wall.py:35; one-to-one in at_rows) -> one name snap_tier, the label column dropped, labels printed
   from the tier (gatesim.py:22's string-valued tier moves the same way).  q_B / p_absent_base = training absence rate of his snap tier (avail.py:64) -> probability_absent_tier.
   shorthist.py:107-111: f1 = candidate P1 fail rate -> fail_rate_candidate; near_zero_pit there = baseline P0 fail rate (v1 renamed f0 by mistake) -> fail_rate_baseline.
   f6_zero_history.py:31 p = zeros (zero-history law: P(Y > 0) = 0) -> probability_nonzero.  Next: rename_pass.py with a dry run.
## ONE FULL RENAME PASS - REGISTRATION - Oct 5 2026 (rename_pass.py b0c48ac51f089d90; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
Owner rulings: one full pass, no partial passes; everything renamed, local names included ("rename everything in one pass so we can move on to the actual work"); one
   name per meaning, after splitting each conflated spelling by meaning; terms at most two words; nothing frozen until the final spellings are in, then one freeze.
Table (rename_pass.py): version 3 explicit map; suffix / prefix grammar; per-file overrides where one spelling held several meanings (pi, f0, f1, kb, ka, kr, RGRID, sh,
   tgt, rs, std, w3, games_before team vs player, dk_expected in j.py and its build() readers, _to_date by file); 27 exact line edits (retarget team concatenations and the
   merge from postgame to pregame, j.py merge, alloc.py stint, hurdle p_event drops, canon.SRC pit_of -> rank_of); fragment rule for names outside the map (pos -> position,
   car -> carry, sd -> standard_deviation, se -> standard_error, resid -> residual, exp -> expected, hat -> prediction, prev -> previous, avail -> availability, pit -> rank,
   pct -> percent, med -> median, opp -> opponent, thru -> through) with overrides read in context (m_pos / r_pos -> positive_part_untruncated_mean /
   positive_part_negative_binomial_size; snap_last -> snap_share_recent1; sh -> shrunk_mean_league / shrunk_mean_peer / share / test_standard_deviation / config_hash;
   tgt -> response / destination; vol -> volume_rows / volume_m / volume_y; last -> previous_row / final_season).  Kept: losses l0-l3, w1 / w2, l2_regularization,
   score_d's sd_exec / sd_fail / sd_hash, prose and docstrings, pandas literals, facts.py raw internals, raw source spellings, model file stems p_coef / p_walk / p_report.
Guards: attributes renamed only where the name is a column string in the file; imported library names never renamed; project names follow their definer in every importer;
   module names never renamed.  Dry run: files changed 101; token changes 2788 (931 distinct); line edits 27, not matching exactly once 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0 | canon.py plan: PLAIN_COL 76 -> 136; PLAIN_SUF 17 -> 23; PLAIN_PRE 7 -> 10; PLAIN_KNOWN 148 -> 240 | identifiers still carrying a retired fragment: 0 distinct, 0 uses: | fragment renames (rule PART): 180 distinct, 1007 uses (full list in /tmp/slate_rename_dry.tsv).
Deferred, before the freeze: snap_state_label collapse into snap_tier (keys and report text change - own transaction); window A to one producer (values move at 1e-17 - own
   transaction).  Files renamed: avail_rows.csv.gz -> availability_rows.csv.gz, avail_report.txt -> availability_report.txt.
Gate (layered along the producer order, snapshot kept until the last layer passes): rerun each live producer; every output equals its snapshot with names mapped by the same
   table (CSV headers by new_name for the producing file; reports and JSON by map_text; gzip decompressed); any difference -> the pass is refused and the snapshot restored.
   Judged artifacts stay as recorded and are read through canon.plain(); fit_contract replay compares through the table.  Layer 1: facts.py, p.py, a.py, j.py.
## ONE FULL RENAME PASS - ATTEMPT 1 - REFUSED AND RESTORED - Oct 5 2026 (registration above; snapshot /tmp/slate_pass)
Applied (101 files and canon.py tables; every file compiled).  Layer 1: facts.py exit 0 in 13 s; p.py exit 1 at line 130 - KeyError on the renamed feature lists
   (air_yards_share_mean_season_pregame, ..._previous_1, ...).  Cause, an instrument defect: Python 3.12 tokenizes f-strings as FSTRING_START / FSTRING_MIDDLE /
   FSTRING_END, and rename_pass.py rewrote only NAME and STRING tokens, so names built inside f-strings (p.features f"{c}_lag{k}", f"{c}_season_mean") kept the old
   spelling while their readers were renamed.  Compiling cannot see it; running did.  Refused as registered; code, facts and proj restored from the snapshot and verified.
Fix before attempt 2: rewrite FSTRING_MIDDLE text from the source; flag every f-string piece that continues into a {field} (a name composed in pieces, e.g. "_lag" + {k})
   and give each an exact line edit; the fragment scan covers f-strings.  Attempt 2 is registered afresh with a new snapshot.  Instrument rule: no exit in pasted blocks.
## ONE FULL RENAME PASS - ATTEMPT 2 - REGISTRATION - Oct 5 2026 (rename_pass.py f0fcf80b7e2ed2c8; TAXONOMY.md b7cc35a5e2f7a693; fresh snapshot /tmp/slate_pass)
Rulings, table, guards, deferrals, file renames and gate as in the registration above.  Instrument changes since attempt 1: FSTRING_MIDDLE text rewritten from the source
   slice; every f-string piece that continues into a {field} is flagged; the fragment scan covers f-strings.  Flagged pieces resolved by exact line edits (p.py and
   purity.py f"{c}_lag{k}" -> f"{c}_previous_{k}"; line edits now 29).  Overrides read in context: spine_compose.py p_pos -> probability_per_trial (catch rate per
   target, work order 31); zero_test.py pi -> probability_near_zero; snap_ws -> snap_share_mean_season_pregame.  Gate refuses if the pass changes rename_pass.py itself.
   Dry run: files changed 101; token changes 2842 (951 distinct); line edits 29, not matching exactly once 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0 | canon.py plan: PLAIN_COL 76 -> 137; PLAIN_SUF 17 -> 23; PLAIN_PRE 7 -> 10; PLAIN_KNOWN 148 -> 241.
## ONE FULL RENAME PASS - ATTEMPT 2 - REFUSED AND RESTORED - Oct 5 2026 (attempt 2 registration above; snapshot /tmp/slate_pass)
Applied (101 files and canon.py tables; rename_pass.py unchanged; every file compiled).  Layer 1: facts.py, p.py, a.py, j.py exit 0; gate 11 outputs same, 2 different:
   proj/p_report.txt line 18 (mapped snapshot 'drop previous_row-week role   d_rho', new 'drop previous_row-week role d_rho'); proj/a_walk.csv.gz line 1 (cell inputs
   'season_role_state,position' vs 'role_tier,position').  Refused as registered; restored and verified.
Causes: (1) the override p.py last -> previous_row (the local name for his last row) also rewrote the English word in the prose label 'last-week role' (p.py line 27 DROP
   keys), and the padded label widened; (2) the gate mapped CSV headers only, while a.py writes the chosen input names into a_walk column inputs (snapshot scan of layer 1
   CSV cells: that column only, 9469 cells).
Fix before attempt 3: a file override of a bare word (no underscore) applies inside a string only when the string is exactly that word; map_text treats a word standing
   alone between quotes the same way; the gate maps every comma-separated cell token through the same table and compares CSVs row by row; comparison stays strict.
## ONE FULL RENAME PASS - ATTEMPT 3 - REGISTRATION - Oct 5 2026 (rename_pass.py 255f048005c478a7; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
Rulings since attempt 2: "one name per orthogonal semantic meaning"; "rename everything, delete alternative spellings. rename short local names to their full 1-2 word semantic meaning in
   plain language. If more than one spelling delete the other. If a collision happens, collapse them to one term"; one pass.
Table additions: role_tier (per game, this game's snaps) / role_tier_team_season_pregame (earlier team-games, absent = 0; row 56 split) / role_tier_team_recent1..3 (st1..st3;
   a.py last folds into recent1); snap_tier_season_pregame (snap_state, 9 producers); snap_share_mean_team_season_pregame (snap_share_season_mean_out_zero); new window
   team_season_pregame; spine sh@ -> share@ in 7 files (counted line edits); mad, ds_mad, rg_mad -> decile_deviation (canon SRC / TEST_BATTERY / STEM / STEMKEY line edits,
   CANON_EXPORT); short-name table 4847 variable renames in 106 files (variable role only - columns, attributes and whole strings keep their spelling until the column pass).
Instrument since attempt 2: bare-word file meanings bind names, not prose (whole-string rule); library-call keywords classed by the resolved callee's signature (explicit
   parameter kept; **kwargs or mapping type = data name); keywords to imported project functions follow the definer; names imported with 'as' renamed at their position;
   f-string conversion characters kept; counted line edits.  Gate: CSV cells mapped token by token; renamed lines that differ only in padding counted and printed;
   TEXT_WORD a.py last.  Dry run: files changed 107; token changes 33439 (5842 distinct); line edits 43, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.  Gate and layers as registered for attempt 1.
## ONE FULL RENAME PASS - ATTEMPT 3 - REFUSED AND RESTORED - Oct 5 2026 (attempt 3 registration above; snapshot /tmp/slate_pass)
Applied (107 files and canon.py tables; rename_pass.py unchanged; every file compiled).  Layer 1 PASS: facts, p, a, j exit 0; 12 outputs same (a_report: 3 renamed lines differ
   only in padding).  Layer 2: avail.py exit 0, 2 outputs same; at_t.py exit 1 at line 17 - at_rows lacks {snap_tier_season_pregame, probability_absent_calibrated,
   probability_plays}: at_t.py reads the judged at_rows.csv.gz directly, not through canon.plain(), while its column list was renamed.  Refused as registered; restored.
Fix before attempt 4: every direct reader of a judged artifact reads it through canon.plain() (readers measured before the fix).
## ONE FULL RENAME PASS - ATTEMPT 4 - REGISTRATION - Oct 5 2026 (rename_pass.py 34fdfdcaabeec871; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As attempt 3, plus: judged files derived from code (every file literal the project passes to canon.plain()); every direct read of one (read_csv / read_table / json.load)
   wrapped as plain(read, file) with the canon import added - 16 reads in 13 files.  Restore replaces files (temp + rename) so read-only frozen artifacts restore.
Layers: 1 facts, p, a, j; 2 avail, at_t; 3 dstick, ystick, retarget; 4 spine 2025 10, spine_compose, f8_tail_attribution; 5 fit_contract replay, native_laws replay;
   6 classe, h7 validate.  Each producer's changed files under facts/ and proj/ are gated against the snapshot (file stems mapped back); a file with no snapshot
   counterpart refuses.  Dry run: files changed 107; token changes 33442 (5842 distinct); line edits 43, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 4 - REFUSED AND RESTORED - Oct 5 2026 (attempt 4 registration above; snapshot /tmp/slate_pass)
Applied (107 files; rename_pass.py unchanged; every file compiled).  Layer 1 PASS (12 outputs same; a_report 3 padded lines).  Layer 2: avail.py exit 0, 2 outputs same;
   at_t.py exit 1 at line 16 - NameError: plain not defined.  Cause, an instrument defect: judged_wrap tested whether the name plain was used (it is, by the wrap itself)
   instead of whether it was imported, so the canon import was never added.  Compiling cannot see a missing import.  Refused as registered; restored.
Fix before attempt 5: the import is added unless the file imports or defines plain; the dry-run block checks every wrapped file for the import.
## ONE FULL RENAME PASS - ATTEMPT 5 - REGISTRATION - Oct 5 2026 (rename_pass.py 6c2a1cf3c1fce5e9; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: the canon import is added unless the file imports or defines plain (attempt 4 tested use, not import); the dry-run block checks every wrapped file.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33442 (5842 distinct); line edits 43, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 5 - REFUSED AND RESTORED - Oct 5 2026 (attempt 5 registration above; snapshot /tmp/slate_pass)
Applied (107 files; rename_pass.py unchanged; every file compiled; every wrapped judged read imports plain).  Layer 1 PASS (12 same).  Layer 2 PASS (avail 2 same;
   at_t exit 0, 2 same, 6 padded lines).  Layer 3: dstick.py exit 1 importing retarget - retarget.py:104 KeyError 'own_abs_tgt': the column was renamed
   (own_abs_tgt -> own_vacated_target) while the reader composes f"own_abs_{share_kind}"; the f-string flag fired only for pieces carrying a retired fragment.
   Refused as registered; restored.
Fix before attempt 6: the dry run flags every f-string whose literal pieces, with each field as identifier text, fully match an old string name the pass renames;
   each flagged site gets a counted line edit.
## ONE FULL RENAME PASS - ATTEMPT 6 - REGISTRATION - Oct 5 2026 (rename_pass.py 15b43cd5c83c3d8c; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: every f-string whose literal pieces could build a renamed string name is flagged in the dry run; 3 real sites given counted line edits (p.py and purity.py season mean, retarget own_abs); 8 reviewed false matches recorded with their loop values.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33440 (5840 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 6 - REFUSED AND RESTORED - Oct 5 2026 (attempt 6 registration above; snapshot /tmp/slate_pass)
Applied (107 files; every file compiled).  Layer 1 PASS (12 same).  Layer 2 PASS (avail 2 same; at_t 2 same, 6 padded lines).  Layer 3: dstick.py exit 0 but its outputs
   end early - dstick_report.txt stops at line 14 and dstick_rows.csv.gz at row 3841 (the 2026 w4 coming-week rows are not written).  A rename silently emptied a
   branch; compiling and the dry run cannot see it, the gate did.  Refused as registered; restored.  Cause read from the applied state before the restore (Read Y).
## ONE FULL RENAME PASS - ATTEMPT 6 - CAUSE CORRECTED - Oct 5 2026 (corrects the attempt 6 refusal entry above)
Not a rename.  dstick.py writes coming-week rows only under `if len(sys.argv) > 2` (dstick.py:83; usage python3 dstick.py [SEASON WEEK]); the snapshot dstick_rows end with
   (2026, 4): 32 rows and its report with "coming week 2026 w4", so the artifact was produced by python3 dstick.py 2026 4, while layer 3 ran dstick.py without arguments.
   The renamed coming-week code (lines 83-93) reads consistently.  Fix: each layer's run form is derived from the producer's usage line and sys.argv uses, checked against
   the last season / week in its snapshot outputs (Read Z).
## ONE FULL RENAME PASS - ATTEMPT 7 - REGISTRATION - Oct 5 2026 (rename_pass.py 15b43cd5c83c3d8c; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: layer run forms derived from each producer's usage line and its snapshot outputs: dstick.py 2026 4, ystick.py 2026 4, retarget.py, spine.py 2025 10, spine_compose.py, f8_tail_attribution.py, fit_contract.py replay, native_laws.py replay, classe.py, h7.py validate.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33440 (5840 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 7 - REFUSED AND RESTORED - Oct 5 2026 (attempt 7 registration above; snapshot /tmp/slate_pass)
Layers 1 and 2 PASS.  Layer 3: dstick 2026 4 (2 same), ystick 2026 4 (same), retarget exit 0 in 234 s - r_report same, r_families.csv header differs: se vs standard_error.
   Cause, an instrument defect: a bare fragment word as a column was renamed through the keyword and attribute roles (PART se -> standard_error) but kept in the string
   role (the header map); one column, two outcomes.  Refused as registered; restored.
Fix before attempt 8: a bare word in any column role (string, attribute, keyword) keeps its spelling in this pass - bare data names go to the column pass; library
   string arguments (agg "std") make the string role unsafe to rename.  Variables keep their renames.
## ONE FULL RENAME PASS - ATTEMPT 8 - REGISTRATION - Oct 5 2026 (rename_pass.py 3b0841910aa1a090; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: a bare fragment word in any column role (string, attribute, keyword) keeps its spelling in this pass (attempt 7: keyword se renamed, header se kept); bare data names go to the column pass.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33439 (5840 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 8 - REFUSED AND RESTORED - Oct 5 2026 (attempt 8 registration above; applied state kept at /tmp/slate_applied_8: all code, 13 changed facts/proj files)
   Layers 1 and 2 PASS.  Layer 3: dstick 2026 4 and ystick 2026 4 same; retarget exit 0 in 279 s - r_report same, r_families.csv header se vs standard_error; the attempt 8 keyword fix
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 9 - REGISTRATION - Oct 5 2026 (rename_pass.py 3b0841910aa1a090; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: attempts 7-8 refused on a stale artifact (r_families.csv header se written by an older retarget.py; the current code writes std_err, renamed standard_error); the gate baseline is now regenerated from the current code before the snapshot.  Baseline: every producer rerun with the original code first; regenerated 3 stale artifacts: proj/fit_contract_manifest.csv, proj/fit_contract_replay_report.txt, proj/r_families.csv.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33439 (5840 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 9 - REFUSED AND RESTORED - Oct 5 2026 (attempt 9 registration above; applied state kept at /tmp/slate_applied_9: all code, 14 changed facts/proj files)
   spine_compose.py exit 1, 2 s
   spine_compose.py (floor-free, corrected verdict table)  tests [2021, 2023, 2024, 2025]; draws 2000; rows RB 5055, WR 8661, TE 5283, QB 1895 (all seasons)
   Traceback (most recent call last):
     File "/Users/cameroncatri/LocalWork/slate_kit/spine_compose.py", line 318, in <module>
       season_fit = fit_state(compose_inputs, s); fitted_states[s] = season_fit; support_params = {}
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/Users/cameroncatri/LocalWork/slate_kit/native_laws.py", line 92, in fit_state
       position_params["receptions_per_target"] = float(to_counts(train_rows.y_rec).sum() / to_counts(train_rows.y_tgt).sum())
                                                                                                      ^^^^^^^^^^^^^^^^
     File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pandas/core/generic.py", line 6321, in __getattr__
       return object.__getattribute__(self, name)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   AttributeError: 'DataFrame' object has no attribute 'y_tgt'. Did you mean: 'y_td'?
   LAYER 4 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 10 - REGISTRATION - Oct 5 2026 (rename_pass.py 4b633531c7d094ba; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: names some code builds in pieces (literal piece joined with _, not itself renamed: y_/m_/s_ + stem, c + _pb/_tb, own_abs_ + t, team_ + c) keep their spelling in column roles until the column pass; derived from code, written to /tmp/slate_keep_composed.txt for the gate.  Baseline: every producer rerun with the original code first; regenerated 0 stale artifacts: none.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33209 (5762 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 10 - REFUSED AND RESTORED - Oct 5 2026 (attempt 10 registration above; applied state kept at /tmp/slate_applied_10: all code, 10 changed facts/proj files)
   avail.py exit 0, 5 s
      avail.py wrote 2 files under facts/ and proj/
      same  proj/avail_report.txt  (avail.py)
      same  proj/avail_rows.csv.gz  (avail.py)
   GATE PASS
   at_t.py exit 0, 3 s
      at_t.py wrote 2 files under facts/ and proj/
      same  proj/at_t_report.txt  (at_t.py) - 6 renamed lines differ only in padding
      DIFFERENT proj/at_t_rows.csv.gz (at_t.py) line 0:
         mapped snapshot: player_id,season,week,position,team,probability_absent_tier,probability_absent_calibrated,did_not_play,games_missed,snap_tier_season_pregame,snap_share_mean_
         new:             player_id,season,week,position,team,probability_absent_tier,probability_absent_calibrated,did_not_play,games_missed,snap_tier_season_pregame,snap_share_mean_
   GATE REFUSED: 1 files
   LAYER 2 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 11 - REGISTRATION - Oct 5 2026 (rename_pass.py d288b8b504566fa4; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: canon_plan follows the column-role rules (string role; names built in pieces not added from EX), so plain() renames judged columns exactly as the gate maps them (attempt 10: at_t_rows games_before).
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33209 (5762 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 11 - REFUSED AND RESTORED - Oct 5 2026 (attempt 11 registration above; applied state kept at /tmp/slate_applied_11: all code, 10 changed facts/proj files)
   dstick.py 2026 4 exit 1, 10 s
   Traceback (most recent call last):
     File "/Users/cameroncatri/LocalWork/slate_kit/dstick.py", line 25, in <module>
       defense_raw = rt.defense_targets.copy(); defense_rows = defense_raw.dropna(subset=["dst_points", "team_dst_points_mean_season_pregame", "games_before"] + OPPF).reset_index(drop
                                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pandas/core/frame.py", line 6692, in dropna
       raise KeyError(np.array(subset)[check].tolist())
   KeyError: ['games_before']
   LAYER 3 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 12 - REGISTRATION - Oct 5 2026 (rename_pass.py a28c7f7bbefc4fb6; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: the kept-set check comes after explicit per-file entries (attempt 11: dstick games_before); spine_f2 c + _before reviewed as a false match (c in targets, carries, attempts), so games_before follows the table again.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33214 (5764 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 12 - REFUSED AND RESTORED - Oct 5 2026 (attempt 12 registration above; applied state kept at /tmp/slate_applied_12: all code, 25 changed facts/proj files)
   fit_contract.py replay exit 1, 2 s
   fit_contract.py replay - contract v1; producers: proj/spine_rows.csv.gz 7b939592aebe1a15; freeze.py f423d20ad635df0b; p.py 1175a2f04c58482c; fit_contract.py 5eca3ead9fc7f00e
      wr_receiving_yards_scale: held-out rows 6954, cutoffs [2021, 2023, 2024, 2025]; rows payload IDENTICAL; params text DIFFERS
         params first difference line 0: replay season,alpha,beta,live_standard_deviation,train_rows,test_rows | recorded season,alpha,beta,live_sd,train_rows,test_rows
      wr_receiving_yards_scale_spline: held-out rows 6954, cutoffs [2021, 2023, 2024, 2025]; rows payload IDENTICAL; params text DIFFERS
         params first difference line 0: replay season,knot1_u,knot2_u,knot3_u,theta0,theta1,theta2,theta3,theta4,live_standard_deviation,train_rows,test_rows | recorded season,knot1_
      te_receiving_yards_location: held-out rows 4235, cutoffs [2021, 2023, 2024, 2025]; rows payload IDENTICAL; params text IDENTICAL
   REPLAY REFUSED - see above; nothing rescued
   LAYER 5 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 14 - REGISTRATION - Oct 5 2026 (rename_pass.py d822a6ebd31d9f9c; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: fit_contract's replay compares against historical f6 params records whose producers refuse under the current code (f6_wr_receiving_yards_scale: live yards forms differ); the replay keeps the recorded column name live_sd; those producers are not layers.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33212 (5763 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 14 - REFUSED AND RESTORED - Oct 5 2026 (attempt 14 registration above; applied state kept at /tmp/slate_applied_14: all code, 25 changed facts/proj files)
   fit_contract.py replay exit 0, 1 s
      fit_contract.py wrote 2 files under facts/ and proj/
      DIFFERENT proj/fit_contract_manifest.csv (fit_contract.py) line 1:
         mapped snapshot: wr_receiving_yards_scale,2021,1707,1704,7bdfabb55bd17f25f9efdbb5959331b8b27125b2574c712d7f173469592aac26,[2.7861992360158383, 0.1644671119575046, 31.69243583
         new:             wr_receiving_yards_scale,2021,1707,1704,7bdfabb55bd17f25f9efdbb5959331b8b27125b2574c712d7f173469592aac26,[2.7861992360158383, 0.1644671119575046, 31.69243583
      DIFFERENT proj/fit_contract_replay_report.txt (fit_contract.py) line 0:
         mapped snapshot: fit_contract.py replay - contract v1; producers: proj/spine_rows.csv.gz 7b939592aebe1a15; freeze.py 415a378da9f5edbf; p.py 45d16a1a3782a769; fit_contract.py 
         new:             fit_contract.py replay - contract v1; producers: proj/spine_rows.csv.gz 7b939592aebe1a15; freeze.py f423d20ad635df0b; p.py 1175a2f04c58482c; fit_contract.py 
   GATE REFUSED: 2 files
   LAYER 5 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 15 - REGISTRATION - Oct 5 2026 (rename_pass.py a1f6251fc8f90f7e; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: the gate maps code-file hashes (snapshot sha256 -> applied sha256, full and 16-character) before comparing: fit_contract's report and manifest fingerprint their producers' code (attempt 14); f6_wr_receiving_yards_scale_report.txt restored from the baseline copy after the refused baseline run overwrote it.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33212 (5763 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 15 - REFUSED AND RESTORED - Oct 5 2026 (attempt 15 registration above; applied state kept at /tmp/slate_applied_15: all code, 25 changed facts/proj files)
      witness zero-history (m, r): 47 component-seasons, differing none
   Traceback (most recent call last):
     File "/Users/cameroncatri/LocalWork/slate_kit/native_laws.py", line 218, in <module>
       hurdle_rows = read_table(os.path.join(output_dir, "f6_zero_history_hurdle_rows.csv.gz"))[["term", "position", "season", "probability_nonzero", "m_pos", "positive_part_negative_
                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pandas/core/frame.py", line 4119, in __getitem__
       indexer = self.columns._get_indexer_strict(key, "columns")[1]
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pandas/core/indexes/base.py", line 6212, in _get_indexer_strict
       self._raise_if_missing(keyarr, indexer, axis_name)
     File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pandas/core/indexes/base.py", line 6264, in _raise_if_missing
       raise KeyError(f"{not_found} not in index")
   KeyError: "['probability_nonzero', 'positive_part_negative_binomial_size'] not in index"
   LAYER 5 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 16 - REGISTRATION - Oct 5 2026 (rename_pass.py a92738a36e70c75e; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: every direct read of a recorded CSV under proj/ or facts/ (not judged) gets .rename(columns=...) from its recorded header through the reader's table, applied after renaming: historical records keep their names, readers see their own, live files are untouched (attempt 15: native_laws read f6_zero_history_hurdle_rows pi / r_pos).
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33212 (5763 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 16 - REFUSED AND RESTORED - Oct 5 2026 (attempt 16 registration above; applied state kept at /tmp/slate_applied_16: all code, 25 changed facts/proj files)
      same  proj/fit_contract_manifest.csv  (fit_contract.py)
      same  proj/fit_contract_replay_report.txt  (fit_contract.py)
   GATE PASS
   native_laws.py replay exit 1, 9 s
   native_laws.py replay (A2') - tests [2021, 2023, 2024, 2025]; zero-history PASS [('F5 TDs', 'TE'), ('F5 TDs', 'WR'), ('F5 receptions', 'TE'), ('Q4 passing TDs', 'QB'), ('QB rushing
      law rows: 109562 rows x 27 columns; differing columns none
      season fits: A1 108, A2' 108 -> IDENTICAL
      witness zero-history (m, r): 47 component-seasons, differing none
   Traceback (most recent call last):
     File "/Users/cameroncatri/LocalWork/slate_kit/native_laws.py", line 219, in <module>
       hbad = [(term_name, p, loop_season) for term_name, p, loop_season, event_prob, second_param, third_param in hurdle_rows.itertuples(index=False) if state_fits.get(loop_season) i
                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   ValueError: too many values to unpack (expected 6)
   LAYER 5 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 17 - REGISTRATION - Oct 5 2026 (rename_pass.py 4a3dafaf7362e579; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: a header map that sends two recorded columns to one name collapses them only when the recorded values are identical (checked from the file at pass time), else flags (attempt 16: f6_zero_history_hurdle_rows pi and p_event, written equal).
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33212 (5763 distinct); line edits 46, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 17 - REFUSED AND RESTORED - Oct 5 2026 (attempt 17 registration above; applied state kept at /tmp/slate_applied_17: all code, 27 changed facts/proj files)
   classe.py exit 0, 5 s
      classe.py wrote 1 files under facts/ and proj/
      DIFFERENT proj/study_classe.txt (classe.py) line 35:
         mapped snapshot:       probability_absent_logistic: calibration fail 48.0% vs null 95th 10.0% over 50 subgroups -> STRUCTURAL;  log-loss 0.2926
         new:                   probability_absent_logistic: calibration fail 48.0% vs null 95th 14.0% over 50 subgroups -> STRUCTURAL;  log-loss 0.2926
   GATE REFUSED: 1 files
   LAYER 6 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 18 - REGISTRATION - Oct 5 2026 (rename_pass.py 0607fb02b562d3a5; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: names only, outputs unchanged (owner): classe.py:77 seeds its null with len(column name); the seed keeps each name's recorded length (attempt 17: null 95th 10.0% vs 14.0%).
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33218 (5763 distinct); line edits 47, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 18 - REFUSED AND RESTORED - Oct 5 2026 (attempt 18 registration above; applied state kept at /tmp/slate_applied_18: all code, 27 changed facts/proj files)
   classe.py exit 0, 5 s
      classe.py wrote 1 files under facts/ and proj/
      same  proj/study_classe.txt  (classe.py)
   GATE PASS
   h7.py validate exit 1, 0 s
   Traceback (most recent call last):
     File "/Users/cameroncatri/LocalWork/slate_kit/h7.py", line 65, in <module>
       train, test = model_rows[model_rows.season < s], model_rows[model_rows.season == s].copy(); test["p1"], _ = at_module["at_fit"](train, test); result_frames.append(test[join_key
                                                                                                                   ~~~~~~~~~^^^^^^^^^^
   KeyError: 'at_fit'
   LAYER 6 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 19 - REGISTRATION - Oct 5 2026 (rename_pass.py 781b57315dc2a0fd; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: h7_exec loads at_t.py and score_t.py definitions by name: h7's literals naming those definitions follow the definer's rename (attempt 18: at_fit -> fit_tiers, M -> prior_strength); conflicts flagged.
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33217 (5762 distinct); line edits 56, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 19 - REFUSED AND RESTORED - Oct 5 2026 (attempt 19 registration above; applied state kept at /tmp/slate_applied_19: all code, 27 changed facts/proj files)
   h7.py validate exit 1, 0 s
   V1 T1 walk-forward via at_t's own at_pool: rows 20764, max |diff| 1.11e-16 (CSV round-trip tolerance 1e-12) -> PASS
   Traceback (most recent call last):
     File "/Users/cameroncatri/LocalWork/slate_kit/h7.py", line 68, in <module>
       live_inputs = h7_inputs([2024, 2025], range(4, 17)).merge(model_rows[join_keys + ["games_missed", "snap_tier_season_pregame"]], on=join_keys, suffixes=("", "_at"))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/Users/cameroncatri/LocalWork/slate_kit/h7.py", line 29, in h7_inputs
       absence_rows = h7_exec("score_t.py", {"st_new_absences"}, return_statement)["st_new_absences"](seasons, weeks)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/Users/cameroncatri/LocalWork/slate_kit/h7.py", line 22, in h7_exec
       if return_source: assert source_text.count(return_source[0]) == 1, f"{path}: expected line changed - stopping"; source_text = source_text.replace(return_source[0], return_sourc
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   AssertionError: score_t.py: expected line changed - stopping
   LAYER 6 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 20 - REGISTRATION - Oct 5 2026 (rename_pass.py dc0c69596be39edd; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: h7.py copies score_t.py line 35 as text (RET) for h7_exec's exact replace: the copied line and its replacement follow score_t.py's own rewrite (attempt 19: expected line changed).
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33216 (5762 distinct); line edits 58, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - ATTEMPT 20 - REFUSED AND RESTORED - Oct 5 2026 (attempt 20 registration above; applied state kept at /tmp/slate_applied_20: all code, 27 changed facts/proj files)
      classe.py wrote 1 files under facts/ and proj/
      same  proj/study_classe.txt  (classe.py)
   GATE PASS
   h7.py validate exit 1, 0 s
   V1 T1 walk-forward via at_t's own at_pool: rows 20764, max |diff| 1.11e-16 (CSV round-trip tolerance 1e-12) -> PASS
   Traceback (most recent call last):
     File "/Users/cameroncatri/LocalWork/slate_kit/h7.py", line 69, in <module>
       match_rate = float(((live_inputs.games_missed == live_inputs.games_missed_at) & (live_inputs.snap_tier_season_pregame == live_inputs.snap_state_at)).mean()); report_line(f"   V
                                                                                                                                ^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pandas/core/generic.py", line 6321, in __getattr__
       return object.__getattribute__(self, name)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   AttributeError: 'DataFrame' object has no attribute 'snap_state_at'. Did you mean: 'snap_state_label'?
   LAYER 6 REFUSED - run AR
   Restored and verified against the snapshot.
## ONE FULL RENAME PASS - ATTEMPT 21 - REGISTRATION - Oct 5 2026 (rename_pass.py 35900c7e577df428; short table 62ed2dbcb01c066a; TAXONOMY.md b7cc35a5e2f7a693; snapshot /tmp/slate_pass)
As the previous attempt, plus: names assembled by a file's own merge suffixes (suffixes=(..., '_at')) follow their renamed base (attempt 20: h7 snap_state_at -> snap_tier_season_pregame_at).
   Layers and gate as registered for attempt 4.  Dry run: files changed 107; token changes 33217 (5763 distinct); line edits 58, not matching their expected count 0 | flags 0; collisions 0; new duplicate strings 0; cross-module breaks 0; canon SRC missing 0; compile failures 0.
## ONE FULL RENAME PASS - OUTCOME - Oct 5 2026 (attempt 21 applied; registrations and refusals 1-20 above)
Applied: 107 files and canon.py tables; 33217 token changes, 58 line edits; dry run clean (0 flags, collisions, duplicates, cross-module breaks, canon SRC misses, compile failures).
Gate (baseline regenerated from the current code before the snapshot; outputs equal after the table's own name map): layer 1 facts p a j 12 same; layer 2 avail at_t 4 same;
   layer 3 dstick 2026 4, ystick 2026 4, retarget 5 same; layer 4 spine 2025 10, spine_compose, f8_tail_attribution 35 same; layer 5 fit_contract replay, native_laws replay
   3 same; layer 6 classe 1 same, h7 validate V1 PASS and V2 PASS (printed, no file).  60 outputs identical; no number changed.
Scope: variables, parameters, functions and table-mapped names.  Kept for the DATA pass: bare and short column names, names built in pieces (/tmp/slate_keep_composed.txt),
   historical-record columns (f6_*_params live_sd), snap_tier_u / snap_tier_tr.  Stale artifacts regenerated by the baseline: r_families.csv, fit_contract_manifest.csv,
   fit_contract_replay_report.txt.  Rules learned are in the name inventory (roles 1-20).  Snapshot, applied states and baseline copy deleted after this entry.
## S1 CODE-NAME COLLAPSE - ATTEMPT 22 - REGISTRATION - Oct 5 2026
   S1 code-name collapse, scoped AST renames of identifiers only (strings, dict keys, attributes, data untouched): train_rows->train, test_rows->test; boolean masks in retarget.py and f6_root1_owner_map.py:46-51 -> train_mask / test_mask; a value tried in a grid search takes the grid's quantity name (shrinkage_strength / td_rate_strength / rate_strength), replacing shrink_strength, group_key (adjudicate, regime_test, zero_test strength sites), kalman_gain (contexts.py:109), rate_candidate, candidate_strength; contexts.py chosen TD-rate strength shrinkage_strength->td_rate_strength; h7.py snap_tier_u->state_rates, snap_tier_tr->row_rates, cells comprehension a->band_label, band_key->state_label. Gate: every layer re-run; facts/ and proj/ byte-identical (gz decompressed; touched code-file sha256 mapped). Owner ruling, same day: recorded and historical CSV headers are rewritten to the one spelling, values untouched, hashes re-recorded; header_wrap bridging retires in the DATA pass.
## S1 CODE-NAME COLLAPSE - ATTEMPT 22 - OUTCOME - Oct 5 2026
   Applied: 57 files, 1594 identifier changes. Every layer re-run; facts/ and proj/ byte-identical (gz decompressed, code-file sha256 mapped); h7 no FAIL. Snapshot /tmp/slate_s1_before.
## DATA NAME COLLAPSE - ATTEMPT 23 - REGISTRATION - Oct 5 2026
   DATA NAME COLLAPSE - one plain name per meaning for column, record-field and table-key spellings. Table /tmp/slate_data_names.tsv (sha256 bac89e9578068765); 94 code files, 3328 edits; 72 CSV headers rewritten under the Oct 5 owner ruling (values untouched; identical duplicates dropped). Strings used as values left untouched. Gate: every runnable touched script and every layer run in two sandbox copies (before / after); facts/ and proj/ equal after the header map; text equal token by token after the name map.
## DATA NAME COLLAPSE - ATTEMPT 23 - REFUSED - Oct 5 2026
   facts.py: renamed code exits 1:   File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pandas/core/generic.py", line 6321, in __getattr__ |     return object.__getattribute__(self, name) |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | AttributeError: 'DataFrame' object has no attribute 'position'. Live repo untouched. Unverifiable (current code exits non-zero): [].
## DATA NAME COLLAPSE - ATTEMPT 24 - REGISTRATION - Oct 5 2026
   DATA NAME COLLAPSE - one plain name per meaning for column, record-field and table-key spellings. Table /tmp/slate_data_names.tsv (sha256 edcae8a32a47eb68); 94 code files, 3318 edits; 72 CSV headers rewritten under the Oct 5 owner ruling (values untouched; identical duplicates dropped). Strings used as values left untouched. Gate: every runnable touched script and every layer run in two sandbox copies (before / after); facts/ and proj/ equal after the header map; text equal token by token after the name map.
## DATA NAME COLLAPSE - ATTEMPT 24 - REFUSED - Oct 5 2026
   a.py: renamed code exits 1: ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | File "/private/tmp/slate_d_after/a.py", line 30, in predict | matched_probs = test[keys].merge(level_groups[keys + ["pooled_probability"]], on=keys, how="left").pooled_probability.values; p = np.where(np.isnan(matched_probs), p, matched_probs) | ~~~~^^^^^^ | indexer = self.columns._get_indexer_strict(key, "columns")[1] | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | self._raise_if_missing(keyarr, indexer, axis_name) | raise KeyError(f"{not_found} not in index") | KeyError: "['pooled_probability', 'row_count'] not in index". Live repo untouched. Unverifiable (current code exits non-zero): [].
## DATA NAME COLLAPSE - ATTEMPT 25 - REGISTRATION - Oct 5 2026
   DATA NAME COLLAPSE - one plain name per meaning for column, record-field and table-key spellings. Table /tmp/slate_data_names.tsv (sha256 edcae8a32a47eb68); 94 code files, 3318 edits; 72 CSV headers rewritten under the Oct 5 owner ruling (values untouched; identical duplicates dropped). Strings used as values left untouched. Gate: every runnable touched script and every layer run in two sandbox copies (before / after); facts/ and proj/ equal after the header map; text equal token by token after the name map.
## DATA NAME COLLAPSE - ATTEMPT 25 - REFUSED - Oct 5 2026
   a.py: renamed code exits 1: ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | File "/private/tmp/slate_d_after/a.py", line 30, in predict | matched_probs = test[keys].merge(level_groups[keys + ["pooled_probability"]], on=keys, how="left").pooled_probability.values; p = np.where(np.isnan(matched_probs), p, matched_probs) | ~~~~^^^^^^ | indexer = self.columns._get_indexer_strict(key, "columns")[1] | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | self._raise_if_missing(keyarr, indexer, axis_name) | raise KeyError(f"{not_found} not in index") | KeyError: "['pooled_probability', 'row_count'] not in index". Live repo untouched. Unverifiable (current code exits non-zero): [].
## DATA NAME COLLAPSE - ATTEMPT 26 - REGISTRATION - Oct 5 2026
   DATA NAME COLLAPSE - one plain name per meaning for column, record-field and table-key spellings. Table /tmp/slate_data_names.tsv (sha256 edcae8a32a47eb68); 94 code files, 3320 edits; 72 CSV headers rewritten under the Oct 5 owner ruling (values untouched; identical duplicates dropped). Strings used as values left untouched. Gate: every runnable touched script and every layer run in two sandbox copies (before / after); facts/ and proj/ equal after the header map; text equal token by token after the name map.
## DATA NAME COLLAPSE - ATTEMPT 26 - REFUSED - Oct 5 2026
   avail.py: renamed code exits 1: File "/private/tmp/slate_d_after/avail.py", line 32, in <module> | candidate_rows = candidate_rows.sort_values(key_columns + ["team"], kind="stable").drop_duplicates(key_columns).merge(team_games[["season", "team", "week", "team_game_no"]], on=["season", "team", "week"], how="left") | ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | indexer = self.columns._get_indexer_strict(key, "columns")[1] | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | self._raise_if_missing(keyarr, indexer, axis_name) | raise KeyError(f"{not_found} not in index") | KeyError: "['team_game_no'] not in index". Live repo untouched. Unverifiable (current code exits non-zero): [].
## DATA NAME COLLAPSE - ATTEMPT 27 - REGISTRATION - Oct 5 2026
   DATA NAME COLLAPSE - one plain name per meaning for column, record-field and table-key spellings. Table /tmp/slate_data_names.tsv (sha256 edcae8a32a47eb68); 97 code files, 3407 edits; 72 CSV headers rewritten under the Oct 5 owner ruling (values untouched; identical duplicates dropped). Strings used as values left untouched. Gate: every runnable touched script and every layer run in two sandbox copies (before / after); facts/ and proj/ equal after the header map; text equal token by token after the name map.
## DATA NAME COLLAPSE - ATTEMPT 27 - REFUSED - Oct 5 2026
   at_t.py: 1 outputs differ. Live repo untouched. Unverifiable (current code exits non-zero): [].
## DATA NAME COLLAPSE - ATTEMPT 28 - REGISTRATION - Oct 5 2026
   DATA NAME COLLAPSE - one plain name per meaning for column, record-field and table-key spellings. Table /tmp/slate_data_names.tsv (sha256 f19c0f7f20f9f99f); 97 code files, 3441 edits; 77 CSV headers rewritten under the Oct 5 owner ruling (values untouched; identical duplicates dropped). Strings used as values left untouched. Gate: every runnable touched script and every layer run in two sandbox copies (before / after); facts/ and proj/ equal after the header map; text equal token by token after the name map.
## DATA NAME COLLAPSE - ATTEMPT 28 - REFUSED - Oct 5 2026
   dstick.py 2026 4: renamed code exits 1: File "/private/tmp/slate_d_after/dstick.py", line 25, in <module> | defense_raw = rt.defense_targets.copy(); defense_rows = defense_raw.dropna(subset=["dst_points", "team_dst_points_mean_season_pregame", "team_games_season_pregame"] + OPPF).reset_index(drop=True) | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | raise KeyError(np.array(subset)[check].tolist()) | KeyError: ['opponent_offense_pts_for_mean_season_pregame']. Live repo untouched. Unverifiable (current code exits non-zero): [].
## DATA NAME COLLAPSE - ATTEMPT 29 - REGISTRATION - Oct 5 2026
   DATA NAME COLLAPSE - one plain name per meaning for column, record-field and table-key spellings. Table /tmp/slate_data_names.tsv (sha256 f19c0f7f20f9f99f); 97 code files, 3447 edits; 77 CSV headers rewritten under the Oct 5 owner ruling (values untouched; identical duplicates dropped). Strings used as values left untouched. Gate: every runnable touched script and every layer run in two sandbox copies (before / after); facts/ and proj/ equal after the header map; text equal token by token after the name map.
## STANDALONE DATA RENAME CLOSED - NAMES MOVE WITH THEIR SSOT - Oct 5 2026
   Owner (Oct 5): the standalone data rename (D1 table; 97 files, 3,447 edits; attempts 23-28 refused; never applied) is closed - a name is canonicalized when its concept's producer moves into its SSOT. Attempt 22 identifier rename stays applied. Probe (90 scripts, both copies): renamed code fails 28 (7 classes); current code fails 34, 6 time out. Current-code failures by sub-root: calibration 9 (adjudicate, regime_test, zero_test .mad; f6_q1_dispersion, f6_zero_history x5 .rank); source-text witnesses 12 (l freeze, chain, atlas, f6_root1_owner_map x4, receiving-yards forms x5) plus score_y / score_d validate; shrinkage reads 3 (spine_qb_rush2, spine_td kb; spine_qb_shr kr); F8 evaluation 1 (f8_vs_y f8_pit); dependence 1 (jexpose); display 1 (card.py 2026 4 KeyError S EXP). Live chain with arguments: s.py 2026 4 exit 0 (expected 141.7; MC p10 110.5 p50 139.2 p90 171.0), dk_classic 2026 4 exit 0, score_s and score_t validate pass. L freeze refuses: s, l, p, a, j, facts, names, lineups9, p_coef.json, a_cells.json changed since 2026-10-02. Gate defect: a current-code failure counted as unverifiable, which hid these. Repo has no .git.
## SSOT REORGANIZATION - TWELVE-MODULE MAP, FIRST TRANSACTIONS - OUTCOME - Oct 5 2026 (owner: ruthless reorganization to the Oct 5 handoff's module map; one definition per name)
The 112 scripts collapse into ingest, facts, state, evaluate, laws, dk, dependence, draws, optimize and the kit.py command (MODULES order: each imports only earlier
   modules).  Moved producers reproduced their recorded outputs on the owner's machine: facts tables identical (decompressed); spine rows and sufficient statistics
   identical (read-only, D3); 20 of 20 recorded wall figures; spine week file 2025 w10 identical; native_laws replay exact (109562 x 27; 108 season fits; witnesses);
   fit contract replay identical (3 targets); F7 self-check; purity 0 cells.  guard.py, ledger.py and canon's battery are replaced by kit.py guard: raw manifest, one
   raw reader, kit modules only, one definition per name (AST), facts' independent check, facts freshness, information set, CHARTER ledger, purity.
Deleted without archive (owner rule): every script outside the module map, including the f6 / spine wall witnesses, one-off measurements, the DK track (p model, a, j, s,
   l, card, dk_classic, score_*), spine_compose.py and fit manifests' source-text hashes.  dstick.py, h7.py, register.py and ystick.py were recorded files whose copies were
   to stay until the 2026 cycle ended; their deletion is legitimate only because that cycle was withdrawn (owner ban on 2026 weeks >= 4).  Every recorded output in proj/
   and facts/ is untouched.  The L freeze and guard check 9 retire with s.py / l.py (R2); guard checks 7, 8 and 11 retire with their subjects.
## CASCADE PRIORITY 1 - B1b-2 (M1) - WEEK-MODE LAW ROWS - OUTCOME - Oct 5 2026 (laws.issue_inputs / week_law_rows; issue path under previous-team-game routing)
ACCEPTED.  Issue path at 2025 w10 (spine choices and law parameters fit on seasons < 2025) against the recorded law rows of that week: paired 1987, 0 differing in 21
   columns (5 discrete exact, 16 numeric within 16 eps); unmatched rows all named - played, not a candidate 13 rows / 2 players (root B); candidate that did not play 418
   / 61; team change 18 / 3 (00-0034960, 00-0037545, 00-0037614: candidate team = previous team-game team); position routing 17 / 1 (00-0038488, recorded root A).
   The week-file writer and its term -> column map retire; the issue path compares row by row through term_rows.
## M2 - KEYED NATIVE SAMPLER - OUTCOME - Oct 5 2026 (draws.py, dependence.py; acceptance at the law-parameter level, cascade-priority-1 registration)
ACCEPTED on tests 2021, 2023-25.  2000 draws per final law row from keyed per-row substreams (work order 19 and 20 (a) key strings reused; every other row "native draw");
   conditioned laws from their parent's draws; earned orders L1 / L2 / L3 (RB, WR) and wall 9 (TE, rows hash verified).  Witness rows (hurdle 2809, work order 20 (a)
   6749): 9558 rows identical on mean, CRPS, 80% coverage and bias.  Moments 37 of 37 groups |z| < 4 (largest 2.2).  Isolation 0 of 100 differ.  Wall 9 rho from the
   recorded composed PITs of earlier seasons: .1911 / .1761 / .1731 reproduced; 2026 uses .1767.  F8 coverage within ~0.003 of the recorded 27a bands (reading).
## CASCADE PRIORITY 1 - B POSITION RULE - IMPLEMENTATION - REGISTRATION - Oct 5 2026 (state.route_rule_b; the rule as registered Oct 4, no new mapping)
The issue path routes every candidate by rule (b); UNRESOLVED POSITION candidates are counted, not routed.  Witness per issue: proj/position_routing_SEASON_wWEEK.csv
   (previous label, earlier played-label sequence, routed position, differs flag).  kit.py issue-check re-runs M1 at 2025 w10 under the rule; unmatched rows keep their
   named reasons.  History law keys are unchanged.
## M3 - SERVE-AS-IF CALIBRATION ATLAS - REGISTRATION - Oct 5 2026 (draws.serve_as_if_replay, evaluate.atlas_cells; registered before the first run)
Replay: tests 2021, 2023-25, weeks 4-16; per week the production path (candidates through week N-1, rule (b), spine choices and law parameters fit on seasons < the
   season, keyed draws, earned orders, F8).  Graded on played rows only (laws are given he plays); stat outcomes from the recorded spine, F8 from facts' dk_points; PIT
   randomized from each row's keyed generator.  Cell = term x routed position x law state (F8: x composition form).  Product evaluation only: no verdict is re-judged; the
   replay is in-sample for seasons that selected the laws (R13).
Rule: fewer than 60 graded rows -> UNRESOLVED.  DECISION-QUALIFIED iff coverage (mean over slates of the share with PIT <= q) is within +-2 slate SE at every q in .10,
   .25, .75, .90 and the PIT decile deviation is at or below its noise 95th.  Otherwise NOT QUALIFIED, named from the q .10 / .90 bands: TOO NARROW (.10 too high and .90
   too low), TOO WIDE (.10 too low and .90 too high), CENTER TOO HIGH (either too high), CENTER TOO LOW (either too low), else MISCALIBRATED (shape).  Every issued
   cell is ISSUABLE; candidates without laws carry NOT ISSUED (fewer than 3 earlier played games on the team) or UNRESOLVED POSITION.  Y's benchmark is a later step.
## M3 - SERVE-AS-IF CALIBRATION ATLAS - OUTCOME - Oct 5 2026 (draws.serve_as_if_replay, evaluate.atlas_cells; run under the registration above)
RAN on tests 2021, 2023-25, weeks 4-16 under rule (b).  Candidates 24480: issued 19743, NOT ISSUED (fewer than 3 earlier played games) 3111, UNRESOLVED POSITION 1626;
   played and not issued 1766; rule (b) differs from the previous team-game label 100.  Graded 109439 played rows; 18151 did not play (not graded); 187 without an
   outcome row.  M1 stays ACCEPTED at 2025 w10 under rule (b) (position routing case 00-0039686); issue 2026 w4: 58 UNRESOLVED POSITION.
Cells: DECISION-QUALIFIED 8 (F5 touchdowns RB nonzero, TE nonzero, TE zero, WR zero; F5 carries RB zero; F5 receptions RB zero; F5 targets TE zero; Q5 interceptions QB
   zero).  NOT QUALIFIED: CENTER TOO LOW 17, TOO NARROW 8 (F5 carries / receptions / targets RB nonzero, F5 receptions TE, F8 QB, Q1, Q2, Q3), TOO WIDE 7, MISCALIBRATED 5,
   CENTER TOO HIGH 4 (F2 team targets among them).  UNRESOLVED (fewer than 60 rows) 2.  Every issued cell is ISSUABLE.
Named defects routed to the work order (no law changed here): (1) normal yards laws in law state zero draw continuous values around 0 while every outcome is exactly 0, so
   those cells grade TOO WIDE (PIT sd about .03-.15) - a law-family defect, not a sampler defect.  (2) TOO NARROW count and QB-chain cells - a dispersion root.
   (3) CENTER TOO LOW is the most common verdict (17 cells) - a center root.  Y benchmark: not yet run; ystick_rows has only p10 / p50 / p90 and a rounded
   outcome_percent, so outcome_percent is excluded as a test input and the benchmark scores Y's quantiles against facts' dk_points on the same played keys.
## M3 - SERVE-AS-IF CALIBRATION ATLAS - OUTCOME CORRECTION - Oct 5 2026 (corrects the outcome entry above; its lines stand as recorded)
TOO WIDE 7 = five zero-state yards cells (RB / WR receiving, RB / TE / WR rushing; PIT sd .031-.103) and two nonzero-state rushing yards cells (TE PIT sd .191, WR .212).
   Defect (1) as recorded covers the five; the two nonzero cells are a separate dispersion finding (receivers' rushing yards with rushing history), not the zero-state law.
## CASCADE PRIORITY 1 - B POSITION RULE - THE 391 RESOLVED - Oct 5 2026 (read: proj/atlas_coverage.csv, the M3 replay under rule (b))
The classification's open item ("rule (b) changes routing for 391 of 6149 candidates in weeks 4-16, cause unknown") is accounted for: 2025 weeks 4-16 candidates 6149 =
   UNRESOLVED POSITION 374 (no earlier played labelled game this season; never routed, no law issued) + label changes 17 (season-to-date mode differs from the previous
   team-game label).  Other seasons, same split: 2021 439 + 25 of 6166; 2023 406 + 23 of 6082; 2024 407 + 35 of 6083.  Nothing unexplained remains.
## M3 - Y BENCHMARK - READING - Oct 5 2026 (evaluate.y_benchmark inside kit.py atlas; frozen Y walk-forward rows vs served F8 on the same played player-weeks; no verdict)
Atlas rerun with stored quantiles: proj/atlas.csv and proj/atlas_coverage.csv identical to the M3 outcome run.  Paired 16597 of 16599 graded F8 player-weeks (Y walk-forward
   rows 22193; outcome_percent never read).  Gain = Y loss - F8 loss per slate, positive = F8 better.
Center absolute error: F8 better RB +.058 (4/4), WR +.023 (3/4), TE +.016 (4/4); Y better QB -.201 (0/4) - the recorded f8_vs_y pattern on the served engine.
Pinball, Y better at every level and position: q .10 RB -.144, WR -.169, TE -.058, QB -.107; q .50 RB -.036, WR -.081, TE -.045, QB -.089; q .90 RB -.052 (1/4), WR -.078,
   TE -.055, QB -.147 (0/4 where not noted).  Coverage q .10 / .90: F8 RB .091 / .874, WR .103 / .865, TE .050 / .874, QB .182 / .856; Y RB .194 / .901, WR .285 / .906,
   TE .384 / .900, QB .120 / .913.
Reading: at q .90 Y is calibrated and sharper - the served P90 defect is a native-engine root to diagnose, not a reason to revive Y (R1).  At q .10 F8 is calibrated in
   aggregate (RB, WR) yet scores worse than a miscalibrated Y: its lower quantile is placed worse row by row (resolution), not mis-sized overall.  QB: Y QB-v2 wins every
   score; F8 QB is TOO NARROW in the atlas.  Some paired TE rows carry Y model QB-v2 (Y's position label differs from rule (b)'s).
## M4 - PLAYER FORECAST CARD v1 (GIVEN HE PLAYS) - REGISTRATION - Oct 5 2026 (cards.py; draws.week_draws is the one producer for kit.py draws and the card)
The card is a reader: every field is a law (family, state, layer, provenance, conditioned_on_draw), a draw summary from draws (center = the law's own mean; for F8 the mean
   of the transform's draws, F8 having no law; quantile_10 ... quantile_90), an atlas cell (qualification, rows, coverage at q .10 / .90, bias) or a named status.  It
   computes no statistic.  Every row carries: conditioning "given he plays"; participation NOT ISSUED (M5); cross-player dependence NOT MODELLED (M9); DRY RUN.
ISSUABLE = a drawn law row.  DECISION-QUALIFIED only where the atlas cell (term x routed position x law state; F8 x order form) says so; a cell the atlas lacks reads
   "NO ATLAS CELL - not graded".  Team (F2) rows are not on the player card.
Coverage contract: every candidate once, one status - ISSUED; UNRESOLVED POSITION; NOT ISSUED with the first reason that holds (every law row drew nothing; week outside 4-16;
   fewer than 3 earlier played games on this team this season; team fewer than 3 earlier games this season); else NOT ISSUED - unexplained.  Accepted iff no unexplained
   candidate, statuses sum to the candidates, no issued candidate without stat rows and no stat row without a candidate.
## M4 - PLAYER FORECAST CARD v1 (GIVEN HE PLAYS) - OUTCOME - Oct 5 2026 (kit.py card 2026 4; DRY RUN)
ACCEPTED.  Candidates 517, each once: ISSUED 329 (2129 stat rows, F8 for all 329); NOT ISSUED - fewer than 3 earlier played games on this team this season 130; UNRESOLVED
   POSITION 58; unexplained 0.  Stat rows by atlas qualification: DECISION-QUALIFIED 240; CENTER TOO LOW 1077; TOO NARROW 382; TOO WIDE 268; MISCALIBRATED (shape) 122;
   CENTER TOO HIGH 40.  Every row labelled given he plays, participation NOT ISSUED (M5), cross-player dependence NOT MODELLED, DRY RUN.
Defect seen on the card, wider than M3 defect (1): normal yards laws in law state nonzero also issue negative P10 (RB rushing -13.1 at center 23.3; RB receiving -12.2 at
   9.3; QB rushing yards given carries -8.0 at 8.3), and F8 inherits it (TE F8 P10 -0.8 although F8 omits fumbles).  Hypothesis, not measured: F8's q .10 loss to Y
   (M3 Y benchmark) comes from these negative yard draws.  Measurement next: share of yards and F8 draws below 0 per cell.
## M4 - NEGATIVE P10 ON THE CARD - MEASURED - Oct 5 2026 (read: proj/card_2026_w4.csv; P10 per card, not per draw)
Cards with P10 < 0 (rows / negative / median P10): receiving yards RB nonzero 64 / 50 / -9.3, zero 13 / 13 / -19.9; TE nonzero 78 / 72 / -10.3, zero 12 / 12 / -7.1; WR
   nonzero 117 / 71 / -5.4, zero 19 / 19 / -37.9.  Rushing yards RB nonzero 67 / 33 / 0.5, zero 10 / 10 / -35.7; TE nonzero 5 / 5, zero 85 / 85; WR nonzero 23 / 23, zero
   113 / 113.  QB rushing yards given carries 26 / 15 / -2.1.  F8: RB 77 / 35, WR 136 / 60, TE 90 / 57 (median -0.6), QB 26 / 0.
Reading: the normal yards family (F6 v1 forms 2 / 3) puts mass below 0 for most skill cards in every state, and F8's lower tail inherits it for half the skill players;
   QB F8 is untouched.  Consistent with, not proof of, F8's q .10 loss to Y.  A law change needs a registered wall; R3 puts the forward promotion gate (R-gate) before any
   new marginal wall - this is the research lane's first target after the R-gate.  Production lane continues with M5.
## M5 - PARTICIPATION (T1, ONE PRODUCER) - REGISTRATION - Oct 5 2026 (kit.py participation-check; kit.py card 2026 4; DRY RUN)
Object: P(he plays | results through week N-1) for every skill candidate, from T1 as recorded (AT step 3, H7 cells): gap {0, 1, 2+} x role state {low < .35, mid < .70,
   high}, pooled rate = (plays + M x parent) / (rows + M), M = 10, an unseen cell takes its parent.  Inputs: state.participation_frame, the one producer that replaces the
   avail.py and score_t.py frames.  Domain: 3+ earlier played games this season (a WR: 1+), every input defined, weeks 4-16; a row outside it is NOT ISSUED with its
   named reason.  Fit and walk-forward: participation.py (at_t.py's at_pool / fit_tiers T1 path and h7.py's h7_cells / play_probability, ported line for line).
Acceptance (all four, fixed before running): W1 every recorded at_rows row is in the frame, in domain, with games_missed, role tier and played equal; W2 the walk-forward
   on those rows equals at_t_rows probability_plays_transition_walkforward, every row paired, max |diff| < 1e-12; W3 the fit on those rows equals t1_cells.json (base,
   role-state rates and cells < 1e-12; M, rows and seasons equal); W4 at 2021 w9, 2024 w9 and 2025 w15 the frame built from results through week N-1 equals the full
   build (inputs, grid, domain reason), 0 differences.
Not re-judged: AT step 3's recorded T1 walk-forward FAIL stands.  On the card T1 is ISSUED - NOT DECISION-QUALIFIED.  P(plays) stands beside the given-he-plays laws and
   is never multiplied into them; the mixture is a later transaction, registered separately.
Card fit: T1 cells refit on every in-domain frame row of seasons 2020 .. min(FROZEN_THRU, issue season - 1), weeks 4-16.  The check prints that fit's rows, seasons and
   largest distance to the recorded cells.  In-domain frame rows that at_rows lacks are a finding for the work order, not settled here.
## M5 - PARTICIPATION (T1, ONE PRODUCER) - OUTCOME - Oct 5 2026 (kit.py participation-check; kit.py card 2026 4; DRY RUN)
ACCEPTED.  W1: the 26003 recorded at_rows rows (seasons 2020, 2021, 2023, 2024, 2025) are all in the frame and in domain; games_missed, role tier and played differ 0;
   in-domain frame rows weeks 4-16 not in at_rows 0.  W2: walk-forward 20764 rows, unpaired 0, max |diff| 0.  W3: full fit rows 26003, seasons equal, M 10, base,
   role-state rates and cells max |diff| 0.  W4: 2021 w9 (449 candidates), 2024 w9 (477), 2025 w15 (517), 0 cells differ.  The card fit equals the recorded cells
   (max distance 0); the registration's open point does not arise, because the frame has no in-domain 2022 row.
Card 2026 w4: participation ISSUED - NOT DECISION-QUALIFIED 379; NOT ISSUED - fewer than 3 earlier played games (a WR: none) 80; NOT ISSUED - no earlier played game
   this season 58 (the 58 UNRESOLVED POSITION).  All 329 stat-ISSUED candidates carry P(plays), mean .897.  Stat statuses and atlas counts unchanged from M4.
Finding (to M6): two short-history rules.  Stat coverage needs 3 earlier played games on this team (no WR exception); participation needs 3 this season (a WR: 1+).
   379 - 329 = 50 candidates carry P(plays) without stat laws.  Which of the 130 they are is not measured.
Finding (work order): the participation frame has no in-domain 2022 row (at_rows lacked 2022 as well); the cause is not measured.
## M6a - ISSUE WEEKS AND HISTORY MINIMUM, ONE DEFINITION EACH - REGISTRATION - Oct 5 2026 (kit.py issue-check; participation-check; card 2026 4)
Finding (M5 outcome, measured): the 50 candidates with P(plays) and no stat laws are all WRs with 1-2 earlier played games this season (QB 24, RB 32, TE 24 are outside both
   rules).  Season 2022 is absent from facts.load (seasons 2019-21, 2023-26); facts.complete decides which seasons enter, and which of its conditions 2022 fails is not
   measured yet.  Defect: state.participation_frame raised on a frame with no candidate rows (an empty .apply returns a frame, not a series); a week-1 card would have
   failed.
Transaction (no value changes): state owns ISSUE_WEEKS = range(4, 17), HISTORY_MINIMUM = 3 and PARTICIPATION_WR_MINIMUM = 1.  build_frames, participation_frame,
   participation.py, draws.serve_as_if_replay and cards.coverage_status read them instead of the literals (4, 16), (4, 17), 3 and (1, 2) they each wrote.  The undefined-
   input reason is built without .apply.  cards.coverage_status names a new reason ahead of short history: NOT ISSUED - team change (fewer than HISTORY_MINIMUM
   earlier played games on this team, HISTORY_MINIMUM+ this season).
Acceptance (fixed before running): issue-check accepted as in M1; participation-check accepted as in M5; card 2026 4 accepted with proj/card_2026_w4.csv and
   proj/card_2026_w4_candidates.csv byte-identical to the M5 card (kit.py same); guard passes.
Not in this transaction: the two minimums stay two rules for two objects (stat laws need 3 on this team; participation's recorded fit includes WRs with 1-2).
   Issuing stat laws for the 50 is the short-history wall, a new marginal law, so it waits behind the R-gate like the negative-yards wall.
## M6 - CANDIDATE COVERAGE - OUTCOME - Oct 5 2026 (M6a: kit.py issue-check; participation-check; card 2026 4; same; guard)
M6a ACCEPTED.  issue-check M1 ACCEPTED (1987 paired, 0 differing in 21 columns); participation-check M5 ACCEPTED (W1-W4 as before); card 2026 4 ACCEPTED, and
   card_2026_w4.csv (1230423 bytes) and card_2026_w4_candidates.csv (131782 bytes) are byte-identical to the M5 card; guard passed, 282 names across 12 modules.
   ISSUE_WEEKS, HISTORY_MINIMUM and PARTICIPATION_WR_MINIMUM now have one definition each, in state.  No team-change candidate at 2026 w4.
M6 stop condition met: every one of the 517 week-4 candidates is ISSUED or carries a named status (unexplained 0).  Not opened: the short-history wall (stat laws for
   the 50 WRs with 1-2 earlier played games, and the other 80) is a new marginal law, and R3 puts the R-gate before any new marginal wall.
2022 (measured): no raw file exists for the season (stats, pbp, injuries, rosters, snaps and snap_counts are all absent), so facts.complete never admits it.  Every
   recorded fit, walk-forward and atlas row was built without 2022.  Fetching it is an owner decision, because it would change facts and every witness that lists seasons.
## M7 - MARKET (P(OVER / UNDER / PUSH) AT AN ENTERED LINE) - REGISTRATION - Oct 5 2026 (kit.py card 2026 4; market-check 2026 4; market; DRY RUN)
Object: market.py, after cards.  P(over), P(under) and P(push) = the shares of week N's frozen draws above, below and at an entered line, given he plays, then under
   the declared settlement: void (P(Y | plays), P(plays) beside it) or zero ((1 - P(plays)) x atom at 0 + P(plays) x P(Y | plays)), per the section 9 conditioning table.
   The line is entered on the command line; no odds file is read (guard check 10 unchanged).  The frozen draws are written with the card
   (draws.freeze_draws -> proj/frozen_draws_SEASON_wWEEK.npz, every issued player stat row x 2000 draws, F8 as composed) and are the market's only source.
Decision status: DECISION-QUALIFIED only when the stat's atlas cell is DECISION-QUALIFIED and, under zero, participation is ISSUED - DECISION-QUALIFIED (no producer
   issues that today, so every zero settlement is UNRESOLVED); otherwise the number is shown with UNRESOLVED and its reason.
Acceptance (fixed before running): W1 one frozen row per card stat row, with draw mean and five quantiles equal to the card's exactly; W2 a rerun of the issue path
   reproduces the frozen keys, terms, positions and every draw exactly; W3 at each row's half-point line, over + under + push = 1 within 1e-12, and zero settlement at
   P(plays) = 1 equals void exactly.
## M7 - MARKET - OUTCOME - Oct 5 2026 (kit.py card 2026 4; market-check 2026 4; market; DRY RUN)
ACCEPTED.  Card 2026 w4 unchanged (517 candidates, 2129 stat rows) and now writes proj/frozen_draws_2026_w4.npz (SHA-256 a31d5545157525aa...).  W1: 2129 frozen rows x 2000
   draws, unpaired 0, draw means and quantiles differing 0 of 12774.  W2: a rerun of the issue path reproduces keys, terms, positions and all 4258000 draws.  W3: max
   |over + under + push - 1| 0, zero settlement at P(plays) 1 differing from void 0.  Decision status at half-point lines: void DECISION-QUALIFIED 240 of 2129, the rest
   UNRESOLVED by their atlas cell; zero settlement UNRESOLVED on all 2129 (participation NOT DECISION-QUALIFIED on the 240).
Queries: Bourne F5 TDs 0.5 void P(over) .0815 DECISION-QUALIFIED; Bourne F5 receiving yards 34.5 zero P(over) .4708 (given he plays .5115, P(plays) .9203) UNRESOLVED -
   CENTER TOO LOW; Brissett Q3 passing yards 249.5 void P(over) .5085 UNRESOLVED - TOO NARROW.  Guard passed, 294 names across 13 modules.
## M8a - DST LAW (THE EARNED V1 YARDSTICK, ONE PRODUCER) - REGISTRATION - Oct 5 2026 (kit.py dst-check; dst 2026 4; issue-check; DRY RUN)
Premises (measured Oct 5): proj/dstick_report.txt records DST yardstick EARNED: V1 (calibration noise-like on dev, tests 2020/2021/2023, and on 2024-25; V1 over V0
   CRPS gain per slate passes on both).  proj/dstick_rows.csv.gz: V0 and V1 walk-forward rows, 384 per test season (2020, 2021, 2023, 2024, 2025; k 8, 8, 8, 12, 12),
   and 32 V1 rows for 2026 w4 (fit on seasons <= 2025, k 20).
Object: state.dst_frame (retarget.py's DST inputs: season-to-date DST mean, earlier team-games, opponent offense season-to-date points, giveaways and sacks taken);
   laws.dst_center / dst_samples / dst_quantiles / dst_rank (dstick.py's ds_center and ds_dist, line for line); laws.dst_week issues the specification the recorded
   verdict names (read from proj/dstick_report.txt; no earned verdict refuses).  Fit rows use state's ISSUE_WEEKS and HISTORY_MINIMUM.  A week-N team-game without a
   law is NOT ISSUED with its reason.  laws.within_tolerance is M1's numeric tolerance, now one definition used by issue-check and dst-check.
Acceptance (fixed before running): W1 the walk-forward of V0 and V1 reproduces every recorded walk-forward row (center, p10, p50, p90, outcome_rank, k within M1's
   tolerance; every row paired); W2 the coming-week path reproduces the recorded 2026 w4 rows (center, p10, p50, p90, k; every team paired); issue-check still accepted.
Findings recorded here, not judged:
   (1) proj/f8_rows.csv.gz is not reproducible by construction: it was drawn on the shared-stream sampler M2 retired.  Measured against the atlas's keyed F8 rows:
       16566 paired, p10 equal 4, p90 equal 2, max |diff| p10 3.19, p90 4.48, means equal 0.  F8's standing comes from the M3 atlas, not from f8_rows.
   (2) The handoff's M8 bar "reconstruction vs recorded DK >= 99%" conflicts with facts' registered floor (DST 97.5%, skill 99.5%); DST stands at 98.4%.  The registered
       floor binds until the owner rules otherwise.
Next (M8b, registered separately): DST draws on keyed substreams on the card and in the frozen draws, and the DK draw with DNP = 0 (a Bernoulli(P(plays)) per player).
## M8a - DST LAW - OUTCOME - Oct 5 2026 (kit.py dst-check; dst 2026 4; issue-check; guard)
ACCEPTED.  W1: walk-forward rows 3840 vs recorded 3840, unpaired 0; center, p10, p50, p90, outcome_rank and k differing 0 (tests 2020, 2021, 2023, 2024, 2025; k 8, 12).
   W2: 2026 w4 laws 32 vs recorded 32, unpaired 0, without a law 0; center, p10, p50, p90 and k differing 0 (k 20).  issue-check M1 ACCEPTED (1987 paired, 0
   differing) through laws.within_tolerance.  Guard passed, 312 names across 13 modules.  Display note: a rounded negative sample prints as -0 (equal to 0).
## M8b - DK DRAWS (DNP = 0) AND DST DRAWS ON THE CARD - REGISTRATION - Oct 5 2026 (kit.py card 2026 4; dk-check 2026 4; market-check 2026 4; DRY RUN)
Object: dk.dnp_zero (mechanical: a DK draw is the F8 draw where the participation uniform falls below P(plays), else 0); draws.dk_slate (participation uniforms on
   each row's own substream, label participation) and draws.dst_slate (2000 draws per DST law resampled from its law sample on its own substream, label = the law's
   model); week_draws carries participation, DST and DK, so the card no longer calls participation itself.  Card rows name their conditioning: given he plays
   (stats, F8), DNP = 0 (DK), the defense plays every game (DST, in proj/card_SEASON_wWEEK_dst.csv).  The frozen draws carry every row; the market applies a
   settlement by conditioning (void does not apply to DK rows; DST rows are unchanged by it).  dk owns the terms F8 dk_points, DK dk_points and DST dk_points.
Acceptance (fixed before running): card ACCEPTED with every F8 row carrying a DK row and the candidates file byte-identical to M7's, the stat card minus its DK rows
   equal to M7's card; dk-check: coverage (DK for every F8 with P(plays), draws for every DST law), moments (summed DK mean vs summed P(plays) x F8 mean, summed
   DST draw mean vs law-sample mean, |z| < 4), isolation (20 DK and 8 DST rows redrawn alone equal); market-check W1-W3 PASS on the extended frozen draws.
Not in this transaction: DST has no atlas cell (its calibration is dstick's own EARNED verdict, not the M3 rule), so every DST probability is UNRESOLVED - NO
   ATLAS CELL until the atlas grades DST; DK inherits participation's NOT DECISION-QUALIFIED.
## M8b - DK DRAWS (DNP = 0) AND DST DRAWS ON THE CARD - OUTCOME - Oct 5 2026 (kit.py card 2026 4; dk-check 2026 4; market-check 2026 4; parity rerun of the M7 code)
ACCEPTED.  Card 2026 w4: 2458 player rows (2129 stat and F8 rows + 329 DK rows, every F8 row with a DK row) and 32 DST rows; candidates file byte-identical to M7's.
   dk-check: coverage PASS (329 DK, 32 DST); moments DK z -0.27, DST z -0.39; isolation 20 DK + 8 DST rows differing 0; DK draws at 0 .103 vs mean 1 - P(plays) .103.
   market-check: frozen rows 2490 x 2000, W1 differing 0 of 14940, W2 all 4980000 draws reproduced, W3 max |sum - 1| 1.1e-16.  Guard passed, 324 names across 13 modules.
Correction to the registered acceptance wording: "the stat card minus its DK rows equal to M7's card" first read False through DataFrame.equals, which compares
   dtypes.  The measured cause: atlas_rows is a whole number on every stat row and blank on every DK row, so it reads as float64 where M7's card read int64.  A rerun
   of the M7 code (dk, draws, cards as of M7) into a scratch folder gave candidates byte-identical and the 2129 stat rows equal cell for cell
   (assert_frame_equal, check_dtype False, check_exact True); the only dtype difference was atlas_rows int64 vs float64.  The criterion is met on values.
Queries: Bourne DK 8.5 zero P(over) .3845 (F8 zero-settled .3783 - two realizations of one mixture); BUF DST 7.5 P(over) .5845; both UNRESOLVED - NO ATLAS CELL.
## M10 - BASE LINEUP (ONE OPTIMIZER ON THE FROZEN DRAWS) - REGISTRATION - Oct 6 2026 (kit.py facts; base 2026 4; DRY RUN)
Premises (measured Oct 5): sources/raw/dk_weekly holds DK_2026_w3.csv and DK_2026_w4.csv (DraftKings' layout; 2026 w4: 729 rows, QB 93 RB 168 WR 271 TE 169 DST 28,
   14 games).  Name key (facts.norm) + team joins 439 of 701 DK skill rows to a card candidate with 0 duplicate matches; ISSUED among them QB 23, RB 68, TE 77, WR 117.
   Materiality unit: 1 DK (CHARTER AT END-TO-END, "1 DK = the kit's materiality unit").
Object: facts.price_file - the one reader of the price file (through ingest's DKW; ingest.RAW_READERS names it for facts).  DraftKings' Status (week N's roster status)
   and AvgPointsPerGame are dropped at the door, unread.  optimize.slate_pool - every price row with expected DK points (the card's DK row center = the mean of the
   frozen DK draws, DNP = 0; the DST card row center = the DST law's center) and one eligibility: ELIGIBLE, or NOT ELIGIBLE with its reason (no candidate with this name
   and team; the candidate's coverage status; no DK draw; no DST law; ambiguous match).  optimize.base - best9 (unchanged) on expected DK points under the cap; slots
   from DraftKings' Position; FLEX = the surplus RB / WR / TE with the smallest expected points.  BASE is ISSUABLE - NOT DECISION-QUALIFIED (DK draws have no atlas
   cell; participation NOT DECISION-QUALIFIED).  An expected total is a sum of means, so BASE does not depend on cross-player dependence; FLOOR and CEILING do (after M9).
Acceptance (fixed before running): kit.py facts rebuilds tables identical in content to the current ones (facts.py changed: freshness); the BASE lineup is legal
   (9 distinct players, 1 QB, 2-3 RB, 3-4 WR, 1-2 TE, 7 skill, 1 DST, salary <= 50000, 2+ games); every price row carries one eligibility; the mean of the lineup's
   per-draw totals equals the summed card centers within 1e-9; no single-exclusion re-solve beats BASE (optimality witness).
Reading, not a gate: per lineup player, re-solve without him; the paired per-draw gap is MATERIAL iff gap - 2 SE > 1 DK, IMMATERIAL iff gap + 2 SE < 1 DK, else
   UNRESOLVED.  Reported: ISSUED candidates on slate teams without a price row (by name), for the work order.
Retires: dk_classic.py and s.py's best9 on expected points (legacy; not kit modules).
## M10 - BASE LINEUP - OUTCOME - Oct 6 2026 (kit.py facts; base 2026 4; DRY RUN)
REFUSED.  facts rebuilt with the price-file door: game, player_game and team_game decompressed byte-identical to the tables before (independent check DST 98.4%,
   skill 99.6%).  Pool: 729 price rows, 14 games, 28 teams, one eligibility each (ELIGIBLE: DST 28, QB 23, RB 68, TE 77, WR 117).  Lineup legal ($50,000, 6 games,
   E[DK] 170.93); no single-exclusion re-solve beats it.  The refusal: the mean of the lineup's per-draw totals (171.00) differs from the summed card centers by +0.068.
Cause (from the code): the registration defined expected points two ways - a player's as the mean of his DK draws, a defense's as the DST law's center (the OLS
   center, which is neither its draw mean nor its law sample's mean).  The check compared the two definitions; the BASE scores carried the mixed one.
Findings for the work order: 4 ISSUED candidates on slate teams have no price row by name key and team (Matthew Hibner BAL, Josh Palmer BUF, Kenneth Gainwell TB,
   Christopher Brooks GB) - given-name forms facts.norm does not join; 262 DK skill rows match no candidate (most have no previous team-game row).
## M10b - BASE LINEUP, ONE DEFINITION OF EXPECTED DK POINTS - REGISTRATION - Oct 6 2026 (kit.py base 2026 4; DRY RUN)
Change: expected DK points = the card's draw_mean (the mean of the row's frozen draws) for every row, players and DST alike; nothing else changes.
Acceptance (as M10, fixed before running): lineup legal; every price row with one eligibility; the mean of the lineup's per-draw totals equals the summed draw means
   within 1e-9; no single-exclusion re-solve beats BASE.  Stability readings and the unpriced ISSUED list reported as in M10.
## M10b - BASE LINEUP - OUTCOME - Oct 6 2026 (kit.py base 2026 4; DRY RUN)
ACCEPTED (the run's report line reads "M10 BASE ACCEPTED"; the code's label predates the b).  Pool unchanged: 729 price rows, 14 games, 28 teams, one eligibility each.
   BASE: Shough, Gibbs, K. Williams, Olave, Adams, Raymond, Kelce, J. Johnson (FLEX), Dolphins - $50,000, 6 games, E[DK] 171.00 (draw totals P10 136.1, P90 208.0);
   the lineup is M10's, the Dolphins' expected points now their draw mean (5.83 for 5.76).  Mean of per-draw totals - summed draw means +2.8e-14; no single-exclusion
   re-solve beats BASE.  Stability: MATERIAL without Raymond 6.42, Shough 4.43, Olave 3.50, J. Johnson 2.93, K. Williams 2.09; UNRESOLVED without Dolphins / Gibbs
   (0.32 +- 0.75, the same alternative) and Kelce / Adams (0.84 +- 1.10, the same alternative).  Guard passed, 332 names across 13 modules.
PRODUCTION LANE COMPLETE (M1-M8, M10 BASE): every candidate issued or named; laws, keyed draws, atlas grades, participation beside the given-plays laws, market at an
   entered line, DK with DNP = 0 and DST, BASE.  Open: the R-gate (R3) before any new marginal wall (short-history, negative yards) or M9; FLOOR / CEILING after M9;
   name aliases at the price door (4 ISSUED unpriced); 2022 not fetched (owner decision).
## STEERING - v0 FROZEN - Oct 6 2026 (owner ruling; binds every later registration)
The engine is built. From here, work only on increasing honest coverage, calibration, or decision relevance of the issued product.
v0 = the production lane as accepted M1-M10b (2026 w4 DRY RUN).  No module restructuring; research produces versioned improvements to v0 only.
ORDER: R-gate -> the largest atlas-owned marginal defect -> coverage (130 short history, 58 unresolved position) -> participation (P(plays) to DECISION-QUALIFIED)
   -> Root 3 -> FLOOR / CEILING.  The R-gate is one registered rule with simulated false-pass and power; after it, governance is not reopened.
RANKING of marginal roots: affected issued rows x calibration severity (atlas) x decision relevance; a root does not go first for looking bad.
ANTI-DRIFT: no wall is registered without the sentence "If this passes, these currently unresolved issued rows become better or DECISION-QUALIFIED: ...", naming them.
PROGRESS METRICS (v0, 2026 w4): candidates receiving a forecast 329 / 517 (63.6%); issued stat rows DECISION-QUALIFIED 240 / 2129 (11.3%); proper score vs frozen Y:
   Y ahead on pinball at every level, F8 ahead on center RB / WR / TE (M3); market queries DECISION-QUALIFIED void 240 / 2129, zero 0; lineup objectives supported by
   earned dependence: BASE needs none, FLOOR / CEILING 0.  Not progress: walls written, scripts deleted, CHARTER lines, mechanisms explored.
Correction (R-gate premise): a season-sign test at S = 4 has a smallest p of 1/16 = .0625, so a 5% target is unreachable that way; the forward rule must treat
   seasons as random effects.
## R-GATE - FORWARD PROMOTION RULE - REGISTRATION - Oct 6 2026 (owner review adopted; before code; no gain inspected)
Rule: a newly registered wall passes iff t = mean(g_s) / (sd(g_s) / sqrt(S)) > Student-t quantile .95 with S - 1 df, where g_s = the mean per-slate paired gain
   (baseline loss - candidate loss) in test season s.  Validated at S = 4: critical 2.353.  Seasons enter as random effects; no season-sign enumeration.
Scope: genuinely new walls registered before their result is inspected.  Historical verdicts unchanged forever.  The five class (3) formulations (WR scale log-linear,
   WR scale spline, TE location, WR L2, RB L3R) stay class (3) / not promoted; re-registering a seen formulation is not prospective.  They supply power templates
   and effect-size targets only.
Null library (eligibility fixed before simulation): every recorded slice (file x term x stage x position) of proj/f6_rows_*.csv.gz and proj/f6_dependence*_rows.csv.gz
   with exactly 4 test seasons, paired slate-level losses for one fixed baseline and candidate, and at least 2 slates per season; excluded only by a recorded verdict
   label naming an instrument defect, an information-set violation or domain incoherence, listed by name in the run.  Branch-balanced: each slice weighted
   1 / (slices in its file x term x position branch); unweighted and per-branch rates reported beside it.
Null DGP, per slice in its own units: season means m_s, within variances v_s, slate counts n_s; tau2 = max(0, Var(m_s) - mean(v_s / n_s)); a replicate is
   g_s* = b_s* + mean of n_s slate residuals (centred within season s) drawn with replacement, b_s* ~ N(0, tau2).  100,000 replicates per slice, seed 20261006.
Power DGP: the same with g_s* = delta + b_s* + residual mean, delta = 0.5 x and 1.0 x each class (3) slice's observed mean gain.  Reported, not a gate.
Decision (fixed now): ADOPT iff the branch-balanced null false-pass <= .055 (5% plus a .005 margin for "materially exceeds"); otherwise REJECT this formulation.
   No critical value is retuned after the result is seen.  Monte Carlo SE reported (about .0007 at .05).
Anti-drift sentence: if this passes, every later marginal wall can earn at four test seasons, so atlas-ranked roots can move issued rows (1889 UNRESOLVED stat rows)
   toward DECISION-QUALIFIED; exact null B's 1 / 16 floor no longer blocks them.
## R-GATE - REGISTRATION OF Oct 6 - WITHDRAWN BEFORE ANY RUN - Oct 6 2026 (no simulation executed; no wall gain inspected; inventory only)
Withdrawn because its parameters were authored, not derived: normal season effects, tau2 by moments, branch weights, the .055 margin, 0.5x / 1.0x power points,
   2 slates per season, 100,000 replicates, seed.  Five-why sub-roots: (R1) a thin level filled with authored structure instead of the wall population;
   (R2) sampling where enumeration was possible; (R3) error rates authored per check instead of once.
Replacement (to be registered next): pooled sign-flip reference over eligible slices, R = {T(eps * d_w)}, c_alpha = its (1 - alpha) quantile, one pool per season
   count S (92 slices at S = 4, 7 at S = 3 per the inventory); t quantile at S - 1 df reported as a diagnostic only; exact duplicates removed; leave-one-file-out
   range of c_alpha reported; per-slice MDE = c_alpha x s_w / sqrt(S) as power.  Eligibility: g_s defined in every test season (n_s >= 1); the one
   "BLOCKED under D" slice excluded by its label.  Kit-wide: one alpha in evaluate for the R-gate, atlas bands, stability readings and moment checks; isolation,
   cutoff and line checks enumerate all rows, weeks and draw values.
Inventory (Oct 6): 100 slices; 92 with seasons 2021, 2023, 2024, 2025 (52 slates each), 8 with 2023-25 (39 slates); verdict files hold HARNESS PASS 33,
   HARNESS FAIL 66, BLOCKED under D 1, zero-history PASS 11 / FAIL 9.
## R-GATE - CANONICAL FORWARD PROMOTION RULE AND THE DRAIN OF AUTHORED CHECK VALUES - REGISTRATION - Oct 6 2026 (before code; no wall gain inspected)
Principle: no authored number.  Every value is a deletion, an enumeration, an exact identity, the statistic's own domain, or distribution theory evaluated on the
   recorded wall population; what remains are three axioms (below), each either tested on the population or ruled by the owner.
DATA: for each eligible slice w (proj/f6_rows_*.csv.gz, proj/f6_dependence*_rows.csv.gz; one pool per season count S): g_ws = mean over season s's slates of
   (l_base - l_cand); T_w = mean(g_w) / (sd(g_w) / sqrt(S)).  Eligible iff g_ws is defined for every test season (n_s >= 1) and no recorded verdict label names a
   domain defect (the one BLOCKED under D slice).  Exact-duplicate slices (identical g vectors) collapse to one.
LIKELIHOOD: T | delta ~ noncentral t (df S - 1, noncentrality delta), delta = mu sqrt(S) / sigma (sign(delta) = sign(mu)).
PRIOR: Kiefer-Wolfowitz NPMLE G over the pool: support = the observed T_w, weights by EM to the float64 fixed point.
RULE: a genuinely new wall, registered before its result is inspected, is EARNED iff E[delta | T_new, G] > 0 (Bayes rule for the proper score's own linear loss,
   zero switching cost).  Historical verdicts never re-judged; the five class (3) formulations stay class (3).
DIAGNOSTIC (reported every run, not a gate): pooled sign-flip reference R = {T(eps * (g_w - mean g_w))}, quantiles beside t(S - 1); the noncentral-t likelihood
   is called into question when they disagree.
AXIOMS: (1) a future wall is exchangeable with the recorded pool; (2) season means are normal around the wall mean (tested by the diagnostic); (3) a promotion
   carries zero switching cost in score units (an owner ruling; a nonzero cost is stated in score units and replaces 0 in the rule).
DRAIN OF CHECK VALUES (one transaction, accepted when each reproduces its prior verdict): M5 W4 every week 4-16 x 2020-25; M7 W3 every distinct draw value and
   midpoint per row; M8b DK draws = F8 x 1[U < p] and DST draws = sample[idx] recomputed byte for byte for all 329 DK and 32 DST rows (moments z test removed);
   M10 stability MATERIAL iff E[gap] > 1 DK (the +-2 SE band removed), MC precision reported.
Withdrawn by this entry: the pooled-quantile c_alpha replacement named in the Oct 6 withdrawal (it still needed alpha).
## R-GATE AND CHECK DRAIN - SUPERSEDED BEFORE CODE, THEN REREGISTERED - Oct 6 2026 (five whys on the drain targets; product delta > 0 and complexity delta <= 0)
Superseded (no code written, no gain inspected): the NPMLE / noncentral-t / EM gate and its diagnostic, and the enumerated or recomputed checks.  Five whys: the
   gate's strictness stood in for a cost the score does not see - added code; enumerating identities and recomputing with the same functions add no information.
R-GATE: a genuinely new wall, registered before its result is inspected, is EARNED iff mean held-out season gain g-bar > 0 (posterior mean of mu under the
   reference prior 1 / sigma) AND the kit's total AST node count after the wall <= before (measured by the guard's AST walk; 63266 on Oct 6).  Promotion decides
   which law issues; DECISION-QUALIFIED stays the atlas's.  Historical verdicts frozen; the five class (3) formulations stay class (3); passes_gate and the exact
   null B promotion path become read-only history.
DRAIN TRANSACTION (next): dissolve market-check W3 (partition identity) and dk-check (tautological recompute; market-check W2 already reproduces every DK and DST draw);
   converge participation W4 into state.purity (participation frame columns at purity's registered cutoffs; every guard); M10 stability MATERIAL iff E[gap] > 1 DK,
   with lineup_totals and the totals identity removed so optimize reads only the card and the price file.  Acceptance: card, market-check W1-W2, base and guard
   unchanged in verdict and output; kit AST node count strictly lower, printed before and after.
## R-GATE - REGISTERED (OWNER: APPLY THE MIGRATION CRITERION LITERALLY) - AND THE CHECK DRAIN - Oct 6 2026 (before code; no wall gain inspected)
Supersedes before code: the NPMLE / noncentral-t / EM gate and the enumerated or recomputed checks.  Five whys: the gate's strictness stood in for a cost the score
   does not see (added code); enumerating identities and recomputing with the same functions add no information.
R-GATE: a genuinely new wall, registered before its result is inspected, is EARNED iff its mean held-out season gain is > 0 (the posterior mean of mu under the
   reference prior 1 / sigma) AND the kit's AST node count after the wall is <= before (evaluate.kit_size, printed by every guard).  evaluate.r_gate_earned is the
   one implementation.  Promotion decides which law issues; DECISION-QUALIFIED stays the atlas's.  Historical verdicts frozen; the five class (3) formulations stay
   class (3); passes_gate and the exact null B path are read-only history.  No alpha, no prior, no simulation.
DRAIN (this transaction): market-check W3 dissolved (shares of a partition sum to 1 and zero at P(plays) 1 is void by definition) and the settlement rule converged
   into market.settlement_applies; dk-check and its command dissolved (it recomputed with the functions it tested; market-check W2 reproduces every DK and DST
   draw from the issue path); participation-check W4 converged into state.purity (participation inputs, T1 grid and domain reason compared at purity's
   registered cutoffs in every guard); BASE stability = expected gap, MATERIAL iff > 1 DK, and optimize no longer reads the frozen draws (a lineup total's spread
   needs cross-player dependence, M9, so it is no longer printed).
Acceptance (fixed now): participation-check W1-W3 PASS; market-check W1-W2 PASS; slate_pool and lineup_base files byte-identical to M10b's; guard passes with
   purity's participation comparison 0 differing; the kit's AST node count strictly lower than before this transaction (guard's kit size line, before and after).
## R-GATE AND CHECK DRAIN - OUTCOME - Oct 6 2026 (participation-check; market-check 2026 4; base 2026 4; same; guard)
ACCEPTED.  Kit size 63266 -> 61936 AST nodes (-1330).  participation-check W1-W3 PASS (W4 now in purity); market-check W1-W2 PASS (2490 x 2000 frozen draws, 4980000
   reproduced); slate_pool (158779 bytes) and lineup_base (3024 bytes) byte-identical to M10b's; BASE stability now expected gaps (MATERIAL: Raymond 6.42, Shough 4.43,
   Olave 3.50, J. Johnson 2.93, K. Williams 2.09; IMMATERIAL: Dolphins / Gibbs 0.32, Kelce / Adams 0.84).  purity: participation inputs 0 differing at all 9 cutoffs
   (472, 438, 500, 507, 449, 511, 505, 477, 508 candidates x 8).  Guard passed, 333 names across 13 modules.
ROOT RANKING (a reading, registered before it is read): per atlas cell, misplaced rows = issued card rows x 5 x max(0, decile_deviation - noise_95th) - the count of
   issued rows whose PIT would have to move to calibrate the cell beyond the atlas's registered noise.  Summed by (law family, term) as the root key from the card.
   Decision relevance dissolved: every issued stat row is a market query.  The first root by misplaced rows is the next wall's target, with its anti-drift sentence.
## D-CONFORMANCE - ZERO-STATE NORMAL YARDS LAWS DRAW THE POINT MASS AT 0 - REGISTRATION - Oct 6 2026 (draws-check; atlas; card 2026 4; market-check; base)
Root (measured, ROOT RANKING Oct 6): normal-family yards hold 240.4 of 317.0 misplaced issued rows; the six zero-state yards cells hold 180.4 (WR rushing 83.5,
   TE rushing 65.0, WR receiving 11.6, RB receiving 7.6, TE receiving 6.6, RB rushing 6.0) on 252 issued rows.
Cause (code read): draws.STATE_ZERO_IS_POINT_MASS omitted the normal family, so a yards law whose center was formed at exactly 0 drew Normal(0, sd) - half its mass
   below 0 - against the registered rule COMPOSITION UNDER D (line 2043: "mean 0 -> point mass at 0", no leak) that the recorded composition followed.  Named as a
   defect in the M3 outcome (line 4065).  This is conformance to a registered rule, not a new law: the R-gate does not apply.  Its two terms are reported anyway.
   Not the rung 3z hurdle (P(0) per slice plus a positive part; harness verdicts frozen as recorded).
Change: normal joins the point-mass families, and the state-zero rule, written four times in draws.py (defined, two draw_law branches, law_expectation), becomes
   one function, draws.point_mass.  Laws unchanged (issue-check unaffected).
Anti-drift sentence: if this conforms, the 252 issued zero-state yards rows (six cells above) stop issuing negative and fractional yards, and their atlas cells are
   regraded on the point mass.
Acceptance (fixed now): draws-check M2 ACCEPTED as before (moments, isolation, recorded witnesses, wall 9 rho); atlas regraded; card 2026 4 ACCEPTED; market-check
   W1-W2 PASS; base ACCEPTED; kit AST strictly lower.  Reported, not gated: per-season mean CRPS gain on the zero-state yards rows (atlas rows before vs after),
   the six cells' new qualifications, and DECISION-QUALIFIED issued stat rows (v0: 240 / 2129).
## D-CONFORMANCE - ZERO-STATE NORMAL YARDS - OUTCOME - Oct 6 2026 (draws-check; atlas; card 2026 4; market-check; base; guard)
ACCEPTED as conformance (not a wall; not EARNED by the R-gate).  draws-check M2 ACCEPTED (37 moment groups pass, isolation 0, 9558 witnesses exact, wall 9 rho
   reproduced); atlas regraded; card, market-check W1-W2 and base ACCEPTED; kit size 61936 -> 61920 AST nodes.  Zero-state yards rows paired 9694; mean CRPS gain per
   season 2021 .961, 2023 1.088, 2024 1.160, 2025 1.180 (point mass vs Normal(0, sd)).  DECISION-QUALIFIED issued stat rows 240 -> 325 / 2129 (+85 = TE rushing
   yards zero, now DECISION-QUALIFIED).  Moved to CENTER TOO LOW: receiving RB / WR zero, rushing RB / WR zero (bias -1.9 to -3.0 on receiving and RB rushing; the
   point mass misses the nonzero outcomes).  F8 WR chain CENTER TOO LOW -> TOO NARROW: the Normal(0, sd) draws had been widening F8; its narrowness is the residual.
   BASE unchanged in membership (E[DK] 171.02).
Five-whys reading: the D rule equates a formed estimate of 0 with impossibility; zero events in n games is evidence, not P = 0.  The yards terms lack the
   zero-history layer the count terms have.  Open question before any wall: the empirical support of game yards (negatives, integers) - measured below.
## CORRECTION - THE Oct 6 ZERO-STATE POINT MASS WAS NOT D-CONFORMANCE - REVERTED - Oct 6 2026 (owner ruling; measured support)
Measured (facts, played rows): game yards take negative integer values at every position (rushing min QB -12, RB -14, TE -7, WR -20; receiving min QB -10, RB -11,
   TE -10, WR -13; negative share up to .1199 QB rushing), non-integer share 0.  Atlas rows, zero state: P(Y > 0) receiving RB .1544, TE .1759, WR .1779; rushing
   RB .1300, WR .0324, TE .0071; P(Y < 0) .0011 to .0090.  So constructor state zero does not imply outcome zero (undefined != zero estimate != impossible outcome),
   and the COMPOSITION UNDER D point mass is not a domain requirement for game yards.
Correction: the D-CONFORMANCE transaction (registration and outcome above) was accepted under a false premise.  Its point mass is a predictive model, P(Y = 0) = 1,
   that the rows falsify; it is not EARNED and not conformance.  Its CRPS gains (.961, 1.088, 1.160, 1.180) stand as a diagnostic reading only: the incumbent
   zero-state Normal(0, sd) is grossly over-dispersed.  Production reverts: normal leaves draws.STATE_ZERO_IS_POINT_MASS; draws.point_mass (one state-zero rule)
   stays.  Acceptance: atlas regraded to its v0 counts (M3: DECISION-QUALIFIED 8, CENTER TOO LOW 17, TOO NARROW 8, TOO WIDE 7, MISCALIBRATED 5, CENTER TOO HIGH 4,
   UNRESOLVED 2); card DECISION-QUALIFIED issued stat rows back to 240 / 2129; BASE E[DK] 171.00; draws-check M2 ACCEPTED; guard passes.
Work order (same premise, registered laws, not changed here): the share laws and yards-given-count also issue a point mass at state zero; F5 targets WR zero is
   CENTER TOO LOW (bias -.337).  Each is a candidate for the zero-history treatment below, through its own registered wall.
## ZERO-HISTORY YARDS WALL - REGISTRATION - Oct 6 2026 (before code; no result of this formulation computed)
Cells: F5 receiving yards RB / TE / WR and F5 rushing yards RB / TE / WR, law state zero (layer 1, as the count terms' zero-history layer).
Law (no family authored): from the training rows of that term x position in law state zero (seasons before the cutoff), P(Y != 0) = their nonzero share (maximum
   likelihood) and Y | Y != 0 = the empirical distribution of their nonzero outcomes (integers, negative and positive).  A draw is 0 when its keyed uniform is at or
   above P(Y != 0), else a keyed resample of the nonzero sample.  No training rows -> undefined (draws nothing, named).
Judgment (R-GATE, per cell): on the M3 serve-as-if replay (tests 2021, 2023, 2024, 2025), per test season the mean over slates of incumbent CRPS - wall CRPS on the
   cell's zero-state rows; a cell is EARNED iff the mean of its four season means > 0 AND the transaction's kit AST after <= before.  Cells that do not earn keep
   the incumbent.  Disclosed before the run: the point-mass reading shows the incumbent is over-dispersed, so the gain sign is expected; the decisive product
   reading is the atlas qualification of each promoted cell.
Anti-drift sentence: if this passes, the zero-state yards rows of these six cells - on the 2026 w4 card WR rushing 113, TE rushing 85, WR receiving 19, RB
   receiving 13, TE receiving 12, RB rushing 10 (252 issued rows) - get a law whose support is the observed one, and their atlas cells are regraded.
## CORRECTION REVERT - OUTCOME - Oct 6 2026 (draws-check; atlas; card 2026 4; market-check; base; guard)
ACCEPTED.  Atlas back to its v0 counts (DECISION-QUALIFIED 8, CENTER TOO LOW 17, TOO NARROW 8, TOO WIDE 7, MISCALIBRATED 5, CENTER TOO HIGH 4, UNRESOLVED 2); card
   DECISION-QUALIFIED issued stat rows 240 / 2129; BASE E[DK] 171.00; draws-check M2 ACCEPTED (witnesses 9558 exact, rho reproduced); kit size 61919 AST nodes.
ZERO-HISTORY YARDS WALL - cost measured before any run: the minimal promotion (fit_state samples, row_laws layer, verdict read, sampler) adds 330 AST nodes
   (61919 -> 62249) before its judgment instrument and witness scoping.  Under the R-gate's literal AST charge the wall cannot earn as registered.  The convergent
   form: one zero-state law (the empirical distribution of training zero-state outcomes) for counts and yards, dissolving the zero-history NB fit, ztnb_fit and the
   hurdle sampler / expectation - judged cell by cell against each earned incumbent; it dissolves code only where every replaced cell earns.
## R-GATE AMENDMENT AND EMPIRICAL ZERO-STATE WALL - REGISTRATION - Oct 6 2026 (owner ruling; before any run of this procedure)
R-GATE AMENDED (owner): two gates.  Scientific gate - a cell of a genuinely new wall is EARNED iff its mean held-out season gain > 0 (evaluate.r_gate_earned; the
   posterior mean of mu under the reference prior 1 / sigma).  Operational gate - an earned cell is integrated only if the production invariants hold (M1 / A2' /
   M2 witnesses scoped to v0 with promoted cells listed; guard); the kit's AST change is reported there as a consequence, never as evidence for promotion.
   The AST term leaves the earning rule.
WALL (supersedes the ZERO-HISTORY YARDS WALL registration; its six cells are included): one procedure, fit per term x position, no evidence pooled across cells.
   For a cell whose law state and own constructor state are both zero, the law at test season s is the empirical distribution of that term x position's
   zero-state outcomes in the recorded spine with season < s: F(y) = (1 / n) sum 1(Y_i <= y).  It carries integer counts, negative yards, the atom at 0, skew and
   tails without a family.  No training rows in a season -> undefined.
JUDGMENT (draws.empirical_zero_state_wall, kit.py zero-state-wall): on the M3 replay rows (proj/atlas_rows.csv.gz, tests 2021, 2023, 2024, 2025), 2000 keyed
   resamples per row (substream label "empirical zero-state"); per season the mean over slates of incumbent CRPS - wall CRPS; incumbent = the replay's issued
   law as graded in atlas_rows (frozen by each verdict's rows_sha256).  A cell is judged iff every test season has graded rows and a training sample, else
   UNRESOLVED.  EARNED -> the empirical law owns the cell at integration; FAIL -> the incumbent remains; no second empirical variant.  Promotes nothing.
STOP RULE: register, judge every cell once, integrate the earned cells in one later transaction under the operational gate, measure its code change, stop.
Anti-drift sentence: if cells earn, these zero-state issued rows on the 2026 w4 card get a law read from their own history: F5 rushing yards WR 113, TE 85,
   RB 10; F5 receiving yards WR 19, RB 13, TE 12; F5 TDs WR 84, TE 58, RB 44; F5 receptions WR 19, RB 12, TE 12; F5 targets WR 12, RB 9, TE 8; F5 carries RB 10;
   QB rushing TDs 14; Q5 interceptions 3 (537 rows).
## EMPIRICAL ZERO-STATE WALL - JUDGMENT OUTCOME - Oct 6 2026 (kit.py zero-state-wall; tests 2021, 2023, 2024, 2025; 21 cells)
EARNED 13; FAIL 6; UNRESOLVED 2 (QB carries, QB rushing yards: a test season without graded rows).  proj/empirical_zero_state_verdicts.csv, rows hashed per cell.
   Yards cells - all EARNED, every season positive: receiving RB +2.07 to +3.01, TE +.89 to +.95, WR +5.45 to +5.50; rushing RB +4.17 to +5.78, TE +.67 to +.71,
   WR +.72 to +.75 CRPS per row.  F5 targets WR EARNED (+.0452, +.0471, +.0177; 2021 -.0048).
   Count cells - EARNED: F5 TDs WR, F5 receptions RB / TE / WR, F5 targets RB / TE; FAIL: F5 TDs RB / TE, F5 carries RB, Q4 passing TDs, Q5 interceptions, QB
   rushing TDs.  Reading: their season gains are within about .005 of 0 (Q5 within .125), the size of the paired Monte Carlo noise of two 2000-draw CRPS estimates;
   the empirical law and the earned parametric zero-state laws (fit on the same zero-state rows) are indistinguishable there, so the EARNED / FAIL split among them
   is not evidence of a difference.  The registered rule stands: EARNED cells integrate, FAIL cells keep their incumbents, no second variant.
## EMPIRICAL ZERO-STATE WALL - INTEGRATION - REGISTRATION - Oct 6 2026 (operational gate; before the run)
Change: laws.zero_state_sample is the one producer of the sample for the judgment and the issued law; build_inputs reads the EARNED cells; fit_state carries their
   samples (integers); row_laws adds a layer-4 law "empirical zero-state" (mean = the sample mean) on each earned cell's zero-state rows, so it is final there;
   draws resample the sample on the layer's keyed substream, the same label as the judgment, so the replay reproduces the judged draws.  zero-state-wall refuses a
   second judgment.
Operational gate (fixed now): M1 issue-check and A2' replay ACCEPTED on v0 rows with the promoted layer-4 rows set aside and counted; draws-check M2 ACCEPTED (the
   promoted cells' hurdle rows are no longer final, so their witnesses retire; every witness still drawn is found and exact); the integration witness: on each
   EARNED cell's zero-state replay rows, per season the mean over slates of (atlas CRPS before - after) equals the judged season gain within 1e-12; atlas, card,
   market-check and base ACCEPTED; guard passes.  Reported, not gated: kit AST change; DECISION-QUALIFIED issued stat rows (v0 240 / 2129); changed qualifications.
## EMPIRICAL ZERO-STATE WALL - INTEGRATION - CORRECTION AND WITNESS REGISTRATION - Oct 6 2026 (before the run)
Correction: the registered integration witness (season gains equal to the judged gains within 1e-12) ran as a printed one-liner, not as a gate; the guard passed and
   the ledger advanced to 4424 lines with it unmet: max |diff| RB rushing yards .109, RB receiving yards .027, TE receiving yards .007, WR receiving yards .0033,
   TE targets .001, the others 1e-4 to 3e-6.  Measured cause in the witness: it averaged every law-state-zero row of a cell (RB receiving yards 408); the
   judgment averaged the law-state-zero rows whose own spine state is also zero (399).  The registration's "each earned cell's zero-state rows" names neither, so
   the issued scope (law state zero) and the judged scope (law and own state zero) were never fixed as one.  proj/atlas_rows_v0.csv.gz and proj/atlas_v0.csv were
   deleted after the run, so the witness is recomputed from the issue path.  The integration is NOT ACCEPTED until it passes; if refused, v0 is restored.
Change: draws.replay_context / replay_slates are the one producer of the M3 replay (atlas and zero-state-check); ungraded_reasons the one gradability rule; row_crps
   the one per-row CRPS; zero_state_scope the one definition of the judged rows (the judgment's filter, now read by the judgment and the check).  kit.py
   zero-state-check draws every issued layer-4 row twice on the issue path - incumbent (layer 4 set aside, final recomputed: the v0 law of M1 / A2') and issued -
   and grades both as the atlas grades, in incumbent atlas order.
Acceptance (fixed now): the atlas rerun equals the pre-change proj/atlas_rows.csv.gz and proj/atlas.csv in content (kit.py same); zero-state-check: issued CRPS
   equals proj/atlas_rows.csv.gz (differing 0); per EARNED cell, judged-scope rows equal the verdict's rows, their content hash equals rows_sha256, every season gain
   within 1e-12 of the judged gain; guard passes.  Reported, not gated: issued rows outside the judged scope per cell, by spine state.  The scope decision (issue
   the law on the judged scope only, or register the wider scope as a new judgment) follows on that reading; nothing is decided here.
## EMPIRICAL ZERO-STATE WALL - INTEGRATION - WITNESS OUTCOME - Oct 6 2026 (kit.py zero-state-check)
Atlas rerun on the converged replay producer: proj/atlas_rows.csv.gz and proj/atlas.csv IDENTICAL in content to the pre-change files.  zero-state-check: issued
   layer-4 rows graded 14851, incumbent drew nothing 0; issued CRPS vs proj/atlas_rows.csv.gz differing 0 of 14851.  Every EARNED cell PASS: judged-scope rows equal
   the verdict's, content hash equals rows_sha256, max |season gain - judged| at most 8.88e-16.  INTEGRATION ACCEPTED: on the judged rows the issued law is the
   judged law.  Reading: 78 issued layer-4 replay rows lie outside the judged scope, every one without a row in the recorded spine at its season, week, key, term
   and position (so without an own state); cause not measured; on the work order.  Kit size 64332 AST nodes (63121 before); DECISION-QUALIFIED 335 / 2129 unchanged.
## JUDGMENT INSTRUMENT v2 - REGISTRATION - Oct 6 2026 (before the run)
Why: the v1 judgment scores incumbent and challenger with independent 2000-draw Monte Carlo.  The zero-state wall's count cells sit within about .005 of 0 and
   this CHARTER called that Monte Carlo noise without measuring it.
Instrument: draws.exact_crps scores a law row at its outcome with no draws - an empirical sample by its own E|X - y| - 1/2 E|X - X'| (exact); a normal law in closed
   form; a count law (point mass, Poisson, negative binomial, support negative binomial, hurdle) as the sum over the integers of (F(k) - 1{y <= k})^2 to the first
   doubling past y where F is 1 in double precision.  A family conditioned on a parent draw that is not a point mass refuses; common random numbers are registered
   when a wall first needs such a family, not before.  Order of instruments: exact, then common random numbers, then independent Monte Carlo; a new judgment does
   not use independent Monte Carlo where an exact score exists.
Gate (fixed now), kit.py instrument-check on the zero-state wall's 21 cells (judged-scope replay rows, incumbent = layer 4 set aside): (1) v1 reproduces - incumbent
   and wall draws on their judged substreams hash to every verdict's rows_sha256 with its row count; (2) on the first row of every cell x season the exact score
   equals the other representation - count laws by the kernel form over the pmf and samples by the threshold integral of the step CDF, within laws.within_tolerance;
   normal by the threshold integral by quadrature, within quadrature's own error bound.  Guard passes.
Reported, not judged: per cell and season the recorded gain, the exact gain, and the v1 identical-law gain (the incumbent on its substream minus the same law on a
   replicate substream: the measured Monte Carlo noise of a v1 comparison).  Under v2 an identical-law gain is 0 by construction (the score is a function of law and
   outcome) - stated, not tested.  No verdict is re-judged and nothing in the product changes.  The scientific gate is unchanged: v2 makes each season gain exact
   for the laws compared; the mean held-out season gain > 0 still decides earning.  Future walls judge with exact_crps.
## JUDGMENT INSTRUMENT v2 - OUTCOME AND CORRECTION - Oct 6 2026 (kit.py instrument-check, first run)
REFUSED as registered.  Gate (1) v1 reproduction: all 21 cells PASS (hash and rows).  Gate (2) identity: 82 cell-seasons, one failing - QB rushing yards QB 2024,
   family yards given count (state zero, point mass at 0).  Cause: the count score summed from k = 0, but a yards outcome can be negative; for y < 0 the terms
   (0 - 1)^2 at y <= k < 0 were dropped (a point mass at 0 scored 0 at y = -3 instead of 3).  The kernel form, which has no such range, caught it.  The exact gains
   printed for QB rushing yards (an UNRESOLVED cell) are therefore wrong where y < 0; every other cell's incumbent family has outcomes >= 0.
Second defect, found by inspection, not observed in this run: the count sum stopped where F(K) is 1 in double precision, and a hurdle law's F = (1 - pi) + pi x
   (F+ - p0) / (1 - p0) rounds below 1 for some pi (2879 of 100000 random pi, p0), which would not terminate.
Corrected method: the count score is the sum of F(k)^2 below y and S(k)^2 from y, S each law's own survival function, over min(0, y) .. K, K the first doubling past
   y where S is 0 in double precision; below 0 a count law has F = 0, S = 1.  The kernel form of the identity check computes E|X - X'| by prefix sums over the pmf.
   instrument-check prints the rows scored per slate.  The registered gates are unchanged; the check runs again.
Reading from the refused run (not a verdict; nothing re-judged): the exact gains of the count cells are near 0 and the recorded gains sat inside the measured v1
   identical-law noise - F5 TDs RB / TE / WR exact |gain| under .0001 per season, recorded up to .0012, identical-law up to .0005; F5 receptions and targets RB / TE
   likewise.  The yards cells' exact gains agree with the recorded gains within the identical-law noise (RB receiving +2.06 to +3.01, WR receiving +5.43 to +5.51).
## JUDGMENT INSTRUMENT v2 - OUTCOME - Oct 6 2026 (kit.py instrument-check, corrected method)
ACCEPTED.  (1) v1 reproduction: all 21 cells PASS.  (2) representation identity: 82 cell-seasons, families Poisson, hurdle, negative binomial, normal, share
   (beta-binomial, point mass), support negative binomial, yards given count (point mass); failing none.  Reading (no verdict re-judged): F5 TDs RB / TE / WR exact
   season gains under .0001 in magnitude, recorded up to .0012, v1 identical-law noise up to .0005 - the count verdicts of the zero-state wall sat in Monte Carlo
   noise, now measured; yards cells' exact gains agree with the recorded within that noise (RB receiving +2.06 to +3.01, WR receiving +5.43 to +5.51).  Future walls
   judge with draws.exact_crps.  Kit size 66451 AST nodes.
## CURRENT PRODUCT WITNESS v1 AND THE FREEZE - REGISTRATION - Oct 6 2026 (before the run)
Why: the v0 witnesses (A2', M1, M2) prove frozen history, and each promotion retires some of them, so they protect less of the served product as it improves.
Change: evaluate.freeze is the one producer of a frozen product - copies of week N's product_files (atlas rows, atlas cells, atlas coverage, week N's law rows, the
   card's three files, the frozen draws, the slate pool, the BASE lineup) to proj/frozen/NAME/ with content digests (file_content: gzip and npz containers stamp time,
   so content is compared), the kit's code digest, the CHARTER's accepted lines and digest, and the UTC time; refused if NAME exists, a file is missing, or the
   CHARTER has unaccepted lines.  The same producer freezes the prospective issue before kickoff.  evaluate.witness_check compares the product now with a freeze file by
   file and reads a differing file by cell (term / position / state; frozen draws by term).  same_content reads through file_content (one content rule).
Run: produce week 2026 w4 on the accepted code (issue, card, base; the atlas files are those the witness transaction reproduced), freeze witness_v1 2026 4, then
   reproduce from nothing (atlas, issue, card, base) and witness-check witness_v1.
Acceptance (fixed now): freeze writes 10 files; witness-check witness_v1 ACCEPTED - every file equal in content; guard passes.  v0 witnesses stay as they are, frozen
   forever.  From here every transaction that changes the product names the cells it promotes; witness-check then reads every other cell equal, and the next
   freeze (witness_v2) is taken after its acceptance.
## CURRENT PRODUCT WITNESS v1 - OUTCOME - Oct 6 2026
ACCEPTED.  freeze witness_v1 2026 4: 10 files -> proj/frozen/witness_v1, kit f56961b0c8f216a1, CHARTER 4492 lines 112f7f82b66d72fd, frozen at
   2026-10-06T02:07:12Z.  Reproduced from nothing (atlas, issue, card, base): witness-check witness_v1 - all 10 files IDENTICAL.
## PRICE-FILE NAME MATCHING - REGISTRATION - Oct 6 2026 (before the run)
Why: the M10 run named 4 ISSUED candidates on slate teams without a price row (Matthew Hibner BAL, Josh Palmer BUF, Kenneth Gainwell TB, Christopher Brooks GB):
   DraftKings and the play-by-play spell first names differently, so the name-and-team join misses them and BASE cannot see them.
Change (optimize.slate_pool): a price row the name-and-team join leaves unmatched joins a candidate it left unmatched with the same surname key (the last token of
   facts.norm's spelling), team and position, only when that pairing is one on each side; otherwise it stays unmatched with its reason.  No alias list: the residual
   sets match against each other.  A match column names how each row matched; base prints every surname match.  witness-check takes the files a transaction
   declares it changes (only those may differ).
Acceptance (fixed now): base 2026 4 ACCEPTED; witness-check witness_v1 with slate_pool_2026_w4.csv and lineup_base_2026_w4.csv declared - every other file
   IDENTICAL; guard passes.  Reported: the surname matches, the ISSUED-without-a-price-row count (was 4), the BASE lineup and its expected total (was 171.11).
   The next freeze (witness_v2) is taken after this acceptance is read.
## PRICE-FILE NAME MATCHING - OUTCOME - Oct 6 2026
ACCEPTED.  base 2026 4: 7 surname matches, each one on each side - Kenny Gainwell = Kenneth Gainwell TB RB, Chris Brooks = Christopher Brooks GB RB, Bam Knight =
   Zonovan Knight ARI RB, Nick Singleton = Nicholas Singleton TEN RB, Hollywood Brown = Marquise Brown PHI WR, Joshua Palmer = Josh Palmer BUF WR, Matt Hibner =
   Matthew Hibner BAL TE; ISSUED candidates on slate teams without a price row 0 (was 4); ELIGIBLE RB 70, TE 78, WR 118 (were 68, 77, 117).  BASE unchanged:
   E[DK] 171.11, same nine.  witness-check witness_v1: the 2 declared files CHANGED (the match column), the other 8 IDENTICAL.  Kit size 68246 AST nodes.
   Then: freeze witness_v2 2026 4 (the current-product witness from here).
## PROSPECTIVE PROTOCOL - DATA FOR 2026 WEEK 6 - REGISTRATION - Oct 6 2026 (before the fetch)
The first prospective issue is 2026 week 6, frozen before its first kickoff (freeze prospective_2026_w6) and scored only after its games.  Its inputs: the 2026
   play-by-play through week 5 and the week 6 DraftKings Classic price file.  Facts hold 2026 weeks 1-4 now.  The 2026 outcomes enter the facts for issuing; laws
   remain fit on seasons < 2026, and no 2026 week 4+ outcome enters research, a wall or a verdict (owner ban).  Scoring 2026 weeks 1-4 against the replay path is
   a separate report labelled RETROSPECTIVE TEMPORAL HOLDOUT, never used for promotion.  No prospective result changes a model without a separately registered cycle.
This step: kit.py fetch 2026 6 without --dk-group - the 2026 nflverse files into data/ (its own checks: one season, same columns, weeks never shrink) and the lobby's
   NFL Classic draft groups listed; no price file written.  The draft group is chosen from that list next (the main Sunday slate).
## PROSPECTIVE PROTOCOL - CORRECTION - Oct 6 2026 (before any price file)
The registration above named 2026 week 6 with play-by-play through week 5.  Wrong week: the fetch shows the 2026 nflverse files now hold weeks 1-4 (stats 4379 rows,
   pbp 10979, snaps 5876), week 5 has not started, and the lobby's next NFL Classic draft group is week 5 - 154467, Thu-Mon, 15 games, first kickoff
   2026-10-08 20:15 ET.  Owner's choice: that group.  The first prospective issue is 2026 week 5: inputs through week 4 and DK_2026_w5.csv from group 154467,
   frozen as prospective_2026_w5 before 2026-10-08 20:15 ET and scored after its games.  Everything else in the registration stands.
This step: kit.py fetch 2026 5 --dk-group 154467 --no-nflverse (writes the price file and its raw JSON), then the guard lists the raw files added or changed since
   the manifest (the nflverse 2026 files moved into data/ by the last fetch, and these two).  accept follows only after that list is read.
## DISPERSION WALL (NB1) - REGISTRATION - Oct 6 2026 (before the run)
Why (the atlas, M3 replay): TOO NARROW - RB carries (below P10 21.1%, above P90 21.4%), RB targets 14.7 / 15.1, RB receptions 14.1 / 15.1, TE receptions 12.0 / 15.7,
   Q1 attempts 22.3 / 23.1; Q2, Q3 and F8 QB below them.  Walk-down: every one is a layer-0 law with no fitted spread (Poisson); the fitted-spread cells (WR
   receptions NB, WR targets beta-binomial, QB carries NB) are near 10 / 10.  The spread was decided by which family a cell happened to carry, not by the rows.
Measured shape (variance-function read, atlas rows, (y - mu)^2 = a mu + b mu^2): b <= 0.02 in every count cell, mostly negative - excess variance linear in the
   forecast, not quadratic; mean (y - mu)^2 / mean mu: RB carries 2.80, Q1 attempts 3.64, RB targets 1.60, RB receptions 1.48, TE receptions 1.48, WR receptions 1.40,
   QB carries 1.58, TDs 0.88 to 1.00.  Family read (card 2026 w4, final laws): nonzero-state layer 0 Poisson - F5 carries RB, F5 receptions RB / TE, F5 targets RB,
   Q1 attempts, Q4 passing TDs, QB rushing TDs; negative binomial - F5 receptions WR, F5 TDs TE, QB carries.
Procedure, one for every such cell (no pooling; one procedure per term x position): phi_s = laws.dispersion_ratio - the Pearson ratio mean((y - mu)^2 / mu) over the
   cell's nonzero-state spine rows of seasons < s, mu the forecast center v1; the law: negative binomial with the row's mean and size mean / (phi_s - 1), so
   Var = phi_s x mean; phi_s <= 1 is the Poisson boundary (an identical law, gain exactly 0 under exact scores).  Scope read from the replay: final layer-0 Poisson or
   negative binomial laws on nonzero-state rows; F5 TDs RB / WR (final layer 3, a different center) and the share, support, hurdle and conditioned families are outside.
Judgment (kit.py dispersion-wall, judged once): tests 2021, 2023, 2024, 2025; incumbent and challenger scored by draws.exact_crps at each row's outcome; per season the mean
   over slates of incumbent - challenger; EARNED iff the mean of the season means > 0.  Refused, with no verdict written, if any row's law mean differs from its
   spine center v1.  Writes proj/dispersion_verdicts.csv (phi and gain per season, rows hashed); promotes nothing.  Integration is a separate registered transaction,
   and Q2 / Q3 are read conditionally on the integrated Q1 before any child wall.
Pre-stated anti-drift line: if this passes, the TOO NARROW count cells above can become DECISION-QUALIFIED and Q2, Q3 and F8 QB widen through the chain.
## DISPERSION WALL - FIRST RUN REFUSED; LEDGER ADVANCED PAST A FAILING GUARD - CORRECTION - Oct 6 2026
Dispersion wall: refused as registered - law mean vs spine center v1 on 28383 scored rows, 21 differing; no verdict written, nothing promoted.  Cause not measured:
   the check counted a row with no spine row at its key, term and position (center missing) the same as a row whose center differs.  dispersion-wall now prints
   the differing rows by cell, split into those two kinds, before it refuses; the registered rule stands and the wall runs again unchanged in substance.
Ledger: the same script ran ledger-advance after a guard that FAILED (raw files added 2, changed 6 - the week 5 price file and the 2026 nflverse files, pending
   accept), and the ledger accepted 24 lines (the week 5 correction and the dispersion registration).  Those lines are as written; the defect is the order.  Cause:
   the scripts called ledger-advance unconditionally.  Remedy: kit.py ledger-advance now runs the guard itself and refuses when it fails.
## PROSPECTIVE 2026 WEEK 5 - DATA ACCEPTED AND THE ISSUE - REGISTRATION - Oct 6 2026 (before the run)
Raw files read before accept (guard): added 2 - sources/raw/dk_weekly/DK_2026_w5.csv (771 players, 15 games) and DK_2026_w5_154467.json; changed 6 - data/
   games_2026, injuries_2026, pbp_2026, rosters_2026, snaps_2026, stats_2026 (the fetch's own checks: one season, same columns, weeks 1-3 -> 1-4, never shrinking;
   games and injuries weeks unchanged).  Nothing else.  accept, then facts.
Leak check (fixed now): with week 4's outcomes now in the facts, the week 4 product reads only through week 3, so atlas, issue, card and base 2026 4 rebuilt from the
   new facts must equal witness_v2 in every file (none declared).
The issue: issue, card, market-check and base 2026 5 on the accepted code.  Acceptance: the guard passes; witness-check witness_v2 ACCEPTED; card, market-check
   and base ACCEPTED.  The freeze prospective_2026_w5 is taken after this outcome is read, before 2026-10-08 20:15 ET.
## DISPERSION WALL - SECOND RUN REFUSED; SCOPE CORRECTION - Oct 6 2026 (before the next run)
Measured (dispersion-wall with the split): 28383 scored rows, 21 differing - all 21 have no spine row at their key, term and position (F5 TDs TE 2, F5 receptions
   RB 2, TE 11, WR 4, F5 targets RB 2); rows with a different center 0.  Wherever a spine row exists, the law mean is the spine center v1.  The 21 are issue-path
   rows routed to a position the recorded spine has no row for (the same kind as the zero-state check's 78).
Correction (before any verdict): a row with no spine row has no center phi could be fit around, so it is outside the judged scope - counted per cell, not scored;
   a differing center on a row that has one still refuses the wall.  Nothing else changes: procedure, scope rule, exact scores and the earning rule as registered.
   Integration, if any cell earns, states how the out-of-scope rows are treated before it runs.
## PROSPECTIVE 2026 WEEK 5 - ISSUE OUTCOME, LEAK CHECK REFUSED, DISPERSION VERDICTS - Oct 6 2026
Data: accept (763 raw files); facts rebuilt (DST 98.4%, skill 99.6% exact; 142593 player-games); guard passed; ledger 4557.
Leak check REFUSED: atlas, coverage, week 4 law rows, DST card, frozen draws and the BASE lineup reproduce witness_v2 IDENTICAL; three files differ -
   card_2026_w4_candidates.csv 15 of 517 rows (RB 5, TE 1, WR 9), card_2026_w4.csv 82 of 2458 rows (all rows of 5 RB and 6 WR players), slate_pool_2026_w4.csv
   2 of 729 rows.  Laws and draws did not move, so the change sits in what the card merges from the candidate rows; which columns is not yet measured - read below.
   Until measured, the week 4 product is NOT shown free of week 4 information.  The week 5 issue is unaffected in one respect only: no week 5 data exists yet.
Week 5 issue (inputs through week 4, group 154467): candidates 480 - ISSUED 340, short history 86, UNRESOLVED POSITION 54; stat rows 2549, DECISION-QUALIFIED 344;
   market-check W1 / W2 PASS; BASE E[DK] 156.14, salary $49,900, 6 games (Allen, K. Williams, Irving, Lamb, Flowers, Raymond, Kittle, Mayer, Raiders); 7 surname
   matches; ISSUED without a price row 1 (KhaDarel Hodge SF).  Freeze prospective_2026_w5 follows now, before 2026-10-08 20:15 ET.
Dispersion wall verdicts (judged once; promotes nothing): EARNED 3 - F5 receptions RB (phi 1.83-1.99), F5 targets RB (1.85-2.06), QB rushing TDs (1.19, then
   1.00 / 0.96 / 1.00: three seasons are the Poisson boundary, gain exactly 0; earned on 2021's +.0039 alone).  FAIL 7 - F5 carries RB (phi 5.58-6.75; gains
   +.034, -.063, +.033, -.046), Q1 attempts (6.71-9.54; -.308, -.091, -.002, +.023), F5 receptions TE, F5 receptions WR, QB carries, Q4 passing TDs, F5 TDs TE.
   Reading, not a verdict: the registered estimator, the mean of (y - mu)^2 / mu, gives RB carries 5.6-6.8 and Q1 6.7-9.5 where the variance read's ratio of
   means gave 2.80 and 3.64 - low-forecast rows carry large ratios and the excess variance is concave in mu (b < 0), so one phi from the mean of ratios over-widens
   the high-volume rows that dominate these cells.  FAIL cells keep their incumbents; nothing is re-judged.  21 rows outside the judged scope (no spine row).
## PROSPECTIVE 2026 WEEK 5 - FROZEN; LEAK READ; PROVENANCE CHECK - REGISTRATION - Oct 6 2026
Frozen: prospective_2026_w5 at 2026-10-06T11:45:03Z (first kickoff 2026-10-08 20:15 ET), 10 files, CHARTER 4579 lines 23bd96e4.  This freeze is the first
   prospective issue; the producer's "DRY RUN - not prospective" banner inside the files is its default label and is not rewritten (the files are frozen as issued).
Leak read (witness_v2 vs the rebuilt week 4 product): the only differing column is the display name - 15 candidates (e.g. Chigoziem Okonkwo -> Chig Okonkwo,
   D.K. Metcalf -> DK Metcalf, Chris Godwin -> Chris Godwin Jr., Kenneth Walker -> Kenneth Walker III), carried into the 82 card rows of those players; and the
   slate pool's match column on 2 rows (Kenny Gainwell, Chris Brooks now join by name and team instead of by surname).  No law, draw, P(plays), eligibility,
   expected point or lineup moved.  Defect, small but real: a candidate's display name is taken from data past week N-1, so week N's facts reach a label.  The fix
   (the name as of the player's last row through week N-1) is registered separately; until then names on a card may differ from a later rebuild, forecasts may not.
Provenance gap: the freeze's kit digest (f16cd79e) is the code at freeze time; the week 5 files were produced before ssot_dispersion2.zsh changed draws.py (the
   dispersion wall only, not on the issue path).  Check (fixed now): issue, card, market-check and base 2026 5 rebuilt on the frozen kit, then witness-check
   prospective_2026_w5 with nothing declared - every file IDENTICAL, or the freeze is recorded as not reproducible by its recorded code.
## PROSPECTIVE 2026 WEEK 5 - PROVENANCE CHECK ACCEPTED; THE SCORING RULE - REGISTRATION - Oct 6 2026 (before any week 5 outcome exists)
Provenance: issue, card, market-check and base 2026 5 rebuilt on kit f16cd79e; witness-check prospective_2026_w5 - all 10 files IDENTICAL; guard passed.  The frozen
   week 5 issue reproduces from its recorded code.  It stays immutable; research proceeds in the working tree, and witness-check guards the frozen copy.
Scoring rule, fixed before the outcomes (kit.py score-freeze NAME): label from the record - PROSPECTIVE iff frozen_at precedes the slate's first kickoff (the price
   file's Game Info), else RETROSPECTIVE TEMPORAL HOLDOUT.  Outcomes: stat terms from the issue path's spine rows of the week, graded on played rows (laws are given
   he plays); F8 from dk_points on played rows; DK from dk_points with a non-playing player scored 0 (the card's DNP = 0); DST from the team's DST points.  Per row
   of the frozen draws: CRPS, randomized PIT, below the draws' P10, above their P90; read by atlas qualification and by cell; the frozen BASE lineup's actual total
   beside its expected.  Refused while the week has no outcome rows.  A reading only: never used for promotion; no model change on it without a separately
   registered cycle; week 5 outcomes do not enter research.
Run now: score-freeze witness_v2 - 2026 w4, issued from data through week 3, frozen after its games, so RETROSPECTIVE TEMPORAL HOLDOUT; and score-freeze
   prospective_2026_w5, which must refuse (no week 5 outcomes yet).
## SCORING - FIRST RUN DEFECTIVE - CORRECTION - Oct 6 2026 (week 4 holdout; no week 5 outcome exists)
The first score-freeze witness_v2 was wrong in two ways; its numbers are void.  (1) Stat outcomes came from the issue path's spine rows, which carry no week-N
   outcome - 1571 stat rows "no outcome on disk", none scored; only DK, DST and F8 rows were.  (2) A player whose team's game is not in the facts was treated as
   not playing: the three New Orleans players of the BASE lineup (Shough, Olave, J. Johnson) were scored 0 under DNP = 0, so "actual 72.70" is not a lineup score.
Corrected rule (the registered rule otherwise unchanged): a row is scored only when its team's game is on disk (a team-game row of the week with points); stat
   outcomes come from facts' columns by one map (draws.TERM_COLUMNS: F5 TDs = rushing + receiving TDs, Q5 = passing interceptions, the rest one column each),
   witnessed before use against the recorded spine's latest season - any differing row refuses the scoring.  Rerun now on witness_v2 (RETROSPECTIVE TEMPORAL
   HOLDOUT) and on prospective_2026_w5 (must refuse).
## SCORING - OUTCOME MAP REFUSED; CAUSE AND CORRECTION - Oct 6 2026 (week 4 holdout; no week 5 outcome exists)
The map witness refused as registered: recorded spine 2025, 23203 played rows, 2077 differing.  Measured cause (map read): every differing row has the spine at 0
   and the facts column missing - played rows with no box-score record (F5 RB 31 per term, TE 225, WR 150; QB 2) - and no row with both present differs.  The
   spine records such rows as zeros under state.box_zero (BOX-SCORE ZEROS UNDER D: only when wholly absent, on the field, 0 DK points; anything partial refuses).
Correction (before any scoring): score-freeze takes outcomes through draws.box_outcomes - state.box_zero on the played rows, the spine's own rule, one producer -
   for the map witness and the scored week alike.  Everything else as registered.  Rerun: witness_v2 (RETROSPECTIVE TEMPORAL HOLDOUT); prospective_2026_w5 refuses.
## WEEK 4 DATA COMPLETED; THE WEEK 5 ISSUE OF RECORD; THE COMPLETENESS GATE - Oct 6 2026 (before any week 5 game)
Data (owner's commands, outside a registered script; recorded here): fetch 2026 4 - stats 4379 -> 4449, pbp 10979 -> 11155, snaps 5876 -> 5970 rows, weeks 1-4
   unchanged (Monday night's ATL @ NO game); guard listed 5 changed data/*_2026 files and nothing else; accept (763 raw files); facts rebuilt (DST 98.4%, skill 99.6%).
Week 4 holdout rescored on complete data (RETROSPECTIVE TEMPORAL HOLDOUT, never for promotion): scored 2330 of 2490 rows, unscored 160 (did not play), none
   missing a game.  DECISION-QUALIFIED 312 rows: PIT mean .522, above P90 .080, bias +.001.  TOO NARROW 482: below P10 .106, above P90 .168.  CENTER TOO LOW 847:
   bias -.818.  Q1 attempts 25: .160 / .280.  F8 WR 124: .121 / .177.  BASE lineup 123.14 actual vs 171.11 expected, 9 of 9.  The earlier 72.70 was a partial total.
The week 5 issue of record is prospective_2026_w5, as frozen.  It was issued before the ATL @ NO week 4 game reached the facts, so its Falcons and Saints players
   lack that game; that gap is part of what was issued and is scored with it.  No second week 5 freeze is taken: choosing between two issues is a choice the
   record should not offer.
Root fix, for every later week: laws.issue refuses while any scheduled team-game of the season before week N has no plays on disk, naming the games.  Check now:
   issue 2026 6 must refuse, naming the week 5 games.
## PROVENANCE ROOT - FIVE WHYS, COHESION, AND THE DELETIONS - Oct 6 2026
Five process defects, five whys each: (1) a script continues past a refusal - acceptance is printed, not recorded; (2) a freeze cannot show which code produced its
   files - production is not recorded; (3) data acceptance enters the CHARTER by hand afterwards - the record is narrated, not emitted; (4) display names come
   from rows past week N-1 - the cutoff is each consumer's habit, not the source's construction; (5) the scorer's below-P10 cannot happen on a count with P10 = 0 -
   a measure was defined twice.  Convergent root: the kit verifies what was produced, never how; lineage (code, inputs, cutoff, definition, acceptance) is not data.
Cohesion (the order each layer depends on): the as-of-week-N-1 view of facts first - without it an input digest records a leak faithfully instead of preventing it;
   one producer per measure second - without it a recorded verdict has no fixed meaning; the kit-written event log third - it records digests of (1) and verdicts of
   (2); consumers that read events fourth (freeze needs ACCEPTED events of the same code and inputs, accept writes its own changed-file list); the CHARTER last, the
   narrative citing events.  Goal served: prospective scores accumulate with lineage, so a DECISION-QUALIFIED claim is earned evidence, not a trusted run.
Static map: evaluate.name_resolution_check joins the guard - every name a module reads is bound in it or a builtin; every name imported or read off a kit module is
   defined at that module's top level.  On the code before any deletion: 13 modules, all resolve.
Deletions now, before their rebuild (the kit is red until the rebuild): cards.py's name lookup from the latest row (root 4) and score-freeze's private measures
   (read_rows, below / above the draws' quantiles; root 5).  Predicted map, fixed before the guard runs: exactly cards.py names (the candidate name assignment) and
   draws.py read_rows (the two report loops) - 3 references, nothing else.  Not visible to a static map: data that crosses a file - the candidate name reaches
   optimize's price-file match through card_SEASON_wWEEK_candidates.csv; witness-check is the instrument for that path.
## PROVENANCE ROOT - DELETION MAP CONFIRMED; LAYERS 1 AND 2 REBUILT - REGISTRATION - Oct 6 2026 (before any week 5 game)
Deletion map: the guard's name resolution found exactly the predicted 3 references (cards.py:39 names; draws.py:545 and :547 read_rows), nothing else; the guard
   failed and ledger-advance refused, as the new rule requires.
Layer 1, the as-of view: facts.load_as_of(season, week) - player rows of earlier seasons and of the season's weeks < N, the one cut.  cards.card reads through it
   for the display name and for the earlier-played counts (its own cut retired).  Other issue-path consumers keep their own cuts for now and move one by one,
   each witnessed.  Acceptance: facts rebuilt; issue, card and base 2026 4 rebuilt; witness-check witness_v2 with nothing declared - all 10 files IDENTICAL (the
   week 4 card again names its players as of week 3, and the price-file match column returns to its frozen values).
Layer 2, one producer per measure - the scoring rule amended before the week 5 games: score-freeze grades each frozen row with draws.grade (the atlas's grading:
   randomized PIT on the atlas rank stream, CRPS, bias, quantiles) and reads it through evaluate.atlas_cells (the atlas's measures: PIT <= .10, PIT > .90 from
   coverage_90, CRPS, bias), by frozen atlas qualification and by atlas cell (term, position, the card's law state).  The strict below-P10 / above-P90 counts are
   gone; ties on count laws are split by the randomized PIT as in the atlas.  Everything else in the scoring rule stands.  Rerun on witness_v2 (RETROSPECTIVE
   TEMPORAL HOLDOUT).  Layer 3, the kit-written event log, is the next transaction.
## PROVENANCE ROOT - LAYER 1 ACCEPTANCE REFUSED; LAYER 2 RAN; THE LEDGER STILL ADVANCED - Oct 6 2026
Layer 1 REFUSED as registered: witness-check witness_v2 - atlas, laws, frozen draws, DST card and lineup IDENTICAL; card_2026_w4_candidates.csv 12 of 517 rows
   differ (RB 5, WR 7; was 15), carried into 82 card rows; slate pool 2 rows.  Reading the week 4 card through facts.load_as_of(2026, 4) did not restore the frozen
   names.  Unmeasured: why rows of weeks 1-3 now carry other names - read below.
Layer 2 ran: score-freeze witness_v2 on draws.grade and evaluate.atlas_cells - RETROSPECTIVE TEMPORAL HOLDOUT, 2330 scored.  By frozen label (PIT <= .10 / > .90):
   DECISION-QUALIFIED 312 rows .093 / .167; TOO NARROW 482 .145 / .183; CENTER TOO LOW 847 .099 / .138 (bias -.82); CENTER TOO HIGH 34 .147 / .000 (+1.37);
   MISCALIBRATED 266 .117 / .113.  Reading: external diagnostic support for the atlas labels' directions on one held-out week, not requalification; rows within a
   slate are dependent.  Monitoring hypothesis for the prospective ledger (W5 on), not a wall: DECISION-QUALIFIED cells under-cover the upper tail in 2026.
Process: the guard passed and the ledger accepted 27 lines while a registered acceptance printed REFUSED - root 1 exactly (acceptance printed, not recorded); the
   accepted lines are the registration and stand; this entry is the outcome.  Layer 3 (kit-written events read by later commands) closes it.
## PROVENANCE ROOT - SOURCE REVISION MEASURED; LAYER 3 (EVENTS, ARCHIVE) - REGISTRATION - Oct 6 2026
Read: all 12 differing candidates' week 1-3 rows now carry the new names (DJ Moore, Kenny Gainwell, Chris Godwin Jr., Deebo Samuel Sr., AJ Dillon, DK Metcalf,
   DeMario Douglas, Chris Rodriguez Jr., KaVontae Turpin, Chris Brooks, Kenneth Walker III; John Metchie both spellings).  nflverse republishes the season's earlier
   weeks with current values on every fetch: a cut by week label removes later rows but not later revisions of earlier rows.  The information set before week N
   is the raw vintage accepted before the issue, not the newest bytes with later weeks dropped.  Layer 1's acceptance is closed with this cause: witness-check
   witness_v2 with card_2026_w4.csv, card_2026_w4_candidates.csv and slate_pool_2026_w4.csv declared (display names revised at the source, 12 players), every
   other file IDENTICAL.
Layer 3: kit.py's main records every command in proj/events.jsonl - time, command, exit (0 accepted), kit code digest, accepted raw manifest before and after, and
   the content digest of every file it wrote under proj/ and facts/; refusals by SystemExit are recorded with exit 1.  freeze refuses unless every product file,
   as it is now, is the output of an accepted event of the current code and the current raw manifest.  accept keeps every raw version in archive/ by its SHA-256
   (a copy) and archives the manifest itself, so every accepted vintage is reconstructible; it prints what was added, changed and removed.  Scripts begin with
   setopt err_exit: a refusing step stops the script.
Not yet: reading a past vintage on the issue path (facts built from the manifest accepted before the issue time).  Until then a rebuild after a source revision
   may differ in revised fields, and a witness declares them with the measured cause.
Run now: accept (archives the 763 accepted files; manifest unchanged), the declared witness-check witness_v2, ledger-advance.
## BOX SCORES - SOURCE OF RECORD AND THE PLAY-BY-PLAY CROSS-CHECK - Oct 6 2026
Measured: box scores rebuilt per game from play-by-play (rushes; targets as pass attempts with a receiver, sacks excluded; passes, sacks excluded; two-point tries
   excluded; lateral yards credited to the player who gained them) against the stats file, every column: 2019 0 of 5243 player-games differ, 2020 3 of 5430, 2021
   3 of 5679, 2023 1 of 5636, 2024 12 of 5581, 2025 2 of 5628, 2026 2 of 1263 - 23 of 34,460 (0.07%), only yards and TDs.  Of 2025's first 18, 16 were lateral
   yards (rule fixed); the 2 left (D. Moore w15 +4, M. Pittman w18 -9) have play-by-play agreeing with its own play descriptions and the stats file not.
Owner's ruling: the stats file stays the source of record (the official, corrected stats DraftKings scores from; no history changes); play-by-play cross-checks it.
   facts.pbp_box_crosscheck runs inside kit.py facts: every differing value to facts/pbp_crosscheck.csv, counts per season in the facts report - a reading, not a gate.
   Display names are not a forecast input; they remain only the price-file join's key, read through the as-of view, with source revisions measured by witness-check.
## DISPERSION WALL - INTEGRATION - REGISTRATION - Oct 6 2026 (operational gate; before the run)
Change: build_inputs reads the EARNED cells (F5 receptions RB, F5 targets RB, QB rushing TDs); fit_state carries phi_s = laws.dispersion_ratio per earned cell;
   row_laws adds a layer-5 law "negative binomial", size mean / (phi_s - 1), provenance "dispersion wall NB1 (earned)", on each earned cell's layer-0 nonzero
   Poisson / negative binomial rows where layer 0 is final, only when phi_s > 1 (at or below 1 the incumbent Poisson is the law: QB rushing TDs in three of four test
   seasons).  It draws on its own keyed substream ("dispersion wall").  Rows with no spine row (outside the judged scope; RB receptions 2, RB targets 2 in the
   replay) receive the law too: phi is a cell parameter fit on the cell's spine rows and needs no center of the row it is applied to.  Promoted layers (4, 5) are
   set aside in every v0 witness (M1, A2').  draws.dispersion_scope is the one scope rule for the wall and its check.
Operational gate (fixed now): issue-check (M1) and replay (A2') ACCEPTED on v0 rows with promoted layers set aside; draws-check (M2) ACCEPTED; dispersion-check: per
   EARNED cell the judged rows, rows_sha256 and every season gain within 1e-12; atlas; issue, card, market-check and base 2026 5 ACCEPTED; guard passes.  Then freeze
   witness_v3 2026 5 - the current-product witness from here (prospective_2026_w5 stays the issue of record, untouched).  Reported, not gated: the atlas
   qualification changes against witness_v2's atlas, and DECISION-QUALIFIED issued stat rows.
## DISPERSION WALL - INTEGRATION - OUTCOME AND CORRECTION - Oct 6 2026 (operational gate; registered before the rerun)
Outcome of the registered run: M1, A2', M2, dispersion-check, atlas, issue 2026 5 and card 2026 5 ACCEPTED; market-check 2026 w5 W1 PASS, W2 (reproduction from
   the issue path) FAIL -> M7 MARKET REFUSED.  Nothing was frozen; the ledger did not advance.  The gate did its work: the frozen draws did not reproduce.
Mechanism (read from code; not yet witnessed on the subject): row_laws appended the layer-5 rows cell by cell in the iteration order of fitted_state["dispersion"],
   a dict built from DSPEARN, a set of (term, position) string tuples.  A string set's order follows the process's hash seed, so the card process and the
   market-check process can lay the same rows out in different orders; draws are keyed per row, so values agree and only the order (keys array) differs.  The three
   earned cells take four distinct orders across hash seeds 1-6 in a plain Python process (Oct 6 reading).  No other fit_state set is iterated into an output
   (ZSEARN feeds a dict read by key from the zero-state block, which iterates the rows' own groupby order).
Correction: the dispersion block iterates the layer-0 nonzero Poisson / negative binomial rows' own groupby(term, position, sort=False) order and reads phi by key -
   the zero-state wall's form.  Same rows, same laws, same sizes; only the order is now the data's.
Gate (fixed now): issue-check, replay, draws-check and dispersion-check ACCEPTED; issue and card 2026 5 under PYTHONHASHSEED 11; market-check 2026 5 ACCEPTED
   under each of PYTHONHASHSEED 1, 2 and 3 (three processes, three seeds, each reproducing the card's frozen draws); base 2026 5; guard; then freeze witness_v3
   2026 5.  A FAIL under any seed refutes the mechanism as the whole cause and stops the run.
## ISSUE OF RECORD - DERIVED - REGISTRATION - Oct 6 2026 (before any week 5 kickoff; supersedes the week 5 issue-of-record line in prose)
Five whys on "which week 5 freeze is scored?":
   1 Why ask?  prospective_2026_w5 and witness_v3 were both frozen before the first kickoff; score-freeze would label either PROSPECTIVE.
   2 Why can both qualify?  The PROSPECTIVE label is derived (frozen_at < first kickoff), but the thing scored was a NAME a person passed to score-freeze.
   3 Why does a person pass it?  "Issue of record" was a fact with no producer: it lived in CHARTER prose, and code never read it.
   4 Why no producer?  freeze writes snapshots; it never says which snapshot is the week's forecast.  Witnessing and issuing were one act told apart only by a name.
   5 Why does that matter?  An issue picked by a person can be picked after the outcomes; one fact with no producer is how "score whichever looks better" gets in.
   Root: one producer per fact was never applied to the week's forecast.  Remedy: derive it, so that no one, Claude included, chooses it.
Socratic choice of the rule:  Can a choice made before the first kickoff use outcomes?  No; so any rule fixed now is honest, and the question is which rule serves
   the goal.  What is the goal?  To measure the forecast that would be acted on.  Which freeze is that?  The last one before kickoff; an earlier freeze that was
   superseded measures a product nobody plays.  Does "last" invite late tinkering?  Only before kickoff, when there are no outcomes to tinker toward; at kickoff
   the week is locked by the rule itself, with no declaration needed.  Does it hold every week?  It reads only meta.json (season, week, frozen_at) and the price
   file's first kickoff; it needs no name, no flag and no prose.
Rule: the issue of record of (season, week) is the last freeze of that week frozen before the slate's first kickoff.  An earlier freeze is an AUDIT WITNESS
   (superseded before kickoff).  A freeze at or after kickoff is not prospective.  Neither is ever scored.  No freeze before kickoff -> no prospective issue; nothing scored.
Change: draws.week_freezes / issue_of_record / score_week replace score_freeze(NAME); kit.py issue-of-record SEASON WEEK (a reading) and score-week SEASON WEEK.
   score-freeze NAME is removed: no command scores a named freeze.  Scored files are proj/score_SEASON_wWEEK.*.  Earlier score_witness_* files stay as the record
   of the week 4 RETROSPECTIVE TEMPORAL HOLDOUT, already read.
Consequence for week 5, by the rule: witness_v3 (13:03:29 UTC) is the issue of record; prospective_2026_w5 (11:45:03 UTC) is an audit witness, never scored.
Gate (fixed now): guard passes; ledger advances; issue-of-record 2026 5 prints witness_v3 ISSUE OF RECORD and prospective_2026_w5 AUDIT WITNESS;
   issue-of-record 2026 4 prints every freeze AFTER THE FIRST KICKOFF.
## CONDITIONAL VARIANCE OWNERSHIP READ and F8 COMPOSITION READ - REGISTRATION - Oct 6 2026 (readings; promote nothing; no week 5 law changes - witness_v3 is the issue of record)
Refactor (one producer): draws.composed_components returns the composed skill components (position, form, keys, the four COPULA_TERMS matrices after the earned
   order); compose_slate passes them through skill_dk exactly as before.  Gate: draws-check (M2) ACCEPTED (its composition witnesses unchanged) and market-check
   2026 5 W2 PASS (the frozen draws of the issue of record reproduce through the refactored path).
Variance read (Var(Y | X), not Var(Y | mu)): cells = every atlas cell NOT QUALIFIED - TOO NARROW, read from proj/atlas.csv (none named by hand).  States
   (draws.variance_states, earlier games only): per ROLE column its season-to-date level, |last game - level| and the sd of the previous three played games;
   the team's plays and dropbacks season-to-date level and the sd of its previous three team-games this season.  Per state, the defined rows are split into terciles; per
   tercile the tail share (PIT <= .10 or > .90; honest .20) and the residual mean square share.  OWNED iff the end terciles' tail shares differ by more than 3
   binomial SE and the lower end's excess over .20 is at most half the higher end's.  A cell with no owner: NOT OWNED.  Its conditional-variance route closes and no
   variance family is tried there.
Composition read: on the M3 replay, every played RB / WR / TE player-week with four composed components and four recorded outcomes; per position and form the
   law second moments (composed draws) vs the realized r r'; realized / law variance per component; both correlation matrices; DK-linear variance (w = 1, .1, .1, 6)
   split into diagonal and off-diagonal parts; eigen decomposition of the DK-weighted realized - law matrix.  The 100-yard bonuses lie outside w.
Also read: the 2026 w4 price file's Game Info dates (issue-of-record put w4's first kickoff at Sun Oct 4 13:00 ET; a Thursday game would mean the price file
   is a partial slate and first_kickoff is the slate's, not the week's).
## CONDITIONAL VARIANCE OWNERSHIP READ - CORRECTION - Oct 6 2026
variance-read stopped before its first cell: the tail column was named "tail", and rows.tail is pandas' DataFrame.tail method (AttributeError).  The column is now
   "in_tail", read by key.  Nothing else changes; the registered definitions and the OWNED criterion stand as registered.  Rerun: variance-read, composition-read and
   the 2026 w4 price file read.
## YARDS GIVEN COUNT WALL - REGISTRATION - Oct 6 2026 (genuinely new wall; registered before the run; judged once; promotes nothing; no week 5 change - witness_v3 is the issue of record)
Evidence (composition-read, Oct 6): the composition draws yards independent of their count.  WR receptions x receiving yards: law correlation +0.000, realized +0.772;
   TE: law +0.169 (copula) / -0.001 (independent), realized +0.807 / +0.809; RB rushing yards x TDs: law +0.001, realized +0.358.  DK-linear variance realized / law:
   WR 1.513, TE 1.301 / 1.529, RB 1.276, nearly all of it off-diagonal.  variance-read: WR F8 is too wide in the low-usage tercile (.14) and too narrow in the high (.37) -
   the shape of yards whose spread ignores the count.
Not a re-judgment: work order 31 L2 for WR (HARNESS FAIL, rows a23a9494...) only REORDERED receiving-yards draws (multiset unchanged), so the constant-sd normal marginal
   stayed.  This procedure replaces the draws: yards = n e + sqrt(max(n, 1) v) Z, the multiset changes with n, and n = 0 gives 0 yards.  The family is dependence wall 7's
   (QB passing and rushing yards, earned); the cells are new.
Scope (draws.yards_count_scope, derived from the slate): a yards component of COPULA_TERMS whose count (YARDS_COUNT: receiving yards <- receptions, rushing yards <-
   carries) has law rows at the position, excluding a component an earned order already couples (receiving yards where L2 is earned).  Expected from code: RB rushing
   yards; WR and TE receiving yards.
Procedure, per test season s and row: n = the composed count draws (receptions after the earned order or copula; carries); e = yards law mean / count law mean (the
   center is kept); v = draws.yards_count_variance on seasons < s; Z on the row's own substream "yards given count wall".  In scope: both laws nonzero with finite means
   and a positive count mean, played, F8 and yards outcomes recorded.
Judgment: row_crps (the atlas's instrument) on F8 and on the yards component, incumbent = the issued composition.  Per season the mean over slates of incumbent - challenger.
   EARNED iff BOTH the F8 and the yards mean season gains are positive (R-GATE).  Refused before any verdict if an incumbent F8 score differs from proj/atlas_rows.csv.gz.
   Reading beside it: F8 tail share, incumbent vs challenger.
Also read: facts/game.csv.gz gameday / gametime for 2026 w4 (whether the week had a game before the price file's first, Sun 10/04 1:00 PM).
## YARDS GIVEN COUNT WALL - OUTCOME - Oct 6 2026
EARNED 3 of 3; every season gain positive on both F8 and the yards component.  TE receiving yards: 3712 rows, F8 +0.040 / +0.031 / +0.035 / +0.024, yards +0.66 / +0.53 /
   +0.55 / +0.48, F8 tail share .196 -> .177.  WR receiving yards: 6454 rows, F8 +0.114 / +0.128 / +0.103 / +0.128, yards +1.24 / +1.53 / +1.20 / +1.35, tail .251 -> .155.
   RB rushing yards: 3735 rows, F8 +0.045 / +0.049 / +0.044 / +0.064, yards +0.94 / +1.00 / +0.92 / +1.20, tail .209 -> .215.  Incumbent F8 = atlas_rows on all 13901 rows.
   Monitored after integration: WR F8 tail .155 sits below .20 (wider than honest in aggregate) - the atlas reads it by cell.  Nothing promoted; integration is its
   own registered transaction (week 6 onward; witness_v3 stays the week 5 issue of record).
## FIRST KICKOFF FROM THE SCHEDULE - CORRECTION - Oct 6 2026 (before any week 5 kickoff)
Defect: draws.first_kickoff read the price file, whose slate can omit games.  2026 w4: the price file began Sun 10/04 1:00 PM; facts/game.csv.gz shows PIT@CLE Thu
   10/01 8:15 PM and IND@WAS Sun 9:30 AM.  A freeze between Thursday and Sunday would have been labelled prospective after a game of the week was played.
Correction: facts.schedule, the one reader of facts/game.csv.gz, schedule columns only (game_id, season, week, gameday, gametime, home_team, away_team; no scores,
   lines or weather).  first_kickoff = the earliest gameday + gametime of the week (nflverse: US Eastern).  Refused when the week has no scheduled games.
Gate: facts rebuilt (facts.py changed; freshness); guard passes; issue-of-record 2026 5 keeps witness_v3 ISSUE OF RECORD and prospective_2026_w5 AUDIT WITNESS;
   issue-of-record 2026 4 prints first kickoff 2026-10-01 20:15 ET with both freezes AFTER THE FIRST KICKOFF.
## YARDS GIVEN COUNT WALL - INTEGRATION - REGISTRATION - Oct 6 2026 (operational gate; before the run; week 5 untouched - witness_v3 is the issue of record)
Change: laws.build_inputs reads the EARNED cells (TE and WR receiving yards, RB rushing yards) as a sorted tuple; fit_state carries their yards_count_variance
   (YARDS_COUNT and yards_count_variance move to laws - one producer for the wall and the issued law).  draws.compose_slate applies them after the earned orders
   (count_yards_components: per in-scope row, yards_given_count on the composed count) and returns (composed, count_yards); the callers that grade or issue (atlas,
   week_draws) merge count_yards over the slate's draws, so the yards stat rows, the frozen draws and the market read the same yards F8 is built from.  The wall's
   own row code now calls the shared count_yards_scope / yards_given_count (its rerun stays refused).  composed_components stays the earned orders only (the
   incumbent; composition-read and the wall read it).
Operational gate (fixed now): issue-check (M1) and replay (A2') ACCEPTED (law rows unchanged); draws-check (M2) ACCEPTED; yards-count-check: per EARNED cell rows equal
   the verdict's, rows_sha256 equal, every F8 and yards season gain within 1e-12 of the judged; atlas regraded; guard passes.  Reported, not gated: atlas qualification
   changes against witness_v3's atlas.
Not run now, by the issue-of-record rule: issue / card / market-check / base 2026 5 (a week 5 freeze before Thu Oct 8 8:15 PM would supersede witness_v3).  The issue
   path's gate runs on the first week issued with this code: card, market-check (W2) and base of 2026 week 6, before any week 6 freeze.
## BATCH 1 - Oct 6 2026 (owner ruling: independent items batched in one script, each gated; err_exit stops the batch at the first failure)
Integration outcome (yards given count): yards-count-check ACCEPTED (3 cells, hashes equal, gains within 2.22e-16); atlas regraded; ledger advanced.  Atlas: WR F8 chain
   TOO NARROW -> CENTER TOO LOW (cov .116 / .866 -> .089 / .898; CRPS 3.2234 -> 3.1122); TE F8 copula CENTER TOO LOW -> TOO NARROW (cov .062 / .873 -> .116 / .881;
   CRPS 2.2242 -> 2.1974).  draws-check (5) and the Y benchmark read q .10 coverage as y <= Q (TE .391, WR .244), the atlas reads randomized PIT (TE copula .116, WR .089):
   the two disagree; read 3 below measures the ties that could separate them.
Item 1 - refactor (one producer): draws.issued_components (composed_components + count_yards_components) feeds compose_slate and composition-read.  Gate:
   yards-count-check ACCEPTED again (compose_slate reproduces the judged challenger).
Item 2 - readings (promote nothing): composition-read of the issued composition; tail-read (new: an atlas cell's PIT <= .10 and > .90 shares by terciles of one
   pregame state) for Q1 attempts QB and F8 QB by snap_share level (which tail the QB regime owns), F8 WR chain and F8 TE copula by dk_points level (width by usage
   after integration); ties: per F8 position, the share of graded rows with outcome = quantile_10, quantile_10 = 0 and outcome = 0.
Not in this batch, and why: (a) QB yards variance onto yards_count_variance - not a pure refactor: the QB wide frame's row set (inner join of every QB term; no count
   state filter for passing) differs from yards_count_variance's, so QB parameters would change; it needs its own wall.  (b) an NB1 phi-estimator wall for RB carries
   / TE receptions - closed: CONDITIONAL VARIANCE OWNERSHIP READ registered "NOT OWNED ... no variance family is tried there".  (c) the short-history prior and (d)
   vintage selection on the issue path - each a design that changes the candidate universe or facts' inputs; each needs its own registration.
## BATCH 1 - OUTCOME, and BATCH 2 - REGISTRATION (readings; promote nothing) - Oct 6 2026
Batch 1: yards-count-check ACCEPTED after the issued_components refactor; ledger 4807.  Ties: graded F8 rows with outcome = quantile_10 - TE .345 (copula and independent),
   WR .195, RB .050, QB .000 - the y <= Q readings (draws-check (5), Y benchmark) count those ties; the atlas's randomized PIT does not.  Issued composition: WR DK-linear
   variance realized / law .888 (law 41.06, realized 36.47; receiving yards .766); TE copula 1.352 and independent 1.503 (receptions x TDs law +.109 / +.001, realized
   +.270 / +.304); RB 1.280 (rushing yards x TDs law +.071, realized +.358).  tail-read: Q1 attempts, lowest snap_share tercile (<= .949) PIT > .90 .388, the other
   terciles .153; PIT <= .10 .215 / .222 / .233.  F8 TE copula by dk_points level: highest tercile .147 / .142.
Batch 2 readings, for the designs they decide: tail-read now also prints mean bias per tercile; residual-read (new): on the recorded spine's test seasons, the residual
   correlation of two terms and their partial correlation given a third.  Run: Q1 attempts QB and F8 QB by snap_share level and by snap_share change (bias - is the low-snap
   excess a center the season-to-date rate holds down); residual-read RB F5 TDs x F5 rushing yards given F5 carries, and given F5 receptions; TE F5 TDs x F5 receiving
   yards given F5 receptions, and F5 TDs x F5 receptions given F5 receiving yards (does a TD order belong on yards or on the count).
## TRUST LADDER - REGISTRATION - Oct 6 2026 (owner ruling: A+, the probabilistic season-to-date empirical reference; definitions fixed before any value is computed)
Ladder per atlas cell: ISSUED -> CENTER USABLE -> WIDTH USABLE -> SKILLFUL VS REFERENCE -> PROSPECTIVE EVIDENCE.  DECISION-QUALIFIED stays the atlas's own label, shown beside.
   CENTER USABLE: the slate share with PIT <= .50 within band of .50.  WIDTH USABLE: the slate share with PIT <= .10 or > .90 within band of .20.  Band = the atlas's rule
   (within +-2 slate SE; evaluate.share_band, now the one producer under coverage_band).
   SKILLFUL VS REFERENCE: reference law = the empirical distribution of the same player's (team's) earlier played outcomes of the same statistic this season, weeks < N,
   given he plays (no information past N-1).  Per row both scored by evaluate.crps (exact for an empirical distribution).  g_s = mean over slates of CRPS_ref - CRPS_kit
   per test season.  PASS iff every test season is present, every g_s > 0, and mean g_s > 0.  CRPSS = 1 - mean CRPS_kit / mean CRPS_ref (shown, not gated).  Rows with
   no earlier played game this season have no reference and are counted, not scored.
   RUNG: 1 issued; 2 iff CENTER and WIDTH both pass; 3 iff rung 2 and SKILL pass (skill never compensates for rung 2).
   PROSPECTIVE EVIDENCE: cumulative from the issue-of-record score files (proj/score_SEASON_wWEEK.csv): frozen weeks, rows, PIT <= .10 / > .90, bias, CRPSS vs the same
   reference.  Shown as evidence ("N frozen weeks"); when the word "validated" applies is registered later, never flipped after one week.
   F8 additionally keeps the Y benchmark (atlas) as a secondary reference.
Every later wall states beforehand which cells it expects to move from rung X toward rung Y and by which of these quantities.
Code: state.team_volume (the frames' team volume, one producer, shared with the team reference); evaluate.share_band; draws.reference_outcomes, reference_crps,
   ladder_cells, ladder (kit.py ladder).  Gate: guard passes (purity covers the frames); ladder's witness - atlas_cells over proj/atlas_rows.csv.gz reproduces proj/atlas.csv
   (qualification and the four coverages), refused otherwise.  The ladder is a reading; it promotes nothing.
## TRUST LADDER - REGISTRATION - CORRECTION - Oct 6 2026 (before any ladder value is computed)
The guard refused the first run: "defined more than once: ladder in ['draws.py', 'evaluate.py']" - evaluate.ladder is the harness's ladder length L.  The trust ladder's
   function is renamed draws.trust_ladder; the command stays kit.py ladder.  Nothing else changes; state.py and evaluate.py as written by that run stand.
## TRUST LADDER - OUTCOME, and BATCH 3 - REGISTRATION - Oct 6 2026 (owner ruling; registered before any batch 3 value is computed; week 5 untouched)
Ladder outcome: witness passed (51 cells, 0 differing); reference rows 109439 of 109439; rung 1: 26 cells (69340 rows), rung 2: 6 (871), rung 3: 19 (39228).
Ladder refinements (readings; no rung changes): rung 3 is named HISTORICALLY SKILLFUL.  Width keeps the total tail rate and adds its two parts, L = share PIT <= .10 and
   U = share PIT > .90, each against .10 by share_band; TAIL BALANCE = balanced iff both within band (shown, not a rung).  Prospective evidence adds the paired weekly gain
   (reference CRPS - kit CRPS) per frozen week.  Actionable (later): a query is qualified by the calibration near its own threshold, not only by the cell.
WALL A - Q1 snap-normalized center (draws.q1_snap_wall; genuinely new formula).  Challenger center (draws.snap_center, earlier played games this season only): attempts per
   offensive snap x mean team snaps per game (offense_snaps / snap_share) x his last game's snap_share; family Poisson and everything else kept.  Scope: final Q1 laws, layer
   0 Poisson, nonzero, played, recorded, center defined.  Gate: exact_crps season gains; EARNED iff their mean > 0 (R-GATE).  Witness: incumbent Q1 draws = atlas_rows.
   Registered targets (readings): lowest snap_share level tercile bias -3.13 toward 0 and PIT > .90 .388 toward .10; Q1 CRPSS vs the reference > 0; downstream Q2, Q3,
   QB F8 row_crps.  Not a target: Q1 total width (the lower tail .21-.23 is flat across snap terciles); if Q1 stays too narrow it is a separate residual.
WALL B - TE receptions <-> TDs (draws.te_td_link_wall; genuinely new formula).  TE TDs reordered to the ranks of Poisson(R tau) + U, R the issued receptions after the
   copula, tau = TE TDs per reception on seasons < s (dependence.chain_l3: marginal-preserving).  Scope: played TE player-weeks with a composed F8 and dk_points.  Gate: F8
   row_crps season gains; EARNED iff mean > 0.  Witness: incumbent F8 = atlas_rows; the TD marginal row_crps unchanged on every row.  Registered targets: TE F8 L / U
   (.116-.125 / .118-.122 by form) toward .10 / .10, TE F8 CRPS down, receptions x TDs draw correlation toward the realized +.270 / +.304.
SHADOW C - season-to-date reference for the historically negative-skill cells (no historical wall: chosen after their result was seen).  Cells: F5 receiving yards RB
   nonzero, F5 rushing yards TE nonzero, F5 rushing yards WR nonzero, Q1 attempts QB nonzero.  The kit law stays official; from the first issue-of-record week scored, the
   ladder's prospective evidence carries their paired weekly gain against the same reference.  When the reference earns prospectively is registered before it is read.
## TRUST LADDER - OUTCOME, and BATCH 3 - REGISTRATION - Oct 6 2026 (owner ruling; registered before any batch 3 value is computed; week 5 untouched)
Ladder outcome: witness passed (51 cells, 0 differing); reference rows 109439 of 109439; rung 1: 26 cells (69340 rows), rung 2: 6 (871), rung 3: 19 (39228).
Ladder refinements (readings; no rung changes): rung 3 is named HISTORICALLY SKILLFUL.  Width keeps the total tail rate and adds its two parts, L = share PIT <= .10 and
   U = share PIT > .90, each against .10 by share_band; TAIL BALANCE = balanced iff both within band (shown, not a rung).  Prospective evidence adds the paired weekly gain
   (reference CRPS - kit CRPS) per frozen week.  Actionable (later): a query is qualified by the calibration near its own threshold, not only by the cell.
WALL A - Q1 snap-normalized center (draws.q1_snap_wall; genuinely new formula).  Challenger center (draws.snap_center, earlier played games this season only): attempts per
   offensive snap x mean team snaps per game (offense_snaps / snap_share) x his last game's snap_share; family Poisson and everything else kept.  Scope: final Q1 laws, layer
   0 Poisson, nonzero, played, recorded, center defined.  Gate: exact_crps season gains; EARNED iff their mean > 0 (R-GATE).  Witness: incumbent Q1 draws = atlas_rows.
   Registered targets (readings): lowest snap_share level tercile bias -3.13 toward 0 and PIT > .90 .388 toward .10; Q1 CRPSS vs the reference > 0; downstream Q2, Q3,
   QB F8 row_crps.  Not a target: Q1 total width (the lower tail .21-.23 is flat across snap terciles); if Q1 stays too narrow it is a separate residual.
WALL B - TE receptions <-> TDs (draws.te_td_link_wall; genuinely new formula).  TE TDs reordered to the ranks of Poisson(R tau) + U, R the issued receptions after the
   copula, tau = TE TDs per reception on seasons < s (dependence.chain_l3: marginal-preserving).  Scope: played TE player-weeks with a composed F8 and dk_points.  Gate: F8
   row_crps season gains; EARNED iff mean > 0.  Witness: incumbent F8 = atlas_rows; the TD marginal row_crps unchanged on every row.  Registered targets: TE F8 L / U
   (.116-.125 / .118-.122 by form) toward .10 / .10, TE F8 CRPS down, receptions x TDs draw correlation toward the realized +.270 / +.304.
SHADOW C - season-to-date reference for the historically negative-skill cells (no historical wall: chosen after their result was seen).  Cells: F5 receiving yards RB
   nonzero, F5 rushing yards TE nonzero, F5 rushing yards WR nonzero, Q1 attempts QB nonzero.  The kit law stays official; from the first issue-of-record week scored, the
   ladder's prospective evidence carries their paired weekly gain against the same reference.  When the reference earns prospectively is registered before it is read.
## BATCH 3 - RUN RECORD - Oct 6 2026
The ledger stood at 4853 accepted lines when the second run began (4836 after the ladder correction, + 17): batch 3 had run once before, unseen in this conversation,
   and its registration was appended a second time by the rerun (lines 4854-4870 repeat 4837-4853; the first copy is the registration of record).  The rerun stopped at
   q1-snap-wall's refusal: "proj/q1_snap_verdicts.csv exists - the wall is judged once".  That verdict was written by the first run, before anyone read it; it stands as
   written.  Read now: both walls' verdict and report files as they are on disk.
## WALL A - OUTCOME, and BATCH 4 - REGISTRATION - Oct 6 2026 (before the run; week 5 untouched - witness_v3 is the issue of record)
Wall A (first batch 3 run, verdict written before read): 1498 rows, 11 outside (center undefined); incumbent = atlas_rows on every row.  Season gains (exact CRPS)
   -0.4053, -0.0443, +0.1914, +0.4689; mean +0.0527 -> EARNED by the registered R-GATE (mean > 0).  Two of four seasons are negative: recorded, not re-judged.
   Targets: lowest snap tercile bias -3.151 -> -0.977, PIT > .90 .388 -> .309, PIT <= .10 .211 -> .243; Q1 CRPSS -0.011 -> +0.001; downstream row_crps F8 QB 4.8432 ->
   4.7363, Q2 4.1063 -> 4.0592, Q3 47.9678 -> 47.8092.  Wall B did not run (no verdict file on disk).
Integration of wall A: laws.snap_center moves from draws (one producer); laws.snap_centers gives the center for any target week (a target week without a played row
   gets a row carrying no values; a row's own values never enter its center).  build_inputs reads the EARNED cells of q1_snap_verdicts.csv and the played rows;
   row_laws adds layer SNAP_LAYER = 6 (provenance "snap center wall A (earned)") on layer-0 Poisson nonzero Q1 rows where layer 0 is final and the center is defined
   and positive: the same Poisson with mean = the center.  Layer 6 joins PROMOTED_LAYERS (set aside in every v0 witness) and draws on its own substream "snap center".
   Q2 and Q3 condition on the issued Q1 draw as before.
Gate (fixed now): te-td-link-wall runs as registered in batch 3 (unchanged code; the TE composition is untouched by wall A).  Then issue-check (M1) and replay (A2')
   ACCEPTED; draws-check (M2) ACCEPTED; q1-snap-check: rows equal the verdict's, rows_sha256 equal, every season gain within 1e-12; atlas regraded; ladder.  The issue
   path's gate runs on 2026 week 6 (card, market-check, base) before any week 6 freeze.
## WALL A - OUTCOME, and BATCH 4 - REGISTRATION - Oct 6 2026 (before the run; week 5 untouched - witness_v3 is the issue of record)
Wall A (first batch 3 run, verdict written before read): 1498 rows, 11 outside (center undefined); incumbent = atlas_rows on every row.  Season gains (exact CRPS)
   -0.4053, -0.0443, +0.1914, +0.4689; mean +0.0527 -> EARNED by the registered R-GATE (mean > 0).  Two of four seasons are negative: recorded, not re-judged.
   Targets: lowest snap tercile bias -3.151 -> -0.977, PIT > .90 .388 -> .309, PIT <= .10 .211 -> .243; Q1 CRPSS -0.011 -> +0.001; downstream row_crps F8 QB 4.8432 ->
   4.7363, Q2 4.1063 -> 4.0592, Q3 47.9678 -> 47.8092.  Wall B did not run (no verdict file on disk).
Integration of wall A: laws.snap_center moves from draws (one producer); laws.snap_centers gives the center for any target week (a target week without a played row
   gets a row carrying no values; a row's own values never enter its center).  build_inputs reads the EARNED cells of q1_snap_verdicts.csv and the played rows;
   row_laws adds layer SNAP_LAYER = 6 (provenance "snap center wall A (earned)") on layer-0 Poisson nonzero Q1 rows where layer 0 is final and the center is defined
   and positive: the same Poisson with mean = the center.  Layer 6 joins PROMOTED_LAYERS (set aside in every v0 witness) and draws on its own substream "snap center".
   Q2 and Q3 condition on the issued Q1 draw as before.
Gate (fixed now): te-td-link-wall runs as registered in batch 3 (unchanged code; the TE composition is untouched by wall A).  Then issue-check (M1) and replay (A2')
   ACCEPTED; draws-check (M2) ACCEPTED; q1-snap-check: rows equal the verdict's, rows_sha256 equal, every season gain within 1e-12; atlas regraded; ladder.  The issue
   path's gate runs on 2026 week 6 (card, market-check, base) before any week 6 freeze.
## BATCH 5 - CENTER READ - REGISTRATION - Oct 6 2026 (owner: address every CENTER TOO LOW cell in one run and learn something actionable; a reading, promotes nothing)
Runs after batch 4's atlas regrade, on the cells then labelled NOT QUALIFIED - CENTER TOO LOW (read from proj/atlas.csv).  Per cell: KIND (MEDIAN SHIFT when the median band
   fails, else TAIL SHAPE when L or U fails, else SHAPE ONLY); the kit center vs simple pregame centers from the season-to-date reference outcomes (mean, last-3 mean,
   last game, median) by bias and MAE; the three largest bias owners among the pregame states (end-tercile gap / SE); bias by week band.  Use: each cell gets a kind and
   an owner.  A center wall that follows must be a mechanism fitted on earlier seasons and registered before it is run; the alternative center that scores best here is
   never itself promoted from this read (it was chosen after seeing these seasons) - it may only run as a prospective shadow.
## BATCH 4 / 5 - RUN RECORD, WALL B - OUTCOME, and WALL B - INTEGRATION - REGISTRATION - Oct 6 2026 (before the run; week 5 untouched)
Run record: ssot_batch4.zsh ran (ledger 4875 -> 4888): WALL B EARNED; M1 ACCEPTED; A2' ACCEPTED (layers 4, 5, 6 set aside: 24515 rows); M2 ACCEPTED (Q1 layer 6 1503 rows,
   z -0.26); q1-snap-check ACCEPTED (1498 rows, hash equal, max gap 2.78e-17); atlas regraded (Q1 CRPS 6.0293, bias +0.557; Q2 4.0529; Q3 47.7139; F8 QB 4.7258, bias +0.619);
   ladder (rung counts unchanged; F8 QB CRPSS +0.088; Q1 skill FAIL, gains -0.422 / -0.023 / +0.130 / +0.340; Q2 skill now FAIL, gains -0.013 / +0.090 / +0.204 / +0.274).
   ssot_batch4_5.zsh then appended the batch 4 registration a second time with batch 5's
   (ledger 4888 -> 4907; the first copy is of record) and stopped at "te_td_link_verdicts.csv exists - the wall is judged once".
Wall B: 4211 rows; incumbent F8 = atlas_rows; TD marginal row_crps differing 0.  tau 0.0968 / 0.0906 / 0.0842 / 0.0807; season gains +0.0103, +0.0029, +0.0028, +0.0022;
   mean +0.0046 -> EARNED (every season positive).  TE F8 copula L .117 -> .114, U .118 -> .115, row_crps 2.1974 -> 2.1948; independent L .127 -> .121, U .121 -> .113,
   2.2208 -> 2.2098; receptions x TDs draw correlation +.189 -> +.267 (realized +.270 / +.304).
Integration of wall B: laws.td_rate_per_reception (one producer, moved from draws); build_inputs reads the EARNED positions of te_td_link_verdicts.csv; fit_state carries
   td_link {position: tau}; draws.issued_components applies chain_l3 to the TDs on the issued receptions after the yards step where earned.  yards-count-check's issued
   side is now the yards step itself (composed_components + count_yards_components), so later steps leave its witness intact; its values are unchanged.
Gate (fixed now): q1-snap-check, te-td-link-check (rows, rows_sha256, season gains within 1e-12 of the verdict) and yards-count-check ACCEPTED; atlas regraded; ladder;
   then batch 5's center-read as registered.  The issue path's gate runs on 2026 week 6 before any week 6 freeze.
## BATCH 6 - OUTCOME, and BATCH 7 - REGISTRATION - Oct 6 2026 (before the run; week 5 untouched)
Batch 6: q1-snap-check, te-td-link-check (4211 rows, hash equal, gap 4.34e-19) and yards-count-check ACCEPTED; atlas: CENTER TOO LOW 14 (TE F8 independent -> MISCALIBRATED
   (shape)); TE F8 copula CRPS 2.1948, L .113 U .116; ladder rung counts unchanged.  Center read (14 cells): KINDS - MEDIAN SHIFT 8 (too low 5, too high 3), TAIL SHAPE 6.
   Learned: (1) the kit center equals the raw season-to-date mean (MAE equal to 3 decimals in receptions, receiving and rushing yards, targets); (2) the top bias owner is the
   usage level - low-usage centers sit below their outcomes, high-usage above (WR targets by target_share level -0.353 / +0.040 / +0.367, gap 9.1 SE; WR receiving yards by
   dk_points level -3.362 / -0.221 / +3.757, 7.6 SE; WR receptions 7.9 SE; RB targets 7.4 SE; RB receiving yards 6.2 SE) - the signature of an unshrunk mean; (3) six cells
   are tail shape, not center (WR TDs, WR receptions, TE targets, Q5, RB and QB rushing yards).  The season-to-date median's lower MAE is the median minimizing absolute
   error, not evidence for a center.
WALL C - shrunk center (draws.shrink_wall; genuinely new).  Per nonzero law: mean' = (n mean + k m) / (n + k), n = earlier played games on this team this season (the
   frames' n), m = the term x position mean outcome of nonzero rows of seasons < s, k from SHRINK_GRID (0, .5, 1, 2, 3, 5, 8, 12, 20, 40; 0 = incumbent) minimizing squared
   error on seasons < s.  Every other parameter kept.  Scope: final layer 0 or 5, nonzero, Poisson / negative binomial / normal, not TEAM, n > 0 (share-of-team-draw and
   support laws are out of scope by family - WR and TE targets).  Gate per cell: exact_crps season gains, EARNED iff mean > 0.  Targets: the usage-tercile bias gap shrinks.
WALL D - TDs on yards (draws.td_yards_wall; genuinely new).  RB and WR TDs reordered to Poisson(issued receiving + rushing yards, negatives 0, x tau) + U, tau = TDs per
   scrimmage yard on seasons < s (chain_l3, marginal-preserving; replaces L3's volume order).  Evidence: residual partial correlation TDs x yards given the count +.244
   (RB rushing), +.236 (WR receiving).  Gate per position: F8 row_crps season gains, EARNED iff mean > 0.  Witness: incumbent F8 = atlas_rows; TD marginal unchanged.
   Targets: yards x TDs draw correlation toward realized (RB rushing +.358, WR receiving +.359); F8 L / U toward .10 / .10.
CONSISTENCY READ (reading): share of issued draws impossible in a box score - receptions > targets, TDs > touches, yards with zero count, negative counts, QB completions >
   attempts, passing yards with zero completions - beside the played box scores; F8 mean vs the linear part at component means.
## BATCH 7 - OUTCOME, CORRECTIONS, OWNER DIRECTIVE; WALL E - REGISTRATION - Oct 6 2026 (before the run; week 5 untouched)
Batch 7 outcome (proj/shrink_verdicts.csv, td_yards and consistency reports): Wall C EARNED 14, FAIL 2 (RB carries mean -0.0176; TE rushing yards k 0 in every season);
   Wall D RB EARNED (F8 L .096 -> .083, U .117 -> .108), WR FAIL; consistency read: RB receiving yards nonzero in 78% of zero-reception draws; receptions > targets TE
   22.5%, RB 5.7%, WR 5.5%; TDs > touches 1-2.4%.  No law promoted.
CORRECTION - Wall C was registered "genuinely new"; it was not.  Cells covered by recorded closures were re-judged; those verdicts are VOID (no allowed use as evidence):
   F5 receptions RB / WR / TE (receptions stay closed, L2580); F5 receiving and rushing yards RB / WR (work order 41 (a): a location remedy already failed in all four
   slices, L2600, L2769); F5 receiving yards TE (the simple TE location branch closes, L2932).  F5 TDs RB / WR / TE, Q4 passing TDs, QB rushing TDs: pooled TD-rate
   mechanisms are the family recorded as collapsing under D (L2140-2141) - DIAGNOSTIC only.  The remaining Wall C cells (RB targets, QB carries, Q1 attempts on 11 rows
   EARNED; RB carries, TE rushing yards FAIL) and Wall D RB are SEEN (Path B): designed from the batch 6 center read on the seasons that judged them; shadow candidates.
CLASSIFICATION - today's integrations (yards given count, wall A layer 6, wall B TE TD link) were designed on the seasons that judged them: SEEN, not independent EARNED.
OWNER DIRECTIVE (Oct 6 2026): "Measurements are the only thing that can keep or remove capability.  Use what we have now as baseline."  The issued law at ledger 4939
   (those integrations included) is the baseline; each served law keeps a version-scoped prospective clock from 2026 week 6; only measurement keeps or removes it.
WALL E - ROLE GROUPS READ FROM THE POPULATION (draws.role_group_wall; owner question: should a mean be pulled toward the position average, or toward players who share
   its role?).  Open branch: N05's archetypes were a beat / boom log-loss feature (L968, L1065), and rank-type targets score uniform level shrinkage zero (L960-962); no
   recorded wall pooled a level toward a population-derived role.  The snap tiers (.35 / .70) are authored cut points; no cut point is authored here.
   Role vector: per played player-week, the season-to-date level (earlier games only, variance_states) of snap_share, target_share, carry_share, air_yards_share - state
   ROLE without dk_points (a role is usage, not production).  Groups: per position (RB, WR, TE, QB) and test season s, a full-covariance Gaussian mixture on the
   position's spine player-weeks of seasons < s with the vector defined (a column constant or undefined throughout is dropped); group counts 1-8, k-means start,
   random_state 0, max_iter 1000, a non-converged fit refuses; the count is the lowest BIC.  One group IS the position: the baseline nests in the candidate and the
   population decides between them.  Laws per row: ISSUED; POSITION prior (n mean + k m) / (n + k), m the training rows' mean outcome; ROLE prior, m the row's
   membership-weighted group means (each group's membership-weighted mean outcome).  Both priors on the same training rows (nonzero-state spine rows, n > 0, vector
   defined, seasons < s); each k from SHRINK_GRID by squared error; every other parameter kept.  Scope: Wall C's (final layer 0 or 5, nonzero, Poisson / negative
   binomial / normal, not TEAM, played, outcome, n > 0) with the role vector defined; rows without one counted and reported.
   Judged once per cell outside the closures above (ROLE_CLOSED; those cells are read only): (1) ROLE vs POSITION - ROLE iff the mean season gain (exact_crps, position
   minus role, weekly means) > 0; one group chosen in every season -> POSITION by construction.  (2) ROLE vs ISSUED - EARNED iff the mean season gain > 0 (R-GATE).
   Evidence state: (1) blind - no role-vs-position comparison has been seen; (2) its position-prior relative on these cells was seen (Wall C) - disclosed.  Promotes
   nothing; an EARNED cell is a Layer C shadow candidate.  Readings: the groups per position x season (BIC by count, weights, centroids - what the natural roles are);
   bias by dk_points level tercile, issued / position / role (Wall C's position prior over-corrected the usage gap).  Writes proj/role_group_verdicts.csv,
   proj/role_group_groups.csv, proj/role_group_report.txt.  Registered once, judged once.
## WALL E - FIRST RUN STOPPED BEFORE ANY VERDICT - INSTRUMENT DEFECT - Oct 6 2026 (the registered procedure re-run once, unchanged)
First run: every mixture fit, 47,265 rows scored (out of scope, role vector undefined: 40), then the verdict step stopped - AttributeError: cell_rows.groupby("season")
   .groups is the GroupBy's own attribute, not the column "groups".  No gain was computed or printed; no verdict, groups or report file was written.  Fix: the column is
   read as groupby("season")["groups"]; nothing else changes.
Reading on screen before the stop (role vectors only, no outcome): BIC chose 8, the top of the registered range 1-8, in all 16 position x season fits - the population
   resolves at least 8 roles at every position.  The registered range is kept (no change after a reading); an uncapped group count is its own registration.
## WALL E - OUTCOME; ABSORPTION ROUTING; THE ROLE ATLAS - REGISTRATION - Oct 6 2026 (proj/role_group_report.txt; week 5 untouched)
Wall E (47,265 rows; 40 without a role vector; BIC chose 8 groups, the registered top, in all 16 fits).  Judged cells (mean of 4 season gains, exact CRPS):
   RB targets ROLE vs position +0.0019 (3/4), role vs issued +0.0169 (4/4) EARNED; RB carries ROLE +0.0061 (2/4), vs issued -0.0115 FAIL (low dk_points tercile bias
   issued -0.550, position +0.180, role +0.005); QB carries POSITION -0.0064 (1/4), role vs issued +0.0185 EARNED (position vs issued +0.0249); TE rushing yards POSITION,
   FAIL (394 rows); Q1 attempts 11 rows POSITION, FAIL.  Reading: roles help where a position holds distinct jobs (RB); where it is one job (QB) eight groups add noise.
   Read-only cells (closures stand; DIAGNOSTIC routing only): role beat position on the mean in 9 of 13 (RB rushing yards +0.058, TE receiving yards +0.039, RB receiving
   yards +0.007, receptions RB / TE / WR +0.004 / +0.006 / +0.002, TE TDs +0.004, Q4 +0.004); WR rushing yards -0.021 (0/4), QB rushing TDs -0.002.  The role prior
   mostly removes the position prior's usage over-correction (RB rushing yards by dk_points level tercile: issued -3.68 / +1.63, position +0.17 / -2.23, role +0.04 / -1.76).
   Evidence state: role vs position blind; role vs issued partly seen (Wall C).  Nothing promoted; RB targets (role) and QB carries (position prior) are SEEN shadow candidates.
ABSORPTION ROUTING (owner question: when a role is out, does another role absorb?).  Measured: reallocation is real - vacated RB carries go 65.6% / 87.1% (dev / 2024-25)
   to baseline RBs, 9.3 / 10.2% to new RBs (L352, L909); old absences are already absorbed through the teammate's last game (L316); QB new absence -> WR+TE bust not earned
   (L315).  As a forecast input, expected vacated share added nothing beyond role momentum (R1, L183) and the vacated-share family was deleted (L144); the price file carries
   a partial pregame trigger for a new absence (backup price +153, L454), registered as H6 (L795).  Routing: absorption by population-derived role is a DIAGNOSTIC lens on
   a measured mechanism; as a forecast input it is the deleted vacated-share family and needs its own case (a role-level signal the player-level test could not see).
THE ROLE ATLAS (draws.role_atlas; owner: "I want the data to tell me what is truth"; roles may cross positions - "sometimes they are simply receivers").  A reading of
   pregame role vectors only (snap / target / carry / air-yards share season-to-date levels); no outcome is read; promotes nothing.  Populations: RB, WR, TE, QB, and
   RB+WR+TE with the position label removed.  Every season's spine player-weeks together; the group count is read from the population with no upper limit - full-
   covariance Gaussian mixtures for counts 1, 2, 3, ... (k-means start, random_state 0, max_iter 1000; non-converged refuses), stopping once 3 successive counts fail to
   lower the best BIC (ROLE_COUNT_PATIENCE, declared).  Per role: weight, centroid, clarity (mean largest membership probability of its rows), its share of each season's
   rows (recurrence: a true role holds in every season), and for the pooled population its members' positions (a mixed-position role is a cross-position role).
   Writes proj/role_atlas_groups.csv, proj/role_atlas_report.txt.  Next lenses, each its own registration after the atlas: team concentration (the team's favorite
   targets regardless of position); absorption by role; role-level comparisons within and across teams and against defenses.
## ROLE ATLAS - OUTCOME; CORRECTIONS (WITHDRAWN-FRAMEWORK WORDING, WALL E CLOSURE SCOPE); WALL F - REGISTRATION - Oct 6 2026 (week 5 untouched)
Role atlas (proj/role_atlas_report.txt; usage vectors only, no outcome): roles RB 11, WR 17, TE 15, QB 12 (BIC, no upper count); large roles hold a stable share in every
   season; mean clarity .81-.85 (soft membership).  Position label removed (RB+WR+TE, 29 roles): WR and TE share roles (role 11 WR .50 / TE .49; role 25, 80% snaps 20%
   targets, WR .75 / TE .25; roles 4, 7, 14, 15, 26 mixed); RBs are 95-100% of every role with meaningful usage.  A reading; nothing promoted.
CORRECTION 1 - withdrawn-framework wording.  The prospective framework (Layer C shadows, sequential rule, SHADOW ELIGIBLE, shadow states) and L1177 / L1180's prospective
   clocks were withdrawn (L3001-3007, L3043-3044).  Entries since then used them: "SHADOW C" and "prospective shadow" (batch 3 / 4 entries), "version-scoped prospective
   clock from 2026 week 6" and "shadow candidates" (batch 7 / 8 / 9 entries).  Those words carry no route.  In force: a design chosen on the seasons that judge it is a
   same-rule consistency check, not clean, unless it carries the whole-pipeline null of its recorded design procedure (L3020-3021) - Wall C, Wall D, yards given count,
   wall A, wall B are same-rule consistency checks; the latter three stay in the issued law as the owner's baseline (Oct 6 directive).  2026 weeks are frozen, scored and
   reported only (L4513-4518); no prospective result changes a model without a separately registered cycle.
CORRECTION 2 - Wall E closure scope.  ROLE_CLOSED named F5 receiving / rushing yards RB / WR under work order 41 (a); its outcome closes "under this formulation: ...
   partial pooling toward the earlier-season positional mean" - not a role target.  Wall E's values there (role vs issued RB receiving +0.265, RB rushing +0.214, WR
   receiving +0.187, WR rushing +0.124, 4/4 each; role vs position +0.007, +0.058, +0.013, -0.021) are DISCOVERY / SEEN POSITIVE, not verdicts, and not integrated.
   Receptions stay closed (the closure is the posterior-mean form, L2580).  TE receiving yards: role groups are the lens L2929 named next ("residualized / nonlinear share");
   its Wall E value is seen; its own registration later.  TD cells stay read only (L2140-2141).
WALL F - THE TRAINING-ONLY SHRINKAGE PROCEDURE (draws.procedure_wall; reviewer (b+), owner-adopted).  Object judged: a procedure that chooses the pull target and strength
   from earlier seasons only - not the cells seen to win.  Cells: Wall E's scope minus PROCEDURE_CLOSED (ROLE_CLOSED without the four 41 (a) cells) with rows in every test
   season: F5 receiving / rushing yards RB / WR, F5 targets RB, F5 carries RB, QB carries, F5 rushing yards TE (Q1 attempts if it holds rows every season).  Variants per
   row (exact_crps): the issued law; (n mean + k prior) / (n + k), k in SHRINK_GRID > 0, prior = the position mean or the hierarchical role prior (player -> role ->
   position): Wall E's role_mixture (unchanged, fit on seasons < the row's season), each group's mean shrunk to the position mean by moments (tau2 = max(0, sum N_g (m_g -
   m_p)^2 / sum N_g - G sigma2 / sum N_g); tau2 = 0 gives every group the position mean).  k and target chosen by CRPS (the judging score), replacing MAE (41 (a)) and
   squared error (C / E).  Nested walk-forward: outer seasons 2023, 2024, 2025 (2021 has no earlier test season to choose on); per cell the variant with the largest mean
   season gain over the earlier test seasons, ties to the issued law; scored on the outer season.  Statistic: mean over cells x outer seasons of the season CRPS gain
   divided by the cell's issued season CRPS.  Whole-pipeline null (the L168 / L269 principle - the whole search re-run on null data): 2000 draws, default_rng(20261015);
   each draw flips the sign of every cell's and variant's weekly gain in a slate together and re-runs selection and outer scoring.  HISTORICAL STRUCTURAL PASS iff the
   statistic is positive and above the null 95th.  PASS -> an integration registration of the frozen procedure in every eligible cell (cells choosing the issued law stay
   unchanged); FAIL -> the role-conditioned level prior closes for these cells; the smooth role curve is the next rung only if a residue reading asks for it.  Writes
   proj/procedure_verdict.csv, proj/procedure_choices.csv, proj/procedure_report.txt.  Registered once, judged once.
## WALL F - OUTCOME; WALL F' AND ITS SIMULATION BENCH - REGISTRATION - Oct 6 2026 (proj/procedure_report.txt; week 5 untouched)
Wall F: 25,581 rows, 9 cells, outer 2023 / 2024 / 2025; pooled relative CRPS gain -0.02865, whole-pipeline null 95th +0.37922 (share at or above .5595) -> HISTORICAL
   STRUCTURAL FAIL.  It stands; not re-run.  INSTRUMENT DEFECT (disclosed): cells were pooled with equal weight and Q1 attempts (11 rows) entered; its relative gains
   (+.2119, -.2166, -1.2268) set both the statistic and the null.  The other 8 cells' 24 outer gains average +0.0191 (arithmetic on printed lines; 22 of 24 >= 0; the
   procedure chose role in 16, position in 6, issued in 2) - SEEN POSITIVE, not a verdict.  Every corpus season is now seen in these cells: no clean historical route
   remains on them.  The registered FAIL consequence ("the role-conditioned level prior closes for these cells") applies to the corpus seasons; an unseen season is not
   covered by it (it carries no information about 2022).
OWNER-ADOPTED ROUTE (reviewer; "simulation calibrates the judge; reality supplies the verdict"): simulate the judge -> freeze the corrected procedure -> decide whether one
   unseen season (2022: no raw file, never admitted, L4151) is worth spending -> if so, and only by an owner decision lifting the no-fetch rule for 2022, consume it once.
WALL F' (frozen now): Wall F's procedure unchanged except the statistic - cells pooled by their row counts in the outer season (procedure_rows_statistic; weights fixed by
   rows, never by results).  2022 design: choose the variant per cell on 2021 (priors fit on seasons < 2021), score 2022 (issued laws fit on seasons < 2022; priors and
   role mixtures fit on seasons < 2022), weekly sign-flip whole-pipeline null of 2000 draws; HISTORICAL STRUCTURAL PASS iff the statistic is positive and above the null
   95th.  PASS -> integration registration of the frozen procedure in every eligible cell; FAIL -> the role-conditioned level prior closes for these cells.
WALL F' BENCH (draws.procedure_simulation; simulated outcomes only; never evidence for a role pull).  Semi-synthetic: the real rows of 2021 (inner) and of 2023, 2024,
   2025 (each standing in for 2022's row structure; their priors refit on seasons < 2022) keep their issued laws, n, priors, weeks and cells; only outcomes are drawn.
   Worlds gamma in {0, .25, .5, 1}: truth mean = issued mean + gamma (role k* mean - issued mean), role k* = the role k with the largest real mean CRPS gain per cell
   (seen; a power target only, as SEEN positive allows); outcome = truth + residuals resampled with replacement from one real (cell, season, week) residual block of the
   same cell drawn at random (week shocks, skew and tails kept); counts rounded, floored at 0.  Witness: the vectorized score equals exact_crps on every variant of every
   20th real row (max |diff| <= 1e-8, else refused).  Per replicate Wall F' runs whole (select on 2021, score the template) against 200 weekly sign-flip draws; 100
   replicates per world x template, default_rng(20261016).  Readings per world: pass share (false pass at 0, power above) with Monte Carlo SE, choice shares, mean statistic
   beside role k*'s own (selection-bias reading).  GATE (registered before the run): false pass <= .05 and power at gamma 1 >= .80 -> 2022 WORTH SPENDING (then the owner
   decides the fetch); otherwise NOT WORTH SPENDING (2022 kept unspent; the role prior waits).  Not covered: drift and confounded worlds (named by the reviewer; later
   benches).  Writes proj/procedure_sim.csv, proj/procedure_sim_report.txt.  Promotes nothing.
## FINAL CORPUS, THE LOCKBOX AND ITS BUDGET - OWNER DECISION AND REGISTRATION - Oct 6 2026 (before the fetch; week 5 untouched)
Owner (verbatim): "yes, but you must proactively mitigate ever asking again, whatever you have to do to the fetched data".  Root (five whys, Oct 6): every request for
   more seasons came from the absence of a data budget - no seasons reserved from reading, so exploring spent the seasons judging needs - made worse by instrument defects
   that burned evidence (Wall F's equal weighting).  The remedy fixes the root once.
CORRECTION - 2022.  Batch 11 treated 2022 as unseen (L4151 "no raw file").  L397 records "2022: used in earlier development ('learned from 2016-2022'), deleted as dirty -
   not a lockbox"; no measurement of 2022's data quality exists on record (the deletion reason on record is the after-inactives frame, L108).  2022 joins DISCOVERY below;
   batch 11's bench result is a one-season power reading only (its "2022 WORTH SPENDING" label has no route).
FINAL CORPUS (ingest.corpus_fetch, kit.py fetch --corpus): one historical fetch, ever.  Every season the kit does not hold - 1999-2018 and 2022 - every ASSETS kind (stats,
   play-by-play, snaps, injuries, weekly rosters), the season's schedule rows, participation (2016+) and FTN (2022+), into data/corpus/TIER/; a kind the release does not
   publish (HTTP 404 in both its encodings) is measured absent (data/corpus/absent.json) and never retried.  The command refuses once data/corpus exists: no historical
   season is ever fetched again, by code.  Completed future seasons arrive only by the weekly cycle.  A question the corpus cannot answer is recorded NOT EVALUABLE ON THE
   CORPUS; no further fetch is proposed.
TIERS (frozen now): DISCOVERY - 2016, 2017, 2018, 2022 (used in earlier development), with every season already in facts (2019-2021, 2023-2025): readings, atlases and
   design run here.  LOCKBOX - 2012-2015 (no use on record; snap counts begin 2012, so roles exist).  DEEP LOCKBOX - 1999-2011 (no use on record; no snap counts, so no
   roles).  Sealed tiers: never in facts, never read by a reading; facts.lockbox_check in the guard fails if a sealed season enters facts' player table or any kit module
   but ingest.py names the corpus folder.  Discovery seasons enter facts only by a separate registration (an engineering transaction, no fetch).
LOCKBOX BUDGET: at most 6 judgments on LOCKBOX and 6 on DEEP LOCKBOX over the project's life, spent in CHARTER order; each a registered wall whose instrument first passed
   its simulation bench (simulation calibrates the judge; reality supplies the verdict); each verdict states its number (k of 6) and the seasons it read; a lockbox season is
   read only by a judgment (proj/lockbox_ledger.csv, append-only, records each spend).  When a budget is spent, new evidence comes only from completed future seasons.
   The owner may close a tier at any time; no tier is ever reopened by refetching.
WALL F' ON THE LOCKBOX (judgment 1 of 6, LOCKBOX; registered here, run only after its instrument exists and passes its bench): train 2012, choose on 2013 (priors on
   seasons < 2013), outer 2014 (choice from 2013) and 2015 (choice from 2013-2014); Wall F's cells and procedure with the row-count pooled statistic; whole-pipeline weekly
   sign-flip null; HISTORICAL STRUCTURAL PASS iff positive and above the null 95th; era disclosed (a pass shows the procedure worked in 2014-15 under refits).  Before it:
   (1) a lockbox law build (laws refit from lockbox facts built in isolation - engineering, no fetch); (2) a bench of this two-season design with gates registered
   before it runs.  Stopping rule (owner, Oct 6): every outcome ends the role-pull question - a data-check failure, a bench that cannot separate the worlds, a FAIL, or a
   PASS (then an integration registration).  Nothing is asked for after it.
This transaction: CHARTER, ingest.py (corpus_fetch), facts.py (lockbox_check), kit.py (guard and fetch usage); facts rebuilt (facts.py changed; the facts content is
   unchanged); ledger advance; then fetch --corpus; then guard lists the added raw files (manifest check fails until accept, the next transaction, after the list is read).
## FINAL CORPUS - FIRST RUN STOPPED - TRANSFER DEFECT - Oct 6 2026 (the same fetch resumed; nothing moved, nothing accepted)
First run: deep_lockbox 1999-2011 and lockbox/stats_2012, pbp_2012 written to data/corpus_incoming; then lockbox/snaps_2012.csv.gz arrived truncated (EOFError: compressed
   file ended before the end-of-stream marker) and the fetch stopped before data/corpus existed.  Measured absent so far: snaps 1999-2011; injuries 1999-2008; weekly
   rosters 1999-2001.  Fix (transport only; the fetch's content and tiers unchanged): every file is checked whole (a gzip file read to its end-of-stream marker), a truncated
   transfer is fetched again at most 3 times then the fetch stops with nothing moved, and a whole file from an interrupted run is kept, not fetched again.  The fetch is
   still the one historical fetch: it resumes only while data/corpus does not exist.  Guard note: until data/corpus is written and accepted, the raw manifest check lists
   data/corpus_incoming - expected; accept follows only after the added list is read.
## FINAL CORPUS - SECOND RUN STOPPED - THE 2012 SNAP FILE IS PUBLISHED BROKEN - Oct 6 2026 (the same fetch resumed; nothing moved, nothing accepted)
Second run: lockbox/snaps_2012.csv.gz arrived "truncated" 3 times and the fetch stopped.  Measured outside the kit (this session's sandbox, curl): the release's
   snap_counts_2012.csv.gz is 103 bytes at its published Content-Length 103 and is not a whole gzip; its plain snap_counts_2012.csv is header only (0 rows); 2013, 2014,
   2015, 2016 and 2019 snap files are whole (about 23,800 rows each).  So 2012 snap counts do not exist in the release - not a transfer fault.  Fix (classification only;
   content and tiers unchanged): a file that arrives whole at its published length but is not a valid file is "broken", the next encoding is tried, and a kind with no
   whole non-empty encoding is measured absent with its reason (data/corpus/absent.json).  The fetch prints the 2012 measurement itself on this run.
Consequence, recorded now, before any lockbox season is read: roles exist in the LOCKBOX for 2013-2015 only (2012 stays sealed; it has play-by-play, stats, injuries and
   rosters but no snap counts).  Wall F' on the lockbox (judgment 1 of 6) needs a design within 2013-2015; it is registered with its corrected null and its simulation
   bench in one entry, before the lockbox is read.
## FINAL CORPUS - OUTCOME AND ACCEPTANCE; WALL F' AMENDMENT (LOCKBOX DESIGN, CONDITIONAL NULL) AND ITS BENCH - REGISTRATION - Oct 6 2026 (before the bench runs; no lockbox season read)
Corpus (fetch --corpus, third run): data/corpus written, 104 data files + absent.json; accepted in this transaction after the fetch's own per-file listing was read.
   Absent 27 (measured): snap counts 1999-2012 (2012: the .gz broken at its published length, the .csv header only); injuries 1999-2008; weekly rosters 1999-2001.
   Present per season: stats, play-by-play and schedule 1999-2022 tiers; injuries 2009+; weekly rosters 2002+; snaps 2013+; participation 2016-2018, 2022; FTN 2022.
   Upstream notes (nflfastR changelog, read by the owner): 1999 and 2000 are no longer supported upstream ("inconsistent data sources") - kept, flagged UNSUPPORTED
   UPSTREAM, and any judgment reading them states it; 2001-2010 come from the 2011+ source (4.0.0) and player ids are standardized across 2011 (2.1.1); the pre-2016
   Jacksonville home-game defect was fixed in the raw data (5.0.0, #478) and this fetch is the current release.
WALL F' AMENDMENT 1 - LOCKBOX DESIGN (supersedes the 2012-2015 design; 2012 has no snap counts): choose on 2014 (priors and role mixtures fit on 2013), judge 2015
   (issued laws, priors and role mixtures fit on seasons < 2015, i.e. 2013-2014); one outer season.  Cells, variants, CRPS selection and the row-count pooled statistic
   unchanged.  Lockbox judgment 1 of 6.
WALL F' AMENDMENT 2 - CONDITIONAL NULL (draws.procedure_outer_null).  The whole-pipeline null re-randomized the inner season too; consistently harmful variants (large k)
   then turned into large chance wins under sign flips, and the batch 11 bench measured the result: null 95th +0.069 to +0.100 against a gamma-1 effect near +0.019;
   power 0.000 at every gamma.  The choice never reads the outer season, so the test is conditional on it: choices fixed from the earlier seasons; each draw flips the sign
   of every outer week (one sign per week, shared by every cell) on the chosen variants' weekly gains; same pooling; 2000 draws in the judgment.  PASS iff the statistic is
   positive and above the null 95th.  The whole-pipeline null stays the rule for designs judged on seasons that shaped them (L3020); the lockbox did not shape this design.
BENCH (draws.procedure_simulation, rerun with procedure_outer_null; outputs proj/procedure_bench.csv / _report.txt; batch 11's files stay as recorded): unchanged worlds,
   residual blocks, witness, 100 replicates per world x template (2021 as the choosing season, 2023 / 2024 / 2025 as the judged one), 200 null draws each.  GATE, fixed
   now: false pass at gamma 0 <= .05 and power at gamma 1 >= .80 -> LOCKBOX JUDGMENT 1 MAY RUN (then the lockbox law build and the judgment, each its own transaction);
   otherwise the lockbox is not spent and the role question ends (owner stopping rule).  Promotes nothing; reads no lockbox season.
## WALL F' BENCH (BATCH 13) - INVALID; FIVE WHYS; CANONICAL REPLACEMENT; INSTRUMENT STATES - Oct 6 2026 (no lockbox season read)
Batch 13 bench (proj/procedure_bench.csv): false pass .183 at gamma 0, power 1.000 at gamma 1; it printed "LOCKBOX NOT SPENT - THE ROLE QUESTION ENDS".  That
   reading is INVALID, and the role question is UNRESOLVED (not ended): the bench's null world was not null.  Correction of the agent's report the same day ("closed").
FIVE WHYS (owner-directed): (1) at gamma 0 the pulls truly improved CRPS - the world was not null; (2) draws.procedure_simulation built outcomes as issued mean + raw
   real residual blocks (y - mean), and each cell's residual mean is the issued law's measured bias (CENTER TOO LOW, 14 cells), carried into every world; (3) the bench's
   only witness checked its arithmetic (vectorized = exact_crps), none its premise; the agent's synthetic tests drew noise centred on the truth, sharing the assumption;
   (4) "gamma 0 = the issued law is the truth" lived in prose (docstring, CHARTER), never as an executable property; (5) SUB-ROOT: the instrument decided by rule what
   the population could tell it - it assumed an unbiased baseline while judging methods whose purpose is to correct the baseline's bias.  Second root (the "closed"
   report): the bench's output had two states, both governance consequences written into the instrument, so an invalid measurement had nowhere to go but "ends".
DELETED: the residual-block world construction (residual pools, block resampling, rounding and flooring of counts) and the consequence strings in the bench's output.
CANONICAL REPLACEMENT (draws.law_outcomes, draws.procedure_simulation): worlds are laws, not rules - in world gamma each row's truth is its issued law (same family and
   dispersion) with its mean moved gamma of the way to its cell's role k* mean; gamma 0 is the issued law itself, so the null holds by construction; outcomes are draws
   from that law.  The measured real bias per cell is printed as a reading and enters no world.  Scope (disclosed): the bench measures the judge under the issued laws'
   own shape (no real week shocks or tails).
INSTRUMENT STATES (evaluate.instrument_state; standing rule from now): every instrument names the premises it rests on and measures each (the bench: the score is
   exact_crps, max |diff| <= 1e-8; in every world and cell the simulated mean equals the truth mean, |z| <= 4 - the null world is the issued law); its state is INVALID
   (each failed premise named with its measurement), VALID PASS or VALID FAIL; a state's consequence lives only in the CHARTER, never in an instrument's output.  A
   synthetic test of an instrument uses fixtures carrying the population's measured failure modes (here a biased baseline), not noise matching the instrument's assumptions.
OWNER ROUTE (a), the last correction, registered before the run: the replaced bench runs once (worlds, gate, replicates, null draws and seed as in batch 13; outputs
   proj/procedure_bench_law.csv / _report.txt).  VALID PASS -> the lockbox law build, then Wall F' lockbox judgment 1 of 6 (each its own transaction).  VALID FAIL or INVALID
   -> the role question is recorded UNRESOLVED and stopped by the owner's rule; no further bench correction is made.
## WALL F' BENCH - OUTCOME (VALID PASS); OPERATING SYSTEM AND v1 FINISH LINE (OWNER-ADOPTED); COHERENCE READ - REGISTRATION - Oct 6 2026
Bench (proj/procedure_bench_law_report.txt): premises held (score = exact_crps, max |diff| 1.17e-13; null world = issued law, max |z| 1.91; other worlds move only the
   mean, max |z| 2.24).  Pass share: gamma 0 .003 +- .003, .25 .067, .5 .560, 1 .993 +- .005 -> VALID PASS.  The judge is a validated instrument; no further method
   work on Wall F'.  Reading: a lockbox FAIL means no effect of the seen size (power at half size .56), not no effect.  Measured real bias per cell on the bench rows is
   small (largest RB rushing yards +1.31; most within +-.5), so the five whys of batch 14 named one of at least three causes of the invalid batch 13 bench - the deleted
   construction also moved residuals across rows of different scale and rounded / floored counts; the deletion removed all three.
STATE: ROLE-CONDITIONED CENTER - READY FOR LOCKBOX (discovery done, judge validated; the only missing transaction is unseen evidence: the lockbox law build, then Wall
   F' judgment 1 of 6).  The usage-conditioned center bias it targets stands in the issued law (issued bias by dk_points level tercile, Wall E: RB rushing yards -3.68 /
   -1.86 / +1.63, WR receiving yards -3.39 / -0.19 / +3.80, RB receiving yards -1.10 / -0.34 / +1.89, TE receiving yards -2.23 / -2.60 / -0.55).
OPERATING SYSTEM (reviewer; owner-adopted): four permanent loops.  INTEGRITY - every issued simulation is a possible football world; a failure stops the product.
   FORECAST - the strongest supported distribution per quantity (earned structural law > earned reference > wide prior > unresolved only when nothing lawful exists);
   a failure selects a weaker lawful forecast, never stops the product.  RESEARCH - owner read -> smallest challenger -> procedure bench -> unseen reality -> integrate
   or close; no alternative search after a closure.  PROSPECTIVE - freeze -> games -> score -> append; never rewrites an issued week.  Caution lives in the machinery
   (guards, witnesses, benches, lockbox, freezes), not in the decisions.
v1 FINISH LINE (registered): (1) every simulated outcome structurally coherent - zero identity violations in every issued draw; (2) every issued forecast carries
   explicit trust-rung fields (issued, center, width / tail, skill vs reference, prospective observations); (3) every negative-skill cell has an explicit status
   ("reference currently preferred"); (4) the weekly issue freezes reproducibly before kickoff; (5) weekly scoring appends without changing history.  When all five
   hold, v1 is finished; everything after is optimization.  Order: coherence integration -> re-run M2 / M3 / F8 and witnesses (declare every downstream change) ->
   ladder and reference status on the card -> freeze the next week through that path -> lockbox build -> Wall F' judgment 1.
COHERENCE READ (draws.coherence_read; a reading, promotes nothing; first step of the integrity loop): on the M3 replay's issued draws, per position and identity
   (receptions <= targets; receptions 0 -> receiving yards 0; RB carries 0 -> rushing yards 0; TDs <= touches), per row: draws violating now, and the fewest any coupling
   of the row's two issued marginals must leave violating (Hall's condition; for a zero identity, parent zeros minus child zeros).  Rule it serves (reviewer: couple
   existing laws coherently, do not casually refit marginals): a row with floor 0 is made coherent by reordering alone, both marginals kept; a row with floor > 0 has
   marginals that themselves break the identity, and its marginal change is a separately registered wall.  Writes proj/coherence_read.csv / _report.txt.
## COHERENCE READ - OUTCOME; FIVE WHYS (RB RECEIVING YARDS); THE STRUCTURAL GRAPH - INTEGRATION - REGISTRATION - Oct 6 2026 (before the run; week 5 untouched)
Coherence read (proj/coherence_read_report.txt; violating now / coupling floor, shares of draws): receptions <= targets TE .22489 / .00029, RB .05733 / .00273, WR .05520 /
   .00866; TDs <= touches RB .01131 / .00002, TE .02380 / .00006, WR .00925 / .00001; RB carries 0 -> rushing yards 0 .00736 / .00025; receptions 0 -> receiving yards 0
   TE .01704 / .00056, WR .01320 / .00052, RB .35317 / .34208.  Every identity but one is a coupling defect (marginals nearly compatible, draws mis-paired); RB receiving
   yards is a marginal-law defect (a third of RB draws stay impossible under any re-pairing).
FIVE WHYS (owner-directed): (1) about 35% of RB draws have 0 receptions and every one carries nonzero receiving yards; (2) RB receiving yards are drawn from a Normal
   (laws.RECEIVING_YARDS_FORM RB form 2) independent of the drawn receptions, and chain_l2 only re-pairs it - a re-pairing cannot create the zeros a Normal lacks; (3) the
   yards given count law applied only to cells its wall EARNED, so a box-score fact (yards are a sum over catches) was judged as a predictive hypothesis and the
   impossible law stayed; (4) the code has no category for structural identities - every stat is its own marginal law and dependence is a marginal-preserving afterthought;
   (5) SUB-ROOT: the unit measured was the single-stat marginal, never the box score, so the box score was never constrained.  The code generated stats in an order
   football does not: snaps -> targets -> receptions -> yards per catch, receptions + carries -> TDs.
OWNER-ADOPTED ARCHITECTURE (reviewer): STRUCTURAL GRAPH -> marginal / conditional laws -> marginal-preserving coupling -> F8 -> cross-player dependence later.  Football
   dictates the structure; snaps and roles may explain parameters inside it only when the data earn them; a player's zero moves no teammate's volume (absorption parked).
STRUCTURAL GRAPH (draws.STRUCTURAL_IDENTITIES, draws.cohere; never judged by a wall): receptions <= targets; receptions 0 -> receiving yards 0; RB carries 0 -> rushing yards
   0; TDs <= touches (receptions + carries for RB; receptions + 1 when rushing yards are nonzero otherwise).  Enforcement, per row, fewest change first: receptions <= targets
   by re-pairing the target draws (targets enter no F8 term; both marginals kept), TDs <= touches by re-pairing the TD draws (draws.swap_to_order: each violating draw
   swapped with a satisfied draw that keeps both satisfied); the coupling floor's draws only are capped at the bound (receptions at targets, TDs at touches); receiving
   yards 0 where receptions are 0, RB rushing yards 0 where carries are 0.  Issued draws (compose_slate -> frozen draws) are the cohered draws.
RB RECEIVING YARDS LAW REPLACED (laws.STRUCTURAL_YARDS): every yards cell whose count is drawn - receiving yards RB, TE, WR and RB rushing yards - is drawn as yards given
   its count (draws.yards_given_count: n e + sqrt(max(n, 1) v) Z, e = the yards law mean / the count law mean (the center kept), v = laws.yards_count_variance on seasons < s;
   n = 0 gives 0).  RB receiving yards joins as structure, not as a verdict; the recorded yards given count verdicts stand as recorded; the RB receiving yards Normal and
   its chain_l2 re-pairing no longer issue.  laws.build_inputs no longer reads proj/yards_count_verdicts.csv (YCEARN deleted; the structural set replaces it).  No role or
   snap term enters the per-catch law here; whether role explains per-catch yards is a later wall.
WITNESS (draws.coherence_check, replacing the coherence read): incumbent (before the graph; yards given count on the previously earned cells) vs issued, M3 replay: issued
   draws violating each identity (premise: 0 - evaluate.instrument_state), draws and marginals changed per term, F8 row_crps and L / U tail shares, RB receiving yards
   row_crps.  No gate: structure is not judged; the accuracy movement is declared.  Declared downstream changes (re-baselined in the next transaction, never silently):
   F8 for RB / TE / WR, frozen-draw and market witnesses (draws-check, market-check), the atlas (atlas rows, ladder), yards-count-check (its F8 gains include the RB
   receiving yards change), and every recorded wall reproduction reading issued_components.  v1 finish-line item (1): zero identity violations.
## THE STRUCTURAL GRAPH - OUTCOME (VALID PASS); RE-BASELINE - REGISTRATION - Oct 6 2026 (week 5 untouched: witness_v3 stays the issue of record)
Witness (proj/coherence_check_report.txt): issued draws violating any structural identity 0 of 9,644,000 (RB), 9,596,000 (TE), 16,176,000 (WR) - VALID PASS; v1
   finish-line item (1) holds on the M3 replay.  Marginals changed (share of draws): RB receiving yards .888 (the law replaced); WR receptions .0118, RB .0048, TE .0018 (floor
   caps); TE receiving yards .0719, WR .0620 and RB rushing yards .0083 (zeros on zero-count draws outside the yards given count scope); TDs <= .0001; targets 0 (re-paired
   only: RB .0957, WR .0792, TE .4210 of draws moved).  Accuracy, incumbent -> issued, played rows: RB F8 row_crps 3.2767 -> 3.2517, L .096 -> .105, U .117 -> .114; RB receiving
   yards row_crps 8.2244 -> 7.4074 (3,958 rows); TE F8 2.1985 -> 2.1988, L .116 -> .111, U .115 -> .119; WR F8 3.1122 -> 3.1070, L .090 -> .084, U .102 -> .105.  Structure is
   not judged; the movement is declared: RB and WR better, TE flat.
RE-BASELINE (this transaction): the graded replay and the ladder are rebuilt on the coherent issued draws (kit.py atlas, kit.py ladder - their files are replaced by the
   producers; the previous versions stay in archive / the event log by content hash), then kit.py draws-check reports the M2 witnesses; any recorded witness that no
   longer reproduces is listed as a declared change of this integration, not a failure of the graph.  Then: the week-6 issue path (card, market-check, base) on the
   coherent draws, and the ladder on the card - v1 finish-line items (2) and (3).
## RE-BASELINE - OUTCOME; THE LADDER ON THE CARD (v1 FINISH-LINE ITEMS 2 AND 3) - REGISTRATION - Oct 6 2026 (before the run; witness_v3 stays the issue of record)
Re-baseline (proj/atlas_report.txt, proj/ladder_report.txt, kit.py draws-check): atlas QUALIFICATION COUNTS - CENTER TOO LOW 19; DECISION-QUALIFIED 10; MISCALIBRATED
   (shape) 9; TOO NARROW 6; CENTER TOO HIGH 3; TOO WIDE 2; UNRESOLVED (fewer than 60 graded rows) 2.  Ladder witness: atlas_cells over atlas_rows vs proj/atlas.csv
   cells 51, unpaired 0, values differing 0; reference rows 109,439 of 109,439.  RUNG COUNTS rung 1: 29 cells (70,460 rows); rung 2: 5 (648); rung 3: 17 (38,331).
   M2 ACCEPTED: moments PASS on every (term, position, family, layer); isolation 0 of 100 differing; witnesses mean / crps / cov / bias_comp 0 of 8,342 differing; wall 9
   TE rho 2023 / 2024 / 2025 reproduce.  F8 coverage (a reading, no gate): TE q .10 .3884 vs recorded .0494; the Y reference reads .384 on the same rows (draws-check
   Y comparison), so the reading counts tied outcomes at the quantile on both sides - a tie reading, not a found miscalibration.
DECLARED CHANGES OF THE INTEGRATION (ladder before -> after, CRPSS / skill / rung / atlas label): RB receiving yards nonzero -0.049 FAIL r1 -> +0.058 PASS r1 (the
   kit now beats the reference; centre still too low); RB receiving yards zero +0.068 r3 shape -> +0.063 r1 CENTER TOO LOW (U .164); TE receiving yards zero +0.102 r3
   shape -> +0.043 r1 CENTER TOO LOW (U .233); WR receiving yards zero +0.075 r1 CENTER TOO HIGH -> +0.036 r1 CENTER TOO LOW (U .207); RB rushing yards zero +0.046 FAIL r2
   DECISION-QUALIFIED -> +0.007 FAIL r1 CENTER TOO LOW (U .198); WR receptions zero shape -> DECISION-QUALIFIED; F8 TE copula TOO NARROW -> CENTER TOO LOW; other CRPSS
   moves <= .008 with rung and label unchanged.  Cells with negative CRPSS now: F5 rushing yards TE nonzero -0.390, F5 rushing yards WR nonzero -0.223 (both unchanged).
WORK ORDER - APPENDED (S: found after the graph's scope was fixed; this transaction gates without it): ZERO-STATE YARDS UNDER THE GRAPH - every zero-state yards cell
   (RB / TE / WR receiving yards zero, RB rushing yards zero; layer 4 empirical zero-state law) lost its rung or label, each now CENTER TOO LOW with the upper tail
   .164 to .233 against .10.  These cells are outside laws.STRUCTURAL_YARDS; the graph sets their yards to 0 on zero-count draws (coherence-check: TE receiving yards
   .0719, WR .0620, RB rushing yards .0083 of draws).  The mechanism (zeros imposed on a marginal not drawn as a sum over its count) is a candidate, not a measurement:
   the measuring read is the zero-state cells' PIT before and after cohere on the same draws.  Its remedy class is the graph's own: yards drawn from the count in every
   cell whose count is drawn, not only the four STRUCTURAL_YARDS cells.
THE LADDER ON THE CARD (cards.card; v1 finish-line items 2 and 3): every stat row carries its trust-ladder cell from proj/ladder.csv by (term, position, state) -
   ladder_rung, ladder_center_share and band, ladder_tail_share and width band, ladder_lower_share / ladder_upper_share and tail balance, ladder_crpss, ladder_skill,
   prospective_evidence - and reference_status, read from the sign of the ladder's CRPSS against the season-to-date reference on the cell's graded rows (no threshold):
   REFERENCE CURRENTLY PREFERRED when negative, TIE when zero, KIT LAW when positive, NO LADDER CELL when the row has no graded cell (DK, DST).  The issued quantiles stay
   the kit law's; the status names which forecast the history prefers.  The card refuses when a graded row has no ladder cell, a ladder cell lands on an ungraded row,
   or a ladder cell's qualification or rows differ from the atlas the card reads.  proj/ladder.csv joins evaluate.product_files (a freeze carries the ladder the card
   shows).  NOT DONE HERE: serving the reference's draws in place of the kit law's on REFERENCE CURRENTLY PREFERRED cells (it would change the frozen draws, F8 and the
   structural graph's inputs) - a later transaction.
RUN (this transaction): atlas and ladder rebuilt under the changed code; then 2026 w5 as a WORKING card through the witness_v3 path - issue and card under
   PYTHONHASHSEED 11, market-check under 1, 2 and 3, base - and witness-check witness_v3 with every product file declared, a reading of what the coherent product
   changes against the issue of record.  No freeze: whether week 5's issue of record moves from witness_v3 is the owner's decision; until then witness_v3 stands.
## THE LADDER ON THE CARD - OUTCOME; THE THREE ZEROS - REGISTRATION (a read) - Oct 6 2026 (witness_v3 stays the issue of record)
Outcome (batch 18): CARD ACCEPTED 2026 w5 (working card, not frozen) - ladder unmatched / orphans / disagreeing 0 / 0 / 0; stat rows by rung 1 1,380, 2 29, 3 832, no ladder
   cell 345 (DK); reference status KIT LAW 2,201, REFERENCE CURRENTLY PREFERRED 40 (F5 rushing yards TE nonzero 7 rows, CRPSS -0.390; WR nonzero 33, -0.223), NO LADDER
   CELL 345.  market-check ACCEPTED under PYTHONHASHSEED 1, 2, 3; base ACCEPTED (E[DK] 161.48); witness-check witness_v3 ACCEPTED with every file declared.  Declared and
   not yet explained: native_law_week_2026_w5 rows 2,846 (witness_v3) -> 2,874 (+28; issued QBs 28) - a read owed (work order).
THE THREE ZEROS (owner, Oct 6 2026: one constructor, three orthogonal zeros).  draws.zero_kinds decides the kind of every value of a term once, from three facts read in
   the order they exist, each kind reading exactly one fact the others do not: ABSENT - not observed (no played game; for a history, no earlier played game): a
   non-measurement, never a 0 a law learns; STRUCTURAL - observed and the parent 0 (draws.STRUCTURAL_PARENTS, the box-score graph as facts columns: receptions <- targets,
   receiving yards <- receptions, rushing yards <- carries, TDs <- receptions + carries; completions and interceptions <- attempts, passing yards and passing TDs <-
   completions, QB rushing yards and TDs <- carries): implied 0 by the graph; MEASURED - observed, a positive parent or a root term, and the value 0: the only zero a law
   learns.  Beside them nonzero and violation (parent 0, value != 0: the facts contradict the graph).  The same constructor at two levels: a game, and a history (the
   sums over the earlier played games on the team this season).  Thin exposure is not a kind (a weight on every value, set by the population); the DNP = 0 settlement
   is a consumer's rule applied to ABSENT, not a kind.
RUN (a read, promotes nothing): kit.py zero-kind-read - (1) the partition per cell and level with its witness (one label per row; absent iff unobserved; zero kinds on 0
   values, nonzero on nonzero; structural and violation only on a term with a parent) and its premise (the frame's game values equal the spine's outcomes); (2) the
   spine's state_v1 against the history kind; (3) the empirical zero-state sample's rows by game kind per test season; (4) the graph on the M3 replay, before cohere vs
   issued on the same draws, per (term, position, law state): draw zero share, zeros imposed, PIT mean, L, U, CRPS, beside outcome and history kinds.
   Hypothesis under test (work order ZERO-STATE YARDS UNDER THE GRAPH): the zero-state sample already carries the zeros its rows' parents implied, and cohere imposes a
   second set of zeros from the independently drawn counts - zeros counted twice, CENTER TOO LOW.  Refuted if (4) shows zero share after the graph at or below the outcome
   zero share on those cells, or no PIT shift.  Remedy class if it holds: the constructor replaces the three rules that now decide zero separately (the point-mass rule,
   the zero-state sample's selection, the graph's zeroing) in one transaction; the graph aligns structural zeros instead of overwriting.
GUARD REFUSAL (batch 19, before the read ran): the information-set check found the week-N price word "implied" (facts.WEEKN: the implied team total) in draws.zero_kinds's
   docstring, draws.py:612 - prose, read by nothing, refused correctly.  Reworded ("The graph forces the value to 0."); in the entry above, "implied 0 by the graph"
   means forced to 0 by the graph.  Nothing else changed; the read runs as registered.
## THE THREE ZEROS - OUTCOME; THE GRAPH ALIGNS ZEROS - REGISTRATION - Oct 6 2026 (before the run; witness_v3 stays the issue of record)
Outcome (proj/zero_kind_read_report.txt): PARTITION VALID PASS - 0 inconsistent (label count, absent / observed, zero kinds on 0 values, nonzero on nonzero, structural
   only on a term with a parent); premise held: spine vs frame paired 115,354, values differing 0.  Facts contradict the graph on few rows (violation, game level): RB
   receiving yards 5, WR receiving yards 4, TE rushing yards 2, WR rushing yards 1, QB rushing yards 2.
   The spine's zero state mixes kinds: state_v1 zero is a zero history sum whatever its cause - e.g. F5 TDs TE zero = measured 2,100 + structural 596; F5 rushing yards
   WR zero = structural 5,288 + measured 98.  The zero-state yards samples are mostly structural-zero games: receiving yards RB .829 / TE .824 / WR .794 structural at
   s 2025; RB rushing yards .880.
   HYPOTHESIS HELD (work order ZERO-STATE YARDS UNDER THE GRAPH): before the graph each zero-state yards cell was calibrated; the graph's zeroing added zeros above the
   outcome rate and moved the upper tail - draw zero share before -> after vs outcome zero, U before -> after, CRPS before -> after: RB receiving yards .819 -> .911 vs
   .841, U .115 -> .162, 1.8176 -> 1.8280; TE receiving yards .833 -> .963 vs .822, U .098 -> .235, 1.7281 -> 1.8432; WR receiving yards .779 -> .955 vs .820, U .079 ->
   .216, 2.8135 -> 2.9307; RB rushing yards .885 -> .986 vs .861, U .130 -> .197, 1.8523 -> 1.9282.  Every other composed cell moved <= .016 in zero share (WR receptions zero .783 -> .799, the receptions <= targets cap; the rest <= .008).
   SECOND FINDING (not this transaction): the two REFERENCE CURRENTLY PREFERRED cells share one root - F5 rushing yards TE nonzero and WR nonzero draw no zeros (draw zero
   share .000) while 80.7% and 74.9% of their outcomes are 0, nearly all structural (TE 313 of 394, WR 1,890 of 2,575): carries are not drawn for WR / TE, so their
   rushing yards have no parent in the draws.
THE GRAPH ALIGNS ZEROS (this transaction).  Sub-root: the graph overwrote a child with 0 wherever its independently drawn parent was 0 - a structural zero added on top of
   the zeros the child's own law already carried.  Remedy, canonical: (a) draws.STRUCTURAL_PARENTS becomes the one box-score graph for facts and draws, in terms
   (receptions <- targets; receiving yards <- receptions; rushing yards <- carries; TDs <- receptions + carries; completions, interceptions <- attempts; passing yards,
   passing TDs <- completions; QB rushing yards, TDs <- QB carries); zero_kinds reads its facts columns through parent_columns (TERM_COLUMNS of each parent term) -
   the partition must reproduce batch 19's counts; (b) cohere's two hand-written zeroing lines are deleted: every composed term whose parent terms are drawn for the
   row is aligned by draws.align_zeros - each violating draw (parent 0, child != 0), largest first, swapped with a draw whose child is 0 and parent positive, smallest
   parent first (the child keeps its values); only draws without a partner (the coupling floor) are set to 0.  The order steps (receptions <= targets, TDs <= touches)
   are unchanged.
GATE (fixed now): coherence-check - issued draws violating any identity 0 (VALID PASS); zero-kind-read - (1) partition counts equal batch 19's on every cell and level,
   (4) on the four zero-state yards cells the draw zero share after the graph moves to within .02 of the before share and U after within .02 of U before; every other
   composed cell's zero share and U move <= .01 against batch 19's after values.  Then atlas and ladder rebuilt, declared changes listed.  A miss on any gate line
   refutes the remedy as written and is recorded; nothing is promoted by a wall (the graph is never judged by a wall).
WORK ORDER - APPENDED: (i) WR / TE RUSHING YARDS WITHOUT A PARENT - draw WR / TE carries so rushing yards have their structural parent (the two reference-preferred
   cells); (ii) LAWS ROUTE BY THE CONSTRUCTOR - state_v1 zero mixes structural and measured histories; a law should learn from measured zeros only and the graph place
   structural ones; (iii) FACTS VIOLATIONS - 14 game rows where the box score contradicts the graph; the issued draws give them probability 0; (iv) the +28 law rows of
   2026 w5 (batch 18), unexplained.
## THE GRAPH ALIGNS ZEROS - OUTCOME (ONE GATE LINE MISSED); THE COUPLING FLOOR - REGISTRATION (a read) - Oct 6 2026 (witness_v3 stays the issue of record)
Gate, line by line (proj/coherence_check_report.txt, proj/zero_kind_read_report.txt): coherence-check VALID PASS - issued draws violating any identity 0 (RB 9,644,000;
   TE 9,596,000; WR 16,176,000) - HELD.  Partition: all 49 lines equal batch 19's - HELD.  Other composed cells: zero share and U equal batch 19's after values on every
   cell (moves 0.000) - HELD.  Four zero-state yards cells, zero share after vs before within .02: RB receiving yards .830 vs .819 (.011), TE .838 vs .833 (.005), RB
   rushing yards .888 vs .885 (.003) - HELD; WR receiving yards .802 vs .779 (.023) - MISSED.  U after vs before within .02: RB .118 vs .115, TE .098 vs .098, WR .092
   vs .079 (.013), RB rushing .130 vs .130 - HELD.  The remedy as written is refuted on the WR zero-share line; recorded.
Against batch 19's issued draws the four cells: zero share .911 -> .830, .963 -> .838, .955 -> .802, .986 -> .888; U .162 -> .118, .235 -> .098, .216 -> .092, .197 ->
   .130; CRPS 1.8280 -> 1.8156, 1.8432 -> 1.7272, 2.9307 -> 2.8183, 1.9282 -> 1.8521.  F8 (incumbent before the graph -> issued): RB 3.2767 -> 3.2531, TE 2.1985 -> 2.1992,
   WR 3.1122 -> 3.1078.  Declared atlas / ladder changes: QUALIFICATION COUNTS CENTER TOO LOW 19 -> 15, DECISION-QUALIFIED 10 -> 13, MISCALIBRATED (shape) 9 -> 10;
   RUNG COUNTS rung 1 29 -> 26, rung 2 5 -> 6, rung 3 17 -> 19; RB receiving yards zero rung 1 -> 3 DECISION-QUALIFIED; TE receiving yards zero rung 1 -> 3 (shape);
   WR receiving yards zero DECISION-QUALIFIED, rung 1 (center share .557, too high); RB rushing yards zero rung 1 -> 2 DECISION-QUALIFIED.
WHY THE LINE CAN MISS (the gate's own defect, candidate): the .02 tolerance was authored.  The population sets the bound: where a row's child has more nonzero draws
   than its parent, a marginal-preserving placement must still add zeros - the coupling floor.  align_zeros adds exactly its violators beyond its partners, which by
   count is the child's nonzero draws beyond the parent's; whether the issued draws show that is not yet measured.
THE COUPLING FLOOR (this read; draws.py changes only zero_kind_read - the issue path is unchanged): zero-kind-read section (5) - per row whose parent terms are
   drawn, the zeros the graph added (after minus before) against the floor, both counted from the draws, not from align_zeros.  An optimization / conformance gate:
   exact, no tolerance.  If added = floor on every row of F5 receiving yards (RB, TE, WR) and RB rushing yards, align_zeros is minimal, the WR excess is floor, and
   "added = floor on every row" replaces "within .02 of before" as a permanent invariant of the graph (made a premise of coherence-check in the next transaction); if
   any row differs, align_zeros is not minimal and the remedy stays refuted, recorded open.
OWNER RULING - ONE DECLARED RISK NUMBER; FOUR KINDS OF GATE (Oct 6 2026, owner with reviewer).  The only human-set statistical number is alpha_family = .05, the
   probability of at least one false scientific promotion in a family; it governs scientific promotion only.  Every gate is one of four kinds, each with its own rule:
   (1) IDENTITY (receptions <= targets, zero routes of STRUCTURAL_PARENTS): exact, zero tolerance; (2) OPTIMIZATION / CONFORMANCE (added zeros = coupling floor; a
   recomputation equals its record): exact optimum or machine precision; (3) ESTIMATION PRECISION (a Monte Carlo false-pass rate, a calibration share): run until
   its uncertainty resolves it against what it is compared to, or a declared compute ceiling reports UNRESOLVED - no fixed draw, replicate or row count; (4)
   SCIENTIFIC PROMOTION (a law beats its incumbent): alpha_family alone.  alpha_family is never applied to kinds 1-3, so a football identity is never again judged
   as a hypothesis.  No power gate: a procedure bench reports P(PASS | gamma) over its effect grid and its resolution (the smallest effect it detects reliably) - Wall
   F' bench read this way: gamma 0 .003, .25 .067, .5 .560, 1 .993 - false passes controlled, weak below about half the observed size, near certain at full size; a
   lockbox failure means no evidence for an effect this instrument resolves, not that no effect exists.  Grids become parameters estimated inside a declared model
   family (the family stays a declared choice; the grid points go); the history minimum becomes a prior through which n = 0, 1, 2 ... widens or narrows the forecast
   (its own wall: it changes coverage); the atlas row floor becomes the resolution of the calibration statistic.
ORDER (owner): (1) this read; (2) if minimal, the floor invariant replaces the .02 line; (3) ZERO SEMANTICS - constructor_state / rate_state, the point-mass
   routing, the zero-state samples and the zero-history training frames read draws.zero_kinds, one transaction (one shared root); (4) witnesses, atlas and ladder
   rebuilt, every downstream change declared; (5) WR / TE rushing parents (a missing-parent model); (6) snap role apart from absence (a state variable); (7) only
   then grids, minimums, simulation sizes, and the existing gates rewritten to the four kinds (PREMISE_Z, the 2-SE bands, alpha .05 with the .9 family rule,
   PROCEDURE_SIM_GATE's .80, ATLAS_MINIMUM_ROWS, MATERIALITY_DK) - each its own transaction.
## ALL AT ONCE; THE ONE REPLAY - REGISTRATION - Oct 6 2026 (supersedes the ORDER above: the owner ruled every step into one batch; witness_v3 stays the issue of record)
Batch 21 ran the floor read alone (the earlier download); its CHARTER lines are accepted above.  This batch carries every buildable step and runs the replay ONCE.
THE ONE REPLAY (owner: no replay repeated between steps): draws.replay_all walks replay_slates once; per slate the draws, the components before the graph and the
   issued blocks are computed once (compose_blocks: one producer for compose_slate and the pass) and read by the atlas, the structural graph witness and the three
   zeros.  serve_as_if_replay, coherence_check and zero_kind_read are deleted; their commands (atlas, coherence-check, zero-kind-read) become kit.py replay-all; their
   output files keep their names.  The witness's before-graph comparison is now uncohered_components on the same fitted state (the batch-16 incumbent, RB receiving
   yards before its law change, is retired).  Not run in this batch: draws-check (draws unchanged; its z line is read at the next draw change) and procedure-sim
   (same seed, same numbers; its new gate line is read when Wall F' next runs).
ALL AT ONCE (owner, Oct 6 2026: every step in one batch, then work backwards from what holds).  Each step reports on its own; the run continues past a failed step.
   (1) THE COUPLING FLOOR read (three zeros, section 5).  (2) THE FLOOR INVARIANT - the graph witness gains the premise "the graph adds exactly the coupling floor on
   every aligned row" (draws.graph_floor, one producer for both; ORDERED_TERMS - receptions and TDs, bounded by an order step - aside).  (3) ZERO SEMANTICS, read: the
   three zeros, section 6, splits every law-state-zero row by history kind (structural / measured) and grades each - the build routes laws by kind on what it shows.  (5)
   THE MISSING PARENT, read: section 7 scores WR / TE rushing yards drawn as a sum over Poisson carries at the season-to-date carry rate (per-carry mean and variance of
   the position, seasons < s) against the issued law and the season-to-date reference, same rows - the build follows if it beats both.  (6) SNAP ROLE APART FROM
   ABSENCE - read from the code: state.role_states and state.snap_share_mean_team_season_pregame (absence counted as a 0 snap share; tier cutoffs .05 / .35 / .70)
   are read by no law, card, draw or wall - only by purity; participation already keeps a played-only snap mean beside games missed.  Deleted, with their purity
   lines.  (7) GATES TO THE FOUR KINDS: evaluate.ALPHA_FAMILY = .05 declared once; evaluate.resolution_z(checks) = the two-sided normal quantile at ALPHA_FAMILY over
   the measured number of checks; PREMISE_Z (4.0) deleted - draws-check moments and the bench premises use resolution_z over their own counts; the atlas band (+-2
   SE) uses resolution_z(1); ATLAS_MINIMUM_ROWS (60) deleted - a cell is UNRESOLVED when a tail interval reaches its bound (q .10 to 0, q .90 to 1, or one slate);
   the decile noise quantile is (1 - ALPHA_FAMILY); PROCEDURE_SIM_GATE (.05 / .80) deleted - the bench passes when its false-pass share's exact upper bound is below
   ALPHA_FAMILY, and reports its power curve with exact intervals and its resolution (smallest gamma resolved above ALPHA_FAMILY) as readings.  replay-all and ladder run on the
   new code; every changed label is a declared change of this batch (draws are unchanged).
NOT IN THIS BATCH, each for a reason the code shows: the search grids, the history minimum and ISSUE_WEEKS - the issue path is witnessed row by row against the
   recorded spine (spine, issue-check, replay, fit-replay), so any of them moves every witness at once and is a re-spine transaction of its own; the harness gates
   (2 SE, positive seasons >= n - 1, the .9 family rule, NDRAW band) - the judge of every recorded verdict, rewritten as "statistic above its null (1 - alpha) quantile"
   with its next use; MATERIALITY_DK - an error on a lineup gap needs cross-player dependence (M9); simulation sizes (2,000 draws, 200 noise samples, NDRAW,
   replicates, flips) - adaptive stopping is its own transaction; participation's .35 / .70 snap labels and pooling 10, DST's window constants - participation is NOT
   DECISION-QUALIFIED and DST has its own yardstick; the builds of (3) and (5) - their reads are in this batch.
## THE SPRINT - EVERY REFACTOR, ONE REPLAY - REGISTRATION - Oct 6 2026 (owner: all changes in one batch, the replay once at the end; witness_v3 stays the issue of record)
Baseline: batch 22's replay-all and ladder (the run before this one).  Judged after the run against that baseline, cell by cell; a change that does not hold is
   reverted in the next sprint.  Cells each change touches are listed so a regression is traced to its change.
(A) ZERO ROUTING (THE THREE ZEROS, items 1-4).  The graph and the zero constructor move to state.py (TERM_COLUMNS, STRUCTURAL_PARENTS, STRUCTURAL_ORDERS, HISTORY_SUMS,
   zero_kind_of, zero_kinds, history_kinds, zero_kind_frame, box_outcomes) - one producer for facts, laws and draws.  laws.build_inputs joins every spine row's history
   kind (history_kinds on the sufficient statistics, the recorded spine and the issue path alike).  Laws learn measured zeros only: the zero-history and hurdle
   training frames keep measured-history rows, and those layers apply to measured rows only; every zero-state row resamples its own kind's outcomes (measured for the
   cells the zero-state wall EARNED; structural for every cell whose term has a parent) and the graph places the structural zeros.  A zero-state law row's state is
   its kind (laws.relabel_zero_state): atlas cells, ladder and card read structural / measured where they read zero.  The point-mass rule applies to both kinds as it
   applied to zero.  Retired with their instrument (it judged the mixed zero): zero-state-wall, zero-state-check, instrument-check (deleted).  Touches every zero-state
   cell: receptions, receiving / rushing yards, TDs (RB / WR / TE), Q2-Q5 and QB rushing.
(B) THE MISSING PARENT (item 5).  WR / TE carries drawn: Poisson at the season-to-date carry rate (sufficient statistics), zero-carry histories resampling the
   zero-carry-history rows' carries from facts (issue window, seasons < s); WR / TE rushing yards join STRUCTURAL_YARDS (yards given count, per-carry variance from facts
   - laws.carry_yards_variance).  Touches: F5 rushing yards WR / TE (the two REFERENCE CURRENTLY PREFERRED cells), F5 TDs WR / TE (touches now receptions + carries), F8 WR / TE.
(C) ONE GRAPH IN THE DRAWS.  draws.cohere_terms enforces STRUCTURAL_PARENTS on any row, parents before children (graph_depth): every child aligned to its parent sum's
   zeros (align_zeros), every STRUCTURAL_ORDERS child then re-paired and capped; the bound moves only when it is free (one parent, no other child, not scored).  Skill
   rows (cohere) and QB rows (cohere_qb, new: passing TDs <= completions, interceptions <= attempts, QB rushing TDs <= QB carries) alike.  Receptions are aligned before
   their order step (the TE receptions excess over the floor in batch 21).  The witness reads the declared graph (identity_checks), and the coupling-floor premise now
   covers every child, ordered ones included (ORDERED_TERMS deleted).  Touches: F5 receptions TE, every QB term, F8 QB.
(D) THE HARNESS ON ALPHA_FAMILY.  alpha per test 1 - (1 - ALPHA_FAMILY)^(1/L) (was min(.05, 1 - .9^(1/L))); the observed gate and the null band at resolution_z(1)
   (was 2).  No wall runs in this sprint; recorded verdicts are not re-judged.
NOT IN THIS SPRINT - each is new modelling, not a refactor of what exists: the history minimum as a prior (a hierarchical law for every term); the search grids as
   estimated parameters (moves the issue path off the recorded spine - a re-spine); adaptive simulation sizes (2,000 draws are every frozen draw's key); MATERIALITY_DK
   (needs cross-player dependence, M9); participation's snap labels and pooling, DST's windows.
RUN: replay-all (atlas, graph witness - identities and the floor on every child, kind 1 and 2, exact - the three zeros with the missing-parent read beside the new law),
   then ladder.  draws-check and procedure-sim wait for their next use (stated in the entry before).
## SPRINTS 22-23 - OUTCOME; SPRINT 24 - REGISTRATION - Oct 6 2026 (witness_v3 stays the issue of record)
Batch 22 (THE ONE REPLAY; gates on ALPHA_FAMILY) - the baseline: graph witness VALID PASS (identities 0; added = floor on every aligned row); partition VALID PASS (0
   inconsistent); atlas CENTER TOO LOW 14, DECISION-QUALIFIED 13, MISCALIBRATED (shape) 10, TOO NARROW 6, CENTER TOO HIGH 3, UNRESOLVED (tail interval at its bound) 3,
   TOO WIDE 2 (51 cells); ladder rung 1 30 cells (84,916 rows), rung 2 6 (871), rung 3 15 (23,652).
Batch 23 (THE SPRINT: zero routing, the missing parent, one graph, harness on alpha): graph witness VALID PASS - every identity 0 violating on skill and QB draws,
   added = floor on every row of every child, ordered ones and QB included; partition VALID PASS.  Atlas (66 cells - zero cells now split structural / measured):
   DECISION-QUALIFIED 17, CENTER TOO LOW 16, MISCALIBRATED (shape) 10, UNRESOLVED 10 (cells of 2 to 13 rows), TOO NARROW 6, CENTER TOO HIGH 5, TOO WIDE 2; ladder rung 1
   34 (84,401 rows), rung 2 15 (1,585), rung 3 17 (23,465).  CRPS by term (rows-weighted over the cells), 22 -> 23: F8 QB 4.7258 -> 4.7247, RB 3.2531 -> 3.2484, TE
   2.1992 -> 2.1974, WR 3.1078 -> 3.1056; F5 rushing yards WR 1.2384 -> 0.9975, TE 0.2742 -> 0.2018, RB 13.6341 -> 13.6331; F5 TDs RB .2242 -> .2238, TE .1222 -> .1219,
   WR .1571 -> .1570; F5 receptions RB .7666 -> .7665, TE .7558 -> .7557; Q5 interceptions .4230 -> .4223 - better.  F5 receiving yards RB 7.4061 -> 7.4073, TE 9.0203 ->
   9.0225, WR 14.0854 -> 14.0888; Q4 passing TDs .6250 -> .6252 - worse.  THE MISSING PARENT held: F5 rushing yards WR nonzero CRPS 2.7793 -> 2.1339, CRPSS vs the
   reference -0.223 -> +0.061, skill FAIL -> PASS (gains +.168, +.130, +.170, +.172); TE nonzero 2.6581 -> 1.8858, -0.390 -> +0.014, PASS - the two REFERENCE CURRENTLY
   PREFERRED cells are KIT LAW.  Negative CRPSS left: F5 TDs RB structural -0.001 (157 rows), F5 carries TE measured (10 rows, both CRPS ~0), F5 rushing yards TE
   measured -0.011 (40 rows).  The read beside the new law: the position's yards per carry beat the player's own ratio on the nonzero cells (WR 2.1353 -> 2.0928, TE
   1.8858 -> 1.8781) and lost on the measured / structural ones.
CAUSE OF THE REGRESSIONS (from the code): cohere_terms moved a child's values without what was drawn given it - receptions moved off a zero-target draw left their
   receiving yards behind, then the yards were aligned on their own; passing TDs likewise against completions.  The graph kept every marginal and every identity,
   but split draws that belonged together.
SPRINT 24 (one batch, one replay): (1) THE SUBTREE MOVES WHOLE - align_zeros and swap_to_order carry the child's graph descendants (descendants_of over
   STRUCTURAL_PARENTS) with it, so a draw's receptions, yards and TDs move as one; the floor and the identities are unchanged by it (tested on synthetic draws: 0
   violations, added = floor, yards per catch kept).  (2) WR / TE RUSHING CENTER - the law's mean is carries x the position's yards per carry (laws.carry_yards_law, the
   read above), on the rows the read measured better.  Judged against batch 23, cell by cell; what does not hold is reverted next sprint.
## SPRINTS 22-23 - OUTCOME; SPRINT 24 - REGISTRATION - Oct 6 2026 (witness_v3 stays the issue of record)
Batch 22 (THE ONE REPLAY; gates on ALPHA_FAMILY) - the baseline: graph witness VALID PASS (identities 0; added = floor on every aligned row); partition VALID PASS (0
   inconsistent); atlas CENTER TOO LOW 14, DECISION-QUALIFIED 13, MISCALIBRATED (shape) 10, TOO NARROW 6, CENTER TOO HIGH 3, UNRESOLVED (tail interval at its bound) 3,
   TOO WIDE 2 (51 cells); ladder rung 1 30 cells (84,916 rows), rung 2 6 (871), rung 3 15 (23,652).
Batch 23 (THE SPRINT: zero routing, the missing parent, one graph, harness on alpha): graph witness VALID PASS - every identity 0 violating on skill and QB draws,
   added = floor on every row of every child, ordered ones and QB included; partition VALID PASS.  Atlas (66 cells - zero cells now split structural / measured):
   DECISION-QUALIFIED 17, CENTER TOO LOW 16, MISCALIBRATED (shape) 10, UNRESOLVED 10 (cells of 2 to 13 rows), TOO NARROW 6, CENTER TOO HIGH 5, TOO WIDE 2; ladder rung 1
   34 (84,401 rows), rung 2 15 (1,585), rung 3 17 (23,465).  CRPS by term (rows-weighted over the cells), 22 -> 23: F8 QB 4.7258 -> 4.7247, RB 3.2531 -> 3.2484, TE
   2.1992 -> 2.1974, WR 3.1078 -> 3.1056; F5 rushing yards WR 1.2384 -> 0.9975, TE 0.2742 -> 0.2018, RB 13.6341 -> 13.6331; F5 TDs RB .2242 -> .2238, TE .1222 -> .1219,
   WR .1571 -> .1570; F5 receptions RB .7666 -> .7665, TE .7558 -> .7557; Q5 interceptions .4230 -> .4223 - better.  F5 receiving yards RB 7.4061 -> 7.4073, TE 9.0203 ->
   9.0225, WR 14.0854 -> 14.0888; Q4 passing TDs .6250 -> .6252 - worse.  THE MISSING PARENT held: F5 rushing yards WR nonzero CRPS 2.7793 -> 2.1339, CRPSS vs the
   reference -0.223 -> +0.061, skill FAIL -> PASS (gains +.168, +.130, +.170, +.172); TE nonzero 2.6581 -> 1.8858, -0.390 -> +0.014, PASS - the two REFERENCE CURRENTLY
   PREFERRED cells are KIT LAW.  Negative CRPSS left: F5 TDs RB structural -0.001 (157 rows), F5 carries TE measured (10 rows, both CRPS ~0), F5 rushing yards TE
   measured -0.011 (40 rows).  The read beside the new law: the position's yards per carry beat the player's own ratio on the nonzero cells (WR 2.1353 -> 2.0928, TE
   1.8858 -> 1.8781) and lost on the measured / structural ones.
CAUSE OF THE REGRESSIONS (from the code): cohere_terms moved a child's values without what was drawn given it - receptions moved off a zero-target draw left their
   receiving yards behind, then the yards were aligned on their own; passing TDs likewise against completions.  The graph kept every marginal and every identity,
   but split draws that belonged together.
SPRINT 24 (one batch, one replay): (1) THE SUBTREE MOVES WHOLE - align_zeros and swap_to_order carry the child's graph descendants (descendants_of over
   STRUCTURAL_PARENTS) with it, so a draw's receptions, yards and TDs move as one; the floor and the identities are unchanged by it (tested on synthetic draws: 0
   violations, added = floor, yards per catch kept).  (2) WR / TE RUSHING CENTER - the law's mean is carries x the position's yards per carry (laws.carry_yards_law, the
   read above), on the rows the read measured better.  Judged against batch 23, cell by cell; what does not hold is reverted next sprint.
## 2026 WEEK 5 ISSUE OF RECORD ON THE COHERENT PRODUCT - REGISTRATION - Oct 6 2026 (run after sprint 24 lands; first kickoff Thu Oct 8 2026 20:15 ET)
v1 finish line, read against the runs: (1) coherent draws - held (graph witness VALID PASS, every identity 0 on skill and QB draws, added = floor on every child);
   (2) trust-rung fields and (3) reference status on every forecast - held on the card (batch 18 CARD ACCEPTED, ladder 0 / 0 / 0); (4) a weekly issue frozen before
   kickoff on the product as it now is - open: witness_v3 predates the graph, the zero routing and the missing parent; (5) scoring that appends - open until week 5
   is played.  This run closes (4): the week-5 issue path on the current code under the witness_v3 seeds (issue and card PYTHONHASHSEED 11; market-check 1, 2, 3;
   base), witness-check against witness_v3 with every product file declared (a reading of what changed), then freeze witness_v4 2026 5 - the last freeze before
   kickoff is the issue of record.  Any failure stops the run before the freeze; witness_v3 then stands.  Next: score-week 2026 5 once its games are on disk
   (closes (5)), then the week-6 issue path and its freeze before Thu Oct 15.
## WORK ORDER 26 - ONE TEAM PASSING VOLUME - REGISTRATION, SPRINT 26 - Oct 6 2026 (before code; no gain inspected; witness_v4 stays the issue of record)
Evidence (pasted instrument output, Oct 6): backtest of witness_v4 (M3 tests 2021, 2023-25) - Q1 attempts inside P10-P90 .556 (L .235, U .209, bias +0.56, CRPSS
   +.003) while F2 team targets is .820 inside; Q2 .611, Q3 .714, QB F8 .684 inherit it.  Atlas F2 cells: team targets only - the earned F2 team attempts negative
   binomial (gate +0.09814 4/4, harness v1/v2 pass) has no consumer and Q1 is a standalone law.  pass_volume_read (facts 2019-2026): targets exceed attempts on 9 of
   3,328 team-games; targets per attempt .946-.959 per season; corr(attempts, targets) .9832; targets given attempts 1.17-1.50 x binomial; team attempts variance
   54.8-72.3 at means 32.0-35.2.  Continuing starters (previous team game share >= .5): pooled share .954, QB attempts given team attempts 13.1-22.4 x binomial
   (all states 17.3-26.9); attempts mean 32.4, variance 85.7.
Five whys: Q1 too narrow on both sides with its center held -> its spread lacks the team's passing volume -> Q1 is drawn apart from any team draw -> the earned team
   attempts law was never drawn -> passing volume has two producers in the code (team targets drawn; team attempts a spine center only).  Sub-root: one fact (the
   team's passing volume in a game), two producers.
Remedy (one producer): F2 team attempts is drawn (negative binomial at its F2 v1 mean, r fit on seasons < s); F2 team targets is drawn inside it (beta-binomial share of
   the attempts draw, p = F2 v1 targets / attempts means, concentration fit on seasons < s over team-games where targets sit inside attempts); Q1 attempts is the QB's
   share of the same draw (beta-binomial, p = his attempts over his team's attempts in his earlier played games this season, concentration fit on seasons < s; rows
   without an earlier game keep the incumbent).  No threshold, state split or authored value enters; the start state is carried by p.  Layer TEAM_PASS_LAYER = 7
   (laws); set aside it restores the incumbent exactly.  Draw order: a conditioned law draws once its parent has (own key's law, else its team's - co-reference), so no
   hand order of depths remains.  The new mean is share x team mean (work order 26's mean challenger, L2400) - the center is not held fixed by construction.
Judgment (R-GATE, once, inside THE ONE REPLAY): cells F2 team targets TEAM and Q1 attempts QB, rows paired on (season, week, key) with proj/frozen/witness_v4
   atlas_rows; per season the mean over slates of baseline CRPS - replay CRPS; EARNED iff the mean > 0.  Written once to proj/team_pass_verdicts.csv; later replays
   issue the EARNED cells only (F2 team attempts is issued with either).  Readings, registered and never judged: F2 team attempts (new cell), Q2, Q3, QB F8, WR F5
   targets, WR F8 - inside / L / U and CRPS before -> after.
Predictions: Q1 inside .556 -> .70 +/- .05, CRPSS clearly positive; F2 team targets within .01 of .820; if Q1 L stays > .15 the next root is participation.
Not in scope: RB carries (no issued team-carries law; NO TEST by construction), Q2 / Q3 laws (unchanged; their parent draw changes), freezes before Oct 8 20:15 ET.
## SPRINT 26 - OUTCOME; SPRINT 27 - REGISTRATION (QB F8 ATTRIBUTION, a reading) - Oct 6 2026 (witness_v4 stays the issue of record)
Batch 26 (THE ONE REPLAY): WORK ORDER 26 judged once against proj/frozen/witness_v4 atlas rows.  Q1 attempts QB (1509 paired): CRPS 6.0293 -> 5.5438, inside .556 ->
   .777 (L .235 -> .129, U .209 -> .095), season gains +0.9859, +0.5035, +0.4127, +0.1327, mean +0.5087 -> EARNED; CRPSS +.083, rung 3.  F2 team targets inside the
   attempts draw (1536): CRPS 4.1459 -> 4.1488, gains -0.0159, -0.0117, +0.0041, +0.0108, mean -0.0032 -> FAIL - team targets keeps its own law; the stochastic parent
   earned for Q1 only, not as a doctrine.  Readings: Q2 4.0529 -> 3.8428 (inside .611 -> .778); Q3 47.7139 -> 46.1086 (.714 -> .821, U .072, bias +4.795); QB F8 4.7247 ->
   4.7651 WORSE (inside .684 -> .715, L .161, U .124, bias +0.665); WR targets and WR F8 unchanged; F2 team attempts new cell inside .827, CRPSS +.103.  Graph witness
   VALID PASS; partition VALID PASS.
OPEN: QB F8 lost CRPS while every QB part it sums gained.  Two readings locate it before any law changes, both promote nothing:
   (1) qb_f8_read (atlas rows, batch 26 vs witness_v4): F8 CRPS, bias, width and tails by season, by whether the Q1 law changed, and by outcome band; Q3 >= 300 share.
   (2) QB F8 ATTRIBUTION inside THE ONE REPLAY (draws.qb_f8_attribution): per played QB row the issued draws' DK parts (dk.qb_dk one part at a time, bonuses inside their
   part) - mean m, covariance C - and the outcome's parts o; Delta = E[(o - m)(o - m)'] - E[C]; 1'Delta1 split into diagonal (each part's spread error) and off-diagonal
   (dependence the draws lack) and per pair; bias per part.  Owner map: if the off-diagonal owns the deficit, the next wall is the largest pair's dependence with both
   marginals preserved, judged on QB F8; if the diagonal owns it, that part's marginal is the target.
This replay issues the EARNED cells only (Q1 on team attempts; team targets on its own law) - the atlas and ladder return to the issued product.
## SPRINT 27 - OUTCOME; SPRINT 28 - QB TD LINK - REGISTRATION - Oct 6 2026 (before code; no gain inspected; witness_v4 stays the issue of record)
Batch 27: the replay issued the EARNED cells only (Q1 on team attempts; F2 team targets back on its own law: 4.1459 = baseline).  qb_f8_read (1511 paired QB F8 rows,
   batch 26 vs witness_v4): CRPS 4.7247 -> 4.7651; season gains +0.1057 (2021), -0.0429, -0.0592, -0.1646; Q1 law changed on 1498 rows; width 17.35 -> 18.53.
   QB F8 ATTRIBUTION (1509 rows): F8 mean square error 70.489 vs issued variance 54.691 - 1'Delta1 +15.798 = diagonal -5.221 + off-diagonal +21.019; every season
   diagonal <= 0 (-11.559, -5.649, -0.970, -2.869) and off-diagonal > 0 (+21.380, +20.772, +18.155, +23.896).  Passing yards x passing TDs owns +17.007 of +21.019:
   residual correlation +0.458 vs the draws' +0.016.  Part biases: passing yards +0.343, rushing TDs +0.350, others within +/-0.07; unscored remainder +0.020.
Five whys: QB F8 lost CRPS as it widened -> its parts are each wide enough (diagonal <= 0) but move independently -> passing TDs are drawn apart from the volume draw
   that carries yards -> the TD law has no parent draw although the graph names completions as its parent (STRUCTURAL_PARENTS) -> the graph enforces only the order
   Q4 <= Q2, never the co-movement.  Sub-root: passing TDs' parent is in the graph's support, not in their draw.
Remedy (marginal-preserving; draws.qb_td_link): each QB's passing TD draws reordered to the ranks of Poisson(completions draw x tau) + U, tau = passing TDs per
   completion on seasons < s (laws.fit_state); dependence.reorder keeps the TD multiset exactly; the structural graph runs after.  The work order 31 L3 form with the
   graph's parent as the volume.  No authored value.
Judgment (R-GATE, once, inside THE ONE REPLAY, same draws): per played QB row F8 row_crps incumbent (no link) vs challenger (link); per season the mean over slates of
   incumbent - challenger; EARNED iff the mean > 0.  Written once to proj/qb_td_link_verdicts.csv; issued while unjudged, then only if EARNED.  Readings: F8 tails
   and the draws' yards x TDs correlation before -> after; QB F8 ATTRIBUTION re-read on the issued draws.
Prediction: QB F8 CRPS below 4.7247 (the witness_v4 value) and its below-P10 share below .161; off-diagonal Delta falls by at least half.
## SPRINT 28 - OUTCOME; SPRINT 29 - QB CONTROL LAW - REGISTRATION - Oct 6 2026 (before code; no gain inspected; witness_v4 stays the issue of record)
Batch 28: QB TD LINK judged once - QB F8 (1511) CRPS 4.7651 -> 4.7428, inside .715 -> .760 (L .161 -> .138, U .124 -> .102), draws' yards x TDs corr +.017 -> +.297,
   season gains +0.0227, +0.0161, +0.0071, +0.0398, mean +0.0214 -> EARNED.  Attribution: 1'Delta1 +15.798 -> +4.983 (diagonal -5.224, off-diagonal +21.019 -> +10.206).
   QB F8 stays above witness_v4 (4.7247).  Graph witness VALID PASS; partition VALID PASS.
qb_center_read (1509 QB rows, batch 28 atlas): F8 bias +0.677 per row.  Outcome side (mechanism only): games where the QB threw <= .5 of his team's attempts - 121 rows,
   F8 bias +7.58, below P10 .488, 0.90 of the total bias; (.5, .9] - 104 rows, +5.77, .365; > .9 - 1272 rows, -0.46, L .083 U .112.  Pregame: previous team game share 0 -
   127 rows, Q1 bias +5.03, F8 +3.54, L .291 (0.44 of the bias); season-to-date share (.9, 1) / 1 - F8 +1.36 / +1.08 (overforecast); <= .5 and (.5, .9] - -2.45 / -1.07
   (underforecast).  Mean and median bias move together within states.
Five whys: QB F8's low tail (.138 vs .102) -> games the QB does not finish or share -> the Q1 law draws his share around one season-to-date value with one
   concentration for every QB -> the share's distribution is not conditioned on the pregame control state -> the share law was built as a scalar per QB, not as a law of
   the next game's share given what is known before it.  Sub-root: the QB's share of his team's attempts is a point, not a law of his pregame state.
Remedy (one producer laws.qb_control_state; laws.fit_qb_control): the Q1 share is beta-binomial in the team attempts draw with mean mu = expit(x b) and concentration
   c = exp(x d), x = (1, previous-game share, season-to-date share), b and d fit by maximum likelihood on every played QB game of seasons < s with a pregame state.  No
   bins, thresholds or authored values; the data set how each state moves both the share and its spread (a full-control history can keep mass at partial games; a low
   share can move to full control).  Rows: the same Q1 rows as work order 26 (a defined season-to-date share).
Judgment (R-GATE, once, inside THE ONE REPLAY) against the batch 28 product (proj/atlas_rows.csv.gz copied to proj/atlas_rows_batch28.csv.gz before the replay):
   Q1 attempts QB and QB F8, rows paired; per season the mean over slates of baseline - replay CRPS; EARNED iff BOTH means > 0.  Context: witness_v4 QB F8 4.7247.
   Readings: Q2, Q3, Q4 and both cells' tails and bias.  Written once to proj/qb_control_verdicts.csv; issued while unjudged, then only if EARNED.
Prediction: QB F8 below P10 .138 -> about .11 with above P90 within .02 of .102; QB F8 CRPS below 4.7428.  If it fails, the partial games are shocks the pregame state
   does not forecast, and their frequency stays in the unconditional share law.
## SPRINT 29 - OUTCOME; SPRINT 30 - THE LEAGUE TO DATE - REGISTRATION - Oct 6 2026 (before code; no gain inspected; witness_v4 stays the issue of record)
Batch 29: QB CONTROL LAW judged once against the batch 28 product - Q1 attempts (1509) CRPS 5.5438 -> 5.1426 (gains +0.1004, +0.2819, +0.6079, +0.6047), QB F8 (1511)
   4.7428 -> 4.6422 (gains +0.0426, +0.1010, +0.1164, +0.1391) -> EARNED (both).  Against witness_v4: QB F8 4.7247 -> 4.6422; Q1 6.0293 -> 5.1426; Q2 4.0529 -> 3.6111;
   Q3 47.7139 -> 44.1308.  Attribution 1'Delta1 -0.339.  Open: the passing chain's center - Q1 bias +0.856, Q3 +7.706, QB F8 +0.774.  DECISION-QUALIFIED 17.
team_center_read / team_center_read2 (1536 F2 team attempts rows): the issued center runs high in every season (+0.501, +0.547, +0.304, +1.181) and week band; the team's
   season-to-date mean is unbiased pooled (+0.042) and so is the league's season-to-date mean (+0.029); the training seasons' league mean runs +1.226.  The issued center
   sits between the team to date and the training league mean (issued - team to date -0.041, +0.240, +1.312, +0.853 as the training mean's excess grows) - laws.fit_team
   shrinks toward train_games' mean: league attempts per team-game fell 35.18 (2020) -> 32.05 (2025), so the target carries earlier seasons' level into the test season.
   The issued center has the lowest absolute error (6.173 vs 6.246 league to date, 6.443 team to date): the shrinkage earns, its target does not.
Five whys: the passing chain runs high -> team attempts' center runs high -> the shrinkage target is above the season's level -> the target is the mean of earlier
   seasons -> the center's target was defined as a constant of the training seasons, not as the league's level known before the week.  Sub-root: the shrinkage target is
   a different season's fact.
Remedy (state.build_frames, one producer: column_lb = the league's mean per team-game over the season's weeks < N; laws.shrink_target): every F2 team volume center
   (attempts, targets, carries) shrinks toward the league to date; the strength is refit on training rows against the same target.  Consumers move with it (team laws,
   Q1, skill counts built from F2).  The recorded spine of earlier seasons is not rebuilt (spine_check will read DIFFER on issue-path rows - declared here).
Judgment (R-GATE, once, inside THE ONE REPLAY) against the batch 29 product (proj/atlas_rows.csv.gz copied to proj/atlas_rows_batch29.csv.gz before the replay):
   cells F2 team attempts, F2 team targets, Q1 attempts, and F8 for QB, RB, WR, TE; per season the mean over slates of baseline - replay CRPS; EARNED iff every cell whose
   rows changed has a positive mean.  Reading: every changed atlas cell, CRPS and bias.  Written once to proj/team_center_verdicts.csv; issued while unjudged, then only
   if EARNED.
Prediction: F2 team attempts bias +0.633 -> within +/- .2; QB F8 bias +0.774 -> below +0.4; QB F8 CRPS below 4.6422.
## SPRINT 30 - OUTCOME; SPRINT 31 - THE PASS LEDGER (a reading) - REGISTRATION - Oct 7 2026 (witness_v4 stays the issue of record)
Batch 30: THE LEAGUE TO DATE judged once against the batch 29 product - bias removed (F2 team attempts +0.633 -> +0.042; Q1 +0.856 -> +0.318; QB F8 +0.774 -> +0.578)
   but CRPS did not follow: F2 team attempts 4.3251 -> 4.3264 (mean -0.0019), Q1 5.1426 -> 5.1419 (-0.0005), QB F8 4.6422 -> 4.6442 (-0.0026), RB F8 -0.0008, WR F8 -0.0002;
   F2 team targets alone gained (+0.0063); TE F8 unchanged -> FAIL (every changed cell must gain).  The loss sits in 2024, whose league to date opened low (31.07 at
   week 4) and rose: the season-to-date target follows early noise as much as the stale target carried old level.  Nothing of it is issued (laws.TEAM_CENTER_ISSUED);
   the atlas and ladder this replay writes return to the batch 29 product.
stack_covariance_read (batch 30 atlas, 14900 QB x receiver pairs of the same team-game; issued cross-player covariance 0 by construction): residual correlation
   attempts x targets +.238, completions x receptions +.245, passing yards x receiving yards +.235, passing TDs x TDs +.175 (WR +.263 / +.257 / +.277 / +.270; RB TDs +.004).
   Missing covariance +7.328 DK^2 per pair: passing TDs x TDs +2.304 (.31), passing yards x receiving yards +1.770 (.24), passing TDs x receiving yards +1.313 (.18),
   passing yards x receptions +1.030 (.14), passing yards x TDs +0.783 (.11).  QB F8 x receiver F8 residual correlation WR +.251, TE +.193, RB +.037; by target rank
   1-4: +.339, +.308, +.247, +.157.
Reading: one pass event produces both the QB statistic and the receiver statistic (completions = receptions, passing yards = receiving yards, passing TDs = receiving
   TDs, plus receivers the product does not issue); the product draws the two sides apart.  Before any law is replaced, THE PASS LEDGER measures whether the issued
   marginals already allow it: per team-game, the QB side (the team's issued QBs) against the receiver side (the team's issued RB / WR / TE), the room left for unissued
   receivers against the outcome room, and the violation share as issued and under the comonotone pairing - the compatibility floor, the fewest violations any
   re-pairing of the two marginals can reach.  Receiver TDs count every TD kind (no receiving TD attribution): an upper bound.  Promotes nothing.
## SPRINT 31 - OUTCOME (THE PASS LEDGER, CONFOUNDED AND MISMEASURED); SPRINT 32 - THE PASS LEDGER CORRECTED (a reading) - Oct 7 2026 (witness_v4 stays the issue of record)
Batch 31: the replay returned the batch 29 product (QB F8 4.6422; DECISION-QUALIFIED 17; graph witness VALID PASS).  THE PASS LEDGER (1517 team-games): completions
   QB side 24.68 vs receiver side 22.54 (outcomes 19.45 vs 20.24); passing yards 272.90 vs 246.63 (outcomes 214.75 vs 223.75); TDs 1.60 vs 2.47 (outcomes 1.37 vs 2.11);
   "floor" .4675 / .4781 / .6570.  Two defects, both of the reading, not of the product:
   (1) SCOPE: every law is given the player plays; the ledger summed every issued player of the team - 11.55 issued receivers per team-game, 2+ issued QBs in 489 of 1517
   team-games - so both sides counted players who did not play (the QB side's forecast 24.68 against an outcome 19.45 is that double count, not a law's bias).
   (2) STATISTIC: the comonotone pairing does not minimise violations; it read above the independent pairing (.4675 vs .4405), which no floor can.  The fewest violations
   any coupling of two marginals reaches is sup over t of P(receiver > t) - P(QB > t) (draws.compatibility_floor).
   The TD ledger's room (-0.86 issued, -0.74 outcome) is the rushing TDs inside the receiver side - receiving TD attribution is still absent.
SPRINT 32 (a reading; promotes nothing): THE PASS LEDGER on played players only (receivers and QBs with a played row; team-games where exactly one issued QB played -
   a QB law is given he plays, not given he plays the whole game), with compatibility_floor.  The scope is the outcome side's knowledge of who played: a reading's
   scope, never a law's input.  What it cannot read: whether the issued product's team-level sums hold when participation itself is drawn - that is the participation
   root (F3), whose law the ledger will need before any cross-player identity is enforced.
## SPRINT 33 - THE RECEIVER YARDS LINK (CHARTER L1723-1724) AND TD ACCOUNTING - REGISTRATION - Oct 7 2026 (before code; no gain inspected; witness_v4 stays the issue of record)
Reviewer adjudication against the CHARTER (copy through L4023; later entries owed): (a) real team-games do not balance exactly - passing yards = summed receiving yards
   88.8%, completions = receptions 88.7%, passing TDs = receiving TDs 98.3% (L1703-1705); 465 team-games had 2 passers - a simulated ledger is held to the measured
   real discrepancy, not to zero, and an 'other' receiver bucket is required.  (b) F5 TDs is rushing + receiving TDs (L1706, L1719; state.TERM_COLUMNS): no passing-TD
   identity can be read on it.  (c) THE PASS LEDGER's floor: draws.compatibility_floor (sup over t of P(receiver > t) - P(QB > t)) equals the brute-force minimum over all
   pairings on the reviewer's counterexample (.25) and on 300 random 6-draw cases (max |difference| 1.1e-16).  (d) The +0.63 team attempts residual and its league-to-date
   challenger were on record (L1524-1525); batch 30's FAIL stands (L403: no rescue).  (e) Dependence wall 4 (QB passing yards -> receiver yards, one-for-one) NOT SHOWN
   (L1720-1722); L1723-1724 registered the next form - receiver mean x (realized / frozen QB yards)^beta, beta fit on training seasons - "relevant only if F8 shows a
   receiving-yard covariance miss".  stack_covariance_read shows it: passing yards x receiving yards +1.770 DK^2 per pair, passing yards x receptions +1.030.  The
   reopening condition the CHARTER set is met; the mechanism is the registered one.
OWNER (Oct 7): TDs are three different events - passing, rushing, receiving.  receiving TDs and rushing TDs enter as a structural decomposition of F5 TDs
   (TD_total = TD_receiving + TD_rushing), reads only this sprint, no producer status; every F5 TDs verdict stays frozen as judged.  The coupling of receiving TDs to
   passing TDs waits on the accounting read (td_accounting_read) and is judged on the joint QB-receiver law, never on a receiving-TD marginal alone.
SPRINT 33 WALL - the receiver yards link (laws.fit_receiver_yards_beta, draws.receiver_yards_link): per position (RB, WR, TE), beta minimises the squared error of a played
   receiver's receiving yards against his season-to-date receiving yards per game x (his team-game's passing yards / the team's season-to-date passing yards per game)^beta
   on seasons < s.  In the draws, each receiver's receiving yards draw x (his team's starter passing yards draw / its mean)^beta, draw by draw (the starter: the team's
   issued QB with the largest expected attempts; no passing yards, no receiving yards); receptions, rushing and TDs unchanged.  Judged once inside THE ONE REPLAY
   (R-GATE) on the same draws: per position, receiver F8 row_crps and the stack (receiver F8 + starter QB F8) row_crps, incumbent - challenger, per season the mean over
   slates; EARNED iff BOTH means > 0.  Written once to proj/receiver_yards_link_verdicts.csv; issued while unjudged, then only for EARNED positions.  Reading: the draws'
   receiver x QB F8 correlation against the outcomes' (WR +.251, TE +.193, RB +.037).
Open governance (owed, not acted on): the reviewer's copy predates the R-GATE; its false-pass rate is unmeasured (the gate passes a zero effect about half the time).
## SPRINTS 32-33 - OUTCOME; SPRINT 34 - THE COUPLING CONTRACT, THE TEAM-GAME SHUFFLE, GRADED VERDICTS - REGISTRATION - Oct 7 2026 (before code; no gain inspected)
Batch 32 THE PASS LEDGER (played players; one issued QB played; 1327 team-games): completions QB side 20.76 (outcome 20.80), receiver side 20.28 (20.31), room +0.48
   (+0.50); passing yards 230.50 (229.34) vs 222.25 (224.40), room +8.25 (+4.94); TDs 1.42 (1.46) vs 2.19 (2.12).  Violations as issued .4406 / .4593 / .5463; floors
   (draws.compatibility_floor) .0701 / .0584 / .2364.  The marginals already admit one pass event producing both sides; the pairing is what is missing.  With one QB
   playing, the QB chain is unbiased - the QB center's bias (Q1 +0.856, QB F8 +0.774 over all games) sits in exit / benching / two-QB games: participation.
Batch 33 TD ACCOUNTING (facts): RB TDs rushing 2292 / receiving 592 (receiving share .205); TE .968; WR .968; QB rushing 639.  Team-games: passing TDs = receiving TDs
   .983, completions = receptions .889, passing yards = receiving yards .890; receiving outside RB / WR / TE .002 / .001 / .000; 641 of 3328 team-games with 2+ passers.
   THE RECEIVER YARDS LINK (v1): beta RB .668-.753, TE .835-.886, WR .893-.915 by season; RB EARNED, TE EARNED, WR FAIL; the draws' receiver x QB F8 correlation RB +.002 ->
   +.041 (outcomes +.037), TE +.007 -> +.088 (+.193), WR +.003 -> +.113 (+.251).  DEFECT (mechanical, L403): (passing / mean)^beta with beta < 1 averages below 1 and is 0 on
   passing-0 draws, so the link moved every receiver mean (receiving yards bias WR -0.018 -> -0.261, TE -1.781 -> -1.973, RB +0.128 -> -0.117) - against the CHARTER's own
   share link, which kept the frozen player mean (L1689, L1767).  The v1 verdicts judged two changes at once; they stay on file and are superseded by v2 below.
Two reviewers adjudicated against each other (owner, Oct 7): INVARIANTS (earned) - I1 a link reorders, it never moves a player's forecast; I2 a link follows the structural
   parent; I3 a parent draw is added only where it carries variance the child lacks; I4 pregame state shapes width, not only center; I5 identities at one door, minimum
   change, measured; I6 shrink toward a stable target; I7 fit on seasons < s, judged once on paired slates.  ANTI-PATTERNS (failed) - A1 replacing an earned marginal by a
   share of a team total; A2 a link that moves means; A3 one-for-one scaling by a realized parent; A4 fixing a bias where the error is not; A5 a target that chases early
   noise; A6 more dispersion families on one law; A7 a share of an undispersed parent; A8 a reading summing laws over players who did not play.
SPRINT 34 (one batch, one replay):
   (1) THE COUPLING CONTRACT (I1), witnessed on every row of the replay: the yards link keeps each row's mean exactly; the shuffle keeps every draw multiset; a breach
   refuses.  THE MEAN-PRESERVING YARDS LINK (draws.receiver_yards_link): the v1 factor, then each row rescaled to its unlinked mean.
   (2) THE TEAM-GAME SHUFFLE (Schaake shuffle / ensemble copula coupling; laws.team_game_templates, draws.team_shuffle_permutations): per team-game, each player's draws
   are permuted whole (every within-player identity kept) so the ranks of the starter QB's passing yards and of each receiver's receiving yards (slot j = the j-th
   receiver by expected targets) follow the ranks of the same slots across DRAW_COUNT real team-games of seasons < s (starter = most season-to-date attempts per game;
   receivers ranked by season-to-date targets per game).  The dependence is the data's own; no parameter is fit; a slot the templates lack stays independent.
   (3) GRADED VERDICTS (draws.graded_evidence): beside the R-GATE, every judgment reports seasons positive and a sign-flip null p over slates (4000 keyed flips).
   Judgment, once, inside THE ONE REPLAY, against PLAIN on the same draws: the link per position EARNED iff receiver F8 AND pair stack (receiver F8 + starter QB F8) mean
   season gains > 0; the shuffle EARNED iff the team stack (starter QB F8 + every played issued receiver's F8) mean season gain > 0 (every player's F8 is unchanged by
   construction).  PRECEDENCE (registered now): an EARNED shuffle is issued and the link is not; else the link for its EARNED positions.  Both issued while unjudged
   (the shuffle takes precedence).  Readings: pair stacks per position and by slot, P90 / P10 exceedance, draws' QB x receiver correlation per arm; THE PASS LEDGER's
   violations as issued (now the shuffled draws) against the floor and against real games' own violation rate.
   (4) READINGS (rank_and_td_read): the missing QB x receiver co-movement by receiver slot; TD type - the receiving probability of an RB / WR / TE TD event by a logistic
   law of pregame touch share, fit on seasons < s, scored by log loss against the position share.
Predictions: the shuffle EARNED with the team stack's P10 / P90 exceedance nearer .10 and the ledger's violations as issued from ~.44 toward the floor; the mean-preserving
   link EARNED for RB and TE; WR open.  Week 5 stays on witness_v4 unless the owner re-freezes before Oct 8 20:15 ET.
## SPRINT 34 - OUTCOME; SPRINT 35 - THE LEDGER SHUFFLE, TD TYPE, EXPOSURE SIZE - REGISTRATION WITH GOALS - Oct 7 2026 (before code; no gain inspected)
Batch 34 (graded): THE TEAM-GAME SHUFFLE EARNED - team stack CRPS 14.0460 -> 14.0097, seasons 4/4, sign-flip p .0013; team stack above P90 .130 -> .114, below P10 .131 ->
   .117; every F8 unchanged.  THE MEAN-PRESERVING YARDS LINK: RB EARNED (F8 3/4 p .0065; stack 4/4 p .0020), TE EARNED (F8 4/4 p .0003; stack 4/4 p .0000), WR FAIL (F8 1/4
   p .9503; stack 3/4 p .0000).  Precedence (registered): the shuffle is issued, the link is not.  Reading: the link's team stack 13.9982 (4/4, p .0312) - it changes each
   receiver's spread, the shuffle keeps every forecast (I1).  Slot correlations with QB, shuffle: .248 / .237 / .135 / .031 (outcomes' residual .341 / .312 / .238 / .156).
   THE PASS LEDGER on the shuffled draws: completions violation .4268 (floor .0777, real games .1093); yards .4202 (floor .0627, real .1251).  rank_and_td_read: ranks 1-2
   hold .530 of the missing QB x receiver co-movement, 1-3 .694, 1-4 .795; WR .700, TE .242, RB .058.  TD type: the touch-share law beat the position share in 11 of 12
   position-seasons (RB 4/4, TE 4/4, WR 3/4).
Five whys (owner: the largest cascading move): stacks are still not trustworthy -> the team total does not behave as one event -> the shuffle couples each receiver to the
   QB pairwise (slot correlations ~.25) while completions = total receptions is a near-identity of the team (real violation .109; corr near 1) -> pairwise ranks cannot make
   a sum track its parent -> the coupling was built per player, not per ledger.  Sub-root: the ledger identity has no level in the coupling.  The same why-chain on TDs:
   passing TDs = receiving TDs (.983 real) has no receiving TD in the draws - F5 TDs mixes kinds.  On the QB center: the bias lives in partial games (batch 32), whose size
   per position has never been measured.
Socratic: does a ledger level break the earned shuffle? No - the receivers keep their template joint; only their block moves, so I1 holds and the slot structure
   survives inside.  Does it add a parameter? No - it ranks the block's receptions on the QB's completions (the identity), I2.  Does typing TDs change any earned law? No -
   it splits the earned total by an earned law (I1, I2).  What would tell participation's worth before building it? The share of each position's F8 error that exposure
   deviation explains.
SPRINT 35 (one batch, one replay):
   (1) THE LEDGER SHUFFLE (draws.team_shuffle_permutations, ledger=True): slot templates inside the receiver block (sprint 34), then the whole block permuted so its total
   receptions rank as the QB's completions; the QB keeps his draws.  Judged once (R-GATE, graded) against the EARNED sprint 34 shuffle: EARNED iff the team stack mean
   season gain over it is positive; issued while unjudged, then only if EARNED.
   (2) TD TYPE (laws.fit_td_type, draws.receiving_td_draws): the receiving probability of a TD = expit(a + b x pregame touch share) per position, fit on seasons < s; each
   draw's TDs split Binomial(TDs, p) - none receiving without a reception, all receiving without carries or rushing yards.  The earned total is unchanged; the split is read
   in THE PASS LEDGER as the typed ledger (passing TDs vs receiving TDs; outcomes: facts' receiving_tds).
   (3) EXPOSURE SIZE (exposure_read): per position, the share of F8 squared error a game's snap share deviation from the season-to-date share explains, and the bias of
   the lowest deviation tenth - the measured size of the participation root before any law.
REGISTERED GOALS (before any result; draws.coupling_judgment prints each MET / NOT MET): G1 team stack CRPS below the sprint 34 shuffle's; G2 completions ledger violation
   share <= real games' .109 + .05; G3 team stack P10 and P90 exceedance both in [.08, .12]; G4 slot 1 draws' QB correlation >= .30.  Read beside them: the yards ledger
   against real .125; the typed TD ledger against its real rate; exposure's explained share per position.
## SPRINT 35 - OUTCOME; SPRINT 36 - THE LEDGER REARRANGEMENT, TD SPLIT AS ISSUED DRAWS, EXPOSURE FORECASTABILITY - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
Batch 35 (graded): THE LEDGER SHUFFLE EARNED over the sprint 34 shuffle - team stack CRPS 14.0097 -> 13.9982, seasons 4/4, sign-flip p .0195 (over PLAIN 14.0460: 4/4,
   p .0005); tails above P90 .106, below P10 .112.  Goals: G1 MET; G2 NOT MET (completions violation .4097 though corr(receptions total, completions) .371 -> .937);
   G3 MET; G4 NOT MET (slot 1 correlation .279 vs .30).  Typed TD ledger: receiving TDs 1.46 vs passing TDs 1.42 (outcomes 1.43 vs 1.46) - the means balance; violation
   .3822, floor .0823, real .0354.  EXPOSURE: snap share deviation explains F8 squared error RB .223, QB .136, WR .072, TE .063; the lowest deviation tenth's bias QB +9.38
   (1.22 of all QB bias), RB +5.33.
Five whys (G2): the receivers outrun the QB in 41% of draws -> their total, aligned at corr .94, is wider than the QB's completions -> receivers' draws are independent of
   each other, while in a real game one receiver's catch is not another's -> the shuffles order receivers by templates and the block by its total, but never against each
   other's share of the same completions -> no step minimises the ledger gap itself.  Sub-root: the ledger identity is ranked, not solved.
Socratic: can the gap be closed without a share law (A1)?  Yes - the rearrangement algorithm (Puccetti & Ruschendorf) reorders whole rows so a sum tracks a target with
   every marginal fixed: competition between receivers appears by construction (I1, I5).  Must the TD split be issued to be read honestly?  Yes - a split drawn in the
   reading after a rearrangement is a different split; the issued draws carry it (F5 receiving TDs, F5 rushing TDs; F5 TDs unchanged, I1).  Is exposure worth a law?  Only
   for its pregame part - measured next.
SPRINT 36 (one batch, one replay):
   (1) TD SPLIT AS ISSUED DRAWS (draws.receiving_probabilities, receiving_td_draws in compose): every receiver's TD draws split receiving / rushing by fit_td_type at his
   pregame touch share; F5 TDs unchanged.
   (2) THE LEDGER REARRANGEMENT (draws.team_rearrangement_permutations): from the ledger shuffle, each receiver's whole rows reordered in turn so the receivers' totals of
   receptions, receiving yards and receiving TDs track the QB's completions, passing yards and passing TDs less the issued room (QB mean - receivers' mean); a candidate
   order is kept only if the summed squared gap (each ledger in units of the QB term's spread) falls; passes repeat until none does.  Judged once (R-GATE, graded)
   against the EARNED ledger shuffle: EARNED iff the team stack mean season gain over it is positive; issued while unjudged, then only if EARNED.
   (3) EXPOSURE FORECASTABILITY (exposure_forecast_read): per position, an OLS law of the snap share deviation on pregame features (last game's gap to the season's share,
   games played, missed the team's previous game, the position group's leader gap), fit on seasons < s; out-of-sample R^2 and the F8 error its prediction explains.
REGISTERED GOALS (before any result; draws.coupling_judgment prints MET / NOT MET): G1 team stack CRPS below the ledger shuffle's; G2 completions - receiver side above
   QB side <= .159; G3 typed TDs - receiver side above QB side <= .085; G4 slot 1 draws' QB correlation >= .30; G5 team stack P10 and P90 exceedance both in [.08, .12].
## SPRINT 36 - OUTCOME; THE DEPARTURE OWNER READ; SPRINT 37 - THE THIRD CUMULANT - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
GOAL (layer 1): F8 cells DECISION-QUALIFIED, 0 of 5 -> 5 of 5, team stack P10 / P90 exceedance held in [.08, .12], QB F8 CRPS held <= witness_v4's 4.7247.  Layers: 1 goal,
   2 rungs (33 / 16 / 18 / 0 validated), 3 roots and work-order lines, 4 departures deleted and readers left, 5 the gate.  A landing that moves only 3-5 is plumbing.
Batch 36 (graded): THE LEDGER REARRANGEMENT FAIL - team stack 13.9982 -> 14.0387, gains -.069 -.037 -.044 -.012, 0/4, p .989; G4 MET (slot 1 corr .582), G5 MET (.090 /
   .093), G1-G3 NOT MET.  TD split issued: typed violation .382 -> .2993, means 1.42 / 1.46 (outcomes 1.46 / 1.43).  EXPOSURE FORECASTABILITY: the predicted snap
   deviation explains .001-.024 of F8 error in every position-season - exposure is width, never center.  Layer 1: 0 -> 0 (plumbing and a falsification).
WORK ORDER (appended): WO36-R the rearrangement's target sums receivers who did not play (A8: coupling_rows adds to the ledger totals before the played test; its room
   counts every issued receiver) - same arm, two producers: pass ledger .4106 vs coupling .6675; settled FAIL.  WO36-P coupling's ledger columns are a second producer of
   the pass ledger - delete them, read the pass ledger; pending.  WO36-X exposure is not forecastable; closed; ANTI-PATTERN A9: a center taken from an unforecastable
   exposure.  WO37 where each departure is born; settled by the read below.
THE DEPARTURE OWNER READ (departure_owner_read, batch 37's one read): given the REALIZED count, the normal yards form keeps the departure - L .058 / .058 / .062 (RB / TE /
   WR receiving), .088 Q3, .073 QB rushing, center .53-.57 - so the yards form owns it, not the count; the same form with the cell's own third cumulant (shifted gamma,
   same mean and variance) given the realized count: RB L .098 center .473; WR L .075 center .503; Q3 L .096 center .510 U .094; QB rushing L .090 center .494 U .104;
   TE L .084 center .446 (mixed); RB rushing k3 < 0 (skew -5.7), center .699 (worse).  Per-count skew measured +1.07 to +1.75 on every receiving and passing cell.
   Receptions given realized targets: center .499 / .509 / .473 - the receptions' center departure is inherited from targets.  RB carries L .212 U .214 (TOO NARROW).
   QB chain by passers: 2+ passer team-games carry Q1 +6.41, Q3 +48.0, F8 +3.72 (110% of QB F8 bias); one-passer games Q1 -.80, F8 -.105; F2 team attempts +.63 in both.
Five whys (F8 skill tails): WR F8 L .088 -> its yards' lower tail is too fat (L .048) -> given the realized count the normal form still puts that mass low -> the per-count
   law is symmetric while every measured per-count skew is positive (+1.1 to +1.7) -> the family was chosen by rule (DE NOVO departure).  Sub-root: one authored shape,
   eight cells, three producers (draw_law's yards branch, draws.yards_given_count, the missing-parent reading), each with its own n = 0 and max(n, 1) guard.
Socratic: does a third cumulant move a mean (A2)?  No - the shifted gamma carries the incumbent's mean n e and variance n v exactly; only the skew is added (I1, I5).  Is k3
   chosen?  No - measured on seasons < s by the variance's own residuals (mean(r^3 / n)), the cumulants of a sum adding (I7).  Are the guards needed?  No - n = 0 is the
   gamma's shape 0 and the normal's scale 0: the zero is the law's.
SPRINT 37 (one batch, one replay): THE THIRD CUMULANT - draws.yards_sum is the ONE PRODUCER of yards given count (draw_law, yards_given_count, the missing-parent reading):
   k3 issued -> n c + sign(theta) Gamma(n k, |theta|), theta = k3 / (2 v), k = v / theta^2, c = e - k theta; k3 not issued -> n e + sqrt(n v) Z (bit-identical to the
   incumbent).  laws.yards_count_cumulants replaces yards_count_variance (one fit: v and k3); carry_yards_law and the QB fits return k3 beside v; the law rows carry
   yards_third_cumulant_per_count.  Cells: the six structural yards cells, Q3 passing yards, QB rushing yards.  Judged once per cell (R-GATE, graded) against the batch 36
   product (proj/atlas_rows_batch36.csv.gz): EARNED iff the cell's mean season gain is positive; issued while unjudged, then only EARNED cells (laws.build_inputs).
   Deleted: two producers of the yards form, six guards (three n = 0, three max(n, 1)).  The yards-count wall keeps judging its normal form (yards_given_count with
   k3 NaN); yards-count-check witnesses the batch 23 normal form and is superseded for any cell whose k3 is issued.
LANDING CONTRACT: the batch snapshots laws.py, draws.py and CHARTER.md before writing and restores them whole if the guard refuses (ledger-advance).
REGISTERED GOALS (before any result; draws.third_cumulant_judgment prints MET / NOT MET): G1 F8 WR DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED >= 1 (layer 1
   0 -> 1); G3 yards cells whose nonzero L moves toward .10 >= 6 of 8; G4 Q3 passing yards U >= .08 (from .055); G5 F5 rushing yards RB FAIL (registered falsification).
PREDICTIONS: WR receiving yards L .048 -> about .07; WR F8 L .088 -> about .10; QB F8 stays CENTER TOO HIGH (exits, sprint 38); RB rushing yards FAIL; TE mixed.
EMBEDDED READ (next_root_read, for sprint 38): the QB share through its training PIT distribution (exits as the population's mixture) and the count shapes (RB carries).
## SPRINT 37 - OUTCOME; OWNER DECISION - THE CONFIRMATION GATE; SPRINT 38 - NB1 DISPERSION OF EVERY POISSON CELL - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
Batch 37 (graded): THE THIRD CUMULANT - EARNED: F5 rushing yards TE (3/4, p .069), F5 rushing yards WR (4/4, p .000), Q3 passing yards (3/4, p .25), QB rushing yards
   (2/4, p .34); FAIL: F5 receiving yards RB / TE / WR (lower tail toward .10 - .061 -> .068, .060 -> .078, .048 -> .054 - while CRPS rose), F5 rushing yards RB (the
   registered falsification, G5 MET).  G1, G2, G4 NOT MET; G3 MET (6 of 8).  Layer 1: F8 qualified 0 -> 0, QB F8 4.6422 -> 4.6402.  Layer 2: rungs 33 / 16 / 18 ->
   33 / 15 / 19 (F8 WR rung 1 -> 3, width .190 -> .194; its label still CENTER TOO LOW, q.10 .091).  Layer 4: three producers of the yards form -> one; six guards deleted.
   QB EXIT SHARE (read): the share law through its own training PITs gains +.015 (3/4); the 2+ passer bias stays +5.1 to +5.8 - exits are not separable from the control
   state.  COUNT SHAPES (read): NB fixes RB carries' calibration (L .209 -> .077, U .207 -> .107) with CRPS mixed - the CHARTER's own record (L1555 earned, L1660 harness).
CHARTER ANSWERS (owner's reviewer, Oct 7 2026): calibration first, sharpness second (L403); only S noise-like -> S, CRPS decides only when both are noise-like (L245); the
   CRPS-only R-GATE contradicts both.  Frozen rows: key the sampler on the recorded family - a normal row needs no k3 column (Q17).  Coupling: one producer for the ledger
   violations (Q14); the rearrangement's A8 target is an accounting bug and may be re-judged (L403).  Team attempts' spread is untested (L1526); QB rushing TDs are a rate
   (L1584); receptions given targets need beta-binomial precision (L1678-1681, L1697); TE targets / receptions read as a level (L1559, L1610).
Five whys (layer 1 at 0 of 5 after 37 sprints): F8 cells fail in their tails and shape -> the fixes that move tails and shape (k3, NB) improve calibration, not CRPS ->
   the R-GATE admits only CRPS gains -> the goal's label (DECISION-QUALIFIED) is a calibration label the gate never reads -> the gate departs from the CHARTER's own
   doctrine (L403, L245).  Sub-root: the gate, not a law.
OWNER DECISION (Oct 7 2026 08:53): "follow the one that addresses the sub root of the problems under the 5 why's" - THE CONFIRMATION GATE governs every new judgment.
   draws.confirmation_verdict, the one door: the challenger alone noise-like (atlas DECISION-QUALIFIED, atlas_cells the one producer of the label) -> EARNED; the
   incumbent alone noise-like -> FAIL; both noise-like -> the R-GATE; neither -> the R-GATE (the doctrine is silent; the incumbent rule stands).  Unresolved or absent
   labels are unknown, never noise-like (CHANCE).  No recorded verdict is re-judged by it; earlier FAILs re-enter only as newly registered challengers.
SPRINT 38 (one batch, one replay):
   (1) NB1 DISPERSION OF EVERY POISSON CELL: every spine cell's nonzero-state layer-0 Poisson rows (where layer 0 is final) take the dispersion wall's own NB1 form,
   Var = phi x mean, phi = laws.dispersion_ratio on seasons < s (phi <= 1 is the Poisson incumbent itself); the wall's earned cells are unchanged.  Cells are not
   chosen: the replay records the cells whose final rows carry the sprint 38 provenance.  Judged once per cell by THE CONFIRMATION GATE against the batch 37 product
   (proj/atlas_rows_batch37.csv.gz); FAIL also where a noise-like F8 cell of the position turns structural.  Issued while unjudged, then only EARNED cells.  Disclosed: RB
   carries' dispersion was earned at a CRPS gate and refused by the harness (L1555, L1660); this is a new challenger under the owner's gate, not a re-judgment.
   (2) THE THIRD CUMULANT AS ITS OWN FAMILY: "yards given count (third cumulant)" is the family of a k3 law row (laws.third_cumulant_family, the verdict's door); draw_law
   reads the k3 column only under that family, so a frozen row of the normal family draws as issued (Q17).
   (3) ONE PRODUCER OF THE LEDGER VIOLATIONS (WO36-P): coupling_rows and coupling_judgment no longer compute the receivers-above-QB shares; THE PASS LEDGER is their one
   producer; the rearrangement's goals G2 / G3 are read there.
REGISTERED GOALS (draws.poisson_dispersion_judgment prints MET / NOT MET): G1 F5 carries RB nonzero no longer TOO NARROW; G2 F8 RB DECISION-QUALIFIED; G3 F8 cells
   DECISION-QUALIFIED >= 1 (layer 1 0 -> 1); G4 atlas DECISION-QUALIFIED cells do not fall (layer 2); G5 F5 receptions TE nonzero no longer TOO NARROW.
PREDICTIONS: RB carries L / U .21 -> about .10; F8 RB TOO NARROW -> qualified or one band away; F8 WR returns toward L .088 (its receiving-yards k3 is not issued);
   QB F8 stays CENTER TOO HIGH (exits and the QB rushing TD rate - sprint 39).
WORK ORDER (appended): WO37 settled (yards form owns the tail; k3 earned on four cells).  WO38-G the gate follows L245 (owner).  WO38-R re-judge the rearrangement on
   played-only totals (accounting bug, L403); pending.  WO38-T team attempts spread challenger (L1526); pending.  WO38-Q QB rushing TD rate (L1584); pending.  WO38-B
   receptions given targets: beta-binomial precision (L1697); pending.  WO38-Z reads report slate-clustered z (L2438); pending.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## SPRINT 38 - OUTCOME; THE SHARE LAW READ; SPRINT 39 - THE RB CONTROL LAW, THE GATE AGAINST CHANCE - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
Batch 38 (graded, THE CONFIRMATION GATE): NB1 DISPERSION OF EVERY POISSON CELL - challenged F5 carries RB, F5 receptions TE, Q1 attempts QB (rows without a control
   state), Q4 passing TDs QB.  F5 carries RB TOO NARROW -> TOO WIDE (L .211 -> .045, U .214 -> .088, center .528 -> .377) FAIL; F5 receptions TE TOO NARROW -> CENTER TOO
   LOW FAIL; Q4 FAIL; Q1 EARNED on a mean gain of +.0006 (1/4 seasons, sign-flip p .44) - within chance.  Every cell took the CRPS branch: none turned noise-like.
   Layer 1: 0 -> 0; QB F8 4.6402 -> 4.6396.  Layer 2: rungs 33 / 15 / 19 -> 36 / 13 / 18 (the failed cells; they leave with their verdicts).  Layer 4: the coupling's
   ledger columns deleted (the pass ledger is the one producer); the third cumulant is its own family.
THE SHARE LAW READ (share_law_read, walk-forward on seasons < s): RB carries as a share of team carries (the QB control law's form refit for carries), team carries drawn
   negative binomial at the team's pregame mean: L .058-.091, center .432-.479, U .070-.121, CRPS 2.43-2.80 against the batch 38 issued law's 2.45-2.84 - gains +.050,
   +.067, +.079, +.012 (4/4); given the REALIZED team carries CRPS 2.01-2.37 (team volume carries .4 of the error).  Measured against the batch 38 product (NB1 issued);
   against the Poisson incumbent the gains read about +.08, +.01, +.11, -.04 (NB1 - Poisson per season added).  Receptions given realized targets: binomial at the
   season-to-date catch rate L .160-.167, U .120-.126 (too narrow); beta-binomial L .131-.158, center .52-.53, CRPS worse in every position - precision alone is not the
   fix; the season-to-date catch rate sits high (CHARTER L117: season-to-date regresses).
Five whys (RB carries): U-shaped PIT (L .21, U .21) -> outcomes in both tails -> a back's carries move with his role and game script, low in committee or a lost script,
   high in a bell-cow game -> a count law's width cannot carry a share that moves both ways (sprint 38: NB1 skews right and drops the median) -> RB carries are a share of
   the team's carries (CHARTER L1763), drawn instead as a count alone.  Sub-root: the RB's count is drawn apart from its structural parent (I2) - the class the QB control
   law closed for attempts (sprint 29, Q1 CRPS 6.03 -> 5.14).
SPRINT 39 (one batch, one replay):
   (1) THE RB CONTROL LAW: laws.share_control_state / fit_share_control / share_control_law / share_control_design are the ONE PRODUCER of the control law for any
   position's count (the QB's attempts call it with QB / attempts - bit-identical); F2 team carries drawn negative binomial at the team's pregame carries per game
   (laws.team_count_state, earlier games only), size by maximum likelihood on seasons < s; each RB's nonzero-state carries a beta-binomial share of that draw, mean
   expit(x b), concentration exp(x d), x = (1, previous-game share, season-to-date share), fit on seasons < s.  Layer CARRY_SHARE_LAYER (8).  Judged once by THE
   CONFIRMATION GATE against the batch 36 product (proj/atlas_rows_batch36.csv.gz - the clean RB incumbent: Poisson carries, normal yards); issued while unjudged, then only
   if EARNED.
   (2) THE GATE AGAINST CHANCE (Law 5): in the CRPS branch a positive mean season gain earns only when its sign-flip p is at most ALPHA_FAMILY; within chance the verdict
   is UNRESOLVED (unknown, never earned, not issued).  Recorded verdicts stand (sprint 38's Q1 EARNED is on file); integration readings print the door's current reading.
REGISTERED GOALS (draws.rb_control_judgment prints MET / NOT MET): G1 F5 carries RB nonzero neither TOO NARROW nor TOO WIDE; G2 F8 RB DECISION-QUALIFIED; G3 F8 cells
   DECISION-QUALIFIED >= 1 (layer 1 0 -> 1); G4 atlas DECISION-QUALIFIED cells do not fall (layer 2); G5 F5 carries RB CRPS gains in every season.
PREDICTIONS: F5 carries RB width resolved (L, U .06-.12) with its center still low (.43-.48 - the share's mean, the next root); RB rushing yards and F8 RB widen with it;
   F8 RB one band from qualified; the verdict likely UNRESOLVED or EARNED on CRPS (about +.04 mean against Poisson) - the label may stay structural on its center.
WORK ORDER (appended): WO38 settled (NB1 refused: a count's width is not the shape).  WO39-C the RB share's center (.43-.48) - pending.  WO39-R the receptions' catch rate
   level (L117 regression) - pending.  WO38-R, WO38-T, WO38-Q, WO38-Z carried.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## SPRINT 39 - OUTCOME; THE BROKEN LINK; SPRINT 40 - THE LINK RESTORED, THE GATE GUARDS THE GOAL - Oct 7 2026 (before code)
Batch 39 (graded): THE RB CONTROL LAW EARNED on its cell - F5 carries RB nonzero TOO NARROW -> MISCALIBRATED (shape), L .212 -> .092, center .528 -> .504, U .214 ->
   .091, CRPS 2.5958 -> 2.5385, gains +.094 +.033 +.123 -.019, p .002.  But the goal regressed: F8 RB CRPS 3.2485 -> 3.2680 (0/4 seasons), bias -.076 -> -.209, L .106
   -> .081; F5 rushing yards RB 14.34 -> 14.77, bias -1.32 -> -2.38.  The gate passed it: F8 RB was structural before and after, and the gate read only labels.
THE NEEDLE, batch 36 -> 39 (layer 1): F8 qualified 0 -> 0 of 5; F8 CRPS QB 4.6422 -> 4.6392, RB 3.2485 -> 3.2680, WR 3.1059 -> 3.1060, TE copula 2.1909 -> 2.1908.
   Layer 2: rungs 33 / 16 / 18 -> 33 / 15 / 20; DECISION-QUALIFIED 17 -> 17.  Net: the goal did not move; RB F8 went back.
Five whys (RB F8 regressed while its parent improved): RB rushing yards lost their carries - the graph witness counts 68.6% of RB rushing yards draws changed and 10.6%
   zeros imposed -> they were drawn from the independent normal law, then zeroed where carries were 0 -> draws.count_yards_scope admits the yards given count wall only
   where the count law states a finite mean -> the share family states no mean (its center is law_expectation's, parent x p) -> the earned yards-given-count link for RB
   rushing yards was dropped by a new law that never stated its center.  Sub-root A (mechanical bug, L403): the share law omits its center.  Sub-root B (gate): the
   gate judged a component's label, never the goal cell it feeds; Done says no layer may regress.
SPRINT 40 (one batch, one replay, no new mechanism):
   (A) THE LINK RESTORED: the RB share law's rows state mean = team pregame carries x share mean (law_expectation's own value), so count_yards_scope keeps RB rushing
   yards as yards given the share law's carries, the center kept (e = yards law mean / that mean).  An accounting fix (L403): no verdict is re-judged; the RB control
   law's EARNED stands, and this replay reads its corrected product.
   (B) THE GATE GUARDS THE GOAL: draws.goal_losses - every F8 cell of the challenged position whose CRPS rises beyond chance (graded_evidence on after - before, a
   positive mean with sign-flip p <= ALPHA_FAMILY); draws.confirmation_verdict takes them first: any -> FAIL.  Every future judgment passes through it.
PREDICTIONS: F5 rushing yards RB returns to yards given carries (no imposed-zero mass beyond the floor; CRPS below 14.34 as its parent is better); F8 RB CRPS below the
   batch 36 3.2485 with bias toward 0; F8 RB label one band from DECISION-QUALIFIED or qualified (layer 1 0 -> 1 if so).
WORK ORDER (appended): WO39-L settled by (A).  WO40-G settled by (B).  WO39-C (RB share center), WO39-R (catch-rate level), WO38-R, WO38-T, WO38-Q, WO38-Z carried.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## SPRINT 40 - OUTCOME; THE LUCK MAP; SPRINT 41 - THE SHRUNK EFFICIENCY - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
Batch 40 (graded): THE LINK RESTORED - RB rushing yards drawn given the share law's carries again (marginal changed .686 -> .00005); F8 RB CRPS 3.2680 -> 3.2418, below
   batch 36's 3.2485 (season gains over batch 36 +.013 -.007 +.015 +.006, p .005), bias -.029, L .074 U .098 - still CENTER TOO LOW (L).  Layer 1: 0 -> 0 qualified; the
   first F8 cell to gain beyond chance this window.  Rungs 33 / 15 / 20 -> 34 / 15 / 19; DECISION-QUALIFIED 17.
OWNER DIRECTION (Oct 7 2026 09:32): "find what's luck and what's forecastable under a stat's sub-root - never just predict the stat; the stat is a composition of
   factors."
THE LUCK MAP (luck_map_read, walk-forward, empirical Bayes by the population's own variance): reliability w of the season-to-date rate and SKILL over the population:
   ROLE - forecastable: carry share RB w .96 skill +.63; target share WR / TE / RB w .90 / .89 / .84, skill +.56 / +.57 / +.37; attempt share QB w .98 skill +.40.
   OPPORTUNITY - partly: team attempts w .38 skill +.06; team carries w .43 skill +.04.
   EFFICIENCY and CONVERSION - luck: yards per carry RB w .002 (raw error 4.71 vs population 3.73); yards per reception WR / TE / RB w .14 / .00 / .00; yards per
   completion w .05; catch rate WR / TE / RB w .26 / .09 / .10; TDs per catch w .08-.13; rushing TDs per carry RB / QB w .06 / .05; passing TDs per completion w .17;
   completion rate w .33.  In every factor the shrunk rate beats the raw season-to-date rate in 4 of 4 seasons.
Five whys (why the centers miss): the laws center each stat on its season-to-date mean -> a stat is opportunity x role x efficiency x conversion -> the season-to-date
   mean carries each factor's luck at face value -> role is forecastable, efficiency and conversion are almost all luck (w .00-.17) -> the issued efficiency is the
   player's own luck.  Sub-root: the stat is centered whole, not composed from factors each weighted by its own reliability.
SPRINT 41 (one batch, one replay) - the first factor class: EFFICIENCY.  laws.efficiency_state (one producer of a player's pregame rate and units), laws.fit_efficiency
   (the luck map's estimator on seasons < s: mu, s2, tau2), laws.issued_efficiency (the one door: mu + w (rate - mu), w = tau2 / (tau2 + s2 / units)) - applied to the
   per-count rate of every yards given count cell: F5 receiving yards RB / WR / TE, F5 rushing yards RB / WR / TE (draws.count_yards_components), Q3 passing yards and QB
   rushing yards (the QB law rows).  Judged once per cell by THE CONFIRMATION GATE with the goal guard against the batch 40 product (proj/atlas_rows_batch40.csv.gz);
   issued while unjudged, then only EARNED cells.  The yards-count wall keeps judging its own form (the season-to-date rate).
REGISTERED GOALS (draws.efficiency_judgment): G1 F8 cells DECISION-QUALIFIED >= 1 (layer 1 0 -> 1); G2 F8 CRPS lower at every position; G3 yards cells EARNED >= 6 of 8;
   G4 atlas DECISION-QUALIFIED cells do not fall; G5 F5 rushing yards RB nonzero L moves toward .10 from .031.
PREDICTIONS: yards cells' CRPS fall (the per-unit error falls 15-21% in the luck map); F8 gains at RB, WR, TE and QB; the yards L tails move toward .10.
NEXT FACTOR CLASSES (work order): WO41-C conversion (TD rates per touch: QB rushing TDs, Q4 passing TDs, F5 TDs) shrunk the same way; WO41-O opportunity (team volume,
   w .4); WO41-R the catch rate where L1 is not earned (TE).  Carried: WO39-C, WO38-R, WO38-Q, WO38-Z.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## SPRINT 41 - OUTCOME; THE CENTER LINES; SPRINT 42 - THE SHRUNK CONVERSION - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
Batch 41 (graded): THE SHRUNK EFFICIENCY - the yards cells gained (receiving yards RB 8.049 -> 7.928 4/4, WR 14.861 -> 14.767 4/4, QB rushing yards 8.453 -> 8.295 4/4)
   but F8 RB 3.2418 -> 3.2696 and F8 WR 3.1060 -> 3.1161 lost beyond chance: the goal guard refused RB / WR cells; Q3 passing yards 44.12 -> 44.78 (0/4) FAIL; TE receiving
   UNRESOLVED; QB rushing yards EARNED (p .003).  Layer 1: 0 of 5; QB F8 4.6392 -> 4.6279.  The guard held the goal: without it six cells would have been issued.
THE CENTER LINES (center_slope_read, the batch 40 product, walk-forward outcome = a + b x issued center): F8 itself over-reacts - b QB .83-.85, WR .85-.88, RB .93,
   TE .95-.99.  CONVERSION over-reacts most: Q4 passing TDs b .54-.60, QB rushing TDs .38-.56, F5 TDs TE .33-.40, WR .74-.79 (RB 1.01-1.11: the volume-anchored law
   is calibrated).  OPPORTUNITY: team carries b .36-.44, team attempts .68-.73, team targets .80-.83.  ROLE: RB carries (the control law) b 1.00-1.03; QB attempts /
   completions / passing yards UNDER-react, b 1.12-1.24 (the issued QB volume is compressed - the exits mixture).  Issued per-count rates: yards per reception RB b .03-.08,
   WR .28-.30, TE .22; yards per carry RB .09-.11; QB yards per completion .23-.73 (the line loses 2/3 - Q3's FAIL); QB yards per carry .30-.41.
Five whys (QB F8 CENTER TOO HIGH, b .84): the F8 center over-reacts -> its parts' centers: passing volume under-reacts (b > 1), passing and rushing TD centers
   over-react (b .38-.60) -> the TD centers are each QB's season-to-date TD mean, a conversion factor that is mostly luck (luck map w .05-.17) multiplied into his own
   volume -> the stat is centered whole, not composed: parent count x a conversion rate weighted by its reliability.  Sub-root: the conversion factor is issued raw.
   (Sprint 41's lesson kept: the rate shrunk is the raw season-to-date rate whose reliability the luck map measured - one estimator, one reliability.)
SPRINT 42 (one batch, one replay): THE SHRUNK CONVERSION - laws.FACTORS (one table: numerator, denominator, kind), fit_efficiency with the binomial per-unit variance
   for a proportion, issued_efficiency (no units observed -> the population rate).  Q4 passing TDs = expected completions x the shrunk passing TDs per completion; QB rushing
   TDs = expected QB carries x the shrunk rushing TDs per carry; nonzero rows, layer CONVERSION_LAYER (9), Poisson (the QB TD link still orders TDs on completions).
   Judged once per cell by THE CONFIRMATION GATE with the goal guard against the batch 40 product; disclosed: this replay also issues sprint 41's earned QB rushing yards
   and drops its failed Q3 shrink, both in the QB F8 reading.
REGISTERED GOALS (draws.conversion_judgment): G1 F8 QB DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED >= 1; G3 F8 QB bias moves toward 0; G4 both TD cells EARNED.
PREDICTIONS: QB rushing TDs bias +.088 -> about 0 and CENTER TOO HIGH resolved; Q4 passing TDs shape tightens toward the line (b .55); F8 QB bias +.77 falls by the
   rushing TD part (+.35 DK); the rest of QB F8's center is exits and team attempts (b .70) - sprint 43.
WORK ORDER (appended): WO41 settled (efficiency: QB rushing yards earned; the yards per-count rates' b .03-.30 confirms luck, but the F8 composition refused them - the
   F8 interaction with the yards rate is open, WO42-Y).  WO42-O opportunity: team carries b .4, team attempts b .7.  WO42-Q the QB volume under-reaction (b 1.12-1.24).
   WO42-T TE TDs b .37.  Carried: WO38-R, WO38-Z.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## SPRINT 42 - OUTCOME; SPRINT 43 - THE SHRUNK OPPORTUNITY - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
Batch 42 (graded): THE SHRUNK CONVERSION - Q4 passing TDs CRPS .6360 -> .6159, MISCALIBRATED -> DECISION-QUALIFIED, EARNED (calibration route; 4/4, p .0022);
   QB rushing TDs CRPS .2002 -> .1894, bias +.088 -> +.006, EARNED (p .0018).  F8 QB 4.6392 -> 4.6104, bias +.774 -> +.554, still CENTER TOO HIGH (L .124, cov.25 .285).
   Layer 1: 0 of 5 F8 cells qualified (flat).  Layer 2: atlas DECISION-QUALIFIED 17 -> 18.  F8 RB 3.2418, WR 3.1060, TE 2.1908 unchanged.  G1 / G2 NOT MET; G3 / G4 MET.
Five whys (QB F8 CENTER TOO HIGH, bias +.554 after conversion): the F8 center is too high -> its remaining parts: passing volume and exits -> passing volume is the QB's
   share (the control law, b ~1) x the team attempts draw, and team attempts is CENTER TOO HIGH (bias +.633) with center line b .68-.73 (over-reacts) -> the team
   attempts mean is the spine's v1, a team's own history issued at full weight; THE LUCK MAP measured team volume reliability w .38 (attempts), .43 (carries) -> the
   opportunity factor is issued raw.  Sub-root: team opportunity is not shrunk by its own reliability toward THE LEAGUE TO DATE (L1524: the league's level moves by
   season, so the target is the season's league to date, never a pooled constant).  Team carries share the sub-root (b .36-.44; bias -.228, CENTER TOO LOW).
SPRINT 43 (one batch, one replay): THE SHRUNK OPPORTUNITY - laws.team_rate_state (replaces team_count_state; one producer state.team_volume): a team's count per game
   over its earlier games this season, those games, and the league's count per team-game over the season's earlier weeks.  laws.fit_opportunity on seasons < s:
   s2 = mean((x - rate)^2 / (1 + 1/games)) (x - rate carries the rate's own error; mock: s2 34.4 vs truth 34, tau2 4.1 vs truth 4 over 20 draws), tau2 = the
   games-weighted variance of (rate - league) - its sampling part, at least 0.  laws.opportunity_mean, the one door: league + w (rate - league), w = tau2 / (tau2 + s2/games);
   no earlier game -> the league to date; unissued -> the incumbent.  Readers rerouted: F2 team attempts' mean (was v1), F2 team carries' mean and the RB share law's
   rb_team_mean (was the raw rate).  One estimator, one reliability: the rate shrunk is the raw rate the reliability is measured on (sprint 41's lesson).
   Disclosed: the NB sizes stay fit on the incumbent means (team attempts on v1, team carries on the raw rate); team targets' share stays m_Ttargets / m_Tattempts.
   Judged once per cell by THE CONFIRMATION GATE with the goal guard (attempts -> QB F8, carries -> RB F8) against the batch 42 product (atlas_rows_batch42).
REGISTERED GOALS (draws.opportunity_judgment): G1 F8 QB DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED >= 1; G3 F8 QB bias moves toward 0; G4 both team volume
   cells EARNED; G5 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: team attempts bias +.633 -> toward 0 and its center line b toward 1; Q1 - Q3 centers fall with it; F8 QB bias +.554 falls (attempts are the largest
   remaining part, exits the rest); team carries' over-reaction (b .4) falls, CRPS falls; F8 RB holds or improves.  Falsifier: if team attempts' bias holds, the
   center's excess is not reactivity but level (v1 vs the league to date) - read before any further shrink.
WORK ORDER (appended): WO42-O landed here.  Open: WO42-Q QB volume under-reaction (b 1.12-1.24) / the exits mixture; WO42-Y the F8 interaction with the yards rate;
   WO42-T TE TDs b .37; TE catch rate; WO43-N the NB sizes refit on the issued means if the cells earn.  Carried: WO38-R, WO38-Z.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## SPRINT 43 - OUTCOME; THE ABSENCE KINDS; SPRINT 44 - THE PLAYING TIME - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
Batch 43 (graded): THE SHRUNK OPPORTUNITY - F2 team carries CRPS 4.3296 -> 4.1807 (4/4, p .0000) EARNED, bias -.228 -> -.232 held (the registered falsifier: its
   excess is level, not reactivity); F2 team attempts bias +.633 -> +.036 as predicted, CRPS 4.3251 -> 4.3145 (3/4, p .28) UNRESOLVED - not issued from here.  Q1 / Q2 ->
   DECISION-QUALIFIED; Q3 -> TOO WIDE (WO43-N).  Layer 1: 0 of 5 (QB F8 4.6104 -> 4.6115, bias +.554 -> +.355); layer 2: 18 -> 20.  Owner: no re-freeze until every goal is met.
THE READS (qb_joint_read, playing_time_read, absence_kind_read; batch 43 product): QB F8 center .500 in band, yet L .118; its parts' lower tails calibrated.  A first
   draft (one partial / full boolean at the snap ceiling, a per-QB exit trait w .44) was HELD before running - owner: "partial" is a constructor hiding three kinds of
   absence, as THE THREE ZEROS hid theirs.  Read by co-reference to the team's QB ledger (no class authored), the issued QB games are: full .694 (F8 L .059, bias -.90 -
   the blend drags it low); role absence .060 (out-snapped, not the incumbent: F8 L .286, bias +6.2, Q1 +11.7; PERSISTENT - .716 again after one, .011 after a full game:
   forecastable, a participation fact); early exit .025 (out-snapped after leading the team's previous game: F8 L .868, bias +13.8; .030 after a full game, base rate:
   luck); the leader below the ceiling .205 - the others' snaps carrying passes (r > 0: L .23-.39, bias +2 to +7, a late exit) or none (r = 0, .40 of them: L .05-.06,
   his role unchanged - shared snaps, no absence); unknown .016.  F8 bias sum +537 = role absence +566, early exit +524, leader below ceiling +423, full -946.
Five whys (QB F8 L .118, bias +.355): too many outcomes below P10 -> they are role absences and exits -> every QB root draws one law blended over full games, exits
   and games he was not the starter -> no door reads the absence kind; "played" is the only participation fact and the role is fit over every kind -> sub-root: the
   absence kind is not a state of the composition (stat = playing time x opportunity x role x efficiency x conversion; playing time = its absence kind x its fraction).
SPRINT 44 (one batch, one replay): THE PLAYING TIME (layer PLAYING_TIME_LAYER 10, QB).  laws.absence_kinds - one producer of every game's kind from the ledger (the
   snap argmax; THE INCUMBENT = the leader of the team's previous game; the others' attempts on the remaining snaps); laws.absence_state (his last game's kind);
   laws.fit_playing_time on seasons < s over the law's own population: P(regime | previous kind) - the transition table measured (no absence = full + shared snaps; exit =
   early + late; role absence), the marginal for a state never seen, each regime's own snap fractions (no absence: the full games'); unknown kinds enter no estimate.
   The QB role = the control law fit on the games of no absence (fit_share_control takes its outcome games: RB and the QB control pass every played game - unchanged).
   Issued: Q1 = binomial(team attempts draw, Beta(role) x f); QB carries, Q4 passing TDs, QB rushing TDs = the final law per full game (mean / E[f]) binomially thinned by
   f (mean preserved).  f: one draw per QB-game from its own keyed substream - the regime by his probabilities, the fraction from that regime's games; every root reads
   the same f; the children (Q2, Q3, QB rushing yards) inherit.  draws: three families with their moments.  Mock-verified: the ledger recovers full, late exit, shared
   snaps exactly; the first game of a benching reads as an early exit (the ledger has no in-game timing) and the transition table carries what follows it.
   Disclosed: Q5 interceptions not thinned (WO44-I); the NB sizes stay fit on the blended means (WO43-N); QB only (WO44-S).  Baseline: the batch 42 product - for every
   QB cell the same laws but the playing time (sprint 43's UNRESOLVED team attempts is not issued).
REGISTERED GOALS (draws.playing_time_judgment): G1 F8 QB DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED >= 1; G3 F8 QB L moves toward .10; G4 F8 QB bias moves
   toward 0 in full games and in role absence; G5 every playing-time cell EARNED; G6 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: QB F8 L .124 (batch 42) -> about .10; full-game bias -.9 rises toward 0 (the full regime's role is no longer diluted); role absence bias +6.2 falls (the
   persistent state carries P(role absence) ~.7 after one); early exits stay mostly in the lower tail (luck priced at ~.03); QB F8 CRPS below 4.6104.  Falsifier: if
   role-absence bias holds, the participation fact lives before the ledger (who is issued) - the issue's QB roster, not the law.
WORK ORDER (appended): WO44-P landed here.  Open: WO43-N NB sizes on the issued means; WO44-I Q5 thinning; WO44-S skill-position absence kinds; WO43-L team carries'
   level (bias -.23); WO42-Y, WO42-T, TE catch rate.  Carried: WO38-R, WO38-Z.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## SPRINT 44 - CORRECTION BEFORE ANY VERDICT - THE ROLE FIT - Oct 7 2026
Batch 44 passed the guard, then replay-all refused at the 2023 cutoff: "fit_share_control QB attempts: seasons < 2023 did not converge (ABNORMAL)" - the QB role, fit
   as the beta-binomial control law on the games of no absence.  Nothing was graded; no verdict was written; the atlas on disk stayed the batch 43 product (the ladder's
   witness reproduced it).  Five whys: the line search failed -> the beta-binomial concentration's maximum lies at infinity -> in the games of no absence the QB's share
   sits at its ceiling with no spread beyond the binomial -> the control law's form (a concentration that is exp of a line) cannot reach the binomial -> sub-root: the
   role was handed a family whose boundary is not in its domain.  Mock: the beta-binomial fit refuses (ABNORMAL) on a ceiling share; the binomial fit converges.
REMEDY (batch 44b, one replay): laws.share_control_rows - the control law's fitted rows, one producer for its two fits; fit_share_control reads it (RB and the QB control:
   mock bit-identical); laws.fit_role - the role's mean expit(x b) by maximum likelihood under the binomial, then its one concentration given mu by fit_concentration on
   GRID (the existing door, infinity included); the playing-time share family draws the share as its mean where the concentration is infinite (the existing share
   family's rule).  Registration, goals, predictions and baseline of sprint 44 unchanged.
## SPRINT 44 - OUTCOME; THE SPINE RECONCILED; T0 - THE BASELINE OF RECORD - REGISTRATION - Oct 7 2026 (before code)
Batch 44b (graded): THE PLAYING TIME - Q1 attempts, Q4 passing TDs, QB carries, QB rushing TDs FAIL (verdicts on file).  QB F8 qualified in that replay by widening
   (L .124 -> .114) while its parts lost (Q1 CRPS 5.142 -> 5.331, 0/4; full-game Q1 4.48 -> 4.60); early exits unmoved (F8 L .868 - luck, L452); role absence worse
   (F8 CRPS 4.03 -> 4.27): the role law fit on starter games gave a backup a starter's share.  The registered falsifier fired (role-absence bias +6.3 -> +6.6).
OWNER RULINGS RECONCILED WITH THE CHARTER (five gaps, five whys each; collapsed where one invariant was guarded from two sides):
   (1) Week-N availability (report, practice, roster status): Y's information set is unchanged (L140-142, guard check 10).  The owner's yes is Y_late - L327: "a new
       forecasting problem, never an amendment to this Y"; inputs exist 2019-25 (L3094); its own information-set registration, timestamp, backtest, freeze and
       confirmation; outside Y's Done.  The game line stays out of participation in both tracks (L55, market-last).
   (2) Two gates, one owner each: ROOT - a cell judged on its own proper score, calibration first (L245, L403), at the first unresolved owner (L3024);
       INTEGRATION - F8 against the current product, lexicographic: the label may not fall; label unchanged -> CRPS may not rise beyond chance; label improved at the
       owner -> CRPS at most the cell's witness_v4 value.  Issued iff both pass; the root verdict stays trinary.  Built with its first reader (T1), not before.
   (3) Verdicts whose inputs change (L2513, open since its registration): frozen; re-judged only on evidence that did not exist at the judgment, a preregistered
       instrument, or a mechanical / accounting defect (L403).  L2513 closes.  An UNRESOLVED candidate never frozen gets no prospective evidence (shadow trials
       withdrawn, L3003): team attempts stays unknown.
   (4) F8 is consequence-only (L2592, L3114); a participation intervention is judged on the participation state's own score.
   (5) Dead code is deleted, never flagged (CONSTRUCTORS); a retry rebuilds from this record.
READS (yards_count_verdicts, variance_read_report, composition_read_report): yards given count EARNED in all three cells (WR receiving +.118 F8 4/4, TE receiving
   +.032, RB rushing +.050).  First unresolved owner per position (L3024 center -> dispersion -> shape -> dependence): WR - spread by usage state (law DK variance
   / realized .888, F8 tail by usage tercile .14 / .24 / .37; owned by target share, air-yards share and DK level); RB - rushing-yards lower tail (L .032), then
   rushing yards x TDs (law +.071, realized +.358; eigen +3.65); TE - its center (catch rate high, L5727; TD conversion raw, b .37), then TDs x volume (law .00-.11,
   realized .27-.30); QB - the exposure state (snap-share level and change own Q1, Q2, Q3 and F8 tails; role absence persistent .716 vs .011 - history only, legal in
   Y, Y being given he plays).  RB carries and TE receptions: no state owns their width - that route closes for them (as registered).
THE SPINE (first unresolved owner per position, ordered by F8 rows): T0 baseline; T1 WR spread by owning state (+ WO43-N audit: every dispersion fit around the
   mean its law issues); T2 RB lower tail, then yards x TDs; T3 TE center, then TDs x volume; T4 QB exposure state from history; T5 accounting (TD ledger
   receiving-only, WO38-R on played totals); T6 team volume (L1232 resolution limit); T7 reads (Q8, Q10, Q13, Q14, WO44-S); coverage after T3 (L4250).
T0 (one batch, one replay): laws.py and draws.py are batch 43's exactly - the playing-time code (laws.absence_kinds .. playing_time_issue, fit_role, its families,
   draws.playing_time_judgment) is deleted; proj/playing_time_verdicts.csv stays as the record and nothing reads it.  No law changes from batch 43 but by the
   verdicts on file: sprint 43's UNRESOLVED team attempts is not issued (v1 again), its EARNED team carries is.
PREDICTION (the baseline of record): the QB block equals batch 42 exactly - QB F8 4.6104 (bias +.554), Q1 5.1420, Q2 3.6102, Q3 44.1182; RB F8 3.2409 (team carries
   kept); atlas DECISION-QUALIFIED 18 (batch 43's 20 counted Q1 / Q2 qualified only through the unearned attempts shrink); every verdict file unchanged.
   Falsifier: any QB value different from batch 42 - the deletion missed a reader.
WORK ORDER (appended): WO44-P settled FAIL; WO44-R becomes T4 (history only) and Y_late (separate track); WO43-N folds into T1; WO44-S into T7; WO38-Z settled
   (graded_evidence flips per slate).
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T0 - OUTCOME; T1 - THE ROLE - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
T0 (batch 45, graded): every prediction held - QB F8 4.6104 (bias +.554), Q1 5.1420, Q2 3.6102, Q3 44.1182, RB F8 3.2409, atlas DECISION-QUALIFIED 18, verdict files
   unchanged.  The baseline of record is proj/atlas_rows_batch45.csv.gz.
THE READ (usage_width_read, batch 45 product; WR rows by terciles of the issued targets center): the WR chain over-reacts and its width ignores usage - targets
   center slope b .88, bias -.32 / -.02 / +.40, variance realized / issued with the bias removed 2.07 / .98 / .79; receptions b .85, 2.49 / 1.06 / .70; receiving
   yards b .82, 2.05 / 1.03 / .71; F8 b .87, 2.03 / 1.19 / .81, tail share .210 / .200 / .160.  The bias is small beside the width: two defects, one owner.
Five whys (WR F8 CENTER TOO LOW; tails too thin at low usage, too fat at high): the F8 width tracks the usage center -> so do targets, receptions and yards, all
   children of the targets draw -> the targets law is the share of the team draw at the raw season-to-date share (center b .88) with one beta concentration per position
   -> a beta's share variance scales with p (1 - p), the realized share variance barely does (a teammate out moves a low-share WR by as much as a starter) -> sub-root:
   the role's center and spread are not the share's own posterior predictive (THE LUCK MAP's estimator gives both).
T1 (one batch, one replay): THE ROLE (layer ROLE_LAYER 10, WR targets).  laws.ROLE_FACTORS ("F5 targets", "WR"): targets per team target (team_targets on the played
   rows from state.team_volume, one producer); fit_efficiency and issued_efficiency reused (the share shrunk by w = tau2 / (tau2 + mu (1 - mu) / units));
   laws.fit_role_spread - the game-level role variance delta2 (squared share error about the shrunk center less its binomial part and the center's posterior
   variance, method of moments, floor 0); laws.role_variance = tau2 (1 - w) + delta2 (no units -> tau2 + delta2).  Issued: share of the team targets draw,
   beta-binomial at mean m, concentration m (1 - m) / v - 1 per row (defined where positive; elsewhere the incumbent).  Mock: tau2 .0059 vs .0062 planted, delta2
   .00084 vs .0009, every row defined.  Receptions (L1), receiving yards (given count, earned) and TDs (L3) inherit through the targets draw.
THE TWO GATES (built here, their first reader): ROOT - F5 targets WR nonzero by THE CONFIRMATION GATE on its own score; INTEGRATION (draws.integration_check) - WR
   F8 against the baseline of record: a label may not fall; unchanged -> no CRPS loss beyond chance (goal_losses); risen -> CRPS at most its witness_v4 cell mean.
   proj/role_verdicts.csv: verdict = the issue decision (EARNED only if both pass; "EARNED - NOT INTEGRATED" otherwise), root_verdict and integration beside it.
   Disclosed: team targets keeps its v1 level (+.56, WO26 FAIL on file) - its share of the high-usage bias stays.
REGISTERED GOALS (draws.role_judgment): G1 F8 WR DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED >= 1; G3 WR targets center slope moves toward 1; G4 the WR F8 tail
   share gap between the usage terciles' ends narrows; G5 the role EARNED and integrated; G6 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: WR targets b .88 -> about 1, its bias by tercile toward 0; WR F8 tail share .210 / .200 / .160 -> about .20 each; WR F8 L .088 -> toward .10; F8 WR CRPS
   at most 3.1060.  Falsifier: if targets b reaches 1 and WR F8's tails by usage stay apart, the width owner is downstream (yards per catch by usage) - read first.
WORK ORDER (appended): T1 here.  Next by the spine: T2 RB (rushing-yards lower tail, then yards x TDs), T3 TE (center, then TDs x volume), T4 QB exposure state.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T1 - OUTCOME; T1b - THE CATCH - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
T1 (batch 46, graded): THE ROLE FAIL (proj/role_verdicts.csv).  ROOT - F5 targets WR CRPS 1.3430 -> 1.3534, gains -.0041 / -.0041 / -.0123 / -.0173, p .96; its label
   CENTER TOO LOW -> MISCALIBRATED (shape), while its calibration by usage was repaired (tails .205 / .212 / .203, bias -.06 / +.00 / +.08, center slope .88 -> .94, G3
   MET).  INTEGRATION - WR F8 3.1060 -> 3.1082, loss beyond chance p .0003, REFUSED.  Receptions (slope .85), receiving yards (.82) and F8 (tails .211 / .200 / .159)
   did not move.  The registered premise was false: "receptions inherit through the targets draw" - WR receptions is its own negative binomial marginal at m_rec (laws
   F6 v1) and the L1 chain only reorders it by target ranks (dependence.chain_l1).  LESSON: a fix at a parent cannot integrate through a child that is not composed
   from it - read the child's law before registering inheritance.
THE READ (catch_given_targets_read; receptions given REALIZED targets, fit on seasons < s; terciles of targets n; tail share honest .20):
   WR  RAW (season-to-date rate, binomial) .290 / .280 / .282, var ratio 1.59 / 1.62 / 1.54; SHRUNK (binomial) .207 / .217 / .227; POSTERIOR (beta-binomial, v = tau2 (1 - w)
       + delta2) .209 / .211 / .200, var ratio 1.04 / 1.03 / .97; mu .63, tau2 .0026-.0033, delta2 .0011-.0017.
   RB  RAW .288 / .283 / .326; POSTERIOR .204 / .182 / .189, var ratio 1.03 / .93 / .96.   TE RAW .290 / .296 / .278; POSTERIOR .188 / .190 / .184, bias +.02 / +.08 / +.10.
   The conditional is the catch rate's posterior predictive.  L1680 (wall 1 conditionals too narrow, PIT sd .299-.314) and L5727 (beta-binomial at the raw rate fails;
   "the catch rate sits high") are the RAW row: precision without the shrunk center.  The center was the missing half.
Five whys (WR F8 tails by usage .210 / .200 / .160): F8's width tracks usage -> receptions' width tracks usage (width only 2.49 / 1.06 / .70) and the yards are drawn
   given receptions -> receptions is a count law at m_rec with one NB size per position, blind to how many targets the draw gives -> the stat is two factors
   (opportunity - targets, forecastable; catch - partly luck) predicted as one -> sub-root: receptions is not the catch rate's posterior predictive of the targets draw.
T1b (one batch, one replay): THE CATCH (layer CATCH_LAYER 11; F5 receptions WR and RB, state nonzero).  laws.CATCH_FACTORS: receptions per target (one table FACTORS,
   kind proportion; laws.fit_efficiency / issued_efficiency, one producer).  laws.fit_game_spread replaces fit_role_spread (one producer for the role and the catch):
   delta2 by the moment over trial pairs, Var(x | n) = n m (1 - m) + n (n - 1) V - T1's per-game form omitted the 1 - 1/n factor (negligible at team targets, not at a
   player's).  laws.share_variance replaces role_variance.  Issued: receptions beta-binomial of the player's own F5 targets draw at the shrunk catch rate m,
   concentration m (1 - m) / v - 1 (v = 0 -> the binomial); a row where no beta of that mean and variance exists refuses the replay (no substitute law).  The law
   states its center (the targets center x m) - the yards given count denominator, so the receiving yards center stays m_ryd before its earned shrink.
   draws.composed_components: a receptions law drawn from the targets draw is already ordered by it (co-reference: the law's own conditioned_on_draw); L1 orders the
   marginal laws only.  L3 (TDs on the composed receptions) unchanged.  Mock: tau2 .0027 vs .0025 planted; delta2 .0012 vs .0016 (its standard error about .0009 at
   9,600 rows - delta2 is weakly determined; the read shows the posterior calibrated with it); every concentration positive (58-140).
DISCLOSED: (1) The family string "share of the team draw (beta-binomial)" is reused - its sampler is a share of the parent draw; here the parent is the player's own
   targets draw.  (2) L2580 "receptions stay closed" closed the count's posterior-mean form (the Gamma-Poisson support law, FAIL, L2079-2080); T1b is a composition
   from the parent draw, on evidence that did not exist at that judgment (L2513 policy).  (3) WR targets stays the batch 45 law (T1 FAIL): its usage misfit (width
   only 2.07 / .98 / .79) is inherited by the composed receptions.  (4) TE goes to T3: its targets law (support negative binomial) has no laws-side center producer
   yet; the read shows the same remedy fits (POSTERIOR .188 / .190 / .184).
THE GATES (draws.catch_judgment): ROOT - F5 receptions nonzero per cell by THE CONFIRMATION GATE; INTEGRATION (draws.integration_check) - the position's F8 against
   the baseline of record proj/atlas_rows_batch45.csv.gz.  proj/catch_verdicts.csv: verdict = the issue decision (EARNED only if both pass), root_verdict and
   integration beside it.  Readings per position by the baseline's usage terciles: targets, receptions, receiving yards, TDs, F8 - tail, bias, width only, slope.
REGISTERED GOALS: G1 F8 WR DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED >= 1; G3 WR receptions tail share gap between the usage terciles' ends narrows; G4 WR F8
   tail share gap narrows; G5 the catch EARNED and integrated in every cell; G6 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: F5 receptions WR and RB CRPS fall; WR receptions width only 2.49 / 1.06 / .70 -> toward the targets law's 2.07 / .98 / .79 (inherited); WR F8 at most 3.1060
   with its tail gap (.210 vs .160) narrowing; RB F8 at most 3.2409; QB F8 4.6104 exactly (no QB law reads a receiver law); atlas DECISION-QUALIFIED at least 18.
   Falsifier: receptions CRPS rises while the conditional is calibrated (this read) - then the targets law's usage width owns receptions, and targets is the next
   owner (re-opened only on a new instrument).
WORK ORDER (appended): T1 FAIL with its lesson; T1b here.  Next by the spine: T2 RB (rushing-yards lower tail, then yards x TDs), T3 TE (center: the catch composition
   with its targets center producer; TDs x volume), T4 QB exposure state.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T1b - OUTCOME; THE GATE BENCH; OWNER RULING - THE SEASON GATE; M0a - THE SEASON GATE AND ITS RE-JUDGMENT - REGISTRATION - Oct 7 2026 (before code)
T1b (batch 47, graded): THE CATCH EARNED and integrated in both cells (proj/catch_verdicts.csv).  F5 receptions WR CRPS .9834 -> .9719, 4/4, CENTER TOO LOW ->
   DECISION-QUALIFIED (calibration route); RB .8294 -> .8247, 4/4, p .023.  WR F8 3.1060 -> 3.0808 (below witness_v4 3.1059), usage tail gap .051 -> .012 (G4 MET);
   RB F8 3.2409 -> 3.2402; QB F8 4.6104 exactly (prediction held); atlas DECISION-QUALIFIED 18 -> 19; rungs 30 / 16 / 22.  WR F8 stays CENTER TOO LOW on its lower
   quantiles (coverage q .10 .092, q .25 .238; bias +.10).  Owed from T1b: L3 and wall 9 re-judged on the new marginals (not registered before landing).
THE GATE BENCH (gate_bench_read; 107 cells whose CRPS changed between consecutive products, batches 36-47; null worlds from each cell's own data): the slate
   sign-flip gate (graded_evidence) holds its .05 where seasons agree (false pass .047-.052) and inflates where they differ - .133 in the top tercile of season
   spread (tau / sigma .19-.71), up to .27.  The R-gate alone passes a zero effect half the time (.502).  This is the p.gate audit's finding, now on every cell.
THE GATE PROOF (gate_proof_read; 104 cells; criterion registered in the probe before any result): SLATE false pass .049 / .048 / .140 by spread tercile (trend p .0000)
   - NOT CONSISTENT; SEASON (one-sided t on the season mean gains, df = seasons - 1) .047 / .037 / .051 under normal season effects, .046 / .039 / .051 under
   resampled ones, no trend - CONSISTENT, PROVEN MORE CONSISTENT than SLATE; BOTH not consistent.  Power at 2 / 3 standard errors: SEASON .49 / .76 (SLATE .72 / .94,
   inflated).  Cost disclosed: with four seasons a real gain needs about 3 standard errors to pass; more small gains read UNRESOLVED.
OWNER RULING (Oct 7 2026): verdicts are re-judged under the new gate if it is truly proven more consistent and confident.  (The proof above is that evidence; a
   preregistered instrument under the verdict policy, L2513.)  Noted by the owner and held by the kit: each week is forecast from weeks before it only (the guard's
   PURE witness at nine cutoffs); weeks 1-3 are not graded; every season's fit reads seasons before it.  The gate judges finished scores, never feeds a forecast.
M0a (one batch, one replay): THE SEASON GATE.  draws.season_chance (one producer): p = P(T >= t), t on the season mean gains, df = seasons - 1.  graded_evidence returns
   it in place of the slate sign flip (its label argument deleted with the flips); draws.chance_verdict - the CRPS route's verdict, one producer for the confirmation
   gate and the re-judgment.  Every gate that reads graded_evidence (confirmation, goal_losses, integration, coupling) reads the season test from here on.
   draws.season_gate_rejudge (once, proj/season_gate_verdicts.csv, before the replay builds its inputs): each verdict by its own gate, only the chance test changed -
   the paired files (efficiency 40 -> 41, conversion 40 -> 42, opportunity 42 -> 43, catch 45 -> 47, rb control 36 -> 39, Poisson dispersion 37 -> 38, third cumulant
   36 -> 37) with the season gains recomputed (witness: their mean equals the recorded mean gain, else refused before any write), recorded labels, goal_losses, the
   noise-like F8 rule and the integration gate where each carried them; the R-GATE-era files whose season gains are on file (dispersion, empirical zero-state, Q1 snap,
   QB control, QB TD link, shrink, TD x yards, TE TD link, team pass, yards given count - its yards gains, the owner cell, I8) by chance_verdict.  Outside, each named
   with its reason: role (FAIL, product gone, negative mean - FAIL under any gate), playing time (arm deleted), team shuffle, ledger shuffle, receiver yards link, team
   center (team-stack season gains not on file - owed), rearrangement (WO38-R - owed); the procedure wall's own whole-pipeline sign-flip null (a separate command - owed).
   Each re-judged file keeps its prior verdict as verdict_slate_gate beside season_t_p and season_gate_route; readers read verdict, unchanged.
PREDICTIONS (season gains on file computed before code): dispersion F5 receptions RB EARNED -> UNRESOLVED (p .140); empirical zero-state F5 TDs WR EARNED ->
   UNRESOLVED (p .246); Q1 snap EARNED -> UNRESOLVED (p .397); shrink F5 receiving yards TE / WR EARNED -> UNRESOLVED (p .387 / .058); held - empirical zero-state RB
   receiving yards (.0006), QB control Q1 / F8 (.025 / .008), QB TD link (.027), shrink TE TDs / RB receiving yards (.040 / .036), TD x yards RB (.024), TE TD link
   (.0495), team pass Q1 (.032), yards given count (.0002-.0003).  From the bench's matching pairs: efficiency F5 receiving yards RB / WR FAIL -> EARNED (the F8 losses
   that failed them are within chance by season: p about .08 / .07; own gains p .004 / .010); efficiency RB rushing yards FAIL -> UNRESOLVED (p .15); Poisson
   dispersion Q1 attempts EARNED -> UNRESOLVED (p .45); third cumulant TE rushing yards EARNED -> UNRESOLVED (about .07); conversion, opportunity and catch hold.
   RB control (36 -> 39, 3 of 4 seasons positive) is not on the bench - read in the output.
   The product moves where a flip is issued: shrunk yards per catch for RB and WR receiving yards (their F8 point estimates were negative in batch 41: -.027 / -.010),
   TE rushing yards loses its third cumulant, WR TD zero rows lose the empirical zero-state law, Q1's snap and dispersion layers leave (team pass, layer 7, sits above
   both).  Reading registered: each F8 cell against the batch 47 product; an F8 cell losing beyond chance (season gate) names the flips at its position in the work
   order as the next landing - a re-judgment ruled by the owner is not reversed by its consequence.
WORK ORDER (appended): T1b EARNED; L3 / wall 9 on the new marginals owed; M0a here; M0b readings print no verdict words (14 judgment functions recompute and print
   verdict words every replay); M0c WO38-R; team-stack verdicts' season gains (owed); the procedure wall's null.
LANDING CONTRACT: snapshot laws.py, draws.py, CHARTER.md and every verdict file before writing; restore them whole if the guard refuses.
## M0a - OUTCOME; T2 - THE SHARE (RB WIDTH) - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
M0a (batch 48, graded): THE SEASON GATE - 86 verdicts re-judged, 27 changed (proj/season_gate_verdicts.csv).  Layer 1: 0 -> 1 of 5 - WR F8 DECISION-QUALIFIED
   (3.0808 -> 3.0770; shrunk yards per catch for RB and WR EARNED, p .004 / .010).  RB F8 3.2402 -> 3.2774, CENTER TOO LOW -> TOO NARROW, 0/4 seasons: the RB control
   law (p .083) and NB1 on RB targets (p .112) are UNRESOLVED and left - RB carries PIT sd .359, RB targets .319, RB receptions .315.  QB F8 4.6104 -> 4.6121; TE
   unchanged; team stack in band (.093 / .093); atlas DECISION-QUALIFIED 19; rungs 31 / 17 / 19.  The registered reading fired at RB: its flips name the next landing.
   Mechanical defects in the re-judgment record, no product effect (only EARNED is read): (1) the RB control law was re-judged with the goal guard of sprint 40, which
   it never carried - under its own gate it reads UNRESOLVED (p .083), recorded FAIL; (2) empirical zero-state QB carries and QB rushing yards, UNRESOLVED (a test
   season without graded rows), were recorded FAIL from empty season gains - unmeasured is unknown, never no (Law 5).  Both corrected with M0b.
THE READS: rb_share_read - the share's posterior predictive given the realized team count: RB carries tails .247 / .238 / .202 (raw .41 / .54 / .44), RB targets
   .202 / .198 / .226, WR targets .206 / .219 / .210.  Its law() fell back to the binomial where v >= m (1 - m) - my defect; variance_form_read on six cells: the ADDED
   game variance (delta2) leaves 578 of 7,651 RB carries rows (7.6%) with no beta of that mean and variance; the PROPORTIONAL form (kappa m (1 - m)) leaves none, and
   its log score is at least ADD's on every cell (RB carries -2.5775 vs -2.6593, RB targets -1.6145 vs -1.6274, WR targets -2.0049 vs -2.0201, receptions WR / RB / TE
   equal).  The data's own choice (registered in the probe): PROPORTIONAL.
Five whys (RB F8 TOO NARROW): RB F8 tails .228 / .273 / .297 by usage -> carries, targets and receptions are too narrow -> carries and targets are Poisson at their
   season-to-date means, the counts' width owned by nothing since the season gate -> a back's carries move with his share of the team's carries (committee, script,
   a teammate out), drawn apart from its structural parent (the class sprint 39 named, I2) -> sub-root: the RB counts are not their share's posterior predictive of
   the team draw (the estimator that earned the catch).
T2 (one batch, one replay): THE SHARE (layer SHARE_LAYER 12; laws.SHARE_FACTORS - F5 carries RB per team carries, F5 targets RB per team targets).  laws.share_law -
   one producer for the role and the share: the share shrunk by its reliability (issued_efficiency), variance share_variance, a beta-binomial of the team draw (no
   beta of that mean and variance refuses the replay); the WR role's branch reads it (FAIL on file, not issued).  fit_game_spread is the proportional moment (kappa)
   for every cell - the catch's spread follows it (disclosed: the catch was judged on the added form; its receptions log score is identical under both, -1.3640 /
   -0.9434).  The team carries law leaves the control law's block: issued every replay (layer CARRY_SHARE_LAYER, its NB size fit on seasons < s) - the RB share draws
   inside it; the control law keeps only its own rows (UNRESOLVED, not issued).  RB targets: the issued targets center (team targets x share) is the center the catch
   composes from (one producer).  Mock: kappa .116 vs .10 planted; every concentration positive down to a .004 share.
THE GATES (draws.gated_judgment - one producer for T1b and T2; catch_judgment reads it): ROOT per cell on its own nonzero cell; INTEGRATION on RB F8; against the baseline
   of record proj/atlas_rows_batch48.csv.gz.  proj/share_verdicts.csv.
REGISTERED GOALS: G1 F8 RB DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED do not fall (1 -> at least 1); G3 F5 carries RB nonzero not TOO NARROW; G4 F8 RB CRPS back
   to at most the batch 47 product's (3.2402); G5 the share EARNED and integrated in both cells; G6 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: RB carries PIT sd .359 -> about .29, CRPS 2.5958 -> below 2.5163 (the control law's); RB targets .319 -> about .29; RB receptions follow targets; RB F8
   3.2774 -> at most 3.2402, out of TOO NARROW; WR F8 3.0770 within .002 and still DECISION-QUALIFIED (the catch's spread form, measured equal); QB 4.6121 and TE
   unchanged exactly; F2 team carries graded again.  Falsifier: RB carries still TOO NARROW with its share calibrated (rb_share_read) - the team carries draw owns the
   width; read next.
WORK ORDER (appended): M0a graded; T2 here; M0b readings print no verdict words, with the two record corrections; M0c WO38-R; team-stack verdicts' season gains;
   L3 / wall 9 on the new marginals; TE receptions with its targets center producer (T3).
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2 - OUTCOME; T2b - THE DRIFT (THE RB CARRY SHARE AS A DISCOUNTED BETA) - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
T2 (batch 49, graded): F5 targets RB EARNED (CRPS .9712 -> .9458, 4/4, p .0024, TOO NARROW -> DECISION-QUALIFIED); F5 carries RB UNRESOLVED (2.5958 -> 2.5652, 2/4,
   p .17; TOO NARROW -> CENTER TOO LOW, bias -.133 -> -.273; tails by usage .41 / .48 / .39 -> .20 / .23 / .14).  RB F8 3.2774 -> 3.2479 (CENTER TOO LOW, only q .10
   coverage off at .087); WR F8 3.0772 DECISION-QUALIFIED; QB, TE unchanged; atlas DECISION-QUALIFIED 19 -> 20; rungs 29 / 18 / 21.  G2, G3 MET; G1, G4, G5 NOT MET.
   Defect found before the next replay (mine, batch 49): the T2 carries block sat between "if position == RB" and its else - with the share UNRESOLVED the else
   would add a second layer-0 carries law to every RB row.  Restored here.
THE READS: rb_carries_center_read - the RB carries center error N m - x = team part m (N - n) + share part n m - x: -.342 = -.064 + -.271; the incumbent (his team's
   leading back of the previous game) -.674 (m .499 vs .528), others with the incumbent playing +.202, the incumbent absent -4.32 (147 rows - his carries go to the
   others; the week-N roster would show it: Y_late; in Y it is luck, the others' mixture mean .174 against their issued .176).  rb_role_prior_read - a prior by role
   (incumbent mu .52 / others .16) barely moves it (log score -2.5661 -> -2.5652).  rb_drift_read - the share drifts: the method of moments over game pairs at lags
   1-4 gives drift q / game variance r .60-.68 every season; the drifting level fixes the center (share part -.181 -> +.006) but a Gaussian level on the share scale
   leaves 133-208 rows with variance above m (1 - m) and loses log score.  rb_discount_read - the bounded form, a discounted beta: delta .67-.68 by maximum likelihood
   (an earlier game's weight halves every 1.7-1.8 games), every row defined, log score -2.5661 -> -2.5166, share part -.181 -> -.082 (incumbent -.666 -> -.264,
   others +.356 -> +.279), tails .153 / .185.
Five whys (RB carries CENTER TOO LOW): the share part owns it -> the lead back is forecast low and the rest high -> each back's share is his season-to-date
   average -> a back's role moves inside a season (the drift is measured, q / r about .6) and the average trails it -> sub-root: the carry share's state is a
   season mean, not the level his recent games carry.
T2b (one batch, one replay): THE DRIFT (layer DRIFT_LAYER 13; laws.DRIFT_FACTORS - F5 carries RB per team carries).  laws.drift_states: the pregame Beta(a, b) from
   his earlier played games this season, pulled back toward the population prior (laws.fit_efficiency's mu, tau2) by delta before each game; laws.fit_drift: delta by
   maximum likelihood on seasons < s (bounded scalar search), kappa by the proportional moment at that delta.  Issued through laws.share_law (one producer) with a
   shape: posterior_shape (T1 / T2) or drift_shape (T2b) - beta-binomial of the team carries draw at m = a / (a + b), concentration 1 / (1 / (a + b + 1) + kappa) - 1.
   Mock: delta .679, kappa .175 on a planted drifting share; first-week rows at the prior exactly.
THE GATES (draws.gated_judgment): ROOT on F5 carries RB nonzero; INTEGRATION on RB F8; against proj/atlas_rows_batch49.csv.gz, whose RB carries are the unjudged T2
   share - stricter than the issued product (Poisson carries again, T2 carries UNRESOLVED).  proj/drift_verdicts.csv.
REGISTERED GOALS: G1 F8 RB DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED do not fall (at least 1); G3 F5 carries RB nonzero neither TOO NARROW nor CENTER TOO LOW;
   G4 F8 RB CRPS at most the batch 47 product's 3.2402; G5 the drift EARNED and integrated; G6 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: RB carries bias -.273 -> about -.15 (share part -.08 and the team part -.06 remain), CRPS 2.5652 -> lower, tails near .20 by usage; RB F8 3.2479 -> lower,
   toward 3.2402; WR F8 3.0772, QB 4.6121 and TE unchanged exactly.  Falsifier: carries CRPS no better than the T2 share's though the read's log score gained .05 -
   the gain lives in rows the atlas does not grade (the incumbent-absent luck), read next.
WORK ORDER (appended): T2 graded (targets EARNED, carries UNRESOLVED); T2b here; the class question - WR targets (the role) and RB targets on the drifting share;
   the team carries center (team part -.064, F2 team carries CENTER TOO LOW); M0b readings without verdict words and the two batch 48 record corrections; M0c WO38-R.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2b - OUTCOME; T2c - THE YARDS SHAPE (RB YARDS GIVEN THEIR COUNT) - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
T2b (batch 50, graded): THE DRIFT EARNED - F5 carries RB 2.5652 -> 2.4732 (4/4, p .0018; better than Poisson 2.596, the control law 2.516, the T2 share 2.565), bias
   -.273 -> -.173, still CENTER TOO LOW; RB F8 3.2479 -> 3.2466, CENTER TOO LOW on q .10 coverage alone (.087); WR F8 3.0772 DECISION-QUALIFIED; QB, TE unchanged;
   atlas DECISION-QUALIFIED 20.  G2, G5, G6 MET; G1, G3, G4 NOT MET.  The restored if / else held (one carries law per RB row).
THE READS: rb_rushing_read - given the realized carries the RB per-carry rate has no between-back signal (tau2 .000-.005; yards per carry is the population's, about
   4.3): the shrunk rate lowers CRPS 10.35 -> 9.49 against the raw season-to-date rate, bias by usage small either way (the atlas's -3.4 / -2.5 / +1.9 is the count's);
   the normal law is too wide in the bulk with a lower tail too long (tails .07-.13, L .01-.05).  (Its drift line is INVALID - one pooled sampling variance under
   heteroscedastic long runs; nothing rests on it.)  rb_yards_shape_read - per-count cumulants fit around the population rate: RB rushing skewness per carry
   +4.03-4.14 every season, RB receiving per catch +2.23-2.54; the shifted gamma (draws.yards_sum's form) given the count: rushing CRPS 9.19 -> 9.00, L by count
   tercile .021 / .043 / .062 -> .218 / .113 / .093; receiving 6.61 -> 6.52, L .037 / .056 / .076 -> .187 / .121 / .112.  (The gamma's floor overshoots the lowest
   counts' lower tail - disclosed.)
Five whys (RB F8 CENTER TOO LOW on q .10): RB F8's lower tail is too long -> so are RB rushing yards (q .10 coverage .062) and receiving yards (.066) -> yards are
   n e + sqrt(n v) Z at the raw season-to-date rate with a normal per-count law -> a back's yards per carry carry no signal of their own, and a carry's yards are
   right-skewed (long runs) - a normal spreads that variance to both sides; sprint 37's k3 was fit around the raw rate a back's own long runs inflate (read < 0, FAIL)
   -> sub-root: the RB yards law's center and shape are not fit around the rate the data supports.
T2c (one batch, one replay): THE YARDS SHAPE (laws.SHAPE_CELLS - F5 rushing yards RB, F5 receiving yards RB).  The per-count rate is the shrunk one (the cells join
   fitted_state efficiency - laws.issued_efficiency, one producer; RB rushing's tau2 about 0 makes it the population rate); laws.fit_shape - (v, k3) around that rate
   on seasons < s, the one producer of these cells' cumulants (the spine cumulants no longer fit for them); k3 issued (draws.yards_sum's shifted gamma).  No law layer:
   the yards are drawn given their count in draws.count_yards_components.  Mock: v 66.3 vs 64, k3 2091 vs 2048 planted.
THE GATES (draws.gated_judgment): ROOT per cell on its own nonzero cell; INTEGRATION on RB F8; against proj/atlas_rows_batch50.csv.gz.  proj/shape_verdicts.csv.
REGISTERED GOALS: G1 F8 RB DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED do not fall (at least 1); G3 F5 rushing yards RB nonzero L moves toward .10; G4 F8 RB CRPS at
   most the batch 47 product's 3.2402; G5 the yards shape EARNED and integrated in both cells; G6 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: RB rushing yards CRPS 14.29 -> lower, L .062 -> toward .10; RB receiving yards 7.84 -> lower; RB F8 3.2466 -> lower with q .10 coverage .087 -> about .10 -
   DECISION-QUALIFIED (layer 1: 1 -> 2); WR F8 3.0772, QB 4.6121 and TE unchanged exactly.  Falsifier: RB F8's q .10 coverage stays below .09 with both yards cells'
   L corrected - the carries count's own lower tail owns it (its bias -.173).
WORK ORDER (appended): T2b EARNED; T2c here; the class - WR / TE yards given count around their issued rates; the team carries center (-.064, F2 team carries CENTER
   TOO LOW); the drifting share for the role and RB targets; M0b with the two batch 48 record corrections; M0c WO38-R.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2c - OUTCOME; T2d - THE PLAY SUM (EVERY STRUCTURAL YARDS CELL AS THE SUM OF ITS PLAYS) - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
T2c (batch 51, graded): THE YARDS SHAPE UNRESOLVED in both cells; RB F8 3.2466 -> 3.2744; not issued from the next replay.  Lesson: a moment-matched gamma's floor
   truncates the low tail at the lowest counts and its k3 split was unstable - a family imposed on a play's luck.
THE READS: rb_layers_read - below the counts an RB's yards per touch are luck (ypc: the back +.0002, his offense +.016, the defense +.003; ypr 0 at every unit).
   rb_play_read - a carry is ordinary (89.8%, mean 2.83) or explosive (10.2%, 40.6% of the yards; its rate luck); the game level about 0 (plays independent).
   yards_plays_read - all eight yards-given-count cells, the sum of the realized count's past plays (seasons < s) against the normal at the same e, v:
   CRPS RB rushing 9.084 -> 8.860, WR rushing 4.505 -> 4.406, TE rushing 4.954 -> 4.413, QB rushing 6.767 -> 6.670, RB receiving 6.538 -> 6.441, WR receiving
   10.731 -> 10.520, TE receiving 7.334 -> 7.135, QB passing 25.052 -> 24.887; tail share from .02-.23 to .16-.32 (honest .20); per-play gain signal by the player
   at most .047 (QB rushing), WR .022, the rest about 0.  Game level (var of the player-game mean beyond its plays'): RB rushing -.61, TE rushing -1.35, RB
   receiving +.72, TE receiving +1.57, WR receiving +4.92 (of 35.1), QB passing +1.45 (of 6.9) - a reading that mixes persistent player levels and count x gain
   dependence with shared in-game luck; the calibration given the count is the direct test.  Disclosed: QB rushing T2 tail .316 (kneels and scrambles, one pool);
   QB passing T3 bias +13 in both forms (count x gain dependence, M4).
Five whys (RB F8 CENTER TOO LOW on q .10): RB F8's lower tail is too long -> so are its yards cells' -> the yards are drawn from a family around the count (normal;
   T2c's gamma) -> a play's gain is luck whose law is the plays' own (losses, an ordinary bulk, a long tail) - no two-or-three-moment family carries it at every
   count -> sub-root: yards given count are drawn from an imposed family, not from the plays that make them.
T2d (one batch, one replay): THE PLAY SUM (laws.PLAY_CELLS = STRUCTURAL_YARDS - rushing and receiving yards of RB, WR, TE).  laws.play_rows: every rush and catch of
   a played row through facts.read_data (the play-by-play files; pbp_box_crosscheck's rules), its position the row's own by co-reference; laws.fit_plays: the
   cell's plays of seasons < s as deviations from their mean - the one producer of its law; draws.play_sum: n e + the sum of n drawn deviations, e the per-count
   rate as issued (laws.issued_efficiency); draws.yards_of_cell - the door count_yards_components draws every structural cell through.  The cell's (v, k3) in
   fitted_state yards_count are the pool's own (readings).  QB passing and QB rushing are not structural cells - left to the work order.  Mock: mean n e and
   variance E[n] v + e^2 Var n reproduced (64.47 vs 64.49; 606.5 vs 605.0); n = 0 gives 0.
THE GATES (draws.gated_judgment): ROOT per cell on its own nonzero cell; INTEGRATION on the position's F8; against proj/atlas_rows_batch50.csv.gz.  proj/play_verdicts.csv.
REGISTERED GOALS: G1 F8 RB DECISION-QUALIFIED; G2 F8 cells DECISION-QUALIFIED do not fall; G3 every yards cell's nonzero L moves toward .10; G4 the play sum EARNED and
   integrated in every cell; G5 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: every yards cell's CRPS lower, its L toward .10; RB F8 3.2466 -> lower, q .10 coverage .087 -> about .10 - DECISION-QUALIFIED (layer 1: 1 -> 2); WR F8
   stays DECISION-QUALIFIED; QB F8 4.6121 unchanged exactly.  Falsifier: the yards cells EARNED with RB F8's q .10 coverage still below .09 - the carries count's own
   lower tail owns it (bias -.173).  WR receiving is the risk: its game level +4.9 may leave its sums too narrow at high counts (T3 tail .228 in the read).
WORK ORDER (appended): T2c UNRESOLVED; T2d here; QB rushing - the play's kind (kneel, sneak, scramble, designed) as its sub-root; QB passing per completion as a
   play sum after M4; count x gain dependence (M4); the team carries center (-.064); the drifting share for the role and RB targets; M0b with the two batch 48
   record corrections; M0c WO38-R.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2d - THE PLAY SUM: THE JUDGMENT RAISED BEFORE ITS VERDICT - Oct 7 2026
Batch 52 replayed with all six play cells issued (unjudged) and graded: atlas DECISION-QUALIFIED 20 -> 22; RB receiving yards nonzero 7.8440 -> 7.8241 and WR
   receiving yards nonzero 14.5596 -> 14.4974 (both now DECISION-QUALIFIED); RB rushing yards nonzero 14.3375 -> 14.2820 (still CENTER TOO LOW, bias -1.318 - the
   carries count's); TE receiving yards nonzero 9.9816 -> 10.0188 (worse); WR F8 3.0772 -> 3.0751 DECISION-QUALIFIED; RB F8 3.2466 -> 3.2474 (CENTER TOO HIGH, q .10
   coverage .111); QB F8 4.6121 unchanged.  ROOT and INTEGRATION ran for RB, TE and WR receiving (EARNED, FAIL, EARNED); the rushing cells' readings raised
   KeyError: 3 in gated_judgment - a reading's rows reached no top usage tercile - before any verdict file was written.
Five whys: no verdict file -> gated_judgment raised in a reading -> the tercile gap named tercile 3 and 1 -> a reading term's rows (a cell's count usage terciles,
   merged to another term's rows) need not reach every tercile -> sub-root: the gap reading named its ends instead of reading them from the rows.  Remedy: the gap
   between the lowest and highest tercile the rows reach.  The product is unchanged (laws.py as batch 52); the replay re-issues the six cells and judges them once.
PREDICTION: verdicts as batch 52 printed for the receiving cells (RB EARNED, TE FAIL, WR EARNED); RB rushing EARNED (14.3375 -> 14.2820); WR and TE rushing EARNED
   on small gains; the TE receiving FAIL leaves its normal law in place from the next replay.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2d - THE PLAY SUM: THE JUDGMENT RAISED BEFORE ITS VERDICT - Oct 7 2026
Batch 52 replayed with all six play cells issued (unjudged) and graded: atlas DECISION-QUALIFIED 20 -> 22; RB receiving yards nonzero 7.8440 -> 7.8241 and WR
   receiving yards nonzero 14.5596 -> 14.4974 (both now DECISION-QUALIFIED); RB rushing yards nonzero 14.3375 -> 14.2820 (still CENTER TOO LOW, bias -1.318 - the
   carries count's); TE receiving yards nonzero 9.9816 -> 10.0188 (worse); WR F8 3.0772 -> 3.0751 DECISION-QUALIFIED; RB F8 3.2466 -> 3.2474 (CENTER TOO HIGH, q .10
   coverage .111); QB F8 4.6121 unchanged.  ROOT and INTEGRATION ran for RB, TE and WR receiving (EARNED, FAIL, EARNED); the rushing cells' readings raised
   KeyError: 3 in gated_judgment - a reading's rows reached no top usage tercile - before any verdict file was written.
Five whys: no verdict file -> gated_judgment raised in a reading -> the tercile gap named tercile 3 and 1 -> a reading term's rows (a cell's count usage terciles,
   merged to another term's rows) need not reach every tercile -> sub-root: the gap reading named its ends instead of reading them from the rows.  Remedy: the gap
   between the lowest and highest tercile the rows reach.  The product is unchanged (laws.py as batch 52); the replay re-issues the six cells and judges them once.
PREDICTION: verdicts as batch 52 printed for the receiving cells (RB EARNED, TE FAIL, WR EARNED); RB rushing EARNED (14.3375 -> 14.2820); WR and TE rushing EARNED
   on small gains; the TE receiving FAIL leaves its normal law in place from the next replay.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2d - THE PLAY SUM: THE JUDGMENT RAISED BEFORE ITS VERDICT - Oct 7 2026
Batch 52 replayed with all six play cells issued (unjudged) and graded: atlas DECISION-QUALIFIED 20 -> 22; RB receiving yards nonzero 7.8440 -> 7.8241 and WR
   receiving yards nonzero 14.5596 -> 14.4974 (both now DECISION-QUALIFIED); RB rushing yards nonzero 14.3375 -> 14.2820 (still CENTER TOO LOW, bias -1.318 - the
   carries count's); TE receiving yards nonzero 9.9816 -> 10.0188 (worse); WR F8 3.0772 -> 3.0751 DECISION-QUALIFIED; RB F8 3.2466 -> 3.2474 (CENTER TOO HIGH, q .10
   coverage .111); QB F8 4.6121 unchanged.  ROOT and INTEGRATION ran for RB, TE and WR receiving (EARNED, FAIL, EARNED); the rushing cells' readings raised
   KeyError: 3 in gated_judgment - a reading's rows reached no top usage tercile - before any verdict file was written.
Five whys: no verdict file -> gated_judgment raised in a reading -> the tercile gap named tercile 3 and 1 -> a reading term's rows (a cell's count usage terciles,
   merged to another term's rows) need not reach every tercile -> sub-root: the gap reading named its ends instead of reading them from the rows.  Remedy: the gap
   between the lowest and highest tercile the rows reach.  The product is unchanged (laws.py as batch 52); the replay re-issues the six cells and judges them once.
PREDICTION: verdicts as batch 52 printed for the receiving cells (RB EARNED, TE FAIL, WR EARNED); RB rushing EARNED (14.3375 -> 14.2820); WR and TE rushing EARNED
   on small gains; the TE receiving FAIL leaves its normal law in place from the next replay.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2d - THE JUDGMENT RAISED AGAIN; THE VERDICTS FIRST - Oct 7 2026
Batch 53: gated_judgment reached the five play cells' verdicts (stdout): RB receiving EARNED, TE receiving FAIL, WR receiving EARNED, RB rushing UNRESOLVED (p .4456),
   TE rushing EARNED - then raised ValueError (qcut: bin edges NaN) in the WR rushing cell's usage reading (its baseline F5 carries WR nonzero centers undefined) before
   any verdict file was written.  Batch 53's remedy named one symptom (tercile 3) of a class.
Five whys: no verdict file twice -> a reading raised -> the readings run inside the verdict loop and the file is written after them -> a reading is computed as if
   it were a precondition of the verdict -> sub-root: gated_judgment orders a reading before the decision it only describes.  Remedy: decide and write every verdict
   first, then read; the usage tercile is the center's rank share in thirds (rows without a center reach no tercile and the reading says so).  Applies to every
   gated_judgment caller; files already judged are only read.  Product unchanged (laws.py as batch 52).
f8_owner_read (the graded product, batch 52 = 53): the F8 error regressed on its components' errors (the data's own weights, 6 / 1 / .1 recovered):
   QB F8 +.564 - passing yards +7.71 own +.404 (attempts +.86, completions +.58); team attempts +.633 (+.50 / +.55 / +.30 / +1.18 by season), team targets +.564 -
   pass volume is forecast high every season.  RB F8 -.107 - rushing yards -1.26 own -.151 (carries -.165, about half of it; the per-carry center the rest); team
   carries -.232, its sign not stable by season (+.163 in 2024).  TE F8 copula -.154 - receiving yards -1.82 (-.201) and receptions -.106 (-.102), TDs +.141; TE
   independent -.083 the same.  WR F8 +.116 - receiving yards +.685 (+.081).
PREDICTION: play_verdicts.csv written - RB receiving EARNED, TE receiving FAIL, WR receiving EARNED, RB rushing UNRESOLVED, TE rushing EARNED, WR rushing EARNED or
   UNRESOLVED; the product unchanged this replay (RB F8 3.2474, WR 3.0751, QB 4.6121).
WORK ORDER (appended): the next sub-root - team pass volume center high every season (team attempts +.633), owner of QB F8's center (+.404 of +.564) and a part of
   WR's; TE receiving volume center low (receptions, yards) - TE F8's owner; RB's per-carry center (-1.26 yards with carries -.165); WR carries baseline centers
   undefined (the usage reading's NaN) - read why.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T2d - OUTCOME; T3 - THE LEAGUE LEVEL (TEAM VOLUME CENTERS) - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
T2d (batch 54): proj/play_verdicts.csv - RB receiving EARNED, WR receiving EARNED, TE rushing EARNED; TE receiving FAIL, WR rushing FAIL; RB rushing UNRESOLVED (p .4456).
   G2, G3 (6 of 6 lower tails toward .10), G5 MET; G1 (RB F8 3.2474), G4 NOT MET.  The verdicts-first order held.
THE READS: f8_owner_read - QB F8 +.564 owned by passing yards +7.71 (+.404; attempts +.86); team attempts +.633, targets +.564 every season.  team_volume_drift_read -
   the league to date does not lag on average (LEAGUE part +.029; TEAM part +.604).  f2_center_read - the issued attempts / targets center shrinks toward the training
   seasons' league mean (weights .593 / .457, explained .927 / .945; opportunity attempts UNRESOLVED and sprint 30 FAIL leave the recorded spine's form issued); carries
   weight .000 (its opportunity law EARNED, toward the league to date); training mean - league to date +.04 / +.70 / +2.42 / +1.62.  league_level_read - the league's
   level as a discounted state (delta fit on seasons < s: 1.000 / .853 / .876 / .848): attempts mean error +.633 -> +.127, MSE 59.136 -> 58.564 (league to date
   +.037 / 58.772, training +.637 / 58.812); targets +.564 -> +.167, 54.372 -> 54.035; carries -.232 -> -.149, 54.198 -> 54.131.
Five whys (QB F8 CENTER TOO HIGH, +.555): QB F8 high -> passing yards high (+7.71) -> attempts high (+.86) -> team attempts high (+.633) -> the center shrinks toward
   a fixed target - the training seasons' mean (stale: the league's pass volume fell) or the league to date (lagging inside a season, 2024 -.99) -> sub-root: the
   league's level is held fixed where it drifts.
T3 (one batch, two replays): replay 1 under batch 54's code - the product of record with the play verdicts applied - copied to proj/atlas_rows_batch55.csv.gz; then
   THE LEAGUE LEVEL (laws.LEVEL_CELLS - F2 team attempts, F2 team carries): laws.fit_level - delta by least squares of each week's league mean on its pregame
   discounted level, seasons < s, and fit_opportunity's moments around that level; laws.league_level - the level before each target week; laws.opportunity_mean,
   the one door - level + w (team rate - level) where issued.  Team targets and the QB's attempts are drawn inside the team attempts draw; RB carries inside the
   team carries draw.  Mock: delta .409 as the read, the level as the read's.
THE GATES (draws.level_judgment): ROOT per cell on its own team cell; INTEGRATION on every position's F8; verdicts written first.  proj/level_verdicts.csv.
REGISTERED GOALS: G1 F8 QB bias toward 0; G2 F8 QB DECISION-QUALIFIED; G3 F8 cells DECISION-QUALIFIED do not fall; G4 team attempts bias toward 0; G5 team targets bias
   toward 0; G6 the league level EARNED and integrated in every cell; G7 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: team attempts bias +.63 -> about +.13, targets +.56 -> about +.17; QB passing yards bias +7.7 -> about +4; QB F8 bias +.555 -> about +.35, CRPS 4.6121 -> lower;
   WR F8 stays DECISION-QUALIFIED; carries about unchanged.  Risk: the CRPS gain is small against per-game noise (MSE -1%) - ROOT may read UNRESOLVED as the opportunity
   law did; then the F8 integration readings carry the record.
WORK ORDER (appended): T2d judged; T3 here; QB's per-attempt and completion centers (the rest of passing yards' +7.7); TE receiving volume low; RB per-carry center.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T3 - OUTCOME; THE SUB-ROOT; T4 - THE ONE CHAIN - REGISTRATION WITH GOALS - Oct 7 2026 (before code)
T3 (batch 55): team carries EARNED (DECISION-QUALIFIED); team attempts UNRESOLVED (bias +.633 -> +.123, p .1132) - reverts.  QB F8 4.6121 -> 4.6114 for one replay.
THE READS: f8_owner_read - each F8 center's owner (QB: passing yards +7.71 on attempts +.86; RB: rushing yards -1.26; TE: receiving yards -1.82).  team_volume_drift_read,
   f2_center_read, league_level_read - the team pass center shrinks toward the training seasons' mean.  one_chain_read - one chain of centers from the law-side
   producers alone (team count at the league level x shrunk share x shrunk rates) against the recorded spine's v1: MSE lower in 16 of 19 cells (RB carries 1.053,
   RB rushing yards 1.006, WR targets 1.002, team carries 1.000 the exceptions); the spine's own QB centers are near unbiased (Q1 -0.162, Q3 +0.68) where the
   issued law is not (+0.856, +7.71) - the bias is made where the QB control share meets the spine's team attempts.  level_chain_read - every rate shrunk toward a
   drifting league level instead: MSE moved at most .4%, the season swings (Q3 2021 +8.7 / 2024 -11.4; RB rushing 2025 -3.0) stay in v1 and both chains alike -
   season luck, FALSIFIED as a root.  fossil_map_read - 24 functions read the spine's centers (law_frames' m_* at 41 sites; fit_state; row_laws); 22 verdict
   switches; replay_all re-runs 20 judged-once judgments every replay.
Five whys (thirty batches, one F8 cell): each batch repaired one junction and exposed the next -> each junction joins two producers of one center -> the
   recorded spine's v1 is still the producer of record and every law since sprint 41 is an overlay switched on by a verdict file and judged against v1's product
   -> an overlay cannot replace the center it sits on, so each new law adds a junction -> sub-root: the center has two producers.  The overlay switches and the
   re-run judgments are what made the junctions constructable and kept them alive.
T4 (one batch, two replays): replay 1 under batch 55's code - the product of record (team attempts reverted) - copied to proj/atlas_rows_batch56.csv.gz.  Then
   THE ONE CHAIN (laws.CHAIN_CELLS - team targets / attempts / carries; RB / WR / TE targets, receptions, receiving yards; RB carries, rushing yards; QB attempts,
   completions, passing yards, carries, rushing yards): laws.one_chain replaces the spine's v1 on every nonzero row of an issued chain cell with laws.chain_center -
   a team count at the league's drifting level, every other cell its parent's center x its shrunk rate (laws.chain_rate, the luck map's estimator), each season
   fit on seasons < s (laws.chain_fits, one producer) - so every reader of a center reads one producer.  Every structural yards cell and the two QB yards cells
   draw at laws.chain_rate where issued (the ratio of two laws retired there).  Unchanged and named: zero-state rows (the state is a fact), the first season
   (no earlier season), TDs (no chain link yet), WR / TE rushing yards' counts (no spine carries).  replay_all stops re-running the 20 judged-once judgments
   (their verdict files stand as the record; the functions are the next landing's fossils) and runs chain_judgment alone.
   Mock: chain fits for 5 seasons; v1 bias +.27 to +4.6 -> within +-.2 on counts; MSE lower in every chained cell.
THE GATES (draws.chain_judgment): ROOT per cell (team cells state team, player cells nonzero); INTEGRATION on every position's F8; verdicts written first.
REGISTERED GOALS: G1 F8 cells DECISION-QUALIFIED rise; G2 they do not fall; G3 F8 QB bias toward 0; G4 F8 TE copula bias toward 0; G5 every chain cell EARNED and
   integrated; G6 atlas DECISION-QUALIFIED cells do not fall.
PREDICTIONS: QB attempts bias +.86 -> about 0, passing yards +7.7 -> about +2, QB F8 bias +.555 -> under +.2; TE receiving yards -1.8 -> about -1.3; RB rushing yards
   about unchanged (its miss is season luck); WR F8 stays DECISION-QUALIFIED; F8 cells qualified 1 -> 2 (QB).  Falsifier: QB F8 bias stays above +.4 - the junction
   is not the owner.  Risk: CRPS gains small against game noise - cells may read UNRESOLVED; each keeps v1 then, named.
WORK ORDER (appended): the next landing deletes the fossils - the 20 judgment functions and their goals, the dead verdict switches (FAIL / UNRESOLVED laws not
   issued), the THREE ZEROS re-run readings; then the TD link of the chain; owed instruments re-recorded on the new centers (spine_check, law_issue_check).
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## T4 - OUTCOME; THE CHAIN IS ONE LAW - Oct 7 2026
T4 (batch 56, the chain issued whole): per cell 5 EARNED (TE receiving yards, TE receptions, RB targets, Q2 completions, QB carries), 8 UNRESOLVED, 6 FAIL - three
   of the FAILs unchanged cells (team carries, RB carries, TE targets: gains .0000, their issued laws read no v1 - UNCHANGED, owed as a record correction).  On the
   chain's product: QB F8 bias +.555 -> +.342 but CRPS 4.6121 -> 4.6217; RB F8 3.2454 -> 3.2786; WR F8 3.0749 -> 3.0855; TE copula 2.1907 -> 2.1835, TE independent
   DECISION-QUALIFIED.  The integration gate passed all three rises (within chance by goal_losses) - weaker than Done #6.
The next replay (the EARNED subset) raised in draw_law: Q2 completions binomial p > 1 - Q2's chain center over Q1's v1.
Five whys: the replay raised -> p = the chain's Q2 / v1's Q1 -> the EARNED subset issued a child without its parent -> the chain was judged and switched cell by
   cell -> sub-root: one law cut into per-cell switches re-creates the junction it was built to remove (the switch pattern itself).  Remedy: the chain is one law -
   issued whole while unjudged, then whole or not at all.
T4 AS ONE LAW (draws.chain_unit_judgment, once, before the replay's inputs): the chain's own product (proj/atlas_rows.csv.gz as batch 56 left it - witness: its Q1
   centers differ from the baseline's) against proj/atlas_rows_batch56.csv.gz; ISSUED iff no F8 cell's CRPS rises, else WITHHELD; for each position that rose, every
   moved chain cell printed beside it.  proj/chain_unit_verdict.csv; laws.CHAIN reads it.
PREDICTION: WITHHELD (QB, RB, WR F8 rose); the replay runs and its product equals the batch 56 baseline (QB F8 4.6121, RB 3.2454, WR 3.0749).  The readings name which
   moved chain cells sit under each F8 rise - the next five whys starts there (the chain moved counts toward the truth and F8 the other way: the order / coupling laws
   were fit on v1's margins is the first candidate).
WORK ORDER (appended): UNCHANGED record correction for the three cells; integration gate against the previous product with no rise (Done #6); readings print no
   verdict words; Q3's spread around its center; fossil deletion.
LANDING CONTRACT: snapshot laws.py, draws.py and CHARTER.md before writing; restore them whole if the guard refuses.
## THE GROUND-UP REWRITE - OWNER DECISION AND REGISTRATION - Oct 7 2026 (before code)
Owner (Oct 7): laws.py, draws.py and dependence.py are deleted; the kit is rewritten from the ground up so that every root discovered cannot be constructed.  The
   three files are kept unchanged in proj/fossils/batch59/ as history (the record of thirty sprints), never imported: a reader of them fails the rewrite.
THE ROOTS (batches 47-57; each observed in pasted output):
   A. Two producers of one center: the recorded spine's v1 is the producer of record; every law since sprint 41 an overlay on it.  Issued QB attempts +.856 where
      v1 is -.162 and the one chain -.105; RB rushing yards per carry = the spine's yards / the drift's carries (CHARTER L1950, L3213).
   B. Parameters frozen to the product they were fit on: wall 9's rho from the recorded composed PITs (dependence.recorded_composed_ranks); Q3's spread fit around
      the old mean (better center, worse CRPS 4 / 4); the chain moved every count toward the truth and QB, RB and WR F8 the other way.
   C. Judged per cell, switched per cell: 22 verdict files switch overlays on and off; replay_all re-ran 20 judged-once judgments; the EARNED subset issued Q2 on v1's
      Q1 (p > 1); unchanged cells filed FAIL; real center fixes UNRESOLVED one cell at a time (team attempts +.633 -> +.123, p .11).
   Converged: a stack of overlays, each fit once and judged once against a frozen product beneath it, never refit end to end.
   Not roots: the season swings (Q3 2021 +8.7 / 2024 -11.4, RB rushing 2025 -3.0) are in every producer alike - season luck (level_chain_read).
THE CONSTRUCTOR RULES the rewrite is built to (each makes a root unconstructable; the guard enforces the ones it can read statically):
   R1 (A) One producer per center: every center derived at the cutoff from facts alone through one chain (team volume at the league level -> share -> rate -> count
      -> yards per count); no recorded forecast (the spine's v1, a frozen atlas, a recorded rank) is an input of any law.
   R2 (B) One fit, refit whole: every parameter - centers, spreads, dispersion, cumulants, dependence - fit at each cutoff on seasons < s, in dependency order, by one
      fit function; a spread is fit around the center it serves; no parameter is read from a file.
   R3 (C) One product, one judgment: a challenger is a whole product version, judged once against the previous product - every F8 cell, no rise (Done #6) - with
      per-cell readings that print no verdict words; no law reads a verdict file; no per-cell switch.
   R4 Trinary and honest: EARNED / UNRESOLVED / FAIL against chance, UNCHANGED where nothing moved; a judgment's verdict is written before any reading runs.
   R5 Draw what the data shows: a law's shape is the measured one (the play sum's lesson) unless a family is earned against it; luck is drawn, never centered on.
THE INTERFACE the rewrite inherits: the readers printed by rewrite_map_read (remaining modules' references to the deleted names, kit.py commands, the records the
   fossils named) - nothing else.
WORK ORDER (appended): the rewrite in order - (1) the one chain of centers and its fit (R1, R2); (2) the laws drawn from it with their spreads refit (R2, R5);
   (3) dependence refit at the cutoff (R2); (4) the one replay and the one judgment (R3, R4); (5) the guard checks that make R1 - R3 static; then the frozen week.

## THE GROUND-UP REWRITE LANDS - chain.py + draws.py (batch 60, Oct 7 2026)
The modules deleted in batch 59 (laws, draws, dependence; fossils in proj/fossils/batch59) are replaced by two: chain.py (the one producer of every center,
rate and spread) and draws.py (one sampler, one replay, one judgment, and the inherited interface: week_draws, freeze_draws, player_draw_matrix,
frozen_draws_path, QUANTILE_LEVELS, QUANTILE_NAMES - the only names cards.py and market.py read, per interface_read).  kit.py's roster loses laws and
dependence and gains chain; every command that reached the deleted modules is removed; `draws` and `replay PREVIOUS_ATLAS_ROWS` remain.
How the rules are made unconstructable, not policed:
- R1 (root A, two producers of one center): chain.py reads facts' played rows through state.team_volume / state.box_zero and nothing else.  There is no
  argument, file or import through which a recorded forecast, frozen atlas, recorded rank or second center can enter.  A center is the parent's center x the
  key's pregame rate, team volume at the league's discounted level (delta fit by least squares).
- R2 (root B, parameters frozen to the product they were fit on): fit_chain(history, s) fits every link at the cutoff on seasons < s in dependency order;
  each spread is measured around the center fit with it, on the issue domain state defines.  No parameter is read from a file; the copula and its recorded
  ranks no longer exist - teammates and a player's own terms are joined by drawing each link on its parent's draw (draw j is one world).
- R3 / R4 (root C, judged and switched per cell): there is no verdict file a law can read and no per-cell switch.  replay judges the whole product once
  against the previous product's graded rows, per F8 cell the previous product graded (read from its rows), on rows both graded; chance_label is the one
  door: UNCHANGED when every paired difference is 0, BETTER / WORSE by the season chance test at ALPHA_FAMILY, UNKNOWN otherwise.  The judgment is written
  (proj/product_judgment.csv) before any reading.  Both sides are read as records at round-trip float precision (a record equals its content).
- R5: every spread is measured (team ratio outcome / center; beta-binomial overdispersion around the shrunk rate; per-unit yards residuals), none chosen.
Mock witness (synthetic league, scratchpad): previous = itself -> all UNCHANGED, ISSUED; previous QB better / WR worse -> QB WORSE, WR BETTER, REFUSED;
previous with two TE F8 cells -> each judged on its own.
Baseline: proj/atlas_rows_batch59.csv.gz = the graded rows on disk when the old modules were deleted (the last old product).
Prediction: ISSUED - no previous F8 cell WORSE; QB F8 bias below the batch 56 +0.342 in magnitude.  Falsifier: any F8 cell WORSE refuses the product
(a verdict: the refused product stays on disk as the subject of the next five whys - there is no old product to restore to).  A crash before the judgment
restores kit.py and the atlas records whole.

## BATCH 60b - ONE READER (Oct 7 2026)
Batch 60's guard passed (12 modules, name resolution, one definition, information set, purity) and its CHARTER lines were accepted; its replay crashed on
its first read: draws.py passed float_precision to facts.read_table, which already owns it (round-trip floats).  The mock's reader did not, and the noise
it produced was remedied in the caller instead of the reader - a second producer of one fact.  Deleted from draws.py; the mock reader now matches facts.
The batch 60 registration stands unchanged (prediction, falsifier, baseline proj/atlas_rows_batch59.csv.gz).

## BATCH 61 - THE ROLE LAW: A PLAYER'S SHARE OF HIS TEAM (Oct 7 2026)
Batch 60b's product was REFUSED (F8 QB WORSE 4.6121 -> 4.7035, 4/4 seasons; F8 RB WORSE) with its centers' bias fixed.  Five whys, each settled by a read:
- loss_shape_read: the loss is RESOLUTION, not width - Q1 attempts corr(center, y) .522 -> .434 with center sd 5.08 -> 7.14 and narrower intervals.
- spread_state_read: the share's spread pooled per position is not the root (grouping by rate gains nothing on Q1 / RB carries).
- share_state_read, discount_state_read: more history is worse (career .374); a fitted discount lifts Q1 to .474 - a patch, not landed (owner: do not harden around
  an incorrect mechanism).
- participation_mechanism_read, factor_swap_read: participation is most of the Q1 miss (this game's snap share known: .762) - luck, drawn not centered on; no
  volume x rate x participation product and not the fossil snap formula (.456) recovers the previous .522.
- control_law_read: the previous product's Q1 / RB carries were the sprint 29 / 39 control law - its state holds his share of his TEAM'S PREVIOUS GAME, 0 when he did
  not play in it: who the team's active player is now, which a season-to-date share over his own games cannot see.  Raw, it wins Q1 (.531) and loses WR / TE.
- role_law_read, nested_law_read: the logistic curve cannot pass through the luck map's share (WR / TE bias +.12-.16); NESTED on it, one law wins or ties every cell -
  Q1 .434 -> .522 (share CRPS given the team's count 2.349 -> 2.026, 4/4 seasons), RB carries .746 -> .761 (2.077 -> 2.004, 4/4), WR tie, TE 0.870 -> 0.863 (4/4).
THE SUB-ROOT: a player's share of his team was built as a rate over his own games; it is a ROLE on his team.  Remedy, one constructor for every link whose parent
is a team count (kind "share", from the graph - F5 targets / carries RB WR TE, Q1 attempts, QB carries): chain.fit_share - the luck map's moments of the season
share, then THE ROLE LAW logit(mean) = logit(shrunk share) + t0 + t1 (previous team-game share - shrunk share), log concentration = t2 + t3 previous + t4 shrunk,
by maximum likelihood on seasons < s (refused by name when it does not converge).  t0 = t1 = 0 is the luck map's share: the data decides per position how much
the team's last game counts; there is no per-cell switch.  Deleted for those links: the pooled overdispersion rho (and with it the rho >= 1 the beta-binomial could
not draw - WO62a).  Conversions keep the luck map; a row whose team has no earlier game this season is named, not drawn.
Judged by THE ONE JUDGMENT against the last ISSUED product, proj/atlas_rows_batch59.csv.gz (60b's refused rows kept as proj/atlas_rows_batch60b.csv.gz, a reading).
Prediction: ISSUED; F8 RB not WORSE (center back to .761); F8 QB not WORSE (Q1 resolution back to the previous level, its share law sharper).  Falsifier: any F8
cell WORSE refuses it.  Owed (work order): the raw control law still beats the nested one on Q1's share law alone (1.885 vs 2.026) - the luck map's single shrink
target for a two-mode role population (starters, backups); Q3 / WR receiving yards per-unit spread grows with the rate (+1.33% / +0.61%, 4/4 seasons).

## BATCH 62 - THE LUCK MAP MEASURED ON THE ROWS IT IS APPLIED TO (Oct 7 2026)
Batch 61 ISSUED (F8 QB 4.6121 -> 4.5740 UNKNOWN; TE copula BETTER; nothing WORSE) with F8 qualified 0 of 4 and twelve cells CENTER TOO LOW.  Reads:
- domain_fit_read: the role law fit on every training game leaves the share cells low on the issue domain (RB / TE / WR targets link bias -0.090 / -0.098 / -0.071);
  fit on the issue domain they go to -0.018 / -0.016 / +0.002 with CRPS better - but Q1 worsens (2.062 -> 2.149, 4/4 seasons).
- evidence_law_read, offset_law_read: a previous-game weight scaled by the prior weight (1 - w) falsified; an offset t5 (1 - w) improves every cell slightly but
  overshoots WR (+0.074) and is unidentified on the domain (t5 = 50) - a patch on the shrink target, not landed.
- luck_domain_read: the luck map's moments pooled every game of the position (early weeks, backups); measured on the issue domain (moments + role law) they are
  best on 7 of 8 share cells (RB carries 1.993 -> 1.982, RB / TE / WR targets 0.839 / 0.860 / 1.184 -> 0.835 / 0.855 / 1.178, QB carries 1.205 -> 1.193, receiver
  bias to ~0); Q1 still loses (2.062 -> 2.153).  The QB shrink target moves 0.843 -> 0.895 on the domain: early-season QB games are dominated by backups, so the
  QB role-change signal lives in games the product never forecasts.
THE RULE, made a constructor (R5 applied to the shrink, not only the spreads): every luck-map estimate of a player link (fit_share, fit_proportion, fit_per_unit
moments) and the role law are measured on the training games of the issue domain.  No term is added.
Judged against the product now issued, proj/atlas_rows_batch61.csv.gz.  A REFUSED verdict keeps batch 61: chain.py, draws.py and the atlas records are restored and
the challenger's graded rows kept as proj/atlas_rows_batch62.csv.gz (a reading).
Prediction: TE / WR / RB F8 not WORSE (their share cells sharper and unbiased); F8 QB at risk (Q1's share law worse on its own by 4%).  The verdict decides;
either outcome is registered.  Owed: the QB role-change signal (backup -> starter transitions) outside the issue domain - what pregame state carries it into
the rows the product forecasts.

## BATCH 63 - THE SIBLING LAW: A SCORE MOVES WITH THE YARDS OF THE SAME TOUCHES (Oct 7 2026)
Batch 62 ISSUED (F8 TE BETTER p .001, WR BETTER p .036; cells DECISION-QUALIFIED 17 -> 24; CENTER TOO LOW 12 -> 5).  The F8 centers are near unbiased (QB +0.026,
RB -0.141, TE -0.023, WR +0.039); the misses are shape (RB TOO NARROW, PIT sd QB .2994 / RB .3006).  composition_read, on the issue-domain facts: a player's
luck left after his counts co-moves between the yards and the TDs of the SAME touches - passing yards / passing TDs per completion +0.378, RB rushing +0.238 and
receiving +0.216, WR receiving +0.229, TE rushing +0.230 (receiving +0.089); across touch types ~0.  The DK-weighted variance ratio (1 = independence right):
QB 1.200, RB 1.233, WR 1.215, TE 1.072 - above 1 in every season for QB / RB / WR.  Independent draws omit ~20% of F8's leftover variance.
THE SUB-ROOT: the chain drew each link given its parent only; a TD and the yards of the same touches are siblings under one parent, drawn as if unrelated.
Remedy, one constructor read from the graph (chain.siblings_of - a count link whose parent also has a per-unit link; refused if ambiguous): THE SIBLING LAW -
logit(rate of draw j) = logit(shrunk rate) + t0 + t1 z_j, z_j the sibling's yards luck per square root of the shared trials in draw j; concentration exp(t2);
maximum likelihood on the issue domain at each cutoff.  t0 = t1 = 0 is the unconditioned count.  The sibling is drawn first (link_order).  No copula, no frozen
rank: the coupling is a parameter of the chain, refit whole (R2).
Judged against the product now issued, proj/atlas_rows_batch62.csv.gz; a REFUSED verdict keeps batch 62 (code and atlas records restored; the challenger's rows
kept as proj/atlas_rows_batch63.csv.gz).
Prediction: t1 > 0 for every sibling pair; F8 QB / RB / WR not WORSE and widened toward calibration (RB leaves TOO NARROW); TE least moved.  Falsifier: t1 ~ 0
(the coupling is not where the read measured it) or any F8 cell WORSE.

## BATCH 63b - THE SIBLING LAW, WELL-POSED (Oct 7 2026)
Batch 63's replay refused itself by name (fit_sibling F5 receiving TDs WR, seasons < 2021: ABNORMAL) and restored batch 62.  Two faults, both mine:
(1) the sibling's luck was in raw yards per sqrt(trial) (receiving yards spread ~12), so the logit reached hundreds and 1 / (1 + exp(z)) rounded to 0 - a
beta-binomial with b = 0; (2) the concentration sat inside the likelihood, and a count with no overdispersion (TDs are near-binomial) has its maximum at
concentration -> infinity, so the optimizer runs off.  Remedies at their sources: the luck has ONE PRODUCER for fit and draw (chain.sibling_luck_of), in units of
the sibling's own measured residual sd; the law's center is binomial maximum likelihood (a logistic regression with offset - convex, one optimum) with both
sides by expit; its overdispersion is MEASURED around that center by moments, as every proportion link's (R5); a measured 0 draws binomial.
The batch 63 registration stands (prediction, falsifier, judgment against proj/atlas_rows_batch62.csv.gz; a REFUSED verdict keeps batch 62).

## BATCH 64 - THE TEAM'S PLAYS: ONE GAME, ONE JOINT LUCK (Oct 7 2026; owner work order: rewrite the root clean)
ASPIRATION: forecast, before kickoff, how many passes and runs a team will run in its game, as one joint distribution.
ROOT (hand-made): chain.LINKS declared "F2 team attempts" and "F2 team carries" as two independent "level" roots; fit_root measured each count's ratio alone and
draw_link drew each with its own luck index.  A person decided passes and runs are unrelated.
LAW (root_coupling_read): a team's passes and runs come out of one game - corr(attempts luck, carries luck) -0.417 / -0.379 / -0.384 / -0.384 (2021 / 2023 /
2024 / 2025), the variance of their sum 0.58-0.62 of the independent figure: game script trades runs for passes.  Each count keeps its pregame center (own pace,
trusted by its amount, around the league's drifting level); the game's luck is ONE draw for both - an earlier issue-domain team-game's pair (passes / center,
runs / center), kept with the team-game it came from.
NEW: plays.py (written from the law, not from the old body).  DELETED in the same landing: chain.level_after, league_levels, root_center, fit_root, the two
"level" LINKS entries, draw_link's level branch, link_rates' level branch.  The landing prints CARRIED (new lines identical to deleted ones), KILLED (each
hand-made rule line, gone or still present) and MOVED (qualification before -> after; conserved may not fall, contradicted may not rise).
Judged against proj/atlas_rows_batch63b.csv.gz (the product now issued); a REFUSED verdict keeps batch 63b.
Prediction: team cells' centers unchanged (same law), their joint luck now anti-coupled; QB and RB - fed by both counts - narrow slightly.  RB is already
TOO NARROW, so CONTRADICTED may rise there: if it does, the player-level positive coupling (RB halves +0.05 in every season but 2026, against the team's
-0.4) is the next root - his own participation shared across his share links - and this landing is reported as not done.

## BATCH 65 - THE TEAM'S TARGETS SPLIT ONCE AMONG THOSE WHO PLAY (Oct 8 2026)
ASPIRATION: every team-game is one world - the team's targets are thrown once and each goes to exactly one player: a slate receiver who plays, or the rest
of the team.  ROOT: draws.draw_slate drew each receiver's F5 targets alone - `draw_link(cell, ...)` per member on the cell
`(("F5 targets", position), (("F2 team targets", TEAM_KEY), "targets", "team_targets", "share"))` - so the members' targets were never a split of the team's:
they exceeded the team's in 26 - 45% of team-games, and the rest (team draw minus members) was below zero in 57.5% of live draws, in every team-game
(joint_split_read).  LAW: the team's drawn targets are split once per draw: members or rest (beta-binomial, C_top), then among the members who play
(Dirichlet-multinomial on their role-law means, C_within); who plays is participation's probability_plays (the product's own producer); the rest's share is
the luck map of its own earlier issue weeks this season; C_top, C_within by maximum likelihood on seasons < s (fit_split); a player's row is drawn given he
plays.  A player counts for a team in a game only where his own row of that game names that team (WO98, trade-deadline weeks: law 1).
EVIDENCE (joint_tree_read_v4, season 2025 scored, fit 2023-2024): member F5 targets CRPS live -> split RB 0.7977 -> 0.7873 (BETTER t +1.79), TE 0.9054 -> 0.8989
(UNKNOWN t +1.01), WR 1.2406 -> 1.2350 (UNKNOWN t +0.78); the rest 2.6810 -> 1.0960 (BETTER t +19.29); the shares' sum weighted by probability_plays 1.001.
KILLED: the per-receiver independent target draw (draw_link on a target share cell) and, for target cells, the role law's concentration (t2 - t4 are fit
and no longer drawn from; the role law's mean stays).  CARRIED: none - the split is new code (fit_split, rest_rows, rest_share, slate_inputs, split_draw,
draw_team_splits).  MOVED: the judgment below.
PREDICTION: F8 QB UNCHANGED (no QB row reads a target draw); F8 RB, TE, WR BETTER or UNKNOWN; none WORSE.  FALSIFIER: any F8 cell WORSE refuses the
product and batch 63b is kept.  Judged against proj/atlas_rows_batch63b.csv.gz.

## BATCH 66 - THE GAME'S RATE LUCK: A YARDS RESIDUAL WIDENS WITH THE TOUCHES (Oct 8 2026)
ASPIRATION: a player's yards on his touches carry two kinds of luck - each touch's own, and the game's (the defense, the script, the day), which every touch
of that game shares - so a back with 25 carries has more room above and below his yards per carry than one with 8.
DRIVER: conversion (yards per touch).  F8 = DK(receptions, receiving yards, rushing yards, TDs); rushing yards = carries x yards per carry.
ROOT: chain.fit_per_unit / draws.draw_link drew every yards link as `np.rint(parent_draws * rate + np.sqrt(parent_draws) * fit["residuals"][...])` - one
residual pool per position on a sqrt(touches) scale: a person's rule that per-touch luck is the same at every volume.
LAW (conversion_width_read_v1): the residual per sqrt(touch) widens with the touches - RB rushing per-touch sd 5.05 - 5.77 below the season's median carries,
6.22 - 7.08 above, every season; tails given the actual carries too wide below (0.07 - 0.09 each) and too narrow above (lower 0.10 - 0.13, upper 0.10 - 0.15);
the same in WR / TE / RB receiving.  E[residual^2 | n] = touch luck + n x game luck, both by moments on seasons < s (cov / var - nothing chosen); the draw
keeps the pool's shape and center and scales its spread by unit_scale(fit, n).  Where the game luck measures 0 the draw is the old one.
IDENTITIES: untouched (yards are drawn on the parent's touches draw; no count identity moves).
REFUSAL CHECKS: one driver (conversion); spread only - the center term (touches x rate + sqrt(touches) x the pool's center) is unchanged; evidence every
season 2020 - 2025 and both volume halves; inputs (touches, yards) cover every season; one law, its two moments measured per cell (position x link) - the
population's own split; no reconciliation.
KILLED: the sqrt-only per-unit scale - `np.sqrt(parent_draws) * fit["residuals"][...]` - now sqrt(touches) x (center + (residual - center) x unit_scale).
CARRIED: chain.py and draws.py otherwise as 63b (this is an amendment of one law, not a rewrite of a file; the new lines are fit_per_unit's two moments,
unit_scale, and the draw line).
DRIVER SCORE before the replay: every yards link, yards given the actual touches, CRPS old -> new, season chance test; any WORSE refuses.
PREDICTION: driver score BETTER for RB rushing yards and WR receiving yards, none WORSE; F8 RB BETTER or UNKNOWN with tails toward .20, WR / TE BETTER or
UNKNOWN, QB UNKNOWN or BETTER (Q3 and QB rushing yards are yards links too).  FALSIFIER: any F8 cell WORSE refuses the product; 63b is kept.
Judged against proj/atlas_rows_batch63b.csv.gz.

## BATCH 67 - THE TRUST IN A TEAM'S OWN PACE, MEASURED (Oct 8 2026)
ASPIRATION: before a game, say how many passes and runs a team will run by moving the league's level toward the team's own pace this season exactly as far
as outcomes have followed such paces before.
DRIVER: team volume (attempts, carries) - the root every player's targets and carries sit on.
FIVE WHYS: (1) the team plays forecast is overconfident - outcomes follow its departure from the league level by only 0.35 - 0.51 in every season
(in_game_driver_read_v4); (2) its center is level + w x (pace - level) with w = tau2 / (tau2 + s2 / games), and w is too large; (3) tau2 is the spread of
teams' season-to-date paces around the level minus their sampling noise, s2 the per-game noise, both by moments; (4) the moments assume a team's games are
independent draws around one fixed pace - but a team's plays are 94% that day's drives x plays per drive (in_game_driver_read_v3); schedule and script do not
persist, so the spread of paces holds variance the next game does not keep; (5) SUB-ROOT: the trust is computed from that assumption instead of measured.
ROOT (deleted): s2 and tau2 by moments in fit_root, and root_center's reliability_shrink(level, fit["s2"], fit["tau2"], rate, games).
LAW: trust w = games / (games + k), k by least squares of each issue-domain team-game's departure from its level on its pace's departure, seasons < s (one
parameter, over log k).  The league level's drift (delta) and the measured ratio shape are kept as laws - they are not the root.
REFUSAL CHECKS: one driver (team volume); center only (the shape is the measured ratio around the fitted center); every season in the driver score; inputs
cover every season; k measured per count; nothing reconciled.
DRIVER SCORE first (attempts and carries, every season; the old law rebuilt for the comparison only): either not BETTER refuses the landing.
PREDICTION: driver score BETTER for attempts and carries; F8 BETTER or UNKNOWN at every position.  FALSIFIER: driver score not BETTER, or any F8 cell WORSE:
refused, 63b kept.  Judged against proj/atlas_rows_batch63b.csv.gz.

## BATCH 68 - TEAM VOLUME AS PLAYS x SHARE, EACH WITH MEASURED TRUST (Oct 8 2026)
ASPIRATION: before a game, say how many plays a team will run and what share of them it will pass, each moved from the league's level toward the team's own
season exactly as far as outcomes have followed such seasons before - so its passes and runs come from one total.
DRIVER: team volume.  Attempts = plays x pass share; carries = plays x run share.
FIVE WHYS (corrected, batch 67 refused by its own driver score): (1) the team plays forecast is overconfident - outcomes follow it by 0.35 - 0.51; (2) but
each count is near honest (63b slopes: attempts 0.80 - 1.07, carries 0.63 - 1.21), so the overconfidence is in their SUM; (3) passes and runs trade (corr
-0.38 to -0.42), so a team's total keeps less of its departure than either part; (4) the product forecasts attempts and carries as two independent volumes,
each trusting its own pace, and the total they imply is no one's forecast; (5) SUB-ROOT: there is no plays node - the total is a by-product of two trusts.
ROOT (deleted): two independent volumes - each count's own moments trust (`s2` and `tau2` in fit_root) and `return reliability_shrink(level, fit["s2"],
fit["tau2"], rate, games)` in root_center.
LAW (volume_structure_read_v1, every season): plays = the plays level moved toward the team's plays pace by games / (games + k_plays) - BETTER than the sum of
63b's two centers in every season (t +3.02), its slope toward 1; each count's share = the share level moved toward the team's share by plays / (plays + k_share);
one drift (delta, fit on plays) for every level, so the shares sum to one.  k's by least squares on seasons < s, nothing chosen.
REFUSAL CHECKS: one driver (team volume); center only - each count keeps its measured ratio shape around its own new center; every season; inputs cover every
season; k per count; nothing reconciled - the shares sum to one by construction.
DRIVER SCORE first: team plays squared error must be BETTER; attempts and carries CRPS may not be WORSE.
PREDICTION: driver score passes; F8 BETTER or UNKNOWN at every position.  FALSIFIER: driver refusal, or any F8 cell WORSE: refused, 63b kept.
Judged against proj/atlas_rows_batch63b.csv.gz.

## BATCH 69 - KEEP THE TAIL A YARDAGE BONUS IS PAID ON (instrument only; Oct 8 2026)
ASPIRATION: grade the product on every DraftKings line it already draws - the +3 at 100 rushing / 100 receiving / 300 passing yards is decided by the tail of
the yards draws, and the graded record kept only the mean and three quantiles, so six bearing cells (RB 100+ receiving, RB 100+ rushing, WR 100+ receiving,
TE 100+ receiving, QB 100+ rushing, QB 300+ passing) could not be judged (product_reach_read_v1: NO TAIL).
DRIVER: none - no law, no draw, no center changes.  ONE PRODUCER: the thresholds lived as three literals inside dk.skill_dk / dk.qb_dk; they become
dk.BONUS_YARDS, read by the transform and by the grading.
ROOT (deleted): the literals 100, 100, 300 in dk.py's transform; grade_slate's record without the tail.
CHANGE: every graded yards row keeps p_bonus = the share of its draws at or above dk.BONUS_YARDS[its outcome column].
PREDICTION: every draw identical to batch 63b (draw_mean equal on every paired row); THE ONE JUDGMENT UNCHANGED at QB, RB, WR, TE -> ISSUED; the product box
(product_reach_read_v2) grades the six bonus cells, at least five REACHES.  FALSIFIER: any draw differs, or any F8 cell not UNCHANGED: refused, 63b restored.

## BATCH 70 - THE FACTS DOOR CARRIES EVERY DRAFTKINGS LINE (no law, no draw; Oct 8 2026)
ASPIRATION: every line DraftKings scores is a fact in facts - the product can only forecast, and the board can only grade, what facts carries.
DRIVER: none.  The facts door only.
FIVE WHYS: (1) 16 bearing cells read NOT IN PRODUCT (fumbles lost, 2-point conversions, return TDs; every DST line); (2) the product reads facts and nothing
else; (3) facts already computed every one of them - facts.dkpts scores the rare player lines from stats columns, facts.dstpts scores every DST line from
play-by-play - (4) but kept only the totals: the player table's keep list drops the rare columns, and dstpts returns one number; (5) SUB-ROOT: facts
produced the DraftKings totals without the lines they are the sum of.
ROOT (deleted): facts.dstpts (a total without its lines); the keep list without the rare columns; played rows with no stat line left blank (V16: a zero is
written by facts, with the play-by-play as its proof - door_identity_read_v1: no play behind any of 5,180 such blanks).
CHANGE: facts.dst_lines returns each DST line (sacks, interceptions, fumble recoveries, safeties, D/ST TDs, blocked kicks, defensive conversions, points
allowed, its tier) from dstpts' own computation; dst_points_of sums them by DST_SCORING - the one producer of the DST total; the player table keeps
rushing / receiving / sack fumbles lost, passing / rushing / receiving 2-point conversions, special-teams TDs, offensive fumble-recovery TDs, return fumbles
lost; a played row with no stat line carries 0 in every box column.
PREDICTION: DST points identical to the previous facts in every team-game (the same computation, summed in the same order); the lines sum to DST points in
1.000; the independent check against DraftKings unchanged (DST, skill); every product draw identical to batch 69 (192,249 rows), the judgment UNCHANGED.
FALSIFIER: any DST point changes, the guard refuses, or any draw moves: refused, facts.py and facts/ restored.

## BATCH 71 - WHO PLAYS (R1 of handoff_team_game_worlds; driver: on the field; Oct 8 2026)
ASPIRATION: say how likely each candidate is to take the field this week from what is known before the freeze - his own last game, his season, his team's
group at his position, and the injury report as it stood at the freeze.
DRIVER: on the field.  The output it feeds: DraftKings points = (points given he plays) x (he plays), DK draws = F8 draws x Bernoulli(P(plays)) (dk.dnp_zero);
P(plays) also feeds the market's settlement (market.settled).  The F8 draws, the laws given he plays, are not touched (V3).
INFORMATION SET (owner, Oct 8 2026): results through week N-1, week N's schedule and price file, and the injury report AS OF THE FREEZE - one door,
facts.game_status_as_of: the latest row stamped at or before the earlier of Saturday 03:00 ET and the team's kickoff; game designations only (Out, Doubtful,
Questionable).  This moves V1 and reopens Class E (L322) for own-player participation.  The information-set check is unchanged because the report still passes
only through facts: no other module names the report's columns.  Known costs, printed: a row changed after the boundary is not read (8.4% of listings;
its pre-freeze value was overwritten in the file); 2025 and 2026 files carry no stamp - read 'latest - unstamped', never trained on, judged with the largest
measured leak (.0079 per slate) subtracted.  Live weeks are only as-of when the fetch precedes the freeze: an ingest stamp at the freeze is owed (work order).
ROOT (deleted), participation.py as it is: T1 - `rate = (plays + M x parent) / (rows + M), M = 10` (POOLING_STRENGTH = 10, pooled_rates); `def probability_plays
(cells, games_missed_bands, snap_state_labels): ... cells["cells"].get(f"{band}|{label}", cells["role_state_rates"].get(label, cells["base"]))` - one rate per
gap band x role cell, pooled by a chosen constant; FIRST_FIT_SEASON = 2020 (no P(plays) for 2020).  r1_law_read_v1: T1 runs QB OVER z -11.9, TE UNDER +7.4,
OVER at 1 - 4 earlier games and UNDER from 7; who_plays_group_read_v1: the group sum overruns with 2 QB candidates by +.266 (z -12.9), underruns with 3 TE by
-.145 (z +8.8).
LAW (who_plays_group_read_v1, r1_landing_premises_read_v1: DPLR3G): logistic by maximum likelihood per position, fit on the stamped seasons before s: the T1
cell, the exit in his team's previous game (DROP: snap share there minus his season-to-date mean before it), log(1 + earlier games), the logit of his cell's
played rate this season through N-1, the as-of designation, log(candidates in his team-position group) and log(1 + the group's played count per team-game
through N-1).  Per-size group terms (DPLR3GS) were measured and did not earn (2020 gain +.048 vs +.066; RB / TE sizes unchanged) - not carried.
IDENTITIES: P in (0, 1); DK = F8 x Bernoulli(P).  The group identity (the drawn present set) is R2's: the group sums S - K and the dispersion .55 - .96
are printed as R2's reading, not repaired here.
REFUSAL CHECKS: one driver; center only (no draw's spread); every season 2020 - 2025 tested (2019 trains 2020); inputs cover every season; per position;
nothing reconciled after the fit.
DRIVER SCORE (judge71.py, walk-forward, every fit on seasons < s; incumbent = the snapshot's T1 walk-forward): (1) draws.chance_label BETTER on the season
log-loss gains, and BETTER with unstamped seasons' gains less .0079; (2) FALSIFIER strata QB, TE, WR, 2023, 2024 inside chance; (3) REGRESSIONS (strata T1
holds that the law departs) within chance - P(>= r of n held | ALPHA_FAMILY each) > ALPHA_FAMILY - where a season scored on an unstamped report counts as a
construction departure iff the stamped seasons scored on latest statuses shift their season z the same way by at least its excess over the chance line
(r1_landing_premises_read_v1: shifts +1.1, +0.9, +0.8, +0.9 in 2020 - 2024; 2025 z +2.7).
PREDICTION: driver BETTER in all six seasons (r1_landing_premises_read_v1: +.066 .. +.120); falsifier strata held; regressions 3 of 20 counted (2025 a
construction departure), p .075 - within chance; every F8 / F5 / Q draw identical to batch 70 (192,249 rows), R3 UNCHANGED (R3 grades F8 given he plays and
cannot see P(plays) - printed beside the driver verdict for the owner).
FALSIFIER: any gate above fails, the guard refuses, facts' tables change in the rebuild, or any draw moves: refused, participation.py, facts.py and facts/ restored.

## BATCH 72 - THE FETCH STAMPS THE REPORT (door only; no law, no draw; Oct 8 2026)
ASPIRATION: every live week's injury report enters the who-plays law built the way the law was trained - as it stood at the freeze - so batch 71's gain
reaches the forecasts users get, not only the backtest.
DRIVER: none.  The report's door only (on the field's input).
FIVE WHYS: (1) the live door for 2026 w5 reads the report 'latest - unstamped' (judge71); (2) facts.game_status_as_of stamps a row only by date_modified;
(3) nflverse's 2025 and 2026 injury files carry no date_modified column (injury_report_accuracy_read_v2); (4) so a live week cannot show its rows predate
the freeze, and the law, trained as-of, is scored on another construction - stamped seasons scored that way shift z +0.74 .. +1.06 (judge71), the 2025
miss; (5) SUB-ROOT: the one time that bounds every row of a fetched file - when it was fetched - is not kept.
ROOT (deleted): facts.game_status_as_of's `else: ... constructions[season_year] = "latest - unstamped"` as the only reading of a file without date_modified.
CHANGE: ingest.nflverse writes injuries_{y}_fetched.csv (season, fetched_at UTC, after the download - no row of the file can be newer) beside the file it
fetches, accepted with it; facts.game_status_as_of stamps every row of a file without date_modified at its fetch time and counts it only when that is at or
before its week's boundary: 'as of the freeze', the trained construction.  Known cost: each fetch replaces the file and its record, so an earlier week of the
same season reads its rows as not listed once a later fetch lands (issued weeks are already frozen by draws.freeze_draws).  A file with no stamp and no
record (2025; the 2026 file now on disk) stays 'latest - unstamped' until its next fetch.
OWNER (Oct 8 2026, "whatever the best available answer is based on the data"): the DK draw (F8 x who plays, absent graded 0) and the team total will be
graded and BINDING beside R3 - no landing may worsen either beyond chance; built as its own instrument landing next.
PREDICTION: facts' tables identical; game_status_as_of identical for every season on disk (no fetch record exists yet); week_participation(2026, 5)
identical to batch 71; every draw identical to batch 71 (192,249 rows), R3 UNCHANGED, ISSUED.  The first live fetch after this writes the record.
FALSIFIER: the guard refuses, a table or a door row changes, or any draw moves: refused, ingest.py, facts.py and facts/ restored.

## BATCH 73 - GRADE THE SCORE USERS CONSUME (instrument; no law, no draw; Oct 8 2026)
ASPIRATION: judge the product on what a user takes from it - each player's DraftKings points with the chance he plays inside them, and each team's total -
so a change to who plays, or to how a team's volume divides, can be seen and can be refused.
DRIVER: none.  The judgment only.
FIVE WHYS: (1) batch 71 changed the DK draws users consume and THE ONE JUDGMENT read UNCHANGED at every position; (2) the replay grades F8 - points given
he plays - and never draws who plays (grade_slate: slate laws and F8 only); (3) DK = F8 x Bernoulli(P(plays)) exists only in week_draws, the live week;
(4) so R2 (who plays drawn jointly: the team's spread) and R3 (the volume split: the team total and its shares) would move nothing any judge reads, and
would be refused on noise or pass unseen; (5) SUB-ROOT: the judged unit is the player given he plays; the consumed unit is the player's points with his
participation inside them, and the team's total.
ROOT (deleted): the DK draw built inline in week_draws only; product_judgment hard-wired to F8; replay(previous_path) with one previous product.
CHANGE: draws.dk_draws_of - one producer of DK draws for the live week and the replay (each row's own participation substream, dk.dnp_zero); draws.grade_dk
- each DK row against DraftKings' recorded points, 0 for a member who did not play, and DK team total (the sum of the team's members' DK draws, draw by draw,
against the sum of their points), in the graded schema, written to proj/dk_rows.csv.gz; the replay fits the who-plays law once per season through
participation's own producers; product_judgment judges the terms it is given, the term in its record; kit.py replay PREVIOUS_ATLAS_ROWS [PREVIOUS_DK_ROWS].
OWNER (batch 72 entry): the DK cells and the team total are BINDING beside F8 from the next landing that changes a draw or a participation probability: the
product is ISSUED only when no F8, DK or team-total cell is WORSE.  This landing writes their baseline (proj/dk_rows_batch73.csv.gz).
PREDICTION: every draw identical to batch 72 (192,249 rows); F8 UNCHANGED at every position, ISSUED; DK rows for QB, RB, WR, TE and TEAM in every replay
season.  Reading (check73.py, registered here): DK under the who-plays law against DK under T1 on the same draws and uniforms - BETTER at QB and TE, the
positions T1 missed most (z -11.9, +7.4); the team total BETTER or UNKNOWN.
FALSIFIER: the guard refuses, any draw moves, F8 not UNCHANGED, or a DK cell missing for a position or season: refused, draws.py and kit.py restored.  If the
reading shows no cell BETTER, the instrument stands but the claim that batch 71 reaches the consumed score is contradicted - reported, not rescued.

## BATCH 75 - AN ADDED SEASON MAY NOT REWRITE AN OLD ROW (facts door identity; no law; Oct 8 2026)
ASPIRATION: a player-week's facts are about that player-week - adding or removing any other season on disk leaves them exactly as they were.
DRIVER: none.  The facts door only (Law 1: identity is content; a row's provenance never decides it).
FIVE WHYS: (1) batch 74 v2 refused: with the discovery seasons present, player_game's old rows changed; (2) facts_shift_read_v1: two columns only - position
384 rows (e.g. 00-0023368 2019 w5 LB -> DL), name 119 rows (e.g. 00-0033931 2019 'Lano Hill' -> 'Delano Hill'); rows by key, every box score, snap and
outcome identical; (3) both are filled where the stats file carries no row; (4) from `rosters.drop_duplicates("gsis_id")` - the first roster row of any
season on disk, rosters read in season order 2010 - 2029; (5) SUB-ROOT: a value chosen by position in a concatenation - the earliest season on disk -
not by the player-week it describes.
ROOT (deleted): facts.py `fill = rosters.drop_duplicates("gsis_id").set_index("gsis_id")` and the position / name fill read from it.
CHANGE: a missing position / name comes from the player's own roster row that week (player_id, season, week); else from his roster rows that season when
they agree on one value; else it stays undefined.  Never another season.
PREDICTION: this landing itself moves the filled values of old rows once (the same week's or season's roster value replaces the earliest season's); every
box score, snap and outcome identical; THE TEST OF THE ROOT: facts built in a temporary folder with the discovery seasons present leaves every old row
identical to this landing's facts; the guard passes; the judgment (binding: F8, DK, team total against batch 73) has no cell WORSE.
FALSIFIER: the root test finds an old row that moves, a box / snap / outcome column changes, the guard refuses, or any cell is WORSE: refused, facts.py and
facts/ restored.

## BATCH 74 - THE DISCOVERY SEASONS ENTER FACTS (registration under L5063; an engineering transaction, no fetch, no code; Oct 8 2026)
ASPIRATION: every law fits on, and every verdict is judged across, all the seasons the project may use - so a forecast that helps shows it, and one that
does not cannot hide in five seasons of noise.
DRIVER: none named - the information every driver is fit on.  No law, no door, no line of code changes.
FIVE WHYS: (1) R2 and every season verdict ran on 2020 - 2025 (four or five test seasons: the one-sided season t has df 3 - 4); (2) 2019 trains 2020 and
nothing trains 2019; (3) facts holds 2019 - 2021, 2023 - 2026 only; (4) the DISCOVERY tier - 2016, 2017, 2018, 2022 - sits in data/corpus/discovery,
whole, with every kind facts.complete requires (discovery_premises_read_v1: stats, play-by-play, injuries - date_modified 1.000 - rosters, snaps,
participation; columns identical to 2019's, none missing, none extra); (5) SUB-ROOT: the tier designed for readings, atlases and design (L5060) was never
registered into facts (L5063).
CHANGE: the discovery files are copied, under the kit's own names, from data/corpus/discovery into data/ (stats, play-by-play, injuries, rosters, snaps,
participation, schedule; FTN 2022), accepted (kit.py accept: archived, manifest written), and facts is rebuilt.  The LOCKBOX (2012 - 2015) and DEEP LOCKBOX
(1999 - 2011) stay sealed: no season of theirs enters facts or any reading; their budgets (6 judgments each) are untouched.  2022's record: 'deleted as
dirty' for the after-inactives frame (L108, L397), no measurement of its quality on record (L5053) - it enters like the others and is judged with them.
HISTORY OF THIS REGISTRATION: v1 refused before any change (a script defect); v2 refused as registered - old player_game rows moved (position 384, name
119: the first-roster-row fill); batch 75 removed that root (its root test: facts built with these seasons present left every old row identical).
IDENTITY CHECK: every facts row of a season already in facts is identical before and after (the transaction only adds seasons); the independent check against
DraftKings' recorded points holds its floors over the longer span (DST 97.5%, skill 99.5%).
JUDGMENT (binding, batch 72 / 73): replay against batch 75's graded rows and DK rows - on the rows both products graded (2020 - 2025), every law now fit on
up to four more earlier seasons; ISSUED iff no F8, DK or team-total cell is WORSE beyond chance.  The new test seasons (2017 - 2019, 2022) are graded and
unpaired - the next landing's baseline.
PREDICTION: facts seasons 2016 - 2026 less 2012 - 2015 and 1999 - 2011; old rows identical; guard passes; no cell WORSE (more history is not a promise of
BETTER: era and rule changes 2016 - 2018 can pull a fit; the judgment decides); replay seasons 2017 - 2025.
FALSIFIER (v3): an old row changes, the independent check falls below its floor, the guard refuses, or any F8 / DK / team-total cell is WORSE: refused, the copies
removed from data/, facts/ (and its raw manifest) restored.  Then the discovery seasons stay out and the reason is recorded, not rescued.

## BATCH 74 v3 - REFUSED (a non-verdict), RESTORED BY HAND; LANDED WAS PRINTED IN ERROR (Oct 8 2026)
The discovery files were copied and accepted, facts rebuilt with every old row identical, the guard passed - then THE ONE REPLAY refused at its first
cutoff: "fit_sibling F5 rushing TDs TE: seasons < 2017 did not converge (ABNORMAL) - refused" (2.9 s; no atlas, no judgment written).  The script's crash
check compared proj/product_judgment.csv's time with a snapshot of CHARTER.md copied with its old time (cp -p), so batch 75's judgment passed for batch 74's
and LANDED was printed.  That is the script's defect, not a verdict: this transaction removes the 29 copies from data/, restores facts/ and its raw manifest
and proj/ to batch 75, and deletes the batch-74-named copies of batch 75's records.  Every later script checks the replay's own exit code.
FINDING (kept): with 2016 in facts the first replay cutoff is 2017, and one link's fit on one season (TE rushing TDs, sibling law) does not converge - and
one cell's failed fit refuses the whole replay.  Which of the two is the root is the next read; the discovery seasons wait on it.

## BATCH 76 - THE LUCK MAP'S CENTER IS MEASURED ON THE ROWS IT SERVES (chain.moments; Law 4 / Law 1; Oct 8 2026)
ASPIRATION: a rate's center is the rate of the rows that carry it - so a player's first carry, target or snap of the season is forecast at the rate such
plays actually convert, and no link's fit depends on which seasons happen to come first.
DRIVER: every proportion and sibling link (shares, conversions, TDs) - the center every pregame rate shrinks toward.
FIVE WHYS: (1) batch 74 v3: the replay refused at its first cutoff (fit_sibling F5 rushing TDs TE, 2017); (2) fit_cutoff_read_v1: that cell only, cutoffs 2017
and 2018, loss not finite; mu 0 with events (3 / 8, 4 / 24); rows shrunk to exactly 0 carry the events; (3) moments_zero_read_v1: every event at 2017 sits on
a row with no earlier carry that season (n_prior 0); (4) chain.moments measures mu on `(units_prior > 0) & (n > 0)` only, while reliability_shrink gives that
mu to every row with units 0; (5) SUB-ROOT: one fact (the center) measured on a population other than the one that reads it - at cutoff 2017 that subset holds
0 events, so mu = s2 = 0 and the rates are 0 / 1 / undefined; the same split biases today's fits (cutoff 2019: mu 2/42 = .048 against 6/63 = .095 on the
rows it serves).
ROOT (deleted): chain.moments `used = (units_prior > 0) & (n > 0)` as the domain of mu.
CHANGE: mu = sum x / sum n over every row with a unit this game (the rows the law serves); s2 and tau2 over those rows that also have earlier units (a prior
rate's spread needs a prior rate).  No other line changes; the domain (issue_domain) and every reader are untouched.
PREDICTION: ROOT TEST - with the discovery seasons in a temporary facts outside the kit, every link fits at every cutoff 2017 - 2025; the guard passes; the
replay (facts 2019 - 2026 as now) runs to its judgment; on F8, DK and the team total against batch 75 no cell is WORSE (cells reading rare-unit links - TE /
WR rushing, QB receiving - move most; BETTER or UNKNOWN).
FALSIFIER: a link still fails at a discovery cutoff (the root is not this one), the replay exits without a judgment, or any cell is WORSE: refused, chain.py
and proj/ restored.
OPEN (not this landing): a cell with no event in all the rows it serves is unidentified (Law 5: unknown) - and one such cell still refuses the whole replay.

## BATCH 76 - LANDED (records written by a finishing transaction; Oct 8 2026)
ROOT TEST: with the discovery seasons in a temporary facts, every link (32) fits at every cutoff 2017 - 2025; F5 rushing TDs TE mu .375 (2017), .167 (2018),
.095 (2019).  GUARD PASSED.  THE ONE JUDGMENT against batch 75: F8 QB / RB / TE / WR UNKNOWN; DK QB / RB / TE UNKNOWN; DK WR BETTER (2.8502 -> 2.8497,
p .035); DK team total BETTER (14.2632 -> 14.2594, p .011); no cell WORSE - PRODUCT ISSUED.  The script then stopped on its own defect (`status=$?`: a
read-only variable in zsh) before copying the records; this transaction verified the judgment on disk is ISSUED and newer than the snapshot and wrote
atlas_rows_batch76, dk_rows_batch76, replay_report_batch76.  Later scripts name the replay's exit code replay_exit.

## BATCH 74 v4 - THE DISCOVERY SEASONS ENTER FACTS, AGAINST BATCH 76 (registration under L5063; no fetch, no code; Oct 8 2026)
As registered in BATCH 74 (v1 - v3 above): the 2016, 2017, 2018 and 2022 files are copied from data/corpus/discovery into data/ under the kit's names, accepted,
and facts rebuilt; the LOCKBOX and DEEP LOCKBOX stay sealed.  v3 refused at the replay's first cutoff (fit_sibling F5 rushing TDs TE, 2017); batch 76 removed
that root (chain.moments' center measured on the rows it serves; its root test: every link fits at every cutoff 2017 - 2025 with these seasons present).
IDENTITY CHECK: every facts row of a season already in facts is identical before and after.
JUDGMENT (binding): replay against batch 76's graded rows and DK rows - on the rows both graded (2020 - 2025), every law fit on up to four more seasons; ISSUED
iff no F8, DK or team-total cell is WORSE beyond chance.  The new test seasons (2017 - 2019, 2022) are graded and unpaired - the next landing's baseline.
PREDICTION: facts seasons 2016 - 2026; old rows identical; guard passes; the replay exits 0 with a judgment over seasons 2017 - 2025; no cell WORSE (more
history is not a promise of BETTER - era and rule changes 2016 - 2018 can pull a fit; the judgment decides).
FALSIFIER: an old row changes, the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, the copies removed from data/, facts/
(and its raw manifest) and proj/ restored; the discovery seasons stay out and the reason is recorded, not rescued.

## BATCH 77 - THE NEXT-UP VACANCY, ON THE OWNER'S FINAL ACTIVE LIST (facts.active_keys; chain.vacancy; role law t5 / t6; Oct 8 2026)
OWNER (Oct 8, standing): at decision time the final active / inactive list (~90 min before kickoff) is known; only players who played are graded; the
question is role to role (QB1, RB1, RB2, WR1, WR2, TE1, DST).
ASPIRATION: when a usual teammate is out, the player next in line at his position is forecast for the share he actually takes - and gives it back when the
teammate returns.
FIVE WHYS: (1) role_vacancy_read_v1: with a role out the roles who play take more and the product does not move (RB1 out -> RB2 +6.1 carries, product -5.3;
WR1 out -> WR2 +1.6 targets, product -1.8; a QB2 who plays -13.7 attempts); (2) each member's share is drawn apart from who else plays; (3) the product cannot
see who is active - week N's roster status is dropped at the door (WEEKN); (4) handing every inactive's share to the actives double-counts routine absence
(active_share_read_v1: WORSE 7 of 8); within the position in proportion overshoots two-fold (v2); team volume does not move (absorption_read_v1: LEVEL
UNKNOWN x3); the next player up is the one recipient in every season, both ways; (5) SUB-ROOT: the share law has no term for a change in who plays beside him.
CHANGE: facts.active_keys - the one door for week N's active list (ACT; no status row = not active); chain.vacancy - per player the share vacated (out) or
reclaimed (back) by the teammates he is next up to (the active members of the absent player's position with the largest share below his; ties share it),
rate_A x (p(A, B) - [A active]) against his own earlier games; role law logit(mean) + t5 out + t6 back, fit with t0 - t4 by maximum likelihood on seasons < s
(training rows: active = played that week); draws pass the active list to link_rates in the replay and the live week.  roster_status stays dropped at the
door and named only by facts.py.
WALL ALREADY PASSED (native units): vacancy_next_up_read_v1 - learned next-up alpha walk-forward BETTER on F5 carries RB (p .011), F5 targets RB (.009), TE
(.004), WR (.0002), Q1 attempts (.003); none WORSE; alpha stable by season; back < out.
PREDICTION: the guard passes; the replay exits with a judgment; fitted t5 > 0 on F5 carries RB, F5 targets RB / TE / WR and Q1 attempts at every cutoff; on
F8 for players who played, DK and the team total against batch 76: no cell WORSE, F8 RB and WR BETTER or UNKNOWN; the atlas's F5 carries RB, F5 targets
and Q1 attempts cells' paired CRPS falls.
HISTORY: v1 refused before any verdict - the guard's freshness check (facts/ older than facts.py, which gained active_keys); v2 rebuilds facts
and requires every table identical to before.
FALSIFIER: a rebuilt facts table differs, the guard refuses, the replay exits without a judgment, or any F8 / DK / team-total cell is WORSE: refused, facts.py chain.py draws.py and proj/
restored.

## BATCH 78 - ONE DEFINITION OF ACTIVE (chain.vacancy, fit_share, fit_chain read facts.active_keys for training and issue rows; Law 1; Oct 8 2026)
FIVE WHYS: (1) batch 77: the team total further short (bias -.83 -> -1.10, UNKNOWN), QB DK bias +.005 -> -.132, F8 QB UNKNOWN with 2023 - 25 negative;
(2) the vacancy term gives less at issue than it learned; (3) in training a member was active when he played that week, at issue when he is ACT; (4) a
dressed player who sits (P(played | ACT) QB .817, RB .940) is a vacancy in training and none at issue; (5) SUB-ROOT: one fact - who is active - built by
two constructions.
ROOT (deleted): chain.vacancy's played-that-week route (active None).
CHANGE: fit_chain(history, s, active) and fit_share pass the final active list to vacancy for the training rows; draws pass it to fit_chain in the replay
and the live week.  No other line changes.
PREDICTION: the guard passes; the replay exits with a judgment; against batch 77 no F8 / DK / team-total cell is WORSE; the team-total bias moves back
toward -.83; F8 RB / TE / WR UNKNOWN or BETTER (the term's size changes, not its form).
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py draws.py and proj/ restored.

## BATCH 78 - ONE DEFINITION OF ACTIVE (chain.vacancy, fit_share, fit_chain read facts.active_keys for training and issue rows; Law 1; Oct 8 2026)
FIVE WHYS: (1) batch 77: the team total further short (bias -.83 -> -1.10, UNKNOWN), QB DK bias +.005 -> -.132, F8 QB UNKNOWN with 2023 - 25 negative;
(2) the vacancy term gives less at issue than it learned; (3) in training a member was active when he played that week, at issue when he is ACT; (4) a
dressed player who sits (P(played | ACT) QB .817, RB .940) is a vacancy in training and none at issue; (5) SUB-ROOT: one fact - who is active - built by
two constructions.
ROOT (deleted): chain.vacancy's played-that-week route (active None).
CHANGE: fit_chain(history, s, active) and fit_share pass the final active list to vacancy for the training rows; draws pass it to fit_chain in the replay
and the live week.  No other line changes.
PREDICTION: the guard passes; the replay exits with a judgment; against batch 77 no F8 / DK / team-total cell is WORSE; the team-total bias moves back
toward -.83; F8 RB / TE / WR UNKNOWN or BETTER (the term's size changes, not its form).
HISTORY: v1 refused before any verdict - draw_link beta 'b <= 0': under one definition of active, Q1 attempts QB fit t5 67.7 on 13 rows at
cutoff 2020 (trained on 2019 alone) and seven backup QBs' share mean rounded to 1.0; link_rates had dropped role_law's own complement and draw_link rebuilt
it as 1 - rate (draw_crash78_read_v1).  v2 adds patch78b: link_rates carries each rate's complement (a share's from the role law), draw_link draws
beta(rate x c, complement x c) - one construction (Law 4).  vacancy_form_read_v1: the log-share alternative cannot fit (closed); this form fits 2021 -
2025.  OPEN: the 2020 QB coefficient is fit on 13 rows - a backup who starts draws about the whole share.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py draws.py and proj/ restored.

## BATCH 79 - WHAT A PLAYER DOES WITH EACH OPPORTUNITY (career and this season's own rate in every conversion / per-unit link; Oct 8 2026)
QUESTION (the gap, from link_rates -> draw_link): at what rate will this player convert each opportunity next game, given his own record?
CRITERION (produced by the population, no labels): agreement between disjoint views of the same player - a rate built from his earlier games against his
later games it never saw (count squared error at his actual opportunities, season chance test).  Stability (weights steady by season) reported, never alone.
THE RULE BEFORE (luck map, this season's games only) ON THE CRITERION: career_prior_read_v1 - loses on TE yards per catch (MSE 213.6 vs 205.5; top 451.7 vs
417.7), WR yards per catch (432.9 vs 426.8), RB rushing yards (373.1 vs 369.2; top 894.4 vs 862.8), TE receptions, WR receiving TDs, QB rushing yards and TDs;
never wins.  Elite RB under-forecast -1.54 DK (level_bias_read_v1) sits in rushing yards (-.72) and TDs (-.91; TD rate itself UNKNOWN - game context, open).
CHANGE: chain.career_rate (every earlier season), chain.fit_efficiency (weights >= 0 by nonnegative least squares, weighted by units, seasons < s - the rate
is a blend of three estimates of one quantity, so it stays a rate with no clip), chain.efficiency_rate; fit_chain fits the weights for every conversion /
per-unit / sibling link, link_rates applies them.
PREDICTION: the guard passes; the replay exits with a judgment; against batch 78 no F8 / DK / team-total cell is WORSE; F8 TE and WR BETTER or UNKNOWN, RB
UNKNOWN or BETTER; the atlas's F5 receiving yards TE / WR and F5 rushing yards RB paired CRPS fall.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE (the criterion at the product's level): refused, chain.py and proj/
restored.

## BATCH 80 - THE QB'S CAST (his usual receivers' vacated target share in his passing conversions; Oct 8 2026)
QUESTION (the gap, from link_rates -> efficiency_rate): at what rate will this QB convert each pass next game, given which of his usual receivers are active?
CRITERION (produced by the population, no labels): the QB's later games against a rate built from his earlier ones, held out by season (paired CRPS, season
chance test) - and agreement with an independent view: the receivers' side, where the absorbers of a WR1's targets convert less (qb_cast_account_read_v1).
THE RULE BEFORE ON THE CRITERION: qb_cast_read_v1 - with the WR1 out and the usual starter active, passing yards miss -14.2 vs -1.0, yards per attempt -.43
vs +.06 (every season), passing TDs -.23 vs +.03, F8 -1.50 vs +.03, all LESS; attempts UNKNOWN; dose on vacated target share LESS (yards, ypa, TDs per
attempt).  pass_from_catch_read_v1 / v2 (passing as the sum of the receivers' draws) refused: QB F8 and team total WORSE - the QB keeps his own producer.
CHANGE: chain.cast_vacancy (chain.vacancy's form against the QB's own earlier games, on the final active list); chain.fit_efficiency fits a third weight on
it for Q2 completions / Q3 passing yards / Q4 passing TDs (career and season weights >= 0, the cast weight's sign the data's); efficiency_rate applies it.
PREDICTION: the guard passes; the replay exits with a judgment; against batch 79 no F8 / DK / team-total cell is WORSE; F8 QB BETTER or UNKNOWN, DK QB
BETTER or UNKNOWN; skill positions UNCHANGED; the atlas's Q3 passing yards QB paired CRPS falls.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py and proj/ restored.

## BATCH 81 - WORK FOLLOWS EFFICIENCY (the role law reads the conversion law's own estimate of what a player does with each touch; Oct 9 2026)
QUESTION (the gap, from link_rates -> role_law): how much of his team's work will this player get next game, given how well he converts it?
CRITERION (produced by the population, no labels): his later games' volume against a share built from his earlier ones, held out by season (paired CRPS,
season chance) - and agreement with independent views: the vacancy rows' under-feed (#7) sits in the efficient half; per-touch accuracy is saturated
(touch_law_read_v1 - v5: four estimators tie), so the count misses must live in the volume.
THE RULE BEFORE ON THE CRITERION: share_eff_read_v1 / v3 - the volume miss rises with efficiency in every share cell (WR / TE / RB targets, RB carries
MORE; F8 MORE x4; RB carries top fifth +.86 carries, +1.06 DK); the product's own efficiency carries it beside the raw record (WR targets, RB carries) and
survives the previous game's volume (WR, TE, RB carries).
CHANGE: chain.yards_path (from LINKS), chain.efficiency_edge (the conversion law's yards per share unit minus the league's this season to date); role_law
+ t7 x edge, fit by maximum likelihood in fit_share; fit_chain fits the share cells after the conversion cells.  Additive - no hand rule is deleted here;
the role law's rewrite is its own landing.
PREDICTION: the guard passes; the replay exits with a judgment; against batch 80 no F8 / DK / team-total cell is WORSE; F8 RB and WR BETTER or UNKNOWN,
TE UNKNOWN, QB UNKNOWN; the atlas's F5 carries RB and F5 targets WR paired CRPS fall; t7 positive on RB carries and WR targets every season.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py and proj/ restored.

## BATCH 82 - THE TEAM SCORING ENVIRONMENT (a touchdown is a team event: every TD link reads its team's environment going in; Oct 9 2026)
QUESTION (the gap, from link_rates -> the sibling law): how many touchdowns will this player score next game, given the scoring environment his team and
its opponent carry into it?
CRITERION (produced by the population, no labels): his and his team's later TDs against rates built from earlier games, held out by season (paired CRPS,
season chance) - and agreement across layers: the same signals failed on single players with absolute levels (td_context_wall) and on team attempts
(team_quality_wall) and held on the team TD layer (layer_matrix_read_v1: volatility .13, strength +.164).
THE RULE BEFORE ON THE CRITERION: team_td_wall_read_v2 (player rows only; walk-forward 2021 - 2025) - team skill TDs 1.7806 -> 1.7499 BETTER (p .003),
RB F8 centre BETTER (p .008), TE (p .041), QB (p .017), WR UNKNOWN; TD margin +.15 to +.21, edge +.06 to +.10, opponent TD margin -.10 to -.15 every season.
CHANGE: chain_history keeps the opponent; chain.team_environment (team TD margin going in, the conversion law's edge of the usual starter, the opponent's
TD margin going in); fit_sibling fits three environment weights with the sibling law by maximum likelihood; link_rates moves each TD rate by them;
fit_chain fits the TD links after the other conversions; draws carries this week's opponent to the rows.
PREDICTION: the guard passes; the replay exits with a judgment and draws every row it drew before (drew nothing 0); against batch 81 no F8 / DK /
team-total cell is WORSE; F8 RB / TE / QB BETTER or UNKNOWN, WR UNKNOWN; team total BETTER or UNKNOWN; the atlas's F5 TDs RB paired CRPS falls.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py, draws.py and proj/ restored.

## BATCH 83 - PARTICIPATION (a share is earned on the field: the role law reads how much of the game a player is about to play; Oct 9 2026)
QUESTION (the gap, from team volume -> share): what share of his team's targets / carries will this player get next game, given how much of the game he
is about to play?
CRITERION (produced by the population, no labels): his later counts in his team's counts against laws built from earlier games, held out by season
(paired CRPS, season chance) - and agreement across views: the realised snap change carries every share miss every season (share_root_read_v2), and
with it in, the over-feed of high-share players vanishes (#42) and share momentum flips sign.
THE RULE BEFORE ON THE CRITERION: snap_predict_read_v1 - the snap change forecastable before kickoff, walk-forward BETTER for RB (p .0013), WR (p .0006),
TE (p .0007); participation_premises_read_v1 - batch 82's centres moved by it, slope fit on earlier seasons only: RB F8 BETTER (p .007), targets (p .023),
carries (p .027); WR F8 BETTER (p .011), targets (p .0002); TE targets BETTER (p .0006), TE F8 UNKNOWN.
CHANGE: chain_history keeps the snap share; chain.participation (last game's snap share minus his season-to-date mean; snaps vacated by teammates above
him at his position who are not on the final active list; returning from a missed team game); the role law reads them by maximum likelihood (theta
8 - 10) in fit_share and at issue in link_rates.
PREDICTION: the guard passes; the replay exits with a judgment and draws every row it drew before (drew nothing 0); against batch 82 no F8 / DK /
team-total cell is WORSE; F8 RB and WR BETTER or UNKNOWN, TE and QB UNKNOWN.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py, draws.py and proj/ restored.

## BATCH 84 - DELETION: SNAPS VACATED (one fact, one producer: the vacancy fact is chain.vacancy's; Oct 9 2026)
QUESTION (redundancy, from the role law's terms): does the share law forecast any worse without the snaps vacated by teammates above a player?
CRITERION (produced by the population, no labels): role_terms_read_v1 - the chain refit at every cutoff exactly as the product fits it, each share cell
refit with one group of terms held at 0, scored held out by the beta-binomial log-likelihood of the player's count in his team's count, paired row by
row, season chance.
THE RULE BEFORE ON THE CRITERION: t9 snaps vacated EARNS in no share cell - REDUNDANT in six, HARMS WR targets (p .0115, every season) and TE targets
(p .0191); share vacancy t5 + t6 EARNS for RB carries (p .0013), TE targets (p .0006), WR targets (p .030).
KILLED: chain.participation's vacated column (roster, pairs, active-list membership), its active-list argument, the role law's theta[10].
PREDICTION: the guard passes; the replay exits with a judgment and draws every row it drew before (drew nothing 0); against batch 83 no F8 / DK /
team-total cell is WORSE; every F8 cell UNKNOWN or BETTER; chain.py shorter.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py, draws.py and proj/ restored.

## BATCH 85 - DRAIN, JUDGED BEFORE LANDING (two role-law terms held at 0 where the gate's own ruler says they harm or carry nothing; Oct 9 2026)
QUESTION (redundancy, from the role law's terms): does the share law forecast as well or better without snap momentum in QB attempts and without share
momentum in WR / TE targets?
CRITERION (produced by the population, no labels): the gate itself, run in memory before landing - masked_gate_read_v2 (self-checked: 'none'
reproduced batch 83 in all 39 cells; 't9@*' reproduced batch 84's refusal), product_judgment against batch 83's rows, every atlas cell by season chance.
THE RULE BEFORE ON THE CRITERION: t8 held at 0 in Q1 attempts QB - F8 QB BETTER (p .028), DK QB BETTER (p .020), Q4 passing TDs BETTER (p .014),
nothing WORSE; t1 held at 0 in WR / TE targets - every cell UNKNOWN or UNCHANGED, nothing WORSE.  Refused by the same instrument and not landed: the
luck map's share on TE / WR / QB carries (QB rushing yards WORSE, p .033).
KILLED: three fitted weights - theta[8] in Q1 attempts QB, theta[1] in F5 targets WR and TE (fit_share holds them at 0 by bounds, ROLE_TERMS_HELD).
PREDICTION: the guard passes; the replay exits with a judgment and draws every row it drew before (drew nothing 0); against batch 83 F8 QB and DK QB
BETTER, every other F8 / DK / team-total cell UNKNOWN or UNCHANGED, none WORSE - the in-memory verdicts reproduced.
FALSIFIER: the guard refuses, the replay exits without a judgment, or any cell is WORSE: refused, chain.py, draws.py and proj/ restored.
