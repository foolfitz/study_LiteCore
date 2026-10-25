# Resumed v23 pure contracts, before native RESET and engine wiring

The owner explicitly resumed v23. Astra `/root/astra_calc_scope` retains the delegated decision role; its proof/cap ruling is `astra-proof-and-k1-ruling.md`. Diagnostic C stays on the existing Writer headless core and ABI 5; feature actions and ABI 6 are later.

## Established by these host unit tests

- `ordered_command_proof_test.cpp` drives the production `ordered_poll.hpp` helper with a cursor-then-selection synthetic flush. Its callback-time composer is a causal red control. Proof is available before the two callbacks on both paths; callbacks must emit no reply and the next poll must contain both state updates.
- The same test checks both immediate editor proof refusals: dispatch failure gives `LOK_COMMAND_FAILED`; dispatched without proof gives `MUTATION_OUTCOME_UNKNOWN`. A stale proof cannot override a failed dispatch. Proof presence alone does not assert command success; 059 and SDK-specific policies remain engine work.
- `ordered_delete_route_test.cpp` supplies NONE, safe TEXT unit, separator and unsupported selection oracles. It covers missing/empty/invalid UTF-8 reads, tab/object units and 128/129/4096/4097-byte boundaries. It chooses a route only, with no RESET or other LOK call.
- `test_ordered_command_contract.py` compiles the two original tests plus nine source mutations, requiring original success and runtime failure of every compilable mutant. Compile errors cannot count as red evidence. Run from the repository root:

```bash
python3 -m unittest discover -s wasm_sdk_probe/tests -p test_ordered_command_contract.py -v
```

`ordered-contract-02.txt` passes both suites, including all nine required red mutations. `ordered-contract-01.txt` is a retained instrumentation failure: the initial test driver omitted `LOK_USE_UNSTABLE_API`, so selection constants were unavailable. This was fixed to match the engine translation unit. Its compiler failures are not product failures or valid mutation reds. Earlier `ordered-reply-01.txt` predates causal isolation of the callback red; `ordered-reply-02.txt` is the corrected proof test evidence.

## Explicitly not established

These helpers are not yet included by `probe_engine.cpp`. No engine callback routing, format staging removal, empty-SelectText refusal, old-stage exclusion, diagnostic WASM identity or browser behavior is certified here. Native RESET is still NOT_ESTABLISHED until the owner compiles the prepared harness and the frozen N=5 cohort passes. In particular, no synchronous engine RESET restoration has been implemented. The diagnostic Makefile target still does not exist, so its checker remains intentionally red against the current Makefile.

No product-path/counting checker was changed and no K cohort ran. Existing Calc acceptance stays closed. The new pure tests are pre-link implementation work, not a new native/browser gate population.
