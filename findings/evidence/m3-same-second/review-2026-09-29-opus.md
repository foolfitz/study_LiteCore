## SUMMARY

Adversarial review (opus, read-only) of the D step: R2/R3 criteria (SPEC-M3-versions §4/§5/§6), `check_m3_same_second.py`, host 0.2.2 diff (uncommitted, on `5e53362`), red evidence on 0.2.1, and the 0.2.2 shakedown `2026-09-29T032619+0000.json` (complete, clean). Tags: [source] read in code, [report] read from a JSON report, [scorer] ran the runner's own scoring offline (on copies), [inference] reasoned, not measured.

1. [BLOCKING before counted run] Host: the read-back can throw out of `put()`. `check.sha256 = await hex(await read.arrayBuffer())` (litecore-editor.js:375) is outside `send()`'s catch. If the body fails mid-read, `save()` rejects with a bare TypeError. That happens on a network drop, or on a Content-Length mismatch when a write lands during the GET (103 measured in-place writes). The result: no copy, not stranded, no download button, and no leave guard. The page has no beforeunload of its own, and `inFlight` is back to 0. 0.2.1 kept the locks spec's "every failed save has a way out"; this breaks it. [source] [inference: reachability]
2. [BLOCKING before counted run] Condition 7 cannot re-run R1 "unchanged": `check_m3_versions.py:54 HOST_COMMIT = "5e53362"` is enforced in strict mode (:296-297), so any 0.2.2 commit scores `VERSIONS NOT CORRECT`. The asset-delivery step hit the same pin and wrote "re-point it; a binding, not a criterion" down first (SPEC-M3-asset-delivery.md:179). Nothing says so for 0.2.2. Write it before the run, or the edit will be a test fix after a red. [source]
3. [SHOULD FIX] Red cases leave sub-clauses unguarded. Deleting any one of these from the scorer leaves all 49 cases red on the clean 0.2.2 report: (b) row order; (c) "Lc lacks S1..S22"; (c) extra row; (c) exactly-one-current; R3 "F, X, S1, S2 distinct"; R3 host lock state; on_wire's If-Match compare, PUT count, LOCK-before-GET. "(c) lacks S1..S22" is the substantive one. On 0.2.1 it only fired entangled with (b) (the spec says so), and the only (c) loss case removes S23. [scorer]
4. [SHOULD FIX] R3 never asserts its mechanism. S2's attempts and the Chrome wire go unchecked, so each of these scores clean as long as the file still holds X: S2 = `[(412, True)]` (plain If-Match), an extra PUT on the wire, or S2 = `['changed', 204]`. The shakedown did go through the compare: 4/4 `changed`, and on the Chrome wire only S1 and the copy were PUT. Add S2 == `[('changed', True)]` and, on Chrome, exactly one PUT to the file. [scorer] [report]
5. [SHOULD FIX] §5 "比對的 GET 距那次寫入 ≥ 1 秒，之後落地的寫入 ETag 一定會換" is too strong, and it is inference. R3 only measures X landing *before* the GET. The mechanism: Local ETag = md5(mtime.ino.dev.size) (Local.php:538-561), reused on equal storage_mtime (Scanner.php:174-183). So a writer that sets the mtime keeps the ETag and is overwritten, if it is same size, in place, after the check GET, and sets the mtime to the host's second. Two such writers: `X-OC-Mtime` (File.php:358-363), and a restore of the current-mtime row, which §5 already names. Narrow and unmeasured, but it is not 一定. [source] [inference]
6. [SHOULD FIX] Condition 2 bookkeeping. The §6 row names only R2 and the 104 bullet. These are not logged: R3, the 103-bullet correction, the (c) "同日補" paragraph, and the post-shakedown note. R3 and the (c) paragraph first appear in 2e473813, with the runner and both 0.2.1 shakedowns (03:12Z, 03:18Z; commit 03:25Z). Git therefore can't show "先於 runner…" or "仍在任何執行之前". §3 still says "宿主的行為：不改" and "103 在宿主這一側關不掉". [source]
7. [NOTE] Q1:
   - (a) is vacuous for non-2xx saves, but shape closes that: every save must be one 204 attempt.
   - (b) does imply distinct mtime seconds. There is one version row per mtime second (FileEventsListener.php:326-352 updates instead of creating), so a same-second pair can't leave both bytes readable.
   - Expiry can only fake a loss, never hide one, and ajax cron doesn't run between the first pair and Lc.
   - Phase control is sound (one kernel clock) and irrelevant to 0.2.2: every second-of-pair PUT waited 879–995 ms, send gaps 1063–1183 ms. [source] [report]
