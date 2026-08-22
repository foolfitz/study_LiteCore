# Result: the engine removes a range, and `[range-single]` was an off switch

Measured 2026-08-22 on the linked ABI 4 artifact. Answers
[`PREDICTION.md`](PREDICTION.md), which was written 2026-08-21 before any of
this ran.

Read with [`RESULT.md`](RESULT.md) (the 2026-08-21 `delete-backward` arm, which
ended in `recoverable-error`) and
[`RESULT-replace-selection.md`](RESULT-replace-selection.md) (the empty-paste
route, closed in compiled code).

## What was under test

The v4 profile shipped `delete-selection` with `gestures: ["range-single"]`.
Three runs of the product path, all Chrome, all against
`dist/profiles/e2-editor-v4/`:

| | manifest | how |
|---|---|---|
| baseline | shipped, `["range-single"]` | ordinary run |
| widened | `["range-single","range-cross"]` | symlink mirror; `dist/` never written, `probe.wasm` byte-identical to `f923cfa5` |

## The finding that came first, and it is about the declaration

**`["range-single"]` is not a narrower grant. It is an off switch.**

`src/probe_engine.cpp`, the gate for a selection the build has not classified:

```cpp
const bool permitted =
    collapsed ? editorGesturePermitted(action, kGestureCollapsed)
              : (editorGesturePermitted(action, kGestureRangeSingle) &&
                 editorGesturePermitted(action, kGestureRangeCross));
```

Both bits, because the engine cannot tell a single-paragraph range from a
cross-paragraph one without an html read, and that read is the wedge risk
findings 037/038 describe. Granting one bit therefore refuses **every** range.

The baseline run says so in the engine's own words:

```
剪下：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this
kind of selection in this profile, so nothing was dispatched and the document
is unchanged
```

That sentence was true of no selection at all. A manifest that declares a
gesture the binary will never honour is the "describes but does not constrain"
defect pointing the other way — and it is worse than either extreme, because it
reads as a deliberate narrowing rather than as a mistake.

## The pre-registered predictions

| | | |
|---|---|---|
| **P-CUT-1** | the refusal is the manifest's, not the engine's | **held** — `refusalReported: false`, no `EDITOR_FORMAT_GESTURE_UNSUPPORTED` anywhere in the run |
| **P-CUT-2** | a within-paragraph range is removed | **held** — target `E1-LC-BETWEEN`: `targetStillPresent: false`, `targetTextAnywhere: false`, `neighboursSurvive: true`, `documentReadableAfter: true`, 9 lines before and after |
| **P-CUT-3** | the session survives it | **held** — `stateAfterCut: "ready"`, and the next step saved 11.8 KB |
| **P-CUT-4** | the cross-paragraph shape is **recorded**, not forecast | measured on **four** shapes; all four correct — see below |

The oracle is the **saved ODT**, anchored to a named paragraph, with the
untouched paragraphs required to survive verbatim. A revision that advanced
proves a dispatch, not a deletion.

## P-CUT-4: four shapes, not one

The prediction reserved this arm with no forecast attached, because the five
paragraph actions were characterised for cross-paragraph ranges and the ten v1
actions were not. Four shapes rather than one because finding 046 was a
multi-block readback verifying the wrong paragraph, and list items are what a
cross-block selection runs into — a cut that takes two plain paragraphs cleanly
says nothing about one that takes a bullet list and a numbered list with a plain
paragraph between them.

Fixture `list-contexts.odt`, nine paragraphs. Each arm re-opens the fixture
under **its own file name** and verifies the nine paragraphs are back before it
drags (see "the bug in the first sweep" below).

| shape | paragraphs | lines | untouched survive | session | document |
|---|---|---|---|---|---|
| heading into body | 0→1 | 9 → **8** | yes | `ready` | readable |
| three paragraphs into a bullet list | 2→4 | 9 → **7** | yes | `ready` | readable |
| a bullet list, a plain paragraph, a numbered list | 3→7 | 9 → **5** | yes | `ready` | readable |
| within one bullet list | 3→4 | 9 → **8** | yes | `ready` | readable |

Every arm merged the way a word processor does — the head of the first
paragraph followed by the tail of the last — and the line count fell by exactly
the number of paragraph boundaries the drag crossed. Arm 3, the widest:

```
before  E1-LC-HEADING / E1-LC-ISOLATED … / E1-LC-SPACER / E1-LC-BULLET-ONE /
        E1-LC-BULLET-TWO 中文項目 / E1-LC-BETWEEN / E1-LC-NUMBER-ONE /
        E1-LC-NUMBER-TWO / E1-LC-END
after   E1-LC-HEADING / E1-LC-ISOLATED … / E1-LC-SPACER / MBER-TWO / E1-LC-END
```

