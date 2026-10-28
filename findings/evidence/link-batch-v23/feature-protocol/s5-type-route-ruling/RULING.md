# S5 typing route for the successor identity: fable ruling (2026-10-28)

Requested by the owner, who chose "ask fable to rule" (option D) when offered A/B/C for the route the successor should use to apply typed text. Forcing measurement: counted S5-02 first failure `shift-Right@cell-end/type` (finding 168) and the native route comparison `../f168-native-routes/` (`420c0301`). The brief sent is `BRIEF.md`. Fable read the named files read-only; it ran no build, browser or native process.

## The ruling, verbatim

> ## SUMMARY
>
> **Ruling: A, narrowed — and A is cheaper than the brief says.** The successor applies TYPED text with `.uno:InsertText` under the existing ordered-UNO proof; real paste and the public `insertText(text)` without an origin keep LOK `paste` byte-for-byte. The origin does not need a page change: `input-adapter.js` already tags every commit (`source: "beforeinput" | "composition" | "clipboard-event" | "clipboard-api"`, lines 226/251/259/268/321), `editor-session.js:92` forwards it as `{ metadata }` and line 511 passes it to `document.insertText(text, options)`; it is dropped at `sdk/document-sdk.js:533` (payload = `{documentHandle, text}`). So the change is SDK + worker + engine, and the E1-C-bound bundle (`e1/editor-shell-bundle-v2.json`, 187706b2) is untouched — no 068-style subclass trick needed.
>
> Shape: a NEW appended engine export (e.g. `oxsdk_document_insert_typed_text`), ABI 6→7, fresh successor identity; the old export keeps paste semantics exactly. Typed commits containing U+000A/U+000D keep the existing path (a raw LF through `SwWrtShell::Insert` is not a paragraph break; keyboard Enter is a different family — out of scope, needs its own ruling if touched). The SDK maps `metadata.source`: beforeinput/composition → typed; clipboard-event/clipboard-api → paste; no metadata → paste (public default unchanged); unknown non-empty source → error, never a silent paste.
>
> Why not B: it rewrites real single-line Ctrl+V over a table selection away from Writer's paste semantics, makes single- vs multi-line Ctrl+V differ in kind, and hides 169 for one case only. Why not C: `postKeyEvent` is an async post with no completion callback (no ordered proof at the first poll — the v23 pattern is UNO_COMMAND_RESULT), it is the path carrying open finding 166 (x processed before an earlier Shift key, 56/56, layer unknown), vcl key chars are 16-bit (non-BMP), and IME commits would be N key events — not how Writer handles IME. ext-text-input also rejected for now: `postExtTextEventAsync` (init.cxx:4867), no result callback.
>
> One correction to the brief: "returned in 0.12 ms (queued)" is a native-non-unipoll artifact. `doc_postUnoCommand` appends `SynchronMode=false` only when `!vcl::lok::isUnipoll()` (init.cxx:5316–5322); the product forces unipoll (probe_engine.cpp:7797–7802) and `InsertText` has no `AsynchronCall` (swriter.sdi:7186) — in the product the dispatch is synchronous inside `postUnoCommand`, like `.uno:Paste` inside `doc_paste` today. No new ordering hazard; the ordered proof is a bonus. Prediction to measure: UNO_COMMAND_RESULT will say `success:false` because the FN_INSERT_STRING case never calls `rReq.Done()` (textsh.cxx:153–156) and `bSuccess = aItem.is()` (unoctitm.cxx:771); the reply must use the void-command policy (presence of the result, not `success`).
>
> 169 is out of the successor's scope as a fix (core patch, owner build, upstream on hold) and IN scope as a positive control. Everything identity-bound (S5 fresh, R1, S1–S4, four arms) re-runs on the successor; the run-03 native oracle is reused unchanged.
>
> ## 1. Ruling and what I verified
>
> Verified by reading: fact 1 (`handleInsertText` at probe_engine.cpp:3788, paste first, postKeyEvent only on `false`); fact 2 run-01 (`reader-run-01.json`, 0 problems, 15 arms × 3 rounds stable, `table2/key-x` = run-03 save `b4f798dc…`, paste = product, `.uno:InsertText` and ext-text-input = key, table4 all later cells `x#`, caret/plain-text paste = key); fact 3 (core HEAD `671c848b`, `sw/` and `desktop/source/lib/` unmodified; `FlushInBuffer` ends `rSh.Insert(m_aInBuffer)` edtwin.cxx:1072; `InsertByWord`→`Insert`→`DelRight`→`Insert2` wrtsh1.cxx, gated by `SwViewOption::IsTypingReplacesSelection()` default `true` (Writer.xcs:2205–2211); `PasteData` skips deletion when `rSh.IsTableMode()` swdtflvr.cxx:1775; `StartExtTextInput` `DelRight` edtwin.cxx:5944). NOT verified by me: the LC_ALL=C "identical 15 arms" claim — `run-02-lc-all-c` has no reader output in the directory and `completion.json` says `protectedInputsUnchanged:false`; run-03 is in progress (11 entries in `saves/` vs 93). Treat it as unread until a reader output exists.
>
> Engine side of A: `expectOrderedUno(".uno:InsertText")`; `postUnoCommand(".uno:InsertText", {"Text":{"type":"string","value":…}}, true)`; reply `type:"inserted", method:"uno-insert-text", completion:"uno-command-result"` composed via `composeOrderedUno`'s void-command branch with the raw result payload recorded; `proof-absent-at-poll` stays an error. Not an editor action: do not touch `kMaxInternalEditorAction`/gesture tables. Known limit to register (not a regression — paste lacks it too): `.uno:InsertText` runs no `SvxAutoCorrect`; the keyboard does at autocorrect chars (edtwin.cxx:2616–2676). S5 types only `x`, so it is outside S5.
>
> ## 2. Finding 169
>
> Out of scope as a product change: it is a Writer defect in paste over a multi-cell PaM ring (source reading, untraced), the fix is a core patch, builds are owner-run, upstream is on hold, and no official-desktop reproduction exists yet. In scope in two ways: (a) a successor positive control — Ctrl+V of `x` over the table2 selection must still save `A1 cell textx` / `B1 cell textx#` on the successor (proves the paste route is unchanged and that the type fix did not come from B); (b) a named known limit in the successor's page honesty text. Do not couple 169's core fix to this successor.
>
> ## 3. Prospective acceptance for the typing route (default verdict if never done in brackets)
>
> - T1, per-instance over the generator's type population: for every type cell whose resolved reference is native (28 `native` + the `native-if-single-line` cells that resolve native), successor after-save paragraph texts equal run-03's after-save; comparator unchanged (ruling 3). [NE; successor has no S5 standing]
> - T2, tool-closed over the recorded replies of every counted type cell: `method == "uno-insert-text"` and `completion == "uno-command-result"`; any `method:"paste"` or proof-absent in a type cell is FAIL for that cell, not NE. [FAIL]
> - T3, tool-closed over the adapter's `source` literals: a test extracts every `source:` literal from `input/input-adapter.js` and asserts each is in the SDK mapping; runtime unknown non-empty source → `INSERT_ORIGIN_UNKNOWN`. Dynamic check: add `source:"fake"` to a scratch copy → red. [FAIL]
> - T4, per-instance over the existing paste/replace-selection/paste-markdown checks named from the closure: byte-identical expectations PASS on the successor. [NE]
> - T5, both browsers, 3/3 each, via REAL key events (CDP typing, not `commitText`): table2 typed `x` → A1 `` / B1 `x`; table2 Ctrl+V `x` → `…textx` / `…textx#` (169 control). [NE]
> - Red controls before any counted S5 run: (i) map `beforeinput` to the old export in a scratch SDK → T2 red; (ii) a reply with `method:"uno-insert-text"` but no UNO_COMMAND_RESULT → NE/FAIL, never PASS; (iii) the v23 counted-02 `shift-Right@cell-end/type` page fed to the successor judge → FAIL (judge sees the route); (iv) T3's fake-source mutation; (v) every T2/T3 guard removal turns its control red. Then the two-browser preparation, freeze bindings, fresh directory.
> - Counting (§9): no clean successor population exists, nothing resets; cutoff = first complete clean S5 population per browser.
>
> ## 4. Revalidate on the successor vs stays v23-scoped
>
> Re-run on the successor before any successor claim: fresh full S5 (both browsers, new directory, zero credit from counted-01/02 and preps), R1 144, S1–S4 234, the four product arms, and the host count chain per the batched-count rule (this IS the engine change the batch was waiting for; list accumulated uncounted changes in the handoff). Stays v23-scoped as v23's record: `e5cf298e` R1, counted-02 stop, four-arm `431bce12`, certificate 05. Reusable unchanged because they are not product-bound: run-03 native type oracle (hash-bound to the plan), Astra A deletion partition, f168 native routes. Ruling 3 and Astra A are not touched; no narrowing is requested.
>
> ## 5. Measurements before implementation, with pass conditions
>
> - M0 (frozen v23, cheap): confirm the S5 runner's `text:x` reaches the engine through `HostInputAdapter.handleBeforeInput` (recorded insert request carries `metadata.source:"beforeinput"`), not a direct `commitText`. Pass: 100% of recorded type-cell inserts carry it; else the runner drives real keys first (harness-path-vs-user-path).
> - M1 (native, f168 harness extended; 1.6 s g++ under the 10-28 build authorization, check `uptime`/`pgrep -a make`, after run-03 finishes): arms `uno-insert-text` with `bNotifyWhenFinished=true` recording the UNO_COMMAND_RESULT payload; texts `x`, `xy`, `中`, `é`, U+1F600; shapes table2, table4, cell-caret, text; plus `key` vs `uno-insert-text` with `teh ` on text (autocorrect divergence, to register, not gate). Pass: result delivered 3/3 per arm with `commandName:".uno:InsertText"` (record `success`); every after-save equals the `key` arm's for the same text/shape except the autocorrect arm (recorded as the named limit); non-BMP inserted intact. Ordering is NOT claimable from native non-unipoll.
> - M2 (WASM, after the owner links the successor): preparation over all 84 type cells × 2 browsers: 0 `proof-absent-at-poll` for `.uno:InsertText`, every reply `method:"uno-insert-text"`, and the save after the reply contains the text; table2 equals run-03. Pass: 0 proof-absent and T5 holds; otherwise no counted run.

