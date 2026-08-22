# Handoff: ABI 4 is linked, measured, and the product path is green

> **SUPERSEDED** as the entry point by
> [`HANDOFF-2026-08-22b-cut-arrows-and-the-ime.md`](HANDOFF-2026-08-22b-cut-arrows-and-the-ime.md).
> Still the record of the link itself and of the five identities it
> minted. Note the correction block below: its claim about the vertical
> arrow keys was inherited from a check that means the opposite thing on
> the two artifacts, and the manifest it names (`f88c6289…`) has since
> been repackaged to `cbf93923…`.

Written 2026-08-22, after the link and its measuring round. Supersedes
[`HANDOFF-2026-08-22-the-oracle-was-the-defect.md`](HANDOFF-2026-08-22-the-oracle-was-the-defect.md)
as the entry point. The link runbook,
[`RUNBOOK-relink-v4.md`](RUNBOOK-relink-v4.md), is now history: its command has
been run.

## The artifact everything now binds to

`dist/profiles/e2-editor-v4/`, ABI 4, 21 actions.

| identity | value |
|---|---|
| `wasmSha256` | `f923cfa5aba30749…` |
| `loaderSha256` | `c382b834aa768b91…` |
| `workerSha256` | `e6ee92ca290b7966…` |
| `manifestSha256` | `f88c6289282bcd48…` |
| shell bundle | **v35**, `60bb0f1d79c2fa54…` |

Archived at `build/archive/e2-editor-v4-f923cfa5-worker-e6ee92ca/`, byte-identical.

**There is a second v4 archive and it is not a mistake.**
`…-worker-bc64be22/` is the profile *as it came off the link*. Finding 071 is a
defect **in that artifact**, so deleting it would delete the thing the finding
is about. The worker was fixed and the profile repackaged — no relink, the wasm
did not move — which is exactly why archive directories carry the worker hash
and not the wasm hash alone.

`dist/profiles/e2-editor-v2/` and `…-v3/` were verified byte-identical to their
own archives after the link, all four files each.

**Do not compare v3 against `build/archive/e2-editor-v3-29ec627b/`.** That
directory is named after the shipped wasm and two of its four files are not what
shipped; the faithful one is `…-29ec627b-worker-a9afbc01/`. It carries an
`ATTRIBUTION.md` explaining itself.

## What shipped, and what is deliberately dark

| | id | gestures |
|---|---|---|
| move-line up/down/home/end | 16–19 | `collapsed` |
| delete-selection | 20 | `range-single` |
| select-all | 21 | **`[]` — shipped dark** |
| redo | — | a document-level SDK operation, no wire id |

Plus: the 32,767 tile refusal, and accessibility honesty
(`core-built-without-accessibility` decided at compile time).

**`withheld: ["select-all"]` in the builder's output is the check that had to
pass.** An empty `withheld` would mean the dark action reached the manifest
with gestures, and a mask can never take back what a manifest granted.

## State: green

Product path (`tools/run_e2_c_product_path.py`, Chrome): **`ok: True`**, 34
checks, 3 NOT_ESTABLISHED and each one explained below. All static gates pass;
73 node tests; queue **0 drifted, P1 complete, blocking none**, 46 items, 12
open.

Working now that did not work before: **重做 and the caret keeping up with
typing** — both driven by a check on the linked artifact.

> **CORRECTION, same day.** This sentence also claimed ArrowUp/Down/Home/End,
> and that half was **not measured**. Every file under
> `findings/evidence/arrow-keys/` was run against `e2-editor-v3`, where
> `move-line-up` is `false`; the arm passes there because it asserts agreement
> with the running profile, and on v3 the agreeing behaviour is "the key does
> nothing". `backspace-and-arrows-reach-the-document` drives only the LEFT
> arrow (`◀ 35 ms`). So nothing has ever measured that the vertical arrows
> move the caret — the claim came from "the link gives them wire ids" plus a
> green check that means something else.
>
> **Then measured, same day.** The diagnostic arm re-run on v4 says
> `move-line-up: true` and ArrowUp moves the caret 2491 → 2457, taken by the
> page, with ArrowLeft holding as the control. And the regression net gained
> `the-vertical-arrows-move-the-caret`, which drives all four: End
> `left 132→509`, Home `509→80`, ArrowDown `top 250→272`, ArrowUp `272→250`,
> every one `defaultPrevented`. Its mutation `line-movement-keys-unbound`
> takes it PASS → FAIL with nothing else moving. The acceptance row is `done`,
> and the acceptance list is now 16 of 16 with no `partial` and no
> `unverified`.

