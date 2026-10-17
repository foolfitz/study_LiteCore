# Ruling request 3 (v21): finding 154 makes D2 NOT_ESTABLISHED on host 0.2.25. Which fix, and what does D2 then run on?

**You decide this question.** The owner chose to send it to fable (2026-10-17, option 「D 交給 fable」 among A host fix / B page fix / C both / D fable). Work read-only: read files, run read-only Python over the reports, but start no browser, touch no ddev, edit nothing and commit nothing. The main session commits your reply verbatim as `review/ruling-fable-3.md`, checks your numbers, and carries out what you order.

Repo: `/home/jiajun/LibreOffice/study_LiteCore`. Read `CLAUDE.md` 「驗收判準的形式」 §1–§11 first; §4 (withdraw, don't build machinery), §6, §8 and §9 (adding versus moving) bear on this. The host app is a separate repo: `/home/jiajun/Projects/Nextcloud_Apps/litecore` (Nextcloud 34.0.2 core under `nextcloud/`).

## Where v21 stands (context)

- v21 ships **item 1 only** (Ctrl/Cmd+Home/End, finding 142). Item 2 (Markdown paste) is withheld by fable ruling 1 (finding 153); spec §12.3 (e) (`specs/SPEC-M3-link-batch-v21.md:469`): 「殼層不提供入口：工具列按鈕與任何通往 `openMarkdownDialog` 的路 … 都不出現」.
- Item-1 evidence (all no-host mirrors): judge `VERDICT PASS` in both browsers (`evidence/judge-item1-after-d7-rerun-2.txt`). Shell v74 frozen (`4628c9d3`). Not bound, not counted.
- Today (handoff 10-17b "Next" 1–3): D2's 0.2.24 red case ran on the host, red 6/6 as required (README §5.8, `b6a92bbe`). Host 0.2.25 was packaged and installed (`findings/evidence/host-0.2.25/README.md`, `ac949ad3`; host commit `03970d0`). D2 then ran on it: **NOT_ESTABLISHED 6/6** (README §5.9, `1e3dae22`).

## F-claims (check each)

- **F1. The criterion.** Spec §11.1 `:353`: 「`press-after-ctrl-home`（宿主）：Backspace 以 `verified-boundary-noop` 完成，revision 不變，存檔文字不變。0.2.24 上照舊是紅的」, form 逐實例, default 「同上」 = 「第 1 項不出貨」. §11.0: NE counts as not done. Revision log `:531`: criteria pinned at `523871fa`, 「之後只准追加更正，不得移動」.
- **F2. Where D2 runs.** ARMS-item1.md `:189`: 「(b), host 0.2.25, after the v74 freeze, Chrome and Firefox, N=3」. `:607`: 「If D2 is red, the §11 default (no binding) means another shell generation and another host version [inferred]」. Spec `:27`: 「新宿主版本（0.2.25 起）」. The tool pins the version: `wasm_sdk_probe/tools/run_v21_d2.py:62-71` `HOST_EXPECT["v21"]["hostVersion"] = "0.2.25"`, together with page `605cf24b…`, S-1 shell digest `e35923a0…`, wasm `db3408f5…`. A mismatch refuses the run.
- **F3. The NE.** `evidence/d2/d2-host-v21-{chrome-20261017T163844,firefox-20261017T165106}.json`: in all 6 rounds the first-line click got no `editorPlaceCaretV2` within 40 s (`clickState` null). Ctrl+Home and Backspace then show as keydowns and send no request, and both saves time out. The judge's reason is 「no Backspace response」. Tool `ce169ef8…` (= `1fe9588d`), unchanged since the red case passed through it.
- **F4. The cause** (finding 154, `findings/154-…md`; diagnostic `findings/evidence/154/`, both browsers):
  - `<dialog id="markdown-dialog">`, added to `wasm_sdk_probe/web/e2-editor.html` by v21 part S (`bc6534e0`), is closed; its computed `display` on the host is **block**.
  - The rule is Nextcloud's `core/css/server.css` reset `article, aside, dialog, figure, footer, header, hgroup, nav, section { display: block }`, an author style that beats the user agent's `dialog:not([open]) { display: none }`. The host puts the page's body inside `#litecore-editor-root` as is (`lib/Controller/EditorController.php:145-185`, `templates/editor.php`).
  - The dialog (absolute, 640×335 at 8,50) covers the click point; `elementFromPoint` gives `TEXTAREA#markdown-text`.
  - **Counterfactual on the same page:** adding one rule `#markdown-dialog:not([open]) { display: none }` gives `CANVAS#canvas` at the point, and the click sends `editorPlaceCaretV2`. Screenshots: `as-shipped-chrome.png`, `with-rule-chrome.png`.
  - The entry button `button[data-action="paste-markdown"]` stays `hidden` / `display: none` on the host.
- **F5. What the visible dialog can do** [source, not measured]: 「插入」 returns at once (`e2-editor-app.js` `insertMarkdownFromDialog`, `if (!PASTE_MARKDOWN_ENTRY_SHIPS) return;`), so item 2's engine path (finding 153) is not reachable through it. 「取消」 calls `closeMarkdownDialog`, which calls `close()` only `if (el.markdownDialog.open)`, so it cannot hide the dialog; it does focus the input sink.
- **F6. Why no earlier run saw it.** Every v21 evidence run was no-host. `v21host` (D11a's variant) is a mirror with a fake `liteCoreHost`, with no Nextcloud page or CSS. E0 (README `:183`) reads only the entry button. 0.2.24 has no dialog.
- **F7. What pins `e2-editor.html`.** It is not in the v74 shell bundle (JS modules only, `wasm_sdk_probe/e2/editor-shell-v2-bundle-v74.json` "scope"), so S-1 and `HOST_EXPECT` do not see it. The host's engine package does: buildId `f5f0df762e1855f2` is over every packaged file, `e2-editor.html` included. The merge runner's BINDING pins `htmlSha256` `b1185aaa…` (v20's; `run_merge_wasm_shakedown.py:172`), which handoff step 4 (re-pin) moves anyway. The item-1 evidence runs served `e2-editor.html` `1d158149…` (the tree's).
- **F8. Host precedent.** `templates/editor.php:31-50` already hides shipped page parts with `#litecore-editor-root … { display: none; }` (SPEC-M3-production-ui), so a host rule hiding a closed dialog matches what the host already does.

## The options the owner was shown

- **A, host fix:** add `#litecore-editor-root dialog:not([open]) { display: none }` to `templates/editor.php`, host 0.2.26. Engine package, page, HTML and shell unchanged (buildId stays `f5f0df76…`). Re-run D2 on 0.2.26 with `HOST_EXPECT["v21"]["hostVersion"]` 0.2.25 → 0.2.26. Page-side hardening rides with v22, where item 2's dialog ships.
- **B, page fix:** add `#markdown-dialog:not([open]) { display: none }` to `e2-editor.html`; new engine package and buildId, host 0.2.26. Safe in any host, but the item-1 evidence served a different HTML than the one that would ship.
- **C, both now.**
- The main session leans A, for the reasons in F7 and F8. It has not checked whether the owner's other hosts or embedders exist. Other options are welcome, for example taking the dialog markup out of v21's HTML (the page's `el.markdownDialog` and related lookups at `e2-editor-app.js:179-181` would then be null; not checked).

## Questions

1. Which fix (A, B, C or other)? In plain words for the owner, and with the conditions the fix must meet before D2 re-runs (for example a red-first check that would have caught 154).
2. Is D2 re-run on the fixed host **the criterion as pinned**, with only the host version changed? Or is changing `HOST_EXPECT`'s version moving a criterion (§9 / revision log `:531`)? What must be written, and where (spec append, ARMS, README)?
3. Under B or C: do the item-1 evidence runs (HTML `1d158149…`) still stand, and what makes that checkable rather than asserted (§8)?
4. Does 154 show a gap that a **new** criterion must close for v21 (for example a host arm reading every shipped-but-hidden element's computed display), or is it a finding plus a v22 work item? If a criterion, check it against §9's four conditions and §1's forms (a list of "hidden elements" written by hand is a manual enumeration).
5. The 0.2.24 red case already ran (red 6/6). Does it need to run again after the fix?
6. §34 accounting: is any of this a repair because of execution (the tool's `HOST_EXPECT` pin), or none?
7. Anything in this brief that is wrong (as F6 was in brief 2). Name it.
