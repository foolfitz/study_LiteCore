# Adversarial review before the v19 link (opus, 2026-10-08, repo HEAD daa5de61)

Read-only on the repository (`git status` clean before and after). Experiments ran on a symlinked mirror in the scratchpad (`scratchpad/mirror/`, `tools/` and `tests/` copied, everything else symlinked; `python3 -B`, `TMPDIR` in the scratchpad). Script: `scratchpad/exp_reader.py`, output `scratchpad/exp_reader.out`. The three unit modules pass on the mirror (81 tests OK). The only other commands were `make -n` and `what_the_link_ships.py` (`git show` plus `-E` preprocessing into the scratchpad), both read-only.

## SUMMARY

Counts: **BLOCKING 2, SHOULD 6, NOTE 11.** All BLOCKING items are in the counted reader (section 2). The engine fix, the page fix and the X1 checker have no defect that can produce a wrong verdict.

- **B1** `judge_counted_m2.py:547` (`--browsers`): `--browsers chrome`, with no Firefox report in the directory at all, exits 0 and prints `VERDICT PASS`. Demonstrated through the CLI (E1c). X7's "reader exit 0" therefore does not imply two browsers.
- **B2** `judge_counted_m2.py:365-366, 409-421`: "counted" and "bound" are taken from each report's own `binding`/`bound`/`runner`. They are never compared with the committed `run_merge_wasm_shakedown.BINDING` or with the runner file's hash.
  - The synthetic green passes (exit 0) while `m.BINDING is None`.
  - With all ten reports given an all-zero binding and runner `not-the-runner00`, the reader still exits 0 with `VERDICT PASS` (E2).
- **SHOULD:**
  - **S1:** the link command does not pin `LOSRC`/`LOBUILD`/`EMSDK_ROOT`/`EXTRA_DEFINES`/`EXTRA_OBJECTS`. All are `?=` and come from the environment, and no post-link gate can see them (M1-1 forces `EXTRA_DEFINES=`).
  - **S2:** "What this link ships" in the runbook is read, not measured. I measured it with `what_the_link_ships.py --since 1990bb64 --variant merge-v15`, and it holds: only `probe_engine` changes, and the diff is exactly the `66e5c0af` hunk.
  - **S3:** M1-1's exit 0 is weaker than X2's text, because a carrier's non-engine objects may differ (`check_merge_key_undo_scope.py:162` against `:167`).
  - **S4:** the binding pins 2 of the 13 shell-bundle modules, and not `e2-editor.html`.
  - **S5:** M2-3's "generation +1" is read only at toast-window close; a second reopen after it passes (E3).
  - **S6:** M2-4's native reference lives only under `build/`, unhashed. Spec §7's "R0 report directory and input sha256" (§7 原文「R0 的報告目錄與輸入 sha256」) is not in the binding.
- **NOTE** highlights:
  - §31.5's "completion between KEYINPUT and KEYUP" cannot happen, because the headless yield drops the SolarMutex only when about to sleep. The comment's safety argument is right, and stronger than written.
  - Negative latencies pass (E5).
  - `completedAt` is no longer a completion signal, and a missing stderr file passes.
  - M2-4 and M2-1b are never paired with a control.
  - X1's wasm clause proves "a different file", not "contains the fix"; X7 does that.
- **No defect found:** section 4 (engine fix, items a-d), section 5 (page fix), section 6's X1 checker and its tests, and the Makefile v19 block. Section 3's runner has nothing BLOCKING: `is_counted`, `teardown`, `mode_schedule`, `limit_clauses` and the drained log are clean.
- **Correct run turned red:** no scenario found in which a correct counted run is made red, other than environmental stderr noise.

## BLOCKING

### B1. A one-browser reader run is a counted PASS

