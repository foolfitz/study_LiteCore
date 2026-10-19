# Finding 155: reduced reproduction of the host rule (2026-10-20)

`precheck_margin_rule.py --out findings/evidence/155/precheck` builds three pages from the real sources and reads the open dialog (`showModal()`) in headless Chrome (1850×980) and Firefox (1850×994). This is a diagnostic: it is not a host measurement and satisfies no criterion. The criterion is H-155 on the host (SPEC-M3-link-batch-v22 §14.3).

The three pages:
- `mirror`: the page's own `<style>` and dialog markup from `wasm_sdk_probe/web/e2-editor.html`, with no Nextcloud CSS. This is the positive control.
- `as-0227`: the same, plus the two Nextcloud reset rules that name `dialog`, copied verbatim from the installed `nextcloud/core/css/server.css`. The page style is wrapped in `@scope (#litecore-editor-root)` as `templates/editor.php` wraps it, and 0.2.26's host rule is added.
- `with-rule`: `as-0227` plus 0.2.28's `#litecore-editor-root dialog[open] { margin: auto; }`.

Readings (`precheck.json`; the source hashes are recorded there):

| browser | variant | box | centre offset | computed margin |
|---|---|---|---|---|
| Chrome | mirror | [605, 329, 640, 322] | [0, 0] | `329px 605px` |
| Chrome | as-0227 | [0, 0, 640, 318] | [-605, -331] | `0px` |
| Chrome | with-rule | [605, 331, 640, 318] | [0, 0] | `331px 605px` |
| Firefox | mirror | [605, 339, 640, 317] | [0, 0] | `auto` |
| Firefox | as-0227 | [0, 0, 640, 317] | [-605, -338] | `0px` |
| Firefox | with-rule | [605, 339, 640, 317] | [0, 0] | `auto` |

How to read them:
- `as-0227` reproduces the host's top-left box from H-154o (`[0, 0, 640, 335]` in Chrome, `[0, 0, 640, 342]` in Firefox). The heights differ because the host's fonts are inherited; the position is the same.
- The computed `margin` string differs between browsers, so it is recorded and not used as a clause.
- `client` (the `documentElement` client size) equals `innerWidth`/`innerHeight` here, because no scrollbar is shown.

The first run died before opening a browser: a `%` in Nextcloud's `font-size:100%` broke a `%`-format string. The fix replaced it with a placeholder.
