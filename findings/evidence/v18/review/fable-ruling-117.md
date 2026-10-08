# Fable's ruling on finding 117 (2026-10-08), verbatim

Asked by the main session at the owner's request ("117 發給fable"). The owner's stance, given with the request: the delay is unacceptable; re-running everything is acceptable; but no wasted work: verification and diagnosis are best batched with more changes. Fable worked read-only.

The main session spot-checked five claims before relaying them, by reading files:
- `LOK_CALLBACK_INVALIDATE_TILES` is not among `m_states` (`init.cxx:1592-1606`).
- `place.size.h` is 51650 and `observerAtEnd.size.h` is 17406 in `m2-4-chrome.json`.
- `tileWasPainted` is the 50 % sampled-opacity rule at `e2-editor-app.js:937-949`.
- The last engine-source commit is `f76c470e` (2026-10-06).
- There is no wall-clock wait in `postMergeKey`, and `stepPending` is cleared only at `probe_engine.cpp:3745`.

All five held. Nothing else was re-checked.

---

## SUMMARY

1. **Fix 117 in the engine and relink as v19 — but run the link-free instrument first, scoped to three questions, because its answers decide whether the v19 change set is one fix or two and whether the page fix can ride the same round.** The owner's "no wasted work" is honoured: nothing the diagnosis produces is thrown away (its instrument becomes v19's prediction baseline, its per-press toast index becomes the page fix's red case), and the engine fix is written in parallel — the diagnosis gates the *freeze* of the change set, not the start of the work.
2. **The fix design is mechanism-independent and sound:** in `MergeAwaitingKey`, re-read `.uno:Undo` on a short engine-side timer (10–20 ms, until the existing 2000 ms deadline) in addition to callback-triggered steps. The key stage's proof is a *state read*, not an *event*, so polling it is legitimate; the other three stages (Escape #1, K2, Escape #2) prove themselves by empty/non-empty *transitions* and must not be polled. Reading more often cannot create a false "changed": the payload moves only under the SolarMutex, by the key itself (`doc_getCommandValues` takes `SolarMutexGuard`, `libreoffice-26-8/desktop/source/lib/init.cxx:6689`; the key runs as a user event under the same lock, `init.cxx:4813`, `sw/source/uibase/uno/unotxdoc.cxx:4011-4012`) and `judgeAfterKey` is untouched (`wasm_sdk_probe/src/merge_key_undo.hpp:391-414`). The R0-round-5 clock guard is **not implemented** (read: no wall-clock wait in `postMergeKey`, `wasm_sdk_probe/src/probe_engine.cpp:3657-3676`); polling neither helps nor hurts it — register, don't widen the change set.
3. **Existing data already excludes "the key itself is slow"**: presses 1, 3, 55 complete in 37–38 ms on both browsers (measured, `findings/evidence/v18/m2-shakedown/m2-4-{chrome,firefox}.json`), and the 2000–2001 ms presses find the record *already there* at the deadline. So the 2 s is purely "nobody looked". But the stated hypothesis (`m_states` de-dup) is **incomplete**: `LOK_CALLBACK_INVALIDATE_TILES` (id 0) is not in `m_states` (`init.cxx:1592-1606`), and a merge that reflows ~100 lines should emit it. Either Writer emits none here (then why?) or it arrives and our step is lost (`stepPending` set and `submit()`ed at `probe_engine.cpp:3555-3568`, cleared only in `advanceMerge` `:3745`) — the latter would also bite the refusal paths, and polling would *mask* it. That one question is what the diagnosis must settle.
4. **The toast is almost certainly page-side and not 117's mechanism** (inference from read code + measured sizes): the document shrank 51,650 → 17,406 twips (3 pages → 1; `place.size.h` vs `observerAtEnd.size.h` in `m2-4-chrome.json`), `renderDocument` still requests the strip for the stale canvas height, and `tileWasPainted` fails any strip with < 50 % opaque samples (`wasm_sdk_probe/web/e2-editor-app.js:937-949`) — at press 55 a 1-page document on a 2-page canvas is ~51 % painted, borderline, fails. Same code ships on v8 → new finding, fixed on the page, verified on **v18** with the M2-4 mode (no link), red case on v8 (grow to 2 pages with Enter, delete one line back).
5. **Nothing else rides the link.** No engine source commit exists since the v15 link (`git log --since=2026-10-06 -- wasm_sdk_probe/src wasm_sdk_probe/Makefile`: only `f76c470e` and earlier are engine; later ones are packaging); the relink queue's engine-side `absent` items are designs or unverified one-liners; ICU trim / `STRIP_*` need a core rebuild and a different verification (corpus under `SAL_LOG`; `research/RESEARCH-2026-10-06-wasm-size-status.md:128-129` already assigns them to the next rebuild). v19 = v18's packs byte-identical + new wasm + Makefile/M1-1 plumbing. Keep it reviewable.
6. **Add a per-press latency clause to M2-4 now (spec §31, append-only), same bound and form as M2-2** (`keyUndo.keyToUndoMs` < 1000 ms **and** runner `keyToResponseMs` < 1000 ms, per press; non-vacuity 105 presses with numbers). Rule 9's four conditions hold: before satisfaction (v18 cannot satisfy it), forced by 117, form 一, closes when the counted M2-4 lands; counting semantics: nothing resets (no counted M2 exists). The v18 shakedown reports are the clause's natural red case. Keep `noToast` as written.
7. **Order so nothing is done twice:** diagnosis → §31 → engine fix + page fix (page half verified on v18 at once) → counted-M2 reader + red cases → adversarial review (opus + `codex exec -s read-only`) → freeze v56, `make` dist → owner links v19, archive → `BINDING` → **one** v19 round: identity, M1-1, cheap W3/W5 probes, corpus vs v18, product-path net v8 vs v19, owner document, and the merge runs **counted directly** (the runner-mode shakedown is already done on v18) → host 0.2.8 → R.

