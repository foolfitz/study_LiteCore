#!/usr/bin/env python3
"""Census the settled-reference instrument's guards and demonstrate each control turns red.

Every need/require and direct refusal in the declared decision functions is enumerated by AST.
The new reader and shared comparator modules are swept in full; the two existing consumer
modules have explicit bounded entrypoints. Semantic route/label/aggregate expressions have
additional exact-target mutations. Mutants run only model/reader tests, never browser or LOK.
"""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[5]
TOOLS=ROOT/'wasm_sdk_probe/tools'
TESTS=ROOT/'wasm_sdk_probe/tests'
TARGETS={'read_v23_native_s5_settled_reference.py':None,'v23_s5_comparison.py':None,
         'judge_v23_feature_selection.py':{'native_reference','s5_reference_schema'},
         'v23_feature_selection_cases.py':{'settled_references'}}
TEXT_MUTATIONS=(
 ('judge_v23_feature_selection.py','queued save used for the new native route',
  "reference=settled_binding(row)['saves'] if every_member_settled else row['native']","reference=row['native']"),
 ('judge_v23_feature_selection.py','new schedule label erased',
  "label='native-every-member-settled' if routed else 'native' if native else 'settled-wasm'","label='native' if native else 'settled-wasm'"),
 ('judge_v23_feature_selection.py','Home/End native branch ignores the browser line witness',
  "row['referencePolicy'].startswith('native-if-single-line') and single","row['referencePolicy'].startswith('native-if-single-line') and True"),
 ('judge_v23_feature_selection.py','historical plans implicitly adopt the new schema',
  "version=plan.get('s5NativeReferenceSchema',1)","version=plan.get('s5NativeReferenceSchema',2)"),
 ('judge_v23_feature_selection.py','aggregate route reconciliation omitted',
  "if groups['S5']['verdict']=='PASS' and groups['S5']['nativeSettledEligibleCells']!=groups['S5']['nativeSettledRoutedCells']:","if False:"),
)
HARNESS=r'''
import importlib,json,os,sys,unittest
directory,tools,tests,target=sys.argv[1:]
sys.path[:0]=[directory,tools,tests]
module=importlib.import_module(target)
assert os.path.dirname(os.path.abspath(module.__file__))==os.path.abspath(directory),module.__file__
suite=unittest.TestSuite();load=unittest.defaultTestLoader
for mod,cls in [('test_v23_native_s5_settled_reference','NativeSettledReader'),
                ('test_v23_settled_native_pages','SettledNativePages'),
                ('test_v23_feature_selection','S5ComparatorControls')]:
    suite.addTests(load.loadTestsFromName(cls,importlib.import_module(mod)))
with open(os.devnull,'w') as sink:result=unittest.TextTestRunner(stream=sink,verbosity=0).run(suite)
print(json.dumps({'ran':result.testsRun,'red':sorted({str(x[0]) for x in result.failures+result.errors})}))
'''


def sha(raw):return hashlib.sha256(raw).hexdigest()


def census(sources):
    found=[]
    for filename,functions in TARGETS.items():
        source=sources[filename];raw=source.encode();offsets=[0]
        for line in raw.splitlines(keepends=True):offsets.append(offsets[-1]+len(line))
        count=0
        for function in ast.parse(source).body:
            if not isinstance(function,ast.FunctionDef) or function.name=='require' or (functions is not None and function.name not in functions):continue
            for node in ast.walk(function):
                condition=replacement=message=None
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('need','require') and len(node.args)>=2:
                    condition=node.args[0];replacement='True';message=ast.get_source_segment(source,node.args[1])
                elif isinstance(node,ast.If) and any(isinstance(n,ast.Raise) for n in node.body):
                    condition=node.test;replacement='False';message='direct refusal'
                if condition is None:continue
                start=offsets[condition.lineno-1]+condition.col_offset;end=offsets[condition.end_lineno-1]+condition.end_col_offset
                found.append({'id':f'{filename}:{function.name}:{condition.lineno}', 'module':filename,
                    'kind':'guard-disabled','message':message,'span':[start,end],'original':raw[start:end].decode(),'replacement':replacement})
                count+=1
        if not count:raise ValueError('census empty module: '+filename)
    return found


