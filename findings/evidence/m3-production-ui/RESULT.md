# M3 production UI — result (2026-10-06): every criterion holds, R after one locks repeat

Spec: `specs/SPEC-M3-production-ui.md` §4, as amended by §7, §9 (B1), §9.6 (`@scope`), §10 and
§11 (bindings). Findings 109 (a delete at a paragraph boundary lost unsaved work) and 110 (the
host page repainted Nextcloud's header and had no close button), and the production UI (A3).
Runner: `wasm_sdk_probe/tools/check_m3_production_ui.py --counted`, sha256 `d23043dc…` (= §11;
every report carries its own `runnerSha256`).

The spec names no verdict token for this step. What it settles is written below as criteria.

## Bound to (written down before any counted run, `533578d7`; checked by each report's `static`)

| What | Value | How it is checked |
|---|---|---|
| Page `e2-editor-app.js` (dist = served) | `e97d6e03…` | `counted_bindings` refuses otherwise |
| Session subclass `narrow-editor-v2-session.js` (served) | `3f5f754b…` | `counted_bindings` |
| Host | `litecore` 0.2.7, `0488586`, clean tree | `counted_bindings` |
| Shell generation | v55, `2470765a…` (freeze tool's question mode, exit 0, same digest) | `counted_bindings` |
| Engine package | buildId `fabdb50ecd038802` | **read from the reports by hand**: it is in `static.buildId` of all three, but `counted_bindings` does not compare it |
| Owner's document | `PMPC指南.odt`, 563,149 bytes, `7b336879…`, 0 markers before any arm | the runner refuses another document; a document that already holds a marker fails the score (review 1-14) |

Dev instance `litecore.ddev.site`, Nextcloud 34.0.2, Chrome 151.0.7922.169 and Firefox 157.0.

## Counted runs (`runs/`)

Written by `wasm_sdk_probe/build/m3-count-2026-10-06/chain.sh` (not in the repo; its log lines
are quoted in the handoff), after all six M3 runners' shakedowns on the same page and host were
clean, one runner at a time:

| Report | Arms × rounds | Window (UTC) |
|---|---|---|
| `counted-B-x3.json` | Bdel, Bbs × 3 per browser | 02:38–02:43 |
| `counted-ctl-S-P.json` | Bctl, S, P × 1 per browser | 02:43–02:46 |
| `counted-B3x-x2.json` | B3x × 2 per browser | 02:46–02:50 |

### Per criterion

| Criterion | What the runs show | Chrome | Firefox |
|---|---|---|---|
| **A1-2** (B-del, B-bs, 3/3 each) | marker typed with real keys (revision 0→3), click to the boundary, the real key refused, the page reopened by itself (generation 1→2), save pressed, the server's `content.xml` holds the marker | Bdel 3/3, Bbs 3/3 | Bdel 3/3, Bbs 3/3 |
| A1-2 positive control (B-ctl, 1 each) | mid-text Backspace: revision 3→4, generation stays 1 (132 ms / 90 ms) | 1/1 | 1/1 |
| **A1-3** | every B arm has blocked samples (`restart-required`, 2 per arm), and in each all 21 toolbar buttons are disabled | 12/12 arms | |
| **A1-5** (B-3x, 2/2 each) | refusals 1 and 2 each opened a new Worker (1→2→3, `ready`); after each reopen the next marker went in **without a click** (revision 0→1→2→3 in generations 2 and 3); refusal 3 did not reopen (generation stays 3, `restart-required`, not `recoverable-error`); `#notice[data-limit]` = `saved` 0.79 s / 0.78 s (Chrome) and 1.09 s / 1.09 s (Firefox) after the key, in the same read the host's last save `settled` with outcome `saved`; no save pressed and the server's file holds `zqa`, `zqb`, `zqc` (none before); the host's unsaved mark gone 0.30 / 0.20 s (Chrome), 0.21 / 0.10 s (Firefox) later; the notice's 「重新整理頁面」 reload was not asked about (the recorder saw `beforeunload` fire, 0 guards); after the reload generation 1, the host's lock `held`, and the page opened the bytes now on the server (sha256 equal) | 2/2 | 2/2 |
| **A2-1** | product sheet disabled vs enabled: 0 of the elements outside `#litecore-editor-root` change, over the browser's own property list (1065 / 974 properties; 285 elements on the page, inside and outside together); 87 inside change; `--accent` resolves in the container (`#3178c6`) | 1/1 | 1/1 |
| **A2-2** | editor page `body`: `rgb(0, 103, 158)` + the theme image, equal to the Files page in the same browser session | 1/1 | 1/1 |
| **A2-3** | title bar shows `m3-109 測試.odt` and a visible close button; clean close → `/apps/files/files/<id>?dir=/`, no `openfile`, no editor on the landing page, the lock released 0.3 s later; dirty close → the host guarded (one guard, reason `page`) | 1/1, stayed on the editor after "stay" | 1/1, left (geckodriver accepts the prompt; named limit, spec §10.3 1-16) |
| **A3-1** | every visible control is in the kept set (close, undo, redo, B/I/U/S, clear format, heading, body, three list buttons, save); 0 stray controls, 0 stray text | 1/1 | 1/1 |
| **A3-2** | real keys mid-text: `a`, Backspace, Delete, Enter, Shift+Enter each +1 revision, generation 1 throughout; unsaved mark shown 0.33 s (Chrome) / 0.03 s (Firefox) after the key, gone as the save landed | 1/1 | 1/1 |

**Red cases** (review 1-17): the runner's `--red-cases` needs a passing run of every arm in one
report, and the counted plan wrote three. The three reports' `runs` were pooled into one file
(the `static` blocks are identical) and red-cased: **30/30** mutations turn the score red
(`runs/red-cases-on-counted-pooled.txt`). Recipe: load the three JSON files, concatenate their
`runs` under the first report's other fields, pass the file to `--red-cases`. Each report alone:
B-x3 4/4, ctl-S-P 13/13, B3x-x2 13/13 of the mutations that have an arm in it.

Not recorded in the report: the time from the refused key to `ready`. What is recorded is the first
blocked sample to `ready` in generation 2: 1.15–1.21 s (Chrome), 2.07–2.19 s (Firefox); the
checkpoint save inside the refusal (about 0.9 s in development) comes before the blocked sample.
The prediction "2–4 s from the key" (§5) is therefore neither confirmed nor refuted by these runs.

### Criteria that are not browser runs

| Criterion | Where it was satisfied |
|---|---|
| A1-1 (unit) | six tests in `narrow-editor-v2-session.test.mjs` (finding 109 section); red cases on 2026-10-06: drop the checkpoint call → 3 red, `restartKeepsContent` as `!dirty \|\| hasCheckpoint` → 1 red |
| A1-4 (unit) | eight tests (session 4, page functions compiled from source 4), base 130/0; the three mutations red 4 / 2 / 1 (`ec951c41`); 135/0 after review 2 (`04d19fcd`) |
| A1-2 / A2-1 / A3-1 red cases | `prefix/prefix-0.2.5*.json`, red for the predicted reasons in both browsers (README) |
| A1-5 red case | `prefix/b3x-red-0.2.6-prefix.json`, red at the ceiling in both browsers (README) |
| A2-4 (`@scope` fallback) | `no-scope/0.2.7-scope-{on,off}.json` on host 0.2.7 (README) |
| R: `make test-e2-c-static` exit 0 | recorded by the counted page-honesty run (`static.testStatic` = 0) |
| R: product-path net on v55 | `product-path/`: v8 and v14 each 40 PASS / 2 NE, cell for cell the same as v54 |

## R: the six M3 runners, counted on page `e97d6e03…` and host 0.2.7

One runner at a time in the same chain, after the production UI runs, each scored by its own
runner and red-cased by the main session on its own counted report (outputs beside each report):

| Runner | Report | Verdict | Red cases |
|---|---|---|---|
| page honesty | `m3-page-honesty/runs/2026-10-06T025007+0000.json` | `PAGE HONEST` (15 arms × 2 browsers × 3) | 154 red, 0 not |
| locks and permissions | `m3-locks/runs/2026-10-06T035016+0000.json` | **`LOCKS DO NOT LAND`** (51/52; `chrome:foreign-lock` 2/3) | 99 red, 0 not |
| versions | `m3-versions/runs/2026-10-06T043734+0000.json` | `VERSIONS CORRECT` (3/3, 3/3) | 68 red, 0 not |
| assets | `m3-assets/runs/2026-10-06T044117+0000.json` | `ASSETS DELIVERED` (chrome, firefox, firefox-nozstd 3/3 each) | 156 red, 0 not |
| host entry | `m3-host-entry/runs/2026-10-06T044528Z.json` | `HOST_ENTRY LANDS` (open-save and conflict 3/3 per browser, broken arms 1/1) | 23 red, base green |
| same-second saves | `m3-same-second/runs/2026-10-06T045028+0000.json` | `SAME-SECOND SAVES KEPT` (3/3 × 4 cells) | 70 red, 0 not |

Every report binds page `e97d6e03…` and host `0488586` with an empty dirty list (host entry records it
under its instance block); `make test-e2-c-static` exit 0 where the runner runs it.

**The locks red** is finding 112: in one Chrome K5 run the Files page rendered no row for 60 s and the
product page was never requested (server logs in `../112/`). It is not the pre-written rule 2 case,
so it was read as a finding first; the owner sent it to fable, whose ruling (A, bounded) allows one
full repeat with an instrument-only runner change (`check_m3_locks.py` `6e6b2fa4…` → `1d3099a2…`,
scoring proven byte-identical; spec §12, `m3-locks/README.md` rule 5). The 10-06 locks report keeps
its verdict. **Until the repeat is green, R does not hold, and findings 109 and 110 stay unfixed.**

**The repeat** (05:30–06:17 UTC, the only process against the instance; chain log
`m3-locks/runs/chain-2026-10-06b.txt`):

| Runner | Report | Verdict | Red cases |
|---|---|---|---|
| locks and permissions, repeat | `m3-locks/runs/2026-10-06T053046+0000.json` | **`LOCKS LAND`** (52/52, `problems=[]`, no fatal) | 99 red, 0 not |

Every pass condition of rule 5.2 holds: `runnerSha256` `1d3099a2…` (the §12.1 pin), page `e97d6e03…`,
host `0488586` clean, `testStatic` 0, `filesRowSeconds` in 52/52 runs and no diagnostic triggered. The
row was there 0.00–0.07 s (Chrome, median 0.05) and 0.00–0.26 s (Firefox, median 0.01) after the
Files page's load returned, so the 60 s of finding 112 was a stall, not a slow page. By the outcome
fixed before the repeat, **R's locks cell holds on 0.2.7**; the first report keeps `LOCKS DO NOT LAND`.

So **R holds**: the six M3 verdicts are counted on page `e97d6e03…` and host 0.2.7, the product-path net
on v55 equals v54 cell for cell, and `make test-e2-c-static` exits 0.

## What this settles

- **Finding 109**: fixed for the paths measured. A refused delete at a paragraph boundary no longer
  loses what was sent to the engine: the first two refusals per page load reopen with nothing
  lost; the third and later hand the content to the host's save and ask for a page reload.
- **Finding 110**: fixed in browsers with CSS `@scope` (Chrome 151, Firefox 157 measured). Without
  `@scope` the host falls back to the unscoped sheet: the editor works and exposes nothing
  internal, but Nextcloud's header is repainted again (§9.6, the fallback's named cost).
- **A3**: the developer controls are hidden in Nextcloud; the keys that replace the hidden editing
  buttons work.

## What it does not settle

- **Finding 111** (Delete, Backspace and arrows can overtake text still in the input adapter's
  queue): open. §10.1 narrowed the claim: zero loss covers what had reached the engine when the
  refusal came; characters still queued in the adapter are not covered.
- Merging paragraphs (C) is still refused by the engine; the user sees a reopen, the caret goes to
  the start of the document and the undo stack is emptied (§6).
- Spec §10.3 registrations stand as written there, among them: the checkpoint save's 5 s limit on
  large documents (named limit), the stale-checkpoint notice path never turned red (behaviour with
  nothing guarding it), Ctrl+S in a stopped session falls to the browser (work item), the IME
  hypothesis Q5 (unverified), close from a subfolder not measured, A3-1 does not read `title`.
- Rounds 3 and later per page load are covered by two B3x runs per browser, on this document only.
- **Finding 112** (the Files page in Chrome once requested none of its own bundles and listed
  nothing): registered, cause unknown. The repeat did not recur it; the capture now in the locks
  runner will keep the browser's side if it does.
