# Brief: C5 (ii) is 44 of 47 by its own rule — does it hold, and what happens to the three?

Owner chose (2026-10-11, AskUserQuestion): "交 fable 裁決". Read-only ruling: do not edit files, do not run browsers or
anything CPU-heavy. Repository root `/home/jiajun/LibreOffice/study_LiteCore`.

## Context (read these; do not trust my summary of them)

- Spec `specs/SPEC-M3-production-ui.md` §17.4 (C5 row), §17.9–§17.10, §17.19, **§17.20** (the result, zh-TW).
- `findings/evidence/c-prime/c5ii/PREDICTION.md` — reading rule and prediction, committed before the chain
  (`a74a2494`, `01c948fc`); **Correction 2** (`b952e5f6`) committed after the v14 run of
  `geometry-declared-but-not-delivered` and before its v12 re-run.
- `findings/evidence/c-prime/c5ii/README.md` — the result and my three diagnoses (English).
- `findings/evidence/c-prime/c5ii/reading.txt` — per-mutation listing (`read_c5ii.py`, ad-hoc, not a judge).
- Reports: `findings/evidence/c-prime/c5ii/mutation-<name>-chrome.json` (51) and
  `mutation-geometry-declared-but-not-delivered-v12-chrome.json`.
- Runner `wasm_sdk_probe/tools/run_e2_c_product_path.py` (`bd6fc0caf677ee9c`, frozen for this chain): `MUTATIONS`
  (`inline-format-rollback` ~:1626, `geometry-declared-but-not-delivered` ~:2159, `rollback` — search), the owning
  check `a-failed-format-does-not-block-the-session` at :6155, the bold presses just above it.
- `CLAUDE.md` §1–§11 (criterion forms; §3 "behaviour with no guard" vs "nothing to guard"; §8 termination; §9 adding
  criteria to a running gate). §34 of `specs/SPEC-M3-paragraph-merge.md` (checks machinery stop rule: a check change
  needs a witness = an honest run's report that was misjudged; otherwise register only; §34.4 counters are
  **因執行而修 6, 因審核而修 5**, and the second number must not grow).
- Precedents: `findings/evidence/release-0.2.9/product-path/PREDICTION.md` (the `rollback` reading on 2026-10-09);
  `findings/evidence/059/disposition-v17/README.md` (when `inline-format-rollback` last bit);
  `findings/evidence/w3-inline-format-mutations/RESULT-W3.md` (field FAILs of the format checks).

## The numbers

51 runs, all `complete: true`. Ordinary mutations (51 − `caret-ignores-x` − 2 declared undetectable −
`a11y-projection-at-its-static-position`) = 47. Declared check FAIL in **44**. `caret-ignores-x` red by §17.10.
`checkpoint-write-fails`, `copy-lies` undetected as declared. `a11y-projection-at-its-static-position` survives as
predicted. Not red: the three below. The prediction was "all 47 red", and the rule says any ordinary not red = C5 (ii)
does not hold → stop before the release step and diagnose.

## My three diagnoses (each is a claim for you to check against the source)

1. **`geometry-declared-but-not-delivered`** — dead under the flag the prediction chose (`--candidate-profile
   e2-editor-v14`): v14's manifest declares `documentOutlineGeometry`, so `Boolean(contract)` and the original are
   both true. Its landing red case (`72f8de7f`) used v12. Re-run with v12 after Correction 2: owning check FAIL on C1
   only (`declared-but-missing`), runner `ok: true`, no collateral.
2. **`inline-format-rollback`** — dead since finding 059's engine fix (2026-08-19 link): the mutated branch
   (`editor-shell-v2/paragraph-editor-client.js:309`) runs only on `LOK_COMMAND_FAILED`; on v19 no format in the
   product path fails (all 51 reports: `a-format-that-worked-is-not-reported-as-failed` PASS, empty toast). The owning
   check never establishes that a format failed, so it PASSes vacuously and has since 08-19. I found only two reports
   for this mutation in the tree (08-18 and this chain).
3. **`rollback`** — declared owner `notice-action-recovers-the-session` is the `recoveryPairing` sentinel (NE when
   bulleting PASSes). Caught by `recovery-returns-what-the-product-promised` FAIL (「回到檢查點 失敗」, session stays
   `recoverable-error`), same four non-PASS checks as the 0.2.9 run, recovery `observed` differing only in two timing
   fields. 0.2.9 recorded this reading and did not change the declaration; my prediction did not carry it forward.

## Claims I have NOT verified and could be wrong about (attack these)

- "C′ did not touch the `formatFailureDisposition` path" and "the P page, same v19 engine, has the same property"
  (inferred from source, not run).
- "The mutation was never run between 08-18 and 10-11" (I searched only `findings/` and `wasm_sdk_probe/build/` for
  JSON with `"mutation": "inline-format-rollback"`).
- "No format action in the product path fails on v19" (based on the bold toast field and every format check passing,
  not on a log of every engine error in a run).
- "Re-running geometry with a different flag after seeing the v14 result is not moving the criterion" (my basis: the
  flag's purpose is to make the mutation live, and v14's deadness is read from the manifests, not from the result;
  Correction 2 was committed before the re-run).

## My leaning (attack it too)

All three registered; the runner not changed (no new bytes before the release; §34 counters unchanged).
C5 (ii) holds as "every live ordinary mutation detected (46: 44 by the declared owner, geometry on v12, rollback by
the recovery cell per the 0.2.9 precedent) + one mutation dead since 2026-08-19, registered with its vacuous check as
a §3 'behaviour with no guard' item". Then the release step as in the handoff's Next 2.

Alternatives I considered for `inline-format-rollback`'s check: (b) make it NOT_ESTABLISHED when no format failed —
runner bytes move, 因執行而修 → 7, a new standing NE in every run, witness = these honest reports where it PASSed with
nothing failing (is that a "misjudged" run under §34?); (c) build an inducer for a real format failure — new
machinery, CLAUDE.md §4.

## What I need back (verdict first, ≤ ~60 lines)

1. Does C5 (ii) hold, so the release step may start? If not, the smallest measurement that would decide it.
2. `inline-format-rollback` and its check: register / (b) / (c) / other — and when.
3. `rollback`'s declaration: leave as is, or change (with the §34 witness question answered).
4. Does the v12 geometry run count, or was choosing it after seeing v14 a moved criterion?
5. Anything the release step's count must now carry because of this (e.g. a line in `RESULT-0.2.12.md`).
6. Any of my claims above that is false, with the file:line that shows it.
