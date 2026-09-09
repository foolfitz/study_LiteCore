# Finding 093, option B, step 5 item 2 — `e2-editor-v13` archived

Written 2026-09-09, executing `handoff/RUNBOOK-operator-093-engine-geometry.md`
§5 step 5's second item ("立刻 archive") immediately after the owner ran step
4's link. Unlike `e2-editor-v12` (archived ten days late, `step2-archive-e2-editor-v12.md`),
this archive was taken the same day as the link — before the repoint (item 3),
the shell-generation freeze (item 4), or anything else in `dist/profiles/`,
`web/`, `src/`, or `sdk/` could move again.

## Where

```
wasm_sdk_probe/build/archive/e2-editor-v13-0fe25650-worker-6e75829a-manifest-76b89576/
```

The three hash segments were derived, not guessed, by running `sha256sum` on
the live files in `dist/profiles/e2-editor-v13/` before naming the
directory: `probe.wasm` → `0fe25650…`, `sdk-worker.js` → `6e75829a…`,
`sdk-manifest.json` → `76b89576…` (first 8 hex each, matching this tree's
convention — confirmed against all 26 pre-existing directories under
`build/archive/`, none of which collides with this name).

## What is genuinely new here, vs. v9/v10/v11/v12

Every prior post-v8 candidate profile was a repackaging of existing bytes.
`e2-editor-v13`'s `probe.wasm` (`0fe25650bec1bac5…`) is a real compile and
link — the first since the a11y build — driven by finding 093 option B's
engine change to `src/a11y_tree_probe.cpp` (commit `c2a7abad`, "093 B 的引擎
半邊": `XAccessibleComponent::getBounds()` converted to twips on the same
`OutputDevice`), plus the `sdk/sdk-worker.js` allowlist change and the new
`--document-outline-geometry` flag in the same commit, the page half
(`18eefcce`), and the new `E2_V13_*` Makefile build+link rules (`a36cbc5e`)
that made a real link possible (v9/v11/v12 had no such rule; they reused
`e2-editor-v10`'s bytes, `4ec1e389…`, which this profile's `probe.wasm`
does **not** match — confirmed distinct).

## What is in it

Ten files copied (`cp -p`, never moved) from `dist/profiles/e2-editor-v13/`,
totalling 244,219,720 bytes (~233.0 MiB, `du -sb` on the archive directory):

| file | bytes |
|---|---|
| `probe.js` | 144,547 |
| `probe.wasm` | 135,236,350 |
| `sdk-worker.js` | 66,284 |
| `sdk-manifest.json` | 8,156 |
| `base-e2-editor-v13.9901e9be29c9ded2.data` | 39,940,977 |
| `base-e2-editor-v13.b1e48f2b7ac50b60.metadata` | 218,954 |
| `cjk-e2-editor-v13.b76b0433203017ca.data` | 19,484,784 |
| `cjk-e2-editor-v13.fafab99558ab6f8b.metadata` | 263 |
| `fallback-fonts-e2-editor-v13.33856e2a082148dd.data` | 49,102,042 |
| `fallback-fonts-e2-editor-v13.924fb0ed8b459946.metadata` | 15,665 |

Plus `ATTRIBUTION.md` and `SHA256SUMS`, written in the archive directory
itself. No `SHA256SUMS.shared`: checked (not assumed) by grepping
`sdk-manifest.json` for `resources/` — zero matches, same as v12 and unlike
v8/v9/v10. Source file mtimes in `dist/profiles/e2-editor-v13/` were
confirmed unchanged after the copy.

## Verification

Re-read the copies after writing (not trusted from the `cp` exit status):

```
$ cd wasm_sdk_probe && sha256sum -c build/archive/e2-editor-v13-0fe25650-worker-6e75829a-manifest-76b89576/SHA256SUMS
(all ten: OK)
```

Also cross-checked as an order-independent set against a fresh `sha256sum` of
the ten source files still in `dist/profiles/e2-editor-v13/`: identical hash
set both ways.

## The candidate page's hash

`ATTRIBUTION.md` records the sha256 of the candidate cutover page —
`31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a` — as a
reference, not a copy, and unlike v12's this one is **not** a git blob: the
tracked `web/e2-editor-app.js` still pins `e2-editor-v8` today (repoint is
runbook step 5.3, not yet performed). The hash was independently reproduced
here, without writing anything, via:

```
$ python3 tools/build_cutover_page.py --profile e2-editor-v13
pin            4a2710bba1ef07d9 -> 0fe25650bec1bac5
pageSha256     31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a
written        no
```

matching both the value this task named and
`findings/evidence/093/post-link-product-path-v13.json`'s
`candidateCutover.pageSha256`. `git status --short` was empty both before and
after running that command.

## Disk space

| | bytes | approx |
|---|---|---|
| Available before copy | 56,171,888,640 | ~52.32 GiB |
| Available after copy | 55,927,492,608 | ~52.09 GiB |
| Filesystem | `/dev/nvme0n1p2`, 94% used at `df -h` resolution | |

~244 MiB consumed, matching the copy size almost exactly (the small
difference is directory-entry/block overhead in `du -sb`). Comparable to
v12's archive (~233 MiB). No risk of filling the disk.

## Git tracking

Nothing under `wasm_sdk_probe/build/archive/` is tracked, including this new
directory — confirmed with `git check-ignore -v` on `ATTRIBUTION.md`,
`SHA256SUMS`, and `probe.wasm`, all three matching `.gitignore:34`
(`/wasm_sdk_probe/*`), exactly as for the `e2-editor-v12` and `e2-editor-v8`
precedents. This document is the tracked record of what the archive
contains; the archive itself is not in git.

## Not addressed here

This step archives bytes; it draws no conclusion about whether v13 is a good
option-B candidate, whether the repoint (step 5.3) should be performed, or
about the gate/soak consequences of a repoint (runbook §6). Nothing under
`dist/profiles/**`, `web/`, `src/`, or `sdk/` was modified while producing
this archive.
