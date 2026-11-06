"""optimize.py - lineups (Slate Kit module map: optimize; M10).  Reads the price file (facts' door), the card and the frozen draws only; recomputes no forecast;
price is used here and nowhere upstream.  best9: the exact dynamic program over DraftKings NFL Classic slots (1 QB, 2-3 RB, 3-4 WR, 1-2 TE - 7 skill players including
FLEX - and 1 DST) under the salary cap; returns the chosen row indices.
BASE (kit.py base SEASON WEEK): the legal lineup with the largest expected DK total.  Expected DK points have one definition for every row: the mean of its frozen
draws (a player's DK draws, DNP = 0; a defense's DST draws) - the card's draw_mean, never a law center (M10b).  An expected total is a sum of means, so BASE does not depend on cross-player dependence (it ships before M9); FLOOR and CEILING do.
Stability reading per lineup player: re-solve without him; the expected gap (BASE expected total - alternative expected total) is MATERIAL iff it exceeds 1 DK
(the kit's materiality unit, CHARTER AT END-TO-END), else IMMATERIAL.  A lineup total's spread is not reported: it needs cross-player dependence (M9)."""
import os, numpy as np, pandas as pd
from ingest import PROJ_DIR, Report
from facts import price_file, read_table, norm
from dk import DK_TERM, DST_TERM
from market import card_rows
salary_cap, UNIT = 50000, 100
position_axis = {"RB": 0, "WR": 1, "TE": 2, "QB": 3, "DST": 4}
MAXC = (3, 4, 2, 1, 1)
def surname_key(names): return names.astype(str).str.lower().str.replace(r"[^a-z ]", "", regex=True).str.replace(r"\s+(jr|sr|ii|iii|iv|v)$", "", regex=True).str.split().str[-1]   # the last name token of facts.norm's spelling
def best9(position, salaries, score):
    """exact DP: 1 QB, 2-3 RB, 3-4 WR, 1-2 TE (7 skill incl. FLEX), 1 DST, salary <= CAP. returns indices."""
    cap_units = salary_cap // UNIT
    shape = tuple(max_count + 1 for max_count in MAXC) + (cap_units + 1,)
    best_values = np.full(shape, -np.inf); best_values[0, 0, 0, 0, 0, 0] = 0.0
    back = []
    for row_number in np.where(np.isfinite(score))[0]:
        axis_number = position_axis[position[row_number]]; cost_units = int(round(salaries[row_number] / UNIT)); player_score = score[row_number]
        source_slices = [slice(None)] * 6; target_slices = [slice(None)] * 6
        source_slices[axis_number] = slice(0, shape[axis_number] - 1); target_slices[axis_number] = slice(1, shape[axis_number])
        source_slices[5] = slice(0, cap_units + 1 - cost_units); target_slices[5] = slice(cost_units, cap_units + 1)
        cand = best_values[tuple(source_slices)] + player_score; current_values = best_values[tuple(target_slices)]
        improved = cand > current_values
        if improved.any():
            best_values = best_values.copy(); destination = best_values[tuple(target_slices)]; destination[improved] = cand[improved]; best_values[tuple(target_slices)] = destination
        back.append((row_number, axis_number, cost_units, improved))
    best, best_state = -np.inf, None
    for rb_count in range(2, 4):
        for wr_count in range(3, 5):
            for te_count in range(1, 3):
                if rb_count + wr_count + te_count != 7: continue
                s = int(np.argmax(best_values[rb_count, wr_count, te_count, 1, 1])); state_value = best_values[rb_count, wr_count, te_count, 1, 1, s]
                if state_value > best: best, best_state = state_value, [rb_count, wr_count, te_count, 1, 1, s]
    if best_state is None: return []
    state = best_state; chosen = []
    for (row_number, axis_number, cost_units, improved) in reversed(back):
        state_cursor = list(state); state_cursor[axis_number] -= 1; state_cursor[5] -= cost_units
        if state_cursor[axis_number] < 0 or state_cursor[5] < 0: continue
        if improved[tuple(state_cursor)]: chosen.append(row_number); state = state_cursor
    return chosen
