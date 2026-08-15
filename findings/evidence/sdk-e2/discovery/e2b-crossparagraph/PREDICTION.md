# Prediction: the three checks that decide B' against A

**Written and committed before the probe exists and before any run.**

Required by `specs/SPEC-E2-B-paragraph-format-contract.md` section 9.7. In
English per `AGENTS.md`.

## What is being decided

SPEC E2-B 9.7 adopts **B'** for cross-paragraph ranges: dispatch the format
command, then verify by reading back the **surviving original selection** and
requiring its text to be byte-equal to the text captured before the dispatch;
if that cannot be done, return the "dispatched, could not verify" typed failure
that 2.3 and 3.5 already define.

That adoption is an **owned deviation** from the pre-registered disposition,
which was refusal only. 9.7 names three checks, any one of which sends the
decision back to **A** (refuse before dispatch). This file predicts all three
before running any of them.

**All three run with zero relinks.** They are native, on the same 26.8 source
tree the shipped engine is built from, so they answer "does the core do this",
not "does the wasm artifact do this".

## Why native and not the browser harness

B' reads the selection **after the uno command and before anything collapses
it**. The shipped engine's barrier collapses to its restore point and re-selects
with `.uno:SelectText`, so from JavaScript the surviving selection is not
observable on this build. Making it observable is an engine change — which is
the relink these checks exist to de-risk. Native LOK has the calls directly.

The cost is the standing one (`handoff` trap 3): this probe waits with fixed
sleeps, so **callback counts and timings are only citable within a run**, and
any arm that flips between rounds is not citable at all.

## Check 1 — substrate

**Question.** On an ordinary cross-paragraph selection, does
`getTextSelection("text/html")` return, and is the markup something the
readback parser can enumerate per block?

**Prediction: it returns, and the markup contains two block elements.**

*Basis.* The plain-text variant already works on exactly this selection: the
gate recorded `selectionBeforeDispatch.text = "E1-MULTI-START alpha\n第二段中文
beta"` in all six G3 runs. The HTML variant goes through the same
`pDoc->getSelection()` (`init.cxx`), and `multi-paragraph.odt` contains no
frame, no footnote and no image — none of the shapes findings 037/038 wedge on.

*Why the check exists anyway.* This call is in the family that findings 037 and
038 measured wedging. "This fixture has none of the wedging shapes" is a reason
to expect it to return, not a measurement that it does.

**If it wedges, or the markup cannot be enumerated per block → A.** B' would
have no verification substrate.

## Check 2 — survival

**Question.** After `.uno:DefaultBullet` is dispatched on a cross-paragraph
range, does the selection survive with **identical** text?

**Prediction: it survives, with identical text.** This is the least supported of
the three and I expect it least confidently.

*Basis.* `.uno:DefaultBullet` changes paragraph attributes; it is not a cursor
movement and not a text edit. Paragraph-level formatting does not change text
content, so if the selection survives at all, byte-equality should follow.

*What I do not have.* No prior measurement. Every gate arm reports
`collapsedAfterDispatch: true`, but that is the **barrier deliberately
collapsing**, not the command's own effect — it says nothing about what the
selection looked like in between. Recorded here so this is not later mistaken
for supporting evidence.

**If the selection does not survive in the common case → A.** B' would fall back
on every multi-paragraph press, so every correct outcome would be reported as
"may have changed, check and undo" — worse for a user than A's clean refusal.

## Check 3 — undo

**Question.** Is a cross-paragraph format dispatch a **single** undo step?

**Prediction: one `.uno:Undo` restores both paragraphs.**

*Basis.* Writer wraps a list toggle over a multi-paragraph selection in one undo
action. This is an expectation about Writer, not a measurement.

*Judged on the document, not on a return value* — the same rule the gate uses.
The probe saves the ODT three times (before dispatch, after dispatch, after one
undo) and a separate judge compares them. Pass requires **after-undo equals
before-dispatch** on the paragraph signature of all five paragraphs.

**If it takes more than one undo → A.** 2.3's fallback tells the host to prompt
the user to undo; if one undo leaves the document half-changed, that instruction
is dishonest for this class, and shipping a dishonest recovery message is worse
than refusing.

## Positive controls

Each check needs an arm that would come out differently if the probe were
measuring nothing:

- **Check 1** also reads the HTML of a **single-paragraph** selection. One block
  there and two in the cross-paragraph case is the discriminating pair; two in
  both would mean the count is not reading paragraphs.
- **Check 2** also runs the same dispatch on a **single-paragraph** range. If the
  selection does not survive there either, survival is not a cross-paragraph
  property and check 2's reading changes.
- **Check 3** also undoes a **single-paragraph** dispatch. If that needs two
  undos, the fixture or the dispatch is wrong, not Writer's undo grouping.

## Rounds

