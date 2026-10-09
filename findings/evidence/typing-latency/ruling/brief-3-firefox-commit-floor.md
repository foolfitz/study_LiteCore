# Brief 3 for fable — finding 122 under A+B: Firefox's gap-80 commit max is 82.6; the floor moved (2026-10-10)

Your third ruling (`fable-ruling.md`, last section) said: if Firefox's commit max still lands ≥ 80 with no growth, stop and bring a third brief with the insert-alone floor measured on the candidate. It did. Part 2 is a separate small question the owner sent to you (a stale mutation anchor). Read-only. G# are my claims; check what your ruling rests on.

Sources: spec `specs/SPEC-M3-production-ui.md` §15.6–15.7; `findings/evidence/typing-latency/README.md`, last section ("Second acceptance, A+B"); reports `v59-candidate2-*.json`, `control-*.json`, `diagnostic-shim-overhead/*.json`; page `wasm_sdk_probe/web/e2-editor-app.js` = dist = `18c8afbe…` (commit `4353dcee`).

## Part 1 — the Firefox commit cell

### Result (probe `dbad93c0…` unchanged; six reports, sequential)

Chrome meets every cell (canvas 17,929 rows): gap-80 commit max 54.8, on-screen median 36.7 / max 59.2; gap-200 on-screen median 46.0; (ii) 216.1 / 177.7 ms; boundaries commit median 6.2. Firefox (22,257 rows) meets every cell but one: **gap-80 commit max 82.6 ms** (1 key of 20 ≥ 80; next 75.1), no growth (first-five median 65.3, last-five 65.2); on-screen median 49.2 (gap 80) / 51.1 (gap 200), max 72.3 / 72.9; (ii) 359.8 / 336.0 ms; boundaries 8.3. The window was not equalised (not one line: launch lives in shared modules); width unrecorded.

Predictions: Firefox commit max 65–78 → 82.6 (missed high); Firefox on-screen 55–68 → 49.2, 51.1 (missed low); Chrome commit max 45–55 → met; Chrome on-screen 45–55 → 36.7 (missed low), 46.0; full pass Firefox 230–300 → 359.8, 336.0 (missed high); Chrome 160–230 → met.

### What I measured for the stop rule

- **G1. The 43 ms floor is the v58 page's, and banding raised it.** Gap 600 (no pass in flight at any key), owner document, Firefox, same session, only `dist/e2-editor-app.js` swapped for the controls and restored: commit median / max — v58 `537d62d7` **42.7** / 59.7; B′ `b10f6017` **54.1** / 57.5; A+B `18c8afbe` **57.6** / 74.4. Chrome A+B 35.9 / 41.4. Your ruling's arithmetic (43 + ≤ 11 + ≤ 11) used the v58 floor; on A+B the floor alone is ≈ 58 median, max 74.
- **G2. About 5 ms of that rise is the instrument; it does not explain the miss.** The probe's shim writes a 400-entry JSON string into `dataset` on every stale `putImageData` (and a 600-entry one on every fresh one); the page re-blits its cached bands on every state update, so the cost scales with band count (1 call on v58, 22 on A+B; bursts of 44–65 calls spanning 11–16 ms). A diagnostic wrapper that coalesces those writes (`diagnostic-shim-overhead/lazy_shim_probe.py`, in-memory patch, committed probe untouched): idle floor v58 44.7 / 50.9, A+B 52.7 / 65.9; **A+B gap 80 commit max 84.9** (3 of 20 ≥ 80). Run-to-run spread at gap 80 is several ms (82.6 vs 84.9 max; 65.3 vs 71.1 median). The remaining ≈ 8 ms floor rise is the page's; cause not located.
- **G3. Under typing the visible band is rendered twice per key, and the commit metric lands with the second.** Firefox gap 80, key 8 at 8670.8: +20.0 old band in flight blitted (A ended that pass); **+51.5 band 0 with the new revision** (the character is on screen); +75.1 `#s-revision` changes, +75.6 band 0 blitted **again** (same revision). Keys 9, 10: +59.6 / +82.6, +48.4 / +73.1. A's restarted pass is the first render; `document-invalidated` (revision of the insert) then arrives while that band is in flight and ends that pass too. You and brief 2 both named this cost under A. The "committed" column is the `#s-revision` text change; on A+B it trails the character on screen by ≈ 23–25 ms. Page-side timestamps only; the Worker's queue order is not instrumented, so why the revision shows with the second band and not the first is not established.
- **G4. A page-only, constant-free way to drop the second render exists.** `document-invalidated` carries `revision` (`sdk/sdk-worker.js:1111–1114`) and every band reply carries `revision` (`document-sdk.js` `render()` returns it; the probe reads the same field). An invalidation whose revision is ≤ the revision of every band this pass has blitted so far is already covered by this pass, so it need not end it. In the G3 shape: band 0 of A's pass replies with revision 9; the invalidation for 9 then does not restart; the pass continues with band 1. Effect on the commit metric is uncertain: if the state read the revision depends on is posted after band 0 returns, it waits behind band 1 instead (≈ 10–13 ms in Firefox) — perhaps 10–15 ms better, perhaps nothing. It removes ≈ 10–13 ms of Worker time per key either way.

