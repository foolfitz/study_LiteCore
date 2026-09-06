# RESULT — 4b instrument-reproduction protocol on `39895d15…`

Executor: sonnet, task T1b of
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, running
`handoff/tasks/TASK-2026-09-06-4b-instrument-reproduction.md` as written.
Session date: 2026-09-06/07 (CST). This report supersedes the run's first
draft, which recorded a blocked session with zero walks; the desktop cleared
partway through the same session (see section 3) and two walks were run
before it closed again.

**Outcome: O-A. STOP-SUCCESS fired on the first pair attempted (arm A0,
setting X, the banked instrument as-is). The criterion of section 2.2 is met
at n = 10 -- every one of the ten visited paragraphs reached Orca's log in
both walks, `focusHeldEveryStop: true` in both, and both walks are VALID. Per
section 6's stop rule, no further arm was run: A0's setting Y
(`drive_walk_focus_noraise.py`) and arms A1-A3 were never attempted.** The
per-paragraph utterance counts show the named residue reproducing: `這一行是
普通內文` is spoken twice in both walks while every other paragraph is spoken
once. T1c is **not** run by this executor; that is the main session's call
per the task brief.

## 1. Identity gate (protocol section 1.3)

| check | expected | before Walk 1 (00:39 CST) | after Walk 2, before commit (00:48 CST) |
|---|---|---|---|
| (a) `build_cutover_page.py --profile e2-editor-v12` `pageSha256` | `39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e` | match | match |
| (b) served bytes, `curl \| sha256sum` | same as (a) | match | match |
| (c) `editor-shell-v2-bundle-v45.json` `bundleSha256` | `a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578` | match | match |
| (d) `pytest tests/test_e2_c_shell_bundle.py -k the_real_manifest_matches_the_real_tree` | pass | `1 passed, 11 deselected` | not re-run (tree unchanged: (a)-(c) unchanged, `git status --porcelain` showed only this evidence directory both times) |

