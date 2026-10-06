# SPEC-M3-production-ui — evidence

Findings 109 (a delete at a paragraph boundary lost unsaved work) and 110 (the host page restyled
Nextcloud's header and had no close button), and the production UI (developer controls hidden in
Nextcloud). Spec: `specs/SPEC-M3-production-ui.md` (criteria §4, addendum §7). Runner:
`wasm_sdk_probe/tools/check_m3_production_ui.py`. Document: the owner's `PMPC指南.odt` (563,149 bytes,
sha256 `7b336879…`), uploaded fresh per arm as `m3-109 測試.odt`; it is not in the repo.

## `prefix/` — the red-first runs (host 0.2.5 `7420418`, page `fc80050c…`, engine `7f4f4e22…`)

`prefix-0.2.5.json`: all five arms, Chrome 151 and Firefox 157. `prefix-0.2.5-chrome-rerun.json`:
Chrome Bctl and P again, after the first run's instrument fault (below).

| arm | Chrome | Firefox | why (read from the report, not only the score) |
|---|---|---|---|
| Bdel | red | red | marker typed (revision 0→3), Delete at the heading's end refused `EDITOR_BOUNDARY_UNSUPPORTED`, `restart-required`, generation stays 1, save refused `EDITOR_NOT_READY`, server file unchanged (sha = the upload) |
| Bbs | red | red | the same with Backspace at the paragraph's start |
| A1-3 | red | red | in `restart-required`, 1 of 21 toolbar buttons disabled |
| Bctl | pass (rerun) | pass | mid-text Backspace: revision +1, generation 1 |
| S | red | red | 178 elements outside the container change when the product stylesheet is disabled, `body` included (`display`, background colour and image); editor `body` `rgb(244,246,248)` / no image against Files' `rgb(0,103,158)` + theme image |
| P | red | red | A3-1: ten developer controls and the provenance text visible; no title, no close button, no unsaved mark. The four real keys mid-text all +1 in both browsers. |

So **Firefox reproduces 109 as Chrome does** (it had not been measured).

### `b3x-red-0.2.6-prefix.json` — A1-5's red case (B1, spec §9.3), 2026-10-06

Host 0.2.6 `fa08307` with the engine package as served before the B1 fix (buildId `253730c6…`, page
`d41ae604…`, session `a4f8c219…`); runner `2f923764` (`runnerSha256` `95bbe9e1…`). One B3x arm per
browser, Chrome 151 and Firefox 157. Spec §9.4 predicted red in both, at the ceiling.

