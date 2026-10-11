# Handoff, 2026-10-11f — the 5-s Chrome warm-up landed (finding 112's fix, `7fb0ed08`); the whole 0.2.12 count chain is re-running from the top; nothing read yet

Picks up from `HANDOFF-2026-10-11e-count-stopped-at-locks-cert-verifier-second-diagnosis-next.md` (its Addendum's Next 1–3 are done here; its Next 4–6 stand). Repository root `/home/jiajun/LibreOffice/study_LiteCore`. Times: commits +0800, chain and evidence UTC.

## Done this stretch

| Commit | What |
|---|---|
| `7fb0ed08` | `wasm_sdk_probe/tools/run_browser_probe.py` `ChromeSession.__init__`: `time.sleep(5)` after `Network.setCacheDisabled`, before control returns (= before any navigation). sha256 `663b2ffa…` → `2f14d9ddec438c501971eec65d3f38c085413083ac09e855744e39a25390b0d9`. Smoke: construction 5.21 s, `evaluate("1+1")` → 2 afterwards. **Spec §17.23** appended (zh-TW): the stop, both diagnoses, the owner's choices, the change, why it is later than E3 (E3 = first request 5.0 s after *launch*; here 5 s after CDP-ready, which is 0.17–0.26 s after launch), what pins the file (nothing absolute; only `m3-install/equivalence.json` `moduleSha256`, within-window), no separate 0-difference reproduction (reason written), **§34.4 = 因執行而修 7, 因審核而修 5; §17.21's future runner opening becomes 7 → 8**, predictions Q1–Q3, three registered residual risks. `make test-e2-c-static` exit 0, E1-C `intact: true` (`findings/evidence/release-0.2.12/test-e2-c-static-after-warmup.txt`). New chain scripts `runs-0.2.12/chain-2026-10-11b.sh`, `red-cases-2026-10-11b.sh` = the 10-11 pair with only the log directory (`build/m3-count-2026-10-11b`) and header comments changed (diffed). |
| `8629c27d` | Finding 112 updated (zh-TW): status = cause confirmed, fix pending verification; the 10-11 browser-side failure list covers every bundle 10-06's Apache log showed as "never requested" (files-init/main/reference-files, core-common/main, core/files/files_lock/files_sharing l10n) → 10-06 inferred to be the same event; upstream = not a defect (inference from fable's Chromium reading); title meaning corrected in a note (filename kept); timeline + revision log. |

## Running now

- **Chain** `findings/evidence/m3-production-ui/runs-0.2.12/chain-2026-10-11b.sh`, launched detached (`setsid -w nohup`, stdin `/dev/null`) at **2026-10-11T14:39:29Z** on tree `7fb0ed08` (START line: host `b245ae7`, page `8909564eb231`, runner `c9d51781f239c2c3`). Log `wasm_sdk_probe/build/m3-count-2026-10-11b/chain.txt`; stdout `runs-0.2.12/chain-2026-10-11b.out`. Expected end ≈ 19:30Z (0.2.11's chain took 4 h 49 m 37 s; this one adds ~5 s per Chrome launch — Q3 is an estimate, record the actual).
- Launch conditions: desktop Chrome had been opened by the owner minutes before; asked, owner chose 「A 你先關、我再啟動」; Chrome process count 0 at launch. A desktop snap Firefox (pid 777820, up 5 days, ~0.4 % CPU) was running — it was up during the 10-10 and 10-11 chains as well (elapsed time), so conditions match those. Other ddev projects paused; only `litecore` up.
- **Do not edit `wasm_sdk_probe/tools/`, `web/`, `dist/` while it runs.** Doc commits are fine (no runner binds study_LiteCore's HEAD; the `rev-parse` calls in `check_m3_production_ui.py:605` / `check_m3_skeleton_open.py:193` read the host repo).

## Next

1. **When the chain ends, read `chain.txt` and `chain-2026-10-11b.out`.** Read by §17.23's table:
   - **Q1**: locks shakedown 12 Chrome arms all pass (K9′ included); the chain passes all six shakedowns.
   - **Q2**: `grep -l ERR_CERT_VERIFIER_CHANGED` over every report this chain wrote = 0 files. Positive control: the same grep on `findings/evidence/m3-locks/shakedown/2026-10-11T110140+0000.json` finds 86 (43 `loadingFailed` + 43 console errors). Limit: only locks, host entry, same second, versions record CDP load failures; the other four would show a hit only as a Files-page failure / red arm.
   - **Q3**: total duration vs 4 h 49 m 37 s; record, it is not a criterion.
   - **If a reset recurs**: shakedown → the chain stops by itself; counted → that runner's verdict stands by its own rule. Either way back to the owner; **do not widen the wait or add flags yourself** (candidates listed in §17.23).
2. Then `bash findings/evidence/m3-production-ui/runs-0.2.12/red-cases-2026-10-11b.sh` (it pools the three production-UI counted reports and runs `--red-cases` on the six runners' newest `runs/` reports).
3. Then 10-11e's Next 4 = 10-11d's Next 2–6: (2) make `release-0.2.12/product-path/judge.py` red offline once on scratch copies, then `judge-output.txt` and old-vs-new v19 against `../release-0.2.11/product-path/`; watch item first (Chrome `clear-format-removes-every-inline-format` NE in ≥ 2 of 6 Chrome runs → do not read the verdict until diagnosed); (3) `findings/evidence/m3-production-ui/RESULT-0.2.12.md` with the §17.21 line, the three registrations with their if-never-done defaults, **and the §17.23 change + ledger 7/5**, appended to spec §17; (4) statuses of 124 / 125 / 126 by their own criteria, only if the count holds; (5) tell the owner (zh-TW) and offer a hand test of 0.2.12; (6) the one future runner opening of §17.21 (now 7 → 8).
4. **Finding 112**: after the count, flip its status — fix verified if Q1/Q2 hold (add a revision-log row citing the chain), otherwise record the recurrence.
5. Finding 127 (autosave) after the hand test, as 10-11e Next 5 says.

## State

| Item | State |
|---|---|
| Product bytes | Unchanged: page `8909564e…`, shell v61 `f48df85b…`, host 0.2.12 `b245ae7`, engine v19. |
| Runner bytes | Only `run_browser_probe.py` changed (above). The six M3 runners and every value in §17.22's binding table unchanged. |
| §34.4 | **因執行而修 7, 因審核而修 5.** |
| Not pushed | 604 commits ahead of `github/main` at `8629c27d` (before this file). Owner's decision. |

## Open (new this stretch)

1. **The ~62 s component-install reset is not covered by the warm-up.** Seen at 62–65 s in the first round (three installs, 0 hits) and at 61.87 s in the second round's `control-70s.json`, where it sent `litecore.ddev.site:8443`'s HTTP/2 session going away (0 hits). Registered in §17.23 residual 2; if a red comes back with a time near 60 s after launch, look here first (`--disable-component-update` removed the install in the first round's E2, but was never measured as a fix for page hits).
2. Carried: 10-11e Open 2–5 and 10-11d's Open list.

## Standing rules (new this stretch)

- **(nnn) A wait added to a shared launcher is measured against the instant the measurement counted from.** E3 counted 5 s from process launch; the fix counts 5 s from CDP-ready. Written in §17.23 that the fix is *later* than what was measured, not earlier — had it been the other way round, the measured margin would not transfer.
