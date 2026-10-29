# Handoff: owner's hand test on 0.2.40 found finding 173; two work orders opened

Checkpoint **2026-10-29 ~22:15 +0800**. Supersedes 10-29g as the entry point; 10-29g
(`handoff/HANDOFF-2026-10-29g-v25-f1-f4-hold-host-0240-installed.md`) still holds for everything up to the 0.2.40
install and its cautions -- read it second.
Study HEAD **d14186167** plus the commit that adds this file and the two work orders. Tree clean except the unrelated
untracked `codex-claude-code-delegation.md` (preserve it). **Nothing is running.**

## State

- **Host**: 0.2.40 installed on the owner's DDEV (host `main` **ae1f9db**, engine **a08bc6ecb7241448**, Writer v25 /
  shell 78), the daily uncounted candidate. Nominal shipped host stays **0.2.26**. K has not run.
- **DDEV**: only `litecore` (+ router) running. fgp-nc and nc-bridge stopped at 18:06 at the owner's request and stay
  stopped (owner's choice). The 0.2.40 slot (18:45:50-19:30) is over; any DDEV step needs a new owner slot with an
  explicit no-site answer.
- **Tree**: `dist/` serves v25 (page `6e66c930`, shell generation 78). Spec v25 is closed through section 17.

## Since 10-29g

1. **Owner asked what `what_the_link_ships` is** -- answered in chat. While re-reading it, a **second blind spot** was
   found and is not yet recorded in any evidence file: its worker half compares the hard-coded `sdk/sdk-worker.js`
   (`tools/what_the_link_ships.py:287`) against the shipped profile's worker, but since v23 the Writer profile workers
   are built from `sdk/v2X-feature-worker.js`. v25's report compared `0bed22bd…` (the generic worker) with v24's
   `41041fe7…`; its "added lines" (`setPart`, `cellRead`, …) are Calc's, unrelated to v25. v25's own worker was covered
   by W1 (closed-list diff against the archived v24 worker) and post-link X1, so v25 is not affected; earlier batches'
   use of the worker half is part of the open `what_the_link_ships` item (first blind spot: sibling `.inc`/`.h`
   resolve to the live tree, `findings/evidence/link-batch-v25/section-9-reader/README.md`).
2. **Owner's hand test on 0.2.40**: (a) a bullet in a NEW blank document shows 「引擎需要重新開啟」; (b) Ctrl+A does not
   select all.
   - (a) = **finding 173** (`d14186167`; `findings/173-…md`, `findings/evidence/173/`): reproduced on the mirror with
     the host's own blank template; v24 and v25 `recoverable-error` with `failureShape: select-text-returned-none`,
     v22 kept the queue open as `stage-deadline:awaiting-selection` (finding 083). The ordered engine renamed 083's
     situation; the page's disposition does not know the new name. First shipped in 0.2.39; still in 0.2.40.
   - (b) is not a regression: select-all (id 21) has been in the engine since v4, withheld by the manifest
     (`gestures: []`), and the page deliberately binds no Ctrl+A (2026-08-19: a geometric range "succeeded" and selected
     nothing).
3. **Owner decisions** (2026-10-29 ~22:00): 173 -> **A, fix the page and ship 0.2.41**; select-all -> **A, candidate for
   the next engine batch (v26)**. Then: "write the work orders first, then hand off" -- so no spec, test or code for
   either has been written.

## Next steps

1. **`handoff/WORKORDER-173-blank-document-bullet-page-fix.md`** -- start at its step 0 (pin
   `specs/SPEC-M3-shell-v79-finding-173.md` before any implementation or browser run). Page-only fix, no relink:
   shell generation 79, host 0.2.41, a new owner slot for the install. The work order lists the traps (serve the
   "before" product from its own bytes; do not edit the v78-pinned tools; re-attach the worker observer after a file
   open).
2. **`handoff/WORKORDER-v26-select-all.md`** -- after 173 or in parallel offline: a zh-TW research note first. Its first
   question is open: whether the ordered engine (v23+) routes action 21 at all (no `ordered_*.inc` mentions it).
3. Still open from 10-29g: K (8-10 h no-site window + the K control protocol,
   `handoff/WORKORDER-v24-K-control-protocol.md`); the `what_the_link_ships` census (both blind spots); spec v25
   section 2/10 leftovers.

## Cautions

All of 10-29g's, plus: a manual product test by the owner found a path no check covered within an hour of install
(the second time this tree has learned that the harness path is not the user's path) -- when writing 173's B1, start
from the owner's exact steps (Files "+ New -> New document", then the toolbar bullet), not from the product-path
fixture.

## Section 34.4 this round

Fixed-by-execution **1** (finding 173's diagnostic tool lost its worker session on file open; re-attached in run-02,
recorded in `findings/evidence/173/README.md`). Fixed-by-review **0**.

## Language

Replies to the owner: Taiwan Traditional Chinese (A/B/C for options). Evidence, upstream text and `handoff/**`:
English. `devlog/`, `research/`, `specs/`: zh-TW (specs append-only once pinned).
