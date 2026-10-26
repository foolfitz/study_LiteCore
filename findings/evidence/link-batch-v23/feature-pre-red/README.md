# Historical v19 pre-red preparation 01

This was the single authorized, uncounted Chrome preparation for case `shift-Left@caret-mid`, using the explicit v19 WASM pin and the frozen historical v57 shell mirror. It is separate from the current ABI6 shell-bundle failure and does not test or certify the current feature page.

The exact command, exit status, stdout, stderr, runner report, page snapshot, and cell report are preserved beside `preparation-01/`. The runner passed its environment guard (`kwalletLocked: b false`, `refuse: []`, `foreignCpu.ok: true`) and opened one Chrome cell. Navigation stopped with `RuntimeError: Chrome page did not finish loading` from `ChromeSession.navigate`. The saved page shows `booted: true`, the initial `list-contexts.odt` open completed at 2063.075 ms, and `view-ready` arrived at 2060.780 ms. No key input was sent (`inputs: []`). The coordinator identified the cause as the harness's generic `ChromeSession.navigate` waiting for `__probe_metrics`, which this product page does not expose; this is a navigation-observer mismatch, not a product readiness result.

The saved cell contains the full traceback, fetched page snapshot/transfer, and `cleanup: {}`. It has no readiness/edit/save measurements, no S2 inspection verdict, and no `EXPECTED_RED` result. This is an incomplete precondition, not a product verdict. The coordinator assigned a minimal existing-navigation fix and causal test; no runtime retry or counted cohort was run here.

## Subsequent retained attempts

This original preparation narrative remains unchanged above. Each later attempt is separate:

| Attempt | Actual result | Scope |
| --- | --- | --- |
| preparation-02 | One Chrome caret-mid EXPECTED_RED with actual edit/save readiness | Uncounted navigation preparation |
| counted-01 | Six Chrome EXPECTED_RED, then list-mid setup NE | Incomplete; no Firefox or aggregate judgment |
| preparation-03 | One Chrome list-mid EXPECTED_RED, literal `List ` preserved | Uncounted preparation after `de01fcf5` |
| counted-02 | Foreign-CPU refusal, zero cells | Environment only; unrelated make was untouched |
| counted-03 | Seven Chrome EXPECTED_RED, then wrap-line-end setup NE | Incomplete; no Firefox or aggregate judgment |

No partial results are spliced together. Counted03 proved the corrected list setup before stopping at an unrelated unsorted-search-rectangle discovery error. Scope agent `/root/astra_calc_scope` approved only the wrap materialization correction; its replacement cohort has not run at this checkpoint. No feature S1–S5 acceptance is established here.

The six reports and18 complete raw cell records are stored under `storage-index-01.json`, using21,445,853 compressed bytes for1,502,767,056 original bytes. `STORAGE.md` explains exact restore/verification. Original raw files remain locally unchanged and ignored. `tool-source-bindings-01.json` independently recovers every recorded Python source pin from committed Git blobs:17 rows per report,20 distinct path/hash pairs, all exact. The matching Git commit is individual blob provenance, not an assertion that its whole tree executed. Stored source blobs and the original served-source mirrors permit later source inspection without substituting the current edited tools.
