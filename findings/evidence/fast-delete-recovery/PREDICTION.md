# A fast Backspace that fails on a large document — what the user is left with (predictions written 2026-10-09, before the probe ran)

Seen once, unplanned: finding 111's owner-document run in Chrome (`../111/browser/owner-chrome.json`, round 6, `X`, `Y`, Backspace at a 0 ms gap) got `⌫ 刪除 失敗` with `EDITOR_STATE_UNAVAILABLE：selection text became visible without its required typed callback` and saved nothing; every one of the 59 later trials in that page typed nothing (revision 0 → 0) although each opened its document and placed its caret.

Read from the source (not measured): the message is the selection barrier's negative-deadline path (`src/probe_engine.cpp` ~:3888, a unit selection that showed up without its typed callback); the error carries no barrier detail, so `recoveryFor` answers `rollback` (`editor-shell-v2/paragraph-editor-client.js` `formatFailureDisposition`, fallback), `_blockQueueIfDispatched` puts the session in `recoverable-error` (`narrow-editor-v2-session.js` ~:716), and nothing takes a checkpoint before a delete (109's fix covers only `EDITOR_BOUNDARY_UNSUPPORTED`).

Probe: `wasm_sdk_probe/tools/probe_fast_delete_recovery.py` (this commit), shipped standalone page from `dist/` (v19), no product byte changed. Each attempt in a fresh page: the owner's document, click the end of 「一、序言」, End, real `X` `Y` Backspace at once; on a failed delete it records the notice, tries the save button, presses the notice's button, saves again, types `Q`, then reopens through the page's file input and types `Q`. Chrome, up to 60 attempts, stopping at 3 failures. The report keeps only the heading paragraph.

## Predictions

| What | Prediction |
|---|---|
| Frequency | the failure recurs: at least 1 in 60 attempts (it was 1 in the first 6 Backspace/0 trials of the 111 run) |
| State after the failure | `recoverable-error`; checkpoint field 「無」 (no selection gesture or move with unsaved work happened) |
| Save button | refused (no bytes) — the queue is blocked |
| The notice | shown, offering a rollback; pressing it reopens the **last saved bytes**, so the typed `X` is **gone** (data loss) |
| Typing after the notice's reopen | works (`Q` moves the revision) |
| Reopening through the file input after the failure | `Q` moves the revision **if** the notice's reopen ran first; the 111 run never pressed the notice, so its dead typing is the blocked queue of the failed session carried into the next open — predicted here only as "typing works after the notice" |

## What would change the decision

- X survives (the save works, or the notice keeps the typed text): not a data-loss defect; the failure is a spurious error to register, ranked with 111.
- X is lost: a new finding of the 109 class (data loss on an everyday edit), ranked ahead of 111; the fix is in the shell (take a checkpoint or keep the queue open on this code), not in the adapter (E1-C).
- The failure does not recur in 60 attempts: registered as seen once, with this run as the attempt to reproduce.

## Results

(appended after the run)
