# check_m3_autosave.py — shakedown on host 0.2.13 (2026-10-12)

Host `litecore` 0.2.13 (source `f0e3464` + `appinfo/info.xml` 0.2.13, not yet committed when these ran), engine package buildId `0574b1b157ce1e1e` (vs 0.2.12's `45cdcedf…` only `e2-editor-app.js` differs), page `c7f904fa…` (web/ = dist/ = served), shell generation v62 NOT frozen. Not counted: the runner's pins were `None`.

| Report | Runner | What |
|---|---|---|
| `2026-10-12T054150+0000.json` (+ `.out`) | `7be150b9` | Chrome, `as2-key` + `as4a`, once each. `as2-key` PASS; `as4a` FAIL on its premise only: `insert()` stopped as soon as the latency line held any 「失敗」, and the auto save before it (which wrote the conflict copy) had left 「自動存回 失敗」 there. Every AS-4(a) clause held in the record. **Witness** for `afeef717` (the insert's own 「插入文字 失敗」 only). Re-scored after the fix: both PASS. |
| `2026-10-12T054605+0000.json` (+ `.out`, `.red-cases.txt`) | `afeef717` | All 12 arms, both browsers where planned, once each (23 runs, 05:46–06:19Z). 21 PASS, AS-1 PASS (29 auto records, every one with `conditions`, every item held). `as2-toolbar` FAIL in both browsers on the reader: its reference was the LAST mutation of `#s-revision`, and the page rewrites the same value many times; the last rewrite came during the auto save. **Witness** for `f6e1706a` (the time the revision last took a new value). Re-scored after the fix: `VERDICT clean`. `--red-cases` on it: 76 of 76 red (38 cases × their browsers). |

§34.4 ledger from these two: 因執行而修 7 → 9 (two reader fixes, each with its committed witness); 因審核而修 unchanged (5).

## Numbers (full shakedown, one run per cell)

| Cell | Chrome | Firefox |
|---|---|---|
| AS-2 key: first auto − last keydown | 30.22 s | 30.19 s |
| AS-2 toolbar: first auto − the revision's change | 30.22 s | 30.21 s |
| AS-2h: hidden after the key / auto after hidden | 1.51 s / 0.20 s | 1.55 s / 0.18 s |
| AS-2c: keying span / auto after the last key / autos | 308 s / 3.21 s / 1 | 308 s / 3.18 s / 1 |
| AS-3, AS-4(a): auto outcomes | copy, saved → the copy | copy, saved → the copy |
| AS-4(c): PUTs on the wire (If-Match, If) | original `(etag, If)` → 412; copy create `(none, none)`; copy save `(copy's etag, none)` | not read (Chrome only) |
| AS-5: letters during the auto (sent / on the server) | 20 / 20 | 20 / 20 |
| AS-5 held: sent / on the server / 「有字沒有輸入」 toasts | 45 / 33 / 12 | 45 / 34 / 11 |
| AS-6(b): leave after the auto copy | not asked, copy = the auto's bytes | same |
| AS-7: auto outcomes | stranded, stranded, saved | — |

The pill went `busy` for the auto's engine part 30.0–30.1 s after the key in every AS-5 run (the fixture of those arms is the owner's document).

## Against the predictions written before implementation (spec §9.6)

- AS-2 "starts 30.6–31.5 s after" — **missed**: 30.19–30.22 s. The prediction added the engine part to 30 s, from M2's owner-document numbers; the host record's `at` is when the host part begins, and on this small fixture the engine part is short. The criterion's window [30.0, 35.0] is unaffected.
- AS-5 0 lost; held key loses 8–14 with a toast each time — held: 0 lost; 12 and 11 lost, one toast per lost key.
- AS-4(a) exactly one copy; AS-4(c) the copy PUT carries no `If` — held.
