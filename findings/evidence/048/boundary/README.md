# Finding 048 — the wait is on the engine's side of the worker boundary

Criteria in `PREDICTION.md`, registered before the harness existed.  Judged by
`tools/analyze_f048_boundary.py`; self-test 9/9.

Two recorded rounds (Chrome, Firefox) on the **frozen `e2-editor-v2`**, on the
same document the 22–28 ms was measured on.  **Nothing was modified**: the
shipped worker forwards LOK callback ids 0 and 1 unconditionally, so a page can
see the invalidation without a debug mode or a diagnostic profile.

## The split

| | Chrome | Firefox |
|---|---|---|
| transport floor (`getState` round trip, median of 40) | **1.02 ms** | **0.88 ms** |
| the click's own round trip (`t0 → promise resolves`) | **0.34 ms** | **0.45 ms** |
| engine side (`promise resolves → invalidation arrives`) | **35.1 ms** | **35.0 ms** |
| total | 35.7 ms | 35.4 ms |
| engine side's share of the total | **99.0 %** | **98.8 %** |

10 of 10 clicks usable in both browsers; none excluded.

All five predictions **held**.  The conclusion the round is allowed to reach:
**`ENGINE-SIDE-OF-THE-WORKER-BOUNDARY`** — our transport and our worker
scheduling are not where the wait is.  Posting the mouse event costs less than
the idle round-trip floor.

## What this round may not conclude, and does not

**Which layer on that side.**  Core's own click handling measures 0.6 ms
natively, so subtracting leaves ~34 ms unaccounted for — and a residue is not an
attribution.  Finding 040 is the standing precedent: a condition an Emscripten
build never sets, attributed to the wrong layer for weeks.  The next controlled
variable is an engine-side timestamp, and that needs a diagnostic build.

## Two limits of the measurement, stated rather than discovered later

1. **The invalidation is not necessarily the cursor's.**  The shipped worker
   collapses LOK callback ids 0 (`INVALIDATE_TILES`) and 1
   (`INVALIDATE_VISIBLE_CURSOR`) into one `document-invalidated` event, so the
   first arrival after a click could be either.  It does not move the
   conclusion — both are emitted from the engine's side — but "the cursor
   callback took 35 ms" is more than this round measured.
2. **35 ms is not the D3 probe's 22–28 ms.**  Different endpoint (first
   invalidation, versus the caret reading back on the new line) and a different
   position in the document.  The registered band was 15–40 ms for that reason,
   and both rounds land in it.  The two numbers are of the same phenomenon, not
   of the same interval.

## Reproducing

```
python3 tools/run_e2_c_d0.py --browser chrome \
  --page e2-c-048-boundary.html --namespace __f048_boundary --output <new dir>
python3 tools/analyze_f048_boundary.py <run dirs> --output verdict.json
python3 tools/analyze_f048_boundary.py --self-test <run dirs>
```
