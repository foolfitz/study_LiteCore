"""Synthetic controls use actual saved native documents; no WASM claim."""
import base64
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import judge_v23_wd as wd
import v23_diagnostic_instruments as instruments
from v23_wd_cases import NATIVE, PLANS, FIXTURES, PRIVATE, LOCATOR, P, D


def packaged(xml):
    """Synthetic ODT carrier for the actual native saved XML shape."""
    source = ET.fromstring(xml)
    ns = 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
    content = ET.Element('{' + ns + '}document-content')
    styles = ET.Element('{' + ns + '}document-styles')
    for child in source:
        (content if child.tag in ('{' + ns + '}body', '{' + ns + '}automatic-styles') else styles).append(copy.deepcopy(child))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('mimetype', 'application/vnd.oasis.opendocument.text')
        archive.writestr('content.xml', ET.tostring(content))
        archive.writestr('styles.xml', ET.tostring(styles))
    return base64.b64encode(buffer.getvalue()).decode()


def synthetic(case):
    oracle = wd.reference(case)
    if case == 'merge':
        saved = gzip.decompress((NATIVE.parent / 'restore-v2/delete/out-01/delete-plain-direct/unipoll-r1.fodt.gz').read_bytes())
    elif case.startswith('d7'):
        saved = (NATIVE / 'fixtures' / (FIXTURES[case] + '.fodt')).read_bytes()
    else:
        saved = gzip.decompress((NATIVE / 'out' / case / 'seq-r1.fodt.gz').read_bytes())
    encoded = packaged(saved)
    expected = {'probe.wasm': 'a' * 64, 'probe.js': 'b' * 64,
                'sdk-worker.js': 'c' * 64, 'sdk-manifest.json': 'd' * 64}
    page = {'complete': True, 'profile': wd.PROFILE, 'manifest': {'profile': wd.PROFILE},
            'arm': 'wd', 'artifacts': expected, 'fixtureSha256': hashlib.sha256((NATIVE / 'fixtures' / (FIXTURES[case] + '.fodt')).read_bytes()).hexdigest(),
            'events': [], 'requests': [], 'responses': []}
    result = {'caseId': case, 'fixture': FIXTURES[case], 'savedBase64': encoded,
              'before': {'a11y': {'unavailable': 'core-built-without-accessibility'}},
              'locator': oracle['caret'] if oracle else ['', ''], 'sequence': []}
    for i, (route, name) in enumerate(PLANS[case] + LOCATOR):
        value = {}
        if name.startswith('delete-'):
            value = {'completion': 'verified-selection-delete'}
        if name == 'set-bold': value = {'state': {'format': {'bold': True}}}
        result['sequence'].append({'route': route, 'name': name, 'result': value})
        if route == D:
            operation, payload = 'v23Diagnostic', {'kind': next(k for k, v in PRIVATE.items() if v == name)}
        elif name == 'insert-x': operation, payload = 'insertText', {'text': 'x'}
        elif name == 'place-recorded-caret': operation, payload = 'editorPlaceCaretV2', {'xTwips': 1, 'yTwips': 2}
        else: operation, payload = 'editorActionV2', {'action': name, 'extendSelection': False, 'enabled': name == 'set-bold'}
        start = len(PLANS[case]) - 3
        at = start * 20 + i - start if case in wd.BASE and start <= i < len(PLANS[case]) else i * 20
        page['requests'].append({'generation': 1, 'requestId': i + 10, 'operation': operation, 'payload': payload, 'at': at})
        page['responses'].append({'generation': 1, 'at': at + 10, 'message': {'requestId': i + 10, 'ok': True, 'result': value}})
    if case == 'merge': result['deleteResult'] = {'completion': 'verified-key-undo'}
    if case.startswith('d7'):
        result.update(unchangedBeforeBase64=encoded, revisionBeforeDelete=0,
                      deleteResult={'completion': 'verified-boundary-noop', 'changed': False, 'revision': 0})
    if case == 'merge' or case.startswith('d7'):
        index = next(i for i, item in enumerate(result['sequence']) if item['name'].startswith('delete-'))
        result['sequence'][index]['result'] = result['deleteResult']
        page['responses'][index]['message']['result'] = result['deleteResult']
    if case == 'd6':
        page['requests'].append({'generation': 1, 'requestId': 90, 'operation': 'editorGetStateV2', 'at': 51})
        page['responses'].append({'generation': 1, 'at': 52, 'message': {'requestId': 90, 'ok': True,
                                  'result': {'caret': {'x': 1, 'y': 0, 'height': 4}}}})
    page['wd'] = result
    return page, expected, oracle


