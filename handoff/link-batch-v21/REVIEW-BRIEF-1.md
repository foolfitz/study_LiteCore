# Review brief 1: SPEC-M3-link-batch-v21 (draft), two seats

You are one of two independent adversarial reviewers. The other seat gets the same brief, and you do not see each other's output. The repo is `/home/jiajun/LibreOffice/study_LiteCore`. **Read-only**: edit nothing, commit nothing, run no `make`, no browser. You may grep, read files and run read-only Python.

## What to review

`specs/SPEC-M3-link-batch-v21.md`. It is in zh-TW; translate it as you read. It specifies the next engine link (profile `e2-editor-v21`). It has three items:

1. **Finding 142.** New editor actions `move-document-start` and `move-document-end` (Ctrl+Home / Ctrl+End). They go on the key path, as wire ids 22/23 and internal ids 24/25. The editor ABI moves 4→5. They are collapsed-only, so on a range the page clicks first.
2. **Markdown paste.** A new document-level export, gated by a manifest declaration. The engine calls LOK `paste(doc, "text/markdown;charset=utf-8", …)`. Its postcondition is a change in the `.uno:Undo` payload.
3. **A manifest field that declares C.** C is the verified-boundary-noop after a 2.25 s window.

## Inputs you should read

- `handoff/PLAN-2026-10-16-link-batch-v21.md`
- The fact sheets in `handoff/link-batch-v21/facts-*.md`
- The native evidence in `findings/evidence/link-batch-v21/native/{142-ctrl-home-end,markdown-paste}/README.md`
- Sections §9–§17 of `specs/SPEC-M3-link-batch.md`, for prior rulings: §10.5 C, §14 ordered commands, §15.1 L-C-number-or-indent, §17.4
- The source the spec cites in `wasm_sdk_probe/src/`, `wasm_sdk_probe/sdk/`, `wasm_sdk_probe/editor-shell-v2/`, `wasm_sdk_probe/web/e2-editor-app.js` and `wasm_sdk_probe/tools/`
- The project's criterion rules: `CLAUDE.md`, section 「驗收判準的形式」 §1–§11

## Attack the criteria, not the conclusions

Asking "is this claim true" mostly gets the answer yes. Ask instead whether anything would tell us when it stops being true.

For each criterion in §5 (D1–D5, M1–M8, C1, I1, K):

- **(a) Find a mutation of the implementation that turns no criterion red** while the item is broken. Examples to try:
  - the engine completes Ctrl+Home on the wrong callback;
  - `kMaxInternalEditorAction` is left at 23;
  - `editorActionMutates` is not changed;
  - the paste postcondition always passes;
  - the page binds the key on a profile without the action;
  - the builder declares `boundaryNoop` without checking.

  Name the mutation and the criterion that should have caught it.
- **(b) The criterion's form** per CLAUDE.md §1. Is it per-instance, tool-closed, or a hand enumeration? If it is a hand enumeration, say what should generate the list.
- **(c) The default.** Is "if never done" written, and is it actionable?
- **(d) A future judgement** (CLAUDE.md §2). Does any criterion depend on a judgement made at run time?

## Also check against source

- **The key path.** Is it really the right dispatch for Ctrl+Home on the WASM engine?
  - Check `probe_engine.cpp` `handleEditorAction` and the select-all case.
  - Is the claim "unipoll ⇒ `postKeyEventAsync` processes the key synchronously" right (`libreoffice-26-8/sfx2/source/view/lokhelper.cxx` ~1270–1290)?
  - What does that mean for the native ordering surprise in the 142 README?
- **Collapsed-only.** Is the reason valid: range ⇒ `TEXT_SELECTION` first, so completing on the first callback serialises a stale caret? Is `moveFromPoint` really the existing range path?
- **Moves at the document boundary.**
  - Is `BOUNDARY_CAPABLE_MOVES` membership right?
  - Are there interactions with the page's delete holding (findings 141, 144, 145; `e2-editor-app.js` ~2700–2750)?
  - What happens with a held or repeated Ctrl+Home?
  - What happens with Ctrl+Home while C's window is open?
- **The Markdown postcondition.**
  - Can the `.uno:Undo` payload change without this paste, for example through an autosave or a concurrent callback?
  - Can it stay unchanged although the paste happened (an undo stack at its limit, an identical `dateTime`)? Read `merge_key_undo.hpp` `summarizeUndoPayload` / `judgeAfterKey` and what payload `getCommandValues(".uno:Undo")` really returns.
  - Is refusing whitespace-only input enough?
  - Is the 64 KiB limit and its pre-committed fallback (M6) well formed?
  - Is the remote-image default (M5) safe if WASM blocks for longer than 6 s?
- **Identity mechanics.**
  - The new v5 builder, with the v4 builder untouched. Is that right under finding 042?
  - X1's new `--declared-changed-leaf` flag.
  - Is anything the link changes not declared?
  - Read `tools/check_profile_identity.py`, `tools/build_e2_editor_v4_profile.py` and `wasm_sdk_probe/Makefile` around 1525–1603.
- **The C declaration.**
  - Is gating it on the wasm fragment meaningful?
  - Is leaving the four tools unchanged defensible under the project's §34 stop rule (`specs/SPEC-M3-paragraph-merge.md` §34)?
- **Anything missing.**
  - Is there a layer the spec forgets? For example: the worker's id table pin, `.d.ts` files, the shell bundle scope, E1-C, the merge runner `BINDING`, host packaging.
  - Is there a named limit that should exist but does not?

## Output

Write one markdown file to the path given in your invocation. Each finding carries:

- a severity: **BLOCKING** (the spec must change before implementation), **SHOULD**, or **NOTE**;
- the spec section;
- evidence as path:line;
- a concrete proposed change.

Label each claim **read in source**, **stated in a doc**, or **inferred**. End with a 10-line summary. Be terse. Do not restate the spec.
