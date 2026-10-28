# e2-editor-v24 candidate attribution

This archive contains the exact owner-linked `e2-editor-v24` candidate (2026-10-28, `tools/link_v24_feature_owner.sh`, log `findings/evidence/link-batch-v24/post-link/link-v24-feature-01.log`): editor ABI 6, 23 public actions, select-all present with no granted gestures, and the typed-insert export `_oxsdk_document_insert_typed_text` declared as `editorContract.typedInsert: "document-sdk-insert-typed-text"` (SPEC-M3-link-batch-v24; fable rulings 1 and 2). It is a link candidate, not a feature acceptance or host deployment verdict.

The WASM identity is `276158084a602178f9b7219c086f749910601b1a121fca9339b10a79b0f7b639`; the worker identity is `41041fe746b2355a1768bc774a10ac59802a8e359579618be405e3696f3b9461`, the bytes of `sdk/v24-feature-worker.js`, which is the archived v23 worker `3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5` plus the closed hunk list `tests/v24-worker-delta.json`. The export list is v23's 36 entries plus the one typed-insert export.

The five bound artifacts are probe.js, probe.wasm, sdk-worker.js, sdk-manifest.json and exports.txt. SHA256SUMS binds their actual bytes; the archive name identifies both WASM and worker. Never overwrite this identity. The owner link left every previously existing profile and archive file unchanged (`findings/evidence/link-batch-v24/post-link/frozen-set-*`).
