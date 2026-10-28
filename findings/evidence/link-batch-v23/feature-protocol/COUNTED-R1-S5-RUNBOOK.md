# Frozen R1 → S5 measurement pipeline

The owner authorized continuing after the delegated Astra A ruling. The launcher `run-counted-r1-s5.py` runs a predeclared full R1 population, independently judges it, then runs and independently judges the fresh full S5 population. It has no retry and stops at the first nonpass or input drift. The model-only dry-run artifact verifies positive sequencing and stop behavior for runner failure, judge failure, changed input and existing output.

The frozen declaration will be `counted-r1-s5-01/cohort.json`; it is created only after successful final-plan S5 preparation 06. Its plan/config hash binds all generated members and inputs, with explicit stage populations and commands, prerequisite hashes and the launcher hash. Frozen plan and source archive accompany it. The counted directories are distinct fresh outputs, `r1-counted-01/` (72 cells per browser) and `s5-counted-02/` (588 per browser). No preparation or partial-run credit is carried.

While running, inspect `counted-r1-s5-01/status.json` and its per-stage runner logs. `RUNNING_R1` or `RUNNING_S5` is progress, not acceptance. `BOTH_COHORTS_PASS` requires both complete runners and both independent judges to exit 0 with matching frozen inputs. `STOPPED_FIRST_NONPASS` and `STOPPED_EXCEPTION` mean preserve the first observation and investigate; do not restart the same directory or skip to the later stage. Cell receipts in each report bind the raw JSON. The aggregate judge needs these raw JSON files, so do not remove them while a stage might still be independently judged.

Do not edit the frozen Python import closure, served sources, profile, fixtures or native certificate inputs during either stage. Documentation and evidence records outside that closure can be committed. A new agent must inspect status/processes before starting any browser/native measurement. The pipeline serializes its own stages; the existing browser lock guards cooperating collectors. Do not interrupt unrelated processes. No compiling make or native execution belongs to this pipeline.

From the repository root, this read-only status command is sufficient for a checkpoint:

```bash
python3 -I - <<'PY'
import json
from pathlib import Path
p=Path('findings/evidence/link-batch-v23/feature-protocol/counted-r1-s5-01')
print((p/'status.json').read_text())
for name in ('r1-counted-01','s5-counted-02'):
    report=p.parent/name/'report.json'
    if report.is_file():
        r=json.loads(report.read_bytes())
        print(name,len(r['runs']),r.get('nonpassing',[]),'postConfig' in r)
PY
```

Preparation/control PASS and the independently established four product arms remain scoped conclusions. Neither a running pipeline nor S5/R1 acceptance establishes overall product acceptance, Firefox 096 B2/B4, remaining named inputs, host/DDEV, K, finding 166's unipoll arm or finding 167's desktop-Writer question.


## Terminal checkpoint, 2026-10-28

The pipeline is finished: terminal state `STOPPED_FIRST_NONPASS`, completed at 2026-10-27 17:18:20 +0800. R1 is complete PASS (144/144, both commands exit 0). S5 is incomplete (401 Chrome PASS, then table/type FAIL at `shift-Right@cell-end/type`; zero Firefox cells). No launcher/collector/judge remains running. The stop preceded the later daemon restart and was caused by the retained first FAIL. See `counted-r1-s5-01/README.md`, its verified completion reader and finding 168. Do not rerun the launcher or reuse existing output names. Archived raw JSON is restorable with the indices in `STORAGE.md`; restoring bytes changes no verdict/count.
