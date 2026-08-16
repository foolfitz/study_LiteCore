# E2-C phase D5 — the machine half is done; the four cells wait for an operator

Design and criteria in `PREDICTION.md`, registered before the harness existed.
Judged offline by `tools/analyze_e2_c_d5.py`; self-test 10/10 in both browsers.

> **Updated 2026-08-16 after four operator rounds**: two cells are now
> **PASS** (`d5-pointer-drag-single`, `d5-pointer-drag-cross`, round 4,
> Firefox), with their bullets visible in the captured documents.  The IME cell
> needs one clean redo on Firefox — Chrome marks `compositionend` untrusted, a
> measured platform limit — and the clipboard cell is waiting on a question
> about where a real paste is lost.  Rounds and readings:
> `operator/round-{1-chrome,2-chrome,3-firefox,4-firefox}/`.

**Verdict of the machine half: `PARTIAL`, with all four cells `NOT_ESTABLISHED`** — which is exactly
what the frozen matrix says an unrun D5 cell is (`onFailure: PARTIAL`).  Nothing
here claims a product property; what it establishes is that **the harness can
tell a real gesture from a fake one**, which is the only thing about D5 that can
be settled without a person.

## The product page is not modified

`web/e2-editor-app.js` is one of the twelve modules the E2-C shell bundle binds.
So the D5 page hosts it **unmodified, in a same-origin iframe**, and observes
from outside:

- capture-phase listeners on the iframe document record `isTrusted` for every
  pointer, keyboard, clipboard and composition event;
- a **declared** shim on the iframe's `URL.createObjectURL` captures the
  product's save, because the product saves by handing a Blob to a download link
  and nothing outside a download can read it.  It is listed in the evidence as
  `shims: ["URL.createObjectURL"]` rather than left to be discovered;
- the product's own status strip supplies revision, state and generation.

The shell bundle digest is recorded before and after every run.  **Unchanged in
both browsers**, which is the measured version of "observing it did not change
it".

## What the machine half proved

`tools/run_e2_c_d5.py --machine-half` drives the same page headlessly and
dispatches synthetic pointer, keyboard and composition events at the product.

| prediction | result |
|---|---|
| P-D5-M1 — every synthetic event is recorded `isTrusted: false` | **held** — 6/6 in both browsers, across `pointerdown`, `pointermove`, `pointerup`, `keydown`, `compositionstart`, `compositionend` |
| P-D5-M2 — the analyzer marks cells built from them `NOT_ESTABLISHED` | **held** — and the self-test shows the same cell passes once its events are marked trusted, so the rejection is the trust check and not some other missing thing |
| P-D5-M3 — the `createObjectURL` shim captures a save | **held** — one document captured per browser |
| P-D5-M4 — the shell bundle digest is unchanged | **held** — both browsers |

The self-test's load-bearing pair, run on the recorded evidence:

- with trust and everything else present, the drag cell **passes**;
- flip **one** event to `isTrusted: false` and it stops passing.

A harness that cannot be shown to reject a fake gesture is a harness that would
accept one.

## What still needs a person

| cell | what the operator does |
|---|---|
| `d5-pointer-drag-single` | drag-select within one paragraph, release, press the bullet button |
| `d5-pointer-drag-cross` | the same across two paragraphs |
| `d5-ime-commit` | a real Fcitx5 Chewing commit at a collapsed caret, then one replacing a selection |
| `d5-clipboard` | a real Ctrl+C / Ctrl+V round trip |

```
python3 tools/run_e2_c_d5.py --serve --port 8791   # prints a URL for a real browser
```

Step-by-step instructions for the person doing it:
`handoff/RUNBOOK-operator-d5.md`.

**Addendum 2026-08-16 (b)**: the page also gained a live readout and a pointer
trace, because the first attempt at an operator session stopped at the first
cell -- **this build paints no caret and no selection highlight**, so a person
clicking in the document sees nothing change and reasonably concludes it is
broken.  Measured in the iframe: the click lands, state stays `ready`, no error
notice, the events are recorded.  The harness now shows what the HARNESS
recorded (event counts, trusted/synthetic, the product's own revision) and draws
where the pointer went.  The overlay is `pointer-events: none` and
`elementFromPoint` over the product area returns the iframe, so it cannot
swallow the gesture being measured.

**Addendum 2026-08-16**: the page gained an export button that saves the whole
round -- metrics and every captured document -- as one JSON file, because the
alternative was telling an operator to copy a global out of the console at the
end of a session.  It touches no measurement path, and the machine half now
exercises it on every run (`operatorExport` in the result), so the last step of
a human session is not the one step nobody ever tested.

SPEC E2-C section 5 says the operator must not be asked repeatedly to reach a
GO, and SPEC E1-C's v9 revision says it in stronger words.  So these stay
`NOT_ESTABLISHED` until there is a session, and the phase reports PARTIAL, which
is what the matrix already prescribed.

**Worth scheduling together with E1-C's requalification** (SPEC E1-C 11.8):
same setup — Fcitx5 Chewing, a real clipboard, trusted pointer events — and
E1-C's deferral names that session as its unblock condition.
