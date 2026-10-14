# Host 0.2.23: a flagged 3-second hold of Backspace at the document start (release-text draft §4.3 / §6)

Scope: one short measurement, the `hold-3s` arm of task 10-14n re-run on the installed host 0.2.23. No product, host, ddev, check, judge, test or Makefile file was touched; no push. Times are milliseconds on the page's own clock (`performance.now()`), measured from the first keydown of the arm unless said otherwise. Facts and readings are labelled; an inference says so.

## Prediction (fixed by the main session before any run; copied verbatim before the first run)

> during a 3-second flagged hold at the document start, **at most 2** delete requests reach the engine (the first at the keydown, at most one more after the first no-op answers at ~2.26 s); **0 characters deleted**, **0 refusals**, the document unchanged; the editor is ready again **at most ~2.4 s after keyup** (one 2.25 s window plus slack), i.e. ready ≤ about 5,400 ms from the keydown. A reading outside this is a finding, not an instrument problem, unless the run itself failed.

## Verdict against the prediction

Every reading is inside the prediction: 6 of 6 hold runs (3 Firefox, 3 Chrome) and both controls. Per criterion (`summary-table.txt`, produced by `summarize_hold.py` from the raw reports):

| criterion (prediction) | Firefox 157.0.1, 3 runs | Chrome 151.0.7922.169, 3 runs | verdict |
|---|---|---|---|
| at most 2 delete requests reach the engine | **2, 2, 2** (sent at 1.1 ms and at 2,273.8–2,275.8 ms) | **2, 2, 2** (1.0–1.3 ms and 2,270.7–2,271.0 ms) | **holds** |
| the second one goes out right after the first no-op answers (~2.26 s) | first answer at 2,256.9–2,257.3; second request 17–19 ms later | first answer at 2,260.9–2,265.4; second request 5–10 ms later | **holds** |
| 0 characters deleted | `verifiedDeletes` 0, no response with `changed: true`, 0 of 3 | same, 0 of 3 | **holds** |
| 0 refusals | 0 error responses, generation `['1']`, no toast, 0 of 3 | same | **holds** |
| the document unchanged | engine answers `rev 0 → 0` (both), page revision 0 at the start and at the end | same | **holds** |
| ready again at most ~2.4 s after keyup | **1,438.5 / 1,438.8 / 1,443.4 ms** after keyup (min 1,438.5, max 1,443.4) | **1,523.3 / 1,523.8 / 1,526.0 ms** (min 1,523.3, max 1,526.0) | **holds** (about 0.9 s of margin) |
| ready ≤ about 5,400 ms from the keydown | final ready at **4,534.6 / 4,538.1 / 4,538.9** | final ready at **4,528.3 / 4,528.8 / 4,530.9** | **holds** (about 0.86 s of margin) |

Positive control (`owner-sequence`, one Backspace at the document start, no hold): **it exercised C** in both browsers, so the hold readings are not void. Firefox: 1 request, `verified-boundary-noop`, `waitedMs 2253`, ready at 2,255.8 ms (label 「⌫ 刪除 2256 ms」). Chrome: 1 request, `verified-boundary-noop`, `waitedMs 2259`, ready at 2,262.8 ms. Both: no toast, generation 1, revision 0 → 0. These are the same numbers as 10-14n on 0.2.20 (2,255.7 ms Firefox, 2,261.4 ms Chrome).

Comparison, from `host-0.2.20-hand-test/README.md` (10-14n, host 0.2.20, the same arm, the same bytes): 85 keydowns, 3 `beforeinput`, 3 no-ops, ready at 6,768.0 ms (Firefox) / 6,771.4 ms (Chrome). Now: 85 keydowns, 4 `beforeinput`, **2** no-ops, ready at 4,528–4,539 ms. So between 0.2.20 and 0.2.23 (the page changes of findings 141 and 144; which of the two did it is not separated here) the flagged hold went from three engine windows to two; the second window is still there.

## What was run

