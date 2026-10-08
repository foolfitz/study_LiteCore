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

## Results (2026-10-09, `browser/chrome.json`, `browser/firefox.json`; Chrome 151.0.7922.169, Firefox 157.0; page `e00ab76a…`; probe at `89793022`)

`browser/smoke-chrome.json` is the instrument check (1 trial per cell) run before them; it is not part of the counts. The real gaps come from the page's own keydown times.

| Nominal gap | Real keydown gaps (X→Y, Y→key) | Chrome Backspace | Chrome Enter | Firefox Backspace | Firefox Enter |
|---|---|---|---|---|---|
| 0 ms | 3–6 ms, 0.5–7 ms | **5/10 overtaken** | **2/10 overtaken** | **9/10 overtaken** | **10/10 overtaken** |
| 10 ms | 13.6–15 ms, 13–20 ms | 0/10 | 0/10 | 0/10 | 0/10 |
| 20 ms | 23–25 ms | 0/10 | 0/10 | 0/10 | 0/10 |
| 40 ms | 43–49 ms | 0/10 | 0/10 | 0/10 | 0/10 |
| 80 ms | 83–90 ms | 0/10 | 0/10 | 0/10 | 0/10 |
| 160 ms | 163–169 ms | 0/10 | 0/10 | 0/10 | 0/10 |

Every overtaken trial is `overtaken-1` (the key landed between X and Y); no `overtaken-2`, no `other`, no `no-save`, no runner error (240 trials).

Against the predictions: **0 ms hit on Firefox, half on Chrome; 10 and 20 ms miss (predicted ≥ 7/10, measured 0/10); 40 ms miss (predicted mixed, 0/10); 80 and 160 ms hit.** What happened is the uncertainty written in advance: one character's commit L on this small document is far below 40 ms — under the model (overtaken when 2 × gap < L), below about 28 ms, since a 14 ms gap never overtakes. The pre-written rule for this outcome: "it lives in key rollover and fast bursts; still a fix, ranked behind data-loss items".

Not measured here: L on a large document (the fixture is 27 short paragraphs; the owner's 563 KB document may commit a character more slowly, which would widen the window toward ordinary fast typing), and Ctrl+S / arrows / format keys (same path by the source, not run).
