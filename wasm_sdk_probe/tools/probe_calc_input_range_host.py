#!/usr/bin/env python3
"""Focused Files verification of direct entry, F2, range selection and save."""
import argparse
import json
from pathlib import Path
import tempfile

from run_calc_editor_host import Harness, ODS
from create_calc_range_fixture import create
from probe_calc_input_range import press, insert
from probe_calc_input_range_full import pointer, shortcut
from probe_calc_format_view import INSTRUMENT, SNAPSHOT
from r7_support import evaluate, run_in_page
from probe_m3_gate0_coep import browser_login
from run_calc_editor_browser import select, wait
from v21_shakedown_common import browser_lock, close_browser


class Focused(Harness):
    def admin_round(self,browser):
        run={'browser':browser};self.report['runs'].append(run)
        session=self.browser(browser,'admin');run['version']=session.version
        name=self.folder+'/'+browser+'.ods';self.paths.append(name)
        try:
            self.fixture=create(self.out/'fixture')
            self.check(browser+'/upload',self.dav('PUT',name,self.fixture.read_bytes(),{'Content-Type':ODS})[0] in (200,201,204),name)
            browser_login(session,self.instance.base,self.instance.password)
            run['entry']=self.open_file(session,name,'ods-editor.html');self.ready_calc(session)
            run_in_page(session,INSTRUMENT)
            select(session,'B2');press(session,'F2')
            self.check(browser+'/F2',evaluate(session,"window.__calcEditor.state.editing==='inline' && window.__calcEditor.state.draft==='格式測試'"),evaluate(session,'window.__calcEditor.state.cell'))
            press(session,'Escape');insert(session,'Host replacement '+browser);press(session,'Enter');wait(session,'!window.__calcEditor.state.busy')
            self.check(browser+'/replacement',evaluate(session,'window.__calcEditor.state.cell.input')=='Host replacement '+browser,evaluate(session,'window.__calcEditor.state.cell'))
            press(session,'ArrowRight',True);wait(session,'!window.__calcEditor.state.busy')
            s=evaluate(session,'window.__calcEditor.state');revision=s['revision']
            self.check(browser+'/shift-range',s['selection']['multiple'] and s['cell']['column']==1 and s['selection']['focus']['column']==2,s['selection'])
            for fmt,key in [('bold','b'),('italic','i'),('underline','u')]:
                shortcut(session,key);wait(session,'!window.__calcEditor.state.busy')
                self.check(browser+'/range-refuses/'+fmt,evaluate(session,f"document.querySelector('[data-format={fmt}]').disabled") and evaluate(session,'window.__calcEditor.state.revision')==revision,evaluate(session,'window.__calcEditor.state'))
            press(session,'F2')
            self.check(browser+'/F2-collapses',evaluate(session,"!window.__calcEditor.state.selection.multiple && window.__calcEditor.state.editing==='inline'"),evaluate(session,'window.__calcEditor.state'))
            press(session,'Escape')
            points=evaluate(session,"(async()=>{const s=window.__calcEditor.session.document,r=document.querySelector('#surface').getBoundingClientRect(),a=(await s.readCell(0,0)).cell,b=(await s.readCell(2,1)).cell;return[a,b].map(c=>({x:r.x+(c.xTwips+c.widthTwips/2)/15,y:r.y+(c.yTwips+c.heightTwips/2)/15}));})()")
            pointer(session,points);wait(session,'!window.__calcEditor.state.busy')
            s=evaluate(session,'window.__calcEditor.state')
            self.check(browser+'/mouse-range',s['selection']['column']==0 and s['selection']['row']==0 and s['selection']['endColumn']==2 and s['selection']['endRow']==1,s['selection'])
            select(session,'A1');insert(session,'Host active '+browser);press(session,'Enter');wait(session,'!window.__calcEditor.state.busy')
            snapshot=evaluate(session,SNAPSHOT);file=self.out/(browser+'-input-tiles.json');file.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
            self.check(browser+'/tiles',snapshot['visibleTiles']>0 and bool(snapshot['tiles']) and all(t['matched'] for t in snapshot['tiles']) and snapshot['revision']==snapshot['context']['revision'],{'snapshot':file.name,'tiles':len(snapshot['tiles'])})
            saved=self.save(session,1)
            self.check(browser+'/manual-save',saved['saves'][0]['outcome']=='saved' and saved['saves'][0]['trigger']=='manual' and not evaluate(session,'window.__calcEditor.state.dirty'),saved['saves'])
            code,data,headers=self.dav('GET',name);file=self.out/(browser+'-saved.ods');file.write_bytes(data)
            self.check(browser+'/server-xml',code==200 and self.xml_cell(file,(0,0,0))=='Host active '+browser and self.xml_cell(file,(0,1,1))=='Host replacement '+browser and self.xml_cell(file,(0,0,1))=='鄰格必須保留',{'file':file.name,'status':code})
            release=self.leave(session,name);self.check(browser+'/own-lock-released',release['lock']!='1',release)
        finally:
            try:(self.out/(browser+'-last.png')).write_bytes(session.screenshot())
            except Exception:pass
            run['browserClose']=close_browser(session)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    with browser_lock('calc-input-range-host'),tempfile.TemporaryDirectory(prefix='calc-input-range-host-',dir=Path(__file__).resolve().parents[1]/'build') as scratch:
        raise SystemExit(0 if Focused(a.out.resolve(),Path(scratch),kind='admin').run() else 1)
