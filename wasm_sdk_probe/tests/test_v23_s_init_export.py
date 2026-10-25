#!/usr/bin/env python3
"""Bounded snapshot transport controls; no browser or SDK changes."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import subprocess
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
            if expression == 'delete window.__sinitExportBytes': return True
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

    def test_fresh_execute_sandboxes_share_only_page_window(self):
        page = {'complete': True, 'text': 'snapshot 😀'}
        raw = json.dumps(page, separators=(',', ':'), ensure_ascii=False).encode()
        expressions = []
        def capture(session, expression):
            expressions.append(expression)
            if len(expressions) == 1:
                return {'byteLength': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            if expression.startswith('delete '): return True
            return base64.b64encode(raw).decode()
        export_page(None, capture)
        script = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
(async () => {
  const window = {__sinit: input.page};
  const results = [];
  for (const expression of input.expressions) {
    // Each execute receives a fresh global, with the same persistent page.
    const context = vm.createContext({window, __sinit: window.__sinit,
      TextEncoder, crypto: require('node:crypto').webcrypto,
      btoa: value => Buffer.from(value, 'binary').toString('base64')});
    results.push(await vm.runInContext(expression, context));
  }
  if ('__sinitExportBytes' in window) throw new Error('snapshot not removed');
  process.stdout.write(JSON.stringify(results));
})().catch(error => { console.error(error.message); process.exitCode = 1; });
"""
        def run(items):
            return subprocess.run(['node', '-e', script], input=json.dumps(
                {'page': page, 'expressions': items}), text=True, capture_output=True)
        result = run(expressions)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertEqual(base64.b64decode(values[1]), raw)
        self.assertEqual(values[0]['sha256'], hashlib.sha256(raw).hexdigest())
        # Causal red: the historical sandbox-global storage loses the bytes.
        broken = run([x.replace('window.__sinitExportBytes', 'globalThis.__sinitExportBytes')
                      for x in expressions])
        self.assertNotEqual(broken.returncode, 0)
        self.assertIn('subarray', broken.stderr)

    def test_large_unicode_snapshot(self): self.transfer()
    def test_truncated_chunk(self):
        with self.assertRaisesRegex(ValueError, 'chunk length'): self.transfer('truncated')
    def test_wrong_chunk(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): self.transfer('wrong-chunk')
    def test_wrong_hash(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): self.transfer('hash')

if __name__ == '__main__': unittest.main()
