# The saved ODT crosses both ways on v12, so a revert stays a pointer flip

Revert condition 2 of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`,
re-earned 2026-09-03 for candidate `e2-editor-v12`. The 2026-08-28 measurement
was on `e2-editor-v11`; the candidate changed identity on 2026-08-29 and the
re-earn list carries this item forward with nothing dropped, because
byte-identical loader and wasm buy the *speed* of the re-run, not exemption.

Re-runnable:

```bash
cd wasm_sdk_probe
python3 tools/probe_odt_roundtrip.py --candidate e2-editor-v12
```

## What had to be true

A revert from the candidate back to `e2-editor-v8` is only cheap if nothing
written under one is unreadable by the other. Grepped first, so the question
could be narrowed before it was driven: the shell uses no `localStorage`, no
`sessionStorage` and no `indexedDB`, and the checkpoint lives in memory — **the
saved ODT is the only cross-version artifact.**

Both crossings matter. Candidate → shipped is the revert itself. Shipped →
candidate is the other one: a user who saved before the cutover opens that file
after it.

## Measured, through the product's own buttons

| | candidate → shipped | shipped → candidate |
|---|---|---|
| document actually opened | `from-candidate.odt` | `from-shipped.odt` |
| state | ready | ready |
| re-saved from the other core is an ODT | **true** | **true** |
| the sentinel text survived | **true** | **true** |

Structure intact on the crossing back: all six fixture lines, the heading, both
list items and the Chinese one. Saved on the candidate: 13,025 bytes. Saved on
the shipped profile: 13,713.

Bytes named, so the result is about something:
candidate page `3dfdcfef4abfe6b7…`, shipped page `28e03e5bc9fcb8c4…`.

**Revert condition 2 is satisfied on v12.**

## The trap this probe exists around, carried forward

The 2026-08-28 run of this probe first reported the sentinel lost in **both**
directions — which would have been a cross-version incompatibility finding, the
most expensive kind, because it argues against a cutover with evidence that is
not about the cutover. The probe had waited for `state == "ready"` after handing
the file to the input, and the page was **already** ready, so both directions
reported on the boot fixture. *Which document is in front of you* and *are you
ready* are different sentences, and `doc` is the only field that answers the
first. The predicate still waits on the document **name**, and this run's `doc`
values above are the field that says so.

## Provenance of the tool

The 2026-08-28 probe hard-coded `e2-editor-v11`. It was lifted into
`wasm_sdk_probe/tools/probe_odt_roundtrip.py` and parameterised; the copy in
`findings/evidence/queue-v11-cutover-soak-not-started/` is **not edited** —
it is the record of what that measurement ran, and evidence in this tree is not
rewritten to serve a later run. The lifted version additionally records both
page hashes and computes its own `ok`, so the verdict is not left to a reader's
eye.
