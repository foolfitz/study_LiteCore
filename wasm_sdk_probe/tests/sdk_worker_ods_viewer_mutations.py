#!/usr/bin/env python3
"""The red cases of sdk/tests/sdk-worker-ods-viewer.test.mjs against sdk/sdk-worker.js (CLAUDE.md §6).

The test runs against a scratch copy of the worker (ODS_VIEWER_WORKER): first as it is (the control,
every test passes), then once per mutation of the worker's source text, each of which must turn the
named test red.  Each edit must match exactly once.

  capability-not-gated         setPart has no capability entry          -> editor-profile refusal fails
  part-text-on-part-switch     partText rides on part-switch            -> per-capability gate fails
  non-integer-part-passed      a non-integer part reaches the engine    -> non-integer refusal fails
  reply-forwarded-whole        part-text forwards the event as it is    -> named-fields test fails
  open-type-dropped            the open reply loses documentType        -> open-reply test fails
  open-type-always-present     an editor's open reply gains the key     -> exact-keys test fails
  wrong-export                 partName calls part_text's export        -> own-export test fails

Usage: python3 -I tests/sdk_worker_ods_viewer_mutations.py
Exit 0 only when the control passes and every mutation is red as required.
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
WORKER = HERE / 'sdk' / 'sdk-worker.js'
TEST = HERE / 'sdk' / 'tests' / 'sdk-worker-ods-viewer.test.mjs'

MUTATIONS = {
    'capability-not-gated': (
        '  ["setPart", "part-switch"],\n', '',
        'on an editor profile every viewer operation is refused'),
    'part-text-on-part-switch': (
        '  ["partText", "part-text"],\n', '  ["partText", "part-switch"],\n',
        'part-switch does not open partText'),
    'non-integer-part-passed': (
        'accept(request, () => (Number.isInteger(payload.part) ? callStatus(',
        'accept(request, () => (true ? callStatus(',
        'a part that is not an integer is refused before the engine'),
    # 2026-10-21 (SPEC-M4-viewer-v2 3.3): the literal gained v2's three wait fields, so the anchor is
    # its first four lines, replaced by `{ ...event,` so the rest still parses and the event goes
    # through whole.  Witness of the drift:
    # findings/evidence/m4-ods/viewer-v2/pre-link/sdk-worker-mutations-red-anchor-drift.txt.
    'reply-forwarded-whole': (
        '        complete(requestId, { part: event.part, text: event.text, textNull: event.textNull,\n'
        '                              selectAllConfirmed: event.selectAllConfirmed,\n'
        '                              partBefore: event.partBefore, partAfter: event.partAfter,\n'
        '                              revision: event.revision,\n',
        '        complete(requestId, { ...event,\n',
        'the four replies pass through with named fields only'),
    'open-type-dropped': (
        '    ...(typeof event.documentType === "string" ? { documentType: event.documentType } : {}),\n', '',
        'the open reply carries documentType and inputSuffix'),
    'open-type-always-present': (
        '    ...(typeof event.documentType === "string" ? { documentType: event.documentType } : {}),\n',
        '    documentType: event.documentType,\n',
        "an editor engine's open reply keeps exactly the keys it had"),
    'wrong-export': (
        'partName: "oxsdk_document_part_name"', 'partName: "oxsdk_document_part_text"',
        'each operation calls its own export'),
}


def run(worker: pathlib.Path):
    env = dict(os.environ, ODS_VIEWER_WORKER=str(worker))
    done = subprocess.run(['node', '--test', '--test-reporter=tap', str(TEST)],
                          capture_output=True, text=True, env=env, timeout=120)
    failed = re.findall(r'^not ok \d+ - (.*)$', done.stdout, re.M)
    counts = {k: int(m.group(1)) for k in ('tests', 'pass', 'fail')
              for m in [re.search(rf'^# {k} (\d+)$', done.stdout, re.M)] if m}
    return done.returncode, counts, failed


def main():
    source = WORKER.read_text()
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        copy = pathlib.Path(tmp) / 'sdk-worker.js'
        copy.write_text(source)
        rc, counts, failed = run(copy)
        control_ok = rc == 0 and counts.get('fail') == 0 and counts.get('tests', 0) > 0
        print(f'control: exit {rc} {counts}')
        ok &= control_ok
        for name, (old, new, expect) in MUTATIONS.items():
            if source.count(old) != 1:
                print(f'{name}: the edit matches {source.count(old)} times (must be 1)')
                ok = False
                continue
            copy.write_text(source.replace(old, new))
            rc, counts, failed = run(copy)
            hit = rc != 0 and any(expect in f for f in failed)
            print(f'{name}: {"red as required" if hit else "NOT RED AS REQUIRED"}: failed {failed}')
            ok &= hit
    print('ALL RED AS REQUIRED' if ok else 'MUTATION CHECK FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
