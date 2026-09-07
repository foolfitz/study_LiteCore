# WAIT-SHAPE — per-thread and per-process shape of the `H` window, both runs

Step 1 of the 2026-09-07 phase-2 task
(`handoff/tasks/TASK-2026-09-07-089-cpu-or-wait.md`, `## Execution record`).
Pure re-derivation over the already-banked `run-1-samples.jsonl.gz` and
`run-2-samples.jsonl.gz` — no browser was run to produce this file. The
derivation script is `waitshape_analyse.py` in this directory; its full
per-tid output for both runs is `waitshape-run-1.json` and
`waitshape-run-2.json`. This file quotes selected rows from those two JSON
files; the JSON files are the primary record.

This file makes **no claim about cause**. Every number below is a rate, a
state-character count, a context-switch delta, or a raw `wchan`/`syscall`
string, over an interval, for a thread identified by pid+tid. Nothing here
says what any thread is waiting *for*.

---

## 1. GEN(5) per tid: parked in `H`, contrasted with working in `B(5)`

`B(5)` = `[gen5FirstAppearance, +10s]` (the boot of the generation that opens
`rows36`). `H` = the ~160.5 s hang window, starting 20 s after `B(5)` ends.
Same tids, same process, same run, ~90–170 s apart.

### Run 1 — GEN(5), B(5) vs H, per tid

| pid | tid | comm | B(5) n | B(5) rate (cores) | B(5) states | H n | H rate (cores) | H states | H wchan | H syscall# distinct | H vol / nonvol Δ |
| ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- | --- | ---: | --- |
| 1622151 | 1622441 | DedicatedWorker | 15 | 0.09286 | R:1,S:14 | 322 | 0.000062 | S:322 | futex_do_wait | 2 | 42 / 2 |
| 1622151 | 1622460 | DedicatedWorker | 14 | 0.01692 | S:14 | 322 | 0.000623 | S:322 | futex_do_wait | 1 | 1601 / 15 |
| 1622151 | 1622461 | DedicatedWorker | 14 | 0.00000 | S:14 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 0 / 0 |
| 1622151 | 1622462 | DedicatedWorker | 14 | 0.00923 | S:14 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 0 / 0 |
| 1622151 | 1622912 | MemoryInfra | 0 | n/a | no samples | 243 | 0.000000 | S:243 | futex_do_wait | 1 | 0 / 0 |
| 1622355 | 1622355 | chrome | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 10 / 1 |
| 1622355 | 1622357 | PerfettoTrace | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | ep_poll | 1 | 0 / 0 |
| 1622355 | 1622358 | ThreadPoolServi | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | ep_poll | 1 | 0 / 0 |
| 1622355 | 1622359 | ThreadPoolForeg | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | futex_do_wait | 2 | 1 / 0 |
| 1622355 | 1622360 | Chrome_ChildIOT | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | ep_poll | 1 | 4 / 0 |
| 1622355 | 1622361 | ThreadPoolForeg | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | futex_do_wait | 2 | 1 / 0 |
| 1622355 | 1622367 | Compositor | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | ep_poll | 1 | 0 / 0 |
| 1622355 | 1622368 | ThreadPoolSingl | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | futex_do_wait | 2 | 1 / 0 |
| 1622355 | 1622369 | HangWatcher | 21 | 0.00000 | S:21 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 16 / 0 |

### Run 2 — GEN(5), B(5) vs H, per tid

