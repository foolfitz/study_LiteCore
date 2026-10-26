"""Causal controls for the public feature selection instruments."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from v23_feature_s_cases import derive,read_rounds
from v23_feature_selection_cases import cases,point_plan,paragraphs,identity,PROFILE,PROJECT

class SourceCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.table=derive(read_rounds())
    def test_exact_source_population_and_references(self):
        rows=cases(self.table)
        self.assertEqual(len(rows),108)
        self.assertEqual(sum('S1' in r['memberships'] for r in rows.values()),84)
        self.assertEqual(sum('S3' in r['memberships'] for r in rows.values()),10)
        for source in self.table['cases']:
            row=rows[source['id']]
            self.assertEqual(row['nativeReferences'],source['nativeReferences'])
            self.assertEqual(row['nativeAfterSelectionText'],source['nativeAfterSelectionText'])
            self.assertFalse(row['reference']['shiftKey'])
            self.assertEqual(row['reference']['fromPoint'],source['setup']['expectedMovingPointName'])
    def test_direction_and_original_native_method_are_not_lost(self):
        rows=cases(self.table)
        self.assertEqual(rows['shift-Left@range-bwd']['anchorPointName'],'p1.19')
        self.assertEqual(rows['shift-Left@range-bwd']['movingPointName'],'p1.9')
        for shape in ('range-bwd','range-fwd','range-one','range-cross'):
            self.assertEqual(rows['shift-Left@'+shape]['nativeSetupMethod'],'drag')
        self.assertEqual(rows['shift-Left@range-kbd']['nativeSetupMethod'],'click+Shift+Right x3')
    def test_bad_membership_or_unmapped_input_refuses(self):
        for kind in ('missing','duplicate','point','method'):
            table=copy.deepcopy(self.table)
            if kind=='missing':table['cases'].pop()
            elif kind=='duplicate':table['cases'].append(table['cases'][0])
            elif kind=='point':table['cases'][0]['setup']['logicalPointNames']=['p999.0']
            else:table['cases'][0]['setup']['method']='guessed-click'
            with self.subTest(kind=kind),self.assertRaises(ValueError):cases(table)
    def test_logical_points_use_codepoints_and_keep_empty_wrap_rules(self):
        text=paragraphs()
        self.assertEqual(point_plan('p5.4',text)['prefix'],'中文段落')
        self.assertEqual(point_plan('p7.5',text)['prefix'],'List ')
        self.assertEqual(point_plan('p3.0',text)['offset'],'next-empty')
        self.assertEqual(point_plan('w.l1end',text)['offset'],'visual-end')
        for bad in ('p1.999','native-x1418-y2522','p-1.0','w.l2end'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):point_plan(bad,text)
    def test_actual_final_feature_shell_profile_and_archive_bind(self):
        value=identity();self.assertEqual(value['profile'],PROFILE)
        self.assertEqual(value['editorAbi'],6)



def synthetic_page(plan,case='shift-Left@caret-mid'):
    from test_v23_feature_pre_red import saved,binary
    from v23_feature_selection_cases import encoded,digest,FIXTURE
    p={'profile':PROFILE,'caseId':case,'userAgent':'Chrome/150','servedSources':plan['servedSources'],
       'artifacts':plan['profile']['artifacts'],'configSha256':digest(encoded(plan)),
       'fixtureManifestSha256':digest(encoded(plan['fixtureManifest'])),'complete':True,
       'requests':[],'responses':[],'events':[],'workers':[],'calls':[],'inputs':[],'keyArms':[]}
    gen=0;clock=0;identifier=0
    def wire(op,payload,value,name=None):
        nonlocal clock,identifier
        identifier+=1;clock+=4;index=len(p['requests'])
        r={'generation':gen,'at':clock+1,'message':{'kind':'request','requestId':identifier,'operation':op,'payload':{'documentHandle':gen,**payload}}}
        t={'generation':gen,'at':clock+2,'message':{'kind':'response','requestId':identifier,'ok':True,'result':copy.deepcopy(value)}}
        p['requests'].append(r);p['responses'].append(t)
        if name:p['calls'].append({'name':name,'generation':gen,'documentHandle':gen,'requestStart':index,'requestEnd':index+1,'startedAt':clock,'finishedAt':clock+3,'ok':True,'result':copy.deepcopy(value)})
        return r,t
    def state(par=0,offset=0,revision=0):return {'documentHandle':gen,'revision':revision,'caret':{'x':100+offset*10,'y':100+par*100,'height':20,'width':0},'selection':{'observed':True,'collapsed':True,'start':None,'end':None,'rectangles':[]}}
    def read(name,value):wire('editorGetStateV2',{},value,name);return copy.deepcopy(value)
    def click(name,c,range_open):
        # NarrowEditorV2Session.placeCaret: its own state read, then the route that read picks.
        index=len(p['requests']);started=clock;before=state();before['selection']['collapsed']=not range_open
        wire('editorGetStateV2',{},before)
        wire('click' if range_open else 'editorPlaceCaretV2',{'xTwips':c['x'],'yTwips':c['y']+10},{})
        p['calls'].append({'name':name,'generation':gen,'documentHandle':gen,'requestStart':index,'requestEnd':index+2,'startedAt':started,'finishedAt':clock+3,'ok':True,'result':{}})
    def selection(name,a,b):wire('editorSelectRangeV2',{'startXTwips':a['x'],'startYTwips':a['y']+10,'endXTwips':b['x'],'endYTwips':b['y']+10},{},name)
    def move(name,action,shift=False,value=None):
        if value is None:value={'action':action,'changed':False,'beforeRevision':0,'revision':0,'completion':'verified-move-readback','state':state()}
        return wire('editorActionV2',{'action':action,'extendSelection':shift},value,name)
    def save(name,text):
        artifact,raw=saved(text);wire('save',{}, {'buffer':binary(raw)},name);p['calls'][-1]['result']={'bytes':binary(raw)};return artifact
    def open_doc():
        nonlocal gen
        gen+=1;wire('open',{'name':'fixture.fodt','buffer':binary(FIXTURE.read_bytes())},{'documentHandle':gen,'width':2000,'height':2000})
        p['workers'].append({'generation':gen,'url':'./profiles/'+PROFILE+'/sdk-worker.js'})
        return {'generation':gen,'documentHandle':gen,'serial':gen,'name':'fixture.fodt','fixtureSha256':plan['fixtureSha256']}
    def locate(prefix,q):
        par=q.get('searchParagraph',q['paragraph']);offset=q['offset'];end=offset if type(offset) is int else len(plan['fixtureParagraphs'][par])
        start=state(par,0);target=state(q['paragraph'],0 if offset=='next-empty' else end)
        wire('search',{'query':q['query']},{'selections':[{'part':'0','rectangles':f'100,{100+par*100},1000,20'}]},prefix+'-search')
        click(prefix+'-search-click',start['caret'],True)
        if q['anchor']=='search-first-displayed-line':move(prefix+'-home','move-line-home')
        read(prefix+'-start-state',start)
        if type(offset) is int:
            for n in range(offset):move(prefix+'-right-'+str(n),'move-character-right')
        else:
            move(prefix+'-end','move-line-end')
            if offset=='next-empty':move(prefix+'-next-empty','move-character-right')
        read(prefix+'-target-state',target);selection(prefix+'-prefix-select',start['caret'],target['caret'])
        text={'text':q.get('prefix',''),'selectionType':'text' if q.get('prefix') else 'none'}
        wire('getSelection',{},text,prefix+'-prefix-text');click(prefix+'-restore-point',target['caret'],bool(text['text']));read(prefix+'-final-state',target)
        return {'plan':q,'boxes':[[100,100+par*100,1000,20]],'start':start,'target':target,'final':target,'selected':text}
    v=p['readiness']={'open':open_doc()};v['setup']=locate('readiness',plan['readinessPoint'])
    v['beforeState']=read('readiness-before-state',state());v['beforeSave']=save('readiness-before-save',plan['fixtureParagraphs'])
    sink={'active':True,'connected':True,'disabled':False,'readOnly':False,'documentHandle':gen,'generation':gen}
    p['inputs'].append({'type':'keydown','key':'Z','isTrusted':True,'at':clock+2.5,'sink':sink})
    p['inputs'].append({'type':'beforeinput','inputType':'insertText','data':'Z','isTrusted':True,'at':clock+3,'sink':sink})
    wire('insertText',{'text':'Z'},{'revision':1});changed=plan['fixtureParagraphs'].copy();changed[0]='Z'+changed[0]
    v['afterSave']=save('readiness-after-save',changed);v['afterState']=read('readiness-after-state',state(revision=1))
    row=plan['cases'][case]
    for which in ('reference','candidate'):
        v=p[which]={'open':open_doc(),'points':{}};v['originalSave']=save(which+'-original-save',plan['fixtureParagraphs'])
        for n,q in row['pointPlans'].items():v['points'][n]=locate(which+'-point-'+n,q)
        origin=v['points'][row['movingPointName']]['final'];click(which+'-origin-click',origin['caret'],False)
        v['setupState']=read(which+'-setup-state',origin);v['setupSelection']={'text':'','selectionType':'none'};wire('getSelection',{},v['setupSelection'],which+'-setup-text')
        v['before']=read(which+'-before-state',origin)
        inputstart=len(p['inputs']);sink={**sink,'generation':gen,'documentHandle':gen};shift=which=='candidate'
        p['inputs'].append({'type':'keydown','key':'ArrowLeft','shiftKey':shift,'isTrusted':True,'at':clock+3,'sink':sink})
        p['keyArms'].append({'name':which+'-move','generation':gen,'at':clock+2.5,'inputStart':inputstart,'inputEnd':inputstart+1})
        target_par,target_offset=(0,0) if case=='shift-Left@doc-start' else (1,10)
        final=state(target_par,target_offset)
        if shift and case!='shift-Left@doc-start':final['selection']={'observed':True,'collapsed':False,'start':copy.deepcopy(final['caret']),'end':copy.deepcopy(origin['caret']),'rectangles':[[200,200,10,20]]}
        reply={'action':row['action'],'changed':False,'beforeRevision':0,'revision':0,'completion':'verified-move-readback','state':final}
        move(which+'-move',row['action'],shift,reply);v['reply']=reply;clock+=500
        v['readback']=read(which+'-readback',final);v['activeSelection']={'text':'E' if shift and case!='shift-Left@doc-start' else '', 'selectionType':'text' if shift and case!='shift-Left@doc-start' else 'none'}
        wire('getSelection',{},v['activeSelection'],which+'-active-selection')
        if which=='reference':
            v['endpoint']=final['caret'];v['mapping']=[]
            for q in plan['mappingPoints']:
                prefix='reference-map-'+str(q['paragraph']);origin=locate(prefix,q)
                v['mapping'].append({'paragraph':q['paragraph'],'origin':origin})
            origin=v['mapping'][target_par]['origin'];prefix='reference-map-'+str(target_par)
            selection(prefix+'-endpoint-select',origin['final']['caret'],final['caret'])
            text={'text':plan['fixtureParagraphs'][target_par][:target_offset],'selectionType':'text' if target_offset else 'none'}
            wire('getSelection',{},text,prefix+'-endpoint-text')
            v['endpointMapping']={'paragraph':target_par,'selected':text}
        wire('close',{}, {},which+'-close')
    return p


class ReaderControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from v23_feature_selection_cases import config
        cls.plan=config()
    def test_full_raw_baseline_and_causes(self):
        from judge_v23_feature_selection import inspect
        p=synthetic_page(self.plan)
        got=inspect(p,self.plan,'chrome');self.assertEqual(got['verdict'],'PASS',got)
        for kind in ('ua','profile','missing-control','self-oracle','native','anchor','range','source','key','readiness','duplicate-terminal'):
            page=copy.deepcopy(p)
            if kind=='ua':page['userAgent']='Firefox/150'
            elif kind=='profile':page['profile']='e2-editor-v23-diag-r2'
            elif kind=='missing-control':page.pop('reference')
            elif kind=='self-oracle':page['reference']['endpoint']=page['candidate']['points']['p1.11']['final']['caret']
            elif kind=='native':page['candidate']['activeSelection']['text']='wrong'
            elif kind=='anchor':page['candidate']['readback']['selection']['end']['x']+=1
            elif kind=='range':page['calls'][0]['requestEnd']=page['calls'][1]['requestEnd']
            elif kind=='source':page['servedSources']={}
            elif kind=='key':page['inputs'][-1]['isTrusted']=False
            elif kind=='readiness':page['readiness']['afterState']['revision']=0
            else:page['responses'].append(page['responses'][-1])
            with self.subTest(kind=kind):self.assertNotEqual(inspect(page,self.plan,'chrome')['verdict'],'PASS')
    def test_population_missing_and_duplicate_actual_page_are_ne(self):
        from judge_v23_feature_selection import judge
        page=synthetic_page(self.plan);cell={'caseId':page['caseId'],'browser':'chrome','page':page}
        self.assertEqual(judge([],self.plan)['verdict'],'NOT_ESTABLISHED')
        result=judge([cell,cell],self.plan);self.assertEqual(result['verdict'],'NOT_ESTABLISHED')
        self.assertIn('duplicate',result['results'][-1]['reason'])


class AdditionalControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from v23_feature_selection_cases import config
        cls.plan=config()
    def test_native_silent_requires_literal_completion(self):
        from judge_v23_feature_selection import inspect
        p=synthetic_page(self.plan,'shift-Left@doc-start')
        got=inspect(p,self.plan,'chrome');self.assertEqual(got['verdict'],'PASS',got)
        self.assertEqual(got['groups']['S3']['verdict'],'PASS')
        p['candidate']['reply']['completion']='guessed-silence'
        call=next(c for c in p['calls'] if c['name']=='candidate-move')
        call['result']['completion']='guessed-silence'
        req=p['requests'][call['requestStart']]
        terminal=next(r for r in p['responses'] if r['generation']==req['generation'] and r['message']['requestId']==req['message']['requestId'])
        terminal['message']['result']['completion']='guessed-silence'
        got=inspect(p,self.plan,'chrome');self.assertNotEqual(got['verdict'],'PASS')
        self.assertIn('native-silent completion',got['reason'])
    def test_geometry_multiple_candidates_is_ne_even_with_selected_label(self):
        from judge_v23_feature_selection import inspect
        p=synthetic_page(self.plan)
        # Move the independent endpoint onto the empty paragraph's actual point;
        # its own raw readback still differs, so a label cannot invent an oracle.
        p['reference']['endpointMapping']['paragraph']=3
        got=inspect(p,self.plan,'chrome');self.assertNotEqual(got['verdict'],'PASS')
        self.assertIn('independently derived',got['reason'])
    def test_actual_js_search_geometry_rejects_bad_and_sorts_raw(self):
        import subprocess
        script=(Path(__file__).resolve().parents[1]/'web/v23-feature-selection.js').read_text()
        fn=script[script.index('function rectangles('):script.index('async function locate(')]
        check=fn+"""
