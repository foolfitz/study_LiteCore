# Handoff, 2026-10-20h: `ods-viewer-v1` is linked and archived; Phase E's first run is next

**First line:**
- **The owner's goal: 「Nextcloud 裡點 .ods 就能開」.** Spec `specs/SPEC-M4-ods-in-nextcloud.md` (pinned `d7ab2815`, addenda 1–5). Read the spec's addenda; they supersede parts of §3–§4.
- **The owner linked `ods-viewer-v1`** on 2026-10-20, 21:16–21:18. wasm `f6ab3cdb…`, worker `cc2d6514…`. Every post-link check passed (`findings/evidence/m4-ods/o4-post-link/README.md`, `31e2622b`). Archived at `wasm_sdk_probe/build/archive/ods-viewer-v1-f6ab3cdb-worker-cc2d6514/`.
- **Nothing has run on the new profile yet.** The first run is Phase E's: `tools/run_ods_viewer_phase_e.py` (selftest 25/25, written before the link, `da9922cc`).
- The round before this one, in detail: `handoff/HANDOFF-2026-10-20g-ods-viewer-link-handed-to-owner.md` (what each commit did, what was found, hazards). This file only adds the link and what comes next.
- The owner asked for this handoff at a context soft limit. Start a fresh session from here.

## State in one table

| item | state | where |
| --- | --- | --- |
| D3 (viewer SDK) | **A** done: `OdsViewerEngine extends DocumentEngine`, zero bytes under `sdk/document-sdk.js` | `viewer-shell/ods-document-sdk.js` |
| D5 (gzip cap) | **A** measured: Firefox 157 keeps up to 52,428,800 → gzip cap 52,428,800, zstd 45,000,000 | spec addendum 2, `findings/evidence/m4-ods/d5-gzip-retention/` |
| Step 1 (v14 mirror, 1 MiB) | 4/4 predictions; 089's file opens through the page | `findings/evidence/m4-ods/step1-mirror-v14-1mib/` |
| O2 engine / worker / SDK | landed; the reader shape had not compiled (fixed; the viewer turns no a11y on) | spec addendum 3, `o2-engine-source/` |
| O3 rule / builder / runbook | landed; M1-1 guards per carrier (witness kept) | spec addendum 4, `o3-pre-link/` |
| O4 link | **done, checked, archived** | `o4-post-link/` |
| Phase E runner | ready, not run; three readings pinned | spec addendum 5 |
| E6 leak bound B | not measured (5 boots of the viewer first) | spec §4 E6 |
| E4b / E9 page runner | not written (adapt `run_ods_viewer_step1.py`) | — |
| O6 host 0.2.29 + packager | not started | spec §3.4–3.5, addendum 2 |

## Next, in order

1. **Phase E, the ladder first:** `python3 wasm_sdk_probe/tools/run_ods_viewer_phase_e.py --only ladder/`. Check the KDE wallet first (the runner refuses if it is locked). The empty control is always staged. Then the full corpus (about 300 entries; estimated 20–30 min).
   - **The first red is the measurement.** Before changing anything, decide whether it is red on the product or on the judge, and read the raw case record (`report-*.json`). The judges are new and not reviewed; if one is wrong, that is a §34 "because of execution" fix with the report as witness.
   - What this run can show for the first time: E2 under the real `.ods` name, `documentType`, E3 part text against the native oracle, E5 switching read back from the engine, E6 peaks with the close stages, and `selectAllConfirmed` (was SelectAll's command result ever missing?).
2. **E6's B:** 5 boots of the viewer link, the noise floor written into the spec (append) before any E6 run counts.
3. **E4b and E9 on the real page** (`web/ods-viewer.html`, whose worker literal already names `ods-viewer-v1`): scroll to the right edge for E4b (step 1 drew only to 1024 px in the headless viewport); click each tab and read back for E9.
4. **The owner's first look:** the viewer page on a mirror, with real sheet names and tabs. Tell the owner when and how (a local server URL).
5. **O6, host 0.2.29** (`~/Projects/Nextcloud_Apps/litecore`), then O7 in the owner's ddev slot, then H7.

## Hazards (new since 10-20g)

- The archive is the only way back to `f6ab3cdb` (finding 036). Never relink `ods-viewer-v1` incidentally; its rule is guarded.
- `sdk/sdk-worker.js` is pinned at `cc2d6514` for this profile. Any change to it means a new worker for the next viewer profile, not this one.
- `cd` slipped into subshells (`( cd … )`) a few times this session. No effect on the session's directory, but follow the rule: no `cd`.

## §34.4

- This stretch (after 10-20g): because of execution +0, because of review +0.
- **Running total since 10-14b: 37 / 27.**
- New tools not yet reviewed: as listed in 10-20g (unchanged).

## Owner decisions still open

- Carried from 10-20e: whether the product moves to one engine on the calc core; A3 for L-C.
