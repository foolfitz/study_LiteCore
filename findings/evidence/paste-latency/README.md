# paste-latency: the owner's slow Ctrl+V into a new document (task 2026-10-14f)

Task: `handoff/tasks/TASK-2026-10-14f-slow-paste-diagnosis.md`. Host: `~/Projects/Nextcloud_Apps/litecore` 0.2.19 (`afbaf3c`), engine package buildId `d6d04880f56e31da` = page `b24d754a…` + profile `e2-editor-v19` (0.2.18's package, kept by 0.2.19; shell generation v66). Browsers: Chrome 151.0.7922.169, Firefox 157.0.1 (both headless, fresh profiles, cold cache). No product byte was changed; nothing here is a fix.

## The report being reproduced

The owner hand-tested host 0.2.19 on `https://litecore.ddev.site:8443`: Files → + New → 新文字文件, then Ctrl+V of a 40-line Markdown text, in Chrome and in Firefox: 「他過好久才跑完，為什麼那麼久？」. Asked three questions, the owner answered (relayed by the main session, verbatim): about ten-plus seconds (「大概十幾秒」); both browsers were slow; the 處理中 pill stayed lit the whole time (not text appearing in pieces, not a frozen page).

The pasted text is the owner's and names a person; it is never written into this folder. Its shape: 40 lines, 577 characters (1,363 bytes UTF-8), 389 of them CJK by the probe's ranges (CJK ideographs, kana, CJK and full-width punctuation; the task's "349" counts ideographs only), sha256 `478f75cb0fbf3086…`. `leak_check.py` searches every file here for every line of the text, every 6-character window that carries a non-ASCII character and every 12-character window (ASCII-only 6-character windows are ordinary words): `hits {}` on the committed tree.

## Conclusion (one paragraph)

**The ten-plus seconds are not the paste. They are the click that precedes it.** The paste itself is one `paste` event → the input adapter's own `paste` listener → one `commitText` → one `insertText` → one engine `paste()` that takes **22.5–24.8 ms in Chrome and 7.5–8.8 ms in Firefox** for all 40 paragraphs (native LibreOfficeKit 26.8: 6.7 ms), with the pill back to 就緒 within 10–27 ms and the page fully repainted within 200–260 ms. What holds the session `busy` is the click a user makes to put the caret into the blank page before pasting: `placeCaret` (`editor-shell/editor-session.js:394`, the base implementation the served v66 shell runs; the v67 override in `editor-shell-v2/narrow-editor-v2-session.js:608` keeps the same wait) returns only when the caret is on the clicked line or the engine moved it, and in an empty document a click anywhere below the first line does neither — the engine clamps the caret to the one position it already has — so the wait runs out its full `caretTimeoutMs` of **30.0 s** (5,328–5,550 `editorGetStateV2` polls), ends in `EDITOR_CARET_NOT_PLACED`, and only then is the queued paste sent to the engine. Measured identically in both browsers and with or without the host: pill `busy` 2.2–5.1 ms after the click, 處理中 shown 700 ms later (finding 125's delay), `paste` event 0.4–0.7 ms after Ctrl+V, `insertText` sent 30,005–30,014 ms after the click (mid-page and 25 %-down clicks alike), 40 paragraphs saved by the autosave 30 s after the pill returned. This is **finding 052's named residual** (a click the engine answers by moving nothing; `editorPlaceCaretV2`, which bounds it at 38/251 ms, is driven only by the harness page `web/e2-c-block-identity-app.js` and not by the product's `placeCaret`), met on the first click of every blank document rather than on a second click outside the text — a new shape of a known finding, not 122, not 111, not the autosave. The owner's "ten-plus" against a measured 30.0 s is the one thing not reproduced; no phase of about ten seconds was found anywhere (see "Not matched" below).

## What was checked of the main session's reading

| claim | measured |
| --- | --- |
| The page has no paste handler; paste arrives as `beforeinput` `insertFromPaste` and the input adapter commits it as one `commitText` | Half right. The page has none (`web/e2-editor-app.js:2392`), but the **input adapter has a `paste` listener** (`input/input-adapter.js:78`, `handlePaste`: `clipboardData.getData("text/plain")`, `preventDefault`, one `commitText`). Because it prevents the default, **no `beforeinput` fires at all** — `beforeinputInsertFromPaste` is null in every run, in both browsers; the `paste` event (577 characters) is the only input event. The outcome the claim cares about holds: exactly one `insertText` of 577 characters, `method: "paste"`. |
| One `document.insertText` → one engine `paste(document, "text/plain;charset=utf-8", …)` | Confirmed: one `insertText` request, reply `method: "paste"`, revision +1, 40 paragraphs in the saved file (1 / 40 / 80 for the controls). |
| The time is between that paste and the page settling: engine layout / callbacks / repaint / autosave / finding 111's hold / something else | None of those. Engine insert 7.4–24.8 ms; drain `getState` 0.7–8 ms; one or two `document-invalidated`; one paint pass of 37–261 ms (3–7 paint requests; no long task); autosave 30 s after the pill returned (its engine part ≈ 400 ms, PUT answered ≈ 90 ms later); no `_afterTyped` hold (the adapter's queue was empty). "Something else": the click before the paste. |

## Method

`wasm_sdk_probe/tools/probe_paste_latency.py` (committed with this evidence). Per arm it drives the owner's path — login as admin, Files → + New → the litecore entry → the name dialog → the editor (`check_m3_new_document.create_from_menu`, the N4 runner's own driving), waits for the host's `done` and the session's `ready` — then appends one instrumentation script to the page (`r7_support.run_in_page`, the same in both browsers, after the editor is ready, no served byte changed). The script records on `performance.now()`: every `keydown`/`paste`/`beforeinput`/`input` (capture phase), every Worker request and reply by id and operation (`Worker.prototype.postMessage` + a `message` listener on the instance), every Worker event, every change of `#state-pill`, `#state-shown`, `#s-revision`, `#s-pending`, `#s-latency`, `#toast`, `#litecore-host-saved/-unsaved`, every `putImageData`, resource timings and (Chrome) long tasks.

