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
