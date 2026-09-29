# Ruling: after `INSTALLS ELSEWHERE`, option D — measure first (fable, 2026-09-29, on the owner's authority)

The owner was away ("請自主執行後續任務 / 如果有需要決策的地方，請發包給fable，我授權它代替我裁決").
The handoff's to-do list was done (`handoff/HANDOFF-2026-09-29c-installs-elsewhere.md`); its
remaining options were written as the owner's choice. The main session asked fable which to take,
**STOP included**, leaning D (host-only hardening for findings 103/104) unless the host turned out
unable to put two saves in one second. fable ran read-only. The Chinese "WHY" is the ruling's own
text, for the owner.

## RULING

D — scope: criteria first, host 0.2.2, a counted verdict for the new arm(s), the four existing
counted runners re-run green on 0.2.2, then stop. Mandatory half = finding 104 (no two host PUTs
in one wall-clock second). The 103 half (compare-before-save) only under condition 6. No App
Store, no new INSTALLS ELSEWHERE window, no page/shell/engine change. **If condition 1's
measurement shows the page cannot produce a same-ETag pair, STOP after registering that
measurement.**

## WHY (for the owner, verbatim)

> 這一輪剩下的選項裡，只有 D 是「產品自己的路就走得到、而且會永久掉資料」的缺陷：使用者連按兩次存檔（或按住 Ctrl+S——頁面沒有過濾鍵盤重複，按住就是一連串存檔）→ 每次 PUT 只要 74 ms，兩次落在同一秒 → 之後任何人從 Files 還原任何舊版本，較晚那次存檔就從檔案和版本歷史裡一起消失（104，實測 5/5）。上游修不了（送出擱置中），頁面不能動（換身分就要重跑全部計數執行），宿主是唯一能動的地方，而宿主的四張回歸網都在。其他選項都該等你回來選：A 要你出面、C 作廢所有計數判定、H 會讓你另外兩個 ddev 專案短暫 404、G 是省流量不是修缺陷、F 沒有資料遺失也還沒有修法設計。D 做完的樣子是宿主 0.2.2＋一支先紅過的新臂＋四支既有 runner 在 0.2.2 上重新全綠；`INSTALLS ELSEWHERE` 仍然只是 0.2.1 的事實，0.2.2 要不要再跑安裝窗留給你。我要求先量「頁面真的能讓兩次存檔落在同一秒」再動手：現有每一筆計數執行的兩次存檔都隔了 ≥1.18 秒，那是 harness 的路，不是使用者的路，沒有人真的量過。

## FACT CHECK (fable's, condensed)

- F1 (the host can put two saves in one second) — **mechanism confirmed, never produced through
  the page**: host `save()` has no spacing (`litecore-editor.js:326-338`, `put` at `:341-351`);
  the page queues saves but does not space them (`e2-editor-app.js:1038-1042`); Ctrl+S has no
  `event.repeat` filter (`:1386-1392`); one host save round trip 74 ms (host-entry counted run
  `2026-09-29T013030Z`, chrome open-save[0] `saved.latency`). All nine counted
  host-entry/locks/versions reports have two-save gaps of 1178–1465 ms (host entry) or ~4.2 s
  (versions R1 waits 3 s), ETags all different; V2's same-second pair was raw HTTP.
- F2 (D is host-only) — confirmed; caveat: the nets assert shapes (one attempt per save, the
  second save chains on the first's version); a wait or an extra GET may need amended
  expectations, allowed only with a written reason.
- F3 — confirmed for C and H; F's "plus a host change" unverified (no hook after the user
  confirms leaving); G's "PHP has no zstd/brotli decoder" unverified.
- F4 (upstream on hold) — confirmed.

The main session re-read `litecore-editor.js:326-356` and `e2-editor-app.js:1034-1044`,
`:1384-1394` before acting.

## CONDITIONS

1. **Measure first**, on 0.2.1, through the real page, both browsers: (a) two presses with no wait
   (button, then Ctrl+S) ≥10 pairs each; (b) held Ctrl+S ~1 s, ≥3 trials. Record per save the
   host's `saves[].etag`, `attempts[].at`, PUT gap, server mtime. Proceed only if ≥1 equal-ETag
   pair per browser (this is the fix's red case). If 0 pairs with recorded gaps < 1 s → the
   ETag-reuse premise fails on this path → STOP, register. If 0 pairs because gaps are ≥ 1 s →
   spacing is moot → STOP, register, hand back.
2. Criteria before code: revise SPEC-M3-versions §5 in place (revision log entry) and add the new
   arm(s) to §4 in form 1/2 with an "if never done" default; every clause has a red case that
   runs red on 0.2.1 before the fix lands.
3. Half A (mandatory): the host sends no PUT to the file until ≥ 1.0 s after the previous PUT's
   response was received (client clock). Pass = 0 equal-ETag pairs over the same ≥ 10 pairs per
   browser, server mtime seconds differ, and after a third save both earlier bytes are in the
   version list. The wait applies only to a second-in-a-row save; record first- and second-save
   latencies before/after.
4. Held Ctrl+S after the fix: count PUTs and tail seconds. If a 1-s hold yields > 5 PUTs,
   register a finding against the page (`event.repeat` unfiltered = page identity); do NOT add
   coalescing or any new mechanism to the host.
5. Host-only: only `js/litecore-editor.js` and `appinfo/info.xml` (0.2.2) change; the page stays
   `fbfb59a4…`; no shell generation, no relink.
6. Half B (103 compare-before-save) only if: GET + sha256 against the host's own last bytes, no
   server-side mechanism; extra latency ≤ one PUT; its red case = a token-bypass write landing in
   the same second as the page's first save, then its second → on 0.2.1: 204 overwrite; on 0.2.2:
   conflict copy. Otherwise register half B as not done, with the reason.
7. After committing 0.2.2: re-run locks, versions, assets and host-entry counted on the dev
   instance; all verdicts unchanged, all red cases red. A red is a finding, never a test fix.
8. Rebuild `litecore-0.2.2.tar.gz` (record only). No new INSTALLS ELSEWHERE window.
9. This WHY goes into the 「裁決」 sections of findings 103 and 104; handoff in English.
10. Stop after 7–9. A/C/F/G/H stay the owner's choice.
