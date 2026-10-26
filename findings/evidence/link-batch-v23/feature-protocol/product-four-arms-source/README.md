# Four ABI6 product arms: instrument source, unexecuted

Source-only instrument unit for `handoff/WORKORDER-2026-10-26-v23-product-four-arms.md`, prepared against HEAD `9309cdbc`, then revised once for the independent adversarial review ("integrate with named fixes", section "Review fixes" below). No browser, build, host or network ran. No existing file was edited: the one required runner change exists only as `integration-pending.patch` (not applied). Nothing here is a feature measurement, a count or an acceptance claim; every row is NOT_ESTABLISHED until a qualifying runner execution per browser produces raw artifacts.

## What was built

| File | sha256 at hand-off | Role |
| --- | --- | --- |
| `wasm_sdk_probe/web/v23-product-four-arms-observer.js` | `1b2327fd…` | Observation entry. Installs the core, then `await import('./e2-editor-app.js')` (the unchanged app). |
| `wasm_sdk_probe/web/v23-product-four-arms-observer-core.js` | `c0ac2ab5…` | Pure observer: Worker wrapper (raw requests, cancels and responses filtered to recorded requests, events, per generation; paint bitmaps as length + SHA-256), pass-through wrappers on `NarrowEditorV2Session` (`open`, and the page's admissions `action` / `deleteKey` / `commitText` / `save`), window key listeners (trusted keydown / keyup / beforeinput with flags, times, sink state, `defaultPrevented`, admissions made during dispatch), release-set snapshots, control API (chunked reference, chunked export). Dormant until `begin()`. |
| `wasm_sdk_probe/tools/v23_product_four_arms.py` | `5e22feff…` | The four-member executable table (fixtures verified against the 9.3 pins, schedules verified against `v21_input._times`, first-paragraph length checked), the declared observer mirror and its whole-served-graph identity, `run_block` (never raises), `restore_neutral`, `with_restore`. |
| `wasm_sdk_probe/tools/judge_v23_product_four_arms.py` | `67a42660…` | Independent raw-artifact reader: per row and aggregate PASS / FAIL / NOT_ESTABLISHED; never raises. |
| `wasm_sdk_probe/tests/test_v23_product_four_arms.py` | `4c6f0b9d…` | Synthetic-page builder reproducing the observer's record semantics; positive baselines; every causal control; hold contradictions; never-stops-the-runner; aggregate; the Node tests; the JS/Python cross-check; the patch test. |
| `wasm_sdk_probe/tests/v23-product-four-arms-observer.test.mjs` | `6ef5c938…` | Drives the observer core's actual source with a fake Worker, a fake queued session and a phased dispatcher (capture listeners, page handler, bubble listeners). |
| `integration-pending.patch` | `f8c5f78d…` | The only change to `tools/run_e2_c_product_path.py` (runner at HEAD `5ca4451e…`). |
| `reader-mutation-sweep.py` | `149c4c2b…` | Disables one defining reader check at a time in a temporary copy and requires its control to go red. |

## The integration patch

1. Imports `v23_product_four_arms` and `judge_v23_product_four_arms`.
2. Builds the observer mirror as the last mirror, before `servedShell` is computed: only `e2-editor.html`'s single module tag changes (`./e2-editor-app.js` to `./v23-product-four-arms-observer.js`) and the two observer files are added. The app, shell, SDK and frozen worker are symlinked byte-identical. `report["v23ProductFourArmsMirror"]` (`evidenceClass: "instrument-observation"`, not `diagnostic`) binds the original and served HTML hashes, both observer hashes, the product module hash, the candidate page hash when `--candidate-profile` is used, every member of the current shell bundle (`build_e2_c_shell_bundle.MANIFEST`) as served beside its declared hash, and every file the profile manifest names. Any diagnostic stamp already in the report, or `--mutate`, is listed in `diagnosticOverrides`. If the mirror cannot bind it is recorded `installed: false`.
3. Inserts the four-arm block before P-CUT-4 (which stays the last diagnostic and itself precedes the terminal 096 block). The block runs inside `liveness.expecting(...)`: it is skipped as NOT_ESTABLISHED when the mirror is not installed or any diagnostic/mutation override is present (no Worker spawned); any exception of `run_block` or the reader becomes the block's NOT_ESTABLISHED (`SessionDied` is re-raised, unchanged semantics); after a block that ran, the product's own file input reopens `e1-fixtures/list-contexts.odt` and must reach `ready` (two attempts), otherwise every PASS of the block is downgraded to NOT_ESTABLISHED. Then the four literal call sites `check("v23-product-insert-then-shift")`, `check("v23-product-merge-then-shift")`, `check("v23-product-held-shift-one-second")`, `check("v23-product-held-shift-two-seconds")`.

Verified statically: `git apply --check` passes against HEAD; the patched runner compiles and imports; `declared_check_ids` returns the pinned original 42 ids in their original order plus the four new ids, contiguous and immediately before `a-boundary-arrow-press-does-not-cost-the-work`; `MUTATIONS` is unchanged. The old 096 reader, mutation definitions, `check_soak_bank.py` and `tests/test_product_path_mutations.py` are untouched.

Residual: the guard still reads the page once on leaving the region. If even the neutral reopen cannot reach `ready`, the existing guard stops the run there, naming the last four-arm check; a page in that state could not serve 096 either. The guard's semantics were not changed to avoid that.

## What one runner execution per browser will do (unexecuted)

`run_block` writes `<--out without .json>.v23-four-arms/` (a fresh temporary directory when there is no `--out`; an existing or unusable directory is refused, never overwritten or re-read):

1. `begin()`: recording starts; the page fetches and hashes the whole served graph (HTML, both observer files, all shell bundle members, every profile file).
2. Readiness, once per browser path, before any measured cell: a disposable copy of `abcd.fodt` opened through `OPEN_BYTES` under its own name, caret at the actual text start, focused enabled sink, one trusted `Z` through `v21_input.key`, quiet, final state, product Save through `capture_save`; raw bytes kept as `saves/<cell>.odt`.
3. Per arm, three fresh `OPEN_BYTES` opens of the pinned fixture (distinct names), public setup, `arm()`, the measured trusted input (`v21_input.chain` for x / Backspace then Shift+Right; `v21_input.hold(..., flagged=True)` for 1000 ms and 2000 ms Shift+Right), a containment-only quiet wait that reads page JavaScript state and never the engine, final `editorGetStateV2` and `getSelection`, product Save.
4. Before the first hold cell, the same-browser reference: a fresh open of `long200.fodt`, then 52 single public extended Right steps, each followed by `getSelection`, driven from Python in chunks of 8 steps so no awaited execute approaches geckodriver's 30 s script timeout.
5. `end()`, chunked export of the raw record to `page.json` (hash-checked), plus `identity.json`, `table.json`, `rows.json`.

The runner then calls `judge_run` on that directory for its four checks. The aggregate over both browsers is the reader's CLI: `judge_v23_product_four_arms.py CHROME_DIR FIREFOX_DIR`, which also compares the table with the runner's literal sites through the runner's own `declared_check_ids`.

## How the reader decides

Each row has an `establish` phase that can only raise NOT_ESTABLISHED and a `decide` phase that can only raise FAIL, so a FAIL never stands on an unfulfilled prerequisite; any other exception, in a row or around the whole run, is NOT_ESTABLISHED with its text. Witnesses established for every row: run identity (UA family; every browser-fetched shell member equal to the reported bundle generation, the entrypoint alternatively equal to the reported candidate page; the bundle manifest file equal to the one reported; observer bytes equal to this tree's; HTML equal to the one-tag transformation; all profile files bound; ABI 6; no diagnostic override); stream invariants (unique request identities, terminals and cancels after their requests, unique sequence numbers, corrected half-open ownership plus the original time checks); every instrument call on the cell's own Worker generation and document; the fresh open; the setup; readiness preceding the cell; no instrument call inside the measured window; the focused enabled sink at arm and on every measured key; no Worker replacement or error, live session; every measured input trusted; release-set snapshots equal to the reader's own reconstruction; the product Save bound three ways; every admission linked FIFO to its own wire request and every wire request to an admission.

Insert / merge then decide: one admission per trusted key; the first request is `insertText "x"` or `delete-backward`; the Shift+Right request is `move-character-right` with `extendSelection: true` on the wire and on the admission; the first request was posted first; both terminals ok; exact saved paragraphs; exact final selected text; the caret is the right endpoint on the anchor's line.

Holds then decide: every move carries the public extension flag; every admission is attributable to its own trusted press (during its dispatch, or released later from an earlier press the page took without admitting) and no press is admitted twice; every admitted extension was answered ok; every extension terminal keeps the reference's terminal anchor; the final selection (logical prefix from its active text, never getState geometry compared with terminal geometry) is a first-paragraph prefix, not collapsed, anchored at the setup anchor, and equal to the reference text after the ADMITTED count of extensions; document and revision unchanged; for S-12 only, growth after release is nonnegative and at most the release-time wire-pending extension count.

## Release witness

The release event is the first trusted keyup of ArrowRight or Shift after the last measured ArrowRight keydown. The wire-pending set is reconstructed from raw Worker records only: product extension requests posted before the release with no response or cancel before it. Held and queued work is recorded separately (admissions not yet posted, and page-retained candidates) and never enters the bound. The release state is the state of the latest ok extension terminal before the release, attributable by `(generation, requestId)`; no read is issued at release. It must match the reference unambiguously (else NE) and cannot be ahead of the extensions answered by then (a post-release state cannot be backdated: NE); being behind is reported as `releaseOrdinalMismatch`. For S-12 the initial nonrepeat press must have been admitted during its own dispatch and posted before the release, and the setup must be clean (no text, delete or save request before the release, `dirty: false` at arm). The one-second arm records this accounting (or the reason it is not established) without being gated on it.

## Tests

Causal controls (`CausalControls`), each asserting its own reason: removed readiness mutation / unsaved readiness (NE); synthetic input (NE); Shift removed (NE); plain move posted (FAIL); swapped order (FAIL "wire order"); wrong fixture, profile, browser, page, lagging/unstamped shell member, unreported manifest, diagnostic override (NE); corrupt raw save (NE); wrong saved content (FAIL); erased terminal (NE); stolen adjacent same-clock request (NE); page snapshot for engine state (NE); post-release state in the release slot (raw tamper: FAIL becomes NE "ahead of the extensions answered"); held work vs wire-pending (raw: held repeat released after the keyup FAILs S-12 "2 exceeds 1", the same extension posted before the keyup PASSes with a wire set of 2); omitted pending request (NE); repeats removed (NE); bound violated (FAIL); copied round (NE). `HoldContradictions`: final anchor moved (FAIL), overshoot (FAIL), one press admitted twice (FAIL), admission never posted (NE), refused terminal (FAIL), S-12 gates on the two-second arm only, reference call on another generation (NE). `NeverStopsTheRunner`: unreadable XML (NE "ParseError"), any reader exception (NE), `run_block` never raises (browser gone, table drift, unusable or existing directory), neutral restore. Positive baselines: 24 rows, same clock, a settled-state representation differing from the terminal, a candidate entrypoint. Node: dormant wrappers pass arguments, `this` and return values through unchanged; recording wrappers return the original promise; cancels filtered like responses; queued work is unposted, not wire-pending; ordered chunked reference. The patch test pins the original 42 ids and their order.

`reader-mutation-sweep.py` disabled 26 defining reader checks one at a time; all 26 controls went red.

Commands, all passing at hand-off: from `wasm_sdk_probe/`, `python3 -m unittest tests.test_v23_product_four_arms` (48 tests, includes the Node run and the JS/Python cross-check with a queued-work snapshot), `node --test tests/v23-product-four-arms-observer.test.mjs` (11), `node --check` on both observer files; from the repository root, `git apply --check findings/evidence/link-batch-v23/feature-protocol/product-four-arms-source/integration-pending.patch`.

## Unexecuted, and therefore NOT_ESTABLISHED until a browser runs

Everything that depends on the real page: whether the observer installs and stays dormant without perturbing the earlier checks; whether Firefox's WebDriver sandbox can call the control API (the selection collector's identical pattern passed 13/13 on Firefox, the only basis); whether typing `x` over a public selection reaches `insertText` and replaces it; whether Chrome `rawKeyDown` for Backspace yields a trusted `deleteContentBackward`; the actual repeat flags of CDP `autoRepeat` and WebDriver repeated keyDown; whether ABI6 extension terminals carry attributable states; checkpoint saves on the dirty arms; hashing every profile file at `begin()` in time; paint traffic and export size; whether the neutral reopen reaches `ready`; actual timings.

## Ambiguities and how they were resolved

1. Readiness scope: one readiness per runner execution (browser) on a disposable, distinctly named copy of `abcd.fodt`, before every measured cell; every product open spawns a new Worker, so "worker path" was read as this profile's worker route in this browser.
2. Release state: only terminals carry a request identity; `editor-state` events are recorded, not used as the release state.
3. Endpoint (both holds): per 9.3 "each admitted Right extend advances", the final selection must equal the reference text after the admitted count; a mismatch between admitted and ok-answered extensions is reported (and a refused or cancelled extension is FAIL). The S-12 bound and its gates bind the two-second arm only.
4. Reference: one per browser run, 52 steps through the public client action (a reference, not measured input), on its own open, generation and recovery check.
5. Page-held work is module-private; only candidates are observable and they never enter a bound.
6. Admission to request linkage is FIFO per category; saves are not linked because checkpoint saves share the operation.
7. Instrument ownership is the synchronous half-open window of a client/document call.
8. Block position: before P-CUT-4, still before 096.
9. Observer mirror always on (dormant); diagnostic and mutation runs skip the block.
10. Setup uses public client calls outside the measured window, as the selection collector does.
11. "Anchored after x" / "at the former boundary": exact selected text and saved content fix the logical range; the anchor is the endpoint that is not the caret, left of it on the same line.
12. A FAIL row makes its arm FAIL even when other rows are NOT_ESTABLISHED.

## Review fixes, and where the literal wording was not followed

1. Review item 1a offered `liveness.expecting` as an alternative; that region still probes on exit, so it alone does not keep a dead page from stopping the run. Both were used (region plus neutral reopen); the residual is stated above.
2. Review item 3 asked that every trusted measured keydown have exactly one admission. Under the shipped depth-2 holding policy flagged repeats beyond the depth are dropped by design, so that literal rule would fail every correct hold. Implemented instead: at most one admission per press, every admission attributable to its own press (direct, or a released retained repeat), the first press admitted during its dispatch (S-12 gate), exactly one admission per key in the two sequence arms, and every admission linked to its own wire request.
3. Review item 2: the release-state lookup stays in the establish phase only where the work order itself makes an unmatched release endpoint NE; everything geometric about the final state moved to the decide phase.

## Points that look like defects or staleness in the ticket

1. The section "Existing 096 Firefox instrument gap" describes a runner that no longer exists at HEAD: `boundary_rescue` already takes the browser and uses `trusted_key`, the 096 admission accepts WebDriver `command`, `FirefoxSession` is launched with `worker_error_server=True`, and `induce_worker_failure` has the `firefox_worker_error` branch. This unit does not touch that seam.
2. The runner's report still declares `isTrusted: false` and `notD5` for the whole run (already partly stale, since 096 presses a trusted key). Trust for the four new checks has to be read from the four-arm artifacts; the header was not changed.
3. `check_soak_bank.py` pins 39 PASS / 2 NE for the closed v13 bank; a future bank of patched-runner reports needs its own composition.
4. 9.3's "Shared evidence contract" still names `editorGetStateV1`; the reader binds the corrected `editorGetStateV2`.

## Coordinator integration status (2026-10-27)

An independent opus adversarial review of the first version recommended "integrate with named fixes": never cut off 096, reachable hold FAILs, admission counting, the full served graph, cancel filtering, skipping under mutation/diagnostic runs, the one-second gates, chunked Firefox references, and stronger tests. The author applied all nine; the sections above describe the fixed version. In the main tree, `python3 -m unittest tests.test_v23_product_four_arms` gives 48 OK and `node --test tests/v23-product-four-arms-observer.test.mjs` 11 pass. The files are committed as unintegrated source. `integration-pending.patch` still applies (`git apply --check`) but is NOT applied.

Next, after applying it:

1. Run the unpatched and the patched product runner once each per browser, and require the 42 existing checks' outcomes to be identical. This is the measurement for the always-on dormant observer, which the review read as effectively pass-through but which has not been run.
2. Then run the first qualifying four-arm execution.