## Main-session verification (2026-10-28)

Checked by reading before acting on the ruling:

- Unipoll makes `.uno:InsertText` synchronous in the product: `desktop/source/lib/init.cxx` `doc_postUnoCommand` adds `SynchronMode=false` only under `!vcl::lok::isUnipoll()`; `probe_engine.cpp` start-up sets `SAL_LOK_OPTIONS` to include `unipoll`. The brief's "returned in 0.12 ms (queued)" was a native, non-unipoll observation; the correction is accepted.
- The origin is already carried to `document.insertText(text, options)`: `editor-shell/editor-session.js:93` (`commit: (text, metadata) => this.commitText(text, { metadata })`) and `:511`; `sdk/document-sdk.js:533` sends only `{documentHandle, text}`. `e1/editor-shell-bundle-v2.json` registers `editor-session.js` and `input-adapter.js` but not `document-sdk.js` or `sdk-worker.js`, so the change set the ruling names leaves the E1-C bundle untouched.
- The fact fable could not verify is now read: `../f168-native-routes/run-03-lc-all-c` (clean, protected inputs unchanged) read together with run-01 gives 0 problems and identical outcomes for all 15 arms (`reader-run-01-run-03.json`).
- The `success:false` prediction for UNO_COMMAND_RESULT is a source reading (`textsh.cxx:153–156` has no `rReq.Done()`; `unoctitm.cxx` `bSuccess = aItem.is()`); M1 records the actual value.

