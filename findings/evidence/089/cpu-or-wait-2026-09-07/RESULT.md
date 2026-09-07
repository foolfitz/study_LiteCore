# Result — finding 089, `rows36` hang: computing or blocked?

Protocol: `handoff/tasks/TASK-2026-09-07-089-cpu-or-wait.md` (drafted at commit
`e7a71edd`). Executed 2026-09-07, 17:08–19:29 CST, by the sonnet executor
seat. This file records what happened; it does not name a cause.

## Outcome

**Waiting.** During the `H` window of both measurement runs, no thread of the
Chrome process tree that opened `rows36` (`GEN(5)`) accumulates meaningful
CPU, every such thread is alive at the run's last sample, and their state
characters are `S`/`D` (never `R`) in effectively 100% of samples.

The one sentence this licenses: **the engine is blocked, not computing** — in
both runs, no thread of the browser process tree running the `rows36` open
accumulates meaningful CPU during a continuous ~160 s window inside the hang.

**What this does not say, stated as plainly as the finding: it says nothing
about what the engine is blocked *in*.** Not a lock, not a message, not a
font, not the main thread, not the proxying layer. `wchan` and `syscall` were
recorded (see "Uninterpreted payload" below) but are not read anywhere in the
outcome logic and do not appear in this sentence. `AGENTS.md` §7 and this
task's own charter: verify the claim, not a proxy for it, and name no cause.

## Why "the instrument never attached" is excluded, not just "no CPU was seen"

The load-bearing control is the in-band one (section 3.4a-3): the **same
`GEN(5)` tids**, in the **same run**, accumulate CPU during their own boot
(`B(5)`, first 10 s after birth) and then accumulate none across the
subsequent ~160 s hang window:

| run | `B(5)` CPU (s) | `H` length (s) | max `GEN(5)` rate over `H` (cores) | duty cycle |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.98 | 160.50 | 0.000623 | 0.0 / 32 sub-windows |
| 2 | 1.02 | 160.50 | 0.000685 | 0.0 / 32 sub-windows |

Because it is the identical tids, the identical process, the identical run,
minutes apart, "the sampler never attached to those threads" is excluded by
construction — the same threads it reports zero for are threads it already
showed nonzero for, earlier in the same run.

## Controls

Thresholds fixed in the protocol (section 3.3): `BUSY_BAR` = mean rate ≥ 0.5
cores; `QUIET_BAR` = mean rate < 0.02 cores/thread; `NOISE_BAR` = mean rate <
0.10 cores (threads outside the candidate set); `SUSTAINED` = rate ≥ 0.5 in
≥ 90% of 5 s sub-windows.

### Control (a) — known-busy, in each measurement run

**Controls-behave predicate: section 3.4a-3 is required, and at least one of
3.4a-1 or 3.4a-2 must also hold.**

| control | requirement | run 1 | run 2 | holds (run1 / run2) |
| --- | --- | ---: | ---: | :---: |
| (a)-3, in-band, `B(5)` | ≥ 0.3 s CPU | 0.98 s | 1.02 s | yes / yes |
| (a)-2, cheap-near, case 2 (`rows35`) window | ≥ 0.15 s CPU | 2.22 s | 2.12 s | yes / yes |
| (a)-2, cheap-near, case 3 (`index36/235`) window | ≥ 0.15 s CPU | 1.94 s | 1.94 s | yes / yes |
| (a)-1, heavy-finite, case 4 (`tdf161948`) window | some thread clears `BUSY_BAR` | **not measurable — see below** | **not measurable — see below** | n/a |
| **controls-behave** | (3) AND ((1) OR (2)) | **true** | **true** | — |

Controls behave in both runs via (3) AND (2); (1) did not produce a
measurement (next section). Per the protocol, controls-behave holding on (2)
and (3) alone is sufficient — (1) failing to produce a figure does not void
the run.

### Control (a)-1 — `case4HeavyFinite: null`, its own section, not a footnote

**What actually happened, stated precisely: case 4 opened successfully in
both runs, but far faster than the banked figure, and the resulting time
window this protocol's method builds around it was empty — no thread failed
`BUSY_BAR`; no window existed for any thread to fail it in.**

- `findings/evidence/089/ladder-2026-09-06.txt` banks `tdf161948_NaturalSort
  SaveLoad.ods` at **30,688 ms** — the slowest opening file in the 306-fixture
  sweep, which is why the protocol chose it as the "heavy and finite" busy
  control.
