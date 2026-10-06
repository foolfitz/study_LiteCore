# Handoff, 2026-10-06g — the paragraph-merge spec is written and reviewed twice, R0 classified every case with no STOP, M1-3/M1-4/M1-5 and the lock check landed; R0b (anchor rectangle) is next, then the engine header

Entry points: this file; `specs/SPEC-M3-paragraph-merge.md` (§1–9 original; §10 dispositions of the first two-seat review; §11 P4 source argument; §12 typed text compared by paragraph text; §13 second opus review: anchor fence + lock order — **§10–13 SUPERSEDE parts of §3–4, read them**); `findings/evidence/merge-native/README.md` section "R0"; `findings/evidence/merge-native/PREDICTION-R0.md`; `handoff/tasks/REVIEW-2026-10-06-paragraph-merge-spec.md` (the review brief). Picks up from `HANDOFF-2026-10-06f-b-restores-in-two-presses-spec-not-written.md`. Session ended because the context passed its soft limit, not because of a blocker. Nothing is running. Tools named below live under `wasm_sdk_probe/tools/`.

## Commits (newest last)

| Commit | What |
|---|---|
| `30d12a45` | Spec: option B designed and its criteria written before any code |
| `404dfb6d` | Spec §10: dispositions of the first two-seat review (opus + codex) |
| `977243a2` | Spec §11: P4 read from source, holds (bounded) |
| `08bb5cce` | Spec §12: typed text is compared by paragraph text, not bytes |
| `9bc0a851` | R0 instruments and predictions (before the run) |
| `58c736b5` | Spec §13: second opus review (anchor fence, lock order) |
| `106eaf1a` | M1-3 / M1-4: shell accepts `verified-key-undo`, worker forwards `keyUndo` and `mergeKey` |
| `525dcffe` | M1-5: page words a boundary refusal by `mergeKey` |
| `0d42628f` | Lock-scope static check (`check_engine_lock_scopes.py`) |
| `fa65a20a` | R0 results |
| `dcbed256` | R0b instruments (not run, no predictions yet) |

## Design state (spec, after both reviews)

- B is entered only for units containing 10, 13, U+2028 or U+2029, and only from the TEXT_SELECTION callback branch, never from the 250 ms deadline branch.
- Restore attribution is anchored to the callback stream and decided on the LOK thread. P = last caret delivered before the unit's non-empty TEXT_SELECTION; U = first caret after it; press-1 evidence = first caret after the collapse callback; press-2 evidence = first caret after posting press 2 that differs from the known caret; at most two presses.
- **FENCE (§13.1, adopted, not yet confirmed by measurement):** the anchor-side selection rectangle from the unit's own flush (TEXT_SELECTION_START for Shift+Right, _END for Shift+Left; computed at flush time, `SwShellCursor::FillStartEnd`) must equal P on (x, y, height), else refuse `keyPosted:false` stage `"anchor-mismatch"`. It replaces the insert-fallback refusal. Reason: a click (handleClick replies before LOK processes the mouse events; placeCaret can return early) or an insert fallback still queued makes P stale even with P1–P4.
- Premises: P1 (user events are FIFO), P2 (caret payload computed at flush time, deduplicated), P3 (selection before caret in one flush) verified from source; P4 (no flush during one arrow key) argued from source, bounded (§11).
- Clock guard WITHDRAWN (§10.1(b)): a new action changes the payload unless all 100 entries are identical. `keyUndo` fields: `comment, actionsBefore, actionsAfter, restorePresses, keyToUndoMs, codePoints`.
- P_start (payload read at transaction start) must equal P0 (restore changed nothing), else stage `"restore-mutated"`.
- `key-deadline` (2000 ms, payload re-read at the deadline) → `EDITOR_BOUNDARY_UNSUPPORTED` + `mergeKey{keyPosted:true}`. Promise: typed text survives, the key's effect is uncertain. The message must not contain "no mutation was dispatched". Every exit after the key is posted carries `keyPosted:true`.
- The shell accepts `verified-key-undo` structurally (`keyUndo` object, `actionsAfter` integer >= 1), **not** on Writer's comment string — a rejection there is `EDITOR_RESULT_INVALID` → rollback → loss.
- Lock order (§13.2): no LOK API and no `emitJson` / `MAIN_THREAD_*` while holding `gState.mutex`.
- Compile guard: `OXSDK_MERGE_KEY_UNDO` together with `OXSDK_MAINLOOP_ENGINE`, or without `OXSDK_FINDING_016_SELECTION_BARRIER`, is an `#error`.
- Typed-text comparisons (follow char, M2-1b, M2-3) compare paragraph-text sequences (`tools/odt_paragraphs.py`): typed text carries a per-session random rsid and WASM types by paste.

## R0 results (native, `.odt` inputs; `classify_merge_r0.py`, no STOP)

