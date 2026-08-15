# D3 addendum — where was the caret? Predictions, registered before the probe

Registered 2026-08-15, after the `before=skip` run of L1–L8 and **before** the
caret-reporting arm existed.

## What the run showed

Every one of the eight cells acted on the document's **first paragraph**, not on
its anchor:

* L1, L8 (`set-list-unordered`) turned `E1-LC-HEADING` into a one-item list. L8's
  anchor was `E1-LC-BETWEEN`, four paragraphs away.
* L3, L4, L7 (`set-list-none`) reported `verified-format-readback` and changed
  nothing — a no-op on a heading that was never in a list.
* L2, L5, L6 (`set-list-ordered`) failed with
  `EDITOR_FORMAT_POSTCONDITION_FAILED`, also on the heading.

So the eight list predictions in `PREDICTION.md` are **not settled by this run**
in either direction. Nothing here is evidence about lists.

The anchor sweep is not the suspect: it returned eight distinct, monotonically
ordered y values 390 twips apart, which is what this corpus's line pitch looks
like.

The suspect is `EditorSession.placeCaret` (`editor-shell/editor-session.js:310`).
It clicks, then polls until the engine reports
`selectionType === "none" && collapsed === true && observed === true` — a
condition **any** collapsed caret satisfies, including the one that is already
there when the document opens. The click's coordinates are never compared
against where the caret ends up. This is the same confirmation signal finding
047 already showed to be insufficient, failing here in the opposite direction:
047 has it return before the engine is ready, this has it return without the
click having moved anything.

## Predictions

| # | claim | confidence |
|---|---|---|
| P-C1 | After `placeCaret(2000, y)` the reported `caret` rectangle is **not** at `y` — it sits at the first paragraph, the same place for every cell | **medium-high** |
| P-C2 | Replacing the gesture with the zero-width `selectRange` D1 and D2 used puts the caret at `y`, and the actions then land on the anchor | medium-high |
| P-C3 | The initial caret is already `observed: true` before any click, which is what lets `placeCaret` return early | medium |
| P-C4 | This is a product-path defect, not an engine one: the engine acts on whatever the caret is, and the caret was never moved | medium — P-C1 failing would invert this, and an engine that ignores a correctly placed caret is a far more serious finding |

## What each answer would mean

* **P-C1 holds** — `placeCaret` cannot confirm what it claims to confirm, and
  every product interaction that starts with a canvas click inherits it. D2 also
  uses `placeCaret` (`web/e2-c-d2-app.js:233`, `:384`); its green cells then owe
  a re-read before they can be quoted, exactly like the two D2 fixture mistakes.
* **P-C1 fails** (the caret is at `y` and the action still hit paragraph one) —
  the engine is applying paragraph format somewhere other than the caret, which
  is a stop-condition-grade finding and outranks everything else in this phase.
* Either way the harness owes a **fail-closed** check: a cell whose caret is not
  at its anchor must not be allowed to report a result at all. Three cells here
  reported `verified-format-readback` while measuring nothing, which is the
  failure mode D2's fixture mistakes already cost this phase once.

## 2026-08-15, later — one variable the first four predictions did not control

P-C1, P-C2 and P-C3 measured as predicted, and P-C4 was about to be written up
as "the product's click gesture does not move the caret". That report would have
been wrong, or at least unqualified, because of a difference between this
harness and the product page that none of the four predictions named:

**this harness never paints a tile, and the product page paints before the user
can click.** `handleClick` (`src/probe_engine.cpp:2343`) is
`postMouseEvent(MOUSEBUTTONDOWN/UP)`, and the engine never calls
`setClientVisibleArea` — it does not exist anywhere in the engine — so whatever
view state maps a document coordinate to a cursor position can only have been
established by `paintTile`. A click into a view that has never painted may
simply have nowhere to land.

| # | claim | confidence |
|---|---|---|
| P-C5 | With `session.document.render(...)` over the page before the click, `placeCaret` moves the caret to the clicked line | **medium** |
| P-C6 | If P-C5 holds, the defect is `placeCaret`'s confirmation predicate alone: it returns successfully in the un-painted case where the click did nothing | medium-high |
| P-C7 | If P-C5 fails, the product's canvas click does not move the caret at all, which contradicts E1-C's manual rounds passing 9/9 in two browsers and would mean those rounds and this measurement disagree about the same gesture | — |

P-C7 is the reason this arm gets measured rather than assumed. E1-C's manual
rounds were done by hand in a real browser on the product page; a human placing
a caret by clicking and then typing would have noticed if the caret never moved.
Two sources disagreeing is the state to resolve before either is quoted.

## 2026-08-15, later still — how it actually came out

**P-C5 failed** (a painted view changes nothing) and **P-C4 was refuted**, which
is the one that matters: the click is not inert. It takes effect in **22-28 ms**,
measured on all eight cells by polling the caret every 5 ms until it arrived, no
cell timing out. `placeCaret` returns before that because its predicate is
satisfied by the caret that is already there.

Two observations forced the correction, and neither was in the four predictions:

* D2's own pre-sweep clicked at y=1820 and the **clicked** paragraph is the one
  that changed in the saved document -- D2 takes a `snapshot()` save between the
  gesture and the action, and ~250 ms of saving is long enough for the click to
  land. So D2's cells were never measuring the wrong paragraph, and the claim
  written into finding 048's first version -- that they were -- was wrong.
* The settle ladder: 250 ms is already enough, so the fixed-delay arms could
  only ever have answered "this much was enough". Polling replaced the ladder
  and gave the number.

The corrected finding is 048. What survives unchanged is the harness rule this
addendum argued for: a cell whose caret is not provably at its anchor must not
be allowed to report a result. That rule is what made the 22-28 ms measurable
instead of leaving eight cells silently mis-anchored, and it stays.

Cross-check on the list results themselves: the eight cells were run through
three separate rounds -- `range-v2` and `run-2` (zero-width selectRange) and
`click-poll` (the product gesture, polled) -- and all nine saved documents,
including the no-action control, are byte-identical across all three.
