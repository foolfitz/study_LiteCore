"""Actual ABI6 selection population and logical setup plans; no browser execution."""
import hashlib
import json
import re
from pathlib import Path
from odt_paragraphs import paragraph_texts_from_xml
from v23_feature_s_cases import ROOT, ARCHIVE, PINS, derive, read_rounds

PROJECT=ROOT/'wasm_sdk_probe'
PROFILE='e2-editor-v23'
BROWSERS=('chrome','firefox')
BUNDLE='e2/editor-shell-v2-bundle-v76.json'
BUNDLE_FILE_SHA256='555590f6eb6e7600ed313b7d866a6a0ba30f190efc6e9c97bb86483b05627093'
PAGE_SHA256='c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490'
ARTIFACT_PINS={
 'probe.wasm':'fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658',
 'probe.js':'4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e',
 'sdk-worker.js':'3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5',
 'sdk-manifest.json':'2b23901ff94edd4c52611d03a31242c9ecfbf33fcf89835c1af13ac04a1e2a91'}
ARCHIVED_PROFILE=PROJECT/'build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6'
FIXTURE=ROOT/ARCHIVE/'fixture-as-run.fodt'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
def sha(path):return digest(Path(path).read_bytes())

def paragraphs():
    raw=FIXTURE.read_bytes()
    if digest(raw)!=PINS['fixture-as-run.fodt']:raise ValueError('native fixture differs')
    return paragraph_texts_from_xml(raw)

def point_plan(name,texts):
    """Native names identify logical inputs; no native coordinates are copied."""
    if name in ('w.l1start','w.l1end'):
        return {'name':name,'paragraph':4,'query':texts[4],
                'anchor':'search-first-displayed-line','offset':0 if name.endswith('start') else 'visual-end',
                'prefixRule':'empty' if name.endswith('start') else 'nonempty-query-prefix',
                'requiredWitness':'actual-first-line-start-and-end-affinity'}
    match=re.fullmatch(r'p([0-9]+)\.([0-9]+|end)',name)
    if not match:raise ValueError('unknown native logical point: '+name)
    paragraph=int(match[1]);offset=match[2]
    if not 0<=paragraph<len(texts):raise ValueError('logical paragraph outside fixture')
    if not texts[paragraph]:
        if name!='p3.0':raise ValueError('undeclared empty-paragraph traversal')
        return {'name':name,'paragraph':paragraph,'searchParagraph':2,'query':texts[2],
                'anchor':'search-text-start','offset':'next-empty','prefix':texts[2]+'\n',
                'requiredWitness':'preceding-paragraph-end-right-empty-caret'}
    if offset=='end':offset=len(texts[paragraph])
    else:offset=int(offset)
    if offset>len(texts[paragraph]):raise ValueError('logical offset outside fixture')
    return {'name':name,'paragraph':paragraph,'query':texts[paragraph],
            'anchor':'search-text-start','offset':offset,'prefix':texts[paragraph][:offset],
            'requiredWitness':'actual-text-start-prefix-and-restored-caret'}

def cases(table=None):
    table=table if table is not None else derive(read_rounds());texts=paragraphs();result={}
    for row in table['cases']:
        setup=row['setup'];names=setup['logicalPointNames']
        if row['id'] in result:raise ValueError('duplicate selection case')
        method=setup['method']
        if method not in ('click','drag','click+Shift+Right x3','click+End'):
            raise ValueError('unmapped native shape method: '+method)
        if len(names)!=(2 if method=='drag' else 1):raise ValueError('native shape point arity differs')
        points={n:point_plan(n,texts) for n in dict.fromkeys(names+[setup['expectedMovingPointName']])}
        # Actual executable route remains declared separately from native provenance.
        result[row['id']]={**row,'pointPlans':points,'nativeSetupMethod':method,
            'anchorPointName':names[0], 'movingPointName':setup['expectedMovingPointName'],
            'productKey':{'key':{'Left':'ArrowLeft','Right':'ArrowRight','Up':'ArrowUp','Down':'ArrowDown',
                                 'Home':'Home','End':'End'}[row['key']], 'shiftKey':row['extendSelection']},
            'reference':{'freshOriginalDocument':True,'fromPoint':setup['expectedMovingPointName'],
                         'key':row['key'],'shiftKey':False,
                         'logicalEndpointWitness':'NOT_ESTABLISHED_UNPERFORMED',
                         'nativeLiteralRequired':row['key'] in ('Left','Right'),
                         'singleLineRequiredForHomeEndNative':row['key'] in ('Home','End')},
            'default':'NOT_ESTABLISHED_UNPERFORMED'}
    if len(result)!=108:raise ValueError('selection population differs')
    return result

