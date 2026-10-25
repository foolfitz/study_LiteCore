#!/usr/bin/env python3
"""Read only bounded040 entrance/timing observations, never all of section9.2."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v23_remaining_cases import ARMS, CASES_040, FRAME_SHA256, identity, sha, fixtures
PASS, FAIL, NE = 'PASS', 'FAIL', 'NOT_ESTABLISHED'


def judge(page, expected, fixture_hashes, profile):
    missing, failures = [], []
    def need(ok, msg):
        if not ok: missing.append(msg)
    def check(ok, msg):
        if not ok: failures.append(msg)
    need(page.get('complete') and not page.get('fatal'), 'incomplete or unclean arm')
    check(page.get('profile') == profile and page.get('artifacts') == expected, 'actual served identity mismatch')
    arm = page.get('arm'); need(arm in ARMS, 'unknown arm')
    if arm in CASES_040:
        check(fixture_hashes.get('frame') == FRAME_SHA256, '040 fixture is not the ruling pin')
    required = {'frame':['frame'], 'html-negative':['frame'], 'html-positive':['frame'],
                'largest':['largest'], 'workload':['plain','long60']}.get(arm, [])
    for name in required:
        check(page.get('fixtures', {}).get(name, {}).get('sha256') == fixture_hashes.get(name), f'{name} fixture mismatch')
    steps = {x['name']: x for x in page.get('steps', [])}
    def step(name, limit=None):
        s = steps.get(name); need(s is not None, f'missing {name}')
        if s:
            check(s.get('ok') is True, f'{name} failed')
            if limit is not None:
                need(all(k in s for k in ('startedAt','finishedAt')), f'{name} timing absent')
                if all(k in s for k in ('startedAt','finishedAt')):
                    check(0 <= s['finishedAt']-s['startedAt'] <= limit, f'{name} outside30s')
    responses = {(x['generation'],x['message'].get('requestId')):x['message'] for x in page.get('responses',[])}
    requests = page.get('requests', [])
    for name in required:
        step('open-'+name, 30000 if name == 'largest' else None)
    if arm in CASES_040:
        opened=[x for x in requests if x.get('operation')=='open']
        need(bool(opened), 'actual frame open request absent')
        for op in opened:
            check(op.get('payload',{}).get('buffer',{}).get('sha256')==FRAME_SHA256, 'wire open/restoration bytes differ from authority')
            need(responses.get((op['generation'],op['requestId']),{}).get('ok') is True, 'actual frame open/restoration response absent')
    if arm == 'frame':
        step('frame-close')
        closes = [x for x in requests if x.get('operation') == 'close']
        need(len(closes)==1, 'no unique actual close')
        if closes:
            reply = responses.get((closes[0]['generation'], closes[0]['requestId']), {})
            check(reply.get('ok') is True and reply.get('result',{}).get('recovered') is not True,
                  'destroy lacks actual successful close reply')
    if arm in ('html-positive', 'html-negative'):
        for name in ('040-anchor','040-select','040-complex-read'): step(name)
        need(page.get('preSelection', {}).get('selectionType') == 'complex', '040 selected-frame COMPLEX precondition absent')
        kind = 9 if arm == 'html-positive' else 3
        controls = [x for x in requests if x.get('operation') == 'v23Diagnostic']
        need(len(controls)==1 and controls[0].get('payload',{}).get('kind') == kind, 'actual private control absent')
        events = [(x['generation'], x['message'].get('detail',{})) for x in page.get('events',[])]
        entries = [(g,e) for g,e in events if e.get('type') == 'v23-control']
        need(len(entries)==1, 'actual control entry absent')
        if entries and controls:
            check(entries[0][0]==controls[0]['generation'] and entries[0][1].get('requestId')==controls[0]['requestId']
                  and entries[0][1].get('kind')==kind, 'control entry attribution mismatch')
        # Establish setup from actual wire replies, not the page's labels.
        searches = [x for x in requests if x.get('operation') == 'search' and x.get('payload',{}).get('query') == 'IV-ASCHAR']
        selects = [x for x in requests if x.get('operation') == 'editorSelectRangeV2']
        reads = [x for x in requests if x.get('operation') == 'getSelection']
        need(len(searches)==1 and len(selects)==1 and len(reads)==1, 'wire search/select/read setup absent')
        if len(searches)==len(selects)==len(reads)==1 and controls:
            search, select, read, control_req = searches[0], selects[0], reads[0], controls[0]
            need(search['generation']==select['generation']==read['generation']==control_req['generation'], 'setup generation mismatch')
            need(search['requestId']<select['requestId']<read['requestId']<control_req['requestId'], 'setup wire order mismatch')
            initial_open=next((o for o in opened if o['generation']==search['generation']), None)
            handle=responses.get((initial_open['generation'],initial_open['requestId']),{}).get('result',{}).get('documentHandle') if initial_open else None
            need(handle is not None, 'opened document handle absent')
            if handle is not None:
                check(all(op.get('payload',{}).get('documentHandle')==handle for op in (search,select,read)), 'setup refers to a different document')
            search_reply=responses.get((search['generation'],search['requestId']),{})
            select_reply=responses.get((select['generation'],select['requestId']),{})
            read_reply=responses.get((read['generation'],read['requestId']),{})
            need(search_reply.get('ok') and search_reply.get('result',{}).get('found'), 'wire anchor not found')
            need(select_reply.get('ok') and read_reply.get('ok') and read_reply.get('result',{}).get('selectionType')=='complex', 'wire selection not COMPLEX')
            try:
                raw=search_reply['result']['selections'][0]['rectangles'].split(';')[0]
                x,y,w,h=map(float,raw.split(','))
                expected_range={'startXTwips':x,'startYTwips':y+h//2,'endXTwips':x+8000,'endYTwips':y+h//2}
                check(all(select.get('payload',{}).get(k)==v for k,v in expected_range.items()), 'wire range differs from actual rectangle')
            except (KeyError,IndexError,ValueError,AttributeError): need(False,'actual search rectangle unreadable')
        c = page.get('control', {})
        if kind == 9:
            returns = [(g,e) for g,e in events if e.get('type')=='v23-html-return']
            need(len(returns)==1, 'literal engine-thread HTML return absent')
            html = c.get('result',{}).get('html')
            need(isinstance(html,str) and bool(html), 'actual HTML output absent')
            if isinstance(html,str):
                check('<img' in html.lower() and 'IV-ASCHAR' in html, 'HTML lacks selected image/anchor witness')
                check(c.get('result',{}).get('bytes')==len(html.encode()), 'HTML byte count mismatch')
            if returns and controls:
                check(returns[0][0]==controls[0]['generation'] and
                      returns[0][1].get('requestId')==controls[0]['requestId'] and
                      returns[0][1].get('html')==html and returns[0][1].get('bytes')==len((html or '').encode()), 'HTML return attribution mismatch')
            check(not c.get('error'), 'positive HTML rejected')
            if controls:
                terminal=responses.get((controls[0]['generation'],controls[0]['requestId']),{})
                need(terminal.get('ok') is True and terminal.get('result',{}).get('html')==html and terminal.get('result',{}).get('bytes')==len((html or '').encode()), 'literal terminal wire result absent')
        else:
            if controls:
                terminal=responses.get((controls[0]['generation'],controls[0]['requestId']))
                check(terminal is None, 'negative control returned a terminal wire reply')
            check(c.get('error',{}).get('code')=='TIMEOUT' and c.get('error',{}).get('details',{}).get('timeoutMs')==30000,
                  'selected-context JS LOK did not reach existing30s timeout')
            check(c.get('stateAfter',{}).get('state')=='recoverable-error', 'session did not enter recovery')
            step('040-restart'); step('040-recovery-save')
            need(len({x['generation'] for x in opened})==2, 'successful fresh-generation restoration absent')
            check(page.get('recovered',{}).get('state')=='ready', 'fresh-worker recovery absent')
            workers = page.get('workers',[]); need(len(workers)==2, 'fresh-worker witness absent')
            if len(workers)==2:
                check(workers[0].get('terminatedAt') is not None and workers[0]['terminatedAt']<=workers[1]['createdAt'],
                      'old worker not disposed before replacement')
    if arm == 'largest': step('first-reply-after-largest'); step('largest-page-rectangles')
    if arm == 'workload':
        for name in ('markdown-64KiB','long60-save'): step(name,30000)
        for name in ('long60-dirty-move','long60-merge','first-reply-after-merge'): step(name)
        check(page.get('markdown',{}).get('bytes')==65536, 'Markdown is not exactly64KiB')
        pasted = [x for x in requests if x.get('operation')=='pasteMarkdown']
        need(len(pasted)==1 and pasted[0].get('payload',{}).get('textUtf8Bytes')==65536, 'actual64KiB dispatch absent')
        need(len(page.get('layoutWindows',[]))==2, 'bounded layout observations missing')
        merge = page.get('merge', {})
        need(merge.get('completion') == 'verified-key-undo' and merge.get('changed') is True,
             'after-merge timing has no actual verified changed merge')
    timing = {name: s.get('finishedAt',0)-s.get('startedAt',0) for name,s in steps.items()}
    return {'verdict': NE if missing else FAIL if failures else PASS, 'missing':missing,'failed':failures,
            'stepMilliseconds':timing, 'unestablishedMetrics':['engine tick intervals','exact INVALIDATE_TILES latency',
            'engine idle-layout completion'], 'caseId':CASES_040.get(arm,arm), 'scope':'only named arm; exact040 requires all three040 arms'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reports',type=Path,nargs='+')
    p.add_argument('--profile',required=True);p.add_argument('--wasm-sha256',required=True)
    p.add_argument('--scope',choices=('040','timing'),default='040')
    a=p.parse_args();expected=identity(a.profile,a.wasm_sha256);results=[]
    _, population=fixtures()
    for path in a.reports:
        report=json.loads(path.read_text())
        for name,digest in report['fixtures'].items():
            if sha(path.parent/'mirror'/f'{name}.odt')!=digest:raise ValueError(f'archived fixture mismatch: {name}')
        if population!=report['population']:raise ValueError('source corpus population drift')
        results.extend(dict(browser=x['browser'],round=x['round'],arm=x['arm'],
            **judge(x.get('page') or {},expected,report['fixtures'],a.profile)) for x in report.get('runs',[]))
    arms=set(CASES_040) if a.scope=='040' else {'largest','workload'}
    expected_population={(b,n,arm) for arm in arms for b in ('chrome','firefox') for n in range(1,4)}
    actual=[(x['browser'],x['round'],x['arm']) for x in results]
    complete=bool(actual) and len(actual)==len(set(actual)) and set(actual)==expected_population
    successor=a.scope!='040' or a.profile=='e2-editor-v23-diag-r2'
    verdict=NE if not complete or not successor or any(x['verdict']==NE for x in results) else FAIL if any(x['verdict']==FAIL for x in results) else PASS
    print(json.dumps({'verdict':verdict,'populationComplete':complete,'successorAcceptanceIdentity':successor,
        'results':results,'allSection9_2Closed':False},indent=2));return 0 if verdict==PASS else 1
if __name__=='__main__':raise SystemExit(main())
