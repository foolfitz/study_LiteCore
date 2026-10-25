#!/usr/bin/env python3
"""Adversarial pending-input validation: never turn refusal into an empty write."""
import time
import json
import run_calc_editor_browser as browser
from r7_support import evaluate, run_in_page
from probe_calc_input_range import insert, press
from probe_calc_input_range_full import pointer, shortcut
from run_browser_probe import ChromeSession


def exercise(session,out,run):
    def state():return evaluate(session,'window.__calcEditor.state')
    def check(name,ok,actual):
        run['checks'].append({'id':name,'pass':bool(ok),'actual':actual})
        if not ok:raise RuntimeError(name)
    def point(c,r):return evaluate(session,f"(async()=>{{const c=(await window.__calcEditor.session.document.readCell({c},{r})).cell;const r=document.querySelector('#surface').getBoundingClientRect();return{{x:r.x+(c.xTwips+c.widthTwips/2)/15,y:r.y+(c.yTwips+c.heightTwips/2)/15}};}})()")
    for case in ('oversized','failed-hit','protected'):
        if case=='protected':
            session.click('[data-part="2"]');browser.wait(session,'!window.__calcEditor.state.busy');browser.select(session,'B1');target=point(0,0)
        else:browser.select(session,'A1');target=point(1,1)
        before=state()['revision']
        failure="throw Object.assign(new Error('injected hit refusal'),{code:'CELL_GEOMETRY_UNAVAILABLE'});" if case=='failed-hit' else 'return r;'
        run_in_page(session,"(()=>{const d=window.__calcEditor.session.document;d.__failureHit=d.hitCell;d.hitCell=async(...a)=>{const r=await d.__failureHit(...a);await new Promise(resolve=>setTimeout(resolve,700));"+failure+"};})();")
        pointer(session,[target,target])
        if case=='oversized':
            if isinstance(session,ChromeSession):insert(session,'x'*32768)
            else:run_in_page(session,"(()=>{const n=document.activeElement;n.dispatchEvent(new InputEvent('beforeinput',{bubbles:true,cancelable:true,inputType:'insertFromPaste',data:'x'.repeat(32768)}));n.value='x'.repeat(32768);n.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertFromPaste',data:n.value}));})();")
        else:insert(session,'must stay buffered')
        press(session,'Enter');time.sleep(1.7);browser.wait(session,'!window.__calcEditor.state.busy')
        check(case+'/no-write',state()['revision']==before and not state()['editing'],state())
        shortcut(session,'b');browser.wait(session,'!window.__calcEditor.state.busy')
        evaluate(session,"window.__calcEditor.session.setFormat('italic',true).catch(()=>null)") if False else None
        session.click('#save-button');time.sleep(.3)
        check(case+'/save-refused',state()['revision']==before and evaluate(session,'window.__calcEditor.lastSave') is None,state())
        press(session,'Escape');browser.wait(session,'!window.__calcEditor.state.busy')
        run.setdefault('postCancel',[]).append({'case':case,'input':evaluate(session,"({...window.__calcEditor.inputState(),valueLength:document.querySelector('#cell-editor').value.length,active:document.activeElement.id})")})
        run_in_page(session,"(()=>{const d=window.__calcEditor.session.document;d.hitCell=d.__failureHit;delete d.__failureHit;})();")
    session.click('[data-part="0"]');browser.wait(session,'!window.__calcEditor.state.busy');browser.select(session,'A1')
    press(session,'F2');insert(session,' old draft')
    target=point(1,1)
    run_in_page(session,"(()=>{window.__entryTrace=[];for(const k of ['beforeinput','input','keydown','pointerdown','pointerup','dblclick'])document.addEventListener(k,e=>{const row={event:k,key:e.key,inputType:e.inputType,target:e.target.id,value:document.querySelector('#cell-editor').value,busy:window.__calcEditor.state.busy,pending:window.__calcEditor.state.selectionPending};window.__entryTrace.push(row);queueMicrotask(()=>{row.afterValue=document.querySelector('#cell-editor').value;row.afterDraft=window.__calcEditor.state.draft;row.afterEditing=window.__calcEditor.state.editing;});},true);})();")
    run_in_page(session,"(()=>{const d=window.__calcEditor.session.document;d.__failureHit=d.hitCell;d.hitCell=async(...a)=>{const r=await d.__failureHit(...a);await new Promise(resolve=>setTimeout(resolve,700));return r;};})();")
    pointer(session,[target,target]);insert(session,'new only');time.sleep(1.7);browser.wait(session,'!window.__calcEditor.state.busy')
    (out/(run['browser']+'-pending-trace.json')).write_text(json.dumps(evaluate(session,'window.__entryTrace'),indent=2,ensure_ascii=False)+'\n')
    check('previous-draft-not-in-new-buffer',state()['cell']['column']==1 and state()['draft']=='new only' and state()['editing']=='inline',state())
    press(session,'Escape')


if __name__=='__main__':
    browser.exercise=exercise
    raise SystemExit(browser.main())
