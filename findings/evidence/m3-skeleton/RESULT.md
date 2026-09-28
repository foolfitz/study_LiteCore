# M3 skeleton — result (counted run, 2026-09-28)

```
$ python3 wasm_sdk_probe/tools/check_m3_skeleton_open.py --score findings/evidence/m3-skeleton/runs/2026-09-28T074930Z.json
SKELETON WORKS chrome=3/3,firefox=3/3 problems=[]
```

**A user's ODT opens from Nextcloud Files in the shipped editor, in gate 0's shape E1h,
3/3 in Chrome 151 and 3/3 in Firefox 156, with no product byte changed.** Every run:
clicked in Files → landed on `/apps/litecore/r/e2-editor.html?fileId=76` → page
cross-origin isolated (Chrome: COOP `same-origin` + COEP `require-corp` on the wire) →
WebDAV GET 200 whose bytes hash to the uploaded file → the product's state `ready` with
the uploaded name → place caret and `set-paragraph-heading` on that document, revision
0 → 1. Criteria S1–S5: `handoff/m3-skeleton/CRITERIA.md`, committed before any run
(`5eae2a15`); the scoring went red on all 10 mutations of shakedown 2 first.

## Identity

| what | value |
| --- | --- |
| report | `runs/2026-09-28T074930Z.json`, sha256 `a2e737e4be6a1595009ed9a900b8dd66ac375161bda2bae03bb03ac539308763`; 07:49:30Z → 07:51:01Z, label `counted`, repeats 3 |
| runner | `check_m3_skeleton_open.py` sha256 `ebd96780b16b…` (= the file in `5eae2a15`) |
| app | `litecore` `a245b2c`, tree clean (`~/Projects/Nextcloud_Apps/litecore`) |
| instance | Nextcloud 34.0.2 (official tarball), Apache, `debug` false, `firstrunwizard` disabled |
| product | the seven gate-0 files, unchanged: `e2-editor.html` `f7e47799…`, `e2-editor-app.js` `1ec7baf9…`, v8 `probe.wasm` `4a2710bb…` (full hashes in the report) |
| document | `e1-fixtures/multi-paragraph.odt` uploaded as `M3 骨架 測試.odt` (1343 bytes, sha256 `3b6db004…`; the bundled sample `list-contexts.odt` differs) |

## Measured

| | Chrome 151 | Firefox 156 |
| --- | --- | --- |
| click → document opened | 3.7–4.0 s | 5.1 s |
| host script start → the product's bundled sample ready | 2.05 s | 2.42–2.47 s |
| WebDAV requests for the document | exactly 1 GET per run, initiated by the page script | not observable (no CDP) |
| place caret / heading | 28–34 ms / 52–89 ms | 31–36 ms / 34–47 ms |

## What this shows and what it does not

- The route resolves `fileId` against the logged-in user's own folder and hands the
  browser a WebDAV URL. It does not read, parse or convert the document. The bytes
  come through Nextcloud's WebDAV (PHP serving a file), and the editor works on them in
  the browser. No document process runs on the server.
- The file name has a space and CJK characters. The WebDAV path encoding worked in both
  browsers.
- **The bridge is the product's own "open a file" input.** The host script puts the
  fetched bytes into `#file` and dispatches `change`, the same path a user's file pick
  takes. It works, but it has two costs, and both come from the page having **no
  embedder entry**:
  1. The product first boots and opens its bundled sample. That takes about half the
     time to open the user's file: 48–55 % of click → opened, 52–62 % on the host
     script's own clock (Firefox at the low end). The engine boot inside that time would
     be paid anyway; opening the sample would not. The host has to wait for it, or two
     sessions would race.
  2. **Saving back is not possible this way.** The product's save hands the bytes to a
     download link (`e2-editor-app.js` `saveDocument()`), and nothing reaches the host.
     Save, locking, versions and conflicts — the rest of roadmap §5.4 — need an entry
     through which the page takes bytes in and gives bytes out. Adding one changes the
     page's identity. That is the owner's decision (see the handoff).

## Named limits

Admin user, own file only (no received shares, no public links: the `r/*` routes are
`NoAdminRequired`, so a public page would need `PublicPage` and a share-token path).
Chrome's click is a synthetic `.click()`; Firefox's is a WebDriver click. Apache only.
One document, one small file (1.3 KB). The product profile is the shipped v8; v14's
`.data`/`.metadata` would need a PHP route (gate 0 C7) that this app does not have yet.

## Correction — 2026-09-28, later the same day (appended)

Same identity gap as gate 0's correction: the seven product hashes do not cover the
shell bundle's eleven other modules, which were shell v52's bytes (inference from
`dist/` hashes and mtimes). And `dist/e2-editor-app.js` changed after this run: it
carries the M3 host entry, which replaces this skeleton's `#file` bridge. The page that
ran here is `1ec7baf9…` (`git show a9759513:wasm_sdk_probe/web/e2-editor-app.js`).
