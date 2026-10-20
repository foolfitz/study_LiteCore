#!/usr/bin/env python3
"""The red cases of tests/ods_viewer_test.cpp against src/ods_viewer.hpp itself (CLAUDE.md §6).

The test is built against a scratch copy of src/ holding the header as it is (the control, which must
pass) and then once per mutation of the header's SOURCE TEXT, each of which must fail in the named
check.  Each edit must match exactly once.

  case-sensitive          the suffix is compared as written              -> S1 fails
  odt-only                .ods is not accepted                           -> S1 fails
  no-stem-required        ".ods" alone is accepted                       -> S1 fails
  types-shifted           spreadsheet is spelled as text                 -> T1 fails
  range-off-by-one        part == parts is in range                      -> R1 fails
  queried-before-range    the current part is asked before the range     -> X1 fails
  always-switch           a switch is made to the part already current   -> X3 fails
  reset-only-on-success   a timed-out SelectAll is left selected         -> X4 fails
  not-restored            the part is not switched back                  -> X2 fails
  part-after-assumed      partAfter is the part asked for, not read      -> X6 fails
  empty-sheet-is-an-error an empty sheet's null text becomes an error    -> X5 fails
  empty-sheet-not-flagged the empty text is not flagged                  -> X5 fails

Usage: python3 -I tests/ods_viewer_mutations.py [--cxx g++]
Exit 0 only when the control passes and every mutation is red as required.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
HEADER = 'ods_viewer.hpp'
TEST = HERE / 'tests' / 'ods_viewer_test.cpp'
LO_INCLUDE = HERE.parent / 'libreoffice-26-8' / 'include'

MUTATIONS = {
    'case-sensitive': (
        '  for (char &c : tail)\n    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));\n',
        '',
        'FAIL S1 BOOK.ODS'),
    'odt-only': (
        '  if (tail == ".odt" || tail == ".ods")\n',
        '  if (tail == ".odt")\n',
        'FAIL S1 book.ods'),
    'no-stem-required': (
        '  if (name.size() < 5)',
        '  if (name.size() < 4)',
        'FAIL S1 a name that is only the suffix'),
    'types-shifted': (
        '  case 1:\n    return "spreadsheet";\n',
        '  case 1:\n    return "text";\n',
        'FAIL T1 spreadsheet'),
    'range-off-by-one': (
        '  return part >= 0 && part < parts;\n',
        '  return part >= 0 && part <= parts;\n',
        'FAIL R1 parts itself'),
    'queried-before-range': (
        '  PartTextResult result;\n  if (!partInRange(part, document.parts())) {\n',
        '  PartTextResult result;\n  result.partBefore = document.part();\n'
        '  if (!partInRange(part, document.parts())) {\n',
        'FAIL X1 nothing but parts()'),
    'always-switch': (
        '  if (part != result.partBefore)\n    document.setPart(part);\n',
        '  document.setPart(part);\n',
        'FAIL X3 no switch'),
    'reset-only-on-success': (
        '  document.resetSelection();\n',
        '  if (result.status == PartTextStatus::Ok)\n    document.resetSelection();\n',
        'FAIL X4 deselected anyway'),
    'not-restored': (
        '  if (document.part() != result.partBefore)\n    document.setPart(result.partBefore);\n',
        '',
        'FAIL X2 the order'),
    'empty-sheet-is-an-error': (
        '  } else if (!document.text(result.text)) {\n    result.text.clear();\n    result.textNull = true;\n  }\n',
        '  } else if (!document.text(result.text)) {\n    result.status = PartTextStatus::SelectAllTimedOut;\n  }\n',
        'FAIL X5 an empty sheet is not an error'),
    'empty-sheet-not-flagged': (
        '    result.textNull = true;\n', '',
        'FAIL X5 the empty text, flagged'),
    'part-after-assumed': (
        '  result.partAfter = document.part();\n',
        '  result.partAfter = result.partBefore;\n',
        'FAIL X6'),
}


def build_and_run(cxx, src, work, name):
    binary = work / f'test-{name}'
    build = subprocess.run([cxx, '-std=c++17', '-O1', '-I', str(src), '-I', str(LO_INCLUDE),
                            '-o', str(binary), str(TEST)], capture_output=True, text=True)
    if build.returncode != 0:
        return None, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    return run.returncode, run.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cxx', default='g++')
    a = ap.parse_args()
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        src = work / 'src'
        shutil.copytree(HERE / 'src', src)
        header = (src / HEADER).read_text()
        rc, out = build_and_run(a.cxx, src, work, 'control')
        print(f'control: exit {rc}: {out.strip().splitlines()[-1] if out.strip() else ""}')
        ok &= rc == 0
        for name, (old, new, expect) in MUTATIONS.items():
            if header.count(old) != 1:
                print(f'{name}: the edit matches {header.count(old)} times (must be 1)')
                ok = False
                continue
            (src / HEADER).write_text(header.replace(old, new))
            rc, out = build_and_run(a.cxx, src, work, name)
            hit = rc not in (0, None) and expect in out
            first = next((x for x in out.splitlines() if x.startswith('FAIL')), out.strip()[:200])
            print(f'{name}: exit {rc}, {"red as required" if hit else "NOT RED AS REQUIRED"}: {first}')
            ok &= hit
        (src / HEADER).write_text(header)
    print('ALL RED AS REQUIRED' if ok else 'MUTATION CHECK FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
