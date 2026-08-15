# The last flip condition: WASM agrees with native

**Date** 2026-08-15. Artifact `572035ac…`, profile `e2-editor-v2`, both browsers.
Prediction: [`../PREDICTION.md`](../PREDICTION.md) round-6 addendum, committed
before the artifact was driven on any range (`3ff063c`).

## Why this cell was dark until now

Every cross-paragraph reading in this project was **native**. Whether WASM
agreed was a premise, not a result, and it could not be measured: the surviving
selection is not observable from JavaScript unless B' exists, and B' required
the relink. The adjudicator's flip condition 3 has stood unanswered since the
ruling.

## Result: predicted, in both browsers

| probe | route | preBlocks | postBlocks | identity | state |
|---|---|---|---|---|---|
| `range-single` | `range-single` | 1 | — | — | — |
| `range-cross` | `range-cross` | **2** | **2** | **held** | **held** |

Chrome and Firefox identical. The crossing selection read back as
`"E1-MULTI-START alpha\n第二段中文 beta"` — both paragraphs, whole.

**Flip condition 3 does not fire.** The manifest keeps `range-cross`, so the
shipped disposition stays B'.

## What this actually closes

G3 is the arm that started this. On the combination artifact it failed three
rounds in both browsers: the engine reported success for a two-paragraph
mutation while its barrier could only ever read back one paragraph.

On this artifact the same input routes to `range-cross`, and the success is
reported only after **both** blocks are verified — identity by per-block html
text, state by per-block structure. `crossIdentityHeld` and `crossStateHeld`
are separate fields precisely so that a pass cannot be claimed from one of them.

## What this is not

- **Not the section 7 measurement.** No document is judged here and no verdict
  is bound. The 90-run matrix, the negative matrix and the no-op equation are
  what bind, and they run with their own pre-registered predictions.
- **Not a claim about the other four actions on a crossing range.** Only
  `set-list-unordered` was dispatched. The matrix covers the rest.
- **Not a claim about disposition A.** The refusal branch is in the same
  binary and is exercised by negative row N11, which has not run yet.
