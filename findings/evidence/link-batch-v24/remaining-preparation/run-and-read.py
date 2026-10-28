#!/usr/bin/env python3
"""Owner-authorized unattended remaining selection, raw reread, then A4; stop at any nonpass."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
SDK = ROOT / 'wasm_sdk_probe'
A4 = ROOT / 'findings/evidence/link-batch-v24/four-arms-counted-01'
PINS = ROOT / 'findings/evidence/link-batch-v24/count-preparation/a4-instruments.sha256'


def now():
    return datetime.datetime.now().astimezone().isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args(); args.cohort = args.cohort.resolve(); out = args.cohort.parent
    commands = {
        'remaining': [sys.executable, '-I', 'tools/run_v24_remaining_cohort.py', '--cohort', str(args.cohort)],
        'raw-read': [sys.executable, '-I', 'tools/read_v24_remaining_cohort.py', '--cohort', str(args.cohort), '--out', str(out / 'completion-read-01.json')],
        'a4-pins-before': ['sha256sum', '--check', str(PINS)],
        'a4-chrome': [sys.executable, '-I', 'tools/run_v24_four_arms.py', '--browser', 'chrome', '--out', str(A4 / 'chrome')],
        'a4-firefox': [sys.executable, '-I', 'tools/run_v24_four_arms.py', '--browser', 'firefox', '--out', str(A4 / 'firefox')],
        'a4-pins-after': ['sha256sum', '--check', str(PINS)],
        'a4-judge': [sys.executable, '-I', 'tools/judge_v24_product_four_arms.py', str(A4 / 'chrome/report.v23-four-arms'),
                     str(A4 / 'firefox/report.v23-four-arms'), '--out', str(A4 / 'aggregate-judge.json')],
    }
    if args.plan_only:
        print(json.dumps({'cwd': str(SDK), 'commands': commands, 'scope': 'Plan only; no status, measurement, DDEV or build'}, indent=1))
        return 0
    status = out / 'job-status.json'
    record = {'schema': 1, 'startedAt': now(), 'authority': 'Owner authorized agent execution while away, 2026-10-29',
              'scriptSha256': sha(Path(__file__)), 'cohortSha256': sha(args.cohort), 'cwd': str(SDK),
              'gitHead': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'state': 'STARTING', 'steps': []}
    with status.open('x') as stream:
        json.dump(record, stream, indent=1); stream.write('\n')
    def write():
        temporary = status.with_suffix('.json.tmp'); temporary.write_text(json.dumps(record, indent=1) + '\n'); temporary.replace(status)
    def run(name):
        record['state'] = name.upper(); entry = {'name': name, 'argv': commands[name], 'startedAt': now()}
        record['steps'].append(entry); write(); started = time.monotonic()
        log = out / ('job-' + name + '.txt')
        with log.open('x') as stream:
            proc = subprocess.Popen(commands[name], cwd=SDK, stdout=stream, stderr=subprocess.STDOUT)
            entry['pid'] = proc.pid; write(); rc = proc.wait()
        entry.update(exit=rc, seconds=round(time.monotonic() - started, 1), finishedAt=now(), log=log.name, logSha256=sha(log)); write()
        return rc
    def stopped():
        record.update(state='STOPPED_NONPASS', finishedAt=now()); write(); return 1
    try:
        rc = run('remaining')
        read_rc = run('raw-read')  # Always preserve the partial verdict, including after a runner refusal.
        if rc or read_rc:
            return stopped()
        for name in ('a4-pins-before', 'a4-chrome', 'a4-firefox', 'a4-pins-after', 'a4-judge'):
            if run(name):
                return stopped()
        record.update(state='SELECTION_AND_A4_PASS', finishedAt=now()); write(); return 0
    except BaseException as error:
        record.update(state='STOPPED_EXCEPTION', finishedAt=now(), error=repr(error)); write(); raise


if __name__ == '__main__':
    raise SystemExit(main())
