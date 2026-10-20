# Handoff, 2026-10-20g: the ODS viewer is ready to link; the link is the owner's

**First line:**
- **The owner's goal: 「Nextcloud 裡點 .ods 就能開」.** Spec `specs/SPEC-M4-ods-in-nextcloud.md`, pinned `d7ab2815`, addenda 1–5 after it.
- **The owner's decisions this round:** "待決事項皆依fable建議進行" → **D3 = A** (subclass the shipped `DocumentEngine`) and **D5 = A** (measure Firefox's gzip retention). Both done.
- **Next is the owner's link** of `ods-viewer-v1`: `handoff/RUNBOOK-link-ods-viewer-v1.md` §2 (three short lines; about 3 minutes). It had **not been started** when this was written (20:42; no `build/ods/`, no log).
- After the link: the post-link checks (runbook §3), then **Phase E's first run** with `tools/run_ods_viewer_phase_e.py` (ready, selftest 25/25).
- v23 stays paused exactly as `HANDOFF-2026-10-20e-…` left it.

## What happened (commits in order)

1. `d7ab2815` — **the spec, pinned before any run.** The plan's criteria with fable's review folded in, D3 = A, D5 = A. **E8 corrected:** the a11y core's base pack `9901e9be` still carries `35-lang-normalize.conf` (finding 114's cause); the review and the plan's amendment both pinned `9901e9be`, which would have put 114 back into the viewer. The viewer's base is `9901e9be` minus that one file.
2. `5becb549` — **step 0 and step 1.**
   - The session refuses an encrypted package before any engine (`viewer-shell/odf-package-probe.js`; over the 306-file corpus: 3 encrypted, exactly the `expect: "refused"` ones, 0 misjudged, 0 unreadable).
   - The page: one `:root` (`light-dark()`), one hard-coded worker literal `./profiles/ods-viewer-v1/sdk-worker.js` (a comment containing `workerUrl: "./…"` would count as a second one for the packager), `data-dev-only`, `?diagnostics=1`.
   - Step 1 on `e2-editor-v14` with the 1 MiB stack, through the page's own file input: **all four predictions met** (`tdf149752.ods` opens, `password.ods` refused with no engine). v14's boot `sbrk` minus v12's = exactly 3 × (1 MiB − 64 KiB), the three started pthreads.
   - **Found:** the close stages exist only under `OXSDK_DIAGNOSTIC_CLOSE_STAGES`, so E6 as pinned could not see past the open (addendum 1: the viewer turns them on).
3. `fe8722df` — **D5-A measured:** Firefox 157 keeps the 47,987,215-byte gzip wasm; kept up to 52,428,800 (= 51,200 KiB), not 53,000,000; controls as X1. **Gzip cap = 52,428,800**; zstd stays 45,000,000 (addendum 2).
4. `762296f8` — **O2, the engine source, worker half and SDK** (all engine code under `OXSDK_ODS_VIEWER`; pure rules in `src/ods_viewer.hpp` with a native test and mutations; `OdsViewerEngine extends DocumentEngine`; the page refits after the first paint, E4b).
   - **Found:** today's engine **did not compile in the reader shape** (16 errors at HEAD). Three editor-only use sites wrapped in `#ifdef OXSDK_EDITOR_DISCOVERY`; every existing rule's objects preprocess identically (112 objects, 0 different). **The viewer switches no accessibility on** — what the plan's D2 said, and not what W2/W5/step 1 ran (editor profiles, a11y on). Registered (addendum 3).
