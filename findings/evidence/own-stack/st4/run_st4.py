#!/usr/bin/env python3
"""ST4 of SPEC-M3-own-stack: the reason for the move.  Poll the own stack while ddev starts and stops a project.

  run_st4.py              run it, write report.json and reading.json next to this file, exit 0 iff ST4_HOLDS
  run_st4.py --self-test  every mutation of report.json must turn the reading red

Uses the real `ddev` (PATH as given, not host-stack/bin) on two projects of ours and no other: `litecoreprobe` is started and
stopped, and `ddev stop litecore` is the very command that removed a stack container during the rehearsal, when the web image
still carried ddev's labels.  `litecore` is stopped, so for ddev that one is a no-op.

The controls are what make green mean something.  ddev's own router must be seen to move while the own stack does not (no move
means the start did not happen, and nothing was tested), and a dead port must read as an error in the same poller.
"""
import argparse
import base64
import copy
import json
from pathlib import Path
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
OWN = 'https://litecore.localhost:18443'
DDEV_SIDE = 'https://litecoreprobe.ddev.site:8443/status.php'
DEAD = 'https://litecore.localhost:18444/status.php'
STACK = ('litecore-own-web-1', 'litecore-own-db-1', 'litecore-own-router-1')
TLS = ssl.create_default_context()
TLS.check_hostname = False
TLS.verify_mode = ssl.CERT_NONE


def run(argv, timeout=300):
    started = time.time()
    done = subprocess.run(argv, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout)
    return {'argv': argv, 'exit': done.returncode, 'seconds': round(time.time() - started, 1),
            'stdout': done.stdout[-1500:], 'stderr': done.stderr[-1500:]}


def containers():
    rows = {}
    for name in STACK:
        out = subprocess.run(['docker', 'inspect', '--format', '{{.Id}} {{.State.StartedAt}} {{.State.Status}} {{index .Config.Labels "com.ddev.platform"}}', name],
                             capture_output=True, text=True)
        rows[name] = out.stdout.strip() or 'absent'
    return rows


def ddev_labelled():
    out = subprocess.run(['docker', 'ps', '-a', '--filter', 'label=com.ddev.platform=ddev', '--format', '{{.Names}}'], capture_output=True, text=True)
    return sorted(out.stdout.split())


def project_status(name):
    states = json.loads(subprocess.run(['ddev', 'list', '-j'], capture_output=True, text=True).stdout)['raw']
    return next(p['status'] for p in states if p['name'] == name)


def get(url, headers=None, method='GET'):
    request = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, context=TLS, timeout=5) as response:
            response.read(2048)
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception as error:  # noqa: BLE001 -- the poll's whole point is to record it
        return f'{type(error).__name__}: {str(error)[:80]}'


class Poller(threading.Thread):
    def __init__(self, url, every, headers=None, method='GET'):
        super().__init__(daemon=True)
        self.url, self.every, self.headers, self.method = url, every, headers, method
        self.rows, self.running = [], True

    def run(self):
        while self.running:
            self.rows.append([round(time.time(), 2), get(self.url, self.headers, self.method)])
            time.sleep(self.every)

    def stop(self):
        self.running = False
        self.join(10)
        outcomes = {}
        for _, outcome in self.rows:
            outcomes[str(outcome)] = outcomes.get(str(outcome), 0) + 1
        changes = [row for prev, row in zip(self.rows, self.rows[1:]) if prev[1] != row[1]]
        return {'url': self.url, 'polls': len(self.rows), 'outcomes': outcomes, 'changes': changes[:40]}


def password():
    import re
    text = (Path.home() / 'Projects/Nextcloud_Apps/litecore/.ddev/config.local.yaml').read_text()
    return re.search(r'NEXTCLOUD_ADMIN_PASSWORD=(\S+)', text).group(1)


