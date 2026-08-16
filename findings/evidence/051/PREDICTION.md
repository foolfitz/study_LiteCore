# Prediction, written before the measurement (2026-08-16)

Claim under test: `caretIsOnLine(caret, yTwips)` in `editor-shell/editor-session.js`
accepts `|yTwips - caret.y| <= caret.height / 2`, and `caret.y` is the TOP of the
caret rectangle, not its centre.  The accepted band is therefore

    [caret.y - height/2, caret.y + height/2]

which covers half a line ABOVE the line box and only the TOP HALF of the line
box itself.  A click that lands in the bottom half of a line is refused even
though the engine put the caret exactly where the click asked.

Geometry measured on the product page, Chrome, list-contexts.odt:
document 12808 x 16408 twips on a 725 x 929 px canvas -> 17.66 twips/px.
The line hit by a click at y-fraction 0.10 reports caret.y = 1418, height = 414,
so the line box is 1418..1832 twips = y-fraction 0.0864..0.1116.

## P-051-1 (the whole claim)

A click at y-fraction **0.092** (twips ~1665... recomputed: 0.092 * 16408 = 1510,
inside 1418..1625, the accepted band) **confirms in under 2 seconds**.

A click at y-fraction **0.106** (0.106 * 16408 = 1739, inside the line box
1418..1832 but above 1625) **times out after 30 seconds** with
EDITOR_CARET_NOT_PLACED, and its reported caret is on the line that was clicked.

If the second click confirms quickly, the diagnosis is wrong and nothing here
may be filed.

## P-051-2 (the fix, measured on a mirror)

With `caretIsOnLine` replaced by "the click is inside the caret rectangle,
extended upward by at most half a line to cover the gap between line boxes",
BOTH clicks confirm in under 2 seconds, and a caret left on a DIFFERENT line
(the stale-caret case finding 048 exists to catch) is still refused.

The second half of that is not optional: a fix that accepts everything would
pass P-051-2's first half and silently undo finding 048.
