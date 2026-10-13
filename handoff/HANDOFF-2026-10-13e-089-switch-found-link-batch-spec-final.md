# Handoff, 2026-10-13e — finding 089's switch is the 64 KB pthread stack; the link-batch spec is FINAL (§10–§12); no product byte changed

This round starts from Addendum 2 of `HANDOFF-2026-10-13d-136-fixed-0.2.18-uncounted-candidate.md`: the owner chose C (two parallel tracks). Track 1 is the link batch (Shift+Arrow, moves on a range, the page number, C, the two engine items from 136, and the full count of 127–136); its first step is the spec. Track 2 is ODS preparation that touches no product bytes and needs no link (finding 089's cause, W6, a W9 draft). Both ran in this session, 2026-10-13 17:36–20:14 +0800, 37 commits `8b9ca181..c6edfd37`. Result: **Track 2** found 089's switch (the default pthread stack, 64 KB), finished W6 and drafted W9. **Track 1** went through native measurement, a draft spec, two adversarial reviews and two fable rulings, and `specs/SPEC-M3-link-batch.md` is now FINAL after §12 (no third spec round). Authority: the owner said 「有疑義的發給fable，我授權它代我下決定」, so fable ruled on the doubts (three rulings, listed below). The owner also pointed to the Collabora source for inspiration (「需要靈感的話可以參考 collabora source code」); the 089 stack hypothesis (H-S) came from `cool-26-04/engine/solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk:25`, and the page-number design was checked against Collabora's source. The drafter was told this session is not bound by the token soft limit (the repo holds no record of the wording). **No product byte changed**: nothing in the range is under `src/`, `dist/`, `e2/`, or the five bundle-scoped directories; the bundle digest re-read by the W9 task is still `70c34178…` (v66). The uncounted candidate is still 0.2.18.

One commit landed after `c6edfd37` while this handoff was drafted: `c163fd0a`, the task brief for Next 1 below (`handoff/tasks/TASK-2026-10-13j-extend-rule-header-and-model-test.md`). It is not one of the 37. Whether an executor has run it is not recorded here: check `git log -- wasm_sdk_probe/src/extend_completion.hpp findings/evidence/link-batch/extend-model/`.

## Commits (`8b9ca181..c6edfd37`, oldest first within each group)

### Track 2 — ODS: finding 089 (16)

| commit | what |
|---|---|
| `b028cbc6` | `probe_ods_on_profile.py --engine-env NAME=VALUE`: sets an engine environment variable in the scratch mirror's `probe.js`; the engine echoes it from preRun. A case without the echo is void. |
| `47440469` | `TASK-2026-10-13f`, written before any run: is the cliff Calc's threaded formula-group path? |
| `3b7f1dce` | E0 control run stopped at the echo gate (0 of 7 cases echoed the ENV). E0-r1 is void. |
| `88472109` | Cause of the void: the probe page attached its listener after `createDocumentEngine()` resolved, so preRun's echo had no listener. Fix: `ods-decisive-probe-app.js` attaches the listener before `_initialize()`. Task Amendment 1. E0-r1 stays as the red case. |
| `8d26c32f` | E0-r2 passes the echo gate; E1 ×3 (`SC_NO_THREADED_CALCULATION=1`), E2 (`SC_FORCE_CALCULATION=core`), E3 ×3 (`threads`): rows36 and index35×36 still time out. |
| `abfa4c67` | Finding 089 appended: outcome **O-N**, the timeout is not in Calc's formula-group calculation. Registers NU-089-3. |
| `53044890` | Task Amendment 2 (written before the run): E4 `SAX_DISABLE_THREADS=1`, E5 `MAX_CONCURRENCY=1`. |
| `831fea32` | E4, E5 run once each: still time out → **O-N2**. |
| `7eb74ac6` | Finding 089 appended: all four env-switchable thread users are not the switch. |
| `c7fe9ec7` | Brief for fable ruling 1: which way after six env switches are refuted. |
| `90fed9b7` | `probe_ods_on_profile.py --pthread-stack-size N` (multiple of 16): replaces the anchored literal `,!ENVIRONMENT_IS_WEB,65536,false);` in the mirror's `probe.js` (must occur exactly once or the tool refuses); every started pthread echoes the size it got. No link. |
| `c6e10b21` | **Fable ruling 1** (`findings/evidence/089/ruling/ruling-1.md`): run the stack arm (H-S) first, the `Debugger.pause` probe (A) only if it fails, no names-carrying build now. |
| `fca34a61` | Finding 089: ruling paragraph; also `redcase-anchor-count.txt` (anchor occurring twice → refused). |
| `4fc2673b` | Task Amendment 3: the H-S protocol, written before any resized run. |
| `34ac5a83` | Stack arms S0–S4 and ladder L: outcome **O-S**. 25 files under `findings/evidence/089/stack-arms-2026-10-13/`. |
| `4aa84ec2` | Finding 089 appended: O-S. "Cause unidentified" is withdrawn and replaced by "switch = 64 KB pthread stack; overflowing function not identified". |

### Track 2 — ODS: W6 and W9 (7)

| commit | what |
|---|---|
| `7e3a8d74` | **W6.** `check_core_build_provides.py` gains a `calc-spreadsheet` capability (four switches: Make variable `ENABLE_WASM_STRIP_CALC`, five `libsclo.a` objects, `-lsclo` in link deps, `services.rdb` registration plus the static constructor map). Self-test 22/22 (was 5/5); four switches red on writer-only, green on writer+calc and native; exit codes with no flag unchanged for all three builds. |
| `ca099937` | ODS plan amendment: W6 done, main session re-ran the self-test 22/22. Names a latent hazard in `probe_a11y_gate0.py` and a cutover trap (see Named limits). |
| `8a8d7f8b` | `TASK-2026-10-13i`: W9 read-only ODS viewer draft, source only. |
| `28daa47e` | **W9 draft.** New files only: `viewer-shell/{ods-viewer-session,w7-adapter,viewer-error}.js`, `web/ods-viewer{.html,-app.js}`, a node test (18/18), a smoke runner, and a red-case harness (27 mutations, each turns the test red). |
| `e4d572aa` | `.gitignore`: allowlist gains `wasm_sdk_probe/viewer-shell`. |
| `37acc397` | W9: one guarded Chrome smoke on `e2-editor-v14`, 13/13 expectations met, diagnostic only; README; wait log. |
| `4476ea55` | ODS plan amendment: W9 exists as a draft in source. |

### Both tracks (2)

| commit | what |
|---|---|
| `e33686f8` | Tasks `10-13g` (W6) and `10-13h` (native extend signatures), written before they ran. |
| `edf3d643` | Registers 089's product consequence: spec §11 (should the link raise the pthread default stack? default: no) and an ODS plan amendment (W8 must carry a stack above 64 KB or `tdf149752.ods` fails G2). |

### Track 1 — link batch (12)

| commit | what |
|---|---|
| `81eaf66d` | **Native step** (`TASK-2026-10-13h`): LOK callbacks after Shift+key and after plain keys on a range; 3 rounds, 111 cells, 27 interaction arms. Tool `link_native_extend_signatures.cpp`, analyser, fixture, evidence under `findings/evidence/link-batch/extend-signatures/`. |
| `aecf926b` | Draft `specs/SPEC-M3-link-batch.md` (unreviewed): scope, current state, design, criteria S1–S4/R1/P1–P3/C1/E1–E3/K, open questions Q-A–Q-D. |
| `b5f2e812` | Spec §9: completion condition for 4.1 fixed from the native run. **Superseded by §10.1.** |
| `ca48673a` | Brief for review 1 (opus, adversarial, §34: attack the product and the criteria only). |
| `cf0e15d2` | **Review 1**: 3 BLOCKING, 12 SHOULD, 11 NOTE. |
| `93b8df21` | Brief for ruling 2 (dispositions of review 1). |
| `918c2497` | **Fable ruling 2** (`findings/evidence/link-batch/review/ruling-2.md`, conditions 1–15). |
| `66e39525` | Spec §10 written from ruling 2. |
| `acf4f268` | Brief for review 3: one bounded round, §10 only, five fixed questions, no further round. |
| `6370916e` | **Review 3**: Q1, Q2, Q4, Q5 counterexample; Q3 SHOULD. |
| `1b38f6c0` | **Fable ruling 3** (`ruling-3.md`, conditions 16–28). |
| `c6edfd37` | Spec §12 written from ruling 3. Spec review ends here. |

## State

| item | state |
|---|---|
| Uncounted candidate | Unchanged: **0.2.18** (page `b24d754a…`, shell v66 `70c34178…`, host `96a87d8`, buildId `d6d04880f56e31da`). The nominal shipped release is still 0.2.12. |
| Count | Still batched with the next engine-changing release (SPEC-M3-autosave §9.21). That release is this link batch: it carries 127–136 plus the batch's own criteria. |
| Finding 089 | **O-S.** On `e2-editor-v12`, patching only the default pthread stack in the mirror's `probe.js` (no link): at 262144, 1048576 and 8388608 bytes, rows36 and index35×36 open 3/3 each, and the neighbouring crashes (rows35, index36×35) are 0 in all 9 runs. At 32768 all six spreadsheets fail (S4, passed its boot gate). At 262144 the rows37–40, rows50 ladder and the corpus's original `tdf149752.ods` all open (1.0–1.6 s). Every pthread echoed the requested size in every stack-arm report. Allowed statement (ruling 1, condition 9): the 64 KB default pthread stack is the switch, mechanism "stack overflow on an artifact with no overflow check"; the overflowing function is **not** identified. Arm A (`Debugger.pause`) was not run and no names-carrying build is requested. Fable corrected three claims of the drafter: `65536` occurs 6 times in `probe.js` (not once); the "config listener" reading of NU-089-3 does not hold for E1; "269 ms" is the m4 oracle number for the original file, the native ladder gives about 1.4 s for the stuck fixtures. |
| W8 obligation (ODS plan amendment `edf3d643`) | The writer+calc relink must carry a default pthread stack above 64 KB, or an explicit engine-thread stack, or `tdf149752.ods` fails G2. Measured floor: 256 KB works, 64 KB does not; values in between are untested. The size is the owner's decision at that link. Not established: which function overflows; whether other corpus entries are stack-limited (the 306-entry sweep ran at 64 KB; re-running it is W5's job on the new candidate). |
| Instrument flags | `wasm_sdk_probe/tools/probe_ods_on_profile.py`: `--engine-env NAME=VALUE` (`b028cbc6`), `--pthread-stack-size N` (`90fed9b7`). Both patch the scratch mirror only; a case with no echo is void. |
| W6 | Done (`7e3a8d74`, plan amendment `ca099937`). `PRODUCT_CORE_BUILD` is not repointed. |
| W9 | Draft done, source only, not staged to `dist/`, not bound by any gate; `evidenceClass` stays `diagnostic` while the pre-W7 adapter stands in. The adapter holds everything W7 is missing: `.odt` name spoof, `documentType` `"unknown (pre-W7)"`, generated sheet names, `PART_SWITCH_UNAVAILABLE`, `currentPartReadBack: null`. W7 (engine/worker/SDK: `documentType`, `partNames`, `setPart`, `currentPart`, `{odt, ods}` allowlist) is not started and needs a new shell generation. |
| Link-batch spec | **FINAL after §12.** `specs/SPEC-M3-link-batch.md`, 363 lines at `c6edfd37`. Identity: profile `e2-editor-v20` = v19's link inputs + the batch's engine changes; ABI 4 → 5; new shell generation; new host version. Core, fonts and data packs unchanged (writer-only core; `cjk-sub-e10`, `base-r5-no35`). The link is the owner's step. |
| Product bytes | None changed. |

