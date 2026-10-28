# Pipeline finished: R1 PASS; S5 stopped at the first table/type failure

The detached process continued after the prior conversation ended. It completed R1 and stopped S5 by its prescribed first-nonpass rule at 2026-10-27 17:18:20 +0800. This is **not** a server-interruption stop. The recorded PID is historical; no collector/launcher/judge remains running at the 2026-10-28 checkpoint. `status.json` is the preserved terminal status `STOPPED_FIRST_NONPASS`.

- R1: full **144/144 PASS** (72 per browser), runner and independent judge both exit 0. Report and independent output hashes match their command receipts. A 2026-10-28 independent-judge replay exits 0 and is byte-identical to the original output.
- S5: **401 PASS, one FAIL**, all Chrome; zero Firefox observations, incomplete population. Stop cell `shift-Right@cell-end/type`, `sequence result differs from its reference`. Runner exit 1; aggregate refuses the incomplete report as expected. No partial count is credited. Fresh two-browser diagnostic prep-07 reproduces the failure and retains plain-text positive controls.

`completion-read-01.json` and `read-completion.py` verify the frozen declaration/config/current source/prerequisite/actual-mirror hashes, terminal stage receipts and every raw cell SHA. They re-read all **546** observed complete inspections without ignored fields. JSON round-tripping preserves tuple-valued logical positions as their original JSON arrays. The generated expected population is checked against the actual unique full R1 sequence and S5 prefix. A wrong raw-receipt SHA control refuses independently in each stage. This reader does not fill the unobserved S5 population or replace its aggregate refusal.

From the repository root, choose a fresh output path:

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/counted-r1-s5-01/read-completion.py --output FRESH-OUTPUT.json
```

The archived source/config/declaration identities are unchanged. No product, oracle, profile, shell generation or frozen acceptance tool changed. `../STORAGE.md` documents verified lossless archives/restoration for R1, stopped S5 and diagnostic prep-07. Raw JSON copies remain locally available; original aggregate judging needs those report-listed paths. The next task is finding 168 and its prospective resolution, as described in `../s5-table-type-diagnostic-01/README.md`. Do not relaunch this pipeline or resume either old output directory.
