# Brief for fable — v24 pre-count: T4's rule 2, the Enter oracle, and tools bound by v23's cohort

Owner's decision (2026-10-28): these three questions go to fable. Read only the files named here; no repository-wide search. Repository rules on criteria are in `CLAUDE.md` (section 驗收判準的形式 §1–§10: the three forms, no rule moved after its run, append-only corrections, termination not carried by the drafter). The spec is `specs/SPEC-M3-link-batch-v24.md` (zh-TW; §6.3 criteria, §14–§15 corrections). Your earlier rulings for this batch: `findings/evidence/link-batch-v23/feature-protocol/s5-type-route-ruling/RULING.md` (ruling 1) and `RULING-2-abi.md` (ruling 2 + follow-up).

## Where v24 stands (all observed, evidence under `findings/evidence/link-batch-v24/pre-count/`)

| §6.3 item | Result | Evidence |
|---|---|---|
| (vi) stale v23 engine pair under the v24 manifest | init refused `DECLARED_EXPORT_MISSING`, both browsers, + control | `page-gates/README.md` |
| (vii) manifest without `typedInsert` | page refuses (`PAGE_BUILD_MISMATCH`), 0 `insertText` over three typing attempts, both browsers, + control | same |
| J-red (ii), (iii), (v) incl. T3's (v) | 36/36 checks; a route-only red (iii′) was added because (iii) alone is caught by both T2 clauses | `j-red/README.md` |
| (i) scratch SDK sends typed text down paste | T2 FAIL naming the route, both browsers; T1 alone would pass | `i-red/README.md` |
| M2 | 168/168 PASS (84 type cells × 2 browsers), 448 insert replies, 0 proof-absent | `m2/README.md` |
| T5 | 12/12 (typed 3/3 and Ctrl+V 3/3 per browser): typed A1 ``/B1 `x`; paste `A1 cell textx`/`B1 cell textx#` | `t5/README.md` |
| T4 | rule 1 PASS; **rule 2 FAIL as written**; one changed outcome diagnosed | `t4/README.md`, `t4/shift-enter-diagnostic.md`, `t4/read-01.json` |

Generation 77 is not frozen (spec §15: after §6.3 passes and no shell change is pending).

## Question 1 — T4 rule 2

Ruling 1 §3: "T4, per-instance over the existing paste/replace-selection/paste-markdown checks named from the closure: byte-identical expectations PASS on the successor. [NE]". The agent pinned rule 2 before the run (`t4/README.md`, commit `749a3f3f`): the set is generated from Chrome's wire record (every check whose step interval holds a paste-route `insertText` or a `replaceSelection`/`pasteMarkdown` request); each member must be PASS on v24 **and** equal to its v23 outcome (baseline `link-batch-v23/feature-protocol/product-four-arms-counted-01/{chrome,firefox}.json`).

Observed: 8 members. 5 are PASS and equal to v23 in both browsers. 3 were not PASS on v23 and are not PASS on v24: `a-boundary-arrow-press-does-not-cost-the-work` (Chrome FAIL both / Firefox NE both; `why`: "the second inducer never fired … auto-attach delivered no session for a document worker"), `clear-format-removes-every-inline-format` and `every-inline-format-reaches-the-document` (NE both; formats not all ON before the clear). Chrome leaf diff v23→v24 of those three entries: identical `why`/`notEstablished` text; only the profile name and millisecond timings differ. Nobody wrote what rule 2 says about a member that was not PASS on v23.

Asked: does T4 hold, and if rule 2 needs a correction, what exactly (form, default, and whether it counts as moving a rule after its run under CLAUDE.md §9)? The agent's leaning: for a member not PASS on v23, require the same outcome and the same reason text (leaf-equal except declared volatile fields: profile name, timings), recorded as an append-only correction citing this ruling.

## Question 2 — `the-enter-key-reaches-the-document` on v24

Chrome only (the check needs CDP). v23 PASS, v24 FAIL: the Shift+Enter arm has both markers in one paragraph with the paragraph count unchanged, but its oracle is the raw-XML substring `SHFTKEYA<text:line-break/>SHFTKEYB` (`wasm_sdk_probe/tools/run_e2_c_product_path.py:8724-8726`). Diagnostic `t4/shift-enter-diagnostic.md` + `shift-enter-diagnostic-02/` (the check's own steps replayed, both arms, the runner's caret helpers, real CDP Shift+Enter, saves kept): v24 2/2 saves `<text:span T1>SHFTKEYA<text:line-break/></text:span><text:span T2>SHFTKEYB</text:span>`, v23 0/2 (`SHFTKEYA<text:line-break/>SHFTKEYB`). T1/T2 carry only `officeooo:rsid` (two values; the check saves between the markers). The agent's reading: the typed route (Writer's keyboard insertion via `.uno:InsertText`) stamps typed runs with rsid spans as desktop Writer typing does; the break is there; the oracle only holds for the paste route's XML. The rsid-per-save explanation is inference; the XML is observed.

