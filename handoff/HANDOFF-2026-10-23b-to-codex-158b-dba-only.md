# Handoff, 2026-10-23b, to Codex: finding 158-B (form controls in the ODS viewer) with dbaccess's core library only -- the owner chose A; nothing written yet

The owner is moving the next tasks from Claude to Codex for usage reasons. This file has three parts: the state, the task in flight with everything Claude found before writing any of it, and the context Claude carried implicitly that Codex does not get from `AGENTS.md`. Read all three before touching anything.

## 1. State (SPEC-M3-link-batch-v22 §13.1's shapes)

- **(a) installed:** ddev's `litecore` app runs **host 0.2.32** (`bffc7dc`, main of `~/Projects/Nextcloud_Apps/litecore`) on engine package **`80349a1a24cecb17`** (editor `e2-editor-v22` wasm `f7a40bcc…`, viewer `ods-viewer-v2` wasm `aa576ce7…`). Phase H H1-H7 hold (SPEC-M4-viewer-v2 §10.4-10.5). The ddev project `litecore` is **stopped** (not paused); `engine.old` was removed on the owner's word.
- **(b) built and archived, uncounted:** the same package, `wasm_sdk_probe/build/archive/host-0.2.32-engine-80349a1a24cecb17/`; the viewer profile `build/archive/ods-viewer-v2-aa576ce7-worker-9c85043a/`.
- **(c) bound / counted:** nothing. Nominal shipped version is still **0.2.26**; the 5-hour count chain K is batched (owner's rule).
- **(d) accumulated-uncounted list:** host 0.2.29-0.2.32 (the viewer route, ODS Files action, page table, gzip cap 52,428,800, findings 157/159/160 fixed in the viewer, 161/162 host fixes).
- Previous handoff: `HANDOFF-2026-10-23-viewer-page-on-v2-host-0232-built-awaiting-slot.md` (with addenda 1-2). Specs: `specs/SPEC-M4-viewer-v2.md` (§0-§11), `specs/SPEC-M4-ods-in-nextcloud.md` (E1-E9, H1-H7). Finding: `findings/158-an-ods-with-form-controls-cannot-be-painted-on-the-wasm-core-forms-service-absent.md` (its "158-B 另立工作項" section is the work item's charter).
- §34.4 running total since 10-14b: **46 / 27** (because of execution / because of review). The budget for "because of review" is spent: that number must stay 0.

## 2. The task in flight: 158-B, option A (dba + dbahsql only)

### 2.1 Why, and what the owner chose

Today a `.ods` with form controls (`<draw:control`, 5 corpus files: `tdf134161`, `tdf106181`, `tdf121963`, `tdf154005`, `move-cell-anchored-shapes`) is refused before any engine starts (`FORM_CONTROLS_UNSUPPORTED`, 158-A). The 10-22 attempt (core `wasm-lite/build-ods-viewer-v2`, DB connectivity on, link `a6390eef`) brought the forms components in but made those 5 files **and** `tdf138507.ods` (a form without controls, which opens today) fail to open: `ODatabaseForm` aggregates `com.sun.star.sdb.RowSet` with `UNO_QUERY_THROW` (`libreoffice-26-8/forms/source/component/DatabaseForm.cxx:358`), and RowSet lives in dbaccess, which the wasm strip removes.

Claude offered (2026-10-23): **A** bring back only dbaccess's base libraries `dba` + `dbahsql` (RowSet is in `dba`); **B** bring back all of dbaccess (database UI `dbu`, `dbaxml`, `sdbt`) and reportdesign with it. **The owner chose A** (「A」). The owner will run the core build by hand (「我可以手動建置」).

### 2.2 Facts established (read from source; cite them, do not re-derive)

- `config_host.mk.in:262`: `ENABLE_WASM_STRIP_DBACCESS=@ENABLE_WASM_STRIP@` -- it has no switch of its own; it follows the global strip (always on for Emscripten).
- Where the strip acts: `RepositoryModule_host.mk:38-48` (the dbaccess module dir, plus reportdesign moved inside by the existing patch `libreoffice-26.8-wasm-reportdesign-follows-dbaccess-strip.patch`), `Repository.mk:1235` (dbaccess UI configs), `filter/Configuration_filter.mk:285` (StarBase type/filter), `postprocess/CustomTarget_registry.mk:41` (database filter fragments in base.xcd). For A, all four stay stripped except that the dbaccess module dir comes in.
- `dbaccess/Module_dbaccess.mk`: `Library_dba` + `Library_dbahsql` (+ `AllLangMoTarget_dba`) are unconditional; `ifneq (,$(filter DBCONNECTIVITY,$(BUILD_TYPE)))` adds `dbaxml`, `dbu`, `sdbt`, seven `UIConfig_*` and tests, and that block runs **to the end of the file** (its `endif` is the last line before the vim modeline). So A needs only that one condition line changed.
- `Repository.mk:409-410`: `dba` and `dbahsql` are registered unconditionally (gbuild refuses to build an unregistered library); `dbu` (`:275`), `dbaxml` (`:413`), `sdbt` (`:470`) are elsewhere. A native build without DB connectivity builds exactly dba + dbahsql already: A is a shape gbuild already has.
- `dbaccess/Library_dba.mk:35-58` links `comphelper cppu cppuhelper dbahsql dbtools fwk i18nlangtag sal salhelper sax sb sfx svl svt svxcore tl ucbhelper utl vcl xo`; every one of them is already built in `wasm-lite/build-ods-viewer-v2` (checked `workdir/LinkTarget/Library/lib*lo.a.objectlist`).
- **Why B is riskier on size:** the wasm build calls `solenv/bin/native-code.py -c workdir/CustomTarget/postprocess/services_constructors.list` (`static/CustomTarget_components.mk:23`), and in `-c` mode every constructor of every built component is referenced (`native-code.py:828-850`) -- so whatever is built gets linked, used or not. Claude first assumed native-code.py's own short dba list limited this; that was wrong.
- Constructors, from the `.component` files (the source of truth; read them, do not hand-copy): `dbaccess/util/dba.component` 8 (incl. `com_sun_star_comp_dba_ORowSet_get_implementation`, `com_sun_star_comp_dbaccess_DatabaseDataProvider_get_implementation`), `dbu.component` 26, `sdbt.component` 1, `dbaxml.component` 0, `reportdesign/util/rpt.component` 8, `rptui.component` 6.
- **Size estimate (a proxy, ±50%):** native `.text` (`build-native-26-8/instdir/program/`): dba 2,173,962, dbahsql 55,841, dbu 3,200,329, dbaxml 271,065, sdbt 51,904, rpt 1,214,823, rptui 931,809. Calibration: the 10-22 DB-connectivity group (frm + dbtools + drivers, native text about 3.95 MB) added 1,153,716 B of gzip to `soffice.wasm` (SPEC-M4-viewer-v2 §5.3), ratio about 0.29. A: about +0.65 MB gzip → the viewer wasm about 49.8 MB against the cap **52,428,800** (Firefox's cache entry limit; the packager refuses above it). `a6390eef`'s measured gzip was 49,153,029.
- **The source tree is shared.** `libreoffice-26-8` is the SRCDIR of `wasm-lite/build-ods-viewer-v2`, `build-a11y-gate0` (the shipped viewer's core), `build-headless-probe` (the editor's core) **and** `build-native-26-8`. The worktree has pre-existing modifications that must never be reset (`wasm-lite/patches/INVENTORY.md`; each patch must still pass `git apply --check --reverse`). The untracked `scriptforge-26.8-findings.md` in it is not ours; leave it.

### 2.3 The patch (A), as Claude would have written it

1. `dbaccess/Module_dbaccess.mk`, the one condition line:
   `ifneq (,$(filter DBCONNECTIVITY,$(BUILD_TYPE)))` → `ifneq (,$(and $(filter DBCONNECTIVITY,$(BUILD_TYPE)),$(if $(filter TRUE,$(ENABLE_WASM_STRIP_DBACCESS)),,yes)))`
   (`$(filter-out TRUE,…)` is wrong here: it is also empty when the variable is empty). Native (strip empty, DBCONNECTIVITY on) → unchanged.
2. `RepositoryModule_host.mk`: a NEW block, placed at least four lines away from the reportdesign patch's hunk (its trailing context ends at the `ifneq ($(ENABLE_WASM_STRIP_ACCESSIBILITY),TRUE)` line ~50) -- e.g. after that accessibility block's `endif` (~line 54):
   ```make
   # A wasm build with DB connectivity still needs dbaccess's core library: the
   # forms' ODatabaseForm aggregates its com.sun.star.sdb.RowSet when a
   # <form:form> is imported (finding 158).  Module_dbaccess.mk keeps dbu,
   # dbaxml, sdbt and the UI configs out under the strip; reportdesign stays out.
   ifeq ($(ENABLE_WASM_STRIP_DBACCESS),TRUE)
   $(eval $(call gb_Module_add_moduledirs,libreoffice,\
   	$(call gb_Helper_optional,DBCONNECTIVITY,dbaccess) \
   ))
   endif
   ```
   `build-a11y-gate0` and `build-headless-probe` have no DBCONNECTIVITY → the new block adds nothing; native takes the old branch.
3. Save it as `wasm-lite/patches/libreoffice-26.8-wasm-dbaccess-core-with-explicit-dbconnectivity.patch` (the diff of exactly these two hunks; `RepositoryModule_host.mk` already carries another patch -- produce the new patch so both reverse-check), add it to `INVENTORY.md` (table row + the "headless probe" paragraph + a dated line), and run the inventory's reverse-check loop: all ten must pass.
4. No `configure.ac` change → no autogen re-run in any tree; K-1 of `tools/check_ods_viewer_v2_core.py --stage configure` should still hold on `build-ods-viewer-v2` (run it).

### 2.4 Order of work (write the spec FIRST; the repo's rules in AGENTS.md §1-§10 apply)

1. **`specs/SPEC-M4-viewer-v3.md`** (zh-TW), pinned before any patch is applied, any build or any run: the decision (A, owner, quote), §2.2's facts, the patch, the checks, the fallbacks and the Phase E criteria below. Commit it alone.
2. Apply the patch (2.3), inventory, reverse-checks. Commit.
3. **`tools/check_ods_viewer_v3_core.py`** (small; import helpers from `check_ods_viewer_v2_core.py` rather than editing it -- its K-2d "no dba" clause was v2's expectation and stays as written): `--stage built` hard clauses: (K3-a) `services_constructors.list` ⊇ the constructors read from `dba.component`; (K3-b) it contains none read from `dbu`, `sdbt`, `rpt`, `rptui` `.component`; (K3-c) v2's K-2a (bridge signatures), K-2c (`OFormsCollection` + scaddins) and K-2e (link inputs exist) still hold; record-only: `soffice.wasm` size and its gzip (gzip 9, mtime 0) against 49,572,266 (the 10-22 core) → projected viewer gzip = 49,153,029 + Δ. **Red cases before the build:** on today's `build-ods-viewer-v2` it must be red on K3-a and green on K3-b; for K3-b's red, a synthetic list containing one dbu constructor (or `build-native-26-8`'s list if that tree has one). Commit with the red-case outputs under `findings/evidence/m4-ods/viewer-v3/core/`.
4. **A build script for the owner**, `handoff/ods-viewer-v3/build-core.sh`, the shape of `handoff/ods-viewer-v2/build-core.sh` (emcc 4.0.10 guard, one log per run, tail-200 on failure, `timing.txt`), `--make-only` only (no autogen), then K3. Hand the owner one short line (pasting long lines truncates). Estimate: 15-40 min (the tree's last full build was 45 min; this one compiles dba + dbahsql and relinks).
5. After K3: the **`ods-viewer-v3` link** prep (v2 is shipped, so a new name -- "version is identity"): Makefile rules and the profile builder for v3 on the `build-ods-viewer-v2` core, modeled on v2's (`ODS_VIEWER_V2` rules, `tools/build_ods_viewer_v2_profile.py`, E8′ base-pack diff read before the link), the same engine source as `aa576ce7` (`OXSDK_ODS_VIEWER_V2`), manifest must declare `form-controls`; archive the current profiles first (`build/archive/`, wasm builds are not reproducible); a link runbook; the owner links.
6. **Phase E on v3**, the runners with `--profile ods-viewer-v3` (they take `--profile`; add v3 to their `PROFILES` tuples) and **always `--out`** (every runner's default `--out` is a counted v1 directory).
7. Package **host 0.2.33** exactly as 0.2.32 was done (`findings/evidence/host-0.2.32/` is the template: worktree branch, `package_m3_engine.py --app <worktree>` -- its default `--app` is the LIVE app dir --, `offline-package-check.py`, archive, install script with pre-checks, `chain-phase-h.sh`, runbook, release text draft). Install and Phase H only in a ddev slot the owner names.

### 2.5 Criteria to pin in SPEC-M4-viewer-v3 (draft; pin before step 2)

| id | criterion | if never done |
| --- | --- | --- |
| K3-a/b/c | as 2.4 step 3 | v3 is not linked |
| F3-1 | the build fails inside dbaccess (dba/dbahsql) → stop, save the log, ask the owner; no patch chains (SPEC-M4-viewer-v2 §2.7's lesson) | -- |
| F3-2 | projected (after K3) or measured (at link) viewer gzip > 52,428,800 → stop | -- |
| V2-158B (original text, on v3) | the profile declares `form-controls`; every `formControls` file opens (E2's open conditions), E4a (each sheet's tile OK), E3 (text = expected) | 158-B not fixed; 0.2.32 stays |
| V3-NR | every corpus entry that opens on `aa576ce7` opens on v3 (per entry; `tdf138507.ods` named) | v3 not shipped |
| V3-SEE | the controls are visible: the owner looks at `tdf134161.ods` (101 controls) on the mirror page and says so; recorded verbatim, like H7 | "controls drawn" is not claimed |
| E1-E9, V2-157/159/160/160-D | re-run on v3 (new link, counts reset) | as in SPEC-M4 |

Pre-written readings: all hold → package 0.2.33. V2-158B or V3-NR red → v3 is not shipped, 0.2.32 stays, finding 158 records the next blocker (likely candidates, unverified: control painting in the headless LOK path, or another dbaccess service). Principle carried from SPEC-M4-viewer-v2 §2.5: never ship "core has forms but the shell refuses" or the reverse.

## 3. Context Claude carried implicitly (not in the repo's AGENTS.md)

### 3.1 The owner's standing rules (from Claude's global instructions; `~/.codex/AGENTS.md` has only the first one)

- Replies to the owner in Taiwan Traditional Chinese; files follow the repo rules (`handoff/**`, `findings/evidence/**`, upstream text in English; `specs/`, `devlog/`, `research/`, findings' own pages in zh-TW).
- `sudo`: never; give the owner the command.
- **Any `make` that compiles** (LibreOffice core, engine links, other projects) goes to the owner: say where to run it, how long, what to report back. Test-only targets (`make -k test-e2-c-static`, `make test-*`) and cp-only staging (`make ods-viewer-assets`) you run yourself. Before handing over a long build, look at `uptime` and `pgrep -a make`.
- Short commands (seconds: installing a host version, a merge + `occ upgrade` script) you run yourself; hour-long chains: ask whether to start them detached (`setsid nohup`) or hand them over.
- When offering choices, label them **A, B, C** (not 甲乙丙), with a recommendation.
- Reports go into `.md` files in the repo, never web pages.
- End every reply with what comes next; continuity is the agent's job, not the owner's.
- Commit messages: never a `Claude-Session:` line. Claude added `Co-Authored-By: Claude …` here (outside `~/OSSII`); for Codex's own commits, ask the owner what trailer, if any, they want. Codex's global rule: one cohesive unit per commit.

### 3.2 Claude's memory -- readable on disk; read these before starting

`/home/jiajun/.claude/projects/-home-jiajun-LibreOffice-study-LiteCore/memory/` (`MEMORY.md` is the index; each file is one fact with **Why** and **How to apply**; some lines are dated and may be stale -- verify a file/flag still exists before relying on it):

- working with the owner: `user-handles-core-rebuilds.md`, `short-commands-run-them-yourself.md`, `ddev-is-shared-do-not-occupy.md` (ddev slots are the owner's; v1.25.3 has no `pause`), `owner-can-run-long-chains.md`, `always-say-what-is-next.md`, `no-release-deadline-framing.md`, `demo-to-colleagues-goal.md`
- measurement discipline (the reason most of this repo looks the way it does): `probe-measurement-discipline.md`, `first-run-of-a-regression-net-is-the-measurement.md`, `harness-path-vs-user-path.md`, `no-verbatim-text-chasing.md`, `checks-stop-rule-spec-34.md`, `user-symptom-may-be-the-step-before.md`
- artifacts and trees: `wasm-build-not-reproducible.md` (archive before any relink; never rebuild between a sweep and its verdict), `libreoffice-worktree-constraints.md`, `study-litecore-git.md` (allowlist `.gitignore`: new directories are not tracked by default -- check `git status` after adding one), `e2b-structural-lessons.md`
- runners and the desk: `evidence-runners-write-by-default.md` (read a runner's docstring before running it; many overwrite committed evidence; use `--out`), `reboot-locks-kwallet-headless-chrome-hangs.md` (`ChromeSession` now passes `--password-store=basic`; still check `busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`), `nextcloud-work-uses-owner-ddev-scaffold.md`, `timing-runs-need-quiet-desk-and-idle-session.md`
- policy: `release-count-batched.md` (K stays batched), `upstream-submissions-on-hold.md` (no upstream submissions), `doc-conventions.md` (zh-TW full-width punctuation; evidence markers 〔已觀察〕〔讀原始碼〕〔推論〕〔未量〕; revise in place with a revision table, except gate documents, which are append-only per AGENTS.md §10)
- history: `litecore-wasm-sdk-status.md` (long; the latest entries are at the end)

### 3.3 Claude-only things the documents mention

- **"fable" / "fable's ruling"** in specs and findings = a separate, stronger Claude model used as an external judge on decisions the owner delegated, each ruling written into the tree. Codex cannot call it. For judgement calls (design trade-offs, "does this conclusion hold"), give the owner A/B/C with a recommendation and the measured numbers.
- "subagent", "opus review", "two-seat review" = Claude's delegation; "codex" in older notes means Codex as a read-only second reviewer (`codex exec -s read-only … < /dev/null`).
- Artifacts / claude.ai pages are never used here.

### 3.4 Environment the runners need (check Codex's sandbox before the first run)

- Mirror runners start a local HTTP server (`web/serve.py` on a free port) and a headless Chrome over CDP (`tools/run_browser_probe.py` `ChromeSession`), sometimes Firefox; host runners talk to ddev (`https://litecore.ddev.site:8443`, docker underneath, the admin password read from the ddev config by `check_m3_skeleton_open.Instance`) and read the container's Apache log with `ddev exec`. A sandbox without localhost networking, process spawning or the docker socket will make them fail in ways that look like product failures -- if so, run them outside the sandbox or hand them to the owner.
- Paths: repo `/home/jiajun/LibreOffice/study_LiteCore`; core trees `wasm-lite/build-*`; LibreOffice source `libreoffice-26-8` (shared, see 2.2); host app `~/Projects/Nextcloud_Apps/litecore` (it IS the live ddev app dir: build packages in a git worktree, never in place); native reference `build-native-26-8`.
- Tests: `node --test wasm_sdk_probe/tests/ods-viewer-session.test.mjs wasm_sdk_probe/tests/ods-document-sdk.test.mjs wasm_sdk_probe/sdk/tests/sdk-worker-ods-viewer.test.mjs`; every judge/probe has `--selftest`; `make -k test-e2-c-static` in `wasm_sdk_probe` (about 40 s).
- Disk: `/` at 91% (87 GB free on 2026-10-23); a profile archive is ~180 MB, a host package ~192 MB.

## 4. Hazards

- `package_m3_engine.py`'s default `--app` is the live app dir; ODS runners' default `--out` is v1's counted directory.
- The pre-link tools `run_ods_viewer_step1.py` / `run_ods_viewer_draft_smoke.py` refuse now (they retarget from v1's literal); intended.
- Do not edit a file a running measurement imports.
- `build-ods-viewer-v2` is 158-B's starting point and nothing ships from it today; `build-a11y-gate0` is the shipped viewer core and `build-headless-probe` the editor's -- never rebuild those two for this task.
- A new check's first red is a measurement; before "fixing" a check, read §34 (a check change needs a witness report).
