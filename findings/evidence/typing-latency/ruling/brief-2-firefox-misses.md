# Brief 2 for fable — finding 122 under B′: Firefox misses three cells (2026-10-10)

You ruled B′ (`fable-ruling.md`). I implemented it as written (`6993186c`, page `b10f6017…`; spec §15.1–15.4) and ran 122-B on the candidate dist/ (`606a8e2b`; spec §15.5; `README.md` last section; six `v59-candidate-*.json`). Read-only. F# are my claims; check what your ruling rests on.

## Result

Chrome meets every 122-B cell (on-screen median 145.7 → 50.9 ms at gap 200, 611.0 → 62.3 ms at gap 80; no backlog; whole canvas current 158.8 / 187.9 ms). Firefox misses three: gap-80 commit max 93.4 ms (criterion < 80); gap-200 on-screen median 99.8 ms (< 90); whole canvas current after the last key 267.5 / 280.0 ms (≤ 200). The C trigger (visible band > 40 ms) is not met: on-screen − commit ≈ 8–18 ms.

## Reading (from `raw.blits`, not instrumented in the Worker)

- F1. Firefox's canvas here is 22,257 rows = 11 bands (Chrome's window gives 17,929 = 9). Fresh band blits arrive every ≈ 18–20 ms in Firefox (≈ 12–16 Chrome), so a quiet full pass is ≈ 210–250 ms in Firefox. A key at gap 200 usually lands inside a pass; Chrome usually finishes before the next key.
- F2. Per key in Firefox: (1) the insert waits for the band in flight (≈ 20 ms); (2) when that band returns the page, not yet told of the change, posts the next band of the OLD pass (distance order, off-screen); the Worker runs the insert first, so that band's reply already carries the new revision — but it is not the caret's band (≈ 30 ms wasted); (3) the session's post-commit state read queues behind that band, so the page's revision shows late; (4) only after `document-invalidated` reaches the page does the next pass start with the visible band. Example (gap 200, key at 8225.7): +22.5 band 16376 old rev; +61.0 band 18423 NEW rev (off-screen); +78.9 page revision; +87.4 band 0 (caret). Gap 80 same shape.
- F3. Firefox's insert alone is ≈ 43 ms median (old page, gap 200, nothing in flight), so commit < 80 leaves ≈ 37 ms for the in-flight wait + anything queued ahead of the state read.
- F4. A quiet Firefox pass alone is ≈ 210+ ms, so "whole canvas current ≤ 200 ms after the last key" cannot be met in Firefox under B′ at this band cost unless each band gets cheaper — whatever the ordering.

## Options (page only, no throttle/debounce constant; attack them)

- **A. Edit intent ends the pass.** A listener on the sink's `beforeinput` (any input type; the page already has one for deletes) sets `renderAgain` when a pass is running. The band in flight becomes the last of the old pass; the next pass starts with the visible band, posted after the insert (the adapter posts on the input event, before that band's reply arrives). Removes F2(2). A key that changes nothing just restarts a pass (all bands still covered once quiet). Cost: when `document-invalidated` then arrives the visible band may be rendered twice (≈ 10–15 ms of Worker time). Predicted Firefox: on-screen median ≈ 60–75 ms at gap 200; commit max still ≈ 43 + in-flight + visible band → likely still ≥ 80 at gap 80.
- **B. Halve the band**: `MAX_TILE_HEIGHT / 32` (≈ 1023 rows; still derived, so the one-tile mutation still bites). Halves the in-flight wait and any wasted band; more requests per pass (per-band overhead unmeasured) → the full pass gets no shorter, maybe longer.
- **A + B** together: my leaning. Predicted Firefox commit max ≈ 43 + ≤ 12 + ≤ 12 ≈ 65–75; on-screen median ≈ 55–70.
- **For the whole-canvas cell** (F4): (i) keep it — then Firefox fails it under B′ and it forces C (relink queue `queue-f122-forward-the-invalidated-rectangle`) before 122 can close in Firefox; (ii) restate it per instance, without time: "once the keys stop, the next pass completes and every band carries the last revision" (the property your "Must not … leave any band stale once the page is quiet" protects), keeping the time as a measured, registered number; (iii) something else. Your text said 122 cannot be fixed without the gap-80 backlog cell and the gap-200 on-screen cell green in both browsers; it did not say what the whole-canvas cell gates.

## What I need back

```
RULING:      A / B / A+B / other — and the whole-canvas cell: (i) / (ii) / other
CONDITIONS:  what must hold before v59 freezes (incl. whether 122-B is re-run in full or only Firefox)
WHY (for the owner, 台灣正體中文白話, ≤ 8 lines)
```
