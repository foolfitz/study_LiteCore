#!/usr/bin/env python3
"""Read the bounded v23 browser protocol. Missing observations are NE, never green.

Not a reader for all SPEC-M3-ordered-commands 9.2. Actual artifacts are mandatory.
"""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

PROFILE = 'e2-editor-v23-diag'
FILES = ('sdk-manifest.json', 'probe.wasm', 'probe.js', 'sdk-worker.js')
ARMS = ('smoke', 'proof', 'hang', 'js-thread')
PASS, FAIL, NE = 'PASS', 'FAIL', 'NOT_ESTABLISHED'


def identity(directory, expected_wasm):
    directory = Path(directory)
    manifest = json.loads((directory / FILES[0]).read_text())
    hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in FILES}
    if manifest.get('profile') != PROFILE:
        raise ValueError('wrong profile: ABI5 is not evidence of v23')
    if hashes['probe.wasm'] != expected_wasm:
        raise ValueError('actual WASM differs from explicit candidate SHA256')
    if manifest.get('editorContract', {}).get('abiVersion') != 5:
        raise ValueError('diagnostic contract must remain ABI5')
    return hashes


def details(record, kind):
    return [(e['generation'], e['message']['detail']) for e in record.get('events', [])
            if e.get('message', {}).get('event') == 'diagnostic'
            and e['message'].get('detail', {}).get('type') == kind]


