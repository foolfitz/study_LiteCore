# Facts for the next link batch: caret placement, document-boundary answer, Ctrl+Home/End

Gathered 2026-10-16, read-only, against `main` at `338b8ddb` (page `web/e2-editor-app.js` = `dist/e2-editor-app.js` = `901dd6a6…`, shell v73, shipped engine profile `e2-editor-v20`, wasm `313b08d5…`, worker `478d0da1…`).

Paths are repo-relative to `/home/jiajun/LibreOffice/study_LiteCore/`; `wsp/` = `wasm_sdk_probe/`.

Tags:
- **[SRC]**: read in source code at the cited lines.
- **[DOC]**: stated in a finding, spec, handoff or evidence README. The claim is the doc's, not re-verified unless noted.
- **[INF]**: my inference. Not measured, not stated anywhere.
- **[MINE]**: my own tally over committed raw evidence, using read-only Python. Nothing was run in a browser and nothing was built.

---

## ITEM 1: `handleEditorPlaceCaret` also completes on `TEXT_SELECTION` (finding 140, second pass)

### (a) Origin

- Finding 140, second ruling (fable for the owner, 2026-10-14). `findings/140-a-click-below-the-first-line-of-a-blank-document-holds-the-queue-for-30-seconds.md:63-80`. The decisive sentence is at :73. It names the engine change and defers it:
  > 「沒做引擎改動（讓 TEXT_SELECTION 也能完成 place-caret）——要連結，列為下批連結的建議，見 `findings/evidence/paste-latency/README.md` 最後一節。」 [DOC]

  The same file's revision log at :86:
  > 「下批連結的建議（引擎的 place-caret 也收 `TEXT_SELECTION`）照第二輪裁決，未做。」 [DOC]
- The recommendation text, `findings/evidence/paste-latency/README.md:221-223` [DOC]:
  > "`handleEditorPlaceCaret` arms `requiredCallback = LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`. The collapse click's TEXT_SELECTION callback arrives, is counted into the state, and does not complete the operation (the probe's arm B: sequence 35 → 36 inside the wait, the answer only at the deadline). Completing the caret operation on `EditorCaretOrSelectionCallback` (visible cursor or text selection), as `completePendingEditorOperation` already does for the operations that arm it, would answer the collapse click on its callback (tens of ms) and let the engine path serve open-range clicks too -- one path instead of two. The open-range rule above keeps 129-B at v67's speed without that link and does not depend on it."
- The task brief permitted recommending it but not making it. `handoff/tasks/TASK-2026-10-14h-finding-140-second-pass.md:26` [DOC]:
  > "An engine change (e.g. completing on `TEXT_SELECTION` as well) needs a link. If you think it belongs in the next link batch, say so; do not make it."
- The handoffs carry it as a batch item:
  - `handoff/HANDOFF-2026-10-14b-v68-v69-frozen-v20-cut-over-host-0.2.20.md:28`: "For the next link batch: complete `handleEditorPlaceCaret` on `TEXT_SELECTION` as well." Also :92 and :182 [DOC].
  - `handoff/HANDOFF-2026-10-16-0.2.24-count-holds-release-text-revised-makefile-a.md:101` [DOC].

### (b) Current behaviour

**Engine** (`wsp/src/probe_engine.cpp`):
- `handleEditorPlaceCaret` [SRC]:
  - :5890-5935. It is BUSY if a selection or format barrier is active, or if `gEditorPending` is held (:5893-5911).
  - It arms `gEditorPending.requiredCallback = LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` (:5916), with `caret = true` (:5919).
  - It always arms the readback deadline `EditorPlaceCaretDeadlineMs = 250` (:5924-5927, constant at :455).
  - It posts MOUSEBUTTONDOWN and MOUSEBUTTONUP with count 1 (:5929-5934).
- `completePendingEditorOperation` [SRC]:
  - :2191-2257. It matches the exact `requiredCallback`, or `EditorCaretOrSelectionCallback` (= -2, :1095), which accepts VISIBLE_CURSOR or TEXT_SELECTION (:2192-2197).
  - For `caret` it emits `editor-caret-placed` with `completion: "documented-callback-<type>"`; a TEXT_SELECTION gives `documented-callback-text-selection` (:2217-2249).
- `completePendingEditorOperation` is called on the LOK callback thread after every typed state callback has updated the cache and pushed an `editor-state` event (:2696-2703) [SRC].
- The deadline path is `completePendingEditorSelectByReadback` → `verified-caret-readback` (:2268-2298, name at :2288). The engine loop synthesises it at :6258-6276 [SRC].
- While place-caret is pending, any `editor-action` is BUSY (:5452-5456) [SRC].

**Worker**:
- `editorPlaceCaretV2` requires non-negative integer twips, else INVALID_ARGUMENT (`wsp/sdk/sdk-worker.js:1552-1568`) [SRC].
- The `editor-caret-placed` event is forwarded whole, with `completion` and the projected state; the completion is not validated (:979-989) [SRC].

**Client**: `ParagraphEditorClient.placeCaret` passes the call through and validates nothing about `completion` (`wsp/editor-shell-v2/paragraph-editor-client.js:193-199`) [SRC].

**Session** (`wsp/editor-shell-v2/narrow-editor-v2-session.js`), `placeCaret` at :694-789 [SRC]:
- `rangeOpen = before.selection.collapsed === false` (:723).
  - Range open → v67 polling path: `document.click`, then `getState` every 5 ms, with finding 138's predicate (:757-788).
  - Collapsed → engine path with `Math.round`ed twips (:725-755).
- The fallback codes are BUSY and UNSUPPORTED_OPERATION (:44).
- Judge (:702-710): `acknowledged = sequenceAdvanced && (caretMoved || selectionChanged)`.
  - On the engine path, an off-line verdict requires `caretMoved` (:751-753).
  - The grace is 400 ms (:697).
  - The returned `state` becomes the drain's state (`wsp/editor-shell/editor-session.js:301-302`).

