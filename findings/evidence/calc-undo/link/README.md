# The ods-editor-v4 link

Run by the agent at the owner's request ("你幫我跑連結"), 2026-11-03 16:34-16:36 +0800: load 0.38, no make running, `build/ods/editor-v4` and `dist/profiles/ods-editor-v4` absent, tree at `1a7e22aef`. Command (the runbook's, with the environment overrides unset as in the batch 3 link script):

    make -j1 build/ods/editor-v4/profile/sdk-manifest.json > build/link-ods-editor-v4-01.log 2>&1

Exit 0 in 2 min 35 s. `link-ods-editor-v4-01.log` is the full log. Read from it: the four objects compiled with `-DOXSDK_ODS_UNDO`; the link with `-sERROR_ON_UNDEFINED_SYMBOLS=1` passed; `exports.txt` ends with `_oxsdk_document_undo _oxsdk_document_redo`, and both names are in `probe.js`; the worker is `derive_ods_v4_worker.py`'s output (`4a06fbe4…`); the profile builder printed `capabilityBits` 1046835. `profile.sha256` lists the development profile's files (wasm `9f37ed5a…`). Not frozen yet: `dist/profiles/ods-editor-v4` does not exist.
