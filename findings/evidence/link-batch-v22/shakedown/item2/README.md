# Item 2 (paste as Markdown) on v22: E2 and I2-v22

The criteria: SPEC-M3-link-batch-v22 §11.2 (E2: v21 §11.2's M0–M11 carried over with the identity moved to v22) and §11.2.1 (fable ruling 6: the first reading, the fix, the re-run, the composed reading).

## Verdict

- **E2: PASS in both browsers.** All 11 M cells are PASS, each read from the report whose procedure ran right (§11.2.1). See the table below.
- **M11's auto-save clause is not established here.** The judge prints `"autosave": "NOT RUN (host arm)"`. M11-autosave runs on host 0.2.27 (§11.2 (c), §11.5), and until it passes, M11's default (no entry) is the standing outcome for the host.
- **I2-v22: PASS** over 13 identity blocks (`../item2-rerun/i2-v22.txt`).

## Where each cell comes from

| cell | Chrome | Firefox | source |
|---|---|---|---|
| M1 | PASS (87) | PASS (87) | first reading |
| M2 | PASS (3) | PASS (3) | first reading |
| M3 | PASS (201) | PASS (189) | first reading |
| M4 | PASS (171) | PASS (171) | first reading |
| M5 | PASS (114) | PASS (111) | **re-run** |
| M6 | PASS (3) | PASS (3) | Chrome: first reading; **Firefox: re-run** |
| M7 | PASS (6) | PASS (6) | first reading |
| M8 | PASS (3) | PASS (3) | first reading |
| M9 | PASS (9) | PASS (9) | first reading |
| M10 | PASS (96) | PASS (96) | first reading |
| M11 | PASS (6) | PASS (6) | first reading; auto-save clause NOT RUN (host arm) |

The two judge outputs, both from the unchanged `judge_v21_shakedown_item2.py --expect-page 3b96cb16…`:
- **first reading:** `first-reading/judge-item2-first.txt`, which ends `VERDICT NOT PASS`, exit 1. Every cell is PASS except `M5: NOT_ESTABLISHED (0 passed)` in both browsers and `firefox M6: NOT_ESTABLISHED (2 passed) r2: foreign CPU load`.
- **re-run:** `../item2-rerun/judge-item2-rerun.txt`, which ends `VERDICT NOT PASS`, exit 1, by construction (ruling 6 item 8). Every other cell reads missing or zero instances there. Only three lines are read: `chrome M5: PASS (114 passed)`, `firefox M5: PASS (111 passed)`, `firefox M6: PASS (3 passed)`.

## What happened

### M5 in both browsers: a binding the v22 move missed

- `v21_network.positive_control` defaulted `profile` to `e2-editor-v21`, and the runner did not pass one. The M5 mirror served `e2-editor-v22`, so every round's positive control was recorded `None`, and the judge's rule (no control → NOT_ESTABLISHED) fired before any item was read.
- The kept proxy logs hold only v22 `probe.wasm` GETs: Chrome 149, Firefox 123, v21 0.
- How much of each round the kept log covers. The report keeps only the last 3000 entries, so this is the coverage as measured, not "only r3":
  - round 1: nothing, in either browser;
  - round 2: the round's later GETs (Chrome 71, Firefox 45);
  - round 3: the round-start GET.
- Diagnostic, not a verdict: `first-reading/m5-positive-control-diagnostic.txt`.
- Fixed in `1b393f8f`: the profile is a required argument, and `arm_m5` passes the profile its own mirror was built with. §34.4: repaired because of execution **+1**. The witness is these two reports, committed first in `22bc3df4`.
- The same default in `v21_workers.shipped_worker_text` was a 0/0 binding: v21's and v22's `sdk-worker.js` are both `0d55bcfa…`.
- The re-run reports record the control in all three rounds of both browsers.

### Firefox M6 r2: the owner's desktop Chrome

`foreignCpu` before r2's paste (the 2 s pre-sample):

```
ok: false
overLimit: pid 3010325, chrome --type=renderer --crashpad-handler-pid=2745205 … --extension-process, 81.0 %, own: false
```

- The round's own reading was 558.6 ms (bound 10,000), with Undo restored.
- `desk.log` counted 39–40 Chrome processes at every chain step.
- The re-run ran on a desk with 0 Chrome processes. M6 read 543.1, 592.1 and 568.7 ms, `foreignCpu.ok` true in all three rounds.

## Notes ruling 6 asked for (item 17)

- **`treeHead` differs between identity blocks.** Chrome's `m6` and `main` blocks say `0da3cc33`; its `bytes`, `trace`, `v20` and `m5` blocks say `ad1bc0e7`. Every Firefox block says `09855075`, and the re-run blocks say `1b393f8f`.
  - The judges do not read `treeHead`.
  - Every v22 block's served hashes are equal: page `3b96cb16…`, wasm `f7a40bcc…`, loader `dc4c2c84…`, worker `0d55bcfa…`, manifest `000921c1…`, HTML `b9c2b975…`.
  - `git diff --name-only 0da3cc33..HEAD` touches no served input.
  - The re-run reports have a different `runnerSha256` (`4f25e0bb…` against `fca737b2…`). Their `instruments` hashes differ for `v21_network.py` and `v21_workers.py`, because of the fix, and are equal for the other seven.
- **The first reading's `chrome M5 info … 0 non-target requests` line is an artefact.** Info is gathered only for rounds the judge reads. With the controls present, the first run's Chrome made 11 such requests; the re-run's Chrome made 16 (`mtalk.google.com:5228` ×12, `android.clients.google.com:443` ×4). All are CONNECTs from the proxied runner Chrome, despite `QUIET_CHROME`. They are recorded and not judged (ruling S3). Firefox made 0.
- **Firefox M5 is 111, not 114.** `m0/X03-nul-suffixed-reference.md`'s dialog cell is withdrawn by its read-back in every Firefox round (`inputIntact: false`; v21 §12.2 (c)), so it is judged on R-sdk only. Chrome's clipboard keeps the NUL, so Chrome has 114. Ruling 6 item 12 pinned both counts as PASS before the re-run.
- **I2-v22, read by `python3`** (`../item2-rerun/i2-v22.txt`):
  - It reads every identity block of the four reports E2 is read from: m6, main, bytes and trace, `results.m5.identity`, and the re-run's m6.
  - Every block's profile hashes equal `common.EXPECTED["e2-editor-v22"]`, with the served page `3b96cb16…` and the source HTML `b9c2b975…`. `refuse()` does not read M5's wasm hash; this read does.
  - The `v20` blocks are M8's v20 page and are not I2-v22 blocks.
  - **The reader's first version was wrong** (`../item2-rerun/i2-v22-reader-bug.txt`, kept on purpose). It looked the expected values up under the wrong keys, so every hash read MISMATCH. The second version fixes the keys and carries a red case: one zeroed wasm hash reads MISMATCH.
- **Item 1's `start.entry` reads, as a cross-reference to M8 and not as M8's verdict** (addendum 1 item 12):
  - E0-v22 read the entry on the same page bytes 379 times in I1-rerun's first execution: 0 red, 0 blind (`../item1/first-reading/e0-v22-first.txt`).
  - On every v22-profile read, there was exactly one visible opener, the toolbar button. On every `v20` read, it was hidden.
  - This is independent corroboration of M8's page cell ("shown iff declared").

## Files

- `report-chrome.json`, `report-firefox.json`, `docs-*/`: the chain's item-2 run (Chrome 12:13–14:04, Firefox 14:04–15:58 on 2026-10-19). The step logs are `../item2-chrome.log` and `../item2-firefox.log`.
- `first-reading/`:
  - the first judge output;
  - the M5 diagnostic;
  - a synthetic demonstration of how the unchanged judge reads reports that carry only the re-run arms. Synthetic, not evidence.
- `../item2-rerun/`:
  - `report-chrome.json` (M5, 2026-10-19 22:53–23:07);
  - `report-firefox.json` (M6 then M5, 2026-10-20 01:19–01:35);
  - `docs-*/`, `rerun.log`, `desk.log`, `step.sh`;
  - the re-run judge output;
  - the I2-v22 reading and the reader's wrong first version.

## §34.4

This stretch: repaired because of execution **+3** (F3's two, plus the positive control), because of review **0**. Running total since 10-14b: **32 / 18**.

Registered by ruling 6 (not gates):
- the `bytes`/`trace` identity blocks do not record which worker text the patch was applied to;
- a form-two guard against `profile` defaults in `tools/v21_*`;
- the kept proxy log should cover every round's start.
