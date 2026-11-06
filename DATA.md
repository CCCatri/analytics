# DATA.md — the fields that carry the claim, then every column on disk

Definitions first for the fields the lead case depends on; then the column lists as read from the files on 2026-11-06, with the kit taxonomy's short definition where it has one (`slate-kit/TAXONOMY.md` is the full vocabulary).

## Fields that carry the claim

- **team attempts** — a team's pass attempts in one game: dropbacks ending in a throw plus accepted-penalty plays recorded as a pass attempt, never sacks (the reconciled counting rule, `cases/two-components-had-to-agree-on-what-counts-as-an-attempt.md`). Kit root cell `("F2 team attempts", TEAM)`; engine field `attempts` in the root-draw file.
- **team carries** — a team's rushing attempts in one game: runs, scrambles and kneels plus accepted-penalty plays recorded as a rush attempt. Kit root cell `("F2 team carries", TEAM)`; engine field `carries`.
- **player attempts (`Q1 attempts`)** — one quarterback's pass attempts in that game, drawn as his share of his team's attempts from his own history.
- **source draw** — one simulated playing of the game by the engine; `draw_id` 0..K-1 in `out/handoff/root_draws_<season>_w<week>.npz` (K = 30 for the Week 15 fixture). Kit column j reads source draw j mod K; a change to source draw d appears at every column j with j mod K = d and nowhere else.
- **observed vs simulated** — `slate-kit/facts/*` are observed (built from the recorded play-by-play, stats, rosters, injuries, snaps). Everything under `draws` is simulated by the kit; in engine mode the two root cells are simulated by the engine instead. A card's `root_source` says which.
- **root_source / root_file / root_file_sha / root_source_draws / root_columns** — engine-mode provenance on every card row: the root came from `engine`; the file it came from; that file's SHA-256 as computed at issue time; how many source draws it held; how many kit columns they were expanded to. Absent in kit mode (schema unchanged).
- **grading_basis** — on engine-mode cards: the atlas and ladder columns are kit baseline evidence, graded on the kit law's replay, not on engine-rooted draws.
- **draw_mean** — the mean of the 2,000 draws the card row was issued from; the demo checks it equals the mean of the draws the player actually consumed.

## card_<season>_w<week>.csv (the issued card)

| column | taxonomy short definition |
|---|---|
| `season` |  |
| `week` |  |
| `player_id` |  |
| `name` |  |
| `team` |  |
| `position` |  |
| `term` |  |
| `law_family` |  |
| `law_state` |  |
| `layer` |  |
| `provenance` |  |
| `conditioned_on_draw` |  |
| `center` |  |
| `center_source` |  |
| `draw_mean` |  |
| `quantile_10` |  |
| `quantile_25` |  |
| `quantile_50` |  |
| `quantile_75` |  |
| `quantile_90` |  |
| `issuable` |  |
| `atlas_qualification` |  |
| `atlas_rows` |  |
| `atlas_coverage_10` |  |
| `atlas_coverage_90` |  |
| `atlas_bias_mean` |  |
| `ladder_rung` |  |
| `ladder_center_share` |  |
| `ladder_center_band` |  |
| `ladder_tail_share` |  |
| `ladder_width_band` |  |
| `ladder_lower_share` |  |
| `ladder_upper_share` |  |
| `ladder_tail_balance` |  |
| `ladder_crpss` |  |
| `ladder_skill` |  |
| `reference_status` |  |
| `prospective_evidence` |  |
| `conditioning` |  |
| `probability_plays` |  |
| `participation_status` |  |
| `dependence_status` |  |
| `issue_mode` |  |
| `root_source` |  |
| `root_file` |  |
| `root_file_sha` |  |
| `root_source_draws` |  |
| `root_columns` |  |
| `grading_basis` |  |

## slate-kit/facts/game.csv.gz

| column | taxonomy short definition |
|---|---|
| `game_id` |  |
| `season` |  |
| `week` |  |
| `gameday` |  |
| `gametime` |  |
| `home_team` |  |
| `away_team` |  |
| `home_score` |  |
| `away_score` |  |
| `spread_line` |  |
| `total_line` |  |
| `home_rest` |  |
| `away_rest` |  |
| `div_game` |  |
| `roof` |  |
| `surface` |  |
| `temp` |  |
| `wind` |  |

## slate-kit/facts/team_game.csv.gz

| column | taxonomy short definition |
|---|---|
| `game_id` |  |
| `season` |  |
| `week` |  |
| `team` |  |
| `opponent` |  |
| `is_home` |  |
| `implied` |  |
| `fav_by` |  |
| `total_line` |  |
| `rest` |  |
| `pts_for` |  |
| `pts_against` |  |
| `plays` |  |
| `dropbacks` |  |
| `pass_rate` |  |
| `sacks_taken` |  |
| `giveaways` |  |
| `epa_play` |  |
| `redzone_plays` |  |
| `neutral_pass_rate` |  |
| `penalties` |  |
| `penalty_yards` |  |
| `drives` |  |
| `neutral_seconds_per_play` |  |
| `trail_pass_rate` |  |
| `trail_plays` |  |
| `trail_spp` |  |
| `lead_pass_rate` |  |
| `lead_plays` |  |
| `lead_spp` |  |
| `dst_sacks` |  |
| `dst_interceptions` |  |
| `dst_fumble_recoveries` |  |
| `dst_safeties` |  |
| `dst_tds` |  |
| `dst_blocked_kicks` |  |
| `dst_defensive_conversions` |  |
| `dst_points_allowed` |  |
| `dst_points_allowed_tier` |  |
| `dst_points` |  |
| `dst_salary` |  |

## slate-kit/facts/player_game.csv.gz

| column | taxonomy short definition |
|---|---|
| `player_id` |  |
| `season` |  |
| `week` |  |
| `team` |  |
| `name` |  |
| `position` |  |
| `dk_points` |  |
| `attempts` |  |
| `completions` |  |
| `passing_yards` |  |
| `passing_tds` |  |
| `passing_interceptions` |  |
| `sacks_suffered` |  |
| `carries` |  |
| `rushing_yards` |  |
| `rushing_tds` |  |
| `targets` |  |
| `receptions` |  |
| `receiving_yards` |  |
| `receiving_tds` |  |
| `rushing_fumbles_lost` |  |
| `receiving_fumbles_lost` |  |
| `sack_fumbles_lost` |  |
| `passing_2pt_conversions` |  |
| `rushing_2pt_conversions` |  |
| `receiving_2pt_conversions` |  |
| `special_teams_tds` |  |
| `off_fr_td` |  |
| `st_fumbles_lost` |  |
| `receiving_air_yards` |  |
| `carry_share` |  |
| `target_share` |  |
| `air_yards_share` |  |
| `redzone_targets` |  |
| `goal_line_targets` |  |
| `redzone_carries` |  |
| `goal_line_carries` |  |
| `redzone_attempts` |  |
| `redzone_target_share` |  |
| `redzone_carry_share` |  |
| `recorded` |  |
| `snap_share` |  |
| `offense_snaps` |  |
| `played` |  |
| `salary` |  |
| `report_status` |  |
| `practice_status` |  |
| `roster_status` |  |
| `game_id` |  |
| `opponent` |  |

## Root-draw file (`out/handoff/root_draws_<season>_w<week>.npz`)

Arrays `game_id`, `team`, `opponent`, `season`, `week` (one row per team-game), `draw_id` (K), `attempts` and `carries` (rows × K). The manifest beside it records the engine sha, the fit mode, the counting rule, the file's own sha and the games file it was drawn with.
