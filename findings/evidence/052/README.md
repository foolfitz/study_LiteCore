# Finding 052 — a click outside the text costs 30 seconds and is then refused

Measured 2026-08-16 on the shipped `e2-editor-v2` artifact (wasm `572035ac…`),
Chrome headless, `list-contexts.odt`, through the product page's own pointer
handler.  Found while checking a claim from an adversarial review of finding
051's fix.

## The measurement that found it

`line-geometry-before-fix-chrome.json` — 26 clicks down one column of the
product page, each resolved before the next was sent:

| | |
|---|---|
| clicks **within** the text | 12, **all confirmed** |
| clicks **above the first line** | 3, all refused, **30.0–30.2 s each** |
| clicks **below the last line** | 10, all refused, **30.2 s each** |

The engine is not at fault: it answers a click outside the text the way every
editor does, by putting the caret on the nearest line.  The confirmation
predicate then asks whether the caret is on the *clicked* line, and the clicked
line does not exist — so it can never be satisfied, and the click waits out the
whole timeout before failing.

This matters because clicking below the last paragraph is how a person reaches
the end of a document.  The whole session queue is serialised behind it.

## The same run measured the geometry an adversarial review asked about

The review's claim was that finding 051's widened band could accept a caret from
an **adjacent** line whenever a caret box is taller than the distance to the
next line's top.  The arithmetic is right — `caretIsOnLine({y:1418,height:414},
1808)` is `true`, and the pre-051 predicate said `false`.  Whether that geometry
exists is a measurement:

| box | height | bottom | next line's top | gap |
|---|---|---|---|---|
| 1418 | 414 | 1832 | 1945 | **+113** |
| 1945 | 348 | 2293 | 2406 | **+113** |
| 2406 | 276 | 2682 | 2795 | **+113** |
| … | | | | **+113** (8 pairs, identical) |

**No box reaches into the next line's box — every gap is exactly 113 twips.**
So the case is not reachable in this corpus, and the number is the same one
finding 048 measured from the other side ("landings sit up to 119 twips above
the rectangle's top"): that 113-twip gap IS where those landings fall, and half
a line of upward slack covers it.

Recorded as *not reachable here*, not as *impossible*: a corpus with a box
taller than its pitch would reach it, and nothing in the code prevents that.

## The fix

The engine having **moved** the caret is the signal that it processed this
click, and the geometric test cannot see it:

```js
const caretMoved = caretDiffers(state?.caret, beforeCaret);
if ((onTarget && (acknowledged || Date.now() - started >= graceMs))
    || (acknowledged && caretMoved)) { … }
```

It does not weaken finding 048's guard, and that is pinned by a test rather than
argued: 048's failure is a **stale** caret, and a stale caret has not moved.  An
acknowledgement that is not about the caret (a tile invalidation) still does not
end the wait.

## After the fix — `clicks-below-the-text-after-fix-chrome.json`

| click | before | after |
|---|---|---|
| first click of the session, below the text | 30 s, refused | **203 ms, confirmed** |
| a second click below the text, caret already clamped there | 30 s, refused | **30.2 s, refused** |
| back into the text | confirmed | **203 ms, confirmed** |
| below the text again, after the caret moved | 30 s, refused | **203 ms, confirmed** |

## The residual, stated rather than papered over

**Clicking outside the text twice in a row still costs 30 s.**  The caret is
already where the clamp would put it, so nothing moves — and nothing moving is
exactly what a *swallowed* click looks like.  With a caret rectangle and a
clicked y as the only inputs, the two are indistinguishable.

Two other known-ambiguous cases sit in the same corner:

* after the grace period, a caret on the clicked line but at a completely
  different **x** is accepted (`x=100` reported for a click at `x=5000`);
  `caretIsOnLine` has no x input.  Reachable only when the engine swallows a
  click.
* the adjacent-line case above, if a corpus ever has a box taller than its
  pitch.

All three have the same remedy and it is not geometric: **the engine reporting
which block the caret is in**, so the confirmation compares identity instead of
rectangles.  That is the same remedy finding 046's `.uno:SelectText` overshoot
needs, and it is on the relink queue as one item rather than two.

## Bindings

* Shell bundle **v8 = `4daad6b4…`**; v7 stays as the record of
  what the D5 machine half re-run and the product-path rounds ran on.
* E1-C divergence declared (fourth entry).  No new requalification cost.
* **No relink.**  This is JS.
