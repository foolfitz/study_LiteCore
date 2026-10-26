# S1 for table-selection members: fable ruling A′ (2026-10-27)

The owner asked for a fable ruling ("交給fable裁決") and later authorized fable to decide difficult questions on the owner's behalf for this session ("難以決定的地方就發給fable，我授權他替我裁決"). The question was put after uncounted preparations 03–05 showed that the S1 premise "Shift endpoint = same-browser unshifted endpoint" is false in native Writer whenever the plain move crosses a table container boundary. In four measured members the product's selected text equalled native Writer's three rounds character for character. The brief listed options A (native text oracle for those members), B (named-limit NE) and C (keep the predicate).

## The ruling, verbatim

> **Ruling: A′ — Option A with four precisions.** Not B (the oracle is not missing; the same protocol already accepts native literal text for Left/Right, and B would make S1 unclosable without a population edit). Not C (it keeps a falsified premise; §4 forbids exactly that).
>
> ### 1. Exact S1 predicate for table-selection members (TSM)
> - Oracle readiness: `row['nativeAfterSelectionText']` has three identical strings; otherwise S1 = NE `native table-selection oracle disagrees` (NE, not FAIL — a disagreeing oracle is not product behaviour).
> - The reference arm still runs, must still be non-stale (`need(not reference['stale'])` stays), and `logical_endpoint(e)` is still derived: the membership rule consumes it. A cell with no derivable reference endpoint is NE and is never classified.
> - Hard clause (the only `contradict` for TSM): `page['candidate']['activeSelection']['text'] == texts[0]`, literal, where `activeSelection` is the existing read taken after the ≥500 ms delayed readback — never the reply.
> - Not asserted for TSM: caret == reference endpoint; post-key `endpoint_pair`; the Home/End single-line literal clause (`single` is still computed and recorded, not used). Setup-time anchor/shape checks in `setup()` are unchanged. Anchor preservation after the key is witnessed only to the extent Writer's own text extent witnesses it (the native text begins/ends in the anchor's cell or paragraph) — record `anchorWitness: 'native-text-extent'` and the named limitation "caret side and text-anchor identity not independently witnessed for TSM". Per §3 this is "behaviour present, no guard", not "nothing to guard".
> - Report per cell: `tableSelection: true`, `containers: [moving, referenceEndpoint]`, `logicalEndpoint` (the plain control's, still recorded), `nativeText`.
> - Every non-TSM member: reader behaviour unchanged, byte for byte. Red case (d) below proves it.
>
> ### 2. Membership rule: form test (§1)
> Passes as a per-instance property **only if stated as a function of three inputs, none of which is a list of member ids**: (i) the moving point's paragraph, `row['pointPlans'][row['movingPointName']]['paragraph']`; (ii) `logical_endpoint(e)[0]` measured in the same cell; (iii) a paragraph→container map parsed from the pinned fixture bytes (`PINS['fixture-as-run.fodt']`, sha-checked, the same bytes `paragraphs()` reads), container ∈ {body, (table, row, col)}. The parser must prove it walks paragraphs in the same order as `paragraph_texts_from_xml` by re-deriving the texts and comparing to `plan['fixtureParagraphs']`; a parser that finds zero tables, a different paragraph count, or nesting it does not model raises NE for the cell — never "not a TSM" (non-vacuity, §6). TSM ⇔ container(i) ≠ container(ii). This is the right branching condition because it is literally the precondition under which the old premise was measured false (the plain move crosses a container boundary).
> Dynamic check: swap the fixture → the sha pin breaks (NE everywhere); add a 15th source shape → the rule classifies it with no reader edit; write `TABLE_MEMBERS = {...}` anywhere → form three, forbidden as a hard criterion (prep-03's census table is fine as a logged one-time measurement).
> Missing inputs → S1 NE with reason, never a branch choice: a wrong branch yields either a false FAIL (old predicate on Writer-correct behaviour) or a false PASS. A shape whose anchor and moving point already sit in different containers at setup (none among the current 14) must raise NE `setup shape crosses container; no oracle`, not be classified.
>
> ### 3. Default and §9 count semantics
> Default per cell stays the plan's `NOT_ESTABLISHED_UNPERFORMED`; an S1 population with any TSM unmeasured is NE and does not close (protocol: missing measurement is NE, "no percentage substitute"). §9: (1) before satisfaction — yes, no counted S1 run exists; (2) forced and named — prep-03 `shift-Up@cell-end`, prep-04 `shift-Down@cell-end`, `shift-Right@cell-end`, `shift-Down@list-mid`, each product == native 3/3 (`extend-signatures/run-20261013T095104Z/arms-r{1,2,3}.jsonl`, lines 94–96 and 60); (3) form — §2 above; (4) cutoff — the first complete clean S1 population per browser closes S1; later table-semantics unease becomes a finding, not a predicate edit.
> Count semantics: this changes a required clean predicate of S1 → S1 counts reset (there are none). S2/S3/S5/R1 predicates untouched → unaffected. Prep-03/04/05 remain uncounted evidence; re-reading their raw cells with the new reader is the reader's red/green test, not a count.
> Red cases required before the first counted run (§6): (a) TSM raw cell with one character altered in the active-selection text → FAIL; (b) a TSM whose candidate selection is what the OLD premise expected (plain-endpoint extension) → FAIL (proves the new clause is not vacuous); (c) parser fed a fixture body without the table → NE, not PASS; (d) `shift-Down@caret-mid` from prep-03 reads identically under old and new reader; (e) reference endpoint moved into another container by editing a raw cell → the branch flips and the report shows it.
> Append-only (§10): do not delete the S1 row's "compare moving endpoint with the same-browser unshifted control" or "Only Left/Right and witnessed single-line Home/End permit literal native comparison"; append the correction naming prep-03/04 as the forcing measurements, and do the same for `contracts.S1` / S-CASES.md. The reader hash changes; prep-03/04 stay bound to the old hash.
>
> ### 4. What this ruling does not decide
> - Firefox: nothing measured; the rule applies identically, no verdict implied. Layout is computed in the core, not by the browser, so a browser-dependent text mismatch is a real difference to investigate, not an instrument artefact by assumption.
> - `shift-Up@doc-end` (in flight): the predicate is fixed, its outcome is not. Note its native text begins with a rendered list label `    • \n`; a label-only mismatch is a FAIL to investigate under this predicate, not a reason to trim the comparison.
> - S2 and S3: unchanged. S5 sequences whose source cell is a TSM (Backspace/Delete on a cell or row selection): comparator and reference remain the protocol's NE-until-produced; nothing here supplies them.
> - R1 table preconditions, the finding-134 table-boundary obligation, and whether Writer's table-selection UX is desirable: untouched; Writer parity is the oracle, not approval of the behaviour.
> - Observed, not changed (not forced): for non-TSM Left/Right the existing clause reads disagreeing native rounds as FAIL rather than NE.
>
> ### 5. Plain-language rationale for the owner
> The acceptance test assumed that holding Shift while moving selects exactly up to where the same move lands without Shift. Writer itself does not work that way around tables: when a move would cross into, out of, or between cells, Writer selects whole cells or jumps the whole table, and in every measured cell the product reproduced Writer's result character for character. Keeping the old test would fail the product for being right. So for exactly those members — identified by whether the plain move crosses a table boundary, computed from the fixture and the control measurement rather than from a hand-written list — the test now compares the product's selected text with Writer's own, which all three native rounds agree on. Everything else stays as it was, unmeasured members stay "not established" until run, and a member that disagrees with Writer is a failure to investigate, not a reason to loosen.

## Implementation

`wasm_sdk_probe/tools/judge_v23_feature_selection.py`:

- `containers_from_xml` parses the pinned fixture into a container per paragraph, walking the same `body.iter()` order and using the same `_inline` text derivation as `paragraph_texts_from_xml`. It requires the derived texts to equal `plan['fixtureParagraphs']`. Any of the following raises NOT_ESTABLISHED: no table, a paragraph inside a note/frame/annotation, a nested or covered cell, rows not directly under `table:table`, a repeated or spanned row/column.
- `fixture_containers` checks the fixture bytes against `plan['fixtureSha256']`.
- `table_selection` requires the anchor and moving point to share a container (otherwise NE `setup shape crosses container; no oracle`) and returns `[moving, endpoint]` when they differ.
- In `inspect`, a table-selection member's only contradiction is the literal native text after the three-round agreement check. Every other member takes the original sequence unchanged.

On the fixture the map is: body for paragraphs 0–7 and 12; A1 `[0,0,0]`, B1 `[0,0,1]`, A2 `[0,1,0]`, B2 `[0,1,1]` for paragraphs 8–11.

Red cases, all in `tests/test_v23_feature_selection.py` `TableSelectionControls`, built from the real preserved cells:

- (a) One character of `shift-Down@cell-end`'s active-selection text altered, consistently in the page record, the call result and the wire reply → S1 FAIL `table-selection native text differs`.
- (b) `shift-Up@cell-end` rewritten to the old premise's extension: caret at the plain endpoint, selection from it to the cell end, a different text → S1 FAIL.
- (c) The parser refuses a fixture without the table, a reversed expected order and a spanned cell.
- (d) `shift-Down@caret-mid` (prep 03), `shift-Home@cell-end` (prep 04) and `shift-Right@range-bwd` (prep 05) read exactly as their runners stored them.
- (e) `shift-Home@list-mid` with its control endpoint moved into A1 flips to a table-selection member, and the report shows `containers: ["body", [0,0,0]]`.

Case (e) moves the endpoint by substituting the reader's mapped paragraph rather than by editing raw coordinates. The mapping's own wire bindings (endpoint-select and endpoint-text calls) would otherwise refuse a forged coordinate as NE before the branch is reached. 29/29 tests pass.

Re-reading every preserved Chrome cell (preparations 02–05, 22 cells with a page) with this reader: all 22 PASS. The five table-selection members are `shift-Up@cell-end` (`[0,0,0]`→body), `shift-Down@cell-end` (A1→A2), `shift-Right@cell-end` (A1→B1), `shift-Down@list-mid` (body→A1) and `shift-Up@doc-end` (body→A2). These are uncounted reader checks, not counts.

## One deviation from the ruling's append list

The ruling asks to append the correction to `contracts.S1` as well. That text is generated by `wasm_sdk_probe/tools/v23_feature_s_cases.py`, and that source belongs to two bound graphs: the sealed pre-red reader's import closure, which `check_pre_red` requires to be byte-identical to counted-05's executed graph (`42b6a97b`), and the native S5 runner's bound sources, which were measuring when this was written. Editing it would make `check_pre_red` refuse the sealed result and break the native run's binding. The correction is therefore appended to the protocol and to `S-CASES.md`, and the generated `contracts.S1` still carries the original wording. A reader of `s-cases.json` must take this record and the protocol appendix as superseding that one field.
