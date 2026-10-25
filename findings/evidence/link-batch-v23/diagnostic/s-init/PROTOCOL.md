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
