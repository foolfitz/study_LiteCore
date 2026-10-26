#!/usr/bin/env python3
"""Independent raw-artifact reader for fixed public ABI6 S1/S2/S3 observations."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v23_feature_selection_cases import config,encoded,digest,verify_mirror,BROWSERS,PROFILE,ROOT
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
    collapsed=((t['message'].get('result') or {}).get('selection') or {}).get('collapsed')
    need(type(collapsed) is bool,'placeCaret route state absent')
    need(routed[0]['message']['operation']==('editorPlaceCaretV2' if collapsed else 'click'),'placeCaret route differs from its own state read')
    return routed[0]['message']['operation']

class Evidence:
    def __init__(self,page,plan,browser):
        self.page,self.plan=page,plan;self.used=set();self.mutations=set();self.call_order=[]
        need(page.get('profile')==PROFILE,'wrong feature profile')
        need(any(page.get('caseId') in plan.get(k,{}) for k in ('cases','interactions','s5')),'undeclared source case')
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
            if op=='paint' and self.replies.get(k,{}).get('message',{}).get('ok') is True:
                # The observer keeps each bitmap's length and SHA-256 (since selection-prep-05);
                # earlier preparations kept the full bytes, a superset.
                pixels=(self.replies[k]['message'].get('result') or {}).get('pixels')
                need(isinstance(pixels,dict) and type(pixels.get('bytes')) is int and (
                     pixels.get('encoding')=='sha256' and re.fullmatch(r'[0-9a-f]{64}',str(pixels.get('sha256'))) is not None
                     or pixels.get('encoding')=='base64' and isinstance(pixels.get('data'),str)),'paint digest incomplete')

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

def drag_witness(e,v,gen,anchor,moving):
    """An actual trusted pointer drag from anchor to moving, bound to its public range requests."""
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

def setup(e,name,row):
    v=e.page[name];gen,handle=e.opened(v['open'])
    need(e.save(name+'-original-save',v['originalSave'])==e.plan['fixtureParagraphs'],'fresh original differs')
    need(set(v['points'])==set(row['pointPlans']),'point discovery population differs')
    for pointname,plan in row['pointPlans'].items():e.locate(name+'-point-'+pointname,v['points'][pointname],plan)
    anchor=v['points'][row['anchorPointName']]['final']['caret'];moving=v['points'][row['movingPointName']]['final']['caret']
    origin=moving if name=='reference' else anchor
    if name=='reference' or row['nativeSetupMethod']!='drag':
        _,r,_=e.place(name+'-origin-click');need(all(r['message']['payload'][k]==z for k,z in point(origin).items()),'shape origin differs')
    else:drag_witness(e,v,gen,anchor,moving)
    # Every arm but the plain control takes the candidate shape (S5 arms s5cand/s5ref too).
    if name!='reference' and row['nativeSetupMethod']=='click+Shift+Right x3':
        right={**row,'action':'move-character-right','productKey':{'key':'ArrowRight'}}
        for n in range(3):e.key(name+'-setup-shift-'+str(n),right,True)
    if name!='reference' and row['nativeSetupMethod']=='click+End':
        e.key(name+'-setup-end',{**row,'action':'move-line-end','productKey':{'key':'End'}},False)
    e.state(name+'-setup-state',v['setupState']);e.text(name+'-setup-text',v['setupSelection'])
    want='' if name=='reference' else row['setup']['expectedSelection']
    need(v['setupSelection']['text']==want,'actual native setup text differs')
    need(v['setupState']['selection']['collapsed'] is (name=='reference' or not row['setup']['expectRange']),'actual native setup shape differs')
    need(xy(v['setupState']['caret'])==xy(moving),'actual moving point differs')
    if name!='reference' and row['setup']['expectRange']:endpoint_pair(v['setupState']['selection'],xy(anchor),xy(moving))
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


TABLE_NS='urn:oasis:names:tc:opendocument:xmlns:table:1.0'

def containers_from_xml(raw,expected):
    """Paragraph -> 'body' or [table,row,column], in paragraph_texts_from_xml order."""
    import xml.etree.ElementTree as ET
    from odt_paragraphs import PARAGRAPHS,CONTAINERS,OFFICE,_inline
    t=lambda name:'{'+TABLE_NS+'}'+name
    body=ET.fromstring(raw).find('{'+OFFICE+'}body');need(body is not None,'container fixture has no body')
    parent={child:node for node in body.iter() for child in node}
    tables=[x for x in body.iter() if x.tag==t('table')];need(tables,'container parser found no table')
    texts=[];out=[]
    for element in body.iter():
        if element.tag not in PARAGRAPHS:continue
        parts=[];_inline(element,parts);texts.append(''.join(parts))
        chain=[];node=element
        while node in parent:node=parent[node];chain.append(node)
        need(not any(x.tag in CONTAINERS for x in chain),'container parser: paragraph in note/frame/annotation not modelled')
        cells=[x for x in chain if x.tag in (t('table-cell'),t('covered-table-cell'))]
        if not cells:out.append('body');continue
        need(len(cells)==1 and cells[0].tag==t('table-cell'),'container parser: nested or covered cell not modelled')
        cell=cells[0];row=parent[cell];table=parent.get(row)
        need(row.tag==t('table-row') and table is not None and table.tag==t('table'),'container parser: row group or header rows not modelled')
        rows=[x for x in table if x.tag==t('table-row')];columns=[x for x in row if x.tag in (t('table-cell'),t('covered-table-cell'))]
        need(not any(x.get(t(a)) for x in rows+columns for a in ('number-rows-repeated','number-columns-repeated','number-columns-spanned','number-rows-spanned')),
             'container parser: repeated or spanned cell not modelled')
        out.append([tables.index(table),rows.index(row),columns.index(cell)])
    need(texts==expected,'container parser paragraph order differs')
    return out

def fixture_containers(plan):
    from v23_feature_selection_cases import FIXTURE
    raw=FIXTURE.read_bytes();need(digest(raw)==plan['fixtureSha256'],'container fixture differs')
    return containers_from_xml(raw,plan['fixtureParagraphs'])

def table_selection(containers,row,anchorname,endpoint_paragraph):
    """Fable ruling 2026-10-27 (A'): a member is a table-selection member when the plain
    control's endpoint lies in a different container than the moving point, the condition
    under which Writer itself selects cells or jumps the table (selection-prep-03/04)."""
    need(type(endpoint_paragraph) is int and 0<=endpoint_paragraph<len(containers),'reference endpoint paragraph absent')
    moving=containers[row['pointPlans'][row['movingPointName']]['paragraph']]
    need(containers[row['pointPlans'][anchorname]['paragraph']]==moving,'setup shape crosses container; no oracle')
    target=containers[endpoint_paragraph]
    return [moving,target] if moving!=target else None

def click_witness(e,v,gen,target,request):
    """One actual trusted click at the target caret, bound to the product's own placeCaret request."""
    pointers=[x for x in e.page['inputs'][v['inputStart']:v['inputEnd']] if x['type'] in ('pointerdown','pointermove','pointerup')]
    need(pointers and all(x.get('isTrusted') is True for x in pointers),'actual trusted click absent')
    down=[x for x in pointers if x['type']=='pointerdown'];up=[x for x in pointers if x['type']=='pointerup']
    need(len(down)==len(up)==1 and down[0]['at']<=up[0]['at'] and (down[0]['clientX'],down[0]['clientY'])==(up[0]['clientX'],up[0]['clientY']),'click is not one press')
    event=down[0];rect=event['paper'];size=event['size'];p=point(target)
    need((event['clientX'],event['clientY'])==(round(rect['left']+rect['width']*p['xTwips']/size['w']),round(rect['top']+rect['height']*p['yTwips']/size['h'])),'actual click point differs')
    projected={'xTwips':max(0,math.floor((event['clientX']-rect['left'])/rect['width']*size['w']+0.5)),
               'yTwips':max(0,math.floor((event['clientY']-rect['top'])/rect['height']*size['h']+0.5))}
    need(all(request['message']['payload'][k]==z for k,z in projected.items()),'click request differs from the actual pointer')
    need(event['at']<=request['at'],'click request precedes the pointer')

def interaction(e,row):
    """S4: Writer's selection after an actual public interaction that follows a Shift extension."""
    v=e.page['interaction'];gen,handle=e.opened(v['open'])
    need(e.save('interaction-original-save',v['originalSave'])==e.plan['fixtureParagraphs'],'fresh original differs')
    need(set(v['points'])==set(row['pointPlans']),'point discovery population differs')
    for name,plan in row['pointPlans'].items():e.locate('interaction-point-'+name,v['points'][name],plan)
    origin=v['points'][row['originPointName']]['final']['caret']
    _,r,_=e.place('interaction-origin-click');need(all(r['message']['payload'][k]==z for k,z in point(origin).items()),'caret-mid origin differs')
    _,before=e.state('interaction-before-state',v['before'])
    need(xy(v['before']['caret'])==xy(origin) and v['before']['selection']['collapsed'] is True,'caret-mid shape differs')
    first={**row,'action':row['firstAction'],'productKey':{'key':row['firstProductKey']['key']}}
    _,r,t=e.key('interaction-first-key',first,True);need(r['at']>=before['at'],'first key precedes its shape')
    e.state('interaction-first-state',v['firstState']);e.text('interaction-first-text',v['firstSelection'])
    need(v['firstState']['selection'].get('collapsed') is False and v['firstSelection'].get('text'),'Shift extension before the interaction absent')
    texts=row['nativeAfterStepText'];need(isinstance(texts,list) and len(texts)==3 and len(set(texts))==1,'native interaction oracle disagrees')
    points=[v['points'][n]['final']['caret'] for n in row['logicalPointNames']]
    if row['method']=='click':
        _,step,_=e.place('interaction-step-click');click_witness(e,v,gen,points[0],step)
    elif row['method']=='drag':drag_witness(e,v,gen,points[0],points[1])
    else:e.selection('interaction-select-range',points[0],points[1])
    e.state('interaction-step-state',v['stepState']);e.text('interaction-step-text',v['stepSelection'])
    if row['method']=='click':
        need(xy(v['stepState']['caret'])==xy(points[0]),'step click landed elsewhere')
        contradict(v['stepState']['selection'].get('collapsed') is True and v['stepSelection'].get('text')==texts[0],'click did not reset the selection')
        homes=row['nativeShiftHomeAfterClickText'];need(isinstance(homes,list) and len(homes)==3 and len(set(homes))==1,'native ShiftHome oracle disagrees')
        _,_,t=e.key('interaction-shift-home',{**row,'action':'move-line-home','productKey':{'key':'Home'}},True);final=homes[0]
    else:
        contradict(v['stepSelection'].get('text')==texts[0],'interaction native text differs');final=texts[0]
        t=e.replies[max((k for k in e.mutations if k[0]==gen),key=lambda k:e.replies[k]['at'])]
    rr,rt=e.state('interaction-readback',v['readback']);need(rr['at']-t['at']>=500,'readback too early')
    ar,_=e.text('interaction-active-selection',v['activeSelection']);need(ar['at']>=rt['at'],'active selection precedes delayed state')
    contradict(v['activeSelection'].get('text')==final,'interaction native text differs after settling')
    _,_,close=e.call('interaction-close','close')
    return gen,close

def inspect_interaction(page,plan,browser):
    groups={'S4':{'verdict':'NOT_ESTABLISHED'}}
    try:
        e=Evidence(page,plan,browser);row=plan['interactions'][page['caseId']]
        g=readiness(e);gen,_=interaction(e,row)
        need(page.get('complete'),'incomplete page')
        need(len({g,gen})==2 and len(page['workers'])==2,'fresh arm/recovery generation differs')
        need(len([r for r in e.requests.values() if r['message']['operation']=='open'])==2,'extra/missing open')
        e.closure()
        contradict(not any(x['message'].get('event') in ('recoverable-error','worker-restart') for x in page['events']),'recovery occurred')
        groups['S4']={'verdict':'PASS','method':row['method'],'nativeText':row['nativeAfterStepText'][0]}
        return {'verdict':'PASS','groups':groups}
    except ProductFailure as error:
        groups['S4']={'verdict':'FAIL','reason':str(error)}
        return {'verdict':'FAIL','reason':str(error),'groups':groups}
    except (NotEstablished,KeyError,ValueError,TypeError,IndexError) as error:
        return {'verdict':'NOT_ESTABLISHED','reason':str(error),'groups':groups}

S5_DELETES={'Backspace':('delete-backward','delete-selection'),'Delete':('delete-forward','delete-selection')}

def odt_content(raw):
    import io,zipfile
    try:return zipfile.ZipFile(io.BytesIO(raw)).read('content.xml')
    except (zipfile.BadZipFile,KeyError) as error:raise NotEstablished('saved ODT unreadable: '+str(error))

def strip_ffd(content):
    """Fable ruling 2 (2026-10-27): against a native save only, remove the single
    office:font-face-decls element, which lists each environment's installed CJK fonts."""
    pattern=rb'<office:font-face-decls>(.*?)</office:font-face-decls>'
    found=re.findall(pattern,content,re.S)
    need(len(found)==1,'font-face-decls not uniquely present')
    need(found[0].strip()!=b'','font-face-decls empty')
    rest=re.sub(pattern,b'',content,count=1,flags=re.S)
    need(b'<office:body>' in rest,'office:body absent after removing font-face-decls')
    return rest

def s5_reduced(raw,native):
    from run_merge_wasm_shakedown import reduce_content
    content=reduce_content(odt_content(raw))
    return strip_ffd(content) if native else content

def s5_compare(family,candidate,reference,native):
    """Deletion: reduce_content byte equality (minus font-face-decls against native); type: paragraph text."""
    if family=='type':
        from odt_paragraphs import paragraph_texts_from_xml
        return paragraph_texts_from_xml(odt_content(candidate))==paragraph_texts_from_xml(odt_content(reference))
    return s5_reduced(candidate,native)==s5_reduced(reference,native)

def native_reference(row,original):
    """The cell's native after-save, once its two guards hold (fable ruling 2)."""
    files={}
    for side in ('before','after'):
        raw=(ROOT/row['native'][side]['path']).read_bytes()
        need(digest(raw)==row['native'][side]['sha256'],'native reference bytes differ');files[side]=raw
    # Per cell: the unedited WASM and native documents agree under the same reduction.
    need(s5_compare(row['family'],original,files['before'],True),'native reference not comparable')
    if row['family']!='type' and s5_reduced(files['before'],True)==s5_reduced(files['after'],True):
        need(odt_content(files['before'])==odt_content(files['after']),'reduction collapses the native edit')
    return files['after']

def single_line(e,name):
    """Every located point of the arm sits on a one-rectangle (single displayed line) paragraph."""
    for pointname,observed in e.page[name]['points'].items():
        _,_,search=call_binding(e.page,name+'-point-'+pointname+'-search','search',e.requests,e.replies)
        raw=search['message']['result'];first=wrap_first_rectangle(raw)
        if len(raw['selections'][0]['rectangles'].split(';'))!=1 or observed['start']['caret']['y']!=first[1] or observed['final']['caret']['y']!=first[1]:
            return False
    return True

def final_save(e,name,saved):
    """The page's own save is queued behind the sequence, so the product's dirty-checkpoint save
    can fall inside its window (s5-prep-02); bind the LAST save there, byte-equal to the call."""
    calls=[c for c in e.page['calls'] if c['name']==name]
    need(len(calls)==1 and calls[0].get('ok') is True,'missing/refused public call '+name)
    need(name not in e.used,'reused call evidence');e.used.add(name);e.call_order.append(name)
    c=calls[0]
    saves=[r for r in e.page['requests'][c['requestStart']:c['requestEnd']] if r['generation']==c['generation']
           and r['message']['operation']=='save' and c['startedAt']<=r['at']<=c['finishedAt']]
    need(saves,'missing wire call '+name);request=saves[-1];terminal=e.replies.get(request_key(request))
    need(terminal is not None and terminal['message'].get('ok') is True and request['at']<=terminal['at']<=c['finishedAt'],'missing/refused terminal '+name)
    need(request['message']['payload'].get('documentHandle')==c['documentHandle'],'wrong document '+name)
    raw=binary(terminal['message']['result']['buffer'])
    need(digest(raw)==saved['sha256'] and binary(c['result']['bytes'])==raw,'save not bound to actual wire bytes')
    need(all(r['at']<request['at'] for r in saves[:-1]),'final save is not the last save in its window')

def s5_arm(e,name,row,source):
    gen,handle,anchor,moving,before=setup(e,name,source)
    v=e.page[name];q=v.get('sequence') or {}
    need(all(type(q.get(k)) is int for k in ('inputStart','inputEnd','requestStart','requestEnd')) and q.get('generation')==gen,'sequence window absent')
    keys=[x for x in e.page['inputs'][q['inputStart']:q['inputEnd']] if x['type']=='keydown' and x.get('key')!='Shift']
    need([(x.get('key'),x.get('shiftKey') is True) for x in keys]==[(k['key'],'shift' in k['mods']) for k in row['keys']],'actual sequence keys differ')
    for x in keys:
        sink=x.get('sink',{})
        need(x.get('isTrusted') is True and not any(x.get(k) for k in ('ctrlKey','altKey','metaKey','repeat')),'sequence key not a trusted plain press')
        need(sink.get('active') and sink.get('connected') and not sink.get('disabled') and not sink.get('readOnly') and sink.get('documentHandle')==handle,'sequence key not in the editable document sink')
    need(keys[0]['at']>=before['at'],'sequence precedes its shape')
    window=[r for r in e.page['requests'][q['requestStart']:q['requestEnd']] if r['generation']==gen]
    moves=[r for r in window if r['message']['operation']=='editorActionV2' and str(r['message']['payload'].get('action','')).startswith('move-')]
    need(len(moves)==1 and moves[0]['message']['payload']['action']==source['action'] and moves[0]['message']['payload'].get('extendSelection') is True,'extension request absent/nonunique')
    extension=e.replies.get(request_key(moves[0]));need(extension is not None,'extension terminal absent')
    deletes=[k for k in row['sequence'] if k in S5_DELETES]
    for r in window:
        op=r['message']['operation']
        if op not in MUTATION_OPS+('insertText',):continue
        need(op in ('editorActionV2','insertText'),'unplanned mutation in the sequence window')
        if op=='editorActionV2' and r is not moves[0]:
            need(r['message']['payload'].get('action') in {a for d in deletes for a in S5_DELETES[d]},'unplanned action in the sequence window')
        if op=='insertText':need(row['family']=='type' and r['message']['payload'].get('text')=='x','unplanned insertion in the sequence window')
        e.mutations.add(request_key(r))
    continuation=keys[row['shiftIndex']+1:]
    result={'generation':gen,'extensionTerminal':extension}
    if name=='s5ref':
        rr,rt=e.state(name+'-settled-state',v['settledState']);need(rr['at']-extension['at']>=500,'settled witness too early')
        ar,at=e.text(name+'-settled-text',v['settledSelection']);need(ar['at']>=rt['at'],'settled selection precedes its state')
        need(type(q.get('continuationInputStart')) is int and all(k['at']>at['at'] for k in continuation),'continuation before the settled witness')
    else:
        # Overlap witness: posted move/extend requests without a terminal or cancel at each
        # continuation's beforeinput (its keydown when the product consumed the key first).
        cancels={(c['generation'],c['message'].get('requestId')):c for c in e.page.get('cancels',[])}
        allmoves=[r for r in e.requests.values() if r['generation']==gen and r['message']['operation']=='editorActionV2' and str(r['message']['payload'].get('action','')).startswith('move-')]
        overlap=[]
        for j,key in enumerate(continuation):
            until=continuation[j+1]['at'] if j+1<len(continuation) else float('inf')
            mark=next((x for x in e.page['inputs'][q['inputStart']:q['inputEnd']] if x['type']=='beforeinput' and key['at']<=x['at']<until),None)
            t=(mark or key)['at']
            pending=[list(request_key(r)) for r in allmoves if r['at']<t and not any(x is not None and x['at']<t for x in (e.replies.get(request_key(r)),cancels.get(request_key(r))))]
            overlap.append({'key':key['key'],'at':t,'witness':'beforeinput' if mark else 'keydown','pendingMoveOrExtendKeys':pending})
        result['overlap']=overlap
    import base64
    def recorded(save):
        raw=base64.b64decode(save['base64'],validate=True);need(digest(raw)==save['sha256'],'page save record differs from its hash');return raw
    final_save(e,name+'-final-save',v['finalSave'])
    e.state(name+'-final-state',v['finalState']);_,_,close=e.call(name+'-close','close')
    result.update(final=recorded(v['finalSave']),original=recorded(v['originalSave']),close=close)
    return result

def inspect_s5(page,plan,browser):
    groups={'S5':{'verdict':'NOT_ESTABLISHED'}}
    try:
        e=Evidence(page,plan,browser);row=plan['s5'][page['caseId']];source=plan['cases'][row['sourceArm']]
        g=readiness(e);cand=s5_arm(e,'s5cand',row,source)
        ref=s5_arm(e,'s5ref',row,source) if row['settledReference'] else None
        arms=1+(ref is not None)
        need(page.get('complete'),'incomplete page')
        need(len({g,cand['generation']}|({ref['generation']} if ref else set()))==1+arms and len(page['workers'])==1+arms,'fresh arms/recovery generation differs')
        need(len([r for r in e.requests.values() if r['message']['operation']=='open'])==1+arms,'extra/missing open')
        e.closure()
        contradict(not any(x['message'].get('event') in ('recoverable-error','worker-restart') for x in page['events']),'recovery occurred')
        single=single_line(e,'s5cand')
        # A type cell without run-03's order witness carries no native save (fable ruling 3, fallback A).
        need(row['native'] is not None or row['referencePolicy']=='settled-wasm' or (row['family']=='type' and row.get('nativeFallback')),'native reference absent')
        native=row['native'] is not None and (row['referencePolicy']=='native' or (row['referencePolicy'].startswith('native-if-single-line') and single))
        # Older configs bound run-01's x-then-Shift type saves; only a witnessed save is a type oracle.
        need(not native or row['family']!='type' or row.get('nativeOrderWitness') in ('selection-before-x','settle-only'),'native type reference without order witness')
        if native:reference=native_reference(row,cand['original'])
        else:
            need(ref is not None,'settled reference arm absent');reference=ref['final']
        contradict(s5_compare(row['family'],cand['final'],reference,native),'sequence result differs from its reference')
        overlapping=any(o['pendingMoveOrExtendKeys'] for o in cand['overlap'])
        groups['S5']={'verdict':'PASS','reference':'native' if native else 'settled-wasm','singleLineWitness':single,
                      'nativeOrderWitness':row.get('nativeOrderWitness') if native else None,
                      'nativeFallback':row.get('nativeFallback'),'overlap':cand['overlap'],'overlapping':overlapping}
        return {'verdict':'PASS','groups':groups}
    except ProductFailure as error:
        groups['S5']={'verdict':'FAIL','reason':str(error)}
        return {'verdict':'FAIL','reason':str(error),'groups':groups}
    except (NotEstablished,KeyError,ValueError,TypeError,IndexError) as error:
        return {'verdict':'NOT_ESTABLISHED','reason':str(error),'groups':groups}

def inspect(page,plan,browser):
    if page.get('caseId') in plan.get('s5',{}):return inspect_s5(page,plan,browser)
    if page.get('caseId') in plan.get('interactions',{}):return inspect_interaction(page,plan,browser)
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
            # The Shift anchor is where the selection was anchored before the key: a range
            # shape's anchor point, but for a collapsed shape the caret itself (the moving
            # point). click+End shapes click elsewhere first (selection-prep-05, wrap-line-end).
            anchorname=row['anchorPointName'] if row['setup']['expectRange'] else row['movingPointName']
            state=page['candidate']['readback'];target=page['reference']['endpoint']
            anchor=candidate['anchor'] if row['setup']['expectRange'] else candidate['moving']
            def single_line():
                single=True
                for pointname,observed in page['candidate']['points'].items():
                    _,_,search=call_binding(page,'candidate-point-'+pointname+'-search','search',e.requests,e.replies)
                    raw=search['message']['result'];first=wrap_first_rectangle(raw)
                    boxes=raw['selections'][0]['rectangles'].split(';')
                    single=single and len(boxes)==1 and observed['start']['caret']['y']==first[1] and observed['final']['caret']['y']==first[1]
                return single and state['caret']['y']==candidate['moving']['y'] and target['y']==candidate['moving']['y']
            anchorplan=row['pointPlans'][anchorname]
            offset=anchorplan['offset'] if type(anchorplan['offset']) is int else 0 if anchorplan['offset']=='next-empty' else len(page['candidate']['points'][anchorname]['selected']['text'])
            crossing=table_selection(fixture_containers(plan),row,anchorname,logical[0])
            if crossing:
                # Oracle: Writer's own selected text, all three native rounds agreeing; the
                # unshifted-endpoint premise is false here (append to the protocol, 2026-10-27).
                texts=row['nativeAfterSelectionText']
                need(isinstance(texts,list) and len(texts)==3 and len(set(texts))==1,'native table-selection oracle disagrees')
                contradict(page['candidate']['activeSelection']['text']==texts[0],'table-selection native text differs')
                groups['S1']={'verdict':'PASS','tableSelection':True,'containers':crossing,'logicalAnchor':[anchorplan['paragraph'],offset],
                              'logicalEndpoint':logical,'nativeText':texts[0],'anchorWitness':'native-text-extent',
                              'namedLimitation':'caret side and text-anchor identity not independently witnessed for table-selection members',
                              'singleLineNativeWitness':single_line()}
            else:
                contradict(xy(state['caret'])==xy(target),'moving endpoint differs from independent control')
                endpoint_pair(state['selection'],xy(anchor),xy(target),measured=True)
                if row['key'] in ('Left','Right'):
                    contradict(all(page['candidate']['activeSelection']['text']==x for x in row['nativeAfterSelectionText']),'native literal selection differs')
                # Native Home/End parity is conditional; the independent control is always retained.
                single=single_line()
                if row['key'] in ('Home','End') and single:
                    contradict(all(page['candidate']['activeSelection']['text']==x for x in row['nativeAfterSelectionText']),'single-line native selection differs')
                groups['S1']={'verdict':'PASS','logicalAnchor':[anchorplan['paragraph'],offset],'logicalEndpoint':logical,'singleLineNativeWitness':single}
        return {'verdict':'FAIL' if any(x['verdict']=='FAIL' for x in groups.values()) else 'PASS','groups':groups}
    except ProductFailure as error:
        groups[current_group]={'verdict':'FAIL','reason':str(error)}
        return {'verdict':'FAIL','reason':str(error),'groups':groups}
    except (NotEstablished,KeyError,ValueError,TypeError,IndexError) as error:
        return {'verdict':'NOT_ESTABLISHED','reason':str(error),'groups':groups}

def import_closure(*starts):
    """Local tools/ modules reachable by import from `starts`; the same walk the pre-red config uses."""
    import ast
    tools=Path(__file__).resolve().parent;pending=[tools/s for s in starts];seen=set()
    while pending:
        path=pending.pop().resolve()
        if path in seen:continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else (
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            pending+=[c for c in (tools/Path(*n.split('.')).with_suffix('.py') for n in names) if c.is_file()]
    return sorted('tools/'+p.name for p in seen)

def preserved_graph(path,executed):
    """Bind the report's executed Python graph to the exact bytes preserved beside its cohort."""
    base=path.parent.parent
    found=[]
    for record in sorted(base.glob('tool-source-bindings-*.json')):
        rows=json.loads(record.read_bytes()).get('reports',{}).get(path.parent.name)
        if rows is not None:found.append(rows)
    need(len(found)==1,'executed graph not uniquely preserved')
    rows=found[0];need(isinstance(executed,dict) and executed and set(rows)==set(executed),'preserved graph membership differs')
    for name,sha in executed.items():
        stored=Path(rows[name].get('storedPath',''))
        need(not stored.is_absolute() and '..' not in stored.parts and rows[name].get('sha256')==sha,'preserved source record differs: '+name)
        blob=base/stored;need(blob.is_file() and digest(blob.read_bytes())==sha,'preserved source blob differs: '+name)
    return rows

def check_pre_red(path):
    # The report records the Python graph that executed it, and tool-source-bindings preserves
    # those bytes.  A later runner-side helper change (the Firefox 096 transport edits
    # run_browser_probe.py and run_e2_c_product_path.py) must not void a sealed result, and
    # arbitrary bytes must not pass either: frozen inputs are recomputed live, the executed
    # graph is bound to its preserved blobs, and the live reader re-judges only when its own
    # import closure is byte-identical to what executed.
    from judge_v23_feature_pre_red import judge as historical_judge
    from v23_feature_pre_red_cases import config as historical_config,verify_mirror as historical_mirror,WASM
    need(path is not None,'complete historical pre-red reference absent')
    path=Path(path).resolve();raw=path.read_bytes();report=json.loads(raw);live=historical_config(WASM)
    executed,post=report.get('config'),report.get('postConfig')
    need(isinstance(executed,dict) and isinstance(post,dict),'historical graph incomplete')
    frozen=lambda plan:{k:v for k,v in plan.items() if k!='instrumentSources'}
    need(frozen(executed)==frozen(live)==frozen(post),'historical frozen inputs differ or incomplete')
    need(post.get('instrumentSources')==executed.get('instrumentSources'),'executed graph changed during the run')
    preserved_graph(path,executed['instrumentSources'])
    reader=import_closure('judge_v23_feature_pre_red.py')
    need(all(live['instrumentSources'].get(n)==executed['instrumentSources'].get(n) is not None for n in reader),
         'historical reader changed; re-judging needs the recorded reader')
    need(not report.get('preparationOnly'),'historical preparation cannot qualify')
    historical_mirror(path.parent/'mirror',executed);cells=[]
    for row in report['runs']:
        data=(path.parent/row['path']).read_bytes();need(digest(data)==row['sha256'],'historical cell bytes differ');cells.append(json.loads(data))
    result=historical_judge(cells,executed);need(result['verdict']=='EXPECTED_RED' and result['populationComplete'],'historical pre-red not complete expected red')
    return {'path':str(path),'sha256':digest(raw),'verdict':'EXPECTED_RED','cells':result['cells']}

def judge(cells,plan,kind='selection'):
    population=plan['s5'] if kind=='s5' else {**plan['cases'],**plan.get('interactions',{})}
    wanted={(b,c) for b in BROWSERS for c in population};seen=set();hashes=set();rows=[]
    for cell in cells:
        key=(cell['browser'],cell['caseId']);page=cell.get('page') or {}
        fingerprint=digest(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
        if key in seen or fingerprint in hashes or key not in wanted:
            rows.append({'cell':key,'verdict':'NOT_ESTABLISHED','reason':'duplicate/undeclared actual observation'});continue
        seen.add(key);hashes.add(fingerprint)
        value=inspect(page,plan,cell['browser']) if not cell.get('fatal') and page.get('caseId')==cell['caseId'] else {'verdict':'NOT_ESTABLISHED','reason':'unclean cell/label'}
        # Recorded, never asserted: does the candidate's selected text equal Writer's? A wrong
        # plain move can take a table member out of the A' branch (review of 853f2522), and
        # Up/Down outside that branch have no native comparison; this makes such a flip visible.
        texts=population[key[1]].get('nativeAfterSelectionText') or []
        observed=((page.get('candidate') or {}).get('activeSelection') or {}).get('text')
        if 'S1' in population[key[1]]['memberships'] and isinstance(observed,str) and texts:
            value={**value,'nativeTextAgreement':{'agrees':all(observed==x for x in texts),'roundsAgree':len(set(texts))==1}}
        rows.append({'cell':key,**value})
    complete=seen==wanted and len(rows)==len(wanted)
    groups={}
    for group in (('S5',) if kind=='s5' else ('S1','S2','S3','S4')):
        members={(b,c) for b,c in wanted if group in population[c]['memberships']}
        observations=[r for r in rows if tuple(r['cell']) in members]
        groups[group]={'required':len(members),'observed':len(observations),
            'verdict':'FAIL' if any(r.get('groups',{}).get(group,{}).get('verdict')=='FAIL' for r in observations) else 'PASS' if complete and len(observations)==len(members) and all(r.get('groups',{}).get(group,{}).get('verdict')=='PASS' for r in observations) else 'NOT_ESTABLISHED'}
    if kind=='s5':
        # Protocol: overlap is claimed only over cells with actual pending move/extend requests at a
        # continuation; an empty overlapping set fails S5 even when every sequence matches.
        overlapping=[r['cell'] for r in rows if r.get('groups',{}).get('S5',{}).get('overlapping')]
        groups['S5']['overlappingCells']=len(overlapping)
        # Recorded, never asserted: how many PASS cells rest on the weaker settle-only native witness.
        s5=[r.get('groups',{}).get('S5',{}) for r in rows]
        groups['S5']['nativeReferenceCells']={label:sum(g.get('reference')=='native' and g.get('nativeOrderWitness')==w for g in s5)
            for label,w in (('selection-before-x','selection-before-x'),('settle-only','settle-only'),('deletion-family',None))}
        groups['S5']['nativeFallbackCells']=sum(bool(g.get('nativeFallback')) for g in s5)
        if groups['S5']['verdict']=='PASS' and not overlapping:groups['S5'].update(verdict='FAIL',reason='empty overlap set')
        verdict=groups['S5']['verdict']
    else:
        verdict='FAIL' if any(r['verdict']=='FAIL' for r in rows) else 'PASS' if complete and all(r['verdict']=='PASS' for r in rows) else 'NOT_ESTABLISHED'
    return {'verdict':verdict,'population':kind,'populationComplete':complete,'groups':groups,'results':rows}

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
    result=judge(cells,plan,report.get('population','selection'));print(json.dumps(result,indent=2));return 0 if result['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
