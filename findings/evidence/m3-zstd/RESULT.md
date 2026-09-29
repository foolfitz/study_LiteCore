# M3 zstd representation of the engine — result: `ZSTD DELIVERED` (2026-09-30)

```
$ python3 wasm_sdk_probe/tools/check_m3_assets.py --score findings/evidence/m3-assets/runs/2026-09-29T163517+0000.json
ASSETS DELIVERED [SPEC-M3-asset-delivery+SPEC-M3-zstd] chrome=3/3 firefox=3/3 firefox-nozstd=3/3 problems=[]
```

`ZSTD DELIVERED` is that verdict on a report whose `criteria` include `SPEC-M3-zstd` (spec §4 as
amended after the review): K0–K2 of the asset-delivery spec plus Z0–Z2 and Z4-1 of
`specs/SPEC-M3-zstd.md`, in all three arms, 3/3 each. Counted run
`findings/evidence/m3-assets/runs/2026-09-29T163517+0000.json` (16:35:17Z–16:39:39Z, which is
2026-09-30 00:35–00:39 local).

## Bound to (written down before the run, `0972b6b2`; checked by reading the run's fields)

| What | Value |
|---|---|
| Host | `litecore` 0.2.5, `7420418`, tree clean (`hostDirty` empty) |
| Engine | buildId `7f4f4e2204b4a9ec` (unchanged from 0.2.4: Z0-4), MANIFEST schema `litecore-engine/2`, 22 files, 169,625,763 raw → 63,858,483 gzip / 48,527,295 zstd |
| Address | `7f4f4e2204b4a9ec-90d7bc2c` (0.2.4's was `…-566647db`: Z1-5) |
| Page | `e2-editor-app.js` `fc80050c…` in `dist/` and `web/` (unchanged); profile `e2-editor-v8` |
| Runner | `check_m3_assets.py` `3370dca99298…` |
| Static | `make test-e2-c-static` exit 0 (run by the runner) |
| Re-scored from the stored report | same verdict |
| `--red-cases` against it | 156, every one red in its own clause, exit 0 (`runs/red-cases-on-2026-09-29T163517.txt`) |
| Criteria | last changed in the spec's post-review §7 row (`2265debd`), before this run; none during it |
| Other ddev projects | none started or restarted during the chain (`docker ps` uptimes 26–35 h throughout) |

## What the nine runs show

| | chrome ×3 | firefox ×3 | firefox-nozstd ×3 |
|---|---|---|---|
| first open, bytes under the address (`%O`) | 48,556,848–48,556,859 | 48,556,851–48,556,854 | 63,887,907–63,887,913 |
| the six `D` rows | zstd size + 875–930 | zstd size + 875–930 | gzip size + 875–930 |
| second open, requests under the address | 2 (document 200, `sdk-manifest.json` 304) | 1 (document) | 1 (document) |
| seconds to the host's `done`, first / second | 2.50–2.56 / 1.87–1.90 | 2.91–2.98 / 2.53–2.57 | 2.90–2.93 / 2.54–2.87 |
| profile disk free | 12.9 GB (tmpfs) | 78–79 GB (ext4) | 78 GB (ext4) |

- **P1 held in every run**: in both browsers the page's module import, the worker's `importScripts`
  and `fetch`, and the pthreads' nested `new Worker(probe.js)` all got zstd. Chrome's CDP record
  (unscored) shows all 13 page-level modules `content-encoding: zstd`, including the 12 too small for
  `%O` to tell apart.
- **P2**: the Firefox pref took effect in every fallback run (gzip-sized rows), and the 40.9 MB gzip
  wasm stayed in Firefox's cache (second open: document only).
- **P4**: first open 48.56 MB against 63.9 MB on 0.2.4 (`runs/2026-09-29T151106`): 15.3 MB (24%)
  less, per user, per address.
- Seconds to `done` did not move against 0.2.4 (Chrome 2.51, Firefox 2.89–2.93 there). This is a
  loopback connection; the transfer is not the bottleneck here, so neither the saving nor any
  decoding cost shows. Registered, no threshold (spec §5).

## Z3: the other five M3 runners, counted on 0.2.5

Each against its own criteria, bindings written before the chain (`0972b6b2`), one runner at a
time, re-scored from the stored report and red-cased by the main session:

| Runner | Report | Verdict | Red cases |
|---|---|---|---|
| page honesty | `m3-page-honesty/runs/2026-09-29T163942+0000.json` | `PAGE HONEST` (15 arms × 2 browsers × 3) | 154/154 |
| locks and permissions | `m3-locks/runs/2026-09-29T174033+0000.json` | `LOCKS LAND` | 99/99 |
| versions | `m3-versions/runs/2026-09-29T182723+0000.json` | `VERSIONS CORRECT` (3/3, 3/3) | 68/68 |
| host entry | `m3-host-entry/runs/2026-09-29T183110Z.json` | `HOST_ENTRY LANDS` (open-save and conflict 3/3 per browser, broken arms 1/1) | 23/23 (the unmutated base green) |
| same-second saves | `m3-same-second/runs/2026-09-29T183630+0000.json` | `SAME-SECOND SAVES KEPT` (3/3 × 4 cells) | 70/70 |

Every report binds page `fc80050c…`, host `7420418` with an empty dirty list (host entry records it
under `instance.app`), and `make test-e2-c-static` exit 0 where the runner runs it. The chain ran
16:35Z–18:47Z; `docker ps` afterwards lists the same containers, each about two hours older, none
restarted.

So **the six M3 counted verdicts hold on 0.2.5**: `ZSTD DELIVERED` (the asset one), `PAGE HONEST`,
`LOCKS LAND`, `VERSIONS CORRECT`, `HOST_ENTRY LANDS`, `SAME-SECOND SAVES KEPT`. The red-case outputs
are beside each report (`red-cases-on-<stamp>.txt`).

## Z4

- Z4-1 (criterion, in every report of the zstd step): the release builder's `engine/` members are
  exactly `MANIFEST.json` plus each path's `.gz` and `.zst`, each matching the manifest.
- Z4-2 (measured): `build_m3_release.py --record findings/evidence/m3-zstd/release-0.2.5.json` →
  111,711,969 bytes (106.5 MiB), 52 members, two builds byte-identical. 0.2.4's archive would have
  been about 60.5 MiB.

## Not shown by this result

Spec §5: Safari, Edge, nginx; Chrome's gzip path in a browser; the page-level
`new Worker(sdk-worker.js)` request's coding (999 B apart); decoding CPU; an installed release
(install-elsewhere I3-1 / I3-8 on 0.2.5 belong to J).
