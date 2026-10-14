# Scroll page bubble: the unit half (U1–U4 of `specs/SPEC-M3-scroll-page-bubble.md`)

The owner's request of 2026-10-14 (「拉著卷軸的游標旁邊會有一個泡泡顯示當前頁數」), ruled the same day to show on ANY scroll of the desk and to fade after scrolling stops, accepted as specified (「OK 照規格走」). The spec's criteria were pinned before this change; this directory holds the unit witnesses. The browser criteria (N1–N6, D1, K1, Z1, no host) and the host criteria (H1–H3) are run later, once the `dist/` mirror may change and a browser may run (the main session's GO-DIST; the host ones after it installs the version).

## The change (`wasm_sdk_probe/web/e2-editor-app.js`, `aa50cd20…` → `ccb67a52a3fe4b73…`)

One new section after the page-number one: constants `SCROLL_BUBBLE_HOLD_MS` 1000, `SCROLL_BUBBLE_FADE_MS` 180, `SCROLL_BUBBLE_THUMB_MIN_PX` 20, `SCROLL_BUBBLE_ARROW_PX` 17, `SCROLL_BUBBLE_RAIL_MIN_PX` 12, `SCROLL_BUBBLE_GAP_PX` 6; the pure functions `scrollBubbleText(statusText)` (the status line's page part, 「第 4–5 頁，共 60 頁」 → 「第 4–5 頁」, else null) and `scrollBubblePlace(desk, bubble)` (the spec §3.2 model: `f = scrollTop/(scrollHeight−clientHeight)`, thumb `t = max(clientHeight²/scrollHeight, 20)`, arrows `a = 17` when the bar occupies width, centre `top + a + t/2 + f·(clientHeight − 2a − t)` clamped inside the desk; side from `clientLeft`/direction; edge `max(rail, 12) + 6` px from the desk's edge; null when nothing scrolls); the record `scrollBubble`; `scrollBubbleElement()` (a `<div id="scroll-bubble" aria-hidden="true">` made on the first scroll, styled by CSSOM, `position: fixed`, inserted after `#desk`, `transition: none` when `prefers-reduced-motion: reduce` matches); `showScrollBubble()` (text from `#page-status`, place from the desk's rect, `data-shown="1"`, hold timer restarted) and `hideScrollBubble()` (`data-shown="0"`, opacity 0, `visibility: hidden` after the fade or at once under reduced motion). Wiring: `onDeskScroll` calls `showScrollBubble()` as its second line (its first stays `updatePageStatus()`, page-number.test's pin); `globalThis.addEventListener("resize", hideScrollBubble)` as its own statement. Nothing else on the page changed; `web/e2-editor.html`, `editor-shell*/`, `sdk/`, the engine and the host are untouched.

**An anchor almost moved.** The first shape put `hideScrollBubble();` inside the existing resize listener, and the product-path mutation `resize-does-not-repaint` (`tools/run_e2_c_product_path.py:1584`) anchors that listener's exact bytes: the anchor count went 1 → 0 (`u/mutation-anchors.json` was red at that point). The change was reshaped into a separate listener and the mutation file was not edited; the final count is 41 anchors, each exactly once (`u/mutation-anchors.json`). The counter is `u/anchors.py` (`python3 -I u/anchors.py <page> tools/run_e2_c_product_path.py tools/check_m3_production_ui.py`: AST-extract every `find` whose `path` is `e2-editor-app.js` from both `MUTATIONS` tables, count it in the page).

## U1–U3 — `editor-shell-v2/tests/page-scroll-bubble.test.mjs` (red first, then green) — `u/`

The functions and the wiring are compiled from the page source (`PAGE_SOURCE=` selects the copy) against a fake desk (K4's two measured desks: Firefox overlay bar, Chrome classic bar with arrows, both at scrollTop 4900 of the 60-page fixture), a fake document and node's mock timers.

| test | the page before (`aa50cd20…`, `scroll-bubble-old-page-aa50cd20.tap`) | the changed page (`scroll-bubble-new-page.tap`) |
|---|---|---|
| U1 text: page part only; null for null/""/「—」 | red (not found) | green |
| U2 place: K4 Firefox desk → centre 222 ± 1, right edge − 18; Chrome → 236 ± 1, − 21; clamped at both ends; overscroll = end; a short document's long thumb | red | green |
| U2 null when nothing scrolls; RTL side from `clientLeft` (classic) or direction (overlay) | red | green |
| U3 a scroll makes the element (sibling after `#desk`), `data-shown="1"`, text 「第 4–5 頁」, `top` 222, `translateY(-50%)`, `left` = edge − width; aria-hidden, no role/aria-live/tabindex, `pointer-events: none`; the status line untouched | red | green |
| U3 timer: second scroll at 600 ms → still shown at 1,100; hidden at 1,000 after the last; `visibility: hidden` 180 ms later; a scroll during the fade brings it back | red | green |
| U3 reduced motion: `transition: none`, hidden at once, the 1 s hold stays | red | green |
| U3 never shows without a page number or without overflow; positive control shows | red | green |
| U3 the resize hides it through its own listener; the canvas's listener carries no bubble call | red | green |
| **totals** | **0 / 8** | **8 / 8** |

**Mutations (spec §5 U2/U3), each on a copy of the changed page** — `mutation-*.tap`:

| copy | red on | the message |
|---|---|---|
| `SCROLL_BUBBLE_THUMB_MIN_PX` 20 → 0 | U2 (and U3's `top`) | `firefox centre 216.69…` (expected 222 ± 1) |
| the clamp removed | U2 | `top 170` (below `top + h/2` = 173 at f = 0) |
| the hold timer not reset on a scroll | U3 timer | `the timer is reset by the second scroll` |

## U4 — the suite and E1-C — `u/suite.tap`, `u/exit-codes.txt`, `u/e1c-intact.json`

`node --test editor-shell-v2/tests/*.test.mjs`: **372 / 372** (364 before + 8). One harness addition, no assertion changed: `page-render-bands.test.mjs` compiles `onDeskScroll` in a scope of its own and now stubs `function showScrollBubble() {}` beside its existing `function updatePageStatus() {}` stub (W-U3–W-U6 were ReferenceError-red without it). `check_e1_c_bundle_intact.py`: `intact: true`.

## Not done here

`make e2-c-assets` (the `dist/` mirror still serves `aa50cd20…` for the host-side H1 of 0.2.22 running meanwhile), every browser run, the v72 freeze, packaging, the host. Harness notes for the browser half: node's `mock.timers.tick(1180)` does not run a timer scheduled inside that tick at exactly its boundary (the test splits it into 1000 + 180); the node mock rejects `clearTimeout` as an API name (`setTimeout`'s mock covers it).
