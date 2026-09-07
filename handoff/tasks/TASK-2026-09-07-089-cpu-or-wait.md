# TASK — finding 089: during the `rows36` hang, is the engine burning CPU or is it waiting?

Pre-registered measurement protocol for finding
`findings/089-a-13kb-spreadsheet-with-a-full-height-repeated-row-times-out-on-wasm-but-opens-in-269ms-natively.md`.
Drafted by the opus seat on 2026-09-07 from the banked evidence in
`findings/evidence/089/`, **before any run of this protocol has been made**.
Every criterion below is pre-registered. `AGENTS.md` §9 governs anything added
after the first run that counts.

**The one question.** `tdf149752-rows36.ods` (`Index ≥ 35` **and** `Index2 ≥ 36`)
does not finish opening on `e2-editor-v12` in 1,800 s; the same file on the same
core commit opens natively in 1,404 ms. **Is the engine computing, or is it
blocked?** Those two answers point at disjoint families of cause and every
measurement banked so far is compatible with both.

**The one thing this protocol may not do.** It may not name a cause. 089 has
refused attribution twice on the record (once after a bisect whose premise was
wrong, once after the ladder turned out to have measured a diagonal), and that
refusal stands. "Computing" and "blocked" are properties of a thread over an
interval; *what* it computes and *what* it waits for are not measured here and
must not appear in any file this task produces. `AGENTS.md` §7 — verify the
claim, not a proxy for it; and finding 040's precedent, quoted in 089 itself: a
confident wrong attribution costs more than the open question.

- **Structure rule.** The executor may write **only** two things: (a) files
  under the new directory `findings/evidence/089/cpu-or-wait-2026-09-07/`, and
  (b) one appended section under `## Execution record` at the end of *this*
  file. No file anywhere else in the tree may be created, edited, moved or
  deleted. Named explicitly, because each has a reason: not
  `wasm_sdk_probe/web/` and not `wasm_sdk_probe/dist/` and not any profile (the
  cutover gate is mid-count and the page identity must not move); not any
  `check_*.py` or other judge; nothing under `findings/evidence/queue-v12-*`;
  nothing else under `findings/evidence/089/` except the new subdirectory (the
  banked fixtures are the anchor of every report already taken — see §1.4 for
  the specific way this task could destroy them by accident); not
  `.gitignore` (`!/findings` already tracks the new directory).
- **Role.** The executor is the sonnet seat: it runs the procedure and records
  what happened. It is **not** the drafting party and carries no judgement. It
  does not name a cause, does not decide what the result means for the ODS
  milestone, and does not relax a criterion. If a criterion turns out to be
  unsatisfiable as written, the executor **stops and reports** — it does not
  rewrite the criterion and it does not build machinery to make one hold
  (`AGENTS.md` §4, self-check: if you find yourself writing a new mechanism
  rather than a test or a sentence, stop and report). `AGENTS.md` §11 is why:
  the drafting party's own measurements were wrong six times in one session on
  2026-08-29, and the remedy adopted was §8 — the terminating declaration is not
  carried by the party that drafted it.

Where the brief lands: item 1 → §1; item 2 → §2; item 3 → §3; item 4 → §4;
item 5 → §5; item 6 → §6; item 7 → §7.

---

## 1. The object, and its identity

### 1.1 What is opened

Five documents, in this order, in one browser session. The probe creates and
disposes **a fresh engine per case** (`web/ods-decisive-probe-app.js`,
`runCase`), so each case owns its own worker and its own pthreads — this is
load-bearing for §2 and §3 and is not an incidental detail.

| # | file | kind | banked behaviour |
| --- | --- | --- | --- |
| 1 | `wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt` | `--control` | opens, ~1,800 ms |
| 2 | `findings/evidence/089/tdf149752-rows35.ods` | fixture | opens, 1,245–1,600 ms |
| 3 | `findings/evidence/089/tdf149752-index36-index235.ods` | fixture | opens, 1,589 ms |
| 4 | `wasm_sdk_probe/test-docs/ods/upstream/tdf161948_NaturalSortSaveLoad.ods` | fixture | opens, **30,688 ms** |
| 5 | `findings/evidence/089/tdf149752-rows36.ods` | fixture | **does not open**; TIMEOUT |

Case 3 is the near neighbour on the other axis: `Index = 36, Index2 = 35`, one
row away from case 5 in each direction, and it opens. Case 4 is the *deliberately
heavy but finite* open — the slowest opening file in the whole 306-fixture sweep
(`findings/evidence/m4-ods/04-sweep-v12.json`), and it is here only as a control
(§3.4), not because anything about it is being investigated.

Profile: `e2-editor-v12` — the same one every row in 089 was taken on.

### 1.2 The native numbers, quoted, not re-measured

From `findings/evidence/089/native-ladder-2026-09-06.txt` (core commit
`671c848b…`, `-O2`, `build-native-26-8/instdir/program`): `rows35` 1,410 ms,
`rows36` 1,404 ms, and the whole twelve-file ladder flat between 1,399.59 and
1,416.87 ms. **Nothing native is run in this task.** Those numbers are the reason
the question is worth asking and are context only.

### 1.3 How the fixtures were built

`findings/evidence/089/build_row_ladder.py`. It shortens the two named ranges
inside `<table:named-expressions>` and nothing else; `--split INDEX INDEX2` sets
them independently, and its `(35,35)` output is byte-identical in `content.xml`
to the ladder's `rows35`.

**Before run 1**, and once only, the executor runs the builder's own verifier:

```
python3 /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/build_row_ladder.py --verify
```

