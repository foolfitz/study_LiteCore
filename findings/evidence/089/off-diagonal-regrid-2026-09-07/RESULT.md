# RESULT -- off-diagonal regrid, 2026-09-07

Executor of `handoff/tasks/TASK-2026-09-07-089-off-diagonal-regrid.md`. Section
numbers below refer to that file. This document does not name a cause for
finding 089 (section 9). It records what happened; it does not decide what the
result means for any milestone, and it does not make the terminating
declaration about whether the "both axes" sentence may be repeated -- that is
the owner's call, not the executor's.

## Outcome

```
OUTCOME: R
TRIGGER: R -- all ten named points REPRODUCE unanimously, the ODT control
opened in every invocation, and no invocation was void
```

No E, C, or S trigger fired. Full detail below.

**What section 1.2 licenses for outcome R, quoted verbatim with today's date
and point list filled in (this is the protocol's own licensed sentence, not an
independent conclusion by the executor):**

> Re-measured on 2026-09-07 on `e2-editor-v12`, three invocations per row. At
> `Index2 = 36` the document opens at `Index` ∈ {20, 25, 30, 33, 34} and does
> not open within 180 s at `Index` = 35. At `Index2 = 35` it opens at `Index`
> ∈ {35, 36, 100}. On these eleven points the 2026-09-06 grid reproduces.

Whether this now licenses repeating "`Index ≥ 35` AND `Index2 ≥ 36`" is the
main session's call (section 1.2: "Only after this outcome may the sentence
... be repeated"), not a declaration made here.

## Pre-flight

- **Fixture identity (section 2.5)**: all twenty files hashed before
  invocation 1; all twenty matched the table in section 2.5 exactly. Re-hashed
  again after invocation 7 (the last browser invocation run): still identical.
  No drift across the whole run. See `identity.json`.
- **`build_row_ladder.py --verify`**: ran once, before invocation 1. Output
  saved verbatim to `build-verify.txt`:
  ```
  rows20: content.xml identical=True  whole-zip identical=False
  rows50: content.xml identical=True  whole-zip identical=False
  verify: the banked fixtures are what this script produces
  ```
  Only `--verify` was run; `--rows` and `--split` were never invoked.
- **Chrome process count before the first browser invocation**: **0**
  (`pgrep -x chrome` and `pgrep -x google-chrome` both returned nothing).
- **`df /tmp` before invocation 1**: tmpfs 16G, 1.6G used, 14G avail, 10%.
  Same after the last invocation.
- **Soak-in-flight check**: no chrome process running at any point in this
  session; the three most recent `queue-v12-cutover-soak` commits
  (`09559711`, `e7571664`, `4f0c276f`) were not made during this session and
  no soak run was observed in flight before any invocation.

## No-browser red cases (run first, per instructions)

All three ran before any browser invocation, over `identity.json` and copies
of the 2026-09-06 banked `grid-index25-30-33-with-index2-36.json` (the only
banked file containing A3). Full detail in `redcase-RC-3.json`,
`redcase-RC-4.json`, `redcase-RC-5.json`.

