# Formal timing12 population

The fixed R2 `largest` and `workload` arms each ran in Chrome and Firefox for rounds 1–3, producing 12 complete pages. Both reports bind the explicit WASM SHA-256 `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`; all runner pre-run refusal arrays are empty and foreign CPU checks passed.

The actual timing aggregate reader returned PASS with all 12 cells present. The observation auditor returned PASS for both reports: 12 pages, 18 successful opens, 1064 same-generation/same-handle accessibility witnesses, and zero problems. The literal workload-input auditor returned PASS for all six workload pages. It confirms the actual `pasteMarkdown` request payload is 65,536 UTF-8 bytes and its SHA-256 matches `page.markdown`; it also confirms the actual mirrored `long60.odt` members match `create_long_document.build(60)` while ignoring ZIP metadata.

The full reports retain every timing step, raw worker reply, long-document save, verified changed merge, layout window observation, and first reply after merge. Exact reader argv, exit codes, stdout, and stderr are preserved under `reader-captures/`. Runner argv and displayed progress are separately recorded; the interactive process wrapper did not retain runner numeric exit codes. Generated mirror trees remain local and are excluded from Git by this directory's `.gitignore`.
