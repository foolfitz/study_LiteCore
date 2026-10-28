#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.3/6.4: the S5 reader on the v24 profile, with T2 read first.

tools/judge_v23_feature_selection.py is byte-bound (counted-r1-s5-01's instrumentSources) and names
v23's profile and readiness payload, so it is imported, never edited.  Its functions run here as
THEIR OWN code objects re-bound to a namespace in which three names are v24's (`G` below); the test
tests/test_v24_feature_selection_judge.py checks that identity, so "the same reader" is a fact:

  PROFILE    'e2-editor-v24' (v23 reads it in Evidence.__init__ and Evidence.opened, nowhere else)
  readiness  v23's text with one line changed: the typed Z's wire payload carries
             route "uno-insert-text" (the v24 SDK routes every insert of a declaring manifest)
  Evidence   v23's class with the two methods above re-bound

New: t2() and the wrapping inspect_s5().  T2 (spec 6.4, tightened by ruling 2's follow-up): every
insertText request of a type cell carries route "uno-insert-text", and its one reply is ok with
method "uno-insert-text" and completion "uno-command-result"; a request without a route, any reply
with method "paste", a refused reply (proof-absent) or a missing one makes the cell FAIL, not NE.
The population is generated from the page (every insertText request in it).  T2 runs on the raw
streams BEFORE anything else, so a page whose typing took the wrong route FAILs naming the route
even when the rest of it cannot be judged (red case (iii): a v23 page).  The clause tags
`# T2-route` and `# T2-proof` are what J-red's guard-removal mutants (red case (v)) delete.

Only S5 is derived here.  R1, S1-S4 and the S4 interactions answer NOT_ESTABLISHED until they are
derived for the counted runs (6.4).
"""
import argparse
import json
from pathlib import Path
import sys
from types import FunctionType
sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_v23_feature_selection as j23
from judge_v23_feature_pre_red import NotEstablished, need
from judge_v23_feature_selection import request_key
from v24_feature_selection_cases import PROFILE, config, digest, verify_mirror, type_cells, BROWSERS

ROUTE = 'uno-insert-text'
COMPLETION = 'uno-command-result'

G = dict(vars(j23))
G['PROFILE'] = PROFILE


def rebound(function, name=None):
    return FunctionType(function.__code__, G, name or function.__name__, function.__defaults__, function.__closure__)


class Evidence(j23.Evidence):
    __init__ = rebound(j23.Evidence.__init__)
    opened = rebound(j23.Evidence.opened)


def readiness(e):
    p=e.page;v=p['readiness'];gen,handle=e.opened(v['open'])
    e.locate('readiness',v['setup'],e.plan['readinessPoint'])
    e.state('readiness-before-state',v['beforeState']);e.state('readiness-after-state',v['afterState'])
    before=e.save('readiness-before-save',v['beforeSave']);after=e.save('readiness-after-save',v['afterSave'])
    expected=e.plan['fixtureParagraphs'];need(before==expected,'readiness original differs');changed=expected.copy();changed[0]='Z'+changed[0]
    need(after==changed,'actual readiness save mutation missing')
    # Only the readiness generation: S5's type family inserts in its own fresh documents.
    mutations=[r for r in e.requests.values() if r['message']['operation']=='insertText' and r['generation']==gen]
    need(len(mutations)==1,'readiness mutation absent/extra')
    r=mutations[0];need(r['generation']==gen and r['message']['payload']=={'documentHandle':handle,'text':'Z','route':'uno-insert-text'},'readiness wire mutation differs')
    need(e.replies[request_key(r)]['message'].get('ok') is True,'readiness mutation refused')
    inputs=[x for x in p['inputs'] if x['type']=='beforeinput' and x.get('inputType')=='insertText' and x.get('data')=='Z' and x.get('isTrusted') is True]
    need(len(inputs)==1 and inputs[0]['at']<=r['at'],'actual readiness beforeinput missing')
    keys=[x for x in p['inputs'] if x['type']=='keydown' and x.get('key')=='Z' and x.get('isTrusted') is True]
    need(len(keys)==1 and keys[0]['at']<=inputs[0]['at'],'actual readiness Z key absent')
    sink=inputs[0]['sink'];need(sink.get('active') and sink.get('connected') and not sink.get('readOnly') and not sink.get('disabled'),'readiness sink unavailable')
    need(v['afterState']['revision']>v['beforeState']['revision'],'readiness revision unchanged')
    return gen


G['Evidence'] = Evidence
G['readiness'] = readiness
inspect_s5_without_t2 = rebound(j23.inspect_s5, 'inspect_s5_without_t2')


def t2(page, plan):
    """None for a non-type cell; else the list of T2 problems (empty: T2 holds)."""
    row = (plan.get('s5') or {}).get(page.get('caseId'))
    if row is None or row['family'] != 'type':
        return None
    requests, responses = page.get('requests') or [], page.get('responses') or []
    replies = {}
    for item in responses:
        replies.setdefault((item.get('generation'), (item.get('message') or {}).get('requestId')), []).append(item)
    problems, owned = [], set()
    inserts = [r for r in requests if (r.get('message') or {}).get('operation') == 'insertText']
    for n, request in enumerate(inserts):
        message = request['message']; payload = message.get('payload') or {}
        key = (request.get('generation'), message.get('requestId')); owned.add(key)
        where = f"insertText #{n} (generation {key[0]}, text {payload.get('text')!r})"
        if payload.get('route') != ROUTE: problems.append(f"{where}: request route {payload.get('route')!r}")  # T2-route
        got = replies.get(key, [])
        if len(got) != 1:
            problems.append(f'{where}: {len(got)} replies')
            continue
        reply = got[0]['message']
        if reply.get('ok') is not True:
            error = reply.get('error') or {}
            continue
        result = reply.get('result') or {}
        if result.get('method') != ROUTE: problems.append(f"{where}: reply method {result.get('method')!r}")  # T2-route
    for item in responses:
        result = (item.get('message') or {}).get('result')
        key = (item.get('generation'), (item.get('message') or {}).get('requestId'))
        if isinstance(result, dict) and result.get('method') == 'paste' and key not in owned: problems.append(f'reply {key} outside insertText: method paste')  # T2-route
    # Non-vacuity: a typed sequence that sent no insertText has nothing for T2 to hold over.
    for arm in (('s5cand', 's5ref') if row['settledReference'] else ('s5cand',)):
        window = (page.get(arm) or {}).get('sequence') or {}
        start, end = window.get('requestStart'), window.get('requestEnd')
        if type(start) is not int or type(end) is not int:
            problems.append(f'{arm}: typed sequence window absent')
        elif not any((r.get('message') or {}).get('operation') == 'insertText' and r.get('generation') == window.get('generation')
                     for r in requests[start:end]):
            problems.append(f'{arm}: no insertText request in the typed sequence window')
    return problems


def inspect_s5(page, plan, browser):
    problems = t2(page, plan)
    rest = inspect_s5_without_t2(page, plan, browser)
    if problems:
        reason = 'T2: ' + '; '.join(problems)
        return {'verdict': 'FAIL', 'reason': reason, 't2': problems,
                'groups': {'S5': {'verdict': 'FAIL', 'reason': reason, 't2': problems, 'withoutT2': rest}}}
    if problems is not None:
        rest = {**rest, 't2': []}
        rest['groups'] = {**rest.get('groups', {}), 'S5': {**rest.get('groups', {}).get('S5', {}), 't2': []}}
    return rest


def inspect(page, plan, browser):
    if page.get('caseId') in plan.get('s5', {}):
        return inspect_s5(page, plan, browser)
    return {'verdict': 'NOT_ESTABLISHED', 'reason': 'only S5 is derived for v24 so far', 'groups': {}}


def m2(cells, plan):
    """Spec 6.3 M2 over a type-only preparation: per cell and browser, T1 (the S5 comparison) and T2."""
    wanted = {(b, c) for b in BROWSERS for c in type_cells(plan)}
    rows, seen = [], set()
    for cell in cells:
        key = (cell['browser'], cell['caseId']); page = cell.get('page') or {}
        if key in seen or key not in wanted:
            rows.append({'cell': key, 'verdict': 'NOT_ESTABLISHED', 'reason': 'duplicate/undeclared observation'}); continue
        seen.add(key)
        value = inspect(page, plan, cell['browser']) if not cell.get('fatal') and page.get('caseId') == cell['caseId'] \
            else {'verdict': 'NOT_ESTABLISHED', 'reason': 'unclean cell/label'}
        rows.append({'cell': key, **value})
    def insert_replies(page):
        keys = {(r.get('generation'), r['message'].get('requestId')) for r in page.get('requests') or []
                if r['message'].get('operation') == 'insertText'}
        return [r for r in page.get('responses') or [] if (r.get('generation'), r['message'].get('requestId')) in keys]
    replies = [r for c in cells for r in insert_replies(c.get('page') or {})]
    inserted = [r for r in replies if r['message'].get('ok') is True]
    refused = [r for r in replies if str((r['message'].get('error') or {}).get('failureShape', '')).startswith('proof-absent')]
    summary = {'required': len(wanted), 'observed': len(seen & wanted),
               'pass': sum(r['verdict'] == 'PASS' for r in rows), 'fail': sum(r['verdict'] == 'FAIL' for r in rows),
               'notEstablished': sum(r['verdict'] == 'NOT_ESTABLISHED' for r in rows),
               'insertTextReplies': len(replies), 'proofAbsentReplies': len(refused),
               'replyMethods': sorted({str(r['message']['result'].get('method')) for r in inserted})}
    verdict = 'FAIL' if summary['fail'] else 'PASS' if seen == wanted and summary['pass'] == len(wanted) and not refused else 'NOT_ESTABLISHED'
    return {'verdict': verdict, 'population': 's5-type', 'summary': summary, 'results': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text()); plan = report['config']
    need(report.get('postConfig') == plan, 'instrument/source graph changed during the run or incomplete')
    if not report.get('scratch'):
        need(config() == plan, 'live instrument/source graph differs from the run')
    need(report['mirrorBindings'] == verify_mirror(args.report.parent / 'mirror', plan), 'mirror receipt differs')
    cells = []
    for item in report['runs']:
        raw = (args.report.parent / item['path']).read_bytes(); need(digest(raw) == item['sha256'], 'cell bytes changed')
        cells.append(json.loads(raw))
    need(report.get('population') == 's5-type', 'only the M2 type population is read here so far')
    result = m2(cells, plan)
    if report.get('scratch'):
        result['scratch'] = report['scratch']
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