def interactions(table,rounds,texts):
    """S4: every native kind=interaction row; its caret-mid origin comes from the S1 shape table."""
    origins={tuple(r['setup']['logicalPointNames']) for r in table['cases'] if r['shape']=='caret-mid'}
    if len(origins)!=1 or len(next(iter(origins)))!=1:raise ValueError('caret-mid origin not unique')
    origin=next(iter(origins))[0]
    keys={'Shift+Right':('ArrowRight','move-character-right'),'Shift+Down':('ArrowDown','move-line-down'),
          'Shift+End':('End','move-line-end')}
    methods={'a':'click','b':'drag','c':'public-select-range'}
    result={}
    for row in table['S4']:
        natives=[]
        for ref in row['nativeReferences']:
            native=rounds[ref['round']-1][ref['line']-1]
            if native.get('sourceLine')!=ref['line'] or native.get('arm')!=row['id'] or native.get('kind')!='interaction':
                raise ValueError('native interaction reference differs')
            natives.append(native)
        names=row['logicalPointNames']
        if row['id'] in result or row['step'] not in methods or row['firstKey'] not in keys or len(natives)!=3 \
                or len(names)!=(1 if row['step']=='a' else 2):
            raise ValueError('unmapped native interaction')
        key,action=keys[row['firstKey']]
        result[row['id']]={**row,'method':methods[row['step']],'originPointName':origin,
            'firstProductKey':{'key':key,'shiftKey':True},'firstAction':action,
            'pointPlans':{n:point_plan(n,texts) for n in dict.fromkeys([origin]+names)},
            'nativeAfterFirstKeyText':[n['afterFirstKey']['getTextSelection'] for n in natives],
            'nativeAfterStepText':[n['afterStep']['getTextSelection'] for n in natives],
            'nativeShiftHomeAfterClickText':[n['shiftHomeAfterClick'] for n in natives] if row['step']=='a' else None,
            'memberships':['S4'],'default':'NOT_ESTABLISHED_UNPERFORMED'}
    if len(result)!=9:raise ValueError('S4 population differs')
    return result

NATIVE_S5=ROOT/'findings/evidence/link-batch-v23/feature-protocol/s5-native'
NATIVE_S5_READER_SHA256='014c1e0d51f6a522101c2acc6395797a8f974822cf085c8ea7f8f978b64ec538'
NATIVE_S5_TYPE_READER_SHA256='305306785509764f1130709650ca44c8a6c0cc320b0d79bb632bbe0817870706'
S5_KEYS={'Shift+Left':('ArrowLeft',('shift',)),'Shift+Right':('ArrowRight',('shift',)),'Shift+Up':('ArrowUp',('shift',)),
         'Shift+Down':('ArrowDown',('shift',)),'Shift+Home':('Home',('shift',)),'Shift+End':('End',('shift',)),
         'Backspace':('Backspace',()),'Delete':('Delete',()),'text:x':('x',())}

def native_saves(run,cell):
    saves={}
    for side in ('before','after'):
        path=NATIVE_S5/run/'saves'/Path(cell['saves'][side]['path']).name
        if sha(path)!=cell['saves'][side]['sha256']:raise ValueError('native S5 save bytes differ: '+cell['id'])
        saves[side]={'path':str(path.relative_to(ROOT)),'sha256':cell['saves'][side]['sha256']}
    return saves