Then the click, the clipboard, the key:

- **click** `first-line` = the N4 runner's point (x 0.3, y 23 mm of A4), waited for like the runners do; `page-middle` = (0.5, 0.5) of `#paper`, NOT waited for — a user clicks and pastes about a second later; `below-first-line` = (0.3, 0.25).
- **clipboard**, real: Chrome — `Browser.grantPermissions` (clipboardReadWrite, clipboardSanitizedWrite) then `navigator.clipboard.writeText` in the page and `readText` back (`same: true` in every run); Firefox — pref `dom.events.testing.asyncClipboard` and the same two calls against its headless clipboard (`same: true`).
- **Ctrl+V**, trusted: Chrome `Input.dispatchKeyEvent` (Control down, v down with modifiers 2, ups); Firefox WebDriver key actions (`\ue009` = Control, `v`). Both browsers produced a trusted `paste` event on the sink; no arm needed a synthetic insert.
- then: wait for the revision to move and the queue to be empty for 0.5 s, 4 s more for repaints, read the log; on the host also wait for the autosave (≤ 50 s) and read the saved file's paragraph count over WebDAV (count only).

Every run preflighted: KWallet `Locked` = `b false`, `pgrep -c chrome` (28–34: the owner's interactive Chrome), none of our runners (`preflight` in each report). The runs' files lived in a folder of the probe's own (`貼上 測試資料夾`) and were deleted afterwards. Never two browsers at once.

## Phase tables (generated by `tables.py` from `raw/*.json`)

Milliseconds after the Ctrl+V keydown on the page's clock. "click" says where the pointer was put and how long before the key (or that the click was waited for before the key). "engine insert" = `insertText` request → reply; "getState" = the drain's own read after it; "getState polls before insert" = `editorGetStateV2` requests between the click and the `insertText` request (the `placeCaret` wait).

| report | mode | browser | arm (lines/chars/CJK) | click (ms before key) | paste event | insertText sent | engine insert | getState | pill ready | last blit | getState polls before insert | autosave PUT answered | saved paragraphs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `host-ddev-chrome-below-first-line-r7-2026-10-14T065849Z.json` | host | chrome | owner (40/577/389) | below-first-line (1,410.9) | 0.5 | 28,594.4 | 24.8 | 1.0 | 28,620.1 | 28,829.5 | 5550 | 59,116.2 | 40 |
| `host-ddev-chrome-first-line-r5-2026-10-14T065537Z.json` | host | chrome | single (1/576/389) | first-line (waited) | 0.5 | 1.8 | 24.0 | 1.3 | 27.1 | 261.4 | 0 | 30,477.9 | 1 |
| `host-ddev-chrome-first-line-r5-2026-10-14T065537Z.json` | host | chrome | ascii (40/600/0) | first-line (waited) | 0.5 | 1.8 | 18.0 | 0.9 | 20.6 | 52.6 | 0 | 30,329.5 | 40 |
| `host-ddev-chrome-first-line-r5-2026-10-14T065537Z.json` | host | chrome | ascii80 (80/1200/0) | first-line (waited) | 0.5 | 1.8 | 12.3 | 0.9 | 15.0 | 74.2 | 0 | 30,256.4 | 80 |
| `host-ddev-chrome-page-middle-r2-2026-10-14T064923Z.json` | host | chrome | owner (40/577/389) | page-middle (1,414.8) | 0.5 | 28,592.2 | 23.7 | 0.8 | 28,616.7 | 28,832.6 | 5518 | 59,119.7 | 40 |
| `host-ddev-chrome-shakedown1-2026-10-14T064301Z.json` | host | chrome | owner (40/577/389) | first-line (waited) | 0.4 | 1.6 | 22.5 | 0.7 | 24.7 | 253.5 | 0 | 30,490.9 | 40 |
| `host-ddev-firefox-first-line-r4-2026-10-14T071309Z.json` | host | firefox | owner (40/577/389) | first-line (waited) | 0.3 | 1.2 | 7.5 | 0.8 | 9.4 | 196.6 | 0 | 30,426.6 | 40 |
| `host-ddev-firefox-first-line-r4-2026-10-14T071309Z.json` | host | firefox | single (1/576/389) | first-line (waited) | 0.2 | 0.9 | 7.8 | 0.9 | 9.5 | 234.0 | 0 | 30,450.9 | 1 |
| `host-ddev-firefox-first-line-r4-2026-10-14T071309Z.json` | host | firefox | ascii (40/600/0) | first-line (waited) | 0.3 | 1.3 | 7.4 | 1.0 | 9.7 | 37.2 | 0 | 30,267.5 | 40 |
| `host-ddev-firefox-first-line-r4-2026-10-14T071309Z.json` | host | firefox | ascii80 (80/1200/0) | first-line (waited) | 0.3 | 1.4 | 8.6 | 0.8 | 10.7 | 55.7 | 0 | 30,300.0 | 80 |
| `host-ddev-firefox-page-middle-r3-2026-10-14T065251Z.json` | host | firefox | owner (40/577/389) | page-middle (1,432.0) | 0.7 | 28,581.6 | 8.8 | 8.0 | 28,598.2 | 28,797.4 | 5358 | 59,045.9 | 40 |
| `nohost-dist-chrome-first-line-r8-2026-10-14T071218Z.json` | nohost/dist | chrome | owner (40/577/389) | first-line (waited) | 0.7 | 1.9 | 14.9 | 1.0 | 17.7 | 191.9 | 0 | – | – |
| `nohost-host-engine-chrome-page-middle-r6-2026-10-14T070111Z.json` | nohost/host-engine | chrome | owner (40/577/389) | page-middle (1,411.8) | 0.4 | 28,595.8 | 20.9 | 0.8 | 28,617.4 | 28,800.8 | 5328 | – | – |
| `nohost-host-engine-firefox-first-line-r6-2026-10-14T070655Z.json` | nohost/host-engine | firefox | owner (40/577/389) | first-line (waited) | 0.4 | 1.6 | 8.8 | 1.2 | 11.4 | 197.9 | 0 | – | – |

## Reading the tables

- **Owner's path, first-line click (waited for, 322–405 ms)**: paste event 0.3–0.7 ms, `insertText` sent 1.2–1.9 ms, engine 7.5 ms (Firefox) / 22.5 ms (Chrome), pill 就緒 at 9–25 ms, last blit ≈ 197–254 ms. Nothing to see.
- **Owner's path, mid-page or 25 %-down click, paste 1.4 s later** (both browsers; `r2`, `r3`, `r7`; the no-host mirror `r6` the same): the pill goes `busy` within 2.2–5.1 ms of the click; `click` is answered by the engine in < 1 ms (revision 0, nothing moved); `placeCaret` then polls `editorGetStateV2` every ≈ 5 ms; the `paste` event arrives 0.5–0.7 ms after Ctrl+V and the session's `pending` rises to 2; at **30.0 s after the click** (30,005–30,014 ms) the wait expires (`#s-latency` 「定位游標 失敗」, toast 「定位游標：EDITOR_CARET_NOT_PLACED：the caret did not reach the point that was clicked」), the `insertText` request goes out in the same millisecond, the engine answers in 8.8–24.8 ms, the pill returns, the page repaints in ≈ 200 ms, and the 40 paragraphs are in the autosaved file 30 s later. In Firefox the engine did announce five `editor-state` changes ≈ 330 ms after the click (sourceSequence 5→9) — an acknowledgement without a caret move, which the wait correctly does not accept.
- **Controls**: the same text as one line (engine 24.0 / 7.8 ms), 40 lines of ASCII (18.0 / 7.4 ms), 80 lines of ASCII (12.3 / 8.6 ms) — the paragraph count and the CJK content cost nothing measurable, and the repaint is what scales (37–74 ms for the ASCII pages, which fit one screen band; 197–261 ms when the page has CJK lines). No host: the host's own engine package decompressed from `engine/files/*.zst` (22 files, every sha256 equal to `engine/MANIFEST.json`, page `b24d754a…`) served by `web/serve.py` with the blank A4 template opened through the page's file input shows the same 30.0 s with the mid-page click (Chrome) and the same 8.8 ms paste with the first-line click (Firefox); `dist/` today (page `7815e16c…`, profile v19) 14.9 ms. So neither the host, nor the autosave, nor the served page version is part of the 30 s.

## The mechanism, read from the source after the measurement

`web/e2-editor-app.js` pointerdown on the paper (served page `:2280`; tree `:2365`) → `run("定位游標", () => session.placeCaret(x, y))`. The served shell (generation v66, `editor-shell-v2/narrow-editor-v2-session.js` `62a2a20e…`) has no override, so this is `EditorSession.placeCaret` (`editor-shell/editor-session.js:394–437`, E1-C-bound): `timeoutMs = 30000`, `graceMs = 400`; after `document.click` it loops `getState` (5 ms sleep between) until `caretIsOnLine(caret, yTwips)` (within half a line above and the line's height below the caret rectangle, `:52`) and the sequence advanced or the grace passed — or the sequence advanced AND the caret moved (finding 052's fix). In a blank document the only caret rectangle is the first line's (≈ 2 cm from the top); a click at 50% or 25% of the page is far below it, so `onTarget` is false, and the engine clamps the caret to the start of the one empty paragraph, which is where it already was, so `caretMoved` is false. Both exits are closed for the whole 30 s. The v67 override (`narrow-editor-v2-session.js:608–650`, finding 138) adds `selectionChanged` as a third acknowledgement and keeps the same timeout; a click in a blank page changes no selection either, so it does not change this case.

The session queue is strictly serial (`EditorSession._drain`): `commitText` from the paste is appended behind the pending `place-caret` item and is dispatched only when it settles. The pill is the session state (`busy` from the click), and finding 125's `BUSY_SHOWN_AFTER_MS = 700` makes 處理中 appear 0.7 s after the click — what the owner saw "the whole time".

Finding 052 (`findings/052-…md`) fixed the common case (a click below the text of a document that has text: the engine moves the caret to the nearest line) and named this residual: "點兩次文字以外的地方，第二次仍然要等 30 秒。游標已經在夾過去的位置了，所以什麼都不會動". A blank document makes the residual the **first** click: the caret is already where every click clamps to. The register's note that `editorPlaceCaretV2` closed it (38/251 ms) holds for the harness page that drives that request (`web/e2-c-block-identity-app.js:11`, "NOT the shell's"); the product's `placeCaret` never calls it (no caller in `web/e2-editor-app.js`, `editor-shell*/`).

## Not matched: "大概十幾秒"

Every measured wait is 30.0 s, in both browsers, and no phase of roughly ten seconds exists on the path (the next-longest things are the 405 ms autosave engine part and the 200 ms repaint). Either the owner's estimate is rough, or the owner's sequence differed from the one reproduced (for example, a click on the first line is instant, a click anywhere else is 30 s; two clicks outside the text queue two waits). A question for the owner, if it matters: did you click into the page body before pasting, and roughly how long after that click did you press Ctrl+V?

## What a fix would touch (not made)

- `editor-shell-v2/narrow-editor-v2-session.js` `placeCaret` (the override that v67 ships; the base `editor-shell/editor-session.js` is E1-C-bound): a third exit for "the engine answered the click and the caret is where the clamp puts it". The engine's own answer exists already — `editorPlaceCaretV2` (`sdk/sdk-worker.js:1552`, "answers with the caret paragraph's fingerprint and the offset in it, and it answers even when nothing moved, which is the case the 30-second waits were made of") — the product never adopted it; adopting it is the 052 prescription (`queue-verify-caret-by-block-identity`), with finding 056's caveat that the fingerprint half is empty on WASM while the bounded answer half works.
- Cheaper and narrower: accept `already-at-target` when the clicked point is below the document's last line box (the page has the page rectangles since v20's `notePageRectangles`, and `document.heightTwips`), or when the document has one empty paragraph; or let the page's pointerdown (`web/e2-editor-app.js:2365`) pass a shorter `caretTimeoutMs` with the refusal kept.
- The owner's symptom would also shrink if a refused `placeCaret` did not hold the queue: the paste could be dispatched as soon as the engine has answered the click (it has, in < 1 ms), but that reorders what finding 138 is about and is not a one-line change.

