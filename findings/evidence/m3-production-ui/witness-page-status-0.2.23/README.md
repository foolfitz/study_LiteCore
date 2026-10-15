# Production UI A3-1 and the page-number line (2026-10-15)

**What went red.** In the 0.2.23 count (chain `20261015T025837Z`), `../runs-0.2.23/counted-ctl-S-P.json` scored the P arm **0/1 in both browsers**. A3-1 failed with `controls [] text [{'text': '第 1 頁，共 18 頁', 'in': 'div#page-status'}]`, so 7 of the pooled red cases had no passing P run to mutate (`red cases: 20/20`, 21 notes; 27/27 with 13 notes was expected).

**Why that is the check, not the product.**
- `#page-status` is the page-number line of SPEC-M3-link-batch §4.3. The owner placed it under §10.10 Q-A: "放在畫面底部的狀態列，左側寫「第 N 頁，共 M 頁」…由頁面畫，所以宿主也看得到".
- The page's own comment (`web/e2-editor.html:322–332`) says it is kept outside `.statusbar` precisely because the host hides `.statusbar`, and "這一行在宿主裡也要看得到".
- Its text is written only by `pageStatusText` (`editor-shell-v2/narrow-editor-v2-session.js:253–260`): `第 ${first} 頁，共 ${count} 頁` or `第 ${first}–${last} 頁，共 ${count} 頁`.
- A3-1's allowed text places (`TEXT_PLACES`) were written before the line existed (0.2.20, engine v20). No production-UI arm had run on a v20 page before this count; the C witness `../witness-c-0.2.23/` ran only the R and B3x arms.

**Repair** (`tools/check_m3_production_ui.py`, runner `36c66e69e668bca1` → `828aed3cc4da20a7`):
- The scorer allows a `badText` entry only when it is in `div#page-status` **and** its text fully matches `第 \d+(–\d+)? 頁，共 \d+ 頁` (`PAGE_STATUS_TEXT`, `developer_text()`).
- The browser-side inventory is unchanged, so reports keep recording the line. Already written 0.2.20+ reports re-score without a re-run.
- One mutation was added, so the narrowed allowance has a red case: "A3-1 the page-number line shows other text" (`修訂 3` in `div#page-status`).

**Witness and readings**
- `before-/after-counted-ctl-S-P.score.txt`: P/chrome and P/firefox **0/1 → 1/1**, `allPass` false → true. Bctl and S are unchanged.
- `after-pooled-red-cases.txt` (`../runs-0.2.23/counted-KR-x3.json` + `counted-ctl-S-P.json`, as `read-0.2.23.sh` pools them): **`red cases: 28/28`**, 13 notes, all `no passing B3x run`, exit 1 by the runner's every-mutation rule. That is the 27 the count preparation expected plus the new mutation.
- `census.txt`, every committed production-UI report (32, `census-reports.txt`), `--score` and `--red-cases`, before and after:
  - **`--score` changes only for `runs-0.2.23/counted-ctl-S-P.json`.**
  - Every `--red-cases` output changes only by the new mutation: its count line goes +1/+1 where a P run passes, or it gains one `no passing P run` note where there is none.
  - The one exception is the 0.2.23 report itself, whose seven P notes disappear because P now passes.
- `make test-e2-c-static` exit 0 (108 tests OK) after the edit.

Not done: a fresh browser run of the P arm. The re-score reads the counted report's own inventory, and a run would add no information about the scorer.

**§34.4**: repaired because of execution **+1** (witness: the counted report above).
