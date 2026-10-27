"""R1 collector controls (handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md): plan derivation, the native
marker mapping over every retained observation, the reader's NE/FAIL red cases on synthetic pages,
and the unchanged selection/S5 re-reading of the preserved preparations.  Nothing here runs a
browser; the synthetic pages model a layout, they are not evidence of one."""
import base64
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile
from xml.sax.saxutils import escape
TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
import v23_feature_selection_cases as cases
from v23_feature_selection_cases import PROFILE,PROJECT,ROOT,encoded,digest

_PLAN={}
def live_plan():
    if 'plan' not in _PLAN:_PLAN['plan']=cases.config()
    return _PLAN['plan']

def collected():
    if 'collected' not in _PLAN:
        from collect_v23_r1_inputs import collect
        _PLAN['collected']=collect()
    return copy.deepcopy(_PLAN['collected'])

# ---- a synthetic page: the overlay's records for one R1 cell, from a small layout model -------
X0,CW,LH,RIGHT,DOC_W,DOC_H=1418,80,276,11390,12808,16408
def ytop(p):return 1418+p*2000
def binary(raw):return {'encoding':'base64','bytes':len(raw),'data':base64.b64encode(raw).decode()}
def saved(texts):
    content=('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
             'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:text>'+
             ''.join('<text:p>'+escape(x)+'</text:p>' for x in texts)+'</office:text></office:body></office:document-content>').encode()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr('content.xml',content)
    raw=stream.getvalue();return {'base64':base64.b64encode(raw).decode(),'sha256':digest(raw)},raw

