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

## Second run: the owner's document (predictions written 2026-10-09 before it ran)

Why: the window is set by one character's commit time L, and the first run's fixture is tiny. On the owner's 563 KB document the M3 runs show a mid-text Backspace at 101–105 ms against 43–78 ms on the fixture, so L there is likely about twice as long. Same probe with `--document owner` (this commit): click at the end of the heading 「一、序言」 (X6's v19 click), End, then the same bursts; the report keeps only the first paragraph (and the key's own new paragraph). Same gaps, 10 trials per cell, both browsers.

| Nominal gap | Prediction, both browsers |
|---|---|
| 0 ms | overtaken in most trials |
| 10 ms | overtaken in some trials (L × 2 on this document puts the edge near 14–28 ms real gaps) |
| 20 ms | rare |
| 40, 80, 160 ms | 0 |

What it changes: overtaking at 20 ms or more (keydown-to-keydown ≈ 24 ms, which is key rollover in ordinary fast typing) makes 111 an everyday bug on real documents; 0 at 10 ms and up keeps it where the first run put it.

## Second run: results (2026-10-09, `browser/owner-chrome.json`, `browser/owner-firefox.json`; `browser/smoke-owner-chrome.json` is the instrument check)

| Nominal gap (real) | Chrome Backspace | Chrome Enter | Firefox Backspace | Firefox Enter |
|---|---|---|---|---|
| 0 ms (≈ 4, ≈ 1 ms) | 5/5 overtaken | 5/5 overtaken | 10/10 overtaken | 10/10 overtaken |
| 10 ms (≈ 14 ms) | 1/5 overtaken | 0/5 | **10/10 overtaken** | **10/10 overtaken** |
| 20, 40, 80, 160 ms | 0/5 each | 0/5 each | 0/10 each | 0/10 each |

**Chrome counts only its first five rounds.** In round 6 the Backspace at 0 ms did not overtake and did not delete: it failed (`⌫ 刪除 失敗`, `EDITOR_STATE_UNAVAILABLE：selection text became visible without its required typed callback`) and nothing was saved; in every one of the 59 trials after it in that page the typed keys never reached the document (revision 0 → 0, the saved file unchanged), although each trial opened its document (「已開啟」) and placed its caret (in about 0.9 s instead of 0.2 s). Those 59 are not 111 data. The failure is followed up on its own (`../fast-delete-recovery/`).

Against the predictions: 0 ms hit; 10 ms "some" — Firefox overtook every time, Chrome once in five; 20 ms "rare" — none; 40 ms and up hit. On the owner's document the edge sits between a 14 ms and a 24 ms keydown-to-keydown gap; on the small fixture it sat below 14 ms. The rule written before the run ("20 ms or more makes it everyday") is not met: 111 is a bug of near-simultaneous keys (key rollover, a key pressed with the last letter), whose window grows with the document.

## After the fix (F111-B, `SPEC-M3-production-ui` §14.2; 2026-10-09)

Candidate `dist/` with finding 111's fix (page `537d62d7…`, session `62a2a20e…`, not yet frozen), same probe, `--gaps 0,10 --keys Backspace,Enter --repeats 10`, both documents, both browsers (`browser/fixed-{boundaries,owner}-{chrome,firefox}.json`): **every cell 10/10 `ok`** — 160 trials, 0 overtaken, 0 `other`, 0 `no-save`; real keydown gaps as in the runs before the fix (≈ 1–6 ms and ≈ 14 ms). Prediction (§14.3: 0 overtaken in every cell) hit. The reading rule's red case: `browser/firefox.json` and `browser/owner-firefox.json`, the unfixed page, have 19 and 20 overtaken trials at 0 ms — the same rule reads them FAIL.
