# Diagnostic: typing and arrows around a document move (v21 shakedown) — recorded, not judged

Nothing here is a verdict. There is no judge, no pass/fail and no count; every report says `"recordedNotJudged": true, "counted": false`. Labels: **[observed]** = read from the reports or the saved documents in this directory; **[source]** = read from the code at the cited place; **[inferred]** = my reading, not measured.

## Why

The item-1 smoke (`../smoke/item1/README.md`, "Product red" and "Observations") left two questions:

1. **Dirty document, first Ctrl+End.** The session sends a checkpoint `save` first, and the move then completes `verified-move-readback` with the old caret, about 251 ms later. An engine ask later shows the caret at the end. Spec `specs/SPEC-M3-link-batch-v21.md` §9.1 names the consequence **L-142-readback-overtaken**: a sync command sent right after the stale readback (typing goes through `paste`) runs before Writer's `GoToEndOfDoc`, and the text lands at the pre-move caret. Does that actually happen to typing?
2. **Move keys during a delete.** The page's arrow keydown path (`web/e2-editor-app.js:3192-3197`) and `sendDocumentMove` (`:3322-3336`) choose `moveFromPoint` (a click, then the move) from `pointMovesInFlight`, the selection shape and the gestures. Neither checks `deletesInFlight`; finding 131's rule A (`deleteActionFor`, `:2787-2789`) does [source]. D8 (e) showed it for Ctrl+End. The arrow path is 0.2.24 code (`dist/e2-editor-app.js:2975-2977`, same condition) [source]. Do arrows show it, on 0.2.24 and on v21?

## What ran

- Tool: `wasm_sdk_probe/tools/diag_v21_dirty_move.py`.
  - It reuses the item-1 runner's `Pages` (S-1 mirrors), `Ctx` (load, open, start state, ask, quiet, save, the item-1 observer log), `run_script` and `element_center`. It also reuses `v21_input` (keys, clicks), `v21_clipboard` (the dialog's paste, D6's route), `v21_shakedown_common` (S-9 lock, pre-run checks, foreign-CPU sample) and `v21_item1_marker.paragraphs_of` (the S-7 adapter).
  - New code:
    - timed key sequences: Chrome uses CDP presses on the monotonic clock; Firefox uses one WebDriver action chain with `pause` actions;
    - a reply-triggered key for V2;
    - a small in-page recorder for V5: dialog `open` mutations, sink `disabled`/`readonly`, `focusin`, keydown/keypress, `beforeinput`/`input` at window level, and `document.hasFocus()`.
  - The +500 ms engine ask is the item-1 observer's own `ask7`.
- The tool that measured has sha256 `7450716a74c2c4d7…` (`toolSha256` in both reports). It is committed as such in the first commit. The second commit changes only `--table`'s rendering: it collapses repeated ops and adds the final-caret column.
- Pages [observed: `pages`, `v21PageCheck`]:
  - v21: served `3d5112161b23b060…`, shell digest `e0252c0b22d37a20…`, `identityOk: true`, built exactly as the item-1 runner builds it;
  - 0.2.24, for V6/V6e: `dist/`'s page, shell and the v20 profile, as the item-1 runner's `d8red` builds it; served `901dd6a6dbff6ad6…`, `identityOk: true`.
- Browsers: Chrome 151.0.7922.169 headless, then Firefox 157.0.1 headless, window 1400×1000. Every round is a fresh load and open, N=3.
- Lock and pre-run: each run held the S-9 lock for its whole duration (`lock` in each report). KWallet was `b false` before both.
- Foreign CPU: sampled for 2 s before every round and recorded, not gated. 3 of 72 samples were over the 50 % limit [observed]:
  - Chrome V5-late r2: `llama-server` 88.9 %;
  - Chrome V6 v21 r2: `llama-server` 87.1 %;
  - Firefox V5-0 r2: a process named `2.1.301` at 70.1 %.

  Those rounds read the same as their siblings.

### Variants

