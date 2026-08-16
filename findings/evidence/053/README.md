# Finding 053 — the product prescribes a recovery whose button it does not show

Two pieces of evidence, neither of them new work: this defect was found by
**driving a path the coverage audit had already named**, and both halves were
already lying in the tree.

## 1. The error is reachable on the shipped artifact, and it prescribes rollback

`../sdk-e2/e2-c-validation/d2-presweep/e2-editor-v2-572035ac/firefox/result.json`
(Chrome's is identical), cell `d2-refused-no-mutation-engine`:

```json
{"code": "EDITOR_FORMAT_POSTCONDITION_FAILED",
 "message": "the document does not show the state this action asked for",
 "recovery": "rollback",
 "disposition": "dispatched-rollback",
 "formatBarrier": {"failureShape": "postcondition-not-met", "dispatched": true}}
```

`recovery: "rollback"` is the field SPEC E2-B 5.13 requires every host to obey.

## 2. The button is not offered in the state that error leaves behind

`../sdk-e2/e2-c-validation/product-path/round-2-high-paths/` — every run records,
under the `notice-action-recovers-the-session` check:

```json
{"noticeOffered": {"shown": false, "label": "回到檢查點", "disabled": false},
 "toastFromPressingItAnyway": "回到檢查點：editor cannot restart from ready"}
```

`#notice` is `display: none` until `data-show="1"`, and that attribute is set in
exactly one place (`web/e2-editor-app.js:93`) from
`state ∈ {recoverable-error, restart-required}` — the same set
`EditorSession.restart()` accepts (`editor-shell/editor-session.js:588`).

## The gap, as two sets

| | |
|---|---|
| prescribes rollback | any format failure whose barrier says `dispatched: true`, plus every `unknown-rollback` (`editor-shell-v2/paragraph-editor-session.js`, `recoveryFor`) |
| offers the button | `TIMEOUT`, `WORKER_CRASHED`, `WORKER_RESTARTED`, `STALE_DOCUMENT`, `MUTATION_OUTCOME_UNKNOWN`, `EDITOR_RESULT_INVALID` (`RECOVERY_ERRORS`), plus `EDITOR_BOUNDARY_UNSUPPORTED`, plus a failed open |

`EDITOR_FORMAT_POSTCONDITION_FAILED` is in the first and not in the second.

Checked for a way out and did not find one: `_blockQueue` and `_enterRecovery`
are called from four places in the whole shell (`editor-session.js` lines 179,
320, 325, 602) and `#notice`'s visibility is assigned once.

## What is NOT established here

**The end-to-end reproduction in the product page has not been done.**  What is
shown above is (a) the error occurs on the shipped artifact with that
prescription and (b) in the state that error leaves the session in, the button is
hidden and pressing it fails.  Joining them in one browser run needs the caret on
an empty paragraph in `e2-editor.html`; the route is written down in the finding.
