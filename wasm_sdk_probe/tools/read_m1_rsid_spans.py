#!/usr/bin/env python3
"""Fable ruling 1 (v24 pre-count) 2.2 item 2: D-typed-rsid-spans, from M1's native saves.

For every shape x text that M1 typed both through the keyboard (`key`) and through `.uno:InsertText`
(`uno-insert-text`), and every round, read the two after-saves' content.xml and count the
`officeooo:rsid` attributes (any style family: a run typed inside a paragraph gets a text style and a
span; text that replaces a whole cell gets the rsid on the paragraph's automatic style instead), the
text automatic styles carrying one, and the `<text:span` elements.  The claim being
recorded: native Writer saves typed text through .uno:InsertText with the same rsid/span structure
as keyboard typing.  Non-vacuity: every key after-save carries at least one rsid attribute, so
equality is never 0 == 0.  The doc-end `teh` pair (autocorrect, spec L-typed-no-autocorrect) is
reported beside the 16 pairs, not in them.  The before-saves' counts are reported as context.

  python3 -I tools/read_m1_rsid_spans.py <M1 run directory> --output <file>
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

RSID_TEXT_STYLE = re.compile(r'<style:style style:name="[^"]+" style:family="text"[^>]*>(?:(?!</style:style>).)*officeooo:rsid=', re.S)


def counts(path):
    content = zipfile.ZipFile(path).read('content.xml').decode('utf-8')
    return {'rsidAttributes': content.count('officeooo:rsid='), 'rsidTextStyles': len(RSID_TEXT_STYLE.findall(content)),
            'spans': content.count('<text:span'),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = [json.loads(line) for line in (args.run / 'native.jsonl').read_text().splitlines() if line.strip()]
    measured = {(r['id'], r['round']): r for r in records if 'afterFile' in r}
    pairs = {}
    for (arm, rnd), r in measured.items():
        shape, rest = arm.split('/', 1)
        route, text = ('key', rest[4:]) if rest.startswith('key-') else ('uno-insert-text', rest[len('uno-insert-text-'):])
        pairs.setdefault((shape, text), {}).setdefault(rnd, {})[route] = r
    rows, problems = [], []
    for (shape, text), rounds in sorted(pairs.items()):
        for rnd, routes in sorted(rounds.items()):
            if set(routes) != {'key', 'uno-insert-text'}:
                continue
            got = {route: {'after': counts(args.run / 'saves' / r['afterFile']), 'before': counts(args.run / 'saves' / r['beforeFile'])}
                   for route, r in routes.items()}
            key, uno = got['key']['after'], got['uno-insert-text']['after']
            shape_of = lambda c: (c['rsidAttributes'], c['rsidTextStyles'], c['spans'])
            equal = shape_of(key) == shape_of(uno)
            row = {'shape': shape, 'text': text, 'round': rnd, 'key': got['key'], 'unoInsertText': got['uno-insert-text'],
                   'equal': equal, 'autocorrectPair': text == 'teh'}
            rows.append(row)
            if text != 'teh':
                if not equal:
                    problems.append(f'{shape}/{text} r{rnd}: key {key} vs uno {uno}')
                if key['rsidAttributes'] < 1:
                    problems.append(f'{shape}/{text} r{rnd}: key after-save has no rsid attribute (vacuous)')
    main_rows = [r for r in rows if not r['autocorrectPair']]
    pair_count = len({(r['shape'], r['text']) for r in main_rows})
    if pair_count != 16 or len(main_rows) != 48:
        problems.append(f'population differs: {pair_count} pairs, {len(main_rows)} pair-rounds (expected 16, 48)')
    out = {'schema': 1, 'run': str(args.run), 'readerSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'pairs': pair_count, 'pairRounds': len(main_rows), 'equalPairRounds': sum(r['equal'] for r in main_rows),
           'autocorrectPair': [r for r in rows if r['autocorrectPair']], 'problems': problems,
           'verdict': 'SAME_RSID_SPAN_STRUCTURE' if not problems else 'DIFFERS_OR_NOT_ESTABLISHED', 'rows': main_rows}
    args.output.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: out[k] for k in ('verdict', 'pairs', 'pairRounds', 'equalPairRounds', 'problems')}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == '__main__':
    raise SystemExit(main())
