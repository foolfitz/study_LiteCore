# Handoff: finding 176 batch shipped -- host 0.2.43 installed, owner hand tests done; two owner decisions open

Checkpoint **2026-10-30 ~16:55 +0800**. Supersedes `HANDOFF-2026-10-30h-v27-linked-gen81-frozen-f3-f4-v0-hold.md` (including its Addendum); that file still holds for whatever it says that is not superseded here.

Study HEAD **860b2a0f3** plus this file's commit. The tree is clean apart from the same three untracked files, all to be kept:
- `codex-claude-code-delegation.md` -- not ours; preserve it;
- `findings/evidence/176/native/build-01/f176-native` and `build-02/f176-native` -- native harness binaries.

**No evidence runner is running.** `dist/` serves generation 81 / profile `e2-editor-v27`. The live host runs **0.2.43**.

## Owner state

Pending with the owner, in this order:
1. **A/B: does 0.2.43 replace 0.2.42 as the daily uncounted candidate**, given the named capture-after red (below)? The main session recommends **A**. The rollback is prepared: `findings/evidence/host-0.2.43/rollback-package.sh` restores the exact 0.2.42 engine; the label stays 0.2.43. Until the owner answers, the records still name 0.2.42 as the daily uncounted candidate while 0.2.43 is what runs. The slot in `slot.json` ends 17:01 +0800; a rollback after that needs a new slot (A/B, with an explicit no-site answer).
2. **Optional product question, the owner's**: should the host show the status strip (「上次操作」) at all? Default if never decided (spec append 1, item 4): the strip stays hidden on the host, and the shell item is carried only by the mirror measurements.
3. **For information, not a question**: the 083 path (a blank one-paragraph document; the last empty line) stays a toast by ruling 3 Q5 (`L-083-stays-a-toast`). Candidates such as `.uno:SelectAll` belong to a later batch, native measurement first (spec 2).

Standing:
- DDEV is used by another session. The owner said today that other DDEV projects may be stopped when DDEV is needed; during the slot only litecore was running, so nothing was stopped (`ddev-before.json`, `ddev-after-slot.json`).
- Judgement calls go to the owner as A/B/C, and to fable when the owner says so.

## Done since 10-30h (all under `findings/evidence/host-0.2.43/`, see its `README.md`)

| Step | Commit | Result |
| --- | --- | --- |
| Offline package | `b99aa6ff4` | worktree branch `host-0.2.43` at **ae8240d** (version only); engine **741afd80a36e673b**; delta vs 0.2.42 exactly the page + v27 x4 added + v26 x4 removed; every v25/v79/v26/v27 gate holds (F3-81 reading 1 exactly the four declared problems); `DELTA_HOLDS` 8/8 reds, `PACKAGE_HOLDS` 22/22, `OFFLINE_INSTALL_READY` |
| Install (owner slot, answer A) | `d95224e3a` | `LIVE_PREFLIGHT_READY`; `CANDIDATE_INSTALLED`: host main 93b1ebc -> ae8240d, `installed_version` 0.2.43, documents and locks preserved across the install |
| Files workflow | `d95224e3a` | `files-workflow-01/`, Chrome and Firefox: **52/52 PASS** |
| capture-after | `d95224e3a` | `post-install-identity.json`: **`holds: false`** on `lockRowsEqualInstallAfter` only (see Cautions) |
| Handoff addendum | `85dea79db` | appended to 10-30h |
| Owner hand tests + corrections | `860b2a0f3` | README section "Owner's hand tests on 0.2.43"; spec append 1; finding 176 append |

**Owner hand tests on 0.2.43 (~16:45 +0800)**, verbatim in the README; screenshot `owner-hand-test-b-toast-20261030-1646.png`:
- (a) as expected: a bullet on an empty line with a paragraph after it shows no toast (engine item C, observed on the host);
- (b) 083's sentence, as designed (spec 2 「083 的路不改」, `L-083-stays-a-toast`);
- (c) as expected: Ctrl+Z undoes the list.

