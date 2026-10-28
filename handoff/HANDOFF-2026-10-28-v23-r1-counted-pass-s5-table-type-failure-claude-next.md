# Claude handoff: counted R1 PASS; S5 blocked by reproducible table/type mismatch

Supersedes `HANDOFF-2026-10-27e-v23-astra-a-adopted-counted-r1-s5-running.md`. Checkpoint 2026-10-28, after the owner requested continuing to a bounded stopping point and then handing off to Claude. **Nothing is running.** The former background pipeline finished yesterday by its first-nonpass rule, before today's daemon restart. This checkpoint completes evidence verification/archive and a bounded two-browser diagnosis; it does not launch another long run or implement an unreviewed oracle/product change.

Evidence/documentation head before this handoff: `c4f6d3f4`. The tree is clean except unrelated untracked `codex-claude-code-delegation.md`; preserve it. No compiling make, native execution, build/relink, root modification, profile/shell change, host/DDEV change or upstream submission occurred here. All frozen product/instrument inputs remain unchanged.

## Established: first complete counted R1, 144/144 PASS

`findings/evidence/link-batch-v23/feature-protocol/r1-counted-01/` is complete: **72 Chrome PASS + 72 Firefox PASS**, population complete, runner exit 0 and independent aggregate judge exit 0. No filters/preparation-only/keep-going/retries. It has 36 literal and 36 layout-relative cells per browser, with all six prescribed wrong-old-click controls PASS across the two browsers.

- Runner: 2026-10-27 13:36:34–15:11:43 +0800, 5,708.5 s; independent judge completed 15:12:07.
- Report SHA-256: `cf943eb9d6878da832f9fb71289f0e5fd4ff2bcba1361a9fab5d1914b619224a`.
- Aggregate SHA-256: `2c23a8a34e1ab81355f342f8847b8757967273b8bfaa33b9064b889e92091d3d`.
- On 2026-10-28 I reran the original independent aggregate judge: exit 0, **byte-identical** output (`aggregate-judge.reread.stdout.json`, empty stderr).
- Report config/postConfig and live final config agree. The required historical pre-red remains EXPECTED_RED, 32 cells, report SHA `5f94f48c2677be548405e1856fb2ac74b6c096e5ddb851943f2af54e3ade05fb`.
- Archive/result commit: **`e5cf298e`**. This R1 result belongs to the exact frozen v23 identity; later S5 failure does not erase it, and a successor artifact does not automatically inherit it.

## Stopped: S5-02 first failure, not an interrupted collector

`feature-protocol/s5-counted-02/`: **401 Chrome PASS, then one FAIL** at `shift-Right@cell-end/type` (402 observations). **Zero Firefox observations**, incomplete population, zero qualifying partial credit. Runner exit 1 at 2026-10-27 17:18:17; pipeline terminal state `STOPPED_FIRST_NONPASS` at 17:18:20. The original independent aggregate judge exits 1 because the stopped report lacks postConfig; `actual instrument/source graph differs or incomplete` is that expected refusal, not a measured source drift. All frozen hashes still match.

- Failed inspection: `sequence result differs from its reference`, reference `native`, first differing paragraph 8. Report SHA `293900a266cea90cc14c7204da42ae18e180548af2426a3470fe25ebea8ac45c`.
- Before the stop: 154 settled-WASM PASS, 245 ordinary-native PASS, two `native-every-member-settled` PASS. The 401 passing inspections have 287 actual-overlap and 114 non-overlap records. These are descriptive partial results, not S5 acceptance.
- Both members of Astra A's order-dependent deletion partition passed. **The current stop is a type cell outside that ruling.** Do not broaden A or silently select settled-WASM to make it green.
- Original report, page, inspection, native oracle, stop logs and aggregate refusal remain unchanged; no counted run was retried/resumed.
- Counted stop plus fresh diagnostic archive: **`ed15fd56`**. Pipeline terminal receipts and complete inspection reread: **`2d778b6b`**.

## New finding 168: type over a table selection uses paste semantics

