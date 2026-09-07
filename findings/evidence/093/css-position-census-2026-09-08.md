# CSS position census — every `position: absolute`/`fixed` rule missing an offset, 2026-09-08

Static, read-only census requested after finding 093 (`#a11y-doc` sits at the
bottom of the paper because `.a11y-only` has `position: absolute` with no
`top`/`left`, while `#sink` — the element finding 069 actually fixed — got
`top: 0; left: 0`). The sentence this census tests: **069 fixed an element,
not a class.**

No browser was used for this document. No file outside this one was written.

## 1. Enumeration

Command:

```
find wasm_sdk_probe/web -type f \( -iname "*.html" -o -iname "*.css" \) | sort
```

**Matched 62 files** (confirmed non-empty; the command is re-runnable as
written). All 62 are tracked by git (`git ls-files --others --exclude-standard
web` returns nothing — no untracked source hiding outside version control).

`wasm_sdk_probe/dist/` was **not** enumerated. It is a build product, entirely
git-ignored (`wasm_sdk_probe/.gitignore: /dist/*`, and the repo-root
`.gitignore` comment: "dist/（6.1 GB 建置產物）與 build/（1.3 GB 中繼物）不進
版控；只收原始碼"). Spot-diffing confirms `dist/*.html` files that exist are
byte-identical copies of the matching `web/*.html` (checked `e2-editor.html`,
`index.html`, `r2.html` — zero diff). `dist/` additionally contains several
Chrome **user-data-dir profile trees** (`dist/r8-c-profiles/…/Default/Extensions/…`,
`dist/r8-d-profiles/…`) holding Chrome's own bundled-extension pages
(`offscreendocument.html`, `craw_window.html`, `craw_window.css`) — these are
not this project's source, not served by `web/serve.py` (which serves `dist/`
as a flat static root and never resolves into those profile subtrees), and are
excluded on that basis, not by omission. `dist/releases/` and
`dist/r8c/releases/` hold copies of `r6.css`/`r7-reference.html`/`r7.css`
already covered via their `web/` originals. No other allowlisted
`wasm_sdk_probe/` subdirectory (`e1/`, `e2/`, `editor-shell/`,
`editor-shell-v2/`, `r7/`, `r8/`, `reader-shell/`, `sdk/`, `src/`, `tests/`,
`tools/`, `assets/`, `collaboration/`, `delivery/`, `input/`, `provider-sdk/`,
`providers/`, `test-docs/`) contains any `.html`/`.css` file (checked with
`find <dir> -type f \( -iname "*.html" -o -iname "*.css" \)` per directory,
all zero). **`web/` is the entire population.**

## 2. Finding the candidates

```
grep -n "position\s*:\s*\(absolute\|fixed\)" <each of the 62 files>
```

18 of the 62 files contain at least one such declaration, **35 rules/uses
total** (this count includes both `<style>` block rules and any inline
`style=` attributes — none of the 35 turned out to be inline; all 35 are in
`<style>` blocks or external `.css` files). Of the 35, **7 already carry a
full offset** (`inset: 0`, or explicit `top`+`left`) and are not candidates:
`#overlay`, `#comments`, `#sink-mirror` (`demo-editor.html`), `#sink`
(`e2-editor.html` — the 069 fix itself), `#trace` (`e2-c-d5.html`), and
`.tile-layer` in both `r6.css` and `r7.css`. **28 candidates remain** — rules
that set `position: absolute`/`fixed` without both `top` and `left` (or an
equivalent `inset`).

## 3. The 28 candidates

