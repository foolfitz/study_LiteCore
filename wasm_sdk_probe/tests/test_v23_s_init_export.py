#!/usr/bin/env python3
"""Bounded snapshot transport controls; no browser or SDK changes."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from run_v23_s_init import export_page, EXPORT_BEGIN, EXPORT_CHUNK_BYTES


class ExportTests(unittest.TestCase):
    def transfer(self, defect=None):
        page = {'complete': True, 'pixels': 'x' * (1048576 + 123), 'unicode': '😀字' * 10000}
        raw = json.dumps(page, ensure_ascii=False).encode()
        offsets = []
        def evaluate(session, expression):
            if expression == EXPORT_BEGIN:
                return {'byteLength': len(raw), 'sha256': '0' * 64 if defect == 'hash' else hashlib.sha256(raw).hexdigest()}
            if expression == 'delete globalThis.__sinitExportBytes': return True
            start, end = map(int, re.search(r'subarray\((\d+), (\d+)\)', expression).groups())
            offsets.append(start)
            chunk = raw[start:end]
            if start == 0 and defect == 'truncated': chunk = chunk[:-1]
            if start == 0 and defect == 'wrong-chunk': chunk = bytes([chunk[0] ^ 1]) + chunk[1:]
            encoded = base64.b64encode(chunk).decode()
            self.assertLess(len(encoded), 1048576)
            return encoded
        actual, metadata = export_page(None, evaluate)
        self.assertEqual(actual, page)
        self.assertEqual(metadata['byteLength'], len(raw))
        self.assertEqual(offsets, list(range(0, len(raw), EXPORT_CHUNK_BYTES)))

    def test_large_unicode_snapshot(self): self.transfer()
    def test_truncated_chunk(self):
        with self.assertRaisesRegex(ValueError, 'chunk length'): self.transfer('truncated')
    def test_wrong_chunk(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): self.transfer('wrong-chunk')
    def test_wrong_hash(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): self.transfer('hash')

if __name__ == '__main__': unittest.main()
