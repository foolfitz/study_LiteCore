# Host 0.2.21: finding 141 fixed on the page, finding 143 fixed in the host template (task 10-14o)

Task: `handoff/tasks/TASK-2026-10-14o-fix-141-and-143-for-host-0.2.21.md` (criteria K1–K4 pinned there before any run). The owner chose A after the 10-14n diagnosis (`findings/evidence/host-0.2.20-hand-test/`); for 143 the owner ruled that the page number's appearance follows Collabora's (a bottom status bar, the number its leftmost item). Rulings on the owner's behalf: appended 裁決 sections in `findings/141-…md` and `findings/143-…md` (zh-TW). English here. The freeze (v70), the re-pins, the packaging, the host version bump and commit, and `occ upgrade` are the main session's and were not done; no link, no `--write`, the only make `e2-c-assets`.

## Part 1 — finding 141, the page (`wasm_sdk_probe/web/e2-editor-app.js`)

**Design.** The delete listener (`beforeinput` → `delete-backward`/`delete-forward`) holds a press of a key whose delete is out and **not yet answered by the engine** (new counter `deletesUnanswered`, distinct from `deletesInFlight`, which spans the repaint `run()` awaits); the press is counted in `heldDeletes`, not queued. The engine's answer decides (`settleDelete`, reached through a new `onResult` hook on `editorAction` that fires at the engine's reply, before the repaint): a `verified-boundary-noop` with `changed: false`, the revision unchanged and the returned caret/selection equal to the state the delete was sent from (`boundaryNoopStands`) **drops** the held presses — their answer is known; anything else (a real delete, a refusal, a state that moved, no readable state) **re-delivers one held press** as a `beforeinput` on the sink (`releaseHeldDelete`), so the same listener sends it and finding 131's press-for-press rule stands for real deletes, one answered-and-repainting while the next is already out (132's depth); a refusal drops the rest (134 B). The frozen input adapter ignores delete input types (`input/input-adapter.js`, "ignored-input-type"), so the re-delivered event reaches only this listener. H2 (`dropsHeldRepeat`, keydown, `repeat === true` at depth 2) is untouched. Fail-closed towards 131: when the answer cannot be read as a standing no-op, the presses go out. Named limit: a K1 landing after the reply (L-C-late-K1) is not seen. The page's `editor-shell-v2/` and `editor-shell/` are unchanged (E1-C intact).

