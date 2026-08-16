# Product path, round 2 — the three HIGH-risk paths, 2026-08-16

`tools/run_e2_c_product_path.py`, Firefox, on the shipped `e2-editor-v2`
artifact (wasm `572035ac…`), shell bundle **v8 `4daad6b4…`**.

Round 1 is [`../`](../) and is unchanged.

## Why this round exists

`e2/product-path-coverage.json` named three paths **HIGH and driven by nothing**,
and said of the third: *"a recovery path that has never been exercised is a
recovery path nobody knows works."*  This round drives them.

## Results

| check | baseline | its mutation |
|---|---|---|
| `product-insert-button-inserts-what-the-field-holds` | **PASS** | `insert-text` (reads `el.text.placeholder` — finding 049's shape) → RED |
| `product-undo-button-reverses-the-last-edit` | **PASS** | `undo` (does nothing) → RED; `undo-twice` (takes back one edit too many) → RED |
| `notice-action-recovers-the-session` | **NOT_ESTABLISHED** | `rollback` declared undetectable; `toolbar-drops-the-list-action` → RED |

Plus the three checks round 1 established, re-run here: the save button, the
three IME commits, and Ctrl+C.  **Nine arms, every one of them `ok: true`.**

## The third path did not become green, and that is the result

The product offers `#notice-action` **only** while the session is in
`recoverable-error` or `restart-required` — the same set
`EditorSession.restart()` accepts.  Pressing it from `ready` measures nothing,
which is what the first version of this check did.

The one recorded route into that state from the product's own UI is finding
047's sequence (save → click-placed caret → format action).  **It did not
reproduce**, in two rounds, with the three actions dispatched back to back from
inside the page: `• 項目符號 472 ms`, state still `ready`.  That is **not** a
verdict on 047 — it was measured on 2026-08-15 through a different harness and a
shell generation before finding 048 changed what `placeCaret` waits for.  Filed
as `queue-047-may-have-closed-under-048`.

So the check reports NOT_ESTABLISHED — its precondition was never reached —
rather than green (it measured nothing) or red (nothing is known to be broken).

**And NOT_ESTABLISHED is not a hiding place**: the run first requires the recipe
to have visibly done something.  If the format action neither blocked the queue
nor completed, the check FAILS.  `mutation-toolbar-drops-the-list-action` is
that guard's proof — a toolbar that silently drops the one action the recipe
dispatches turns this check red.

## What the first press found

[Finding 053](../../../../../053-the-product-prescribes-a-recovery-whose-button-it-does-not-show.md).
Every run here records it:

```json
{"noticeOffered": {"shown": false, "label": "回到檢查點"},
 "toastFromPressingItAnyway": "回到檢查點：editor cannot restart from ready"}
```

## Two things this round changed about how checks are written

Both came out of runs that went red for the wrong reason, and both were
adjudicated externally on 2026-08-16.

1. **Absence oracles need witnesses, and the witnesses are DERIVED.**  "The
   marker is gone" is equally true of an undo that empties the document; "the
   marker is present" is equally true of an insert that destroys everything
   else.  The first version required the three IME strings outright — and the
   `ime` mutation, which drops two of them by design, turned two unrelated
   checks red.  The witness set is now derived from *this run's own previous
   capture*: a check may require content whose presence **it** verified, never
   content whose presence is another check's subject.  An empty witness set is
   NOT_ESTABLISHED.
2. **A declaration must not claim more than the harness delivers.**  Mutations
   upstream of a check's setup destroy its precondition rather than its outcome,
   so `alsoNotEstablished` declares that — and the run **verifies** it, flagging
   the declaration stale if the check ever runs at all.  This is not decoration:
   it moved `product-insert-…` out of the save mutation's `alsoRed` on this very
   round, because once the witnesses became derived, a broken save leaves an
   empty witness set.

## Not established here

* **`isTrusted` is false throughout.**  This is not D5 and no D5 cell may cite
  it.
* **Where the insert landed.**  The check reads presence in the saved ODT, not
  position.
* **That the recovery works while the queue is BLOCKED**, which is the situation
  SPEC E2-B 5.13 prescribes it for.
* **Chrome.**  This round is Firefox only; round 1 has both.