| pid | tid | comm | B(5) n | B(5) rate (cores) | B(5) states | H n | H rate (cores) | H states | H wchan | H syscall# distinct | H vol / nonvol Δ |
| ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- | --- | ---: | --- |
| 1629527 | 1629815 | DedicatedWorker | 13 | 0.04833 | R:1,S:12 | 322 | 0.000125 | S:322 | futex_do_wait | 2 | 18 / 2 |
| 1629527 | 1629830 | DedicatedWorker | 13 | 0.02000 | S:13 | 322 | 0.000685 | S:322 | futex_do_wait | 1 | 1600 / 14 |
| 1629527 | 1629831 | DedicatedWorker | 13 | 0.00000 | S:13 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 0 / 0 |
| 1629527 | 1629832 | DedicatedWorker | 13 | 0.01833 | S:13 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 0 / 0 |
| 1629527 | 1630278 | MemoryInfra | 0 | n/a | no samples | 243 | 0.000000 | S:243 | futex_do_wait | 1 | 0 / 0 |
| 1629730 | 1629730 | chrome | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 10 / 0 |
| 1629730 | 1629732 | PerfettoTrace | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | ep_poll | 1 | 0 / 0 |
| 1629730 | 1629733 | ThreadPoolServi | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | ep_poll | 1 | 0 / 0 |
| 1629730 | 1629734 | ThreadPoolForeg | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | futex_do_wait | 2 | 1 / 0 |
| 1629730 | 1629735 | Chrome_ChildIOT | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | ep_poll | 1 | 4 / 0 |
| 1629730 | 1629736 | ThreadPoolForeg | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | futex_do_wait | 2 | 1 / 0 |
| 1629730 | 1629747 | Compositor | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | ep_poll | 1 | 0 / 0 |
| 1629730 | 1629748 | ThreadPoolSingl | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | futex_do_wait | 2 | 1 / 0 |
| 1629730 | 1629749 | HangWatcher | 20 | 0.00000 | S:20 | 322 | 0.000000 | S:322 | futex_do_wait | 1 | 16 / 0 |

