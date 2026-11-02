"""SPEC-P-demo-batch-3 E1: the PRODUCTION parser, predicates and block scan, compiled with the v31 define, on the markup N1 recorded.

`parseFormatReadback`, its helpers and the two predicates are cut from src/probe_engine.cpp (not re-written); `extractBlocks` and
`everyBlockHasAlign` come from src/format_readback_text.hpp.  The rows are tool-closed: every arm of
findings/evidence/demo-batch-3/native-writer-align/observations.jsonl.  Each row is judged twice: the align the command set must
satisfy, and a different one must not, so a predicate that ignores the attribute is red.  The saved ODT is the arm's truth.

Run from wasm_sdk_probe/:  python3 -I tests/test_format_readback_v31.py
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

SDK = Path(__file__).resolve().parents[1]
N1 = SDK.parent / 'findings/evidence/demo-batch-3/native-writer-align'
N2 = SDK.parent / 'findings/evidence/demo-batch-3/native-writer-align-caret'
DEFINES = ['-DOXSDK_E2_V25_FORMAT_PROOF', '-DOXSDK_E2_V27_FIRST_BLOCK', '-DOXSDK_E2_V28_LAST_BLOCK',
           '-DOXSDK_E2_V23_FEATURE_ABI6', '-DOXSDK_E2_V31_ALIGNMENT']
ALIGN = {'.uno:LeftPara': 'left', '.uno:CenterPara': 'center', '.uno:RightPara': 'right', '.uno:JustifyPara': 'justify'}
FO = '{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}text-align'
STYLE = '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v27 = load('format_readback_v27', SDK / 'tests/test_format_readback_v27.py')


def literal(text):
    return json.dumps(text)


def program(rows):
    engine = (SDK / 'src/probe_engine.cpp').read_text()
    types = '\n'.join(v27.cut(engine, r'^(?:struct|enum class) ' + name + r' \{.*?\n\};', name)
                      for name in ['EditorRect', 'FormatBarrierTarget', 'FormatBarrierStage', 'FormatReadback',
                                   'FormatBarrierRoute', 'FormatStateBarrier'])
    functions = '\n'.join(v27.cut(engine, r'^' + signature + r'.*?\n\}\n', signature) for signature in [
        r'bool formatTagIsStructural\(', r'bool formatTagIsBlock\(', r'bool formatDivIsFootnoteApparatus\(',
        r'FormatReadback parseFormatReadback\(', r'bool formatBarrierReadbackSatisfied\(',
        r'bool formatBarrierFallbackReadbackSatisfied\(', r'bool formatBarrierAlignCaretReadSatisfied\('])
    cases = ',\n'.join('  {%s, %s, %s, %s, %s}' % (literal(r['name']), literal(r['html']), literal(r['align']), literal(r['other']), literal(r['route']))
                       for r in rows)
    return ('#include <chrono>\n#include <cstdint>\n#include <cstdio>\n#include <cstring>\n#include <string>\n#include <vector>\n'
            '#include "format_readback_text.hpp"\nusing namespace probe;\n'
            'constexpr int LOK_SELTYPE_NONE=0, LOK_SELTYPE_TEXT=1;\n'
            + types + '\nFormatStateBarrier gFormatBarrier;\n' + functions +
            '\nstruct Case { const char *name, *html, *align, *other, *route; };\n'
            'static bool judge(const Case &c, const char *align) {\n'
            '  gFormatBarrier = FormatStateBarrier{};\n'
            '  gFormatBarrier.selectionTypeReadable = true; gFormatBarrier.fallbackReadable = true;\n'
            '  gFormatBarrier.expectedAlign = align;\n'
            '  gFormatBarrier.readback = parseFormatReadback(c.html);\n'
            '  gFormatBarrier.fallbackReadback = gFormatBarrier.readback;\n'
            '  if (!std::strcmp(c.route, "cross")) return everyBlockHasAlign(extractBlocks(c.html), align);\n'
            '  if (!std::strcmp(c.route, "fallback")) return formatBarrierFallbackReadbackSatisfied();\n'
            '  if (!std::strcmp(c.route, "caret-back")) return formatBarrierAlignCaretReadSatisfied();\n'
            '  if (!std::strcmp(c.route, "caret-forward")) { gFormatBarrier.alignReadBack = false; return formatBarrierAlignCaretReadSatisfied(); }\n'
            '  return formatBarrierReadbackSatisfied();\n'
            '}\n'
            'int main() {\n const Case cases[] = {\n' + cases + '\n };\n'
            ' for (const Case &c : cases) {\n'
            '  const bool wanted = judge(c, c.align), other = judge(c, c.other);\n'
            '  std::printf("%s\\t%d\\t%d\\t%s\\n", c.name, wanted ? 1 : 0, other ? 1 : 0, gFormatBarrier.readback.blockAlign.c_str());\n'
            ' }\n return 0;\n}\n')


def compile_and_run(rows, defines=DEFINES):
    with tempfile.TemporaryDirectory(prefix='v31-parser-') as directory:
        source = Path(directory) / 'parser_test.cpp'
        source.write_text(program(rows))
        binary = Path(directory) / 'parser_test'
        built = subprocess.run(['g++', '-std=c++17', '-Wall', f'-I{SDK / "src"}', *defines, str(source), '-o', str(binary)],
                               capture_output=True, text=True, timeout=60)
        if built.returncode:
            raise AssertionError(built.stderr)
        out = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10, check=True).stdout
    return {line.split('\t')[0]: line.split('\t') for line in out.splitlines()}


def rows():
    out = []
    observations = [json.loads(line) for line in (N1 / 'observations.jsonl').read_text().splitlines()]
    for index, row in enumerate(observations):
        align = ALIGN[row['command']]
        other = 'right' if align != 'right' else 'center'
        route = 'cross' if row['arm'] == 'range-cross' else 'first'
        html = row['html']
        if row['selectionAtRead'] == 0:
            html, route = row['fallbackHtml'], 'fallback'
        out.append({'name': f"{index}-{row['arm']}-{align}", 'html': html, 'align': align, 'other': other, 'route': route, 'saved': row['saved']})
    # N2: the caret read the engine does.  Every `sel` arm that read anything; a blank document reads nothing.
    for index, line in enumerate((N2 / 'observations.jsonl').read_text().splitlines()):
        row = json.loads(line)
        if row['route'] != 'sel' or row['how'] == 'blank':
            continue
        align = ALIGN[row['command']]
        other = 'right' if align != 'right' else 'center'
        out.append({'name': f"n2-{index}-{row['place']}-{align}", 'html': row['html'], 'align': align, 'other': other,
                    'route': 'caret-back' if row['how'] == 'left' else 'caret-forward', 'saved': row['saved']})
    return out


class Alignment(unittest.TestCase):
    def test_population(self):
        population = rows()
        self.assertEqual(len(population), 32 + 33)
        self.assertEqual({r['route'] for r in population}, {'first', 'cross', 'fallback', 'caret-back', 'caret-forward'})

    def test_every_recorded_arm(self):
        population = rows()
        parsed = compile_and_run(population)
        self.assertEqual(len(parsed), len(population))
        for row in population:
            name, wanted, other, _ = (parsed[row['name']] + [''])[:4]
            self.assertEqual((wanted, other), ('1', '0'), f"{row['name']} route {row['route']}")

    def test_style_attribute_is_not_the_align_attribute(self):
        row = {'name': 'style-only', 'html': '<html><body><p style="text-align: center">x</p></body></html>', 'align': 'center',
               'other': 'right', 'route': 'first', 'saved': ''}
        self.assertEqual(compile_and_run([row])['style-only'][1], '0')

    def test_a_forward_read_judges_the_first_block(self):
        # An empty first paragraph: the step forward crosses the break, and the caret's paragraph is the first block.
        html = '<html><body><p align="center"><br/></p><p>next</p></body></html>'
        row = {'name': 'forward', 'html': html, 'align': 'center', 'other': 'right', 'route': 'caret-forward', 'saved': ''}
        self.assertEqual(compile_and_run([row])['forward'][1], '1')

    def test_a_cross_range_with_one_block_behind_is_refused(self):
        html = '<html><body><p align="center">a</p><p>b</p></body></html>'
        row = {'name': 'cross-short', 'html': html, 'align': 'center', 'other': 'right', 'route': 'cross', 'saved': ''}
        self.assertEqual(compile_and_run([row])['cross-short'][1], '0')


if __name__ == '__main__':
    raise SystemExit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
