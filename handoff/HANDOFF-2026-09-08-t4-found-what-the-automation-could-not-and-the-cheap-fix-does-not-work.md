# Handoff, 2026-09-08 — T4 found what nine soak runs could not, and the cheap fix is measured not to work

Written overnight while the owner slept, after they asked the session to keep
going on its own. Everything below is checkable in the tree. Entry points, in
order: this file, then `findings/093-*.md` (read it whole — the rulings are
appended in order at the end), then
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`'s last two sections.

Tree at `72628a06`, clean. `web/` and `dist/` are byte-unchanged from where the
day started: **no fix has been landed, deliberately.**

## The one thing to read if you read nothing else

`.a11y-only` — the class on `#a11y-doc`, which carries the whole accessibility
projection — is `position: absolute` with **no `top`/`left`**
(`web/e2-editor.html:65-70`). Its static position is therefore the bottom of the
paper, 928px down a 929px canvas on the short fixture and **27,197 down a 27,198
canvas on a real 133-paragraph document**. Browsing into it takes the viewport
with it.

Four CSS rules above sits the comment that explains exactly this hazard, written
when **finding 069** was fixed — and `#sink` got the fix at `:98`. `#a11y-doc`
never did. **069 fixed an element, not a class**, and its regression net follows
suit: it reads `#sink` only, driven by an IME commit, and never measures scroll.

The owner found this with their eyes, in browse mode, with the sound not working,
in about twenty minutes. Nine clean automated runs on the same page had not.

## The gate, as of now

**Soak: 0 of 12.** The owner ruled **D-c** (`ed1ea02a`) — fix it regardless of
classification, because it is an accessibility blocker on an accessibility
product — and D-c's written cost is a restart. **The restart is not mechanically
forced**: finding 094 means the six banked runs would have survived the edit
untouched. The count is zero because the adjudication says the change counts.

Condition 3 and 4b's judgement half were **discharged** by the round, but they
are bound to page `9b29e39b…` and do not survive the page moving.

## What was measured overnight, in order

1. **Phase 2** — the mechanism, both profiles, pixel-identical: `#a11y-doc`
   `offsetTop` 928 against canvas 929; scroll consumes 0.9759 of `.desk`'s room;
   `#sink.offsetTop` 80 (the element that got 069's fix rides the caret);
   positive control collapses the fraction to 0.0000. Outcomes O-1, O-2 fired.
   Two honest corrections are recorded there: my `≳99%` threshold was **not met
   literally** (0.9759, the residual is `.desk`'s 20px padding and
   `block:"nearest"`'s stopping rule, and it moves with window size exactly as
   that explanation predicts), and the executor's **first reading read v12 as
   identical to v8** because it settled 1.5s where v12 needs 1.0–1.5s to project
   — that version would have reported no difference, and it would have been green.
2. **A census** of every `position:absolute/fixed` rule without offsets across
   62 served HTML/CSS files: **exactly one instance of 093's shape, which is 093
   itself.** The defect has not spread. One row could not be settled statically
   (`demo-editor.html`'s `#sink` reachable by native Tab while unpositioned).
3. **Phase 3 — the fix shapes**, against an oracle registered *before the probe
   existed* (`ORACLE-fix-shape.md`, `8edd7cf8`): *after arriving at paragraph N,
   the band the engine renders N in overlaps the visible band by ≥ half a line.*

| shape | short fixture | **133-paragraph document** |
|---|---|---|
| S0 unfixed, v12 **and v8** | 1/3, 1/3 | **0/3, 0/3** |
| S1 `top:0;left:0`, 1 line | 3/3, 3/3 | **0/3, 0/3 — at scroll fraction 0.0000** |
| S2 +2 JS lines | 3/3, 3/3 | 0/3, 0/3 |
| S2b +3 JS lines | 3/3, 3/3 | browse **1/3**, focus 3/3 |
| S3′ node-per-paragraph | 3/3, 3/3 | **3/3, 3/3** |

**S1's row is why nothing was landed.** A perfect 0.0000 scroll fraction with
zero of three paragraphs visible: the proxy scores full marks while the product
is entirely broken. Had the one-line fix been landed on "autonomy", the tree
would have been green, the page would have been unfixed, and per finding 094 no
check would have gone red.

**Per-paragraph geometry does not exist**: the engine's outline walk queries only
`XAccessibleContext`/`XAccessibleText` (`src/a11y_tree_probe.cpp:252-345`);
`XAccessibleComponent`/`getBounds` appear nowhere in `src/`. So the real fix costs
an engine change plus a relink.

## What the owner has to rule on, and why it is a different question now

D-c was chosen when the fix looked like one line of CSS. The price is now an
engine change and a relink. The four options are written at the end of finding
093: **A** ship S3′ (works, but its map is derived by moving the user's caret and
**goes stale on every edit and layout while looking exactly like a correct map**);
**B** the engine route; **C** revert to D-a and defer — supported by a new fact,
that **S0 fails identically on v8, so the cutover does not make this worse**;
**D** land S1 as a stopgap *with its limits written down*, because nothing will
tell the next person otherwise.

**The drafting party did not choose.** If no further ruling ever comes, 093 rests
at "mechanism and shapes measured, nothing landed" and the soak stays at 0.

## Two more things filed overnight

* **094** — `web/e2-editor.html` is hashed by **nothing**. No bundle generation
  v1..v48 includes an HTML path; `served_shell_identity()`
  (`run_e2_c_product_path.py:2303`) walks only `manifest["included"]`;
  `candidateCutover.pageSha256` covers `app.js`; no `check_*.py` reads `.html`.
  Twelve clean runs would assert an identity excluding the file that carries
  every CSS rule — and conversely a behaviour-changing edit to it turns nothing
  red.
* **095** — after ArrowDown at the last line, the next canvas click places no
  caret for 25s, no error, both profiles, 6/6 on the short fixture and not on the
  long one. **Observation, not investigated**, and the harness path has not been
  excluded. Deliberately not merged with the owner's "arrow keys will not bring
  it back": that is arrows, this is clicks.

## The work item that closes only while the count is zero

If the fix lands without a geometry check, we will have fixed a second element
and still not guarded the shape — 069's story, a third time. `probe_093_*` is
wired into neither the Makefile nor `run_e2_c_product_path.py`, and the one check
that touches this DOM (`READ_A11Y_REGION`, `:619`) returns six fields, none of
them geometry.

Adding a check moves the clean-run predicate from 38 PASS / 2 NE to 39 / 2 —
itself a restart — and the count is **already** zero, so this is the one moment
it is free. Its §9 eligibility is better than 094's binding: the form test passes
(the gate document itself records that "every id in `report["checks"]` appears in
`MUTATIONS`" is a tool-closed enumeration), where 094's hand-kept `included` list
fails it. **The window closes with the first new clean run.**

## The link nobody has measured, and everything rests on it

Whether **Orca's browse cursor** is what drives the scroll in practice. Every
verdict above comes from a probe calling `scrollIntoView` itself; the connection
to what the owner experienced rests on 069's precedent and on their two walks.
Measuring it needs Orca running, which speaks aloud, so it waits for the owner to
be awake. **It is the first thing to do when they are.**
