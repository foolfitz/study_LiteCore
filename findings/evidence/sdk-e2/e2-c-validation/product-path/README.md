# The product path, driven automatically — first run, 2026-08-16

`tools/run_e2_c_product_path.py`, on the shipped `e2-editor-v2` artifact
(wasm `572035ac…`), shell bundle **v8 `4daad6b4…`**.

## Why this exists

Three product defects were found on 2026-08-16 **by a person**, in the D5
operator round, and by nothing else in this tree:

| | |
|---|---|
| [049](../../../../049-the-product-save-button-writes-fifteen-bytes-of-object-object.md) | the save button wrote 15 bytes of `[object Object]` |
| [050](../../../../050-every-ime-commit-after-the-first-is-rejected-as-a-buffer-mismatch.md) | every IME commit after the first was dropped |
| Ctrl+C | never asked the engine for the selection |

They share one shape: **every harness in this tree calls `session.save()` and
`session.commitText()` itself**, so all of them exercised the shell and none of
them ever went through the product's own handlers.  Where the harness's path and
the user's path differ, only the user's path is unmeasured.

This runner takes the user's path: the product's save button, the product's
input sink, the product's copy handler.

## What it is not

Every event here is synthesised, so `isTrusted` is **false** throughout.  **This
is not D5 and no D5 cell may cite it.**  D5's whole subject is trusted input and
it needs a human.  This is a regression net underneath D5, sharing only the
path.

## Results

| run | save button | three IME commits | Ctrl+C |
|---|---|---|---|
| `baseline-chrome.json` | PASS — ZIP magic, 9 entries, ODT mimetype, `content.xml` parses, toast "11.9 KB" | PASS — revision 0→1→2→3, one per commit, all three strings in the saved ODT | PASS — handler ran, engine returned a non-empty selection |
| `baseline-firefox.json` | PASS | PASS | PASS |

## Each check was shown to fail

`--mutate` reintroduces one defect into a **symlink mirror** of `dist/` (7.5 GB
of frozen profiles; nothing is copied and `dist` is never written) and requires
the owning check to go red while the others stay green.

| mutation | reintroduces | must go red | result |
|---|---|---|---|
| `save` | 049's exact line | save **and** IME | both red, Ctrl+C green — chrome & firefox |
| `ime` | 050's missing sink clear | IME | red, others green — chrome & firefox |
| `copy` | the unbound `copy` listener | Ctrl+C | red, others green — chrome & firefox |
| `copy-lies` | *nothing that has happened*: a handler that prevents the default and toasts success **without calling the engine** | **nothing — declared undetectable** | not detected, as declared |

The `save` mutation reproduces finding 049 to the byte: `capturedBytes: 15`,
`head: "[object Object]"`, `toast: "已存出 NaN KB"` — the same file the operator
downloaded.

**Why the save mutation must also redden the IME check**, declared rather than
worked around: the IME check reads the document **through the product's own
save**, because that is the only way out of the page — which is precisely why
049 could hide as long as it did.  The alternative, an IME check that asks only
whether the revision moved, is the criterion round 5 passed while the product
was silently dropping two of three real commits.

## What this harness is NOT claimed to catch

An adversarial review (2026-08-16) asked which checks could still pass against a
broken product.  Three answers were fixed the same day and are covered above:
the save check now requires an ODT rather than any ZIP (an ODT mimetype entry
and a `content.xml` that parses), the IME check now pairs **each** commit with
exactly one revision advance rather than checking the total, and the copy check
classifies the outcome by which error the clipboard adapter raises.

One answer could not be fixed, and is recorded as a mutation instead of as an
assumption.  `--mutate copy-lies` gives the page a copy handler that prevents
the default and reports `已複製 1 字` **without ever calling
`session.copySelection()`**, and the check passes:

```
handlerRan: true   toast: "已複製 1 字"   outcome: "copied"
```

From outside the page, "the engine was asked" is not observable — the product's
only outward signal is its own toast, and a lying handler writes the same toast.
Closing it needs the shell's clipboard trace reported somewhere a harness can
read, which is a product change and therefore a decision, not a detail.  The
mutation is kept in the tool so that if this ever DOES become detectable, the
run says the recorded limit is out of date.

## Declared shims

A harness that patches the page it observes says so where the evidence can see
it (SPEC E2-C 6):

* `URL.createObjectURL` — the product saves by handing a Blob to a download
  link, and nothing outside the page can read a download.
* `HTMLAnchorElement.prototype.click`, for anchors carrying `download` — so a
  headless browser is never asked to open a save dialog, which would block every
  later command.  This leaves the download plumbing itself unmeasured; an
  operator established that by hand (`findings/evidence/049/verified-by-operator/`).
* `#toast.textContent` cleared between steps, so "the product said nothing" is
  distinguishable from "the product said something earlier".

One further note on fidelity, because it is the difference between a check that
can fail and one that cannot: the IME sequence writes `sink.value += text`
before dispatching `compositionend`.  A real IME does not write that line — the
browser does, as the default action of `beforeinput`/`insertCompositionText`,
which is not cancelable during composition.  Synthetic events run no default
action, so without it the buffer stays empty, the adapter's comparison
short-circuits, and finding 050 would be as invisible here as it was everywhere
else.

## What this run also found

The first attempt never reached any of the three checks: it failed at
`place-caret`, after 30 seconds, on the shipped artifact.  That is
[finding 051](../../../../051-the-caret-confirmation-refuses-the-bottom-half-of-every-line.md)
— the caret confirmation refused every click landing in the bottom half of its
own line — and it is fixed in the bundle these runs are bound to.

## Not covered here

* whether the OS clipboard actually received the text (WebDriver refuses
  clipboard access; that half is D5's)
* trusted input of any kind
* every product path that is not one of these three
