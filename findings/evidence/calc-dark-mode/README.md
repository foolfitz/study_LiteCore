# Calc inline-edit text under dark host palettes

The owner accepted the multi-cell formatting/autosave behavior and separately reported pale cell-edit text on the white canvas under browser dark mode. The actual Nextcloud global textarea rule supplies `var(--color-main-text)`; the Calc overlay had a white background without a text-color declaration. Commit `0515dfca` pairs that field with the page's fixed `--ink:#22312d`, caret currentColor and light native control scheme.

## Bounded observation

- `red-01/report.json`: before correction, Chrome light passes and dark fails, contrast 1.170734; the owned failed-run fallback cleanup is recorded, with unrelated locks untouched.
- `preview-01/report.json`: both Chrome and Firefox, both palettes, 12/12 checks; only the candidate source field rules are injected into the private page DOM.
- `installed-01/report.json`: actual installed host 0.2.38, no source-rule injection, 12/12. All four samples have text/caret/text fill `rgb(34,49,45)`, white background, light control scheme and contrast 13.590178. Normal owner-lock release; temporary resources removed; no fallback unlock.
- `../host-0.2.38/capture-after.py` additionally reads/asserts text-fill/caret/scheme, exact served build ID and installed archive identity. Its stored result also confirms fresh protected-document hashes, unrelated locks and shared ddev states unchanged.
- Claude's excerpt review and Astra's evidence-based disposition are retained as `REVIEW-01*`. The request omitted the existing causal red witness; the disposition records that limit explicitly.

The palette changes are private DOM variables using the actual loaded host CSS. This establishes the reported inherited-foreground defect and correction under these two palettes. It does not claim browser-extension auto-dark transformations, OS forced-color coverage, general CSS color parsing, or a full new Calc acceptance cohort.

## Installed identity

Host commit `fff18e48bda0a9606319ec5f24148854c9cec281`, version 0.2.38, package `5ad1f70a8c5f7d2f`. Only raw `ods-editor.html` changes: 45 of 46 complete package records are identical to 0.2.37. No JS/profile/native change or relink. Exact archive and rollback script are retained under the sibling release evidence/build archive; the owned staging worktree was removed after exact verification. The completed range/autosave gates remain closed. K remains deferred at nominal shipped 0.2.26, cumulative counters 47/27, with this CSS release adding 0/0.
