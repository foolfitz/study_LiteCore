# Ruling brief 1 — finding 089: what next, now that six environment switches are refuted

**Authority:** the owner, 2026-10-13: 「有疑義的發給fable，我授權它代我下決定」 ("anything in doubt goes to
fable; I authorise it to decide for me"). You rule on the owner's behalf. Link steps, pushes and deletions are
excluded.

**Reply with four headed parts:**
- `RULING`
- `WHY (for the owner)`: in Traditional Chinese (Taiwan), plain language, 3–6 sentences
- `FACT CHECK`: for each F below, confirmed / refuted / not checked, with file:line
- `CONDITIONS`: numbered; each one checkable

Write it to `findings/evidence/089/ruling/ruling-1.md`. Commit only that file, with an English message ending
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and no `Claude-Session:` line.

## Facts (claims to check, not premises to accept)

- **F1.** On the writer+calc profile `e2-editor-v12`, `rows36` and `index35×36` never open: 180 s cap, 3/3 on
  2026-09-07 and every arm on 2026-10-13. `rows35` and `index36×35` open in about 1.2 s, but the worker dies
  with `memory access out of bounds` on the default path. Natively the file opens in about 269 ms.
  Sources: `findings/089-*.md`, "非對角線量完了" and later sections.
- **F2.** While hung, the whole browser process tree uses about 1% of one core. One `DedicatedWorker` thread is
  woken about 10 times a second and does nothing. Source: `findings/evidence/089/cpu-or-wait-2026-09-07/`.
- **F3.** Six environment arms, pre-registered in `handoff/tasks/TASK-2026-10-13f-089-threading-arms.md`
  (§5 and Amendment 2), echo-verified, evidence in `findings/evidence/089/threading-arms-2026-10-13/`:
  - `SC_NO_THREADED_CALCULATION=1` ×3, `SC_FORCE_CALCULATION=core`, `SC_FORCE_CALCULATION=threads` ×3,
    `SAX_DISABLE_THREADS=1`, and `MAX_CONCURRENCY=1` each leave both hung fixtures hung.
  - The crash disappears under every `SC_*` arm (0/14) and stays under the other two.
- **F4.** `dist/profiles/e2-editor-v12/probe.wasm` and `e2-editor-v14/probe.wasm` contain no custom sections,
  so they have no name section. The main session measured this on 2026-10-13 by walking the section table.
- **F5.** Finding 037's precedent (`wasm_sdk_probe/tools/probe_wait_primitive_names.py` docstring; the tool
  `probe_wedge_thread_state.py`): a CDP `Debugger.pause` on every worker target reads frames without a
  rebuild, but application frames come back as `$funcN`. Naming them needs the same inputs relinked with
  `--profiling-funcs`, and function indices do not correspond between two links.
- **F6.** A names-carrying link is the owner's step. The Makefile has no rule for a `--profiling-funcs` twin of
  the writer+calc profiles. Editing the Makefile relinks every artifact that depends on it unless guarded
  (finding 042). Existing guarded precedent: `link_e2_preguard_profiling` (`wasm_sdk_probe/Makefile` ~line 913).
- **F7.** The owner's current order (handoff 10-13d, addendum 2):
  - Track 1 is the link batch on the writer-only core (Shift+Arrow, page numbers, and more). The spec is in
    review now.
  - Track 2 is ODS preparation with no link. 089's cause is one of its three items. W6 and the W9 draft are
    done.
  - The writer+calc core switch and W8, a writer+calc relink by the owner, come after the link batch.
- **F8.** `upstream/tdf149752.ods`, the source of every 089 fixture, is an entry in `test-docs/ods/manifest.json`
  (~line 4407). Gate G2 (`handoff/PLAN-2026-09-03-ods-reading.md` §3) requires every entry to open, or to be a
  typed refusal declared `expect: "refused"`. As it stands, 089 blocks G2.

## Options (the main session's reading; attack it)

- **A.** An index-only pause probe now. Adapt `probe_wedge_thread_state.py` / `pause_and_read` to the ODS
  probe page. No owner step, about an hour.
  - What it can show: which worker targets exist; which pause (running or periodically woken) and which never
    pause (parked in a wait); the shape of the wait; and whether some worker never started. A worker that
    never started would be a pthread-pool signature by itself. The pool is `-sPTHREAD_POOL_SIZE=7`, not
    strict.
  - What it cannot show: which LibreOffice function is waiting.
- **B.** Ask the owner now for a `--profiling-funcs` diagnostic twin of v12's inputs, linked into `build/` only,
  then run the pause probe with names. One owner link, plus a guarded Makefile rule.
- **C.** Do nothing more on 089 now. Write down that a names twin rides along with W8's owner link after the
  link batch, so one sitting does both. 089 stays unattributed and G2 stays blocked until then.
- **D.** A now, then C.

**The main session's lean: D.**
- A costs no owner time.
- It has one outcome that would be decisive without names: a worker that never started.
- The owner's attention is on the link batch, and a names twin can share W8's sitting.
- Against D: per F5, A's application frames are unreadable, and 037 already showed that "parked in
  `atomic.wait32`" is the expected shape. A may well add nothing that F2 does not already say.

## Also rule on

**Q2.** NU-089-3 (the crash follows the `SC_*` variables). The source reading, unmeasured, is that all three
`SC_*` arms skip the configuration-listener construction inside `ScCalcConfig::isThreadingEnabled()`
(`libreoffice-26-8/sc/source/core/tool/calcconfig.cxx:80–89`; the short-circuit at `formulacell.cxx:5096`).
Is that worth one more pre-registered arm now? For example, a profile-level configuration override that
disables threading through the registry instead of the environment would separate "the listener" from "the
variable". Or should it be recorded and left, given that the crash does not stop the file opening?
