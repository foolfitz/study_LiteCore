# W1: v12's boot `sbrk`, the number the ODS memory question depends on

Measured 2026-09-03. `handoff/PLAN-2026-09-03-ods-reading.md` §4 said the
headroom calculation depends on a number **nobody had ever recorded** — the
candidate's boot `sbrk` — rather than on the document size the roadmap quotes.
Here it is.

## The numbers, three cycles, byte-identical

| stage | `sbrk` | |
|---|---|---|
| `open.begin` (the engine, booted, no document) | **290,066,432** | 276.6 MiB |
| `open.documentLoad-returned` (one ODT loaded) | 293,605,376 | 280.0 MiB |
| the document's own cost | **3,538,944** | **3.4 MiB** |
| ceiling (`-sTOTAL_MEMORY=1GB`, no growth) | 1,073,741,824 | 1024 MiB |
| **headroom after boot** | **783,675,392** | **747.4 MiB** |

All three cycles report the same values to the byte, and `open.begin` returns to
290,066,432 on every cycle — so at that stage the **noise floor is zero** and
there is no cross-cycle growth to subtract. (The plan's leak bound wants five
opens; three is what this run took, and the bound is still owed.)

## Against the incumbent's core

The comparison the roadmap's framing invites is the wrong one, so both halves
are stated:

| | boot `sbrk` | binary on disk |
|---|---|---|
| `e2-editor-v2`, writer-only (2026-08, Firefox) | 287,248,384 | 115 MB |
| `e2-editor-v12`, writer+calc+a11y | **290,066,432** | 135 MB |
| difference | **+2,818,048 (+2.7 MiB)** | +20 MB |

**The bigger binary does not cost bigger heap.** 20 MB more `.wasm` buys 2.7 MiB
more `sbrk` at boot. That refutes the plausible fear — that the accessibility
plus Calc core would eat the headroom before a spreadsheet was even opened —
which nothing had measured either way.

**What this does NOT say.** It is one ODT on one machine in Chrome; the v2 row
is Firefox and a different core, so the +2.7 MiB is a comparison across two
browsers as well as two cores. It is quoted as the order of magnitude it is, not
as a controlled delta. No spreadsheet has been opened yet — that is W2.

## The instrument said the product had failed, and it had not

The first run of this measurement reported:

```
"complete": false,
"error": {"code": "RUNNER_TIMEOUT", "message": "page never completed"}
"cycles": 0, "samples": 0
```

after waiting out its full **40-minute** timeout. The page's own log, written
beside it, says:

```
{"complete":true,"cycles":3,"stages":18,"workers":{"created":4,"terminated":4}}
```

**with the last cycle ending at 8,830 ms.** The page finished in under nine
seconds and the runner waited forty minutes to announce that the product never
completed.

The cause: `tools/run_e2_c_d4.py` polls `globalThis.<namespace>` with
`--namespace` defaulting to `__e2c_d4`, and `e2-c-d4-heap-app.js` publishes to
`globalThis.__e2c_d4_heap`. The heap page is a different page with a different
handle, and the default belongs to its sibling. Re-run with
`--namespace __e2c_d4_heap`: `complete: true`, 3 cycles, 8 samples, twenty-two
seconds.

Both runs are kept. The failed one is the evidence, because this is the worst
class of instrument error this tree files: **it did not merely fail to measure,
it reported a product failure that had not happened**, and it did so with a
timeout long enough to look like a real investigation. A reader who had taken
`RUNNER_TIMEOUT` at face value would have opened a memory investigation into a
core that boots in two seconds.

Registered as a queue item; the fix is not merely to pass the flag but to make
the runner say *which* namespace it polled and what else it found, so the next
mismatch names itself.
