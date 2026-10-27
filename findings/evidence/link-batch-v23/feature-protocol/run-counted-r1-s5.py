#!/usr/bin/env python3
"""Run the predeclared frozen R1 then S5 cohorts; preserve the first failure and stop."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
SDK=ROOT/'wasm_sdk_probe'
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(SDK/'tools'))
from v23_feature_selection_cases import config,encoded,digest


def now():return datetime.datetime.now().astimezone().isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    declaration=BASE/'counted-r1-s5-01/cohort.json'
    frozen=json.loads(declaration.read_bytes());status=declaration.with_name('status.json')
    if status.exists():raise SystemExit('existing pipeline status; no retry')
    record={'schema':1,'startedAt':now(),'pid':os.getpid(),'cohortSha256':sha(declaration),
            'gitHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'state':'STARTING','stages':[]}
    def write():
        temporary=status.with_suffix('.json.tmp');temporary.write_bytes(encoded(record));temporary.replace(status)
    def verify():
        assert sha(Path(__file__))==frozen['launcherSha256'],'launcher changed'
        assert digest(encoded(config()))==frozen['configSha256'],'frozen plan/input drift'
        for path,want in frozen['prerequisites'].items():assert sha(ROOT/path)==want,'prerequisite changed: '+path
    write()
    try:
        for stage in frozen['stages']:
            verify();output=ROOT/stage['output']
            assert not output.exists(),'cohort output already exists'
            entry={'population':stage['population'],'runnerArgv':stage['runnerArgv'],
                   'judgeArgv':stage['judgeArgv'],'cwd':str(SDK),'startedAt':now()}
            record['stages'].append(entry);record['state']='RUNNING_'+stage['population'].upper();write()
            log=BASE/('counted-r1-s5-01/'+stage['population']+'.runner.txt')
            start=time.monotonic()
            with log.open('x') as stream:
                result=subprocess.run(stage['runnerArgv'],cwd=SDK,stdout=stream,stderr=subprocess.STDOUT)
            entry.update(runnerExitCode=result.returncode,runnerWallSeconds=round(time.monotonic()-start,1),
                         runnerFinishedAt=now(),runnerLogSha256=sha(log));write()
            if (output/'report.json').is_file():
                entry['reportSha256']=sha(output/'report.json')
                with (output/'aggregate-judge.stdout.json').open('x') as out,(output/'aggregate-judge.stderr.txt').open('x') as err:
                    judged=subprocess.run(stage['judgeArgv'],cwd=SDK,stdout=out,stderr=err)
                entry.update(judgeExitCode=judged.returncode,judgeFinishedAt=now(),
                             judgeOutputSha256=sha(output/'aggregate-judge.stdout.json'))
                (output/'commands.json').write_bytes(encoded(entry))
            verify();write()
            if result.returncode or entry.get('judgeExitCode')!=0:
                record['state']='STOPPED_FIRST_NONPASS';record['finishedAt']=now();write();return 1
        record['state']='BOTH_COHORTS_PASS';record['finishedAt']=now();write();return 0
    except BaseException as error:
        record.update(state='STOPPED_EXCEPTION',finishedAt=now(),error=repr(error));write();raise


if __name__=='__main__':raise SystemExit(main())
