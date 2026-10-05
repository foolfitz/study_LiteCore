# Finding 110 — evidence

Reported by the owner on 2026-10-05: Nextcloud's header looks covered on the editor page, and there is no close button like richdocuments' top-right 「X」. Measured the same evening on the dev instance (host 0.2.5), Chrome 151 over CDP, 1850 × 980.

| page | `body` background colour | `body` background image | header |
| --- | --- | --- | --- |
| Files (`/apps/files/files?dir=/`, `files-page.png`) | `rgb(0, 103, 158)` (the theme's primary) | `…/apps/theming/img/background/jo-myoung-hee-fluid.webp` | transparent |
| the editor (`editor-page.json`, `editor-page.png`) | `rgb(244, 246, 248)` | none | transparent, 50 px |

Nextcloud draws its header over the body's themed background with white icons; on the editor page the body background is the product page's own `--bg` (`#f4f6f8`), so the icons are near-invisible (top-left of `editor-page.png`). Cause: the host prints the product page's `<style>` verbatim into Nextcloud's page (`~/Projects/Nextcloud_Apps/litecore/templates/editor.php`, from `EditorController::editor`), and that style sets `body { margin: 0; background: var(--bg); display: flex; height: 100vh }` and restyles every `button`, `select` and `input[type=text]` on the page — Nextcloud's own included. The host adds no close control.
