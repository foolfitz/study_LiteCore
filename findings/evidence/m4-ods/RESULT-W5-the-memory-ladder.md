# W5: the memory question the plan called the real risk is answered, and it is not one

Ladder measured 2026-09-03 on `e2-editor-v12`, diagnostic (spoofed `.odt` name,
finding 013). `handoff/PLAN-2026-09-03-ods-reading.md` §4 named one number as
deciding the shape of the work: **the 100k-cell fixture's peak `sbrk` minus
v12's boot `sbrk`**, with "under ~100 MB and memory is not the risk for the
default class; over ~400 MB and the class shrinks".

**It is 23.6 MiB.**

## The ladder

Boot `sbrk` is 290,066,432 on every case — the same number W1 recorded, across
ten separate engine instances. The kill line fixed before the run is a peak of
939,524,096 (896 MiB).

| fixture | cells | `sbrk` after load | the document's own cost | headroom left |
|---|---|---|---|---|
| `d1-anchors.odt` (ODT control) | — | 293,605,376 | 3.4 MiB | 616 MiB |
| `one-cell-a1.ods` | 1 | 295,370,752 | 5.1 MiB | 614 MiB |
| `empty-one-sheet.ods` | 0 | 295,370,752 | 5.1 MiB | 614 MiB |
| `three-sheets-distinct.ods` | 3 | 295,378,944 | 5.1 MiB | 614 MiB |
| `numeric-10k.ods` | 10,000 | 295,604,224 | 5.3 MiB | 614 MiB |
| **`numeric-100k.ods`** | **100,000** | **314,814,464** | **23.6 MiB** | **596 MiB** |
| `ten-sheets-10k.ods` | 100,000 over 10 sheets | 314,548,224 | 23.3 MiB | 596 MiB |
| `formula-100k.ods` | 100,000 formulas | 340,684,800 | 48.3 MiB | 571 MiB |
| `numeric-1m.ods` — **out of class** | 1,000,000 | 513,667,072 | 213.2 MiB | 406 MiB |

**All ten opened**, including the out-of-class million-cell fixture, and every
one painted a tile.

## Three things the ladder says that one fixture could not

**A spreadsheet has a floor of about 5 MiB and then costs by cells.** One cell,
zero cells and three sheets all cost 5.1 MiB; the shape of that number is the
Calc document and view, not the data.

**Sheets are not a cost axis; cells are.** Ten sheets holding 100,000 cells
between them cost 23.3 MiB, and one sheet holding 100,000 costs 23.6 MiB — the
same number. A ladder that had only varied the cell count on one sheet could not
have said this, and the owner's class is written on both axes.

**Formulas cost about twice what literals do** — 48.3 MiB against 23.6 for the
same 100,000 cells. That is the dependency tree, and it is why the ladder has a
formula rung rather than assuming cells are cells.

**Extrapolating from the 1M rung**: 213.2 MiB for ten times the class maximum,
against 23.6 for the maximum itself, is close to linear in cells with the 5 MiB
floor removed. Under that reading the class could hold roughly **2.8 million
cells** before the kill line, or about **28× the owner's maximum**. Offered as
the shape of the curve, not as a promise: three rungs is not a curve, and the
sentence that matters is the measured one — at the class maximum, 596 MiB
remain.

## The limit of this measurement, stated because it changes what it proves

**These are `sbrk` at the last OPEN stage, not the peak over the whole
lifecycle.** The engine emits stage events through `open.query-metadata` and
stops; the paint that follows allocates a tile buffer (finding 076: malloc'd)
and nothing here observed it. G6 asks for the peak over **open + one tile per
sheet + close**, and this is the open half of it.

So the honest form of the result is: **at the class maximum, the document costs
23.6 MiB and 596 MiB remain for everything the criterion still has to add.** A
tile buffer at 1024×1024×4 is 4 MiB. The conclusion is not close to its margin,
which is why it can be stated before the rest is measured — but the number that
satisfies G6 has not been taken.

Also: one engine per case, disposed between cases, so no cross-open growth is
measured here either. The G6 leak bound still wants five opens on one engine.

## What this changes

The plan called §4 "the real risk" of the milestone after gate 0 turned out to
be paid for. Both are now retired for **reading** at the owner's class:

* gate 0 — the core builds, loads, opens and renders a spreadsheet (W2);
* §4 — the class maximum costs 23.6 MiB against 596 MiB of headroom.

**Neither says anything about writing**, which is M5, and neither says anything
about fidelity, which is G3 and G4 and has not been measured at all.
