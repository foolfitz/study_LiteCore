# M3 versions — result

**`VERSIONS CORRECT`**: arm R1 of `specs/SPEC-M3-versions.md` §4, Chrome 151 3/3 and
Firefox 156 3/3, counted run `runs/2026-09-28T152217+0000.json` (15:22:17Z–15:26:04Z).

| binding | value |
| --- | --- |
| host | `litecore` `49cc4ab5bad1…`, tree clean; `js/litecore-editor.js` `a6c51d6a…`, `EditorController.php` `52075fe1…`, `templates/editor.php` `49876f2b…` |
| page | `e2-editor-app.js` `fbfb59a4…` in both `dist/` and `web/` (unchanged since the host entry) |
| runner | `check_m3_versions.py` `ea1685d5…` (committed in `820557a7`, criteria revised after the review and before this run) |
| static | `make test-e2-c-static` exit 0 |
| re-scored from the stored report | same verdict |
| `--red-cases` against it | 67 mutation × browser cases and the static case, all red |
| other ddev projects | no container created or recreated during the run (`docker ps` before and after identical) |

Page, shell (v53), engine, profile and host: untouched by this step.

## What the six runs show (identical in every run)

1. Opening the file (token lock, then read) adds no version: the listing is the current row
   only, and that row has no version file under it (`GET` 404).
2. Two saves, 3 s apart, both 204 with the token: the history is `[F, S1]` + current (S2),
   every row by `admin`, the current row still 404.
3. A restore of F sent as Files' Versions tab sends it (`MOVE` to `restore/target`, no
   token): **201 through our token lock**; the file is F, the token is unchanged, the ETag moved.
4. After it the history is `[S1, S2]` + current (F): the pre-restore content is kept.
5. The page's third save: one attempt, 412 with the token and the pre-restore `If-Match`, no
   retry; the bytes go to one conflict copy (= S3) whose own history is empty; the page says
   `存回 失敗` with `CONFLICT` and the copy's name; the host still holds the lock.
6. Leaving releases the lock in 0.3–0.4 s; neither the refused save nor the release adds a
   row or moves the mtime; read after leaving, the original is still F.

So all four states the user produced — F, S1, S2, S3 — can be had back byte for byte, at the
time they were written.

## What this settles for roadmap §5.5

"Versions correct" holds through the real page: our saves version like any client's
(`README.md` V1), and a restore made while the page is open is neither blocked nor
overwritten — it wins, and the page's next save goes to a conflict copy.

## What it does not settle (spec §5)

- The page does not show a restore made while it is open; nothing reloads the server's
  version.
- **Finding 103**: `If-Match` cannot see a second write in the same wall-clock second as the
  write whose ETag the host holds. With the lock held only lock-bypassing writes can hit
  that window; without it (lock failed, lock expired) anyone can.
- **Finding 104**: after two writes in the same second, any restore loses the later write
  for good. The host saving twice within a second is enough for the first half.
- Retention (`auto`) may later thin S1; "retrievable" is a write-time property.
- The Files UI itself (whether it shows "Restore" on a file we hold) was not driven; R1 sends
  the request read from its source map.

## Re-run on the page-honesty page and host 0.2.4 (2026-09-29)

SPEC-M3-page-honesty §7.6/§7.11: the page moved to `fc80050c…` (view-only mode, the leave
guard, held Ctrl+S) and the host to 0.2.4 (`369e6ed`, finding 108), so this runner was
re-counted. Bindings written before the run (`a2df684f`): `HOST_COMMIT` = `369e6ed` (the page pin is `check_m3_locks.PAGE_SHA256`). Engine package
`7f4f4e2204b4a9ec`, shell generation v54. No expectation amended.

- Shakedown: `shakedown/2026-09-29T121311+0000.json` — clean.
- **Counted: `runs/2026-09-29T150721+0000.json` — `VERSIONS CORRECT`**, 3/3 per browser, no problems.
- Red cases on the counted report: `runs/red-cases-on-2026-09-29T150721.txt` — 68 red, 0 not.

Run one at a time after `PAGE HONEST` (`m3-page-honesty/RESULT.md`, which lists all six).
