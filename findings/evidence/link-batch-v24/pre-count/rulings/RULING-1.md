# Ruling 1 (v24 pre-count): T4 rule 2, the Enter oracle, v23-bound tools

Fable, 2026-10-28. Read-only: no build, browser, native process, write, or repository-wide search. "Checked" below means I verified it by reading the named file or running a short read-only command; where I took the brief's word I say so.

## SUMMARY

**Q1 — T4 rule 2.** Rule 2 as pinned is *unsatisfiable* for a member that was not PASS on v23: "PASS on v24 **and** the same outcome as v23" has no satisfying value when the v23 outcome is FAIL or NE. An unsatisfiable clause measures nothing about the product, so correcting it loosens nothing the product could ever have met — but it is still a rule written after its run, and CLAUDE.md §9(1) therefore bars run 01 from being the run that satisfies it. Correction (append-only, citing this ruling): rule 2 splits into **2a** (v23 PASS → v24 PASS) and **2b** (v23 non-PASS → identical outcome *and* identical check entry leaf for leaf, except a pinned, fail-safe list of timing/identity leaves). T4's verdict is taken from **run 02**, which Q2 forces anyway; run 01 stays as the record of rule 1 PASS, 2a 5/5 in both browsers, and the three members that forced the correction. Default if never done: unchanged — T4 NE, v24 may not claim "paste unchanged".

**Q2 — `the-enter-key-reaches-the-document`.** Oracle defect, not a product regression — and the "as desktop Writer typing does" half is now an **observation**, not an inference: in M1's native saves the keyboard arm and the `.uno:InsertText` arm both produce exactly one `officeooo:rsid` text style in all 16 shape×text pairs, 3/3 rounds (checked today, `m1-run-01/saves/`); v23's paste route produced none (0 in the v23 save, 4 in the v24 save). The rsid spans are a **declared difference in saved output** — not a limit — to be registered in spec §10 and the release notes, with a small reader over the existing M1 saves as the evidence. No new native comparison is needed. The oracle must read the paragraph *through* `text:span` (line-break → `\n`); it is a nested function inside `main()` of a bound file, so it is edit **E1** under Q3.

**Q3 — the bound tool files.** **(b′)**: an edit to a v23-bound shared tool is allowed only when (1) forced by a named fact that a wrapper cannot repair without new mechanism, (2) declared in a machine-readable list *before* the edit, (3) witnessed per §34, and (4) followed by **V0″** — V0′ extended to tools: the declared files restored to their frozen bytes, `counted-r1-s5-01/read-completion.py` exit 0 with the recorded verdicts, files put back, hashes checked. Spec §5.4 is corrected by append (as §14.2 corrected V0). Authorised now, as a closed list: **E1** (`tools/run_e2_c_product_path.py`: the Shift+Enter oracle and its payload, nothing else) and **E2** (`tools/build_e2_c_shell_bundle.py`: `MANIFEST`→v77 and `FROZEN_MANIFESTS` += v76, in the same commit that writes v77). The two native build scripts stay untouched (doubly bound; AGENTS.md). V0″ runs after every declared edit and again as the preflight of every §6.4 count.

**Generation 77: not now.** Order: write the corrections → reader red cases → E1 + its witness + V0″ run 1 → T4 run 02 (both browsers) → T4 verdict → the freeze commit (E2 + `e2/editor-shell-v2-bundle-v77.json` with the seven explicit exclusions + digest equal to the candidate `56ce44c7…` + `make test-e2-c-reachability` green + V0″ run 2) → §6.4.

**Two corrections to the brief** (details §0): (i) `product-four-arms-counted-01/cohort.json` *also* binds 24 of these tools (verified at completion by `post-inputs.json`, no live assertion), and two of them — `judge_v23_feature_selection.py`, `v23_feature_selection_cases.py` — already differ from that cohort, moved between 11:40 and 13:36 on 10-27, before v24; so only `counted-r1-s5-01/read-completion.py` asserts live hashes, and "bound tools never move after a counted cohort" was already untrue in this tree. (ii) `read_v24_t4.py` was committed *after* run 01 (dfc66261, 14:05); what was pinned before the run (749a3f3f 13:41:36; Chrome run start 13:41:41) was the rule text and the wrapper. Both are facts to record, not faults.

## 0. What I checked, and what I found

