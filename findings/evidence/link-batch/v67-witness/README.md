# v67 candidate witness (task 2026-10-14c): 129-B on both browsers; restore-window skipped

Facts only. Anything not checked is marked "unverified". Times are UTC unless stated. Task: `handoff/tasks/TASK-2026-10-14c-pre-v67-witness.md`. Executor: Sonnet 5.5. No shell generation was frozen, no `--write` mode was run, nothing under `web/`, `editor-shell*/`, `sdk/`, `src/`, the `Makefile` or the host repo was edited or touched.

## Verdict per step

| Step | Verdict |
|---|---|
| W0 candidate bytes copied to `dist/`, five pairs equal, bundle intact, profile `e2-editor-v19` | PASS |
| W1 129-B Chrome | PASS (all clauses, 54/54 cells, 0 differ from all three reference rounds) |
| W1 129-B Firefox | PASS (same) |
| W2 restore-window | SKIPPED: the probe needs the ddev host (decided from its source, below) |

## W0 -- the candidate

Started 2026-10-14T02:19:40Z.

`make -n e2-c-assets` (run from `wasm_sdk_probe/` first) printed exactly five lines, all `cp`:

```
cp web/e2-editor.html dist/e2-editor.html
cp web/e2-editor-app.js dist/e2-editor-app.js
cp editor-shell-v2/narrow-editor-v2-client.js dist/editor-shell-v2/narrow-editor-v2-client.js
cp editor-shell-v2/narrow-editor-v2-session.js dist/editor-shell-v2/narrow-editor-v2-session.js
cp sdk/document-sdk.js dist/sdk/document-sdk.js
```

Then `make e2-c-assets` printed the same five lines. No other make target was run.

sha256 after the copy (each source/dist pair equal, checked by comparing the two hashes in a script):

| File | sha256 (source = dist) | dist before the copy |
|---|---|---|
| `e2-editor.html` | `b1185aaa4f77b892a82edb8d892aadff6f7f025369bb700f316b884661ad9512` | `f7e47799…` |
| `e2-editor-app.js` | `7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799` | `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678` |
| `editor-shell-v2/narrow-editor-v2-client.js` | `af4919b2d3108fd095dce5649fb223a7aa8d07d3652a5849c48f7837299cae2e` | `b0a9d74c…` |
| `editor-shell-v2/narrow-editor-v2-session.js` | `77841656c08a221026c457642d86b305075ee65918c897c95582cfc98c4f9e14` | `62a2a20e…` |
| `sdk/document-sdk.js` | `6898b7958d8ef08571be4215eaaab4d8911cb90ce89a81a6e6c9fdce8c9a3347` | `e4c3fe92…` |

`dist/` is git-ignored (`.gitignore:34`), so the copy leaves no change in `git status`.

`python3 tools/check_e1_c_bundle_intact.py` (from `wasm_sdk_probe/`), exit 0, printed `"bundleSha256": "187706b2dcb07d2b"`, `"includedFiles": 5`, `"availableModules": 6`, `"intact": true`, `"divergedAsDeclared": []`, `"unbinds": null`, `"problems": []`.

Profile, read from the page source (`dist/e2-editor-app.js`, `engineFactory()`, line 3020): `workerUrl: "./profiles/e2-editor-v19/sdk-worker.js"`. `dist/e2-editor.html` itself names no profile; it loads `./e2-editor-app.js` as a module (line 346). So the page loads `e2-editor-v19`, as expected. `dist/profiles/` holds `e2-editor-v8`, `e2-editor-v14`, `e2-editor-v19` among others (not otherwise examined).

## W1 -- 129-B

Pin commit (its own, before the run): `5f7f26fe` -- `FINAL_PAGE_SHA256` in `wasm_sdk_probe/tools/probe_129_m4_wasm.py` from `b24d754a…` to `7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799`, the old value kept in a comment above (`git diff`: 3 insertions, 1 deletion).

Command, the 10-13d chain's G3 form (docs directory and arguments the precedent's: round label 4, 1 round), from `wasm_sdk_probe/`:

```
tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1
```

Run detached through a wrapper in the session scratchpad (not kept in the tree). Driver exit 0; its own output is `round: …/round-20261014T022210Z`. The round directory name is the driver's (it stamps `round-<UTC start>`); the task's example name `round-v67-candidate-<browser>` was not used because the driver runs both browsers into one directory and names it itself. Round directory: `findings/evidence/129/final/round-20261014T022210Z/`.

Desk at the start (`machine-at-start.txt`, 02:22:10Z): load 0.34 1.14 1.20; `pgrep -c chrome` was 31 at the task's launch and 1 at my first look (the one process was MarkText's `chrome_crashpad_handler`, the owner's); `pgrep -c firefox` 0; `pgrep -af "probe_|check_m3|run_e2_c"` matched nothing of ours; `busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked` printed `b false` just before the launch (the wallet was not re-checked between the two halves; unverified whether it stayed unlocked, but neither half has a `fatal`). I waited until the 1-minute load average was below 0.5 before launching; a transient `python` process at 80% CPU seen once in `ps` was not ours and was gone at the next look. Chrome 02:22:10--02:34:40Z (Chrome/151.0.7922.169), Firefox 02:34:40--02:49:02Z (157.0.1), driver ended 02:49:12Z. Load at the end: 1.03 1.37 1.46 (`machine-at-end.txt`). No fatal in either report.

`preflight.final` in both `report-chrome.json` and `report-firefox.json`: `pageUnderTestSha256` `7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799`, `pageUnderTestIsFinal: true`; `redControlSha256` `8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401`, `redControlIs0212: true`; `patchedServedSha256` `05fd8b0adc3af8a4e30a1a5162152c33f04965b9e936018fbb9dccb2c2a7d1bb`. Neither report has a `fatal` field.

