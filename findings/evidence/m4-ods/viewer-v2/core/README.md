# The ODS viewer v2 core build (2026-10-21/22)

`wasm-lite/build-ods-viewer-v2`, built by the owner with `handoff/ods-viewer-v2/build-core.sh` (SPEC-M4-viewer-v2 §2, §2.7, §5.1).

| file | what |
| --- | --- |
| `timing.txt` | the four `make` runs: 003 race (0 min), the 003 retry (2 min, log lost), the dbu stop (0 min), then exit 0 after 45 min; tree 6.0 GB |
| `k1-configure.json` | K-1 after autogen: DB connectivity on, dbaccess and the three SDBC drivers off, Calc/a11y as gate0, autogen.input = gate0's + 4 lines |
| `build-20261022T002600-dbu-tail200.txt` | run 3's tail: `used LinkTarget Library/libdbulo.a not defined` (reportdesign needs dbaccess's dbu; fixed by the ninth patch) |
| `k2-built.json` | K-2: 80 bridge signatures, equal to the offline set; 783 constructors incl. OFormsCollection, no dbaccess; the five link inputs; sizes beside gate0 |