Three rounds of every arm. Any arm whose verdict is not identical in all three
is recorded as unstable and **may not be cited** — arms F, Y and Z of task #49
flipped exactly this way under the same fixed-sleep probe.

## What these checks do not decide

- They do not measure the WASM artifact.
- They do not establish that B' is implementable, only that its substrate exists.
- They do not touch section 5's protocol blockers, which are separate.

---

# Addendum, round 2: separating a confound I built into my own control

**Written and committed after round 1 and before round 2 runs.** Round 1's
records are in `native-round1/` and are not revised by this.

## What round 1 found

- **Check 1 passed**: `text/html` returned in 0 ms, 630 bytes, **2 blocks** for
  the cross-paragraph selection against **1 block** for the control.
- **Check 3 passed**, judged on the documents: the dispatch changed two
  paragraphs (one in the control) and **one** `.uno:Undo` restored every
  paragraph signature exactly, 3/3 in both arms.
- **Check 2 came back against the prediction.** The selection survived (type 1,
  52 bytes) but its text was **not equal**: `"    • E1-MULTI-START alpha\n
  • 第二段中文"`. The bullet markers are serialised into the plain-text
  readback. My stated basis — "paragraph formatting does not change text
  content, so equality is exact" — is true of the document and false of
  `getTextSelection`.

## The confound, which is mine

The control selected a **partial** range inside paragraph 1 (the anchor
rectangle covers `E1-MULTI-START`, not `E1-MULTI-START alpha`). So it differed
from the test arm in **two** ways at once: one paragraph versus two, and partial
versus whole. Its `textEqual: true` therefore cannot be attributed.

It is not that the control failed to apply the bullet: the saved documents show
`dispatchApplied: true` for every control round. A partial in-paragraph
selection simply reads back without the marker.

## Round 2's new arm and its prediction

**`single-paragraph-whole`**: the whole of paragraph 1, same y, `x2` far to the
right so the range runs to the end of the line — the geometry the browser gate
uses. One paragraph, no paragraph boundary crossed.

**Prediction: it reads back WITHOUT a bullet marker, so `textEqual` is true.**

*Basis.* Round 1's cross-paragraph readback put a marker on **both**
paragraphs, including the second one, which was only **partially** selected.
So the marker does not track "is this paragraph wholly selected". The remaining
candidate is that it tracks **whether the selection crosses a paragraph
boundary**: inside one paragraph the serialiser emits a text fragment, and
across a boundary it emits block structure with decoration.

**If this prediction holds, the consequence is on B', not on the probe.** The
equality gate SPEC E2-B 9.7 adopted — pre-dispatch plain text must equal
post-dispatch plain text — would then be **broken exactly in the cross-paragraph
case B' exists for**: every successful list dispatch would fail its own
verification and return "dispatched, could not verify". B' would collapse into
fallback-always, which is check 2's stated disqualifier.

That is a repairable break rather than a refutation — the comparison could
normalise list decoration, and a selection that shrank by a paragraph would
still be caught by the missing text. But the repair is a change to an
adjudicated construction, so it goes back to the adjudicator rather than being
adopted here.

**If the prediction fails** — a whole single paragraph also gains a marker —
then the marker tracks whole-paragraph selection, the confound resolves the
other way, and the same consequence for B' still follows.

Either outcome breaks the equality gate as literally written. What round 2
decides is **why**, and therefore what a repair would have to normalise.

---

# Addendum, round 3: the partial **leading** paragraph

**Written and committed after round 2 and before round 3 runs.** Rounds 1 and 2
are not revised by this; round 2's README carries its own correction.

## Why there is a round 3

Round 2 refuted the scope I gave break two. A partially-selected paragraph
inside a **crossing** selection reads back with full list structure — the
cross-paragraph arm's second paragraph is partial (`第二段中文` of
`第二段中文 beta`) and reports `blocks: 2, items: 2`, three rounds out of three.
The false negative is confined to selections that stay **inside one paragraph**,
which is the case the existing `.uno:SelectText` barrier already handles.

But every crossing selection measured anywhere in this project — these native
arms and the browser gate's G3 — **starts at a paragraph head**. Round 2 only
measured a partial **trailing** edge.

**Dragging from the middle of a line is the ordinary gesture.** If the
serialiser goes structure-blind at a partial *leading* edge the way it does
inside a single paragraph, the repaired B' construction has a hole at the
commonest input, and that hole would be structural rather than repairable.

## The arm

**`cross-paragraph-partial-head`**: start the range **inside** paragraph 1 —
after its first word, not at its head — and end inside paragraph 2, exactly as
the existing crossing arm does. One paragraph boundary crossed; **both** edges
partial.

Everything else identical to the existing crossing arm: same fixture, same
`.uno:DefaultBullet`, same three rounds, same document-level undo judge.

## Prediction

