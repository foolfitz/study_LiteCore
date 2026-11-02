# Owner's v32 link (demo batch 4)

Spec `specs/SPEC-P-demo-batch-4.md`, sections 5 to 7. One fresh product link of a new identity, `e2-editor-v32`, on the existing core. It touches no frozen profile, no host, no core, no count chain. Calc is not linked.

## The line

From `wasm_sdk_probe/`:

```bash
bash tools/link_demo_batch_4_owner.sh
```

About 3 minutes (v31 and ods-editor-v3 together took 5 min 7 s). It refuses if an attempt exists. If it stops, keep the files and report; do not retry or clean.

Expected at the end: `v32 preconditions hold` twice, then four sha256 lines. If the link fails on an undefined symbol, that is the new unit: `pre-link/symbols.json` says the two sfx2 symbols exist in the archives, so report the name.

An agent may run this line only if the owner says so in that session ("連結你幫我跑").

## After the link (agent)

1. Archive as `build/archive/e2-editor-v32-<wasm8>-worker-<worker8>`, with `SHA256SUMS` and `ATTRIBUTION.md`. Template: the v31 archive.
2. `make e2-c-assets` (the tree is ahead of `dist/` on purpose until here).
3. **P4**: `python3 -I tools/check_writer_toggle.py --profile e2-editor-v32 --out ../findings/evidence/demo-batch-4/p4/run-01`. It has never run against an engine. Its first red is the instrument's until shown otherwise. T7's long fixture has 20,000 paragraphs: opening it is the slow step.
4. P4's red cases, all three must read `P4_RED`: `--mutate swap-levels`, `--mutate no-undo`, `--mutate no-second-press`.
5. **P1'**: `python3 -I tools/check_writer_align.py --profile e2-editor-v32 --out ../findings/evidence/demo-batch-4/p1/run-01`. Alignment now goes through the new read, so this is a real regression, and `P1c/list-button-keeps-the-caret` is the cell finding 180 turned around.
6. If either finds the read wrong on Wasm: stop. The native proof (N4, N5) does not bind the Wasm engine. In particular read the first press's latency: two reads per press, and the Wasm factor on the bridge has never been measured.
7. `python3 tools/build_cutover_page.py --profile e2-editor-v32`; freeze generation 87 (template `findings/evidence/demo-batch-3/freeze-86/freeze.py`, exclusion for `sdk/v32-paragraph-read-worker.js`); repoint the bundle line in the Makefile. `editor-shell-v2/` gained no file.
8. Derive v87 tools and V0' from `demo-batch-3/derive/derive_v86_tools.py` and `derive_v0_prime_86.py`. The next F3 runner takes the toast wait as a replacement (finding 178's append). Chain template `demo-batch-3/chain-86.sh`. **Add no file under `sdk/` or `editor-shell-v2/` while it runs.**
9. Units and mutation tools by hand: the chain does not run them (`node --test editor-shell-v2/tests/*.test.mjs`, `node --test tests/calc-*.test.mjs tests/ods-*.test.mjs`, `tools/check_calc_{format_entry,range,autosave}_mutations.py`). The Calc tools should not move.
10. Host 0.2.52 from `host-0.2.51/derive_host_0251.py`; Writer only moves. `host_batch4`, from `host-0.2.51/host_batch3.py`: real keys, save, WebDAV read-back. T6 extended to the menu open, both themes.

## Declared moves in F3

The hidden setter buttons stay in the DOM and the runner clicks them by `data-action`, so the runner is not edited and F3 drives the new read.

- A range stays selected after a paragraph action: it used to collapse. A cell that read a collapsed selection afterwards moves.
- No notice on a blank document's bullet: the prompt's premise is gone.
- Every moved cell is explained one by one. None is loosened.

## The owner's hand test, once the host is installed

- 標題 button opens a menu: 內文, 標題 1 to 4. The current level has a check mark. Picking the current level goes back to body.
- 項目符號 and 編號: press once on, press again off. 移除清單 and 內文 are gone from the toolbar.
- Type after any of these: the letter lands where the caret was (finding 180).
- Select the first word of a paragraph, pick a heading: the whole paragraph becomes the heading, no frame (finding 181).
- Select from the middle of one paragraph into the next, pick a heading: both become headings and the session stays alive (finding 182).
- A new blank document: bullet, heading: no notice.
