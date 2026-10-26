# Selection collector preparation 02 (uncounted): passive page-count read

Second uncounted preparation, same cell as 01 (Chrome, `shift-Right@caret-mid`), after the place-caret route correction `7872a89e`. Receipt `runner.command.json` (exit 1, 53 s). Readiness, both fresh opens, every point discovery, the reference arm, the candidate arm, the 500 ms delayed reads and the endpoint mapping all completed; the runner's inspection then returned NOT_ESTABLISHED, `unplanned wire operation`.

The operation was `pageRectangles`, three requests, one per open (generations 1/2/3), owned by no instrument call. It is the shell76 page-count scheduler's automatic read (`e2-editor-app.js` `PageRectanglesScheduler`). The engine handler `handlePageRectangles` (`src/probe_engine.cpp`) calls only `getPartPageRectangles`, `getDocumentSize` and `getParts`; it changes nothing. Shell57 under v19 never sent it, which is why the copied passive list lacked it.

Disposition: `pageRectangles` joins the reader's passive operation set, with its source reason in a comment. A new control keeps an extra passive `pageRectangles` request PASS and an unknown `pasteMarkdown` request NOT_ESTABLISHED (`unplanned wire operation`). 15/15 tests pass.

`reread-corrected-reader.json` re-reads this preserved page with the corrected reader and records the reader hashes: aggregate PASS, S1 PASS (logical anchor p1:11, endpoint p1:12, single-line native witness), S2 PASS (no stale fields, delayed read 501 ms after the terminal), S3 not applicable. This is one uncounted cell in one browser; it is not part of any population and establishes no group.

Raw cell: `chrome-shift-Right@caret-mid.json.gz`, SHA256 `5b407772…08a7` before compression and after decompression.
