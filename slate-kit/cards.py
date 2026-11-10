"""cards.py - the Player Forecast card (Slate Kit module map: cards).  A reader only: every field is a law, a draw summary, an atlas cell or a named status; the card
computes no statistic.  The stat forecast is given he plays; P(he plays) stands beside it from participation (M5, T1), never merged into it; cross-player dependence is not modelled (M9).
Writes proj/card_{SEASON}_w{WEEK}.csv (one row per issued stat of an issued candidate, F8 included) and proj/card_{SEASON}_w{WEEK}_candidates.csv (every candidate once,
with its coverage status: ISSUED, NOT ISSUED with its reason, or UNRESOLVED POSITION, and its participation status and P(plays)) and proj/card_{SEASON}_w{WEEK}_dst.csv
(one row per DST law).  Each row names its conditioning: given he plays (stats, F8), DNP = 0 (DK), or the defense plays every game (DST).  The issued draws behind it
are frozen by draws.freeze_draws to proj/frozen_draws_{SEASON}_w{WEEK}.npz, the market's only source.
Root provenance (2026-11-05): every card row, the candidates file and the report carry the issue's root source - 'kit', or 'engine' with the draw file, its computed
SHA-256, the source draw count and the emitted column count (draws.root_record) - so an engine-rooted card is identified on the artifact itself."""
import os, numpy as np, pandas as pd
from ingest import PROJ_DIR, Report
from facts import load_as_of, team_game, read_table, SKILL_POSITIONS
from state import ISSUE_WEEKS, HISTORY_MINIMUM
from dk import F8_TERM, DK_TERM, DST_TERM
from draws import week_draws, freeze_draws, LINK_CHAIN_STATE
CONDITIONING = "given he plays"
DNP_CONDITIONING = "DNP = 0: P(plays) mixed into the draws"
ALL_WORLDS = "every world (carried over unchanged)"   # acceptance-criteria/one-game-one-reality.md: a quarterback line names the world he starts in
DST_CONDITIONING = "the defense plays every game"
DST_PARTICIPATION = "NOT APPLICABLE - the defense plays every game"
DEPENDENCE_STATUS = "cross-player dependence NOT MODELLED (M9); within-player order as earned"
ISSUE_MODE = "DRY RUN - not prospective"
GRADING_BASIS = "kit baseline evidence: atlas and ladder judgments graded on the kit law's replay, not on engine-rooted draws"
FLAG_K = 4.0   # games of the position's mean blended into a skill player's own season-to-date average (fixed before the run, 2026-11-08)
FLAG_CELLS = {("F5 targets", "WR"): ("targets", 0.5, 29, 27), ("F5 targets", "TE"): ("targets", 0.5, 33, 28), ("F5 carries", "RB"): ("carries", 0.5, 33, 37),
              ("F5 receiving yards", "TE"): ("receiving_yards", 0.5, 30, 28), ("F5 rushing yards", "RB"): ("rushing_yards", 0.5, 28, 35)}
