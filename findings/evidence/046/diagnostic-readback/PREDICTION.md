# 046 / relink queue 3b — reading the barrier's own record off the FROZEN engine.  Registered before the profile was built.

Written 2026-08-16, after external adjudication (fable, subagent) refuted the
premise that these questions need a relink.

## Why this round exists, and why it costs nothing

Two relink blockers were waiting on one thing: **what the barrier actually read**
on an empty paragraph.  The shipped worker projects named fields and drops the
readback markup, so the browser could not see it — and I concluded that seeing it
required the v3 link.

**That was wrong, and it is checkable:**

| claim | check |
|---|---|
| `tools/build_e2_discovery_profile.py` **copies** the wasm (`shutil.copy2`, `--wasm` is an input) | verified at `:171-173` |
| the **frozen** `572035ac` wasm already serialises `"readback":{"parsed":`, `"blockCount":`, `"itemCount":`, `"html":"` and `"containment":{"checked":` | one occurrence each, byte-grep |
| the six worker patch anchors match the **frozen** dist worker exactly once each | verified |

So a diagnostic profile is a **Python repackage around the shipping engine
bytes**.  The engine is not rebuilt, not relinked, not modified.  Only the
worker's projection is swapped for the raw event
(`WORKER_BARRIER_AFTER` / `WORKER_ERROR_AFTER`).

**The frozen worker is the patch input, not the live one.**  `sdk/sdk-worker.js`
now carries today's unlinked projection changes; using it would confound the
comparison with the product round recorded earlier today.

## The two questions

1. **3b's criterion** — on the empty paragraph, is the readback *nothing*
   (`parsed:false`) or *only list items* (`parsed:true, blockCount:0,
   itemCount>=1`)?  The engine's own parser distinguishes them; the product
   cannot see which.
2. **The containment ordering** — is `containment.checked` true and `held` false
   on the disputed cells?  If so, the reorder (containment judged before
   `multiBlock`) changes exactly those cells and is justified by data.  If
   `checked` is false there, the reorder is a **no-op for the case that
   motivated it** and belongs in a later link.

## Method: the same page, the same arms, one thing different

`web/e2-c-046-empty.html` is run **unchanged**, against the diagnostic profile
instead of the product one.  Same fixture, same anchors, same gestures, same
five arms (`A3-text-click` control, `A1-empty-click`, `A2-empty-selectrange`,
`A4-last-empty-click`, `A5-text-range`).

Recorded earlier today on the product profile, in both browsers, so the
comparison is against evidence that already exists:
`findings/evidence/046/browser-vs-native/`.

## Predictions

- **P-046D-1** — the raw record carries a **non-empty `readback.html`** for the
  disputed empty-paragraph arms.  The engine read *something*.
- **P-046D-2** — those arms show **`parsed: true`, `blockCount: 0`,
  `itemCount >= 2`** — the "multiBlock with no block in it" combination 046
  inferred from the product's contradictory message and the native parser
  confirmed as reachable.
- **P-046D-3** — those arms show **`containment.checked: true` and
  `containment.held: false`**: the selection the postcondition read describes
  does **not** cover the caret the action was dispatched from.
- **P-046D-4** — the control arm (`A3-text-click`, a text paragraph, collapsed
  route, **succeeds**) shows `parsed: true`, `blockCount: 1`, and
  `containment.held: true`.
- **P-046D-5** — **the load-bearing control for the whole method**: every arm's
  *outcome* (`accepted`, `failureShape`, session state) is **identical** to the
  product-profile round recorded earlier today.  Swapping the projection must
  change what can be seen, not what happens.  If outcomes differ, this profile
  is not the product path and **nothing measured here transfers**.

## The decision rule, written before the data

- **P-046D-5 fails** → stop.  The round says only "the diagnostic profile is not
  the same path", and both blockers stay where they are.
- **P-046D-2 holds** → 3b's criterion is writable, and it is written on
  `parsed` (nothing read) versus `parsed && blockCount == 0 && itemCount >= 1`
  (only list items) — **not** on a block count alone, which is the mistake 046
  has been circling since 2026-08-15.
- **P-046D-3 holds** → the containment reorder goes into **this** link, with
  the flip set enumerated from the recorded D2 failure families first.
- **P-046D-3 fails with `checked: false`** → the reorder is a no-op for the
  motivating case; it is deferred and the reason is recorded.  (This retreat
  condition was named by the adjudication before the data existed.)
- Whatever the numbers: **no shape is written into the engine in this round.**
  This round produces a criterion and a decision, and both land in the v3 link.

## What voids the round

- The diagnostic profile's `probe.wasm` is not byte-identical to
  `dist/profiles/e2-editor-v2/probe.wasm`: void, because the whole argument is
  that the engine is the shipping one.
- The page fails to reach an arm for a reason unrelated to the barrier: that arm
  is recorded as void, not retried.
- The evidence is filed as **diagnostic** and never as matrix evidence.  The D0
  entry assertion refuses a profile whose hashes are not the frozen baseline —
  which is correct, and the bypass this round needs is a **declared** one that
  stamps the evidence, not a relaxation of the guard.
