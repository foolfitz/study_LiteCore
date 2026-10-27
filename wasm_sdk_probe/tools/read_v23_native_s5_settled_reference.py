#!/usr/bin/env python3
"""Certify existing every-member-settled native saves (owner-delegated Astra ruling).

Reads only preserved artifacts. The complete generated native-capable deletion population is
validated before deriving its non-empty-mark, order-dependent partition. No native execution.
"""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import read_v23_native_s5_empty_mark as marks
import read_v23_native_s5 as queued
from v23_s5_comparison import odt_content,s5_compare,s5_reduced,validate_settled_pair
from run_merge_wasm_shakedown import reduce_content

ROOT=marks.ROOT
TOOLS=ROOT/'wasm_sdk_probe/tools'
QUEUED=marks.NATIVE/'run-01'
DEFAULT=marks.NATIVE/'empty-mark-witness-01'
SCHEDULE={'after':'every member','quietMs':800,'capMs':8000}
VERDICT='NATIVE_S5_EVERY_MEMBER_SETTLED_REFERENCES_READ'


def require(ok,message,observed=None):
    if not ok:raise ValueError(message+(' | '+json.dumps(observed,ensure_ascii=False) if observed is not None else ''))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def name(path):
    path=Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
def resolve(path):return Path(path) if Path(path).is_absolute() else ROOT/path
def finite(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def index_records(rows,wanted,label):
    records=[r for r in rows if 'id' in r]
    result={r['id']:r for r in records}
    require(len(result)==len(records) and set(result)==set(wanted),label+' missing/extra/duplicate witness')
    return result


def validate_order(row,expected):
    require(row.get('sequence')==expected['sequence'],'native sequence differs: '+expected['id'],{'actual':row.get('sequence'),'expected':expected['sequence']})
    require(row.get('interMemberSettle')==SCHEDULE,'native inter-member policy differs: '+expected['id'],row.get('interMemberSettle'))
    steps=row.get('steps');posts=row.get('posts')
    require(isinstance(steps,list) and all(isinstance(s,dict) for s in steps) and [s.get('operation') for s in steps]==expected['sequence'],
            'native member operations/count differ: '+expected['id'],steps)
    require(isinstance(posts,list) and all(isinstance(p,dict) for p in posts) and all(type(p.get(k)) is int for p in posts for k in ('type','character','key'))
            and [{k:p[k] for k in ('type','character','key')} for p in posts]==queued.expected_posts(expected),
            'native key posts/count differ: '+expected['id'],posts)
    for field in ('openedSettleMs','setupSettleMs'):
        require(finite(row.get(field)) and row[field]>=0,'native settle missing/capped: '+field,{'actual':row.get(field)})
    last=-1
    for p in posts:
        require(finite(p.get('atMs')) and finite(p.get('returnMs')) and last<=p['atMs']<=p['returnMs'],
                'invalid native post time: '+expected['id'],{'post':p,'previousReturnMs':last})
        last=p['returnMs']
    result=[]
    for i,step in enumerate(steps):
        require(all(finite(step.get(k)) for k in ('settleMs','readStartMs','readEndMs')) and step['settleMs']>=0,
                'native member settle/read missing/capped: '+expected['id'],step)
        following=posts[2*i+2]['atMs'] if i+1<len(steps) else None
        require(posts[2*i+1]['returnMs']<=step['readStartMs']<=step['readEndMs']
                and (following is None or step['readEndMs']<following),
                'native member read not ordered between posts: '+expected['id'],{'step':step,'keyUp':posts[2*i+1],'nextKeyDownMs':following})
        result.append({'operation':step['operation'],'keyUpReturnMs':posts[2*i+1]['returnMs'],
            'readStartMs':step['readStartMs'],'readEndMs':step['readEndMs'],'nextKeyDownMs':following})
    return result


def python_sources():
    """Tool-closed dependency census; pure comparators avoid a consumer-plan/hash cycle."""
    pending=[TOOLS/Path(__file__).name,TOOLS/'read_v23_native_s5_empty_mark.py',TOOLS/'read_v23_native_s5.py']
    found=set()
    while pending:
        path=pending.pop().resolve()
        if path in found:continue
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for module in names:
                child=TOOLS/Path(*module.split('.')).with_suffix('.py')
                if child.is_file():pending.append(child)
    require(found and not any(p.name=='v23_feature_selection_cases.py' for p in found),'native reader depends on its consumer plan')
    return found


def binding_paths(directory,table):
    paths=python_sources()|{ROOT/p for p in table['inputPins']}
    for filename in ('comparison.json','command.json','native.jsonl','cells.txt','fixture.fodt','build/build-receipt.json'):
        paths.add(directory/filename)
    summary=json.loads((directory/'comparison.json').read_bytes())
    paths.update(directory/p for p in summary['artifacts'])
    paths.update(directory/'build/source'/p for p in marks.COMPILED)
    paths.update(TOOLS/p for p in marks.COMPILED)
    command=json.loads((directory/'command.json').read_bytes())
    paths.add(Path(command['argv'][3]));paths.add(Path(command['argv'][4])/'libmergedlo.so')
    identity=json.loads((QUEUED/'identity.json').read_bytes())
    completion=json.loads((QUEUED/'completion.json').read_bytes())
    paths.update(QUEUED/p for p in ('identity.json','completion.json','cases.json','inventory.jsonl','native.jsonl'))
    paths.update(QUEUED/p for p in completion['artifacts'])
    for group in ('sources','libraries','inputPins'):
        paths.update(resolve(p) for p in identity[group])
    paths.add(resolve(identity['binary']['path']));paths.add(resolve(identity['buildReceipt']['path']))
    receipt=json.loads(resolve(identity['buildReceipt']['path']).read_bytes())
    paths.update(ROOT/p for p in receipt['headers'])
    return {Path(p).resolve() for p in paths}


def verify_bindings(bindings,paths):
    require(isinstance(bindings,dict) and set(bindings)=={name(p) for p in paths},'native reference binding population differs')
    for path in paths:
        require(path.is_file() and sha(path)==bindings[name(path)],'native reference input changed: '+name(path))


def checked_save(directory,row,side,artifacts):
    filename=row.get(side+'File','')
    require(isinstance(filename,str) and filename and Path(filename).name==filename and row.get('saved'+side.title()) is True,
            'native own save missing: '+side)
    path=directory/'saves'/filename
    require(path.is_file() and artifacts.get('saves/'+filename)==sha(path),'native own save missing/hash differs: '+side)
    return {'path':name(path),'sha256':sha(path)},path.read_bytes()


def validate_execution(directory,receipt,command):
    binary=directory/'build/v23-native-s5-settled';argv=command.get('argv') or []
    require(len(argv)==9 and argv[:3]==['nice','-n','10'] and argv[3]==str(binary)
            and argv[5:]==[(directory/'profile').as_uri(),(directory/'fixture.fodt').as_uri(),str(directory/'saves'),str(directory/'cells.txt')],
            'native settled invocation differs')
    require(binary.is_file() and sha(binary)==receipt.get('binary'),'native settled binary differs')
    require(command.get('mode')=='default-native-queued' and command.get('interMemberSettle')=='every member, 800 ms quiet / 8000 ms cap',
            'native settled command policy differs')
    require(sha(Path(argv[4])/'libmergedlo.so')==command.get('installSha256',{}).get('libmergedlo.so'),'native settled core differs')


def read(directory):
    directory=Path(directory).resolve();table,expected=marks.population()
    base=marks.read(directory)
    require(base.get('verdict')=='NATIVE_S5_EMPTY_MARK_WITNESS_READ' and base.get('problems')==[],'invalid native empty-mark witness: '+str(base.get('problems')))
    original=queued.read(QUEUED)
    require(original.get('verdict')=='NATIVE_S5_SAVES_AVAILABLE' and original.get('problems')==[],'invalid queued native witness: '+str(original.get('problems')))
    rows=[json.loads(line) for line in (directory/'native.jsonl').read_bytes().splitlines() if line.strip()]
    byid=index_records(rows,expected,'settled');empty=index_records(base['cells'],expected,'empty-mark')
    originals=index_records(original['cells'],[r['id'] for r in table['S5'] if r['referencePolicy']!='settled-wasm'],'queued')
    receipt=json.loads((directory/'build/build-receipt.json').read_bytes())
    command=json.loads((directory/'command.json').read_bytes())
    validate_execution(directory,receipt,command)
    summary=json.loads((directory/'comparison.json').read_bytes());result=[]
    for cid,spec in sorted(expected.items()):
        row=byid[cid];timing=validate_order(row,spec)
        before,before_raw=checked_save(directory,row,'before',summary['artifacts'])
        after,after_raw=checked_save(directory,row,'after',summary['artifacts'])
        old=originals[cid]
        queued_before=resolve(old['saves']['before']['path']).read_bytes()
        queued_after=resolve(old['saves']['after']['path']).read_bytes()
        independent=reduce_content(odt_content(after_raw))==reduce_content(odt_content(queued_after))
        require(type(empty[cid].get('emptyMark')) is bool and empty[cid]['orderIndependent']==independent,'native witness classification differs: '+cid)
        member=empty[cid]['emptyMark'] is False and not independent
        if member:validate_settled_pair(before_raw,after_raw,queued_before)
        reference={'kind':'native-every-member-settled','id':cid,'family':spec['family'],'sequence':spec['sequence'],
            'referencePolicy':spec['referencePolicy'],
            'schedule':dict(SCHEDULE),'saves':{'before':before,'after':after},
            'witness':{'run':directory.name,'raw':{'path':name(directory/'native.jsonl'),'sha256':sha(directory/'native.jsonl')},
                       'id':cid,'memberReads':timing,'setupSaveLifecycle':'source-bound; not independently timestamped'}} if member else None
        result.append({'id':cid,'emptyMark':empty[cid]['emptyMark'],'orderIndependent':independent,'reference':reference})
    paths=binding_paths(directory,table)
    return {'schema':1,'verdict':VERDICT,'problems':[],'witnessDirectory':name(directory),
        'bindings':{name(p):sha(p) for p in sorted(paths)},'cells':result,
        'counts':{'population':len(result),'partition':sum(r['reference'] is not None for r in result)},
        'authority':'findings/evidence/link-batch-v23/feature-protocol/s5-order-oracle-review/RULING.md',
        'scope':'Exact continuation with every member settled; no browser acceptance or schedule-equivalence claim'}


def references(report,table):
    require(type(report.get('schema')) is int and report['schema']==1 and report.get('verdict')==VERDICT and report.get('problems')==[],
            'native settled reference report invalid')
    expected={r['id']:r for r in table['S5'] if r['family']!='type' and r['referencePolicy']!='settled-wasm'}
    cells=index_records(report.get('cells') or [],expected,'settled report')
    verify_bindings(report.get('bindings'),binding_paths(resolve(report['witnessDirectory']),table))
    result={}
    for cid,spec in expected.items():
        cell=cells[cid];reference=cell.get('reference')
        require(type(cell.get('emptyMark')) is bool and type(cell.get('orderIndependent')) is bool,'native settled classification malformed: '+cid)
        member=cell['emptyMark'] is False and cell['orderIndependent'] is False
        require(isinstance(reference,dict) if member else reference is None,'native settled partition/reference differs: '+cid)
        if member:
            require(reference.get('kind')=='native-every-member-settled' and reference.get('id')==cid
                    and reference.get('family')==spec['family'] and reference.get('sequence')==spec['sequence']
                    and reference.get('referencePolicy')==spec['referencePolicy']
                    and reference.get('schedule')==SCHEDULE,'native settled reference identity differs: '+cid)
            result[cid]=reference
    return result


def binding(row):
    """A sealed per-cell certificate can be re-read with its historical plan; no implicit adoption."""
    ref=row.get('nativeEveryMemberSettled')
    require(isinstance(ref,dict),'every-member-settled reference absent')
    require(row.get('emptyMark') is False and row.get('nativeOrderIndependent') is False and row['family']!='type',
            'invalid every-member-settled partition')
    receipt=ref.get('readerReport') or {};p=Path(receipt.get('path',''))
    require(str(p) not in ('','.') and not p.is_absolute() and '..' not in p.parts,'native settled certificate path invalid')
    p=ROOT/p
    require(p.is_file() and sha(p)==receipt.get('sha256'),'native settled certificate missing/hash differs')
    report=json.loads(p.read_bytes())
    require(type(report.get('schema')) is int and report['schema']==1 and report.get('verdict')==VERDICT and report.get('problems')==[],
            'native settled certificate invalid')
    cells=[c for c in report['cells'] if c['id']==row['id']]
    own={k:v for k,v in ref.items() if k!='readerReport'}
    require(len(cells)==1 and cells[0].get('emptyMark') is False and cells[0].get('orderIndependent') is False
            and cells[0].get('reference')==own,'native settled certificate cell differs')
    require(own.get('kind')=='native-every-member-settled' and own.get('id')==row['id']
            and own.get('family')==row['family'] and own.get('sequence')==row['sequence'] and own.get('schedule')==SCHEDULE
            and own.get('referencePolicy')==row['referencePolicy'],
            'native settled certificate sequence/schedule differs')
    return ref


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',nargs='?',type=Path,default=DEFAULT)
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    try:result=read(args.directory)
    except (OSError,ValueError,KeyError,TypeError,IndexError) as error:result={'schema':1,'verdict':'NOT_ESTABLISHED','problems':[str(error)]}
    encoded=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if args.output:
        with args.output.open('x') as out:out.write(encoded)
    print(json.dumps({k:result[k] for k in ('verdict','counts','problems') if k in result}))
    return 0 if result['verdict']==VERDICT else 1


if __name__=='__main__':raise SystemExit(main())
