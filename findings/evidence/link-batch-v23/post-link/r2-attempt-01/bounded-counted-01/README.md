# Bounded R2 counted population

This is the fixed-graph R2 bounded population after the clean N1 preparation. It contains 18 direct pages: smoke, proof, and hang in Chrome and Firefox for rounds 1–3. All pages are complete with no fatal payload. The pre-run refusal list and foreign CPU over-limit set are empty.

The reports bind profile `e2-editor-v23-diag-r2`, explicit WASM SHA-256 `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`, and fixture `plain-grapheme.odt`. Runner argv and displayed progress are preserved separately. The runner report confirms 18 cells; its interactive process wrapper did not retain the runner's numeric exit code.

The aggregate reader verified candidate identity, input and served-mirror bindings, fixture identity, actual user-agent/browser agreement, and all page criteria. It returned PASS with `populationComplete: true`, 18 direct pages, and 6 corrected-040 HTML-negative references from `040-counted-02/html-negative/report.json`; all 24 logical cells passed. Exact reader command arrays, exit codes, stdout, and stderr are in `reader-captures/`.

The independent observation auditor returned PASS for all 18 direct pages: 24 successful opens, 126 same-generation/same-handle accessibility witnesses, 6 proof events, and zero problems. The six corrected-040 references were separately audited with their own 040 report.

The aggregate and auditor outputs establish only this bounded population. Generated `mirror/` content is retained locally and ignored by this output directory's `.gitignore`.
