# Lossless raw-cell storage

Raw cell JSON contains complete wire paint payloads and can exceed100MB per cell. Git stores those exact files as deterministic `.json.gz`; `.gitignore` excludes only the corresponding uncompressed browser-cell filenames and the runtime-only absolute `mirror/profiles` symlink. Reports, source mirrors, command receipts, failures and verdicts are preserved separately. Compression does not remove fields, rewrite reports, rerun a product or change any observation.

`store_payloads.py` is a storage tool, not an acceptance reader. Pack requires explicit completed cohort directories and a fresh index; it checks every cell against its original runner-report SHA256 before compression, verifies decompression and rereads the original. The index records uncompressed and compressed identities. Verify checks report and gzip bytes; restore additionally recreates missing original files and refuses to overwrite an existing differing file. Six tiny storage controls in `storage-controls.json` include raw/gzip mutation rejection, exact restore and empty-inventory rejection. They make no product or pre-red claim.

From this directory, use the recorded index named in the final status:

```bash
python3 -I store_payloads.py verify --index storage-index.json
python3 -I store_payloads.py restore --index storage-index.json
```

The original bytes/hashes and original reader paths are then available. Replaying a product judgment additionally requires that cohort's exact tool/source graph, frozen profile/resources and native input fixture from this repository; the report records those pins. A later edited reader cannot silently replace the recorded graph. Each tracked mirror already retains the served JavaScript/config/fixture bytes; its excluded `profiles` symlink is a runtime convenience, never standalone artifact evidence. Original profile/resource hashes remain in each report and refer to the separately frozen SDK profiles. Stopped preparations/cohorts remain stopped; byte restoration does not grant them missing readiness, postConfig, browser cells or aggregate acceptance.