MATERIALITY_DK = 1.0
BASE_STATUS = "ISSUABLE - NOT DECISION-QUALIFIED (DK draws have no atlas cell; participation NOT DECISION-QUALIFIED); DRY RUN - not prospective"
def slate_pool(issue_season, issue_week):
    """Every row of week N's price file with its expected DK points (the mean of its frozen draws) and eligibility: a skill row joins the card candidate with the same name key and team;
    a row left unmatched joins a candidate left unmatched with the same surname key, team and position when that pairing is one on each side (DraftKings and the
    play-by-play spell first names differently - Matt / Matthew); the match column names which.  A matched skill row is
    ELIGIBLE iff that candidate is ISSUED with a DK row; a DST row is ELIGIBLE iff its team has a DST law.  Every other row carries the reason."""
    prices = price_file(issue_season, issue_week); card = card_rows(issue_season, issue_week)
    candidates = read_table(os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}_candidates.csv")); candidates["name_key"] = norm(candidates.name)
    expected = card[card.term.isin([DK_TERM, DST_TERM])][["player_id", "term", "draw_mean"]].rename(columns={"player_id": "key", "draw_mean": "expected_points"})
    skill_rows = prices[prices.dk_position != "DST"].merge(candidates[["player_id", "name_key", "team", "coverage_status"]], on=["name_key", "team"], how="left")
    skill_rows["match"] = np.where(skill_rows.player_id.notna(), "name and team", "none")
    open_prices = skill_rows[skill_rows.player_id.isna()].assign(surname=lambda frame: surname_key(frame.dk_name))
    open_candidates = candidates[~candidates.player_id.isin(skill_rows.player_id)].assign(surname=lambda frame: surname_key(frame.name))
    one_price = open_prices.groupby(["surname", "team", "dk_position"]).dk_id.transform("size") == 1; one_candidate = open_candidates.groupby(["surname", "team", "position"]).player_id.transform("size") == 1
    pairs = open_prices[one_price].reset_index().merge(open_candidates[one_candidate][["player_id", "surname", "team", "position", "coverage_status"]], left_on=["surname", "team", "dk_position"], right_on=["surname", "team", "position"], suffixes=("_unmatched", ""))
    skill_rows.loc[pairs["index"].values, ["player_id", "coverage_status"]] = pairs[["player_id", "coverage_status"]].values; skill_rows.loc[pairs["index"].values, "match"] = "surname, team and position, one on each side"
    skill_rows = skill_rows.assign(key=skill_rows.player_id, term=DK_TERM); dst_rows = prices[prices.dk_position == "DST"].assign(key=lambda frame: frame.team, term=DST_TERM, coverage_status="DST", match="team")
    pool = pd.concat([skill_rows, dst_rows], ignore_index=True).merge(expected, on=["key", "term"], how="left")
    ambiguous = pool.dk_id.duplicated(keep=False) | (pool.key.notna() & pool.duplicated(["key", "term"], keep=False))
    pool["eligibility"] = np.select([ambiguous, (pool.term == DK_TERM) & pool.player_id.isna(), (pool.term == DK_TERM) & (pool.coverage_status != "ISSUED"), pool.expected_points.isna()],
                                    ["NOT ELIGIBLE - name and team match more than one row", "NOT ELIGIBLE - no card candidate with this name and team", "NOT ELIGIBLE - candidate " + pool.coverage_status.astype(str),
                                     np.where(pool.term == DST_TERM, "NOT ELIGIBLE - no DST law", "NOT ELIGIBLE - no DK draw (participation NOT ISSUED)")], "ELIGIBLE")
    return pool.drop_duplicates("dk_id").reset_index(drop=True), candidates
def legal(lineup_rows):
    """DraftKings NFL Classic: 9 distinct players, 1 QB, 1 DST, 2-3 RB, 3-4 WR, 1-2 TE (7 skill), salary <= cap, players from 2+ games."""
    counts = lineup_rows.dk_position.value_counts()
    return (len(lineup_rows) == 9 and lineup_rows.dk_id.nunique() == 9 and counts.get("QB", 0) == 1 and counts.get("DST", 0) == 1 and 2 <= counts.get("RB", 0) <= 3 and 3 <= counts.get("WR", 0) <= 4
            and 1 <= counts.get("TE", 0) <= 2 and counts.get("RB", 0) + counts.get("WR", 0) + counts.get("TE", 0) == 7 and int(lineup_rows.salary.sum()) <= salary_cap and lineup_rows.game.nunique() >= 2)
def slots(lineup_rows):
    """Slot labels: the surplus RB / WR / TE with the smallest expected points is FLEX."""
    lineup_rows = lineup_rows.assign(slot=lineup_rows.dk_position.values); minimum = {"RB": 2, "WR": 3, "TE": 1}
    surplus = [position for position in minimum if int((lineup_rows.dk_position == position).sum()) > minimum[position]]
    if surplus: lineup_rows.loc[lineup_rows[lineup_rows.dk_position == surplus[0]].sort_values("expected_points", kind="stable").index[0], "slot"] = "FLEX"
    return lineup_rows.assign(slot_order=lineup_rows.slot.map({"QB": 0, "RB": 1, "WR": 2, "TE": 3, "FLEX": 4, "DST": 5})).sort_values(["slot_order", "expected_points"], ascending=[True, False]).drop(columns="slot_order")
