# Handoff: the acceptance list is 16 of 16, and three green checks meant nothing

Written 2026-08-22, after the ABI 4 link's measuring day and the operator round
that followed it. Supersedes
[`HANDOFF-2026-08-22-abi-4-is-linked-and-measured.md`](HANDOFF-2026-08-22-abi-4-is-linked-and-measured.md)
as the entry point; that document is still the record of the link itself and of
the five identities, and its correction block is worth reading.

## State

| | |
|---|---|
| product path | **`ok: True`**, **36 checks**, 2 NOT_ESTABLISHED |
| acceptance list | **16 of 16 `done`** — no `partial`, no `unverified`, no `blocked` |
| relink queue | 48 items, 13 open, **0 drifted**, P1 complete, blocking none |
| shell bundle | **v36**, `23163eb6c97a1083…` |
| profile | `e2-editor-v4`, wasm `f923cfa5…`, manifest **`cbf93923…`** |

All static gates pass: `test-e2-c-static`, `test-e2-b-static`,
`test-e2-c-reachability`, the queue self-test (14/14), the E1-C bundle guard,
73 node tests.

**An operator has now looked at all of it with their own eyes** and confirmed
every item, including the one they found broken (below).

## The artifact moved, and only one of its five identities did

`delete-selection` shipped from the link with `gestures: ["range-single"]`.
That is **not** a narrower grant. `probe_engine.cpp` gates an unclassified
selection on `range_single AND range_cross`, because it cannot tell the two
apart without an html read and that read is the wedge risk findings 037/038
describe. One bit refuses **every** range.

So from the link until today the engine refused every cut with

```
this action is not offered for this kind of selection in this profile
```

— a sentence that was true of no selection at all. A manifest declaring a
gesture the binary will never honour is the "describes but does not constrain"
defect pointing the other way, and it is worse than either extreme because it
reads as a deliberate narrowing.

Widened on a pre-registered measurement. Repackage only, no relink:

| | |
|---|---|
| `wasmSha256` | `f923cfa5aba30749…` unchanged |
| `loaderSha256` | `c382b834aa768b91…` unchanged |
| `workerSha256` | `e6ee92ca290b7966…` unchanged |
| `manifestSha256` | `f88c6289282bcd48…` → **`cbf9392311fac92a…`** |

Archived at `build/archive/e2-editor-v4-f923cfa5-worker-e6ee92ca-manifest-cbf93923/`.
**The directory name grew a third hash on purpose**: the old rule (wasm +
worker) would have produced a name that already exists, and writing it would
overwrite a generation. Its `ATTRIBUTION.md` says so, and explains why both
earlier v4 archives are kept.

**The builder was run directly, not through `make`.** The Makefile had been
edited in the same session, so `make` would have judged `probe.js` stale and
tried to link. The recipe's command is in the ATTRIBUTION and in
`findings/evidence/queue-cut-cannot-remove-text/RESULT-range-cross.md`.

`withheld: ["select-all"]` still holds. That is the check every repackage has
to pass — a mask can never take back what a manifest granted.

## What the measurement said

Predictions were written 2026-08-21, before any of it ran
([`PREDICTION.md`](../findings/evidence/queue-cut-cannot-remove-text/PREDICTION.md)).

P-CUT-1/2/3 held. P-CUT-4 carried **no** prediction by design and was measured
on **four** shapes, not one — because finding 046 was a multi-block readback
verifying the wrong paragraph, and list items are what a cross-block selection
runs into:

| shape | lines | untouched | session | document |
|---|---|---|---|---|
| heading into body | 9 → 8 | verbatim | ready | readable |
| three paragraphs into a bullet list | 9 → 7 | verbatim | ready | readable |
| bullet list → plain → numbered list | 9 → 5 | verbatim | ready | readable |
| within one bullet list | 9 → 8 | verbatim | ready | readable |

Every arm merged the way a word processor does — head of the first paragraph,
tail of the last — and the line count fell by exactly the number of boundaries
crossed. Across three runs the shipped checks moved in **one** place, and that
place was this measurement's own obsolete oracle.

This also **vindicates the ABI 4 design by measurement rather than by
argument**: the 2026-08-21 arm widened `delete-backward` and hit the selection
barrier (`EDITOR_STATE_UNAVAILABLE`, recoverable-error, save refused).
`delete-selection` dispatches `.uno:Delete` plainly and deliberately, and it is
clean on all four shapes.

