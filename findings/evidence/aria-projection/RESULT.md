# §3.4 first increment — measured 2026-08-23: **G3.4-1 and G3.4-2 both PASS**

Criteria were fixed in [`PREDICTION.md`](PREDICTION.md), written before the
projection existed. The before-picture is [`BASELINE.md`](BASELINE.md): 171
accessibility-tree nodes, **zero** carrying a character of the document.

Same instrument both sides — `tools/probe_aria_projection.py`, reading
`Accessibility.getFullAXTree`.

## G3.4-1 — the reading half

Profile `a11y-projection` (wasm `23233fa7…`), fixture `list-contexts.odt`.

| placement | y | reason | what the ACCESSIBILITY TREE carries |
|---|---|---|---|
| 0 | 0.098 | `paragraph` | `E1-LC-HEADING` |
| 1 | 0.126 | `paragraph` | `E1-LC-ISOLATED 前後都不是清單的段落` |
| 2 | 0.150 | `paragraph` | `E1-LC-SPACER` |

**Three distinct readings, and each is the paragraph actually targeted** —
these are the fixture's paragraphs 0, 1 and 2 verbatim, the same three the gate
0 fingerprints matched against the fixture's own XML. Term 3 is the one that
does the work: three *different* strings would also be produced by a counter.

Node count 171 → 175. Not a threshold; recorded so a later round starts from a
measurement (same reason G0-5 recorded size).

## G3.4-2 — the honesty half

The same page and the same projection on the **shipped** profile
`e2-editor-v4`, whose contract does not declare `caretParagraphText`:

```
regionAtLoad: { reason: "profile", offers: "0",
                text: "這一版引擎沒有提供段落文字，所以無法朗讀文件內容。" }
documentTextInTree: false      (all three placements)
```

Two profiles, one instrument, opposite readings. The region **says why it is
empty** instead of standing empty — an empty document region announces as
"document, blank", which is a confident wrong answer about the user's own file.
The engine already refuses that shape one layer down (`enabled: false`,
`unavailable: "core-built-without-accessibility"`); this is the same rule at
the top of the stack.

## Repeated, because one run is not a regression net

Three runs of G3.4-1, **identical**: 175 nodes, three distinct readings, all
three matching their targeted paragraph when compared against the fixture's own
XML in code rather than by eye. Recorded as runs because an intermittent result
read once gives a confident wrong answer — finding 068 cost five rounds for
exactly that.

Raw records: `gate-run1/2/3-2026-08-23.json`,
`honesty-e2-editor-v4-2026-08-23.json`.

## The product did not regress

`run_e2_c_product_path.py` on the shipped profile: **38 checks, 35 PASS,
`ok: True`** (`product-path-2026-08-23.json`). Two of the three
NOT_ESTABLISHED were already so; the third is this round's new refusal arm
abstaining correctly without its diagnostic flag.

`the-document-region-says-why-it-is-empty` **PASSES** there, observing
`{present: true, offers: "0", reason: "profile", text: "這一版引擎沒有提供段落文字…"}`.
The visual editor is the product; a projection that broke the canvas, the
toolbar or the caret would be a regression and not a trade-off.

Shell generation **v37**, `f9fcfb6b6409363d…`, frozen after these runs rather
than before — a generation is the record of what a round actually ran on.

## The first run was red, and it was red in a third place

Worth more than the pass. Run 1: **one** distinct reading, two placements
reporting `reason: engine`.

`engine` covered four different causes at once, so the run could say "something
upstream is unhappy" and could not say which. **The defect was in the
instrument, not in a conclusion** — which is the cheap place for it. Reasons
were split (`noParagraph` / `disabled` / `stale` / `noText`, several sharing one
user-visible sentence on purpose) and run 2 named it immediately:
`caretParagraph` was absent.

Then the actual defect, which the split exposed: **two writers set the page's
`editorState` and only one had been fixed.** The `editor-state` announcement
MERGES into the snapshot; `editor-session.js` REPLACES it with the `getState`
reply. So whichever landed last decided whether the projected name existed, and
the projection reported "no paragraph" on two of three placements. Adding
`caretParagraph` to the reply branch as well — from the same
`productEditorState`, never a second copy of the rule — took it to 3/3.

That is `queue-product-page-holds-the-raw-editor-state` being real rather than
theoretical: the mitigation had to be applied at **every** writer, and the
first attempt found only one of them.

## What must go red

Mutation `projection-not-wired` removes the single `projectFocusedParagraph`
call from `updateState`, leaving the region present and empty — exactly the
failure the check exists for.

**Run, not asserted** (`mutation-projection-not-wired-2026-08-23.json`):

```
mutation: projection-not-wired
PASS 34   NOT_ESTABLISHED 3   FAIL 1
FAIL :: the-document-region-says-why-it-is-empty
        observed: {"present": true, "text": ""}
```

Against the clean run's `PASS 35 / NOT_ESTABLISHED 3 / FAIL 0`, **exactly one
check moved**, and the observation is the failure in its own words: the region
is *present* and *empty*, which is what a screen reader reads as "document,
blank". A mutation that reddened several checks would not have shown that this
one can fail; a mutation that reddened none would have meant the check was
never tested at all.

The split is deliberate: the product path runs on the shipped profile and can
only measure the **honesty** half, so that is the half it owns. The reading
half needs a profile that carries the text and lives in
`probe_aria_projection.py`.

## Scope, named rather than discovered later

This projects the **focused paragraph**, because that is what the engine hands
over. It is **not a browsable document** — browse mode needs every paragraph
and the engine gives exactly one. Whole-document projection is roadmap §3.4's
route A and was not the route chosen.

Also not covered, and named narrowly: how a particular screen reader *renders*
this tree — announcement order, verbosity, browse-mode behaviour — is the AT's
own business. "a11y needs a human" is wrong; "one AT's reading behaviour needs
a human" is right, and it is a much smaller claim.

## Reproducing

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 tools/probe_aria_projection.py --browser chrome --profile a11y-projection
python3 tools/probe_aria_projection.py --browser chrome --profile e2-editor-v4
```

Chrome only: the AX tree is a CDP domain and the Firefox session here has no
CDP.