def base(issue_season, issue_week):
    """python3 kit.py base SEASON WEEK: the BASE lineup from week N's price file and card -> proj/slate_pool_*.csv, proj/lineup_base_*.csv."""
    report = Report(); pool, candidates = slate_pool(issue_season, issue_week)
    scores = np.where(pool.eligibility == "ELIGIBLE", pool.expected_points, -np.inf); chosen = best9(pool.dk_position.values, pool.salary.values, scores)
    lineup_rows = pool.iloc[chosen]; lineup_legal = legal(lineup_rows); base_expected = float(lineup_rows.expected_points.sum())
    slate_teams = set(pool.team); issued_unpriced = candidates[(candidates.coverage_status == "ISSUED") & candidates.team.isin(slate_teams) & ~candidates.player_id.isin(pool.player_id)]
    report.say(f"kit.py base {issue_season} w{issue_week} ({BASE_STATUS}): price file rows {len(pool)}, games {pool.game.nunique()}, teams {len(slate_teams)}")
    for (position, eligibility), count in pool.groupby(["dk_position", "eligibility"]).size().items(): report.say(f"   {position:<3} {eligibility}: {count}")
    surname_matches = pool[pool.match == "surname, team and position, one on each side"]; candidate_names = dict(zip(candidates.player_id, candidates.name))
    report.say(f"   matched by surname, team and position (one on each side): {len(surname_matches)}" + ("" if surname_matches.empty else " (" + ", ".join(f"{row.dk_name} = {candidate_names[row.player_id]} {row.team} {row.dk_position}" for row in surname_matches.itertuples(index=False)) + ")"))
    report.say(f"   ISSUED candidates on slate teams without a price row: {len(issued_unpriced)}" + ("" if issued_unpriced.empty else " (" + ", ".join(f"{row.name} {row.team}" for row in issued_unpriced.itertuples(index=False)) + ")"))
    report.say(f"\nBASE LINEUP (expected DK points = mean of the frozen DK / DST draws):")
    for row in slots(lineup_rows).itertuples(index=False): report.say(f"   {row.slot:<4} {row.dk_name:<26} {row.team:<4} {row.game:<8} ${int(row.salary):>5}  E[DK] {row.expected_points:6.2f}")
    report.say(f"   SALARY ${int(lineup_rows.salary.sum()):,}   E[DK] {base_expected:.2f}   games {lineup_rows.game.nunique()}   (a lineup total's spread needs cross-player dependence: M9)")
    report.say(f"\nSTABILITY (re-solve without each lineup player; expected gap vs BASE; MATERIAL iff the gap > {MATERIALITY_DK:.0f} DK):"); alternative_better = 0
    for row_number in chosen:
        masked = scores.copy(); masked[row_number] = -np.inf; alternative_rows = pool.iloc[best9(pool.dk_position.values, pool.salary.values, masked)]
        if not legal(alternative_rows): report.say(f"   without {pool.dk_name.iloc[row_number]}: no legal alternative"); continue
        gap = base_expected - float(alternative_rows.expected_points.sum()); alternative_better += int(gap < 0)
        report.say(f"   without {pool.dk_name.iloc[row_number]:<26} gap {gap:6.2f} -> {'MATERIAL' if gap > MATERIALITY_DK else 'IMMATERIAL'}  (adds {', '.join(alternative_rows[~alternative_rows.dk_id.isin(lineup_rows.dk_id)].dk_name)})")
    reasons_complete = bool(pool.eligibility.notna().all()); accepted = lineup_legal and reasons_complete and alternative_better == 0
    report.say(f"\nCHECK: lineup legal {lineup_legal}; every price row with one eligibility {reasons_complete}; alternatives better than BASE {alternative_better}")
    pool.to_csv(os.path.join(PROJ_DIR, f"slate_pool_{issue_season}_w{issue_week}.csv"), index=False); slots(lineup_rows).assign(base_status=BASE_STATUS).to_csv(os.path.join(PROJ_DIR, f"lineup_base_{issue_season}_w{issue_week}.csv"), index=False)
    report.say(("M10 BASE ACCEPTED" if accepted else "M10 BASE REFUSED") + f" - wrote proj/slate_pool_{issue_season}_w{issue_week}.csv, proj/lineup_base_{issue_season}_w{issue_week}.csv")
    report.write(os.path.join(PROJ_DIR, f"lineup_base_{issue_season}_w{issue_week}_report.txt")); return 0 if accepted else 1
