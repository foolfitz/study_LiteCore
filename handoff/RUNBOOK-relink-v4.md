# Runbook: the ABI 4 link (**the link command is the user's to run**)

Written 2026-08-22. Successor to
[`RUNBOOK-relink-v3.md`](RUNBOOK-relink-v3.md), whose structure this follows.

This link was **authorised by the user** ("好，連結吧", 2026-08-21). That
settles the timing question the proposal left open — `research/PROPOSAL-2026-08-21-abi-revision.md`
§5 argued for waiting until the a11y gate-0 rebuild made a bigger payload, and
the user decided otherwise. Nothing below re-litigates that.

A link mints a new identity. Prior verdicts do not become false; they stop
describing the product (finding 027's shape).

## What this link ships

A **successor profile**, `e2-editor-v4`. `e2-editor-v3` is not touched: its own
build and dist directories are untouched by these targets, and its four files
stay byte-identical.

| | what | id |
|---|---|---|
| move by line | up / down / home / end | 16–19 |
| delete-selection | the one new behaviour | 20 |
| select-all | **ships dark** — empty gesture list | 21 |
| redo | a document-level SDK operation | **no wire id** |
| a11y honesty | reports `core-built-without-accessibility` at compile time | — |
| 32,767 refusal | refuses an oversized tile before allocating | — |
| finding 068 | the worker stops dropping the engine's `editor-state` | — |

Finding 068's fix rides this link **for free and needs nothing done for it**:
half of it is in `sdk/sdk-worker.js`, the builder hashes whichever worker is in
the tree, and the other half already shipped in shell bundle v30. It was
verified in a mirror first — 5/5 against 2/7 before — which is the condition
for putting anything into an already-green payload.

Ids 1–15 are inherited verbatim. `tests/editor_abi_header_test.cpp` pins every
one of the twenty-one.

**Two ship withheld, and withheld is not absent.** The engine initialises every
gesture entry to all-permitted on the first mask call and intersects from there,
so an action omitted from the manifest ships *wide open*. Withholding means
`gestures: []` — present, mask 0. `tests/test_e2_editor_v4_profile.py` pins
that distinction; do not "tidy" a dark action out of the manifest.

## 0. Pre-link gates (all machine-decidable; all run 2026-08-22, all green)

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe

python3 tools/check_relink_queue.py          # 0 drifted, P1 complete: True, blocking: none
python3 tools/check_relink_queue.py --self-test
make test-e2-c-reachability                  # exit 0
make test-e2-c-static && make test-e2-b-static
python3 tools/check_product_build_reaches.py # unreachableInProductBuild: []
c++ -std=c++17 -Isrc -fsyntax-only tests/editor_abi_header_test.cpp
python3 -m unittest tests.test_e2_editor_v4_profile
node --test editor-shell-v2/tests/*.test.mjs # 61 pass
```

State at the time of writing: 46 queue items, 33 present, 13 open, **0 drifted,
P1 complete: True, blocking: none**. Shell bundle generation **v33**,
`debec482106d1a45…`. (The extra open item is
`queue-caret-does-not-follow-typed-text` — finding 068, fixed in source and
staying open until it ships and a product-path check can measure it.)

**Do not link on `p1Complete: False`** — that guard is what "missing one item
means a second relink" cost us. The only exception is a user decision recorded
in `e2/relink-queue-v3.json`'s `blocksRelink`, which shows up in a diff.

## 1. Archive: **check the right directory**

`dist/profiles/e2-editor-v3/` is not rebuilt by the v4 targets, so v3 needs no
fresh archive. But if you verify it, verify against the right one:

```bash
for f in probe.wasm probe.js sdk-worker.js sdk-manifest.json; do
  cmp build/archive/e2-editor-v3-29ec627b-worker-a9afbc01/$f \
      dist/profiles/e2-editor-v3/$f && echo "same  $f" || echo "DIFF  $f"
done
```

**Not `build/archive/e2-editor-v3-29ec627b/`.** That directory is named after
the shipped wasm hash and two of its four files are *not* what shipped; it
carries an `ATTRIBUTION.md` saying so. The lesson it encodes: a profile is five
bound identities, and an archive named after the wasm alone cannot tell apart
two profiles that share a binary.

## 2. The link (**this step is the user's to run**)

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v4/sdk-manifest.json
```

- `ALLOW_FROZEN_RELINK=1` is deliberate consent. Without it the Makefile
  refuses and prints what the artifact carries (`refuse_unasked_relink`). v4
  carries that guard **from its first link**, as v2 and v3 did, so no v4
  artifact ever appears by accident.
- The target is a file path, no alias. It links into `build/e2/editor-v4/` and
  `tools/build_e2_editor_v4_profile.py` packages it into
  `dist/profiles/e2-editor-v4/`.
- **No v2 or v3 target moves.**
- The builder prints the five identities plus `withheld: ["select-all"]`.
  If `withheld` comes back empty, stop: the dark action reached the manifest
  with gestures, and the mask cannot take back what a manifest granted.

## 2b. The shell is already waiting for it

Nothing in the shell needs editing on the day. Three capabilities were wired
ahead of the link and each gates itself on what the running profile declares,
so they light up when the manifest carries them:

- **arrow keys** — all six listed, each gated on `offers()`. On v3 Up/Down/
  Home/End fall through untouched (measured: not taken, `defaultPrevented`
  false, no error). Re-run `--arms arrow-keys-match-the-profile` afterwards:
  it reads the profile and will then *require* ArrowUp to move the caret, with
  no edit to the check.
- **redo** — a hidden 重做 button plus Ctrl+Shift+Z and Ctrl+Y, gated on
  `offersRedo()`. Hidden rather than disabled, because a disabled control
  promises a later moment that never arrives on a profile without redo.
- **cut** — dispatches `delete-selection` when the profile offers it, and
  otherwise falls back to today's behaviour rather than to an untested path.

Shell bundle **v33**, `debec482106d1a45…`. Finding 068's caret fix and
069's sink fix are in it too; 068's other half is the worker, which this link
hashes.

## 3. Immediately after the link, before any measurement

1. **Archive the new profile**, named with both the wasm and the worker hash,
   per §1's lesson.
2. **Point the product page and tools at v4.** These still say `e2-editor-v3`
   and were deliberately left alone so the tree stayed green while waiting for
   the link:
   - `web/e2-editor-app.js`
   - `tools/audit_product_path_coverage.py` (`BINDING_PROFILE`)
   - `tools/run_e2_c_product_path.py`
   - `tools/probe_a11y_gate0.py`, `tools/run_block_identity_link.py` (defaults)
   Historical references must NOT move: `e2/validation-matrix-v2.json`, the
   queue's notes, and everything under `findings/evidence/` record what was
   true of the v3 artifact.
3. **Mint shell bundle v30** for that page change (v29 is frozen).
4. Re-state all five bindings and re-run D0 in **both** browsers.

## 4. What the first run is for

The four movements, delete-selection and redo have **never run on a linked
artifact**. Their postconditions are asserted in the client, not measured:
movement by line borrows the character moves' postcondition because it takes
the same route through the engine (posted key event, `mutation = false`), and
delete-selection is filed with the UNO mutations because it dispatches
`.uno:Delete`.

If those assertions are wrong the client throws, loudly, on the first call.
**That is the measurement.** Do not soften an assertion to make the first run
green — the first run of a regression net is worth exactly what it is red about.

Two queue items stay `absent` on purpose and only a run can close them:

- `queue-cut-cannot-remove-text` — the engine half shipped; the item is that
  cut does not remove text, and its check now wants a product-path check named
  `cut-removes-the-selected-text`.
- `queue-no-select-all-action` — about the *shortcut*, not the id. The client
  must not bind a key to an action the engine refuses every time.
