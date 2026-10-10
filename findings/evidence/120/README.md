# Finding 120 — evidence (2026-10-09)

- **Seen first** in finding 111's owner-document run (`../111/browser/owner-chrome.json`): after the delete failed in round 6 the page sat in `recoverable-error`; the probe then opened every later trial's document through the page's file input, and in all 59 of them the typed keys never reached the document (revision 0 → 0) while the caret placement still worked.
- **Half one, measured**: at the moment a session blocks, the input sink is disabled — `../fast-delete-recovery/chrome-same-page-1.json` attempt 41, the notice read right after the failure: `"sinkDisabled": true`.
- **Half two, measured** (`sink_probe.py`, `sink-chrome.json`, `sink-firefox.json`; the shipped standalone page from `dist/`, page `537d62d7…`; a browser per arm): the control arm opens two documents through the file input, clicks, types `Q` → sink enabled and focused, revision 0 → 1. The residue arm sets `#sink.disabled = true` before the second open (the state a blocked session leaves) → after the open and the click the sink is still disabled and unfocused, and `Q` does not land (revision 0 → 0). Both browsers alike.
- **Read from the source**: `input/input-adapter.js` `setBlocked` writes `target.disabled`; `detach()` removes the listeners but never re-enables the target; `attach()` does not sync `disabled`; a new session calls `setBlocked(false)` inside `_openFresh`, before the page attaches the sink (`web/e2-editor-app.js` `openDocument`: `session.open()` then `session.attachInput(el.sink)`), so it cannot reach the element.
- The first `sink_probe.py` version ran both arms in one Chrome and hung for 180 s on the page's own leave prompt (the control arm's unsaved `Q`); Firefox's driver accepts that prompt. Fixed by a browser per arm (handoff rule jj).

## 120-B on the candidate dist/ (2026-10-10; spec §15.2; page `b10f6017f36582d9…`, the probe unchanged)

`v59-candidate-sink-{chrome,firefox}.json`: the residue arm's sink was disabled before the second open and is enabled and focused after the open and the click; `Q` lands (revision 0 → 1), as in the control arm. The red case is `sink-*.json` (residue: disabled, 0 → 0). 120-B met in both browsers.

## 120-B on the final v59 page bytes (2026-10-10; page `18c8afbe…`, A+B; fable's fourth ruling condition 4)

`v59-candidate2-sink-{chrome,firefox}.json` (binding: `v59-candidate2-binding.txt`, dist `18c8afbe…` before and after): residue arm disabled before the second open, enabled and focused after it, `Q` lands (0 → 1), like the control arm. Identical to the `b10f6017…` reports. 120-B met in both browsers on the final bytes.

## 120-B on the release-P page bytes (2026-10-10; page `36c2b18b…`; spec §16.2 P4)

`p-candidate-sink-{chrome,firefox}.json` (binding `p-candidate-binding.txt`, dist `36c2b18b…` before and after): identical to the `v59-candidate2-*` reports (no field differs). 120-B still met in both browsers.
