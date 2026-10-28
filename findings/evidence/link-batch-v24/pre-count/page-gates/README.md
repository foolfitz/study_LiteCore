# v24 page gates: (vi) stale wasm at init, (vii) page refusal without the typed-insert leaf

Spec `specs/SPEC-M3-link-batch-v24.md` §6.3 rows (vi) and (vii); fable ruling 2 (c), (d) and follow-up A2 (`findings/evidence/link-batch-v23/feature-protocol/s5-type-route-ruling/RULING-2-abi.md`). Runner `wasm_sdk_probe/tools/run_v24_page_gates.py` (new file). This section was written and committed before the first run.

## What is served

A symlink mirror of `wasm_sdk_probe/dist/` per arm (`run_e2_c_product_path.build_mirror`; dist is never written). The page is the cutover page as served from dist (`e2-editor-app.js` `b15a6d8e…`, SDK `afdff2d4…`), unmodified; the HTML gets one observer `<script>` before the page module (wraps `Worker`, records every request/response/event/worker error and the trusted key, beforeinput and pointerdown events; pixel buffers become their length). Exactly one profile file set differs per arm; the runner checks the v24 profile in dist against the archive's `SHA256SUMS` and the v23 files against theirs before any browser starts. Both browsers, one page load per arm and browser, nothing retried.

## Arms and what counts

| Arm | Served under `profiles/e2-editor-v24/` | Expected | Verdict rule |
|---|---|---|---|
| `control` | everything as linked; the manifest materialised byte-identical | init ok, open ok; a real click on the paper and a real `x`: the first `insertText` request carries `route: "uno-insert-text"`; its reply `ok`, `method: "uno-insert-text"`, `completion: "uno-command-result"` | PASS only if all of that holds. The positive control of both (vi) and (vii) |
| `vii-leafless` | the v24 manifest with the one line `"typedInsert": …` removed (the runner checks the parsed result equals the original minus that key) | page refuses on the `PAGE_BUILD_MISMATCH` path (`#expired` shown, pill `expired`); zero `insertText` requests in the whole window | PASS only if refused and zero `insertText` requests across the window below |
| `vi-stale-pair` | the archived v23 `probe.wasm` **and** `probe.js` (`build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/`) beside the v24 manifest and worker | the init reply is `ok: false`, `code: "DECLARED_EXPORT_MISSING"`; no `WORKER_EXCEPTION`; zero `insertText` requests | PASS only if the init codes are exactly `["DECLARED_EXPORT_MISSING"]` and the other two hold. This is the (vi) verdict |
| `vi-stale-wasm-only` | only `probe.wasm` is v23's; the loader stays v24's | recorded, no verdict | see below |

**The window** in `vii-leafless` and both `vi` arms runs from page load through three typing attempts made after the page settled: (a) a real `x` wherever the page left focus; (b) a real click where the paper was, then `x`; (c) `#sink.focus()` by script, then `x`. (a) and (b) are what a user can do; (c) is not a user path (the sink is inside `#paper`, which `showExpired` sets to `display: none`) and is there to see whether anything below the page still accepts a typed character. The handoff noted that `showExpired` does not detach the input adapter; (c) is the measurement of whether that matters. A non-zero count from any of the three is a FAIL of the arm.

**Why the stale arm swaps the loader too.** Emscripten emits `probe.js` and `probe.wasm` from one link, and the loader binds the wasm's exports by their minified names (the v24 loader assigns `Module["_oxsdk_document_insert_typed_text"] = wasmExports["Ya"]`), so a v23 wasm under the v24 loader is not a stale build but an incoherent pair. The hazard ruling 2 names — a stale engine beside a fresh manifest — is the previous link's pair under the new manifest, which is `vi-stale-pair`. The literal reading (wasm only) runs too, as `vi-stale-wasm-only`, so the record shows what it does; it is not the (vi) verdict either way.

## Defaults (spec §6.3)

- (vi) not run, red, or NE: the stale-wasm hazard is open on v24; v24 is not bound.
- (vii) not run, red, or its positive control not holding: v24 is not bound; a control that does not hold makes the arm NE (nothing was measured).

## Run 01 (2026-10-28 11:13–11:22 +0800) — results

`run-01/` (`report.json` + one file per browser and arm; the mirrors, 225 MB with two copies of the v23 wasm, were deleted after the run — every overridden file's SHA-256 is in each cell's `mirrorOverrides`). Pre-run: KWallet unlocked, no refusal, foreign CPU ok, load 0.63; no lagging shell file.

| Arm | Chrome | Firefox | What was observed |
|---|---|---|---|
| `control` | PASS | PASS | trusted click on the canvas → `editorPlaceCaretV2`; trusted `x` → keydown+beforeinput on `#sink` → one `insertText` with payload `{documentHandle: 1, text: "x", route: "uno-insert-text"}`; reply `ok`, `method: "uno-insert-text"`, `completion: "uno-command-result"`, `resultPayload` = the raw `.uno:InsertText` result (`success: false`, `wasModified: false`, as M1 measured natively) |
| `vii-leafless` | PASS | PASS | init and open ok (4 requests: init, open, pageRectangles, editorGetStateV2), then `#expired` shown, `#paper` `display: none`, pill `expired`; all three typing attempts delivered a trusted `keydown` (target `BODY`); `#sink.focus()` by script left `document.activeElement` on `BODY` (the sink is inside the hidden paper); **0 `insertText` requests** |
| `vi-stale-pair` | **PASS** | **PASS** | the only request is `init`; reply `ok: false`, `code: "DECLARED_EXPORT_MISSING"`, message `profile e2-editor-v24 declares typedInsert: "document-sdk-insert-typed-text" but this binary has no oxsdk_document_insert_typed_text`; no `WORKER_EXCEPTION`; 0 `insertText` (the script-focused sink did take a `beforeinput`, with no document to send it to) |
| `vi-stale-wasm-only` | RECORDED | RECORDED | refused at init with `INCOMPATIBLE_ABI`: `editor ABI 1 in this binary does not match 6` — the v24 loader called the v23 wasm through v24's minified export names, so `oxsdk_editor_abi_version` reached some other function and returned 1. Refused at init, by the wrong check for the wrong reason, which is the incoherent-pair point above made concrete |

**(vi) holds and (vii) holds** in both browsers, each with its positive control.

Observation outside both rules (no verdict here; triage later): in `vii-leafless`, the state pill read `expired` when the refusal settled and `ready` on every later snapshot, while `#expired` stayed shown and `#paper` hidden. Something after `showExpired` (the session's state callback, `web/e2-editor-app.js:979`, by reading only) repaints the pill. The same path runs on a wrong wasm, so this is not v24-specific.
