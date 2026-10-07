# Handoff, 2026-10-07b — v16 replaces v15 as the shipping identity; merge runs on WASM; no product-path run has measured B's page yet

Picks up from `HANDOFF-2026-10-07-v15-linked-wasm-shakedown-next.md` (its product-path section A/B is now explained by finding 113). Entry points: this file; `specs/SPEC-M3-paragraph-merge.md` **§20** (and §14–19 before it); `findings/113-the-v15-cjk-subset-has-one-family-so-cjk-lines-get-a-latin-line-height.md`; `findings/evidence/v15-shakedown/cjk-ab/README.md`; `findings/evidence/v16-shakedown/{product-path,merge}/README.md`; `findings/evidence/merge-native/README.md` (R0c-frame). Tree clean at `60f00db4`, no runner active at the end. Not pushed.

## Since the previous handoff (oldest first)

| Commit | What |
|---|---|
| `8f54ea3a` | Prediction, before the run: v15 link + full `cjk-r5` pack (A/B) should bring v8's cells back. |
| `7b8f1ec4` | Asian-font-slot probe (`tools/probe_cjk_font_slots.py`) + prediction (hypothesis: the default Asian slot resolves to a Latin font on v15). |
| `0a6222dd` | Five-family candidate + prediction. Probe fix: its fixture was a 404 page (see Lessons); added zh-TW font-name variants. |
| `0f7aff63` | **Finding 113** + `cjk-ab` evidence. |
| `7b9d87d3` | Native R0c-frame (E shape inside a text frame): F01/F02 merge 3/3, 0 KILL, as predicted; frame needs no engine refusal, N1 left for WASM. |
| `55eaefaf` | **v16** (owner chose A) + spec §20; packaging tool with `--check`. |
| `de479dd5` | Merge WASM shakedown runner and corpus layout tool, both unrun at that commit. |
| `60f00db4` | v16 product-path net (3 rounds x Chrome/Firefox) and two merge-shakedown runs. |

## Finding 113 in one paragraph

v15's two product-path reds (Chrome check 42, Firefox caret cells) came from the CJK pack, not the engine. The tier-E subset had one family (`Noto Sans CJK TC`); the default Asian font (engine writes `Liberation Sans` on v15, `Noto Sans CJK KR` on v8) and the SC/JP/KR names fell to Liberation Sans, so CJK lines got about 0.8 of v8's line height. The A/B (same v15 link, full `cjk-r5`, same instrument) restored v8 cell for cell in both browsers, so B, 096 and 082 are clean on those cells. **Open, not a v15 difference:** Taiwanese document font names (思源黑體, PMingLiU, 新細明體, Microsoft JhengHei, AR PL UMing TW, 標楷體) already get a Latin line height on v8. Undiagnosed, unmeasured as a fidelity gap.

## The shipping identity: `e2-editor-v16`

| | |
|---|---|
| Link | v15's, unchanged: wasm `ad3f68bb…`, loader `46b2f40a…`, worker `00882139…`, same export list. **No link was run.** |
| CJK pack | `cjk-sub-e5.ce59153d3861ef9c`: the same tier-E font as five families (JP KR SC TC HK), shared tables, 7,210,328 B (+9,696 over `cjk-sub-e`). Manifest `99cf5f13…`. |
| Built by | Makefile block "v16" (packaged from v15's archive, not the build tree); `wasm_sdk_probe/tools/build_cjk_subset_ttc_pack.py` (`--check` fails on a manifest that differs from what it generates or on a missing pack; red cases run in-session before the commit: a tampered v16 manifest → FAIL, and `verify()` against the tier-C font instead of tier E → 50 problems, with the right font → none). |
| Archive | `wasm_sdk_probe/build/archive/e2-editor-v16-ad3f68bb-worker-00882139-cjk-e5-ce59153d/` (7 files in `SHA256SUMS`, manifest hash equals `dist/profiles/e2-editor-v16/`). `exports.txt` was added to v15's archive (its `ATTRIBUTION.md` says why). |
| v15 | Stays archived: "linked, not shipped because of 113". v8 unchanged. |
| Spec §20 | Records the identity, **withdraws §19's tile criterion**, drafts §20.3 (every corpus page's line positions equal between v16 and the full-TTC A/B profile; tolerance to be set from a same-profile repeat before the counted comparison), and moves runbook §4's steps to v16. |

## Which page was measured (read this before trusting any "candidate" report)

