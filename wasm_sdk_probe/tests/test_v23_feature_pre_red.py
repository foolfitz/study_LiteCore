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
        if name:p['calls'].append({'name':name,'generation':gen,'documentHandle':gen,'requestStart':len(p['requests'])-1,'requestEnd':len(p['requests']),'startedAt':clock,'finishedAt':clock+3,'ok':True,'result':copy.deepcopy(value)})
        return clock
    def call(name,op,payload,value):return wire(op,{'documentHandle':gen,**payload},value,name)
    def state(x=100,revision=0):return {'documentHandle':gen,'revision':revision,'caret':{'x':x,'y':100,'width':0,'height':20},
        'selection':{'collapsed':True,'observed':True,'start':None,'end':None,'rectangles':[]}}
    def open_doc(name):
        wire('open',{'buffer':binary(NATIVE_FIXTURE.read_bytes()),'name':name},{'documentHandle':gen})
        p['workers'].append({'generation':gen,'url':'./profiles/e2-editor-v19/sdk-worker.js'})
        return {'generation':gen,'documentHandle':gen,'name':name,'fixtureSha256':plan['fixtureSha256'],'serial':gen}
    def setup(prefix,discovery):
        call(prefix+'-search','search',{'query':discovery['query']},{'selections':[{'part':'0','rectangles':('100,200,100,20; 100,100,100,20' if discovery.get('anchor')=='search-first-displayed-line' else '100,100,100,20')}]})
        call(prefix+'-search-click','click',{'xTwips':100,'yTwips':110},{})
        if discovery.get('anchor')!='search-text-start':
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


class ListMidSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=config(WASM)
    def test_native_offset_and_prefix_preserved(self):
        for direction in ('Left','Right'):
            case='shift-'+direction+'@list-mid'
            discovery=self.plan['cases'][case]['discovery']
            self.assertEqual(discovery,{'paragraph':7,'offset':5,'query':'List item one','anchor':'search-text-start'})
            page=make_page(self.plan,case)
            self.assertEqual(page['measured']['setup']['selected']['text'],'List ')
            self.assertEqual(inspect(page,self.plan,'chrome')['verdict'],'EXPECTED_RED')
    def test_unplanned_home_rejected(self):
        old=copy.deepcopy(self.plan);case='shift-Left@list-mid'
        del old['cases'][case]['discovery']['anchor']
        page=make_page(old,case)
        page['configSha256']=digest(encoded(self.plan))
        page['measured']['setup']['plan']=self.plan['cases'][case]['discovery']
        result=inspect(page,self.plan,'chrome')
        self.assertEqual(result['verdict'],'NOT_ESTABLISHED')
        self.assertIn('undeclared',result['reason'])
    def test_four_rights_cannot_replace_native_five(self):
        wrong=copy.deepcopy(self.plan);case='shift-Left@list-mid'
        wrong['cases'][case]['discovery']['offset']=4
        page=make_page(wrong,case);page['configSha256']=digest(encoded(self.plan))
        page['measured']['setup']['plan']=self.plan['cases'][case]['discovery']
        self.assertEqual(inspect(page,self.plan,'chrome')['verdict'],'NOT_ESTABLISHED')
    def test_missing_literal_space_rejected_even_when_wire_agrees(self):
        page=make_page(self.plan,'shift-Left@list-mid')
        page['measured']['setup']['selected']['text']='List'
        call=next(c for c in page['calls'] if c['name']=='measured-prefix-text')
        call['result']['text']='List'
        request=next(r for r in page['requests'] if r['message']['operation']=='getSelection'
                     and call['startedAt']<=r['at']<=call['finishedAt'])
        next(r for r in page['responses'] if r['message']['requestId']==request['message']['requestId'])['message']['result']['text']='List'
        result=inspect(page,self.plan,'chrome')
        self.assertEqual(result['verdict'],'NOT_ESTABLISHED')
        self.assertIn('actual setup text',result['reason'])
    def test_start_state_must_be_actual_search_text_start(self):
        page=make_page(self.plan,'shift-Left@list-mid')
        page['measured']['setup']['start']['caret']['x']=99
        call=next(c for c in page['calls'] if c['name']=='measured-start-state')
        call['result']['caret']['x']=99
        request=next(r for r in page['requests'] if r['message']['operation']=='editorGetStateV2'
                     and call['startedAt']<=r['at']<=call['finishedAt'])
        next(r for r in page['responses'] if r['message']['requestId']==request['message']['requestId'])['message']['result']['caret']['x']=99
        selection=next(c for c in page['calls'] if c['name']=='measured-prefix-select')
        next(r for r in page['requests'] if r['message']['operation']=='editorSelectRangeV2'
             and selection['startedAt']<=r['at']<=selection['finishedAt'])['message']['payload']['startXTwips']=99
        result=inspect(page,self.plan,'chrome')
        self.assertEqual(result['verdict'],'NOT_ESTABLISHED')
        self.assertIn('actual search text start',result['reason'])
    def test_actual_locate_does_not_enter_list_label(self):
        import subprocess
        source=(Path(__file__).resolve().parents[1]/'web/v23-feature-pre-red.js').read_text()
        locate='async function locate'+source.split('async function locate',1)[1].split('function fail',1)[0]
        script=r"""
let at=0,range=[0,0];const moves=[];const text='List item one';
const current={document:{search:async()=>({selections:[{rectangles:'100,100,100,20'}]}),
 getSelection:async()=>({text:text.slice(Math.max(0,range[0]),Math.max(0,range[1]))})},
 editor:{selectRange:async(a,b)=>{range=[a.xTwips-100,b.xTwips-100]}}};
const call=async(name,fn)=>await fn();
const place=async p=>{at=p.xTwips-100};
const move=async direction=>{moves.push(direction);if(direction==='line-home')at=-1;else if(direction==='character-right')at++};
const state=async()=>({caret:{x:100+at,y:100,width:0,height:20}});
const point=caret=>({xTwips:caret.x,yTwips:caret.y+Math.floor(caret.height/2)});
"""+locate+r"""
locate({paragraph:7,offset:5,query:text,anchor:'search-text-start'},'measured')
 .then(result=>process.stdout.write(JSON.stringify({text:result.selected.text,moves})))
 .catch(error=>{console.error(error);process.exitCode=1});
"""
        run=subprocess.run(['node','-e',script],text=True,capture_output=True)
        self.assertEqual(run.returncode,0,run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['text'],'List ')
        self.assertEqual(result['moves'],['character-right']*5)


