# Handoff, 2026-10-15b: release text A–H decided; v20 bound; count chain ready and preflighted, NOT started (needs the owner's window); boundary hold measured; production-UI arms re-expected under C

This continues `HANDOFF-2026-10-15-0.2.23-installed-pre-binding-prep-done.md`. It covers commits `3a9d6007..c85118a8` (17 commits, nothing pushed).

**Authority.** The owner authorised **opus (the main session)** to decide the release text's §7 A–H. The owner then went to sleep: "請你自主執行，告一段落之後自己寫交接文件". The main session read that as **not** covering the count chain's start. Ruling J-a P5 says the chain starts only after the owner agrees a window ("if the owner cannot be asked, the chain is not started"), and memory `release-count-batched` says ask before running. The owner has not confirmed this reading.

## State

| item | state |
|---|---|
| Installed host | 0.2.23 (`2ccf1a9`, buildId `c3c22d92…`, page `ccb67a52…`, shell v72, engine v20). Unchanged tonight. |
| Counted | Nominal **0.2.12**. Uncounted: 0.2.13–0.2.23. |
| Release text | `handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md`. §7 decided. §4.3, §4.5 and §6 now carry tonight's measurements. §5 is corrected: the arms are v8/v20; the new-document runner is listed; A1-5 and A1-2′ R are added as not proved. It stays a draft until RESULT's numbers are checked. |
| v20 binding | **Done.** Runner pins: `4421df62`. Merge runner `BINDING` = v20: `22e8c900`; that runner is frozen under §34.1 until the v20 count's verdict is read. |
| Count chain | **Ready, not started.** `findings/evidence/m3-production-ui/runs-0.2.23/chain-0.2.23.sh`. `--preflight-only` at `c85118a8`: P0–P4 ok, P5 lock table 0 ok, P5 agreement REFUSED (no window, by design), P6 134 + 108 tests OK. |

## What was done

1. **Release text §7 A–H** (`3a9d6007`). Decisions and plain reasons are in the draft's §7.
   - A: 137 is written as reaching 0.2.12–0.2.23. 0.2.20–0.2.23 were upgraded from inference to source plus model: `dispatchDelete`/`deleteActionFor` still route on the engine snapshot, `holdsDelete` holds only same-key repeats, and condition 32's model ran on v20's keys.
   - B: 135's rate is published.
   - C: 144 on 0.2.21 is named.
   - D: `keyrepeat-check.html` is optional.
   - E: the three-run C2 rule is accepted.
   - F and G: kept as drafted.
   - H: both never-shipped rows are kept.
   - The ruling's J-b.3 odds were corrected append-only: 1.3 % → 1.09 % at p = 0.11. The rule's power against a real rate shift is close to the single run's, which is why the rate is always reported.
2. **Binding**. Evidence: `findings/evidence/link-batch/binding-v20/README.md`. Spec: SPEC-M3-link-batch §17.1–17.2.
   - Thirteen pin lines moved to 0.2.23/v72. Every value has two or more sources.
   - The nine `BINDING` values were computed by `bound_values()` and each was checked against a second source. The v8 red case still differs only in `PROFILE_BOUND`.
   - **V19Witness repaired** (`00903e29`): it also materialises `BINDING` at `b8324a85`. Red 2 → green 5/5.
   - **Observation:** `tests/test_judge_counted_m2.py` and `tests/test_merge_wasm_clauses.py` are in **no Makefile target**. `make test-e2-c-static` exited 0 while V19Witness was red. The chain's preflight P6 now runs them by hand.
3. **Boundary hold measured on 0.2.23** (`e4f5776b`, `af58cbf0`, `findings/evidence/host-0.2.23-hold/`). This is a flagged Backspace hold at the document start, 3 runs per browser, with single-press controls. The main session re-read the raw logs with its own reader (within 1 ms).
   - `hold-3s`: 2 requests, 0 deleted, 0 refusals, ready 1.44–1.53 s after keyup (0.2.20: 3 no-ops, 6.8 s).
   - `hold-2300`, the worst case (keyup 44–142 ms after the second request): ready 2.12–2.22 s after keyup. "At most one window" holds.
   - Not measured: holds longer than two windows; an unflagged hold.