def s5(table,cases_by_id):
    """S5: every Table 1 arm by the seven families, with the native references bound by hash:
    run-01 for the deletion families, run-03 for type (fable ruling 3; run-02 printed timestamps
    too coarse to witness order).  run-01's type saves measured x-then-Shift and are never an
    oracle; a type cell without run-03's order witness takes the fresh settled-WASM
    reference (fallback A), its reasons recorded."""
    raw=(NATIVE_S5/'reader-01.json').read_bytes()
    if digest(raw)!=NATIVE_S5_READER_SHA256:raise ValueError('native S5 reader output differs')
    native=json.loads(raw)
    if native.get('verdict')!='NATIVE_S5_SAVES_AVAILABLE' or native.get('problems')!=[]:raise ValueError('native S5 references unavailable')
    native={c['id']:c for c in native['cells']}
    raw=(NATIVE_S5/'reader-03.json').read_bytes()
    if digest(raw)!=NATIVE_S5_TYPE_READER_SHA256:raise ValueError('native S5 type reader output differs')
    typed=json.loads(raw)
    if typed.get('verdict')!='NATIVE_S5_TYPE_SAVES_READ' or typed.get('problems')!=[]:raise ValueError('native S5 type references unavailable')
    typed={c['id']:c for c in typed['cells']}
    result={}
    for row in table['S5']:
        source=cases_by_id.get(row['sourceArm'])
        if row['id'] in result or source is None or not source['extendSelection']:raise ValueError('unmapped S5 source arm')
        keys=[S5_KEYS[k] for k in row['sequence']]
        shift=[i for i,k in enumerate(row['sequence']) if k.startswith('Shift+')]
        if len(shift)!=1 or row['sequence'][shift[0]]!='Shift+'+source['key']:raise ValueError('S5 sequence differs from its source arm')
        reference=witness=fallback=None
        if row['referencePolicy']!='settled-wasm' and row['family']=='type':
            cell=typed.get(row['id'])
            if cell is None:raise ValueError('native S5 type cell missing: '+row['id'])
            if cell.get('status')=='NATIVE_SAVE_AVAILABLE' and cell.get('orderWitness') in ('selection-before-x','settle-only'):
                reference=native_saves('run-03',cell);witness=cell['orderWitness']
            elif cell.get('status')=='NOT_ESTABLISHED' and cell.get('reasons'):fallback=cell['reasons']
            else:raise ValueError('native S5 type cell neither witnessed nor reasoned: '+row['id'])
        elif row['referencePolicy']!='settled-wasm':
            cell=native.get(row['id'])
            if cell is None or cell.get('status')!='NATIVE_SAVE_AVAILABLE':raise ValueError('native S5 save missing: '+row['id'])
            reference=native_saves('run-01',cell)
        result[row['id']]={'id':row['id'],'sourceArm':row['sourceArm'],'family':row['family'],'sequence':row['sequence'],
            'keys':[{'key':k,'mods':list(m)} for k,m in keys],'shiftIndex':shift[0],'comparison':row['comparison'],
            'referencePolicy':row['referencePolicy'],'native':reference,'nativeOrderWitness':witness,'nativeFallback':fallback,
            'memberships':['S5'],'settledReference':row['referencePolicy']!='native' or reference is None,
            'default':'NOT_ESTABLISHED_UNPERFORMED'}
    if len(result)!=588:raise ValueError('S5 population differs')
    return result

def identity():
    directory=PROJECT/'dist/profiles'/PROFILE
    for name,expected in ARTIFACT_PINS.items():
        if sha(directory/name)!=expected or sha(ARCHIVED_PROFILE/name)!=expected:
            raise ValueError('actual feature/archive identity differs: '+name)
    manifest=json.loads((directory/'sdk-manifest.json').read_text())
    if manifest['profile']!=PROFILE or manifest['editorContract']['abiVersion']!=6:
        raise ValueError('actual feature ABI/profile differs')
    if sha(PROJECT/BUNDLE)!=BUNDLE_FILE_SHA256:raise ValueError('final shell manifest differs')
    bundle=json.loads((PROJECT/BUNDLE).read_text())
    for row in bundle['included']:
        path=row['path'];served=path.removeprefix('web/')
        if sha(PROJECT/path)!=row['sha256'] or sha(PROJECT/'dist'/served)!=row['sha256']:
            raise ValueError('final shell source/dist differs: '+path)
    if sha(PROJECT/'web/e2-editor-app.js')!=PAGE_SHA256:raise ValueError('final page differs')
    paths=set(ARTIFACT_PINS)
    paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks',[]):paths.update((pack['data'],pack['metadata']))
    return {'profile':PROFILE,'editorAbi':6,'artifacts':{n:sha(directory/n) for n in sorted(paths)},
            'bundleFileSha256':BUNDLE_FILE_SHA256,'bundleSha256':bundle['bundleSha256'],
            'pageSha256':PAGE_SHA256,'originalHtmlSha256':sha(PROJECT/'web/e2-editor.html')}