It must print `content.xml identical=True` for `rows20` and `rows50` and the
line `verify: the banked fixtures are what this script produces`. Save the
output to `cpu-or-wait-2026-09-07/build-verify.txt`. If it does not print that,
**stop and report**: the fixtures are not what the script makes and nothing
downstream is about the documents 089 measured.

### 1.4 The way this task could destroy the banked evidence, named so it does not happen

`build_row_ladder.py` writes to `OUT_DIR = Path(__file__).parent`, which is the
**banked** `findings/evidence/089/`. `--rows` and `--split` therefore overwrite
banked fixtures in place, and because zip metadata is not reproduced, the whole-
zip sha256 would change even where `content.xml` did not — which would break the
`inputs[].sha256` line of every report already banked. **Run `--verify` and
nothing else.** `--verify` builds into a `TemporaryDirectory` and writes nothing
to `OUT_DIR`.

### 1.5 Identity, recorded and compared before the first run

The executor writes `cpu-or-wait-2026-09-07/identity.json` containing the
sha256 of every file below, computed fresh, and compares each against this
table, which was computed on 2026-09-07 while this task was drafted. **Any
mismatch: stop and report.** Do not "update the table".

| file | sha256 |
| --- | --- |
| `findings/evidence/089/tdf149752-rows35.ods` | `a16ac9c5a1e450d6de1a5f586a1a18595dcabf72654dec4852d4aa2bf70524ee` |
| `findings/evidence/089/tdf149752-rows36.ods` | `87b92dbeb653fefcfc9d3017ad646e25431fa51a6981f26220036881b7649a70` |
| `findings/evidence/089/tdf149752-index36-index235.ods` | `ea10861849df43dbf4e54a1ac34a64434f262090a8b7ce74f835e1da39efc6e6` |
| `findings/evidence/089/tdf149752-index35-index236.ods` | `b28d71507d28b6b789636b7e182cd8bacc5cf929c8342b0f9ca9bb3cbdd33809` |
| `findings/evidence/089/build_row_ladder.py` | `53c771637bc72b25a36adb7f66c6aed8163eaa963d5ad7beda5abbe3c77252c6` |
| `wasm_sdk_probe/test-docs/ods/upstream/tdf149752.ods` | `2d6a2c6aa63c33b0971ef7e3e67b7fc5727639387e5a6eb8c73ae86194f0052e` |
| `wasm_sdk_probe/test-docs/ods/upstream/tdf161948_NaturalSortSaveLoad.ods` | `ef161c0600bace29e04e51b0e5f57204178a0a809686d7c947ea29648a3a02bc` |
| `wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt` | `f89f1e63dcf7c8956f3986257dd79a7ed02bb7825c844a63f73abc4a5c68d241` |
| `wasm_sdk_probe/tools/probe_ods_on_profile.py` | `5c8d567f7a92b39274379a6d9ec3e01c4981b16743b7f64eaf4af88851e34c8a` |
| `wasm_sdk_probe/tools/run_browser_probe.py` | `663b2ffab8174afc070401a15afac18c9ba12950b6a39f146b331ceeab7d8e3e` |
| `wasm_sdk_probe/web/ods-decisive-probe-app.js` | `36326957b26199082ca4667bc8ed95798e9eca57cd4978e81a0f11d395f3099e` |
| `wasm_sdk_probe/web/ods-decisive-probe.html` | `4009fc481d589838d2750831b6e95b4c6802982200ecb1d05a7c9fca40f9a204` |
| `wasm_sdk_probe/dist/profiles/e2-editor-v12/probe.wasm` | `4ec1e389aaab3b0335875d06044639e33e94de777d04f15bb133d0d9e34ef452` |
| `wasm_sdk_probe/dist/profiles/e2-editor-v12/sdk-manifest.json` | `2734229351dac1da514df08ada878a47af442d729ff42195d43e5d9c6794d5be` |

`identity.json` also records: `google-chrome --version`, `getconf CLK_TCK`,
`uname -r`, `git rev-parse HEAD`, and the sha256 of every script the executor
itself writes (§3.6), taken **after** they are written and **before** run 1.

The probe also records fixture hashes in-band (`inputs[].sha256`), so every run
report carries its own identity independently of this table; §4.5 requires the
two to agree.

### 1.6 Where the evidence goes

`findings/evidence/089/cpu-or-wait-2026-09-07/`, new, and nothing else. Files:

```
identity.json              build-verify.txt
sample_threads.py          idle_control.py          analyse.py     run_one.py
run-<N>-probe.json         run-<N>-samples.jsonl.gz run-<N>-meta.json
run-<N>-verdict.json
idle-<N>-samples.jsonl.gz  idle-<N>-meta.json       idle-<N>-verdict.json
redcase-<name>.json
RESULT.md
```

`RESULT.md` is in **English** (`AGENTS.md`: `findings/evidence/**` is English)
and carries the tables, the verdict, the raw numbers, and — if any — the list of
things that did not work. It does not carry a cause.

---

## 2. Which thread, named before measuring

This tree's most repeated failure is measuring one thing and signing for another
(`AGENTS.md` §11; 2026-08-23, five times in one day). So identification is
written down here, before any sample is taken, and it is written so that **the
central verdict does not depend on picking a thread at all**.

### 2.1 The shape of the thing being identified

The engine is Emscripten with pthreads: `dist/profiles/e2-editor-v12/probe.js`
contains `new Worker(pthreadMainJs, {workerData:"em-pthread", name:"em-pthread"})`
and 55 `proxyToMainThread` sites. So one open involves, in the renderer process:
the page's main thread, the SDK worker's thread (`sdk-worker.js`), and one or
more `em-pthread` worker threads, all of which Chrome runs as dedicated-worker
threads inside **one renderer process**. The boot of a case and the `open` of
that case may therefore run on **different** threads of the same generation.
Nothing below assumes they are the same thread.

