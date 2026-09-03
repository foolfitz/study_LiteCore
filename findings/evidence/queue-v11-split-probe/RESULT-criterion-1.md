# B-2 criterion 1 — reconciliation: **PASS**, 2026-08-29

Criterion fixed before the probe in
[`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`](../../../handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md),
addendum part 2, B-2:

> `create_pack` splits v11's image into base + packs whose file sets and bytes
> reunite to v11's image exactly, verified from the metadata.

## Result

`e2-editor-v11`'s filesystem image, 108,527,803 bytes over 1,606 entries,
splits with `tools/build_r5_profiles.py`'s **unmodified** `classify()` and
`create_pack()`:

| group | files | bytes | MiB |
|---|---:|---:|---:|
| base | 1,489 | 39,940,977 | 38.1 |
| cjk | 1 | 19,484,784 | 18.6 |
| fallback-fonts | 116 | 49,102,042 | 46.8 |
| **total** | **1,606** | **108,527,803** | **103.5** |

* Reunites to the image **to the byte**, and to `remote_package_size`.
* The three groups are an exact partition of the entry list, no duplicates.
* Reaching the split at all is part of the result: `classify()` raises on
  non-contiguous or duplicated metadata entries, so v11's image is confirmed
  well-formed for slicing.

## The font corpus is unchanged between the two cores

| pack | v11's slice | the product core's | identical |
|---|---|---|---|
| cjk | `b76b0433203017ca…` | `b76b0433203017ca…` | **yes** |
| fallback-fonts | `33856e2a082148dd…` | `33856e2a082148dd…` | **yes** |
| base | `9901e9be29c9ded2…` | `ba15a988a7fec468…` | no — as it must be |

The two font packs are **byte-identical** to the ones `e2-editor-v8` already
serves, one of them lazily. The base differs, which is what a base carrying a
different core's registry and (on v11) the Calc configuration has to do; a base
that matched would mean the wrong image had been read, and the probe asserts
that too.

**What this buys**: criterion 3 (the lazy path) is now a **wiring** question —
does the a11y core's loader fetch a deferred pack the way the product core's
does — and not a **content** question. The bytes on the other end of that fetch
are bytes v8 already ships.

**What it does not buy**: nothing here shows the split profile boots, and the
split profile still gets its **own** pack files under its own manifest (B-2).
Byte-identity is a fact about the corpus, not a licence to reference the shared
files.

## The probe goes red

A green probe that has never failed is a green light with no evidence behind
it. `--profile-dir` exists so this one can be pointed at a doctored copy:

```
# one byte removed from the last metadata entry's extent
AssertionError: group bytes 108527802 != image 108527803
```

Red on the perturbation, green on the real profile, same invocation otherwise.

## Reproducing

```bash
cd wasm_sdk_probe
python3 ../findings/evidence/queue-v11-split-probe/probe_split_reconciliation.py \
    --out <scratch dir>
```

Writes only to the scratch directory. It does **not** mint artifacts into
`dist/` — a probe that moves the candidate while its own soak is running is the
failure this gate exists to prevent.

## Still open

Criteria 2 (the split profile boots and one product-path run reconciles clean),
3 (the lazy path, both directions) and 4 (the recomputed figure). The bound is
2026-08-30.