def run(filename,source):
    compile(source,filename,'exec')
    with tempfile.TemporaryDirectory(prefix='s5-settled-mutant-') as directory:
        (Path(directory)/filename).write_text(source)
        result=subprocess.run([sys.executable,'-I','-c',HARNESS,directory,str(TOOLS),str(TESTS),Path(filename).stem],
                              capture_output=True,text=True,cwd=ROOT)
    if result.returncode or not result.stdout.strip():return {'ran':0,'red':[],'harnessError':result.stderr[-1600:]}
    return json.loads(result.stdout.strip().splitlines()[-1])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=3);args=parser.parse_args()
    sources={n:(TOOLS/n).read_text() for n in TARGETS}
    test_paths=[TESTS/n for n in ('test_v23_native_s5_settled_reference.py','test_v23_settled_native_pages.py','test_v23_feature_selection.py')]
    input_paths=[TOOLS/n for n in TARGETS]+test_paths
    pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in input_paths}
    guards=census(sources);changed=dict(sources)
    changed['read_v23_native_s5_settled_reference.py']+='\ndef invented_guard():\n    require(False,"invented")\n'
    assert len(census(changed))==len(guards)+1,'new check omitted by census'
    empty=dict(sources);empty['read_v23_native_s5_settled_reference.py']=''
    try:census(empty)
    except ValueError:pass
    else:raise AssertionError('empty census reported green')
    baseline=run('read_v23_native_s5_settled_reference.py',sources['read_v23_native_s5_settled_reference.py'])
    report={'schema':1,'scope':'Native settled reference reader/consumer guard controls, not browser evidence',
        'inputs':pins,'baseline':baseline,'selfChecks':{'newCheckEnumerated':True,'emptyModuleRefused':True},'mutations':[]}
    if baseline['red'] or not baseline['ran']:
        report['verdict']='RED_BASELINE'
    else:
        jobs=[]
        for guard in guards:
            raw=sources[guard['module']].encode();start,end=guard['span']
            jobs.append((guard,(raw[:start]+guard['replacement'].encode()+raw[end:]).decode()))
        for filename,label,old,new in TEXT_MUTATIONS:
            if sources[filename].count(old)!=1:raise ValueError('mutation target not unique: '+label)
            jobs.append(({'id':'text:'+label,'module':filename,'kind':'semantic','original':old,'replacement':new},sources[filename].replace(old,new)))
        def exercise(job):
            record,source=job;outcome=run(record['module'],source)
            return {**record,**outcome,'killed':outcome['ran']>0 and bool(outcome['red'])}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for outcome in pool.map(exercise,jobs):
                report['mutations'].append(outcome)
                print(('KILLED ' if outcome['killed'] else 'SURVIVED ')+outcome['id'],file=sys.stderr,flush=True)
        report['survivors']=[r['id'] for r in report['mutations'] if not r['killed']]
        report['counts']={'guards':len(guards),'semantic':len(TEXT_MUTATIONS),'mutations':len(jobs),
                          'killed':sum(r['killed'] for r in report['mutations'])}
        report['verdict']='ALL_KILLED' if not report['survivors'] else 'SURVIVORS'
    report['inputsUnchanged']=all(sha((ROOT/name).read_bytes())==value for name,value in pins.items())
    if not report['inputsUnchanged']:report['verdict']='INPUT_DRIFT'
    with args.out.open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({k:report[k] for k in ('verdict','counts','survivors') if k in report}))
    return 0 if report['verdict']=='ALL_KILLED' else 1


if __name__=='__main__':raise SystemExit(main())
