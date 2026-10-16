# Review 1, seat opus: SPEC-M3-link-batch-v21 (draft)

Target: `specs/SPEC-M3-link-batch-v21.md` at `5b48dd95`. Read-only. I ran grep, sed and read-only Python only: manifest flattening, `arms.json` listing, and byte counts in the shipped `dist/profiles/e2-editor-v20/probe.wasm`.

Labels: **[src]** read in source (a byte search of a shipped artifact counts as this), **[doc]** stated in a doc, **[inf]** inferred. Paths are repo-relative. `wsp/` stands for `wasm_sdk_probe/` and `lo/` for `libreoffice-26-8/`.

## BLOCKING

### B1. The product engine is not unipoll. §3.1's last bullet and Q3 rest on a false premise (§3.1, §8 Q3)

Evidence:
- `wsp/src/probe_engine.cpp:15-17` says `#ifdef OXSDK_MAINLOOP_ENGINE` → `#error "OXSDK_MERGE_KEY_UNDO is not wired into OXSDK_MAINLOOP_ENGINE"`. The v20 rule defines `OXSDK_MERGE_KEY_UNDO` (`wsp/Makefile:1550-1554`), and v21 inherits it. [src]
- The `setenv("SAL_LOK_OPTIONS","unipoll")` the spec cites (`probe_engine.cpp:6667-6683`) is inside `mainLoopEngineThreadMain` (`:6656`). That function starts only `#ifdef OXSDK_MAINLOOP_ENGINE` (`:6756-6760`). [src]
- The product runs `engineLoop` on a `std::thread` (`:6238-6242`, `:6759`) with no LOK options. LOK therefore spawns `lo_startmain` (`lo/desktop/source/lib/init.cxx:8378-8384`). [src]
- The engine says so in its own comment: "The shipped and candidate profiles are built WITHOUT that define, so the product reaches this through engineLoop" (`probe_engine.cpp:2331-2333`). [src]
- A byte search of the shipped v20 `probe.wasm` finds `start.sal_lok_options` ×0, `mainloop.runLoop` ×0, `:unipoll` ×0, and `start.libreofficekit_hook_2` ×1. [src]
- The project already treats unipoll as an *unadopted* candidate for ordered commands (`specs/SPEC-M3-link-batch.md:401`, `:429`). Finding 137's premise is a stalled core *thread* (`findings/137-…md:22-23`, `:72`). The native README repeats the error (`findings/evidence/link-batch-v21/native/142-ctrl-home-end/README.md:49`, `:237-239`). [doc]

Consequences:
- **Key path.** On the product, as in the native harness, a posted Ctrl+Home takes two hops. The first is the KeyInput user event (`lo/sfx2/source/view/lokhelper.cxx:1278-1287`, non-unipoll branch). The second is `AsyncAccelExec` (`lo/svtools/source/misc/acceleratorexecute.cxx:213-226`, reached through `KeyToView`, `lo/sw/source/uibase/docvw/edtwin.cxx:2420-2444`). [src]
  - So the native B/Q ordering result describes the product's topology, not a property of the harness. [inf]
  - Native callback timings also transfer in shape; WASM is only slower. [inf]
- **Reachability in the product.** The engine posts nothing behind a move until the move completes. A reorder therefore needs an early completion. [inf]
  - The 250 ms `verified-move-readback` is that early completion when the core thread stalls for more than 250 ms. It serialises the engine *cache* and does not read core (`probe_engine.cpp:2335-2361`). [src]
  - Every synchronous call made next then runs before the queued `GoToStartOfDoc`: typing's `paste`, the Markdown `paste`, the `.uno:` formats, and `.uno:Delete`. [inf]
  - This is finding 137 class 6. The difference is the size of the error: typed or pasted text lands at the pre-move caret, which can be anywhere in the document, not one step away. [inf]
  - It is most likely right after item 2's large paste, while core is busy with layout and callbacks. That is the ordinary sequence "paste, Ctrl+End, type". [inf]
- **D2 cannot answer Q3.** D2 waits for the completion before the Backspace, and the session queue does the same, so no pending dispatch is ever exercised. [src: spec §5 D2; `findings/evidence/host-0.2.20-hand-test/probe_10_14n.py:361-373`]

