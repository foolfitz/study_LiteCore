"""tools/v21_page_hook.py (S-3): the hook's logic, run under node against fake classes and a fake DOM.

What must hold: the wrappers pass the page's calls through unchanged (same value, same rejection object);
the page's session is captured on its first wrapped call; a request reaches session / document / editor;
a request with `textUrl` decodes strictly as UTF-8; rejections keep code, recovery, dispatched, the size
details and `recoveryFor`.  Red cases: no wrapped call -> not captured and every request refused with
HOOK_NOT_CAPTURED; a class without the method to wrap -> an `error` entry; an empty wrap list (a hook that
captures nothing) -> not captured; invalid UTF-8 at `textUrl` -> the request fails, nothing is called.
The browser half (the module URLs really share instances with the page) is the per-load positive control
`capture_check()`, exercised in the runners.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v21_page_hook as hook  # noqa: E402

HARNESS = r"""
CORE_PLACEHOLDER
const nodes = {};
const listeners = {};
const sRevision = { textContent: "0" };
const documentElement = {
  dataset: {},
  addEventListener(type, fn) { (listeners[type] ||= []).push(fn); },
  dispatchEvent(event) { (listeners[event.type] || []).forEach((fn) => fn(event)); return true; },
  appendChild(node) { nodes[node.id] = node; },
};
const fakeDocument = {
  readyState: "complete", documentElement,
  head: { appendChild(node) { nodes[node.id] = node; } },
  createElement() { return { dataset: {}, textContent: "" }; },
  querySelector(selector) { return selector === "#s-revision" ? sRevision : null; },
  addEventListener() {},
};
const bytes = { "ok.md": new TextEncoder().encode("# 標題"), "bad.bin": new Uint8Array([0x43, 0x61, 0x66, 0xe9]) };
const fakeFetch = async (url) => ({ arrayBuffer: async () => bytes[url].slice().buffer });
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const read = () => JSON.parse(nodes["v21-hook"]?.textContent || "[]");

const refusal = Object.assign(new Error("remote"), { code: "MARKDOWN_REMOTE_IMAGE", recovery: "none",
                                                     details: { dispatched: false, operation: "paste-markdown" } });
class Base { open() { return "opened"; } undo() { return Promise.resolve({ revision: 9 }); } }
function makeSession(Klass) {
  const s = new Klass();
  s.state = { snapshot: { revision: 0, state: "ready", dirty: false, hasCheckpoint: false } };
  s.enqueueCount = 4;
  s.document = { handle: 1, revision: 0, calls: [],
    async pasteMarkdown(text) {
      this.calls.push(text);
      if (text === "over") throw Object.assign(new Error("over"), { code: "INVALID_ARGUMENT",
        details: { dispatched: false, limitBytes: 65536, utf8Bytes: 65537 } });
      return { revision: 1 };
    } };
  s.editor = { async action(name, options) { return { action: name, completion: "documented-callback-visible-cursor", expectedRevision: options?.expectedRevision ?? null }; } };
  return s;
}
class FakeSession extends Base {
  offersPasteMarkdown() { return true; }
  hasUnsavedEdits() { return false; }
  action() { return "act"; }
  pasteMarkdown(text) { return text === "refuse" ? Promise.reject(refusal) : Promise.resolve({ revision: 1 }); }
}
const recoveryFor = (error) => (error?.details?.dispatched === false ? "none" : "rollback");
let n = 0;
async function request(payload) {
  n += 1;
  const id = "r" + n;
  documentElement.dataset.v21hookReq = JSON.stringify({ id, ...payload });
  documentElement.dispatchEvent({ type: "v21-hook" });
  for (let i = 0; i < 20; i += 1) { await tick(); const hit = read().find((e) => e.k === "call" && e.id === id); if (hit) return hit; }
  return null;
}
const out = {};
const env = (Session, wrap) => ({ Session, recoveryFor, document: fakeDocument, wrap,
                                  now: () => 1, defer: (fn) => setTimeout(fn, 0), fetch: fakeFetch });
