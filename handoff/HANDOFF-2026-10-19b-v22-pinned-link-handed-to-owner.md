# Handoff, 2026-10-19b: v22's criteria pinned, the Makefile block in, every pre-link gate green; the link is the owner's

This continues `HANDOFF-2026-10-19-count-holds-0226-v22-ruling-4.md` and covers commits `07df06f8..HEAD`. The main session is opus. The owner was present and asked to continue from that handoff and prepare the v22 link (「準備 v22 的連結」). It replaces 10-19 as the entry point; the memory index points here.

## State

| item | state |
|---|---|
| Nominal shipped version | 0.2.26 (unchanged) |
| Shell / engine in `dist/` | v74 / `e2-editor-v21` (unchanged) |
| v22 spec | `specs/SPEC-M3-link-batch-v22.md`, **criteria pinned at `937bc684`**. Append-only from here |
| v22 Makefile block | In (`1f64160f`): `link_product_stack_1m` (one token: `-sDEFAULT_PTHREAD_STACK_SIZE=1048576`) and the `E2_V22_*` block (v21's rules under v22's names) |
| Pre-link gates | All green: S3 (a) and (b), S1-red, M1-1 red then green, `test-e2-c-static` exit 0, frozen set 1,370 files (`findings/evidence/link-batch-v22/pre-link/README.md`) |
| Runbook | `handoff/RUNBOOK-relink-v22.md` |
| The link | **Handed to the owner, not run** (as of this handoff's commit). §0 item 8 re-run at 10:36: `find` printed 0, no make running, v21 archive 5/5 |

## What happened

1. **Ruling 4 §4.1:** `SPEC-M3-link-batch.md` §11 answered by v22 (1,048,576 for every product link from v22).
   - The Writer stack sweep (§12.6 and its procedure §15.4) is withdrawn; `L-writer-stack-64k` can no longer be registered.
   - Additions only (12 lines). Findings 089 and 153 got dated appends.
2. **Ruling 4 §4.2: the v22 spec**, committed before any v22 execution (`937bc684`).
   - Scope: one engine variable. No v22 define; v21's source (`5f5bf11c`), defines, worker, packs and builder flags.
   - Decision record = ruling items 1–11.
   - Criteria: S3, S1-red, S1, S2 (recorded), I1-v22, C1, H1 (recorded), K.
   - Two things the ruling did not spell out, written into the spec before any run:
     - **C1 has a positive control**: `sdk-md:cjk:65536:v21` once per browser must NOT be `ok`, or C1 is NE.
     - **I1-v22 has one pre-declared reading.** X1's wasm clause treats an equal wasm as "the fix is not in it". v22's value lives only in the loader (the `libpthread.js` template). So a wasm byte-equal to v21's fails X1 only on that clause, and then reads as: every other clause holds and S1 passes.
3. **Ruling 4 §4.3, "parametrize or a new macro: S3 decides".**
   - Both give the same v22 `make -n`.
   - A parameter would change the text that 22 existing callers expand from, which would need its own witness. A new macro leaves them byte-unchanged.
   - So: a new macro, and S3 measures the copy (spec §4.1).
4. **Ruling 4 §4.4: S3 and S1-red run and committed** (`1f64160f`).
   - S3 (a): exactly three changed lines, as the closed list says.
   - S1's positive control hashes to `dc4c2c84…`, the loader the diag tool served as `v21stack1048576`.
5. **Caught before any run:** the mechanical `E2_V21` → `E2_V22` rename also renamed `-DOXSDK_E2_V21_LINK_BATCH` in the v22 compile rule.
   - That would have linked v22 without v21's engine code (Ctrl+Home/End, Markdown).
   - Seen in the Makefile diff and restored before S3. S3 would also have shown it.

## Next, in order

1. **The owner links** (`RUNBOOK-relink-v22.md` §2, three short lines). If time has passed since 10:36, re-run §0 item 8 (`find … -newer` must print 0) before they do.
2. **Same day, the main session:** runbook §3 items 1–8:
   - the frozen set;
   - S1;
   - I1-v22 (X1);
   - `ScDocShell` 0;
   - E1-C;
   - S2;
   - archive v22;
   - commit `post-link/`.
3. **Then spec §7 steps 2–7:**
   - the diag tool's `v22` page family;
   - C1 (both browsers, N=3, the positive control) and H1;
   - the shell items (criteria appended first);
   - freeze the shell;
   - the host version (ask first);
   - `BINDING`;
   - the count chain.

Owner-paced, carried:
- the hand test of 0.2.26 on the user path;
- the reading of the release text.

## Hazards

- **Never pass `ALLOW_FROZEN_RELINK=1` for v8, v15, v18, v19, v20 or v21.** Since the Makefile changed, make sees every older target as out of date (finding 042).
- **The link and any compiling `make` are the owner's.** If the owner says 「幫我建置」, check `uptime` and `pgrep -a make` first.
- **`dist/` is v21** until the shell is repointed (spec §7 step 3). `e2/expected-gesture-offers.json` still names v21; it moves with the shell.
- **A v22 that X1 calls FAIL on the wasm clause alone is not automatically red.** Read spec §5.2.
- **In this session a `cd …&&` at the head of a Bash call did not take effect** once, when two calls ran in parallel, so a relative path missed. Use absolute paths for writes.

## §34.4

- Repaired because of execution: **0**. Repaired because of review: **0**.
- Additions, not repairs (ruling 4 §4.4):
  - the S1 checker;
  - the `what_the_link_ships` variant (data);
  - the M1-1 carrier line;
  - the new link macro.
- Running total since 10-14b: execution 29, review 18 (unchanged).

## Addendum, 2026-10-19 (after the link)

- **The owner linked v22** at 10:39–10:42 (runbook §2, no error). The main session did runbook §3 the same day (`3ba23e05`; `findings/evidence/link-batch-v22/post-link/README.md`; spec §10):
  - the frozen set holds;
  - S1 PASS;
  - S2 0: the loader is v21's with the one literal changed;
  - I1-v22 PASS (X1 default mode; the equal-wasm reading was not needed);
  - `ScDocShell` 0; E1-C intact.
- **Archived** at `wasm_sdk_probe/build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/`. Hashes:
  - wasm `f7a40bcc…`;
  - loader `dc4c2c84…`;
  - manifest `000921c1…`;
  - worker `0d55bcfa…`.
- **Recorded:** the wasm differs from v21's in one function of 149,474, and only `probe_engine.o` differs among the objects (finding 036's shape). The stack value is in no differing byte.
- **Next:** spec §7 step 2.
  - Add the diag tool's `v22` page family (an addition): v21's page-family mirror with the page pointed at `e2-editor-v22`, and an identity block that records the served `probe.js` hash.
  - Commit the identity witness.
  - Then run C1: four cells, `--repeat 3`, Chrome and Firefox, plus `sdk-md:cjk:65536:v21` once per browser as the positive control.
  - Then H1.
- **v22 is unbound.** `dist/`'s page still points at v21.
