"""SPEC-P-demo-batch-4 E2: the verdicts in src/writer_caret_bridge.h, compiled as they ship, on the rows N4 recorded.

The rows are tool-closed: every arm of findings/evidence/demo-batch-4/native-caret-read that read.  Each arm's post rows are judged by
`everyParagraphMeets` against what the command set: the command's own target must hold, and another target must not, so a predicate
that ignores a field is red.  `toggleTakesOff` is judged on the pre rows, against a hand table of what the fixture holds at each place.

Run from wasm_sdk_probe/:  python3 -I tests/test_paragraph_read_v32.py
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
N4 = SDK.parent / 'findings/evidence/demo-batch-4/native-caret-read'
# (list, block, align)
TARGET = {'bullet-on': ('ul', '', ''), 'number-on': ('ol', '', ''), 'remove': ('none', '', ''), 'h1': ('', 'h1', ''), 'h2': ('', 'h2', ''), 'h3': ('', 'h3', ''),
          'h4': ('', 'h4', ''), 'body': ('', 'p', ''), 'left': ('', '', 'left'), 'center': ('', '', 'center'), 'right': ('', '', 'right'), 'justify': ('', '', 'justify')}
OTHER = {'bullet-on': ('ol', '', ''), 'number-on': ('ul', '', ''), 'remove': ('ul', '', ''), 'h1': ('', 'h2', ''), 'h2': ('', 'h3', ''), 'h3': ('', 'h4', ''),
         'h4': ('', 'h1', ''), 'body': ('', 'h1', ''), 'left': ('', '', 'right'), 'center': ('', '', 'left'), 'right': ('', '', 'center'), 'justify': ('', '', 'center')}


def literal(text):
    return json.dumps(text, ensure_ascii=True)


def rows_cpp(rows):
    return '{' + ','.join('{%s,%s,%s,%s,%s}' % (literal(r['list']), literal(r['block']), literal(r['align']), literal(r['style']), literal(''))
                          for r in rows) + '}'


def arms():
    out = []
    for path in sorted(N4.glob('*/observations.jsonl')):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get('route') == 'read' and row['post']['ok'] == 1 and path.parent.name != 'range':
                out.append(row)
    return out


def run(cases):
    source = ['#include <cstdio>', '#include <cstring>', '#include "src/writer_caret_bridge.h"', 'using namespace probe;',
              'using Rows = std::vector<WriterParagraphRead>;', 'int main() {']
    source += cases
    source += ['return 0; }']
    with tempfile.TemporaryDirectory() as directory:
        cpp = Path(directory) / 'verdict.cpp'
        cpp.write_text('\n'.join(source))
        binary = Path(directory) / 'verdict'
        subprocess.run(['g++', '-std=c++17', '-I', str(SDK), str(cpp), '-o', str(binary)], check=True, capture_output=True, text=True)
        return subprocess.run([str(binary)], check=True, capture_output=True, text=True).stdout.split('\n')


def meets(rows, target):
    return 'everyParagraphMeets(Rows%s, %s, %s, %s)' % (rows_cpp(rows), literal(target[0]), literal(target[1]), literal(target[2]))


class Verdicts(unittest.TestCase):
    def test_every_recorded_arm(self):
        rows = arms()
        self.assertGreaterEqual(len(rows), 12, 'no rows: N4 moved')
        cases = []
        expected = []
        for row in rows:
            command = row['command']
            # A read whose paragraph did not reach the command's own target is not this test's to judge: the reader reports it.
            own = all((TARGET[command][0] == '' or (r['list'] or 'none') == TARGET[command][0]) and (TARGET[command][1] == '' or r['block'] == TARGET[command][1])
                      and (TARGET[command][2] == '' or r['align'] == TARGET[command][2]) for r in row['post']['rows'])
            cases.append('printf("%%d\\n", (int)%s);' % meets(row['post']['rows'], TARGET[command]))
            expected.append(int(own))
            cases.append('printf("%%d\\n", (int)%s);' % meets(row['post']['rows'], OTHER[command]))
            expected.append(-1)
        got = run(cases)
        for index, want in enumerate(expected):
            if want >= 0:
                self.assertEqual(int(got[index]), want, rows[index // 2]['place'])
            else:
                self.assertEqual(int(got[index]), 0, ('the other target held', rows[index // 2]['place'], rows[index // 2]['command']))

    def test_predicates(self):
        p = {'list': '', 'block': 'p', 'align': '', 'style': 'Text body'}
        ul = {**p, 'list': 'ul'}
        ol = {**p, 'list': 'ol'}
        h2 = {**p, 'block': 'h2', 'style': 'Heading 2'}
        cases = [
            (meets([], ('none', '', '')), 0),                                   # none of nothing proves nothing
            (meets([p, ul], ('ul', '', '')), 0),                                # one paragraph short
            (meets([ul, ul], ('ul', '', '')), 1),
            (meets([p], ('none', '', '')), 1),
            ('toggleTakesOff(Rows%s, "ul", "")' % rows_cpp([ul, ul]), 1),
            ('toggleTakesOff(Rows%s, "ul", "")' % rows_cpp([ul, ol]), 0),       # mixed goes on
            ('toggleTakesOff(Rows%s, "ul", "")' % rows_cpp([p]), 0),
            ('toggleTakesOff(Rows%s, "", "h2")' % rows_cpp([h2, h2]), 1),
            ('toggleTakesOff(Rows%s, "", "h2")' % rows_cpp([h2, p]), 0),
            ('toggleTakesOff(Rows%s, "", "h3")' % rows_cpp([h2]), 0),
            ('toggleTakesOff(Rows{}, "ul", "")', 0),
            ('numberingHasNoEffect(Rows%s)' % rows_cpp([h2]), 1),
            ('numberingHasNoEffect(Rows%s)' % rows_cpp([h2, ul]), 1),
            ('numberingHasNoEffect(Rows%s)' % rows_cpp([h2, p]), 0),
            ('numberingHasNoEffect(Rows%s)' % rows_cpp([ul]), 0),
            ('numberingHasNoEffect(Rows%s)' % rows_cpp([p]), 0),
        ]
        got = run(['printf("%%d\\n", (int)%s);' % c for c, _ in cases])
        for index, (case, want) in enumerate(cases):
            self.assertEqual(int(got[index]), want, case)


if __name__ == '__main__':
    unittest.main()
