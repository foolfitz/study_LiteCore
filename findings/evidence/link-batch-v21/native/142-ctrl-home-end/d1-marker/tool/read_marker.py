#!/usr/bin/env python3
"""D1 native reference: where the typed marker lands in the saved document.

Usage: python3 -I read_marker.py OUT_DIR FIXTURES_DIR ARMS_JSON_142 OUT_142 [--runs 3]

  OUT_DIR        this folder's out/ (runs.json, population.json, <name>/r<N>.*)
  FIXTURES_DIR   ../../fixtures
  ARMS_JSON_142  ../../out/arms.json (the population is recomputed from it)
  OUT_142        ../../out (the 142 run's own locator, for the cross-check)

PARAGRAPH ORDER (the one reader for every file, native or WASM): every text:p and
text:h element, in XML document order (pre-order), in two parts --
  part "master": under office:master-styles (page headers and footers, in the
                 order the master pages and their header/footer elements are written);
  part "body":   under office:body (table cells row by row, then column by column,
                 as the XML nests them; section and list contents in place).
The index is 0-based within its part. A paragraph's text is its character data
with text:s -> spaces (text:c), text:tab -> \\t, text:line-break -> \\n, and every
other child element's text included in place. The marker offset is a code-point
offset into that text (the marker is ASCII, so it is also the UTF-16 offset).

Exit 1 (red) when any of these fails:
  * population: the IN set recomputed from ARMS_JSON_142 by d1_population.py
    differs from out/population.json, or out/runs.json lacks an IN arm or a control,
    or runs a script other than the one the population gives;
  * completeness: a run file is missing, has a `fatal` record, lacks `done`,
    `typed` or `saved`, the paste returned false, the typed marker is not "Z",
    the saved file is missing or does not parse as XML;
  * the marker: a fixture already contains "Z" anywhere in its text, or a saved
    document does not contain exactly one "Z" (all parts counted);
  * in-process cross-check: the run's own locator (Shift+End / Shift+Home after
    the save) does not read the marker paragraph split right after the marker;
  * agreement: the rounds of a run disagree on (part, index, paragraph text, offset);
  * the 142 cross-check: for a D1 arm, the text before / after the marker differs
    from what the 142 run's locator read at the same point (all its rounds);
  * positive control: a no-Ctrl control lands at the same (part, index, offset)
    as its paired Ctrl arm in any pair of rounds.
"""
import argparse
import difflib
import gzip
import importlib.util
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

MARKER = 'Z'
T = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
O = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'


def para_text(el):
    out = []

    def walk(node):
        if node.text:
            out.append(node.text)
        for ch in node:
            if ch.tag == T + 's':
                out.append(' ' * int(ch.get(T + 'c', '1')))
            elif ch.tag == T + 'tab':
                out.append('\t')
            elif ch.tag == T + 'line-break':
                out.append('\n')
            else:
                walk(ch)
            if ch.tail:
                out.append(ch.tail)
    walk(el)
    return ''.join(out)


def paragraphs(xml_bytes):
    """[(part, index, text)] in the order defined above. Raises on bad XML."""
    root = ET.fromstring(xml_bytes)
    out = []
    for part, tag in (('master', O + 'master-styles'), ('body', O + 'body')):
        node = root.find(tag)
        if node is None:
            continue
        i = 0
        for el in node.iter():
            if el.tag in (T + 'p', T + 'h'):
                out.append((part, i, para_text(el)))
                i += 1
    return out


def compare_rest(base, got):
    """Saved paragraphs with the marker removed vs the fixture's: 'same' or the first difference."""
    a = [f'{p}:{t}' for p, _, t in base]
    b = [f'{p}:{t.replace(MARKER, "")}' for p, _, t in got]
    if a == b:
        return 'same'
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b).get_opcodes():
        if op == 'equal':
            continue
        x = ' / '.join(repr(s.split(':', 1)[1]) for s in a[i1:i2])
        y = ' / '.join(repr(s.split(':', 1)[1]) for s in b[j1:j2])
        if op == 'insert':
            where = f'after {a[i1 - 1].split(":", 1)[1]!r}' if i1 > 0 else 'at the start'
            return f'paragraph {y} added {where} ({len(a)} -> {len(b)} paragraphs)'
        if op == 'delete':
            return f'paragraph {x} gone ({len(a)} -> {len(b)} paragraphs)'
        return f'{x} -> {y}'
    return 'differs'


