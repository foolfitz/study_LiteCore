# Handoff, 2026-10-14 (b): finding 140 fixed (v68), the page cut over to engine v20 (v69), host 0.2.20 installed; both new judges reviewed; §10.7's host arms re-expected

This round continues `HANDOFF-2026-10-14-v20-linked-v67-frozen-new-document-0.2.19.md` (its Addendum 2 was the entry point). Commits `2b470a6a..73d34430` here, plus host `2ff30b5`.

**Authority.**
- The owner chose B at the end of 10-14: a fresh fable does finding 140's second pass.
- This round the owner chose **A**: cut the page over to v20 and install host 0.2.20 on the ddev instance.
- Every other ruling below was made by fable on the owner's behalf, following the standing pattern, and is recorded where it was made.
- Nothing was pushed. The link stays the owner's step; no link was run.

## State

| item | state |
|---|---|
| Releases | Nominal shipped and counted: **0.2.12**. Uncounted candidates: 0.2.13–0.2.19, and now **0.2.20**. 0.2.20 is installed on ddev (host `2ff30b5`, `occ app:list` 0.2.20). Its engine package is buildId `6cffc5960ebbbd98`: profile `e2-editor-v20`, wasm `313b08d5…`, page `53019168…`, shell v69. HTTP serving decodes to `53019168…` under gzip and zstd, and `check_engine_decoded.py` passed. It is archived in `wasm_sdk_probe/build/archive/host-0.2.20-engine-6cffc5960ebbbd98/` (read-only, with `ATTRIBUTION.md`). To roll back: 0.2.19 is host `afbaf3c` with archive `host-0.2.18-engine-d6d04880f56e31da/`. **The owner's hand test of 0.2.20 has not been reported yet.** |
| Product page | **Cut over to `e2-editor-v20`** (`f554fe6b`, page `53019168…`), with the owner's approval. The relink-queue item `queue-v11-cutover-soak-not-started` drifted, as designed, and was re-anchored to v20 with a CORRECTION paragraph; the precedent is `6e9ec27e`. |
| Shell | **v68 frozen** (`aed18fe0`, bundle `e6f7ca64…`): finding 140, session `f47c80ec…`. **v69 frozen** (`f554fe6b`, bundle `cdc20ef8…`): v68 plus the cut-over entrypoint. After each freeze, `make test-e2-c-static` exits 0 (node 352+5, python 108), E1-C is intact and the relink queue has 0 drifted. |
| Finding 140 | **Fixed and shipped in 0.2.20 (uncounted).** First pass `6c761117` (red at 129-B). Second pass `a60456a6` (task 10-14h, fable): a click made while a range is open takes v67's polling path; a click on a collapsed selection asks the engine with `Math.round`ed twips. C1: blank-page clicks resolve in 405–413 ms on v19 and v20 in both browsers. C2 (task 10-14k, `69bd8178`): 129-B 54/54 in both browsers, 0 cells differ from four reference rounds; `定位游標` median 27.5 ms in Chrome and 29.1 ms in Firefox. The latency clause was written before the run. |
| v20 binding prerequisites done | The merge runner re-expects C29/C30 under C (`7e6c9acd`). The held-into-refusal judge holds the C rules for §10.7's five arms (`269cbc6d`). restore-window is retired on C profiles as "nothing to guard". Both new judges got their one §34.3 review, and the dispositions are applied (`166a7cda` J1, `96f86b22` J2). |
| v20 binding prerequisites **not** done | See Next 2. |

## What was decided (fable on the owner's behalf unless marked)

- **Finding 140, second pass** (`findings/140-…md` 裁決（第二輪）; `findings/evidence/paste-latency/second-pass/README.md`).
  - The probe established the cause of the red: the engine completes place-caret only on `INVALIDATE_VISIBLE_CURSOR`. A collapse click's `TEXT_SELECTION` arrives and does not complete it, so the engine answers at its 250 ms deadline.
  - A "second click is read as a double click" hazard was refuted from VCL's source.
  - Named limit: with a range open, a click core never processes keeps v67's 30 s timeout.
  - For the next link batch: complete `handleEditorPlaceCaret` on `TEXT_SELECTION` as well.
