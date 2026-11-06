"""kit.py - the Slate Kit command: a composition of the modules; it owns no concept.
Usage: python3 kit.py COMMAND [ARGS]
  draws SEASON WEEK                                   draws: week N drawn from the one chain, frozen draws written (DRY RUN)
  replay PREVIOUS_ATLAS_ROWS                          draws: the one replay and the one product judgment against the previous product's graded rows
  fetch SEASON WEEK [--dk-group ID] [--no-nflverse]   ingest: the one fetcher (also --check-dk CSV JSON, --odds-lines, --odds-history, --sources FAMILIES, --corpus once ever)
  accept                                              ingest: the raw manifest accepts every raw file now on disk
  facts                                               facts: rebuild facts/ from the raw files
  guard                                               every check: raw manifest, raw readers, kit modules, one definition, facts' independent check, facts freshness,
                                                      information set, lockbox seal, CHARTER ledger, purity
  purity                                              state: non-anticipation of windows and participation inputs
  participation-check                                 participation: M5 acceptance - T1 against at_rows, at_t_rows and t1_cells.json, and non-anticipation
  card SEASON WEEK                                    cards: the Player Forecast card (given he plays, with P(plays) beside it) for every candidate -> proj/card_SEASON_wWEEK*.csv
  market SEASON WEEK PLAYER_ID "TERM" LINE void|zero    market: P(over / under / push) at an entered line from the frozen draws, under the declared settlement
  market-check SEASON WEEK                            market: M7 acceptance - frozen draws are the card's and reproduce from the issue path; probability laws
  base SEASON WEEK                                    optimize: M10 BASE lineup from the price file, card and frozen draws -> proj/lineup_base_SEASON_wWEEK.csv
  ledger-check                                        evaluate: the CHARTER ledger check alone
  harness MODE                                        evaluate: spine | f6 | dependence | invariance | exact
  f7                                                  evaluate: F7 self-checks
  ledger-advance                                      kit: the guard, then (only if it passes) the CHARTER ledger accepts the CHARTER's new lines
  same FIRST SECOND                                   evaluate: decompressed content of two files, byte for byte
  freeze NAME SEASON WEEK                             evaluate: week N's product files -> proj/frozen/NAME/ with content digests, kit digest, CHARTER version, UTC time (never rewritten)
  witness-check NAME [FILE ...]                       evaluate: the product files now against proj/frozen/NAME/; only the declared FILEs may differ"""
import glob, os, sys, time
from datetime import datetime, timezone
import ingest, facts, state, participation, evaluate, draws, cards, market, optimize
MODULES = ["ingest", "facts", "state", "participation", "evaluate", "dk", "chain", "draws", "cards", "market", "optimize"]   # the kit, bottom to top: each module imports only modules before it
def guard():
    paths = [str(ingest.ROOT / f"{name}.py") for name in MODULES + ["kit"]]
    checks = [ingest.raw_manifest_check(), ingest.raw_reader_check(paths), evaluate.kit_modules_check(), evaluate.one_definition_check(), evaluate.name_resolution_check(), evaluate.kit_size(), facts.independent_check(),
              facts.freshness_check(), facts.information_set_check(paths), facts.lockbox_check(paths), evaluate.ledger_check()]
    for passed, message in checks: print(("ok    " if passed else "FAIL  ") + message)
    purity_code = state.purity(); failures = sum(not passed for passed, message in checks) + (purity_code != 0)
    print(f"\n{'GUARD PASSED' if failures == 0 else f'GUARD FAILED: {failures} problem(s)'}"); return 0 if failures == 0 else 1
def advance():
    """The ledger accepts the CHARTER's new lines only after the guard passes (the guard runs here; a failing guard refuses the advance)."""
    if guard() != 0: print("ledger-advance refused: the guard failed - the CHARTER's new lines stay unaccepted"); return 1
    return evaluate.ledger_advance()
COMMANDS = {"fetch": lambda argv: ingest.fetch_command(argv),
            "accept": lambda argv: ingest.accept(),
            "facts": lambda argv: facts.build(),
            "guard": lambda argv: guard(),
            "purity": lambda argv: state.purity(),
            "card": lambda argv: cards.card(int(argv[0]), int(argv[1])),
            "participation-check": lambda argv: participation.participation_check(),
            "market": lambda argv: market.prop(int(argv[0]), int(argv[1]), argv[2], argv[3], float(argv[4]), argv[5]),
            "market-check": lambda argv: market.market_check(int(argv[0]), int(argv[1])),
            "base": lambda argv: optimize.base(int(argv[0]), int(argv[1])),
            "ledger-check": lambda argv: evaluate.ledger_command(),
            "harness": lambda argv: evaluate.harness(argv[0]),
            "f7": lambda argv: evaluate.f7_check(),
            "ledger-advance": lambda argv: advance(),
            "same": lambda argv: evaluate.same_content(argv[0], argv[1]),
            "freeze": lambda argv: evaluate.freeze(argv[0], int(argv[1]), int(argv[2])),
            "witness-check": lambda argv: evaluate.witness_check(argv[0], argv[1:]),
            "draws": lambda argv: draws.draw_issue(int(argv[0]), int(argv[1])),
            "replay": lambda argv: draws.replay(*argv)}
def main(argv):
    """Run one command and record what it did: the time, the command, its exit (0 accepted), the kit's code digest, the accepted raw manifest before and after, and
    the content digest of every file it wrote under proj/ and facts/ - the event later commands read instead of trusting a script's order."""
    if not argv or argv[0] not in COMMANDS: print(__doc__); return 2
    started = time.time(); kit_digest, manifest_before = evaluate.kit_sha(), ingest.manifest_sha()
    try: exit_code = COMMANDS[argv[0]](argv[1:])
    except SystemExit as stop:
        if not isinstance(stop.code, int): print(stop.code)
        exit_code = stop.code if isinstance(stop.code, int) else 1
    written = [path for folder in (ingest.PROJ_DIR, ingest.FACTS_DIR) for path in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
               if os.path.isfile(path) and os.path.getmtime(path) >= started and os.path.abspath(path) != os.path.abspath(ingest.EVENT_LOG)]
    ingest.record_event(dict(time=datetime.now(timezone.utc).isoformat(), command=argv, exit=int(exit_code), kit_sha=kit_digest, raw_manifest_before=manifest_before,
                             raw_manifest=ingest.manifest_sha(), outputs={os.path.relpath(path, ingest.ROOT): evaluate.content_sha(path) for path in sorted(written)}))
    return exit_code
sys.exit(main(sys.argv[1:]))
