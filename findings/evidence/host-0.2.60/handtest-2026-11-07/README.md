# Owner's hand test of host 0.2.60 (2026-11-08, shortly after 00:03)

Script: `HANDTEST-2026-11-07-host-0.2.60.md` (10 items), on the install of 2026-11-07 23:51 (`../README.md`), fixtures in admin's
`手測-0.2.60/`.

The owner's report, verbatim: 「測完了，基本上都正常，我只想改一個UX的小地方，就是Calc在縮放的時候，好像是以當前畫面的中心為焦點，
但比如說資料只有上面幾列的時候，中心點其實是空白的，放大之後就只能看到空白，所以我覺得縮放時應該以畫面左上角為焦點
或是你看一下collabora 怎麼做？」

- No item was reported as failing. That includes item 1, the reason for this release: a column copied into desktop Calc no longer
  splits at spaces. It also includes the two things the machine could not see: a real Ctrl+C writing both formats, and the paste
  into desktop Calc.
- One UX request: the zoom anchor. The page keeps the viewport's centre in place (SPEC-P-calc-zoom P-Z5, as specified). When the
  data fills only the top rows, the centre is empty cells, so zooming in shows only empty cells. The owner suggests the view's
  top-left as the anchor, or Collabora's behaviour.

What the two references do (read from the code, not measured):

- Collabora Online co-26.04, desktop Calc (`browser/src/map/Map.js`, `getDesktopCalcZoomCenter` and `setDesktopCalcViewOnZoom`;
  `browser/src/layer/tile/CanvasTileLayer.js`, `_getZoomDocPos`): the anchor is the cell cursor's top-left corner if it is in
  view; otherwise the centre of the cell selection if that is in view; otherwise the view's centre. The anchor keeps its position
  on screen, and the new top-left is clamped at the sheet's start (no scrolling past row 1 or column A).
- Desktop LibreOffice Calc (`sc/source/ui/view/tabview5.cxx` `ScTabView::SetZoom` -> `tabview3.cxx` `ZoomChanged`): zoom changes
  only the scale. The view's position is kept in cells (`ScViewData` PosX/PosY) and is not touched, so the top-left visible cell
  stays.
