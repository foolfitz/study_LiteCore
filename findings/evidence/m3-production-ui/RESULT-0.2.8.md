# M3 production UI on v19 (host 0.2.8) — result (2026-10-09)

Spec: `specs/SPEC-M3-production-ui.md` §13 (R re-bound to v19, written before any 0.2.8 run, `9b26cbb1`; the runner pin in §13.7 as corrected, `c54cd6e3`). The 0.2.7 result stays in `RESULT.md`; this file is the v19 one. Runner `wasm_sdk_probe/tools/check_m3_production_ui.py --counted`, sha256 `3e19651098fa9926581e4cc1eea55bed73c8eda06895783835105e615ea4aead` in every report.

## Bound to (spec §13.5; checked by each report's `static`)

| What | Value | How it is checked |
|---|---|---|
| Page `e2-editor-app.js` (dist = served) | `e00ab76a…` | `counted_bindings` |
| Session `narrow-editor-v2-session.js` (served) | `ee3e53a2…` | `counted_bindings` |
| Host | `litecore` 0.2.8, `4140e00`, clean tree | `counted_bindings` |
| Shell generation | v57, `1aed21b1…` (freeze tool's question mode, exit 0) | `counted_bindings` |
| Engine package | buildId `63656ee4aa7e4059` | read from the reports by hand (`static.buildId`, the same in all three), as on 0.2.7 |
| Owner's document | `7b336879…`, 0 markers before any arm | the runner refuses another document; a marker already present fails the score |
| References | original's paragraph text `d646dda7…`, Writer's key arm `1f53faf4…` (native R-host round) | runner constants |

Chrome 151.0.7922.169, Firefox 157.0. The three reports' `static` blocks are identical.

## Counted runs (`runs-0.2.8/`, written by `wasm_sdk_probe/build/m3-count-2026-10-09/chain.sh` after the six M3 runners' shakedowns were clean)

| Report | Arms × rounds | Window (UTC, 2026-10-08) |
|---|---|---|
| `counted-KR-x3.json` | Kdel, Kbs, Rbs, Rdel × 3 per browser | 17:42–17:54 |
| `counted-ctl-S-P.json` | Bctl, S, P × 1 per browser | 17:54–17:56 |
| `counted-B3x-x2.json` | B3x × 2 per browser | 17:56–18:00 |

Each report scores `allPass: true` on its own. **Red cases: 40/40** on the three reports' runs pooled (`red-cases-on-counted-pooled.txt`; recipe as on 0.2.7).

### Per criterion

| Criterion | What the runs show | Chrome | Firefox |
|---|---|---|---|
| **A1-2′ K** (Kdel, Kbs, 3/3 each) | marker typed with real keys (revision 0→3); Kdel: one Delete at the heading's end, `⌦ 前刪` 169–170 ms (Chrome) / 164–165 ms (Firefox), revision 3→4; Kbs: two Backspaces at the body's start, 150–154 + 168–173 ms / 138–141 + 171–173 ms, revision 3→4→5; generation 1 throughout, no sample outside `ready`/`busy`; the server's file has the marker once and its paragraph text (marker removed) is Writer's key arm's (`1f53faf4…`, 210 paragraphs) in all 12 | Kdel 3/3, Kbs 3/3 | Kdel 3/3, Kbs 3/3 |
| **A1-2′ R** (Rbs, Rdel, 3/3 each) | Rbs: marker mid-text, the first line, Home (842–905 ms: the C-half checkpoint and the move, see the shakedown README), Backspace refused and the page reopened by itself (`重新載入` 1024–1097 ms / 1915–1952 ms), generation 1→2; Rdel: the last line, End (277–278 ms), the marker typed there, Delete refused and reopened (1020–1029 ms / 1916–1947 ms); the server's file has the marker once and its text (marker removed) is the original's (`d646dda7…`) in all 12 | Rbs 3/3, Rdel 3/3 | Rbs 3/3, Rdel 3/3 |
| **A1-3′** | every R arm has blocked samples (2 per arm) and in each all toolbar buttons are disabled; every B3x run likewise | 6/6 R arms, 2/2 B3x | 6/6, 2/2 |
| A1-2 positive control (Bctl) | mid-text Backspace, revision 3→4 (105 / 101 ms), generation 1 | 1/1 | 1/1 |
| **A1-5** (B3x, 2/2 each) | three refusals at the document's start; generations 1→2→3→3 (`ready`, `ready`, `restart-required`); `data-limit` `saved` 0.48 s after the third key in all four runs, the host's last save settled `saved` in the same read; no save pressed and the server holds `zqa`, `zqb`, `zqc`; unsaved mark gone 0.20 / 0.20 s (Chrome), 0.31 / 0.41 s (Firefox); the reload not asked about; after it generation 1, lock `held` | 2/2 | 2/2 |
| **A2-1** | 0 elements outside the container change, over 1065 / 974 properties, 285 elements; 87 inside change; `--accent` `#3178c6` | 1/1 | 1/1 |
| **A2-2** | editor `body` background equals the Files page's | 1/1 | 1/1 |
| **A2-3** | close → `/apps/files/files/7340?dir=/`, lock released; dirty close guarded by the host | 1/1, stayed after "stay" | 1/1, left (geckodriver accepts the prompt; named limit §10.3 1-16) |
| **A3-1** | 0 stray controls, 0 stray text | 1/1 | 1/1 |
| **A3-2** | `a`, Backspace, Delete, Enter, Shift+Enter mid-text each +1 revision, generation 1; unsaved mark shown 0.34 s / 0.13 s after the key, gone as the save landed | 1/1 | 1/1 |

Predictions (§13.6): K, R, B3x, Bctl, S, P all as predicted. The one cell predicted wrong was the red case's Rbs positive control on v8 (shakedown README).

## R's other cells (spec §13.4)

The six M3 runners, re-pinned to 0.2.8/v19 in `92281cc1` (spec §13.5), each shaken down clean and then counted on the same host and page, one at a time (`runs-0.2.8/chain-2026-10-09.sh`, log `chain-2026-10-09.txt`, 2026-10-08 16:39–20:11 UTC). Red cases on each counted report, each runner's own `--red-cases`, all exit 0 (`runs-0.2.8/red-cases-six.txt`).

| Runner | Counted report | Verdict | Red cases |
|---|---|---|---|
| page honesty | `m3-page-honesty/runs/2026-10-08T180043+0000.json` | **PAGE HONEST** (every cell 3/3 per browser) | 154 red, 0 not |
| locks | `m3-locks/runs/2026-10-08T190058+0000.json` | **LOCKS LAND** (first run, no repeat) | 99 red |
| versions | `m3-versions/runs/2026-10-08T194718+0000.json` | **VERSIONS CORRECT** (3/3, 3/3) | 68 red |
| assets | `m3-assets/runs/2026-10-08T195114+0000.json` | **ASSETS DELIVERED** (chrome, firefox, firefox-nozstd 3/3) | 156 red (incl. Z2-2 and Z2 D′ on `cjk-sub-e10`) |
| host entry | `m3-host-entry/runs/2026-10-08T195525Z.json` | **HOST_ENTRY LANDS** | 23 red (the baseline green) |
| same second | `m3-same-second/runs/2026-10-08T200038+0000.json` | **SAME-SECOND SAVES KEPT** (3/3 ×4) | 70 red |

- Product-path net (merge spec M2-5): **X5 counts**, as §13.4 decided before the runs (`v19/x5-product-path/`, page `e00ab76a…`, served shell = v57).
- `make test-e2-c-static`: exit 0 on the tree after the chain (`89793022`; `runs-0.2.8/test-e2-c-static.txt`).
- Host merge arm = Writer's key: by A1-2′ K above (paragraph text; the byte form withdrawn, §13.3).

**R holds on host 0.2.8.** Every M3 verdict that bound 0.2.7 now also binds 0.2.8 with v19, page `e00ab76a…`, shell v57. Since the cutover, the boundary keys at a heading's end and a paragraph's start on the owner's document are Writer's own (a merge, or Writer's first step), with no reopen; the refusals left on that document are its two ends, and they keep the unsaved work as 0.2.7 did.