8. [NOTE] The spacing argument holds for writers that stamp real time: m(P1) ≤ answer(P1) and send(P2) ≥ answer(P1) + 1000 ms (monotonic) put P1 and P2 in different seconds. Two caveats. It relies on the page serialising saves; the host doesn't serialise concurrent `save()` calls. And Firefox resistFingerprinting's 100 ms `performance.now()` can shrink the gap to ~900 ms. [source] [inference]
9. [NOTE] The ETag format agrees: `check.etag == ifMatch` in all 100 attempts of the 0.2.2 shakedown (OC-ETag on GET and PUT, `afterMethod:*`), so a gzip suffix can't split them. A refresh LOCK and lock expiry don't move the ETag (LockService.php:160-190, 335-340). GET is not blocked by other users' locks (LockWrapper.php:74-76). [report] [source]
10. [NOTE] Q4: apart from item 2, nothing in locks/versions/assets/host-entry is turned red or blinded by the wait or the read-back. The check lives inside the attempt, so there is still one attempt per PUT. on_wire counts only PUTs and orders only the first GET. SAVED accepts any number of ms. The expired/broken arms keep their shapes, with a ~1 s pause. Assets never saves; only K0-6 touches the fix (js and info.xml must be in one commit). [source]
11. [NOTE] On the red 0.2.1 base, cases for clauses that already fire there (R3 kept/copy/page) pass only because the message text changed, so they prove nothing "before the fix". The harness also accepts a red base, where check_m3_locks SKIPs one. The informative run is 49/49 red on the clean 0.2.2 shakedown; cite that one, and re-run on the counted report. [scorer]
12. [NOTE] Condition 8: `build_m3_release.py` rewrites `findings/evidence/m3-install/release.json` in place. That file is what `host_binding` compares litecoreprobe (still 0.2.1) against, so a "record only" 0.2.2 build makes that instance read as dirty from then on. Keep the 0.2.1 record. [source]
13. [NOTE] Smaller points:
    - The written prediction was "about 7 of 10 pairs same-second on 0.2.1"; the runs gave 9/8/9/8. Register the miss.
    - `admission()` pools 46 saves per browser; the spec says 23.
    - The R3 entry condition holds on a 9.5 KB fixture only (GET median 23/24 ms vs PUT 46/46.5 ms), yet the read-back downloads the whole document before every save.
    - A 1 s held Ctrl+S now holds the leave guard for ~33 s. [report] [scorer]

## What was run (offline only)

- `check_m3_same_second.py --score` on `shakedown/2026-09-29T031828+0000.json` (0.2.1): red, every R2 run in (a)(b)(c)+`(c) 104`, every R3 run in kept/copy/page, premise held 4/4. On a scratch copy of `2026-09-29T032619+0000.json` (0.2.2): `clean`, 8/8 runs. Entry condition: Chrome GET 23 / PUT 46 ms, Firefox 24 / 46.5 ms.
- `--red-cases` on both: 49/49 red on each.
- Clause-deletion experiment (item 3): the scorer's source patched in memory one sub-clause at a time, then its own `red_cases()` run on the 0.2.2 copy. Controls: deleting the `(a)` line, the `(c) 104` line or the R3 premise ETag compare *does* turn their cases GREEN, so the method discriminates.
- Mechanism mutations on the 0.2.2 R3 run (item 4): each scored `[]`.
- No browser, no ddev, no HTTP to either instance.

## 1. Host: an uncaught throw in the read-back (BLOCKING)

```js
const read = await send(config.file.davUrl, { cache: 'no-store', headers: headers() })
check.status = read.status
if (read.ok) {
    check.etag = versionOf(read)
    check.sha256 = await hex(await read.arrayBuffer())   // :375 -- not inside send()'s try
}
```

`send()` only catches the `fetch()` promise, which resolves at the headers. `arrayBuffer()` rejects if the body fails: connection reset, or `ERR_CONTENT_LENGTH_MISMATCH` / `NS_ERROR_NET_PARTIAL_TRANSFER` when the server sends fewer bytes than it announced. The rejection propagates out of `put()` → `saveOnce()` → `save()`. `finally` decrements `inFlight` and marks the record settled. Nothing else runs:

- no `record.status`,
- no `saveCopy`,
- no `strand()`.

The page shows `存回 失敗` with a TypeError text. `session.save()` has already marked the session clean (e2-editor-app.js:1056-1058). The page has no beforeunload handler of its own (no match in e2-editor-app.js). The host's guard (litecore-editor.js:234) needs `stranded || inFlight > 0`, and both are false now. So leaving discards the edits without asking. In 0.2.1 every non-2xx or `network` PUT reached the copy/strand path; that is the S4–S6 contract counted in `LOCKS LAND`.

Reachability [inference]:

- A network hiccup during a small GET is rare; for a large document it is proportionally likelier.
- The race half B is built for makes it worse. 103 measured in-place writes (inode unchanged over three rounds), so a write landing *during* the check GET can truncate what Sabre streams after it has sent `Content-Length`. That is exactly the "someone wrote in this second" case.

Fix: catch around the body read. Treat a failed read like a non-ok GET (fall through to `If-Match`), or send it to the copy path. Record `check.error`.

Other host points I checked and consider correct [source unless marked]:

- **Spacing.** `lastAnswered` is set after every PUT answer, including 412/423/403 and `network`, and only there. The copy PUTs go to other files. The wait loop re-checks `performance.now()` after each timer, so an early timer can't shorten it. `performance.now()` is monotonic and does not advance during suspend on Linux Chrome, so a suspend makes the host wait longer, which is the safe direction [inference]. The argument in summary item 8 holds for any writer whose mtime is the kernel clock at write time. A PUT that fails with `network` although the server did write: the next PUT carries the old `If-Match`, and the server's ETag moved (the lost write is ≥1 s after the previous answer), so it gets 412, not an overwrite [inference].
- **Retry without the token.** The second `put()` waits 1 s after the 412 answer (harmless; a 412 wrote nothing) and re-checks. `attempts[0].withToken` is assigned before every return path, so the `412 && withToken` branch still sees it.
- **A refresh LOCK in flight during a queued save.** files_lock's extend path does not propagate the ETag (LockService.php:166-179). Only a new lock does (:189). Expiry deletes without propagating (:141-155, :335-340). If a refresh answer calls `loseLock()` during the wait, the PUT goes out without `If`, and `withToken` is now recorded after the wait, so it matches the request. Before, it was recorded at attempt start; this is more truthful.
- **The beforeunload guard while waiting.** `inFlight` was incremented before `saveOnce`, so the guard holds during the wait. The window where a confirmed "leave" drops a queued save grows from ~50 ms to ~1 s, or ~33 s for a held Ctrl+S (condition 4).
- **Compare bookkeeping.**
  - `lastSha` = the load body's hash, or the last 2xx save's bytes; `etag` moves only on 2xx.
  - After `changed` / 412 / strand, both stay, so every later save goes to a copy. This matches the 412 behaviour, not a new trap.
  - The first save compares against the load's post-lock ETag and body.
  - Readonly: GET allowed, PUT 403, copy. No lock: same.
  - A GET that is not ok falls through to `If-Match`. A 404 gives 412 on the PUT.
  - The HEAD-fallback case (`etagFrom: 'HEAD'`) is now *safer*: if a foreign write lands between the PUT and the HEAD, the next check sees that ETag with other bytes and refuses [inference].
- **ETag formats.** `versionOf` prefers `OC-ETag`, which CopyEtagHeaderPlugin copies on `afterMethod:*` (CopyEtagHeaderPlugin.php:34-49), so GET and PUT both carry it unmangled by mod_deflate. The report agrees: 100/100 `check.etag == ifMatch` (92 R2 attempts + 8 R3) [report].
- **Concurrency assumption.** The host doesn't serialise `save()` itself. Two overlapping calls would both pass the wait on the same `lastAnswered` and PUT in one second with the same `If-Match`. The frozen page serialises (`hostSaves` chain, e2-editor-app.js:1038-1042), so this is latent. Worth one line in the host comment.
- **Timer precision** [inference]: under Firefox `privacy.resistFingerprinting`, `performance.now()` is 100 ms-coarse, so the real gap can be ~900 ms + GET + request. Default Firefox and Chrome in a cross-origin-isolated page are µs-precise. The ruling fixed 1.0 s; if margin matters, 1.1 s costs nothing.
- **Size.** The read-back downloads the whole document before every save (memory ×2, time and traffic ~×2). The entry condition was measured on the 9.5 KB fixture only. For large files GET ≤ PUT is plausible (no versioning copy, download ≥ upload) but not measured.
- `attempt = {}` is pushed and may be published by an unrelated `publish()` while the host waits. A driver reading attempts mid-wait sees an empty object. Cosmetic.