- Classes: merge 30; typed-merge 2 (Y01, Y02); restore-refused 2 (C15, C16); key-noop 1 (C17); nothing-selected 2 (C29, C30); barrier 1 (G01).
- Restore presses were 2 for exactly I02 C08 C10 I03 I01 Y02 P27 E13 P62 P63. Follow text `Z` landed identically to Writer's key everywhere.
- H03 (default limit, 105 presses): 321 presses, 0 payload disagreements. G14: 0 disagreements.
- G13: press 33 (the third folded line break) changed the document but not the payload, 3/3 — predicted. v15 will `key-deadline`-refuse that shape (registered, honest).
- **Predicted wrong by one:** full stops stop changing the payload from press 19, not 20 (ShortenString's `...` filler is itself full stops).
- PMPC documents stay under `wasm_sdk_probe/build/merge-native-pmpc/r0/`; limit/grouping documents also under `build/`; limit arms are gzipped in evidence.

## What landed in code (all JS tests 173/173 at `525dcffe`; red cases run before each commit)

- **M1-3** (`106eaf1a`): the v1/v2 client matrix declares the `verified-key-undo` divergence for the two deletes, 5/5 mutants red. Session tests: a `keyPosted` refusal in 3 start states x key applied/not keeps every typed change; removing the refusal checkpoint goes red.
- **M1-4** (`106eaf1a`): first worker event-forwarding tests (vm loads the real `sdk-worker.js`). `keyPosted` missing or non-boolean → `true` (fails toward "posted"); 4/4 mutants red.
- **M1-5** (`525dcffe`): page `boundaryText` / `boundaryKeyUncertain`. "文件沒有被改動" only for stages known to be pre-key and pre-mutation (fail-closed set `MERGE_KEY_UNCHANGED_STAGES`). The error is passed into `reopenAfterBoundaryRefusal(error)`. BUSY render retries 6→84 (about 10 s). 5/5 mutants red (one survived first; assertion added). `workerUrl` and `PINNED_WASM_SHA256` are still v8 — they move only after the link.
- `0d42628f`: `check_engine_lock_scopes.py` (12 lock scopes, 0 violations today, 4/4 red cases). **Not yet wired into `make test-e2-c-static`** — do it when adding the v15 Makefile rules.
- `make e2-c-assets` was run (two `cp` into `dist/editor-shell-v2`, gitignored). **`make test-e2-c-static` is RED by design** (shell bundle manifest out of date: client and session changed). It is resolved by freezing shell generation v56 once this round's shell changes are complete. Do not freeze before the engine side settles.
- `c41e8582` confirmed (inference, three corroborations) as v8's link commit: v8 objects compiled 00:29 after `c41e8582` (00:20), profile packed 00:31, the next commit `be014393` touched no src/sdk/Makefile, worker sha `070229cd` equal.

## What is next (in order)

1. **R0b.** Write `PREDICTION-R0b.md` BEFORE running. Predict from source: caret rect = `SwVisibleCursor::SetPos` char-rect position with cursor height and width 0; selection ends = `GetCharRect` layout rect; x and y expected equal, height uncertain. Run all three R0 case files, one round each is enough (`MERGE_RESTORE_PRESSES=2`), owner's document under `build/`. Then `tools/check_merge_anchor_rect.py <round dirs>`. All agree on x, y, height → implement the fence as written. Any disagreement → append to the spec before writing engine code (e.g. compare (x, y) only, with the measurement that forced it).
2. **Engine:** `src/merge_key_undo.hpp` (pure logic) + a native test generated from an event model (M1-2, as amended in §10.2 / §13); then the engine glue behind `OXSDK_MERGE_KEY_UNDO`; the M1-1 tool (every TU of every profile rule, a floor on rules found, illegal define combinations fail); `RUNBOOK-relink-v15`; owner links (archive first).
3. WASM shakedown, bindings, counted M2 runs, host 0.2.8, R.

Consider an opus adversarial review of the header + model test before the link.

## Registered / open (spec §8, §10.4, §13.3)

- Finding 111 changes class with B (a silent wrong merge).
- `keyPosted:true` has never been exercised on the real host.
- EditEngine text (comments, draw text): B must refuse when observable (e.g. graphic selection non-empty).
- COMPLEX units are excluded.
- 250 ms under LOK load degrades B to refuse+reopen and burns Worker generations.
- Hide-changes mode unread. v14 has no B.

## Things this round taught

- Two review rounds each found a way B would press the key in the wrong place and report success (stale P from typing; an unsolicited idle-layout caret; then stale P from a queued click). Each was a premise the previous fix silently relied on. The fix that held moved the truth into the unit's own flush (the anchor rectangle) instead of adding conditions.
- A mechanism that maintained a stronger claim than needed (the clock guard) was what the reviewers broke three ways, and it carried an unbounded wait. Withdrawing the claim removed both.
- The reviewers' diagnoses were checked against source before adoption. Two codex BLOCKINGs were accepted in substance but resolved by an honest promise (`key-deadline`) instead of new machinery.
- Byte equality is impossible for anything with typed text (per-session rsid). This was found while building R0, before any comparison was trusted.
- A prediction can be wrong in a way that teaches about the instrument: 19 vs 20, because the ellipsis filler is itself a full stop.

## Standing rules (carried from 06e/06f, plus two new)

- Never two M3 runners (or an M3 probe) at once; each clears the whole `oc_files_lock` table.
- Counted runners refuse a dirty host tree; a host JS change means an `info.xml` bump + `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`; the buildId is content-addressed.
- A runner changed after its pin is a new pin (append to the spec), or its reports do not count; the locks runner's pin is `1d3099a2…` (§12.1). `check_m3_same_second.py` and `probe_m3_save_throw.py` import `open_from_files` from it.
- `findings/evidence/**` and `handoff/**` English; specs, findings' prose zh-TW; specs append-only.
- Native probes load a per-round copy of the fixture, never the fixture itself.
- Never `pkill -f` with a pattern that also matches your own shell command line.
- Never edit `tools/run_merge_native.sh` or the probe while a runner batch is queued or running — each invocation recompiles.
- The owner's PMPC document never enters the repository; rounds on it run under `wasm_sdk_probe/build/` and only arms/summaries are copied into `findings/evidence/`.
- **New:** never compare typed-text documents by bytes; compare paragraph-text sequences.
- **New:** the shell generation is frozen only when the round's shell changes are complete.