### 2.2 Process identification — `/proc` first, CDP as cross-check

* **C1 (primary, `/proc` only, exact).** `run_one.py` launches the probe as its
  own subprocess, so it knows the probe's pid. `ChromeSession.__init__` does
  `subprocess.Popen([...])`, so the Chrome **browser** process is a direct child
  of the probe. Discover it by iterating `pgrep -x chrome` (and `pgrep -x
  google-chrome`), reading `/proc/$p/stat` field 4 for ppid, and keeping the one
  whose ppid is the probe pid — or, if `/usr/bin/google-chrome` (a wrapper) did
  not `exec`, whose grandparent is the probe pid. Record which of the two held.
  Then take the **ppid closure** over all `chrome` processes to get the whole
  tree (renderers are forked from a zygote whose parent is the browser).
* **C2 (`/proc`, classification).** Read `/proc/<pid>/cmdline` for every process
  in the tree and classify by the `--type=` flag: absent → browser;
  `renderer` / `gpu-process` / `utility` / `zygote`. Record every cmdline
  verbatim in `run-<N>-meta.json`, including the browser's
  `--user-data-dir=` and `--remote-debugging-port=` values.
* **C3 (CDP, best effort).** From a **second** websocket to the browser-level
  endpoint (`GET http://127.0.0.1:<port>/json/version` →
  `webSocketDebuggerUrl`), call `SystemInfo.getProcessInfo`. It returns
  `{type, id (pid), cpuTime}` per process, from Chrome itself. Its renderer pid
  set must equal C1∩C2's. If the method is unavailable or errors, record the
  error verbatim and continue — C1+C2 stand alone.
* **C4 (CDP, best effort).** `Target.getTargets` once per case, recording every
  target's `type`, `url`, `targetId`. The count of worker targets whose url ends
  `sdk-worker.js` or `probe.js` is the cross-check on the number of worker-family
  threads seen in `/proc`. Do **not** attach to a worker target in runs 1–2
  (§3.5 reserves that for run 4): attaching changes the thing being measured.
* **C5 (`/proc`, corroboration).** `VmRSS` from `/proc/<pid>/status` per process
  each sample. The renderer holding the wasm heap is hundreds of MB; a spare
  renderer is tens. Recorded, not decisive.

### 2.3 Thread identification, and the generation trick

For every process in the tree, every sample, enumerate `/proc/<pid>/task/` and
read for each tid: `comm`, and from `stat` the state character, `utime`,
`stime`, `processor`; from `status` the two context-switch counters. **Every
thread of every process in the tree is sampled — not a selected one.** That is
deliberate: the central question ("is anything computing") is then answerable
without having identified anything.

Define, from the sample stream alone:

* `GEN(k)` — the set of tids in the renderer that first appear at or after the
  start of case *k* and (for cases 1–4) vanish before case *k+1* begins; for
  case 5, are still present at the last sample. Because the page disposes the
  engine at the end of every case, each case's worker threads are born and die
  inside it, and the generations are separated in the sample stream without any
  naming at all.
* `B(k)` — the boot window of case *k*: from the first appearance of `GEN(k)` to
  +10 s, clipped to case *k*.
* `H` — the hang window: from first appearance of `GEN(5)` **+20 s** to the last
  sample **−5 s**. Twenty seconds is a huge margin over a boot that costs about
  a second and an `open` that costs under 400 ms warm
  (`findings/evidence/089/openTimeout-knob.md`), and it exists so that no part
  of `H` can contain legitimate boot work. Expected `|H| ≈ 155 s`; **`|H| < 120 s`
  voids the run** (§4.4).

Do **not** hardcode a comm string. Record what `comm` actually says (Chrome's
dedicated-worker threads are expected to read `DedicatedWorker`, truncated to
15 bytes, and there will be several of them) and let the table say it.

### 2.4 What to do when identification is ambiguous

Several threads will share a `comm`, and C4's worker-target count may not map
one-to-one onto them. That is expected and it is not a failure. The rule:

* If the CPU-vs-wait answer is **unanimous over every candidate** in `GEN(5)`
  (all of them near-zero, or exactly one of them busy and the rest near-zero),
  report the answer and set `threadIdentification: "ambiguous"` with the whole
  per-tid table beside it. The answer stands; the naming does not.
* If candidates **disagree** (some busy, some not, in a way that changes the
  verdict), the verdict is `mixed` (§4.3) and the record says so.
* Never pick one tid because it looks right. Never write a tid into the verdict
  that C1–C5 did not converge on. If asked for one and there is none, the record
  says "not identified" — that is a result, not a gap to be filled.

---

## 3. The discriminator, and the two positive controls

### 3.1 The primary instrument: per-thread CPU deltas from `/proc`

`sample_threads.py`, written by the executor into the evidence directory,
sampling **every 500 ms** for the whole life of the browser. 500 ms rather than
the brief's 2 s because the cheap busy control (§3.4b) is a burst under 400 ms
and must land in more than one sample; `H` is 155 s long, so the hang side loses
nothing.

Parse `stat` exactly like this — `comm` can contain spaces and parentheses, so
split after the **last** `)`, and the field indices are off by three:

```python
raw  = open(f"/proc/{pid}/task/{tid}/stat", "rb").read().decode("utf-8", "replace")
rest = raw[raw.rindex(")") + 2:].split()   # rindex, not index
state       = rest[0]        # field  3   R running, S sleep, D uninterruptible
utime       = int(rest[11])  # field 14   clock ticks
stime       = int(rest[12])  # field 15   clock ticks
processor   = int(rest[36])  # field 39
```

