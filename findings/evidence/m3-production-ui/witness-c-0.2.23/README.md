# Witness: arms Rbs, Rdel, B3x on engine v20 / host 0.2.23 (SPEC-M3-link-batch §10.7)

One plain, **non-counted** run of the committed runner `wasm_sdk_probe/tools/check_m3_production_ui.py`, unedited, as the witness for changing the expectation of the refusal arms now that C makes a boundary Backspace/Delete a no-op. Requested by the main session. English.

## Prediction (fixed by the main session before the run; copied verbatim before running)

> Rbs and Rdel — generation '1' -> '1'; the boundary key completes as a no-op (look in the recorded timeline for `verified-boundary-noop` or equivalent and quote it); the reopen wait runs its full ~60 s; the server file has exactly one marker; the server text with the marker removed equals the original (`seqSha256 == ORIGINAL_SEQ`); the runner's score for each lists `no refusal-and-reopen happened` and NO other line. B3x — no generation change at any of the three presses, no `data-limit` 'saved'; red only in its refusal/limit lines. Any other red line, a fatal, or a toast is a finding — report it, do not explain it away.

## Reader's note written before the run (by the agent running it; not part of the prediction above)

Read from the runner's source before running, so that a difference is not explained away afterwards:

1. `score_run` (`check_m3_production_ui.py` ~:630–660) has, for Rbs/Rdel/B3x, a second check after the generation line: `blocked = [s for s in timeline if s.state not in ("ready", "busy")]`; **if there is none, it appends `A1-3: no sample outside ready/busy`.** On a run where nothing is refused there is no `restart-required`/`loading` sample, so I expect that line to appear **in addition to** `no refusal-and-reopen happened` for Rbs and Rdel. Read literally, the prediction ("and NO other line") would then be outside; I will report it as outside the prediction, not as a pass. (Whether it is a runner defect or the expected consequence of the changed expectation is for the main session; I record only that it is there.)
2. The runner's own `timeline` (`TIMELINE` js, :118) samples `state`, generation, revision, checkpoint, disabled/buttons counts and the toast text on every DOM change. It does **not** record the engine's completion name. So `verified-boundary-noop` will not literally be in the report. The "equivalent" I can quote is: a `busy` interval of about 2.25 s after the key, then `ready`, the generation unchanged, the revision unchanged, no toast; plus `afterKey` (the page state at the end of the reopen wait, which may carry the page's latency label 「⌫ 刪除 … ms」 / 「⌦ 刪除 … ms」). I will not add a hook to see the completion name (the runner must run unedited).
3. For B3x, `score_three_refusals` (:763) lists many lines, not only refusal/limit ones: generations, the state after the third key, the notice's limit, the server lacking `zqa/zqb/zqc` (no save is pressed in that arm, and with no refusal there is no rescue), `unsavedHiddenAfter`, the reload guard, `genReloaded`, the fetched sha, the lock. With no refusal I expect typed-but-unsaved content on the page, so I expect more red lines than "refusal/limit" (at least the server-lacks-markers line and the unsaved/reload-guard ones), and a risk that `leave_by_close(... NOTICE_ACTION)` finds no notice button. Also reported as outside the prediction when it happens.
4. The runner clears the **whole** `oc_files_lock` table at the start of every arm (`Server.clear_locks`) and again in `finally`; that is its documented contract ("Never run two M3 runners at once") and runs unedited. Before the run I only read the table (below).

## Desk (before the run; `desk-readings.txt`)

2026-10-14T18:49:44Z: KWallet `Locked` `b false`; `pgrep -c chrome` 32, `pgrep -c firefox` 1 (both the owner's, untouched); load `0.41 0.57 0.98`; no M3 runner, probe or chain process running. `oc_files_lock` (a read-only `SELECT` through `ddev mysql`): 10 rows (ids 3989–4011, file ids 18591–18621), **all lapsed** (ttl 300 s; ages 1,063–7,327 s; the newest, file 18621, is the last row of my earlier `hold-2300` probe). None is live, so there was nothing to wait for and nothing was cleared by me; the runner's own `clear_locks` removes them when its first arm starts.

## The run

`cd wasm_sdk_probe && python3 tools/check_m3_production_ui.py --rounds 1 --arms Rbs,Rdel,B3x --out <this directory>/witness-c-0.2.23.json` — no `--counted`, default browsers `chrome,firefox` (the 0.2.13 chain `runs-0.2.13/chain-2026-10-12.sh` passes no `--browsers` either), one round, arms in the runner's loop order (per browser: Rbs, Rdel, B3x; Chrome first). The runner is the committed one: sha256 `bd3a15fbd4a9f30db5d3ac7eb632f230e8d58ddb8e7cef80a4749a76081a112b` = `git show HEAD:…/check_m3_production_ui.py` (last touched by 4421df62, the 0.2.23 pin move), `git status` clean for it; `runner-sha256.txt`. 2026-10-14T18:50:05Z → 19:02:42Z (about 12.6 min), exit 0, `stderr.txt` empty, `stdout.txt` kept. Identities from the report's `static`: host 0.2.23 commit `2ccf1a9`, `hostDirty []`, buildId `c3c22d9294de068a`, served page = dist page `ccb67a52a3fe…`, served session `f47c80ec9553…`, shell bundle v72 exit 0; document `PMPC指南.odt` sha256 `7b336879547df057…` (= the runner's `DOC_SHA256`), 563,149 bytes, 0 markers. Chrome 151.0.7922.169, Firefox 157.0.1. Locks cleared by the runner at each arm's start: 10, 1, 1, 1, 0, 0 rows; `oc_files_lock` read 0 rows after the run. No fatal in any of the six runs.

The numbers below are read by `read_witness.py` (my own small reader, in this directory; output `reader-output.txt`) from the raw report; the runner's own score lines are copied verbatim from `report["score"]`. A note on the one thing the prediction asked to quote: the runner's report has no `verified-boundary-noop` string (its timeline samples only state, generation, revision, checkpoint, disabled-button count and the toast text). What it does record, and what I quote as the equivalent, is a `busy` sample followed by a `ready` sample about 2.26 s later with the revision and generation unchanged; the engine-level name for exactly that sequence, `verified-boundary-noop` with `waitedMs` 2252–2260, was read on this host version in `findings/evidence/host-0.2.23-hold/`.

## Readings per arm and browser (from the raw report)

| arm / browser | generation | the key (busy → ready in the timeline) | revision | markers on the server | `seqSha256 == ORIGINAL_SEQ` | the reopen wait | runner's red lines (verbatim) |
|---|---|---|---|---|---|---|---|
| Rbs / Chrome | `1` → `1` | busy at 9,100 ms → ready at 11,360 ms = **2,260 ms** | 3 → 3 | 1 | **true** | last sample at 71,475 ms (60 s wait + two 1 s sleeps after the key at ~9 s); `afterKey` ready, pending 0, generation 1 | `generation 1 -> 1: no refusal-and-reopen happened`; `A1-3: no sample outside ready/busy` |
| Rdel / Chrome | `1` → `1` | busy 8,180 → ready 10,441 = **2,261 ms** | 3 → 3 | 1 | **true** | last sample 70,620 ms | the same two lines |
| Rbs / Firefox | `1` → `1` | busy 9,237 → ready 11,494 = **2,257 ms** | 3 → 3 | 1 | **true** | last sample 71,845 ms | the same two lines |
| Rdel / Firefox | `1` → `1` | busy 8,153 → ready 10,411 = **2,258 ms** | 3 → 3 | 1 | **true** | last sample 70,751 ms | the same two lines |
| B3x / Chrome | `1→1`, `1→1`, `1→1` (after the notice step still `1`) | three busy → ready spans: 9,101→11,364 (**2,263 ms**, rev 3→3), 79,237→81,493 (**2,256 ms**, 6→6), 149,329→151,585 (**2,256 ms**, 9→9) | 0 → 9 (3 typed per round, none changed by a key) | `zqa` 1, `zqb` 1, `zqc` 0 | n/a for this arm | n/a | seven A1-5 lines and `A1-3` (below) |
| B3x / Firefox | `1→1` ×3 | 39,443→41,700 (**2,257 ms**, 3→3), 109,586→111,843 (**2,257 ms**, 6→6), 179,878→182,136 (**2,258 ms**, 9→9) | 0 → 9 | `zqa` 1, `zqb` 1, `zqc` 0 | n/a | n/a | the same |

All four R runs: `save.outcome` saved (2 saves), no sample outside `ready`/`busy`, generation `['1']` throughout, `fatal` none; the timeline's toast text is only the open's 「已開啟 m3-109 測試.odt」 and, at the very end, the runner's own explicit save's 「已存回 m3-109 測試.odt（553.9–554.0 KB）」. During the 60 s wait the host's own autosave ran (`afterKey.latency` reads 「自動存回 85–97 ms」 in all four; in the Chrome Rbs timeline the checkpoint goes 「有（r3）」 → 「無」 at 39 s), which is why `afterKey` shows that label and not 「⌫ 刪除 …」.

B3x, per press (generation before → after; state after the press; `data-limit`): Chrome press 1 `1→1`, ready, none; press 2 `1→1`, ready, none; press 3 `1→1`, ready, latency 「⌫ 刪除 2257 ms」, none, `limitAfter` null. Firefox: the same, latencies 「⌫ 刪除 2258 ms」, 「自動存回 84 ms」, 「⌫ 刪除 2259 ms」. Presses 1 and 2 in Chrome (and press 2 in Firefox) show an autosave label because the host's autosave fired between the no-op and the runner's read; the busy spans above show every one of the three presses completing as the ~2.26 s no-op. `unsavedHiddenAfter` null. The host saved twice on its own in each browser before the notice step (`trigger: auto`; Chrome sha `ff8a46a7230c…`, `5d5be221fae2…`; Firefox `bc6d1738890c…`, `a017c99817c5…`); the server ended with `zqa` and `zqb` but not `zqc`. After the runner clicked `#notice-action` (a direct `.click()`; whether the element was visible is not recorded) the page was **not** reloaded: `reload.path` unchanged (`…/e2-editor.html?fileId=7340`), the recorder only has its `installed` entry (no `beforeunload` fired), generation `1`, and the page state reads latency 「回到檢查點 失敗」 with toast **「回到檢查點：editor cannot restart from ready」**, in both browsers.

Runner's own score lines, verbatim:

```
Rbs/chrome   0/1: generation 1 -> 1: no refusal-and-reopen happened | A1-3: no sample outside ready/busy
Rdel/chrome  0/1: generation 1 -> 1: no refusal-and-reopen happened | A1-3: no sample outside ready/busy
Rbs/firefox  0/1: generation 1 -> 1: no refusal-and-reopen happened | A1-3: no sample outside ready/busy
Rdel/firefox 0/1: generation 1 -> 1: no refusal-and-reopen happened | A1-3: no sample outside ready/busy
B3x/chrome   0/1 (and the same eight lines for B3x/firefox, with only the recorder's timestamp differing):
  A1-5: generations [('1', '1'), ('1', '1'), ('1', '1')], want 1->2, 2->3, 3->3
  A1-5: after the third refusal the state is 'ready'
  A1-5: the notice says None 10 s after the key, not 'saved'
  A1-5: the server's file lacks ['zqc'] (no save was pressed)
  A1-5: the host still showed unsaved work 3 s after the rescue
  A1-5: the recorder saw no beforeunload, so 'not asked' means nothing ([{'what': 'installed', 'at': 166333}])
  A1-5: the reloaded page did not open the server's rescued bytes
  A1-3: no sample outside ready/busy
docClean True, allPass False
```

(Firefox B3x's recorder entry reads `'at': 197011`; the line is otherwise identical.)

## Verdict against the prediction

| prediction | reading | verdict |
|---|---|---|
| Rbs, Rdel: generation `1` → `1` | 4 of 4 | holds |
| the boundary key completes as a no-op (quote the timeline) | 4 of 4: a busy → ready span of 2,257–2,261 ms with revision 3 → 3 and generation 1 → 1 (quoted in the table); the name `verified-boundary-noop` is not in the runner's report (see above) | holds, on the equivalent |
| the reopen wait runs its full ~60 s | 4 of 4: the timeline runs to 70.6–71.8 s after a key at 8.2–9.2 s; no generation change ever made the wait's predicate true | holds |
| the server file has exactly one marker | 4 of 4 (`marks` 1) | holds |
| server text without the marker equals the original | 4 of 4 (`seqSha256` `d646dda7c887a8b6…` = `ORIGINAL_SEQ`) | holds |
| the runner's score lists `no refusal-and-reopen happened` and **no other line** | each of the four lists that line **and** `A1-3: no sample outside ready/busy` | **outside the prediction** (the second line is the runner's A1-3 expectation that a refusal leaves a blocked state; it was predicted from the source in the reader's note, item 1) |
| B3x: no generation change at any of the three presses | 6 of 6 presses `n → n`; each a 2.26 s no-op (revision unchanged) | holds |
| B3x: no `data-limit` `saved` | `limit` None in both browsers | holds |
| B3x: red only in its refusal/limit lines | red also in: server lacks `zqc`; host still showed unsaved work; no `beforeunload` seen; reloaded page did not open the rescued bytes; plus `A1-3` | **outside the prediction** (reader's note, item 3) |
| a toast is a finding | no toast in the R arms beyond the open's and the runner's own save's; **B3x: 「回到檢查點：editor cannot restart from ready」 (latency 「回到檢查點 失敗」) after the runner's `#notice-action` click, in both browsers, with no reload** | **finding** |
| a fatal is a finding | 0 of 6 | none |

One of my own guesses was also off: reader's note item 3 expected the server to lack all of `zqa/zqb/zqc`; the host's autosave had already put `zqa` and `zqb` there (only `zqc` is missing).

Not explained here, reported as read: why the B3x notice button exists and is clickable in `ready` with no refusal (the runner clicks it blindly), and whether `A1-3` is a line the changed expectation should drop. Those are for the main session's expectation change (SPEC-M3-link-batch §10.7).

## Side effects in the instance

The runner uploads its document as `m3-109 測試.odt` into the admin files root at the start of every arm (documented contract). That path is fileId **7340**, the same file the 10-14n README names as the owner's `m3-109 測試.odt`; this run therefore overwrote it, as every M3 runner run does. It now holds the last arm's (Firefox B3x) state: 567,408 bytes, sha256 `a017c99817c5a32d…`, with the markers `zqa` and `zqb` in it. I did not save its previous bytes; Nextcloud's file versions may hold them. `oc_files_lock` is empty. No folder or file of mine was added.
