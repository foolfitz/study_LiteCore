# Handoff, 2026-10-20b: v23 ordered commands — native C-HOLDS and N1-HOLDS, spec pinned; host 0.2.28 prepared, not installed

**First line: ddev still runs host 0.2.27 (unchanged). Host 0.2.28 (finding 155) is prepared but not installed: it waits for a window the owner names in his own words. For v23, candidate C (unipoll) holds natively, the spec is pinned (`b9080313`), and N1 holds. Nothing is linked yet.**

This continues `HANDOFF-2026-10-20-v22-host-0227-installed-all-arms-pass.md`. That handoff stays valid for the v22 and 0.2.27 items: the owner's hand tests, the release text and K. This one covers `b26b230d..0ecec9a0`. The main session was opus.

## Authority this stretch

- At about 06:10 on 2026-10-20, the owner could not hand-test, and asked the session to continue from the 10-20 handoff. Ruling 7's plain section was relayed to the owner in the conversation.
- The owner chose **"A+B"**:
  - **B**: prepare host 0.2.28 (finding 155) without installing it (「安裝等你給時段」);
  - **A**: start the preliminary work for the ordered-commands batch (engine v23): native measurement, the spec with its criteria first, and review. No link and no ddev.
- The owner then said 「我不在座位，請自主執行任務，另外我授權給fable 代我做決策」. This is the 12th delegation (memory `away-owner-delegates-decisions-to-fable`).
- No build authorization this round. Nothing was pushed or deleted. The only ddev command was a read-only `ddev list` at 06:43.
- **The rulings.** One fable subagent, id `a97ca80a963dc123a`, continued via SendMessage, gave two:
  - ruling 1 (`findings/evidence/link-batch-v23/review/ruling-fable-1.md`, `cca06f7a`);
  - addendum 1 (`ruling-fable-1-addendum-1.md`, `3b93c7e2`).

  Both were committed verbatim, with the main session's source check appended.
- **Not yet relayed to the owner:** ruling 1 §1 and addendum 1 §1, the plain-language sections. Next 1.

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.26** (count `efb8ae77`). Unchanged |
| Host on ddev | **0.2.27**, buildId `817413d5ad5bd502`, host commit `d7c0a5e`. Unchanged |
| Host 0.2.28 | **Prepared, not installed** (`b6a8379f`, `a6bb3b29`). It is the patch, criterion H-155 with its red cases, and the chain. It waits for the owner's window (ruling 1 §2.9) |
| Engine | v22, `e2-editor-v22`. Unchanged. v23 is not linked |
| v23 plan | `handoff/PLAN-2026-10-20-ordered-commands-v23.md` (`44ce9115`): 18 deferred items. §7 records ruling 1 |
| v23 spec | `specs/SPEC-M3-ordered-commands.md` (zh-TW). Drafted in `b943adb4`, **PINNED** in `b9080313`. Append-only from then |
| Native arms (C) | **VERDICT C-HOLDS**, N=5 (`24c5b635`) |
| N1 (spec §9.1) | **VERDICT N1-HOLDS**, N=5 (`0ecec9a0`) |
| Model, M1/M2 (spec §8) | Not started |
| Finding 156 | Registered (`24c5b635`). Not sent |

## What happened (in order)

1. **B: host 0.2.28** (`b6a8379f`, `a6bb3b29`; `findings/evidence/host-0.2.28/README.md`):
   - v22 spec §14 was appended (`specs/SPEC-M3-link-batch-v22.md`). The change is host-only: the rule `#litecore-editor-root dialog[open] { margin: auto; }` and info.xml 0.2.27 → 0.2.28. The engine package `817413d5ad5bd502` is unchanged.
   - The patch is `host-0.2.28.patch`. `git apply --check` passed against host `d7c0a5e`.
   - The README has the restore and install steps.
   - `chain-h155.sh` needs `WINDOW_END='YYYY-MM-DD HH:MM'`.
   - A reduced repro is in `findings/evidence/155/precheck/`. In both browsers the open dialog sits at `[0, 0, …]` without the rule, and the centre offset is `[0, 0]` with it.
   - **H-155** (centre offset ≤ 16 px) was added to `findings/evidence/154/diag_markdown_dialog_on_host.py` behind `--require-h155`. The self-test passes 16/16, and H-155 reads red on 0.2.27's reports.
   - Ruling 1 §2.9: **not installed now.**
