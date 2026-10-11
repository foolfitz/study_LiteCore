# The witness: result (2026-10-11)

The unported product-path net on the C′-only page, run exactly as `PREDICTION.md` (committed in `ea0bbd04`,
before any run) says. **Result: 0 witness-red cells in both browsers, and 0 other movements. The prediction
holds.**

## What ran

| Item | Value |
|---|---|
| Page | C′ only: `57d21411` on `c-prime-page`, cherry-picked into main as `90242ebc`; `make e2-c-assets` put it in `dist/` (`dist/e2-editor-app.js` = `web/e2-editor-app.js` = sha256 `f5121fd432ac02ea…`). Each report's `servedShell.entrypointSha256` names `f5121fd…`. |
| Runners | the pre-port commit `08d73cff`, restored temporarily by `run-witness.sh`: `run_e2_c_page_smoke.py` `5f26e3bd1280b3a9`, `run_e2_c_product_path.py` `a6e318966d50cf14`, `check_m3_page_honesty.py` `505f4f3a91ab93e5`. HEAD's ported runners were put back on exit and checked: `cc38ee97ca20611d`, `aa9a22806d10ed71`, `17a38fe756fe3e0b` (`product-path/chain.log`: `RESTORE OK`). |
| Arm | v19 (dist as served, no `--candidate-profile`), Chrome 01:33:12–01:39:39Z exit 0, Firefox 01:39:39–01:45:48Z exit 1 |
| Reference | `../../release-0.2.11/product-path/e2-editor-v19-{chrome,firefox}-r{1,2,3}.json` |
| Reader | `judge_witness.py` (PREDICTION.md's rule: FAIL in the witness and PASS in all three 0.2.11 rounds of the same browser; any other outcome not among the three reference outcomes is listed apart). Its control and red cases, run before the witness was read: `judge-red-cases.txt` (control exit 0; one all-PASS cell flipped to FAIL → exit 1 naming it; mixed browsers → REFUSED; incomplete witness → REFUSED). |

## Result (`product-path/judge-output.txt`)

| Browser | Cells | Witness-red | Other movements | Report |
|---|---|---|---|---|
| Chrome | 42 | **0** | 0 | `ok: true`; NE `notice-action-recovers-the-session`, `a-refused-action-is-reported-and-changes-nothing` (as in all three 0.2.11 rounds) |
| Firefox | 42 | **0** | 0 | `ok: false`; the only FAIL is `an-inline-format-reaches-a-selection`, FAIL in all three 0.2.11 rounds (the known Firefox red); its NE set lies within the reference outcomes |

**Positive control (the window was really in effect):** the long-document arm
(`a-long-document-is-drawn-or-the-product-says-it-is-not`, PASS) records the canvas the unported runner read.
On the C′-only page it is the window; on the P page it was the whole document:

| Arm | Witness `geometry.height` (device rows) | 0.2.11 r1 |
|---|---|---|
| one page, dpr 1 | 1,012 | 1,012 |
| 5 pages, dpr 1 | **4,092** | 4,992 |
| 20 pages, dpr 1 | **4,092** | 19,919 |
| 35 pages, dpr 1 | **4,092** | 34,847 |
| 20 pages, dpr 2 | **4,092** (CSS 2,045.95 px) | 39,839 |
| the document that grew | 2,007 → 3,002 (below W, wholly on the canvas) | 2,007 → 3,002 |

So "0 red" is not "C′ never engaged": the windowed canvas was there in four arms and the unported readers,
reading only the canvas's own frame at `winTop = 0`, still judged every cell as on the P page — the reason
PREDICTION.md gives.

## Before the witness

- **Uncounted smoke** (`smoke/smoke-chrome.txt`): HEAD's `run_e2_c_page_smoke.py` on the C′-only page in Chrome,
  exit 0, `ok: true`, revision 0 → 1, state `ready`.
- **Static suite on the C′-only tree** (rule ddd; `../page/static-on-main-cprime-only.txt`): `make
  test-e2-c-static` exit 2 — node tests pass; Python 108 tests, 4 failures and 1 error, three kinds:
  1. `test_the_real_manifest_matches_the_real_tree`: the shell manifest (v60) is out of date because the page
     changed. Expected between a page change and the next shell freeze (finding 091's shape); clears at v61.
  2. `gesture-abort-not-wired` matches 0 times: known, re-anchored by `13f91117` on the branch.
  3. **Not anticipated by the handoff**: `--caret-source-diagnostic` (finding 084's instrument) cannot find two
     anchors on the C′ page — `CARET_SOURCE_ANCHOR` (`moveSinkToCaret`'s second line now reads `#paper`) and
     `CARET_ANNOUNCE_ANCHOR` (`onEvent`'s `if` now opens a block); three tests (two anchor counts, one patch
     that refuses). The instrument's inserted code reads neither `#canvas` nor `#paper` geometry, so this is a
     re-anchor only. It edits `run_e2_c_product_path.py`, so it was not done before the witness (whose
     restore step checks HEAD's hash); this file is its witness.

  None of the three is read by the pre-port product-path runner (it does not run the static suite), so the
  witness is not affected.

## What this leaves (no decision taken here)

Per PREDICTION.md's last section: with 0 witness-red cells, the ports of `run_e2_c_product_path.py` and
`check_m3_page_honesty.py` have no witness on the C′-only page, and the port of `run_e2_c_page_smoke.py` has a
predicted one only on a host build (production UI `Rdel`). §34.4: a check changes on a witness, or is only
registered. The decision is the owner's (or fable's).
