# Runbook: the v22 link — the engine thread's default pthread stack, 1 MiB (finding 153) (**the link command is the owner's to run**)

Written 2026-10-19. It follows [`RUNBOOK-relink-v21.md`](RUNBOOK-relink-v21.md) and rests on:

- `specs/SPEC-M3-link-batch-v22.md`, criteria pinned at `937bc684`. §5 is the criteria table.
- Fable ruling 4 (`findings/evidence/link-batch-v22/review/ruling-fable-4.md`, `ba41330a`).
- The Makefile block and the pre-link gates: `1f64160f` (`findings/evidence/link-batch-v22/pre-link/README.md`).

A link mints a new identity. v21 keeps its own build and dist directories and its archive, so it stays as it is. v22 binds nothing until its `BINDING` commit, which comes after the link, C1 and the shell items.

## What this link ships

- **Engine:** v21's source (the tree v21 was linked from, `5f5bf11c`; no code change since) with v21's defines, compiled again into `build/e2/editor-v22/`.
- **One changed link flag:** `-sDEFAULT_PTHREAD_STACK_SIZE=1048576` (was `65536`), through the new macro `link_product_stack_1m`. Everything else on the link line is v21's. `STACK_OVERFLOW_CHECK` stays 0 (`L-153-no-overflow-check`).
- **Worker:** v21's, sha256 `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`. The recipe refuses any other bytes.
- **Export list and packing:** v21's (the v5 builder with `--inline-range-gestures all --page-rectangles --paste-markdown`), profile `e2-editor-v22`, editor ABI 5.
- **Not in the profile:** the shell items (item 2's entry, finding 152, finding 154's page rule). They come after the link.

## 0. Gates before the link (state on 2026-10-19)

1. ✅ **Criteria pinned before any v22 execution:** `937bc684`.
2. ✅ **S3 (a)**: `make -n` of the v22 manifest target, read as v21, differs from v21's witness in exactly three lines: the link line's one token, the worker pin, the guard text (`pre-link/s3-word-diff.txt`).
3. ✅ **S3 (b)**: `what_the_link_ships.py --since 5f5bf11c --variant link-batch-v22`: `ok: true`, `configurationDrift: []`, four units identical, worker identical.
4. ✅ **S1-red**: `tools/check_pthread_stack_literal.py` is red on v21's `probe.js` and on an anchor-twice copy, green on the positive control (`pre-link/s1-red-first.txt`).
5. ✅ **M1-1**: red without the `E2_V22` carrier (on exactly its three objects), green with it.
6. ✅ **`make -k test-e2-c-static`**: exit 0 after the Makefile change.
7. ✅ **v21 is archived** at `build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/`: `sha256sum -c` 5/5 OK, the four files equal `dist/`.
8. ✅ **The core link inputs** are not newer than v21's link: the `find … -newer build/e2/editor-v21/probe.wasm` from RUNBOOK-relink-v21 §2 printed `0`. **The main session runs it again right before handing you §2**, and tells you what it printed.
9. ✅ **The frozen set before the link**: `findings/evidence/link-batch-v22/pre-link/frozen-set-before.sha256`, 1,370 files under `dist/profiles/` and `build/archive/`.

## 1. Do not run any other make target

The Makefile changed, and every rule lists it as a prerequisite (finding 042). So make now treats **every** older profile target as out of date. Nothing in them changed.

- Their links refuse without `ALLOW_FROZEN_RELINK=1`.
- **Never pass that flag for v8, v15, v18, v19, v20 or v21.**

## 2. The link (**the owner's step**)

Three short lines, in your own terminal:

```
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v22/sdk-manifest.json 2>&1 | tee build/link-v22.log
```

- **`ALLOW_FROZEN_RELINK=1` on this one target only.** The v22 rule is guarded from its first link, like v21's.
- **What it does:**
  1. Compiles `build/e2/editor-v22/{sdk_api,probe_engine,unoembind_stub,editor_api}.o` with v21's compile line.
  2. Regenerates `build/r5/writer-review/exports.txt` (a text file, not frozen).
  3. Writes `build/e2/editor-v22/exports.txt`, then links `build/e2/editor-v22/probe.{js,wasm}`.
  4. Checks the worker pin (`sha256sum -c` against `0d55bcfa…`) and the packs.
  5. Packs `dist/profiles/e2-editor-v22/` with the v5 builder.
- **Expected time:** v21's same four compiles and link took about three minutes (22:22–22:25 on 10-16). Allow 10 minutes. It runs one job at a time (no `-j`).
- **If it stops with an error, stop there** and tell the main session. Do not re-run with other flags.

## 3. Right after the link

**Send back only "done"** (or "failed"). The main session reads `build/link-v22.log` and computes every hash itself, in this order, the same day:

1. **The frozen set** (I1-v22): `sha256sum -c --quiet` over `pre-link/frozen-set-before.sha256` prints nothing, and `find dist/profiles build/archive -type f` lists no new file outside `dist/profiles/e2-editor-v22/`. If either fails, stop. Nothing else runs.
2. **S1:** `python3 tools/check_pthread_stack_literal.py dist/profiles/e2-editor-v22/probe.js build/e2/editor-v22/probe.js` prints `VERDICT PASS`.
3. **I1-v22, X1 in its default mode** (no declared flags):

   ```
   python3 tools/check_profile_identity.py --candidate dist/profiles/e2-editor-v22 \
       --reference dist/profiles/e2-editor-v21 \
       --candidate-exports build/e2/editor-v22/exports.txt \
       --reference-exports build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/exports.txt
   ```

   Expected `VERDICT PASS`, exit 0. The one reading written beforehand (spec §5.2): if X1 fails **only** because v22's `probe.wasm` is byte-equal to v21's, I1-v22 holds if every other clause holds and S1 passes. The value lives only in the loader.
4. **Writer only:** `grep -a -o ScDocShell dist/profiles/e2-editor-v22/probe.wasm | wc -l` prints `0`.
5. **E1-C:** `python3 tools/check_e1_c_bundle_intact.py` gives `"intact": true`.
6. **S2 (recorded):** v22's `probe.js` with the S1 literal set back to 65536 once, `cmp` against v21's. Expected equal. If not, the token diff is appended to the spec.
7. **Archive at once** into `build/archive/e2-editor-v22-<wasm sha8>-worker-0d55bcfa/`: `probe.wasm`, `probe.js`, `sdk-worker.js`, `sdk-manifest.json`, `exports.txt`, `SHA256SUMS`, `ATTRIBUTION.md`. Finding 036: the wasm is not a function of the source.
8. Commit the witnesses under `findings/evidence/link-batch-v22/post-link/`.

## 4. After that (the main session)

Spec §7 steps 2–7:

1. **The diag tool's `v22` page family** (an addition; its identity block records the served `probe.js` hash).
2. **C1**: finding 153's four inputs, N=3, Chrome and Firefox, plus the positive control on v21. **H1** (recorded): six headroom cells, Chrome, N=1.
   - If C1 is red at 1 MiB: stop and reopen ruling 4 with the reports. Do not move to 2 MiB without a measurement.
3. **The shell items:** item 2's re-enable, 152, 154's page rule and 154's host criteria. Their criteria are appended before they run.
4. **Freeze the shell.**
5. **The host version:** ask the owner before installing.
6. **`BINDING`** for v22, in its own commit.
7. **The count chain** (`release-count-batched`), in the owner's window, detached from the session.
