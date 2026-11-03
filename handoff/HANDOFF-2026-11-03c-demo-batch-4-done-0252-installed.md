# Handoff: demo batch 4 done, host 0.2.52 installed, the owner's hand test is next

Checkpoint **2026-11-03 09:40**. Supersedes `HANDOFF-2026-11-03b-demo-batch-4-link-next.md`. K's numbers in `HANDOFF-2026-11-02b-k-0245-holds.md` stand.

## State

- **Nominal shipped: 0.2.45** (K holds). It carries findings 179 to 182. **Installed on the own stack: 0.2.52**, uncounted: host `c657aba`, engine `21985315bc752e57`, Writer on `e2-editor-v32` (wasm `54e50093`), Calc on `ods-editor-v3`, shell generation 87 (`97c3da29`). `https://litecore.localhost:18443`.
- Everything in `handoff/RUNBOOK-relink-v32.md` is done. `findings/evidence/demo-batch-4/README.md`, `findings/evidence/host-0.2.52/README.md`, spec section 8.
- **Nothing of ours is running. Nothing is pushed.** The owner pushes: this repo's `main`, and the host repo's `main` and branch `host-0.2.52`.

## Next

1. **The owner's hand test on 0.2.52**: the list at the end of the runbook. Reload open tabs. Whether it becomes the daily candidate is the owner's.
2. Ordered-commands product arms (the owner put them behind the demo); Microsoft formats and Calc zoom only when asked.

## After the reboot (added 2026-11-03, the owner is rebooting and cannot hand test yet)

The owner chose this order: A the census, B fixes that need no link, C ordered-commands. A's reading half is done: `research/RESEARCH-2026-11-03-open-findings-census-0.2.52.md`. Of 21 findings whose headers look open, 16 are fixed; only five are not, and only 151 is on the ordinary typing path.

1. **Bring the stack up, it does not restart by itself** (`restart: "no"`): from `wasm_sdk_probe/host-stack`, `docker compose --env-file litecore.env up -d`, then `curl -sk -o /dev/null -w "%{http_code}\n" https://litecore.localhost:18443/status.php` must read 200.
2. KWallet is locked after a reboot. `ChromeSession` carries `--password-store=basic`; the four preflights that do not go through it need it unlocked.
3. **Measure finding 151's arrow half on 0.2.52**: `tools/diag_v21_dirty_move.py` V8d, whose page is pinned to `v21`/`dist0224` (`:663`), so it needs a page family for 0.2.52. N=3, both browsers. Green closes it. Red: read which layer before fixing.
4. **The refusal sentences**: `web/e2-editor-app.js:2394` prints `describeError` for non-review refusals, so Enter over a selection reads like old finding 174. Page only: a new generation, no link.
5. C, the ordered-commands product arms.
6. **Calc undo, the owner asked for it on 2026-11-03.** The Calc page has no document undo: no control, Ctrl+Z sends nothing, the Worker refuses `undo` on `ods-editor-v3`, and the Calc engine's `oxsdk_capabilities` lacks `OXSDK_CAPABILITY_UNDO` (`findings/evidence/calc-undo/README.md`). It needs a link, so it goes into the next link batch, not into B: the capability bit in the Calc build, a new Calc profile whose manifest and worker carry `undo`/`redo`, then the page's 復原/取消復原 buttons and Ctrl+Z/Ctrl+Y. Core undoes a Calc write in one step natively (`demo-batch-3/native-calc-style/run-01`), so measure natively first which Calc actions take more than one step (a range format, an entry that recalculates). Pin the criteria in a spec before the code.

Progress since the reboot: the own stack's stale log FIFO fixed (`specs/SPEC-M3-own-stack.md`, last section); finding 151 closed on 0.2.52; B is on the tree (`specs/SPEC-P-demo-batch-5.md`, Enter over a selection and the empty-copy sentence), P5 run-02 is the next read.

Keep 169 out of a demo script. Do not rewrite the stale finding headers: the census is the record.

## What the link settled

- **The bridge works on Wasm.** It had only run natively. A press at a caret is 10 to 24 ms at any document size tried; 500 paragraphs selected is 0.26 to 0.38 s, and taking bullets off all 500 is 1.4 s, the worst the page allows. `p4/read-cost-02`, spec section 8.
- **A paragraph with an as-char picture now takes a paragraph action**: 16 ms, saved correctly. Finding 037 stays open in core, but this path no longer reaches it, because the read does not call `getTextSelection`.
- **No F3 cell moved.** The runbook's declared moves did not happen; spec section 8 says why.

## New finding

**183, low.** A document holding a corrupt PNG never answers its first paint and the session goes `recoverable-error`. v31 and v32 alike, so not a regression. Cause not read. It came from my own hand-made fixture, whose IDAT CRC was wrong.

## Cautions

- `page.wait()` in the tools returns on timeout without raising. A failed `save()` surfaces later as `b is undefined`, and on Chrome as a `dict` where a string was expected. Read that as "no Blob was made", not as a reader bug.
- A red case that ends in `*/fatal` proves nothing about the reader. `swap-levels` went red that way first: the client's own `_validateResult` stopped the run. Read which cell is red, not just the verdict.
- The page's `beforeunload` holds a navigation on an unsaved document, and CDP's `Page.navigate` then waits out its 180 s. Save before moving to the next document.
- `read_cost.py` and `diag_t12.py` are diagnostics, not gates.
- Use absolute paths; a shell `cd` carries between calls.

## Limits

As in the previous handoff, unchanged: `L-number-on-heading`, `L-table-in-selection`, `L-list-style-levels`, `L-none-list-level`, `L-numbered-heading-state`, the read's limit of 500 paragraphs. New: finding 183.

## Section 34.4

Work since the previous handoff.

- **Fixed-by-execution: 5.** T4's `bullet-middle` expectation. T4's wrapped place. T12's fixture. `swap-levels` red on the client's check. `read_cost.py` on `beforeunload`. Witness: `p4/run-01`, committed before the tool changed.
- **Fixed-by-review: 0.** No Codex or Opus round: no product byte changed after the link.
- **Fable rulings: 0.** Nothing needed one.
- Wrong statements, corrected: 1. The runbook's declared F3 moves.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Compiling `make` and the link stay the owner's unless they say otherwise for that build. Commit messages: `Co-Authored-By` yes, `Claude-Session` never. Codex through `codex exec` only.
