# Review 2, seat opus: SPEC-M3-link-batch-v21 after §9

Target: `specs/SPEC-M3-link-batch-v21.md` at `1b0ccaee`, §1–§9.14. Read-only: grep, sed, `llvm-nm` on two static libraries, and one read-only Python pass over `dist/profiles/*/sdk-manifest.json`. No build, no browser, nothing compiled or run from the evidence folders.

Labels: **[src]** read in source, **[doc]** stated in a doc, **[inf]** inferred. `wsp/` = `wasm_sdk_probe/`, `lo/` = `libreoffice-26-8/`, `md4c/` = `wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src/`.

## 1. Review-1 items: resolved or reworded

| item | §9 text | verdict | what is left |
|---|---|---|---|
| opus B1 / codex R1 (not unipoll) | §9.1, §9.13 OD1=A | **resolved** | D2′ cannot go red at nominal timing (see C7). |
| opus B2 (defaults after the link) | §9.2 | **resolved** | M3's boundary arms do not follow the operative limit (C3). |
| opus B3 / codex R2 (D1 population) | §9.5, §9.14 | **resolved** | Header/footer now has zero D1 arms; registered under L-142-steps. |
| opus B4 / codex R3 (M1 population) | §9.6 | **partial** | Classified over round 1 only, and "remote image" is a label, not the scan's verdict. Round-2 items (S14, S15, N1, W3, W4, H1–H7) are in no WASM criterion (C2). |
| opus S1 (wrong completion invisible) | §9.7 D7 | **resolved** | D7 has no default and does not pin the 250 ms deadline (C1, C6). |
| opus S2 (mask unwitnessed) | §9.7 | **resolved** | See A3 for the residual. |
| opus S3 (shell lists unguarded) | §9.7 | **resolved** | — |
| opus S4 / codex R4 (Markdown postcondition) | §9.4, §9.14 M9 | **partial** | The disposition that was chosen loses unsaved work. M9 runs on a clean document only (B1). |
| opus S5 (M3 unit/boundary) | §9.12 | **partial** | The arms are pinned at 65,536 B, not at the operative limit. SDK and engine refusals look the same (C3). |
| opus S6 / codex R5 (images) | §9.3, §9.14 | **partial** | Images are closed by the parser, but rule 2 (HTML) has no WASM arm, and the scan's input ≠ Writer's input (A1, C2). |
| opus S7 (held Ctrl+Home) | §9.8 L-142-no-repeat, D9 | **partial** | It keys on `event.repeat`, the basis that finding 141's ruling rejected (C5). |
| opus S8 (pin list) | §9.10 | **resolved** | Add the md4c `#include`/`-I` to the define-gated list (A5). |
| opus S9 (v5 builder) | §9.10 | **resolved** | — |
| opus S10 / codex R12 (C field) | §9.11, §9.13 OD3=A | **resolved** | Withdrawn. |
| opus S11 (D4 default) | §9.9 | **resolved** | — |
| opus S12 (view follows Ctrl+End) | §9.9 D10 | **partial** | D10 has no read time, no default and no freshness clause (C6). |
| opus S13 (N) | §9.12 | **resolved** | — |
| opus S14 (positions) | §9.12, §9.14 | **resolved** | L-md-unmeasured-positions is not restated for what is still unmeasured: footers, footnotes, unprotected frames, a document starting with a table (round-2 README:176) (D5). |
| opus S15 (Q1) | §9.13 | **resolved** | The cancel arm has no default (C1). |
| opus S16 (paste bookkeeping) | §9.12 | **partial** | It states a fact but gives no arm and no default. The view-only refusal of the paste is not in the negative matrix (C1). |
| opus S17 (residuals) | §9.12 | **resolved** | — |
| codex R6 (16 KiB fallback) | §9.2, §9.12 | **partial** | Same as S5. |
| codex R7 (completion/bookkeeping) | §9.7 | **resolved** | — |
| codex R8 (hold vs move) | §9.8 | **partial** | The rule as worded can reopen 141 and still swallows presses (A4). |
| codex R9 (negative matrix) | §9.10 | **resolved** | Make "one action withheld, the other offered" an explicit row (D5 in the table). |
| codex R10 (comparator) | §9.12 | **resolved** | — |
| codex R11 (identity) | §9.10 | **partial** | I1's frozen-hash list is still five named profiles out of 55 dirs in `wsp/dist/profiles/` (C4). |

