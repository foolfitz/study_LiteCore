#!/usr/bin/env python3
"""Fable ruling 1 (v24 pre-count) 2.4: the Enter check's Shift-arm oracle, old against new (E1).

Old oracle: the expression E1 replaced (tools/run_e2_c_product_path.py before E1, lines 8724-8726,
with its nested `paragraphs_of`), copied here verbatim in substance.  New oracle: the E1 function
`paragraph_texts_with_breaks`, imported from the live runner.  Positive controls: the four
shift-enter-diagnostic-02/*-SHFTKEYA.odt saves.  Negative controls: scratch copies of v24-1's
content.xml with the break removed (n1), turned into a paragraph split (n2), turned into a tab (n3),
or followed by other text (n4).  Writes results.json beside this file.
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
from run_e2_c_product_path import paragraph_texts_with_breaks  # noqa: E402

FIRST, SECOND = 'SHFTKEYA', 'SHFTKEYB'
DIAG = HERE.parent / 'shift-enter-diagnostic-02'


def paragraphs_of(content):
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return []
    return [''.join(node.itertext()) for node in root.iter() if node.tag.split('}')[-1] in ('p', 'h')]


def old(content):
    return any(FIRST in p and SECOND in p for p in paragraphs_of(content)) and f'{FIRST}<text:line-break/>{SECOND}' in content


def new(content):
    return any(f'{FIRST}\n{SECOND}' in t for t in paragraph_texts_with_breaks(content))


def main():
    rows, checks = [], []
    positives = {}
    for name in ('v23-1', 'v23-2', 'v24-1', 'v24-2'):
        raw = (DIAG / f'{name}-SHFTKEYA.odt').read_bytes()
        positives[name] = zipfile.ZipFile(DIAG / f'{name}-SHFTKEYA.odt').read('content.xml').decode('utf-8')
        rows.append({'control': f'positive {name}', 'odtSha256': hashlib.sha256(raw).hexdigest(),
                     'old': old(positives[name]), 'new': new(positives[name])})
    checks.append(('old oracle on the four positives is True, True, False, False (the red before E1)',
                   [r['old'] for r in rows] == [True, True, False, False]))
    checks.append(('new oracle on the four positives is True x4', [r['new'] for r in rows] == [True] * 4))
    base = positives['v24-1']
    seam = '<text:line-break/></text:span>'
    if base.count(seam) != 1:
        raise SystemExit('v24-1 does not have the one break-at-span-end the negatives mutate')
    negatives = {
        'n1 break removed': base.replace('<text:line-break/>', '', 1),
        'n2 paragraph split': base.replace(seam, '</text:span></text:p><text:p text:style-name="P2">', 1),
        'n3 tab instead': base.replace('<text:line-break/>', '<text:tab/>', 1),
        'n4 text after the break': base.replace('<text:line-break/>', '<text:line-break/>QQ', 1),
    }
    for name, content in negatives.items():
        texts = paragraph_texts_with_breaks(content)
        parsed = bool(texts) and any(FIRST in t for t in texts) and any(SECOND in t for t in texts)
        rows.append({'control': f'negative {name}', 'parsedWithBothMarkers': parsed, 'old': old(content), 'new': new(content),
                     'paragraphs': [t for t in texts if FIRST in t or SECOND in t]})
        checks.append((f'{name}: parses, both markers present, new oracle False', parsed and not new(content)))
    out = {'runner': 'wasm_sdk_probe/tools/run_e2_c_product_path.py',
           'runnerSha256': hashlib.sha256((ROOT / 'wasm_sdk_probe/tools/run_e2_c_product_path.py').read_bytes()).hexdigest(),
           'rows': rows, 'checks': [{'check': c, 'ok': bool(ok)} for c, ok in checks],
           'verdict': 'CONTROLS_HOLD' if all(ok for _, ok in checks) else 'CONTROLS_DO_NOT_HOLD'}
    (HERE / 'results.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    for c, ok in checks: print(('ok   ' if ok else 'FAIL ') + c)
    print(out['verdict'])
    return 0 if out['verdict'] == 'CONTROLS_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
