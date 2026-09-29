# Ruling: control 4 on the real php-fpm path, and what binds the tools (fable, 2026-09-29, on the owner's authority)

The owner was away and had authorized fable to decide in their place ("如果有需要決策的地方，
請發包給fable，我授權它代替我裁決"). Three items of the second review
(`review-2026-09-29-opus-2.md`) had been left for "the next session to decide": item 4 (a
php-fpm-faithful control for I2-3), item 14 ("no subreaper in the container" was inferred),
item 12 (`module_shas` misses lazily imported modules and everything `make test-e2-c-static`
reads). The main session measured first (`fpm-path-measurement-2026-09-29.md`), then asked.
fable ran read-only. The Chinese "WHY" below is the ruling's own text, for the owner.

## Question, as put

- **Q1** (item 4). A: no control, restate I2-3's reach as statistical. B: an in-window control
  through the probe app's HTTP route (the reviewer's suggestion), with an excused span in I2-3
  and I2-4. C: an in-window **control 4 over FastCGI** — a real `php-fpm: pool www` worker holds
  a mount file ~3 s, runs a foreground `/tmp/litecore-ctl/…` child, backgrounds another; every
  window must see all three. Main session leaned C, with A's restatement regardless.
- **Q2** (item 14). A: mark as inference. B: cite the one-off measurement. C: per window, via
  Q1-C's backgrounded child. Main session leaned C if Q1 is C.
- **Q3** (item 12). A: each runner records its own loaded modules at exit. B: hash every
  `tools/*.py` plus the Makefile. C: record `git rev-parse HEAD:wasm_sdk_probe` and an empty
  `git status --porcelain --untracked-files=no -- wasm_sdk_probe` at the equivalence check,
  window start and window end. Main session leaned C.

## RULING

