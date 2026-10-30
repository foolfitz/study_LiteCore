"""SPEC-M3-v27-finding-176 7.2 E4 (fable ruling 3 Q6.2): the PRODUCTION parser and predicate on the markup the
native arm recorded, judged against the saved documents.

`parseFormatReadback`, its three helpers and `formatBarrierReadbackSatisfied` are cut from src/probe_engine.cpp
(not re-written), compiled natively, and fed each row's recorded `format.html`
(findings/evidence/176/native/out*/<cell>/r1.jsonl).  The expected predicate result for a row is whether the
SAVED document's dispatch paragraph is in the action's target state (read_cells.saved_target) -- the ground
truth the native readers used, from a different implementation than the parser.  Three rows also pin the parsed
fields by hand (n2: the first tag is not a list; r6: two items in one list; r5: a heading block).

Run from wasm_sdk_probe/:  python3 -m unittest tests/test_format_readback_v27.py
"""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
NATIVE = SDK.parent / 'findings/evidence/176/native'
_spec = importlib.util.spec_from_file_location('read_cells', NATIVE / 'tool/read_cells.py')
read_cells = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(read_cells)

# (records directory, cell, target).  The F rows and their G twins; the product runs G.
ROWS = [('out', c, t) for c, t in [
    ('a1-text-mid', 'bullet'), ('a2-empty-mid', 'bullet'), ('n2-sham-empty-before-list', 'bullet'),
    ('n3-sham-empty-after-list', 'bullet'), ('r1-noop-empty-bulleted', 'bullet'), ('r3-number-empty-mid', 'number'),
    ('r4-none-empty-bulleted', 'none'), ('r5-heading-empty-mid', 'heading'), ('r6-bullet-empty-before-list', 'bullet'),
    ('g-a1-text-mid', 'bullet'), ('g-a2-empty-mid', 'bullet'), ('g-n2-sham-empty-before-list', 'bullet'),
    ('g-n3-sham-empty-after-list', 'bullet')]] + [('out-q63', c, t) for c, t in [
    ('g-r3-number-empty-mid', 'number'), ('g-r4-none-empty-bulleted', 'none'), ('g-r5-heading-empty-mid', 'heading'),
    ('a6g-empty-empty', 'bullet'), ('b1g-body-on-empty-heading', 'body')]]
# The barrier's expectations per action (startOrderedFormatAction): list actions set expectedListTag, the two
# paragraph-style actions expectedBlockTag.
EXPECT = {'bullet': ('ul', ''), 'number': ('ol', ''), 'none': ('none', ''), 'heading': ('', 'h1'), 'body': ('', 'p')}
# Hand-pinned parsed fields (listTag, blockTag, blockCount, itemCount, multiBlock); None = not pinned.
PINNED = {
    'n2-sham-empty-before-list': ('', 'p', None, 1, True),
    'r6-bullet-empty-before-list': ('ul', 'p', None, 2, True),
    'r5-heading-empty-mid': ('', 'h1', None, 0, True),
    'a1-text-mid': ('ul', 'p', 1, 1, False),
}


def saved_in_target(saved, target):
    if target == 'bullet':
        return bool(saved['inList']) and saved['listKind'] == 'bullet'
    if target == 'number':
        return bool(saved['inList']) and saved['listKind'] == 'number'
    if target == 'none':
        return not saved['inList']
    if target == 'heading':
        return bool(saved['heading'])
    return not saved['heading']  # body


def cut(engine, pattern, what):
    match = re.search(pattern, engine, re.S | re.M)
    if not match:
        raise AssertionError(f'{what} not found in probe_engine.cpp')
    return match.group()