- **T4 run 01**: `read-01.json` — rule 1 PASS: 41 `insertText` requests (23 `paste`, 18 `uno-insert-text`), 0 problems, 0 unattributed, `stored: 0`. Rule 2: 8 members generated from the wire; 5 PASS/PASS in both browsers; 3 not PASS in either. Rules commit 749a3f3f at 13:41:36; `chrome/steps.json` first line 13:41:41, Firefox 13:55:50–14:04:32. Reader `read_v24_t4.py` first appears in dfc662613 (14:05:21).
- **The three members, leaf-diffed by me** (v23 `product-four-arms-counted-01/{chrome,firefox}.json` vs v24 `t4/{chrome,firefox}/report.json`): Chrome `a-boundary-arrow-press-does-not-cost-the-work` FAIL→FAIL, identical `why` ("the second inducer never fired … auto-attach delivered no session for a document worker"), 3 of 52 leaves differ: `/observed/offered/profile`, `/observed/placed` ("定位游標 60 ms"→"57 ms"), `/observed/presses[1]/seconds` (4.12→4.11). `clear-format-removes-every-inline-format` NE→NE, 0 of 23 leaves differ, identical `notEstablished`. `every-inline-format-reaches-the-document` NE→NE, 10 of 395 leaves differ, all `formatPressLatency` (strings like "B 27 ms") or `formatPressWaitedMs` (403→402); **its `why` and `notEstablished` are both null in both products** — the reason is not recorded as text for this member. Firefox: 3/37, 0/23, 11/395 with the same leaf names; the boundary check is NE in Firefox with identical `why` ("the page never took the boundary key").
- **The Enter check on v24 Chrome**: Shift arm `paragraphsBefore` 12 = `paragraphsAfter` 12, `together` true, `firstLanded`/`secondLanded` true, `lineBreaksBetween` false, `ok` false; the check's `why` is `None` (the FAIL carries no payload). Oracle at `run_e2_c_product_path.py:8724-8726`: `f"{first}<text:line-break/>{second}" in content` on raw content.xml; `paragraphs_of` (8683-8691) already parses the XML with ElementTree and `itertext()`, which flattens spans but drops the empty `<text:line-break/>` element. Both live in `enter_arm`, nested inside `main()` (`def main` at 4491; the check at ~8693-8775). `capture_save` is module-level (4057). The only other raw `line-break` oracle is 7269 (`the-edit-buttons-do-what-they-say`, presence anywhere — span-safe, and a PASS member of rule 2).
- **Diagnostic 02** (`--replay --repetitions 2`): v23 shift arm `literal: true` ×2 with `SHFTKEYA<text:line-break/>SHFTKEYBE`; v24 `literal: false` ×2 with `<text:span T1>SHFTKEYA<text:line-break/></text:span><text:span T2>SHFTKEYB</text:span>E`. I opened the saved ODTs: v24's T1–T4 automatic styles carry only `officeooo:rsid` (T1 `0005e7d8`, T2 `00070e01`); `officeooo:rsid` occurs 4× in the v24 content.xml and 0× in v23's.
- **M1 native saves** (`s5-type-route-ruling/m1-run-01/saves/`, 228 files): for every shape × text that has both arms (cell-caret, text, doc-end, table2, table4 × x, xy, cjk, e-acute, teh), the `key` arm and the `uno-insert-text` arm have the same `officeooo:rsid` count (1) and the same `<text:span` count (1 for text/cell-caret/doc-end, 0 for table shapes) in all 3 rounds. The emoji text has no key arm (non-BMP cannot be a vcl key). This turns the diagnostic's rsid inference into an observation on the existing evidence.
- **Bindings**: `counted-r1-s5-01/cohort.json` (createdAt 10-27 13:36, gitHead `ca91d148`): 30 `instrumentSources`, all SAME as the live tree today; 10 `prerequisites` SAME, including `frozen-sources.tar.gz` (45 members: `instrument/` 30 + `served/` 15). `read-completion.py:37-39`: config sha first (`'live frozen plan differs'` — the shell), then every instrument `assert file_sha(...)==want,path` (payload = the path), then prerequisites. `product-four-arms-counted-01/cohort.json` (10-27 11:40, gitHead `48b372bf`): 24 `instrumentSources`, 22 SAME, 2 DIFF as stated above; its README's re-read is `judge_v23_product_four_arms.py <dirs>`, no live-hash assertion. `s5-native/run-03/identity.json`: 12 sources all SAME, including `build_v23_native_s5_owner.py` and `build_v23_native_s5_type_owner.py`.
- **MANIFEST couplings**: `build_e2_c_shell_bundle.py:783` `MANIFEST = v76`; `FROZEN_MANIFESTS` (106-146) ends at v75; `--manifest` defaults to `MANIFEST` (936); the tool's own guard text (1022) says "bump MANIFEST and add this one to FROZEN_MANIFESTS". Runner `:2571` `SHELL_BUNDLE_V2 = PROJECT / _shell_bundle.MANIFEST` with the comment "follows every freeze without anyone remembering to move it"; consumers 2658, 2681, 2702. `v23_product_four_arms.shell_graph` (190-201) reads `bundle.MANIFEST` at run time. The v23 four-arm judge resolves its manifest from the *identity it reads* (`manifest_path = repo / str(shell.get("bundle"))`, :211), and `v23_feature_selection_cases.identity()` (484-500) uses hard-coded `BUNDLE`/`BUNDLE_FILE_SHA256`/`PAGE_SHA256` — so E2 cannot redden v23's four-arm re-read or the R1/S5 config check; it only changes `build_e2_c_shell_bundle.py`'s bytes (a declared instrument drift). `Makefile:4843` runs the tool with no `--manifest`.
- **Shell state**: v76 includes 13 paths (incl. `sdk/document-sdk.js`, `web/e2-editor-app.js`), excludes 6 (`sdk/sdk-worker.js`, `reader-shell/reader-session.js`, `reader-shell/state-machine.js`, `sdk/v23-diagnostic-worker-tail.js`, `sdk/v23-diagnostic-r2-worker-tail.js`, `sdk/v23-feature-worker.js`). v77.json does not exist; `sdk/v24-feature-worker.js` exists (80,287 bytes). Cutover README: candidate digest `56ce44c78043220e4f135343dc87a8e847e83849e4c6571345b1ac9e2e8a294a`, 13 paths. V0′ was run at 10:23 and 11:03; each output landed within the minute, so a V0″ run costs about a minute.
- **Spec**: §5.4 pins "v24's instruments are always new files, never edit v23's; V0 proves it" — (b′) needs an append correction. §6.1 V0's default is "stop: a bound byte moved, find and restore it". §15 orders 77 after §6.3 including T4, before §6.4, with 7 explicit exclusions. §10 lists limits (L-typed-no-autocorrect, L-169, L-168, L-typed-line-break). Handoff 10-28d line 10 itself prescribes "add v76 to FROZEN_MANIFESTS and bump MANIFEST" — an edit of a bound file.
- **Uncommitted in the tree**: `findings/evidence/link-batch-v24/pre-count/m1-rerun/run-02/` (14:28–14:40; the §10 M1 rerun work item, I assume; not read). Check `pgrep` for anything native or browser-driven before E1 and before run 02 (measurement-in-progress rule).
- **Not re-read by me**: `odt_paragraphs.py` (the S5/T1 comparator); `read_v24_t4.py` beyond its header; the Firefox run's stderr. Nothing below depends on them.

## 1. Question 1 — T4 rule 2

### 1.1 Finding

Rule 2's text binds two conditions with "and": PASS on v24, and equal to the v23 outcome. For a member whose v23 outcome is FAIL or NE the conjunction is false for every possible v24 outcome. That is not a criterion the product failed; it is a clause with no pass case, and nobody noticed because ruling 1's T4 wording ("byte-identical expectations PASS on the successor") silently assumed every paste-route check had passed on v23. Three had not — one for an instrument reason recorded as FAIL (CDP auto-attach), two because a precondition (all four formats ON) did not hold on v23 either. The agent was right not to reinterpret and to send it here.

Rule 1 (per request) and the five v23-PASS members of rule 2 are unaffected: 41/41 requests carry a route, one reply each, `ok`, `method == route`, both routes present; 5/5 PASS→PASS in both browsers.

### 1.2 Decision: correction of rule 2 (append-only)

Append to `findings/evidence/link-batch-v24/pre-count/t4/README.md` a section "Correction 1 (ruling 1, v24 pre-count)" that replaces rule 2 with:

- **Population** (unchanged, form two): every check id whose step interval holds an `insertText` with `route: "paste"` or any `replaceSelection`/`pasteMarkdown` request, generated from Chrome's wire; Firefox uses Chrome's set; repeated ids compared as ordered lists. Non-vacuity: the set is non-empty **and** contains at least one member whose v23 outcome is PASS; otherwise T4 is NE.
- **2a** — for each member whose v23 outcome (same browser) is PASS: the v24 outcome is PASS. Anything else → FAIL for that member.
- **2b** — for each member whose v23 outcome is not PASS: the v24 outcome equals the v23 outcome, **and** the check entry's leaf map (every `path → value` after flattening the JSON) equals v23's except for leaves on the volatile list below. An outcome change in *either* direction (including NE→PASS or FAIL→PASS) and any differing non-volatile leaf → FAIL for that member. An improvement is a behaviour change on a paste-route check and is explained by an append-only note naming its cause, never waved through by the reader.
- **Volatile list** (pinned now, by key name — the last path component): `profile`, `placed`, `seconds`, `formatPressLatency`, `formatPressWaitedMs`. Nothing else.
- **Payload**: for every red member the reader prints the member, the rule (2a/2b), both outcomes, and each differing non-volatile leaf as `path | v23 value | v24 value`.
- Rule 3 (payload-byte checks seeing `route: "paste"`) is unchanged.

