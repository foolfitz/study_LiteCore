# Handoff, 2026-10-06 — production UI built and shaken down; review found B1 (the third boundary refusal loses the work again), so no counted run yet

Entry points: this file; `specs/SPEC-M3-production-ui.md` (criteria §4, predictions §5, addenda §7 and §8); `findings/evidence/m3-production-ui/README.md`; the review `findings/evidence/m3-production-ui/review-2026-10-06-opus.md` (B1 + 20 non-blocking items); findings 109 and 110 with `findings/evidence/109/`, `evidence/110/`; screens `findings/evidence/m3-production-ui/screens/`.

Picks up from `handoff/HANDOFF-2026-10-05-owner-chose-a-109-110-production-ui.md` (owner chose A: stop 109's data loss, fix 110, hide the developer controls, pay the M3 re-count once). Nothing in the gate documents changed. `main` at `b8dfd333` plus this file, not pushed. **No counted run of anything has happened.**

## What happened this session

| Commit | What |
|---|---|
| `8b08d94d` | Spec written before any counted run. It says honestly that A1's code and the §2 dev measurements came before it; those are not counted. |
| `27402abc` | **A1 (109)**: `NarrowEditorV2Session._checkpointBeforeBoundaryRestart` + `restartKeepsContent()`; the page auto-reopens after a boundary refusal when `restartKeepsContent()` holds; toolbar disabled outside ready/busy; `editorAction` silent when not accepting. 6 unit tests; each of the 2 mutations turns some red. |
| `04bf9346` | Runner `wasm_sdk_probe/tools/check_m3_production_ui.py`; pre-fix red evidence (host 0.2.5: **Firefox 157 also reproduces 109**); 0.2.6 shakedown; spec §7. `check_m3_page_honesty.py` `activate()` now clicks `#state-pill` (`#text` is hidden on 0.2.6; a click on a 0x0 box lands on Nextcloud's header). |
| `b8dfd333` | Opus adversarial review verbatim + spec §8. |
| host `96a13b9` | **0.2.6**: `@scope` via `EditorController::scopedStyle` (110), title bar with file name + 「尚未儲存」mark + ✕ close, developer controls hidden by host CSS. |
| host `fa08307` | Close URL from `linkToRoute('files.view.indexViewFileid')` (the hand-built URL was wrong under pretty URLs; the A2-3 regex still matched it, the scorer did not catch it, reading the landing URL did). |

Dev instance `litecore` is on 0.2.6 (`ddev occ upgrade` done). Its `engine/` was re-packaged from `dist/`: buildId `253730c6228b350c`, page `e2-editor-app.js` `d41ae604…`, session `a4f8c219…`. `dist/e2-editor-app.js` and `dist/editor-shell-v2/narrow-editor-v2-session.js` were updated by plain `cp` (`dist/` is gitignored).

**Shell generation v55 is deliberately NOT frozen**: B1's fix changes page and session again. **The pins are not written**: `PAGE_SHA256` etc. in the six M3 runners and in `check_m3_production_ui.py` are `None`/old.

Dev measurements (standalone page + fake host, Chrome, the owner's 563 KB document; not counted): checkpoint save inside the refusal ~0.94 s, reopen ~1.2 s, key to editable ~2.2 s. Mid-text Backspace 95 ms, generation unchanged.

## BLOCKING B1 — owner decision needed

**Claim at risk:** spec §3.1 says a boundary refusal loses nothing. That holds for the first two refusals per page load only (**read from source, not yet measured in a browser**).

**Mechanism:** `editor-shell/editor-session.js:81` `maxWorkerGenerations ?? 3`, and the page passes none. `restart()` disposes the engine **before** `_openFresh` checks the ceiling at `:148`. So the third boundary refusal in one page load (second, if a rollback happened earlier) ends in `recoverable-error`, `WORKER_GENERATION_LIMIT`, `engine === null`: save refused, the work exists only in the checkpoint bytes, reload loses everything since the last save. §7 made these refusals routine (Tab, the break after Shift+Enter, U+FFFC), so this is not a rare path. Reviewer reproduced it with the real session class; the main session confirmed it by reading.

| Option | What | Notes |
|---|---|---|
| **A** (reviewer's and main session's lean) | Before a restart that would hit the ceiling, hand `session.checkpointBytes()` to `HOST.save()` (a download when there is no host) and ask the user to reload. Check **before** `restart()`. Scope the spec claim to "the first N refusals per page load" and add a three-refusal arm with the expected result written down first. | Subtlety to design: after `HOST.save()` of checkpoint bytes the session's `dirty` stays true, so the host's `beforeunload` still asks on the reload. |
| **B** | Also avoid a new Worker for refusals that leave nothing behind (a11y semantic check, deadline refusal; resolve and rethrow outside the drain, the `DISPATCHED_UNVERIFIED` pattern). | Lowers the frequency only; does not fix B1. |
| **C** | Raise `maxWorkerGenerations`. | Likely unsafe (finding 024, Firefox worker reclamation); would need its own measurement. Not recommended. |

## The 20 non-blocking items (review file, numbered there)

- **Fix in the same page change (product-facing):** (2) keys typed during the reload are dropped but the toast says 「尚未儲存的修改都還在」; (3) after the reload `#sink` is not refocused and the caret is at the document start (typing after the reload is unmeasured); (6) Ctrl+Z / Ctrl+Y / Ctrl+S still toast `EDITOR_NOT_READY` during the reload (spec :58 overstates); (8) `@scope` floor: a browser without it drops the whole product sheet (Firefox ESR 140 unmeasured).
- **Disposition (fix or register) before counting, append to the spec as §9+:** runner items 11–18 (11 A2-1's 18 properties are a hand enumeration; 12 "revision +1" cannot tell Backspace from Delete or Enter from Shift+Enter; 13 the A3-2 clock makes `shown` 0.0 by construction; 14 A1-2 never requires `marks == 0`; 15 A2-3 only tests `dir=/`; 16 Firefox dirty close measures leaving, not staying; 17 reports carry no runner sha256 and the runner changed after the prefix run, so re-score the stored prefix JSON with the final scorer and `--expect-red`; 18 `counted_bindings` does not bind v55 or the document sha256). Also 4, 5, 9, 10, 19 (row A1-1 has no never-done default), 20 (a toolbar `.click()` outside ready/busy is now a silent no-op; name `capture_save` in `run_e2_c_product_path.py:3926-3936` before counting), 21.

## Background chain — check it first

At 17:09 UTC (01:09 local) a background chain started the six M3 runners with `--label shakedown --repeats 1`, **one at a time**, on host 0.2.6, in this order: page_honesty, locks, versions, assets, host_entry, same_second. **page_honesty finished 17:30 UTC: `VERDICT clean`, every arm 1/1 in both browsers** (report `m3-page-honesty/shakedown/2026-10-05T170957+0000.json`, committed with this file) — so hiding the controls and moving `activate()` to `#state-pill` broke nothing there. locks started 17:30 UTC; the other four were still ahead when this was written.

- Per-runner stdout: `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/9a41d5e2-3f9d-4289-a7a4-3832e3b1ce4f/scratchpad/m3shake/<runner>.log`
- Chain summary: `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/9a41d5e2-3f9d-4289-a7a4-3832e3b1ce4f/tasks/biiqafqyr.output`
- Reports land under `findings/evidence/m3-*/` (uncommitted; page_honesty's is `m3-page-honesty/shakedown/2026-10-05T170957+0000.json`).

Next session: check whether the chain finished (`ps aux | grep check_m3`), read each report (the `static` block and the arms, not only the score), and note that **this shakedown informs only the host-side changes** (hidden controls, `@scope`, the `activate()` change), because the page changes again for B1. **Do not start any other M3 runner while the chain may still run** (each clears the whole `oc_files_lock` table).

## What is next, in order

1. Owner decides B1 (A / B / C).
2. Implement it; unit tests (mutations each red); the product-facing non-blocking items (2, 3, 6, 8).
3. Disposition runner items 11–18 and the rest into the spec as §9+ (append-only).
4. `dist/` copy, re-run `package_m3_engine.py`; re-run the `check_m3_production_ui` shakedown in both browsers **plus a three-refusal arm** (expected result written before running).
5. Freeze shell generation v55 (`tools/build_e2_c_shell_bundle.py`, MANIFEST pointer with a dated comment); `make test-e2-c-static`; product-path net v8/v14 cell for cell against v54's 40 PASS / 2 NE.
6. Write the pins (page, session, host commit, v55, document sha256, runner sha256) **before** any counted run.
7. Counted: `check_m3_production_ui` (B-del / B-bs x3 per browser, B-ctl, S, P) and the six M3 runners on 0.2.6. Tell the owner before a counted run (a runner clears locks; they may have the editor open).
8. Mark 109 and 110 fixed; a short zh-TW note to the owner listing what changed on screen.

## Things this round taught

- **A recovery path measured once is measured at N=1.** The shakedown arms each trigger one refusal per page load; the reviewer's question "what is the budget this path spends?" found the ceiling. A claim about recovery needs an arm that exhausts what the recovery consumes.
- **A scorer can pass on a wrong result.** A2-3's regex matched the hand-built close URL that landed in the wrong place; reading the landing URL caught it. The scorer is now anchored at the start of the path.
- **The shakedown's instrument faults were all in the runner** (CDP frame over 1 MiB from the PUT body; `keyed()` read a field `READ_STATE` does not have; the 1.5 s window started before the key). Each was fixed without moving a criterion.
- **Red-first covers the half you can reach.** 0.2.5 never reopens, so "restart reopens older bytes" was never exercised red.

## Standing rules to carry

- Never two M3 runners (or an M3 probe) at once; each clears the whole `oc_files_lock` table.
- Counted runners refuse a dirty host tree; host JS change means `info.xml` bump + `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`.
- Snap Firefox cannot see `/tmp`; its profiles live under `wasm_sdk_probe/build/`.
- Chrome CDP frames over 1 MiB kill the socket (a large document's PUT body in Network events); the new runner disables Network.
- `findings/evidence/**` and `handoff/**` English; `specs/`, `research/`, `devlog/` and findings' prose zh-TW. Specs and gate documents are append-only.
- Byte-for-byte equality is for machine data, not prose (owner, 2026-10-03).
- The owner is the one observer who does not share our instruments; a subagent's diagnosis is a hypothesis until the source is read.