# selected 2026-11-08 through excel_struggle itself: largest 2020-24 lift with >= 10% of lines flagged and shuffled projections earning <= +5; judged on 2025.
# RB targets, WR and RB receiving yards: clean lift but under 10% flagged at every threshold tried; QB attempts: shuffled projections kept +9 to +11 (regression to the mean, not the projection)
FLAG_COLUMNS = ["baseline", "baseline_own_mean", "baseline_games", "baseline_sd", "delta", "z", "flag", "flag_threshold_sd", "flag_evidence"]   # appended to the stat lines only; DST rows carry no flag
# (term, position) -> (stat column, threshold in SDs chosen on 2020-24, lift in points on 2020-24, lift on 2025 held out); a cell not listed has no measured threshold
def excel_struggle(rows, history, season, week):
    """EXCEL / STRUGGLE against the player's own baseline (definition fixed 2026-11-08; threshold per cell chosen on 2020-24, judged on 2025 held out).
    Baseline: his mean in his earlier games this season (3 or more), blended with his position's mean so far by FLAG_K games for RB / WR / TE; his own mean for a QB.
    z = (projection - baseline) / his game-to-game SD so far, blended with his position's SD by the same FLAG_K games (a QB: his own SD). EXCEL when z is above the cell's threshold, STRUGGLE when below minus the threshold, WITHIN NOISE between.
    A line whose cell has no measured threshold, or a player with fewer than 3 earlier games or no spread, is NOT RATED with its reason.
    Returns a frame aligned to rows: baseline, baseline_games, baseline_sd, delta, z, flag, flag_threshold_sd, flag_evidence."""
    earlier = history[(history.season == season) & (history.week < week)]
    n = len(rows); base = np.full(n, np.nan); own = np.full(n, np.nan); games = np.zeros(n); sd = np.full(n, np.nan); thr = np.full(n, np.nan)
    flag = np.array(["NOT RATED - no measured threshold for this line"] * n, dtype=object); ev = np.array([""] * n, dtype=object)
    keys = rows.key.astype(str).to_numpy(); terms = rows.term.to_numpy(); positions = rows.position.to_numpy(); proj = rows.draw_mean.to_numpy(float)
    for col in sorted({cell[0] for cell in FLAG_CELLS.values()}):
        e = earlier[["player_id", "position", col]].dropna(); agg = e.groupby("player_id")[col].agg(["count", "mean", "std"]); pos_mean = e.groupby("position")[col].mean(); pos_var = e.groupby("position")[col].var()
        for (term, position), (c, t, dev_lift, hold_lift) in FLAG_CELLS.items():
            if c != col: continue
            idx = np.where((terms == term) & (positions == position))[0]
            if not len(idx): continue
            a = agg.reindex(keys[idx]); cnt = a["count"].fillna(0).to_numpy(); m = a["mean"].to_numpy(float); s = a["std"].to_numpy(float); pm = float(pos_mean.get(position, np.nan)); pv = float(pos_var.get(position, np.nan))
            b = m if position == "QB" else (cnt * m + FLAG_K * pm) / (cnt + FLAG_K)
            s = s if position == "QB" else np.sqrt((cnt * np.square(s) + FLAG_K * pv) / (cnt + FLAG_K))   # his spread blended with the position's by the same FLAG_K games as his average
            base[idx] = b; own[idx] = m; games[idx] = cnt; sd[idx] = s; thr[idx] = t
            ev[idx] = f"lift {dev_lift:+d} points on 2020-24, {hold_lift:+d} on 2025 held out (flagged lines landing on the flagged side of the baseline, minus lines near it)"
            ok = (cnt >= 3) & np.isfinite(s) & (s > 0); z = np.where(ok, (proj[idx] - b) / np.where(ok, s, 1.0), np.nan)
            flag[idx] = np.where(~ok, "NOT RATED - fewer than 3 earlier games this season or no spread", np.where(z > t, "EXCEL", np.where(z < -t, "STRUGGLE", "WITHIN NOISE")))
    good = np.isfinite(sd) & (sd > 0); delta = proj - base; z_all = np.where(good, delta / np.where(good, sd, 1.0), np.nan)
    return pd.DataFrame(dict(baseline=base, baseline_own_mean=own, baseline_games=games, baseline_sd=sd, delta=delta, z=z_all, flag=flag, flag_threshold_sd=thr, flag_evidence=ev), index=rows.index)
ROOT_FIELDS = ["root_source", "root_file", "root_file_sha", "root_source_draws", "root_columns"]
LADDER_FIELDS = {"rung": "ladder_rung", "center_share": "ladder_center_share", "center_band": "ladder_center_band", "tail_share": "ladder_tail_share", "width_band": "ladder_width_band",
                 "lower_share": "ladder_lower_share", "upper_share": "ladder_upper_share", "tail_balance": "ladder_tail_balance", "crpss": "ladder_crpss", "skill": "ladder_skill",
                 "prospective_evidence": "prospective_evidence"}
