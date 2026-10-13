## SUMMARY

Task: `handoff/tasks/TASK-2026-10-13f-089-threading-arms.md` (commit 47440469). Profile `e2-editor-v12`. Instrument: `wasm_sdk_probe/tools/probe_ods_on_profile.py`, run from `wasm_sdk_probe`.

**Outcome: VOID (stopped at the E0 gate). E1, E2, E3 were not run. No outcome letter (O-T / O-T-off-only / O-G / O-N) was assigned.**

Reason, taken literally from §5 ("every case must be echoed") and §2 ("a case whose `engineEnvEchoed` is not `true` is void"): in E0, `engineEnvEchoed` is `false` for all 7 cases (control + F1..F6) and `engineEnv.everyCaseEchoed` is `false`. The string `[engine-env]` occurs 0 times in `E0-r1-report.json`.

E0 states do match the banked states (F1..F5 as banked 2026-09-07, F6 clean), but those states are void as arm evidence because no case carries the engine's echo.

| E0-r1 case | banked state | E0 state | open ms (`opened.atMs`; timeout: `elapsedMs`) | `engineEnvEchoed` |
|---|---|---|---|---|
| C  d1-anchors.odt (ODT control) | opens | clean | 1541 | false |
| F1 rows35 | opens, worker crashed | crashed (`workerCrashed: true`) | 1173 | false |
| F2 rows36 | TIMEOUT | timeout (`SdkTimeoutError`, `opened` null) | 180879 | false |
| F3 index30-index236 | opens clean | clean | 1056 | false |
| F4 index35-index236 | TIMEOUT | timeout (`SdkTimeoutError`, `opened` null) | 180927 | false |
| F5 index36-index235 | opens, worker crashed | crashed (`workerCrashed: true`) | 1054 | false |
| F6 rows20 | opens | clean | 1684 | false |

Arms not run: E1 (`SC_NO_THREADED_CALCULATION=1`, 3 runs), E2 (`SC_FORCE_CALCULATION=core`, 1 run), E3 (`SC_FORCE_CALCULATION=threads`, 3 runs). Optional native arm (§6): not run (no §5 outcome).

Preconditions at E0 start (2026-10-13T09:37:57Z): kdewallet `Locked` = `b false`; load average 0.38 0.47 0.38; no Chrome other than the run's own (`chrome-others-at-start: []`); wait polls 0. Run finished 09:44:13Z, exit 0, `timedOut: false`, 7 of 7 cases seen, `openTimeoutMs` 180000.

Patched `probe.js` sha256 (E0): `a45491710a580bf6d2dac8933896656ed90a20f0e71e77a29c34f9d3809c19b5` (unpatched `96f18d0c1f6b9b11c7d212bc0e176759ce5d4422e272f59e435c93e0e031364b`).

Default conclusion per §5 stands: 089's cause is still unattributed; H-T is a source reading only and may not be quoted as a cause.

## Details

Files in this directory:

- `E0-r1-report.json` - the full report written by the tool (`--out`).
- `E0-r1-runlog.txt` - wrapper log: arm, engine-env, wallet state, load at start, Chrome check, start/finish times, and the tool's stdout (first 4000 characters of the report).

Command (cwd `wasm_sdk_probe`; fixtures are in `findings/evidence/089/`):

```
python3 tools/probe_ods_on_profile.py --profile e2-editor-v12 --engine-env OXSDK_089_ARM=control --control <abs>/wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt --fixture <abs>/tdf149752-rows35.ods --fixture <abs>/tdf149752-rows36.ods --fixture <abs>/tdf149752-index30-index236.ods --fixture <abs>/tdf149752-index35-index236.ods --fixture <abs>/tdf149752-index36-index235.ods --fixture <abs>/tdf149752-rows20.ods --open-timeout-ms 180000 --timeout 1380 --out E0-r1-report.json
```

`verdict.spreadsheetsOpened` is in `E0-r1-report.json` under `verdict` (field values, verbatim from the report):