const scenario = process.argv[2];
if (scenario === "main") {
  v21InstallPageHook(env(FakeSession, ["offersPasteMarkdown", "open", "pasteMarkdown", "action", "undo"]));
  out.beforeCapture = await request({ target: "hook", method: "state" });
  out.refusedBeforeCapture = await request({ target: "document", method: "pasteMarkdown", args: ["# a"] });
  const s = makeSession(FakeSession);
  out.offer = s.offersPasteMarkdown();
  out.actionPassThrough = s.action();
  out.openPassThrough = s.open();
  out.undoPassThrough = await s.undo();
  out.pageOk = await s.pasteMarkdown("# x");
  try { await s.pasteMarkdown("refuse"); } catch (error) { out.sameRejection = error === refusal; }
  await tick(); await tick();
  out.state = await request({ target: "hook", method: "state" });
  out.sdkOver = await request({ target: "document", method: "pasteMarkdown", args: ["over"] });
  out.sdkUrl = await request({ target: "document", method: "pasteMarkdown", textUrl: "ok.md" });
  out.sdkBadUrl = await request({ target: "document", method: "pasteMarkdown", textUrl: "bad.bin" });
  out.documentCalls = s.document.calls;
  out.editor = await request({ target: "editor", method: "action", args: ["move-document-end", { expectedRevision: 0 }] });
  out.noMethod = await request({ target: "editor", method: "nope" });
  out.log = read();
} else if (scenario === "missing-method") {
  class Bare extends Base { hasUnsavedEdits() { return false; } }
  v21InstallPageHook(env(Bare, ["offersPasteMarkdown"]));
  await tick();
  out.log = read();
} else if (scenario === "captures-nothing") {
  v21InstallPageHook(env(FakeSession, []));
  const s = makeSession(FakeSession);
  s.offersPasteMarkdown();
  out.state = await request({ target: "hook", method: "state" });
  out.call = await request({ target: "document", method: "pasteMarkdown", args: ["# a"] });
}
console.log(JSON.stringify(out));
"""


def run(scenario: str) -> dict:
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is not installed")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "harness.mjs"
        path.write_text(HARNESS.replace("CORE_PLACEHOLDER", hook.CORE_JS), encoding="utf-8")
        done = subprocess.run([node, str(path), scenario], capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout.strip().splitlines()[-1])


class PageHook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = run("main")

    def test_pass_through_is_exact(self):
        m = self.main
        self.assertIs(m["offer"], True)
        self.assertEqual(m["actionPassThrough"], "act")
        self.assertEqual(m["openPassThrough"], "opened")
        self.assertEqual(m["undoPassThrough"], {"revision": 9})
        self.assertEqual(m["pageOk"], {"revision": 1})
        self.assertIs(m["sameRejection"], True)

    def test_capture_and_state(self):
        st = self.main["state"]["value"]
        self.assertIs(st["captured"], True)
        self.assertEqual(st["sessions"], 1)
        self.assertEqual((st["revision"], st["pageRevision"]), (0, "0"))
        self.assertEqual(st["enqueueCount"], 4)
        self.assertEqual(st["documentHandle"], 1)

    def test_page_pastes_are_logged_without_text(self):
        pastes = [e for e in self.main["log"] if e["k"] == "paste"]
        self.assertEqual(len(pastes), 2)
        self.assertEqual((pastes[0]["ok"], pastes[0]["revision"], pastes[0]["utf8"]), (True, 1, 3))
        self.assertEqual(pastes[1]["error"]["code"], "MARKDOWN_REMOTE_IMAGE")
        self.assertEqual((pastes[1]["error"]["recovery"], pastes[1]["error"]["dispatched"]), ("none", False))
        self.assertNotIn("# x", json.dumps(pastes, ensure_ascii=False))

    def test_requests_reach_the_document_and_the_editor(self):
        over = self.main["sdkOver"]
        self.assertFalse(over["ok"])
        self.assertEqual(over["error"]["code"], "INVALID_ARGUMENT")
        self.assertEqual((over["error"]["details"]["limitBytes"], over["error"]["details"]["utf8Bytes"]), (65536, 65537))
        self.assertEqual(over["error"]["recoveryFor"], "none")
        self.assertTrue(self.main["sdkUrl"]["ok"])
        self.assertEqual(self.main["sdkUrl"]["textBytes"], len("# 標題".encode("utf-8")))
        self.assertEqual(self.main["documentCalls"], ["over", "# 標題"])
        self.assertEqual(self.main["editor"]["value"]["expectedRevision"], 0)
        self.assertEqual(self.main["noMethod"]["error"]["code"], "HOOK_NO_METHOD")

    # ---- red cases ----
    def test_red_nothing_captured_before_the_page_calls(self):
        self.assertIs(self.main["beforeCapture"]["value"]["captured"], False)
        self.assertEqual(self.main["refusedBeforeCapture"]["error"]["code"], "HOOK_NOT_CAPTURED")

    def test_red_invalid_utf8_url_never_reaches_the_sdk(self):
        bad = self.main["sdkBadUrl"]
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["error"]["name"], "TypeError")
        self.assertNotIn("Caf", json.dumps(self.main["documentCalls"]))

    def test_red_missing_method_is_an_error_entry(self):
        log = run("missing-method")["log"]
        self.assertTrue(any(e["k"] == "error" and "offersPasteMarkdown" in e["what"] for e in log))

    def test_red_a_hook_that_wraps_nothing_captures_nothing(self):
        out = run("captures-nothing")
        self.assertIs(out["state"]["value"]["captured"], False)
        self.assertEqual(out["call"]["error"]["code"], "HOOK_NOT_CAPTURED")

    def test_snippet_imports_the_page_urls(self):
        self.assertIn('from "./editor-shell-v2/narrow-editor-v2-session.js"', hook.SNIPPET)
        self.assertIn('from "./editor-shell-v2/paragraph-editor-session.js"', hook.SNIPPET)
        self.assertTrue(hook.SNIPPET.startswith('<script type="module">') and hook.SNIPPET.endswith("</script>"))
        page = (Path(__file__).resolve().parent.parent / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
        self.assertIn('from "./editor-shell-v2/narrow-editor-v2-session.js"', page)


if __name__ == "__main__":
    unittest.main()