def sources():
    import posixpath
    bundle=json.loads((PROJECT/BUNDLE).read_text());out={}
    for row in bundle['included']:
        raw=(PROJECT/row['path']).read_bytes()
        if digest(raw)!=row['sha256']:raise ValueError('frozen source differs')
        out[row['path'].removeprefix('web/')]=raw
    original=(PROJECT/'web/e2-editor.html').read_bytes()
    needle=b'<script type="module" src="./e2-editor-app.js"></script>'
    if original.count(needle)!=1:raise ValueError('product HTML entry differs')
    out['e2-editor.html']=original.replace(needle,b'<script type="module" src="./v23-feature-selection.js"></script>')
    out['v23-feature-selection.js']=(PROJECT/'web/v23-feature-selection.js').read_bytes()
    for name,raw in out.items():
        if not name.endswith('.js'):continue
        for spec in re.findall(r'(?:from\s*|import\s*\(?)\s*[\"\']([^\"\']+)[\"\']',raw.decode()):
            if spec.startswith('.') and posixpath.normpath(posixpath.join(posixpath.dirname(name),spec)) not in out:
                raise ValueError('missing executed import: '+spec)
    return out

def config():
    import ast
    pending=[PROJECT/'tools'/n for n in ('v23_feature_selection_cases.py','run_v23_feature_selection.py','judge_v23_feature_selection.py')]+[PROJECT/'web/serve.py']
    closure=set()
    while pending:
        path=pending.pop().resolve()
        if path in closure:continue
        closure.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                candidate=PROJECT/'tools'/Path(*name.split('.')).with_suffix('.py')
                if candidate.is_file():pending.append(candidate)
    texts=paragraphs();rounds=read_rounds();table=derive(rounds);selection=cases(table)
    return {'schema':1,'profile':identity(),'servedSources':{n:digest(v) for n,v in sources().items()},
            'instrumentSources':{str(p.relative_to(PROJECT)):sha(p) for p in sorted(closure)},
            'cases':selection,'interactions':interactions(table,rounds,texts),'s5':s5(table,selection),'sourceTable':table,'fixtureSha256':PINS['fixture-as-run.fodt'],
            'fixtureParagraphs':texts,'fixtureManifest':{'fixtures':[{'id':'list-contexts'}]},
            'readinessPoint':point_plan('p0.0',texts),
            'mappingPoints':[point_plan(f'p{i}.0',texts) for i in range(len(texts))]}

def mirror(target,plan):
    target.mkdir(parents=True,exist_ok=False)
    (target/'profiles').symlink_to(PROJECT/'dist/profiles',target_is_directory=True)
    for name,raw in sources().items():
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    (target/'e1-fixtures').mkdir()
    (target/'e1-fixtures/manifest.json').write_bytes(encoded(plan['fixtureManifest']))
    for name in ('e1-fixtures/list-contexts.odt','feature-selection.odt'):(target/name).write_bytes(FIXTURE.read_bytes())
    (target/'selection-config.json').write_bytes(encoded(plan))

def verify_mirror(target,plan):
    for name,want in plan['servedSources'].items():
        if sha(target/name)!=want:raise ValueError('actual source mirror differs: '+name)
    for name in ('e1-fixtures/list-contexts.odt','feature-selection.odt'):
        if sha(target/name)!=plan['fixtureSha256']:raise ValueError('actual fixture mirror differs')
    for name,value in [('selection-config.json',plan),('e1-fixtures/manifest.json',plan['fixtureManifest'])]:
        if (target/name).read_bytes()!=encoded(value):raise ValueError('actual config mirror differs')
    return {'sources':plan['servedSources'],'fixtureSha256':plan['fixtureSha256'],'configSha256':digest(encoded(plan))}
