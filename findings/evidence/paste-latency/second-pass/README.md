# Finding 140, second pass (task 2026-10-14h): what the engine answers, and the fix's red-first tests

Task: `handoff/tasks/TASK-2026-10-14h-finding-140-second-pass.md`. Executor: fable, deciding on the owner's behalf. Facts here are measured unless marked otherwise. Times are UTC. Nothing under `web/`, `editor-shell/`, `sdk/`, `src/`, the `Makefile`, `dist/profiles/*`, any check or judge, or the host was edited; no shell generation was frozen; no `--write` mode was run; the only `make` was `e2-c-assets` (one `cp` line, the session file).

## 1. The confirmation probe: what `editorPlaceCaretV2` answers for the product's three clicks

The red 129-B witness (`findings/evidence/link-batch/v68-witness/`) measured the page's 「定位游標」 at 253–268 ms on the first-pass bytes and *inferred* that the engine answered at its 250 ms readback deadline, because `completion` was not in the arms' records. `probe_140_completion.py` (this folder; it was run from the session scratchpad, this is the as-run copy) records the `editorPlaceCaretV2` request/reply pair at the Worker boundary -- `completion`, the round trip, the caret and selection in the answer, `callbackSequenceBefore/After` -- on the first-pass bytes, for the three clicks the product makes. Chrome only; the 129-B numbers were the same shape in both browsers.

Identity (`completion-red-chrome.json`): page `7815e16c…` (v19, `dist/`), session `fc5ac883…` (the first pass), client `aaceb555…`, profile `e2-editor-v19`, document `arrow-selection-shapes.odt` (`883c48c0…`, the 129 fixture), Chrome 151.0.7922.169. The page is a `pp.build_mirror` of `dist/` with the 129 probe's one appended line (`globalThis.__m4`), served by `web/serve.py`; no dist byte changed. Preflight 08:37:23Z: KWallet `b false`, other runners `[]`, `pgrep -c chrome` 37 (the owner's desktop browser).

