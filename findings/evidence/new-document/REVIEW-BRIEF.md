# Review brief: `check_m3_new_document.py` before it joins the count chain (§34.3)

Written 2026-10-14 by the main session, after the tool's acceptance run (`runs/2026-10-14T035226Z.json`, `NEW-DOCUMENT WORKS`) and the owner's hand test of 0.2.19. That acceptance run was the spec's own criterion for 0.2.19, an uncounted candidate (spec §4 "計數語意"); the next counted use is the overnight count chain after v20 is bound. This is the tool's one two-seat review (opus and codex, B′ form). Dispositions go in an appended section of `findings/evidence/new-document/README.md`, before the count.

## What to review

- `wasm_sdk_probe/tools/check_m3_new_document.py`: `score_run` (N1–N6), `score` (N8–N10, N12, the strict clauses and bindings), `RED_CASES` / `red_cases`, and what `run_once`, `host_static`, `repo_static`, `run_readonly` record for those rules to read.
- `specs/SPEC-M3-new-document.md` §4 (criteria table, the five pre-count amendments, counting semantics, bindings) and §7.1 (the verdict).
- `wasm_sdk_probe/tests/test_new_document_templates.py`, and the generator it tests (`gen.compare` is what N6 calls).

## Fixed questions (answer each with COUNTEREXAMPLE, NONE, or SHOULD)

1. **Find a broken product that this tool passes.** For each of N1–N6, N8, N9, name a host or engine defect whose report would read `WORKS`. Candidates to try: a template whose `styles.xml` is right but whose `content.xml` overrides the language with an automatic style (does N6 read only the default style?); a save that writes the marker into a different file than the one created (N4 reads `savedFile` by which path?); a reopen that lands on the editor with a cached engine copy rather than the saved bytes (N5 compares `fetched.sha256`; who fills it?).
2. **Find a working product that this tool fails.** In particular: N6's ≤ 1 mm paper tolerance against a template that writes 215.9 × 279.4 mm in inches; N4's `markCount == 1` when the user's own Templates hold an `.odt` that already contains `zqx`; N3's `opened.doc == run.name` when Nextcloud de-duplicates the name.
3. **Bindings that belong to 0.2.19 only.** N9 asserts "0.2.19 changed only the host" against 0.2.18's engine package and page (`CONTROL_BUILD_ID`, `CONTROL_PAGE_SHA256`, `CONTROL_HOST_COMMIT`), and the strict clauses bind `HOST_COMMIT afbaf3c` / `HOST_VERSION 0.2.19`. The next host is 0.2.20 (engine v20, shell v68). Which rules are properties of the 0.2.19 delta and will be red by construction on 0.2.20, which are recurring properties of "New document" that a count should keep, and is there a rule whose meaning silently changes when only the binding is updated?
4. **Non-vacuity.** A run whose `keys` list is empty, whose `reopen.a11y.offers` is missing, whose `checks.N10.validated` is 0, whose `readOnly` block is absent — each must not read `WORKS`. Find a vacuous report that does.
5. **Red-case coverage.** For each rule in `score_run` and `score`, name the entry in `RED_CASES` that exercises it, or say it has none (do the census; do not sample). Note that a mutation that raises is counted as a failure of the self-test, not as red.
6. **What the tool restores.** It switches the admin's `core/lang` and `core/locale` and must restore them (`settingsRestored`). Find a path (a dead browser, a `fatal`, a `KeyboardInterrupt`) where the owner's settings are left changed and the report still exists.

## What the reviewers do not need to decide

Whether the templates' defaults are the right defaults (spec §6, ruled); whether 0.2.19 works (§7.1 and the hand test); `Language=` and D12 (the next link batch).

## Rules for the seats

Read-only. Do not run the tool against the ddev instance (it changes the owner's settings and creates files); you may run `--red-cases` against the committed report and copy files to a scratch directory to try variants. For every block where you find nothing, say "no defect found"; do not pad.
