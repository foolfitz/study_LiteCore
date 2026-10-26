# ABI6 feature post-link audit 01

This is a read-only audit of the owner-produced `e2-editor-v23` link. The actual compile/link log, profile and build outputs were not modified. No archive was created by this audit.

## Results

- The fresh build log contains four ABI6-selected object compilations (`sdk_api.cpp`, `probe_engine.cpp`, `unoembind_stub.cpp`, and `editor_api.cpp`) and one link. The log reader passed; the log and its exact SHA256 are preserved here.
- The ABI6 manifest and actual loader/WASM binary contract reader passed. It checked public loader names against actual binary function exports. Manifest identity is `e2-editor-v23`, editor ABI 6, 23 actions. The sole action with an empty gesture list is `select-all`, representing the expected withheld action.
- The five requested identities match exactly: WASM `fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658`, loader `4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e`, feature worker `3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5`, manifest `2b23901ff94edd4c52611d03a31242c9ecfbf33fcf89835c1af13ac04a1e2a91`, and exports sidecar `78d4750fd2f98747ac2c677d9459873d4cf253ba14cfc86aa3f05e76b178a2a6`.
- All 250 canonical compiled-input rows, including the 189 frozen r2 core rows, match their pre-link byte and SHA256 records. The bound linkdeps record has 300 tokens and 42 direct archive references.
- All 2,337 frozen profile/archive entries remain byte-identical. Exactly four additions are present, all in the new feature profile; there are no deletions or changed old files. The shared Calc worker and frozen v22 feature-worker base match their pinned hashes. E1-C is intact.

## Preserved initial audit mistake

`audit-initial-fail.json` and `audit-initial-run.*` preserve the first audit script's failed status. Its only problem was an incorrect lookup of a top-level `withheld` field; the manifest records withholding as the action whose `editorContract.actions[*].gestures` list is empty. The corrected audit derives that representation directly, and `audit.json` is the final machine report. The actual contract reader passed in both runs. No product source or acceptance criterion was changed.

Exact command arrays, exit codes, stdout and stderr for the final audit and each reader are preserved in the adjacent command files. The fresh build-output sizes, hashes and modification times are in `audit.json`. The owner archive step remains separate and has not been performed here.


## Evidence seal

The final result is `audit.json` (PASS, zero problems). Its corrected auditor SHA256 is `b3fd92e4dd6b1e82ee9d6c3b6619e989ef890ae3a3cd9399bf56af7ac9d61c59`. `audit-initial-fail.json` and `audit-initial-run.*` preserve the original first-run output. The original script was not saved before editing; `audit-initial-script-reconstructed.py` is explicitly reconstructed by reversing only the recorded lookup/label changes, and `seal.json` records its hash and this limitation. The frozen baseline contains 2,337 unique rows, with no empty paths, hashes, or zero-byte files. The canonical compiled-input manifest has 250 nonempty rows, zero mismatches, and zero reread changes. These counts describe the audit snapshot before root created the archive; the audit was not rerun afterward.
