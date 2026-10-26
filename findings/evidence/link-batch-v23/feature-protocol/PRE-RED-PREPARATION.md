# Public v19 S2 pre-red instrument preparation

This unit implements only the corrected sixteen old-v19 SDK cells in each browser (32 complete population entries), plus a reusable S2 state-comparison function. It does not implement all feature S1–S5 runtime arms, create native continuation oracles, or claim feature acceptance. No browser has run this instrument. The current preparation is source, mirror construction, syntax checks and synthetic raw-wire reader controls.

The historical product graph is frozen shell v57, commit `6e9ec27eb4163aa52a9288ee7549569ae5a46405`. Every included JavaScript file is read from that commit and checked against `e2/editor-shell-v2-bundle-v57.json`. The original HTML is read from the same commit; its single module entry is replaced only in the new measurement mirror by `v23-feature-pre-red.js`, which imports the original product app after installing observation wrappers. It records Worker requests/replies and observes the original session's open method without changing arguments or results. The original product sink, input adapter and commit handler perform the readiness edit. No original/frozen source or artifact is overwritten. Current ABI6 client/page changes cannot silently enter this old-source mirror.

Actual profile/loader/worker/manifest bytes must equal the v19 archive `build/archive/e2-editor-v19-1aafd4f9-worker-00882139`, with explicit WASM pin `1aafd4f9da42fd83d9be4c4e9edfbd818e3c7ea17d62fa1cb1bfbd47d1a32819`. Resource files are also hashed. The mirror's private `list-contexts.odt` alias carries the exact archived extend-signature FODT bytes, not the historical bundled list-contexts content; its generated one-entry fixture manifest and the alias bytes are bound and browser-fetched. This lets the original product boot load precisely the measured fixture. A subsequent actual file-input open of `feature-pre-red.odt` reloads those same bytes in a fresh product session.

The readiness sequence uses public search/caret/Home setup on the first paragraph, captures actual V2 engine state and a baseline save, focuses the original enabled/connected/non-readOnly `#sink`, and sends a real browser `Z` key. A successful public insertText request, revision advance and an independently parsed save with exactly `Z` at the first paragraph start are all required. The instrument does not proceed to measured Shift when this evidence is absent. It then reloads the original through the product file input and proves the readiness marker is absent in a saved document.

Each measured caret shape is located using actual public search results and the existing public Home/End/Right actions, never native XY or unexposed Ctrl+Down. Setup prefix selection/readback independently checks the logical point before restoring the measured caret. The native source table owns the sixteen IDs and their original pre-key text. A wrapped-line endpoint uses the actual browser's Home→End result and verified literal prefix; empty-paragraph placement uses the preceding paragraph End→Right. Every setup request is bound to its actual public call and input coordinates.

The measured move is the old SDK client's actual Left/Right with extendSelection=true. The old page's Shift-dropping key handler is not used as the pre-red stimulus. Keep raw terminal, full state, generation/request ID, revision and completion evidence. The delayed public getState occurs at least 500 ms after the terminal, followed by active getSelection. **Both historical and current narrow clients use literal editorGetStateV2**; wrong V1 evidence is rejected. A valid stale reply gives EXPECTED_RED. A valid matching reply gives UNEXPECTED_GREEN and stops progression. Refusal, missing readiness/open/state, duplicate terminal, early readback, wrong shape or identity, or absent data gives NOT_ESTABLISHED and also stops. Missing or repeated population entries and reused actual page observations cannot pass the aggregate.

The runner uses the existing shared browser lock, CPU guard and owned browser/server cleanup. It freezes source/profile/fixture bindings before execution, checks them per cell and afterward, preserves every completed/failing cell, and stops at the first non-EXPECTED_RED without product retries. Full snapshots use UTF-8/base64 chunks with exact reconstructed length and SHA-256 checks; raw wire data is not truncated. The outer observation bound is instrument containment, not a feature completion policy. Full source readiness remains conditional on a coordinator-scheduled first preparation run; synthetic controls cannot establish that the old product path loads/edits in today's browser.

## Commands for a later coordinated window

From the repository root, first one explicitly uncounted cell:

