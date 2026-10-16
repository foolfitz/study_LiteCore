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
