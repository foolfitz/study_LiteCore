# Evidence for finding 048 — placeCaret confirms before the click takes effect

Everything here was produced by `web/e2-c-d3-app.js` and `web/e2-c-d2-app.js` on
profile `e2-editor-v2` (wasm `572035ac...`), Chrome, 2026-08-15.  The raw runs
live under `../sdk-e2/e2-c-validation/`; this file says what each one was for and
what it showed.

The D3 harness records, for every cell, the caret rectangle reported by
`editorGetStateV2` immediately BEFORE the positioning gesture and immediately
AFTER it, and refuses to dispatch when the caret is not within half a line pitch
(195 twips) of the requested y.

| run | arm | what it controls | result |
|---|---|---|---|
| `d3-lists/caret-probe/click-v2` | `caret=click` | the product's gesture, read back at once | 8/8 refused; caret still at y=1418 for requested y from 1950 to 4810 |
| `d3-lists/caret-probe/click-painted` | `caret=click&paint=page` | whether the click needs a painted view | 8/8 refused, caret still 1418, with a 512x512 tile of the whole page rendered first |
| `d3-lists/caret-probe/range-then-click` | `caret=range-then-click` | whether the mouse path works once a real selection has happened | caret placed at 1945/3184/2795 by `selectRange`, then clicked 780 twips lower; caret unchanged when read at once |
| `d3-lists/caret-probe/click-settle{,-250,-500,-1000}` | `caret=click&settle=N` | how long is enough | 250 ms already lands every cell; the ladder cannot say more than that |
| **`d3-lists/caret-probe/click-poll`** | `caret=click&settle=poll` | **how long it actually takes** | **22-28 ms, all eight cells, none timing out** |
| `d3-lists/caret-probe/range-v2`, `d3-lists/run-2` | `caret=range` | the control: a path that positions synchronously | 8/8 land within 65 twips of the requested y |
| `d2-narrow/caret-click-arm` | D2's empty-paragraph cell, `caret=click` | the same gesture with a ~250 ms save between gesture and action | caret READBACK still reports 1418, and the CLICKED paragraph is the one that changed |

**Reproducing these runs**: they were taken when `caret=click` still meant the
BARE gesture.  It now means the verified one -- click, then poll until the
engine reports the caret on the requested line -- and the bare gesture is
`caret=click-unverified`, the same spelling D2 uses.  Every `caret=click` row
above reproduces as `caret=click-unverified`.

`d3-lists/caret-probe/click` and `.../range` are the first pair, kept for the
record.  Their gate asked for a `caret.available` field that the engine does not
emit -- it writes JSON `null` for an absent rectangle and `{x,y,width,height}`
for a present one -- so both arms refused every cell, the range arm for the wrong
reason.  The caret coordinates in those files are still valid readings and they
agree with the corrected runs.

## The second signal, and the one that corrected this finding

`d3-lists/run-1b-before-skip/` is the D3 execution that dispatched all eight list
actions immediately after a `placeCaret`, before any of the above existed.  Every
one landed on the document's FIRST paragraph: `set-list-unordered` turned
`E1-LC-HEADING` into a one-item list in the cell whose anchor was
`E1-LC-BETWEEN`, four paragraphs away, and three cells reported
`verified-format-readback` for a no-op on a heading that was never in a list.
(The sibling `e2-editor-v2-572035ac/` is the execution before that one, which
died of finding 047 without dispatching anything.)

That run, plus the caret readbacks, is what the first version of this finding
called "the click never moves the caret at all".  What refuted it was
`d2-narrow/caret-click-arm`: the same gesture, but with a save between the
gesture and the action, and there the clicked paragraph is the one that changed.
The click lands; it is the immediate readback and the immediate dispatch that
are too early.  The polled run then measured how early.
