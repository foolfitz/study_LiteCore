# Ruling request 2 (v21 shakedown): D7 in Firefox is NOT_ESTABLISHED twice, from the instrument's timer

**You decide this question.** The owner is awake and chose to send it to fable (2026-10-17, 「D7 發給 fable」), out of the three options in `handoff/HANDOFF-2026-10-17-v21-shakedown-item1-only.md` 「D7 re-run」. Work read-only: read files and run read-only Python over the reports, but start no browser, edit nothing and commit nothing. The main session commits your reply verbatim as `review/ruling-fable-2.md`, checks it, and runs whatever it orders, under the browser lock.

Repo: `/home/jiajun/LibreOffice/study_LiteCore`. Read `CLAUDE.md` 「驗收判準的形式」 §1–§11 first. §2 (no criterion quantified over a future judgement), §4, §6, §8 and §9 (adding versus moving) bear on this question.

For context only: the owner also chose the next-link order **C** today. v21 finishes first (freeze shell v74, host 0.2.25, the host arms, binding, the count). Then v22 is a relink that changes one variable, the engine thread's stack (finding 153), with item 2's re-enable and fix 3 riding along. The freeze waits on this ruling, because option C below changes the shell.

## The criterion (F-claims: check each against the files)

- **F1.** Spec `specs/SPEC-M3-link-batch-v21.md:359`, §11.1, verbatim: 「D1 母數的每一下：原生有游標回呼 → `documented-callback-*`；原生無聲 → `verified-move-readback`，< 500 ms；回覆裡的游標等於回覆後 **500±50 ms** 的單次 `editor-get-state`」. Form: 工具封閉. Default: **「第 1 項不出貨」**.
- **F2.** §11.0 (`:340-346`): N=3 per arm per browser, pass = N/N. 「缺報、缺回、NE 一律等於「沒做」，套用該條的預設」. The revision log (`:483`) says the criteria are pinned from `523871fa`: 「之後只准追加更正，不得移動」.
- **F3. Where the window came from.**
  - SPEC-M3-link-batch §10.2 S2 (`specs/SPEC-M3-link-batch.md:159`): 「完成後至少 500 ms」.
  - v21 §9.7 (`SPEC-M3-link-batch-v21.md:220`): 「≥500 ms 之後」.
  - Codex review 2, S4 (`handoff/link-batch-v21/review-2-codex.md:152`): 「`S:220` 只寫「≥500 ms 之後」，沒有固定採哪次讀取，容許實作者一直重讀到相等」, with the fix 「D7 指定單次採樣時點與容許時間窗」.
  - `523871fa` then wrote 「500±50 ms 的單次」 in §11.1. **The ±50 has no stated derivation**: the commit adds only the table row [observed: `git show 523871fa`; `grep 單次|採樣|時間窗` over the spec finds only `:359`]. The point of the change was a single read at a fixed time, so that nobody can re-read until the carets agree.
- **F4. D7 is read in other criteria too.** D10 (`:362`) adds 「外加 D7 的新鮮度條款」, and D10 is PASS in both browsers with the current instrument. D11a's judge also reads the same ask (`judge_v21_shakedown_item1.py:1416`, self-test).

## The instrument

- **F5. The observer** (`wasm_sdk_probe/tools/v21_item1_observer.py:73-104`; ARMS-item1 §2.2 (c), DECISION D-15 A):
  - The observer wraps `window.Worker` and adds its `message` listener when the engine worker is constructed, so it runs before the page's own listener [inferred from the source: listener order is registration order].
  - On a successful `move-document-*` response, the listener logs `rs` with `t = performance.now()` (rounded to 0.1 ms) and immediately calls `setTimeout(…, 500)`. The callback posts one `editorGetStateV2` and records `tPosted = now()`.
  - So `tPosted − rs.t` measures only the timer's lateness on the main thread.
- **F6. The runner** (`run_v21_shakedown_item1.py:350-380`): after the reply, it waits up to 3 s for the ask's answer before it does anything else. No input of ours lies between the reply and the read.
- **F7. The judge** (`judge_v21_shakedown_item1.py:58`, `:216-241`, `:244-273`):
  - `ASK7_WINDOW = (450.0, 550.0)`; outside it, that press reads NE;
  - a press with fewer than 3 non-NE rounds and no FAIL becomes NE;
  - D7 is the worst over the 64 presses.
- **F8. Identity.** Every report binds the injected snippets (`snippetSha256`, `htmlServedSha256`; `v21_shakedown_common.py:301-311`), so a changed timer constant shows in every report. `runnerSha256` hashes the runner file only, and the observer is a separate module.

## The data (the main session computed it from the reports; please recompute)

Script: `review/d7-delay-distribution.py`, output `review/d7-delay-distribution.txt` (reads `results.d1.rounds[*].presses[*]`, delay = `ask7.tPosted − response.t`). Reports under `findings/evidence/link-batch-v21/shakedown/evidence/`.