Still uncharacterised, and named in the manifest's `limits` rather than implied:
a range **inside a table**, and one covering a **note reference mark**. Neither
is in this fixture. The gate is binary, so measuring them changes what is
known, not what is granted.

## Three green checks that meant nothing, and they are the real content

**1. A mutation that could not be applied.** `cut-swallows-its-failure` named
`session.action("delete-backward", {})` inside the cut handler; the link
replaced that line with a ternary. Its pattern matched `dist/` **zero** times.
`apply_mutation` fails loudly on that — but only for somebody who runs it, and
nobody did between the link and the day it was noticed. A mutation is a check's
only proof it can go red.
Replaced by `cut-falls-back-to-the-caret-only-delete`, and the whole sweep is
now a **static gate**: `tests/test_product_path_mutations.py` checks all 38
patterns still apply, that no `find` equals its `replace`, and that every
`mustGoRed` names a check id something emits.

**2. A check that is green whichever way the world is.** The acceptance row for
line movement sat at `blocked` through the link and then read as satisfied,
because `arrow-keys-match-the-profile` was PASSing. Every file under
`findings/evidence/arrow-keys/` was run against **`e2-editor-v3`**, where
`move-line-up` is `false` — and that arm asserts *agreement with the running
profile*, so on v3 the agreeing behaviour is "the key does nothing". The same
green means the opposite thing on v4. `backspace-and-arrows-reach-the-document`
drives only the **left** arrow.

So four of six arrows shipped, were believed to work, and were driven by
nothing. Now measured on v4 (`move-line-up: true`, ArrowUp 2491 → 2457, taken
by the page, ArrowLeft holding as control) and covered by
`the-vertical-arrows-move-the-caret`:

```
End        left 132 -> 509   top 250 -> 250   taken
Home       left 509 ->  80   top 250 -> 250   taken
ArrowDown  left  80 ->  80   top 250 -> 272   taken
ArrowUp    left  80 ->  80   top 272 -> 250   taken
```

The oracle is **inverses**, not "each moved something": two keys travelling the
same way each pass a did-it-move test. Every key must also come back
`defaultPrevented` — on v3 ArrowUp came back `false` with no error, so without
that term "the page never bound this key" and "it bound it and could not act"
read identically. Mutation `line-movement-keys-unbound` takes it PASS → FAIL
with nothing else moving.

**3. A predicate that a page doing nothing satisfies.** Found by running that
mutation, not by foresight: `downAndUpAreInverses` is `up.topAfter ==
down.topBefore`, and under the mutation both presses leave the caret at row 250,
so it reads **green while all four keys are dead**. It is carried by the
conjunction, so the check still fails — but it is written down rather than left
to hold by luck. **I have no mechanical way to find others of this shape yet.**

## Finding 073: the operator found the one thing that was broken

Everything on the manual checklist passed except one: typing Chinese with 新酷音
showed **nothing** — no bopomofo, no candidate window — until the character
committed.

The mechanism is structural. `#sink` is a `width: 1px; opacity: 0` textarea,
and the browser draws an IME's **preedit inside it**. There were no
`compositionstart`/`compositionupdate` handlers anywhere in the page:
composition was entirely the browser's until `beforeinput` delivered the
result, and that half had always worked.

It is **not** finding 005. That was Qt5's wasm plugin registering no composition
events at all, so text never arrived. This sink is the *remedy* for that class
of problem — and the remedy solved "the text arrives" and left "you can see what
you are typing" to nobody.

Fixed: visible while composing, back to one transparent pixel after. The font
size is derived from the caret's own height (which finding 069 already pinned to
the engine's cursor rectangle), the width from a **detached** measuring canvas,
and **both endings are wired** — `compositionend` and `blur`. The second is the
one that gets forgotten, and a sink left visible is a box of stale text on top
of the document, which is worse than the defect.

**And it turned out not to be human-only.** CDP's `Input.imeSetComposition`
drives the renderer's own IME path, so composition events fire for real:

| | opacity | width | left | top | value |
|---|---|---|---|---|---|
| at rest | 0 | 1 | 132 | 250 | `""` |
| composing | **1** | **38** | 132 | 250 | `ㄊㄞˊ` |
| after | 0 | 1 | 132 | 250 | `""` |

Both ends are checked and the position must not move. The positive control is
whether the composition started at all. Mutation `composition-never-shown`
reddens it.

**The lesson is the reusable part**: "only a human can do this" is a
*falsifiable claim*, not a category. IME was filed under D5-by-definition, which
is true of a real input method and does **not** imply that composition
visibility cannot be measured. The missing step was looking for an instrument.

