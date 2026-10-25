# Disposition of diagnostic build-support review

Scope: the review saved as `REVIEW.json`, actual source reads, and focused packaging/worker tests. This is unlinked build preparation. The formal 45-process RESET result is FAIL, preserved separately; the next owner compilation is the native restore-v2 harness. No WASM link readiness, real engine guard success, LOK behavior or browser recovery is claimed here.

## 1. Manifest failure cleanup — accepted and fixed

The review correctly identified that cleanup covered only a returned contract-problem list. Exceptions after v5 wrote the manifest, and v5 nonzero/exception failures after a partial write, could leave a target that make might later accept.

The wrapper now reads the frozen reference before v5 packing, inside a single validation cleanup boundary. A success flag is set only after candidate JSON, semantic contract, actual artifact bindings and captured summary have validated and the final summary has printed. Every unsuccessful exit from that boundary removes the candidate manifest, including a nonzero return, SystemExit, parse/IO exception and interruption. Partial non-manifest artifacts remain available for diagnosis. A pre-existing manifest is also removed if reference preflight fails. No frozen reference is modified.

The tests execute the real wrapper with only the underlying packer or a specific fault site injected, using temporary files under the project's build directory. Cases include malformed candidate JSON, reference preflight missing/invalid JSON, post-write reference mismatch, post-write validator exception, malformed summary, v5 nonzero return, RuntimeError and SystemExit. The stale-target and captured-output checks failed before the fix (`packaging-faults-red.txt`); all 14 test groups passed after it (`packaging-faults-green.txt`). Later artifact-binding controls extend the same suite to 17 groups.

## 2. Captured v5 diagnostics — accepted and fixed

On every unsuccessful exit from that boundary, the complete captured stdout is written to stderr, including v5 failure and post-pack validation/summary failure. The tests compare the exact emitted text, including multiline diagnostics, rather than merely checking a nonempty message. The original exception or return code remains the result. No successful summary is fabricated on failure.

## 3. Timeout/cancellation — wording accepted; pending claim partly rejected

Source: `DocumentEngine._request`, `_nextId`, `restart` and `dispose` in `sdk/document-sdk.js`; `accept`, `fail`, `handleCancel` and the `error` case in `sdk/sdk-worker.js`; session restart/disposal in `editor-shell/editor-session.js`.

The SDK page-side timeout removes its pending entry, posts a best-effort cancel and rejects with TIMEOUT, subject to its existing late-deadline extension policy. It does not terminate a worker by itself. Kind 3's synchronous JS-thread LOK call can block receipt of cancellation. Kind 1's never-returning engine command can leave worker pending state; `handleCancel` only publishes a cancel result and does not directly remove that state. The runbook and tail comments now require the existing recovery/disposal route to terminate a hung worker before reuse, with no new timeout or recovery mechanism.

The review's statement that kind 2 necessarily leaves worker pending state is incorrect for the intended typed engine error: the base worker's `error` case calls `fail()`, which deletes pending and open state. The real-SDK test now observes both main-side and worker-side pending maps empty after that response. This is synthetic event integration, not proof that the not-yet-wired engine emits the event.

## 4. Actual dependency checks

- **Profile name:** v5 requires an explicit profile and rejects only v4's frozen name. It forwards `e2-editor-v23-diag` to v4, which stamps the supplied profile; there is no whitelist rejecting this name.
- **Contract hashes: an additional real blocker found and fixed.** `build_e2_b_profile.py` puts `loaderSha256`, `wasmSha256`, and `workerSha256` inside `editorContract`; the actual v22 manifest contains all three. The earlier whole-dictionary equality would reject a correctly linked candidate. Semantic equality now excludes exactly these three binding fields, while a separate read verifies every one against its actual packaged file. Missing/stale fields and changed artifact bytes all fail. An unreadable packaged file also invalidates the manifest and preserves diagnostics. `artifact-bindings-red.txt` rejects a semantic-equivalent candidate with fresh hashes under the old comparator; `artifact-bindings-green.txt` records 17 passing groups after correction. The old preparation README's “complete contract” equality claim is superseded by this distinction.
- **Request ids:** the SDK initializes at 1 and wraps after 0xffffffff, so its ids are uint32, not signed int32. The private C signature takes `int`; the tail intentionally rejects values above 0x7fffffff. The runbook documents this diagnostic-only bound and fresh-engine use. The new test also sends an actual SDK-generated id through `_request`, rather than only fabricated worker messages.
- **WASM markers:** `read_wasm` checks the WASM header and accessibility marker bytes only. It does not parse the export section or prove the diagnostic entrance exists. The builder's export-list check is link-input evidence; `-sEXPORTED_FUNCTIONS` consumes that list. Actual linked/runtime entrance verification remains part of the post-link diagnostic execution; no export-existence claim is inferred from marker success.
- **Makefile dependency:** the coordinator added the imported `check_v23_diagnostic_build.py` as a diagnostic manifest prerequisite. The frozen v22 manifest is deliberately not a normal make target dependency, which would traverse its historical relink rule.

## 5. Missing-proof error projection — integration gap fixed in the derived worker

Actual source showed the frozen base worker drops an engine's top-level `failureShape` while projecting other error fields. Merely observing it in a raw debug event would not satisfy a typed SDK error reading. The diagnostic-only tail now wraps `handleCEvent` and `postResponse`: for the exact diagnostic profile and ABI 5, a string failureShape is added to the matching synchronous error response. The base error handler still constructs every existing field and performs pending cleanup. A finally block restores projection context; other profiles, ABI values, malformed events, non-string shapes and unrelated later responses do not inherit it. No frozen worker, public capability, action or SDK method changed.

`v23_diagnostic_error_test.cjs` executes the actual `document-sdk.js` module and base-plus-tail worker with only the WASM call/event injected. An actual `DocumentEngine._request('v23Diagnostic', {kind: 2})` rejects with `MUTATION_OUTCOME_UNKNOWN`, `details.failureShape == 'proof-absent-at-poll:UNO_COMMAND_RESULT'`, the original revision/document/dispatched fields, and empty pending maps. Before the projection the test fails on the missing shape (`error-projection-red.txt`); after it the test passes (`error-projection-green.txt`). This uses the existing 30-second default but does not wait for or claim to test a real hang/recovery.

No counting/K checker, native acceptance population, frozen profile, service or core build was changed. Real engine replacement guards and all post-link diagnostic gates remain pending.