REFERENCE_LAW = "the season-to-date reference (his earlier played outcomes of this stat this season, draws.reference_crps)"
def reference_status(crpss):
    """The cell's standing against the season-to-date reference, read from the ladder's CRPSS on the cell's graded rows (CHARTER v1 FINISH LINE item 3): the sign of the
    measured comparison decides it, no threshold.  The issued quantiles stay the kit law's; the status names which forecast the history prefers."""
    return np.select([np.isnan(crpss), crpss < 0, crpss == 0], ["NO LADDER CELL - not graded against the reference",
                      f"REFERENCE CURRENTLY PREFERRED - {REFERENCE_LAW} scored lower CRPS than the kit law on this cell's graded rows",
                      f"TIE - {REFERENCE_LAW} and the kit law scored equal CRPS on this cell's graded rows"],
                     f"KIT LAW - lower CRPS than {REFERENCE_LAW} on this cell's graded rows")
def coverage_status(candidate, issued_keys, undrawn_keys, earlier_played, earlier_played_season, team_earlier_games, issue_week):
    """The one coverage status of a candidate, in order: UNRESOLVED POSITION; ISSUED; NOT ISSUED with the first reason that holds (laws that drew nothing, week, his
    earlier played games on the team, split by whether a team change is why, the team's earlier games); else NOT ISSUED - unexplained.  The thresholds are state's."""
    if candidate.position == "UNRESOLVED POSITION": return "UNRESOLVED POSITION - no earlier played labelled game this season"
    if candidate.player_id in issued_keys: return "ISSUED"
    if candidate.player_id in undrawn_keys: return "NOT ISSUED - every law row drew nothing (undefined parameters)"
    if issue_week not in ISSUE_WEEKS: return f"NOT ISSUED - week outside {ISSUE_WEEKS.start}-{ISSUE_WEEKS.stop - 1}"
    if earlier_played.get((candidate.player_id, candidate.team), 0) < HISTORY_MINIMUM:
        if earlier_played_season.get(candidate.player_id, 0) >= HISTORY_MINIMUM: return f"NOT ISSUED - team change: fewer than {HISTORY_MINIMUM} earlier played games on this team, {HISTORY_MINIMUM}+ this season"
        return f"NOT ISSUED - fewer than {HISTORY_MINIMUM} earlier played games on this team this season"
    if team_earlier_games.get(candidate.team, 0) < HISTORY_MINIMUM: return f"NOT ISSUED - team has fewer than {HISTORY_MINIMUM} earlier games this season"
    return "NOT ISSUED - unexplained"
