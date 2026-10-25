# Diagnostic R2 pre-link mechanical audit

The captured explicit source input list verified 43/43 files with zero size or SHA-256 mismatches. The core input list verified 189/189 files with zero mismatches. All 2,326 frozen profile/archive file rows verified with zero mismatches, and the current profile/archive inventory is exactly 2,326 files: no missing or extra members.

The recorded 12 checks all have exit code 0 and nonempty output files. Per-check output sizes and SHA-256 values are in `audit.json`. This audit inspected the recorded results; it did not rerun tests or build commands.

The R2 frozen worker archive matches the pinned SHA-256, and the Makefile R2 worker base path and pin match that archive. Its preflight, object, worker, and manifest rules reference the same base path. The R2 profile directory, R2 build directory, and R2 link log are absent.

The AST tooling-input collector was available. Running its documented read-only command produced JSON exactly equal to the saved inventory. All 13 listed file records (including Makefile and collector) matched current size and SHA-256; all 19 local import edges target listed existing files. The inventory records four roots, zero literal dynamic import/execution sites, nine `sys.path` mutation sites, and 98 unresolved nonlocal imports. The collector's documented limits remain in the saved data.

See `audit.json` for complete counts, mismatches, inventory membership, checks, exact base path, and AST closure comparison. No build, profile packaging, or browser runtime was run for this audit.
