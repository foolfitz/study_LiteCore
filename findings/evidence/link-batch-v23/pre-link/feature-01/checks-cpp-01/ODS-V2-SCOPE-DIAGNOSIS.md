# Existing Calc V2 carrier omission

Read-only diagnosis, 2026-10-26. No source, checker, test, profile, core or worker edits; no project compilation or linking. Only `make -n -B` command expansion and C++ `-E -P` preprocessing were performed. No carrier exception was applied.

The entire `ODS_EDITOR_V2_CORE :=` through `$(ODS_EDITOR_V2_BUILD)` Make block is byte-identical between pre-feature protocol boundary `561db7f6` and the current tree. That boundary already lacks `--carrier ODS_EDITOR_V2=...`. The target was introduced by `33bb89f9`; the range-capability source gating was introduced by `18f59653`. Both commits are ancestors of `561db7f6`.

Actual current Make-expanded preprocessing flags include `-DLOK_USE_UNSTABLE_API`, `-DOXSDK_READER_PROFILE`, `-DOXSDK_ODS_VIEWER`, `-DOXSDK_ODS_VIEWER_V2`, `-DOXSDK_ODS_EDITOR`, `-DOXSDK_ODS_RANGE`. There is no `OXSDK_MERGE_KEY_UNDO` or v23 selector. The core is `../wasm-lite/build-ods-viewer-v2`.

Using the existing checker's `compile_command`, `preprocess_args` and `run` functions, each of its three object rules was preprocessed against isolated copies of `src/` from `5d77dc84`, `561db7f6`, and the current working tree. Relative source paths and external include paths were identical. Hashes use the checker's existing normalization: discard blank lines, trim trailing whitespace. All nine runs exited 0 with empty stderr.

| Source | Object | Preprocessed SHA-256 |
| --- | --- | --- |
| `5d77dc84` | sdk_api | bbacb04eaa739a3d50dabd88d369c4de6165f9f2a3c36ba2d6a096913c42d073 |
| `561db7f6` | sdk_api | 9e518411d5311a59fff6e8185de4fb12c0d336ea1b771e5947063b61bfc52225 |
| current | sdk_api | 9e518411d5311a59fff6e8185de4fb12c0d336ea1b771e5947063b61bfc52225 |
| `5d77dc84` | probe_engine | e06ee53878f530f62396cf7696d06041809076db053fcd825af1c47682f944e1 |
| `561db7f6` | probe_engine | e71aaf342a244b45fe0d673a34375f78f723a81b01bd268ab6acbfcabdcd4da7 |
| current | probe_engine | e71aaf342a244b45fe0d673a34375f78f723a81b01bd268ab6acbfcabdcd4da7 |
| `5d77dc84` | unoembind_stub | 8d683b69586bb31c45413f5541420ac4a5ecbb14661a16bd38f5d642c5c1de83 |
| `561db7f6` | unoembind_stub | 8d683b69586bb31c45413f5541420ac4a5ecbb14661a16bd38f5d642c5c1de83 |
| current | unoembind_stub | 8d683b69586bb31c45413f5541420ac4a5ecbb14661a16bd38f5d642c5c1de83 |

Thus both differing objects already differed before feature implementation, and all three current Calc V2 preprocessed objects equal that pre-feature boundary. The stub stays equal even to the old global baseline.

Injecting `-DOXSDK_MERGE_KEY_UNDO` into Calc V2's actual probe_engine preprocessing command failed with exit 1 for both `561db7f6` and current. Actual compiler diagnostic:

```text
src/probe_engine.cpp:69:2: error: "OXSDK_ODS_VIEWER is the reader rule's shape: OXSDK_READER_PROFILE and none of the editor's defines"
   69 | #error "OXSDK_ODS_VIEWER is the reader rule's shape: OXSDK_READER_PROFILE and none of the editor's defines"
      |  ^
1 error generated.
```

The existing `guard_variants` non-B branch already selects precisely that injected-B refusal; no checker or guard change is necessary. Proposal for root/scope adjudication: append only `--carrier ODS_EDITOR_V2=probe_engine,sdk_api` to the static check invocation, exactly analogous to ODS_EDITOR_V1. This declares existing non-B source differences within the tool-closed inventory; it does not permit B, exempt unoembind_stub, change core/worker/feature behavior, or alter any old declared carrier. The complete global checker must still be run after any authorized declaration change.