Analysis, run from `findings/evidence/129/final/` with `python3 ../../../../wasm_sdk_probe/tools/analyze_129_m4.py round-20261014T022210Z <reference>` (the same analyzer as the precedent; it also wrote `analysis.json` and `summary.md` in the round directory, the last invocation's form being the task's): three invocations, all exit 0 -- against `round-20261012T092119Z` (the precedent's reference; `analysis-stdout.txt`, run last), against `round-20261012T235136Z` (the 134 page's round; `analysis-vs-235136Z-stdout.txt`) and against `round-20261013T063013Z` (the 136 page's round, both browsers; `analysis-vs-063013Z-stdout.txt`). The last two are extra invocations, not named in the task.

| Clause (129-B, as in `../../129/final/README.md` and the 10-13d G3) | Chrome | Firefox | Verdict |
|---|---|---|---|
| 42 brief cells land where native `ref` lands | old 12 = native exact 12/12; S1--S5 30/30 by rule, 28/30 exact (`s1/Down`, `s1/End`, the same two cells as in every earlier round); drag cells follow native `ref` (`dragDownFollowsRef: ["s1d","m1d"]`) | same | PASS |
| toolbar shape after the key is `collapsed` | 54 of 54 m4 arms counted; analyzer: `not fresh: []; selection-mismatch: []; other not counted: []` | same | PASS |
| 0 toasts | analyzer: `toasts in m4 arms (whole arm after the open): 0 arms []; pill 'stopped' in: []` | same | PASS |
| key -> move done < 400 ms (analyzer limit 200 ms for keys that move the caret) | max 284.9 ms (47 moving keys 81.4--84.8; the 7 arms whose key does not move the caret 283.2--284.9) | max 289.7 ms (47 moving keys 83.9--91.4; the 7 non-moving 284.3--289.7) | PASS |
| Shift+arrow does not move, no toast | `shift` arms: collapsed `caretMoved: false`, revision `[0, 0]`, `toasts: []`; range arm `sameCaret` and `sameSelection` true | same | PASS |
| red control refuses | 3 of 3 `red-*` arms `refused: true`, toast `EDITOR_FORMAT_GESTURE_UNSUPPORTED` | 3 of 3 | red, as required |
| L-129 cells (recorded, not judged) | `s1d`/`m1d` Down follow native `ref`; `reach-*` caret and selection values as in the previous round | same | recorded |

Cross-checks the analyzer printed (`differ: []` and `wrapOffsetsSame: True` in each): Chrome vs Firefox landing index equal in 54/54 cells; each browser against `round-20261012T092119Z`, `round-20261012T235136Z` and `round-20261013T063013Z`: `compared: 54, differ: [], wrapOffsetsSame: True`. So 0 cells differ from all three reference rounds, in both browsers.

`diff` of `analysis-stdout.txt` here against `round-20261013T063013Z/analysis-stdout.txt` (the previous page's round): only the start/end times and load lines, the timing numbers (e.g. Firefox moving-key max 91.4 ms here against 87.7 ms there; Chrome moving 81.4--84.8 against 81.5--85.1) and the swap line differ. The landing tables, the bottom lines, the shift arms, the red control and the `reach` arms are line-for-line equal. The swap line: this round every arm had no swap activity (`pswpinMax` 0, `armsWithNoSwapActivity` 54 in both browsers); the previous round recorded `pswpinMax` 4 (Chrome) and 3060 (Firefox). The 10-13d chain noted that Firefox's 3060 and did not look into it; here it is absent. Cause of the difference unverified.

Inputs hashed by the driver (`inputs.sha256`): `probe_129_m4_wasm.py` `ab773929…`, `run_probe_129_final.sh` `83c48ec7…`, `dist/e2-editor-app.js` `7815e16c…`, the archived 0.2.12 page `133eaba4…`; as-run copy of the probe in the round directory.

## W2 -- restore-window: skipped, it needs the ddev host

Decided from the source of `findings/evidence/134/restore-window/probe_restore_window.py` (not run):

- `main()` builds `server = probe.Server(probe.Instance(probe.DEFAULT_DDEV), [])`; `probe.Instance` and `DEFAULT_DDEV` come from `wasm_sdk_probe/tools/check_m3_skeleton_open.py`, where `DEFAULT_DDEV = Path.home() / "Projects" / "Nextcloud_Apps" / "litecore"` (line 49) and `Instance.__init__` runs `ddev describe -j` and reads `.ddev/config.local.yaml` (lines 141--147).
- `run_round()` calls `server.clear_locks()`, `server.upload(server.admin, probe.NAME, doc)`, `probe.login(session, base, "admin", server.instance.password)` and `probe.open_from_files(…)`, i.e. it logs in to the Nextcloud instance, uploads a document by WebDAV and opens it from the Files app; it reads the document back with `probe.server_read`. `ui.static_facts(probe.DEFAULT_DDEV)` also takes the host path as its argument (what it reads there: unverified).
- It does not serve `dist/` on its own. The task's rule is to skip the step if the probe needs the host; no output directory `findings/evidence/link-batch/v67-witness/restore-window/` was created.

Consequence (stated, not measured): the restore-window path on the new page bytes has no witness from this task. It was last read on the 136 page (`findings/evidence/136/guard-r2/`, G5: 3/3 rounds per browser met the criterion, `scrollTop` never 0). Whether the new bytes change that path is unverified.

## Anything odd

- `pgrep -c chrome` was 31 at the task launch (as the task said) and 1 at my first command; I did not look into the 30 that went away. I started and stopped no browser other than the probe's own.
- The driver exits 0 whatever the halves do; the verdict above is from the reports' `fatal` fields (absent) and the analyzer.
- The wallet was checked once before the driver (`b false`), not between Chrome and Firefox halves.
- `analysis.json` and `summary.md` in the round directory are from the last analyzer invocation (the task's form, against `round-20261012T092119Z`).
- Unverified: whether the page diff of v20 part 1/2 and ruling 6 conditions 45, 47, 48 touches only the paths the task lists; I did not read the diff. The criteria are the ones the task and the precedents state.
- Not run: `make` for any other target, `package_m3_engine.py`, `ddev`, anything under `~/Projects/Nextcloud_Apps`, any `--write` mode, `git push`.
