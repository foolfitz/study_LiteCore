# Handoff, 2026-10-16b: v21 linked (finding 142's Ctrl+Home/End plus Markdown paste); post-link checks green; the WASM shakedown is next

This continues `HANDOFF-2026-10-16-0.2.24-count-holds-release-text-revised-makefile-a.md`. Commits `338b8ddb..58fef59d` (32 commits: `git log --oneline 28f9c183..HEAD`). Main session: opus.

The session opened when the owner said they had read the 0.2.24 release text and that the previous session had said the link could start. It went through plan, native arms, spec, two review rounds, implementation and the link. **No v21 code has run in a browser yet.**

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.24**, unchanged. By spec §11.3 K, v21 stays an uncounted candidate until a count holds |
| 0.2.24 release text | **Final** (`338b8ddb`): the owner read it and flagged nothing. Its two "next link" promises were corrected the same day (`71fa6ad9`); see What happened 2 |
| Lock table | Rows 4779 and 4783 were deleted with the owner's A at 09:44:42 +0800, leaving 0 rows (`831188ce`; `findings/evidence/m3-production-ui/runs-0.2.24/lock-cleanup-2026-10-16b.txt`) |
| v21 scope | Finding 142 (`move-document-start`/`end`, Ctrl/Cmd+Home/End) and Markdown paste (a dialog entry). The C declaration was withdrawn (OD3) |
| Spec | `specs/SPEC-M3-link-batch-v21.md` (zh-TW). Criteria were pinned at `523871fa`, and **§11 is the only criteria table**. §12.1 (valid UTF-8) was appended after the pin (`3d9ca3a4`) |
| **Profile `e2-editor-v21`** | **Linked**, 22:22:06–22:25:18 +0800, make exit 0. wasm `db3408f5…`, loader `0b6cf02a…`, worker `0d55bcfa…`, manifest `72067d5a…`. ABI 5, 23 actions, `select-all` withheld (`gestures: []`), `pasteMarkdown = "document-sdk-paste-markdown"`. Archived at `wasm_sdk_probe/build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/` (7 files, not in git). **Not bound** |
| Post-link checks | All green (`58fef59d`; `findings/evidence/link-batch-v21/post-link/README.md`) |
| Shell generation v74 | **Not frozen.** The page, shell and SDK changes are in the tree (`bc6534e0`); the `dist/` copies are still 0.2.24's |
| WASM shakedown (§11 D1–D13, M1–M11) | **Not started; no runner exists** |
| Host | 0.2.24 installed; 0.2.25 not built |
| New findings | 146, 147, 148, 149 (see What happened 3) |
| Tree | Clean at `58fef59d` |

## What happened

1. **Session start.** Release text final (`338b8ddb`); two expired runner locks deleted by id with the owner's A (`831188ce`). The owner used ddev in another session today; this session did not use ddev after the lock cleanup.
2. **Plan and scope** (`de4d0159`, `handoff/PLAN-2026-10-16-link-batch-v21.md`; three read-only fact sheets in `handoff/link-batch-v21/facts-*.md`).
   - The owner's 「好，請開始」 was taken as **scope A** (plan §6). Then three owner answers, all A (`836f5043`, spec §9.13): **Q1** the Markdown entry is a dialog with a text box; **OD1** the Ctrl+Home/End readback stays at 250 ms; **OD3** the C manifest field leaves v21 (nothing in v21 reads it; it ships with its first reader).
   - Deferred: `Language=` and D12 (measured natively, decision later); `handleEditorPlaceCaret` on `TEXT_SELECTION` and the immediate document-boundary answer (both to the ordered-commands batch).
   - The release text's two "next link" promises were corrected in place, with a revision-log row (`71fa6ad9`).