`tools/run_e2_c_product_path.py --candidate-profile` repoints **`dist/e2-editor-app.js`** (line 4637 `root = PROJECT / "dist"`, line ~4814 reads it). `tools/build_cutover_page.py` repoints **`web/e2-editor-app.js`**. The two sources differ by 63 diff lines (8 hunks; B's refusal wording; `RENDER_BUSY_RETRIES` 6 -> 84). So the v15 and v16 product-path "candidate" reports measured the v8-era page with the new engine, while their `candidateCutover.note` says the cutover produces those exact bytes (product-path `pageSha256` `cc523c9c…`; the merge run that used `web/` had `3cf01330…`). The cutover tool would refuse on the sha mismatch, so it is not silent at cutover, but **no product-path run has measured B's page**.

v16 product-path result (`v16-shakedown/product-path/README.md`): 3 rounds x 2 browsers, all complete, no refusal, no session death; **no check differs from v8** (Chrome 40 PASS / 2 NE; Firefox 1 FAIL `an-inline-format-reaches-a-selection`, same on v8). The v8 baseline was **not re-run**: it is the morning's six v15-shakedown v8 reports (same runner sha, same browsers).

## Merge on WASM (uncounted, instrumented; `v16-shakedown/merge/README.md`)

Runner `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py`; a Worker observer in the served HTML writes the worker's answers into the DOM. Chrome only, one round. Run 1 served dist's page (wrong: old toasts, C15 `keyPosted:true` said 「沒有被改動」). **Run 2 served web's page:**

| Cases | Result |
|---|---|
| C01 C02 I02 C11 Y01 | all `verified-key-undo`, no reopen; paragraph text = native key arm / key-follow |
| C29 C30 | refused `nothing-selected` |
| C17 | refused `anchor-mismatch` |
| C15 | `key-deadline`, `keyPosted:true`, the uncertain sentence, never 「沒有被改動」 |
| F01 (text frame) | `anchor-mismatch` in both runs: **spec 18.1 N1 confirmed on WASM** |

Open: **M2-0** — `content.xml` bytes differ from native on both fixtures (text equal), so no byte criterion can be judged until a reduction is derived from that diff and appended to the spec. An intermittent extra toast 「重繪失敗：ENGINE_DISPOSED」 during refusal reopens (F01 run 2, C17 run 1) would fail M2-3 "no other toast". The refusal marker is typed at a `boundaries.odt` position even on `text-frame.odt` (F01's reopen check is meaningless). Not run: Firefox, rounds > 1, M2-1's tool-closed list, the v8 red case, M2-1b (N >= 20), M2-2, M2-4.

## Tools written, unrun

`wasm_sdk_probe/tools/compare_layout_corpus.py` (76 `.odt` under `wasm_sdk_probe/test-docs`, three of them deliberately broken zip files, which the tool records as not comparable and reboots the page after; the tool has not been run, and has no red case yet -- make one (e.g. a profile compared with a copy whose line spacing is changed) before its first counted comparison. The comparator red cases in `de479dd5`'s message are the merge runner's, run offline). Diagnostic profiles in `wasm_sdk_probe/dist/profiles/` (gitignored): `e2-editor-v15-cjk-r5-ab`, `e2-editor-v15-cjk-ttc5-ab`.

## Next, in order

1. **Decide how candidate measurements get the cutover's page** (owner/fable): either the product-path runner's candidate mode reads `web/e2-editor-app.js` like `build_cutover_page.py` (a runner change = new runner sha, pins move), or freeze the shell generation first. Until then product-path "candidate" results do not cover B's page.
2. **M2-0 reduction** from the WASM-vs-native `content.xml` diff (both fixtures), appended to the spec before anything is counted.
3. **Merge runner**: fix the text-frame marker; diagnose the ENGINE_DISPOSED toast; Firefox; then an **adversarial review (opus) of the runner design** before any counted M2. Questions: is an instrumented page acceptable for counted runs; placement by clicking the native caret and requiring exact equality; attributing the delete's own reply (every editor reply carries `completion`); the marker/reopen check.
4. **§20.3 corpus layout**: run `compare_layout_corpus.py` v16 vs v16 (noise), then v16 vs `e2-editor-v15-cjk-r5-ab`. Set the tolerance from the first, before the second counts.
5. Freeze shell generation **v56**, pin, counted M2 (spec 4.3 as amended through §20), host 0.2.8 (`check_m3_assets.py` Z2-2 and "Z2 D" hardcode `cjk-r5` -> `cjk-sub-e5`, which makes it a new pin), R. The page's `workerUrl` moves to v16 last (wasm pin value unchanged).

## Waiting on the owner

- Size work beyond the CJK subset (unchanged from the previous handoff: measure first, Brotli, base-pack `FS.open` census; ICU trim deferred to the next core rebuild).

## Standing rules (carried, plus new)

- One runner at a time; native probe runs need a quiet machine; never `pkill -f` with a pattern matching your own command line.
- Never `rm -rf "$VAR/…"` — the harness refuses it; use literal paths or new directory names.
- The owner's `PMPC指南.odt` never enters the repository (read only from `wasm_sdk_probe/build/scratch-m3-production-ui/`).
- Typed-text documents compare by paragraph text, never bytes.
- `build_cutover_page.py --write` only at the cutover; candidate measurements use `--candidate-profile`.
- Anything packed into a profile is built deterministically (fontTools: `recalcTimestamp=False`) and **verified table by table against what it replaces**.
- **New:** never write into a mirror subdirectory (they are symlinks into `dist/`), only the mirror root.
- `findings/evidence/**` and `handoff/**` English; specs, research, findings' prose zh-TW; specs append-only.

## Lessons this stretch

- The A/B with the same instrument and one variable settled in two runs what reading the code could not; the code reading (why not TC?) was left undone because the fix is itself the falsifiable measurement.
- The band-count guard (`len(bands) >= len(base_lines)`) counted a non-body band (the page-bottom endnote) and let a merged line aim the 038 inducer at the wrong line; a body-line count would have refused the aim instead of missing.
- A probe served a 404 page as its fixture (`build_mirror` only replaces files that already exist); an unverified "document opened" would have reported it as data.
- The page measured by "candidate" runs was not the page the cutover ships. When a tool repoints something, check which source it reads, and compare that against the tool that will ship it.
