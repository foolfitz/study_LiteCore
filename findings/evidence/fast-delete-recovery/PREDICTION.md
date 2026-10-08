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

## Run 1 result, and run 2's prediction (written 2026-10-09, before run 2)

**Run 1** (`chrome.json`, fresh page every attempt): **0 failures in 60** (44 overtaken, 16 correct). The frequency prediction ("at least 1 in 60") **missed**. The other rows have nothing to judge.

What differs from the one time it happened: in the 111 run the failing trial was the 61st document opened in one page (five rounds of twelve, every one opened through the page's file input in the same Worker session). Run 1 started every attempt in a fresh page.

**Run 2** (`chrome-same-page.json`, `--same-page`, this commit's probe): the page booted once (and again after a failure), every attempt's document opened through the file input, up to 120 attempts, stop at 3 failures.

| What | Prediction |
|---|---|
| Frequency | the failure comes back once the page has opened many documents (≥ 1 in 120), none in the first 30 |
| After it | as the table above (recoverable-error, save refused, the notice's reopen loses X) |

If run 2 also finds nothing: registered as seen once (with its conditions and both runs as the attempts), no finding opened.

## Run 2 results (2026-10-09; written after both same-page runs)

- `chrome-same-page-1.json` (probe before the leave-prompt fix): **attempt 41 failed** with the measured code; after it: `recoverable-error`, revision 1, checkpoint 「無」, the save button disabled and no bytes, the notice 「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來」 with one button 「重新開啟」; pressing it reopened generation 2 at revision 0 and the saved heading held **no X** (data loss, as predicted); `Q` typed without a click after that reopen did **not** land (predicted to work: missed); reopening through the file input, clicking and typing `Q` worked. Attempts 42–43 then hung on the page's own leave prompt (the probe had left an unsaved `Q`); the run was stopped there and the probe fixed to save first.
- `chrome-same-page-2.json` (fixed probe): **0 failures in 150** (all `overtaken-1` or `ok`).
- So the frequency prediction for run 2 ("≥ 1 in 120, none in the first 30") hit on run 1 and missed on run 2. Together: 2 natural failures in about 250 same-page attempts (run 1's 41, run 2's 150, the 111 round's 61), 0 in 60 fresh-page attempts. Finding 119 records the consequences; the ruling (`ruling/fable-ruling.md`) sets how its fix is verified.

## F119-B on the fixed page (SPEC-M3-production-ui §14.2; 2026-10-09)

Candidate `dist/` (page `537d62d7…`, session `62a2a20e…`; findings 119 and 111 fixed, v58 not yet frozen), probe with `--fixed`:

- **Injection arm** (`fixed-inject-chrome.json`, `fixed-inject-firefox.json`; each attempt a fresh page; the served HTML's shim answered the delete request with the recorded error, the request never reached the Worker): **3/3 PASS in each browser** — reopened by itself in 2.53–2.74 s (Chrome) / 3.37–3.47 s (Firefox), generation 1 → 2, `#notice` hidden, 19/19 toolbar buttons enabled, the saved heading 「一、序言XY」 (X and Y kept), `Q` typed with no click advanced the revision 0 → 1.
- **Natural arm** (`fixed-natural-chrome.json`, Chrome, one page, 400 attempts): **0 failures** — all 400 `ok` (with 111's fix no Backspace overtook Y any more).
- **Reading rule's red case** (`read-rule-red-case.txt`): `chrome-same-page-1.json` attempt 41 under the same rule reads FAIL.

Verdict under the rule written before the run (§14.2 F119-B): natural occurrences 0 (fewer than 2) → **the natural path is registered 「沒有實例可量」 (0 in 400 on the fixed page)**, and the browser half is carried by the injection arm, which passed 3/3 in both browsers. **F119-B holds; it does not establish the natural path.** Predictions (§14.3): the injection arm hit; "2–3 natural failures in 400" missed. The 0 in 400 is recorded, not read as evidence that the cause is gone (the ruling's F6: 111's fix changes when the delete starts, not why the callback is late).
