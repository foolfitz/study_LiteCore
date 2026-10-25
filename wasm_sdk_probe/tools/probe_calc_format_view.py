#!/usr/bin/env python3
"""Finding 165: compare the actual post-format DOM tiles with direct engine render."""
import base64
import json
from pathlib import Path
import time

import run_calc_editor_browser as browser
from r7_support import evaluate, run_in_page
from run_calc_cell_native import cells_from_xml

INSTRUMENT = '''(() => {
 const v=window.__calcEditor.session.viewer, original=v._onTile;
 window.__formatTiles=new Map();
 v._onTile=entry=>{window.__formatTiles.set(entry.key,entry);original(entry);};
})();'''
SNAPSHOT = '''(async()=>{
 const s=window.__calcEditor.session;
 await s.drain(); await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
 const visible=document.querySelector('#viewport').getBoundingClientRect();
 const result={revision:s.document.revision,context:{...s.scheduler._context},metrics:{...s.scheduler.metrics},
   state:window.__calcEditor.state,tiles:[],visibleTiles:0};
 for(const canvas of document.querySelectorAll('#tiles canvas')) {
  const rect=canvas.getBoundingClientRect(), entry=window.__formatTiles.get(canvas.dataset.key);
  const shown=rect.right>visible.left && rect.left<visible.right && rect.bottom>visible.top && rect.top<visible.bottom;
  if(shown)result.visibleTiles++;
  const row={key:canvas.dataset.key,shown,generation:entry?.generation,matched:false};
  if(entry) {
   const tile=await s.document.render({...entry.region,canvasWidthPx:canvas.width,canvasHeightPx:canvas.height});
   const actual=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data,expected=new Uint8Array(tile.pixels);
   let mismatch=actual.length===expected.length?-1:Math.min(actual.length,expected.length);
   if(mismatch===-1)for(let i=0;i<actual.length;i++)if(actual[i]!==expected[i]){mismatch=i;break;}
   row.matched=mismatch===-1;row.firstMismatch=mismatch;row.bytes=actual.length;
   if(mismatch>=0)row.values=[actual[mismatch],expected[mismatch]];
  }
  result.tiles.push(row);
 }
 return result;
})()'''


def exercise(session,out,run):
    prefix=f"{run['browser']}-r{run['repeat']}"
    def check(id,passed,actual):
        run['checks'].append({'id':id,'pass':bool(passed),'actual':actual})
    browser.select(session,'B2')
    browser.wait(session,'!window.__calcEditor.state.busy')
    evaluate(session,'window.__calcEditor.session.drain()')
    run_in_page(session,INSTRUMENT)
    for format in ('bold','italic','underline'):
        for mode in ('inline','cell'):
            if mode=='inline':
                box=evaluate(session,'(()=>{const r=document.querySelector("#selection").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()')
                browser.double_click(session,box['x'],box['y'])
                browser.wait(session,'window.__calcEditor.state.editing === "inline"')
                evaluate(session,'(()=>{const n=document.querySelector("#cell-editor");n.focus();n.select();return {start:n.selectionStart,end:n.selectionEnd};})()')
            else:
                browser.select(session,'B2')
            before=evaluate(session,'window.__calcEditor.state.cell')
            session.click(f'[data-format="{format}"]')
            browser.wait(session,'!window.__calcEditor.state.busy')
            snapshot=evaluate(session,SNAPSHOT)
            name=f'{prefix}-{format}-{mode}'
            (out/(name+'.json')).write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+'\n')
            (out/(name+'.png')).write_bytes(session.screenshot())
            check(format+'/'+mode+'/model',snapshot['state']['cell'][format] is not before[format] and snapshot['state']['cell']['input']=='格式測試',snapshot['state']['cell'])
            check(format+'/'+mode+'/view',snapshot['context']['revision']==snapshot['revision'] and snapshot['visibleTiles']>0 and all(t['matched'] for t in snapshot['tiles']) and snapshot['state']['tileErrors']==0,
                {'snapshot':name+'.json','revision':snapshot['revision'],'contextRevision':snapshot['context']['revision'],'tiles':len(snapshot['tiles']),'visibleTiles':snapshot['visibleTiles'],'mismatched':sum(not t['matched'] for t in snapshot['tiles'])})
    session.click('#save-button')
    browser.wait(session,'Boolean(window.__calcEditor.lastExport) && !window.__calcEditor.state.saving')
    downloaded=Path(run['downloadDirectory'])/'cell-editing.ods'
    deadline=time.monotonic()+30
    while not downloaded.exists() and time.monotonic()<deadline:time.sleep(.1)
    saved=out/(prefix+'-saved.ods');saved.write_bytes(downloaded.read_bytes())
    check('saved-xml',bool(cells_from_xml(saved)[1]),{'file':saved.name,'bytes':saved.stat().st_size})
    session.set_file('#file-input',saved)
    browser.wait(session,f'window.__calcEditor.state?.fileName === {json.dumps(saved.name)} && Boolean(window.__calcEditor.state.cell)')
    browser.select(session,'B2')
    cell=evaluate(session,'window.__calcEditor.state.cell')
    check('reopened-format',cell['input']=='格式測試' and all(cell[f] is False for f in ('bold','italic','underline')),cell)

if __name__=='__main__':
    browser.exercise=exercise
    raise SystemExit(browser.main())
