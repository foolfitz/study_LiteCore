# The revert rehearsal, this time including step 3 — and the revert's destination is not a declared state

Work item **W-5** of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`:
*"Freezing a generation and repointing `MANIFEST`, and un-freezing on revert,
was discovered by the revert rehearsal and has not itself been rehearsed."*

Rehearsed 2026-09-06, on candidate `e2-editor-v12` and page `20f09cc9…`.
Script: `rehearse_revert.sh`, wired to a `trap … EXIT` that undoes all three
steps whether it finishes, fails or is killed. Full transcript:
`rehearsal-2026-09-06.log`.

## What was done

| | |
|---|---|
| baseline | `web/` and `dist/` both `5aeae0e1…`, `MANIFEST = v43`, `git status` clean |
| step 1 | `build_cutover_page.py --profile e2-editor-v12 --write --expect-sha256 20f09cc9…` → page written, `20f09cc9…` |
| step 2 | `cp web/e2-editor-app.js dist/` → `20f09cc9…` |
| step 3 | froze `e2/editor-shell-v2-bundle-v44.json` (`bundleSha256 78c23684…`, `problems: []` after write), then repointed `MANIFEST` v43 → v44 |
| run | the net on the cutover page, **no** `--candidate-profile` |
| revert | all three undone |
| run | the net on the reverted page |

## Step 3 works, and it is what closes the 2026-08-28 refusal

Post-cutover run: **38 PASS / 2 NE**, the two standing sentinels,
`candidateCutover: null` — a real shipped-page run, carrying no candidate stamp.

```
servedShell.bundle           e2/editor-shell-v2-bundle-v44.json
servedShell.declaredSha256   78c2368403e16af1…
servedShell.servedSha256     78c2368403e16af1…      <- equal
servedShell.differingPaths   []
servedShell.entrypointSha256 20f09cc9…
check_usable_editor          ok: true, reconciledFor.kind = "shipped-page"
```

On 2026-08-28 the same shape **without** step 3 produced
`differingPaths: ['web/e2-editor-app.js']` and a refusal. With step 3 it
reconciles. **W-5's question is answered: freezing the generation and repointing
`MANIFEST` is sufficient, and the cutover is executable as four steps.**

## The revert is byte-clean

`web/` and `dist/` both back to `5aeae0e1…`, `MANIFEST` back to v43, the v44
manifest deleted, `git status` empty. Verified after the explicit revert and
again by the trap on exit.

## But the post-revert run was REFUSED, and that is a real result

Post-revert run: 38 PASS / 2 NE, runner `ok: true`. `check_usable_editor`:
**`ok: false`.**

```
servedShell.bundle           e2/editor-shell-v2-bundle-v43.json
servedShell.declaredSha256   7e99d3a3b8ba789b…
servedShell.servedSha256     f89d7bb9d1438ef2…      <- NOT equal
servedShell.differingPaths   ["web/e2-editor-app.js"]
servedShell.differsOnlyInTheEntrypoint  true
```

**This is not damage the rehearsal did.** Measured with the tree fully restored
and `git status` clean (`v43-vs-the-tree-after-restore.json`):

```
manifest       e2/editor-shell-v2-bundle-v43.json
tree digest    f89d7bb9d1438ef2…
problems       ["manifest is out of date: added=[] removed=[] changed=['web/e2-editor-app.js']",
                "refusing to rewrite … A changed shell needs a NEW generation …"]
```

v43 was frozen 2026-08-27 and declares `web/e2-editor-app.js` =
`28e03e5bc9fcb8c4…`. The tree serves `5aeae0e1…`. The page moved when finding
087's and 088's fixes landed (`681a22b0`, `3d3d0323`) and again when finding
090's `make dist/e2-editor-app.js` ran, and **no generation was frozen for any
of it**. One file differs; everything else in the bundle still matches.

So the state the revert returns to is a state **no frozen generation
describes**. Filed as finding 091.

## Why nothing caught it until now

Every soak run is a **candidate** run. The served-shell check exempts those
deliberately and narrowly — a candidate run carries `candidateCutover` and its
entrypoint hash is required to equal the page the cutover will write. Ten
banked runs, three 4a runs, three caret diagnostics and an ODT round-trip all
went through that exemption or through their own probes. **This rehearsal's
second half is the first plain shipped-page run since the 087/088 fixes
landed**, and it went red on its first try.

The banked evidence is unaffected: the exemption is what those runs were judged
under, and it is still satisfied.

## What this does NOT settle

Whether to freeze a generation for the current shell now, before the cutover, so
the revert has a declared state to land in — and whether doing that mid-count
disturbs anything the soak is judged on. That is a change to the tree's declared
identity while a gate is counting against it, and it is **not the drafting
party's call**. Registered in finding 091 and in the plan; not done.

---

## Correction, same day: step 3 had already been rehearsed, and something did guard the mismatch

Both errors were found by the adjudication of finding 091 (ruling E-6) and
verified against the tree before being recorded here.

**Step 3 was rehearsed on 2026-09-03, not for the first time here.**
`../queue-v12-cutover-revert/RESULT-2026-09-03-step-3-rehearsed.md` performed
the full cutover and revert on `e2-editor-v12`, with and without step 3, and its
post-revert run reconciled `true` on page `28e03e5b…`. The quotation from W-5 at
the top of this file — *"has not itself been rehearsed"* — was already stale
when this take was made; it was copied from the plan without checking whether
the tree had answered it. What this take adds is the same procedure on the page
the ten banked soak runs measure (`20f09cc9…`), which the page move of
2026-09-04 required, **plus the failure the 2026-09-03 take could not have
produced**: on 2026-09-03 `dist/` still held `28e03e5b…` and matched v43, so its
revert landed in a declared state.

**"The first plain shipped-page run since the 087/088 fixes landed" is true and
misleading.** `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree`
guards exactly this and had been red since 087's fix; it was never run. So the
section "Why nothing caught it until now" names the right blind spot for the
*runs* and the wrong one for the *tree*: something guarded it, and nobody ran
the guard. Ruling E-3 makes running it part of the acceptance, which is the
prescription that follows from the corrected reading and not from the original
one.

Both corrections are recorded in `findings/091-*.md` with the measurements.