`git rev-parse HEAD` throughout the walks: `09e596534184903bb5340407dab00d5d45327fb2`
(the commit that closed this task's first, blocked attempt). `git status
--porcelain` carried only this evidence directory, before and after.

## 2. The two walks

Both under arm A0, setting X (the banked instrument, unmodified, raises the
window once at start). Bounded slices at both ends per section 4.3.

| id | startedAt (UTC) | completedAt (UTC) | focusHeldEveryStop | announced | attach (`文件內容`) | verdict |
|---|---|---|---:|---:|---:|---|
| a0-raise-1 | 2026-09-06T16:41:33Z | 2026-09-06T16:43:32Z | true | 10 | 2 | VALID |
| a0-raise-2 | 2026-09-06T16:45:02Z | 2026-09-06T16:47:00Z | true | 10 | 2 | VALID |

Per-paragraph utterance counts, identical shape in both walks:

| paragraph | a0-raise-1 | a0-raise-2 |
|---|---:|---:|
| 這一行應該被唸成第一層標題 | 1 | 1 |
| **這一行是普通內文** | **2** | **2** |
| 這一行應該被唸成第二層標題 | 1 | 1 |
| 那一行也是內文 不過和上面每一行都不一樣 | 1 | 1 |
| • 清單開始了 這裡應該被唸成項目清單的第一項 | 1 | 1 |
| • 接下來這一項應該被唸成項目清單的第二項 | 1 | 1 |
| 夾在中間的這一行不是清單 只是普通內文 | 1 | 1 |
| 1. 編號的部分開始 這裡應該被唸成編號清單的第一項 | 1 | 1 |
| 2. 再來這一項應該被唸成編號清單的第二項 | 1 | 1 |
| 最後一行到了 整份文件到這裡結束 | 1 | 1 |

`這一行是普通內文` is doubled in both walks: once as its own paragraph
(step 1) and once again immediately after the second heading's announcement
(step 2) -- the exact residue shape described in the protocol's section 8.3
and in `orca-AFTER-THE-FIX-slow-dwell.log`. Both walks visited all ten
`a11y-node-0`..`a11y-node-9` refs in order (section 2.3's V6 check), and both
have `focusHeldEveryStop: true` with an empty `stopsWithoutFocus`.

Full speech payloads (every `SPEECH OUTPUT` line in the bounded slice, verbatim):

### a0-raise-1

```
00:41:33.408963 - SPEECH OUTPUT: '尚未開啟文件。'
00:41:38.586527 - SPEECH OUTPUT: '文件內容'
00:41:38.587356 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
00:41:38.587773 - SPEECH OUTPUT: 'heading 1'
00:41:45.910978 - SPEECH OUTPUT: '文件內容'
00:41:45.911651 - SPEECH OUTPUT: '這一行是普通內文.'
00:41:57.716252 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
00:41:57.716914 - SPEECH OUTPUT: 'heading 2'
00:41:57.839985 - SPEECH OUTPUT: '這一行是普通內文'
00:42:09.509085 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
00:42:21.335266 - SPEECH OUTPUT: 'List with 2 items'
00:42:21.335953 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
00:42:33.127655 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
00:42:44.940724 - SPEECH OUTPUT: 'leaving list.'
00:42:44.941669 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
00:42:56.770003 - SPEECH OUTPUT: 'List with 2 items'
00:42:56.771160 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
00:43:08.559665 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
00:43:20.371001 - SPEECH OUTPUT: 'leaving list.'
00:43:20.371818 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

### a0-raise-2

```
00:45:02.227646 - SPEECH OUTPUT: '尚未開啟文件。'
00:45:07.395044 - SPEECH OUTPUT: '文件內容'
00:45:07.395796 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
00:45:07.396229 - SPEECH OUTPUT: 'heading 1'
00:45:14.340219 - SPEECH OUTPUT: '文件內容'
00:45:14.340846 - SPEECH OUTPUT: '這一行是普通內文.'
00:45:26.137234 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
00:45:26.137801 - SPEECH OUTPUT: 'heading 2'
00:45:26.257401 - SPEECH OUTPUT: '這一行是普通內文'
00:45:37.943463 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
00:45:49.769225 - SPEECH OUTPUT: 'List with 2 items'
00:45:49.770144 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
00:46:01.550275 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
00:46:13.361949 - SPEECH OUTPUT: 'leaving list.'
00:46:13.362716 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
00:46:25.177100 - SPEECH OUTPUT: 'List with 2 items'
00:46:25.177886 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
00:46:36.978199 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
00:46:48.796752 - SPEECH OUTPUT: 'leaving list.'
00:46:48.797370 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

Every line in both slices is attributable to the candidate page or to Orca's
own vocabulary (protocol section 7.5's list); no foreign application is named
in either slice, so neither walk is a V5 environment void.

## 3. The environment history of this session

The first attempt (before this resumption) found two pre-existing Chrome
process families on the desktop -- an orphaned headless probe instance and
what the process evidence indicated was the owner's own browser -- and
stopped with zero walks, per section 4.1's precondition. That state, and the
bounded 310 s wait that failed to clear it, is preserved in the Execution
record's first entry rather than rewritten here.

The main session then reported (i) it had verified and terminated the
orphaned headless instance (PID 806014, `/tmp/wasm-sdk-probe-chrome-cearp5rb`)
and a stale candidate-page server pair on port 8801 (PIDs 923743/923744,
predating this task's dispatch), and (ii) the owner was being asked to close
their own browser. On the next check by this executor, `pgrep -x chrome` and
`pgrep -x google-chrome` both returned empty -- the owner's browser (PID
935754 and its children) was gone. The identity gate was re-run (section 1)
and Walk 1 started immediately. Both walks ran with exactly one top-level
Chrome process on the desktop throughout (checked before each walk's launch
per section 7.4, filtering out `--type=` child processes), and no `orca`
process other than this session's own was ever observed. Environment voids
this session: **0**.

Cleanup performed before the walks (section 7.6, this project's own debris):
`/tmp/wasm-sdk-probe-chrome-cearp5rb` (already removed by the time this
executor checked) and this executor's own per-walk
`/tmp/wasm-sdk-probe-chrome-v12c-a0-raise-*` directories and candidate-page
server mirror, all removed after use. Three other `/tmp/candidate-round-*`
directories, dated 2026-09-06 evening and predating both this task's dispatch
and the main session's message, were left untouched: this executor could not
verify which one (if any) corresponds to the port-8801 server named in the
main session's message -- the owning process had already exited before this
executor could inspect it, no log or trace in `/tmp` ties any of the three to
port 8801, and one of the three (`candidate-round-tx3ue8b9`) mirrors the
reverted v46 page (`e2-editor-app.js` sha256 `9b29e39b...`, matching
`orca-v46-9b29e39b.log` in the banked v12b evidence) rather than the current
candidate -- deleting it on a guess would risk destroying debris that is
still named in this protocol's own section 8. Per the instruction to "touch
nothing else in /tmp," these three were left in place.

## 4. What this means for T1c (not decided here)

Per the protocol's section 5, O-A means "4b's mechanical half is measurable
again on `39895d15…`" and that the heading-boundary residue (`這一行是普通
內文` spoken twice, at the second heading) is present and reproducing on the
candidate page -- which is what v46 targets. The settled configuration for
any T1c comparison is:

- **Arm:** A0
- **Setting:** X -- the banked instrument as-is (raises the window once, at
  start, before the walk)
- **Instrument file and sha256:** `drive_walk_focus.py`,
  `414f1245c8fd02056e52906d420c6e58bbe2046897749aa273282f7371f29813`
  (byte-identical to the banked file in `manual-round-v12b-20f09cc9/`)
- **Start order:** Orca started first (`Screen reader on.` confirmed in the
  log before Chrome was launched), consistent with every walk in this
  session
- **Orca lifecycle:** a fresh `orca` process per walk, no `--replace`, clean
  SIGTERM stop and `Screen reader off.` observed after each walk
- **Tab/process lifecycle:** a fresh Chrome process per walk, a fresh
  `--user-data-dir` per walk (`/tmp/wasm-sdk-probe-chrome-v12c-a0-raise-1`
  and `-2`), a single tab, no reuse across walks

**This executor does not decide whether T1c should run.** That decision, and
`AGENTS.md` sections 2/8, belong to the plan's main session.

## 5. Files in this directory

| file | status |
|---|---|
| `CONSENT.md` | written, protocol §1.4 |
| `drive_walk_focus.py` | executed twice, unmodified, sha256 recorded above |
| `drive_walk_focus_noraise.py` | staged for arm A0 setting Y, **not executed** (STOP-SUCCESS fired before it was needed) |
| `drive_walk_focus_noraise.diff.txt` | the one-line diff between the two instruments |
| `walk-a0-raise-1.json`, `walk-a0-raise-2.json` | the instrument's stdout, unedited |
| `walk-a0-raise-1.record.json`, `walk-a0-raise-2.record.json` | this executor's sidecars, per §1.6 |
| `orca-a0-raise-1.log.gz`, `orca-a0-raise-2.log.gz` | full Orca debug logs, gzipped; uncompressed sha256/size in the record JSONs |
| `orca-a0-raise-1.walk-slice.log`, `orca-a0-raise-2.walk-slice.log` | the bytes between the two walk bounds, uncompressed |
| `orca-a0-raise-1.walk-bounds.txt`, `orca-a0-raise-2.walk-bounds.txt` | START then END byte offsets |
| `orca-a0-raise-1.speech.txt`, `orca-a0-raise-2.speech.txt` | every `SPEECH OUTPUT` line of the slice |
| `RESULT-4b-instrument-reproduction.md` | this file |
