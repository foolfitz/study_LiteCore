**Ruling 3 (v21, finding 154), fable, 2026-10-17, read-only.**

Basis. Read in full: the brief (`review/brief-fable-3-f154.md`, `c6884f42`), CLAUDE.md 「驗收判準的形式」 §1–§11, spec v21 §1 (`:27`), §11.0–§11.1 (`:338-366`), §12.3 (e) (`:464-471`), §12.4 (`:476-519`), the revision log (`:520-536`); `SPEC-M3-paragraph-merge.md` §34 (`:1164-1250`); `SPEC-M3-link-batch.md:535-541` (the v20 re-pin precedent); ARMS-item1.md §0–§1 (`:8-37`), D2 (`:186-216`), D-1 (`:606-610`), §8 (`:713`); `run_v21_d2.py` whole file (sha `ce169ef8…`, equal to `git show 1fe9588d:…`); `probe_10_14n.py:278-300, :344-370`; `e2-editor-app.js:60-72, :170-181, :1215-1229, :2340-2404`; `e2-editor.html:228-252, :305-315, :365-378`; `editor-shell-v2-bundle-v74.json`; `package_m3_engine.py:62-76, :109-112`; `run_merge_wasm_shakedown.py:160-177`; host repo `templates/editor.php` (whole), `lib/Controller/EditorController.php:134-185`, `appinfo/info.xml:11`, `nextcloud/core/css/server.css` line 14, `nextcloud/version.php`, `git log` / `git show --stat 03970d0`; shakedown README §1–§5.9; `findings/evidence/host-0.2.25/README.md`; finding 154 and `findings/evidence/154/README.md`; handoff 10-17b `:60-120`. Ran read-only `python3 -I` over: the 8 D2 reports, the 2 `diag-154-*.json`, the 12 item-1 reports, the 0.2.25 and 0.2.24 archived `MANIFEST.json`, the v74 bundle. Started no browser, touched no ddev, edited and committed nothing.

---

## 1. 裁決（給擁有者）

選 **A**：在宿主的 `templates/editor.php` 加一條 CSS 規則，把「關著的對話框」藏起來，出宿主 **0.2.26**；引擎封包、頁面、HTML、殼層一個位元組都不動（buildId 仍是 `f5f0df762e1855f2`）。理由：這個缺陷是 Nextcloud 的全域樣式蓋過了瀏覽器內建的「關著的對話框不顯示」，問題出在宿主這一層，而宿主本來就在同一個檔案裡用同樣的方式藏頁面的其他部件；改頁面那邊（B）會換掉 HTML 和 engine 封包，已經跑完的第 1 項十二份報告都記著 HTML `1d158149…`，就對不上要出貨的東西，等於要重跑好幾個小時。D2 在 0.2.26 上重跑**就是釘死的判準本身**——判準寫的是「宿主」沒寫版號，規格第 1 節寫的是「0.2.25 **起**」；工具裡那個 `0.2.25` 只是指認候選宿主的釘子，跟著產品版本走，不算搬門檻、也不算修檢查，§34.4 兩個數字都不加。但**只准這一次**：0.2.26 上再紅或再 NE，第 1 項就照預設不在 v21 出貨，不再出第三個宿主版本。重跑 D2 之前，先用已經寫好的診斷工具在 0.2.26 上量一次（它在 0.2.25 上讀到的紅已經 commit 了），讀到對話框真的不顯示、點下去真的會定位游標，才准跑 D2。0.2.24 的紅案不用重跑；154 不用加新判準，記成 finding 加 v22 的工作項。

---

## 2. Answers

### Q1. Which fix

**RULING: A (host rule), host 0.2.26. Not B, not C, not "remove the markup".**

Why A and not the others, from the files:

- The defect is in the host layer. The page's own stylesheet sets no `display` on `#markdown-dialog` (`e2-editor.html:234-250`); it relies on the user agent's `dialog:not([open]) { display: none }`. Nextcloud 34.0.2's `core/css/server.css` (line 14) has the reset `article,aside,dialog,figure,footer,header,hgroup,nav,section{display:block}`, an author rule that wins over the UA rule. The host puts the page's `<body>` inside `#litecore-editor-root` as is (`EditorController.php:145-185`, `templates/editor.php:73-76`). Measured, both browsers: `diag-154-*.json` `asShipped.read.dialog.display == "block"`, `rulesSettingDisplay[0].sheet == "css/server.css?v=…"`, `elementAtPoint == TEXTAREA#markdown-text`, `placeCaretRequests == []`; `withRule`: `display none`, `CANVAS#canvas`, `placeCaretRequests == ["editorPlaceCaretV2"]`.
- The host already restates UA hiding where its own CSS breaks it: `templates/editor.php:31-50` hides shipped parts with `#litecore-editor-root … { display: none }`, and `:71` restates `#page-status[hidden] { display: none; }` with the comment 「`display` is set, so `hidden` is restated」. A `dialog:not([open])` rule is the same move for the same reason.
- Under A every identity the evidence carries stays equal to the shipped bytes: page `605cf24b…`, shell digest `e35923a0…`, wasm `db3408f5…`, HTML source `1d158149…`, buildId `f5f0df762e1855f2`. The engine package is not rebuilt; `engine/MANIFEST.json` stays byte-equal to the archive (`54bebc4d…`, verified equal today).
- Under B, `e2-editor.html` changes. It is inside the engine package (`MANIFEST.json` lists `e2-editor.html` `1d158149…`; `build_id` is over `{path: sha256}` of all 22 files, `package_m3_engine.py:109-112`), so buildId changes, and the 12 item-1 reports' `pages.*.htmlSourceSha256` (`1d158149…`, 12/12) no longer equal the candidate's HTML. See Q3: that evidence would not stand without a re-run or a post-hoc weakening of identity. B also leaves `HOST_EXPECT` blind: it pins no buildId (`run_v21_d2.py:62-71`, four keys), so a new package with the same page/shell/wasm would pass the identity check unremarked.
- "Remove the dialog markup" is out: `e2-editor-app.js:2399-2404` registers listeners on `el.markdownCancel`, `el.markdownDialog`, `el.markdownInsert` at module load; with the markup gone they throw and the module dies. Fixing that is a JS change, which moves the page hash `605cf24b…` and voids every item-1 report (§11.0).
- Page hardening (`#markdown-dialog:not([open]) { display: none }`) is right in itself and goes with v22, where the dialog ships and gets its own criteria (Q4).