## 1. Fix now or diagnose first

**Ruling: both, in this order — diagnosis instrument first (hours, no link), engine fix written in parallel, change set frozen after the diagnosis answers three questions.** Plain reasons:

- A link is the owner's step and voids every binding on `ad3f68bb…`; the fix itself is ~30 lines in one loop. The expensive thing is the *round after* the link, and the owner wants exactly one. The diagnosis is what makes one round enough: it says whether a second engine fix (lost step) must be in the same link, and whether the toast can be fixed on the page before the round so the round binds the final page.
- First suspects were wrong in 114 and 116 (measured history). Here the first suspect ("de-dup") is *provably incomplete* from reading alone (`INVALIDATE_TILES` is not de-duplicated), so committing a link to it unexamined is the 114/116 pattern again.
- What existing data **already** proves (measured): key processing is prompt (37–38 ms on presses 1/3/55; the same posting path for all presses), and the record exists by 2000 ms — the delay is in *our* wait, not in LOK. That is why the polling fix can be written before the diagnosis without risk of fixing the wrong layer.

**What the diagnosis must establish (and why it is not wasted):**

| Question | Instrument | What each answer does |
|---|---|---|
| D1. On a slow press, does **any** `lok` event reach `onLokCallback` (`probe_engine.cpp:2537-2546`, which emits every callback as `type:"lok"`) between the key post and the deadline? Which ids, when? | Throwaway worker: copy `wasm_sdk_probe/sdk/sdk-worker.js` and forward every `lok` event with `performance.now()` (today only ids 0/1 are forwarded, `sdk-worker.js:1109-1113`; ids 12/15/16/30/31/32 only under `debug`, `:1114-1116`). New profile name, wasm byte-identical, archived, never shipped (precedent: finding 083, worker-only). One M2-4 run, Chrome suffices (both browsers identical). | **None** → polling alone is the fix. **Id 0 arrives and the press is still slow** → a lost step in our machinery; second fix in the same link, and it affects refusal paths too (a lost proof at Escape/K2 = `restore` refusal = reopen). |
| D2. Why 1, 3, 55? | Same run. Prediction to commit first: press 1 = `STATE_CHANGED` (8) with `.uno:Undo` becoming enabled; presses 3 and 55 = `DOCUMENT_SIZE_CHANGED` (13). Basis (inference): 51,650 twips = 3 × 16,838 + 2 × 568 = three A4 pages; 17,406 = one page; 107 paragraphs at ~52 lines/page → page 3 empties at press 3, page 2 at press 55. | If it holds, the de-dup story is confirmed for cursor/selection/state and the open point is only why id 0 is absent — register, do not chase; polling does not depend on it. |
| D3. Which press toasts, and which strip? | Same run; runner records toasts per press (today only once at the end, `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:852`) plus the strip's `yTwips`/`heightTwips` and `tile.documentSizeChanged`. Prediction: press 55 only (2-page canvas, 1-page document, ~51 % painted; press 3 is ~2/3 painted and passes the 50 % test). | Page-side confirmed → page fix lands before the v19 round and is verified on v18 now. Engine-side (an unpainted tile for a region inside the document) → it joins the link. |
| D4 (same instrument, +2 min). The 628–633 ms typed-merge plateau: does the first callback after the key arrive at ~630 ms? | One M2-1b run. | Yes → v19 prediction becomes one-sided ("Y01/Y02 drop to the untyped 28–49 ms range"). No → separate finding; M2-2's margin stays. Grep found no ~600 ms Writer timer (`sw/source/uibase/docvw/edtwin.cxx:5623` is 20 ms, `uiview/view.cxx:844` is 120 ms); unexplained, do not guess. |

