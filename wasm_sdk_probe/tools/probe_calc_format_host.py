#!/usr/bin/env python3
"""Finding 165 actual Files arm and a real 35 s Calc idle-save observation."""
import argparse
import json
from pathlib import Path
import tempfile
import time

from run_calc_editor_host import Harness, ODS
from probe_calc_format_view import INSTRUMENT, SNAPSHOT
from r7_support import evaluate, run_in_page
from probe_m3_gate0_coep import browser_login
from run_calc_editor_browser import double_click, type_text, key, wait
from v21_shakedown_common import browser_lock, close_browser

class Focused(Harness):
    def admin_round(self,browser):
        run={'browser':browser,'version':None};self.report['runs'].append(run)
        session=self.browser(browser,'admin');run['version']=session.version
        name=self.folder+'/'+browser+'.ods';self.paths.append(name)
        try:
            self.check(browser+'/upload',self.dav('PUT',name,self.fixture.read_bytes(),{'Content-Type':ODS})[0] in (200,201,204),name)
            browser_login(session,self.instance.base,self.instance.password)
            run['entry']=self.open_file(session,name,'ods-editor.html');self.ready_calc(session)
            run_in_page(session,INSTRUMENT)
            from run_calc_editor_browser import select
            select(session,'B2')
            for fmt in ('bold','italic','underline'):
                for mode in ('inline','cell'):
                    if mode=='inline':
                        rect=evaluate(session,'(()=>{const r=document.querySelector("#selection").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()')
                        double_click(session,rect['x'],rect['y']);wait(session,'window.__calcEditor.state.editing === "inline"')
                        evaluate(session,'(()=>{document.querySelector("#cell-editor").select();return true;})()')
                    else:select(session,'B2')
                    session.click(f'[data-format="{fmt}"]');wait(session,'!window.__calcEditor.state.busy')
                    snapshot=evaluate(session,SNAPSHOT)
                    file=self.out/f'{browser}-{fmt}-{mode}.json';file.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+'\n')
                    self.check(browser+'/'+fmt+'/'+mode,snapshot['context']['revision']==snapshot['revision'] and snapshot['visibleTiles']>0 and bool(snapshot['tiles']) and all(t['matched'] for t in snapshot['tiles']) and snapshot['state']['tileErrors']==0,{'snapshot':file.name,'revision':snapshot['revision'],'tiles':len(snapshot['tiles'])})
            # Observe actual product time, not a shortened timer or inferred autosave.
            self.calc_input(session,'A1','Idle observation '+browser)
            before=evaluate(session,'({at:Date.now(),dirty:window.__calcEditor.state.dirty,saves:JSON.parse(document.documentElement.getAttribute("data-litecore")).saves})')
            deadline=time.monotonic()+35
            while time.monotonic()<deadline:time.sleep(.25)
            after=evaluate(session,'({at:Date.now(),dirty:window.__calcEditor.state.dirty,saves:JSON.parse(document.documentElement.getAttribute("data-litecore")).saves})')
            run['idleObservation']={'before':before,'after':after,'scope':'35 real seconds without input, committed edit; not a proof about every future time'}
            self.check(browser+'/current-idle-does-not-autosave',after['at']-before['at']>=35000 and before['saves']==after['saves']==[] and after['dirty'],run['idleObservation'])
            saved=self.save(session,1)
            self.check(browser+'/manual-save-positive',saved['saves'][0]['outcome']=='saved' and saved['saves'][0]['trigger']=='manual' and not evaluate(session,'window.__calcEditor.state.dirty'),saved['saves'])
            code,data,headers=self.dav('GET',name);file=self.out/(browser+'-saved.ods');file.write_bytes(data)
            self.check(browser+'/server-xml',code==200 and self.xml_cell(file,(0,0,0))=='Idle observation '+browser,{'status':code,'file':file.name,'contentType':headers.get('Content-Type')})
            release=self.leave(session,name);self.check(browser+'/own-lock-released',release['lock']!='1',release)
        finally:
            try:(self.out/(browser+'-last.png')).write_bytes(session.screenshot())
            except Exception:pass
            run['browserClose']=close_browser(session)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    with browser_lock('calc-format-host'),tempfile.TemporaryDirectory(prefix='calc-format-host-',dir=Path(__file__).resolve().parents[1]/'build') as scratch:
        # Existing helper's isolated setup/cleanup uses only its owned folder/share/user.
        raise SystemExit(0 if Focused(args.out.resolve(),Path(scratch),kind='admin').run() else 1)
