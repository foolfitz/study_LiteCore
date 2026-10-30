# Handoff: finding 176 batch -- v27 linked, generation 81 frozen, every spec 7.3 check holds; next: host 0.2.43

Checkpoint **2026-10-30 ~16:10 +0800**. Supersedes `HANDOFF-2026-10-30g-v27-link-handed-to-owner.md`; that file still holds for whatever it says that is not superseded here.

Study HEAD **fd3aaf0fc** plus this file's commit. The tree is clean apart from three untracked files, all to be kept:
- `codex-claude-code-delegation.md` -- not ours; preserve it;
- `findings/evidence/176/native/build-01/f176-native` and `build-02/f176-native` -- native harness binaries.

**Nothing is running.** `dist/` serves generation 81 / profile `e2-editor-v27`.

## Owner state

- The owner linked v27 at 14:19-14:22 and reported the JSON. It matched exactly (`withheld: []`, wasm `c089dfd6…`).
- DDEV is used by another session. The host install needs the owner's slot (A/B question, with an explicit no-site answer in `slot.json`).
- Judgement calls go to the owner as A/B/C, and to fable when the owner says so.

## Done since 10-30g (all under `findings/evidence/v27-176/`)

| Step | Where | Result |
| --- | --- | --- |
| P-v27 | `post-link/` (`c29101c34`) | log, contract, manifest, I1 PASS vs v26 + 3 reds, frozen set 2,757/2,757 with exactly 4 new, v27 literal only in v27's wasm, archive `build/archive/e2-editor-v27-c089dfd6-worker-8152448a` |
| Cutover | `cutover/` (`bbee9b040`) | `build_cutover_page.py`, two lines; page `b63d8ee5` |
| S3 | `s3/` (`abebdc2f9`; tool `check_v81_blank_line_bullet.py`, products `v81_f_products.py`) | **S3_HOLDS** 12/12; three mutations caught (`cosmetic-review` only by the worker reply row); self-test 19/19 |
| S2′ | `s2p/` (`54adf80fb`; tool `check_v81_blank_bullet.py`) | **S2P_HOLDS** 24/24 (strip 「• 項目符號：待確認」); self-test 11/11 |
| Freeze 81 | `freeze-81/` (`e5793d0a4`) | `6eb7ca108ea77c4a`; differs from 80 by the page alone; Makefile bundle line -> v81 with four witnesses |
| F3-81 | `f3-81/` (`f9b493563`; `run_v81_f3_clipboard.py`, `read_v81_f3_equal.py`) | **F3_81_DECLARED_ONLY** (45/46 per browser equal F3-80; the bulleting cell PASS->FAIL with v27's reason; `held` true->false); reading 1 **F3_RED with exactly the four declared problems**; self-test 10/10 |
| F4-81 | `f4-81/` (`f9b493563`) | **24/24 PASS**; preflight READY, two identity reds |
| V0′-81 | `v0/` (`fd3aaf0fc`) | **V0_PRIME_HOLDS** (stages v24/v25/v79/v80 byte-identical; put back to 81) |
| E1-C | `v0/e1-c-after-put-back.json` | `intact: true` |

Spec 7.3's default ("any check not run, NE, or with an undeclared move: 0.2.43 is not sent for install") is satisfied: every check ran and holds.

## Next: host 0.2.43 (spec 7.4)

Derive from `findings/evidence/host-0.2.42/` and do not edit those files. Follow the README's structure:
1. Isolated worktree `wasm_sdk_probe/build/host-0.2.43/litecore`, branch `host-0.2.43` from **93b1ebc**. The live repo `~/Projects/Nextcloud_Apps/litecore` is on main at 93b1ebc, clean. Its only change: `appinfo/info.xml` 0.2.42 -> 0.2.43.
2. **`prepare-release.py`.** Predecessor engine archive `host-0.2.42-engine-01e6c3fb62626d16`. The editor page is generation 81's (`v81_four_arms_identity.py`, profile `e2-editor-v27`).
   - Expected delta against 0.2.42, exactly:
     - changed 1: `e2-editor-app.js`;
     - added 4: `profiles/e2-editor-v27/*`;
     - removed 4: `profiles/e2-editor-v26/*`, after first checking that no other page of the 0.2.42 package uses v26.
   - Red cases: one more changed, one fewer, and v27's wasm equal to v26's (= no new engine).
   - Gate: 0.2.42's gate plus v27's: PL-1, pre-link E1-E4/V0/S/W/M1-1/L/PIN, P-v27, S3 and its mutations, S2′, F3-81 (reading 1 exactly `F3_RED` + the four problems, spec 8 item 5; reading 2 `F3_81_DECLARED_ONLY`), F4-81, V0′-81, E1-C.
   - From v27 on, no reading may require `held: true`.
3. **Offline checks**, then ask the owner for a slot: `check-delta.py` with its red cases, `offline-package-check.py`, `install-0.2.43.py --offline-only`.
4. **In the slot.** `slot.json`, `--preflight-only`, the install, the Files workflow (`run_calc_editor_host.py`), `capture-after.py`. Then the owner's hand tests:
   - (a) a document with text, an empty line with a paragraph after it, bullet -> no toast; the strip shows time;
   - (b) a new blank document, bullet -> 083's sentence (normal style); the strip says 「待確認」;
   - (c) after (a), Ctrl+Z -> the list is undone.

Default: no slot, no install; 0.2.42 stays the daily uncounted candidate.

## Cautions

- **Cross-session.** Another session uses DDEV. Do not touch DDEV or the owner's desktop processes. Read the live host repo only; package in the worktree.
- **Bound tools.** `run_e2_c_product_path.py`, `check_v79_blank_bullet.py`, `check_v80_blank_bullet.py`, and every v80/0.2.42 tool or script: derive, never edit.
- **`make -k test-e2-c-static`.** It has three pre-existing red unit tests, named in `pre-link/README.md`. The shell-bundle one should now be re-checked against generation 81, since 81 is frozen and the page is copied.

## Section 34.4 this round (10-30g onwards)

- Fixed-by-execution: **1**. I1 red case (c)'s first copy was read-only and not mutated; it is kept as a control run.
- Fixed-by-review: **0**.
- Fable rulings: **0**.

## Language

- Replies to the owner: Taiwan Traditional Chinese, A/B/C for options.
- Evidence and `handoff/**`: English.
- Specs and findings: zh-TW.
