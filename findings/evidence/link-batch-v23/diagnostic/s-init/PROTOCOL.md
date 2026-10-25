# Bounded S-init public-route comparison instruments

Authority: `handoff/RULING-2026-10-26-v23-s-init-and-040.md` and SPEC-M3 section20. This is instrument preparation, not behavioral acceptance. No browser process was started by this preparation.

`wasm_sdk_probe/tools/v23_s_init_cases.py` is the executable source of the six case IDs, exact trigger strings, fixture membership, profiles, browsers, rounds and render region. The reader derives the Cartesian population from that table: **6 × actual frozen v22/r2 × Chrome/Firefox × 3 = 72 cells**. `paragraph-break` is a separate case. The two linguistic fixture variants belong to the same case and run in separate fresh workers.

Four deterministic ODT files live in `wasm_sdk_probe/test-docs/v23-s-init/`; their committed manifest binds exact bytes. Every document has an en-US paragraph. The empty paragraph supports the three exact insertion triggers and the separate InsertPara marker. The direct-load authority has a language-tagged paragraph. The two narrow linguistic documents contain identical correctly spelled and deliberately misspelled words; their package entries differ only in `fo:hyphenate=true/false`. A focused test proves that difference. The documents use a six-by-eight-inch page and a fixed 600×800 RGBA observation of 8640×11520 twips. These fixtures are public-route probes, not assertions that dictionaries or autocorrection are available.

## Observation and attribution

The separate page `web/v23-s-init.js` uses the existing `NarrowEditorV2Session`, public document operations and public InsertPara. It adds no private diagnostic or arbitrary-key route. Its wrapper records the actual worker requests, terminal responses, callback/events and binary payloads before transfer. Public insertion method comes from the actual `insertText` response, not from a page label or the presumed paste path.

Every page fetches and hashes the actual served manifest, worker, loader, WASM and resource data/metadata named by that profile. The runner independently hashes the corresponding source files, resource files, local module import graph and pinned fixture bytes, before each cell and after the cohort. This records available served resource identity; it **does not** inspect worker FS or prove service registration. Both profiles must use the same core commit and identical resource inputs. The shared SDK/session files and frozen profiles are read only.

For direct-load-reopen, the reader binds the first saved ODT to its actual save response, requires the old owned worker's termination before a different worker is created, and compares the actual second open request bytes byte-for-byte with that saved response. The final save must preserve semantic content and the unique marker. This is the fresh-worker restoration mechanism; the separate timeout/recovery cohort still owns recovery-transition evidence.

For linguistic layout, the reader binds the requested region and decoded RGBA bytes to actual paint requests/responses, and page rectangles to the actual geometry response. It compares exact RGBA bytes via their recomputed hash, not PNG metadata. Enabled/disabled observations remain separately preserved. A differing setting control is reported as an observation, not promoted into a dictionary inventory.

Saved ODT comparison parses XML, resolves named paragraph/text style inheritance, and keeps text/order, inline structure, list depth/numbering definitions and effective properties, including language and hyphenation. ZIP timestamps and incidental style identifiers are not comparisons. Writer's `SvxHyphenZoneItem::CreateDefault` is false (`editeng/source/items/paraitem.cxx`), so omitted false is normalized to that default; this is not evidence that the runtime service is available. Raw saved bytes remain in each cell for review.

## Reader rejection behavior

```bash
python3 -I wasm_sdk_probe/tests/test_v23_s_init_reader.py
node --input-type=module --check < wasm_sdk_probe/web/v23-s-init.js
```

The synthetic clean 72-cell population passes with explicit residual NE. Seventeen altered-cell controls reject: missing cell, duplicate cell, wrong candidate bytes, wrong fixture bytes, coherently changed saved outcome, changed actual insertion method, changed geometry, coherently changed decoded pixels, missing fresh-worker witness, substituted reopen bytes, failed response, a worker URL using the other profile, changed fetched instrument/config bytes, an extra no-op mutation, both profiles silently dropping input, and a non-advancing insertion revision. Separate file controls alter actual mirror source, fixture and config bytes, and reject an explicit WASM pin inconsistent with actual profile bytes. The changed-output controls update their corresponding wire reply too, so they test cross-profile comparison rather than merely inconsistent duplicate fields. These controls are synthetic and do not count as browser runs.

## Execution only after coordinator lock clearance and the actual r2 link

```bash
python3 -I wasm_sdk_probe/tools/run_v23_s_init.py \
  --v22-wasm-sha256 ACTUAL_FROZEN_V22_WASM_SHA256 \
  --candidate-wasm-sha256 ACTUAL_OWNER_LINKED_R2_WASM_SHA256 \
  --output findings/evidence/link-batch-v23/post-link/s-init-01
python3 -I wasm_sdk_probe/tools/judge_v23_s_init.py \
  findings/evidence/link-batch-v23/post-link/s-init-01/report.json \
  --v22-wasm-sha256 ACTUAL_FROZEN_V22_WASM_SHA256 \
  --candidate-wasm-sha256 ACTUAL_OWNER_LINKED_R2_WASM_SHA256
```