One thing is **not** measured and the finding says so: the candidate window is
the input method's own OS-level window, and this harness can read the sink's
geometry but not where fcitx paints. The operator confirms it now appears; the
plausible mechanism is the same one, but that is inference, not measurement.

## What automation cannot see, still

The coverage audit caught the three new composition listeners and failed the
build until they were registered — the gate working. It did **not** catch the
fourth listener in the same edit (`blur` on `#sink`), because it keys on the
**event name** and `listener:blur` was already registered for a different
handler on a different element. The granularity is the hole, not the entry.
Recorded as `queue-coverage-audit-keys-on-the-event-name`, with the remedy
(key on target+event; the parser already sees them as distinct text) and why it
was not done in the same commit.

## What widening cost

`queue-cut-refusal-lost-its-inducer`. Finding 063 — a refused cut used to send
the session into recoverable-error and tell the user to discard unsaved work
over an action that had dispatched nothing — was verified on every run by the
old cut check. Granting the gesture removes the refusal from the product's path,
so that check could no longer be about it. The refusal now lives only in a
mutation, which asserts a check goes red rather than asserting finding 063's
three properties.

**Third time in this tree that a fix removed the state its own regression check
needed** (046's disposition, 038's inducer, now this). Two candidate routes are
in the queue item; the cheaper reuses the `--range-delete-diagnostic` machinery
to *narrow* an action in a mirror and assert 063's properties there.

## Open work, in the order I would take it

1. **a11y gate 0** — the only thing blocked on the user.
   `tools/probe_a11y_gate0.py` correctly **refuses to run**: the core build
   still sets `ENABLE_WASM_STRIP_ACCESSIBILITY=1`, so there is nothing to
   measure and it declines rather than producing a number about an unapplied
   patch. Needs `handoff/a11y-gate-0/PATCH.md` applied and core rebuilt. The
   patch names the ordering trap that would otherwise waste a rebuild.
2. **`queue-cut-refusal-lost-its-inducer`** — restore finding 063's coverage
   without breaking the product to do it.
3. **`queue-coverage-audit-keys-on-the-event-name`** — mechanical, bounded, and
   it protects a class this tree has been bitten by three times.
4. **Table and note-apparatus ranges for `delete-selection`** — named limits
   today; measuring them changes what is known, not what is granted.
5. **`queue-no-select-all-action`** stays absent by design. Granting select-all
   costs a measurement of what `.uno:SelectAll` does here, not a link.

## Commands

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe

make test-e2-c-static && make test-e2-b-static && make test-e2-c-reachability
python3 tools/check_relink_queue.py && python3 tools/check_relink_queue.py --self-test
python3 tools/check_e1_c_bundle_intact.py
python3 tools/build_e2_c_shell_bundle.py     # must report problems: []
node --test editor-shell-v2/tests/*.test.mjs
python3 -m unittest tests/test_ink_rows_caret.py tests/test_product_path_mutations.py

# the product path -- ~15 min, and it is KILLED if backgrounded the ordinary
# way. Detach it:
TMPDIR=/home/jiajun/.cache/litecore-probe-tmp setsid nohup \
  python3 tools/run_e2_c_product_path.py --browser chrome --out <path> \
  > <log> 2>&1 < /dev/null &

# the four cross-paragraph arms run ONLY under this flag, and last:
#   --range-delete-diagnostic --range-delete-action delete-selection
# finding 072's remedy can be turned off to reproduce the merged band:
#   --no-caret-exclusion

# serving the product: dist IS the widened v4
python3 web/serve.py --port 8791
```

## Two operational notes

**`/tmp` is a 16 GB tmpfs and it filled during this session**, to the point
where the Bash tool's own output could not be written. It was not this
project's doing — `/tmp/claude-1000/adr0066-review` alone was 3.6 GB. The
workaround, if it happens again: write every command's output to
`~/.cache/litecore-probe-tmp/` and read it back.

**Finding 072's remedy is in and verified**: `bandsAtInducer` is back to the v3
numbers exactly (`[83,95] [106,120] [130,143] [1000,1018]`) and
`recovery-returns-what-the-product-promised` went NOT_ESTABLISHED → PASS. Its
second version was stopped by an adversarial review that showed it would have
declined on the real page ~40% of the time and that its seven unit tests could
never have shown that — the fixture drew the caret as two columns of pure black,
while the real one is **one** nominal backing pixel at fractional coordinates,
and both defects lived entirely in that difference. The fix was small: take the
solidity ratio over the **interior** rows only.
