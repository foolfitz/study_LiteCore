# M3 zstd representation of the engine — evidence

Spec: `specs/SPEC-M3-zstd.md` (item G of `handoff/HANDOFF-2026-09-29h-page-honest-counted.md`).

## Step 0: offline sizes (2026-09-30)

`offline-sizes-2026-09-30.json`, produced by `offline_sizes.py` and `v14_sizes.py` (copied here as
they ran; they read `wasm_sdk_probe/dist` and the `litecore` app's `engine/MANIFEST.json`, write
nothing but stdout). Python 3.14 `compression.zstd`, libzstd 1.5.7, level 19, single thread. The
gzip sizes are the packaged ones from `engine/MANIFEST.json` (buildId `7f4f4e2204b4a9ec`, page
`fc80050c…`); every zstd frame was decoded back and compared with the source bytes.

- The shipped closure (22 files): 169,625,763 bytes raw, 63,858,483 gzip, **48,527,295 zstd** (−24%).
- The three big files' frames have Window_Size 8,388,608 (2^23); the others are single-segment
  frames (the window is the content size, at most 181,072). The script records `window: null` for a
  single-segment frame; its `contentSize` is the window.
- Six files differ by ≥ 1,500 bytes between gzip and zstd (the set `D` of spec §4 Z2): the wasm, both
  `.data`, the base `.metadata`, `probe.js`, `e2-editor-app.js`. The other 16 differ by ≤ 999;
  `editor-shell/state-machine.js` is 3 bytes *larger* as zstd.
- **The a11y candidate's wasm** (`profiles/e2-editor-v14/probe.wasm`, 135,237,060 bytes) is
  **47,987,197 bytes of gzip -9 (mtime 0)** — over the packager's `MAX_GZ_BYTES` = 45,000,000, so
  today's `package_m3_engine.py` refuses to package that core. As zstd -19 it is 36,078,637.

Not measured here: what the browsers send in `Accept-Encoding` (spec §2, prediction P1; Z2-1 is its
measurement).

## Shakedown 1 (host 0.2.5, uncommitted tree identical to `7420418`)

`findings/evidence/m3-assets/shakedown/2026-09-29T161427+0000.json` (UTC; 2026-09-30 00:14 local),
`check_m3_assets.py --label shakedown --repeats 1`: chrome 1/1, firefox 1/1, firefox-nozstd 1/1,
every K and Z clause clean. `--red-cases`: 147 cases, every one red in its own clause
(`red-cases-on-2026-09-29T161427.txt` beside the report).

- Address `7f4f4e2204b4a9ec-90d7bc2c` (build id unchanged, policy hash moved: P3).
- First open, bytes under the address (Apache `%O`): Chrome 48,556,860 (22 requests); Firefox the
  same six `D` rows as zstd; firefox-nozstd 63,887,915, every `D` row gzip-sized (P2: the pref took
  effect). Second open: Chrome 2 requests (the document and the `sdk-manifest.json` 304), Firefox
  and firefox-nozstd 1 (the document).
- The `D` rows in both zstd arms: `e2-editor-app.js` 32,371, `probe.js` 34,568, `probe.wasm`
  30,671,453, base `.metadata` 16,964, base `.data` 5,533,560, cjk `.data` 12,171,668 — each its
  zstd size plus 875–930 bytes of headers. So the page's module import, the worker's
  `importScripts`/`fetch` all advertised zstd in both browsers (P1, one round each so far).

## Z4: the release archive (measured, registered)

Host `7420418`, engine buildId `7f4f4e2204b4a9ec` with both codings. Same command as the asset
spec's K4 (mtime `2026-09-30 00:00Z`), built in the session scratchpad, not kept:
**111,689,706 bytes (106.5 MiB)**, 69 entries; `engine/` is 112,394,407 bytes before tar (K4 on
0.2.0 was 63,416,048 bytes, 47 entries). Prediction was about 107 MiB.
