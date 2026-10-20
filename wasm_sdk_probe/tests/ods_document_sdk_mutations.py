#!/usr/bin/env python3
"""The red cases of tests/ods-document-sdk.test.mjs against viewer-shell/ods-document-sdk.js (CLAUDE.md §6).

The test runs against a scratch copy of viewer-shell/ (VIEWER_SHELL_DIR; sdk/ and reader-shell/ beside
it are links to the real, unmodified ones): first as it is (the control, every test passes), then once
per mutation of the SDK's source text, each of which must turn the named test red.  Each edit must
match exactly once.

  part-echoes-request     setPart records the part asked for          -> read-back test fails
  names-synthesised       partNames are made up, not asked for        -> names test fails
  part-switch-ungated     the queries are added on any profile        -> plain-handle test fails
  part-text-ungated       partText is added without part-text         -> partText test fails
  type-defaulted          a missing documentType becomes spreadsheet  -> no-documentType test fails
  part-not-validated      setPart sends whatever it is given          -> refusal test fails

Usage: python3 -I tests/ods_document_sdk_mutations.py
Exit 0 only when the control passes and every mutation is red as required.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
SDK = 'ods-document-sdk.js'
TEST = HERE / 'tests' / 'ods-document-sdk.test.mjs'

MUTATIONS = {
    'part-echoes-request': (
        '      handle.currentPart = result.part;\n', '      handle.currentPart = part;\n',
        'setPart: the handle follows the engine'),
    'names-synthesised': (
        '      names.push((await request("partName", { part })).name);\n', '      names.push(String(part));\n',
        "viewer profile: the handle carries the engine's type"),
    'part-switch-ungated': (
        '    if (declares(this.manifest, PART_SWITCH_CAPABILITY))\n', '    if (true)\n',
        'a profile without part-switch gets the plain handle'),
    'part-text-ungated': (
        '    if (declares(this.manifest, PART_TEXT_CAPABILITY))\n', '    if (true)\n',
        'partText exists only with part-text'),
    'type-defaulted': (
        '    if (typeof reply.documentType === "string")\n      handle.documentType = reply.documentType;\n',
        '    handle.documentType = reply.documentType || "spreadsheet";\n',
        'an open reply without documentType'),
    'part-not-validated': (
        '      requirePart(part, "setPart");\n', '',
        'a part that is not a non-negative integer is refused'),
}


def run(shell_dir: pathlib.Path):
    env = dict(os.environ, VIEWER_SHELL_DIR=str(shell_dir))
    done = subprocess.run(['node', '--test', '--test-reporter=tap', str(TEST)],
                          capture_output=True, text=True, env=env, timeout=120)
    failed = re.findall(r'^not ok \d+ - (.*)$', done.stdout, re.M)
    counts = {k: int(m.group(1)) for k in ('tests', 'pass', 'fail')
              for m in [re.search(rf'^# {k} (\d+)$', done.stdout, re.M)] if m}
    return done.returncode, counts, failed


def main():
    source = (HERE / 'viewer-shell' / SDK).read_text()
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        shell = root / 'viewer-shell'
        shutil.copytree(HERE / 'viewer-shell', shell)
        for linked in ('sdk', 'reader-shell'):
            os.symlink(HERE / linked, root / linked)
        rc, counts, failed = run(shell)
        print(f'control: exit {rc} {counts}')
        ok &= rc == 0 and counts.get('fail') == 0 and counts.get('tests', 0) > 0
        for name, (old, new, expect) in MUTATIONS.items():
            if source.count(old) != 1:
                print(f'{name}: the edit matches {source.count(old)} times (must be 1)')
                ok = False
                continue
            (shell / SDK).write_text(source.replace(old, new))
            rc, counts, failed = run(shell)
            hit = rc != 0 and any(expect in f for f in failed)
            print(f'{name}: {"red as required" if hit else "NOT RED AS REQUIRED"}: failed {failed}')
            ok &= hit
        (shell / SDK).write_text(source)
    print('ALL RED AS REQUIRED' if ok else 'MUTATION CHECK FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
