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

## 4. The two quality gates on a joined run (in this order; the second does not run until the first passes)
Quality gate 1 - legality of what the engine hands over: the generated games behind the root draws pass the unchanged record checks (engine-legality.md section 4)
with coverage printed; the four injected violations P1-P4 are each rejected through that path. A failing control or an undetected violation stops here. PASSED 2026-11-05 on 2024 w15 (30 draws; P1-P4 each detected on its own line; engine-legality.md Status).
Quality quality gate 2 - what the engine contributed: the kit's replay (kit.py replay) run twice on the same slate window, same salaries, eligibility and scoring rule, with
ROOT_SOURCE 'kit' and 'engine'; paired by (season, week, key, term); the season chance test as the kit already defines it (BETTER / WORSE / UNKNOWN /
UNCHANGED). Exposure stated before the number: the window is unseen only if the engine's fits for season s read seasons < s; with the current look-back
fits the result is reported as IN-SAMPLE AT THE ROOT and is not the integration claim. An UNKNOWN is reported as UNKNOWN.

## 5. What is not claimed
No forecast-accuracy claim for the engine until quality gate 2 reads BETTER on a window whose exposure is stated and clean. The first priced slate traced to engine
draws (quality gate 1 passed, the file's manifest in the card's provenance) is the integration milestone; it is not an accuracy result.

## 6. Integration checks (pinned 2026-11-05, before the adapter is written)
Contract: the kit's downstream path is fixed-width at DRAW_COUNT = 2,000 columns (draw_link, player_draw_matrix), so engine mode emits 2,000 columns from the
fixture's 30 source draws by the rule: kit column j (zero-based) takes engine draw j mod 30, both teams of a game from the same engine draw. Provenance records
source draws 30, emitted columns 2,000, the manifest's draw_count read from the file; under this rule source draws 0-19 appear 67 times and 20-29 appear 66 times.
Fixture: out/handoff/root_draws_2024_w15.npz. 2024 w15 is an integration fixture only.
Check A - kit mode: ROOT_SOURCE = 'kit' reproduces today's card_2026_w4.csv identical by (season, week, player_id, term) in every value (the comparison that read
0 changed on 2026-11-05), and the replay's paired rows unchanged.
Check B - trace the draw: a fresh card for the fixture week carries the draw file's SHA-256 in its provenance; at kit column 30 (past the first cycle) the root
draw for a named team equals the engine file's attempts (or carries) at source index 0 for that team, and the opponent's root at column 30 equals the engine's
value at source index 0 for the opponent in the same game; that source draw is followed through one downstream term (the named player's share) on the fresh card.
Check C - verify the file: a SHA mismatch is the hash computed from the draw file on disk differing from the hash the manifest states; a missing file, a mismatch,
a team with a game but absent from the file, or a draw_count that does not equal the arrays' width each produce an explicit refusal naming the cause, write no
card in engine mode, and never fall back to the kit's own root draw in the same run.
The forward-evaluation window is chosen separately and declares one hold-out (the kit lists 2022 as readable; the engine holds it out); until then no comparison
is run.

### Section 6 results (2026-11-06, run 20261105_220733, PASS)

One command, `checks/run_handoff.sh`; evidence in `cases/evidence/handoff_20261105_220733/`. Baseline: pre-adapter `draws.py`/`cards.py` run in an isolated copy on the same inputs, six replay outputs absent before and present after. A1: kit-mode card 2026 w4 equal to the baseline card by column set, key and value. A2: kit-mode replay in a second isolated copy from the same snapshot and identity — 192,330 atlas rows and 26,722 DK rows equal by key and value, `atlas.csv` and `ladder.csv` byte-identical, grader 9 cells UNCHANGED (judged separately). B: columns 29/30/31 = source 29/0/1, both teams, both terms; Ridder (00-0038122) Q1 attempts received LV's root at the boundary. B2: LV source draw 0 raised 36 → 60 (mapped columns named before the run); team root moved at all 67 mapped columns only; player moved at mapped columns only; received 60 at column 30, drawn attempts 6 → 10. C: four isolated injected faults, cached wrong week, source typo — all refused by name, no artifact. Run 20261105_210053 before it: FAIL on two harness assertions (replay required to change the bytes of its own already-identical outputs), kept as the original. Not shown: forecast improvement on predictions recorded before kickoff; the forward window remains the separate gate. Open: a clean-checkout demo (the card refuses in a clone without the live proj/ state).
Closed 2026-11-06: the clean-checkout demo (`checks/demo_w15.py`) passed from a fresh clone at `babfb39` in 100 s; its inputs are the pinned fixtures in `checks/fixtures/demo_w15/` (atlas, ladder, five injuries files) plus the tracked `facts/` and engine fixture. Still open: confirm the nflverse redistribution terms noted in `ORIGINS.md` before the repository is public; `checks/handoff_identity.py` records `raw_pin_sha` as None (path to the engine's raw pin to be corrected).
