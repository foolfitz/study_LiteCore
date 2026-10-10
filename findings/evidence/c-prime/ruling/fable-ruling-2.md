# fable's ruling on brief 2 (C5 (i) stopped on the static suite), verbatim — 2026-10-11

The owner: 「做法發給fable裁決，我授權他待我決定」. Brief: `brief-2-c5i-static-suite.md`. fable ran as a subagent, read-only.

RULING: **B** — give the test's `#canvas` stub `dataset: {}`; runners stay byte-identical; `make test-e2-c-static` → 0; re-run only the five static-gated M3 runners counted-shape; re-compare, expect 0. Not A, not C.

WHY（給擁有者）
1. 瀏覽器裡的 canvas 一定有 `dataset`，是假畫布少了這個欄位；這 18 個紅是測試的模型沒跟上，不是搬過的網在瀏覽器裡出錯——168＋45 格逐格相同就是量到的證據。
2. 選 A 會改 runner 的位元組：產品路徑是 `import` 進來用這段字串，它的 pin 只算自己檔案的雜湊，看不到這個改動——改了之後「同一個 pin、不同的讀取器」，整條鏈的 0 差異就得重跑才算數。
3. 選 C 等於事後把 C5 (i) 的「判定行也要相同」放寬，而且是靠人解釋五個判定；規矩說終止宣告不能靠起草方的判斷，而且發佈鏈第 7 步本來就要跑這套靜態測試，不修也過不了。
4. B 的代價就是那五支重跑約兩小時（脫離 session 跑），產品路徑、production UI、host entry 不用重跑——它們的位元組沒變，也從來不看靜態測試。
5. 這算一次「因執行而修」（3 → 4），證人就是這五份判定被作廢的報告；「因審核而修」維持 5，不得再長。

CONDITIONS
1. One file changes: `wasm_sdk_probe/tests/test_ink_rows_caret.py`, the `#canvas` stub in `_run` gains `dataset: {}` and nothing else (no `window`/`changes`/`bands` keys; nothing under `tools/`, `web/`, `dist/`). Check: the commit's `--stat` lists that file alone; sha256 prefixes of the seven runners unchanged (`cc38ee97`, `aa9a2280`, `17a38fe7`, `8f4829e2`, `da362514`, `cc07367c`, `266d8b66`).
2. `make test-e2-c-static` exits 0 with 108 tests / 0 failures; its tail saved beside `static-failure-excerpt.txt` (which stays) as the after-state.
3. Re-run only page honesty, locks, versions, assets, same second, counted-shape, with the same invocation lines as `chain-c5i.sh`, detached, on `dist/` = `web/` = `36c2b18baa83`, host `6b53c2e`; reports go to a sibling dir (e.g. `runs-p-page/m3-rerun/`), the five witness reports and `chain.txt` untouched. No shakedown repeat: shakedowns run `strict=False` and never invoke the static suite, and nothing they exercise changed. Each new report: `static.testStatic` 0, same `runnerSha256`, same `static.page.dist`, same `hostRepo`.
4. Re-compare with `compare.py`: same 0.2.11 reference set, the ORIGINAL product-path dir (`--cand-runner aa9a2280…`), original production UI and host entry reports, the five NEW `--m3` candidates. Expect `SUMMARY differences 0`, saved as a second output file next to `compare-output.txt`. Any nonzero = STOP and hand back again; this ruling pre-authorizes nothing beyond zero.
5. Product path (168 cells), production UI (three reports), host entry stand as measured; not re-run (Q2). Their runners never gate on the static suite (grep: no `testStatic` in product path, production UI, host entry).
6. §34.4 entry (Q3): 因執行而修 3 → 4 — check = the ink-rows test fixture; witness = the five counted-shape reports in `runs-p-page/m3/` at `87d57ff6` (each `static.testStatic` 2, every cell equal to 0.2.11) plus the excerpt. 因審核而修 stays 5. README append + §17.12 append carry both numbers.
7. Two NOTE lines, no code (§34.2): (a) `__docWindow` throws in a non-browser host without `dataset` — only tests are such hosts; (b) see CHECKED last item.

CHECKED
- F-a/F-b: all five JSONs read with python: `testStatic` 2, `problems` = the static exit string, every cell equal; host entry has no `static` at all. Gate ordering: each counted runner runs `make test-e2-c-static` BEFORE the browser starts (`check_m3_page_honesty.py:1332`, `check_m3_locks.py:1214`), so cells never depended on it.
- F-c: `test_ink_rows_caret.py` `_run` stub = `{width,height,getContext,getBoundingClientRect}`, no `dataset`; node run: `dataset: {}` → `windowed:false`; no `dataset` → the same TypeError. Only this test stubs a canvas (grep over `tests/`). Makefile target includes it (:3535 unittest line).
- F-d: `identity.mjs:31` non-windowed branch is literally `dataset: {}` — B's fixture already is the identity proof's fixture. `git show --stat a0925990 -- wasm_sdk_probe/tests` is empty: the port touched no test.
- A's blind spot: `run_e2_c_product_path.py:78` imports `DOC_WINDOW_JS`; `runnerSha256` = own file only (`:1338`), so A changes the product path's reader without moving its pin.
- F-e/F-f: handoff :18 and :59 (3 / 5; "any difference = STOP"); chain.txt durations 60/46/4/4/11 min.
- Spec: §17.4 C5 defines an M3 difference as "判定行或任一臂的計數不同", so C is a post-hoc criterion move (CLAUDE.md §8/§9).
- Outside the brief, measured not inferred: on a P-page canvas `__docRowsCover` sleeps once before returning (`waited:'current'`, 51 ms in node), so every ported reader pays ~50 ms per read — §17.11 says 「立即讀」. Not a difference (the chain measured 0 with it in), not to be fixed now (it would change runner bytes); NOTE it, and it becomes a §34.4 witness only if a timing arm goes red.

## Main session's check (2026-10-11)

The last CHECKED item does not hold for the readers as written. `__docRowsCover` would sleep once on a P-page
canvas if called, but no ported reader calls it there: each reader first tests `__docRowsHeld(win, ...)`, which
returns `true` at once when the canvas has no `data-window` (`!w.windowed`), and returns `read(win)`
synchronously (TOP_INK, CARET_COLUMNS, LINE_INK, INK_ROWS in `run_e2_c_product_path.py`; TEXT_LINES in
`check_m3_page_honesty.py`). Measured in real browsers before the chain: every ported reader returned a plain
object with no `windowWait` on the served P page, Chrome and Firefox (`../c5/port-identity/paper-vs-canvas.json`,
`readersSynchronousAndClean: true`). So condition 7 (b)'s NOTE is recorded as "examined, does not apply"; the
ruling itself does not depend on it.
