# Handoff, 2026-10-07 — v15 is linked and archived; the WASM shakedown is next

Picks up from `HANDOFF-2026-10-06h-e-shape-wired-waiting-for-the-v15-link.md` (read its "What happened" table for the E shape, R0b/R0c, the review). Entry points: this file; `handoff/RUNBOOK-relink-v15.md` (§4 and the "Link record"); `specs/SPEC-M3-paragraph-merge.md` **§14–19**; `findings/evidence/merge-native/README.md` (R0b, R0c); `findings/evidence/cjk-subset/README.md`; `research/RESEARCH-2026-10-06-wasm-size-status.md`. Session ended by choice (context size), not by a blocker.

## Since 06h

| Commit | What |
|---|---|
| `7142cbbd` … `a7535fb2` | Owner chose option D for size (keep bundled fonts, subset CJK), fontTools as a build dependency (`python3-fonttools` 4.61.1, apt). `tools/build_cjk_subset.py`: tiers C/E/F, coverage + outline/metric identity + corpus checks, red cases 3/3. Two predictions wrong and recorded (all-features policy doubled the glyphs → policy = fontTools defaults minus `locl`, because LibreOffice shapes with HarfBuzz defaults only, `CommonSalLayout.cxx:446–462`; combining marks missing from the base set). |
| `81ca5dad` | Owner chose **tier E** (5.60 MB zstd vs 12.17): `tools/build_cjk_subset_pack.py` → `dist/profiles/resources/cjk-sub-e.2d8240354ce1cf78.data` (deterministic build), `sdk/v15-writer-review-manifest.json` (r6 with only the CJK entry replaced); the v15 profile rule runs `--check` first. Spec §19. |
| `4928aced` | **v15 linked by the owner** (10:24): wasm `ad3f68bb…` (v8 + 9,766 B), loader `46b2f40a…`, worker `00882139…`, manifest `2a98050c…`, packs `cjk-sub-e` + `fallback-fonts-r5`. v8's four files unchanged. Archived: `wasm_sdk_probe/build/archive/e2-editor-v15-ad3f68bb-worker-00882139/` (6/6 verified). |
| `43d5370d` | Text-frame fixture (`test-docs/merge/text-frame.{fodt,cases.tsv}`, `odt/text-frame.odt`) and `PREDICTION-R0c-frame.md` — **not run yet**. |

## Running when this session ended

A sonnet subagent was running the **product-path net, v15 candidate vs v8** (runbook §4 step 2): `tools/run_e2_c_product_path.py`, Chrome and Firefox, 3 rounds each, `--candidate-profile e2-editor-v15` for v15. Output: `findings/evidence/v15-shakedown/product-path/<profile>-<browser>-r<N>.json` and a `README.md` with a per-check table — **not committed** (the main session commits after reading). If the directory is missing or incomplete, rerun it the same way (one runner at a time; refusals reported verbatim, never worked around).

## Next, in order

