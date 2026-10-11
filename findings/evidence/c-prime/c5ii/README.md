# C5 (ii): every product-path mutation on the final C′ page — result

Spec `specs/SPEC-M3-production-ui.md` §17.4 C5 (ii), §17.20 (zh-TW). Prediction and reading rule: `PREDICTION.md`
(committed before the chain, `a74a2494` / `01c948fc`; correction 2 `b952e5f6` before the one re-run).

## What ran

`chain-c5ii.sh`, Chrome, one full `--mutate` run per mutation, page `dist/` = `web/` = `8909564eb2316afa…`, runner
`run_e2_c_product_path.py` `bd6fc0caf677ee9c`, tree `01c948fc`. 51 runs, 2026-10-11T03:56:00Z → 09:59:14Z
(6 h 03 min, ~7.1 min per run; predicted ~5.5 h). Progress log `chain.txt` (one line per mutation; `exit` is the
runner's strict `ok`, not the reading — rule eee). Every run wrote a report with `complete: true`; nothing needed the
"re-run once alone" clause. One extra run after the chain (`…-v12-chrome.json`, below), logged in the same file.

## Reading (by `PREDICTION.md`'s rule, from each report's own checks)

`reading.txt` is the listing, produced by `read_c5ii.py` (an ad-hoc listing of the declared check's outcome per
report — not a judge, no thresholds; re-run: `python3 -I read_c5ii.py findings/evidence/c-prime/c5ii
wasm_sdk_probe/tools` from the repository root).

| Class | n | Mutations |
|---|---|---|
| Ordinary, **red** (declared check FAIL) | **44** | all except the three below |
| Ordinary, **not red** | **3** | `inline-format-rollback`, `geometry-declared-but-not-delivered` (v14), `rollback` |
| `caret-ignores-x`, §17.10 | 1 | red (own check NE, also-red `the-caret-is-drawn-where-it-was-placed` FAIL) — as predicted |
| Declared undetectable | 2 | `checkpoint-write-fails`, `copy-lies`: not detected, as declared |
| Recorded, not counted | 1 | `a11y-projection-at-its-static-position`: survives (check PASS), as predicted (§17.9 (g) S5) |

**By the rule as written, C5 (ii) does not hold: 3 of 47 ordinary mutations are not red.** The prediction was "all 47
red". Per `PREDICTION.md`, the release step is stopped and the three were diagnosed. None of the three is a mutation
that C′ stopped from biting; each has a cause that is older than C′, read from the source and from earlier reports.

## Diagnosis of the three

### 1. `geometry-declared-but-not-delivered` — dead under the flag the prediction chose

The mutation replaces `contract?.documentOutlineGeometry === "accessible-paragraph-geometry"` with
`Boolean(contract)` (`web/e2-editor-app.js:374`). The chain ran it with `--candidate-profile e2-editor-v14`, whose
`sdk-manifest.json` (`9943b064d4e18515…`) **declares** `documentOutlineGeometry: accessible-paragraph-geometry`, so on
v14 both expressions are `true` and the page cannot reach `declared-but-missing`. The report shows it: `geometry:
"present"`, 24 carried / 24 placed. The mutation's own red case when it landed (`72f8de7f`,
`probe_093_placement_red_cases.py`, default `--profile e2-editor-v12`) used v12, which declares the outline and not the
geometry (`2734229351dac1da…`). Correction 2 in `PREDICTION.md` (committed before the re-run) records the v14 run as
not judged and predicts the v12 re-run red on clause C1.

**Re-run with `--candidate-profile e2-editor-v12`** (`mutation-geometry-declared-but-not-delivered-v12-chrome.json`, 2026-10-11T09:59:52Z → 10:06:43Z, same page / runner hashes, logged in `chain.txt`): **red, as predicted** — owning check FAIL on clause C1 only (`geometry: "declared-but-missing"`, carried 0 / placed 0, C2 and C3 true), the runner's own verdict "the mutation was detected by the check that owns it" (`ok: true`), and no collateral: the only other non-PASS cells are the two standing NOT_ESTABLISHED ones. The candidate page measured is `7c9a84be…` (v12 pin), which is the C′ page repointed to v12 by the runner's own `repointed_page` (pin and worker URL).

### 2. `inline-format-rollback` — dead since finding 059 was fixed (2026-08-19); its owning check passes vacuously

