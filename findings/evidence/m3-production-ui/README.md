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

Observed costs (Bdel, Chrome, host): refusal → `ready` in generation 2 about 1.2 s after the
`restart-required` sample; the checkpoint save inside the refusal about 0.9 s (standalone dev
measurement on the same document).

## `screens/`

`editor-0.2.6-chrome.png`, `editor-0.2.6-chrome-unsaved.png`: the editor in Nextcloud on 0.2.6
(Chrome 151 headless, 1850×980), before and after typing one character.
