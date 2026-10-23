# ods-viewer-v3, first link, 2026-10-24

The owner ran `handoff/ods-viewer-v3/link.sh`; make and tee exited 0 (`link.log`).

Identity: wasm **ebb7e0cb…**, loader **a6f77b08…**, worker **9c85043a…**. `identity.json` records every local file's exact SHA256 and size. The manifest declares `part-info` and `form-controls`, capability bits **63539**, base data **21bec646…**, metadata **43da6a24…**.

Actual viewer gzip (level 9, mtime 0): **49,530,696 B**, **2,898,104 B** under 52,428,800 B, 1,491 B below the projection. F3-2 is not triggered.

All **1,643** old files in the pre-link frozen snapshot still hash identically (`frozen-set-check.txt`). The wasm contains the viewer fields and SelectAll retry message, Calc/forms/RowSet markers, and no editor completion marker. Stack literal PASS (`stack.txt`); E1-C intact (`e1-c-intact.json`). These are artifact checks, not proof that controls paint correctly.

Archived immediately as `wasm_sdk_probe/build/archive/ods-viewer-v3-ebb7e0cb-worker-9c85043a/`, with the six profile-local files, exports, base report, SHA256SUMS and ATTRIBUTION.md; copies verified against dist and the checksum file checked (`archive-check.txt`). Shared packs retain v1's bytes and are also in the pre-link backup.

Next: pinned Phase E on this exact identity, starting with ladder, the five form-control files, tdf138507, the 157/159 controls. Every runner gets `--profile ods-viewer-v3` and an explicit new `--out`. V2-158B or V3-NR failure stops v3 shipment and records the next blocker. No ddev use; host remains 0.2.32.

Section 34.4: +0 / +0, cumulative 46 / 27.
