# v22 pre-link gates (main session, 2026-10-19)

All of these ran after the criteria were pinned (`specs/SPEC-M3-link-batch-v22.md`, commit `937bc684`). Commands ran in `wasm_sdk_probe/` with the six `?=` variables (`LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX`) unset.

## S3 (spec 5.1): the link differs from v21's by one token

- `make-n-v22.txt`: `make -n dist/profiles/e2-editor-v22/sdk-manifest.json`, taken while `build/e2/editor-v22/` and `dist/profiles/e2-editor-v22/` did not exist. Exit 0. 79 lines, the same count as v21's witness. `make -n` compiled nothing and created neither directory (checked with `ls` before and after).
- `s3-word-diff.txt`: `git diff --no-index --word-diff=plain` of `../../link-batch-v21/part-e-red/make-n-v21.txt` against `make-n-v22.txt` with every `editor-v22` read as `editor-v21` (`sed`, in a scratch copy).
  - **Exactly three changed lines**: 3 `[-…-]` and 3 `{+…+}` markers; a plain `diff` shows 6 changed lines (3 removed, 3 added).
  - Each line changes only where the spec's closed list says:
    1. the guard line's `it carries:` text (v21's description → v22's);
    2. the link line, one token: `-sDEFAULT_PTHREAD_STACK_SIZE=65536` → `-sDEFAULT_PTHREAD_STACK_SIZE=1048576`;
    3. the worker pin: `PENDING-PART-S-WORKER-SHA256` → `0d55bcfa…` (v21's witness predates part S's pin).
  - In particular, the four compile lines are identical, defines included. **S3 (a): PASS.**
- `what-the-link-ships-v22.json`: `python3 tools/what_the_link_ships.py --since 5f5bf11c --variant link-batch-v22 --shipped-profile dist/profiles/e2-editor-v21 --json`, exit 0.
  - `ok: true`, `configurationDrift: []`.
  - `identical`: `sdk_api`, `probe_engine`, `unoembind_stub`, `editor_api`; `changed: {}`.
  - The worker: `0d55bcfa2ee0e4dd` shipped and in the tree, `identical: true`.
  - **S3 (b): PASS.**
- Caught while writing the block, before any of the above ran: the mechanical rename `E2_V21` → `E2_V22` had also turned `-DOXSDK_E2_V21_LINK_BATCH` into `-DOXSDK_E2_V22_LINK_BATCH`, a define no source reads, so the link would have dropped v21's engine code. Seen in the Makefile diff and restored. S3 (a) would also have shown it as a fourth changed line.

## S1-red (spec 5.1): the checker is red on v21

`s1-red-first.txt`, three runs of `tools/check_pthread_stack_literal.py`:

| input | anchors (1048576 / 65536) | exit |
|---|---|---|
| `dist/profiles/e2-editor-v21/probe.js` (`0b6cf02a…`, shipped) | 0 / 1 | 1 |
| the positive control below plus a second `1048576` anchor | 2 / 0 | 1 |
| positive control: v21's `probe.js` with the anchor's `65536` replaced by `1048576` once | 1 / 0 | 0 |

The positive control hashes to `dc4c2c84657e…`. That is the loader the diag tool served as `v21stack1048576` on 2026-10-19 (fable ruling 4, F3: "`dc4c2c84`"). Two independent routes produced the same bytes.

## M1-1 with the v22 block (spec 4.2)

- `m1-1-red-without-e2-v22.txt`: `check_merge_key_undo_scope.py --base 5d77dc84` with test-e2-c-static's old carrier list (E2_V15, E2_V19, E2_V20, E2_V21), exit 1. It fails on exactly `E2_V22`'s `sdk_api.o`, `probe_engine.o` and `editor_api.o`; `unoembind_stub.o` is not named.
- `m1-1-green-with-e2-v22.txt`: the same plus `--carrier E2_V22=probe_engine,sdk_api,editor_api`, exit 0. 28 rules, 112 objects, 11 different = the five carriers' declared sets (1 + 1 + 3 + 3 + 3).

## The frozen set and the static target

- `frozen-set-before.sha256`: `find dist/profiles build/archive -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum`; 1,370 files.
  - Against v21's pre-link set (`../../link-batch-v21/pre-link/frozen-set-before.sha256`, 1,306 files): none of the 1,306 changed or went missing.
  - The 64 new files are v21's profile (4), v21's archive (7), the shell v73 archive of 10-17 (7) and the host 0.2.25 archive (46).
- `test-e2-c-static.txt`: `nice make -k test-e2-c-static` after the Makefile change, **exit 0**.
  - node: 485/485 and 5/5; python unittest: 108 OK and 134 OK.
  - The M1-1 line runs with the new `E2_V22` carrier and passes.
  - `check_gesture_offers.py` passes against v21 (it does not know v22 yet; that moves with the shell, spec §7 step 3).

## Pre-checks for the link (RUNBOOK-relink-v22 §0)

At 10:2x on 2026-10-19:
- `find $L/instdir/program $L/workdir/LinkTarget $L/workdir/CustomTarget/static/emscripten_fs_image ../libreoffice-26-8/static/emscripten/environment.js -newer build/e2/editor-v21/probe.wasm -type f | wc -l` printed `0`.
- No `?=` variable was set in the session's environment.
- The v21 archive verified 5/5 and equals `dist/`.
