# Host 0.2.20: §10.7's host arms, first v20 runs (the §34.4 witnesses)

Task: `handoff/tasks/TASK-2026-10-14l-host-0.2.20-held-and-restore-window-arms.md`. Mechanical runs of existing probes, with the existing judge unchanged, on host 0.2.20. Nothing here changes a probe, judge, check or product file. The held and table judge runs are **expected red** under v19's rules: that red is the witness a later task needs before it may change the judge, and it is recorded here, not fixed. Facts only. Anything I did not check is marked "unverified", and inferences are labelled as inferences. Times are UTC (file mtimes on disk are local, UTC+8).

## Static (every report)

`static` and `staticAfter` of all three reports (checked by a script over the JSON, not by eye) are identical to each other and read:

- `hostVersion` 0.2.20, `hostCommit` `2ff30b5`, `hostDirty` `[]`;
- `buildId` `6cffc5960ebbbd98`;
- `servedPage` = `distPage` = `53019168651b6b4686f1baaba9aa75e0b566d02a3e2cc8a8e8ed4339f360bfd7`;
- `servedSession` `f47c80ec955397c44d7638da63ed6837a3dea47125f6e279192298c20ed62ba9`;
- `shellBundle` exit 0, manifest `e2/editor-shell-v2-bundle-v69.json`, sha256 `cdc20ef8…`, `problems` `[]`.

No round in any report has a `fatal`. The "stop and report" condition did not occur.

## H0 / desk

`health-checks.txt` holds a block before each step and one after H3: the wallet, a default-flag headless Chrome check, the process counts, the load average and "ours running". The helper scripts live in the session scratchpad, not in the tree; they wrote that file.

- `ddev occ app:list | grep litecore` → `litecore: 0.2.20` (2026-10-14T09:49:17Z).
- KWallet `Locked` (`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`) read `b false` at all five checks (H0, before H1, H2, H3, after H3).
- Default-flag Chrome check (`timeout 30 google-chrome --headless=new --user-data-dir="$(mktemp -d)" --dump-dom https://litecore.ddev.site:8443/login`): rc 0 and `Nextcloud` ×328, all five times.
- **The desk was not clean.** The owner's Chrome (pid 577918, started 2026-10-14 14:15 local, with the claude-in-chrome extension host), the owner's snap Firefox (pid 553880) and MarkText's crashpad handler were running for the whole task. I did not start, stop or touch any of them.

| time (UTC) | step | `pgrep -c chrome` | Chrome browser processes (`pgrep -fc '/opt/google/chrome/chrome( \|$)'`) | `pgrep -c firefox` | load average (1/5/15 min) |
|---|---|---|---|---|---|
| 09:49:44 | H0 | 34 | 31 | 1 | 1.53 1.53 1.58 |
| 09:49:54 | before H1 | 32 | 29 | 1 | 1.60 1.54 1.59 |
| 10:00:37 | before H2 | 34 | 31 | 1 | 2.39 2.52 2.09 |
| 10:09:46 | before H3 | 34 | 31 | 1 | 2.55 2.44 2.21 |
| 10:15:26 | after H3 | 31 | 28 | 1 | 1.91 2.32 2.25 |

- The load was 1.5–2.7 for the whole task. I did not find its source: `top` at 09:49 showed a `php8.4` process at 67% (not ours) and a `zen` browser process, and I did not look further. None of the judged criteria below is a latency gate, and I did not rerun anything on a quieter desk, so whether a quieter desk would change any number is unverified.
- "Ours running" read 0 at H0 and after H3. It reads 1 before H1, H2 and H3 only because the pattern matches the command line of my own wrapper that had just started the step (its arguments name the probe). Before each step I also ran `pgrep -af 'probe_|judge_'` by hand and nothing of ours was running.
- No `.git/index.lock` at any point before the commit.

## Commands and exits

Each probe ran with its default arguments (both browsers, the probe's default rounds), one job at a time, detached, with `probe.out` plus `started-utc.txt` / `ended-utc.txt` written by my wrapper (the wrapper's lines are the trailing `probe exit N` and those two files).