4. **Count prep** (fable: `aed97819`, `03052985`, `01eaa155`, `65a8ec1c`, `8d500626`, `72510e5e`, `f1228f07`; the main session reviewed it).
   - **Chain.** Preflight P0–P6, then the desk line before each step, then the steps:
     - shakedowns, with the STOP rule: six M3 runners, autosave gate, new-document;
     - counted production UI: KR×3 and ctl/S/P×1;
     - six counted M3 runners;
     - autosave counted: the first counted AS-* run;
     - new-document counted;
     - product-path net: v8/v20 × 3 rounds × 2 browsers;
     - merge count: v19 X7's modes on e2-editor-v20, red case on v8;
     - C2 r1–r3, per J-b.

     About 8.2 h. The reader is `read-0.2.23.sh`; `c2-extension.sh` is for J-b's one extension.
   - **Product-path** reader copy and `PREDICTION.md`. The main session re-derived the v8 repoint `49d1fd5f…` and checked the edit-buttons claim at `run_e2_c_product_path.py:7197–7208`. One open prediction: the v20-only `#page-status` line.
   - **Production-UI blocker found and resolved.** Rbs/Rdel scored a refusal plus reopen and B3x scored three refusals to the ceiling. On v20, C makes those keys `verified-boundary-noop`, so all three arms were red by construction. SPEC-M3-link-batch §10.7's list had missed them.
     - Witness `f3b543c9` (non-counted, runner unedited).
     - Rbs/Rdel re-expected under C, keyed on the bytes of the wasm the host serves (`65a8ec1c`; the merge runner's `boundary_noop_declared` precedent; fail-closed). All 30 committed production-UI runner reports re-score byte-identically. The 4 `no-scope/*.json` files differ only in traceback line numbers: they have no `runs` and were never runner reports. The C-branch red cases read 6/6.
     - **B3x withdrawn from this count** (AGENTS.md §4: its premise is false under C).
     - AGENTS.md §3 registration: A1-5 and A1-2′ R's rescue across a refusal still exist (e.g. Delete at a table cell's end) but nothing counted induces them. Spec §17.3.
   - **Named limit §17.4** (`c85118a8`, the main session's review; no code, because §34.4 has no witness). Under C, Rbs/Rdel have no positive control: a swallowed key would read green. RESULT must confirm, by hand, one busy span ≥ 2,000 ms with `rev` unchanged for every counted R run. The witness shows 2,257–2,261 ms against ≤ 905 ms for every other span. A run without it reads NOT_ESTABLISHED for that arm.
   - The B3x toast 「回到檢查點：editor cannot restart from ready」 is **harness-only**: the runner JS-clicks a hidden `#notice-action` (`web/e2-editor.html:214`). It is not a product finding.

## For the owner (in the morning)

1. **The window.** Agree a window in which you will not open `litecore.ddev.site`. Then start the chain:
   ```
   cd /home/jiajun/LibreOffice/study_LiteCore
   setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.23/chain-0.2.23.sh --owner-window "<window>, agreed by the owner at <time>" > /dev/null 2>&1 &
   ```
2. **B3x withdrawal** (the main session's decision under AGENTS.md §4; reversible: put the step back, and it will read red by construction). Confirm or overrule.
3. **Your file `m3-109 測試.odt` (fileId 7340).**
   - The production-UI runner uploads over it at every arm. This is not new: every M3 count has done it.
   - Tonight's witness overwrote it; it is now 567,408 B.
   - The pre-witness version is in Nextcloud versions as `m3-109 測試.odt.v1791975573` (2026-10-14 18:59, 567,309 B).
   - The count will overwrite it many times. Copy it first if you care about its contents.
4. **Makefile.** Should the two judge test files join a target?
   - **A (lean):** add them to `test-e2-c-static`. It costs about 17 s, and nothing would ever again go red without being noticed.
   - **B:** add a separate `test-m2-judge` target.
   - **C:** leave them to the chain's P6 only.
5. Optional, 10 s: `keyrepeat-check.html` (§7 D).

## §34.4

- This file: repaired because of execution **2**:
  - V19Witness `00903e29`; its witness is the v19 X7 reports.
  - `check_m3_production_ui.py` `65a8ec1c`; its witness is `f3b543c9`.
- Repaired because of review **0**. §17.4 is a registration, not code.
- Running total since 10-14b: **execution 7, review 18** (the 18 are the two judges' spent §34.3 budgets, as before).

## Next (in order)

1. The owner's window → start the chain (above).
2. **After `DONE`**, run `bash findings/evidence/m3-production-ui/runs-0.2.23/read-0.2.23.sh <LOG>`. Then write RESULT in the shape of `RESULT-0.2.12.md`, applying:
   - J-a.2's reading table;
   - J-b's C2 table, attributable meaning only `chrome owner-gap80 on-screen max` < 200, with the rate always written;
   - §17.4's hand check of the R-arm busy spans;
   - the product-path reader made red once on scratch copies first, with its verdict taken from the `SUMMARY` line;
   - `judge_counted_m2.py --profile e2-editor-v20`;
   - the descriptive v20-vs-0.2.12-v19 comparison;
   - the expected production-UI `--red-cases` reading: 27/27 with 13 `no passing B3x run` notes, exit 1 by the every-mutation rule.

   Then re-check every number in the release text against RESULT.
3. If the count holds: 0.2.23 becomes the nominal shipped version. The release text gets finalised.
4. **The next link batch** (unchanged from 10-15):
   - `Language=` with 031's fix;
   - Markdown paste (A);
   - D12;
   - `handleEditorPlaceCaret` on `TEXT_SELECTION`;
   - a manifest field declaring C;
   - an immediate answer at document boundaries;
   - 142's `move-document-start`/`end`.
5. **Later.** Unchanged from 10-15, plus three items from tonight:
   - **new:** an A1-5 / A1-2′ R arm on a fixture with a real refusal (new mechanism; a work item only);
   - **new:** a boundary hold longer than two windows, and an unflagged hold (re-run 10-14q's N1);
   - **new:** the 8 probe folders in the admin trash bin from tonight, plus 16 older ones (all fixtures; the owner may empty them).

## Subagents (roles; not reachable from a new session)

- **fable:** count prep (chain, reader, product-path PREDICTION) and the production-UI re-expectation.
- **sonnet:** the boundary-hold measurements and the production-UI witness.
- **Main session (opus):**
  - the A–H decisions, the binding and the V19Witness repair;
  - re-reading every agent measurement from raw logs with its own reader;
  - the review of fable's work: re-derived the v8 repoint, checked the C2 cells and merge modes against their precedents, re-scored the witness with and without keying;
  - found §17.4's missing positive control.
