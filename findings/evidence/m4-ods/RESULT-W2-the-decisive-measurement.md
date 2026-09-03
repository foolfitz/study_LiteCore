# W2: the candidate opens and renders a spreadsheet — and Calc has no
# accessibility broadcaster

The decisive measurement of `handoff/PLAN-2026-09-03-ods-reading.md` §5, taken
2026-09-03 on `e2-editor-v12`. **Diagnostic evidence**: the bytes are handed
over under a spoofed `.odt` name, because `oxsdk_document_open` rejects any
other suffix before the engine queue (finding 013). Every record carries
`nameSpoofed: true` and none of this may be quoted as the product opening a
spreadsheet — the product refuses to.

## The result

| case | opened | `parts` | `view-ready` | tile | document cost (`sbrk`) |
|---|---|---|---|---|---|
| `d1-anchors.odt` — the positive control | **yes** | 1 | 1580 ms | 254,690 non-paper px | 3.4 MiB |
| `empty-one-sheet.ods` — the empty control | **yes** | 1 | 1221 ms | 72,936 px | 5.1 MiB |
| **`three-sheets-distinct.ods`** | **yes** | **3** | 1269 ms | 73,208 px | 5.1 MiB |
| `one-cell-a1.ods` | **yes** | 1 | 1029 ms | 73,190 px | 5.1 MiB |
| `truncated.ods` — the negative control | **no**, typed `LOK_ERROR` | — | — | — | 1.4 MiB |

**Every branch the plan named as decisive resolved the good way.** `opened`
arrives, `parts == 3` on the three-sheet fixture, `view-ready` arrives on all of
them, and the tile is not the empty tile. The plan's other three branches —
`opened` never arriving, `view-ready` never arriving, the accessibility refresh
wedging the view — did not occur.

**`parts == 3` is the whole discriminator.** A Writer document reports its page
count there; three sheets is not a page count for a fixture that is three cells.
Calc answered.

**The controls did their jobs.** The ODT opened, so a spreadsheet failure would
have been about Calc rather than about the instrument. The truncated file was
refused with a typed error and the worker stayed alive, so "did not open" is
distinguishable from "died". And the empty sheet is **not a blank tile** —
72,936 non-paper pixels, because Calc draws its grid and headers — which is
precisely why G4 compares against that tile rather than against blankness.

## Cross-checked against the native oracle, and one disagreement

| fixture | wasm `parts` × size | native `parts` × size |
|---|---|---|
| `empty-one-sheet.ods` | 1 × 26593 × 13005 | 1 × 26593 × 13005 ✅ |
| `three-sheets-distinct.ods` | 3 × **26593** × 13005 | 3 × **26775** × 13005 |
| `one-cell-a1.ods` | 1 × **26593** × 13005 | 1 × **26775** × 13005 |

Part counts and heights agree everywhere. **Widths differ by 182 twips (0.7%)
on the two fixtures that have content**, and agree on the one that does not.

Registered, not explained: the shape of it — a difference that appears only
where cells carry text — points at column width derived from font metrics, and
the wasm core ships a reduced font set. **That is a hypothesis and it has not
been tested.** It matters because G3 and G4 compare the candidate against
native-derived expectations: a systematic width difference would arrive as a
fidelity failure that is not one. The sweep must decide, before it runs, whether
document width is compared or recorded.

## The finding this measurement was not looking for

Every spreadsheet case, and no ODT case, logs:

```
warn:legacy.osl:sc/source/ui/view/tabvwshh.cxx:237: no accessibility broadcaster?
```

three times, immediately after `open.query-metadata` — which is where
`refreshEditorAccessibility()` calls `setAccessibilityState(view, true)`.

The §3 registration asked what that call does to a Calc view. **Answer: it warns
and continues.** The document opens, the view initialises, the tile paints. It
does not wedge, which is what the plan needed to know.

**But the warning is not nothing, and it is the more important half.** A Calc
view in this build has no accessibility broadcaster, so the projection that
justifies this core's existence — the one gate condition 4a measures, the one
the whole cutover is being paid for — **does not extend to spreadsheets as it
stands.** An ODS viewer built on this core would be as inaccessible as the
product is today.

That is not a reason to stop: the milestone as the owner framed it is *reading*
ODS, and route B is a read-only viewer. It is a reason the milestone must not be
described as "accessible spreadsheet reading" anywhere, and a reason to size
that work before anyone assumes it rides along. Registered as a queue item.

Also logged on every spreadsheet and no ODT:

```
warn:sc:sc/source/filter/orcus/orcusfiltersimpl.cxx:111:
    Unable to load styles from xml file! filesystem error: in file_size: No su...
```

A Calc filter looking for a styles file the reduced filesystem image does not
carry. The document still opens and paints; whether it affects rendering
fidelity is exactly what G3 and G4 are for, and it is named here so that a
fidelity failure later is not investigated from scratch.

## Memory, second data point

`open.begin` is 290,066,432 on every case — the same boot number W1 recorded, to
the byte, across five engine instances. The spreadsheets cost **5.1 MiB** each
against the ODT's 3.4 MiB, all three identical regardless of one cell or three
sheets. That is a floor, not a curve: the ladder (10k, 100k, 1M cells) is what
bends it, and it has not run.

## Two instrument defects, both caught before they could be read as product results

**The mirror silently dropped the probe's own page.** `build_mirror` materialises
an override only when it meets that path while walking the source, so an
override for a file `dist/` does not have is dropped without a word — which is
every file this probe adds. The first run died on a 404 for its own page. Fixed
in the probe rather than in `build_mirror`, whose contract the product path
depends on, and the probe now refuses to start if any override is missing from
the mirror.

**`DocumentHandle` has no `setPart` and no `paintTile`.** Checked before the
first run rather than after: the painting call is `render(region, options)` and
there is no part-switching call at all — which is not a surprise but the plan's
W7. So this probe paints part 0 and reads the sheet count from `handle.parts`,
which the open reply already carries. **The count is the discriminator; part
switching is the next measurement, not this one.**