- **Merge runner under C** (10-14i). Neither the manifest nor the ABI declares C. v19 and v20 manifests differ only in the three hashes and `pageRectangles`. The keying is therefore the engine-emitted fragment `,"completion":"verified-boundary-noop"` in the profile's wasm: v20 carries it, v19 and v8 do not. The re-judge of part B's eight reports: 4 records per shakedown/control report flip to pass, everything else is unchanged. The 90 s toast wait is gone for no-ops. For the next link: declare C in the manifest.
- **J1 — `judge_v20_shakedown.py`** (`findings/evidence/link-batch/v20-shakedown/review/DISPOSITION.md`). Fixed 8, Claim corrected 6, Registered 20, Stop 0. The fixes that matter:
  - C1's `noSelectionAt500ms` read the TEXT_SELECTION cache; it now requires the fresh `selectionType == "none"`;
  - a FAIL followed by a green re-run in one directory exited 0; duplicates now FAIL;
  - E2 passed vacuous runs;
  - `--expect-page` is mandatory.

  The committed reports re-judge byte-identically, still `VERDICT PASS`. The runner-side changes are unit-tested only; their first browser run is the next v20 shakedown or the count.
- **J2 — `check_m3_new_document.py`** (`findings/evidence/new-document/review/DISPOSITION.md`, spec §7.5). Fixed 10, Registered 20, Claim corrected 4, work items 5. The fixes that matter:
  - the settings restore could delete the owner's `core/lang` and record `ok: true`; the tool now refuses to run on an unreadable setting. The `--default-value` read has **not yet run against the real occ**: the brief forbade touching the instance;
  - N9's "0.2.19 changed only the host" clauses now run only on a 0.2.19 report;
  - the count binds `ENGINE_BUILD_ID` / `PAGE_SHA256`, which are `None` until binding, so the count refuses until then;
  - N4 requires the saved paragraphs to be exactly `["zqx"]`, and N5 requires reopening onto N2's fileid.

  No committed verdict moved.
- **The owner chose A**: cut over, freeze v69, package 0.2.20, install.
- **§10.7's host arms** (10-14l run by sonnet, `09770d87`; 10-14m by fable, `269cbc6d`).
  - On 0.2.20, every C arm meets §10.7 in both browsers: 0 refusals, generations `['1']`, document = original + marks, the marker at the caret. The caret clause is inferred from where the marker landed; no probe records the caret.
  - The judge keys C through `static.buildId` to the archived package's wasm. **It therefore needs `wasm_sdk_probe/build/archive/` (untracked)** and fails closed without it.
  - 13/13 v19-era reports re-judge identically. v20 held goes from FAIL(30) to PASS, and table from FAIL(12) to PASS.
  - The four non-C table arms still refuse on v20 and PASS.
  - The 3.0–4.3 s busy tail after releasing a held key at a C boundary is an instance of named costs: 2.25 s per no-op × H2's depth of 2, a band of [2.25, 4.5] s. It is neither a finding nor a new limit.

## §34.4 (this round)

