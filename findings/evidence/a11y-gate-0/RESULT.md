# A11y gate 0 — measured 2026-08-22: **PASS**

Criteria were fixed in [`handoff/a11y-gate-0/PREDICTION.md`](../../../handoff/a11y-gate-0/PREDICTION.md),
written 2026-08-21 before the patch and before the core rebuild. Nothing below
was chosen after seeing the output.

> **Does LOK emit a focused paragraph on WASM?** — **Yes.**

## G0-1, the precondition: both halves, on the gate core

`tools/check_core_build_provides.py --build ../wasm-lite/build-a11y-gate0`

```
objectsCompiled: true   missingObjects: []
macro ENABLE_WASM_STRIP_ACCESSIBILITY: 0 (required 0)
callersCompiled: true   provided: true   ok: true
```

First time this guard has been green on any WASM build in this tree. The
product's core is untouched and the same guard with no `--build` is still red,
which is the honest reading: the shipped profile does not provide this.

`sw/source/core/access/` objects: **28** in the gate build, **2** in the
product's.

## G0-2, the gate: three placements, three identities

Three runs, `list-contexts.odt`, Chrome, profile `a11y-gate0`
(wasm `7dddbc6e…`). **Identical on all three runs** — recorded as runs, not as
one, because an intermittent result read once gives a confident wrong answer.

| placement | y | contentLength | listPrefixLength | fingerprint | enabled | fresh |
|---|---|---:|---:|---|---|---|
| 0 | 0.098 | 13 | 13 | `cbf29ce484222325` | true | true |
| 1 | 0.126 | 25 | 0 | `d389fc99dd9a78cf` | true | true |
| 2 | 0.150 | 12 | 0 | `ecb72cdf76d825c2` | true | true |

`unavailable: ""` throughout. `observed` goes `false → true → true` with
`changeCount 0 → 1 → 2`: placement 0's identity came from the **synchronous**
`getA11yFocusedParagraph()` read before any callback had fired, and the
`LOK_CALLBACK_A11Y_FOCUS_CHANGED` path carried the other two. The engine keeps
`enabled` / `observed` / `fresh` as three separate bits precisely so that can
be told apart, and here it was.

### The identities match the paragraphs, and that is measured rather than assumed

The engine's fingerprint is FNV-1a 64 over the paragraph body **after stripping
`listPrefixLength` characters** (`probe_engine.cpp:1614-1667`). Computing the
same hash over the fixture's own XML:

| fixture paragraph | text | len | FNV-1a |
|---|---|---:|---|
| 1 | `E1-LC-ISOLATED 前後都不是清單的段落` | 25 | `d389fc99dd9a78cf` |
| 2 | `E1-LC-SPACER` | 12 | `ecb72cdf76d825c2` |

Placements 1 and 2 match **both the hash and the length** of the paragraphs
their y-fractions land in, in document order. This is the half of G0-2 that
does the work: "three different numbers" would also be produced by a counter.

**PASS**: the bar was ≥ 2 distinct identities each matching the paragraph
targeted. Two match exactly; the third is distinct and is discussed below.

## The control: the same harness on the product profile

Added 2026-08-22, after the runs above. **This is the arm that makes the PASS
mean something**: same harness, same page, same fixture, same three bands —
only the profile and the core differ. Without it, "three distinct fingerprints"
could have been produced by the harness rather than by LOK.

`--profile e2-editor-v4 --core-build ../wasm-lite/build-headless-probe`

The probe **refused** first, which is the refusal working: G0-1 fails on that
core and a gate number from it would be about the patch not having been
applied. Re-run with `--i-know-the-macro-is-set`, which stamps the record
`UNMEASURABLE` — this is a check on the engine's self-report, **not** a gate
outcome, and it may not be quoted as one.

All three placements, identical:

```
enabled: false   unavailable: "core-built-without-accessibility"
contentLength: 0   position: 0   fingerprint: cbf29ce484222325
```

So the two profiles are cleanly opposed, and roadmap §3.5's queue item
(`queue-engine-must-report-core-lacks-accessibility`) is **verified by
measurement rather than by its own note**: the engine no longer claims a
working mechanism on a core that has none.

### And the control found a second lie one level down

`paragraphFresh: true` — on a build where no read can succeed.

On a stripped core every LOK entry point still **exists**;
`getA11yFocusedParagraph()` returns a well-formed empty answer (`content: ""`,
`position: 0`); and `parseEditorSemanticJson`'s postcondition is
`position >= 0 && contentLength >= 0`, which that satisfies. So the engine
recorded a *successful reading of nothing*.

