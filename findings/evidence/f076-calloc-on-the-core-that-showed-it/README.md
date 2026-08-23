# Finding 076 — the fix, measured on the core where the symptom was visible

Measured 2026-08-24 with `wasm_sdk_probe/tools/capture_canvas_edges.py`, the
same instrument that produced finding 075's table.

## Why this run had to happen

`calloc` shipped in `e2-editor-v8` on 2026-08-24 and the product core came back
clean. **That proves less than it looks like.** The product core already read as
transparent off-page under `malloc` — 0% opaque, by 075's own table — so a clean
canvas there says "no regression", not "cured". The noise the operator actually
saw was on the **accessibility** core, whose lineage still carried `malloc`.

Closing a defect on a build where its symptom was never visible is a shape this
tree keeps writing down. So: link the a11y lineage with the one-line fix and
look.

## A single-variable experiment

`a11y-calloc` against `e2-editor-v5`, the artifact the operator looked at:

| | v5 | a11y-calloc |
|---|---|---|
| `probe.js` | `697cf13bfbfec593` | **byte-identical** |
| `sdk-worker.js` | `070229cd10bda4a0` | **byte-identical** |
| `soffice.data` | `15237566b8267e70` | **byte-identical** |
| `soffice.data.js.metadata` | `25b75fd3e0d64ddc` | **byte-identical** |
| `probe.wasm` | `e32d50d3522810bc` | `b60cc46fcc6bf572` |

The manifests differ in `profile`, `sdkVersion` and `wasmSha256` and in nothing
else; the gesture maps are identical.
`what_the_link_ships.py --variant a11y --since 7fcb143` reports the wasm
difference as **one hunk**: `std::malloc` → `std::calloc`.

The first attempt at packaging got this wrong and is worth recording: the
builder inherits `artifactFiles` from the source manifest, which points
`soffice.data` at the shared **product-core** image. A profile linked against
one core would have loaded another core's filesystem. Caught by diffing the
manifest against v5's before measuring anything — `resourcePacks` was `[]` on
one side and a CJK pack on the other. The builder now takes `--core-data`, so it
is a build step rather than a thing to remember.

## The answer

Off-page columns only (`x < 14` and `x >= 710`), 26,941 pixels per shot:

| shot | alpha == 0 | alpha > 128 | passes the ink test | distinct alphas | PNG bytes |
|---|---|---|---|---|---|
| v5 (`malloc`) at rest | 21,559 | 3 | 0 | 46 | 45,294 |
| v5 after caret | 19,236 | **290** | **30** | **184** | **90,538** |
| v5 after set-bold | 19,236 | **1,235** | **853** | 186 | 89,542 |
| **a11y-calloc at rest** | 21,595 | **0** | **0** | 33 | 42,639 |
| **a11y-calloc after caret** | 21,595 | **0** | **0** | 33 | 42,621 |
| **a11y-calloc after set-bold** | 21,595 | **0** | **0** | 33 | 42,669 |

Gone, in all three states.

Two things make this stronger than a single before/after:

* **The post-fix rows equal the PRODUCT core's own.** `e2-editor-v8` measures
  21,595 / 0 / 0 / 33 in every state. Two different cores, built from different
  configurations, now produce the same off-page region to the pixel — which they
  did not before.
* **The baseline reproduces across profiles.** 075's archived `a11y-gate0`
  after-caret shot is 290 opaque, 31 ink, 184 distinct alphas. This run's v5,
  a *different profile* on the same core, is 290, 30, 184.

The PNG size is the cheap tell, and it is unchanged as a tell: **90,538 →
42,621**. Noise does not compress.

## The defect was worse than the finding recorded

Finding 075 measured **at rest** and **after a caret**. Nobody had driven an
edit and looked.

One format press takes v5 from 290 opaque pixels to **1,235, of which 853 are
dark enough to pass the ink test** — against 31 in the shot 075 was written
from. The `--after-action` arm exists because it was added on 2026-08-23 for a
different question (band counts), and pointing it at this one cost nothing.

## What this still does not say

* **Rate.** One run per profile. The mechanism is deterministic in source and
  the effect size is 1,235 → 0, but nothing here measures how often a user would
  have seen it.
* **What those bytes were.** Still not traced to an allocation. Unchanged from
  the original finding.
* **Nothing about v5's product-path reds.** Band counts are 9/9 on both
  profiles here, so this run does not speak to why v5 was reverted (the format
  barrier's `stage-deadline`, bold not reaching the document). `a11y-calloc` is
  **not** a product candidate — it carries v5's pre-078 manifest, so selected
  text cannot be emboldened on it.
