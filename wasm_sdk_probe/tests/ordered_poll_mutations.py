#!/usr/bin/env python3
"""The red cases of tests/ordered_poll_test.cpp against src/ordered_poll.hpp itself (CLAUDE.md §6).

The test's own red variants (the old drain, command-first, the old anyInput) show the RULES are needed;
this shows the test notices when the header loses one.  The test is built against a scratch copy of src/
holding the header as it is (the control, which must pass) and then once per mutation of the header's
SOURCE TEXT (each of which must fail in the named check).  Each edit must match exactly once.

  drain-until-empty      the DispatchOne step loops while anything is queued   -> P1 fails
  anyinput-queue-only    anyInput() ignores a pending reply                    -> P2 fails
  command-first          choose() dispatches before a pending reply            -> P3 fails
  guard-not-reset        the re-entrancy flag is not cleared on an exception   -> P6 fails

Usage: python3 -I tests/ordered_poll_mutations.py [--cxx g++]
Exit 0 only when the control passes and every mutation is red as required.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
HEADER = 'ordered_poll.hpp'
TEST = HERE / 'tests' / 'ordered_poll_test.cpp'

MUTATIONS = {
    'drain-until-empty': (
        '  case Step::DispatchOne:\n    engine.dispatchOne();\n',
        '  case Step::DispatchOne:\n    while (engine.pollInputs().queued > 0)\n      engine.dispatchOne();\n',
        'FAIL P1 '),
    'anyinput-queue-only': (
        '  return in.queued > 0 || in.replyPending;\n',
        '  return in.queued > 0;\n',
        'FAIL P2 '),
    'command-first': (
        '  if (in.replyPending)\n    return Step::SendReply;\n  if (in.queued > 0)\n    return Step::DispatchOne;\n',
        '  if (in.queued > 0)\n    return Step::DispatchOne;\n  if (in.replyPending)\n    return Step::SendReply;\n',
        'FAIL P3 '),
    'guard-not-reset': (
        '    ~Reset() { flag = false; }\n',
        '    ~Reset() { (void)flag; }\n',
        'FAIL P6'),
}


def build_and_run(cxx, src, work, name):
    binary = work / f'test-{name}'
    build = subprocess.run([cxx, '-std=c++17', '-O1', '-I', str(src), '-o', str(binary), str(TEST)],
                           capture_output=True, text=True)
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
