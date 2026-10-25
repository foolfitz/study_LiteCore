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
import sys
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROFILE = 'e2-editor-v23-diag'
R2_PROFILE = 'e2-editor-v23-diag-r2'
PROFILES = (PROFILE, R2_PROFILE)
R2_HASHES = {
 'probe.wasm':'683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078',
 'sdk-manifest.json':'716620972050c5d55485cb99564102cfe0e749af81457180f7f7a265701709da',
 'sdk-worker.js':'c8a3de873c3fbd61b20cc3404eb582433f0c8b1db2e52be374671c3b8851de50',
 'probe.js':'f0c77adde7313ece193f16b3a97ea6d539492d282ad787b4f2cdb260c7229fd3',
}
FILES = ('sdk-manifest.json', 'probe.wasm', 'probe.js', 'sdk-worker.js')
ARMS = ('smoke', 'proof', 'hang', 'js-thread')
PASS, FAIL, NE = 'PASS', 'FAIL', 'NOT_ESTABLISHED'


def identity(directory, expected_wasm, profile=PROFILE):
    directory = Path(directory)
    manifest = json.loads((directory / FILES[0]).read_text())
    hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in FILES}
    if profile not in PROFILES or manifest.get('profile') != profile:
        raise ValueError('wrong profile: ABI5 is not evidence of v23')
    if hashes['probe.wasm'] != expected_wasm:
        raise ValueError('actual WASM differs from explicit candidate SHA256')
    if manifest.get('editorContract', {}).get('abiVersion') != 5:
        raise ValueError('diagnostic contract must remain ABI5')
    if profile == R2_PROFILE and hashes != R2_HASHES:
        raise ValueError('r2 artifact bytes differ from the owner-linked frozen identity')
    return hashes


def details(record, kind):
    return [(e['generation'], e['message']['detail']) for e in record.get('events', [])
            if e.get('message', {}).get('event') == 'diagnostic'
            and e['message'].get('detail', {}).get('type') == kind]


def judge(record, expected, profile=PROFILE):
    missing, failed = [], []
    def need(ok, message):
        if not ok: missing.append(message)
    def check(ok, message):
        if not ok: failed.append(message)
    need(record.get('complete') is True and not record.get('fatal'), 'incomplete/unclean browser arm')
    check(profile in PROFILES and record.get('profile') == profile and record.get('manifest', {}).get('profile') == profile,
          'wrong profile (v22/ABI-only evidence rejected)')
    check(record.get('artifacts') == expected, 'served artifact hashes differ from actual candidate')
    arm = record.get('arm')
    need(arm in ARMS, 'unknown arm')
    check(not (profile == R2_PROFILE and arm == 'js-thread'), 'r2 generic plain-NONE js-thread cannot count; cite corrected040')
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
        if profile == R2_PROFILE and controls:
            owner=controls[0]; terminal=responses.get((owner['generation'],owner['requestId']))
            if kind == 2:
                check(terminal is not None and terminal.get('ok') is False and
                      terminal.get('error',{}).get('code')=='MUTATION_OUTCOME_UNKNOWN' and
                      terminal.get('error',{}).get('failureShape')=='proof-absent-at-poll:UNO_COMMAND_RESULT',
                      'r2 proof rejection lacks actual typed wire response')
            else:
                check(terminal is None, 'r2 hang has a terminal wire response')
                cancels=record.get('cancels',[])
                need(len(cancels)==1, 'r2 hang lacks unique actual SDK cancellation')
                if len(cancels)==1:
                    check(cancels[0].get('kind')=='cancel' and cancels[0].get('generation')==owner['generation']
                          and cancels[0].get('requestId')==owner['requestId'], 'r2 cancellation attribution mismatch')
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