def card(issue_season, issue_week):
    """python3 kit.py card SEASON WEEK: the week's issued draws and laws, graded by the atlas cell of each (term, position, state) and by its trust-ladder
    cell (proj/ladder.csv: rung, center, width and tails, skill vs the season-to-date reference, prospective evidence, reference status), with every candidate's status.
    Refused if a graded row has no ladder cell, a ladder cell lands on an ungraded row, or a ladder cell's qualification or rows differ from the atlas it was read from."""
    report = Report(); week = week_draws(issue_season, issue_week); candidate_rows = week["issued"]["candidates"]; week_laws = week["laws"]; summaries = week["summaries"]
    root = week.get("root", dict(root_source="kit", root_file="", root_file_sha="", root_source_draws=np.nan, root_columns=np.nan))
    engine_fields = ({**{field: root[field] for field in ROOT_FIELDS}, "grading_basis": GRADING_BASIS} if root["root_source"] == "engine" else {})   # engine-mode artifacts only: kit mode keeps its schema
    player_rows = load_as_of(issue_season, issue_week); names = player_rows.sort_values(["season", "week"]).drop_duplicates("player_id", keep="last").set_index("player_id")["name"]
    before = player_rows[(player_rows.season == issue_season) & (player_rows.played == 1)]
    earlier_played = before.groupby(["player_id", "team"]).size().to_dict(); earlier_played_season = before.groupby("player_id").size().to_dict()
    team_games = team_game(); team_earlier_games = team_games[(team_games.season == issue_season) & (team_games.week < issue_week) & team_games.plays.notna()].groupby("team").size().to_dict()
    player_summaries = summaries[~summaries.position.isin(["TEAM", "DST"])]; issued_keys = set(player_summaries.key); stat_summaries = player_summaries[player_summaries.term != DK_TERM]
    candidates = candidate_rows.assign(name=candidate_rows.player_id.map(names))
    candidates["coverage_status"] = [coverage_status(candidate, issued_keys, {row[2] for row in week["undrawn"]}, earlier_played, earlier_played_season, team_earlier_games, issue_week) for candidate in candidates.itertuples(index=False)]
    candidates["stats_issued"] = candidates.player_id.map(stat_summaries.groupby("key").size()).fillna(0).astype(int)
    participation_rows, participation_cells = week["participation"]
    candidates = candidates.merge(participation_rows[["player_id", "probability_plays", "probability_starts", "participation_status", "participation_cell", "games_missed", "snap_share_mean_season_pregame"]], on="player_id", how="left")
    candidates["participation_status"] = candidates.participation_status.where(candidates.participation_status.notna(), np.where(candidates.previous_label.isin(SKILL_POSITIONS), "NOT ISSUED - not a skill candidate of the participation frame", "NOT ISSUED - previous label " + candidates.previous_label.astype(str) + " is not a skill position"))
    law_fields = week_laws[["key", "term", "position", "layer", "provenance", "conditioned_on_draw"]]
    atlas = read_table(os.path.join(PROJ_DIR, "atlas.csv"))[["term", "position", "state", "rows", "qualification", "coverage_10", "coverage_90", "bias_mean"]].rename(columns={"rows": "atlas_rows", "qualification": "atlas_qualification", "coverage_10": "atlas_coverage_10", "coverage_90": "atlas_coverage_90", "bias_mean": "atlas_bias_mean"})
    ladder = read_table(os.path.join(PROJ_DIR, "ladder.csv"))[["term", "position", "state", "rows", "qualification"] + list(LADDER_FIELDS)].rename(columns={"rows": "ladder_rows", "qualification": "ladder_qualification", **LADDER_FIELDS})
    for name, table in (("atlas", atlas), ("ladder", ladder)):   # the judge is joined on (term, position, state): a state spelled differently in proj/{name}.csv than in the kit grades nothing, silently - refused by name instead
        if len(table) and not (table.state == LINK_CHAIN_STATE).any(): raise SystemExit(f"card {issue_season} w{issue_week}: proj/{name}.csv spells the state {sorted(table.state.unique())} and the kit spells it '{LINK_CHAIN_STATE}' - no line could be graded; refused, nothing issued (re-spell the {name} or the kit, then re-pin)")
    stat_rows = player_summaries.merge(law_fields, on=["key", "term", "position"], how="left").merge(atlas, on=["term", "position", "state"], how="left").merge(ladder, on=["term", "position", "state"], how="left")
    graded_cells = stat_rows.atlas_qualification.notna(); ladder_unmatched = int((graded_cells & stat_rows.ladder_rung.isna()).sum()); ladder_orphans = int((~graded_cells & stat_rows.ladder_rung.notna()).sum())
    ladder_disagree = int((graded_cells & stat_rows.ladder_rung.notna() & ((stat_rows.ladder_qualification != stat_rows.atlas_qualification) | (stat_rows.ladder_rows != stat_rows.atlas_rows))).sum())
    stat_rows["reference_status"] = reference_status(stat_rows.ladder_crpss.to_numpy(float)); stat_rows["prospective_evidence"] = stat_rows.prospective_evidence.fillna("NO LADDER CELL")
    stat_rows["provenance"] = stat_rows.provenance.where(stat_rows.term != F8_TERM, "F8 transform of the " + stat_rows.state + " order (dk)").where(stat_rows.term != DK_TERM, "F8 draws x the participation draw, DNP = 0 (dk.dnp_zero)")
    stat_rows["atlas_qualification"] = stat_rows.atlas_qualification.fillna("NO ATLAS CELL - not graded")
    missing = {"player_id", "position", "targets", "carries", "receiving_yards", "rushing_yards", "attempts"} - set(player_rows.columns)
    if missing: raise SystemExit(f"card {issue_season} w{issue_week}: player rows lack {sorted(missing)} - the EXCEL / STRUGGLE baseline cannot be read; refused, nothing issued")
    if "ladder_skill" not in stat_rows.columns: raise SystemExit(f"card {issue_season} w{issue_week}: no ladder_skill column - the judge's skill verdict cannot be read; refused, nothing issued")
    flags = excel_struggle(stat_rows, player_rows, issue_season, issue_week)
    judged = stat_rows.atlas_qualification.eq("DECISION-QUALIFIED") & stat_rows.ladder_skill.eq("PASS")
    flags["flag"] = flags.flag.where(judged | flags.flag.str.startswith("NOT RATED"), "NOT RATED - the judge has not qualified this line (atlas or ladder)")
    stat_rows = pd.concat([stat_rows, flags], axis=1)
    stat_rows = stat_rows.rename(columns={"key": "player_id", "family": "law_family", "state": "law_state"}).merge(candidates[["player_id", "name", "team", "probability_plays", "probability_starts", "participation_status"]], on="player_id", how="left")
    stat_rows["world"] = np.where((stat_rows.position == "QB") & stat_rows.probability_starts.notna(), stat_rows.team.astype(str) + ": " + stat_rows.name.astype(str) + " starts", ALL_WORLDS)
    stat_rows = stat_rows.assign(issuable="ISSUABLE", conditioning=np.where(stat_rows.term == DK_TERM, DNP_CONDITIONING, CONDITIONING), dependence_status=DEPENDENCE_STATUS, issue_mode=ISSUE_MODE, **engine_fields)
    columns = ["season", "week", "player_id", "name", "team", "position", "term", "law_family", "law_state", "layer", "provenance", "conditioned_on_draw", "center", "center_source", "draw_mean",
               "quantile_10", "quantile_25", "quantile_50", "quantile_75", "quantile_90", "issuable", "atlas_qualification", "atlas_rows", "atlas_coverage_10", "atlas_coverage_90", "atlas_bias_mean",
               *[field for field in LADDER_FIELDS.values() if field != "prospective_evidence"], "reference_status", "prospective_evidence", "conditioning", "probability_plays", "probability_starts", "world", "participation_status", "dependence_status", "issue_mode", *engine_fields.keys()]
    stat_rows = stat_rows[columns + FLAG_COLUMNS].sort_values(["team", "position", "player_id", "term"], kind="stable").reset_index(drop=True)
    candidate_columns = ["player_id", "name", "team", "position", "previous_label", "label_sequence", "coverage_status", "stats_issued", "probability_plays", "probability_starts", "participation_status", "participation_cell", "games_missed", "snap_share_mean_season_pregame"]
    dst_rows = summaries[summaries.position == "DST"].merge(week["dst"]["rows"][["team", "opponent"]], left_on="key", right_on="team", how="left").rename(columns={"key": "player_id", "family": "law_family", "state": "law_state"})
    dst_rows = dst_rows.assign(name=dst_rows.team + " DST", layer=np.nan, provenance="laws.dst_week (the earned yardstick, verdict in proj/dstick_report.txt)", conditioned_on_draw=np.nan, issuable="ISSUABLE",
                               atlas_qualification="NO ATLAS CELL - not graded", atlas_rows=np.nan, atlas_coverage_10=np.nan, atlas_coverage_90=np.nan, atlas_bias_mean=np.nan,
                               **{field: np.nan for field in LADDER_FIELDS.values() if field != "prospective_evidence"}, prospective_evidence="NO LADDER CELL", reference_status=reference_status(np.array([np.nan]))[0], conditioning=DST_CONDITIONING,
                               probability_plays=np.nan, probability_starts=np.nan, world=ALL_WORLDS, participation_status=DST_PARTICIPATION, dependence_status=DEPENDENCE_STATUS, issue_mode=ISSUE_MODE, **engine_fields)[columns + ["opponent"]].sort_values("team", kind="stable").reset_index(drop=True)
    card_path = os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}.csv"); candidates_path = os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}_candidates.csv"); dst_path = os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}_dst.csv")
    stat_rows.to_csv(card_path, index=False); candidates[candidate_columns].assign(issue_mode=ISSUE_MODE, **engine_fields).to_csv(candidates_path, index=False); dst_rows.to_csv(dst_path, index=False); frozen_path, frozen_sha = freeze_draws(week, issue_season, issue_week)
    status_counts = candidates.coverage_status.value_counts(); unexplained = int((candidates.coverage_status == "NOT ISSUED - unexplained").sum())
    issued_without_rows = int(((candidates.coverage_status == "ISSUED") & (candidates.stats_issued == 0)).sum()); orphan_rows = int((~stat_rows.player_id.isin(candidates.player_id)).sum())
    f8_missing = sorted(set(candidates[candidates.coverage_status == "ISSUED"].player_id) - set(stat_rows[stat_rows.term == F8_TERM].player_id)); dk_missing = sorted(set(stat_rows[stat_rows.term == F8_TERM].player_id) - set(stat_rows[stat_rows.term == DK_TERM].player_id))
    report.say(f"kit.py card {issue_season} w{issue_week} ({ISSUE_MODE}; {CONDITIONING}; participation T1 fit on seasons {participation_cells['seasons']}, {participation_cells['rows']} rows): candidates {len(candidates)}; stat rows {len(stat_rows)} for {len(issued_keys)} players")
    if root["root_source"] == "engine":
        report.say(f"   root: engine - {root['root_file']} SHA-256 {root['root_file_sha']}, source draws {root['root_source_draws']} -> {root['root_columns']} columns (column j = source j mod {root['root_source_draws']}); root center = the engine draws' mean; atlas and ladder columns are {GRADING_BASIS}")
        import json as _json; _json.dump(dict(issue=dict(season=issue_season, week=issue_week), **root, grading_basis=GRADING_BASIS), open(os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}_root.manifest.json"), "w"), indent=1)
    for status, count in status_counts.items(): report.say(f"   {status}: {count}")
    for status, count in candidates.participation_status.value_counts().items(): report.say(f"   participation {status}: {count}")
    issued_participation = candidates[candidates.coverage_status == "ISSUED"]
    report.say(f"   ISSUED stat candidates with P(plays) {int(issued_participation.probability_plays.notna().sum())} of {len(issued_participation)}; mean P(plays) {issued_participation.probability_plays.mean():.3f}")
    report.say("   stat rows by atlas qualification: " + "; ".join(f"{label} {count}" for label, count in stat_rows.atlas_qualification.value_counts().items()))
    report.say(f"   ATLAS (proj/atlas.csv): stat rows graded {int(graded_cells.sum())} of {len(stat_rows)} (state '{LINK_CHAIN_STATE}')")
    report.say("   EXCEL / STRUGGLE (against his own baseline): " + ", ".join(f"{k} {v}" for k, v in stat_rows.flag.str.split(" - ").str[0].value_counts().items()))
    report.say(f"   LADDER (proj/ladder.csv): graded stat rows without a ladder cell {ladder_unmatched}; ladder cells on ungraded rows {ladder_orphans}; rows whose ladder qualification or rows differ from the atlas {ladder_disagree}")
    report.say("   stat rows by trust rung: " + "; ".join(f"rung {int(rung)} {count}" for rung, count in stat_rows.ladder_rung.value_counts().sort_index().items()) + f"; no ladder cell {int(stat_rows.ladder_rung.isna().sum())}")
    report.say("   stat rows by reference status: " + "; ".join(f"{label.split(' - ')[0]} {count}" for label, count in stat_rows.reference_status.value_counts().items()))
    for cell in stat_rows[stat_rows.reference_status.str.startswith("REFERENCE CURRENTLY PREFERRED")].groupby(["term", "position", "law_state"]).agg(rows=("player_id", "size"), crpss=("ladder_crpss", "first")).reset_index().itertuples(index=False):
        report.say(f"      REFERENCE CURRENTLY PREFERRED: {cell.term} {cell.position} {cell.law_state} - stat rows {cell.rows}, ladder CRPSS {cell.crpss:+.3f}")
    report.say(f"   F8 rows {int((stat_rows.term == F8_TERM).sum())}; issued candidates without F8 {len(f8_missing)}" + (f" ({', '.join(f8_missing[:8])})" if f8_missing else ""))
    report.say(f"   DK rows (DNP = 0) {int((stat_rows.term == DK_TERM).sum())}; F8 rows without a DK row {len(dk_missing)};  DST rows {len(dst_rows)}, DST without a law {len(week['dst']['without'])}" + "".join(f"; {team} NOT ISSUED - {reason}" for team, reason in week["dst"]["without"].itertuples(index=False)))
    for reason, count in pd.Series([row[5] for row in week["undrawn"]], dtype=object).value_counts().items(): report.say(f"   law rows that drew nothing: {reason} {count}")
    for position in ("QB", "RB", "WR", "TE"):
        example = stat_rows[stat_rows.position == position].player_id.head(1).tolist()
        if not example: continue
        report.say(f"\n   example {position}: {stat_rows[stat_rows.player_id == example[0]].name.iloc[0]} ({example[0]}, {stat_rows[stat_rows.player_id == example[0]].team.iloc[0]}); P(plays) {stat_rows[stat_rows.player_id == example[0]].probability_plays.iloc[0]:.3f} - {stat_rows[stat_rows.player_id == example[0]].participation_status.iloc[0]}")
        for row in stat_rows[stat_rows.player_id == example[0]].itertuples(index=False):
            report.say(f"      {row.term:<18} center {row.center:8.2f}  P10 {row.quantile_10:7.1f}  P50 {row.quantile_50:7.1f}  P90 {row.quantile_90:7.1f}  {row.law_family} / {row.law_state}  -> {row.atlas_qualification}; rung {row.ladder_rung}; {row.reference_status.split(' - ')[0]}")
    participation_unmatched = int(candidates.participation_status.str.startswith("NOT ISSUED - not a skill candidate").sum())
    accepted = ladder_unmatched == 0 and ladder_orphans == 0 and ladder_disagree == 0 and len(dk_missing) == 0 and participation_unmatched == 0 and unexplained == 0 and issued_without_rows == 0 and orphan_rows == 0 and int(status_counts.sum()) == len(candidates) and not candidates.player_id.duplicated().any()
    report.say(f"\nCHECK: every candidate exactly once {not candidates.player_id.duplicated().any()}; statuses sum to candidates {int(status_counts.sum()) == len(candidates)}; unexplained {unexplained}; issued without stat rows {issued_without_rows}; stat rows without a candidate {orphan_rows}; candidates without a participation row {participation_unmatched}; F8 rows without a DK row {len(dk_missing)}; ladder unmatched / orphans / disagreeing {ladder_unmatched} / {ladder_orphans} / {ladder_disagree}")
    report.say(("CARD ACCEPTED" if accepted else "CARD REFUSED") + f" - wrote {card_path}, {candidates_path}, {dst_path}, {frozen_path} (SHA-256 {frozen_sha})" + (f"; root engine {root['root_file']} {root['root_file_sha']}" if root["root_source"] == "engine" else ""))
    report.write(os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}_report.txt")); return 0 if accepted else 1
