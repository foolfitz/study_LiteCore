# The saved ODT crosses both ways, so a revert stays a pointer flip

Revert condition 2 of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`,
measured 2026-08-28.

## What had to be true

A revert from `e2-editor-v11` back to `e2-editor-v8` is only cheap if nothing
written under one is unreadable by the other. Grepped first, so the question
could be narrowed before it was driven: the shell uses no `localStorage`, no
`sessionStorage` and no `indexedDB`, and the checkpoint lives in memory. **The
saved ODT is the only cross-version artifact.**

Both crossings matter. v11 → v8 is the revert itself. v8 → v11 is the other one:
a user who saved before the cutover opens that file after it.

## Measured, through the product's own buttons

Everything goes through the file input and the save button. A round-trip
performed by the harness would be a round-trip nobody ships.

| | v11 → v8 | v8 → v11 |
|---|---|---|
| opened | `from-v11.odt`, "已開啟 from-v11.odt" | `from-v8.odt`, "已開啟 from-v8.odt" |
| state | ready | ready |
| re-saved from the other core is an ODT | **true** | **true** |
| the sentinel text survived | **true** | **true** |
| structure intact | all six fixture lines, headings, list items and the Chinese one | — |

Saved on the candidate: 12,818 bytes. Saved on the shipped profile: 13,242.

**Revert condition 2 is satisfied.**

## The first run said the opposite, and it was not a product result

It reported `markSurvived: false` in both directions. It was wrong, and the
field that caught it was not the one under test:

```
"v11ToV8": { "state": "ready", "doc": "list-contexts.odt", ... }
```

`doc` was still the **boot fixture**. The probe waited for
`state == "ready"` after handing the file to the input — and the page was
already ready before the file was handed over, so the predicate was satisfied
instantly and everything after it described a document that had never been
opened.

Had that been reported, it would have been a **false cross-version
incompatibility finding** — the most expensive kind, because it argues against a
cutover with evidence that is not about the cutover. What prevented it was
recording *which document is in front of you* beside *are you ready*. The two
sentences are not the same, and only one of them can tell a fresh document from
a stale one.

The broken run is kept as `first-run-measured-the-boot-fixture.json`.

## What this does not cover

**One document, one edit.** The fixture is `list-contexts.odt` with a single
committed sentinel. It does not exercise the accessibility core's own additions
— there are none in the file format — but it also does not exercise tables,
images, tracked changes, or a document either core had to repair on open.

**Not a claim about LibreOffice 26.8 in general.** Both profiles are built from
the same core commit; this measures that the two builds agree about the format
they share, not that either agrees with anything else.
