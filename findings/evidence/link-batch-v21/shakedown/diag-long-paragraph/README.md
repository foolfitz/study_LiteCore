# Long-paragraph crash diagnosis (v21 shakedown, item 2 follow-up)

**Recorded, not judged. Nothing here is counted.** 2026-10-17, Chrome 151.0.7922.169 (headless) and Firefox (headless, Marionette), the shipped `e2-editor-v21` profile (`probe.wasm` db3408f5…, `probe.js` 0b6cf02a…, worker 0d55bcfa…, page 3d511216…, shell digest e0252c0b…; `identityOk: true` in every report), the round's page and shell as the item-2 runner serves them.

Labels: **[observed]** measured in these runs; **[source]** read in source (file:line); **[inferred]** a reading of the two.

## The question

The item-2 smoke (`../smoke/item2/README.md`, rows "M3 size" and "Product") saw a Markdown paste of one CJK paragraph of 65,536 UTF-8 bytes (`"中" * 21845 + "a"`, sha256 9ecdb239…) crash the WASM worker through the SDK (`WORKER_CRASHED`, `memory access out of bounds`) and get no reply when posted to the worker directly, both in a long browser session. The main session's hypothesis: the link sets `-sDEFAULT_PTHREAD_STACK_SIZE=65536` and the engine runs on a pthread.

## Answer

