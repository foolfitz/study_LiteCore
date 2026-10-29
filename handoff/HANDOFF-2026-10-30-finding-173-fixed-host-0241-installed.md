# Handoff: finding 173 fixed on the page (shell generation 79), host 0.2.41 installed; select-all route read

Checkpoint **2026-10-30 ~00:00 +0800**. Supersedes 10-29h as the entry point; 10-29h
(`handoff/HANDOFF-2026-10-29h-finding-173-and-select-all-work-orders.md`) and 10-29g still hold for everything they
say that is not superseded here. Tree clean except the unrelated untracked `codex-claude-code-delegation.md`
(preserve it). **Nothing is running.**

## State

- **Host**: **0.2.41 installed** on the owner's DDEV (host `main` **2bb5718**, engine **829a988e199ebc43**, Writer v25 /
  shell generation **79**), the daily uncounted candidate, superseding 0.2.40. Nominal shipped host stays **0.2.26**.
  K has not run. Owner slot 23:51:55-00:30 (`findings/evidence/host-0.2.41/slot.json`); only `litecore` (+ router)
  running; fgp-nc and nc-bridge stay stopped (owner's choice).
- **Tree**: `dist/` serves page **`9cb6ea1f…`** (generation 79, profile `e2-editor-v25`, pin `44cb15ea8d36f0e0`).
  Makefile bundle line -> v79. Spec `specs/SPEC-M3-shell-v79-finding-173.md` closed through section 10 (append-only).

## Done this round (commits a43a69bc6 .. d06b7c439)

1. **Work order 173 complete except the owner's hand test** (`findings/evidence/shell-v79-173/README.md`):
   spec pinned first; U1/U2 red then green (shell tests 524/524); `paragraph-editor-client.js` exports
   `EMPTY_SELECTION_SHAPES` (the two names of finding 083's situation) and the page's review sentence imports the
   same list; B1 (`tools/check_v79_blank_bullet.py`, the owner's path with REAL clicks and keys, saved ODT read)
   `B1_HOLDS` 12/12 after, 12/12 before red for 173, Chrome + Firefox; generation 79 frozen; F3-79 holds under spec v25
   16/16.1 and is cell-for-cell equal to v25 F3 run-02 (46/46 x 2); F4-79 24/24; V0' holds (both declared files
   restored, three readers byte-identical); E1-C intact; host 0.2.41 packaged (exactly two records changed vs 0.2.40,
   `DELTA_HOLDS` with five reds, `PACKAGE_HOLDS` 22/22), installed, Files 52/52, post-install read holds.
2. **Select-all research note, part 1** (`research/2026-10-29-select-all-route-on-v25.md`, zh-TW): on v25, action 21
   reaches the ordered key path (`dispatchOrderedKey`, `Key::A|Mod1`, `mutation=false`) once a gesture is granted;
   today the worker's manifest check, the engine mask and the shell client's closed lists withhold it. **Granting it
   needs no relink** (a new manifest = new profile identity; shell client change = new generation; page binding).
   Two details: it keeps the revision-demanding class (`editorActionMutates`), and an existing range needs BOTH range
   bits. Postcondition NOT measured. Main-session notes of the subagent trace:
   scratchpad only (not kept); the note cites the source lines read.

## Next steps

1. **Owner's hand test on 0.2.41** (asked at the end of this session): Files "+ New -> New document" -> bullet ->
   type -> save. Expected: no 「引擎需要重新開啟」; toast 「動作已送出，但這一段是空的…」; the typed text is a bullet
   item. Record the answer in finding 173 (status line + revision log) and the host README. If it fails, the
   host route differs from the mirror's file-input route (spec v79 section 6, L-mirror-open-route) -- measure that
   route before touching code.
2. **Select-all, work order step "deliverable 1" questions 2-4**: a scratch manifest (never in `dist/`) granting all
   three gestures to `select-all`, measured on the mirror: engine selection state and painted wash after select-all,
   whether the reply and its callbacks land in the same poll, then typing/delete/format/copy/undo over the whole
   range, on documents with tables, frames, notes and a blank document. A positive control must catch the 2026-08-19
   "reported success, selected nothing" shape. The shell client refuses `select-all` before any request, so the
   measurement must post to the worker directly (harness path) -- say so in the note, and plan the page path for the
   spec. Then a zh-TW spec with pinned criteria and red cases (work order "Then").
3. Still open: K (8-10 h no-site window + control protocol); the `what_the_link_ships` census (both blind spots,
   10-29g/h); spec v25 section 2/10 leftovers; **new**: `capture-after.py` gates on the runner's `ok` summary, not on
   the cells (host-0.2.41 README, named limit) -- a successor that re-derives `ok` belongs in the next host's scripts.

## Cautions

All of 10-29g/h's, plus:
- `tools/v25_f_products.py`, `run_v25_f3.py`, `run_v25_four_arms.py`, `judge_v25_product_four_arms.py`,
  `v25_four_arms_identity.py` pin generation 78 and are now NE on the live tree by construction. Do not edit them;
  use the v79 derivations or the V0' restore (`findings/evidence/shell-v79-173/v0/run_v0_prime.py`).
- `run_v0_prime.py` rewrites the page and client in source and `dist/` while it runs; never run it while anything
  serves `dist/`.
- B1 mirrors symlink `dist/`; same rule.

## Section 34.4 this round

Fixed-by-execution **0**. Fixed-by-review **0**. Operator slips with no tool change: B1's first launch redirected
stderr into a missing directory; `capture-after.py` was first run without its two arguments; the first
post-install red case was built inconsistently (cell flipped, summary not) and exposed the named limit above.

## Language

Replies to the owner: Taiwan Traditional Chinese (A/B/C for options). Evidence, upstream text and `handoff/**`:
English. `devlog/`, `research/`, `specs/`: zh-TW (specs append-only once pinned).