| name | opened | parts | viewReady | workerCrashed | engineEnvEchoed | error |
|---|---|---|---|---|---|---|
| tdf149752-rows35.ods | true | 2 | true | true | false | null |
| tdf149752-rows36.ods | false | null | false | false | false | SdkTimeoutError / TIMEOUT / "open timed out after 180000 ms" |
| tdf149752-index30-index236.ods | true | 2 | true | false | false | null |
| tdf149752-index35-index236.ods | false | null | false | false | false | SdkTimeoutError / TIMEOUT / "open timed out after 180000 ms" |
| tdf149752-index36-index235.ods | true | 2 | true | true | false | null |
| tdf149752-rows20.ods | true | 2 | true | false | false | null |

`verdict.controlOdtOpened`: true. `engineEnv` block in the report: `pairs {"OXSDK_089_ARM": "control"}`, `anchor ENV.MAX_CONCURRENCY="4"`, `everyCaseEchoed false`.

Worker-crash cases (F1, F5) carry the warning `worker sent an error! .../profiles/e2-editor-v12/probe.js:7: Uncaught RuntimeError: memory access out of bounds` (count 1 each). The two timeout cases carry `sal.osl.mutex ... pthread_mutex_unlock failed: EPERM` (count 1 each). No case has a warning starting with `[engine-env] `.

Nothing under `dist/`, `web/`, `sdk/`, any profile, the tool, or finding 089 was edited. No other check or judge was run. Next step belongs to the main session: decide how to get an echoed E0 (the tool/echo path is the open question) before any of E1..E3 is run.

---

## SUMMARY (resumed protocol after Amendment 1; supersedes the E0-r1 outcome above, which is left unedited)

Resumed per Amendment 1 (commit 88472109: the probe page registers its listener before engine init). Same task file, same profile `e2-editor-v12`, same fixtures and order (C, F1..F6), same wrapper. E0-r1 above stands as the red case for the echo check.

**Outcome: O-N (H-T refuted).** Applied literally from §5: E0-r2 gate passed (F1..F5 at their banked states, F6 clean, 7 of 7 cases echoed). E1 (`SC_NO_THREADED_CALCULATION=1`, 3 runs) left F2 and F4 timing out in 3/3. E2 (`SC_FORCE_CALCULATION=core`, 1 run) left F2 and F4 timing out. So neither E1 nor E2 opens F2 or F4. O-T, O-T-off-only and O-G do not apply. E3 (`SC_FORCE_CALCULATION=threads`, 60000 ms cap, 3 runs) was also run, as the coordinator instructed: F2 and F4 timed out in 3/3, F3 and F6 clean in 3/3. The §6 native arm was not run (only for O-T / O-T-off-only).

State per run (`clean` / `crashed` = `opened` non-null with `workerCrashed: true` / `timeout` = `opened` null; number = `opened.atMs`, for timeout `elapsedMs`, in ms):

| fixture | E0-r2 | E1-r1 | E1-r2 | E1-r3 | E2-r1 | E3-r1 | E3-r2 | E3-r3 |
|---|---|---|---|---|---|---|---|---|
| C d1-anchors.odt | clean 1633 | clean 1587 | clean 1604 | clean 1505 | clean 1517 | clean 1551 | clean 1580 | clean 1575 |
| F1 rows35 | crashed 1362 | clean 1180 | clean 1258 | clean 1217 | clean 1285 | clean 1234 | clean 1237 | clean 1286 |
| F2 rows36 | timeout 180920 | timeout 180839 | timeout 180839 | timeout 180830 | timeout 180845 | timeout 60870 | timeout 60890 | timeout 60894 |
| F3 index30-index236 | clean 1121 | clean 1069 | clean 1057 | clean 1043 | clean 1103 | clean 1297 | clean 1073 | clean 1058 |
| F4 index35-index236 | timeout 180851 | timeout 180860 | timeout 180913 | timeout 180862 | timeout 180859 | timeout 61056 | timeout 60853 | timeout 60829 |
| F5 index36-index235 | crashed 1045 | clean 1025 | clean 1066 | clean 1065 | clean 1059 | clean 1058 | clean 1115 | clean 1029 |
| F6 rows20 | clean 1016 | clean 1040 | clean 987 | clean 1007 | clean 1064 | clean 1057 | clean 1086 | clean 1033 |

Recorded alongside the outcome, not part of it (§5): F1 and F5 crashed in E0-r2 and did not crash in any of the seven E1 / E2 / E3 runs. The timeout cases F2 and F4 did not change state in any arm. Per §5 wording this is "the timeout and the crash separate"; it is not explained here.

