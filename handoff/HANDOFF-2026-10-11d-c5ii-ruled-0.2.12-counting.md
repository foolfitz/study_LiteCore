# Handoff, 2026-10-11d — C5 (ii) not held as written, C5 (ii)′ holds (fable's ruling); shell v61 frozen, host 0.2.12 bound; the pre-port `Rdel` witness is red as predicted; the 0.2.12 count chain is RUNNING and its results are NOT known

Picks up from `HANDOFF-2026-10-11c-cprime-in-main-next5-done-c5ii-running.md` (and its Addendum). Repository root
`/home/jiajun/LibreOffice/study_LiteCore`. Spec `specs/SPEC-M3-production-ui.md` §17.20–§17.22 (zh-TW) record
everything below; evidence READMEs are English.

## What happened, in order

| Commits | What |
|---|---|
| `b952e5f6` | `PREDICTION.md` correction 2, **before the re-run**: `geometry-declared-but-not-delivered` is a no-op on v14 (v14's manifest declares `documentOutlineGeometry`, so `Boolean(contract)` equals the original); its landing red case (`72f8de7f`) used v12. |
| `1e1082d7` | **C5 (ii) result, facts only (§17.20)**: 51 runs complete (03:56–09:59Z). By the committed rule, 44 of 47 ordinary mutations red → **not held**; three not red, each with a cause older than C′: geometry (wrong flag; the v12 re-run is red exactly as predicted, C1 only, `ok: true`); `inline-format-rollback` (dead since finding 059's engine fix of 2026-08-19; its owning check `a-failed-format-does-not-block-the-session` passes vacuously since then — a §3 "behaviour with no guard"); `rollback` (declared owner is the `recoveryPairing` sentinel, NE; caught by `recovery-returns-what-the-product-promised`, same four non-PASS cells as 0.2.9's run). Evidence `findings/evidence/c-prime/c5ii/README.md`, `reading.txt`, `read_c5ii.py` (ad-hoc listing). |
| `e6a83791`, `fd39038b` | Owner chose 「交 fable 裁決」. Brief `c5ii/ruling/brief-c5ii-three-not-red.md`; ruling verbatim + the main session's line-by-line check `c5ii/ruling/fable-ruling.md` (one wrong line number in the ruling: the dead-session `ok=False` override is `run_e2_c_product_path.py:9792-9794`, not `:9775-9781`). **§17.21: C5 (ii) as written not held; C5 (ii)′ = every mutation live on C′ under the flag its own red case used is red, 46/46, plus one dead since 08-19, registered — the release step may start.** `rollback` keeps its declaration and gets a §17.10-style reading; the v12 geometry run counts; three items (inline-format-rollback's `expectedToBeDetected: False` + the check's NE, rollback if ever, geometry's profile) go into **one future runner opening** after the 0.2.12 count (因執行而修 6 → 7 then; 因審核而修 stays 5). Drafter ledger (three mispredictions) in §17.21, not in `CLAUDE.md` (owner's call). The optional P-page run was not done (the load-bearing claim is shown by `git show --stat` of C′'s commits). |
| `80294630` | **Shell generation v61 frozen** `f48df85b…`: differs from v60 only in the page (`8909564e…`) and the date; static before = only the manifest failure, after = exit 0; E1-C intact; v60 untouched. |
| litecore `b245ae7` | **Host 0.2.12**: `engine/` repackaged by `tools/package_m3_engine.py` (buildId `45cdcedfc0fe7e61`; vs 0.2.11 only `e2-editor-app.js` differs); 0.2.11's engine archived at `wasm_sdk_probe/build/archive/host-0.2.11-engine-b99f4b138839ff04/` (`diff -r` identical); `ddev occ upgrade` → 0.2.12. Not pushed. |
| `fb839ec1` | **Bindings (§17.22)**: six M3 runners re-pinned (12 pin lines only), static exit 0 after; product-path reader `findings/evidence/release-0.2.12/product-path/judge.py` (0.2.11's with the two page constants: v19 `8909564e…`, v8-repointed `0660beaf…` from the runner's own `repointed_page()`) and `PREDICTION.md`; chain scripts `findings/evidence/m3-production-ui/runs-0.2.12/{chain,red-cases}-2026-10-11.sh` (0.2.11's with paths changed). |
| `fa8b0ddb` | **Pre-count `Rdel` witness** (`findings/evidence/c-prime/witness/host-rdel/`): production UI `Rdel` with the pre-port `run_e2_c_page_smoke.py` and `check_m3_page_honesty.py` (`08d73cff`) on 0.2.12 — **red in both browsers, as predicted, by the predicted mechanism** (no refusal-and-reopen; the server's text differs from paragraph 42 of 211, about page 4). The page-smoke port now has its §34.4 witness. Attempt 1 restored only one file and died at import (kept in `attempt-1-import-error/`). |

## State

| Item | State |
|---|---|
| Product bytes | `web/` = `dist/` page `8909564eb2316afa…`; shell **v61** `f48df85b…`; host `litecore` **0.2.12** `b245ae7` (buildId `45cdcedf…`); engine v19 unchanged. |
| **Count chain** | **RUNNING**, detached (`setsid -w`), started 2026-10-11T10:41:28Z from tree `fa8b0ddb`. Order: six shakedowns (any non-zero = `STOP`; each runner's exit code is computed from its report verdict, a crash is non-zero), counted production UI (KR ×3; Bctl,S,P ×1; B3x ×2), the six counted, 12 product-path runs (v8/v19 × Chrome/Firefox × 3), then — only if the chain exits 0 — the red-case script. 0.2.11's took 4 h 50 min → expect about **15:30Z (23:30 CST)**. |
| Progress files | `wasm_sdk_probe/build/m3-count-2026-10-11/chain.txt` (ends `DONE` or `STOP:`); `wasm_sdk_probe/build/chain-2026-10-11.out` (ends `chain exit N`); `wasm_sdk_probe/build/red-cases-2026-10-11.out` (ends `red exit N`); `findings/evidence/release-0.2.12/product-path/chain.log`. |
| Constraint while it runs | Do not touch `web/`, `dist/`, `wasm_sdk_probe/tools/`, the litecore app or its ddev instance; no browsers; nothing CPU-heavy (rule vv); do not start other ddev projects (shared router 404s). Committing docs elsewhere is safe. |
| §34.4 | **因執行而修 6, 因審核而修 5** (unchanged this stretch; the future opening will make it 7 / 5). |
| Findings | 124, 125, 126: criteria measured on the final page; statuses are set at the end of this release step, each by its own criterion, not before. |
| Not pushed | study_LiteCore (`git rev-list --count github/main..HEAD`) and litecore — the owner's decision. |

## Next

1. **When the chain ends**, read `chain.txt` and the two `.out` files. Any `STOP:` = no counted run started: report which shakedown and why, change nothing. Product-path `exit 1` on Firefox is not by itself a problem (known `an-inline-format-reaches-a-selection` reds); `judge.py` decides. Read every M3 verdict from its report.
2. **Product-path verdict**: make `release-0.2.12/product-path/judge.py` red offline once on scratch copies (flipped v19 cell where v8 passes → P3 MISS; wrong v19 entrypoint → P2 MISS), as 0.2.11's `judge-red-offline.txt`; then `judge-output.txt`, and the descriptive old-vs-new v19 comparison against `../release-0.2.11/product-path/` (`old-vs-new-v19.txt`). **Watch item first**: Chrome `clear-format-removes-every-inline-format` NE in ≥ 2 of the 6 Chrome runs → do not read the verdict until diagnosed.
3. Write `findings/evidence/m3-production-ui/RESULT-0.2.12.md` modelled on `RESULT-0.2.11.md`, carrying the §17.21 line ("C5 (ii): 44/47 by the committed rule, not held (§17.20); C5 (ii)′ 46/46 live red + 1 dead (§17.21); runner `bd6fc0ca…` unchanged; 6/5; Chrome only"), the three registrations with their if-never-done defaults, and the drafter ledger. Append the result to spec §17 (zh-TW).
4. Statuses of findings 124 / 125 / 126, each by its own criterion (124-U/124-B, 125-U/125-B, C6's C′ half) and only if the count holds.
5. Tell the owner (台灣正體中文) and offer a hand test of 0.2.12: typing; arrows on a long document (the desk follows the caret, no 「處理中」 flash); a document past 33 pages at 150 % if their machine has it.
6. Later, registered not scheduled: the one runner opening of §17.21 (before the next census or mutation run that depends on those three).

## Open (new this stretch)

- `inline-format-rollback` dead since 2026-08-19; `a-failed-format-does-not-block-the-session` PASS is not evidence (§17.21 item 1).
- `rollback`'s runner `ok` is structurally false (dead session by construction) — its judge is the §17.21 reading, permanently.
- `geometry-declared-but-not-delivered`'s `requiresFlag` names no profile — run it on v12.
- Stale side declarations (no bytes): `caret-off-by-one-line` bulleting, `inline-format-rollback` bold, `save` notice-action.
- §17.19 calibration v0: `inline-format-rollback` marked dead; geometry's calibration is the v12 report.
- Carried unchanged: the previous handoff's Open list.

## Standing rules (new this stretch)

- **(hhh) A mutation's `requiresFlag` is not its live configuration; read the mutation's own landing red case for the profile.** Evidence: `geometry-declared-but-not-delivered` on v14 (no-op) vs v12 (red), `c5ii/PREDICTION.md` correction 2.
- **(iii) A reading precedent recorded in one release's PREDICTION is not carried by the runner; the next prediction must carry it explicitly.** Evidence: `rollback`, 0.2.9 → C5 (ii).
- **(jjj) Before a script restores files with `git checkout HEAD --`, commit the edits it would overwrite, and have it refuse on a dirty file.** Evidence: the `Rdel` witness script nearly restored `check_m3_page_honesty.py` over the uncommitted re-pin; `run-host-rdel.sh` now refuses (`git diff --quiet`).
