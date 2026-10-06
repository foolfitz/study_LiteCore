# Handoff, 2026-10-06h — the E shape is wired and reviewed; v15 waits for the owner's link

Picks up from `HANDOFF-2026-10-06g-spec-reviewed-twice-r0-classified-r0b-next.md`. Entry points: this file; `handoff/RUNBOOK-relink-v15.md` (the owner's next step); `specs/SPEC-M3-paragraph-merge.md` **§14–18** (they supersede parts of §3–4, §10, §13); `findings/evidence/merge-native/README.md` sections R0b and R0c. Nothing is running.

## What happened, in order (commits)

| Commit | What |
|---|---|
| `596443ba` / `f934d4ff` | R0b: prediction first, then result. The anchor rect never equals the caret on height (SVRect takes one off; taller lines: whole line vs portion). Fence relaxed to: equal x, caret's vertical span inside the anchor's (§14). C17 (table-cell selection) sends no anchor at all — read from source, every cell selection (§14.1). |
| `3498adaf` | Header + generated-model test (M1-2). The model found a real counterexample family: a transient relayout between restore press 1 and 2 → "restored" while press 2 still queued (§15). §10.1(a)'s press-2 argument was wrong. |
| `1bb128b0` | Owner delegated §15.2 to fable: **E shape** (§16) — K1 Shift+arrow, `.uno:Escape`, K2 Shift+arrow back, `.uno:Escape`, the key; no unshifted arrow; each step sent only after the previous proof (an emptiness transition). Fable's first proposal ([Right, Shift+Left]) was withdrawn after the main session showed a K1/K2 mutex race. |
| `cfc41b55` / `60058eb4` | R0c (native, 3 files × 3 rounds): 0 KILL, 0 STOP; all 29 merges incl. the nine labelled ones and both typed cases equal Writer's key. Predicted wrong once: C15/C16 come back and Writer's key is a no-op → `key-deadline`/`keyPosted:true` — the WASM inducer §14.4 lacked (§17). |
| `06e61634` | Header and model rewritten for the E shape: 1.35 M generated sequences, 0 counterexamples, 0 liveness misses; red cases (no K2 fence, P4 broken, eager Escape #2) behave; 10/12 header mutants killed, 2 equivalent (reasons in the test). |
| `5d77dc84` | M1-1 tool (`check_merge_key_undo_scope.py`). |
| `4863f593` | Engine glue under `OXSDK_MERGE_KEY_UNDO`, v15 Makefile rules, `#error` guards, lock-scope check extended to `gMergeMutex`, all wired into `make test-e2-c-static`. |
| `9919d06a` | Page: `return-mismatch` in the "not changed" set; M1-5 test now derives expectations from the header's `kStages`. `what_the_link_ships.py --variant merge-v15`. |
| `f76c470e` | Opus review dispositions (§18): no BLOCKING. S1 fixed by design (LOK thread only feeds the tracker and queues a step via a ticket under `gMergeMutex`; merge stages written by the engine thread only); S2 try/catch → B's exit; N2/N3/N5(`unit-late`)/N6 fixed; S3 (EditEngine text) and N1 (text frames: TEXT_SELECTION before START/END → refusals) registered. |
| (this commit) | `RUNBOOK-relink-v15.md`. |

Side work the owner asked for: `research/RESEARCH-2026-10-06-wasm-size-status.md` (`b7c6cda1`) — WASM size status and fable's method analysis (ICU data ≈ 32 MB raw of the wasm's data section; CJK subset, Brotli, base-pack census need no relink).

## State

- Engine, Makefile, page, tests: committed. `make test-e2-c-static`: red only on the shell bundle manifest (by design until v56 is frozen).
- v15 is **not linked**. `dist/profiles/e2-editor-v15/` does not exist. The page still pins v8.
- Shell generation v56 **not frozen** — freeze only when the shakedown needs no more shell changes.

## Next (in order)

1. Owner runs the link per `RUNBOOK-relink-v15.md` §2; then §3 (hashes, v8 untouched, archive v15).
2. WASM shakedown (runbook §4.1), including a text-frame case (§18 N1) and C15 (`keyPosted:true`).
3. Product-path net v15 vs v8 (096's engine half and 082's fix land on this line for the first time).
4. Freeze shell v56, pin, counted M2 (the M2-3 list comes from `r0c/eshape.json`, §17), host 0.2.8, R.

## Lessons this round

- A generated model found what two review rounds had not (§15), and only after the invariant was checked when LOK processes the key and the engine's posting lag was modelled. A model that checks at decision time hid it.
- Safety-only criteria let a refuse-everything rule pass; the liveness oracle is what killed the snapshot-P and press-2 mutants.
- The M1-1 tool's first real run went red on a blank line (`-E -P` pads skipped `#if` blocks): a new check's first red was the tool, not the product — confirmed by diffing before changing anything.
- "What the link ships" is three engine changes, not one: 096's and 082's fixes have never been on the v8 line.

## Addendum, 2026-10-07 — the CJK subset rides v15

Owner chose option D (keep bundled fonts, subset CJK) and tier E, to ship with v15 (one identity change). `81ca5dad`: `tools/build_cjk_subset.py` (subset + coverage/identity/corpus checks, deterministic) and `tools/build_cjk_subset_pack.py` (pack `cjk-sub-e.2d8240354ce1cf78`, 7.2 MB raw / 5.6 MB zstd vs 12.17; `sdk/v15-writer-review-manifest.json` = r6 with only the CJK entry replaced; the v15 profile rule runs `--check` first). Evidence `findings/evidence/cjk-subset/`; spec §19; runbook updated (v15 now ships four things; WASM step 2b is a CJK tile A/B). fontconfig in the base pack scans `/instdir/share/fonts` with no prebuilt cache, so the renamed font file is found (read, not run). `check_m3_assets.py` hardcodes `cjk-r5` in two red cases: change at host 0.2.8, which makes it a new pin. The link step and command are unchanged.
