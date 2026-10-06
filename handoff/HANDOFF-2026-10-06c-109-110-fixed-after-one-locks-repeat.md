# Handoff, 2026-10-06c — 109 and 110 fixed on host 0.2.7; locks was red once (finding 112) and held on its one repeat

Entry points: this file; `findings/evidence/m3-production-ui/RESULT.md` (every criterion, the six runners' table, what is and is not settled); `specs/SPEC-M3-production-ui.md` §12–§12.2; finding 112 (its 裁決 section is fable's ruling); `findings/evidence/m3-locks/README.md` rule 5.

Picks up from `handoff/HANDOFF-2026-10-06b-b1-fixed-counting-under-way.md`. No upstream remote configured; nothing pushed.

## What happened this session

| Commit | What |
|---|---|
| `4cf203b9` | The counted chain's reports and red cases. Production UI 22/22 (Bdel, Bbs 3/3 and B3x 2/2 per browser; Bctl, S, P 1/1), the three reports pooled for `--red-cases`: 30/30. PAGE HONEST 154, VERSIONS CORRECT 68, ASSETS DELIVERED 156, HOST_ENTRY LANDS 23 + base green, SAME-SECOND SAVES KEPT 70. **Locks: `LOCKS DO NOT LAND`**, 51/52 (Chrome K5 2/3). Also finding 111 extended from source: Enter, Shift+Enter, Ctrl+B/I/U, Ctrl+Z/Y and Ctrl+S/the save button take the same path that does not wait for the input adapter (not measured). |
| `62d471c0` | **Finding 112**: in that one run the Files page in Chrome loaded 188 resources in one second (the host's `litecore-files.mjs` among them), never requested Files' own bundles (`files-init.js`, `files-main.js`, `core-main.js`, …) or any PROPFIND/REPORT, and listed nothing for 60 s; the product page was never requested. Server-side evidence in `findings/evidence/112/` (Apache window; router counter gap 223 = Apache 234 − 10 idle 408 − 1 health check). Not rule 2's router-404 case, so read as a finding first; the owner sent it to fable: **A, bounded** (one repeat, instrument-only runner change, outcomes fixed before the repeat, C as fallback). |
| `9bc23bbf` | `check_m3_locks.py` `6e6b2fa4…` → `1d3099a2…`: `filesRowSeconds` on every run, `filesRowDiagnostic` (DOM summary, CDP summary + unanswered requests + Script URLs on Chrome, screenshot) on a Files-row timeout. Scoring proven byte-identical (old and new runner, `--score` and `--red-cases`, on the 10-06 and 10-02 reports); the capture made red once with a deliberately absent row name in both browsers (`findings/evidence/112/capture-red/`, also the reference for a normal Files page: list present, 14 rows, `files-main.js` requested). Locks README rule 5, spec §12/§12.1. |
| `10c1032a` | 109/110 interim lines (passed this spec's A rows, R not yet). |
| `adcc1797` | **The repeat**: `m3-locks/runs/2026-10-06T053046+0000.json`, `LOCKS LAND`, 52/52, red cases 99/0, the new pin, `filesRowSeconds` in 52/52, no diagnostic triggered (the row was there 0.00–0.26 s after load, so 112's 60 s was a stall, not a slow page). **R holds; 109 and 110 marked 已修** (spec §12.2). RESULT.md for production UI; each of the six runners' RESULT/README has an appended section. |

Dev instance `litecore`: host 0.2.7 `0488586` (clean), engine buildId `fabdb50ecd038802`, page `e97d6e03…`, shell v55. No runner is running.

## State of the findings

- **109** fixed (data loss at a paragraph-boundary delete; not merging — the engine still refuses, the page checkpoints and reopens, the third refusal per page load hands the content to the save and asks for a reload).
- **110** fixed in browsers with CSS `@scope`; without it the unscoped fallback repaints Nextcloud's header (named cost, §9.6).
- **111** open: Delete/Backspace/arrows/Enter/format keys/undo/save can overtake text still queued in the input adapter. Read from source + unit-level only.
- **112** open: cause unknown, repeat budget spent. A recurrence in a later counted locks run is read as a finding again (rules 2 and 5), now with the browser-side capture.

## What is next

1. **Tell the owner what changed on screen** (done in the session's last reply; the owner may want to hand-test on the dev instance: delete at a paragraph boundary, the title bar and close button, the hidden developer controls).
2. **Finding 111's round** — measure before designing (spec first, criteria before any run):
   - In both browsers with real keys (the production-UI runner already drives Chrome via CDP `Input.dispatchKeyEvent` and Firefox via WebDriver actions; reuse its login/open helpers), type a short marker and then press one of Backspace, Delete, ArrowLeft, Enter, Ctrl+S at a swept inter-key delay (e.g. 0, 10, 30, 60, 120 ms), and read the result from the engine (the document text / saved `content.xml`), not from the screen. The quantity is the fraction of trials where the non-text key landed before the last typed character, per key and per delay.
   - The fix is "wait only for what was queued before this key" — not `idle()`, which also waits for keys typed after. `input/input-adapter.js` is in the shell bundle (`e2/editor-shell-v2-bundle-v*.json`), so a fix there is a new shell generation (v56), a new page/session pin and another M3 re-count; a page-only barrier needs a way to know what the adapter has queued without reading its private fields. Decide after the measurement.
3. 112: nothing to do unless it recurs.

## Things this round taught

- **"Read as a finding first" paid for itself.** The red was not in the product, but reading it found that the runner had the browser-side evidence and threw it away (`drain()` before the click). A blind repeat would have been green and taught nothing.
- **Nextcloud's server side has three logs and only one has the 2xx.** The ddev router logs status 300–510 only (`~/.ddev/traefik/.static_config.yaml`); `nextcloud.log` has errors only; the in-container Apache `/var/log/apache2/access.log` (+0800) has everything. The router's request counter (the number after the referer) lets you reconcile the two.
- **A bounded repeat needs its outcomes written before it runs** — green means X, red means no third run and the step goes to C. That is what kept "one full green run" from becoming "eventually green".
- **Re-derive before you write.** Two of my sentences were wrong when first written (finding 112 said "every l10n" was missing; finding 110 said 285 elements outside the container — 285 is the whole page). Both were caught by recomputing from the stored report, not by rereading prose.
- The chain's verdict grep only matched `VERDICT|LANDS`, so `clean`, `LOCKS LAND`, `VERSIONS CORRECT`… showed as empty in `chain.txt`. Read each runner's log, not the chain line.

## Standing rules to carry

- Never two M3 runners (or an M3 probe) at once; each clears the whole `oc_files_lock` table.
- Counted runners refuse a dirty host tree; a host JS change means an `info.xml` bump + `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`; the buildId is content-addressed.
- A runner changed after its pin is a new pin (append to the spec), or its reports do not count; the locks runner's pin is now `1d3099a2…` (§12.1). `check_m3_same_second.py` and `probe_m3_save_throw.py` import `open_from_files` from it.
- `findings/evidence/**` and `handoff/**` English; specs, findings' prose zh-TW; specs append-only.
