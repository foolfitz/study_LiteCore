# Result: two empty scans agreed with each other, and that counted as settled

`queue-canvas-grew-arm-abstains-intermittently`, 2026-08-27.

## What was owed

The item asked one question: **why does the band scan come back empty on a
two-page document the session already calls `ready`?** The fields added on
2026-08-26 -- `bandsBeforeTheEdit`, `scanWidth`, `stateBeforeTheEdit` -- were
there so the next occurrence could say which precondition failed instead of
stopping at `heightWhenOpened`.

## The next occurrence, twice

Both are acceptance runs for finding 084's fix, shipped profile, shell v43,
same machine, same hour:

```
bandsBeforeTheEdit: 0        <- not "too few to compare". ZERO.
scanWidth:          725      <- a full-width scan
stateBeforeTheEdit: ready    <- the session said so itself
heightWhenOpened:   2007     <- and the canvas was the right size
```

Identical in both, and identical to the signature of the three abstentions of
2026-08-26. So: the state was fine and the scan was the thing that came back
empty, which is what the new fields were added to be able to say.

## The cause is in the instrument

`stable_bands()` waited for the scan's shape to repeat before trusting it --
written 2026-08-19, after the same page reported 11 bands and then 9, a repaint
caught in flight. The rule was:

```python
if previous is not None and shape == previous:
    return scan, bands
```

**Two empty scans agree with each other.** A canvas that had not painted yet
satisfied the repeat test after one 0.5 s sleep, and the function returned
"settled, zero bands" half a second after the document opened. "The page has
settled with no ink on it" and "nothing has been drawn yet" are the same answer
to that test -- the tree's own recurring shape, where *nothing happened* and
*the mechanism never ran* look alike and both look green.

## The fix, and the number that proves it was the cause

An empty shape no longer ends the wait; it uses the whole budget. The scan now
records how it finished, so the two cases stay distinguishable afterwards:
`stableBecause: "repeated"` is the shape settling, `"exhausted"` is the budget
running out with the canvas still blank.

Same run, same machine, immediately after:

```
bandsBeforeTheEdit:    2
scanSettledAfterTries: 4          <- ink appeared on the FOURTH scan
scanSettledBecause:    repeated
heightWhenOpened:      2007
heightAfterTheEdit:    3002
heightWhenReopened:    3002       -> the arm established, and PASSED
```

**Four tries.** The old rule returned at try 2. The canvas really was blank for
the first second; the instrument stopped looking before it was painted.

The whole run: **38 PASS / 2 NOT_ESTABLISHED, `ok: true`**, and
`tools/check_usable_editor.py` reconciles the checklist -- `"problems": []`,
`"ok": true` -- which the two abstaining runs could not do.

## Cost, measured rather than assumed

Arms that deliberately expect a blank canvas -- the above-the-wall pair -- now
spend the full budget before saying so, and a canvas that stayed blank for six
seconds is a stronger statement than one that was blank for one. Run duration to
the last check: **361.4 s before, 364.7 s after**. Not minutes.

## Three runs, and the number is the same in all three

| run | canvas arm | bands | `scanSettledAfterTries` | outcomes | checklist |
|---|---|---|---|---|---|
| c | **PASS** | 2 | **4** | 38 PASS / 2 NE | `ok: true` |
| d | **PASS** | 2 | **4** | 38 PASS / 2 NE | `ok: true` |
| e | **PASS** | 2 | **4** | 37 PASS / 3 NE | `ok: true` |

Four tries every time -- the ink appears about 1.5 s after the open, and the old
rule stopped looking at 0.5 s. That is not a rate, it is a constant, which is
what an instrument reading too early looks like once the instrument stops
reading too early.

(Run e has a third abstention, `clear-format-removes-every-inline-format`,
unrelated to this arm; the checklist reconciles anyway.)

## What this does not settle

**It does not explain the tile timing.** Why a two-page document takes more than
a second to paint on this core is a separate question, and this measurement only
says the instrument was reading before it happened.
