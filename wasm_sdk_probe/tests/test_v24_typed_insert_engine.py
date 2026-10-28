#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.1 E1: the typed-insert engine source, before any link.

1. Outside OXSDK_E2_V24_TYPED_INSERT nothing changed: with the v24 regions
   removed, each of the four engine sources has the same nonblank lines as at
   the commit that pinned the spec (ceaa2770; sha256 of those blobs below).
   So every v23 object, handleInsertText included, sees the bytes it was
   linked from, and old insert_text keeps paste semantics.
2. handleInsertTypedText refuses invalid UTF-8, NUL, LF and CR before it
   dispatches, and its reply is built on the result's presence, never on its
   `success`/`wasModified` (M1: both false on every delivery).

This reads source text; the runtime proof is T2 on recorded replies (6.4).
"""
import hashlib
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# A scratch copy of src/ for the red cases; the base blobs always come from git.
SRC = Path(os.environ.get("V24_E1_SRC", ROOT / "src"))
PIN_COMMIT = "ceaa2770"
BASE_SHA256 = {
    "probe_engine.cpp": "4c597b9240460b81df8d755ddbe8bd385b0e1eb4ae7b404e66655b747f6ef946",
    "probe_engine.hpp": "472e15d79d0e4739957bec46b31b734aba8a15037308563c33741abf7383cb97",
    "sdk_api.cpp": "042b6ca0a8357d3fef4081cd30056af302090d65e6e0d69067fea492b0db59f8",
    "editor_api.h": "33989b23ccf91020d7ed4e761ba23adbcb811a35b889bbeb9a11fa03048837a9",
}
BLOCK = re.compile(r"^#ifdef OXSDK_E2_V24_TYPED_INSERT\n.*?^#endif\n", re.M | re.S)
HEADER_REGION = re.compile(
    r"^/\*\n \* OXSDK_E2_V24_TYPED_INSERT .*?^#error \"the v24 typed insert requires the ABI6 feature engine\"\n",
    re.M | re.S)


def strip_v24(name, text):
    pattern = HEADER_REGION if name == "editor_api.h" else BLOCK
    stripped, count = pattern.subn("", text)
    return stripped, count


def nonblank(text):
    return [line for line in text.splitlines() if line.strip()]


def base_text(name):
    blob = subprocess.run(["git", "show", f"{PIN_COMMIT}:wasm_sdk_probe/src/{name}"],
                          cwd=ROOT, check=True, capture_output=True).stdout
    if hashlib.sha256(blob).hexdigest() != BASE_SHA256[name]:
        raise AssertionError(f"{PIN_COMMIT}:{name} is not the pinned base blob")
    return blob.decode()


def function_body(text, signature):
    start = text.index(signature)
    depth, i = 0, text.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
        i += 1


def without_comments(code):
    return re.sub(r"//[^\n]*", "", code)


class OutsideTheDefineNothingChanged(unittest.TestCase):
    EXPECTED_REGIONS = {"probe_engine.cpp": 4, "probe_engine.hpp": 1, "sdk_api.cpp": 1, "editor_api.h": 1}

    def test_each_source(self):
        for name, regions in self.EXPECTED_REGIONS.items():
            with self.subTest(name):
                current = (SRC / name).read_text()
                stripped, count = strip_v24(name, current)
                self.assertEqual(count, regions, "v24 regions found")
                self.assertNotIn("OXSDK_E2_V24_TYPED_INSERT", stripped, "a v24 line outside its region")
                self.assertEqual(nonblank(stripped), nonblank(base_text(name)))


class TypedInsertHandler(unittest.TestCase):
    def setUp(self):
        text = (SRC / "probe_engine.cpp").read_text()
        self.body = without_comments(function_body(text, "void handleInsertTypedText(const Command &command) {"))
        self.dispatch = self.body.index("postUnoCommand(")

    def test_refusals_precede_the_dispatch(self):
        for code in ('"INVALID_UTF8"', '"INVALID_ARGUMENT"'):
            self.assertLess(self.body.index(code), self.dispatch, code)
        for value in ("codePoint == 0 ", "codePoint == 0x0a", "codePoint == 0x0d"):
            self.assertLess(self.body.index(value), self.dispatch, value)
        self.assertLess(self.body.index('expectOrderedUno(".uno:InsertText")'), self.dispatch)

    def test_reply_rests_on_presence(self):
        reply = self.body[self.body.index("setOrderedReply("):self.dispatch]
        self.assertIn('orderedUnoResult(".uno:InsertText", payload)', reply)
        self.assertIn('emitOrderedMissingProof(command, "insert", "UNO_COMMAND_RESULT")', reply)
        self.assertLess(reply.index("emitOrderedMissingProof"), reply.index("advanceRevision()"))
        for field in ("success", "wasModified", "commandResultSucceeded"):
            self.assertNotIn(field, reply)
        for literal in ('\\"method\\":\\"uno-insert-text\\"', '\\"completion\\":\\"uno-command-result\\"', 'resultPayload'):
            self.assertIn(literal, reply)

    def test_wired(self):
        text = (SRC / "probe_engine.cpp").read_text()
        self.assertIn("case CommandType::InsertTypedText:\n    handleInsertTypedText(command);", text)
        self.assertIn("Command command{CommandType::InsertTypedText};", text)
        self.assertIn("oxsdk_document_insert_typed_text(", (SRC / "sdk_api.cpp").read_text())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
