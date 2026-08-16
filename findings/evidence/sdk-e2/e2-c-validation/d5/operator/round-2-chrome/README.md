# D5, second operator round (Chrome, 2026-08-16) — the round that found the save is broken

Preserved exactly as exported.  **Verdict: PARTIAL, four cells
`NOT_ESTABLISHED`** — and this time the blocker is a product defect, not an
instruction.

## What improved over round 1

| | round 1 | round 2 |
|---|---|---|
| cross-paragraph revision advanced | no (1 → 1) | **yes (1 → 2)** |
| synthetic events in the drag cells | 0 | 0 |
| events recorded | 832 | 574 |

The revision readout added after round 1 did its job: the cell that silently
failed on "the action never landed" now lands.

## Why every cell is still NOT_ESTABLISHED

**`savedDocumentCaptured` fails in all four, and it cannot be made to pass**:
pressing the product's own 儲存 ODT button writes **15 bytes containing
`[object Object]`** — [finding 049](../../../../../049-the-product-save-button-writes-fifteen-bytes-of-object-object.md).
The operator's own downloaded file (`findings/evidence/049/product-save-output.odt`)
is those 15 bytes.

The frozen matrix's oracle for the two drag cells is "a trusted pointer drag …
**and the saved ODT shows it**".  **That oracle is unreachable while the save is
broken**, so D5 cannot reach PASS until finding 049 is fixed.  No amount of
operator time changes that, which is why the round was stopped here rather than
repeated.

Two further cells have their own reasons, recorded as measured:

- **`d5-ime-commit` was never ended** — `stripAfter` is null and the cell holds
  no events.  The next cell's begin button took over while it was still open.
  Nothing about the IME is established or refuted by this round; round 1's
  `compositionend isTrusted:false` measurement stands and still needs a Firefox
  control.
- **`d5-clipboard` shows a real Ctrl+C and a real Ctrl+V** (1 copy, 1 paste, both
  trusted) **with the revision stuck at 3 and the product in `busy` at both
  ends**.  The paste reached the page; the document did not move.  The session
  was already `busy` when the cell began, so the most likely reading is that the
  commit queued behind whatever was in flight — but this round does not measure
  that, and it is not recorded as if it did.  Round 1's clipboard cell **did**
  advance the revision (11 → 13), so the paste path is not dead.

## What this round establishes

- The harness's new readout closed the gap it was built for (revision).
- **The product's save button has never worked**, and no automated round could
  have found it: every harness calls `session.save()` itself and destructures
  `{ bytes }`, so they all exercise the shell's save and never the product's
  button.  It took a person pressing it.

That is the argument for D5's existence, made by D5 on its second attempt.
