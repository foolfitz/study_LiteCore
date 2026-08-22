# §3.4 baseline: what a screen reader gets from the editor page today

Measured 2026-08-22, **before** any projection code exists, with
`tools/probe_aria_projection.py` on profile `a11y-gate0` (the core that
provides accessibility — so this is the *best* case, not a handicapped one).

## The number

**171 accessibility-tree nodes. Zero of them carry a character of the
document.**

```
nodeCount:            171
documentTextInTree:   false
nodesCarryingDocumentText: []
```

The whole document region is one node:

```
Canvas   name="ODT 文件畫面"   value=None
```

Roles present: `RootWebArea`, `Canvas`, `StaticText`, `InlineTextBox`,
`generic`, `button`, `combobox`, `option`, `textbox`, `status`, `code`,
`LineBreak`, `MenuListPopup`.

Roles **absent**, and this is the content of the finding: no `document`, no
`paragraph`, no `heading`, no `list`, no `listitem`. The 52 `StaticText` and 58
`InlineTextBox` nodes are the toolbar, the status strip and the fixture
dropdown — page chrome, every one of them.

So a screen reader on this page announces the toolbar buttons and then
"ODT 文件畫面, canvas". A nine-paragraph document is one image with a label.

## Why this is a measurement and not a human report

"A screen reader has to read it, so a person has to try it" is a **falsifiable
claim, not a category**. Finding 073 made exactly that mistake about IME
composition — filed under human-only by definition — and CDP's
`Input.imeSetComposition` refuted it the same day.

The accessibility tree is what every screen reader consumes, the browser builds
it, and CDP exposes it through `Accessibility.getFullAXTree`. So the
before-picture is measurable, and **the same instrument will measure the
projection that is supposed to replace it**. A before-and-after on one
instrument is worth more than two impressions.

What this instrument does **not** cover, stated rather than left to be
discovered: how a particular screen reader *renders* the tree (announcement
order, verbosity, browse-mode behaviour) is the AT's own business and is not in
this tree. That part stays human, and naming it narrowly is the point — it is a
smaller claim than "a11y needs a human".

## Not judged

`outcome: SEE_NODES`, `judges: null`. §3.4's gate G3.4-1 has no threshold
written yet (`research/DESIGN-2026-08-22-aria-projection.md` §6), and inventing
one from this first output would turn the highest-uncertainty question in §3.4
into a formality — the order the a11y gate 0 prediction was written to refuse.

This file is the *before*. The threshold goes in a prediction, written before
the projection is built.

## Reproducing

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 tools/probe_aria_projection.py --browser chrome --out <path>
```

Chrome only: the AX tree is a CDP domain and the Firefox session here has no
CDP. Raw record: `baseline-2026-08-22.json` (all 171 nodes).