M0 and M1 results are appended below as they land.

## M0 result (2026-10-28): PASS, with one stated proxy

`wasm_sdk_probe/tools/census_f168_type_input_path.py` over every retained S5 type cell (`s5-counted-02`, `s5-counted-01`, `s5-prep-05`, `-06`, `-07`), output `m0-input-path-census.json`: **81 cells, 81 on the beforeinput path** (Chrome 77, Firefox 4), 0 failures. Per cell, after the last trusted Shift keydown on the sink: exactly one trusted `keydown x`, exactly one trusted `beforeinput` `insertText` data `x`, no `insertFromPaste`, and exactly one `insertText` request with text `x` posted after that beforeinput.

Proxy, stated: the ruling's pass condition names `metadata.source:"beforeinput"` on the recorded insert request, but v23's request payload carries only `{documentHandle, text}` (that omission is the thing being repaired), so the source literal is not on the wire. What the census reads instead is the event that `input-adapter.js` turns into `source: "beforeinput"` (line 259) and the single insert that follows it. On the successor, T2 reads the route itself from every reply.

Census red cases (scratch copies): beforeinput removed → exit 1 (`beforeinput after Shift: []`); its inputType changed to `insertFromPaste` → exit 1 (two problems named); empty directory → exit 1 (zero cells read).

