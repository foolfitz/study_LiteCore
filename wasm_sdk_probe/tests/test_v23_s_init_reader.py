"""Synthetic causal controls over actual saved ODT and decoded RGBA evidence."""
import base64
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import unittest
import xml.etree.ElementTree as ET
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import judge_v23_s_init as reader
from v23_s_init_cases import CASES, PROFILES, BROWSERS, ROUNDS, REGION, FIXTURES, fixture_identity, config_bytes, verify_mirror, profile_identity


def binary(data): return {'encoding': 'base64', 'bytes': len(data), 'data': base64.b64encode(data).decode()}
def saved(data): return {'sha256': reader.digest(data), 'base64': base64.b64encode(data).decode()}
def modified(data, text, paragraph=False):
    out=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(out,'w') as dest:
        for name in source.namelist():
            content=source.read(name)
            if name=='content.xml':
                root=ET.fromstring(content); p=next(root.iter(reader.q('text','p')))
                p.text=text
                if paragraph:
                    parent=next(el for el in root.iter() if p in list(el)); parent.append(ET.Element(p.tag,p.attrib))
                content=ET.tostring(root)
            dest.writestr(name,content)
    return out.getvalue()


def population():
    config={'fixtures':fixture_identity(),'instrumentSha256':{'instrument':'synthetic'},'servedSources':{'e2-editor.html':'synthetic-source'},
            'profiles':{p:{'profile':p,'coreCommit':'test-core','artifacts':{'probe.wasm':p,'resource':'same'}} for p in PROFILES}}
    cells=[]
    pixels=bytes(600*800*4)
    for case_id,plan in CASES.items():
        for profile in PROFILES:
            page={'profile':profile,'caseId':case_id,'complete':True,'plan':plan,'artifacts':config['profiles'][profile]['artifacts'],
                  'manifest':{'profile':profile,'coreCommit':'test-core'},'servedSources':config['servedSources'],
                  'configSha256':reader.digest(config_bytes(config)),
                  'requests':[],'responses':[],'events':[{'actual':'synthetic-red-control-only'}],
                  'steps':[{'ok':True}],'workers':[],'observations':[]}
            def request(gen,op,payload,result):
                ident=len(page['requests'])+1
                page['requests'].append({'generation':gen,'message':{'requestId':ident,'operation':op,'payload':payload}})
                page['responses'].append({'generation':gen,'message':{'requestId':ident,'ok':True,'result':result}})
            gen=0
            for fixture in plan['fixtures']:
                gen+=1; original=(FIXTURES/fixture).read_bytes()
                page['workers'].append({'generation':gen,'createdAt':gen*10,'terminatedAt':gen*10+5,'url':f'http://local/profiles/{profile}/sdk-worker.js'})
                request(gen,'init',{}, {'profile':profile,'coreCommit':'test-core'})
                request(gen,'open',{'name':fixture,'buffer':binary(original)},{'revision':0})
                data=original; setup=None
                if case_id=='paragraph-break':
                    initial={'revision':0,'caret':{'x':10,'y':20,'height':10},'selectionType':'none','selection':{'observed':False,'collapsed':True}}
                    placed=copy.deepcopy(initial);placed['selection']['observed']=True
                    point={'xTwips':10,'yTwips':25}; placement={'revision':0,'state':placed}
                    request(gen,'editorGetStateV2',{},initial)
                    request(gen,'editorPlaceCaretV2',point,placement)
                    request(gen,'editorGetStateV2',{},placed)
                    setup={'initialState':initial,'point':point,'placement':placement,'afterPlacementState':placed}
                if 'input' in plan:
                    request(gen,'insertText',{'text':plan['input']},{'method':'paste','revision':1})
                    text=plan['input']+('Language tagged authority paragraph.' if case_id=='direct-load-reopen' else '')
                    data=modified(data,text,case_id=='paragraph-break')
                if case_id=='paragraph-break':
                    post=copy.deepcopy(placed);post['revision']=1;setup['postMarkerState']=post
                    request(gen,'editorGetStateV2',{},post)
                    request(gen,'editorActionV2',{'action':'insert-paragraph-break'},{})
                obs={'fixtureName':fixture,'fixtureSha256':reader.digest(original),'openGeneration':gen,'saved':saved(data)}
                if setup is not None: obs['paragraphSetup']=setup
                if case_id=='linguistic-layout':
                    geo={'parts':1,'rectangles':[{'x':0,'y':0,'width':8640,'height':11520}],'widthTwips':8640,'heightTwips':11520}
                    request(gen,'pageRectangles',{},dict(parts=1,rectangles='0,0,8640,11520',documentWidthTwips=8640,documentHeightTwips=11520))
                    request(gen,'paint',REGION,{'pixels':binary(pixels)})
                    obs.update(geometry=geo,render={'region':REGION,'width':600,'height':800,'rgbaSha256':reader.digest(pixels),'rgbaBase64':binary(pixels)['data']})
                request(gen,'save',{}, {'buffer':binary(data)})
                if case_id=='direct-load-reopen':
                    gen+=1; page['workers'].append({'generation':gen,'createdAt':gen*10,'terminatedAt':gen*10+5,'url':f'http://local/profiles/{profile}/sdk-worker.js'})
                    request(gen,'init',{}, {'profile':profile,'coreCommit':'test-core'})
                    request(gen,'open',{'name':'exact-saved-reopen.odt','buffer':binary(data)},{})
                    request(gen,'save',{}, {'buffer':binary(data)})
                    obs.update(reopenGeneration=gen,reopenInputSha256=reader.digest(data),reopened=saved(data))
                page['observations'].append(obs)
            for browser in BROWSERS:
                for n in ROUNDS:
                    actual_page=copy.deepcopy(page)
                    actual_page['userAgent']='Mozilla/5.0 Firefox/140.0' if browser=='firefox' else 'Mozilla/5.0 HeadlessChrome/140.0'
                    actual_page['steps'][0]['startedAt']=n
                    cells.append({'caseId':case_id,'profile':profile,'browser':browser,'round':n,'page':actual_page})
    return cells,config


class SInitReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.cells,cls.config=population()
    def test_clean_synthetic_population(self):
        result=reader.judge(self.cells,self.config)
        self.assertEqual(result['verdict'],'PASS',result)
        self.assertIn('NOT_ESTABLISHED',result['residuals']['serviceDictionaryAvailability'])
    def test_causal_rejections(self):
        for mutation in ('missing-cell','duplicate-cell','wrong-candidate','wrong-fixture',
                         'changed-saved-outcome','changed-method','changed-geometry','changed-pixels',
                         'missing-reopen','substituted-reopen-bytes','failed-response','wrong-worker',
                         'wrong-served-source','wrong-served-config','extra-noop-mutation','both-silent-drop','no-revision-advance','missing-placement'):
            with self.subTest(mutation=mutation):
                cells=copy.deepcopy(self.cells)
                case='paragraph-break' if mutation=='missing-placement' else 'linguistic-layout' if mutation in ('changed-geometry','changed-pixels') else 'direct-load-reopen' if mutation in ('missing-reopen','substituted-reopen-bytes') else 'input-teh'
                cell=next(c for c in cells if c['caseId']==case and c['profile']==PROFILES[1])
                page=cell['page']; obs=page['observations'][0]
                if mutation=='missing-cell': cells.pop()
                elif mutation=='duplicate-cell': cells.append(copy.deepcopy(cells[0]))
                elif mutation=='wrong-candidate': page['artifacts']=dict(page['artifacts'],**{'probe.wasm':'wrong'})
                elif mutation=='wrong-fixture': obs['fixtureSha256']='wrong'
                elif mutation=='changed-method':
                    request=next(r for r in page['requests'] if r['message']['operation']=='insertText')
                    next(r for r in page['responses'] if r['message']['requestId']==request['message']['requestId'])['message']['result']['method']='postKeyEvent'
                elif mutation=='changed-saved-outcome':
                    data=modified((FIXTURES/'empty-en-US.odt').read_bytes(),'WRONG')
                    obs['saved']=saved(data)
                    req=next(r for r in page['requests'] if r['message']['operation']=='save')
                    next(r for r in page['responses'] if r['message']['requestId']==req['message']['requestId'])['message']['result']['buffer']=binary(data)
                elif mutation=='changed-geometry':
                    obs['geometry']['widthTwips']+=1
                    req=next(r for r in page['requests'] if r['message']['operation']=='pageRectangles')
                    next(r for r in page['responses'] if r['message']['requestId']==req['message']['requestId'])['message']['result']['documentWidthTwips']+=1
                elif mutation=='changed-pixels':
                    pixels=bytearray(reader.decode(obs['render']['rgbaBase64']));pixels[0]=1;pixels=bytes(pixels)
                    obs['render'].update(rgbaBase64=binary(pixels)['data'],rgbaSha256=reader.digest(pixels))
                    req=next(r for r in page['requests'] if r['message']['operation']=='paint')
                    next(r for r in page['responses'] if r['message']['requestId']==req['message']['requestId'])['message']['result']['pixels']=binary(pixels)
                elif mutation=='missing-reopen': obs.pop('reopenGeneration')
                elif mutation=='substituted-reopen-bytes':
                    next(r for r in page['requests'] if r['generation']==2 and r['message']['operation']=='open')['message']['payload']['buffer']=binary((FIXTURES/'language.odt').read_bytes())
                elif mutation=='failed-response': page['responses'][0]['message']['ok']=False
                elif mutation=='wrong-worker': page['workers'][0]['url']='http://local/profiles/e2-editor-v22/sdk-worker.js'
                elif mutation=='wrong-served-source': page['servedSources']={'e2-editor.html':'substituted-source'}
                elif mutation=='wrong-served-config': page['configSha256']='wrong'
                elif mutation=='missing-placement':
                    request=next(r for r in page['requests'] if r['message']['operation']=='editorPlaceCaretV2')
                    ident=request['message']['requestId'];page['requests'].remove(request)
                    page['responses']=[r for r in page['responses'] if r['message']['requestId']!=ident]
                elif mutation=='no-revision-advance':
                    req=next(r for r in page['requests'] if r['message']['operation']=='insertText')
                    next(r for r in page['responses'] if r['message']['requestId']==req['message']['requestId'])['message']['result']['revision']=0
                elif mutation=='both-silent-drop':
                    for target in cells:
                        if target['caseId'] != 'input-teh': continue
                        target_page=target['page']; data=(FIXTURES/'empty-en-US.odt').read_bytes()
                        target_page['observations'][0]['saved']=saved(data)
                        req=next(r for r in target_page['requests'] if r['message']['operation']=='save')
                        next(r for r in target_page['responses'] if r['message']['requestId']==req['message']['requestId'])['message']['result']['buffer']=binary(data)
                elif mutation=='extra-noop-mutation':
                    ident=999
                    page['requests'].append({'generation':1,'message':{'requestId':ident,'operation':'editorActionV2','payload':{'action':'set-bold','enabled':False}}})
                    page['responses'].append({'generation':1,'message':{'requestId':ident,'ok':True,'result':{}}})
                result=reader.judge(cells,self.config)
                self.assertNotEqual(result['verdict'],'PASS',mutation)
    def test_empty_body_numbering_is_a_substantive_transform(self):
        original=(FIXTURES/'empty-en-US.odt').read_bytes(); out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(out,'w') as dest:
            for name in source.namelist():
                data=source.read(name)
                if name=='content.xml':
                    root=ET.fromstring(data); p=next(root.iter(reader.q('text','p')))
                    parent=next(el for el in root.iter() if p in list(el)); parent.remove(p)
                    listing=ET.SubElement(parent,reader.q('text','list'),{reader.q('text','style-name'):'L1'})
                    ET.SubElement(listing,reader.q('text','list-item')).append(p)
                    auto=next(el for el in root.iter() if el.tag.endswith('}automatic-styles'))
                    style=ET.SubElement(auto,reader.q('text','list-style'),{reader.q('style','name'):'L1'})
                    ET.SubElement(style,reader.q('text','list-level-style-number'),{reader.q('text','level'):'1',reader.q('style','num-format'):'1'})
                    data=ET.tostring(root)
                dest.writestr(name,data)
        data=out.getvalue(); cells=copy.deepcopy(self.cells)
        for cell in cells:
            if cell['caseId']!='input-number': continue
            page=cell['page'];page['observations'][0]['saved']=saved(data)
            req=next(r for r in page['requests'] if r['message']['operation']=='save')
            next(r for r in page['responses'] if r['message']['requestId']==req['message']['requestId'])['message']['result']['buffer']=binary(data)
        result=reader.judge(cells,self.config)
        self.assertEqual(result['verdict'],'PASS',result)
    def test_observed_opaque_default_and_nondefault_opacity(self):
        evidence=Path(__file__).resolve().parents[2]/'findings/evidence/link-batch-v23/post-link/r2-attempt-01/s-init-prep-02'
        opacity='{urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0}opacity'
        for profile in PROFILES:
            record=json.loads((evidence/f'chrome-r1-direct-load-reopen-{profile}.json').read_text())
            obs=record['page']['observations'][0]
            original=reader.decode(obs['saved']['base64']); reopened=reader.decode(obs['reopened']['base64'])
            self.assertEqual(reader.semantic(original),reader.semantic(reopened),profile)
            changed=io.BytesIO(); edits=0
            with zipfile.ZipFile(io.BytesIO(reopened)) as source, zipfile.ZipFile(changed,'w') as dest:
                for name in source.namelist():
                    data=source.read(name)
                    if name.endswith('.xml'):
                        root=ET.fromstring(data)
                        for element in root.iter():
                            if element.get(opacity)=='100%': element.set(opacity,'50%'); edits+=1
                        data=ET.tostring(root)
                    dest.writestr(name,data)
            self.assertGreater(edits,0)
            self.assertNotEqual(reader.semantic(original),reader.semantic(changed.getvalue()),profile)
    def test_real_mirror_covers_transitive_import_graph(self):
        from v23_s_init_cases import instrument_identity, served_sources
        from run_v23_s_init import mirror
        config={'fixtures':fixture_identity(),'instrumentSha256':instrument_identity(),
                'servedSources':served_sources()}
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'mirror'
            mirror(target,config)
            verify_mirror(target,config)
    def test_actual_mirror_source_config_and_fixture_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory); (path/'s-init-fixtures').mkdir()
            source=b'actual served source'; fixture=b'actual copied fixture'
            config={'servedSources':{'e2-editor.html':reader.digest(source)},
                    'fixtures':{'authority.odt':reader.digest(fixture)}}
            files={'e2-editor.html':source,'s-init-fixtures/authority.odt':fixture,
                   's-init-config.json':config_bytes(config)}
            for name,data in files.items(): (path/name).write_bytes(data)
            verify_mirror(path,config)
            for name,data in files.items():
                (path/name).write_bytes(data+b'changed')
                with self.assertRaises(ValueError,msg=name): verify_mirror(path,config)
                (path/name).write_bytes(data)
    def test_explicit_pin_rejects_actual_profile_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory); path=project/'dist/profiles'/PROFILES[0];path.mkdir(parents=True)
            manifest={'profile':PROFILES[0],'coreCommit':'test','editorContract':{'abiVersion':5},'artifactFiles':{}}
            (path/'sdk-manifest.json').write_text(json.dumps(manifest))
            for name in ('probe.js','probe.wasm','sdk-worker.js'): (path/name).write_bytes(name.encode())
            with patch('v23_s_init_cases.PROJECT',project):
                profile_identity(PROFILES[0],reader.digest(b'probe.wasm'))
                with self.assertRaises(ValueError): profile_identity(PROFILES[0],'0'*64)
    def test_incidental_style_names_are_not_content(self):
        original=(FIXTURES/'language.odt').read_bytes(); out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(out,'w') as dest:
            for name in source.namelist():
                data=source.read(name)
                if name.endswith('.xml'): data=data.replace(b'"P1"',b'"RenamedGeneratedStyle"')
                dest.writestr(name,data)
        self.assertEqual(reader.semantic(original),reader.semantic(out.getvalue()))
    def test_fixture_control_differs_only_in_hyphenation(self):
        with zipfile.ZipFile(FIXTURES/'hyphenation-on.odt') as on, zipfile.ZipFile(FIXTURES/'hyphenation-off.odt') as off:
            self.assertEqual(on.namelist(),off.namelist())
            for name in on.namelist():
                left=on.read(name)
                if name=='content.xml': left=left.replace(b'fo:hyphenate="true"',b'fo:hyphenate="false"')
                self.assertEqual(left,off.read(name),name)

if __name__=='__main__': unittest.main()
