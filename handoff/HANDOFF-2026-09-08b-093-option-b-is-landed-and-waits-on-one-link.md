# Handoff, 2026-09-08 — 093 option B is landed in source and waits on one link the owner runs

Written when the owner's usage ran out. Entry points, in order: this file, then
`handoff/RUNBOOK-operator-093-engine-geometry.md` (zh-TW, its reader is the
owner, and its step 4 is the only thing left that a person must do), then
`findings/093-*.md` — read it whole, the rulings are appended in order at the end.

Tree at `a36cbc5e`, clean, nothing pushed. `make test-e2-c-static` exit 0.

## Where this stands in one paragraph

The owner's T4 manual round found a defect nine clean automated runs had not:
arrow-key browsing drags the viewport to the bottom of the page and the editor
becomes unusable. Root cause is in shared bytes (`#a11y-doc` is absolutely
positioned with no `top`/`left`, so it sits at the bottom of the paper — 069's
defect, on the element 069 did not fix). The owner ruled **D-c** (fix it
regardless of classification; the soak count restarts) and then, when
measurement showed the cheap fixes do not work on a real document, ruled **B**
(give the engine real per-paragraph geometry). Steps 1–3 of option B are done.
**Step 4 — the link — is the owner's, is now runnable, and has never been run.**

## Step 4, the only thing waiting on a person

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v13/sdk-manifest.json
```

**Never run bare `make`.** Every `.o` in this tree has been stale for a long
time: the baseline `make -n` for *every* existing profile target shows 5–6
`em++`. What actually holds those artifacts still is the `refuse_unasked_relink`
guard, **not** make's dependency graph. A bare `make` would relink everything,
and a wasm hash is not a function of its source (finding 036), so those artifacts
would not come back.

Before: `make -n … | grep -c 'em++'` must be **6** (five TUs plus the link), every
`-o` under `build/e2/e2-editor-v13/`. Record the three hashes below. After: check
all three are unmoved, and expect six data-pack files under v13.

| profile | `probe.wasm` sha256 (first 16) |
|---|---|
| `e2-editor-v8` (shipping) | `4a2710bba1ef07d9` |
| `e2-editor-v10` | `4ec1e389aaab3b03` |
| `e2-editor-v12` | `4ec1e389aaab3b03` |

v10 and v12 share a hash because **v9, v11 and v12 were never linked** — their
Makefile rules repackage an archived artifact with different flags, workers and
manifests. v12 had no rule at all. That is why step 4's target did not exist and
had to be written (`a36cbc5e`): option B changed engine source, so it needs the
first real compile-and-link since the a11y build.

Two things nobody knows, stated rather than guessed: **the wall-clock cost of the
link is recorded nowhere in this tree**, and **the link itself has never run** —
symbol resolution was established by set-differencing the TU's undefined symbols
against 170 archives, leaving the same 44 libc/libc++/emscripten symbols that
were unresolved for the TU which did link into v10. That is strong, but archive
member selection, `--wrap`, duplicate definitions and link order are invisible to
it. **A link failure here is an anticipated risk, not a mistake.**

## What is in the tree that was not there yesterday

* **Engine** (`src/a11y_tree_probe.cpp`): the outline walk queries
  `XAccessibleComponent`, and converts with
  `pDev->PixelToLogic(rect, MapMode(MapTwip))` on the device the bounds came
  from. **No `/96`, no pixels-per-twip constant anywhere** — it asks the device
  to invert its own transform, so it is right whatever the wasm device's DPI
  turns out to be. Step 1 measured DPI 96 on the *native* device and deliberately
  did not carry that number across. Unreadable bounds emit nothing, never zeros.
* **Worker allowlist** (`sdk/sdk-worker.js`): four fields, `null` when absent.
  Omitted means unreachable, so this is load-bearing.
* **Builder** (`tools/build_e2_editor_v4_profile.py`): `--document-outline-geometry`,
  **off by default**, separate from `--document-outline`.
* **Page** (`web/e2-editor.html`, `e2-editor-app.js`): `#a11y-doc` gets
  `top:0;left:0;height:100%`, children carry the clip, `positionProjection()`
  places each node at its paragraph's twips. **Geometry is not in finding 088's
  `signature`** — placement is a separate pass, plus a call from `layoutCanvas()`.
* **The 41st check**, `the-projection-is-placed-where-the-document-is`, with two
  `MUTATIONS` entries. This moves the clean-run predicate from 38 PASS / 2 NE to
  **39 / 2**. AGENTS.md §9's four conditions are appended to
  `PLAN-2026-08-28-the-v11-cutover-horizon.md` (append only) so the owner can
  audit or reverse it before the link.
