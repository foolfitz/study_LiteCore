#!/usr/bin/env python3
"""Public S2 evidence reader; old-v19 stale replies are expected-red only after readiness."""
import argparse
import base64
import io
import json
from pathlib import Path
import re
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from odt_paragraphs import paragraph_texts_from_xml
from v23_feature_pre_red_cases import PROFILE,BROWSERS,WASM,config,encoded,digest,verify_mirror

class NotEstablished(ValueError): pass

def need(value,message):
    if not value: raise NotEstablished(message)

def binary(value):
    need(value.get('encoding')=='base64','binary wire evidence absent')
    raw=base64.b64decode(value['data'],validate=True)
    need(len(raw)==value['bytes'],'binary length mismatch')
    return raw

def paragraphs(saved):
    raw=base64.b64decode(saved['base64'],validate=True)
    need(digest(raw)==saved['sha256'],'saved bytes hash differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return paragraph_texts_from_xml(archive.read('content.xml'))

def stream(page):
    requests={}; replies={}
    for item in page['requests']:
        key=(item['generation'],item['message']['requestId'])
        need(key not in requests,'duplicate request identity'); requests[key]=item
    for item in page['responses']:
        key=(item['generation'],item['message']['requestId'])
        need(key not in replies,'duplicate terminal'); replies[key]=item
    need(set(replies)<=set(requests),'terminal has no posted request')
    return requests,replies

def call_binding(page,name,operation,requests,replies):
    calls=[c for c in page['calls'] if c['name']==name]
    need(len(calls)==1 and calls[0].get('ok') is True,'missing/refused public call '+name)
    call=calls[0]
    matches=[(key,r) for key,r in requests.items() if r['generation']==call['generation'] and
             r['message']['operation']==operation and call['startedAt']<=r['at']<=call['finishedAt']]
    need(len(matches)==1,'missing/nonunique wire call '+name)
    key,request=matches[0]; terminal=replies.get(key)
    need(terminal is not None and terminal['message'].get('ok') is True,'missing/refused terminal '+name)
    need(request['at']<=terminal['at']<=call['finishedAt'],'terminal outside public call '+name)
    need(request['message']['payload'].get('documentHandle')==call['documentHandle'],'wrong document '+name)
    return call,request,terminal

def binding(page,plan,browser):
    need(page.get('profile')==PROFILE,'wrong profile')
    need(page.get('caseId') in plan['cases'],'undeclared pre-red case')
    ua=page.get('userAgent','')
    family='firefox' if re.search(r'Firefox/\d',ua) else 'chrome' if re.search(r'(?:Headless)?Chrome/\d',ua) else None
    need(family==browser,'actual browser family differs')
    need(page.get('servedSources')==plan['servedSources'],'served source identity differs')
    need(page.get('artifacts')==plan['profile']['artifacts'],'actual profile/resource identity differs')
    need(page.get('configSha256')==digest(encoded(plan)),'actual config identity differs')
    need(page.get('fixtureManifestSha256')==digest(encoded(plan['fixtureManifest'])),'fixture alias manifest differs')
    need(not page.get('fatal'),'unclean page is not expected red')
    return stream(page)

def opened(page,record,plan,requests,replies):
    need(record.get('fixtureSha256')==plan['fixtureSha256'],'opened fixture identity differs')
    selected=[(k,r) for k,r in requests.items() if r['generation']==record['generation'] and
              r['message']['operation']=='open']
    need(len(selected)==1,'actual open missing/nonunique')
    key,req=selected[0]; response=replies.get(key)
    need(response is not None and response['message'].get('ok') is True,'successful open missing')
    need(response['message']['result']['documentHandle']==record['documentHandle'],'wrong open handle')
    need(req['message']['payload']['name']==record['name'],'open name differs')
    need(digest(binary(req['message']['payload']['buffer']))==plan['fixtureSha256'],'open bytes differ')
    workers=[w for w in page['workers'] if w['generation']==record['generation']]
    need(len(workers)==1 and workers[0]['url'].endswith('/profiles/'+PROFILE+'/sdk-worker.js'),'wrong actual worker')
    return record['documentHandle'],record['generation']

def bound_state(page,name,value,requests,replies):
    call,req,res=call_binding(page,name,'editorGetStateV2',requests,replies)
    need(call['result']==value==res['message']['result'],'state is not the actual V2 reply')
    need(value.get('documentHandle')==req['message']['payload']['documentHandle'],'state belongs to another document')
    return req,res

def bound_save(page,name,saved,requests,replies):
    call,req,res=call_binding(page,name,'save',requests,replies)
    raw=binary(res['message']['result']['buffer'])
    need(digest(raw)==saved['sha256'],'save not bound to actual wire bytes')
    need(binary(call['result']['bytes'])==raw,'public saved result differs')
    return paragraphs(saved)

def validate_setup(page,prefix,setup,plan,requests,replies):
    need(setup['plan']==plan,'setup discovery differs')
    _,search_req,search_res=call_binding(page,prefix+'-search','search',requests,replies)
    need(search_req['message']['payload']['query']==plan['query'],'setup search query differs')
    coordinates=list(map(int,search_res['message']['result']['selections'][0]['rectangles'].split(';')[0].split(',')))
    need(len(coordinates)==4,'actual search rectangle absent')
    _,click_req,_=call_binding(page,prefix+'-search-click','click',requests,replies)
    payload=click_req['message']['payload']
    need((payload['xTwips'],payload['yTwips'])==(coordinates[0],coordinates[1]+coordinates[3]//2),
         'setup point not derived from actual search')
    text_start=plan.get('anchor')=='search-text-start'
    moves=[] if text_start else [(prefix+'-home','move-line-home')]
    if isinstance(plan['offset'],int):moves += [(prefix+'-right-'+str(i),'move-character-right') for i in range(plan['offset'])]
    else:
        moves.append((prefix+'-end','move-line-end'))
        if plan['offset']=='next-empty':moves.append((prefix+'-next-empty','move-character-right'))
    order=[prefix+'-search',prefix+'-search-click']
    if not text_start:order.append(prefix+'-home')
    order.append(prefix+'-start-state')
    order += [name for name,_ in (moves if text_start else moves[1:])]
    order += [prefix+'-target-state',prefix+'-prefix-select',prefix+'-prefix-text',prefix+'-restore-point',prefix+'-final-state']
    previous=-1
    for name in order:
        entries=[c for c in page['calls'] if c['name']==name]
        need(len(entries)==1 and entries[0]['startedAt']>=previous,'setup call order differs')
        previous=entries[0]['finishedAt']
    for name,action in moves:
        _,request,_=call_binding(page,name,'editorActionV2',requests,replies)
        need(request['message']['payload']['action']==action and request['message']['payload']['extendSelection'] is False,
             'setup public key sequence differs')
    for phase in ('start','target','final'):
        bound_state(page,prefix+'-'+phase+'-state',setup[phase],requests,replies)
    def point(state):
        c=state['caret'];return c['x'],c['y']+c['height']//2
    if text_start:
        need(not any(c['name']==prefix+'-home' for c in page['calls']),'unplanned Home at text-start anchor')
        need((setup['start']['caret']['x'],setup['start']['caret']['y'])==(coordinates[0],coordinates[1]),
             'list anchor is not actual search text start')
        need(setup['start']['selection']['collapsed'] is True,'list text-start is not collapsed')
    a,b=point(setup['start']),point(setup['target'])
    _,selection,_=call_binding(page,prefix+'-prefix-select','editorSelectRangeV2',requests,replies)
    payload=selection['message']['payload']
    need((payload['startXTwips'],payload['startYTwips'],payload['endXTwips'],payload['endYTwips'])==(*a,*b),
         'prefix selected different points')
    _,_,selected=call_binding(page,prefix+'-prefix-text','getSelection',requests,replies)
    need(setup['selected']==selected['message']['result'],'setup text is not actual selection')
    _,restored,_=call_binding(page,prefix+'-restore-point','click',requests,replies)
    need((restored['message']['payload']['xTwips'],restored['message']['payload']['yTwips'])==b,
         'setup restoration uses different point')
    need(setup['final']['caret']==setup['target']['caret'],'setup caret not restored')


def mutation_closure(page,requests,plan):
    # Product paints/observers may run automatically; state-changing operations
    # must belong to the fixed setup, readiness key or measured Shift calls.
    mutations={'click','editorSelectRangeV2','editorActionV2','insertText'}
    passive={'init','open','close','paint','search','getSelection','editorGetStateV2','save'}
    allowed={'measured-shift'}
    for prefix,discovery in [('readiness',{'offset':0}),('measured',plan['cases'][page['caseId']]['discovery'])]:
        allowed.update(prefix+'-'+suffix for suffix in ('search-click','prefix-select','restore-point'))
        if discovery.get('anchor')!='search-text-start':allowed.add(prefix+'-home')
        if isinstance(discovery['offset'],int):allowed.update(prefix+'-right-'+str(i) for i in range(discovery['offset']))
        else:
            allowed.add(prefix+'-end')
            if discovery['offset']=='next-empty':allowed.add(prefix+'-next-empty')
    for request in requests.values():
        operation=request['message']['operation']
        need(operation in mutations|passive,'unplanned public operation '+operation)
        if operation=='insertText':continue  # Bound uniquely by readiness; forbidden in the measured generation below.
        if operation in mutations:
            calls=[c for c in page['calls'] if c['generation']==request['generation'] and
                   c['startedAt']<=request['at']<=c['finishedAt']]
            need(len(calls)==1,'mutation outside a declared call')
            name=calls[0]['name'];payload=request['message']['payload']
            need(name in allowed,'undeclared setup/measurement mutation')
            if operation=='editorActionV2':
                if name=='measured-shift':continue
                need(re.fullmatch(r'(readiness|measured)-(home|end|next-empty|right-\d+)',name) is not None,
                     'unplanned setup action')
                need(payload['extendSelection'] is False and payload['action'] in
                     ('move-line-home','move-line-end','move-character-right'),'unplanned state-changing action')
            elif operation=='click':need(name.endswith(('-search-click','-restore-point')),'unplanned click')
            else:need(name.endswith('-prefix-select'),'unplanned range selection')

def readiness(page,plan,browser):
    requests,replies=binding(page,plan,browser)
    ready=page.get('readiness',{})
    handle,gen=opened(page,ready['open'],plan,requests,replies)
    validate_setup(page,'readiness',ready['setup'],{'query':plan['fixtureParagraphs'][0],'paragraph':0,'offset':0},requests,replies)
    mutation_closure(page,requests,plan)
    bound_state(page,'readiness-before-state',ready['beforeState'],requests,replies)
    bound_state(page,'readiness-after-state',ready['afterState'],requests,replies)
    original=bound_save(page,'readiness-before-save',ready['beforeSave'],requests,replies)
    after=bound_save(page,'readiness-after-save',ready['afterSave'],requests,replies)
    need(original==plan['fixtureParagraphs'],'readiness loaded document differs')
    expected=original.copy();expected[0]='Z'+expected[0]
    need(after==expected,'actual readiness edit absent/wrong saved insertion')
    sink=ready['beforeInput']
    need(sink.get('id')=='sink' and sink.get('active') is True and sink.get('connected') is True
         and sink.get('disabled') is False and sink.get('readOnly') is False
         and sink.get('documentHandle')==handle and sink.get('generation')==gen,'readiness product sink unavailable')
    inputs=[e for e in page['inputs'] if e['type']=='beforeinput' and e.get('inputType')=='insertText'
            and e.get('data')=='Z' and e.get('isTrusted') is True and e['sink']==sink]
    keys=[e for e in page['inputs'] if e['type']=='keydown' and e.get('key')=='Z' and e.get('isTrusted') is True]
    need(len(inputs)==1 and len(keys)==1,'actual browser readiness key/beforeinput absent')
    mutations=[(key,r) for key,r in requests.items() if r['generation']==gen and r['message']['operation']=='insertText']
    need(len(mutations)==1 and sum(r['message']['operation']=='insertText' for r in requests.values())==1,
         'readiness mutation missing/nonunique or extra-generation mutation')
    key,req=mutations[0];reply=replies.get(key)
    need(req['message']['payload']=={'documentHandle':handle,'text':'Z'},'wrong readiness mutation')
    need(reply is not None and reply['message'].get('ok') is True,'readiness mutation refused')
    need(inputs[0]['at']<=req['at']<=reply['at'],'readiness input/wire order differs')
    need(ready['afterState']['revision']>ready['beforeState']['revision'],'readiness revision did not advance')
    return requests,replies

def s2_compare(reply,readback,active):
    """Reusable S2 semantic comparison; capture full states outside this projection."""
    need(reply.get('changed') is False and reply.get('revision')==reply.get('beforeRevision'),
         'move changed document/revision')
    need(isinstance(reply.get('state'),dict) and isinstance(readback,dict),'move/state absent')
    need(active.get('selectionType') in ('none','text','complex'),'active selection type unavailable')
    stale_fields=[key for key in ('caret','selection') if reply['state'].get(key)!=readback.get(key)]
    collapsed=reply['state'].get('selection',{}).get('collapsed')
    need(type(collapsed) is bool,'reply collapsed status absent')
    if collapsed != (active['selectionType']=='none'): stale_fields.append('active-selection-type')
    return stale_fields

def inspect(page,plan,browser):
    try:
        requests,replies=readiness(page,plan,browser)
        need(page.get('complete'),'incomplete measured page')
        measured=page['measured'];old=page['readiness']['open']
        handle,gen=opened(page,measured['open'],plan,requests,replies)
        need(gen!=old['generation'] and measured['open']['serial']>old['serial'],'fresh original document absent')
        need({w['generation'] for w in page['workers']}=={old['generation'],gen} and len(page['workers'])==2,
             'unexpected worker/recovery generation')
        need(sum(r['message']['operation']=='open' for r in requests.values())==2,'extra/missing document open')
        need(bound_save(page,'measured-original-save',measured['originalSave'],requests,replies)==plan['fixtureParagraphs'],
             'measured original fixture contains readiness edit/drift')
        expected=plan['cases'][page['caseId']]
        setup=measured['setup'];validate_setup(page,'measured',setup,expected['discovery'],requests,replies)
        need(not any(r['generation']==gen and r['message']['operation']=='insertText' for r in requests.values()),
             'unplanned measured text mutation')
        prefix=setup['selected'].get('text','');discovery=expected['discovery'];offset=discovery['offset']
        want=discovery['query'][:offset] if isinstance(offset,int) else discovery['query']+'\n' if offset=='next-empty' else discovery['query']
        if offset=='visual-end': need(bool(prefix) and discovery['query'].startswith(prefix),'wrapped prefix is not fixture text')
        else: need(prefix==want,'actual setup text differs from logical point')
        need(setup['final']['caret']==setup['target']['caret'],'setup did not restore actual measured point')
        need(measured['before']['selection']['collapsed'] is True,'pre-red origin is not caret')
        before_req,before_res=bound_state(page,'measured-before-state',measured['before'],requests,replies)
        final_call=next(c for c in page['calls'] if c['name']=='measured-final-state')
        need(before_req['at']>=final_call['finishedAt'],'before state precedes setup')
        call,req,res=call_binding(page,'measured-shift','editorActionV2',requests,replies)
        need(req['at']>=before_res['at'],'Shift precedes precondition state')
        need(req['message']['payload']['action']==expected['action'] and req['message']['payload']['extendSelection'] is True,
             'actual public Shift dispatch absent/wrong')
        need(req['generation']==gen and req['message']['payload']['documentHandle']==handle,'measured dispatch stale document')
        need(call['result']==measured['reply']==res['message']['result'],'move reply not bound to terminal')
        need(measured['reply'].get('action')==expected['action'],'reply action differs')
        need(measured['reply']['beforeRevision']==measured['before']['revision'],'move precondition revision differs')
        readreq,readres=bound_state(page,'measured-readback',measured['readback'],requests,replies)
        need(readreq['at']-res['at']>=500,'engine readback was too early')
        need(measured['readback']['revision']==measured['reply']['revision'],'delayed revision differs')
        _,active_req,active_res=call_binding(page,'measured-active-selection','getSelection',requests,replies)
        need(measured['activeSelection']==active_res['message']['result'],'active selection not wire result')
        need(active_req['at']>=readres['at'],'active selection precedes delayed state')
        _,_,closed=call_binding(page,'measured-close','close',requests,replies)
        stale=s2_compare(measured['reply'],measured['readback'],measured['activeSelection'])
        late=[e for e in page['events'] if e['generation']==gen and readres['at']<e['at']<=closed['at']
              and e['message'].get('event') in ('editor-state','document-invalidated')]
        return {'verdict':'EXPECTED_RED' if stale else 'UNEXPECTED_GREEN','staleFields':stale,
                'terminalCount':1,'readbackDelayMs':readreq['at']-res['at'],'lateCursorObservations':late}
    except (NotEstablished,KeyError,ValueError,TypeError,zipfile.BadZipFile) as error:
        return {'verdict':'NOT_ESTABLISHED','reason':str(error)}

def judge(cells,plan):
    wanted={(b,c) for b in BROWSERS for c in plan['cases']};seen=set();hashes=set();rows=[]
    for cell in cells:
        key=(cell['browser'],cell['caseId']);page=cell.get('page') or {}
        ph=digest(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
        if key in seen or ph in hashes:
            rows.append({'cell':key,'verdict':'NOT_ESTABLISHED','reason':'duplicate cell/actual page'});continue
        seen.add(key);hashes.add(ph)
        value=inspect(page,plan,cell['browser']) if not cell.get('fatal') and page.get('caseId')==cell['caseId'] else {'verdict':'NOT_ESTABLISHED','reason':cell.get('fatal') or 'actual case label differs'}
        rows.append({'cell':key,**value})
    verdict='EXPECTED_RED' if seen==wanted and len(rows)==len(wanted) and all(r['verdict']=='EXPECTED_RED' for r in rows) else 'UNEXPECTED_GREEN' if any(r['verdict']=='UNEXPECTED_GREEN' for r in rows) else 'NOT_ESTABLISHED'
    return {'verdict':verdict,'populationComplete':seen==wanted and len(rows)==len(wanted),'cells':len(rows),'results':rows,
            'featureS1S5Acceptance':'NOT_ESTABLISHED: this instrument implements v19 S2 pre-red only'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path)
    parser.add_argument('--v19-wasm-sha256',required=True);args=parser.parse_args()
    report=json.loads(args.report.read_text());actual=config(args.v19_wasm_sha256)
    need(report['config']==actual,'actual pinned graph/config differs')
    need(report.get('postConfig')==actual,'post-run identity absent/different')
    need(not report.get('preparationOnly'),'filtered preparations do not satisfy full pre-red')
    verify_mirror(args.report.parent/'mirror',actual)
    cells=[]
    for record in report['runs']:
        raw=(args.report.parent/record['path']).read_bytes();need(digest(raw)==record['sha256'],'cell bytes changed');cells.append(json.loads(raw))
    result=judge(cells,actual);print(json.dumps(result,indent=2));return 0 if result['verdict']=='EXPECTED_RED' else 1
if __name__=='__main__':raise SystemExit(main())
