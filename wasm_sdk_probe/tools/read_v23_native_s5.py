#!/usr/bin/env python3
"""Read actual native continuation saves. Availability is not browser parity."""
import argparse
import json
import math
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_v23_native_s5 import ROOT,TOOLS,SOURCES,cases,sha,read_inventory,validate_build_receipt
from odt_paragraphs import paragraph_texts_from_xml
from run_merge_wasm_shakedown import reduce_content
KEYS={'Left':1026,'Right':1027,'Home':1028,'End':1029}

def content(path):
    with zipfile.ZipFile(path) as z:return z.read('content.xml')

def comparison(path,family):
    data=content(path)
    return paragraph_texts_from_xml(data) if family=='type' else reduce_content(data)

def compare_saved(reference,candidate,family):
    """Literal comparator only; caller must first establish the oracle's applicability."""
    return comparison(reference,family)==comparison(candidate,family)

def expected_posts(row):
    result=[]
    for op in row['sequence']:
        if op.startswith('Shift+'):char,key=0,KEYS[op[6:]]|0x1000
        elif op=='text:x':char,key=120,0
        else:char,key=0,{'Backspace':1283,'Delete':1286}[op]
        result.extend({'type':t,'character':char,'key':key} for t in (0,1))
    return result

def validate_cell(row,expected,setup,saves,artifacts):
    issues=[]
    if row.get('sequence')!=expected['sequence']:issues.append('sequence mismatch')
    if row.get('mode')!='default-native-queued':issues.append('wrong native mode')
    if row.get('family')!=expected['family'] or row.get('key')!=setup['key'] or row.get('shape')!=setup['shape']:
        issues.append('source identity mismatch')
    posts=row.get('posts',[])
    if [{k:p.get(k) for k in ('type','character','key')} for p in posts]!=expected_posts(expected):
        issues.append('actual FIFO key posts differ')
    previous=-1
    for post in posts:
        start,end=post.get('atMs'),post.get('returnMs')
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (start,end)) or start<previous or end<start:
            issues.append('invalid actual post ordering');break
        previous=end
    for field in ('openedSettleMs','setupSettleMs','finalSettleMs'):
        value=row.get(field)
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            issues.append('unestablished settle: '+field)
    selection=setup['setup']['expectedSelection']
    if row.get('expectedSelection')!=selection:issues.append('setup declaration differs from retained source')
    if row.get('expectedCursorPoint')!=setup['setup']['expectedMovingPointName'] or not row.get('expectedCursorRect'):
        issues.append('missing or wrong logical setup point')
    for which in ('before','beforePost'):
        state=row.get(which,{})
        if state.get('getTextSelection')!=selection or state.get('INVALIDATE_VISIBLE_CURSOR')!=row.get('expectedCursorRect'):
            issues.append('missing or wrong actual pre-key selection/caret: '+which)
    if row.get('beforeSelectionType')!=(1 if setup['setup']['expectRange'] else 0):
        issues.append('actual pre-key selection type differs')
    if row.get('afterSelectionType') not in (0,1,2) or not isinstance(row.get('after',{}).get('getTextSelection'),str):
        issues.append('missing actual post-key selection')
    outputs={}
    for label in ('before','after'):
        name=row.get(label+'File','')
        if not name or Path(name).name!=name or not name.endswith('.odt'):
            issues.append('invalid save path: '+label);continue
        path=saves/name
        if row.get('saved'+label.title()) is not True or not path.is_file():
            issues.append('missing actual save: '+label);continue
        if artifacts.get('saves/'+name)!=sha(path):issues.append('save not bound to completion: '+label)
        try:
            raw=content(path);paragraphs=paragraph_texts_from_xml(raw);reduced=reduce_content(raw)
            import hashlib
            outputs[label]={'path':str(path),'sha256':sha(path),'paragraphs':paragraphs,
                'reducedContentSha256':hashlib.sha256(reduced).hexdigest()}
        except (ValueError,KeyError,zipfile.BadZipFile) as exc:issues.append('unreadable saved content: '+str(exc))
    return issues,outputs

def read(directory):
    table,expected=cases();problems=[];results=[]
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
        build=json.loads(Path(receipt['path']).read_text())
        from build_v23_native_s5_owner import COMPILED
        if build.get('sources')!={str((TOOLS/n).relative_to(ROOT)):sha(TOOLS/n) for n in COMPILED} or build.get('binary')!=identity.get('binary') or build.get('exitCode')!=0 or build.get('protectedInputsUnchanged') is not True or build.get('snapshotsMatch') is not True:
            problems.append('owner build receipt does not bind compiled source/binary')
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
    for item in expected:
        if item['id'] not in byid:continue
        issues,outputs=validate_cell(byid[item['id']],item,setups[item['sourceArm']],directory/'saves',artifacts)
        actual=byid[item['id']]
        if actual.get('expectedCursorRect')!=points.get(actual.get('expectedCursorPoint')):
            issues.append('setup cursor not bound to actual native discovery')
        if 'before' in outputs and outputs['before']['paragraphs']!=paragraph_texts_from_xml((directory/'fixture.fodt').read_bytes()):
            issues.append('before save differs from fixture paragraph text')
        problems.extend(item['id']+': '+issue for issue in issues)
        results.append({'id':item['id'],'status':'NOT_ESTABLISHED' if issues else 'NATIVE_SAVE_AVAILABLE',
            'referencePolicy':item['referencePolicy'],'requiresBrowserSingleLineWitness':item['referencePolicy']!='native',
            'browserParity':'NOT_ESTABLISHED_UNPERFORMED','comparison':item['comparison'],'saves':outputs})
    return {'schema':1,'verdict':'NOT_ESTABLISHED' if problems else 'NATIVE_S5_SAVES_AVAILABLE',
            'nativeExecutionsPerCell':1,'cells':results,'problems':problems,
            'scope':'Native reference availability only; Home/End remains conditional; no browser or Up/Down parity claim'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:result=read(a.directory.resolve())
    except (OSError,ValueError,KeyError,TypeError) as error:result={'verdict':'NOT_ESTABLISHED','problems':[str(error)]}
    text=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')
    return int(result['verdict']!='NATIVE_S5_SAVES_AVAILABLE')
if __name__=='__main__':raise SystemExit(main())
