# E2-C D1 pre-flight — is an inline format at a collapsed caret visible in the document?

**Artifact**: `e2-editor-v2`, wasm `572035ac…`. **Fixture**: `test-docs/e2/d1-anchors.odt`.
**Date**: 2026-08-15. **Browsers**: Chrome and Firefox. **Not a verdict**: this ran to
decide what D1's criteria may say, before those criteria were frozen for D1.

## The question

The review of SPEC E2-C required D1 to judge each inline format against **its own
anchor in the saved ODT**, because all four return the same completion
(`uno-command-result`) and a mapping error would report the action it was asked for
while changing the wrong property. That requirement is right.

But the manifest declares these ten actions for the `collapsed` gesture, and
`.uno:Bold` at a collapsed caret conventionally sets the **typing attribute** rather
than changing existing text. If the document does not change, then "this anchor
became bold" is a criterion no run can satisfy — and freezing it would have frozen
four cells that must fail for a reason that has nothing to do with the product.

## The measurement

Per format: place a collapsed caret in the anchor paragraph, save; dispatch the
format; save; commit a marker string at that caret; save; then dispatch the same
format on a **range** covering the anchor (characterisation only — the contract does
not declare that gesture) and save again.

**Chrome and Firefox agree on every observation.**

| | `set-bold` | `set-italic` |
|---|---|---|
| engine result at the caret | `changed: true`, revision 0 → 1, `uno-command-result` | same |
| `<office:body>` after that dispatch | **byte-identical to before** | **byte-identical to before** |
| text committed afterwards | lands in a span with `fo:font-weight="bold"` | lands in a span with `fo:font-style="italic"` |
| dispatch on a range | changes the body | changes the body |

## What this establishes

1. **The caret-level format is real.** It is a pending typing attribute: the effect
   is on what gets typed next, which is what a word processor does and what a user
   expects.

2. **`changed: true` here does not mean "the saved document changed".** The engine
   reports a change and advances the revision while `<office:body>` stays identical
   byte for byte. That is not finding 022's shape — 022 was a stale cache reporting
   success for an action that did nothing at all, and here something real did happen
   — but the two are close enough that the difference should be written down rather
   than assumed: **`changed: true` for an inline format at a collapsed caret means
   the engine accepted the command and its state advanced, not that the document's
   bytes moved.** E1's contract has been shipping that meaning without stating it.

3. **D1's oracle for the four inline formats is therefore**: dispatch at the caret,
   commit a marker unique to that action, and require the marker's span to carry the
   property (and for the `-false` cells, to lack it). This stays inside the declared
   gesture, and it is still attributable per action, which is the property the review
   asked for.

`e2/validation-matrix-v1.json` was amended accordingly **before D1 ran**; each amended
cell carries an `amended` field naming this evidence.

## Files

```
<profile>-<wasm prefix>/<browser>/result.json     observations, including the anchor survey
<profile>-<wasm prefix>/<browser>/page.log        the page's own log
<profile>-<wasm prefix>/<browser>/saved/*.odt     four saves per format: before, after-action, after-insert, after-range
```

The anchor sweep runs in a **throwaway document**, never in the one being measured:
the sweep selects, and a selection made by the setup is exactly the state the
measurement is about. Same rule the E2-B matrix carries.
