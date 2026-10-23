# Viewer v3 core preparation (finding 158-B), 2026-10-23

Spec: `specs/SPEC-M4-viewer-v3.md`, pinned before the patch. The owner chose dba + dbahsql only. **The core has not been rebuilt yet.** These are pre-build measurements, not evidence that 158-B is fixed.

## Patch and configuration

- `patch-reverse-checks.txt`: all ten LibreOffice patches pass `git apply --check --reverse` in the shared `libreoffice-26-8` worktree, including the existing reportdesign patch and the new dbaccess-core patch separately.
- `k1-configure-before-build.json`: the unchanged v2 checker, `--stage configure`, passes K-1a through K-1e against `wasm-lite/build-ods-viewer-v2`. No autogen was run.
- `module-selection.json`: a one-time measurement using GNU make to expand the actual patched module files with recording macros and a no-op target, compiling nothing. The four combinations (strip TRUE/empty, DBCONNECTIVITY present/absent) match the intended scope. The library list is what `Module_dbaccess.mk` selects *when read*; when the module is not selected, that list does not mean anything is built. This is not an additional gate.

## K3 red cases before the build

Commands, from the repo root:

```bash
python3 wasm_sdk_probe/tools/check_ods_viewer_v3_core.py --stage built
python3 wasm_sdk_probe/tools/check_ods_viewer_v3_core.py --self-test
```

Use `--report <new-path>` to save a rerun; do not overwrite these pre-build reports after the owner builds. The self-test intentionally requires the pre-build state and will no longer apply once dba is present.

- `k3-before-build.json`: exit **1**, K3-a **red**, K3-b **green**, K3-c **green**. All eight constructors read from dba.component are absent, including RowSet. None of the constructors read from dbu/sdbt/rpt/rptui are present. Existing bridge signatures, forms/scaddins constructors and the five link inputs pass the inherited v2 checks.
- `k3-red-cases.json`: exit **0**, meaning the three expected outcomes occurred: the actual pre-build list fails a and passes b; the **synthetic** list with all dba constructors added passes a/b; adding one constructor read from dbu.component makes b red. Synthetic results are checker controls, not evidence of a built core. The report records the exact injected constructor and all source sets/hashes.
- `first-run-missing-dbaxml/`: the first attempt failed before evaluating any clause because I used `dbaccess/util/dbaxml.component`; the actual file is `dbaccess/source/filter/xml/dbaxml.component`. The initial outputs are retained. This was a new checker under construction, before it judged anything; the v2 checker was not changed.

The measured baseline core has `soffice.wasm` 153,330,836 B, gzip **49,572,266 B** (level 9, mtime 0), reproducing the spec's 10-22 baseline. Its projected viewer size is therefore still the *old* diagnostic viewer's 49,153,029 B. This says nothing yet about the new core's size; F3-2 must be read after the build and again after linking.

## Next

The owner runs `bash handoff/ods-viewer-v3/build-core.sh --make-only` from the repo root. The script writes each run into a fresh `runs/<id>/` directory, checks K-1 before make, and K3/F3-2 afterwards. If dbaccess fails to build, stop and read the saved log with the owner; do not grow a patch chain. Only a green built K3 and an in-cap projection permit v3 link preparation.

Section 34.4: this preparation adds a checker for a newly pinned criterion; it does not change any existing checker. Because of execution **+0**, because of review **+0**; cumulative **46 / 27**.