The mutation disables the `LOK_COMMAND_FAILED` → `dispatched-unverified` branch of `formatFailureDisposition`
(`editor-shell-v2/paragraph-editor-client.js:309`). That branch runs only when a format action returns
`LOK_COMMAND_FAILED`. The mutation bit once, on 2026-08-18 (`../../059/disposition-v17/`), because the engine then
reported core's `success:false` for a bold that had succeeded (finding 059). 059's engine half was fixed and shipped in
the 2026-08-19 link (`296f3ea7…`): the engine now asks the document's own state and reports the failure only when
the state disagrees (`src/probe_engine.cpp:2754-2768`). On v19 no format action in the product path fails: in all 51
C5 (ii) reports `a-format-that-worked-is-not-reported-as-failed` is PASS with `toastAfterFirstPress: ""`, and bold
toggles `false → true → false`. So the replaced line is never reached. Between 2026-08-18 and this chain the mutation
was never run (two reports exist in the tree: 08-18 and this one), which is why nothing noticed.

The deeper half: the owning check `a-failed-format-does-not-block-the-session`
(`run_e2_c_product_path.py:6155`) reads "session `ready` and no rollback notice" after the two bold presses. It does
not establish that a format **failed**, so with no failure it reports PASS. Since 2026-08-19 every PASS of this check
is the "nothing happened" reading of a check that has no positive control (CLAUDE.md §3: a behaviour — the
`LOK_COMMAND_FAILED` disposition, still reachable when core really rejects a format — with nothing guarding it).
C′ did not touch this code path; the P page, on the same v19 engine, has the same property (inferred from the
source, not run).

### 3. `rollback` — the declared owner is the designed sentinel; the mutation is caught by the recovery cell, exactly as on 0.2.9

Declared check `notice-action-recovers-the-session` is NOT_ESTABLISHED: it is the sentinel of `recoveryPairing`
(`bulleting` PASS → `noticeAction` abstains, `held: true`; CLAUDE.md §3 names it). The mutation (rollback wired to
undo) is caught by `recovery-returns-what-the-product-promised` FAIL: notice shown with `rescue: checkpoint`, pressed,
state stays `recoverable-error`, the product says 「回到檢查點 失敗」, and the run stops there
(`the-run-stopped-because-the-session-was-dead`). This is the same signature as `../../release-0.2.9/product-path/mutation-rollback-chrome.json` (2026-10-09):
the same four non-PASS checks, and the recovery cell's `observed` differs in exactly two timing fields (`caret` 32 vs
26 ms; `stateAfterDrag` `busy` vs `ready`) and nothing else. There the reading was
recorded as "the condition named the sentinel cell; the cell that went red is the one that exercises the same
capability in this run" (`../../release-0.2.9/product-path/PREDICTION.md`). The runner's declaration was not changed
then, and this chain's prediction did not carry that precedent forward — the prediction missed it, not C′.

## Stale side declarations seen (recorded, not read)

- `caret-off-by-one-line`: declared also-red `bulleting-a-blank-line-does-not-demand-a-rollback` PASS on C′.
- `inline-format-rollback`: declared also-red `bold-can-be-turned-off-again` PASS (same cause as §2 above).
- `save`: declared also-red `notice-action-recovers-the-session` NOT_ESTABLISHED (the sentinel).

## Not decided here

Whether C5 (ii) holds with these three diagnoses, and what (if anything) changes in the runner, is put to the owner
(§17.20). The runner is untouched; §34.4 stays **因執行而修 6, 因審核而修 5**.

## Corrections after fable's ruling (2026-10-11; `ruling/fable-ruling.md`) — appended, the text above stands

- "Two reports exist in the tree" for `inline-format-rollback`: a third JSON names it —
  `../../w3-inline-format-mutations/census-2026-09-03-can-these-four-go-red.json` — a census over 160 existing reports,
  not a run. "Never run between 08-18 and this chain" stands. "Which is why nothing noticed" is overstated: W-3
  (2026-09-03, `RESULT-W3.md:16`) already had the data (the format checks' only FAILs were on 2026-08-18) and its own
  question — can the check fail? — was never asked of `a-failed-format-does-not-block-the-session`.
- "On v19 no format action in the product path fails" is bounded to **no recorded failure**: in all 52 reports
  `LOK_COMMAND_FAILED` appears only in `oracle` text (104 hits); the runner records toasts where it reads them, it does
  not keep an engine error log.
- `rollback` vs 0.2.9: `stateAfterDrag` `busy` → `ready` is a timing-dependent state read, not a timing field; the
  other difference (`caret` 32 → 26 ms) is a timing field.

## Outcome

**C5 (ii) as written: not held (44/47).** **C5 (ii)′ (spec §17.21): holds** — every mutation live on the C′ page
under the flag its own red case used is red, 46/46 (44 by the declared check, `geometry-declared-but-not-delivered` on
v12, `rollback` by the recovery cell under the §17.21 reading), plus `inline-format-rollback` dead on every page since
2026-08-19 and registered. Chrome only. Runner `bd6fc0caf677ee9c` unchanged; §34.4 6 / 5.
