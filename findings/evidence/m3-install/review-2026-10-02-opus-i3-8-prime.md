# Adversarial review of the I3-8′ proposal (opus, read-only), 2026-10-02

Target: `proposal-2026-10-02-i3-8-prime.md` (`bf9bcfb9`). Verbatim below. The main session verified finding 1 itself: `firefox --version` = 157.0, `snap list --all firefox` shows 156.0-1 (rev 8929) disabled and 157.0-1 (rev 8995) active, refreshed 2026-10-01 10:42 CST; Chrome 151.0.7922.169 unchanged; geckodriver 0.37.1. Dispositions: see the handoff of the same day and the spec revision row that follows it.

---

## SUMMARY

Target: `findings/evidence/m3-install/proposal-2026-10-02-i3-8-prime.md` (committed in `bf9bcfb9`, which touches only `findings/evidence/m3-install/*`, so the tree binding is unchanged: `HEAD:wasm_sdk_probe` is still `75e1e93f` and porcelain is empty). This review was read-only. The only things I ran were pure scoring functions in-process and a read-only `build_m3_release.collect`. I did not run any runner CLI, browser, install, equivalence or `run`.

1. **BLOCKING (verified, live today).** The browsers are not bound. Firefox snap auto-refreshed 156.0 → 157.0 on 2026-10-01 10:42 CST. The dev reports ran on 09-29 with Firefox 156.0 in every run, and any 0.2.5 window now would run 157. I3-8′ passes anyway.
2. **HEAVY (hole, no drift today).** .3 binds only the runner file. The runners' shared modules aren't bound between the dev runs and the equivalence check. Real instruments live there: the Z0-2 frame parser `package_m3_engine.zstd_frame`, the K2 `RECORDER` in `check_m3_page_honesty.py`, and the `host_binding` branch for the other instance. The dev reports carry no tree or module binding.
3. **HEAVY.** .3's selection has no instance filter, and `runs/` holds litecoreprobe reports too (verified: four of them from the 0.2.1 window). Also, "each report's sha equals the current sha" means an older-sha dev report on the same commit makes .3 permanently red unless evidence is deleted.
4. **HEAVY (Q2: yes).** A field that exists only now does change verdicts. Z0-1 and Z0-2 read exactly the four only-now `zst*` fields. Z4-1's `release` record (which has its own branch per instance) and `hostBinding` are neither compared nor listed. Anchoring to PRE also means the next deliberate change to a PRE field recreates today's failure. Fix: compare against the dev reports. I verified that comparison is exactly equal today.
5. **HEAVY.** The proposal attributes the rows wrongly in one place and leaves out three things:
   - The locks rows fail on **readonly (K9′) and nowhere (K10′)**. Both come from page-honesty §7.4 (`1dc85602`), not §7.11 / finding 108, and readonly isn't mentioned at all.
   - K2 fails in Firefox as well as Chrome.
   - `redExit` went 0→1 on the assets and locks rows, and that isn't mentioned.
   The conclusion "deliberate and re-counted" holds for all 5 rows. But the stated justification is narration, and it is already wrong once (§8 and §11).
6. **HEAVY.** The form claims under §9 don't hold. This is a relaxation of an existing criterion, written after its measurement was seen. That is §4 withdrawal plus relaxation, not a §9 addition. The cutoff contradicts itself ("0.2.5 and after" against "closes when 0.2.5 lands"). The 10-02 revision row's "判準條文不動" has to be corrected append-only.
7. **HEAVY.** Implementing it can't be green as-is:
   - `score()` hard-requires rows covering every runner (`check_m3_install_elsewhere.py:1154-1157`).
   - Four I3-8 red cases are pinned to rows and would FAIL, which breaks the "zero SKIP/GREEN" gate before counting.
   - .1 and .3 have no red cases.
   - .3 must be re-derived at scoring time from paths and sha256s, not stored as a boolean.
   - The equivalence check must be re-run after the tool commit, and I3-7 after that.
