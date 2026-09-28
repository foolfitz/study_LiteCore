# M3 skeleton — evidence

Question: does the first M3 step work in gate 0's shape (E1h) — a Files action opens a
user's ODT in the shipped editor, bytes over WebDAV, no product byte changed. Criteria:
`handoff/m3-skeleton/CRITERIA.md` (written before the first run). The verdict is the
one line of `wasm_sdk_probe/tools/check_m3_skeleton_open.py --score REPORT`.

| path | what |
| --- | --- |
| `shakedown/` | Instrument runs, never counted. `074537Z` = shakedown 1: the runner's CSS selector carried JSON `\uXXXX` escapes for the CJK file name, which CSS does not read, so the Files row was never found (instrument, not product; fixed with `ensure_ascii=False`, and a timed-out wait now records the row names it did see). `074822Z` = shakedown 2: 1/1 in both browsers; the base of `--red-cases` (10 mutations, all red). |
| `RESULT.md` | **The result**: `SKELETON WORKS chrome=3/3,firefox=3/3` on `runs/074930Z`, what it shows, and why save needs an embedder entry. |
| `runs/` | Counted runs (`--label counted`, repeats 3, refuses a dirty app tree). `2026-09-28T074930Z.json` is the first. |

App: `~/Projects/Nextcloud_Apps/litecore` (own git repo; each report records its commit
and the sha256 of every tracked file). Instance: DDEV scaffold, official Nextcloud
34.0.2 tarball, Apache, `debug` false, `firstrunwizard` disabled. Product bytes:
`wasm_sdk_probe/dist`, bind-mounted read-only; the seven gate-0 product files are
hashed into each report.
