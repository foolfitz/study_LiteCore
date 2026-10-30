# F3-82: the product-path suite on frozen generation 82 (v28), read against F3-81 (2026-10-30)

Spec `specs/SPEC-M3-v28-last-line-fallback.md` 7.3 F3-82 and section 8 (declared moves: none).

The runner is `wasm_sdk_probe/tools/run_v82_f3_clipboard.py`, committed `00e3f352f` before its first run: the F3-81 clipboard runner rebound to generation 82 by `../derive/derive_v82_tools.py` (closed list in its docstring); the bound `run_e2_c_product_path.py` is still `7ba30235...`. Stale-value scan before the first run (`../stale-scan/`): red on the parents, green on the derived tools, self-test holds. Local mirror of `dist/` (generation 82, profile v28; `servedShell` `a02673fa…` in both reports), no DDEV. `../f3-f4-run.sh`, 22:25-22:44 +0800.

## run-01 (Chrome, then Firefox)

Both runner exits are 1: the report is `ok: false` with "the recovery pair disagrees: bulleting FAIL beside notice-action NOT_ESTABLISHED", `recoveryPairing.held: false` -- exactly F3-81's.

Clipboard reads (`clipboard-reads.json`): Chrome six reads, each count equal to its toast (23, 12 x3, 5, 5), as in F3-81; Firefox six refused copies (`CLIPBOARD_DENIED`, L-firefox-copy), as in F3-81.

## Reading 2: `equal-01.json` (`read_v82_f3_equal.py --v82 run-01`): **F3_82_EQUAL**

- Chrome 46/46 and Firefox 46/46 cells equal F3-81 (`../../v27-176/f3-81/run-01`). No cell moved. The bulleting cell (a blank line in the middle of the document, 046's cell) stays v27's FAIL-by-design; v28's fallback does not run there.
- `recoveryPairing.held`, `ok` and the verdict prefix equal F3-81's.
- `equal-01-self-test.json`: **ALL_RED**, 8/8 (pass->fail, ne->pass, missing, extra, empty, the bulleting cell back to PASS, pairing held, report ok).
- Before the run, the reader was checked on F3-81 itself (EQUAL, 46/46) and on F3-80 (red on exactly the expected moves).

## Reading 1: `read-01.json` (`read_v25_f3.py --v25 run-01`, unchanged): **F3_RED**, exactly F3-81's four problems

```
chrome bulleting-a-blank-line-does-not-demand-a-rollback [P]: v24 FAIL -> v25 FAIL
chrome notice-action-recovers-the-session [recovery-pairing]: held False
firefox bulleting-a-blank-line-does-not-demand-a-rollback [P]: v24 FAIL -> v25 FAIL
firefox notice-action-recovers-the-session [recovery-pairing]: held False
```

Reading 2's tool checks the same (`reading1.exactlyAsF381: true`). 0.2.44's `prepare-release.py` requires exactly this, written out.