`MBER-TWO` is the tail of `E1-LC-NUMBER-TWO`: four boundaries crossed, four
lines gone, the three paragraphs above and the one below verbatim.

No arm produced `MUTATION_OUTCOME_UNKNOWN`, an unreadable save, a partial
removal, or a wedged session — the outcomes the prediction named as blocking.

## What the shipped checks did

Across all three runs the 34 product-path checks moved in **exactly one**
place, and that place was this measurement's own obsolete oracle:

```
ctrl-x-is-handled-by-the-product   PASS -> FAIL
```

It demanded `documentUnchanged: true` and `refusalReported: true`. It went red
**because the cut started working**. Same shape as finding 069's first
criterion, and the remedy is the same: replace the criterion and say why.

## Why this vindicates the ABI 4 design rather than just confirming it

The 2026-08-21 arm widened `delete-backward` and hit the **selection barrier**:
`EDITOR_STATE_UNAVAILABLE: selection barrier requires a callback-confirmed
collapsed caret`, session in `recoverable-error`, and the save that would have
answered the question refused with `EDITOR_NOT_READY`.

`delete-selection` dispatches `.uno:Delete` **plainly and deliberately** —
`startSelectionBarrierDelete` refuses a pre-existing selection by design, and
the whole point of this action is that the range is the caller's. That was a
design argument when the payload was written. It is now a measurement.

## What is still not characterised

Named rather than implied, and carried in the manifest's `limits` as
`not-characterised-in-tables-or-note-apparatus`:

* a range inside a **table**;
* a range covering a **footnote or endnote reference mark**.

Neither is in this fixture. The engine gate is binary, so granting the bits
makes both reachable — measuring them does not change what is granted, it
changes what is known.

## The bug in the first sweep, kept because the shape recurs

The first four-shape run reported `lines: 0` for arms two, three and four and
declined. The cause was in the harness, not the product: **every arm re-opened
the fixture under the same file name**, so the wait for
`doc == "cross-paragraph-cut.odt" && state == "ready"` was satisfied the instant
it was asked — by the *previous* arm's document, which already carried that name
and was already ready. Each arm then measured a page that was still loading.

Same family as the 2026-08-18 round that spent four rounds measuring a 404 page
the label said was the fixture. **A name is a label, and a label the page
already had is no evidence at all.** Fixed two ways: a distinct name per arm,
and a content check — the first arm defines what the fixture looks like and
every later arm must open into the same nine paragraphs or it declines and
records what it saw instead.

The arms declined rather than reporting a number, which is what they were built
to do. But their stated reason blamed the band-to-paragraph mapping, which was
not the cause.

## The cost, recorded because it is a loss and not a gap

Finding 063 is that a **refused** cut used to send the session into
`recoverable-error` and tell the user to discard unsaved work, over an action
that declared it had dispatched nothing. The disposition was fixed, and
`ctrl-x-is-handled-by-the-product` verified it on every run.

Granting the gesture removes the refusal from the product's own path, so that
check can no longer be about it. The refusal is now driven only by the
`cut-falls-back-to-the-caret-only-delete` mutation — which runs when somebody
names it, and which asserts that a check goes red rather than asserting finding
063's three properties.

This is the third time in this tree that a fix has removed the state its own
regression check needed (finding 046's disposition, finding 038's inducer, now
this). Recorded as `queue-cut-refusal-lost-its-inducer`, with two candidate
routes that do not require breaking the product first.

## Identities

Repackage only — no relink, and the guard on the `probe.js` target was never
reached because that target was already up to date.

| | |
|---|---|
| `wasmSha256` | `f923cfa5aba30749…` — **unchanged** |
| `loaderSha256` | `c382b834aa768b91…` — unchanged |
| `workerSha256` | `e6ee92ca290b7966…` — unchanged |
| `manifestSha256` | `f88c6289282bcd48…` → `cbf9392311fac92a…` |

`withheld: ["select-all"]` still holds in the builder's output. An empty
`withheld` would mean the dark action reached the manifest with gestures, and a
mask can never take back what a manifest granted.

## Re-running it

```bash
cd wasm_sdk_probe
TMPDIR=/home/jiajun/.cache/litecore-probe-tmp setsid nohup \
  python3 tools/run_e2_c_product_path.py --browser chrome \
  --range-delete-diagnostic --range-delete-action delete-selection \
  --no-caret-exclusion --out <path> > <log> 2>&1 < /dev/null &
```

The diagnostic still widens a **mirror**, which is now the same as the shipped
manifest — so the flag's value from here is the four cross-paragraph arms, which
run only under it and only at the very end.
