# D4 follow-up — is the WASM heap really unreachable?  Registered before the harness existed

Written 2026-08-16, after D4 reported `d4-memory` as PARTIAL with the WASM half
`notValidated`.

D4's own `PREDICTION.md` says, under "The WASM heap: registered expectation is
that it CANNOT be measured":

> Checked before writing the harness: **nothing in the product reports a WASM
> heap size.**  `sdk/sdk-worker.js` never sends one […]

**That check now looks wrong**, and it is the sole justification for a relink
queue item ("the engine must report its WASM heap in the typed state").  A queue
item costs a link; a link mints a new identity and voids every verdict filed
against the old one.  So the premise gets measured before it gets paid for.

## What was read (source, not measurement)

| what | where |
|---|---|
| `emitStage()` has **no compile guard** and prints `emscripten_get_heap_size()` | `src/probe_engine.cpp:1665-1674` |
| one document open passes through **7 stages** (`open.begin` … `open.query-metadata`) | `:2217-2281` |
| the **shipped** `e2-editor-v2` binary contains `heapBytes` and `"type":"stage"` | byte grep of `dist/profiles/e2-editor-v2/probe.wasm` |
| the **shipped** worker forwards stage events as `diagnostic`, gated on `debugEnabled` | `dist/profiles/e2-editor-v2/sdk-worker.js:776-778` |
| `debugEnabled` comes from the init payload, and `createDocumentEngine({debug:true})` already sets it | `sdk/sdk-worker.js` init, `sdk/document-sdk.js:96,111` |
| worker `kind:"event"` messages reach any page listener registered with `engine.onEvent` | `sdk/document-sdk.js:226-227,263-265` |

If this reading is right, the number is reachable **on the frozen artifact, with
no edit to any hash-bound file** — the harness only passes an option the SDK
already accepts and subscribes to an event the SDK already delivers.

Reading is not measuring.  That is what this round is for.

## What `emscripten_get_heap_size()` actually returns

**Allocated linear memory, not memory in use.**  It can only grow within one
instance; freeing an allocation never lowers it.  Registered here rather than
explained afterwards, because it decides how the number may be read:

- a rising series is **not** by itself a leak — it is the high-water mark of
  demand;
- a **flat** series across cycles is not proof of no leak either, if each cycle
  gets a fresh instance;
- the only reading that carries weight is growth **within one engine instance**
  across repeated documents.

## Two arms, because one of them cannot answer the question

| arm | shape | what it can show |
|---|---|---|
| `fresh` | D4's own shape: a new `NarrowEditorV2Session` (hence a new Worker, hence a new WASM instance) per cycle | whether the product path yields a number **in the shape D4 measures** |
| `shared` | one engine, N documents opened / edited / saved / closed through it — R7-D's `s2-reuse` shape, driven at the SDK level because `EditorSession.close()` disposes its engine by contract | whether the number can **move at all** |

The `shared` arm is declared as SDK-level: it is not the product session, and it
is not offered as evidence about the product session.

## Predictions

- **P-H1** — with `debug:true`, one document open produces **at least one**
  diagnostic stage event carrying a numeric `heapBytes`, in both browsers.
- **P-H2** — every cycle of the `fresh` arm yields at least one heap value, so
  the series R7-D's sampler has always read as `null` becomes non-null for
  8/8 cycles in both browsers.
- **P-H3** — within a single open, the heap values across the 7 stages are
  **non-decreasing** (allocated memory cannot shrink).
- **P-H4** — across the `fresh` arm's cycles, the per-cycle maximum heap varies
  by **less than 2 MB**, because each cycle is a fresh instance.  **Registered
  consequence:** if P-H4 holds, then the frozen `d4-memory` WASM criterion
  ("slope ≤ 2 MB/session, absolute growth ≤ 20 MB") applied to D4's ten-cycle
  design is close to vacuous — it would be measuring instance-to-instance
  variation of a fresh instance, not a leak.  The honest fix is then a
  long-lived arm in the matrix, not only an engine-side field.
