# D0, round two — artifact `29ec627b`, 2026-08-21

The second round's D0. Round one is beside this, under
`e2-editor-v2-572035ac`; the namespaces are the artifact, so neither round can
overwrite the other.

## Result

| | Chrome | Firefox |
|---|---|---|
| `pass` | **true** | **true** |
| `problems` | `[]` | `[]` |

Judged by `tools/analyze_e2_c_d0.py` against
`e2/validation-matrix-v2.json`, not by reading the raw output.

## The matrix had to be re-frozen first, and the guard is what said so

The matrix was frozen on **2026-08-17** against artifact `d538ce0b` and that
day's shell bundle. Two relinks (`296f3ea7`, then `29ec627b`) and thirteen shell
generations (v12 → v25) later, the baseline no longer described the tree.

`tools/e2_c_matrix_entry.py` **refused to start a browser**:

```
D0 entry assertion refused this round:
  - baseline wasmSha256 does not match the artifact on disk (d538ce0b9147… vs 29ec627bf8a5…)
  - baseline loaderSha256 does not match the artifact on disk (2a1ea5c18c6e… vs 6ff0f962eded…)
  - baseline workerSha256 does not match the artifact on disk (b546231338ab… vs a9afbc0101eb…)
Fix the matrix (or the profile) before running, not afterwards -- the whole
point of a frozen matrix is that it exists first.
```

That refusal is recorded because it is **the guard doing its job**, not an
obstacle that was worked around. External review named the window between a
relink and a freeze, on 2026-08-16, as the one place round one's mistake could
repeat; this is that guard catching exactly that window, four days later.

All five bindings were then **re-stated** — re-freezing is a deliberate edit,
not a refresh — and the before/after pairs are in the matrix's own
`refreezeLog`:

| | frozen 2026-08-17 | re-frozen 2026-08-21 |
|---|---|---|
| `wasmSha256` | `d538ce0b9147…` | `29ec627bf8a5…` |
| `loaderSha256` | `2a1ea5c18c6e…` | `6ff0f962eded…` |
| `workerSha256` | `b546231338ab…` | `a9afbc0101eb…` |
| `manifestSha256` | `a7d2b6ba09a0…` | `ff6834f9301d…` |
| `shellBundleSha256` | `e48685976e86…` | `07143f961d82…` (v25) |

`manifestSha256` moved because the 2026-08-19 relink changed what is *in* the
manifest — which is the reason SPEC E2-C 11.3 bound it as the fifth identity in
the first place.

Two of the five (`shellBundleSha256`, `manifestSha256`) are checked for **shape
and freeze only**, not against a file in `dist/profiles/`
(`e2_c_matrix_entry.py:39-47`). That omission is deliberate and named there; it
means those two were filled by hand here and are only as good as this record.

## What this round did NOT change

No shell or profile file was touched by the 2026-08-21 work — only `tools/` and
`e2/` bookkeeping, plus new tests. So this D0 binds **the same artifact and the
same shell generation** the day's other measurements were made on, and the
matrix now describes the tree that produced them.

## Reproduce

```
python3 tools/run_e2_c_d0.py --browser chrome  --profile e2-editor-v3 \
    --matrix e2/validation-matrix-v2.json --output <dir>
python3 tools/run_e2_c_d0.py --browser firefox --profile e2-editor-v3 \
    --matrix e2/validation-matrix-v2.json --output <dir>
python3 tools/analyze_e2_c_d0.py <dir>/e2-editor-v3-29ec627b/<browser> \
    --matrix e2/validation-matrix-v2.json
```
