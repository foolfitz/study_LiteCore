# Handoff: v28 (the 083 path's multi-paragraph last line) -- implemented, every pre-link gate green, link handed to the owner

Checkpoint **2026-10-30 ~20:45 +0800**. Supersedes `HANDOFF-2026-10-30j-083-path-native-measured.md` (and its three addenda) for what is next; that file holds the measurement and ruling history.

Study HEAD **7a04885ec** plus this file's commit. Untracked, all to be kept:
- `codex-claude-code-delegation.md` -- not ours;
- native harness binaries under `findings/evidence/176/native*/build-*/`.

**No runner is running.**
- `dist/` still serves generation 81 / `e2-editor-v27` (untouched).
- The live host runs **0.2.43**, the daily uncounted candidate.
- The source tree carries v28's shell changes (page + client), not yet cut over or frozen.

## Owner state

**Pending: the owner runs the link** (`handoff/RUNBOOK-relink-v28.md`, about 3-5 minutes):

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v28_last_block_owner.sh
```

Expected in the final JSON:
- `profile e2-editor-v28`, `abiVersion 6`, 23 actions;
- **`withheld: []`**;
- a new `wasmSha256` (not `c089dfd6…`).

On failure: preserve everything, report.

Owner decisions this session (all recorded in the spec):
- 「A. 量 083 那格」;
- 「A. 做多段文件最後一行」;
- a restore failure after the fallback keeps rollback 「A」;
- the table case gets 「A. 新寫一句」;
- the reminder 「不要陷入修機械或修散文的坑裡」: one review round per document; nits get a line or nothing.

## What v28 is (spec `specs/SPEC-M3-v28-last-line-fallback.md`, pinned `b1241e3dd`)

**The trigger.** On the collapsed route, when `.uno:SelectText` reads NONE (finding 083's path) and the restore point is valid, the engine posts `.uno:CharLeftSel`, reads it, and judges the readback's **LAST block**, which must be one of exactly 2 blocks.

**The outcomes:**

| outcome | shape |
|---|---|
| the fallback also reads NONE (the blank document) | `select-text-returned-none`, unchanged |
| the fallback reads but cannot be judged (a table…) | new `fallback-readback-refused` -> review (client) + its own sentence (page) |
| the restore failed | `selection-not-restored`, judged BEFORE the structural refusals |
| judged, not satisfied | `postcondition-not-met` |

**The basis:**
- the native arm `findings/evidence/176/native-q52/` (V1-V7);
- fable ruling 4 `findings/evidence/176/RULING-fable-2026-10-30-d.md`;
- one opus review (20 items, adopted).

## Done this session (evidence `findings/evidence/v28-083/`)

| Gate | Result | Commit |
|---|---|---|
| U-v28 (shell) | 4 red first, then green; shell 565/566 (pre-existing **L-select-all-u2-pins-v26-profile**); E1-C intact | `0763ed918` |
| E1/E2 | 20 FAIL on the v27 inc, then green; 8 mutations red | `1236422d4` |
| E3 | inc tests green; `test-e2-c-static` no new red. Pre-existing and named: the three of v27, L-select-all-u2, **L-relink-queue-drift-v26-v27** | `1236422d4` |
| E4 | v27's 18 rows unchanged under the v28 define; 26 tool-closed fallback rows | `1236422d4` |
| V0-v28 | vs **3a6998b33**: 16/16, positive control | `fe4df808a` |
| S | clean + both controls | `fe4df808a` |
| W1/W2 | worker = archived v27 + closed list; 5 causal controls | `d492e0d5c` |
| Makefile/tools | v28 block, contract check, builder, link script (`bash -n`), profile test 7/7, `test-v28-last-block-static` | `215ff7098` |
| M1-1 | red without the carrier, green with it (caught a mangled define) | `215ff7098` |
| L | `CONFINED_V28_HOLDS` (15 groups), ships ok, 2 red cases | `fe4df808a`, `7a04885ec` |
| PIN | 11 core files agree in both trees, one-byte red case; v27 archive 5/5; frozen set 2,862 | `fe4df808a` |
| PL-1-v28 | `PL1_V28_HOLDS` 6/6 (Chrome + Firefox x3), self-test 6/6 | `5fdcc97e1` |

## Next (after the owner's link; spec 7.3, 11)

1. **P-v28**: hashes, contract, log defines (v27 + v28), frozen set, archive `build/archive/e2-editor-v28-<wasm8>-worker-<worker8>`.
2. **Cutover.** Page `workerUrl` + `PINNED_WASM_SHA256`. Generation 82 = 81 + page + client; exclusions = 81's + `sdk/v28-last-block-worker.js`; bundle line red/green/red.
3. **S4 a-e.** Write `tools/check_v82_last_line_bullet.py`, derived from `check_v81_blank_line_bullet.py` (the PL-1 tool shows the import pattern and the click-below-text point).
   - Fixtures for S4-b, S4-d are made via a native `saveAs`; real Heading 1 for heading/body.
   - `fallback.restoreConfirmed` N/N.
4. **Freeze gen 82** -> F3-82 (no declared move), F4-82, V0′-82, E1-C.
5. **Host 0.2.44** (owner's DDEV slot) -> Files workflow -> owner hand tests (a)-(d).

**Accumulated uncounted engine changes since 0.2.26: v22-v27, + v28 once linked.** K and the count chain stay batched.

## Cautions

- **Bound tools:** derive, never edit (`run_e2_c_product_path.py`, `check_v8x_*`, the v80-v81 tools; S3's tool was imported, not edited).
- **Cross-session:** DDEV is shared; do not touch the owner's desktop processes.
- **What the shell tests show:** `page-select-all.test.mjs` U2 is red by construction since the v27 cut-over (named, not fixed). `check_relink_queue.py` has three pre-existing drifts (named, not fixed).

## Section 34.4 this session

- **Fixed-by-execution: 9.**
  - native-q52 (3): the self-test scope index; the headings reader's target; amendment 2's UNSAFE direction.
  - E1's fake markup had no `<body>`.
  - E4's refused-row expectation.
  - M1-1 caught the mangled define.
  - The L alignment on a bare brace.
  - The V0 baseline (HEAD -> 3a6998b33).
  - The pin red case first run on an empty copy (redone properly).
- **Fixed-by-review: 20** (the spec's one round).
- **Fable rulings: 1** (ruling 4).

## Language

- Replies to the owner: Taiwan Traditional Chinese, with A/B/C options.
- Evidence and handoff: English.
- Specs and findings: zh-TW.
