# ABI 6 feature pre-link mechanical checks (partial)

This evidence records the authorized focused C++/packaging checks only. It does not include page JavaScript checks or a product build/link. Exact argv, working directory, exit code, stdout and stderr are indexed in `commands.json`; each command's raw streams are separate files. The complete `make -n` recipe is preserved in `dry-run.log`, and `syntax-command-derivation.json` records the four compile recipes transformed by removing `-c`/`-o` and adding `-fsyntax-only`.

The pre-check source pins matched all 60 captured source, worker/base/export, and local packaging-tooling files against `build-inputs.json`. The feature ABI, profile, and build unit drivers passed (1, 6, and 2 tests respectively); the isolated feature-worker Node test and E1-C bundle guard exited 0. The feature Makefile dry-run exited 0, and `check_v23_feature_contract.py --build-log` exited 0. All four actual feature compile recipes passed syntax-only under `taskset -c 0`; no object files were emitted by these commands.

The run stopped at the existing `check_merge_key_undo_scope.py` carrier audit, which exited 1. Its full stdout is retained in `merge-key-undo-scope.stdout.txt`; the two reported differences are:

```text
FAIL ODS_EDITOR_V2 build/ods/editor-v2/sdk_api.o: preprocessed output differs from 5d77dc84
FAIL ODS_EDITOR_V2 build/ods/editor-v2/probe_engine.o: preprocessed output differs from 5d77dc84
```

The same output reports 36 rules, 139 objects, 30 differences, and one unbuildable historical `FINDING_012_DIAGNOSTIC` probe_engine object. Every listed compile guard exited 1 as required. The checker stderr is empty. No retry or source/criterion change was made, and no post-check source pins were collected after this failure.

The preprocessing command was bounded to CPU 0 (the process affinity set was CPUs 0–11). Immediately before it, `uptime` reported load averages 0.42, 0.28, 0.34; `pgrep -a make` exited 1 with empty output (no matching process). These command outputs and the selected CPU are recorded in this directory.