8. **LIGHT.** .1 doesn't say what "recursively" means for lists or type changes (`dirty`, `treeEntries` and `trackedDist` are lists).
9. **LIGHT.** .3 trusts `runnerSha256` as the report's own self-report. Each selected report's blob should be bound to its committed blob.
10. **LIGHT.** `criteria` in the assets report decides whether Z0–Z2 get scored at all (`check_m3_assets.py:732`). No I3 clause compares the window report's `criteria` with the dev report's.
11. **LIGHT (verified).** The "Re-check" commands in the 0.2.1 RESULT.md now come out red for I3-1/2/3 under current tools. Pin the re-check to the tool commit (`b30b58b7`). The same will happen to the 0.2.5 result.
12. **LIGHT.** libssl3 was upgraded 2026-10-02 09:24, after the dev reports. The tree binding's `sys.version` doesn't capture it.

**Recommended consolidated fix (A).** Replace .3 with I3-7 extended to all four runners. Each gets a fresh dev counted report that starts after the re-run equivalence check and ends before the window. Each is passed in explicitly and bound by sha. Each must reach its verdict, with red cases re-run at scoring and runner sha equal to the equivalence check's. Add one new check: per-run browser `version` sets equal to the matching litecoreprobe report's. This reuses existing machinery and puts the dev runs inside the span that .4 already binds. Cost is about one hour of dev runs (locks ~47 min). Keeping .3 on the historical reports (option B) fails today on Firefox 156≠157, so B collapses into A.

## DETAILS

### 1. BLOCKING — the browsers are not bound, and they have already drifted (verified)
- **Claim.** A verdict on litecoreprobe is only comparable with the dev verdicts if both used the same browser. I3-8′.4 binds python/node/make, the tree and the modules. .3 binds runner files. Nothing binds Chrome, Firefox or geckodriver.
- **Evidence.**
  - Every run records `version`: `runs[i].version` in assets, versions and locks; `browsers/<b>/<arm>[i].version` in host-entry.
  - All four dev reports (`2026-09-29T163517`, `182723`, `174033`, `183110Z`) show `{"156.0", "Chrome/151.0.7922.169"}`.
  - `snap list --all firefox` shows 156.0-1 (rev 8929) disabled and 157.0-1 (rev 8995) active. `snap info firefox`: `refresh-date: yesterday at 10:42 CST`. `firefox --version` gives `Mozilla Firefox 157.0`.
  - geckodriver also comes from the snap (`run_browser_probe.py:86` uses `shutil.which("geckodriver") or "/snap/bin/geckodriver"`).
  - Chrome is unchanged at 151.0.7922.169.
- **Failure scenario.** The 0.2.5 window runs today with Firefox 157. The I3-1 arms that depend on Firefox's HTTPS Accept-Encoding are judged on a browser the dev verdict never saw: Z1/P1 (Firefox sends zstd) and Z2-2 (`firefox-nozstd` relies on the pref `network.http.accept-encoding.secure`, `check_m3_assets.py` `NOZSTD_PREFS`). I3-8′.1–.4 are all green.
- **Fix.** Add a per-instance raw-field check: for each runner, the set of per-run `version` values in the litecoreprobe report equals the set in the dev report it is compared against. This alone would be red today, which forces fresh dev runs, i.e. option A. Optionally the user can hold snap refreshes for the window (that needs sudo, so the user runs it). Even so, the check above is what verifies it.

### 2. HEAVY — shared modules are unbound between the dev runs and the equivalence check
- **Claim.** In .3, "the tool that recorded the dev verdict is the tool that will judge litecoreprobe" only holds for the runner file. The tool also includes the runners' import closure, and `make test-e2-c-static` inputs.
- **Evidence.**
  - Imports: `check_m3_assets.py:58-70` imports `build_m3_release`, `check_m3_host_entry`, `check_m3_page_honesty` (READ_RECORD, RECORDER = the K2 A′ instrument, used at :572/:575), `check_m3_skeleton_open`, `package_m3_engine` (`zstd_frame`, `MAX_ZSTD_WINDOW`, `build_id`), `probe_m3_assets`, `probe_m3_gate0_coep`, `r7_support`, `run_browser_probe`, `run_e2_c_page_smoke`. `check_m3_host_entry.py:104` lazily imports `build_e2_c_shell_bundle`.
  - The dev reports carry only `runnerSha256` / `runner.sha256` plus `static.page`, `testStatic` and host binding. They have no tree, commit, porcelain or module shas (I dumped the top-level keys of all four).
  - I3-8′.4 binds from the equivalence check onward only.