Change:
- Strike 「這不轉移到 WASM … 一律不拿來當 WASM 的證據」 and Q3's 「unipoll 推論是」.
- Append a correction to the 142 README, in English and append-only.
- Name **L-142-readback-overtaken**: Ctrl+Home/End answered by the readback during a stall, so the next synchronous command lands at the pre-move caret. List it in the release text beside 137.
- Add one recorded, ungated arm: N runs, both browsers. Paste the M6 corpus, then press Ctrl+End and type a marker without waiting. Record the completion kind and where the marker lands.
- Owner's choice:
  - **A**: keep 250 ms and accept the named limit.
  - **B**: a longer readback deadline for internal ids 24/25 only. The cost is that wait on every press already at the boundary.

### B2. The defaults for item 2 cannot be executed after the link, and M6's fallback needs another link (§4.2, §4.4, §5 M1–M4, M6)

- The manifest is minted in the owner's link step. The recipe runs the builder with the declaration flags (`wsp/Makefile:1582-1603`), and §4.4 adds `--paste-markdown` to v21's recipe. M1–M8 can only run afterwards (`handoff/PLAN-2026-10-16-link-batch-v21.md:155-156`). [src][doc]
- M1's default 「manifest 不宣告 pasteMarkdown」 (and M2–M4's 「同 M1」) would therefore mean re-minting `e2-editor-v21` after X1 and the archive: two artifacts under one name. [inf]
- §4.2 puts the 64 KiB refusal in the engine, so M6's 「降成 16 KiB」 needs a relink. [doc]

Change: choose one before the criteria are pinned.
- **A**: the engine keeps 64 KiB as a hard cap, and the *operative* limit lives in the SDK and page (a new shell generation, no relink). A red M6 lowers the shell limit. Item 2's default becomes: the page has no entry, the manifest still declares the export, and the SDK path stays callable, named as such.
- **B**: the v21 link does not pass `--paste-markdown`. The declaration ships in a later profile after M1–M8 pass.

### B3. D1's population is wrong in both directions (§5 D1, §8 Q2)

Read from `findings/evidence/link-batch-v21/native/142-ctrl-home-end/out/arms.json`. [src]

- **Excluded, but the product can reach them:**
  - every `sec-*` arm places the caret with Down and Right only (`k1024x2,k1027x6`);
  - `hf-home-hdr-click` enters the header with the engine's own click (README:315). That click is the product's `placeCaret`.
- **Included, but the product cannot send them, or they are red by construction:**
  - `red-*-k1*` and `ctl-k1*`, which are K1 reads;
  - `b2b-*`, which are back-to-back posts;
  - `q-*`, which post from inside a callback;
  - `place-*`, which press no Ctrl key;
  - the `ctl-*` controls;
  - `red-home-bksp`, `red-end-del` and `x-*-home-bksp`. In the product the Backspace goes through the barrier and C. On `x-*` the native result is `Number On/Off` or `Apply attributes`, while the product's is `verified-boundary-noop`.

Change: generate the population from the script grammar, not from fixture names.
- An arm is in D1 iff every step is one the product can send: `k1024|1025|1027|1028|1029`, `r…`/`s…` ranges through select-range, `c…` clicks through place-caret, and `M…=9220|9221`.
- An arm with a `bksp`, `del`, `K`, `J`, `B`, `Q` or `u.` step is out.
- Record each excluded arm with the rule that excluded it.
- `x-*-home-bksp` goes to S17.

### B4. M1's population is red by construction (§5 M1)

`…/native/markdown-paste/tool/corpus/` holds three items that cannot pass [src]:
- `C1.md`, the text/plain control;
- `M8-utf16le.bin`, UTF-16 bytes, which is not text input for a string API;
- `M14b.md`, 262,262 bytes, above the 64 KiB refusal.

Change: exclude them by rule. C1 belongs to M7, `.bin` files are not text, and anything over the limit belongs to M3/M6. Pin the input document by its sha (`tool/inputs/empty-template.odt`, `a3354bae…`).