| | Chrome | Firefox |
|---|---|---|
| refusal 1 (Delete at the heading's end) | generation 1→2, `ready` | 1→2, `ready` |
| refusal 2 (Backspace at the paragraph's start) | 2→3, `ready` | 2→3, `ready` |
| refusal 3 (Delete at the heading's end) | stays 3, **`recoverable-error`** | stays 3, **`recoverable-error`** |
| notice after refusal 3 | no `data-limit`; text 「這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。」, its button disabled | same |
| server file | none of `zqa`/`zqb`/`zqc` | none |
| notice button | disabled, so no reload; generation still 3 | same |

Red for the predicted reason in both browsers; refusals 1 and 2 each opened a new Worker, so it is
not vacuous. **Measured on the way (review item 3):** after each reopen the next marker was typed
without clicking, and none of its keys landed (revision stayed 0 in generations 2 and 3, both
browsers) — the reopened page did not give the input sink its focus back. It was read from source
only until now.

Instrument fault in the first Chrome run (Bctl, P): `websockets ConnectionClosedError 1009` — the
save's `Network.requestWillBeSent` carried the 573 KB PUT body (1.37 MB JSON-escaped), past the CDP
socket's 1 MiB frame limit. The runner's Chrome side now disables the Network domain.

## `shakedown/` — host 0.2.6

- `shake1-0.2.6.json` (host `96a13b9`, engine `253730c6…`, page `d41ae604…`, session `a4f8c219…`):
  Bdel, Bbs, Bctl, S pass in both browsers. P red in both on A3-2 "unsaved mark shown None" — an
  instrument fault (the 1.5 s window started before `keyed()`, which itself waits longer); and,
  found by reading the landing URL rather than by the score, the close button landed on
  `/apps/files/index.php/apps/files/files/<id>` (a hand-built URL under pretty URLs). Re-scored with
  the anchored path check, this report is red on that too.
- `shake2-0.2.6-P.json` (host `fa08307`: the close URL from `files.view.indexViewFileid`): P passes in
  both browsers; close lands on `/apps/files/files/<id>?dir=/`; dirty close asked by the host with
  reason `page` (Chrome: dialog dismissed, still on the editor; Firefox: the driver accepts the prompt).
- Red cases (`--red-cases` on shake1's B/S runs + shake2's P runs): 15/15 mutations turn the score red.

- `shake3-0.2.7.json` (host 0.2.7 `0488586`, engine buildId `63e149f3…`, page `1c438c36…`, session
  `3f5f754b…`; the B1 fix `04d19fcd`; runner with review items 10, 11, 13, 14 and the B3x arm): all six
  arms, both browsers. Bdel, Bbs, Bctl, S, P pass in both. **B3x red in both, on one line:** the
  server's file lacks `zqb` and `zqc`. Everything else in A1-5 held (third refusal not restarted,
  `restart-required`, `data-limit=saved` 0.78 s / 1.09 s after the key with the host's last save
  `settled` and `saved`, reload not asked, the reload opened the rescued bytes, lock `held`). Read
  from the report: after each reopen the FIRST key typed without clicking (`z`) left the revision at
  0 and the next two landed, in both browsers. The page gave the sink its focus only after `run()`
  had also awaited the repaint, so a key typed once the pill said 就緒 went to the body (review
  2026-10-06b item 10 had predicted this). Fixed in the page (focus inside the operation, right after
  `restart()` returns); re-run as shake4. Also measured here for the first time with the clock at the
  key (review item 13): the unsaved mark appeared 0.49 s (Chrome) / 0.14 s (Firefox) after the key.
  S compared 1065 (Chrome) / 974 (Firefox) properties over 285 elements, `--accent` resolves in the
  container, 0 elements outside change.
- `shake4-0.2.7-focus.json` (host 0.2.7 `0488586`, engine buildId `fabdb50e…`, page `e97d6e03…`
  with the focus fix `bc95b342`, session `3f5f754b…`): B3x, Bdel, Bbs, both browsers, **all pass**.
  B3x: every key typed after a reopen without clicking landed (revision 0→1→2→3 in generations 2
  and 3); third refusal not restarted; `data-limit=saved` 0.78 s (Chrome) / 1.09 s (Firefox) after
  the key, the host's last save `settled`/`saved`; `zqa`, `zqb`, `zqc` all in the server's file with
  no save pressed; the host's unsaved mark gone 0.51 s / 0.31 s later; the reload through the
  notice's button was not asked about (the recorder saw the `beforeunload` fire); generation 1
  after it, the host's lock `held`, and the page opened the rescued bytes.
- Re-scored with the final scorer and `--expect-red` (review item 17): `prefix/prefix-0.2.5.json`,
  `prefix-0.2.5-chrome-rerun.json` and `b3x-red-0.2.6-prefix.json` stay red for their original
  reasons (S additionally red on the two fields those older reports do not have); Bctl, the positive
  control, passes.

Observed costs (Bdel, Chrome, host): refusal → `ready` in generation 2 about 1.2 s after the
`restart-required` sample; the checkpoint save inside the refusal about 0.9 s (standalone dev
measurement on the same document).

## `no-scope/` — a browser without CSS @scope (review item 8, spec §9.6)

`probe_m3_no_scope.py`, Firefox 157 with `layout.css.at-scope.enabled` set by the probe (standing in
for a browser without @scope; Firefox ESR 140 is not installed here). One open of the usual test file
on host 0.2.6 `fa08307`, engine buildId `253730c6…`.

| | pref on (control) | pref off |
|---|---|---|
| `typeof CSSScopeRule` | `function` | `undefined` |
| `#notice` / `#expired` / `#sink` visible | no / no / no | **yes / yes / yes** |
| A3-1 inventory: stray controls / stray text | 0 / 0 | 0 / **8** (the `#expired` banner's text) |
| screenshot | `0.2.6-scope-on.png` | `0.2.6-scope-off.png`: **no document on screen at all**, only a column of toolbar buttons and the notice's 「回到檢查點」 |

So on 0.2.6 the whole product sheet is dropped without @scope and the editor is unusable, not merely
unstyled. The control shows the probe can tell the two apart.

### Host 0.2.7 `0488586` — criterion A2-4 (spec §9.6), same probe, same engine package

| | pref on | pref off |
|---|---|---|
| `typeof CSSScopeRule` | `function` | `undefined` |
| host `data-litecore` `.scope` | `scoped` | `unscoped-fallback` |
| `#litecore-unscoped` `media` | `not all` (only the scoped sheet in force) | `all` |
| `#notice` / `#expired` / `#sink` visible | no / no / no | no / no / no |
| A3-1 inventory: stray controls / stray text | 0 / 0 | 0 / 0 |
| state after open | `ready` | `ready` |

A2-4 holds as predicted. The fallback's cost is visible in `0.2.7-scope-off.png`: Nextcloud's header
is repainted light again (finding 110's look) while the editor's layout is intact. In both 0.2.7
screenshots the page itself is blank white: the screenshot is taken at `ready` and does not show the
document in either mode, so it says nothing about rendering; what the probe measures is the layout
and which parts are exposed.

## `screens/`

`editor-0.2.6-chrome.png`, `editor-0.2.6-chrome-unsaved.png`: the editor in Nextcloud on 0.2.6
(Chrome 151 headless, 1850×980), before and after typing one character.