- It is not the session's state: a fresh browser crashes **3/3** (SDK) and gets **no reply 3/3** (raw worker message, the pthread raised the same `memory access out of bounds`) [observed].
- It is not the paste's size or the Markdown: it is **how many pages of ONE paragraph a single layout pass has to format** (step 9: a one-character insert at the start of an existing long paragraph fails too). One CJK paragraph is fine up to **43,008 bytes (14,336 characters, 10 pages)** and fails from **43,520 bytes (14,508 characters)** in 3/3 [observed]. Splitting the same 65,536 bytes into 2, 4 or 16 paragraphs is fine; 65,536 ASCII `a` and CJK with a space every 100 characters crash [observed].
- Plain text fails too: the SDK's `insertText` of the same paragraph hangs (30 s `TIMEOUT`, then the worker answers nothing) at 65,536 and 43,520 bytes on v21, and **0.2.24's engine (`e2-editor-v20`) hangs the same way** given the text by a raw `insertText` [observed]. The defect predates v21. **0.2.24's Ctrl+V cannot deliver it in one paste**: the page's input adapter refuses anything over 16,384 bytes, on both pages [observed][source].
- **But 0.2.24 does fail without any paste** (not in the brief, added after the above): open a document whose body already holds one CJK paragraph of 10 or 14 pages — the open itself is fine on both pages — then insert ONE character at the caret the open leaves (the paragraph's start): **0.2.24 fails 4/4** (14 pages: hang, hang, engine abort after the insert answered; 10 pages: engine abort), **v21 2/2** (hang; abort). Controls: the same on a 1-page paragraph is fine on both pages; the bigger-stack loader makes both long documents fine [observed]. The character went in by a raw `insertText`, the engine operation a typed key becomes [inferred: not driven through the keyboard here].
- Native LibreOffice (round 2's probe) pastes it fine, 6/6, ~50 ms, 12 pages [observed]. Firefox fails like Chrome (65,536: crash 3/3; 43,520: ok then the engine broken; 43,008: ok) [observed].
- The crash site, mapped by function-body matching against two named links: Writer's layout formats a paragraph's follow frames **recursively** (`SwContentFrame::MakeAll → SwTextFrame::Format → FormatImpl → Format_ → FormatAdjust → SwFrame::Calc → PrepareMake → MakeAll`, 11 levels), and the trap is a store inside `__pthread_mutex_trylock` under `SwFrame::InsertPage` [observed stack][mapped].
- **The hypothesis holds as a counterfactual**: the same page with ONE change in the mirror's `probe.js` (the default pthread stack handed to `_emscripten_thread_init`, 65,536 → 1,048,576; `probe.wasm` untouched) pastes every failing input fine, 6/6, and takes the typed character into both long documents, 2/2 [observed].

## Table

Outcome labels (`tool/diag_long_paragraph.py` `classify`): **ok** answered ok, worker alive, document saved; **crash** `WORKER_CRASHED` or `memory access out of bounds` / an uncaught exception on a pthread; **hang** the SDK's 30 s `TIMEOUT` (or no reply on a raw route) and the worker answers no state ask afterwards, the browser's processes at ~0 % CPU where sampled; **ok-then-crash** the paste answered ok and the engine thread aborted seconds later; **no-request** the page sent nothing to the worker. Pages are `meta:page-count` of the document the cell saved. One fresh browser per cell.

| step | cell (route : corpus : bytes [: page]) | N | outcome | pages / paragraphs | note |
|---|---|---|---|---|---|
| 1 | sdk-md : cjk : 65,536 | 3 | crash 3/3 | — | `WORKER_CRASHED`, 0.1 s |
| 1 | worker-md : cjk : 65,536 | 3 | crash 3/3 (no reply) | — | pthread `memory access out of bounds` |
| 2 | sdk-md : cjk : 4,096 / 8,192 / 16,384 / 24,576 / 32,768 | 1 each | ok | 1 / 2 / 4 / 6 / 7 | |
| 2 | sdk-md : cjk : 40,960 | 1 | ok | 9 | bisect 1 |
| 2 | sdk-md : cjk : 43,008 | 3 | ok 3/3 | 10 | last OK (bisect 3 + 2) |
| 2 | sdk-md : cjk : 43,520 | 3 | hang 1, ok-then-crash 2 | — | first failing (bisect 5 + 2) |
| 2 | sdk-md : cjk : 44,032 | 1 | hang | — | bisect 4 |
| 2 | sdk-md : cjk : 45,056 | 1 | hang | — | bisect 2 |
| 2 | sdk-md : cjk : 49,152 | 1 | crash | — | |
| 3 | sdk-md : ascii : 65,536 | 1 | crash | — | 65,536 characters, no break opportunity |
| 3 | sdk-md : cjksplit2 : 65,536 | 1 | ok | 14 / 2 (+1 empty) | longest 10,924 characters |
| 3 | sdk-md : cjksplit4 : 65,536 | 1 | ok | 14 / 4 | longest 5,461 |
| 3 | sdk-md : cjksplit16 : 65,536 | 1 | ok | 15 / 16 | longest 1,365 |
| 3 | sdk-md : cjkspace100 : 65,536 | 1 | crash | — | 217 spaces |
| 4a | sdk-text : cjk : 65,536 | 1 | hang | — | `insertText`, no SDK size limit (none exists, [source] `document-sdk.js:533-543`) |
| 4a | sdk-text : cjk : 43,520 | 1 | hang | — | |
| 4b | ctrlv-text : cjk : 65,536 | 1 | no-request | — | page toast 「有字沒有輸入：一次送出的內容太大，請檢查最後打的字」 |
| 4b | ctrlv-text : cjk : 43,520 | 1 | no-request | — | same |
| 4b+ | ctrlv-textx3 : cjk : 16,383 | 1 | ok | 11 / 1 | three Ctrl+V into one paragraph: 16,383 characters |
| 4b | ctrlv-text : cjk : 65,536 : v0224 | 1 | no-request | — | `InputAdapterError: input is 65536 UTF-8 bytes; limit is 16384` |
| 4b | ctrlv-text : cjk : 43,520 : v0224 | 1 | no-request | — | same |
| 4+ | worker-text : cjk : 65,536 : v0224 | 1 | hang | — | 0.2.24's engine, raw `insertText` |
| 4+ | worker-text : cjk : 43,520 : v0224 | 1 | hang | — | |
| 5 | native, text/markdown, P1 | 3 | ok 3/3 | 12 / 1 (+1 empty) | 48.8–56.5 ms, 21,846 characters |
| 5 | native, text/plain, P1 | 3 | ok 3/3 | 12 / 1 | 46.9–50.6 ms |
| 7 | Firefox : sdk-md : cjk : 65,536 | 3 | crash 3/3 | — | `WORKER_CRASHED` ("uncaught exception: [object ErrorEvent]") |
| 7 | Firefox : sdk-md : cjk : 43,520 | 1 | ok-then-crash | — | paste ok (28.8 ms), then `recoverable-error` |
| 7 | Firefox : sdk-md : cjk : 43,008 | 1 | ok | 10 / 1 (+1 empty) | |
| 8 | sdk-md : cjk : 65,536 : v21big | 3 | ok 3/3 | 14 / 1 (+1 empty) | counterfactual loader |
| 8 | sdk-md : cjk : 43,520 : v21big | 1 | ok | 10 | |
| 8 | sdk-text : cjk : 65,536 : v21big | 1 | ok | 14 / 1 | |
| 8 | sdk-md : ascii : 65,536 : v21big | 1 | ok | 15 | |
| 9 | open : ok10 (43,008-byte paragraph saved by v21) | 1 | ok | 10 | |
| 9 | open : long10 / long14 | 1 each | ok | 10 / 14 | documents saved by the v21big cells |
| 9 | open : long10 / long14 : v0224 | 1 each | ok | 10 / 14 | |
| 9 | opentype : short1 (1 page) [: v0224] | 1 each | ok | 1 | `x` lands at the paragraph's start |
| 9 | opentype : long14 | 1 | hang | — | the insert never answers |
| 9 | opentype : long10 | 1 | ok-then-crash | — | insert ok, then the engine aborts |
| 9 | opentype : long14 : v0224 | 3 | hang 2, ok-then-crash 1 | — | **0.2.24** |
| 9 | opentype : long10 : v0224 | 1 | ok-then-crash | — | **0.2.24** |
| 9 | opentype : long14 / long10 : v21big | 1 each | ok | 14 / 10 | counterfactual loader |

Every cell, with its stored fields: `python3 -B tool/summarize.py out` (re-labels with the current `classify` and shows a different stored label beside it).

## Step by step

### 1. Fresh browser [observed]

`out/report-chrome-s1-sdk.json`, `out/report-chrome-s1-worker.json`. SDK route: `WORKER_CRASHED` ("Uncaught [object ErrorEvent]") 0.1 s after the call, 3/3; the worker answers no state ask afterwards. Raw worker route: no reply in 240 s, 3/3, and CDP shows the same exception on the loader's worker (a pthread). The 64 KiB corpus of many short sections in the smoke is not this case (step 3).

Every crash cell's pthread exception has **112 frames**, identical in shape at 49,152 and 65,536 bytes, CJK or ASCII, SDK or worker route: the overflow happens at a fixed depth, not at a fixed input size [observed]. (`chrome-s1-sdk` kept only 80 of the 112 frames; see "Fixed because of execution".)

### 2. Threshold [observed]

Pages per CJK size in WASM: 1,366 characters 1 page … 14,336 characters 10 pages (the WASM layout fits fewer characters per page than native: 65,536 bytes is 14 pages in WASM, 12 natively). Last OK **43,008 bytes = 14,336 characters** (3/3, 10 pages); first failing **43,520 bytes = 14,508 characters** (3/3 failing, two ways). Resolution 512 bytes (bisection 32,768 → 49,152 → 40,960 OK → 45,056 hang → 43,008 OK → 44,032 hang → 43,520 hang).

Three failure modes, by size [observed]:

- **crash** (≥ 49,152): `memory access out of bounds` inside layout (stack in "Crash site").
- **hang** (43,520–45,056; also every plain-text `insertText` failure): the SDK's 30 s `TIMEOUT`, then no answer to a state ask; the browser's processes at 0–0.5 % CPU in every hang cell sampled (all after bisect 2, which predates the sample), so the engine thread is parked, not spinning.
- **ok-then-crash** (43,520, 2/3): the paste answers ok (revision 1, 43.6 ms), ~4 s later the engine thread aborts: `RuntimeError: unreachable` from `abort ← std::terminate ← std::condition_variable::wait ← (engine loop) ← std::thread` (mapped, `out/function-map-abort.json`; two frames there map to unrelated names, likely identical-code aliases, and are not used: 3710, 117863). The page shows `recoverable-error` (需要回復).

### 3. Shape [observed]

All 65,536 bytes. Two, four or sixteen paragraphs of the same CJK text: ok, 14–15 pages in total, longest paragraph 10,924 / 5,461 / 1,365 characters. One paragraph of 65,536 ASCII `a`: crash. One CJK paragraph with a space every 100 characters: crash. So the total size and the number of pages do not matter, the paragraph does; line-break opportunities do not.

### 4. Plain text

(a) [observed] `DocumentHandle.insertText` through the S-3 hook: the SDK has no size limit for it ([source] `sdk/document-sdk.js:533-543`), and the engine's `insertText` is LOK `paste("text/plain;charset=utf-8")` ([source] `src/probe_engine.cpp:3258-3266`), the same `doc_paste → .uno:Paste` path as the Markdown paste. Hang at 65,536 and at 43,520 bytes.

(b) [observed] Real clipboard + trusted Ctrl+V into `#sink`: **the page sends nothing** at 65,536 or 43,520 bytes. The input adapter refuses over 16,384 UTF-8 bytes ([source] `input/input-adapter.js:1`, `:338-345`; the session builds it without `maxUtf8Bytes`, `editor-shell/editor-session.js:92-96`) and the page shows 「有字沒有輸入：一次送出的內容太大，請檢查最後打的字」. Same on 0.2.24 (`dist/input/input-adapter.js:1`), where the refusal also surfaces as an uncaught page exception `InputAdapterError: input is 65536 UTF-8 bytes; limit is 16384`.

Plain text fails in the engine, so the defect predates v21 [observed]: **0.2.24's engine** (`e2-editor-v20`, `probe.wasm` 313b08d5…), given the 65,536- or 43,520-byte paragraph by a raw `insertText` message on the 0.2.24 page, hangs (no reply in 90 s, parked) [observed]. Its link has the same flags ([source] `Makefile:1576` → `link_r5_product`, `Makefile:847`) and its loader the same `65536` ([source] `dist/profiles/e2-editor-v20/probe.js`, `__emscripten_thread_init(tb,…,65536,false)`).

What a 0.2.24 user can reach by Ctrl+V [observed, v21 page]: three Ctrl+V of 16,383 bytes into one paragraph grow it to 16,383 characters and 11 pages without failing. So the depth that fails is not the paragraph's length but how many of its follow frames one layout pass formats, nested: appending at the end reformats only the last ones [inferred]. A single Ctrl+V into an empty or short paragraph (≤ 16,384 bytes, ≤ ~4 CJK pages) stays below it on both pages; at the start of an existing long paragraph it would not (step 9) [inferred].

### 5. Native [observed]

Round 2's probe rebuilt with g++ exactly as its README says (binary sha256 425a8b01…, the counted runs' hash reproduced), run by round 2's `run_arms2.run_one` imported unchanged except `corpus_path` (`tool/native_long_paragraph.py`): P1 of the empty template, `text/markdown;charset=utf-8` and `text/plain;charset=utf-8`, N=3 each. 6/6 returned, rc 0, no watchdog, paste call 46.9–56.5 ms, process 6.1–6.4 s; saved: one paragraph of 21,846 characters (the Markdown paste adds the template's empty paragraph after it), `meta:page-count` 12; eleven `DOCUMENT_SIZE_CHANGED` callbacks, one page at a time. Outputs: `out/native/`.

