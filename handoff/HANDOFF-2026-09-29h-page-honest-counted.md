# Handoff, 2026-09-29h — `PAGE HONEST` counted, host 0.2.4, all six M3 runners re-counted

Entry points: this file, `findings/evidence/m3-page-honesty/RESULT.md` (the verdict and the table
of all six counted runs), `specs/SPEC-M3-page-honesty.md` §7.11–§7.13 (BLOCKING 1, the K-sep runner
fix, condition 9), `findings/108-host-a-lock-lost-while-saving-throws-and-the-edits-are-gone.md`,
`findings/evidence/m3-page-honesty/save-throw/README.md`,
`findings/evidence/m3-page-honesty/shakedown/README.md` (re-shakedown section at the end),
`findings/evidence/m3-page-honesty/product-path/README.md`.

Picks up from `handoff/HANDOFF-2026-09-29g-review-dispositioned-blocking1-to-measure.md`. Steps 1–7
of its "What is next" are done except H+J, which the owner deferred (they pick the time).

## What happened this session (`study_LiteCore`, `main`, not pushed)

| Commit | What |
|---|---|
| `cbe15a48` | BLOCKING 1 measured in three steps, each as predicted before running: host 0.2.3 → **LOST**; catch-all only → **KEPT** (stranded, leave asked); plus `sentToken` → **KEPT on the original** (412 with token, 204 without). Host 0.2.4 = `litecore` `369e6ed`, `ddev occ upgrade` done; step 3 re-run on the clean committed host. Finding 108 registered; spec §7.11. The refresh against a deleted lock row answers **400**, not 412 (400 is in the host's `LOST`). |
| `a2df684f` | Bindings written before any run: page `fc80050c…`, session `747eea71…`, host 0.2.4 / `369e6ed`, plus §7.6's four constants. `dist/` updated (plain `cp`), engine re-packaged: buildId `7f4f4e2204b4a9ec`. |
| `b954857d` | Re-shakedown, one runner at a time. Page honesty first **died at cell 23 (K-sep)**: `versions()` read all 1,645 versions of the test file one GET at a time, the CDP socket went unread for minutes, `websockets` 15 defaults (`max_queue` 16, ping 20 s/20 s) dropped it, and the unguarded `drain()` in `finally` killed the runner. Fixed (spec §7.12): K-sep reads only versions named at or after `versionsSince` (a wrong `since` can only turn it red), a failed drain is that cell's `fatal`. Then 30/30 clean, red cases 154/154. Other five clean: assets 90/90, locks 22 arms 99/99, versions 68/68, host entry 23/23, same-second 70/70. |
| `3bffb272` | Shell generation **v54** frozen (`4a92f90f…`): the session subclass and the page changed since v53. `make test-e2-c-static` exit 0 after fixing one anchor in `run_e2_c_product_path.py` (`--barrier-details-diagnostic`: the page's `run()` catch now opens with the view-only branch). Product-path net v8 and v14 each 40 PASS / 2 NE, cell for cell equal to v53's. |
| `82d79451` | **Counted: `PAGE HONEST`** (15 arms × 2 browsers × 3 rounds, all 3/3; red 154/154), **`LOCKS LAND`** (99/99), **`VERSIONS CORRECT`** (68/68), **`ASSETS DELIVERED`** (90/90), **`HOST_ENTRY LANDS`** (23/23), **`SAME-SECOND SAVES KEPT`** (70/70) — all bound to page `fc80050c…`, host `369e6ed` clean, engine `7f4f4e22…`, shell v54; every report's `static` checked by reading it. Findings 106, 107, 108 marked fixed. |
| `0ca3f79c`, `80ae2aca` | **Condition 9** (owner chose "now"): `probe_m3_leave_unlock.py`, Firefox cache on, host 0.2.4. Guarded leave (edit arm, every leave guarded with reason `page`) **12/12** released within 10 s; unguarded control 12/12; 0 instrument failures. Finding 105's "about half" was an extrapolation and is replaced by the measurement; why the pagehide UNLOCK now arrives is not attributed (different host from the pre-fix runs, no same-host control). Spec §7.13 (ran on 0.2.4, the condition said 0.2.3 when that was thought final). |

Long runs were run by the main session as background shell chains (one runner at a time, stdout to
the scratchpad), not delegated to a sonnet agent: a script chain costs the main session no context
while it runs, and there was nothing for an agent to decide.

## State

- `study_LiteCore`: `main`, clean after this handoff's commit, not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `369e6ed` (0.2.4), clean, not pushed; dev instance upgraded
  to 0.2.4. `engine/` (gitignored) is buildId `7f4f4e2204b4a9ec` from page `fc80050c…`.
- `litecoreprobe`: unchanged (`litecore` 0.2.1 from the 0.2.1 archive).
- `dist/` = the reviewed page; shell generation v54 matches `dist/`.
- The dev instance's test file (fileid 76, `M3 骨架 測試.odt`) carries ~1,800 versions from the
  day's runs. Harmless now that K-sep filters; anything else that lists versions should filter too.
- The stray geckodriver (PID 2827195, from 2026-09-28, not this session) is still there; left alone.

## What is next

1. **H+J — owner picks the time.** H = a truly fresh ddev instance (creating a project rebuilds the
   shared router; the owner's other ddev projects 404 briefly); J = an install window on a 0.2.4
   release archive. `build_m3_release.py` rewrites `findings/evidence/m3-install/release.json` in
   place and litecoreprobe's binding reads that file: save the 0.2.4 record separately and keep the
   installed version's record until the reinstall. No container lifecycle activity on the host
   during the install window.
2. Then the agreed priority order continues: **A** distribution channel (needs an outward action by
   the owner), **G** zstd/brotli for the engine, **F** finding 105's Firefox-only minimal repro
   (upstream submissions stay on hold). Condition 9 changes F's premise: the guarded leave no
   longer loses the lock on 0.2.4, so a repro must reproduce on the pre-fix host shape.
3. Registered, not scheduled: held Enter on the save button (106 through the button); finding 108's
   natural rate; `e2-editor.html` outside the hash net (094); the shared `ChromeSession` keeps
   `websockets` defaults (any runner that goes >20–40 s without reading CDP while the page emits
   events will drop the same way — not changed because it binds many runners' identities).

## Things this round taught

- **Writing the prediction before each step of a fix measurement made the result legible.** LOST,
  then KEPT-by-stranding, then KEPT-on-original: three runs, three predictions, and the middle one
  showed the catch-all alone suffices while the throw still happens.
- **A readback that scales with the instance's history is a time bomb on a long-lived dev
  instance.** K-sep's "all versions" was fine on the day it was written and fatal 1,645 versions
  later. Filter to what this run created, in the direction where a wrong filter turns red.
- **An unguarded `finally` turns one dead cell into a lost report.** The runner wrote per-cell, so
  22 cells survived on disk — but the process died and the chain moved on. Guard the cleanup.
- **A static test on a diagnostic's anchor caught page drift that no run would have** (nobody runs
  `--barrier-details-diagnostic` routinely).
- **An extrapolation written as a rate reads like a measurement.** Finding 105's "about half" came
  from pre-fix numbers on another host; the measurement said 12/12.

## Standing rules to carry

- Never run two M3 runners (or an M3 probe) at once — each clears the whole `oc_files_lock` table.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` version bump
  and `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/`, and
  findings' prose are zh-TW. Specs and gate documents are append-only.
- Don't start or restart other ddev projects during a counted run or an install window.