**CONDITIONS (the fix, before D2 re-runs).**

1. The rule, exactly: `#litecore-editor-root dialog:not([open]) { display: none; }`. No `!important`. `:not([open])` is mandatory (a bare `dialog { display: none }` would kill the open dialog in v22). Nothing on `dialog[open]`.
2. Placement: in the host's **own** `<style>` block (`templates/editor.php:18-72`, the one holding the production-UI hides and `#page-status[hidden]`), with a comment naming finding 154 and the server.css reset. Not in the `@scope` block (`:8-10`) or the unscoped copy (`:15-17`): those are generated from the page's style and the fallback path drops the scoped one.
3. Host 0.2.26: `appinfo/info.xml` version bump and `templates/editor.php` in one host commit ("Host 0.2.26: …", English, as `03970d0`). `ddev occ upgrade` is the owner's step. Version is identity: no measurement between the template edit and the upgrade completing; every report must read `static.hostVersion == "0.2.26"` and `static.hostDirty == []`.
4. The package is untouched, checkably: `sha256sum engine/MANIFEST.json` = `54bebc4de343526bf44ad9b57472608942125b009ce16dee9787960c7b7a439b` (= the archive's); `check_engine_decoded.py` on the installed copy passes; `http_served_page.py` on 0.2.26 prints the same address `f5f0df762e1855f2-90d7bc2c` (the address is buildId plus the SERVE_POLICY hash, `EditorController.php:134-135`; the app version is not in it) and decodes page/worker/wasm as on 0.2.25. File under `findings/evidence/host-0.2.26/`.
5. **Red first, then the fix's acceptance, with the tool unchanged** (`findings/evidence/154/diag_markdown_dialog_on_host.py`, sha `757c44766d44445b221c2fd6d9f32d17af96b28511f60be19b527c5f41fdfa14`). Its red case is already committed: the two 0.2.25 runs (`asShipped`: block / TEXTAREA / no place-caret). On 0.2.26, both browsers, the **`asShipped`** branch must read: `dialog.open false`, `dialog.display "none"`, `dialog.box [0,0,0,0]`, `rulesSettingDisplay` containing an `inline` rule with selector `#litecore-editor-root dialog:not([open])` and `display none` (this is the "edit took effect" read: if the rule is not in the list, the served template is stale — check opcache/`occ upgrade` before judging the fix), `elementAtPoint CANVAS#canvas` with `insideDialog false`, `placeCaretRequests ["editorPlaceCaretV2"]`, `clickState.latency` containing 「定位游標」, `button.hidden true` / `display none`. `hostIdentity.hostVersion` must read `0.2.26`. The `withRule` branch runs as the tool does; it must read the same. Save as `findings/evidence/154/diag-154-0226-{chrome,firefox}-*.json`.
6. If any read in 5 fails: stop. Do not touch `run_v21_d2.py`, do not run D2. Report; the fix is wrong or not served.
7. Default if 5 is never done: D2 is not run → §11.0 「沒做」 → 「第 1 項不出貨」.

### Q2. Is D2 on the fixed host the criterion as pinned, and is the `HOST_EXPECT` change a move

**RULING: Yes, it is the criterion as pinned; the version change is a re-pin of the candidate's identity, not a move of a criterion and not a repair.**

- The pinned text names no version: 「`press-after-ctrl-home`（宿主）：Backspace 以 `verified-boundary-noop` 完成，revision 不變，存檔文字不變。0.2.24 上照舊是紅的」 (spec `:353`). The host version appears in spec §1 as 「新宿主版本（**0.2.25 起**）」 (`:27`), which includes 0.2.26. ARMS-item1 `:189` ("host 0.2.25") is the arm's plan, written when 0.2.25 was the next version; the ruling D-1 B (`:713`) says "the host run after the freeze is the criterion".
- `HOST_EXPECT["v21"]` (`run_v21_d2.py:62-66`) identifies the candidate host; the other three fields (page, shell digest, wasm) stay exactly as they are. The candidate moved because the product moved, not because the criterion was hard to satisfy. Precedent for "a pin following a product cutover is binding, not repair": `SPEC-M3-link-batch.md:535` 「這是綁定，不是修理：§34.4 兩個數字都不加」; the relink-queue re-anchor listed under "Not counted" in handoff 10-17b `:113`.
- §9 forbids moving a threshold after the fact; here no threshold, window, judge clause or default changes. `judge_d2` (`:91-123`) is untouched. §11.0 「與最終候選不符就作廢」 makes the 0.2.25 reports void **as D2 evidence** (they were NE anyway); they stay as finding 154's witness.
- Re-running a criterion after a product fix is the batch's normal path: §12.3 (a) fixed finding 150, then D8 ran green; §12.3 (b)/(c) fixed 151, then D11/D14 ran. What §12.4 (e) added for D7 was a **stop rule**; D2 gets one here too (condition 5 below), so this is not an open-ended "fix hosts until green".

**CONDITIONS.**

1. Before editing the tool, on the installed 0.2.26: `run_v21_d2.py --mode host --page v21 --identity-only` must print exactly one problem, `hostVersion: the host packages 0.2.26, the run needs 0.2.25`. This is the pin's red (it refuses, as designed) and the proof that only the version moved. Save as `evidence/d2/host-identity/identity-v21-on-0226-before-repin.json`.
2. The edit: `"hostVersion": "0.2.25"` → `"0.2.26"` in `HOST_EXPECT["v21"]`, and nothing else. `git diff 1fe9588d -- wasm_sdk_probe/tools/run_v21_d2.py` shows exactly that one line. Record the new `toolSha256`.
3. `run_v21_d2.py --self-test` → 19/19 (the identity cases at `:373-384` do not depend on the literal 0.2.25). `--identity-only --page v21` → `problems: []`; `--identity-only --page 0224` → refused on all four fields. Save both; commit the tool and the three identity files **before** any D2 round.
4. D2 as pinned: `--mode host --page v21`, Chrome N=3 then Firefox N=3, under the browser lock, desktop conditions of §12.4 (desktop Chrome closed, load < 1.5 at start, no foreign process > 50 %, KWallet unlocked), `preRun.refuse` empty. PASS = 6/6 `PASS` from the unchanged `judge_d2`: `move-document-start` response present, Backspace `verified-boundary-noop` with `changed false` and `rev == beforeRev`, `savedEqualsOpened true`, `controlDiffers true` (ARMS `:200-203`, tool `:104-123`). Prediction to write before the run (ARMS `:213`): `boundaryNoop.waitedMs` about 2,252–2,255, revision 0→0, text unchanged.
5. **Stop rule (pre-committed).** This is the one permitted D2 re-run on a fixed host within v21.
   - 6/6 PASS → D2 PASS.
   - Any round FAIL → D2 FAIL: product finding, 「第 1 項不出貨」, no re-run, no 0.2.27 in this batch.
   - Any round NE → 「第 1 項不出貨」, no third host version in v21. Two exceptions only: (i) an honest crash (`fatal` traceback, §34.1 (a)) → fix the crash, re-run that browser once; (ii) an NE whose cause is recorded as external in the report (`preRun`, lock holder, router 404 from another ddev project) → re-run that browser once. Neither exception applies to an NE with `clickState null` and no external cause.
   - Item 1 not shipping is not loss: it goes with v22 (order C), the host rule stays.
6. **What is written, where, before the fix is applied and before any browser starts** (§9 condition 1; §12.3/§12.4 precedent):
   - spec v21 **§12.5** (append, zh-TW): source (this ruling), finding 154, fix A and its one rule, host 0.2.26, D2's text unchanged and quoted, the one-value re-pin of `HOST_EXPECT` with the before/after identity outputs as witnesses, the acceptance reads of Q1 condition 5, the stop rule of condition 5 above, the 0.2.24 red case standing (Q5), §34.4 accounting (Q6), the default 「若這件事永遠沒做：第 1 項不出貨」; plus a revision-log row. Results appended later under the same section, as §12.4 did.
   - ARMS-item1.md (English): a dated correction appended under D2 or in a §9: "host 0.2.26 (ruling 3); the 0.2.25 run `d2-host-v21-*` is finding 154's witness, void as D2 evidence (§11.0); `:607`'s 'another shell generation' does not apply, the shell is unchanged". Do not edit `:189`.
   - shakedown README **§5.10** (English): the fix, the identity outputs, the diag reads on 0.2.26, the D2 results, the §34.4 line.
   - finding 154: a 「裁決」 section (zh-TW), the acceptance as its own criterion with the 0.2.25 reads as the red case, and the v22 work items of Q4.
   - `findings/evidence/host-0.2.25/README.md`: one appended line, "superseded by 0.2.26 (finding 154); package unchanged".
   - `findings/evidence/host-0.2.26/README.md`: the 0.2.25 shape.

### Q3. Under B or C, would the item-1 evidence stand

**RULING: No, not without a re-run; and the reason is checkable, which is why A is chosen.**

- Every item-1 report records the HTML it was built from: `pages.{v21|v21host|v21hook}.htmlSourceSha256 == 1d158149…` in 12/12 reports (and `htmlServedSha256` `9d2e18da…`, or `ae70c494…` for the Firefox D1 re-run at constant 455, both = source plus the observer snippet). ARMS-item1 §1 `:33` lists "the HTML source's sha256" among what every report records. The host package pins the same file: `MANIFEST.json` `e2-editor.html` `1d158149…`.
- Under B the shipped HTML would be some other hash. §11.0's identity list (wasm, worker, 頁面, 殼層, inputs, references) does not name the HTML, so one could *read* the reports as standing. That reading would be made after the fact to rescue evidence — the same shape as moving a criterion — and I do not grant it. The alternative, re-running every item-1 arm against the new HTML, costs the day's runs again.
- Under A the check is a one-liner, not an assertion: `MANIFEST.json["files"]["e2-editor.html"]["sha256"]` on the installed 0.2.26 == `1d158149…` == each report's `htmlSourceSha256`. Write that equality into README §5.10 with the command.

**CONDITION.** README §5.10 prints the 12 `htmlSourceSha256` values and the package's `e2-editor.html` hash side by side (python over the reports and the manifest, `-I`).

### Q4. Does 154 need a new v21 criterion

**RULING: No new §11 criterion for v21. Finding 154 (fixed in host 0.2.26, acceptance per Q1 condition 5) plus two v22 work items.**

- Apply §5's test: the mutation "the host displays a closed dialog over the editor" — does anything turn red? Yes: D2 went NE 6/6 on the user's path, and its default applied. D2 is the criterion that reads the host, and it did its job. There is no "mutation nothing turns red on" for the thing 154 is.
- A candidate criterion — "on the host, every `dialog:not([open])` and every `[hidden]` element under `#litecore-editor-root` has computed `display: none`", enumerated from the served DOM — would pass §9's four conditions in form (1: D2 not yet satisfied; 2: forced by finding 154; 3: form two, tool-closed over the DOM, not a hand list; 4: closes when D2 lands). But §9's conditions are necessary, not sufficient. §34.6 「新判準只能照第 9 條的四個條件加」 and §34.8 「也不再加…不為判讀器再寫判讀器」, and CLAUDE.md §4's self-check (writing a new mechanism → stop and report) decide it: this is a new judging tool for the host layer, which under §34.3 needs its own double review before first counted use. That is not v21's business; v21 needs D2 green on the fixed host, nothing more.
- The gap 154 shows is real but belongs to the host's production-UI criteria and to item 2's criteria when its dialog ships. Register, don't build:
  1. **v22 page hardening**: `#markdown-dialog:not([open]) { display: none }` in `e2-editor.html`, with item 2's host criteria including the closed state (display none, nothing at the click point) **and the open state** measured on the host — server.css's reset also sets `margin: 0; padding: 0; border: 0` on `dialog` (line 14), which removes the UA's `margin: auto` centering; the open dialog may sit at the top-left on the host [inferred from the CSS, not measured]. Write it into finding 154's 「下一批的判準」 as finding 153 did.
  2. **Production-UI host arm**: a DOM-enumerated read of hidden parts' computed display (form two), for the host's own next criteria round, reviewed once under §34.3 before use. Also one line, no code: `HOST_EXPECT` pins no buildId; adding a bound field needs a §34.5-type witness.
- The NE reason "no Backspace response" carried no payload about the click (CLAUDE.md §7); a separate diagnostic was needed. Register one line for v22's host-arm design (record `elementFromPoint` at the click point). Do not add it to `run_v21_d2.py` now (§34.4: no witness of a wrong verdict; §34.8).

### Q5. Does the 0.2.24 red case re-run

**RULING: No.**

- The red case's claim is about 0.2.24: host `1479e56`, buildId `d3cd39bbc71ec311`, page `901dd6a6…`, shell `e7c4eefe…`, wasm `313b08d5…` (`d2-host-0224-*.json` `static`, `identityProblems []`), red 3/3 per browser (`FAIL, "0.2.24 still red: verified-selection-delete, revision +1"`), save landed and `LD-PAGE-01 → LD-AGE-01` 6/6, control differs 6/6 (README §5.8). None of that changes.
- The tool's red branch (`judge_d2(..., red=True)`, `:104-109`), the probe (`4e92e920…`) and `HOST_EXPECT["0224"]` are byte-unchanged; the only diff is the one value in `HOST_EXPECT["v21"]` (Q2 condition 2).
- The host fix matches nothing on 0.2.24: its HTML `b1185aaa…` has zero `<dialog` (verified: `git show 3ff15b0c:…/e2-editor.html` = `b1185aaa…`, 0 matches; the dialog arrives at `bc6534e0` = `1d158149…`).
- Re-installing 0.2.24 means a downgrade of the ddev host for no information.

**CONDITIONS.** README §5.10 cites the two 0.2.24 reports by filename and `toolSha256 ce169ef8…`, and states the one-line diff. If the tool ever changes by more than that line before D2 lands, the red case re-runs (default otherwise: D2 NE, 「第 1 項不出貨」).

### Q6. §34 accounting

**RULING: None. Repaired because of execution: 0. Repaired because of review: 0. Running totals stay 28 / 18.**

- The D2 host arm's verdict (NE, "no Backspace response") was correct; its reports become finding 154's witness. No judge, probe or arm code changes. §34.4 permits a code change only with a report proving a wrong verdict; there is none, so nothing is repaired.
- The `HOST_EXPECT` version is a re-pin following the product version, the class the project already does not count (`SPEC-M3-link-batch.md:535`; handoff 10-17b `:113`). List it in the handoff under "Not counted", with its witnesses (the before/after `--identity-only` outputs of Q2 conditions 1 and 3).
- `diag_markdown_dialog_on_host.py` is a diagnostic, not a check: 0. The host rule is a product change: 0.
- Registered as one line each, no code (§34.4 「否則只登錄一行」): the NE reason without payload; `HOST_EXPECT` pins no buildId.

### Q7. What is wrong or needs a nuance in the brief

1. **F7, "the item-1 evidence runs served `e2-editor.html` `1d158149…`"** — the *served* HTML was `9d2e18da…` (11 reports) and `ae70c494…` (the Firefox D1 re-run); `1d158149…` is `htmlSourceSha256`, the source before the observer is inserted. The substance (source HTML = the package's) holds, and it is checkable, not asserted (Q3).
2. **F7 omits** that `HOST_EXPECT` pins no buildId (`:62-71`, four keys): under B, a new package with the same page/shell/wasm would pass the identity check. Under A, moot; register it.
3. **F2's `:607` quote** is D-1 **option A's** text; the ruling was B (`:713`). Its inference "another shell generation" does not follow for a host-layer NE: under fix A no JS changes, v74 stays frozen. It must not be read as requiring v75.
4. **"Other" option (remove the markup)** — now checked: `e2-editor-app.js:2399-2404` would throw at module load; the option needs a JS change and voids the page hash. Out.
5. **F4** — Chrome box 640×335, Firefox 640×330; both read block / TEXTAREA. Minor.
6. **F5** adds nothing wrong; one more harmless fact: 「取消」 also clears the textarea (`:2359`). The `cancel` event (`:2400`) never fires for a non-open dialog, so Escape does nothing on the host.
7. **F3** holds in detail: `fullLog` per round has `kd Home` (ctrl true) and `kd Backspace`, 14 `rq` all `paint`/`pageRectangles`, no `editorAction`/`move-document-*`; `save1`/`save2` `timedOut true`.
8. Nothing else in the brief is wrong. The brief's "host app is Nextcloud 34.0.2" holds (`version.php`).

---

## 3. F-claims checked

| claim | status | how |
|---|---|---|
| F1 criterion text, form, default 「同上」=「第 1 項不出貨」; §11.0 NE = not done; revision log `:531` | **verified** | spec `:352-353`, §11.0 second bullet, `:531` |
| F2 ARMS `:189`, `:607`; spec `:27`; `HOST_EXPECT` `:62-71` four fields; mismatch refuses | **verified**, with nuance Q7-3 | ARMS, spec, `run_v21_d2.py:62-71, :221-230, :247-253` |
| F3 6/6 NE, `clickState null`, keydowns without requests, saves time out, reason "no Backspace response", tool `ce169ef8` = `1fe9588d` | **verified** | python over both `d2-host-v21-*.json`; `git show 1fe9588d:… \| sha256sum` |
| F4 dialog added in part S `bc6534e0`; display block on host; server.css reset; host wraps body as is; covers click point, `TEXTAREA#markdown-text`; counterfactual rule → `CANVAS#canvas` + `editorPlaceCaretV2`; button hidden | **verified** | `git log -- e2-editor.html`; `diag-154-*.json` `asShipped`/`withRule`; `server.css` line 14; `EditorController.php:145-185`; `templates/editor.php:73-76` |
| F5 「插入」 returns at once; 「取消」 cannot hide; focuses sink | **verified** (source) | `e2-editor-app.js:2357-2364, :2372-2375` |
| F6 all runs no-host; `v21host` fake host; E0 reads only the button (README `:183`); 0.2.24 has no dialog | **verified** | README `:183`, §5.2; ARMS D-2; `git show 3ff15b0c:…` 0 `<dialog`, = `b1185aaa` = 0.2.24 package's |
| F7 HTML not in v74 bundle; in engine package and buildId; merge BINDING `htmlSha256` `b1185aaa` `:172`; item-1 runs' HTML `1d158149` | **verified**, with nuance Q7-1/2 | bundle `included` 13 JS paths; `MANIFEST.json` 22 files; `package_m3_engine.py:109-112`; `run_merge_wasm_shakedown.py:172`; 12 reports |
| F8 `templates/editor.php:31-50` hides shipped parts | **verified** | file `:31-50`, and `:71` `#page-status[hidden]` |
| Context: v74 `4628c9d3`; host `03970d0` = info.xml only; §5.8 red 6/6; §5.9 NE 6/6 | **verified** | `git log`; `git show --stat 03970d0`; `d2-host-0224-*.json` |
| Context: item-1 `VERDICT PASS` both browsers | **verified in part** | per-criterion PASS rows read in `judge-item1-after-d7-rerun-2.txt`; the VERDICT line is cited by spec §12.4 and README `:175`, not re-read to its end |
| "the owner's other hosts or embedders" | **not checked** (no source in the tree) | any embedder with the same reset hits it [inferred]; v22 page hardening closes it for all |

---

## 4. What the main session does next, in order

0. Commit this reply verbatim as `review/ruling-fable-3.md`; recompute the numbers above before adopting (12/12 `htmlSourceSha256`; the `fullLog` shape; the diag reads).
1. **Append, before any host edit or browser start**: spec v21 §12.5 + revision-log row; ARMS-item1 correction; README §5.10 header with the pre-registered acceptance reads, the prediction and the stop rule; finding 154 「裁決」 with the acceptance criterion, its 0.2.25 red case and the two v22 work items (Q4). Commit. *Default if skipped: the run has no pinned criterion in front of it; treat anything measured as diagnostic, not evidence.*
2. **Host 0.2.26** (host repo): the one rule in the host's own `<style>` block with its comment (Q1 conditions 1–2); `info.xml` 0.2.26; one commit. Owner: `ddev occ upgrade`. Then Q1 condition 4 (MANIFEST sha, `check_engine_decoded.py`, `http_served_page.py`, address unchanged), filed under `findings/evidence/host-0.2.26/`. *Default if the package hash differs: stop; the package was rebuilt; do not run D2.*
3. **Pin red on 0.2.26**: `--identity-only --page v21` with the tool unchanged → exactly the `hostVersion` problem (Q2 condition 1). Save.
4. **Fix acceptance**: the unchanged diag tool, Chrome and Firefox, on 0.2.26 (Q1 condition 5). *Default if any read fails: stop, do not touch the tool, do not run D2; report.*
5. **Re-pin**: the one value; `git diff 1fe9588d` one line; `--self-test` 19/19; `--identity-only` v21 `[]` and 0224 refused on four fields. Commit tool + identity files.
6. **D2 as pinned**: Chrome N=3, Firefox N=3, lock, desktop conditions (Q2 condition 4). Read with the unchanged judge. Apply the stop rule (Q2 condition 5). *Default if never run: 「第 1 項不出貨」.*
7. **Append results**: README §5.10 (incl. the 12-report HTML equality, the 0.2.24 red case citation and one-line diff), spec §12.5 結果, finding 154, `host-0.2.25/README.md` one line, handoff with §34.4 **0 / 0**, totals 28 / 18, "Not counted: `HOST_EXPECT` re-pin (witnesses: before/after identity outputs); diag tool; host rule", and the two registered one-liners (NE without payload; no buildId pin).
8. Then handoff 10-17b "Next" 4 onward (re-pin values now name host **0.2.26** and commit; `BINDING` in its own commit; count chain by the owner; 0.2.26 release text carries finding 154 as fixed in the host and the v22 page hardening as pending; v22 = stack relink + item 2 + page rule, order C).

---

## Main session's pre-adoption check (2026-10-17; not part of the ruling)

Recomputed with `python3 -I` over the files before adopting:
- the 12 item-1 reports: every `pages.v21*.htmlSourceSha256` is `1d158149…` (12/12, as the ruling says); the installed `engine/MANIFEST.json` sha256 is `54bebc4de343526b…` and its `e2-editor.html` is `1d158149…`;
- the six `d2-host-v21-*` rounds: 14 requests each, all `paint`/`pageRectangles`; `save1` and `save2` `timedOut` in all six;
- the diag tool's sha256 is `757c44766d44445b…`; `git show 3ff15b0c:wasm_sdk_probe/web/e2-editor.html` has 0 `<dialog`.
- One small difference: counting page entries, `htmlServedSha256` reads `9d2e18da…` 10 times, `08e08ec4…` and `f57e8534…` twice each (the v21host and v21hook variants), and `ae70c494…` once. The ruling's "9d2e18da… (11 reports)" does not match that count. Its point, that the served hashes are the source plus the observer snippets, stands, and nothing in the ruling depends on the count.

---

**Ruling 3, addendum 1 (fix acceptance on host 0.2.26: the `withRule` Chrome read), fable, 2026-10-17, read-only.**

Basis. Read: `findings/evidence/154/diag_markdown_dialog_on_host.py` (sha `757c4476…`, whole file; `measure()` `:69-83`, `main()` `:86-130`); `wasm_sdk_probe/tools/check_m3_production_ui.py:261-272` (`state`, `until`); `findings/evidence/host-0.2.20-hand-test/probe_10_14n.py:39-100` (`INSTRUMENT`), `:236-246` (`LOG_LENGTH`, `log_from`); `wasm_sdk_probe/web/e2-editor-app.js:2112-2131` (`run()`), `:2673-2688` (the `pointerdown` handler), `:958`, `:987` (state pill and pending writers); `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js:741-800` (`placeCaret`); `narrow-editor-v2-client.js:503-506`. Ran `python3 -I` over the four diag reports (`154/0226/diag-154-{chrome-20261017T181633,firefox-20261017T181647}.json`, `154/diag-154-{chrome-20261017T170402,firefox-20261017T170449}.json`). `git log` to `fd72505b`. No browser, no ddev, no edits.

---

### 裁決（給擁有者）

**修法的驗收算過了。** 兩個瀏覽器在 0.2.26 上「照出貨的頁面」那一臂每一項都讀到預期值：關著的對話框不顯示、宿主那條規則在清單裡、點擊點底下是畫布、點下去真的送出 `editorPlaceCaretV2`。Chrome 第二臂少掉的那一筆，是**量具自己的問題**，不是產品：第二次點擊時，狀態列上還留著第一次點擊的「定位游標 45 ms」，量具一看到這四個字就以為完成了，立刻去讀紀錄，而頁面這時才剛開始處理第二次點擊（報告自己寫著 `busy`、待處理 1）——Firefox 只是跑得剛好快一點。這一臂在 0.2.25 上之所以乾淨，是因為那時第一次點擊打在對話框上、根本沒寫過這四個字。我當初寫「第二臂也要讀到一樣」時沒看量具的這個前提，是我寫錯，主 session 停下來是對的。處置：**撤掉那一句**（前提不成立），登錄成量具的具名極限；**不改量具、不重跑**——沒改的量具再跑一次只是擲銅板，改了量具才跑等於為一個在 0.2.26 上已經沒東西可量的臂造機械。接下來照裁決 3 走：改那一個版號、自測、身分檢查、commit，然後跑 D2。

---

### Q1. Met, not met, or not established

**RULING: The acceptance (spec §12.5 (c) / ruling 3 Q1 condition 5) is MET, on the branch that measures it.** The `withRule` Chrome `placeCaretRequests []` is **not a product red and not a failed acceptance read**: it is a read taken before the request existed, by an instrument whose completion predicate is satisfied by the previous click's label. The clause "the `withRule` branch … must read the same" is **withdrawn for 0.2.26** under CLAUDE.md §4 (its premise is false by construction), with the reason below; it is not moved, weakened or re-interpreted.

**FACT CHECK (the mechanism, from source, not from the brief's inference).**

1. The label is never cleared at the start of an action. `run()` writes `#s-latency` only on completion (`e2-editor-app.js:2121`, `${label} ${ms} ms`) or on failure (`:2127`, `:2131`). After the first click it reads `定位游標 45 ms` (Chrome) / `28 ms` (Firefox) until the second click's `run()` completes. [verified]
2. `ui.until` returns the first polled state the predicate accepts; it has no "changed since the click" clause (`check_m3_production_ui.py:265-272`). With the label already containing `定位游標`, the first poll after `real_click` returns at once. [verified]
3. `measure()` then reads the log immediately (`diag_markdown_dialog_on_host.py:79-81`: `until(...)`, then `log_from(start)` filtered to `k == "rq"` with `"PlaceCaret" in op`). No settle, no second read. [verified]
4. The page's click path posts two requests in sequence: `session.placeCaret` (`pointerdown`, `e2-editor-app.js:2685`) is `_enqueue("place-caret", …)` whose body first `await editor.getState(options)` (`narrow-editor-v2-session.js:743`) and only then calls `editor.placeCaret(...)` (`:772-778`). The instrument logs `rq` at `Worker.prototype.postMessage` (`probe_10_14n.py:67-75`), so the `editorPlaceCaretV2` entry exists only after the `editorGetStateV2` round trip has returned. An immediate read sees at most the getState request, which the filter drops. [verified]
5. The reports carry the payload that says so: both browsers' `withRule.clickState` read `state "busy"`, `pending "1"` — the queued place-caret in flight at the read — against `ready` / `0` in every `asShipped` read and in both 0.2.25 `withRule` reads. Firefox's read happened to fall after its getState round trip (`['editorPlaceCaretV2']` logged); Chrome's fell before. [verified from the four JSONs]
6. Why 0.2.25's `withRule` was clean: its `asShipped` click landed on `TEXTAREA#markdown-text` and never wrote the label (`asShipped.clickState null`), so the second click's `until` waited for the real completion (`state ready`, `pending 0`, `latency 定位游標 37/36 ms`). The branch was clean there **because the fix was absent**, not because the predicate is sound. [verified]
7. The falsified premise of my clause: "the `withRule` branch reads a second click cleanly". From 1–4 it reads cleanly only when the first click set no label, i.e. only when the fix is absent. On a fixed host the branch is a race by construction; it is not a threshold that can be tuned. §4 applies: delete the clause, do not build machinery to keep it true. My condition 5 was written without reading the tool's predicate; that is the drafter's error (CLAUDE.md §11), and the main session's stop under §12.5 (c) was correct.
8. The acceptance's substance is measured by the first-click branch, which is exactly the branch whose red case is committed (0.2.25 `asShipped`: `display block`, `TEXTAREA#markdown-text`, `placeCaretRequests []`, `clickState null`). On 0.2.26 that branch reads, in **both** browsers: `dialog.open false`, `display "none"`, `box [0,0,0,0]`, `rulesSettingDisplay` containing `inline` / `#litecore-editor-root dialog:not([open])` / `none`, `elementAtPoint CANVAS#canvas` `insideDialog false`, `placeCaretRequests ['editorPlaceCaretV2']`, `clickState.state "ready"`, `latency 定位游標 45 ms` / `28 ms`, `button.hidden true` / `display "none"`, `hostIdentity.hostVersion "0.2.26"`, `buildId f5f0df762e1855f2`, tool `757c4476…`. Every pre-registered read holds. [verified from `154/0226/*.json`]
9. No v21 criterion claims anything about a **second** click at the same point on a collapsed selection: D1's 38 arms, D4's `r-*`, D2's host arm each click once on a fresh page. D2's own click predicate (`probe_10_14n.py:364`) is the same label predicate, but runs on a page where no `定位游標` label exists yet, so it is clean by construction. The second-click behaviour is **not measured and not claimed**; register it as such.

### Q2. What may be done

- **Re-run the unchanged tool: REFUSED.** The second branch is a race on any fixed host (fact 7); a passing re-run would be a coin flip presented as a measurement, the "re-run until green" that rulings 2 and 3 forbid. It would also not test the fix: the first branch already did.
- **Accept the `asShipped` branch as the acceptance: YES — this is the ruling.** With the clause withdrawn under §4 and the premise written down. The `withRule` branch on 0.2.26 is **recorded, not judged** (both reports kept as they are; nothing moved to `superseded/`).
- **Change the tool: NOT NOW.** §34.4's witness exists (the committed Chrome 0226 report shows the read taken at `busy`/`pending 1`), so a repair would be *permitted*; it is not *ordered*, because on 0.2.26 the branch has no counterfactual left to measure (the page rule is redundant to the host rule) — fixing a predicate so that a redundant branch turns green is machinery for a claim already withdrawn (§4 self-check). If v22's host criteria reuse the counterfactual shape, fix `measure()` then (wait for `state == "ready"` and `pending == "0"` after the click, or for the label to change, before reading the log), count it then as "repaired because of execution +1", with `154/0226/diag-154-chrome-20261017T181633.json` as its red case. Named limit now: **L-154-diag-second-click** — "the diag tool's second click reads the log as soon as the latency label contains 定位游標; when the first click already set that label the read precedes the request, so only the first click's read is clean".
- **§34.4 this step: 0 / 0**, totals unchanged (28 / 18). One registered line, no code (L-154-diag-second-click).

### Q3. What is appended before proceeding (append-only, §10; before the re-pin and before any D2 round)

1. **spec v21 §12.5 (c′)** (zh-TW): the 0.2.26 reads of fact 8 for both browsers, verbatim, with the report paths `findings/evidence/154/0226/diag-154-{chrome-20261017T181633,firefox-20261017T181647}.json` (the `0226/` subdirectory, chosen so the 0.2.25 screenshots are kept — this supersedes the file-name pattern in ruling 3 Q1 condition 5); the withdrawal of the `withRule` clause with the falsified premise (fact 7) and the mechanism (facts 1–5, with the file:line); L-154-diag-second-click; the sentence "the second-click behaviour is not measured and not claimed by any v21 criterion"; the acceptance verdict **met**; the default unchanged (「若 asShipped 任一項未讀到：停，不改工具，不跑 D2」, which did not trigger). Revision-log row.
2. **README §5.10** (English): the same facts and paths; the §34.4 line (0 / 0; "a witness exists, the tool is not changed because the clause is withdrawn, not repaired"); the one registered line; the note that D2's own click predicate is clean by construction (fact 9).
3. **finding 154 「裁決」 addendum** (zh-TW): fix accepted on host 0.2.26, both browsers; the instrument limit and the v22 note on `measure()`.
4. Commit 1–3 together with this addendum appended verbatim to `review/ruling-fable-3.md`.
5. Then ruling 3 Q2 conditions **2 → 6** unchanged: the one-value re-pin (`git diff 1fe9588d` exactly one line), `--self-test` 19/19, `--identity-only` v21 `[]` and 0224 refused on four fields, commit; D2 Chrome N=3, Firefox N=3 under the lock and §12.4 desktop conditions; the stop rule of ruling 3 Q2 condition 5 governs the outcome.

**Default if 1–4 are not done:** the acceptance is not on record as met; do not re-pin, do not run D2; 「第 1 項不出貨」 stands. **Default if D2 is never run:** the same.

---

Main session's check of addendum 1 (not part of the ruling): recomputed from the four reports — 0.2.26 `withRule.clickState` is `busy` / pending `1` in both browsers, `asShipped` `ready` / `0`; 0.2.25 `withRule` `ready` / `0`. `e2-editor-app.js:2121` writes the latency label at completion; `narrow-editor-v2-session.js:743` awaits `getState` before `placeCaret` (`:772-778`). Agrees.