`getconf CLK_TCK` is 100 on this machine (recorded in `identity.json`, not
assumed by the parser): one tick is 10 ms, so per-sample quantisation is 2 % of
a core — coarse per sample, irrelevant over `H`, where 0.05 cores is 775 ticks.

Per sample also record from `/proc/<pid>/task/<tid>/status`:
`voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches`. These are a second,
independent signature: a thread spinning on CPU shows nonvoluntary switches at
roughly the scheduler tick rate and almost no voluntary ones; a thread parked
shows almost none of either; a thread ping-ponging shows many voluntary ones.

Best effort, recorded raw and **not interpreted in the verdict**:
`/proc/<pid>/task/<tid>/wchan` and `/proc/<pid>/task/<tid>/syscall`. If they are
unreadable or return `0`, record that verbatim. They may appear in `RESULT.md`
under a heading that says "recorded, not interpreted"; they may not appear in
the verdict, because naming *what* is waited on is the attribution this task may
not make.

**Payload, not a summary of the payload** (`AGENTS.md` §7). Keep the raw `stat`
line verbatim for: every thread's first and last sample; every sample of every
tid in `GEN(5)`; and every 40th sample for all threads. Gzip the stream at the
end (`run-<N>-samples.jsonl.gz`). Expected size well under 10 MB compressed.

Loop discipline: absolute deadlines (`next_t += 0.5`), record `sampleLagMs` per
sample, tolerate `FileNotFoundError` on a thread that exited (record it as
`gone`, do not drop the sample), and **fail loudly with `status: "no-tree"` if
zero Chrome processes are found** — see §7 red case R-D.

### 3.2 What the discriminator computes

For a thread *t* and a window *W*: `rate(t, W) = ΔCPU(t, W) / |W|`, in cores,
where `ΔCPU = (Δutime + Δstime) / CLK_TCK`. `analyse.py` derives, and writes
into `run-<N>-verdict.json`:

* `rate(t, H)` for **every** tid in the tree, sorted;
* `maxRateAllThreads(H)` — the maximum over the whole tree, which is the
  identification-free half of the answer;
* `rate(t, H)` restricted to `GEN(5)`, per tid;
* the duty cycle: the fraction of 5 s sub-windows of `H` in which some `GEN(5)`
  thread has `rate ≥ 0.5`;
* the state-character histogram per `GEN(5)` tid over `H`;
* the context-switch deltas per `GEN(5)` tid over `H`;
* the same quantities over `B(1..5)` and over each case's open window.

### 3.3 Thresholds, fixed here

| name | definition |
| --- | --- |
| `BUSY_BAR` | mean `rate ≥ 0.5` cores over the window |
| `QUIET_BAR` | mean `rate < 0.02` cores over the window, per thread |
| `NOISE_BAR` | mean `rate < 0.10` cores, for threads outside `GEN(5)` |
| `SUSTAINED` | `rate ≥ 0.5` in ≥ 90 % of the 5 s sub-windows of the window |

### 3.4 The two positive controls — both mandatory

Without both, "we saw near-zero CPU" and "the instrument never attached" are the
same picture. `AGENTS.md`, and this tree's own rule from 2026-08-21: every arm
that says "X did not happen" needs a positive arm, or "nothing happened" and
"the mechanism never ran" look identical and both look green.

**(a) Known-busy — three of them, and the third is the one that matters.**

1. *Heavy and finite*: case 4, `tdf161948_NaturalSortSaveLoad.ods`, banked at
   30,688 ms and opening. Requirement: some thread in `GEN(4)` clears `BUSY_BAR`
   over that case's open window.
2. *Cheap and near*: case 2 (`rows35`) and case 3 (`index36/index2-35`).
   Requirement: `GEN(2)` and `GEN(3)` accumulate ≥ 0.15 s CPU each within their
   open windows.
3. *In-band, same threads as the hang*: `B(5)` — the boot of the very generation
   that then hangs. Requirement: `GEN(5)` accumulates **≥ 0.3 s CPU** within
   `B(5)`. This is the strongest of the three because it is the same tids, the
   same process, the same run, minutes apart: if `GEN(5)` shows CPU during
   `B(5)` and none during `H`, "the instrument never attached to those threads"
   is excluded by construction.

**Controls-behave predicate**: (3) is **required**, and at least one of (1) or
(2) must also hold. If (1) fails while (2) and (3) hold — i.e. a 30 s *successful*
open also shows no CPU — that is not a quiet failure to be swallowed: record it
prominently in `RESULT.md`, because it says something about this stack much
broader than 089, and it makes the busy control weaker than intended. Report it;
do not interpret it.

**(b) Known-idle — the same instrument, on the same page, settled.**

A separate short run, `idle_control.py`, because the probe closes the browser the
moment it is done and leaves no settled tail:

1. Serve the page source directory read-only:
   `python3 wasm_sdk_probe/web/serve.py --port <free> --root wasm_sdk_probe/web`
   is not enough on its own, because the page fetches `./profiles/<profile>/…`
   and the case files. Build a scratch root under the scratchpad containing four
   **symlinks**: `ods-decisive-probe.html`, `ods-decisive-probe-app.js`,
   `profiles/e2-editor-v12` → the profile directory, and `ods-cases/d1-anchors.odt`.
   `serve.py` uses `SimpleHTTPRequestHandler(directory=…)` and follows symlinks;
   it also sets the COOP/COEP headers the pthread build needs. **Symlinks only —
   nothing under `web/`, `dist/` or the profile is copied, written or modified.**
