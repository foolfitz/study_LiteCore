# 087: the obvious fix does not work; `aria-activedescendant` does

Measured 2026-09-03 with Orca on the owner's desktop session (consent recorded
in `../manual-round-v12/CONSENT.md`), on a standalone probe page —
`mechanism-probe.html` — that copies the product's shape (a focusable sink plus
a visually hidden projection) and nothing else. **The product was not touched.**

The plan's ruling of 2026-09-04 named both mechanisms as **unmeasured** and said
to measure before trusting either. This is that measurement.

## Result

| arm | mechanism | Orca said | role announced |
|---|---|---|---|
| **A** control | live region, `textContent` only — the product today | `對照組甲 這一行只有文字沒有角色` | — |
| **B** | live region's own node carries `role="heading" aria-level="1"` | `乙臂 這一行的節點帶著標題角色和層級一` | **NO** |
| **B2** | live region's own node carries `role="listitem"` | `丙臂 這一行的節點帶著清單項目角色` | **NO** |
| **C** | `aria-activedescendant` from the sink → heading node | `C 標題節點` then **`heading 1`** | **YES** |
| **C** | → plain paragraph node | `C 普通段落節點.` | — (correct) |
| **C** | → list item inside `role="list"` | **`List with 2 items`** then `C 清單項目節點.` | **YES** |
| **C** | → second list item | `C 第二個清單項目節點.` | list not repeated (correct) |

`orca-mechanism-3.log` (arms A, B, B2, C-heading, C-paragraph) and
`orca-mechanism-4.log` (all of the above plus the corrected list arms).

## What this settles

**Putting the role on the live region does not work.** That is the obvious
one-attribute fix — `el.a11yPara.setAttribute("role", "heading")` beside the
existing `textContent` assignment — and Orca announces the text and nothing
else. Twice, for two different roles. **The ruling was right to forbid trusting
it unmeasured**, and right that the `paragraph` role sitting there today proved
nothing by its silence: a *different* role is equally unspoken.

**`aria-activedescendant` into a roled node works, for both roles the criterion
names.** `heading 1` is the role and the level. `List with 2 items` is the list
container, announced once on entry and not repeated on the second item — which
is what a screen reader is supposed to do and what
`queue-list-prefix-read-twice` would have to be re-measured against.

## Two limits, stated

**One AT, one version.** Orca on this machine. NVDA and VoiceOver are
unmeasured, and 4b was always about one AT by construction.

**Arm C switches Orca to Browse mode** (`23:48:23 Browse mode` right after the
heading). Whether that interferes with typing in the real product is unmeasured
and is exactly the kind of thing the human round exists to catch. It is not a
reason to prefer B — B does not work at all — but it is a named risk for the
fix's own manual round.

## The probe's own defect, and why it is in the record

The first run of arm C's list case put `role="listitem"` under a plain `div`.
That is invalid ARIA — a list item outside a list — and Orca announced the text
with no role. **That reading was about the fixture, not about the mechanism.**
Wrapping the items in `role="list"` produced `List with 2 items` immediately.

Kept because the failure mode is the one this tree files most often: an
instrument's own defect wearing a product result's clothes. The difference
between "the mechanism does not carry list structure" and "my fixture was not a
list" is one attribute, and only the re-run tells them apart.

## Three attempts before a valid run, and why the first two were void

**The control arm is what caught both.** Runs 1 and 2 produced nothing at all —
not even arm A, which is the product's current behaviour and must speak.

* Run 1: `sink.focus()` focuses an element; it does not make the window active.
  Orca's `live-regions/present-from-inactive-tab = False` then discards every
  update — the same policy the 2026-09-04 ruling identified for
  `E1-LC-NUMBER-TWO`.
* Run 2: `Page.bringToFront` does not raise a window on Wayland either.
* Run 3: launching Chrome with `--new-window` immediately before driving —
  a new window takes focus from the compositor — and clicking the sink through
  CDP input events. All six arms spoke.

**Without arm A there would have been a conclusion.** Runs 1 and 2 would have
read as "neither mechanism works", which is the opposite of the answer for C.
