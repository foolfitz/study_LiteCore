# Firefox: navigated-away pages' pthread-pool workers are reclaimed lazily; repeated navigation wedges WebAssembly init silently

Self-contained reproduction. A page spawns a dedicated worker that instantiates
a small Emscripten pthread module (40 KB wasm, 1 GiB shared
`WebAssembly.Memory`, `-sPTHREAD_POOL_SIZE=7`), never terminates it, and
re-navigates to itself. The navigation is expected to tear the workers down;
Firefox releases their worker slots and memory only lazily, so a
deterministic per-navigation leak accumulates until one of two budgets is
exhausted:

| mode | budget exhausted | observed wall (Firefox 153.0.1, Linux) |
|---|---|---|
| default | worker slots (`dom.workers.maxPerDomain`, default 512): excess `new Worker()` calls queue **silently**, the pthread pool never comes up, module init never completes, no error anywhere | 65 navigations (this page); 66 in the originating harness — same band, different page weight |
| default + `dom.workers.maxPerDomain=64` | same, budget shrunk — the wall moves with the pref, which is the attribution | 9 navigations |

With a large real-world module (115 MB) there is a second, earlier wall: the
memory budget — RSS climbs ~0.7–0.9 GB per navigation (dead workers' compiled
code + the bound 1 GiB shared memory) until `WebAssembly.instantiate` aborts
around navigation 8. This page's `?touch` knob does not reproduce that
variant (see notes below).

Chrome 150 runs the same page clean (tested to 120 navigations): it reclaims
the previous page's workers and memory promptly.

**Fixed in Nightly 155.0a1** (BuildID 20260806211740, tested 2026-08-07):
default ran 1343 navigations, `dom.workers.maxPerDomain=64` ran 624, both
clean, with the full pool spawning every navigation. The same driverless
harness reproduces 65 / 9 on release 153, so the comparison is like-for-like.

Notes for running this:
- Snap-packaged Firefox (Ubuntu default) cannot read a profile under `/tmp` —
  it silently never loads the page. Keep profiles under `$HOME`.
- geckodriver 0.37 rejects the current Nightly layout with "binary is not a
  Firefox executable"; drive Nightly without WebDriver (launch
  `firefox -headless -profile <dir> <url>` and read the wall from serve.py's
  log: the last `?n=K` it served).
- The `?touch` knob does NOT reproduce the memory-budget variant: Firefox
  reclaims both committed shared-memory pages and GC-pressured JS heaps of
  dead workers. The ~8-navigation `WebAssembly.instantiate` abort needs a
  large real-world module (observed with a 115 MB module: compiled code plus
  the bound 1 GiB shared memory per leaked worker).

The silent-queue behaviour itself is known
([bug 1052398](https://bugzilla.mozilla.org/show_bug.cgi?id=1052398)); the
problem here is that slots stay occupied by workers belonging to pages that
no longer exist. Related: [bug 1576829](https://bugzilla.mozilla.org/show_bug.cgi?id=1576829)
(memory leak on page refresh),
[bug 1592227](https://bugzilla.mozilla.org/show_bug.cgi?id=1592227)
(worker busy-count tracking).

## Run it

Manual:

```bash
python3 serve.py            # COOP/COEP server on 127.0.0.1:8912
# open http://127.0.0.1:8912/index.html in Firefox and watch the counter;
# the page renavigates itself and reports WEDGED when init stops completing.
```

Automated (needs `geckodriver` and `firefox` in PATH; stdlib only):

```bash
python3 check.py                                      # worker-slot wall (65)
python3 check.py --pref dom.workers.maxPerDomain=64   # wall moves to 9
```

`check.py` prints one line per navigation and a final JSON with the wall.

## Files

- `index.html` — self-renavigating page; leaves the worker for navigation teardown
- `worker.js` — classic worker; `importScripts` the module glue, waits for the pool
- `minimal.js` / `minimal.wasm` — Emscripten 4.0.10 MODULARIZE build:
  `-pthread -sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0
  -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --no-entry -Oz`; source is a single
  `extern "C"` function that runs one `std::thread` and returns 42
- `serve.py` — static server with COOP/COEP (SharedArrayBuffer prerequisite)
- `check.py` — WebDriver automation, stdlib only