Q1 C (with A's reach restatement, mandatory regardless) · Q2 C · Q3 C, amended:
`--untracked-files=all`, plus the last commit touching the path, plus interpreter versions.

## WHY (for the owner, verbatim)

> Q1：B 最差——I2-4 的整句意思就是「窗內沒有任何 /apps/litecoreprobe/ 請求」，B 要在那裡開豁免；而且照探針 app 的程式碼，`.wasm` 根本是 redirect 到 Apache 靜態檔去，不經 php-fpm，PHP 那條路也只在 `file_get_contents` 那幾毫秒持有 fd，所以 B 既不 php-fpm-faithful 也不改機率。A 只有一次性量測，容器換 image、換 php-fpm 設定就沒人看著。C 是逐實例性質（每個窗都要看到），成本一支 docker exec 約 5 秒，跑在 runner 之前所以不跟 runner 搶 worker。但要講清楚：C **不改 I2-3 的射程**，它證明的是「儀器看得到真 php-fpm worker 的 fd」與「I4-1a／1b 在真的 php-fpm 血統上會亮」——現有對照 1 是 bash 改名的假 php-fpm，掛在 docker exec 底下。射程句照 A 改寫，不論 C 落不落地。
>
> Q2：既然 C 每個窗都有一個真 worker 背景化的孤兒，「沒有 subreaper」就從推論變成每窗量到的事實。但要寫成量到的那句——「兩條路（docker exec 根：對照 1；php-fpm worker：對照 4）背景化的子行程在對照期間內是 PID 1 的直接子行程」——不是「容器裡沒有 subreaper」這種全稱句。fd 繼承那件事留在一次性量測檔裡登錄。順帶查過：PID 1 是 `bash /pre-start.sh` 停在 `wait`，孤兒會被收屍，三次 shakedown 之後沒有殭屍。
>
> Q3：A 只綁 runner 自己 process 載入的模組，`make test-e2-c-static` 那串（node 測試、Makefile、web/*.js）還是沒人綁，而且要改四支 runner 的記錄路徑、碰 I3-8。B 是手工枚舉（第 1 節不可當硬判準那種）：多一個輸入目錄它不會紅。C 是工具封閉的枚舉，成員由 git 生成。但主 session 寫的 `--untracked-files=no` 有洞：一個沒進版控的 `tools/foo.py` 或 `tests/*.test.mjs`（Makefile 用 glob）它看不到；改成 `all` 要空，今天這棵樹本來就沒有這種檔，不多花任何東西。另外現況比 F4 說的還少：`module_shas` 量的是編排器自己的 process，runner 是 subprocess。

## FACT CHECK (fable's, condensed)

- F1 (probe route holds the file only during the read) — **partly wrong**:
  `ProbeController.php:151-153` redirects `.wasm` (and static-mode JS) to Apache's static
  `dist/`, so under B the largest file is not read by php-fpm at all. The conclusion stands.
- F2 (41 MB gz served in 0.096 s) — confirmed, but that run is the **dev** instance through the
  host app's `StreamResponse` (`EditorController.php:226`). "~80 cold opens" unverified; the
  third shakedown had 471 engine-route requests in a 383 s window.
- F3 (the fpm-path measurement) — confirmed as documented, not reproduced (read-only).
- F4 (`module_shas` misses things) — confirmed and understated: `module_shas` runs in the
  orchestrator, while the runners are subprocesses.
- F5 (one request per worker) — confirmed: pool `www`, `pm = dynamic`, `max_children 8`,
  workers uid 1000, socket 0666, `request_terminate_timeout 0`; the measurement's worker pid
  equals the fd holder's.

The main session re-checked before acting: `shakedown/2026-09-28T231953+0000.json` has
`probeLog.engineRoute` 471 over a 383.5 s window; `check_m3_host_entry.py:104` imports
`build_e2_c_shell_bundle` inside `served_shell()`; `EditorController.php:226` is a
`StreamResponse`; the working tree had 5 modified files under `wasm_sdk_probe/tools/`.

## CONDITIONS, and what was done with each

| # | condition (fable's words, condensed) | done |
| --- | --- | --- |
| 1 | Restate I2-3's reach: a read shorter than 0.5 s is caught with probability ≈ duration/0.5; cite F2; statistical over the window's engine requests, not a per-fetch guarantee; default conclusion if never seen. | Spec §4 I2-3. |
| 2 | Control 4's script order: background orphan first (`… </dev/null >/dev/null 2>&1 & echo $!`), then the foreground child, then fopen + sleep 3 + fclose, then print `worker=… orphan=…`. | `FPM_SCRIPT`. |
| 3 | Distinct names (`lcfg`, `lcorphan4`); wanted set per control; `I4-1a lcfg` counts only when its php-fpm is the reported worker and that worker's parent is `php-fpm` with ppid ≠ 0 (the real master). | `CONTROL_WANTS`, `control_label`. |
| 4 | One span per control; an I2-3 entry is excused iff (control lineage OR pid = reported worker) AND within that control's span ±1 s; a missing worker pid is "not seen", never SKIP. | Scorer. Stricter than asked: the worker's fd is excused only on the file the script opened (condition 5's option). |
| 5 | Named limit: for ~3 s one php-fpm pid may open anything on the mount unflagged; optionally record `readlink` so the problem line carries the path. | The loop records each fd's target; the excuse is restricted to `FPM_FILE`, so the remaining limit is "that worker, that file, that span". Spec §3.5. |
| 6 | Red cases: drop the worker's fds; alter the reported worker pid; drop `lcorphan4`; drop `lcfg` or put it below a fake master; shift the span. | Seven cases (one more: the worker holding another mount file). |
| 7 | Control 4 runs where the controls run now, in its own docker exec; cleanup removes `/tmp/litecore-ctl` including the two PHP files. | `positive_controls()`. |
| 8 | Q2 wording: "on both paths exercised (docker-exec root: control 1; php-fpm worker: control 4) a backgrounded child is a direct child of PID 1 within the control's span, measured in every window"; strike the old sentence; fd inheritance stays in the one-off file. | Spec §3.5. |
| 9 | Q3 at three points: tree hash, last commit touching `wasm_sdk_probe`, `--untracked-files=all` porcelain (must be empty); tree and last commit equal across all three; keep `module_shas`; a non-empty porcelain at window start **refuses** a counted run. | `tree_binding()`, `run()`, scorer I3-8 (strict). |
| 10 | Named limit: gitignored paths are outside; `dist/` is bound by the page/engine shas. | Spec §3.3. |
| 11 | Also record and require equal: `sys.version`, `node --version`, `make --version` line 1. | `tree_binding()`. |
| 12 | I3-7: the dev host-entry report's `startedAt` must be after `equivalence.json`'s timestamp. | Scorer I3-7. |
| 13 | Red cases for Q3: tree hash differing at start, porcelain non-empty at end, last commit differing. | Four cases (one more: an interpreter version differing). |
