# Finding 096 — `e2-editor-v14` archived

Written 2026-09-10, closing the gap `RESULT-after-the-link.md` §S6 flagged:
"`build/archive/` has no v14. Step 1 was not done before the measurements
were taken." (Step 1 of `handoff/HANDOFF-2026-09-09-096-is-landed-in-source-and-waits-on-the-same-link.md`'s
post-link order: "record the five hashes; archive immediately.") The owner
linked `e2-editor-v14` on 2026-09-09; this archive was taken the next day,
following the same-day-as-linked discipline `e2-editor-v13` set
(`findings/evidence/093/step5-archive-e2-editor-v13.md`), before the link
could be overwritten by any further work — a wasm build is not reproducible,
so an unarchived profile that gets overwritten is simply gone.

## Where

```
wasm_sdk_probe/build/archive/e2-editor-v14-5847a140-worker-6e75829a-manifest-9943b064/
```

The three hash segments were derived, not taken on trust from this task's
brief, by running `sha256sum` on the live files in
`dist/profiles/e2-editor-v14/` before naming the directory: `probe.wasm` →
`5847a140…` (matching the brief's stated prefix, confirmed rather than
assumed), `sdk-worker.js` → `6e75829a…` (byte-identical to v13's — unchanged
since finding 093's step 3), `sdk-manifest.json` → `9943b064…`.

## What is genuinely new here

`e2-editor-v14`'s `probe.wasm` is a real compile and link — the second since
the a11y build (after v13) — driven by finding 096's fix A in
`src/probe_engine.cpp` (commit `761fc80d`, "096 的兩半一起落地"), landed on
top of finding 093 option B (same `coreCommit`,
`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`, as v13; the LibreOffice core did
not move). Re-verified here rather than taken on report: the literal
`verified-move-readback` occurs once in this `probe.wasm` and zero times in
v13's and v8's; the positive control `verified-caret-readback` occurs once
in all three.

## What is in it

Ten files copied (`cp -p`, never moved) from `dist/profiles/e2-editor-v14/`,
totalling 244,220,430 bytes (~233.0 MiB, `du -sb` on the archive directory):

| file | bytes |
|---|---|
| `probe.js` | 144,547 |
| `probe.wasm` | 135,237,060 |
| `sdk-worker.js` | 66,284 |
| `sdk-manifest.json` | 8,156 |
| `base-e2-editor-v14.9901e9be29c9ded2.data` | 39,940,977 |
| `base-e2-editor-v14.b1e48f2b7ac50b60.metadata` | 218,954 |
| `cjk-e2-editor-v14.b76b0433203017ca.data` | 19,484,784 |
| `cjk-e2-editor-v14.fafab99558ab6f8b.metadata` | 263 |
| `fallback-fonts-e2-editor-v14.33856e2a082148dd.data` | 49,102,042 |
| `fallback-fonts-e2-editor-v14.924fb0ed8b459946.metadata` | 15,665 |

Plus `ATTRIBUTION.md` and `SHA256SUMS`, written in the archive directory
itself. No `SHA256SUMS.shared`: checked (not assumed) by grepping
`sdk-manifest.json` for `resources/` — zero matches, same as v12 and v13 and
unlike v8/v9/v10. Source file mtimes in `dist/profiles/e2-editor-v14/` were
confirmed unchanged after the copy.

## Verification

Re-read the copies after writing (not trusted from the `cp` exit status):

```
$ cd wasm_sdk_probe && sha256sum -c build/archive/e2-editor-v14-5847a140-worker-6e75829a-manifest-9943b064/SHA256SUMS
(all ten: OK)
```

Also cross-checked as an order-independent set against a fresh `sha256sum`
of the ten source files still in `dist/profiles/e2-editor-v14/`: identical
hash set both ways.

## The candidate page's hash

`ATTRIBUTION.md` records the sha256 of the candidate cutover page —
`d74801324d24394924ef044cf3d291614538332d74e136aed531f8042332591e` — as a
reference, not a copy, and like v13's (unlike v12's) it is **not** a git
blob: `git log --all -S "e2-editor-v14" -- web/e2-editor-app.js` returns
nothing, and the tracked `web/e2-editor-app.js` still pins `e2-editor-v8`.
The hash was independently reproduced here, without writing anything, via:

```
$ python3 tools/build_cutover_page.py --profile e2-editor-v14
pin            4a2710bba1ef07d9 -> 5847a1407d3af58f
pageSha256     d74801324d24394924ef044cf3d291614538332d74e136aed531f8042332591e
written        no
```

`--write` was never passed. `git status --short` was empty both before and
after running that command.

## Disk space

| | bytes | approx |
|---|---|---|
| Available before copy | 71,693,213,696 | ~66.8 GiB |
| Available after copy | 71,447,515,136 | ~66.5 GiB |
| Filesystem | `/dev/nvme0n1p2`, 93% used at `df -h` resolution | |

245,698,560 bytes (~234.3 MiB) consumed, matching the copy size closely.
Comparable to v12's and v13's archives (~233 MiB each). No risk of filling
the disk.

## Git tracking

Nothing under `wasm_sdk_probe/build/archive/` is tracked, including this new
directory — confirmed with `git check-ignore -v` on `ATTRIBUTION.md`,
`SHA256SUMS`, and `probe.wasm`, all three matching `.gitignore:34`
(`/wasm_sdk_probe/*`), exactly as for the `e2-editor-v8`/`v12`/`v13`
precedents. This document is the tracked record of what the archive
contains; the archive itself is not in git.

## Not addressed here

This step archives bytes; it draws no conclusion about whether v14 is a good
finding-096 candidate, whether a repoint should be performed, or about the
open question `RESULT-after-the-link.md` left standing — that both controls
(v13, v8) still die at the boundary press, now labelled
`DIED_WITH_CHECKPOINT` rather than `REPRODUCED` because half C changed the
label without changing the death. Nothing under `dist/profiles/**`, `web/`,
`src/`, or `sdk/` was modified while producing this archive.
