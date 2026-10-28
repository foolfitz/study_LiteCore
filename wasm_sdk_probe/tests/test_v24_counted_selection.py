"""Instrument controls only. Rewritten historical pages are synthetic, never v24 count credit."""
import copy
import difflib
import gzip
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import judge_v23_feature_selection as old
import judge_v24_feature_selection as prep
import judge_v24_counted_selection as reader
import v24_counted_selection_cases as cases

BASE = SDK.parent / 'findings/evidence/link-batch-v23/feature-protocol'


def historical(directory, receipt):
    return reader.load_cell(BASE / directory, receipt)


def shape(cell, plan):
    cell = copy.deepcopy(cell)
    p = cell['page']
    p.update(profile='e2-editor-v24', servedSources=plan['servedSources'], artifacts=plan['profile']['artifacts'],
             configSha256=cases.digest(cases.encoded(plan)))
    for worker in p['workers']:
        worker['url'] = worker['url'].replace('/e2-editor-v23/', '/e2-editor-v24/')
    inserts = set()
    for request in p['requests']:
        if request['message']['operation'] == 'insertText':
            request['message']['payload']['route'] = 'uno-insert-text'
            inserts.add(old.request_key(request))
    for reply in p['responses']:
        if old.request_key(reply) in inserts and reply['message'].get('ok'):
            reply['message']['result'].update(method='uno-insert-text', completion='uno-command-result')
    cell.pop('inspection', None)
    return cell


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = cases.config()
        cls.r1report = json.loads((BASE / 'r1-counted-01/report.json').read_bytes())

    def test_population_and_preparation_unchanged(self):
        self.assertEqual({k: len(cases.population(self.plan, k)) * 2 for k in cases.KINDS},
                         {'s5': 1176, 'r1': 144, 'selection': 234})
        original = cases.preparation.config()
        self.assertEqual({k: v for k, v in original.items() if k != 'instrumentSources'},
                         {k: v for k, v in self.plan.items() if k != 'instrumentSources'})
        # The preparation runner is not executed by this collector; membership comes from imports.
        for name in cases.STARTS:
            self.assertIn('tools/' + name, self.plan['instrumentSources'])
        self.assertIn('tools/judge_v24_feature_selection.py', self.plan['instrumentSources'])
        with self.assertRaises(ValueError):
            cases.population(self.plan, 'invented')

    def test_reader_code_objects_and_routes(self):
        for name in ('inspect', 'inspect_r1', 'inspect_interaction', 'judge', 'r1_arm'):
            fn = reader.G[name] if name == 'r1_arm' else getattr(reader, name)
            self.assertIs(fn.__code__, getattr(old, name).__code__)
            self.assertIs(fn.__globals__, reader.G)
        self.assertIs(reader.G['inspect_s5'], prep.inspect_s5)
        self.assertIs(reader.G['Evidence'], prep.Evidence)
        self.assertIs(reader.G['readiness'], prep.readiness)
        a = inspect.getsource(old.r1_marker_witness).splitlines()
        b = inspect.getsource(reader.r1_marker_witness).splitlines()
        changes = [s for s in difflib.unified_diff(a, b, n=0) if s[:1] in '+-' and s[:3] not in ('---', '+++')]
        self.assertEqual(len(changes), 2, changes)
        self.assertEqual(changes[0][1:].replace("'text':'#'}", "'text':'#','route':'uno-insert-text'}"), changes[1][1:])

    def test_every_historical_r1_and_selection_synthetic_shape(self):
        # Tool-closed population from the retained reports, including both browsers and S4 interactions.
        for directory, kind in (('r1-counted-01', 'r1'), ('selection-counted-01', 'selection')):
            report = json.loads((BASE / directory / 'report.json').read_bytes())
            cells = []
            for receipt in report['runs']:
                cell = shape(historical(directory, receipt), self.plan)
                value = reader.inspect(cell['page'], self.plan, cell['browser'])
                self.assertEqual(value['verdict'], 'PASS', (directory, receipt['path'], value))
                cells.append(cell)
            value = reader.judge(cells, self.plan, kind)
            self.assertEqual(value['verdict'], 'PASS', value['groups'])
            self.assertTrue(value['populationComplete'])
            self.assertNotEqual(reader.judge(cells[:-1], self.plan, kind)['verdict'], 'PASS')
            self.assertNotEqual(reader.judge(cells + cells[:1], self.plan, kind)['verdict'], 'PASS')
            self.assertNotEqual(reader.judge([], self.plan, kind)['verdict'], 'PASS')

    def test_old_profile_and_missing_marker_route_rejected(self):
        original = historical('r1-counted-01', self.r1report['runs'][0])
        self.assertEqual(reader.inspect(original['page'], self.plan, original['browser'])['verdict'], 'NOT_ESTABLISHED')
        cell = shape(original, self.plan)
        p = cell['page']
        for q in p['requests']:
            if q['message']['operation'] == 'insertText' and q['message']['payload']['text'] == '#':
                q['message']['payload'].pop('route')
        value = reader.inspect(p, self.plan, cell['browser'])
        self.assertEqual(value['verdict'], 'NOT_ESTABLISHED', value)
        self.assertIn('marker insertion absent/extra', value['reason'])

    def test_s5_real_v24_and_t2_reds(self):
        base = SDK.parent / 'findings/evidence/link-batch-v24/pre-count/m2/run-01'
        report = json.loads((base / 'report.json').read_bytes())
        # Real M2 wire record, only the config identity is recast for this instrument control.
        cell = reader.load_cell(base, report['runs'][0])
        p = copy.deepcopy(cell['page'])
        p['configSha256'] = cases.digest(cases.encoded(self.plan))
        self.assertEqual(reader.inspect(p, self.plan, cell['browser'])['verdict'], 'PASS')
        bad = copy.deepcopy(p)
        request = next(q for q in bad['requests'] if q['message']['operation'] == 'insertText')
        request['message']['payload'].pop('route')
        value = reader.inspect(bad, self.plan, cell['browser'])
        self.assertEqual(value['verdict'], 'FAIL'); self.assertIn('route', value['reason'])
        bad = copy.deepcopy(p)
        request = next(q for q in bad['requests'] if q['message']['operation'] == 'insertText')
        reply = next(t for t in bad['responses'] if old.request_key(t) == old.request_key(request))
        reply['message']['result'].pop('completion')
        value = reader.inspect(bad, self.plan, cell['browser'])
        self.assertEqual(value['verdict'], 'FAIL'); self.assertIn('completion', value['reason'])
        reply['message'] = {'requestId': request['message']['requestId'], 'ok': False,
                            'error': {'code': 'MUTATION_OUTCOME_UNKNOWN', 'failureShape': 'proof-absent-at-poll:UNO_COMMAND_RESULT'}}
        value = reader.inspect(bad, self.plan, cell['browser'])
        self.assertEqual(value['verdict'], 'FAIL'); self.assertIn('refused', value['reason'])

    def test_preparation_never_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'report.json'
            path.write_text(json.dumps({'preparationOnly': True, 'countedV24': True}))
            with self.assertRaisesRegex(ValueError, 'preparation'):
                reader.read_report(path)

    def test_cell_hash_and_path_reds(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'cell.json'
            path.write_text('{}')
            good = {'path': path.name, 'sha256': cases.digest(path.read_bytes())}
            self.assertEqual(reader.load_cell(path.parent, good), {})
            with self.assertRaisesRegex(ValueError, 'cell bytes changed'):
                reader.load_cell(path.parent, {**good, 'sha256': '0' * 64})
            with self.assertRaisesRegex(ValueError, 'invalid cell path'):
                reader.load_cell(path.parent, {**good, 'path': '../cell.json'})


if __name__ == '__main__':
    unittest.main()