def experiment():
    auth = {'Authorization': 'Basic ' + base64.b64encode(('admin:' + password()).encode()).decode(), 'Depth': '0'}
    before = {'containers': containers(), 'ddevLabelled': ddev_labelled(), 'probeStatus': project_status('litecoreprobe')}
    status = Poller(OWN + '/status.php', 0.25)
    dav = Poller(OWN + '/remote.php/dav/files/admin/', 1.0, auth, 'PROPFIND')
    side = Poller(DDEV_SIDE, 0.5)
    for poller in (status, dav, side):
        poller.start()
    steps = []
    time.sleep(10)
    steps.append(run(['ddev', 'start', 'litecoreprobe']))
    during = project_status('litecoreprobe')
    time.sleep(20)
    steps.append(run(['ddev', 'stop', 'litecoreprobe']))
    time.sleep(5)
    steps.append(run(['ddev', 'stop', 'litecore']))
    time.sleep(5)
    polls = {'status': status.stop(), 'dav': dav.stop(), 'ddevSide': side.stop()}
    return {'before': before, 'steps': steps, 'probeStatusDuring': during, 'polls': polls, 'deadPort': get(DEAD),
            'after': {'containers': containers(), 'ddevLabelled': ddev_labelled(), 'probeStatus': project_status('litecoreprobe')}}


def judge(r):
    problems = []
    for name, want in (('status', {'200'}), ('dav', {'207'})):
        p = r['polls'][name]
        if not p['polls'] or set(p['outcomes']) != want:
            problems.append(f"{name}: {p['outcomes']}")
    if r['before']['containers'] != r['after']['containers'] or 'absent' in r['after']['containers'].values():
        problems.append(f"containers moved: {r['before']['containers']} -> {r['after']['containers']}")
    for side in ('before', 'after'):
        if set(r[side]['ddevLabelled']) & set(STACK):
            problems.append(f"{side}: ddev can see the stack: {r[side]['ddevLabelled']}")
    # Controls: nothing above means anything without them.
    if r['probeStatusDuring'] != 'running' or r['after']['probeStatus'] != 'stopped':
        problems.append(f"control: litecoreprobe {r['probeStatusDuring']} then {r['after']['probeStatus']}")
    if len(r['polls']['ddevSide']['outcomes']) < 2:
        problems.append(f"control: ddev's side did not move: {r['polls']['ddevSide']['outcomes']}")
    if isinstance(r['deadPort'], int):
        problems.append(f"control: the dead port answered {r['deadPort']}")
    if any(s['exit'] != 0 for s in r['steps']):
        problems.append(f"a ddev step failed: {[(s['argv'], s['exit']) for s in r['steps']]}")
    return {'verdict': 'ST4_HOLDS' if not problems else 'ST4_NOT_ESTABLISHED', 'problems': problems,
            'polls': {k: {'polls': v['polls'], 'outcomes': v['outcomes']} for k, v in r['polls'].items()},
            'seconds': [[s['argv'][1:], s['seconds']] for s in r['steps']]}


def self_test(r):
    def one_error(x):
        x['polls']['status']['outcomes']['URLError: refused'] = 1

    def dav_500(x):
        x['polls']['dav']['outcomes']['500'] = 1

    def recreated(x):
        name = STACK[0]
        x['after']['containers'][name] = 'another-id ' + x['after']['containers'][name]

    def removed(x):
        x['after']['containers'][STACK[0]] = 'absent'

    def labelled(x):
        x['after']['ddevLabelled'].append(STACK[0])

    def side_still(x):
        x['polls']['ddevSide']['outcomes'] = {'404': 9}

    def no_start(x):
        x['probeStatusDuring'] = 'stopped'

    def dead_answers(x):
        x['deadPort'] = 200

    def empty(x):
        x['polls']['status'] = {'polls': 0, 'outcomes': {}}

    results = {}
    for fn in (one_error, dav_500, recreated, removed, labelled, side_still, no_start, dead_answers, empty):
        mutated = copy.deepcopy(r)
        fn(mutated)
        results[fn.__name__] = judge(mutated)['verdict'] != 'ST4_HOLDS'
    return {'selfTest': 'ALL_RED' if all(results.values()) else 'SOME_HELD', 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = self_test(json.loads((HERE / 'report.json').read_text()))
        (HERE / 'self-test.json').write_text(json.dumps(result, indent=1) + '\n')
        print(json.dumps(result))
        return 0 if result['selfTest'] == 'ALL_RED' else 1
    report = experiment()
    (HERE / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    reading = judge(report)
    (HERE / 'reading.json').write_text(json.dumps(reading, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(reading, ensure_ascii=False)[:3000])
    return 0 if reading['verdict'] == 'ST4_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
