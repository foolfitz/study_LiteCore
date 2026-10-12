# Review 1 — adversarial pass on the finding-134 judge (ruling-1 condition 9; one pass)

Reviewer: opus subagent, 2026-10-13. One pass, per §34.

**Read:** `brief-1-judge.md`; `132/held-into-refusal/ruling/ruling-1.md` (conditions 1–3, 7, F6); `judge_held_into_refusal.py` (whole); `probe_held_into_refusal.py` (whole); `git diff 32aaddb0 702c19ec -- wasm_sdk_probe/web/e2-editor-app.js` plus the page code around it (`run()` 1797–1855, `editorAction()` 1914–1944, delete `beforeinput` 2375–2390, H2 2597–2610, B 2612–2648, `reopenAfterBoundaryRefusal` 1648–1718); `editor-shell/editor-session.js` (drain 296–335, `_blockQueue` 342–352, `placeCaret` 394–448, `restart` 587–595, `_openFresh` 158–197); `editor-shell-v2/narrow-editor-v2-session.js` `_enqueue` 635–690; `input/input-adapter.js` `setBlocked`/`invalidate` 286–320; `tools/check_m3_production_ui.py` (`press`, `keyed`, `save_and_settle`, `static_facts`); `tools/probe_hand_test_0212.py` `hold_key`; `tools/run_browser_probe.py` launch arguments.

**Ran:** the judge on `134/red-d-on-0.2.15/report.json` (reads a JSON file); three read-only Python passes over the `log` arrays of run-1, red-D and acceptance-0.2.16. No browser, no probe, nothing against the ddev host. Nothing edited except this file; nothing committed.

**Acceptance directory:** when first read it had 7 rounds and no `staticAfter`; it completed during this review (`completedAt` 2026-10-12T22:58:56Z, 12 rounds, `judge-output.txt` exit 0, `README.md`). Figures marked "acceptance" are from the completed report.

## Verdict

**BLOCKING: none.** I found no reachable path (this probe at its default options, page `6470dec0…`) on which the judge exits 0 while finding 134 is unfixed, and none on which it fails a correct B+D and reports the failure as a 134 failure, other than the fail-closed cases listed under NOTE.

