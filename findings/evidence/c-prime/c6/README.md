# C6 red case on the P page (spec SPEC-M3-production-ui §17.4, §17.5; predictions §17.6, committed in `93a455e3` before any run)

Question: does finding 062's 65,535-row browser canvas ceiling blank the last page of a long document on the page as shipped (`dist/` = `36c2b18b…`, release P, the whole document on one canvas)? If it does not, the ceiling claim and C6 are withdrawn and C′ goes back to the owner (§17.1).

Instrument: `wasm_sdk_probe/tools/probe_c6_long_document.py` (new; no product byte changed; dist through a mirror). A4 documents of an exact page count from `create_long_document.build`, opened through the product's file input at the given devicePixelRatio and CSS window (Chrome `Emulation.setDeviceMetricsOverride`; Firefox `MOZ_HEADLESS_WIDTH/HEIGHT` and `layout.css.devPixelsPerPx`, as the typing-latency wrapper does). After the session is quiet plus 10 s, `#desk` is scrolled so that the top of the document, then the top of the LAST page (fraction (pages − 1) / pages of `#paper`), is at the top of the view, and a screenshot cropped to the desk counts pixels darker than luma 128 ("dark"). Every toast is logged.

Smoke (not counted, `smoke/chrome-02p-dpr1.json`): 2 pages at ratio 1, canvas 900 × 2,491; top 34,723 dark, last page 34,901 — a screenful of text is tens of thousands; the desk background is `#f4f6f8` and paper white, so a blank view is near 0.

Runs (both browsers): red 40 pages `--dpr 2 --window 1400x1000` (predicted canvas 1800 × ≈ 98,900) and 50 pages `--dpr 1.5 --window 1400x1000` (1350 × ≈ 92,750); controls 24 pages ratio 2 wide (≈ 59,350) and 33 pages ratio 1.5 wide (≈ 61,200). Prediction (§17.6): the two red documents show no ink on the last page in both browsers — Chrome silently, Firefox with 「重繪失敗」; the controls are drawn.

## Results (2026-10-10 16:05–16:10 UTC; `run-p-page.sh`, log `run-p-page.log`; all eight runs exit 0; page `36c2b18b…`, probe `7a31fba6…`)

| Run | Canvas | dark at the top | dark on the last page | toasts |
| --- | --- | --- | --- | --- |
| Chrome 40 p, ratio 2 wide | 1800 × 98,869 | **0** | **0** | 已開啟 only |
| Chrome 24 p, ratio 2 wide (control) | 1800 × 59,338 | 147,194 | 154,776 | 已開啟 only |
| Chrome 50 p, ratio 1.5 wide | 1350 × 92,682 | **0** | **0** | 已開啟 only |
| Chrome 33 p, ratio 1.5 wide (control) | 1350 × 61,181 | 74,573 | 72,030 | 已開啟 only |
| Firefox 40 p, ratio 2 wide | 1800 × 98,869 | **0** | **0** | **重繪失敗：11：CanvasRenderingContext2D.putImageData: Canvas exceeds max size.** |
| Firefox 24 p, ratio 2 wide (control) | 1800 × 59,338 | 127,420 | 132,867 | 已開啟 only |
| Firefox 50 p, ratio 1.5 wide | 1350 × 92,682 | **0** | **0** | **重繪失敗 … Canvas exceeds max size.** |
| Firefox 33 p, ratio 1.5 wide (control) | 1350 × 61,181 | 66,204 | 69,735 | 已開啟 only |

**C6's red case reproduces, and worse than predicted.** Predicted: the last page blank, Chrome silent, Firefox 「重繪失敗」; the controls drawn. Observed: the controls are drawn, but the two red documents are blank **everywhere** — the top of the document has 0 dark pixels as well — in both browsers; Chrome says nothing and its state is `ready`, Firefox toasts "Canvas exceeds max size". So the question §17.5 asked ("bottom not drawn, or the whole canvas fails?") is answered: past 65,535 rows the whole canvas fails, not only the rows past the limit (062 had measured only a canvas of 65,536 rows, where the bottom rows were lost). The page counts of §17.1 stand as computed (canvas heights within 0.05 % of the arithmetic: 98,869 against 98,920, 92,682 against 92,750). The ceiling claim is not withdrawn; C′ goes on (§17.1). Registered as finding 126.