3. **Native evidence**, in five folders under `findings/evidence/link-batch-v21/native/`. The main session re-derived every reader's output byte-identical.
   - **`language/`** (`b5f22e79`, 31 arms × 2): `LANG=de_DE` with `Language=zh-TW` saves Western **en-US**, so analysis-1's de-DE leak claim does not hold (correction appended to `findings/evidence/new-document/analysis-1.md`, `7703ed83`). `en` gives A4, `en-US` Letter; an invalid tag and `zh_TW` are silently ignored.
   - **`142-ctrl-home-end/`** (`1389c023`): 81 arms × 3, every arm 3/3. **`d1-marker/`** (`a2c7c4cc`): D1's population by script grammar, 38 IN / 43 OUT; 120 processes, all 3/3.
   - **`markdown-paste/`** (`68a98f09`): every construct converts; one paste is one Undo action (152/152 processes); `paste()` returns true even on empty input. **`round-2/`** (`17fe9054`): cells and the header behave in-region; seven positions return true with no Undo action (protected section etc.), M9's red case; raw HTML fetches remote URLs.
   - **Findings**, all native-only and recorded only (upstream submissions are on hold):
     - **146** (`f4937666`): Markdown bold and italic are Western-only, so CJK and CTL text is not bolded. Upstream code.
     - **147** (`e30e5dc0`): a paste inside a `text:text-input` field garbles the text, and one Undo does not restore it. **`text/plain` is affected too, so today's Ctrl+V is affected natively.** WASM unmeasured.
     - **148** (`e30e5dc0`): a multi-cell Markdown paste writes source text and mojibake into the second cell. v21 avoids it by pasting on a collapsed caret only (L-md-collapsed-only).
     - **149** (`1327c11a`): HTML entities are dropped (`AT&amp;T` → `ATT`). Upstream code; 1 native run.
   - The owner chose **B** for constructs Writer handles badly: paste as-is and register named limits (L-md-entities, L-md-task-checkbox; spec §10 header and §10.4).
