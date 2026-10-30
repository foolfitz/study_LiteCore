"""SPEC-M3-v28-last-line-fallback 7.2 E1/E2: the one-position-back fallback on production source.

Native g++ against the fake LOK of ordered_format_test.cpp, with test_ordered_format_v27.py's preamble and these
additions: `.uno:CharLeftSel` sets its own selection type and markup, a `gOrderedProof` stand-in, and the REAL
`parseFormatReadback` (with its helpers) and `formatBarrierFallbackReadbackSatisfied` cut from
src/probe_engine.cpp -- not faked, so that a mutation of the real predicate can turn a case red (review item 3).
The original must be green; "v27 behaviour" (the inc with its v28 blocks stripped, compiled WITH the v28 define)
and every mutation must turn it red.

Run from wasm_sdk_probe/:  python3 -m unittest tests/test_ordered_format_v28.py
Witness before the inc edit:  python3 tests/test_ordered_format_v28.py --witness
"""
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('v27', SDK / 'tests/test_ordered_format_v27.py')
v27 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v27)

V28 = '#ifdef OXSDK_E2_V28_LAST_BLOCK'
DEFINES = v27.DEFINES + ['-DOXSDK_E2_V28_LAST_BLOCK']
FAKE_PARSE = ('FormatReadback parseFormatReadback(const std::string&) {\n'
              ' FormatReadback r; r.parsed=true; r.blockTag=firstBlockTag; r.blockCount=multiBlock ? 2 : 1;'
              ' r.multiBlock=multiBlock; return r;\n}\n')
REAL = [r'bool formatTagIsStructural\(', r'bool formatTagIsBlock\(', r'bool formatDivIsFootnoteApparatus\(',
        r'FormatReadback parseFormatReadback\(']


def cut(engine, signature):
    match = re.search(r'^' + signature + r'.*?\n\}\n', engine, re.S | re.M)
    if not match:
        raise AssertionError(f'{signature} not found in probe_engine.cpp')
    return match.group()


def fixtures(engine=None):
    engine = engine if engine is not None else (SDK / 'src/probe_engine.cpp').read_text()
    types, preamble = v27.fixtures()
    for before, after in [
        ('int selectedType=1, currentType=0, htmlReads=0;',
         'int selectedType=1, currentType=0, htmlReads=0;\n'
         'int fallbackType=1, fallbackHtmlReads=0; std::string fallbackHtml;\n'
         'bool fallbackSelected=false, deliverFallback=true;\n'
         'struct FakeUnoProof { bool seen=false; std::string payload; };\n'
         'struct { std::map<std::string,FakeUnoProof> uno; } gOrderedProof;\n'
         'const char *kFormatBarrierFallbackCommand=".uno:CharLeftSel";'),
        (' calls.push_back(name);\n if (!listener) std::abort();\n',
         ' calls.push_back(name);\n if (!listener) std::abort();\n'
         ' if (std::string(name)==".uno:CharLeftSel") {\n'
         '  currentType=fallbackType; inSelect=true; fallbackSelected=true;\n'
         '  if (deliverFallback) gOrderedProof.uno[name].seen=true;\n'
         '  return;\n }\n'),
        ('char *html(Doc*,const char*,void*) { ++htmlReads; return strdup("<p>text</p>"); }',
         'char *html(Doc*,const char*,void*) {\n'
         ' ++htmlReads;\n'
         ' if (fallbackSelected) { ++fallbackHtmlReads; return strdup(fallbackHtml.c_str()); }\n'
         # the real parser needs <body>; v27's fake parser never read the markup
         ' return strdup("<html><body><p>text</p></body></html>");\n}'),
        (' if(type==LOK_SETTEXTSELECTION_RESET) currentType=0;',
         ' if(type==LOK_SETTEXTSELECTION_RESET) { currentType=0; fallbackSelected=false; }'),
        (FAKE_PARSE, '\n'.join(cut(engine, s) for s in REAL)
         + cut(engine, r'bool formatBarrierFallbackReadbackSatisfied\(')),
    ]:
        if preamble.count(before) != 1:
            raise AssertionError(f'preamble anchor moved: {before[:60]}')
        preamble = preamble.replace(before, after)
    return types, preamble


def strip_v28(source):
    """The inc as v27 compiled it: every v28 block removed (v28 blocks have no #else and no nesting)."""
    out, inside = [], False
    for line in source.splitlines(keepends=True):
        bare = line.rstrip('\n')
        if not inside:
            if bare == V28:
                inside = True
            else:
                out.append(line)
        elif line.startswith('#if') or bare == '#else':
            raise AssertionError('a nested conditional or #else inside a v28 block')
        elif bare == '#endif':
            inside = False
    if inside:
        raise AssertionError('an unterminated v28 block')
    return ''.join(out)


def run_inc(inc_text, engine=None):
    types, preamble = fixtures(engine)
    with tempfile.TemporaryDirectory(prefix='v28-format-') as directory:
        work = Path(directory)
        (work / 'format_types.inc').write_text(types)
        (work / 'preamble.inc').write_text(preamble)
        (work / 'ordered_format.inc').write_text(inc_text)
        return v27.compile_and_run(work, SDK / 'tests/ordered_format_v28_test.cpp', DEFINES)


# (label, file, before, after): each must occur exactly once and must turn the test red.
MUTATIONS = [
    ('fallback-branch-disabled', 'inc', 'if (gFormatBarrier.fallbackRan &&\n'
     '      gFormatBarrier.fallbackSelectionType != LOK_SELTYPE_NONE) {', 'if (false) {'),
    ('no-block-count', 'inc', 'gFormatBarrier.fallbackReadback.blockCount != 2', 'false'),
    ('restore-judged-after-structure', 'inc', '// v28: the restore before the structural refusals\n'
     '    if (!gFormatBarrier.restoreConfirmed) {', '// mutated\n    if (false) {'),
    ('html-regardless-of-type', 'inc', 'stepBack.type == LOK_SELTYPE_TEXT', 'true'),
    ('fallback-any-primary-type', 'inc', 'selected.type == LOK_SELTYPE_NONE &&', 'true &&'),
    ('fallback-any-route', 'inc', 'barrier.route == FormatBarrierRoute::Collapsed &&\n        selected',
     'true &&\n        selected'),
    ('fallback-ignores-restore-point', 'inc', '&& barrier.restorePointValid) {', ') {'),
    ('predicate-reads-first-block', 'engine',
     'readback.lastListTag.empty() ? std::string("none") : readback.lastListTag',
     'readback.listTag.empty() ? std::string("none") : readback.listTag'),
]


class OrderedFormatV28(unittest.TestCase):
    def test_083_last_line_fallback(self):
        source = (SDK / 'src/ordered_format.inc').read_text()
        engine = (SDK / 'src/probe_engine.cpp').read_text()
        stripped = strip_v28(source)
        self.assertNotEqual(stripped, source, 'v27-behaviour strips nothing')
        variants = [('original', source, engine), ('v27-behaviour', stripped, engine)]
        for label, where, before, after in MUTATIONS:
            text = source if where == 'inc' else engine
            self.assertEqual(text.count(before), 1, label)
            mutated = text.replace(before, after)
            variants.append((label, mutated, engine) if where == 'inc' else (label, source, mutated))
        for label, inc, eng in variants:
            with self.subTest(label=label):
                code, output = run_inc(inc, eng)
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