5. `9edd8f9e` — **O3:** the Makefile rule (reader shape on `$(E2_V5_CORE)`, v14's link line with one token changed, guarded from the first link, no `probe_api` so no dark save), `tools/build_ods_viewer_profile.py` (base pack built two ways, same sha `6f7424a1…`; zstd 5,649,371), the pre-link gates, the runbook. **M1-1 changed** (`guard_variants`; witness kept): B's compile guards apply to carriers that define B; a carrier without B must refuse B.
6. `9f90d55d` — part_text replies an empty sheet's null text as `""` (`textNull`), not `LOK_ERROR` (found by reading the native oracle's `text: null`).
7. `a344c8aa` — part_text reads the text even when SelectAll's command result does not come within 3 s, and says so (`selectAllConfirmed`), so one missing notification cannot cost a second link. **Worker pin `cc2d6514…`.** The pre-link gates were re-run on this source.
8. `da9922cc` — **the Phase E runner and harness**, before any run; addendum 5 pins three readings (E4a's "where the manifest says", E2's 60 s from the case start, E3's null expected texts from the oracle).

## Next, in order

1. **The owner runs the link** (runbook §2). If they reply "done": runbook §3 — the frozen set (`o3-pre-link/frozen-set-before.sha256`, 1,430 files), `check_pthread_stack_literal.py` on the new `probe.js`, `ScDocShell` in the wasm, E1-C intact, then **archive at once** into `build/archive/ods-viewer-v1-<wasm8>-worker-cc2d6514/`, witnesses under `findings/evidence/m4-ods/o4-post-link/`.
2. **Phase E's first run:** `python3 wasm_sdk_probe/tools/run_ods_viewer_phase_e.py --only ladder/` first (fast, has the controls), then the full corpus (about 300 entries; estimate 20–30 min; ask the owner before a run that long only if it is an hour-class chain). The first red is the measurement (memory `first-run-of-a-regression-net-is-the-measurement`): check whether it is red on the product or on the judge before touching either.
3. **E6's leak bound B:** 5 boots of the viewer link for the noise floor, written into the spec before any E6 run counts.
4. **E4b and E9 on the real page:** adapt `run_ods_viewer_step1.py` (no retarget, no stack patch; scroll to the right edge for E4b; click tabs and read back for E9).
5. **The owner's first look:** the viewer on a mirror page with real sheet names and tabs. Tell the owner when.
6. **O6, host 0.2.29** (`~/Projects/Nextcloud_Apps/litecore`): one Files action for both mimes, the viewer route and `templates/viewer.php`, `js/litecore-viewer.js` providing `liteCoreViewerHost = { load }`; the packager's page table, manifest `litecore-engine/3`, **gzip cap 52,428,800**. Then O7 in the owner's ddev slot, then H7.

## Hazards

- **Never `cd`** in shell commands (it slipped once in a subshell this session; no effect, but avoid).
- **Compiling `make` belongs to the owner.** `make -n`, `make test-*` without compiles, and `em++ -fsyntax-only` / single TUs to scratch (the v14 precedent, seconds each) were run here.
- **The Makefile changed (finding 042):** every older profile target is out of date; their links refuse without `ALLOW_FROZEN_RELINK=1`.
- **`sdk/sdk-worker.js` changed in O2:** v21's and v22's packaging rules check `0d55bcfa…` and now refuse to repackage — that is their guard, by design. The viewer's rule checks `cc2d6514…`; any further change to the worker refuses the viewer's packaging too, until its pin is moved on purpose.
- **ddev is shared.** Host work only in the owner's slot.
- **The spec is append-only.**
- **Headless Chrome:** check the KDE wallet first. The owner's desktop Chrome runs all day; the new runners record it and do not refuse (no timing criterion), the old W9 smoke runner still refuses.
- `tests/test_e1_corpus.py` fails (the E1 corpus generator; it reads neither `src/` nor `sdk/`); not investigated.

## §34.4

- **This stretch:**
  - because of execution **+4**: two source-text tests in `tests/test_e2_profile.py` (a 6000-character window, the `getTextSelection` census), the W9 close test (fixed delays → wait for the call), and M1-1's per-carrier guards (witness `o3-pre-link/test-e2-c-static-red-viewer-not-declared.txt`);
  - because of review **+0**.
- **Running total since 10-14b: 37 / 27.**
- **New tools, not yet reviewed** (all diagnostic, none used for a count): `run_ods_viewer_step1.py`, `probe_gzip_retention_firefox.py`, `run_ods_viewer_phase_e.py`, `build_ods_viewer_profile.py`, `preprocess_identity.py` (one-shot), the mutation runners `ods_viewer_mutations.py`, `sdk_worker_ods_viewer_mutations.py`, `ods_document_sdk_mutations.py`.

## Owner decisions still open

- Carried from 10-20e: whether the product moves to one engine on the calc core; A3 for L-C.
- D3 and D5 are closed (A and A).
