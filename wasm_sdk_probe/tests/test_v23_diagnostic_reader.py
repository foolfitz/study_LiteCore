#!/usr/bin/env python3
"""Synthetic reader controls only. None constitutes WASM/browser evidence."""
import base64
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

path = Path(__file__).resolve().parents[1] / 'tools/judge_v23_diagnostic.py'
spec = importlib.util.spec_from_file_location('reader', path)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
EXPECTED = {name: 'a' * 64 for name in r.FILES}


def sample(arm='smoke'):
    def request(i, op, gen=1, payload=None):
        return {'generation': gen, 'requestId': i, 'operation': op, 'payload': payload or {}}
    def response(i, data, gen=1):
        return {'generation': gen, 'message': {'requestId': i, 'ok': True, 'result': data}}
    def event(data, gen=1):
        return {'generation': gen, 'message': {'event': 'diagnostic', 'detail': data}}
    data = {'complete': True, 'profile': r.PROFILE, 'manifest': {'profile': r.PROFILE},
        'artifacts': EXPECTED.copy(), 'arm': arm,
        'requests': [request(2, 'open'), request(3, 'editorGetStateV2')],
        'responses': [response(2, {}), response(3, {'a11y': {'unavailable': 'core-built-without-accessibility'}})],
        'events': [event({'type': 'v23-poll', 'poll': 1, 'queued': 2, 'drained': 1,
            'replyPending': False, 'reply': False, 'requestId': 3})],
        'steps': [{'name': n, 'ok': True} for n in ('open', 'type', 'move', 'save', 'queue-pair')],
        'workers': [{'createdAt': 0, 'terminatedAt': 30002}, {'createdAt': 30003, 'terminatedAt': 31000}]}
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w') as z:
        z.writestr('content.xml', '<doc>V23_DIAGNOSTIC_TOKEN</doc>')
    data['savedBase64'] = base64.b64encode(raw.getvalue()).decode()
    if arm != 'smoke':
        kind = {'proof': 2, 'hang': 1, 'js-thread': 3}[arm]
        data['requests'].append(request(4, 'v23Diagnostic', payload={'kind': kind}))
        data['events'].append(event({'type': 'v23-control', 'kind': kind, 'requestId': 4}))
        if kind == 2:
            data['events'].append(event({'type': 'v23-proof-absent', 'requestId': 4,
                'count': 1, 'callback': 'UNO_COMMAND_RESULT'}))
            data['control'] = {'error': {'code': 'MUTATION_OUTCOME_UNKNOWN',
                'details': {'failureShape': 'proof-absent-at-poll:UNO_COMMAND_RESULT'}}}
        else:
            data['control'] = {'error': {'code': 'TIMEOUT', 'details': {'timeoutMs': 30000}},
                               'stateAfter': {'state': 'recoverable-error'}}
            data['recoveredState'] = {'state': 'ready'}
            data['steps'].append({'name': 'recovery-save', 'ok': True})
            data['requests'] += [request(2, 'open', 2), request(3, 'editorGetStateV2', 2)]
            data['responses'] += [response(2, {}, 2), response(3,
                {'a11y': {'unavailable': 'core-built-without-accessibility'}}, 2)]
    return data