class CallOwnershipTests(unittest.TestCase):
    def test_adjacent_same_clock_calls_keep_actual_request_ownership(self):
        plan=config(WASM);page=make_page(plan)
        first=next(c for c in page['calls'] if c['name']=='readiness-start-state')
        second=next(c for c in page['calls'] if c['name']=='readiness-target-state')
        second['startedAt']=first['finishedAt']
        page['requests'][second['requestStart']]['at']=first['finishedAt']
        self.assertEqual(inspect(page,plan,'chrome')['verdict'],'EXPECTED_RED')

    def test_adjacent_same_clock_mutation_has_one_owner(self):
        plan=config(WASM);page=make_page(plan)
        first=next(c for c in page['calls'] if c['name']=='readiness-search')
        second=next(c for c in page['calls'] if c['name']=='readiness-search-click')
        second['startedAt']=first['finishedAt']
        page['requests'][second['requestStart']]['at']=first['finishedAt']
        self.assertEqual(inspect(page,plan,'chrome')['verdict'],'EXPECTED_RED')

    def test_invalid_or_reassigned_call_ranges_are_ne(self):
        plan=config(WASM)
        for change in ('missing','empty','bool','negative','outside','overlap','wrong-owner'):
            page=make_page(plan);call=page['calls'][0]
            if change=='missing':call.pop('requestStart')
            elif change=='empty':call['requestEnd']=call['requestStart']
            elif change=='bool':call['requestStart']=True
            elif change=='negative':call['requestStart']=-1
            elif change=='outside':call['requestEnd']=len(page['requests'])+1
            elif change=='overlap':call['requestEnd']=page['calls'][1]['requestEnd']
            else:
                a,b=page['calls'][:2]
                a['requestStart'],b['requestStart']=b['requestStart'],a['requestStart']
                a['requestEnd'],b['requestEnd']=b['requestEnd'],a['requestEnd']
            with self.subTest(change=change):
                self.assertEqual(inspect(page,plan,'chrome')['verdict'],'NOT_ESTABLISHED')