- **P-H5** — `debug:true` does not change what the memory round measures:
  the browser PSS slope of a `debug:true` run and a `debug:false` run of the
  same arm differ by **≤ 2 MB/session**.  Without this control, the round would
  be judging leakage on a build put into a mode by the act of observing it.

## The decision rule, written before the data

- **P-H1 and P-H2 hold** → the relink queue item loses its stated
  justification.  It is then rewritten to whatever is actually left (for
  example "reachable without `debug`", if that matters) **or deleted**, and
  both `PLAN-E2-C-relink-v3.md` and D4's evidence record *why the original
  claim was wrong*.  `d4-memory` is re-judged **on the existing frozen
  artifact**.
- **P-H1 fails** → the queue item stands, and it now stands on a measurement
  that names the layer where the number stops (engine did not emit / worker did
  not forward / page did not receive), instead of on a source reading.
- **P-H3 or P-H4 fails** → recorded as-is; P-H4 failing would be the more
  interesting outcome, because a fresh instance whose heap drifts across cycles
  means something survives a worker teardown.
- **P-H5 fails** → the heap numbers are still valid, but the PSS half of any
  `debug:true` round is not comparable with D4's, and this is written down
  rather than averaged away.

Under no outcome does this round change `d4-memory`'s **first-round** verdict:
that round ran, its evidence stands, and PARTIAL is what it recorded.  What can
change is the second round's queue.

## Addendum A1 (2026-08-16, after the harness smoke run, before any recorded round)

A two-cycle Firefox smoke run — harness validation, written to a scratch
directory, **not** evidence — arrived before the rounds below were taken.  It
moved what the interesting number is, so the change is registered here rather
than explained afterwards.

**What the smoke run showed:** the heap figures arrive (six stage events per
open, both cycles), and **`heapBytes` is exactly `1073741824` in every one of
them.**  On the same line, `sbrk` moves: `287248384` → `290983936` across an
open.

**Why, from the build rather than from the data:** every profile in this tree
links with `-sTOTAL_MEMORY=1GB` and no `ALLOW_MEMORY_GROWTH`
(`Makefile:417,780,831,849,1314`).  So `emscripten_get_heap_size()` **is a
constant by construction** — it reports the size of the linear memory, which
this build fixes at 1 GiB.  It is not a measurement of anything the engine does.

**The consequence for the queue item is sharper than "unnecessary".**  The item
reads "the engine must report its WASM heap in the typed state".  A field
carrying `emscripten_get_heap_size()` would have reported a constant, and the
`d4-memory` criterion ("slope ≤ 2 MB/session, absolute growth ≤ 20 MB") applied
to it would have passed **for every build, forever, including a leaking one**.
The moving number is `sbrk`, and the engine already prints it on the same line.

Registered now, before the recorded rounds:

- **P-H6** — `heapBytes` is `1073741824` in **every** stage event of every
  recorded round, both browsers, both arms.
- **P-H7** — `sbrk` is **non-decreasing within one engine instance**, and in
  the `shared` arm its value after the last cycle is **greater** than after the
  first (one engine, eight documents: the allocator's break has to have moved).
- **P-H8** — in the `fresh` arm, the per-cycle final `sbrk` values agree within
  **2 MB** of each other, because each cycle is a fresh instance.

P-H3 as originally written ("heap values are non-decreasing within one open") is
**true but empty** if P-H6 holds — a constant is non-decreasing.  It is scored
as held-but-vacuous rather than quietly rewritten.

## What voids the round

- The page fails to reach 8 cycles for a reason unrelated to memory: fewer
  cycles are reported, not padded.
- The `shared` arm's engine is restarted by a crash mid-run: the samples after
  the restart belong to a different instance and are dropped, not joined.
- The shipped artifact hashes do not match the frozen four: the round is void,
  because it would be describing a different product.
