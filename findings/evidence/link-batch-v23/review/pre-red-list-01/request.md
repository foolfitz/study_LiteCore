Perform a bounded adversarial source review of the historical v19 list-mid setup correction only. Reply in English. Do not invoke tools or propose broader gates. Native logical point remains paragraph7 offset5, query List item one, exact selected prefix "List " (space required). Actual old run search click was x2138 at text start; Home moved to x1778 before the label, then first Right returned to2138, so five Rights selected only List. New branch uses actual search-text-start, no Home, exactly five Rights, literal prefix unchanged. Find a concrete causal defect in setup or its evidence reader that could accept a wrong point or corrupt the fixed16-cell pre-red population. Distinguish missing future runtime from actual source bugs. If none, state NO_CONCRETE_FINDING with review scope. Product WASM/features unchanged.

FILE wasm_sdk_probe/tools/v23_feature_pre_red_cases.py
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
        if row['shape']=='list-mid': plan['anchor']='search-text-start'
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

FILE wasm_sdk_probe/web/v23-feature-pre-red.js
// Observation-only entry around the pinned v57 product page; no SDK overrides.
import {NarrowEditorV2Session} from './editor-shell-v2/narrow-editor-v2-session.js';
const result = window.__featurePreRed = {schema:1, profile:'e2-editor-v19',
  caseId:new URLSearchParams(location.search).get('caseId'), userAgent:navigator.userAgent,
  requests:[],responses:[],events:[],cancels:[],workers:[],inputs:[],calls:[],opens:[],complete:false};
const bytes64 = bytes => {let s=''; const b=new Uint8Array(bytes);
  for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s);};
const hash = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
  .map(x=>x.toString(16).padStart(2,'0')).join('');
const snap = value => {
  if(value instanceof ArrayBuffer)return {encoding:'base64',bytes:value.byteLength,data:bytes64(value)};
  if(ArrayBuffer.isView(value))return snap(value.buffer.slice(value.byteOffset,value.byteOffset+value.byteLength));
  if(Array.isArray(value))return value.map(snap);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,snap(v)]));
  return value;
};
let generation=0,current,config;
const NativeWorker=window.Worker;
window.Worker=class extends NativeWorker {
  constructor(url,options){super(url,options);this.observedGeneration=++generation;
    const gen=this.observedGeneration;this.observedRecord={generation:gen,url:String(url),createdAt:performance.now()};
    result.workers.push(this.observedRecord);
    this.addEventListener('message',event=>{const item={generation:gen,at:performance.now(),message:snap(event.data)};
      if(event.data?.kind==='response')result.responses.push(item);
      if(event.data?.kind==='event')result.events.push(item);});}
  postMessage(message,...args){const item={generation:this.observedGeneration,at:performance.now(),message:snap(message)};
    if(message?.kind==='request')result.requests.push(item);
    if(message?.kind==='cancel')result.cancels.push(item);
    return super.postMessage(message,...args);}
  terminate(){this.observedRecord.terminatedAt=performance.now();return super.terminate();}
};
const openOriginal=NarrowEditorV2Session.prototype.open;
NarrowEditorV2Session.prototype.open=async function(input,...args){
  const record={serial:result.opens.length+1,name:input.name,fixtureSha256:await hash(input.bytes),startedAt:performance.now()};
  result.opens.push(record);current=this;
  const value=await openOriginal.call(this,input,...args);
  Object.assign(record,{finishedAt:performance.now(),generation,documentHandle:this.document.handle});
  result.currentOpen=record;return value;
};
const sinkSnapshot=()=>{const el=document.querySelector('#sink');return {id:el?.id,
  active:document.activeElement===el,disabled:el?.disabled,readOnly:el?.readOnly,connected:el?.isConnected,
  documentHandle:current?.document?.handle,generation};};
