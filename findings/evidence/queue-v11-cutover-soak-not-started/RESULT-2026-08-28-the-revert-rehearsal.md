# The revert rehearsal: performed, not assumed

Revert condition 3 of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`,
2026-08-28. *"A revert that has never been executed is a hope, not a plan."*

## What was done

The cutover was performed **for real** — `build_cutover_page.py --profile
e2-editor-v11 --write --expect-sha256 …` over `web/e2-editor-app.js`, staged
into `dist/` — the net was run against the real page, the revert was performed
with the same tool in the other direction, and the net was run again.

The revert was wired to a `trap … EXIT`, so a run that died in the middle could
not leave the tree cut over. A rehearsal that can strand the tree is not one.

## The four runs

| | ok | composition | shell |
|---|---|---|---|
| baseline, v8 | true | 38 PASS / 2 NE | matches the declared generation |
| candidate, mirrored | true | 38 / 2 | differs only in `web/e2-editor-app.js` |
| **after the real cutover** | true | **37 / 3** | differs only in `web/e2-editor-app.js` |
| **after the revert** | true | **38 / 2** | **matches again** |

The tree afterwards: `git status` clean, both copies of the page back to
`28e03e5bc9fcb8c4` — **the baseline hash, byte for byte** — pointing at
`profiles/e2-editor-v8/sdk-worker.js`, and the post-revert run reconciles the
checklist `ok: true`.

**The revert is a pointer flip and it has now been executed.**

## Finding 1: a real cutover mints a shell generation, or every run after it is refused

Measured rather than reasoned — `check_usable_editor.py` on the post-cutover
report:

```
"the shell that ran is not the declared generation
 (e2/editor-shell-v2-bundle-v43.json): served cdab7fda212d6720,
 declared 7e99d3a3b8ba789b -- differing paths ['web/e2-editor-app.js']"
"ok": false
```

The product page **is** the bundle's entrypoint and is in its `included` list,
so rewriting two of its lines moves the bundle digest. A candidate run is
exempted deliberately and narrowly (it carries `candidateCutover` and its
entrypoint hash must equal the page the cutover will write). **A run after the
cutover carries no such stamp and is refused.**

So the cutover is not two lines. It is:

1. `build_cutover_page.py --profile e2-editor-v11 --write --expect-sha256 …`
2. `cp web/e2-editor-app.js dist/`
3. **freeze the new generation** — `build_e2_c_shell_bundle.py --manifest
   e2/editor-shell-v2-bundle-v44.json --frozen-date … --write`, and point
   `MANIFEST` at it
4. and the revert undoes **all three**, or the tree ships v8 while declaring a
   generation whose entrypoint points at v11.

Step 3 was missing from the plan. It is the thing that "a revert that has never
been executed" hides: not that the flip fails, but that something else has to
flip with it.

## Finding 2: the extra NE was not v11's

The post-cutover run came back 37/3, the third being
`clear-format-removes-every-inline-format`. That is **not** attributable to the
cutover: the same check abstained once on a plain **shipped-profile** run
earlier the same day (`acceptance-v8-e`). One occurrence on each side, so
nothing can be named — it is an intermittent that predates this work.

Under the plan's soak criterion it would **restart the clock**, which is the
criterion working as designed rather than an argument for loosening it.

## What this does not cover

**No new generation was frozen and none was reverted.** The rehearsal exercised
steps 1, 2 and 4 of the list above. Step 3 was discovered by it and has not
itself been rehearsed.

**One cycle.** The claim is that this revert works, not that any revert will.