## 2. The new mechanisms

### B1 — BLOCKING. Markdown's post-dispatch failure rolls back to old bytes, so unsaved typing is lost. M9 cannot see it (§9.4, §9.14 M9, L-md-protected)

- A document-level operation goes through the base drain. `MUTATION_OUTCOME_UNKNOWN` is in `RECOVERY_ERRORS` (`wsp/editor-shell/editor-session.js:15-22`), so the drain calls `_blockQueue(…, "recoverable-error")` (`:320-325`). No checkpoint is taken first. [src]
- Checkpoints are written only before selections and boundary moves, and only when the document is dirty (`editor-session.js:472-476`; `narrow-editor-v2-session.js:848-862`). Typing writes none. [src]
- The only exit is the page's 「回到檢查點」 → `session.rollback()` (`wsp/web/e2-editor-app.js:2389-2403`). That reopens the checkpoint if it is newer than the last save, otherwise the last saved bytes (`editor-session.js:163-167`). While the queue is blocked, save is refused. Autosave runs after 30 s idle, capped at 5 min (`e2-editor-app.js:92-94`). [src]
- So: type, then paste Markdown with the caret in a protected section. The paste does nothing (round-2 T2, 7 positions). Then the rollback discards everything typed since the last save or checkpoint. That is finding 119's failure, and its own comment describes it: "the queue blocked in recoverable-error with no checkpoint and the only exit reopened the last SAVED bytes -- everything typed since was gone" (`narrow-editor-v2-session.js:1001-1011`). [src][inf]
- §9.4 cites `narrow-editor-v2-session.js:1022` as support. That comment explains how `action()` *avoids* the base class's block. It does not show that a rollback is safe. [src]
- M9 opens a clean fixture, so "回到檢查點，文件不變" holds trivially. L-md-protected's 「不會掉資料」 is false for a dirty document. [inf]

Change, before pinning:
- **A (recommended).** `pasteMarkdown`'s operation runs `_checkpointBeforeBoundaryMove(document)` before dispatch. That is a no-op when the document is clean or already banked. The manifest's `rollback-to-checkpoint` then really returns to the pre-paste content.
- **B.** Use finding 119's mould instead: on a post-dispatch failure, `_checkpointBeforeBoundaryRestart`, then `restart-required`, then the page reopens if `restartKeepsContent()`. Under B the paste's uncertain effect is kept.
- Either way:
  - add **M9-dirty**: type a marker without saving, paste in the protected section, recover, save. The marker must be present. It is red on the implementation as specified.
  - Default if never done: the page has no entry.
- Optional, owner's call because it is new mechanism: refuse before dispatch when the last `.uno:Paste` state is disabled. 5 of the 7 native positions report `disabled` (round-2 README:66-72).

### A1 — SHOULD. The scan does not parse the bytes Writer parses: trailing NULs lead to a remote fetch (§9.3, §9.14 rule 1)

