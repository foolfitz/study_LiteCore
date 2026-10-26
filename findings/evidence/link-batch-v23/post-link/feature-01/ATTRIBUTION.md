# ABI6 feature candidate attribution

This archive contains the exact owner-linked `e2-editor-v23` candidate: editor ABI6, 23 public actions, and select-all present with no granted gestures. It is a feature candidate, not a feature acceptance or host deployment verdict.

The WASM identity is `fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658`; the isolated worker identity is `3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5`. The worker derives from frozen v22 `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`, with the reviewed ABI6 six-move extension validation. No diagnostic tail or diagnostic entry point is included. Existing public IDs and the 36 inherited public function exports are preserved.

The five bound artifacts are probe.js, probe.wasm, sdk-worker.js, sdk-manifest.json and exports.txt. SHA256SUMS binds their actual bytes; the archive name identifies both WASM and worker. Never overwrite this identity. The shared Calc worker and all previous archives/profiles were unchanged by the owner build.

Evidence: `findings/evidence/link-batch-v23/post-link/feature-01/audit-01/audit.json`, the copied actual build log in that directory, and the one-shot archive receipt `feature-01/archive.json`. Runtime acceptance remains subject to final shell binding, readiness, required independent references and the fixed feature protocol.