- In this session, case 4 opened in **1,090 ms** (run 1) and **1,046 ms**
  (run 2) — both times reported directly from `run-<N>-probe.json`'s
  `cases[].elapsedMs`, and both times case 4 `opened: true` with no error.
- This protocol's operationalisation of "case *k*'s open window" is a time
  slice `[T_k, T_(k+1))` derived from a CDP phase-stamp poll on a **2 s**
  cadence (section 3.6 step 4; the cadence is the protocol's own, not chosen
  here). With case 4 finishing in ~1 s, the poll that first saw
  `cases.length >= 4` and the poll that first saw `cases.length >= 5` were the
  **same poll** in both runs (`caseBoundaries["4"] == caseBoundaries["5"]`
  exactly, to the recorded double, in both `run-1-verdict.json` and
  `run-2-verdict.json`). `window_activity()` therefore received
  `w_end <= w_start` and returned `None` before computing any rate —
  `controls.case4HeavyFinite` is `null` for that reason alone.
- This is a **different** situation from the one the protocol's section 3.4a
  pre-registers a "record prominently" clause for (a 30 s *successful* open
  showing *no CPU*, which would say something about the whole stack). That
  did not happen here: case 4 was never slow enough this session for the
  2 s-granularity method to form a window to test at all. Recorded because
  the protocol asks for it to be recorded, not interpreted as evidence about
  case 4, case 5, or anything the busy control was meant to probe.
- Consequence for this task: **control (a)-1 was not exercised in either
  run.** The controls-behave predicate is satisfied through (2) and (3)
  alone, per the protocol's own "at least one of (1) or (2)" wording.

### Control (b) — known-idle (`idle_control.py`, run 3 of the budget)

180.0005 s settled window, 361/361 ticks all "tree found" (0 empty ticks),
`pageDoneError: null`.

| requirement | measured | holds |
| --- | ---: | :---: |
| every renderer thread's mean rate < `QUIET_BAR` (0.02) | max renderer-thread rate 0.000333 | yes |
| `maxRateAllThreads` < `NOISE_BAR` (0.10) | 0.005833 | yes |

`quietBarHeld: true`, `noiseBarHeld: true`, `status: "ok"`. This establishes
that the sampler reports real zeros over a settled 180 s window on this page
— not its constant output — with the named limit the protocol registers:
because the page disposes the engine at the end of a case, this control has
no *live engine thread* to read zero for; it is control (b) plus the in-band
`B(5)`-vs-`H` comparison above, together, that cover both halves.

## The two measurement runs, in full

| field | run 1 | run 2 |
| --- | --- | --- |
| started (UTC) | 2026-09-07T09:23:54.057Z | 2026-09-07T09:32:12.156Z |
| completed (UTC) | 2026-09-07T09:27:05.168Z | 2026-09-07T09:35:23.698Z |
| `verdict.controlOdtOpened` | true | true |
| case 2/3/4 `opened` | true / true / true | true / true / true |
| case 5 `opened` | false, `TIMEOUT`, "open timed out after 180000 ms" | false, `TIMEOUT`, "open timed out after 180000 ms" |
| `openTimeoutMs` | 180000 | 180000 |
| `inputs[].sha256` match section 1.5 | yes | yes |
| `gen5FirstAppearance` (tMono) | 198081.2655 | 198579.3640 |
| `H` window | [198101.2655, 198261.7658] | [198599.3640, 198759.8640] |
| `H` length | 160.50 s (≥ 120 s required) | 160.50 s |
| `GEN(5)` tid count | 14 | 14 |
| `maxRateAllThreads` over `H` (whole tree) | 0.004984 | 0.004299 |
| `maxRateOutsideCandidate` over `H` | 0.004984 | 0.004299 |
| `noiseBarHeld` | true | true |
| duty cycle (5 s sub-windows ≥ `BUSY_BAR`) | 0 / 32 | 0 / 32 |
| `cpuBoundTids` | [] | [] |
| `threadIdentification` | ambiguous | ambiguous |
| max sample gap inside `H` / empty ticks inside `H` | 0.50 s / 0 | 0.50 s / 0 |
| other Chrome processes at start | 0 | 0 |
| `git status --porcelain` guard violation | none | none |

Both runs agree on outcome class (Waiting), both pass the non-vacuity gate
(section 4.5), both have `|H|` well above the 120 s void floor, and neither
shows a sample gap or empty-tree tick inside `H`.

