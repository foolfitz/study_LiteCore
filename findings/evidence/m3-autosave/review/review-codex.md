# Review of check_m3_autosave.py — seat 2 (codex), 2026-10-12

Brief: `brief-runner.md` (commit `e309b70e`). Runner under review: `f6e1706a` (sha256 `a60eff46dff5c274…`). Run as `codex exec -s read-only -C <repo> "Read findings/evidence/m3-autosave/review/brief-runner.md and do exactly what it asks. ..." < /dev/null` (codex-cli 0.162.0). Its final answer, verbatim:

---

BLOCKING

References: R = wasm_sdk_probe/tools/check_m3_autosave.py; P = wasm_sdk_probe/web/e2-editor-app.js; S = specs/SPEC-M3-autosave.md; H = ~/Projects/Nextcloud_Apps/litecore/js/litecore-editor.js. Other helper filenames below are under wasm_sdk_probe/tools/.

1. A/B — AS-2c adds an outcome requirement absent from the criterion. R:603 requires “saved”; S:263–266 requires the timing, no auto during keying, and no new auto during the final quiet interval. An honest transient original PUT failure followed by a successful copy can meet all three clauses: a copy reaches a file and resets the cap (P:1984; H:594–609). The runner nevertheless returns FAIL. This is an extra gate, not a failed stimulus premise.

2. B — AS-5 can PASS without typing during the engine segment. After R:335 observes busy, an honest scheduling pause can delay R:343–346 until the first auto has already settled. All letters then arrive normally; the next auto carries them; R:735–751 accepts both outcomes and the complete text. It never compares typing times with the first auto’s engine interval. Example: busy sampled at 30.0 s, first host record starts at 30.7 s, runner resumes typing at 31.0 s. Both AS-5 arms can PASS despite missing the required overlap (S:274).

3. B — The claimed single clock is actually two clocks. R:112 timestamps keys with performance.timeOrigin + performance.now(), whereas H:451 uses Date.now(); R:469–471 merely reconstructs that wall-clock timestamp. An honest wall-clock correction of −0.5 s during an otherwise correct 30.2 s idle run produces a measured 29.7 s and FAIL at R:549. No report or constant editing is needed. The same mismatch affects the other cross-clock comparisons.

4. C — After normal pinning, “served” can mean manifest metadata rather than served bytes. R:1305 uses check_m3_page_honesty.py:1285–1294, which reads the packaged manifest’s hashes. On the dev instance, check_m3_skeleton_open.py:119–124 uses git status, while the host’s .gitignore:4 excludes engine/. An accidentally stale encoded module under an otherwise correct manifest can escape the binding check if it remains loadable. EditorController.php:272–300 streams the encoded file and takes its headers from the manifest; it does not verify its contents. This concerns the runner’s reliance on the frozen helper as evidence of actual served identity.

5. C — Binding is sampled only before the entire run (R:1305–1311), although fresh browsers load the application throughout R:1329–1335. An honest package/version replacement during the long run can therefore supply another page, session, or host to later cells while the report retains the original passing binding. The per-run opening check only requires “ready” (check_m3_page_honesty.py:763–767). An upgrade retaining the tested behavior can still yield AUTOSAVE HOLDS for mixed identities.

NON-BLOCKING

A — Criterion-by-criterion assessment, apart from the blocking items:
- AS-1: all eight condition comparisons are correct (R:474–482). However, R:489 reads only run.host. A crash after a phase snapshot but before R:433 leaves the opening host record there, undercounting observed autos. The fatal cell already prevents HOLDS (R:435,810).
- AS-2 key and toolbar: no defect found in the driven shapes, inclusive [30,35] comparison, saved outcome, or server-content checks (R:228–247,532–559). The revision fix correctly ignores repeated writes of the same value.
- AS-2h: no defect found in the inclusive timing comparisons or Firefox’s switch-back/read path (R:221–243,562–582).
- AS-2c: [3,6], the early-record comparison, and the final count/quiet checks match the criterion; the extra outcome gate is item 1 (R:585–612).
- AS-3 and AS-4(a): no further defect found in the lock/conflict setup, phase counts, copy target/content, notices, titles, or original-file comparisons (R:265–281,633–675).
- AS-4(b)/(c): no further defect found. The wire capture retains requests through both saves; the decoded filename suffix matches the copy this arm creates; If-Match uses the copy’s recorded ETag (R:301–317,679–727; check_m3_locks.py:434–447).
- AS-5, both arms: item 2 affects the required shape. No additional defect found in the committed reports’ extracted letter runs (R:320–355).
- AS-6(b): no defect found in using the leave recorder, checking that beforeunload fired without an asker, or comparing the copy with the auto’s bytes (R:358–369,755–766; check_m3_page_honesty.py:749–759).
- AS-7: no defect found in the stranded sequence, replacement hash, recovery, notice clearing, or server comparison (R:375–385,769–797).
- O2-1(a–e): no defect found. snap() selects the successful copy’s respondedAt for “copy” and the final attempt otherwise; HH:MM is calculated in the browser’s timezone (R:157–168,502–512,689–697,782–795).

B — wait_autos() waits for settled records, including copy/stranded outcomes (R:146–154; H:470–474). phase() subsequently observes at least 40 s after the recorded edit completion (R:197–202). No additional defect found in either mechanism or in copy_list()/copy_facts() naming (R:172–174; check_m3_locks.py:259–271; probe_autosave_m3.py:64–74).

C — The current None pins intentionally refuse counted execution; that is correctly assessed (R:80–83,1302–1304). Items 4–5 concern operation after legitimate pinning.

Writer judgement 1: CONFIRM PASS when lossRuns == 0, provided the required stimulus occurred. S:274 makes the toast obligation conditional on loss; R:855–857 truthfully reports whether that path was exercised.

Writer judgement 2: CONFIRM NE for hiding later than 5 s: the specified stimulus was not established, so that observation cannot judge the within-2-s behavior (S:262; R:569–571).

Writer judgement 3: CONFIRM reading lastSaved. Its precise timestamp and target distinguish a real update when two saves share the displayed minute (R:693–697; H:185–192).

Writer judgement 4: CONFIRM the FAIL policy for failed editing premises, but REJECT the assertion that every premise is fully checked: item 2 permits an unexercised AS-5 overlap to PASS.

D — Every named criterion has a case, but individual gated clauses lack dedicated red cases: AS-1’s seven non-composing conditions; AS-2’s key persistence; AS-2h’s saved outcome; AS-3’s original/content/target comparisons; AS-4(a)’s unchanged #s-doc and AS-4(b)/(c)’s second-edit persistence; AS-5’s timing premise; and AS-7’s initial notice and recovered server hash (R:928–1014).

D — These omissions alone do not establish honest-run misclassification: many corresponding comparisons are present. AS-5’s missing timing case matters because item 2 supplies an honest false PASS. The selftest’s coverage assertion checks arms, not clauses (R:1224–1226).

Validation: selftest passed; the complete committed shakedown re-scored clean with 29 auto records; all 76 red-case applications produced their expected results. No files were written; no browsers, builds, ddev, or network were used. The already registered limits were not mis-assessed.