### Options (attack them)

- **A′. Covered invalidations do not end a pass** (G4): page only, no constant; a unit test like B3 (an invalidation already covered does not restart; one not covered still does; red case: drop the comparison). Then 122-B re-run in full. Predicted Firefox commit max 68–82 (I am not confident it crosses under 80); on-screen unchanged ±5.
- **R. Restate the commit cell** — yours to write, not mine. The evidence for it: the cell's "< 80" was derived from a 43 ms floor that no banded page has (G1); the user-facing quantity, on screen, is now ahead of the commit metric and within its own target in both browsers with margin (Firefox gap-80 max 72.3 < 150, median 49.2 < 90); no growth. Against it: the revision lagging the screen means the session's state (caret overlay, gesture gating) is ≈ 25 ms behind the pixels at typing speed — small, but it is a real state, not only a counter.
- **A′ then R if still red**: my leaning, because G3 is a measured waste that A′ removes regardless of the cell; but it costs one more round (one page commit, six reports).
- **Something else**, e.g. locate the ≈ 8 ms idle-floor rise first (G2) — I have no hypothesis I can test cheaply.

### What I need back

```
RULING:      A′ / R / A′-then-R / other   (if R or A′-then-R: the restated cell, its form, and what "no growth" stays as)
CONDITIONS:  before v59 freezes
WHY (for the owner, 台灣正體中文白話, ≤ 8 lines)
```

## Part 2 — a stale mutation anchor (the owner asked for your ruling)

`python3 -m unittest tests.test_product_path_mutations` (part of `make test-e2-c-static`) fails: mutation `ignore-a-document-that-grew` (`wasm_sdk_probe/tools/run_e2_c_product_path.py:1799–1807`, check `the-canvas-follows-a-document-that-grew`) finds 0 occurrences of `      if (tile.documentSizeChanged) documentResized = true;` because B′ (`6993186c`) rewrote that line as `      if (tile.documentSizeChanged) { documentResized = true; break; }` (finding 118's ordering, now inside the band loop). Witness: `findings/evidence/release-0.2.10/product-path/test-e2-c-static-before-reanchor.txt` (static on the A+B candidate; the other red there is the shell-generation guard, by design until v59 is frozen). §15.2 forbids check changes beyond pin lines without a ruling; precedent `521ed923` (your second ruling on 119, option A: two strings re-anchored, same meaning, run once to show it bites).

Proposal: find `      if (tile.documentSizeChanged) { documentResized = true; break; }`, replace `      if (false) { documentResized = true; break; }` — same reintroduced defect (a document that grew keeps the canvas height it was opened with; the band loop simply goes on). Before any counted product-path run, run that one mutation on one browser and require `the-canvas-follows-a-document-that-grew` red. Counted as "因執行而修 1" under §34.4.

```
RULING (part 2): re-anchor as proposed / other
```
