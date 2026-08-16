# E2-C phase D5 — design and criteria, registered before the harness existed

Written 2026-08-16.  D5 is the one phase automation cannot do: its whole point
is `isTrusted`.  SPEC E2-C section 5 lists four things, and
`e2/validation-matrix-v1.json` froze them with `onFailure: PARTIAL`:

| cell | oracle, as frozen |
|---|---|
| `d5-pointer-drag-single` | a trusted pointer drag on the product page selects one paragraph, a format button then applies to it, and the saved ODT shows it |
| `d5-pointer-drag-cross` | a trusted pointer drag spanning two paragraphs, then a format button; both paragraphs verified |
| `d5-ime-commit` | a real Fcitx5 Chewing commit at a collapsed caret, and one replacing a selection, on the v2 artifact |
| `d5-clipboard` | a real Ctrl+C / Ctrl+V round trip, plain text only |

## The product page is not modified, and that is the constraint everything follows from

`web/e2-editor-app.js` is one of the twelve modules the E2-C shell bundle binds
(`e2/editor-shell-v2-bundle-v3.json`).  Editing it to add a recorder would
change the digest every D-phase result is filed under — the exact move SPEC E2-C
section 6 exists to prevent.  E1-C could put its manual round in a validation
page; E2-C cannot, because 2.4 established that **the thing under test is the
product page itself**.

So: the D5 page **hosts the unmodified product page in a same-origin iframe** and
observes it from outside.  The operator uses the real product UI.

Three observation points, all in the iframe's realm at runtime, none of them a
change to a file:

1. **capture-phase listeners** on the iframe document for `pointerdown`,
   `pointermove`, `pointerup`, `keydown`, `copy`, `paste`,
   `compositionstart/update/end` — recording `isTrusted` for every one;
2. **a shim on `URL.createObjectURL` inside the iframe**, because the product
   saves by handing a Blob to a download link and a harness outside cannot read
   a download.  The shim reads the Blob and passes the call through unchanged.
   **It is declared in the evidence** (`shims: ["URL.createObjectURL"]`) rather
   than left for someone to discover;
3. **the product's own status strip**, read from the iframe DOM, for revision,
   generation and state.

Nothing is written to `web/e2-editor-app.js`, `dist/e2-editor-app.js`, or any
bundled module.  The bundle digest is checked before and after the round.

## What a cell needs before it may be marked done

Registered here so the page cannot be argued into accepting less:

- **every gesture event backing a cell carries `isTrusted: true`.**  One
  synthetic event anywhere in a cell's window disqualifies the cell.  This is
  the only property D5 exists to establish;
- the product's revision advanced across the cell;
- for the drag cells, the drag produced **`pointermove` events between down and
  up** — a click is a zero-length drag and the product treats it as a caret
  placement, so a "drag" with no moves is a click that was called a drag;
- for the cross-paragraph cell, the recorded start and end y differ by **more
  than one line box**, measured from the caret rectangles the product reports,
  not from a constant;
- a document was saved and captured, and the offline validator finds the
  expected anchors in it.

## The machine half, which runs today with no operator

The four cells need a person.  **The harness's ability to tell a real gesture
from a synthetic one does not**, and that is the part that can fail silently.

So `tools/run_e2_c_d5.py --machine-half` drives the same page headlessly,
dispatches synthetic pointer, keyboard and composition events, and asserts:

- **P-D5-M1** — every synthetic event is recorded with `isTrusted: false`;
- **P-D5-M2** — the analyzer marks every cell backed by them `NOT_ESTABLISHED`,
  never PASS;
- **P-D5-M3** — the `createObjectURL` shim captures the product's save when the
  save is triggered synthetically, so the evidence path is proved before an
  operator is asked to walk it;
- **P-D5-M4** — the shell bundle digest is identical before and after the
  machine half, i.e. observing the product did not change it.

**A harness that cannot be shown to reject a fake gesture is a harness that
would accept one.**  E1-C's manual gate learned this the expensive way: an
anchor criterion of `>= 1` passed for years before someone read section 6 and
found it should have been `== 1`.

## Predictions for the operator round

Registered now, scored when it runs:

- **P-D5-1** — a trusted single-paragraph drag followed by a format button
  produces the format in the saved ODT.
- **P-D5-2** — the same across two paragraphs affects both.
- **P-D5-3** — a real Chewing commit at a collapsed caret inserts exactly the
  committed text once, and one replacing a selection replaces it exactly once.
- **P-D5-4** — a real Ctrl+C / Ctrl+V round trip moves plain text only.

## What voids the round

- Any cell whose events include a synthetic one: recorded `NOT_ESTABLISHED`,
  and **not retried by dispatching a synthetic version to "check the plumbing"**
  — that is how a fake gesture ends up in the evidence.
- The shell bundle digest differs before and after: the round is discarded,
  because the product that was exercised is not the product the verdict binds.
- The operator is unavailable: the cells stay `NOT_ESTABLISHED` and the phase
  reports PARTIAL, which is what the matrix's `onFailure` already says.  SPEC
  E2-C section 5 forbids repeatedly asking an operator to reach a GO.