| step | command | window (UTC) | exit |
|---|---|---|---|
| H1 | `python3 findings/evidence/132/held-into-refusal/probe_held_into_refusal.py --out findings/evidence/link-batch/host-0.2.20/held` | 09:49:55–09:59:59 | 0 |
| H2 | `python3 findings/evidence/134/table/probe_table_refusal.py --out findings/evidence/link-batch/host-0.2.20/table` | 10:00:37–10:09:34 | 0 |
| H3 | `python3 findings/evidence/134/restore-window/probe_restore_window.py --out findings/evidence/link-batch/host-0.2.20/restore-window` | 10:09:47–10:14:20 | 0 |
| H4 (held) | `python3 findings/evidence/132/held-into-refusal/judge_held_into_refusal.py findings/evidence/link-batch/host-0.2.20/held/report.json --page 53019168651b6b4686f1baaba9aa75e0b566d02a3e2cc8a8e8ed4339f360bfd7` | 10:00 | **1**, `verdict FAIL (30)` (`held/judge-output.txt`) |
| H4 (table) | same judge, `table/report.json`, same `--page` | ~10:10 | **1**, `verdict FAIL (12)` (`table/judge-output.txt`) |

- Rounds: held = 6 per browser (`start-press` 1, `start-hold` 2, `end-hold` 2, `end-press-type` 1), 12 runs; table = 6 per browser (the four 1-round arms plus `cell-start-hold` 2), 12 runs; restore-window = 3 per browser, 6 runs. Hold arms hold the key 8 s (`holdMs` 8000, delay 500 ms, interval 30 ms; `deskRepeat` read back as delay 500, repeat-interval 30, repeat true).
- The judge cannot read the restore-window report (`report["probe"]` must be the held or the table probe), and G5 did not judge it either, so H3 has no judge output; it is read as `findings/evidence/136/guard-r2/README.md` §G5 read it (below).
- The per-run `h5-facts.txt` in each directory is the output of a one-off reader script (session scratchpad, not kept in the tree) over `report.json`. The numbers in this README were read from `report.json` and from those outputs; the extra per-hold numbers (time from the last repeat keydown to the first `ready` entry; the restore-window timing columns) come from a second one-off script over the same files.

## The two expectations

**v19's** is the judge's own `RULES` (`findings/evidence/132/held-into-refusal/judge_held_into_refusal.py`), quoted verbatim:

```
"start-press": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
"start-hold": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
"end-hold": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("end", "last"), mark_then_after, scroll_end),
"end-press-type": all_of(one_reopen, document_kept, counts(1, 1, 0), control_at("last"), mark_at_end, contiguous, scroll_end),
"cell-start-hold": all_of(one_reopen, stage_is("nothing-selected"), document_kept, counts(0, 0, 1), after_at("start", 1)),
```

with `one_reopen` = exactly 1 refusal, generations `['1', '2']`, no limit notice; `scroll_end` = from the first `restart-required` sample to the end of the log every `scrollTop` ≥ 0.5 × the last sample before the refusal (and the rule FAILs if there is no `restart-required` sample); `stage_is("nothing-selected")` = the refusal stage read from the page's toast. The other table arms' rules (`before-table-*`, `cell-press-type`, `cell-hold`) are also `one_reopen` plus placement. `restore-window` has no judge rule; its v19 expectation is `../../134/restore-window/README.md`'s prediction: refusals 1, generations `['1','2']`, `marks == 1`, mark in paragraph 210, rest unchanged.

**C's** is `specs/SPEC-M3-link-batch.md` §10.7, five properties: (1) 0 refusals; (2) generations `['1']`; (3) the document unchanged; (4) the caret unchanged; (5) the typed marker at the caret.

How I read C's properties against what the probes record (a limit of the instruments, not a result):

- (1) and (2) are measured (`summary.refusals`, `summary.generations`).
- (3) is measured by the server read-back: the saved document, with the three marks stripped, equals the original (`sameAsOriginal` true, `charDelta` 0), and the mark counts equal what the arm typed.
- **(4) is not measured directly.** No probe records a caret offset or rectangle: the reports carry the `placed` / `moved` results (a latency label and revisions) and nothing about where the caret is. "Caret before" below is therefore what the arm did to put it there (click, Home/End, typed text), and "caret after" is **inferred** from (5).
- (5) is measured as paragraph indexes and booleans (`afterParagraphs`, `afterAtStart`, `markThenAfter`, `controlThenMark`, …). (4) and (5) rest on the same read-back; I did not find an independent read of the caret.

