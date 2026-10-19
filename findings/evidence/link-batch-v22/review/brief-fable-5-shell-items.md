# Ruling request 5 (v22): the shell items after the link — scope, criteria, order, and the host step

To: fable (external judge). From: the main session (opus), 2026-10-19. **Read-only for you**: read files and `git show`. No browser, no make, no ddev, nothing written.

**Authority.** The owner, 2026-10-19: 「請繼續並且自主執行，直到需要交接。若遇到需要裁決的地方，則發給fable，我授權他帶我決定」. Then: 「但fable的決策要白話跟我講」. So: decide for the owner, and **put a short plain-language section in zh-TW for the owner first** (「裁決（白話，給擁有者）」, as ruling 4 did). Read `CLAUDE.md` 「驗收判準的形式」 §1–§11 before ruling.

## Facts (each checked by the main session today unless marked otherwise)

**F1 — where v22 stands.**
- The spec is `specs/SPEC-M3-link-batch-v22.md` (pinned `937bc684`; §10 and §10.1 appended). The link ran 10:39–10:42.
- Every v22 criterion so far is green:
  - S3 and S1-red before the link;
  - S1, S2 = 0 and I1-v22 PASS after it (`3ba23e05`);
  - C1 PASS: 24/24 in Chrome and Firefox, the positive control on v21 crashing in both;
  - H1: 6/6 ok (`473918f1`).
- v22 is archived (`wasm_sdk_probe/build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/`) and **unbound**. `dist/`'s page and shell are still v74 pointing at v21 (`605cf24b…`, HTML `1d158149…`). The tree's `web/e2-editor-app.js` and `web/e2-editor.html` are byte-equal to `dist/`'s.
- Spec §7 step 3 says: "the shell items: item 2's re-enable, 152, 154's page rule and 154's host criteria — their criteria appended before they run". Then: freeze the shell, the host version, `BINDING`, and the count chain (K).

**F2 — the three shell changes, as the code stands.**
- **Item 2's entry** is off by one constant, `const PASTE_MARKDOWN_ENTRY_SHIPS = false;` (`wasm_sdk_probe/web/e2-editor-app.js:72`, comment `:62-71`).
  - It gates the toolbar button (`:1225-1230`), `openMarkdownDialog` (`:2347`) and `insertMarkdownFromDialog` (`:2374`).
  - Turning it on is one token. The v22 manifest declares `pasteMarkdown`, as v21's does.
- **Finding 152's fix 3**: in `closeMarkdownDialog` (`:2357-2364`), `el.sink.focus({ preventScroll: true })` becomes `el.sink.blur(); el.sink.focus(...)`.
  - It was measured only in a mirror on v21 (`findings/evidence/link-batch-v21/shakedown/diag-dirty-move/report-*-fix3*.json`): headless Chrome V5 3/3 and V11c 3/3, headed Chrome V5 1/1, Firefox V5 1/1.
  - Fix 3b (rAF-deferred focus) was never run.
- **Finding 154's page-side rule**: `#markdown-dialog:not([open]) { display: none; }` in `web/e2-editor.html` (the dialog is at `:369-378`, its styles at `:234-250`). The host already carries its own rule (0.2.26, `#litecore-editor-root dialog:not([open])`).
- Changing the HTML changes the engine package's buildId and needs a new host version (finding 154 「修法選項」).

