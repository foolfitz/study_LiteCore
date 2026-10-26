# Lossless raw-cell storage

Raw cell JSON contains complete wire paint payloads and can exceed100MB per cell. Git stores those exact files as deterministic `.json.gz`; `.gitignore` excludes only the corresponding uncompressed browser-cell filenames and the runtime-only absolute `mirror/profiles` symlink. Reports, source mirrors, command receipts, failures and verdicts are preserved separately. Compression does not remove fields, rewrite reports, rerun a product or change any observation.

`store_payloads.py` is a storage tool, not an acceptance reader. Pack requires explicit completed cohort directories and a fresh index; it checks every cell against its original runner-report SHA256 before compression, verifies decompression and rereads the original. The index records uncompressed and compressed identities. Verify checks report and gzip bytes; restore additionally recreates missing original files and refuses to overwrite an existing differing file. Six tiny storage controls in `storage-controls.json` include raw/gzip mutation rejection, exact restore and empty-inventory rejection. They make no product or pre-red claim.

From this directory, use the recorded index named in the final status:

```bash
python3 -I store_payloads.py verify --index storage-index.json
python3 -I store_payloads.py restore --index storage-index.json
```

The original bytes/hashes and original reader paths are then available. Replaying a product judgment additionally requires that cohort's exact tool/source graph, frozen profile/resources and native input fixture from this repository; the report records those pins. A later edited reader cannot silently replace the recorded graph. Each tracked mirror already retains the served JavaScript/config/fixture bytes; its excluded `profiles` symlink is a runtime convenience, never standalone artifact evidence. Original profile/resource hashes remain in each report and refer to the separately frozen SDK profiles. Stopped preparations/cohorts remain stopped; byte restoration does not grant them missing readiness, postConfig, browser cells or aggregate acceptance.

Historical source copies are exact evidence, including original whitespace. The six frozen `mirror/input/clipboard-adapter.js` copies and recorded Python blob `b76d54f9…` end with a preexisting blank line. Their literal bytes are preserved; the archive commit's whitespace check therefore separately excludes only `**/mirror/**` and `tool-source-blobs/**`. Current implementation/source checks retain their normal rules.

The second storage batch adds preparation04 and counted04, including two more exact mirrors with the same historical whitespace. The final inventory uses **both** `storage-index-01.json` and `storage-index-02.json`; verify or restore each with the commands above, substituting its actual index name. Both preserve their original reports and paths. Neither inventory supplies the future corrected-graph32-cell population.

## Added cohort: counted-05

`storage-index-03.json` adds the corrected complete historical cohort only: one report and 32 full raw pages, 2,682,882,779 raw bytes and 38,684,767 gzip bytes. Existing indices01/02 and their stopped/preparation evidence remain unchanged. The runner and independent aggregate reader both exited0 with all32 EXPECTED_RED observations; storage itself supplies no product verdict. See counted-05's retained reader, correction and post-run scope records.

Use the existing tool with `verify --index storage-index-03.json` or `restore --index storage-index-03.json` for this cohort. Raw originals remain present/ignored and deterministic gzip files are tracked. `tool-source-bindings-03.json` binds its 17 recorded Python sources to preserved exact blobs. Source mirror and source-blob whitespace is preserved byte-for-byte; only those archival paths were excluded from this evidence commit's whitespace check, with ordinary source checks unchanged.