**Identification note (section 2.4).** `threadIdentification: "ambiguous"` in
both runs: `GEN(5)` (defined as "renderer thread absent at the renderer's
birth, present at the run's last sample") includes, in both runs, threads
from **two** renderer-type processes — the page's own renderer (a handful of
`DedicatedWorker` + `MemoryInfra` threads) and a second renderer process that
came into existence at almost exactly `gen5FirstAppearance` and carries a full
set of ordinary renderer baseline threads (`Compositor`, `HangWatcher`,
`ThreadPoolForeg`, etc.). No attempt was made to decide which one is "the
real" case-5 worker generation: per section 2.4, since **every** candidate
tid reads near-zero over `H` (max 0.0006–0.0007 cores), the answer is
unanimous across the whole ambiguous set, so the Waiting verdict stands and
the naming does not matter. The full per-tid table is in
`run-<N>-verdict.json` under `gen5PerTidH`.

## Uninterpreted payload (recorded, not interpreted in the verdict)

Per `GEN(5)` tid, over `H`, in both runs: state-character histogram was **100%
`S`** for every tid with a complete sample count (one late-born tid,
`MemoryInfra`, shows 100% `S` over its shorter post-birth span too — see
`stateHistogramH` in the verdict files); context-switch deltas
(`ctxtDeltaH`) range from 0 to ~1,600 voluntary switches and 0–15
nonvoluntary, varying by tid, over the ~160 s window; `wchan` is constant per
tid across every sample of `H` (either `futex_do_wait` or `ep_poll`,
depending on the tid, in both runs); `syscall` likewise reads either one or
two distinct raw `/proc/.../syscall` lines per tid throughout `H`, always
under a single syscall number per tid (202 for the `futex_do_wait` tids, 232
for the `ep_poll` tids — the raw line's first field) — several tids show
exactly two distinct argument-value lines under that same number across `H`
rather than one, both runs agreeing on which tids do. The
full per-tid `wchanCountsH` / `syscallCountsH` maps (distinct values seen,
with sample counts) are in `run-1-verdict.json` and `run-2-verdict.json`
under `gen5PerTidH`. **These numbers are recorded because section 3.1 and
4.2 require it and are not read by any outcome logic in `analyse.py` — no
syscall number, wchan string, or argument value appears in the outcome
determination, and none is named as a mechanism here.**

## Identity check (section 1.5)

All 14 fixed-file hashes matched the pre-registered table exactly
(`fixedFilesAllMatch: true`, `mismatches: []` in `identity.json`). No stop
condition triggered. Recorded alongside: `google-chrome --version` = Google
Chrome 151.0.7922.169; `getconf CLK_TCK` = 100; `uname -r` =
7.0.0-30-generic; `git rev-parse HEAD` at the time of the check = `c08323d3
230996745ee42b61dd383a8e01c390cb` (the tree advanced by one unrelated commit,
`handoff/RUNBOOK-operator-T4-manual-round.md`, between this task's drafting
commit `e7a71edd` and the identity check — touching none of the 14 hashed
paths; `git status --porcelain` was clean of anything but this task's own new
directory throughout). `build_row_ladder.py --verify` printed
`content.xml identical=True` for `rows20` and `rows50` and the required
`verify:` line (`build-verify.txt`).

## Red cases (section 7)

| case | required record | actual | matches |
| --- | --- | --- | :---: |
| R-A (`--force-tid 999999`) | `{"status":"void","reason":"tid 999999 is absent from every sample"}` | identical | yes |
| R-D (sampler vs a `sleep 5` pid, no Chrome child) | `{"status":"no-tree"}`, non-zero exit | `{"status":"no-tree", ...}`, exit 1 | yes |
| R-B (`--force-thread comm=CrBrowserMain`) | `{"status":"void","reason":"controls did not behave on the selected thread"}` | `{"status":"void","reason":"no thread with comm='CrBrowserMain' in any sample"}` | **no — see below** |
| R-C (`--force-thread comm=CrRendererMain`) | same shape as R-B | `{"status":"void","reason":"no thread with comm='CrRendererMain' in any sample"}` | **no — see below** |

**R-B/R-C found unsatisfiable as literally written, reported rather than
repaired.** Run 1's entire sample stream was scanned exhaustively for every
distinct `comm` value recorded, across all 383 ticks and every process in
the tree: the comm of every process's main thread — browser, every renderer,
the zygote, every utility process — is literally `chrome`, not
`CrBrowserMain` or `CrRendererMain`. Google Chrome 151.0.7922.169 on this
machine does not rename process main threads via `prctl(PR_SET_NAME)` the
way the protocol's premise assumed. `analyse.py --force-thread` correctly
reports a void for "no thread with that comm exists" rather than fabricating
a match, degrading to the pre-registered wording, or silently substituting a
different selection rule (e.g. matching a thread by `tid == pid`, which
would have been a new, un-pre-registered identification mechanism). Full
detail in `redcase-R-B.json` and `redcase-R-C.json`.

**Consequence, stated plainly: the busy control's *negative*-discriminating
power — that it correctly rejects a genuinely near-idle, mis-pointed thread —
was not demonstrated by a dedicated red case in this session.** Its
*positive*-discriminating power (accepting genuinely busy tids) was
exercised live by every controls-behave check above. R-A and R-D's checks
(an absent tid, an absent tree) did pass and are unaffected by this gap.

## Instrument fixes made mid-session, before any verdict was finalised

Recorded here because `identity.json`'s `notes` list gives the same account
with exact sha256 values; this is the plain-language version.

1. **`analyse.py`'s CPU-bound test originally checked only the `SUSTAINED`
   fraction**, not the section 3.3 `BUSY_BAR` mean-rate requirement over the
   whole of `H` — both are required by section 4.1's two explicit clauses.
   Fixed before any real sample data was analysed with the looser version.
2. **A data-shape mismatch**: `run_one.py` nested the CDP phase stamps under
   `meta["cdp"]["phaseStamps"]`; `analyse.py` read only the top-level
   `meta["phaseStamps"]`. Unfixed, every run would have voided on the
   controls-behave predicate for a wiring reason, not a measurement one.
   Fixed on both sides (`run_one.py` now writes both locations for future
   runs; `analyse.py` accepts either). Run 1's own verdict was regenerated
   over its already-banked sample stream after the fix — no browser was
   re-run for this.
3. **`wchan`/`syscall` were sampled but discarded** during `analyse.py`'s
   reshaping step; both runs' verdicts were regenerated over their banked
   streams to add this payload once found missing. No browser was re-run.
4. **`idle_control.py`'s scratch root needed a fifth symlink**
   (`sdk -> wasm_sdk_probe/dist/sdk`, read-only, whole directory) beyond the
   protocol's literally-named four: `ods-decisive-probe-app.js` imports
   `./sdk/document-sdk.js` relative to itself, which the real measurement
   runs get for free from `build_mirror()`'s fallback symlinking but the
   idle control's hand-built root does not unless added. Documented in
   `idle_control.py`'s module docstring and in `idle-1-meta.json`'s
   `symlinks` map.

None of these changed any threshold, window definition, or outcome category;
all were fixed before the first verdict that used them was finalised, and
runs 1 and 2's final, reported figures above are the post-fix ones (run 1's
verdict was written twice — the fix history is in the `identity.json`
notes — run 2's was written once, correctly, since both fixes landed before
it started).