def load_population_module():
    path = pathlib.Path(__file__).resolve().parent / 'd1_population.py'
    spec = importlib.util.spec_from_file_location('d1_population', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('fixtures')
    ap.add_argument('arms142')
    ap.add_argument('out142')
    ap.add_argument('--runs', type=int, default=3)
    a = ap.parse_args()
    out, fixtures, out142 = pathlib.Path(a.out), pathlib.Path(a.fixtures), pathlib.Path(a.out142)
    problems = []

    # population
    pop_mod = load_population_module()
    arms142 = json.loads(pathlib.Path(a.arms142).read_text())
    ins, _outs, errors = pop_mod.classify(arms142)
    if errors or not ins:
        problems.append(f'population recomputation is red: {errors or "zero IN"}')
    pop = json.loads((out / 'population.json').read_text())
    if [x['name'] for x in ins] != [x['name'] for x in pop['in']]:
        problems.append('population.json IN set differs from the recomputed one')
    want = {x['name']: x['d1Script'] for x in ins}
    runs = json.loads((out / 'runs.json').read_text())
    have = {x['name']: x for x in runs}
    for name, script in want.items():
        if name not in have:
            problems.append(f'{name}: IN arm not in runs.json')
        elif have[name]['script'] != script:
            problems.append(f'{name}: runs.json script {have[name]["script"]!r} != population {script!r}')
    controls = [x for x in runs if x['role'] == 'control']
    if not controls:
        problems.append('runs.json has no control')
    for c in controls:
        src = next((x for x in ins if x['name'] == c['pairedWith']), None)
        if not src or c['script'] != src['noCtrlScript']:
            problems.append(f'{c["name"]}: script is not the no-Ctrl variant of {c["pairedWith"]}')

    # fixtures
    base = {}
    for fx in sorted({x['fixture'] for x in runs}):
        paras = paragraphs((fixtures / f'{fx}.fodt').read_bytes())
        n = sum(t.count(MARKER) for _, _, t in paras)
        if n:
            problems.append(f'fixture {fx} already contains {n} x {MARKER!r}')
        base[fx] = paras

    # per run
    results = {}
    for x in runs:
        name = x['name']
        per = []
        for r in range(1, a.runs + 1):
            jp = out / name / f'r{r}.jsonl'
            if not jp.exists():
                problems.append(f'{name} r{r}: missing {jp.name}')
                continue
            recs = [json.loads(line) for line in jp.read_text().splitlines() if line.strip()]
            kinds = [y['rec'] for y in recs]
            if 'fatal' in kinds or 'done' not in kinds or 'typed' not in kinds or 'saved' not in kinds:
                problems.append(f'{name} r{r}: fatal, or no done/typed/saved record')
                continue
            typed = next(y for y in recs if y['rec'] == 'typed')
            saved = next(y for y in recs if y['rec'] == 'saved')
            loc = next((y for y in recs if y['rec'] == 'locate'), None)
            if typed['marker'] != MARKER or not typed['pasteOk']:
                problems.append(f'{name} r{r}: typed marker {typed["marker"]!r}, pasteOk {typed["pasteOk"]}')
                continue
            gz = out / name / f'r{r}.fodt.gz'
            if not saved['ok'] or not gz.exists():
                problems.append(f'{name} r{r}: save failed or file missing')
                continue
            try:
                paras = paragraphs(gzip.decompress(gz.read_bytes()))
            except Exception as e:  # noqa: BLE001 -- any read failure is red, with its message
                problems.append(f'{name} r{r}: saved file unreadable: {type(e).__name__}: {e}')
                continue
            hits = [(p, i, t, off) for p, i, t in paras for off in range(len(t)) if t[off] == MARKER]
            if len(hits) != 1:
                problems.append(f'{name} r{r}: {len(hits)} markers in the saved document: {hits}')
                continue
            part, idx, text, off = hits[0]
            if loc is None or loc['selBefore'] != '' or loc['prefix'] != text[:off + 1] \
                    or loc['suffix'] != text[off + 1:]:
                problems.append(f'{name} r{r}: in-process locator {loc and (loc["prefix"], loc["suffix"])!r} '
                                f'does not split {text!r} right after the marker')
            undo = ''
            try:
                acts = json.loads(typed['undoAfter']).get('actions') or []
                undo = acts[0].get('comment', '?') if acts else ''
            except Exception:  # noqa: BLE001
                undo = '<unparsable>'
            per.append({'part': part, 'index': idx, 'text': text, 'offset': off,
                        'rest': compare_rest(base[x['fixture']], paras),
                        'selBefore': typed['selTextBefore'], 'undoChanged': typed['undoChanged'], 'undoTop': undo})
        results[name] = per

    # agreement
    agree = {}
    for x in runs:
        per = results[x['name']]
        keys = [json.dumps([y['part'], y['index'], y['text'], y['offset']]) for y in per]
        same = max((keys.count(k) for k in keys), default=0)
        agree[x['name']] = f'{same}/{a.runs}'
        if len(per) != a.runs or same != a.runs:
            problems.append(f'{x["name"]}: rounds disagree or incomplete ({same}/{a.runs}, {len(per)} complete)')

    # 142 cross-check: the 142 run's locator after the same last press
    cross = {}
    for x in runs:
        if x['role'] != 'D1':
            continue
        seen = set()
        for r in range(1, a.runs + 1):
            p = out142 / x['name'] / f'r{r}.jsonl'
            if not p.exists():
                continue
            loc = next((y for y in map(json.loads, filter(str.strip, p.read_text().splitlines()))
                        if y['rec'] == 'locate'), None)
            if loc:
                seen.add((loc['prefix'], loc['suffix']))
        mine = {(y['text'][:y['offset']], y['text'][y['offset'] + 1:]) for y in results[x['name']]}
        ok = len(seen) == 1 and mine == seen
        cross[x['name']] = 'agrees' if ok else f'DIFFERS: 142 {sorted(seen)} vs D1 {sorted(mine)}'
        if not ok:
            problems.append(f'{x["name"]}: marker landing differs from the 142 locator: {cross[x["name"]]}')

    # positive controls
    ctl_lines = []
    for c in controls:
        mine = {(y['part'], y['index'], y['offset']) for y in results[c['name']]}
        theirs = {(y['part'], y['index'], y['offset']) for y in results.get(c['pairedWith'], [])}
        ok = bool(mine) and bool(theirs) and not (mine & theirs)
        ctl_lines.append(f'- control `{c["name"]}` (placement of `{c["pairedWith"]}`, no Ctrl press): '
                         f'{sorted(mine)} vs `{c["pairedWith"]}` {sorted(theirs)}: '
                         f'{"DIFFERENT (OK)" if ok else "NOT DIFFERENT (FAILED)"}')
        if not ok:
            problems.append(f'positive control {c["name"]} failed: lands where {c["pairedWith"]} lands')

    # table
    print('| run | role | rounds agree | fixture | part | paragraph index | offset | paragraph text with the marker '
          '| same as the 142 locator | rest of the document vs the fixture | Undo top after the paste |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for x in runs:
        per = results[x['name']]
        if not per:
            print(f'| {x["name"]} | {x["role"]} | {agree[x["name"]]} | {x["fixture"]} | | | | | | | |')
            continue
        y = per[0]
        shown = y['text'][:y['offset']] + '[Z]' + y['text'][y['offset'] + 1:]
        cells = [x['name'], x['role'] if x['role'] == 'D1' else f'control for {x["pairedWith"]}',
                 agree[x['name']], x['fixture'], y['part'], y['index'], y['offset'], f'«{shown}»',
                 cross.get(x['name'], '-'), y['rest'], y['undoTop']]
        print('| ' + ' | '.join(str(c).replace('|', '\\|') for c in cells) + ' |')
    print()
    print('Positive controls')
    print()
    for line in ctl_lines:
        print(line)
    sels = sorted({(x['name'], y['selBefore']) for x in runs for y in results[x['name']] if y['selBefore']})
    print()
    print(f'Selection non-empty right before the paste: {sels if sels else "none, in every run"}')
    print()
    if problems:
        print('RED:')
        for p in problems:
            print(f'- {p}')
        return 1
    n_d1 = sum(1 for x in runs if x['role'] == 'D1')
    print(f'GREEN: {n_d1} D1 arms + {len(controls)} controls x {a.runs} rounds; every run {a.runs}/{a.runs}; '
          f'exactly one marker per saved document; in-process locator and the 142 locator agree; controls differ')
    return 0


if __name__ == '__main__':
    sys.exit(main())
