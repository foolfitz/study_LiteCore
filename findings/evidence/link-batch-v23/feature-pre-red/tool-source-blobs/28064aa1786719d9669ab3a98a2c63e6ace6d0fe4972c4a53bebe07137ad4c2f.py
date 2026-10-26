"""Pinned historical v19 source mirror and finite sixteen-cell pre-red inputs."""
import hashlib
import ast
import posixpath
import re
import json
from pathlib import Path
import subprocess
from odt_paragraphs import paragraph_texts_from_xml
from v23_feature_s_cases import ROOT, ARCHIVE, PINS, derive, read_rounds

PROJECT = ROOT / 'wasm_sdk_probe'
PROFILE = 'e2-editor-v19'
WASM = '1aafd4f9da42fd83d9be4c4e9edfbd818e3c7ea17d62fa1cb1bfbd47d1a32819'
ARTIFACT_PINS = {'probe.wasm': WASM,
    'probe.js': '46b2f40ac24b6a787481f8dbf341817f903d30f130580825e3f1145976a8c2e1',
    'sdk-worker.js': '00882139cd0b2e5898a96b8c7b21a4f8ee1d231ae13da39929e12088e9bb0241',
    'sdk-manifest.json': '902111faaed3430cc910744d1fb5d2925bd8d4728bf2f2b5d024ad26da5d58d5'}
SHELL_COMMIT = '6e9ec27eb4163aa52a9288ee7549569ae5a46405'
BUNDLE = 'e2/editor-shell-v2-bundle-v57.json'
PROFILE_ARCHIVE = PROJECT / 'build/archive/e2-editor-v19-1aafd4f9-worker-00882139'
NATIVE_FIXTURE = ROOT / ARCHIVE / 'fixture-as-run.fodt'
BROWSERS = ('chrome','firefox')
MARKER = 'Z'

def digest(raw): return hashlib.sha256(raw).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def encoded(value): return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()

def historical(path):
    return subprocess.check_output(['git','show',f'{SHELL_COMMIT}:wasm_sdk_probe/{path}'],cwd=ROOT)

def frozen_sources():
    bundle = json.loads(historical(BUNDLE))
    sources = {}
    for item in bundle['included']:
        data = historical(item['path'])
        if digest(data) != item['sha256']: raise ValueError('historical shell source differs: '+item['path'])
        sources[item['path'].removeprefix('web/')] = data
    original = historical('web/e2-editor.html')
    old = b'<script type="module" src="./e2-editor-app.js"></script>'
    if original.count(old) != 1: raise ValueError('historical page entry not unique')
    sources['e2-editor.html'] = original.replace(old,b'<script type="module" src="./v23-feature-pre-red.js"></script>')
    sources['v23-feature-pre-red.js'] = (PROJECT/'web/v23-feature-pre-red.js').read_bytes()
    for name,data in sources.items():
        if not name.endswith('.js'): continue
        imports=re.findall(r'(?:from\s*|import\s*\(?)\s*[\"\']([^\"\']+)[\"\']', data.decode())
        for spec in imports:
            if spec.startswith('.'):
                target=posixpath.normpath(posixpath.join(posixpath.dirname(name),spec))
                if target not in sources: raise ValueError('missing frozen import: '+target)
    return sources

def fixture_paragraphs():
    raw=NATIVE_FIXTURE.read_bytes()
    if digest(raw)!=PINS['fixture-as-run.fodt']: raise ValueError('source fixture changed')
    return paragraph_texts_from_xml(raw)

def cases():
    table = derive(read_rounds())
    rows = {r['id']:r for r in table['cases'] if 'v19-pre-red' in r['memberships']}
    paragraphs = fixture_paragraphs()
    for row in rows.values():
        point = row['setup']['logicalPointNames'][0]
        if point == 'w.l1start': plan={'paragraph':4,'offset':'visual-end'}
        else:
            part,offset=point[1:].split('.')
            plan={'paragraph':int(part),'offset':int(offset) if offset.isdecimal() else offset}
        if row['shape']=='empty-para': plan={'paragraph':2,'offset':'next-empty'}
        plan['query']=paragraphs[plan['paragraph']]
        row['discovery']=plan
    return rows

