"""market.py - the market (Slate Kit module map: market; M7).  P(over / under / push) at an entered line, after freeze: the share of week N's frozen draws
(proj/frozen_draws_{SEASON}_w{WEEK}.npz, written with the card) above, below and at the line, under a declared settlement.  Market last: it reads the card and the
frozen draws and feeds nothing upstream; the line is entered, never read from an odds file.
SETTLEMENTS   void  the market voids the prop when he does not play: P(Y | plays), with P(plays) shown beside it.
              zero  the market settles a non-participant at zero: (1 - P(plays)) x atom at 0 + P(plays) x P(Y | plays).
A probability is DECISION-QUALIFIED only when its stat's atlas cell is DECISION-QUALIFIED and, under zero, its participation status is ISSUED - DECISION-QUALIFIED
(participation issues no such status today: T1 is NOT DECISION-QUALIFIED).  Otherwise the number is shown with its UNRESOLVED label and the reason.
A row's card conditioning decides how a settlement applies: given he plays (stats, F8) - void or zero as above; DNP = 0 (DK) - the draws already settle a
non-participant at 0, so only zero applies; the defense plays every game (DST) - the settlement does not change the probabilities."""
import os, numpy as np, pandas as pd
from ingest import PROJ_DIR, Report
from facts import read_table
from draws import week_draws, player_draw_matrix, frozen_draws_path, QUANTILE_LEVELS, QUANTILE_NAMES
from cards import CONDITIONING, DNP_CONDITIONING, DST_CONDITIONING
SETTLEMENTS = {"void": "the market voids the prop when he does not play: P(Y | plays), P(plays) beside it",
               "zero": "the market settles a non-participant at zero: (1 - P(plays)) x atom at 0 + P(plays) x P(Y | plays)"}
def frozen_draws(issue_season, issue_week):
    """Week N's frozen player draw matrix, as written."""
    with np.load(frozen_draws_path(issue_season, issue_week), allow_pickle=False) as frozen: return {name: frozen[name] for name in frozen.files}
def card_rows(issue_season, issue_week):
    """Week N's card rows, as written: the player card's stat, F8 and DK rows and the DST card's rows."""
    return pd.concat([read_table(os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}.csv")), read_table(os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}_dst.csv"))], ignore_index=True)
def line_probabilities(draw_values, line):
    """P(over), P(under), P(push) given he plays: the shares of the draws above, below and equal to the line."""
    return float(np.mean(draw_values > line)), float(np.mean(draw_values < line)), float(np.mean(draw_values == line))
def settled(given_plays, line, probability_plays, settlement):
    """The settled (over, under, push) under a settlement; under zero a non-participant's 0 is over, under or a push against the line."""
    if settlement == "void": return given_plays
    zero_outcome = (float(0 > line), float(0 < line), float(0 == line))
    return tuple((1 - probability_plays) * zero_value + probability_plays * given_value for zero_value, given_value in zip(zero_outcome, given_plays))
def settlement_applies(conditioning, settlement):
    """Void does not apply to DNP = 0 draws (they already settle a non-participant at 0); every other pairing applies."""
    return not (conditioning == DNP_CONDITIONING and settlement == "void")
def row_probabilities(row, draw_values, line, settlement):
    """(over, under, push) of one card row under a settlement, by its conditioning; None when the settlement does not apply to the row."""
    if not settlement_applies(row.conditioning, settlement): return None
    as_drawn = line_probabilities(draw_values, line)
    return settled(as_drawn, line, row.probability_plays, settlement) if row.conditioning == CONDITIONING else as_drawn
def decision_status(atlas_qualification, participation_status, settlement, conditioning):
    if atlas_qualification != "DECISION-QUALIFIED": return f"UNRESOLVED - stat {atlas_qualification}"
    if conditioning != DST_CONDITIONING and settlement == "zero" and participation_status != "ISSUED - DECISION-QUALIFIED": return f"UNRESOLVED - participation {participation_status}"
    return "DECISION-QUALIFIED"
def frozen_index(frozen):
    return {(key, term): row_number for row_number, (key, term) in enumerate(zip(frozen["keys"], frozen["terms"]))}