- **Host**: `https://litecore.ddev.site:8443`, host 0.2.23 (commit `2ccf1a9`, `hostDirty []`), buildId `c3c22d9294de068a`, served page `ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e` (= `dist/` page), served session `f47c80ec9553…`, shell bundle `e2/editor-shell-v2-bundle-v72.json` exit 0, `problems []` (every report's `static`, read at the start of each invocation; the page hash is the one named in the task).
- **Probe**: `probe_10_14q.py`, a byte-for-byte copy (cmp identical; sha256 `9d95c8157e56737383b6aea9406cef4cdae15355baee33bab2051bd4ba9bd900`) of `findings/evidence/host-0.2.22/probe_10_14q.py` (commit 54dafccd), the newest probe that has `hold-3s`. It pins no page hash and no host version (it records them), so **no pin line was changed**; the copy is unedited. Its one hard-coded input path, the owner's document copy `…/30f3fb46-…/scratchpad/owner-docs/16630.odt` from an earlier session, still existed and was used as is.
- **Document**: `--doc owner16630`, the owner's `手測-126-60頁.odt` bytes (sha256 `e1d5658e598d51f94a0e7d5358101b63bc0134101d8a81f31d00e08e868ab9c3`, 24,340 bytes, 60 pages), the document 10-14n's `hold-3s` used; uploaded as a copy to a probe-created folder, never the owner's file itself. The caret is put at the document start by a real click on the first line then Home (`click-home`, settled before the key).
- **The hold** (`hold-3s`): one keydown, repeats every 30 ms from 500 ms with `repeat: true` as WebDriver/CDP flag them (84 of 85 keydowns flagged in every run), keyup scheduled at 3,005 ms. Chrome's keyup landed at 3,004.9–3,005.0 ms; Firefox's (WebDriver action latency) at 3,094.7–3,100.1 ms. Ready-after-keyup is computed from the actual keyup.
- **Runs**: `owner-sequence` once and `hold-3s` three times in each browser, one browser job at a time, each round a fresh login, a fresh headless browser profile and a fresh open (`--rounds 3`). Firefox 157.0.1 headless (geckodriver, 1850×1080), Chrome headless over CDP (1850×980); both are the probe's own private instances, the owner's windows were not touched. Order: Firefox control, Firefox hold ×3, Chrome control, Chrome hold ×3. No run failed (`fatal` absent in all eight).
- **Desk** (before the first run, `desk-readings.txt`): KWallet `Locked` `b false`; `pgrep -c chrome` 32 (the owner's Chrome, running throughout), `pgrep -c firefox` 1 (the owner's); `/proc/loadavg` `1.11 1.42 1.66`. Each run's own `preflight` is in its report: KWallet `b false` every time, chrome 33–37, firefox 1, `oursRunning []`, 1-minute load 1.56–3.56 (the highest at the start of the first Chrome hold round; the readings of that round are within 3 ms of the others).

## Per-run table (from `summary-table.txt`)

`engine req` counts `editorActionV2` requests sent to the engine worker (paints excluded); `ready` is the page's `#state-pill` going to `ready`. The pill read `ready` for a short moment between the two windows (about 19 ms in Firefox, about 6 ms in Chrome: the first answer, the repaint, then the second request), so the table gives both the first and the final ready.

| browser | arm | run | keydowns (flagged) | `beforeinput` | engine req | no-ops | refusals | deleted | revision | keyup ms | 1st ready | final ready | ready after keyup | requests at ms | answers at ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| firefox | owner-sequence (control) | 0 | 1 (0) | 1 | 1 | 1 | 0 | 0 | 0→0 | 2.3 | 2,255.8 | 2,255.8 | n/a (single press) | 0.7 | 2,256.0 |
| firefox | hold-3s | 0 | 85 (84) | 4 | 2 | 2 | 0 | 0 | 0→0 | 3,100.1 | 2,257.1 | 4,538.9 | 1,438.8 | 1.1, 2,275.8 | 2,257.3, 4,539.2 |
| firefox | hold-3s | 1 | 85 (84) | 4 | 2 | 2 | 0 | 0 | 0→0 | 3,096.1 | 2,256.7 | 4,534.6 | 1,438.5 | 1.1, 2,273.8 | 2,256.9, 4,534.8 |
| firefox | hold-3s | 2 | 85 (84) | 4 | 2 | 2 | 0 | 0 | 0→0 | 3,094.7 | 2,256.8 | 4,538.1 | 1,443.4 | 1.1, 2,274.7 | 2,257.0, 4,538.3 |
| chrome | owner-sequence (control) | 0 | 1 (0) | 1 | 1 | 1 | 0 | 0 | 0→0 | 3.0 | 2,262.8 | 2,262.8 | n/a (single press) | 0.9 | 2,262.9 |
| chrome | hold-3s | 0 | 85 (84) | 4 | 2 | 2 | 0 | 0 | 0→0 | 3,005.0 | 2,265.2 | 4,528.8 | 1,523.8 | 1.3, 2,270.8 | 2,265.4, 4,528.9 |
| chrome | hold-3s | 1 | 85 (84) | 4 | 2 | 2 | 0 | 0 | 0→0 | 3,005.0 | 2,260.7 | 4,528.3 | 1,523.3 | 1.0, 2,271.0 | 2,260.9, 4,528.4 |
| chrome | hold-3s | 2 | 85 (84) | 4 | 2 | 2 | 0 | 0 | 0→0 | 3,004.9 | 2,262.0 | 4,530.9 | 1,526.0 | 1.1, 2,270.7 | 2,262.2, 4,531.0 |

All eight runs: generation `['1']`, no toast, no limit notice, `deletesAfterRelease` 0, every no-op `waitedMs` 2252–2260 (the engine's 250 ms + 2,000 ms window), `changed: false`, `rev`/`beforeRev` 0.

## Readings (beyond the criteria)

- **Four `beforeinput` events, two requests** (fact): in every hold run the sink saw 4 `beforeinput` (the first at ~0 ms, then ~500 ms, then one right around the first no-op's answer at ~2.27 s, then ~2.3 s) and only 2 `editorActionV2` requests left the page; the other 81 keydowns produced no `beforeinput` at all. **Inference** from the timestamps of run 0 in each browser (the page source was not re-read for this): the press at ~500 ms and the one at ~2.3 s are held presses, and each is dropped when the no-op that was in flight answers (the names `boundaryNoopStands` / `dropHeldDeletes` in the 10-14q README), so the second request is the repeat that arrives just after the first answer. Not needed for any verdict above.
- **The cost of a flagged hold at a C boundary is one engine window per ~2.26 s the key stays down, past the first.** For a 3 s hold that is 2 windows and 4.5 s of 「處理中」, 1.4–1.5 s of it after the key is up. The 0.2.22 README named this residual ("a flagged hold at a C boundary still costs one no-op per 2.25 s window"); this run measures it at 2 windows. **Not measured**: a hold longer than ~4.5 s (the pattern, a repeat after each answer being sent, suggests a third request at ~4.5 s, and so on; that is an inference, not a reading), and an *unflagged* hold (release/press pairs, which is the `burst-1s` shape; 10-14q's N1 measured it at 1 request / ready 2,258 ms on the dist mirror, not re-run here).
- **Against the release-text draft §4.3 / §4.5** (`handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md`): it says that during a flagged hold each 2.25 s window takes one silent no-op, and that after the key comes up the editor stays 「處理中」 for at most one more window (about 2.25 s); it marks both 「0.2.22／0.2.23 的瀏覽器實測：未量」 and calls the 「最多一個窗」 a source-reading inference. This run is a browser reading for one hold length: 2 no-ops in a 3 s hold (one per window, as stated), nothing deleted, and 1.44–1.53 s of busy after the key came up, inside one window. The worst case the sentence has to cover (key released just after a request goes out, so close to a full 2.25 s remaining) and longer holds were **not** measured; this run does not contradict the sentence and does not prove its bound. The earlier suggestion in the 0.2.22 README, 「further presses or a held key cost nothing more」, is too generous for a held key with flagged repeats: it cost one extra window here (ready at 4.5 s, not 2.26 s). For separate presses and unflagged repeats, 10-14q's N1 reading (1 request, ready 2,258 ms) stands and was not re-run.

## Limits

- Headless browsers with driver-flagged repeats; the owner's real keyboard path (Wayland, fcitx5) was not driven. 10-14n noted that path may deliver unflagged repeats; that case is the burst, not this arm.
- Single document (the owner's 60-page bytes), caret at the document start of an unnumbered first heading; no table, list, numbered or indented first paragraph.
- One hold length (3 s) and three runs per browser: the final ready times differ by 4.3 ms (Firefox) and 2.6 ms (Chrome) across the rounds, and every run gave 2 requests, so no intermittency showed at this count. That is a count of three, not a rate; other hold lengths were not tried.
- The page's own clock; the summarizer reads the page's `#state-pill` transitions and the hooked worker messages, as in 10-14n.

## Instrument check (a green from the summarizer alone proves nothing)

`self-test.txt`: `python3 -I summarize_hold.py --self-test` feeds the verdict functions copies of a real run deliberately broken one criterion at a time (3 requests; 1 deleted; 1 refusal; revision 0 → 1; ready 2.5 s after keyup; ready at 5,500 ms) and a control with no engine request at all; every one turns red, and the unbroken real runs are green first. The control criterion K1–K3 would be red if the arm had not reached the engine (the case that would void the hold readings).

## Fixtures left in the instance

The probe uploads one folder per invocation and deletes it at the end (every report: `deletedFolder: 204`; a `PROPFIND` of the admin files root after the runs lists no `probe-10-14*` folder). Nextcloud's trash bin still holds the four folders of this run, each containing one `probe-10-14n-copy-16630.odt` (the owner's 60-page bytes, a copy), which can be emptied or deleted:

| folder (in the admin trash bin) | invocation |
|---|---|
| `probe-10-14n-20261014T181837` (`.d1792001948`) | Firefox control |
| `probe-10-14n-20261014T181913` (`.d1792002063`) | Firefox hold ×3 (one upload, three opens) |
| `probe-10-14n-20261014T182113` (`.d1792002096`) | Chrome control |
| `probe-10-14n-20261014T182142` (`.d1792002186`) | Chrome hold ×3 |

The trash bin also holds sixteen older `probe-10-14n-2026…` folders from earlier tasks, not ours to judge here. No other file was written to the instance. Nothing was saved from the editor in any run (`saves []`, `limit` null).

## Files

| path | what |
|---|---|
| `probe_10_14q.py` | the probe, unedited copy of the 10-14q one |
| `summarize_hold.py`, `summary-table.txt`, `self-test.txt` | the table and the verdicts, read from the raw reports; the self-test |
| `desk-readings.txt` | KWallet, process counts and load before the first run |
| `firefox-control/`, `firefox-hold/`, `chrome-control/`, `chrome-hold/` | per invocation: `report-host-<browser>-owner16630.json` (the raw report, each run's full engine/page log under `runs[].log`), `probe.out` (stdout, ends `rc=0`), `probe.err` (stderr, empty), `started-utc.txt`, `ended-utc.txt`, one end screenshot per run |
