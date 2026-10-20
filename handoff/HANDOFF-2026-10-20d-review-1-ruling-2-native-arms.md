# Handoff, 2026-10-20d: two-seat review 1, ruling 2, and the native arms it asked for

**First line:**
- **ddev runs host 0.2.28** (`0870695`). It is the uncounted candidate for daily use; the nominal shipped version is still 0.2.26.
- For v23 (candidate C), review 1 and ruling 2 are disposed; nothing is linked yet.
- **The caret-delete witness reads G-HOLDS (N=5).**
- **One native run may have been cut short by the session restart.** Check `object-click/out/` first (Next 1).

This continues `HANDOFF-2026-10-20c-host-0228-installed-h155-pass.md`, whose 0.2.28 facts stand, and `HANDOFF-2026-10-20b-v23-spec-pinned-n1-holds.md`. Next 2 of 10-20b is done, Next 3 is done, and Next 4 is still ahead. The main session was opus. The owner was present and paused at 17:26 to restart the session under tmux.

## What happened (commits in order)

1. **Host 0.2.28 installed**, in the owner's window 14:00–14:45 (10-20c). The desk gate was withdrawn for non-timing chains (v22 spec §14.5).
2. **The model in two modes** (`76fe206f`; spec §14):
   - the threaded mode still prints 27,744 / 2,448 / 5,474 / 3,868, now all pinned;
   - mode C is 0 Writer-divergent and 0 forged in all 8 shapes, and its two red cases are red.
3. **Two-seat review 1:**
   - the brief is `152949f5`;
   - the codex (`codex exec -s read-only`) and opus seats are imported verbatim in `ef673ecc`;
   - the main session's checks are in `findings/evidence/link-batch-v23/review/disposition-1/`.
4. **Undo grouping, measured natively** (`disposition-1/grouping/`):
   - the `.uno:Undo` payload stops changing after the 19th equal character deleted in one direction;
   - spec §5.4/§5.5's undo proof then answers a real Delete with `verified-boundary-noop`.
5. **Ruling 2** (fable, on the owner's choice A; `18e961d0`, with the main session's source check appended):
   - caret delete: undo paired with `getA11yFocusedParagraph`, guarded to mid-paragraph positions, measured first; the default is the barrier;
   - "STATE_CHANGED is timer class" is withdrawn in favour of a tool-generated on-time list;
   - object click: a named limit plus an arm;
   - content after the reply: limits;
   - N1a's tile clause is withdrawn;
   - one command per poll: an engine red case plus a §9.2 cell.
   - The source check found the product core compiles a11y in (`build-a11y-gate0`), so the decider needs an a11y-available guard.
6. **Spec §15 appended** (`516390c7`). It holds every withdrawal and correction, three named limits, the §9.2 cells and precondition, the readers' fix list and the order.
7. **The readers' one review (§34.3), disposed** (`465c55c1`; `review/DISPOSITION-two-seat-1.md`):
   - nine fixes, each with a red case shown failing on the HEAD reader and passing on the fixed one (`red-old-vs-new.txt`);
   - re-judged, C-HOLDS and N1-HOLDS **did not move**.
8. **The caret-delete witness, counted** (`e129ac42` criteria and smoke; `4e0207ab` result; `native/caret-delete-witness/README.md`). **G-HOLDS**: 50 processes.
   - uni1, every round: paired = lost (25, 25, 25, 0, 0), and undo-only = 19 on the two underscore arms.
   - The a11y read at return carries the key's effect.
   - **Correction to ruling 2:** 25 distinct CJK characters give undo-only 25/25. The hole is runs of identical characters (fill-in lines), not CJK sentences. Spec §15.7 says so, and requires that the product-path arm include such a run.
9. **The object-click arm**, pinned with its smoke (`1085726b`; `native/object-click/ARMS.md`). The smoke landed every arm in uni1f as in seq. The harness gained mode `uni1f`, op `I<ms>` and the click offset `+dx`; the binary is `cdda2f0f…`.
10. **The N1 second run**, pinned (`ed7666e4`; `native/ordered-commands/ARMS-n1b.md`). **Not run yet.**

## Next

1. **The object-click counted run** (`native/object-click/out/`, uncommitted). It was 64 of 80 cells done at 17:26 when the session was paused. If the run finished and its log has 80 exit-0 lines:
   - read it: `python3 -I findings/evidence/link-batch-v23/native/object-click/read_oc.py findings/evidence/link-batch-v23/native/object-click/out`, saving the output as `out/reader-output.txt`;
   - write `object-click/README.md`;
   - commit.

   If it was cut short:
   - rename `out/` to `out-interrupted-1726/`, together with `out-runner.log`. Do not delete it;
   - rebuild the binary from the line in `object-click/build.txt` (absolute paths). It must reproduce `cdda2f0f…`;
   - re-run `run_arms.py --arms-set o --modes seq,uni1f --runs 5` into a fresh `out/`, which takes about 20 minutes.
2. **The N1 second run:** `ARMS-n1b.md` says how. Two invocations go into `out-n1b/`: all arms in `uni1ai`, then `--only join200 --modes uni1`. That is about 85 processes and 25 minutes. Then:
   - read it with `tool/read_n1.py out-n1b`;
   - generate `--on-time-list`;
   - commit.
3. **Then the diagnostic-profile engine code** (spec §9.2 as amended by §15.4/§15.1). **Red cases first, as engine unit tests:**
   - one command per poll, where the old drain-until-empty must fail;
   - `anyInput` including a pending reply;
   - reply first;
   - a non-blocking poll;
   - the paired caret-delete decider as a pure function, with the G run's recorded tuples as its fixture and labels from the saved text; the undo-only variant must mislabel 6 ops;
   - the a11y-available guard;
   - `STACK_OVERFLOW_CHECK=2` on the diagnostic link only;
   - `OXSDK_FINDING_016_SCHEDULER_PROBE` not defined (a precondition read from the build record).

   This is big. Ask the owner whether to start it in that session. **The owner links it** (the owner's make).

## Hazards

- **Never `cd` in shell commands.** This stretch slipped twice into evidence directories, and the harness moved the primary working directory. Use absolute paths.
- **Native runs never overlap.** Each `run_arms.py` invocation is one at a time.
- **The harness binaries live in this session's scratchpad**, which is lost on restart. Rebuild them from `build.txt` and check the sha before any run:

  | binary | build record | for |
  |---|---|---|
  | `b857a9b0…` | `native/caret-delete-witness/build.txt` | the G run |
  | `cdda2f0f…` | `native/object-click/build.txt` | the object-click run and the N1 second run |

- **The two native readers have had their one review.** Their repaired-because-of-review count must stay 0 from now on. `read_g.py` and `read_oc.py` are new and not yet reviewed.
- **The spec is append-only.** Any new criterion needs CLAUDE.md §9's four conditions.

## §34.4

- **This stretch:**
  - because of execution **+1**: the 0.2.28 chain's guard;
  - because of review **+9**: the native readers' one review.
- **Running total since 10-14b: 33 / 27.**
- **New tools, not yet reviewed:** `read_g.py`, `read_oc.py`, `n1_outside_window.py`, `red_old_vs_new_*.py`; and the harness modes and ops `OC_A11Y`, `uni1f`, `I<ms>`, `+dx`.

## Registered work items (new)

- The §9.3 product-path arm for caret deletes. It must include a run of identical characters (§15.7).
- `.uno:Delete` on empty table cells answers `changed:true`. Pre-existing; a §9.3 table arm.
- The native harness's poll callback has no re-entrancy guard against `Reschedule` (HTML/Markdown import).