2. Launch a browser with `ChromeSession("cold")` imported from
   `wasm_sdk_probe/tools/run_browser_probe.py` (import, do not edit), navigate to
   `…/ods-decisive-probe.html?profile=e2-editor-v12&openTimeoutMs=180000&cases=<inline JSON>`
   with the inline case list holding the ODT control only. The page reads
   `params.get("cases")` before falling back to `ods-cases.json`, so no mirror is
   needed.
3. Wait for `window.__odsProbe.done`.
4. **Keep sampling for 180 s with the page settled**, then close.

Requirement: over that 180 s window, every surviving thread of the page's
renderer is under `QUIET_BAR`, and the run's `maxRateAllThreads` is under
`NOISE_BAR`. This is what proves the sampler's near-zero is a measurement and
not its constant output.

**Its named limit, registered now.** The page disposes the engine at the end of
the case, so during the idle window there is no live engine thread to report
zero for. The idle control therefore establishes "this sampler reports real
zeros over a 180 s window on this page", not "an idle engine thread reads zero".
The second statement is not obtainable without changing `web/`, which this task
may not do. That is why control (a)(3) exists: it covers the same-thread half
from the other side.

### 3.5 The secondary instrument: a sampling profile, best effort, run 4 only

Attempted **only if** runs 1–2 land on CPU-bound or mixed. If the answer is
"waiting", a CPU profile has nothing to sample and the run is skipped with that
reason recorded.

* **S1 — `Profiler` on the worker target.** `Target.setAutoAttach`
  (`{autoAttach: true, waitForDebuggerOnStart: false, flatten: true}`) on the
  page session to get worker sessions — `setAutoAttach`, not `attachToTarget`;
  this tree learned that on 2026-08-28. Then `Profiler.enable`,
  `Profiler.setSamplingInterval(1000)`, `Profiler.start` **before** case 5 is
  handed over, `Profiler.stop` after.
  **Pre-registered**: `Profiler.stop` is expected *not* to be serviced during the
  hang, because inspector messages for a worker are dispatched on that worker's
  own task runner. **A non-response is not evidence either way** — a thread busy
  inside one long wasm call and a thread blocked inside one both fail to answer
  identically. Record the timeout as an instrument outcome and move on.
* **S2 — browser-level `Tracing`.** `Tracing.start` with
  `disabled-by-default-cpu_profiler` plus `toplevel` on the browser endpoint,
  `Tracing.end`, stream to `redcase`-free file `run-4-trace.json.gz`. Also best
  effort: per-thread trace buffers are flushed by the threads themselves, so a
  wedged thread may contribute nothing. If it yields nothing, record the
  emptiness explicitly — an empty trace is not "no samples were taken".
* **Symbols.** There will be none: this is a stripped release wasm build.
  **An unsymbolised profile still discriminates**: samples concentrating in one
  `wasm-function[N]` frame say "computing", and their absence says nothing (see
  the non-response rule above). Record the top frames verbatim, with their
  indices, as observations. Do **not** attempt to resolve `wasm-function[N]` to
  a source symbol, and do **not** let a frame index into the verdict — that
  would be the attribution this task may not make.
* Neither S1 nor S2 can void a run and neither is required for any outcome.

### 3.6 Running one run, step by step

`run_one.py`, in the evidence directory, doing all of it in one process so the
probe pid is known exactly:

1. Check the clock window (§6). Check `git status --porcelain` and record it.
2. `subprocess.Popen` the probe, cwd `wasm_sdk_probe`, absolute paths:

```
python3 tools/probe_ods_on_profile.py \
  --profile e2-editor-v12 \
  --control /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-rows35.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-index36-index235.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/test-docs/ods/upstream/tdf161948_NaturalSortSaveLoad.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-rows36.ods \
  --open-timeout-ms 180000 --timeout 480 \
  --out /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/cpu-or-wait-2026-09-07/run-<N>-probe.json
```

3. Start the sampling loop immediately (before Chrome exists, so thread births
   are seen). Wait up to 120 s for the browser child; if none appears, kill the
   probe, mark the run void, report.
4. Start the CDP cross-check in a **separate thread** with its own websocket, so
   the sampling loop can never block on it: C3 and C4 every 10 s, plus
   `window.__odsProbe.cases.length` on the page target every 2 s as a phase
   stamp. Every call wrapped, every failure recorded verbatim. **Any CPU this
   poller induces lands on the renderer's main thread and must not be read as
   engine activity** — it is a named, expected contribution and `analyse.py`
   reports the main thread separately for exactly this reason.
5. Sample until the probe process exits, plus 2 s.
6. Write `run-<N>-meta.json` (pids, cmdlines, port, C1 route, chrome version,
   `startedAt`/`completedAt` in **both UTC and CST**, the count of *other*
   Chrome processes on the machine at start, the `git status --porcelain` before
   and after), gzip the samples, run `analyse.py`, write the verdict.
7. Clean up (§6) and re-check `git status --porcelain`.

The wall clock in UTC is required, not optional: the 2026-09-03 adjudication on
the soak bank was that a report with no wall-clock time is not a dated report.

---

## 4. What each outcome means — written before anything runs

Every outcome below is a statement about **threads over an interval**. None of
them may be extended, in any file, into a statement about what the engine is
doing algorithmically.

### 4.1 CPU-bound

**Conditions.** Controls behave (§3.4). Some thread in `GEN(5)` clears
`BUSY_BAR` and `SUSTAINED` over `H`, and its state histogram is dominated by
`R`.

**Records**: *the engine is computing, not blocked* — during the hang, a thread
of the worker generation that opened `rows36` accumulates CPU continuously for
at least 120 s.

**Does not record**: what it computes; which code; whether it would ever
terminate; whether the same is true beyond `H`; anything about `Index`/`Index2`,
`COUNTIF`, formula evaluation, or any named mechanism.