Why leaf equality rather than "same reason text" (the agent's first instinct in the brief): for `every-inline-format-reaches-the-document` both `why` and `notEstablished` are null in both products, so a reason-text rule would compare null to null and say nothing; the 385 equal non-volatile leaves of its `observed.arms` are the only thing that actually compares what happened.

### 1.3 Form, default, and §9

- **Form.** 2a: per-instance property over a tool-closed set. 2b: per-instance property over the same set, with a **hand-enumerated exclusion list**. §1 forbids hand enumerations as hard criteria because they fail silently; this one cannot: its only failure mode is a *red* (an unlisted leaf that differs makes the member FAIL and is printed). It is therefore admissible as an exclusion, and it is the one thing in T4 that can hide a difference — which is why its membership is fixed by key name and may grow only as below.
- **Growing the list.** A sixth name may be added only by an append-only correction that quotes both values of the leaf as durations or the profile identity and cites the run that forced it. Because excluding a duration leaf cannot turn a non-duration difference green, that run may then be *re-read* under the grown list without a new run — once. A second new leaf in the same run means a re-run, not another correction.
- **Default if never done**: T4 NE; v24 may not claim "paste unchanged" (as pinned in the spec).
- **Is this moving a rule after its run?** The clause was unsatisfiable, so correcting it cannot loosen a standard the product could have met; §9(2) forcing fact: run 01's three members, named above; §9(3) form: as stated; §9(4) cutoff: T4 closes when run 02's read is recorded, later concerns become findings. But §9(1) is decisive on crediting: the correction is written after run 01, so **run 01 does not satisfy 2b**. T4's verdict is run 02's. The five volatile key names were learned from run 01's diff; I accept that because each is a duration or the profile name by both name and value, and because the list is fail-safe — but it is stated here as the §9 hazard it is.
- **Counting semantics**: T4 has no count; nothing resets. Run 01 remains in the record as rule 1's first PASS, 2a's 5/5, and the forcing observation.

### 1.4 Reader red cases (scratch copies of run 01's files, `--out` into the scratchpad, recorded under `t4/reader-red-01/` with the mutation script, committed before run 02)

- R-a: Chrome copy with `ctrl-v-reaches-the-document` v24 outcome PASS→FAIL → rule 2 FAIL naming it under 2a.
- R-b: `clear-format-removes-every-inline-format` v24 NE→PASS → FAIL naming it under 2b (proves equality, not "at least as good").
- R-c: `every-inline-format-reaches-the-document` with one non-volatile leaf changed (a boolean or string under `observed.arms[*]`) → FAIL naming the member and printing that leaf path.
- R-d: the same member with only `formatPressWaitedMs` 402→999 → the member stays ok (proves the exclusion is applied and is the only place a difference can hide).
- R-e: `wire.json` with every `route: "paste"` request and all `replaceSelection`/`pasteMarkdown` removed → T4 NE, not PASS (non-vacuity).
- R-f: run 01 unmodified under the corrected reader → `read-01b.json`, labelled in its README "not T4's verdict — the rule was corrected after this run"; expected rule 2 PASS. This is a dry re-read of real data, nothing more.

### 1.5 Run 02 and the T4 verdict

Run 02 = `tools/run_v24_t4.py` on both browsers, after E1 (§2) is committed with its witness and V0″ run 1 is green, with the corrected reader committed and R-a…R-f recorded. Pinned expectations of run 02, written before it:

- Rule 1 PASS; 2a all PASS; 2b all equal (both browsers).
- `the-enter-key-reaches-the-document` **PASS in Chrome** (E1's intended effect). If it stays FAIL, Q2's reading was wrong: stop, finding, nothing frozen on top of it.
- **Differential against run 01** (per-instance over the report's check list, the §34 witness that E1 changed only what it declared): every check's outcome in run 02 equals its run-01 outcome in the same browser, except the Enter check in Chrome. Any other difference is named in the read and T4 is not declared until it is diagnosed; it may be attributed to intermittency only by a run 03 in which the same check moves again with no edit in between.
- T4 verdict = run 02's read (`read-02.json`). Default if run 02 never happens: T4 NE.

## 2. Question 2 — the Enter oracle

### 2.1 What is observed (checked)

The line break is in the document on v24: same paragraph, paragraph count unchanged, `<text:line-break/>` between the markers, 2/2 on v24 and 0/2 showing the raw literal, against 2/2 literal on v23 with the same steps. What differs is the XML around typed runs: v24 wraps them in `text:span` automatic styles whose only property is `officeooo:rsid`; the save between the two markers starts a new rsid, so the second marker opens a second span and the literal substring no longer exists. M1's native saves show the keyboard arm and the `.uno:InsertText` arm producing the identical rsid/span structure in every shape, text and round — so v24's saved shape *is* native Writer typing's saved shape, and v23's (paste route) was the odd one.

### 2.2 Decision

1. **Oracle defect** for the check: the oracle encodes the paste route's XML shape; it is false on the typed route for a document that satisfies the check's own stated property. Fixed by E1 (§2.3), witnessed (§2.4).
2. **Declared difference in saved output, not a limit, not a regression**: typed text on v24 is saved with `officeooo:rsid` character spans as native keyboard typing saves it; v23's paste route saved none. Register in spec §10 as **D-typed-rsid-spans** (a "D" line beside the "L" lines, so it is not mistaken for a limitation) and in the v24 release notes in one sentence. Evidence: diagnostic-02's ODTs plus a small reader over `m1-run-01/saves/` that reports, per shape×text×round, the rsid-style count and span count for the `key` and `uno-insert-text` arms and asserts equality (expected: 16 pairs × 3 rounds equal). That reader is the thing that turns "as desktop Writer does" from inference into record; **default if it is never written: the sentence stays an inference and may not appear in the release notes as fact.**
3. **No new native or S5/T1-style run.** T1's comparator is paragraph texts (ruling 3) and M2 already passed 168/168 on v24 with these spans present, so the counted route is not blocked. One-line confirmation to record: that the comparator flattens spans (I did not re-read `odt_paragraphs.py`).
4. **Census (one-time, registered, not a gate)**: targeted grep of `run_e2_c_product_path.py` for raw-content oracles whose needle spans two typed runs or includes markup. Result expected and to be written down: 8726 (the Enter arm) only; 7269 is presence-anywhere and span-safe; `firstLanded`/`secondLanded` are single-run needles.

### 2.3 The oracle on v24 (E1's content — the whole of what E1 may touch)

- Factor a module-level `def paragraph_texts_with_breaks(content: str) -> list[str]` beside `paragraphs_of`'s logic: parse with ElementTree; for every `text:p`/`text:h`, concatenate text in document order descending into every inline element, emitting `"\n"` for each `text:line-break`. Nothing else is transformed.
- `lineBreaksBetween` := any paragraph `P` with `f"{first}\n{second}" in P` (adjacency across the break is kept, as today).
- Record payload: `arm["paragraphText"]` = the flattened text of the paragraph holding `first` (so the next FAIL shows what was seen — run 01's FAIL carried none and cost a replay to learn the shape).
- `together`, the Enter (paragraph) arm, `press_key`, the check's prose, the Firefox NE path: untouched.

### 2.4 Witness and controls (recorded before run 02, under `t4/enter-oracle-witness/`)

- Witness per §34: run 01's Chrome report (an honest run misjudged) and diagnostic-02 (the break present) — already committed; cite them.
- Positive controls (new oracle → True): the four `*-SHFTKEYA.odt` of diagnostic-02 (v23 ×2 without spans, v24 ×2 with spans). The old oracle must give True, True, False, False on the same four — the red-before.
- Negative controls (new oracle → False), on scratch copies of a v24 content.xml: (n1) the `<text:line-break/>` element removed (markers adjacent across the span boundary); (n2) the break replaced by a paragraph split (markers in two `text:p`); (n3) the break replaced by `<text:tab/>`; (n4) other text between the break and the second marker.
- Then E1's behavioural scope is checked by run 02's differential (§1.5).
- Default if the controls are never run: E1 may not be relied on; the Enter check stays unestablished on v24.

### 2.5 Form and default

Per-instance over the enter arms (two arms, Chrome). Default if never done: the check stays FAIL on v24 and v24 may not claim from the product path that Shift+Enter reaches the document; diagnostic-02 is a diagnostic, not a product-path PASS.

## 3. Question 3 — the bound tool files

### 3.1 What the binding is (checked)

Two counted cohorts bind instrument bytes. `counted-r1-s5-01` asserts, on every re-read, that the *live* file equals the frozen hash for 30 tools and archives those bytes in `frozen-sources.tar.gz`. `product-four-arms-counted-01` recorded 24 of the same tools at completion (`post-inputs.json`) and has no live assertion; two of its 24 already differ from the live tree, moved before v24 by the later R1/S5 work. The native run-03 identity binds 12 files, among them the two build scripts AGENTS.md names; none of those 12 is touched by anything below. The live tree today has **zero** instrument drift against `counted-r1-s5-01`; the only divergences are the two declared shell files handled by V0′.

### 3.2 Decision: (b′), and why not (a) or (c)

The live assertion's purpose is that v23's counted record can be re-read with the bytes that produced it. The archive exists for exactly that; the live-tree equality is a proxy for "nothing drifted unnoticed". §14.2 already replaced the proxy with "declared divergence + restore-and-re-read" for the shell files of the *same* cohort. Extending the same method to tools is not a new idea in this tree; refusing it would require the tree to maintain "untouched" with mechanism:

- (a) needs, for the Enter check, a wrapper that monkeypatches the module-level `capture_save` to tee saves and a second judge of one check inside `read_v24_t4.py`; the product-path report itself would carry a permanent FAIL on v24+, and every plain invocation would need the same explanation forever. For the shell generation, (a) leaves `MANIFEST` at v76 after 77 is frozen — the runner's own comment says the constant exists so that identity "follows every freeze without anyone remembering to move it", and `make test-e2-c-reachability` would stay red for good, which §34's threat model (checks guard against accidents) cannot absorb: a permanently red check teaches people to ignore it. That is CLAUDE.md §4's self-check condition verbatim — writing new mechanism to keep a claim true whose premise ("v24 needs no v23 tool") has been falsified by the oracle.
- (c) a copied-and-edited runner beside the frozen one is "adding beside" (E2-B lesson) and forks a 9,989-line instrument; rejected.
- (b′) adds no mechanism: a data file (the declared list), the existing reader run with files restored (as V0′ already did twice by hand), and the check fixes themselves, each witnessed.

What (b′) must honour from this tree's own law: §34 — a modified check needs a witness report and counts as "fixed because of a run" in the handoff; AGENTS.md — the two native build scripts' bytes do not move; E2-B — nothing is added beside a bound file; and the fail-safe direction of every assertion (an undeclared drift is red by name; a declared edit that did not move is red too — the X1 principle).

### 3.3 The declared-edit list

`findings/evidence/link-batch-v24/pre-count/bound-tool-edits.json`, English, committed **before** each edit it names (a first version listing E1 before E1 lands; E2 added in the freeze commit before the edit in the same commit is acceptable because the commit is atomic). Per entry: `path` (relative to `wasm_sdk_probe/`), `frozenSha256` per cohort that binds it (`counted-r1-s5-01`, and `product-four-arms-counted-01` where present — both `7ba30235…` for the runner, `407afdff…` for the bundle tool), `liveSha256` after the edit, `reason` (one sentence), `forcingEvidence` (paths), `witness` (paths), `rulingSection` (this document), `commit`. Authorised entries now — a closed list:

- **E1** `tools/run_e2_c_product_path.py` — §2.3 only. Forcing: `t4/README.md` run 01, `shift-enter-diagnostic.md`, `shift-enter-diagnostic-02/`. Witness: §2.4.
- **E2** `tools/build_e2_c_shell_bundle.py` — line 783 `MANIFEST` → `e2/editor-shell-v2-bundle-v77.json`; `FROZEN_MANIFESTS` += `e2/editor-shell-v2-bundle-v76.json`. Two lines. Forcing: the freeze of 77 and the tool's own guard text. Witness: `make test-e2-c-reachability` red before (as it is now) and green after, both recorded.

Any further edit to a bound file needs its own entry with a forcing fact, a witness, and a V0″ run; it does not need another ruling. **Never**: `tools/build_v23_native_s5_owner.py`, `tools/build_v23_native_s5_type_owner.py` (bound twice; AGENTS.md).

### 3.4 V0″: what it must show, and when it runs

V0″ is V0′ (§14.2) extended to tools. Script it (new file, e.g. `wasm_sdk_probe/tools/run_v24_v0_double_prime.py`, or do it by hand exactly as V0′ was, provided every step's argv, exit code and streams are recorded under `findings/evidence/link-batch-v24/pre-count/v0-double-prime/run-NN/`). Steps and the fact each must show:

1. **Live tree, nothing restored**: `counted-r1-s5-01/read-completion.py --output <fresh>` exits 1 and the failing assertion is the shell one (`live frozen plan differs`), as today.
2. **Shell restored only** (V0′'s restore: `sdk/document-sdk.js` → `9dcb8312…`, `web/e2-editor-app.js` → `c25b11c4…`, source and `dist/` copies): the reader exits 1 and the failing assertion's payload is **exactly a declared tool path** (the first drifted instrument in `cohort.json` order). Then, for each declared tool left live while the others are restored: exit 1 naming **exactly that path**. (For E1 alone this is one run; after E2, two.) This is the proof that the live tree's only instrument divergences are the declared ones, with the path as payload.
3. **Shell and every declared tool restored** — tool bytes taken from `frozen-sources.tar.gz` member `instrument/<path>`, each restored file's sha256 checked against `cohort.json` before the read: the reader exits **0** and its stages read `COMPLETE_R1_PASS` 144/144 and `STOPPED_S5_INCOMPLETE` 401 PASS + 1 FAIL, equal to `completion-read-01.json` on the stage verdicts and counts (not on timestamps or `completionReaderSha256`).
4. **Native run-03 re-read** on the live tree (no restore needed; nothing bound there is edited): `read_v23_native_s5_type.py` exits 0 and its output equals the committed `s5-native/reader-03.json`.
5. **E1-C**: `check_e1_c_bundle_intact.py` exits 0, `intact: true`, live tree.
6. **Put back**: every restored file returns to its live bytes; each declared tool's live sha256 equals its `liveSha256` in the list **and differs from** its frozen sha256 (declared-but-unmoved is red); the shell files' live hashes equal the cutover's (`afdff2d4…`, `b15a6d8e…`); `git status` shows no change under `wasm_sdk_probe/`.
7. **Report only**: for `product-four-arms-counted-01/cohort.json`, the set of its 24 instruments differing from the live tree, which must be ⊆ declared paths ∪ {`tools/judge_v23_feature_selection.py`, `tools/v23_feature_selection_cases.py`} (the two pre-v24 moves). Anything else in that set is an undeclared drift and is red.

**When**: (i) immediately after each declared-edit commit, before any v24 run that imports the edited file (run 1 after E1, before T4 run 02; run 2 in or right after the freeze commit, before any §6.4 count); (ii) as the preflight of every §6.4 count (S5-v24, R1-v24, S14-v24, A4-v24) and of K. Cost is about a minute per read (V0′'s two runs each landed within the minute), so "once per edit **and** once before each count" is the answer, not either.

**Form**: step 2/3 are tool-closed over `cohort.json`'s 30 paths with the path as payload; step 6 is per-instance over the declared list; step 4/5 per-instance. **Default if never run after an edit**: V0's default applies — stop; the edit is undeclared drift, v23's counted record is not shown re-readable, and no §6.4 count may start.

### 3.5 Red cases for V0″ (once, before it is relied on)

- V-1: the declared list without E1 while E1 is live → the procedure stops at step 2 with the reader naming `tools/run_e2_c_product_path.py` (this is also step 2's normal negative, so it comes for free; record it as the red).
- V-2: a declared entry whose `liveSha256` is wrong → step 6 red naming the path.
- V-3: a declared entry for a bound file that did not move (e.g. `tools/web/serve.py`… i.e. `web/serve.py`) → step 6 red "declared but unmoved".
- Corrupt archive is already covered: `frozen-sources.tar.gz` is in the cohort's `prerequisites`, so `read-completion.py:39` refuses before any read; no separate red is needed, say so.

### 3.6 Spec corrections to append (one new section, append-only, citing this ruling)

- §5.4 → "v24's instruments are new files **except the declared edits listed in `bound-tool-edits.json`**; V0 → V0″ (§3.4 here)". Original text stays.
- §6.1 V0 row → V0″ with its default unchanged ("stop …").
- §6.3 T4 row → note pointing to `t4/README.md` Correction 1 (2a/2b, the volatile list, run 02 as the verdict run, the differential).
- §10 → add **D-typed-rsid-spans** (§2.2 item 2).
- §13 → rows R-a…R-f, the Enter positive/negative controls, V-1…V-3.
- §14-style closing line: §34.4 numbers (§5 below).

### 3.7 What stays forbidden

Editing anything bound that is not on the list; editing the two native build scripts under any reason; "adding beside" a bound file; changing `read-completion.py`, `cohort.json`, `status.json` or the archive; and any edit to a bound file while a measurement that imports it is running.

## 4. Generation 77 and the order

**Not now.** §15's condition (all of §6.3 passed, no shell change pending) is not met: T4 has no verdict yet. No shell change is pending — E1 and E2 are tool edits and do not touch the 13 included paths — so 77's bytes will be exactly today's candidate, and that is a checkable fact at freeze time.

Order (each step's output committed before the next starts):

1. Write the corrections: `t4/README.md` Correction 1; `bound-tool-edits.json` v1 (E1); spec append (§3.6); the Enter controls' expected values (§2.4) and run 02's expectations (§1.5). Commit.
2. Corrected `read_v24_t4.py` + R-a…R-f + `read-01b.json`. Commit.
3. E1 + the oracle controls (old oracle red-before, new oracle positives and n1–n4) + the M1 rsid reader (§2.2 item 2) + the census (§2.2 item 4). V0″ run 1 (with V-1…V-3). Commit. Check `uptime`/`pgrep` for the m1-rerun or anything else first.
4. T4 run 02, both browsers → `read-02.json`; the differential; the Enter check PASS in Chrome. T4 verdict. Commit.
5. Freeze 77, one commit: E2; `python3 tools/build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v77.json --write --frozen-date <date>` with the seven `--exclude PATH=REASON` (v76's six + `sdk/v24-feature-worker.js`); assert the written `bundleSha256` equals `56ce44c78043220e4f135343dc87a8e847e83849e4c6571345b1ac9e2e8a294a` (if not, §15's redo clause applies and the §6.3 preparations are repeated on the new bytes); `make test-e2-c-reachability` green, recorded; `bound-tool-edits.json` v2 (E2); V0″ run 2 (two declared tools). Conditions, all checkable: `read-02.json` verdict PASS; Enter PASS in run 02 Chrome; V0″ run 1 exit 0; `git status` clean under the 13 included paths; (vi), (vii), J-red, M2, T5, (i) recorded PASS (they are).
6. §6.4. After E2 the frozen runner's identity names v77 and the four-arm shell clause can hold on v24; the profile/ABI pins in `judge_v23_product_four_arms.py:198` still need the v24 wrapper the spec already anticipates (ruling 2 §1 point 4) — not changed by this ruling. V0″ as preflight of each count.

## 5. §34.4 accounting, and where things go

- Checks fixed because of a run: **2** (`read_v24_t4.py` rule 2; `run_e2_c_product_path.py` Enter oracle). Fixed because of review: **0**. E2 is the freeze's own step, not a check fix; the V0″ script, the declared list, the M1 rsid reader and the census are new files, not modified checks.
- Everything under `findings/evidence/**` and `bound-tool-edits.json` in English; spec appends in zh-TW (repo rule).
- The handoff lists: the two numbers above; the three inherited non-PASS members as "inherited from v23, reproduced leaf for leaf on v24" (not as T4's blessing of them); D-typed-rsid-spans; and that 77 waits on step 4.

Claims in this ruling I could not verify and say so: that `shell_graph` is what the runner uses at run time to stamp identity (no caller by that name in the judge or the runner's own text; consistent with the NE message, not traced); the comparator's span-blindness (§2.2 item 3). Neither changes a decision above.

---

# Ruling 1 — Addendum 1

Fable, 2026-10-28, after V0″ run 01 (`v0-double-prime/README.md`, `run-01/`) and the revert of E1 (aaea5336). Read-only as before; no repository-wide search. "Checked" = verified by reading the named file or a short read-only command.

## SUMMARY

**The new fact is real and I missed it.** `s5-native/settled-reference-reader-05.json` carries `bindings` for 1,772 files (1,480 under `findings/`, 256 under `native-lok-26-8/`, 6 LibreOfficeKit headers, 24 `wasm_sdk_probe/tools/*.py`, 4 native sources, 2 native build artifacts) and `read_v23_native_s5_settled_reference.references()` re-verifies every one against the live tree (`:188` → `verify_bindings` `:119-122`). v23's `settled_references()` (`v23_feature_selection_cases.py:156-159`) calls it on every plan build; v24's `config()` is v23's `s5()` unchanged, so it calls it too. The runner enters that closure through `run_merge_wasm_shakedown.py:96` (`import run_e2_c_product_path as pp`, although the three readers import only `reduce_content`), the bundle tool through the function-local import at `v23_product_four_arms.py:192`. Ruling 1 §3.1 named the two cohorts and run-03's identity and did not open reader-05's `bindings`; §3.2's claim that (b′) "adds no mechanism" is therefore false: with E1 live, v24 cannot build its own S5/R1 plan unless a re-issued certificate is adopted by an override — mechanism that recurs on every edit and every generation. **(b′) is withdrawn for every file in a live-asserted binding.** The revert was the right action under V0's default.

**Decisions.** (1) Enter: option (a). The frozen runner's Shift-arm oracle becomes a declared instrument limit on v24 (**I-enter-raw-substring**); the property is read by a new v24 check, `tools/check_v24_shift_enter.py` (the diagnostic's `--replay` promoted, v24 only, span-aware oracle, 3 repetitions × both arms), with the already-recorded controls re-run against it. (2) Generation 77: `--manifest` with the bound tool unchanged; `Makefile:4843` passes `--manifest` (the Makefile is in no live-asserted set — checked); the handoff's "bump MANIFEST / add v76 to FROZEN_MANIFESTS" is withdrawn; `v24_feature_selection_cases.identity()` (a v24 file) pins v77's file after the freeze. (3) A4-v24: a wrapper that rebinds `build_e2_c_shell_bundle.MANIFEST` in-process before importing the runner, the override recorded, the v24 four-arm judge wrapper requiring the identity to name frozen 77. (4) T4 run 02: Correction 2, appended before the run — Enter **FAIL in Chrome by the frozen oracle, equal to run 01**; all 46 outcomes equal run 01 in both browsers (runner and product are byte-identical, so run 02 is a true repeat); the replay check's 3/3 PASS recorded beside it.

**Re-issuing the certificate (option B) was assessed and rejected**: feasible in minutes and read-only, but it puts the override in v24's plan, re-binds the certificate to bytes its readers never execute, and has to be repeated for every later edit — the dance (b′) tried to avoid, institutionalised. Kept as the named fallback if a bound tool ever *must* change for a product reason; none does now.

**New standing rule**: no edit to any file in the **live-asserted set** = `counted-r1-s5-01/cohort.json` `instrumentSources` (30) ∪ reader-05 `bindings` under `wasm_sdk_probe/` (30: 24 `.py`, 4 native sources, 2 build artifacts) ∪ `s5-native/run-03/identity.json` `sources` (12), while any plan in use imports v23's `s5()`. `bound-tool-edits.json` is closed; E1's entry stays as the record. V0″'s runner stays as the preflight (empty declared list → `V0PP_HOLDS`), and prints the live-asserted set once per run.

**77 timing unchanged**: after T4 run 02 PASS and the Enter replay PASS, before §6.4.

## 0. What I checked

- The chain: `v24_feature_selection_cases.config()` (`:118-121`) → `s5` imported from v23 (`:24-25`) → `settled_references()` (`v23_feature_selection_cases.py:156-165`, hard-codes `settled-reference-reader-05.json` and its sha `ad4febf6…` at `:115-116`) → `settled_native.references()` → `verify_bindings()`; the run-01 traceback ends `native reference input changed: wasm_sdk_probe/tools/run_e2_c_product_path.py`. V0″ step 2's census: 1 of 30 differing, exactly the declared path.
- reader-05: `bindings` 1,772; `witnessDirectory` `s5-native/empty-mark-witness-01`; `counts` population 336, **partition 2** (the certificate's native-every-member-settled reference is used by two cells); `authority` the Astra ruling of 10-27. Its 24 Python tools include `run_e2_c_product_path.py` and `build_e2_c_shell_bundle.py`; its non-Python `wasm_sdk_probe/` members are the native build receipt/binary and four native sources. `Makefile` is not bound by it, by the cohort or by run-03.
- `python_sources()` (`:80-92`) is a static `ast` import walk from the three readers; it refuses only `v23_feature_selection_cases.py`. The readers need `reduce_content` from `run_merge_wasm_shakedown.py`, whose module level imports the whole runner (`:96`; 50 `pp.` uses, all browser-side helpers). Over-inclusion by construction: a design note for the next time the readers are versioned (import `reduce_content` from a pure module), not actionable now — every file involved is bound.
- Re-issue history: `settled-reference-reader-01…05.json`, 10-27 12:24 → 13:23, five issues in an hour; the reader "reads only preserved artifacts, no native execution" — a re-issue costs seconds.
- Commits: 39d09c5c (Correction 1), ae093b6c + 5deaf5f9 (reader, R-a…R-f), da556907 (E1, +35/−3 lines, controls `CONTROLS_HOLD` 6/6 against `59804737…`, census, `read_m1_rsid_spans.py` 48/48 on both native runs), 62f66e94 (V0″ runner), aaea5336 (revert; runner back to `7ba30235…`; `bound-tool-edits.json` status `reverted`). `t4/README.md` Correction 1 and the run-02 expectations read as ruling 1 §1.2/§1.5 wrote them; spec §16 items 1–6 as the agent appended them.
- The rsid correction is accepted: my §2.1 said "exactly one `officeooo:rsid` text style"; the count was right, the family was not — for table2/table4 the rsid sits on the paragraph automatic style with 0 spans. The reader now counts any family; 48/48 both runs. The reader's own non-vacuity check caught its first version (`rsid-spans/README.md`).
- `build_e2_c_shell_bundle.py`: the guard against rewriting an existing generation is the digest comparison (`:1013-1023`), not `FROZEN_MANIFESTS`; the list only feeds exclusion inheritance (`:972-981`), which explicit `--exclude` bypasses. So freezing 77 without touching the tool loses nothing the tool protects.
- `v24_feature_selection_cases.identity()` binds the shell by `shell_bundle.compute(PROJECT)`'s digest and names `'generation': 'candidate-77-not-frozen'` (`:60-75`); it does not read `MANIFEST`.

## 1. Corrections to ruling 1 (append-only; the ruling's text stays)

- §3.1: add the third live-asserted record (reader-05's `bindings`, verified through v23's plan) and its reach (v24's plan too).
- §3.2 "(b′) adds no mechanism": withdrawn. (b′) is withdrawn for every file in the live-asserted set. The six cohort-bound files outside the certificate (`collect_v23_r1_inputs.py`, `judge_v23_feature_selection.py`, `run_v23_feature_selection.py`, `v21_shakedown_common.py`, `v23_feature_selection_cases.py`, `web/serve.py`) are also in the set, so (b′) is moot everywhere; `bound-tool-edits.json` closes.
- §3.3 E1, E2: not authorised. E1's revert stands; its controls remain the oracle's witness (they ran against E1's function text, whose sha the results record).
- §3.4 V0″: kept as the preflight, with an empty declared list; its two departures from the letter (step 1 fails on the shell inside `config()`; step 2 is a census over the 30 instruments) are accepted — the census is what the read was asked to prove, and it carries the path as payload.
- §2.1: rsid family corrected as above.
- §4 order: replaced by §7 below.

## 2. Option B (re-issue the certificate), assessed

Mechanics: run `read_v23_native_s5_settled_reference.py` on the live tree → `settled-reference-reader-06.json`, which must equal reader-05 on every field except `bindings` of the edited paths (checkable). v23's module pins reader-05 and is bound, so v24 would adopt reader-06 by setting `v23_feature_selection_cases.NATIVE_S5_SETTLED_READER_FILE/SHA256` from `v24_feature_selection_cases.py` before calling `s5()` (works: `settled_references()` reads the module globals at call time). Cost: seconds to issue; one visible override in v24's plan module; V0″ still needed for v23's re-read; **and** reader-06 then binds the edited bytes, so every later edit to any of the 24 tools needs reader-07 and an override update, and once v24's cohort pins reader-06, v24 is exactly as immobile as v23 is now. It also re-binds the certificate to a runner its readers never execute. That is machinery built to keep "the tools may be edited" true (§4). Rejected. Kept as the named fallback for a bound tool that must change for a *product* reason; none exists.

## 3. Decision (1): the Enter check on v24

- **I-enter-raw-substring** (instrument limit, declared): on any profile whose typed text is saved with rsid spans (v24 onward), the frozen runner's `the-enter-key-reaches-the-document` FAILs in Chrome because its Shift-arm oracle is the raw substring `A<text:line-break/>B` (`:8724-8726`); the break is present (`t4/shift-enter-diagnostic-02/`, oracle controls 6/6). Register in spec §10 beside D-typed-rsid-spans, in `t4/README.md`, and in the first lines of the next handoff, so no one re-diagnoses it. Every v24 product-path report (T4 run 02, A4-v24) is expected to carry this FAIL.
- **`tools/check_v24_shift_enter.py`** (new; `diag_v24_shift_enter.py --replay` promoted): v24 only (dist as served, page `b15a6d8e…`), Chrome, `--repetitions` default 3, `--out` must not exist; each repetition replays the check's own two arms with the runner's helpers (importing `run_e2_c_product_path` read-only is fine — no byte changes), reopening `enter-key.odt`, saving after the first marker as the check does; the Enter arm judged by paragraph count +1 and markers not together; the Shift arm judged by `paragraph_texts_with_breaks` (E1's function text, moved here verbatim; record its sha) — some paragraph contains `first\nsecond` and the paragraph count is unchanged; the saved ODTs kept and the flattened paragraph recorded as payload; NE for an arm when CDP is absent or a marker did not land; verdict `V24_ENTER_HOLDS` only if every arm of every repetition is PASS.
- **Pass**: 3/3 repetitions × 2 arms PASS, recorded under `t4/enter-replay-01/`. **Form**: per-instance (arm × repetition). **Default if never run**: Enter/Shift+Enter unestablished on v24; the frozen FAIL stands unexplained; v24 may not claim the property.
- **Red cases before relying on it** (`enter-oracle-witness-02/`): (i) `controls.py` importing the function from the new tool — old oracle True, True, False, False on the four diagnostic-02 saves; new oracle True ×4; n1–n4 False — identical to witness-01; (ii) the tool's arm judge fed the four diagnostic-02 Shift arms' saved XML → PASS ×4 (v23's paste-shape XML included), and fed a scratch content.xml with the break removed → FAIL (proves the end-to-end judge uses the new oracle, not a copy of the old one); (iii) `--repetitions 0`, or CDP unavailable → NE/refusal, never PASS.
- §34: the runner is byte-identical, so no check was modified; the new tool is a new instrument with its controls. It feeds no count, so §34's one-time double-seat review does not apply unless it ever becomes a count input.

## 4. Decision (2): freezing generation 77 without touching the bound tool

- Command, tool unchanged: `python3 tools/build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v77.json --write --frozen-date <date>` with seven explicit `--exclude PATH=REASON` (v76's six + `sdk/v24-feature-worker.js`). Checkable facts after the write: `bundleSha256 == 56ce44c78043220e4f135343dc87a8e847e83849e4c6571345b1ac9e2e8a294a` (else §15's redo clause); `included` is v76's 13 paths, `sdk/document-sdk.js` `afdff2d4…` and `web/e2-editor-app.js` `b15a6d8e…`, the other 11 equal to v76; `excluded` exactly the seven; `exclusionsInheritedFrom` null; `git status` clean under the 13 paths.
- `MANIFEST` stays v76 in the bound tool for as long as v23's records are live-asserted. Each consequence handled: (a) `Makefile:4843` becomes `python3 tools/build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v77.json > /dev/null`; witness: `make test-e2-c-reachability` red before (as now) and green after, both recorded; red case: the same line pointed at v76 → red. (b) The handoff 10-28d line-10 instruction and the tool's own guard text ("bump MANIFEST and add this one to FROZEN_MANIFESTS") are withdrawn/stale for this tree — say so in spec §16's addendum and the handoff. (c) The frozen runner's `SHELL_BUNDLE_V2` stays v76: plain invocations on v24 keep naming v76 and NE'ing the four arms; the v24 way to run the product path is the wrappers (§5), stated in the spec and handoff. (d) `v24_feature_selection_cases.identity()` (v24 file, free): after the freeze, also pin `e2/editor-shell-v2-bundle-v77.json`'s file sha256 and name generation 77 (keep the digest check); red case: a scratch v77.json with one byte changed → `identity()` refuses. This lands before any §6.4 count (it changes v24's `configSha256`; the counts are fresh populations, so nothing recorded is invalidated; §6.3's preparations stand because the shell digest is unchanged).
- **Form**: per-instance over the written manifest's fields and the Makefile target. **Default if never done**: 77 is not frozen; §6.4 may not start.
- **Timing**: unchanged — after T4 run 02 PASS and the Enter replay PASS (§7), before §6.4, with V0″ (empty list) as the preflight.

## 5. Decision (3): A4-v24

- Wrapper `tools/run_v24_four_arms.py` (new; keep `run_v24_t4.py` as the tool that ran T4): before any import of the runner, `import build_e2_c_shell_bundle as b; b.MANIFEST = Path('e2/editor-shell-v2-bundle-v77.json')`, then `import run_e2_c_product_path as pp` (`SHELL_BUNDLE_V2` is computed at import, `:2571`; `shell_graph` reads the same module object at run time, `:192`). The identity the runner writes then names v77 — true facts about the served tree. The wrapper records `shellManifestOverride: {default: "…v76.json", used: "…v77.json", fileSha256}` in its output.
- The v24 four-arm judge wrapper (required anyway for the profile/ABI pins at `judge_v23_product_four_arms.py:198`, ruling 2 §1 point 4) additionally requires `identity.shell.bundle == e2/editor-shell-v2-bundle-v77.json` and `bundleFileSha256` equal to the committed v77's; otherwise NE "shell generation is not frozen 77".
- Red cases: (i) the wrapper without the override on v24 → four arms NE `served sdk/document-sdk.js is not the reported shell generation` (run 01 shows it; re-record once through the wrapper); (ii) override to a non-existent v78 → refusal at the manifest read (`:2658`); (iii) the v24 judge wrapper fed run 01's four-arm directories (v76 identity) → NE naming the generation.
- **Form**: per-instance, 4 arms × 3 cells × 2 browsers, as v23. **Default**: A4-v24 NE; v24 may not claim the four arms.

## 6. Decision (4): T4 run 02's pinned expectation

Append **Correction 2** to `t4/README.md` before run 02 (legitimate under §9: before the run, forced by the third binding and the revert, and not a loosening — the property is still required, by the tool that can read it, and the differential tightens):

- Rule 1 PASS; 2a all PASS; 2b all equal; both browsers.
- `the-enter-key-reaches-the-document`: **FAIL in Chrome by the frozen oracle (I-enter-raw-substring), NE in Firefox** — equal to run 01. A PASS would itself be a change to diagnose (it would mean no span boundary fell between the markers that time).
- **Differential against run 01**: every check's outcome equals run 01's in both browsers — runner `7ba30235…` and product unchanged, so run 02 is a true repeat and the intermittency sample ruling 1 lacked. Any difference is named; intermittency may be claimed only by a run 03 in which the same check moves again.
- Beside it, same day: `check_v24_shift_enter.py` 3/3 (`t4/enter-replay-01/`). T4's README reports Enter as "frozen oracle FAIL (declared) / replay check PASS".
- T4 verdict = `read-02.json`. Default unchanged.

## 7. The no-edit rule, V0″, and the order

- **Rule** (spec §16 addendum, supersedes §16 items 1 and 2 and ruling 1 §3.3): no edit to any file in the live-asserted set (§SUMMARY) while any plan in use imports v23's `s5()`; the two native build scripts are in it. `bound-tool-edits.json`: `edits` closed (`closedBy: RULING-1 Addendum 1`), E1's entry kept. If a bound tool ever must change for a product reason, option B is the route, by a new ruling.
- **V0″ runner**: kept as the preflight of every §6.4 count and K, run with the empty declared list; required verdict `V0PP_HOLDS` (census 0/30 drift; shell-restored read exit 0 with the recorded stage verdicts; run-03 re-read equal; E1-C intact; put back clean). Add one reporting step: compute and print the live-asserted set (the union above, with per-source counts) so the next agent sees what may not be touched without opening three files. V-1…V-3 remain its red cases, with a scratch declared list.
- **Order** (each step committed before the next):
  1. Append Correction 2; spec §16 addendum (items 1, 2, 3, 6 superseded; I-enter-raw-substring in §10; red cases in §13); withdraw the handoff's MANIFEST bump; close `bound-tool-edits.json`.
  2. `check_v24_shift_enter.py` + witness-02 + its red cases → run on v24 3× → `t4/enter-replay-01/`.
  3. T4 run 02, both browsers → `read-02.json`; differential; verdict. Check `uptime`/`pgrep` first (the m1-rerun is done; nothing else should be running).
  4. Freeze 77 (§4): manifest written and asserted; `Makefile:4843`; v24 `identity()` pin + its red; reachability green; V0″ run.
  5. A4 wrapper + v24 judge wrapper + their red cases; then §6.4 with V0″ before each count.
- **77 may be frozen** when: `read-02.json` verdict PASS; `t4/enter-replay-01/` `V24_ENTER_HOLDS`; V0″ `V0PP_HOLDS` on the current tree; candidate digest unchanged; (vi), (vii), J-red, M2, T5, (i) recorded PASS (they are). Not before.

## 8. §34.4 and what to record

- Checks fixed because of a run: **1** (`read_v24_t4.py` rule 2). Fixed because of review: **0**. E1 was landed and reverted; the runner is byte-identical to run 01's; `check_v24_shift_enter.py`, the A4 wrapper and the judge wrapper are new instruments.
- Record in the handoff, first lines: I-enter-raw-substring (the frozen runner's Enter FAIL on v24 is declared, read by the replay check); the live-asserted set and that `bound-tool-edits.json` is closed; 77's freeze is by `--manifest` and the Makefile, the bound tool's default stays v76 by design.
- Design note (not a gate, not for now): the settled certificate's static import closure binds the product-path runner through `run_merge_wasm_shakedown.py:96` although no reader executes it, and certifies two cells with 1,772 bindings; when the readers are next versioned, `reduce_content` should come from a module without browser imports.
