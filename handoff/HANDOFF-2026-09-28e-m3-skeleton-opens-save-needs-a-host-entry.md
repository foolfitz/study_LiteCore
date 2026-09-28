# Handoff, 2026-09-28 (e) — M3 skeleton opens ODT from Files; save needs a host entry

Entry points: this file, `findings/evidence/m3-skeleton/RESULT.md`,
`handoff/m3-skeleton/CRITERIA.md`, the app repo `~/Projects/Nextcloud_Apps/litecore`.

The owner chose **B** of 09-28d (continue M3 on the E1h shape, starting with an app
skeleton).

## Done

- New app `litecore` (own git repo, `a245b2c`; DDEV scaffold, official Nextcloud 34.0.2
  tarball, `https://litecore.ddev.site:8443`, admin password in
  `.ddev/config.local.yaml`; `debug` false via `nextcloud/config/zz-litecore.config.php`,
  `firstrunwizard` disabled — same environment as gate 0).
  - `src/files.js` → `js/litecore-files.mjs` (esbuild; `npm run build`): the
    `@nextcloud/files` 4.1 default action for ODT, **navigates** to
    `/apps/litecore/r/e2-editor.html?fileId=<id>`.
  - `lib/Controller/EditorController.php`: E1h's route, copied in shape from the probe:
    the page is re-wrapped, COOP + COEP, JS by PHP with COEP, `.wasm` redirected to static,
    and `json`/`odt` by PHP. `fileId` is resolved against the user's own folder and turned
    into a WebDAV URL. The route never reads the document.
  - `js/litecore-editor.js`: imports the product module, waits for the product's own
    boot, fetches the file over WebDAV, and opens it through the product's `#file` input.
- Check `wasm_sdk_probe/tools/check_m3_skeleton_open.py` (criteria S1–S5 committed first,
  `5eae2a15`; `--red-cases` 10/10 red). Counted run: **`SKELETON WORKS
  chrome=3/3,firefox=3/3`** (`7cb3e943`). No product byte changed.
- Shakedown 1 was red on the instrument (JSON `\uXXXX` in a CSS selector for the CJK file
  name). Registered in the evidence README.

## The blocker, and why it is the owner's

The product page has **no host entry**. `openDocument(bytes, name)` and
`saveDocument()` are module-private in `web/e2-editor-app.js`. The skeleton opens through
the file input: it works, but the product first opens its bundled sample (about half of
the open time), and **save cannot reach the host** (the product's save is a download
link). Write-back, locking, versions and conflicts (roadmap §5.4) all need bytes out.

Adding an entry changes `web/e2-editor-app.js`. That file is the cutover's `pageSha256`
and one of the shell bundle's 13 included files (PLAN-2026-08-28 §"2026-09-05 rule":
any byte change moves `pageSha256` and voids runs on the other sha; a new shell
generation must be frozen). Soak is **0/12**, so no banked run would be voided today.

## What is next — the owner's call

- **A. Add a host entry to the product page now (recommended).** A small contract:
  the host hands `open(bytes, name)` and receives the bytes on save instead of a
  download, and the page skips its bundled sample when a host is present. Freeze it as
  the next candidate page and shell generation before any soak run banks. The Nextcloud
  app then does save = WebDAV PUT with `If-Match: <etag>` (conflict = 412), then locks
  and versions. Cost: page identity moves, and T4 re-binds to the new page. Soak loses
  nothing (0/12).
- **B. A Nextcloud-only entry module**, leaving the cutover page alone: a second page
  (`nc-editor-app.js`) that drives the SDK directly. The cutover is untouched, but the
  ~1700-line page UI gets forked, or the page must be refactored into exports, which
  changes its bytes anyway.
- **C. Prototype save without touching the product:** the host script captures the
  product's download (patch `URL.createObjectURL`/anchor click) and PUTs it. Nothing
  moves, and it would let us learn Nextcloud's lock/version/conflict behaviour now. But
  it is machinery built around a missing interface, and it breaks the moment the
  product's save changes.

Inclination: **A**, now, because it is the cheapest moment (soak 0/12), and every §5.4
item needs it. C is acceptable only as a throwaway to measure WebDAV semantics, never
as the shipped path.

## State

study_LiteCore: tree clean at `7cb3e943` plus this file; not pushed. The litecore app
repo is clean at `a245b2c`. Both DDEV projects (`litecoreprobe`, `litecore`) are running;
nothing depends on keeping them up.
