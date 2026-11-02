You are the second review seat on a design that is about to be linked into a WebAssembly build of LibreOffice's Writer (a closed "ordered" engine driven from a browser worker). The link mints a new artifact, costs minutes, and cannot be cheaply undone. Find what is wrong. Read-only: do not edit, do not build.

Repo root is the working directory. Read, in this order:
- specs/SPEC-P-demo-batch-4.md section 5 (the design and the pinned criteria)
- wasm_sdk_probe/src/writer_caret_bridge.h and .cpp (new; the read)
- wasm_sdk_probe/src/ordered_format.inc: the blocks under OXSDK_E2_V32_PARAGRAPH_READ, especially startOrderedParagraphRead, resolveOrderedToggle, finishOrderedParagraphRead
- wasm_sdk_probe/src/probe_engine.cpp: grep OXSDK_E2_V32_PARAGRAPH_READ
- wasm_sdk_probe/editor-shell-v2/paragraph-editor-client.js: paragraphFormatShown, PARAGRAPH_READ_SHAPES, formatFailureDisposition
- wasm_sdk_probe/web/e2-editor-app.js: updateParagraphState, the heading menu functions, updateAlignAffordance; wasm_sdk_probe/web/e2-editor.html the toolbar block
- wasm_sdk_probe/tools/check_writer_toggle.py (the acceptance tool, not yet run against an engine)
- core source for reference: libreoffice-26-8/sw/source/core/unocore/ (unotext, unoparagraph, unocrsrhelper), sw/source/uibase/uno/unotxvw.cxx (getSelection), sw/source/uibase/app/docst.cxx (MakeInlineHeading)

Attack these, each with a concrete construction. Say "no defect found" for a section where you find nothing; do not pad.

1. Predicates. For each of crossIdentityHeld, crossStateHeld, toggleTakesOff, numberingHasNoEffect, paragraphMeets: construct a document and a press where the document ends up wrong and the predicate is green, or right and the predicate is red. Consider the empty-expectation semantics, `expectedListTag` values, lists whose level has NUMBER_NONE, headings in lists, numbered headings imported from DOCX (a list style other than "Outline" on Heading 1), a paragraph style that carries a list, style names on localized documents.
2. The read. What does XModel::getCurrentSelection return, in core, for: a caret in a footnote, a header or footer, a text frame, a comment; an image or shape selected; several table cells selected; a multi-range selection; a read-only section? Does the enumeration on a collapsed range always give exactly one paragraph, and the caret's? Can it throw, block, or be expensive on a large selection? Is anything here unsafe in a Writer build with only LOK callbacks on the engine thread (SolarMutexGuard re-entry, SfxLokHelper::getViewOfId with the current view, a stale view)?
3. Ordering. The read runs synchronously straight after postUnoCommand with no yield. Is the model guaranteed updated at that point for each of the commands used (.uno:DefaultBullet On=true, .uno:DefaultNumbering On=true, .uno:RemoveBullets, .uno:StyleApply, .uno:LeftPara and friends) under this engine's dispatch path? Native measurements used a 180 ms drain, so they do not prove it; v23 onward reads HTML at the same point. What would break if a command were asynchronous here, and would the verdict go red or silently green?
4. The widening. .uno:SelectText on a selection inside one paragraph, then StyleApply. Empty paragraph cases, a selection the routing called RangeSingle that spans a field or a footnote anchor, and the read of `before` after the widening. Is the selection left in a state the page handles? The page's lastSelectionShape, the toolbar.
5. The page. Any way the menu leaves focus stranded, stays open after the toolbar goes unavailable, or a press lands while the session is busy. Does the hidden-buttons approach break anything a user can reach (keyboard tab order into hidden buttons, the view-only gate, `applySessionAvailability`)?
6. The acceptance tool. Name each cell that cannot fail, or passes for the wrong reason. Name a defect in the engine change that no cell would catch.
7. Regressions on the five inherited actions, which now go through the new path on every route. What did the old read refuse that the new read lets through, and is that safe?

Report as a numbered list, most severe first. Each item: file:line, the construction, what happens, what you would change. Keep it under 80 lines.