**Page** (`wsp/web/e2-editor-app.js`, page `901dd6a6…`) has three callers [SRC]:
- pointerdown (:2525), which rounds to integer twips via `pointToTwips` (stated in `findings/evidence/paste-latency/second-pass/README.md:25`; not re-read) [DOC];
- the reopen (:1966);
- `moveFromPoint` (:3068), which clicks at `caret.y + caret.height / 2`.

`moveFromPoint` is used only when the shape is not `collapsed` and the action's gestures do not include it (:2973-2979). So every click before a key is made on an open range and takes the polling path [SRC].

**Measured on WASM** (first-pass bytes, Chrome) [DOC; `findings/evidence/paste-latency/second-pass/README.md:11-17`]:

| arm | completion | round trip | sequence |
|---|---|---|---|
| A: moving click on a collapsed selection | `documented-callback-visible-cursor` | 24.1 ms | 2→3 |
| B: collapse click at the caret's own point, range open | `verified-caret-readback` | 251.4 ms | 35→36: one callback arrived, and it was TEXT_SELECTION |
| C: identical-point click, collapsed | `verified-caret-readback` | 250.6 ms | 37→37 |

The blank-page clicks resolve at 404.8-412.7 ms: the 250 ms deadline plus the session's 400 ms grace (`findings/evidence/paste-latency/README.md:219`) [DOC].

**Native callback order for clicks on a selection** [MINE, from `findings/evidence/129/native/*/arms-r*.jsonl`, field `callbacksAfterClick`, 306 records]:
- 252 clicks at the caret's own rectangle (`emu` 216 + `click-only` 36) produce **TEXT_SELECTION only**.
- 54 clicks that move the caret (`emuend`) produce **TEXT_SELECTION first, then INVALIDATE_VISIBLE_CURSOR**, in 54 of 54.

The README states the same counts without the order: `findings/evidence/129/README.md:131,133` [DOC]. Native key cells agree that the cursor callback is always last (98/98, `specs/SPEC-M3-link-batch.md:107`) [DOC].

### (c) Decided vs open

Decided [DOC]:
- The engine change is recommended for the next link batch, and the batch list includes it.
- The session's two-path rule stands without it (the paste-latency README at :223).
- Integer twips are the worker's contract (:1552).

Open; a spec must settle these:
1. **Which completion rule.**
   - The literal recommendation completes on the *first* TEXT_SELECTION. In the 54/54 native moving-click cases that TEXT_SELECTION precedes the cursor callback [MINE]. The reply would therefore serialise the **pre-click caret**. This is the defect §9 found for moves on a range ("a completion on the first TEXT_SELECTION would put the pre-key caret in the reply", `specs/SPEC-M3-link-batch.md:113`; `wsp/src/extend_completion.hpp:29-31`) [DOC].
   - Through the session's judge that stale state gives `acknowledged` (the selection changed) with `caretMoved = false`. A click on another line then returns `engine-answered-the-caret-stayed`, `caretOnClickedLine: false`, and the drain stores the stale state until the next push with a higher `sourceSequence` converges [INF from :702-753 and editor-session.js:301].
   - Rule (a) of §10.1 avoids the stale reply: a TEXT_SELECTION that differs from the dispatch cache, then the next cursor callback (`specs/SPEC-M3-link-batch.md:134-139`; pure function in `wsp/src/extend_completion.hpp`, wired into nothing per :11-13 and :70-71). But it gains nothing for the 252/306 own-point collapse clicks, because no cursor callback follows [INF].
   - So the spec must choose. One option: complete on TEXT_SELECTION only when the click point lies on the cached caret's line [INF]. Another: complete on TEXT_SELECTION and accept the stale-reply limit.
2. **Whether the session changes too.** The engine change alone does not change the shipped product's latency [INF]:
   - Open-range clicks take the polling path (:723), which never calls the engine's place-caret.
   - Collapsed clicks get no TEXT_SELECTION. An empty-to-empty selection is deduplicated by LOK (F1, `specs/SPEC-M3-link-batch.md:127`).
   - The benefit ("one path instead of two") needs a session change that routes open-range clicks to the engine path. That means a new shell generation, and the second-pass tests that pin today's routing would have to be revised.
3. **The blank-page click is not touched** [INF]. It produces no callback at all (C1: `verified-caret-readback`, 27-29 re-reads), so it keeps the ≈405 ms (250 ms deadline + 400 ms grace). If that cost is wanted down, it is a separate question: the grace and the deadline.
4. **Prior-flush interaction**, the class named L-extend-prior-flush (`specs/SPEC-M3-link-batch.md:145-148`) [DOC]:
   - Completing on TEXT_SELECTION frees `gEditorPending` before the same flush's cursor callback is processed.
   - The next key (`moveFromPoint` sends one right after the click) arms `EditorCaretOrSelectionCallback` (:5706-5708) and could be completed by the click's late cursor callback if a stall separates them [INF].
   - The native gap within one flush is about 1 ms (`specs/SPEC-M3-link-batch.md:109` for keys) [DOC].
5. **`completion` vocabulary.** `documented-callback-text-selection` would be new for `editor-caret-placed`. No client validates it today [SRC above]. Any judge or probe that keys on `documented-callback-visible-cursor` would need checking; `probe_140_completion.py` records it.

### (d) Layers changed

- **Engine C++** [SRC/INF]: about one line at `probe_engine.cpp:5916` (or a rule function). This needs a relink, hence a new profile identity.
- **ABI**: unchanged.
- **Worker**: unchanged.
- **Session**: changes only if open-range routing moves (item 1(c)2). That means a new shell generation, because the bundle scope covers `editor-shell-v2`, `sdk`, and so on (`wsp/tools/build_e2_c_shell_bundle.py:767-768`).
- **Page**: unchanged unless the session API changes.
- `editor-shell/` (E1-C bound) must not be touched; the override pattern already lives in `narrow-editor-v2-session.js` (:607-610) [SRC].

### (e) Tests, criteria, evidence