def program(rows):
    engine = (SDK / 'src/probe_engine.cpp').read_text()
    types = '\n'.join(cut(engine, r'^(?:struct|enum class) ' + name + r' \{.*?\n\};', name)
                      for name in ['EditorRect', 'FormatBarrierTarget', 'FormatBarrierStage', 'FormatReadback',
                                   'FormatBarrierRoute', 'FormatStateBarrier'])
    functions = '\n'.join(cut(engine, r'^' + signature + r'.*?\n\}\n', signature) for signature in [
        r'bool formatTagIsStructural\(', r'bool formatTagIsBlock\(', r'bool formatDivIsFootnoteApparatus\(',
        r'FormatReadback parseFormatReadback\(', r'bool formatBarrierReadbackSatisfied\('])
    cases = ',\n'.join('  {%s, %s, %s, %s}' % (json.dumps(name), json.dumps(html), json.dumps(lt), json.dumps(bt))
                       for name, html, lt, bt in rows)
    return ('#include <chrono>\n#include <cstdint>\n#include <cstdio>\n#include <string>\n#include <vector>\n'
            'constexpr int LOK_SELTYPE_NONE=0, LOK_SELTYPE_TEXT=1;\n'
            + types + '\nFormatStateBarrier gFormatBarrier;\n' + functions +
            '\nstruct Case { const char *name, *html, *listTag, *blockTag; };\n'
            'int main() {\n const Case cases[] = {\n' + cases + '\n };\n'
            ' for (const Case &c : cases) {\n'
            '  gFormatBarrier = FormatStateBarrier{};\n'
            '  gFormatBarrier.selectionTypeReadable = true;\n'
            '  gFormatBarrier.expectedListTag = c.listTag; gFormatBarrier.expectedBlockTag = c.blockTag;\n'
            '  gFormatBarrier.readback = parseFormatReadback(c.html);\n'
            '  const FormatReadback &r = gFormatBarrier.readback;\n'
            '  std::printf("%s\\t%s\\t%s\\t%u\\t%u\\t%d\\t%d\\t%d\\n", c.name, r.listTag.c_str(), r.blockTag.c_str(),\n'
            '              r.blockCount, r.itemCount, r.multiBlock ? 1 : 0, r.parsed ? 1 : 0,\n'
            '              formatBarrierReadbackSatisfied() ? 1 : 0);\n'
            ' }\n return 0;\n}\n')


def rows_and_expectations():
    rows, expected = [], {}
    for directory, cell, target in ROWS:
        record = next(json.loads(line) for line in (NATIVE / directory / cell / 'r1.jsonl').read_text().splitlines()
                      if json.loads(line).get('rec') == 'measured')
        html = record['ops'][0]['format']['html']
        saved = read_cells.saved_target(NATIVE / directory / cell / 'r1.fodt.gz', 1)
        rows.append((cell, html) + EXPECT[target])
        expected[cell] = saved_in_target(saved, target)
    return rows, expected


def run(rows):
    with tempfile.TemporaryDirectory(prefix='v27-parser-') as directory:
        source = Path(directory) / 'parser_test.cpp'
        source.write_text(program(rows))
        binary = Path(directory) / 'parser_test'
        built = subprocess.run(['g++', '-std=c++17', '-Wall', str(source), '-o', str(binary)],
                               capture_output=True, text=True, timeout=60)
        if built.returncode:
            raise AssertionError(built.stderr)
        out = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10, check=True).stdout
    parsed = {}
    for line in out.splitlines():
        name, list_tag, block_tag, blocks, items, multi, ok, satisfied = line.split('\t')
        parsed[name] = {'listTag': list_tag, 'blockTag': block_tag, 'blockCount': int(blocks),
                        'itemCount': int(items), 'multiBlock': multi == '1', 'parsed': ok == '1',
                        'satisfied': satisfied == '1'}
    return parsed


def problems(parsed, expected):
    found = []
    for cell, want in expected.items():
        got = parsed.get(cell)
        if got is None:
            found.append(f'{cell}: no output')
            continue
        if not got['parsed']:
            found.append(f'{cell}: not parsed')
        if got['satisfied'] != want:
            found.append(f'{cell}: predicate {got["satisfied"]} but the saved paragraph says {want}')
        for key, value in zip(('listTag', 'blockTag', 'blockCount', 'itemCount', 'multiBlock'), PINNED.get(cell, ())):
            if value is not None and got[key] != value:
                found.append(f'{cell}: {key} {got[key]!r} != pinned {value!r}')
        if cell not in ('a1-text-mid', 'g-a1-text-mid') and not got['multiBlock']:
            found.append(f'{cell}: expected a multi-block read')
    return found


class ProductionParserOnRecordedMarkup(unittest.TestCase):
    def test_parser_agrees_with_the_saved_documents(self):
        rows, expected = rows_and_expectations()
        self.assertEqual(len(rows), 18)
        parsed = run(rows)
        self.assertEqual(problems(parsed, expected), [])
        # Red first: one mutated expectation, and one mutated pin, must each be reported.
        flipped = dict(expected, **{'n2-sham-empty-before-list': not expected['n2-sham-empty-before-list']})
        self.assertTrue(problems(parsed, flipped))
        PINNED['r6-bullet-empty-before-list'] = ('ul', 'p', None, 1, True)
        try:
            self.assertTrue(problems(parsed, expected))
        finally:
            PINNED['r6-bullet-empty-before-list'] = ('ul', 'p', None, 2, True)


if __name__ == '__main__':
    unittest.main()
