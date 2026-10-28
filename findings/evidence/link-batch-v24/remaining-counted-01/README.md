# Fresh R1/S1-S4 after retained complete S5

SPEC section 19; owner authorization 2026-10-29 to run measurements and necessary work while away.
This is a new directory, never a retry into `counted-selection-01`.

- Retain S5 1,176/1,176 PASS from the original stopped cohort, re-read from original raw artifacts.
- Fresh R1 144 cells, then S1-S4 234 cells, both browsers. No S5 execution in this declaration.
- Original config sha256 unchanged: `c1060f390cd768a7c576494ddc4a22b2187d9afa2cf0b6e1e283318487ad17a0`.
- Original 38 instrument bindings unchanged; the 44-file orchestration union is separately
  preserved and live-verified. The inherited `gitHead` is from the source declaration; the new
  orchestration identity is its exact source hashes, and job-status records the actual launch HEAD.
- Original verifier's code object, with KINDS/stage_spec rebound; all named entry-point overrides
  recorded in the declaration. CPU limit, fresh V0 per stage, stop-on-first-nonpass, no retry unchanged.
- Qualification and plan: `../remaining-preparation/`, 6/6 tests PASS, including raw S5 reread.

Unattended execution: `../remaining-preparation/run-and-read.py`. It first runs this cohort,
then reads its raw artifacts together with the original S5. Only complete combined PASS proceeds
to A4: source closure checksum, Chrome, Firefox, source closure checksum, raw aggregate judge.
Any nonpass stops; no count is restarted and no browser is closed to bypass the CPU guard.

Progress: `job-status.json`, `status.json`, `r1.runner.txt`, `selection.runner.txt`.
Final job state `SELECTION_AND_A4_PASS` means those declared stages succeeded; it does not imply
host package, BINDING, K, DDEV operations, or release promotion.
