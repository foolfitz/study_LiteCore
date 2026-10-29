"""SPEC-M3-link-batch-v25 6.1: findings 171 (D1/D2) and 172 (R1/R2) on production source.

Native g++ against fake LOK, like test_ordered_format.py: command integration
evidence, not WASM evidence.  Every mutation must turn the original's green red.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
V25 = '#ifdef OXSDK_E2_V25_FORMAT_PROOF'


def compile_and_run(work, test, defines):
    binary = work / 'test'
    compiled = subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', *defines,
                               '-I' + str(work), '-I' + str(SDK / 'src'), str(test), '-o', str(binary)],
                              capture_output=True, text=True, timeout=60)
    if compiled.returncode:
        return None, compiled.stderr
    ran = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
    return ran.returncode, ran.stdout + ran.stderr


def strip_v25(source):
    """The same file as v24 compiled it: every v25 block removed."""
    return re.sub(re.escape(V25) + r'\n.*?\n#endif\n', '', source, flags=re.S)


class OrderedFormatV25(unittest.TestCase):
    def test_171_dispatched_is_recorded(self):
        engine = (SDK / 'src/probe_engine.cpp').read_text()
        types = '\n'.join(re.search(r'(?:struct|enum class) ' + name + r' \{.*?\n\};', engine, re.S).group()
                          for name in ['EditorRect', 'FormatBarrierTarget', 'FormatBarrierStage',
                                       'FormatReadback', 'FormatBarrierRoute', 'FormatStateBarrier'])
        harness = (SDK / 'tests/ordered_format_test.cpp').read_text()
        preamble = harness[:harness.index('#include "ordered_format.inc"')]
        for before, after in [
            ('bool crossRoute=false, crossIdentity=true, malformed=false;',
             'bool crossRoute=false, crossIdentity=true, malformed=false;\n'
             'bool refuseRoute=false, multiBlock=false;'),
            ('bool routeFormatBarrier(FormatStateBarrier &b,unsigned,std::string&) {',
             'bool routeFormatBarrier(FormatStateBarrier &b,unsigned,std::string &refusal) {\n'
             ' if(refuseRoute) { refusal="gesture-not-permitted"; return false; }'),
            ('r.parsed=true; r.blockTag="p"; r.blockCount=1; return r;',
             'r.parsed=true; r.blockTag="p"; r.blockCount=1; r.multiBlock=multiBlock; return r;'),
        ]:
            self.assertEqual(preamble.count(before), 1, before)
            preamble = preamble.replace(before, after)
        source = (SDK / 'src/ordered_format.inc').read_text()
        variants = [('original', source), ('v24-behaviour', strip_v25(source))]
        for label, before, after in [
            ('stage-not-advanced', '  barrier.stage = FormatBarrierStage::AwaitingResult;\n#endif', '#endif'),
            ('dispatched-always-true', 'gFormatBarrier.dispatched = dispatched;', 'gFormatBarrier.dispatched = true;'),
            ('record-skipped', 'gFormatBarrier.dispatchRecorded = true;', ''),
        ]:
            self.assertEqual(source.count(before), 1, label)
            variants.append((label, source.replace(before, after)))
        self.assertNotEqual(variants[1][1], source, 'v24-behaviour strips nothing')
        with tempfile.TemporaryDirectory(prefix='v25-format-') as directory:
            work = Path(directory)
            (work / 'format_types.inc').write_text(types)
            (work / 'preamble.inc').write_text(preamble)
            for label, candidate in variants:
                with self.subTest(label=label):
                    (work / 'ordered_format.inc').write_text(candidate)
                    code, output = compile_and_run(work, SDK / 'tests/ordered_format_v25_test.cpp',
                                                   ['-DOXSDK_E2_V25_FORMAT_PROOF'])
                    self.assertIsNotNone(code, output)
                    self.assertEqual(code, 0 if label == 'original' else 1, output)
                    if label != 'original':
                        self.assertIn('FAIL ', output)

    def test_172_noop_witness(self):
        reply = (SDK / 'src/ordered_engine_reply.inc').read_text()
        start = reply.index(V25 + '\n// Finding 172')
        block = reply[start + len(V25) + 1:reply.index('\n#endif\n', start)] + '\n'
        engine = (SDK / 'src/probe_engine.cpp').read_text()
        gate = re.search(r'bool inlineFormatArgumentResolved\(.*?\n\}\n', engine, re.S).group()
        self.assertIn('gOrderedProof.stateItems.count(unoCommand)', gate, 'the shipped v23 gate moved')
        noop = 'return orderedInlineFormatStateEquals(unoCommand, requested) ? "state-noop" : nullptr;'
        variants = [('original', block)]
        for label, before, after in [
            ('noop-ignores-cache', noop, 'return "state-noop";'),
            ('noop-removed', noop, 'return nullptr;'),
            ('result-ignored', 'if (commandResultSucceeded(payload.c_str()))\n    return "uno-success";',
             'if (false)\n    return "uno-success";'),
        ]:
            self.assertEqual(block.count(before), 1, label)
            variants.append((label, block.replace(before, after)))
        with tempfile.TemporaryDirectory(prefix='v25-witness-') as directory:
            work = Path(directory)
            (work / 'shipped_gate.inc').write_text(gate)
            for label, candidate in variants:
                with self.subTest(label=label):
                    (work / 'witness.inc').write_text(candidate)
                    code, output = compile_and_run(work, SDK / 'tests/ordered_noop_witness_v25_test.cpp',
                                                   ['-DOXSDK_E2_V23_LINK_BATCH'])
                    self.assertIsNotNone(code, output)
                    self.assertEqual(code, 0 if label == 'original' else 1, output)
                    if label != 'original':
                        self.assertIn('FAIL ', output)


if __name__ == '__main__':
    unittest.main()