2. **Census and facts** (`44ce9115`):
   - An Explore subagent found 18 items deferred to "ordered commands", listed in the PLAN.
   - The facts sheet is `handoff/link-batch-v23/facts-lok-command-ordering.md`. It covers:
     - accelerator keys take two hops in threaded LOK (`AsyncAccelExec`), and printable characters take one;
     - the listener forces `postUnoCommand(…, true)` to run SYNCHRON;
     - finding 142's native reorder;
     - Collabora's WASM runs unipoll.
3. **Ruling 1** (brief `9613bfea`, ruling `cca06f7a`):
   - Scope: PLAN §4 A (tiers 1 and 2).
   - Candidate C (unipoll) is measured first, natively.
   - A′ and B-as-stated are withdrawn.
   - A is not a fallback. The undo proof makes completion independent of the hop count, but order still depends on it. The main session's lean on this was wrong.
   - B″ (quiescence) is the fallback.
   - Ruling 4's "C constrained by 040" is struck.
   - 0.2.28 is not installed.
4. **Native arms** (`8e7f4b08` harness and smoke; `24c5b635` counted N=5). They are in `findings/evidence/link-batch-v23/native/ordered-commands/`:
   - files: harness `tool/oc_native.cpp`, runner `run_arms.py`, readers `read_results.py` and `read_n1.py`, the fixtures, and `smoke/` and `smoke-n1/` with `NOTES.md`;
   - modes: seq (the Writer order, measured), q (threaded queued, the control) and unipoll;
   - **VERDICT C-HOLDS:**
     - d1, d2, d2p, d3, d4, d5 and d6 under unipoll equal seq 5/5, and q reorders 5/5;
     - D8 holds;
     - D7, the undo top at return: (i) `Number On/Off`, (ii) `Number On/Off`, (iii) `Apply attributes`, plain none;
     - 165 processes, all exit 0.
   - **Two native-only workarounds** were needed. Both came from smoke crashes and were read in the source:
     - skip `runLoop`. Upstream `caa4036188ed` makes `ImplSVMain` return early when VCL is initialised, and natively `soffice_main`'s stack Desktop is destroyed;
     - call `SfxApplication::GetOrCreate()`, as iOS's LOK init does.
   - **d7i's placement was corrected before the counted run**, to review 6's position (i): one unshifted Left at the document start, which puts the caret in front of the label (`smoke/NOTES.md`).
5. **Finding 156** (`findings/156-lok-unipoll-runloop-no-longer-runs-the-application.md`, `findings/evidence/156/`, `24c5b635`):
   - LOK unipoll's `lo_runLoop` returns at once (0.02–0.03 ms, 0 polls) since `caa4036188ed`. A native `documentLoad` after it then crashes with SIGSEGV.
   - It is not fixed on origin/master as of 2026-10-11. Collabora's co-26.04 core has the old `ImplSVMain`.
   - Not sent: upstream submissions are on hold.
   - There is no positive control, because no native build from before `caa4036` exists.
6. **Inventory** (`ee0f167e`): `handoff/link-batch-v23/facts-async-key-machinery.md`. It lists:
   - A1–A13, the machinery built for asynchronous keys;
   - the consumers of the completion vocabulary;
   - the ABI: 5 under V21, `kMaxInternalEditorAction` 25.
7. **Addendum 1** (spec draft and brief `b943adb4`; addendum `3b93c7e2`):
   - The counted 096 check is unchanged. B2 must appear in `clausesExercised` on every v23 run, or the product is red.
   - Barrier K1 is withdrawn. Caret deletes send the user's own key.
   - **Every completion name stays, including `verified-move-readback`.** The main session's draft said that name would disappear; that was wrong. The frozen client's `MOVE_COMPLETIONS` accepts only `documented-callback-*` and `verified-move-readback`.
   - One command per poll, with the reply at the next poll. `anyInput` = a command is queued ∨ a reply is pending. The poll does not block on WASM.
   - No new 5 s watchdog. The SDK's 30 s stands.
   - N1 is split into N1a, N1b and N1c.
   - `STACK_OVERFLOW_CHECK=2` goes on the v23 diagnostic link only.
   - Finding 156's consequence: `Desktop::Main` does not run under C. The check is §9.2 S-init.
8. **Spec pinned** (`b9080313`). The draft was `b943adb4`.
9. **N1** (`7b4e2f1f`: the tools and the smoke; `0ecec9a0`: counted N=5, 70 processes, all exit 0). **VERDICT N1-HOLDS:**
   - **N1a PASS:** 12 arms × 5, with no late reply-type callback;
   - **N1b** (a record): `STATE_CHANGED` n=253, 0.5–622 ms late; the rulers 459–762 ms late; the tleave control is present;
   - **N1c PASS:** uni1 takes 1.18–1.26 ms and uni1ai 0.08–0.11 ms. The native effect is about 1 ms; on WASM it is inferred to be about 10 ms per task.

