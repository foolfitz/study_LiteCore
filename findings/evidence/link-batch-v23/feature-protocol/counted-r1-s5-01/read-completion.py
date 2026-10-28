#!/usr/bin/env python3
"""Verify retained frozen-run receipts and re-read every observed cell without filling gaps."""
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[3]
sys.path.insert(0,str(ROOT/'wasm_sdk_probe/tools'))
import judge_v23_feature_selection as reader
from v23_feature_selection_cases import config,encoded


def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):return sha(path.read_bytes())


def cell(directory,receipt):
    path=directory/receipt['path']
    raw=path.read_bytes() if path.is_file() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
    assert sha(raw)==receipt['sha256'],'raw cell receipt differs: '+receipt['path']
    return json.loads(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    frozen=json.loads((HERE/'cohort.json').read_bytes());status=json.loads((HERE/'status.json').read_bytes())
    assert status['cohortSha256']==file_sha(HERE/'cohort.json')
    assert status['state']=='STOPPED_FIRST_NONPASS'
    assert file_sha(BASE/'run-counted-r1-s5.py')==frozen['launcherSha256']
    assert sha(encoded(config()))==frozen['configSha256'],'live frozen plan differs'
    for path,want in frozen['instrumentSources'].items():assert file_sha(ROOT/'wasm_sdk_probe'/path)==want,path
    for path,want in frozen['prerequisites'].items():assert file_sha(ROOT/path)==want,path
    assert [s['population'] for s in status['stages']]==[s['population'] for s in frozen['stages']]
    output={'schema':1,'scope':'Retained completed R1 and stopped S5 only; no new browser observations or missing-cell credit',
            'at':datetime.datetime.now().astimezone().isoformat(),'readerSha256':file_sha(Path(reader.__file__)),
            'completionReaderSha256':file_sha(Path(__file__)),'cohortSha256':status['cohortSha256'],
            'configSha256':frozen['configSha256'],'frozenInputsUnchanged':True,'stages':[]}
    for spec,receipt in zip(frozen['stages'],status['stages']):
        directory=ROOT/spec['output'];report=json.loads((directory/'report.json').read_bytes());plan=report['config']
        assert file_sha(directory/'report.json')==receipt['reportSha256']
        assert file_sha(directory/'aggregate-judge.stdout.json')==receipt['judgeOutputSha256']
        assert file_sha(HERE/(spec['population']+'.runner.txt'))==receipt['runnerLogSha256']
        assert report['argv']==['tools/run_v23_feature_selection.py',*spec['runnerArgv'][3:]]
        assert not report['preparationOnly'] and sha(encoded(plan))==frozen['configSha256']
        assert report['mirrorBindings']==reader.verify_mirror(directory/'mirror',plan)
        assert report['preRed']==frozen['preRed']
        expected=[(b,c) for b in spec['browsers'] for c in spec['caseIds']]
        assert report['runs'],'empty observed population'
        rows=[];failures=[];counts=Counter();references=Counter();overlap=Counter()
        for item in report['runs']:
            observed=cell(directory,item)
            # Reports serialize tuple-valued logical positions as JSON arrays; retain every field.
            value=json.loads(encoded(reader.inspect(observed['page'],plan,observed['browser'])))
            assert value==observed['inspection'],'inspection differs: '+item['path']
            identity=(observed['browser'],observed['caseId']);counts[observed['browser']+'/'+value['verdict']]+=1
            group=value['groups'].get('S5',{});reference=group.get('reference')
            if reference:references[observed['browser']+'/'+reference]+=1
            if 'overlapping' in group:overlap[observed['browser']+'/'+str(group['overlapping'])]+=1
            rows.append({'browser':identity[0],'caseId':identity[1],'verdict':value['verdict'],
                         'reference':reference,'cellSha256':item['sha256'],'inspectionUnchanged':True})
            if value['verdict']!='PASS':failures.append({'cell':identity,'inspection':value})
        identities=[(r['browser'],r['caseId']) for r in rows]
        assert identities==expected[:len(rows)] and len(set(identities))==len(rows),'population is not the declared unique prefix'
        if spec['population']=='r1':
            assert identities==expected and not failures and report['postConfig']==plan
            assert receipt['runnerExitCode']==receipt['judgeExitCode']==0
            aggregate=json.loads((directory/'aggregate-judge.stdout.json').read_bytes())
            assert aggregate['verdict']=='PASS' and aggregate['populationComplete']
            assert (directory/'aggregate-judge.stdout.json').read_bytes()==(directory/'aggregate-judge.reread.stdout.json').read_bytes()
            conclusion='COMPLETE_R1_PASS'
        else:
            assert len(rows)<len(expected) and len(failures)==1 and identities[-1]==tuple(failures[0]['cell'])
            assert report['nonpassing']==[identities[-1][1]] and 'postConfig' not in report
            assert receipt['runnerExitCode']==receipt['judgeExitCode']==1
            assert (directory/'aggregate-judge.stderr.txt').read_text().endswith('actual instrument/source graph differs or incomplete\n')
            conclusion='STOPPED_S5_INCOMPLETE'
        wrong={**report['runs'][0],'sha256':'0'*64}
        try:cell(directory,wrong)
        except AssertionError:pass
        else:raise AssertionError('corrupt raw receipt accepted')
        output['stages'].append({'population':spec['population'],'conclusion':conclusion,'required':len(expected),
            'observed':len(rows),'counts':dict(counts),'references':dict(references),'overlap':dict(overlap),
            'reportSha256':receipt['reportSha256'],'aggregateSha256':receipt['judgeOutputSha256'],
            'wrongReceiptControlRefused':True,'failures':failures,'rows':rows})
    with args.output.open('x') as stream:json.dump(output,stream,indent=2);stream.write('\n')
    print(json.dumps([{k:s[k] for k in ('population','conclusion','required','observed','counts')} for s in output['stages']]))


if __name__=='__main__':main()