## SHOULD

**S1. No D criterion can see a wrong completion (§5 D1–D4).**
- Mutation: give 24/25 `requiredCallback = LOK_CALLBACK_TEXT_SELECTION`, as the extend branch does (`probe_engine.cpp:5706-5708`). Every press then completes by the 250 ms readback; positions stay right and D1–D4 stay green. [src][inf]
- Granting range gestures has the same effect: the move completes on the first, empty `TEXT_SELECTION` with a stale caret, and D4 compares only the final marker. [inf]
- Change: derive a per-press clause from `arms.json`. [inf]
  - A press with a native cursor callback completes `documented-callback-*`.
  - A silent native press completes `verified-move-readback` in under 1000 ms. This replaces D3's two hand-picked positions.
  - For every press, the reply's caret equals `editor-get-state` read ≥500 ms later, the §10.2 S2 reference.

**S2. Nothing witnesses the gesture mask.**
- The worker ignores the status of `oxsdk_editor_set_action_gestures` (`wsp/sdk/sdk-worker.js:1253-1254`; `callStatus` only returns the number, `:541-543`). [src]
- If `kMaxExternalAction` stays at 21, the call for 22/23 returns `INVALID_ARGUMENT` silently (`wsp/src/editor_api.cpp:175-176`). Internal 24/25 then keep "all gestures" (`probe_engine.cpp:7073-7092`). The page clicks first anyway, so nothing goes red. [src]
- `wsp/e2/expected-gesture-offers.json` still names `e2-editor-v8`, so a manifest that granted ranges to 24/25 is also unseen. [src]
- Change:
  - the worker fails init on a non-OK mask status (the worker changes in this batch anyway);
  - add an SDK arm: `move-document-*` on a range → `EDITOR_FORMAT_GESTURE_UNSUPPORTED`, document unchanged;
  - repoint the expectation file to v21, with `["collapsed"]` for both actions.

**S3. The shell lists are hand-kept and unguarded.**
- `_validateInherited` has no final branch. An appended action that belongs to no class is accepted with no postcondition at all (`wsp/editor-shell-v2/narrow-editor-v2-client.js:287-335`). [src]
- `BOUNDARY_CAPABLE_MOVES` (`narrow-editor-v2-session.js:81-84`) also decides `actionMutates` (`:1091-1093`) and the view-only refusal (`:1113-1117`). If 22/23 are left out, every Ctrl+Home is a mutation: it sets dirty, triggers autosave (finding 098 again), and view-only mode refuses it. No D criterion opens a view-only document or reads `dirty`. [src][inf]
- Change:
  - a form-two unit test: every ABI-5 appended action belongs to exactly one postcondition class, and `BOUNDARY_CAPABLE_MOVES` equals the set whose postcondition is `MOVE_COMPLETIONS`;
  - one arm: in a view-only document Ctrl+End moves, and `dirty` stays false.

**S4. The Markdown postcondition has no red case and no failure disposition (§4.2).**
- Mutation "the postcondition always passes" leaves M1–M8 green. Natively no input was found for which `paste()` adds no Undo action; even M13 adds one (README:107-109). There is no WASM red today. [doc]
- 「否則回錯，revision 不動」 leaves the queue item failed. The session then sets neither `dirty` nor the stamp (`wsp/editor-shell/editor-session.js:299-326`), although core may have changed. [src]
- The contract already declares `postDispatchFailureDisposition: "rollback-to-checkpoint"` (v20 manifest; `wsp/tools/build_e2_b_profile.py:152`). [src]
- What happens when the Undo read fails before or after the paste is unspecified. The merge path has `undo-read` and `key-read` for this (`merge_key_undo.hpp:224-225`, `:368-418`). [src]
- Change:
  - write the judge as a pure header function with a model test:
    - unchanged payload → error;
    - changed with 0 actions → error;
    - changed with ≥1 action → ok;
    - read failure before the paste → refuse undispatched;
    - read failure after the paste → post-dispatch failure;
  - name the error code, and say it takes the manifest's rollback disposition;
  - look natively for an input with no effect and no Undo action (candidate: caret in a protected section) and make it M9's WASM red.

