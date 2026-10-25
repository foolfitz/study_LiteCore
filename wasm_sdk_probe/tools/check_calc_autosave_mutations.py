#!/usr/bin/env python3
"""Prove each autosave guard has a failing executable control; no browser/build."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS={
    'dom-timer-receiver':('setTimer=(fn,delay)=>setTimeout(fn,delay),clearTimer=id=>clearTimeout(id)','setTimer=setTimeout,clearTimer=clearTimeout'),
    'host-required':('s.host===true && s.state===','s.state==='),
    'draft-preserved':('&& s.selectionPending!==true && s.editing==null && s.composing!==true','&& s.selectionPending!==true && s.composing!==true'),
    'single-flight':('this.closed || this.paused || this.inFlight','this.closed || this.paused'),
    'failure-pauses':('this.paused=error.outcome || error.code || "failed";','this.paused=null;'),
    'activity-delays':('activity() {this.lastActivity=this.now();this.update();}','activity() {this.update();}'),
    'closed-no-save':('this.closed || this.paused || this.inFlight','this.paused || this.inFlight'),
}

def main():
    source=(ROOT/'spreadsheet-shell/calc-autosave.js').read_text()
    results=[]
    with tempfile.TemporaryDirectory(prefix='calc-autosave-red-',dir=ROOT/'build') as scratch:
        for name,(old,new) in MUTATIONS.items():
            if old not in source:raise RuntimeError('mutation premise drifted: '+name)
            module=Path(scratch)/(name+'.mjs');module.write_text(source.replace(old,new,1))
            env={**os.environ,'CALC_AUTOSAVE_MODULE':str(module)}
            r=subprocess.run(['node','--test','--test-timeout=2000',str(ROOT/'tests/calc-autosave.test.mjs')],env=env,capture_output=True,text=True,timeout=10)
            failures=[x for x in r.stdout.splitlines() if x.startswith('✖') or x.startswith('not ok ')]
            results.append({'id':name,'rejected':r.returncode!=0 and bool(failures),'failures':failures})
    print(json.dumps({'pass':all(r['rejected'] for r in results),'controls':results},indent=2))
    return 0 if all(r['rejected'] for r in results) else 1

if __name__=='__main__':raise SystemExit(main())