Why this shape: it does not depend on `event.repeat` (the owner's input path — KDE Wayland, fcitx5 as KWin's IM, Firefox a Wayland client — was not measured; see 10-14n), it does not drop presses that could change the document (131), and it needs no link; the engine-side answer-at-the-boundary (§10.5's `waitedMs`) stays a next-link-batch item that would remove the first press's 2.25 s as well.

**Bytes.** `web/e2-editor-app.js` sha256 `53019168651b6b46…` → **`2d6c4580e8beaac7…`**; `dist/e2-editor-app.js` is the same after `make e2-c-assets` (`cp`). `web/e2-editor.html` `b1185aaa…` and `editor-shell-v2/narrow-editor-v2-session.js` `f47c80ec…` unchanged. Two existing tests in `editor-shell-v2/tests/page-delete-and-sink.test.mjs` were adapted to the new handler shape with their clauses kept (132 U6's harness carries the held-delete state and a dispatching sink, its scenario reads "one out, one held, the held one goes out at the first answer, one repaint once all settled"; 134 U-B4's text pin points at the new call shape, the flag still set on the same promise's rejection). New: `editor-shell-v2/tests/page-held-deletes.test.mjs`.

### K1 — unit (red first on today's bytes, then green) — `k1/`

| test | today's page `53019168…` (`PAGE_SOURCE=`, `held-deletes-old-page-53019168.tap`) | the changed page (`held-deletes-new-page.tap`) |
|---|---|---|
| T1: 18 unflagged presses in 1 s at a C boundary, fake engine answering the no-op at 2,250 ms | **red**: `expected 1, actual 18` requests | green: 1 request, `deletesInFlight` 0 and nothing held at 2.5 s, one repaint, still 1 request at 45 s |
| T2 (control, 131): the same 18 presses inside text | 18 requests (red only on the new throughput clause: nothing is held there) | green: 18 requests, revision +18, each held press out at the previous answer, 17 held |
| T3a (control): a press after the caret moved | red (3 requests for 3 presses) | green: 1, then the moved-caret press makes 2 |
| T3b / T3c (controls): a no-op whose state differs / without a state releases the held presses | green | green (3 requests for 3 presses) |
| T3d: a refusal drops the held presses, hold marked refused | red (3 requests) | green (1 request, `deleteRefusedThisHold` true) |
| T3e: a Delete while a Backspace is unanswered is another key, not held | green | green |
| T4: flagged repeats obey H2 at the keydown | green | green |
| T5: `node --test editor-shell-v2/tests/*.test.mjs` | — | **360 / 360** (352 before + 8), `suite.tap`; `check_e1_c_bundle_intact.py` **`intact: true`** (`e1c-intact.json`) |

The fake engine answers one action at a time, as the session's queue does, on mocked time (`mock.timers`); the harness compiles the listener and its helpers from the page source (`PAGE_SOURCE` selects the copy), so the red run is the same test on the shipped bytes.

### K2 — no host, both browsers — `k2-nohost-v20/`

The dist mirror (symlinks to `dist/`, the changed page, profile `e2-editor-v20`, served by `web/serve.py`), the 60-page fixture opened through the page's file input, the 10-14n probe's `burst-1s` arm (18 keydowns as release/press pairs within 1 s, `repeat: false`) at the document start after a real click on the first line and Home, and the new control arm `burst-1s-in-text` (the same burst after a real click inside the text of page 1). Judge: `judge_k.py --k2 k2-nohost-v20` (`k2-judge.txt`); its self-test reads the 10-14n no-host report red on (a) and (b).

| arm | Firefox 157 | Chrome 151 |
|---|---|---|
| `burst-1s` at the document start (18 keydowns, 18 `beforeinput`) | (a) **1** engine delete request, 1 answer (`verified-boundary-noop`, `waitedMs 2253`); (b) ready at **2,260.1 ms**; (c) generation `['1']`, revision 0 → 0, no toast — PASS | (a) **1** / 1 (`waitedMs 2256`); (b) **2,259.4 ms**; (c) `['1']`, 0 → 0, no toast — PASS |
| `burst-1s-in-text` (control; the same burst with the caret inside page 1's text) | 18 requests, 18 `verified-selection-delete`, revision 0 → **18**, the last ready at 1,320 ms (the instrument counts 34 `beforeinput`: the 18 presses plus the 16 held presses re-delivered through the sink) — PASS | 18 / 18, 0 → **18**, last ready at 1,330 ms, 34 `beforeinput` — PASS |

Before this change the same `burst-1s` on the same mirror read 18 requests and 40,617.5 ms (`host-0.2.20-hand-test/nohost-v20-firefox-owner16630/`), which is what the judge's self-test reads red. The served page in both reports: `2d6c4580e8beaac7…`, session `f47c80ec…`, profile `e2-editor-v20`.

## Part 2 — finding 143, the host (`~/Projects/Nextcloud_Apps/litecore/templates/editor.php`, uncommitted)

**Design (the owner's ruling: Collabora's appearance).** CSS only, over the page's existing `#page-status`; page and shell bytes untouched for 143. (1) The editor root no longer overflows Nextcloud's content box: its inline `height: calc(100vh - 50px)` becomes `height: 100%` (`#content` is already `--body-height` = 100vh − 50 − 8 px, `overflow: clip`, radius 16 px). (2) `#page-status` becomes the editor's status bar: `#litecore-editor-root #page-status { display: flex; align-items: center; width: 100%; min-height: 32px; padding: 0 12px; font-size: 13px; color: var(--color-main-text); background: var(--color-main-background); border-top: 1px solid var(--color-border); }`, plus `[hidden] { display: none; }` because the page deliberately sets no `display` so that `hidden` works. Two ids beat the page's `#page-status` inside `@scope`; the pre-146 Firefox unscoped fallback gets the same rules. Result: the root's full width along its bottom edge, inside `#content`, 32 px tall, the page number its leftmost text in the host's size and colour — Collabora's bar position and look (`cool-26-04`: bottom, full width, `StatePageNumber` leftmost). Not in this release, named for later: Collabora's badge around the number (needs a span in the page markup; CSS alone cannot frame the text) and the click that opens Go to Page (an action, or a page-side scroll to the rectangle).

**The diff** (`editor.php.diff`, the host tree otherwise clean at `2ff30b5`; this file is live on the owner's instance since it was saved):

```diff
diff --git a/templates/editor.php b/templates/editor.php
index 4bcbd60..4a0760a 100644
--- a/templates/editor.php
+++ b/templates/editor.php
@@ -49,8 +49,28 @@
 #litecore-editor-root #text,
 #litecore-editor-root [data-action="insert-text"],
 #litecore-editor-root .statusbar { display: none; }
+/* Finding 143 (host 0.2.21; the owner's ruling of 2026-10-14: the page number
+   looks like Collabora's). The page's own #page-status is 12 px muted text in
+   a 27 px strip, and with .statusbar hidden it was the root's last strip --
+   8 px of which sat under #content's clip (the root was calc(100vh - 50px),
+   #content is --body-height = 100vh - 50px - 8px). Here it is the editor's
+   status bar: the root's full width along its bottom edge, inside #content,
+   32 px tall, the page number its leftmost text in the host's own text size
+   and colour. `display` is set, so `hidden` is restated: the page hides the
+   element until the first page-rectangle answer and while no document is open.
+   Collabora draws the number as a badge and opens Go to Page on click; the
+   badge needs a span in the page markup and the click an action -- neither is
+   in this release (study_LiteCore findings/143, 裁決). */
+#litecore-editor-root #page-status {
+	display: flex; align-items: center; box-sizing: border-box;
+	width: 100%; min-height: 32px; padding: 0 12px; margin: 0;
+	font-size: 13px; line-height: 1.5; text-align: left;
+	color: var(--color-main-text); background: var(--color-main-background);
+	border-top: 1px solid var(--color-border);
+}
+#litecore-editor-root #page-status[hidden] { display: none; }
 </style>
-<div id="litecore-editor-root" style="display: flex; flex-direction: column; height: calc(100vh - 50px); width: 100%;">
+<div id="litecore-editor-root" style="display: flex; flex-direction: column; height: 100%; width: 100%;">
 <div id="litecore-host-bar" role="status" hidden><span id="litecore-host-notice"></span><button type="button" id="litecore-host-download" hidden>下載這份內容</button></div>
 <?php print_unescaped($_['body']); ?>
 </div>
```

### K4 — the current host (0.2.20 bytes + this template), both browsers — `k4-host-css/`

The 10-14n probe's `page-number` arm on the 60-page fixture (Files → open, 18 real wheel steps). Judge: `judge_k.py --k4 k4-host-css` (`k4-judge.txt`); its self-test reads the 10-14n host report red on (d), (e) and (g).

| clause | Firefox 157 (viewport 1850×994) | Chrome 151 (1850×980) |
|---|---|---|
| (d) text bottom ≤ `#content` bottom | **980.5 ≤ 986** PASS (10-14n: 990 > 986) | **965.8 ≤ 972** PASS |
| (e) font ≥ 13 px, contrast ≥ 4.5:1 | **13 px, 15.91:1** (`rgb(34,34,34)` on white) PASS (10-14n: 12 px, 4.31) | 13 px, 15.91:1 PASS |
| (f) follows the wheel | 18 steps, 第 1–2 … 16 … 1 頁，共 60 頁, never hidden, 0 engine requests PASS | same PASS |
| (g) full-width bar at the root's bottom edge, number leftmost | bar `[8, 954, 1834, 32]` = `#content`'s x/width, bottom 986 = root bottom; text at x 20 PASS | bar `[8, 940, 1834, 32]`, bottom 972 = root bottom; text at x 20 PASS |

Screenshots: `k4-host-css/firefox-probe-10-14n-long60-page-number-0-mid.png` and `chrome-…-mid.png` (scrollTop 4900, 「第 4–5 頁，共 60 頁」 on the bar), `status-bar-bottom-left-{firefox,chrome}-x2.png` (the bottom-left 700×70 px, 2×).

## Desk, files, not done

- Before every browser run: KWallet `Locked` `b false`; `pgrep -c chrome` 32–35 (the owner's Chrome, untouched); nothing of ours running (the probe refuses otherwise — its first K4 attempt refused itself on its own wrapper's command line and was rerun after the exclusion was widened; the refused attempts' outputs were discarded, nothing had opened a browser). One browser job at a time (a queue script). Test files only in folders the probe created and deleted (`deletedFolder 204`); the owner's files and windows untouched.
- `probe_10_14o.py` = the 10-14n probe plus the `burst-1s-in-text` control arm and the preflight exclusion; `judge_k.py` the K2/K4 reader with its red self-test; `k1/` the unit witnesses; `k2-nohost-v20/`, `k4-host-css/` the browser reports, logs and screenshots; `editor.php.diff` the host change.
- Not done (the main session's): the v70 freeze, re-pins (`FINAL_PAGE_SHA256` etc.), packaging, the 0.2.21 host commit and version, `occ upgrade`, K3.
- For the freeze/release: the page's new identifiers are `deletesUnanswered`, `heldDeletes`, `DELETE_INPUT_TYPE_OF`, `deleteStateOf`, `boundaryNoopStands`, `holdsDelete`, `dropHeldDeletes`, `releaseHeldDelete`, `settleDelete`, and `editorAction(action, { onResult })`; the release text should say that at a document boundary the first press still waits about 2.25 s and further presses or a held key cost nothing more (SPEC-M3-held-key §3.2's 「放開之後最多再刪 2 字」 is unaffected inside text; at a C boundary it is now "nothing more").