## H5 — per-arm table

Chrome and Firefox read the same on every field below unless a cell says both numbers. "v19" = the judge's verdict for that arm; "C" = §10.7's five properties; "(i)" = inferred, not measured.

### Held probe (`held/`)

| arm (rounds/browser) | refusals, stage | generations | document read back | where the marker landed | caret before → after | toasts | `scrollTop` | v19 (judge) | C (§10.7) |
|---|---|---|---|---|---|---|---|---|---|
| `start-press` (1) | 0 (`refusalsMs` `[]`; stage not applicable) | `['1']` | original + `zqx` + `wvy`; `sameAsOriginal` true, `charDelta` 0, 211/211 paragraphs, marks 1 / controls 0 / afters 1 | `wvy` in paragraph 0 only, at its start (`afterAtStart` true); `zqx` in paragraph 1 (typed earlier, mid-text) | before: document start (click on the first line, then Home). After (i): document start; Backspace was a no-op (revision 3 → 3 across the key; label 「⌫ 刪除 2260 ms」 Chrome, 2258 ms Firefox) | none (`toasts` `[]`) | 0 throughout (series `[0]`) | **FAIL**: `refusals 0 != 1`; `generations ['1'] != ['1', '2']`. `document_kept`, `counts`, `after_at`, `scroll_start` pass | meets all five (4 by inference) |
| `start-hold` (2) | 0 in all 4 runs | `['1']` | original + `zqx` + `wvy`; `kjkjk` fully gone (controls 0), `sameAsOriginal` true, `charDelta` 0; revision 8 → 13 during the hold (the five deletes) then 16 after `wvy` | `wvy` in paragraph 0 only, at its start | before: document start, five letters `kjkjk` just typed there. After (i): document start | none | 0 throughout | **FAIL** ×4: same two lines as `start-press`; the rest pass | meets all five (4 by inference) |
| `end-hold` (2) | 0 in all 4 runs | `['1']` | original + `zqx` + `wvy`; `sameAsOriginal` true, `charDelta` 0 | `zqx` and `wvy` both in paragraph 210 (the last), `zqxwvy` contiguous (`markThenAfter` true), `wvy` at the paragraph end (`afterAtEnd` true) | before: end of the last paragraph (click on the last line, End), `zqx` typed. After (i): still right after `zqx` at the end of paragraph 210 | none | Chrome 21504 before the key, constant through the hold, then 21620 from an entry 3.9–5.4 ms after the `ready` entry of the second typed letter (`v`, revision 5) in all four runs; Firefox 21490, then 21606 at the same point. Never below the pre-key value | **FAIL** ×4: `refusals 0 != 1`; `generations ['1'] != ['1', '2']`; `scrollTop: no restart-required sample`. The other rules pass | meets all five (4 by inference) |
| `end-press-type` (1) | 0 | `['1']` | original + `kj` + `zqx`; `sameAsOriginal` true, `charDelta` 0, marks 1 / controls 1 / afters 0 | `kj` and `zqx` both in paragraph 210, `kjzqx` contiguous (`controlThenMark` true) | before: end of the last paragraph, `kj` typed. After (i): after `kj` at the end of paragraph 210 (the label after the key is 「⌦ 前刪 2263 ms」 Chrome, 2258 ms Firefox; revision unchanged by the key) | none | 21504 (Chrome) / 21490 (Firefox) throughout | **FAIL** ×2: `refusals 0 != 1`; `generations ['1'] != ['1', '2']`; `scrollTop: no restart-required sample` | meets all five (4 by inference) |

### Table probe (`table/`)

| arm (rounds/browser) | refusals, stage | generations | document read back | where the marker landed | caret before → after | toasts | `scrollTop` | v19 (judge) | C (§10.7) |
|---|---|---|---|---|---|---|---|---|---|
| `cell-start-hold` (2) | 0 in all 4 runs; `refusalStage` `{"stage": null, "stages": []}` | `['1']` | original + `wvy`; `kjkjk` fully gone; `paragraph1IsAfterThenOriginal` true, `sameAsOriginal` true, `charDelta` 0, 6/6 paragraphs; revision 5 → 10 during the hold (five deletes), 13 after `wvy` | `wvy` at the start of paragraph 1 (cell A1) only (`afterParagraphs` `[1]`, `afterAtStart` true, `paragraph1StartsWithAfter` true) | before: start of cell A1 (ArrowDown, Home), `kjkjk` typed there. After (i): start of A1 | none | 0 throughout (the table arms are exempt from the scroll rule; the series is printed) | **FAIL** ×4: `refusals 0 != 1`; `generations ['1'] != ['1', '2']`; `refusal stage None: measures that stage, not D`. `document_kept`, `counts`, `after_at` pass | meets all five (4 by inference) |

