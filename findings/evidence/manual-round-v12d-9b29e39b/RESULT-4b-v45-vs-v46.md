# RESULT — 4b comparison, v45 against v46 (protocol §8)

Executor: sonnet, task T1c, opened by the main session on the settled
configuration from T1b's O-A result
(`findings/evidence/manual-round-v12c-39895d15/RESULT-4b-instrument-reproduction.md`).
Ruling: `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, section
"T1b: outcome O-A, and T1c is opened" (commit `69e5d9bc`). Session:
2026-09-06/07 (CST).

**Verdict: all three clauses of §8.3 are MET. No drift (§8.4). v46 measures
better than v45 on this protocol, on this page pair.** This executor does not
decide whether v46 lands; that is D1, the owner's decision, relayed through
the main session.

## 1. How v46 was obtained (§8.1)

Not reconstructed. `/tmp/candidate-round-tx3ue8b9/root/e2-editor-app.js`
(mirror built by the previous session on 2026-09-06 23:15) was verified
before anything else:

```
sha256sum /tmp/candidate-round-tx3ue8b9/root/e2-editor-app.js
9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c
```

matching the sha256 named in the banked `orca-v46-9b29e39b.log` and in the
plan's ruling. Preserved into this directory as `v46-e2-editor-app.js` before
anything else, per the instruction. `diff -u` against a freshly built v45
candidate page's `e2-editor-app.js` (`v45-to-v46.diff`, 27 lines) is **exactly
one hunk**: a comment block plus

```diff
-  const doubled = typeof text === "string" && structureSpeaks === text;
+  const doubled = structureSpeaks !== null;
```

No other hunk exists in the diff. This matches the plan's description
verbatim, so §8.1's requirement (obtain the edit, do not reconstruct it) is
satisfied by inspection rather than by trust.

## 2. How v46 was served

A fresh v45 mirror was built with `build_cutover_page.py`'s
`repointed_page()` (the same mechanism `serve_candidate_page.py` uses),
verified to be the unmodified v45 bytes (`39895d15…`), then **only**
`e2-editor-app.js` in that mirror's root was replaced with the preserved v46
bytes. Served with `web/serve.py --port 8766 --root <mirror>` directly (the
same static server `serve_candidate_page.py` launches internally), while the
unmodified v45 mirror kept serving on port 8765 throughout, untouched. No
file under `web/`, `dist/`, or any profile directory was edited; no
generation was frozen. This is a measurement, not a landing.

## 3. Identity gate

| check | v45 (port 8765) | v46 (port 8766) |
|---|---|---|
| page sha, from `build_cutover_page.py` / from the preserved file | `39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e` | `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c` |
| served bytes, `curl \| sha256sum` (checked before the first walk of each pair and again after the last walk of the session) | match, both times | match, both times |
| shell/generation terms (c)/(d) | `editor-shell-v2-bundle-v45.json` `bundleSha256` `a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578`, matches | **N/A by construction** -- "v45 tree + one substituted file (`e2-editor-app.js`)", not expected to match any manifest, as instructed |

`git rev-parse HEAD` throughout: `69e5d9bc5e1d5647d04930e30b0c7cc534fcd245`.
`git status --porcelain` carried only the two evidence directories
(`manual-round-v12c-39895d15/`, `manual-round-v12d-9b29e39b/`) at every check.

## 4. The six walks

Order: v45 pair, v46 pair, v45 return pair, per §8.4. No spares were needed --
all six walks were VALID on the first attempt, so none of the two spare
walks were used.

| id | page | focusHeldEveryStop | announced | 這一行是普通內文 | 文件內容 | verdict |
|---|---|---|---:|---:|---:|---|
| v45-pre-1 | v45 (`39895d15…`) | true | 10 | **2** | 2 | VALID |
| v45-pre-2 | v45 (`39895d15…`) | true | 10 | **2** | 2 | VALID |
| v46-1 | v46 (`9b29e39b…`) | true | 10 | **1** | 2 | VALID |
| v46-2 | v46 (`9b29e39b…`) | true | 10 | **1** | 2 | VALID |
| v45-return-1 | v45 (`39895d15…`) | true | 10 | **2** | 2 | VALID |
| v45-return-2 | v45 (`39895d15…`) | true | 10 | **2** | 2 | VALID |

All six walks visited all ten `a11y-node-0`..`a11y-node-9` refs in order
(§2.3's V6 check), had `focusHeldEveryStop: true` with empty
`stopsWithoutFocus`, and had no foreign speech line in their bounded slice
(§7.5) -- no V5 among the six. Environment voids this session: **0**. Exactly
one top-level Chrome process (filtering `--type=` children) was confirmed
before every walk's launch.

Per-paragraph utterance counts, every paragraph other than `這一行是普通內文`
was 1 in all six walks; only that one paragraph varies, and it varies exactly
with the page (2 on both v45 pages, 1 on both v46 walks). Full tables are in
each walk's `.record.json`.

## 5. Full speech payloads

### v45-pre-1

```
00:56:58.361636 - SPEECH OUTPUT: '尚未開啟文件。'
00:57:03.943204 - SPEECH OUTPUT: '文件內容'
00:57:03.944207 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
00:57:03.944685 - SPEECH OUTPUT: 'heading 1'
00:57:11.275585 - SPEECH OUTPUT: '文件內容'
00:57:11.276440 - SPEECH OUTPUT: '這一行是普通內文.'
00:57:23.097131 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
00:57:23.097745 - SPEECH OUTPUT: 'heading 2'
00:57:23.220218 - SPEECH OUTPUT: '這一行是普通內文'
00:57:34.865482 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
00:57:46.686327 - SPEECH OUTPUT: 'List with 2 items'
00:57:46.687167 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
00:57:58.482827 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
00:58:10.290657 - SPEECH OUTPUT: 'leaving list.'
00:58:10.291558 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
00:58:22.114011 - SPEECH OUTPUT: 'List with 2 items'
00:58:22.114985 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
00:58:33.898550 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
00:58:45.716039 - SPEECH OUTPUT: 'leaving list.'
00:58:45.716774 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

