#!/usr/bin/env python3
"""Read the empty-mark witness run (fable ruling 4): per deletion cell, Writer's state after its Shift.

Input: a directory written by diag_v23_native_s5_settled.py over all 336 native-capable deletion
cells (every member settled, the state read after each).  A cell is `emptyMark` iff, immediately
after its Shift member, selection type is 0 and both getTextSelection and TEXT_SELECTION are
empty.  Run-level problems (bindings, population, the two consistency checks the ruling names)
make the verdict NOT_ESTABLISHED, and the selection plan then refuses to build.  Per cell, a
settled after-save that differs from run-01's back-to-back after-save is recorded as not
order-independent; the plan carries it and the judge reads that cell NE."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
import v23_feature_s_cases as source
from odt_paragraphs import paragraph_texts_from_xml
from run_merge_wasm_shakedown import reduce_content
from read_v23_native_s5 import expected_posts
ROOT=source.ROOT
TOOLS=ROOT/'wasm_sdk_probe/tools'
NATIVE=ROOT/'findings/evidence/link-batch-v23/feature-protocol/s5-native'
COMPILED=('v23_native_s5_settled.cpp','v23_native_s5_sequence.hpp','link_native_extend_signatures.cpp')
CORE_SHA256='2d49c9ff845d3e2c'  # libmergedlo.so prefix named by ruling 4 condition 1
SINGLE=('backspace','delete','backspace-twice','delete-twice')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def content(path):
    with zipfile.ZipFile(path) as z:return z.read('content.xml')

def population():
    """All native-capable deletion cells, from the generator, never a hand list."""
    table=source.derive(source.read_rounds())
    rows=[r for r in table['S5'] if r['family']!='type' and r['referencePolicy']!='settled-wasm']
    return table,{r['id']:r for r in rows}

def state_after_shift(row):
    seq=row.get('sequence') or []
    shift=[i for i,op in enumerate(seq) if op.startswith('Shift+')]
    steps=row.get('steps') or []
    if len(shift)!=1 or len(steps)!=len(seq):return None
    return steps[shift[0]]

def witness(step):
    """(emptyMark, record) or (None, reason) for a malformed or unsettled Shift-step state."""
    if not isinstance(step,dict) or not isinstance(step.get('state'),dict):return None,'missing Shift-step state'
    if not finite(step.get('settleMs')) or step['settleMs']<0:return None,'Shift-step settle missing or capped'
    kind,state=step.get('selectionType'),step['state']
    text,mark=state.get('getTextSelection'),state.get('TEXT_SELECTION')
    if kind not in (0,1,2,3) or not isinstance(text,str) or not isinstance(mark,str):return None,'malformed Shift-step state'
    empty=text=='' and mark==''
    if (kind==0)!=empty:return None,'selection type and selection text disagree'
    return empty,{'selectionType':kind,'text':text,'TEXT_SELECTION':mark}

def check_cell(row,item,setup,saves,artifacts,fixture):
    issues=[]
    if row.get('sequence')!=item['sequence'] or row.get('family')!=item['family']:issues.append('sequence mismatch')
    if row.get('key')!=setup['key'] or row.get('shape')!=setup['shape']:issues.append('source identity mismatch')
    if row.get('mode')!='default-native-queued':issues.append('wrong native mode')
    posts=row.get('posts') or []
    if [{k:p.get(k) for k in ('type','character','key')} for p in posts]!=expected_posts(item):issues.append('actual FIFO key posts differ')
    previous=-1
    for p in posts:
        if not (finite(p.get('atMs')) and finite(p.get('returnMs'))) or p['atMs']<previous or p['returnMs']<p['atMs']:
            issues.append('invalid actual post ordering');break
        previous=p['returnMs']
    for field in ('openedSettleMs','setupSettleMs'):
        if not finite(row.get(field)) or row[field]<0:issues.append('unestablished settle: '+field)
    if any(not finite(s.get('settleMs')) or s['settleMs']<0 for s in row.get('steps') or [{}]):issues.append('a member settle capped')
    selection=setup['setup']['expectedSelection']
    for which in ('before','beforePost'):
        if (row.get(which) or {}).get('getTextSelection')!=selection:issues.append('wrong pre-key selection: '+which)
    if row.get('beforeSelectionType')!=(1 if setup['setup']['expectRange'] else 0):issues.append('wrong pre-key selection type')
    out={}
    for label in ('before','after'):
        name=row.get(label+'File','')
        path=saves/name
        if not name or Path(name).name!=name or row.get('saved'+label.title()) is not True or not path.is_file():
            issues.append('missing save: '+label);continue
        if artifacts.get('saves/'+name)!=sha(path):issues.append('save not bound: '+label);continue
        out[label]=path
    if 'before' in out and paragraph_texts_from_xml(content(out['before']))!=fixture:issues.append('before save differs from fixture')
    return issues,out

def rounds_disagreements(results,setups):
    """Ruling 4 condition 1: for single and twice families the Shift is the first member, so the
    witness must agree with the arm's three archived rounds (empty in all three = empty mark)."""
    out=[]
    for r in results:
        if r['status']=='WITNESSED' and r['family'] in SINGLE:
            rounds=setups[r['sourceArm']]['nativeAfterSelectionText']
            if r['emptyMark']!=(len(rounds)==3 and all(x=='' for x in rounds)):out.append(r['id']+': witness disagrees with the arm rounds')
    return out