**It reads back with full block structure: `blocks: 2`, and after the dispatch
`items: 2`** — the same as the existing crossing arm, and unlike the
within-one-paragraph control.

*Basis.* The discriminator round 2 established is **whether the selection
crosses a paragraph boundary**, not how much of any paragraph it covers. That
was demonstrated on the trailing edge; the serialiser has no obvious reason to
treat the two edges differently, because in both cases it must emit a block
structure to represent the boundary at all. This is an argument from the
mechanism round 2 measured, not a second measurement of it — which is why the
arm exists.

*Confidence.* Higher than round 2's check-2 prediction, lower than checks 1
and 3. The specific way it could be wrong: the serialiser may anchor its block
structure on the selection's **start** node and emit a bare text fragment for a
leading partial, which would produce `blocks: 1` or a missing first `<li>`.

## What each outcome means

| reading | consequence |
|---|---|
| `blocks: 2`, `items: 2` | the repaired B' construction holds at ordinary drags; the routing predicate (pre-dispatch block count) is sound at both edges |
| `blocks: 1`, or fewer items than blocks, or the first paragraph missing from the readback | **structural hole at the commonest gesture → A**, per the adjudicator's flip condition 1 |
| anything unstable across the three rounds | not citable; re-run before it is used for anything |

## Also recorded, not predicted

`.uno:DefaultNumbering`'s decoration prefix is **unmeasured**. The repaired
construction's normalisation needs a **closed, sampled set** of decoration
prefixes per action, and `"    • "` is the only sample taken so far. Round 3
also dispatches `set-list-ordered` on a crossing selection **for sampling only**
— its readback prefix is recorded, not judged, because no prediction was
committed for its value and a sampled constant is not a hypothesis.

---

# Addendum, round 4: does the CROSSING ordered readback carry digits as text?

**Written and committed before the probe change and before round 4 runs.**

## Why

Round 3 sampled `.uno:DefaultNumbering` and found the **plain-text** readback
carries incrementing decoration (`"    1. "`, `"    2. "`). I took that to mean
the decoration set could not be closed as literals, and asked whether numbering
therefore needed a pattern or could not use an identity gate at all.

Both options assumed the gate must run on **plain text**. That assumption is
refuted by evidence already in this tree. The A2 arm's barrier readback, on the
**wasm** artifact, both browsers, three rounds
(`e2b-gate/e2-combination-940b7723/*/result.json`, `formatBarrier.readback.html`):

```html
<ol><li><p style="margin-bottom: 0.08in; line-height: 100%">E1-LC-ISOLATED <font face="Noto Sans CJK KR"><span lang="zh-TW">前後都不是清單的段落</span></font></p></li>
</ol>
```

**A numbered paragraph, and there are no digits in the text content.** The
number is in the `<ol>` structure. The incrementing decoration exists only in
the plain-text serialisation.

So the identity gate moves to **per-block text extracted from the html
readback**, and state stays structure (`items`/`blocks`/tags). Both sides come
from the same serialiser, both list kinds verify the same way, and no
decoration set, pattern or per-action normalisation table is needed.

## The one premise that is still open

That sample is the **single-paragraph** `.uno:SelectText` readback. My probe
parsed the crossing selection's html for `blocks` and `items` but **never
dumped its text nodes** — it recorded counts only. So "the crossing ordered html
has no digits in text" is inference from the single-paragraph case, not a
measurement.

## The arm

Amend the probe to keep the full `html` string before and after the dispatch for
every arm, and check the ordered crossing arm's text nodes for digits.

## Prediction

**No digits in the text nodes of the crossing ordered readback.** Structure
`<ol>` with two `<li>`, each containing a `<p>` whose text is the paragraph's own
text, inline markup (`<font>`, `<span>`) inside it and nothing else.

*Basis.* Same serialiser, same document, and the only difference from A2 is the
number of list items. The plain-text decoration is produced by the plain-text
path, which round 3 measured separately.

*How it could be wrong.* The html serialiser could emit an explicit marker when
the selection does not start at the list's first item — the same "context from
outside the selection" that makes an ordered list start at 3 rather than 1.

## Consequences

| reading | consequence |
|---|---|
| no digits in text nodes | the html-text identity gate closes; **the pattern question never needed answering** |
| digits present | the adjudicator's **contingency** ruling activates: markers must validate as one consecutive ascending integer run across marker-bearing lines, any base; strip at most one *validated* marker per line; any structure violation → cannot-verify with nothing stripped |

Also recorded, not predicted: the A2 body shows text wrapped in `<font>` and
`<span>`, so **extraction must concatenate across inline markup**. Whether that
round-trips genuine text byte-exactly is a separate check and is not claimed
here.

---

# Addendum, round 5: the misfire control

**Written and committed before the fixture and the probe change.**