## 2. Condition 7 and the R1 pin (BLOCKING)

`check_m3_versions.py:54` `HOST_COMMIT = "5e53362"`, enforced in `score(strict=True)` at :296-297:

```python
if strict and not (report.get("hostRepo") or "").startswith(HOST_COMMIT):
    problems.append(f"host is {report.get('hostRepo')!r}, spec §3 names {HOST_COMMIT}")
```

A counted R1 on the 0.2.2 commit therefore can't say `VERSIONS CORRECT` while the runner is unchanged. The ruling's condition 7 says "re-run … unchanged … A red is a finding, never a test fix".

The precedent is commit `81641337`: SPEC-M3-asset-delivery.md:179 wrote before its K3 run that `HOST_COMMIT` is re-pointed "（那是綁定，不是判準）", with the reason in the commit. Do the same here, before the run. `check_m3_same_second.py` imports only `MTIME, NS, VServer, older` from that module, so the edit changes nothing for R2/R3.

The other three runners have no commit pin:
- locks and host entry check dirty + hostFiles;
- assets checks dirty + hostRepo non-empty.

## 3. Red cases: sub-clauses without a case (SHOULD FIX)

Method: patch one sub-clause of the scorer out (source edit in memory, not on disk), then run the scorer's own `red_cases()` on the clean 0.2.2 copy. "failures=0" means no case turned GREEN, i.e. nothing guards that sub-clause. Controls turn GREEN as they should.

| Sub-clause removed | Cases GREEN |
|---|---|
| (b) "Lb rows are not in save order" | 0 |
| (c) "Lc lacks S1..S22" | 0 |
| (c) "Lc has a row that is … not one of S1..S23" | 0 |
| (c) "Lc does not have exactly one current row" | 0 |
| R3 shape: F, X, S1, S2 all different | 0 |
| R3 lock: host lock state `held` | 0 |
| on_wire: If-Match equals recorded | 0 |
| on_wire: PUT count equals attempts | 0 |
| on_wire: LOCK before first GET | 0 |
| control: the (a) line | 2 |
| control: the `(c) 104` line | 2 |
| control: R3 premise ETag compare | 2 |

"(c) Lc lacks S1..S22" is the one that matters. It is (c)'s claim that a restore keeps *everything*, not just S23. `_drop_last_known("Lc")` on a clean report drops S23, which only produces the `(c) 104` line. On 0.2.1 the older-row losses fired, but the spec itself says they were carried by (b) (§4 R2, "同日補"). So this sub-clause has neither an independent natural red nor a synthetic one.

Cheap additions:
- drop a middle Lc row (e.g. S10);
- append F to Lc (a restore that copied instead of moved);
- a second current row in Lc;
- swap two Lb revisions;
- R3 S2 := X's sha;
- R3 host lock `lost`;
- a wire PUT with another If-Match;
- one PUT removed from the wire.

The locks suite has its own cases for on_wire, but condition 2 asks for this arm's clauses.

## 4. R3 checks the outcome, not the mechanism (SHOULD FIX)

`score_foreign` checks S1's attempts, premise, kept, copy, page and lock. It never looks at S2's attempts and has no wire check. Mutations of the clean Chrome R3 run, each scored `[]`:

- S2 → status 412, attempts `[(412, True)]`, `tokenOnServer: True`: the copy made by an ordinary If-Match.
- The same plus a second PUT to the file on the wire.
- S2 attempts `['changed', 204]`: the host says it PUT S2 after all.

Physically, the only way to reach the first shape is something moving the ETag between `afterForeign` and S2's check. Nothing in the flow does that (refresh/expiry don't, [source]), so I rate the risk low. But the premise is measured at `afterForeign`, not at S2's check. With the mechanism pinned, R3 would prove what condition 6 describes rather than an outcome two paths can produce.

