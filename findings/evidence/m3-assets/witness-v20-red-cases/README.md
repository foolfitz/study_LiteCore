# Assets runner red cases on a v20 report: K1-6's manifest path (2026-10-15)

**What went wrong.** The 0.2.23 count's reader (`read-0.2.23.sh`, step 2) ran `check_m3_assets.py --red-cases` on the counted report `../runs/2026-10-15T064913+0000.json`. The report itself is green: `ASSETS DELIVERED`, chrome / firefox / firefox-nozstd 3/3. The red-case mode died before it printed a count, with `KeyError: 'profiles/e2-editor-v19/sdk-manifest.json'` (`before-2026-10-15T064913+0000.txt`). One mutation in `WIRE_CASES`, K1-6 "a conditional request answered with the body", named the v19 profile's manifest literally. Every other wire mutation finds the served profile through `_wasm_path(m)`. Since the 0.2.20 cutover the host serves `e2-editor-v20`, so that key is absent from the report's `wire.files`. The report does hold `profiles/e2-editor-v20/sdk-manifest.json` with `conditional.status` 304.

**Repair.** A new helper, `_manifest_path(m)`, returns the `sdk-manifest.json` next to `_wasm_path(m)`. K1-6 uses it. The change is in the red-case table only, so no scoring line is touched. Runner `c3e1c42310676f19` → `1e306a3e58ff1cab` (`runner-before.txt`, `runner-after.txt`).

**Witness and readings**

| report | before | after |
|---|---|---|
| `2026-10-15T064913+0000` (0.2.23 counted, v20) | `KeyError`, exit 1, no count | **156 red, exit 0**; K1-6 is among them (line 36). The count equals 0.2.12's 156 (`RESULT-0.2.12.md`) |
| `2026-10-11T180154+0000` (0.2.12 counted, v19) | 137 red + `MISSING package cases: the package record is not clean`, exit 1 | **byte-identical** to before (`cmp`) |

The v19 report's exit 1 is not caused by this change. Since `4421df62` the runner's package pins are 0.2.23's, so that report's package record no longer reads clean and the package cases cannot be mutated. The K1-6 path the helper derives for that report is the literal it replaced, and the identical output shows it.

**§34.4**: repaired because of execution **+1** (witness: the counted report above, whose red-case run raised).
