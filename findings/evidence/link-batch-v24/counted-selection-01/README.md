# Counted selection 01: complete S5 PASS, stopped before R1 observations

Owner-run 2026-10-28 17:33:58 to 2026-10-29 01:24:20 +0800. Frozen declaration and status are
preserved. No retry or manual status edit. The completion reader was run by the agent after the
owner reported completion; exit 1 correctly means the whole three-population cohort is incomplete.

- S5: **1,176/1,176 PASS**, both browsers, complete. Runner exit 0, 28,039.1 s (7 h 47 m 19.1 s);
  judge exit 0, 53.5 s. Raw reread inspections and aggregate equal the recorded results.
- R1: **0/144**, NE. Its pre-run CPU sample found an external Zen process at **105.8% of one core**,
  above the unchanged 50% limit. It refused before opening a browser, with zero raw cells.
- Selection (S1-S4): **0/234**, never launched after the first nonpass.
- Both stage V0'' preflights held. Whole cohort: `STOPPED_FIRST_NONPASS`, completion verdict NE.

S5 includes 840 overlapping cells, 0 native fallbacks, and all 49 empty-mark routes in each
browser. The inherited named limitation remains: S5 does not guard the delete unit after a no-op
extension. T1/T2 hold in every S5 cell under the frozen reader; no preparation credit is used.

Before any follow-on count, SPEC §19 preserves this complete S5 population and declares a fresh
R1/selection-only cohort. The owner subsequently authorized agent execution while away.
This directory remains stopped. No source/verdict changes are authorized by storage compression.

Storage: raw S5 cells will be gzip-compressed individually, verified by decompression and the
original report's sha256 receipts before removing the uncompressed copy. A storage index records
both raw and stored hashes. The frozen reader already supports `.json.gz` when `.json` is absent.

Storage completed: all 1,176 cells, 1,444,050,931 raw bytes to 337,980,741 gzip bytes. The subsequent
remaining-cohort qualification re-read all original cells successfully from gzip and reproduced
the existing completion report exactly. This is storage verification, not another execution.