### 6. Crash site

**Symbols** [observed]: `probe.wasm` (v21, shipped and `build/e2/editor-v21/`) has **no custom section at all** (no `name`, no `target_features`), and neither directory holds a symbol map. Two other links of the same core tree carry a `name` section: `build/e2/preguard-profiling/probe.wasm` (same flags + `--profiling-funcs`) and `build/e2/wait-diagnostic/probe.wasm`. `tool/map_functions.py` (written for this by a subagent; method and limits in its docstring) matches function bodies with link-dependent immediates normalised, checks uniqueness in both directions, checks every frame offset falls on an instruction of the given function and every caller instruction calls the next frame, and confirms each edge in the reference. The crash stack's top 20 functions: 20/20 exact-unique in both references, every edge (the ring included) confirmed in both (`out/function-map.json`); its bottom 28 frames: 26/28 exact-unique in reference A and 25/28 in B, the two engine functions unmatched (`out/function-map-bottom.json`).

**The stack** (Chrome, the pthread's `Runtime.exceptionThrown`, 112 frames, innermost first) [observed + mapped]:

```
__pthread_mutex_trylock            <- trap: memory access out of bounds (an i32.store)
__pthread_mutex_lock
osl_acquireMutex
SfxBaseModel::Notify  (+ its non-virtual thunk)
SfxBroadcaster::Broadcast
SwRootFrame::CheckViewLayout
SwPageFrame::Paste
(anon)::doInsertPage
SwFrame::InsertPage
SwFrame::GetNextLeaf
SwFrame::GetLeaf
SwFlowFrame::MoveFwd
SwContentFrame::MakeAll   -+
SwFrame::PrepareMake       |
SwFrame::Calc              |  the ring, 11 x MakeAll in the stack:
SwTextFrame::FormatAdjust  |  a follow frame is formatted from inside
SwTextFrame::Format_       |  its master's FormatAdjust
SwTextFrame::FormatImpl    |
SwTextFrame::Format       -+  (x 10 more)
SwContentFrame::MakeAll
SwFrame::OptPrepareMake
SwLayAction::FormatContent_ / FormatContent / InternalAction / Action
SwViewShell::ImplEndAction / EndAction, SwCursorShell::EndAction, SwViewShell::EndAllAction
SwTransferable::PasteData / Paste, SwBaseShell::ExecClpbrd, SfxStubSwBaseShellExecClpbrd
SfxDispatcher::Call_Impl / Execute_ / Execute, SfxDispatchController_Impl::dispatch
SfxOfficeDispatch::dispatch (+ thunk), comphelper::dispatchCommand (x3)
doc_paste
wasm-function[77122], [91105]   (engine; no match: the engine objects changed since the references)
std::__thread_proxy<..., void (*)(probe::(anon)::Command), ...>
invokeEntryPoint, handleMessage (probe.js)
```

**Why it nests** [source]: `SwTextFrame::FormatAdjust` (`sw/source/core/text/frmform.cxx:1216`) calls `AdjustFollow_` (`:1519`), which calls `CalcFollow` (`:695`), which calls `pMyFollow->Calc(pRenderContext)` (`:290`) — the follow is formatted inside its master's format, and its own `FormatAdjust` does the same for the next follow; the three inner calls are inlined in the WASM ring (the mapped ring goes `FormatAdjust → SwFrame::Calc` directly). So one layout pass nests once per follow frame (page) of the paragraph it formats. Natively the 65,536-byte paragraph is 12 such levels, on a thread stack of megabytes [inferred].

**Why 64 KiB** [source]: v21 does not define `OXSDK_MAINLOOP_ENGINE` (`Makefile:1654-1659`), so the engine thread is `std::thread(engineLoop, …)` (`src/probe_engine.cpp:6956`; the stack's bottom is `std::__thread_proxy` [observed]); libc++ creates it with `pthread_create(__t, nullptr, …)` (`emsdk …/system/lib/libcxx/include/__thread/support/pthread.h:182`); a null attribute takes `__default_stacksize` (`emsdk …/system/lib/pthread/pthread_create.c:141-144`, emsdk 4.0.10), which the loader sets once from the link's `DEFAULT_PTHREAD_STACK_SIZE` (`emscripten_thread_init.c:22-23`; served `probe.js`: `__emscripten_thread_init(tb,!ENVIRONMENT_IS_WORKER,1,!ENVIRONMENT_IS_WEB,65536,false)`; `Makefile:847` in `link_r5_product`, used by v21 at `:1682`). `-sASSERTIONS=0` (`Makefile:849`) leaves `STACK_OVERFLOW_CHECK` at 0 (`emsdk …/src/settings.js:55,67`): nothing checks the shadow stack. The thread's block is laid out low to high as `struct pthread`, TLS, TSD pointers, **then the stack** (`pthread_create.c:146-152`), so a shadow stack that overflows downward writes the thread's own `struct pthread` first.

**The trap** [inferred, from the decoded instruction, `tool/map_functions.py` reading by the subagent]: the store is `*(next - sizeof(void*)) = &m->_m_next`, musl's robust-list link for a non-normal (here recursive: the SolarMutex) mutex, where `next` is `self->robust_list.head` — a field of that same `struct pthread`. A corrupted `struct pthread` gives exactly this trap; a different corruption at a slightly different depth gives the hang (a parked lock or condition wait) or the late `condition_variable::wait → std::terminate` seen at 43,520 bytes.

### 7. Firefox [observed]

`out/report-firefox-s7.json`, Firefox 157.0.1 headless (no CDP: the worker's own exception is not visible; the SDK's answer, the page's state, a state ask and the save are). 65,536 bytes: `WORKER_CRASHED` ("uncaught exception: [object ErrorEvent]") 3/3, the page in `recoverable-error` (重新開啟). The same edge as Chrome: 43,520 bytes answers ok (28.8 ms, revision 1) and the engine is then broken (page `recoverable-error`, the state ask answered `ok: false`, the save never comes) — Chrome's ok-then-crash; 43,008 bytes ok, 10 pages, 14,336 characters. Not browser-specific.

### 8. Counterfactual: a bigger default pthread stack, nothing else (not in the brief) [observed]

`out/report-chrome-s8-bigstack.json`, page `v21big`: the mirror's `profiles/e2-editor-v21/probe.js` is the shipped loader with ONE change, the literal in `__emscripten_thread_init(tb,!ENVIRONMENT_IS_WORKER,1,!ENVIRONMENT_IS_WEB,65536,false)` → `1048576` (served sha256 dc4c2c84…, shipped 0b6cf02a…). `probe.wasm`, the worker, the manifest, the page and the shell are the shipped ones (the mirror's `probe.wasm` stays a symlink into `dist/`; the worker has no integrity check on the loader, [source] `sdk/sdk-worker.js:743-771`; the identity block's `identityChecks.probe.js` compares `dist/`'s file, so read `counterfactual.servedSha256` for what was served). Results: the 65,536-byte CJK Markdown paste ok 3/3 (14 pages, one paragraph of 21,846 characters); 43,520 bytes ok (10 pages, 14,508 characters); `insertText` 65,536 ok (14 pages); 65,536 ASCII ok (15 pages, 65,536 characters). No exception on any worker.

This is a non-shipped loader. It shows that the default pthread stack is sufficient cause; it does not say what size the product should link with, nor whether other threads or other inputs need more.

### 9. Open a document that already holds the paragraph, then type (not in the brief) [observed]

Added after step 4, because "0.2.24's Ctrl+V cannot deliver it" does not cover a document that already has such a paragraph (made in desktop LibreOffice, or received). `out/report-chrome-s9-open.json`, `out/report-chrome-s9-opentype.json`, `out/report-chrome-s9-opentype2.json`. Documents: `long14` and `long10` are what the v21big cells saved (one paragraph of 21,846 / 14,508 CJK characters, 14 / 10 pages, sha256 150d28f5… / be41163b…); `ok10` the 43,008-byte document a shipped-loader cell saved; `short1` the 4,096-byte one (1 page).

- **Opening** each of them is fine on v21 and on 0.2.24 (the open takes ~1.8 s; the save afterwards reports 10 / 14 pages, so the layout did run) — the load lays the paragraph out without the nesting [inferred: not traced].
- **Then one character** (`insertText "x"` posted raw to the worker, at the caret the open leaves, which is the paragraph's start: the controls' saved documents begin `x中中中…`): 1-page control fine on both pages; `long14` and `long10` fail on both: v21 hang (14 pages) and ok-then-crash (10 pages); **0.2.24 hang, hang, ok-then-crash (14 pages) and ok-then-crash (10 pages)**. The abort's stack on 0.2.24's engine is the same as v21's (`condition_variable::wait → std::terminate → abort` under the engine thread's `std::thread`, `out/function-map-abort-v20.json`). With the bigger-stack loader both long documents take the character fine (21,847 / 14,509 characters saved).

So a 0.2.24 user reaches it without pasting anything: open a document with a ~10-page paragraph and type at its start [observed for an inserted character; a real keystroke goes through the page's input adapter to the same engine `insertText`, not driven here].

## Reading [inferred]

The worker crash is a **shadow-stack overflow on the engine thread**: Writer formats a paragraph's follow frames from inside its master's format, one nesting level per follow frame the pass formats, and at about ten levels the 64 KiB default pthread stack (no overflow check) runs into the thread's own `struct pthread`. What it then hits decides the symptom — an out-of-bounds store in the next recursive-mutex lock, a parked wait, or a `std::terminate` from a failed condition wait. It is not Markdown-specific, not v21-specific (0.2.24's engine fails on the same plain text and on one character typed into such a paragraph) and not Chrome-specific (Firefox fails at the same sizes). It is per paragraph: 64 KiB of short sections, or the same text in two paragraphs, is fine; loading such a paragraph is fine, but an edit that makes one pass reformat its follows (an insert at its start, a paste that creates them) is not. Three Ctrl+V of 16 KiB appended at the paragraph's end grew it to 11 pages without failing: appending reformats only the last frames, so the depth there is the pages that one paste adds (≤ ~4 per 16 KiB Ctrl+V) [inferred from that cell and the typed-at-start cells]. v21's paste-as-Markdown lets one pass add up to ~14 CJK pages and so reaches the limit from an empty document; 0.2.24 reaches it from an existing long paragraph.

Not settled here: why some failures hang and others trap or abort (a different corruption at a different depth is a guess); whether typing in the middle or at the end of a long opened paragraph fails (only the start was tried); whether other deep layout (tables, nested sections, long footnotes, frames) reaches the same limit; native with a typed character at the start of a long opened paragraph (not run).

## Fixed because of execution

The tool changed between reports; each report keeps its own `toolSha256` (`fe177d8b` s1-sdk → `aed5415a` s1-worker, s2-sizes, bisect 1–2 → `cb55c311` bisect 3–5, edges → `cefa6253` s3, s4-plain → `efe0d0c1` s4-v0224, s8 → `22ac9d2a` firefox-s7, s9-open → `3f4449bd` s9-opentype → `07353416` s9-opentype2, the committed file). `summarize.py` applies the committed `classify` to every report.

1. After `chrome-s1-sdk`: the CDP frame list was cut at 80 frames; raised to 300. `chrome-s1-sdk` keeps 80 of its 112 frames (its `frameCount` is whole); every later report has all frames.
2. After `chrome-s2-bisect2-45056` (the first SDK `TIMEOUT`): added `browserCpu` (CPU of the browser's processes over 2 s after the attempt) and the label `hang`. The bisect-2 report's stored label is `refused:TIMEOUT`; `summarize.py` shows both.
3. After `chrome-s2-edges`: the label `ok-then-crash` (a paste answered ok, then the pthread aborted); the stored label there is `ok`.
4. For the 0.2.24 cells: the route `worker-text` (raw `insertText`; the 0.2.24 page has no S-3 hook) and a 90 s raw-route wait (`chrome-s1-worker` waited 240 s).
5. The first Firefox invocation waited 20 min for the S-9 lock (held by the dirty-move diagnostic's back-to-back runs) inside a 58 min `timeout`; it was stopped before its first cell (no cell ran) and its empty report removed, then rerun with a longer timeout.
6. Added the routes `open` and `opentype` (step 9) after step 4; and the Firefox reading of ok-then-crash without CDP (the page in `recoverable-error`, or the state ask answered `ok: false`) after `firefox-s7`, whose 43,520 cell is stored as `ok`.
7. `opentype`'s first labels were `crash` for an insert that answered ok before the abort; relabelled `ok-then-crash` like the paste cells (stored `crash` in `chrome-s9-opentype`).

## Not done / limits

- Bisection resolution 512 bytes; the boundary is not deterministic in its failure mode (43,520: one hang, two ok-then-crash).
- The hang was not traced (no thread dump of a parked WASM thread was taken).
- Two engine frames (`wasm-function[77122]`, `[91105]`) have no name: the engine objects changed since the named references.
- Ctrl+V was measured only in Chrome.
- The counterfactual tried one size (1 MiB) only.
- Step 9 is N=1 per cell except 0.2.24 `long14` (N=3); the typed character went in by a raw message, not a keystroke.
- Firefox: no worker-side stack (no CDP); only the SDK route.

## Reproduce

```
R=/home/jiajun/LibreOffice/study_LiteCore; D=$R/findings/evidence/link-batch-v21/shakedown/diag-long-paragraph
python3 -B $D/tool/corpora.py --check                          # cjk(65536) == the item-2 fixture, sha 9ecdb239…
python3 -B $D/tool/diag_long_paragraph.py --browser chrome --out OUT --label L [--repeat N] CELL ...
    # cells as in the table, e.g. sdk-md:cjk:65536  worker-md:cjk:65536  sdk-text:cjk:43520
    # ctrlv-text:cjk:65536:v0224  worker-text:cjk:43520:v0224  sdk-md:cjk:65536:v21big
    # --odt long14=out/docs-chrome-s8-bigstack/001-sdk-md_cjk_65536_v21big.odt opentype:long14:0:v0224
(cd $R/findings/evidence/link-batch-v21/native/markdown-paste/round-2/tool && \
 g++ -std=c++17 -O2 -Wall -I $R/libreoffice-26-8/include md_paste_probe2.cpp -ldl -lpthread -o S/md-paste-probe2)
python3 -B $D/tool/corpora.py --write S/corpus cjk:65536
python3 -B $D/tool/native_long_paragraph.py S/md-paste-probe2 S/runs OUT/native S/corpus \
    N-md-cjk65536:md:cjk-65536 N-plain-cjk65536:plain:cjk-65536 --runs=3
python3 -B $D/tool/map_functions.py $R/wasm_sdk_probe/dist/profiles/e2-editor-v21/probe.wasm \
    --ref $R/wasm_sdk_probe/build/e2/preguard-profiling/probe.wasm \
    --ref $R/wasm_sdk_probe/build/e2/wait-diagnostic/probe.wasm N@OFFSET ...
python3 -B $D/tool/summarize.py $D/out
```

Every browser cell takes and waits for the S-9 lock, runs the S-9 pre-run checks (KWallet `b false` in every cell), opens a new browser, and closes it.

## Files

- `tool/diag_long_paragraph.py` browser cells; `tool/corpora.py` corpora; `tool/native_long_paragraph.py` native driver; `tool/map_functions.py` function mapping; `tool/summarize.py` the table.
- `out/report-<label>.json` one per invocation (identity, pre-run checks, per cell: load, attempt, after-state, CDP exceptions with frames, console errors, attached/detached targets, browser CPU, saved document summary); `out/docs-<label>/` the documents saved after an ok cell.
- `out/native/` round 2's layout (`cmd.txt`, `stdout.jsonl`, `stderr.txt`, `before/after.fodt.gz`, `summary.json` with `paragraphsAfter`), `runner.log`.
- `out/function-map*.json` the mapper's output for the crash stack (top, bottom), the abort stack (v21), and the abort stack on 0.2.24's `probe.wasm` (`-v20`).