* **Shell generation v49** was frozen, because `dist/` must match `web/` or the
  freeze guard refuses. **Consequence to know: until the link lands, the page
  behaves like shape S1** — pinned to the top instead of the bottom. By the
  oracle that is the same 0/3 as unfixed, but the visible behaviour has changed.
* **`e2-editor-v12` is archived at last**
  (`build/archive/e2-editor-v12-4ec1e389-worker-03f5b69a-manifest-27342293/`, ten
  files, `sha256sum -c` all OK). Its `ATTRIBUTION.md` says plainly that it was
  taken **late** and protected nothing before this date. The candidate page's
  bytes are pinned by reference to git blob `000a57e2` — the premature-cutover
  commit, which now serves as their permanent record.

## The soak, and a discrepancy that must not be lost

**No soak run has been taken since run 08 on UTC 2026-09-07**, and none should be
until after the link — the identity is about to move again.

`check_soak_bank.py` currently reports `cleanRuns: 6, every-run-clean: true`.
**That number is stale, and the ruling contradicts it.** D-c declared the count
zero (`ed1ea02a`); the judge still counts six because its `DEFAULT_SHA` still
pins `9b29e39b…`, and the six banked runs match that pin. The live candidate page
is now `db2ed393f3433e2e64398234563e2e5a5ba12daaab1abc849ad1f6c9c726d5d6`.

The discrepancy resolves itself when the pins move after the link. But the order
matters and was measured: **emptying the bank breaks `check_soak_bank.py
--self-test`** (it builds its fixtures from banked clean reports), so the void-move
of the six 2026-09-07 runs must follow the **first post-link clean run**, not
precede it. Do not move them early to make the number look right.

## After the link — the first things to do, in order

1. Re-check the three artifact hashes above are unmoved.
2. Run the pinned oracle: `findings/evidence/093/ORACLE-fix-shape.md` (commit
   `8edd7cf8`, written before the probe existed), instrument
   `tools/probe_093_fix_shape_oracle.py`. Target: **3/3 on both arms of the
   133-paragraph document.** S3′ already reached that; B must at least match.
3. **Check that clause C3 of the new check actually executed.** It has never run
   — it is only reachable when geometry is really delivered, and the check
   reports `clausesExercised`. A green that never exercised its own clause is the
   failure mode this tree names by name.
4. Only then: move the pins, take the first clean run, and then move the six void
   runs aside.

## Still unmeasured, and one of them carries everything

* **Whether a screen reader's browse cursor is what drives the scroll in
  practice.** Every verdict in 093 comes from a probe calling `scrollIntoView`
  itself; the link to what the owner experienced rests on 069's precedent and on
  their two walks. Measuring it needs Orca, which speaks aloud, so it needs the
  owner awake. **This is the weakest joint in the whole chain.**
* The cost of 133 `getBounds()` calls per state read.
* Empty paragraphs, tables, frames, multi-column — `getBoundsImpl`'s
  non-root-parent and empty-preview-page branches were never reached.
* Whether the wasm device's conversion matches the caret the way the native one
  did (20/20, sub-pixel, 39.4× inside tolerance).
* **Finding 095** — after ArrowDown at the last line, the next canvas click
  places no caret for 25s, both profiles, 6/6 on one fixture and not the other.
  Observation, not investigated; the harness path has **not** been excluded.
* The top-boundary focus escape (`leaving panel`, three occurrences) — a separate
  observation from the scroll defect, deliberately not merged, **still unruled**.

## Corrections made to my own claims, kept rather than quietly fixed

* I told the owner the caller "adds zero new external symbols". **Wrong** — it
  adds four (`GetOutDev`, `MapMode` ctor/dtor, `PixelToLogic`). All are `T` in
  `libvcllo.a`, already on the link line, so the conclusion (no core rebuild)
  survives, but the statement did not.
* I unified the owner's two observations into one hypothesis ("focus escapes").
  The second walk refuted it: focus leaves the region only three times, all at the
  top boundary, while the viewport is at the bottom the rest of the time.
* My pre-registered O-1 threshold said the scroll would consume "≳99%" of the
  scrollable room; it consumed 0.9759. I did **not** move the threshold — O-1
  stands on its direct clause (`offsetTop` 928 against canvas 929) and the
  wording defect is registered instead.
* An earlier subagent claimed `getBounds()` returns 1/100 mm from general UNO
  convention. Measured: output-device pixels, and the 1/100 mm hypothesis is
  26.5× away.
