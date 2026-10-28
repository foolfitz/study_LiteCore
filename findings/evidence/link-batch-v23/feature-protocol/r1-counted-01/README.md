# R1 first complete counted population: 144/144 PASS

The full frozen population completed in Chrome and Firefox: **72 PASS per browser, 144/144 PASS**, complete population and aggregate `R1: PASS`. Runner exit 0; independent aggregate judge exit 0. Launched from `../counted-r1-s5-01/cohort.json`, committed before execution at `28e4295e`, using final config SHA-256 `0a47d0e82fc5b8f9d43e3aa3c59fab6592510526356a1100b9e70b38e2f91552`. No filters, preparation-only, keep-going or retries. The per-browser population has 36 literal and 36 layout-relative oracles; all six prescribed wrong-old-click controls across both browsers pass.

Runner: 2026-10-27 13:36:34–15:11:43 +0800, 5,708.5 s. Independent judge completed at 15:12:07. `commands.json` and the stopped pipeline's retained status preserve exact commands/times/exits. Report SHA-256 `cf943eb9d6878da832f9fb71289f0e5fd4ff2bcba1361a9fab5d1914b619224a`; independent output SHA-256 `2c23a8a34e1ab81355f342f8847b8757967273b8bfaa33b9064b889e92091d3d`. The report has identical initial/final configs, the required 32-cell historical EXPECTED_RED prerequisite, valid actual mirror bindings and the complete generated population. Source/prerequisite/stage-receipt hashes were checked again on 2026-10-28.

On 2026-10-28, re-executing the independent judge against the retained raw records exits 0 and produces **byte-identical output**, preserved as `aggregate-judge.reread.stdout.json` with empty stderr. No product or input change was made. This establishes R1 within the frozen protocol, independently of the later S5 stop; it does not establish overall product acceptance or any unmeasured obligation.

Raw report-listed cell JSON remains locally available. Lossless deterministic `.json.gz` storage and its index retain the exact uncompressed bytes and report receipts. Restore raw records before replaying the original aggregate judge on a checkout that has only the compressed archives; the exact frozen tool/profile/native environment is also required. See the sibling storage instructions and `../counted-r1-s5-01/frozen-sources.tar.gz`.

From `wasm_sdk_probe/`, after restoring raw cells if necessary:

```bash
python3 -I tools/judge_v23_feature_selection.py ../findings/evidence/link-batch-v23/feature-protocol/r1-counted-01/report.json
```
