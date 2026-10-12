# fable's ruling on `brief-2-q2-premise.md` (2026-10-12), verbatim except §7

§7's zh-TW spec text was appended word for word to `specs/SPEC-M3-autosave.md` as §9.15–§9.17 and is not repeated here.

The owner chose 「交 fable 重新裁決」. fable worked read-only. The main session checked the code lines it cites (`e2-editor-app.js` `bandOrder` 1122–1130, the `renderAgain` break at 1200, `endRenderPassOnInput` 2355–2356, `run()` awaiting `renderDocument()` 1746; `editor-session.js` 262–266 pushes with no cap; `probe_hand_test_0212.py` "about 30 ms" comment) and re-ran the readers: `read_ghost_long.py` on the three 20-key reports and `read_128b_cells.py` on the 128-B re-run give output identical to the committed `read.txt` / `cells.txt`; the pre-fix 4-key cells match correction 1 (each `–` with a non-zero `persistent`; Firefox high, `persistent` 0, reads 76.8 / 10.9 / 73.8 / 84.6); +23.7 / +9.1 / +26.7 / +16.3 % and 284.2 / 293.1 ms re-computed. They hold.

---

RULING 2 on findings/evidence/128/ruling/brief-2-q2-premise.md (fable, 2026-10-12, read-only; nothing run that writes, no browser started).

**Q2′ — A′ (A with the wording and the disposition corrected): withdraw the 4-key rapid clause of 128-B, register L-128-rapid worded structurally (a hold, not "N keys = M ms"), freeze v62; the two repaint remedies go to one post-release spec as two separately A/B'd mechanisms. C is rejected.**
**Q2′b — The 4-key clause is the wrong form and is withdrawn, not reinterpreted. No new rapid criterion for 0.2.13: transience is already a hard criterion (131-B `persistent.differing == 0`); duration becomes a named limit with no guard, registered as such; the hold criterion is written in the post-release spec before that spec's first run.**
**Q4 — The §9.13 substitution is sound and nothing else is needed before freezing; one unmeasured hole is registered as NOT_ESTABLISHED (not a defect, not a gate).**
**Q5 — Still not a blocker, still post-release; but the registration must change: it is a regression in kind vs 0.2.12 at 50 ms spacing (keeps up → falls behind), the real auto-repeat rate (~30 ms) is unmeasured and by arithmetic makes the backlog about equal to the hold, the queue has no cap, and the owner's hand test must include a 2 s hold.**

---

## 0. What I re-derived, and what I could not

Re-derived from the committed `report.json` files with the repo's own readers (`python3 -I`), byte-for-byte equal to the committed `read.txt` / `cells.txt` / `ghost-arms.txt` / `burst-times.txt`:

- `131/ghost-20/report.json` (fixed page): Chrome low stale per key starts 1274.1, band fresh 1319.1 for all 20 keys, last keydown 1034.9; Firefox low 1296.2 / 1341.9 / 1048.8; Chrome high per-key stale 72.2–87.2 (first 13.9, last 281.0), Firefox high 69.6–82.6 (one 11.6, last 286.3); `persistent` 0 ×4.
- `131/ghost-20-ab/host-0.2.12-…/report.json`: Chrome low 1005.7 / 1049.6 (key 20: 1256.4), Firefox low 1114.8 / 1160.5; high worst 562.9 / 465.2; `persistent` 21778 / 13843 / 22753 / 13843.
- `131/ghost-20-ab/host-0.2.13-prefix-…/report.json`: Chrome low 1030.0 / 1072.7, Firefox low 1188.0 / 1234.1; high worst 138.6 / 77.8; `persistent` 20606 / 47938 / 23122 / 13748.
- `128/final-0.2.13-131fix/report.json` (4-key cells): single 13.4–31.6 all ≤ 40; rapid Chrome high [15.3, –, 80.3, 23.8], Chrome low [167.1, –, 100.5, 25.2], Firefox high [77.3, –, 76.2, 85.1], Firefox low [220.5, 154.5, 153.2, 89.0]; `persistent` 0 ×4.
- `131/131-B/report.json`: same arms [27.6, –, 79.8, 22.5] / [213.9, –, 148.1, 15.4] / [76.8, 10.7, 75.1, 85.7] / [223.8, –, 156.9, 90.6]; 20th-key delete time Chrome 310, 321, 311, 323, 318, 320; Firefox 269, 267, 269, 270, 265, 271. Slope re-derived: Chrome (310−45)/19 … (323−46)/19 = 13.9–14.6 ms/key; Firefox from 65–73 to 265–271 = 10.1–10.8 ms/key (§9.14 says 11–12; the difference is where the start is taken — immaterial).
- `128/final-0.2.13/report.json` (pre-fix 4-key cells): Chrome high [17.2, –, 13.8, 16.6] `persistent` 21778; Chrome low [90.5, –, 24.6, 24.1] 13843; Firefox high [76.8, 10.9, 73.8, 84.6] **0**; Firefox low [96.4, –, 29.3, 32.3] 13843.
- Identity of every run from each report's own `static` block (not the READMEs): ghost-20, 131-B and the 128-B re-run served page `d761f1ce…` / buildId `59e6a9fe…`; the A/B arms served `8909564e…`/`45cdcedf…` and `c7f904fa…`/`0574b1b1…`; the pre-fix 128-B run `c7f904fa…`/`0574b1b1…`.
- 121-B: the four JSONs under `findings/evidence/121/0.2.13-131fix-*.json` read directly; binding file reads `d761f1ce…` at 09:03:49Z and 09:05:09Z; §9.13's commit `4ebfb604` is dated 09:03:44Z (git), i.e. before the run.
- Geometry from the fixed-page report: desk 820 (Chrome) / 834 (Firefox) px, bands of 1,023 rows, `high` caret row 229 (band 0), `low` caret row 1338 (band 1).

Not re-derived (taken from the record): 0.2.12's original "125–283 ms" (128 README, different reader over `chrome-1.json`/`firefox-1.json`); the rapid-ab refusal counts 4/80 and 19/80 and the red control's 5/20 per browser (`131/red-control/` not opened); the host-segment numbers (23.6 / 31.4 ms PASS, 2780 / 2767 FAIL) from the README; `judge_131b.py` not re-run (its committed `judge.txt` was read: 12 bursts `deleted 20 refused 0 other []`, exit 0).

## 1. Mechanism, read in code (confirms the brief's reading; two corrections)