- **Repaired because of execution: 2.**
  - `run_merge_wasm_shakedown.py` (witness: part B's reports): 1.
  - `judge_held_into_refusal.py` (witness: `findings/evidence/link-batch/host-0.2.20/`): 1.
- **Repaired because of review: 18.**
  - `judge_v20_shakedown.py` and `run_v20_shakedown.py`: 8.
  - `check_m3_new_document.py`: 10.

  This is each new judge's one §34.3 review. **Both budgets are now spent**, so for these two tools the review number must stay 0 from here on.
- New probes or instruments used for the first time (not repairs): `extract_click_latency.py` and `clause_counts.py` (v68-witness-2), and `probe_140_completion.py` (second-pass).

## Uncounted changes since 0.2.12 (for the next count)

- 0.2.13–0.2.19, as listed in earlier handoffs.
- **0.2.20**: engine v20 (page number, C, `caretBefore`), conditions 45, 47 and 48, finding 138 fixed, finding 140 fixed.

## Next (in order)

1. **The owner hand-tests 0.2.20.** The list given in chat:
   - the page number while scrolling;
   - Backspace at the document start and Delete at the document end do nothing (about 2 s) and do **not** reopen;
   - new blank document, click below the first line, paste: immediate;
   - new document, type, save, reopen as on 0.2.19.
2. **Before `BINDING` v20** (RUNBOOK-relink-v20 §4.2):
   - **a.** `tools/judge_counted_m2.py:112` still maps `nothing-selected` to a refusal; it must learn C, with the same keying and the part B reports as witness. Separately, `tests/test_judge_counted_m2.py::V19Witness` (2 tests) is **red by construction** since `7e6c9acd`: the frozen judge's `thisRunner` compares the live runner hash with the v19 reports' `73b2e9ff`, and its docstring says to re-judge at the run's commit. These tests are not in `make test-e2-c-static`.
   - **b.** `check_m3_new_document.py`: write `ENGINE_BUILD_ID = 6cffc5960ebbbd98` and `PAGE_SHA256 = 53019168…`, plus the host bindings for 0.2.20.
   - **c.** Pin rebinding for the nine runners to page `53019168…`. `FINAL_PAGE_SHA256` in `probe_129_m4_wasm.py` is still `7815e16c…`, and 129-B retires on v20 per §10.9 S-2. Check each runner's pin, one line per pin commit, as in the precedents `1b5efdbb` and `a0ed713f`.
   - **d.** The count chain's abort rule, 135's C2 semantics, and the **release text**. The release text must cover:
     - finding 137's three effects;
     - L-C-late-K1;
     - L-C-number-or-indent;
     - 138 and 140 fixed;
     - the held-key tail (up to about 4.5 s busy after releasing at a C boundary);
     - and `specs/SPEC-M3-held-key.md` §3.2's owner-facing 「放開之後最多再刪 2 字、約 0.13 秒」, which is now stale at a C boundary.
3. **Bind v20, then run the full count chain overnight**, detached from the session.
4. **The next link batch.** Every item needs a link:
   - `Language=` with 031's fix and the three fallbacks pinned;
   - Markdown paste (A);
   - new-document's D12;
   - `handleEditorPlaceCaret` completing on `TEXT_SELECTION` as well (finding 140's second pass);
   - a manifest field that declares C (10-14i). Today two tools key on a wasm string.
5. **Later:**
   - the Writer stack sweep (condition 52);
   - the ordered-commands spec;
   - a measurement of typing during a no-op's 2.25 s window (10-14m's work item, near L-C-late-K1);
   - J2's work items, among them N6's crafted-override blind spot, which goes with `Language=`.

## Loose ends

- `probe-held-refusal.odt` is still in the admin's Files on ddev. The held probe's `main()` never deletes it; task 10-14l's brief wrongly said the probes clean up. It is a probe fixture, not the owner's content. It was left there; delete it only if the owner agrees.
- The 129-B desk was not clean in 10-14k and 10-14l: the owner's Chrome had about 30 processes, load was 1.5–2.7, and swap was active in 41/54 arms. No clause went red. The effect is unverified.
- `editor-shell-v2` suite counts: the older "412/425" figures do not reproduce with node 24.16. 352 is the current editor-shell-v2 count, used in the v68 and v69 freezes.

## Subagents this round (roles; not reachable from a new session)

- **fable, executors and judges:**
  - 10-14h (finding 140, second pass);
  - 10-14i (merge runner under C);
  - 10-14j J1 and J2 (review dispositions);
  - 10-14m (held judge under C).
- **sonnet, executors:**
  - 10-14k (129-B, C2);
  - 10-14l (host arms on 0.2.20).
- **Review seats:** opus ×2 and `codex exec -s read-only` ×2 (the codex MCP failed to connect; the CLI worked).
- **Main session (opus 5.5):**
  - the briefs (10-14h to 10-14m) and the two review briefs' import;
  - checks of every report against source and tests;
  - the v68 freeze;
  - the cutover with the v69 freeze;
  - packaging, install and archive of 0.2.20;
  - finding 140's status;
  - this handoff.
