"""Red-first witness: apply each deliberate mutation in place, run the test file that must catch it,
record which tests went red, restore the file, and verify the restore by sha256."""
import hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
M = [
 # id, file, old, new, test file, what it breaks
 ("W1", "sdk/sdk-worker.js", "        if (maskStatus !== 0) {", "        if (false) {",
  "sdk/tests/sdk-worker-v21.test.mjs", "init ignores the mask status again (pre-9.7)"),
 ("W2", "sdk/sdk-worker.js", "const actionId = EDITOR_V4_ACTION_IDS[payload.action];", "const actionId = EDITOR_V3_ACTION_IDS[payload.action];",
  "sdk/tests/sdk-worker-v21.test.mjs", "editorActionV2 reads the ABI 4 table: no ids 22/23"),
 ("W3", "sdk/sdk-worker.js", '''  ["pasteMarkdown", { field: "pasteMarkdown",
                      declaration: "document-sdk-paste-markdown" }],
''', "", "sdk/tests/sdk-worker-v21.test.mjs", "pasteMarkdown not gated on the declaration"),
 ("W4", "sdk/sdk-worker.js", 'dispatched: typeof event.dispatched === "boolean" ? event.dispatched : undefined,', "",
  "sdk/tests/sdk-worker-v21.test.mjs", "the error branch drops `dispatched`"),
 ("W5", "sdk/sdk-worker.js", "complete(requestId, { revision: event.revision });\n      break;\n    case \"comments\"",
  "complete(requestId, { ...event });\n      break;\n    case \"comments\"",
  "sdk/tests/sdk-worker-v21.test.mjs", "markdown-pasted forwarded whole, not named fields"),
 ("S1", "sdk/document-sdk.js", "    if (contract?.pasteMarkdown !== PASTE_MARKDOWN_DECLARATION) {", "    if (false) {",
  "sdk/tests/paste-markdown.test.mjs", "SDK does not gate on the declaration"),
 ("S2", "sdk/document-sdk.js", "const utf8Bytes = utf8.encode(text).byteLength;", "const utf8Bytes = text.length;",
  "sdk/tests/paste-markdown.test.mjs", "limit counted in UTF-16 units, not UTF-8 bytes"),
 ("S3", "sdk/document-sdk.js", "if (utf8Bytes > MARKDOWN_PASTE_LIMIT_BYTES) {", "if (utf8Bytes >= MARKDOWN_PASTE_LIMIT_BYTES) {",
  "sdk/tests/paste-markdown.test.mjs", "exactly the limit refused (off by one)"),
 ("C1", "editor-shell-v2/narrow-editor-v2-session.js", '''  "move-document-start", "move-document-end",
]);''', '''  "move-document-start",
]);''', "editor-shell-v2/tests/closed-lists.test.mjs", "BOUNDARY_CAPABLE_MOVES loses move-document-end"),
 ("C2", "editor-shell-v2/narrow-editor-v2-client.js", '''      throw invalidResult(
        `no inherited postcondition applies to ${String(action)}`, { action, result });''', "",
  "editor-shell-v2/tests/closed-lists.test.mjs", "_validateInherited's final branch removed (falls through)"),
 ("C3", "editor-shell-v2/narrow-editor-v2-client.js", '''      || DOCUMENT_MOVE_ACTIONS.has(action)) return "move";''', ''') return "move";''',
  "editor-shell-v2/tests/closed-lists.test.mjs", "the ABI 5 moves are in no postcondition class"),
 ("P1", "editor-shell-v2/paragraph-editor-client.js", '''  "MARKDOWN_UNDO_UNREADABLE",
  "MARKDOWN_CHECKPOINT_FAILED",''', '''  "MARKDOWN_CHECKPOINT_FAILED",''',
  "editor-shell-v2/tests/markdown-paste-session.test.mjs", "a header pre-dispatch code missing from the JS list"),
 ("P2", "editor-shell-v2/narrow-editor-v2-session.js", '''      if (this.state.snapshot.dirty === true
          && this._checkpointStamp !== this._currentContentStamp) {''', '''      if (false) {''',
  "editor-shell-v2/tests/markdown-paste-session.test.mjs", "the paste goes out over a failed checkpoint"),
 ("P3", "editor-shell-v2/narrow-editor-v2-session.js", '''    return this._enqueue("paste-markdown", async ({ document }) => {
      await this._checkpointBeforeBoundaryMove(document);''', '''    return this._enqueue("paste-markdown", async ({ document }) => {''',
  "editor-shell-v2/tests/markdown-paste-session.test.mjs", "no checkpoint before the paste (the pre-10.1 design)"),
 ("P4", "editor-shell-v2/paragraph-editor-client.js", '''  if (!barrier && (error?.details?.dispatched ?? error?.dispatched) === false)
    return "refused-no-mutation";''', "",
  "editor-shell-v2/tests/markdown-paste-session.test.mjs", "`dispatched: false` alone no longer gives none"),
 ("P5", "editor-shell-v2/narrow-editor-v2-session.js", "    this._beforeEnqueue?.(label);\n    this.enqueueCount += 1;\n",
  "    this.enqueueCount += 1;\n",
  "editor-shell-v2/tests/markdown-paste-session.test.mjs", "the beforeEnqueue hook is never called"),
 ("P6", "editor-shell-v2/narrow-editor-v2-session.js", "    this._beforeEnqueue?.(label);\n    this.enqueueCount += 1;\n",
  "    this._beforeEnqueue?.(label);\n",
  "editor-shell-v2/tests/markdown-paste-session.test.mjs", "enqueueCount never counts"),
 ("K1", "web/e2-editor-app.js", "  return action !== undefined && offered(action) === true ? action : null;",
  "  return action !== undefined ? action : null;", "editor-shell-v2/tests/page-document-keys.test.mjs",
  "the page takes Ctrl+Home/End whether or not the profile offers the move"),
 ("K2", "web/e2-editor-app.js", "  if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey || event.isComposing) return null;",
  "  if (!(event.ctrlKey || event.metaKey) || event.altKey || event.isComposing) return null;",
  "editor-shell-v2/tests/page-document-keys.test.mjs", "Shift+Ctrl+Home taken"),
 ("K3", "web/e2-editor-app.js", "  return event.repeat === true || unanswered > 0;", "  return false;",
  "editor-shell-v2/tests/page-document-keys.test.mjs", "repeats and same-key presses are not dropped (D9)"),
 ("K4", "web/e2-editor-app.js", '''  const fromPoint = pointMovesInFlight === 0 && shape !== "collapsed"
    && Array.isArray(gestures) && !gestures.includes(shape);''', '''  const fromPoint = false;''',
  "editor-shell-v2/tests/page-document-keys.test.mjs", "on a range the move is sent as is (no moveFromPoint, D4)"),
 ("K5", "web/e2-editor-app.js", '''  if (takeDocumentKey(event)) return;
  if (accel) return;''', '''  if (accel) return;
  if (takeDocumentKey(event)) return;''',
  "editor-shell-v2/tests/page-document-keys.test.mjs", "the binding sits after the accel bail-out (finding 142 as shipped)"),
 ("D1", "web/e2-editor-app.js", "  button.hidden = session?.offersPasteMarkdown?.() !== true;", "  button.hidden = false;",
  "editor-shell-v2/tests/page-markdown-dialog.test.mjs", "the Markdown entry shown on every profile (M8)"),
 ("D2", "web/e2-editor-app.js", '''function cancelMarkdownDialog() {
  closeMarkdownDialog();
}''', '''function cancelMarkdownDialog() {
  void insertMarkdownFromDialog();
}''', "editor-shell-v2/tests/page-markdown-dialog.test.mjs", "取消 sends the text (M11)"),
 ("D3", "web/e2-editor-app.js", '''  if (shape !== "collapsed") { showMarkdownMessage("請先取消選取"); return; }''', "",
  "editor-shell-v2/tests/page-markdown-dialog.test.mjs", "插入 with a range selected sends (9.14)"),
 ("H1", "web/e2-editor-app.js", '''  return last !== null && last.settled === false && last.action === action
    && enqueueCount === last.enqueueMark;''', '''  return last !== null && last.settled === false && last.action === action;''',
  "editor-shell-v2/tests/page-held-after-move.test.mjs", "§10.3 rule 1 without the enqueue counter"),
 ("H2", "web/e2-editor-app.js", '''  const send = heldDeletes.last;
  if (heldDeletes.sending || send === null || send.held.length === 0) return;''', '''  return;''',
  "editor-shell-v2/tests/page-held-after-move.test.mjs", "§10.3 rule 4 off: held presses not released before other items"),
 ("H3", "web/e2-editor-app.js", '''    heldDeletes.last.held.push(action);''', '''    heldDeletes.last.held.push(heldDeletes.last === null ? action : "delete-forward");''',
  "editor-shell-v2/tests/page-held-after-move.test.mjs", "§10.3 rule 2 off: a held press loses its own key"),
 ("T2", "sdk/document-sdk.d.ts", '''  pasteMarkdown(text: string, options?: AbortableOptions): Promise<MarkdownPasteResult>;
''', "",
  "editor-shell-v2/tests/declaration-drift.test.mjs", "the SDK .d.ts does not declare pasteMarkdown"),
 ("T3", "sdk/document-sdk.d.ts", "export const MARKDOWN_PASTE_LIMIT_BYTES: 65536;", "export const MARKDOWN_PASTE_LIMIT_BYTES: 16384;",
  "editor-shell-v2/tests/declaration-drift.test.mjs", "the declared limit drifts from the runtime's"),
 ("T1", "editor-shell-v2/narrow-editor-v2-client.d.ts", '''export type EditorV4AppendedAction =
  | "move-document-start"
  | "move-document-end";''', '''export type EditorV4AppendedAction =
  | "move-document-start";''', "editor-shell-v2/tests/declaration-drift.test.mjs", "the .d.ts drifts from the runtime's ABI 5 list"),
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

only = set(sys.argv[1:])
results = []
for mid, rel, old, new, testfile, what in M:
    if only and mid not in only: continue
    path = ROOT / rel
    original = path.read_bytes()
    before = sha(path)
    text = original.decode("utf-8")
    n = text.count(old)
    if n != 1:
        results.append({"id": mid, "error": f"anchor occurs {n} times in {rel}"}); continue
    path.write_text(text.replace(old, new), encoding="utf-8")
    try:
        run = subprocess.run(["node", "--test", testfile], cwd=ROOT, capture_output=True, text=True, timeout=600)
    finally:
        path.write_bytes(original)
    assert sha(path) == before, f"{rel} was not restored"
    out = run.stdout + run.stderr
    summary = {k: int(v) for k, v in re.findall(r"^ℹ (tests|pass|fail) (\d+)$", out, re.M)}
    failed = sorted(set(re.findall(r"^✖ (.+?) \(\d", out, re.M)) - {"failing tests:"})
    results.append({"id": mid, "file": rel, "what": what, "test": testfile, "exit": run.returncode,
                    "summary": summary, "red": failed})
print(json.dumps(results, ensure_ascii=False, indent=1))
