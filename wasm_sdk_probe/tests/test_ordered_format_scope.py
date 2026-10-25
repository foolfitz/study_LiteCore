"""Check actual FORMAT reply helper bodies, and reject causal source mutations."""
from pathlib import Path
import unittest
from ordered_format_scope import violations

SDK = Path(__file__).resolve().parents[1]


class OrderedFormatScope(unittest.TestCase):
    def test_actual_reply_has_no_lok_or_staging_dependency(self):
        engine = (SDK / 'src/probe_engine.cpp').read_text()
        include = (SDK / 'src/ordered_format.inc').read_text()
        self.assertEqual(violations(engine, include), [])
        mutations = [
            ('direct-reply-read', engine, include.replace(
                '    finishOrderedFormatReadback();', '    readSelection();\n    finishOrderedFormatReadback();')),
            ('serializer-lok-read', engine.replace(
                'void completeFormatBarrier() {', 'void completeFormatBarrier() {\n  readSelection();'), include),
            ('old-stage-in-command', engine, include.replace(
                '  FormatStateBarrier barrier;', '  queueFormatBarrierStep(FormatBarrierStage::SelectQueued);\n  FormatStateBarrier barrier;')),
            ('restore-in-reply', engine, include.replace(
                '    finishOrderedFormatReadback();', '    restoreOrderedFormatPoint();\n    finishOrderedFormatReadback();')),
            ('legacy-RESET-only-restore', engine, include.replace(
                '    restoreOrderedFormatPoint();', '    postFormatBarrierRestore();')),
            ('missing-roots', engine, ''),
        ]
        for label, changed_engine, changed_include in mutations:
            with self.subTest(label=label):
                self.assertNotEqual((changed_engine, changed_include), (engine, include))
                self.assertTrue(violations(changed_engine, changed_include), label)


if __name__ == '__main__':
    unittest.main()