```sh
python3 -I wasm_sdk_probe/tools/run_v23_feature_pre_red.py --v19-wasm-sha256 1aafd4f9da42fd83d9be4c4e9edfbd818e3c7ea17d62fa1cb1bfbd47d1a32819 --preparation-only --browser chrome --case-id shift-Left@caret-mid --output findings/evidence/link-batch-v23/feature-pre-red/preparation-01
```

After the coordinator reviews the preparation under the owner’s standing autonomous grant, a fresh unfiltered 32-cell population (no repeated/reused preparation cells):

```sh
python3 -I wasm_sdk_probe/tools/run_v23_feature_pre_red.py --v19-wasm-sha256 1aafd4f9da42fd83d9be4c4e9edfbd818e3c7ea17d62fa1cb1bfbd47d1a32819 --output findings/evidence/link-batch-v23/feature-pre-red/counted-01
python3 -I wasm_sdk_probe/tools/judge_v23_feature_pre_red.py findings/evidence/link-batch-v23/feature-pre-red/counted-01/report.json --v19-wasm-sha256 1aafd4f9da42fd83d9be4c4e9edfbd818e3c7ea17d62fa1cb1bfbd47d1a32819
```

The full reader rejects preparation-only reports. EXPECTED_RED closes only the old-v19 witness prerequisite; it is not feature S2 PASS.

## Concrete remaining S5 native preparation

The archived `tool-source-as-run.cpp` in the extend-signatures run performs one move followed by snapshots; it has no continuation-save oracle for the new table. The old executable must not be invoked as if it accepted seven continuation families. A future isolated source fork needs explicit family selection from `s-cases.json`, exact literal `x` input, each ordered delete/Shift/delete sequence, actual before/after saveAs ODT artifacts, native selection/undo evidence, and source/core/fixture identities. Its reader must validate literal-safe eligibility and compare saved documents using the existing reduced-content/paragraph-text functions. Missing native artifacts remain NE. Layout-dependent cells instead need the separately specified fresh settled-WASM reference, not native endpoint reconstruction.

The owner compile template, **not yet runnable because that source fork is not implemented**, is the archived harness's actual build recipe with new filenames:

```sh
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
g++ -std=c++17 -O2 -I../libreoffice-26-8/include tools/v23_native_s5_continuations.cpp -ldl -lpthread -o build/v23-native-s5-continuations
```

The future runtime must bind `native-lok-26-8/build/instdir/program`, use isolated fresh documents/profiles and retain each actual save. No owner compile is requested by this document yet. A compiled binary, finite input dispatcher, actual oracle runs and reader are all still missing; no 588-cell runtime completion is claimed.

## List-mid discovery correction before the replacement cohort

The retained `feature-pre-red/counted-01/chrome-shift-Left@list-mid.json` is NOT_ESTABLISHED because the instrument did not reach native p7.5. Its actual search rectangle and clicked caret start at x2138; the inserted Home moves to x1778 before the list label. The first of five Right actions returns to x2138, so the final selected prefix is only `List` (four text characters), not native `List ` (five). The native `discover-p7` record has prefix `List ` and suffix `item one`; its `makeShape` clicks that discovered p7.5. The original cohort remains six EXPECTED_RED entries followed by this setup NE, never a full pass.

Scope authorizes this one setup correction: both list-mid direction cells declare `anchor: search-text-start`; after the public search-derived click, capture actual start state and issue exactly five Right actions, with **no Home**. Require that start state's actual V2 caret equal the search rectangle's text start, and retain the exact literal `List ` prefix, paragraph7, offset5, query and source fixture. Other shapes keep their existing setup. The reader rejects an inserted Home, offset4/four Rights, a missing trailing space even when page and wire agree, or an anchor different from the actual search text start. The actual JavaScript locate function was red before this change in a model of the observed label transition (`List` versus `List `), then green with the corrected branch.

This changes the new instrument/source graph, not v19, its frozen shell, the feature product, the original sixteen-cell membership or the expected stale-reply predicate. After preparation under the corrected graph, use a fresh complete32-cell cohort. Do not splice the old six rows into it or relabel the old list NE. No runtime was performed while making this correction.
