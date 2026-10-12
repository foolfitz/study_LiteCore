# Finding 121 — evidence (2026-10-09)

Reported by the owner from the hand test of host 0.2.9 ("如果把文字反白再按 backspace 或 delete，會報錯"), reproduced with `select_delete_probe.py` (standalone page from `dist/`, `boundaries.odt`, a drag through the page's own pointer handler across "plain" in "M01 plain alpha", then one real key):

| Report | Page | Key | Selection shape before | Result |
|---|---|---|---|---|
| `chrome-backspace-v58-page.json` | dist (`537d62d7…`, shell v58) | Backspace | `range-single` | `⌫ 刪除 失敗`, toast `EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged`; state `ready`, generation 1 → 1, the saved paragraph unchanged |
| `chrome-delete-v58-page.json` | dist | Delete | `range-single` | the same with `⌦ 前刪` |
| `firefox-backspace-v58-page.json` | dist | Backspace | `range-single` | the same |
| `chrome-backspace-v57-page.json` | v57's page (`e00ab76a…`, from git at `6e9ec27e`) | Backspace | `range-single` | the same — so not something 0.2.9 introduced |

Read from the source: the page's `beforeinput` handler maps `deleteContentBackward`/`deleteContentForward` to `delete-backward`/`delete-forward` whatever the selection (`web/e2-editor-app.js` `DELETE_INPUT_TYPES`); v19's manifest offers those two for `collapsed` only and offers `delete-selection` for `range-single` and `range-cross` (`dist/profiles/e2-editor-v19/sdk-manifest.json`, `editorContract.actions`); the page already uses `delete-selection` for cut when the profile offers it.

## 121-B on the candidate dist/ (2026-10-10; spec §15.2; page `b10f6017f36582d9…`, the probe unchanged, `page: "dist"` in each report)

`v59-candidate-{chrome,firefox}-{backspace,delete}.json`: in all four, the drag left `range-single`, the key ran 「刪除選取」 (13–17 ms), state `ready`, generation 1 → 1, revision 0 → 1, no toast, and the saved first paragraph is `M01 alpha` (the selected word gone). The red case is the v58-page reports above (refusal, reopen). 121-B met in both browsers.

## 121-B on the final v59 page bytes (2026-10-10; page `18c8afbe…`, A+B; spec §15.7–15.8, fable's fourth ruling condition 4)

Re-run because A+B changed the page after the run above, and these reports record only `page: "dist"`; the binding is `v59-candidate2-binding.txt` (dist sha256 read before and after the six 121/120 runs, `18c8afbe…` both times). `v59-candidate2-{chrome,firefox}-{backspace,delete}.json`: all four `range-single` → 「刪除選取」 (14–18 ms), `ready`, generation 1 → 1, revision 0 → 1, no toast, first paragraph `M01 alpha`. Field by field identical to the `b10f6017…` reports except the two latency strings. 121-B met in both browsers on the final bytes.

## 121-B on the release-P page bytes (2026-10-10; page `36c2b18b…`; spec §16.2 P4)

`p-candidate-{chrome,firefox}-{backspace,delete}.json` (binding `p-candidate-binding.txt`: dist `36c2b18b…` before and after the six 121/120 runs). Identical to the `v59-candidate2-*` reports field by field once the latency strings are removed: `range-single` → 「刪除選取」 (9–18 ms), `ready`, generation 1 → 1, revision 0 → 1, first paragraph `M01 alpha`. 121-B still met in both browsers.

## 121-B on the 0.2.13 page with finding 131's rule A (2026-10-12; page `d761f1ce…`; SPEC-M3-autosave §9.12–9.13)

`0.2.13-131fix-{chrome,firefox}-{backspace,delete}.json` (binding `0.2.13-131fix-binding.txt`: dist `d761f1ce…` before and after the four runs, 09:03:49–09:05:09Z; probe unchanged). All four: `range-single` → 「刪除選取」 (9–15 ms), `ready`, generation 1 → 1, revision 0 → 1, no toast, first paragraph `M01 alpha`. Same as the `p-candidate-*` reports once the latency strings are removed. Rule A leaves 121 intact: with no delete of this page's own out, the engine's range still goes out as `delete-selection`.
