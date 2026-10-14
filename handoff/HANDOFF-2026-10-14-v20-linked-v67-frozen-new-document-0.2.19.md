# Handoff, 2026-10-14: v20 linked, shell v67 frozen, the first v20 shakedown passes; "New document" lands as host 0.2.19

This round continues `HANDOFF-2026-10-13g-v20-part2-and-review-6-landed-dispositions-pending.md`.

**Authority.** The owner said 「我授權fable代我做決定，Makefile 草稿也交給他」. This round, then, the Makefile answer went to fable as well (ruling 6 Q7). Linking stayed the owner's step, and the owner ran it. Pushing and deleting were not done.

The owner also asked for a new feature mid-round: 「我昨天人工測試的時候，發現沒辦法建立新文件，我希望可以在nextcloud中建立新文件」, to be done the way richdocuments and Collabora do it. After reading analysis 1 the owner chose **A**: 「範本寫明預設＋下批連結補 Language=」.

There are 48 commits, `3ac5045f..d98e57fa`, plus the merge-shakedown commits listed below.

## State

| item | state |
|---|---|
| Releases | Nominal shipped and counted: **0.2.12**. Uncounted candidates: 0.2.18 (page `b24d754a…`, shell v66, host `96a87d8`), and now **0.2.19** (host `afbaf3c`). 0.2.19 = 0.2.18 + "New document", with the same engine package (buildId `d6d04880f56e31da`, shell v66, engine v19). It is installed on the ddev instance and **waits for the owner's hand test**. |
| v20 | **Linked by the owner** (wasm `313b08d5…`, loader `e6b8c74a…`, worker `478d0da1…`, manifest `50aade86…`) and archived to `build/archive/e2-editor-v20-313b08d5-worker-478d0da1/`. Post-link checks all pass (`findings/evidence/link-batch/v20-post-link/`): v8, v15, v18 and v19 unchanged; the export is in the glue; `ScDocShell` 0; X1 v20 mode `VERDICT PASS`; M1-1 exit 0 on both bases. The engine source is final at `543a5566`. **Nothing is bound to v20 yet.** |
| Shell | Generation **v67 frozen** (`ac6267c8`, bundle `a3ee3e66…`, page `7815e16c…`, session `77841656…`). After the freeze, `make test-e2-c-static` exits 0 (332+5). It was witnessed before the freeze on v19 by 129-B in both browsers (54/54, 0 cells differ from three reference rounds; `findings/evidence/link-batch/v67-witness/`). `restore-window` needs the host and was **not** run on these bytes. |
| First v20 shakedown, part A | **VERDICT PASS** in both browsers (task 10-14e; `findings/evidence/link-batch/v20-shakedown/`; the main session re-ran the judge, exit 0, and the self-test, 0 failures). Results: P1-60 119/119; P1-mixed 15/15 (the engine string is byte-identical to native); P2 61 then 60 pages within 2 s; P3 no reads on scroll; C1 6/6 `verified-boundary-noop`, waitedMs 2252–2255, no selection left; E2 `caretBefore` equals the engine's last pushed caret every time. P2-c is `NOT_ESTABLISHED`, so finding 138 stays SHOULD and is already fixed in v67. E3 has no reachable instance; K was not run. §10.1's three counted product-path arms: **0 of 3 survive**, because all three need Shift+Arrow, which §13.3 withdrew. |
| First v20 shakedown, part B (merge shakedown) | Done in both browsers, uncounted (`83ea8eb8`, `1f93c11a`; `findings/evidence/link-batch/v20-shakedown/merge/`). **Only C29 and C30 differ from v19, as predicted:** they now complete `verified-boundary-noop` (generation `['1','1']`, about 2256 ms, documents = original + marker). The runner's `expectation()` still maps `nothing-selected` to a refusal, so those 4 records per report read `pass: false`. The main session checked that the failing records are exactly C29/C30 ×2 in all four shakedown and control reports. Everything else: 26 of 28 cases identical to v18; 101 kept documents per side have the same paragraph text as v18; no runner errors and no 重繪失敗 toast. M2-4: 105/105 `verified-key-undo`, keyToUndoMs [30, 32, 33] (v19 [30,32,36] / [30,32,33]). M2-1b: 20/20. `--pair` exits 1 in both browsers on one `toastsAtEnd` KB figure (14.2 vs 14.3), v19's known §35 cause. |
| New findings | **138**: a click on the caret's own line is reported placed by any callback. It reaches 0.2.12 and 0.2.18 through tile invalidations; fixed in v67 by condition 45. **139**: WASM lays out a long document lazily and emits no `DOCUMENT_SIZE_CHANGED` when done; the page number is right only through the paint-reply trigger. No fix today; it is a dependency to keep. |

