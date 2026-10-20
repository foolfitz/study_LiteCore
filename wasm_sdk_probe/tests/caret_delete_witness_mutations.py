#!/usr/bin/env python3
"""The red cases of tests/caret_delete_witness_test.cpp against the decider itself (CLAUDE.md §6: a
green test only proves it can print green).

The test's own R1-R4 are variants written inside the test, so they show the RULES are needed; they cannot
show that the test notices when src/caret_delete_witness.hpp itself loses one.  This script builds the test
against a scratch copy of src/ holding the header as it is (the control, which must pass) and then once per
mutation of the header's SOURCE TEXT (each of which must fail, and must fail in the named check).  Each edit
must match exactly once, so a refactor that moves the line makes this script fail loudly instead of
mutating nothing (the markdown_paste_mutations.py pattern).

  paragraph-branch-removed   contentDiffers() always false          -> W fails (grouped cells mislabelled)
  guard-removed              caretStrictlyInside() only asks `ok`    -> R2 fails
  a11y-guard-removed         judgeBeforeKey() ignores accessibility  -> R3 fails
  after-read-as-noop         a failed after-read reads as no effect  -> R4 fails
and one on the input:
  fixture-empty              the fixture without its op lines        -> the non-vacuity count fails

Usage (from anywhere): python3 -I tests/caret_delete_witness_mutations.py [--cxx g++]
Exit 0 only when the control passes and every mutation is red as required.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
HEADER = 'caret_delete_witness.hpp'
TEST = HERE / 'tests' / 'caret_delete_witness_test.cpp'
FIXTURE = HERE / 'tests' / 'caret_delete_witness_fixture.tsv'

MUTATIONS = {
    'paragraph-branch-removed': (
        '  return a.length != b.length || a.listPrefixLength != b.listPrefixLength ||\n'
        '         a.fingerprint != b.fingerprint;\n',
        '  (void)a; (void)b;\n  return false;\n',
        'FAIL W '),
    'guard-removed': (
        '  return key == Key::Backspace ? before.position >= 1\n'
        '                               : before.position < before.length;\n',
        '  (void)key;\n  return true;\n',
        'FAIL R2 '),
    'a11y-guard-removed': (
        '  if (!accessibilityAvailable)\n    return "a11y-unavailable";\n',
        '  (void)accessibilityAvailable;\n',
        'FAIL R3 '),
    'after-read-as-noop': (
        '    if (!after.ok) {\n      out.stage = "paragraph-read-after";\n',
        '    if (!after.ok) {\n      out.verdict = Verdict::BoundaryNoop;\n      return out;\n'
        '      out.stage = "paragraph-read-after";\n',
        'FAIL R4 '),
}


def build_and_run(cxx, src, fixture, work, name):
    binary = work / f'test-{name}'
    build = subprocess.run([cxx, '-std=c++17', '-O1', '-I', str(src), '-o', str(binary), str(TEST)],
                           capture_output=True, text=True)
    if build.returncode != 0:
        return None, build.stderr
    run = subprocess.run([str(binary), str(fixture)], capture_output=True, text=True)
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

        rc, out = build_and_run(a.cxx, src, FIXTURE, work, 'control')
        print(f'control: exit {rc}: {out.strip().splitlines()[-1] if out.strip() else ""}')
        ok &= rc == 0

        for name, (old, new, expect) in MUTATIONS.items():
            if header.count(old) != 1:
                print(f'{name}: the edit matches {header.count(old)} times (must be 1)')
                ok = False
                continue
            (src / HEADER).write_text(header.replace(old, new))
            rc, out = build_and_run(a.cxx, src, FIXTURE, work, name)
            hit = rc not in (0, None) and expect in out
            first = next((x for x in out.splitlines() if x.startswith('FAIL')), out.strip()[:200])
            print(f'{name}: exit {rc}, {"red as required" if hit else "NOT RED AS REQUIRED"}: {first}')
            ok &= hit
        (src / HEADER).write_text(header)

        empty = work / 'empty.tsv'
        empty.write_text(''.join(x for x in FIXTURE.read_text().splitlines(True) if x.startswith('#')))
        rc, out = build_and_run(a.cxx, src, empty, work, 'fixture-empty')
        hit = rc not in (0, None) and 'fixture has 0 ops' in out
        print(f'fixture-empty: exit {rc}, {"red as required" if hit else "NOT RED AS REQUIRED"}')
        ok &= hit
    print('ALL RED AS REQUIRED' if ok else 'MUTATION CHECK FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