## M1 result (2026-10-28): M1_PASS; one teardown anomaly recorded

Harness `wasm_sdk_probe/tools/f168_native_insert_text_m1.cpp` (includes the retained signature setup `1e29f73b…ef17` unchanged), built by `build_f168_m1_native.py` (`m1-build-01/`, binary `62860ff0…31b5`, after `uptime` load 0.05 and no `make`), run by `run_f168_m1_native.py` with the f168 runner's procedure (run-03 fixture and environment, pins before/after, one execution, 3 rounds, 38 arms). Reader `read_f168_m1_native.py`, output `m1-reader-01.json`: 0 structural problems, `table2/key-x` reproduces run-03's bound save, **verdict M1_PASS**.

- **Result delivered:** every `uno-insert-text` arm, every round, delivered `LOK_CALLBACK_UNO_COMMAND_RESULT` with `commandName: ".uno:InsertText"`. Its payload is `{"success": false, "result": {"type": "void"}, "wasModified": false, …}` in every case — the ruling's `success:false` prediction holds, so the successor's reply must take the result's presence as the proof (void-command policy), never `success`; `wasModified` is also false although the text changed, so it is not usable either.
- **Equal to the keyboard:** 16/16 pairs (shapes table2, table4, cell-caret, text × texts `x`, `xy`, `中`, `é`) give the same saved paragraphs for `.uno:InsertText` as for KEYINPUT; every arm stable in 3/3 rounds. E.g. table4 `中`: A1, B1, A2 cleared, B2 `中`, for both routes.
- **Non-BMP:** 4/4 shapes insert U+1F600 intact at the same place as `x` (table2: A1 ``, B1 `😀`).
- **Named limit (not a gate):** at the document end, the keyboard turns ` teh ` into ` The ` (replacement and sentence capitalisation); `.uno:InsertText` leaves ` teh `. Paste has no autocorrect either, so this is not a regression of the successor against v23; it is a difference from desktop typing that the successor must state.
- **Reader red cases** (`m1-reader-controls.json`, scratch copies): a key save copied over a uno save → M1_FAIL with three named failures; one round's UNO result removed → M1_FAIL naming that arm.
- **Anomaly, not investigated:** the native process exited **1** after printing its last record (all 114 records and 228 saves complete and hash-verified); `native.stderr` ends with one `Unspecified Application Error`, its only occurrence. The four earlier native runs today and native run-03 exited 0 with no such line. This harness is the first to post `.uno:InsertText` with `bNotifyWhenFinished=true`; whether that is related is unknown. It does not alter any recorded save, and it is native-only (the product does not tear LOK down this way), but it is open: if it recurs in a rerun it should become a finding before the engine relies on notify-mode results at shutdown.
- As the ruling says, nothing here is an ordering claim: native LOK in this run is not unipoll.