Read `findings/168-sdk-type-over-a-cross-cell-selection-pastes-into-both-cells-and-adds-a-hash.md` and the English `feature-protocol/s5-table-type-diagnostic-01/README.md`. Diagnostic/finding commit: **`6532141c`**.

The existing fixture has A1 `A1 cell text`, B1 `B1 cell text`. From A1 text end, Shift+Right then type `x`:

| Saved paragraphs | A1 | B1 |
| --- | --- | --- |
| Counted product Chrome | `A1 cell textx` | `B1 cell textx#` |
| Fresh diagnostic Chrome | `A1 cell textx` | `B1 cell textx#` |
| Fresh diagnostic Firefox | `A1 cell textx` | `B1 cell textx#` |
| Bound run-03 native keyboard oracle | empty | `x` |

`s5-prep-07/` runs a **fresh uncounted** two-case diagnostic in each browser: plain-text `shift-Right@caret-mid/type` PASS in both, table `shift-Right@cell-end/type` FAIL in both. Explicit preparation-only/keep-going preserves both failures, no qualifying credit. Exit 1, 95.8 s, config/postConfig equal; report SHA `f9e4c7d069b8f760e736e3e0a43606655cdaa8a0ab20620d0c8d74f261cf7cbc`. Its complete inspections and receipts re-read unchanged. Three product table observations share one native reference; these are not three native repetitions.

Every candidate's original save matches the unedited fixture. The measured window contains one public `insertText(text='x')`, and the terminal says **`method: paste`**. The insertion request is posted **after** the successful Shift extension terminal. There is no extra public `#` insertion. Thus a missing readiness/original, direct old R1 marker in the input, or insertion posted before the extension terminal does not explain the saved result. Do not infer heap contamination or a responsible layer.

### Source reading: observed route versus unproved explanation

`s5-table-type-diagnostic-01/comparison.json` binds exact source file hashes/line anchors plus saved paragraphs, native-save identities and extension/insert request/response payloads. Its reader reproduces all five page inspections from retained data; controls reject a wrong raw receipt and changed reference metadata without altering preserved files.

- SDK engine `probe_engine.cpp::handleInsertText` first uses LOK `paste(text/plain;charset=utf-8)`; postKeyEvent is fallback only if paste returns false. Actual response confirms paste here.
- Core `desktop/source/lib/init.cxx::doc_paste` sets clipboard bytes and dispatches `.uno:Paste`. `lokclipboard.cxx` constructs an explicit-length UTF-8 OUString; this inspected constructor does not ignore length.
- Writer `sw/source/uibase/dochdl/swdtflvr.cxx::PasteData` excludes table mode from selected-content deletion. `PasteFileContent` builds a UTF-16 stream and sets the ASCII reader to UCS2. This supports the observed append-versus-keyboard-replacement distinction.
- `sw/source/filter/basflt/shellio.cxx::SwReader::Read` reuses/rewinds that stream across the PaM ring. `AsciiReader::Read` in `sw/source/filter/ascii/parasc.cxx` resets ASCII options after each read. Reset restores the thread/system charset. The text parser has charset detection and replaces control characters below space with `#`.

**Inference only:** a later PaM may interpret the same UTF-16 `x` stream under reset/detected encoding, turning its NUL into `#`. There is no runtime trace, direct native-plain-paste measurement or charset perturbation, so the precise `#` cause remains unproved. Core source HEAD read: `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`. Older native Markdown multi-cell paste observations in `findings/evidence/link-batch-v21/native/markdown-paste/round-2/README.md` are related context, a different MIME/corpus, not proof of identical mechanism.

## Evidence verification and replay

Everything is committed; raw JSON also remains locally present/ignored. No evidence fields were dropped. `feature-protocol/STORAGE.md` documents the unchanged existing lossless store and thin directory-root wrapper:

- `r1-counted-01/storage-index.json`: 144 raw cells, 542,826,351 bytes → 44,180,198 gzip bytes.
- `s5-counted-02/storage-index.json`: stopped S5 plus prep-07, 406 raw cells, 512,407,438 bytes → 119,886,720 gzip bytes.
- Pack checks original runner SHA, verifies decompression and rereads original; separate verify exits 0 for both indices. Runtime mirror/profile symlinks remain ignored; exact served mirrors/reports/commands are tracked.