### v45-pre-2

```
00:59:57.691619 - SPEECH OUTPUT: '尚未開啟文件。'
01:00:02.868176 - SPEECH OUTPUT: '文件內容'
01:00:02.868826 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
01:00:02.869227 - SPEECH OUTPUT: 'heading 1'
01:00:10.201643 - SPEECH OUTPUT: '文件內容'
01:00:10.202303 - SPEECH OUTPUT: '這一行是普通內文.'
01:00:22.004607 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
01:00:22.005224 - SPEECH OUTPUT: 'heading 2'
01:00:22.128250 - SPEECH OUTPUT: '這一行是普通內文'
01:00:33.795805 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
01:00:45.618092 - SPEECH OUTPUT: 'List with 2 items'
01:00:45.618849 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
01:00:57.413952 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
01:01:09.235015 - SPEECH OUTPUT: 'leaving list.'
01:01:09.235883 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
01:01:21.037475 - SPEECH OUTPUT: 'List with 2 items'
01:01:21.038196 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
01:01:32.837499 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
01:01:44.646736 - SPEECH OUTPUT: 'leaving list.'
01:01:44.647481 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

### v46-1

```
01:03:01.122886 - SPEECH OUTPUT: '尚未開啟文件。'
01:03:06.280141 - SPEECH OUTPUT: '文件內容'
01:03:06.280733 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
01:03:06.281278 - SPEECH OUTPUT: 'heading 1'
01:03:13.234061 - SPEECH OUTPUT: '文件內容'
01:03:13.234668 - SPEECH OUTPUT: '這一行是普通內文.'
01:03:25.040436 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
01:03:25.041017 - SPEECH OUTPUT: 'heading 2'
01:03:36.828368 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
01:03:48.661218 - SPEECH OUTPUT: 'List with 2 items'
01:03:48.661986 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
01:04:00.456738 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
01:04:12.267306 - SPEECH OUTPUT: 'leaving list.'
01:04:12.268006 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
01:04:24.093440 - SPEECH OUTPUT: 'List with 2 items'
01:04:24.094450 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
01:04:35.868559 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
01:04:47.694649 - SPEECH OUTPUT: 'leaving list.'
01:04:47.695310 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

Note the absence of a second `這一行是普通內文` after `heading 2` -- this is
the shape §8.3's clause 2 asks for: the residue utterance simply does not
occur, rather than the whole paragraph going silent.

### v46-2

```
01:06:07.317329 - SPEECH OUTPUT: '尚未開啟文件。'
01:06:12.482774 - SPEECH OUTPUT: '文件內容'
01:06:12.483504 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
01:06:12.483971 - SPEECH OUTPUT: 'heading 1'
01:06:19.824181 - SPEECH OUTPUT: '文件內容'
01:06:19.824818 - SPEECH OUTPUT: '這一行是普通內文.'
01:06:31.615470 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
01:06:31.616049 - SPEECH OUTPUT: 'heading 2'
01:06:43.409831 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
01:06:55.248225 - SPEECH OUTPUT: 'List with 2 items'
01:06:55.248900 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
01:07:07.034389 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
01:07:18.861163 - SPEECH OUTPUT: 'leaving list.'
01:07:18.861815 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
01:07:30.668677 - SPEECH OUTPUT: 'List with 2 items'
01:07:30.669850 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
01:07:42.455373 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
01:07:54.268994 - SPEECH OUTPUT: 'leaving list.'
01:07:54.270104 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

### v45-return-1

```
01:09:06.034712 - SPEECH OUTPUT: '尚未開啟文件。'
01:09:11.213077 - SPEECH OUTPUT: '文件內容'
01:09:11.213792 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
01:09:11.214300 - SPEECH OUTPUT: 'heading 1'
01:09:18.151350 - SPEECH OUTPUT: '文件內容'
01:09:18.151962 - SPEECH OUTPUT: '這一行是普通內文.'
01:09:29.947361 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
01:09:29.947745 - SPEECH OUTPUT: 'heading 2'
01:09:30.067112 - SPEECH OUTPUT: '這一行是普通內文'
01:09:41.744870 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
01:09:53.567364 - SPEECH OUTPUT: 'List with 2 items'
01:09:53.567869 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
01:10:05.366245 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
01:10:17.176574 - SPEECH OUTPUT: 'leaving list.'
01:10:17.177057 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
01:10:28.996746 - SPEECH OUTPUT: 'List with 2 items'
01:10:28.997388 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
01:10:40.781350 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
01:10:52.606836 - SPEECH OUTPUT: 'leaving list.'
01:10:52.607673 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