**SHOULD: 3** (S1 B's non-vacuity unjudged; S2 D judged per paragraph, claimed per caret; S3 release binding). **NOTE: 9.**

## SHOULD

### S1. B's non-vacuity is not judged, and B's direct observable is in the log but unused
`judge_held_into_refusal.py:36-45, 67-73`; `probe_held_into_refusal.py:183-187, 222`.

- The hold arms judge B by its consequences (no second reopen, document unchanged). Those consequences only appear if repeats keep arriving after the reopened engine would accept one, and nothing in the judge requires that. **Construction (reachable with this probe, by a supported flag):** `--hold-ms 2500` on a page with D but without B. start-hold: refusal ≈1.2 s after the first keydown, new generation ready ≈2.2 s (Chrome) / ≈3.2 s (Firefox), then the gesture gate swallows repeats for another 0.85–0.99 s (run-1, ruling-1 last fact-check bullet), key up at 2.5 s → refusals 1, gens `['1','2']`, no limit, same True, marks 1 → **PASS** with B absent. end-hold likewise. At the default 8 s the same happens only if a Firefox reopen took ≳6 s instead of ≈2 s. The judge never reads `report["hold"]`.
- **Not what happened in this acceptance.** Per hold round, repeat keydowns that landed in the sink more than 1 s after the new generation was ready: Chrome 158 / 160 / 170 / 171, Firefox 133 / 131 / 144 / 144; last repeat 5.1–6.1 s after ready. The PASS is non-vacuous in fact; the judge just does not say so.
- **B's literal claim has a per-instance observable already recorded.** Condition 1: "no further Backspace/Delete keydown with `repeat === true` reaches the engine". A keydown that `skipRefusedRepeat` prevents produces no `beforeinput`, and the probe logs every sink `beforeinput` (`probe:76`). Delete-type `beforeinput` after the first `restart-required` state entry: **acceptance 0 in all 8 hold rounds; run-1 (pre-fix) 8 in every start-hold round, 74–86 in every end-hold round.**
- Proposed form-1 rule for both hold arms, computable from the existing report without a re-run: (i) zero delete-type `beforeinput` after the first transition into `restart-required`; (ii) at least N repeat keydowns with `focus == "sink"` later than the new generation's first `ready` + 1 s (N = 20, say). (i) is red on run-1 and green on acceptance.
- Under §34 adopting this is the owner's decision (a changed check needs a witness report). If it is not adopted, register the two figures above next to the verdict as a one-time measurement.

### S2. D is judged per paragraph; the claim is per caret
`judge_held_into_refusal.py:59-64`; `probe_held_into_refusal.py:87-97`.

- `mark_at_end` accepts `zqx` anywhere in paragraph 210. In the owner's document that paragraph is 72 characters long (computed locally from the scratch copy, sha `7b336879…`, lengths only), which is at least two lines at this page width. `LAST_LINE` clicks at x ≈ 0.837 of the page width *before* End. **Construction (question 1b):** a D that restored to the pre-End click point, or to the start of the last line, would put `zqx` mid-paragraph: same True, marks 1, markParagraphs `[210]` → **PASS** while the next input lands away from the caret.
- **Not reachable that I could find on this page.** The caret D reads (`page:1676`) is the state the drain wrote after End (`editor-session.js:307-311`); the end-of-document barrier selects nothing, so it pushes no intermediate caret; the reopened layout is the same bytes laid out by the same engine. Hence SHOULD, not BLOCKING.
- The fix needs a probe field, not only a judge line: for example `markAtParagraphEnd: [texts[i].endswith(MARK) for i in markParagraphs]` (booleans, no text) and the rule `== [True]`. It cannot be retrofitted to the acceptance report.

### S3. The static check binds the verdict to the page bytes, not to the release under test
`judge_held_into_refusal.py:26, 94-100`.

- **Bound:** `servedPage` == `distPage` == `6470dec0…`, unchanged across the run. `servedPage` is the host checkout's `engine/MANIFEST.json` claim (`check_m3_production_ui.static_facts`), not bytes read back from the browser. The check that ties the manifest to the served `.zst`/`.gz` (`134/check-engine-decoded-0.2.16.txt`, 22:50:40Z) lives outside the report and ran once, 21 s before the run started.
- **Not bound in the acceptance report:**
  - `hostCommit` is `568608c` (0.2.15's commit) with `hostDirty ["M appinfo/info.xml"]`. The engine/ repackage (buildId daf70d77 → 9352fae3) does not show in git status, so hostCommit and hostDirty say nothing about the engine bytes.
  - `shellBundle.exit` is 1: "manifest is out of date … changed web/e2-editor-app.js". v65 was not frozen when the run started.
  - `hostVersion` and `buildId` are compared before against after, never against a named value.
  - `servedSession` (`62a2a20e…`, the file that carries the `placeCaret` and `restart` that D depends on) is not in `STATIC_KEYS`.
- **Consequence:** for "B+D on page 6470dec0 fixes 134" the page binding is enough. For condition 5 ("host 0.2.16 / shell v65 is the candidate") it is not. After the v65 freeze and the host commit, record that v65's manifest names page `6470dec0…` and session `62a2a20e…`, and that the committed host's MANIFEST buildId is `9352fae3aea68b5e`. This is a one-time binding note, not a judge change.

## NOTE

**N1. Question 3: the refusal counter is fail-closed but timing-fragile.** `probe:132-133`; `editor-session.js:316, 320, 591`.
- **The window:** `restart-required` lasts 0–1 ms in every log (acceptance Chrome end-press-type 2839 → `loading` 2840; Firefox 2890 → 2890). It is sampled only because `item.reject(error)` (316) runs before `_blockQueue`'s transition (320), and the rejection takes at least two microtask hops to reach `run()`'s catch → `reopenAfterBoundaryRefusal` → `restart()`'s synchronous `transition("loading")` (591). The MutationObserver microtask queued by the transition runs in between. Evidence: at the `restart-required` entry the `latency` field still shows the previous label (移到行尾), so the observer ran before `run()`'s catch rewrote it.
- **Fail direction:** a refactor that shortens that chain to one hop makes `refusals` 0, which FAILs a correct fix. It cannot flip a verdict to PASS:
  - a second reopen changes `generations` (judge 41);
  - a second refusal at the ceiling sets `limit` (43);
  - a second refusal with `restartKeepsContent()` false stays in `restart-required` and is counted.
- **Gate refusals** (`EDITOR_FORMAT_GESTURE_UNSUPPORTED`, "nothing was dispatched") make no state transition, use no generation and change nothing, so they have nothing to count. None appear in the acceptance toasts.
- **Other reopens:** 119's `deleteUnverified` reopens through the same function and is counted, which is the right count for these rules. `recoverable-error` is neither counted nor reopened automatically. Such a round fails on marks (the save does not reach the server), but with a message that does not name the cause.

**N2. D is exercised only in the end arms, and judged only in end-press-type.**
- **Start arms:** in all 6, the state sequence after `ready` has no `busy`. The short-circuit at `page:1697` fired (reopened caret == recorded caret), so start-hold witnesses B only. Brief Q2's "D puts the caret back at the start" is, in fact, "D finds it already there".
- **End arms:** in all 6, the pill reads `busy` for 0.71–0.78 s after `ready`, `scroll` goes 0 → 21477 / 21463, and the toast lacks 「游標現在在文件開頭」. D's click ran 6/6, but only the 2 end-press-type rounds judge where it put the caret. The end-hold scroll series corroborates this; it is reported, not judged (condition 7).

**N3. The README's 0.7 s window, read from code (unmeasured): keys typed after `el.sink.focus()` land at the restored caret, not at the start.**
- **Order:** `placeCaret` is enqueued in the same task as the focus (`page:1694` → `1699`, no await between them when the caret differs).
- **No hold:** the v2 `_enqueue` (`narrow-editor-v2-session.js:653`) does not hold it, because the refusal's `setBlocked(true)` → `invalidate()` (`input-adapter.js:286-291`) emptied the adapter queue. A character typed afterwards is queued as `commit-text` behind `place-caret` in the base FIFO.
- **Conflict with the ruling:** this contradicts ruling-1 F6, "a key typed between the sink focus and the placeCaret ack lands at the start".
- **Exception:** a Delete/Backspace *press* in that window at the document end still goes out (B lets presses through) and is refused again, costing one more generation (the B1 named limit).
- Not a judge issue: the probe types after a 2.5 s settle, so it sees neither case.

**N4. F6 misnames the placeCaret timeout.** Ruling-1 F6 says a placeCaret timeout is a `TIMEOUT` in `RECOVERY_ERRORS` and blocks the queue. In the code, placeCaret's own 30 s expiry throws `EDITOR_CARET_NOT_PLACED` (`editor-session.js:442`), which is not in `RECOVERY_ERRORS`. The queue stays open, and D's fail-soft (`page:1700-1702`, toast `1714`) is what the user sees. Only an inner `getState`/`click` `TIMEOUT` (a dead engine) blocks. In the probe either case FAILs end-press-type (mark in paragraph 0, or marks 0).

**N5. Question 5: rounds are independent, and contamination fails closed.**
- **Window blur:** both browsers run headless (`run_browser_probe.py`: `-headless`, `--headless=new`), with a fresh profile per round. The owner's desktop and Firefox cannot take OS focus and fire the window `blur` that ends a hold (`page:2648`). I found no path for it to reach the probe.
- **Contamination:** each round re-uploads the original and clears locks. The remaining cross-round paths are a late PUT or UNLOCK from the previous round's closed browser, or a silently failed upload. Each leaves a file that already carries one `zqx`, so the round ends with marks ≥ 2 and FAILs; none produces a PASS.
- The judge reads neither the `upload` status nor a pre-open server read; `marks == 1` is what makes contamination fail-closed, so keep it in every rule.

**N6. start-hold also checks that B does not over-block.** All five `kjkjk` must be deleted before the start is reached, so a B that dropped repeats too early FAILs with charDelta > 0. B sets its flag on *any* rejection of a delete the page sent (`page:2388`), not only boundary ones. A stray mid-hold rejection (131 or 119 class) would therefore FAIL start-hold with charDelta +k. That is B doing what condition 1 says; read the sign of charDelta before blaming 134.

**N7. The red for `mark_at_end` failing by its own rule is not in evidence.** I ran the judge on `134/red-d-on-0.2.15/report.json --page abe93f45…`. It printed `FAIL chrome end-press-type r0: mark in paragraphs [0], last is 210` and the same line for Firefox, with exit 1 (plus the expected "0 rounds" lines for the absent arms). `red-a-run-1.txt` shows end-press-type only as absent. This output is worth saving next to the other two reds; I did not write it.

**N8. The judge trusts its inputs without binding them.** It reads the probe's run-time `summary`, not the `log` it was computed from. It reads `ARMS` from the probe source at judge time, while the report carries no sha for the probe or the judge. A later probe edit (an arm renamed or redefined) would change what an old report is judged against, with no trace. Recording sha256 of the probe and the judge in the report and output closes this. Low risk: the tree was clean at the acceptance run.

**N9. Scope of the verdict line and of the server comparison.**
- `--browsers chrome` narrows the requirement, and the final verdict line does not print the browser set (judge 88, 110, 130); only the per-round lines show it.
- The server comparison (`paragraph_texts_from_xml`) is text-only and cannot see non-text changes. That is adequate for 134, whose damage is character deletion and paragraph joins.

## Brief question 1: constructions
- **(a) A held key reaches the engine after the refusal, and the judge passes.** Reachable with this probe only by a flag (`--hold-ms` ≲ 3 s) on a page without B; see S1. At the default options it is not reachable: margins measured above, and any repeat that reaches either end's engine is refused again and changes `generations`.
- **(b) The next input after a reopen lands away from the caret, and the judge passes.** Only a misplacement *within* paragraph 210 passes (S2); I found no path to it on this page. The 0.7 s window does not produce one by code (N3).
- **(c) The document changes, and the judge passes.** Only with a hand-made report (the judge trusts `server.sameAsOriginal` and `summary`), or with a non-text change (N9). On this page B only drops keydowns and D only clicks; neither mutates.

## Brief question 2: per-arm rules under B+D
Checked by code, then against the acceptance run.

- **start-hold, `refusals == 1`.** Right. The refused delete and the second delete in flight (H2 depth 2) are rejected by one `_blockQueue`, which makes one transition. Whichever rejection chain reaches `reopenAfterBoundaryRefusal` second sees `loading` and returns. The flag is set in the `.catch` before `finally` lowers the depth, so no task can slip in between. Acceptance 4/4: 7 `beforeinput` events, all before the refusal (5 letters + the refused delete + the queued one), 0 after.
- **end-hold, `sameAsOriginal True` and `marks == 1` with the mark typed before the hold.** Right, and it is B's witness, not D's. It also checks that the reopen kept unsaved content: the checkpoint path makes `dirty: useCheckpoint`, and marks would be 0 if the reopen fell back to the authority bytes.
- **end-press-type, `markParagraphs == [last]`.** Right in direction: red-D gives `[0]`, acceptance gives `[210]`. It is coarser than the claim (S2). `genBeforeMark` is `'2'` in both acceptance rounds; the judge does not read it, but `generations` + `marks` + `settle` already exclude a mark typed before the reopen.
- **start-press.** Unchanged, and correct for this build.