4. **The lesson of the round: the product engine is threaded LOK, not unipoll.**
   - The 142 native README and the spec draft (§3.1, §8 Q3) took the unipoll setup from `mainLoopEngineThreadMain`. That function exists only under `OXSDK_MAINLOOP_ENGINE`, and the product rules cannot carry that define (`probe_engine.cpp:15-17` `#error`).
   - Both review seats found it independently (opus B1, codex R1). Corrected by an appended note in the 142 README (`91ca7318`) and spec §9.1; the task brief states it.
   - Consequence: the native ordering result describes the product. Named **L-142-readback-overtaken** (finding 137's class); the root fix is the ordered-commands batch.
5. **Two review rounds, two seats each**: an opus subagent and `codex exec -s read-only` (the codex MCP failed to connect this session).
   - **Round 1** (`91ca7318`): opus 4 BLOCKING / 17 SHOULD / 12 NOTE; codex 6 BLOCKING / 6 SHOULD. Dispositions in §9 (`a3f1f073`); second-native-round dispositions in §9.14 (`613ae72a`).
   - **Round 2** (`1327c11a`): codex 26 resolved / 7 partial; opus 17 resolved / 10 partial. Dispositions in §10; the pinned table §11 (`523871fa`, status `0897ba82`); pin list `handoff/link-batch-v21/pin-list-grep.txt` (88 lines, 26 files).
   - **§12.1** (`3d9ca3a4`): pre-dispatch rule "input must be valid UTF-8", appended after the pin under `CLAUDE.md` 判準形式 §9's four conditions. Forced by part E's fixture item X07: the scanner and Writer parse different bytes.
6. **Implementation.** Task brief `handoff/tasks/TASK-2026-10-16-v21-implementation.md` (`07d01cf8`), parts E and S in parallel.
   - **M0 fixture before any scanner code** (`975343c2`): 65 items.
     - Expected verdicts: PASS 29, REMOTE 10, HTML 8, INVALID_UTF8 6, NUL 5, NO_BLOCK 5, PARSE_FAIL 1, TOO_LARGE 1.
     - Stored in `wasm_sdk_probe/tests/markdown_paste_expected.json`.
   - **Part S** (`bc6534e0`; evidence `part-s-red/`, `5a820c28`): node tests 561/561 (re-run by the main session); 31 mutations, all red; D8's sequences on the 0.2.24 page logic 3 pass / 4 fail ((a), (c), (d), (e) red), all seven pass on the new page.
   - **Part E** (`516e53e4`; evidence `part-e-red/`). The main session re-ran the M0 model test (478 checks, ok), the mutation runner (every mutation red), 94 Python unit tests (OK), the ABI header test with and without the define (exit 0) and E1-C (intact). Part E also ran `em++ -fsyntax-only` on the engine (a syntax check, not a make, no objects) and said so in its report; no committed evidence file records that command.
   - **Pre-link** (`497aa9f7`): worker pin `0d55bcfa…`; `test-e2-c-static`'s M1-1 gains the `E2_V21` carrier; `what_the_link_ships` gains the `link-batch-v21` variant (`ok: true`, drift `[]`, three units changed).
   - **Runbook** `handoff/RUNBOOK-relink-v21.md` (`5f5bf11c`): gates §0 1–9 green; the pre-link frozen set has 1,306 files.
7. **The link** (`58fef59d`).
   - **The owner asked the main session to run it** (「請你幫我跑連結指令」/「我複製貼上怕有誤」). This is a one-time explicit request. **The global rule still stands by default: a compiling `make` is the owner's.**
   - The two pre-checks printed `0` and nothing. Post-link, all green: frozen set 1,306 files identical; `_oxsdk_document_paste_markdown` glue mapping 1; `ScDocShell` 0; X1 against v20 `VERDICT PASS` with exactly the declared deltas (`abiVersion` 4→5 as a changed leaf, six action leaves, `pasteMarkdown`); M1-1 base A `5d77dc84` (V15/V19/V20/V21) and base B `523871fa` (V21) both exit 0.

## For the owner

1. **Nothing waits on you right now.** The next step is the main session's: writing the shakedown runners.
2. **A process that is not ours is using a full core.**
   - PID 3675664, `python3 -` (a heredoc that imports PIL), started 2026-10-15 10:53:18 under `codex-linux-sandbox`, cwd `~/Projects/quiz_platform`. It read 99.8% CPU when this handoff was drafted.
   - You were told; it was not touched.
   - The shakedown has timing bounds: D7 < 500 ms, D9 ≤ 500 ms, M6 ≤ 10 s. Please stop the process, or say it should stay, before those runs.
3. **Later, a yes for the host 0.2.25 install** (Next 4). You used ddev in another session today, so the router and app state get checked before that step.

## Not done / open

- **Nothing of v21 has run on the WASM engine or in a browser.** The JS ran under node unit tests and the scanner ran natively in the M0 model test; the engine's move and paste paths were compile-checked, then linked.
  - Markdown's first WASM run decides the encoding question. The engine refuses when `osl_getThreadTextEncoding()` is not UTF-8 (`MARKDOWN_ENCODING_UNSUPPORTED`, §10.4). If the WASM codeset is not UTF-8, every paste refuses, and item 2 does not ship.
- **Expected reds right now** (re-checked read-only when this handoff was drafted):
  - `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree` is red (1 failure among the module's 12 tests): the dist copies of `narrow-editor-v2-client.js`, `narrow-editor-v2-session.js`, `paragraph-editor-client.js`, `sdk/document-sdk.js` and `web/e2-editor-app.js` differ from the tree, and the manifest is out of date. Cause: v74 is not frozen, so `make test-e2-c-static` stays red until the freeze.
  - `check_gesture_offers.py`, red before the link, now exits 0 (`e2-editor-v21: 23 actions, 0 problem(s)`). `check_e1_c_bundle_intact.py` reads `"intact": true`. The full `make -k test-e2-c-static` was **not** re-run after the link.
- **`tools/audit_product_path_coverage.py` is red.** It runs in `make test-e2-c-reachability`, not in the static target.
  - **Already red before this batch** (`findings/evidence/link-batch/v20-part2/README.md`): the `#paper` pointer listeners, `scroll#desk`, and four stale `#canvas` registry entries. The 5 unattributed `addEventListener` calls count the same at `07d01cf8` and HEAD.
  - **New:** `action:paste-markdown`, `listener:cancel#markdown-dialog`, `listener:click#markdown-cancel` and `listener:click#markdown-insert`. Register them only once the M runners drive them.
- **Finding 147 on WASM** is unmeasured, and so is today's Ctrl+V into an input field. Finding 149 has 1 native run, not 3.
- **The 0.2.25 release text** is not started. Named limits to carry (§9–§11): L-142-readback-overtaken, -steps, -sdk-callable; L-md-137, -merge, -softbreak, -no-html, -collapsed-only, -protected, -input-field, -entities, -task-checkbox, -sdk-callable; L-hold-release-cost; L-142-held-after-move only if D8 goes red.
- Plan §4 step 1d (a diagnostic Markdown profile) was never done; the link came first.
- Carried from 10-16, unchanged: the new-document runner's leftover locks; `read-0.2.24.sh`'s header-line count; the J-b.1 append; the Firefox early-key latency on v20 pages; the round-3 Rbs offset; the `place-caret-second-pass` flake.

## §34.4

- Repaired because of execution: **0**.
- Repaired because of review: **0**.
- Running total since 10-14b: **execution 9, review 18** (unchanged).
- The tool changes this session are **new uses for a new identity**, not repairs of a check that misjudged an honest run: X1's `--declared-changed-leaf` (11 tests, the §11 X1-cl red cases), the `what_the_link_ships` `link-batch-v21` variant, the Makefile's `E2_V21` M1-1 carrier, the v5 builder.
- Existing unit tests were extended for the two ABI-5 actions, following product changes (e.g. `narrow-editor-v2-session.test.mjs`: "six" → "eight" key-path moves, `EDITOR_V3_ACTIONS` → `EDITOR_V4_ACTIONS`).

## Next (in order)

1. **Write the v21 shakedown runners** for §11 D1–D13 and M1–M11, plus the record arms (D6, x-lc, table Ctrl+Home+Backspace).
   - Red first. N=3 per browser (Chrome, Firefox); a pass is N/N.
   - Missing, NE or no reply counts as "not done" and takes the row's default.
   - Every report carries the wasm, worker, page, shell, input and reference hashes (§11.0).
   - Use the no-host page from `tools/build_cutover_page.py --profile e2-editor-v21`.
   - **D1:**
     - the population comes from `native/142-ctrl-home-end/d1-marker/tool/d1_population.py` (38 arms);
     - the reader `read_marker.py` needs its ODT adapter, with the four red cases (cross-container equality, marker shift, duplicate marker, missing XML), **before** any D1 run.
   - **M1, M3 and M5** route by M0's expected verdicts (`markdown_paste_expected.json`).
   - **M5** needs its positive control: the worker's `probe.wasm` fetch in the same network log.
   - Clean the desk first (For the owner 2).
2. **Apply any §11 default or fallback to the shell before freezing** (D4 red: intercept on a range with a hint; M6 red: a 16 KiB SDK limit, then no entry; an item that does not ship: no binding, no entry). Any arm whose evidence identity no longer matches the final candidate is void and must be re-run (§11.0).
3. **Freeze shell generation v74.** Check `make -n` first: the test's hint names `make e2-c-assets`, and finding 042 applies after the v21 Makefile block.
4. **Host 0.2.25.** Ask the owner before installing. Then `BINDING` for v21 in its own commit.
5. **The full count chain**, in the owner's window, detached (about 8 h). Then the 0.2.25 release text.

**Later.**

- The `Language=` / D12 decision. Native answers are in `native/language/README.md`.
- The ordered-commands spec: the immediate boundary answer; `placeCaret` on `TEXT_SELECTION`; the C declaration with its first reader; the L-142-readback-overtaken root fix.
- Finding 147 on WASM. The task-checkbox click recording arm (§11.2 record, L-md-task-checkbox).
- Carried from 10-16 "Later": the J-b.1 append; the reader's header count; the new-document runner's locks; a Firefox early-key measurement design; the A1-5 / A1-2′ R arm; a boundary hold longer than two windows; the admin trash-bin probe folders.

## Subagents

- **Fact sheets:** three read-only opus subagents. The main session spot-checked their citations (plan, header).
- **Native runs:** five, by subagents. Each reader's output was re-derived by the main session, byte-identical.
- **Reviews:** two rounds. Each had one opus subagent and one `codex exec -s read-only` run.
- **Implementation:** parts E and S, run in parallel. The main session reviewed the diffs, re-ran the tests listed above and committed.
- **This handoff:** drafted by a subagent. When drafting, it re-ran three read-only checks: the shell-bundle test, `check_gesture_offers.py` and E1-C.