The shakedown confirms the path today [report]:
- S2 `status: 'changed'`, `waited: 0`, `check.etag == ifMatch == S1's ETag`, `check.sha256` = X's bytes, in 4/4;
- on the Chrome wire, only S1's PUT and the copy's PUT (no `If-Match`).

It also confirms that R3's green is not the 1-s wait: S2 comes ~2.5 s after S1, `waited: 0`.

The premise itself is sound. ETag equality after X means Scanner reused it, which requires equal storage_mtime (Scanner.php:174-183), i.e. X in S1's second. The margin: X lands at .64–.68 of the second, S1's PUT at .27–.30.

## 5. §5's residual statement (SHOULD FIX)

Windows after 0.2.2, as I read the source:

- **W1 (closed):** a foreign write in the host's version's second, *before* the check GET. It is caught by compare-before-save; R3 measures exactly this.
- **W2 (closed for real-time writers, [inference]):** a write *after* the check GET. The GET is ≥1 s after the answer that ended the host's version-writing PUT, so the write's mtime is in a later second and the ETag moves.
- **W3 (open, not stated):** writers that *set* mtime. File.php:358-363 touches the file to `X-OC-Mtime` after the write. A restore sets it to the restored revision.
  - Local's ETag is `md5(mtime . ino . dev . size)` (Local.php:538-561), recomputed after that touch.
  - So such a write keeps the ETag and passes `If-Match` if it (a) lands after the check GET, (b) sets the mtime to the host's version's second, (c) is the same size, and (d) is in place (103 measured in place).
  - §5 already names the restore instance and calls it 推論; the new sentence "ETag 一定會換" contradicts it.
  - Narrow and unmeasured. Say "for writes that take the server's clock", or list W3.
- **W4 (stated, correct):** host version from load, first-save check GET in the second of the pre-open write. Unreachable in practice: open takes seconds.
- **104 from a foreign same-second write:** still open, stated correctly.

"宿主自己寫出的版本的窗口就關上了" is inference from source plus the spacing, not a measurement; tag it 推論. Also: R3 would be withdrawn if the entry condition failed; it held (23/24 vs 46/46.5 ms).

## 6. Spec bookkeeping (SHOULD FIX)

- §6 top row: "加 R2 `same-second`（§4），§5 的「不做，除非擁有者要」改寫成做". Unlogged: R3; the 103-bullet correction ("~~不做~~ 更正…條件 6"); the (c) "同日補" paragraph; the "0.2.1 第一次 shakedown 之後補" note.
- `git show b498d213` has R2 only. R3 and the (c) paragraph arrive in `2e473813` (11:25 +0800) together with `check_m3_same_second.py` and both 0.2.1 shakedowns (`031241` 11:12, R2-only and aborted; `031828` 11:18, the first R3 runs). The headings "先於 runner 與宿主改動寫下" and "（同日補，仍在任何執行之前）" may be true, but this tree's rule is that the ordering should be auditable (CLAUDE.md §9–10). As it stands only the author's word carries it. Log it honestly in §6 with times; for later arms, commit the criteria alone first.
- §3 still says "宿主的行為：不改", names `49cc4ab`, and lists "103 在宿主這一側關不掉（第 5 節）". §5 and §4 now say the host changes and half B narrows 103. Append a correction rather than editing (§10 of CLAUDE.md).

## 7. Questions 1–2 in detail

- **(a) and non-2xx.** (a) skips non-2xx pairs, but the shape clause requires `attempts(s) == [(204, True)]` for all 23 and `len(saves) == 23`. Any non-2xx save, `changed`, retry or missing save is red there [scorer]. (a) also reads PUT-response ETags; an intervening ETag move could fake "different". That can't hide a loss, because (b) catches it independently.
- **(b) ⇒ distinct seconds.**
  - `post_write_hook` creates a version row only when the node's mtime changed; otherwise it updates the existing row (FileEventsListener.php:326-352).
  - `store()` writes `.v<mtime>`, so a same-second pair shares one row, and after the next write the row holds only one of the two.
  - A pair (S20, S21) in one second would make S20's row the current row (revision == mtime), excluded from `older()`, hence "Lb lacks S20".
  - So "[F, S1..S20] non-current + S21 current" forces 21 distinct mtime seconds [source].
