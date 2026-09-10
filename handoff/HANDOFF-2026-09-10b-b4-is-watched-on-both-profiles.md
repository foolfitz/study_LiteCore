# Handoff, 2026-09-10 (b) — B4 is watched on both profiles; the rest of the 09-10 list is untouched

Entry points, in order: this file, then
`handoff/HANDOFF-2026-09-10-096-is-fixed-and-the-guard-went-quiet-where-it-matters.md`
(everything there still holds except its one undecided item, closed below),
then `findings/096-*.md` read whole (the T8b section is the last one), then the
last two sections of `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`.

Tree clean, nothing pushed. `make test-e2-c-static` exit 0 at `ffb5c96a`; no
runner change since.

## What was decided and done today, after the morning handoff

The owner ruled **(a)**: the 42nd check gets a second inducer so B4 is reachable
on a profile carrying A. It followed the `recovery-returns-what-the-product-
promised` precedent exactly — `induce_worker_failure`, a real uncaught error in
the document worker, induced over CDP from outside the product. Registered as a
**designed sentinel** (AGENTS.md §3), not a hole; not new machinery (§4): no
product byte, no engine change, no link.

Delegation ran in form B: the main session wrote the brief and pre-read the
diff; opus expanded the protocol and implemented (T8a, nine commits); sonnet ran
the red cases and the plain runs (T8b, two commits); the main session re-read
the seven JSON reports with its own reader before writing anything.

## The state of the 42nd check

| | v14 (`e2-editor-v14`, fixed) | v8 (shipping) |
|---|---|---|
| `clausesExercised` | `[B1, B3, B2, B4]` 3/3 | `[B1, B3, B4]` unchanged |
| `b4Inducer` | `worker-failure` | `boundary-press` |
| B1–B4 | all true, 3/3 | all true, cell-for-cell the banked run |
| composition | 40 PASS / 2 NE | 40 PASS / 2 NE |

Red cases, each reddening this check and nothing else: (i)
`boundary-move-takes-no-checkpoint` now reds B3 **and** B4; (ii)
`worker-crash-throws-the-checkpoint-away` reds B4 alone; (iii)
`worker-crash-is-never-noticed` leaves B4 `null`, omits it from
`clausesExercised`, and the check is **FAIL, not NOT_ESTABLISHED** — the reason
is protocol §3 and the code comment: NE would keep the run green while hiding
the same hole one notch quieter.

## What the next person must carry

* **B4 on v14 is a weaker claim than B4 on v8.** It shows the gesture's
  checkpoint survives a death from another cause; it cannot show that the
  gesture's own death is recoverable, because on a profile carrying A the
  gesture cannot kill the session. Do not quote one for the other.
* **The inducer is instrument.** If `induce_worker_failure` stops working for
  an instrument reason, this check is red on every fixed-profile run until
  someone looks. That cost is written in the code and accepted.
* **Two `Target.setAutoAttach` call sites have an order dependency** (protocol
  §7). Today only the boundary arm's fires, because 038 still reproduces on both
  profiles and so the recovery arm never falls back. If 038 ever stops
  reproducing, both fire in one run and that has not been measured.
* **Worker generation budget is exactly spent**: 3 of 3 on both profiles
  (initial open, recovery arm, boundary arm). Any new arm that restarts the
  worker will hit `WORKER_GENERATION_LIMIT`.

## Measured and not explained (new today)

* `savedBytes` took four values across four unmutated saves
  (12895 / 12897 / 12899 / 12899).
* `offPageInk.scans` was 38 or 39 across otherwise identical plain v14 runs.

## Still open — unchanged from the morning handoff

1. The wrong-gesture wording of the notice (061's shape). Owner's ruling; the
   cost argument is weaker now that the page moves with every link anyway.
2. Findings 094, 095, 097. 095 has a one-line discriminator (wait longer than
   30 s) and its harness-path caveat is not excluded.
3. Why the core broadcasts nothing at a boundary. Two remedies named:
   engine-side callback/command correlation (relink) or the browser-free native
   LOK harness under `tools/f059_native_*.cpp` (no relink).

## The gate

Unchanged: everything identity-bound died with the link to v14; the soak is
reordered to the end (0 of 12, full run on the final identity before any
cutover, floor of three calendar days); T4 must be re-earned on the final
identity and is the owner's evening. The shipping page still points at v8.
**No cutover has been performed.**

---

## Later the same day (append-only)

* **Form B′** replaces form B for tasks opened after 2026-09-10 (PLAN, "Form
  B′"): diagnosis and discrimination design, pinned criteria, and small
  semantics-heavy runner/probe edits return to the main session; sonnet keeps
  long runs and evidence banking; opus and codex (available again) review only.
  A subagent's diagnosis is a hypothesis until the main session has read the
  source it rests on.
* **T9 closed**: finding 095 is re-attributed as 096's pre-death window on
  profiles without half A (S8 died 3/3 at 30.0 s, S14 survived 3/3, L8 was
  never a boundary press — the long fixture ends with an empty paragraph).
  See PLAN "T9 landed".
* Open list is now: the wrong-gesture wording (061's shape, owner's ruling);
  findings 094 and 097; why the core broadcasts nothing at a boundary (next,
  under B′: main session designs the discrimination from the engine source,
  sonnet runs the native harness, codex reviews the diagnosis before action);
  and the new unexplained item that arrow presses alone let half C bank a
  checkpoint.
