#!/usr/bin/env python3
"""Read W-D against saved native Writer-order landings and actual wire records."""
import argparse
import base64
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v23_wd_cases import ROOT, NATIVE, BASE, PLANS, FIXTURES, PRIVATE, LOCATOR, P, D, instrument_files
from judge_v23_diagnostic import PROFILE, identity, details
from read_results import shape, read_cell, run_log, landing


def odt_shape(encoded):
    """Feed actual saved ODT XML to the SAME shape reader as the native run."""
    raw = base64.b64decode(encoded, validate=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = ET.Element('{urn:oasis:names:tc:opendocument:xmlns:office:1.0}document')
        for member in ('styles.xml', 'content.xml'):
            for child in ET.fromstring(archive.read(member)):
                root.append(copy.deepcopy(child))
    with tempfile.TemporaryDirectory(prefix='v23-wd-shape-') as directory:
        path = Path(directory) / 'saved.fodt.gz'
        path.write_bytes(gzip.compress(ET.tostring(root)))
        return shape(path)


def reference(case):
    if case.startswith('d7'):
        return None
    if case == 'merge':
        out = NATIVE.parent / 'restore-v2/delete/out-01'
        arm, mode = 'delete-plain-direct', 'unipoll'
    else:
        out, arm, mode = NATIVE / 'out', case, 'seq'
    log = run_log(out)
    values = []
    for n in range(1, 6):
        cell = read_cell(out / arm, mode, n, log)
        if cell['problems']:
            raise ValueError(f'unclean native reference {case}/{n}: {cell["problems"]}')
        values.append(landing(cell))
    if any(value != values[0] for value in values):
        raise ValueError(f'unstable native reference {case}')
    return json.loads(values[0])


def wire_actor(request):
    operation, payload = request.get('operation'), request.get('payload', {})
    if operation == 'editorActionV2':
        if payload.get('extendSelection') is not False:
            return ('invalid-public-extend', payload.get('action'))
        if payload.get('enabled') is not (payload.get('action') == 'set-bold'):
            return ('invalid-public-option', payload.get('action'))
        return (P, payload.get('action'))
    if operation == 'v23Diagnostic':
        return (D, PRIVATE.get(payload.get('kind'), 'unknown-private-input'))
    if operation == 'insertText':
        return (P, 'insert-x' if payload.get('text') == 'x' else 'wrong-insert')
    if operation == 'editorPlaceCaretV2':
        return (P, 'place-recorded-caret')
    return None


def judge(page, case, expected, oracle):
    missing, failed = [], []
    need = lambda ok, message: None if ok else missing.append(message)
    check = lambda ok, message: None if ok else failed.append(message)
    need(page.get('complete') is True and not page.get('fatal'), 'unclean/incomplete W-D page')
    check(page.get('profile') == PROFILE and page.get('manifest', {}).get('profile') == PROFILE,
          'profile is not the diagnostic candidate')
    check(page.get('artifacts') == expected, 'served bytes do not bind actual candidate')
    source = NATIVE / 'fixtures' / (FIXTURES[case] + '.fodt')
    check(page.get('fixtureSha256') == hashlib.sha256(source.read_bytes()).hexdigest(),
          'fixture bytes differ from the original native input')
    wd = page.get('wd') or {}
    need(wd.get('caseId') == case and wd.get('fixture') == FIXTURES[case], 'missing/mismatched W-D case')
    plan = PLANS[case] + LOCATOR
    labels = [(item.get('route'), item.get('name')) for item in wd.get('sequence', [])
              if item.get('route') in (P, D)]
    check(labels == plan, 'page input/provenance sequence differs from native protocol')
    actors = [(request, wire_actor(request)) for request in page.get('requests', [])]
    observers = {'init', 'open', 'save', 'editorGetStateV2', 'getSelection'}
    check(all(actor is not None or request.get('operation') in observers for request, actor in actors),
          'unplanned worker operation outside the exact-input/observer protocol')
    actors = [(request, actor) for request, actor in actors if actor is not None]
    check([actor for _, actor in actors] == plan, 'actual worker requests differ from declared route sequence')
    responses = {(x['generation'], x['message'].get('requestId')): x for x in page.get('responses', [])}
    labeled = [item for item in wd.get('sequence', []) if item.get('route') in (P, D)]
    for i, (request, _) in enumerate(actors):
        response = responses.get((request['generation'], request['requestId']))
        need(response is not None, 'wire input lacks terminal response')
        if response:
            check(response['message'].get('ok') is True, 'required W-D input was refused')
            check(i < len(labeled) and labeled[i].get('result') == response['message'].get('result'),
                  'page result witness differs from the actual worker response')
    if case in BASE and len(actors) == len(plan):
        burst = actors[-5:-2]  # final native trigger + two ops, before L's two keys
        first = responses.get((burst[0][0]['generation'], burst[0][0]['requestId']))
        need(first is not None and all(item[0]['at'] < first['at'] for item in burst),
             'native three-input burst was serialized at the caller')
    check(not details(page, 'v23-proof-absent'), 'ordinary W-D path lacks proof')
    check(wd.get('before', {}).get('a11y', {}).get('unavailable') == 'core-built-without-accessibility',
          'open state does not report the actual headless a11y limit')
    try:
        saved = odt_shape(wd['savedBase64'])
        if oracle is not None:
            check({'shape': saved, 'caret': wd.get('locator')} == oracle,
                  'saved shape or native L landing differs from Writer order')
        else:
            check(saved == odt_shape(wd['unchangedBeforeBase64']), 'D7 NONE path mutated the document')
            outcome = wd.get('deleteResult', {})
            check(outcome.get('completion') == 'verified-boundary-noop' and outcome.get('changed') is False
                  and outcome.get('revision') == wd.get('revisionBeforeDelete'), 'D7 limitation response is not immediate noop')
    except (KeyError, ValueError, zipfile.BadZipFile, ET.ParseError):
        need(False, 'missing/unreadable actual saved document')
    if case in ('d2', 'd2p'):
        deletes = [x for x in wd.get('sequence', []) if x.get('name') in ('delete-forward', 'delete-backward')]
        check(len(deletes) == 1 and deletes[0].get('result', {}).get('completion') == 'verified-selection-delete',
              'caret unit delete did not use the measured C barrier shape')
    if case == 'merge':
        check(wd.get('deleteResult', {}).get('completion') == 'verified-key-undo', 'merge lacks key undo proof')
    if case == 'd4':
        formats = [x for x in wd.get('sequence', []) if x.get('name') == 'set-bold']
        check(len(formats) == 1 and formats[0].get('result', {}).get('state', {}).get('format', {}).get('bold') is True,
              'd4 lacks its positive Bold-state witness')
    if case == 'd6':
        places = [r for r, actor in actors if actor == (P, 'place-recorded-caret')]
        third_right = responses.get((actors[2][0]['generation'], actors[2][0]['requestId'])) if len(actors) >= 4 else None
        first_left = actors[3][0] if len(actors) >= 4 else None
        states = [r for r in page.get('requests', []) if r.get('operation') == 'editorGetStateV2'
                  and places and third_right and first_left
                  and r['generation'] == places[0]['generation']
                  and third_right['at'] <= r['at'] <= first_left['at']]
        need(len(places) == 1 and bool(states), 'no actual pre-click point read')
        if len(places) == 1 and states:
            last = max(states, key=lambda r: (r['at'], r['requestId']))
            point_reply = responses.get((last['generation'], last['requestId']), {}).get('message', {})
            point = point_reply.get('result', {}).get('caret') or {}
            need(point_reply.get('ok') is True and all(type(point.get(k)) is int for k in ('x', 'y', 'height')),
                 'no actual recorded caret rectangle')
            need(responses.get((last['generation'], last['requestId']), {}).get('at', float('inf')) <= first_left['at'],
                 'point read completed after the caret had already moved left')
            if all(type(point.get(k)) is int for k in ('x', 'y', 'height')):
                check(places[0]['payload'].get('xTwips') == point['x']
                      and places[0]['payload'].get('yTwips') == point['y'] + point['height'] // 2,
                      'click payload differs from the actual recorded point')
    return {'verdict': 'NOT_ESTABLISHED' if missing else 'FAIL' if failed else 'PASS',
            'missing': missing, 'failures': failed}


def read(reports, directory, pin):
    expected = identity(directory, pin)
    cells, duplicates = {}, []
    for path in reports:
        report = json.loads(Path(path).read_text())
        if report.get('identity') != expected:
            raise ValueError('report identity differs from actual candidate')
        instruments = {str(p.relative_to(ROOT / 'wasm_sdk_probe')): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in instrument_files()}
        if report.get('wdInstrumentSha256') != instruments:
            raise ValueError('W-D instrument source identity changed or absent')
        mirror = Path(path).resolve().parent / 'mirror/v23-diagnostic-wd.js'
        copied = hashlib.sha256(mirror.read_bytes()).hexdigest()
        if copied != report.get('wdMirrorSha256') or copied != instruments['web/v23-diagnostic-wd.js']:
            raise ValueError('executed copied W-D module differs from recorded source')
        for run in report.get('runs', []):
            page = run.get('page') or {}
            case = page.get('wd', {}).get('caseId')
            key = (run.get('browser'), run.get('round'), case)
            if key in cells: duplicates.append(key)
            cells[key] = page
    wanted = {(b, r, c) for b in ('chrome', 'firefox') for r in range(1, 6) for c in PLANS}
    if duplicates or set(cells) != wanted:
        return {'verdict': 'NOT_ESTABLISHED', 'reason': 'missing/extra/duplicate W-D cells',
                'duplicates': duplicates, 'cells': len(cells), 'expected': len(wanted)}
    judged = {str(key): judge(page, key[2], expected, reference(key[2])) for key, page in cells.items()}
    verdicts = [item['verdict'] for item in judged.values()]
    return {'verdict': 'NOT_ESTABLISHED' if 'NOT_ESTABLISHED' in verdicts else 'FAIL' if 'FAIL' in verdicts else 'PASS',
            'cells': judged, 'identity': expected,
            'scope': 'W-D topology with explicit private inputs; public ABI6 gestures remain untested'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reports', type=Path, nargs='+'); p.add_argument('--profile-dir', type=Path, required=True)
    p.add_argument('--wasm-sha256', required=True); a = p.parse_args()
    result = read(a.reports, a.profile_dir, a.wasm_sha256)
    print(json.dumps(result, indent=2)); raise SystemExit(0 if result['verdict'] == 'PASS' else 1)
