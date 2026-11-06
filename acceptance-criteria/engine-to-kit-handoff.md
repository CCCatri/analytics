# engine-to-kit-handoff.md - the one interface between the engine and the slate kit (written before code, 2026-11-05)

## 0. What is handed over, and where it lands
The kit's chain has two root cells with no parent, drawn today as the team's pregame center x a bootstrapped ratio (draws.draw_link, kind 'level'):
("F2 team attempts", TEAM) and ("F2 team carries", TEAM). The engine replaces those two draws for the teams of one issue week and nothing else; every
other cell keeps drawing from its parent's draw by the kit's own laws. Draw j stays one world: the same engine game supplies both teams' attempts and
carries at index j.

## 1. Reconciliation (measured 2026-11-05; checks/reconcile_root_counts_by_position.py, exit 1 unless every team-week is equal)
The kit's root counts are sums over its priced universe (facts.load filters to QB, RB, WR, TE) of the nflverse weekly stats file, regular season, per (season, week,
team), team codes normalized (OAK->LV, SD->LAC, LA/STL->LAR). The engine-side count that equals them to the row, on 3,200 of 3,200 regular-season team-weeks
2019-2021, 2023-2025: attempts = snaps of kind pass or spike, plus accepted-foul rows (kind penalty) carrying pass_attempt = 1 that are not sacks; carries = snaps
of kind run, scramble or kneel, plus accepted-foul rows carrying rush_attempt = 1; two-point tries excluded; counted only where the ball-handler's stats-file
position is QB, RB, WR or TE. The last clause was found by two rows: 2024 w15 HOU, a fake-punt run nullified by a foul that the stats file still credits
(Ogunbowale, play 2274), and 2025 w2 PIT, the intentional-grounding row the downs check pins as P9 (Rodgers, play 3686). Snaps outside the universe (289 FB
carries, 51 punter passes, a scatter of defenders', linemen's and kickers' snaps over six seasons) are in the engine's team totals and outside the kit's root by
the kit's definition; the handoff file counts the universe definition and prints both totals.

## 2. The file (one per issue week)
out/handoff/root_draws_{season}_w{week}.npz holding, for every team with a scheduled game that week: game_id, season, week, team, opponent, draw_id (0..DRAW_COUNT-1,
the engine game index), attempts, carries (whole counts), plus a manifest JSON beside it: engine.py sha, the model-file shas from out/engine/MANIFEST.json, the
fit cutoff ("seasons < {season}" or "look-back: the five other seasons" - stated, never implied), the information set ("through week N-1"), DRAW_COUNT, and
the teams with no engine game (listed by reason). A team listed there is UNDRAWN at the root in the kit with that reason (draws.draw_slate's undrawn rows),
never filled from the kit's own ratio draw in the same run.

## 3. Adapter rule
The adapter touches draw_link's 'level' branch only, behind one switch (ROOT_SOURCE = 'engine' | 'kit'); with 'kit' the product is byte-identical to today
(checked by the replay's paired rows: every CRPS unchanged). The adapter reads the file, checks the manifest shas, refuses on a mismatch, and passes the
attempts and carries arrays as the root draws. Players, shares, conversions and DK transforms are untouched; missing players are the kit's own business
(participation, DNP = 0) and are not changed by the handoff.

## 4. The two gates on a joined run (in this order; the second does not run until the first passes)
Gate 1 - legality of what the engine hands over: the generated games behind the root draws pass the unchanged record checks (engine-legality.md section 4)
with coverage printed; the four injected violations P1-P4 are each rejected through that path. A failing control or an undetected violation stops here. PASSED 2026-11-05 on 2024 w15 (30 draws; P1-P4 each detected on its own line; engine-legality.md Status).
Gate 2 - what the engine contributed: the kit's replay (kit.py replay) run twice on the same slate window, same salaries, eligibility and scoring rule, with
ROOT_SOURCE 'kit' and 'engine'; paired by (season, week, key, term); the season chance test as the kit already defines it (BETTER / WORSE / UNKNOWN /
UNCHANGED). Exposure stated before the number: the window is unseen only if the engine's fits for season s read seasons < s; with the current look-back
fits the result is reported as IN-SAMPLE AT THE ROOT and is not the integration claim. An UNKNOWN is reported as UNKNOWN.

## 5. What is not claimed
No forecast-accuracy claim for the engine until gate 2 reads BETTER on a window whose exposure is stated and clean. The first priced slate traced to engine
draws (gate 1 passed, the file's manifest in the card's provenance) is the integration milestone; it is not an accuracy result.

## 6. Integration checks (pinned 2026-11-05, before the adapter is written)
Fixture: out/handoff/root_draws_2024_w15.npz, draw_count 30 (the kit's root draws 2,000). Pinned rule: kit draw j takes engine draw j mod 30, so the two teams of
a game stay in one world; the manifest's draw_count is read, never assumed. Before the switch is wired, the downstream path is shown to accept a 30-column root
and to carry draw identity across both teams of a game (one game, both teams, draw j on each side from the same engine game).
Check A - kit mode: ROOT_SOURCE = 'kit' reproduces today's card_2026_w4.csv identical by (season, week, player_id, term) in every value (the comparison that
read 0 changed on 2026-11-05), and the replay's paired rows unchanged.
Check B - engine mode: a fresh card for the fixture week carries the draw file's sha in its provenance, and one traced row (a named player, one term) shows the
root draw at index j equal to the engine file's value for his team at j, with the opponent's root at j from the same engine game.
Check C - broken handoff: a missing draw file, a manifest sha mismatch, a team absent from the file, or a draw_count that does not match the arrays each produce
an explicit refusal naming the cause; no fallback to the kit's own root draw in the same run.
2024 w15 is an integration fixture only. The forward-evaluation window is chosen separately and declares one hold-out (the kit lists 2022 as readable; the engine
holds it out); until then no comparison is run.
