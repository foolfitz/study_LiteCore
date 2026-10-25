#!/usr/bin/env python3
"""Uncounted C2 records using the unchanged real-key/fresh-paint probes.

One invocation is one of eight profile/browser/cadence preparation slots.
No historical performance thresholds are imported. Never edits dist or the SDK.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import time
import traceback

TOOLS=Path(__file__).resolve().parent
PROJECT=TOOLS.parent
sys.path.insert(0,str(TOOLS))
import probe_typing_latency as probe
import run_e2_c_product_path as pp
import v21_shakedown_common as common
from build_e2_c_shell_bundle import imports_of

DIST=PROJECT/'dist'
OWNER=PROJECT/'build/scratch-m3-production-ui/PMPC指南.odt'
OWNER_SHA='7b336879547df057ae6d38e907f221b40c90c37cd65d2df5afceceb91941657e'
PINS={
 'e2-editor-v22':{'probe.wasm':'f7a40bcce073d913e562245b96f32a1051766dda23da0da3911741f03934d49e',
                 'sdk-manifest.json':'000921c176b57174cc1680825c73f878564b3a216e6849dd0d50c8078a9516d5',
                 'probe.js':'dc4c2c84657e350668fbfc0048e2ded9c49ca5076610a6389944cf71ea4ba9af',
                 'sdk-worker.js':'0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350'},
 'e2-editor-v23-diag-r2':{'probe.wasm':'683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078',
                 'sdk-manifest.json':'716620972050c5d55485cb99564102cfe0e749af81457180f7f7a265701709da',
                 'probe.js':'f0c77adde7313ece193f16b3a97ea6d539492d282ad787b4f2cdb260c7229fd3',
                 'sdk-worker.js':'c8a3de873c3fbd61b20cc3404eb582433f0c8b1db2e52be374671c3b8851de50'},
}
FILES=('sdk-manifest.json','probe.wasm','probe.js','sdk-worker.js')
OLD='./profiles/e2-editor-v22/sdk-worker.js'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def patched_page(raw,profile):
    if profile not in PINS:raise ValueError('unknown comparison profile')
    old=('workerUrl: "'+OLD+'"').encode()
    if raw.count(old)!=1:raise ValueError('source must have exactly one reviewed v22 workerUrl')
    new=('workerUrl: "./profiles/'+profile+'/sdk-worker.js"').encode()
    result=raw.replace(old,new)
    if result.replace(new,old)!=raw:raise ValueError('patch changed more than the worker URL')
    return result,{'before':old.decode(),'after':new.decode(),'occurrences':1,
                   'changed':profile!='e2-editor-v22'}


def served_graph(root):
    """Hash the actual local import graph served from the copied product page."""
    pending=['e2-editor-app.js'];found={'e2-editor.html':sha(root/'e2-editor.html')}
    while pending:
        name=pending.pop()
        if name in found:continue
        path=root/name
        if not path.is_file():raise ValueError(f'missing served import: {name}')
        found[name]=sha(path)
        for target in imports_of(path.read_text()):
            if target.startswith('.'):
                relative=os.path.normpath(str(Path(name).parent/target))
                if relative.startswith('../'):raise ValueError('served import escapes mirror')
                pending.append(relative)
    return found


def probe_source_graph():
    pending=[Path(__file__),TOOLS/'probe_typing_latency.py',TOOLS/'probe_typing_latency_view.py',
             TOOLS/'build_e2_c_shell_bundle.py'];found={}
    while pending:
        path=pending.pop()
        key=str(path.relative_to(PROJECT))
        if key in found:continue
        found[key]=sha(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else (
                  [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                target=TOOLS/Path(*name.split('.')).with_suffix('.py')
                if target.is_file():pending.append(target)
    return found


def browser_observation_problems(observed,browser,artifacts):
    ua=observed.get('userAgent','')
    family=('Firefox/' in ua) if browser=='firefox' else ('Chrome/' in ua and 'Firefox/' not in ua)
    problems=[]
    if not family:problems.append('observed userAgent does not match browser')
    if observed.get('geometry')!={'width':1400,'height':1000,'dpr':2}:problems.append('actual geometry differs')
    if observed.get('artifacts')!=artifacts:problems.append('browser-fetched candidate differs')
    return problems


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',choices=PINS,required=True)
    p.add_argument('--browser',choices=('chrome','firefox'),required=True)
    p.add_argument('--gap',type=int,choices=(80,200),required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prepare-only',action='store_true',help='create and bind mirror without any browser/server')
    a=p.parse_args();chars=20 if a.gap==80 else 10
    if sha(OWNER)!=OWNER_SHA:raise ValueError('PMPC authority fixture differs')
    artifacts={name:sha(DIST/'profiles'/a.profile/name) for name in FILES}
    if any(artifacts[k]!=v for k,v in PINS[a.profile].items()):raise ValueError('frozen comparison identity differs')
    manifest=json.loads((DIST/'profiles'/a.profile/'sdk-manifest.json').read_text())
    if manifest.get('profile')!=a.profile:raise ValueError('manifest profile differs')
    a.output.mkdir(parents=True,exist_ok=False);out=a.output.resolve();mirror=out/'input-mirror'
    raw=(DIST/'e2-editor-app.js').read_bytes();patched,patch=patched_page(raw,a.profile)
    pp.build_mirror(DIST,mirror,{'e2-editor-app.js':patched})
    graph=served_graph(mirror)
    # Keep originals and the materialized override reviewable without any dist writes.
    (out/'original-e2-editor-app.js').write_bytes(raw)
    record={'schema':1,'scope':'uncounted C2 preparation record only','profile':a.profile,'browser':a.browser,
       'gapMs':a.gap,'chars':chars,'requestedGeometry':{'width':1400,'height':1000,'dpr':2},
       'fixture':{'path':str(OWNER),'sha256':OWNER_SHA,'bytes':OWNER.stat().st_size},'artifacts':artifacts,
       'patch':patch,'sourcePageSha256':hashlib.sha256(raw).hexdigest(),'servedSourceGraph':graph,
       'probeSources':probe_source_graph(),'status':'NOT_ESTABLISHED'}
    def write(): (out/'binding.json').write_text(json.dumps(record,indent=2)+'\n')
    if a.prepare_only:record['preparationOnly']=True;write();return 0
    native_nav,native_mirror=pp.navigate,pp.build_mirror
    owned_sessions=[];executed_roots=[];owned_servers=[]
    native_popen=probe.subprocess.Popen
    def capture_server(command,*args,**kwargs):
        child=native_popen(command,*args,**kwargs)
        if isinstance(command,(list,tuple)) and len(command)>1 and command[1]==str(PROJECT/'web/serve.py'):
            owned_servers.append(child)
        return child
    def capture_mirror(source,target,overrides):
        native_mirror(source,target,overrides);executed_roots.append(Path(target))
        actual=served_graph(Path(target))
        expected={**graph,'e2-editor.html':hashlib.sha256((
          (mirror/'e2-editor.html').read_text().replace('<script type="module" src="./e2-editor-app.js"></script>',
          probe.PAINT_SHIM+'<script type="module" src="./e2-editor-app.js"></script>')).encode()).hexdigest()}
        if actual!=expected:raise ValueError('executed graph differs from unchanged probe paint-shim composition')
        record['executedGraph']=actual
    def navigate_and_bind(session,*args,**kwargs):
        owned_sessions.append(session)
        result=native_nav(session,*args,**kwargs)
        prefix='./profiles/'+a.profile+'/'
        script="""(() => {
          globalThis.__v23C2Identity = null;
          (async () => {
            const hashes = {};
            for (const name of NAMES) {
              const response = await fetch(PREFIX + name, {cache:'no-store'});
              if (!response.ok) throw new Error(name + ':' + response.status);
              hashes[name] = [...new Uint8Array(await crypto.subtle.digest('SHA-256', await response.arrayBuffer()))]
                .map(x => x.toString(16).padStart(2,'0')).join('');
            }
            globalThis.__v23C2Identity = {artifacts:hashes,userAgent:navigator.userAgent,
              geometry:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio}};
          })().catch(e => {globalThis.__v23C2Identity={error:String(e)}});
          return true;
        })()""".replace('NAMES',json.dumps(FILES)).replace('PREFIX',json.dumps(prefix))
        pp.evaluate(session,script)
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            observed=pp.evaluate(session,'globalThis.__v23C2Identity')
            if observed:break
            time.sleep(.1)
        else:raise RuntimeError('profile fetch identity did not complete before measurement')
        record['browserObserved']=observed
        problems=browser_observation_problems(observed,a.browser,artifacts)
        if problems:raise ValueError('; '.join(problems))
        return result
    old_dist=probe.DIST;old_argv=sys.argv[:]
    try:
        with common.browser_lock('record_v23_c2'):
            record['preRun']=common.pre_run_checks();record['foreignCpu']=common.foreign_cpu()
            if not record['foreignCpu'].get('ok'):raise RuntimeError('foreign CPU load; no browser started')
            probe.DIST=mirror;pp.navigate=navigate_and_bind;pp.build_mirror=capture_mirror;probe.subprocess.Popen=capture_server
            sys.argv=[str(TOOLS/'probe_typing_latency_view.py'),'--dpr','2','--window','1400x1000',
              '--browser',a.browser,'--document','owner','--gap',str(a.gap),'--chars',str(chars),'--out',str(out/'probe.json')]
            try:runpy.run_path(str(TOOLS/'probe_typing_latency_view.py'),run_name='__main__')
            except SystemExit as e:
                if e.code not in (None,0):raise
            if probe_source_graph()!=record['probeSources'] or served_graph(mirror)!=graph:
                raise ValueError('instrument/source changed during observation')
            report=json.loads((out/'probe.json').read_text())
            rows=report.get('rows',[])
            record['status']='RECORDED' if len(rows)==chars and all(x.get('revisionMs') is not None and x.get('onScreenMs') is not None for x in rows) else 'NOT_ESTABLISHED'
            record['summary']=report.get('summary');record['performanceGateApplied']=False
    except Exception:
        record['error']=traceback.format_exc()
    finally:
        pp.navigate=native_nav;pp.build_mirror=native_mirror;probe.DIST=old_dist;sys.argv=old_argv;probe.subprocess.Popen=native_popen
        record['cleanup']=[common.close_browser(s) for s in owned_sessions]
        for server in owned_servers:
            if server.poll() is None:
                server.terminate()
                try:server.wait(timeout=10)
                except probe.subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
        for i,root in enumerate(executed_roots):
            # Archive symlinks plus the original probe's materialized HTML/fixture.
            if root.exists():
                shutil.copytree(root,out/f'executed-mirror-{i}',symlinks=True)
                shutil.rmtree(root.parent)
        write()
    return 0 if record['status']=='RECORDED' else 1

if __name__=='__main__':raise SystemExit(main())
