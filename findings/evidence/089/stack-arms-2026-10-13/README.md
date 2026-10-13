## SUMMARY

Protocol: `handoff/tasks/TASK-2026-10-13f-089-threading-arms.md` Amendment 3 (commit 4fc2673b, 2026-10-13T11:03:25Z) implementing `findings/evidence/089/ruling/ruling-1.md` (conditions 1-14). Instrument: `probe_ods_on_profile.py --pthread-stack-size N --engine-env OXSDK_089_ARM=<arm>` (90fed9b7), profile `e2-editor-v12`, open cap 60000 ms, fixtures C, F1..F6. Anchor red case (condition 14): `redcase-anchor-count.txt`, already in this directory.

**Outcome: O-S.** (a) holds: at 262144 (S1), 1048576 (S2) and 8388608 (S3), F2 and F4 opened in 3 of 3 runs each, and F1 and F5 did not crash in any of those 9 runs (all 7 cases `clean` in all 9 runs). (b) holds: S4 (32768) passed its boot gate (control ODT `clean`, 7 of 7 cases echo 32768), and all six spreadsheets failed (opened null; F1, F2, F4, F5, F6 `WORKER_CRASHED` at 0.8-1.1 s, F3 `TIMEOUT` at 60825 ms). (c) holds: ladder L at 262144 opened rows37, rows38, rows39, rows40, rows50 and the original `tdf149752.ods` (all clean, 1.0-1.6 s): "all open", no cliff in that range. S0 gate passed. S4' (49152) was not run (S4 was not void under condition 6).

Reading note for condition 4 (flagged, not decided here): in S4 every case has 3 thread starts, and S0 has 7 for F1, F3, F5, F6. I did not void S4 on that, because the ruling's wording is "+-0 for cases that reach the same state" and those four reached a different state (failed instead of opened). Amendment 3 omits that qualifier. If the main session reads the amendment's sentence as voiding S4, the letter would be O-S-up-only.

Thread starts (sum of `engineStackSizes` counts): S0: C 3, F1 7, F2 3, F4 3, F3/F5/F6 7. S1, S2, S3 (all 9 runs): C 3, every spreadsheet 7 (equal to S0 for every case that kept its S0 state; F2 and F4 went 3 to 7 when they opened). S4: 3 for every case. For the hung cases in S0 the count is 3, not 7. Not read as pool exhaustion.

State table (number = `opened.atMs`; for non-opened cases `elapsedMs`; `crashed` = opened with `workerCrashed`; `timeout` = opened null, `SdkTimeoutError`):

| fixture | S0-r1 | S1-r1 | S1-r2 | S1-r3 | S2-r1 | S2-r2 | S2-r3 | S3-r1 | S3-r2 | S3-r3 | S4-r1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C ODT control | clean 1526 | clean 1607 | clean 1733 | clean 1585 | clean 1691 | clean 1608 | clean 1639 | clean 1588 | clean 1594 | clean 1552 | clean 1438 |
| F1 rows35 | crashed 1241 | clean 1351 | clean 1306 | clean 1351 | clean 1226 | clean 1243 | clean 1325 | clean 1233 | clean 1228 | clean 1209 | failed:WORKER_CRASHED 932 |
| F2 rows36 | timeout 60858 | clean 1087 | clean 1189 | clean 1102 | clean 1051 | clean 1099 | clean 1101 | clean 1041 | clean 1037 | clean 1060 | failed:WORKER_CRASHED 844 |
| F3 index30-index236 | clean 1061 | clean 1095 | clean 1055 | clean 1036 | clean 1073 | clean 1027 | clean 1180 | clean 1071 | clean 1108 | clean 1033 | failed:TIMEOUT 60825 |
| F4 index35-index236 | timeout 60908 | clean 1083 | clean 1195 | clean 1123 | clean 1074 | clean 1029 | clean 1148 | clean 1053 | clean 1061 | clean 1051 | failed:WORKER_CRASHED 1057 |
| F5 index36-index235 | crashed 1040 | clean 1146 | clean 1207 | clean 1267 | clean 1058 | clean 1096 | clean 1188 | clean 1055 | clean 1100 | clean 1108 | failed:WORKER_CRASHED 1018 |
| F6 rows20 | clean 1647 | clean 1551 | clean 1592 | clean 1610 | clean 1578 | clean 1556 | clean 1663 | clean 1590 | clean 1602 | clean 1553 | failed:WORKER_CRASHED 838 |