## What was decided (all by fable on the owner's behalf, except where marked)

- **Ruling 6** (`findings/evidence/link-batch/review/ruling-6.md`, spec §15). It has two amendments.
  - **Q1 = A.** The residual **L-C-number-or-indent** covers three positions: Delete in front of a numbering label, and Backspace at the document start when the first paragraph is bulleted or indented. In those positions v20 waits about 2.25 s and does nothing; Writer would change the document. Only ordered-commands candidate A (the user's own key) closes it. The engine was not changed.
  - **Q2.** `placeCaret` acknowledges a click only when the sequence advanced **and** the caret position or the selection actually changed. This is a `NarrowEditorV2Session` override, because `editor-shell/` is E1-C-bound. The trigger on today's releases is finding 138.
  - **Q3.** A noop delete is not a mutation (`_enqueueOwned`).
  - **Q4.** After a failed page-rectangles read, the scheduler re-reads on the next state write.
  - **Q5.**
    - X1 gained declared-delta flags, recorded as a new use.
    - M1-1 gained per-carrier object sets, recorded as a repair with a witness. **Amendment 1:** E2_V20 = `probe_engine`, `sdk_api`, `editor_api`; `editor_api` differs by declarations only.
    - `what_the_link_ships` is data; it is blind to headers, which is now a named limit.
  - **Q6.** The Writer stack sweep runs after the link, in diagnostic directories that are deleted afterwards.
  - **Q7.** The Makefile block was applied with a corrected comment.
  - **Amendment 2.** Part 1 had one change outside the define in `finishMergeKeyError`. `543a5566` restored the old text there. v20's preprocessed `probe_engine` is unchanged (`8926e4cb…`), and M1-1 at base `82af92ca^` exits 0.
- **New document**, the owner's choice A, then twelve rulings by fable recorded in `specs/SPEC-M3-new-document.md` §6. In plain words:
  - only `.odt`; no `.ott` and no spreadsheet;
  - the Western language follows the user's Nextcloud language;
  - the Asian language follows the user's own language only for Chinese, Japanese and Korean users, and is zh-TW for everyone else;
  - paper comes from an explicitly set locale, otherwise from the region part of the language code, otherwise A4. The cost: a US `en` user with no locale set gets A4;
  - 30 static templates are generated deterministically;
  - when a write fails, the empty file is deleted first.

  The result is `NEW-DOCUMENT WORKS`: 4/4 cells, 29 red cases red, and `styles.xml` byte-identical between a zh-TW Chrome and an en-US Firefox.
- **Analysis 1** (`findings/evidence/new-document/analysis-1.md`):
  - LOK forces en-US at init, so a style-less document is Letter everywhere.
  - The Asian default follows `navigator.language`.
  - The default Asian font is `Noto Sans CJK KR` whatever the language.
  - `Language=` fixes the languages and the paper but not the fonts, and it needs a relink. It is queued for the next link batch, with finding 031's fix and the three fallbacks pinned.

## §34.4

- **Repaired because of execution: 9.**
  - M1-1 tool (witness `f4c1e7ac`): 1.
  - `test-e2-c-static`'s M1-1 invocation (witness `test-e2-c-static-red-default-carriers.txt`): 1.
  - The new v20 shakedown runner on its first runs (`77fafb75`, `b9ec221d`, `feeb96d1`, `4ad0c638`; each witness committed first): 4.
  - The new new-document runner before its count (`b893e7bf` and two earlier instrument faults in spec §4): 3.
- **Repaired because of review: 0.**
- **Extended for a new identity (not a repair):** X1. **Data:** the `what_the_link_ships` variant.

## Uncounted changes since 0.2.12 (for the next count)

- 0.2.13–0.2.18, as listed in earlier handoffs.
- **0.2.19:** "New document".
- **v20 with v67:** page number, C, `caretBefore`, conditions 45, 47 and 48.

## Next (in order)

1. **The owner hand-tests 0.2.19.** Steps:
   - in Files, "+ New → 新文字文件" (the picker appears because the owner's Templates folder holds 11 `.odt` files; "Blank" is preselected);
   - type, save, reopen;
   - optionally open the file in desktop LibreOffice and check A4 and Chinese (Taiwan).
2. **Before binding v20, change the merge runner's expectation for C29/C30** (§10.7's re-expectation under C). Today `run_merge_wasm_shakedown.py`'s `expectation()` maps `nothing-selected` at a document end to a refusal. Under C it is `verified-boundary-noop`: generation unchanged, no toast, document = original + marker. The §34.4 witness is part B's four honest reports (`v20-shakedown/merge/shakedown-*.json`, `control-*.json`). The change moves the runner's sha256, so it lands before `BINDING`. It also counts as repaired because of execution +1.
3. **A host candidate carrying v20 and v67**, as 0.2.20 on top of 0.2.19: package the engine with the v20 profile and the v67 page, then run §10.7's host arms. Those are `judge_held_into_refusal.py:266–282` and `restore-window`, with the new expectations: 0 refusals, generations `['1']`, the document and caret unchanged, the marker at the caret. Each one's first v20 run is its §34.4 witness.
4. **§34.3 reviews before first counted use.** Two new judges need a one-time two-seat review: `judge_v20_shakedown.py` (brief written: `v20-shakedown/REVIEW-BRIEF.md`) and `check_m3_new_document.py`. M1-1's extension and X1's flags are not new judges.
5. **Bind v20, then run the full count chain overnight**, detached from the session. Before that, settle:
   - the chain's abort rule;
   - 135's C2 semantics;
   - the release text: finding 137's three effects, L-C-late-K1, L-C-number-or-indent, and 138 fixed;
   - pin rebinding for the nine runners.
6. **Later:**
   - the Writer stack sweep (condition 52);
   - the ordered-commands spec;
   - `Language=` in the next link batch, with 031's fix and pinned fallbacks;
   - new-document's D12 (Letter versus A4 for `en` once `Language=` exists).

## Subagents this round (roles; not reachable from a new session)

- **fable, judge:** ruling 6 and amendments 1–2.
- **fable, analyst:** new-document analysis 1.
- **fable, executors:**
  - the page fixes (`aeaf92c0`..`b110834f`);
  - new document (`503263d2`, `b893e7bf`, `dda99342`; host `afbaf3c`);
  - v20 shakedown part A (`1ac40425`..`7df0b995`).
- **sonnet, executors:** the checks (X1, M1-1 extension, `what_the_link_ships`), the v67 witness, and the merge shakedown (part B).
- **Main session (opus 5.5):** the briefs, the condition-56 engine edit, the Makefile static fix, the v67 freeze, the runbook, the post-link checks, findings 138 and 139, spec §15, this handoff.

---

## Addendum (after `8bd7e700`): the hand test passed, Markdown is decided, finding 140 is fixed and waits for the v68 freeze

The commits are `defb4686..ab845a12`.

### What happened

- **The owner hand-tested 0.2.19 and it passed** (`defb4686`; `findings/evidence/new-document/hand-test-2026-10-14/`). The owner saved from Firefox and from Chrome. Both saves are A4, en-US / zh-TW / hi-IN, Liberation Serif / Noto Sans CJK TC / Liberation Sans, with `styles.xml` byte-identical (`5addf7dc…`). The documents themselves are not committed, because they are the owner's personal content.
- **Markdown paste: the owner chose A**, an explicit 「貼上為 Markdown」 command; Ctrl+V stays plain text. This is LibreOffice 26.x's own behaviour: Paste Special → Markdown, with the heuristics removed in tdf#171481, and Collabora follows it in cool#15535.
  - Our WASM core has md4c and the sw markdown filter compiled in.
  - The engine hard-codes `text/plain` at `probe_engine.cpp:3239`. A fix therefore needs an engine change, and it goes into the **next link batch**, together with `Language=` and 031's fix.
  - Notes and a draft scope: `research/RESEARCH-2026-10-14-markdown-paste.md` (`f3999ead`).
- **The "slow paste" was not the paste** (task 10-14f, `72cd5e41`, `findings/evidence/paste-latency/`).
  - The owner reported 「大概十幾秒，兩個都慢，處理中一直亮著」.
  - The paste itself is one engine `paste()`: 7.5–24.8 ms for 40 paragraphs.
  - The cause is the click before it. On a blank document, a click below the first line makes `placeCaret` wait its full **30.0 s** timeout, because the caret cannot move and the clicked line does not exist. The paste queues behind that wait.
  - Registered as **finding 140** (`b05f081b`). It is 052's residual, met on the first click. 052's register said `editorPlaceCaretV2` closed it, but only a harness page ever called that.
- **Finding 140 was ruled A and fixed** (`6c761117`) by the fable that diagnosed it, on the owner's instruction 「給fable」 「可以給同一個fable subagent嗎」.
  - The product's `placeCaret` (the v2 override) now asks the engine through `editorPlaceCaretV2`. Both v19 and v20 export it, so no link is needed. It judges the answer with 138's predicate, and keeps 048's 400 ms grace before it accepts "the engine answered, the caret stayed". v67's polling stays as the fallback for BUSY and UNSUPPORTED.
  - Tests: 425/425; the new `place-caret-blank-page.test.mjs` had 7 of 13 cases red on v67 first.
  - E1-C intact.
  - Witness: it was red first, at 30,007 ms on v20. The fix resolves in 405.9–412.8 ms on v19 and v20, in both browsers; the paste is sent 1–2 ms after its event.
  - Named limit: a click that the core processes more than 400 ms after the request is accepted with the old caret. This is the same bound as the existing identical-point grace.
  - The main session re-ran the tests and the E1-C check.
- **The pre-v68 witness is running** (task 10-14g, sonnet): 129-B in both browsers on the candidate bytes, which are the session `fc5ac883…`, with the page unchanged at `7815e16c…`. Criterion: 54/54 cells, with 0 differing from the reference rounds and from the v67 witness round `round-20261014T022210Z`. Output: `findings/evidence/link-batch/v68-witness/`.
- **§34.4 for this addendum.** `probe_paste_latency.py` and `tables.py` were extended with a "click resolved" field. That is a new probe's first use, not a repair. Repaired because of execution: 0. Repaired because of review: 0. The round total stays execution 9, review 0.

### State changes against the table above

- **Shell:** v67 is frozen. The **v68 candidate** is the v67 bytes plus finding 140's change to `editor-shell-v2/narrow-editor-v2-session.js`, `narrow-editor-v2-client.js` and `paragraph-editor-client.js` (and their `.d.ts` files). `dist/` currently holds the candidate session (`make e2-c-assets`), so `make test-e2-c-static` is red on the manifest until v68 is frozen. That is expected.
- **Uncounted changes since 0.2.12:** 0.2.13–0.2.19, v20 with v68 (page number, C, `caretBefore`, conditions 45, 47 and 48, finding 140).

### Next (replaces the list above, in order)

1. **Read the v68 witness** (`findings/evidence/link-batch/v68-witness/README.md`). If it passes, freeze **v68** as `ac6267c8` froze v67:
   - in `tools/build_e2_c_shell_bundle.py`, point `MANIFEST` at `e2/editor-shell-v2-bundle-v68.json`, with a comment that names finding 140 and the witness;
   - run `python3 tools/build_e2_c_shell_bundle.py --write --frozen-date <date>`;
   - check that `problems` is `[]`, that `make test-e2-c-static` exits 0, and that E1-C is intact.

   If a cell differs, that is a product question for fable, not a check change.
2. **Merge runner, C29/C30 re-expectation under C**, before binding v20. The witness is the part B reports. This counts as repaired because of execution +1.
3. **Host 0.2.20** = 0.2.19 + an engine package with the **v20** profile and the **v68** page.
   - **Ask the owner before installing**, because it replaces the engine they use daily.
   - Then run §10.7's host arms (`judge_held_into_refusal.py:266–282`, `restore-window`) with the new expectations.
4. **§34.3 two-seat reviews before first counted use:** `judge_v20_shakedown.py` (its brief is written) and `check_m3_new_document.py`.
5. **Bind v20, then run the full count chain overnight**, detached from the session. Settle first: the abort rule, 135's C2 semantics, the release text (137's three effects, L-C-late-K1, L-C-number-or-indent, 138 and 140 fixed), and the pin rebinding.
6. **The next link batch:**
   - `Language=` with 031's fix and the three fallbacks pinned;
   - **Markdown paste (A)**;
   - new-document's D12.

   Separately: the Writer stack sweep and the ordered-commands spec.