class Doc:
    """Paragraph p's offsets [kW,(k+1)W) are its line k; offset kW shown at line k-1's end is affinity 'end'."""
    def __init__(self,texts,containers,wraps):
        self.texts=list(texts);self.containers=containers;self.wraps=wraps;self.anchor=None;self.point=(0,0,'start')
    def W(self,p):return self.wraps.get(p)
    def lines(self,p):
        W=self.W(p);n=len(self.texts[p]);return 1 if not W or n==0 else (n-1)//W+1
    def line(self,pos):
        p,o,aff=pos;W=self.W(p)
        if not W:return 0
        if aff=='end' and o>0 and o%W==0:return o//W-1
        return min(o//W,self.lines(p)-1)
    def caret(self,pos):
        p,o,_=pos;k=self.line(pos);W=self.W(p)
        return {'x':X0+(o-k*W if W else o)*CW,'y':ytop(p)+k*LH,'width':0,'height':LH}
    def hit(self,x,y):
        for p in range(len(self.texts)):
            for k in range(self.lines(p)):
                if ytop(p)+k*LH<=y<ytop(p)+(k+1)*LH:
                    W=self.W(p);n=len(self.texts[p]);last=k==self.lines(p)-1
                    length=n-k*W if W and last else (W if W else n)
                    col=max(0,min(length,round((x-X0)/CW)))
                    if W and not last and col==W:return (p,(k+1)*W,'end')
                    return (p,(k*W if W else 0)+col,'start')
        raise ValueError('synthetic hit outside the text')
    def moved(self,pos,action):
        p,o,_=pos;n=len(self.texts[p]);W=self.W(p);k=self.line(pos)
        if action=='move-character-right':return (p,o+1,'start') if o<n else (min(p+1,len(self.texts)-1),0 if p+1<len(self.texts) else o,'start')
        if action=='move-character-left':return (p,o-1,'start') if o>0 else ((p-1,len(self.texts[p-1]),'start') if p else pos)
        if action=='move-line-home':return (p,k*W if W else 0,'start')
        if action=='move-line-end':
            if W and k<self.lines(p)-1:
                end=(k+1)*W;return (p,end-1,'start') if self.texts[p][end-1]==' ' else (p,end,'end')
            return (p,n,'start')
        x=self.caret(pos)['x'];q,k=p,k+(1 if action=='move-line-down' else -1)
        if k>=self.lines(q):q,k=q+1,0
        if k<0:q,k=q-1,(self.lines(q-1)-1 if q>0 else 0)
        if q<0:return (0,0,'start')
        if q>=len(self.texts):return (len(self.texts)-1,len(self.texts[-1]),'start')
        return self.hit(x,ytop(q)+k*LH)
    def is_range(self):return self.anchor is not None and self.anchor[:2]!=self.point[:2]
    def cells(self):
        a,b=self.containers[self.anchor[0]],self.containers[self.point[0]]
        return a!='body' and b!='body' and a!=b
    def text(self):
        if not self.is_range():return ''
        rendering,spans=cases.r1_rendering(self.texts,self.containers)
        if self.cells():
            lo,hi=sorted((self.anchor[0],self.point[0]));return rendering[spans[lo][0]:spans[hi][1]]+'\n'
        a,b=sorted((cases.r1_index(spans,self.anchor[:2]),cases.r1_index(spans,self.point[:2])));return rendering[a:b]
    def state(self,handle,revision):
        sel={'observed':True,'collapsed':not self.is_range(),'start':None,'end':None,'rectangles':[]}
        if self.is_range():
            if self.cells():lo,hi=self.anchor[:2],(self.anchor[0],len(self.texts[self.anchor[0]]))
            else:lo,hi=sorted((self.anchor[:2],self.point[:2]))
            sel['start']={**self.caret((*lo,'start')),'height':LH-1};sel['end']={**self.caret((*hi,'start')),'height':LH-1}
            sel['rectangles']=[{'x':sel['start']['x'],'y':sel['start']['y'],'width':100,'height':LH-1}]
        return {'documentHandle':handle,'revision':revision,'caret':self.caret(self.point),'selection':sel}
    def search(self,p,query):
        W=self.W(p);n=len(query);count=1 if not W else max(1,(n-1)//W+1);rows=[]
        for k in range(count):
            width=RIGHT-X0 if k<count-1 else max(1,(n-(k*W if W else 0))*CW)
            rows.append(f'{X0},{ytop(p)+k*LH},{width},{LH-1}')
        return {'selections':[{'part':'0','rectangles':';'.join(rows)}]}

class Builder:
    """Mirrors web/v23-feature-selection.js (prepareR1/shapeR1/controlPointR1/finishR1/markerR1) and
    tools/run_v23_feature_selection.py run_r1, on the Doc model.  `faults` perturbs the modelled
    product consistently (every record agrees), so the reader sees a coherent page."""
    def __init__(self,plan,case,browser='chrome',faults=None):
        self.plan=plan;self.case=case;self.faults=faults or {};self.clock=0;self.ident=0;self.gen=0;self.handle=0;self.revision=0
        self.p={'schema':1,'profile':PROFILE,'caseId':case,'userAgent':'Chrome/150' if browser=='chrome' else 'Firefox/150',
                'servedSources':plan['servedSources'],'artifacts':plan['profile']['artifacts'],'configSha256':digest(encoded(plan)),
                'fixtureManifestSha256':digest(encoded(plan['fixtureManifest'])),'complete':False,
                'requests':[],'responses':[],'events':[],'cancels':[],'workers':[],'inputs':[],'calls':[],'opens':[],'keyArms':[]}
    def tick(self,n=1):self.clock+=n;return self.clock
    def wire(self,op,payload,result):
        self.ident+=1
        r={'generation':self.gen,'at':self.tick(),'message':{'kind':'request','requestId':self.ident,'operation':op,'payload':{'documentHandle':self.handle,**payload}}}
        t={'generation':self.gen,'at':self.tick(),'message':{'kind':'response','requestId':self.ident,'ok':True,'result':copy.deepcopy(result)}}
        self.p['requests'].append(r);self.p['responses'].append(t);return result
    def call(self,name,fn):
        start=self.tick();index=len(self.p['requests']);result=fn()
        self.p['calls'].append({'name':name,'generation':self.gen,'documentHandle':self.handle,'startedAt':start,'requestStart':index,
                                'requestEnd':len(self.p['requests']),'finishedAt':self.tick(),'ok':True,'result':copy.deepcopy(result)})
        return copy.deepcopy(result)
    def sink(self):return {'id':'sink','active':True,'connected':True,'disabled':False,'readOnly':False,'documentHandle':self.handle,'generation':self.gen}
    def state(self,doc):return doc.state(self.handle,self.revision)
    def read(self,name,doc):return self.call(name,lambda:self.wire('editorGetStateV2',{},self.state(doc)))
    def text(self,name,doc):
        value=doc.text();return self.call(name,lambda:self.wire('getSelection',{},{'text':value,'selectionType':'text' if value else 'none'}))
    def save(self,name,doc):
        artifact,raw=saved(doc.texts)
        def run():self.wire('save',{},{'buffer':binary(raw)});return {'bytes':binary(raw)}
        self.call(name,run);return artifact
    def place_ops(self,doc,x,y):
        self.wire('editorGetStateV2',{},self.state(doc))
        self.wire('click' if doc.is_range() else 'editorPlaceCaretV2',{'xTwips':x,'yTwips':y},{})
        doc.anchor=None;doc.point=doc.hit(x,y);return {}
    def place(self,name,doc,x,y):return self.call(name,lambda:self.place_ops(doc,x,y))
    def move(self,name,doc,action):
        def run():
            doc.anchor=None;doc.point=doc.moved(doc.point,action)
            return self.wire('editorActionV2',{'action':action},{'action':action,'changed':False,'beforeRevision':self.revision,
                             'revision':self.revision,'completion':'verified-move-readback','state':self.state(doc)})
        return self.call(name,run)
    def select(self,name,doc,a,b):
        def run():
            doc.anchor=doc.hit(*a)[:2]+('start',);doc.point=doc.hit(*b)
            return self.wire('editorSelectRangeV2',{'startXTwips':a[0],'startYTwips':a[1],'endXTwips':b[0],'endYTwips':b[1]},{})
        return self.call(name,run)
    def search(self,name,doc,p,query):return self.call(name,lambda:self.wire('search',{'query':query},doc.search(p,query)))
    @staticmethod
    def pt(c):return (c['x'],c['y']+c['height']//2)
    @staticmethod
    def boxes(found):return sorted([list(map(int,x.split(','))) for x in found['selections'][0]['rectangles'].split(';')],key=lambda r:(r[1],r[0]))
    def locate(self,doc,plan,prefix):
        boxes=self.boxes(self.search(prefix+'-search',doc,plan.get('searchParagraph',plan['paragraph']),plan['query']));r=boxes[0]
        self.place(prefix+'-search-click',doc,r[0],r[1]+r[3]//2);start=self.read(prefix+'-start-state',doc)
        if type(plan['offset']) is int:
            for i in range(plan['offset']):self.move(prefix+'-right-'+str(i),doc,'move-character-right')
        else:
            self.move(prefix+'-end',doc,'move-line-end')
            if plan['offset']=='next-empty':self.move(prefix+'-next-empty',doc,'move-character-right')
        target=self.read(prefix+'-target-state',doc)
        self.select(prefix+'-prefix-select',doc,self.pt(start['caret']),self.pt(target['caret']))
        selected=self.text(prefix+'-prefix-text',doc)
        self.place(prefix+'-restore-point',doc,*self.pt(target['caret']));final=self.read(prefix+'-final-state',doc)
        return {'plan':plan,'boxes':boxes,'start':start,'target':target,'selected':selected,'final':final}
    def walk(self,doc,plan,prefix):
        boxes=self.boxes(self.search(prefix+'-search',doc,plan['paragraph'],plan['query']));r=boxes[0]
        self.place(prefix+'-search-click',doc,r[0],r[1]+r[3]//2);start=self.read(prefix+'-start-state',doc);steps=[]
        for i in range(1,plan['limit']+1):
            self.move(prefix+'-right-'+str(i),doc,'move-character-right');step=self.read(prefix+'-step-'+str(i),doc);steps.append(step)
            if step['caret']['y']!=start['caret']['y']:return {'plan':plan,'boxes':boxes,'start':start,'steps':steps,'wrap':i}
        raise ValueError('synthetic paragraph does not wrap')
    def open(self,name,texts):
        self.gen+=1;self.handle=self.gen;self.revision=0;raw=texts
        self.p['workers'].append({'generation':self.gen,'url':'./profiles/'+PROFILE+'/sdk-worker.js'})
        self.wire('open',{'name':name,'buffer':binary(raw)},{'documentHandle':self.handle,'width':DOC_W,'height':DOC_H})
        record={'serial':self.gen,'name':name,'fixtureSha256':digest(raw),'generation':self.gen,'documentHandle':self.handle}
        self.p['opens'].append(record);self.p['currentOpen']=record;return copy.deepcopy(record)
    def key(self,name,doc,key,shift,action,landing=None,reply=None):
        arm={'name':name,'generation':self.gen,'inputStart':len(self.p['inputs']),'at':self.tick()}
        self.p['keyArms'].append(arm)
        self.p['inputs'].append({'type':'keydown','key':key,'shiftKey':shift,'isTrusted':True,'at':self.tick(),'ctrlKey':False,'altKey':False,
                                 'metaKey':False,'repeat':False,'sink':self.sink()})
        def run():
            before=self.revision
            if shift:
                doc.anchor=doc.anchor or doc.point[:2]+('start',);doc.point=doc.moved(doc.point,action)
            else:doc.anchor=None;doc.point=landing
            value={'action':action,'changed':False,'beforeRevision':before,'revision':self.revision,'completion':'verified-move-readback','state':self.state(doc)}
            if reply:reply(value)
            return self.wire('editorActionV2',{'action':action,'extendSelection':shift},value)
        value=self.call(name,run);arm['inputEnd']=len(self.p['inputs']);return value,arm
    def readiness(self):
        from v23_feature_selection_cases import FIXTURE
        texts=self.plan['fixtureParagraphs'];doc=Doc(texts,['body']*len(texts),{})
        v=self.p['readiness']={'open':self.open('list-contexts.odt',FIXTURE.read_bytes())}
        v['setup']=self.locate(doc,self.plan['readinessPoint'],'readiness');v['beforeState']=self.read('readiness-before-state',doc)
        v['beforeSave']=self.save('readiness-before-save',doc)
        self.p['inputs'].append({'type':'keydown','key':'Z','isTrusted':True,'at':self.tick(),'sink':self.sink()})
        self.p['inputs'].append({'type':'beforeinput','inputType':'insertText','data':'Z','isTrusted':True,'at':self.tick(),'sink':self.sink()})
        self.revision=1;self.wire('insertText',{'text':'Z'},{'revision':1});doc.texts[0]='Z'+doc.texts[0]
        v['afterSave']=self.save('readiness-after-save',doc);v['afterState']=self.read('readiness-after-state',doc)
    def arm(self,which,row):
        f=self.plan['r1Fixtures'][row['fixture']];s=row['setup'];faults=self.faults.get(which,{})
        wraps=faults.get('wraps',self.faults.get('wraps',{'arrow-selection-shapes':{0:101},'arrow-selection-wrap':{0:89}})).get(row['fixture'],{})
        doc=Doc(f['paragraphs'],f['containers'],wraps)
        v=self.p[which]={'open':self.open(f['servedName'],(ROOT/f['path']).read_bytes()),'points':{}}
        v['originalSave']=self.save(which+'-original-save',doc);wrap=None
        if s['walk']:v['walk']=self.walk(doc,s['walk'],which+'-walk');wrap=v['walk']['wrap']
        for spec in s['points']:v['points'][spec['name']]=self.locate(doc,cases.r1_point_plan(f['paragraphs'],spec,wrap),which+'-point-'+spec['name'])
        anchor=v['points']['anchor']['final']['caret']
        if s['method']!='drag':self.place(which+'-anchor-click',doc,*self.pt(anchor))
        v['inputStart'],v['requestStart']=len(self.p['inputs']),len(self.p['requests'])
        if s['method']=='keys':
            for n in range(s['count']):self.key(which+'-setup-shift-'+str(n),doc,s['productKey'],True,s['action'])
        elif s['method']=='shift-end':self.key(which+'-setup-end',doc,'End',True,'move-line-end')
        else:
            line=v['walk']['boxes'][0];right=line[0]+line[2]
            v['dragEnd']={'x':right+(DOC_W-right)//2,'y':line[1],'height':line[3]}
            self.drag(doc,self.pt(anchor),self.pt(v['dragEnd']))
        v['setupState']=self.read(which+'-setup-state',doc);v['setupSelection']=self.text(which+'-setup-text',doc)
        v['inputEnd'],v['requestEnd']=len(self.p['inputs']),len(self.p['requests'])
        v['before']=self.read(which+'-before-state',doc)
        if which=='r1control':
            rule=faults.get('rule',row['control']['rule'])
            r=v['before']['caret'] if rule=='emu' else v['before']['selection']['end']
            v['controlRect']=r;self.place(which+'-control-click',doc,r['x'],r['y']+r['height']//2)
            v['controlState']=self.read(which+'-control-state',doc)
            self.control_position=doc.point
        if row['oracle']=='literal':landing=tuple(row['native']['markerLogical'])+('start',)
        elif which=='r1control' or not hasattr(self,'control_landing'):landing=doc.moved(doc.point,row['action'])
        else:landing=self.control_landing
        landing=faults.get('landing',landing)
        if which=='r1control':self.control_landing=landing
        v['reply'],arm=self.key(which+'-move',doc,row['productKey']['key'],False,row['action'],landing,faults.get('reply'))
        if faults.get('keep-range'):doc.anchor=(0,0,'start') if doc.point[:2]!=(0,0) else (0,1,'start')
        self.tick(500);v['readback']=self.read(which+'-readback',doc);v['activeSelection']=self.text(which+'-active-selection',doc)
        v['marker']={'generation':self.gen,'inputStart':len(self.p['inputs']),'requestStart':len(self.p['requests']),'at':self.tick()}
        self.p['inputs'].append({'type':'keydown','key':'#','isTrusted':True,'at':self.tick(),'shiftKey':False,'ctrlKey':False,'altKey':False,
                                 'metaKey':False,'repeat':False,'sink':self.sink()})
        self.p['inputs'].append({'type':'beforeinput','inputType':'insertText','data':'#','isTrusted':True,'at':self.tick(),'sink':self.sink()})
        self.revision+=1;self.wire('insertText',{'text':'#'},{'revision':self.revision})
        p,o,_=doc.point;doc.texts[p]=doc.texts[p][:o]+'#'+doc.texts[p][o:]
        v['marker']['inputEnd']=len(self.p['inputs']);v['finalSave']=self.save(which+'-final-save',doc)
        v['marker']['requestEnd']=len(self.p['requests']);v['finalState']=self.read(which+'-final-state',doc)
        self.call(which+'-close',lambda:self.wire('close',{},{}))
    def drag(self,doc,a,b,steps=4):
        paper={'left':0,'top':0,'width':DOC_W,'height':DOC_H};size={'w':DOC_W,'h':DOC_H}
        def event(kind,x,y,buttons):
            self.p['inputs'].append({'type':kind,'at':self.tick(),'isTrusted':True,'clientX':x,'clientY':y,'buttons':buttons,'button':0,
                                     'generation':self.gen,'paper':paper,'size':size})
        event('pointerdown',*a,1);self.place_ops(doc,*a);anchor=doc.point
        for i in range(1,steps+1):
            x,y=round(a[0]+(b[0]-a[0])*i/steps),round(a[1]+(b[1]-a[1])*i/steps);event('pointermove',x,y,1)
            doc.anchor=anchor;doc.point=doc.hit(x,y)
            self.wire('editorSelectRangeV2',{'startXTwips':a[0],'startYTwips':a[1],'endXTwips':x,'endYTwips':y},{})
        event('pointerup',*b,0)

def r1_page(case,browser='chrome',faults=None,order=None,plan=None):
    plan=plan or live_plan();b=Builder(plan,case,browser,faults);row=plan['r1'][case];b.readiness()
    for which in order or ((['r1control'] if row['control'] else [])+['r1cand']):b.arm(which,row)
    b.p['complete']=True;b.p['phase']='complete'
    # Through JSON, as the runner exports the page: no record shares an object with the plan.
    return json.loads(json.dumps(b.p))

def edit_call(page,name,mutate,ops=('getSelection','editorGetStateV2','editorActionV2')):
    """Edit a public call's result and its wire terminal together (the page record separately)."""
    call=next(c for c in page['calls'] if c['name']==name)
    request=next(r for r in page['requests'][call['requestStart']:call['requestEnd']] if r['message']['operation'] in ops)
    reply=next(x for x in page['responses'] if x['generation']==request['generation'] and x['message']['requestId']==request['message']['requestId'])
    for value in (call['result'],reply['message']['result']):mutate(value)
    return call,request,reply

def judged(page,plan=None,browser='chrome'):
    from judge_v23_feature_selection import inspect
    return inspect(page,plan or live_plan(),browser)


class R1Plan(unittest.TestCase):
    """Population, partition and controls come from collect(), not from a hand list."""
    def test_population_partition_and_controls(self):
        plan=live_plan();rows=plan['r1'];data=collected()
        self.assertEqual(sorted(rows),sorted(c['id'] for c in data['cells']));self.assertEqual(len(rows),72)
        self.assertEqual({g:sum(r['group']==g for r in rows.values()) for g in ('main','wrap-keys','wrap-drag')},{'main':42,'wrap-keys':18,'wrap-drag':12})
        wrapped={'s1','s1e','m1r','m1e','s1d','m1d'}
        for r in rows.values():
            # The protocol's owner-proxy decision, restated as its own rule.
            literal=r['key'] in ('Left','Right') or (r['key'] in ('Home','End') and r['shape'] not in wrapped)
            self.assertEqual(r['oracle'],'literal' if literal else 'layout-relative',r['id'])
            self.assertEqual(r['control'] is None,literal,r['id'])
            self.assertEqual(r['productKey'],{'key':cases.R1_KEYS[r['key']],'shiftKey':False})
            f=plan['r1Fixtures'][r['fixture']];self.assertEqual(data['fixtures'][f['path']],f['sha256'])
        self.assertEqual(sum(r['oracle']=='literal' for r in rows.values()),36)
        emuend=sorted(i for i,r in rows.items() if r['control'] and r['control']['rule']=='emuend')
        self.assertEqual(emuend,['wrap-drag/m1d/Down','wrap-drag/s1d/Down','wrap-keys/m1e/Down'])
        self.assertEqual(sorted(i for i,r in rows.items() if r['wrongOldClickControl']),emuend)
        self.assertEqual(rows['wrap-drag/s1d/Down']['wrongOldClickControl']['emulatedLogical'],[0,199])
        self.assertEqual({r['literalPremise'] for r in rows.values() if r['oracle']=='literal' and r['key'] in ('Home','End')},
                         {'single-visual-line','hard-break-line','empty-paragraph','table-cell-line'})
        self.assertEqual(sum(1 for r in rows.values() if r['literalPremise']),12)
    def test_index_binding_and_refusals(self):
        self.assertEqual(digest(cases.R1_INDEX.read_bytes()),cases.R1_INDEX_SHA256)
        base=collected()
        def changed(edit):
            data=copy.deepcopy(base);edit(data);return data
        refusals=(('missing cell',lambda d:d['cells'].pop()),
                  ('unknown shape',lambda d:d['cells'][0].update(shape='s9')),
                  ('native made',lambda d:d['cells'][0]['native'].update(made='BETA GAMMB')),
                  ('marker text',lambda d:d['cells'][0]['native'].update(text=d['cells'][0]['native']['text'].replace('#','')+'#x')),
                  ('fixture pin',lambda d:d['fixtures'].update({k:'0'*64 for k in d['fixtures']})),
                  ('emuend control',lambda d:d['wrongOldClickControls'].pop()),
                  ('uncollapsed native',lambda d:d['cells'][0]['native'].update(selectedAfterKey='x')))
        for name,edit in refusals:
            with self.subTest(name=name),self.assertRaises(ValueError):cases.r1(changed(edit))
        self.assertEqual(cases.r1(changed(lambda d:None))[0],live_plan()['r1'])
    def test_recipes_reproduce_native_semantics_with_native_wraps(self):
        # The native discover rows give W=101 (S1) and B=89 (token); the as-run made texts follow.
        self.assertEqual(cases.r1_native_wraps(collected()),{'s1':101,'m1':89})
        rows=live_plan()['r1']
        for shape,anchor,point in (('p2-forward',[1,9],[1,19]),('p2-backward',[1,19],[1,9]),('s1',[0,91],[0,101]),('s2',[1,9],[1,20]),
                                   ('s3',[2,25],[3,0]),('s4',[5,3],[5,10]),('s5',[5,11],[6,0]),('s1e',[0,91],[0,100]),('m1r',[0,79],[0,89]),
                                   ('m1e',[0,79],[0,89]),('s1d',[0,91],[0,101]),('m1d',[0,80],[0,89])):
            row=next(r for r in rows.values() if r['shape']==shape)
            self.assertEqual(row['native']['setupLogical'],{'anchor':anchor,'point':point},shape)
        # Native-only cross-checks of the endpoint rules (native pixels compared with native pixels).
        native={(c['shape'],c['key']):c['native'] for c in collected()['cells']}
        rect=lambda s:tuple(map(int,s.split(',')[:2]))
        st=lambda shape:native[(shape,'Left')]['selectionState']
        for shape in ('p2-forward','s1','s2','s3','s4','m1r'):
            self.assertEqual(rect(st(shape)['INVALIDATE_VISIBLE_CURSOR']),rect(st(shape)['TEXT_SELECTION_END']),shape)
        self.assertEqual(rect(st('p2-backward')['INVALIDATE_VISIBLE_CURSOR']),rect(st('p2-backward')['TEXT_SELECTION_START']))
        self.assertEqual(rect(st('s5')['TEXT_SELECTION_END']),rect(native[('s4','End')]['cursorAfter']))   # A1 end
        self.assertEqual(rect(st('s5')['TEXT_SELECTION_START']),rect(native[('s4','Right')]['cursorAfter']))   # A1:11
        for shape in ('m1e','s1d','m1d'):   # the two-location shapes
            cursor,end=rect(st(shape)['INVALIDATE_VISIBLE_CURSOR']),rect(st(shape)['TEXT_SELECTION_END'])
            self.assertEqual(cursor[1],rect(st(shape)['TEXT_SELECTION_START'])[1]);self.assertGreater(end[1],cursor[1])
        self.assertEqual(rect(st('s1e')['INVALIDATE_VISIBLE_CURSOR']),rect(st('s1e')['TEXT_SELECTION_END']))
    def test_made_text_alone_does_not_pin_the_token_wrap(self):
        # Why literal rows carry the setup-logical premise: the token's ten letters recur.
        token=live_plan()['r1Fixtures']['arrow-selection-wrap']['paragraphs'][0]
        starts=[i for i in range(len(token)) if token.startswith('insxchmrwb',i)]
        self.assertEqual(starts,[12,79,110,141,172,208,239,270,301])
        shapes=live_plan()['r1Fixtures']['arrow-selection-shapes']['paragraphs'][0]
        self.assertEqual([i for i in range(len(shapes)) if shapes.startswith('scar papa ',i)],[91])


class R1MarkerMapping(unittest.TestCase):
    """Native `.uno:SelectAll` text -> (paragraph, code-point offset), over all 216 retained observations."""
    def test_every_native_observation_maps_uniquely_and_round_trips(self):
        plan=live_plan();fixtures=cases.r1_fixtures(collected());count=0
        for cell in collected()['cells']:
            row=plan['r1'][cell['id']]
            for ref in cell['observations']:
                lines=(ROOT/ref['path']).read_text().splitlines();record=json.loads(lines[ref['line']-1])
                self.assertEqual((record['kind'],record['shape'],record['key'],record['round']),('ref',cell['shape'],cell['key'],ref['round']))
                stem,position=cases.r1_marker(fixtures,record['text'])
                self.assertEqual((stem,list(position)),(row['fixture'],row['native']['markerLogical']),cell['id'])
                count+=1
        self.assertEqual(count,216)
    def test_rendering_positions_are_a_bijection(self):
        for stem,f in cases.r1_fixtures(collected()).items():
            rendering,spans=cases.r1_rendering(f['paragraphs'],f['containers'])
            seen=set()
            for g in range(len(rendering)+1):
                position=cases.r1_position(spans,g);self.assertEqual(cases.r1_index(spans,position),g);seen.add(position)
            self.assertEqual(len(seen),len(rendering)+1,stem)
    def test_topology_and_saved_marker(self):
        f=cases.r1_fixtures(collected())['arrow-selection-shapes']
        self.assertEqual(f['rendering'].split('\n')[6:8],['S4 cell A1 text\tS4 cell B1 text','S4 cell A2 text\tS4 cell B2 text'])
        texts=f['paragraphs'];marked=list(texts);marked[1]=marked[1][:21]+'#'+marked[1][21:]
        self.assertEqual(cases.r1_saved_marker(marked,texts),(1,21))
        for bad in ([*marked[:1],marked[1].replace('#','##'),*marked[2:]],texts,[*marked[:2],'x'+marked[2],*marked[3:]],marked[:-1]):
            self.assertIsNone(cases.r1_saved_marker(bad,texts))
        with self.assertRaises(ValueError):cases.r1_marker({'x':f},'no marker')


class R1ReaderBaseline(unittest.TestCase):
    """Every cell's synthetic page reads PASS: the reader consumes the page shape the overlay writes."""
    def test_all_72_cells_pass_on_the_model(self):
        for case,row in live_plan()['r1'].items():
            with self.subTest(case=case):
                value=judged(r1_page(case));self.assertEqual(value['verdict'],'PASS',value)
                self.assertEqual(value['groups']['R1']['oracle'],row['oracle'])
    def test_aggregate_is_per_cell_and_lists_the_three_controls(self):
        from judge_v23_feature_selection import judge
        plan=live_plan();cells=[{'browser':b,'caseId':c,'page':r1_page(c,b)} for b in ('chrome','firefox') for c in plan['r1']]
        result=judge(cells,plan,'r1');g=result['groups']['R1']
        self.assertEqual((result['verdict'],result['populationComplete'],g['required'],g['observed']),('PASS',True,144,144))
        self.assertEqual(sorted((x['cell'][0],x['cell'][1]) for x in g['wrongOldClickControls']),
                         sorted((b,c) for b in ('chrome','firefox') for c in ('wrap-drag/m1d/Down','wrap-drag/s1d/Down','wrap-keys/m1e/Down')))
        self.assertEqual(g['oracleCellsPerBrowser'],{'literal':36,'layout-relative':36})
        # One FAIL fails R1; one missing cell leaves it NOT_ESTABLISHED.
        bad=[*cells[:-1],{**cells[-1],'page':r1_page(cells[-1]['caseId'],'firefox',faults={'r1cand':{'reply':lambda v:v.update(changed=True)}})}]
        self.assertEqual(judge(bad,plan,'r1')['verdict'],'FAIL')
        self.assertEqual(judge(cells[:-1],plan,'r1')['verdict'],'NOT_ESTABLISHED')
        self.assertEqual(judge(cells+cells[-1:],plan,'r1')['verdict'],'NOT_ESTABLISHED')


class R1ReaderRedCases(unittest.TestCase):
    """The protocol's last section: no setup, missing control, nonpublic request, uncollapsed result,
    changed revision, missing marker/export, late/error/recovery never PASS; a valid setup with a
    mismatching landing is FAIL.  Plus the shape, wrap, premise and control witnesses."""
    LITERAL='main/p2-forward/Left';LAYOUT='main/s1/Down';DRAG='wrap-drag/s1d/Up';EMUEND='wrap-drag/m1d/Down';TOKEN='wrap-keys/m1r/Down'
    def expect(self,page,verdict,reason):
        value=judged(page);self.assertEqual((value['verdict'],value.get('reason')),(verdict,reason),value)
    def setup_state(self,page,arm,mutate):
        for name in ('-setup-state','-before-state'):edit_call(page,arm+name,mutate)
        for field in ('setupState','before'):mutate(page[arm][field])
    # -- setup / shape (NE) --
    def test_no_setup(self):
        page=r1_page(self.LITERAL);page.pop('r1cand');page['complete']=True
        self.assertEqual(judged(page)['verdict'],'NOT_ESTABLISHED')
    def test_setup_text_differs(self):
        page=r1_page(self.LITERAL);edit=lambda v:v.update(text='BETA GAMM')
        edit_call(page,'r1cand-setup-text',edit);edit(page['r1cand']['setupSelection'])
        self.expect(page,'NOT_ESTABLISHED','R1 setup selected text differs from native')
    def test_setup_made_no_range(self):
        page=r1_page(self.LITERAL);self.setup_state(page,'r1cand',lambda v:v['selection'].update(collapsed=True))
        self.expect(page,'NOT_ESTABLISHED','R1 setup made no range')
    def test_setup_point_differs(self):
        page=r1_page(self.LITERAL);self.setup_state(page,'r1cand',lambda v:v['caret'].update(x=v['caret']['x']+CW))
        self.expect(page,'NOT_ESTABLISHED','R1 setup point/affinity differs')
    def test_drag_point_not_at_line_end(self):
        page=r1_page(self.DRAG);self.setup_state(page,'r1cand',lambda v:v['caret'].update(y=v['caret']['y']+LH))
        self.expect(page,'NOT_ESTABLISHED','R1 setup point not displayed at the end of line 1')
    def test_setup_endpoints_differ(self):
        page=r1_page(self.DRAG);self.setup_state(page,'r1cand',lambda v:v['selection']['end'].update(y=v['selection']['end']['y']-LH))
        self.expect(page,'NOT_ESTABLISHED','R1 setup selection endpoints differ')
    def test_wrong_fixture(self):
        page=r1_page(self.LITERAL);page['r1cand']['open']['name']='feature-selection.odt'
        self.expect(page,'NOT_ESTABLISHED','R1 fixture alias differs')
        page=r1_page(self.LITERAL);page['r1cand']['open']['fixtureSha256']='0'*64
        self.expect(page,'NOT_ESTABLISHED','opened fixture differs')
    def test_original_differs(self):
        page=r1_page(self.LITERAL);fixture=live_plan()['r1Fixtures']['arrow-selection']['paragraphs']
        art,raw=saved(['x'+fixture[0],*fixture[1:]]);page['r1cand']['originalSave']=art
        call=next(c for c in page['calls'] if c['name']=='r1cand-original-save');call['result']={'bytes':binary(raw)}
        req=page['requests'][call['requestStart']]
        next(x for x in page['responses'] if x['message']['requestId']==req['message']['requestId'] and x['generation']==req['generation'])['message']['result']={'buffer':binary(raw)}
        self.expect(page,'NOT_ESTABLISHED','fresh original differs')
    # -- wrap discovery --
    def test_wrap_transition_and_result(self):
        page=r1_page(self.LAYOUT);v=page['r1cand']['walk'];step=v['steps'][3]
        edit_call(page,'r1cand-walk-step-4',lambda s:s['caret'].update(y=s['caret']['y']+1));step['caret']['y']+=1
        self.expect(page,'NOT_ESTABLISHED','wrap discovery transition differs')
        page=r1_page(self.LAYOUT);page['r1cand']['walk']['wrap']+=1
        self.expect(page,'NOT_ESTABLISHED','wrap discovery result differs')
    def test_arms_disagree_on_the_wrap(self):
        page=r1_page(self.TOKEN,faults={'r1cand':{'wraps':{'arrow-selection-wrap':{0:120}}}})
        self.expect(page,'NOT_ESTABLISHED','arms disagree on the visual wrap')
    def test_drag_end_is_recomputed(self):
        page=r1_page(self.DRAG);page['r1cand']['dragEnd']['x']+=1
        self.expect(page,'NOT_ESTABLISHED','drag end not derived from public geometry')
    # -- control (NE) --
    def test_missing_control(self):
        page=r1_page(self.LAYOUT,order=['r1cand'])
        self.expect(page,'NOT_ESTABLISHED','independent control arm absent/undeclared')
    def test_control_after_candidate(self):
        page=r1_page(self.LAYOUT,order=['r1cand','r1control'])
        self.expect(page,'NOT_ESTABLISHED','control not established before the candidate key')
    def test_emuend_rule_is_the_selection_end(self):
        page=r1_page(self.EMUEND,faults={'r1control':{'rule':'emu'}})
        self.expect(page,'NOT_ESTABLISHED','control rectangle is not the shape rectangle')
        self.assertEqual(judged(r1_page(self.EMUEND))['groups']['R1']['controlRule'],'emuend')
    def test_control_click_and_witness(self):
        page=r1_page(self.LAYOUT);call=next(c for c in page['calls'] if c['name']=='r1control-control-click')
        next(r for r in page['requests'][call['requestStart']:call['requestEnd']] if r['message']['operation'] in ('click','editorPlaceCaretV2'))['message']['payload']['yTwips']+=1
        self.expect(page,'NOT_ESTABLISHED','control click differs')
        page=r1_page(self.LAYOUT);edit=lambda v:v['caret'].update(x=v['caret']['x']+CW)
        edit_call(page,'r1control-control-state',edit);edit(page['r1control']['controlState'])
        self.expect(page,'NOT_ESTABLISHED','control point/affinity not witnessed')
    def test_control_outcome_is_an_oracle_not_a_product_result(self):
        page=r1_page(self.LAYOUT,faults={'r1control':{'reply':lambda v:v.update(changed=True)}})
        self.expect(page,'NOT_ESTABLISHED','independent control outcome invalid: measured move changed the document/revision: changed')
    # -- candidate request (NE) --
    def test_nonpublic_candidate_request(self):
        page=r1_page(self.LITERAL);arm=next(a for a in page['keyArms'] if a['name']=='r1cand-move')
        page['inputs'][arm['inputStart']]['isTrusted']=False
        self.expect(page,'NOT_ESTABLISHED','wrong actual product key')
        # A collapse click between the shape and the key: the product did not move from the range.
        page=r1_page(self.LITERAL);call=next(c for c in page['calls'] if c['name']=='r1cand-move')
        click=copy.deepcopy(page['requests'][call['requestStart']]);click['message'].update(operation='click',requestId=10**6,payload={'documentHandle':click['generation'],'xTwips':1,'yTwips':1})
        click['at']-=0.5;page['requests'].append(click)
        self.expect(page,'NOT_ESTABLISHED','unplanned mutation between the shape and the delayed read')
    def test_error_and_late(self):
        page=r1_page(self.LITERAL);_,_,reply=edit_call(page,'r1cand-move',lambda v:None);reply['message']['ok']=False
        self.expect(page,'NOT_ESTABLISHED','missing/refused terminal r1cand-move')
        page=r1_page(self.LITERAL);call=next(c for c in page['calls'] if c['name']=='r1cand-readback')
        for r in page['requests'][call['requestStart']:call['requestEnd']]:r['at']-=450
        call['startedAt']-=450
        self.expect(page,'NOT_ESTABLISHED','readback too early')
        page=r1_page(self.LITERAL);m=page['r1cand']['marker'];key=[x for x in page['inputs'][m['inputStart']:m['inputEnd']] if x['type']=='keydown'][0]
        key['at']=0
        self.expect(page,'NOT_ESTABLISHED','marker typed before the delayed read')
    # -- candidate outcome (FAIL) --
    def test_changed_revision_fails(self):
        for edit,fields in ((lambda v:v.update(changed=True),'changed'),(lambda v:v.update(revision=v['revision']+1),'revision,delayed-revision')):
            with self.subTest(fields=fields):
                self.expect(r1_page(self.LITERAL,faults={'r1cand':{'reply':edit}}),'FAIL','measured move changed the document/revision: '+fields)
    def test_uncollapsed_result_fails(self):
        self.expect(r1_page(self.LITERAL,faults={'r1cand':{'keep-range':True}}),'FAIL','measured move result not collapsed')
    def test_mismatching_landing_fails(self):
        self.expect(r1_page(self.LITERAL,faults={'r1cand':{'landing':(1,17,'start')}}),'FAIL','logical landing differs from native')
        self.expect(r1_page(self.LAYOUT,faults={'r1cand':{'landing':(0,203,'start')}}),'FAIL','logical landing differs from the control')
    def test_same_offset_other_affinity_fails(self):
        # m1r/End: the control lands at the end of line 2, displayed there (affinity 'end').
        case='wrap-keys/m1r/End';base=judged(r1_page(case));self.assertEqual(base['verdict'],'PASS',base)
        self.assertEqual(base['groups']['R1']['landing'],[0,178])
        self.expect(r1_page(case,faults={'r1cand':{'landing':(0,178,'start')}}),'FAIL','caret differs from the control')
    def test_recovery_fails(self):
        page=r1_page(self.LITERAL);page['events'].append({'generation':3,'at':1,'message':{'kind':'event','event':'worker-restart'}})
        self.expect(page,'FAIL','recovery occurred')
    # -- marker / export (NE) --
    def test_missing_marker(self):
        page=r1_page(self.LITERAL);m=page['r1cand']['marker']
        for x in page['inputs'][m['inputStart']:m['inputEnd']]:
            if x['type']=='keydown':x['isTrusted']=False
        self.expect(page,'NOT_ESTABLISHED','marker key absent or not one trusted press')
        page=r1_page(self.LITERAL);m=page['r1cand']['marker']
        for x in page['inputs'][m['inputStart']:m['inputEnd']]:
            if x['type']=='beforeinput':x['data']='3'
        self.expect(page,'NOT_ESTABLISHED','marker beforeinput absent')
        page=r1_page(self.LITERAL);m=page['r1cand']['marker']
        insert=next(r for r in page['requests'][m['requestStart']:m['requestEnd']] if r['message']['operation']=='insertText')
        insert['message']['payload']['text']='x'
        self.expect(page,'NOT_ESTABLISHED','marker insertion absent/extra')
    def test_missing_or_wrong_export(self):
        page=r1_page(self.LITERAL);page['calls']=[c for c in page['calls'] if c['name']!='r1cand-final-save']
        self.assertEqual(judged(page)['verdict'],'NOT_ESTABLISHED')
        page=r1_page(self.LITERAL);texts=live_plan()['r1Fixtures']['arrow-selection']['paragraphs']
        art,raw=saved([texts[0],texts[1][:18]+'##'+texts[1][18:],texts[2]]);page['r1cand']['finalSave']=art
        call=next(c for c in page['calls'] if c['name']=='r1cand-final-save');call['result']={'bytes':binary(raw)}
        req=page['requests'][call['requestStart']]
        next(x for x in page['responses'] if x['message']['requestId']==req['message']['requestId'] and x['generation']==req['generation'])['message']['result']={'buffer':binary(raw)}
        self.expect(page,'NOT_ESTABLISHED','export is not the fixture plus one marker')
        page=r1_page(self.LITERAL);m=page['r1cand']['marker']
        insert=next(r for r in page['requests'][m['requestStart']:m['requestEnd']] if r['message']['operation']=='insertText')
        reply=next(x for x in page['responses'] if x['message']['requestId']==insert['message']['requestId'] and x['generation']==insert['generation'])
        reply['at']=10**9
        self.expect(page,'NOT_ESTABLISHED','export precedes the marker insertion')
    # -- literal premises (NE) --
    def test_token_wrap_exposure_is_recorded_not_decided(self):
        # Open question Q1 (r1-source/README.md): the token's ten letters recur, so a browser that
        # wrapped at 120 would make the native text at 110..120 and its literal Left/Right rows read
        # FAIL against the native absolute position.  Recorded on the reason, never turned into NE.
        for case,landing in (('wrap-keys/m1r/Left',119),('wrap-drag/m1d/Right',121)):
            self.assertIs(judged(r1_page(case))['groups']['R1']['setupAtNativePosition'],True)
            # The modelled product moves one character from its own point at 120, as Writer does.
            page=r1_page(case,faults={'wraps':{'arrow-selection-wrap':{0:120}},'r1cand':{'landing':(0,landing,'start')}})
            self.expect(page,'FAIL','logical landing differs from native (setup not at the native logical position)')
        # The same layout leaves a layout-relative cell comparable against its own control.
        self.assertEqual(judged(r1_page('wrap-keys/m1r/Down',faults={'wraps':{'arrow-selection-wrap':{0:120}}}))['verdict'],'PASS')
    def test_literal_home_end_premise(self):
        for case,wraps,kind in (('main/p2-forward/Home',{'arrow-selection':{1:12}},'single-visual-line'),
                                ('main/s4/End',{'arrow-selection-shapes':{0:101,5:6}},'table-cell-line'),
                                ('main/s2/Home',{'arrow-selection-shapes':{0:101,1:12}},'hard-break-line')):
            with self.subTest(case=case):
                self.assertEqual(judged(r1_page(case))['groups']['R1']['premise'],kind)
                self.expect(r1_page(case,faults={'wraps':wraps}),'NOT_ESTABLISHED','literal premise not witnessed: '+kind)
        self.assertEqual(judged(r1_page('main/s3/Home'))['groups']['R1']['premise'],'empty-paragraph')


def insert_request(page,index,request):
    """Insert a raw request and shift every recorded request window past it."""
    page['requests'].insert(index,request)
    def shift(record):
        for k in ('requestStart','requestEnd'):
            if type(record.get(k)) is int and record[k]>=index+(k=='requestStart'):record[k]+=1
    for call in page['calls']:shift(call)
    for arm in ('r1control','r1cand'):
        if arm in page:shift(page[arm]);shift(page[arm].get('marker') or {})

def by_name(page,name):return next(c for c in page['calls'] if c['name']==name)
def window(page,name,ops):
    c=by_name(page,name);return next(r for r in page['requests'][c['requestStart']:c['requestEnd']] if r['message']['operation'] in ops)
def terminal(page,request):
    return next(x for x in page['responses'] if x['generation']==request['generation'] and x['message']['requestId']==request['message']['requestId'])

class R1ReaderEvidenceBinding(unittest.TestCase):
    """One red case per remaining R1 reader check (the mutation sweep's census needs each)."""
    LITERAL='main/p2-forward/Left';LAYOUT='main/s1/Down';DRAG='wrap-drag/s1d/Up'
    def run_case(self,case,mutate,reason,verdict='NOT_ESTABLISHED',plan=None):
        page=r1_page(case,plan=plan);plan=plan or live_plan();mutate(page,plan)
        value=judged(page,plan);self.assertEqual((value['verdict'],value.get('reason')),(verdict,reason),value)
    def test_walk_binding(self):
        def plan_input(p,_):p['r1cand']['walk']['plan']['limit']+=1
        def query(p,_):window(p,'r1cand-walk-search',('search',))['message']['payload']['query']+='x'
        def boxes(p,_):p['r1cand']['walk']['boxes'][0][2]+=1
        def click(p,_):window(p,'r1cand-walk-search-click',('click','editorPlaceCaretV2'))['message']['payload']['yTwips']+=1
        def start(p,_):
            edit=lambda v:v['caret'].update(x=v['caret']['x']+1);edit_call(p,'r1cand-walk-start-state',edit);edit(p['r1cand']['walk']['start'])
        def empty(p,_):p['r1cand']['walk']['steps']=[]
        def order(p,_):
            a,b=by_name(p,'r1cand-walk-step-1'),by_name(p,'r1cand-walk-step-2');a['name'],b['name']=b['name'],a['name']
            s=p['r1cand']['walk']['steps'];s[0],s[1]=s[1],s[0]
        for mutate,reason in ((plan_input,'wrap discovery input differs'),(query,'query differs'),(boxes,'unbound page search boxes'),
                              (click,'actual text-start click differs'),(start,'actual text start caret differs'),
                              (empty,'wrap discovery walk absent or unbounded'),(order,'wrap discovery call order differs')):
            with self.subTest(reason=reason):self.run_case(self.LAYOUT,mutate,reason)
    def test_drag_needs_paper_right_of_the_line(self):
        def narrow(p,_):
            opened=next(r for r in p['requests'] if r['generation']==p['r1cand']['open']['generation'] and r['message']['operation']=='open')
            terminal(p,opened)['message']['result']['width']=RIGHT
        self.run_case(self.DRAG,narrow,'no paper right of the first displayed line')
    def test_marker_binding(self):
        def no_window(p,_):p['r1cand']['marker'].pop('inputEnd')
        def sink(p,_):
            m=p['r1cand']['marker'];next(x for x in p['inputs'][m['inputStart']:m['inputEnd']] if x['type']=='keydown')['sink']['active']=False
        def refused(p,_):
            m=p['r1cand']['marker'];r=next(x for x in p['requests'][m['requestStart']:m['requestEnd']] if x['message']['operation']=='insertText')
            terminal(p,r)['message']['ok']=False
        def mutation(p,_):
            m=p['r1cand']['marker'];r=next(x for x in p['requests'][m['requestStart']:m['requestEnd']] if x['message']['operation']=='insertText')
            extra=copy.deepcopy(r);extra['message'].update(operation='editorActionV2',requestId=10**6,payload={'documentHandle':r['generation'],'action':'move-character-left'})
            insert_request(p,p['requests'].index(r)+1,extra)
        for mutate,reason in ((no_window,'marker window absent'),(sink,'marker key not in the editable document sink'),
                              (refused,'marker insertion refused'),(mutation,'unplanned mutation around the marker')):
            with self.subTest(reason=reason):self.run_case(self.LITERAL,mutate,reason)
    def test_setup_binding(self):
        def population(p,_):p['r1cand']['points'].pop('point')
        def kind(p,_):
            edit=lambda v:v.update(selectionType='none');edit_call(p,'r1cand-setup-text',edit);edit(p['r1cand']['setupSelection'])
        def anchor(p,_):window(p,'r1cand-anchor-click',('click','editorPlaceCaretV2'))['message']['payload']['xTwips']+=1
        def changed(p,_):
            edit=lambda v:v['caret'].update(x=v['caret']['x']+1);edit_call(p,'r1cand-before-state',edit);edit(p['r1cand']['before'])
        for mutate,reason in ((population,'point discovery population differs'),(kind,'R1 setup selection type absent'),
                              (anchor,'shape anchor differs'),(changed,'shape changed before measured key')):
            with self.subTest(reason=reason):self.run_case(self.LITERAL,mutate,reason)
    def test_key_and_reply_binding(self):
        def order(p,_):
            move=window(p,'r1cand-move',('editorActionV2',));before=window(p,'r1cand-before-state',('editorGetStateV2',))
            terminal(p,before)['at']=move['at']+0.5;by_name(p,'r1cand-before-state')['finishedAt']=move['at']+0.5
        def reply(p,_):p['r1cand']['reply']['completion']='other'
        def accounting(p,_):
            edit=lambda v:v.pop('changed');edit_call(p,'r1cand-move',edit);edit(p['r1cand']['reply'])
        def early(p,_):
            c=by_name(p,'r1cand-active-selection');r=window(p,'r1cand-active-selection',('getSelection',))
            rb=terminal(p,window(p,'r1cand-readback',('editorGetStateV2',)));r['at']=rb['at']-0.5;c['startedAt']=r['at']-0.5
        for mutate,reason in ((order,'measured key ownership/order differs'),(reply,'actual measured reply differs'),
                              (accounting,'move accounting witness missing'),(early,'active selection precedes delayed state')):
            with self.subTest(reason=reason):self.run_case(self.LITERAL,mutate,reason)
    def test_page_binding(self):
        def incomplete(p,_):p['complete']=False
        def worker(p,_):p['workers'].append({'generation':99,'url':'./profiles/'+PROFILE+'/sdk-worker.js'})
        def opened(p,_):
            r=copy.deepcopy(next(x for x in p['requests'] if x['message']['operation']=='open'));r['generation']=99;p['requests'].append(r)
        for mutate,reason in ((incomplete,'incomplete page'),(worker,'fresh arms/recovery generation differs'),(opened,'extra/missing open')):
            with self.subTest(reason=reason):self.run_case(self.LITERAL,mutate,reason)
    def test_plan_control_declaration(self):
        plan=copy.deepcopy(live_plan());plan['r1'][self.LAYOUT]['control']=None
        def rebind(p,q):p['configSha256']=digest(encoded(q))
        page=r1_page(self.LAYOUT);rebind(page,plan)
        value=judged(page,plan);self.assertEqual((value['verdict'],value['reason']),('NOT_ESTABLISHED','R1 control declaration differs'))


class R1SourcePaths(unittest.TestCase):
    """The page's point plan equals the Python one; the runner's R1 orchestration and mirror."""
    def test_js_point_plan_equals_python(self):
        plan=live_plan();script=(PROJECT/'web/v23-feature-selection.js').read_text()
        fn=script[script.index('const codePoints='):script.index('// The first visual wrap W')]
        jobs=[];want=[]
        for row in plan['r1'].values():
            texts=plan['r1Fixtures'][row['fixture']]['paragraphs']
            for spec in row['setup']['points']:
                for wrap in ((101,89,120) if spec.get('wrapDelta') is not None else (None,)):
                    try:value=cases.r1_point_plan(texts,spec,wrap)
                    except ValueError:value='refused'
                    jobs.append([texts,spec,wrap]);want.append(value)
        jobs.append([['', 'a'],{'name':'x','paragraph':0,'kind':'offset','offset':0},None]);want.append('refused')
        check=fn+"\nconst jobs="+json.dumps(jobs)+";\nconst out=jobs.map(([t,s,w])=>{try{return r1PointPlan(t,s,w);}catch(e){return 'refused';}});\nprocess.stdout.write(JSON.stringify(out));"
        run=subprocess.run(['node','--input-type=module'],input=check,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout),want)
        self.assertGreater(len(want),150)
    def test_runner_r1_sequence(self):
        from unittest.mock import patch
        import run_v23_feature_selection as runner
        plan=live_plan()
        for case,arms in (('main/p2-forward/Left',['r1cand']),('wrap-drag/m1d/Down',['r1control','r1cand']),('wrap-keys/s1e/Up',['r1control','r1cand'])):
            row=plan['r1'][case];log=[]
            with patch.object(runner,'fresh',lambda s,t,n:log.append(('fresh',n))),\
                 patch.object(runner,'control',lambda s,e:log.append(('control',e)) or {'method':row['setup']['method'],'points':[{},{}],'size':{}}),\
                 patch.object(runner,'product_key',lambda s,b,n,k,sh:log.append(('key',n,k,sh))),\
                 patch.object(runner,'drag',lambda s,b,setup:log.append(('drag',))),\
                 patch.object(runner,'actual_marker',lambda s,b:log.append(('marker',))),\
                 patch.object(runner,'wait_page',lambda s,p:log.append(('wait','insertText' in p))):
                runner.run_r1(None,'chrome',row,Path('/nonexistent'),plan['r1Fixtures'][row['fixture']])
            with self.subTest(case=case):
                self.assertEqual([x[1] for x in log if x[0]=='fresh'],[plan['r1Fixtures'][row['fixture']]['servedName']]*len(arms))
                self.assertEqual([x[1] for x in log if x[0]=='control' and x[1].startswith('prepareR1')],[f'prepareR1("{a}")' for a in arms])
                moves=[x for x in log if x[0]=='key' and x[1].endswith('-move')]
                self.assertEqual(moves,[('key',a+'-move',row['productKey']['key'],False) for a in arms])
                setup=[x for x in log if x[0]=='key' and '-setup-' in x[1]]
                if row['setup']['method']=='drag':self.assertEqual((setup,sum(x[0]=='drag' for x in log)),([],len(arms)))
                else:self.assertTrue(setup and all(x[3] is True for x in setup))
                self.assertEqual(('control','controlPointR1()') in log,'r1control' in arms)
                self.assertEqual(sum(x[0]=='marker' for x in log),len(arms));self.assertEqual(sum(x==('wait',True) for x in log),len(arms))
    def test_chrome_marker_avoids_the_end_virtual_key(self):
        import run_v23_feature_selection as runner
        import v21_input
        sent=[]
        class Session:
            def call(self,method,params):sent.append(params)
        runner.actual_marker(Session(),'chrome')
        self.assertEqual([(p['type'],p['key'],p['code'],p['windowsVirtualKeyCode']) for p in sent],[('keyDown','#','Digit3',51),('keyUp','#','Digit3',51)])
        self.assertEqual(sent[0]['text'],'#')
        # The generic one-character rule would have sent End's virtual key (35) for '#'.
        self.assertEqual(v21_input._cdp_params('#',())[0]['windowsVirtualKeyCode'],v21_input.KEYS['End'][2])
    def test_mirror_serves_each_fixture_under_its_alias(self):
        import tempfile
        from unittest.mock import patch
        import run_v23_feature_selection as runner
        plan=live_plan()
        with tempfile.TemporaryDirectory(prefix='r1-mirror-') as directory:
            target=Path(directory)/'mirror';cases.mirror(target,plan);receipt=cases.verify_mirror(target,plan)
            self.assertEqual(receipt['r1Fixtures'],{f['servedName']:f['sha256'] for f in plan['r1Fixtures'].values()})
            for f in plan['r1Fixtures'].values():
                self.assertTrue(f['servedName'].endswith('.odt'));self.assertEqual((target/f['servedName']).read_bytes(),(ROOT/f['path']).read_bytes())
            class Session:
                def set_file(self,selector,path):self.path=path
            session=Session()
            with patch.object(runner,'evaluate',return_value=1),patch.object(runner,'wait_page') as wait:
                runner.fresh(session,target,'r1-arrow-selection-wrap.odt')
            self.assertEqual(session.path.name,'r1-arrow-selection-wrap.odt')
            self.assertIn("name==='r1-arrow-selection-wrap.odt'",wait.call_args.args[1])
            (target/'r1-arrow-selection.odt').write_bytes(b'changed')
            with self.assertRaises(ValueError):cases.verify_mirror(target,plan)


class PreservedPreparationRereads(unittest.TestCase):
    """Selection and S5 unchanged: every preserved page of selection-prep-07 and s5-prep-03, read by
    the current reader with its own stored config, gives the stored inspection exactly."""
    BASE=PROJECT.parent/'findings/evidence/link-batch-v23/feature-protocol'
    def test_every_preserved_page_keeps_its_verdict(self):
        from judge_v23_feature_selection import inspect
        count=0
        for prep in ('selection-prep-07','s5-prep-03'):
            plan=json.loads((self.BASE/prep/'report.json').read_bytes())['config']
            self.assertNotIn('r1',plan)
            for path in sorted((self.BASE/prep).glob('*.json.gz')):
                cell=json.loads(gzip.decompress(path.read_bytes()))
                with self.subTest(path=path.name):
                    self.assertEqual(json.loads(json.dumps(inspect(cell['page'],plan,cell['browser']))),cell['inspection'])
                count+=1
        self.assertEqual(count,13+22)

if __name__=='__main__':unittest.main()
