# Finding 045 — the inline format actions discard `enabled` and dispatch a toggle

**Artifact**: `e2-editor-v2`, wasm `572035ac…` (the shipped E2-B product).
**Fixture**: `test-docs/e2/d1-anchors.odt`. **Date**: 2026-08-15.
**Browsers**: Chrome and Firefox, one round each, **identical results**.

## The decisive case

A **fresh engine and a fresh document**, a collapsed caret in plain text, one
dispatch, one commit:

```
select the same point twice at E2-D1-BOLD-ON   -> a collapsed caret in plain text
set-bold(enabled: false)                       -> changed: true, revision 0 -> 1,
                                                  completion uno-command-result
insert "OFFONLY" at that caret
save
```

Both browsers produce:

```xml
<text:p text:style-name="P1">E2-D1<text:span text:style-name="T1">OFFONLY</text:span>-BOLD-ON plain</text:p>
<style:style style:name="T1" style:family="text">
  <style:text-properties fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>
</style:style>
```

**Off was requested. On was delivered.** Nothing earlier in that engine's life
could have set a typing attribute: the document had just been opened.

## Why a second case in the same file is NOT evidence

`off-in-plain-fresh-document` is clean. `on-then-off-same-document` is not, and
it is kept here to say so rather than quietly dropped.

That case dispatches `set-bold(true)`, types `ONFIRST`, dispatches
`set-bold(false)` at the same coordinates, types `OFFSECOND`. Both markers come
back bold — but the second insert lands **adjacent to the first**, and text
inserted beside a bold run inherits it. So the observation cannot separate "the
toggle did not turn it off" from "the new text inherited the neighbouring
formatting". It is recorded, and it is not used.

Measuring this properly needs two positions that are **not adjacent**. That is
listed as outstanding in the finding.

## What is in this directory

```
e2-editor-v2-572035ac/<browser>/result.json    observations, with the anchor survey
e2-editor-v2-572035ac/<browser>/page.log       the page's own log
e2-editor-v2-572035ac/<browser>/saved/*.odt    the saved documents, including
                                               off-off-in-plain-fresh-document.odt
```

`result.json` also carries the D1 pre-flight cells (`set-bold`, `set-italic`),
which measured the other half of the picture: a format at a collapsed caret
leaves `<office:body>` **byte-identical**, and the effect appears only in text
committed afterwards.

## Reproducing

```
make e2-c-assets
python3 tools/run_e2_c_d0.py --browser chrome \
    --page e2-c-d1-probe.html --namespace __e2c_d1_probe \
    --fixture d1-anchors.odt --output ../findings/evidence/045
```

The page is `web/e2-c-d1-probe-app.js`. It drives the **product client**
(`editor-shell-v2/narrow-editor-v2-client.js`), not a diagnostic path, so what it
measures is what a host gets.