## THE ONE THING IN FLIGHT

A measurement was **launched just before this handoff was written** and its
output will be sitting at:

```
/home/jiajun/.cache/litecore-probe-tmp/v4-range-delete-selection.json
```

Command, if it needs re-running:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 tools/run_e2_c_product_path.py --browser chrome \
  --range-delete-diagnostic --range-delete-action delete-selection \
  --out <path>
```

### What it is for

**Cut still cannot remove text, and the reason is a design conflict I created.**

The engine's gesture gate (`src/probe_engine.cpp:4471`):

```cpp
collapsed ? permitted(action, collapsed)
          : (permitted(action, range_single) && permitted(action, range_cross))
```

An unclassified range must satisfy **both** range bits. The engine cannot tell
single from cross without an html read, and that read is the wedge risk findings
037/038 describe, so it is conservative.

The v4 manifest grants `delete-selection` **`range-single` only** — I narrowed
it from the queue item's "range-single + range-cross", citing the rule against
declaring a gesture nobody measured. **Under this engine's semantics that
narrowing is an off switch**: delete-selection is unreachable on any range, so
cut falls back to `delete-backward`, which is caret-only, and is refused. The
run said so, not reasoning.

The diagnostic widens `delete-selection` to both range bits **in a mirror** —
`dist/` untouched, `probe.wasm` byte-identical — and asks what a range delete
actually does. **The user approved running it.** The decision it feeds:
whether to grant `range-cross` in the shipped manifest (repackage, no relink)
or to leave cut broken and say so.

Read it with the `rangeDeleteDiagnostic` block and the `ctrl-x-…` check's
`rangeDelete` observation.

## The three NOT_ESTABLISHED, each with a reason

- **`recovery-returns-what-the-product-promised`** — finding 072. Was PASS on
  v3. The inducer no longer wedges the engine because the harness aims from ink
  bands and a **correct caret** now sits in the gap between two of them, merging
  them. Mechanism settled; **remedy not found** (see below).
- **`notice-action-recovers-the-session`** — long-standing, finding 053's shape.
  Briefly FAILed while finding 071 hung the session; back to its v3 state.
- **`an-aborted-gesture-stops-selecting`** — long-standing on both browsers, and
  identical control observations before and after everything here. The harness
  cannot start a drag there.

## What the link found: four layers of the same lag

Each was a separate list of "what exists", each updated on its own, and **none
was reachable until a manifest offered the new actions**:

| layer | symptom |
|---|---|
| `narrow-editor-v2-client.js` `APPENDED` | updated when written |
| `NarrowEditorV2Session` `ACTIONS` | `EDITOR_ACTION_UNSUPPORTED` |
| the page's `editorAction()` label lookup | TypeError; key eaten, nothing dispatched |
| **`sdk-worker.js` reply dispatch** | **finding 071: the session hangs** |

The first three are loud. **The fourth is silent and breaks the most.**

The waiver that caught it was `action:redo`, registered in
`e2/product-path-coverage.json` with its reason **pinned to the v3
`manifestSha256`**. The moment the v4 artifact shipped that pin expired and the
audit demanded the path be driven. A reason written without a binding would
have survived the link in silence.

## Findings opened or changed today

- **068** — the caret. Claim changed **three times**; the final one is that the
  page's `getState()` is answered one callback before the cursor callback and
  nothing asks again, because the worker dropped the engine's `editor-state`
  announcements on product profiles. Fixed (worker + a `NarrowEditorV2Session`
  override) and **verified on the linked artifact**, 3/3.
- **069** — `#sink` had `position: absolute` with no `top`/`left`, so it sat at
  the bottom of a full-document-height canvas and every IME composition scrolled
  the desk there. Fixed: the sink rides the caret. **Side effect worth knowing:
  the caret's position is now a DOM observable**, which is what
  `caret-follows-the-text-you-type` reads.
