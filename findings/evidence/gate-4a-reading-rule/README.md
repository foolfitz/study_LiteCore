# The instrument was reading DOM order, and one term was checking a pointer against itself

Evidence for the gate amendment of 2026-09-05 (Rulings 1 and 2), in
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`.

## What was wrong

Gate condition 4a term 4 asks whether the caret's paragraph reaches the
accessibility tree. Since 2026-08-23 the probe answered it by taking **the name
of the first AX node, in full-tree order, carrying the fixture marker**. That is
not a fact about focus. `#a11y-para` precedes `#a11y-structure` in
`e2-editor.html`, so the "first marker node" was the live region for no reason
other than source order.

Term 8, added 2026-09-04, then took its *expectation* from term 4's reading. Two
consequences, both measured rather than argued:

* **The rule reddens on a change to nothing it names.** Placing the structure
  subtree before the live region turns term 4 red on every held record
  (`replay-2026-09-05.txt`, `[reorder] A: t4=R`). The product is untouched.
* **With the live region emptied and the pointer correct, term 8 went red on a
  pointer that was right** — `findings/evidence/088/4a-with-live-region-silenced-TERM4-AND-8-RED.json`.
  The reading fell back to the heading three times, so term 8 expected `heading`
  at all three placements.

That is the second half of the 088 residue story: the fix attempt was reverted
because two checks went red, and at least one of those two was the instrument.

## What changed

**Ruling 1** — `axReading` is the text under the node the AX tree marks as the
active descendant of the focused node: its name, else its descendants' text
concatenated. A `paragraph`-role node has no accessible name, so a name-only
rule reads `['E1-LC-HEADING', '', '']` (RED 1 below). If the tree carries no
such relation the reading falls back to the live region, which keeps finding
087's natural red case red — a pointer-only rule turns `3dfdcfef`'s term 8
green and erases it.

**Ruling 2** — terms 4 and 8 compare placement *i* against fixture paragraph
*i*, read from `content.xml`, gated on the run finding as many bands as the
fixture has paragraphs and on each placement's recorded `bandIndex` agreeing
with its index. Before this, term 4 accepted a reading that matched *any*
fixture paragraph and term 8 took its expectation from the reading, so a pointer
aimed at the wrong paragraph satisfied both — term 8 was comparing the pointer
with itself.

## The files

* `replay_readings.py` / `replay-2026-09-05.txt` — three candidate definitions
  of the reading over six held records, with the reorder and mispoint
  mutations. This is the measurement the ruling rests on. It re-implements the
  two terms, which is why it is a **replay and not the judge**.
* `red_cases.py` / `red-cases-2026-09-05.txt` — the red cases owed under §6.
  These mutate held records and hand them to the real `check_4a.judge` and the
  real `probe_aria_projection.reading_for_placement`. Six cases, all as the
  amendment says:

  | case | red terms |
  | --- | --- |
  | CONTROL: held green record, reread under Ruling 1 | none |
  | RED 1: name-only reading, no subtree fallback | 4 |
  | RED 2a: structure before the live region, OLD rule | 4 |
  | GREEN 2b: the same reorder, Ruling 1's rule | none |
  | RED 3: placement 1's pointer redirected at the heading | 4 and 8 |
  | RED 4: live region silenced AND pointer detached | 4 and 8 |

  RED 3 is the one that pays for Ruling 2. Under Ruling 1 alone it reddens
  nothing in term 8.

## Regression, and the one verdict that moved

The amended judge over the held records:

* `088` runs 1–3 with `gate-4a/control-v8.json` — all terms green, exit 0.
* `087` runs 1–3 — green, exit 0.
* `087/4a-term8-RED-before-the-fix.json` — term 8 red, at placement 0:
  expected `heading`, got nothing. Finding 087's natural red case survives,
  which the pointer-only rule would have erased.

**One held verdict moved, and it is named here rather than left to be found.**
On `088/4a-with-live-region-silenced-TERM4-AND-8-RED.json`, term 8 is now
**green**: its expectation comes from the fixture, and that record's pointer was
correct at all three placements. The file's name records what the *old* judge
said and is left unchanged — renaming evidence that other documents cite is how
a tree loses the ability to check itself. Nothing gated on that record; it is a
diagnostic of a reverted fix attempt, not a banked run. Under the amended
instrument the arrangement it captured would have been judged green on term 8
and red on term 4 only until the reading rule changed too.

## What this does not settle

The 088 residue — the caret paragraph announced twice, once by the live region
and once by the pointer — is still open. Ruling 2 removes the argument that the
live region must keep *announcing* to serve as term 8's independent witness:
the witness is now the fixture. The preferred fix (`aria-live="off"` while a
pointer exists, keeping the text) is unmeasured, and finding 087 is the standing
warning that an obvious one-attribute fix in this area failed.
