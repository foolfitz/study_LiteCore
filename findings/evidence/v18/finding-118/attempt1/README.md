# Finding 118, attempt 1 (2026-10-08 12:19-12:26): NOT MEASURED, kept as run

All four runs (P1 v8 dist page, P2 v18 cutover page, Chrome and Firefox) printed `VERDICT NOT MEASURED`: none saw the growth to 34,528 twips or the shrink to 17,406.

**Cause (read, then measured):** the runner passed the fixture to `build_mirror` as an override. `build_mirror` writes an override only where its walk of `dist/` meets that path, so a file that is not in `dist/` is silently never written. The page's `fetch("./shrink-52.odt")` got serve.py's 404 page, and the engine opened that HTML: 37,325 twips wide, 2,875 tall at open and growing as it laid out, identically on v8 and v18. The repaint failures in these reports are on that HTML document; they are not evidence about finding 118.

**Diagnosis runs** (ad hoc, `diagnosis/`; the runner with a monkeypatched open or fixture, not committed code):
- `control-107.json`: the uncut 107-paragraph fixture, opened the same broken way.
- `control-orig.json`: the original file's bytes instead of the rewritten zip, opened the same way. So the zip rewrite is not the cause.
- `twice-52.json`: two opens; the second (worker generation 3) is as wide as the first. Falsifies "only the first open after boot is laid out differently".
- `control-107-fixed.json`: after the fix (the fixture written into the mirror root, as the merge runner does), the uncut fixture opens at 12,474 × 51,650, which is M2-4's size.

**The chain's `exit=0` lines here are not exit codes.** `echo "$(ts) END ... exit=$?"` expands `$?` after the `$(ts)` substitution, so it always prints 0. These runs exited 3 (NOT MEASURED), as the direct rerun of the control shows. Fixed in `../chain-red.sh` (`local rc=$?` first). The same pattern is in `../../m2-shakedown/chain.sh`, `../../diag-117/chain.sh` and `../../diag-117/chain-rerun.sh`; those records carry dated corrections.