## Files

| path | what |
| --- | --- |
| `raw/*.json` | one report per run: preflight, host identity, versions, text shape (no text), the whole event log, the host's `data-litecore` after the autosave, the saved file's paragraph count, and the derived `phases` block |
| `tables.py` | the phase tables above, from `raw/` |
| `refresh_phases.py` | recompute every stored `phases` block with the probe's current extraction |
| `leak_check.py` | proves the owner's text is not in this folder |
| `native/` | `tool/lok_paste_probe.cpp` (LibreOfficeKit client, built with `-DLOK_USE_UNSTABLE_API`), its stdout/stderr for `paste` and `keys` on the blank A4 template under `LANG=zh_TW.UTF-8`, `SAL_USE_VCLPLUGIN=svp`; `SHA256SUMS` |
| `wasm_sdk_probe/tools/probe_paste_latency.py` (repo root) | the probe; `--summarize raw/*.json` prints one line per run |

Native (26.8, same binary as `new-document/probe-1-native-defaults`): `paste()` of the owner's text **6.7 ms** (40 paragraphs, 537 characters in the saved file, no LOK callback during the call); the same text through `postKeyEvent` one code point at a time **114.9 ms** (41 paragraphs: the trailing newline). The process dies with signal 11 at `destroy` after `saveAs`, after every number above was printed; not investigated.

