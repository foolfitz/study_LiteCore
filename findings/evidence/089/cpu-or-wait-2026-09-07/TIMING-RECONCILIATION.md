# TIMING-RECONCILIATION — is the case-4 speed-up (30,688 ms → ~1.05 s) specific to that run, or does today re-time everything faster?

Step 2 of the 2026-09-07 phase-2 task
(`handoff/tasks/TASK-2026-09-07-089-cpu-or-wait.md`, `## Execution record`).
This section is written and committed **before any timing run below is
executed**, per the task's instruction. The "Results" section at the bottom
is appended after the runs; nothing above that heading is edited afterward.

## Why this is being asked

`RESULT.md` (phase 1, this same directory) recorded that
`tdf161948_NaturalSortSaveLoad.ods` opened in **1,090 ms** (run 1) and
**1,046 ms** (run 2) on 2026-09-07, both inside the same protocol that
otherwise reproduced finding 089's central "Waiting" result. The banked
figure for the same file is **30,688 ms**
(`findings/evidence/m4-ods/04-sweep-v12.json:33191`, `"elapsedMs": 30688`,
`tdf161948_NaturalSortSaveLoad.ods`, part of the 306-fixture sweep on the
same profile `e2-editor-v12`). That is a ~28-30x discrepancy on the same
document, the same profile, one day apart — and 089's whole ladder
(including the `Index ≥ 35` / `Index2 ≥ 36` frontier that this finding's
central claim rests on) was measured on 2026-09-06, the same day this
machine is independently known to have carried an orphaned headless Chrome
(`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`: running from
20:21 on 09-06 for about four hours) plus the owner's own browser session.
**Contention is a live hypothesis for the discrepancy. It is a hypothesis,
not a finding**, and this document does not resolve it by asserting it —
only by re-timing.

## 1. Exact fixtures to re-time

Four files, the same four `findings/evidence/089/build_row_ladder.py`-family
fixtures (plus the upstream one) that phase 1 already re-verified the
identity of in `identity.json` (all four also appear in TASK §1.5's hash
table, already matched there):

| # | file | role |
| --- | --- | --- |
| 1 | `findings/evidence/089/tdf149752-rows35.ods` | "rows35-equivalent that opens" (`Index=35, Index2=35`) |
| 2 | `findings/evidence/089/tdf149752-index36-index235.ods` | "index36/index2-35 that opens" (`Index=36, Index2=35`) |
| 3 | `wasm_sdk_probe/test-docs/ods/upstream/tdf161948_NaturalSortSaveLoad.ods` | the case-4 heavy-but-finite control — the file with the discrepancy |
| 4 | `findings/evidence/089/tdf149752-rows36.ods` | the hang itself (`Index=36, Index2=36`), expected not to open |

Plus the ODT control (`wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt`) in
every invocation, exactly as phase 1's `run_one.py` used it — its own
purpose is to tell "the instrument did not attach" apart from "this file is
slow", and dropping it here would remove that check.

## 2. The banked number for each, quoted with source

| fixture | banked elapsed | source | note |
| --- | ---: | --- | --- |
| `tdf149752-rows35.ods` | **1,245 ms** | `findings/evidence/089/grid-2026-09-06.txt:21` | also 1,260 ms at `findings/evidence/089/ladder-2026-09-06.txt:12` (different run, same day) |
| `tdf149752-index36-index235.ods` | **1,589 ms** | `findings/evidence/089/grid-2026-09-06.txt:24` | `Index=36, Index2=35` |
| `tdf161948_NaturalSortSaveLoad.ods` | **30,688 ms** | `findings/evidence/m4-ods/04-sweep-v12.json:33191` | the number this whole reconciliation is about |
| `tdf149752-rows36.ods` | **TIMEOUT, 180,919 ms / 180,991 ms** (both non-opens) | `findings/evidence/089/ladder-2026-09-06.txt:20` and `:15` | also **1,800,901 ms, still TIMEOUT** at the raised 1,800 s ceiling — `findings/evidence/089/rows36-open-timeout-1800s.json`, quoted in `findings/089-...md`, section "`rows36` does not open in thirty minutes" |

## 3. Repeats, idle check