**Next question, not asked here**: where the samples land — which is S1/S2
(§3.5) or an instrumented build, and it is a separate task.

### 4.2 Waiting

**Conditions.** Controls behave. Every tid in `GEN(5)` is under `QUIET_BAR` over
`H`; every thread outside `GEN(5)` is under `NOISE_BAR`; all `GEN(5)` tids are
alive at the last sample of `H`; their state characters are in `{S, D}` in ≥ 95 %
of samples.

**Records**: *the engine is blocked, not computing* — during the hang, no thread
of the browser process tree running this open accumulates meaningful CPU.

**Does not record**: what it waits for. Not a lock, not a message, not a font,
not the main thread, not the proxying layer. `wchan` and `syscall`, if they
were readable, are recorded under a heading that says they are not interpreted.

**Next question, not asked here**: what the blocked threads are blocked *in* —
which needs either a debug build or a debugger attach, and is a separate task
with its own attribution discipline.

### 4.3 Mixed / oscillating

**Conditions.** Anything between: a `GEN(5)` mean rate in `[0.02, 0.5)`, or a
rate that clears `BUSY_BAR` in some 5 s sub-windows and not others, or `GEN(5)`
candidates that disagree with each other (§2.4).

**Records**: the measurement as measured — the per-tid mean rates, the **duty
cycle** (fraction of 5 s sub-windows above `BUSY_BAR`), the state histogram, and
the context-switch deltas. The word to use is "not resolved". Do not round a
duty cycle to "mostly waiting" or "mostly busy" and do not pick the reading that
fits a story.

**Next question, not asked here**: whether the duty cycle is periodic, which
needs a finer cadence than 500 ms and is a separate run, not a re-reading of
this one.

### 4.4 Instrument failure — void

**Any** of: the controls-behave predicate fails; the browser tree cannot be
identified (C1 finds no child, or C1/C2 and C3 disagree); `GEN(5)` cannot be
formed; `|H| < 120 s`; more than two consecutive samples are missing inside `H`;
the probe report fails §4.5; `sample_threads.py` reports `no-tree`.

**Records**: `status: "void"` and the reason, verbatim. **A void run is never
reported as "waiting"** — that is the specific misreading this whole protocol is
built to prevent, and it is the reading a broken instrument produces for free.
A voided run consumes budget (§5) and is banked with its samples.

### 4.5 The probe report's own non-vacuity gate

A run is usable only if `run-<N>-probe.json` shows all of:

* `verdict.controlOdtOpened == true`;
* cases 2, 3 and 4 `opened` truthy;
* case 5 not opened, with `error.code == "TIMEOUT"` and a message quoting
  `180000`;
* `openTimeoutMs == 180000` (the field the 2026-09-06 correction added);
* every `inputs[].sha256` equal to §1.5.

If case 5 **opens**, the hang did not reproduce on this date. That is a real and
important record on its own; the protocol stops there, `RESULT.md` says so, and
**no CPU-vs-wait claim of any kind is made**.

---

## 5. Budget and stop rule — in runs, not hours

**One run** = one invocation of `run_one.py` (~4 min: ~35 s of controls, 180 s of
hang, overhead) or one invocation of `idle_control.py` (~4 min).

**Budget: 8 runs total.**

| run | what |
| --- | --- |
| 1 | the measurement (§3.6) |
| 2 | the measurement again, an independent invocation |
| 3 | the idle control (§3.4b) |
| 4 | the profile, best effort — **only if** 1–2 read CPU-bound or mixed (§3.5) |
| 5–8 | reserve |

Reserve runs may be spent only on: replacing a voided run; or **one**
pre-named variation, chosen from exactly this list — (i) sampler cadence 100 ms,
(ii) the CDP cross-check thread disabled, to test whether the poller perturbs.
No other variation may be introduced. Nothing may be added to the criteria
mid-flight (`AGENTS.md` §9: additions need to precede satisfaction, be forced
and named, pass the form test, and carry a deadline — a variation invented after
seeing run 1 satisfies none of them).

**Stop rule.** Stop as soon as runs 1 and 2 both produce non-void verdicts that
**agree** on the outcome class (§4.1/4.2/4.3), the idle control has passed, and
the red cases of §7 have been recorded. Stop unconditionally after the 8th run.

**Default conclusion if the budget is exhausted without two agreeing non-void
runs** (`AGENTS.md` §2: every criterion carries its "if this never happens"
answer):

> **Not measured.** The CPU-vs-wait question for finding 089 remains open, and
> this protocol produced no answer to it. In particular it is **not** recorded as
> "waiting", is **not** recorded as "probably waiting", and no partial run's
> numbers are quoted as if they were the answer. What is banked is: the sample
> streams, the void reasons, and a sentence in `RESULT.md` naming which control
> or which identification step is what made the measurement unobtainable — so
> the next attempt starts from the obstacle rather than from the question.

If the *hang itself* stops reproducing (§4.5), the default is different and is
stated there.

---

## 6. Environment, as instructions

* **Headless only.** `ChromeSession` already passes `--headless=new`. Do not
  launch a headed browser, do not connect to the owner's Chrome, do not touch
  the desktop session, **do not start or use Orca** — the owner is at the
  machine. Record the number of *other* `chrome` processes at the start of each
  run (context: a busy desktop makes the machine busier, which is worth knowing
  and does not void anything).
* **Clock windows — do not run 08:10–08:45 or 15:40–16:15 CST.** Scheduled
  cutover soak runs own the machine then, and a second headless Chrome would
  contend with a gate measurement. The machine's timezone is `Asia/Taipei`, so
  `date +%H:%M` is CST directly. **Rule: start a run only if now + 20 min is
  entirely outside both windows.** If a run is somehow still in flight when a
  window opens, let it finish, start no other, and record the overlap.