- **Where:** `wasm_sdk_probe/tools/judge_counted_m2.py:547` (`--browsers`, `nargs="+"`, `choices=BROWSERS`), the loop at `:522`, and the verdict at `:532-539`.
  - The docstring (`:33`) says "0 every criterion PASSES on every browser". That means every browser *asked for*.
  - Spec §32.2 defines X7's "reader exit 0" as "this one without `--uncounted`" (原文「這支**不帶** `--uncounted` 的 exit 0」); nothing else is pinned.
- **Predicate attacked:** X7 = "3 rounds × two browsers … reader exit 0 and a passing VERDICT line" (原文「3 輪×兩瀏覽器 … 判讀器 exit 0 且 VERDICT 行為過」).
- **Scenario:** Firefox's counted chain crashes, or comes back red, or was never run. The reader is run as `--browsers chrome`: exit 0, `VERDICT PASS`. The VERDICT line names no browser, so the record "exit 0, VERDICT PASS" cannot be told apart from a two-browser pass.
- **How shown (`exp_reader.out`):**
  - E1 deletes every `*firefox*` report and `.docs` from the synthetic green. The library call gives `exit 0 | VERDICT PASS`.
  - E1c runs `judge_counted_m2.py --dir D --profile … --browsers chrome` through the CLI: `exit 0 | VERDICT PASS`.
  - E1b, the same directory with default browsers, gives exit 3, as it should.
- **Remedy (cheap):** drop `--browsers`. Or make any browser set other than `BROWSERS` exit 4, like `--uncounted` ("not a counted verdict"). Print the judged browsers, the profile and the binding's wasm sha in the VERDICT line. Write the exact X7 command into §31.4.

### B2. "Counted" and "bound" are self-attested by each report; the committed binding is never consulted

- **Where:**
  - `judge_counted_m2.py:365-366`: `counted = report.counted is True and report.binding is not None`.
  - `:409-421` (`together`): one runner string, one binding string, and `bound == binding` inside each report.
  - Nothing compares `report["binding"]` with `run_merge_wasm_shakedown.BINDING`, or `report["runner"]` with `sha256(run_merge_wasm_shakedown.py)[:16]`.
  - The runner sets `counted` from whatever `BINDING` the running copy holds (`run_merge_wasm_shakedown.py:1190`).
- **Predicate attacked:**
  - Spec §7 and §30.2: the binding is written into the runner's constants before any counted run (原文「綁定（任何計數執行之前寫進 runner 常數）」).
  - §30.1 and `test_nothing_is_bound_before_v56`: nothing counts while `BINDING` is None.
  - The reader's docstring `:33`: "the reports are the counted run (counted, bound, one runner)".