- **Unit tests**:
  - `wsp/editor-shell-v2/tests/place-caret-second-pass.test.mjs` (7). Its fake engine answers on the cursor callback only when the rectangle changes, otherwise at 250 ms (`findings/evidence/paste-latency/second-pass/README.md:44`). It would need a TEXT_SELECTION-completing variant.
  - `place-caret-blank-page.test.mjs` (13).
  - `place-caret-acknowledgement.test.mjs` (17, finding 138).
  - Known flake: "defect 2" returned at 24 ms against a `>= 25` bound (`place-caret-second-pass.test.mjs:170`; `handoff/HANDOFF-2026-10-15c-…md:57`) [DOC/SRC].
- **Probes**:
  - `findings/evidence/paste-latency/second-pass/probe_140_completion.py` records `completion` and the round trip per arm. Arm B is the direct witness: expected about 25 ms with `documented-callback-text-selection` instead of 251 ms.
  - `tools/probe_paste_latency.py`: C1, the blank page, should stay ≈405 ms.
  - 129-B (`probe_129_m4_wasm.py`): C2's latency clause, `定位游標` < 100 ms and median ≤ 40 ms (`TASK-…14h…md:38`). The reference medians are 27.5 ms (Chrome) and 29.1 ms (Firefox) (`findings/140…md:86`).
- **Native data to reuse** (no new native run needed for the callback order):
  - `findings/evidence/129/native/` (306 clicks, tallied above);
  - `findings/evidence/link-batch/extend-signatures/run-20261013T095104Z/` (key cells).

### (f) Interactions

