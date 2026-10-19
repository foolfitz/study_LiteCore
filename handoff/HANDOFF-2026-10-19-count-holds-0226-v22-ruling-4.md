# Handoff, 2026-10-19: the count holds on 0.2.26 (now the nominal shipped version); v22's stack size measured without a relink and ruled (fable ruling 4); the v22 spec is next

This continues `HANDOFF-2026-10-17c-d2-pass-host-0226-bound-count-chain-ready.md` (and its "Addendum, 2026-10-19") and covers commits `9c8d83cc..HEAD`. The main session is opus. The owner was present. They:
- ran the 0.2.26 count chain themselves overnight;
- asked to be guided through the v22 link (order C);
- sent both v22 questions to fable (「兩個問題都發給fable」).

This file replaces 10-17c as the entry point; the memory index points here.

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.26**, replacing 0.2.24 (`efb8ae77`; `findings/evidence/m3-production-ui/RESULT-0.2.26.md`; `SPEC-M3-link-batch-v21` §12.6 K result) |
| Host | 0.2.26, host `3c01876`; engine package `f5f0df762e1855f2`. Unchanged |
| Shell / engine | v74 (`27f33a13…`), page `605cf24b…`; `e2-editor-v21` (wasm `db3408f5…`, loader `0b6cf02a…`, worker `0d55bcfa…`). `dist/` is v21 |
| v21 archive | `wasm_sdk_probe/build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/` (10-16). `sha256sum -c SHA256SUMS`: 5/5 OK on 10-19; probe.wasm and probe.js equal `dist/`'s |
| Item 2 (Markdown paste) | Still withheld (finding 153). The release text's §4.1 sentence stands |
| Release text | `handoff/RELEASE-TEXT-0.2.25-0.2.26.md` (`ff03403c`), zh-TW for the owner. Owner's reading not confirmed |
| Owner's hand test of 0.2.26 | **Not reported** |
| v22 | Order C. Value ruled: `-sDEFAULT_PTHREAD_STACK_SIZE=1048576`; `STACK_OVERFLOW_CHECK` off (ruling 4, `ba41330a`). **Not started:** no spec, no `E2_V22_*` Makefile block, no runbook, no link |
| Merge runner | §34.1 freeze lifted (the 0.2.26 verdict has been read) |
| Tree | Clean after this handoff's commit |

## What happened

1. **The count chain on 0.2.26** (`efb8ae77`).
   - The owner started it at 00:06 and it reached `DONE` at 07:55 (7 h 48 m 40 s). `IDENTITY-END` equals `IDENTITY-START`.
   - The main session read it in-session: **the count holds**; 0.2.26 is the nominal shipped version.
   - Merge `VERDICT PASS`: the first count on v21.
   - C2: PASS 3/3 (J-b.2 row 1).
   - §17.4: R spans 12/12 (2,258–2,263 ms).
   - Product-path reader: red once offline (P3 MISS, P2 MISS), then `SUMMARY` P1–P3 HIT.
   - Against 0.2.24's v20 reports: 0 cells worse.
   - Recorded, not attributed: Firefox C2's early keys are back inside the pre-v20 range.
   - §34.4 for the reading: 0 / 0. Already written up in the 10-17c addendum.
2. **Release text for 0.2.26** (`ff03403c`): `handoff/RELEASE-TEXT-0.2.25-0.2.26.md`, zh-TW (the stated exception to `handoff/**` English).
   - 0.2.25 is listed as void; 0.2.26 superseded it the same day.
   - Finding 153 is listed as known and unfixed (§4.1, the sentence its criterion 4 requires); item 2 is listed as withheld.
3. **The owner asked to be guided through the v22 link** (order C).
   - The link changes one engine variable: the default pthread stack (finding 153).
   - Item 2's re-enable, finding 152's fix and finding 154's page-side rule ride in the shell, after the link.
4. **Stack size measured without a relink** (`c56be2ed`; `findings/evidence/link-batch-v22/stack-size/README.md`).
   - Tool: `findings/evidence/link-batch-v21/shakedown/diag-long-paragraph/tool/diag_long_paragraph.py`, which gained the page family `v21stack<N>`: v21 with only the mirror loader's stack value changed.
   - Bisect, Chrome, N=1: 65,536 fails all four of finding 153's inputs; 131,072, 262,144, 524,288 and 1,048,576 pass all four.
   - Headroom (insertText, and open + type at the start, up to ~112-page paragraphs): ok at every size from 131,072. 65,536 hangs on the 28-page open + type.
   - Measured need: >64 KiB and ≤128 KiB, flat up to 112 pages.
5. **Ruling request 4 to fable** (`d7b7d392`; `findings/evidence/link-batch-v22/review/brief-fable-4-stack.md`). It asked two questions: the stack value, and `STACK_OVERFLOW_CHECK`.
6. **Fable ruling 4**, adopted (`ba41330a`; `findings/evidence/link-batch-v22/review/ruling-fable-4.md`).
   - Stack = **1,048,576**, on three legs:
     - the Writer measurement (item 4 above);
     - finding 089's Calc path, whose lowest passing rung is 256 KiB (128 KiB untried);
     - LO's own 1 MiB in `sal/osl/unx/thread.cxx`.
   - Memory: settled by arithmetic plus 089's thread counts (3 per ODT open, 7 per ODS; heap top ~277 MiB of the fixed 1 GiB). No new measurement is needed before the link.
   - `STACK_OVERFLOW_CHECK` is off in v22, as the named limit **L-153-no-overflow-check**. Level 1 never checks a thread that never returns. Level 2's cost is unmeasured, so a level-2 work item goes on the next diagnostic link.
   - **Nothing more to measure before the link.**
   - The brief had missed finding 089 and `SPEC-M3-link-batch.md` §11 (ruling item 18); the v22 spec must cite and close them.

