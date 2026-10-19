# v22 post-link checks (main session, 2026-10-19, the day of the link)

The owner linked at 10:39–10:42 +0800 (`handoff/RUNBOOK-relink-v22.md` §2; log `wasm_sdk_probe/build/link-v22.log`, copied here as `link-v22.log`, 92 lines, no error). The manifest step printed `profile e2-editor-v22`, `abiVersion 5`, 23 actions, `withheld: ["select-all"]` and `pasteMarkdown: document-sdk-paste-markdown`, the same as v21.

Spec criteria: `specs/SPEC-M3-link-batch-v22.md` §5.2. Run in `wasm_sdk_probe/`, in the runbook's §3 order.

| # | check | file | result |
|---|---|---|---|
| 1 | Frozen set: `sha256sum -c --quiet` over `../pre-link/frozen-set-before.sha256` (1,370 files). New regular files under `dist/profiles/` and `build/archive/` (`comm` against the pre-link list) | `frozen-set-after.txt` | Nothing printed, exit 0. The only new files are the four in `dist/profiles/e2-editor-v22/`. Measured before the v22 archive was made |
| 2 | **S1**: `tools/check_pthread_stack_literal.py` on `dist/…/e2-editor-v22/probe.js` and `build/e2/editor-v22/probe.js` | `s1.txt` | `VERDICT PASS`. Both are `dc4c2c84…`, anchors 1 / 0 |
| 3 | **I1-v22**: X1 default mode against v21 (exports from the v21 archive) | `x1-check-profile-identity.txt` | `VERDICT PASS`, exit 0. Moved leaves: `loaderSha256`, `wasmSha256`, `profile`, `sdkVersion`, and no other. wasm `f7a40bcc…` (v21 `db3408f5…`), worker `0d55bcfa…`, exports byte-identical. The spec's pre-declared reading for a byte-equal wasm was **not needed** |
| 4 | `grep -a -o ScDocShell dist/profiles/e2-editor-v22/probe.wasm \| wc -l` | `scdocshell-count.txt` | `0` |
| 5 | E1-C: `tools/check_e1_c_bundle_intact.py` | `e1-c-intact.json` | `"intact": true`, exit 0 |
| 6 | **S2** (recorded): v22's `probe.js` with the S1 literal set back to 65536 once, against v21's | `s2.txt` | **Byte-equal** (`0b6cf02a…`, `cmp` same): 0 differing tokens |
| 7 | Archive | `wasm_sdk_probe/build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/`; its `SHA256SUMS` copied as `archive-SHA256SUMS` | Seven files; the four profile files `cmp`-equal to `dist/` |

**I1-v22: PASS. S1: PASS. S2: 0.**

## v22's loader is the bytes the stack measurement already served

v22's `probe.js` (`dc4c2c84…`) is byte-identical to two other things:
- the S1 positive control (`../pre-link/s1-red-first.txt`), which is v21's loader with the one literal replaced;
- the loader the diag tool served as `v21stack1048576` on 2026-10-19 (fable ruling 4, F3).

So the 10-19 headroom and bisect cells at 1,048,576 ran v22's exact loader on v21's wasm. That makes ruling item 17's attribution run (archived v21 with the `v21stack1048576` loader) differ from v22 **only in the wasm** [inferred from the hashes].

## How the wasm differs (recorded; not a criterion)

`probe.wasm` is 115,314,061 bytes, one more than v21's.
- **Sections:** read with a small section walker (Python, in the session, not committed). There are 12 sections. Every one except the code section is byte-equal.
- **Code section:** 149,474 function bodies, and exactly one differs: index 77040, 25,122 → 25,123 bytes. Two local indices go 2 → 3, and one `try` block (`06 40`) sits at another offset.
- **The stack value is not in any differing byte.** `i32.const 65536` occurs once in that function in both builds; `i32.const 1048576` occurs in neither.
- **Objects:** `sdk_api.o`, `unoembind_stub.o` and `editor_api.o` are byte-equal to v21's. `probe_engine.o` differs (`16e643eb…` in v21, `77062f5c…` in v22): the same source and the same compile line (S3), compiled twice.
- That is the finding 036 shape (the artifact is not a function of the source). Attributing function 77040 to `probe_engine.o` is inferred: it is the only object that differs. The function has no name: there is no name section.
- **Consequence:** v22's engine is v21's except for one function's code generation, and the loader except for the one literal.