- Writer's input is `TransferableDataHelper::GetString`, which **strips every trailing 0x00** (`lo/vcl/source/treelist/transfer.cxx:1510-1515`). It then decodes with the thread encoding (`:1517`), goes through a UCS-2 stream (`lo/sw/source/uibase/dochdl/swdtflvr.cxx:2214-2243`), and is turned back into UTF-8 (`lo/sw/source/filter/md/swmd.cxx:915-923`). The markdown flavour is kept as raw bytes, NULs included (`lo/desktop/source/lib/lokclipboard.cxx:198-206`). [src]
- md4c ends a link destination at any control character (`md4c/md4c.c:2058`), and a reference definition fails if anything follows on the line (`:2227-2229`). [src]
- Consider `![a][r]` ⏎⏎ `[r]: http://host/x.png` followed by `\0`:
  - the scan sees no definition, so no `MD_SPAN_IMG`, and the input passes;
  - Writer sees the NUL stripped, so the definition is valid and the image is fetched (S03's path, natively `OPTIONS`+`GET`). [inf; not run]
- A textarea rarely holds U+0000. A direct SDK caller (L-md-sdk-callable) can pass it trivially. §9.3 claims SDK callers are covered.
- Change: the engine refuses any input containing 0x00 (`INVALID_ARGUMENT`) before the scan. That is a closed rule, and it makes the two inputs byte-equal when the encoding is UTF-8. Add the item above to the model test and to M5.
- The rest checks out [src]:
  - flags must be copied from `swmd.cxx:950-958`;
  - the UCS-2 round trip is lossless for TextEncoder output;
  - Writer reads attributes raw, without decoding entities (`lo/sw/source/filter/md/mdcallbcks.cxx:177-180`), so the scan must read `src.text[0..size)` the same way.
- Encoding: `osl_getThreadTextEncoding` = `nl_langinfo_l(CODESET)` of `LC_ALL`/`LC_CTYPE`/`LANG` (`lo/sal/osl/unx/nlsupport.cxx:562-612`, `:626-638`). The scan's verdicts depend on ASCII syntax. The exception is Unicode case-folded reference labels, which can diverge only when the encoding is not UTF-8. Write that the scan's guarantee to SDK callers assumes M2. [src][inf]

### A2 — SHOULD. `MARKDOWN_NEEDS_CARET` has no specified source, and every source available fails somewhere (§9.14)

The engine has two sources [src]:
- the callback cache, `gEditorState.selectionObserved`/`selectionRectangles`, written as callbacks arrive (`wsp/src/probe_engine.cpp:2602-2606`);
- `readSelection()`, a synchronous core read (`:3321-3341`).

`handleEditorAction` uses the cache only and fails closed while nothing has been observed (`:5514-5520`). C uses both (`:4020-4023`).

How each choice fails:
- **Cache only, fail closed.** Right after open or reopen nothing has been observed, and that gate refuses actions ("no selection has been reported yet", `findings/evidence/132/held-into-refusal/ruling/ruling-1.md:39`). M1 pastes into a just-opened empty document, so every M1 arm would be refused. The implementer will be pushed to fail open: "classifying without an observation" (`probe_engine.cpp:5508-5513`). [src][inf]
- **Cache only, fail open.** It misses a selection core holds but has not flushed, e.g. L-C-late-K1. [inf]
- **`readSelection()` only.** An empty text/plain selection, such as one covering only an as-char image, reads as `NONE` (`lo/desktop/source/lib/init.cxx:5988-6040`). A frame or graphic selection reads as `COMPLEX`. [src]

Change: define collapsed as `readSelection().type == NONE && !textMissing && (!selectionObserved || selectionRectangles.empty())`. Any other type is refused. Add arms:
- paste right after open, with no click;
- an image-only selection;
- a selected frame.

### A3 — NOTE. Worker init failing on a non-OK mask status (§9.7): no regression

- Its only runtime caller is `wsp/sdk/sdk-worker.js:1244-1256`. Tests and builders only name the symbol. [src]
- Every one of the 55 `dist/profiles/*` ships its own worker copy, and v21 is the only consumer of the new bytes. [src]
- Even repacked, every compile rule whose manifest carries `gestureBits` defines `OXSDK_E2_FORMAT_BARRIER` (`wsp/Makefile:643` … `:1552`), so no existing profile would fail. [src]
- Residual 1: the check sees only the external bound (`wsp/src/editor_api.cpp:175`). Leaving `kMaxInternalEditorAction` at 23 still returns OK (`probe_engine.cpp:7073-7077`). It is caught by D1, as a refusal. [src]
- Residual 2: an omitted `gestures` field is skipped (`sdk-worker.js:1248`) and an unknown gesture name gives mask 0. Both are silent. The SDK range arm covers move-document. [src]

### A4 — SHOULD. The `holdsDelete` rewrite (§9.8) can reopen 141 and still swallows presses

Today a press is held on `unanswered > 0 && sameKey` (`wsp/web/e2-editor-app.js:2712-2714`). **Any** settle drops **all** held presses (`:2716-2720`, `:2732-2747`). [src]

§9.8 anchors the rule at 「第一下尚未回答之後」:
- **Anchored at the first unanswered press, 141 comes back.** Sequence: Backspace at the start (C window), Ctrl+Home, then Backspace mashed or held without repeat flags. No press is held while any delete stays unanswered, so it queues N × 2.26 s. [inf]
- **Anchored at the latest send, presses are lost.** Sequence: Backspace(C), Ctrl+End, Backspace, Backspace. The fourth press is held behind the third, and the global drop at the *first* delete's standing no-op throws it away. [inf]
- **"Any other action" has no choke point in the page.** Sends go out through `editorAction` (`:2185`), `placeCaret` (`:2525`, `:3068`), `selectRange` (`:2426`), undo/redo (`:2860-2870`) and save, and typing goes through the frozen adapter. D8 tests Ctrl+End only. Today Backspace(C), a click elsewhere, then Backspace swallows that last Backspace. [src][inf]
- 144 is not reopened: the depth guard still counts `deletesInFlight`. 145 is not reopened, provided the new state is per send. [src][inf]

Change:
- Held presses belong to the send they wait behind, and only that send's settle drops or releases them.
- A press is held iff the most recent session enqueue is an unanswered same-key delete. Read this from a session-side enqueue counter, so every path counts.
- Add, red first on the 0.2.24 page where marked:
  - **D8b**: Backspace(C), Ctrl+Home, 18 unflagged Backspaces in 1 s. At most 2 delete requests reach the engine. Today: green; it must stay green.
  - **D8c**: Backspace(C), Ctrl+End, two quick Backspaces. Two characters are deleted. Today: red.
  - **D8d**: Backspace(C), a click mid-document, Backspace. It deletes at the click. Today: red.

### A5 — NOTE. `md_parse` link and header (§9.3)

- It resolves:
  - `libmd4c.a` is tokens 139 and 150 of `wasm-lite/build-headless-probe/instdir/program/soffice.js.linkdeps`, which `link_r5_product` passes (`wsp/Makefile:841-856`);
  - `llvm-nm` gives `T md_parse` in `libmd4c.a` and `U md_parse` in `libswlo.a`;
  - wasm-ld resolves archives regardless of order;
  - `-sERROR_ON_UNDEFINED_SYMBOLS=1` makes a miss loud. [src]
- `E1_CPPFLAGS` has no md4c `-I` (`wsp/Makefile:7-12`). Add `-I$(LOBUILD)/workdir/UnpackedTarball/md4c/src` to the v21 rule only. Put `#include <md4c.h>` inside `OXSDK_E2_V21_LINK_BATCH`, so older rules neither fail nor preprocess differently. Make `src/markdown_paste.hpp` a prerequisite of v21 objects only (finding 042). [src][inf]
- Never compile `md4c.c` into the engine. Writer and the scan would then run two parsers, and closure is lost. Assert that `what_the_link_ships` lists no md4c object among ours.
- Raw HTML: refusing it is closed against Writer's filter:
  - `InsertHtmlData` is reachable only from leaving `MD_BLOCK_HTML` (`mdcallbcks.cxx:131-132`);
  - `m_htmlData` is filled only by `MD_TEXT_HTML` (`:272-276`);
  - links, autolinks and wikilinks only set `SwFormatINetFormat` (`:164-173`, `:219-230`);
  - reference definitions only feed `MD_SPAN_A`/`MD_SPAN_IMG`. [src]

### A6 — SHOULD. The new refusal codes get a rollback disposition (§9.3, §9.14)

- `MARKDOWN_REMOTE_IMAGE`, `MARKDOWN_HTML_UNSUPPORTED` and `MARKDOWN_NEEDS_CARET` are not in `PRE_DISPATCH_CODES` (`wsp/editor-shell-v2/paragraph-editor-client.js:248-253`). `formatFailureDisposition` therefore returns `unknown-rollback` (`:336-342`), and `recoveryFor` returns `rollback` (`paragraph-editor-session.js:77`). [src]
- If the paste path applies `_withDisposition`, as `action()` does, the page appends 「可能已經改到文件：請回到檢查點」 to a refusal that touched nothing (`e2-editor-app.js:2098-2100`). That is finding 063's class. [src][inf]
- Change: put the paste's pre-dispatch codes in the pre-dispatch set (or attach `dispatched: false`). Unit-test every code the paste path can emit before dispatch → `recovery: "none"`, generating the list from `markdown_paste.hpp`.

## 3. Criteria with §9 applied

| crit | (a) a mutation that stays green | (b) form | (c) default if never done | (d) run-time judgement |
|---|---|---|---|---|
| D1 | a header/footer defect (zero arms) | tool-closed | stated; the SDK still offers 22/23 (name it) | when Z is typed after the reply |
| D2 | none found | fixed red case | stated | none |
| D2′ | none can turn it red at nominal timing (completion is by callback) | fixed case, **no positive control** | stated | none |
| D3 | readback deadline raised to 900 ms | fixed (superseded by D7) | stated | none |
| D4 | `moveFromPoint` clicks the anchor (plain-text `r-*` land the same) | subset of D1 | stated | none |
| D5 | Ctrl+End tests `offers("move-document-start")` | matrix (needs a single-withheld row) | stated | none |
| D6 | — | record | — | — |
| D7 | deadline 900 ms; reply and `get-state` both read the cache | tool-closed | **missing** | "has a cursor callback" window unpinned |
| D8 | the "other action" flag set only for Ctrl+Home/End | single instance | **missing** | none |
| D9 | unflagged repeats | single instance | **missing** | none |
| D10 | the page scrolls late after a stale reply | single fixture | **missing** | **when to read** |
| M1 | scan regressions (case-sensitive `data:`, old no-text rule) | tool-closed over round 1 only | stated | "remote" is a label |
| M2 | none | per instance | stated | none |
| M3 | SDK counts UTF-16 units or is off by one, masked by the engine's 64 KiB; no arm at 16 KiB | generated | stated | none |
| M4 | an Undo regression at P5 (list start) | **hand list** | stated | none |
| M5 | rule 2 dropped; the NUL bypass | **hand list** | stated | "0 requests" without a positive control |
| M6 | a pathological 64 KiB input | single | stated | none |
| M7 | none found | fixed | stated | none |
| M8 | per matrix | matrix | stated | none |
| M9 | rollback to the last save on a dirty document | fixed red case | only 「若紅」 | precondition (caret inside the section) unchecked |
| I1 | a relink rewrites a frozen profile outside {v8, v15, v18, v19, v20} | **hand list** for frozen hashes | stated | none |
| K | n/a | chain (J-a.2) | stated | §17.4 reading (pre-existing) |

**Fail 「驗收判準的形式」:**
- §2 (no default): D7, D8, D9, D10, M9 ("not done"), the dialog-cancel arm, S16.
- §2 (judgement at run time): D10.
- §1 (hand enumeration): M4, M5, I1's frozen list.
- §6 (no red case or positive control): D2′, and M5's network clause.

### C1 — SHOULD. Write the defaults (§9.7–§9.9, §9.12–§9.14)

- D7, D10, M9, the cancel arm and S16 → item not shipped, or the page has no entry.
- D8 → the page keeps today's hold, with **L-142-held-after-move** named.
- D9 → amend L-142-no-repeat: "a held key queues one 250 ms move per repeat when repeats are unflagged".

### C2 — SHOULD. One population for M1, M3 and M5 from the scan model (§9.6, §9.14)

- Run the natively compiled `markdown_paste.hpp` over the corpora of both rounds. Each item's verdict routes it: PASS → M1; REMOTE/HTML → M5; NO_BLOCK/oversize → M3.
- Today S14, S15, N1, W3, W4, S06–S13 and H1–H7 are in no WASM criterion. So a case-sensitive rule 1, the old no-text rule 3, or a missing rule 2 all stay green.

### C3 — SHOULD. Tie M3 to the operative limit (§9.2, §9.12)

- Arms at L and L+1, where L is the SDK limit in force (64 KiB or 16 KiB). Each asserts which layer refused: the SDK sends no worker request; the engine returns `INVALID_ARGUMENT` to a sent one.
- Keep the direct-engine 65,537.

### C4 — SHOULD. Generate I1's frozen set (§5 I1)

Hash every file under `wsp/dist/profiles/` and `wsp/build/archive/` before the link, and compare after, except `dist/profiles/e2-editor-v21/`.

### C5 — SHOULD. Make D9 independent of the repeat flag (§9.8)

- Drop a Ctrl+Home/End keydown while a move of the same key is unanswered. The cost is the same as L-142-no-repeat's.
- D9 runs with flagged CDP repeats **and** with unflagged presses 30 ms apart. Busy must end ≤ 500 ms after release.

### C6 — SHOULD. Pin D7 and D10 (§9.7, §9.9)

- D7: a silent press completes in < 500 ms (pins OD1's 250 ms; < 1000 ms admits 900).
- D10: read at the reply and again after 1 s of quiet; both must show the last page. Also apply D7's freshness clause on the 60-page fixture.

### C7 — NOTE. Positive controls

- **D2′:** register under CLAUDE.md §3 as "nominal-timing only". D6 is the only arm that can show the overtaking.
- **M5:** the same network capture must show the worker's own fetch of `probe.wasm`. Otherwise "0 requests" is vacuous.
- **M4:** generate positions by rule from the native position arms:
  - collapsed caret → M4 (adds P5, P2);
  - range → refusal arm;
  - protected → M9.

## 4. What a 0.2.25 user hits that nothing covers

- **D1 — SHOULD. Entities vanish.**
  - Writer ignores `MD_TEXT_ENTITY` (`mdcallbcks.cxx:297-300`), and md4c emits `&amp;`, `&lt;`, `&nbsp;` and numeric references as entities (`md4c/md4c.c:4409`). [src]
  - So `AT&amp;T` → `ATT` and `a &lt; b` → `a  b`. No corpus item contains `&` (grep, both rounds). [inf]
  - Options:
    - **A**: an upstream finding plus **L-md-entities**;
    - **B**: a fourth scan rule refusing any `MD_TEXT_ENTITY`, which is new mechanism (CLAUDE.md §4: owner's call).
- **D2 — SHOULD. Task lists create checkbox content controls, and a click toggles them.**
  - `- [ ]` → a checkbox content control (`swmd.cxx:501-530`). Clicking one toggles it, with an Undo action (`lo/sw/source/uibase/wrtsh/wrtsh3.cxx:135-160`). [src]
  - The product's click is `placeCaret`, a non-mutation, so `dirty` and autosave would not see the change. [inf]
  - The corpus has no task list (README:234).
  - Measure natively. Then either refuse `MD_BLOCK_LI_DETAIL.is_task` in the scan or name **L-md-task-checkbox**.
- **D3 — NOTE. Soft breaks become U+00A0** (`mdcallbcks.cxx:293-296`).
  - Hard-wrapped source becomes non-breaking joins, and CJK lines gain a visible space.
  - Name it with L-md-merge.
- **D4 — NOTE. L-md-no-html reaches further than `<br>`.**
  - Any `<word>` outside code is raw HTML to md4c: `List<T>`, `<your-name>`. The whole paste is refused.
  - Widen the named sentence and suggest backticks in the message.
- **D5 — NOTE.** Still unmeasured: GFM tables pasted into cells give nested tables, editing them meets 136's cell boundaries, and there are positions nobody has run (round-2 README:176). Keep L-md-unmeasured-positions with that list.

## Summary (10 lines)

1. BLOCKING B1: Markdown's `MUTATION_OUTCOME_UNKNOWN` goes through the base drain into `recoverable-error`, and rollback reopens a checkpoint or the last save. No checkpoint precedes a paste, so a protected-section paste on a dirty document loses up to 5 min of typing (finding 119 again). M9 is clean-only. Checkpoint before dispatch, and add M9-dirty.
2. SHOULD A1: Writer strips trailing NULs (`transfer.cxx:1510-1515`) and the scan does not, so a reference image followed by `\0` passes the scan and is fetched. Refuse 0x00.
3. SHOULD A2: `MARKDOWN_NEEDS_CARET` has no source. The cache fails closed right after open (M1 would be red everywhere), and `readSelection` folds image-only selections to NONE. Use C's conjunction and add three arms.
4. SHOULD A4: §9.8's "since the first unanswered press" reopens 141 on Backspace(C), Ctrl+Home, mash. With today's global drop, it still swallows presses after a click or a second Backspace. Make holds per send, keyed on a session enqueue counter; add D8b–d.
5. SHOULD A6: the three new refusal codes default to `rollback` (`PRE_DISPATCH_CODES`), so the page tells an untouched user to go back to the checkpoint.
6. NOTE A3/A5: the worker init check affects no existing profile, and `md_parse` resolves (T in libmd4c.a, which is in linkdeps). Add the md4c `-I`/`#include` under the v21 define. HTML refusal is closed against Writer's filter.
7. Review 1: 17 of 27 rows resolved. 10 are partial: B4/R3, S4/R4, S5, R6, S6/R5, S7, S12, S16, R8, R11. None is unaddressed.
8. Form failures: no default for D7–D10, M9, the cancel arm and S16; hand lists M4 (P5 omitted), M5, I1's frozen hashes; D10's read time; no positive control for D2′ or M5's network clause.
9. SHOULD C2–C6: route M1/M3/M5 by the scan model over both rounds (rule 2 and S14/S15/N1 have no WASM arm); tie M3 to the operative limit; generate I1's hash set; make D9 independent of the repeat flag; pin D7 < 500 ms and D10's read time.
10. 0.2.25 gaps: entities silently dropped (`AT&amp;T` → `ATT`), task-list checkboxes toggled by a non-mutating click, soft breaks become NBSP, `List<T>` refuses the whole paste.