### The four other table arms (not on §10.7's list; they still refuse on v20)

These arms are not at the document start or end, and §10.7 does not list them. They still meet v19's expectation exactly: the judge reads **PASS** for all eight runs (4 arms × 2 browsers).

| arm | refusals, stage (Chrome / Firefox) | generations | document | marker | toasts |
|---|---|---|---|---|---|
| `before-table-press-type` | 1, `key-posted` / 1, `key-posted` | `['1','2']` | `sameAsOriginal` true, `charDelta` 0 | `kj` + `zqx` contiguous in paragraph 0 | 「這一下刪除送出了，但沒能確認它做了什麼，正在重新載入…」, then 「…已重新載入。請看一下那個位置：這一鍵可能生效了，也可能沒有。」 |
| `before-table-hold` | 1, `key-posted` / same | `['1','2']` | same | `wvy` at the end of paragraph 0 | same two toasts (plus 「已開啟 probe-held-refusal.odt」) |
| `cell-press-type` | 1, `anchor-mismatch` / same | `['1','2']` | same | `kj` + `zqx` contiguous in paragraph 1 (cell A1) | 「這裡目前還不能這樣刪除。文件沒有被改動，正在重新載入…」, then 「…已重新載入。緊接在這一鍵前後打的字可能沒有打進去，請看一下。」 |
| `cell-hold` | 1, `anchor-mismatch` / same | `['1','2']` | same | `wvy` at the end of paragraph 1 | the `anchor-mismatch` toasts (plus 「已開啟 …」) |

From `specs/SPEC-M3-link-batch.md` §4.4 / §10.5, C's no-op covers only a merge-key barrier that stops at `nothing-selected` with `keyPosted === false`. The `key-posted` and `anchor-mismatch` stages here are other exits; that they still refuse is consistent with that text. I read the spec text; I did not read the engine source, so whether the engine does exactly this is unverified.

### H3 — restore-window (`restore-window/`), read the way `136/guard-r2/README.md` §G5 read it

The arm is named `end-press-type-fast` in the report. v19's expectation (G5's criterion): every round 1 refusal, generations `['1','2']`, `marks == 1`, mark in paragraph 210, rest unchanged, and `scrollTop` never 0.

| browser | round | refusals | generations | `scrollTop` over the 10 state entries | `marks` / paragraph | rest of document | toasts |
|---|---|---|---|---|---|---|---|
| chrome | 0 | **0** | `['1']` | 21504 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 | 「已開啟 probe-held-refusal.odt」 only |
| chrome | 1 | 0 | `['1']` | 21504 in all | 1 / 210 | same | same |
| chrome | 2 | 0 | `['1']` | 21504 in all | 1 / 210 | same | same |
| firefox | 0 | 0 | `['1']` | 21490 in all | 1 / 210 | same | same |
| firefox | 1 | 0 | `['1']` | 21490 in all | 1 / 210 | same | same |
| firefox | 2 | 0 | `['1']` | 21490 in all | 1 / 210 | same | same |

