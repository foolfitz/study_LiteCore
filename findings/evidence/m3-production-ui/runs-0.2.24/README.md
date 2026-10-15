# The 0.2.24 count chain (host 0.2.24, engine v20): 0.2.23's chain on finding 145's fix

Prepared 2026-10-15 by the main session, **not run**. 0.2.23's chain ran to `DONE` (`../runs-0.2.23/chain-20261015T025837Z.out`) and its count did not hold: the merge step read `VERDICT FAIL`, explained by finding 145 (`findings/145-…md`, `findings/evidence/145/`). The owner chose A: fix the page, ship 0.2.24, run the full chain again.

## What changed from 0.2.23's chain

- **Identity:**
  - page `901dd6a6…` (`f7887ced`), shell v73 `6ab20f68…` (`2c3c6ed5`);
  - host `1479e56` 0.2.24, installed with `ddev occ upgrade`;
  - engine package `d3cd39bbc71ec311`, archived read-only in `wasm_sdk_probe/build/archive/host-0.2.24-engine-d3cd39bbc71ec311/` (`findings/evidence/host-0.2.24/`).
- **Pins** moved in `a8b5ff33` (`findings/evidence/host-0.2.24/repin_0224.py`).
- **Scripts:**
  - `chain-0.2.24.sh` is `../runs-0.2.23/chain-0.2.23.sh` with PAGE, ARCHIVE, the evidence directories (`runs-0.2.24`, `release-0.2.24`) and three message lines changed (`diff` them). Steps, preflight, desk lines and the STOP rule are 0.2.23's.
  - `read-0.2.24.sh` is `read-0.2.23.sh` with paths moved and the production-UI expectation now **`red cases: 28/28`** with 13 `no passing B3x run` notes, exit 1. The extra mutation comes from `74489aa0`.
- **Checks repaired after 0.2.23's chain, with witnesses (§34.4 execution +2, `74489aa0`):**
  - production-UI A3-1 allows the page-number line (`../witness-page-status-0.2.23/`);
  - the assets red case K1-6 finds the served profile's manifest (`../../m3-assets/witness-v20-red-cases/`).
- **Product path:** `../../release-0.2.24/product-path/judge.py` (constants `901dd6a6…`, v8 repoint `daa868d3…`) and `PREDICTION.md`, both written before any run.
- **B3x stays withdrawn** (SPEC-M3-link-batch §17.3; same engine v20). The owner confirmed it for 0.2.23 at 06:43.

## Preflight only (`preflight-only-2026-10-15.txt`, 12:28Z)

- P0–P4 ok. P4 reads `901dd6a6…` for dist, web and archive, and the installed host serves the same; host `1479e56` 0.2.24, clean.
- P6 ok: 134 unit tests and the static gate's 108.
- **P5 refused twice:**
  - no owner window, by design;
  - **`oc_files_lock` rows: 2.** Both are `admin` locks, type 2, ttl 300 s, created 16:34:46 and 16:35:56 local. They sit on `新文件 測試資料夾/新文件 測試-TW-chrome-083420Z.odt` and `…-EN-chrome-083530Z.odt`, the files 0.2.23's counted new-document run made (08:34–08:37Z).
  - They expired four hours ago. They are left because no host-touching runner ran after new-document in that chain (product path, merge and C2 serve `dist/` locally). They are the runner's, not the owner's.
  - They are **not** deleted here: deleting is a write to the owner's instance and waits for the owner. If the owner agrees, the two rows go by id (4426, 4430) before the start, and the next preflight must read 0.

## Start (after the owner agrees a window and the two rows)

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.24/chain-0.2.24.sh \
     --owner-window "<window>, agreed by the owner at <time>; B3x withdrawal as confirmed for 0.2.23" > /dev/null 2>&1 &
# progress: tail -f wasm_sdk_probe/build/m3-count-<stamp>/chain.txt
```

About 8.2 h (7.5–9.5 h). During it:
- no `litecore.ddev.site`;
- no core build;
- no `ddev start`, `stop`, `restart` or `poweroff` of **any** ddev project (0.2.23's stop-1: another project's start recreated the shared router, `../runs-0.2.23/stop-1/`);
- no edit to any file a runner imports (finding 145's N1: three runs died on a mid-run edit, `findings/evidence/145/n1/failed-on-my-edit/`).

After `DONE`: `bash findings/evidence/m3-production-ui/runs-0.2.24/read-0.2.24.sh`, then the hand readings 0.2.23's README lists: J-b.2 on C2, §17.4's R-arm busy spans, the product-path reader made red once offline, RESULT.