**S5. M3 pins neither the boundary nor the unit.**
- Mutations that survive [inf]:
  - the limit counted in UTF-16 units or characters instead of UTF-8 bytes;
  - 64,000 instead of 65,536;
  - a whitespace set wider or narrower than md4c's.
- Change:
  - arms at 65,536 and 65,537 UTF-8 bytes, built from CJK at 3 bytes per character;
  - define 「空白」 as md4c's whitespace set and unit-test the predicate over all code points;
  - state which layer M3 drives (the SDK directly, or the page).

**S6. M5 measures the native hazard, not the WASM one, and its fallback is incomplete.**
- Both arms use `127.0.0.1`. On WASM, sockets go through Emscripten's emulation and the host's CSP, so a hostname or an `https` URL may behave differently. [inf]
- The rewrite `![alt](url)` misses reference-style images (`![a][r]` plus `[r]: url`), which md4c also turns into an image. They were not in the native corpus (README:234). [inf]
- 「保守比對」 is not written down, so the rule would be designed after the red (CLAUDE.md §2). [doc]
- Change: add an https hostname arm and run M5 on the host route. Write the rewrite now, including reference images; or decide to rewrite always.

**S7. Holding Ctrl+Home queues 250 ms per repeat.**
- At the boundary every press after the first is silent, so each one waits out the 250 ms readback. Key repeat is about 30 ms (`wsp/web/e2-editor-app.js:2984`), and the move keys have no repeat handling (`:2944-2980`). [src]
- A one-second hold of Ctrl+End is about 33 presses, about 8 s busy after release. [inf]
- Change: drop `event.repeat` for 22/23, named as a limit (a held Ctrl+Home in a table then steps only one level), or hold while unanswered as finding 141 does. Add a hold arm.

