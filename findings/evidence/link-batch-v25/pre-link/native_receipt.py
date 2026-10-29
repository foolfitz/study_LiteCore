#!/usr/bin/env python3
"""Receipt for tests/test_ordered_format_v25.py: every variant's exit code and FAIL lines.

Patches the module's runner to record what each variant printed, then runs the two tests.
"""
import json
from pathlib import Path
import sys
import unittest

SDK = Path(__file__).resolve().parents[4] / 'wasm_sdk_probe'
sys.path.insert(0, str(SDK))
import tests.test_ordered_format_v25 as t  # noqa: E402

seen = []
original = t.compile_and_run


def recording(work, test, defines):
    code, output = original(work, test, defines)
    variant = (work / ('witness.inc' if 'witness' in test.name else 'ordered_format.inc')).read_text()
    seen.append({'test': test.name, 'defines': defines, 'exit': code,
                 'variantSha256': __import__('hashlib').sha256(variant.encode()).hexdigest()[:16],
                 'failLines': [line for line in output.splitlines() if line.startswith('FAIL ')]})
    return code, output


t.compile_and_run = recording
result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(t))
print(json.dumps({'ok': result.wasSuccessful(), 'variants': seen}, indent=1))
sys.exit(0 if result.wasSuccessful() else 1)