- **v19 expectation: not met in 6 of 6 rounds** (refusals 0 not 1, generations `['1']` not `['1','2']`). `marks == 1` in paragraph 210 and the unchanged rest do hold.
- **C expectation: met in 6 of 6** (0 refusals, `['1']`, document unchanged, marker in paragraph 210, which is where the caret was left: End on the last line; (4) by inference).
- **The arm no longer measures a window.** The probe presses Delete once, then polls `#s-generation` for a change for at most 20 s, then types. There is no generation change, so every round polled to the deadline (`polls` 965 / 965 / 966 Chrome, 898 / 901 / 902 Firefox) and the first typed key came **20.01–20.02 s after the Delete keydown** (keys at +20009 to +20149 ms, 50–70 ms apart). G5's keys were typed +6.5 to +132 ms after the new generation's `ready`. So a pass of `marks == 1` here says nothing about typing during a restore window; it says the typed text landed at the end of the last paragraph 20 s after a no-op Delete. (`genSeenAt` in the report is the time the poll gave up, not a generation change.)
- `scrollTop` never went to 0 and never changed (a single value per round, 21504 Chrome / 21490 Firefox). The probe takes no `stateBeforeKey` sample, so the first sample is the entry 1 ms after the Delete keydown.
- The no-op Delete: the session went `busy` 1 ms after the keydown and back to `ready` about 2.26 s later (Chrome 4995.9 − 2733.0 = 2262.9 ms in round 0; the label reads 「⌦ 前刪 2263 ms」 Chrome, 2257–2258 ms Firefox), revision unchanged until the first typed letter, then 0 → 3 for `zqx`. §10.5 names this cost ("在文件開頭按 Backspace，約 2.25 秒才回應"); the spec says document start, and the same figure shows here at the document end with Delete. I did not check why.
- No caret-back time exists to report (no restore happens).

## Anything odd, and what was not checked

- **No arm meets neither expectation.** Every `held` / `cell-start-hold` / restore-window arm meets C's five properties (property 4 by inference), and the four non-listed table arms meet v19's. So I have no candidate finding from this task. The facts that look like findings but are not, as the main session may want them:
  - after the key is released, the page stays `busy` for 3.0–4.3 s before the first `ready` entry (time from the last repeat keydown): held Chrome `start-hold` 4030 / 4031 ms, `end-hold` 3287 / 3287; Firefox `start-hold` 3737 / 3708, `end-hold` 3032 / 3006; table `cell-start-hold` Chrome 3972 / 3970, Firefox 3740 / 3732 (and the four old table hold arms 4205–4298, which refuse). The probes settle before typing `wvy`, so the judged properties do not depend on it. §10.5's named cost is about the first no-op (~2.25 s); the labels in the hold read 「⌫ 刪除 4510 ms」 / 「⌦ 前刪 4487 ms」 at the end. I did not check whether this is the designed behaviour: unverified.
  - during each hold the page logged 251 repeat keydowns, and in the held probe's `start-hold` / `end-hold` and the table's `cell-start-hold` all 255 keydowns were `focus: sink` with `sinkDisabled` false, while only 13 (`start-hold`, `cell-start-hold`) or 8 (`end-hold`) `beforeinput` events were logged per run (these include the three typed `wvy` letters, so 10 or 5 came from the held key); the other repeats produced no `beforeinput` (page behaviour, not looked into). In the four old table hold arms that still refuse, 191–234 of 255 keydowns reached the sink, as the sink is disabled during the reload.
  - `end-hold`'s `scrollTop` rises by 116 px (Chrome) / 116 px (Firefox) on typing the second letter (`v`) after the hold. It looks like the paragraph growing (unverified), is far above 0.5 × the pre-key value, and is not a restore excursion.