**3 repeats minimum.** Each repeat is one invocation of
`wasm_sdk_probe/tools/probe_ods_on_profile.py` (the same tool phase 1's
`run_one.py` drives, read-only — it has no `--write` flag or any other
mutating option, confirmed via `--help`), opening, in one browser session:
the ODT control, then the three fixtures that are expected to open
(`rows35`, `index36-index235`, `tdf161948`), then `tdf149752-rows36.ods`
capped as below. `--open-timeout-ms 180000` (the SDK's own default), so a
`TIMEOUT` on `rows36` reads at the standard 180 s mark, not the 1,800 s
ceiling phase 1 already used once — see the cap rule (§4).

**Idle check before every repeat:**
```
pgrep -x chrome ; pgrep -x google-chrome
```
both expected empty before a repeat is started. Also checked: no other
headless run of mine (this task's own prior runs' user-data-dirs are gone;
`/tmp/wasm-sdk-probe-chrome-*` from a previous repeat is cleaned before the
next one starts, per the task's own `/tmp` housekeeping rule). Recorded
per-repeat in the run's own meta output, not asserted after the fact.

## 4. The cap for `rows36`

**Do not re-run the 1,800 s timeout.** `--open-timeout-ms 180000` (the
default) is used for every repeat, exactly as phase 1's `run_one.py` did for
runs 1–2. A `TIMEOUT` at ~180 s here is not evidence of anything beyond what
is pre-registered next: it means "still does not open within the standard
window", not "faster" or "slower" than the banked 30-minute datum, and this
document draws no comparison between today's 180 s cap and the 1,800 s
figure banked elsewhere.

## 5. What each outcome means — written before running

* **(i) Today's numbers reproduce the banked ones** (rows35 ≈ 1,245 ms,
  index36/235 ≈ 1,589 ms, tdf161948 ≈ 30,688 ms, rows36 still TIMEOUT at
  180 s) — within, say, a factor of 2 for the sub-2-s opens and a factor of
  2 for the 30 s one: **the discrepancy is specific to phase 1's case 4
  measurement and the ladder stands.** Phase 1's fast tdf161948 opens
  (1.09 s / 1.05 s) would then be the anomaly needing its own explanation
  (not offered here), and 089's frontier claims are untouched.
* **(ii) Today's numbers are systematically faster** — in particular if
  `tdf161948` lands anywhere near phase 1's ~1.05–1.09 s rather than
  ~30.7 s, or if `rows35`/`index36-235` are markedly faster than their
  banked figures too: **the banked ladder was measured under a condition
  this session can now name (a busier machine on 2026-09-06), and the
  frontier itself (`Index ≥ 35` / `Index2 ≥ 36`, and in particular whatever
  in it depends on absolute wall-clock thresholds rather than open-vs-
  timeout) must be re-measured before any statement about `Index`/`Index2`
  is repeated.** This document says that plainly and stops there — it does
  **not** re-measure the whole grid itself; that is separate work, out of
  this task's scope, and would need its own budget and pre-registration.
* **(iii) Mixed or noisy** — e.g. `tdf161948` reproduces near 30 s but
  `rows35`/`index36-235` do not, or the three repeats disagree with each
  other by more than measurement noise should allow: **report the spread,
  resolve nothing.** No reading is picked because it fits a preferred story;
  the numbers are banked as they come out, and this document says "not
  resolved" rather than rounding to (i) or (ii).

`rows36`'s outcome (open vs. TIMEOUT) is recorded in all three cases as a
fact about today, cross-checked against the pre-existing "does it still
reproduce" question (`findings/evidence/089/rows36-open-timeout-1800s.json`
already answered this once at the 1,800 s ceiling); it is not itself one of
the three timing outcomes above, since it has no continuous banked number to
compare against — only "opens" vs. "does not".

---

## Results

Recorded after the pre-registration above. Nothing above this line was
edited after these runs.

Executed 2026-09-07, 21:01–21:14 CST (well outside both no-run clock
windows; now+20min checked before each of the three repeats). `pgrep -x
chrome` and `pgrep -x google-chrome` both empty immediately before every
repeat; no leftover `/tmp/wasm-sdk-probe-chrome-*` from a prior repeat.
`git status --porcelain` showed only this task's own new files throughout
(`TIMING-RECONCILIATION.md`, then `timing/`). Every repeat's per-case
`inputSha256` matched the four rows of TASK §1.5's table exactly, in all
three repeats, with no mismatch — same identity phase 1 already checked.
Each repeat is one `probe_ods_on_profile.py` invocation, `--open-timeout-ms
180000` (the cap named in §4 above, not the 1,800 s ceiling), `--timeout
400`, opening the ODT control then the three fixtures expected to open then
`tdf149752-rows36.ods` in that order, in one browser session — the same
tool and the same case order phase 1's `run_one.py` used, run without the
CPU sampler since this step only needs `elapsedMs`.

