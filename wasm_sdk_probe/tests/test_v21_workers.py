"""tools/v21_workers.py (S-10), run on the REAL v21 worker source in a node vm (the harness shape of
sdk/tests/sdk-worker-v21.test.mjs: a stub `self`, a stub module that can allocate).

Holds: the carrier hands an ArrayBuffer's bytes -- invalid UTF-8 and NUL included -- to
oxsdk_document_paste_markdown unchanged; the shipped `pasteMarkdown` on the same patched worker still
TextEncodes (a lone surrogate arrives as EF BF BD), so the carrier is the only raw route; the trace worker
posts a `merge-trace` event for an engine event and still completes the request.  Red cases: an anchor
missing (the patch refuses), the carrier applied twice (refuses), a carrier that TextEncodes (the bytes
test fails -- shown by a mutated carrier in the test).
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
import v21_workers as workers  # noqa: E402

HARNESS = r"""
import vm from "node:vm";
import { readFileSync } from "node:fs";
const SOURCE = readFileSync(process.argv[2], "utf8");
const MANIFEST = JSON.parse(readFileSync(process.argv[3], "utf8"));
const posted = [];
const self = { location: { href: "https://example.test/sdk-worker.js" }, addEventListener() {},
               postMessage(message) { posted.push(message); } };
const context = vm.createContext({ self, console, URL, TextDecoder, TextEncoder, setTimeout, clearTimeout,
                                   queueMicrotask, Uint8Array, ArrayBuffer, performance });
vm.runInContext(SOURCE, context, { filename: "sdk-worker.js" });
vm.runInContext(`moduleInstance = {
    calls: [], HEAPU8: new Uint8Array(1 << 20), next: 64,
    ccall(name, returnType, types, args) {
      if (name === "oxsdk_buffer_alloc") { const p = this.next; this.next += args[0] + 8; return p; }
      if (name === "oxsdk_buffer_free") return 0;
      this.calls.push({ name, args: [...args] });
      return 0;
    } };
  activeManifest = ${JSON.stringify(MANIFEST)};`, context);
const out = {};
const heapHex = (pointer, length) => Buffer.from(vm.runInContext("moduleInstance.HEAPU8", context)
  .slice(pointer, pointer + length)).toString("hex");
const lastCall = () => JSON.parse(JSON.stringify(vm.runInContext("moduleInstance.calls", context).at(-1) ?? null));
// The carrier with raw bytes: X05's shape (Latin-1 byte), a NUL, a lone surrogate's CESU bytes.
const raw = [0x43, 0x61, 0x66, 0xe9, 0x00, 0xed, 0xa0, 0x80];
vm.runInContext(`handleRequest({ protocolVersion: 1, kind: "request", requestId: 7, operation: "v21PasteMarkdownBytes",
                                 payload: { documentHandle: 1, buffer: new Uint8Array(${JSON.stringify(raw)}).buffer } })`, context);
let call = lastCall();
out.carrier = call ? { name: call.name, requestId: call.args[0], handle: call.args[1], length: call.args[3],
                       hex: heapHex(call.args[2], call.args[3]) } : null;
out.carrierResponse = posted.length ? JSON.parse(JSON.stringify(posted.at(-1))) : null;
posted.length = 0;
vm.runInContext(`handleRequest({ protocolVersion: 1, kind: "request", requestId: 8, operation: "v21PasteMarkdownBytes",
                                 payload: { documentHandle: 1, buffer: "not bytes" } })`, context);
out.carrierRefusal = JSON.parse(JSON.stringify(posted.at(-1) ?? null));
// The shipped route on the same worker: a lone surrogate is TextEncoded.
vm.runInContext(`handleRequest({ protocolVersion: 1, kind: "request", requestId: 9, operation: "pasteMarkdown",
                                 payload: { documentHandle: 1, text: "a\uD800b" } })`, context);
call = lastCall();
out.shipped = call ? { name: call.name, hex: heapHex(call.args[2], call.args[3]) } : null;
// An engine event for a pending request: the trace (if patched) and the completion.
posted.length = 0;
vm.runInContext(`pending.set(7, { operation: "v21PasteMarkdownBytes" });`, context);
vm.runInContext(`handleCEvent(${JSON.stringify(JSON.stringify({ type: "error", requestId: 7, documentHandle: 1, revision: 0,
                                                                operation: "paste-markdown", code: "INVALID_ARGUMENT",
                                                                message: "not valid UTF-8", dispatched: false }))})`, context);