for(const type of ['keydown','keyup','beforeinput','input'])document.addEventListener(type,event=>{
  if(event.target?.id==='sink')result.inputs.push({type,at:performance.now(),isTrusted:event.isTrusted,
    key:event.key,code:event.code,repeat:event.repeat,inputType:event.inputType,data:event.data,sink:sinkSnapshot()});
},true);
async function call(name,fn){const entry={name,generation,documentHandle:current?.document?.handle,startedAt:performance.now()};
  result.calls.push(entry);try{const value=await fn();entry.result=snap(value);entry.ok=true;return value;}
  catch(error){entry.ok=false;entry.error={code:error?.code,message:String(error?.message||error)};throw error;}
  finally{entry.finishedAt=performance.now();}}
const state=name=>call(name,()=>current.editor.getState());
const move=(direction,name)=>call(name,()=>current.editor.action('move-'+direction));
const point=caret=>({xTwips:caret.x,yTwips:caret.y+Math.floor(caret.height/2)});
async function save(name){const saved=await call(name,()=>current.save());
  return {base64:bytes64(saved.bytes),sha256:await hash(saved.bytes)};}
async function place(p,name){return call(name,()=>current.placeCaret(p.xTwips,p.yTwips));}
async function locate(plan,prefix){
  const found=await call(prefix+'-search',()=>current.document.search(plan.query));
  const coords=String(found?.selections?.[0]?.rectangles||'').split(';')[0].split(',').map(Number);
  if(coords.length!==4||!coords.every(Number.isFinite))throw new Error('actual search rectangle missing');
  await place({xTwips:coords[0],yTwips:coords[1]+Math.floor(coords[3]/2)},prefix+'-search-click');
  // List Home enters the label position; native p7.5 counts from text start.
  if(plan.anchor!=='search-text-start')await move('line-home',prefix+'-home');
  const start=await state(prefix+'-start-state');
  if(typeof plan.offset==='number')for(let n=0;n<plan.offset;n++)await move('character-right',prefix+'-right-'+n);
  else {await move('line-end',prefix+'-end');
    if(plan.offset==='next-empty')await move('character-right',prefix+'-next-empty');}
  const target=await state(prefix+'-target-state');
  const a=point(start.caret),b=point(target.caret);
  await call(prefix+'-prefix-select',()=>current.editor.selectRange(a,b));
  const selected=await call(prefix+'-prefix-text',()=>current.document.getSelection());
  await place(b,prefix+'-restore-point');
  const final=await state(prefix+'-final-state');
  return {plan,start,target,selected,final};
}
function fail(error){result.fatal={code:error?.code,message:String(error?.message||error)};result.complete=true;return false;}
window.__preRedControl={
  async prepareReadiness(){try{
    result.readiness={open:snap(result.currentOpen)};
    result.readiness.setup=await locate({query:config.fixtureParagraphs[0],paragraph:0,offset:0},'readiness');
    result.readiness.beforeState=await state('readiness-before-state');
    result.readiness.beforeSave=await save('readiness-before-save');
    document.querySelector('#sink').focus();result.readiness.beforeInput=sinkSnapshot();
    result.phase='send-readiness-Z';return true;
  }catch(error){return fail(error);}},
  async finishReadiness(){try{
    result.readiness.afterSave=await save('readiness-after-save');
    result.readiness.afterState=await state('readiness-after-state');
    result.phase='readiness-recorded';return true;
  }catch(error){return fail(error);}},
  async measure(){try{
    const plan=config.cases[result.caseId];
    if(!plan||result.currentOpen.serial<=result.readiness.open.serial)throw new Error('fresh measured open absent');
    result.measured={open:snap(result.currentOpen)};
    result.measured.originalSave=await save('measured-original-save');
    result.measured.setup=await locate(plan.discovery,'measured');
    result.measured.before=await state('measured-before-state');
    result.measured.reply=await call('measured-shift',()=>current.editor.moveCharacter(plan.key.toLowerCase(),{extendSelection:true}));
    result.measured.replyAt=performance.now();
    // Observation-only delay from the original S2 criterion, never a completion policy.
    await new Promise(resolve=>setTimeout(resolve,500));
    result.measured.readbackRequestedAt=performance.now();
    result.measured.readback=await state('measured-readback');
    result.measured.activeSelection=await call('measured-active-selection',()=>current.document.getSelection());
    await call('measured-close',()=>current.close());
    result.complete=true;result.phase='complete';return true;
  }catch(error){return fail(error);}}
};
try{
  const configBytes=await (await fetch('./pre-red-config.json',{cache:'no-store'})).arrayBuffer();
  result.configSha256=await hash(configBytes);config=JSON.parse(new TextDecoder().decode(configBytes));
  result.servedSources={};result.artifacts={};
  for(const path of Object.keys(config.servedSources)){
    const response=await fetch('./'+path,{cache:'no-store'});if(!response.ok)throw new Error('source HTTP '+path);
    result.servedSources[path]=await hash(await response.arrayBuffer());}
  for(const path of Object.keys(config.profile.artifacts)){
    const response=await fetch('./profiles/e2-editor-v19/'+path,{cache:'no-store'});if(!response.ok)throw new Error('artifact HTTP '+path);
    result.artifacts[path]=await hash(await response.arrayBuffer());}
  result.fixtureManifestSha256=await hash(await (await fetch('./e1-fixtures/manifest.json',{cache:'no-store'})).arrayBuffer());
  await import('./e2-editor-app.js');result.booted=true;
}catch(error){fail(error);}