- **Measured drift (Q3).**
  - `git diff --stat 0972b6b2 HEAD -- wasm_sdk_probe/` touches only `check_m3_install_elsewhere.py` (+27/−5). No runner imports it (`grep -l check_m3_install_elsewhere *.py` matches only itself).
  - `git diff 0972b6b2 3c75b00c -- wasm_sdk_probe/` is empty.
  - Last commits of the shared modules: `check_m3_page_honesty.py` at `0972b6b2` 16:35:03Z; `package_m3_engine.py` and `build_m3_release.py` at `2265debd` 16:34:15Z; everything else earlier. All of them precede the first dev report (16:35:17Z).
  - So there is **no committed drift affecting scoring or recording**. Whether the working tree was clean during 16:35–18:47Z is **not recorded anywhere** (inferred only).
- **Failure scenario.** Someone commits a change to `package_m3_engine.zstd_frame` before the equivalence check, for example making `trailingBytes` always 0. Runner shas are unchanged, so .3 passes. The dev reports re-score from their stored frames, still green. `zstFrame` counts as an "addition", so .1 passes. .4 starts after the change, so it passes too. Litecoreprobe's Z0-2 is then judged by a different parser.
- **Fix.** Option A (fresh dev runs inside the .4 span) closes this. Option B: the tool takes the last `wasm_sdk_probe` commit at or before each dev report's `startedAt`, requires `git diff --name-only <it> <equivalence HEAD> -- wasm_sdk_probe/` to exclude every file in the runners' transitive import closure (computed with `modulefinder` over `TOOLS`, so form 2) plus the Makefile, tests and `web/`, and names the dev-time working-tree state as a stated limit.

### 3. HEAVY — .3's selection rule (verified)
- **Evidence.** `runs/` contains litecoreprobe counted reports: `m3-assets/runs/2026-09-29T012410`, `m3-versions/…012641`, `m3-locks/…013546`, `m3-host-entry/…013030Z`, all with baseUrl litecoreprobe. The runners write `runs/` for any counted run regardless of instance (`check_m3_assets.py:1150`). On litecoreprobe, `hostRepo` is the release commit (`check_m3_skeleton_open.host_binding`), so a 0.2.5 window's reports match ".3: host commit starts with release.json's commit".
- **Failure scenarios.**
  - (a) After any 0.2.5 counted attempt, a tool fix and a re-run of the equivalence check: .3 selects litecoreprobe's own reports as the "dev" baseline, which is circular. If one of them was red, .3 goes red permanently.
  - (b) A dev re-run after a runner fix leaves an older-sha dev report on 7420418. "Each report's sha equals current" is then red unless evidence is deleted. That is a perverse incentive.
- **Fix.**
  - Filter on `baseUrl == DEV_URL` (top-level for versions and locks, `instance.baseUrl` for assets and host-entry) and on `startedAt < equivalence.at`.
  - Semantics: at least one report per runner recorded by the current runner sha, and all of those reach the verdict (no cherry-picking). Reports with other shas are listed in `equivalence.json`, not judged.
  - Record path and sha256 in `equivalence.json`, and have `score()` re-derive and compare.

### 4. HEAVY — "additions allowed" (Q2: yes, an added field can change a verdict)
- **Evidence.**
  - `score_zstd_package` (`check_m3_assets.py:207-232`): Z0-1 reads `zstSha256`, `zstBytes` and `zstDecodedSha256`; Z0-2 reads `zstFrame`. These are exactly the four only-now keys. I verified 22 paths, and the only added keys are those four. No PRE field changed or went missing.
  - The scorer can therefore move from relying on a PRE field to relying on an added one, while every PRE field stays equal.
  - Beyond that, `release_record` (`:746-757`, scored as Z4-1 at `:796`, with its own `installed_app(root) is None` branch at `:750`, added in `e25751b4`) and `hostBinding` (from `binding_fields`) are recorded by the runners but sit outside `NEW_RECORDING` (`check_m3_install_elsewhere.py:659-670`). They are neither compared nor "listed".
  - Anchoring to PRE (`9748b714`) means any future deliberate change to a PRE field (say `HOST_FILES` loses one) reproduces today's dead end.