out.afterEvent = JSON.parse(JSON.stringify(posted));
console.log(JSON.stringify(out));
"""

MANIFEST = Path(__file__).resolve().parent.parent / "dist" / "profiles" / "e2-editor-v21" / "sdk-manifest.json"


def run_worker(source: bytes) -> dict:
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is not installed")
    with tempfile.TemporaryDirectory() as tmp:
        worker = Path(tmp) / "sdk-worker.js"
        worker.write_bytes(source)
        harness = Path(tmp) / "harness.mjs"
        harness.write_text(HARNESS, encoding="utf-8")
        done = subprocess.run([node, str(harness), str(worker), str(MANIFEST)], capture_output=True, text=True,
                              timeout=60)
    if done.returncode != 0:
        raise AssertionError(done.stderr[-2000:])
    return json.loads(done.stdout.strip().splitlines()[-1])


class Workers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = workers.shipped_worker_text()
        cls.carrier = run_worker(workers.raw_bytes_carrier(cls.text))
        cls.trace = run_worker(workers.trace_worker(workers.raw_bytes_carrier(cls.text).decode("utf-8")))

    def test_carrier_passes_bytes_unchanged(self):
        c = self.carrier["carrier"]
        self.assertEqual(c["name"], "oxsdk_document_paste_markdown")
        self.assertEqual((c["requestId"], c["handle"], c["length"]), (7, 1, 8))
        self.assertEqual(c["hex"], "436166e900eda080")
        self.assertIsNone(self.carrier["carrierResponse"], "accepted: no response until the engine answers")
        self.assertEqual(self.carrier["carrierRefusal"]["error"]["code"], "INVALID_ARGUMENT")

    def test_shipped_route_still_text_encodes(self):
        self.assertEqual(self.carrier["shipped"]["hex"], "61efbfbd62")

    def test_engine_reply_reaches_the_page_with_dispatched(self):
        response = [m for m in self.carrier["afterEvent"] if m.get("kind") == "response"][-1]
        self.assertEqual((response["requestId"], response["ok"]), (7, False))
        self.assertEqual(response["error"]["code"], "INVALID_ARGUMENT")
        self.assertIs(response["error"]["dispatched"], False)
        self.assertFalse(any(m.get("event") == "merge-trace" for m in self.carrier["afterEvent"]))

    def test_trace_worker_posts_merge_trace_and_still_completes(self):
        traces = [m for m in self.trace["afterEvent"] if m.get("event") == "merge-trace"]
        self.assertEqual(len(traces), 1)
        self.assertEqual((traces[0]["type"], traces[0]["requestId"], traces[0]["code"]), ("error", 7, "INVALID_ARGUMENT"))
        self.assertTrue(any(m.get("kind") == "response" and m.get("requestId") == 7 for m in self.trace["afterEvent"]))

    def test_patches_touch_only_their_anchor(self):
        carrier = workers.raw_bytes_carrier(self.text).decode("utf-8")
        self.assertEqual(carrier.replace(workers.CARRIER_CASE, "", 1), self.text)
        trace = workers.trace_worker(self.text).decode("utf-8")
        self.assertEqual(trace.replace(workers.TRACE_PATCH, "", 1), self.text)

    # ---- red cases ----
    def test_red_missing_anchor_refuses(self):
        with self.assertRaises(workers.PatchError):
            workers.raw_bytes_carrier(self.text.replace('    case "pasteMarkdown":\n', '    case "pasteMd":\n'))
        with self.assertRaises(workers.PatchError):
            workers.trace_worker(self.text.replace("  switch (event.type) {", "  switch (event.kind) {", 1))

    def test_red_double_carrier_refuses(self):
        with self.assertRaises(workers.PatchError):
            workers.raw_bytes_carrier(workers.raw_bytes_carrier(self.text).decode("utf-8"))

    def test_red_a_carrier_that_text_encodes_is_caught(self):
        mutated = workers.raw_bytes_carrier(self.text).decode("utf-8").replace(
            "withWasmBytes(new Uint8Array(buffer),",
            "withUtf8(new TextDecoder().decode(new Uint8Array(buffer)),", 1)
        out = run_worker(mutated.encode("utf-8"))
        self.assertNotEqual(out["carrier"]["hex"], "436166e900eda080")


if __name__ == "__main__":
    unittest.main()