class WrapAnchorTests(unittest.TestCase):
    def run_wrap(self, mutate=lambda script:script):
        import subprocess
        source=(Path(__file__).resolve().parents[1]/'web/v23-feature-pre-red.js').read_text()
        locate='async function locate'+source.split('async function locate',1)[1].split('function fail',1)[0]
        script=r"""
let x=1418,y=0,range;const clicks=[],moves=[];const query='W1 first line followed by more text';
const current={document:{search:async()=>({selections:[{part:'0',rectangles:
 '1418,3350,1846,275; 1418,2522,9972,275; 1418,2798,9972,551'}]}),
 getSelection:async()=>({text:y===2522?'W1 first line':'it finally stops here'})},
 editor:{selectRange:async(a,b)=>{range=[a,b]}}};
const call=async(name,fn)=>await fn();
const place=async p=>{clicks.push(p);x=p.xTwips;y=p.yTwips-137};
const move=async direction=>{moves.push(direction);x=direction==='line-home'?1418:11390};
const state=async()=>({caret:{x,y,width:0,height:275},selection:{observed:true,collapsed:true}});
const point=c=>({xTwips:c.x,yTwips:c.y+Math.floor(c.height/2)});
"""+locate+r"""
locate({paragraph:4,offset:'visual-end',query,anchor:'search-first-displayed-line'},'measured')
 .then(value=>process.stdout.write(JSON.stringify({value,clicks,moves})))
 .catch(error=>{console.error(error);process.exitCode=1});
"""
        return subprocess.run(['node','-e',mutate(script)],text=True,capture_output=True)

    def test_actual_js_chooses_first_displayed_line_from_unsorted_search(self):
        run=self.run_wrap()
        self.assertEqual(run.returncode,0,run.stderr)
        actual=json.loads(run.stdout)
        self.assertEqual(actual['clicks'][0],{'xTwips':1418,'yTwips':2659})
        self.assertEqual(actual['value']['start']['caret']['y'],2522)
        self.assertEqual(actual['value']['target']['caret']['y'],2522)
        self.assertEqual(actual['value']['selected']['text'],'W1 first line')
        self.assertEqual(actual['moves'],['line-home','line-end'])

    def test_actual_js_rejects_malformed_and_ambiguous_search(self):
        original='1418,3350,1846,275; 1418,2522,9972,275; 1418,2798,9972,551'
        for raw in ['1418,2522,9972,275; BAD','1418,2522,0,275',
                    '1418,2522,9972,275;1418,2522,9972,275',
                    '1418,2522,9972,275;1418,2522,10,10','']:
            with self.subTest(raw=raw):self.assertNotEqual(self.run_wrap(lambda s:s.replace(original,raw)).returncode,0)
        self.assertNotEqual(self.run_wrap(lambda s:s.replace("part:'0'","part:'1'")).returncode,0)

    def test_reader_derives_minimum_and_rejects_consistent_old_last_line(self):
        plan=config(WASM);case='shift-Left@wrap-line-end'
        self.assertEqual(plan['cases'][case]['discovery']['anchor'],'search-first-displayed-line')
        page=make_page(plan,case)
        self.assertEqual(inspect(page,plan,'chrome')['verdict'],'EXPECTED_RED')
        def alter(value):
            if isinstance(value,dict):
                for k,v in value.items():
                    if k=='y' and v==100:value[k]=200
                    elif k in ('yTwips','startYTwips','endYTwips') and v==110:value[k]=210
                    else:alter(v)
            elif isinstance(value,list):
                for v in value:alter(v)
        alter(page['measured'])
        for group in ('calls','requests','responses'):
            for entry in page[group]:
                if entry['generation']==2:alter(entry)
        # Prefix is deliberately still the acceptable full query; page and wire agree.
        self.assertEqual(inspect(page,plan,'chrome')['verdict'],'NOT_ESTABLISHED')
        for entry in page['requests']:
            if entry['generation']==2 and entry['message']['operation']=='click':
                entry['message']['payload']['yTwips']=110
                break
        verdict=inspect(page,plan,'chrome')
        self.assertEqual(verdict['verdict'],'NOT_ESTABLISHED')
        self.assertIn('first displayed search text start',verdict['reason'])

    def test_reader_rejects_every_bad_rectangle_and_part(self):
        from judge_v23_feature_pre_red import wrap_first_rectangle, NotEstablished
        good={'selections':[{'part':'0','rectangles':'1418,3350,1846,275;1418,2522,9972,275;1418,2798,9972,551'}]}
        self.assertEqual(wrap_first_rectangle(good),(1418,2522,9972,275))
        variants=[None,[],{'selections':[None]},{'selections':[[]]}]
        for raw in ['', '100,100,10,20;bad', '100,100,10,0','100,100,10,20;',
                    '100,100,10,20;100,100,10,20','100,100,10,20;100,100,11,20','１００,100,10,20']:
            v=copy.deepcopy(good);v['selections'][0]['rectangles']=raw;variants.append(v)
        for part in [None,True,'1',1,'0.0']:
            v=copy.deepcopy(good);v['selections'][0]['part']=part;variants.append(v)
        v=copy.deepcopy(good);v['selections']*=2;variants.append(v)
        v=copy.deepcopy(good);v['selections'].append({'part':'1','rectangles':'100,100,10,20'});variants.append(v)
        for value in variants:
            with self.subTest(value=value),self.assertRaises(NotEstablished):wrap_first_rectangle(value)


