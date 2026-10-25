# Isolated C2 record preparation

Source preparation only. The initial eight slots are uncounted observations: actual frozen v22 and diagnostic r2, Chrome and Firefox, gap80ms×20 keys and gap200ms×10 keys. A repeat population or N3 comparison is not declared here. The already required diagnostic cohorts take priority. There is no historical C2 numeric gate, no performance PASS, and no claim that this isolates stack-overflow-check cost.

`tools/record_v23_c2.py` reuses `probe_typing_latency_view.py` over `probe_typing_latency.py` without editing either. It fixes the existing view arguments to1400×1000 CSS pixels, devicePixelRatio2, and the existing owner fixture. PMPC指南.odt is pinned to SHA256 `7b336879547df057ae6d38e907f221b40c90c37cd65d2df5afceceb91941657e`,563149bytes. The unchanged probe still owns the click/End positioning, real CDP/WebDriver keys, revision mapping and first fresh ImageData blit logic. It still distinguishes fresh rendered text from cached overlay blits. The wrapper neither substitutes SDK commit time nor changes the historical probe's caret-line estimator.

The wrapper creates an owned mirror and materializes only its e2-editor-app.js. It requires exactly one existing workerUrl declaration, preserves it byte-for-byte for v22 and replaces only that URL for r2. Both profiles otherwise use the same product source/import graph. The original page bytes, exact substitution, copied/source hashes and full local served imports are recorded. The unchanged probe then creates its own executed mirror and adds its existing paint shim; the wrapper verifies that resulting graph exactly equals the declared unchanged-shim composition, archives that mirror and cleans up the owned temporary root. Dist, product source, SDK and frozen profiles are never edited.

A navigation wrapper records actual browser userAgent, innerWidth/innerHeight/devicePixelRatio and browser-fetched manifest/WASM/loader/worker SHA256 before the unchanged measurement begins. Those hashes must match the pinned frozen profile. Fetching the identity bytes is an explicit preparation action on both profiles; it is not included as a measured open-time result. The actual original probe reports, raw keys/revisions/fresh blits and summary are retained alongside binding.json. Missing readiness, missing metrics or wrong identity/geometry produce NOT_ESTABLISHED; there is no product workaround or changed performance threshold. RECORDED means the requested samples exist with matching provenance, not that performance is acceptable.

The wrapper holds the shared browser lock and uses the existing foreign-CPU guard. Existing probe cleanup runs normally; a final owned-process cleanup also handles the specific isolated browser and local server if the probe exits exceptionally. No host, service configuration, live document or build operation is performed.

From `wasm_sdk_probe`, an example single slot, only after coordination:

```sh
python3 -I tools/record_v23_c2.py --profile e2-editor-v23-diag-r2 --browser chrome --gap 80 --output ../findings/evidence/link-batch-v23/post-link/r2-attempt-01/c2-prep/r2-chrome-gap80
```

`--gap 80` fixes20 keys; `--gap 200` fixes10. Choose `e2-editor-v22` or `e2-editor-v23-diag-r2`, `chrome` or `firefox`; each fresh invocation owns a separate output directory. Add `--prepare-only` to bind the owned mirror without starting a browser or server. No runtime invocation was performed while introducing this wrapper. Pure tests cover the exact one-URL patch, duplicate/missing-source rejection, actual-observation identity/browser/geometry negatives, the pinned owner fixture and source-graph non-vacuity.