def identity(pin):
    if pin != WASM: raise ValueError('explicit pin is not frozen v19')
    directory=PROJECT/'dist/profiles'/PROFILE
    manifest=json.loads((directory/'sdk-manifest.json').read_text())
    if manifest['profile']!=PROFILE or manifest['editorContract']['abiVersion']!=4:
        raise ValueError('wrong historical profile/ABI')
    paths={'probe.wasm','probe.js','sdk-worker.js','sdk-manifest.json'}
    paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks',[]): paths.update((pack['data'],pack['metadata']))
    hashes={p:sha(directory/p) for p in sorted(paths)}
    for name in ('probe.wasm','probe.js','sdk-worker.js','sdk-manifest.json'):
        if hashes[name]!=ARTIFACT_PINS[name] or hashes[name]!=sha(PROFILE_ARCHIVE/name): raise ValueError('historical profile archive differs: '+name)
    if hashes['probe.wasm']!=pin: raise ValueError('WASM differs')
    return {'profile':PROFILE,'artifacts':hashes,'editorAbi':4}

def config(pin):
    sources=frozen_sources()
    pending=[PROJECT/'tools'/name for name in ('v23_feature_pre_red_cases.py',
        'run_v23_feature_pre_red.py','judge_v23_feature_pre_red.py')]+[PROJECT/'web/serve.py']
    closure=set()
    while pending:
        path=pending.pop().resolve()
        if path in closure: continue
        closure.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else (
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                candidate=PROJECT/'tools'/Path(*name.split('.')).with_suffix('.py')
                if candidate.is_file():pending.append(candidate)
    return {'schema':1,'profile':identity(pin),'shellCommit':SHELL_COMMIT,
        'bundleSha256':digest(historical(BUNDLE)),
        'originalHtmlSha256':digest(historical('web/e2-editor.html')),
        'servedSources':{p:digest(b) for p,b in sources.items()},
        'instrumentSources':{str(p.relative_to(PROJECT)):sha(p) for p in sorted(closure)},
        'cases':cases(),'fixtureSha256':PINS['fixture-as-run.fodt'],
        'fixtureParagraphs':fixture_paragraphs(),
        'fixtureManifest':{'fixtures':[{'id':'list-contexts'}]},'marker':MARKER,
        'stateOperation':'editorGetStateV2'}

def mirror(target, plan):
    target.mkdir(parents=True,exist_ok=False)
    (target/'profiles').symlink_to(PROJECT/'dist/profiles',target_is_directory=True)
    for name,raw in frozen_sources().items():
        path=target/name; path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    fixture=NATIVE_FIXTURE.read_bytes()
    if digest(fixture)!=plan['fixtureSha256']: raise ValueError('native fixture changed')
    (target/'e1-fixtures').mkdir()
    (target/'e1-fixtures/manifest.json').write_bytes(encoded(plan['fixtureManifest']))
    (target/'e1-fixtures/list-contexts.odt').write_bytes(fixture)
    (target/'feature-pre-red.odt').write_bytes(fixture)
    (target/'pre-red-config.json').write_bytes(encoded(plan))

def verify_mirror(target,plan):
    if {p:sha(target/p) for p in plan['servedSources']}!=plan['servedSources']:
        raise ValueError('executed source mirror differs')
    for name in ('feature-pre-red.odt','e1-fixtures/list-contexts.odt'):
        if sha(target/name)!=plan['fixtureSha256']: raise ValueError('fixture mirror differs')
    if (target/'pre-red-config.json').read_bytes()!=encoded(plan): raise ValueError('config mirror differs')
    if (target/'e1-fixtures/manifest.json').read_bytes()!=encoded(plan['fixtureManifest']): raise ValueError('fixture manifest differs')
    return {'sources':plan['servedSources'],'fixtureSha256':plan['fixtureSha256'],
            'configSha256':digest(encoded(plan)),'fixtureManifestSha256':digest(encoded(plan['fixtureManifest']))}