### The spec as it now stands (§10 and §12 override §4, §5 and §9 where they name them)

§10 (fable ruling 2, review 1):
- **Completion rule (a), replacing §9's "wait for the cursor"** (§9's rule is the one `SPEC-M3-paragraph-merge` §3.2 had already rejected). For an extend from any start, and for a plain move whose dispatch-time cached `selectionRectangles` is non-empty: complete on a `TEXT_SELECTION` whose parsed rectangle list differs from the dispatch cache (empty versus non-empty counts as different), then the next `INVALIDATE_VISIBLE_CURSOR`; report the cache after that cursor. The 250 ms readback (`verified-move-readback`) stays the fallback. Caret-start plain moves are unchanged. The rule is a pure function in a header (the style of `merge_key_undo.hpp`) and its criterion is a generated LOK model test; both red cases (§9's rule, v19's rule) must fail "insert then Shift+key" and "type over a range then Shift+key"; the engine is not wired before that test is committed and red.
- **S2 pre-red on v19 is 16 cells, not §9's 18** (`shift-Left@doc-start` and `shift-Right@doc-end` have no callbacks). Sent through the SDK client because v19's page drops Shift. Any green cell: stop.
- **Delete form decided at run time.** The page no longer chooses `delete-backward` or `delete-selection`; the session method takes a resolver that runs when the queue item executes (`editor-shell/editor-session.js:287–311`). Not "the page waits for the move's promise" (that is finding 111's shape). S5 (form 2, from Table 1's 84 Shift cells): each cell followed with no wait by Backspace, Delete, or a typed character.
- **C gets a time window.** After the first 250 ms NONE, the transaction stays in `AwaitingUnitSelection` for one more `MergeStepDeadlineMs` (2000 ms). K1's `TEXT_SELECTION` in the window → today's path. Window expiry with NONE and a collapsed cache → `verified-boundary-noop` (`changed: false`, `boundaryNoop: { waitedMs }`), no `EDITOR_BOUNDARY_UNSUPPORTED`, no reopen. Named cost: about 2.25 s to respond to Backspace at document start.
- §4.5 (1) and E1 are withdrawn (every selection-leaving refusal reopens or locks the queue; `kStages` does not cover `finishSelectionBarrierError`). §4.5 (2) `caretBefore` stays as data.
- **Page number mechanism.** `page-rectangles` is a document-level export gated by a manifest field and `offers` (the redo precedent), never an action; the editor ABI is 5. Re-read trigger: a `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED` counter in editor state plus the paint reply's `documentSizeChanged`; **not** `documentChangeSequence` (typing sends no `INVALIDATE_TILES`, so it never advances). Scroll, resize, zoom and worker reopen recompute N and L on the page without calling the engine. Correction: Collabora's read-only `Parts.js:307–322` only serves previous/next page; its edit-mode string comes from the core.
- Owner questions, decided by fable: **Q-A** bottom status line, left side, "第 N 頁，共 M 頁" or "第 N–L 頁，共 M 頁", drawn by the page so the host shows it (host styling is an owner hand-test item, not a count criterion); **Q-C** item 2 ships in this batch (range arrow keys go to Writer; L-129 closes if R1's wrapped-line cell passes); **Q-D** not computed by the core, computed on the page.
- §10.11: one more bounded review (done as review 3).

§12 (fable ruling 3, review 3):
- **L-extend-prior-flush's population is whatever the model test prints**, not §10.1's prose. The LOK model gains two event shapes: a command result queued ahead of its own SEL/CUR (the `startEditorUnoAction` family) and a range select made of three `setTextSelection` calls. §10.1's "the document is never changed wrongly" is struck.
- **Flagged delete (data-changing hole, confirmed in source).** A Barrier-class unit has no anchor fence, so an extend completed by readback before its key ran lets the barrier's Shift+Left stack on it and delete two units where Writer deletes one. The engine keeps `extendUnconfirmed`: set when an extend completes by readback; cleared only by a rule-(a) completion, by a flagged delete completing with proof, or on close or a new worker (a caret-start plain move does not clear it). While set: `delete-selection` is refused before dispatch; a Barrier-class K1 is accepted only if it is exactly one code point; MergeKey keeps its fence plus K2; window expiry refuses instead of `verified-boundary-noop`. Stage `prior-key-unconfirmed`, `keyPosted: false`, reopen as for every boundary refusal. Criterion: the model test, committed and red before wiring. Red case 1: remove the flag → prints the two-unit delete and the silent no-op. Red case 2: apply the one-code-point rule unflagged → false refusal of a multi-code-point unit with nothing pending. The WASM stall is not inducible in an honest run: named, no instrument built. Dismissed: waiting 2 s after every extend, refusing deletes until the next push, dropping Shift+Arrow, and the review's own proposal (refuse the Barrier-class delete only when K1 arrives after 250 ms).
- **Page-number counter** increments on every `DOCUMENT_SIZE_CHANGED` callback (not on payload change) and its arrival pushes editor-state by itself. P2 needs an arm whose flush contains only the size change (asserted from the `lok` event log); if no product-reachable edit produces one, the arm is registered NOT_ESTABLISHED.
- **Rule A (131) moves into the run-time resolver**: if the previous queue item was a delete, use this key's own collapsed form; otherwise use the snapshot. This is a data-safety requirement: the gate reads the engine cache, so a `delete-selection` chosen from a stale snapshot would pass the gate and `.uno:Delete` would silently delete forward one character on an already-collapsed caret. S5 gains two-key sequences (the same delete twice; a delete before the Shift+key) over the 84 cells, judged after `reduce_content` (`SPEC-M3-paragraph-merge` §24), with the in-flight count per cell as the positive control (an empty overlap set fails).
- **Pins are produced by grep at implementation time**, command and output recorded in the spec. Known: `e2/expected-gesture-offers.json` (still points at v8; `expected` and `rationale` change together), `e2/relink-queue-v3.json` rows `p1-4-abi-3` and `p1-7-header-test` (add 4→5 `supersedes` rows), the builder's ABI per profile, `src/editor_api.h:43`, the d.ts `moveLine` overload, the client check, the page's `MOVE_ACTIONS`, `DECLARED_DIVERGENCE`, and `m4-shift-*` retiring with 129-B.
- **§11: the stack is unchanged in this link** (no measured Writer failure; one variable per link). Registered instead, before W8 and without a link: a Writer stack sweep, 64 KB versus 256 KB.
- No third spec round. Default conclusions are in §12.7 (no flag or model test → item 1 does not ship; no resolver → item 1 does not ship; no counter → item 3 does not ship).

## Next (in order, from the spec)

1. **Pure-function header for rule (a) and the flag, and the extended LOK model test** (brief already written: `handoff/tasks/TASK-2026-10-13j-extend-rule-header-and-model-test.md`, `c163fd0a`). Deliverables: `src/extend_completion.hpp`, `tests/extend_completion_model_test.cpp` (sequences generated, not listed by hand; extends the model of `tests/merge_key_undo_model_test.cpp` with command-result-ahead-of-flush, a multi-call selection, a queued insert flush and a late readback flush), evidence in `findings/evidence/link-batch/extend-model/`. Red cases per §10.1 and §12.2 (§9's rule, v19's rule, no flag, unflagged one-code-point rule). Committed and red **before** anything in `probe_engine.cpp` uses it. The Makefile may only gain a host-test rule, with `make -n` on a profile target before and after (finding 042).
2. **S2's v19 pre-red on exactly 16 cells** through the SDK client (§10.2). It needs no link and can run before Next 1. Any green cell: stop and find out whether WASM's callback order differs from native or the instrument missed it.
3. **Writer stack sweep, 64 KB versus 256 KB (§12.6), pre-W8, no link.** Product-path net and the merge shakedown on the shipped Writer profile, 64 KB as control and 256 KB via the mirror patch of `90fed9b7`, both browsers, echoes recorded. A differing cell is a finding; no difference registers **L-writer-stack-64k**. Caution: `run_e2_c_product_path.py` rewrites the page's `PINNED_WASM_SHA256` in its mirror (around lines 455–470), and the loader is one of a profile's five bound files, so a stack patch changes a bound byte; and under §34 a change to a check needs a witness report. How to add the patch (this runner or a copy) is not decided.
4. **Implementation**, after Next 1 is red and committed: engine (rule (a) wiring, `extendUnconfirmed`, C's window, `caretBefore`, the `DOCUMENT_SIZE_CHANGED` counter and the `page-rectangles` export), worker (v19's is a copy of the v15 archive whose `EDITOR_V1_MOVE_ACTIONS` rejects line-move extends, so it must be rebuilt), SDK, client (`extendSelection` for six moves; completion whitelist accepts `verified-boundary-noop`), builder (`build_e2_editor_v4_profile.py`: `ABI_VERSION`, `no-extend-selection`), manifest (six moves get `collapsed`, `range-single`, `range-cross`; the four line moves lose `no-extend-selection`), and every pin (found by grep, §12.5). Page: Shift sends `extendSelection`; range arrows go straight to Writer (the 0.2.13 point-click-then-move is removed); the run-time resolver with rule A; held-key pacing for Shift+Arrow (S-12: count in-flight moves and extends); the bottom status line; `page-rectangles` gated export. A new shell generation is needed (the page and `editor-shell/` are bundle-scoped).
5. **Engine-code review (opus, spec §6)** before the runbook. The brief carries two fixed questions on the flag: (1) a sequence that clears the flag by a forged confirmation before the stacked K1 runs; (2) a common sequence the flag refuses that the one-code-point rule should admit.
6. **`handoff/RUNBOOK-relink-v20.md`** for the owner, in the shape of `RUNBOOK-relink-v19.md`: archive first (`build/archive/`), `ALLOW_FROZEN_RELINK=1` on the single v20 target, post-link checks (wasm hash, the export table contains the new operation, `ScDocShell` 0 occurrences, v8 and v19 untouched). Makefile changes go to the owner first (finding 042). **The link is the owner's step.**
7. **Shakedown, then the count chain overnight**, detached from the session (shape of `runs-0.2.13/chain-2026-10-12.sh`), with §7's account: 127, 128 treatment B, 129, 130, 131 rule A, 133, 134, 136 and 132's page fix, plus the batch. Arms: S1, S2, S3, S4, S5, R1, P1, P2, P3, C1, E2, E3, K, and the three counted product-path arms of §10.1 (insert then Shift+key with no wait; a merging Backspace then Shift+key; Shift+Right held 1 s). Before counting, list the existing arms whose expectations name `nothing-selected`, a rejection count or a generation list (§10.7: candidates `start-press`, `start-hold`, `end-hold`, `end-press-type`, `restore-window`, `cell-start-hold`) with their new expectation (0 rejections, generations `['1']`, document and caret unchanged); the first v20 shakedown of those arms is a §34.4 witness. Rebind the pins of the six M3 runners, the production-UI runner, the autosave runner and the product-path net. The task must say either "abort only if load ≥ X at start" or "never abort a started chain" (10-13d's deviation), and finding 135's C2 repeat semantics must be decided first (default: single-run rule with a ratio beside).

## Named limits and open items registered this session

- **L-extend-prior-flush** (§10.1, redefined by §12.1): an extend completed by rule (a) before an earlier operation's own flush carries a stale state. The population is the model test's printout; the effect is one stale completion reply and, through a following delete, the forged-completion residual below.
- **Forged-completion residual** (§12.2): if a rule-(a) completion is itself forged, the extend's key is still queued and the flag is not set, so a delete behind it can stack and remove one unit too many. It needs three coincidences; the model prints its population. Two closures are registered as the owner's choices and **not taken in this link**: the one-code-point rule applied without the flag (regresses multi-code-point graphemes), or a FIFO marker after each posted key (needs a forgery analysis and a native measurement first).
- **L-flagged-delete-grapheme** (§12.2): while the flag is set, Backspace over a multi-code-point grapheme (combining marks, ZWJ emoji, variation selectors) and `delete-selection` are refused and reopen; typed text is kept (109's checkpoint).
- **L-C-late-K1** (§10.5): a K1 arriving after about 2,250 ms leaves a selection in the live session; the next typed character replaces that unit. Cannot be closed: at the true document ends K1 produces no callback, so there is nothing to wait for.
- **L-page-margin** (§4.3): the page counts a page as visible by its whole rectangle, so a view showing only the previous page's bottom margin counts one page more than Writer does.
- **L-page-virtual** (§4.3): custom starting page numbers and Roman numerals are unknown to the page.
- **L-page-size-invariant** (§12.3): a page-count change that leaves the document size unchanged and happens during a paint or inside `CalcLayout` emits neither signal; no product trigger was found.
- **NU-089-3** (finding 089): worker crashes (`memory access out of bounds`) follow "a Calc calculation env variable is set" (across 7 runs, all 14 F1/F5 cases clean), not the SAX thread or the ThreadPool cap. Consistent with the stack mechanism, not proven by it. Unexplained, as before.
- **L-writer-stack-64k**: pending. Registered only if Next 3 finds no difference.
- Carried from 10-13d, unchanged: L-136-rule-iii-residual and the two engine items from 136 (now in the batch as C and `caretBefore`); L-129 until R1 passes; finding 135's follow-ups; the wallet launcher flag (the owner chose A, not urgent: check `kdewallet` `Locked` before any Chrome probe after a reboot).
- From W6: `probe_a11y_gate0.py` reads exit 0 as "provides accessibility", so a core with accessibility but no Calc would be read as "no accessibility" (fix: `--capability writer-lok-accessibility` at that call site); and at cutover the a11y negative control in the self-test needs its own writer-only path.
- From W9: both fixtures report `documentSizeChanged: true` on the first paint (width 26593 then 26775). W2 had recorded a 182-twip candidate-versus-native width difference; if W2 read the open-time width, that difference may be "not yet laid out". Unmeasured.

## Lessons

- `grep -c` counts lines, not occurrences. `probe.js` is about one line, so "grep -c 65536 = 1" looked like a unique literal and was wrong (6 occurrences). The patch is safe because the tool demands that its anchor occur exactly once, not because 65536 is unique.
- A probe page must register its listener before engine init. `createDocumentEngine()` resolves after the worker's preRun, so an echo printed in preRun reaches no listener. The echo gate stopped the run (E0-r1 0/7); the states matched the banked ones and were still not read.
- Read prior rulings before writing a completion rule. §9 chose "wait for the cursor", which `SPEC-M3-paragraph-merge` §3.2 and §16.1 had already rejected (any rectangle change can forge a cursor); review 1 found it as BLOCKING B1.

## §34.4

- This segment: 因執行而修 **1** (the probe page's listener-before-init fix, `88472109`, witnessed by E0-r1's 0/7 echo), 因審核而修 **0**.
- Not counted: the spec revisions in §10 and §12 (dispositions of reviews 1 and 3 on a spec before any check built from it existed) and the three drafter errors fable corrected in finding 089. This is the drafter's classification.

## Subagents (not reachable from a new session)

- fable (rulings, for the owner): 089 ruling 1 (`c6e10b21`); link-batch ruling 2 (`918c2497`); link-batch ruling 3 (`1b38f6c0`). Their outputs are the `ruling-*.md` files.
- opus (adversarial reviewers): link-batch review 1 (`cf0e15d2`, the whole draft); review 3 (`6370916e`, §10 only).
- sonnet (executors): `TASK-2026-10-13f` (089 threading arms, then the stack arms), `10-13g` (W6), `10-13h` (native extend signatures), `10-13i` (W9 draft). Their outputs are the READMEs under `findings/evidence/089/`, `m4-ods/` and `link-batch/extend-signatures/`.
