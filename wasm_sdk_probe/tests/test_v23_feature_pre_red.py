#!/usr/bin/env python3
"""Raw-wire causal controls for historical pre-red readiness and S2 reading."""
import base64
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from xml.sax.saxutils import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from v23_feature_pre_red_cases import config,WASM,NATIVE_FIXTURE,encoded,digest,mirror,verify_mirror
from judge_v23_feature_pre_red import inspect,judge,s2_compare


def binary(raw):return {'encoding':'base64','bytes':len(raw),'data':base64.b64encode(raw).decode()}
def saved(paragraphs):
    content=('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
             'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:text>'+
             ''.join('<text:p>'+escape(x)+'</text:p>' for x in paragraphs)+
             '</office:text></office:body></office:document-content>').encode()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr('content.xml',content)
    raw=stream.getvalue();return {'base64':base64.b64encode(raw).decode(),'sha256':digest(raw)},raw


def make_page(plan,case='shift-Left@caret-mid',browser='chrome'):
    p={'profile':'e2-editor-v19','caseId':case,'userAgent':'Chrome/140' if browser=='chrome' else 'Firefox/157',
       'servedSources':plan['servedSources'],'artifacts':plan['profile']['artifacts'],
       'configSha256':digest(encoded(plan)),'fixtureManifestSha256':digest(encoded(plan['fixtureManifest'])),
       'complete':True,'requests':[],'responses':[],'events':[],'calls':[],'workers':[],'inputs':[]}
    clock=0;gen=1;identifier=0
    def wire(op,payload,value,name=None):
        nonlocal clock,identifier
        identifier+=1;clock+=4;request={'kind':'request','requestId':identifier,'operation':op,'payload':payload}
        p['requests'].append({'generation':gen,'at':clock+1,'message':request})
        p['responses'].append({'generation':gen,'at':clock+2,'message':{'kind':'response','requestId':identifier,'ok':True,'result':copy.deepcopy(value)}})
        if name:p['calls'].append({'name':name,'generation':gen,'documentHandle':gen,'startedAt':clock,'finishedAt':clock+3,'ok':True,'result':copy.deepcopy(value)})
        return clock
    def call(name,op,payload,value):return wire(op,{'documentHandle':gen,**payload},value,name)
    def state(x=100,revision=0):return {'documentHandle':gen,'revision':revision,'caret':{'x':x,'y':100,'width':0,'height':20},
        'selection':{'collapsed':True,'observed':True,'start':None,'end':None,'rectangles':[]}}
    def open_doc(name):
        wire('open',{'buffer':binary(NATIVE_FIXTURE.read_bytes()),'name':name},{'documentHandle':gen})
        p['workers'].append({'generation':gen,'url':'./profiles/e2-editor-v19/sdk-worker.js'})
        return {'generation':gen,'documentHandle':gen,'name':name,'fixtureSha256':plan['fixtureSha256'],'serial':gen}
    def setup(prefix,discovery):
        call(prefix+'-search','search',{'query':discovery['query']},{'selections':[{'rectangles':'100,100,100,20'}]})
        call(prefix+'-search-click','click',{'xTwips':100,'yTwips':110},{})
        call(prefix+'-home','editorActionV2',{'action':'move-line-home','extendSelection':False},{})
        start=state();call(prefix+'-start-state','editorGetStateV2',{},start)
        offset=discovery['offset'];x=100
        if isinstance(offset,int):
            for n in range(offset):
                x+=10;call(prefix+'-right-'+str(n),'editorActionV2',{'action':'move-character-right','extendSelection':False},{})
            text=discovery['query'][:offset]
        else:
            x+=100;call(prefix+'-end','editorActionV2',{'action':'move-line-end','extendSelection':False},{})
            text=discovery['query']
            if offset=='next-empty':
                call(prefix+'-next-empty','editorActionV2',{'action':'move-character-right','extendSelection':False},{});text+='\n'
        target=state(x);call(prefix+'-target-state','editorGetStateV2',{},target)
        call(prefix+'-prefix-select','editorSelectRangeV2',{'startXTwips':100,'startYTwips':110,'endXTwips':x,'endYTwips':110},{})
        selected={'text':text,'selectionType':'text' if text else 'none'}
        call(prefix+'-prefix-text','getSelection',{},selected)
        call(prefix+'-restore-point','click',{'xTwips':x,'yTwips':110},{})
        call(prefix+'-final-state','editorGetStateV2',{},target)
        return {'plan':discovery,'start':start,'target':target,'final':target,'selected':selected}
    def save(name,text):
        value,raw=saved(text);call(name,'save',{}, {'buffer':binary(raw)})
        p['calls'][-1]['result']={'bytes':binary(raw)}
        return value
    ready={'open':open_doc('list-contexts.odt')};p['readiness']=ready
    ready['setup']=setup('readiness',{'query':plan['fixtureParagraphs'][0],'paragraph':0,'offset':0})
    ready['beforeState']=state();call('readiness-before-state','editorGetStateV2',{},ready['beforeState'])
    ready['beforeSave']=save('readiness-before-save',plan['fixtureParagraphs'])
    ready['beforeInput']={'id':'sink','active':True,'connected':True,'disabled':False,'readOnly':False,'documentHandle':gen,'generation':gen}
    p['inputs']=[{'type':'keydown','at':clock+3.5,'key':'Z','isTrusted':True,'sink':ready['beforeInput']},
                 {'type':'beforeinput','at':clock+3.6,'inputType':'insertText','data':'Z','isTrusted':True,'sink':ready['beforeInput']}]
    wire('insertText',{'documentHandle':gen,'text':'Z'},{'revision':1})
    after=plan['fixtureParagraphs'].copy();after[0]='Z'+after[0]
    ready['afterSave']=save('readiness-after-save',after);ready['afterState']=state(revision=1)
    call('readiness-after-state','editorGetStateV2',{},ready['afterState'])
    gen=2
    measured={'open':open_doc('feature-pre-red.odt')};p['measured']=measured
    measured['originalSave']=save('measured-original-save',plan['fixtureParagraphs'])
    measured['setup']=setup('measured',plan['cases'][case]['discovery'])
    measured['before']=measured['setup']['final'];call('measured-before-state','editorGetStateV2',{},measured['before'])
    reply={'action':plan['cases'][case]['action'],'changed':False,'revision':0,'beforeRevision':0,'state':copy.deepcopy(measured['before'])}
    call('measured-shift','editorActionV2',{'action':plan['cases'][case]['action'],'extendSelection':True},reply)
    measured['reply']=reply;measured['replyAt']=clock+3;clock+=500
    later=copy.deepcopy(measured['before']);later['caret']['x']+=10
    later['selection']['collapsed']=False
    measured['readback']=later;call('measured-readback','editorGetStateV2',{},later)
    measured['activeSelection']={'selectionType':'text','text':'E'}
    call('measured-active-selection','getSelection',{},measured['activeSelection'])
    call('measured-close','close',{}, {})
    return p


class PreRedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=config(WASM)
    def page(self):return make_page(self.plan)
    def assert_ne(self,page):self.assertEqual(inspect(page,self.plan,'chrome')['verdict'],'NOT_ESTABLISHED')
    def test_bound_expected_red(self):self.assertEqual(inspect(self.page(),self.plan,'chrome')['verdict'],'EXPECTED_RED')
    def test_complete_population(self):
        cells=[{'browser':b,'caseId':c,'page':make_page(self.plan,c,b)} for b in ('chrome','firefox') for c in self.plan['cases']]
        self.assertEqual(judge(cells,self.plan)['verdict'],'EXPECTED_RED')
        self.assertEqual(judge(cells[:-1],self.plan)['verdict'],'NOT_ESTABLISHED')
    def test_missing_open_terminal(self):
        p=self.page();p['responses']=p['responses'][1:];self.assert_ne(p)
    def test_wrong_open_handle(self):
        p=self.page();p['readiness']['open']['documentHandle']=99;self.assert_ne(p)
    def test_wrong_state_literal(self):
        p=self.page();next(x for x in p['requests'] if x['message']['operation']=='editorGetStateV2')['message']['operation']='editorGetStateV1';self.assert_ne(p)
    def test_duplicate_terminal(self):
        p=self.page();p['responses'].append(copy.deepcopy(p['responses'][-2]));self.assert_ne(p)
    def test_readiness_refusal_is_not_red(self):
        p=self.page();req=next(r for r in p['requests'] if r['message']['operation']=='insertText')
        next(r for r in p['responses'] if r['message']['requestId']==req['message']['requestId'])['message']['ok']=False;self.assert_ne(p)
    def test_no_saved_edit(self):
        p=self.page();p['readiness']['afterSave']=p['readiness']['beforeSave'];self.assert_ne(p)
    def test_false_focus(self):
        p=self.page();p['readiness']['beforeInput']['active']=False;self.assert_ne(p)
    def test_synthetic_key(self):
        p=self.page();p['inputs'][0]['isTrusted']=False;self.assert_ne(p)
    def test_missing_mutation_but_key_survives(self):
        p=self.page();p['requests']=[r for r in p['requests'] if r['message']['operation']!='insertText'];self.assert_ne(p)
    def test_wrong_browser(self):
        p=self.page();p['userAgent']='Firefox/157';self.assert_ne(p)
    def test_changed_identity(self):
        p=self.page();p['artifacts']=dict(p['artifacts'],**{'probe.wasm':'0'*64});self.assert_ne(p)
    def test_forged_setup_text(self):
        p=self.page();p['measured']['setup']['selected']={'text':'fake','selectionType':'text'};self.assert_ne(p)
    def test_copied_page(self):
        p=self.page();cells=[{'browser':'chrome','caseId':p['caseId'],'page':p},{'browser':'firefox','caseId':p['caseId'],'page':copy.deepcopy(p)}]
        self.assertIn('duplicate',judge(cells,self.plan)['results'][1]['reason'])
    def test_fresh_state_is_unexpected_green(self):
        p=self.page();m=p['measured'];m['reply']['state']=copy.deepcopy(m['readback'])
        c=next(c for c in p['calls'] if c['name']=='measured-shift');c['result']=copy.deepcopy(m['reply'])
        request=next(r for r in p['requests'] if r['message']['operation']=='editorActionV2' and r['message']['payload'].get('extendSelection'))
        next(r for r in p['responses'] if r['message']['requestId']==request['message']['requestId'])['message']['result']=copy.deepcopy(m['reply'])
        self.assertEqual(inspect(p,self.plan,'chrome')['verdict'],'UNEXPECTED_GREEN')
    def test_actual_frozen_mirror_and_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'mirror';mirror(target,self.plan);verify_mirror(target,self.plan)
            path=target/'editor-shell-v2/narrow-editor-v2-client.js';path.write_bytes(path.read_bytes()+b'\n// drift\n')
            with self.assertRaises(ValueError):verify_mirror(target,self.plan)

if __name__=='__main__':unittest.main()