def corrected_references(paths, expected):
    """Rejudge six actual corrected040 negatives; references never create new runs."""
    import judge_v23_remaining as remaining
    import v23_remaining_cases as cases
    references=[]
    _, population=cases.fixtures()
    for path in paths:
        path=Path(path).resolve();report=json.loads(path.read_text())
        if report.get('profile')!=R2_PROFILE or report.get('identity')!=expected:
            raise ValueError('corrected040 reference is not bound to actual r2 identity')
        cases.verify_bindings(report,path.parent/'mirror')
        if report.get('population')!=population:raise ValueError('corrected040 input population drift')
        for name,digest in report['fixtures'].items():
            if cases.sha(path.parent/'mirror'/f'{name}.odt')!=digest:raise ValueError('corrected040 fixture drift')
        report_sha=hashlib.sha256(path.read_bytes()).hexdigest()
        for index,run in enumerate(report.get('runs',[])):
            page=run.get('page') or {}
            if run.get('arm')!='html-negative' or page.get('arm')!='html-negative':
                raise ValueError('only corrected frame-html-js observations may replace r2 logical js-thread obligations')
            verdict=remaining.judge(page,expected,report['fixtures'],R2_PROFILE)
            references.append(dict(browser=run.get('browser'),round=run.get('round'),arm='js-thread',
                source={'path':str(path),'sha256':report_sha,'runIndex':index,
                        'pageSha256':hashlib.sha256(json.dumps(page,sort_keys=True).encode()).hexdigest(),
                        'caseId':'frame-html-js'}, **verdict))
    return references


def summarize(results, references, profile):
    problems=[]
    if profile==R2_PROFILE:
        if any(r.get('arm')=='js-thread' for r in results):problems.append('generic r2 js-thread cell cannot count')
        keys=[(r.get('browser'),r.get('round')) for r in references]
        wanted={(b,n) for b in ('chrome','firefox') for n in range(1,4)}
        if len(keys)!=6 or set(keys)!=wanted:problems.append('missing/extra/duplicate corrected040 references')
        ids=[(r.get('source',{}).get('sha256'),r.get('source',{}).get('runIndex')) for r in references]
        pages=[r.get('source',{}).get('pageSha256') for r in references]
        if len(ids)!=len(set(ids)) or len(pages)!=len(set(pages)) or any(x is None for x in pages):
            problems.append('duplicate or unidentified corrected040 observation')
    elif references:problems.append('original identity does not use corrected r2 references')
    cells=results+references
    population={(b,n,a) for b in ('chrome','firefox') for n in range(1,4) for a in ARMS}
    actual=[(r.get('browser'),r.get('round'),r.get('arm')) for r in cells]
    complete=len(actual)==24 and len(set(actual))==24 and set(actual)==population and not problems
    verdict=NE if not complete or any(r['verdict']==NE for r in cells) else FAIL if any(r['verdict']==FAIL for r in cells) else PASS
    return {'verdict':verdict,'populationComplete':complete,'problems':problems,
            'directCells':len(results),'referencedCells':len(references),'results':cells,
            'scope':'24 logical bounded obligations; six r2 negatives reuse uniquely identified corrected040 observations',
            'notClosed':['W-D','S-init','040-W frame/destroy/engine-HTML','large fixtures/64KiB/long60',
                         'idle layout/tile timing','feature gates','host/K']}


def main():
    from v23_diagnostic_instruments import verify_bindings
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--profile',choices=PROFILES,default=PROFILE)
    parser.add_argument('--profile-dir',type=Path,required=True)
    parser.add_argument('--wasm-sha256',required=True)
    parser.add_argument('--corrected-040-report',type=Path,action='append',default=[])
    args=parser.parse_args();expected=identity(args.profile_dir,args.wasm_sha256,args.profile)
    report=json.loads(args.report.read_text())
    if report.get('profile')!=args.profile or report.get('identity')!=expected:raise ValueError('report candidate identity mismatch')
    verify_bindings(report,args.report.parent/'mirror')
    fixture=hashlib.sha256((args.report.parent/'mirror/fixture.odt').read_bytes()).hexdigest()
    if report.get('fixtureSha256')!=fixture:raise ValueError('actual fixture identity mismatch')
    results=[]
    for run in report.get('runs',[]):
        page=run.get('page') or {}
        if page.get('fixtureSha256')!=fixture:raise ValueError('browser fixture identity mismatch')
        if run.get('arm')!=page.get('arm'):raise ValueError('run/page arm mismatch')
        results.append(dict(browser=run.get('browser'),round=run.get('round'),arm=run.get('arm'),
                            **judge(page,expected,args.profile)))
    references=corrected_references(args.corrected_040_report,expected)
    result=summarize(results,references,args.profile)
    print(json.dumps(result,indent=2));return 0 if result['verdict']==PASS else 1

if __name__=='__main__':raise SystemExit(main())
