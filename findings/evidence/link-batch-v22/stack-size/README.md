# v22 stack size: what the engine thread needs (finding 153, criterion 2) — measured without a relink (2026-10-19)

Diagnostic, not evidence for a counted criterion. The tool is `../../link-batch-v21/shakedown/diag-long-paragraph/tool/diag_long_paragraph.py`, with a page family added today: `v21stack<N>`. It is v21's page and engine with ONE change in the mirror's `profiles/e2-editor-v21/probe.js`: the default pthread stack passed to `_emscripten_thread_init` is N bytes instead of 65,536. `probe.wasm`, the worker, the manifest and the page are the shipped ones. `v21big` = `v21stack1048576`, the counterfactual of finding 153. Chrome 151 headless, one fresh browser per cell.

## 1. Bisect on finding 153's four failing inputs (`report-bisect1.json`)

| stack | Markdown 65,536 CJK | Markdown 43,520 CJK | Markdown 65,536 ASCII | open the 14-page paragraph, type at its start |
|---|---|---|---|---|
| **65,536 (shipped)** | crash | hang | crash | ok-then-crash |
| 131,072 | ok | ok | ok | ok |
| 262,144 | ok | ok | ok | ok |
| 524,288 | ok | ok | ok | ok |
| 1,048,576 | ok | ok | ok | ok |

The 65,536 row is the positive control: it reproduces finding 153 on every input.

## 2. Headroom: longer single paragraphs (`report-headroom1.json`, `report-opentype1.json`)

`sdk-text` = one SDK `insertText` of N bytes of CJK into the empty document (no size limit on this route). `opentype` = open a saved document holding one such paragraph, then one raw `insertText "x"` at the caret the open leaves (the paragraph's start); this is finding 153's deepest case, because the edit reformats the follow frames.

| stack | insertText 131,072 (~28 pp) | 262,144 (~56 pp) | 524,288 (~112 pp) | open 28 pp + type | open 56 pp + type | open 112 pp + type |
|---|---|---|---|---|---|---|
| 65,536 | — | — | — | **hang** (90 s) | — | — |
| 131,072 | ok (118 ms) | ok | ok (826 ms) | ok | ok | ok |
| 262,144 | ok | ok | ok | ok | ok | ok |
| 524,288 | ok | ok | ok | ok | ok | ok |
| 1,048,576 | ok | ok | ok (1,234 ms) | ok | ok | ok (0.81 s) |

The page counts are approximate, scaled from finding 153's 14 pages per 65,536 CJK bytes. The documents are in `docs-headroom1/`.

## 3. What this says, and does not

- Every input measured needs **more than 64 KiB and at most 128 KiB** of thread stack [observed]. Up to 112 pages, the need did not grow with the paragraph's length: 128 KiB took the 112-page type-at-start as it took the 14-page one. So the nesting per edit is bounded well below one level per page on these inputs [inferred]. Finding 153's sentence "one nesting level per follow frame the pass formats" holds only up to about ten levels.
- **Not measured:** other recursion paths in the core. Examples are deeply nested tables, lists and sections; import of deeply nested XML; and other threads' work. LibreOffice is written for native thread stacks (8 MiB by default on Linux) [source: the platform default, not this tree]. A value just above 128 KiB covers what was measured and nothing else.
- **Memory:** the link fixes the heap at 1 GB (`-sTOTAL_MEMORY=1GB`, no growth) with a pool of 7 pthreads (`-sPTHREAD_POOL_SIZE=7`, not strict) [source: `wasm_sdk_probe/Makefile` `link_r5_product`]. Each thread's stack comes out of that heap when the thread is created. 7 × 64 KiB = 448 KiB today. At 128 KiB, 256 KiB, 512 KiB and 1 MiB it is 0.9, 1.75, 3.5 and 7 MiB (0.1–0.7 % of the heap) for 7 threads [arithmetic]. The number of pthreads alive at once was not counted.
- `STACK_OVERFLOW_CHECK` stays 0 at `-sASSERTIONS=0` [source: finding 153]. Nothing here measures its cost.
