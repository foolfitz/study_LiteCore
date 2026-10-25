# Diagnostic packaging preparation

These are source/VM/dry-run witnesses, not a successful link or WASM integration result. No compiling make, native harness compilation, service action or frozen-profile write was performed.

- `makefile.txt`: existing diagnostic build reader accepts the new rule.
- `build-reader-controls.txt`: all 23 existing reader controls pass, including deliberate red inputs.
- `packaging-controls.txt`: seven test groups use the actual v22 manifest as the reference population; they reject every removed action (all 23), an added action, ABI 6, a public diagnostic capability, wrong reference identity and v22 masquerading as the diagnostic.
- `worker-controls.txt`: Node VM executes the actual frozen base worker plus the new tail. Profile/ABI/argument guards, all three dispatch mappings, pending requests, submit errors and ordinary-operation delegation pass. Acceptance produces no fabricated completion.
- `worker-profile-guard-red.txt`: executable mutation removes the exact-profile guard from the tail in memory, with no disk edit. The same test exits 1 with AssertionError at the expected refusal on v22. This is a source-level positive control; no LOK call was made.
- `dry-run.txt`: `make -n -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v23-diag/sdk-manifest.json`, run from `wasm_sdk_probe`. Four diagnostic object compiles and one diagnostic link are planned. No old profile link is planned.
- `dry-run-reader.txt`: the existing reader accepts those planned commands. The owner must still run the actual link and its actual log and WASM must be checked.

The private worker operation is `v23Diagnostic`, callable through the existing SDK engine object's `_request`, with its existing timeout and cancellation behavior. It is not added to the public SDK method or capability/action tables. The exact engine export is `int oxsdk_v23_diagnostic(int kind, int requestId)`, diagnostic define only: 1 queued never-return, 2 queued missing proof, 3 direct JS-thread LOK selection call (requires an open document). Browser verification must exercise the actual session recovery route for the never-return case; the VM test does not establish recovery.

The owner command and remaining artifact checks are in `handoff/RUNBOOK-v23-diagnostic-link.md`. Engine source completion, native RESET-HOLDS and integration red controls remain coordinating-agent responsibilities. The recorded dry-run must be refreshed after final engine prerequisites are added; it is not an immutable claim about future source.
