#!/usr/bin/env python3
"""Public v19 S2 pre-red only: sixteen finite SDK cells in both browsers."""
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
from r7_support import evaluate
from run_browser_probe import ChromeSession
from v23_feature_pre_red_cases import BROWSERS,config,mirror,verify_mirror,encoded,digest
from judge_v23_feature_pre_red import readiness,inspect


def export_page(session):
    meta=evaluate(session,"""(async()=>{const b=new TextEncoder().encode(JSON.stringify(window.__featurePreRed));
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
        fatal=evaluate(session,'window.__featurePreRed?.fatal || null')
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v19-wasm-sha256',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preparation-only',action='store_true');parser.add_argument('--browser',choices=BROWSERS)
    parser.add_argument('--case-id');args=parser.parse_args()
    plan=config(args.v19_wasm_sha256)
    if (args.browser or args.case_id) and not args.preparation_only:parser.error('filters require preparation-only')
    if args.case_id and args.case_id not in plan['cases']:parser.error('unknown source case')
    args.output.mkdir(parents=True,exist_ok=False);target=args.output.resolve()/'mirror';mirror(target,plan)
    report={'schema':1,'argv':sys.argv,'cwd':str(Path.cwd()),'config':plan,'preparationOnly':args.preparation_only,'mirrorBindings':verify_mirror(target,plan),'runs':[]}
    def write(): (args.output/'report.json').write_bytes(encoded(report))
    write()
    with common.browser_lock('v23-feature-pre-red'):
        report['preRun']=common.pre_run_checks();report['foreignCpu']=common.foreign_cpu();write()
        if not report['foreignCpu'].get('ok'):raise SystemExit('foreign CPU refusal; zero browser cells')
        with common.served(target) as base:
            for browser in ([args.browser] if args.browser else BROWSERS):
                for case in ([args.case_id] if args.case_id else plan['cases']):
                    cell={'browser':browser,'caseId':case};session=None
                    print(browser,case,flush=True)
                    try:
                        if config(args.v19_wasm_sha256)!=plan:raise ValueError('source/profile drift')
                        verify_mirror(target,plan)
                        session=common.open_browser(browser)
                        session.navigate(base+'?'+urlencode({'caseId':case}))
                        wait_page(session,"Boolean(window.__featurePreRed?.booted && window.__featurePreRed?.currentOpen && !document.querySelector('#sink').disabled && !document.querySelector('#sink').readOnly)")
                        if evaluate(session,'window.__preRedControl.prepareReadiness()') is not True:raise ValueError('readiness preparation failed')
                        actual_Z(session)
                        if evaluate(session,'window.__preRedControl.finishReadiness()') is not True:raise ValueError('readiness edit/save failed')
                        initial,meta=export_page(session);cell['readinessTransfer']=meta
                        readiness(initial,plan,browser)
                        cell['readinessPage']=initial
                        evaluate(session,"document.querySelector('#file').value='';true")
                        session.set_file('#file',target/'feature-pre-red.odt')
                        wait_page(session,"Boolean(window.__featurePreRed?.currentOpen?.name==='feature-pre-red.odt' && window.__featurePreRed.currentOpen.serial>window.__featurePreRed.readiness.open.serial)")
                        evaluate(session,'window.__preRedControl.measure()')
                        cell['page'],cell['pageTransfer']=export_page(session)
                        cell['inspection']=inspect(cell['page'],plan,browser)
                    except Exception:
                        cell['fatal']=traceback.format_exc()
                        if session is not None:
                            try:cell['page'],cell['pageTransfer']=export_page(session)
                            except Exception:cell['exportFailure']=traceback.format_exc()
                    finally:
                        if session is not None:cell['cleanup']=common.close_browser(session)
                        name=f'{browser}-{case}.json';path=args.output/name;path.write_bytes(encoded(cell))
                        report['runs'].append({'path':name,'sha256':digest(path.read_bytes())});write()
                    if cell.get('fatal') or cell.get('inspection',{}).get('verdict')!='EXPECTED_RED':
                        raise SystemExit('first non-expected-red; evidence retained, no retry')
    report['postConfig']=config(args.v19_wasm_sha256);verify_mirror(target,plan);write()
    if report['postConfig']!=plan:raise SystemExit('post-run source/profile drift')
    return 0
if __name__=='__main__':raise SystemExit(main())
