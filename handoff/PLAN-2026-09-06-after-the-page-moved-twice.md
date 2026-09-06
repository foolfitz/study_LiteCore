# Plan, 2026-09-06 — after the page moved twice: what runs, in what order, and who runs it

Written by the fable main session from
`HANDOFF-2026-09-06-the-page-moved-twice-and-the-4b-instrument-broke.md`.
This document carries the *judgement*: sequence, delegation, and the decisions
that are the owner's. Facts are checked against the tree where stated; where a
fact is inherited from the handoff without re-checking, it says so.

## Working form for this line (adopted from `study_OxODF`, 2026-09-04 "B form")

The main session is fable and does judgement only. Cost is roughly context size
times turn count, so the loops, the code edits and the large-file reads go to
subagents, and each subagent's report starts with `## SUMMARY` of at most 30
lines, which is all the main session reads.

| kept by fable | delegated to |
|---|---|
| decisions, the ten-line brief for each task, one pre-read of an assembled object, the sentence that says a gate condition passed | — |
| expanding a brief into a pre-registered protocol (criteria written before the run), adversarial review of a protocol or a verdict | **opus** subagent |
| Task 0, gate operations (4a, condition 2, ODT round trip, revert condition 3), soak runs, measurement loops, handoff drafts | **sonnet** subagent |
| review seat b | **codex** — *off by default* in this project (memory, 2026-08-23: its quota runs out; delegating is not saving, it is paying elsewhere). The owner may switch it on per task. |

Isolation: a task that touches only tracked files runs in a git worktree
(`Agent isolation: worktree`) and the main session fast-forwards its branch after
reading the diff. A task that needs `wasm_sdk_probe/dist/` (untracked, 0 files in
git), a browser or the desktop runs in the main tree and commits only its own
files.

Discipline for the main session: no code edits, no loops, no `cat` of a large
file (grep a section), no `fork` (a fork inherits the whole context and runs on
fable).

## State at the start of this plan (checked 2026-09-06)

| | value | source |
|---|---|---|
| tree | clean, 555 commits unpushed, `main` has no upstream | `git status` |
| candidate page | `39895d15…` (`build_cutover_page.py --profile e2-editor-v12`) | handoff, not rebuilt here |
| frozen generation | v45, `bundleSha256 a46c8518a7ebfb12…` | `wasm_sdk_probe/e2/editor-shell-v2-bundle-v45.json` |
| `check_soak_bank.py` `DEFAULT_SHA` / `DEFAULT_SERVED_SHELL` | `20f09cc9…` / `78c23684…` — **stale** | lines 108, 217 |
| `check_caret_diagnostics.py` `DEFAULT_SHA` | `20f09cc9…` — **stale** | line 50 |
| soak bank | 10 runs + 3 diagnostics + condition-2 verdict, all on the dead page | `findings/evidence/queue-v12-cutover-soak/` |
| soak count | **0 of 12** | ruling of 2026-09-06 |
| `/tmp` | 4% of 16 GB used; the 98% trap is gone | `df` |
| desktop | `DISPLAY=:0`, Orca and google-chrome installed; agent-driving consent on file | `manual-round-v12b-20f09cc9/CONSENT.md` |

## Critical path

```
T0  re-point the judges, void the dead runs, self-test both   [sonnet, worktree]  ── no desktop
 │
 ├── T1a design the 4b instrument-reproduction protocol         [opus]             ── no desktop
 │    └── T1b run it                                            [sonnet, main tree, desktop idle]
 │         └── T1c only if it reproduces: v45 vs v46, same protocol   [sonnet]
 │              └── D1 (owner): land v46 + freeze generation in the same commit, or ship v45
 │
 └── after D1 the page is FINAL for this gate; everything below is bound to it
      T2  re-earn 4a, condition 2, ODT round trip, revert condition 3   [sonnet, main tree]
      T3  soak: 12 clean runs, >=3 UTC days, >=2 per day                [sonnet, scheduled]
      T4  the owner's manual round: condition 3's six cells + 4b's judgement half   [owner]
```

T0 and T1a start now, in parallel. T1b waits for two things: T1a's protocol
committed, and a window in which the owner is not using the desktop — the
handoff's cleanest-looking failed walk was Orca narrating a company-registry
page in another window, and no instrument can subtract the owner's own typing
from the log.

**Nothing in T2–T4 starts before D1**, because every one of them is
identity-bound and the next page move voids it. That is the whole lesson of
today's count going 10 → 0.

## The decisions that are the owner's

**D1 — which page does the gate freeze on?** v45 ships the doubled-paragraph
fix and leaves one audible residue (at the second heading the live region
speaks the previous paragraph). v46 fixes that residue but is
NOT_ESTABLISHED because the instrument stopped reproducing.

