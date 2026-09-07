# Finding 093, phase 2 — where `#a11y-doc` sits, and what it costs the viewport

Measured 2026-09-08 by agent, against the pre-registration written into
`findings/093-...md` (section "Phase 2 的預先登錄") **before any number in this
file existed**. The four measurements below are that pre-registration's four,
in its order. No outcome was added or moved.

- Instrument: `wasm_sdk_probe/tools/probe_093_a11y_region_position.py`
- Raw: `phase2-region-position.json` (Chrome default viewport),
  `phase2-region-position-1920x1080.json` (1920x1080)
- Fixture: `a11y-audible` — the one the owner's walk used, named in the Orca log
  at 00:10:43.828 (`'範例文件' combo box 'a11y-audible'`)
- Browser: headless Chrome, its own temporary profile. The owner's Chrome was
  not touched.

## Scope, stated so it is not over-read

This probe measures **geometry and scroll**. It does not run a screen reader
and makes no claim about what Orca does. It answers where the region sits and
what scrolling its contents into view costs `.desk`. The link from that to the
owner's observation is the same link finding 069 already established for
`#sink`, and it is not re-established here.

## Measurement 1 — `#a11y-doc.offsetTop` against `#canvas.offsetHeight`

| | v8 (shipping) | v12 (candidate) |
|---|---|---|
| `#a11y-doc.offsetTop` | **928** | **928** |
| computed `top` | `929px` | `929px` |
| computed `left` | `0px` | `0px` |
| `#canvas.offsetHeight` | 929 | 929 |
| `.paper` height | 929 | 929 |
| offset parent | `paper` | `paper` |
| `#sink.offsetTop` (069's fix, for contrast) | **80** | **80** |

`#a11y-doc` sits at the bottom of the paper on **both** profiles, at the full
height of the canvas. The 1px gap between `offsetTop` 928 and computed `top`
929px is `.a11y-only`'s `margin: -1px`.

`#sink` at 80 in the same reading is the internal control: the element that
*did* get 069's fix is riding the caret, in the same page, at the same moment.

At 1920x1080 the same numbers scale together: `offsetTop` 1152, canvas 1153,
both profiles.

## Measurement 2 — the fraction of `.desk`'s scrollable room

`desk.scrollTop = 0`, then `target.scrollIntoView({block: "nearest"})`.
Fraction, not pixels, for the reason 069 records: its first criterion demanded
"< 50px", measured 125, and failed a working fix.

Chrome default viewport (`.desk` 139px tall, room 830px):

| target | v8 | v12 |
|---|---|---|
| `#a11y-doc` | 810px = **0.9759** | 810px = **0.9759** |
| `#a11y-para` | 810px = **0.9759** | 810px = **0.9759** |
| first projected node | (none) | 810px = **0.9759** |
| `aria-activedescendant` node | (none) | 810px = **0.9759** |

1920x1080 (`.desk` 864px tall, room 329px): **0.9392** on every target, both
profiles.

**The fraction is not a function of the window**, which is what the second
viewport was run to test rather than assert.

## Measurement 3 — the structure projection, and the stop count

Sampled 16 times over 8 seconds, **fixed count with no early exit**, so both
profiles get identical treatment (a loop that stopped at the first `projected`
would give v12 as long as it needed and v8 the full wait, and the difference
between the two is the measurement).

| | v8 | v12 |
|---|---|---|
| `#a11y-structure` states across 16 samples | `unavailable` x16 | `unavailable` x2, then `projected` x14 |
| `aria-hidden` | `true` | absent |
| children | 0 | 8 (`data-paragraphs` = 10) |
| `#a11y-para` reason | `profile` | `paragraph` |
| sink `aria-owns` | absent | `a11y-structure` |
| sink `aria-activedescendant` | absent | `a11y-node-0` |
| **browsable stops inside `#a11y-doc`** | **1** | **13** |

v8's single stop is the reason sentence
「這一版引擎沒有提供段落文字，所以無法朗讀文件內容。」

"Browsable stop" = a descendant of `#a11y-doc` that is not under an
`aria-hidden` ancestor and carries non-empty text. v12's 13 counts the
`#a11y-structure` container and the `role="list"` wrapper alongside the 10
paragraph nodes; the count is reported as measured rather than filtered down to
the number the prediction expected.

## Measurement 4 — the positive control

`#a11y-doc.style.top = '0px'; left = '0px'` on the live DOM — 069's fix, given
to the element that never received it. **Not** an edit to `e2-editor.html`:
that file is hashed by nothing (finding 094), so an edit to it would not turn a
single check red, which is the reason not to make one. The mutation is the same
shape 069's own probe used in the opposite direction
(`PARK_SINK_AT_THE_BOTTOM`), and it is reverted after the reading.

| | before | after |
|---|---|---|
| `#a11y-doc.offsetTop` | 928 | -1 |
| scroll fraction, every target, both profiles, both viewports | **0.9759 / 0.9392** | **0.0000** |

**The control collapsed.** Outcome O-4 did not fire.

## Which pre-registered outcome fired

- **O-1 — fired.** Both profiles: `offsetTop` 928 against a 929px canvas, and
  scrolling the region's contents into view consumes 0.9759 of the scrollable
  room. Shared mechanism, not candidate-introduced. **With one deviation from
  the pre-registration's wording, recorded rather than rounded away** — see
  below.
- **O-2 — fired.** v8 has **1** browsable stop in the region, v12 has **13**
  (10 paragraphs). Same defect, one stop against one per paragraph.
- **O-3 — did not fire.** The geometry is identical on both profiles to the
  pixel. Phase 1's source reading stands.
- **O-4 — did not fire.** The control collapsed to 0.0000.

## Two things the pre-registration did not anticipate

**1. The fraction is 0.9759, not the "≳99%" O-1 asked for.** Stated plainly
because rounding it up would be fitting the number to the outcome. The 2.4%
shortfall is fully accounted for and is not evidence against the mechanism:
`.desk` has `padding: 20px` (`e2-editor.html:77-78`), so `scrollHeight` is
969 = 929 paper + 40 padding, while `block: "nearest"` stops as soon as the
target's bottom edge reaches the viewport's bottom edge and never crosses the
final 20px of bottom padding. 810 is the largest value `nearest` can produce
here. At 1920x1080 the same padding is a larger share of a smaller room, and
the fraction drops to 0.9392 — the residual moves with the padding, as that
explanation predicts. Whether 0.9759 satisfies "≳99%" is a reading of the
pre-registration's wording, and it is left to the gate owner rather than
settled here.

**2. Measurement 3 is time-dependent, and the first run got a different
answer.** The first 1920x1080 run read v12 as `unavailable` with 0 children —
i.e. it recorded v12 looking exactly like v8 — because the probe settled for
1.5s and v12 needs roughly 1.0–1.5s after `ready` to project. The settle trace
was added in response and shows the transition directly (2 samples
`unavailable`, then 14 stable `projected`). `projectStructure` documents this
transient itself (`web/e2-editor-app.js:267-270`: two readings on 2026-08-23
came back with no tree at all). **A single reading of measurement 3 is a coin
toss on v12, not a profile fact**, and the version of this probe that took one
would have reported O-2 as not firing and looked green doing it.

## Not measured

- Whether Orca's browse cursor moving between these nodes is what triggers the
  scroll in practice. This probe drives `scrollIntoView` directly. The owner's
  two walks and finding 069 are the evidence for the link; this run does not
  add to it.
- "Press Tab after the page is at the bottom and see where focus lands" — the
  direct discriminator named as not-done in 093, still not done.
- The top-boundary focus escape (`leaving panel`, 3 occurrences). Untouched
  here; it is a separate observation and 093 keeps it separate.