- **Scenarios:**
  - (a) A counted chain run from a working copy whose `BINDING` was edited and not committed, or amended afterwards. The reports say `counted: true`, and the reader passes them.
  - (b) X7 is voided, v57 is frozen and `BINDING` is re-committed (§31.4's "X7 作廢" path). The old v56 directory still judges PASS, because its reports agree with themselves.
  - (c) A runner whose clause-feeding code (placement, latency `t0`, `await_delete`) was edited produces "one runner" reports that pass. The reader recomputes clauses only from fields that runner wrote.
- **How shown:**
  - E0: the synthetic green (`BINDING = {"wasmSha256": "w"*64, …}`, `runner: "synthetic000000"`) exits 0 with `VERDICT PASS` while `m.BINDING = None`. That is a counted PASS in the committed state where §30.1 says nothing can count.
  - E2: every report's `binding`/`bound` is replaced by all-zero hashes and `runner` by `not-the-runner00` (the real runner is `bd684ebabe07263e`). Result: `exit 0 | VERDICT PASS`.
- **Remedy:** in `identity()`/`together()`, require `report["binding"] == m.BINDING` (and `m.BINDING is not None`) and `report["runner"] == sha256(Path(m.__file__).read_bytes()).hexdigest()[:16]`; otherwise NOT DONE.
  - Because `BINDING` lives in the runner file, the runner hash alone already pins the binding, the observer and every clause-feeding function.
  - The synthetic green test then patches `m.BINDING` and the expected runner hash, and gains a red case for each.
  - `--profile` becomes derivable from the binding and can go.

## SHOULD

### S1. The link command inherits five environment-overridable inputs that no gate after the link can see

- **Where:** `wasm_sdk_probe/Makefile:1-4` (`LOSRC ?=`, `LOBUILD ?=`, `EMSDK_ROOT ?=`), `:1085` (`EXTRA_DEFINES ?=`, a documented mechanism for a11y variants), `:1090` (`EXTRA_OBJECTS ?=`). `handoff/RUNBOOK-relink-v19.md` §2 runs `make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v19/sdk-manifest.json` with none of them pinned.
- **Why no gate catches it:**
  - `check_merge_key_undo_scope.py:55` forces `EXTRA_DEFINES=`, so X2 measures the empty case, not the owner's shell.
  - X1 compares the manifest, worker and exports; it is blind to compile defines and to the core linked in.
  - `.coreCommit` in the manifest is copied from `sdk/v18-writer-review-manifest.json`, not measured.
  - The pre-link gate "v15 and v19 compile commands identical" (`gates.txt`) was taken in the agent's shell.
- **Scenario:** the owner's terminal still exports `EXTRA_DEFINES=-DOXSDK_A11Y_PARAGRAPH_TEXT`, or `LOBUILD` from an a11y-core session. v19 links with it, and every identity check stays green. A link cannot be undone (finding 036).
- **How shown:** by reading. My shell has no such variables. `find` over `$(LOBUILD)/instdir/program` and `workdir/LinkTarget` for files newer than the v15 link (2026-10-07 10:00) returns 0, and `soffice.js.linkdeps` and `soffice.data.js.link` are dated 2026-08-01. So today's core inputs equal v15's.
- **Remedy:** pin all five on the runbook's link line: `LOSRC=../libreoffice-26-8 LOBUILD=../wasm-lite/build-headless-probe EMSDK_ROOT=../wasm-lite/tools/emsdk EXTRA_DEFINES= EXTRA_OBJECTS=`. Add a pre-link step run in the owner's shell: `make -n … | grep -- '-o build/e2/editor-v19/probe_engine.o'`, compared with the v15 line. Add the `find -newer` stamp on the core link inputs, expected 0 files.

### S2. "What this link ships" is read, not measured; v15's runbook measured it

- **Where:** `RUNBOOK-relink-v19.md` "What this link ships" says "whose engine differs from v15's by one commit, 66e5c0af". The v15 runbook ran `tools/what_the_link_ships.py` ("measured, not read"), and that tool exists because reading git logs answers about the repository, not the build (its docstring). M1-1 cannot answer this, because BASE `5d77dc84` predates B.
- **Measured here:** `what_the_link_ships.py --since 1990bb64 --variant merge-v15 --shipped-profile dist/profiles/e2-editor-v18 --json` (v19's defines equal v15's) gives:
  - `ok: true`, no configuration drift;
  - only `probe_engine` changed, and its hunks are exactly `66e5c0af` (`MergeKeyPollMs`, the `wake`/`expired`/`values[0] = expired ? 2 : 3` block);
  - `sdk_api`, `unoembind_stub` and `editor_api` identical;
  - worker `00882139…` identical.
  - Output: `scratchpad/ships-since-v15.json`.
- **Caveat:** `1990bb64` is inferred as the tree at the v15 link (the last commit before the 10:22-10:24 link; `4928aced` records it).
- **Remedy:** put this command and its expected answer into the runbook's §0 gates.

### S3. M1-1's exit 0 does not imply X2's sentence

- **Where:** `check_merge_key_undo_scope.py:162`, `elif rule not in carriers and not row["same"]: failures.append(...)`. For carriers there is only `:167`, `if carrier in rules and not any(not r["same"] for r in rows if r["rule"] == carrier)`.
- **Predicate attacked:**
  - X2 (§31.4): "exit 0: only v15's and v19's `probe_engine` objects differ from BASE" (原文「只有 v15 與 v19 的 `probe_engine` 物件與 BASE 不同」).
  - §31.3: "the `probe_engine` objects of v15 and v19 must both differ from BASE" (原文「v15 與 v19 的 `probe_engine` 物件都必須與 BASE 不同」).
- **Scenario:** an `#ifdef OXSDK_MERGE_KEY_UNDO` block lands in `editor_api.cpp` or `sdk_api.cpp`. Only the two carriers' copies of that object change, and the exit code stays 0. Only the printed `different` count (3 instead of 2) shows it.
- **Remedy:** for each carrier, require that exactly `…/probe_engine.o` differs; or have X2 read the JSON rows instead of the exit code.

### S4. The binding pins 2 of the 13 shell-bundle modules and not the HTML

- **Where:** `run_merge_wasm_shakedown.py:979-987` binds wasm, worker, `narrow-editor-v2-session.js`, the page, the page source and `eshape.json`. The bundle (`e2/editor-shell-v2-bundle-v55.json`) has 13 modules: `editor-session.js`, `input-adapter.js`, `document-sdk.js`, `tile-scheduler.js`, `recovery-notice.js` and others.
  - `shell_lagging_source` (`:1124`) proves only that dist equals source at run start. The source can change between the five reports.
  - The reader's `together()` compares neither `candidate.uninstrumentedHtmlSha256` nor any bundle digest. `e2-editor.html` is the file finding 094 named as outside the hash net.
- **Scenario:** a fix to `input/input-adapter.js` (finding 111 territory) is made and `make` is run between `counted-B` and `m2-1b-B`. The reader says "one binding", even though the reports measured two shells, and neither of them is necessarily v56's declared bundle (the runner never compares served files with the v56 manifest).
- **Remedy:** bind `pp.served_shell_identity(root)` (its served digest, the differing paths limited to the entrypoint) and the HTML sha. The product-path runner already computes these. Today's binding is a hand-picked list (form 3, CLAUDE.md §1).

### S5. M2-3 accepts a session reopened twice

- **Where:** `judge_counted_m2.py:238` (`window.generation == g0+1`); runner `:709` (same); `pair` `:1041` (uses the window's generation). The record's own `generation[1]`, read after the 90 s quiet (`:804`), is never compared.
- **Scenario:** after the first reopen's "已重新載入" closes the window, a second reopen happens (a late BUSY or disposal race in the reopen flow). The reopened text is still original + marker, because the second reopen loads the same checkpoint. Every clause holds, and the pair agrees.
- **How shown:** E3 sets C29 r2's `generation` to `["1", "3"]` and leaves the window at "2". Result: `exit 0 | VERDICT PASS`.
- **Remedy:** add `record.generation[1] == window.generation` to `refusal_record`, and to `pair`'s comparison.

### S6. M2-4's native reference is not bound and not versioned (§7's "R0 report directory and input sha256" is missing from the binding)

- **Where:** `run_merge_wasm_shakedown.py:146`, with `LIMIT_ROUND` under `build/` (not in git).
  - `limit_reference()` (`:858-880`) checks only that the three native rounds agree with each other, and reads H03's caret from `build/…/arms.jsonl`. The evidence copy is `arms.jsonl.gz` plus `inputs.sha256`, inputs only.
  - The reader's `limit_record` (`:262-264`) reads `build/…/docs/r1-H03-key105.odt` with no hash check.
  - `bound_values` binds `eshape.json` but none of the native reference documents.
- **Scenario:** `build/` is cleaned or regenerated (R0 run 4 re-run into the same path, or restored from a different machine). The final-document clause then compares against an unverified file. When the file is missing, the reader stops with NOT DONE and cannot be recovered.
- **Recorded value to pin:** the v18 reports carry `finalDocument.theirs = 60087d9401a68bf6`, the sha16 of the reference `content.xml`. The `.odt` file itself is `d8e8fcfd12228dda…`.
- **Remedy:** a constant beside `LIMIT["fixtureSha256"]` for the reference's `content.xml`, checked by the runner and by the reader. Or copy the two docs into `findings/evidence/merge-native/r0/limit-round-…/`.

## NOTE

1. **§31.5's ordering cannot occur, and the comment's argument is stronger than written.**
   - The LOK thread releases the SolarMutex only on its way to sleep. In `vcl/headless/svpinst.cxx:442-444`, a dispatched user event returns at once. At `:448-455` it returns without releasing unless it must sleep. The release is at `:471`.
   - The key arrives as two queued user events (`unotxdoc.cxx:4012` → `lokhelper.cxx:1294-1311`). The flush the key itself triggers is a third (`init.cxx:2578-2582`, `PostUserEvent`).
   - `doc_getCommandValues` takes `SolarMutexGuard` (`init.cxx:6689`).
   - So a poll read lands only after KEYINPUT, KEYUP and the key's own synchronous callbacks have run. It is not after "KEYINPUT but before KEYUP", and it is never mid-key. v19 does not register an anyInput callback; that code is only in the `OXSDK_MAINLOOP_ENGINE` branch, which the 3.1/10 guard forbids with B.
   - What really reorders: callbacks Writer emits from later timers now arrive after the completion. Examples are D4's `.uno:DocumentRepair`/`.uno:Undo` at about 628 ms, and probably D2's +36 ms ones. The page tolerates this: a late `INVALIDATE_TILES` triggers `document-invalidated` → repaint (`e2-editor-app.js:2027`), and 118's path then re-lays out. The register should be restated with this reason.
2. **The §31.5 clock-guard argument rests on v18's "each press ≥ 37 ms" (原文「每下 ≥ 37 ms，已量」).** v19's poll lowers it, and M2-4's 0.5 s quiet between presses cannot probe it. Record X7's minimum `keyToUndoMs`, or restate the argument as "a transaction is several LOK round trips".
3. **A Python traceback in the reader exits 1, the same code as FAIL.** This is not a pass risk.
4. **`completedAt` and `stderrEmpty` carry less than they appear to.** `completedAt` is written in `finally` (runner `:1254`), so after the teardown fix it no longer means "completed". `stderrEmpty` (`judge:364`) passes when no `.stderr.txt` exists, and the synthetic green has none. Population checks carry the weight; the reader could require the stderr file.
5. **`fast()` has no lower bound (`judge:173-176`; runner `:913-915`).** A negative latency, meaning a response taken from before the key, passes. Shown as E5: −250 ms on C01 r1 and −3 ms on M2-4 press 11 give exit 0. Require `0 <= ms`.
6. **A refusal's kept reopened document is bound to its report only by paragraph count.** See runner `:816-817` and `judge:227`. Merges, by contrast, are bound by content hash plus text verdict. Record the reopened document's `content.xml` sha.
7. **Page fix `840794af`: harmless, with one pre-existing side effect.**
   - **The partial `strips`:** after `break`, `lastTiles = strips; paint()` runs before `layoutCanvas()`. Then `layoutCanvas` clears the canvas and sets `lastTiles = []` (`e2-editor-app.js:779-785`), so partial strips never survive.
   - **The side effect:** when ≥1 strip was kept (a canvas over 32,767 rows), `paint()` uses the old `el.canvas.height` with the new `heightTwips`. `moveSinkToCaret` then parks the IME sink at the wrong place until the re-render paints (finding 069's surface). The growth path did the same before the fix. Skipping `paint()` when `documentResized` would remove it.
   - **The 062 detection** is kept, because `documentSizeChanged` is engine-global and reported once (`probe_engine.cpp:3129-3133`).
   - **`run_shrink_repaint.py:182-186`'s GREEN** is narrower than P3's text. Any toast that is not TILE_NOT_PAINTED, and any rows other than the two-page rows, still give GREEN. P3 was confirmed by reading the reports (no toasts, 1,012/1,256 rows); it is a one-time verification.
8. **M2-4 and M2-1b, the two timing-sensitive criteria, run only instrumented and are never paired.** Since 117 the instrument also samples every paint reply's pixels and serialises a trace node. M2-4 also waits ≥0.5 s quiet between presses, so held-key Delete is not measured. Do not let "117 fixed" be read as "holding Delete is fast".
9. **X1 proves "a different file", not "contains the fix".** `check_profile_identity.py`'s `wasm` clause establishes only that the wasm is a different file; a relink of unchanged sources also differs (036). The `.coreCommit` leaf is a copied declaration. X7's M2-4 is what proves the fix. That is fine, but do not cite X1 for it.
10. **v19's packing rule packs from `build/e2/editor-v19/`, not from the archive.** See `Makefile:1493-1513`; v16-v18 pack from v15's archive. After step 3's archive, a later `make` of v19's manifest (any of its nine tool prerequisites edited) repacks from whatever `build/` holds. Consider re-pointing the rule at the archive once it exists.
11. **The reader's docstring list of what it shares with the runner is incomplete.** It omits `FIXTURES` (round keys and directories), `MARKER_AT`/`MARKER`, `LIMIT_ROUND`/`LIMIT_FIXTURE` and the `ESHAPE` path.

## No defect found

- **Section 1 (spec §30-32):**
  - The per-instance forms, red cases and non-vacuity clauses are sound as written, apart from the items above: B1 (X7's invocation is not pinned), S3 (X2's wording against the tool), S6 (§7's R0 binding) and NOTE 1-2 (the §31.5 register).
  - §32.3's red-case counting is sound: `is_counted("m2-1-red")` excludes exactly wasm, worker and `pageSha256`, and requires the same key set. Tested, and re-read.
- **Section 2 (reader):**
  - Beyond B1, B2, S5 and NOTE 3-6/11, no path to a false PASS was found.
  - The reader re-derives every clause from fields and kept documents, rejects a kept document whose hash disagrees, reconstructs the population, and checks M2-4's per-press latency.
  - No correct-run-turns-red scenario was found. The only non-product way to go red is noise on a captured stderr.
- **Section 3 (runner):**
  - `mode_schedule`, `run_limit`, `limit_clauses` (with `latency`), `is_counted`, `teardown` (closes in `finally`, and a failing read is recorded) and `pair`: no defect.
  - The drained log: the global `TRACE` persists across cases, but each run loads the page once and the observer's sequence is monotonic, so it is correct. The log is diagnostic only.
- **Section 4 (engine `66e5c0af`):**
  - (a) and (c): see NOTE 1. A read cannot land mid-key or between KEYINPUT and KEYUP. A read before LOK has picked up the key sees P0 → Pending, never a refusal, because refusal happens only at the deadline. So no half-done state can be judged as verified or as a refusal.
  - (b): the synthetic step is `sdk=false`. `finishExecuting(requestId)` is a no-op, because `executingRequest` was cleared after the original dispatch. The same path was already taken by every callback-queued step (`values[0] = 3`).
  - (d): `values[0] = 2` is still produced only when `now >= deadline`, and `handleMergeDeadline` is unchanged. The other three stages compute `wake = deadline` and fall through as before. The deadline now ends in a refusal in practice, where before it could end in a verified completion. Its reading is unchanged.
- **Section 5 (page `840794af`):** no defect (NOTE 7).
- **Section 6 (plumbing):**
  - **Makefile v19 block:** `make -n ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v19/sdk-manifest.json` reaches only v19's four objects, v19's export list, v19's link, the v15 archive `sha256sum -c` and v19's packing. No other guarded link is reached.
  - **X1 checker and its 11 tests:** no defect (NOTE 9). The real v18 manifest has no size-like leaf that a correct v19 would move.
  - **M1-1:** S3 only.
  - **Runbook:** S1 and S2.