- `renderDocument` asks only for bands overlapping the window and stale (`e2-editor-app.js:1197-1198`), ordered by `bandOrder` — distance 0 for every band under the view, tie broken by index (`:1122-1130`). So with the view straddling bands 0 and 1, band 0 is always asked first.
- A key that will reach the engine sets `renderAgain` while a pass is running (`:2355-2356`), and the pass breaks before the next band (`:1200`). In a burst a pass therefore paints band 0 and stops; band 1 is never reached until no key arrives during a pass. That is H2, and it is the whole of the `low` arm on all three pages (band fresh at one instant for all 20 keys). It is independent of rule A and of remedy B.
- `run()` awaits `renderDocument()` (`:1746`); the per-key cost in a burst is one delete plus one band-0 paint in the same Worker — the ramp (132). 0.2.12's BUSY back-off (120 ms with `rendering` held) made most of those paints not happen, which is why 0.2.12 is flat at 41–50 ms/key: it was faster because it was not painting.
- Correction 1 (to §9.14 "修好的頁面比修法前慢一倍多"): the pre-fix 4-key numbers are refusal artefacts. In the pre-fix run every `–` coincides with a non-zero `persistent` (Chrome high key 2, Chrome low key 2, Firefox low key 2), and keys 3–4 of those arms read 24–32 ms = settled single keys: the refusal returned at once, the queue drained, the repaint got in. The one pre-fix arm with no refusal (Firefox high, `persistent` 0) reads 74–85 ms per key — the same as the fixed page's high arm (76–86). Rule A did not slow the 4-key case; it removed the refusals that made the pre-fix numbers look fast. (Rule A does lengthen the low-arm hold: +23.7 % Chrome / +9.1 % Firefox vs pre-fix, +26.7 % / +16.3 % vs 0.2.12 — "about 20 %" in §9.14 is a rough mean; the Firefox-vs-pre-fix figure is 9 %.)
- Correction 2 (instrument semantics, bears on wording): `lag_per_key` (`probe_hand_test_0212.py:335-357`) takes `moved` = the first sink move inside the key's own 50 ms window and `fresh` = the first band label ≥ the counter seen in that window, searched to the end of the log. In the low arm the band is painted once, after the burst drains, so every key's `staleAfterCaretMs` = (end of burst + backlog + one repaint) − (a caret move in that window). It is linear in burst length: 4 keys read 167–224, 20 keys read 1274–1296. "4 keys ≈ 225 ms" is a property of the instrument's burst length, not of the product. The last key's 281/286 in the high arm is the same thing (its window runs to the end of the log) — it is the backlog, not a second ghost. `–` has two causes: on the pre-fix page a refusal; on the fixed page the queue (the key's own delete ran after its 50 ms window; `refused 0`).

## 2. Q2′ — attack on A, and why A′ rather than C

Attack on the main session's A, honestly:
1. "0.2.12 does the same" is true (1006 / 1115 ms) but the owner's 128 report says only 「殘影」; the 128 README reproduced the single-key 120 ms and treated that as the cause. If what the owner actually saw was a held key, 0.2.13 ships with the owner's complaint intact and 9–27 % longer, under a finding marked fixed. This is a real risk to A; the answer is not C but honesty: the limit must be worded in the owner's terms and the owner's hand test must include the hold (§4 below).
2. A's wording "4 keys: up to about 225 ms" is a hand-enumerated number for an arbitrary burst length (correction 2). It would be false for 5 keys. Rejected; the limit is worded structurally.
3. A's "re-read the clause as written → limit" leaves a criterion on the books whose ≤ 60 ms bound no page has met without a refusal (pre-fix three of four arms over 60; Chrome high's 17.2 had a refusal at key 2). A criterion nobody can meet is withdrawn under house rule §4, not dispositioned.
4. 132's ramp is a regression vs 0.2.12 in kind (keeps up → falls behind at 50 ms), and it compounds with the low-arm ghost into over-deletion after release (Q5). A says "post-release" without naming that; the registration must.

Why not C (do not freeze until the hold ghost is fixed): (a) it is the shipped 0.2.12's band order (H2), not introduced here; (b) the two fixes are new mechanisms — caret band first needs the caret position in `bandOrder` and reopens 122-U B2; coalescing reopens `run()`'s wait — each needs its own spec, A/B and prediction, and reopens 122-B, 128-B, 129-B, 130-U, 121-B, 131-B; doing that inside this freeze is exactly "a new mechanism at the last step"; (c) 0.2.13 carries autosave, 129, 130, 121 and the 131 data fix (the two pages without rule A left characters in the document in every 20-key burst: `persistent` 13748–47938; the fixed page 0 ×4). Holding a data fix for a transient ghost that the shipped version already has is the wrong trade. Verdict A′.

What A′ changes relative to A: the clause is withdrawn (not re-read); the limit is structural; 131-B's `persistent` is named as the guard of transience; the post-release spec is required to A/B two mechanisms separately and to measure the real auto-repeat rate first; the owner's hand test includes the hold.

Plain reason for the owner (English; the zh-TW version is in the spec text): When you hold Backspace with the caret below a dividing line that moves as you scroll, the screen does not change while you hold, and the characters vanish together about a third of a second after you let go. 0.2.12 already does this (about 1.0–1.1 s for a 1 s hold); the fixed 0.2.13 does it for about 1.3 s because every key now really executes. Without that fix, a 1 s hold leaves a character or two undeleted in the document — that is a data problem; the ghost is a display problem. Blocking the version that fixes the data problem over a display problem the current version already has is the wrong trade. Removing the ghost means changing the repaint order, which is a new mechanism and goes in its own spec after this release.

## 3. Q2′b — criterion form