### Raw numbers, all three repeats, against the banked figures

| fixture | banked | repeat 1 | repeat 2 | repeat 3 | today's mean | ratio (today/banked) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `d1-anchors.odt` (control) | 1,742–1,881 ms (context only) | 1,627 ms | 1,760 ms | 1,712 ms | 1,700 ms | ~1.0x |
| `tdf149752-rows35.ods` | **1,245 ms** (`grid-2026-09-06.txt:21`) | 1,422 ms | 1,372 ms | 1,353 ms | 1,382 ms | **1.10x** (10% slower today) |
| `tdf149752-index36-index235.ods` | **1,589 ms** (`grid-2026-09-06.txt:24`) | 1,172 ms | 1,136 ms | 1,162 ms | 1,157 ms | **0.73x** (27% faster today) |
| `tdf161948_NaturalSortSaveLoad.ods` | **30,688 ms** (`04-sweep-v12.json:33191`) | 1,397 ms | 1,053 ms | 1,014 ms | 1,155 ms | **0.038x — today is ~26.6x faster** |
| `tdf149752-rows36.ods` | TIMEOUT (180,919 / 180,991 ms banked; 1,800,901 ms at the raised ceiling) | TIMEOUT, 180,836 ms | TIMEOUT, 180,854 ms | TIMEOUT, 180,835 ms | TIMEOUT, all three | matches: still does not open |

All three repeats agree with each other to within normal run-to-run spread
for each fixture (rows35: 1,353–1,422 ms; index36-235: 1,136–1,172 ms;
tdf161948: 1,014–1,397 ms; rows36: TIMEOUT at 180,835–180,854 ms every
time — no outlier repeat, no fixture that opened on one repeat and not
another).

### Which pre-registered outcome obtains

**Not (i) as stated for all four fixtures**, because (i) required
`tdf161948` to land near its banked 30,688 ms, and it did not, in any of the
three repeats. **Not (iii)**: the three repeats do not disagree with each
other beyond ordinary spread, and the fixtures do not read as noisy —
`rows35` and `index36-235` reproduce their banked figures within a plain
factor of about 1.1–1.3x (the same order of run-to-run spread the
2026-09-06 banked data itself shows: `rows35` was banked at both 1,245 ms
and 1,260 ms on that day, `findings/evidence/089/ladder-2026-09-06.txt:12`
and `:19`), while `tdf161948` reproduces phase 1's same-day fast numbers
(1,090 ms / 1,046 ms) far more closely than it reproduces its own banked
figure — 1,014–1,397 ms today, against phase 1's 1,046–1,090 ms earlier the
same day, against 30,688 ms banked from 2026-09-06.

**(ii) obtains, on its own pre-registered trigger clause**: "`tdf161948`
lands anywhere near phase 1's ~1.05–1.09 s rather than ~30.7 s" is exactly
what happened, in all three repeats, on a session run hours after phase 1
and independently idle-checked. Combined with phase 1's own two runs
earlier the same day, this is now **five** independent measurements across
**two** sessions on 2026-09-07, all in the 1.0–1.4 s band, against **one**
historical measurement — 30,688 ms, from 2026-09-06, the day this machine
is independently documented to have carried an orphaned headless Chrome for
about four hours plus the owner's own browser
(`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`). The sentence this
outcome licenses, exactly as pre-registered: **the banked ladder was
measured under a condition this session can now name, and the frontier
itself (`Index ≥ 35` / `Index2 ≥ 36`) must be re-measured before any
statement about `Index`/`Index2` is repeated.** This document does not
re-measure the whole grid — that is separate, out-of-scope work needing its
own budget and pre-registration, exactly as pre-registered above.

**A nuance the pre-registration did not anticipate, recorded rather than
resolved**: the effect is not uniform across fixtures. The two short opens
(`rows35`, `index36-235`, both under 2 s) land close to their banked
figures (within the same spread the banked ladder itself already shows
between its own repeated measurements of `rows35`); only the ~30 s-class
control (`tdf161948`) shows an order-of-magnitude gap. `rows36`'s own
TIMEOUT behaviour is identical across today's three repeats and consistent
with every prior banked TIMEOUT for that file. This asymmetry is stated as
a fact about which fixtures moved and which did not — it is not evidence
about *why*, and no cause is offered here for why a long-running open would
be more exposed to whatever changed than two short ones.