The output directory must be new. The runner acquires the existing browser lock and starts only its own temporary HTTP/browser processes; it does not touch host services or live documents. Every cell is a fresh browser process. The 480-second outer observation bound is an instrument stop, not an SDK timeout change; public SDK/session timeouts remain their defaults. Do not count a failed outer-bound observation as successful recovery.

The only possible PASS claim is **bounded S-init product-route comparison PASS**. Service/dictionary availability without a discriminating witness, unexposed effective spelling/autocorrection configuration, naturally unobserved key fallback, and long-lived omitted-disableRecovery effects remain the explicit residuals accepted by the ruling. An observed v22 effect missing in r2 is a comparison failure. No run means NOT_ESTABLISHED; synthetic controls never establish S-init behavior.

## Source-readiness review corrections before any execution

The page independently fetches and hashes its actual served HTML/JS/import graph and the config response bytes. It does not copy an expected instrument hash and call that an observation. The runner and CLI independently re-read the copied entry files, symlinked imports, copied fixtures and config in the actual mirror. The CLI requires external explicit v22 and r2 WASM pins and checks the corresponding actual profile/resource files; report-owned pins alone are insufficient.

The reader derives the exact mutation sequence from the case table for each generation, while allowing the declared session observers and saves/checkpoints. Unknown mutations, extra no-op format actions, mutations during saved-byte restoration and unplanned worker generations are refused. Worker URLs and actual init-response profile/core identities bind the runtime being used, separately from prefetch identities.

The owner proxy accepted a non-vacuity implementation for the existing three input cases: the matched insertion response must advance the actual open revision, and saved semantic content must differ from the pinned empty baseline with substantive non-whitespace text or, for `input-number`, newly established list membership. Revision alone is insufficient. The reader rejects a coherent both-profile silent drop, while a synthetic empty-body numbered-list transformation passes. Literal unchanged trigger strings are not required, preserving the possibility of genuine autocorrection.

Before the counted population, use `--preparation-only` with `--case-id`, `--browser` and `--profile` to select one uncounted round. No cell filter is accepted without that flag. Such reports are explicitly marked uncounted and the final CLI rejects them as acceptance evidence. Preparation outputs and any failures remain separate from the later fresh 72-cell output directory. Browser execution still waits for coordinator lock clearance.

## Preparation 02 correction: effective text opacity

The first actual v22/r2 direct-load-reopen pair both preserved text and structure but caused the reader to distinguish omitted opacity from explicit `loext:opacity="100%"` on the second export. The core-source chain and retained raw files are documented in `post-link/r2-attempt-01/s-init-prep-02/README.md`. The normalizer now seeds the proven effective paragraph text-opacity default,100%, while inherited/explicit nondefault values override it. A regression over the actual saved bytes passed only after this change; a50% mutation remains unequal. This implements semantic-content comparison and adds no browser cells or service coverage. The failed preparation remains uncounted and is not rewritten.

## Preparation 03 disposition: paired public paragraph-action precondition

The owner proxy approved this exact setup after the retained prep03 baseline refusal: for `paragraph-break` only, on both profiles, read the actual initial empty-paragraph state, call the existing public client `placeCaret` once at that state's x and y plus floor(height/2), then read fresh state and require observed/collapsed selection. Only then insert the same fixed marker. Record another fresh state after the marker and require observed/collapsed selection before the unchanged public InsertPara. Use no private route, guessed coordinate, retry, added sleep, or post-marker repositioning. The direct client call deliberately avoids the session wrapper's retry/grace loop. If placement or either witness fails, the preparation remains unestablished/refused; it does not retry until green.

This establishes admissible input for the existing paragraph-action comparison. It does not fix initialization or erase the original cold unprimed asymmetry: prep03 v22 refused while r2 succeeded. The post-marker v22 cached caret had remained at x1004 versus r2 x4457, so using those post-marker points would target different logical positions; the approved setup occurs before insertion instead. The six cases, two profiles, two browsers and N3 population are unchanged, and no counted population has begun. The next bounded preparation should filter to the paragraph-break pair before rerunning all24 uncounted cells.

The reader binds the single placement request/response and its coordinates to the actual initial state, proves it precedes insertion, and binds the fresh placed and post-marker witnesses to wire responses. Its exact mutation projection now contains this one setup operation for this case only. A causal control removes the actual placement exchange while retaining the claimed setup and saved result; the reader rejects it.

The existing two-browser/N3 provenance condition is also implemented directly: actual captured `page.userAgent` must match the outer Chrome/Firefox family, and a canonical hash of the actual page observation cannot be reused across cells. Wrong-family and copied-round controls reject; this uses already captured evidence and adds no case or data collection.