const good={selections:[{part:'0',rectangles:'1418,3350,1846,275;1418,2522,9972,275;1418,2798,9972,551'}]};
if(rectangles(good)[0][1]!==2522)throw Error('unsorted geometry');
for(const raw of ['1,2,3,4;bad','1,2,0,4','1,2,3,4;1,2,4,5','１,2,3,4']){
 let refused=false;try{rectangles({selections:[{part:'0',rectangles:raw}]});}catch(e){refused=true;}
 if(!refused)throw Error('malformed geometry accepted');
}
"""
        run=subprocess.run(['node','--input-type=module','-e',check],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)


    def test_actual_js_paint_digest_keeps_length_and_hash_only(self):
        import subprocess
        script=(Path(__file__).resolve().parents[1]/'web/v23-feature-selection.js').read_text()
        head=script[script.index('const bytes64'):script.index('let generation=0')]
        check="const window={};"+head+"""
const pixels=new Uint8Array([1,2,3,4]);
const message=paintResponse({kind:'response',requestId:9,ok:true,result:{pixels:pixels.buffer,width:1,height:1,revision:0}});
if(message.result.width!==1||message.result.pixels.bytes!==4||message.result.pixels.sha256!==null)throw Error('digest shape');
await Promise.all(window.__featureSelectionPending);
if(message.result.pixels.sha256!=='9f64a747e1b97f131fabb6b447296c9b6f0201e79fb3c5356e6c77e89b6a806a')throw Error('wrong digest');
if(JSON.stringify(message).includes('AQIDBA'))throw Error('bitmap bytes retained');
const plain=paintResponse({kind:'response',requestId:9,ok:false,error:{code:'X'}});if(plain.error.code!=='X')throw Error('refusal changed');
"""
        run=subprocess.run(['node','--input-type=module','-e',check],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
    def test_actual_js_worker_wrapper_routes_only_paint_replies_to_digests(self):
        import subprocess
        script=(Path(__file__).resolve().parents[1]/'web/v23-feature-selection.js').read_text()
        wrapper=script[script.index('const result = window.__featureSelection'):script.index('const openOriginal')]
        check="""const window={},location={search:''},navigator={userAgent:'node'};