- Item 3: on a range, `moveFromPoint` clicks before sending `move-document-start/end` if their gestures are `collapsed` only. Item 1's routing decides whether that click costs 26-32 ms (polling) or about 25 ms (engine path plus engine change) [INF].
- The new-document blank page is unaffected (item 1(c)3).
- Markdown paste queues behind the click exactly as the plain paste does (finding 140's original scenario) [INF].

---

## ITEM 2: an immediate engine answer at document start/end (C without the ~2.25 s window)

### (a) Origin

- **§10.5** (ruling 2, `specs/SPEC-M3-link-batch.md:173-184`) [DOC]:
  - The window: the first 250 ms NONE, then one more `MergeStepDeadlineMs` (2000 ms), then `verified-boundary-noop` with `boundaryNoop: { waitedMs }` (:175-178).
  - The named residual **L-C-late-K1** (:183):
    > 「這個殘留關不掉：在真正的文件兩端，K1 不產生任何回呼（原生 P-b），沒有訊號可等，只能靠時間窗。」
  - The named cost (:184):
    > 「在文件開頭按 Backspace，約 2.25 秒才回應。`waitedMs` 留作日後追加一節、以量測縮短的依據。窗長對 135 夠用：量到的停頓是 196.6–210 ms。」
- **§15.1** (ruling 6, :439-455) [DOC]:
  - Registers **L-C-number-or-indent**: three positions where K1 shows nothing to the barrier but Writer's own key changes the document (:441-446).
  - "Only the ordered-commands spec's candidate A can close it" (:447).
  - Does **not** adopt "refuse when the caret moved at expiry" (:448-451).
  - Corrects §10.5's cost: "Writer does nothing" holds only for an unnumbered, unindented first paragraph (:452).
- **Finding 141, ruling (3)** (`findings/141-a-held-backspace-at-a-c-boundary-queues-silent-no-ops.md:28`) [DOC]:
  > 「(3) 引擎端讓文件起訖直接回答（不等 2 秒窗）需要連結，留給下一批（§10.5 的 `waitedMs`）；本修法不排斥它，兩者疊加後第一下也不用等。」
- **Finding 144** (`findings/144-…md:28`) [DOC]:
  > 「具名殘留：在邊界按住（有標記）仍是每個 2.25 秒的窗一個 no-op…141 的「記住上一個 no-op」沒做，留給引擎端的直接回答（§10.5 `waitedMs`）。」
- **Release text** (`handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md`) [DOC]:
  - :156-158 (§3.4): the cost is about 2.25 s at the document start; "下一批連結要讓引擎對文件起訖直接回答".
  - :178 L-C-late-K1.
  - :179-183 L-C-number-or-indent.
  - :188 the held-key tail, at most one window.
  - :190 「引擎端讓文件起訖直接回答（不等 2 秒窗）在下一批連結；疊上去之後第一下也不用等（finding 141 裁決 (3)）。」
- **The original proposal** (`findings/evidence/host-0.2.20-hand-test/README.md:125`, option B) [DOC]:
  > "answer the boundary without waiting when the caret is at the document's start/end and the paragraph is neither numbered nor indented (`SwCursorShell::IsStartOfDoc()`/`IsEndOfDoc()` plus the §15.1 conditions), or shorten the 2,000 ms window from a measurement (§10.5 left `waitedMs` for this). This removes the 2.25 s for the first press too. Red test: C1's `waitedMs` ≤ a new bound at positions (i)/(ii) and unchanged at (iii)."

  The "(i)/(ii)/(iii)" in that red test are not defined in that README. The ambiguity is the doc's own.

### (b) Current behaviour

**Engine** (`wsp/src/probe_engine.cpp`), under `-DOXSDK_E2_V20_LINK_BATCH` [SRC]:
- `startSelectionBarrierDelete` (:4181-4247):
  - It requires a callback-confirmed collapsed caret with readSelection NONE (:4189-4197).
  - It sets the 250 ms `boundaryDeadline` (:4208-4210, re-set after the `.uno:Undo` P_start read at :4220-4224).
  - It records `caretBefore` (:4213-4215) and `startedAt` just before K1 (:4241).
  - It posts **K1 = Shift+Left/Right** as a key event (:4236-4246).
- The engine loop waits on `boundaryDeadline` (:6279-6298), then calls `rejectSelectionBarrierAtDeadline` (:4007-4080).
  - First NONE, with the typed selection collapsed: `boundaryNoopWindow = true` and the deadline moves `+MergeStepDeadlineMs` (2000, :579) (:4035-4041).
  - Second NONE: `finishSelectionBarrierBoundaryNoop` (:4042-4043), which emits `editor-action-completed`, `changed:false`, `completion:"verified-boundary-noop"`, and `boundaryNoop.waitedMs` measured from K1's post (:3543-3571).
- **What the no-op is verified against today**: readSelection NONE at +250 ms and again at +2250 ms, with the cached typed selection collapsed (:4020-4023, :4042). It is **not** verified that the caret is at the document start or end; "boundary" means "K1 selected nothing" [SRC]. Review 6 says so: "Nothing in that path asks whether K1 *did* anything. It only asks whether a selection exists." (`findings/evidence/link-batch/review/review-6-engine-code.md:15`) [DOC].
- The engine sees core only through the public LOK headers. The one internal-API translation unit, `wsp/src/a11y_tree_probe.cpp` (`-DLIBO_INTERNAL_ONLY`, `SfxViewShell::Current()`), is compiled only for the v5 a11y core (`wsp/Makefile:1629-1634`; header comment `probe_engine.cpp:45-56`) [SRC]. There is no `IsStartOfDoc` and no doc-start query anywhere in `wsp/src/` [SRC grep].
- **Synchronous LOK calls run before keys still queued in core**: "`setTextSelection RESET` 是同步的，會在佇列中的 K1 之前執行" (`specs/SPEC-M3-link-batch.md:180`) [DOC]. Also ".uno:Delete runs synchronously under the SolarMutex and jumps every posted key" (`wsp/src/extend_completion.hpp:56-57`) [DOC in a source comment].

**Native, review 6 §1.2** (`findings/evidence/link-batch/review/review-6-engine-code.md:21-27`; artifacts in `review-6-artifacts/native/k1probe.cpp`) [DOC]:

| case | K1 callbacks | Writer's own key |
|---|---|---|
| plain first paragraph at doc start (control) | none | unchanged |
| (i) Delete in front of a bullet label | one INVALIDATE_VISIBLE_CURSOR, no TEXT_SELECTION | `Number On/Off` |
| (ii) Backspace at doc start, first paragraph bulleted | none | `Number On/Off` |
| (iii) Backspace at doc start, first-line indent | none | `Apply attributes` |

Reading: (ii) and (iii) cannot be told apart from a true boundary by callbacks.

**Native extend signatures**: ten cells produce no callback at all, among them doc-start Shift+Left/Up/Home and doc-end Shift+Right/Down/End (`specs/SPEC-M3-link-batch.md:108`) [DOC].

**Client**: `_validateInherited` accepts `verified-boundary-noop` only with `changed === false` and an unchanged revision (`wsp/editor-shell-v2/narrow-editor-v2-client.js:304-324`) [SRC].

**Session**: on `verified-boundary-noop` with `changed === false` it calls `tools.completedUnchanged()` (`narrow-editor-v2-session.js:995-996`) [SRC].

**Page** (141/144 holding):
- `boundaryNoopStands` requires completion `verified-boundary-noop`, `changed:false`, an unchanged revision, and the same collapsed caret rectangle as at send (`wsp/web/e2-editor-app.js:2701-2709`).
- `holdsDelete` (:2712).
- `settleDelete` drops the held presses on a standing no-op (:2732-2745) [SRC].

**Measured**:
- 2,253 ms in the engine and 2,256 ms on the page, every time, both browsers (`findings/evidence/host-0.2.20-hand-test/README.md:63-71,87`) [DOC].
- C1 `waitedMs` 2252-2255 ms (release text :156) [DOC].
- Hold on 0.2.23: 2 requests, released 1.44-1.53 s after keyup, worst case 2.12-2.22 s (release text :188) [DOC].

### (c) Decided vs open

Decided [DOC]:
- It goes into the next link batch, it needs a link, and it is compatible with the page holding (141 (3)).
- L-C-number-or-indent stays a residual that only ordered-commands candidate A closes (§15.1).
- "Refuse when the caret moved" is rejected (§15.1).

Open:
1. **What the boundary answer is verified against.** Today it is "K1 selected nothing within 2.25 s". An immediate answer needs a different, positive signal. Candidates [INF unless marked]:
   - **A. Pre-check before K1** (e.g. doc start for Backspace, doc end for Delete). The public LOK API offers no such query [SRC above]. It would need an internal-API translation unit (precedent: `a11y_tree_probe.cpp`, not in the v20 product link) or a geometric heuristic. **Ordering hazard**: a synchronous check runs before keys still queued in core (§10.5 :180). That is the finding 137 premise (a move reported done by readback that core has not run). The check could answer "no-op" at a position the queued key is about to leave, and the delete would be lost silently. This does not damage the document. Today's K1 is posted behind those keys, so it is FIFO-ordered with them.
   - **B. A FIFO marker after K1**: a posted event that always produces a callback, so the engine knows K1 has run. This is the "有序指令" spec's candidate B (named at §15.1 :447) [DOC]. No such marker exists today: `postUnoCommand` jumps posted keys (extend_completion.hpp:56-57).
   - **C. Shorten the 2,000 ms window from a measurement**. This is what §10.5 left `waitedMs` for, and option B in the hand-test README. The bound is finding 135's stalls (196.6-210 ms, §10.5 :184). Trade-off: a shorter window widens **L-C-late-K1** exposure (a K1 later than the window leaves a selection that the next typed character replaces, :183).
   - **D. Remember a standing no-op** (finding 144's undone item): answer at once when the previous same-direction delete was `verified-boundary-noop` and no callback, revision change or press has happened since. This does not help the first press.
   - **E. Item 3 knowledge**: right after the engine's own `move-document-start/end` (no later callbacks), the engine knows where the caret is. This covers only the Ctrl+Home path [INF].
2. **L-C-number-or-indent positions (ii) and (iii).**
   - Under A, the pre-check must exclude a numbered or indented first paragraph, as option B proposed. Otherwise the immediate answer reports "nothing to do" faster where Writer would act. Today's answer is equally silent, only 2.25 s later.
   - Whether the engine can see "numbered/indented" through public LOK, and how, is unknown: the 056 fingerprint/a11y is empty on the shipped core (`findings/140…md:47`) [DOC].
   - Position (i), Delete in front of a label, is not at a document end at all.
3. **What happens to L-C-late-K1.** If K1 is not posted at all (A), it disappears for those presses. Under C it grows. The spec should restate the residual under the chosen design.
4. **Completion vocabulary.**
   - Keep `verified-boundary-noop` with a smaller `waitedMs`, perhaps plus a basis field. Then the client (:314-316), the session (:995), the page (`boundaryNoopStands` :2702), the merge runner's wasm-fragment keying (`wsp/tools/run_merge_wasm_shakedown.py:200-206`) and the production-UI keying (§17.3, `specs/SPEC-M3-link-batch.md:559`) all keep working unchanged.
   - Or mint a new completion. Then each of those consumers changes [SRC for the consumers; INF for the consequence].
5. **The positive control for Rbs/Rdel is lost.** §17.4 (`specs/SPEC-M3-link-batch.md:565-567`) makes the RESULT reader confirm a busy period of ≥ 2,000 ms with an unchanged `rev` for every counted Rbs/Rdel. That busy period is the only evidence that the boundary key reached the engine. An immediate answer removes that signature, so the count reading needs a new positive control, for example the engine's answer record in the timeline [INF from the cited text].

### (d) Layers changed

- **Engine C++**: the barrier path in `probe_engine.cpp` :4007-4080 and :4181-4247, under a new link define (precedent: `OXSDK_E2_V20_LINK_BATCH`, the only define site `wsp/Makefile:1551-1554`). Design A may add a new internal-API translation unit and a Makefile rule. This needs a relink, which mints a new profile identity [SRC/INF].
- **ABI**: unchanged if the completion stays as it is [INF].
- **Worker**: forwards `boundaryNoop` named fields only (`wsp/sdk/sdk-worker.js:225-230`). A new field needs a worker hunk, hence a new worker hash pin (`E2_V20_WORKER_SHA256` precedent, `wsp/Makefile:1546,1590`) [SRC].
- **Manifest**: see "a manifest field declaring C" under (f).
- **Shell and page**: no change if the completion is unchanged. The page holding (141/144) keeps working and simply drops held presses sooner [INF].

### (e) Tests, criteria, evidence

- **Engine model tests** (pure-header precedent): `tests/merge_key_undo_model_test.cpp`, `tests/extend_completion_model_test.cpp` (`handoff/RUNBOOK-relink-v20.md:57-59`).
- **C1**: `wsp/tools/judge_v20_shakedown.py`. It requires `waitedMsPresent` (:264, :392) and a fresh `selectionType == "none"` 500 ms after the answer. It sets no lower bound on `waitedMs` [SRC], so an immediate answer passes it as written; a new upper bound needs a new clause.
- **Page**:
  - `page-held-deletes.test.mjs` T1: the fake engine answers the no-op at 2,250 ms (`findings/141…md:35`). A fast-answer variant is needed.
  - `boundary-noop.test.mjs`, `page-boundary-noop.test.mjs` (client and page red cases).
- **Browser arms**:
  - `findings/evidence/host-0.2.20-hand-test/probe_10_14n.py`: `owner-sequence`, `double-press`, `hold-3s`, `burst-1s`. Today these read 2,256 / 4,513 / 6,768 / 40,605 ms on 0.2.20.
  - `findings/evidence/host-0.2.23-hold/probe_10_14q.py` (`hold-3s`, `hold-2300`).
  - The merge runner C29/C30 (`run_merge_wasm_shakedown.py:178-206`).
  - §10.7's held-into-refusal arms (`handoff/RUNBOOK-relink-v20.md:133`).
  - Production UI Rbs/Rdel (§17.3).
- **Native evidence to reuse**:
  - `findings/evidence/link-batch/review/review-6-artifacts/native/` (`k1probe.cpp`, `make_fixtures.py`, `out/`): the three L-C positions and the plain control.
  - `findings/evidence/link-batch/extend-signatures/` (the ten silent cells).
  - `wsp/tools/merge_native_boundaries.cpp`.
- **What would show it works**:
  - `waitedMs` (or the page's busy→ready time) for a single press at a plain doc start or end drops below a pre-written bound, both browsers.
  - The L-C positions behave as the spec decides.
  - A mid-text delete is unchanged (132-B: ≤ 2 characters after release).
  - The control arm "plain first paragraph" stays a no-op with the document unchanged.

### (f) Interactions

See also the cross-item table at the end.

- **A manifest field declaring C** (10-14b :29; `run_merge_wasm_shakedown.py:183-199`) [DOC/SRC]:
  - Neither the manifest nor the ABI declares C today. The tools key on the wasm string `,"completion":"verified-boundary-noop"`.
  - v20's manifest still says `boundaryRejectionRequiresFreshWorker: true` [SRC, read from `dist/profiles/e2-editor-v20/sdk-manifest.json`]. A grep finds that field consumed only by E1 and diagnostic pages and tests, not by the product page or shell [SRC grep].
  - If item 2 changes C's semantics, the new field should describe the new behaviour; deciding them together avoids declaring C twice [INF].
- **`Language=`** (finding 031: localized UI names) [INF]: the merge-key path reads `.uno:Undo` payloads, and the L-C native table quotes localized undo strings (`Number On/Off`, `Apply attributes`). An immediate-answer design must not key on Writer's strings, because those change with `Language=`.

---

## ITEM 3: finding 142, Ctrl+Home / Ctrl+End → `move-document-start` / `move-document-end`

### (a) Origin

- `findings/142-ctrl-home-does-not-move-the-caret.md` [DOC]:
  - Status: registered, not fixed (:5).
  - Location (:7) [DOC; the line has drifted, now `:2950`]:
    > 「`web/e2-editor-app.js:2679`：按鍵處理遇到 Ctrl／Cmd 組合鍵就 `return`，頁面不處理；隱藏的輸入 textarea 自己吃掉這個鍵，文件游標不動。引擎沒有「移到文件開頭／結尾」的動作。」
  - The fix direction (:15):
    > 「正解要引擎動作（`move-document-start`／`move-document-end`），進下一批連結；紅案＝`press-after-ctrl-home` 臂必須讀成邊界 no-op。連結之前的過渡選項（頁面攔下 Ctrl+Home／End 並提示「尚不支援」，或用既有動作組合模擬）未評估。」
- The proposal, `findings/evidence/host-0.2.20-hand-test/README.md:126` (option C) [DOC]:
  > "`move-document-start` / `move-document-end` actions (`.uno:GoToStartOfDoc`/`GoToEndOfDoc` through the existing move machinery) bound to Ctrl+Home/Ctrl+End in `KEY_ACTIONS`, with the accelerator check moved after the table. Red test: … after Ctrl+Home the engine's caret must be at the document start and the following Backspace a `verified-boundary-noop` (today: `verified-selection-delete`, revision 0 → 1). Until the link, the page-level honest step is to `preventDefault` Ctrl+Home/End with a toast …"
- The measurement: the `press-after-ctrl-home` arm gave `verified-selection-delete`, revision 0→1, one character of 「LD-PAGE-01」 deleted, caret x 2129→1951 (`…/host-0.2.20-hand-test/README.md:66,90`) [DOC].
- Release text §4.7 (`handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md:212-214`) [DOC].

### (b) Current behaviour

**Page** (`wsp/web/e2-editor-app.js`) [SRC]:
- `KEY_ACTIONS` maps ArrowLeft/Right/Up/Down and Home/End to the six moves (:2835-2842).
- In the keydown handler (:2844-2981), `accel = ctrlKey || metaKey` (:2846). Ctrl+Z, Ctrl+Shift+Z/Y, Ctrl+S, Ctrl+B/I/U and Enter are handled first (:2855-2949); then `if (accel) return;` (:2950) runs before the table lookup (:2951).
- The binding is gated by `session.offers(action)`, which follows the manifest (:2956; `narrow-editor-v2-client.js:211-218`). Shift+move is not taken (:2960).
- On a range whose shape the action's gestures do not include, the page calls `moveFromPoint`, which clicks then moves (:2973-2979, :3057-3075).
- `ACTION_LABELS` gives a label for button-less actions; the new actions need entries (:2177-2183).

**Engine moves** (`wsp/src/probe_engine.cpp`) [SRC]:
- The key path is in `handleEditorAction` (:5654-5743). For example `MOVE_LINE_HOME` → `Key::HOME` (:5668-5670).
- Select-all already uses `Key::A | EditorMod1Modifier` (:5674-5691; Mod1 = 0x2000 at :1094). It is "SHIPPED BUT WITHHELD… Its postcondition is NOT characterised".
- Moves complete on `EditorCaretOrSelectionCallback` (:5706-5708), with `mutation=false` (:5709) and the 250 ms `EditorMoveReadbackDeadlineMs` always armed (:5735-5738). A boundary press is answered `verified-move-readback` (:2336-2364).
- **No barrier or position check verifies a move.** Moves are judged only by the client postcondition: revision unchanged, `changed:false`, completion `documented-callback-*` or `verified-move-readback` (`narrow-editor-v2-client.js:122-124,297-303`).
- The UNO route `startEditorUnoAction` → `startUnoMutation` is the *mutation* route (:4520-4551). The select-all comment explains why a selection or caret change must not take it: "the uno-mutation route reports a mutation… would advance the revision for an edit that never happened -- finding 067's engine half" (:5675-5680).
- **The hand-test README's "`.uno:GoToStartOfDoc` through the existing move machinery" is internally inconsistent**: the move machinery is the key path [SRC + INF].

**Action tables and limits** [SRC]:
- **Internal ids**: `editor_discovery_api.h:15-51`, 1-23, with select-all = 23.
- **Engine bound** (`probe_engine.cpp:7062-7069`): `kMaxInternalEditorAction = 23`, with the comment "THIS BOUND MUST MOVE WITH THE ACTION LIST… silent and total". `editorSetActionGestures` returns early above it, and `editorGesturePermitted` returns false (:7073-7092). This is the rule in `CLAUDE.md` ("界限要跟著清單走").
- **Wire ids** (`editor_api.h:45-122`):
  - v1 is 1-10, v2 is 11-15, v3 (ABI 4) is 16-21, with `SELECT_ALL = 21` dark.
  - Doctrine (:30-35): appending happens under a successor identity with an exact-match ABI handshake. "What makes appending safe here -- and unsafe in place -- is that the runtime handshake is an EXACT match".
- **`editor_api.cpp`** (:10-42, :60-65, :78-81, :90-137, :152-167, :173-188):
  - The internal enum.
  - `kMaxExternalAction = 21`, which bounds `set_action_gestures`.
  - `isMove`: only the two character moves accept `extend_selection`.
  - The `internalAction()` switch.
- **`editorActionMutates(action)` is `action >= 7`** (`probe_engine.cpp:4469-4471`). Internal ids 24 and 25 would be classified as "mutating" and so revision-guarded (`requireRevision`, :5469-5471, :2495-2500). Select-all (23) already is. This does not change `mutation=false` on the key path (:5709) [SRC].
- **`editorActionMoves`** covers internal 1-6 only (:4473-4476). It is used only for the extend flag (:5464) [SRC].
- **Gesture gate** for all non-paragraph actions (:5507-5539): before any selection is observed, the action is refused with `EDITOR_FORMAT_GESTURE_UNSUPPORTED` (:5514-5519). That is the same as today's moves [SRC].

**Worker** [SRC]:
- `EDITOR_V3_ACTION_IDS` (1-21, `wsp/sdk/sdk-worker.js:87-95`).
- `manifestAllowsAction`: withheld means `gestures: []`, not absent (:110-130).
- At init it calls `oxsdk_editor_set_action_gestures` per manifest action (:1244-1256), after the exact ABI check (:1225-1235).

**Manifest builder** [SRC]:
- `wsp/tools/build_e2_editor_v4_profile.py`: `MOVE_LINE_ACTIONS` gets `collapsed` and `no-extend-selection` (:107-127).
- It **hard-checks `ids == 1..21`** (:197-199).
- v20's manifest: move-line-* are `{"gestures":["collapsed"],"limits":["no-extend-selection"]}`, and select-all is `gestures: []` [SRC, read from the dist manifest].

**Shell** [SRC]:
- Client: `EDITOR_V3_APPENDED_ACTIONS` (:59-65), `LINE_MOVE_ACTIONS` (:93-95; it is the postcondition set).
- Session: `ACTIONS = new Set(EDITOR_V3_ACTIONS)` (:59, "the layer the ABI 4 link found").
- **"The six moves"** are `BOUNDARY_CAPABLE_MOVES` (:81-84). Membership means `_checkpointBeforeBoundaryMove` runs when the document is dirty (:848-860, finding 096 half C) and the move is enqueued with `mutation: false` (:991-992, :1047; finding 098).

**Native**:
- The key path for Ctrl+Home already exists in a native harness: `wsp/tools/f096_native_dedup.cpp:48-50,111` posts `KEY_HOME|KEY_MOD1`. Its result row: "setup Ctrl+Home | to doc start | no [cursor callback] (only the STATE_CHANGED init burst)", because the caret was already at the start after load (`findings/evidence/096/native/RESULT-native-dedup.md:16`) [DOC].
- `.uno:GoToStartOfDoc` at doc start "moves nothing, emits no cursor rectangle" (`findings/evidence/021/native-caret-tracking/probe-source.cpp:195-203`) [DOC, source comment].
- **WASM has never dispatched Ctrl+Home/End to the engine.** The 10-14n arm's chord stopped at the page [DOC :90].

### (c) Decided vs open

Decided [DOC]:
- The fix is an engine action, in the next link batch.
- Red case: `press-after-ctrl-home` must read as a boundary no-op.
- Names: `move-document-start` and `move-document-end`.

Open:
1. **Dispatch route.** Either the key path, `Key::HOME|Mod1` and `Key::END|Mod1` (FIFO with other posted keys, `mutation=false`, the 096 readback), or `.uno:GoToStartOfDoc/EndOfDoc`. The UNO route is the mutation route, and per extend_completion.hpp:56-57 a UNO dispatch jumps posted keys, which is finding 137's class [SRC/INF]. The key path also needs a characterisation on WASM. Today's Mod1 use (select-all) is explicitly uncharacterised (:5689-5690).
2. **Ids and ABI.**
   - The new wire ids would be 22 and 23 (append-only, pinned by `tests/editor_abi_header_test.cpp:55-67`), and the new internal ids 24 and 25.
   - The batch must order these appends together with any other new action (for example Markdown paste, if it is an action rather than a document-level op, as `redo` and `pageRectangles` are).
   - **Does the ABI move 4→5?** The doctrine at `editor_api.h:30-35` says appended ids ride a successor identity with an exact-match handshake, and the v20 link kept ABI 4 because no action changed (`RUNBOOK-relink-v20.md:17`). It also says an allowlist's version is an identity. I infer that 5 is required [INF]. That cascades into `tests/editor_abi_header_test.cpp:20`, the builder's `ABI_VERSION`, and the worker's exact check.
3. **Gestures.** One option is `collapsed` only, like the six moves. Then on a range the page does `moveFromPoint` (click, then move), which ties in item 1. Granting `range-single` and `range-cross` would instead need a native characterisation: does Writer's Ctrl+Home on a range collapse and go to the start? `f129_native_arrow_on_selection.cpp` is the precedent harness. Note that the engine gate requires both range bits for an unclassified range (:5528-5531).
4. **Extend.** Ctrl+Shift+Home/End are out (`isMove`, :78-81; the page's Shift rule, :2960; Shift+arrow is withdrawn until "有序指令", release text :208-210) [SRC/DOC].
5. **Verification of the move itself.**
   - Today no move verifies its target. The spec must say whether "caret at document start" is checked. The README's red test checks it indirectly: the next Backspace answers `verified-boundary-noop`.
   - With a11y absent on the shipped core there is no paragraph index or fingerprint (`findings/140…md:47`).
   - Possible checks [INF]: the caret rectangle in the answer against the first page's rectangle via `page-rectangles` (v20), or the next delete's no-op.
6. **Writer semantics in special places** [INF from general LibreOffice knowledge, not verified in this repo]: Ctrl+Home inside a table cell (Writer steps cell → table → document), inside a header, footer or footnote, and in a document that starts with a table. These need native arms before the manifest claims the action.
7. **Page binding.**
   - Move the `if (accel) return;` (:2950) or add Ctrl+Home/End before it.
   - Should macOS Cmd+Up/Down also bind? `accel` treats Cmd as Ctrl, so Cmd+Home would map automatically [SRC/INF].
   - `preventDefault` so the hidden textarea does not move its own caret.
   - `ACTION_LABELS`.
   - The "a key that cannot dispatch must not be taken" rule (:2824-2829) on profiles without the action. Should the interim toast (README option C) ship before the link?
8. **`BOUNDARY_CAPABLE_MOVES` membership** (checkpoint before the move, non-mutation) and `LINE_MOVE_ACTIONS`, or a new set, for the client postcondition [SRC/INF].

### (d) Layers changed

- **Engine C++**:
  - `editor_discovery_api.h`: the internal enum.
  - `editor_api.h`: a new v4 wire enum and maybe the ABI constant.
  - `editor_api.cpp`: the internal enum, `kMaxExternalAction`, `internalAction()`.
  - `probe_engine.cpp`: `editorActionName`, the key-path cases, and **`kMaxInternalEditorAction` 23 → 25**.
- **SDK worker**: the action-id table → new worker sha → the Makefile pin.
- **Manifest builder**: new `NEW_ACTIONS` and the 1..N id check (:198), plus `tests/test_e2_editor_v4_profile.py` (e.g. :141).
- **Identity checks**:
  - X1 (`tools/check_profile_identity.py --declared-…`, `RUNBOOK-relink-v20.md:113-118`).
  - `tools/what_the_link_ships.py`.
  - `tools/check_merge_key_undo_scope.py` carriers (`RUNBOOK-relink-v20.md:33-37`).
- **Shell (v2 only)**: client lists and postcondition sets, session `ACTIONS` (inherits from the client constant) and `BOUNDARY_CAPABLE_MOVES`, the `.d.ts` files.
- **Page**: `KEY_ACTIONS`/accelerator handling and `ACTION_LABELS`.
- **Cost of a page change**: a new page sha re-pins every runner and judge (e.g. `PAGE_SHA256` in `wsp/tools/check_m3_*.py`, now `901dd6a6…`), plus the new-document check bindings and the host package.
- **Shell generation**: the bundle scope includes `sdk`, `editor-shell-v2` and the entrypoint (`build_e2_c_shell_bundle.py:757-768`), so a new generation (v74+) is needed.
- **E1-C**: `editor-shell/` stays untouched.

### (e) Tests, criteria, evidence

- **Red case**: `press-after-ctrl-home` in `findings/evidence/host-0.2.20-hand-test/probe_10_14n.py`. Today it gives `verified-selection-delete` and revision 0→1. After the fix: the caret at the document start, then Backspace gives `verified-boundary-noop` (and with item 2, fast).
- **Unit tests**:
  - `editor-shell-v2/tests/offers.test.mjs` and `narrow-editor-v2-session.test.mjs` reference `move-line-home`.
  - The client postcondition tests.
  - The page keydown tests (`product-page-calls.test.mjs`, `page-*.test.mjs`).
  - `tests/editor_abi_header_test.cpp`, `tests/test_e2_editor_v4_profile.py`.
- **The CLAUDE.md "withheld vs omitted" rule**: if one of the two ships dark, it must be `gestures: []`, never omitted [DOC].
- **Native to reuse or extend**:
  - `wsp/tools/f096_native_dedup.cpp` (Ctrl+Home on the key path, native 26.8, at doc start: no cursor callback).
  - `wsp/tools/link_native_extend_signatures.cpp`: the shape for a "which callbacks does Ctrl+Home/End emit from 14 starting shapes" table.
  - `wsp/tools/f129_native_arrow_on_selection.cpp`: on a range.
- **WASM measurements that would show it works**:
  - From mid-document, Ctrl+Home completes with `documented-callback-visible-cursor` and the caret at the first text position.
  - At doc start, `verified-move-readback` within about 250 ms with revision unchanged and the session not blocked (096's shape).
  - Ctrl+End mirrors both.
  - On a range: `moveFromPoint`, then the move.
  - The `press-after-ctrl-home` arm.

### (f) Interactions

- **With item 2**: the red test needs Backspace after Ctrl+Home to be a boundary no-op, so a Ctrl+Home followed quickly by Backspace exercises C. If a move-document-start completed by readback (at doc start) and the Backspace is posted behind it, today's K1 is FIFO-ordered. A synchronous pre-check (item 2, design A) would not be ordered [INF].
- **With item 1**: see item 1 (f).

---

## Cross-item interactions and the rest of the batch

| pair | fact or inference |
|---|---|
| 1 ↔ 3 | `move-document-*` with `collapsed` gestures on a range goes through `moveFromPoint` → `placeCaret` (page :2973-2979, :3068). Item 1's routing decides that click's path [SRC/INF]. |
| 2 ↔ 3 | 142's red test is item 2's no-op. With the key path, Ctrl+Home and K1 are FIFO in core. A synchronous boundary pre-check is not [INF; §10.5 :180]. |
| 2 ↔ page 141/144 | Holding still applies. An immediate answer drops held presses sooner, and the 144 flagged-hold residual (one window per flagged repeat) collapses [INF]. |
| 2 ↔ §17.4 | The count's only positive control for Rbs/Rdel is the ≥ 2,000 ms busy period, which item 2 removes [DOC :565-567; INF]. |
| 2 ↔ manifest C field | Tools key on the wasm fragment (`run_merge_wasm_shakedown.py:200`, and production UI per §17.3). Decide the field and the (possibly new) semantics together. `boundaryRejectionRequiresFreshWorker: true` is stale on v20 [SRC]. |
| all ↔ ABI/ids | Only item 3 adds wire ids. If Markdown paste becomes an action, its id must be appended in the same successor identity (`research/RESEARCH-2026-10-14-markdown-paste.md:28`: "ABI 與 action 清單怎麼擴充由規格決定") [DOC]. |
| all ↔ `Language=` | Engine load uses `documentLoadWithOptions` with `Language=` only under `OXSDK_E2_UI_LANGUAGE` today (`probe_engine.cpp:2969-2994`) [SRC]. A UI language changes Writer's localized strings (finding 031). Neither item 2 nor item 3 may key on Writer's strings [INF]. |
| all ↔ D12 | D12 is the paper size for `en` (Letter vs A4) once `Language=` exists (`specs/SPEC-M3-new-document.md:228,287`) [DOC]. It matters only if item 2 or item 3 verifies by page geometry (e.g. first-page rectangle) [INF]. |
| all ↔ identity | One relink means one new profile (e.g. `e2-editor-v21`), a new Makefile block and define, a worker pin, X1 deltas, a shell generation, a page re-pin if the page changes, a host version and a full count. Per memory, the count is batched with this engine change [DOC: RUNBOOK-relink-v20 structure; `handoff/HANDOFF-2026-10-16…md:106`: "Archive the current profile first… v20 `.o` files are already stale"]. |

## Stale references found while reading (doc text vs current source)

- `findings/142…md:7` cites `web/e2-editor-app.js:2679`; the `if (accel) return;` is now at :2950 (page `901dd6a6…`).
- `findings/140…md` cites page lines `:2373`, `:2365` (`caretTimeoutMs`), `:1821`, `:2787` and `:2704-2708`. The current callers are at :2525, :1966 and :3068; the branch is at :2973-2979. `caretTimeoutMs` no longer appears in the page (grep: 0 hits).
- `findings/evidence/host-0.2.20-hand-test/README.md:126` proposes `.uno:GoToStartOfDoc` "through the existing move machinery"; the existing machinery is the key path (see item 3(b)).
