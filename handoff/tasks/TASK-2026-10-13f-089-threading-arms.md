# TASK 2026-10-13f — finding 089: is the cliff Calc's threaded formula-group path?

Written by the main session BEFORE any run below. Predictions and outcome rules
are fixed here; a run does not move them. Evidence goes to
`findings/evidence/089/threading-arms-2026-10-13/` (English, per `AGENTS.md`).

## 1. Why this arm, and what it rests on (read in source, not measured)

Finding 089: on the writer+calc a11y core (profile `e2-editor-v12`), `rows36` and
the `Index ≥ 35 ∧ Index2 ≥ 36` points never open (180 s cap, three of three,
2026-09-07), while the tree is *waiting*, not computing. Four nearby points open
but the worker dies with `memory access out of bounds` (A5, B1, B2, K1; 3/3).
Natively the same files open in ~269 ms.

Source reading (`libreoffice-26-8`), **not yet a measurement**:

- `ScFormulaCell::InterpretFormulaGroup` (sc/source/core/data/formulacell.cxx:4897)
  attempts group calculation only when the group's weight ≥
  `mnOpenCLMinimumFormulaGroupSize` (= 100, sc/source/core/tool/calcconfig.cxx:144).
- Weight = Σ over double references of (rows × cols / 10), times the group length
  (sc/source/core/tool/token.cxx:5462, formulacell.cxx:5784). A threshold that
  depends on two named ranges' sizes and on a row count is the shape a weight
  threshold would produce. That is a resemblance, nothing more.
- The threaded path (`InterpretFormulaGroupThreading`, formulacell.cxx:5095)
  is entered unless `SC_NO_THREADED_CALCULATION` is set; threading is on by
  default (officecfg Calc.xcs:1441). It pushes tasks to
  `comphelper::ThreadPool`, sized by `MAX_CONCURRENCY`, which LibreOffice's own
  pre-js sets to 4 (`static/emscripten/environment.js:3`). The profile links
  `-sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0`.
- `SC_FORCE_CALCULATION=core` disables group calculation entirely;
  `SC_FORCE_CALCULATION=threads` forces the threaded path regardless of weight
  (calcconfig.cxx:39, formulacell.cxx:4894–4900).

**Hypothesis H-T:** the cliff is the threaded formula-group path being entered on
WASM. This file does not say *why* that path would wait or crash on WASM; the
arms below only ask whether entering it is what flips the outcome.

## 2. Instrument

`wasm_sdk_probe/tools/probe_ods_on_profile.py` at commit `b028cbc6` or later, with
`--engine-env NAME=VALUE`. It patches only the scratch mirror's copy of
`profiles/<profile>/probe.js` (next to LibreOffice's own
`ENV.MAX_CONCURRENCY="4"`), and the engine echoes its ENV from inside its preRun.
**A case whose `engineEnvEchoed` is not `true` is void**: it was not run under
the arm its report is labelled with.

Profile: `e2-editor-v12` (the profile every banked 089 number was taken on).
Do not change any profile, anything under `dist/`, `web/`, `sdk/`, or the tool.

## 3. Fixtures (all already in `findings/evidence/089/`)

| id | file | banked state (2026-09-07, 3/3) |
|---|---|---|
| C | `wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt` (`--control`) | opens |
| F1 | `tdf149752-rows35.ods` | opens, worker crashed |
| F2 | `tdf149752-rows36.ods` | TIMEOUT |
| F3 | `tdf149752-index30-index236.ods` | opens clean |
| F4 | `tdf149752-index35-index236.ods` | TIMEOUT |
| F5 | `tdf149752-index36-index235.ods` | opens, worker crashed |
| F6 | `tdf149752-rows20.ods` | opens (banked 2026-09-06; not in the 09-07 grid) |

Three states per case, read from the report, never from a screenshot:
**clean** (`opened` non-null, no `workerCrashed`), **crashed** (`opened`
non-null, `workerCrashed: true`), **timeout/failed** (`opened` null).

## 4. Arms

One `probe_ods_on_profile.py` invocation per run, cwd `wasm_sdk_probe`,
absolute fixture paths, all fixtures in one invocation in the order C, F1…F6.

| arm | `--engine-env` | `--open-timeout-ms` | runs |
|---|---|---|---|
| E0 instrument control | `OXSDK_089_ARM=control` | 180000 | 1 |
| E1 threading off | `SC_NO_THREADED_CALCULATION=1` | 180000 | 3 |
| E2 group calc off | `SC_FORCE_CALCULATION=core` | 180000 | 1 |
| E3 threading forced | `SC_FORCE_CALCULATION=threads` | 60000 | 3 |