## What remains unmeasured

- **What the blocked threads are blocked *in*.** Not measured here by
  design (section 4.2's "next question"); needs either a debug build or a
  debugger attach, with its own attribution discipline, and is explicitly a
  separate task.
- **The busy control's negative-discriminating power**, per the R-B/R-C gap
  above: whether the controls-behave predicate would correctly reject a
  genuinely near-idle, mis-pointed thread was not demonstrated this session.
- **The secondary profiling instrument (section 3.5, run 4) was not
  attempted.** It is gated on runs 1–2 reading CPU-bound or mixed; both read
  Waiting, so — per the protocol's own text ("If the answer is 'waiting', a
  CPU profile has nothing to sample") — it was correctly skipped, not
  omitted.
- **Whether case 4's fast opens (1.09 s / 1.05 s, against a banked 30,688 ms)
  are themselves stable, notable, or a measurement artefact of this
  environment.** Recorded as an observation twice-reproduced within this
  session; not investigated further, and no cause is offered for it here —
  that would be exactly the kind of attribution this task may not make, and
  it is outside this protocol's one question besides.
- **Two runs, one machine, one day.** Runs 1 and 2 agreeing is agreement of
  two runs on one machine on one day, not a claim about every environment or
  every day; the protocol's stop rule treats two agreeing non-void runs plus
  a passing idle control as sufficient to stop, and that is what stopped
  this session — it is not a claim that a third or fourth run would
  necessarily agree.

## Budget used

3 of 8 runs: run 1 (measurement), run 2 (measurement), idle control (run 3).
Run 4 (profile) correctly not attempted (outcome is Waiting, not CPU-bound or
mixed). Runs 5–8 (reserve) not used. Stop rule satisfied: runs 1 and 2 both
produced non-void verdicts agreeing on outcome class (Waiting), the idle
control passed, and all four red cases of section 7 were recorded (two as
specified, two found unsatisfiable as written and reported as such).
