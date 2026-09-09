# Revert condition 3 on `31787584…` (candidate `e2-editor-v13`): E-3's universal clause is MET, its named instance was NOT TAKEN

**2026-09-09.** This is a **partial** discharge and is filed as one. Read the
last section before quoting anything above it.

Finding 093 option B was linked today; the candidate is `e2-editor-v13` and the
candidate page is
`31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`. Everything
bound to `9b29e39b…` died with it, including
`RESULT-2026-09-07-revert-condition-3-discharged-on-9b29e39b.md` beside this
file, which is the immediately preceding take and is left unedited.

## Identity of the tree this was measured on

| | |
|---|---|
| shipping page (`web/` and `dist/`) | `1ec7baf9fb53c808cf127476346d69d56cf93a802f6c72680fa84416f7599ecc` — **still `e2-editor-v8`** |
| shipped generation | `e2/editor-shell-v2-bundle-v49.json`, committed at `18eefcce` |
| `MANIFEST` in `tools/build_e2_c_shell_bundle.py` | `e2/editor-shell-v2-bundle-v49.json` |
| candidate page (measured, never written) | `31787584…` |
| `git status --short` | clean apart from this pass's untracked evidence |

## E-3's criterion, term by term, on a plain shipped-page run

Ruling **E-3** (`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`) is form 1
and universal: *after the freeze is committed, **every plain shipped-page run**
taken against that tree reconciles with these values.* One such run was taken.

```
make test-e2-c-static                      # exit 0, immediately before
python3 tools/run_e2_c_product_path.py --browser chrome \
    --out plain-shipped-run-31787584.json           # no --candidate-profile
python3 tools/check_usable_editor.py \
    --report plain-shipped-run-31787584.json \
    > reconcile-plain-shipped-run-31787584.json
```

| E-3 requires, on a plain shipped-page run | measured |
|---|---|
| `check_usable_editor` `ok` | **true** |
| `reconciledFor.kind` | **`shipped-page`** |
| `servedShell.bundle` | **`e2/editor-shell-v2-bundle-v49.json`** |
| `declaredSha256 == servedSha256` | **true**, `4f8494b6b25736c6314d9cfb8772670009057313d5b0e6753c12b75771e3b9cd` |
| `servedShell.differingPaths` | **`[]`** (and `missing: []`, `differsOnlyInTheEntrypoint: false`) |
| `problems` | **`[]`** |

The run itself: 41 checks, `complete: true`, **39 PASS / 2 NOT_ESTABLISHED, no
FAIL**, the NE set exactly the fixed pair
(`notice-action-recovers-the-session`,
`a-refused-action-is-reported-and-changes-nothing`), `candidateCutover: null`
— a genuine shipped-page run, not a candidate mirror. `startedAt`
2026-09-09T14:11:25+08:00, `completedAt` 2026-09-09T14:17:31+08:00. The
forty-first check `the-projection-is-placed-where-the-document-is` is **PASS**
on the shipped profile as the 2026-09-08 amendment predicted.

*This run is banked here and **not** in the soak directory: it is a shipped-page
run, and the count is over candidate runs. It does not touch the count, which
stands at 3 of 12.*

## E-3's supporting requirements — all met

| requirement | measured |
|---|---|
| `python3 tools/build_e2_c_shell_bundle.py` (default manifest) | **exit 0**, `bundleSha256 4f8494b6…` (= v49's declared value), `problems: []` |
| `python3 -m unittest tests.test_e2_c_shell_bundle` | **12 of 12 OK** |
| `make test-e2-c-static` | **exit 0** (before the run and again after; `test-e2-c-static-2026-09-09.log`) |
| `make test-e2-c-reachability` | **exit 0** (`test-e2-c-reachability-2026-09-09.log`) |
| the anti-rewrite proof, against the **past** generation | `--manifest e2/editor-shell-v2-bundle-v48.json` **still refuses**: *"manifest is out of date: added=[] removed=[] changed=['web/e2-editor-app.js'] … refusing to rewrite … A changed shell needs a NEW generation"*, exit 1 |

All thirteen bound paths, sha256 before and after this pass, in both the source
tree and the `dist/` mirror, are **identical** — `diff` empty on both listings:

```
bound-sha-before-31787584.txt      bound-sha-after-31787584.txt
bound-sha-before-dist-31787584.txt bound-sha-after-dist-31787584.txt
```

and the mirror matches the source on every one of the thirteen, entrypoint
included (`1ec7baf9…` on both sides, which is what v49 declares — hence
`differingPaths: []`).

## What was NOT taken, and why — this is the part that matters

E-3 names a specific instance on top of its universal clause: *"In particular
the **re-run of the revert rehearsal** — `rehearse_revert.sh` with `NEWGEN` =
… and nothing else changed, `trap` intact — must produce a
`reconcile-after-revert.json` with exactly those values."*

**That re-run was not performed.** The commissioning task for this pass carries
hard constraints that forbid every one of the rehearsal's four cutover steps:

* *"Do not run `build_cutover_page.py --write`"* — the rehearsal's step 1;
* *"Do not touch `web/`, `dist/`"* — steps 1 and 2 write both;
* *"The rehearsal must not actually perform a cutover"* — steps 3 and 4 freeze
  a new generation on cutover bytes and repoint `MANIFEST` at it, which is
  exactly the v47 mistake the 2026-09-09 correction to
  `handoff/RUNBOOK-operator-093-engine-geometry.md` was appended to stop.

There is no route around this: the rehearsal's value is that it *executes* the
cutover and then undoes it, and an execution that writes nothing is not that.
Using `build_cutover_page.py --out` into a scratch path and copying the bytes
into `web/` would be the same act by a different spelling, and is refused here
for that reason rather than taken as a technicality.

**Consequence, stated plainly: revert condition 3 is NOT discharged on
`31787584…`.** What is established here is the half that can be established
without a cutover — that **the state a revert would land in is a declared state
that reconciles**, which is the substance of what E-3 asks and the exact defect
(finding 091) that opened the condition on 2026-09-06. What is **not**
established on this identity is that the revert *procedure* returns the tree to
that state byte-for-byte. That property was measured on 2026-09-07 on
`9b29e39b…` / v48, with the same `restore()` implementation
(`git checkout -- web/e2-editor-app.js tools/build_e2_c_shell_bundle.py`, then
`cp web/e2-editor-app.js dist/e2-editor-app.js`, then `rm` the new generation)
and the same thirteen bound paths; **that is an argument from an unchanged
mechanism, not a measurement on this identity, and it is recorded as an
argument.**

**Default if the re-run is never taken:** revert condition 3 stays open and the
gate does not close — E-3's own default sentence, unchanged. Whoever owns the
decision has two options and this pass takes neither:

* **A.** Authorise the rehearsal drill explicitly (it is byte-clean under its
  `trap`, and has been run three times without residue: 2026-09-03,
  2026-09-06, 2026-09-07), and re-take the named instance on `31787584…`.
* **B.** Rule that E-3's named instance is subsumed by its universal clause on
  this identity, and record the ruling — which would be an *amendment*, and
  therefore append-only, named, and not something a drafting party declares for
  itself (AGENTS.md §8).

## Chrome census

One Chrome instance before and after — the owner's (crashpad handler 211863),
unchanged. No headless Chrome, no `serve_candidate_page.py` left behind.
Nothing was killed.
