#!/usr/bin/env python3
"""S-10: the two NON-shipped workers of the v21 shakedown, served from the mirror only.

Arms: findings/evidence/link-batch-v21/shakedown/ARMS.md S-10; ARMS-item2.md I-8, DM-3 and §9 (rulings
DM-3 A, DM-6 narrowed); spec §12.2 (a).  A report served with either worker says
`instrumentedWorker: true` (S-1 computes it from the served bytes) and may carry ONLY: DM-3's
engine-reply clauses, records (DM-14's CORE_LOG count), and DM-17's selection precondition.

  trace_worker(text)        finding 117's trace patch (build_merge_trace_profile.ANCHOR/PATCH), placed
                            BEFORE the `switch` of handleCEvent as v20 fixed it (run_v20_shakedown.py:1150-
                            1160): every engine event is also posted as a `merge-trace` event
                            (type, id, requestId, completion, code, payload length and first 96 chars).
  raw_bytes_carrier(text)   one more request operation, RAW_BYTES_OPERATION, inserted before the
                            shipped `case "pasteMarkdown":`.  Its payload is {documentHandle, buffer:
                            ArrayBuffer}; the bytes go to `oxsdk_document_paste_markdown` through the
                            worker's own accept/withWasmBytes/callStatus, with NO TextEncoder: the only
                            route for §12.1's raw-byte items (X05-X07, X15-X17, M8-utf16le.bin).  Every
                            shipped case is left as it is, `pasteMarkdown` included.
  shipped_worker_text(profile)

Both refuse to patch unless their anchor occurs exactly once (a worker that changed under them is a
loud error, not a silent no-op).  Tests: tests/test_v21_workers.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_merge_trace_profile import ANCHOR as TRACE_ANCHOR, PATCH as TRACE_PATCH  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
RAW_BYTES_OPERATION = "v21PasteMarkdownBytes"
CARRIER_ANCHOR = ('    case "pasteMarkdown":\n'
                  '      if (typeof payload.text !== "string" || payload.text.length === 0) {\n')
CARRIER_CASE = """    // V21 SHAKEDOWN RAW-BYTES CARRIER (tools/v21_workers.py; mirror only, never shipped).
    // Spec 12.2 (a): the bytes of payload.buffer reach the export unchanged -- no TextEncoder.
    case "v21PasteMarkdownBytes": {
      const buffer = payload.buffer;
      if (!(buffer instanceof ArrayBuffer) || buffer.byteLength === 0) {
        postResponse(request.requestId, false, {
          code: "INVALID_ARGUMENT", message: "v21PasteMarkdownBytes requires a non-empty ArrayBuffer",
          dispatched: false,
        });
        break;
      }
      accept(request, () => withWasmBytes(new Uint8Array(buffer), (pointer, length) =>
        callStatus(
          "oxsdk_document_paste_markdown",
          ["number", "number", "number", "number"],
          [request.requestId, payload.documentHandle, pointer, length],
        )));
      break;
    }
"""


class PatchError(RuntimeError):
    """The anchor a patch needs is not in the worker exactly once."""


def shipped_worker_text(profile: str) -> str:
    return (PROJECT / "dist" / "profiles" / profile / "sdk-worker.js").read_text(encoding="utf-8")


def trace_worker(text: str) -> bytes:
    if text.count(TRACE_ANCHOR) != 1:
        raise PatchError("the trace patch's anchor (handleCEvent's requestId line and switch) is not there exactly once")
    patched = text.replace(TRACE_ANCHOR, TRACE_ANCHOR.replace("  switch (event.type) {",
                                                              TRACE_PATCH + "  switch (event.type) {"), 1)
    return patched.encode("utf-8")


def raw_bytes_carrier(text: str) -> bytes:
    if text.count(CARRIER_ANCHOR) != 1:
        raise PatchError("the carrier's anchor (the shipped `case \"pasteMarkdown\":`) is not there exactly once")
    if RAW_BYTES_OPERATION in text:
        raise PatchError("the worker already mentions the carrier's operation")
    return text.replace(CARRIER_ANCHOR, CARRIER_CASE + CARRIER_ANCHOR, 1).encode("utf-8")