## Next (spec §10)

1. **Tell the owner, in zh-TW, ruling 1 §1 and addendum 1 §1.** Ask the owner for 0.2.28's window. The chain is ready, and only the owner can name the window.
2. **The model in two modes** (spec §8; `wasm_sdk_probe/tests/extend_completion_model_test.cpp`). It is a host g++ build of about 12 s and reads no files, so this absolute-path form is equivalent to `cd wasm_sdk_probe && …`:
   ```
   W=/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
   g++ -std=c++17 -O2 -I$W/src -o $W/build/extend_completion_model_test $W/tests/extend_completion_model_test.cpp && $W/build/extend_completion_model_test
   ```
   - **Threaded mode** must still print 27,744 / 2,448 / 5,474 / 3,868. If it does not, stop.
   - **A new synchronous-key mode (C)**: keys apply at dispatch, one command per poll, flush before the next decision, and caret deletes are the user's own key. It must print 0 Writer-divergent for every shape, including condition 33's two, and the forged-completion class must be empty.
   - Not started. Do not run it while a timing measurement runs.
3. **Two-seat review**: opus plus `codex exec -s read-only < /dev/null`. The codex MCP failed to connect this session. The review covers:
   - the three fixed questions (spec §7);
   - addendum §2.2's vocabulary table and §2.3's `anyInput` rule;
   - the one-time two-seat review of `read_results.py` and `read_n1.py` before their first counted use (§34; spec §12).
4. **The diagnostic-profile engine code** (spec §9.2), red cases first:
   - the loop wiring;
   - one command per poll;
   - `anyInput` with the pending-reply term;
   - the non-blocking poll;
   - `-sSTACK_OVERFLOW_CHECK=2`.

   **The owner links it**, because a compiling make is the owner's. Then the §9.2 cells run.
5. **Later**, in order:
   - the feature profile (§9.3);
   - host 0.2.29;
   - K, the count, in the owner's window, after asking first.

## Hazards

- **ddev still runs 0.2.27.** 0.2.28 is prepared and **not installed**. Installing needs the owner's own words naming a window (ruling 1 §2.9).
  - Until then, do not apply `host-0.2.28.patch` to the live host repo. Its templates are served live.
- **`SPEC-M3-ordered-commands` is pinned** (`b9080313`) and append-only. Any new criterion needs the four conditions in CLAUDE.md §9.
- **Native measurements:**
  - never overlap two runs. N1c works at the millisecond scale.
  - The harness binary was built into the session scratchpad and is lost after the session. Rebuild it with the line in `findings/evidence/link-batch-v23/native/ordered-commands/smoke-n1/build.txt`, with its relative paths made absolute.
  - The counted C-HOLDS run used the binary from `smoke/build.txt`, sha `719d6ac9…`. N1 used the one from `smoke-n1/build.txt`, `3fda8963…`.
- **Never `cd` into a directory in shell commands**, especially `REPO/libreoffice-26-8`, which is a git worktree of LO core. The harness then treats that directory as the primary working directory. Use absolute paths.
- **Unchanged from 10-20:**
  - run the desk gate before timing steps;
  - `m11_autosave.py` leaves its scratch under `--out`;
  - commit attribution is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, with no `Claude-Session:` line;
  - never pass `ALLOW_FROZEN_RELINK=1`.

## §34.4

- **This stretch:** repaired because of execution **0**, because of review **0**.
- **Additions (0/0):**
  - the H-155 key and its flag;
  - `oc_native.cpp`, `run_arms.py`, `read_results.py` and `read_n1.py`. These are new tools, and their one-time two-seat review is pending (Next 3);
  - the native workarounds (diagnostic).
- d7i's placement was changed before any counted run, so it is not a repair (`smoke/NOTES.md`).
- **Running total since 10-14b: 32 / 18** (unchanged).

## Accumulated uncounted changes

As the 10-20 handoff lists. Nothing in this stretch has shipped: 0.2.28 is not installed and v23 is not linked.

## Registered work items (not gates)

- **New:**
  - finding 156 needs a positive control: a native build from before `caa4036188ed`, which is the owner's make. It also needs a Bugzilla duplicate search when submissions resume;
  - on WASM, find what triggers the creation of `SfxApplication` before the first open (spec §5.1). §9.2 S-init checks it.
- **Carried unchanged:** the 10-20 handoff's registered list.
