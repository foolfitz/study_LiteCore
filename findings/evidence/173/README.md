# Finding 173 evidence: a bullet in a NEW blank document locks the queue on the ordered engine (v24, v25)

Reported by the owner on host 0.2.40 (2026-10-29 evening): in a blank document from Files "+ New -> New document", pressing the bullet button shows 「引擎需要重新開啟。沒有檢查點…」. Reproduced on the local mirror, no DDEV.

## Tool and inputs

`blank_bullet.py` (a diagnostic, not a gate; `python3 -I blank_bullet.py <new dir>`). It imports `../link-batch-v25/f1/diag_format_v25.py` for the products and the engine-record observer. Products: v22 (the 0.2.27 package, i.e. the engine line host 0.2.38 shipped), v24 from its own bytes, v25 as `dist/` serves it (identity checked; both ok). The document is the host's own blank template for a zh_TW user, `/home/jiajun/Projects/Nextcloud_Apps/litecore/blank/en-US_zh-TW_A4.odt` (sha256 in the report), opened through the page's own file input. Two arms: press the bullet right after the document opens, and after clicking into the paragraph. Chrome.

Run 01 (scratch, not kept) failed in the tool itself: opening a document starts a new worker, so the engine-record observer attached before the open lost its CDP session (`Session with given id not found`). The tool now re-attaches after the open; run-02 is the measurement.

## run-02 (2026-10-29 ~21:55 +0800)

| Product | Both arms | failureShape | dispatched (engine record / page) | Page |
| --- | --- | --- | --- | --- |
| v22 | same | `stage-deadline:awaiting-selection` | absent, stage `awaiting-selection` / true (inferred) | `ready`, toast "動作已送出，但這一段是空的…這是檢查的極限" |
| v24 | same | `select-text-returned-none` | absent, stage `idle` / false | `recoverable-error`, notice 「引擎需要重新開啟。沒有檢查點…」 |
| v25 | same | `select-text-returned-none` | **true**, stage `awaiting-result` / true | `recoverable-error`, same notice; toast "（可能已經改到文件：請回到檢查點）" |

## Mechanism (read from the code, consistent with the table)

- The page's disposition (`wasm_sdk_probe/editor-shell-v2/paragraph-editor-client.js` `formatFailureDisposition`) treats an unverified dispatch as `dispatched-unverified` (queue stays open, undo reachable) for exactly two shapes: `multi-block-readback` (finding 046: a blank line whose selection overshoots into the next paragraph) and `stage-deadline:awaiting-selection` with `selectionResultSeen` (finding 083: a blank paragraph where `.uno:SelectText` selects nothing). Every other dispatched failure is `dispatched-rollback`.
- The ordered engine (v23 onward) reports finding 083's situation under a new name: `finishOrderedFormatReadback` in `wasm_sdk_probe/src/ordered_format.inc` refuses with `select-text-returned-none` when the synchronous selection type is `LOK_SELTYPE_NONE`. The page does not know that name, so the same situation that v22 kept open now demands a rollback; a new document has no checkpoint, hence 「引擎需要重新開啟」.
- On v24 the 171 projection (`dispatched: false`) took the same blank document to the same notice by another route. v25's 171 fix makes `dispatched` true, which then meets this missing branch.
- A blank line INSIDE a document overshoots into the next paragraph (`multi-block-readback`), which is the case F1/F3 measured; a whole blank document has no next paragraph. No check covers it.

Other shapes the ordered readback can emit (`selection-type-not-readable`, `footnote-apparatus-readback`, `unknown-structural-tag`, `malformed-readback-nesting`, `block-extraction-failed`, `postcondition-not-met`) also reach `dispatched-rollback`; whether v22 kept any of those situations open is not measured here.
