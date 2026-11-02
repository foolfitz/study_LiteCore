#!/usr/bin/env python3
"""K1-K8 of SPEC-M3-K-0.2.45 section 7 (SPEC-M3-K-0.2.44 section 6), read from the chain's products, so that whether K holds is a line
anyone can re-run and not the drafter's sentence (CLAUDE.md section 8).  Read-only; no browser, no host.

  read_k.py LOGDIR               write findings/evidence/release-0.2.45/k-verdict.json, exit 0 iff K_HOLDS
  read_k.py LOGDIR --self-test   every mutation of the inputs must turn the verdict red
"""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / 'findings/evidence'
R = EV / 'release-0.2.45'
E = EV / 'm3-production-ui/runs-0.2.45'
K45 = EV / 'k-0.2.45'
PAGE = '022d0cd0b5152f1e'
SIX = {'page_honesty': ('m3-page-honesty', 'PAGE HONEST'), 'locks': ('m3-locks', 'LOCKS LAND'), 'versions': ('m3-versions', 'VERSIONS CORRECT'),
       'assets': ('m3-assets', 'ASSETS DELIVERED'), 'same_second': ('m3-same-second', 'SAME-SECOND SAVES KEPT')}


def text(path):
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def load(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def collect(log):
    chain = text(log / 'chain.txt')
    six = {}
    listing = text(E / 'red-cases-six.txt')
    for name in (*SIX, 'host_entry'):
        m = re.search(rf'^== {name} (\S+)$', listing, re.M)
        six[name] = {'path': m.group(1) if m else None, 'report': load(ROOT / m.group(1)) if m else {},
                     'exit': (re.search(rf'^== {name} .*?^exit (\d+)$', listing, re.M | re.S) or [None, None])[1]}
    c2 = {r: {'c2': text(R / f'c2/r{r}/judge-output.txt'), 'p2': text(R / f'c2/r{r}/p2-output.txt'),
              'desk': text(R / f'c2/r{r}/desk-gate.txt')} for r in (1, 2, 3)}
    return {'chain': chain, 'pooled': text(E / 'red-cases-on-counted-pooled.txt'),
            'ui': [load(E / n) for n in ('counted-KR-x3.json', 'counted-ctl-S-P.json')],
            'six': six, 'autosaveRed': text(E / 'red-cases-autosave.txt'), 'newDocumentRed': text(E / 'red-cases-new-document.txt'),
            'autosaveLog': text(log / 'counted-autosave.log'), 'newDocumentLog': text(log / 'counted-new_document.log'),
            'mergeRead': load(R / 'merge-m2/read-k-merge.json'), 'mergeExit': text(R / 'merge-m2/judge-exit.txt'), 'mergeJudge': text(R / 'merge-m2/judge-output.txt'),
            'c2': c2, 'path': load(R / 'product-path/read-k-path.json'),
            'gate': load(K45 / 'legacy-v8-gate/report.json'), 'enter': load(K45 / 'enter-replay/report.json')}


def judge(i):
    rows = {}

    def k(name, checks):
        bad = [label for label, ok in checks if not ok]
        rows[name] = {'holds': not bad, 'failed': bad}

    start = re.search(r'IDENTITY-START (.+)$', i['chain'], re.M)
    end = re.search(r'IDENTITY-END (.+)$', i['chain'], re.M)
    k('K1', [('a DONE line', bool(re.search(r' DONE \(read with', i['chain']))), ('no STOP', ' STOP' not in i['chain']),
             ('preflight P0-P6 ok', 'PREFLIGHT ok (P0-P6)' in i['chain']),
             ('identity start == end', bool(start and end) and start.group(1) == end.group(1)),
             ('the identity is the candidate', bool(start) and f'dist-page {PAGE}' in start.group(1) and 'version 0.2.45' in start.group(1) and 'dirty[]' in start.group(1))])
    k('K2', [('both counted steps exit 0', len(re.findall(r'counted production_ui (?:KR x3|ctl/S/P) exit 0', i['chain'])) == 2),
             ('red cases 28/28', re.search(r'^red cases: 28/28$', i['pooled'], re.M) is not None),
             ('13 B3x notes and no other', len(re.findall(r'no passing', re.sub(r'^expected:.*$', '', i['pooled'], flags=re.M))) == 13),
             ('every cell passes, documents clean', len(i['ui']) == 2 and all((u.get('score') or {}).get('allPass') is True and (u.get('score') or {}).get('docClean') is True and u.get('counted') is True for u in i['ui']))])
    checks = []
    for name, (_, word) in SIX.items():
        s = i['six'][name]
        checks += [(f'{name} verdict', ((s['report'].get('score') or {}).get('verdict')) == word), (f'{name} counted', s['report'].get('label') == 'counted'), (f'{name} red cases exit 0', s['exit'] == '0')]
    s = i['six']['host_entry']
    checks += [('host_entry lands', (s['report'].get('score') or {}).get('lands') is True), ('host_entry counted', s['report'].get('label') == 'counted'), ('host_entry red cases exit 0', s['exit'] == '0')]
    k('K3', checks)
    k('K4', [('autosave holds', re.search(r'^VERDICT AUTOSAVE HOLDS', i['autosaveLog'], re.M) is not None), ('autosave red cases', re.search(r'^exit 0$', i['autosaveRed'], re.M) is not None),
             ('new document works', 'NEW-DOCUMENT WORKS' in i['newDocumentLog'] and 'problems=[]' in i['newDocumentLog']), ('new document red cases', re.search(r'^exit 0$', i['newDocumentRed'], re.M) is not None)])
    k('K5', [('reader counted', i['mergeRead'].get('verdict') == 'K_MERGE_COUNTED'), ('judge exit 4', i['mergeExit'].startswith('exit=4')),
             ('verdict PASS, uncounted', 'VERDICT PASS (NOT A COUNTED VERDICT: uncounted)' in i['mergeJudge']),
             ('red PASS both browsers', len(re.findall(r'^red\s+PASS', i['mergeJudge'], re.M)) == 2),
             ('one runner', re.search(r"runners \['aaee0cda5be5ad84'\]", i['mergeJudge']) is not None), ('no FAIL line', re.search(r'^\S+\s+FAIL', i['mergeJudge'], re.M) is None)])
    checks = []
    for r, c in i['c2'].items():
        checks += [(f'r{r} judge_c2', c['c2'].rstrip().endswith('exit 0') and 'PASS: both browsers, every cell' in c['c2']),
                   (f'r{r} judge_p2', c['p2'].rstrip().endswith('exit 0') and 'PASS: both browsers, every cell' in c['p2']),
                   (f'r{r} gate 16', '(needs <= 16)' in c['p2']), (f'r{r} desk clean', '"gate": "clean"' in c['desk'])]
    k('K6', checks)
    k('K7', [('K_PATH_HOLDS', i['path'].get('verdict') == 'K_PATH_HOLDS'), ('no problems', not i['path'].get('problems'))])
    k('K8', [('page gate', i['gate'].get('verdict') == 'LEGACY_V8_CONTROL_REFUSED' and i['gate'].get('sourceSha256', '').startswith(PAGE)), ('Enter replay', i['enter'].get('verdict') == 'V24_ENTER_HOLDS')])
    return {'verdict': 'K_HOLDS' if all(r['holds'] for r in rows.values()) and len(rows) == 8 else 'K_DOES_NOT_HOLD', 'rows': rows}


def mutations():
    def sub(key, old, new):
        def f(i):
            if old not in i[key]:
                raise SystemExit(f'mutation target gone: {old}')
            i[key] = i[key].replace(old, new)
        return f

    def on_score(name, value):
        return lambda i: i['six'][name]['report']['score'].update(verdict=value)

    def c2(r, kind, old, new):
        def f(i):
            if old not in i['c2'][r][kind]:
                raise SystemExit(f'mutation target gone: {old}')
            i['c2'][r][kind] = i['c2'][r][kind].replace(old, new)
        return f
    yield 'K1', 'no DONE', sub('chain', ' DONE (read with', ' STOPPED (read with')
    yield 'K1', 'identity moved', lambda i: i.update(chain=re.sub(r'(IDENTITY-END .*?)dirty\[\]', r'\1dirty[x]', i['chain']))
    yield 'K2', 'red cases 27/28', sub('pooled', 'red cases: 28/28', 'red cases: 27/28')
    yield 'K2', 'a cell not passing', lambda i: i['ui'][0]['score'].update(allPass=False)
    yield 'K2', 'an uncounted report', lambda i: i['ui'][1].update(counted=False)
    yield 'K3', 'locks do not land', on_score('locks', 'LOCKS DO NOT LAND')
    yield 'K3', 'assets shakedown label', lambda i: i['six']['assets']['report'].update(label='shakedown')
    yield 'K3', 'red cases exit 1', lambda i: i['six']['versions'].update(exit='1')
    yield 'K3', 'host entry not landing', lambda i: i['six']['host_entry']['report']['score'].update(lands=False)
    yield 'K4', 'autosave does not hold', sub('autosaveLog', 'VERDICT AUTOSAVE HOLDS', 'VERDICT AUTOSAVE DOES NOT HOLD')
    yield 'K4', 'new document not established', sub('newDocumentLog', 'NEW-DOCUMENT WORKS', 'NEW-DOCUMENT NOT_ESTABLISHED')
    yield 'K5', 'not counted', lambda i: i['mergeRead'].update(verdict='K_MERGE_NOT_COUNTED')
    yield 'K5', 'judge exit 3', sub('mergeExit', 'exit=4', 'exit=3')
    yield 'K5', 'a judge FAIL line', lambda i: i.update(mergeJudge=i['mergeJudge'] + '\nM2-1a      FAIL     x\n')
    yield 'K6', 'a p2 FAIL', c2(2, 'p2', 'PASS: both browsers, every cell', 'FAIL: chrome boundaries-gap200 commit median')
    yield 'K6', 'the old gate', c2(3, 'p2', '(needs <= 16)', '(needs <= 10)')
    yield 'K6', 'dirty desk', c2(1, 'desk', '"gate": "clean"', '"gate": "dirty"')
    yield 'K7', 'path does not hold', lambda i: i['path'].update(verdict='K_PATH_RED')
    yield 'K8', 'page gate', lambda i: i['gate'].update(verdict='LEGACY_V8_RAN')
    yield 'K8', 'Enter', lambda i: i['enter'].update(verdict='V24_ENTER_DIFFERS')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('log', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    inputs = collect(args.log)
    result = judge(inputs)
    if args.self_test:
        if result['verdict'] != 'K_HOLDS':
            print(json.dumps(result, indent=1, ensure_ascii=False))
            print('self-test needs a holding input')
            return 2
        rows = {}
        for row, label, mutate in mutations():
            mutated = copy.deepcopy(inputs)
            mutate(mutated)
            got = judge(mutated)
            rows[f'{row} {label}'] = got['verdict'] != 'K_HOLDS' and not got['rows'][row]['holds']
        out = {'selfTest': 'ALL_RED' if all(rows.values()) else 'SOME_HELD', 'mutations': len(rows), 'held': [k for k, v in rows.items() if not v]}
        (R / 'k-verdict-self-test.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out['selfTest'] == 'ALL_RED' else 1
    (R / 'k-verdict.json').write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    print(result['verdict'])
    for name, row in result['rows'].items():
        print(f"{name} {'holds' if row['holds'] else 'DOES NOT HOLD ' + str(row['failed'])}")
    return 0 if result['verdict'] == 'K_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