The 4-key clause is per-instance in form, but its premise is false on two counts: 4 keys at 50 ms does not stand for a held key (the number scales with burst length and depends on which band holds the caret), and ≤ 60 ms was never met by any page without a refusal. Withdraw it (CLAUDE.md §4). Do not write a replacement rapid criterion into 0.2.13: one the fixed page passes (e.g. "all bands fresh within 0.5 s of the last key", measured 284–293 ms) would be written after seeing the data and cannot count; one it fails is C. Transience ("it goes away when the keys stop") is already guarded by 131-B's `persistent.differing == 0` in all four high/low arms — the before/after pixel comparison with the caret back in place catches a ghost left on the canvas as well as a character left in the document; it is a hard criterion with 「若永遠沒做：0.2.13 不凍結」. Duration has no guard in 0.2.13 and is registered as such (house rule §3: behaviour with nothing guarding it, instrument exists). The hold criterion belongs to the post-release spec and must be written before that spec's first run; its shape is given in §9.17 below.

## 4. Q4 — the 121 witness substitution

Sound. The withdrawn clause's premise (the instrument reads the engine's shape) was false: it read `#toolbar[data-selection-shape]` = `lastSelectionShape`, which keyboard deletes never write (`e2-editor-app.js:2294-2299` says so), so it is `range-single` on every page. Withdrawing beats exporting the engine's shape to the DOM (product bytes; a guard for its own sake). 121-B is 121's own instrument (`findings/evidence/121/select_delete_probe.py`, SPEC-M3-production-ui §15.2, red case on record) and verifies the claim itself — the selected text is absent from the saved first paragraph — plus the delete-selection latency line, `ready`, generation 1→1, revision 0→1, no toast; 4/4 on `d761f1ce…` with the binding read before and after; the spec rewrite (`4ebfb604`, 09:03:44Z) preceded the run (09:03:49Z). The first run's other two clauses stand; `selection-arms.txt`'s `121-witness FAIL` line stays as the record of the misread.

