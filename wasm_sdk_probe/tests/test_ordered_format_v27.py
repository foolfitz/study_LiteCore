"""SPEC-M3-v27-finding-176 7.2 E1/E2: finding 176's first-block read on production source.

Native g++ against fake LOK, like test_ordered_format_v25.py: command integration evidence, not WASM
evidence.  The original must be green; "v25 behaviour" (the inc with its v27 blocks stripped, compiled WITH
the v27 define, so that it compiles) and every mutation must turn it red.

Run from wasm_sdk_probe/:  python3 -m unittest tests/test_ordered_format_v27.py
Witness before the inc edit:  python3 tests/test_ordered_format_v27.py --witness
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
V27 = '#ifdef OXSDK_E2_V27_FIRST_BLOCK'
DEFINES = ['-DOXSDK_E2_V25_FORMAT_PROOF', '-DOXSDK_E2_V27_FIRST_BLOCK']
# The native records' own payloads (findings/evidence/176/native/out/a2-empty-mid/r1.jsonl).
UNDO_EMPTY = '{\\n    \\"actions\\": \\"\\"\\n}\\n'
UNDO_ONE = ('{\\n    \\"actions\\": [\\n        {\\n            \\"index\\": \\"0\\",\\n'
            '            \\"comment\\": \\"Number On/Off\\",\\n            \\"viewId\\": \\"0\\",\\n'
            '            \\"dateTime\\": \\"2026-10-30T03:26:53,677640668\\"\\n        }\\n    ]\\n}\\n')


def compile_and_run(work, test, defines):
    binary = work / 'test'
    compiled = subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', *defines,
                               '-I' + str(work), '-I' + str(SDK / 'src'), str(test), '-o', str(binary)],
                              capture_output=True, text=True, timeout=60)
    if compiled.returncode:
        return None, compiled.stderr
    ran = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
    return ran.returncode, ran.stdout + ran.stderr


def strip_v27(source):
    """The same file as v25 compiled it: every v27 block removed, the #else half of each kept.

    Line-based; a v27 block holds no nested conditional (spec 4.1 item 6), and one that did is refused."""
    out, mode = [], None
    for line in source.splitlines(keepends=True):
        if mode is None:
            if line.rstrip('\n') == V27:
                mode = 'v27'
            else:
                out.append(line)
        elif line.startswith('#if'):
            raise AssertionError('a nested conditional inside a v27 block')
        elif line.rstrip('\n') == '#else':
            mode = 'else'
        elif line.rstrip('\n') == '#endif':
            mode = None
        elif mode == 'else':
            out.append(line)
    if mode is not None:
        raise AssertionError('an unterminated v27 block')
    return ''.join(out)


def fixtures():
    engine = (SDK / 'src/probe_engine.cpp').read_text()
    types = '\n'.join(re.search(r'(?:struct|enum class) ' + name + r' \{.*?\n\};', engine, re.S).group()
                      for name in ['EditorRect', 'FormatBarrierTarget', 'FormatBarrierStage',
                                   'FormatReadback', 'FormatBarrierRoute', 'FormatStateBarrier'])
    harness = (SDK / 'tests/ordered_format_test.cpp').read_text()
    preamble = harness[:harness.index('#include "ordered_format.inc"')]
    for before, after in [
        ('bool crossRoute=false, crossIdentity=true, malformed=false;',
         'bool crossRoute=false, crossIdentity=true, malformed=false;\n'
         'bool refuseRoute=false, multiBlock=false, rangeSingle=false, undoReadable=true;\n'
         'int undoReads=0; std::string firstBlockTag="p";'),
        ('bool routeFormatBarrier(FormatStateBarrier &b,unsigned,std::string&) {\n'
         ' b.route=crossRoute ? FormatBarrierRoute::RangeCross : FormatBarrierRoute::Collapsed;',
         'bool routeFormatBarrier(FormatStateBarrier &b,unsigned,std::string &refusal) {\n'
         ' if(refuseRoute) { refusal="gesture-not-permitted"; return false; }\n'
         ' b.route=crossRoute ? FormatBarrierRoute::RangeCross\n'
         '  : rangeSingle ? FormatBarrierRoute::RangeSingle : FormatBarrierRoute::Collapsed;'),
        ('r.parsed=true; r.blockTag="p"; r.blockCount=1; return r;',
         'r.parsed=true; r.blockTag=firstBlockTag; r.blockCount=multiBlock ? 2 : 1;'
         ' r.multiBlock=multiBlock; return r;'),
    ]:
        if preamble.count(before) != 1:
            raise AssertionError(f'preamble anchor moved: {before[:60]}')
        preamble = preamble.replace(before, after)
    preamble += ('#include "merge_key_undo.hpp"\n'
                 'bool readMergeUndoPayload(std::string &out) {\n'
                 ' calls.push_back("undo");\n'
                 f' out = undoReads++ == 0 ? "{UNDO_EMPTY}" : "{UNDO_ONE}";\n'
                 ' return undoReadable;\n'
                 '}\n')
    return types, preamble


def run_inc(inc_text):
    types, preamble = fixtures()
    with tempfile.TemporaryDirectory(prefix='v27-format-') as directory:
        work = Path(directory)
        (work / 'format_types.inc').write_text(types)
        (work / 'preamble.inc').write_text(preamble)
        (work / 'ordered_format.inc').write_text(inc_text)
        return compile_and_run(work, SDK / 'tests/ordered_format_v27_test.cpp', DEFINES)


MUTATIONS = [
    ('collapsed-check-all-routes', 'readback.multiBlock &&\n        gFormatBarrier.route != FormatBarrierRoute::Collapsed',
     'readback.multiBlock && false'),
    ('g-on-range-single', 'if (barrier.route != FormatBarrierRoute::Collapsed)\n      restoreOrderedFormatPoint();',
     'if (false)\n      restoreOrderedFormatPoint();'),
    ('undo-record-skipped', 'gFormatBarrier.undoAttempted = true;', ''),
]


class OrderedFormatV27(unittest.TestCase):
    def test_176_first_block(self):
        source = (SDK / 'src/ordered_format.inc').read_text()
        stripped = strip_v27(source)
        self.assertNotEqual(stripped, source, 'v25-behaviour strips nothing')
        variants = [('original', source), ('v25-behaviour', stripped)]
        for label, before, after in MUTATIONS:
            self.assertEqual(source.count(before), 1, label)
            variants.append((label, source.replace(before, after)))
        for label, candidate in variants:
            with self.subTest(label=label):
                code, output = run_inc(candidate)
                self.assertIsNotNone(code, output)
                self.assertEqual(code, 0 if label == 'original' else 1, output)
                if label != 'original':
                    self.assertIn('FAIL ', output)


if __name__ == '__main__':
    if sys.argv[1:] == ['--witness']:
        code, output = run_inc((SDK / 'src/ordered_format.inc').read_text())
        print(f'exit {code}')
        print(output, end='')
        raise SystemExit(0)
    unittest.main()