class ProductNavigationTests(unittest.TestCase):
    def test_product_ready_state_without_probe_metrics(self):
        from run_v23_feature_pre_red import navigate
        from run_browser_probe import ChromeSession
        class FakeChrome(ChromeSession):
            def __init__(self):
                self.calls=[];self.expressions=[];self.generic_calls=0
            def call(self,method,payload):
                self.calls.append((method,payload));return {}
            def navigate(self,url):
                self.generic_calls+=1
                raise RuntimeError('generic navigation requires absent __probe_metrics')
            def evaluate(self,expression):
                self.expressions.append(expression)
                self.assert_ready="document.readyState === 'complete'" in expression
                return self.assert_ready and '__probe_metrics' not in expression
        page=FakeChrome();url='http://127.0.0.1/product'
        # Historical path is red on this loaded product page.
        with self.assertRaisesRegex(RuntimeError,'__probe_metrics'):page.navigate(url)
        navigate(page,url)
        self.assertEqual(page.generic_calls,1)
        self.assertEqual(page.calls,[('Page.navigate',{'url':url})])
        self.assertTrue(page.assert_ready)
        self.assertEqual(len(page.expressions),1)
        self.assertNotIn('__probe_metrics',page.expressions[0])

    def assert_main_product_route(self,main):
        from contextlib import ExitStack, nullcontext, redirect_stdout
        from unittest.mock import Mock, patch
        import run_v23_feature_pre_red as runner
        browser=Mock()
        browser.navigate.side_effect=RuntimeError('generic-route-sentinel')
        navigate=Mock(side_effect=RuntimeError('product-navigation-route-sentinel'))
        case='shift-Left@caret-mid';plan={'cases':{case:{}}}
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            output=Path(directory)/'fresh-output'
            stack.enter_context(patch.object(sys,'argv',['pre-red','--v19-wasm-sha256',WASM,
                '--preparation-only','--browser','chrome','--case-id',case,'--output',str(output)]))
            for name,value in {'config':Mock(return_value=plan),'mirror':Mock(),
                'verify_mirror':Mock(return_value={}), 'navigate':navigate,
                'export_page':Mock(return_value=({},{}))}.items():
                stack.enter_context(patch.object(runner,name,value))
            wait=stack.enter_context(patch.object(runner,'wait_page'))
            ready=stack.enter_context(patch.object(runner,'readiness'))
            for name,value in {'browser_lock':Mock(side_effect=lambda *a:nullcontext()),
                'pre_run_checks':Mock(return_value={}), 'foreign_cpu':Mock(return_value={'ok':True}),
                'served':Mock(side_effect=lambda *a:nullcontext('http://127.0.0.1/product')),
                'open_browser':Mock(return_value=browser), 'close_browser':Mock(return_value={})}.items():
                stack.enter_context(patch.object(runner.common,name,value))
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(SystemExit,'first non-expected-red'):
                main()
            navigate.assert_called_once_with(browser,'http://127.0.0.1/product?caseId=shift-Left%40caret-mid')
            browser.navigate.assert_not_called()
            wait.assert_not_called();ready.assert_not_called()
            report=json.loads((output/'report.json').read_text())
            self.assertEqual(len(report['runs']),1)
            cell=json.loads((output/report['runs'][0]['path']).read_text())
            self.assertIn('product-navigation-route-sentinel',cell['fatal'])

    def test_actual_main_uses_product_navigation(self):
        import run_v23_feature_pre_red as runner
        self.assert_main_product_route(runner.main)

    def test_historical_main_callsite_fails_route_control(self):
        import inspect
        import types
        import run_v23_feature_pre_red as runner
        source=inspect.getsource(runner.main)
        old=source.replace("navigate(session,base+'?'+urlencode({'caseId':case}))",
                           "session.navigate(base+'?'+urlencode({'caseId':case}))")
        self.assertNotEqual(source,old)
        namespace={}
        exec(compile(old,'<historical-main-callsite>','exec'),namespace)
        historical=types.FunctionType(namespace['main'].__code__,runner.__dict__)
        # Execute the actual main body with only its old callsite restored.
        # An unused correct import must not preserve the routing control's green.
        with self.assertRaises(AssertionError):self.assert_main_product_route(historical)

if __name__=='__main__':unittest.main()
