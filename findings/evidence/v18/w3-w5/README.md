# v18: W3 (engine side) and W5 (fixed-pitch probe), spec SPEC-M3-paragraph-merge section 28.4

The criteria were written in §28.4 (`37525eec`) before any v18 measurement. The runner and the reader were committed `f8749eed` before this run. The reader's red cases are on committed v17 data (`selftest-output.txt`). W3 on v17 is FAIL. W5 is FAIL with v17 standing in for v18 and PASS with the control standing in. The scan clause also has a positive case: v17's log contains its own e5 path.

Run 2026-10-08 (+08:00). `run.py`: four cold Chrome sessions, one at a time, with fc-request's own `one_session`. Exit 0, stderr empty. Raw output: `sessions.json` and one `*-fc-log.txt` per session. Verdicts: `judge-output.txt`.

- **W3 PASS.** On v18 with the corpus fixture, K1 is answered `Noto Sans Mono CJK KR` (v17: Liberation Mono). 21 conf.d files. The log scans `/instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E10.ttc`.
- **W5 PASS.** Instrument alive on all three sessions (PC-M2a′ without the Courier New clause). PC-M2b holds: v17 answers Liberation Mono, the control Noto Sans Mono CJK KR. On v18, every 細明體/MingLiU request has the control's answer families, there are 8 bands as on the control, and every band top is equal to the control's (difference 0).
- Not a criterion, recorded: v18's 27 bands on the corpus fixture equal the control's from fc-request (difference 0 at every band). The counted comparison is W4.
