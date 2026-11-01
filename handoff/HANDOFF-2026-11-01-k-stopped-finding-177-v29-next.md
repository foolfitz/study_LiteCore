# Handoff: K for 0.2.44 was not run, finding 177 stops it, next is v29 (tick pacing)

Checkpoint **2026-11-01 ~09:20 +0800**. Supersedes `HANDOFF-2026-10-31-k-0244-chain-running.md` for what is next.

## State

- **K did not run. No counted step exists.** Nominal shipped stays **0.2.26**. **0.2.44** stays the daily uncounted candidate.
- Owner's decisions this session: ddev window A (then released by the next one); fable for the merge table (A); on finding 177, **B: no chain, ddev released, fix the latency first** (v29, then a K on the new identity).
- **ddev: do not use it without asking.** `litecore` is left running and idle (lock table 0 at the last read). The owner's desktop has a Firefox open: not ours, do not touch it.
- Untracked and not ours: `codex-claude-code-delegation.md`. Pre-chain leftovers under `findings/evidence/k-0.2.44/{enter-replay/mirror,legacy-v8-gate/mirror-*,merge-smoke/shakedown-chrome.docs}` and `findings/evidence/new-document/shakedown/2026-10-31T152855Z.json` are left untracked as they were.

## What this session found

Spec `specs/SPEC-M3-K-0.2.44.md` appends 1-3 are the record. Nine defects on the path to the count, one of them a product defect:

| | What | State |
|---|---|---|
| H1 | assets assumed one page | fixed, clean on the real site |
| H2 | six counted runners required the static target's exit 0 (exit 2 on named reds); autosave would have refused | fixed, `k_static_target.py` |
| H3 | production UI and host_entry asked the bound tool's default manifest (v76) | fixed, pinned v82 |
| H4 | production UI's C keying refused three wasms, and read v23+ as without C | fixed, page table and ABI >= 6 |
| Merge table | smoke was 21 pass 5 FAIL, not 26/26; frozen tables predate v23 | fable ruling `k-0.2.44/merge-keying/RULING.md`, wrappers keyed in-process, red cases 14/14, mirror proof 20/20 |
| same-second R3 | `premise` 0/2: X crossed the second | phase 0.60, **not re-run** |
| A3-1 | retained list missed the shipped `paste-markdown` | fixed, **not re-run** |
| AS-5 | ninth letter refused with the page's toast, both browsers | inferred second symptom of 177, **re-run on v29** |
| **Finding 177** | typing commit 4 ms to 85 ms since v23/v24 | **cause located, not fixed** |

**Lesson for the next K spec: list the counted-only paths before the chain.** Five of these were unreachable by a shakedown.

## Finding 177 (read it first: `findings/177-...md`)

Core ticks at 100 fps and dispatches one user event per tick; the ordered engine replies at the poll, so 8-9 events cost 85 ms. Proof without a rebuild, `first-contact/typing-control/diag_tick.py` (mirror copy of `probe.js` only): setTimeout(0) 44.8 ms, immediate 9.8 ms; long-document cells meet C2. `boundaries` commit median sits on the 10 ms line (Chrome 9.8, Firefox 10.1). Immediate cannot ship as it is: a core spins while idle.

## Next: v29

Engine change only where it must be: a pure pacing state machine (immediate while there is work, back to 10 ms after 300 ms idle), hooked at the poll, calling `emscripten_set_main_loop_timing`. No core change. Worker and ABI as v28. Template: `specs/SPEC-M3-v28-last-line-fallback.md` sections 5 and 11, `tools/*v28*`, Makefile v28 block.

Link is the owner's (`tools/link_v29_*_owner.sh`, agents run `bash -n` only). After the link: cut the page, generation 83, F3/F4/V0', host 0.2.45, then a new K spec that copies appends 1-3.

**Before the next K, on v29:** C2 cells (the boundaries line), `as5`, P arm, same-second R3. `FOREIGN_PHASE` was set for v28's save speed; if v29 saves faster it must be set again (0.05 fitted v21).

## Section 34.4 this session

Fixed-by-execution: 3 (merge literal, R3 phase, A3-1), plus H1 from the stop. Fixed-by-reading before any run: H2, H3, H4. Fable rulings: 1.
