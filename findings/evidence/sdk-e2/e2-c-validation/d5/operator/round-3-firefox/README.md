# D5, third operator round (Firefox, 2026-08-16) — the IME control, and finding 049 confirmed by hand

Preserved exactly as exported, with the operator's own saved document beside it.

## The two things this round was for

### 1. `compositionend` is trusted in Firefox — the Chrome result is browser-specific

Round 1 (Chrome) measured every `compositionend` arriving with
`isTrusted: false`, which by D5's rule disqualifies the cell.  Firefox, same
operator, same Fcitx5 Chewing, same machine:

```
compositionstart   isTrusted=true   ''
compositionupdate  isTrusted=true   'ㄋ' … '你好'
compositionend     isTrusted=TRUE   '你好'
```

**Four sequences, four trusted `compositionend`, zero synthetic events in the
whole cell.**

So D5's criterion is not wrong and does not need relaxing: **the IME cell is
obtainable, on Firefox**.  What Chrome does is a measured platform limit, and it
belongs in the matrix as one — not as a reason to weaken the rule that makes
this phase mean anything.

### 2. Finding 049's fix, verified by the person who found it

The operator's downloaded file: **12,949 bytes, a valid ZIP with 9 entries**,
and `E1-LC-SPACER你好` in the body — the IME text is in the document.  Before the
fix the same button produced 15 bytes of `[object Object]`.

Kept as `operator-saved.odt` here and in `findings/evidence/049/verified-by-operator/`.

## Cells

| cell | events | revision | synthetic |
|---|---|---|---|
| `d5-pointer-drag-single` | 2 down, 85 moves, 2 up | 0 → **1** | 0 |
| `d5-pointer-drag-cross` | 2 down, 67 moves, 2 up | 1 → **2** | 0 |
| `d5-ime-commit` | 4 compositions, 24 updates, 53 keydown | 2 → **3** | **0** |
| `d5-clipboard` | 1 copy, 1 paste | 3 → 3 | 0 |

Three of the four now fail on **one** check, and only that one:
`savedDocumentCaptured`.  The operator saved — the file above proves it — but
the page's shim did not see it, which means the save happened outside the page
whose `URL.createObjectURL` is shimmed.

**That step has now failed in all three rounds**, for a different reason each
time, so it stopped being a step: `endCell` now closes the cell's event window
and *then* presses the product's save button itself, attributing the captured
document to the cell just ended (`pressedBy: "harness"`).  Verified: 12,197
bytes, ZIP magic, correct cell.  The criterion is about the saved document, not
about whose finger pressed the button — and the click happens after the window
closes, so it cannot touch the trust accounting.

## The open question this round produced

**Four IME commits advanced the revision once, and a real paste advanced it not
at all.**

Not diagnosed, and deliberately not guessed at:

- A control was run — four consecutive `session.commitText()` calls through the
  same shell, same fixture — and **all four advanced the revision** (0→1→2→3→4,
  1–2 ms each).  So the loss is **not** in the shell's commit path.
- That places it between the browser's composition events and `commitText`,
  i.e. in `HostInputAdapter`.
- **The adapter keeps its own trace, and the product throws it away**:
  `EditorSession` accepts `onInputTrace`, and `web/e2-editor-app.js` does not
  pass one.  So the layer where the loss happens is the one layer nobody is
  recording.

Next controlled variable, named: wire `onInputTrace` (and `onClipboardTrace`)
into a page the operator can drive, and repeat this cell.  That is a product
change to a bundle-bound module, so it is a decision, not a detail.
