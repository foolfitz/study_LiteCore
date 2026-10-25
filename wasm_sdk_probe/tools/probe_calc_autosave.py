#!/usr/bin/env python3
"""Finite Calc autosave browser acceptance using a named local host double.

The real page, worker, frozen engine, ODS exporter and trusted typing run intact.
The host double records bytes and deterministic copy/stranded outcomes; it is
not evidence of WebDAV behavior. Clock units cover cap/blocked timing separately.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time

from create_calc_edit_fixture import create
from run_calc_editor_browser import PROJECT,mirror,wait,select,key
from probe_calc_input_range import insert
from run_calc_cell_native import cells_from_xml,NAMES
from r7_support import evaluate,run_in_page,wait_page
from run_browser_probe import free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock,open_browser,close_browser


def exercise(session,out,run):
    def xml_text(cells,address):return '\n'.join(''.join(p.itertext()) for p in cells[address].findall('text:p',{'text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}))
    def check(id,ok,actual=None):
        run['checks'].append({'id':id,'pass':bool(ok),'actual':actual})
        print(('PASS ' if ok else 'FAIL ')+run['browser']+'/'+id,flush=True)
        if not ok:raise AssertionError(id)
    def state():return evaluate(session,'window.__calcEditor.state')
    def auto():return evaluate(session,'window.__autoHost.calls')
    def flush():
        run_in_page(session,'window.__autoFlush=window.__calcEditor.autosave.flush("hidden");')
        wait(session,'!window.__calcEditor.state.busy && !window.__calcEditor.autosave.inFlight')
    def commit(text):
        insert(session,text);key(session,'Enter');wait(session,'!window.__calcEditor.state.busy && !window.__calcEditor.state.editing')
    def bytes_file(label):
        encoded=evaluate(session,'btoa(Array.from(new Uint8Array(window.__autoHost.bytes),v=>String.fromCharCode(v)).join(""))')
        file=out/(run['browser']+'-'+str(run['repeat'])+'-'+label+'.ods');file.write_bytes(base64.b64decode(encoded));return file
    select(session,'B2');flush();check('clean-no-save',len(auto())==0,auto())
    insert(session,'Unconfirmed draft');flush()
    check('draft-never-forced',len(auto())==0 and state()['editing']=='inline' and state()['draft']=='Unconfirmed draft',state())
    check('draft-status-visible','確認後自動儲存' in evaluate(session,'document.querySelector("#autosave-status").textContent'))
    key(session,'Escape')
    marker='Idle '+run['browser']+' '+str(run['repeat']);commit(marker)
    run['idleController']=evaluate(session,'(()=>{const a=window.__calcEditor.autosave;return {allowed:a._allowed(a.snapshot()),snapshot:a.snapshot(),timer:a.timer,now:a.now(),lastActivity:a.lastActivity,firstDirty:a.firstDirty,closed:a.closed};})()')
    time.sleep(1);check('idle-no-early-save',len(auto())==0,auto())
    wait(session,'window.__autoHost.calls.length===1 && !window.__calcEditor.autosave.inFlight',timeout=40)
    calls=auto();elapsed=calls[0]['started']-calls[0]['activity']
    check('production-idle-30s',30000<=elapsed<=35000 and calls[0]['trigger']=='auto',calls)
    check('auto-clears-committed-dirty',not state()['dirty'] and not state()['committedDirty'],state())
    file=bytes_file('idle');_,cells=cells_from_xml(file)
    check('idle-ods-xml',xml_text(cells,(0,1,1))==marker and xml_text(cells,(0,0,1))=='鄰格必須保留',{'file':file.name})
    # Delay native export, then type through the actual textarea during autosave.
    run_in_page(session,'(()=>{const d=window.__calcEditor.session.document,f=d.save.bind(d);d.save=async(...a)=>{await new Promise(r=>setTimeout(r,1500));return f(...a);};})()')
    commit('Hidden checkpoint');run_in_page(session,'window.__autoFlush=window.__calcEditor.autosave.flush("hidden");')
    wait(session,'window.__calcEditor.state.saving');insert(session,'Typed while exporting')
    wait(session,'!window.__calcEditor.autosave.inFlight && !window.__calcEditor.state.busy')
    check('export-keeps-new-draft',state()['draft']=='Typed while exporting' and state()['editing']=='inline' and state()['dirty'],state())
    check('input-focus-survives-export',evaluate(session,'document.activeElement.id')=='cell-editor')
    file=bytes_file('hidden');_,cells=cells_from_xml(file)
    check('hidden-snapshot-excludes-draft',xml_text(cells,(0,1,1))=='Hidden checkpoint' and auto()[-1]['conditions']['reason']=='hidden',{'file':file.name})
    key(session,'Escape')
    # Host failures pause persistently; new edits and timer/hidden triggers do not retry.
    for outcome in ['copy','stranded']:
        run_in_page(session,f'window.__autoHost.mode={json.dumps(outcome)};')
        commit('Outcome '+outcome);flush();count=len(auto())
        check(outcome+'-pauses',bool(evaluate(session,'window.__calcEditor.autosave.state.paused')) and '已暫停' in evaluate(session,'document.querySelector("#autosave-status").textContent'),auto()[-1])
        commit('Retained '+outcome);flush()
        check(outcome+'-no-retry-storm',len(auto())==count and state()['dirty'],{'calls':len(auto()),'state':state()})
        run_in_page(session,'window.__autoHost.mode="saved";document.querySelector("#save-button").click();')
        wait(session,f'window.__autoHost.calls.length==={count+1} && !window.__calcEditor.state.busy')
        check(outcome+'-manual-resumes',not evaluate(session,'window.__calcEditor.autosave.state.paused') and not state()['dirty'] and auto()[-1]['trigger']=='manual',auto()[-1])
    # The mock does not model a sticky copy target; that is existing host behavior.
    commit('Final checkpoint');flush();file=bytes_file('final');_,cells=cells_from_xml(file)
    check('final-xml-and-neighbors',xml_text(cells,(0,1,1))=='Final checkpoint' and xml_text(cells,(0,0,1))=='鄰格必須保留',{'file':file.name})
    run['autosaveEvents']=evaluate(session,'window.__calcEditor.autosave.events')
    run['hostCalls']=auto()
    run['files']=[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.glob(run['browser']+'-'+str(run['repeat'])+'-*.ods')]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--repeats',type=int,default=3);p.add_argument('--browsers',default='chrome,firefox');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);fixture=create(out/'fixture')
    root=mirror(out,PROJECT/'dist/profiles/ods-editor-v1')
    host='''window.__autoHost={calls:[],mode:"saved",bytes:null};window.liteCoreHost={watchUnsaved(check){window.__autoHost.unsaved=check;},async load(){return {bytes:Uint8Array.from(atob(FIXTURE),c=>c.charCodeAt(0)).buffer,name:"autosave.ods"};},async save(bytes,options){const h=window.__autoHost,c={trigger:options.trigger,conditions:options.conditions||null,started:performance.now(),activity:window.__calcEditor.autosave.lastActivity,bytes:bytes.byteLength,outcome:h.mode};h.calls.push(c);h.bytes=bytes;if(h.mode!=="saved")throw Object.assign(new Error("Fixture "+h.mode),{code:"HOST_SAVE_FAILED",outcome:h.mode});return {target:"original",name:"autosave.ods"};}};'''.replace('FIXTURE',json.dumps(base64.b64encode(fixture.read_bytes()).decode()))
    (root/'host-fixture.js').write_text(host)
    page=root/'ods-editor.html';page.write_text(page.read_text().replace('<script type="module"','<script src="./host-fixture.js"></script>\n<script type="module"'))
    report={'schema':1,'host':'deterministic double, not WebDAV','toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runs':[]}
    port=free_port();log=(out/'server.txt').open('w');server=subprocess.Popen(['python3',str(PROJECT/'web/serve.py'),'--port',str(port),'--root',str(root)],stdout=log,stderr=subprocess.STDOUT)
    url=f'http://127.0.0.1:{port}/ods-editor.html?diagnostics=1'
    try:
        wait_page(url)
        with browser_lock('calc-autosave',wait_s=0):
            for browser in a.browsers.split(','):
                for repeat in range(1,a.repeats+1):
                    s=None;run={'browser':browser,'repeat':repeat,'checks':[],'error':None};report['runs'].append(run)
                    try:
                        s=open_browser(browser,(1440,1000));run['version']=s.version;navigate(s,url)
                        wait(s,'Boolean(window.__calcEditor?.autosave && window.__calcEditor.state.cell)')
                        exercise(s,out,run)
                    except Exception as error:
                        run['error']=repr(error)
                        if s:
                            try:
                                run['failureState']=evaluate(s,'window.__calcEditor?.state');run['failureAuto']=evaluate(s,'window.__autoHost.calls')
                                run['failureController']=evaluate(s,'(()=>{const a=window.__calcEditor.autosave;return {allowed:a._allowed(a.snapshot()),snapshot:a.snapshot(),timer:a.timer,now:a.now(),lastActivity:a.lastActivity,firstDirty:a.firstDirty,closed:a.closed,events:a.events};})()')
                            except Exception:pass
                    finally:
                        if s:
                            try:(out/(browser+'-'+str(repeat)+'-last.png')).write_bytes(s.screenshot())
                            except Exception:pass
                            run['cleanup']=close_browser(s)
                        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    finally:server.terminate();server.wait(timeout=10);log.close()
    ok=bool(report['runs']) and all(not r['error'] and r['checks'] and all(c['pass'] for c in r['checks']) for r in report['runs'])
    print(json.dumps({'pass':ok,'runs':[{'browser':r['browser'],'repeat':r['repeat'],'checks':len(r['checks']),'error':r['error']} for r in report['runs']]}));return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
