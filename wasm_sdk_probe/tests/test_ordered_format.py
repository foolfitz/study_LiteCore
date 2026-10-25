"""Compile the production format command against fake synchronous LOK calls.

This is command integration evidence, not native RESET or WASM evidence.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]


class OrderedFormat(unittest.TestCase):
    def test_first_poll_refusal_and_mutations(self):
        source = (SDK / 'src/ordered_format.inc').read_text()
        engine = (SDK / 'src/probe_engine.cpp').read_text()
        types = '\n'.join(re.search(r'(?:struct|enum class) ' + name +
                                   r' \{.*?\n\};', engine, re.S).group()
                          for name in ['EditorRect', 'FormatBarrierTarget',
                                       'FormatBarrierStage', 'FormatReadback',
                                       'FormatBarrierRoute', 'FormatStateBarrier'])
        variants = [('original', source)]
        for label, before, after in [
            ('read-NONE-as-TEXT', 'selected.type == LOK_SELTYPE_TEXT', 'true'),
            ('restore-assumed', 'gFormatBarrier.restorePointValid && readSelection().type == LOK_SELTYPE_NONE', 'true'),
            ('selection-proof-ignored', '(selects && !gFormatBarrier.selectionResultSeen)', 'false'),
            ('Q-does-not-clear-selection-mode', 'LOK_SETTEXTSELECTION_START, x, y',
             'LOK_SETTEXTSELECTION_RESET, x, y'),
            ('Q-intermediate-read', '      gState.document, LOK_SETTEXTSELECTION_START, x, y);',
             '      gState.document, LOK_SETTEXTSELECTION_START, x, y);\n  readSelection();'),
            ('reply-waits-instead-of-next-poll', '    finishOrderedFormatReadback();', '    return;'),
        ]:
            self.assertEqual(source.count(before), 1, label)
            variants.append((label, source.replace(before, after)))
        for forbidden in ['queueFormatBarrierStep(', 'armFormatBarrierDeadline(',
                          'stageDeadline', 'checkFormatBarrierContainment(',
                          'finishFormatBarrierAfterRestore(']:
            self.assertNotIn(forbidden, source)
        with tempfile.TemporaryDirectory(prefix='v23-format-') as directory:
            work = Path(directory)
            (work / 'format_types.inc').write_text(types)
            for label, candidate in variants:
                with self.subTest(label=label):
                    (work / 'ordered_format.inc').write_text(candidate)
                    binary = work / 'test'
                    compiled = subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra',
                        '-I' + str(work), str(SDK / 'tests/ordered_format_test.cpp'),
                        '-o', str(binary)], capture_output=True, text=True, timeout=30)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    ran = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
                    self.assertEqual(ran.returncode, 0 if label == 'original' else 1,
                                     ran.stdout + ran.stderr)
                    if label != 'original':
                        self.assertIn('FAIL ', ran.stdout)


if __name__ == '__main__':
    unittest.main()
