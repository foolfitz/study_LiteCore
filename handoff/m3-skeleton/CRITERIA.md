# M3 skeleton — "open an ODT from Files": criteria

Written 2026-09-28, before any run of `wasm_sdk_probe/tools/check_m3_skeleton_open.py`.
Not a gate: this checks that the first M3 step works in the shape gate 0 chose (E1h),
and finds what the next step needs. Append-only once the first counted run exists.

## What is under test

App `litecore` (`~/Projects/Nextcloud_Apps/litecore`, own git repo, same DDEV scaffold
and official Nextcloud 34.0.2 tarball as gate 0, `debug` false, `firstrunwizard`
disabled, product bytes bind-mounted read-only from `wasm_sdk_probe/dist`):

- A Files action (`@nextcloud/files` 4.1 `registerFileAction`, default action for
  `application/vnd.oasis.opendocument.text`) that **navigates** to
  `/apps/litecore/r/e2-editor.html?fileId=<id>`.
- That route: the shipped page re-wrapped under Nextcloud's header, COOP + COEP
  `require-corp`, engine scripts by PHP with COEP, `.wasm` static — E1h's shape. The
  route resolves the file id to the user's WebDAV URL; it does not read, parse or convert
  the document (the bytes reach the browser through Nextcloud's own WebDAV, which is PHP
  serving a file, not a document process).
- `js/litecore-editor.js`: imports the product module, waits for the product's own boot
  (it opens its bundled sample `list-contexts.odt` first), fetches the file over
  WebDAV, and hands the bytes to the product through the product's own file input.
  **No product byte changes.**

## Per run (fresh browser, logged in as admin)

The runner uploads `e1-fixtures/multi-paragraph.odt` as `M3 骨架 測試.odt` (space and
CJK exercise the WebDAV path encoding), opens Files, and clicks the file's name.

- **S1 click path:** the browser ends on `/apps/litecore/r/e2-editor.html?fileId=<the
  uploaded file's id>`, reached from the Files page by the click (not a typed URL).
- **S2 isolated:** the editor page reads `crossOriginIsolated` and `SharedArrayBuffer`
  true; in Chrome the document response on the wire carries COOP `same-origin` and COEP
  `require-corp`.
- **S3 the user's bytes:** WebDAV GET status 200, and the sha256 of the fetched bytes
  equals the sha256 of the uploaded file (which differs from the bundled sample's).
- **S4 opened:** the product's state is `ready` and its document label equals the
  uploaded name (not `list-contexts.odt`).
- **S5 live on that document:** the page-smoke step of gate 0 on the opened document —
  place caret, `set-paragraph-heading`, revision +1.

A run passes iff S1–S5 all hold. **The skeleton works iff 3/3 runs pass in Chrome and
3/3 in Firefox.** Scoring reads raw fields only, and is made red first: the runner's
`--red-cases` mutates a report once per criterion and each copy must fail.

**If this is never run:** the skeleton is untested, and the next step (save back) is
designed on an unmeasured open path.

## Recorded, not judged

Seconds from click to `opened`; the time spent booting the bundled sample first; in
Chrome, the requests for the document (expected: exactly one WebDAV GET from the page).

## Named limits (declared now)

Admin user, own file only (no shares received, no public links). Chrome's click is a
synthetic `.click()`; Firefox's is a WebDriver click. Apache only. The bridge through
the product's file input is the skeleton's, not the design: the design needs an embedder
entry for open and save (an owner decision; it changes the page's identity).
