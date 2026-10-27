# Ruling 4 named limitation: guard attribution remains NOT_ESTABLISHED

Registration under AGENTS.md section 3: **behavior exists and is exercised; an external guard against the named mutation has not been demonstrated**. This is not an unexercisable capability or a deliberately held sentinel.

The named mutation is "caret deletion after a no-op Shift extension removes two units." Ruling 4 deliberately routes empty-mark deletion cells to a fresh settled-WASM reference; a defect shared by the candidate and that reference can therefore pass S5. This limitation is already declared in S-CASES and in the aggregate. Finding 167 records the related native empty-mark behavior; it does not itself establish a regression guard for the product's delete unit.

The handoff suggested the ordered-delete gates as the external guard but did not identify a demonstrated red check. The following source inspection does not supply that demonstration:

- `wasm_sdk_probe/tests/ordered_delete_route_test.cpp` and `test_ordered_command_contract.py` exercise route classification, UTF-8/type refusal, byte caps and proof availability. The route test deliberately accepts a multi-codepoint ordinary-text selection up to the byte cap; it does not establish that an actual no-op-Shift sequence deletes exactly one logical unit.
- `wasm_sdk_probe/tests/test_ordered_engine_scope.py` checks the actual engine dependency graph, current-command proof, gesture gates and non-draining polls. Its enumerated causal mutations do not include the named two-unit deletion after a no-op extension.
- `wasm_sdk_probe/tests/extend_completion_model_test.cpp` has a `twoUnitDelete` model counter and a missing-flag red control. That is useful model coverage, but no read performed here binds that control to a mutation of the current ordered-delete product path in the specified sequence.

This is a scoped source inspection, **not an exhaustive claim that no guard exists anywhere in the repository**. No existing check is credited as red for the named mutation without a preserved causal result. Guard attribution therefore remains NOT_ESTABLISHED; the narrow S5 ordering/self-consistency claim stands. No test, product tracker or other mechanism is added to make a broader claim true.