FILE wasm_sdk_probe/tools/judge_v23_feature_pre_red.py
#!/usr/bin/env python3
"""Public S2 evidence reader; old-v19 stale replies are expected-red only after readiness."""
import argparse
import base64
import io
import json
from pathlib import Path
import re
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from odt_paragraphs import paragraph_texts_from_xml
from v23_feature_pre_red_cases import PROFILE,BROWSERS,WASM,config,encoded,digest,verify_mirror

class NotEstablished(ValueError): pass

def need(value,message):
    if not value: raise NotEstablished(message)

def binary(value):
    need(value.get('encoding')=='base64','binary wire evidence absent')
    raw=base64.b64decode(value['data'],validate=True)
    need(len(raw)==value['bytes'],'binary length mismatch')
    return raw

def paragraphs(saved):
    raw=base64.b64decode(saved['base64'],validate=True)
    need(digest(raw)==saved['sha256'],'saved bytes hash differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return paragraph_texts_from_xml(archive.read('content.xml'))

def stream(page):
    requests={}; replies={}
    for item in page['requests']:
        key=(item['generation'],item['message']['requestId'])
        need(key not in requests,'duplicate request identity'); requests[key]=item
    for item in page['responses']:
        key=(item['generation'],item['message']['requestId'])
        need(key not in replies,'duplicate terminal'); replies[key]=item
    need(set(replies)<=set(requests),'terminal has no posted request')
    return requests,replies

def call_binding(page,name,operation,requests,replies):
    calls=[c for c in page['calls'] if c['name']==name]
    need(len(calls)==1 and calls[0].get('ok') is True,'missing/refused public call '+name)
    call=calls[0]
    matches=[(key,r) for key,r in requests.items() if r['generation']==call['generation'] and
             r['message']['operation']==operation and call['startedAt']<=r['at']<=call['finishedAt']]
    need(len(matches)==1,'missing/nonunique wire call '+name)
    key,request=matches[0]; terminal=replies.get(key)
    need(terminal is not None and terminal['message'].get('ok') is True,'missing/refused terminal '+name)
    need(request['at']<=terminal['at']<=call['finishedAt'],'terminal outside public call '+name)
    need(request['message']['payload'].get('documentHandle')==call['documentHandle'],'wrong document '+name)
    return call,request,terminal

def binding(page,plan,browser):
    need(page.get('profile')==PROFILE,'wrong profile')
    need(page.get('caseId') in plan['cases'],'undeclared pre-red case')
    ua=page.get('userAgent','')
    family='firefox' if re.search(r'Firefox/\d',ua) else 'chrome' if re.search(r'(?:Headless)?Chrome/\d',ua) else None
    need(family==browser,'actual browser family differs')
    need(page.get('servedSources')==plan['servedSources'],'served source identity differs')
    need(page.get('artifacts')==plan['profile']['artifacts'],'actual profile/resource identity differs')
    need(page.get('configSha256')==digest(encoded(plan)),'actual config identity differs')
    need(page.get('fixtureManifestSha256')==digest(encoded(plan['fixtureManifest'])),'fixture alias manifest differs')
    need(not page.get('fatal'),'unclean page is not expected red')
    return stream(page)

def opened(page,record,plan,requests,replies):
    need(record.get('fixtureSha256')==plan['fixtureSha256'],'opened fixture identity differs')
    selected=[(k,r) for k,r in requests.items() if r['generation']==record['generation'] and
              r['message']['operation']=='open']
    need(len(selected)==1,'actual open missing/nonunique')
    key,req=selected[0]; response=replies.get(key)
    need(response is not None and response['message'].get('ok') is True,'successful open missing')
    need(response['message']['result']['documentHandle']==record['documentHandle'],'wrong open handle')
    need(req['message']['payload']['name']==record['name'],'open name differs')
    need(digest(binary(req['message']['payload']['buffer']))==plan['fixtureSha256'],'open bytes differ')
    workers=[w for w in page['workers'] if w['generation']==record['generation']]
    need(len(workers)==1 and workers[0]['url'].endswith('/profiles/'+PROFILE+'/sdk-worker.js'),'wrong actual worker')
    return record['documentHandle'],record['generation']

def bound_state(page,name,value,requests,replies):
    call,req,res=call_binding(page,name,'editorGetStateV2',requests,replies)
    need(call['result']==value==res['message']['result'],'state is not the actual V2 reply')
    need(value.get('documentHandle')==req['message']['payload']['documentHandle'],'state belongs to another document')
    return req,res

def bound_save(page,name,saved,requests,replies):
    call,req,res=call_binding(page,name,'save',requests,replies)
    raw=binary(res['message']['result']['buffer'])
    need(digest(raw)==saved['sha256'],'save not bound to actual wire bytes')
    need(binary(call['result']['bytes'])==raw,'public saved result differs')
    return paragraphs(saved)

def validate_setup(page,prefix,setup,plan,requests,replies):
    need(setup['plan']==plan,'setup discovery differs')
    _,search_req,search_res=call_binding(page,prefix+'-search','search',requests,replies)
    need(search_req['message']['payload']['query']==plan['query'],'setup search query differs')
    coordinates=list(map(int,search_res['message']['result']['selections'][0]['rectangles'].split(';')[0].split(',')))
    need(len(coordinates)==4,'actual search rectangle absent')
    _,click_req,_=call_binding(page,prefix+'-search-click','click',requests,replies)
    payload=click_req['message']['payload']
    need((payload['xTwips'],payload['yTwips'])==(coordinates[0],coordinates[1]+coordinates[3]//2),
         'setup point not derived from actual search')
    text_start=plan.get('anchor')=='search-text-start'
    moves=[] if text_start else [(prefix+'-home','move-line-home')]
    if isinstance(plan['offset'],int):moves += [(prefix+'-right-'+str(i),'move-character-right') for i in range(plan['offset'])]
    else:
        moves.append((prefix+'-end','move-line-end'))
        if plan['offset']=='next-empty':moves.append((prefix+'-next-empty','move-character-right'))
    order=[prefix+'-search',prefix+'-search-click']
    if not text_start:order.append(prefix+'-home')
    order.append(prefix+'-start-state')
    order += [name for name,_ in (moves if text_start else moves[1:])]
    order += [prefix+'-target-state',prefix+'-prefix-select',prefix+'-prefix-text',prefix+'-restore-point',prefix+'-final-state']
    previous=-1
    for name in order:
        entries=[c for c in page['calls'] if c['name']==name]
        need(len(entries)==1 and entries[0]['startedAt']>=previous,'setup call order differs')
        previous=entries[0]['finishedAt']
    for name,action in moves:
        _,request,_=call_binding(page,name,'editorActionV2',requests,replies)
        need(request['message']['payload']['action']==action and request['message']['payload']['extendSelection'] is False,
             'setup public key sequence differs')
    for phase in ('start','target','final'):
        bound_state(page,prefix+'-'+phase+'-state',setup[phase],requests,replies)
    def point(state):
        c=state['caret'];return c['x'],c['y']+c['height']//2
    if text_start:
        need(not any(c['name']==prefix+'-home' for c in page['calls']),'unplanned Home at text-start anchor')
        need((setup['start']['caret']['x'],setup['start']['caret']['y'])==(coordinates[0],coordinates[1]),
             'list anchor is not actual search text start')
        need(setup['start']['selection']['collapsed'] is True,'list text-start is not collapsed')
    a,b=point(setup['start']),point(setup['target'])
    _,selection,_=call_binding(page,prefix+'-prefix-select','editorSelectRangeV2',requests,replies)
    payload=selection['message']['payload']
    need((payload['startXTwips'],payload['startYTwips'],payload['endXTwips'],payload['endYTwips'])==(*a,*b),
         'prefix selected different points')
    _,_,selected=call_binding(page,prefix+'-prefix-text','getSelection',requests,replies)
    need(setup['selected']==selected['message']['result'],'setup text is not actual selection')
    _,restored,_=call_binding(page,prefix+'-restore-point','click',requests,replies)
    need((restored['message']['payload']['xTwips'],restored['message']['payload']['yTwips'])==b,
         'setup restoration uses different point')
    need(setup['final']['caret']==setup['target']['caret'],'setup caret not restored')


def mutation_closure(page,requests,plan):
    # Product paints/observers may run automatically; state-changing operations
    # must belong to the fixed setup, readiness key or measured Shift calls.
    mutations={'click','editorSelectRangeV2','editorActionV2','insertText'}
    passive={'init','open','close','paint','search','getSelection','editorGetStateV2','save'}
    allowed={'measured-shift'}
    for prefix,discovery in [('readiness',{'offset':0}),('measured',plan['cases'][page['caseId']]['discovery'])]:
        allowed.update(prefix+'-'+suffix for suffix in ('search-click','prefix-select','restore-point'))
        if discovery.get('anchor')!='search-text-start':allowed.add(prefix+'-home')
        if isinstance(discovery['offset'],int):allowed.update(prefix+'-right-'+str(i) for i in range(discovery['offset']))
        else:
            allowed.add(prefix+'-end')
            if discovery['offset']=='next-empty':allowed.add(prefix+'-next-empty')
    for request in requests.values():
        operation=request['message']['operation']
        need(operation in mutations|passive,'unplanned public operation '+operation)
        if operation=='insertText':continue  # Bound uniquely by readiness; forbidden in the measured generation below.
        if operation in mutations:
            calls=[c for c in page['calls'] if c['generation']==request['generation'] and
                   c['startedAt']<=request['at']<=c['finishedAt']]
            need(len(calls)==1,'mutation outside a declared call')
            name=calls[0]['name'];payload=request['message']['payload']
            need(name in allowed,'undeclared setup/measurement mutation')
            if operation=='editorActionV2':
                if name=='measured-shift':continue
                need(re.fullmatch(r'(readiness|measured)-(home|end|next-empty|right-\d+)',name) is not None,
                     'unplanned setup action')
                need(payload['extendSelection'] is False and payload['action'] in
                     ('move-line-home','move-line-end','move-character-right'),'unplanned state-changing action')
            elif operation=='click':need(name.endswith(('-search-click','-restore-point')),'unplanned click')
            else:need(name.endswith('-prefix-select'),'unplanned range selection')

def readiness(page,plan,browser):
    requests,replies=binding(page,plan,browser)
    ready=page.get('readiness',{})
    handle,gen=opened(page,ready['open'],plan,requests,replies)
    validate_setup(page,'readiness',ready['setup'],{'query':plan['fixtureParagraphs'][0],'paragraph':0,'offset':0},requests,replies)
    mutation_closure(page,requests,plan)
    bound_state(page,'readiness-before-state',ready['beforeState'],requests,replies)
    bound_state(page,'readiness-after-state',ready['afterState'],requests,replies)
    original=bound_save(page,'readiness-before-save',ready['beforeSave'],requests,replies)
    after=bound_save(page,'readiness-after-save',ready['afterSave'],requests,replies)
    need(original==plan['fixtureParagraphs'],'readiness loaded document differs')
    expected=original.copy();expected[0]='Z'+expected[0]
    need(after==expected,'actual readiness edit absent/wrong saved insertion')
    sink=ready['beforeInput']
    need(sink.get('id')=='sink' and sink.get('active') is True and sink.get('connected') is True
         and sink.get('disabled') is False and sink.get('readOnly') is False
         and sink.get('documentHandle')==handle and sink.get('generation')==gen,'readiness product sink unavailable')
    inputs=[e for e in page['inputs'] if e['type']=='beforeinput' and e.get('inputType')=='insertText'
            and e.get('data')=='Z' and e.get('isTrusted') is True and e['sink']==sink]
    keys=[e for e in page['inputs'] if e['type']=='keydown' and e.get('key')=='Z' and e.get('isTrusted') is True]
    need(len(inputs)==1 and len(keys)==1,'actual browser readiness key/beforeinput absent')
    mutations=[(key,r) for key,r in requests.items() if r['generation']==gen and r['message']['operation']=='insertText']
    need(len(mutations)==1 and sum(r['message']['operation']=='insertText' for r in requests.values())==1,
         'readiness mutation missing/nonunique or extra-generation mutation')
    key,req=mutations[0];reply=replies.get(key)
    need(req['message']['payload']=={'documentHandle':handle,'text':'Z'},'wrong readiness mutation')
    need(reply is not None and reply['message'].get('ok') is True,'readiness mutation refused')
    need(inputs[0]['at']<=req['at']<=reply['at'],'readiness input/wire order differs')
    need(ready['afterState']['revision']>ready['beforeState']['revision'],'readiness revision did not advance')
    return requests,replies

def s2_compare(reply,readback,active):
    """Reusable S2 semantic comparison; capture full states outside this projection."""
    need(reply.get('changed') is False and reply.get('revision')==reply.get('beforeRevision'),
         'move changed document/revision')
    need(isinstance(reply.get('state'),dict) and isinstance(readback,dict),'move/state absent')
    need(active.get('selectionType') in ('none','text','complex'),'active selection type unavailable')
    stale_fields=[key for key in ('caret','selection') if reply['state'].get(key)!=readback.get(key)]
    collapsed=reply['state'].get('selection',{}).get('collapsed')
    need(type(collapsed) is bool,'reply collapsed status absent')
    if collapsed != (active['selectionType']=='none'): stale_fields.append('active-selection-type')
    return stale_fields

def inspect(page,plan,browser):
    try:
        requests,replies=readiness(page,plan,browser)
        need(page.get('complete'),'incomplete measured page')
        measured=page['measured'];old=page['readiness']['open']
        handle,gen=opened(page,measured['open'],plan,requests,replies)
        need(gen!=old['generation'] and measured['open']['serial']>old['serial'],'fresh original document absent')
        need({w['generation'] for w in page['workers']}=={old['generation'],gen} and len(page['workers'])==2,
             'unexpected worker/recovery generation')
        need(sum(r['message']['operation']=='open' for r in requests.values())==2,'extra/missing document open')
        need(bound_save(page,'measured-original-save',measured['originalSave'],requests,replies)==plan['fixtureParagraphs'],
             'measured original fixture contains readiness edit/drift')
        expected=plan['cases'][page['caseId']]
        setup=measured['setup'];validate_setup(page,'measured',setup,expected['discovery'],requests,replies)
        need(not any(r['generation']==gen and r['message']['operation']=='insertText' for r in requests.values()),
             'unplanned measured text mutation')
        prefix=setup['selected'].get('text','');discovery=expected['discovery'];offset=discovery['offset']
        want=discovery['query'][:offset] if isinstance(offset,int) else discovery['query']+'\n' if offset=='next-empty' else discovery['query']
        if offset=='visual-end': need(bool(prefix) and discovery['query'].startswith(prefix),'wrapped prefix is not fixture text')
        else: need(prefix==want,'actual setup text differs from logical point')
        need(setup['final']['caret']==setup['target']['caret'],'setup did not restore actual measured point')
        need(measured['before']['selection']['collapsed'] is True,'pre-red origin is not caret')
        before_req,before_res=bound_state(page,'measured-before-state',measured['before'],requests,replies)
        final_call=next(c for c in page['calls'] if c['name']=='measured-final-state')
        need(before_req['at']>=final_call['finishedAt'],'before state precedes setup')
        call,req,res=call_binding(page,'measured-shift','editorActionV2',requests,replies)
        need(req['at']>=before_res['at'],'Shift precedes precondition state')
        need(req['message']['payload']['action']==expected['action'] and req['message']['payload']['extendSelection'] is True,
             'actual public Shift dispatch absent/wrong')
        need(req['generation']==gen and req['message']['payload']['documentHandle']==handle,'measured dispatch stale document')
        need(call['result']==measured['reply']==res['message']['result'],'move reply not bound to terminal')
        need(measured['reply'].get('action')==expected['action'],'reply action differs')
        need(measured['reply']['beforeRevision']==measured['before']['revision'],'move precondition revision differs')
        readreq,readres=bound_state(page,'measured-readback',measured['readback'],requests,replies)
        need(readreq['at']-res['at']>=500,'engine readback was too early')
        need(measured['readback']['revision']==measured['reply']['revision'],'delayed revision differs')
        _,active_req,active_res=call_binding(page,'measured-active-selection','getSelection',requests,replies)
        need(measured['activeSelection']==active_res['message']['result'],'active selection not wire result')
        need(active_req['at']>=readres['at'],'active selection precedes delayed state')
        _,_,closed=call_binding(page,'measured-close','close',requests,replies)
        stale=s2_compare(measured['reply'],measured['readback'],measured['activeSelection'])
        late=[e for e in page['events'] if e['generation']==gen and readres['at']<e['at']<=closed['at']
              and e['message'].get('event') in ('editor-state','document-invalidated')]
        return {'verdict':'EXPECTED_RED' if stale else 'UNEXPECTED_GREEN','staleFields':stale,
                'terminalCount':1,'readbackDelayMs':readreq['at']-res['at'],'lateCursorObservations':late}
    except (NotEstablished,KeyError,ValueError,TypeError,zipfile.BadZipFile) as error:
        return {'verdict':'NOT_ESTABLISHED','reason':str(error)}

def judge(cells,plan):
    wanted={(b,c) for b in BROWSERS for c in plan['cases']};seen=set();hashes=set();rows=[]
    for cell in cells:
        key=(cell['browser'],cell['caseId']);page=cell.get('page') or {}
        ph=digest(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
        if key in seen or ph in hashes:
            rows.append({'cell':key,'verdict':'NOT_ESTABLISHED','reason':'duplicate cell/actual page'});continue
        seen.add(key);hashes.add(ph)
        value=inspect(page,plan,cell['browser']) if not cell.get('fatal') and page.get('caseId')==cell['caseId'] else {'verdict':'NOT_ESTABLISHED','reason':cell.get('fatal') or 'actual case label differs'}
        rows.append({'cell':key,**value})
    verdict='EXPECTED_RED' if seen==wanted and len(rows)==len(wanted) and all(r['verdict']=='EXPECTED_RED' for r in rows) else 'UNEXPECTED_GREEN' if any(r['verdict']=='UNEXPECTED_GREEN' for r in rows) else 'NOT_ESTABLISHED'
    return {'verdict':verdict,'populationComplete':seen==wanted and len(rows)==len(wanted),'cells':len(rows),'results':rows,
            'featureS1S5Acceptance':'NOT_ESTABLISHED: this instrument implements v19 S2 pre-red only'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path)
    parser.add_argument('--v19-wasm-sha256',required=True);args=parser.parse_args()
    report=json.loads(args.report.read_text());actual=config(args.v19_wasm_sha256)
    need(report['config']==actual,'actual pinned graph/config differs')
    need(report.get('postConfig')==actual,'post-run identity absent/different')
    need(not report.get('preparationOnly'),'filtered preparations do not satisfy full pre-red')
    verify_mirror(args.report.parent/'mirror',actual)
    cells=[]
    for record in report['runs']:
        raw=(args.report.parent/record['path']).read_bytes();need(digest(raw)==record['sha256'],'cell bytes changed');cells.append(json.loads(raw))
    result=judge(cells,actual);print(json.dumps(result,indent=2));return 0 if result['verdict']=='EXPECTED_RED' else 1
if __name__=='__main__':raise SystemExit(main())

FILE wasm_sdk_probe/tests/test_v23_feature_pre_red.py
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