1. **Product-path results.** Read the README and spot-check the JSON with your own reader; commit. Any cell where v15 differs from v8 is investigated before anything else — 096's engine half and 082's fix are on the v8 line for the first time.
2. **Native R0c-frame** — the command is in `PREDICTION-R0c-frame.md`; only when no browser run is going (the native probe's readbacks use fixed waits).
3. **The B WASM shakedown** (runbook §4 step 1; uncounted; evidence under `findings/evidence/v15-shakedown/merge/`). There is no runner yet; write `tools/run_merge_wasm_shakedown.py`, reusing `run_e2_c_product_path.py`'s infrastructure (mirror and serving, browser launch, `repointed_page` for the v15 candidate page, document open, `capture_save`/`zip_report`). Design (decided here, not yet reviewed):
   - **Document**: `test-docs/merge/odt/boundaries.odt`; `odt/text-frame.odt` for the frame case.
   - **Placement**: from the document start with real keys — `ArrowDown`×n, then `End` (forward) or `Home` (backward); the page maps them to `move-*` actions (`web/e2-editor-app.js` `KEY_ACTIONS`). Self-check per case: the engine's caret rectangle equals R0b's placed caret for that case (`findings/evidence/merge-native/r0b/anchor-rect.json`, field `caret`); a case that does not match is refused, not run. If every case mismatches (native vs WASM layout), fall back to checking the caret paragraph's text and say so.
   - **Key**: real Delete/Backspace through the input adapter (Chrome: CDP `Input.dispatchKeyEvent`; Firefox: the runner's existing path) — never the toolbar or a direct API call.
   - **Cells and expectations**: C01, C02 merge; I02 (labelled, forward) and C11 (labelled, backward) merge; Y01 = type `x` and press Delete at once (the M2-1b shape) → typed-merge; C29/C30 → `nothing-selected`; C17 → `anchor-mismatch`; C15 → `key-deadline` with `keyPosted:true` (spec §17); F01 (frame) → `anchor-mismatch` expected (§18 N1), otherwise compared like a merge against R0c-frame.
   - **Outcomes**: merges — save through the fake host and compare `content.xml` with the native key arm `findings/evidence/merge-native/r0c/round-20261006T144628Z/docs/r1-<case>-key.odt` (bytes; Y01 by paragraph text with `tools/odt_paragraphs.py`); refusals — the `mergeKey.stage` above, a typed marker survives the reopen, and the toast for `keyPosted:true` never says 「沒有被改動」.
   - Get the design reviewed (opus, adversarial) before the first run counts for anything.
4. **CJK tile A/B** (runbook §4 step 2b; spec §19): an unshipped profile from the same v15 link packed with the r6 source manifest (full `cjk-r5`) into a scratch dist directory; corpus page tiles identical wherever the page's characters are in tier E.
5. Freeze shell generation v56 (only when the shell needs no more changes), pin, counted M2 (spec 4.3 as amended in 10.2, 14.4, 17, 18, 19; the M2-3 list comes from `r0c/eshape.json`), host 0.2.8 (`check_m3_assets.py` Z2-2 and "Z2 D" hardcode `cjk-r5` → change, which makes it a new pin), R. The page's `workerUrl` and `PINNED_WASM_SHA256` move to v15 together, last.

## Waiting on the owner

- Size, beyond the CJK subset (research doc §7–8): proposed and **not yet approved** — (a) measure first: throttled first open (CDP 10/50/100 Mbps) and a startup phase timeline; (b) Brotli as the preferred coding (≈ −3 MB, no relink); (c) a base-pack `FS.open` census (−1.3 to −2.7 MB, no relink). ICU data trim (−4.7 to −5.7 MB measured) is deferred to the next core rebuild, not v15.

## Standing rules (carried, plus new)

- One runner at a time; native probe runs need a quiet machine; never `pkill -f` with a pattern matching your own command line.
- Never `rm -rf "$VAR/…"` — the harness refuses it; use literal paths or new directory names.
- The owner's `PMPC指南.odt` never enters the repository (read only from `wasm_sdk_probe/build/scratch-m3-production-ui/`).
- Typed-text documents compare by paragraph text, never bytes.
- `build_cutover_page.py --write` only at the cutover; candidate measurements use `--candidate-profile`.
- New: anything packed into a profile must be built deterministically (fontTools defaults to rewriting `head.modified`; the subset tool loads with `recalcTimestamp=False`).
- `findings/evidence/**` and `handoff/**` English; specs, research, findings' prose zh-TW; specs append-only.

## Lessons this stretch

- The first subset doubled in size because "keep every layout feature" pulled in every alternate; the fix came from reading what the shaper actually applies, not from a size target.
- A content-addressed pack built by a non-deterministic tool would have changed identity on every build; caught by building twice before packing.
- The link shipped exactly what the dry run and `what_the_link_ships.py` said, and v8 stayed byte-identical — because the dry run was read before the owner ran it.
