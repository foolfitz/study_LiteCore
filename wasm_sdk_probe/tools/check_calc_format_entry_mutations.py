#!/usr/bin/env python3
"""Reject each actual format-eligibility predicate and entry/refresh bypass."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"web/ods-editor-app.js"
source=APP.read_text()
body=re.search(r"function formatAvailable\(state\) \{([\s\S]*?)\n\}",source)
assert body,"missing actual eligibility function"
predicate=re.compile(r'!?state(?:\??\.[A-Za-z]\w*)+(?:===(?:"ready"|true))?|!pendingEntry|!dragWork')
terms=list(predicate.finditer(body[1]));assert terms,"empty predicate population"
remaining=predicate.sub("",body[1]).replace("return","")
assert re.fullmatch(r"[\s&|();]*",remaining),"unrecognized eligibility expression"
mutations=[]
for term in terms:
    start=body.start(1)+term.start();end=body.start(1)+term.end()
    mutations.append((term[0],source[:start]+"true"+source[end:]))
for name,before,after in [
    ("entry-bypass","if(!session || !formatAvailable(session.state))return;",""),
    ("toolbar-bypass","node.disabled=!formatAvailable(state);","node.disabled=false;"),
]:
    assert source.count(before)==1,name
    mutations.append((name,source.replace(before,after,1)))
refresh="if(session)renderFormatControls(session.state);"
positions=[m.start() for m in re.finditer(re.escape(refresh),source)]
assert len(positions)==2,"drag refresh population changed"
for index,pos in enumerate(positions):
    mutations.append((f"drag-refresh-{index}",source[:pos]+source[pos+len(refresh):]))
results=[]
with tempfile.TemporaryDirectory(prefix="calc-format-mutants-",dir=ROOT/"build") as scratch:
    for index,(name,mutated) in enumerate(mutations):
        path=Path(scratch)/f"app-{index}.js";path.write_text(mutated)
        run=subprocess.run(["node","--test",str(ROOT/"tests/calc-format-entry.test.mjs")],
            env={**os.environ,"CALC_FORMAT_APP":str(path)},capture_output=True,text=True,timeout=15)
        rejected=run.returncode!=0 and "AssertionError" in run.stdout+run.stderr
        results.append({"id":name,"rejected":rejected})
        assert rejected,f"mutation survived or did not reach assertions: {name}\n{run.stdout}\n{run.stderr}"
print(json.dumps({"pass":True,"sourcePredicates":len(terms),"mutations":results},indent=2))
