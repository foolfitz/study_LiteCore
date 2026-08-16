# D4 follow-up — the WASM heap was reachable all along, and it was the wrong number

Criteria in `PREDICTION.md` (P-H1..P-H5 registered before the harness existed;
P-H6..P-H8 in addendum A1, after a scratch smoke run and before any recorded
round).  Judged offline by `tools/analyze_e2_c_d4_heap.py`; self-test 11/11 in
both directions.

**Twelve recorded rounds, all on the frozen `e2-editor-v2` artifact
(`572035ac…`), no file edited to obtain them.**

## The answer to the queue item

| question | answer |
|---|---|
| Can the product report a WASM heap figure at all? | **Yes — on the shipped artifact, today.** `reachability: REACHABLE-ON-SHIPPED-ARTIFACT` |
| Does the figure the queue item names mean anything? | **No.** `emscripten_get_heap_size()` is a constant `1073741824` in all 384 recorded stage events |
| What does move? | **`sbrk`**, the allocator's break — printed by the engine on the same line, already forwarded by the shipped worker |

The relink queue item read: *"the engine must report its WASM heap in the typed
state, because nothing in the product can report this number."*  Both halves are
wrong, and the second is the expensive one: **a field carrying
`emscripten_get_heap_size()` would have reported a constant**, so the frozen
`d4-memory` criterion (slope ≤ 2 MB/session, absolute growth ≤ 20 MB) would have
passed on it for every build forever, including a leaking one.  Paying a relink
for that field would have bought a number that cannot move.

Why it is constant is a build fact, not a measurement: every profile here links
`-sTOTAL_MEMORY=1GB` with no `ALLOW_MEMORY_GROWTH`
(`Makefile:417,780,831,849,1314`), so the linear memory never changes size.

## How the number is reached — nothing was modified

- `emitStage()` has **no compile guard** and prints both figures
  (`src/probe_engine.cpp:1665-1674`); a document open passes through 7 stages.
- The **shipped** worker forwards stage lines as `diagnostic` events when
  `debug` is on (`dist/profiles/e2-editor-v2/sdk-worker.js:776-778`).
- `createDocumentEngine({debug: true})` already sets it, and `engine.onEvent`
  already delivers it (`sdk/document-sdk.js:96,111,226`).

So the harness passes one option and subscribes to one event.  **No hash-bound
file was touched**; the artifact hashes are recorded in every round and match.

## Prediction results

| id | claim | result |
|---|---|---|
| P-H1 | debug:true yields stage events with a numeric `heapBytes` | **held** — 48 events per round, both browsers |
| P-H2 | every fresh-arm cycle yields one | **held** — 8/8 cycles, and the sampler's `wasmHeapBytes`, null since R7-D, is non-null |
| P-H3 | heap non-decreasing within an open | **held, and vacuous** — a constant is non-decreasing; recorded as vacuous rather than counted as a win |
| P-H4 | fresh-arm heap varies < 2 MB across cycles | **held** — zero variation |
| P-H5 | debug on/off do not change the PSS slope by > 2 MB/session | **FAILED as written** — see below |
| P-H6 | `heapBytes` is exactly 1073741824 everywhere | **held** — one distinct value in 384 events |
| P-H7 | `sbrk` is non-decreasing within an instance and grows in the shared arm | **held** — 290.8 MB → 338.7 MB over eight documents on one engine |
| P-H8 | fresh-arm per-cycle `sbrk` agrees within 2 MB | **held** — byte-identical across all eight cycles |
| control | a debug:false run yields **zero** stage events | **held** — so the gate is `debug`, not something else |

## P-H5 failed, and the repeats say what that means

One pair differed by 4.67 MB/session in Firefox (1.82 MB in Chrome), over the
registered 2 MB.  Three runs per condition were then recorded:

| | |
|---|---|
| spread **within** debug:true | 21.5 MB/session |
| spread **within** debug:false | 19.8 MB/session |
| mean difference **between** them | 2.7 MB/session |

`separation: NOT_SEPARATED`.  **The registered threshold was below the noise
floor of the quantity it compares.**  So P-H5 is recorded FAILED — scored against
what was written, not against what the repeats made obvious — and what it
licenses is narrow: *the control could not be run as written*, which is not the
same as *debug changed the memory*.

The heap and `sbrk` results do not depend on it: those are read from the engine,
not from PSS.

**This is worth carrying into the second round**: an 8 MB/session PSS threshold
is being applied to single runs of a quantity whose run-to-run spread here is
~20 MB/session.  D4's own page is not this page (10 cycles, forced GC, a 3 s
settle), so this is not a claim about D4's threshold — it is a reason to
**measure that page's noise floor before judging anything against it**.

## What the round found that nobody predicted

Recorded as an observation, not scored as a prediction, because it was not
registered:

**On one engine, a search after a reopen never returns.**  Cycle 1 (open,
search, click, insertText, save, close) succeeds; cycle 2's search times out at
30 s and every later search returns `BUSY` — the worker's own in-flight guard.
The opens keep working throughout: all six stage events arrive for every cycle.
**Reproduced identically in Chrome and Firefox.**

The controlled variable is in the evidence: `shared-nosearch`, the same loop
without the search, completes **8/8 cycles in both browsers**.  So this belongs
to search-after-reopen, not to reopening.

**The product does not take this path today** — `EditorSession` builds a fresh
engine per session and disposes it on close — which is why this is filed as an
SDK-level observation and a queue candidate, not a product defect.  It is also
why the shared arm's wedged rounds are **excluded** from P-H7 and the exclusion
is printed in the verdict rather than left implicit.

## Layout

```
fresh-debug1/          8 cycles, product session shape, debug on   (chrome, firefox)
fresh-debug0/          the control: same, debug off                 (chrome, firefox)
shared-debug1/         one engine, with search -- WEDGED at cycle 2 (chrome, firefox)
shared-nosearch-debug1/ one engine, no search -- 8/8               (chrome, firefox)
repeats/               two more Firefox pairs, for the noise floor
verdict.json           the offline judgement
```

Re-judge:

```
python3 tools/analyze_e2_c_d4_heap.py $(find <this dir> -name result.json -printf '%h\n')
python3 tools/analyze_e2_c_d4_heap.py --self-test <the same list>
```
