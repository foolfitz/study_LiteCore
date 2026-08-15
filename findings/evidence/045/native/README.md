# Finding 045 native probe — the parameter makes them setters

**Build**: native LibreOffice 26.8 at core `671c848b` (`../build-native-26-8`).
**Fixture**: `wasm_sdk_probe/test-docs/e2/d1-anchors.odt`. **Date**: 2026-08-15.
**Predictions**: `PREDICTION.md` in this directory, registered **before** the probe
was written. **Nothing describes the WASM artifact** — that is a separate run on a
relinked build.

## Result: six of seven predictions held; the one that broke is the one that was
## flagged as unmeasured

| # | arm | predicted | measured | |
|---|---|---|---|---|
| P1 | `param-off` at a caret in plain text | marker NOT formatted | **NOT formatted** | **held** |
| P2 | `param-on` at a caret | marker formatted | formatted | held |
| P3 | `bare` at a caret | marker formatted | formatted | held |
| P4 | `bare` at **two non-adjacent** positions | first on, **second off** | **both on** | **broken** |
| P5 | `param-off` then `param-on`, two positions | off then on | off then on | held |
| P6 | `param-on` over a **selection** | selected text formatted | formatted | held |
| P7 | `param-off` over a selection already formatted | property removed | **removed** | held |

All four commands (`.uno:Bold`, `.uno:Italic`, `.uno:Underline`, `.uno:Strikeout`)
behave identically. 28 arms, each in a freshly loaded document.

## P1 is the one that mattered, and it holds

```
.uno:Bold  {"Bold":{"type":"boolean","value":false}}
```

dispatched at a collapsed caret in plain text, then a marker committed: the marker
lands in a span carrying `fo:font-weight="normal"`. Requested off, delivered off.
The same form with `value: true` gives `fo:font-weight="bold"`.

So the fix finding 045 proposes — one argument string per case in
`probe_engine.cpp:3897-3912`, the same shape as `kListOnArguments` at `:3091` — is
confirmed against core before any relink. That was the point of running this: a
relink in this repo costs an E2-B re-run plus a full E2-C round, and this cost an
afternoon.

## P7 matters nearly as much, and nobody had measured it

`param-off` over a selection that was formatted by the same parameter form removes
the property (`fo:font-weight="normal"` on the previously bold run). **The shipped
product cannot do this at all today** — there is no way to take formatting off a
selection, because the only dispatch form it has toggles.

## P4 broke, and the correction is to the mechanism's wording

The prediction was that a bare dispatch is a shell-wide flip, so a second bare
dispatch — at a **different paragraph**, to keep the markers from inheriting each
other — would come out unformatted. It did not: **both markers are formatted**.

The corrected model: **a bare dispatch toggles relative to the state at the caret.**
Two plain positions both toggle from off to on. This does not weaken finding 045's
headline — `enabled: false` still produces formatted text, measured twice in WASM
and once here — but it does replace "press twice and it turns off" with something
narrower and true: press twice **in the same place** and it turns off; press it in a
plain paragraph and it turns on, whatever you asked for.

The non-adjacent-marker control that finding 045 listed as owed is therefore
**discharged**, with a result that contradicted the prediction. That is the useful
direction for a control to point.

## Files

```
PREDICTION.md                  registered before the probe existed
run/arms.jsonl                 one line per command and arm, with anchor coordinates
run/after-<command>-<arm>.odt  28 saved documents, one per arm
run/sal.log                    the native build's stderr
```

Judge with `python3 tools/analyze_f045_native.py <run>`; `--self-test` checks the
property detector against seven synthetic spans, because "off" is **not** the
absence of the property — LibreOffice writes an explicit `fo:font-weight="normal"`
and `style:text-underline-style="none"`, and a detector that only looks for the ON
pattern reports "off" for a span that says nothing at all.
