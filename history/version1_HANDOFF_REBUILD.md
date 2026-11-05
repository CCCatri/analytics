# HANDOFF: REBUILD THE ACCEPTED PRODUCT, ONCE, FROM ITS LAWS
Scope: the product only (the engine that draws every slate member's stats). The check, the grader and the record are not
rebuilt; they are reused verbatim and they are what accepts the rebuild. Read the old code only to learn what a piece is for.
Write from the law. Delete the old body in the same acceptance.

## 0. THE BAN
Nothing in the rebuilt product decides by rule what the NFL record could tell it. No default, threshold, roster, chosen column,
chosen window, chosen count, chosen order, chosen fallback, chosen stopping point. Every number is one of exactly three things:
  (a) a whole number read from the NFL's own record (a play, a yard, a point, a player on a list), or a ratio of two such counts;
  (b) a value the record determines by likelihood or by a chance test, on seasons before the one being forecast, printed with
      what it was fit on and its value at the ends of its range;
  (c) the check's own printed level (its significance level, its SE multiple), owned by the check, never by the product.
Anything else is a DataGap. On meeting one, the thread prints `DataGap: <what the product needs to know> <where the record could say it>`
and stops that piece. The reviewer answers GAPs; the thread never fills one. A label is a claim: before any name, rank, role, position
or kind is used, its derivation from the record is printed. Nothing is inferred, normalised, scaled or mutated. Only the NFL's
record is reality. 2022, data/discovery, data/held out and data/held_2026 are not read.

## 1. WHAT EXISTS AND IS REUSED (hashes as the record holds them at handoff; print and match before anything)
  .revision stage/revision stage.py           the grader and the only writer of the record (RULE 13b).        reuse verbatim
  check/criterion.py the check: 51 slices, slice_rows.csv per player-season.      reuse verbatim; `time` first
  scratch/probe_624.py    the scorecard: 17 position x stat cells vs B1, held out.       reuse verbatim; run once per acceptance
  door.py                 the one producer of lists, labels, participation, facts.       reuse; every read of the record goes through it
  GOAL_LADDER.md          the loop; every turn names its rung.
  The accepted product (draws.py and whatever else the bindings' `product` globs name) at its accepted hash: the thing being rebuilt.

## 2. THE CLAIM THE PRODUCT SERVES
For every active player in this week's game, worlds of his stats such that P(stat > his season-to-date average) is calibrated
held out and beats B1. The product does not compute that probability; it draws worlds. The check reads them.

## 3. THE LAWS (what the accepted product conserves and measures; the rebuild must hold each one by construction)
the game level  THE GAME. A world is one real game, played earlier, drawn whole: both sides, its plays, its points. The slate team stands on
    the side it played, else the side its opponent decides, else as the record's home/away says. The world's volume (passes thrown,
    sacks, runs) is that game's, play by play. Which earlier games are eligible, and how many worlds, is read from the record and
    printed with its derivation.
the team level  THE PLAY'S MAN. Each play of the drawn game is taken by one player. He is on the team's final active list for this week (the
    list is the record's). Whether he is on the field in a world is a chance the record gives per player. His chance of the play is
    formed from his own real plays of that kind for this team this season and from how players who held his place have been used
    in earlier seasons, in a form the record determines by likelihood on earlier seasons (rolling origin), printed. A pass to no
    one stays to no one. One ball per play. No player the record lists is said 0.
the play-call level  THE PLAY'S OUTCOME. What a pass becomes - its depth, whether it is caught, what is gained after the catch, whether it scores -
    and what a run becomes, are drawn as real past plays from the leaf of a conditional inference tree grown on every play of that
    kind before this week, at the check's level, with every play carrying its game (the game is the unit of variance). The
    columns offered to the tree are every field the record carries at the play's the data available before kickoff; the chance test keeps or
    refuses each; nothing is chosen. The leaf's plays are drawn, never averaged. Yards cannot pass the goal line.
T   TALLY. A player's stat in a world is the sum over the plays credited to him. The QB's passing line is the sum of his receivers'
    lines. Every player on the slate carries every term of his position in every world, 0 where he had none.
D   DETERMINISM. Every draw has its own stream named by (term, position, season, week, key, label). The same inputs give the same
    worlds. The grader pins the hash seed; the product adds nothing.

## 4. IDENTITIES (printed as IDENTITY GAPS across every draw; each must be exactly 0)
  plays in a world = passes to someone + passes to no one + sacks + runs of the drawn side
  acceptance criteria = attempts to someone; receptions <= acceptance criteria; receiving TDs <= receptions
  the passer's attempts / completions / yards / TDs = the sums of his receivers' targets / receptions / yards / TDs
  carries = the drawn side's runs; each run has one carrier
  the shares of the players on offense sum to one on every play
  no stat below 0; no yards past the goal line; points of the world = the drawn game's points

## 5. THE REBUILD IS ONE LANDING, JUDGED LIKE ANY OTHER
  Wall: `W_REBUILD_<id>` with CHAIN, PLACE (the product files), COST, and one RULED OUT per closed branch in GOAL_LADDER.md §7.
  PREDICTION, printed before land: the rebuilt product is the accepted product. Its slice_rows.csv matches the record's accepted rows
  by hash; the 624 matrix matches cell for cell; RULE 13b fails 0 of the frozen slices (identity); every IDENTITY DataGap is 0.
  Printed before the judgment, as the rewrite order requires: COVERAGE (each input per season; no season drops), IDENTITY GAPS,
  CARRIED (new lines identical to deleted lines; near 0 - a copy is not a rebuild), KILLED (each rule removed, by its old line,
  with the law that replaced it), and the DataGap list (every rule the record could not derive; each stopped, none filled).
  A rebuild whose rows differ from the accepted rows is not wrong by that alone: the difference is printed per slice under RULE 13b
  and 624, and the reviewer reads whether a DataGap's old filling was the cause. It lands only on the bar: no frozen slice worse beyond
  the allowance, the pooled units BETTER or identical, 624 no cell down.

## 6. AFTER
The queue in GOAL_LADDER.md §5 continues from the rebuilt product. Nothing in §6 runs before the rebuild has accepted or closed.