def read(directory):
    table,cells=population();setups={c['id']:c for c in table['cases']};problems=[]
    receipt=json.loads((directory/'build/build-receipt.json').read_text())
    if receipt.get('exitCode')!=0 or receipt.get('sources')!=receipt.get('snapshots') or receipt.get('sources')!={n:sha(TOOLS/n) for n in COMPILED}:
        problems.append('build receipt does not bind the current harness sources')
    for n in COMPILED:
        if sha(directory/'build/source'/n)!=receipt.get('sources',{}).get(n):problems.append('source snapshot differs: '+n)
    if receipt.get('sources',{}).get('link_native_extend_signatures.cpp')!=source.PINS['tool-source-as-run.cpp']:problems.append('retained setup source changed')
    command=json.loads((directory/'command.json').read_text())
    if not str(command.get('installSha256',{}).get('libmergedlo.so','')).startswith(CORE_SHA256):problems.append('native core differs from the ruling')
    if command.get('environment')!={'SAL_USE_VCLPLUGIN':'svp','SAL_LOK_OPTIONS':None,'OC_A11Y':None}:problems.append('native environment differs')
    summary=json.loads((directory/'comparison.json').read_text())
    if summary.get('exitCode')!=0:problems.append('native run failed')
    artifacts=summary.get('artifacts',{})
    for name,value in artifacts.items():
        if Path(name).is_absolute() or '..' in Path(name).parts or not (directory/name).is_file() or sha(directory/name)!=value:
            problems.append('changed native output: '+name)
    if sha(directory/'fixture.fodt')!=table['fixture']['sha256']:problems.append('fixture differs')
    listed=[l for l in (directory/'cells.txt').read_text().splitlines() if l]
    if sorted(listed)!=sorted(cells):problems.append('witness population is not the 336 native-capable deletion cells')
    rows=[json.loads(l) for l in (directory/'native.jsonl').read_text().splitlines() if l.strip()]
    if any(r.get('fatal') for r in rows):problems.append('native discovery/load failure')
    byid={r['id']:r for r in rows if 'id' in r}
    if len([r for r in rows if 'id' in r])!=len(byid) or set(byid)!=set(cells):problems.append('missing/extra/duplicate witness cells')
    old={r['id']:r for r in (json.loads(l) for l in (NATIVE/'run-01/native.jsonl').read_text().splitlines() if l.strip()) if 'id' in r}
    fixture=paragraph_texts_from_xml((directory/'fixture.fodt').read_bytes());results=[]
    for cid in sorted(cells):
        if cid not in byid:continue
        item=cells[cid];row=byid[cid];setup=setups[item['sourceArm']]
        issues,out=check_cell(row,item,setup,directory/'saves',artifacts,fixture)
        empty,record=witness(state_after_shift(row))
        if empty is None:issues.append(record)
        independent=None
        if 'after' in out:
            run01=NATIVE/'run-01/saves'/old[cid]['afterFile']
            independent=reduce_content(content(out['after']))==reduce_content(content(run01))
        results.append({'id':cid,'status':'NOT_ESTABLISHED' if issues else 'WITNESSED','reasons':issues,
            'emptyMark':None if issues else empty,'witness':None if issues else record,
            'orderIndependent':independent,'family':item['family'],'sourceArm':item['sourceArm']})
    problems+=[r['id']+': '+x for r in results for x in r['reasons']]
    problems+=rounds_disagreements(results,setups)
    diag=NATIVE/'diag-settled-01'
    if diag.is_dir():
        prior={x['id']:x for x in (json.loads(l) for l in (diag/'native.jsonl').read_text().splitlines() if l.strip()) if 'id' in x}
        for r in results:
            if r['id'] in prior and r['status']=='WITNESSED':
                was,_=witness(state_after_shift(prior[r['id']]))
                same=paragraph_texts_from_xml(content(diag/'saves'/prior[r['id']]['afterFile']))==paragraph_texts_from_xml(content(directory/'saves'/byid[r['id']]['afterFile']))
                if was!=r['emptyMark'] or not same:problems.append(r['id']+': witness disagrees with diag-settled-01')
    else:problems.append('diag-settled-01 missing')
    witnessed=[r for r in results if r['status']=='WITNESSED']
    return {'schema':1,'verdict':'NOT_ESTABLISHED' if problems else 'NATIVE_S5_EMPTY_MARK_WITNESS_READ',
            'authority':'findings/evidence/link-batch-v23/feature-protocol/s5-silent-shift-deletion-ruling/RULING.md',
            'cells':results,'problems':problems,
            'counts':{'cells':len(results),'emptyMark':sum(r['emptyMark'] is True for r in witnessed),
                      'emptyMarkSingleOrTwice':sum(r['emptyMark'] is True and r['family'] in SINGLE for r in witnessed),
                      'notOrderIndependent':sum(r['orderIndependent'] is False for r in results)},
            'scope':'Membership of the empty-mark route only; not an oracle; no browser claim'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:result=read(a.directory.resolve())
    except (OSError,ValueError,KeyError,TypeError) as error:result={'verdict':'NOT_ESTABLISHED','problems':[str(error)]}
    text=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')
    return int(result['verdict']!='NATIVE_S5_EMPTY_MARK_WITNESS_READ')
if __name__=='__main__':raise SystemExit(main())
