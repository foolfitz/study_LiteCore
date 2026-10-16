#!/usr/bin/env python3
"""Run the D1 marker variant of every arm in the D1 population, plus the no-Ctrl controls.

Usage:
  python3 -I run_d1.py --binary BIN --install DIR --fixtures DIR --population POP_JSON
                       --out DIR --work DIR [--runs 3] [--only NAME[,NAME...]]

POP_JSON is written by d1_population.py (--json). For every IN arm the script is
its `d1Script` (the 142 arm's steps up to its last Ctrl+Home/End press, then T,
S, L). The controls (CONTROLS below) run the paired arm's `noCtrlScript`: the
same placement with every Ctrl press removed, then T, S, L.

Each (run, round) is its own process: `nice -n 10`, a fresh empty user profile,
its own copy of the fixture, SAL_USE_VCLPLUGIN=svp, SAL_LOK_OPTIONS removed (so
LOK runs threaded, as in the 142 run and in the product, see the 142 README's
correction). Rounds are run-major. Before each process the runner waits while
another LOK process is running (other_lok below) and logs how long it waited.

--resume skips (run, round) pairs that already completed (used once, after the
runner was stopped while waiting on the owner's desktop LibreOffice; README).

Writes out/runs.json (what was run), out/<name>/r<N>.jsonl, r<N>.stderr,
r<N>.fodt.gz, and appends one line per process to out/run-log.jsonl.
"""
import argparse
import datetime
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import time

# control name -> the IN arm whose placement it repeats without the Ctrl press(es)
CONTROLS = {
    'ctl-noctrl-a1-home-mid': 'a1-home-mid',     # expected to differ by paragraph
    'ctl-noctrl-t-home-B2-n1': 't-home-B2-n1',   # expected to differ by offset in the same paragraph
}

# Executable names of the probes this machine runs (the Markdown agent's md-paste-probe,
# md-paste-probe2, ...; this folder's f142-*). soffice / soffice.bin count only when
# they run from an `instdir/program` (a study build): a desktop LibreOffice from
# /opt or /usr is the owner's editor, not a probe, and can stay open for hours.
# (Changed during the run, see the README: the first version also matched every
# soffice.bin and waited on the owner's desktop Writer.)
PROBE_NAMES = re.compile(r'^(md-paste-probe.*|f142-.*|native-md.*)$')


def other_lok():
    """Other processes that are LOK probes: a process that maps a libmergedlo.so
    from an `instdir/program` install, or was given an `instdir/program` path as
    an argument (the Markdown runner's own rule, so both runners see each other,
    including `timeout` wrappers), or whose executable name is a known probe."""
    me = os.getpid()
    busy = []
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid) == me:
            continue
        try:
            with open(f'/proc/{pid}/cmdline', 'rb') as f:
                args = [x.decode('utf-8', 'replace') for x in f.read().split(b'\0') if x]
        except OSError:
            continue
        if not args:
            continue
        base = os.path.basename(args[0])
        if base in ('bash', 'sh', 'zsh', 'python3', 'python'):
            continue
        hit = PROBE_NAMES.match(base) or any(a.rstrip('/').endswith('instdir/program') for a in args[1:]) \
            or (base in ('soffice', 'soffice.bin') and 'instdir/program/' in args[0])
        if not hit:
            try:
                with open(f'/proc/{pid}/maps', 'rb') as f:
                    hit = b'instdir/program/libmergedlo.so' in f.read()
            except OSError:
                pass
        if hit:
            busy.append(f'{pid} {" ".join(args)[:160]}')
    return busy


def wait_for_quiet():
    waited, seen = 0.0, []
    while True:
        busy = other_lok()
        if not busy:
            return waited, seen
        if not seen or seen[-1] != busy:
            seen.append(busy)
        time.sleep(2)
        waited += 2
        if waited > 3600:
            raise SystemExit(f'another LOK process has been running for 60 min: {busy}')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--binary', required=True)
    ap.add_argument('--install', required=True)
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--population', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--only', default='')
    ap.add_argument('--resume', action='store_true',
                    help='skip a (run, round) whose r<N>.jsonl already has a done record and whose fodt.gz exists')
    a = ap.parse_args()
    pop = json.loads(pathlib.Path(a.population).read_text())
    by_name = {x['name']: x for x in pop['in']}
    runs = [{'name': x['name'], 'fixture': x['fixture'], 'script': x['d1Script'], 'role': 'D1',
             'pairedWith': None} for x in pop['in']]
    for ctl, arm in CONTROLS.items():
        runs.append({'name': ctl, 'fixture': by_name[arm]['fixture'], 'script': by_name[arm]['noCtrlScript'],
                     'role': 'control', 'pairedWith': arm})
    out = pathlib.Path(a.out)
    work = pathlib.Path(a.work)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'runs.json').write_text(json.dumps(runs, indent=1) + '\n')
    only = set(filter(None, a.only.split(',')))
    todo = [x for x in runs if not only or x['name'] in only]
    env = dict(os.environ)
    env['SAL_USE_VCLPLUGIN'] = 'svp'
    env.pop('SAL_LOK_OPTIONS', None)
    total_wait = 0.0
    with (out / 'run-log.jsonl').open('a') as log:
        for r in range(1, a.runs + 1):
            for x in todo:
                prev = out / x['name'] / f'r{r}.jsonl'
                if a.resume and prev.exists() and '"rec":"done"' in prev.read_text() \
                        and (out / x['name'] / f'r{r}.fodt.gz').exists():
                    continue
                d = work / f"{x['name']}-r{r}"
                if d.exists():
                    shutil.rmtree(d)
                (d / 'prof').mkdir(parents=True)
                fx = d / f"{x['fixture']}.fodt"
                shutil.copyfile(pathlib.Path(a.fixtures) / f"{x['fixture']}.fodt", fx)
                saved = d / 'saved.fodt'
                od = out / x['name']
                od.mkdir(exist_ok=True)
                cmd = ['nice', '-n', '10', a.binary, a.install, f'file://{d}/prof', f'file://{fx}',
                       x['script'], f'file://{saved}']
                waited, seen = wait_for_quiet()
                total_wait += waited
                start = utc()
                t0 = time.monotonic()
                with open(od / f'r{r}.jsonl', 'w') as so, open(od / f'r{r}.stderr', 'w') as se:
                    rc = subprocess.run(cmd, stdout=so, stderr=se, env=env, timeout=300).returncode
                dur = time.monotonic() - t0
                if saved.exists():
                    with open(saved, 'rb') as f, gzip.GzipFile(od / f'r{r}.fodt.gz', 'wb', mtime=0) as g:
                        g.write(f.read())
                log.write(json.dumps({'run': x['name'], 'round': r, 'start': start, 'seconds': round(dur, 1),
                                      'exit': rc, 'waitedForOtherLokSeconds': waited,
                                      'busySeen': [b[:3] for b in seen[:3]],
                                      'loadavg': open('/proc/loadavg').read().split()[:3], 'cmd': cmd}) + '\n')
                log.flush()
                print(f"{start} r{r} {x['name']}: exit {rc}, {dur:.1f}s, waited {waited:.0f}s", flush=True)
                shutil.rmtree(d)
    print(f'total wait for other LOK processes: {total_wait:.0f} s', flush=True)


if __name__ == '__main__':
    main()
