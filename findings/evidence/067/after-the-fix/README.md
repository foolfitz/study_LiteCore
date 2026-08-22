# Finding 067, after the fix — shell v27 (2026-08-22)

The product half only. The engine half (`handleInsertText` incrementing the
revision unconditionally) is unchanged and still needs a relink.

## The shipped runner

| | Chrome | Firefox |
|---|---|---|
| `ok` | **true** | **true** |
| `the-enter-key-reaches-the-document` | **PASS** | **NOT_ESTABLISHED** |

Chrome's two arms:

| key | paragraphs | markers together | `<text:line-break/>` between |
|---|---|---|---|
| Enter | 10 → **11** | **no** | no |
| Shift+Enter | 12 → **12** | yes | **yes** |

Firefox abstains by design: the check needs a **real** key through CDP, because
only a real key runs the default action that produces `beforeinput`. A
synthesised keydown would pass this on a page where the binding is absent —
which is how 067 survived in the first place.

**The oracle is the paragraph count, never the revision.** Under 067 the
revision advanced on every broken press while `content.xml` stayed
byte-identical; the counter is the thing that lied.

## `mutation-enter-key-not-bound.json`

Disabling the branch (`--mutate enter-key-not-bound`) turns **only** the owning
check red, and its arms go back to 067's numbers exactly: paragraphs 10 → 10 and
11 → 11. The declared `alsoRed: []` is measured, not asserted.

## `probe-real-enter.json`

The diagnostic probe's own arm across the same change: FAIL → **PASS**,
paragraphs 9 → 10, `contentIdentical` false, control still landing on both sides
of the key.

## What is NOT covered

A `beforeinput insertLineBreak` that arrives **without** a keydown — a mobile
virtual keyboard, autocorrect — still reaches the frozen adapter's
`commitText("\n")` and still hits the engine no-op with a lying revision.
Unmeasured, deliberately not pre-fixed.
