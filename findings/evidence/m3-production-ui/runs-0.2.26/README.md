# The 0.2.26 count chain (host 0.2.26, engine v21): 0.2.24's chain on the v21 candidate

Prepared 2026-10-17 by the main session, **not run**. 0.2.24's chain ran to `DONE` and its count held (`../RESULT-0.2.24.md`). This count is SPEC-M3-link-batch-v21's criterion **K** (§1, §11.1 K; §12.6): until it holds, v21 is an uncounted candidate and the nominal shipped version stays 0.2.24. The owner said they will run it by hand and open a session afterwards to have it read (handoff 10-17b "Next" 5).

## What changed from 0.2.24's chain

- **Identity:**
  - engine **v21** (`e2-editor-v21`, wasm `db3408f5…`, worker `0d55bcfa…`), item 1 only;
  - page `605cf24b…`, shell v74 `27f33a13…` (`4628c9d3`);
  - host `3c01876` **0.2.26** = 0.2.25 + finding 154's host rule, installed with `ddev occ upgrade`;
  - engine package `f5f0df762e1855f2`. 0.2.26 carries 0.2.25's package byte for byte, so `ARCHIVE` is `wasm_sdk_probe/build/archive/host-0.2.25-engine-f5f0df762e1855f2/` (`findings/evidence/host-0.2.26/`).
- **Pins:** moved in `a643de39` (`findings/evidence/host-0.2.26/repin_0226.py`, 11 files, 25 lines). The merge `BINDING` moved in `7ea8038f` (`findings/evidence/link-batch-v21/binding-v21/`).
- **Scripts** (`diff` them against `../runs-0.2.24/`):
  - `chain-0.2.26.sh`: PAGE, ARCHIVE, the evidence directories (`runs-0.2.26`, `release-0.2.26`), the candidate `e2-editor-v21` for the merge count, the product-path plain arm and the judge line, and message lines. Steps, preflight, desk lines and the STOP rule are 0.2.24's.
  - `OURS` (P3 and the desk) is widened by `run_v21_|diag_v21_`. This is chain-local, as P0 and P6 are. It only adds refusals: today's v21 shakedown runners and diagnostics did not match J-a.1's pattern.
  - `read-0.2.26.sh`: paths, `pooled-0.2.26.json`, `--profile e2-editor-v21` and its wasm line. The production-UI expectation stays **`red cases: 28/28`** with 13 `no passing B3x run` notes and exit 1, because the runner is unchanged (`24be3053`). The no-passing count no longer counts its own `expected:` line, which read 14 in 0.2.24.
- **A check repaired before this chain, with a witness** (§34.4 execution +1, `94b4913e`): page honesty §7.14. V2's writable arm no longer asks a button the page hid at census to advance. That is v21's withheld `paste-markdown`; without the repair the chain would STOP at its first shakedown. Witness and red cases: `../../m3-page-honesty/fix-7.14/`.
- **Product path:** `../../release-0.2.26/product-path/judge.py` (plain arm v21, constants `605cf24b…` and v8 repoint `ea3b6bad…`) and `PREDICTION.md`, both written before any product-path run on v21.
- **B3x stays withdrawn** (SPEC-M3-link-batch §17.3): engine v21 also carries C. The owner re-confirms it in the window string, as for 0.2.24.

## First contact, before the window (not part of the count; `../../link-batch-v21/first-contact/`)

- **The chain's shakedown phase, run as the chain runs it** (`shakedown-phase.sh`, 11:20–12:37Z): page honesty, locks, versions, assets, host entry, same second, the autosave gate and new-document all exit 0 and read clean.
- **The merge runner's shakedown on v21** (Chrome, 1 round): its recorded `bound` equals `BINDING`. All 26 cases' outcomes occur among v20's counted rounds.
- **The product-path net on v21** (plain arm, Chrome and Firefox, 1 round each): see below.

## Preflight only

See `preflight-only-2026-10-17.txt` and the note appended below once it has run.

## Before the start: two lock rows (the owner's call)

`oc_files_lock` has 2 rows. Both are `admin`, type 2, ttl 300 s, created 20:34:45 and 20:35:51 local, on `新文件 測試資料夾/新文件 測試-{TW,EN}-chrome-…Z.odt`: the files the first-contact new-document shakedown made. They expired long ago and are the runner's, as in 0.2.24. P5 refuses until they are gone. Deleting them is a write to the owner's instance, so it waits for the owner's yes:

```bash
cd ~/Projects/Nextcloud_Apps/litecore
ddev mysql -e "DELETE FROM oc_files_lock WHERE id IN (4882, 4886);"
```

Then the preflight must read 0.

## Start (after the owner agrees a window and the two rows are gone)

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.26/chain-0.2.26.sh --owner-window "<window>, owner at <time>; B3x withdrawn as for 0.2.24" > /dev/null 2>&1 &
```

Progress: `tail -f wasm_sdk_probe/build/m3-count-<stamp>/chain.txt`.

About 8 h (0.2.24's took 7 h 59 m). During it:
- no `litecore.ddev.site`;
- no core build;
- no `ddev start`, `stop`, `restart` or `poweroff` of **any** ddev project (another project's start recreates the shared router);
- no edit to any file a runner imports;
- the desktop Chrome closed (its extension renderer voided timing cells on 10-17).

After `DONE`, in a new session: `bash findings/evidence/m3-production-ui/runs-0.2.26/read-0.2.26.sh`, then the hand readings 0.2.24's README lists: J-b.2 on C2, §17.4's R-arm busy spans, the product-path reader made red once offline (PREDICTION.md), and RESULT-0.2.26.md.
