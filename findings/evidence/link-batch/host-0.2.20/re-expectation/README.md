# The held-into-refusal judge and restore-window under C (task 2026-10-14m)

**§34.4: repaired because of execution, +1 (`findings/evidence/132/held-into-refusal/judge_held_into_refusal.py`). Witness: `findings/evidence/link-batch/host-0.2.20/` (task 10-14l, commit `09770d87`): on host 0.2.20 (engine v20, buildId `6cffc5960ebbbd98`) the unchanged judge read `held/report.json` as `FAIL (30)` and `table/report.json` as `FAIL (12)`, every red line on a clause that presupposes a refusal and a reopen (`one_reopen`, `scroll_end`'s "no restart-required sample", `stage_is("nothing-selected")`), while v20 ships C (SPEC-M3-link-batch §10.5, §10.7).** Repaired because of audit: 0. The restore-window probe is unchanged (`probe_restore_window.py` sha256 `c173cf743b87eddb…`).

Judge sha256 `b0ed5fa050a8d5c4…` before (`00900fdd`), `67c9e763e04225e5…` after. No browser was run; nothing under `dist/`, `web/`, `editor-shell*/`, `sdk/`, `src/`, the Makefile or the host was touched. The rulings below were made on the owner's behalf for fable; each carries its plain-language reason.

## 1. The keying: the precedent's rule, read through the identity these reports carry

**Rule reused.** Task 10-14i (`7e6c9acd`, `run_merge_wasm_shakedown.boundary_noop_declared`) keys C on the byte fragment the engine emits for the completion, `,"completion":"verified-boundary-noop"` (`probe_engine.cpp`, `finishSelectionBarrierBoundaryNoop`, behind `OXSDK_E2_V20_LINK_BATCH`), read from the bytes the run bound, fail-closed both ways. The judge uses the same constant (`BOUNDARY_NOOP_FRAGMENT`; `rejudge.py` asserts it equals the runner's) and the same semantics. No second keying was invented.

**What is different, and why.** The merge runner's reports record `candidate.profile` and `bound.wasmSha256`, so it reads `dist/profiles/<profile>/probe.wasm` and STOPs unless the sha256 matches. The held and table reports record neither; what they record (`static.buildId`, from `check_m3_production_ui.static_facts`) is the host engine's `buildId`, which `package_m3_engine.py` defines as the first 16 hex of the sha256 of the canonical JSON `{path: sha256}` of the packaged closure, the page, the worker and the wasm included. That is a stronger binding than a profile name: it names the exact bytes the host served, and the served bytes are what the probes measured through. So the judge:

1. resolves `static.buildId` to the engine package the host served, `wasm_sdk_probe/build/archive/host-*-engine-<buildId>/` (the archived output of `package_m3_engine.py`; `--engine DIR` overrides, e.g. a live host's `engine/`);
2. requires the package's `MANIFEST.json` to carry that `buildId`, to **recompute** to it from its own `files` (`build_id`, the packager's function verbatim), and to name the report's `servedPage` as its `e2-editor-app.js` hash;
3. decompresses `files/<profile>/probe.wasm.gz`, requires its sha256 to equal the manifest's;
4. only then tests the fragment.

Any step failing is `FAIL engine: …`, `verdict FAIL (1)`, nothing judged: **no bytes, no expectation.** There is no default. A v19 profile judged under C is red on `no_reopen` (R2 below), a C profile judged under the refusal is red as the witness was (R3), so a keying error in either direction cannot pass.

**Why not the name, the manifest or the host version.** `e2-editor-v20` is a label; the precedent's reason stands (a diagnostic profile minted from an older engine under a newer name). The profile manifest declares nothing about C (10-14i checked `editorContract` on v19 and v20). `hostVersion` names a package, not an engine: 0.2.8 through 0.2.18 all shipped `e2-editor-v19` (`1aafd4f9…`), as the keying table in `rejudge-output.txt` shows, and nothing stops a host version from re-shipping an older engine.

**What the archive holds (read, not assumed).** All 15 `host-*-engine-*` packages are `litecore-engine/2`, each recomputes its own `buildId`, each carries its wasm as `.gz` whose decoded sha256 equals the manifest's `source.wasmSha256`. The fragment is in exactly one: `host-0.2.20-engine-6cffc5960ebbbd98` (profile `e2-editor-v20`, wasm `313b08d5…`). 0.2.7 is `e2-editor-v8`, every other one is `e2-editor-v19`. Every committed held/table report's `buildId` (`daf70d77…` 0.2.15, `9352fae3…` 0.2.16, `e3944715…` 0.2.17, `d6d04880…` 0.2.18, `6cffc596…` 0.2.20) resolves to exactly one package.

**Limit, named.** `build/archive` is not in git (allowlist `.gitignore`; the 1.7 GB of frozen artifacts live on this disk, memory `study-litecore-git`), as `dist/profiles/` is not for the precedent. On a tree without it the judge reads `FAIL engine: … 0 engine packages …` and judges nothing, which is the intended reading of "the bytes are not here", not a verdict on the report. `--engine` takes a live host's `engine/` directory (the same `MANIFEST.json` + `files/` layout, the same checks).

## 2. The rules under C (`RULES_C`), per arm

`RULES` is untouched and still judges every arm on a profile without the fragment. On a profile with it, the five arms §10.7 lists take `RULES_C`; the four other table arms (`before-table-*`, `cell-press-type`, `cell-hold`) keep `RULES` because their exits (`key-posted`, `anchor-mismatch`) still refuse on v20, measured in the witness (8/8 PASS under `one_reopen`). `RULES_C` is a mirror of §10.7's list, and it cannot pass wrongly: an arm listed that still refuses is red on `no_reopen`; an arm omitted that completes as a no-op is red on `one_reopen`.

| clause | v19 (`RULES`) | C (`RULES_C`) | why |
|---|---|---|---|
| reopen | `one_reopen`: refusals 1, generations `['1','2']`, no limit notice | `no_reopen`: refusals 0, generations `['1']`, no limit notice, **no reopen toast** (`summary.toasts` has no entry containing 「重新載入」) | §10.5: the key completes `verified-boundary-noop`, "不回 `EDITOR_BOUNDARY_UNSUPPORTED`、不重開", the page "不跳提示". The limit clause means the same thing. The toast clause is the page-side half of "no reopen": `one_reopen` needed none because `refusals == 1` already pinned the toast's cause; under C a refusal that the state sample missed would still show its toast pair, which the table probe's `refusal_stage` classifies by the same substring. Restricted to reopen toasts so the 「已開啟 …」 toast of a fast open cannot red it. |
| document kept | `document_kept` | unchanged | §10.7 "文件…不變": the saved document with the three marks stripped equals the original |
| counts | `counts(...)` per arm | unchanged | each mark exactly once where typed, absent where not |
| placement | `after_at`, `mark_then_after`, `mark_at_end`, `control_at`, `contiguous` | unchanged | §10.7 "打的標記落在游標所在處": the marker in the paragraph the caret was in, at its start/end, contiguous with what was typed before the key |
| caret | (implied by placement) | (implied by placement) | no probe records a caret; the witness README says so ("(4) by inference"). Not added: it would be a new instrument, not a rule |
| scroll, start arms | `scroll_start`: every sample 0 | unchanged | the view at the start stays at the start |
| scroll, end arms | `scroll_end`: from the first `restart-required` to the end of the log, every sample ≥ 0.5 × the last sample before it (> 0); a 「已重新載入」 sample must follow | `scroll_kept`: from `stateBeforeKey` (> 0, same guard) to the end of the log, every sample ≥ 0.5 × that sample | the v19 window was anchored on the refusal because the excursion it guards against (L-134-restore-flash) is the reopen's; under C nothing anchors a window, so the whole log after the key is the window. The threshold and the meaning ("the view never goes near the document start") are the same. `stateBeforeKey` is required (the held probe records it) |
| `cell-start-hold` control | `stage_is("nothing-selected")`: the toast's stage is D's, not `anchor-mismatch` | `stage_none`: `refusalStage` recorded, `stage` None, `stages` `[]` | the positive control inverts: under C the `nothing-selected` exit is the no-op and the others still refuse, so "measures D, not anchor-mismatch" becomes "no stage was read at all"; a stage read is a refusal. `refusalStage` missing is still "not recorded", a FAIL |

Per arm: `start-press` / `start-hold` = `no_reopen, document_kept, counts(1,0,1), after_at("start",0), scroll_start`; `end-hold` = `no_reopen, document_kept, counts(1,0,1), after_at("end","last"), mark_then_after, scroll_kept`; `end-press-type` = `no_reopen, document_kept, counts(1,1,0), control_at("last"), mark_at_end, contiguous, scroll_kept`; `cell-start-hold` = `no_reopen, stage_none, document_kept, counts(0,0,1), after_at("start",1)`. `MIN_ROUNDS` unchanged. The judge prints which expectation it applied (`expectation C (RULES_C on [...])` / `expectation v19 (...)`) and the keying (`engine buildId … declares C: …`).

## 3. `restore-window` under C: retired on C profiles as "nothing to guard"

**Ruling: retire the arm on a profile that declares C, in AGENTS.md §3's second sense (nothing to guard), not its first (a behaviour nobody guards). The probe is not changed.**

- **The window is D's, and D runs only on a refusal.** The caret restore is inside `reopenAfterBoundaryRefusal` (`web/e2-editor-app.js:1767–1830`: `session.restart()`, then `placeCaret(caret.x, caret.y + h/2)`), which `editorAction`'s catch enters only when `reopensAfterRefusal(error)` (`:1943`; `EDITOR_BOUNDARY_UNSUPPORTED`, or `EDITOR_STATE_UNAVAILABLE` with `recovery: "restart"`). C's exit is not an error: `finishSelectionBarrierBoundaryNoop` emits `editor-action-completed` with `changed: false` (`probe_engine.cpp:3543–3570`) and the session accepts it as a completion (`narrow-editor-v2-session.js:995`). No error, no reopen, no restart, no `placeCaret`, no window. The witness measured exactly that: 6/6 rounds, 0 refusals, generations `['1']`, the poll ran to its 20 s deadline (`polls` 898–966; `genSeenAt` is the deadline, not a generation change) and the first typed key came 20.01–20.02 s after the Delete.
- **What the arm would assert on C is already judged.** The arm's place (last line, End, Delete) is `end-press-type`'s; its C properties (0 refusals, `['1']`, document unchanged, `zqx` in paragraph 210) are `end-press-type`'s `RULES_C` minus the control, judged above from a report with `stateBeforeKey` and the full instrument. The only difference would be 20 s of polling before typing, which measures nothing.
- **Why not rewrite the wait.** A wait that types inside the no-op's 2.25 s (while the barrier transaction is open) would measure a different question, where text typed behind an open barrier lands, the neighbourhood of L-C-late-K1 and of the "ordered commands" spec's fixed question 2. That is a new arm with its own prediction and witness, not this arm under a new expectation, and §34.4 does not let this witness stand for it. Noted as a work item, not a gate (AGENTS.md §9 condition 3).
- **D's window still exists on v20 for the exits that refuse** (`key-posted`, `anchor-mismatch`: the four other table arms reopen and restore). The arm's position pins it to the one exit C removed; moving it is a probe change with a different measurand (another stage's reopen), not done here.
- **How a report of this probe on a C profile is recognised**, since the probe will still run: `summary.refusals` 0, `generations` `['1']`, `polls` at the deadline (≈ 20 s / `pollS`), `genSeenAt − key` ≈ 20 s. Such a report is void as a window measurement; G5's v19 criterion (`136/guard-r2/README.md` §G5) must not be read against it. The judge still refuses the probe's reports (`report['probe']` is neither held nor table), before and after, shown in `rejudge-output.txt`.
- **Default if never acted on**: the arm is listed as retired-on-C here; on a v19 profile G5's criterion still applies unchanged.

## 4. The held-key tail: an instance of two named numbers, not a limit or a finding

**Ruling: an instance of a named cost.** §10.5's named cost (one no-op ≈ 2.25 s) composed with H2's depth (SPEC-M3-held-key §3.2, `HELD_DELETE_DEPTH = 2`, `web/e2-editor-app.js:2713–2733`: "放開之後最多再做完這兩個").

- **Each no-op costs 250 + 2000 ms in the engine** (`SelectionBarrierBoundaryDeadlineMs = 250`, `probe_engine.cpp:583`; `MergeStepDeadlineMs = 2000`, `:579`; `rejectSelectionBarrierAtDeadline` `:4007–4044`: the first NONE at 250 ms opens `boundaryNoopWindow` for one more `MergeStepDeadlineMs`, the second NONE completes the no-op). Measured: 2257–2322 ms for every no-op that ran alone (the single presses and the first no-op of each hold).
- **H2 keeps one delete in the engine and one queued.** The engine runs one barrier transaction at a time (`gSelectionBarrier` is one; a second editor-action waits), so the queued no-op's latency is its wait plus its own: **4479–4518 ms on every queued no-op of the twelve holds** (the labels 「⌫ 刪除 4510 ms」 / 「⌦ 前刪 4487 ms」 the witness quoted).
- **At release, at most one is running (0–2.25 s left) and one is queued (2.25 s)**, so the tail is in [2.25, 4.5] s plus a repaint, whenever the hold is longer than one no-op. Measured, from the last repeat keydown to the first `ready`: Chrome `start-hold` 4030/4030, `end-hold` 3287/3287; Firefox `start-hold` 3737/3708, `end-hold` 3032/3006; table `cell-start-hold` Chrome 3972/3970, Firefox 3740/3732: **12/12 in the band**.
- **Worked from one log** (Chrome `end-hold` r0, `held/report.json`, times from the first keydown): Delete `beforeinput`s at 0, 500, 2270, 4520, 6800 ms (the second is the first repeat at the 500 ms delay, allowed at depth 1; each later one is sent the moment a no-op completes, as H2 says); completions at 2261, 4518, 6774, 9031, 11288 ms, 2.26 s apart; release at 8000 ms; the fifth completes at 11288: tail 3287 ms. 251 repeats, 5 sent: H2 dropped the rest (`beforeinputs` 8 = 5 + `wvy`).
- **Not a new limit**: both numbers are already named and the composition is arithmetic. **Not a finding**: both documents describe exactly this behaviour; nothing deviates. **One sentence is stale, for the main session to append where it lives**: SPEC-M3-held-key §3.2's owner-facing prediction "放開之後最多再刪 2 字、約 0.13 秒" and §10.5's named cost were each written for their own case; at a document or cell boundary under C, "the two" cost up to 4.5 s, with no message. Candidate text for §10.5's named-cost line: "按住時：放開後最多再忙 4.5 秒（兩個 no-op，H2 的深度）". Whether that is worth a line in the release notes beside L-C-late-K1 and L-C-number-or-indent is the main session's call; the number is here.
- Not checked: the page's own 「busy」 pill versus the state sample (the probes read the same instrument), and a tail on a quieter desk (the band is bounded by the two constants, not the load).

## 5. The re-judge (`rejudge.py`, output `rejudge-output.txt`, `rejudge.json`, full outputs under `outputs/`)

Every committed report of the two probes (13 v19-era, 2 v20) was judged by the judge before (`00900fdd`, loaded from git and run with `__file__` at the real path so its probe lookups resolve as they did) and by the judge after, each with the report's own `servedPage`. The comparison strips only the two lines the edited judge adds (`engine …`, `expectation …`); everything else, verdict included, must be identical for a v19-era report.

| report | host | engine | before | after | other lines |
|---|---|---|---|---|---|
| `132/held-into-refusal/run-1` | 0.2.15 | v19 | FAIL (72) | FAIL (72) | identical |
| `134/acceptance-0.2.16` | 0.2.16 | v19 | FAIL (58) | FAIL (58) | identical |
| `134/red-d-on-0.2.15` | 0.2.15 | v19 | FAIL (18) | FAIL (18) | identical |
| `134/table/run-1` | 0.2.16 | v19 | FAIL (54) | FAIL (54) | identical |
| `134/table/run-2` | 0.2.16 | v19 | FAIL (34) | FAIL (34) | identical |
| `134/table/run-3` | 0.2.16 | v19 | FAIL (24) | FAIL (24) | identical |
| `136/acceptance-0.2.17/held` | 0.2.17 | v19 | FAIL (4) | FAIL (4) | identical |
| `136/acceptance-0.2.17/table` | 0.2.17 | v19 | FAIL (2) | FAIL (2) | identical |
| `136/acceptance-0.2.18/held` | 0.2.18 | v19 | PASS | PASS | identical |
| `136/acceptance-0.2.18/table` | 0.2.18 | v19 | PASS | PASS | identical |
| `136/baseline-0.2.16/held` | 0.2.16 | v19 | FAIL (6) | FAIL (6) | identical |
| `136/baseline-0.2.16/table` | 0.2.16 | v19 | FAIL (8) | FAIL (8) | identical |
| `136/cell-start-hold/red-aebef525` | 0.2.17 | v19 | FAIL (12) | FAIL (12) | identical |
| `link-batch/host-0.2.20/held` | 0.2.20 | **v20** | FAIL (30) | **PASS** | the witness |
| `link-batch/host-0.2.20/table` | 0.2.20 | **v20** | FAIL (12) | **PASS** | the witness |

- **13/13 v19-era reports unchanged**, line for line. **Both v20 reports PASS under C** (`held-under-c.txt`, `table-under-c.txt`: 12/12 and 12/12 runs, the four non-C table arms among them still under `one_reopen`).
- The "before" column is the `00900fdd` judge, not the `judge-output.txt` of record in those directories. Where the two differ (`134/acceptance-0.2.16` PASS of record vs FAIL (58); `136/acceptance-0.2.17/table` PASS vs FAIL (2); `136/baseline-0.2.16/table` FAIL (6) vs FAIL (8); `136/cell-start-hold/red-aebef525` FAIL (16) vs FAIL (12)), the difference predates this task: those outputs were written by earlier judge versions, before the S1/N1 edits of 2026-10-13 (`136/judge/README.md`, `136/review/review-1.md`). This task moves none of them: before equals after on every one.
- The four restore-window reports are refused by both judges identically (`verdict FAIL (1)`, `report['probe']` unknown); the edited judge prints their keying first (v19 ×3 `declares C: False`, v20 `True`), then refuses.

## 6. Red cases (AGENTS.md §6), each kept beside this file

- **R1** (`red-R1a…`, `red-R1b…`, `red-R1c…`): the v20 reports doctored, judged under C. (a) `start-press` Chrome with refusals 1, generations `['1','2']` and a reopen toast: 3 red lines, all `no_reopen` (`refusals 1 != 0`, `generations … != ['1']`, `reopen toast shown under C`). (b) one `end-hold` scroll sample set to 0: `scrollTop: 1 of 14 samples from the key to the end of the log < 0.5 x 21490 (lowest 0)`. (c) `cell-start-hold` with `refusalStage` `nothing-selected`: `refusal stage 'nothing-selected' read …: a refusal, not C's no-op`. Nothing else turned red.
- **R2** (`red-R2-…-under-c.txt`): 0.2.18's held and table reports forced under C (`judge_report(..., declared=True)`, a call the CLI does not expose): held FAIL (36), red on all four arms, 12 `no_reopen` lines; table FAIL (16), red on `cell-start-hold` only (4 `no_reopen` lines), the four other arms still PASS. A v19 report does not pass under C.
- **R3**: the v20 reports forced under the refusal: FAIL (30) and FAIL (12), failure lines equal to the committed `held/judge-output.txt` and `table/judge-output.txt`. The refusal path is the one the judge before ran.
- **R4** (`red-R4…`): the v20 held report with `--engine` pointing at the 0.2.18 package: `FAIL engine: …/MANIFEST.json: buildId d6d04880f56e31da != the report's 6cffc5960ebbbd98`, `verdict FAIL (1)`, exit 1, nothing judged.
- **R5** (`red-R5…`): a scratch package made of 0.2.20's `MANIFEST.json` over 0.2.18's `probe.wasm.gz`: `FAIL engine: …probe.wasm.gz: sha256 1aafd4f9da42fd83 != the manifest's 313b08d5cb085897; the declaration must be read from the bytes that ran`, exit 1, nothing judged. The declaration cannot be borrowed from a manifest.
- Also asserted by the script: the fragment constant equals `run_merge_wasm_shakedown.BOUNDARY_NOOP_FRAGMENT`; the judge before has no `judge_report` (it is the unkeyed one); every listed report path is a file (a fictitious entry STOPs).

## 7. Things to know

- The judge's output has two new header lines; any reader that counts lines or compares outputs byte for byte (none is known: nothing under `wasm_sdk_probe/tools`, `tests` or the Makefile references the judge or the probes) must strip them.
- `rejudge.py --scratch DIR` writes the doctored reports' package (R5, 41 MB) to `DIR`, not to the tree; the run here used the session scratchpad.
- 10-14i's note stands: a manifest field for C, TOLD to the profile builder at link time, would let both the runner and this judge read the manifest and stop when it and the wasm disagree. Outside this task's paths; needs a mint.
