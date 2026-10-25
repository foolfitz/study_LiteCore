#!/usr/bin/env python3
"""Red witness for typing immediately after a slow selected-cell hit."""
import time
import run_calc_editor_browser as browser
from r7_support import evaluate, run_in_page
from probe_calc_input_range import insert
from probe_calc_input_range_full import pointer


def exercise(session,out,run):
    browser.select(session,'A1')
    p=evaluate(session,"(async()=>{const c=(await window.__calcEditor.session.document.readCell(1,1)).cell;const r=document.querySelector('#surface').getBoundingClientRect();return{x:r.x+(c.xTwips+c.widthTwips/2)/15,y:r.y+(c.yTwips+c.heightTwips/2)/15};})()")
    run_in_page(session,"(()=>{const d=window.__calcEditor.session.document,f=d.hitCell.bind(d);d.hitCell=async(...a)=>{const r=await f(...a);await new Promise(resolve=>setTimeout(resolve,600));return r;};})();")
    pointer(session,[p,p]);insert(session,'raced input')
    time.sleep(.8);browser.wait(session,'!window.__calcEditor.state.busy')
    state=evaluate(session,'window.__calcEditor.state')
    run['checks'].append({'id':'pending-click-typing','pass':state['cell']['column']==1 and state['cell']['row']==1 and state['draft']=='raced input' and state['editing']=='inline','actual':state})


if __name__=='__main__':
    browser.exercise=exercise
    raise SystemExit(browser.main())