### v45-return-2

```
01:12:04.298364 - SPEECH OUTPUT: '尚未開啟文件。'
01:12:09.483998 - SPEECH OUTPUT: '文件內容'
01:12:09.484910 - SPEECH OUTPUT: '這一行應該被唸成第一層標題'
01:12:09.485439 - SPEECH OUTPUT: 'heading 1'
01:12:16.429599 - SPEECH OUTPUT: '文件內容'
01:12:16.430389 - SPEECH OUTPUT: '這一行是普通內文.'
01:12:28.315531 - SPEECH OUTPUT: '這一行應該被唸成第二層標題'
01:12:28.324940 - SPEECH OUTPUT: 'heading 2'
01:12:28.565175 - SPEECH OUTPUT: '這一行是普通內文'
01:12:40.045097 - SPEECH OUTPUT: '那一行也是內文 不過和上面每一行都不一樣.'
01:12:51.859054 - SPEECH OUTPUT: 'List with 2 items'
01:12:51.859809 - SPEECH OUTPUT: '• 清單開始了 這裡應該被唸成項目清單的第一項.'
01:13:03.654540 - SPEECH OUTPUT: '• 接下來這一項應該被唸成項目清單的第二項.'
01:13:15.470955 - SPEECH OUTPUT: 'leaving list.'
01:13:15.471620 - SPEECH OUTPUT: '夾在中間的這一行不是清單 只是普通內文.'
01:13:27.289504 - SPEECH OUTPUT: 'List with 2 items'
01:13:27.290317 - SPEECH OUTPUT: '1. 編號的部分開始 這裡應該被唸成編號清單的第一項.'
01:13:39.083440 - SPEECH OUTPUT: '2. 再來這一項應該被唸成編號清單的第二項.'
01:13:50.878216 - SPEECH OUTPUT: 'leaving list.'
01:13:50.878805 - SPEECH OUTPUT: '最後一行到了 整份文件到這裡結束.'
```

## 6. §8.3's three clauses

| clause | requirement | v46-1 | v46-2 | met? |
|---|---|---|---|---|
| 1 | `announced == 10` on both v46 walks | 10 | 10 | **MET** |
| 2 | per-paragraph utterance count is 1 for every paragraph on v46, including `這一行是普通內文` | all 1s | all 1s | **MET** |

| clause | requirement | v45-return-1 | v45-return-2 | met? |
|---|---|---|---|---|
| 3 | the v45 return pair still shows `這一行是普通內文` at 2 | 2 | 2 | **MET** |

**§8.4 drift check:** the v45 return pair's `announced` (10, 10) and its
`這一行是普通內文` count (2, 2) both reproduce the first v45 pair's values
(10, 10 and 2, 2) exactly. **No drift.** The comparison is not void.

**All three clauses of §8.3 are met and there is no drift: v46 measures
better than v45 on this protocol.** This executor records that fact and does
not make a landing recommendation; D1 (whether to land v46, freeze generation
v47, and where) is the owner's decision.

## 7. Files in this directory

| file | status |
|---|---|
| `CONSENT.md` | written, quoting the three utterances the plan's ruling relies on |
| `v46-e2-editor-app.js` | the preserved v46 bytes, sha256 `9b29e39b…`, obtained per §8.1 |
| `v45-to-v46.diff` | the one-hunk diff verifying §8.1's premise |
| `drive_walk_focus.py` | copy of the settled instrument, sha256 `414f1245…`, for self-containedness |
| `walk-v46-1.json`, `walk-v46-2.json` | the instrument's stdout for the v46 pair, unedited |
| `walk-v46-1.record.json`, `walk-v46-2.record.json` | this executor's sidecars |
| `orca-v46-1.log.gz`, `orca-v46-2.log.gz` | full Orca debug logs, gzipped |
| `orca-v46-1.walk-slice.log`, `orca-v46-2.walk-slice.log` | bounded slices, uncompressed |
| `orca-v46-1.walk-bounds.txt`, `orca-v46-2.walk-bounds.txt` | START/END byte offsets |
| `orca-v46-1.speech.txt`, `orca-v46-2.speech.txt` | every `SPEECH OUTPUT` line of each slice |
| `RESULT-4b-v45-vs-v46.md` | this file |

The v45 pre-pair and return-pair evidence (`walk-v45-pre-*`, `walk-v45-return-*`
and their `orca-*` siblings) live in
`../manual-round-v12c-39895d15/`, per the walk plan.
