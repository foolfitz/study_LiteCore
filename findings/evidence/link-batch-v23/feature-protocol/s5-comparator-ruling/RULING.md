# S5 deletion comparator against native saves: fable ruling 2 (2026-10-27)

Requested under the owner's standing authorization for this session ("難以決定的地方就發給fable，我授權他替我裁決").

## The forcing measurement

Before any S5 browser cell ran, two unedited saves of the same fixture bytes were compared. One is the WASM product's readiness `beforeSave` (`selection-prep-05/chrome-shift-Home@doc-start.json.gz`). The other is the native `s5-native/run-01/saves/shift-Left@caret-mid_backspace-before.odt` (sha256 `59c97a869bdd…`). They are not equal under `run_merge_wasm_shakedown.reduce_content`.

Comparing each top-level child of content.xml: `office:scripts` equal; `office:automatic-styles` equal (767 bytes each); `office:body` equal (2303 bytes each); root attributes equal. Only `office:font-face-decls` differs. WASM declares Liberation Sans, Liberation Serif, Noto Sans CJK KR and Noto Sans CJK SC; native declares Liberation Sans, Liberation Serif, Noto Sans CJK TC, Noto Sans CJK TC1 and Noto Serif CJK TC. These are the two environments' installed CJK fonts, not edit effects.

Prerequisite scan, a scoped scan of the 784 run-01 saves:

- Every one has exactly one `office:font-face-decls` element.
- `rsid` occurs only in 56 type-family after-saves, and the type family is compared by paragraph text.
- No deletion-family save contains `rsid`.

## The ruling, verbatim

> **Ruling: A′ — Option A, with the control made mandatory and two guards.** Not B: `office:automatic-styles` carries edit effects (a deleted span's automatic style disappears on save), so body-only would hide real deletion outcomes. Not C: it fails the product on the two machines' default CJK fonts, which no deletion can change. A′ follows M2-0's own method (spec 24 was "derived from the no-edit diff and from nothing else"): one operation per measured difference, no more.
>
> **Exact comparison.**
> - Native-referenced deletion cells (Left/Right; Home/End only with the single-line witness): `strip_ffd(reduce_content(candidate_after.content.xml)) == strip_ffd(reduce_content(native_after.content.xml))`, byte equality. `strip_ffd` removes exactly one `<office:font-face-decls>…</office:font-face-decls>` element (regex, `count==1` else NE `font-face-decls not uniquely present`); the removed element must be non-empty and the remainder must still contain `<office:body>` (else NE). Nothing else is normalised; rsid, automatic-styles, scripts, root attributes all stay compared.
> - Settled-WASM deletion cells (Up/Down, multi-line Home/End): unchanged, full `reduce_content`, byte equality, same environment.
> - Type-`x` family: unchanged (paragraph text).
> - `run_merge_wasm_shakedown.reduce_content` itself must NOT be edited — it is M2-0's bound reduction and S-CASES says no other normalisation is authorised there. `strip_ffd` is a separate function in the S5 reader, applied after it, used only on the native-referenced branch.
>
> **Before-save control: required, per cell.** `strip_ffd(reduce_content(candidate_original_save)) == strip_ffd(reduce_content(native_before_save))` for that cell's own two files. Failure or a missing original save → that cell's S5 is **NE** (`native reference not comparable`), never FAIL and never skipped — plus a mandatory finding entry, because an unedited round trip that differs in body/styles is a real load/save fidelity observation even though it is not S5's claim. The control is what makes the reduction honest: it proves, per instance, that the stripped element was the only cross-environment difference and surfaces any other drift instead of hiding it.
> Second guard (precedent: `reduction_collapses`, spec 10.2): for each native-referenced cell, `strip_ffd(reduce_content(native_before)) != strip_ffd(reduce_content(native_after))` unless the raw content.xml pair is byte-identical (a genuine native no-effect, which the protocol allows only when the oracle demonstrates it); otherwise NE `reduction collapses the native edit`.
> §6 red cases before the first counted S5 cell: one byte changed inside `office:body` of a native after-save → FAIL; one byte inside `office:automatic-styles` → FAIL; one byte inside `office:font-face-decls` → still PASS (documents what is ignored); one byte in the candidate original save's body → control NE; a save with two font-face-decls elements → NE.
>
> **§9 / count semantics.** No S5 browser cell has run, counted or not, so all four conditions are met cleanly: (1) before satisfaction; (2) forced by the named measurement […]; (3) form — a fixed element removal plus a per-instance control, no hand list; (4) cutoff — the first complete clean S5 population per browser closes it; later font-declaration drift is a finding. This changes a required clean predicate of the native-referenced partition only (196 Left/Right + single-line Home/End); the settled-WASM partition and the type family are untouched. There are no counts to reset. […] Before the counted S5 run, scan the 784 native saves' content.xml for `rsid` […] and run ONE uncounted native-referenced deletion cell through the new comparator. If either shows rsid or any non-font drift, come back for a §9 addition; do not pre-authorise rsid removal on zero evidence, and do not burn a counted population on a predictable instrument issue.
>
> **Plain-language rationale for the owner.** The two machines list different default Chinese fonts in the saved file's font table, and that table is written from the environment, not from anything the user did — so the product would fail every deletion test for using a different font list, not for deleting wrongly. We ignore exactly that one table, and only when comparing against the native machine, and we first check on every test that the untouched document from both machines is identical once that table is ignored; if it is not, the test says "not comparable" and we record a finding, rather than passing or failing on a hidden difference. Comparisons between two WASM runs stay byte-exact.

## Implementation

`judge_v23_feature_selection.py`: `strip_ffd`, `s5_reduced`, `s5_compare` and `native_reference` (the per-cell control and the collapse guard). `reduce_content` is unchanged. Red cases are in `S5ComparatorControls`, built from the real WASM unedited save and native run-01 saves:

- One byte in a native after-save's `office:body` → differs.
- One byte in its `office:automatic-styles` → differs.
- One byte in its `office:font-face-decls` → still equal.
- One byte in the candidate original's body → NE `native reference not comparable`.
- A duplicated font table → NE `not uniquely present`.
- A native after that differs only inside the font table → NE `reduction collapses the native edit`.

Each edit is asserted to land inside its named section. The real control and reference pass. Full `reduce_content` still sees the font table on the WASM-vs-native pair, so the settled branch was not silently loosened.

The ruling's second prerequisite, one uncounted native-referenced deletion cell through the new comparator, is pending the browser lock.
