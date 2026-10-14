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