- **F9. Chrome 151 (headless):** `item1/report-chrome-d1-20261017T064131.json`, 192 reads, all at **500.1–500.9 ms**. D7 PASS.
- **F10. Firefox 157.0.1 (headless), first run:** `superseded/item1/report-firefox-d1-20261017T071208.json`, 192 reads.
  - 165 reads land in [500, 505); 15 are later than 520; the maximum is 553.5.
  - **2 reads are outside the window**: 550.1 (t-end-B2-n1 r3) and 553.5 (t-home-B2-n2 r1).
  - Reads later than 505, by fixture family: `t-*` 16/72, `tl-*` 5/18, `sec-*` 4/36, `a3-*` 2/21; `r-*`, `tf-*`, `a1`, `a2`, `x` 0.
  - Foreign CPU was clean.
- **F11. Firefox, re-run under the lock** (desk load 0.18 at the start): `item1/report-firefox-d1-20261017T092410.json`, 192 reads.
  - 166 reads land in [500, 505); 13 are later than 520; the maximum is 560.3.
  - **6 reads are outside the window, at 554.7–560.3 ms.** All six are `t-*` "cursor" presses.
  - Reads later than 505: `t-*` 16/72, `a3-*` 4/21, `r-*` 2/18 (one at 546.2), `tl-*` 2/18, `sec-*` 1/36, `tf-*` 1/18.
  - **One more cell is NE from foreign CPU:** sec-home-n1 r2, the owner's desktop Chrome extension renderer at 79 %.
  - The re-judged output is `evidence/judge-item1-after-d7-rerun.txt` (D7 Firefox NE; D1 and D4 PASS).
- **F12.** In every read outside the window, in both runs, the reply caret equals the read caret in all four fields. **No FAIL anywhere.** The late reads are mostly an arm's first press (`ch1`/`ce1`).
- **F13.** The silent presses complete by readback at 250.6–251.2 ms (§12.3, `:450`), so the engine's own 250 ms deadline is far from either end of the window.

## My reading, and its unverified premise

**Reading** [inferred]: Firefox runs the timer late when the main thread is busy after a move in a table fixture (most likely the repaint). The product property D7 measures held in every read. Chrome shows no such lateness.

**My option A assumes the lateness is additive**: a timer aimed at +470 would fire at most about 60 ms late, so by about +530. **That is not measured.** The late reads end at 522–560 ms in both runs, which says when the busy stretch ended, not when it began. If it begins before +470, a +470 timer is held to the same end and still misses. No main-thread trace exists in the reports.

## Options

- **A. Calibrate the instrument, not the criterion.** Change the observer's constant 500 → 470, and nothing else.
  - The window, D7's wording and the judge stay as they are.
  - It is a §34 change (execution +1). The witnesses are the two Firefox reports above, already committed.
  - Re-run Firefox D1 only (about 35 min), with the owner's desktop Chrome closed.
  - Chrome's D7 PASS stands at constant 500: both constants are inside the window, and the change is recorded.
- **A0. Before A, map the busy stretch** (a diagnostic, not evidence, about 10–15 min):
  - Firefox, the `t-*` arms only, with a copy of the observer that adds sentinel timers at +440, +470 and +500 and a 5 ms `setInterval` heartbeat logging gaps over 10 ms;
  - the constant is then picked from that data. We may instead learn that no single constant works.
- **A″. Like A, but aim at +455.** That gives the most slack (+95 ms), and a read further from the nominal 500.
- **C. Take the default 「第 1 項不出貨」.** Nothing in the evidence says the product is wrong, so this withholds item 1 over an instrument miss, and the shell changes before the freeze (§11.0: the page stops binding Ctrl+Home/End; L-142-sdk-callable).

**Not offered, and why** (you may disagree; say why):
- Widening the judge's window, or reading it one-sided (≥450). That would move a pinned threshold after the data were seen (CLAUDE.md §9; revision log `:483`). The one-sided reading is also exactly what codex S4 had closed.
- Taking three in-window rounds per press across the two Firefox reports. That is choosing reads, which S4 forbade.
- Re-running unchanged. Two runs gave 2 and then 6 out of 192.

**My lean: A0, then A** with the constant A0 supports. A alone is acceptable if you judge the additivity premise immaterial.

## Questions

- **Q1.** Which option, the constant, and whether A0 comes first.
- **Q2.** Can Chrome's D7 PASS (constant 500) stand beside a Firefox run at another constant, or must Chrome D1 be re-run too (about 35 min)? D10 (Chrome and Firefox) and D11a also read the same ask and are PASS at constant 500: re-run them or not?
- **Q3. Pre-commit the outcome now** (CLAUDE.md §2): if the re-run at the new constant still has a read outside the window, what is the verdict? Is there one more calibration, or does the default apply? What is the stop rule?
- **Q4. §34:**
  - Is this "modified because of execution" (+1), with these witnesses?
  - Is anything red-first needed? The judge does not change. Does the instrument need its own control, for example showing that a stale reply still reads FAIL at the new constant?
- **Q5.** Anything I have not seen, including a premise above that is wrong.

## What I need back

For each of Q1–Q5:

- `RULING`;
- `WHY（給擁有者）`: 台灣正體中文白話，三到六句;
- `FACT CHECK`: which F-claims you checked and against what, and any that are wrong;
- `CONDITIONS`: numbered and checkable. Include what is re-run, on which browser, under what desk conditions, and what is appended to the spec or the results README under CLAUDE.md §9/§10.

Then one line: **what happens next, in order**, up to the v74 freeze.