| arm | what the product does | engine round trip | `completion` | sequence before → after | page 「定位游標」 |
|---|---|---|---|---|---|
| A | a click that moves the caret (x 1418 → 4369 on the first line), selection collapsed before | **24.1 ms** | `documented-callback-visible-cursor` | 2 → 3 | 26 ms |
| B | a real Left key while a drag range is open (`pha bravo `, `range-single`): `moveFromPoint` clicks at the caret end's own point (x 2917, y 1418 + 276/2) to collapse it | **251.4 ms** | `verified-caret-readback` | 35 → 36, selection already `collapsed: true` in the answer | 254 ms, then 「◀ 41 ms」 for the key (keydown → move done 300.7 ms) |
| C | a click on the caret's own point, selection collapsed (056's identical-point click) | **250.6 ms** | `verified-caret-readback` | 37 → 37 | 403 ms (the readback plus the session's grace to 400) |

Reading. The engine's place-caret completes on `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` only (`src/probe_engine.cpp` `handleEditorPlaceCaret`: `requiredCallback = LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`; `completePendingEditorOperation` matches that type alone for a caret operation; `parseEditorRectangle` returns true on any well-formed payload, so an unchanged rectangle would still complete it). Arm A gets that callback and is answered in 24 ms. Arm B gets no visible-cursor callback: the click collapses the range at the caret's own point, the caret rectangle does not change, and what core emits is `TEXT_SELECTION` -- visible in the answer as the sequence advancing by one and the selection already collapsed -- which the engine counts into its state but does not complete the operation on. The answer comes at the deadline. Arm C gets nothing at all (37 → 37) and is answered at the deadline too, as 056 measured. So the brief's claim 2 is **confirmed and sharpened**: the 254 ms is the deadline, and the callback that *does* arrive for the collapse click is the selection one.

The v67 polling path (`document.click` + `editorGetStateV2` every 5 ms) saw arm B's selection collapse as finding 138's evidence at 26–32 ms in the 129-B reference rounds; the first pass awaited the engine's answer instead. Returning early while the engine's place-caret is still pending is not an option on this side: the engine holds `gEditorPending` until it answers, and the next callback-correlated operation -- the arrow key `moveFromPoint` sends right after the click -- is answered `BUSY` (`probe_engine.cpp:5452`).

## 2. The brief's claims, checked against source and probe

| claim (brief) | status |
|---|---|
| the half-integer y comes from `caret.y + caret.height / 2` at `web/e2-editor-app.js:1821` (reopen) and `:2787` (`moveFromPoint`); the pointerdown path rounds (`pointToTwips`, `:1686`) | confirmed by reading |
| the worker refuses non-integers with INVALID_ARGUMENT (`sdk/sdk-worker.js:1552–1559`) and the first pass's `PLACE_CARET_FALLBACK_CODES` does not include it | confirmed by reading |
| v67's `click` path truncated the half-integer toward zero | confirmed by reading: the worker's `click` case validates nothing and `ccall`s `oxsdk_document_click` with `"number"` arguments; the export's parameters are `int` (`Command.values[6]` is `int`), and the WebAssembly JS API converts a Number to `i32` with ToInt32 -- truncation toward zero |
| the engine answers the collapse click at its 250 ms deadline because no visible-cursor callback arrives | confirmed by probe (arm B, above), and the callback that does arrive is TEXT_SELECTION |
| a second mouse click at the same point after v67's `document.click` may be read by core as a double click | **refuted by reading**: VCL's LOK path `ImplLOKHandleMouseEvent` (`vcl/source/window/winproc.cxx`, same in `libreoffice-26-2` and `native-lok-26-8`) takes the click count as given -- `pFrameData->mnClickCount = nClicks` -- and both engine handlers pass `1`; no double click is synthesised from timing there. (The design below posts no second click anyway.) |
| while the engine's place-caret is pending the next callback-correlated operation gets BUSY | confirmed by reading (`handleEditorAction`, `probe_engine.cpp:5452`); it is what rules out "return early, let the engine finish" |
| `moveFromPoint` is the path 129-B's click takes | confirmed by reading, with one more fact: the page calls it only when the selection shape is not `collapsed` (`web/e2-editor-app.js:2704–2708`), so every click-before-a-key is made on an open range |

## 3. The second pass (the design; the ruling text is in `../README.md`, appended)

The path a click takes is decided by the selection it is made on, read in the `before` state the session already takes:

- **range open** (`before.selection.collapsed === false`) → v67's polling path. A plain click on an open range always collapses it; that collapse is the click's own evidence under 138's predicate, at the speed v67 had, and no engine operation is left pending in front of the key. `document.click` receives the point as the caller gave it (the bytes 129-B's reference rounds were made with). The polling loop gains one exit so the first pass's bound is not given back there: collapsed by the click and the caret stayed off the clicked line → `engine-answered-the-caret-stayed` after the grace. Named limit: a range open and a click core never processes keeps v67's 30 s timeout; no second click is posted. No instance of that shape is known in a text document.
- **selection collapsed** → the engine path of the first pass, asked with **`Math.round`ed twips**. Answered on the cursor callback when the caret moves (arm A: 24 ms), at the readback deadline when it cannot (the blank page, the identical point: 400 ms with the grace, as v67's identical-point click already paid). The engine path's "moved off the line" verdict now requires the caret to have moved; selection-only evidence with the caret staying is "stayed".

Touched: `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js` (`placeCaret`), the two client `.d.ts` files (a comment: integer twips), the new test file. Not touched: the client `.js` files (`aaceb555…`, `38a46f4b…` as in the first pass), `editor-shell/`, `web/`, `sdk/`, `src/`.

## 4. Tests, red first

`wasm_sdk_probe/editor-shell-v2/tests/place-caret-second-pass.test.mjs`, seven cases against a scripted engine that refuses non-integer twips as the worker does, answers on the cursor callback only when the caret rectangle changes (else at 250 ms), and reports whether its place-caret is still pending when the session returns.

- `second-pass-red-on-fc5ac883.txt`: on the first-pass bytes **5 of 7 red** -- both defect-1 cases (INVALID_ARGUMENT), the defect-2 case (returned at ≈ 291 ms, after the deadline), the open-range margin click (took the engine path), the named limit (the engine path accepted it); the two controls (a moving click on a collapsed selection; the blank-page click) green.
- `second-pass-green-on-f47c80ec.txt`: on the candidate **7/7**; `place-caret-blank-page.test.mjs` and `place-caret-acknowledgement.test.mjs` unchanged (git-clean) and **30/30**; the whole `editor-shell-v2` suite **352/352** (345 before this file; `editor-shell/tests` + `editor-shell-v2/tests` together 417 -- the handoff's "425" is not reproducible from either glob with node 24.16 and is reported as measured here); `check_e1_c_bundle_intact.py` `"intact": true` before and after (bundle `187706b2dcb07d2b`, 5 files, `problems: []`).

## 5. Files

| file | what |
|---|---|
| `probe_140_completion.py` | the confirmation probe, as run (`37b74bed…`) |
| `completion-red-chrome.json` | its report on the first-pass bytes (`81037c62…`) |
| `second-pass-red-on-fc5ac883.txt` | the new test file on the first-pass bytes |
| `second-pass-green-on-f47c80ec.txt` | the new test file, the two protected files, the whole suite and the E1-C check on the candidate |

## 6. C1 (the browser witness), run after everything above

Bound, from the task brief (written before any run): page-middle and 25 %-down clicks on a new blank document, no toast, the paste's `insertText` sent within 1,500 ms of the click, both browsers, v19 and v20; first-line arms unchanged from the first pass's witness.

Twelve `probe_paste_latency.py --mode nohost --arms owner` runs, one browser job at a time, each preflighted by the probe (KWallet `b false`, other runners `[]`, `pgrep -c chrome` 31–39, the owner's desktop browser): v19 = `dist/` after `make e2-c-assets` (one `cp`, the session file; page `7815e16c…`, session `f47c80ec…`); v20 = `build/paste-repro/mirror-v20-cand2`, a `pp.build_mirror` of `dist/` carrying the page `build_cutover_page.py --profile e2-editor-v20 --out …` produced (`53019168…`, the same page the first pass's v20 witness used; no `--write`). Reports: `../raw/nohost-dist-*-cand2-v19-*.json` and `../raw/nohost-dir-mirror-v20-cand2-*-cand2-v20-*.json`; the phase table is in `../README.md` (Second pass → Witness).

Result: every `page-middle` and `below-first-line` arm resolved the click at **404.8–412.7 ms after the click** (「定位游標 404–407 ms」, 27–29 re-reads), no error toast in any arm (the only toast is 「已開啟 新文件.odt」), `insertText` sent 1.2–2.2 ms after its `paste` event, `revision` 0 → 1 in every arm; `first-line` arms 「定位游標 403–407 ms」 with 0 polls, as in the first pass. **The bound holds.** C2 (129-B) was not run here; the bytes for it are in `dist/`.
