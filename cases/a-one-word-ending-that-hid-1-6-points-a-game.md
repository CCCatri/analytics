# A one-word ending that hid 1.6 points a game

## Wrong
Every possession ended in one word ("punt", "turnover"), so the 508 where the other side scored on that same play (pick-sixes 221, fumble returns 117, punt returns 68) read as plain stops. The simulator plays none of them.

## Caught
Every possession now carries two parts: the stop (one of eight, from the offense's last snap) and the score on the play (from the scoreboard). nflfastR as outside judge on all 36,349: 36,344 agree, 4 named, 4 inside its own two numbering errors (a lightning delay and a timeout kept the old drive number). Where the two sources disagreed, the rule book ruled, and on one muffed field goal it ruled against us: one merged possession fixed.

## Control
Before its verdict the check must catch four injected faults: a possession dropped, one split in two, the muffed field goal merged back, a pick-six with its points removed. All four FAIL as required.

## Changed
One definition in `rules.py`; the project owner's law that every use of the simulator carries every stop-and-score cell, record beside engine (`acceptance-criteria/possession-ends.md`). It exposed the gap: the other side scores 1.60 a game in the play-by-play record and 0.19 in the engine; the offense 39.5 against 35.9. `fde46dc`, `8470eb2`, `bba2ad4`, `377ff0e`. Résumé: left out (no weaker line to replace, no gap); it competes with the simulator bullet once the gap is closed.

