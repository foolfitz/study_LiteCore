# v21 WASM shakedown: results

Arms: `ARMS.md`, `ARMS-item1.md` (rulings §8), `ARMS-item2.md` (rulings §9), committed at `8f1dbf0a`. Those files are not edited after that commit; corrections are appended **here** and say what they replace.

**State (2026-10-17 03:00):**

- Phase B is built.
- One Chrome smoke has run per item: `smoke/item1/`, `smoke/item2/`. The smokes are development runs and are not judged.
- **No evidence run has started.**
- Two diagnostics are running: `diag-dirty-move/` and `diag-long-paragraph/`.

## 1. Rulings after the smoke (main session, 2026-10-17, before any evidence run)

Each ruling names the smoke observation that forced it. None moves a threshold in spec §11.

| # | ruling | forced by | replaces |
|---|---|---|---|
| S1 | **D4: the place-caret request may be `click` or `editorPlaceCaretV2`.** On an open range, the session's place-caret goes out as `click` (`narrow-editor-v2-session.js:734-737`, v67's path). The judge's `DEVIATION-D4-op` line is accepted, and the clause reads "one place-caret request, then the move". | item-1 smoke D4, 6/6 `click` | `ARMS-item1.md` D4's op name |
| S2 | **R-xlc's population is the `x-lc` arms whose script has a Backspace step** (3 arms). The group label alone gives 4. Record arm; no verdict. | item-1 smoke | `ARMS-item1.md` R-xlc "group x-lc" |
| S3 | **M5 is judged on the spec's wording: 0 requests and 0 connection attempts to the item's target hosts.** Targets are every `scheme://host:port` written in the item's bytes, plus the target-port listeners. An item with no URL has no target, so its M5 cell is its refusal. Every other non-mirror request is **recorded** with its host and window, not judged. The positive controls (`probe.wasm` and `/m5-control` in the **proxy's** log) stay required. | item-2 smoke M5: Chrome's own GCM/Google traffic fell in 6 of 38 item windows despite the quieting flags; a policy that stops it needs root | `ARMS-item2.md` M5 "0 requests to any origin other than the mirror's", which was the draft's stronger reading, not spec §11 M5 「對目標主機 0 個請求」 |
| S4 | **M4 placement on round-2 positions is confirmed by either of two checks.** (i) The engine caret equals the native `cursorAtPaste` rectangle. (ii) The after-paste signature equals the native `after.fodt.gz` of the same arm (DM-11 A's rule). Check (ii) reads the document instead of a coordinate, which fonts move on WASM (finding 113). A cell with neither is NOT_ESTABLISHED. | item-2 smoke `M4-T2-ccplain-M2`: caret 17 twips right of native; paste and Undo correct | `ARMS-item2.md` M4 "confirmed by the engine caret equal to the native `cursorAtPaste` rectangle" for round-2 positions |
| S5 | **M6 runs alone in a fresh browser**, as `ARMS-item2.md` M6 already says; the smoke's in-sequence M6 was runner fault R4. A paste the SDK gives up on after 30 s busy reads **FAIL** (the busy span exceeds the 10 s bound), not NOT_ESTABLISHED (judge fault J1, fixed). | item-2 smoke M6 | — |
| S6 | **`v21_input.key` mis-sends `#$%&'(` in Chrome** (as End, Home and the arrows: the character code used as a key code). No item-1 arm types them, so it is recorded, not fixed. Any arm that types them must use the clipboard instrument or a fixed key. | item-2 agent | — |

The judge changes that S3 and S5 need are execution-driven (§34.4): the witness is the smoke report that the old reading misjudged.

## 2. Product observations from the smokes (not verdicts; under diagnosis)

1. **D8 (e), item 1: a move key pressed while a delete is out takes the click-then-move range path.** The barrier's one-character range is read as the user's. A key pressed meanwhile is queued between the click and the move, so it runs at the click point: P2 «Bra scond» instead of «Bra second». [observed: smoke item 1]
   - Source: `web/e2-editor-app.js` `sendDocumentMove` (about line 3330) and the arrows' path (about line 3194) decide the shape without `deletesInFlight === 0`. Finding 131's rule A (`deleteActionFor`, about line 2787), the overlay (132) and the reopen caret (136) all apply that check. [source]
   - The arrows' path is 0.2.24 code, so the gap may predate v21. Measured in `diag-dirty-move/` V6.
2. **In a dirty document, the first Ctrl+Home/End's reply carries the pre-move caret.** The session sends a checkpoint `save` first. The move then completes `verified-move-readback` about 251 ms after its request, with the caret where it was before the move. An engine read later shows the caret at the target.
   - Seen in item-1 smoke D11b-dirty (reply `1564,1418`, later `3657,1970`), D6, and D8 (e). [observed]
   - Clean documents answer `documented-callback-*` in 33–50 ms. [observed: D7]
   - This is the shape of L-142-readback-overtaken (spec §9.1). That limit is registered as a stall case. Here it appears every time after a checkpoint save, and D7's population (clean documents) cannot see it.
   - Whether typed text then lands at the old caret: `diag-dirty-move/` V1–V4.
3. **A 65,536-byte single CJK paragraph pasted as Markdown crashes the WASM worker** (`memory access out of bounds`). Direct to the worker it gets no reply. A 64 KiB corpus of short sections pastes fine. [observed: item-2 smoke and dev-r1]
   - M3's size arms say both complete.
   - The link rules set a 64 KiB pthread stack (`-sDEFAULT_PTHREAD_STACK_SIZE=65536`, `Makefile:483`). [source] That this is the cause is a hypothesis. [inferred]
   - Diagnosed in `diag-long-paragraph/`.
4. **M6's 64 KiB corpus took 32 s in a long browser session and 0.66 s on a fresh page.** [observed: item-2 smoke] Open.
5. **D6's `Z`, typed 3 ms after the Markdown dialog closed, produced no `beforeinput`.** It may be harness timing. Measured in `diag-dirty-move/` V5.
6. **The foreign load during the smokes**:
   - another session's Python script at 99.5 %;
   - the owner's desktop Chrome with an extension relay at 66–126 %;
   - Zen at 60 %.
   
   These made 6 D7 presses, one D9 sub-arm and D10 NOT_ESTABLISHED. [observed: the samples in the item-1 smoke report] The evidence runs need a quiet desk.

## 3. Identity after the fixes (2026-10-17, before any evidence run)

Fable ruling 1 (`review/ruling-fable-1.md`) and spec §12.3 (`e25ccc15`) moved the page and the session. The fixes were committed at `712f955a`; their red-first evidence is in `../fixes-ruling-1/`.

The evidence runs measure the new identity. Everything recorded before it — the smokes and the two diagnostics — ran on the old pins of `ARMS.md` §1. That record stays as it is, and none of it is evidence.

| item | before (ARMS.md §1) | after `712f955a` |
|---|---|---|
| page served (`build_cutover_page.py --profile e2-editor-v21`, no `--write`) | `3d5112161b23b060…` | `605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f` |
| `web/e2-editor-app.js` | `bd15e7ef…` | `59553850b3383e4fe6e48bbb8eaf82c5aeebe380bde4e8d9e9e35430b3176a1c` |
| `editor-shell-v2/narrow-editor-v2-session.js` | `443e0f1e…` | `f1509ff22e6e2d8d945cfd803d293fd4cf102cece27618f54825571a2e1ef3a8` |
| `web/e2-editor.html` | `1d158149…` | unchanged |
| shell digest over the tree sources (v73 bundle's module list) | `e0252c0b…` | `e35923a08107662d600d874f6986ef31aa8e8583955386929c26ebec62d82b06` |
| profile `e2-editor-v21` | wasm `db3408f5…`, worker `0d55bcfa…` | unchanged (no relink) |

The main session recomputed both pins: the page by `build_cutover_page.py`, the shell digest by `run_merge_wasm_shakedown.digest` over the bundle's modules. It re-pinned `tools/v21_shakedown_common.py` (`EXPECTED`, `EXPECTED_SHELL_DIGEST`); `test_v21_shakedown_common.py` gives 9 OK. The node suite at `712f955a` gives 596/596 and E1-C reads `"intact": true`; both were re-run by the main session.

## 4. Runner and judge changes for spec §12.3 (before any evidence run)

Spec §12.3 (b), (c) and (e) (`e25ccc15`, fable ruling 1) change what the item-1 runner drives and what its judge reads. The changes were made and committed before any evidence run, and no browser was started while making them. The judge was committed red first (`8b9b1b59`), then made green. These are spec-driven changes, not runner-error fixes, so the §34.4 tally does not move: no run was misjudged and no witness is needed.

Tools: `wasm_sdk_probe/tools/run_v21_shakedown_item1.py`, `wasm_sdk_probe/tools/judge_v21_shakedown_item1.py`, and the new unit test `wasm_sdk_probe/tests/test_v21_item1_judge.py` (the item-1 judge had none).

### 4.1 What changed

| # | spec | runner | judge | replaces |
|---|---|---|---|---|
| 1 | §12.3 (c), new criterion D14 | new arm `d14` | new clause D14 | — |
| 2 | §12.3 (b), D11 withdrawn for 22/23 | unchanged (it already records the requests, `#s-checkpoint` and the `beforeunload` read per press) | D11b's dirty half rewritten | `ARMS-item1.md` D11b dirty: "exactly one `save` request before the first move's request, and `#s-checkpoint` becomes 「有（r1）」", and its red case "no checkpoint `save`, or a second one: FAIL" |
| 3 | §12.3 (e) and §11.0 「第 2 項沒出貨時：頁面沒有入口」 | every arm's start state records the item-2 entry read | new clause E0 | — |
| 4 | §12.3 (e), the entry is gone | `d6` stays selectable but is recorded as `notRun: "not runnable: item 2 not shipped (spec §12.3 (e))"` and never driven | D6 printed 「未量」 per browser | `ARMS-item1.md` D6's steps (they need the dialog) |

**1. D14.**
- **Procedure.** Per round, plain3 then long60, each on a fresh load and open: real `Z` at the document start, with its reply awaited (the document is now dirty); the dirty read; real Ctrl+End; real `Q`; then the move's reply, the insert, quiet, an ask, and the product's save.
- **Reused, not copied.** This is `diag-dirty-move` V1 (plain3) and V4 (long60). The arm imports `diag_v21_dirty_move` and uses its `settle_long` (long60 waits for 60 page rectangles), `timed_keys` (Chrome: CDP presses on the monotonic clock; Firefox: one WebDriver chain with a pause) and `move_tail` (reply, insert, +500 ms ask, quiet, final ask, log, save, saved texts, summary). The report binds the diag tool's sha256.
- **Departure 1: `Q` is planned 20 ms after Ctrl+End, not 30 ms.** V1/V4 planned 30 ms, and the page saw 30.0–31.0 ms between the keydowns in Chrome and 32.7–34.6 ms in Firefox (every V1/V4 round in `diag-dirty-move/report-*.json`, fixed or not). Against §12.3 (c)'s 「30 ms 內」 most of those rounds would read NOT_ESTABLISHED. The judge reads the gap on the page's own keydown times, so the plan only has to land inside the window.
- **Departure 2: one added read.** After `Z`, the page's `beforeunload` guard is read (D11b's instrument). A document that does not read dirty has not set up the arm.
- **Pass, per round:** `Q` is the last character of the last body paragraph, read through the S-7 adapter (`v21_item1_marker.paragraphs_of`). Per fixture this must hold N/N, in both browsers.
- **The judge's own landing read.** The classes are the words diag's `q_class` printed for V1/V4 ("document end", "pre-move caret", "elsewhere"). The judge does not import the diag tool, which imports the runner and the browser stack.
- **Recorded, not judged:** the move's completion, its round trip, its reply time after Ctrl+End's keydown, and the request order. After fix 1 no `save` is expected before the move, but D14 judges only the landing.
- **Foreign CPU:** sampled per round and recorded, not gated. The window is established by the page's own keydown times, and the landing is an ordering property, not a time bound. D-18 A′ named D7, D9 and D10 as the timing-bound arms.
- **NOT_ESTABLISHED when:** the round is not done; the document did not read dirty, or `Z` was not answered; a keydown is missing; `Q` came ≤ 0 ms or > 30 ms after Ctrl+End; there is no saved document; `Z` is missing from the document start; or a fixture has fewer than N established rounds.
- **FAIL when:** `Q` is anywhere but the document end, there are 0 or 2+ markers, or the saved document is unreadable (the parser's message is the payload, as in D1).

**2. D11b dirty** (22/23 only; the clean half is unchanged).
- **Pass:** no `save` request before the second move's request, which covers both before Ctrl+End and before Ctrl+Home; `#s-checkpoint` reads 「無」 after both presses; `dirty` reads true after both.
- **NOT_ESTABLISHED** when `dirty` reads false after typing (the read is blind, unchanged). Also when fewer than two move requests are in the log, because "no save before a move" would then hold vacuously. That second NE clause is new.

**3. E0.**
- **What is read.** `Ctx.start_state()` (every arm calls it, including `v21_item1_sdk_arms` and `d14`) reads `ENTRY_READ` once the sink has focus:
  - `exists`/`hidden` for `#toolbar [data-action="paste-markdown"]` (`checkVisibility`, then a non-zero box);
  - `visibleOpeners`: every rendered control outside `#markdown-dialog` that names the dialog or Markdown. These are any `[data-action="paste-markdown"]` (the toolbar click handler's only route to `openMarkdownDialog`), `aria-controls`/`commandfor`/`popovertarget` on the dialog, and any button, link or menu item whose text matches `/markdown/i`;
  - `controlVisible`: the same read on `#toolbar [data-action="undo"]`;
  - the page variant.
- **A static read.** Nothing is clicked, so the start state is unchanged.
- **The judge, per browser:** every report must carry at least one read on the final shell (`v21`, `v21host`, `v21hook`, `v20`). The 0.2.24 page of D8's red case is not the final shell and is skipped.
  - Any read with the button rendered, or with a visible opener → FAIL.
  - A read whose control reads not visible (the read is blind), or a done round without the read → NOT_ESTABLISHED.
  - Otherwise PASS.
- **Not a new criterion.** It is §12.3 (e)'s 「殼層不提供入口」 read on the evidence runs' own start states. It is in the judge's criterion list, so a FAIL makes the item-1 verdict NOT PASS.
- **Checked without a browser.** The read was exercised only against a DOM stub in node (hidden, absent, visible, another opener, blind), a scratch check that is not committed. On the tree at `712f955a` the button stays in the DOM with `hidden` forced (`PASTE_MARKDOWN_ENTRY_SHIPS`), which is the `exists: true, hidden: true` shape.

**4. D6.**
- **Runner.** `arm_d6` and its inputs (the M6 corpus in the mirror, the Firefox clipboard prefs) are removed from the runner. They are in git at `e25ccc15` for the batch that ships item 2.
- **Judge.** For each browser with no done D6 round, the judge prints `D6 未量 (<why>); default 「未量，不做任何排序宣稱」`, where `<why>` is the report's `notRun` or "no D6 report".

### 4.2 Red first

| step | self-test | what it shows |
|---|---|---|
| before (`e25ccc15`) | 63/63 | — |
| cases added, clauses unchanged (`8b9b1b59`, the witness commit) | 66/79, green baseline **False** | D11b FAILs the §12.3 (b) shape under the withdrawn clause; 12 D14/E0 cases MISSING; the D6 rule NOT RED |
| the final case list against the `e25ccc15` clauses (scratch rerun) | 59/76, green baseline False (the 7 exit rules not rerun) | adds: the D11b "no move request" case reads FAIL where NE is required; the three later D14 cases MISSING |
| after | **83/83** | every case reads as required, each on its intended branch (checked by printing each case's verdict line) |

The four new D11b dirty FAIL cases (a save before Ctrl+End, a save before Ctrl+Home, `#s-checkpoint` not 「無」, dirty lost after a move) read FAIL at `8b9b1b59` only because that baseline already FAILs. They are vacuous there and meaningful after.

Red cases added (20 plus one rule):
- **D11b:** the four above; `NE` for no move request in the log.
- **D14:** `FAIL` for the marker at the pre-move caret on plain3 and on long60, and for an unreadable saved document. `NE` for a missing save, zero rounds, a fixture's rounds missing, the marker 30.5 ms after Ctrl+End, the marker keydown before Ctrl+End's, the document not dirty, the dirtying `Z` absent, and no keydown on the page.
- **E0:** `FAIL` for the entry visible in a report and for another visible opener. `NE` for a report with no entry read and for the read being blind.
- **Rule:** D6 skipped (chrome) or absent (firefox) is printed 「未量」 for both browsers.

`python3 -m unittest discover -s tests -p 'test_v21_*.py'` in `wasm_sdk_probe/`: 94 tests, OK.
- The new `test_v21_item1_judge.py` runs the self-test and checks that every criterion has a red case, and that D14, E0 and D11b-dirty each have a FAIL case and an NE case.
- It also checks that the runner and the judge agree: D6's `notRun` text, D14's fixtures, and the 20 ms plan inside the 30 ms window.
- One run during this work went red on `test_v21_shakedown_common` (`pageServed`/`shellDigest` false). `712f955a` had moved the page before `f5f60ac1` re-pinned it. It does not import these tools, and it gives 9 OK after the re-pin.

### 4.3 For the evidence run

- **The page to pass.** The judge's `--expect-page` is `605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f` (§3). The judge's own `PAGE_V21` constant is the old pin and is used only by its self-test's synthetic reports.
- **The arm list.** It now includes `d14` (`--rounds 3` gives 3 rounds per fixture, 6 per browser). `d6` may be listed or left out; either way the judge prints 「未量」.

## 5. Evidence runs (N=3, Chrome and Firefox)

Run 2026-10-17 05:43–09:12 by a subagent of the main session. This is fable ruling 1, "Overall" step (6). The tree was `1b247bdb`, plus the two tool fixes in §5.5. Chrome ran first, then Firefox, with one browser at a time under the S-9 lock. KWallet read `b false` before every run.

The desk was recorded before each run (`evidence/desk.log`). The load average was 0.15–1.45, and nothing of ours ran beside the runner. No `make`, no `--write`, nothing under `dist/`, no ddev, no host run. Every report says `"counted": false`.

Files, all under `evidence/`:

| dir | what |
|---|---|
| `item1/` | the item-1 reports judged (12: 5 Chrome, 7 Firefox), their `docs/`, and run logs |
| `judge-item1.txt` | `judge_v21_shakedown_item1.py --dir evidence/item1 --expect-page 605cf24b… --rounds 3`, with the judge at `c32fc13d` |
| `d2/` | D2's no-host predictor and its 0.2.24 red case, per browser (reports and run logs; the logs carry the tool's own verdicts) |
| `m7/` | M7 (`m7a`, `m7b`) reports and `docs-*` |
| `judge-m7.txt` | `judge_v21_shakedown_item2.py --dir evidence/m7 --expect-page 605cf24b…` |
| `v6e/` | the V6e record (`diag_v21_dirty_move.py --variants v6e --fix none --rounds 3`), per browser |
| `unit/` | the unit halves: D5 (`page-document-keys`, D5-gen), D12 (`sdk-worker-v21`), D13 (`closed-lists`), with file hashes; and `test_v21_*.py` after the judge fix |
| `superseded/item1/` | Chrome's first d1 run (D7 NE from foreign CPU; §5.4) |
| `witness/` | the three §34.4 witnesses (§5.5) |

### 5.1 Verdicts

Only the item-1 judge's verdict decides. Its last line is `VERDICT NOT PASS (1 criterion cell(s) not PASS)`; the one cell is D7 in Firefox.

| criterion | Chrome | Firefox | read from | note |
|---|---|---|---|---|
| D1 | PASS | PASS | judge, `d1` | 38 arms + 2 controls × 3. Chrome is the re-run report (§5.4). |
| D2′ | PASS | PASS | judge, `d2p` | move `documented-callback-visible-cursor`, Backspace `verified-boundary-noop`, P2 unchanged |
| D4 | PASS | PASS | judge, `d1` | 18/18 per browser carry `DEVIATION-D4-op` (`click`), accepted by ruling S1 |
| D5, unit | PASS | — | `unit/unit-halves.txt` | `page-document-keys.test.mjs` 18/18, `page-document-keys-generated.test.mjs` (D5-gen) 17/17 |
| D5-w | PASS | PASS | judge, `d5w` | Firefox PASS after judge fix J2 (§5.5). Before it, the judge read NE. |
| D7 | PASS | **NOT_ESTABLISHED** | judge, `d1` | Firefox: 2 of 192 +500 ms reads were posted at **550.1** and **553.5 ms** after the reply. Foreign CPU was clean, so the arm was **not re-run** (§5.4). |
| D7 (after ruling 2, appended) | PASS | **PASS** | judge, `d1` (`judge-item1-after-d7-rerun-2.txt`) | Firefox re-run once at the observer's constant 455 (spec §12.4, §5.7 below); Chrome stands on its constant-500 report. The row above stays as written. |
| D8 | PASS | PASS | judge, `d8` + `d8red` | (a)–(e) 3/3 each; 0.2.24 red case below |
| D9 | PASS | PASS | judge, `d9` | flagged hold: 1 move, ready 0 ms. Unflagged: Chrome 3 moves, ready 28–29 ms; Firefox 4 moves, ready 236–238 ms (≤ 500). |
| D10 | PASS | PASS | judge, `d10` | `第 60 頁，共 60 頁` at both reads, 3/3 |
| D11 | PASS (a, b, c) | PASS (a, b, c) | judge | D11b dirty read under §12.3 (b). D11c: the SDK reports `EDITOR_RESULT_INVALID` for both stale moves, the §12.2 (f) observation. |
| D12 | PASS | PASS | judge, `d12` | unit half `sdk-worker-v21.test.mjs` 17/17; `sdk/sdk-worker.js` = the profile's worker `0d55bcfa…` |
| D13, unit | PASS | — | `unit/unit-halves.txt` | `closed-lists.test.mjs` 12/12 |
| D14 | PASS | PASS | judge, `d14` | 6/6 per browser: `Q` at the document end. Ctrl+End→`Q` keydown gap 20.2–20.9 ms (Chrome), 22.9–24.8 ms (Firefox). The move completed `documented-callback-visible-cursor` in 34.9–43.1 ms, with no `save` before it. |
| E0 | PASS | PASS | judge | every start-state read: the button exists, is hidden, and has no other opener. 198 reads per browser, on v21, v21host, v21hook, v20. |
| M7 | PASS | PASS | `judge-m7.txt` | `m7a` + `m7b` 3/3 each. The judge prints every other M criterion as NE or FAIL (`missing`) because none was run; their defaults are taken by §12.3 (e). |
| D2 no-host predictor (v21) | PASS 3/3 | PASS 3/3 | `run_v21_d2.py`'s own verdicts | D2 itself is the host run after the freeze; not run (§5.6). |
| 0.2.24 red cases | red 3/3, as required | red 3/3, as required | | D8 (d) on 0.2.24 FAILs 3/3. D2 no-host on 0.2.24: `verified-selection-delete`, revision +1, 3/3. |
| R-xlc (record) | 9/9 recorded | 9/9 recorded | judge records | Backspace `verified-boundary-noop`, waited 2252–2257 ms, document as the fixture (L-C-number-or-indent) |
| R-table (record) | 3/3 recorded | 3/3 recorded | judge records | Backspace `EDITOR_BOUNDARY_UNSUPPORTED`, generation 2, document as the fixture |
| V6e (record) | see below | see below | `v6e/` | recorded, not judged |
| D6 | 未量 | 未量 | judge | `not runnable: item 2 not shipped (spec §12.3 (e))`; default 「未量，不做任何排序宣稱」 |

**V6e.** From «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60. Key order expects P2 «Bra econd paragraph».

| page | Chrome P2 (r1, r2, r3) | Firefox P2 (r1, r2, r3) |
|---|---|---|
| v21 `605cf24b…` | «Bra econd paragraph» ×3 | «Bra econd paragraph» ×3 |
| 0.2.24 (`dist/`, v20) | «Brasecond paragraph» ×3 | «Bra econd paragraph», «Brasecond paragraph», «Brasecond paragraph» |

- **v21:** no place-caret request before the move in any round. The request order was `delete-backward, delete-backward, save, move-character-right, delete-forward`. The arrows keep their checkpoint, by §12.3 (b).
- **0.2.24, the rounds that went wrong:** `delete-backward, editorPlaceCaretV2, delete-backward, delete-forward, save, move-character-right`. The second Backspace and the Delete ran at the click point, as finding 150 describes.
- **0.2.24, Firefox r1:** the key order held. Firefox's keydowns landed at 0/23/45–50/68–73 ms, against Chrome's 0/20/40/60.

### 5.2 Identity each report carried

| reports | page served | shell digest | profile (wasm, worker) | `identityOk` |
|---|---|---|---|---|
| item 1 v21, v21host, v21hook; D2 v21; M7 `main`; V6e v21 | `605cf24b3dff5a2d…` | `e35923a08107662d…` | `e2-editor-v21` (`db3408f5…`, `0d55bcfa…`) | true in every one |
| D5-w's v20 page (S-5) | `59553850…` (the tree source, already pinned to v20's wasm) | `e35923a0…` | `e2-editor-v20` (`313b08d5…`, `478d0da1…`) | true |
| 0.2.24 page (D8 red, D2 red, V6e) | `901dd6a6…` | `e7c4eefe…` (`dist/`) | `e2-editor-v20` (`313b08d5…`, `478d0da1…`) | true |

- **Tools.** Every report has `instrumentedWorker: false`. Browsers: Chrome 151.0.7922.169 (headless) and Firefox 157.0.1.
- **Runner hashes.** Item-1 runner `4fba3d19…` (all 12 reports), item-2 runner `fca737b2…`, D2 tool `1f2155fc…`.
- **The diag tool d14 imports.** It is bound as `diagSha256`: Chrome d14 has `75750e47…` (before fix J1), Firefox d14 and both V6e reports have `55867050…`. J1 changed only the `V21_PAGE_PREFIX` constant and its comment, not the functions d14 imports (`settle_long`, `timed_keys`, `move_tail`).

### 5.3 Product reds

None. No criterion FAILs, and the 0.2.24 red cases are red as required.

### 5.4 Runs repeated, and departures

1. **Chrome d1 was re-run (the rule for NE from foreign CPU).**
   - **First run** (`superseded/item1/report-chrome-d1-20261017T054335.json`): D7 read NE. Two arms' foreign-CPU samples were over the limit: sec-home-n2 r1 at 74.5 % and sec-end-n1 r3 at 75.6 %. Both came from the owner's desktop Chrome: an `--extension-process` renderer of that Chrome, which runs an extension relay page (`connect.html?mcpRelayUrl=…`). A new such renderer appeared every few minutes during the runs [observed: `ps` start times], and each one used about 75 % of a core for a moment.
   - **The re-run counts** (`item1/report-chrome-d1-20261017T064131.json`): 0 samples over the limit, and D1, D4 and D7 PASS.
   - **The first run's D1 was NE for another reason.** One start state (t-end-A1-n1 r3, table-mid) saw no selection within 10 s: `not-observed`, foreign CPU clean. D1 counts from the re-run only because D1, D4 and D7 share one arm and the judge takes one report per (browser, arm). That NE is recorded here as an observation (1/120 start states).
2. **Firefox D7 was not re-run.**
   - **What happened.** Foreign CPU was clean in every d1 round. The two reads outside 500±50 were posted by the page-side timer 550.1 ms and 553.5 ms after the reply, on t-end-B2-n1 r3 and t-home-B2-n2 r1. The reply caret equalled the read caret in both. Over all 192 Firefox reads, 15 were posted later than 520 ms: 11 on `t-*`, 3 on `tl-*`, 1 on `sec-*`. In Chrome all 192 were posted at 500.1–500.9 ms.
   - **Why no re-run.** The brief allows a re-run only for NE caused by foreign CPU. **Per §11.0, D7 Firefox is "not done", and its default is 「第 1 項不出貨」.** Whether a late-posted read in Firefox earns a re-run, or a change to the instrument, is the main session's call.
3. **Firefox's "rest" arms were re-run in three fresh sessions** (§34.4 witness W2). The run itself is described in §5.5. The re-run reports count: `report-firefox-d2p-d8-d8red-d11b-20261017T085102.json`, `report-firefox-d11a-d11c-d12-20261017T085811.json`, `report-firefox-d5w-xlc-table-d6-20261017T090001.json`.
4. **D8's 0.2.24 red case is sequence (d) only.** The runner's `d8red` is (d), as the brief says. Spec §11.1 names (c)(d)(e) on 0.2.24; (c) and (e) are covered by the node witness of `bc6534e0`, not re-run here.
5. **The item-2 judge prints missing criteria as FAIL.** M6 and M8–M11 read `FAIL (… missing)`, and M1–M5 read NE (zero instances or no report). None of them was run, by §12.3 (e), so neither verdict is a product result. The judge was not changed.

### 5.5 §34.4

| # | what | witness (committed before the change) | change |
|---|---|---|---|
| J1 | `diag_v21_dirty_move.py` refused V6e: its `V21_PAGE_PREFIX` was still the pre-fix pin `3d511216`. It builds from the tree, so the served page is `605cf24b…` (`identityOk: true`). | `witness/diag-v6e-stale-pin/` (`55331af1`) | `6aa8e184`: the pin only |
| W2 | One Firefox session lost d5w rounds 2–3, xlc and table. After 44 good loads across five origins (v21, dist0224, v21host, v21hook, v20), every init failed `WORKER_INIT_FAILED` (abort in `instantiateArrayBuffer`). This is the shape of finding 024 [inferred]. The same page loaded 120 times in its own Firefox session without a failure. | `witness/firefox-rest-worker-init-failed/` (`43ec5333`) | procedural, no tool edited: the arms were re-run in three fresh sessions (§5.4 item 3) |
| J2 | The item-1 judge's D5-w took the chord's first keydown. In Firefox that is the modifier's (`Control`/`Meta`, never prevented), so all 12 v21 chords read "not taken" (NE). | `witness/judge-d5w-modifier-keydown/` (`4bf78a3d`) | `c32fc13d`: the first keydown that is not a modifier's. Two Firefox-shaped self-test cases, red first: 83/85 on the old clause, 85/85 after. `test_v21_*.py` 94 OK. |
| J3 | D7 in Firefox read NE twice: the observer's `setTimeout(500)` posted 2/192, then 6/192, reads after +550 ms (max 560.3), all carets equal. An instrument miss, not a product one (fable ruling 2). | the first Firefox D1 report and `judge-item1.txt` (`a46b9267`); the re-run report and `judge-item1-after-d7-rerun.txt` (`fd2f854a`). The first report now lives in `superseded/item1/` | pending: one constant in `v21_item1_observer.py`, chosen by spec §12.4 (c) after A0 (`review/diag-d7-timer/`); runner and judge unchanged |

**Tally (this round):** modified because of execution **2** (J1, J2); modified because of review **0**; runs lost to the harness and re-run **1** (W2). The phase-B tally (2/0, smoke README) and ruling 1's (1/0) stand beside it.

**Tally after fable ruling 2 (appended 2026-10-17; the line above stands as written):** modified because of execution **3** (J1, J2, J3); modified because of review **0**; runs lost to the harness and re-run **1** (W2), plus one more if spec §12.4 (e) 3 (a foreign-CPU re-run) is spent.

### 5.6 Not covered here

- **D2 on the host** after the v74 freeze, and its 0.2.24 host red case: ddev is needed and the owner must be asked; both are refused in this phase.
- M11-autosave, I1, K.
- **Ruling 1's `open` cell** (Q4 condition 4) was not in this task and was not run.
- **The judgement this round leaves to the main session:** D7 in Firefox (§5.4 item 2).

### 5.7 D7 in Firefox: the re-run, fable ruling 2, and corrections (appended 2026-10-17)

**The re-run** (`fd2f854a`, 09:24–09:57, under the lock, desk load 0.18 at the start). `ARMS-item1.md` D7 says a missed window "reads NOT_ESTABLISHED and is re-run", so Firefox D1/D4/D7 was re-run. The first Firefox report and its docs moved to `superseded/item1/`; the re-judged output is `evidence/judge-item1-after-d7-rerun.txt`, beside the first `judge-item1.txt`.
- D1 and D4 PASS. D7 NOT_ESTABLISHED again: 6 of 192 +500 ms reads were posted at 554.7–560.3 ms, all on `t-*` fixtures, all "cursor" presses, all caret-equal.
- One more cell was voided by foreign CPU (sec-home-n1 r2: the owner's desktop Chrome extension renderer at 79 %). With Chrome's first D1 run (§5.4 item 1), the desktop Chrome has voided three D7 cells today.

**Ruling 2** (`review/ruling-fable-2.md`, `7a5cc0e9`; the request is `review/brief-fable-2-d7.md`, `269e1f9b`; the owner sent it to fable). The rules are pinned in spec §12.4, written before any browser run that follows:
- A0 first, a diagnostic and not evidence: sentinel timers at +440/+455/+470 and paint-reply stamps, on a copy of the observer, Firefox `t-*` arms, N=3.
- Then one constant in the observer, chosen by §12.4 (c): 470, 455, or none.
- Then exactly one Firefox D1 evidence re-run, judged by the unchanged judge; any read outside [450, 550] means item 1 does not ship in v21 (§12.4 (e)).
- Chrome's D7, and D10 and D11a in both browsers, stand on their constant-500 reports: every read there is inside the window (Chrome D7 500.1–500.9; D10 500.2–501.0; D11a 500.2–500.6).

**Corrections to the instrument's description** (ruling 2 Q5; they replace the sentences named, which stay where they are):
- **Our own main-thread work inside the window.** The brief said nothing of ours lies between the reply and the read. That holds for input, not for the main thread: while it waits for the ask, the runner drains the page every ~50 ms (`run_v21_shakedown_item1.py:373-377`; each drain is one to three script evaluations: the length, the whole JSON log, the cut), and the observer's `flush` (`JSON.stringify(log)`) runs as a 0 ms timer after every `put`. Chrome shows no lateness under the same polling, so this is not shown to be the cause; A0 keeps it by using the same runner.
- **The shape of the lateness** (both Firefox runs, 384 reads): a ceiling of 60.3 ms; bimodal (about +10–20 and +40–60); repeatable on the same cells (`t-home-B2-n1` ch1, `t-end-B2-n1` ce1, `t-home-B2-n3` ch1); the ask's round trip after a late post equals the on-time one (about 1 ms), so the stretch ends when the timer fires. The reports carry no page time that says when the stretch starts. "Most likely the repaint" is a hypothesis that A0's paint stamps test.
- **"Mostly an arm's first press"** holds for the tail beyond +550 (8/8 are `ch1`/`ce1`), not for lateness in general: reads later than +505 by press index are 12/114, 11/54, 4/24 (run 1) and 14/114, 10/54, 2/24 (run 2).
- **Where a changed constant shows.** The handoff 10-17 says Chrome's runner "differs only in the … timer constant". The runner's hash (`4fba3d19…`) does not change with the observer; `pages.v21.snippetSha256[1]` (today `52c08695…`) does.
- **Ask ids.** `ARMS-item1.md` §2.2 (c) says D7's ask ids are ≥ `0x7F000000`; the observer uses `0x7E000000` (`v21_item1_observer.py:48`). The judge matches on `k == "ask7"` and `forRq`, so no verdict depends on it.
- **The silent presses' readback times** quoted from spec §12.3 (250.6–251.2 ms) are the diagnostic's. In the D1 reports they are 250.5–251.5 ms (Chrome) and 250.9–254.0 ms (Firefox).

**Outcome (appended 2026-10-17 12:10): spec §12.4 (e) 1, D7 Firefox PASS.**
- **A0** (`review/diag-d7-timer/`, diagnostic): uninformative. 0 of 72 `t-*` +500 reads were late (500.1–501.5) with the desktop Chrome closed, so by §12.4 (c) the constant is 455, 「premise unmeasured, maximum slack chosen」 (`303e6296`, the one token).
- **The single Firefox D1 evidence re-run** (`item1/report-firefox-d1-20261017T113643.json`, 11:36–12:09):
  - under the lock; desktop Chrome closed (0 processes; `item1/desk-firefox-d1-rerun2-20261017T113643.txt`); load 0.80 at the start; foreign CPU over the limit in 0 of 120 rounds;
  - the previous Firefox D1 report (`092410`), its run log and docs moved to `superseded/item1/`, not deleted.
- **The unchanged judge** (at `c32fc13d`; `judge-item1-after-d7-rerun-2.txt`, beside the earlier two) reads **D7 Firefox PASS** and `VERDICT PASS (0 criterion cell(s) not PASS)`. Against `judge-item1-after-d7-rerun.txt`, D7 Firefox is the only verdict line that changed.
- **The edit took effect** (§12.4 (e) 5): all 192 reads lie in the window, at a median of 455.2 ms and a minimum of 455.1 ms.
- **Near an edge** (ruling 2 Q5 item 7): 179 of 192 reads lie within 10 ms of the lower edge (455.1–459.9 ms). That follows from the constant, because a timer never posts early (ruling 2 Q1, F5). None lies within 10 ms of the upper edge.
- **The lateness is still there, but there is less of it.** Six reads were 15 ms or more late:
  - t-end-B2-n3 ce1 +26.6;
  - r-cross-end ce +17.5 and +30.9;
  - t-end-A1-n3 ce3 +33.9;
  - sec-home-n3 ch3 +15.9;
  - t-home-A1-n2 ch2 **+50.4**. At the old constant, this read would have posted at 550.4 and read NE.
  
  The two earlier runs had 15 and 13 reads later than +20. This run alone cannot tell whether the closed desktop Chrome made the difference.
- **Carets** equal 192/192. Completions: as the judge reports, no FAIL.

**Which observer each judged report used** (ruling 2 Q2 condition 1; `pages.*.snippetSha256[1]`, the item-1 SNIPPET):

| report | item-1 snippet | D7 ask at |
|---|---|---|
| Chrome `d1-064131`, `d9`, `d10`, `d14`, rest (`d2p-…-d6`) | `52c08695…` | +500 |
| Firefox `d9`, `d10`, `d14`, `d2p-d8-d8red-d11b`, `d11a-d11c-d12`, `d5w-xlc-table-d6` | `52c08695…` | +500 |
| Firefox `d1-113643` | `9063835a…` | +455 |

D7's criterion is the window (500±50 ms, a single read), not the aim. Chrome D7, and D10 and D11a in both browsers, stand on their +500 reports without a re-run or re-judge (ruling 2 Q2). Their reads are all inside the window: Chrome D7 500.1–500.9 ms, D10 500.2–501.0 ms, D11a 500.2–500.6 ms.

**Tally** (unchanged from the line after ruling 2): execution **3** (J1, J2, J3), review **0**, runs lost and re-run **1** (W2). The §12.4 (e) 3 allowance was not spent.

### 5.8 D2's 0.2.24 red case on the host (appended 2026-10-17 15:31–15:37)

The owner said ddev was free for this session. The `litecore` ddev project was started (it was paused); nothing else of the owner's was touched. The host was **0.2.24** (`1479e56`, buildId `d3cd39bbc71ec311`, `hostDirty: []`), debug false.

- **Identity first** (`run_v21_d2.py --mode host --page 0224 --identity-only`): `problems: []`; page `901dd6a6…`, shell `e7c4eefe…` (12 paths, none missing), profile `e2-editor-v20`, wasm `313b08d5…`. As in `evidence/d2/host-identity/`.
- **Smoke, one round per browser** (`smoke/item1-d2-host/`). This arm had never run against the host. Both rounds completed on the first try; no tool was changed.
- **Evidence, N=3 per browser** (`evidence/d2/d2-host-0224-{chrome-20261017T153333,firefox-20261017T153501}.json`, with `run-host-*-0224.log`). Tool `ce169ef8…` (= `1fe9588d`), probe `4e92e920…`. Under the lock; pre-run refuse list empty; load 0.84 / 0.87. Chrome 151.0.7922.169 (headless), Firefox 157.0.1.

| | Chrome | Firefox |
|---|---|---|
| tool verdict (red mode) | red 3/3: `verified-selection-delete`, revision +1, no `move-document-*` | red 3/3, same |
| save 1 (real Ctrl+S, host save log) | `saved` 3/3 | `saved` 3/3 |
| server bytes changed / saved text equals opened | true / **false** 3/3 | true / **false** 3/3 |
| first paragraph on the server after save 1 | `LD-AGE-01` (opened: `LD-PAGE-01`) 3/3 | `LD-AGE-01` 3/3 |
| positive control (`Z`, save 2 > 1 s later) differs | true 3/3 | true 3/3 |
| folder MKCOL / DELETE | 201 / 204 | 201 / 204 |

**Reading.** On 0.2.24 the Ctrl+Home does not move the caret, so the Backspace deletes the character before the first-line click (the `P` of `LD-PAGE-01`), and the host saves that loss. This is the red the judge expects, measured through the shipped host, not inferred from the no-host case. The comparison is not blind: the control's save differs 6/6.

### 5.9 D2 on host 0.2.25: NOT_ESTABLISHED 6/6, a product defect (finding 154) (appended 2026-10-17 16:38–17:03)

Host 0.2.25 installed (`findings/evidence/host-0.2.25/README.md`; identity `problems: []`). `run_v21_d2.py --mode host --page v21 --rounds 3`, tool `ce169ef8…`, Chrome then Firefox (`evidence/d2/d2-host-v21-{chrome-20261017T163844,firefox-20261017T165106}.json`, `run-host-*-v21.log`).

- **Verdict 6/6 `NOT_ESTABLISHED` ("no Backspace response").** In every round the first-line click got no place-caret within 40 s (`clickState` null). After it, Ctrl+Home and Backspace were seen as keydowns and sent no request, and both saves timed out (no save was made, so `serverChanged` false). Folders 201 / 204.
- **Cause, measured** (`findings/evidence/154/`, diagnostic, both browsers): the closed `<dialog id="markdown-dialog">` that v21 part S added to `e2-editor.html` has computed `display: block` on the host. The rule is Nextcloud's `core/css/server.css` reset `article, aside, dialog, … { display: block }`, which overrides the user agent's `dialog:not([open]) { display: none }`. The dialog sits over the editor's top left, and the click point lands on `TEXTAREA#markdown-text`. With one added rule (`#markdown-dialog:not([open]) { display: none }`) on the same page, the point lands on `CANVAS#canvas` and the click sends `editorPlaceCaretV2`.
- **Why nothing earlier saw it:** every v21 evidence run was no-host, `v21host` included (a fake `liteCoreHost`, no Nextcloud page or CSS); E0 read the entry button, not the dialog.
- **By the pinned rule** D2 is not done, and its default is 「第 1 項不出貨」. ARMS-item1.md D2 (`:607`) foresaw that a red D2 means another host version (spec §1: 「新宿主版本（0.2.25 起）」). The fix and whether D2 re-runs on it are the owner's call; nothing is changed yet.

### 5.10 Finding 154 fixed in the host (0.2.26), and D2 re-run once (fable ruling 3; appended 2026-10-17, before the fix and before any browser)

Ruling: `review/ruling-fable-3.md` (the owner chose to send it to fable). Spec §12.5 holds the pinned text. This header is written first; results are appended below it.

**Pre-registered, in order:**
1. **The fix.** Host 0.2.26 = one rule `#litecore-editor-root dialog:not([open]) { display: none; }` in `templates/editor.php`'s own `<style>`, plus the version, in one host commit. `ddev occ upgrade` is run by the owner. Package untouched: `engine/MANIFEST.json` sha256 `54bebc4de343526bf44ad9b57472608942125b009ce16dee9787960c7b7a439b`, `check_engine_decoded.py` passes, `http_served_page.py` shows address `f5f0df762e1855f2-90d7bc2c` (filed under `findings/evidence/host-0.2.26/`). If the package hash differs: stop.
2. **The pin's red.** `--identity-only --page v21` on 0.2.26 with the tool unchanged → exactly one problem, `hostVersion`.
3. **Fix acceptance** (`findings/evidence/154/diag_markdown_dialog_on_host.py`, unchanged, sha `757c4476…`; red case = the committed 0.2.25 runs). Both browsers, `asShipped`: dialog open false / display none / box [0,0,0,0]; an inline rule `#litecore-editor-root dialog:not([open])` → none in `rulesSettingDisplay`; `CANVAS#canvas` at the point, `insideDialog` false; `editorPlaceCaretV2` sent and 「定位游標」; entry button hidden / none; `hostVersion` 0.2.26. Any read off → stop: no tool change, no D2.
4. **Re-pin.** The one value; `git diff 1fe9588d` shows one line; `--self-test` 19/19; identity v21 `[]`, 0224 refused on four fields. Committed before any D2 round.
5. **D2** (`--mode host --page v21`), Chrome N=3 then Firefox N=3, lock, desktop conditions of §12.4. Unchanged `judge_d2`. Prediction: a `move-document-start` response; Backspace `verified-boundary-noop`, `waitedMs` about 2,252–2,255, revision 0→0, saved text unchanged, control differs.
6. **Stop rule (§12.5 (e)).** 6/6 PASS → D2 PASS. Any FAIL → item 1 does not ship, no re-run, no 0.2.27. Any NE → item 1 does not ship, except (i) a crash with a `fatal` traceback or (ii) an external cause recorded in the report: that browser re-runs once.

**Not re-run:** the 0.2.24 red case (§5.8; the tool differs by the one line, and 0.2.24's HTML `b1185aaa…` has no `<dialog`). **§34.4:** 0 / 0. The `HOST_EXPECT` version is a binding (not counted); the diag tool is a diagnostic; the host rule is a product change.

**Results so far (appended 2026-10-17 18:10–18:20):**
- **The fix (pre-registered 1).** Host 0.2.26 = host commit `3c01876` (info.xml + the rule, one commit). `occ upgrade` was run by the session on the owner's typed command; `app:list` 0.2.26. Package untouched: `engine/MANIFEST.json` `54bebc4de343526b…`, `diff -rq` equal to the 0.2.25 archive, `check_engine_decoded.py` passes, HTTP address `f5f0df762e1855f2-90d7bc2c` with page / worker / wasm decoding as on 0.2.25 (`findings/evidence/host-0.2.26/`).
- **The pin's red (2).** `evidence/d2/host-identity/identity-v21-on-0226-before-repin.json`: exactly `hostVersion: the host packages 0.2.26, the run needs 0.2.25`.
- **Fix acceptance (3): met** (fable ruling 3, addendum 1; spec §12.5 (c′)). Reports `findings/evidence/154/0226/diag-154-{chrome-20261017T181633,firefox-20261017T181647}.json` (a subdirectory so the 0.2.25 screenshots are kept). In both browsers `asShipped` reads every pre-registered value: closed dialog display none, box 0; the inline rule `#litecore-editor-root dialog:not([open])` → none in the list; `CANVAS#canvas` at the point; `editorPlaceCaretV2` sent, state ready, 「定位游標 45 ms」 (Chrome) / 「28 ms」 (Firefox); entry button hidden; `hostVersion` 0.2.26.
  - `withRule`: Firefox the same; Chrome logged no `editorPlaceCaretV2` at its read. Both browsers read `busy` / pending 1 there. The clause "withRule must read the same" is **withdrawn** (premise false by construction, CLAUDE.md §4). The latency label is written only at completion (`e2-editor-app.js:2121`), the tool's `until` accepts the first click's stale label at once (`check_m3_production_ui.py:265-272`), and `placeCaret` posts `editorPlaceCaretV2` only after a `getState` round trip (`narrow-editor-v2-session.js:743`, `:772-778`). `withRule` is recorded, not judged. Named limit **L-154-diag-second-click**. D2's own click is clean by construction: it is the first click on a fresh page, where no 「定位游標」 label exists yet. A second click at the same point is not measured and not claimed by any v21 criterion.
  - §34.4: 0 / 0 (a witness exists, but the clause is withdrawn, not repaired; the tool is unchanged).

**D2 on host 0.2.26 (pre-registered 4–6; appended 2026-10-17 18:24–18:27): PASS 6/6. Stop rule §12.5 (e) 1.**
- **Re-pin (4)** (`090da6b6`): `git diff 1fe9588d -- wasm_sdk_probe/tools/run_v21_d2.py` is the one line `"hostVersion": "0.2.25"` → `"0.2.26"`. Tool `ce169ef8…` → `b4e24f0e…`. `--self-test` 19/19 (`evidence/d2/host-identity/self-test-after-repin-0226.txt`). Identity: v21 `[]`, 0224 refused on four fields (`identity-v21-on-0226-after-repin.json`, `identity-0224-refused-on-0226.json`).
- **Runs (5)**: `evidence/d2/d2-host-v21-{chrome-20261017T182415,firefox-20261017T182550}.json`, with `run-host-*-v21-0226.log`.
  - Desk: under the lock; `preRun.refuse` empty; load 0.19 / 1.00; KWallet `b false`. `chromeProcesses: 1` is marktext's `chrome_crashpad_handler` (`pgrep -c chrome` matches substrings); the desktop Chrome was closed (`pgrep -x chrome` 0). No foreign process over 50 % (the top entries are the sampler's own `ps` and our runner).
  - `static.hostVersion` 0.2.26, `hostDirty` []. Folders 201 / 204. Chrome 151.0.7922.169, Firefox 157.0.1.
- **Verdicts (unchanged `judge_d2`)**: Chrome PASS 3/3, Firefox PASS 3/3. Every round:
  - `move-document-start` completed `documented-callback-visible-cursor`;
  - Backspace `verified-boundary-noop`, `changed` false, revision 0 → 0;
  - save 1 and save 2 `saved`; `savedEqualsOpened` true (the server's first paragraph is still `LD-PAGE-01`); `controlDiffers` true.
- **Against the prediction**: as predicted, except `boundaryNoop.waitedMs`. It was 2,258–2,259 in Chrome (predicted about 2,252–2,255) and 2,253 in Firefox. No judge clause reads it.
- **HTML identity (ruling 3 Q3)**: `evidence/d2/html-source-equality-0226.txt` prints every v21 page entry of the 12 item-1 reports (15 entries: v21, v21host, v21hook) beside the installed package's `e2-editor.html`. All are `1d158149…` and all are equal. Command: `python3 -I` over `evidence/item1/report-*.json` and `engine/MANIFEST.json` (the script is at the top of the file's commit).
- **The 0.2.24 red case stands** (ruling 3 Q5): `evidence/d2/d2-host-0224-{chrome-20261017T153333,firefox-20261017T153501}.json`, tool `ce169ef8…`. Between that tool and today's, the only diff is the one `HOST_EXPECT["v21"]` line above.
- **§34.4 for this step: 0 / 0.** Not counted: the `HOST_EXPECT` re-pin (witnesses: the before/after identity outputs), the diag tool, the host rule. Registered, one line each, no code: L-154-diag-second-click; the D2 NE reason carries no payload about the click point; `HOST_EXPECT` pins no buildId.
- **D2: PASS in both browsers.** With §5.1–§5.7, every item-1 criterion is now PASS in both browsers.
- *Correction (appended):* the line above saying the script "is at the top of the file's commit" is wrong; the script was run inline. It is now saved as `evidence/d2/html_source_equality.py`, and its output is byte-equal to `html-source-equality-0226.txt`.
