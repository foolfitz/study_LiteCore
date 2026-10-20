## SUMMARY

W9 draft of the read-only ODS viewer, source only. Not staged to `dist/`, not bound by any gate, to be revised once W7 exists. Nothing here is gate evidence; if W7 never lands the default conclusion is that G9 stays closed and every report from this draft stays `diagnostic`.

- **Files added** (all new, no existing file edited): `wasm_sdk_probe/viewer-shell/{ods-viewer-session,w7-adapter,viewer-error}.js`, `web/ods-viewer.html`, `web/ods-viewer-app.js`, `tests/ods-viewer-session.test.mjs`, `tools/run_ods_viewer_draft_smoke.py`, and this directory (`red-cases.py/.json/.txt`, `bundle-check.txt`, `smoke-report.json`, `wait-log.txt`). `viewer-shell/` had to be force-added: `.gitignore`'s allowlist does not list it (not edited; see Notes).
- **Adapter-only (pre-W7) list**, all in `viewer-shell/w7-adapter.js`: (1) name spoof `.ods` to `.odt` (finding 013) -> `nameSpoofed`; (2) `documentType` of the handle else `"unknown (pre-W7)"`, a KNOWN non-spreadsheet is refused `DOCUMENT_TYPE_REFUSED`; (3) part names `工作表 1..N` with `namesFromEngine: false`; (4) no `setPart` -> part k>0 refused `PART_SWITCH_UNAVAILABLE`, tab disabled with the reason; (5) `currentPartReadBack: null`, never the requested k. `evidenceClass` is `diagnostic` while any of these stood in. A test scans the directory so this vocabulary cannot leak into the session.
- **Unit test: 18/18** (`node --test wasm_sdk_probe/tests/ods-viewer-session.test.mjs`), fake engine + a pre-W7 handle and a W7-shaped handle. **Red first: 27 mutations of the session/adapter, every one turns the test red, each in a test it was meant to hit** (`red-cases.txt`; the harness also fails if a replacement does not apply exactly once, if the unmutated copy is not 18/18, or if a test is named by no mutation).
- Caught by: tabs=parts M01 (line 173); showPart reconfigures with part k M02 (line 220); read-back not echoed M03/M04 (lines 230, 200); pre-W7 showPart(1) refused and nothing repaints M05 (line 262); known `text` refused M06 (line 296); spoof flag only when spoofed M09/M10/M11 (lines 337-339).
- **Smoke: ONE browser run**, Chrome 151, `e2-editor-v14`, through the page's own file input, both files in one page: `DRAFT SMOKE: every expectation met (diagnostic, not gate evidence)` (13/13 expectations; `smoke-report.json`). `opened` yes/yes; `parts` 3 and 1; tabs 3 and 1, texts `工作表 1/2/3` and `工作表 1` (synthesised); enabled `[true,false,false]` and `[true]` (disabled ones carry a title); `nameSpoofed: true`; `evidenceClass: "diagnostic"`; `currentPartReadBack: null`; `documentType: "unknown (pre-W7)"`; `showPart(1)` -> `PART_SWITCH_UNAVAILABLE`, 12 tiles before and after.
- **First-tile comparison (recorded, not a gate): NOT byte-equal**, three-sheet `0a516b644c78...` vs empty `387aac13437d...` (same 256x256 size; non-paper pixels 4817 vs 4545).
- Smoke judge shown red: `run_ods_viewer_draft_smoke.py --selftest` 20/20 (a clean control plus 19 broken reports, each flips the named expectation; zero runs is red, not "zero problems").
- Smoke preconditions were enforced by the runner itself (wallet `b false`, no other Chrome, load 1-min 0.09 < 1.0). Waited 1985 s (33 min, 34 polls) for the other agent's 089 chain to finish; the run itself took 9.7 s. Nothing under `dist/` was written (nothing newer than 17:00 anywhere in it afterwards).
- **Bundle check** (`bundle-check.txt`): `build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v66.json` WITHOUT `--write`: digest `70c34178...d027439`, `problems: []`, 13 included, output byte-identical before and after adding the files (`cmp`). `check_e1_c_bundle_intact.py`: `intact: true`. Product page graph reaches no viewer file; the viewer reaches only `reader-shell/tile-scheduler.js` and `sdk/document-sdk.js` (both unmodified, served hashes `4c60ab4e...` and `e4c3fe92...` equal v66's).
- **What W7 must provide for G9** (member names are my INFERENCE from the plan text, one constant each in the adapter): ods open allowed by name + a manifest capability (assumed `open-ods`); `documentType` on `opened`/handle; `partNames` (length == parts); `setPart(k, options)` ordered with paints, refreshing the per-part size; `currentPart` read from the ENGINE (initial value on `opened`, refreshed after every set_part); all of it in `sdk/document-sdk.js`+`.d.ts`, i.e. a new shell bundle generation. Details below.
- Commits: see `git log -- findings/evidence/m4-ods/W9-viewer-draft` (code `28daa47e`; evidence+README in the follow-up commit).

## Details

### Layout and import discipline

`web/ods-viewer-app.js` imports `./sdk/document-sdk.js` and `./viewer-shell/ods-viewer-session.js` (the DIST layout, like every page in `web/`); the session imports `../reader-shell/tile-scheduler.js`. The session never touches the engine except through the adapter's view (`render`, `setPart`, `close`, read-only facts), and the unit test records every call on a Proxy and asserts the set is a subset of `{render, setPart, close}` on the document and `{open, onEvent, dispose}` on the engine (the exercised calls are also asserted non-empty, so an empty log cannot pass).

The engine factory in the page attaches the listener BEFORE `_initialize()` (commit 88472109, finding 089 E0); the session hands its event sink INTO the factory for the same reason, and a test emits an event during "init" to prove the order.

### Tests and the red exhibit

Run order (nothing here needs a browser): `node --test wasm_sdk_probe/tests/ods-viewer-session.test.mjs`; `python3 findings/evidence/m4-ods/W9-viewer-draft/red-cases.py`. The harness copies `viewer-shell/` to a scratch directory, breaks the copy once, runs the same test file with `VIEWER_SHELL_DIR` pointing at the copy and records which test failed and at which assertion (first stack frame in the test file). The real source is never edited.

| id | what was broken | test that caught it | assertion | failing |
|---|---|---|---|---|
| M01 | the tab strip has one tab fewer than parts | pre-W7 handle | 173 `assert.equal(state.tabs.length, 3);` | 3/18 |
| M02 | the scheduler is reconfigured with part 0 whatever part was switched to | showPart(k) | 220 `assert.equal(tile.part, String(k), "the scheduler's tile key carries part k");` | 2/18 |
| M03 | the session reports the requested part as the read-back | an engine that ignores set_part | 230 `await assert.rejects(session.showPart(1), (error) => {` | 2/18 |
| M04 | the adapter's read-back is the last part asked for, not the engine's current part | W7-shaped handle | 200 `assert.equal(state.currentPart, 2);` | 2/18 |
| M05 | without a part switch, part k > 0 is accepted and shown | pre-W7 | 262 `await assert.rejects(session.showPart(1), (error) => {` | 1/18 |
| M06 | a document the engine says is text is shown as a spreadsheet | a known non-spreadsheet document is refused, released, and paint | 296 `await assert.rejects(session.open({ bytes: bytesOf(), name: "letter.ods" }), (er` | 1/18 |
| M07 | a refused document is left open in the engine | a known non-spreadsheet document is refused, released, and paint | 304 `assert.equal(handle.closed, true, "the document was handed back");` | 1/18 |
| M08 | an UNKNOWN document type is refused too (refusal no longer needs a known wrong type) | refusal needs a KNOWN wrong type | 162 `await session.open({ bytes: bytesOf(), name });` | 5/18 |
| M09 | the spoof flag is set even when the name was passed through unchanged | the spoof flag is set only when the adapter rewrote the name | 339 `assert.equal(state.nameSpoofed, item.spoofed, item.label);` | 2/18 |
| M10 | the name is rewritten to .odt but the flag says it was not | the spoof flag is set only when the adapter rewrote the name | 339 `assert.equal(state.nameSpoofed, item.spoofed, item.label);` | 1/18 |
| M11 | an engine that lists the ods capability is spoofed anyway | the spoof flag is set only when the adapter rewrote the name | 337 `assert.equal(engine.openCalls[0].name, item.openedAs, item.label);` | 2/18 |
| M12 | a late tile of the previous part is delivered under the new one | a tile of the previous part never reaches onTile | 351 `assert.equal(tiles.length, 0, "no part-0 tile was delivered under part 1");` | 1/18 |
| M13 | a part switch does not invalidate the previous part's generation | a tile of the previous part never reaches onTile | 351 `assert.equal(tiles.length, 0, "no part-0 tile was delivered under part 1");` | 1/18 |
| M14 | the event listener is added after the engine has initialised | the event listener is attached before initialisation | 364 `assert.deepEqual(events.map((event) => event.message), ["preRun echo"]);` | 1/18 |
| M15 | painting a tile also sends the engine a click | read-only | 393 `assert.deepEqual([...handleCalls].filter((call) => !allowedHandle.has(call)), []` | 1/18 |
| M16 | the word pre-W7 appears outside the adapter | W7 vocabulary appears only in the adapter | 408 `assert.ok(!token.test(source), `${file} must not contain ${token}: that knowledg` | 1/18 |
| M17 | a handle without documentType is reported as a spreadsheet | pre-W7 handle | 180 `assert.equal(state.documentType, "unknown (pre-W7)");` | 2/18 |
| M18 | invented sheet names are reported as the engine's | pre-W7 handle | 175 `assert.equal(state.namesFromEngine, false);` | 2/18 |
| M19 | a partNames array of the wrong length is used as it is | partNames that disagree with parts are not used and the disagree | 449 `assert.equal(state.tabs.length, 3, "still one tab per part");` | 1/18 |
| M20 | two quick tab clicks run concurrently | switches are serialised | 417 `assert.equal(handle.currentPart, 2);` | 1/18 |
| M21 | a worker-crashed event does not change the state | a worker crash takes the session to a typed error and stops sche | 426 `assert.equal(session.state.state, "error");` | 1/18 |
| M22 | a part outside 0..parts-1 is passed to the engine | a part outside 0..parts-1 is refused before the engine is asked | 286 `await assert.rejects(session.showPart(k), { code: "PART_OUT_OF_RANGE" });` | 1/18 |
| M23 | a failed open leaves the engine running | an open that fails is typed, and the engine is given back | 442 `assert.equal(engine.disposed, true);` | 2/18 |
| M24 | the part the engine is on at open is not read; part 0 is assumed even when the engine says otherwise | W7-shaped handle | 200 `assert.equal(state.currentPart, 2);` | 1/18 |
| M25 | an engine that finishes starting after close() is used to open the document | a close() that arrives while the document is opening is not undo | 467 `assert.equal(engine.openCalls.length, 0, "no document was opened on it");` | 1/18 |
| M26 | a document that opens after close() is adopted and the session comes back to life | a close() that arrives while the document is opening is not undo | 480 `await assert.rejects(opening, { code: "CLOSED_DURING_OPEN" });` | 1/18 |
| M27 | close() does not tell an in-progress open that it was closed | a close() that arrives while the document is opening is not undo | 465 `await assert.rejects(opening, { code: "CLOSED_DURING_OPEN" });` | 1/18 |

Two things the exhibit found while it was being built: (a) the first M23 replacement stopped applying after a later edit of the session, and the harness's "applies exactly once" rule reported it instead of letting a stale mutation go green; (b) a `close()` that raced an `open()` used to be undone by the open finishing later (a leaked engine and a session resurrected as "ready"); that was fixed in the session, covered by one test, and M25-M27 are its mutations.

### Smoke details

`tools/run_ods_viewer_draft_smoke.py` mirrors `dist/` with symlinks into a scratch root (the `probe_ods_on_profile.py` pattern), writes the five page files into the mirror only, serves it with `web/serve.py --root`, and drives `#file-input` with CDP `DOM.setFileInputFiles` (`three-sheets-distinct.ods` first, `empty-one-sheet.ods` second, same page). Before open the page hashes the input; both fixtures' sha256 are in the report (`0402e52724cb5bbd...`, `27c90c9863e758cd...`). The report carries the sha256 of every page file it served, of the two files imported unmodified as served, and of the profile's `sdk-manifest.json`.

Engine events seen in both runs: `resource-pack-loaded`, `view-ready`, `editor-state`. Opened at 1579 ms and 1020 ms after the run started (engine start included). Open reply size 26593 x 13005 twips for both.

### What W7 must provide for this draft to meet G9

Each item is where the draft currently substitutes, and what replaces the substitute. Names are INFERRED, not read from W7 (which does not exist); the adapter holds one constant or one member access for each, so a different name is a one-line change.

1. **Open by `.ods` name.** The `format` allowlist `{odt, ods}` (finding 013) and a manifest capability string the adapter can test (assumed `open-ods`, constant `OPEN_ODS_CAPABILITY`). Then `nameSpoofed` becomes false by itself.
2. **`documentType`** on the `opened` reply, surfaced as `DocumentHandle.documentType` (`"spreadsheet"` for Calc, anything else for Writer). `sdk/sdk-worker.js` whitelists reply fields (finding 062's comment), so the field is invisible to the SDK until it is named there. Needed for G2's injection 2 (the refusal path is already tested with a `"text"` handle).
3. **`partNames`**, an array of non-empty strings of length `parts`, from `part_name` per part. A wrong-length array is treated as W7 being wrong (recorded in `partNamesProblem`), not as W7 being absent.
4. **`setPart(k, options)`** on `DocumentHandle` -> engine `set_part`. It must be ordered with paints in the worker queue (the draft can only serialise its own calls; a paint queued before a `set_part` must not return the new part's pixels), and the reply or the handle must refresh `widthTwips`/`heightTwips` because sheets differ in size.
5. **`currentPart` read from the engine**: the initial value on `opened` (a Calc document opens on its saved active sheet, not necessarily 0) and refreshed from the engine after every `set_part`, never copied from the argument. The draft's tests include an engine that ignores `set_part` and an adapter that caches the request; both turn red.
6. **Where it lives.** All of 2-5 are `DocumentHandle` members, i.e. `sdk/document-sdk.js` and `.d.ts`, which are inside the bundle (`included` in v66). That is a new shell generation by the plan's own W7 row; the viewer imports the file unmodified until then.
7. **Profile manifest** for the relinked profile lists the new capability and the matching `expectedCapabilityBits`.

Observation that is NOT a W7 item but will matter for G4/G9: the first paint of both fixtures reports `documentSizeChanged: true` with `documentWidthTwips: 26775` while the open reply said 26593 (182 twips, the same difference the W2 amendment records against the native oracle). The draft does not act on it, so the last ~12 CSS px of the sheet fall outside the scheduled tile columns. The final viewer has to refit after the first paint (G4 expects `documentSizeChanged == false` on the second paint).

### Not done in this draft, on purpose

Zoom, search, scroll-to-last-cell, a download/save path (read-only by construction), staging to `dist/` or any Makefile target (post-cutover, plan W9 row), a synchronous engine dispose on `pagehide` (the page calls the async `close()` best-effort; finding 024 is why a real dispose matters on Firefox), and Firefox (Chrome only, one run).

### Notes for the owner of the repo

- `.gitignore` has an allowlist and does not list `/wasm_sdk_probe/viewer-shell`; the three files there were added with `git add -f`. A new file later added to that directory will be silently ignored until `!/wasm_sdk_probe/viewer-shell` is added. I did not edit `.gitignore` (outside the new paths).
- The page's UI strings are zh-TW; the adapter's `工作表 N` default names and `PART_SWITCH_DISABLED_REASON` are zh-TW by design (they are what the user sees).

### Re-running

```
node --test wasm_sdk_probe/tests/ods-viewer-session.test.mjs
python3 findings/evidence/m4-ods/W9-viewer-draft/red-cases.py
python3 wasm_sdk_probe/tools/run_ods_viewer_draft_smoke.py --selftest
python3 wasm_sdk_probe/tools/run_ods_viewer_draft_smoke.py --check-only   # exit 3 if the machine is busy
python3 wasm_sdk_probe/tools/run_ods_viewer_draft_smoke.py                # guarded; one browser run
cd wasm_sdk_probe && python3 tools/build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v66.json   # no --write
```

## Addendum, 2026-10-20: step 0 of SPEC-M4 (the package probe and the page fixes)

Spec: `specs/SPEC-M4-ods-in-nextcloud.md` §5 (pinned in `d7ab2815`).

- **New module `viewer-shell/odf-package-probe.js`.** It reads `META-INF/manifest.xml` from the zip's central directory (stored or deflate) and reports `encryption-data`. The session asks it **before** `engineFactory`: encrypted → `ENCRYPTED_DOCUMENT`, state `refused`, no engine. A package it cannot read goes to the engine as before, with the reason in the state. Checked over the 306-file corpus with the module itself (node, 2026-10-20): 3 encrypted (exactly the three `expect: "refused"`), 303 plain, 0 unreadable, 0 mismatches.
- **Unit test: 22 tests** (18 + 4 for the probe). The close-during-open test now waits for the factory (phase 1) and the document open (phase 2) to be *called* before closing; a fixed delay landed in the new package read instead, so phase 1 no longer tested the window it names. Phase 0 (closed during the package read) is new.
- **Red cases: 35 mutations** (27 + M28–M35 for the probe and the refusal path). `red-cases.txt`: control 22/22, every mutation red in a test it names, `problems: none`.
- **Page:** one `:root` rule (`light-dark()`); the worker URL hard-coded to `./profiles/ods-viewer-v1/sdk-worker.js` as the only `workerUrl: "./…"` literal in the file (the packager's pattern; a comment containing it would count); `?profile=` dropped; `data-dev-only` on the header, the toolbar and the status line; `?diagnostics=1` records stage lines and de-duplicated engine messages per run; `record.close`.
- **Smoke runner:** `PAGE_FILES` carries the new module, and the mirror's copy of the page is retargeted to `--profile` (anchor exactly once; both hashes in the report). Self-test 20/20.
- **Shell bundle v75 unchanged:** `build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v75.json` (no `--write`) gives `5b14038e…`, `problems: []`.