`B(5)` and `H` identify the same 14 tids in both runs (by pid+tid). Every row
that has CPU in `B(5)` (the first two `DedicatedWorker` rows in each run: rate
0.017–0.093 cores, one with an `R` sample) drops to a rate of 0.00006–0.00069
cores in `H`. `pid` 1622355 / 1629730 is the second, ambiguous renderer
process named in `RESULT.md`'s identification note (born at
`gen5FirstAppearance`); its whole baseline thread set shows zero CPU in
*both* windows, in both runs — it never worked during `B(5)` either, which is
itself a fact about that candidate set and not about the answer (the Waiting
verdict does not depend on which of the two candidate processes is "the
real" one, per task §2.4).

### The raw `syscall` argument-line variants, quoted (not interpreted)

`RESULT.md` records that several `GEN(5)` tids show exactly two distinct
argument-value lines under syscall number 202 (`futex`) across `H`, rather
than one. Run 1's raw lines for the four tids where this holds:

```
pid 1622151 tid 1622441 (DedicatedWorker):
   28 x '202 0x7ddb115d9e50 0x89  0x0 0x7ddb115d9dc8 0x0 0xffffffff 0x7ddb115d9c48 0x7ddd862aca82'
  294 x '202 0x7ddb115d9e50 0x189 0x0 0x0           0x0 0xffffffff 0x7ddb115d9c58 0x7ddd862aca82'

pid 1622355 tid 1622359 (ThreadPoolForeg):
   80 x '202 0x7ddd7c7fbfc0 0x89  0x0 0x7ddd7c7fbf38 0x0 0xffffffff 0x7ddd7c7fbdb8 0x7ddd862aca82'
  242 x '202 0x7ddd7c7fbf30 0x189 0x0 0x0           0x0 0xffffffff 0x7ddd7c7fbd38 0x7ddd862aca82'

pid 1622355 tid 1622361 (ThreadPoolForeg): same shape, own addresses (80 / 242)
pid 1622355 tid 1622368 (ThreadPoolSingl): same shape, own addresses (80 / 242)
```

The other ten `GEN(5)` tids show exactly one syscall-202 or syscall-232
(`ep_poll`) line, unchanging, for their entire span of `H`. Run 2 shows the
identical shape on the identically-positioned tids (`1629815`, `1629734`,
`1629736`, `1629748`). This is recorded as a payload fact; no meaning is
assigned to the difference between the two argument lines.

---

## 2. Is the whole process-tree group parked, or only `GEN(5)`?

### Every process in the tree, over `H`

**Run 1** — 153 threads across 13 processes; 1.740 CPU-seconds accumulated
over 160.5 s (mean rate **0.01084 cores across the entire tree**):

| pid | type | thread count | total CPU-s over H | mean rate (cores) | max single-thread rate |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1622062 | browser | 33 | 1.1500 | 0.007165 | 0.004984 |
| 1622077 | zygote | 1 | 0.0000 | 0.000000 | 0.000000 |
| 1622078 | zygote | 1 | 0.0000 | 0.000000 | 0.000000 |
| 1622080 | zygote | 1 | 0.0300 | 0.000187 | 0.000187 |
| 1622101 | gpu-process | 22 | 0.0000 | 0.000000 | 0.000000 |
| 1622103 | utility | 10 | 0.1600 | 0.000997 | 0.000935 |
| 1622105 | utility | 8 | 0.0000 | 0.000000 | 0.000000 |
| 1622130 | renderer | 18 | 0.0300 | 0.000187 | 0.000125 |
| 1622151 | renderer (hosts GEN(5) `DedicatedWorker`/`MemoryInfra`) | 28 | 0.3700 | 0.002305 | 0.000623 |
| 1622186 | renderer | 11 | 0.0000 | 0.000000 | 0.000000 |
| 1622355 | renderer (the ambiguous 2nd GEN(5) candidate) | 9 | 0.0000 | 0.000000 | 0.000000 |
| 1622373 | renderer | 10 | 0.0000 | 0.000000 | 0.000000 |
| 1628906 | utility | 1 | 0.0000 | 0.000000 | 0.000000 |

**Run 2** — 159 threads across 14 processes; 1.650 CPU-seconds accumulated
over 160.5 s (mean rate **0.01028 cores across the entire tree**):

| pid | type | thread count | total CPU-s over H | mean rate (cores) | max single-thread rate |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1629438 | browser | 30 | 1.0600 | 0.006604 | 0.004299 |
| 1629453 | zygote | 1 | 0.0100 | 0.000062 | 0.000062 |
| 1629454 | zygote | 1 | 0.0000 | 0.000000 | 0.000000 |
| 1629456 | zygote | 1 | 0.0300 | 0.000187 | 0.000187 |
| 1629477 | gpu-process | 22 | 0.0000 | 0.000000 | 0.000000 |
| 1629479 | utility | 12 | 0.1400 | 0.000872 | 0.000872 |
| 1629481 | utility | 8 | 0.0000 | 0.000000 | 0.000000 |
| 1629505 | renderer | 18 | 0.0500 | 0.000312 | 0.000187 |
| 1629527 | renderer (hosts GEN(5) `DedicatedWorker`/`MemoryInfra`) | 28 | 0.3600 | 0.002243 | 0.000685 |
| 1629555 | renderer | 11 | 0.0000 | 0.000000 | 0.000000 |
| 1629724 | renderer | 10 | 0.0000 | 0.000000 | 0.000000 |
| 1629730 | renderer (the ambiguous 2nd GEN(5) candidate) | 9 | 0.0000 | 0.000000 | 0.000000 |
| 1630420 | utility | 7 | 0.0000 | 0.000000 | 0.000000 |
| 1631665 | utility | 1 | 0.0000 | 0.000000 | 0.000000 |

### State characters, whole tree

| | run 1 | run 2 |
| --- | ---: | ---: |
| tids present over `H` | 153 | 159 |
| tids with **any** `R`-state sample in `H` | 3 | 2 |
| tids with **any** `D`-state sample in `H` | 0 | 0 |
| tids with nonzero mean rate over `H` (≥ 1 clock tick accumulated) | 31 | 27 |
| aggregate sample-state counts, whole tree, whole `H` | S:42464, R:4 | S:42143, R:3 |

The tids that ever show `R` in `H`, both runs, are **outside `GEN(5)`**:
run 1 — `1622062/1622085` (`ThreadPoolForeg`, browser), `1622062/1622062`
(`chrome`, browser main), `1622103/1622110` (`Chrome_ChildIOT`, utility);
run 2 — the same two browser-process tids, no third. Every `GEN(5)` tid, in
both runs, is `S` in 100% of its `H` samples — 322/322 for the 13 tids
present for all of `H`, 243/243 for the one late-born `MemoryInfra` tid. Of
the 31 (27) tree-wide tids with a nonzero mean rate, most sit at exactly one
clock tick over the whole 160.5 s window (rate 0.000062 = 10 ms / 160.5 s),
i.e. at the sampler's own resolution floor, not a sustained rate.

### What this answers

**Not "the engine's threads are parked while the rest of the tree hums
along."** The whole tree — 13–14 processes, 153–159 threads, including every
renderer, the GPU process, every utility process and every zygote — spends
the entire ~160 s window at a combined **~1% of one core**. The two threads
that ever touch `R` do so a total of 3–4 times out of ~42,000+ thread-samples
across the whole tree, and both are the browser-process housekeeping thread
and its DevTools/IO-adjacent utility thread — the location this protocol's
own §3.6-step-4 pre-registered as the expected home for the CDP poller's
induced CPU, not a `GEN(5)` thread. So: **the group as a whole is parked,
not merely the engine's own slice of it**, with a single-digit fraction of
one thread's time going to housekeeping/instrumentation.

---

## 3. Context-switch counters over `H`

Voluntary and nonvoluntary deltas are already columns 11–12 of the two
per-tid `GEN(5)` tables in section 1. The distinguishing case: `pid.tid`
`1622151.1622460` (run 1) / `1629527.1629830` (run 2) — the **second**
`DedicatedWorker` tid — logs **1601 / 1600** voluntary context switches over
`H` (≈ 10/s, i.e. woken roughly once every 100 ms for the full 160.5 s),
while accumulating only 0.0623–0.069 s of total CPU (rate 0.00062–0.00069
cores) across that same window. Every other `GEN(5)` tid logs 0–42 voluntary
switches across the same 160.5 s (i.e. woken at most a few times an hour by
that rate, most of them never).

For reach beyond `GEN(5)`, the whole-tree ranking by voluntary switches over
`H`:

**Run 1:**

| pid | tid | type | comm | in GEN(5)? | voluntary Δ | nonvoluntary Δ |
| ---: | ---: | --- | --- | :---: | ---: | ---: |
| 1622062 | 1622089 | browser | Chrome_IOThread | no | 2040 | 5 |
| 1622151 | 1622460 | renderer | DedicatedWorker | yes | 1601 | 15 |
| 1622062 | 1622062 | browser | chrome | no | 1567 | 66 |
| 1622103 | 1622110 | utility | Chrome_ChildIOT | no | 1369 | 186 |
| 1622062 | 1622085 | browser | ThreadPoolForeg | no | 1153 | 25 |
| 1622062 | 1622122 | browser | Chrome_DevTools | no | 400 | 11 |
| 1622151 | 1622156 | renderer | Chrome_ChildIOT | no | 339 | 21 |
| 1622062 | 1622086 | browser | ThreadPoolForeg | no | 318 | 1 |

**Run 2:**

| pid | tid | type | comm | in GEN(5)? | voluntary Δ | nonvoluntary Δ |
| ---: | ---: | --- | --- | :---: | ---: | ---: |
| 1629438 | 1629466 | browser | Chrome_IOThread | no | 2025 | 5 |
| 1629527 | 1629830 | renderer | DedicatedWorker | yes | 1600 | 14 |
| 1629438 | 1629438 | browser | chrome | no | 1562 | 25 |
| 1629479 | 1629499 | utility | Chrome_ChildIOT | no | 1533 | 19 |
| 1629438 | 1629461 | browser | ThreadPoolForeg | no | 1187 | 26 |
| 1629438 | 1629490 | browser | Chrome_DevTools | no | 399 | 11 |
| 1629438 | 1629462 | browser | ThreadPoolForeg | no | 383 | 1 |
| 1629527 | 1629532 | renderer | Chrome_ChildIOT | no | 325 | 2 |

The one `GEN(5)` tid with high wake counts (`1622460`/`1629830`) is the
**second-highest waker in the entire tree** in both runs, reproducing almost
exactly (1601 vs 1600 voluntary switches). Nonvoluntary switches are small
everywhere (≤ 186, dominated by a utility-process IO thread, not any
`GEN(5)` tid) — i.e. nothing in the tree is being preempted off the CPU at a
rate that would indicate it was running and got interrupted; the switches
recorded are consistent with threads voluntarily blocking and being woken.

---

## What this is, and is not

**This is:** a table. Per-tid CPU rate, state-character counts, raw
`wchan`/`syscall` strings, and voluntary/nonvoluntary context-switch deltas,
for every thread this run's sampler saw, over two named time windows
(`B(5)`, `H`), re-derived from the exact sample stream `RESULT.md`'s verdict
was computed from. The one comparison this file adds beyond `RESULT.md`: the
same `GEN(5)` tids' own numbers *during their own boot*, side by side with
*during the hang*, and the full-tree (not top-10) picture for the same
window.

**This is not:** an account of what any thread is waiting for, an
identification of "the" worker thread among the two ambiguous candidate
processes, or a claim about periodicity, causality, or mechanism. The two
`futex` argument-line variants, the `futex_do_wait` vs `ep_poll` `wchan`
split, and the one tid with ~10 wakeups/second are reported because they are
what the numbers say; none of them is read as a lock, a message queue, a
timer, or a proxying layer. Two runs, one machine, one day — the same limit
`RESULT.md` already states.
