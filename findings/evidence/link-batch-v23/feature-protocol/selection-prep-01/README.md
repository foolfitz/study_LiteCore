# Selection collector preparation 01 (uncounted): reader route defect

First browser preparation of the public ABI6 selection collector, explicitly `--preparation-only`, Chrome, one source case `shift-Right@caret-mid`. It counts toward nothing. Command receipt: `runner.command.json` (exit 1, 15 s). The foreign-CPU guard passed (`report.json` `foreignCpu.ok: true`); lock and cleanup are in the cell record.

## What happened

The page booted on the actual feature profile, the readiness document opened, the readiness `Z` reached the wire and both readiness saves completed (`readiness-after-save` shows the mutation). The runner's in-loop readiness reader then stopped the cell:

```
judge_v23_feature_pre_red.NotEstablished: missing/nonunique wire call readiness-restore-point
```

The raw cell is `chrome-shift-Right@caret-mid.json.gz` (deterministic gzip of the original, SHA256 `cc3beeb1…c297` both before compression and after decompression; the uncompressed original is ignored by `../.gitignore`).

## Cause (read from the raw page and the product source)

`NarrowEditorV2Session.placeCaret` (`editor-shell-v2/narrow-editor-v2-session.js`, finding 140 second pass) chooses its wire route from its own first `editorGetStateV2` read: an open range posts `click`; a collapsed caret posts `editorPlaceCaretV2`. In this page:

- `readiness-search-click` ran after `search` had selected the match, so it posted `click`.
- `readiness-restore-point` ran after an empty-prefix selection (the readiness point is the paragraph start), so the caret was collapsed and it posted `editorPlaceCaretV2`, followed by the product's own grace polls.

The selection reader had copied the historical v19 pre-red reader's literal `'click'` for every place-caret call. On the v19 route only `click` exists, so that assumption was invisible there. On ABI6 it is false whenever the caret is collapsed, which also covers every measured cell's `-origin-click` after a fresh open and the drag's initial pointerdown.

## Disposition (source, before any further runtime)

`tools/judge_v23_feature_selection.py` now derives the expected operation per call from the raw reply to the product's first in-call state read (`place_route`), not from page labels: collapsed → `editorPlaceCaretV2`, range → `click`. Exactly one route operation must exist in the call window and must follow that read; a fallback carrying both routes, a missing read, or a route that contradicts its own read is NOT_ESTABLISHED. `editorPlaceCaretV2` joins the owned-mutation set used by closure and by the measured-key interval check. The historical pre-red reader is unchanged.

`tests/test_v23_feature_selection.py`: the synthetic page now models the product's two routes (both occur in the baseline), and `PlaceRouteControls` adds five red controls (collapsed-but-click, range-but-placeCaret, stale state read, fallback with both routes, missing state read); all five read NOT_ESTABLISHED with a placeCaret reason. 14/14 tests pass.

Re-reading this preserved page with the corrected reader: `readiness()` now passes on the actual evidence. The measured arms were never reached, so nothing about S1/S2/S3 behavior is established by this preparation.