- **A (recommended)** — bound pursuit. Run T1 with a budget of **two sonnet
  sessions or 2026-09-08, whichever first**. If the instrument reproduces and
  v46 measures better on the same protocol, land v46 with generation v47 in
  the same commit and freeze there. If the budget runs out, freeze on v45 and
  record the residue under 4b's named-residue clause (the plan already allows
  it: "against a baseline of nothing, a verified-correct tree is the benefit").
- **B** — freeze on v45 now and start T2 today. Fastest to a running soak; the
  residue becomes a post-cutover finding. Risk: the owner already chose once to
  fix what they heard rather than ship it; if that holds, this restarts the
  count later at a higher price.
- **C** — no freeze until v46 is established, no budget. Rejected by the
  drafting party: an open-ended condition is exactly the form `AGENTS.md` §2
  forbids.

Default if the owner says nothing: **A**.

**D2 — finding 086 (setting a heading fails on a real document, on both
profiles, ships on v8 today).** Its fix lives in the shell's barrier, so it
moves the page. Either it is batched into the same freeze as D1, or it waits
for after the cutover. **Recommended: after the cutover.** It is not a
regression, the revert trigger does not fire on it, and batching it means T1
must re-measure on yet another page.

**D3 — codex as review seat b** for T1a's protocol. Off by default (see the
table). The owner can say "codex on" for that one review.

## Parked, and why

- **Finding 090's guard** (compare `web/` with `dist/`): not built. The finding
  itself says inventing machinery while closing a gate is how a gate stops
  meaning anything (`AGENTS.md` §4's self-check). Every run keeps the manual
  `sha256sum` of both directories in its record. Revisit after the cutover.
- **Finding 089** (the ODS cliff, two axes, WASM-side, no cause named): a
  separate line, not on this gate. Untouched until the soak is running.
- **Pushing the 555 commits**: the owner's step.
- **Environment traps**: `/tmp` is clear now; Orca logs go on disk under
  `findings/evidence/`, never `/tmp`; never `pkill -f`/`pgrep -f` — iterate
  `pgrep -x python3` and read `/proc/$p/cmdline`.

## Task briefs

Each brief is ten lines or fewer. The executor expands it; the expansion is
committed before the work it governs.

### T0 — re-point the judges and void the dead runs (sonnet, worktree)

1. `check_soak_bank.py`: `DEFAULT_SHA` → `39895d15…`; `DEFAULT_SERVED_SHELL` →
   v45's `a46c8518…`, **verified** by recomputing `shell_bundle_digest` over the
   tracked `web/` (the worktree has no `dist/`) and by reading
   `editor-shell-v2-bundle-v45.json`. `check_caret_diagnostics.py`:
   `DEFAULT_SHA` → `39895d15…`.
2. Void by the per-instance rule, not by name: every `*.json` under
   `queue-v12-cutover-soak/` whose page sha is `20f09cc9…` (soak runs,
   diagnostics, and the condition-2 verdict judged on them) moves with `git mv`
   to the sibling `queue-v12-cutover-soak-void-20f09cc9/`, with
   `WHY-THESE-ARE-VOID.md` (English) naming the page move and the handoff.
   Files bound to any other page stay; the classification table goes in the
   report. Append the void to `RUNS.md`.
3. `--self-test` on both judges, then a real run of `check_soak_bank.py` on the
   now-empty bank: expected **0 of 12**, not RED.
4. One commit, zh-TW subject, `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`,
   no session line. Report `## SUMMARY` ≤ 30 lines: the three old/new values,
   the classification table, both self-test outputs, the 0-of-12 line.

### T1a — the 4b instrument-reproduction protocol (opus, design only)

1. Object: `drive_walk_focus.py` (banked in `manual-round-v12b-20f09cc9/`) on
   the candidate page `39895d15…`; new evidence directory
   `manual-round-v12c-39895d15/`.
2. Reproduction criterion, per-instance: two consecutive walks on identical
   bytes with `focusHeldEveryStop: true` give the same announced-paragraph
   count, **and** that count equals the number of stops at which focus was held
   and the paragraph's text reached the Orca log. Two walks that agree at 1
   are a reproducible broken instrument, not a reproducing one; say so.
3. Separate the three named variables one at a time, each against a control:
   Orca before Chrome vs after; a fresh Orca per walk vs `orca --replace`
   cycling; a fresh tab per walk vs the same tab walked twice. Never raise the
   window before every press (measured worse, 1 of 10).
4. Pre-register the stop rule and the budget (walks, not minutes). Say what
   each outcome means before anything runs.
5. Environment constraints to write in: `DISPLAY=:0`, consent file cited,
   desktop idle, logs on disk, no `pkill -f`.
6. Deliverable: `handoff/tasks/TASK-2026-09-06-4b-instrument-reproduction.md`
   (English), committed, plus `## SUMMARY` ≤ 30 lines. No desktop use, no runs.

### T1b, T2, T3 — briefs written after T0 and T1a land.