- **Retention.** `scheduleExpire` pushes a bus command → background job (Storage.php:822-833). In ajax mode one job runs per rendered page. R2 renders no page between opening the editor and `finish()` (after Lc). So no expiry runs in the window [source + inference]. Expiry can only delete rows: a false red, never a false green. The spec's "先當 finding 讀" is the right disposition.
- **Phase.** It is the runner's press moment on the host clock; the browser and ddev share the kernel clock (Docker on Linux). Press→first PUT is ~0.2–0.3 s (engine save), so the sweep maps to PUT phases ~.23–1.03 [report]. On 0.2.2 phase is irrelevant: the second PUT of every pair comes 1063–1183 ms after the first, `waited` 879–995 ms [report]. On 0.2.1 it made (a)(b)(c) red deterministically; the prediction "about 7 of 10" came out 9/8/9/8 [report]. Register the miss. (The boundary sits on where the *second* PUT lands: e.g. Chrome run 2 pair 7, PUT phases .832/.973, got distinct ETags.)
- **R3 alternatives to the compare.**
  - The wait: not involved (`waited: 0`).
  - The lock: held, and the token is unchanged (checked).
  - X failing: the premise requires 204 and ETag equality.
  - Page text: produced by `changed` → `CONFLICT`.
  - The only alternative is an ETag move before S2 (item 4).
  - Is "kept == X + one copy == S2 + CONFLICT" enough for the *claim* (X not overwritten, S2 not lost)? Yes. S1's bytes end up only in `.vT` under the current row (104 by someone else's write). They are superseded by S2 in the copy, since S2 is a later save of the same session; the spec says so.

## 8. Question 4: the four runners on 0.2.2

Read against the 0.2.2 attempt shape `{waited, check, ifMatch, withToken, at, respondedAt, status}`:

- **locks.**
  - `attempts()` reads only status/withToken.
  - `on_wire` counts PUTs to the file and uses `gets[0]` (still the load GET).
  - K1: chain and 2×204. K3: one 204. K5: `(423, False)`, GET allowed under the other user's lock (LockWrapper.php:74-76). K9/K10: 403, GET allowed.
  - K6: `[(412, True), (412, False)]`; the owner unlock and the intruder's later-second write move the ETag, so the check falls through.
  - K7: `[(412, True), (204, False)]` with a ~1 s pause, since deleting the lock row doesn't move the ETag. `QUIET_PHASE` leaves a 35 s window.
  - K8: expiry deletes without propagating, so its 204 is unchanged.
  - K11: the offline GET fails with `network`, falls through to the PUT, which fails with `network`, then strands; the online save is > 60 s later, so no wait.
  - K12: refused unlock moved the ETag → 412, `tokenOnServer` true.
- **versions R1.** Only item 2. S1→S2 is 3 s + insert, so no wait. Step 6: the restore moved the ETag, so the check falls through to 412 and `attempts[0].ifMatch` is still the pre-restore version.
- **host entry.** H2 chain and `SAVED` regex (`^存回 \d+ ms$`) are fine. H3 with the token intruder: the intruder writes ≥10 s after the upload, in a later second than the storage_mtime, so the ETag moves → `[(412, True)]` + `tokenOnServer` true ×2.
- **assets.** Opens and edits, never saves. K0-6 requires `lastJsCommit ≤ lastVersionCommit`, so commit `js/` and `info.xml` together.

"Silently stops testing": I found none. Recording the check inside the attempt keeps "one attempt per PUT", which avoids fable's F2 caveat without amending expectations.

One latent trap: a `changed` attempt has no PUT and no `at`. If one ever occurred in a locks arm, `on_wire` would report a count mismatch instead of the real cause. Not expected in any arm.

## 9. Conditions 2–6 and 8–9, status as I read them