`counted-r1-s5-01/read-completion.py` verifies declaration/config/current import closure/prerequisites/actual mirrors/stage receipts, all raw hashes and every one of **546** retained R1/S5 inspections. JSON round-trip maps Python tuples to their serialized arrays; **no fields are ignored**. It verifies complete R1 and the unique declared S5 prefix, rejects a wrong raw SHA for each stage, and retains S5's incomplete result. Output: `completion-read-01.json`. `s5-prep-07/reread.json` separately verifies all four fresh diagnostic inspections.

From repo root, after restoring raw files if absent:

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/store_raw_cells.py verify --index r1-counted-01/storage-index.json
python3 -I findings/evidence/link-batch-v23/feature-protocol/store_raw_cells.py verify --index s5-counted-02/storage-index.json
python3 -I findings/evidence/link-batch-v23/feature-protocol/counted-r1-s5-01/read-completion.py --output FRESH-COMPLETION-OUTPUT.json
python3 -I findings/evidence/link-batch-v23/feature-protocol/s5-table-type-diagnostic-01/read-diagnostic.py --output FRESH-DIAGNOSTIC-OUTPUT.json
```

Use `restore` instead of `verify` to recreate missing raw files. Both readers require a fresh output filename. The original full R1 aggregate command, from `wasm_sdk_probe/`, is:

```bash
python3 -I tools/judge_v23_feature_selection.py ../findings/evidence/link-batch-v23/feature-protocol/r1-counted-01/report.json
```

Replay before changing the closure, or use the exact preserved graph in an isolated checkout. The archived source tar/config/declaration are in `counted-r1-s5-01/`; do not silently rejudge historical runs with changed tools. Do not rerun the completed launcher or reuse counted output directories.

## Claude's next bounded work

1. Resolve finding 168 under the existing native-type requirement. If needed, prepare a small native direct-paste versus actual-key-input experiment on the same table selection, with plain-text and encoding/length controls. Distinguish generic paste's append semantics from why the later cell gets `#`; do not fix only the suffix while leaving the replacement mismatch.
2. Prepare a reviewable product repair if the typing path is wrong. Any engine/core rebuild follows the owner's build rule. A new artifact must use a successor identity and fresh bindings, never overwrite frozen v23. Preserve the existing identity-bound R1 and four-arm results; establish what needs revalidation for the successor rather than silently transferring those results.
3. A proposed semantic narrowing instead needs an explicit prospective ruling; Astra A authorizes only the prior deletion-reference amendment. The owner limits Astra usage to hard decisions, not routine delegation. No new decision was requested or made in this checkpoint.
4. Only after the chosen fix/ruling, red controls, final two-browser preparation and frozen bindings, declare a fresh full S5 run in a new directory. Old counted-01/02 and preparations contribute zero partial credit. Do not start another hours-long run merely to rediscover this known blocker.

The personal rule is still **no sudo/su/doas/root changes**, even if the owner says elevated. Compiling make is owner-run unless the owner explicitly asks to build; native harness compile ownership also follows the protocol. No current build authorization should be inferred from “continue.” Repository evidence/upstream text/handoff/commit messages are English; conversation and internal findings are zh-TW.

Earlier S1–S4/four-arm conclusions remain within their recorded scopes; four product arms are independently 24/24 PASS (`431bce12`). The integrated four-arm patch must not be reapplied. Current identity is still e2-editor-v23 ABI6, WASM `fe1f99cd…`, worker `3fd3e1e6…`, page `c25b11c4…`, generation 76. Exact config SHA remains `0a47d0e82fc5b8f9d43e3aa3c59fab6592510526356a1100b9e70b38e2f91552`; certificate 05 remains current (`ad4febf6…57e43`). No overall product acceptance is claimed. Remaining named inputs, Firefox 096 B2/B4, host/DDEV, K, finding 166 unipoll and finding 167 desktop-Writer remain unclosed.
