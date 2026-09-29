# M3 page honesty — result: `PAGE HONEST` (2026-09-29)

Counted run `runs/2026-09-29T131943+0000.json` (13:19–14:20 UTC),
`wasm_sdk_probe/tools/check_m3_page_honesty.py --label counted`, runner `11b350c4…`.
Spec: `specs/SPEC-M3-page-honesty.md` §4 as amended by §7 (§7.1–§7.12).

## Bound to (written down before the run, `a2df684f`; checked by the run's `static`)

| What | Value |
|---|---|
| Page `e2-editor-app.js` (web = dist = served) | `fc80050c…` |
| Session subclass `narrow-editor-v2-session.js` (tree = dist = served) | `747eea71…` |
| Host | `litecore` 0.2.4, `369e6ed`, clean tree |
| Engine package | buildId `7f4f4e2204b4a9ec` (profile `e2-editor-v8`, wasm `4a2710bb…`) |
| Shell generation | v54, `4a92f90f…` (frozen `3bffb272`, after the shakedowns and before this run) |
| `make test-e2-c-static` | exit 0 (run by the runner before counting) |

Dev instance `litecore.ddev.site`, Nextcloud 34.0.2, Chrome 151 and Firefox 156.

## Per arm (3 rounds × 2 browsers, every cell)

| Arm | What it holds | Chrome | Firefox |
|---|---|---|---|
| U0 | the recorder sees a leave the runner itself guards, and only the runner's stack | 3/3 | 3/3 |
| U1 | edited, not saved, leaving → asked; the host guards with reason `page` and keeps its lock | 3/3 | 3/3 |
| Uwin | leaving between the page's save and the host's → asked | 3/3 | 3/3 |
| U2 | saved (204) then leaving → not asked; the server has the sent bytes | 3/3 | 3/3 |
| U3 | saved then edited again → asked | 3/3 | 3/3 |
| U4 | a 412 that went to a conflict copy → not asked | 3/3 | 3/3 |
| U5 | opened, not edited → not asked | 3/3 | 3/3 |
| U7 | a paragraph action and a leave in one task → asked with `pending > 0` | 3/3 | 3/3 |
| U6a / U6b | no host (download mode): unsaved → the page asks; downloaded → not | 3/3, 3/3 | 3/3, 3/3 |
| K-held | held Ctrl+S (30 synthetic keydowns) → 30/30 prevented, 1 page save, 1 host save | 3/3 | 3/3 |
| K-sep | two separate Ctrl+S with a marker between, < 300 ms apart (3 ms Chrome, 6 ms Firefox) → 2 saves; save #1 read back from Nextcloud's versions without the marker; the server holds save #2 | 3/3 | 3/3 |
| K-two | button then Ctrl+S during save #1 → exactly 2 saves | 3/3 | 3/3 |
| Vro | a read-only file opens view-only: no LOCK, 「只能檢視」; the census of 26 controls changes nothing; the caret still moves (V4); save refused (V5); leaving not asked (V6); `disabled` = `data-mutates` (V7) | 3/3 | 3/3 |
| Vrw | the writable control: every content-changing control advances the revision | 3/3 | 3/3 |

V3 (the view-only gate) and U3's "never by revision" are unit tests
(`editor-shell-v2/tests/`, 116/116 in the same `make test-e2-c-static`), with their mutants
recorded in `unit-red-cases/`.

**Red cases** on this report: `runs/red-cases-on-2026-09-29T131943.txt` — **154 red, 0 not
red or missing.** A case counts only if the problem it causes contains its own criterion's
string.

## The other five M3 runners, counted on the same page, host and engine

One at a time, right after this run, each with its red cases on its own counted report:

| Verdict | Report | Red cases |
|---|---|---|
| `LOCKS LAND` (22 arms, 52 runs) | `m3-locks/runs/2026-09-29T142032+0000.json` | 99 red, 0 not |
| `VERSIONS CORRECT` | `m3-versions/runs/2026-09-29T150721+0000.json` | 68 red, 0 not |
| `ASSETS DELIVERED` | `m3-assets/runs/2026-09-29T151106+0000.json` | 90 red, 0 not |
| `HOST_ENTRY LANDS` | `m3-host-entry/runs/2026-09-29T151343Z.json` | base GREEN, 23 RED |
| `SAME-SECOND SAVES KEPT` | `m3-same-second/runs/2026-09-29T151851+0000.json` | 70 red, 0 not |

Each of those runners' RESULT (or README) has the same rows appended.

## What this settles

- **Finding 107** (leaving with unsaved edits asked nothing): fixed on this page and host.
  The host alone decides leaving (`watchUnsaved`), guards without releasing the lock, and
  records why.
- **Finding 106** (held Ctrl+S saved once per key repeat): fixed on this page — one save per
  hold, and two separate presses still make two saves.
- **Finding 108** (a lock lost while a save's PUT was out threw, and the edits were gone):
  fixed in host 0.2.4. Its own measurement is `save-throw/`; this run shows 0.2.4 changes
  nothing the six runners measure.
- The owner's ruling A on read-only files (view only): holds.

## What it does not settle

- Spec §5: Firefox's leave dialog itself is not observed (only that the leave was guarded);
  closing a tab or window and reload are not measured; view-only is a client guarantee
  (the server's is Nextcloud's 403); `mutation` flags are measured for today's controls
  only; held Ctrl+S is synthetic keydowns only.
- Spec §7.5 registrations: in Firefox, choosing "leave" after the host guarded goes out on
  `pagehide` alone (finding 105's path); V2 counts revisions, not content; download mode
  drops unsaved edits when the sample or a local file is switched; `placeCaret` is marked
  non-mutating but a LOK click may change content (inferred).
- Registered by the implementation review, not fixed: held Enter on the save button (106
  through the button); `e2-editor.html` is outside the hash net (finding 094).
- Finding 108's natural rate (a refresh landing inside a PUT's round trip) is not measured.
- The M3 product still ships `e2-editor-v8`, so finding 096 (ArrowDown on the last line
  kills v8 after 30 s) is in the product; the V arms aim at the first line for that reason
  (§7.9).
- Condition 9 of the K2 ruling (§7.8: Firefox, cache on, leave after being guarded, ×12) is
  a one-time measurement still to run, before the H+J release archive.

## How it got here

Shakedown reports and every runner fix are in `shakedown/README.md` (§7.9, §7.10, §7.12):
the V arms first died on finding 096 (aimed at the last line); the writable control needed
its precondition laid out; U3's unit test missed a `!==` mutant; the implementation review
(`review-2026-09-29-opus-implementation.md`) forced the page's `hasUnsavedWork()` to be
fail-closed and found BLOCKING 1 (finding 108); the re-shakedown on 0.2.4 died in K-sep
because it read all 1,645 versions of the file and the CDP socket timed out. Product-path
net on shell v54: `product-path/`, v8 and v14 cell for cell the same as v53.