Echo: every case in all 14 reports has `engineStackEchoed` true (every echoed value equals the requested size) and `engineEnvEchoed` true; `engineStack.everyCaseEchoed` and `engineEnv.everyCaseEchoed` true in all 14. Per-run load at start, wallet and Chrome check are in the table in the Details section (every start: load < 1.0, wallet `b false`, no foreign Chrome).

## Details

Files: `S<arm>-r<n>-report.json` and `-runlog.txt` for S0 (r1), S1/S2/S3 (r1-r3), S4 (r1), SL (r1, the ladder L). States are read from `page.cases[].opened`, `workerCrashed` and `engineStackSizes` (via a reader that walks `page.cases`, not stdout). The tool reports carry no `startedAt` field; the wrapper's `started-utc` in each runlog is the start record. Condition 1: the first sized run (S1-r1) started 11:14:08Z, after Amendment 3's commit time 11:03:25Z; S0 (11:11:19Z) was also after it.

Thread starts per case (sum of counts in `engineStackSizes`, one `[engine-stack]` line per started pthread):

| fixture | S0-r1 | S1-r1 | S1-r2 | S1-r3 | S2-r1 | S2-r2 | S2-r3 | S3-r1 | S3-r2 | S3-r3 | S4-r1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C ODT control | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| F1 rows35 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 3 |
| F2 rows36 | 3 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 3 |
| F3 index30-index236 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 3 |
| F4 index35-index236 | 3 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 3 |
| F5 index36-index235 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 3 |
| F6 rows20 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 3 |

Within each of S1, S2, S3 the three runs have identical start counts for every case. S0's last stage line for the two hung cases (F2, F4) is `open.documentLoad` with `sbrk` 290066432 and `heapBytes` 1073741824; every opened case in S0-S3 reaches `open.query-metadata`. In S4 the six spreadsheets all end at `open.documentLoad` (`sbrk` 289935360).

S4 detail: `verdict.controlOdtOpened` true; F1, F2, F4, F5, F6 `opened` false with `workerCrashed` true and error `WORKER_CRASHED` ("Uncaught [object ErrorEvent]"); F3 `opened` false, `workerCrashed` false, `SdkTimeoutError` after 60 s.

Ladder L (one run, 262144, the smallest size that opened F2 and F4 in 3 of 3; original `wasm_sdk_probe/test-docs/ods/upstream/tdf149752.ods`, sha256 starts `2d6a2c6aa63c33b0`; rows37-rows40, rows50 from `findings/evidence/089/`):

| fixture | state | open ms | thread starts | echoed sizes |
|---|---|---|---|---|
| d1-anchors.odt | clean | 1600 | 3 | {'262144': 3} |
| tdf149752-rows37.ods | clean | 1222 | 7 | {'262144': 7} |
| tdf149752-rows38.ods | clean | 1054 | 7 | {'262144': 7} |
| tdf149752-rows39.ods | clean | 1055 | 7 | {'262144': 7} |
| tdf149752-rows40.ods | clean | 1029 | 7 | {'262144': 7} |
| tdf149752-rows50.ods | clean | 1103 | 7 | {'262144': 7} |
| tdf149752.ods | clean | 1558 | 7 | {'262144': 7} |

Recorded alongside the outcome (condition 8): the start counts above. Pool exhaustion is not measured by this instrument (it does not record `pthread_create` requests) and is not inferred.

Run log:

| run | size | cap ms | start (UTC 2026-10-13) | loadavg at start | wallet | other Chrome | wait polls | exit |
|---|---|---|---|---|---|---|---|---|
| S0-r1 | 65536 | 60000 | 11:11:19 | 0.64 1.16 0.98 | `b false` | none | 13 | 0 |
| S1-r1 | 262144 | 60000 | 11:14:08 | 0.40 0.82 0.88 | `b false` | none | 0 | 0 |
| S1-r2 | 262144 | 60000 | 11:14:24 | 0.75 0.87 0.89 | `b false` | none | 0 | 0 |
| S1-r3 | 262144 | 60000 | 11:17:10 | 0.78 0.93 0.91 | `b false` | none | 5 | 0 |
| S2-r1 | 1048576 | 60000 | 11:17:55 | 0.84 0.95 0.92 | `b false` | none | 1 | 0 |
| S2-r2 | 1048576 | 60000 | 11:18:41 | 0.91 0.95 0.92 | `b false` | none | 1 | 0 |
| S2-r3 | 1048576 | 60000 | 11:19:27 | 0.96 0.97 0.93 | `b false` | none | 1 | 0 |
| S3-r1 | 8388608 | 60000 | 11:22:43 | 0.86 1.03 0.98 | `b false` | none | 6 | 0 |
| S3-r2 | 8388608 | 60000 | 11:22:59 | 0.76 1.00 0.97 | `b false` | none | 0 | 0 |
| S3-r3 | 8388608 | 60000 | 11:23:15 | 0.75 0.98 0.97 | `b false` | none | 0 | 0 |
| S4-r1 | 32768 | 60000 | 11:24:05 | 0.69 0.94 0.95 | `b false` | none | 0 | 0 |
| SL-r1 | 262144 | 60000 | 11:25:57 | 0.86 1.01 0.98 | `b false` | none | 0 | 0 |

Patched `probe.js` sha256 per arm (unpatched in every report: `96f18d0c1f6b9b11c7d212bc0e176759ce5d4422e272f59e435c93e0e031364b`; the stack patch is applied on top of the env patch):

| arm | stack size | final served `probe.js` sha256 (env + stack patch) | env-patch-only sha256 |
|---|---|---|---|
| S0 | 65536 | `0c035f375e7c81d7e42ab75459c8e4b5e47d8fb7f2a8c4a817c120f9d1794170` | `1ccf36fe0f5782b5f534d306236257f5f36d34dbd6c60dc23bd8ec5508a368d9` |
| S1 | 262144 | `4150682aa84e2d5eb1fb94d13fdd399babf4f31fd22abb53c203e8948d29d98a` | `b3fcc217373dd575c91b157fddc6883fc7e10edbc2d4aeb09ca4c860b27900a3` |
| S2 | 1048576 | `18910b0a8733077ed52c596fbd462836f188212860e398e95772fb3c93957c08` | `78295cc1302f3f832d27a8d1f9ea7fea29140a1badf2c0174ce9ea73616d6957` |
| S3 | 8388608 | `f22d518bb5758a45686648c33f91998a02aa97fd0edec8605449c0d337ea6f20` | `f6f3cc333c3a2d400bf0192f0158f5257f58ad3780535eeb65ddbae5d197c9a0` |
| S4 | 32768 | `3965a3b88a306c97e4c3c9169ed4b43dc84c43007c4a6f2b0201ce36bed54dac` | `da05cfaaa063b19289f0a394f93dfb90c89386b6eb59ceec170f8338389ac5af` |
| SL | 262144 | `1e34064e3f9413af254deb7a73079398125edfa1fae2a2a6f5ed5c3926eb4793` | `03007f546f1a0f1bdf02d5bab7f3c6896a76ef69366cd22bc5748f02851fc16c` |

Deviations: none from the Amendment 3 run set. The first-run-opened rule was applied by the wrapper (r2 and r3 run only if F2 and F4 both had `opened` non-null in r1); it triggered at S1, S2 and S3. No run was aborted. Nothing under `dist/`, `web/`, `sdk/`, any profile, the tool, or finding 089 was edited. No other check or judge was run. The wrapper scripts are in the executor's scratchpad, not in the repository.