- **Fix (verified satisfiable today).** .1′: the current dev recording path, extended with `release_record(DEFAULT_DDEV, binding)`, must **exactly** equal what each selected dev report recorded, with no exemption for additions. I checked in-process:
  - `equivalence.json` `recording.after.package` equals the assets dev report's `package`, `zst*` included, with zero differences.
  - `hostRepo`, `hostDirty` and `hostFiles` are equal for the assets, versions and locks reports.
  - `describeApp` equals the host-entry and assets `instance.app`.
  - A read-only recompute of `build_m3_release.collect(DEFAULT_DDEV,"HEAD")` engine members equals the assets report's `release.engineMembers` (45 entries).
  - Keep PRE vs now (with .2) only as a regression check if wanted.

### 5. HEAVY — row attribution (Q4), each row checked
All five differing rows trace to deliberate changes that were re-counted. The proposal's text is wrong or incomplete in places:
- **assets `2026-09-28T172628`**: page pin (`fbfb59a4`→`fc80050c`, page-honesty §7.6/§7.11, `a2df684f`) and K2 A′ (`1dc85602`, page-honesty §7.8 / asset-delivery revision row). In-process `score_run` shows `K2 instrument …: pre-leave save did not land` and `leave was guarded None / no fired record` for **both chrome and firefox**; the proposal says chrome only. `redExit` 0→1 because the runner's red cases count "unmutated run already red" as failure; not mentioned. Re-counted as `151106` (369e6ed) and `163517` (7420418).
- **versions `152217`**: red before (host 49cc4ab vs pin 5e53362) and red after (page pin, imported from `check_m3_locks.PAGE_SHA256` at `check_m3_versions.py:41`, plus pin 7420418). The verdict is unchanged; only the message differs.
- **versions `173014`**: green → red on the page pin and host pin (`b1b46ef7`/`a2df684f`/`0972b6b2`). Re-counted as `150721` and `182723`.
- **locks `131020` and `174346`**: page pin plus **readonly (K9′) and nowhere (K10′)**. In-process `score_arm` problems: `lock at open None/readonly`, `share None at open … wanted 3 -> 1`, `server lock at the cut None`. That is SPEC-M3-page-honesty **§7.4** (`1dc85602` "K9′／K10′"), **not §7.11 / finding 108**. Readonly is omitted from the proposal. `redExit` 0→1. Re-counted as `142032` and `174033`.
- **Fix.** Generate the per-row problem list and its cause with a tool (the scorer's per-arm problems plus a `git log -S` on the changed constant or scorer line) instead of narrating it.

### 6. HEAVY — the form claims (§9, §1)
- **§9.** It is "before satisfaction" formally, since no 0.2.5 window has run. But .1's exemption and .3's "today selects exactly one per runner" were fitted to the already-inspected `equivalence.json` (14:21:12Z). §9 legitimizes *adding* criteria, not relaxing one. This is §4 (withdraw the rows) plus a relaxation (.1), and the spec must say so. It can't claim "判準沒有一條被放寬" again, and the 10-02 row "判準條文不動" needs an append-only correction (§10).
- **"Forced and named"**: met.
- **Cutoff**: contradictory ("windows on 0.2.5 and after" vs "closes when the 0.2.5 counted window lands").
- **§1, dynamic test on .3.** Inserting a fake member breaks it two ways:
  - A litecoreprobe report added to `runs/` gets selected (wrong).
  - A shared helper changed after the dev reports turns zero checks red while "same tool" becomes false. On the tool side that is form 3.
- **§1, .1.** The field set is tool-generated from PRE (form 2), but the choice of recording paths (three callables) is a hand enumeration. `release_record` is the existing counter-example.

### 7. HEAVY — implementing it and red cases (Q6)
- `score()`, `check_m3_install_elsewhere.py:1154-1171`:
  - If strict or rows exist, rows must cover `set(RUNNERS)` and each row must have before == after.
  - Empty rows under strict produce "I3-8 equivalence covers []".
  - Retained PRE rows stay red.
- Red cases pinned to rows ("a report scoring differently", "a report whose red cases now pass", "equivalence missing a runner", "an equivalence row without its red-case exit", around `:1480-1574`) would FAIL as "mutation does not apply". That breaks the spec's pre-count `--strict --red-cases` with zero SKIP/GREEN.
- **Needed.**
  - Write the `score()` and `equivalence()` changes and new pinned red cases first. For .1: PRE field changed, PRE field missing, nested `package/files` field changed (plus a unit check that a change to an only-now field does not go red). For .3: a runner without a dev report, a dev report with another sha, a dev report that re-scores red, dev red cases that stay green, a dev report from litecoreprobe, and a dev report changed since the check.
  - Commit, then re-run the equivalence check (the module sha and tree change), then run I3-7 after it.
  - .3 must be re-derived at scoring time from raw fields (the tool docstring forbids stored conclusions).
- Nothing else is weakened: the window-runner-sha == equivalence check (`:1125`) and the I3-7 checks are independent of rows.

### 8–12. LIGHT
- **8.** Define .1's recursion: dicts recurse; lists, scalars and type changes are leaves compared for equality; a missing key is red.
- **9.** Bind each selected dev report by `git ls-files` plus `git diff --quiet HEAD -- <path>`, and record its sha256. I verified the four dev reports are unchanged since `3c75b00c`.
- **10.** `zstd_step` reads the report's own `criteria` (`check_m3_assets.py:732`). Add a check that the litecoreprobe report's `criteria` equal the dev report's. The bound runner sha makes this hold today.
- **11.** Re-scoring the 0.2.1 window's runner reports with current modules (in-process `runner_verdict`) gives assets NOT DELIVERED, versions NOT CORRECT, locks DO NOT LAND, host-entry LANDS, dev host-entry LANDS. RESULT.md's "Re-check" should say "with tools at `b30b58b7`".
- **12.** apt history shows a libssl3/openssl upgrade on 2026-10-02 09:24, after the dev reports. Python, node and make binary mtimes predate the dev reports. Either record `ssl.OPENSSL_VERSION` or name it as a limit.

### Checked, not a problem
- Committed tool drift since the dev reports: none that touches the runners (finding 2's evidence). `bf9bcfb9` is evidence only.
- The dev reports' runner shas equal the current ones: 3370dca9, c8855e8e, 399cb112 and 4c507d3a all match `equivalence.json` `runnerSha256`.
- PRE→now recording: additions only (22×4 `zst*` keys), with no changed or missing PRE field. The proposal is accurate here.
- Imports between the four runners (versions imports locks' `PAGE_SHA256`; assets, versions and locks import from host-entry) are covered, because .3 checks all four runner shas together.
- The host-entry runner hasn't changed since the 0.2.1 window (no commit after `b30b58b7`), consistent with its row staying SAME.
- Dropping the rows loses nothing that comparability needs. The versions `152217` row was a negative control, but the runners' own red cases (re-run in .3) cover rejecting bad reports. What the rows don't cover (instrument and environment) they never covered either. That gap is findings 1, 2 and 4.

### Files
- `/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/m3-install/proposal-2026-10-02-i3-8-prime.md`
- `/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_install_elsewhere.py` (:114, :659-726, :1125, :1154-1171, red cases ~:1480-1574)
- `/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_assets.py` (:60, :64, :169-177, :207-232, :732, :746-757)
- `/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_locks.py` (:997-1024, :1106-1136)
- `/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-page-honesty.md` (§7.4, §7.6, §7.8, §7.11)
- `/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-install-elsewhere.md` (§3.3, I3-7, I3-8, 2026-10-02 revision row)