**Fix design and its risks (read):**

- Engine loop at `probe_engine.cpp:6057-6075` waits only until `stageDeadline`; change: when `stage == MergeAwaitingKey`, wait until `min(stageDeadline, now + pollMs)` and on a poll wake synthesize the existing step (`values[0] = 3` → `advanceMerge` → `verifyMergeKey(false)`, `:3745-3763`) so it passes through the S2 try/catch (`:3958-3975`). Deadline semantics unchanged (`verifyMergeKey(true)` at 2000 ms, `:3770-3778`). Keep callback-triggered steps as the fast path. Do not poll the other three stages.
- *Mid-key read*: impossible — `doc_getCommandValues` holds the SolarMutex (`init.cxx:6689`), the key runs as a user event under it (`init.cxx:4813`; `SfxLokHelper::postKeyEventAsync`, `unotxdoc.cxx:4012`), and P4 (no nested flush inside key processing) is spec §11, bounded. A poll sees P0 or the post-key state, never between.
- *Stale state*: P0 is read right before the key under the same lock (`:3658-3666`); the "one event in flight" invariant (spec §16.2) means nothing older is queued. Unchanged by polling.
- *Clock guard / same-comment at the limit*: not implemented (R0 round 5 only suggested it, `findings/evidence/merge-native/README.md:174`). Two presses in one millisecond cannot happen (≥ 37 ms per transaction) → registered limit, not a v19 item. Polling does not change the comparison (`merge_key_undo.hpp:399-405`).
- *New ordering artefact to name for the reviewer*: with polling the completion may be emitted between KEYINPUT and KEYUP (both posted at `:3591-3596`); today it always lands after KEYUP because the flush is queued behind it. KEYUP has no document effect and the next K1 is queued behind it anyway. Harmless, but written down, not discovered.
- *Cost*: `.uno:Undo` serialises ≤ 100 actions (~12 KB) per poll; at 50–100 Hz for ≤ 2 s negligible on WASM; paints are BUSY-rejected during a barrier (`e2-editor-app.js:795-801`), so polls do not contend with tiles.
- *Not fixed by this, must not be expected*: C17-type "key had no effect" still waits the full deadline before refusing (spec §8) — absence of change cannot be proven early.

## 2. What rides the link, what does not

