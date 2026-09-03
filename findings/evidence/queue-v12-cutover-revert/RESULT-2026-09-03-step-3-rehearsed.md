# The revert rehearsal, this time including step 3

Re-earn item 3 of the 2026-08-29 amendment to
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, performed 2026-09-03 for
candidate `e2-editor-v12`. The 2026-08-28 rehearsal **discovered** step 3 — the
freeze-and-repoint — and did not itself rehearse it. It has now been rehearsed.

Re-runnable: `rehearse_revert_with_step_3.sh` (banked here as it ran).

## What was done, for real

The cutover was performed against the real tree — page written, staged into
`dist/`, generation frozen, `MANIFEST` repointed — the net run against the real
page at two of those points, then all three steps undone and the net run again.

| stage | page sha | run `ok` | checklist `ok` | composition |
|---|---|---|---|---|
| baseline | `28e03e5bc9fcb8c4` | — | — | — |
| after steps 1+2, **step 3 omitted** | `3dfdcfef4abfe6b7` | **true** | **false** | 38 / 2 |
| after step 3 | `3dfdcfef4abfe6b7` | true | **true** | 38 PASS / 2 NE |
| after the revert of all three | `28e03e5bc9fcb8c4` | true | true | 38 PASS / 2 NE |

## Step 3 is necessary, and this is the measurement that says so

With the page cut over and nothing frozen, the run itself is green and the
checklist refuses it:

```
the shell that ran is not the declared generation
(e2/editor-shell-v2-bundle-v43.json): served 14bf3c391c001efb,
declared 7e99d3a3b8ba789b -- differing paths ['web/e2-editor-app.js']
"ok": false
```

The product page **is** the bundle's entrypoint and is in its `included` list,
so rewriting two of its lines moves the bundle digest. A candidate run is
exempted narrowly — it carries `candidateCutover` — and a post-cutover run
carries no such stamp.

After freezing `v44` and repointing `MANIFEST`, `servedShell` reads
`declaredSha256 == servedSha256 == 14bf3c391c001efb…` and the checklist
reconciles `ok: true`. **The cutover is four steps and all four have now been
executed and undone.**

## The revert, and what the guard forces it to include

`build_e2_c_shell_bundle.py` refuses to rewrite an existing manifest whose
digest would change. So a revert cannot leave `v44` behind: with the page back
at baseline the tree hashes `7e99d3a3…` while `v44` declares `14bf3c39…`, and
the next freeze would be refused. **The revert therefore deletes the generation
file and restores `MANIFEST`**, and the rehearsal did both. Afterwards: `v44`
absent, `MANIFEST` back to `v43`, both copies of the page byte-identical to
`28e03e5bc9fcb8c4`, `git status` clean.

`dist/e2-editor-app.js` is **not tracked by git** — the allowlist `.gitignore`
excludes `wasm_sdk_probe/dist` — so `git checkout` cannot restore it and the
rehearsal backed it up by hand. A revert plan that assumes git can undo the
staging step would leave the served copy cut over.

## The safety net was tested by an accident, not by a drill

The first attempt was **killed mid-run** by the harness (the script needs about
25 minutes; the background task had a shorter limit). The `trap … EXIT` fired:
both copies of the page returned to `28e03e5bc9fcb8c4`, `MANIFEST` to `v43`,
`v44` was removed, and `git status` was clean — verified before anything else
was done. The rehearsal was then relaunched under `setsid` so it no longer
shares the harness's lifetime. *A revert that has never been executed is a
hope*; a trap that has never fired is the same thing one layer down, and this
one has now fired for real.

## What the rehearsal found: a new generation inherits the wrong ancestor's exclusions

Freezing `v44` reported:

```
"exclusionsInheritedFrom": "e2/editor-shell-v2-bundle-v40.json"
```

Not `v43`. `FROZEN_MANIFESTS` in `tools/build_e2_c_shell_bundle.py` ends at
**v40**, while `v41`, `v42` and `v43` exist in `e2/` — adding a generation to
that tuple is a manual step and it has lagged three generations. The builder
walks that tuple in reverse to find exclusions to inherit, so a freeze that
passes no `--exclude` inherits from the newest **listed** manifest rather than
the newest **existing** one.

**No difference this time, and that is luck rather than mechanism**: `v40`,
`v41`, `v42` and `v43` carry the same three exclusions, item for item
(`sdk/sdk-worker.js`, `reader-shell/reader-session.js`,
`reader-shell/state-machine.js`), so `v44` came out identical either way.
Had any of the three changed an exclusion, `v44` would have silently inherited
`v40`'s and **nothing would have gone red** — the tool even reports
`exclusionsInheritedFrom` honestly, and no check reads it.

The builder's own comment anticipated the manual step being missed — *"Adding it
to FROZEN_MANIFESTS is a manual step, so 'not yet listed there' cannot be what
protects it"* — and the guard it then wrote protects against **overwriting** a
generation, not against **inheriting** from a stale one.

**Not fixed here.** Changing the builder mid-gate is an instrument change the
gate cannot absorb, and the measured outcome for this cutover is unaffected.
Registered as a queue item instead; the fix (catch `FROZEN_MANIFESTS` up, or
make the walk use the newest existing generation) is post-cutover work.
