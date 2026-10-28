#!/usr/bin/env python3
"""The v24 S5 reader is v23's reader with exactly the declared differences.

tools/judge_v24_feature_selection.py runs v23's functions as their own code objects re-bound to a
namespace where PROFILE, Evidence and readiness are v24's.  This checks that the re-bound functions
ARE v23's code (not copies that could drift), that the namespace differs from v23's in exactly those
three names, and that v24's readiness differs from v23's by the one declared payload line.
"""
import difflib
import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import judge_v23_feature_selection as j23  # noqa: E402
import judge_v24_feature_selection as j24  # noqa: E402


class Rebound(unittest.TestCase):
    def test_functions_are_v23_code(self):
        self.assertIs(j24.inspect_s5_without_t2.__code__, j23.inspect_s5.__code__)
        self.assertIs(j24.Evidence.__init__.__code__, j23.Evidence.__init__.__code__)
        self.assertIs(j24.Evidence.opened.__code__, j23.Evidence.opened.__code__)
        self.assertIs(j24.inspect_s5_without_t2.__globals__, j24.G)

    def test_namespace_differs_in_exactly_three_names(self):
        changed = sorted(k for k in set(j24.G) | set(vars(j23)) if j24.G.get(k, KeyError) is not vars(j23).get(k, KeyError))
        self.assertEqual(changed, ['Evidence', 'PROFILE', 'readiness'])
        self.assertEqual(j24.G['PROFILE'], 'e2-editor-v24')
        self.assertEqual(j23.PROFILE, 'e2-editor-v23')

    def test_evidence_methods_other_than_two_are_inherited(self):
        own = sorted(k for k, v in vars(j24.Evidence).items() if callable(v))
        self.assertEqual(own, ['__init__', 'opened'])

    def test_readiness_differs_by_the_route_line_only(self):
        a = inspect.getsource(j23.readiness).splitlines()
        b = inspect.getsource(j24.readiness).splitlines()
        diff = [line for line in difflib.unified_diff(a, b, lineterm='', n=0) if line[:1] in '+-' and line[:3] not in ('---', '+++')]
        self.assertEqual(len(diff), 2, diff)
        old, new = diff[0][1:], diff[1][1:]
        self.assertEqual(old.replace("'text':'Z'}", "'text':'Z','route':'uno-insert-text'}"), new)


if __name__ == '__main__':
    unittest.main()
