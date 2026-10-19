# v22 browser criteria: C1 and H1 (2026-10-19)

Spec: `specs/SPEC-M3-link-batch-v22.md` §5.3. Tool: `../../link-batch-v21/shakedown/diag-long-paragraph/tool/diag_long_paragraph.py` with the page family `v22` (`7973c427`), sha256 `e3d7fcd9130f…` in every report below. Each cell runs in one fresh headless browser. The tool takes the S-9 lock and records its pre-run checks: KWallet unlocked, foreign CPU within the limit. The owner's own Chrome was open, about 38 processes; on 10-19 `opentype1` ran with about 30, and its results matched. The commands are in the `*.cmd` files and the console output in the `*.log` files. The run took 10:52–11:06 +0800.

## Identity

- `report-identity-chrome.json`: a witness cell `sdk-text:cjk:1024:v22` (not a C1 cell; it came out `ok`).
  - The `v22` identity: `identityOk: true`, and all six checks are true: the shell digest, the four profile files against the archived v22 bytes, and `v22:loaderServed`.
  - `loaderServed` is the loader **fetched from the mirror's server**: `dc4c2c84…`. That is S1's served clause.
  - The page pin moves from `db3408f5…` to `f7a40bcc…`. The shell is v74 (`e35923a0…`). The worker served is `0d55bcfa…`.
- `identity-red-case.txt`: the same identity, built without a browser while expecting v21's loader hash. `identityOk` turns false, on `v22:probe.js` only.
- Every C1 and H1 report below has `identityOk: true`. Its `profileHashes` equal `dist/profiles/e2-editor-v22/` (read again at judging), and its fetched loader is `dc4c2c84…`.

## C1 (finding 153 criterion 1): PASS

Read by the main session with `python3 -I`, by the rule pinned in the spec. A cell passes when `outcome == "ok"`, which is the tool's `classify`:
- the attempt answered ok;
- on Chrome, no `memory access out of bounds` and no exception from a `probe.js` thread;
- the page is not in `recoverable-error`;
- the alive ask afterwards answered `ok`.

| browser | report | cells | per input | outcome |
|---|---|---|---|---|
| Chrome 151.0.7922.169 | `report-c1-chrome.json` | 12 | `sdk-md:cjk:65536`, `sdk-md:cjk:43520`, `sdk-md:ascii:65536`, `opentype:long14:0`: 3 each | **12/12 ok** |
| Firefox 157.0.1 | `report-c1-firefox.json` | 12 | the same, 3 each | **12/12 ok** |

Under the label, in every one of the 24 cells:
- **The edit answered ok:**
  - `pasteMarkdown` answered `ok` with `revision: 1` in 30–112 ms;
  - for `opentype`, the open took 1.9–3.1 s and the typed `x` answered `ok` in 0.103–0.110 s.
- **No exception** was recorded (Chrome), and the page ended `ready`.
- **The alive ask** answered `ok` at `rev` 1.
- **The text is in the document.** The saved ODT of every cell (`docs-c1-chrome/`, `docs-c1-firefox/`) holds the input as one paragraph of exactly the input's UTF-8 length: 65,536, 43,520 and 65,536 bytes. The `opentype` cells hold `x` plus the 65,536-byte fixture paragraph (65,537 bytes).

The fixture `long14` is `../../link-batch-v21/shakedown/diag-long-paragraph/out/docs-chrome-s8-bigstack/001-sdk-md_cjk_65536_v21big.odt`, sha256 `150d28f5…`.

### The positive control: the instrument discriminates

| browser | report | cell | outcome | what it saw |
|---|---|---|---|---|
| Chrome | `report-c1-pc-chrome.json` | `sdk-md:cjk:65536:v21` | **crash** | `memory access out of bounds` and an exception on a `probe.js` thread; page `recoverable-error`; alive ask unanswered |
| Firefox | `report-c1-pc-firefox.json` | the same | **crash** | page `recoverable-error`; alive ask unanswered |

Same day, same tool, same input, on the shipped v21 (`identityOk: true`, page `605cf24b…`). Finding 153 reproduces on v21 in both browsers, and does not on v22.

## H1 (recorded, Chrome, N=1): six of six ok

`report-h1-chrome.json`, with the 10-19 measurement on v21's wasm with `v21stack1048576` (v22's exact loader) for comparison:

| cell | v22 | 10-19, v21 wasm + the same loader |
|---|---|---|
| `sdk-text:cjk:131072` (~28 pp) | ok, 120 ms | ok, 103 ms |
| `sdk-text:cjk:262144` (~56 pp) | ok, 283 ms | ok, 277 ms |
| `sdk-text:cjk:524288` (~112 pp) | ok, 845 ms | ok, 1,234 ms |
| `opentype:long28:0` | ok, open 1.93 s, type 0.103 s | ok, 1.83 s / 0.103 s |
| `opentype:long56:0` | ok, open 2.22 s, type 0.307 s | ok, 2.32 s / 0.306 s |
| `opentype:long112:0` | ok, open 2.62 s, type 0.814 s | ok, 2.72 s / 0.812 s |

N=1 each; the timings are records, not comparisons with a claim.

The pthread count on v22 was not taken: no instrument exists that leaves every bound byte alone (spec §3.2). The spec cites v12's counts, 3 per ODT open and 7 per ODS open.
