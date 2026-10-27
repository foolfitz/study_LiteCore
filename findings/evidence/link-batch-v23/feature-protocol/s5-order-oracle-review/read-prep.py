#!/usr/bin/env python3
"""Compare the preserved order-dependent S5 preparations without changing their verdicts.

This is an evidence reader for an oracle decision, not an acceptance judge. Every input is
hashed; browser arms go through the existing evidence bindings before any comparison.
Run from any directory; optionally pass a different preparation directory.
"""
import difflib
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'wasm_sdk_probe/tools'))
from judge_v23_feature_selection import (Evidence, readiness, s5_arm, single_line,
    s5_compare, s5_reduced, paragraph_difference, odt_content)
from odt_paragraphs import paragraph_texts_from_xml
from read_v23_native_s5 import expected_posts
from read_v23_native_s5_empty_mark import read as read_witness

BASE=ROOT/'findings/evidence/link-batch-v23/feature-protocol'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def settled_order(row):
    """Read the timestamp witnesses, keeping lifecycle source binding a separate claim."""
    steps=row['steps'];posts=row['posts'];sequence=row['sequence']
    if row['interMemberSettle']!={'after':'every member','quietMs':800,'capMs':8000}:
        raise ValueError('different inter-member policy: '+row['id'])
    if len(posts)!=2*len(sequence) or [s['operation'] for s in steps]!=sequence:
        raise ValueError('member population differs: '+row['id'])
    if [{k:p[k] for k in ('type','character','key')} for p in posts]!=expected_posts(row):
        raise ValueError('different native key posts: '+row['id'])
    def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
    last=-1
    for post in posts:
        if not all(finite(post[k]) for k in ('atMs','returnMs')) or not last<=post['atMs']<=post['returnMs']:
            raise ValueError('invalid post time: '+row['id'])
        last=post['returnMs']
    result=[]
    for i,step in enumerate(steps):
        if not all(finite(step[k]) for k in ('settleMs','readStartMs','readEndMs')) or step['settleMs']<0:
            raise ValueError('unwitnessed member read: '+row['id'])
        next_post=posts[2*i+2]['atMs'] if i+1<len(steps) else None
        if not posts[2*i+1]['returnMs']<=step['readStartMs']<=step['readEndMs'] or (next_post is not None and not step['readEndMs']<next_post):
            raise ValueError('member read not ordered between posts: '+row['id'])
        result.append({'operation':step['operation'],'keyUpReturnMs':posts[2*i+1]['returnMs'],
            'readStartMs':step['readStartMs'],'readEndMs':step['readEndMs'],'nextKeyDownMs':next_post})
    return result


def main():
    directory=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else BASE/'s5-order-prep-02'
    inputs={}
    def read(path,expected=None):
        raw=path.read_bytes();actual=sha(raw)
        if expected is not None and actual!=expected:raise ValueError('changed input: '+str(path))
        inputs[str(path.relative_to(ROOT))]=actual
        return raw
    report=json.loads(read(directory/'report.json'));plan=report['config']
    if report.get('postConfig')!=plan:raise ValueError('preparation did not finish without drift')
    witness=BASE/'s5-native/empty-mark-witness-01'
    validation=read_witness(witness)
    if validation['verdict']!='NATIVE_S5_EMPTY_MARK_WITNESS_READ':raise ValueError(validation)
    summary=json.loads(read(witness/'comparison.json'))
    rows=[json.loads(line) for line in read(witness/'native.jsonl',summary['artifacts']['native.jsonl']).splitlines() if line]
    native={r['id']:r for r in rows if 'id' in r}
    timing_census={cid:len(settled_order(row)) for cid,row in native.items()}
    result=[]
    for entry in report['runs']:
        path=directory/entry['path']
        if path.is_file():raw=read(path,entry['sha256'])
        else:
            raw=gzip.decompress(read(Path(str(path)+'.gz')))
            if sha(raw)!=entry['sha256']:raise ValueError('changed compressed page: '+str(path))
        cell=json.loads(raw);page=cell['page'];row=plan['s5'][cell['caseId']]
        evidence=Evidence(page,plan,cell['browser']);readiness(evidence)
        arms={name:s5_arm(evidence,name,row,plan['cases'][row['sourceArm']]) for name in ('s5cand','s5ref')}
        evidence.closure()
        queued=read(ROOT/row['native']['after']['path'],row['native']['after']['sha256'])
        after=Path('saves')/native[row['id']]['afterFile']
        settled=read(witness/after,summary['artifacts'][str(after)])
        before=Path('saves')/native[row['id']]['beforeFile']
        settled_before=read(witness/before,summary['artifacts'][str(before)])
        references={'native-queued':queued,'native-settled':settled,'wasm-settled':arms['s5ref']['final']}
        comparisons={}
        for name,value in references.items():
            is_native=name.startswith('native-')
            comparisons[name]={'referenceSha256':sha(value),
                'reducedEqual':s5_compare(row['family'],arms['s5cand']['final'],value,is_native),
                'paragraphsEqual':paragraph_texts_from_xml(odt_content(arms['s5cand']['final']))==paragraph_texts_from_xml(odt_content(value)),
                'firstDifferingParagraph':paragraph_difference(arms['s5cand']['final'],value)}
        a=s5_reduced(queued,True).decode();b=s5_reduced(settled,True).decode()
        delta=list(difflib.unified_diff(a.replace('><','>\n<').splitlines(),b.replace('><','>\n<').splitlines(),
                                      fromfile='native-queued',tofile='native-settled',n=1))
        result.append({'browser':cell['browser'],'caseId':row['id'],'storedInspection':cell['inspection'],
            'singleLineWitness':single_line(evidence,'s5cand'),'emptyMark':row['emptyMark'],
            'nativeOrderIndependent':row['nativeOrderIndependent'],
            'originalComparableToNative':s5_compare(row['family'],arms['s5cand']['original'],
                read(ROOT/row['native']['before']['path'],row['native']['before']['sha256']),True),
            'originalComparableToSettledNative':s5_compare(row['family'],arms['s5cand']['original'],settled_before,True),
            'settledReductionDoesNotHideEdit':s5_reduced(settled_before,True)!=s5_reduced(settled,True) or odt_content(settled_before)==odt_content(settled),
            'settledMemberOrder':settled_order(native[row['id']]),
            'candidateSha256':sha(arms['s5cand']['final']),
            'candidateParagraphs':paragraph_texts_from_xml(odt_content(arms['s5cand']['final'])),
            'comparisons':comparisons,'nativeReducedDiff':delta,'nativeSettledSteps':native[row['id']]['steps']})
    print(json.dumps({'schema':1,'scope':'Oracle decision evidence only; no acceptance verdict',
        'readerSha256':sha(Path(__file__).read_bytes()),'nativeWitnessValidation':{'verdict':validation['verdict'],'counts':validation['counts']},
        'settledTimingCensus':{'population':len(timing_census),'valid':len(timing_census),'members':sum(timing_census.values())},
        'lifecycleScope':'Member reads have timestamp witnesses; setup and save order are bound through the retained harness source, not independent timestamps',
        'inputs':inputs,'cells':result},indent=2))


if __name__=='__main__':main()
