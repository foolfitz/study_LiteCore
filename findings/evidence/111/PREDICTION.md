# Finding 111 in a browser — predictions (written 2026-10-09, before the probe ran)

Finding 111 was read from the source and reproduced only in a unit test (2026-10-06). Its own next step: measure in a browser with real keys, sweeping the gap between keys, before choosing a fix. Probe: `wasm_sdk_probe/tools/probe_111_overtake.py` (this commit). It changes no product byte: the shipped standalone page from `dist/` (page `e00ab76a…`, v19), a symlink mirror plus one fixture, `boundaries.odt`.

One trial: open the fixture fresh, click at the end of the first paragraph ("M01 plain alpha") and press End, wait for idle; then real keys `X`, gap, `Y`, gap, KEY (Backspace or Enter); wait for idle; save with the product's button (captured); classify the saved first paragraphs (`ok`, `overtaken-1` = the key landed between X and Y, `overtaken-2` = before both, `other`). Gaps 0, 10, 20, 40, 80, 160 ms, 10 trials per key and gap, interleaved; Chrome (CDP, the gap slept in Python between keys) and Firefox (one WebDriver action chain with pauses). The page's own keydown times are recorded, so the real gaps are in the report.

## The model the predictions come from (read from the source, not measured)

X goes into the adapter and is sent at once; Y, arriving while X's commit is in flight, waits in the adapter until X completes; the key goes straight into the session queue. So the key overtakes Y when it arrives before X's commit completes: about **2 × gap < L**, where L is one character's commit time (page → worker → engine → reply). L on v19 is not measured; the M3 runs show a mid-text Backspace at 90–132 ms and a typed character at roughly the same order.

## Predictions

| Gap | Backspace and Enter, both browsers |
|---|---|
| 0, 10, 20 ms | overtaken (`overtaken-1`) in most trials, ≥ 7 of 10 |
| 40 ms | mixed |
| 80 ms | rare, ≤ 2 of 10 |
| 160 ms | never, 0 of 10 |

`overtaken-2` rare or absent (X's beforeinput reaches the adapter, and its commit is queued, before the next key's task runs). `other` and `no-save`: 0. Enter behaves like Backspace (same path: keydown → `editorAction` → session queue).

Uncertain, said in advance: Chrome's CDP dispatch adds a few ms per event, so its "0 ms" is not zero; Firefox's pauses are the driver's. If L is far below 40 ms, the edge moves down to 0–10 ms and the bug only exists for key rollover.

## What would change the decision

- Overtaking at 80 ms or more (ordinary typing speed): 111 is an everyday bug; its fix comes before other open work.
- Overtaking only at 0–10 ms: it lives in key rollover and fast bursts; still a fix, ranked behind data-loss items.
- No overtaking at any gap: the unit-test mechanism does not occur in the browser (something serialises the two paths); 111's status changes to "not reproduced in the browser" and the reason gets looked for before any fix.

## Results

(appended after the run)
