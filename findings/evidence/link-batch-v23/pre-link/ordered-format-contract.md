# Ordered format command contract

The production include `wasm_sdk_probe/src/ordered_format.inc` implements the synchronous command portion of SPEC-M3 §16.3. Integration must include it in the engine anonymous namespace after the legacy format helper definitions, only under `OXSDK_E2_V23_LINK_BATCH`, and route paragraph-format actions to `startOrderedFormatAction`.

## Integration obligations

- `expectOrderedUno(name)` accumulates expected names for the current command. It must not discard the format result when SelectText is registered.
- `orderedUnoResult(name, payload)` looks up the current command's retained results after the poll flush. Both names remain available until reply composition finishes.
- `setOrderedReply(function)` schedules exactly one owned reply for the first post-command poll and supplies any request tracking required by the existing serializers. The format code itself does not start asynchronous tracking.
- v23 callbacks must bypass legacy format barrier observers and finishers. The temporary `gFormatBarrier` is used by existing synchronous read helpers; `formatBarrierActive()` tests its target, not its stage. The global is cleared before returning from the command.
- `completeFormatBarrier` and `failFormatBarrier` are serializer dependencies, called only from the deferred reply. No LOK call occurs in that reply.

## Decisions retained or made explicit

The cross-paragraph route preserves the caller's selected range rather than replacing it with SelectText. Its per-block content identity and target-state proof remain mandatory. The ordered verdict additionally requires a synchronous NONE restoration and rejects malformed, unknown, unparsed, or footnote/endnote structural readback on this route; the old finalizer omitted those checks on its early cross-route branch. These changes narrow acceptance.

The single-paragraph route captures the 046 fingerprint at the synchronous selected location, checks the 037 type before HTML, and restores with a direct NONE read. Missing or unusable accessibility fingerprints retain explicit declined evidence. Equal paragraph text remains indistinguishable: **L-format-read-identity-by-content** is not removed by this change. Callback containment is intentionally absent.

An empty SelectText read never enters the HTML call. With result attribution present, it yields `MUTATION_OUTCOME_UNKNOWN`, `failureShape: select-text-returned-none`, on the first reply poll. If attribution itself is absent, the first-poll missing-proof refusal takes precedence. No timer or queued stage can postpone either refusal.

## Reproducible focused test

```bash
python3 wasm_sdk_probe/tests/test_ordered_format.py
```

The test compiles the actual production include against a fake synchronous LOK and declarations extracted from `probe_engine.cpp`. The unchanged implementation passes. Four separately compiled mutations must fail at runtime: treating NONE as TEXT; assuming restoration; ignoring SelectText attribution; and postponing verdict instead of answering on the first poll. Compiler errors are not accepted as mutation failures.

Additional cases cover stale nonempty callback rectangles with a successful synchronous NONE read, absent format attribution, cross-range success without SelectText, cross-block identity failure, and malformed cross-range markup. This is bounded command integration evidence, not native RESET, complete engine compilation, browser, or WASM evidence. No project build or native RESET execution was performed by this subtask.
