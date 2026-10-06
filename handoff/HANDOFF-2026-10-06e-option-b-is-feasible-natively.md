# Handoff, 2026-10-06e — option B (the user's own key, proved by the undo stack) is feasible on native LibreOffice; no spec, no engine byte changed

Entry points: this file; `findings/evidence/merge-native/README.md` (every round's table; sections "Second round, D" onward are this session's); `PREDICTION-2.md`, `PREDICTION-3.md`, `PREDICTION-4.md` (each written before its round); `wasm_sdk_probe/tools/merge_native_boundaries.cpp`, `run_merge_native.sh`, `analyze_merge_native.py`, `analyze_merge_undo.py`; `wasm_sdk_probe/src/probe_engine.cpp` (barrier at `:3246–3560`).

Picks up from `handoff/HANDOFF-2026-10-06d-paragraph-merge-measured-natively.md`. No upstream remote; nothing pushed. Nothing is running.

## Owner decisions this session

- **Order: A** — the paragraph merge before finding 111's measurement.
- After rounds D/E the owner was given A (merge on a `[10]` unit both ways; Backspace skips Writer's first step), B (at a boundary press the user's own key, prove the outcome from the undo stack), C (Delete only). The owner asked whether **B brings more features in line with LibreOffice**. Answer given: yes, as a *mechanism* — Backspace at paragraph starts (indent / numbering / list header), tables and document ends reported honestly instead of refusal+reopen, Enter (today `.uno:InsertPara` = `SplitNode`, so Enter in an empty list item does not end the list and Enter-time autoformat does not run), Tab/Shift+Tab in lists — but each key moved onto it is its own measured step. Not aligned by B: typed text (goes via paste for IME, so no typing-time autocorrect), formatting buttons (already UNO commands), mouse and selection.
- Owner chose **B′**: measure B's feasibility natively first; feasible → B, otherwise A.
- The owner asked whether to switch the engine to the main-loop poll model (the one with a scheduler-idle signal). Answer given: no performance measurement exists (finding 021's `e2-mainloop-attribution` only measured state freshness); the engineering is large (021: "屬重構" — `unipoll`, enter `Application::Execute()` whose emscripten main loop throws `unwind` and never returns, dispatch every command from the poll callback, a new engine identity, R6–E1 regression); B does not need it. Recommendation: do not switch. Performance as its own question was **not registered** anywhere yet.

## Commits

| Commit | What |
|---|---|
| `c35d350c` | Round D/E instruments + `PREDICTION-2.md`: probe takes a cases TSV; reader sees `is-list-header`, automatic-style indents, bookmarks; `boundaries-indent.fodt`, `pmpc.cases.tsv` |
| `3b1359cc` | Round D results (15 cases × 3) |
| `076ac980` | Multi-press instruments (PRESSES) + `PREDICTION-3.md` |
| `9d5c2448` | Placement fix: one search from the document start, check, return; both arms check and record the drawn caret |
| `202153b5` | Multi-press results, PMPC rerun (18 cases), round-four instruments (arm b, undo readback, `occurrence`/`offset`, `undo-grouping.fodt`, `analyze_merge_undo.py`) + `PREDICTION-4.md` |
| `720fa7af` | Round four results |
| `2e952d79` | Fifth-round instruments (not run, no predictions): `MERGE_UNDO_STEPS`, `undo-limit.fodt`, `round-h-limit.cases.tsv`; README count wording |
| the commit adding this file | This handoff |

## What was measured (numbers from the README)

- **Round D** (`round-20261006T073255Z`, synthetic): every boundary reads back `[10]`; Delete at a paragraph's end = the key everywhere; Backspace at an unlabelled heading's start (key: heading not counted) or an indented paragraph's start (key: indent removed) differs. 45/45 dispatches success + collapsed, 45/45 undos restore. Every prediction held. **`[10]` is enough to merge on Delete, not on Backspace.**
- **Round E first attempt does not count** (second-search fault): the select arm searched twice; the second search landed on the heading's copy in the table of contents while the check had passed on the heading. Fixed in `9d5c2448`.
- **Round E** (`pmpc-round-20261006T075511Z`, owner's document, 18 cases): every Delete at a paragraph's end equals the key; every measured Backspace at a paragraph's start differs. 54/54 undos restore; both arms' caret equal everywhere.
- **Multi-press** (`presses/`): deleting the barrier's selection at a paragraph start = Writer's document after **2** presses (heading, list item, first-line/left indent), **3** for a hanging indent (D12) and an indented bullet item (E17). It never produces a document Writer cannot reach — option A's exact cost.
- **Round four** (`undo/`): B's sequence (unit selection → unshifted opposite arrow → user's key) gives **`content.xml` byte-identical to the key at every paragraph boundary, 3/3** (plain, line break, numbered and unlabelled headings, list items, first-line and hanging indents, TOC-bookmarked headings, owner's document). Undo stack changed exactly when the document did: **324 boundary-batch presses (174 + 60 + 90), 0 disagreements**. Inside a paragraph, a run of identical characters (G10, G11) breaks the stack from press 20 (folded comment `Delete “aaaaaaaa...aaaaaaa”` stops changing) — why B is boundary-only. C08 (Delete before a bullet item: the arrow lands in front of the label) and C15/C16 (table) cannot be stepped back, 0/3, detectably. Undo comments: `Delete paragraph`, `Number On/Off`, `Apply attributes`, `Delete One line break`, `Delete Paragraphs`.
- **T01 predicted wrong about its target**: PMPC's TOC title 「目次」 is editable; Writer's own Delete merges it into the first entry. The first-attempt no-op (success + collapsed, nothing changed) was between two index *entries*; not re-measured.

## B as worked out (not yet a spec)

- Barrier unchanged for any unit without a separator.
- Boundary unit: record the caret (`gEditorState.caret`, from `INVALIDATE_VISIBLE_CURSOR`); press the opposite arrow **without** Shift; require a collapsed selection and the caret equal to the pre-selection caret, else refuse with view recovery (today's reopen path). Read the `.uno:Undo` payload, post the user's key, re-read on later callbacks; payload changed → completion **`verified-key-undo`** carrying the top action's comment; deadline (initial 2000 ms, to be set from WASM measurement) → refuse with view recovery, **never report "unchanged"** (a late key would make that a lie — finding 016's shape).
- Compare the whole payload, not `UndoCount`: the count saturates at the undo limit (default `Steps` in `officecfg/.../Common.xcs` — the value was **not read**; verify).
- Nothing selected (document ends): unchanged, 250 ms refusal. Tables: still refused.
- Shell (`editor-shell-v2/narrow-editor-v2-client.js:276`) must accept the new completion → new generation. Page `workerUrl` is hard-coded `./profiles/e2-editor-v8/sdk-worker.js` (`web/e2-editor-app.js` ~1915) → new profile **`e2-editor-v15`**, Makefile rules a copy of v8's (RUNBOOK-relink-v8 pattern). v8 builds without `OXSDK_MAINLOOP_ENGINE`: blocking engine loop, LibreOffice's loop on LOK's own `lo_startmain` thread; key-vs-readback ordering on WASM is **unmeasured**.

## What the relink would ship besides B (measured this session)

`python3 tools/what_the_link_ships.py --since c41e8582`: `probe_engine.cpp` 20 hunks (+43/−11 preprocessed; 082's fingerprint degeneracy and 096's move-readback deadline among them); worker `070229cd` → `6e75829a` (+41 lines, 5 code); the other three units identical. **`c41e8582` as v8's link commit is an inference** (RUNBOOK-relink-v8 was written there) — confirm before linking. `check_relink_queue.py` this session: 64 items, 48 present, 16 open, 0 drifted, nothing blocking.

## What is next

1. **Write `specs/SPEC-M3-paragraph-merge.md`** (zh-TW, append-only, criteria before code, each with its "if never done" default). Drafted criteria: shell unit tests + red cases for `verified-key-undo`; WASM user path with real keys on `boundaries.fodt`, `boundaries-indent.fodt` and PMPC — saved document equals the native key arm's, completion `verified-key-undo` with the native comment, no reopen, 3/3 per browser, red against v8; key-to-undo latency recorded per completion, none at the deadline; refusals still honest (C08, C15, C16, C17, C29, C30) with 109's content guarantee; undo limit; product-path net v8 vs v15 cell by cell; **R** = six M3 runners + production-UI runner recount — its A1-2 B-del/B-bs arms will no longer see a refusal and must be re-pinned to a boundary B still refuses (C08 shape in PMPC: Delete at a body's end before the WW8Num4 bullet list). Opus adversarial review of the spec before code.
2. **Fifth native round**: undo limit with the committed instruments (`MERGE_UNDO_STEPS=3`, `undo-limit.fodt`, `round-h-limit.cases.tsv`, PRESSES=10) — predictions first. A protected index-entry no-op needs a TSV escape for the tab in entry text; design first.
3. **Finding candidate**: the shipped barrier's proof (success + collapsed selection) held on a delete that changed nothing between index entries — first attempt only; measure before filing.
4. Engine, shell, page change; red cases before trusting green.
5. Runbook + owner-run link (archive first); 6. package, host bump, recount. Finding 111 stays open after this.

## Things this round taught

- **A placement check must check the placement that is measured.** The select arm searched again after its check and measured the TOC copy. Both arms now record the drawn caret and the reader requires equality.
- **Editing a running bash runner corrupts it** (bash reads the script as it runs); the killed run's cleanup did not run.
- **Shakedowns before predictions found two ways B's sequence fails**: Shift + opposite arrow leaves a mark and the next key does nothing; an unshifted arrow when nothing was selected moves the caret and Backspace deleted the wrong character.
- **The block reduction treats the TOC as one opaque block**; `content.xml` bytes and the undo stack saw what it could not.
- **A prediction can be wrong about its target while the mechanism holds** (T01) — say which.

## Standing rules to carry

- Never two M3 runners (or an M3 probe) at once; each clears the whole `oc_files_lock` table.
- Counted runners refuse a dirty host tree; a host JS change means an `info.xml` bump + `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`; the buildId is content-addressed.
- A runner changed after its pin is a new pin (append to the spec), or its reports do not count; the locks runner's pin is `1d3099a2…` (§12.1). `check_m3_same_second.py` and `probe_m3_save_throw.py` import `open_from_files` from it.
- `findings/evidence/**` and `handoff/**` English; specs, findings' prose zh-TW; specs append-only.
- Native probes load a per-round copy of the fixture, never the fixture itself.
- Never `pkill -f` with a pattern that also matches your own shell command line.
- **New:** never edit `tools/run_merge_native.sh` or the probe while a runner batch is queued or running — each invocation recompiles.
- **New:** the owner's PMPC document never enters the repository; rounds on it run under `wasm_sdk_probe/build/` and only arms/summaries are copied into `findings/evidence/`.
