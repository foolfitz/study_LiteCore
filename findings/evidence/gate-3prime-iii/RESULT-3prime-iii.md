# B-2 criterion 3′-iii — the functional consequence, measured 2026-08-29

The criterion, fixed 2026-08-29 before this run
(`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, addendum part 3 §C-2):

> One recorded measurement of the functional consequence: a fixture requiring a
> font present only in the fallback pack (family chosen from the pack's own
> metadata), opened on v8, split v11 and unsplit v11, with what each renders
> recorded.

**It does not gate the probe. It gates the owner's confirmation.**

## The fixture

`fallback-script.odt`, built by `create_fallback_script_fixture.py`. Four
paragraphs at 20pt:

| # | text | family | asks |
|---|---|---|---|
| 1 | `TP3-LATIN control ABCdef 123` | default | the **control** — identical everywhere or the comparison measures the harness |
| 2 | `TP3-ARABIC السلام عليكم` | **`Amiri`** | a **named** font that exists only in the fallback slice |
| 3 | `TP3-ARABIC السلام عليكم` | default | the engine's own **script fallback** |
| 4 | `TP3-HEBREW שלום עולם` | default | a **second script**, so a result cannot be an Arabic-shaping peculiarity |

`Amiri` was chosen from the fallback pack's own metadata, per the criterion. The
base and cjk slices contain only `Liberation*` and `NotoSansCJK`.

## The result

| profile | canvas PNG sha256 | ink pixels |
|---|---|---|
| `e2-editor-v8` (ships today) | `5d78ff2e559d826e…` | 57,233 |
| `e2-editor-v12` (split candidate) | **`5d78ff2e559d826e…`** | **57,233** |
| `e2-editor-v11` (unsplit) | `f16d4770de2af000…` | 56,589 |

**The split candidate and the shipping product render this document to
byte-identical pixels.** The unsplit profile does not.

What the pixels show:

| line | v8 and v12 | v11 |
|---|---|---|
| Latin control | correct | correct |
| Arabic, named `Amiri` | **tofu boxes** □□□□□ | correct, shaped |
| Arabic, default family | **tofu boxes** | correct, shaped |
| Hebrew | **correct** | correct |

### The loss is narrower than "complex scripts"

**Hebrew renders on all three profiles.** Only Arabic degrades, and it degrades
on the profile that ships today exactly as it does on the split candidate. So
the honest statement is not "the split loses complex-script support"; it is:

> **Arabic renders as missing-glyph boxes on the product as it ships today, and
> the split candidate does not change that. The unsplit profile would fix it,
> for +46.8 MiB at startup.**

Both Arabic lines are tofu, the named one and the default one alike — so this is
not a font-name resolution failure with a working fallback behind it. There is
nothing to fall back to.

## What this establishes for the decision

* **The split introduces no regression.** v12 is byte-identical to v8 on this
  document, which is the strongest form the parity claim can take.
* **Unsplit v11 carries a real, visible capability that v8's users have never
  had** — Arabic. Nobody had counted it, in either direction.
* **The question is therefore a product-scope one and belongs to the owner**:
  is Arabic inside this product's scope for the institutional buyer? If yes,
  +46.8 MiB buys something. If no, or if unanswered, the default stands — split,
  fallback off, matching what ships today.
* Turning it on later is one manifest field (`loadAtStartup: true` on the
  fallback pack) plus its own gate, and the pack is already a banked,
  byte-identical artifact.

## Limits, named

* One document, one engine, one browser, one zoom level. Not a survey of scripts.
* Whether an Arabic-using institution would accept boxes is not a rendering
  question and is not measured here.
* The ink-band statistic collapsed to a single band on all three profiles (the
  page border inks every row), so it discriminated nothing. **The PNG comparison
  is what carries this result**; the band numbers are recorded and unused.

## Reproducing

```bash
cd wasm_sdk_probe
python3 ../findings/evidence/gate-3prime-iii/create_fallback_script_fixture.py \
    dist/e1-fixtures/fallback-script.odt
for p in e2-editor-v8 e2-editor-v11 e2-editor-v12; do
  python3 ../findings/evidence/gate-3prime-iii/probe_fallback_script_rendering.py \
      --profile $p --out-dir ../findings/evidence/gate-3prime-iii
done
```

The probe waits for the state's `doc` to become the fixture's name, not for
`state == "ready"` — the page is already ready, still showing the previous
document, and that confusion once produced a false cross-version
incompatibility finding.