**F3 — item 2's criteria as they exist.**
- `specs/SPEC-M3-link-batch-v21.md` §11.2 holds M0–M11 and the record arm, with the general rules in §11.0. Read with:
  - §12.1 (valid UTF-8 before dispatch);
  - §12.2 (the shakedown arms' readings);
  - §12.3 (e) (item 2 withheld in v21; M1–M6 and M9–M11 never run; their defaults taken).
- The operational arms are `findings/evidence/link-batch-v21/shakedown/ARMS-item2.md` (85 KB, committed `8f1dbf0a`, rulings §9). The smoke rulings S3–S6 are in `shakedown/README.md` §1.
- **The machinery exists and has never produced evidence.**
  - Tools: `tools/run_v21_shakedown_item2.py`; `tools/judge_v21_shakedown_item2.py` (self-test 69 red cases); `tools/v21_item2_population.py`; `population.json` (M1 29 items, M3 35, M4 38 collapsed, 14 range, 5 protected, M5 19). Instruments S-1..S-11, with tests.
  - The only run was one Chrome smoke on v21: 01:35–02:20, i.e. **45 minutes for N=1**, plus three partial re-runs. The smoke found finding 153 (M3's ENG-65536) and the runner faults R1–R5, all fixed before ruling 1.
  - **No item-2 evidence run (N=3, both browsers) has ever started.** The N=3 two-browser run will take hours [inferred from the smoke].
- **M0** (the scanner's model test) was run by part E. `src/markdown_paste.hpp`, `tests/markdown_paste_model_test.cpp` and `tests/markdown_paste_expected.json` have not changed since `516e53e4`/`975343c2` (`git log`), and v22 compiles that source unchanged (S3).
- **Bindings to move for v22** (the main session's reading):
  - the judge pins `WASM = db3408f5…` (v21) and `EXPECT_PAGE = 3d511216…`, the page as served during the smoke (`judge_v21_shakedown_item2.py:32-33`);
  - the runner builds its mirrors with `v21_shakedown_common.build_mirror`, whose default profile is `e2-editor-v21` and whose `EXPECTED` table has no v22 entry;
  - `diag_v21_dirty_move.py` (152's V arms) uses the item-1 runner's `Pages`, also on v21.

**F4 — finding 152's own criteria** (`findings/152-…md` 「裁決」; fable ruling 1 Q3), written for "the batch that ships item 2":
1. V5 (type 0 ms and 300 ms after the dialog closes), V11c and V11d: N=3, both browsers, and the typed characters land in the document.
2. The owner hand-tests in a real Chrome: type once after 插入 and once after 取消.
3. If not done: no entry.

The ruling also said the blur's side effects on other blur-related page paths were never measured.

**F5 — finding 154's v22 work items** (fable ruling 3, `findings/154-…md`):
1. The page-side rule (F2). Item 2's **host** criteria must measure the dialog **closed** (not displayed; nothing of it under the click point) and **open**. The reset also zeroes `dialog`'s margin, so an open dialog may sit at the top left instead of the centre [inferred from CSS, unmeasured].
2. "宿主 production-UI 臂加一份由 DOM 列舉的檢查：讀所有隱藏部件計算後的 display（判準形式二）。第一次計入之前，先依 §34.3 審核一次。"
- Also registered there: L-154-diag-second-click. If the 154 diagnostic is reused in that counterfactual shape, `measure()` must wait for `ready` and `pending == "0"`, with `0226/diag-154-chrome-20261017T181633.json` as its red case.

**F6 — item 1 on v22.**
- Item 1's criteria (v21 §11.1, D1–D14) passed on v21's bytes. D2 passed on host 0.2.26.
- v22's engine is v21's source with v21's defines. It differs in one wasm function's code generation (`probe_engine.o` recompiled) and in the loader's stack literal (`post-link/README.md`).
- The shell changes in F2 touch only the dialog's open and close paths and one CSS rule.
- Nothing in spec v22 re-runs item 1. K, the count chain, is the regression net for the product paths.

**F7 — the host and the owner's environment.**
- The host is a Nextcloud app on the owner's ddev (`~/Projects/Nextcloud_Apps/…`), currently 0.2.26 (host `3c01876`, engine package `f5f0df762e1855f2`).
- A new host version is needed for F5.1's host criteria and for K.
- Standing practice from 10-17: the main session asked before each ddev step; it then packaged and installed 0.2.25 and 0.2.26 itself, at the owner's word.
- The owner's hand tests are not reported: 0.2.26's, and 152's criterion 2 would be another.
- K is 7–8 hours (0.2.26's took 7 h 49 m) and runs in the owner's window, detached (`release-count-batched`, `owner-can-run-long-chains`).

## What the main session proposes (argue with it)

- **P1 scope:** F2's three changes. F5.2's DOM-enumerated check is **not** in v22: it is new machinery that needs a two-seat review before its first count (§34.3), and no v22 measurement forces it. Registered with a default. F5.1's host criteria are in.
- **P2 item 2's criteria:**
  - Carry v21 §11.2 M0–M11 and the record arm, §12.1, §12.2, ARMS-item2 and smoke rulings S3–S6 **verbatim**. Only the identity pins move: wasm `f7a40bcc…`, and the page = the tree's page with F2 applied, repointed to v22.
  - M0 stands without a re-run (F3).
  - Defaults as written: if not done or red, item 2's entry does not ship (`PASTE_MARKDOWN_ENTRY_SHIPS` back to false before the freeze), L-md-sdk-callable stays.
  - The population is regenerated by its tool and must equal the committed `population.json`. The runner already refuses otherwise.
- **P3 152:**
  - Fix 3.
  - F4.1 on the final shell and v22, N=3, both browsers.
  - F4.2, the owner's hand test, is a precondition for item 2's entry reaching users: the host version that ships the entry is not called shippable before it.
  - Blur side effects: covered by the page's node tests plus K. No new arm.
- **P4 item 1:** no re-run before the freeze; K covers it.
- **P5 host:** within this autonomous run the main session packages host 0.2.27 (v22 profile, the frozen shell v75, the HTML with the rule) and installs it on ddev the way 0.2.26 was. It then runs F5.1's host criteria and re-pins and binds as in v21 §12.6.
  - The run stops and hands off before K and before the owner's hand tests.
  - If you rule that ddev needs the owner's word, the handoff point is the shell freeze.
- **P6 order:**
  1. Append the criteria to the v22 spec (§11) and commit.
  2. Make the tree edits (F2) with their unit tests red first.
  3. Move the bindings (F3).
  4. Item 2 evidence (N=3, Chrome then Firefox, detached).
  5. 152's V arms.
  6. Freeze the shell v75 and cut the page over to v22.
  7. Host 0.2.27 and F5.1.
  8. Re-pin and `BINDING`.
  9. Hand off: K and the hand tests.

## Questions

- **Q1.** Is P1's scope right, in particular leaving F5.2 out of v22?
- **Q2.** Can item 2's v21 criteria carry over verbatim with only the identity pins moved (P2), or does anything in them need restating for v22? For example, M3's size arms are now expected to pass (C1). Does M0 stand?
- **Q3.** For 152: fix 3 or 3b, the criteria, and whether the owner's hand test gates the entry.
- **Q4.** Item 1 on v22: is K enough, or does anything need re-running before the freeze?
- **Q5.** May the main session package and install host 0.2.27 on the owner's ddev within this run (P5)? What exactly are F5.1's host criteria for the open and the closed dialog: form and default?
- **Q6.** Is the order in P6 right? What is the handoff point?
- **Q7.** Anything the brief gets wrong or leaves out.

## Answer format

As ruling 4:
1. 裁決（白話，給擁有者）, zh-TW, short;
2. answers Q1–Q7 in English, each with its form (§1) and its default (§2);
3. the F-claims you checked;
4. "What the main session must do next, in order".
