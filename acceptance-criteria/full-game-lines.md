# Full-game lines: a line names the game it is about, and is graded only on games that match (the project owner's law, 2026-11-10)

Sentence served: the player level, "He gets N of his group's, because ___": N is his share of a game he plays from start to finish. Terms as in `VOCABULARY.md`.

1. Every player's projection is for a full game (the project owner's premise, 2026-11-08: no mid-game injuries). Whether he plays at all is a separate layer above it: P(plays), and for a quarterback P(starts), one quarterback per world (`one-game-one-reality.md`).
2. A share measured over every game a player appeared in blends full games, games he left and games he came into, so it reads low for a full game and high for a relief appearance. A player's share is measured on full games only.
3. Grading: a full-game line is graded only on games the record shows he played in full; his other games are written apart with their kind of game and reported beside the graded ones, never dropped. The team's lines are graded on every game: the team total holds whoever plays (`one-game-one-reality.md`, clause 5). A DK line (DNP = 0) is graded on every game except those with a change at his position during the game, which are set apart the same way.
4. Status by position, each walked from the record:
   - QB passing and F8: ESTABLISHED. Full game = the only quarterback to throw a pass for his team that game (`draws.qb_games`). Full-game share 0.9975 of the team's attempts, measured at each cutoff. Replay 2026-11-10 on 1,483 finished games against the previous product: attempts CRPS 4.83 to 4.39, bias -2.03 to -0.20 (now decision-qualified, rung 3); passing yards bias -14.7 to -1.6; F8 CRPS 4.568 to 4.446, BETTER (p 0.025). Set apart: 1,470 rows from games he left, 678 relief, 396 did not throw.
   - QB carries: NOT YET MEASURED on full games; still the share of every game he played, and its label says so.
   - RB, WR, TE: NOT YET MEASURED. No record test of a full game is in use for them yet; the next measurement reads what the record holds (snap counts) before any share changes.
5. Judged by `checks/check_full_game_qb.py` (the card) and `checks/check_full_game_grading.py` (the replay), each with a self-test that catches its injected faults.