| red case | required record | result |
| --- | --- | --- |
| RC-5 (empty directory) | `{"status": "no-reports"}`, non-zero exit | **MATCHES**: exact output, exit code 1 |
| RC-4 (sha256 altered by one hex digit) | `{"status": "void", "reason": ..., "mismatches": ["<path>"]}` naming the path | **MATCHES**: status void, `mismatches` names `../findings/evidence/089/tdf149752-index30-index236.ods` exactly |
| RC-3 (A3's `opened` flipped to null) | "the outcome letter changes from R to C, with sub-case C1 and the point named" | **Outcome letter changed (void -> C1, point A3 named)** -- see note below |

**RC-3 note, stated plainly rather than smoothed over.** The unmutated
`grid-index25-30-33-with-index2-36.json`, used alone, contains only A2, A3, A4
-- all three banked as "opened" and all three opened in that file. Fed alone
to `reduce.py`, this file fails section 4.5's own RC-1 gate
(`bothOutcomesSeen`: every spreadsheet case in it opened, none failed), so
`reduce.py` correctly reports the *whole invocation* as **void** before
mutation -- not the outcome letter "R". Outcome R itself requires all ten
named points to be present and reproducing (section 1.2), which a 3-case file
never can, no matter what it contains. After flipping A3's `opened` to
`null`, the same file now shows both a truthy and a falsy `opened` among its
spreadsheet cases for the first time, so it simultaneously (a) passes RC-1
and becomes analyzable, and (b) shows A3 contradicting its banked "opened"
verdict -- and `reduce.py` reports **C (C1), point A3 named**. The letter
changed (void -> C), demonstrating `reduce.py` reads the `opened` field and
retires the claim correctly. It did not literally pass through the letter
"R" first, because no single banked A-row file can satisfy Outcome R's own
completeness requirement; this is reported as a discrepancy against the
literal red-case text, not resolved by widening or substituting.

RC-2 (needs a browser; charged to reserve budget) is reported in the
invocation log below.

## Invocations

Budget: 8. Used: **7** (6 required + 1 reserve for RC-2). Reserve invocation 8
was **not spent** -- the stop rule was met (both shapes had three non-void
repeats, `reduce.py` produced a verdict, all section 6 red cases recorded) and
no invocation was voided, so no tie-break or replacement was needed.

| # | shape/purpose | order | started (UTC) | completed (UTC) | exit | chrome procs after | git delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | A repeat 1 | ascending | 14:03:11 | 14:06:22 | 0 | 0 | none |
| 2 | A repeat 2 | ascending | 14:07:13 | 14:10:24 | 0 | 0 | none |
| 3 | A repeat 3 | **reversed** | 14:10:54 | 14:14:05 | 0 | 0 | none |
| 4 | B repeat 1 | as written | 14:14:35 | 14:17:42 | 0 | 0 | none |
| 5 | B repeat 2 | as written | 14:18:11 | 14:21:18 | 0 | 0 | none |
| 6 | B repeat 3 | **reversed** | 14:21:47 | 14:24:54 | 0 | 0 | none |
| 7 | RC-2 (Shape B + `--truncated`) | as written | 14:26:05 | 14:29:14 | 0 | 0 | none |
| 8 | reserve | -- not spent -- | -- | -- | -- | -- | -- |

Every invocation: `verdict.controlOdtOpened == true`, `openTimeoutMs ==
180000`, `progress.fatal == null`, `bothOutcomesSeen == true` (RC-1, in band).
None void. Full per-invocation gate detail in `meta/*-meta.json` and
`regrid-verdict.json`'s `perReport` array. `git status --porcelain` showed no
delta beyond this task's own new directory, before and after every single
invocation.

## Per-point results (2026-09-07 vs. banked 2026-09-06)

Categorical verdict first (this is what selects the outcome), timing band
second (informational, per section 4.2 -- never overrides the categorical
verdict).

| point | `Index` | `Index2` | banked verdict | banked `elapsedMs` | 2026-09-07 `elapsedMs` (3 repeats) | categorical | `r` (median/banked) | band |
| --- | ---: | ---: | --- | --- | --- | --- | ---: | --- |
| A1 | 20 | 36 | opened | 1228 | 1370, 1398, 1118 | REPRODUCES | 1.12 | reproduces the banked figure |
| A2 | 25 | 36 | opened | 1484 | 1141, 1150, 1176 | REPRODUCES | 0.77 | reproduces the banked figure |
| A3 | 30 | 36 | opened | 1223 | 1178, 1108, 1148 | REPRODUCES | 0.94 | reproduces the banked figure |
| A4 | 33 | 36 | opened | 1274 | 1136, 1161, 1120 | REPRODUCES | 0.89 | reproduces the banked figure |
| A5 | 34 | 36 | opened | 1496 | 1127, 1158, 1351 | REPRODUCES | 0.77 | reproduces the banked figure |
| A6 | 35 | 36 | TIMEOUT (180969, 181017) | -- | 181383, 181377, 181361 | REPRODUCES | n/a (no band for TIMEOUT) | n/a |
| B1 | 100 | 35 | opened | 1486 | 1354, 1350, 1142 | REPRODUCES | 0.91 | reproduces the banked figure |
| B2 | 36 | 35 | opened | 1589 | 1154, 1158, 1162 | REPRODUCES | 0.73 | reproduces the banked figure |
| K1 (anchor) | 35 | 35 | opened | 1245 / 1260 | 1118, 1143, 1352 | REPRODUCES | 0.92 (vs 1245) | reproduces the banked figure |
| K2 (anchor) | 36 | 36 | TIMEOUT (180919, 180991) | -- | 180849, 180883, 180849 | REPRODUCES | n/a (no band for TIMEOUT) | n/a |

All ten points: **REPRODUCES unanimously across all three repeats**, all
non-void, all within the [0.5, 2.0] "reproduces the banked figure" band where
a band applies. Every A6/K2 `elapsedMs` fell inside the required
[180000, 182000] ms window with `error.code == "TIMEOUT"` and the message
containing `180000`.

**Section 3.4's ordering control**: repeat 3 of both shapes ran in reversed
fixture order (Shape A: 34,33,30,25,20, then 35; Shape B: rows35,
index36-235, index100-235, then rows36). Every point's repeat-3 value sits
inside the same range as repeats 1-2 (e.g. A1: 1370/1398 ascending vs. 1118
reversed; A5: 1127/1158 ascending vs. 1351 reversed) -- no point's categorical
verdict depended on its position in the session.

## Triggers (section 1.2)

- **E1** (anchor contradicts within its own repeats): **did not fire**. K1
  opened in all 3 repeats it appeared in; K2 timed out in all 3.
- **E2** (2+ owed points SPLIT): **did not fire**. Zero owed points split.
- **E3** (elapsedMs spread > 4.0x for a point that opened every repeat):
  **did not fire** for any of the ten points, nor for the control. Largest
  spread observed among opened points: K1 at 1352/1118 = 1.21x; control
  (`d1-anchors.odt`) at 1752/1638 = 1.07x across all 7 invocations.
- **C** (a banked point contradicts unanimously): **did not fire**. Zero owed
  points contradicted.
- **S** (a point splits after tie-break): **did not fire**. No tie-break was
  needed (section 3.4) since nothing split.
- **R**: fired, as above.

## NU-089-1 and NU-089-2 -- recorded, not interpreted (section 9 binds this)

- **NU-089-1** (only the 30-s-class file moved between 09-06 and 09-07): this
  protocol measured nothing in the 30-s class (every point here is 1.1-1.6 s
  or a 180 s TIMEOUT). Per section 7.1, **a clean outcome R here is not
  evidence about NU-089-1 in either direction** and is not read as such.
  NU-089-1 stays open.
- **NU-089-2** (`workerCrashed: true` on cases that still opened): recorded
  per case, verbatim, not interpreted. Today's pattern matches the banked
  pattern exactly: `workerCrashed: true` on A5, B1, B2, K1 in every repeat
  they appear in; `workerCrashed: false` on A1-A4, A6, K2, and the control, in
  every repeat. (Full per-case `workerCrashed` and warning text is in
  `regrid-verdict.json`'s `points.*.repeats[]` and the raw `A-*-report.json` /
  `B-*-report.json` files.) This reproduces NU-089-2's own banked pattern; it
  changes no verdict and is named as a mechanism for nothing.

## RC-2 (the browser red case)

Charged to reserve invocation 7, since both reserves were free after
invocations 1-6 completed clean. Shape B plus a `--truncated` file (the first
4096 bytes of `tdf149752-index20-index236.ods`, written only to the
scratchpad, sha256 `68da3248e02dcfc385236e59857d6c85c4389ab4dfbeab65f97d8016cd2fe41b`,
never placed under `findings/evidence/089/`).

Result: `opened: false`, `error.code == "LOK_ERROR"` (not `"TIMEOUT"`),
`error.message == "loadComponentFromURL returned an empty reference"`,
`elapsedMs: 926`. This is a **third value** in the "did not open" column,
distinct from every banked/measured TIMEOUT. Full record in
`redcase-RC-2.json` and `redcase-RC-2-invocation.json`.

## Files in this directory

- `identity.json` -- section 2.5 identity snapshot (20 hashes, chrome
  version, kernel, git HEAD, `reduce.py`'s own sha256), taken before
  invocation 1.
- `build-verify.txt` -- `build_row_ladder.py --verify` output.
- `reduce.py` -- the form-two instrument (section 4.6).
- `A-1-report.json` / `A-2-report.json` / `A-3-report.json` -- Shape A
  repeats 1-3 (raw `probe_ods_on_profile.py` output).
- `B-1-report.json` / `B-2-report.json` / `B-3-report.json` -- Shape B
  repeats 1-3.
- `redcase-RC-2-invocation.json` -- the raw report from the RC-2 browser
  invocation (Shape B + `--truncated`).
- `redcase-RC-2.json` / `redcase-RC-3.json` / `redcase-RC-4.json` /
  `redcase-RC-5.json` -- the five section 6 red-case records.
- `regrid-verdict.json` -- `reduce.py`'s full output over the six real
  invocations: per-point repeat data, triggers, outcome, trigger clause.
- `meta/*.json`, `meta/*.txt` -- per-invocation timestamps (UTC and CST),
  gate results, chrome-process and git-status bookkeeping.
- `logs/*.log` -- raw stdout/stderr from every `probe_ods_on_profile.py`
  invocation.

## What the protocol did not anticipate -- stated plainly

1. **No historical single banked A-row file can pass section 4.5's own RC-1
   gate on its own** (see the RC-3 note above). The 2026-09-06 grid was taken
   across three separate invocations (section 3.4), and the A2/A3/A4
   invocation alone never contained a hang case. This protocol's own Shape A
   invocations always bundle all six points with the hang, so this problem is
   specific to reusing 2026-09-06 artefacts as red-case inputs, not to the
   real measurement.
2. **Section 1.2's outcome-C/S/E trigger text says "the six owed points" /
   "the owed points" without a single consistent count.** Section 1.1 and the
   summary sentence in section 1.2 name only Row A's six points as "owed",
   but sections 5.1 and 5.3 (sub-case C2: "B1 or B2 does not open. N2
   falls.") substantively treat B1 and B2 as owed points too. `reduce.py`
   follows the substantive eight-point reading (Row A + Row B) for E2/C/S,
   since that is what the sub-case definitions actually require; this is
   named here rather than silently resolved. It did not change the outcome
   in this run (no point in either row contradicted or split).
3. Every other step in the protocol executed exactly as written: all twenty
   section-2.5 hashes matched with no adaptation, all six required
   invocations passed every section 4.5 gate on the first attempt (no voided
   invocation, no reserve needed for replacement, no tie-break needed), and
   RC-1/RC-2/RC-3/RC-4/RC-5 all produced their required records.
