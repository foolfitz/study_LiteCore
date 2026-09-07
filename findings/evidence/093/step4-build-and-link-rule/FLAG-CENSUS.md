# The packaging flag census — one flag out at a time, on the real builder

Finding 093 option B, step 4. Taken 2026-09-08. **No link was run**; the builder
only copies an existing loader and wasm and writes JSON, so every case below was
produced from `build/archive/e2-editor-v10-4ec1e389-worker-070229cd-manifest-d57de339/`
into a scratch directory. `dist/profiles/**` was not written.

## Why this census exists

The step-3 amendment to the runbook recorded that omitting
`--document-outline-geometry` fails **silently**: the engine emits the
rectangles, the manifest does not declare them, the page reads no declaration
and takes its honest-degradation path (`data-geometry="absent"`), and the
product path's new check PASSES — because that path is the legal state the check
was written to protect. The result is a new identity, five pins dropped, and
behaviour identical to before the link.

The runbook's response was to write the flag down. Writing it down is what a
person does once and a tired person skips once. So the rule asserts the
manifest that comes **out** instead, and this census is the measurement that
says the assertions have discriminating power — the AGENTS.md §5 question,
"find a mutation that turns nothing red", asked as a full enumeration of the
flags rather than a sample.

The assertions live in `V13_MANIFEST_MUST_DECLARE` in `wasm_sdk_probe/Makefile`.
Each names a **declaration in the output**, never a flag on the input, so they
are not a mirror of the command line they guard.

## The command being censused

```
python3 tools/build_e2_editor_v4_profile.py \
    --source-manifest sdk/r6-writer-review-manifest.json \
    --loader  <artifact>/probe.js \
    --wasm    <artifact>/probe.wasm \
    --worker  sdk/sdk-worker.js \
    --exports <artifact>/exports.txt \
    --profile e2-editor-v13 --paragraph-text --document-outline \
    --document-outline-geometry \
    --inline-range-gestures all --core-data ../wasm-lite/build-a11y-gate0 \
    --split-core-data \
    --output  <dir>
```

## Result

| case | builder | assertions | what caught it |
|---|---|---|---|
| **full line** | exit 0 | **all 9 green** | — |
| `--profile` dropped | **exit 1** | (no manifest produced) | the builder refuses to grant range gestures under `e2-editor-v4`'s frozen name |
| `--paragraph-text` dropped | exit 0 | **RED** | `"caretParagraphText"` absent |
| `--document-outline` dropped | exit 0 | **RED** | `"documentOutline"` absent |
| `--document-outline-geometry` dropped | exit 0 | **RED** | `"documentOutlineGeometry"` absent |
| `--inline-range-gestures all` dropped | exit 0 | **RED** | `"inlineRangeEvidence"` absent |
| `--inline-range-gestures range-single` (narrowed, not dropped) | exit 0 | **RED** | `"inlineRangeEvidence"` absent |
| `--core-data` dropped, `--split-core-data` kept | **exit 1** | (no manifest produced) | the builder refuses: nothing to slice |
| `--split-core-data` dropped | exit 0 | **RED ×4** | `"./base-e2-editor-v13.`, `"cjk-e2-editor-v13"`, `"fallback-fonts-e2-editor-v13"`, `9901e9be29c9ded2` |
| both `--core-data` and `--split-core-data` dropped | exit 0 | **RED ×4** | same four |
| right flags, **wrong core** (`build-headless-probe`) | exit 0 | **RED** | `9901e9be29c9ded2` absent |

Nothing gets through. Two of the seven flags the builder refuses by itself; the
other five each land on a named declaration.

The two builder refusals, verbatim:

```
refusing to grant unmeasured inline range gestures under the product's own name
(e2-editor-v4). Pass --profile with a diagnostic name: a manifest that claims
coverage the evidence does not have is the one thing this contract exists to prevent

--split-core-data needs --core-data: there is nothing to slice. Splitting the
PRODUCT core's shared image is not what this flag does and would put a second
copy of those packs in a profile directory
```

## Two assertions this census killed before they shipped

**`"range-cross"` has zero discriminating power.** It was the obvious test for
`--inline-range-gestures all` and it is worthless: the paragraph actions carry
`range-cross` unconditionally and `gestureBits` names it, so the substring is in
the manifest whether the flag was passed or not. `drop-gestures` came out
**green** on the first census run. `"inlineRangeEvidence"` replaced it, and the
`range-single` row above is why the replacement was checked against a *plausible*
wrong value and not only against the flag's absence.

**Pack names cannot say which core was sliced.** Every name-shaped assertion
(`./base-e2-editor-v13.…`, `cjk-e2-editor-v13`, `fallback-fonts-e2-editor-v13`)
passes when the profile is packaged against the **product** core, because the
names are built from the profile name, not the image. Measured: the base pack
comes out `ba15a988a7fec468` instead of `9901e9be29c9ded2`. The bare hash
literal in the checker exists for that one hazard, and it is the reason it is
listed as a separate line with its own message rather than folded into the
`--split-core-data` group — they are two different failures and one sentence
covering both would say one of them wrong.

## A cross-check that fell out of the census

The full-line run produced pack files whose content hashes are **identical** to
the ones `e2-editor-v12` ships:

```
base-e2-editor-v13.9901e9be29c9ded2.data     v12: base-e2-editor-v12.9901e9be29c9ded2.data
cjk-e2-editor-v13.b76b0433203017ca.data      v12: cjk-e2-editor-v12.b76b0433203017ca.data
fallback-fonts-e2-editor-v13.33856e2a082148dd.data
                                             v12: fallback-fonts-e2-editor-v12.33856e2a082148dd.data
```

The slice is deterministic over the same core image, so the data packs are not
a source of variance between v12 and v13. Only the wasm, the worker, the
manifest and the profile name will move.

## Reproducing

The scratch outputs were not kept — they contain a 135 MB copy of v10's wasm and
a v13-named manifest that is **not** a real v13 and must not be mistaken for
one. Re-running the table is the command above with one flag removed per run,
then:

```
python3 -c "$V13_MANIFEST_MUST_DECLARE" <dir>/sdk-manifest.json
```

with the variable taken from the Makefile (`make` exports it).
