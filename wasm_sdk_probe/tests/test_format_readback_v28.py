"""SPEC-M3-v28-last-line-fallback 7.2 E4: the PRODUCTION parser and both predicates, compiled with the v28 define,
on the markup the native arm recorded.

`parseFormatReadback`, its three helpers, `formatBarrierReadbackSatisfied` and
`formatBarrierFallbackReadbackSatisfied` are cut from src/probe_engine.cpp (not re-written).  Two parts:

1. v27's 18 rows (tests/test_format_readback_v27.py, its own rows, expectations and pins), with the v28 define:
   the first-block fields and the first-block predicate must agree exactly as they do for v27 -- V0 cannot see
   the copy compiled with the define (review item 5).
2. The fallback rows, tool-closed: every `cl-*` cell under findings/evidence/176/native-q52/{out,out-actions,
   out-headings,out-v6} whose round-1 fallback read TEXT is a row.  The expected last-block predicate is whether
   the SAVED document's last paragraph is in the target state (read_q52.saved_last / matches) -- except the three
   out-actions pseudo-heading cells, whose expected fields and verdict are the recorded reader's (named
   L-pseudo-heading, spec 9).  A few rows also pin fields by hand.  Every row without a table reads two blocks.

Run from wasm_sdk_probe/:  python3 -m unittest tests/test_format_readback_v28.py
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
Q52 = SDK.parent / 'findings/evidence/176/native-q52'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v27 = load('format_readback_v27', SDK / 'tests/test_format_readback_v27.py')
rq = load('read_q52', Q52 / 'tool/read_q52.py')
DEFINES = ['-DOXSDK_E2_V25_FORMAT_PROOF', '-DOXSDK_E2_V27_FIRST_BLOCK', '-DOXSDK_E2_V28_LAST_BLOCK']
DIRS = ['out', 'out-actions', 'out-headings', 'out-v6']
PSEUDO = {'out-actions/cl-body-heading-last', 'out-actions/cl-nbody-sham-heading-last',
          'out-actions/cl-nhead-after-heading'}
# (listTag, blockTag, lastListTag, lastBlockTag, blockCount, unknownTagName); None = not pinned
PINNED = {
    'out/cl-n8-sham-after-bullet': ('ul', 'p', '', 'p', 2, ''),
    'out/cl-a8-after-bullet': ('ul', 'p', 'ul', 'p', 2, ''),
    'out/cl-t1-table-then-empty-last': (None, None, None, None, None, 'table'),
    'out-actions/cl-nnum-after-number': ('ol', 'p', '', 'p', 2, ''),
    'out-headings/cl-nhead-after-realheading': (None, None, '', 'p', 2, ''),
    'out-headings/cl-nbody-realheading-last': (None, None, '', 'h1', 2, ''),
    'out-headings/cl-body-realheading-last': (None, None, '', 'p', 2, ''),
    'out-v6/cl-long-300': (None, None, 'ul', 'p', 2, ''),
}
EXPECT = dict(v27.EXPECT, sham=('ul', ''))


def program(rows):
    engine = (SDK / 'src/probe_engine.cpp').read_text()
    types = '\n'.join(v27.cut(engine, r'^(?:struct|enum class) ' + name + r' \{.*?\n\};', name)
                      for name in ['EditorRect', 'FormatBarrierTarget', 'FormatBarrierStage', 'FormatReadback',
                                   'FormatBarrierRoute', 'FormatStateBarrier'])
    functions = '\n'.join(v27.cut(engine, r'^' + signature + r'.*?\n\}\n', signature) for signature in [
        r'bool formatTagIsStructural\(', r'bool formatTagIsBlock\(', r'bool formatDivIsFootnoteApparatus\(',
        r'FormatReadback parseFormatReadback\(', r'bool formatBarrierReadbackSatisfied\(',
        r'bool formatBarrierFallbackReadbackSatisfied\('])
    cases = ',\n'.join('  {%s, %s, %s, %s}' % (json.dumps(n), json.dumps(h), json.dumps(lt), json.dumps(bt))
                       for n, h, lt, bt in rows)
    return ('#include <chrono>\n#include <cstdint>\n#include <cstdio>\n#include <string>\n#include <vector>\n'
            'constexpr int LOK_SELTYPE_NONE=0, LOK_SELTYPE_TEXT=1;\n'
            + types + '\nFormatStateBarrier gFormatBarrier;\n' + functions +
            '\nstruct Case { const char *name, *html, *listTag, *blockTag; };\n'
            'int main() {\n const Case cases[] = {\n' + cases + '\n };\n'
            ' for (const Case &c : cases) {\n'
            '  gFormatBarrier = FormatStateBarrier{};\n'
            '  gFormatBarrier.selectionTypeReadable = true; gFormatBarrier.fallbackReadable = true;\n'
            '  gFormatBarrier.expectedListTag = c.listTag; gFormatBarrier.expectedBlockTag = c.blockTag;\n'
            '  gFormatBarrier.readback = parseFormatReadback(c.html);\n'
            '  gFormatBarrier.fallbackReadback = gFormatBarrier.readback;\n'
            '  const FormatReadback &r = gFormatBarrier.readback;\n'
            '  std::printf("%s\\t%s\\t%s\\t%s\\t%s\\t%u\\t%u\\t%d\\t%d\\t%d\\t%d\\t%s\\n", c.name, r.listTag.c_str(),\n'
            '              r.blockTag.c_str(), r.lastListTag.c_str(), r.lastBlockTag.c_str(), r.blockCount,\n'
            '              r.itemCount, r.multiBlock ? 1 : 0, r.parsed ? 1 : 0,\n'
            '              formatBarrierReadbackSatisfied() ? 1 : 0,\n'
            '              formatBarrierFallbackReadbackSatisfied() ? 1 : 0, r.unknownTagName.c_str());\n'
            ' }\n return 0;\n}\n')


def run(rows):
    with tempfile.TemporaryDirectory(prefix='v28-parser-') as directory:
        source = Path(directory) / 'parser_test.cpp'
        source.write_text(program(rows))
        binary = Path(directory) / 'parser_test'
        built = subprocess.run(['g++', '-std=c++17', '-Wall', *DEFINES, str(source), '-o', str(binary)],
                               capture_output=True, text=True, timeout=60)
        if built.returncode:
            raise AssertionError(built.stderr)
        out = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10, check=True).stdout
    parsed = {}
    for line in out.splitlines():
        (name, lt, bt, llt, lbt, blocks, items, multi, ok, first, last, unknown) = (line.split('\t') + [''])[:12]
        parsed[name] = {'listTag': lt, 'blockTag': bt, 'lastListTag': llt, 'lastBlockTag': lbt,
                        'blockCount': int(blocks), 'itemCount': int(items), 'multiBlock': multi == '1',
                        'parsed': ok == '1', 'satisfied': first == '1', 'lastSatisfied': last == '1',
                        'unknownTagName': unknown}
    return parsed


def fallback_rows():
    rows, expected = [], {}
    for directory in DIRS:
        cells = json.loads((Q52 / directory / 'cells.json').read_text())
        for cell in cells:
            if not cell['name'].startswith('cl-'):
                continue
            record = next(json.loads(line) for line in
                          (Q52 / directory / cell['name'] / 'r1.jsonl').read_text().splitlines()
                          if json.loads(line).get('rec') == 'measured')
            fallback = record['ops'][0]['format'].get('fallback') or {}
            if fallback.get('type') != 1:
                continue
            key = f"{directory}/{cell['name']}"
            rows.append((key, fallback['html']) + EXPECT[cell['action']])
            if key in PSEUDO:
                reader = json.loads((Q52 / directory / 'reader-output.json').read_text())['cells']
                round1 = reader[cell['name']]['rounds'][0]
                expected[key] = {'lastSatisfied': round1['LAST'] == 'satisfied',
                                 'last': tuple('' if v == 'none' else v for v in round1['last'])}
            else:
                saved = rq.saved_last(Q52 / directory / cell['name'] / 'r1.fodt.gz')
                # A row the parser must refuse (a pinned refused tag) is never satisfied: fail closed,
                # whatever the saved document says (cl-t1: applied, but behind a body-level <table>).
                refused = bool((PINNED.get(key) or (None,) * 6)[5])
                expected[key] = {'lastSatisfied': rq.matches(cell['action'], saved) and not refused, 'last': None}
    return rows, expected


def fallback_problems(parsed, expected, pinned):
    found = []
    for key, want in expected.items():
        got = parsed.get(key)
        if got is None:
            found.append(f'{key}: no output')
            continue
        if got['lastSatisfied'] != want['lastSatisfied']:
            found.append(f'{key}: last-block predicate {got["lastSatisfied"]}, expected {want["lastSatisfied"]}')
        if want['last'] is not None and (got['lastListTag'], got['lastBlockTag']) != want['last']:
            found.append(f'{key}: last fields {(got["lastListTag"], got["lastBlockTag"])} != recorded {want["last"]}')
        if not got['unknownTagName'] and got['blockCount'] != 2:
            found.append(f'{key}: {got["blockCount"]} blocks without a refused tag')
        for field, value in zip(('listTag', 'blockTag', 'lastListTag', 'lastBlockTag', 'blockCount',
                                 'unknownTagName'), pinned.get(key, ())):
            if value is not None and got[field] != value:
                found.append(f'{key}: {field} {got[field]!r} != pinned {value!r}')
    return found


class ProductionParserV28(unittest.TestCase):
    def test_v27_rows_unchanged_under_the_v28_define(self):
        rows, expected = v27.rows_and_expectations()
        self.assertEqual(len(rows), 18)
        self.assertEqual(v27.problems(run(rows), expected), [])

    def test_the_fallback_rows(self):
        rows, expected = fallback_rows()
        self.assertGreaterEqual(len(rows), 20, 'non-vacuous: the four directories hold at least 20 TEXT rows')
        self.assertTrue(PSEUDO <= set(expected), 'the pseudo-heading rows are present')
        parsed = run(rows)
        self.assertEqual(fallback_problems(parsed, expected, PINNED), [])
        # Red first: one flipped expectation and one mutated pin must each be reported.
        flipped = dict(expected)
        flipped['out/cl-n8-sham-after-bullet'] = dict(flipped['out/cl-n8-sham-after-bullet'], lastSatisfied=True)
        self.assertTrue(fallback_problems(parsed, flipped, PINNED))
        self.assertTrue(fallback_problems(parsed, expected,
                                          dict(PINNED, **{'out/cl-a8-after-bullet': ('ul', 'p', '', 'p', 2, '')})))


if __name__ == '__main__':
    unittest.main()