class ReaderControls(unittest.TestCase):
    def verdict(self, data): return r.judge(data, EXPECTED)['verdict']

    def test_synthetic_positives(self):
        for arm in r.ARMS:
            with self.subTest(arm=arm): self.assertEqual(self.verdict(sample(arm)), r.PASS)

    def test_red_identity(self):
        for mutate in (lambda d: d.update(profile='e2-editor-v22'),
                       lambda d: d['manifest'].update(profile='e2-editor-v22'),
                       lambda d: d['artifacts'].update({'probe.wasm': 'b' * 64})):
            d = sample(); mutate(d); self.assertEqual(self.verdict(d), r.FAIL)

    def test_missing_polls_and_depth_are_ne(self):
        d = sample(); d['events'] = []; self.assertEqual(self.verdict(d), r.NE)
        d = sample(); d['events'][0]['message']['detail']['queued'] = 1
        self.assertEqual(self.verdict(d), r.NE)

    def test_old_drain_and_reply_priority_red(self):
        for patch in ({'drained': 2}, {'replyPending': True}, {'reply': True}):
            d = sample(); d['events'][0]['message']['detail'].update(patch)
            self.assertEqual(self.verdict(d), r.FAIL)

    def test_every_actual_open_a11y(self):
        d = sample('hang'); d['responses'][-1]['message']['result']['a11y']['unavailable'] = 'wrong'
        self.assertEqual(self.verdict(d), r.FAIL)
        d = sample(); d['responses'][-1]['message']['result']['a11y'] = {}
        self.assertEqual(self.verdict(d), r.FAIL)
        d = sample(); d['requests'] = []; self.assertEqual(self.verdict(d), r.NE)

    def test_no_proof_control_cannot_pass(self):
        for arm in ('proof', 'hang', 'js-thread'):
            d = sample(arm); d['events'] = d['events'][:1]
            self.assertEqual(self.verdict(d), r.NE)
        d = sample('proof'); d['events'].append(copy.deepcopy(d['events'][-1]))
        self.assertEqual(self.verdict(d), r.NE)

    def test_ordinary_absence_violation_and_wrong_typed_failure(self):
        d = sample(); d['events'].append(sample('proof')['events'][-1])
        self.assertEqual(self.verdict(d), r.FAIL)
        d = sample('proof'); d['control']['error']['details'] = {}
        self.assertEqual(self.verdict(d), r.FAIL)

    def test_hang_requires_timeout_recovery_and_disposal(self):
        mutations = [lambda d: d['control'].update(error={'code': 'CANCELLED'}),
            lambda d: d['control']['error']['details'].update(timeoutMs=100),
            lambda d: d['control']['stateAfter'].update(state='ready'),
            lambda d: d['recoveredState'].update(state='recoverable-error'),
            lambda d: d['workers'][0].update(terminatedAt=None)]
        for mutate in mutations:
            d = sample('hang'); mutate(d); self.assertEqual(self.verdict(d), r.FAIL)

    def test_saved_content_not_proxy(self):
        d = sample(); d['savedBase64'] = ''; self.assertEqual(self.verdict(d), r.NE)
        d = sample(); data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z: z.writestr('content.xml', '<doc/>')
        d['savedBase64'] = base64.b64encode(data.getvalue()).decode()
        self.assertEqual(self.verdict(d), r.FAIL)

    def test_explicit_r2_and_no_generic_negative(self):
        d=sample();d['profile']=d['manifest']['profile']=r.R2_PROFILE
        self.assertEqual(r.judge(d,EXPECTED,r.R2_PROFILE)['verdict'],r.PASS)
        self.assertEqual(self.verdict(d),r.FAIL)
        d=sample('js-thread');d['profile']=d['manifest']['profile']=r.R2_PROFILE
        self.assertNotEqual(r.judge(d,EXPECTED,r.R2_PROFILE)['verdict'],r.PASS)
        d=sample();d['profile']=d['manifest']['profile']='e2-editor-v22'
        self.assertEqual(r.judge(d,EXPECTED,r.R2_PROFILE)['verdict'],r.FAIL)

    def test_r2_private_controls_require_wire_evidence(self):
        for arm in ('proof','hang'):
            d=sample(arm);d['profile']=d['manifest']['profile']=r.R2_PROFILE
            self.assertNotEqual(r.judge(d,EXPECTED,r.R2_PROFILE)['verdict'],r.PASS)
            if arm=='proof':
                d['responses'].append({'generation':1,'message':{'requestId':4,'ok':False,'error':{
                    'code':'MUTATION_OUTCOME_UNKNOWN','failureShape':'proof-absent-at-poll:UNO_COMMAND_RESULT'}}})
            else:d['cancels']=[{'kind':'cancel','generation':1,'requestId':4}]
            self.assertEqual(r.judge(d,EXPECTED,r.R2_PROFILE)['verdict'],r.PASS)
            if arm=='proof':d['responses'][-1]['message']['error']['failureShape']='wrong'
            else:d['cancels'][0]['requestId']=99
            self.assertNotEqual(r.judge(d,EXPECTED,r.R2_PROFILE)['verdict'],r.PASS)

    def test_r2_actual_artifacts_must_match_owner_link(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in r.FILES:(root/name).write_bytes(b'fake')
            (root/'sdk-manifest.json').write_text(json.dumps({'profile':r.R2_PROFILE,'editorContract':{'abiVersion':5}}))
            with self.assertRaisesRegex(ValueError,'owner-linked'):
                r.identity(root,hashlib.sha256(b'fake').hexdigest(),r.R2_PROFILE)
            with self.assertRaisesRegex(ValueError,'wrong profile'):
                r.identity(root,hashlib.sha256(b'fake').hexdigest())

    def test_r2_reference_population_and_duplicate_reds(self):
        direct=[{'browser':b,'round':n,'arm':a,'verdict':r.PASS} for b in ('chrome','firefox') for n in range(1,4) for a in r.ARMS[:3]]
        refs=[{'browser':b,'round':n,'arm':'js-thread','verdict':r.PASS,
               'source':{'sha256':'reference-report','runIndex':i,'pageSha256':str(i)}}
              for i,(b,n) in enumerate((b,n) for b in ('chrome','firefox') for n in range(1,4))]
        self.assertEqual(r.summarize(direct,refs,r.R2_PROFILE)['verdict'],r.PASS)
        for altered in (refs[:-1],refs+[refs[0]],[]):
            self.assertEqual(r.summarize(direct,altered,r.R2_PROFILE)['verdict'],r.NE)
        for field in ('runIndex','pageSha256'):
            altered=copy.deepcopy(refs);altered[1]['source'][field]=altered[0]['source'][field]
            self.assertEqual(r.summarize(direct,altered,r.R2_PROFILE)['verdict'],r.NE)
        self.assertEqual(r.summarize(direct+[refs[0]],refs,r.R2_PROFILE)['verdict'],r.NE)

    def test_old_identity_cannot_be_corrected_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json';path.write_text(json.dumps({'profile':r.PROFILE,'identity':EXPECTED,'runs':[]}))
            with self.assertRaisesRegex(ValueError,'actual r2 identity'):r.corrected_references([path],EXPECTED)

    def test_actual_files_are_required_and_v22_rejected(self):
        import json, hashlib
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name in r.FILES: (p / name).write_bytes(b'fixture')
            (p / 'sdk-manifest.json').write_text(json.dumps({'profile': 'e2-editor-v22',
                'editorContract': {'abiVersion': 5}}))
            with self.assertRaisesRegex(ValueError, 'wrong profile'):
                r.identity(p, hashlib.sha256(b'fixture').hexdigest())


if __name__ == '__main__': unittest.main()
