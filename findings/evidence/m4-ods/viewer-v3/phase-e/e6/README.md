# v3 E6 boot/reopen measurement, 2026-10-24

Command: `run_ods_viewer_e6_leak.py --profile ods-viewer-v3 --out findings/evidence/m4-ods/viewer-v3/phase-e/e6`, without `--bound`, as SPEC-M4 addendum 12 requires. Report `report-2026-10-23T162930Z.json`, stdout in the parent directory's `e6-run.txt`.

Exit 0: boots and five-cycle reopen shape pass for one-cell-a1, three-sheets-distinct and numeric-100k. The five independent one-cell-a1 boots have identical open.begin sbrk, **B = 0**. Every tested cycle has the required stage/paint shape and stays under the E6 high-water cap.

The reopen series is **recorded, not judged as a leak bound**. The distinct-sheets tail still grows by 12,288 B per reopen here; that is data, not a new pass/fail condition. Finding 164 and L-E6-leak-sbrk remain applicable. A green exit does not withdraw them.
