# Formal S-init execution commands

Prepared only. Runtime remains on hold until the coordinator releases the shared browser lock. Run from `/home/jiajun/LibreOffice/study_LiteCore`. The default unfiltered runner population is six cases × two profiles × two browsers × three rounds = 72 cells. No preparation result contributes to this count. Monitor each newly written cell and each completed profile pair; stop the owned runner on the first failure, refusal, or mismatch, preserving its records and source graph.

```bash
python3 -I wasm_sdk_probe/tools/run_v23_s_init.py \
  --v22-wasm-sha256 f7a40bcce073d913e562245b96f32a1051766dda23da0da3911741f03934d49e \
  --candidate-wasm-sha256 683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078 \
  --output findings/evidence/link-batch-v23/post-link/r2-attempt-01/s-init-counted-01 \
  > findings/evidence/link-batch-v23/post-link/r2-attempt-01/s-init-counted-01-runner.txt 2>&1
```

Only after the complete run, retain both actual reader output and its exit status:

```bash
python3 -I wasm_sdk_probe/tools/judge_v23_s_init.py \
  findings/evidence/link-batch-v23/post-link/r2-attempt-01/s-init-counted-01/report.json \
  --v22-wasm-sha256 f7a40bcce073d913e562245b96f32a1051766dda23da0da3911741f03934d49e \
  --candidate-wasm-sha256 683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078 \
  > findings/evidence/link-batch-v23/post-link/r2-attempt-01/s-init-counted-01/reader-result.json
```

Then retain the independent observation auditor output and exit status:

```bash
python3 -I wasm_sdk_probe/tools/audit_v23_observations.py \
  findings/evidence/link-batch-v23/post-link/r2-attempt-01/s-init-counted-01/report.json \
  --wasm-sha256 683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078 \
  > findings/evidence/link-batch-v23/post-link/r2-attempt-01/s-init-counted-01/observation-audit.json
```

The comparison reader validates both actual profile identities and all 72 cells; the observation auditor independently examines r2 observations and explicitly counts skipped v22 reference cells. Neither replaces the other. Accepted service/fallback residuals remain explicit; equal renders do not establish unavailable dictionary/service capabilities. Preserve the generated mirror locally for actual binding verification but exclude it from version control.
