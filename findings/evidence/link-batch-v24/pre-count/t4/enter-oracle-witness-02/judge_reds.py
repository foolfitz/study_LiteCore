#!/usr/bin/env python3
"""Ruling 1 Addendum 1 §3 reds (ii) and (iii) for tools/check_v24_shift_enter.py.

(ii)  the tool's arm judge, end to end, on the four shift-enter-diagnostic-02 Shift-arm after-saves
      (paragraph count before = after, as the Shift arm keeps it) -> PASS x4, v23's paste-shape XML
      included; on v24-1's content.xml with the break removed -> FAIL.
(iii) `--repetitions 0` -> refused before anything runs; a session without CDP -> NOT_ESTABLISHED,
      never PASS (the tool's main() run in-process with open_browser replaced by a CDP-less stub;
      it still builds and serves its mirror, under --out in the scratch directory given).

  python3 -I .../enter-oracle-witness-02/judge_reds.py --scratch <new dir>
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
TOOLS = ROOT / 'wasm_sdk_probe/tools'
sys.path.insert(0, str(TOOLS))
import check_v24_shift_enter as tool  # noqa: E402
import v21_shakedown_common as common  # noqa: E402

DIAG = HERE.parent / 'shift-enter-diagnostic-02'


class NoCdp:
    process = None
    def close(self): pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    rows, checks = [], []
    for name in ('v23-1', 'v23-2', 'v24-1', 'v24-2'):
        content = zipfile.ZipFile(DIAG / f'{name}-SHFTKEYA.odt').read('content.xml').decode('utf-8')
        count = len(tool.paragraph_texts_with_breaks(content))
        rows.append({'case': f'(ii) {name}', **tool.judge(True, 'SHFTKEYA', 'SHFTKEYB', count, content)})
    checks.append(('(ii) the four diagnostic Shift-arm saves judge PASS', [r['outcome'] for r in rows] == ['PASS'] * 4))
    content = zipfile.ZipFile(DIAG / 'v24-1-SHFTKEYA.odt').read('content.xml').decode('utf-8')
    broken = content.replace('<text:line-break/>', '', 1)
    row = {'case': '(ii) v24-1 break removed', **tool.judge(True, 'SHFTKEYA', 'SHFTKEYB', len(tool.paragraph_texts_with_breaks(broken)), broken)}
    rows.append(row)
    checks.append(('(ii) the break removed judges FAIL', row['outcome'] == 'FAIL'))
    zero = subprocess.run([sys.executable, '-I', str(TOOLS / 'check_v24_shift_enter.py'), '--out', str(args.scratch / 'zero'), '--repetitions', '0'],
                          capture_output=True, text=True)
    rows.append({'case': '(iii) --repetitions 0', 'exit': zero.returncode, 'stderrTail': zero.stderr.strip().splitlines()[-1:],
                 'outputCreated': (args.scratch / 'zero').exists()})
    checks.append(('(iii) --repetitions 0 is refused before anything runs', zero.returncode != 0 and not (args.scratch / 'zero').exists()))
    common.open_browser = lambda browser, *a, **k: NoCdp()
    sys.argv = ['check_v24_shift_enter.py', '--out', str(args.scratch / 'no-cdp'), '--repetitions', '1']
    code = tool.main()
    verdict = json.loads((args.scratch / 'no-cdp/report.json').read_text())
    rows.append({'case': '(iii) no CDP', 'exit': code, 'verdict': verdict['verdict'],
                 'fatalTail': (verdict['repetitions'][0].get('fatal') or '').strip().splitlines()[-1:]})
    checks.append(('(iii) a session without CDP is NOT_ESTABLISHED, never PASS', code != 0 and verdict['verdict'] == 'NOT_ESTABLISHED'))
    out = {'rows': rows, 'checks': [{'check': c, 'ok': bool(ok)} for c, ok in checks],
           'verdict': 'REDS_HOLD' if all(ok for _, ok in checks) else 'REDS_DO_NOT_HOLD'}
    (HERE / 'judge-reds.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    for c, ok in checks: print(('ok   ' if ok else 'FAIL ') + c)
    print(out['verdict'])
    return 0 if out['verdict'] == 'REDS_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
