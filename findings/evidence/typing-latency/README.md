# Typing latency on the shipped page (2026-10-09; finding 122)

The owner, hand-testing host 0.2.9: "打字到文字出現在段落中，有點慢". Probe `wasm_sdk_probe/tools/probe_typing_latency.py` (shipped standalone page from `dist/`, page `537d62d7…`; the served HTML gets a pre-module script that timestamps every `putImageData`; real keys; per character: keydown → the page's revision showing it committed, and → the first blit after that). Measured before any prediction was written — an exploratory measurement, not a judged one. The first version matched revisions wrongly (the page rewrites `#s-revision` on every state update, so the first write after a key was a repeat); fixed to wait for `start + i + 1` before any of the reports below.

| Report | Browser | Document | Gap | Key → committed (median, max) | Key → on screen (median, max) |
|---|---|---|---|---|---|
| `chrome-boundaries-gap200.json` | Chrome 151 | boundaries (27 short paragraphs) | 200 ms, 6 chars | 6.3, 17.1 ms | 9.1, 22.9 ms |
| `chrome-owner-gap200.json` | Chrome 151 | the owner's 563 KB document | 200 ms, 10 chars | 35.4, 37.4 ms | 39.4, 41.3 ms |
| `firefox-owner-gap200.json` | Firefox 157 | the owner's document | 200 ms, 10 chars | 44.9, 48.5 ms | 45.7, 49.3 ms |
| `chrome-owner-gap80.json` | Chrome 151 | the owner's document | 80 ms, 20 chars | 348.5, 774.9 ms | 348.7, **862.4** ms |

At 80 ms between keys the lag GROWS: character i commits about 120 ms after character i−1 (revisions 1 → 2 → 3 … at 38, 202, 333, 455, 577 … ms), so every key adds ~40 ms of backlog — 20 characters end ~0.8 s behind. At 200 ms between keys there is no backlog.

Why, read from the source: `renderDocument` (`web/e2-editor-app.js` ~:803) re-renders the WHOLE canvas, which is the whole document (the owner's ~22 pages), strip by strip through the document Worker, after every change (`document-invalidated` → `renderDocument`). The next character's insert waits in the same Worker behind that repaint. The Worker's `document-invalidated` event carries only the handle and revision (`sdk/sdk-worker.js` ~:1111), not the invalidated rectangle LOK reported, so the page cannot repaint only what changed.
