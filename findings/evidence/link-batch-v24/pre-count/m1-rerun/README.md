# M1 rerun: the native exit-1 teardown recurs (finding 170)

Handoff 10-28d item 5 / spec §10 work item: rerun M1 once to see whether the exit-1 teardown recurs. Same binary (`build/native/f168-m1-01/f168-native-insert-text-m1`, sha256 `62860ff0…31b5`, unchanged since `m1-build-01`), same runner (`tools/run_f168_m1_native.py`), same install and procedure; load 0.34, no `make` at start. No compile.

`run-02/` (2026-10-28 14:28–14:41 +0800, 13 min wall, 27 s user): `completion.json` `exitCode: 1`, `protectedInputsUnchanged: true`; `native.jsonl` 125 lines and 228 saves, as in run-01; `native.stderr` ends with exactly one `Unspecified Application Error`, as in run-01. Reader (`tools/read_f168_m1_native.py`) → `m1-reader-02.json`: **M1_PASS**, 0 problems, 0 failures — every recorded result and save is the same kind as run-01's.

So the anomaly is 2/2 (run-01 and run-02); the four earlier native runs that day and native run-03 (other harnesses) exited 0. Recorded as finding 170 (`findings/170-…md`). Source reading only: the harness's `main` returns 0 or 5 and never calls `destroy`; the line is printed by `SalAbort` with an empty message (`libreoffice-26-8/vcl/source/app/salplug.cxx:348`), i.e. something calls `Application::Abort` with no text while the process tears down. Who calls it was not traced.