def prop(issue_season, issue_week, player_id, term, line, settlement):
    """python3 kit.py market SEASON WEEK PLAYER_ID "TERM" LINE void|zero"""
    if settlement not in SETTLEMENTS: print(f"settlement must be one of {sorted(SETTLEMENTS)}"); return 2
    frozen = frozen_draws(issue_season, issue_week); index = frozen_index(frozen); stat_rows = card_rows(issue_season, issue_week)
    matching = stat_rows[(stat_rows.player_id == player_id) & (stat_rows.term == term)]
    if matching.empty:
        candidates = read_table(os.path.join(PROJ_DIR, f"card_{issue_season}_w{issue_week}_candidates.csv")); candidate = candidates[candidates.player_id == player_id]
        print(f"{player_id} {term}: NOT ISSUED - " + (f"no card stat row; candidate status {candidate.coverage_status.iloc[0]}" if len(candidate) else "not a candidate of this week")); return 1
    row = matching.iloc[0]; draw_values = frozen["draws"][index[(player_id, term)]]; probabilities = row_probabilities(row, draw_values, line, settlement)
    if probabilities is None: print(f"{row['name']} ({player_id}) {term}: these draws already settle a non-participant at 0 ({row.conditioning}); use zero, or query F8 dk_points for void"); return 2
    over, under, push = probabilities; as_drawn = line_probabilities(draw_values, line)
    print(f"{row['name']} ({player_id}, {row.team} {row.position}) {term} line {line} - {settlement}: {SETTLEMENTS[settlement]}; card conditioning: {row.conditioning}")
    print(f"   P(over) {over:.4f}  P(under) {under:.4f}  P(push) {push:.4f}   as drawn: over {as_drawn[0]:.4f} under {as_drawn[1]:.4f} push {as_drawn[2]:.4f};  P(plays) {row.probability_plays:.4f}")
    print(f"   {decision_status(row.atlas_qualification, row.participation_status, settlement, row.conditioning)};  draws {frozen['draws'].shape[1]} frozen, center {row.center:.2f}, P10 {row.quantile_10:.1f}, P90 {row.quantile_90:.1f}; {row.issue_mode}")
    return 0
def market_check(issue_season, issue_week):
    """python3 kit.py market-check SEASON WEEK: M7 acceptance (with M8b's DK and DST rows).  W1 the frozen draws are the card's: one frozen row per card stat row, each row's draw mean and
    quantiles equal to the card's exactly; W2 the frozen file reproduces from the issue path (week_draws rerun, keys, terms and every draw equal; DK and DST rows
    included).  The probability identities (shares of a partition sum to 1; zero at P(plays) 1 is void) hold by definition and are not tested."""
    report = Report(); frozen = frozen_draws(issue_season, issue_week); index = frozen_index(frozen); stat_rows = card_rows(issue_season, issue_week)
    card_keys = set(zip(stat_rows.player_id, stat_rows.term)); unpaired = len(card_keys ^ set(index)); summary_differ = 0
    for row in stat_rows.itertuples(index=False):
        draw_values = frozen["draws"][index[(row.player_id, row.term)]]
        summary_differ += int(float(draw_values.mean()) != row.draw_mean) + int(sum(float(value) != getattr(row, name) for value, name in zip(np.quantile(draw_values, QUANTILE_LEVELS), QUANTILE_NAMES)))
    first_passed = unpaired == 0 and summary_differ == 0 and len(stat_rows) == len(frozen["keys"])
    report.say(f"kit.py market-check {issue_season} w{issue_week} (M7): frozen rows {len(frozen['keys'])} x {frozen['draws'].shape[1]} draws; card stat rows {len(stat_rows)}")
    report.say(f"   W1 frozen = card: unpaired {unpaired}; draw means and quantiles differing {summary_differ} of {len(stat_rows) * 6} -> {'PASS' if first_passed else 'FAIL'}")
    reissued = player_draw_matrix(week_draws(issue_season, issue_week))
    second_passed = all(np.array_equal(frozen[name], reissued[name]) for name in ("keys", "terms", "positions", "draws"))
    report.say(f"   W2 reproduction from the issue path: keys, terms, positions and {reissued['draws'].size} draws equal -> {'PASS' if second_passed else 'FAIL'}")
    status_counts = {}
    for row in stat_rows.itertuples(index=False):
        for settlement in [settlement for settlement in SETTLEMENTS if settlement_applies(row.conditioning, settlement)]:
            label = row.conditioning.split(":")[0] + " | " + decision_status(row.atlas_qualification, row.participation_status, settlement, row.conditioning).split(" (")[0]; status_counts[(settlement, label)] = status_counts.get((settlement, label), 0) + 1
    report.say("   decision status by settlement (a reading):")
    for (settlement, label), count in sorted(status_counts.items()): report.say(f"      {settlement:<4} {label}: {count}")
    accepted = first_passed and second_passed
    report.say("\nM7 MARKET " + ("ACCEPTED - every query reads the frozen draws, which are the card's and reproduce from the issue path" if accepted else "REFUSED"))
    report.write(os.path.join(PROJ_DIR, f"market_check_{issue_season}_w{issue_week}_report.txt")); return 0 if accepted else 1
