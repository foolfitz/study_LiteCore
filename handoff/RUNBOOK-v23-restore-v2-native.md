# One owner build for the versioned restoration experiments

The original 45-cell RESET cohort failed and is retained unchanged in `native/reset-restore/out-01` (commit `f8e6370c`). Do not use the original single RESET in the engine. Specification appendix 18 and the new versioned ARMS define the next measurements. No new native compilation or execution has occurred yet.

The new source is a separate copy at `findings/evidence/link-batch-v23/native/restore-v2/tool/oc_native.cpp`. Its Q operation performs RESET→START→RESET synchronously at one recorded point without intermediate reads. E performs END for the format continuation. F/G stage the exact asynchronous fallback: K1+Escape(no listener) in one poll, then a guarded key in the immediately following poll. Op poll indices make the timing observable. The original harness and its cohort source hashes are unchanged.

## Owner compilation

The output directory is prepared. This compiles only the small native harness and normally takes a few seconds. Run from any directory, and return the compiler result and hash:

```bash
g++ -std=c++17 -O2 -Wall \
  -I /home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8/include \
  /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch-v23/native/restore-v2/tool/oc_native.cpp \
  -ldl -lpthread \
  -o /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-restore-v2-native/oc-native
sha256sum /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-restore-v2-native/oc-native
```

This is not the v23 diagnostic WASM link. The agent records the actual binary and input hashes before running anything. A reported compilation success without a supplied log is recorded as owner-reported, not as an observed compiler transcript.

## Agent measurements after a successful build

Run sequentially, using fresh output and work directories. The DELETE cohort is 45 processes (about 10 minutes), FORMAT is 40 processes (about 12 minutes). Stop to assess an instrumentation failure; do not erase failed artifacts or rewrite criteria. These commands are from the repository root:

```bash
python3 -I findings/evidence/link-batch-v23/native/restore-v2/delete/run_delete.py \
  --binary /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-restore-v2-native/oc-native \
  --install /home/jiajun/LibreOffice/study_LiteCore/native-lok-26-8/build/instdir/program \
  --out /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch-v23/native/restore-v2/delete/out-01 \
  --work /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-restore-v2-native/delete-work-01
python3 -I findings/evidence/link-batch-v23/native/restore-v2/delete/read_delete.py \
  findings/evidence/link-batch-v23/native/restore-v2/delete/out-01
python3 findings/evidence/link-batch-v23/native/restore-v2/format/run_format.py \
  --binary /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-restore-v2-native/oc-native \
  --install /home/jiajun/LibreOffice/study_LiteCore/native-lok-26-8/build/instdir/program \
  --out /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch-v23/native/restore-v2/format/out-01 \
  --work /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/v23-restore-v2-native/format-work-01
python3 findings/evidence/link-batch-v23/native/restore-v2/format/read_format.py \
  findings/evidence/link-batch-v23/native/restore-v2/format/out-01
```

Only each cohort's complete reader result can establish its own restoration. No run or missing evidence means `NOT_ESTABLISHED`; failures remain failures. Read raw saved documents, undo and subsequent selection witnesses, not only the final verdict. A pass does not close L-C-number-or-indent, add new actions, change the Writer core, or authorize a host rollout.

The asynchronous fallback is compiled into this binary to avoid another owner build, but is not run automatically. If Q is sufficient, leave it dormant. If needed after adjudication, complete the dedicated runner/reader and controls for `restore-v2/fallback/ARMS.md` before any counted fallback execution. Existing uni1f setup settles precede F; no settle occurs between F and G. A delayed/stabilized key is not acceptable evidence for the exact next-poll prerequisite.
