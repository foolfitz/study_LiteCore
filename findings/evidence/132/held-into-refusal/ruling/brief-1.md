# Brief 1 — L-132-held-into-refusal: which prescription (owner-delegated ruling)

**Owner's authorisation (2026-10-13, verbatim):** 「發給fable，我授權他帶我裁決」 — you rule on the owner's behalf for this one decision. Not durable beyond it.

**Return format:** `RULING` / `WHY (for the owner, 台灣正體中文白話, ≤15 lines)` / `FACT CHECK` (each F below: holds / wrong / unverified, with file:line) / `CONDITIONS` (numbered, each checkable). Write it to `findings/evidence/132/held-into-refusal/ruling/ruling-1.md` (English except the WHY block). Do not edit product bytes (`wasm_sdk_probe/web/**`, `dist/**`, host repo), do not run browsers, do not commit. Reading anything is fine.

## Where we are

- Product: LiteCore editor page `e2-editor-app.js` (served page `abe93f45…`), shell v64, host app 0.2.15 (`568608c`) = **uncounted candidate** (full count deferred to the next engine-changing batch, owner 2026-10-12). Owner hand-tested 0.2.15: pass (spec §12).
- Finding 132 (held Backspace falls behind the key) is fixed by H1–H3 (`specs/SPEC-M3-held-key.md` §3). §9 S1 registered **L-132-held-into-refusal** as a named limit only. Owner then chose "A = measure it first" → spec §13 (mechanism, three arms, predictions, written before any run; commit `47a42f5f`).
- Read §13 in full before ruling (`specs/SPEC-M3-held-key.md:184-230`). §13.4 names the two candidate prescriptions from §9: **B** (page: after a refusal, drop the rest of the same hold's Backspace/Delete repeats until keyup, same shape as H2) and **C** (engine: do nothing at the two document ends instead of refusing; needs a link, goes into the link batch).

## Measured (probe `probe_held_into_refusal.py`, `run-1/report.json`; desk repeat delay 500 / interval 30 ms, hold 8 s, owner-document copy, 211 paragraphs)

Reader: `python3 findings/evidence/132/held-into-refusal/read_report.py findings/evidence/132/held-into-refusal/run-1/report.json`. Reproduce my numbers from the report, do not copy them.

| browser | arm | refusals at (ms from first keydown) | generations | ready in new gen (ms) | limit `saved` (ms) | server |
|---|---|---|---|---|---|---|
| chrome | start-press r0 | 260 | 1→2 | 1306 | — | same as original, `zqx` ×1 |
| chrome | start-hold r0 | 1161 / 3093 / 5262 | 1→2→3 | 2239 / 4363 | 5351 | same as original, `zqx` ×1 |
| chrome | start-hold r1 | 1157 / 3109 / 5113 | 1→2→3 | 2236 / 4208 | 5192 | same as original, `zqx` ×1 |
| chrome | end-hold r0 | 797 | 1→2 | 1883 | — | **firstDiff para 0, −82 chars, 211→210 paras**, `zqx` ×1, saved |
| chrome | end-hold r1 | 792 | 1→2 | 1854 | — | **firstDiff para 0, −83 chars, 211→210 paras**, `zqx` ×1, saved |
| firefox | start-press r0 | 256 | 1→2 | 2243 | — | same as original |
| firefox | start-hold r0 | 1270 / 4210 / 7108 | 1→2→3 | 3224 / 6201 | 7210 | same as original |
| firefox | start-hold r1 | 1276 / 4136 / 7021 | 1→2→3 | 3214 / 6092 | 7107 | same as original |
| firefox | end-hold r0 | 868 | 1→2 | 2816 | — | **firstDiff para 0, −71 chars, 211→210 paras**, `zqx` ×1, saved |
| firefox | end-hold r1 | 832 | 1→2 | 2780 | — | **firstDiff para 0, −72 chars, 211→210 paras**, `zqx` ×1, saved |

Probe exit 0, all 10 rounds; `static` and `staticAfter` identical (host 0.2.15 `568608c`, served page = dist page `abe93f45…`).

Against §13.3's predictions (written before the run): every arm on both browsers lands inside the predicted ranges; none of the "would change the plan" outcomes occurred. (i) holds: a held Backspace at the document start burns all three Worker generations in 5.2–5.4 s (Chrome) / 7.1–7.2 s (Firefox), ends at "please reload", no data lost. (ii) holds on both browsers: one refusal, then the held Delete deletes **from the document start** (gen-2 revision span = chars deleted + 1 paragraph join: Chrome 0→83 / 0→84, Firefox 0→72 / 0→73), and the change is saved to the server. Firefox deletes fewer because its restart takes ~2.8 s vs ~1.9 s, leaving less of the 8 s hold.

Probe defect (not product): `deletesSeen` undercounts by one — the first delete's revision bump arrives while the latency label still names the previous action (`probe_held_into_refusal.py:128-130`). The server diff and the revision span are authoritative.

## Claims to verify (mine; attack them)

- **F1** Restart puts the caret at the document start, and nothing restores the pre-refusal caret: `e2-editor-app.js:1676-1686` (comment "a restart puts at the document start", `focus({preventScroll:true})`, no placeCaret after `session.restart()`).
- **F2** §13.1 says (ii)'s deletion is "not on screen". **Unverified and probably wrong**: `followCaret()` (`e2-editor-app.js:810-825`, 124's fix) scrolls `#desk` to centre the caret whenever the caret rectangle changes and is out of view, so after the restart the view likely jumps to the document start and the user watches the start being eaten. The probe did not record `scrollTop`. Severity of (ii) depends on this only partly — the document is changed either way.
- **F3** (ii) is not specific to holding the key. After ONE refused Delete at the end (single press), the caret is at the start (F1); the user's next separate Delete press, or any typed text, lands at the document start. H2/B do nothing for presses (`repeat === false` always goes out, `e2-editor-app.js:2579-2583`). Unmeasured; follows from F1 if F1 holds.
- **F4** Therefore **B alone does not close (ii)**: B drops the rest of the same hold, but the caret is still at the start for the next press / next typing (F3). B does close (i)'s run to the generation limit within one hold.
- **F5** **C alone** removes both (i) and (ii) for the two document ends (no refusal → no restart → caret stays), and also the start-press cost (one generation per single press, which neither B nor a caret fix removes). But C needs a link (engine), so it ships only with the next link batch; owner rule: prefer what needs no link, collect engine changes for one link (memory `short-term-goal-is-a-usable-editor`). C does not cover refusals that are not at the ends (tables, `anchor-mismatch`; v19 refuses only at the two ends on this document per SPEC-M3-production-ui §13.2, tables unmeasured).
- **F6** A third page-only option exists that §9 did not list — **D: after the boundary restart, put the caret back** (e.g. `session.placeCaret` at the pre-refusal caret rectangle, the same call `moveFromPoint` uses at `e2-editor-app.js:2592-2604`; the document after restart is the checkpoint of the same content, so the same twip point should map to the same position). D closes (ii) and F3 for single presses and typing; it does not stop (i) (caret back at the start → the held Backspace refuses again). Unverified: whether the restored document's layout is identical so the point lands in the same place; whether placeCaret at the end-of-document caret rectangle lands at the end.
- **F7** My lean: **B + D now (page only, no link), C queued for the link batch** as the real fix for the ends; with C landed, B and D become dead paths but harmless. Cost of B+D: two small page changes, each with its own unit/browser criterion; page bytes change → new shell generation + host bump, counting stays deferred per §9.21 rules. Alternative lean I rejected: D only (leaves (i)'s 5–7 s run to "please reload" — no data loss, but a session ended by a held key).
- **F8** (ii) is now a measured data-changing defect, not a named limit. Should it become its own finding number (next free: 134) rather than staying under L-132-held-into-refusal? My lean: yes — it predates 132's fix (the restart-at-start path dates from 109's fix, 2026-10-06), so it is not a 132 regression; check with `git log -S'reopenAfterBoundaryRefusal' -- wasm_sdk_probe/web/e2-editor-app.js` and the pre-132 page `d761f1ce…`.

## What I am asking you to rule

1. Which prescription(s): B / C / D / combination / something else — and which ship now vs. with the link batch.
2. Is F2 worth measuring (scrollTop after the restart) before the fix, or is it irrelevant to the ruling?
3. F8: new finding or stays a named limit.
4. Acceptance criteria shape for whatever you choose (per CLAUDE.md "驗收判準的形式": per-instance or tool-closed, a default verdict if never run, a red case per criterion). The §34 stop rule applies (`memory checks-stop-rule-spec-34`): checks guard accidents only; count "fixed because of a run / because of a review" in the handoff.