## Next, in order

**The plan is ruling 4 §4, "What the main session must do next" (`review/ruling-fable-4.md`). Follow it, not this summary.**

1. **Append to `specs/SPEC-M3-link-batch.md` §11**: answered by v22 at 1,048,576 for every product link. Withdraw §12.6's Writer stack sweep (`:342`); `L-writer-stack-64k` can no longer be registered.
2. **Write `specs/SPEC-M3-link-batch-v22.md` and commit it before any v22 execution** (CLAUDE.md §9.1).
   - Scope: one engine variable.
   - Decision record: ruling items 1–11.
   - Criteria, each with its form and its default:
     - **C1**: 153's four inputs, N=3, both browsers.
     - **S1**: the `probe.js` literal; red first on v21.
     - **S2**: token diff against v21, expected 0.
     - **S3**: `make -n`, exactly one differing token; `configurationDrift: []`.
     - **I1-v22**: identity against v21.
     - **H1**: the six headroom cells, recorded.
   - Release-text consequences.
3. **Makefile `E2_V22_*` block**, its link carrying `1048576`. Whether to parametrize `link_r5_product` (`Makefile:841-856`) or add a v22 macro is decided by S3.
   - Archive v21 first. The 10-16 archive exists and verifies (State); decide in the spec whether it serves or a fresh copy is made.
   - Write `frozen-set-before.sha256` (v21's is at `findings/evidence/link-batch-v21/pre-link/`).
4. **Run S3 and the S1 red case; commit both witnesses.** S3's pair is `findings/evidence/link-batch-v22/pre-link/make-n-v22.txt` against `findings/evidence/link-batch-v21/part-e-red/make-n-v21.txt`.
5. **`handoff/RUNBOOK-relink-v22.md`** in `RUNBOOK-relink-v21.md`'s shape. Hand the owner **one short link line**. The link is the owner's.
6. **After the link**, in this order:
   - S1, S2, I1-v22 (static, same day);
   - C1 in both browsers, N=3, and H1 (the diag tool with a `v22` page; witness its identity block);
   - the shell items: item 2's re-enable, 152, 154's page rule and 154's host criteria;
   - freeze the shell;
   - the host version;
   - the count chain, per `release-count-batched`.
7. **Defaults** (ruling §4.7). If C1 is red at 1 MiB: stop and reopen the ruling. Do not move to 2 MiB without a measurement.

Alongside, owner-paced:
- the owner's hand test of 0.2.26 on the user path: Ctrl/Cmd+Home/End on a real document, then Backspace; and that no Markdown box covers the editor;
- the owner's reading of the release text.

## Hazards the next session must know

- **The merge runner's §34.1 freeze is lifted**: the 0.2.26 verdict has been read.
- **`dist/` is v21.**
- **Never pass `ALLOW_FROZEN_RELINK=1` for an older profile.** It is allowed only on the target being linked (`Makefile:1541`, `:1639`).
- **The link and any compiling `make` are the owner's** (global CLAUDE.md). Only if the owner explicitly says 「幫我建置」 may the session run it, and only after checking `uptime` and `pgrep -a make`.
- **Hand over short command lines.** Long pasted lines get cut.
- **The owner on the phone cannot run `!` commands.** A command the owner types in full is a request for the session to run it.
- Carried from 10-17c: re-judging 0.2.24's reports on the live tree reads NOT YET / NOT DONE (identity) by construction. Use the runners as of `a8b5ff33`.

## Not done / open

- Everything in "Next".
- Owner-side, not reported:
  - the hand test of 0.2.26;
  - the reading of the release text.
- Superseded by ruling 4, not edited (evidence):
  - `stack-size/README.md` §3's "[source: the platform default, not this tree]" (ruling item 20: the source is `thread.cxx:258-290`);
  - its "pthreads alive not counted" (item 18: 089 counted them on v12).
- Ruling 4's non-gating items:
  - the level-2 `STACK_OVERFLOW_CHECK` work item (item 11);
  - the live pthread count on v22, only with an instrument that touches no bound byte (item 7);
  - the post-link attribution run on archived v21 with `v21stack1048576`, only if a red needs it (item 17).
- Carried unchanged from 10-17c's "Not done / open".

## §34.4

- **Repaired because of execution: 0** in this stretch.
- **Repaired because of review: 0.**
- The page-honesty repair was counted in 10-17c.
- **Running total since 10-14b: execution 29, review 18.**
- **Not counted:**
  - the diag tool's `v21stack<N>` page family (a diagnostic);
  - the release text (documentation);
  - ruling 4 (a decision).
- **Ahead:** ruling 4 §4.4 says to count the S1 checker and the diag tool's `v22` page family as additions, not repairs.

## Subagents

- **Fable**, ruling 4, read-only (brief `d7b7d392`; ruling `ba41330a`).
  - Before adopting, the main session checked `libreoffice-26-8/sal/osl/unx/thread.cxx:278-284`, `findings/evidence/089/stack-arms-2026-10-13/README.md:29-45`, and `specs/SPEC-M3-link-batch.md:252-260` and `:340-343`. All agree.
  - The ruling corrected the brief in two places: finding 089 was omitted (item 18), and `link_r5_product` ends at `:856`, not `:857` (item 19).