`fresh` is the bit whose whole job is to say "the last read succeeded, so the
fingerprint describes where the caret is **now**". This is the `enabled: true`
defect again, one level down — and it matters directly to §3.4, because an ARIA
projection decides whether to trust a fingerprint by reading exactly this bit.

Fixed in source (`refreshCaretParagraph` returns early with the fields cleared
unless `gEditorAccessibilityEnabled`), syntax-checked against both core
configs, and **not in the product until a link**. Recorded as
`queue-fresh-is-true-where-no-read-can-succeed`.

Worth naming the shape: this was found by running the arm whose only job was to
be a control. The gate would have passed without it.

## The one thing that is NOT clean, stated rather than rounded off

Placement 0 is the heading `E1-LC-HEADING` (13 characters). LOK reported
`listPrefixLength: 13` — **the whole paragraph as list prefix** — so the body
left to hash was empty and the fingerprint is `cbf29ce484222325`, which is the
FNV-1a offset basis, i.e. **the hash of an empty string**. That constant is
already known in this tree as the value that means "unfed" (it is what every
paragraph reported when the offset basis was mistyped, 2026-08-17).

It does not move the verdict — the criterion asks for ≥ 2 distinct identities
matching their targets, and placements 1 and 2 supply that with exact matches —
but it is a real limit on what the fingerprint can identify:

**Any paragraph whose `listPrefixLength` equals its `contentLength` collapses
to the empty-string fingerprint, and two such paragraphs are indistinguishable.**

Two hypotheses, neither measured, and no layer is named: LOK reports the prefix
that way for an outline-numbered heading, or our parse of the focused-paragraph
JSON mis-assigns the field. The cheap next measurement is the native build
(`build-native-26-8`), which has the same LOK and needs no rebuild. Recorded as
`queue-a11y-prefix-swallows-the-paragraph`.

## G0-5, the size baseline: recorded, not judged

Roadmap §3.2 rates size as the *weak* reason for this ordering and M2a is where
size gets judged, against R10's six lines of evidence. Recorded so that M2a
starts from a measurement instead of a memory.

| | product core | gate core | delta |
|---|---:|---:|---:|
| `soffice.wasm` | 127,685,177 | 149,208,138 | +21,522,961 |
| `soffice.data` | 102,765,226 | 108,527,803 | +5,762,577 |
| `soffice.data.js.metadata` | 150,565 | 180,087 | +29,522 |
| **`probe.wasm`** (ours) | **115,297,675** | **135,216,207** | **+19,918,532** |

Core exports are **byte-identical** between the two builds (`e9b54133…`):
adding calc and accessibility moved no ABI surface.

The gate profile carries the fs image **whole** rather than as the three r5
packs. Those packs are a partition of the *product* core's `soffice.data` and
describe a file this core did not produce; re-running the pack builder would
prune `dist/profiles/resources/`, which frozen profiles bind to.

## What this run is, and what it is not

Diagnostic on three counts, each recorded in the run's own report:

* a **core** that is not the product's (`wasm-lite/build-a11y-gate0`);
* a **profile** that is not the product's (`a11y-gate0`, its own identity — the
  builder grew a `--profile` flag rather than letting a second artifact wear
  `e2-editor-v4`);
* a **mirrored page**: the worker URL repointed and `PINNED_WASM_SHA256`
  rewritten, because the shipped page refuses a wasm it does not recognise and
  that guard was doing its job. `dist/` was never written; `e2-editor-v4` is
  byte-identical to its archive after all of it.

## What a PASS does not license (G0-4, decided in advance)

* **Not** the ARIA projection (§3.4). Screen readers cannot read a canvas and
  that path is still zero lines. This gate says the data source exists.
* **Not** a reprieve for `queue-engine-must-report-core-lacks-accessibility`.
  The engine's honesty fix is owed either way and a PASS makes it **more**
  urgent, because `enabled: true` starts being load-bearing.
* **Not** block identity (roadmap §9). Same data source, different question —
  and the heading result above is a concrete reason to keep them apart.

## Reproducing

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 tools/probe_a11y_gate0.py --browser chrome --out <path>
```

Defaults are the gate's: `--profile a11y-gate0`,
`--core-build ../wasm-lite/build-a11y-gate0`.

Raw records: `run3.json`, `run4.json`, `run5.json` in this directory. Runs 1
and 2 are not kept as evidence and are described in the handoff: run 1 read the
**projected** field name (`caretParagraph`) and got `null` from a page whose
snapshot is the **raw** engine state, and run 2 is the one that measured that
distinction instead of guessing at it.
