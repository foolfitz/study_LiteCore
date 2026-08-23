# Finding 078 — characterising what an inline format does to a SELECTION

Measured 2026-08-23 with `wasm_sdk_probe/tools/probe_inline_range_format.py`.

The shipped manifest offers `set-bold` and its three siblings for `collapsed`
only, so the measurement cannot be taken through it: the engine refuses before
dispatch. It was taken on `e2-inline-range`, a **diagnostic profile packaged
from the shipped artifact** — byte-identical loader, wasm and worker,
`f923cfa5...` — with the range gestures granted in the manifest and nowhere
else. No relink: the binary already implements the dispatch and the mask
withheld it. The builder refuses to grant them under the product's own name.

## Result

Two runs, identical.

| arm | selected text | bold text in the saved ODT | verdict |
|---|---|---|---|
| baseline (nothing pressed) | — | none anywhere | clean |
| `range-single` | `1-LC-NUMBER-TW` | `1-LC-NUMBER-TW` | **exact** |
| `range-cross` | `␣␣␣␣␣1-LC-NUMBER-TWO\nE1-LC-END` | `1-LC-NUMBER-TWOE1-LC-END` | **exact**, whitespace squeezed |
| shipped profile (control) | same drags | none; both presses refused | the mask is what blocks it |

On `range-cross` the second paragraph — fully selected — comes back as
**paragraph-level** bold rather than a text span. The visible result is the
same; text typed into that paragraph later would inherit it, and whether that
matches native LibreOffice was not checked.

## Two wrong conclusions were produced first, and both are kept here

`withdrawn-count-oracle-run1.json` is retained deliberately.

**Wrong conclusion 1 — "applying bold to a selection also emboldens two
unrelated list paragraphs."** The paragraph-style parser matched
`<style:style ... style:family="paragraph" ...>(.*?)</style:style>`, and the
paragraphs in question use a **self-closing** style element with no text
properties at all. With no closing tag to stop at, the scan ran past it into a
later text style that WAS bold, and attributed that weight to it. Reproducible
across two runs — a stable wrong answer, which looks exactly like a real
finding. What caught it was putting the style's own markup into the record
beside the verdict. What did NOT catch it was the unit test, because the
synthetic document written for that test contained no self-closing style: it
only ever proved the parser correct on shapes its author had thought of.

**Wrong conclusion 2 — "range-cross under-applies by a quarter."** The oracle
compared the engine's reported selection LENGTH (30) against the bold character
count (24). Both numbers were right and the comparison was not: the engine's
selection string carries a 5-character **list prefix** on the first paragraph
when the selection crosses paragraphs, plus a `\n` separator, and neither is
document text. 30 − 5 − 1 = 24, exactly. The fixture's paragraph is
`E1-LC-NUMBER-TWO` with no leading spaces, which is how the prefix was
identified.

The oracle now compares the bold TEXT against the selected TEXT. Strings cannot
be fooled the way counts were.

## Not established

* One fixture, one selection geometry per arm, Chrome only.
* **Bold only.** Italic, underline and strikethrough were not exercised.
* The drag is synthetic PointerEvents, not real mouse input.
* **The 5-character list prefix is unexplained.** It appears when the selection
  crosses paragraphs and not when it does not. Finding 074 concerns the same
  engine treating an attribute run as a list prefix; whether these are the same
  mechanism has not been asked.
* Whether paragraph-level bold on a fully-selected paragraph matches what
  native LibreOffice writes.
* No regression-net check formats a selection, and none has a mutation that
  could turn such a check red.

## Files

| file | what it is |
|---|---|
| `range-granted-run1.json`, `-run2.json` | the measurement that stands |
| `shipped-profile-control.json` | the same probe on the shipped profile: both refused |
| `withdrawn-count-oracle-run1.json` | the run that produced both wrong conclusions |