- **2:** criteria and "if never done" defaults present for R2 and R3. The red cases for the natural (a)(b)(c) and kept/copy/page were red on 0.2.1 [scorer]. Gaps: item 3; the log/ordering in item 6. The 0.2.1-base synthetic runs of already-red single-line clauses (R3 kept/copy/page) prove nothing: the "new line" rule accepts a changed message. Cite the 49/49 on the clean 0.2.2 report instead, and repeat it on the counted report.
- **3:** met by R2's design. Latencies are registered: page `存回` ~950–1060 ms for pairs, 68–73 ms for the single save, vs 40–58 / 50–57 ms on 0.2.1 [report].
- **4:** not yet. `probe_m3_same_second_saves.py` uses `attempts[0].at` as "sentAt", which on 0.2.2 is the PUT send time (after wait and check). That is still comparable as "PUT sent".
- **5:** the diff touches only the two files; the page sha is unchanged in every report.
- **6:** met (GET + sha256 against the host's own last bytes; no server change; 23/24 ms ≤ 46/46.5 ms; its red case ran red on 0.2.1 and clean on 0.2.2). `admission()` pools 46 saves per browser where the spec says 23; the verdict is the same. Measured on a 9.5 KB fixture only.
- **8:** item 12. `build_m3_release.py:116-117` overwrites `release.json`, which `check_m3_skeleton_open.host_binding` (:126-137) uses as the reference for any non-dev instance.
- **9:** pending. Finding 104 still says "宿主這一側可以不讓自己的兩次存檔落在同一秒…**沒有做**", and 103 still says the host "沒有研究" how to close it.

## 10. Cosmetic

- `(h or '?')[:12]` prints "GET incomple" for an unreadable row.
- `registered()` truncates nothing else.
- `one_line()` prints red clauses per run, which is good.

## Disposition (main session, 2026-09-29, before any counted run)

Each load-bearing claim was checked against the source or a report before acting.

| Item | Verified | Disposition |
| --- | --- | --- |
| 1 read-back can throw out of `put()` | yes (own code: `arrayBuffer()` outside `send()`'s catch) | **Fixed in the host.** A body that breaks off is recorded as `check.error` and treated as no answer: the PUT decides, as on 0.2.1, so every refused save keeps its way out. Not exercised by any net (no runner can break a body mid-way); registered in the README. |
| 2 `HOST_COMMIT` pin in R1 | yes (`check_m3_versions.py:54`, `:296-297`; precedent `SPEC-M3-asset-delivery.md` K3) | Written into the spec before condition 7 (§3 correction, commit `e672b20a`): the pin is a binding, not a criterion; it moves to the 0.2.2 commit. |
| 3 sub-clauses without a red case | yes (ablation re-run by the main session) | 21 cases added (69 → 70 after one more for R3's wire). Ablating each sub-clause now turns at least one case GREEN. |
| 4 R3 does not show the read-back stopped S2 | yes (scorer) | **Criterion added** (spec R3 step 3, before counting): S2 is one attempt `changed` with the token, and on Chrome the only PUT to the file is S1's. |
| 5 "a later write always moves the ETag" too strong | yes (read `File.php` `X-OC-Mtime`, Scanner reuse) | Spec §5 and R3 narrowed to writes whose mtime is the server's time; the self-stamped-mtime exception named, unmeasured. |
| 6 condition-2 bookkeeping | yes (`git show --stat 2e473813`) | §6 now logs R3, the 103 correction and the (c) paragraph, and says plainly that git proves only R2's precedence (`b498d213`); the rest is the main session's account. §3 corrected. |
| 7 answers to question 1 | — | Noted. |
| 8 spacing relies on page serialization; coarse timers | serialization: yes (page `saveDocument`); timer coarsening: not measured | Spacing raised to 1.1 s (reason in the host comment and spec R2); host does not queue concurrent `save()` — stated, not built (the page's queue is page identity). |
| 9 ETag formats agree | yes (100/100 `check.etag == ifMatch` in `032619Z`) | Noted. |
| 10 nothing else in the four nets turns red | — | To be confirmed by the condition-7 runs themselves. |
| 11 red cases on an already-red base prove little | yes | Harness now prefers a clean base run; the synthetic cases are cited on the clean 0.2.2 reports. The 0.2.1 runs remain the product-level red for (a)(b)(c)/104 and R3 kept/copy/page. |
| 12 `build_m3_release.py` rewrites `release.json` in place | yes (`build_m3_release.py:116-117`) | Condition 8 keeps the 0.2.1 record (litecoreprobe still runs 0.2.1); the 0.2.2 record is kept under its own name. |
| 13 prediction miss, admission count, size limit, leave guard | yes | Registered in the spec (8–9 same-second pairs vs ~7 predicted, with the ~30 ms server offset as the reason); admission holds per run as well (GET 23–24 ms vs PUT 45–47 ms), only on 9.5 KB; the 33 s leave guard is in finding 106. |
