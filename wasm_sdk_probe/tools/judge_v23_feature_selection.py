#!/usr/bin/env python3
"""Independent raw-artifact reader for fixed public ABI6 S1/S2/S3 observations."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v23_feature_selection_cases import config,encoded,digest,verify_mirror,BROWSERS,PROFILE
from judge_v23_feature_pre_red import (NotEstablished,need,stream,call_binding,bound_state,bound_save,
                                     binary,s2_compare,wrap_first_rectangle)


class ProductFailure(ValueError):pass

def contradict(value,message):
    if not value:raise ProductFailure(message)


def xy(value):
    need(isinstance(value,dict) and all(type(value.get(k)) in (int,float) for k in ('x','y')),'actual coordinate missing')
    return value['x'],value['y']

def point(value):return {'xTwips':value['x'],'yTwips':value['y']+int(value['height']//2)}

def request_key(item):return item['generation'],item['message']['requestId']

# NarrowEditorV2Session.placeCaret (finding 140) picks its wire route from its own
# first state read: an open range posts `click`, a collapsed caret posts
# `editorPlaceCaretV2`.  The v19 pre-red route this reader came from had only
# `click`; selection-prep-01 is the ABI6 counterexample.
PLACE_OPS=('click','editorPlaceCaretV2')
MUTATION_OPS=PLACE_OPS+('editorActionV2','editorSelectRangeV2')

def place_route(requests,replies,generation):
    """The route the product chose, from the raw reply to its first in-call state read."""
    reads=[r for r in requests if r['generation']==generation and r['message']['operation']=='editorGetStateV2']
    routed=[r for r in requests if r['generation']==generation and r['message']['operation'] in PLACE_OPS]
    need(reads and len(routed)==1 and reads[0]['at']<=routed[0]['at'],'placeCaret route witness absent/nonunique')
    t=replies.get(request_key(reads[0]));need(t is not None and t['message'].get('ok') is True,'placeCaret state read refused')
    collapsed=(t['message'].get('result') or {}).get('selection',{}).get('collapsed')
    need(type(collapsed) is bool,'placeCaret route state absent')
    need(routed[0]['message']['operation']==('editorPlaceCaretV2' if collapsed else 'click'),'placeCaret route differs from its own state read')
    return routed[0]['message']['operation']

class Evidence:
    def __init__(self,page,plan,browser):
        self.page,self.plan=page,plan;self.used=set();self.mutations=set();self.call_order=[]
        need(page.get('profile')==PROFILE,'wrong feature profile')
        need(page.get('caseId') in plan['cases'],'undeclared source case')
        ua=page.get('userAgent','')
        actual='firefox' if re.search(r'Firefox/[0-9]',ua) else 'chrome' if re.search(r'(?:Headless)?Chrome/[0-9]',ua) else None
        need(actual==browser,'actual UA family differs')
        need(page.get('servedSources')==plan['servedSources'],'executed source differs')
        need(page.get('artifacts')==plan['profile']['artifacts'],'fetched feature identity differs')
        need(page.get('configSha256')==digest(encoded(plan)),'config identity differs')
        need(page.get('fixtureManifestSha256')==digest(encoded(plan['fixtureManifest'])),'fixture alias differs')
        need(not page.get('fatal'),'unclean observation')
        self.requests,self.replies=stream(page)
    def call(self,name,op):
        need(name not in self.used,'reused call evidence');self.used.add(name);self.call_order.append(name)
        c,r,t=call_binding(self.page,name,op,self.requests,self.replies)
        if op in MUTATION_OPS:self.mutations.add(request_key(r))
        return c,r,t
    def place(self,name):
        calls=[c for c in self.page['calls'] if c['name']==name]
        need(len(calls)==1 and type(calls[0].get('requestStart')) is int and type(calls[0].get('requestEnd')) is int,'missing/refused public call '+name)
        c=calls[0];return self.call(name,place_route(self.page['requests'][c['requestStart']:c['requestEnd']],self.replies,c['generation']))
    def state(self,name,value):
        c,r,t=self.call(name,'editorGetStateV2')
        need(c['result']==value==t['message']['result'],'state not actual wire result')
        return r,t
    def text(self,name,value):
        c,r,t=self.call(name,'getSelection');need(c['result']==value==t['message']['result'],'selection not actual wire result');return r,t
    def save(self,name,value):
        self.used.add(name)
        return bound_save(self.page,name,value,self.requests,self.replies)
    def opened(self,record):
        need(record['fixtureSha256']==self.plan['fixtureSha256'],'opened fixture differs')
        matches=[r for r in self.requests.values() if r['generation']==record['generation'] and r['message']['operation']=='open']
        need(len(matches)==1,'actual fresh open absent/nonunique');r=matches[0];t=self.replies.get(request_key(r))
        need(t and t['message'].get('ok') is True,'open refused')
        need(t['message']['result']['documentHandle']==record['documentHandle'],'open handle differs')
        need(digest(binary(r['message']['payload']['buffer']))==self.plan['fixtureSha256'],'wire open bytes differ')
        need(r['message']['payload']['name']==record['name'],'wire filename differs')
        workers=[w for w in self.page['workers'] if w['generation']==record['generation']]
        need(len(workers)==1 and workers[0]['url'].endswith('/profiles/'+PROFILE+'/sdk-worker.js'),'actual worker differs')
        return record['generation'],record['documentHandle']
    def locate(self,prefix,record,plan):
        order_start=len(self.call_order)
        need(record['plan']==plan,'logical discovery input differs')
        _,r,t=self.call(prefix+'-search','search');need(r['message']['payload']['query']==plan['query'],'query differs')
        first=wrap_first_rectangle(t['message']['result'])
        raw_boxes=sorted([list(map(int,x.split(','))) for x in t['message']['result']['selections'][0]['rectangles'].split(';')],key=lambda r:(r[1],r[0]))
        need(record.get('boxes')==raw_boxes,'unbound page search boxes')
        _,r,_=self.place(prefix+'-search-click')
        need(r['message']['payload']['xTwips']==first[0] and r['message']['payload']['yTwips']==first[1]+first[3]//2,'actual text-start click differs')
        if plan['anchor']=='search-first-displayed-line':self.move(prefix+'-home','move-line-home',False)
        self.state(prefix+'-start-state',record['start'])
        need(xy(record['start']['caret'])==first[:2],'actual text start caret differs')
        offset=plan['offset']
        if type(offset) is int:
            for n in range(offset):self.move(prefix+'-right-'+str(n),'move-character-right',False)
        else:
            self.move(prefix+'-end','move-line-end',False)
            if offset=='next-empty':self.move(prefix+'-next-empty','move-character-right',False)
        self.state(prefix+'-target-state',record['target'])
        self.selection(prefix+'-prefix-select',record['start']['caret'],record['target']['caret'])
        self.text(prefix+'-prefix-text',record['selected'])
        text=record['selected']['text']
        if 'prefix' in plan:need(text==plan['prefix'],'actual logical prefix differs')
        elif offset=='visual-end':need(bool(text) and plan['query'].startswith(text) and record['target']['caret']['y']==first[1],'first visual-line prefix differs')
        else:need(text=='','nonempty start prefix')
        _,r,_=self.place(prefix+'-restore-point');p=point(record['target']['caret'])
        need(all(r['message']['payload'][k]==v for k,v in p.items()),'restore coordinates differ')
        self.state(prefix+'-final-state',record['final'])
        need(record['final']['caret']==record['target']['caret'] and record['final']['selection']['collapsed'] is True,'point not restored')
        expected_order=self.call_order[order_start:]
        need([c['name'] for c in self.page['calls'] if c['name'] in expected_order]==expected_order,'point discovery call order differs')
        return record['final']['caret']
    def selection(self,name,a,b):
        _,r,_=self.call(name,'editorSelectRangeV2');payload=r['message']['payload']
        want={'startXTwips':point(a)['xTwips'],'startYTwips':point(a)['yTwips'],'endXTwips':point(b)['xTwips'],'endYTwips':point(b)['yTwips']}
        need(all(payload[k]==v for k,v in want.items()),'text-handle coordinates differ')
    def move(self,name,action,shift):
        c,r,t=self.call(name,'editorActionV2');p=r['message']['payload']
        need(p['action']==action and p.get('extendSelection',False) is shift,'actual action/extension differs')
        need(c['result']==t['message']['result'],'public result differs from wire terminal')
        return c,r,t
    def key(self,name,key,shift):
        c,r,t=self.move(name,key['action'],shift)
        expected=key['productKey']['key']
        arms=[a for a in self.page['keyArms'] if a['name']==name]
        need(len(arms)==1,'product input arm absent/duplicate');arm=arms[0]
        start,end=arm['inputStart'],arm['inputEnd']
        need(type(start) is int and type(end) is int and 0<=start<end<=len(self.page['inputs']),'input arm bounds invalid')
        inputs=[x for x in self.page['inputs'][start:end] if x['type']=='keydown' and x.get('key')!='Shift']
        need(len(inputs)==1 and inputs[0].get('key')==expected and arm['generation']==r['generation']
             and arm['at']<=inputs[0]['at']<=c['startedAt']<=r['at'],'actual product input ownership differs')
        need(inputs,'actual product key missing');event=inputs[-1]
        need(event.get('isTrusted') is True and event.get('shiftKey') is shift and not any(event.get(k) for k in ('ctrlKey','altKey','metaKey','repeat')),'wrong actual product key')
        sink=event.get('sink',{});need(sink.get('active') and sink.get('connected') and not sink.get('disabled') and not sink.get('readOnly'),'key not in editable focused sink')
        need(sink['documentHandle']==r['message']['payload']['documentHandle'],'key document differs')
        return c,r,t
    def closure(self):
        need({c['name'] for c in self.page['calls']}==self.used and len(self.page['calls'])==len(self.used),'unplanned/duplicate public call')
        for k,r in self.requests.items():
            op=r['message']['operation']
            # pageRectangles: the shell76 page-count scheduler's per-open read (getPartPageRectangles,
            # getDocumentSize, getParts in handlePageRectangles); shell57 under v19 never sent it.
            need(op in {'init','open','close','paint','pageRectangles','search','getSelection','editorGetStateV2','save','insertText',*MUTATION_OPS},'unplanned wire operation')
            if op in MUTATION_OPS:need(k in self.mutations,'unowned wire mutation')

def readiness(e):
    p=e.page;v=p['readiness'];gen,handle=e.opened(v['open'])
    e.locate('readiness',v['setup'],e.plan['readinessPoint'])
    e.state('readiness-before-state',v['beforeState']);e.state('readiness-after-state',v['afterState'])
    before=e.save('readiness-before-save',v['beforeSave']);after=e.save('readiness-after-save',v['afterSave'])
    expected=e.plan['fixtureParagraphs'];need(before==expected,'readiness original differs');changed=expected.copy();changed[0]='Z'+changed[0]
    need(after==changed,'actual readiness save mutation missing')
    mutations=[r for r in e.requests.values() if r['message']['operation']=='insertText']
    need(len(mutations)==1,'readiness mutation absent/extra')
    r=mutations[0];need(r['generation']==gen and r['message']['payload']=={'documentHandle':handle,'text':'Z'},'readiness wire mutation differs')
    need(e.replies[request_key(r)]['message'].get('ok') is True,'readiness mutation refused')
    inputs=[x for x in p['inputs'] if x['type']=='beforeinput' and x.get('inputType')=='insertText' and x.get('data')=='Z' and x.get('isTrusted') is True]
    need(len(inputs)==1 and inputs[0]['at']<=r['at'],'actual readiness beforeinput missing')
    keys=[x for x in p['inputs'] if x['type']=='keydown' and x.get('key')=='Z' and x.get('isTrusted') is True]
    need(len(keys)==1 and keys[0]['at']<=inputs[0]['at'],'actual readiness Z key absent')
    sink=inputs[0]['sink'];need(sink.get('active') and sink.get('connected') and not sink.get('readOnly') and not sink.get('disabled'),'readiness sink unavailable')
    need(v['afterState']['revision']>v['beforeState']['revision'],'readiness revision unchanged')
    return gen

def endpoint_pair(selection,anchor,moving,measured=False):
    """LOK start/end are not named anchor/end; require a unique geometric pairing."""
    need(selection.get('observed') is True,'selection unobserved')
    check=contradict if measured else need
    if selection.get('collapsed') is True:
        check(anchor==moving,'collapsed selection with distinct logical endpoints');return
    need(selection.get('collapsed') is False,'collapsed status absent')
    points=[xy(selection.get('start')),xy(selection.get('end'))]
    check(anchor!=moving and points.count(anchor)==1 and points.count(moving)==1,'anchor/moving endpoints not uniquely witnessed')

def setup(e,name,row):
    v=e.page[name];gen,handle=e.opened(v['open'])
    need(e.save(name+'-original-save',v['originalSave'])==e.plan['fixtureParagraphs'],'fresh original differs')
    need(set(v['points'])==set(row['pointPlans']),'point discovery population differs')
    for pointname,plan in row['pointPlans'].items():e.locate(name+'-point-'+pointname,v['points'][pointname],plan)
    anchor=v['points'][row['anchorPointName']]['final']['caret'];moving=v['points'][row['movingPointName']]['final']['caret']
    origin=moving if name=='reference' else anchor
    if name=='reference' or row['nativeSetupMethod']!='drag':
        _,r,_=e.place(name+'-origin-click');need(all(r['message']['payload'][k]==z for k,z in point(origin).items()),'shape origin differs')
    else:
        start,end=v['requestStart'],v['requestEnd']
        need(type(start) is int and type(end) is int and 0<=start<end<=len(e.page['requests']),'drag request bounds invalid')
        requests=[r for r in e.page['requests'][start:end] if r['generation']==gen and r['message']['operation']=='editorSelectRangeV2']
        need(requests,'actual drag wire absent')
        inputs=e.page['inputs'][v['inputStart']:v['inputEnd']]
        pointers=[x for x in inputs if x['type'] in ('pointerdown','pointermove','pointerup')]
        need(pointers and all(x.get('isTrusted') is True for x in pointers),'actual trusted drag absent')
        down=[x for x in pointers if x['type']=='pointerdown'];up=[x for x in pointers if x['type']=='pointerup']
        need(len(down)==len(up)==1 and down[0]['at']<up[0]['at'],'drag direction evidence absent')
        openreq=next(r for r in e.requests.values() if r['generation']==gen and r['message']['operation']=='open')
        metadata=e.replies[request_key(openreq)]['message']['result']
        # Literal frozen page pointToTwips projection; no added pixel tolerance.
        def projected(event):
            rect=event['paper'];size=event['size']
            need(size=={'w':metadata['width'],'h':metadata['height']},'pointer document geometry differs')
            return {'xTwips':max(0,math.floor((event['clientX']-rect['left'])/rect['width']*size['w']+0.5)),
                    'yTwips':max(0,math.floor((event['clientY']-rect['top'])/rect['height']*size['h']+0.5))}
        for event,caret in ((down[0],anchor),(up[0],moving)):
            rect=event['paper'];size=event['size'];p=point(caret)
            wanted=(round(rect['left']+rect['width']*p['xTwips']/size['w']),round(rect['top']+rect['height']*p['yTwips']/size['h']))
            need((event['clientX'],event['clientY'])==wanted,'actual pointer endpoint differs')
        a,b=projected(down[0]),projected(up[0])
        allowed_ends=[projected(x) for x in pointers]
        for r in requests:
            payload=r['message']['payload']
            need(payload['startXTwips']==a['xTwips'] and payload['startYTwips']==a['yTwips'],'drag anchor differs')
            need({'xTwips':payload['endXTwips'],'yTwips':payload['endYTwips']} in allowed_ends,'drag endpoint without actual pointer')
            e.mutations.add(request_key(r))
        payload=requests[-1]['message']['payload'];need(payload['endXTwips']==b['xTwips'] and payload['endYTwips']==b['yTwips'],'drag final endpoint differs')
        route=place_route(e.page['requests'][start:end],e.replies,gen)
        clicks=[r for r in e.page['requests'][start:end] if r['generation']==gen and r['message']['operation']==route]
        need(len(clicks)==1 and all(clicks[0]['message']['payload'][k]==z for k,z in a.items()),'drag initial click differs');e.mutations.add(request_key(clicks[0]))
    if name=='candidate' and row['nativeSetupMethod']=='click+Shift+Right x3':
        right={**row,'action':'move-character-right','productKey':{'key':'ArrowRight'}}
        for n in range(3):e.key('candidate-setup-shift-'+str(n),right,True)
    if name=='candidate' and row['nativeSetupMethod']=='click+End':
        e.key('candidate-setup-end',{**row,'action':'move-line-end','productKey':{'key':'End'}},False)
    e.state(name+'-setup-state',v['setupState']);e.text(name+'-setup-text',v['setupSelection'])
    want='' if name=='reference' else row['setup']['expectedSelection']
    need(v['setupSelection']['text']==want,'actual native setup text differs')
    need(v['setupState']['selection']['collapsed'] is (name=='reference' or not row['setup']['expectRange']),'actual native setup shape differs')
    need(xy(v['setupState']['caret'])==xy(moving),'actual moving point differs')
    if name=='candidate' and row['setup']['expectRange']:endpoint_pair(v['setupState']['selection'],xy(anchor),xy(moving))
    _,before=e.state(name+'-before-state',v['before'])
    need(v['before']['caret']==v['setupState']['caret'] and v['before']['selection']==v['setupState']['selection'],'shape changed before measured key')
    return gen,handle,anchor,moving,before

def arm(e,name,row):
    v=e.page[name];gen,handle,anchor,moving,before=setup(e,name,row)
    c,r,t=e.key(name+'-move',row,row['extendSelection'] if name=='candidate' else False)
    need(r['generation']==gen and r['message']['payload']['documentHandle']==handle and r['at']>=before['at'],'measured key ownership/order differs')
    need(v['reply']==c['result']==t['message']['result'],'actual measured reply differs')
    bad=[]
    need(type(v['reply'].get('changed')) is bool and all(type(v['reply'].get(k)) is int for k in ('revision','beforeRevision')),'move accounting witness missing')
    if v['reply']['beforeRevision']!=v['before']['revision']:bad.append('before-revision')
    if v['reply']['changed'] is not False:bad.append('changed')
    if v['reply']['revision']!=v['reply']['beforeRevision']:bad.append('revision')
    rr,rt=e.state(name+'-readback',v['readback']);need(rr['at']-t['at']>=500,'readback too early')
    if v['readback']['revision']!=v['reply']['revision']:bad.append('delayed-revision')
    ar,_=e.text(name+'-active-selection',v['activeSelection']);need(ar['at']>=rt['at'],'active selection precedes delayed state')
    for request in e.requests.values():
        if request['generation']==gen and before['at']<request['at']<=ar['at'] and request['message']['operation'] in MUTATION_OPS+('insertText',):
            need(request_key(request)==request_key(r),'unplanned mutation between precondition and delayed read')
    comparison={**v['reply'],'changed':False,'revision':v['reply']['beforeRevision']}
    stale=s2_compare(comparison,v['readback'],v['activeSelection'])+bad
    return {'generation':gen,'anchor':anchor,'moving':moving,'stale':stale,'readbackAt':rt['at'],
            'readbackDelayMs':rr['at']-t['at'],'terminal':t}

def logical_endpoint(e):
    ref=e.page['reference'];need(ref['endpoint']==ref['readback']['caret'],'reference endpoint not actual readback')
    rows=ref['mapping'];need([r['paragraph'] for r in rows]==list(range(len(e.plan['fixtureParagraphs']))),'mapping population differs')
    candidates=[];endpoint=ref['endpoint']
    for r,plan in zip(rows,e.plan['mappingPoints']):
        prefix='reference-map-'+str(r['paragraph']);origin=e.locate(prefix,r['origin'],plan)
        # Parse every raw wire rectangle independently; never trust page boxes.
        _,_,terminal=call_binding(e.page,prefix+'-search','search',e.requests,e.replies)
        result=terminal['message']['result'];wrap_first_rectangle(result)
        boxes=[tuple(map(int,x.split(','))) for x in result['selections'][0]['rectangles'].split(';')]
        query=e.plan['fixtureParagraphs'][r['paragraph']]
        eligible=xy(origin)==xy(endpoint) if not query else any(x<=endpoint['x']<=x+w and y<=endpoint['y']<=y+h for x,y,w,h in boxes)
        if eligible:candidates.append((r,origin))
    need(len(candidates)==1,'independent logical endpoint geometry missing/ambiguous')
    chosen,origin=candidates[0];mapping=ref['endpointMapping'];paragraph=chosen['paragraph']
    need(mapping['paragraph']==paragraph,'endpoint paragraph not independently derived')
    prefix='reference-map-'+str(paragraph)
    e.selection(prefix+'-endpoint-select',origin,endpoint);e.text(prefix+'-endpoint-text',mapping['selected'])
    text=mapping['selected']['text'];query=e.plan['fixtureParagraphs'][paragraph]
    need(isinstance(text,str) and query.startswith(text),'logical endpoint prefix differs')
    need((endpoint['y'],endpoint['x']) >= (origin['y'],origin['x']),'prefix endpoint precedes text start')
    return paragraph,len(text)


def inspect(page,plan,browser):
    groups={'S1':{'verdict':'NOT_APPLICABLE'},'S2':{'verdict':'NOT_ESTABLISHED'},'S3':{'verdict':'NOT_APPLICABLE'}}
    try:
        e=Evidence(page,plan,browser);row=plan['cases'][page['caseId']]
        for group in ('S1','S3'):
            if group in row['memberships']:groups[group]={'verdict':'NOT_ESTABLISHED'}
        g=readiness(e);reference=arm(e,'reference',row);logical=logical_endpoint(e)
        _,_,refclose=e.call('reference-close','close')
        candidate=arm(e,'candidate',row);_,_,close=e.call('candidate-close','close')
        need(page.get('complete'),'incomplete page')
        need(len({g,reference['generation'],candidate['generation']})==3 and len(page['workers'])==3,'fresh arms/recovery generation differs')
        need(len([r for r in e.requests.values() if r['message']['operation']=='open'])==3,'extra/missing open')
        e.closure()
        need(not reference['stale'],'independent control reply stale')
        late=[x for x in page['events'] if x['generation']==candidate['generation'] and candidate['readbackAt']<x['at']<=close['at'] and x['message'].get('event') in ('editor-state','document-invalidated')]
        groups['S2']={'verdict':'FAIL' if candidate['stale'] else 'PASS','staleFields':candidate['stale'],
                      'readbackDelayMs':candidate['readbackDelayMs'],'lateCursorObservations':late}
        current_group='S3'
        if 'S3' in row['memberships']:
            need(isinstance(page['candidate']['reply'].get('completion'),str),'completion witness missing')
            contradict(page['candidate']['reply'].get('completion')=='verified-move-readback','native-silent completion differs')
            contradict(not any(x['message'].get('event') in ('recoverable-error','worker-restart') for x in page['events']),'recovery occurred')
            groups['S3']={'verdict':'PASS'}
        current_group='S1'
        if 'S1' in row['memberships']:
            state=page['candidate']['readback'];target=page['reference']['endpoint'];anchor=candidate['anchor']
            contradict(xy(state['caret'])==xy(target),'moving endpoint differs from independent control')
            endpoint_pair(state['selection'],xy(anchor),xy(target),measured=True)
            if row['key'] in ('Left','Right'):
                contradict(all(page['candidate']['activeSelection']['text']==x for x in row['nativeAfterSelectionText']),'native literal selection differs')
            # Native Home/End parity is conditional; the independent control is always retained.
            single=True
            for pointname,observed in page['candidate']['points'].items():
                _,_,search=call_binding(page,'candidate-point-'+pointname+'-search','search',e.requests,e.replies)
                raw=search['message']['result'];first=wrap_first_rectangle(raw)
                boxes=raw['selections'][0]['rectangles'].split(';')
                single=single and len(boxes)==1 and observed['start']['caret']['y']==first[1] and observed['final']['caret']['y']==first[1]
            single=single and state['caret']['y']==candidate['moving']['y'] and target['y']==candidate['moving']['y']
            if row['key'] in ('Home','End') and single:
                contradict(all(page['candidate']['activeSelection']['text']==x for x in row['nativeAfterSelectionText']),'single-line native selection differs')
            anchorplan=row['pointPlans'][row['anchorPointName']]
            offset=anchorplan['offset'] if type(anchorplan['offset']) is int else 0 if anchorplan['offset']=='next-empty' else len(page['candidate']['points'][row['anchorPointName']]['selected']['text'])
            groups['S1']={'verdict':'PASS','logicalAnchor':[anchorplan['paragraph'],offset],'logicalEndpoint':logical,'singleLineNativeWitness':single}
        return {'verdict':'FAIL' if any(x['verdict']=='FAIL' for x in groups.values()) else 'PASS','groups':groups}
    except ProductFailure as error:
        groups[current_group]={'verdict':'FAIL','reason':str(error)}
        return {'verdict':'FAIL','reason':str(error),'groups':groups}
    except (NotEstablished,KeyError,ValueError,TypeError,IndexError) as error:
        return {'verdict':'NOT_ESTABLISHED','reason':str(error),'groups':groups}

def check_pre_red(path):
    from judge_v23_feature_pre_red import judge as historical_judge
    from v23_feature_pre_red_cases import config as historical_config,verify_mirror as historical_mirror,WASM
    need(path is not None,'complete historical pre-red reference absent')
    path=Path(path).resolve();raw=path.read_bytes();report=json.loads(raw);plan=historical_config(WASM)
    need(report.get('config')==plan and report.get('postConfig')==plan,'historical graph differs or incomplete')
    need(not report.get('preparationOnly'),'historical preparation cannot qualify')
    historical_mirror(path.parent/'mirror',plan);cells=[]
    for row in report['runs']:
        data=(path.parent/row['path']).read_bytes();need(digest(data)==row['sha256'],'historical cell bytes differ');cells.append(json.loads(data))
    result=historical_judge(cells,plan);need(result['verdict']=='EXPECTED_RED' and result['populationComplete'],'historical pre-red not complete expected red')
    return {'path':str(path),'sha256':digest(raw),'verdict':'EXPECTED_RED','cells':result['cells']}

def judge(cells,plan):
    wanted={(b,c) for b in BROWSERS for c in plan['cases']};seen=set();hashes=set();rows=[]
    for cell in cells:
        key=(cell['browser'],cell['caseId']);page=cell.get('page') or {}
        fingerprint=digest(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
        if key in seen or fingerprint in hashes or key not in wanted:
            rows.append({'cell':key,'verdict':'NOT_ESTABLISHED','reason':'duplicate/undeclared actual observation'});continue
        seen.add(key);hashes.add(fingerprint)
        value=inspect(page,plan,cell['browser']) if not cell.get('fatal') and page.get('caseId')==cell['caseId'] else {'verdict':'NOT_ESTABLISHED','reason':'unclean cell/label'}
        rows.append({'cell':key,**value})
    complete=seen==wanted and len(rows)==len(wanted)
    groups={}
    for group in ('S1','S2','S3'):
        members={(b,c) for b,c in wanted if group in plan['cases'][c]['memberships']}
        observations=[r for r in rows if tuple(r['cell']) in members]
        groups[group]={'required':len(members),'observed':len(observations),
            'verdict':'FAIL' if any(r.get('groups',{}).get(group,{}).get('verdict')=='FAIL' for r in observations) else 'PASS' if complete and len(observations)==len(members) and all(r.get('groups',{}).get(group,{}).get('verdict')=='PASS' for r in observations) else 'NOT_ESTABLISHED'}
    return {'verdict':'FAIL' if any(r['verdict']=='FAIL' for r in rows) else 'PASS' if complete and all(r['verdict']=='PASS' for r in rows) else 'NOT_ESTABLISHED',
            'populationComplete':complete,'groups':groups,'results':rows}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);args=parser.parse_args()
    report=json.loads(args.report.read_text());plan=config()
    need(report['config']==plan and report.get('postConfig')==plan,'actual instrument/source graph differs or incomplete')
    need(not report.get('preparationOnly'),'preparation cannot qualify finite population')
    need(report['preRed']==check_pre_red(report['preRed']['path']),'historical prerequisite binding differs')
    need(report['mirrorBindings']==verify_mirror(args.report.parent/'mirror',plan),'mirror receipt differs')
    cells=[]
    for item in report['runs']:
        raw=(args.report.parent/item['path']).read_bytes();need(digest(raw)==item['sha256'],'cell bytes changed');cells.append(json.loads(raw))
    result=judge(cells,plan);print(json.dumps(result,indent=2));return 0 if result['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
