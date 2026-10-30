# P-v28 (SPEC-M3-v28-last-line-fallback 7.3): the link and its static checks

**The link.** It was run by the agent at the owner's explicit request (「我不在座位，請你幫我跑」, 2026-10-30 ~20:34 +0800; global rule: an explicit 幫我建置 allows it).
- Pre-checks: load 0.14; `pgrep -a make` empty; the v27 archive verified 5/5; no v28 output existed.
- Command: `bash tools/link_v28_last_block_owner.sh`. Exit 0 in 175 s.
- Stream: `link-owner-run.stdout.txt`. Make log: `link-v28-last-block-01.log`.

**The final JSON** (the link script's): `profile e2-editor-v28`, `abiVersion 6`, `typedInsert document-sdk-insert-typed-text`, select-all on all three gestures, **23 actions, `withheld: []`**.

| artifact | sha256 |
|---|---|
| wasm | `13f674e498a56c8a…` (new) |
| loader | `c5336b96…` |
| worker | `a5df83db…` (= `sdk/v28-last-block-worker.js`, byte for byte) |
| manifest | `7b4eb474…` |
| exports | `f5b21630…` (= v27's) |

**Checks.**
- `check_v28_last_block_contract.py`: "v28 preconditions hold" for both the build log and the manifest + exports (inside the link script).
- The log: 4 compilations carrying `-DOXSDK_E2_V27_FIRST_BLOCK -DOXSDK_E2_V28_LAST_BLOCK`, one link of `build/e2/editor-v28/probe.js`.
- The frozen set (`frozen-set-after.sha256` against `../pre-link/frozen-set-before.sha256`, `frozen-set-delta.json`): **holds**. The 2,862 existing files are unchanged, and the only additions are v28's four profile files.
- Archive `wasm_sdk_probe/build/archive/e2-editor-v28-13f674e4-worker-a5df83db/`: five artifacts, `SHA256SUMS` (all OK), `ATTRIBUTION.md`, made read-only. Its two metadata files are hashed in `archive.sha256`.

**Next** (spec 7.3): the cutover (page `workerUrl` and `PINNED_WASM_SHA256 = 13f674e498a56c8a`), then S4 a-e, then freeze generation 82, then F3-82/F4-82/V0′-82/E1-C, then host 0.2.44.
