# M3 production UI on v19 (host 0.2.8) — shakedown and the K red case (2026-10-09, not counted)

Spec: `specs/SPEC-M3-production-ui.md` §13 (written before any of these runs, `9b26cbb1`). Runner `wasm_sdk_probe/tools/check_m3_production_ui.py` at `c823b955`, sha256 `3e19651098fa9926…` (every report carries it). Host `litecore` 0.2.8 (`4140e00`), page `e00ab76a…`, shell v57 `1aed21b1…`, engine buildId `63656ee4aa7e4059`, the owner's document `7b336879…`. Chrome 151, Firefox 157. None of these runs is counted (`counted: false`).

## Shakedown on v19

| Report | Arms | Result |
|---|---|---|
| `sd1-chrome-KR.json` | Kdel, Kbs, Rbs, Rdel, Chrome | 4/4 pass |
| `sd1-firefox-KR.json` | the same, Firefox | 4/4 pass |
| `sd2-rest.json` | Bctl, S, P, B3x, both browsers | 8/8 pass |
| `red-cases-pooled.txt` | the three reports' runs pooled | 40/40 mutations turn the score red |

What the arms did (from the reports):

- **Kdel**: one Delete at the heading's end, `⌦ 前刪 177 ms` (Chrome) / `166 ms` (Firefox), revision 3 → 4, generation 1 throughout, only `ready`/`busy` in the timeline; the server's file has the marker once and its paragraph text (marker removed) is the native key arm's (`1f53faf4…`, 210 paragraphs).
- **Kbs**: two Backspaces at the first body paragraph's start, 155 + 171 ms / 146 + 171 ms, revision 3 → 4 → 5, generation 1; the same text as Kdel.
- **Rbs**: marker mid-text, the first line, Home, Backspace: refused and reopened (`重新載入 1139 ms` / `2049 ms`), generation 1 → 2, blocked samples with all 21 buttons disabled; the server's text (marker removed) is the original's (`d646dda7…`, 211 paragraphs).
- **Rdel**: the last line, End, the marker typed there, Delete: the same (`重新載入 1094 ms` / `2051 ms`).
- **B3x**: three refusals at the document's start, generations 1 → 2 → 3 → 3, `data-limit` `saved` 0.48 s after the third key in both browsers, `zqa`, `zqb`, `zqc` on the server, reload not asked, generation 1 after it.
- **Bctl, S, P**: as on 0.2.7; P's five keys mid-text each +1 revision in generation 1.

## The K red case (spec §13.3 「紅一次（K）」)

`red-once-v8-engine-chrome.json`: the dev instance's `engine/` was moved aside and replaced by the archived 0.2.7 package (`wasm_sdk_probe/build/archive/host-0.2.7-engine-fabdb50ecd038802/`: v8, page `e97d6e03…`); Kdel, Kbs, Rbs, Rdel once each in Chrome; then the v19 `engine/` was moved back (its `MANIFEST.json` sha256 `ade0a2e8…` before and after, buildId `63656ee4…`). The report's `static.buildId` is `fabdb50ecd038802`.

| Arm | Predicted (§13.6) | Result |
|---|---|---|
| Kdel | red, generation 1 → 2 | **red as predicted**: the Delete was refused and the page reopened (`重新載入 1285 ms`), generation 1 → 2, the server's text = the original's (v8 kept the marker and merged nothing) |
| Kbs | red, generation 1 → 2 | **red as predicted**: the first Backspace refused and reopened (generation 2); the second, now at the document's start, refused again (generation 3) |
| Rdel | green | **green** (End 69 ms, refused, reopened, generation 1 → 2, text = original) |
| Rbs | green | **red, not for the reason the control is about**: `Home` (`move-line-home`) at the start of the document never finished on v8 — the page took a checkpoint (r3) before the move, then `TIMEOUT：editorActionV2 timed out after 30000 ms`, `recoverable-error`; the Backspace was pressed into a stopped session, nothing was saved (0 saves) |

So the K red case holds (both K arms red, and red on the reopen). The positive control holds at the document's end; at its start it was not reached on v8, because of a v8 move that hangs at the document boundary — the shape of finding 096 (a move at a document boundary kills the session). Not re-run: the control was there to show that the two ends are refusals on v8 as well, the end showed it, and the start is a refusal on v19 in all eight attempts here (Rbs ×2, B3x ×6).

## Observation (not judged; a lead for finding 096)

On v19 the same `Home` at the document's start finished in all 8 attempts, taking **717–981 ms** (Rbs 981 / 910, B3x 892 / 717 / 753 / 897 / 886 / 913), where on v8 it hung for 30 s once in once. `End` at the document's end took 278 ms on v19 and 69 ms on v8. Both are far slower than a caret placement (≈200 ms) or a merge (≈160 ms). Whether v19's engine poll (finding 117's fix) is what ends v19's wait is not measured.