`--timeout` must exceed the worst case: 7 cases × open cap + 120 s.
Run order: E0, then E1 ×3, then E2, then E3 ×3. **Never abort a started run**;
if the machine is not idle before a run (1-min load ≥ 1.0, or a Chrome not
started by this task), wait and re-check before starting it, and record the
load at start of every run.

Preconditions before the first run, recorded in the README:
`busctl --user get-property org.freedesktop.secrets
/org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection
Locked` must print `b false` (if `b true`: stop and report — do not work
around it); `pgrep -af chrome` shows no other Chrome.

## 5. Predictions and outcome rules (fixed now)

**Gate on E0.** E0 must reproduce the banked states for F1–F5 (F6: clean) and
every case must be echoed. If any of F1–F5 departs from its banked state, the
patch itself changed behaviour: **stop, report, read no other arm.**

Then exactly one outcome, by these rules (all counts "3/3" mean every E1 or E3
run agrees; 2 of 3 is SPLIT and is reported as SPLIT, not rounded):

- **O-T (H-T supported in both directions):** E1 3/3: F2 and F4 open (clean or
  crashed), AND E3 3/3: at least one of F3, F6 is no longer clean.
- **O-T-off-only:** E1 flips F2 and F4 as above, but E3 leaves F3 and F6 clean in
  3/3. Reading: entering the threaded path is necessary for the cliff, forcing it
  on small groups is not sufficient to reproduce it.
- **O-G (the group path, not threading):** E1 leaves F2 and F4 timing out, E2
  opens them. Reading: the group interpretation path is implicated, threading is
  not.
- **O-N (H-T refuted):** neither E1 nor E2 opens F2 or F4. Reading: the cliff is
  not in Calc's formula-group calculation; record and stop.
- **SPLIT / void:** anything not above (including any unechoed case).

Recorded alongside the outcome, and **not** part of it: per arm, whether the
`workerCrashed` cases (F1, F5) still crash. H-T's simplest reading predicts E1
removes the crash as well; if E1 opens F2/F4 but F1/F5 still crash, that is
reported as "the timeout and the crash separate", not explained.

**If this is never run, the default conclusion is:** 089's cause is still
unattributed; H-T is a source reading only and may not be quoted as a cause.

## 6. Optional native arm (only after §5 has an outcome)

If and only if the outcome is O-T or O-T-off-only: run the native oracle
(`wasm_sdk_probe/tools/run_ods_native_oracle.sh`, record which native build it
uses) on F2 with `SC_FORCE_CALCULATION=threads` and on F2 with no variable,
once each. Question: does the forced threaded path complete natively? Record the
two open times. No prediction is attached; it is a record.

## 7. Deliverable

`findings/evidence/089/threading-arms-2026-10-13/README.md` (English), starting
with `## SUMMARY` (≤ 30 lines): the outcome letter, a per-arm × per-fixture
state table (clean / crashed / timeout, with open ms), echo status, load at
start of each run. All reports as `E<arm>-r<n>-report.json`. Commit only that
directory (`git commit -- <paths>`; if `index.lock` exists, wait and retry). Do
not edit finding 089 itself; the main session does that after reading the raw
reports.

---

## Amendment 1 (2026-10-13, main session; append-only, nothing above edited)

**E0-r1 is void, as §2 and §5 required** (`threading-arms-2026-10-13/E0-r1-report.json`, commit `3b7f1dce`): 0 of 7
cases echoed. Its states matched the banked ones on all seven fixtures, but that is not read as arm evidence.

**Cause, read in source and then measured:** `web/ods-decisive-probe-app.js` registered its `onEvent` listener
AFTER `createDocumentEngine()` resolved, and that promise resolves only after the worker's `init` (module load,
preRun, resource packs) — so the preRun echo was dispatched to zero listeners
(`sdk/document-sdk.js` `_emitEvent`, `createDocumentEngine`). The instrument defect was the main session's
design, not the run's.

**Fix:** the page now constructs `DocumentEngine`, registers the listener, then calls `_initialize()` — same
options, only the order changed. A short instrument check after the fix (control ODT + F3, arm
`OXSDK_089_ARM=echo-check`, 60 s cap): 2 of 2 echoed with the right ENV
(`threading-arms-2026-10-13/instrument-echo-check-after-fix.json`). E0-r1 stands as this check's red case.

**What changes for the remaining runs:** nothing in §4–§5. E0 is re-run as `E0-r2` and gates exactly as §5
says. A side effect to expect: every case's `warnings` now also holds the stderr emitted during init, which
earlier reports never captured; states are read from `opened` / `workerCrashed` as before.