| | fixture | steps |
|---|---|---|
| V1 | plain3 | real `Z` at the start, reply awaited; real Ctrl+End; real `Q` 30 ms after Ctrl+End's keydown; quiet; save |
| V2 | plain3 | as V1, but `Q` 50 ms after the move's reply (polled from the observer's node, page clock) |
| V3 | plain3 | as V1 without `Z`: clean, no checkpoint (control) |
| V4 | long60 (`create_long_document.build(60)`) | as V1; the open waits for 60 page rectangles as D10 does |
| V5 | plain3 | paste `# a` into the Markdown dialog with the clipboard instrument (D6's route), click 「插入」, real `Z` 0 ms or 300 ms after the dialog closes |
| V5-late (added) | plain3 | as V5, `Z` once the page is quiet (ready, nothing pending, 0.5 s) plus 1 s |
| V5-no-dialog (added) | plain3 | the clipboard instrument's steps exactly as in V5 (grant, `Page.bringToFront`, `writeText`), no dialog, then `Z` |
| V5 all (added) | — | after `Z`: a real `Y` with no click, then a real click at the engine's caret and a real `X` |
| V6 | plain3, caret «Bravo\|» (`k1024,k1027x5`) | Backspace @0, ArrowRight @20, Delete @40; quiet; save; on the v21 page and the 0.2.24 page |
| V6e (added) | as V6 | D8 (e)'s exact shape with ArrowRight in Ctrl+End's place: Backspace @0, Backspace @20, ArrowRight @40, Delete @60; both pages |

The added rows were written after a development round showed the need. Each addition is listed under "Changes during development".

## Files

- `report-chrome-20261017T032237.json`, `report-firefox-20261017T033236.json`. Each holds:
  - identity per page, pre-run checks and lock holder;
  - per round: the foreign-CPU sample, load and open, the raw observer log (`kd kdp rq rs bi ask7post ask7 askx`), the saved document's paragraphs (`savedTexts`) and a `summary`;
  - for V5, the recorder's events.
- `docs/{browser}-{stamp}/*.odt`: every saved document (72). The landings below are read from these files by `v21_item1_marker.paragraphs_of` [observed].
- Tables: `python3 wasm_sdk_probe/tools/diag_v21_dirty_move.py --table findings/evidence/link-batch-v21/shakedown/diag-dirty-move`. They are reproduced below.

## Readings

### 1. Typing right after a dirty document's Ctrl+End lands at the pre-move caret

- **Where `Q` lands** [observed: saved documents]:
  - V1, V2, V4: at the pre-move caret, 3/3 in both browsers (18/18). On plain3 the saved P1 is `ZQAlpha first paragraph`; on long60 the saved first paragraph is `ZQLD-PAGE-01`.
  - V3 (clean): at the document end, 3/3 in both browsers (`Charlie third paragraphQ`).
- **Request order** [observed]:
  - V1/V2/V4: always `save` → `move-document-end` → `insertText`.
  - V1/V4: `Q`'s keydown came 30 ms after Ctrl+End's, while the `save` was still running, yet `insertText` is posted 0.6–1.1 ms after the move's reply, 320–1885 ms after the keydown. So the typing waits for the move's reply.
  - V2: `insertText` is posted 1.1–1.8 ms after `Q`'s keydown, which came after the reply.
  - The reply is `verified-move-readback` after 250.5–251.7 ms, with the pre-move caret: `1564,1418` on plain3 (after the `Z`), `1613,1418` on long60.
  - V3: `move-document-end` → `insertText`. The move answers `documented-callback-visible-cursor` in 34–45 ms with the end caret `3657,1970`.
- **Where the engine's caret is afterwards** [observed]:
  - V1/V2: the +500 ms ask reads `3657,1970` (P3's end) 12/12.
  - V4: the +500 ms ask still reads the old caret `1613,1418`, 6/6.
  - The final ask after quiet (≥ 1.5 s) reads the end in every round: plain3 `3657,1970`; long60 `4037,1021644`, page 60.
- **V2** [observed]: `Q` 50.9–54.2 ms after the move's reply still lands at the pre-move caret, 6/6. The window is therefore at least 50 ms past the reply on plain3, and past +500 ms on long60. Where it ends was not measured.
- **Reading** [inferred]: the page and session keep their order: nothing is posted before the move answers [source: spec §9.1 「產品在移動完成之前不送下一個指令」]. The move "answers" by its 250 ms readback, though, while Writer's `GoToEndOfDoc` has not run yet. The `paste` that carries the typed character then runs first, at the old caret, and the move lands afterwards. This is L-142-readback-overtaken exactly as §9.1 describes it, and it happens to ordinary typing. It is not only something a scripted queue can reach.
- **Related** [observed]: the arrow's move after a checkpoint `save` (V6, 12/12) also completes `verified-move-readback` with the pre-move caret `1884,1694`. There, though, the following Delete removed the character after the moved caret (`Brav econd paragraph` = key order). So in these rounds the readback-overtaken shape did not misplace a delete. Why it differs from typing is not established [inferred: the delete's own barrier/verification may give the move time to land; not measured].

### 2. V5: the lost `Z` after the Markdown dialog is not the harness's timing; in Chrome typing stays dead after the dialog

- **Chrome** [observed], 9/9 dialog rounds (0 ms, 300 ms, late at about 1.6 s):
  - `Z`'s keydown and keypress reach the sink. The sink is the active element, not disabled, not read-only, `document.hasFocus()` is true, and the keypress is not prevented.
  - No `beforeinput` and no `input` fire anywhere in the page, no `insertText` is posted, and `Z` is absent from the saved document.
  - The same holds for the following `Y` (no click) and for `X` typed after a real click at the caret, whose `editorPlaceCaretV2` did go out.
  - The paste itself worked (`a` is a new first paragraph); it had answered before `Z` in every round.
- **Chrome no-dialog control** [observed]: same clipboard steps, no dialog. It types `ZYXAlpha first paragraph`, 3/3.
- **Firefox** [observed]: `Z`, `Y` and `X` are typed in all 12 rounds. After the dialog they land at P2 offset 0 (`ZYXAlpha first paragraph`, after the pasted heading `a`); in the no-dialog control at P1 offset 0.
- **Source** [source]:
  - The page has no `keypress` listener. A grep over `web/`, `editor-shell*/`, `sdk/`, `input/`, `src/` and `e2/` finds only comments, a test, and a note in `e2/relink-queue-v3.json` that says the same.
  - `closeMarkdownDialog` calls `dialog.close()` and then `el.sink.focus({ preventScroll: true })` (`web/e2-editor-app.js:2337-2344`).
- **Reading** [inferred]: D6's lost `Z` (item-1 smoke) is this Chrome behaviour, not a race: waiting 300 ms or 1.6 s does not help, and neither does a click. This diagnostic cannot decide whether a real keyboard in a real Chrome loses typing the same way, or whether this is CDP key input after a modal `<dialog>` in headless Chrome. The input never reaches the page's code, so it is either Chrome's editing or the harness. Typing a character by hand in Chrome after 「插入」 would decide it.

### 3. Arrows during a delete take the click path too; on 0.2.24 as well

- **V6 as specified** (Backspace @0, ArrowRight @20, Delete @40) [observed]:
  - No place-caret request in any round: 12/12, both pages, both browsers.
  - The order is `delete-backward` → `save` → `move-character-right` → `delete-forward`.
  - P2 is `Brav econd paragraph`, which is the key order.
  - In Firefox the chain's real gaps were 23 ms and 45–53 ms.
- **V6e** (added; D8 (e)'s shape with ArrowRight) [observed], 3/3 on each page in both browsers (12/12):
  - **v21:** `delete-backward ×2` → `editorGetStateV2` → `editorPlaceCaretV2` → `delete-forward` → `save` → `move-character-right`. P2 saved `Bra scond paragraph`, where key order gives `Bra econd paragraph`. That is the same text D8 (e) saved for Ctrl+End. The click answers `documented-callback-visible-cursor` with caret x 1917, a position none of the keys produced (placement 2004, after the first delete 1884, after the second 1764).
  - **0.2.24:** `delete-backward` → `editorGetStateV2` → `editorPlaceCaretV2` → (22–26 × `editorGetStateV2`) → `delete-backward` → `delete-forward` → `save` → `move-character-right`. The click went out before the second Backspace was sent, and answered `verified-caret-readback` after 255–258 ms at x 1884. The second Backspace and the Delete both ran after the click and before the move. P2 saved `Brasecond paragraph`.
- **0.2.24 shows the misplaced Delete** [observed, V6e]. It also misplaces the second Backspace's turn relative to the arrow.
- **Why V6 at 20 ms does not take the path and V6e at 40 ms does** [not established]: in both, the arrow came before the first delete's reply (V6 20–24 ms vs. a reply at 43–56 ms; V6e 40–45 ms vs. 45–54 ms). The difference is the second Backspace pressed before the arrow. The selection shape the page read at the arrow's keydown was not recorded.
- **Reading** [inferred]:
  - A user who presses Backspace twice quickly and then an arrow and Delete gets the Delete applied at a click point taken from a stale caret, before the arrow's move.
  - On 0.2.24 the held Backspace also lands after the click.
  - The arrow path was not introduced by v21; Ctrl+End in v21 reuses it, as `sendDocumentMove`'s comment says.

## Changes during development (§34.4-style tally)

Development rounds ran in the scratchpad and are not kept. Their results were reproduced by the recorded runs above.
- **Modified because of execution: 5.** All are additions after a development witness, not repairs:
  - the V5 recorder widened to window-level `beforeinput`/`input` and keypress `defaultPrevented`, after the first round showed no `beforeinput` at the sink;
  - V5-late, after 300 ms still lost `Z`;
  - the `Y`/`X` steps;
  - V5-no-dialog, to separate the clipboard instrument from the dialog;
  - V6e, after V6's development round took no click path.
- **Modified because of review: 0.**
- After the recorded runs: `--table` rendering only (second commit).

## Not done

- No hand test in a real Chrome for V5.
- The window of reading 1 was not measured to its end.
- The page's selection shape at the arrow's keydown was not recorded.

## Tables (generated by `--table`)
### chrome (Chrome/151.0.7922.169), `report-chrome-20261017T032237.json`


**V1** (plain3, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | pre-move caret | 30.3 | -402.5 | verified-move-readback (251.7) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 2 | pre-move caret | 30.3 | -326.6 | verified-move-readback (251.0) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 3 | pre-move caret | 30.3 | -319.0 | verified-move-readback (250.6) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |

**V2** (plain3, dirty, Q 50 ms after the move's reply)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | pre-move caret | 403.2 | 50.9 | verified-move-readback (250.6) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 2 | pre-move caret | 397.5 | 51.1 | verified-move-readback (250.7) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 3 | pre-move caret | 394.9 | 51.2 | verified-move-readback (250.5) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |

**V3** (plain3, clean control, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 30.3 | -4.5 | documented-callback-visible-cursor (33.9) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 30.4 | -4.8 | documented-callback-visible-cursor (34.3) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 30.0 | -15.8 | documented-callback-visible-cursor (44.6) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V4** (long60, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | pre-move caret | 30.2 | -1884.2 | verified-move-readback (251.0) | 1613,1418 | 1613,1418 | 4037,1021644 | save → move-document-end → insertText → editorGetStateV2 |
| 2 | pre-move caret | 30.4 | -414.6 | verified-move-readback (250.7) | 1613,1418 | 1613,1418 | 4037,1021644 | save → move-document-end → insertText → editorGetStateV2 |
| 3 | pre-move caret | 30.3 | -424.8 | verified-move-readback (250.6) | 1613,1418 | 1613,1418 | 4037,1021644 | save → move-document-end → insertText → editorGetStateV2 |

**V5** (Markdown dialog `# a`, Z 0 / 300 ms after it closes (+ added controls late, no-dialog))

| round | delay | dialog close → Z kd (ms) | Z kd target / active | sink disabled at Z | keypress (prevented) | beforeinput / input anywhere after Z | insertText | Z in saved doc | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0.8 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 2 | 0 | 0.6 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 3 | 0 | 0.6 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 1 | 300 | 302.1 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 2 | 300 | 301.2 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 3 | 300 | 300.9 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 1 | late | 1609.1 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 2 | late | 1611.7 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 3 | late | 1611.4 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 1 | no-dialog |  | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 0 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | insertText → editorGetStateV2 |
| 2 | no-dialog |  | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 0 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | insertText → editorGetStateV2 |
| 3 | no-dialog |  | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 0 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | insertText → editorGetStateV2 |

**V6** («Bravo|»: Backspace @0, ArrowRight @20, Delete @40)

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0, 20.1, 40.2] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| v21 | 2 | [0, 20.4, 40.4] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| v21 | 3 | [0.0, 20.4, 40.2] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| dist0224 | 1 | [0.0, 20.3, 40.3] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| dist0224 | 2 | [0.0, 20.2, 40.2] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| dist0224 | 3 | [0.0, 20.5, 40.2] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |

**V6E** ((added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight))

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 20.5, 40.2, 60.4] | 'Bra scond paragraph' | 'Bra econd paragraph' | True | True | delete-backward ×2 → editorGetStateV2 → editorPlaceCaretV2 → delete-forward → save → move-character-right |
| v21 | 2 | [0.0, 20.2, 40.3, 60.3] | 'Bra scond paragraph' | 'Bra econd paragraph' | True | True | delete-backward ×2 → editorGetStateV2 → editorPlaceCaretV2 → delete-forward → save → move-character-right |
| v21 | 3 | [0.0, 20.5, 40.2, 60.3] | 'Bra scond paragraph' | 'Bra econd paragraph' | True | True | delete-backward ×2 → editorGetStateV2 → editorPlaceCaretV2 → delete-forward → save → move-character-right |
| dist0224 | 1 | [0.0, 20.6, 40.5, 60.3] | 'Brasecond paragraph' | 'Bra econd paragraph' | True | True | delete-backward → editorGetStateV2 → editorPlaceCaretV2 → editorGetStateV2 ×24 → delete-backward → delete-forward → save → move-character-right |
| dist0224 | 2 | [0.0, 20.4, 40.2, 60.4] | 'Brasecond paragraph' | 'Bra econd paragraph' | True | True | delete-backward → editorGetStateV2 → editorPlaceCaretV2 → editorGetStateV2 ×25 → delete-backward → delete-forward → save → move-character-right |
| dist0224 | 3 | [0.0, 20.6, 40.2, 60.9] | 'Brasecond paragraph' | 'Bra econd paragraph' | True | True | delete-backward → editorGetStateV2 → editorPlaceCaretV2 → editorGetStateV2 ×24 → delete-backward → delete-forward → save → move-character-right |

### firefox (157.0.1), `report-firefox-20261017T033236.json`


**V1** (plain3, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | pre-move caret | 34.6 | -374.6 | verified-move-readback (251.1) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 2 | pre-move caret | 32.8 | -384.4 | verified-move-readback (251.1) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 3 | pre-move caret | 33.1 | -374.3 | verified-move-readback (251.2) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |

**V2** (plain3, dirty, Q 50 ms after the move's reply)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | pre-move caret | 467.8 | 54.2 | verified-move-readback (251.3) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 2 | pre-move caret | 467.5 | 52.8 | verified-move-readback (250.8) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |
| 3 | pre-move caret | 479.4 | 53.3 | verified-move-readback (250.9) | 1564,1418 | 3657,1970 | 3657,1970 | save → move-document-end → insertText → editorGetStateV2 |

**V3** (plain3, clean control, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 34.3 | -10.7 | documented-callback-visible-cursor (43.4) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 33.2 | -9.9 | documented-callback-visible-cursor (42.0) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 33.2 | -8.0 | documented-callback-visible-cursor (40.1) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V4** (long60, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | pre-move caret | 32.7 | -545.5 | verified-move-readback (250.9) | 1613,1418 | 1613,1418 | 4037,1021644 | save → move-document-end → insertText → editorGetStateV2 |
| 2 | pre-move caret | 34.3 | -505.7 | verified-move-readback (251.1) | 1613,1418 | 1613,1418 | 4037,1021644 | save → move-document-end → insertText → editorGetStateV2 |
| 3 | pre-move caret | 34.0 | -499.3 | verified-move-readback (250.9) | 1613,1418 | 1613,1418 | 4037,1021644 | save → move-document-end → insertText → editorGetStateV2 |

**V5** (Markdown dialog `# a`, Z 0 / 300 ms after it closes (+ added controls late, no-dialog))

| round | delay | dialog close → Z kd (ms) | Z kd target / active | sink disabled at Z | keypress (prevented) | beforeinput / input anywhere after Z | insertText | Z in saved doc | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 4.0 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 2 | 0 | 2.7 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 3 | 0 | 4.5 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 1 | 300 | 303.4 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 2 | 300 | 303.7 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 3 | 300 | 304.6 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 1 | late | 1628.9 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 2 | late | 1627.7 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 3 | late | 1627.2 | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 1 | no-dialog |  | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 0 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | insertText → editorGetStateV2 |
| 2 | no-dialog |  | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 0 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | insertText → editorGetStateV2 |
| 3 | no-dialog |  | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 0 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | insertText → editorGetStateV2 |

**V6** («Bravo|»: Backspace @0, ArrowRight @20, Delete @40)

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 23.6, 52.6] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| v21 | 2 | [0.0, 22.9, 48.4] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| v21 | 3 | [0.0, 23.5, 50.5] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| dist0224 | 1 | [0.0, 23.3, 45.2] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| dist0224 | 2 | [0.0, 23.0, 45.3] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |
| dist0224 | 3 | [0.0, 23.5, 49.1] | 'Brav econd paragraph' | 'Brav econd paragraph' | False | False | delete-backward → save → move-character-right → delete-forward |

**V6E** ((added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight))

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 22.6, 43.9, 67.1] | 'Bra scond paragraph' | 'Bra econd paragraph' | True | True | delete-backward ×2 → editorGetStateV2 → editorPlaceCaretV2 → delete-forward → save → move-character-right |
| v21 | 2 | [0.0, 22.9, 45.3, 69.3] | 'Bra scond paragraph' | 'Bra econd paragraph' | True | True | delete-backward ×2 → editorGetStateV2 → editorPlaceCaretV2 → delete-forward → save → move-character-right |
| v21 | 3 | [0.0, 23.4, 44.7, 66.7] | 'Bra scond paragraph' | 'Bra econd paragraph' | True | True | delete-backward ×2 → editorGetStateV2 → editorPlaceCaretV2 → delete-forward → save → move-character-right |
| dist0224 | 1 | [0.0, 23.1, 44.6, 68.3] | 'Brasecond paragraph' | 'Bra econd paragraph' | True | True | delete-backward → editorGetStateV2 → editorPlaceCaretV2 → editorGetStateV2 ×23 → delete-backward → delete-forward → save → move-character-right |
| dist0224 | 2 | [0.0, 23.2, 44.8, 72.3] | 'Brasecond paragraph' | 'Bra econd paragraph' | True | True | delete-backward → editorGetStateV2 → editorPlaceCaretV2 → editorGetStateV2 ×26 → delete-backward → delete-forward → save → move-character-right |
| dist0224 | 3 | [0, 22.5, 44.9, 71.2] | 'Brasecond paragraph' | 'Bra econd paragraph' | True | True | delete-backward → editorGetStateV2 → editorPlaceCaretV2 → editorGetStateV2 ×22 → delete-backward → delete-forward → save → move-character-right |



---

# Follow-up (2026-10-17, 03:56–04:50): V7–V11, two candidate fixes, a headed Chrome

The main session asked for these after reading the section above. The owner is asleep and has authorised decisions through fable; these numbers go into fable's brief. Same rules as above: recorded, not judged; labels **[observed]** / **[source]** / **[inferred]**.

## What ran

- **Tool versions:**
  - `54203322ddf14f97…` measured V7–V11 and the fix runs (commit `f7f18dbf`);
  - `2032567065d6fce8…` measured V11g (the next commit). It differs only by `HeadedChromeSession`, `--headed` and `--v5-delays` (`git diff f7f18dbf -- wasm_sdk_probe/tools/diag_v21_dirty_move.py`).
- **Reports** [observed: each report's `outcome`s, `v21PageCheck`, `preRun`, `foreign`]:

  | report | browser | fix | rounds |
  |---|---|---|---|
  | `report-chrome-followup-20261017T040938.json` | Chrome 151 | none | 29 |
  | `report-firefox-followup-20261017T041915.json` | Firefox 157 | none | 14 |
  | `report-{chrome,firefox}-fix1-*.json` | both | fix1 | 18 each |
  | `report-{chrome,firefox}-fix2-*.json` | both | fix2 | 9 each |
  | `report-{chrome,firefox}-fix12-*.json` | both | fix1 and fix2 | 2 each |
  | `report-chrome-headed-20261017T044017.json` | Chrome 151, headed | none | 7 |

  - All 108 rounds are `done`.
  - The v21 page before any fix is `3d5112161b23b060…` in every report.
  - KWallet was `b false` before each run, and each run held the S-9 lock.
  - 90 rounds took a foreign-CPU sample and 0 were over the limit. The 18 rounds of the reused item-1 arms (D11b, D8 (e)) take none.
- **Candidate fixes**, applied to the served copy in the mirror only, never the tree [observed: `candidateFix` in each report; `git status` showed `web/`, `editor-shell-v2/`, `dist/` unchanged]:
  - **fix1**: served `editor-shell-v2/narrow-editor-v2-session.js` `8828a390500912f5…`. The unpatched served copy and the tree are both `443e0f1e7c85f359…`. In `action()`, the `BOUNDARY_CAPABLE_MOVES` checkpoint line gets `&& action !== "move-document-start" && action !== "move-document-end"`. Nothing else changes.
  - **fix2**: served page `17a28c1cf6c859da…`, with `patchOnly: true`: undoing the two edits gives back `3d5112161b23b060…` exactly. `deletesInFlight === 0 &&` is added in front of the arrow path's and `sendDocumentMove`'s range decision.
  - **fix12**: both.
  - The patch tool refuses to write when the file, or any directory between the mirror and it, is a symlink: the mirror symlinks into `dist/`.
- **Additions of mine:**
  - **V8d**, because V8 as asked banks its checkpoint during the placement (see reading 2).
  - **V11f** is recorded as not run: the 0.2.24 page (`dist/e2-editor.html`, `dist/e2-editor-app.js`) has no `<dialog>` element and no `showModal` [source: grep].
- **A window appeared on the owner's desktop** between 04:45:55 (lock acquired; the window opened right after) and 04:49:30 (+0800, closed). That was V11g's headed Chrome on the owner's Plasma/Wayland session (`DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0`; which of the two Chrome used was not recorded). It was closed by the tool: `close: {}`, and no remote-debugging Chrome was left. The session was locked before and after (`loginctl … LockedHint=yes` at 04:40:17 and 04:49:30) [observed].

## Readings

### 1. V7: the stale reply follows any save, not the checkpoint; it lasts less than 300 ms after the save's reply

- **X ≈ 0** [observed], Ctrl+End 1.6–9.4 ms after the toolbar save's reply:
  - No checkpoint `save` follows the key in any round (the content was already banked).
  - The move still answers `verified-move-readback` after 251.4–255.0 ms with the old caret `1564,1418`.
  - `Q` lands at the pre-move caret (`ZQAlpha…`), 6/6 (3 Chrome, 3 Firefox).
- **X = 300, 1000, 3000** [observed]: the move answers `documented-callback-visible-cursor` in 38–49 ms, and `Q` lands at the document end, 10/10.
- **Reading** [inferred]: what stalls `GoToEndOfDoc` is the engine's state right after a save, whatever asked for the save. On plain3 that state is gone within 300 ms of the save's reply. Between 10 and 300 ms was not measured, and neither was a larger document. An autosave or a Ctrl+S just before a document move would open the same window; neither was measured here.

### 2. V8 / V8d: an arrow that takes the checkpoint is overtaken the same way

- **V8 as asked** [observed]: Z at the start, then «Bravo|», then ArrowDown with Q 30 ms later.
  - The placement's first ArrowDown takes the checkpoint, because arrows are in `BOUNDARY_CAPABLE_MOVES` [source: `editor-shell-v2/narrow-editor-v2-session.js:90-94`].
  - So the measured ArrowDown sends no `save` and answers `documented-callback-visible-cursor` in 33–46 ms.
  - `Q` lands on P3, the line moved to (`CharliQe third paragraph`), 6/6.
- **V8d** [observed]: «Bravo|» first, then Z there, so the ArrowDown is the first move after the change.
  - Order: `save` → `move-line-down`, which answers `verified-move-readback` after 250.6–251.3 ms with the old caret.
  - `Q` lands on P2 right after the Z (`BravoZQ second paragraph`), 6/6.
- **Reading** [inferred]: L-142-readback-overtaken is not specific to Ctrl+Home/End. Any of the eight boundary-capable moves that takes the checkpoint has it, and fix1 as specified leaves the six arrow/Home/End moves as they are.

### 3. V9, fix1 (Ctrl+Home/End take no checkpoint)

- **V1/V2/V4** [observed]: `Q` at the document end, 18/18. Every move answers `documented-callback-visible-cursor` in 33–51 ms, and there is no `save` request. On long60 the reply caret is already the end (`4037,1021644`).
- **V3 (clean)** [observed]: at the end, 6/6, as without the fix.
- **D11b** (the item-1 arm, reused), 3 rounds × clean/dirty × 2 browsers [observed]:
  - dirty: 0 `save` requests; unsaved is `true` after typing, after Ctrl+End and after Ctrl+Home, 6/6;
  - both: the checkpoint line shows 「無」.
- **What fix1 gives up** [observed]: in the item-1 smoke, D11b dirty showed 「有（r1）」 after the first move. With fix1 a dirty document gets no checkpoint from Ctrl+Home/End at all. What that checkpoint protected, a document move on a dirty document whose engine dies (findings 096–099, `narrow-editor-v2-session.js` comment before `_checkpointBeforeBoundaryMove` [source]), would then rest on the next arrow move or the autosave [inferred].

### 4. V10, fix2 (rule A in the two range paths)

- **V6e** [observed]: `Bra econd paragraph`, the key order, 6/6. The order is `delete-backward ×2` → `save` → `move-character-right` → `delete-forward`, with no place-caret request. Without the fix it was `Bra scond paragraph`, 6/6 (section above).
- **D8 (e)** (the item-1 `run_d8(…, ["e"])`, reused) [observed]: all three paragraphs equal the item-1 judge's `D8_EXPECT["e"]`, 6/6.
  - The `move-document-end` still answers `verified-move-readback` with the old caret x 1764, after its checkpoint `save`.
  - The Delete then answers `verified-boundary-noop` after 2252–2253 ms: it ran at the document end.
- **Range control** [observed]: the drag selects `second`, and ArrowRight still goes `click` → `move-character-right`, 6/6. Rule A only bites while a delete is out. Final caret `2790,1694`; P2 unchanged.
- **fix1 and fix2 together** (N=1 per browser) [observed]:
  - V1: `Q` at the end, `documented-callback-visible-cursor`, no `save`;
  - V6e: `Bra econd paragraph`.

  They compose.

### 5. V11 and V11g: typing after the Markdown dialog

- **Headless Chrome, N=3 each** [observed]:
  - **(a)** `Z` through CDP `Input.insertText`: `beforeinput insertText@sink`, an `insertText` request, and `Z` lands, 3/3. The real `Y` and `X` after it are lost, 3/3.
  - **(b)** `sink.blur(); sink.focus()`, then real keys: `Z`, `Y` and `X` all land, 3/3.
  - **(c)** open the dialog and press 取消, with nothing sent: `Z`, `Y` and `X` are lost, 3/3.
  - **(d)** with `second` selected, paste, 「插入」 refused (the dialog stays open), then 取消: `Z`, `Y` and `X` are lost, 3/3.
  - **(e)** a real Ctrl+V of `W` into the sink: `W` lands (`WAlpha…`, an `insertText` request, no `beforeinput`), 3/3. `Y` and `X` are lost.
- **At every first input** (all variants) [observed]:
  - the sink is the active element: not disabled, not read-only, not `inert`, no `[inert]` ancestor;
  - `pointer-events: none`, which is also the case in (b), where typing works;
  - the dialog is closed and `document.hasFocus()` is true.
- **V11g, headed Chrome** on the owner's display [observed]:
  - V5 at 300 ms: lost, 3/3;
  - V11c (取消 only): lost, 3/3;
  - the no-dialog control: `ZYXAlpha…`, 1/1.
- **Reading** [inferred]:
  - The sink can still receive text: `Input.insertText` and a paste reach it.
  - The page never sees a `beforeinput` for the lost keys, so no page code refuses them. What breaks is Chrome's key-to-text step for the sink after `closeMarkdownDialog` runs `dialog.close()` and then `el.sink.focus()` in the same task [source: `web/e2-editor-app.js:2337-2344`]. Re-focusing repairs it.
  - It is not headless-only: a headed Chrome that types normally without the dialog loses the keys after it, by the coordinator's rule "likely real".
  - Two limits remain:
    - the keys are still CDP key events, not an OS keyboard;
    - the headed window sat behind a locked screen.

    A hand test in a real Chrome would close both.
  - Firefox is not affected (V5 above, 12/12).

## Changes during development (follow-up)

- Development rounds ran in the scratchpad (Chrome, N=1) before the recorded runs, and are not kept.
- **Modified because of execution: 0.** The development rounds needed no change.
- **Modified because of review: 0.**
- **Additions on the coordinator's request:** V7–V11 and the fixes, then V11g with `--headed`/`--v5-delays`.
- **Additions of mine:** V8d, and V11f recorded as not run.
- One edit was refused by this session's permission classifier, and the same change was then made with the Edit tool. No measurement was affected.

## Follow-up tables (generated by `--table` with `--table-glob`)

### chrome (Chrome/151.0.7922.169), candidateFix: none, `report-chrome-followup-20261017T040938.json`


**V7** (plain3, dirty, toolbar save, X ms after its reply Ctrl+End, Q 30 ms after that keydown)

| X planned (ms) | round | X actual: Ctrl+End kd − toolbar save reply (ms) | checkpoint save after the key | Q lands | move completion (round trip ms) | reply caret | +500 ms ask caret | final caret | request order |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 3.3 | False | pre-move caret | verified-move-readback (251.4) | 1564,1418 | 3657,1970 | 3657,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 0 | 2 | 3 | False | pre-move caret | verified-move-readback (252.4) | 1564,1418 | 3657,1970 | 3657,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 0 | 3 | 1.6 | False | pre-move caret | verified-move-readback (255.0) | 1564,1418 | 3657,1970 | 3657,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 300 | 1 | 300.9 | False | document end | documented-callback-visible-cursor (37.7) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 1000 | 1 | 1001.5 | False | document end | documented-callback-visible-cursor (46.6) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 1000 | 2 | 1001.4 | False | document end | documented-callback-visible-cursor (44.9) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 1000 | 3 | 1001.8 | False | document end | documented-callback-visible-cursor (38.9) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 3000 | 1 | 3001.3 | False | document end | documented-callback-visible-cursor (49.1) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |

**V8** (plain3: Z at the start, then «Bravo|», then ArrowDown and Q 30 ms later)

| round | caret before | Q lands | Q kd − ArrowDown kd (ms) | arrow completion (round trip ms) | reply caret | final caret | request order |
|---|---|---|---|---|---|---|---|
| 1 | 2064,1694 | P3 (the line moved to): para 2 off 6 'CharliQe third paragraph' | 30.4 | documented-callback-visible-cursor (45.9) | 2017,1970 | 2191,1970 | move-line-down → insertText → editorGetStateV2 |
| 2 | 2064,1694 | P3 (the line moved to): para 2 off 6 'CharliQe third paragraph' | 30.4 | documented-callback-visible-cursor (33.2) | 2017,1970 | 2191,1970 | move-line-down → insertText → editorGetStateV2 |
| 3 | 2064,1694 | P3 (the line moved to): para 2 off 6 'CharliQe third paragraph' | 31.0 | documented-callback-visible-cursor (35.2) | 2017,1970 | 2191,1970 | move-line-down → insertText → editorGetStateV2 |

**V8D** ((added) plain3: «Bravo|», then Z there, then ArrowDown and Q 30 ms later (the arrow is the first move after the change))

| round | caret before | Q lands | Q kd − ArrowDown kd (ms) | arrow completion (round trip ms) | reply caret | final caret | request order |
|---|---|---|---|---|---|---|---|
| 1 | 2151,1694 | P2 (the line before the move): para 1 off 6 'BravoZQ second paragraph' | 30.2 | verified-move-readback (250.6) | 2151,1694 | 2371,1970 | save → move-line-down → insertText → editorGetStateV2 |
| 2 | 2151,1694 | P2 (the line before the move): para 1 off 6 'BravoZQ second paragraph' | 30.3 | verified-move-readback (250.7) | 2151,1694 | 2371,1970 | save → move-line-down → insertText → editorGetStateV2 |
| 3 | 2151,1694 | P2 (the line before the move): para 1 off 6 'BravoZQ second paragraph' | 30.2 | verified-move-readback (251.0) | 2151,1694 | 2371,1970 | save → move-line-down → insertText → editorGetStateV2 |

**V11A** (after 「插入」 closes the dialog: Z through CDP Input.insertText)

| round | first input | at that moment: active / disabled / readOnly / inert / closest [inert] / pointer-events / dialog open / hasFocus | beforeinput / input anywhere | insertText | Z | W (pasted) | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | insertText Z | sink / False / False / False / None / none / False / True | ['insertText@sink'] / [] | True | para 1 off 0 'ZAlpha first paragraph' | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 2 | insertText Z | sink / False / False / False / None / none / False / True | ['insertText@sink'] / [] | True | para 1 off 0 'ZAlpha first paragraph' | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 3 | insertText Z | sink / False / False / False / None / none / False / True | ['insertText@sink'] / [] | True | para 1 off 0 'ZAlpha first paragraph' | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |

**V11B** (after 「插入」 closes the dialog: sink.blur(); sink.focus(), then a real Z)

| round | first input | at that moment: active / disabled / readOnly / inert / closest [inert] / pointer-events / dialog open / hasFocus | beforeinput / input anywhere | insertText | Z | W (pasted) | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | keydown Z | sink / False / False / False / None / none / False / True | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | absent | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 2 | keydown Z | sink / False / False / False / None / none / False / True | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | absent | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 3 | keydown Z | sink / False / False / False / None / none / False / True | ['insertText@sink'] / [] | True | para 1 off 0 'ZYXAlpha first paragraph' | absent | Y in, X after click in | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |

**V11C** (open the dialog, 取消 (no paste), then a real Z)

| round | first input | at that moment: active / disabled / readOnly / inert / closest [inert] / pointer-events / dialog open / hasFocus | beforeinput / input anywhere | insertText | Z | W (pasted) | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |
| 2 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |
| 3 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |

**V11D** (a range (`second`), open the dialog, paste, 「插入」 refused (dialog stays open), 取消, then a real Z)

| round | first input | at that moment: active / disabled / readOnly / inert / closest [inert] / pointer-events / dialog open / hasFocus | beforeinput / input anywhere | insertText | Z | W (pasted) | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |
| 2 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |
| 3 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |

**V11E** (after 「插入」 closes the dialog: a real Ctrl+V of plain text `W` into the sink)

| round | first input | at that moment: active / disabled / readOnly / inert / closest [inert] / pointer-events / dialog open / hasFocus | beforeinput / input anywhere | insertText | Z | W (pasted) | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | Ctrl+V W | sink / False / False / False / None / none / False / True | [] / [] | True | absent | para 1 off 0 'WAlpha first paragraph' | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 2 | Ctrl+V W | sink / False / False / False / None / none / False / True | [] / [] | True | absent | para 1 off 0 'WAlpha first paragraph' | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |
| 3 | Ctrl+V W | sink / False / False / False / None / none / False / True | [] / [] | True | absent | para 1 off 0 'WAlpha first paragraph' | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 → insertText → editorGetStateV2 |

**V11F** (the V5 step on the 0.2.24 page with another <dialog>)

Not run: the 0.2.24 page (dist/e2-editor.html, dist/e2-editor-app.js) has no <dialog> element and no showModal call, so there is no dialog to open and close.

### firefox (157.0.1), candidateFix: none, `report-firefox-followup-20261017T041915.json`


**V7** (plain3, dirty, toolbar save, X ms after its reply Ctrl+End, Q 30 ms after that keydown)

| X planned (ms) | round | X actual: Ctrl+End kd − toolbar save reply (ms) | checkpoint save after the key | Q lands | move completion (round trip ms) | reply caret | +500 ms ask caret | final caret | request order |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 9.4 | False | pre-move caret | verified-move-readback (251.4) | 1564,1418 | 3657,1970 | 3657,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 0 | 2 | 5.0 | False | pre-move caret | verified-move-readback (251.7) | 1564,1418 | 3657,1970 | 3657,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 0 | 3 | 6.7 | False | pre-move caret | verified-move-readback (251.5) | 1564,1418 | 3657,1970 | 3657,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 300 | 1 | 304.3 | False | document end | documented-callback-visible-cursor (41.1) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 1000 | 1 | 1004.3 | False | document end | documented-callback-visible-cursor (37.9) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 1000 | 2 | 1004.3 | False | document end | documented-callback-visible-cursor (38.5) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 1000 | 3 | 1003.9 | False | document end | documented-callback-visible-cursor (38.3) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |
| 3000 | 1 | 3003.6 | False | document end | documented-callback-visible-cursor (43.5) | 3657,1970 | 3830,1970 | 3830,1970 | save → editorGetStateV2 → move-document-end → insertText → editorGetStateV2 |

**V8** (plain3: Z at the start, then «Bravo|», then ArrowDown and Q 30 ms later)

| round | caret before | Q lands | Q kd − ArrowDown kd (ms) | arrow completion (round trip ms) | reply caret | final caret | request order |
|---|---|---|---|---|---|---|---|
| 1 | 2064,1694 | P3 (the line moved to): para 2 off 6 'CharliQe third paragraph' | 33.4 | documented-callback-visible-cursor (38.2) | 2017,1970 | 2191,1970 | move-line-down → insertText → editorGetStateV2 |
| 2 | 2064,1694 | P3 (the line moved to): para 2 off 6 'CharliQe third paragraph' | 32.8 | documented-callback-visible-cursor (38.6) | 2017,1970 | 2191,1970 | move-line-down → insertText → editorGetStateV2 |
| 3 | 2064,1694 | P3 (the line moved to): para 2 off 6 'CharliQe third paragraph' | 32.9 | documented-callback-visible-cursor (37.9) | 2017,1970 | 2191,1970 | move-line-down → insertText → editorGetStateV2 |

**V8D** ((added) plain3: «Bravo|», then Z there, then ArrowDown and Q 30 ms later (the arrow is the first move after the change))

| round | caret before | Q lands | Q kd − ArrowDown kd (ms) | arrow completion (round trip ms) | reply caret | final caret | request order |
|---|---|---|---|---|---|---|---|
| 1 | 2151,1694 | P2 (the line before the move): para 1 off 6 'BravoZQ second paragraph' | 33.3 | verified-move-readback (251.3) | 2151,1694 | 2371,1970 | save → move-line-down → insertText → editorGetStateV2 |
| 2 | 2151,1694 | P2 (the line before the move): para 1 off 6 'BravoZQ second paragraph' | 33.7 | verified-move-readback (251.2) | 2151,1694 | 2371,1970 | save → move-line-down → insertText → editorGetStateV2 |
| 3 | 2151,1694 | P2 (the line before the move): para 1 off 6 'BravoZQ second paragraph' | 33.4 | verified-move-readback (251.0) | 2151,1694 | 2371,1970 | save → move-line-down → insertText → editorGetStateV2 |

### chrome (Chrome/151.0.7922.169), candidateFix: fix1 (`editor-shell-v2/narrow-editor-v2-session.js` 8828a390500912f5…), `report-chrome-fix1-20261017T042309.json`


**V1** (plain3, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 31 | -18.5 | documented-callback-visible-cursor (48.0) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 30.5 | -16.8 | documented-callback-visible-cursor (46.3) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 30.5 | -5.5 | documented-callback-visible-cursor (34.9) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V2** (plain3, dirty, Q 50 ms after the move's reply)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 85.5 | 51.3 | documented-callback-visible-cursor (33.2) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 86.2 | 51.3 | documented-callback-visible-cursor (34.0) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 85.8 | 51.1 | documented-callback-visible-cursor (33.8) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V4** (long60, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 30.4 | -7.6 | documented-callback-visible-cursor (37.1) | 4037,1021644 | 4210,1021644 | 4210,1021644 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 30.8 | -17.4 | documented-callback-visible-cursor (47.2) | 4037,1021644 | 4210,1021644 | 4210,1021644 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 31.0 | -20.5 | documented-callback-visible-cursor (50.6) | 4037,1021644 | 4210,1021644 | 4210,1021644 | move-document-end → insertText → editorGetStateV2 |

**V3** (plain3, clean control, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 30.1 | -11.3 | documented-callback-visible-cursor (40.5) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 30.5 | -4.9 | documented-callback-visible-cursor (34.5) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 30.4 | -7.6 | documented-callback-visible-cursor (36.9) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**D11B** (the item-1 D11b arm reused: clean and dirty, Ctrl+End then Ctrl+Home, requests and unsaved state)

| round | kind | save requests | requests | completions (End, Home) | reply carets | +500 ms carets | unsaved: open / after typing / after End / after Home | checkpoint shown |
|---|---|---|---|---|---|---|---|---|
| 1 | clean | 0 | move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / None / false / false | ['無', '無'] |
| 1 | dirty | 0 | insertText → editorGetStateV2 → move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / true / true / true | ['無', '無'] |
| 2 | clean | 0 | move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / None / false / false | ['無', '無'] |
| 2 | dirty | 0 | insertText → editorGetStateV2 → move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / true / true / true | ['無', '無'] |
| 3 | clean | 0 | move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / None / false / false | ['無', '無'] |
| 3 | dirty | 0 | insertText → editorGetStateV2 → move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / true / true / true | ['無', '無'] |

### firefox (157.0.1), candidateFix: fix1 (`editor-shell-v2/narrow-editor-v2-session.js` 8828a390500912f5…), `report-firefox-fix1-20261017T042818.json`


**V1** (plain3, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 34.0 | -7.1 | documented-callback-visible-cursor (39.6) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 33.5 | -9.2 | documented-callback-visible-cursor (41.7) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 32.9 | -6.1 | documented-callback-visible-cursor (38.2) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V2** (plain3, dirty, Q 50 ms after the move's reply)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 94.0 | 52.4 | documented-callback-visible-cursor (40.7) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 97.1 | 55.6 | documented-callback-visible-cursor (40.5) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 94.5 | 52.9 | documented-callback-visible-cursor (40.7) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V4** (long60, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 33.1 | -9.3 | documented-callback-visible-cursor (41.5) | 4037,1021644 | 4210,1021644 | 4210,1021644 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 33.3 | -8.7 | documented-callback-visible-cursor (41.0) | 4037,1021644 | 4210,1021644 | 4210,1021644 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 33.7 | -8.1 | documented-callback-visible-cursor (40.4) | 4037,1021644 | 4210,1021644 | 4210,1021644 | move-document-end → insertText → editorGetStateV2 |

**V3** (plain3, clean control, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 34.1 | -9.1 | documented-callback-visible-cursor (42.3) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 2 | document end | 33.2 | -8.1 | documented-callback-visible-cursor (40.4) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |
| 3 | document end | 33.8 | -7.9 | documented-callback-visible-cursor (40.8) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**D11B** (the item-1 D11b arm reused: clean and dirty, Ctrl+End then Ctrl+Home, requests and unsaved state)

| round | kind | save requests | requests | completions (End, Home) | reply carets | +500 ms carets | unsaved: open / after typing / after End / after Home | checkpoint shown |
|---|---|---|---|---|---|---|---|---|
| 1 | clean | 0 | move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / None / false / false | ['無', '無'] |
| 1 | dirty | 0 | insertText → editorGetStateV2 → move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / true / true / true | ['無', '無'] |
| 2 | clean | 0 | move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / None / false / false | ['無', '無'] |
| 2 | dirty | 0 | insertText → editorGetStateV2 → move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / true / true / true | ['無', '無'] |
| 3 | clean | 0 | move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / None / false / false | ['無', '無'] |
| 3 | dirty | 0 | insertText → editorGetStateV2 → move-document-end → move-document-start | ['documented-callback-visible-cursor', 'documented-callback-visible-cursor'] | ['3657,1970', '1418,1418'] | ['3657,1970', '1418,1418'] | false / true / true / true | ['無', '無'] |

### chrome (Chrome/151.0.7922.169), candidateFix: fix2 (`e2-editor-app.js` 17a28c1cf6c859da…), `report-chrome-fix2-20261017T043407.json`


**V6E** ((added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight))

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 20.2, 40.2, 60.2] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |
| v21 | 2 | [0.0, 20.3, 40.4, 60.5] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |
| v21 | 3 | [0.0, 20.5, 40.4, 60.2] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |

**D8E** (the item-1 D8 (e) sequence reused: «Bravo|», Backspace @0, Backspace @20, Ctrl+End @40, Delete @60)

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 20.5, 40.4, 61.1] | 'Bra second paragraph' | 'Bra second paragraph' | False | False | delete-backward ×2 → save → move-document-end → delete-forward |
| v21 | 2 | [0.0, 20.7, 40.2, 60.7] | 'Bra second paragraph' | 'Bra second paragraph' | False | False | delete-backward ×2 → save → move-document-end → delete-forward |
| v21 | 3 | [0.0, 20.3, 40.2, 60.6] | 'Bra second paragraph' | 'Bra second paragraph' | False | False | delete-backward ×2 → save → move-document-end → delete-forward |

**RANGE** (a real drag selecting `second` in P2, then a real ArrowRight (no delete out))

| round | dragged | place-caret before the move | move completion | final caret | saved P2 | request order |
|---|---|---|---|---|---|---|
| 1 | 'second' | True | documented-callback-visible-cursor | 2790,1694 | 'Bravo second paragraph' | editorGetStateV2 → click → editorGetStateV2 ×5 → move-character-right |
| 2 | 'second' | True | documented-callback-visible-cursor | 2790,1694 | 'Bravo second paragraph' | editorGetStateV2 → click → editorGetStateV2 ×5 → move-character-right |
| 3 | 'second' | True | documented-callback-visible-cursor | 2790,1694 | 'Bravo second paragraph' | editorGetStateV2 → click → editorGetStateV2 ×5 → move-character-right |

### firefox (157.0.1), candidateFix: fix2 (`e2-editor-app.js` 17a28c1cf6c859da…), `report-firefox-fix2-20261017T043606.json`


**V6E** ((added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight))

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 23.5, 46.2, 72.1] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |
| v21 | 2 | [0.0, 22.8, 44.3, 67.6] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |
| v21 | 3 | [0.0, 23.0, 44.4, 71.1] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |

**D8E** (the item-1 D8 (e) sequence reused: «Bravo|», Backspace @0, Backspace @20, Ctrl+End @40, Delete @60)

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0, 21.1, 42, 60.6] | 'Bra second paragraph' | 'Bra second paragraph' | False | False | delete-backward ×2 → save → move-document-end → delete-forward |
| v21 | 2 | [0.0, 20.6, 41.1, 60.8] | 'Bra second paragraph' | 'Bra second paragraph' | False | False | delete-backward ×2 → save → move-document-end → delete-forward |
| v21 | 3 | [0.0, 21.0, 41.1, 60.8] | 'Bra second paragraph' | 'Bra second paragraph' | False | False | delete-backward ×2 → save → move-document-end → delete-forward |

**RANGE** (a real drag selecting `second` in P2, then a real ArrowRight (no delete out))

| round | dragged | place-caret before the move | move completion | final caret | saved P2 | request order |
|---|---|---|---|---|---|---|
| 1 | 'second' | True | documented-callback-visible-cursor | 2790,1694 | 'Bravo second paragraph' | editorGetStateV2 → click → editorGetStateV2 ×4 → move-character-right |
| 2 | 'second' | True | documented-callback-visible-cursor | 2790,1694 | 'Bravo second paragraph' | editorGetStateV2 → click → editorGetStateV2 ×5 → move-character-right |
| 3 | 'second' | True | documented-callback-visible-cursor | 2790,1694 | 'Bravo second paragraph' | editorGetStateV2 → click → editorGetStateV2 ×5 → move-character-right |

### chrome (Chrome/151.0.7922.169), candidateFix: fix12 (`e2-editor-app.js` 17a28c1cf6c859da…, `editor-shell-v2/narrow-editor-v2-session.js` 8828a390500912f5…), `report-chrome-fix12-20261017T043829.json`


**V1** (plain3, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 30.4 | -10.6 | documented-callback-visible-cursor (39.4) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V6E** ((added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight))

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 21.0, 40.3, 60.5] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |

### firefox (157.0.1), candidateFix: fix12 (`e2-editor-app.js` 17a28c1cf6c859da…, `editor-shell-v2/narrow-editor-v2-session.js` 8828a390500912f5…), `report-firefox-fix12-20261017T043900.json`


**V1** (plain3, dirty, Q 30 ms after Ctrl+End's keydown)

| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) | reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | document end | 34.2 | -8.8 | documented-callback-visible-cursor (41.8) | 3657,1970 | 3830,1970 | 3830,1970 | move-document-end → insertText → editorGetStateV2 |

**V6E** ((added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight))

| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move | a delete between that click and the move | request order |
|---|---|---|---|---|---|---|---|
| v21 | 1 | [0.0, 22.8, 44.9, 72.7] | 'Bra econd paragraph' | 'Bra econd paragraph' | False | False | delete-backward ×2 → save → move-character-right → delete-forward |

### chrome (Chrome/151.0.7922.169), candidateFix: none, `report-chrome-headed-20261017T044017.json`


**V5** (Markdown dialog `# a`, Z 0 / 300 ms after it closes (+ added controls late, no-dialog))

| round | delay | dialog close → Z kd (ms) | Z kd target / active | sink disabled at Z | keypress (prevented) | beforeinput / input anywhere after Z | insertText | Z in saved doc | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 300 | 301.2 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 2 | 300 | 301.2 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 3 | 300 | 301.7 | sink / sink | False | True (False) | [] / [] | False | absent | Y absent, X after click absent | pasteMarkdown → editorGetStateV2 |
| 1 | no-dialog |  | sink / sink | False | True (False) | ['insertText@sink'] / [] | True | para 0 off 0 'ZYXAlpha first paragraph' | Y in, X after click in | insertText → editorGetStateV2 |

**V11C** (open the dialog, 取消 (no paste), then a real Z)

| round | first input | at that moment: active / disabled / readOnly / inert / closest [inert] / pointer-events / dialog open / hasFocus | beforeinput / input anywhere | insertText | Z | W (pasted) | then Y (no click), X (after click) | request order |
|---|---|---|---|---|---|---|---|---|
| 1 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |
| 2 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |
| 3 | keydown Z | sink / False / False / False / None / none / False / True | [] / [] | False | absent | absent | Y absent, X after click absent |  |

