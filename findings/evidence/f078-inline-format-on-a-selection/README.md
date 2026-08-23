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

## The grant cannot be partial — measured 2026-08-23, after the adjudication

All four inline formats were then measured on the diagnostic profile, one run
each (`granted-set-*.json`). Every arm, both gestures: the formatted text in the
saved ODT equals the selected text, with a clean baseline. The characterisation
covers what a grant would name.

A profile granting **`range-single` only** (`e2-editor-v6`) was minted from the
shipped artifact and probed on a clean document: **both arms refused**
(`range-single-only-refused.json`). A profile granting **`range-cross` only**
was minted and probed: **both arms refused** too
(`range-cross-only-refused.json`). The same drags succeed where both are
granted.

The engine says why, at the gate, in its own comment:

> An unclassified range must satisfy BOTH range bits, because
> `editorGesturePermitted()` accepts on any intersection: passing the OR of the
> two would let a profile that allows only range-single admit a range this build
> never classified, which may be a cross-paragraph one. Telling them apart needs
> the html read, and that read is the wedge risk findings 037/038 describe -- so
> the check is conservative instead.

At that point the selection has NOT been classified. Classifying it needs an
HTML read, and that read is a known engine-wedge risk. So the gate demands both
bits.

**Therefore "grant range-single and withhold range-cross" is inexpressible for
these actions.** A profile granting only one admits nothing at all for a
non-collapsed selection. `e2-editor-v6` exists and is kept as the artifact that
demonstrates this; it is not a candidate for shipping.

The two range-cross artifacts look weaker in this light, though neither is
resolved:

* the paragraph-level expression happened on a paragraph that was **fully
  selected**, where hoisting direct formatting to the paragraph may be exactly
  what LibreOffice's own export does. Unverified against native.
* the 5-character list prefix appears in the **selection text reported by the
  copy path**, not in the formatting, and no formatting outcome depended on it
  once the oracle compared strings instead of counts.

## The re-decision, and what it cost to reach

The adjudication was revisited with the AND-semantics fact and reversed to
**grant both**. Its reasoning: the case for granting one had rested on the two
gestures' evidence differing in KIND, and that difference had evaporated —
all four actions measure text-exact on both shapes, and the two range-cross
artifacts turned out to be a question about ODF *shape* and a quirk in the
*reporting* path, neither of them evidence that the formatting is wrong. And
under AND-semantics a manifest withholding `range-cross` claims "ranges
unsupported" about a binary that measurably supports them — the same dishonesty
the original restriction avoided, pointed the other way.

Three conditions came due with the grant.

### 1. Native comparison — cleared, with no divergence at all

`tools/f078_native_range_format.cpp`, LOK against the native 26.8 build, same
fixture, `.uno:Bold` on a selection made by `.uno:ExecuteSearch` (which leaves
its hit selected):

| native arm | spans | paragraph styles |
|---|---|---|
| whole paragraph selected | — | `E1-LC-END` (9), bold |
| part of a paragraph | `LC-ISOLATED` (11), bold | — |

**Native writes exactly what the WASM engine writes** — paragraph-level for a
fully selected paragraph, a span for a partial one, same extents. There is not
even a divergence to record in the profile's limits.

### 2. The minted identity's own green — `e2-editor-v7`

Everything above was measured on a DIAGNOSTIC profile. The transfer argument
(byte-identical wasm, manifest-only delta) is sound and was still not accepted
as the shipped claim, because conclusions had twice been published that day
against a different artifact than the conclusion was about.

On `e2-editor-v7` itself: all four inline formats, both shapes, **eight arms,
every one text-exact, every baseline clean** (`v7-own-*.json`), and the product
path at **36 PASS / 3 NOT_ESTABLISHED, `ok: true`** (`v7-product-path.json`) —
one PASS more than the shipped baseline, the new selection-formatting check
being the extra.

### 3. Operator real-mouse pass — outstanding

The drags here are synthetic PointerEvents. By this project's own history the
closure of an issue like this is the operator's own path, not the harness going
green.

## The oracle's normalisation, named rather than promised

The comparison squeezes whitespace, and that is an instrument accommodation of
the unexplained list prefix. `probe_inline_range_format.py --self-test` runs the
table showing what it can and cannot hide: a dropped paragraph, a dropped
character and an extra character all still fail; **a difference that is only
whitespace is invisible, deliberately**, and nothing has measured whether a
format can miss a space between two words it covered.

Saying "exact" without that qualifier — as an earlier round of this write-up
did — reports the oracle more strongly than it earns.

## The mutation, and the one that did nothing

`format-ignores-a-selection` makes every format press send `enabled: false`, so
nothing a user selects ever gains a format. On `e2-editor-v7` it takes
`an-inline-format-reaches-a-selection` from PASS to **FAIL**
(`v7-mutation-detected.json`). The check can go red.

**Its named weakness**: the blast radius is wide — `the-keyboard-reaches-the-document`
and `bold-can-be-turned-off-again` go red too, and four inline checks drop to
NOT_ESTABLISHED. So this proves the check CAN fail, not that it is the one that
would notice.

A tighter mutation was tried first and **never fired**
(`mutation-that-never-fired.json`): it returned early when
`lastSelectionShape !== "collapsed"`, and that condition was never true at press
time, on either run. The page's own selection shape is **stale** when the button
is pressed — which is finding 079, and which is also why a profile granting one
range bit showed an ENABLED button and an engine refusal at the same time.

Keeping the run that did nothing: an inert mutation looks exactly like a check
that cannot fail, and the difference was only visible because the "nothing"
was investigated instead of replaced.
