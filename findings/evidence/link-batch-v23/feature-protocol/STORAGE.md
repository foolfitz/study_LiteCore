# Lossless counted-feature cell storage

`store_raw_cells.py` reuses the unchanged tested implementation `../feature-pre-red/store_payloads.py`, with only its evidence-directory root set to this directory. Wrapper SHA-256 `5371e3baa8d116eb8f43bf56399ca2d52d16525c8d1c8dce2f73918b99af5e94`; implementation SHA-256 `4510f520bd3c791e6a099d6929ff3b8e8ddab88e623835f5442c81efd143a7ba`. The original six storage controls and scope are documented in `../feature-pre-red/STORAGE.md`. No acceptance predicate or frozen instrument changed.

Two verified indices retain original reports and raw-cell receipt identities:

- `r1-counted-01/storage-index.json`: one report, 144 cells, 542,826,351 uncompressed bytes, 44,180,198 gzip bytes.
- `s5-counted-02/storage-index.json`: the stopped S5 report plus diagnostic prep-07 report, 406 cells total (402 + 4), 512,407,438 uncompressed bytes, 119,886,720 gzip bytes.

Pack checks every raw file against its original report SHA before compression, then checks decompression and rereads the original. Verify was separately run for each index and exits 0; command output is preserved beside each index. Raw JSON copies remain present locally and ignored by Git. Reports, exact mirrors, commands, failures, verdicts and deterministic `.json.gz` files are tracked; the runtime `mirror/profiles` symlink is ignored. Restoring bytes gives no missing postConfig, browser observation or qualifying credit to a stopped/diagnostic run.

From the repository root, verify or restore either index as needed:

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/store_raw_cells.py verify --index r1-counted-01/storage-index.json
python3 -I findings/evidence/link-batch-v23/feature-protocol/store_raw_cells.py restore --index r1-counted-01/storage-index.json
python3 -I findings/evidence/link-batch-v23/feature-protocol/store_raw_cells.py verify --index s5-counted-02/storage-index.json
python3 -I findings/evidence/link-batch-v23/feature-protocol/store_raw_cells.py restore --index s5-counted-02/storage-index.json
```

The original independent aggregate judge needs raw JSON at its report-listed paths. Exact Python tools, served/profile/resource/native inputs are also required; `counted-r1-s5-01/` retains the frozen declaration, config and source archive. Historical mirror/source whitespace is preserved verbatim. Do not fix whitespace or rewrite report/inspection bytes inside archived evidence.
