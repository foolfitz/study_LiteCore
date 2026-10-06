# Handoff, 2026-10-06b — B1 fixed (owner chose A), host 0.2.7, v55 frozen, pins written; the counted chain is running

Entry points: this file; `specs/SPEC-M3-production-ui.md` §9 (B1's fix, criteria A1-4/A1-5, predictions), §9.6 (@scope fallback, A2-4), §10 (dispositions of both reviews), §11 (counted bindings); `findings/evidence/m3-production-ui/README.md`; reviews `review-2026-10-06-opus.md` and `review-2026-10-06b-opus.md`; new finding 111.

Picks up from `handoff/HANDOFF-2026-10-06-production-ui-b1-blocks-the-count.md`. Not pushed.

## What happened this session

| Commit | What |
|---|---|
| `74cbbfed` | Spec §9 before any code: owner chose **A**; criteria A1-4 (unit) and A1-5 (browser arm B3x, three refusals in one page load), red case, predictions. |
| `ec951c41` | B1 fix. Session: `restartAvailable()` (asked BEFORE `restart()`, which disposes first), `takeContentForRescue()` (only from a stopped session and only when `restartKeepsContent()`; marks clean like `save()`'s finalize). Page: `reopenAfterBoundaryRefusal` checks the ceiling first and goes to `rescueAtGenerationLimit()` (existing save path: `hostSaves`, `savesUnsettled`); notice states in `#notice[data-limit]`; button reloads (or saves when nothing was attempted). Review-1 items 2, 3, 6. |
| `2f923764`, `c3bef9b4` | Runner: B3x arm + scorer + mutations, `runnerSha256` in reports; review-1 items 10/11/13/14. **A1-5 red case** on the pre-fix page, both browsers, red where predicted (`recoverable-error` at refusal 3, notice button disabled, nothing on the server). Also measured for the first time: on the pre-fix page no key typed after a reopen landed (review-1 item 3). |
| `04d19fcd` | Review-2 dispositions in code: named `onNoticeAction`, `limitNotice()`, rescue uses `limitState()`, failed text shows the host's own sentence, toast no longer claims "everything before this key", `preventScroll`; A1-5 binds the host's settled `saved` save in the same read, and `lock.state == held` after the reload. Unit 135/0; the review's surviving mutations S1, P1, P2, P4, P5, P16 now red. |
| `2e1d60fa` | Spec §10 (every review item: fixed + what guards it, or which kind of registration); finding 111; review-2 verbatim. |
| `2e3bb09e`, `3658b6c4`, `61bfef27` | §9.6 before the host change; **no-@scope red case** on 0.2.6 (Firefox 157 with `layout.css.at-scope.enabled` off: `#notice`/`#expired`/`#sink` exposed, no document on screen); host **0.2.7** `0488586` (unscoped sheet with `media="not all"`, switched on when `CSSScopeRule` is missing; `scopedStyle` counts every occurrence); A2-4 holds both ways. |
| `bc95b342` | shake3 (host 0.2.7, all six arms) found the first key after a reopen lost in both browsers: the page focused the sink only after `run()` had also awaited the repaint. Focus moved inside the operation, right after `restart()` returns. |
| `68f68b1b` | shake4: B3x, Bdel, Bbs pass in both browsers (third refusal → `saved` 0.78 s / 1.09 s, all three markers on the server, reload not asked, lock held). |
| `72549b38` | **Shell generation v55 frozen** (`2470765a…`). Two anchors re-pointed to `const { bytes } = await take();` (product-path `save` mutation; relink-queue item 049), reasons written beside them. `make test-e2-c-static` exit 0. |
| `533578d7` | **Pins** (spec §11): page `e97d6e03…`, session `3f5f754b…`, host 0.2.7 `0488586`, buildId `fabdb50ecd038802`, v55, document `7b336879…`, runner sha256 of `check_m3_production_ui.py`. Six M3 runners re-pinned. |
| `2101790b` | Product-path net on v55: v8 and v14 each 40 PASS / 2 NE, cell for cell the same as v54. |
| `2f75c4ee` | The 2026-10-05 locks shakedown that the machine shutdown cut off, recorded as superseded. |

Dev instance `litecore`: host 0.2.7 (`occ upgrade` done), engine/ packaged from `dist/` (buildId `fabdb50ecd038802`). `dist/e2-editor-app.js` and `dist/editor-shell-v2/narrow-editor-v2-session.js` equal source.

## Running now: the counted chain (owner approved, option A)

`wasm_sdk_probe/build/m3-count-2026-10-06/chain.sh`, started 01:35 UTC with `setsid nohup` (survives the Claude session ending, not a reboot). One runner at a time:

1. Shakedown (`--label shakedown --repeats 1`): page_honesty, locks, versions, assets, host_entry, same_second. **Any non-zero exit stops the chain before any counted run.**
2. Counted production UI: `runs/counted-B-x3.json` (Bdel, Bbs × 3 per browser), `runs/counted-ctl-S-P.json`, `runs/counted-B3x-x2.json` (under `findings/evidence/m3-production-ui/`).
3. Counted six (`--label counted`).

Progress: `wasm_sdk_probe/build/m3-count-2026-10-06/chain.txt` (one line per begin/exit), per-runner logs beside it; reports land in each runner's `findings/evidence/m3-*/shakedown|runs/`. Check `ps -eo pid,etime,args | grep -E 'chain.sh|check_m3'` before starting anything else: **never two M3 runners at once.**

## What is next

1. Read every report (the `static` block and the arms, not only the score). Run `--red-cases` on each counted report.
2. If all counted: mark 109 and 110 fixed (and 111 stays open); short zh-TW note to the owner on what changed on screen; README/RESULT under `findings/evidence/m3-production-ui/`.
3. Finding 111 (delete/arrows overtake text still in the input adapter's queue) is its own round: measure the frequency in a browser with real keys at a cadence sweep first, then design a barrier that waits only for what was queued before the key (`idle()` is not it).

## Things this round taught

- **A recovery path has a budget; the arm has to spend it.** B1 was a ceiling nobody's arm reached. B3x reaches it.
- **The shakedown found what two reviews did not measure.** Review 2 predicted the late focus could drop a key (item 10); shake3 measured it in both browsers. The fix was one line moved; the evidence was a revision that stayed at 0.
- **Ask the same question in the same read.** A1-5 originally read the server seconds after the notice said `saved`; a page that said it early would still pass. The host's last save is now read in the same evaluation.
- **A refactor drifts every substring that pointed at the old line.** Two anchors (a mutation and a relink-queue check) moved with `saveOnce()`; both said so loudly, and both were re-pointed with the reason written down.
- **Detach long chains.** The previous session's chain died with the machine; this session's product-path run died with the Claude process. The counted chain runs under `setsid nohup`.

## Standing rules to carry

- Never two M3 runners (or an M3 probe) at once; each clears the whole `oc_files_lock` table.
- Counted runners refuse a dirty host tree; a host JS change means an `info.xml` bump + `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`; the buildId is content-addressed.
- A runner changed after §11 is a new pin (append to the spec), or its reports do not count.
- `findings/evidence/**` and `handoff/**` English; specs, findings' prose zh-TW; specs append-only.