This is the adjudicator's remaining flip condition: the gate must **pass** on
text that would trip a naive implementation. A gate that only ever fires red is
as useless as one that only ever fires green.

## What is actually required, stated precisely

The gate compares **pre-dispatch html text against post-dispatch html text**.
It does **not** compare html text against the document's characters. So what has
to hold is that the html extraction is **stable between the two reads** — not
that it inverts back to the authored bytes.

That is weaker than "byte-exact round-trip of genuine text", which is how I
phrased it when I sent the question. Both are worth recording, and only the
first is load-bearing:

- **stability** (load-bearing): `blocks(htmlBefore) == blocks(htmlAfter)`
- **fidelity** (recorded, not required): does the extracted text equal the
  paragraph's authored text?

Escaping does not threaten stability on its own: if `&` reads back as `&amp;` it
does so on both sides. What could threaten it is escaping that differs **by
context** — a `<p>` at body level versus the same `<p>` inside `<li>` — which is
exactly what the dispatch changes.

## The fixture

`dist/e2b-fixtures/outline-prose.odt`, four paragraphs, chosen so that a naive
implementation fails:

1. `E2B-OUT-HEAD marker`
2. four leading spaces (`text:s`) then `1. this line already looks numbered` —
   **the shape a decoration-stripping gate would eat**
3. `Ampersand & less-than < quote " and 12. mid-line` — entity-prone, plus an
   outline-looking run that is not at the start
4. `E2B-OUT-TAIL marker`

Paragraphs 2 and 3 are the crossing range; `.uno:DefaultNumbering` is dispatched
on them, so the serialiser's own numbering coexists with text that looks like
numbering.

## Prediction

**The gate passes: per-block text identical before and after, 3/3.**

*Basis.* Round 4 established that the number lives in `<ol>` and the text is left
alone, and the html gate does no stripping at all, so there is nothing that
could eat paragraph 2's leading `1.`. Escaping applies to both reads.

*How it could be wrong.* `text:s` may serialise as `&nbsp;` at body level and as
plain spaces inside `<li>`, or be dropped in one context — a context-dependent
difference, which is the one thing that breaks stability.

**Fidelity is not predicted.** Whether the extracted text equals the authored
characters (entities unresolved, leading spaces preserved) is recorded as a
measurement. If extraction turns out not to be faithful, that is a note for
whoever implements the gate, not a failure of it.

## Consequences

| reading | consequence |
|---|---|
| per-block text identical 3/3 | flip condition 2 does not fire; the html gate is closed on both directions |
| identical on some rounds only | unstable, not citable, re-run |
| differs | **the gate misfires on ordinary prose → A** |

---

# Addendum, round 6: wasm parity, the last flip condition

**Written and committed before the v2 artifact is driven on any range.**

The adjudicator's flip condition 3 has stood unanswered since the beginning:
every cross-paragraph reading in this project is **native**. Whether the WASM
build agrees was a premise, and it could not be measured until B' existed,
because the surviving selection is not observable from JavaScript without it.

B' now exists: artifact `572035ac…`, profile `e2-editor-v2`, and the collapsed
route is already known to work end to end (`tools/run_e2b_smoke.py`).

## What is being checked

For each route, on the WASM artifact, through the product v2 client:

| route | fixture | expectation |
|---|---|---|
| `range-single` | `list-contexts.odt`, one paragraph | `preBlocks == 1`, action completes |
| `range-cross` | `multi-paragraph.odt`, spanning two | `preBlocks >= 2`, `crossIdentityHeld == true`, `crossStateHeld == true`, action completes |

## Prediction

**Both routes behave as the native rounds did.** Specifically: the routing read
returns rather than wedging, `preBlocks` discriminates 1 from 2, and the
cross-paragraph verification holds — because per-block html text is identical
before and after, which is what native rounds 4 and 5 measured fifteen and nine
times respectively without a single disagreement.

*Basis.* The serialiser is the same code in both builds; what differs is the
platform underneath it. The one native-versus-wasm difference this project has
measured is timing, not markup.

*How it could be wrong.* The wasm build's html serialisation could differ in
whitespace or inline markup — the A2 sample from the earlier gate came from
wasm and agreed with native, but that was a single-paragraph readback through
`.uno:SelectText`, not a crossing one.

## What each outcome means

| reading | consequence |
|---|---|
| both routes as predicted | **flip condition 3 does not fire**; B' stands and the manifest keeps `range-cross` |
| `range-cross` verification fails while the document is correct | the wasm serialisation differs from native → **switch the manifest to disposition A** (drop `--cross-paragraph`), which costs no relink |
| the routing read wedges | **disposition A**, and a finding: the 037 guard did not cover this call |

**This is still wiring, not the section 7 measurement.** It reports what the
engine routed and returned; it judges no document and produces no verdict. The
90-run matrix and the negative matrix are what bind, and they run after the
harness and the predictions for them are in place.
