# Finding 111 — a prototype of the ordering fix (not product code; 2026-10-09)

`narrow-editor-v2-session.diff` against the tree's `editor-shell-v2/narrow-editor-v2-session.js` (session `ee3e53a2…`), and its unit test `f111-proto.test.mjs`. Neither is in the product. They exist to show the fix is possible where it has to live: `input/input-adapter.js` and `editor-shell/editor-session.js` are in E1-C's bundle (`e1/editor-shell-bundle-v2.json`) and cannot change, so the fix is in the v2 session subclass.

The idea: an operation that is not typed text (`_enqueue` with any label but `commit-text`), arriving while the input adapter still holds typed characters it has not handed to the session (`input._queue.length > 0`), is held with the adapter's current request number as its barrier. The subclass's `commitText` override releases, before enqueueing character k, every held operation whose barrier is below k, and after it, every one whose barrier is k. The session's queue is FIFO, so the order the engine sees is the order the keys were pressed. Typed text that the adapter cancels never reaches `commitText`; the adapter's `idle()` releases what is left.

It reads two private fields of the adapter (`_queue`, `_requestCount`). The adapter is frozen by E1-C's hash, so they cannot drift without that check going red first.

Run in a scratch copy of the tree (2026-10-09): the five tests pass with the prototype; against the tree's session the three ordering tests fail (X, Y, Delete → Delete before Y) and the two controls pass; the whole `editor-shell-v2/tests/*.test.mjs` (155 tests) passes with the prototype (160 with these five).
