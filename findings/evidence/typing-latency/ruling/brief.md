# Brief for fable — finding 122 (typing falls behind on a large document): which fix, and what ships with it (2026-10-10)

You are ruling on the owner's behalf; the owner is awake this time and asked for your ruling explicitly ("發給 fable 裁決"). Repository /home/jiajun/LibreOffice/study_LiteCore (product code under wasm_sdk_probe/). Read-only. F# are my claims and may be wrong; check what your ruling rests on.

## Where things stand

R′ holds on host 0.2.9 (shell v58, page 537d62d7…; `findings/evidence/m3-production-ui/RESULT-0.2.9.md`); 119 and 111 are fixed. The owner hand-tested 0.2.9: groups 1–5 of my test plan passed, and they reported two things: (1) select text, press Backspace/Delete → error (now finding 121: the page sends `delete-backward`/`delete-forward`, offered for `collapsed` only; v19 offers `delete-selection` for ranges and the page's cut already uses it; reproduced both browsers, also on v57's page; `findings/121-*.md`, `findings/evidence/121/`); (2) "打字到文字出現在段落中，有點慢" (now finding 122). Also open: finding 120 (standalone page only: after a stopped session, opening another file via the file input leaves `#sink.disabled`; one-line page fix proposed; `findings/120-*.md`).

## Finding 122, measured (`findings/evidence/typing-latency/README.md`, exploratory: no prediction was written before these runs)

- 200 ms between keys: key → on screen ≈ 9 ms (small fixture, Chrome), ≈ 40 ms (owner's 563 KB document, Chrome), ≈ 46 ms (Firefox). No backlog.
- 80 ms between keys, owner's document, Chrome, 20 chars: each char commits ≈ 120 ms after the previous one, so the backlog grows ≈ 40 ms per key; the 20th char appears 862 ms after its key.

- F1. `renderDocument` (`web/e2-editor-app.js` ~:803–905) re-renders the whole canvas every time, and the canvas is the whole document (`layoutCanvas` ~:773: height = width × document ratio; the owner's document ≈ 900 × 22,256 device px, i.e. one strip of ≈ 80 MB RGBA per repaint, `MAX_TILE_HEIGHT` 32767).
- F2. Every change triggers it: the session's `onEvent` queues `renderDocument` on `document-invalidated` (`openDocument` ~:2050), and `run()` repaints after every action. It already coalesces repaints requested while one is in flight (`rendering` / `renderAgain`, ~:807, ~:902).
- F3. The repaint and the next character's insert go through the same document Worker, so the next insert waits behind a whole-document render (inference from F1/F2 and the 120 ms cycle ≈ 35 ms commit + ≈ 85 ms render; not instrumented on the Worker side).
- F4. `sdk/sdk-worker.js` ~:1111 posts `document-invalidated` with only `documentHandle` and `revision`; the rectangle LOK reports with its invalidate callback is dropped. The worker is part of the profile's identity (v19's worker `00882139…` is bound), so changing it means a new profile (repackage, no relink), a cutover and a re-validation round.

## Options (attack them)

- **A. Throttle repaints (page only).** My first idea was "don't repaint while the input adapter still holds characters" — but at 80 ms between keys with ≈ 35 ms inserts the adapter queue is usually EMPTY between keys, so that rule would rarely fire and the backlog would stay. What would work is a throttle: at most one repaint per T ms while edits keep coming (e.g. T = 250 ms: ≈ 85 ms of render per 250 ms + ≈ 35 ms per 80 ms of inserts ≈ 0.78 utilisation, no backlog; characters appear in chunks every ~250 ms). A debounce (repaint only after a pause) would show nothing during a burst — worse.
- **B. Repaint only what is visible (page only).** Render the strips intersecting the viewport (+ margin) and mark the rest stale by revision; re-render stale strips when they scroll into view. ≈ 10–20× cheaper per repaint on the owner's document. Larger change, near findings 062 (tile limit, strips) and 118 (height change) territory.
- **C. Repaint only the invalidated rectangle (worker + page).** Forward LOK's rectangle in `document-invalidated` and re-render only that band. The real fix; costs a new profile identity, cutover and re-validation.
- My leaning: A now, in one page release (shell v59, host 0.2.10) with 121's fix (`delete-selection` for a range in the `beforeinput` handler) and 120's one line; B or C registered. Verification for A: the same probe, owner's document, both browsers, 80 ms × 20 chars: the 20th char on screen < 300 ms after its key (and the 200 ms run not worse than today); unit tests for the throttle; the M3 recount and product-path net as in R′.

## What I need back

```
RULING:      for 122 (A/B/C/other, with T if A), and what ships together in the next release (121, 120)
WHY (for the owner, 台灣正體中文白話, ≤ 10 lines)
FACT CHECK:  which F# you checked; any that are wrong
CONDITIONS:  criteria to write before any run (unit and browser, with numbers), the release steps, anything I must not do
```