One registration, not a gate: what the withdrawn clause would have caught had it been readable — "after a range delete returns, the engine's shape is collapsed, so the next Backspace goes out as `delete-backward` and is not refused" — is measured by nothing (121-B stops at the save; 131-B's bursts start from a caret). Mechanism says it holds (the drain reads `getState()` after the action, `editor-session.js:301-311`), unmeasured. Register NOT_ESTABLISHED with a work item (a `selection_arm` followed by one Backspace, both browsers), not as a hole the substitution opened: it was never measurable.

## 5. Q5 — finding 132

Not a blocker, post-release, for the reasons the first ruling gave and which still hold: bounded by the burst, self-clearing, no data lost (131-B 12/12 bursts 20/20, `persistent` 0 ×4). The Chrome miss (310–323 vs 150–250) is a model error of ~60–73 ms, not a different mechanism. But the registration is incomplete in four ways that the owner must see:
1. It is a regression vs 0.2.12 in kind at 50 ms spacing (flat 41–50 ms/key → +10–14 ms/key), and it is the cost of 128's remedy B; pre-fix 0.2.13 had it too, reset by refusals.
2. A real held key repeats at about 30 ms (the probe's own comment, `probe_hand_test_0212.py:362`), not 50. With a per-key cost of 61–64 ms the backlog grows 31–34 ms per key at 30 ms spacing — about the hold length itself (hold 1 s → deletion continues ~1 s after release). Arithmetic, not measured; 0.2.12 would also fall behind at 30 ms (11–20 ms/key by the same arithmetic), about half as much.
3. The action queue has no cap (`editor-session.js:262-266` pushes unconditionally; the 「佇列滿」 notice of 130 belongs to the input adapter's text queue, not re-verified here). So the consequence of a long hold is over-deletion, not dropped keys: in the low arm the screen shows nothing while holding, and after release the queued deletes land. Undo exists (`session.undo()`, `e2-editor-app.js:2042`); how many characters one undo recovers is unmeasured.
4. The post-release spec must measure the real rate on 0.2.13 first (an instrument parameter for the gap, default 0.05 unchanged — an instrument change under §34, not a check fix), then A/B two mechanisms separately, with a per-instance criterion written before its first run.

The owner's hand test after freezing must include a ~2 s hold with the caret in the lower half of the screen; what the owner sees is appended as an observation. Whether to ship with it is the owner's decision; if the owner rejects it, that is the C path (new mechanism, new generation), not an edit to the registration.

## 6. Release steps, in order

0. Save this ruling verbatim as `findings/evidence/128/ruling/fable-ruling-2.md`; append §9.15–§9.17 below to `specs/SPEC-M3-autosave.md`; commit both. No page byte changes: v62 freezes on `d761f1ce…`, engine `59e6a9fe…`.
1. 129-B lands (round `findings/evidence/129/final/round-20261012T092119Z/` is on disk, untracked): judge per §9.4; any red stops here and goes back to the page, not to a criterion edit.
2. 128-B disposition recorded as: single ✓, host segment ✓ with red control ✓, rapid clause withdrawn → L-128-rapid registered (evidence already on record: `128/final-0.2.13-131fix/`, `131/ghost-20/`, `131/ghost-20-ab/`). No re-run.
3. Verify `dist/e2-editor-app.js` sha256 is still `d761f1ce…` and `check_engine_decoded.py` passes; freeze shell generation v62; write the pin; commit host 0.2.13 (`appinfo/info.xml` is currently uncommitted per every report's `hostDirty`).
4. Start the count chain (six M3 runners with the two cells registered in §9.4, production UI, product path) on the frozen bytes.
5. In parallel, on the same frozen package: the owner's hand test as for 0.2.12, plus the 2 s hold with the caret in the lower half; the observation is appended (§9.18). If the owner rejects the hold behaviour, the count is moot and the work goes to the post-release spec first.
6. After the count: open the post-release spec (one document, two mechanisms: caret band first; coalesce repaints while deletes are queued), first step the real-rate baseline on 0.2.13, criterion written before the first A/B run.

## 7. Spec text to append

Appended to `specs/SPEC-M3-autosave.md` as §9.15–§9.17 (zh-TW); not repeated here.

## Sources read (path:line)

- findings/evidence/128/ruling/brief-2-q2-premise.md:1-36
- findings/evidence/128/ruling/fable-ruling.md:1-45
- specs/SPEC-M3-autosave.md:111-124 (§5), :252-346 (§9.4–9.8), :428-520 (§9.12–9.14)
- specs/SPEC-M3-production-ui.md:573-600 (§15.2–15.4), :631-688 (121-B reruns)
- findings/evidence/128/README.md:1-50 (H2 at :50)
- findings/evidence/128/final-0.2.13-131fix/README.md:1-18, cells.txt, selection-arms.txt, report.json (`static`, re-derived cells)
- findings/evidence/128/final-0.2.13/report.json (re-derived pre-fix cells, `static`)
- findings/evidence/131/131-B/README.md:1-9, judge.txt, ghost-arms.txt, burst-times.txt, report.json (re-derived)
- findings/evidence/131/ghost-20/read.txt, report.json (re-derived; `static`, geometry)
- findings/evidence/131/ghost-20-ab/README.md:1-15, log.txt, host-0.2.12-engine-45cdcedfc0fe7e61/{read.txt,report.json}, host-0.2.13-prefix-engine-0574b1b157ce1e1e/{read.txt,report.json} (re-derived; `static`)
- findings/evidence/131/read_ghost_long.py:1-28, read_128b_cells.py:1-9, read_burst_times.py:1-21
- findings/evidence/121/0.2.13-131fix-binding.txt, 0.2.13-131fix-{chrome,firefox}-{backspace,delete}.json, select_delete_probe.py:4-50
- wasm_sdk_probe/web/e2-editor-app.js:101 (engineActionsOut), :210 / :1091 (band height), :1122-1130 (bandOrder), :1138-1147 (visibleDocRows), :1149-1293 (renderDocument; BUSY :1266-1275), :1559 (SESSION_ACCEPTS), :1737-1747 (run), :1854-1885 (editorAction), :2042 (undo), :2233-2236 (DELETE_INPUT_TYPES), :2287-2326 (121/131 listener, deleteActionFor), :2348-2358 (ENGINE_INPUT_TYPES, endRenderPassOnInput)
- wasm_sdk_probe/editor-shell/editor-session.js:250-270 (_enqueue, no cap), :279-335 (_drain)
- wasm_sdk_probe/tools/probe_hand_test_0212.py:269-384 (rapid_arm, keys_at, lag_per_key, ghost_arm; "about 30 ms" at :362)
- git: 6326d31b (rule A, 1 file, +21/−4), 4ebfb604 / d618a45d / 76bcd8de timestamps, log -8