Asked: is this a product difference v24 must answer for (e.g. a named limit, or an S5/T1-style comparison against native Writer typing), or an oracle defect only? And what should the oracle be on v24 — given Question 3, since the oracle lives inside `main()` of a byte-bound file and cannot be changed by a wrapper.

## Question 3 — the 30 tool files bound by v23's counted cohort

`link-batch-v23/feature-protocol/counted-r1-s5-01/read-completion.py:38` asserts, for every path in the frozen config's `instrumentSources` (30 files; list in `cohort.json`), that the LIVE file's sha256 equals the frozen one. The list includes shared tools, not only v23's: `run_e2_c_product_path.py`, `build_e2_c_shell_bundle.py`, `run_browser_probe.py`, `v21_shakedown_common.py`, `v21_input.py`, `r7_support.py`, `web/serve.py`, among others. AGENTS.md already forbids editing two of them (`build_v23_native_s5_owner.py`, `build_v23_native_s5_type_owner.py`) for this reason. The cohort also archives `frozen-sources.tar.gz`. Spec §14.2 (V0′) set the precedent for the shell: v23 is re-read with the declared changed files restored to their generation-76 bytes, then put back.

What v24's remaining steps want from those files (checked by the agent today):

- **Freezing generation 77.** The handoff said "bump `MANIFEST` and add v76 to `FROZEN_MANIFESTS` in `tools/build_e2_c_shell_bundle.py`". Not strictly needed: the tool takes `--manifest e2/editor-shell-v2-bundle-v77.json --write --exclude PATH=REASON … --frozen-date …`, so 77 can be written with the tool unchanged (seven explicit exclusions: v76's six plus `sdk/v24-feature-worker.js`). But the default stays v76, and `make test-e2-c-reachability` (Makefile:4843, `python3 tools/build_e2_c_shell_bundle.py`) has been red since the v24 implementation — it reports `sdk/document-sdk.js` and `web/e2-editor-app.js` changed and `sdk/v24-feature-worker.js` unaccounted. The Makefile is not bound; that line could pass `--manifest`.
- **A4-v24 (the four product arms, §6.4).** On v24 they are NE (`judge_v23_product_four_arms.py:223`, "served sdk/document-sdk.js is not the reported shell generation") because `run_e2_c_product_path.SHELL_BUNDLE_V2 = PROJECT / build_e2_c_shell_bundle.MANIFEST` (`:2571`) is v76. A v24 wrapper could set `build_e2_c_shell_bundle.MANIFEST` before importing the runner (the T4 wrapper `tools/run_v24_t4.py` already re-binds `ChromeSession` that way) — no bound byte changes.
- **The Enter oracle (Question 2).** Only an edit to `run_e2_c_product_path.py` changes it in the product-path run; otherwise a separate v24 tool would have to replace that one arm's reading.

Options as the agent sees them:

- **(a) Never edit a bound file.** Everything v24 needs goes through new files and wrappers (77 via `--manifest`, Makefile passes it, A4 via a MANIFEST-rebinding wrapper, the Enter arm read by a new replay tool). Cost: every plain run of the shared runner keeps reporting v76 as "the shell" and the Enter check red, for good; wrappers multiply.
- **(b) Edits allowed, each one declared.** A list (in the v24 spec) of bound files changed after v23's cohort, with reasons; v23's completion re-read is then V0″ — the declared files restored to their frozen bytes (from git or `frozen-sources.tar.gz`), re-read, put back — exactly V0′'s method extended to tools.
- **(c)** something else you see.

The agent leans (b) for shared tools, keeping AGENTS.md's two native build scripts as they are.

## What the agent needs back

For each question: the decision, its form (CLAUDE.md §1), the default if it is never done, and any red case required before relying on it. If (b): what must V0″ show, and whether it has to run once per edit or once before each count. Whether generation 77 may be frozen now (shell changes pending: none known), and in what order relative to your answers.