- **`probe-held-refusal.odt` is still on the instance** in the `admin` files (567233 bytes, checked by `GET` / `PROPFIND` through the probes' own `Instance` helper after H3 had ended). The held, table and restore-window probes all upload under that name and none of their `main()` functions removes it afterwards (I read the three `main()` functions: `clear_locks` is called in `finally`, nothing deletes the file; `Server.teardown` exists in `check_m3_locks.py` but is not called). Its content is the last round's end state. I left it, because deleting files on the instance was not in the task. Earlier probe files (`probe-hand-0212.odt`, `probe-autosave-m1.odt`, `probe-autosave-m3.odt`) and the owner's own files are also there and were not touched. The task text says the probes "remove their own files"; for this one file that did not happen.
- The judge's red lines under C, as a witness for the later task, are exactly: `one_reopen` (refusals and generations) on every held / `cell-start-hold` run; `scroll_end` ("no restart-required sample") on `end-hold` and `end-press-type`; `stage_is("nothing-selected")` on `cell-start-hold`. No other rule is red: `document_kept`, `counts`, `after_at`, `mark_then_after`, `mark_at_end`, `control_at`, `contiguous` and `scroll_start` pass on all of them. I did not run any mutation of the judge or check how it behaves on a made-up member; that is the later task's work.
- Not checked: the caret by any independent read (see above); a rerun on a quiet desk; Orca or any screen-reader path; the host-segment arms (not in this task); whether `servedPage` matched under gzip and zstd (the task states it; the probes read the served page once per report, and that read equals `distPage`).
- Not done, by instruction: no `make`, link, freeze, `--write`, `package_m3_engine.py`, `ddev occ upgrade`; no edit of any tool, judge, probe, check, `web/`, `editor-shell*/`, `sdk/` or `src/`; nothing changed in `~/Projects/Nextcloud_Apps/litecore` (host HEAD `2ff30b5`, `git status --short` there empty at 10:16Z). No `git push`.
- Files in each step directory: `report.json`, `probe.out`, `started-utc.txt`, `ended-utc.txt`, `h5-facts.txt` (and `judge-output.txt` for held and table). `health-checks.txt` sits one level up in this directory.

## Appended 2026-10-14 (task 10-14m): the judge's expectation under C, with this directory as the §34.4 witness

**§34.4: repaired because of execution, +1 — `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py` (sha256 `b0ed5fa050a8d5c4…` → `67c9e763e04225e5…`); witness: this directory (`held/judge-output.txt` `FAIL (30)`, `table/judge-output.txt` `FAIL (12)`, every red line on `one_reopen`, `scroll_end`'s "no restart-required sample" or `stage_is("nothing-selected")`, on an engine that ships C). Repaired because of audit: 0.** The restore-window probe was not changed. Full write-up, re-judge and red cases: `re-expectation/README.md`.

- **Keying**: the precedent's rule (10-14i, the engine-emitted fragment `,"completion":"verified-boundary-noop"` read from the bytes that ran), reached through the identity these reports carry: `static.buildId` → the archived engine package `wasm_sdk_probe/build/archive/host-*-engine-<buildId>/` (recomputed buildId, page hash = `servedPage`, wasm sha256 = manifest) → the fragment. No package or any mismatch: `FAIL engine: …`, nothing judged. Only `host-0.2.20-engine-6cffc5960ebbbd98` declares C; 0.2.8–0.2.18 are all `e2-editor-v19`.
- **C rules** (`RULES_C`, the five §10.7 arms only): `no_reopen` (0 refusals, `['1']`, no limit notice, no reopen toast) replaces `one_reopen`; `scroll_kept` (from `stateBeforeKey` > 0 to the end of the log, every sample ≥ 0.5 × it) replaces `scroll_end` on the end arms; `stage_none` replaces `stage_is("nothing-selected")` on `cell-start-hold`; `document_kept`, the counts and the placement rules unchanged. The four other table arms keep `RULES` (they still refuse on v20: 8/8 PASS here).
- **This directory under the edited judge**: `held` PASS (12/12 runs), `table` PASS (12/12). **The 13 committed v19-era reports**: verdict and every line unchanged (`re-expectation/rejudge-output.txt`).
- **restore-window**: retired on C profiles as "nothing to guard" (AGENTS.md §3): D's restore runs only inside `reopenAfterBoundaryRefusal`, which only an error enters; C's exit is a completion. What it would assert on C is `end-press-type`'s C rule, already judged. A report of this probe on a C profile is recognisable by `refusals` 0, `['1']`, `polls` at the 20 s deadline; G5's criterion must not be read against it.
- **The 3.0–4.3 s busy tail after release**: an instance of §10.5's named cost (one no-op = 250 + 2000 ms in the engine; 2257–2322 ms measured alone) composed with H2's depth 2 (SPEC-M3-held-key §3.2): at release one no-op is running and one queued, so the tail is in [2.25, 4.5] s; every queued no-op's label reads 4479–4518 ms; Chrome `end-hold` r0 worked from the log: sends at 0/500/2270/4520/6800 ms, completions 2.26 s apart, the fifth at 11288 ms, release at 8000 → 3287 ms. 12/12 holds in the band. Not a new limit, not a finding; one stale owner-facing sentence in SPEC-M3-held-key §3.2 ("約 0.13 秒") is noted for the main session.
- **Red cases**: a doctored v20 refusal / scroll-0 / stage-read is red under C on exactly that clause; 0.2.18's reports forced under C are red on every §10.7 arm; the v20 reports forced under the refusal reproduce this directory's outputs; the v20 report keyed on the 0.2.18 package, and a package with 0.2.20's manifest over 0.2.18's wasm, both `FAIL engine`, nothing judged.
