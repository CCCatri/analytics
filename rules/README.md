# rules/ — the rule books the product reads, pinned

The NFL rulebooks by season (`nfl_rulebook_2020.pdf` … `nfl_rulebook_2026.pdf`, `nfl_rulebook_2025.html`). `product/rules.py` reads the 2026 book (sha `144cec5bffd2`) for the next-down rule's exceptions and reads each season's rule from that season's book through `RULE_PINS.json`, which pins every file's sha; `product/measure_season_rules.py` writes the measured values to `out/season_rules.csv`. A changed book is refused by the pin. `play_clock_pins.tsv` and `warning_pins.tsv` hold line-level pins for the clock clauses.

These are the NFL's documents, kept here so the pins resolve; they are not this project's work.