**S8. The pin list is missing (§12.5's rule: generate it with grep and record the command and its output).**
- Known now [src]:
  - `wsp/tests/editor_abi_header_test.cpp:20` asserts `== 4u` (syntax-checked at `wsp/Makefile:3496`);
  - `wsp/e2/relink-queue-v3.json` rows `p1-4-abi-3` and `p1-7-header-test` (`blocksRelink: true`);
  - `wsp/e2/expected-gesture-offers.json` (still v8);
  - `wsp/tools/check_e2_b_inventory.py` (V1/V2 enums only, profile v2);
  - `wsp/editor-shell-v2/tests/manifest-reachability.test.mjs` (v2);
  - three `.d.ts` files and `declaration-drift.test.mjs`;
  - `tests/test_e2_editor_v4_profile.py`;
  - the session's `ACTIONS` (`narrow-editor-v2-session.js:59`).
- v8–v20's preprocessed output stays equal only if these sit under `OXSDK_E2_V21_LINK_BATCH`:
  - the ABI constant;
  - the V4 wire enum;
  - the discovery enum;
  - the new `sdk_api.h` declaration.

  Say so in the spec.
- Before M1-1 runs, name its two bases and predict the carriers (probe_engine, sdk_api, editor_api). v20's surprise was editor_api (SPEC-M3-link-batch §15.3). [doc]

**S9. 「以 v4 產生器為底（import）」 cannot be implemented as written.**
- v4 is one `main()` that builds its own argparse parser and reads the module globals `ABI_VERSION` and `action_map()` (`wsp/tools/build_e2_editor_v4_profile.py:81`, `:191-202`, `:452-454`, `:567-575`). [src]
- Importing it leaves the new flags unparseable, and the ABI and the ids are reachable only by monkeypatching.
- Change: state the mechanism. For example, v5:
  1. patches `v4.ABI_VERSION` and `v4.action_map`;
  2. strips its own flags from `argv` and calls `v4.main()`;
  3. adds its leaves, rewrites the manifest and reprints the digest.

  The v21 manifest rule lists both builder files as prerequisites.

**S10. The C field is inert in v21, and the spec ruled on the §34.4 category itself.**
- Nothing reads the field: the tools stay unchanged and product code does not read it (§4.3).
- The plan asked for a ruling on the category (`handoff/PLAN-2026-10-16-link-batch-v21.md:92`). The spec rules on it itself (CLAUDE.md §8). [doc]
- §1's stated value, tools that are honest about C, is not delivered by this batch.
- Change: get the ruling, or defer the field to the batch with its first reader. If it is kept, write "inert in v21" and register it under CLAUDE.md §3 as 「沒有東西可守」.

**S11. D4's default brings finding 142 back on ranges.**
- 「範圍上不綁」 means the textarea eats Ctrl+Home and the range stays. The next Backspace then goes out as `delete-selection` (`wsp/web/e2-editor-app.js:2648-2651`) and deletes the range. [src][inf]
- Change: the default is `moveFromPoint` anyway (native r-* collapse 6/6), or take the key and say "not supported". It must not fall through.

**S12. No criterion checks that the view follows Ctrl+End.**
- Native arms are single-page (README:248). [doc]
- Change: one arm on the 60-page P1 fixture (§10.8). After Ctrl+End, the engine caret lies inside the viewport and `#page-status` names the last page. Judge from state, not pixels.

**S13. Run counts are not written.**
- Change: N = 3 per arm and per browser for D1–D4 and M1–M7, and pass means N/N (CLAUDE.md: intermittent defects). The native arms ran 3/3.

**S14. Markdown positions the product reaches but nobody measured.**
- A table cell (including a GFM table pasted into a cell), a header or footer, and a range across cells (README:234). [doc]
- Change: native arms first, or name L-md-unmeasured-positions with these cells.

**S15. Q1 is still open while M1, M7 and M8 depend on the entry point.**
- Change: resolve Q1 before pinning, or pin the criteria per option.
  - Under A, add an arm: type a marker in the dialog, cancel, save → the marker is absent. Also state that the dialog's input never passes through the E1-C adapter.
  - Under B, add a permission-prompt arm per browser on the host route.

**S16. Nothing checks the paste's mutation bookkeeping.**
- Mutation: enqueue `pasteMarkdown` as a non-mutation. `dirty` is then never set and autosave is skipped, but M1 saves explicitly and stays green (`wsp/editor-shell/editor-session.js:299-310`). [src]
- Change: an arm in which, after a paste, `dirty` is true and autosave fires.

**S17. Two existing residuals are now one key away.**
- x-lc: Ctrl+Home then Backspace at a bulleted, numbered or indented first paragraph. The product answers with C's no-op after 2.25 s; Writer does `Number On/Off` or `Apply attributes`. §3.1 says so, but no criterion covers it. [doc]
- Inside a table, Ctrl+Home goes to the cell start (L-142-steps). A Backspace there is the cell-boundary refusal and reopen (finding 136; `boundaryRejectionRequiresFreshWorker: true`). [inf]
- Change: record both on v21 as ungated arms, and list them in the release text with L-142-steps.

## NOTE

- **N1.** The client always sends the current revision (`narrow-editor-v2-client.js:368-369`), so leaving 24/25 classed as mutating (`editorActionMutates`) changes nothing observable. Drop the item, or test it through the SDK with a stale `expectedRevision`. [src]
- **N2.** The new binding sits before `if (accel) return;` (`wsp/web/e2-editor-app.js:2950`), but today's `shiftKey` check comes after it (`:2960`). Exclude Shift there, and `isComposing` as Enter does (`:2942`). D5 should test both, against the real v20 manifest rather than a fake one. [src]
- **N3.** Interplay with findings 141 and 144 [inf]:
  - Ctrl+Home followed by two or more quick Backspaces: `stateAtSend` holds the pre-move snapshot (`:2760`), so `boundaryNoopStands` fails and one held press is released. That costs two C windows, about 4.5 s.
  - A range, Ctrl+Home, then a quick Backspace: the shape read at send is the range, so `delete-selection` is sent and refused at the collapsed caret (`probe_engine.cpp:5528-5537`), with a toast. No data is lost; register it.
- **N4.** Ctrl+Home while C's window is open is queued behind the delete, because the drain is serial. It also clears a late-K1 selection if one landed. [inf]
- **N5.** `verified-move-readback` is a serialised cache, not a fresh read of core (`probe_engine.cpp:2335-2361`). Do not let 「讀回」 be read as verification. [src]
- **N6.** v20's manifest rule pins the tree's worker (`wsp/Makefile:1590`), so it fails once the worker is edited. That is intended; say so, or point the rule at `build/archive/e2-editor-v20-313b08d5-worker-478d0da1/`. [src]
- **N7.** ABI 5 was once pencilled in for extend (SPEC-M3-link-batch §10.8 「editor ABI 是 5」, §12.5 「4→5」). Extend now needs ABI 6. Append a one-line correction there. [doc]
- **N8.** M4 compares saved text, but the native run compared structure (README:107). Use `md_structure.py --compare`, and take positions P1–P7 from the native arms by tool rather than picking four by hand.
- **N9.** M6's 10 s is not derived from anything; the SDK timeout is 30 s (`wsp/sdk/document-sdk.js:151`). Say what is timed: the engine reply, or the page's busy-to-ready time. [src][inf]
  - Every LOK callback is forwarded to the worker as JSON (`probe_engine.cpp:2575-2584`).
  - With a11y on, a 64 KiB paste would send about 10,000 `CORE_LOG` events (2,684 natively for 16.6 KB).
- **N10.** C's gate cannot tell the variants apart (window or immediate). "A new value for a new variant" is a hand rule; name it L-C-decl-variant.
- **N11.** The Undo payload can change without the paste [inf]. A key queued by `handleInsertText`'s `postKeyEvent` fallback (`probe_engine.cpp:3242-3256`) can add or merge a "Typing" action between the two reads. This is finding 137's class and rare.
- **N12.** X1: the two actions are six leaves (`id`, `gestures[0]` and `limits[0]` for each), so they need six `--declared-new-leaf` flags. Write them in the runbook beforehand. `--declared-changed-leaf OLD->NEW` must also parse values that themselves contain `->`.

## Source checks the brief asked for (short answers)

- **Key path.** It is the right route.
  - It matches select-all (`probe_engine.cpp:5674-5691`).
  - `postUnoCommand` from the engine thread would jump every queued key, so it is worse.
  - Nuance: under threaded LOK the key path is FIFO only with other accelerator keys. One-hop keys handled in `SwEditWin::KeyInput` (Backspace or Delete at labels and numbered starts) can overtake it. In the product the engine posts one only in merge-key, after proofs. See B1. [src][inf]
- **"unipoll ⇒ synchronous".** True of LOK's source, false of our product; see B1.
- **Collapsed-only.** The reason is valid.
  - On a range, native sends an empty `TEXT_SELECTION` and then the cursor (README:30-32), so completing on the first callback reproduces the §9 defect.
  - `moveFromPoint` is the existing, generic range path (`wsp/web/e2-editor-app.js:2973-2979`, `:3057-3075`).
- **`BOUNDARY_CAPABLE_MOVES`.** Membership is right; the set itself is unguarded (S3).
- **`.uno:Undo` payload.**
  - The payload lists every action with `index`, `comment`, `viewId` and `dateTime` (`lo/svl/source/undo/undo.cxx:1310-1335`).
  - "Holds at the limit" is right, because the list shifts. An identical payload after a real paste would need identical dateTimes across the whole stack, which cannot happen.
  - It can change without the paste only through a queued async key (N11).
  - Read failures are unspecified (S4).
- **Whitespace refusal.**
  - Enough to keep empty data from reaching `ERRCODE_IO_INVALIDCHAR` and the dialog (`lo/sw/source/filter/md/swmd.cxx:931-934`).
  - Not enough for inputs that produce nothing; that case is named as L-md-noop-input.
- **v4 untouched.** Right under finding 042: v20's manifest rule lists the v4 builder as a prerequisite (`wsp/Makefile:1582-1589`). The mechanism is S9.
- **Undeclared deltas.** None found in the v20 manifest's flattened leaves beyond what §5 I1 lists. The risk is outside the manifest (S8).

## Per criterion

| crit | (a) mutation that stays green | (b) form | (c) default | (d) run-time judgement |
|---|---|---|---|---|
| D1 | wrong completion callback (S1); range grant (S2); out of `BOUNDARY_CAPABLE_MOVES` (S3) | intended tool-closed; population wrong (B3) | actionable, but the SDK offer stays live | "本文可達" (Q2) |
| D2 | none for the arm itself; cannot see ordering (B1) | one red case | ok | none |
| D3 | completion kind not pinned (S1) | hand-enumerated; generate from silent native presses | ok | none |
| D4 | stale reply on a range grant (S1/S2) | hand-enumerated; use every `r-*` arm | brings 142 back (S11) | none |
| D5 | binds Ctrl+Shift+Home (N2) | unit test with a fake manifest | ok | none |
| M1 | postcondition always passes (S4) | tool-closed; population wrong (B4) | not executable (B2) | depends on Q1 (S15) |
| M2 | n/a (the comparison can go red) | one item | not executable (B2) | none |
| M3 | char vs byte limit; off-by-boundary (S5) | hand-enumerated; generate the whitespace set from md4c | not executable (B2) | none |
| M4 | text-only comparison (N8) | four hand-picked positions | not executable (B2) | none |
| M5 | regex misses reference images (S6) | two hand-picked arms | rewrite rule unwritten | yes: 「保守比對」 |
| M6 | char vs byte limit | one arm | needs a relink (B2) | 10 s not grounded (N9) |
| M7 | none found | two arms | ok | none |
| M8 | worker gate dropped (SDK gate still throws) | unit test | ok | none |
| C1 | none found | three unit cases | ok | none |
| I1 | none in the manifest; carriers unnamed (S8) | X1 is form two | ok | M1-1 bases chosen later (S8) |
| K | n/a | chain | ok | §17.4 manual reading, as before |

## Summary (10 lines)

1. BLOCKING B1: the product engine is not unipoll (`probe_engine.cpp:15-17`, `:2331-2333`; byte search of v20 wasm), so §3.1's "native ordering does not transfer" and Q3 are false.
2. B1 consequence: Ctrl+Home is two hops, as in the native run. A 250 ms readback during a stall lets typing or pasting land at the pre-move caret anywhere in the document. Name L-142-readback-overtaken and add a recorded arm.
3. BLOCKING B2: the item-2 defaults ("manifest 不宣告", "降成 16 KiB") cannot be carried out after the link. Move the operative limit into the shell, or do not declare at the v21 link.
4. BLOCKING B3/B4: D1 excludes reachable arms (`sec-*`, `hf-home-hdr-click`) and includes unsendable or red-by-construction ones. M1 includes C1, the UTF-16 file and M14b. Generate both populations by rule.
5. SHOULD S1–S3: wrong completion callback, a missing gesture mask (`kMaxExternalAction`, the worker ignores the mask status), and missing shell list entries all stay green. Add per-press completion and reply-freshness clauses, a worker init check, a v21 gesture expectation and closed-list unit tests.
6. SHOULD S4–S6: the Markdown postcondition has no red case and no post-dispatch disposition (the manifest says rollback-to-checkpoint). M3 does not pin the byte boundary or the whitespace set. M5 tests only 127.0.0.1, and its regex misses reference images.
7. SHOULD S7, S11, S12: a held Ctrl+Home queues 250 ms per repeat; D4's default brings 142 back on ranges; no criterion checks that the view follows Ctrl+End in a long document.
8. SHOULD S8–S10: write the grep pin list (header test 4u, relink-queue rows, gesture expectation still on v8, `.d.ts`). Specify how v5 imports v4's monolithic `main()`. The C field is inert in v21 and needs the §34.4 ruling the plan asked for.
9. SHOULD S13–S17: N runs; unmeasured Markdown positions; Q1 must be settled before pinning; check `dirty` after a paste; L-C-number-or-indent and the cell-start refusal are now one key away.
10. Confirmed sound: the key path over `.uno:` (same shape as select-all), collapsed-only plus `moveFromPoint`, `BOUNDARY_CAPABLE_MOVES` membership, Undo-payload change at the stack limit, a separate v5 builder under finding 042, and the X1 changed-leaf flag (with red cases).
