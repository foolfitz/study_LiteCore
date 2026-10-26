#!/usr/bin/env python3
"""New public feature selection collector; explicit fixed population, no retries."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time
import traceback
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parent))
import v21_shakedown_common as common
import v21_input as inputs
from r7_support import evaluate
from run_browser_probe import ChromeSession
from run_e2_c_page_smoke import navigate
from v23_feature_selection_cases import BROWSERS,config,mirror,verify_mirror,encoded,digest
from judge_v23_feature_selection import Evidence,readiness,inspect,check_pre_red

def export_page(session):
    meta=evaluate(session,"""(async()=>{const pending=window.__featureSelectionPending||[];let n;
      do{n=pending.length;await Promise.all(pending.slice());}while(pending.length!==n);
      const b=new TextEncoder().encode(JSON.stringify(window.__featureSelection));
      window.__featureExport=b;const h=await crypto.subtle.digest('SHA-256',b);
      return {length:b.length,sha256:Array.from(new Uint8Array(h),x=>x.toString(16).padStart(2,'0')).join('')};})()""")
    parts=[]
    for start in range(0,meta['length'],65536):
        end=min(start+65536,meta['length'])
        value=evaluate(session,f"""(()=>{{const b=window.__featureExport.subarray({start},{end});let s='';
          for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s);}})()""")
        part=base64.b64decode(value,validate=True)
        if len(part)!=end-start:raise ValueError('snapshot chunk truncated')
        parts.append(part)
    raw=b''.join(parts)
    if len(raw)!=meta['length'] or digest(raw)!=meta['sha256']:raise ValueError('snapshot hash/length mismatch')
    value=json.loads(raw.decode('utf-8'));evaluate(session,'delete window.__featureExport')
    return value,meta


def wait_page(session,predicate):
    # Existing instrumentation observation bound; not a new product timeout.
    until=time.monotonic()+480
    while time.monotonic()<until:
        fatal=evaluate(session,'window.__featureSelection?.fatal || null')
        if fatal:raise RuntimeError(json.dumps(fatal))
        if evaluate(session,predicate):return
        time.sleep(.25)
    raise RuntimeError('outer observation bound; no product retry')


def actual_Z(session):
    if isinstance(session,ChromeSession):
        session.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Z','code':'KeyZ',
                     'text':'Z','unmodifiedText':'Z','windowsVirtualKeyCode':90,'nativeVirtualKeyCode':90})
        session.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'Z','code':'KeyZ',
                     'windowsVirtualKeyCode':90,'nativeVirtualKeyCode':90})
    else:
        session.command('POST','/actions',{'actions':[{'type':'key','id':'readiness-keyboard','actions':[
            {'type':'keyDown','value':'Z'},{'type':'keyUp','value':'Z'}]}]})



def control(session,expression):
    value=evaluate(session,'window.__selectionControl.'+expression)
    if value is False:raise ValueError('instrument stopped; preserve raw page')
    return value

def fresh(session,target):
    serial=evaluate(session,'window.__featureSelection.currentOpen.serial')
    evaluate(session,"document.querySelector('#file').value='';true")
    session.set_file('#file',target/'feature-selection.odt')
    wait_page(session,f"window.__featureSelection?.currentOpen?.serial>{serial} && window.__featureSelection.currentOpen.name==='feature-selection.odt'")

def product_key(session,browser,name,key,shift):
    control(session,'arm('+json.dumps(name)+')')
    inputs.key(session,browser,key,('shift',) if shift else ())
    control(session,'answered()')

def screen_rect(session,setup,last):
    # Existing helper scrolls to the point; compute endpoints from the final
    # observed paper rectangle, then require them to remain visible.
    size=setup['size'];inputs.paper_point(session,evaluate,last['x'],last['y'],last['height'],size)
    rect=evaluate(session,inputs.PAPER_RECT)
    def screen(c):return (round(rect['left']+rect['width']*c['x']/size['w']),
                         round(rect['top']+rect['height']*(c['y']+int(c['height']//2))/size['h']))
    return rect,screen

def drag(session,browser,setup):
    a,b=setup['points'];rect,screen=screen_rect(session,setup,b)
    aa,bb=screen(a),screen(b)
    if not all(rect['deskTop']<=q[1]<=rect['deskBottom'] for q in (aa,bb)):
        raise ValueError('native drag endpoints not both visible; no guessed autoscroll')
    inputs.drag(session,browser,aa,bb)
    # Observe the final actual public drag request/terminal, not a sleep
    # standing in for completion. The outer wait remains containment only.
    wait_page(session,"""(()=>{const p=window.__featureSelection,g=p.currentOpen.generation;
      const up=p.inputs.filter(e=>e.type==='pointerup'&&e.generation===g).at(-1);if(!up)return false;
      const r=up.paper,s=up.size,x=Math.max(0,Math.round((up.clientX-r.left)/r.width*s.w)),y=Math.max(0,Math.round((up.clientY-r.top)/r.height*s.h));
      const q=p.requests.filter(e=>e.generation===g&&e.message.operation==='editorSelectRangeV2'&&e.message.payload.endXTwips===x&&e.message.payload.endYTwips===y).at(-1);
      return q&&p.responses.some(e=>e.generation===g&&e.message.requestId===q.message.requestId);})()""")

def run_interaction(session,browser,row):
    """S4: Shift extension from caret-mid, then the actual public interaction."""
    setup=control(session,'prepareInteraction()')
    product_key(session,browser,'interaction-first-key',row['firstProductKey']['key'],True)
    control(session,'afterFirstKey()');control(session,'markStep()')
    if row['method']=='click':
        rect,screen=screen_rect(session,setup,setup['points'][0]);at=screen(setup['points'][0])
        if not rect['deskTop']<=at[1]<=rect['deskBottom']:raise ValueError('click point not visible; no guessed autoscroll')
        control(session,'armPlace("interaction-step-click")');inputs.click(session,browser,*at);control(session,'answeredPlace()')
    elif row['method']=='drag':drag(session,browser,setup)
    else:control(session,'selectRangeStep()')
    control(session,'afterStep()')
    if row['method']=='click':product_key(session,browser,'interaction-shift-home','Home',True)
    control(session,'finishInteraction()')

def run_arm(session,browser,which,row):
    setup=control(session,'prepare('+json.dumps(which)+')')
    if setup['method']=='drag':drag(session,browser,setup)
    elif setup['method']=='click+Shift+Right x3':
        for n in range(3):product_key(session,browser,'candidate-setup-shift-'+str(n),'ArrowRight',True)
    elif setup['method']=='click+End':product_key(session,browser,'candidate-setup-end','End',False)
    control(session,'before()')
    product_key(session,browser,which+'-move',row['productKey']['key'],row['extendSelection'] if which=='candidate' else False)
    control(session,'finish()')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--preparation-only',action='store_true')
    parser.add_argument('--browser',choices=BROWSERS);parser.add_argument('--case-id',action='append',help='preparation only; repeatable, run in the given order');parser.add_argument('--pre-red-report',type=Path)
    parser.add_argument('--keep-going',action='store_true',help='preparation only: record every listed cell instead of stopping at the first nonpassing one')
    args=parser.parse_args();plan=config()
    if (args.browser or args.case_id or args.keep_going) and not args.preparation_only:parser.error('filters require preparation-only')
    population=list(plan['cases'])+list(plan['interactions'])
    if args.case_id and (set(args.case_id)-set(population) or len(set(args.case_id))!=len(args.case_id)):parser.error('unknown or repeated source case')
    if not args.preparation_only and not args.pre_red_report:parser.error('qualifying collection requires complete historical pre-red')
    prerequisite=check_pre_red(args.pre_red_report) if args.pre_red_report else {'verdict':'NOT_ESTABLISHED'}
    args.output.mkdir(parents=True,exist_ok=False);target=args.output.resolve()/'mirror';mirror(target,plan)
    report={'schema':1,'argv':sys.argv,'cwd':str(Path.cwd()),'config':plan,'preparationOnly':args.preparation_only,
            'preRed':prerequisite,'mirrorBindings':verify_mirror(target,plan),'runs':[]}
    def write():(args.output/'report.json').write_bytes(encoded(report))
    write()
    with common.browser_lock('v23-feature-selection'):
        report['preRun']=common.pre_run_checks();report['foreignCpu']=common.foreign_cpu();write()
        if not report['foreignCpu'].get('ok'):raise SystemExit('foreign CPU refusal; no browser cells')
        with common.served(target) as base:
            for browser in ([args.browser] if args.browser else BROWSERS):
                for case in (args.case_id or population):
                    cell={'browser':browser,'caseId':case};session=None
                    try:
                        if config()!=plan:raise ValueError('source/profile drift')
                        verify_mirror(target,plan);session=common.open_browser(browser)
                        navigate(session,base+'?'+urlencode({'caseId':case}))
                        wait_page(session,"Boolean(window.__featureSelection?.booted && window.__featureSelection?.currentOpen && !document.querySelector('#sink').disabled && !document.querySelector('#sink').readOnly)")
                        control(session,'prepareReadiness()');actual_Z(session);control(session,'finishReadiness()')
                        initial,meta=export_page(session);readiness(Evidence(initial,plan,browser))
                        cell['readinessTransfer']=meta
                        if case in plan['interactions']:fresh(session,target);run_interaction(session,browser,plan['interactions'][case])
                        else:
                            for which in ('reference','candidate'):
                                fresh(session,target);run_arm(session,browser,which,plan['cases'][case])
                        cell['page'],cell['pageTransfer']=export_page(session);cell['inspection']=inspect(cell['page'],plan,browser)
                    except Exception:
                        cell['fatal']=traceback.format_exc()
                        if session is not None:
                            try:cell['page'],cell['pageTransfer']=export_page(session)
                            except Exception:cell['exportFailure']=traceback.format_exc()
                    finally:
                        if session is not None:cell['cleanup']=common.close_browser(session)
                        path=args.output/f'{browser}-{case}.json';path.write_bytes(encoded(cell))
                        report['runs'].append({'path':path.name,'sha256':digest(path.read_bytes())});write()
                    if cell.get('fatal') or cell.get('inspection',{}).get('verdict')!='PASS':
                        report.setdefault('nonpassing',[]).append(cell['caseId']);write()
                        if not args.keep_going:raise SystemExit('first nonpassing observation retained; no retry')
    report['postConfig']=config();verify_mirror(target,plan);write()
    if report['postConfig']!=plan:raise SystemExit('post-run drift')
    return 1 if report.get('nonpassing') else 0
if __name__=='__main__':raise SystemExit(main())
