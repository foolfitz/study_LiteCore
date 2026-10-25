# Bounded R2 preparation, six direct cells

This fresh preparation followed the runner name-shadowing fix. It ran `smoke`, `proof`, and `hang` once in each browser with profile `e2-editor-v23-diag-r2`, fixture `plain-grapheme.odt`, and explicit WASM SHA-256 `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`. All six pages are complete and have no fatal payload. The pre-run CPU refusal list is empty.

The aggregate reader checked the runner's artifact identity, original input graph, served mirror graph, fixture binding, browser labels versus actual user-agent, and all page judges. All six direct page verdicts are PASS. The same corrected-040 HTML-negative report contributes six referenced `js-thread` observations, each PASS. The aggregate therefore reports `NOT_ESTABLISHED`, `directCells: 6`, `referencedCells: 6`, `populationComplete: false`, and no problems: this is preparation-only because the other twelve direct cells require the later N3 count.

The observation auditor independently returned PASS for the six R2 pages: eight successful opens, 42 same-handle accessibility witnesses, two correctly attributed proof events, and zero problems. Exact reader argv, exit codes, stdout, and stderr are preserved in `reader-captures/`.

Runner argv and displayed progress are preserved separately. Its report was produced after all six progress lines; the interactive process wrapper did not retain the runner's numeric exit code. Generated `mirror/` content is retained locally and excluded from Git by the output directory's `.gitignore`.