| # | File:line | Selector | Element(s) | Containing block | In a scroll container? | Static position | Positioned by JS? | Classification | Guard |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `e2-editor.html:65-70` | `.a11y-only` | `#a11y-doc` (`:236`), the only user of the class | `.paper` (`:79`, `position: relative`) | Yes — `.desk` (`:77`, `overflow: auto`) | Directly after `#canvas` (`:228`), full document height | No (`e2-editor-app.js` touches `el.a11yDoc` only via `.dataset.offers`, verified independently) | **Same shape as 093 — this IS the 093 defect** | See §4 — measured, not guarded |
| 2 | `e2-editor.html:145-146` | `#toast` | `#toast` (`:264`) | viewport (`position: fixed`, sibling of `.desk`) | N/A (fixed) | N/A — `left: 50%; bottom: 26px` fully anchors both axes | No, doesn't need to | Not the 093 shape (anchored via `left`+`bottom`, never static) | Content-only checks (see §4), geometry never read — irrelevant here |
| 3 | `demo-editor.html:129-130` | `#overlay .sel` | selection-rectangle `div`s, created in `paintOverlay()` | `#overlay` (`:124`, `inset: 0`, itself positioned) | Yes — `.desk` (`:102-106`, `overflow: auto`) | Top-left of (empty) `#overlay` | Yes — `demo-editor-app.js:424-425`, set **before** `el.overlay.replaceChildren(...)` (`:436`) inserts the node | Positioned by JS | None (see note below) |
| 4 | `demo-editor.html:133-134` | `#overlay .caret` | caret `div`, `paintOverlay()` | `#overlay` | Yes | Top-left of `#overlay` | Yes — `:432-433`, set before `:436` insertion | Positioned by JS | None |
| 5 | `demo-editor.html:149-150` | `#comments .comment` | comment cards, `renderComments()` | `#comments` (`:148`, `inset: 0`) | Yes | Top-left of `#comments` | Yes — `:365` (left), `:404` (top), both before `el.comments.replaceChildren(...)` (`:398`) | Positioned by JS | None |
| 6 | `demo-editor.html:159-160` | `#comments .tie` | connector line, `renderComments()` | `#comments` | Yes | Top-left of `#comments` | Yes — `:379-380`, before `:398` | Positioned by JS | None |
| 7 | `demo-editor.html:167-168` | `#comments .margin-cover` | column cover, `renderComments()` | `#comments` | Yes | Vertical fully set (`top:0;bottom:0`); horizontal (`left`) missing in CSS | Yes — `:394` sets `left`, `:395` sets `right`, before `:398` | Positioned by JS (only the horizontal axis needed it) | None |
| 8 | `demo-editor.html:171-172` | `#comments .pin` | anchor dot, `renderComments()` | `#comments` | Yes | Top-left of `#comments` | Yes — `:374-375`, before `:398` | Positioned by JS | None |
| 9 | `demo-editor.html:179-180` | `#sink` | `<textarea id="sink">` (`:292-293`) | `.paper` (`position: relative`) | Yes — `.desk` | Right after `#canvas` in flow (the two other absolutely-positioned siblings before it — `#overlay`, `#comments` — don't count toward the hypothetical flow box) — **same static position as the pre-069 `#sink`** | Partially: `moveSink()` (`:703-706`) always runs before the one `.focus()` call (`:819`, `{preventScroll:true}`) on the click path. **But `#sink` has no `tabindex`, so it is a normal stop in the browser's native Tab order**, and nothing in this file's JS or CSS runs `moveSink()` before a Tab-driven focus. Whether a Tab-only path (no prior click) can reach `#sink` while it is still at its unset/static position is **not determinable without a browser** | **Positioned by JS on the click path; the Tab-order path is undetermined (flag, not a finding)** | None |
| 10 | `demo-editor.html:219-220` | `#toast` | `#toast` (`:309`) | viewport (fixed) | N/A | `left: 50%; bottom: 56px` — fully anchored | No | Not the 093 shape | None |
| 11 | `demo-structure.html:68` / `demo-structure-discovery.html:68` | `#caret` | `<div id="caret">` (`:147` / `:144`) | `.paper` (`:66`, `position: relative`) | Yes — `.desk` (`:64`, `overflow: auto`) | Right after `#canvas` (`:146`/`:143`) in flow; masked by `display: none` default | Yes — both apps set `.style.left`/`.style.top` (`demo-structure-app.js:133-134`, `demo-structure-discovery-app.js:144-145`) **before** the following line flips `display` to `"block"` | Positioned by JS | None |
| 12 | `demo-structure.html:77-78` / `demo-structure-discovery.html:77-78` | `#toast` | `#toast` (`:167`/`:164`) | viewport (fixed) | N/A | `left: 50%; bottom: 26px` — fully anchored | No | Not the 093 shape | None |
| 13–24 | `e2-c-046-empty.html:13`, `e2-c-046-overshoot.html:13`, `e2-c-048-boundary.html:13`, `e2-c-block-identity.html:13`, `e2-c-caret-ack.html:13`, `e2-c-commit-drop.html:4`, `e2-c-d2.html:13`, `e2-c-d3-corpus.html:13`, `e2-c-d3.html:13`, `e2-c-d4-heap.html:13`, `e2-c-d4.html:13`, `e2-c-ime-replace.html:6` | `#sink` | one `<textarea id="sink">` per file, identical minimal harness pages | initial containing block (no positioned ancestor anywhere in these files) | **No** — these pages have no `.desk`/`overflow:auto` wrapper at all; the page scrolls natively | Right after a `<p>`/`<h1>` (small, not full-height) and **before** `#log` (the only element that grows), so static position sits near the top of the page, never after tall content | No (`grep sink\.style\.(top\|left)` on each `*-app.js` = 0 hits) | **Not in a scroll container** (doubly so: no scroll wrapper, and DOM order puts the tall element *after* `#sink`, not before it) | None (checked `run_block_identity_link.py`, `run_e2_c_d4.py` — no geometry reads) |
| 25 | `r6.css:62` | `.document-tile` | tile `<canvas>` elements, `drawTile()` in `r6-reader-app.js` and `r6-reference-app.js` | `#tiles`/`.tile-layer` (`inset: 0`) → `.document-surface` (`position: relative`) | Yes — `.viewport` (`overflow: auto`, both files' CSS) | Top-left of `#tiles` (first/only tile at that key) | Yes — `r6-reader-app.js:162-163`, `r6-reference-app.js:214-215`. The canvas is `.append()`-ed one statement *before* `style.left`/`.top` is set (`:158`→`:162`, `:210`→`:214`), but both happen synchronously in the same task with no `await`/rAF between them, so no frame paints the tile unpositioned | Positioned by JS | None (`run_r6_browser.py`, `run_r6_reference.py` take screenshots but never read tile geometry) |
| 26 | `r7.css:27` | `.document-tile` | tile `<canvas>`, `renderViewport()` in `r7-reference-app.js` (the only one of the 5 files that load `r7.css` — `r8-update.html`, `r7-longevity.html`, `r7-compatibility.html`, `r7-close-minimizer.html` — that ever instantiates `#tiles`/`.document-tile` markup) | `#tiles`/`.tile-layer` (`inset: 0`) → `#surface`/`.document-surface` (`position: relative`) | Yes — `#viewport`/`.viewport` (`overflow: auto`) | Top-left of `#tiles` | **No** — `renderViewport()` never sets `.style.left`/`.top`; the canvas is inserted via `$("#tiles").replaceChildren(canvas)`, always as the sole child | **Does not fit any of the four given buckets cleanly.** It is not JS-positioned, yet it is also not the 093 shape: `#tiles` is emptied before every render, so the tile is always the *only* content and its static position (top-left, i.e. `0,0`) happens to be correct, because `renderViewport()` only ever renders from `xTwips:0, yTwips:0` (no tall preceding sibling exists inside `#tiles` the way `#canvas` precedes `.a11y-only`) | None |

**No row above is a second live instance of the 093 defect.** Row 1 is the
defect itself. Every other row either has an explicit JS positioning call
that runs before the element can be observed unpositioned, has enough CSS
offset to never be static in the first place, or is not inside anything that
scrolls.

## 4. Guard status, in detail

- **`#sink` (`e2-editor.html`, the fixed element) — guarded.**
  `sink_does_not_drag_the_page` (`tools/probe_064_format_reaches_typing.py:2603`,
  registered as check id `"sink-does-not-drag-the-page"` at `:2911`, invoked at
  `:3072-3074`) reads `#sink`'s geometry and `.desk`'s scroll fraction, with a
  mutation-based positive control (`PARK_SINK_AT_THE_BOTTOM` at its old static
  position must reproduce the drag).

- **`.a11y-only`/`#a11y-doc` (the row-1 defect) — measured, not a standing
  guard.** `tools/probe_093_a11y_region_position.py` (356 lines) is a
  purpose-built instrument for exactly this defect, pre-registered in finding
  093 before any number existed. **It has now been run**: this directory
  already holds `RESULT-phase2-region-position.md` and two raw JSON files
  (`phase2-region-position.json`, `phase2-region-position-1920x1080.json`),
  timestamped 2026-09-08, confirming `#a11y-doc.offsetTop` (928) equals
  `#canvas.offsetHeight` (929) on both profiles and that scrolling the region
  into view consumes 0.9759–0.9392 of `.desk`'s scrollable room. That is a
  banked *measurement*, not a *regression gate*: `probe_093_a11y_region_position.py`
  is not called from the `Makefile`, from `run_e2_c_product_path.py`, or from
  any other runner (checked by grepping its filename across both) — nothing
  re-runs it automatically. The one check that *is* wired into the standing
  regression net and touches this DOM subtree, `run_e2_c_product_path.py`'s
  `READ_A11Y_REGION` (`:619-629`), reads only `.textContent`/`.dataset`/
  `aria-activedescendant` — never `.offsetTop` or any geometry — so a future
  regression run would not re-detect this even though a human-run instrument
  already has.

- **Everything in rows 3–12 (`demo-editor.html`, `demo-structure.html`,
  `demo-structure-discovery.html`) — no guard of any kind.** These three
  files are not referenced by any file under `tools/` or `tests/`
  (`grep -rl demo-editor.html tools/*.py tests/*.py` and the same for the
  other two both returned nothing). Their JS-positions-it safety (rows 3–8,
  11) is real but currently rests entirely on reading the source, not on any
  check that would catch a regression.

- **Rows 13–24 (the 12 `e2-c-*` probe harnesses' `#sink`) — no guard**, but
  also no hazard by construction (not in a scroll container, and DOM order
  keeps the one growing element, `#log`, after it rather than before it).

- **Rows 25–26 (`.document-tile` in `r6.css`/`r7.css`) — no guard.**
  `run_r6_browser.py`, `run_r6_reference.py`, `run_r7_input.py`,
  `run_r7_usability.py`, `r8_release.py`, and `tests/test_r8_bundle.py` were
  all checked for `getBoundingClientRect`/`offsetTop`/`offsetLeft`/
  `style.left`/`style.top`/`scrollTop` — zero hits in any of them. Some of the
  r6/r7 tools do capture screenshots, but a screenshot is a pixel comparison,
  not a position read, and this tree's own prior finding (see `probe-measurement-discipline`
  material referenced from `AGENTS.md`) is that pixels cannot distinguish "not
  drawn" from "drawn somewhere else" — so a screenshot's presence is not
  counted as a guard against this specific hazard.

## 5. What this census did **not** cover

- **No browser was launched.** Every "positioned by JS" and "not the 093
  shape" conclusion above is a source-reading argument (order of statements,
  presence/absence of `await`/rAF between DOM insertion and style assignment,
  CSS cascade). None of it was confirmed by measuring an actual laid-out page,
  except for row 1, where an independent instrument's already-banked results
  are cited (not re-run) in §4.
- **The Tab-order path for `demo-editor.html`'s `#sink` (row 9) is
  explicitly left undetermined**, not folded into "positioned by JS" — see the
  note in the table. This is the one row in the table that could plausibly
  hide a second live instance of the 093 shape and that this census could not
  rule out from source alone.
- **`dist/`, the Chrome-extension profile trees under it, and everything
  outside `wasm_sdk_probe/`** were not enumerated — see §1 for why.
- **CSS `position: sticky` was not in scope** (the finding and the requesting
  brief both name only `absolute`/`fixed`); no census of `sticky` usage was
  attempted.
- **This document proposes no fix.** Row 1 restates finding 093; every other
  row is reported as found, per the task's constraint against patching.
