# Handoff: v28 cut over, S4 holds, generation 82 frozen, F3-82/F4-82/V0′-82 hold, host 0.2.44 packaged offline -- install waits for the owner's slot

Checkpoint **2026-10-30 ~23:20 +0800**. Supersedes `HANDOFF-2026-10-30k-v28-link-handed-to-owner.md` (and its addendum) for what is next.

Study HEAD **82c4c6dcb** plus this file's commit. Untracked, all to be kept:
- `codex-claude-code-delegation.md` -- not ours;
- native harness binaries under `findings/evidence/176/native*/build-*/`.

**No runner is running.**
- `dist/` serves **frozen generation 82** / `e2-editor-v28` (wasm `13f674e4…`).
- The live host still runs **0.2.43**, the daily uncounted candidate.
- Candidate host **0.2.44** is packaged (engine `dacdfa20fd4ff1ea`), not installed.

## Owner state

**Pending: the owner's DDEV slot for 0.2.44** (`findings/evidence/host-0.2.44/README.md`, "Next"). Ask with A/B; write `slot.json` with the explicit no-site answer (precedent: `host-0.2.43/slot.json`). No slot -> no install; 0.2.43 stays the daily candidate.

## Done this session (evidence `findings/evidence/v28-083/`, spec `specs/SPEC-M3-v28-last-line-fallback.md`)

| Step | Result | Commit |
|---|---|---|
| Cutover | `build_cutover_page.py`: exactly two lines (pin `13f674e498a56c8a`, worker URL); `make e2-c-assets` copied page + client; live shell vs 81 = exactly page + client; E1-C intact | `fc85cce5a` |
| Spec append 1 (14) | S4 procedure pinned before any run (fixtures, click below the text, no Enter where the fixture's last paragraph is the target, wrong-button map, S4-c equality) | `61633e7df` |
| S4 tool + fixtures | `tools/check_v82_last_line_bullet.py`, `tools/v82_f_products.py`; three ODTs saved once by the native core (`fixtures-s4/`), read through the instrument's reader | `61633e7df` |
| **S4** | `S4_HOLDS`: 8 cells x 2 browsers x 3 (c: x2 arms). All five actions verified by the fallback (2 blocks, last block = target, restore confirmed, saved state, undo); table refused with the new sentence, no selection left behind; blank document unchanged (24 runs, one user-visible value); gen 81 red for 083 in every judged cell. Self-test 130/130. Six mutations caught (press-list-none on its re-run; the first had one `page not ready` NE, kept) | `d506643ad` |
| Freeze 82 | `a02673fa0dd34b6b`, file `da4e595d…`; = 81 + page + client; 81's ten exclusions + `sdk/v28-last-block-worker.js`; Makefile bundle line -> v82 (red/green/red) | `6e3e14f1b` |
| F3/F4 tools | derived by `derive/derive_v82_tools.py`; `read_v82_f3_equal.py` (F3-81 baseline, no declared move); stale scan; F4 preflight READY + 2 reds | `00e3f352f` |
| **F3-82** | `F3_82_EQUAL` 46/46 per browser vs F3-81; self-test 8/8; reading 1 exactly F3-81's four | `1b905d10c` |
| **F4-82** | 24/24 PASS | `1b905d10c` |
| **V0′-82** | run-02 `V0_PRIME_HOLDS` (five stages incl. v81; put back to 82; E1-C intact). run-01 kept (red on F4-81's re-read: input-path spelling) | `fa36a6e78` |
| **Host 0.2.44 offline** | worktree `host-0.2.44` at `a97724f` (version only); engine `dacdfa20fd4ff1ea`; delta = page + client changed, v28 four added, v27 four removed; every gate (v25, v79, v26, v27, v28) holds; DELTA_HOLDS 9/9 reds, PACKAGE_HOLDS 22/22, OFFLINE_INSTALL_READY | `2a6c1e52e`, `82c4c6dcb` |

## Next

1. **Owner's slot** -> `install-0.2.44.py --preflight-only`, then `install-0.2.44.py` (from `findings/evidence/host-0.2.44/`).
2. Files workflow (`wasm_sdk_probe/tools/run_calc_editor_host.py`, as 0.2.43) -> `capture-after.py <install-dir> <workflow-dir>`. The named limit L-capture-after-expired-lock-lazily-deleted may show again.
3. Owner hand tests (a)-(d) (README "Next"); then the owner decides whether 0.2.44 replaces 0.2.43 as the daily uncounted candidate.

**Accumulated uncounted engine changes since 0.2.26: v22-v28.** K and the count chain stay batched (owner, 10-12).

## Cautions

- **Bound tools:** derive, never edit. New this session and now bound: `check_v82_last_line_bullet.py`, `v82_f_products.py`, the v82 F3/F4 tools, `read_v82_f3_equal.py`, `v28-083/v0/run_v0_prime.py`, the host-0.2.44 scripts.
- **Generation 81 readers are NE on the live tree by construction** (S3, S2′, F3-81, F4-81); V0′-82 re-reads them with 81's files put back.
- **V0′ argv spelling:** a re-read must use the committed result's exact argv, path spelling included (F4-81 recorded `…/wasm_sdk_probe/../findings/…`).
- DDEV is shared; do not touch the owner's desktop processes.

## Section 34.4 this session

- **Fixed-by-execution: 4.**
  - `make_s4_odts.py` repo-root depth (`parents[2]` -> `[3]`), before any output.
  - The host gate's E1-C read: U-v28's receipts end in an `exit 0` line.
  - V0′-82's v81 F4 argv path spelling (run-01 red, run-02 holds).
  - `prepare-release.py` syntax: the E1-C fix's `'\n'` escape turned into a real newline by the derivation (package-run-01 never started).
- Re-measured, not a fix: S4's press-list-none mutation (one `page not ready` NE; re-run 6/6 caught).
- **Fixed-by-review: 0.** **Fable rulings: 0.**

## Language

- Replies to the owner: Taiwan Traditional Chinese, with A/B/C options.
- Evidence and handoff: English.
- Specs and findings: zh-TW.

## Addendum (~23:55 +0800): 0.2.44 installed

The owner answered 「A 現在裝（建議）」 (`findings/evidence/host-0.2.44/slot.json`). Only litecore was running; nothing was stopped.
- `CANDIDATE_INSTALLED`: host main a97724f, engine `dacdfa20fd4ff1ea`, documents and locks preserved.
- Files workflow 52/52; capture-after `holds: true` (empty lock table).

**Next:** the owner's hand tests (a)-(d) (`host-0.2.44/README.md`), then the owner decides whether 0.2.44 replaces 0.2.43 as the daily uncounted candidate (A/B). Rollback: `rollback-package.sh`.

## Addendum 2 (2026-10-31 ~00:05 +0800): hand tests pass, 0.2.44 is the daily candidate

- The owner reported 「已經測完，皆符合你的預期 / 選A」, then 「d有做」: (a)-(d) all as expected on 0.2.44, the optional table case included.
- **Decision A: 0.2.44 replaces 0.2.43 as the daily uncounted candidate** (`findings/evidence/host-0.2.44/README.md`). Finding 176 and 083 appends record the last line as fixed; the one-paragraph document stays 083's sentence by design.
- **The v28 batch is complete.** Nothing is pending from it. Still open from before: K and the count chain (batched; accumulated uncounted engine changes since 0.2.26: v22-v28); the named limits in spec v28 section 9 (L-fallback-html-read-is-new-on-this-path is unmeasured).