* **Never `pkill -f` or `pgrep -f`.** Iterate `pgrep -x chrome` (and
  `pgrep -x google-chrome`) and read `/proc/$p/cmdline` to decide. If a run has
  to be cleaned up after an abort, kill **by pid**, and only pids whose cmdline
  contains that run's own recorded `--user-data-dir=` value.
* **Never pass `--write`** (or any other mutating flag) to any tool that has
  one. Nothing in this task writes to a shared artefact.
* **Nothing may be written** under `wasm_sdk_probe/web/`, `wasm_sdk_probe/dist/`,
  any profile, any `check_*.py` or other judge, or anywhere under
  `findings/evidence/queue-v12-*`. Reading them is required and fine: the probe
  mirrors `dist/` with symlinks into a scratch root and serves from there — its
  own docstring says a run writes nothing under `dist/`, `web/` or `sdk/`, and
  §3.6 step 1/7 is how that is checked rather than trusted. **Do not run `make`,
  do not relink, do not rebuild anything.**
* **The guard, in band.** `git status --porcelain` immediately before and
  immediately after every run, both saved into `run-<N>-meta.json`. The
  comparison is **against that run's own "before" snapshot**, not against a list
  written here: the cutover soak commits into this tree between runs (it added
  `soak-run-06/07/08-candidate.json` and two commits during the hour this task
  was drafted), so a frozen baseline would go stale and start reporting the
  soak's work as an anomaly. The only delta this task may cause is **new files
  under `findings/evidence/089/cpu-or-wait-2026-09-07/`**. Any other delta that
  is not plainly the soak's own paths under
  `findings/evidence/queue-v12-cutover-soak/`: **stop and report**. Touch none
  of the soak's paths for any reason.
* **Scratch** goes under
  `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/5553bcc0-16b3-4240-9ee3-0570a4c16e23/scratchpad`
  — the idle control's symlink root, any working file, anything not evidence.
* **Per-run `/tmp` dirs are cleaned.** After each run, remove only
  `/tmp/ods-decisive-*` and `/tmp/wasm-sdk-probe-chrome-*` whose mtime falls
  inside that run's window (the probe removes its own scratch in a `finally`,
  but an aborted run leaves both). **Leave every `/tmp/candidate-round-*`
  directory alone** — they are the cutover soak's, there were three on
  2026-09-07 (`8gtss_xh`, `mcott7q1`, `tx3ue8b9`) and there may be more by the
  time this runs; the rule is the prefix, not the list. Delete nothing outside
  the two prefixes named above, and delete nothing at all that predates the run.
* **The executor commits nothing.** It writes the evidence directory and the
  `## Execution record` section, and reports. Whether any of it is committed is
  the owner's call.

---

## 7. A red case for the instrument itself

`AGENTS.md` §6: a checker that returns green only proves it can return green.
Each red case below is run and its result written to
`cpu-or-wait-2026-09-07/redcase-<name>.json`. Three of the four need no browser
run at all — they are re-derivations over run 1's banked sample stream, which is
possible precisely because every thread is sampled (§2.3).

**R-A — a tid that does not exist.** Run `analyse.py --force-tid 999999` over
run 1's stream. **Required record**: `{"status":"void","reason":"tid 999999 is
absent from every sample"}`. If instead it emits a row of zeros and a "waiting"
verdict, the analyser is wrong, **everything it has produced is void**, the fix
is made in `analyse.py` (which lives in the evidence directory and is within the
Structure rule), and every verdict is re-derived over the **same** banked
streams — not by re-running the browser.

**R-B — the browser's main thread during a worker-side hang.** Run
`analyse.py --force-thread comm=CrBrowserMain` over run 1's stream. That thread
really is near-idle through `H`, so a naive instrument answers "waiting" — the
right answer to the wrong question, which is this tree's signature failure.
**Required record**: not "waiting" but
`{"status":"void","reason":"controls did not behave on the selected thread"}`,
because the mandatory busy predicate (§3.4a) evaluated **on that same forced
thread** fails: `CrBrowserMain` clears neither `BUSY_BAR` over case 4's open
window nor 0.3 s over `B(5)`. This is the demonstration that the busy control,
not the analyst's judgement, is what catches a mis-pointed instrument.

**R-C — the page renderer's main thread.** Same, with
`--force-thread comm=CrRendererMain` in the renderer that hosts the page.
Expected: caught the same way. **But it may not be**, because the renderer main
thread does real work driving each case (fetch, `postMessage`, the paint call)
and the CDP poller adds more. **Pre-registered**: if R-C is *not* caught, that is
recorded plainly as a limit of the busy control — it discriminates "attached to
nothing" from "attached to something", and does **not** by itself discriminate
main-thread from worker-thread; in that case the only thing separating them is
the C1–C5 identification of §2, and `RESULT.md` says so in those words. Do not
tighten a threshold to make R-C fail after seeing it pass; that is moving a
criterion after the fact.

**R-D — no tree at all.** Run `sample_threads.py` for 5 s against a probe pid
with no Chrome child (e.g. a `sleep 5` subprocess). **Required record**:
`{"status":"no-tree"}` and a non-zero exit — a sampler that searched nothing must
be red, not a clean file of zeros. This is the same rule as
`probe_ods_on_profile.py`'s own `--corpus selected nothing` guard and the census
scripts of 2026-08-29: a sweep that found zero files must fail, not report zero.

---

## Execution record