def judge(record, expected):
    missing, failed = [], []
    def need(ok, message):
        if not ok: missing.append(message)
    def check(ok, message):
        if not ok: failed.append(message)
    need(record.get('complete') is True and not record.get('fatal'), 'incomplete/unclean browser arm')
    check(record.get('profile') == PROFILE and record.get('manifest', {}).get('profile') == PROFILE,
          'wrong profile (v22/ABI-only evidence rejected)')
    check(record.get('artifacts') == expected, 'served artifact hashes differ from actual candidate')
    arm = record.get('arm')
    need(arm in ARMS, 'unknown arm')
    requests = record.get('requests', [])
    opens = [r for r in requests if r.get('operation') == 'open']
    need(bool(opens), 'no actual open request')
    responses = {(r['generation'], r['message'].get('requestId')): r['message']
                 for r in record.get('responses', [])}
    for op in opens:
        key = (op['generation'], op['requestId'])
        need(responses.get(key, {}).get('ok') is True, f'open lacks successful response {key}')
        states = [responses.get((r['generation'], r['requestId']), {}).get('result', {})
                  for r in requests if r.get('operation') == 'editorGetStateV2'
                  and r['generation'] == op['generation'] and r['requestId'] > op['requestId']]
        need(bool(states), f'open lacks actual state read {key}')
        if states:
            check(states[0].get('a11y', {}).get('unavailable') == 'core-built-without-accessibility',
                  f'actual a11y status wrong after open {key}')
    polls = details(record, 'v23-poll')
    need(bool(polls), 'no actual poll instrumentation')
    seen = set()
    for gen, p in polls:
        key = (gen, p.get('poll'))
        check(key not in seen, f'duplicate poll {key}'); seen.add(key)
        need(all(k in p for k in ('poll', 'queued', 'drained', 'replyPending', 'reply', 'requestId')),
             'incomplete poll payload')
        check(p.get('drained') in (0, 1), 'more than one command drained')
        check(not (p.get('reply') and p.get('drained')), 'reply and command in same poll')
        check(not (p.get('replyPending') and p.get('drained')), 'reply priority violated')
    proofs = details(record, 'v23-proof-absent')
    if arm != 'proof': check(not proofs, 'ordinary path has missing proof')
    if arm == 'smoke':
        need(any(p.get('queued', 0) >= 2 for _, p in polls), 'no queue-depth >=2 positive witness')
        for name in ('open', 'type', 'move', 'save', 'queue-pair'):
            matches = [s for s in record.get('steps', []) if s.get('name') == name]
            need(len(matches) == 1, f'missing/nonunique {name}')
            if matches: check(matches[0].get('ok') is True, f'{name} failed')
        try:
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(record['savedBase64'], validate=True))) as z:
                root = ET.fromstring(z.read('content.xml'))
                check('V23_DIAGNOSTIC_TOKEN' in ''.join(root.itertext()), 'saved content lacks typed token')
        except (KeyError, ValueError, zipfile.BadZipFile, ET.ParseError):
            need(False, 'no readable actual saved ODT')
    elif arm in ARMS:
        kind = {'proof': 2, 'hang': 1, 'js-thread': 3}[arm]
        controls = [r for r in requests if r.get('operation') == 'v23Diagnostic']
        need(len(controls) == 1 and controls[0].get('payload', {}).get('kind') == kind,
             'no unique actual private control request')
        entries = details(record, 'v23-control')
        need(len(entries) == 1, 'private control entry not observed')
        if controls and entries:
            check(entries[0] == (controls[0]['generation'], {'type': 'v23-control', 'kind': kind,
                  'requestId': controls[0]['requestId']}), 'private entry/request mismatch')
        control = record.get('control', {})
        if kind == 2:
            need(len(proofs) == 1, 'missing-proof positive control must produce exactly one event')
            if proofs and controls:
                check(proofs[0][0] == controls[0]['generation'] and
                      proofs[0][1].get('requestId') == controls[0]['requestId'] and
                      proofs[0][1].get('count') == 1 and
                      proofs[0][1].get('callback') == 'UNO_COMMAND_RESULT', 'proof event attribution/count wrong')
            check(control.get('error', {}).get('code') == 'MUTATION_OUTCOME_UNKNOWN' and
                  control.get('error', {}).get('details', {}).get('failureShape') ==
                  'proof-absent-at-poll:UNO_COMMAND_RESULT', 'typed proof rejection missing')
        else:
            check(control.get('error', {}).get('code') == 'TIMEOUT', 'private hang did not reach SDK timeout')
            check(control.get('error', {}).get('details', {}).get('timeoutMs') == 30000,
                  'SDK default 30-second timeout not used')
            check(control.get('stateAfter', {}).get('state') == 'recoverable-error', 'session did not enter recovery')
            check(record.get('recoveredState', {}).get('state') == 'ready', 'session restart did not recover')
            workers = record.get('workers', [])
            need(len(workers) == 2, 'restart lacks fresh worker witness')
            if len(workers) == 2:
                check(workers[0].get('terminatedAt') is not None and
                      workers[0]['terminatedAt'] <= workers[1]['createdAt'], 'stuck worker not terminated before replacement')
            need(any(s.get('name') == 'recovery-save' and s.get('ok') for s in record.get('steps', [])),
                 'no post-recovery save')
    return {'verdict': NE if missing else FAIL if failed else PASS,
            'missing': missing, 'failed': failed, 'scope': 'bounded diagnostic only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--profile-dir', type=Path, required=True)
    parser.add_argument('--wasm-sha256', required=True)
    args = parser.parse_args()
    expected = identity(args.profile_dir, args.wasm_sha256)
    report = json.loads(args.report.read_text())
    results = [dict(browser=r.get('browser'), round=r.get('round'), arm=r.get('arm'),
                    **judge(r.get('page', {}), expected)) for r in report.get('runs', [])]
    population = [(b, n, a) for b in ('chrome', 'firefox') for n in range(1, 4) for a in ARMS]
    actual = [(r['browser'], r['round'], r['arm']) for r in results]
    complete = sorted(actual) == sorted(population)
    verdict = NE if not complete or any(r['verdict'] == NE for r in results) else (
        FAIL if any(r['verdict'] == FAIL for r in results) else PASS)
    print(json.dumps({'verdict': verdict, 'populationComplete': complete, 'results': results,
          'notClosed': ['W-D', 'S-init', '040-W frame/destroy', 'large fixtures/64KiB/long60',
                        'idle layout/tile timing', 'feature gates', 'host/K']}, indent=2))
    return 0 if verdict == PASS else 1


if __name__ == '__main__':
    raise SystemExit(main())