- **Rides**: (a) the key-stage poll; (b) a lost-step fix **only if D1 shows one**; (c) a `Makefile` rule for `e2-editor-v19` (clone of the v15 rule, `wasm_sdk_probe/Makefile:1228-1291`, packed with v18's `cjk-sub-e10` + `base-r5-no35`), and `tools/check_merge_key_undo_scope.py` extended so M1-1 finds the v19 rule (the "boundary must follow the list" lesson).
- **Does not ride**: ICU trim / `STRIP_CHART` / `STRIP_HUNSPELL` (core rebuild, behaviour changes, `SAL_LOG` corpus — the next rebuild's batch); `queue-identity-checked-is-reported-as-unavailable-when-preempted` (small, but no product-path cell watches it → an unverified hunk, the M2-5 "20 hunks" problem, spec §4.3); `queue-quantifier-check…`, `queue-verify-caret-by-block-identity` (designs); the toast (page); the clock guard (register); the 630 ms plateau (may fall out for free; add no code for it).

## 3. The toast

Handle **separately, on the page, before the v19 round** — not in the link. Evidence: the sizes above (measured); the strip loop throws on the first unpainted strip *before* acting on `documentSizeChanged` (`e2-editor-app.js:828-848`); `tileWasPainted`'s 50 % sampled-opacity rule (`:937-949`); the catch toasts and does not retry (`:866-890`). Finding 062's fix handled growth; shrink is its mirror and was never exercised (growth never produces a stale-too-tall canvas). v8 ships the same code → own finding number, red case on v8 without a link. The page fix changes the page sha → it must land before v56 is frozen and before any run that binds the page (spec §21.1). Verify the page half on v18 immediately with the M2-4 mode (`noToast` true; D3's recorded press as the red case) — the 068 lesson: never hand over half a fix.

## 4. Order of the remaining work

Now, on v18 (none of this depends on the link):
1. Commit predictions D1–D4; build the diagnostic profile; one M2-4 + one M2-1b run; write 117's 成因 section (measured) and the toast finding.
2. Spec §31 (append): M2-4 per-press latency clause (M2-2's bound and form; "never done" default: "repeated merges measured once, 2000 ms on v18; v19 not shown"); toast disposition (page; `noToast` wording kept); v19 definition (v18 packs byte-identical + new wasm), its round and the predictions file; M1-1 extended to v19; clock-guard registration; counting semantics (no reset).
3. Engine fix + Makefile/M1-1; page fix + its two red cases (v8 grow-then-shrink; v18 M2-4 with the old page).
4. Counted-M2 reader with red cases (the v18 M2-4 reports are real reds for latency and toast; verdict line + distinct exit code, rule p).
5. Adversarial review, B′ form: §30 + §31, runner modes, engine fix (name the KEYUP ordering point), page fix.
6. Freeze v56 (only after 3 and 5), `make` dist.

Then: owner links v19 (pattern `handoff/RUNBOOK-relink-v15.md`), archive named with worker sha, identity hashes; set `BINDING` + update `test_nothing_is_bound_before_v56` in one commit.

The single v19 round (predictions committed first): W2-shaped identity (manifest = v18's except `probe.wasm`/`probe.js`; worker and packs byte-identical); M1-1; W3/W5 font probes (cheap; 036 says the wasm is not a function of the source); corpus vs v18 (predict PASS, same 23 unsettled); product-path net v8 vs v19 (§23 cell-by-cell); owner document V5-type; merge: **counted M2-0..M2-4 directly** — 3 rounds × 2 browsers + control + `--pair`, plus `m2-1b`, `m2-4`, `m2-1-red` — with predictions: M2-4 105/105 verified, max `keyToUndoMs` < 300 ms (prediction; criterion 1000), no toast, final document = native; M2-1b plateau per D4. Counting directly saves a full merge run set; the risk is a page/shell red that voids the count, which a cheap generation number (v57) absorbs. Then host 0.2.8 (`tools/check_m3_assets.py:1015-1021` pin → `cjk-sub-e10`) → R.

## 5. Framing corrections

- "Diagnose first **or** fix now" is a false choice; the link is the batch point, the diagnosis is an hour and gates the change-set freeze only.
- The de-dup hypothesis cannot be the whole mechanism (id 0 is not de-duplicated); say so in the finding before measuring, so a D1 result showing id 0 arriving is read as "lost step", not noise.
- The 1/3/55 pattern is explainable now (page-count drops + first undo state) — write it as a prediction, not a result.
- The toast is not 117's; its attribution (page, 50 % sampling on a stale canvas) is inference until D3, and should become a measurement in the same run, not a link item.
- "Re-run everything" should not mean W1–W6 verbatim: W1 is a pack build (unchanged); re-run what the new bytes can touch (identity, probes, corpus, net, merge, owner doc).
- Keep `noToast`; add latency; do not narrow M2-4. M2-1b needs no new clause (M2-2 already covers its 40 attempts, spec §30.2).
- The handoff's "whether M2-4 is satisfiable on any engine we have": on v18 no (latency and toast); on v19 predicted yes, with the page fix.
