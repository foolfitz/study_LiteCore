# Prediction: finding 063's three properties, on a withheld action

STATUS: MEASURED 2026-08-26, both ways — see [`RESULT.md`](RESULT.md). All four criteria held on the shipped `e2-editor-v8`, and the `cut-swallows-the-refusal` mutation turned the check red on the term it moves. Everything below this line is the prediction as written on 2026-08-22 and is unedited.

Written 2026-08-22, **before** the arm was run and before the core rebuild it
is waiting behind finished. The queue item is
`queue-cut-refusal-lost-its-inducer`; the harness is
`tools/run_e2_c_product_path.py --refusal-diagnostic`.

## Why an arm exists at all

Finding 063: a **refused** cut used to send the session into
recoverable-error and tell the user to discard unsaved work, over an action
that had dispatched nothing. The fix was verified on every run by
`ctrl-x-is-handled-by-the-product`, because until 2026-08-22 the shipped
manifest declared `delete-selection` `["range-single"]` and this engine gates
an unclassified range on **both** bits — so every cut was refused and the
refusal was on the product's own path.

Widening the gesture made cut work and **took that state away**. The coverage
moved into the `cut-falls-back-to-the-caret-only-delete` mutation, which
asserts that a check goes RED — not that the refusal was reported, the
document left alone and the session kept alive. Third time in this tree that a
fix removed the state its own regression check needed (046's disposition,
038's inducer, now this).

## What this arm does, and what it deliberately does not

`--refusal-diagnostic` rewrites **one** field of the manifest in a symlink
mirror: the named action's `gestures` becomes `[]`. `dist/` is not written and
`probe.wasm` is byte-identical.

Empty rather than removed, on purpose. The engine initialises every entry to
all-permitted on the first mask call and intersects from there, so **deleting**
the action would ship it wide open — the opposite of the intent, and silent.
This is the same rule the shipped manifest obeys for `select-all`.

The route this produces is not an approximation of finding 063's, it is
finding 063's: `offers()` reads a present-but-empty gesture list as withheld,
so the page's cut handler falls back to `delete-backward` exactly as it did on
v3, and the engine refuses that on the range a cut necessarily has.

**Rejected alternative, and why**: driving `select-all`, which ships
`gestures: []` already. The product offers no control for it, so reaching it
needs a page that dispatches an action `offers()` says no to — test-only
behaviour welded into the product.

**Rejected alternative, and it was rejected by reading the code rather than by
taste**: a cut on a *collapsed* caret, which would dispatch `delete-selection`
against a caret-only gesture set and be refused on the shipped manifest, with
no mirror at all. It cannot happen: `clipboard-adapter.js:69` throws
`CLIPBOARD_EMPTY_SELECTION` before the delete is reached, and the handler's
ordering comment says that is deliberate — a failed copy must not still remove
the text. The refusal is unreachable that way.

## The criteria, fixed now

`a-refused-action-is-reported-and-changes-nothing` PASSES only if **all four**
hold on the same run:

1. `refusalReported` — a toast names the reason
   (`EDITOR_FORMAT_GESTURE_UNSUPPORTED`). A refusal the user cannot see is a
   refusal nobody reports.
2. `documentUnchanged` — the saved ODT's lines are what they were.
3. `stateAfterCut == "ready"` — the session did not go to recoverable-error.
4. `saveStillWorks` — the save after the refusal produced a readable ODT.
   063's actual harm was being told to discard unsaved work; a session that
   reports `ready` and can no longer save has failed 063 while passing a state
   check.

Anything else is a FAIL. `NOT_ESTABLISHED` is reserved for two preconditions
that are about the harness rather than the product: no `--refusal-diagnostic`
(no refusal exists to judge), and `clipboardGranted: false` (Firefox has no
CDP here, the copy half is denied by the driver, and the delete half never
runs).

## The positive control, and why it needs no extra driving

The term at risk is `documentUnchanged`: "nothing changed" and "nothing
happened" are the same observation, and this tree wrote that lesson down three
times on 2026-08-21 alone. The control is already in the net — the **same**
drive, on the **same** named line (`E1-LC-BETWEEN`), with the shipped
manifest, is `cut-removes-the-selected-text`, which requires that line to be
**gone**. One run of each says the document survived because the action was
refused, not because the drag missed or the key never arrived.

## What must go red

Mutation `cut-swallows-the-refusal` puts the discard back where finding 063
had it — inside the operation, where `run()` can no longer see the rejection,
so no toast is emitted. Expected: `refusalReported: false`, the check FAILS,
and `cut-removes-the-selected-text` stays `NOT_ESTABLISHED` (this arm withholds
the delete, so it is not scorable either way).

It is declared `requiresFlag: "--refusal-diagnostic"` and
`tests/test_product_path_mutations.py` now enforces that the flag exists. Run
without it the mutation changes no observable at all and would report "the
product survived it" — the reading a dead mutation gives, and the reason
`cut-swallows-its-failure` had to be replaced in the first place.

## Commands

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe

TMPDIR=/home/jiajun/.cache/litecore-probe-tmp setsid nohup \
  python3 tools/run_e2_c_product_path.py --browser chrome \
    --refusal-diagnostic \
    --out <path> > <log> 2>&1 < /dev/null &

# and the control that proves it can fail:
#   --refusal-diagnostic --mutate cut-swallows-the-refusal
```

Not run while the a11y gate 0 core build holds all twelve cores: this net has
timing-sensitive terms (`stable_bands`, the settle sleeps), and a measurement
taken against a loaded machine is a measurement of the machine.
