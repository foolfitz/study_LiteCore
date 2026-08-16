# Product path, round 3 — on shell **v9**, with the recovery path finally driveable

`tools/run_e2_c_product_path.py`, Firefox, artifact `572035ac…` (**unchanged, no
relink**), shell bundle **v9 `eb76c5be…`**.

Round 2 is [`../round-2-high-paths/`](../round-2-high-paths/) and is unchanged;
it ran on v8, before findings 053 and 054 were fixed.

## Nine arms, every one `ok: true`

| check | baseline | mutations that must turn it red |
|---|---|---|
| `product-save-button-writes-a-real-odt` | PASS | `save` |
| `every-ime-commit-reaches-the-document` | PASS | `ime`, `save` |
| `ctrl-c-asks-the-engine` | PASS | `copy` |
| `product-insert-button-inserts-what-the-field-holds` | PASS | `insert-text` |
| `product-undo-button-reverses-the-last-edit` | PASS | `undo`, `undo-twice` |
| `notice-action-recovers-the-session` | **PASS** | `rollback`, `toolbar-drops-the-list-action`, `save` |

The last row is the change: in round 2 it was NOT_ESTABLISHED, because nothing
could put the product into the state where it offers the button.

## The route that made it driveable

Through the page's own buttons, no fixture switch and no coordinates guessed
from a document's twips:

1. click **past the end of a line** — measured natively, the clamp saturates at
   the end-of-line offset (`findings/evidence/queue-block-identity/`);
2. press **分段** (`insert-paragraph-break`) — the caret lands in a new **empty**
   paragraph;
3. press **項目符號** — that is finding 046's cell: `.uno:SelectText` overshoots
   into the neighbour and the barrier refuses a mutation that succeeded.

The queue blocks, `#notice` appears, pressing it returns the session to `ready`,
and the product saves a real ODT afterwards.

## What this round does NOT prove

**It is not evidence for finding 053's fix.**  The error the route produces is

```
MUTATION_OUTCOME_UNKNOWN: the postcondition read covered more than one
paragraph, so it does not describe the paragraph this action was dispatched on
```

and `MUTATION_OUTCOME_UNKNOWN` was **already** in the base class's
`RECOVERY_ERRORS` — it blocked the queue before the fix as well.  The fix is for
`EDITOR_FORMAT_POSTCONDITION_FAILED` with `dispatched: true`, and **whether a
user can reach that code through the product page is still not shown**: the only
place it has been observed is `../../d2-presweep/`, which drives the shell
directly.  The fix's evidence is the seam's unit test, where removing it turns a
test red.

Also unchanged from round 2: `isTrusted` is false throughout, **this is not D5**,
and where the insert landed is not checked — only that it is in the document.

## Two declarations changed, and the harness is what changed them

Neither was noticed by reading; both were reported by a run.

* **`rollback` was declared "expected not to be detected"** while its check
  could not run at all.  Once the route existed, the run reported the
  declaration **stale** and detected the mutation.  The declaration is gone and
  this is a live verification.
* **`save` now also reddens `notice-action-recovers-the-session`**, because that
  check ends by requiring the product to save a real ODT after recovering — that
  is how it shows the session is usable rather than merely in a good-looking
  state.  Declared in `alsoRed` after the run said so.

`alsoNotEstablished` carries the other half: `save` and `insert-text` destroy the
insert/undo checks' **preconditions**, so those cannot go red, only fail to run —
and the run verifies that outcome rather than assuming it.