**Correction (spec `specs/SPEC-M3-v27-finding-176.md`, 追加一; finding 176, 追加 2026-10-30 下午).** The host has hidden the whole `.statusbar` since host 0.2.6 (`96a13b9`, 2026-10-06; `templates/editor.php:51`); the rule is in both 93b1ebc and ae8240d. So 「上次操作」 was never on the owner's screen. In summary, the append:
1. corrects spec 1's attribution: the 「• 項目符號 失敗」 reading was a mirror measurement (S2 run-02, F3), not the owner's screen; only the toast was observed there;
2. keeps the shell item (「待確認」 instead of 「失敗」): it is real, but only on the mirror and the standalone page, where U1 and S2′ measured it. Nothing new is added to make it visible on the host (CLAUDE.md section 4);
3. withdraws the two strip clauses of the spec 7.4 hand tests ((a) "shows the time", (b) 「待確認」) as unobservable on the host: neither passed nor failed. The hand tests are judged on the toast alone;
4. sets the default: the strip stays hidden on the host.

Finding 176 status: the 046 cell (a) is fixed, confirmed by the owner on the host; the 083 cell stays a toast by design.

## Next

1. Relay the owner's answers. On **A**, record 0.2.43 as the daily uncounted candidate (memory and the next handoff). On **B**, run `rollback-package.sh` in a slot, then the Files workflow.
2. Re-check `make -k test-e2-c-static`'s shell-bundle test against generation 81 (Cautions). The target contains M1-1: check `uptime` and `pgrep -a make` first, per CLAUDE.md.
3. Otherwise nothing is queued in this batch. K and the count chain stay batched (owner, 2026-10-12); the uncounted engine changes since 0.2.26 now span **v22-v27**, and go into the next engine batch's count. The 083 candidates wait for that batch, native measurement first.

## Cautions

- **Cross-session.** Another session uses DDEV. Do not touch DDEV or the owner's desktop processes. Read the live host repo only; package in a worktree.
- **The capture-after red is named, not fixed.** The stale lock row 5412 (expired ~5 h before the install) was present in the installer's after-state and is gone now. Nextcloud files_lock deletes an expired row whenever any request looks it up (`apps/files_lock/lib/Service/LockService.php:141-155`, `:337-339`); our tools only read the lock table, and which request triggered it was not measured. Named **L-capture-after-expired-lock-lazily-deleted**. `capture-after.py` is a derived copy kept byte for byte; do not redesign its lock clause (new mechanism), and do not rewrite the verdict.
- **Bound tools.** `run_e2_c_product_path.py`, `check_v79_blank_bullet.py`, `check_v80_blank_bullet.py`, and every v80/0.2.42/0.2.43 tool or script: derive, never edit.
- **`make -k test-e2-c-static`.** Three pre-existing red unit tests, named in `findings/evidence/v27-176/pre-link/README.md` (section `make -k test-e2-c-static`). The shell-bundle one (`real_manifest_matches_the_real_tree`) was expected to close at generation 81's freeze; it has not been re-run since. The other two (`copy-lies`, `inducing_arms_hold_the_guard_off`) stay red against bound runners.

## Section 34.4 this round (10-30g onwards)

- Fixed-by-execution: **1**. I1 red case (c)'s first copy was read-only and not mutated; it is kept as a control run.
- Corrected by the owner's observation: **1**. The 「上次操作」 attribution (spec 1, spec 7.4 (a)/(b)), corrected by spec append 1 after the owner's hand test. Counted separately: it is neither execution nor review.
- Fixed-by-review: **0**.
- Fable rulings: **0**.

## Language

- Replies to the owner: Taiwan Traditional Chinese, A/B/C for options.
- Evidence and `handoff/**`: English.
- Specs and findings: zh-TW.
