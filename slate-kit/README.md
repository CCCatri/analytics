# slate-kit/ — the player-projection component

Modules: `ingest.py` (fetch and pin raw files), `facts.py` (the derived tables in `facts/`), `state.py` (information set before week N), `participation.py` (P(plays)), `chain.py` and `draws.py` (the opportunity ladder and its draws; `draws.py` holds the engine-root adapter, `SLATE_ROOT_SOURCE` unset/kit/engine), `cards.py` (the issued card), `dk.py` and `market.py` (DK DFS scoring and prices), `evaluate.py` (grading, freezes, the CHARTER ledger), `optimize.py` (lineups), `kit.py` (the command line).

`CHARTER.md` is the kit's append-only working ledger — 6,800 lines of rulings and results — checked by `evaluate.py` against a digest in `proj/charter_ledger.json`; it is product, not reading material. `TAXONOMY.md` is its vocabulary. `facts/` holds the tables built from nflverse releases (origins in `checks/fixtures/demo_w15/ORIGINS.md`); `prices/` the one DK salary file. `data/`, `proj/` and `sources/` are local state and not tracked.
