# F3-81: the product-path suite on frozen generation 81 (v27), read against F3-80 (2026-10-30)

Spec `specs/SPEC-M3-v27-finding-176.md` 7.3 F3-81 and section 8.

The runner is `wasm_sdk_probe/tools/run_v81_f3_clipboard.py`, committed `33842e1fe` before its first run. It is the clipboard F3 runner of F3-80 rebound to generation 81, a closed-list derivation; the bound `run_e2_c_product_path.py` is still `7ba30235...`.

The stale-value scan was run before the first run (`../stale-scan/`): red on the parents, green on the derived tools. Local mirror of `dist/` (generation 81, profile v27), no DDEV.

## run-01 (Chrome, then Firefox)

`run-01/{chrome,firefox}/`. Both runner exits are 1. That is the declared `ok: false`: the report verdict is "the recovery pair disagrees: bulleting FAIL beside notice-action NOT_ESTABLISHED…", with `recoveryPairing.held: false`.

**Clipboard reads** (`clipboard-reads.json`):
- Chrome: six reads, each count equal to its toast (23, 12 x3, 5, 5), the same texts as F3-80.
- Firefox: six refused copies, no read (L-firefox-copy), as in F3-80.

## Reading 2: `equal-01.json` (`read_v81_f3_equal.py --v81 …/f3-81/run-01`): **F3_81_DECLARED_ONLY**

- Chrome 45/46 and Firefox 45/46 cells equal F3-80 (`select-all-v26/f3-clipboard/run-01`).
- The one remaining cell per browser is the declared move. `bulleting-a-blank-line-does-not-demand-a-rollback` goes PASS -> FAIL, and the FAIL is v27's, not a rollback: `observed.state "ready"`, `observed.toast ""`, `observed.unverifiedSentence null`. The bullet was verified, so there is no toast to assert on (spec 8 item 1).
- `notice-action-recovers-the-session` stays NOT_ESTABLISHED in both browsers (spec 8 item 2).
- `recoveryPairing.held` goes true -> false, and the verdict is "the recovery pair disagrees…" (spec 8 item 3).
- F3-80's reports already had `ok: false`, so `ok` is not itself a move. The verdict string and `held` are.
- No other cell moved.

`equal-01-self-test.json`: **ALL_RED, 10/10.** It applies v80's five mutations (pass->fail, ne->pass, missing, extra, empty) plus five more:
- bulleting still PASS;
- bulleting FAIL by rollback (`state recoverable-error`);
- bulleting FAIL with a toast;
- pairing still held;
- report `ok` true.

## Reading 1: `read-01.json` (`read_v25_f3.py --v25 …`, unchanged): **F3_RED**, exactly the declared four problems (spec 8 item 5)

```
chrome bulleting-a-blank-line-does-not-demand-a-rollback [P]: v24 FAIL -> v25 FAIL
chrome notice-action-recovers-the-session [recovery-pairing]: held False
firefox bulleting-a-blank-line-does-not-demand-a-rollback [P]: v24 FAIL -> v25 FAIL
firefox notice-action-recovers-the-session [recovery-pairing]: held False
```

Reading 2's tool checks the same thing (`reading1.exactlyDeclared: true`).

Reading 1's `improved` list is F3-80's minus exactly the two bulleting cells, which F3-80 listed as FAIL -> PASS. It adds nothing.

0.2.43's `prepare-release.py` must require exactly this reading-1 result (spec 8 item 5). From v27 on, no reading may require `held: true`, and the bulleting cell's PASS may not be cited for anything (spec 8 items 1, 3). Its successor is S3 (`../s3/`).
