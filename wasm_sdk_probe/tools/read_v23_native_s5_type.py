#!/usr/bin/env python3
"""Read native S5 type-family run 02 (fable ruling 3): saves plus the per-cell order witness.

A cell is native-referenced only with its witness; without one it is NOT_ESTABLISHED with a
recorded reason, and its consumer falls back to the fresh settled-WASM reference (fallback A),
never to native-without-witness.  Run-level binding problems leave every cell unusable.
Availability is not browser parity."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_v23_native_s5 import ROOT,TOOLS,read_inventory,sha
from run_v23_native_s5_type import SOURCES,cases,validate_build_receipt
from read_v23_native_s5 import validate_cell
import v23_feature_s_cases as source
from odt_paragraphs import paragraph_texts_from_xml

def finite(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def round_states(rounds,arm):
    """The three archived native rounds' before/after snapshots for one Shift source arm."""
    found=[[r for r in rows if r.get('kind')=='shift' and r.get('arm')==arm] for rows in rounds]
    if any(len(x)!=1 for x in found):raise ValueError('native round arm missing/duplicated: '+arm)
    return [x[0] for x in found]

def order_witness(row,setup,states):
    """Ruling 3 (ii)/(iii).  Returns (witness, issues); witness is None when issues exist."""
    issues=[]
    texts=setup['nativeAfterSelectionText']
    if not (isinstance(texts,list) and len(texts)==3 and len(set(texts))==1):
        return None,['native rounds disagree on the Shift selection']
    settled=row.get('shiftSettleMs')
    if not finite(settled):issues.append('missing Shift settle')
    elif settled<0:issues.append('Shift settle reached its cap')
    between=row.get('between')
    start,end=row.get('betweenReadStartMs'),row.get('betweenReadEndMs')
    if not isinstance(between,dict) or not isinstance(between.get('getTextSelection'),str) or not finite(start) or not finite(end):
        return None,issues+['missing between-read']
    posts=row.get('posts',[])
    x=[p for p in posts if p.get('type')==0 and p.get('character')==120 and p.get('key')==0]
    shift=[p for p in posts if p.get('character')==0 and isinstance(p.get('key'),int) and p['key']&0x1000]
    if len(x)!=1 or len(shift)!=2 or not all(finite(p.get('atMs')) and finite(p.get('returnMs')) for p in x+shift):
        return None,issues+['Shift/x posts not uniquely recorded']
    if not shift[-1]['returnMs']<=start<=end:issues.append('between-read does not follow the Shift posts')
    if not end<x[0]['atMs']:issues.append('between-read does not complete before the x post')
    if between['getTextSelection']!=texts[0]:issues.append('between-read selection differs from the three native rounds')
    witness='selection-before-x'
    if texts[0]=='':
        # Silent member: only "settled, collapsed, caret at the moving point" is witnessable.
        witness='settle-only'
        if row.get('betweenSelectionType')!=0:issues.append('silent member not collapsed at the between-read')
        befores={s['before'].get('INVALIDATE_VISIBLE_CURSOR') for s in states}
        afters={s['after'].get('INVALIDATE_VISIBLE_CURSOR') for s in states}
        if len(befores)!=1 or len(afters)!=1:issues.append('native rounds disagree on the silent member caret')
        elif row.get('beforePost',{}).get('INVALIDATE_VISIBLE_CURSOR') not in befores:
            issues.append('native round caret not comparable with this run')
        elif between.get('INVALIDATE_VISIBLE_CURSOR') not in afters:
            issues.append('silent member caret not at the moving point')
    return (None if issues else witness),issues

