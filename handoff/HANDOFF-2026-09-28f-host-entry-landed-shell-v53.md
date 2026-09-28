# Handoff, 2026-09-28 (f) — Host entry landed; shell v53; next is locks

Entry points: this file, `specs/SPEC-M3-host-entry.md`,
`findings/evidence/m3-host-entry/RESULT.md` and `README.md`, the app repo
`~/Projects/Nextcloud_Apps/litecore`.

The owner chose **A** of 09-28e (add a host entry to the product page, now).

## Done

- `web/e2-editor-app.js` `1ec7baf9…` → `fbfb59a4…` (staged into `dist/`). It reads
  `globalThis.liteCoreHost = { load, save }` once at module evaluation. With a host it
  opens what `load()` gives, never touches the bundled sample, disables the two local
  file pickers, and hands save bytes to `save()` instead of triggering a download; saves
  are serialized one at a time end to end (`saveDocument` → `saveOnce`, through
  `hostSaves`). A wrong-shaped host is refused (`HOST_ENTRY_INVALID`). No host present →
  page unchanged.
- Shell generation **v53** frozen (`wasm_sdk_probe/e2/editor-shell-v2-bundle-v53.json`,
  `bundleSha256` `2e3a2021…`), differing from v52 only in `web/e2-editor-app.js`;
  `tools/build_e2_c_shell_bundle.py` `MANIFEST` now points at v53 with a dated comment.
  Still pins `e2-editor-v8`; no engine change, no link.
- Nextcloud app `~/Projects/Nextcloud_Apps/litecore` (own git repo): `a245b2c` skeleton,
  `6f8a780` first host script, `0dcb745` host after review. `https://litecore.ddev.site:8443`,
  admin password in `.ddev/config.local.yaml`. Host is `js/litecore-editor.js`:
  - `load` = WebDAV GET keeping `OC-ETag` (fallback `ETag`; refuses to open without one).
  - `save` = PUT with `If-Match` always (never unconditional).
  - 412 → conflict copy named `〈name〉（衝突副本 〈stamp〉）.odt` via
    `If-None-Match: *`, and a `CONFLICT` error surfaced to the page.
  - `X-Requested-With` on every request; each save marked settled.
- Measurement: `wasm_sdk_probe/tools/check_m3_host_entry.py` (runner sha `e39e336f…`).
  Counted run `findings/evidence/m3-host-entry/runs/2026-09-28T095100Z.json`:
  **`HOST_ENTRY LANDS`** — H1 (open skips the sample) 6/6 per browser; H2 (two saves,
  button then insert-marker + Ctrl+S, version chaining) 3/3 per browser; H3 (conflict
  twice, both 412, view not reloaded after 5 s, two conflict copies) 3/3 per browser; H5
  (broken hosts `{}` and load-without-save) Chrome 1/1 each (Firefox driver cannot inject
  a pre-document script). H4: `run_e2_c_product_path.py` on v8 and v14, each 40 PASS / 2
  NE, cell for cell equal to the v52 baseline (`findings/evidence/098/product-path/v52-*.json`);
  `make test-e2-c-static` exit 0. 21 red cases red. Click-to-opened: Chrome 2.51–2.54 s,
  Firefox 3.01–3.08 s (skeleton was 3.7–4.0 / 5.1).

## Wrong turns, recorded

H2's criterion first required `<text:h>`, but the product writes
`<text:p text:style-name="Heading_20_1">` — known in this tree since 2026-08-19
(`run_e2_c_product_path.py` `document_lines`) and not checked when drafting. An opus
adversarial review, before the counted run, broke the criteria and the host (not the
page's no-host path); adopted fixes are listed in the spec's revision log. Criteria and
runner were committed together with the result, not before it — order is evidenced only
by mtimes and the shakedown reports' runner sha.

Corrections appended today to `findings/evidence/m3-gate-0/RESULT.md` and
`m3-skeleton/RESULT.md`: the seven `PRODUCT_FILES` hashes never bound the shell bundle's
other 11 modules (they were v52's bytes then); after the dist page changed, gate 0's
reader predicate (d) goes red by design (the page that ran is
`git show a9759513:wasm_sdk_probe/web/e2-editor-app.js`).

## Named limits

From `RESULT.md`: `session.save()` marks clean before the host accepts; 403/423/network
failure strand the edits in the page (no way out); conflict copy is made per refused
press; not exercised: shares/public links/other users, file moved mid-edit, render
failure after a successful PUT; Apache only; admin user.

## State

study_LiteCore: tree clean at `1c0975a6`, not pushed. Roadmap
`research/ROADMAP-2026-08-20-milestones.md` §5.4 records the landing; remaining M3
items: locks (423/403 currently strand edits), versions (Nextcloud keeps them, not
measured), and the shell semantic that "clean" is set before the host accepts.

The v14 cutover gate: soak 0/12, reordered to the end of development, full run on the
final identity; T4 to be re-earned on the final identity. The page identity has moved
again (`fbfb59a4…`, shell v53) — nothing banked was voided because nothing was banked.
No cutover performed. Nothing pushed.

Both ddev projects (`litecoreprobe`, `litecore`) are running; nothing depends on them
staying up.

## What is next — the owner's call

- **A. Locks and permissions next.** Take a WebDAV/Nextcloud lock on open (or use the
  `files_lock` app, or Nextcloud's own lock API — either is currently unmeasured which
  one fits best), release on close, and give 403/423/network failures a way out (e.g.
  the same conflict-copy path, or a download) so edits are never stranded; measure with
  the same runner pattern used for the host entry. Inclination A because it closes the
  only named data-loss path.
- **B. Versions next.** Measure that each save produces a Nextcloud version and that
  restoring one works. Cheap, but it measures Nextcloud more than our code.
- **C. Cutover path next.** Freeze the final identity (v14 + shell v53 + the page
  `fbfb59a4…` repointed to v14 — H4 measured that repoint as `64f70410…`) and run T4
  plus the 12-run soak over ≥3 UTC days; the host entry would then ship.

Inclination: **A**, because it closes the only named data-loss path (403/423/network
failures currently strand edits with no way out), and it is cheap right now — soak is
still 0/12, so no banked run is at risk from another identity move.

Session context was past the soft limit; this file is the entry point for a fresh session.