---

# Ruling and fix (2026-10-14, fable on the owner's behalf; append-only from here)

## The bound, stated before any run

Candidate: `wasm_sdk_probe/editor-shell-v2/` with `placeCaret` asking the engine (`editorPlaceCaretV2`) first and judging its answer with finding 138's predicate; v67's polling kept as the fallback (details in the ruling section below, written after the witness so that it records what was run; the bound here was written first).

Prediction, per arm of `probe_paste_latency.py --mode nohost`, owner text, both browsers, v19 profile (dist/) and v20 profile (a dist mirror with `build_cutover_page.py --profile e2-editor-v20 --out …`, never `--write`):

- `page-middle` and `below-first-line` clicks: `insertText` is sent **within 1,500 ms of the click** (engine readback 250 ms + the 400 ms grace counted from the request + page and worker overheads; the red case on the current v67 bytes is 30,005–30,014 ms, measured above on v19, and is measured below on v20 before the candidate). The toast 「定位游標：EDITOR_CARET_NOT_PLACED…」 must not appear; the pill must return to 就緒 before the paste lands; 40 paragraphs must still be the result (`revision` 1 after the paste).
- `first-line` click: unchanged in outcome — `#s-latency` 「定位游標 N ms」 with N ≤ 500 (today 322–405 ms by the grace; the engine path may answer earlier on the cursor callback), engine insert within the ranges above (7–25 ms), `insertText` sent within 5 ms of the paste event.
- Nothing else on the path changes: one `paste` event, one `insertText`, `method: "paste"`, no `beforeinput`.

If any arm misses the bound, the candidate is not frozen and the miss is recorded here as measured.

## Ruling (fable, on the owner's behalf, 2026-10-14): A — the product's `placeCaret` asks the engine

**Chosen: A**, finding 052's own prescription, with finding 138's predicate kept as the judge of the engine's answer and finding 048's grace kept as the guard. Not B, not C.

- **A** (`editorPlaceCaretV2`): the engine posts the mouse events itself and answers on the cursor callback the click caused (`documented-callback-visible-cursor`) or, when the click changed nothing and no callback came, at its own 250 ms readback deadline (`verified-caret-readback`; `src/probe_engine.cpp:5890–5936`, `EditorPlaceCaretDeadlineMs = 250`). It completes only on the visible-cursor callback (`completePendingEditorOperation`), never on a tile or size callback, so 138's lone bump cannot end it. Reachable on the shipped profiles: the worker gates it on `narrow-editor-v2` version 2 (`sdk/sdk-worker.js:48,184,1552`), which v19 and v20 both declare; `_oxsdk_editor_place_caret` is in both `probe.js` export tables (`Module["_oxsdk_editor_place_caret"]`). No relink. **056's caveat**: the answer's `caretParagraph` half (the a11y fingerprint) is empty on the shipped Writer cores (`ENABLE_WASM_STRIP_ACCESSIBILITY` → `refreshCaretParagraph` is a no-op; v19/v20 are not the a11y core) — this fix never reads it; it uses the `caret` rectangle, the `selection` and `completion`, which come from the cursor/selection callbacks and `appendEditorState`, the same fields `getState` already serves. 056 measured the bounded half as 38 ms (callback) / 251 ms (readback) on WASM; that is the half used here.
- **B** (narrower exit: accept when the click is below the last line box / the document is one empty paragraph) was rejected: the session has no line boxes but the caret's own (v20's page rectangles are pages, not lines, and v19 has none), "one empty paragraph" would need the outline the stripped cores do not carry, and B still leaves every other no-move click — between two lines in a document with text, in a margin beside an unchanged caret — on the 30 s path. It is a special case of a problem the engine already answers generally.
- **C** (shorter timeout) was rejected: it turns a legitimate click into a refusal after N seconds instead of 30, still holds the paste behind it, and still shows the EDITOR_CARET_NOT_PLACED toast for a click the engine handled correctly.

