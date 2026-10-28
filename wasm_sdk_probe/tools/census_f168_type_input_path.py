#!/usr/bin/env python3
"""Type-route ruling M0: does every retained S5 type cell's x reach the engine through the sink's
beforeinput (the input adapter's source "beforeinput"), not a direct commitText or a paste?

Read-only over retained raw cell JSON.  Per cell, after the last trusted Shift keydown on the sink:
exactly one trusted keydown "x", exactly one trusted beforeinput insertText data "x", no paste-type
input, and exactly one insertText request with text "x" posted after that beforeinput.  The census
refuses (exit 1) when it reads zero cells or any cell lacks the shape.

Usage: census_f168_type_input_path.py DIR [DIR ...] --output FRESH.json
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cell_shape(page):
    inputs = page['inputs']
    shifts = [i for i, e in enumerate(inputs) if e['type'] == 'keydown' and e.get('shiftKey') and e.get('isTrusted')]
    if not shifts:
        return ['no trusted Shift keydown']
    tail = inputs[shifts[-1]:]
    problems = []
    keydowns = [e for e in tail if e['type'] == 'keydown' and e.get('key') == 'x']
    before = [e for e in tail if e['type'] == 'beforeinput']
    if len(keydowns) != 1 or not keydowns[0].get('isTrusted'):
        problems.append(f'{len(keydowns)} keydown x after Shift')
    if len(before) != 1 or before[0].get('inputType') != 'insertText' or before[0].get('data') != 'x' \
            or not before[0].get('isTrusted'):
        problems.append('beforeinput after Shift: ' + json.dumps([(e.get('inputType'), e.get('data'), e.get('isTrusted')) for e in before]))
    if any((e.get('inputType') or '').startswith('insertFromPaste') for e in tail):
        problems.append('paste input after Shift')
    if before:
        at = before[0]['at']
        inserts = [r for r in page['requests'] if r['message'].get('operation') == 'insertText' and r.get('at', -1) >= at]
        if len(inserts) != 1 or inserts[0]['message'].get('payload', {}).get('text') != 'x':
            problems.append(f'{len(inserts)} insertText requests after the beforeinput')
    return problems


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dirs', nargs='+', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output must be fresh')
    cells, failures = [], []
    for d in a.dirs:
        for f in sorted(d.glob('*__type.json')):
            page = json.loads(f.read_text())['page']
            problems = cell_shape(page)
            cells.append({'file': f'{d.name}/{f.name}', 'sha256': sha(f), 'problems': problems})
            if problems:
                failures.append(cells[-1])
    by_browser = {}
    for c in cells:
        b = c['file'].split('/')[1].split('-')[0]
        by_browser.setdefault(b, [0, 0])[0 if not c['problems'] else 1] += 1
    result = {'schema': 1, 'censusSha256': sha(Path(__file__)), 'cells': len(cells),
              'byBrowser': {b: {'beforeinputPath': v[0], 'other': v[1]} for b, v in by_browser.items()},
              'failures': failures, 'records': cells}
    a.output.write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({k: result[k] for k in ('cells', 'byBrowser')} | {'failures': len(failures)}))
    return 1 if not cells or failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
