# A4-v24 complete: four product arms, both browsers, 24/24 PASS

Ran 2026-10-29 after the combined S5/R1/S1-S4 raw reader returned V24_SELECTION_COUNTS_HOLD.
Chrome wrapper: 551.5 s; Firefox wrapper: 565.2 s, including each wrapper's V0 preflight.
The detached chain finished 06:06:18 +0800. Every job step exited 0.

`aggregate-judge.json`: all four arms PASS, 24 distinct rows (four arms x three fresh cells x
two actual browser families), no aggregate problems. Readiness and independent references are
read from the raw observer records and saved ODTs, not the runner's literal check verdicts.

Both wrapper identities explicitly record default generation 76 overridden to frozen 77 before
runner import. Profile e2-editor-v24, ABI 6, exact artifacts, product page and manifest file hash
are required by the v24 reader. The 31-file tool closure's before/after checksum outputs are
identical and all green (`../remaining-counted-01/job-a4-pins-*.txt`).

The unchanged full product-path runner also reports declared/inherited non-A4 failures/NE; its
exit is recorded separately from the v24 wrapper's four-arm verdict. In particular the frozen
Chrome Enter oracle's raw-substring limitation is I-enter-raw-substring, already independently
read by the span-aware replay. These runs do not withdraw that limit or claim all 46 checks PASS.

Post-job validation re-runs the raw four-arm judge to a new file, compares its full result with
the recorded aggregate, and verifies the job's script/log hashes. No browser is restarted.
Host package, BINDING, K and release promotion are separate pending work.

Post-job result: raw reread exit 0, byte-identical to the first aggregate (1.096 s). The full
outcome census against T4 run-02 changes only the four A4 checks in each browser (NE -> PASS,
now stamped 77) and Chrome `editing-a-long-document-stays-responsive` (FAIL -> PASS, the already
recorded intermittent ink-trigger race). All other outcomes match the prior run, including the
bullet-disposition and inline-selection-format FAILs. No new non-A4 regression is claimed here.
