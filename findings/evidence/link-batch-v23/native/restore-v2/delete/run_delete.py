#!/usr/bin/env python3
"""Run the predeclared 9 x 5 DELETE Q cohort, fresh directories only."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from arms import D_ARMS

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / 'ordered-commands/tool'
FIXTURES = OLD.parent / 'fixtures'
SOURCES = [HERE / name for name in ('arms.py', 'run_delete.py', 'read_delete.py', 'ARMS.md')]
SOURCES += [HERE.parent / 'tool/oc_native.cpp', OLD / 'read_results.py']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(binary):
    return {'binary': str(Path(binary).resolve()), 'binarySha256': digest(binary),
            'sources': {str(p): digest(p) for p in SOURCES},
            'fixtures': {str(FIXTURES / (name+'.fodt')): digest(FIXTURES / (name+'.fodt')) for name in sorted({a['fixture'] for a in D_ARMS})}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('binary', 'install', 'out', 'work'):
        p.add_argument('--' + arg, type=Path, required=True)
    a = p.parse_args()
    assert not a.out.exists() and not a.work.exists(), 'out and work must both be fresh'
    a.out.mkdir(parents=True); a.work.mkdir(parents=True)
    (a.out / 'identity.json').write_text(json.dumps(identity(a.binary), indent=2) + '\n')
    (a.out / 'arms.json').write_text(json.dumps(D_ARMS, indent=2) + '\n')
    with (a.out / 'run-log.jsonl').open('x') as log:
        for r in range(1, 6):
            for arm in D_ARMS:
                work = a.work.resolve() / f'{arm["name"]}-r{r}'
                (work / 'prof').mkdir(parents=True)
                fixture = work / (arm['fixture']+'.fodt')
                shutil.copyfile(FIXTURES / (arm['fixture']+'.fodt'), fixture)
                out = a.out / arm['name']; out.mkdir(exist_ok=True)
                env = dict(os.environ, SAL_USE_VCLPLUGIN='svp', SAL_LOK_OPTIONS='unipoll')
                env.pop('OC_A11Y', None)
                cmd = ['nice', '-n', '10', str(a.binary.resolve()), 'unipoll', str(a.install.resolve()),
                       (work / 'prof').as_uri(), fixture.as_uri(), arm['script'], (work / 'saved.fodt').as_uri()]
                start = time.monotonic()
                with (out / f'unipoll-r{r}.jsonl').open('x') as stdout, (out / f'unipoll-r{r}.stderr').open('x') as stderr:
                    try:
                        result = subprocess.run(cmd, stdout=stdout, stderr=stderr, env=env, timeout=180)
                        status = result.returncode
                    except subprocess.TimeoutExpired:
                        status = 'timeout'
                if (work / 'saved.fodt').exists():
                    (out / f'unipoll-r{r}.fodt.gz').write_bytes(gzip.compress((work / 'saved.fodt').read_bytes()))
                row = {'arm': arm['name'], 'mode': 'unipoll', 'round': r, 'exit': status,
                       'seconds': time.monotonic() - start, 'cmd': cmd,
                       'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
                log.write(json.dumps(row) + '\n'); log.flush()
                print(json.dumps(row), flush=True)
                # Output and the saved document are archived above. Keep failed
                # child profiles for diagnosis; remove only successful owned work.
                if status == 0 and (work / 'saved.fodt').exists():
                    shutil.rmtree(work)


if __name__ == '__main__':
    main()