**What was kept, by test** (`editor-shell-v2/tests/place-caret-blank-page.test.mjs`, red first — 7 of 13 red on the v67 bytes, 13/13 on the candidate; `place-caret-acknowledgement.test.mjs`'s seven 138 arms and controls untouched and green; full suite 412 → 425, all green; `check_e1_c_bundle_intact.py` intact before and after):

- 138: the engine's answer is judged — evidence = the sequence advanced AND the caret position or the selection differs from the pre-click read; never the sequence alone. A lone unrelated callback inside the window does not end the wait; the click's own evidence does.
- 048: an answer without evidence is not accepted on arrival. The core gets the same `caretAckGraceMs` (400 ms, counted from the request) the identical-point click has always had, re-read every 5 ms; a click landing inside the grace is seen and judged (test: the readback at 250 ms carries the old caret, the click lands at 300 ms on another line → `engine-moved-the-caret-off-the-clicked-line` with the new caret, and the next command sees it).
- 052: a click the engine answers by moving the caret to another line → the base's `engine-moved-the-caret-off-the-clicked-line`, on the cursor callback, no grace paid.
- identical point: `already-at-target` after the grace, as before.
- the new case: no evidence and off the line after the grace → `engine-answered-the-caret-stayed`, `caretOnClickedLine: false`, the engine's caret in `state`, plus `completion`. One new `caretConfirmedBy` value; nothing in `web/` reads the field (grep). The page is unchanged.
- fallback: a client without `placeCaret`, a worker that refuses it (`UNSUPPORTED_OPERATION`) or an engine `BUSY` behind a barrier take v67's polling loop unchanged, with its timeout and its EDITOR_CARET_NOT_PLACED error and details; any other engine error is the caller's.
- **named limit** (test): a click the core processes only after the grace (> 400 ms from the request) is accepted as "stayed" with the old caret — the same bound the identical-point click has always had. On this machine the core processes a click in 22–28 ms (048); a stall ten times that would be needed.

**Cost**: a blank-page click now ends at ≈ 400 ms (readback 250 + grace to 400) instead of 30 s; the first-line click, which already paid the grace (`already-at-target`), is unchanged at ≈ 405 ms; a click that moves the caret is answered by the callback (tens of ms) with no grace, as 138's arms require. Polls per click: ≈ 28 `getState` re-reads during the grace instead of 5,300–5,550.

**Touched**: `editor-shell-v2/narrow-editor-v2-session.js` (`placeCaret` override, `PLACE_CARET_FALLBACK_CODES`), `editor-shell-v2/paragraph-editor-client.js` + `narrow-editor-v2-client.js` (`placeCaret` request method, `.d.ts` both), the new test file, and `tools/probe_paste_latency.py` (`--root dir --root-dir`, shell identity in the no-host reports). Not touched: `editor-shell/` (E1-C), `web/`, `sdk/`, `src/`, the Makefile, the host, any profile. `dist/editor-shell-v2/` was refreshed by `make e2-c-assets` (three `cp` lines, checked with `make -n` first) so that the witness served the candidate; that directory is git-ignored, so nothing of dist is committed here and the main session's v68 freeze copies the same bytes from source. **No shell generation was frozen; no host was changed.**


## Witness (after the bound above; the probe's rows, `tables.py` output filtered to these runs)

Red first on the v20 profile too: `mirror-v20-red` = dist symlinked + the v20 candidate page (`build_cutover_page.py --profile e2-editor-v20 --out …`, page `53019168…`) + the three `editor-shell-v2` files at HEAD `b05f081b` (session `77841656…` = the v67 bytes), materialised so that `make e2-c-assets` could not touch it. Then `make e2-c-assets` (three `cp` lines) and the candidate: v19 = `dist/` (page `7815e16c…`), v20 = `mirror-v20-candidate` (the same v20 page over dist's symlinks); candidate session `fc5ac883…`.

| report | mode | browser | arm (lines/chars/CJK) | click (ms before key) | click resolved (ms after click) | paste event | insertText sent | engine insert | getState | pill ready | last blit | getState polls before insert | autosave PUT answered | saved paragraphs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `nohost-dir-mirror-v20-candidate-chrome-first-line-cand-v20-2026-10-14T073555Z.json` | nohost/dir | chrome | owner (40/577/389) | first-line (waited) | 定位游標 408 ms | 0.4 | 1.8 | 17.0 | 3.0 | 21.7 | 214.4 | 0 | – | – |
| `nohost-dir-mirror-v20-candidate-chrome-page-middle-cand-v20-2026-10-14T073539Z.json` | nohost/dir | chrome | owner (40/577/389) | page-middle (1,410.6) | 409.2 (定位游標 408 ms) | 0.4 | 1.8 | 17.5 | 1.1 | 20.3 | 244.8 | 29 | – | – |
| `nohost-dir-mirror-v20-candidate-firefox-below-first-line-cand-v20-2026-10-14T073635Z.json` | nohost/dir | firefox | owner (40/577/389) | below-first-line (1,331.6) | 412.0 (定位游標 406 ms) | 0.3 | 1.6 | 10.0 | 1.1 | 12.7 | 215.1 | 28 | – | – |
| `nohost-dir-mirror-v20-candidate-firefox-page-middle-cand-v20-2026-10-14T073611Z.json` | nohost/dir | firefox | owner (40/577/389) | page-middle (1,331.9) | 410.6 (定位游標 405 ms) | 0.2 | 1.4 | 7.9 | 0.8 | 10.1 | 201.1 | 28 | – | – |
| `nohost-dir-mirror-v20-red-chrome-page-middle-red-v20-2026-10-14T073706Z.json` | nohost/dir | chrome | owner (40/577/389) | page-middle (1,411.5) | 30,006.9 (定位游標 失敗) | 0.4 | 28,595.2 | 12.2 | 0.9 | 28,608.2 | 28,819.8 | 5542 | – | – |
| `nohost-dist-chrome-below-first-line-cand-v19-2026-10-14T073419Z.json` | nohost/dist | chrome | owner (40/577/389) | below-first-line (1,410.9) | 405.9 (定位游標 405 ms) | 0.4 | 1.6 | 14.9 | 1.1 | 17.5 | 238.1 | 28 | – | – |
| `nohost-dist-chrome-first-line-cand-v19-2026-10-14T073435Z.json` | nohost/dist | chrome | owner (40/577/389) | first-line (waited) | 定位游標 407 ms | 0.4 | 2.0 | 12.8 | 1.0 | 15.7 | 259.2 | 0 | – | – |
| `nohost-dist-chrome-page-middle-cand-v19-2026-10-14T073404Z.json` | nohost/dist | chrome | owner (40/577/389) | page-middle (1,411.9) | 406.3 (定位游標 405 ms) | 0.7 | 2.2 | 18.0 | 1.1 | 21.3 | 243.2 | 28 | – | – |
| `nohost-dist-firefox-first-line-cand-v19-2026-10-14T073515Z.json` | nohost/dist | firefox | owner (40/577/389) | first-line (waited) | 定位游標 405 ms | 0.2 | 1.8 | 8.3 | 0.9 | 11.0 | 205.5 | 0 | – | – |
| `nohost-dist-firefox-page-middle-cand-v19-2026-10-14T073451Z.json` | nohost/dist | firefox | owner (40/577/389) | page-middle (1,331.6) | 412.8 (定位游標 406 ms) | 0.2 | 1.3 | 8.8 | 1.0 | 11.0 | 212.9 | 27 | – | – |

| report | profile | page | shell session | preflight (KWallet / chrome / other runners) |
| --- | --- | --- | --- | --- |
| `nohost-dir-mirror-v20-candidate-chrome-first-line-cand-v20-2026-10-14T073555Z.json` | e2-editor-v20 | `53019168…` | `fc5ac883…` | b false / 31 / [] |
| `nohost-dir-mirror-v20-candidate-chrome-page-middle-cand-v20-2026-10-14T073539Z.json` | e2-editor-v20 | `53019168…` | `fc5ac883…` | b false / 28 / [] |
| `nohost-dir-mirror-v20-candidate-firefox-below-first-line-cand-v20-2026-10-14T073635Z.json` | e2-editor-v20 | `53019168…` | `fc5ac883…` | b false / 29 / [] |
| `nohost-dir-mirror-v20-candidate-firefox-page-middle-cand-v20-2026-10-14T073611Z.json` | e2-editor-v20 | `53019168…` | `fc5ac883…` | b false / 31 / [] |
| `nohost-dir-mirror-v20-red-chrome-page-middle-red-v20-2026-10-14T073706Z.json` | e2-editor-v20 | `53019168…` | `77841656…` | b false / 33 / [] |
| `nohost-dist-chrome-below-first-line-cand-v19-2026-10-14T073419Z.json` | e2-editor-v19 | `7815e16c…` | `fc5ac883…` | b false / 31 / [] |
| `nohost-dist-chrome-first-line-cand-v19-2026-10-14T073435Z.json` | e2-editor-v19 | `7815e16c…` | `fc5ac883…` | b false / 31 / [] |
| `nohost-dist-chrome-page-middle-cand-v19-2026-10-14T073404Z.json` | e2-editor-v19 | `7815e16c…` | `fc5ac883…` | b false / 30 / [] |
| `nohost-dist-firefox-first-line-cand-v19-2026-10-14T073515Z.json` | e2-editor-v19 | `7815e16c…` | `fc5ac883…` | b false / 31 / [] |
| `nohost-dist-firefox-page-middle-cand-v19-2026-10-14T073451Z.json` | e2-editor-v19 | `7815e16c…` | `fc5ac883…` | b false / 30 / [] |

**Against the bound**: every `page-middle` and `below-first-line` arm on the candidate resolved the click at **405.9–412.8 ms after the click** (`#s-latency` 「定位游標 405–407 ms」, no EDITOR_CARET_NOT_PLACED toast), 27–28 `getState` re-reads instead of 5,300–5,550, and the paste that followed 1.3–1.4 s later was sent 1.3–2.2 ms after its `paste` event — within the stated 1,500 ms by a factor of three; `revision` 1 after the paste in every arm (the paste landed). Both browsers, both profiles. The red case on the v20 page (`red-v20`, the v67 bytes) is 30,007 ms after the click with 5,542 polls — the same shape as v19's `r2`/`r3`/`r6`/`r7`. The `first-line` arms are unchanged in outcome (「定位游標 405–407 ms」, engine insert 8.3–17.0 ms, `insertText` 1.8–2.0 ms after the paste event; the 322–328 ms the v67 Firefox rows showed for this arm came from the polling loop's grace being counted after `document.click` returned, the engine path counts it from the request). One `paste` event, one `insertText`, `method: "paste"`, no `beforeinput`, in every arm. **The bound holds; the candidate is not frozen here (the main session freezes v68).**

---

# Second pass (task 2026-10-14h, fable on the owner's behalf; append-only from here)

## Why there is a second pass

The first pass above was witnessed by 129-B before the v68 freeze (`findings/evidence/link-batch/v68-witness/README.md`) and came back red, with two defects: (1) `s3`'s six cells in both browsers toasted `定位游標：INVALID_ARGUMENT：editorPlaceCaretV2 requires non-negative integer twips` and left the range selected -- the page sends `caret.y + caret.height / 2`, a half-integer on a 277-twip line (`web/e2-editor-app.js:1821`, `:2787`), and the worker refuses non-integers (`sdk/sdk-worker.js:1552–1559`); (2) every other click's 「定位游標」 went from 26–32 ms on v67 to 253–268 ms. The main session read both from source; this pass confirmed them by probe and by reading before building on them (`second-pass/README.md` §1–2). The engine's place-caret completes on the visible-cursor callback alone (`handleEditorPlaceCaret`: `requiredCallback = LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`). A click that collapses a range at the caret's own point moves no caret and produces only a TEXT_SELECTION callback -- visible in the engine's answer as the sequence advancing (35 → 36) with the selection already collapsed -- so the engine answers at its 250 ms readback deadline: `verified-caret-readback` at 251.4 ms, measured on the first-pass bytes in Chrome; a click that moves the caret is answered on the callback at 24.1 ms; the identical-point click at 250.6 ms with nothing in between (37 → 37). Two more facts from the source: the page clicks before an arrow key only when the selection shape is not `collapsed` (`web/e2-editor-app.js:2704–2708`), so every one of 129-B's clicks is made on an open range; and while the engine's place-caret is pending, the next callback-correlated operation -- the key `moveFromPoint` sends right after the click -- is answered BUSY (`probe_engine.cpp:5452`), which rules out "return early and let the engine finish" on this side.

## The bound for C1, written before the run (in the task brief)

Page-middle and 25 %-down clicks on a new blank document: no toast, the paste's `insertText` sent within 1,500 ms of the click, in both browsers, on v19 and v20; first-line arms unchanged from the first pass's witness. Default if never met: v68 is not frozen, the host stays on 0.2.19 / shell v66, finding 140 stays open on shipped releases.

## Ruling (second pass): the selection the click is made on decides the path

- **A range is open** (`before.selection.collapsed === false`) → v67's polling path: `document.click`, `getState` every 5 ms, finding 138's predicate. A plain click on an open range always collapses it; the collapse is the click's own evidence, at the speed v67 had (26–32 ms in the 129-B reference rounds), and no engine operation is left pending in front of the key. `document.click` receives the point as the caller gave it, the half-integer included, exactly as v67 sent it: the worker's `click` case validates nothing and the export's `int` parameter truncates it toward zero at the wasm boundary (the WebAssembly JS API's ToInt32), and 129-B's reference rounds were made with those bytes on the wire. One exit is added to the loop so that the first pass's bound is not given back on this path: collapsed by the click and the caret stayed off the clicked line → `engine-answered-the-caret-stayed` after the grace (≈ 400 ms instead of 30 s). **Named limit**: a range open and a click core never processes (no evidence at all) keeps v67's 30 s timeout; no second click is posted to ask the engine. No instance of that shape is known in a text document.
- **The selection is collapsed** → the first pass's engine path, asked with `Math.round`ed twips (the worker's contract; the reopen path at `:1821` is the caller that reaches it with a half-integer). Answered on the cursor callback when the caret moves (24 ms), at the readback deadline when it cannot -- the blank page and the identical point: ≈ 405 ms with the grace, which v67's identical-point click already paid. The engine path's "moved off the line" verdict now requires the caret to have moved; selection-only evidence with the caret staying is "stayed".
- **Not chosen**: polling first with the engine as the rescue after an unconverged grace (the handoff's first direction). The first pass's tests, kept unchanged by this task, pin that when the engine answers it posted the click itself (`documentClick === 0`), and the rescue would be a second mouse click the first did not need. (The brief's cost "core may read the second click as a double click" is refuted by reading: VCL's LOK path `ImplLOKHandleMouseEvent` takes the count as given, `mnClickCount = nClicks`, no double click from timing; both core trees.) **Not made**: an engine change; it needs a link and is recommended below.

Tests (`second-pass/README.md` §4; outputs there): `editor-shell-v2/tests/place-caret-second-pass.test.mjs`, seven cases, **5 of 7 red** on the first-pass bytes (`fc5ac883…`), **7/7** on the candidate (`f47c80ec…`); `place-caret-blank-page.test.mjs` (13) and `place-caret-acknowledgement.test.mjs` (17) unchanged and green; the whole `editor-shell-v2` suite **352/352** (345 before the new file); `check_e1_c_bundle_intact.py` `"intact": true` before and after. Touched: `narrow-editor-v2-session.js` (`placeCaret`), a comment in `narrow-editor-v2-client.d.ts` and `paragraph-editor-client.d.ts`, the new test file. The client `.js` files are the first pass's (`aaceb555…`, `38a46f4b…`); the page is unchanged (`7815e16c…`); `editor-shell/`, `web/`, `sdk/`, `src/`, the Makefile, the profiles, the host: untouched. §34.4: no probe or check was changed; repaired because of execution 0, because of review 0.

## Witness (C1, after the bound above; `tables.py` output filtered to these runs)

v19 = `dist/` after `make e2-c-assets` (one `cp` line, the session file; `make -n` checked first). v20 = `build/paste-repro/mirror-v20-cand2`, a dist mirror carrying the page `build_cutover_page.py --profile e2-editor-v20 --out …` produced (`53019168…`, the same page as the first pass's v20 witness; no `--write`). Chrome 151.0.7922.169, Firefox 157.0.1, one browser job at a time, each run preflighted by the probe.

| report | mode | browser | arm (lines/chars/CJK) | click (ms before key) | click resolved (ms after click) | paste event | insertText sent | engine insert | getState | pill ready | last blit | getState polls before insert | autosave PUT answered | saved paragraphs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `nohost-dist-chrome-below-first-line-cand2-v19-2026-10-14T084606Z.json` | nohost/dist | chrome | owner (40/577/389) | below-first-line (1,411.8) | 408.0 (定位游標 407 ms) | 0.6 | 2.2 | 14.6 | 1.0 | 17.7 | 205.9 | 29 | – | – |
| `nohost-dist-chrome-first-line-cand2-v19-2026-10-14T084622Z.json` | nohost/dist | chrome | owner (40/577/389) | first-line (waited) | 定位游標 405 ms | 0.4 | 1.9 | 17.6 | 1.1 | 20.4 | 214.1 | 0 | – | – |
| `nohost-dist-chrome-page-middle-cand2-v19-2026-10-14T084551Z.json` | nohost/dist | chrome | owner (40/577/389) | page-middle (1,413.8) | 404.8 (定位游標 404 ms) | 0.4 | 1.5 | 16.5 | 0.7 | 18.7 | 210.4 | 28 | – | – |
| `nohost-dist-firefox-below-first-line-cand2-v19-2026-10-14T084702Z.json` | nohost/dist | firefox | owner (40/577/389) | below-first-line (1,330.6) | 408.9 (定位游標 404 ms) | 0.3 | 1.6 | 8.8 | 1.0 | 11.4 | 189.0 | 27 | – | – |
| `nohost-dist-firefox-first-line-cand2-v19-2026-10-14T084726Z.json` | nohost/dist | firefox | owner (40/577/389) | first-line (waited) | 定位游標 405 ms | 0.3 | 1.6 | 8.8 | 1.2 | 11.5 | 191.6 | 0 | – | – |
| `nohost-dist-firefox-page-middle-cand2-v19-2026-10-14T084638Z.json` | nohost/dist | firefox | owner (40/577/389) | page-middle (1,331.2) | 409.7 (定位游標 404 ms) | 0.2 | 1.6 | 8.8 | 1.1 | 11.4 | 176.1 | 27 | – | – |
| `nohost-dir-mirror-v20-cand2-chrome-below-first-line-cand2-v20-2026-10-14T084814Z.json` | nohost/dir | chrome | owner (40/577/389) | below-first-line (1,412.9) | 407.8 (定位游標 407 ms) | 0.6 | 2.0 | 17.9 | 1.1 | 20.9 | 214.0 | 29 | – | – |
| `nohost-dir-mirror-v20-cand2-chrome-first-line-cand2-v20-2026-10-14T084830Z.json` | nohost/dir | chrome | owner (40/577/389) | first-line (waited) | 定位游標 407 ms | 0.3 | 1.6 | 14.9 | 2.7 | 19.2 | 204.2 | 0 | – | – |
| `nohost-dir-mirror-v20-cand2-chrome-page-middle-cand2-v20-2026-10-14T084759Z.json` | nohost/dir | chrome | owner (40/577/389) | page-middle (1,412.3) | 407.6 (定位游標 407 ms) | 0.5 | 2.1 | 15.8 | 1.1 | 19.0 | 224.8 | 29 | – | – |
| `nohost-dir-mirror-v20-cand2-firefox-below-first-line-cand2-v20-2026-10-14T084909Z.json` | nohost/dir | firefox | owner (40/577/389) | below-first-line (1,330.2) | 412.7 (定位游標 407 ms) | 0.3 | 1.4 | 9.2 | 1.2 | 11.8 | 220.8 | 28 | – | – |
| `nohost-dir-mirror-v20-cand2-firefox-first-line-cand2-v20-2026-10-14T084933Z.json` | nohost/dir | firefox | owner (40/577/389) | first-line (waited) | 定位游標 403 ms | 0.3 | 1.3 | 7.5 | 1.1 | 9.7 | 204.3 | 0 | – | – |
| `nohost-dir-mirror-v20-cand2-firefox-page-middle-cand2-v20-2026-10-14T084846Z.json` | nohost/dir | firefox | owner (40/577/389) | page-middle (1,329.6) | 411.9 (定位游標 406 ms) | 0.2 | 1.2 | 9.0 | 1.0 | 11.1 | 209.5 | 28 | – | – |

| report | profile | page | shell session | preflight (KWallet / chrome / other runners) |
| --- | --- | --- | --- | --- |
| `nohost-dist-chrome-page-middle-cand2-v19-…T084551Z` | e2-editor-v19 | `7815e16c…` | `f47c80ec…` | b false / 34 / [] |
| `nohost-dist-chrome-below-first-line-cand2-v19-…T084606Z` | e2-editor-v19 | `7815e16c…` | `f47c80ec…` | b false / 34 / [] |
| `nohost-dist-chrome-first-line-cand2-v19-…T084622Z` | e2-editor-v19 | `7815e16c…` | `f47c80ec…` | b false / 37 / [] |
| `nohost-dist-firefox-page-middle-cand2-v19-…T084638Z` | e2-editor-v19 | `7815e16c…` | `f47c80ec…` | b false / 37 / [] |
| `nohost-dist-firefox-below-first-line-cand2-v19-…T084702Z` | e2-editor-v19 | `7815e16c…` | `f47c80ec…` | b false / 39 / [] |
| `nohost-dist-firefox-first-line-cand2-v19-…T084726Z` | e2-editor-v19 | `7815e16c…` | `f47c80ec…` | b false / 38 / [] |
| `nohost-dir-mirror-v20-cand2-chrome-page-middle-cand2-v20-…T084759Z` | e2-editor-v20 | `53019168…` | `f47c80ec…` | b false / 33 / [] |
| `nohost-dir-mirror-v20-cand2-chrome-below-first-line-cand2-v20-…T084814Z` | e2-editor-v20 | `53019168…` | `f47c80ec…` | b false / 37 / [] |
| `nohost-dir-mirror-v20-cand2-chrome-first-line-cand2-v20-…T084830Z` | e2-editor-v20 | `53019168…` | `f47c80ec…` | b false / 37 / [] |
| `nohost-dir-mirror-v20-cand2-firefox-page-middle-cand2-v20-…T084846Z` | e2-editor-v20 | `53019168…` | `f47c80ec…` | b false / 33 / [] |
| `nohost-dir-mirror-v20-cand2-firefox-below-first-line-cand2-v20-…T084909Z` | e2-editor-v20 | `53019168…` | `f47c80ec…` | b false / 35 / [] |
| `nohost-dir-mirror-v20-cand2-firefox-first-line-cand2-v20-…T084933Z` | e2-editor-v20 | `53019168…` | `f47c80ec…` | b false / 31 / [] |

**Against the bound**: every `page-middle` and `below-first-line` arm resolved the click at **404.8–412.7 ms after the click** (「定位游標 404–407 ms」, 27–29 `getState` re-reads), no error toast in any arm (the only toast in every report is 「已開啟 新文件.odt」), the paste's `insertText` sent **1.2–2.2 ms after its `paste` event** (1,331–1,416 ms after the click, inside the stated 1,500 ms), engine insert 7.5–17.9 ms, `revision` 0 → 1 in every arm (the paste landed), one `paste` event and no `beforeinput`. The `first-line` arms: 「定位游標 403–407 ms」, 0 polls, `insertText` 1.3–1.9 ms after the paste event -- unchanged from the first pass's witness (405–408 ms). Both browsers, both profiles. **The bound holds.** Not run here: C2 (129-B, a separate task); the bytes for it are in `dist/` (session `f47c80ec…`, page `7815e16c…`). Nothing frozen, nothing linked, no host change. `leak_check.py`: `hits {}` over the 45 files of this folder with the new reports in it.

## For the next link batch (recommended, not made)

`handleEditorPlaceCaret` arms `requiredCallback = LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`. The collapse click's TEXT_SELECTION callback arrives, is counted into the state, and does not complete the operation (the probe's arm B: sequence 35 → 36 inside the wait, the answer only at the deadline). Completing the caret operation on `EditorCaretOrSelectionCallback` (visible cursor or text selection), as `completePendingEditorOperation` already does for the operations that arm it, would answer the collapse click on its callback (tens of ms) and let the engine path serve open-range clicks too -- one path instead of two. The open-range rule above keeps 129-B at v67's speed without that link and does not depend on it.