Executed 2026-09-07, 17:08-19:29 CST, by the sonnet executor seat, at
`findings/evidence/089/cpu-or-wait-2026-09-07/` (identity check at git HEAD
`c08323d3230996745ee42b61dd383a8e01c390cb`; the tree advanced by one
unrelated commit after this task's own drafting commit `e7a71edd`, touching
none of the 14 hashed paths). Full detail, tables and raw numbers are in that
directory's `RESULT.md`; this section is the pointer and the headline, not a
duplicate.

**Outcome: Waiting.** Both measurement runs agree: no thread of the `GEN(5)`
process tree accumulates meaningful CPU across a ~160 s window inside the
hang (`H`), while the identical tids accumulate ~1 s of CPU during their own
10 s boot window (`B(5)`) in the same run — which is what excludes "the
instrument never attached" by construction. This licenses exactly one
sentence: the engine is blocked, not computing, during the `rows36` hang. It
says nothing about what it is blocked in; no cause is named anywhere in the
evidence directory or here, per this task's own charter and `AGENTS.md` §7.

**Order actually followed.** Section 1.5's identity check ran first (all 14
hashes matched, no mismatch). `R-D` (needs no browser) ran before any
measurement. Run 1 then ran, after which `R-A`, `R-B`, `R-C` were run against
run 1's own banked stream (they are specified in section 7 as re-derivations
over run 1's stream, so they could not precede it; they did precede run 2 and
every subsequent judgement of run 1's own verdict). Run 2, then the idle
control (run 3), then this write-up. Run 4 (the profiler) was correctly
skipped: it is gated on a CPU-bound-or-mixed reading from runs 1-2, and both
read Waiting.

**Budget: 3 of 8 runs** (run 1, run 2, idle control). Reserve runs 5-8 not
used. Stop rule satisfied: runs 1 and 2 both produced non-void, agreeing
verdicts; the idle control passed (`quietBarHeld: true`, `noiseBarHeld:
true`); all four section 7 red cases were recorded.

**Controls.** Controls-behave in both runs via (a)-3 (in-band `B(5)`, 0.98 s
/ 1.02 s CPU, required and held) and (a)-2 (cases 2 and 3, 2.22/1.94 s and
2.12/1.94 s CPU, well above the 0.15 s bar). Control (a)-1 (case 4, the
30,688 ms-banked "heavy and finite" open) produced no figure in either run:
case 4 opened in ~1.05-1.09 s this session, not ~30.7 s, so the 2 s-cadence
phase-stamp window this protocol builds `case4`'s open-window from collapsed
to zero length before any rate could be computed — `controls.
case4HeavyFinite: null` in both verdict files. This is recorded, not
interpreted, and is a different situation from the pre-registered
"a slow case 4 shows no CPU" concern in section 3.4a, which did not occur.
The known-idle control (idle control, run 3) held over its full 180 s window.

**Red cases.** `R-A` and `R-D` matched their required records exactly.
`R-B` and `R-C`, run exactly as specified
(`--force-thread comm=CrBrowserMain` / `comm=CrRendererMain`), were found
**unsatisfiable as written on this machine**: an exhaustive scan of run 1's
entire sample stream shows every process's main thread -- browser, every
renderer, the zygote, every utility process -- carries the comm `chrome`,
never `CrBrowserMain` or `CrRendererMain`, on Google Chrome 151.0.7922.169
here. Per this task's role (an unsatisfiable-as-written criterion is
reported, not repaired), no substitute thread-selection rule was invented;
`analyse.py --force-thread` reported the honest "no such thread" void instead
of the pre-registered wording. Consequence stated plainly: the busy control's
ability to *reject* a genuinely near-idle, mis-pointed thread was not
demonstrated this session (its ability to *accept* genuinely busy threads
was, live, by every controls-behave check above). Full detail in
`redcase-R-B.json` / `redcase-R-C.json`.

**Instrument fixes made mid-session, before the affected verdict was
finalised** (exact sha256 values in `identity.json`'s `notes`): (1)
`analyse.py`'s CPU-bound test originally checked only the `SUSTAINED`
fraction, not section 4.1's separate `BUSY_BAR`-mean-over-`H` clause -- fixed
before any real data was analysed with the looser version; (2) a data-shape
mismatch (`run_one.py` nested CDP phase stamps under `meta["cdp"]
["phaseStamps"]`, `analyse.py` read only the top-level key) that would have
voided every run for a wiring reason -- fixed on both sides, and run 1's
verdict was regenerated over its own already-banked stream, no browser
re-run; (3) `wchan`/`syscall` were sampled but discarded during reshaping --
both runs' verdicts regenerated over their banked streams once found
missing, again with no browser re-run; (4) `idle_control.py`'s scratch root
needed a fifth, read-only symlink (`sdk -> wasm_sdk_probe/dist/sdk`) beyond
the protocol's literally-named four, because `ods-decisive-probe-app.js`
imports `./sdk/document-sdk.js` relative to itself and the real measurement
runs get that path for free from `build_mirror()`'s fallback symlinking.
None of these changed a threshold, a window definition, or an outcome
category.

**What remains unmeasured**, named rather than left implicit: what the
blocked threads are blocked in (needs a debug build or debugger attach, a
separate task with its own attribution discipline); the busy control's
untested negative-discriminating power (the R-B/R-C gap); whether case 4's
now-fast opens are stable, notable, or an artefact of this environment (no
cause offered, out of scope for this protocol's one question); and that two
agreeing runs are agreement on one machine on one day, not a claim about
every environment or every day.

Deliverables: `findings/evidence/089/cpu-or-wait-2026-09-07/` (identity.json,
build-verify.txt, the four scripts, run-1/run-2 probe/samples/meta/verdict,
idle-1 samples/meta/verdict, four redcase-*.json, RESULT.md) and this
section. `git status --porcelain` showed only this task's own new directory
throughout; no file outside it was created, edited, moved, or deleted.
