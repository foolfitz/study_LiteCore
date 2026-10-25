# v23 resume: native RESET prerequisite, then diagnostic C

The owner's explicit request to resume v23 supersedes the spreadsheet-first pause. It does not make the old link command ready. The chosen sequence remains diagnostic candidate C on the Writer headless core, editor ABI 5; feature action additions later require ABI 6. Keep Calc's separately built successor core separate from Writer. `wasm-lite/build-headless-probe/config_host/config_wasm_strip.h` still defines `ENABLE_WASM_STRIP_ACCESSIBILITY 1`; `build-a11y-gate0` defines 0. Installing a Calc profile did not change the Writer v22 link or give it accessibility.

Astra owns the diagnostic build checker additions and native RESET preparation. The coordinating agent owns engine/SDK/Makefile wiring. The new diagnostic checker accepts `--wasm PATH` for actual linked-byte absence/presence checks, and `--feature-build-log LOG [--feature-build-dir DIR]` to reject diagnostic instrumentation in feature compilation/linking. `--self-test` covers 23 fixed green/red inputs. The current Makefile is expected to remain red until the coordinator creates the diagnostic target. A passing old Writer binary marker check proves only its accessibility build precondition, not v23 behavior or identity.

## First owner action, after source review

The original specification requires the native RESET result before writing that engine branch. The harness/arms/reader are source-complete but have not been compiled or run. This is a small native harness compilation, not a LibreOffice core build, normally a few seconds. The agent must not run it under the current owner instruction. The directory `wasm_sdk_probe/build/v23-reset-native` is prepared. Run this from any directory:

```bash
g++ -std=c++17 -O2 -Wall \
  -I /home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8/include \
  /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch-v23/native/ordered-commands/tool/oc_native.cpp \
  -ldl -lpthread \
  -o /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-reset-native/oc-native
sha256sum /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-reset-native/oc-native
```

Report the compiler exit/result and binary hash. Do not run any old v23 or frozen-profile relink command yet. After successful compilation, the agent performs the native finite measurement, without services or live documents, from the repository root:

```bash
python3 -I findings/evidence/link-batch-v23/native/ordered-commands/tool/run_arms.py \
  --binary /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-reset-native/oc-native \
  --install /home/jiajun/LibreOffice/study_LiteCore/native-lok-26-8/build/instdir/program \
  --fixtures /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch-v23/native/ordered-commands/fixtures \
  --out /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch-v23/native/reset-restore/out-01 \
  --work /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-reset-native/work-01 \
  --arms-set r --modes unipoll --runs 5
python3 -I findings/evidence/link-batch-v23/native/reset-restore/read_reset.py \
  findings/evidence/link-batch-v23/native/reset-restore/out-01
```

The runner must use a fresh output path; its existing append-only run log makes rerunning a cell in place fail the reader. Expect roughly 10–15 minutes for 45 separate native processes. Capture the command, current harness/runner/reader/fixture hashes, binary hash, compiler result, and output. A smoke, if needed to diagnose instrumentation, uses a separate output path and is never counted as part of the N=5 cohort.

## Remaining diagnostic sequence

1. Finish the original red gates: callback-flush composition, both proof-absent refusal branches, K1's three selection-oracle branches, empty SelectText refusal, and routing/preprocessor exclusion of the old staging loops. Existing ordered-poll/witness/reply-state helpers remain useful but are not yet engine wiring evidence.
2. Wire one command per poll, pending reply first, no poll blocking, replies composed only at the first post-command poll, callback-only evidence caching, and diagnostic instrumentation under one diagnostic-only define. Keep the existing headless core and ABI 5. Do not quietly add Shift/feature actions or a core switch to this diagnostic.
3. Adopt the measured RESET branch only after `RESET-HOLDS`; otherwise stop that adoption and adjudicate the specified alternative with the failed evidence intact.
4. Complete diagnostic Makefile/profile-builder/reader identity checks and the exact owner diagnostic compile/link runbook. Only then ask the owner to run that command. The native harness command above is not that diagnostic link.
5. Read the actual compile log and resulting WASM bytes, execute the predeclared diagnostic browser gates, then prepare feature ABI 6 and its own action/manifest/red gates. Feature compilation must exclude the diagnostic define and stack-overflow-check flag. No stale 0.2.29 host release or historical K window is implicitly authorized by this document.

No native compilation, WASM link, service action or live-document mutation was performed during this preparation. The current host release and cumulative counters belong to the coordinator's latest handoff; the paused handoff's 0.2.28 and 33/27 values are historical, not the resumed baseline.