class FakeWorker extends EventTarget{constructor(){super();}postMessage(){}terminate(){}}
window.Worker=FakeWorker;"""+wrapper+"""
const a=new window.Worker('w1'),b=new window.Worker('w2');
a.postMessage({kind:'request',requestId:5,operation:'paint',payload:{}});
a.postMessage({kind:'request',requestId:6,operation:'save',payload:{}});
const reply=(w,id)=>{const e=new Event('message');e.data={kind:'response',requestId:id,ok:true,result:{pixels:new Uint8Array([1,2]).buffer}};w.dispatchEvent(e);};
reply(b,5);reply(a,6);reply(a,5);reply(a,5);
await Promise.all(window.__featureSelectionPending);
const enc=result.responses.map(x=>x.message.result.pixels.encoding).join(',');
if(enc!=='base64,base64,sha256,base64')throw Error('routing '+enc);
"""
        run=subprocess.run(['node','--input-type=module','-e',check],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
    def test_paint_digest_is_required(self):
        from judge_v23_feature_selection import inspect
        for pixels,verdict in (({'encoding':'sha256','bytes':4,'sha256':'0'*64},'PASS'),({'encoding':'sha256','bytes':4,'sha256':None},'NOT_ESTABLISHED'),
                               ({'encoding':'base64','bytes':4,'data':'AQIDBA=='},'PASS'),({'encoding':'base64','bytes':4},'NOT_ESTABLISHED'),(None,'NOT_ESTABLISHED'),('no-result','NOT_ESTABLISHED')):
            page=synthetic_page(self.plan);r=copy.deepcopy(page['requests'][-1]);t=copy.deepcopy(page['responses'][-1])
            r['message'].update(requestId=10**6,operation='paint',payload={'documentHandle':r['generation']})
            t['message'].update(requestId=10**6,ok=True,result={'pixels':pixels,'width':1,'height':1} if pixels!='no-result' else None);page['requests'].append(r);page['responses'].append(t)
            with self.subTest(pixels=pixels):
                value=inspect(page,self.plan,'chrome');self.assertEqual(value['verdict'],verdict,value)
                if verdict!='PASS':self.assertEqual(value['reason'],'paint digest incomplete')


class ProductContradictionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from v23_feature_selection_cases import config
        cls.plan=config()
    def patch_call(self,page,name,mutate):
        c=next(c for c in page['calls'] if c['name']==name)
        r=page['requests'][c['requestStart']]
        t=next(t for t in page['responses'] if t['generation']==r['generation'] and t['message']['requestId']==r['message']['requestId'])
        mutate(c['result']);mutate(t['message']['result'])
    def test_consistent_wrong_product_semantics_fail_not_ne(self):
        from judge_v23_feature_selection import inspect,judge
        for kind in ('endpoint','native','changed','stale'):
            p=synthetic_page(self.plan)
            if kind=='native':
                p['candidate']['activeSelection']['text']='WRONG'
                self.patch_call(p,'candidate-active-selection',lambda r:r.update(text='WRONG'))
            elif kind=='changed':
                p['candidate']['reply']['changed']=True
                self.patch_call(p,'candidate-move',lambda r:r.update(changed=True))
            elif kind=='endpoint':
                p['candidate']['reply']['state']['caret']['x']=190
                p['candidate']['readback']['caret']['x']=190
                self.patch_call(p,'candidate-move',lambda r:r['state']['caret'].update(x=190))
                self.patch_call(p,'candidate-readback',lambda r:r['caret'].update(x=190))
            else:
                p['candidate']['reply']['state']['caret']['x']=190
                self.patch_call(p,'candidate-move',lambda r:r['state']['caret'].update(x=190))
            with self.subTest(kind=kind):
                result=inspect(p,self.plan,'chrome');self.assertEqual(result['verdict'],'FAIL',result)
                aggregate=judge([{'browser':'chrome','caseId':p['caseId'],'page':p}],self.plan)
                self.assertEqual(aggregate['verdict'],'FAIL')
        p=synthetic_page(self.plan);p['reference'].pop('endpointMapping')
        self.assertEqual(inspect(p,self.plan,'chrome')['verdict'],'NOT_ESTABLISHED')
    def test_page_only_single_line_boxes_are_rejected(self):
        from judge_v23_feature_selection import inspect
        p=synthetic_page(self.plan);p['candidate']['points']['p1.11']['boxes']=[[100,200,1,1]]
        value=inspect(p,self.plan,'chrome')
        self.assertEqual(value['verdict'],'NOT_ESTABLISHED');self.assertIn('unbound page search boxes',value['reason'])


class PlaceRouteControls(unittest.TestCase):
    """selection-prep-01: ABI6 placeCaret posts editorPlaceCaretV2 on a collapsed caret, click on a range."""
    @classmethod
    def setUpClass(cls):
        from v23_feature_selection_cases import config
        cls.plan=config()
    def test_route_is_read_from_the_products_own_state_read(self):
        from judge_v23_feature_selection import inspect
        p=synthetic_page(self.plan)
        self.assertLessEqual({'click','editorPlaceCaretV2'},{r['message']['operation'] for r in p['requests']})
        self.assertEqual(inspect(p,self.plan,'chrome')['verdict'],'PASS')
        def window(page,name):
            c=next(c for c in page['calls'] if c['name']==name);return c,page['requests'][c['requestStart']:c['requestEnd']]
        def reply(page,request):
            return next(t for t in page['responses'] if t['generation']==request['generation'] and t['message']['requestId']==request['message']['requestId'])
        for kind in ('collapsed-but-click','range-but-placecaret','stale-state-read','fallback-both','no-state-read','read-after-route','other-generation-read','selection-none'):
            page=copy.deepcopy(p)
            if kind=='collapsed-but-click':window(page,'candidate-origin-click')[1][1]['message']['operation']='click'
            elif kind=='range-but-placecaret':window(page,'readiness-search-click')[1][1]['message']['operation']='editorPlaceCaretV2'
            elif kind=='stale-state-read':reply(page,window(page,'candidate-origin-click')[1][0])['message']['result']['selection']['collapsed']=False
            elif kind=='no-state-read':window(page,'candidate-origin-click')[1][0]['message']['operation']='paint'
            elif kind=='read-after-route':
                read,route=window(page,'candidate-origin-click')[1];read['at'],route['at']=route['at'],read['at']
            elif kind=='other-generation-read':
                read=window(page,'candidate-origin-click')[1][0];reply(page,read)['generation']+=100;read['generation']+=100
            elif kind=='selection-none':reply(page,window(page,'candidate-origin-click')[1][0])['message']['result']['selection']=None
            else:
                c,requests=window(page,'candidate-origin-click');at=c['requestEnd'];extra=copy.deepcopy(requests[-1])
                answer=copy.deepcopy(reply(page,extra));extra['message']['requestId']=answer['message']['requestId']=10**6
                extra['message']['operation']='click';page['requests'].insert(at,extra);page['responses'].append(answer)
                for other in page['calls']:
                    if other['requestStart']>=at:other['requestStart']+=1;other['requestEnd']+=1
                c['requestEnd']+=1
            with self.subTest(kind=kind):
                value=inspect(page,self.plan,'chrome')
                self.assertEqual(value['verdict'],'NOT_ESTABLISHED',value);self.assertIn('placeCaret',value['reason'])


    def test_passive_page_rectangles_pass_and_unknown_operations_do_not(self):
        from judge_v23_feature_selection import inspect
        for op,verdict in (('pageRectangles','PASS'),('pasteMarkdown','NOT_ESTABLISHED')):
            page=synthetic_page(self.plan);r=copy.deepcopy(page['requests'][-1])
            r['message'].update(requestId=10**6,operation=op,payload={'documentHandle':r['generation']});page['requests'].append(r)
            with self.subTest(op=op):
                value=inspect(page,self.plan,'chrome');self.assertEqual(value['verdict'],verdict,value)
                if verdict!='PASS':self.assertEqual(value['reason'],'unplanned wire operation')


class PreRedProvenanceControls(unittest.TestCase):
    """The sealed v19 counted-05 report survives a runner-side helper change, not a reader or input change."""
    REPORT=PROJECT.parent/'findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json'
    @classmethod
    def setUpClass(cls):
        import v23_feature_pre_red_cases as historical
        report=json.loads(cls.REPORT.read_bytes())
        if not all((cls.REPORT.parent/r['path']).is_file() for r in report['runs']):
            raise unittest.SkipTest('counted-05 raw cells not restored (store_payloads.py restore)')
        cls.historical=historical;cls.live=historical.config(historical.WASM)
    def check(self,mutate):
        from unittest.mock import patch
        from judge_v23_feature_selection import check_pre_red
        plan=copy.deepcopy(self.live);mutate(plan)
        with patch.object(self.historical,'config',return_value=plan):return check_pre_red(self.REPORT)
    def test_runner_helper_change_keeps_the_sealed_result(self):
        def helper(plan):plan['instrumentSources']['tools/run_browser_probe.py']='0'*64
        self.assertEqual(self.check(helper)['verdict'],'EXPECTED_RED')
        # The strict live comparison this replaces would have refused the same change.
        plan=copy.deepcopy(self.live);helper(plan)
        self.assertNotEqual(json.loads(self.REPORT.read_bytes())['config'],plan)
    def test_reader_or_frozen_input_change_is_refused(self):
        from judge_v23_feature_pre_red import NotEstablished
        def reader(plan):plan['instrumentSources']['tools/judge_v23_feature_pre_red.py']='0'*64
        def inputs(plan):plan['fixtureSha256']='0'*64
        for mutate,reason in ((reader,'historical reader changed'),(inputs,'historical frozen inputs differ')):
            with self.subTest(reason=reason),self.assertRaisesRegex(NotEstablished,reason):self.check(mutate)

class PreservedGraphControls(unittest.TestCase):
    def layout(self,directory,blobs=None,extra=None):
        import hashlib
        base=Path(directory);(base/'cohort').mkdir();(base/'tool-source-blobs').mkdir()
        executed={}
        rows={}
        for name,data in (blobs or {'tools/a.py':b'a\n','tools/b.py':b'b\n'}).items():
            sha=hashlib.sha256(data).hexdigest();executed[name]=sha
            (base/'tool-source-blobs'/(sha+'.py')).write_bytes(data)
            rows[name]={'sha256':sha,'storedPath':'tool-source-blobs/'+sha+'.py'}
        (base/'tool-source-bindings-01.json').write_text(json.dumps({'reports':{'cohort':rows}}))
        if extra:(base/'tool-source-bindings-02.json').write_text(json.dumps({'reports':{'cohort':rows}}))
        return base/'cohort'/'report.json',executed,rows
    def test_blobs_bind_exactly(self):
        import tempfile
        from judge_v23_feature_selection import preserved_graph
        from judge_v23_feature_pre_red import NotEstablished
        for kind in ('exact','corrupt','membership','duplicate','escape'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                path,executed,rows=self.layout(directory,extra=kind=='duplicate')
                if kind=='corrupt':(path.parent.parent/rows['tools/a.py']['storedPath']).write_bytes(b'changed\n')
                elif kind=='membership':executed['tools/c.py']='0'*64
                elif kind=='escape':
                    rows['tools/a.py']['storedPath']='../outside.py'
                    (path.parent.parent/'tool-source-bindings-01.json').write_text(json.dumps({'reports':{'cohort':rows}}))
                if kind=='exact':self.assertEqual(set(preserved_graph(path,executed)),set(executed))
                else:
                    with self.assertRaises(NotEstablished):preserved_graph(path,executed)


class PreservedPages:
    """Mixin: preserved uncounted pages with their own executed config, and consistent edits."""
    BASE=PROJECT.parent/'findings/evidence/link-batch-v23/feature-protocol'
    def page(self,prep,case):
        import gzip
        plan=json.loads((self.BASE/prep/'report.json').read_bytes())['config']
        return json.loads(gzip.decompress((self.BASE/prep/f'chrome-{case}.json.gz').read_bytes()))['page'],plan
    def consistent(self,page,name,mutate):
        # Mutate the page record, the public call result and the wire reply together.
        call=next(c for c in page['calls'] if c['name']==name)
        request=next(r for r in page['requests'][call['requestStart']:call['requestEnd']] if r['message']['operation'] in ('getSelection','editorGetStateV2'))
        reply=next(x for x in page['responses'] if x['generation']==request['generation'] and x['message']['requestId']==request['message']['requestId'])
        for value in (call['result'],reply['message']['result']):mutate(value)

class ActualPreparationRereads(PreservedPages,unittest.TestCase):
    """Preserved uncounted pages re-read by the current reader with their own executed config."""
    def test_collapsed_click_end_shape_anchors_at_the_caret(self):
        from judge_v23_feature_selection import inspect
        page,plan=self.page('selection-prep-05','shift-End@wrap-line-end')
        value=inspect(page,plan,'chrome');self.assertEqual(value['verdict'],'PASS',value)
        self.assertEqual(value['groups']['S1']['logicalAnchor'],[4,101])
        # A product that kept the setup click (line start) as the Shift anchor must not read PASS.
        moved=copy.deepcopy(page);start=moved['candidate']['points']['w.l1start']['final']['caret']
        call=next(c for c in moved['calls'] if c['name']=='candidate-readback')
        request=next(r for r in moved['requests'][call['requestStart']:call['requestEnd']] if r['message']['operation']=='editorGetStateV2')
        reply=next(x for x in moved['responses'] if x['generation']==request['generation'] and x['message']['requestId']==request['message']['requestId'])
        for state in (moved['candidate']['readback'],call['result'],reply['message']['result']):
            state['selection'].update(collapsed=False,start={**start,'height':275},end={**state['caret'],'height':275})
        bad=inspect(moved,plan,'chrome');self.assertEqual(bad['groups']['S1']['verdict'],'FAIL',bad)
    def test_full_bitmap_preparation_still_reads(self):
        from judge_v23_feature_selection import inspect
        page,plan=self.page('selection-prep-02','shift-Right@caret-mid')
        self.assertEqual(inspect(page,plan,'chrome')['verdict'],'PASS')


class TableSelectionControls(PreservedPages,unittest.TestCase):
    """Fable ruling 2026-10-27 (A'), red cases (a)-(e)."""
    def test_a_one_character_off_native_text_fails(self):
        from judge_v23_feature_selection import inspect
        page,plan=self.page('selection-prep-04','shift-Down@cell-end')
        self.assertTrue(inspect(page,plan,'chrome')['groups']['S1'].get('tableSelection'))
        edit=lambda v:v.update(text=v['text'].replace('A2','A3',1))
        edit(page['candidate']['activeSelection']);self.consistent(page,'candidate-active-selection',edit)
        value=inspect(page,plan,'chrome');self.assertEqual(value['groups']['S1'],{'verdict':'FAIL','reason':'table-selection native text differs'})
    def test_b_the_old_premise_extension_fails(self):
        from judge_v23_feature_selection import inspect
        page,plan=self.page('selection-prep-03','shift-Up@cell-end')
        # What the withdrawn premise expected: extend from the cell end to the plain Up endpoint.
        end=page['reference']['endpoint'];anchor=page['candidate']['before']['caret']
        def old(state):
            state.update(caret=copy.deepcopy(end));state['selection'].update(collapsed=False,start={**end,'height':275},end={**anchor,'height':275})
        old(page['candidate']['readback']);self.consistent(page,'candidate-readback',old)
        text=lambda v:v.update(text='item one\nA1 cell text')
        text(page['candidate']['activeSelection']);self.consistent(page,'candidate-active-selection',text)
        self.assertEqual(inspect(page,plan,'chrome')['groups']['S1']['verdict'],'FAIL')
    def test_b_named_limit_caret_side_is_not_witnessed(self):
        from judge_v23_feature_selection import inspect
        page,plan=self.page('selection-prep-03','shift-Up@cell-end')
        end=page['reference']['endpoint'];anchor=page['candidate']['before']['caret']
        def old(state):
            state.update(caret=copy.deepcopy(end));state['selection'].update(collapsed=False,start={**end,'height':275},end={**anchor,'height':275})
        old(page['candidate']['readback']);self.consistent(page,'candidate-readback',old)
        value=inspect(page,plan,'chrome')['groups']['S1']
        self.assertEqual((value['verdict'],value['anchorWitness']),('PASS','native-text-extent'))
    def test_aggregate_records_native_text_agreement_without_asserting_it(self):
        import gzip
        from judge_v23_feature_selection import judge
        plan=json.loads((self.BASE/'selection-prep-03'/'report.json').read_bytes())['config']
        cell=json.loads(gzip.decompress((self.BASE/'selection-prep-03'/'chrome-shift-Down@caret-mid.json.gz').read_bytes()))
        row=next(r for r in judge([cell],plan)['results'] if tuple(r['cell'])==('chrome','shift-Down@caret-mid'))
        self.assertEqual(row['verdict'],'PASS');self.assertIn('nativeTextAgreement',row)
        cell['page']['candidate']['activeSelection']['text']+='x'
        row=next(r for r in judge([cell],plan)['results'] if tuple(r['cell'])==('chrome','shift-Down@caret-mid'))
        self.assertEqual(row['nativeTextAgreement']['agrees'],False)
    def test_c_container_parser_refuses_what_it_does_not_model(self):
        import re
        from judge_v23_feature_selection import containers_from_xml
        from judge_v23_feature_pre_red import NotEstablished
        from v23_feature_selection_cases import FIXTURE,config
        raw=FIXTURE.read_text();expected=config()['fixtureParagraphs']
        self.assertEqual(containers_from_xml(raw.encode(),expected)[8],[0,0,0])
        no_table=re.sub(r'<table:table .*?</table:table>','',raw,flags=re.S)
        spanned=raw.replace('<table:table-cell office:value-type="string"><text:p>A1','<table:table-cell table:number-columns-spanned="2" office:value-type="string"><text:p>A1',1)
        for name,text,wanted in (('no table',no_table,[t for t in expected if 'cell text' not in t]),('order',raw,expected[::-1]),('spanned',spanned,expected)):
            with self.subTest(name=name),self.assertRaises(NotEstablished):containers_from_xml(text.encode(),wanted)
    def test_d_non_table_members_read_as_before(self):
        import gzip
        from judge_v23_feature_selection import inspect
        for prep,case in (('selection-prep-03','shift-Down@caret-mid'),('selection-prep-04','shift-Home@cell-end'),('selection-prep-05','shift-Right@range-bwd')):
            cell=json.loads(gzip.decompress((self.BASE/prep/f'chrome-{case}.json.gz').read_bytes()))
            plan=json.loads((self.BASE/prep/'report.json').read_bytes())['config']
            # As stored: the runner wrote the reader's output through JSON.
            with self.subTest(case=case):self.assertEqual(json.loads(json.dumps(inspect(cell['page'],plan,'chrome'))),cell['inspection'])
    def test_e_a_crossing_control_endpoint_flips_the_branch(self):
        from unittest.mock import patch
        import judge_v23_feature_selection as judge
        page,plan=self.page('selection-prep-05','shift-Home@list-mid')
        self.assertNotIn('tableSelection',judge.inspect(page,plan,'chrome')['groups']['S1'])
        real=judge.logical_endpoint
        with patch.object(judge,'logical_endpoint',lambda e:(8,real(e)[1])):
            value=judge.inspect(page,plan,'chrome')['groups']['S1']
        self.assertEqual(value.get('containers'),['body',[0,0,0]])
        self.assertIn(value['verdict'],('PASS','FAIL'))


class InteractionControls(PreservedPages,unittest.TestCase):
    """S4 red cases built from the real preparation-06 pages (one per interaction method)."""
    def read(self,case,mutate=None):
        from judge_v23_feature_selection import inspect
        page,plan=self.page('selection-prep-06',case)
        if mutate:mutate(page)
        return inspect(page,plan,'chrome')
    def test_real_pages_pass(self):
        for case in ('inter-Shift+Right-a','inter-Shift+Down-b','inter-Shift+End-c'):
            with self.subTest(case=case):self.assertEqual(self.read(case)['verdict'],'PASS')
    def test_wrong_interaction_outcomes_fail(self):
        def text(name,field,value):
            def mutate(page):
                edit=lambda v:v.update(text=value)
                edit(page['interaction'][field]);self.consistent(page,name,edit)
            return mutate
        def kept_range(page):
            edit=lambda v:v['selection'].update(collapsed=False)
            edit(page['interaction']['stepState']);self.consistent(page,'interaction-step-state',edit)
        for case,mutate,reason in (
                ('inter-Shift+Right-a',text('interaction-active-selection','activeSelection','P3 plain paragr'),'interaction native text differs after settling'),
                ('inter-Shift+Right-a',kept_range,'click did not reset the selection'),
                ('inter-Shift+Down-b',text('interaction-step-text','stepSelection','ALPH'),'interaction native text differs'),
                ('inter-Shift+End-c',text('interaction-active-selection','activeSelection','DELT'),'interaction native text differs after settling')):
            with self.subTest(case=case,reason=reason):
                value=self.read(case,mutate);self.assertEqual(value['groups']['S4'],{'verdict':'FAIL','reason':reason})
    def test_missing_or_foreign_witnesses_are_ne(self):
        def untrusted(page):
            for x in page['inputs'][page['interaction']['inputStart']:page['interaction']['inputEnd']]:x['isTrusted']=False
        def click_payload(page):
            c=next(c for c in page['calls'] if c['name']=='interaction-step-click')
            r=next(r for r in page['requests'][c['requestStart']:c['requestEnd']] if r['message']['operation'] in ('click','editorPlaceCaretV2'))
            r['message']['payload']['xTwips']+=1
        def range_payload(page):
            c=next(c for c in page['calls'] if c['name']=='interaction-select-range')
            page['requests'][c['requestStart']]['message']['payload']['endXTwips']+=1
        def no_extension(page):
            edit=lambda v:v['selection'].update(collapsed=True)
            edit(page['interaction']['firstState']);self.consistent(page,'interaction-first-state',edit)
        def early(page):
            c=next(c for c in page['calls'] if c['name']=='interaction-readback')
            for r in page['requests'][c['requestStart']:c['requestEnd']]:r['at']-=400
            c['startedAt']-=400
        def unowned(page):
            r=copy.deepcopy(next(r for r in page['requests'] if r['message']['operation']=='editorActionV2'))
            t=copy.deepcopy(next(x for x in page['responses'] if x['generation']==r['generation'] and x['message']['requestId']==r['message']['requestId']))
            r['message']['requestId']=t['message']['requestId']=10**6;page['requests'].append(r);page['responses'].append(t)
        for case,mutate,reason in (('inter-Shift+Right-a',untrusted,'actual trusted click absent'),
                                   ('inter-Shift+Right-a',click_payload,'click request differs from the actual pointer'),
                                   ('inter-Shift+Down-b',untrusted,'actual trusted drag absent'),
                                   ('inter-Shift+End-c',range_payload,'text-handle coordinates differ'),
                                   ('inter-Shift+End-c',no_extension,'Shift extension before the interaction absent'),
                                   ('inter-Shift+Down-b',early,'readback too early'),('inter-Shift+End-c',unowned,'unowned wire mutation')):
            with self.subTest(case=case,mutate=mutate.__name__):
                value=self.read(case,mutate);self.assertEqual((value['verdict'],value['reason']),('NOT_ESTABLISHED',reason))


class S5ComparatorControls(PreservedPages,unittest.TestCase):
    """Fable ruling 2 (2026-10-27) red cases, on real files: a WASM unedited save and native run-01 saves."""
    NATIVE=PROJECT.parent/'findings/evidence/link-batch-v23/feature-protocol/s5-native/run-01/saves'
    def setUp(self):
        import base64,gzip
        cell=json.loads(gzip.decompress((self.BASE/'selection-prep-05'/'chrome-shift-Home@doc-start.json.gz').read_bytes()))
        self.original=base64.b64decode(cell['page']['readiness']['beforeSave']['base64'])
        self.before=(self.NATIVE/'shift-Left@caret-mid_backspace-before.odt').read_bytes()
        self.after=(self.NATIVE/'shift-Left@caret-mid_backspace-after.odt').read_bytes()
        self.row={'family':'backspace','native':{side:{'path':str((self.NATIVE/f'shift-Left@caret-mid_backspace-{side}.odt').relative_to(PROJECT.parent)),
                  'sha256':__import__('hashlib').sha256(raw).hexdigest()} for side,raw in (('before',self.before),('after',self.after))}}
    def edit(self,raw,section,old=None,new=None):
        """Rebuild the ODT with one byte changed inside the named content.xml section."""
        import io,re,zipfile
        source=zipfile.ZipFile(io.BytesIO(raw));content=source.read('content.xml')
        if section=='duplicate-ffd':
            block=re.search(rb'<office:font-face-decls>.*?</office:font-face-decls>',content,re.S).group(0);content=content.replace(block,block+block,1)
        else:
            m=re.search(rb'<office:%s>(.*?)</office:%s>'%(section.encode(),section.encode()),content,re.S)
            assert m and old in m.group(1),(section,old);i=m.start(1)+m.group(1).find(old);content=content[:i]+new+content[i+len(old):]
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as target:
            for item in source.infolist():target.writestr(item,content if item.filename=='content.xml' else source.read(item.filename))
        return out.getvalue()
    def test_real_control_and_reference(self):
        from judge_v23_feature_selection import native_reference,s5_compare
        self.assertEqual(native_reference(self.row,self.original),self.after)
        self.assertFalse(s5_compare('backspace',self.original,self.before,False),'full reduce_content must still see the font table')
    def test_ruling_red_cases(self):
        from judge_v23_feature_selection import native_reference,s5_compare,strip_ffd
        from judge_v23_feature_pre_red import NotEstablished
        self.assertFalse(s5_compare('backspace',self.edit(self.after,'body',b'ALPHA',b'ALPHB'),self.after,True))
        self.assertFalse(s5_compare('backspace',self.edit(self.after,'automatic-styles',b'P1',b'P9'),self.after,True))
        self.assertTrue(s5_compare('backspace',self.edit(self.after,'font-face-decls',b'Liberation Serif',b'Liberation Serig'),self.after,True))
        with self.assertRaisesRegex(NotEstablished,'native reference not comparable'):
            native_reference(self.row,self.edit(self.original,'body',b'ALPHA',b'ALPHB'))
        with self.assertRaisesRegex(NotEstablished,'not uniquely present'):
            s5_compare('backspace',self.edit(self.after,'duplicate-ffd'),self.after,True)
        with self.assertRaisesRegex(NotEstablished,'not uniquely present'):strip_ffd(b'<office:body></office:body>')
    def test_collapsing_reduction_is_not_a_native_no_effect(self):
        from judge_v23_feature_selection import native_reference
        from judge_v23_feature_pre_red import NotEstablished
        import hashlib,tempfile,shutil
        # A native after that differs from before only inside font-face-decls collapses under the reduction.
        collapsed=self.edit(self.before,'font-face-decls',b'Liberation Serif',b'Liberation Serig')
        with tempfile.TemporaryDirectory(dir=PROJECT.parent/'findings') as directory:
            path=Path(directory)/'after.odt';path.write_bytes(collapsed)
            row={**self.row,'native':{**self.row['native'],'after':{'path':str(path.relative_to(PROJECT.parent)),'sha256':hashlib.sha256(collapsed).hexdigest()}}}
            with self.assertRaisesRegex(NotEstablished,'reduction collapses the native edit'):native_reference(row,self.original)


class OpenBoundaryControls(unittest.TestCase):
    def test_actual_runner_alias_and_mirror_respect_sdk_suffix_without_repacking(self):
        import re
        import tempfile
        from unittest.mock import patch
        import run_v23_feature_selection as runner
        from v23_feature_selection_cases import config,mirror,verify_mirror,FIXTURE,PROJECT
        source=(PROJECT/'src/sdk_api.cpp').read_text()
        body=source[source.index('int32_t oxsdk_document_open('):source.index('int32_t oxsdk_document_paint(')]
        ordinary=body.split('#else',1)[1].split('#endif',1)[0]
        guard=re.search(r'name.size\(\) < ([0-9]+) \|\| name.substr\(name.size\(\) - ([0-9]+)\) != "([^"]+)"',ordinary)
        self.assertIsNotNone(guard,'actual non-ODS open suffix guard changed')
        width,substr,suffix=guard.groups();self.assertEqual((width,substr,suffix),('4','4','.odt'))
        self.assertIn('return probe::SubmitStatus::InvalidArgument;',ordinary)
        plan=config()
        with tempfile.TemporaryDirectory(prefix='selection-open-boundary-') as directory:
            target=Path(directory)/'mirror';mirror(target,plan);verify_mirror(target,plan)
            class Session:
                def set_file(self,selector,path):self.selector,self.path=selector,path
            session=Session()
            with patch.object(runner,'evaluate',return_value=1),patch.object(runner,'wait_page') as wait:
                runner.fresh(session,target)
            self.assertEqual(session.selector,'#file')
            self.assertEqual(session.path.name,'feature-selection.odt')
            self.assertTrue(session.path.name.endswith(suffix))
            self.assertFalse('feature-selection.fodt'.endswith(suffix),'old alias must fail actual suffix boundary')
            self.assertEqual(session.path.read_bytes(),FIXTURE.read_bytes())
            self.assertFalse((target/'feature-selection.fodt').exists())
            self.assertIn("name==='feature-selection.odt'",wait.call_args.args[1])

if __name__=='__main__':unittest.main()
