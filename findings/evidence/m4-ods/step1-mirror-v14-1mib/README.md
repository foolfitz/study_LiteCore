# Step 1: the viewer page on `e2-editor-v14` with a 1 MiB pthread stack (diagnostic)

Spec: `specs/SPEC-M4-ods-in-nextcloud.md` §7 (predictions pinned in `d7ab2815`, before this run).
Runner: `wasm_sdk_probe/tools/run_ods_viewer_step1.py` (judge self-test 12/12 before the run).
Report: `report-2026-10-20T113849Z.json`. Chrome 151.0.7922.169, headless, cache disabled.

**Evidence class: diagnostic.** The name is still spoofed to `.odt` (W7 does not exist) and the
reader object set on this core is not measured; only the `ods-viewer-v1` link can do that.

## What ran

- `dist/` mirrored with symlinks; two files rewritten in the MIRROR only:
  - the page's one worker literal, `./profiles/ods-viewer-v1/sdk-worker.js` → `./profiles/e2-editor-v14/sdk-worker.js`;
  - v14's `probe.js`: the default pthread stack literal 65536 → 1048576, plus an echo of each
    pthread's stack size (finding 089's arm, both anchors exactly once).
- `dist/profiles/e2-editor-v14/probe.js` hashes the same after the run (`distProbeJsUnchanged: true`).
- The page with `?diagnostics=1`, four files through its own file input, in this order.

## Results (all four predictions met)

| file | outcome | parts | view-ready (ms from the file input) | `open.begin` sbrk | last open-stage sbrk | document cost | pthreads echoing 1048576 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `three-sheets-distinct.ods` | opened | 3 | 1789 | 293,015,552 | 298,328,064 | 5,312,512 | 3 |
| `numeric-100k.ods` | opened | 1 | 1439 | 294,244,352 | 317,792,256 | 23,547,904 | 3 |
| `tdf149752.ods` (finding 089) | opened | 2 | 1191 | 293,015,552 | 305,037,312 | 12,021,760 | 7 |
| `password.ods` | **refused `ENCRYPTED_DOCUMENT`**, no engine created, no engine event | — | — | — | — | — | — |

Read:

- **089 at 1 MiB on the page's path:** `tdf149752.ods` opens. Before this, 1 MiB had been measured
  on this core only through the decisive probe's own page (`findings/089-…`, v12).
- **The encrypted file never reached an engine** (`engineCreated: false`, zero stage lines, zero
  engine events): the typed refusal is before the engine queue, as E2 asks.
- **The boot difference against v12 is the stacks, to the byte:** v14's `open.begin`
  293,015,552 − W1's v12 boot 290,066,432 = 2,949,120 = 3 × (1,048,576 − 65,536), and three
  pthreads echoed the 1 MiB stack in that run.
- `numeric-100k`'s last open stage is W5's 314,814,464 + 2,977,792, inside the predicted range
  (W5 + 7 × (1 MiB − 64 KiB)). Its `open.begin` is 1,228,800 higher than the other two: the input
  bytes (615,493) are copied into the heap before that stage (inference: two copies, rounded to pages).
- Every first paint reported `documentSizeChanged: true` (the 12 px refit question; E4b).

## What this run found that the spec got wrong

**No `document-destroy-*` stage line arrived in any run.** Those two stages are emitted only under
`OXSDK_DIAGNOSTIC_CLOSE_STAGES` (`wasm_sdk_probe/src/probe_engine.cpp:2548-2553`), which no
product or editor rule defines. E6 as pinned reads its peak from "every stage line, including
`document-destroy-enter`", so on the viewer link it could only ever have seen the open stages.
Disposed in the spec's first addendum: the viewer define turns those two stages on.

## Not measured here

- The reader object set on this core, `documentType`, part switching, part text (W7): the link.
- Firefox: this run is Chrome only.
- Other Chrome processes were running (29, the owner's desktop Chrome); recorded, not refused:
  nothing here is a timing criterion.
