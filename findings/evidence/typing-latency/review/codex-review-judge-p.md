# codex review of judge_p.py (2026-10-10; `codex exec -s read-only`, codex-cli 0.162.0; prompt `review-prompt-judge-p.md`). Final answer, verbatim.

**BLOCKING**

- **P1 adds an unspecified flag restriction.** A correct P run with explicit `--dpr 1` satisfies §16.2 but gets REFUSED: the wrapper records `dprRequested=1.0`, while the reader requires `None`. Evidence: `SPEC-M3-production-ui.md:735`; `blit_bytes_probe.py:54,266`; `judge_p.py:43,92`.

- **“First ImageData use” is broader than “new band’s first blit.”** An accidental restore that copies cached pixels into a new `ImageData`, then restores the whole band, is excluded as fresh. Executing the actual shims without a browser produced zero measured stale bytes for ten such restores, although each restored 2,966,700 bytes—5.71% of the Chrome canvas. This is an honest product regression yielding false PASS, without changing the runner or reports. Evidence: `blit_bytes_probe.py:90,97,111`; `judge_p.py:115`; cache/restore paths at `e2-editor-app.js:951,1087`.

- **123-B can accept partial first blits as whole-band coverage.** If a P edit accidentally applies the dirty-rectangle helper to `paintBand`, the probe still logs `image.height`, ignoring the dirty rectangle and destination context. The actual shims recorded 36 bands covering all 36,847 rows when each native call copied only 3×18 pixels. With final-revision replies, both all-current and bottom-band checks pass despite incomplete repainting. Offscreen first blits have the same attribution problem. Evidence: `probe_typing_latency.py:71,76,189`; `judge_p.py:144,149`; `e2-editor-app.js:1122`.

**NON-BLOCKING**

- **Cell coverage and thresholds:** no defect found. P1 uses each counter delta and rejects `> 0.02`, correctly allowing equality. All three specified 123-B cells are present; elapsed time is correctly recorded without a threshold. The permitted shipped-page invocation returned exit 1 with eight failing cells. Evidence: `judge_p.py:110,128,140,144,149`.

- **Windowing:** no defect found in the stated keydown-to-next-keydown/final arithmetic. `final` is a periodic snapshot, not an instantaneous READ snapshot; the probe’s post-typing waits normally let it catch up. A genuinely new background band after the last key is correctly excluded from P1. Evidence: `judge_p.py:111`; `blit_bytes_probe.py:94,136`; `probe_typing_latency.py:152`.

- **Current P freshness path:** no defect found. `paintBand` first uploads the complete image; `paint` subsequently reuses that object with seven arguments, so both trackers agree. Using `drawImage` for restores would evade the prescribed implementation, but P1 explicitly measures `putImageData` bytes; adding a drawImage-cost gate would exceed this reader’s specification. Evidence: `e2-editor-app.js:1087,1122`; `probe_typing_latency.py:75`; `SPEC-M3-production-ui.md:725,735`.

- **Other suggested edges:** no defect found on the reviewed runs. Startup/open toasts establish recorder activity; float values `1.0`/`2.0` compare correctly. The 600-entry tail retains the observed final passes. Blits lack layout epochs, so old geometry is a limitation, but no separate verdict-changing witness was found. Evidence: `blit_bytes_probe.py:140`; `p-release/README.md:20`; `judge_p.py:96,150`; `probe_typing_latency.py:78,185`.

- **Red cases:** K1/K2/K5/K6/K7 exercise bytes, toast, all-current, bottom-band, and P1 key-count cells. **123-B’s key-count cell has no red case.** This is incomplete coverage, not independently blocking: §16.3’s required mutations are present, and §34 does not demand every branch be tested against impossible reports. Evidence: `judge-p-red-cases.txt:22,43,107,128,149`; `judge_p_red_cases.py:108`; `judge_p.py:134`; `SPEC-M3-paragraph-merge.md:1202`.

- **§16.8:** no defect found. The preauthorized window adjustment targets the same measured canvas and reproduces Firefox’s failure at 797×1000 before implementation; browser-specific binding is sound. “因執行而修 1” accurately counts an execution-driven binding correction, not a discovered reader logic bug. Evidence: `SPEC-M3-production-ui.md:745,799,803`; `p-release/README.md:24,30`; `judge_p.py:45`.

The shim counterexamples are constructed product regressions, not committed browser-run witnesses; §34.4’s witness requirement still applies before changing machinery (`SPEC-M3-paragraph-merge.md:1218`). I made no repository writes and ran no browser or red-case generator.