class WdReader(unittest.TestCase):
    def test_every_registered_case_on_actual_native_shape(self):
        self.assertEqual(len(PLANS), 12)
        for case in PLANS:
            with self.subTest(case=case):
                page, expected, oracle = synthetic(case)
                self.assertEqual(wd.judge(page, case, expected, oracle)['verdict'], 'PASS')

    def test_actual_js_fixture_population(self):
        script = SDK / 'web/v23-diagnostic-wd.js'
        code = ('const m=await import("data:text/javascript;base64,' + base64.b64encode(script.read_bytes()).decode()
                + '");process.stdout.write(JSON.stringify(m.WD_FIXTURES));')
        result = subprocess.run(['node', '--input-type=module', '-e', code], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), {case: FIXTURES[case] for case in PLANS})

    def test_causal_rejections(self):
        for mutation in ('wrong-profile', 'wrong-bytes', 'wrong-fixture', 'wrong-save', 'wrong-locator',
                         'dropped-input', 'private-code', 'serialized-burst', 'missing-proof', 'unavailable-response'):
            with self.subTest(mutation=mutation):
                page, expected, oracle = synthetic('d2')
                if mutation == 'wrong-profile': page['profile'] = 'e2-editor-v22'
                elif mutation == 'wrong-bytes': page['artifacts'] = {}
                elif mutation == 'wrong-fixture': page['fixtureSha256'] = '0' * 64
                elif mutation == 'wrong-save': page['wd']['savedBase64'] = synthetic('d3')[0]['wd']['savedBase64']
                elif mutation == 'wrong-locator': page['wd']['locator'] = ['', '']
                elif mutation == 'dropped-input': page['requests'].pop(0)
                elif mutation == 'private-code': page['requests'][-1]['payload']['kind'] = 9
                elif mutation == 'serialized-burst': page['requests'][-3]['at'] = 1000
                elif mutation == 'missing-proof': page['events'] = [{'generation': 1, 'message': {'event': 'diagnostic', 'detail': {'type': 'v23-proof-absent'}}}]
                else: page['responses'].pop(0)
                self.assertNotEqual(wd.judge(page, 'd2', expected, oracle)['verdict'], 'PASS')

    def test_d4_requires_positive_format_state(self):
        page, expected, oracle = synthetic('d4')
        next(item for item in page['wd']['sequence'] if item['name'] == 'set-bold')['result'] = {}
        self.assertEqual(wd.judge(page, 'd4', expected, oracle)['verdict'], 'FAIL')

    def test_d7_limitation_is_not_silent_mutation(self):
        page, expected, oracle = synthetic('d7plain')
        page['wd']['deleteResult']['changed'] = True
        self.assertEqual(wd.judge(page, 'd7plain', expected, oracle)['verdict'], 'FAIL')

    def test_r2_is_explicit_and_original_default_stays_strict(self):
        page,expected,oracle=synthetic('d1');page['profile']=page['manifest']['profile']='e2-editor-v23-diag-r2'
        self.assertEqual(wd.judge(page,'d1',expected,oracle,'e2-editor-v23-diag-r2')['verdict'],'PASS')
        self.assertEqual(wd.judge(page,'d1',expected,oracle)['verdict'],'FAIL')
        page['profile']=page['manifest']['profile']='e2-editor-v22'
        self.assertEqual(wd.judge(page,'d1',expected,oracle,'e2-editor-v23-diag-r2')['verdict'],'FAIL')

    def test_actual_wire_provenance_controls(self):
        for mutation in ('bold-disabled', 'false-wire-bold', 'wrong-click', 'extra-click'):
            with self.subTest(mutation=mutation):
                case = 'd6' if mutation == 'wrong-click' else 'd4'
                page, expected, oracle = synthetic(case)
                if mutation == 'bold-disabled': page['requests'][2]['payload']['enabled'] = False
                elif mutation == 'false-wire-bold':
                    page['responses'][2]['message']['result'] = {'state': {'format': {'bold': False}}}
                elif mutation == 'wrong-click':
                    next(r for r in page['requests'] if r['operation'] == 'editorPlaceCaretV2')['payload'].update(xTwips=999999, yTwips=999999)
                else:
                    page['requests'].append({'generation': 1, 'requestId': 99, 'at': 50, 'operation': 'click', 'payload': {}})
                self.assertNotEqual(wd.judge(page, case, expected, oracle)['verdict'], 'PASS')

    def test_complete_population_and_copied_instrument(self):
        seeds = {case: synthetic(case) for case in PLANS}
        expected = seeds['d1'][1]
        report = {'profile': wd.PROFILE, 'identity': expected, 'runs': [
            {'browser': browser, 'round': n, 'page': copy.deepcopy(seeds[case][0])}
            for browser in ('chrome', 'firefox') for n in range(1, 6) for case in PLANS]}
        report['wdInstrumentSha256'] = {str(p.relative_to(SDK)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in wd.instrument_files()}
        report['instrument']={str(p.relative_to(SDK)):instruments.sha(p) for p in instruments.instrument_files()}
        report['mirrorInstrument']=instruments.served_instruments()
        for row in report['runs']:
            row['page']['instrumentServed']={k:report['mirrorInstrument'][k] for k in ('e2-editor.html','v23-diagnostic.js','v23-diagnostic-wd.js')}
        copied = (SDK / 'web/v23-diagnostic-wd.js').read_bytes()
        report['wdMirrorSha256'] = hashlib.sha256(copied).hexdigest()
        with tempfile.TemporaryDirectory(prefix='v23-wd-report-') as directory:
            path = Path(directory) / 'report.json'
            mirror = Path(directory) / 'mirror/v23-diagnostic-wd.js'
            mirror.parent.mkdir(); mirror.write_bytes(copied)
            for name in report['mirrorInstrument']:
                source=SDK/({'e2-editor.html':'web/v23-diagnostic.html','v23-diagnostic.js':'web/v23-diagnostic.js','v23-diagnostic-wd.js':'web/v23-diagnostic-wd.js'}.get(name,name))
                target=mirror.parent/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
            # Artifact identity itself has separate tests. This stub isolates
            # population/instrument enforcement without fabricating a WASM.
            with patch.object(wd, 'identity', return_value=expected):
                path.write_text(json.dumps(report))
                self.assertEqual(wd.read([path], Path(directory), 'unused')['verdict'], 'PASS')
                for rows in ([], report['runs'][:-1], report['runs'] + [report['runs'][0]]):
                    altered = {**report, 'runs': rows}; path.write_text(json.dumps(altered))
                    self.assertEqual(wd.read([path], Path(directory), 'unused')['verdict'], 'NOT_ESTABLISHED')
                path.write_text(json.dumps(report)); mirror.write_text('// wrong executed instrument')
                with self.assertRaises(ValueError): wd.read([path], Path(directory), 'unused')
                mirror.write_bytes(copied)
                for name in ('e2-editor.html','v23-diagnostic.js','sdk/document-sdk.js'):
                    target=mirror.parent/name;raw=target.read_bytes();target.write_bytes(raw+b' changed')
                    with self.assertRaises(ValueError):wd.read([path],Path(directory),'unused')
                    target.write_bytes(raw)


if __name__ == '__main__':
    unittest.main()
