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
        for kind in ('collapsed-but-click','range-but-placecaret','stale-state-read','fallback-both','no-state-read'):
            page=copy.deepcopy(p)
            if kind=='collapsed-but-click':window(page,'candidate-origin-click')[1][1]['message']['operation']='click'
            elif kind=='range-but-placecaret':window(page,'readiness-search-click')[1][1]['message']['operation']='editorPlaceCaretV2'
            elif kind=='stale-state-read':reply(page,window(page,'candidate-origin-click')[1][0])['message']['result']['selection']['collapsed']=False
            elif kind=='no-state-read':window(page,'candidate-origin-click')[1][0]['message']['operation']='paint'
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
