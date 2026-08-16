# Finding 051 — the caret confirmation refuses the bottom half of every line

Measured 2026-08-16 on the shipped `e2-editor-v2` artifact (wasm `572035ac…`),
Chrome headless, `list-contexts.odt`, through the product page's own pointer
handler.  Predictions were written before the measurement and are reproduced
below verbatim from `PREDICTION.md`.

## What the product does

`editor-shell/editor-session.js` confirms a click by waiting until the engine
acknowledges it AND the caret is on the clicked line (finding 048).  "On the
clicked line" was

    Math.abs(yTwips - caret.y) <= Math.max(caret.height / 2, 1)

and `caret.y` is the **top** of the caret rectangle, not its middle.  The
accepted band is therefore `[caret.y - h/2, caret.y + h/2]`: half a line ABOVE
the line box, plus the box's own **top half**.  A click that lands in the bottom
half of a line is never confirmed — it waits out the 30-second timeout and then
fails with `EDITOR_CARET_NOT_PLACED`.

## The measurement

`four-clicks-all-refused-chrome.json` — four isolated clicks, each resolved
before the next was sent (the shell serialises them, and an earlier run that
fired clicks without waiting was unreadable for that reason):

| click | wall | outcome |
|---|---|---|
| (0.40, 0.10) | 30.1 s | `EDITOR_CARET_NOT_PLACED` |
| (0.40, 0.18) | 30.1 s | `EDITOR_CARET_NOT_PLACED` |
| (0.15, 0.10) | 30.1 s | `EDITOR_CARET_NOT_PLACED` |
| (0.40, 0.03) | 30.1 s | `EDITOR_CARET_NOT_PLACED` |

The error's own details show the engine had done exactly what was asked:

```
asked   xTwips 5123  yTwips 1641
caret   x 4298  y 1418  width 0  height 414      -> the line box is 1418..1832
sequenceAdvanced: true
```

1641 is inside 1418..1832.  The caret was on the clicked line; the predicate's
band ended at 1625.

`halves-before-fix-chrome.json` — the same line, top half against bottom half,
twice each:

| click | y twips | wall | outcome |
|---|---|---|---|
| top half | 1510 | **0.3 s** | confirmed |
| bottom half | 1739 | **30.1 s** | refused |
| top half again | 1510 | **0.5 s** | confirmed |
| bottom half again | 1739 | **30.1 s** | refused |

`halves-after-fix-chrome.json` — the same four clicks with the predicate
corrected: **0.3, 0.5, 0.5, 0.3 s, all confirmed.**

## Predictions, written before the measurement

* **P-051-1** — a click in the accepted band confirms in under 2 s; a click in
  the same line's bottom half times out at 30 s with the caret reported on the
  clicked line.  *Explicit retreat condition: if the second click confirms
  quickly, the diagnosis is wrong and nothing may be filed.*
  **HELD**, twice each.
* **P-051-2** — with the predicate corrected both clicks confirm quickly, AND a
  caret left on a different line is still refused.  **HELD**: the browser half
  above, and the stale-caret half in `editor-shell/tests/place-caret.test.mjs`,
  where finding 048's five tests still pass unchanged.

## How it was found, and why no earlier round found it

`tools/run_e2_c_page_smoke.py` — the one automated thing that drives the product
page — was green on 2026-08-15 (recorded in SPEC E2-C 2.4) and red on
2026-08-16, at `place-caret`.  It was run again only because a **product-path
regression harness** was being built out of the day's three operator-found
defects.

The D5 operator rounds did not catch it, and could not have been expected to:
their four cells **drag**, and a drag selects through `selectRange`, whose
confirmation this predicate is not part of.  The one operator report that does
match it is round 1's opening sentence — *"the caret cannot be placed, so I
can't start"* — which was read at the time as the product drawing no caret.  It
was also literally true.

## The fix

```js
const slackAbove = Math.max(caret.height / 2, 1);
return yTwips >= caret.y - slackAbove && yTwips <= caret.y + caret.height;
```

Asymmetric, and the asymmetry is the measurement: real landings sit up to 119
twips **above** a rectangle's top, because a click can fall in the gap between
two line boxes and the engine attributes it to the line below — so slack is
needed above and nothing is needed below, where the next line's own box begins.

Verified by mutation: with the old predicate restored, the two new tests fail
and finding 048's five tests still pass; with the fix in place all eight pass.
End to end, `run_e2_c_page_smoke.py` goes from `place-caret` refused after 30 s
to **`定位游標 34 ms`** and a green run.

## Bindings

* Shell bundle **v7 = `e9668347…`**; v6 = `9b7e7d2a…` is frozen as the record of
  what D5's four operator cells ran on.
* E1-C divergence declared (third entry in
  `wasm_sdk_probe/e1/editor-shell-bundle-v1-divergence.json`); no new
  requalification cost, since that binding was already broken by 048 and 050.
* **No relink.**  The artifact is untouched: this is JS.
