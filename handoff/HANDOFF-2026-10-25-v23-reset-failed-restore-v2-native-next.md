# v23: original RESET fails; versioned restore-v2 native build is next

The owner completed the original small native compilation. The agent read binary SHA256 `5071c808b40033bda709f72dc4e4216cdb473b7e218b5a5f5801535faec1779a`, then ran the entire predeclared45-process RESET cohort. All45 children and runner exited0; the unchanged reader exited1 with **RESET-FAILS**,15 restored-landing differences, zero cleanliness problems. Evidence and original input identity are committed in `f8e6370c`, `findings/evidence/link-batch-v23/native/reset-restore/`. Do not erase or reinterpret this failure.

## Why the native prerequisite did not pass

All15 direct/restore pairs have equal saved shape, undo top and settled cursor rectangle. Subsequent real Shift selection differs in every pair: the restored locator reads empty text. Local source `SwEditWin::SetCursorTwipPosition` clears the mark but does not call `EndSelect` in the RESET branch; `SwWrtShell::SttSelect` returns before creating a mark when its selection-mode flag is already set. This supports a source-based latent-mode diagnosis; the flag itself was not directly instrumented. The subsequent selection difference is measured. The separately audited SelectText/FORMAT restoration shares this problem (`fd655ec8`), and finding049's history does not establish Escape as a FORMAT cure.

## Concrete next human action

The next owner compilation is the **new small native restore-v2 harness**, not a WASM link. Its exact command is in `handoff/RUNBOOK-v23-restore-v2-native.md` and was already presented through an asynchronous input request. The new binary `wasm_sdk_probe/build/v23-restore-v2-native/oc-native` was still absent at the final check. Do not infer completion from elapsed time. The output directory exists.

The versioned harness (`dbbe94dd`) keeps original v1 source/reader/counted outputs untouched. Q is synchronous RESET→START→RESET at one recorded point with no intermediate read/yield; E supplies END. F/G stage the exact asynchronous DELETE fallback with observable adjacent poll indices; its separate runner/reader is deliberately not yet claimed ready. Root ran only `g++ -fsyntax-only`, exit0, no output/object/binary. Exact source hash/command are in `native/restore-v2/tool/syntax-only.json` (`5bac7e4c`). No agent ran an actual native/core/project build.

After the owner reports completion, record the actual new binary/input hashes and run the fixed cohorts **sequentially**, with fresh paths, as the combined runbook specifies:

1. DELETE: nine arms×5 =45 processes, approximately10 minutes. `native/restore-v2/delete/run_delete.py` and `read_delete.py`; reader has10 synthetic red controls.
2. FORMAT: eight arms×5 =40 processes, approximately12 minutes. `native/restore-v2/format/run_format.py` and `read_format.py`; reader has16 synthetic red controls, including common positive pollIndex and exact Q primitive records. Both tools support isolated Python invocation. The runner records actual commands/installation and removes only successful owned work after output archival; failed child profiles remain for diagnosis.

Unperformed/unclean/nondiscriminating evidence gives NOT_ESTABLISHED. Each cohort must establish its own restoration use. A DELETE pass alone does not authorize FORMAT, and no pass closes later browser gates or L-C-number-or-indent. The exact async fallback remains dormant if Q suffices; if Q fails, adjudicate its preserved evidence and complete the predeclared fallback reader/runner before counting anything. The new primitive is not in engine code. Spec append§18 records this decision and its finite populations before any new counted execution; the original45 result stays closed and failed.

## Other preparation completed while native work ran

- Diagnostic-only candidate C remains **ABI5**, same Writer headless core with accessibility stripped. Feature/new Shift actions require ABI6 after diagnostic acceptance. Do not switch Writer core because Calc has a separate current core.
- `ordered_format.inc` and its fake-LOK tests prepare the one-command formatting path, including immediate empty-SelectText refusal, but the actual RESET residue audit is a blocker on wiring it unchanged. Fake calls/first-poll tests do not establish native restoration.
- Makefile has isolated E2_V23D build/link/export/derived-worker rules, private `oxsdk_v23_diagnostic(kind,requestId)`, stack-overflow diagnostic flags, and narrowed static carrier-guard selection. Actual engine replacement guards, private C entrance, poll/callback/command routing and final includes/prerequisites are **not implemented**. `probe_engine.cpp` was not changed this turn. Do not present `RUNBOOK-v23-diagnostic-link.md` as ready.
- Claude review attempt01 timed out with no verdict. Shorter review02 succeeded (`f726ff63-2e80-450c-a6fc-1145e99d65e6`) and its source checks exposed real packaging errors. `12e67f94` invalidates manifests on failed packing/post-processing and preserves exact captured diagnostics. `a36b605f` compares the semantic ABI5 contract while verifying the three actual loader/WASM/worker hash bindings separately. `a771f1f9` preserves typed proof failureShape through the actual SDK `_request` and original base-worker cleanup.17 packaging test groups and both worker/SDK tests pass. Root read these source/results; raw reviews/disposition are in `review/resumed-build-0{1,2}/`. `430cc218` preserves the timed-out attempt too; it was never approval.
- `364159aa` adds the packager's imported build checker as a manifest prerequisite. Do not add frozen v22 as a normal make target prerequisite: that can traverse its historical relink rule.
- The private diagnostic ids are positive int32 only, while the SDK generates uint32. Timeout/best-effort cancel does not kill a blocked worker: later diagnostic hang tests must exercise existing session recovery/disposal. No real hang/recovery/browser result has been claimed.

## Agents and preservation

Reusable owner-delegated Astra agents: `/root/astra_calc_scope` owns native results, new shared harness/DELETE/fallback and scope decisions; `/root/astra_v23_format` owns FORMAT preparation/source audit; `/root/astra_v23_build` owns diagnostic build/worker/packager preparation. Root coordinates and owns future `probe_engine.cpp` integration. All are idle/available after their committed subtasks.

Installed host remains0.2.38/package5ad1f70a8c5f7d2f with the completed Calc dark-theme fix. No ddev, live file, lock, service, frozen profile or WASM artifact was touched during this native/preparation turn. Do not reopen Calc acceptance or K; nominal shipped0.2.26 and existing cumulative product counters are not changed by these source/VM/native measurements. Preserve owner documents24674/24920/25391 and all actual current locks, never restore historic content. The unrelated untracked `codex-claude-code-delegation.md` remains untouched/uncommitted. No sudo/root actions. Compiling project make stays owner-run.
