#!/usr/bin/env python3
"""Red cases for prepare-release.py's v29 gate: run its real main() with what it reads from the evidence changed in memory, one
change at a time.  Nothing on disk is touched and nothing is packaged: the source is patched to stop right after the gates.

Needs the live host still on 0.2.44 (the gate's own precondition), so it has to run before the install.  Exit 0 iff the
unchanged run passes the gates and every case is refused by the v29 gate itself, on the row it names.
"""
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
SRC = OUT / 'prepare-release.py'
sys.dont_write_bytecode = True
real_read_text, real_read_bytes, real_is_file = Path.read_text, Path.read_bytes, Path.is_file


def as_json(change):
    def apply(text):
        data = json.loads(text)
        change(data)
        return json.dumps(data)
    return apply


def add_fail_line(text):
    return text.replace('FAIL: chrome boundaries-gap200 commit median',
                        '  FAIL  firefox  boundaries-gap200 commit median: 14 (needs <= 10)\nFAIL: chrome boundaries-gap200 commit median')


CASES = {
    # name: (path suffix, how, the gate row that must refuse it)
    't1-second-fail-line': ('t1/judge-p2-r2.txt', add_fail_line, 'T1-P2-one-line'),
    't1-c2-red': ('t1/judge-c2-r3.txt', lambda t: t.rstrip() + '\nFAIL: chrome owner-gap80\n', 'T1-C2'),
    't2-v29-spins': ('post-link/idle-v29-chrome-owner-r2.json', as_json(lambda d: d['opened'].update(cpuSeconds=99)), 'T2'),
    't2-red-arm-quiet': ('post-link/idle-spin-chrome-owner-r1.json', as_json(lambda d: d['opened'].update(cpuSeconds=0.1)), 'T2-red'),
    'f3-moved': ('f3-83/diag-single-press/equal.json', as_json(lambda d: d['reading2'].update(moved=[{'check': 'x'}])), 'F3-83-reading2'),
    'f3-other-problem': ('f3-83/diag-single-press/equal.json', as_json(lambda d: d['reading1']['problems'].append('another')), 'F3-83-reading1'),
    'f3-pinned-no-longer-red': ('f3-83/equal-02.stdout.txt', as_json(lambda d: d.update(verdict='F3_83_EQUAL')), 'F3-83-pinned-runner'),
    'f4-one-arm': ('f4-83/final-page/aggregate-judge.json', as_json(lambda d: next(iter(d['arms'].values())).update(outcome='FAIL')), 'F4-83'),
    's4-mutation-missed': ('v29-177/s4/mutation-cosmetic-review/report.json', as_json(lambda d: d.update(verdict='S4_HOLDS')), 'S4-mutations'),
    'merge': ('t3/merge/reading-01.json', as_json(lambda d: d.update(verdict='MERGE_T3_RED')), 'merge'),
    'gap-23-of-24': ('t3/typing-gap/reading-01.json', as_json(lambda d: d.update(held=23)), 'gap-order'),
    't4-one-run': ('t4/reading-run-02.json', as_json(lambda d: d.update(verdict='T4_RED')), 'T4'),
    'v0': ('v29-177/v0/v0-prime.json', as_json(lambda d: d.update(verdict='V0_PRIME_RED')), 'V0prime-83'),
    'e1-c': ('freeze-83/e1-c.txt', lambda t: t.replace('"intact": true', '"intact": false'), 'E1-C'),
    'toolbar': ('toolbar-icons/check-02/firefox.json', as_json(lambda d: d.update(holds=False)), 'toolbar'),
    'st1': ('own-stack/cutover/after.json', as_json(lambda d: d.update(lockRows='a row')), 'ST1'),
    'st2': ('own-stack/st2/reading.json', as_json(lambda d: d.update(verdict='ST2_ST3_DIFFERS')), 'ST2-ST3'),
    'st4': ('own-stack/st4/reading.json', as_json(lambda d: d.update(verdict='ST4_NOT_ESTABLISHED')), 'ST4'),
    'contract': ('host-0.2.45/p-contract.txt', lambda t: 'v29 preconditions failed\n', 'P-contract'),
    'syntax-control-silent': ('pre-link/syntax-control-call.exit.txt', lambda t: '0\n', 'S'),
    'mutation-survived': ('pre-link/pacing-mutations.txt', lambda t: t.replace(' exit 1', ' exit 0', 1), 'U'),
    'static-reds': ('pre-link/static-reds-after-v29.txt', lambda t: t + 'another red\n', 'M'),
}
MISSING = {'missing-st4-reading': 'own-stack/st4/reading.json', 'missing-t1-round': 't1/judge-c2-r2.txt'}


def run(target=None, how=None, gone=None):
    def read_text(self, *a, **k):
        text = real_read_text(self, *a, **k)
        return how(text) if target and str(self).endswith(target) else text

    def read_bytes(self):
        body = real_read_bytes(self)
        return how(body.decode()).encode() if target and str(self).endswith(target) else body

    def is_file(self):
        return False if gone and str(self).endswith(gone) else real_is_file(self)
    Path.read_text, Path.read_bytes, Path.is_file = read_text, read_bytes, is_file
    source = real_read_text(SRC)
    for old, new in (("if (OUT / 'release.json').exists():", 'if False:'),
                     ("    old = json.loads((OLD / 'MANIFEST.json').read_bytes())\n", "    raise RuntimeError('GATES_PASSED')\n"),
                     ("    main()\n", "    pass\n")):
        if source.count(old) != 1:
            raise SystemExit(f'patch point moved: {old!r}')
        source = source.replace(old, new)
    scope = {'__name__': 'gate', '__file__': str(SRC)}
    try:
        exec(compile(source, str(SRC), 'exec'), scope)
        scope['main']()
    except RuntimeError as stop:
        return str(stop)
    except ValueError as refused:
        return str(refused)
    finally:
        Path.read_text, Path.read_bytes, Path.is_file = real_read_text, real_read_bytes, real_is_file
    return 'ran off the end'


def main():
    argv, sys.argv = sys.argv, ['prepare-release.py']
    base = run()
    results = {}
    for name, (target, how, row) in CASES.items():
        said = run(target, how)
        results[name] = {'row': row, 'refused': said.startswith('spec v29 verdicts do not hold') and json.dumps(row) in said}
        if not results[name]['refused']:
            results[name]['said'] = said[:300]
    for name, target in MISSING.items():
        said = run(gone=target)
        results[name] = {'refused': said.startswith('spec v29 evidence missing') and target.split('/')[-1] in said}
        if not results[name]['refused']:
            results[name]['said'] = said[:300]
    sys.argv = argv
    held = [n for n, r in results.items() if not r['refused']]
    report = {'unchanged': base, 'verdict': 'GATE_RED_CASES_HOLD' if base == 'GATES_PASSED' and not held else 'GATE_RED_CASES_FAIL',
              'held': held, 'cases': len(results), 'results': results}
    (OUT / 'gate-red-cases.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('unchanged', 'verdict', 'held', 'cases')}))
    for n in held:
        print(n, results[n].get('said'))
    return 0 if report['verdict'] == 'GATE_RED_CASES_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