def read(directory):
    table,expected=cases();problems=[];results=[]
    rounds=source.read_rounds()
    identity=json.loads((directory/'identity.json').read_text())
    completion=json.loads((directory/'completion.json').read_text())
    if completion.get('exitCode')!=0 or completion.get('protectedInputsUnchanged') is not True or completion.get('afterIdentity')!=identity:
        problems.append('native run failed or protected inputs changed')
    if json.loads((directory/'cases.json').read_text())!=expected:problems.append('case schedule differs')
    read_inventory((directory/'inventory.jsonl').read_text(),expected)
    for group in ('sources','libraries','inputPins'):
        if not identity.get(group):problems.append('empty input binding: '+group)
        for name,value in identity.get(group,{}).items():
            path=Path(name) if Path(name).is_absolute() else ROOT/name
            if not path.is_file() or sha(path)!=value:problems.append('changed bound input: '+name)
    if identity.get('sources')!={str(p.relative_to(ROOT)):sha(p) for p in SOURCES}:
        problems.append('source closure differs')
    if identity.get('inputPins')!={str(ROOT/p):v for p,v in table['inputPins'].items()}:
        problems.append('historical input bindings differ')
    receipt=identity.get('buildReceipt',{})
    if not receipt.get('path') or not Path(receipt['path']).is_file() or sha(receipt['path'])!=receipt.get('sha256'):
        problems.append('owner build receipt missing or changed')
    else:
        try:
            if validate_build_receipt(Path(identity['binary']['path']),Path(receipt['path']))!=receipt:
                problems.append('owner build receipt binding changed')
        except (OSError,ValueError,KeyError) as error:problems.append('invalid owner build receipt: '+str(error))
    binary=identity.get('binary',{})
    if not binary.get('path') or not Path(binary['path']).is_file() or sha(binary['path'])!=binary.get('sha256'):
        problems.append('owner binary missing or changed')
    artifacts=completion.get('artifacts',{})
    for name,value in artifacts.items():
        path=directory/name
        if Path(name).is_absolute() or '..' in Path(name).parts or not path.is_file() or sha(path)!=value:
            problems.append('changed native output: '+name)
    required={'native.jsonl','native.stderr','identity.json','cases.json','inventory.jsonl','command.json','fixture.fodt'}
    if not required<=artifacts.keys():problems.append('missing output bindings')
    if sha(directory/'fixture.fodt')!=table['fixture']['sha256']:problems.append('fixture differs')
    rows=[json.loads(line) for line in (directory/'native.jsonl').read_text().splitlines() if line.strip()]
    if any(r.get('fatal') for r in rows):problems.append('native discovery/load failure')
    measured=[r for r in rows if 'id' in r]
    byid={r['id']:r for r in measured}
    if len(measured)!=len(expected) or set(byid)!={r['id'] for r in expected}:problems.append('missing/extra/duplicate native cells')
    setups={r['id']:r for r in table['cases']}
    points={p['name']:p.get('rect') for r in rows if r.get('arm','').startswith('discover-') for p in r.get('steps',[])}
    if not points:problems.append('missing actual discovery points')
    fixture=paragraph_texts_from_xml((directory/'fixture.fodt').read_bytes())
    for item in expected:
        if item['id'] not in byid:continue
        actual=byid[item['id']];setup=setups[item['sourceArm']]
        issues,outputs=validate_cell(actual,item,setup,directory/'saves',artifacts)
        if actual.get('expectedCursorRect')!=points.get(actual.get('expectedCursorPoint')):
            issues.append('setup cursor not bound to actual native discovery')
        if 'before' in outputs and outputs['before']['paragraphs']!=fixture:
            issues.append('before save differs from fixture paragraph text')
        witness,why=order_witness(actual,setup,round_states(rounds,item['sourceArm']))
        issues+=why
        results.append({'id':item['id'],'status':'NOT_ESTABLISHED' if issues else 'NATIVE_SAVE_AVAILABLE',
            'orderWitness':None if issues else witness,'reasons':issues,
            'between':{'getTextSelection':(actual.get('between') or {}).get('getTextSelection'),
                       'shiftSettleMs':actual.get('shiftSettleMs'),'readEndMs':actual.get('betweenReadEndMs'),
                       'xPostMs':next((p.get('atMs') for p in actual.get('posts',[]) if p.get('character')==120 and p.get('type')==0),None)},
            'nativeAfterSelectionText':setup['nativeAfterSelectionText'][0],
            'referencePolicy':item['referencePolicy'],'requiresBrowserSingleLineWitness':item['referencePolicy']!='native',
            'browserParity':'NOT_ESTABLISHED_UNPERFORMED','comparison':item['comparison'],'saves':outputs})
    witnessed=[r for r in results if r['status']=='NATIVE_SAVE_AVAILABLE']
    return {'schema':1,'verdict':'NOT_ESTABLISHED' if problems else 'NATIVE_S5_TYPE_SAVES_READ',
            'authority':'findings/evidence/link-batch-v23/feature-protocol/s5-type-oracle-ruling/RULING.md',
            'nativeExecutionsPerCell':1,'cells':results,'problems':problems,
            'counts':{'cells':len(results),'selectionBeforeX':sum(r['orderWitness']=='selection-before-x' for r in witnessed),
                      'settleOnly':sum(r['orderWitness']=='settle-only' for r in witnessed),
                      'fallbackSettledWasm':len(results)-len(witnessed)},
            'scope':'Native type references with a per-cell order witness; a cell without one falls back to '
                    'settled-WASM (fallback A); Home/End remains conditional; no browser or Up/Down parity claim'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:result=read(a.directory.resolve())
    except (OSError,ValueError,KeyError,TypeError) as error:result={'verdict':'NOT_ESTABLISHED','problems':[str(error)]}
    text=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')
    return int(result['verdict']!='NATIVE_S5_TYPE_SAVES_READ')
if __name__=='__main__':raise SystemExit(main())
