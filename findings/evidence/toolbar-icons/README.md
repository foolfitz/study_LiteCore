# Icon toolbar (owner 2026-11-01)

Owner: the toolbar's buttons as web-style icons (Material or Bootstrap), the text shown only on hover, Collabora as the reference.

**What changed.** `wasm_sdk_probe/web/e2-editor.html` only, `b9c2b975...` -> `ca58f40f...`, produced by `build_toolbar_html.py` (a checked transform of the page, icon package pinned by sha256). `web/e2-editor-app.js` is not touched, and the HTML is not in the shell bundle, so generation 83's digest `607b280d...` stands (bundle line exit 0, E1-C intact, `hashes-*.txt`).

**Choices.**
- Material Symbols outlined, `@material-symbols/svg-400` 0.48.2, Apache-2.0: Nextcloud's own icons are the same family, so the page does not look foreign in the host. Inline sprite: no new file for the package tables, no new request.
- Collabora's pattern (`cool-26-04/browser/src/control/Control.JSDialogBuilder.js` `data-cooltip`, `browser/css/tooltip.css`): icon-only buttons, the name in a tooltip on hover and on keyboard focus, shortcuts in the tooltip. Only shortcuts the page really handles are named (`e2-editor-app.js:3147-3186`).
- **The button text stays in the button**, in a visually hidden span. `run()` puts it in the status strip, `check_m3_page_honesty.py` and `run_e2_c_product_path.py` read `textContent`, and it is the accessible name. So nothing that reads the page moves.
- `.toolbar button[hidden]` is restated: `display: inline-flex` would otherwise have shown redo and Markdown before they are declared.

**check-02** (`check_toolbar.py`, real pointer, a mirror of `dist/`): both browsers HOLD. Text, order and action equal the page before; Chrome's accessible names equal the text; every icon drawn at 20 x 20; labels clipped; tooltip hidden at rest, shown on hover, gone after; a real click on the icon flips the format and writes the strip; every tooltip inside the viewport. `check-01` is kept: Firefox `clickIcon` red because the clause assumed a start of false, and Firefox's metrics put the caret on a bold line (the clicks were right, `['false', 'true']` from `true`). Fixed by execution.

Not looked at inside Nextcloud yet: that needs host 0.2.45.
