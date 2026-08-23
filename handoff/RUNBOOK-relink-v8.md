# Runbook: finding 076's link (**the link command is the user's to run**)

Written 2026-08-24. Successor to [`RUNBOOK-relink-v4.md`](RUNBOOK-relink-v4.md),
whose structure this follows.

Authorised by the user on 2026-08-24 ("076 的 relink"). A link mints a new
identity. Prior verdicts do not become false; they stop describing the product
(finding 027's shape).

## What this link ships — measured, not read

`tools/what_the_link_ships.py --since eab775c` preprocesses the product's four
translation units with the product's own defines at the shipped commit and at
the working tree, and diffs them. Result, kept at
`findings/evidence/f076-what-the-link-ships/`:

| unit | verdict |
|---|---|
| `sdk_api.cpp`, `unoembind_stub.cpp`, `editor_api.cpp` | preprocess identically |
| `probe_engine.cpp` | **two hunks** |

### 1 and 2. The engine

1. **Finding 076** — `std::malloc(byteCount)` → `std::calloc(byteCount, 1)` for
   the tile pixel buffer. `paintTile` draws only the page and `putImageData`
   blits the whole buffer, so uninitialised heap reached a canvas the user can
   screenshot. The operator confirmed seeing it.
2. **`queue-fresh-is-true-where-no-read-can-succeed`** — an early return in
   `refreshCaretParagraph()` so `a11yParagraphFresh` is false on a build where
   no accessibility read can succeed.

**Two, not one.** Reading the `#ifdef`s would have found only the first: hunk 2
is gated on a *runtime* flag on purpose, so it is behind no `OXSDK_A11Y_*` and
does reach the product build. It is wanted; it is named here so nobody discovers
it afterwards.

Everything else added to the engine since `eab775c` — 153 lines across five
commits — is accessibility work behind `OXSDK_A11Y_*`, which this build does not
define, plus `a11y_tree_probe.cpp`, which is not in `E2_V4_OBJECTS` at all.

### 3. The worker, and it is not the engine's story

`sdk-worker.js` moves `e6ee92ca290b7966` → `070229cd10bda4a0`: **+93 lines, 21 of
them code.** The profile builder hashes *whichever worker is in the tree*, so a
link ships every accumulated worker change too. The v4 runbook already knew —
"finding 068's fix rides this link for free" — and the first version of
`what_the_link_ships.py` still answered as if the engine were the whole story,
until a dry packaging run showed `workerSha256` moving under it.

The 21 code lines forward `a11y.paragraphText` as `text` and `a11y.outline` as
`documentOutline`, plus those two on two event payloads. All additive, all
presence-guarded.

**Expected to be inert on this core — and that is a derivation, not a
measurement.** The product core emits neither field, so both project as `null`,
and v8's manifest declares neither `caretParagraphText` nor `documentOutline`, so
the page does not read them. §4 is where that gets checked.

**The tree's worker ships rather than v7's being pinned**, deliberately: it is
the maintained source of truth (`check_e2_b_inventory.py` and the E2-B tests read
it), and pinning an old copy would make source and dist diverge permanently so
that the *next* link ships the divergence with less scrutiny than this one gets.

**Same core.** `e2-editor-v8` links against the product core via
`link_r5_product`, exactly as v4 does. Only the v5 lineage names
`../wasm-lite/build-a11y-gate0`, and nothing here touches it.

## The identity

`e2-editor-v8`, with its own `build/e2/editor-v8/` and
`dist/profiles/e2-editor-v8/`. Nothing in the v2/v3/v4/v5 lineage moves.

**v4 and v7 must both stay byte-identical.** v4 carries round two's verdict; v7
is v4's artifact under the wider manifest and is what ships today. Relinking
either would unbind both, since they share three of their four hashes.

The v8 rules are a **copy** of v4's with one directory changed, not a refactor
into a shared template. A template both artifacts share is a thing that can be
edited once and change two artifacts, one of which is bound to a verdict.

### The manifest inherits v7's gestures, and that is not a widening

The recipe passes `--inline-range-gestures all`. That is what `e2-editor-v7`
already ships: characterised on the minted identity itself (four formats × two
selection shapes, formatted text equal to selected text, native LibreOffice
writing the same shapes) and confirmed by the operator with a real mouse —
finding 078.

**Omitting it would narrow the product on the day of a link that has nothing to
do with gestures**, which is 078 reintroduced. `check_gesture_offers.py`
compares against `e2/expected-gesture-offers.json`, kept outside the manifest,
so a narrowing fails rather than passing quietly.

Both range bits or neither: for a selection the engine has not classified it
requires both, so granting one alone admits nothing. It cost three minted
profiles to find that.

## 0. Pre-link gates — all run 2026-08-24, all green

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe

python3 tools/check_relink_queue.py            # 0 drifted, P1 complete: True, blocking: none
python3 tools/check_relink_queue.py --self-test
python3 tools/check_product_build_reaches.py   # ok: true
c++ -std=c++17 -Isrc -fsyntax-only tests/editor_abi_header_test.cpp
python3 -m unittest tests.test_e2_editor_v4_profile   # 11 tests
node --test editor-shell-v2/tests/*.test.mjs          # 83 pass
make test-e2-c-static && make test-e2-b-static && make test-e2-c-reachability
python3 tools/what_the_link_ships.py --since eab775c   # 3 identical, 1 changed
```

State at the time of writing: **56 queue items, 41 present, 15 open, 0 drifted,
P1 complete: True, blocking: none.** Shell bundle generation **v40**,
`d8720b8b7281a8cf`.

**Do not link on `p1Complete: False`.** That guard is what "missing one item
means a second relink" cost us.

## 1. Archive — done 2026-08-24, before the link

`build/archive/e2-editor-v7-f923cfa5-worker-e6ee92ca-manifest-75aca740/`, with
`SHA256SUMS` and an `ATTRIBUTION.md`, verified byte-for-byte against
`dist/profiles/e2-editor-v7/`.

**The manifest hash is in the name on purpose.** v7 shares its loader, wasm and
worker with v4 and differs only in the manifest, so an archive named after the
wasm alone cannot tell the two apart. The neighbouring
`…-manifest-cbf93923/` is v4's. Both are correct; they are different profiles.

## 2. The link (**this step is the user's to run**)

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v8/sdk-manifest.json
```

- `ALLOW_FROZEN_RELINK=1` is deliberate consent. Without it the Makefile refuses
  and prints what the artifact carries. v8 carries that guard **from its first
  link**, as every predecessor did, so no v8 artifact ever appears by accident.
- The target is a file path, no alias. It links into `build/e2/editor-v8/` and
  packages into `dist/profiles/e2-editor-v8/`.
- **No v2, v3, v4, v5 or v7 target moves.**
- The builder prints the five identities. **`withheld` must come back
  `["select-all"]`.** If it is empty, stop: the dark action reached the manifest
  with gestures, and a mask cannot take back what a manifest granted.

## 3. Immediately after the link, before any measurement

1. **Archive the new profile**, named with the wasm, the worker *and* the
   manifest hash, per §1's lesson.
2. **Re-state the five identities** and record them.
3. **Point the product page at v8 — both lines together.** `workerUrl` **and**
   `PINNED_WASM_SHA256` in `web/e2-editor-app.js`, and the copy in `dist/`.
   Unlike the v7 cutover, **the pin does move this time**, because the artifact
   does. A page with one and not the other runs an engine its evidence does not
   describe; the expiry screen exists to make that loud.
4. **Point the tools at v8**: `tools/audit_product_path_coverage.py`
   (`BINDING_PROFILE`), `tools/run_e2_c_product_path.py`, and
   `e2/expected-gesture-offers.json`'s `profile` field — that last one names
   which profile the expectation is about; **its `expected` map must not
   change**, and if it has to, the manifest is wrong.
   Historical references must NOT move: `e2/validation-matrix-*.json`, the
   queue's notes, and everything under `findings/evidence/`.
5. **Freeze shell bundle v41** for the page change (v40 is frozen).
6. Re-run `make test-e2-c-static`, then the product path with no `--profile`.

## 4. What the first run is for

**Finding 076 has never been measured on a linked artifact.** The `calloc` fix
is a syntax-checked source change and nothing more; the two `-fsyntax-only`
passes recorded in the finding prove it compiles, not that the canvas is clean.

The measurement to take first, because it is the one the user can see: the
off-page region of the canvas, with `tools/capture_canvas_edges.py` — the same
instrument that produced finding 075's table, so the numbers are comparable.

**An earlier draft of this section said "after `calloc` the off-page region must
be uniformly zero". That criterion is wrong and would have misread the result.**
075's own table shows the shipped v4 core at **21,563 of 26,941** off-page pixels
with `alpha == 0` and **33–47 distinct alpha values** — while `alpha > 128` and
the ink count are both **0**. So the shipped core was never uniformly zero
off-page, and whatever produces those non-zero-but-transparent values is not the
`malloc`'d buffer (the likeliest candidate is edge interpolation from
`layoutCanvas`'s proportional scaling, which is not measured here and is not
claimed). A criterion of "uniformly zero" would have gone red on a correct
build.

The honest criterion is the comparison: on v8, off-page `alpha > 128` and the
ink count must both stay **0**, and nothing may be worse than the archived v4
row.

Note the asymmetry before quoting it: the visible symptom was measured on the
**a11y** core, and v8 is the **product** core, where the same region already read
as transparent. So a clean v8 canvas does **not** by itself demonstrate that the
user-visible noise is gone — it demonstrates the mechanism is closed. The a11y
lineage needs its own link to make that claim, and that is a separate decision.

**The worker's two added fields must project as `null`** and the manifest must
declare neither `caretParagraphText` nor `documentOutline`. That is the §"third
thing" derivation turned into a check; if either field arrives non-null on the
product core, something is emitting what this core was built without.

`queue-fresh-is-true-where-no-read-can-succeed` is the other half: on the product
core `gEditorAccessibilityEnabled` is false, so `a11yParagraphFresh` must now
read false where it previously read true with a zero-length fingerprint. The
product page's accessibility region already says why it is empty; the check
`the-document-region-says-why-it-is-empty` holds it to that.

**Do not soften an assertion to make the first run green.** The first run of a
regression net is worth exactly what it is red about.

## 5. Two queue items close only on a run

- `queue-tile-buffer-is-not-zeroed` — the source check passes today; the item is
  about what the product does, and only a linked artifact can answer.
- `queue-fresh-is-true-where-no-read-can-succeed` — same shape.

Both are `expectation: present` and `blocksRelink: false` already.
