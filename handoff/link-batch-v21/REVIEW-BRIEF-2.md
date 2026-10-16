# Review brief 2: SPEC-M3-link-batch-v21 after review 1. Two seats, last round

You are one of two independent adversarial reviewers. You do not see the other seat. Repo: `/home/jiajun/LibreOffice/study_LiteCore`.

**Read-only.** Edit nothing, commit nothing. Run no `make` and no browser. You may grep, read, and run read-only Python, including the evidence folders' own readers on scratch copies.

**This is the last review round** (precedent: `specs/SPEC-M3-link-batch.md` §12, 「不再有第三輪」). After it, the main session writes the dispositions, pins the criteria, and implementation starts. Spend your effort where a defect would otherwise reach the implementation.

## What changed since review 1

`specs/SPEC-M3-link-batch-v21.md` §9.1–§9.14 were appended. They are the dispositions of review 1 (`handoff/link-batch-v21/review-1-{opus,codex}.md`), the owner's three answers (§9.13), and the second native round (§9.14). Read the whole spec. §9 supersedes earlier sentences where it names them.

Scope is now two items:

1. Finding 142: `move-document-start` / `move-document-end`.
2. Markdown paste.

The C declaration was withdrawn (OD3).

New evidence:
- `findings/evidence/link-batch-v21/native/142-ctrl-home-end/d1-marker/` (D1 reference);
- `findings/evidence/link-batch-v21/native/markdown-paste/round-2/` (cells, header, a paste with no Undo action, the md4c classification, raw HTML fetch);
- findings 146–148.

## What to check

1. **Did each review-1 item get resolved, or only reworded?** For every BLOCKING and SHOULD in both review-1 files, point to the §9 text that disposes of it and judge it: **resolved**, **partially resolved** (say what is left), or **not resolved**. Make a table.
2. **The new mechanisms §9 introduces.** Check each against source for new defects:
   - **The engine's md4c pre-scan** (§9.3 and §9.14: three rules; header from `wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src/md4c.h`; `md_parse` already in the link).
     - Does linking our engine object against the core's `md_parse` actually resolve in the product link (`wasm_sdk_probe/Makefile` v20 block ~1525–1603, `$(cat $(LINKDEPS))`)?
     - Can the pre-scan and Writer's own parse disagree? Check flags (`swmd.cxx:951`), the input transformation Writer applies first (UCS2 → UTF-8 round trip, `swmd.cxx:898-960`), and the encoding (`osl_getThreadTextEncoding`).
     - Is "raw HTML → refuse" closed? Are there other md4c constructs that make Writer fetch (wiki links, autolinks, link reference definitions)?
   - **The worker failing init on a non-OK gesture-mask status** (§9.7). What else calls `oxsdk_editor_set_action_gestures`? Would any existing profile served with the new worker now fail init? Remember: the worker file is pinned per profile, so check which profiles would get it.
   - **The page change to `holdsDelete`** (§9.8: hold only if no other action was sent since the first unanswered press). Re-read findings 141, 144 and 145 and `web/e2-editor-app.js` ~2690–2770. Does this re-open 144 (a held delete inside text deleting many characters after release) or 145 (stuck accounting)?
   - **`MARKDOWN_NEEDS_CARET` (collapsed-only).** Where does the engine get "collapsed" from, and is it fresh at dispatch? Compare with how `handleEditorAction` reads its typed selection.
   - **`MUTATION_OUTCOME_UNKNOWN` for the Markdown post-dispatch failure** (§9.4). Trace what the session does with it for a document-level operation that is not an editor action: `editor-shell/editor-session.js` RECOVERY_ERRORS and `narrow-editor-v2-session.js` ~1022. Does the recovery restore the checkpoint, and does the checkpoint exist when the document was clean?
3. **Criteria form, one more time.** Use the criteria as they now stand: D1, D2, D2′, D3–D10, M1–M9, I1, K, with §9 applied. For each:
   - (a) a mutation that stays green;
   - (b) the form (per-instance / tool-closed / hand enumeration);
   - (c) the default if never done;
   - (d) any run-time judgement.

   Mark which ones still fail CLAUDE.md 「驗收判準的形式」.
4. **Anything a 0.2.25 user would hit that no criterion or named limit covers.**

## Output

Write one markdown file to the path given in your invocation. Each finding carries:
- a severity: **BLOCKING**, **SHOULD** or **NOTE**;
- the spec section;
- path:line evidence;
- labels: read in source / stated in a doc / inferred;
- a concrete change.

End with a 10-line summary. Be terse. Do not restate the spec.