Echo status: `engineEnvEchoed` is `true` for all 7 cases in all 8 reports; `engineEnv.everyCaseEchoed` is `true` in all 8. Each report holds 7 `[engine-env] {...}` warnings, e.g. E3: `{"MAX_CONCURRENCY":"4","SC_FORCE_CALCULATION":"threads"}`; E0-r2: `{"MAX_CONCURRENCY":"4","OXSDK_089_ARM":"control"}`. All 8 reports: ODT control opened, `timedOut: false`, 7 of 7 cases seen, `openTimeoutMs` 180000 (E0, E1, E2) or 60000 (E3).

Load at start of each run (1-min / 5-min / 15-min), kdewallet `Locked` = `b false` and `chrome-others-at-start: []` for every run:

| run | start (UTC 2026-10-13) | loadavg at start | wait polls before start |
|---|---|---|---|
| E0-r2 | 09:47:48 | 0.86 0.81 0.58 | 0 |
| E1-r1 | 09:54:21 | 0.41 0.46 0.50 | 0 |
| E1-r2 | 10:00:36 | 0.12 0.25 0.39 | 0 |
| E1-r3 | 10:06:50 | 0.46 0.22 0.31 | 0 |
| E2-r1 | 10:13:04 | 0.29 0.21 0.27 | 0 |
| E3-r1 | 10:19:18 | 0.82 0.71 0.47 | 0 |
| E3-r2 | 10:29:05 | 0.93 1.10 0.84 | 15 (30 s each) |
| E3-r3 | 10:31:18 | 0.51 0.85 0.78 | 0 |

Patched `probe.js` sha256 per arm (unpatched in every report: `96f18d0c1f6b9b11c7d212bc0e176759ce5d4422e272f59e435c93e0e031364b`):

- E0 (`OXSDK_089_ARM=control`): `a45491710a580bf6d2dac8933896656ed90a20f0e71e77a29c34f9d3809c19b5`
- E1 (`SC_NO_THREADED_CALCULATION=1`): `1b5bbb22a159baa8e94c73add3701e1d0aaa4af0b5c5c65bd700e6c8e7f2d33c`
- E2 (`SC_FORCE_CALCULATION=core`): `c985f021845cc7ef73a497d0886df0aef85a6dba003319bf130f49073b5af1a2`
- E3 (`SC_FORCE_CALCULATION=threads`): `a777df33ead324daccfcdc3645d97ef167ebf6d4bef703856934317a548bfc69`

## Details of the resumed protocol

Files added: `E0-r2-report.json`, `E1-r{1,2,3}-report.json`, `E2-r1-report.json`, `E3-r{1,2,3}-report.json`, each with an `-runlog.txt` (wrapper log: arm, engine-env, wallet state, load at start, Chrome check, wait polls, start/finish times, the tool's stdout head). `verdict.spreadsheetsOpened` (verbatim arrays) is in each report under `verdict`; the table above is read from `page.cases[].opened` and `workerCrashed`, which are the same fields.

Command shape (cwd `wasm_sdk_probe`, absolute fixture paths in the order C, F1..F6; `--timeout` = 7 x cap + 120 s): `python3 tools/probe_ods_on_profile.py --profile e2-editor-v12 --engine-env <NAME=VALUE> --control <abs>/dist/e2-fixtures/d1-anchors.odt --fixture <abs F1..F6> --open-timeout-ms <180000|60000> --timeout <1380|540> --out E<arm>-r<n>-report.json`.

Warning counts observed in the reports (grep over the report text): `memory access out of bounds` appears 2 times in E0-r2 (F1, F5) and 0 times in every E1 / E2 / E3 report; `pthread_mutex_unlock failed: EPERM` appears 2 times in E0-r2 (F2, F4) and 0 times in every E1 / E2 / E3 report.

Deviations: none in the run set. The wrapper ran the E1..E3 runs back to back and, per run, waited for 1-min load < 1.0 and no foreign Chrome before starting (E3-r2 waited 15 polls). The chain was not stopped after the O-N outcome became apparent from E1 and E2, because the coordinator's instruction listed E3 x3 as part of the resumed run set. No run was aborted. Nothing under `dist/`, `web/`, `sdk/`, any profile, the tool, or finding 089 was edited. No other check or judge was run.