- **071** — redo hung the session (above). Fixed.
- **072** — a correct caret moved the harness aim. **Open: mechanism settled,
  remedy not found.**

## Open work, in the order I would take it

1. **Read the range-delete measurement** and decide on `range-cross` for
   `delete-selection`. This is the only thing between the product and a working
   cut, and it closes `queue-cut-cannot-remove-text`.
2. **Finding 072's remedy.** The thing to filter is a **column**, not a run of
   rows: a caret is a vertical line crossing many rows, one or two columns wide.
   That means dropping such columns from the scan **before** row counts are
   aggregated — and `scan` currently exposes only `counts`/`firsts`/`lasts`,
   already aggregated per row. **So it is a change on the scanning side, not in
   `text_bands()`.** My first attempt filtered row-runs and did nothing; see
   below.
3. **a11y gate 0** — `tools/probe_a11y_gate0.py` **refuses to run**, correctly:
   the core build still sets `ENABLE_WASM_STRIP_ACCESSIBILITY=1`, so there is
   nothing to measure. It declines rather than producing a number about a patch
   not having been applied. Needs the user to apply
   `handoff/a11y-gate-0/PATCH.md` and rebuild core.
4. **`queue-no-select-all-action`** stays absent by design. Granting select-all
   later costs a measurement of what `.uno:SelectAll` does here, not another
   link.
5. **Ask the operator to look**, at 8792 or their own server (both serve v4
   now). Nobody has looked at the arrow keys, 重做, or the sink fix with their
   eyes; every "it works" above is a machine reading.

## Mistakes I made today, because they are the cheap part to inherit

**Do not repeat these.**

1. **I gave the user half a fix to test.** 068's session half was in `dist/`
   and its worker half was in the frozen v3 profile, so they tested "the
   listener is installed and nobody is broadcasting" and saw no change. Before
   handing anything to a person, **check the bytes they will open**. The remedy
   was a mirror plus a **visible banner naming the build** — "which one did you
   test" should never be a guess.
2. **My harness path was not the user's path.** `commit()` drives the product's
   insert field and button; a person types into the sink. Both end at
   `document.insertText` and the difference is everything *around* it. 5/5 green
   and the operator saying "no change" were both true.
3. **I attributed an intermittent failure from two runs.** I said my failed 072
   remedy broke two checks; it did not — they were flaky, and the cause was
   another change I made in the same batch. **Two runs is one sample.**
4. **Seven passing unit tests and a remedy that did nothing.** They tested that
   a thin standalone run is excluded. That behaviour was real. It was not what
   happens here. **A test can verify a behaviour perfectly and be about the
   wrong thing.**
5. **I reverted a mutation with `git checkout` on a file whose real changes were
   uncommitted**, and lost them. Caught only by comparing sha256 before and
   after. Use a backup copy.

## Commands

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make test-e2-c-static && make test-e2-b-static && make test-e2-c-reachability
python3 tools/check_relink_queue.py && python3 tools/check_relink_queue.py --self-test
python3 tools/check_e1_c_bundle_intact.py
node --test editor-shell-v2/tests/*.test.mjs

# the product path -- ~15 min, and it gets KILLED if backgrounded the ordinary
# way. Detach it:
TMPDIR=/home/jiajun/.cache/litecore-probe-tmp setsid nohup \
  python3 tools/run_e2_c_product_path.py --browser chrome --out <path> \
  > <log> 2>&1 < /dev/null &

# serving the product: dist IS v4 now
python3 web/serve.py --port 8791
```
