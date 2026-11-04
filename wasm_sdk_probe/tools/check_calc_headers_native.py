#!/usr/bin/env python3
"""SPEC-P-calc-headers 4.1: N-H1..N-H3 (and N-H4's timings) on the native 26.8 core, with the spec's three red cases and the
control build (no OXSDK_ODS_HEADERS).  The harness is tools/calc_undo_native.cpp built by tools/build_calc_undo_native.py from
the bridge source that will be linked.  A fresh fixture (tools/create_calc_headers_fixture.py) per harness session.

  check_calc_headers_native.py --harness BUILD/headers/calc-undo-native --control BUILD/v5/calc-undo-native --out NEW_DIR

Verdict N_HOLDS iff the fixture reads back as built, N-H1, N-H2 and N-H3 hold, every red case is red in its own cell, and the
control refuses op 13 and the whole-column write.  Every request and reply is kept (observations-*.jsonl).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SDK = Path(__file__).resolve().parents[1]
ROOT = SDK.parent
CORE = ROOT / 'build-native-26-8/instdir/program'
sys.path.insert(0, str(SDK / 'tools'))
from create_calc_headers_fixture import create  # noqa: E402

MAX_COLUMNS, MAX_ROWS = 16384, 1048576
RECTANGLES = {  # twips: x, y, width, height
    'top-left': (0, 0, 15000, 6000), 'middle': (4410, 1095, 9000, 4000), 'row-1000': (0, 254000, 15000, 6000),
    'columns-only': (0, 0, 15000, 0), 'rows-only': (0, 0, 0, 6000), 'past-z': (22500, 0, 15000, 3000)}
HIDDEN = {'columns': {3}, 'rows': {3}}
OLD_REPLY = ROOT / 'findings/evidence/m4-cell-editing/native/geometry-discovery/observations.jsonl'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def letters(index):
    out = ''
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        out = chr(65 + rest) + out
    return out


class Harness:
    def __init__(self, binary, out, name):
        self.name, self.log = name, (out / f'observations-{name}.jsonl').open('w')
        directory = out / f'session-{name}'
        directory.mkdir()
        self.fixture = create(directory / 'fixture')
        profile = directory / 'profile'
        profile.mkdir()
        self.proc = subprocess.Popen([str(binary), str(CORE), profile.as_uri(), self.fixture.as_uri()], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=(directory / 'stderr.txt').open('w'), text=True,
                                     env={**os.environ, 'SAL_USE_VCLPLUGIN': 'svp'})

    def send(self, request):
        started = time.monotonic()
        self.proc.stdin.write(json.dumps(request, ensure_ascii=False) + '\n'); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        ms = round((time.monotonic() - started) * 1000, 3)
        try:
            reply = json.loads(line)
        except json.JSONDecodeError:
            reply = {'unparsed': line}
        self.log.write(json.dumps({'request': request, 'ms': ms, 'reply': reply}, ensure_ascii=False) + '\n')
        return reply, ms

    def cell(self, operation, column, row, part=0, text='', enabled=0):
        return self.send({'operation': operation, 'part': part, 'column': column, 'row': row, 'text': text, 'enabled': enabled})

    def cursor(self):
        return self.send({'action': 'command-values', 'command': '.uno:CellCursor'})[0].get('commandValues')

    def headers(self, rect, part=0):
        x, y, w, h = rect
        return self.cell(13, 0, 0, part, json.dumps({'x': x, 'y': y, 'width': w, 'height': h}))

    def range(self, operation, column, row, end_column, end_row, part=0, enabled=0):
        return self.cell(operation, column, row, part, json.dumps({'endColumn': end_column, 'endRow': end_row}), enabled)

    def bold(self, column, row, part=0):
        reply, _ = self.range(6, column, row, column, row, part)
        return reply.get('bold')

    def close(self):
        self.proc.stdin.close()
        code = self.proc.wait(timeout=60)
        self.log.close()
        return code


def entries(reply, axis):
    value = reply.get(axis)
    return [] if value in ('', None) else value


def shape_ok(reply):
    """3.1's closed shape: indices contiguous, startPx <= endPx, each entry starts where the previous ended, hidden iff empty."""
    for axis in ('columns', 'rows'):
        previous = None
        for e in entries(reply, axis):
            index, start, end = int(e['index']), int(e['startPx']), int(e['endPx'])
            if start > end or (e['hidden'] == 'true') != (start == end):
                return False
            if previous and (index != previous[0] + 1 or start != previous[1]):
                return False
            previous = (index, end)
    return str(reply.get('maxColumns')) == str(MAX_COLUMNS) and str(reply.get('maxRows')) == str(MAX_ROWS)


def aligned(h, reply):
    """Each visible header against op 0's cursor geometry: start x 15 = x/yTwips, (end - start) x 15 - 1 = width/heightTwips."""
    cells = []
    for axis in ('columns', 'rows'):
        for e in entries(reply, axis):
            index, start, end = int(e['index']), int(e['startPx']), int(e['endPx'])
            if start == end:
                cells.append({'axis': axis, 'index': index, 'hidden': True, 'expectedHidden': index in HIDDEN[axis],
                              'ok': index in HIDDEN[axis]})
                continue
            cell, _ = h.cell(0, index, 0) if axis == 'columns' else h.cell(0, 0, index)
            pos, size = ('xTwips', 'widthTwips') if axis == 'columns' else ('yTwips', 'heightTwips')
            got = (int(cell.get(pos, -1)), int(cell.get(size, -1)))
            want = (start * 15, (end - start) * 15 - 1)
            label_ok = e['label'] == (letters(index) if axis == 'columns' else str(index + 1))
            cells.append({'axis': axis, 'index': index, 'label': e['label'], 'got': got, 'want': want,
                          'ok': got == want and label_ok and index not in HIDDEN[axis]})
    return cells


def normalise_core(raw):
    """The bridge's headerEntries in Python, for red case (c) only: a raw core reply to the bridge's shape."""
    out = {'maxColumns': str(MAX_COLUMNS), 'maxRows': str(MAX_ROWS)}
    for axis in ('columns', 'rows'):
        items, rows, first, previous = raw[axis], [], True, None
        for item in items:
            if first:
                previous, first = (int(item['text']) - 1, int(item['size'])), False
                continue
            index = previous[0] + 1
            rows.append({'index': str(index), 'label': item['text'], 'startPx': str(previous[1]), 'endPx': str(item['size']),
                         'hidden': 'true' if item['size'] == previous[1] else 'false'})
            previous = (index, int(item['size']))
        out[axis] = rows
    return out


def whole_targets():
    targets = [{'id': f'column-{letters(c)}', 'range': (c, 0, c, MAX_ROWS - 1),
                'reads': [(c, 0), (c, 999), (c, MAX_ROWS - 1)]} for c in (0, 1, 2, 3, 4, 5, 26)]
    targets += [{'id': f'row-{r + 1}', 'range': (0, r, MAX_COLUMNS - 1, r),
                 'reads': [(0, r), (4, r), (MAX_COLUMNS - 1, r)]} for r in (0, 2, 999)]
    targets.append({'id': 'sheet', 'range': (0, 0, MAX_COLUMNS - 1, MAX_ROWS - 1),
                    'reads': [(0, 0), (2, 2), (MAX_COLUMNS - 1, MAX_ROWS - 1)]})
    return targets


def write_whole(h, target):
    c, r, ec, er = target['range']
    reply, ms = h.range(7, c, r, ec, er, enabled=1)
    after = [h.bold(*cell) for cell in target['reads']]
    if reply.get('ok') != 'true':  # refused: nothing to undo, and an undo would revert something else
        undo, undone = {}, []
    else:
        undo, _ = h.send({'action': 'uno-wait', 'command': '.uno:Undo', 'timeoutMs': 10000})
        undone = [h.bold(*cell) for cell in target['reads']]
    ok = (reply.get('ok') == 'true' and reply.get('changed') == 'true' and all(b == 'on' for b in after)
          and undo.get('resultCame') is True and all(b == 'off' for b in undone))
    return {'id': target['id'], 'range': target['range'], 'reply': {k: reply.get(k) for k in ('ok', 'code', 'changed', 'bold')},
            'ms': ms, 'boldAfter': after, 'boldAfterUndo': undone, 'undoResultCame': undo.get('resultCame'), 'ok': ok}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'tool': {'path': 'wasm_sdk_probe/tools/check_calc_headers_native.py', 'sha256': sha(__file__), 'argv': sys.argv[1:]},
              'harness': {'path': str(args.harness), 'sha256': sha(args.harness)},
              'control': {'path': str(args.control), 'sha256': sha(args.control)},
              'bridgeSourceSha256': sha(SDK / 'src/calc_cell_bridge.cpp'), 'uptime': subprocess.check_output(['uptime'], text=True).strip()}

    h = Harness(args.harness, out, 'headers')
    report['fixtureSha256'] = sha(h.fixture)
    # Precondition: the fixture through the instrument's own path.
    want = json.loads((h.fixture.parent / 'manifest.json').read_text())['expected']['cells']
    seen = [{'cell': (c['column'], c['row']), 'want': c['text'], 'got': h.cell(0, c['column'], c['row'])[0].get('text')} for c in want]
    report['fixture'] = {'cells': seen, 'ok': all(s['got'] == s['want'] for s in seen)}

    nh1 = []
    for name, rect in RECTANGLES.items():
        before = h.cursor()
        reply, ms = h.headers(rect)
        after = h.cursor()
        row = {'rect': name, 'ms': ms, 'ok_reply': reply.get('ok') == 'true', 'cursorBefore': before, 'cursorAfter': after,
               'cursorUnchanged': before == after, 'shape': reply.get('ok') == 'true' and shape_ok(reply),
               'columns': len(entries(reply, 'columns')), 'rows': len(entries(reply, 'rows'))}
        row['cells'] = aligned(h, reply) if row['shape'] else []
        row['ok'] = row['ok_reply'] and row['cursorUnchanged'] and row['shape'] and bool(row['cells']) and all(c['ok'] for c in row['cells'])
        nh1.append(row)
    report['N-H1'] = {'rows': nh1, 'holds': all(r['ok'] for r in nh1)}

    nh2 = [write_whole(h, t) for t in whole_targets()]
    report['N-H2'] = {'rows': nh2, 'holds': all(r['ok'] for r in nh2)}

    protected, _ = h.range(7, 0, 0, 0, MAX_ROWS - 1, part=2, enabled=1)
    too_large, _ = h.range(7, 0, 0, 1, 39999, enabled=1)
    merge, _ = h.range(7, 0, 2, 0, 2, enabled=1)
    nh3 = [{'id': 'protected-whole-column', 'code': protected.get('code'), 'boldAfter': h.bold(0, 0, part=2),
            'ok': protected.get('code') == 'READ_ONLY'},
           {'id': 'non-whole-80000-cells', 'code': too_large.get('code'), 'ok': too_large.get('code') == 'RANGE_TOO_LARGE'},
           {'id': 'non-whole-across-merge', 'code': merge.get('code'), 'ok': merge.get('code') == 'RANGE_MERGE_BOUNDARY'}]
    nh3[0]['ok'] = nh3[0]['ok'] and nh3[0]['boldAfter'] == 'off'
    column_a = next(r for r in nh2 if r['id'] == 'column-A')
    a3 = h.range(7, 0, 0, 0, MAX_ROWS - 1, enabled=1)[0]
    a3_bold = h.bold(0, 2)
    h.send({'action': 'uno-wait', 'command': '.uno:Undo', 'timeoutMs': 10000})
    nh3.append({'id': 'whole-column-A-through-A3:B3', 'code': a3.get('code'), 'a3Bold': a3_bold,
                'ok': a3.get('ok') == 'true' and a3_bold == 'on' and column_a['ok']})
    report['N-H3'] = {'rows': nh3, 'holds': all(r['ok'] for r in nh3)}

    # N-H4: timings, registered (not a criterion).
    report['N-H4'] = {'op13Ms': [r['ms'] for r in nh1], 'wholeMs': {r['id']: r['ms'] for r in nh2}}

    # Red cases: each must turn its own cell red.
    before = h.cursor(); h.cell(0, 2, 1); after = h.cursor()
    red_a = {'case': 'op 0 in place of op 13 for "the cursor does not move"', 'cursorUnchanged': before == after}
    red_a['red'] = not red_a['cursorUnchanged']
    short = dict(whole_targets()[2]); short['id'] = 'column-C-endRow-maxRows-2'; short['range'] = (2, 0, 2, MAX_ROWS - 2)
    red_b = write_whole(h, short)
    red_b = {'case': 'whole column with endRow = maxRows - 2', 'code': red_b['reply'].get('code'), 'red': not red_b['ok']}
    old = json.loads(OLD_REPLY.read_text().splitlines()[0])
    h.cell(0, 0, 0)  # the bridge's zoom, as for N-H1
    old_cells = aligned(h, normalise_core(old))
    red_c = {'case': 'the pre-zoom core reply (A = 110 px) against the cursor', 'mismatched': [c for c in old_cells if not c['ok']][:3]}
    red_c['red'] = any(not c['ok'] and c['axis'] == 'columns' for c in old_cells)
    report['redCases'] = [red_a, red_b, red_c]
    report['headersExit'] = h.close()

    c = Harness(args.control, out, 'control')
    op13, _ = c.headers(RECTANGLES['top-left'])
    whole, _ = c.range(7, 2, 0, 2, MAX_ROWS - 1, enabled=1)
    report['control'] = {'op13Code': op13.get('code'), 'wholeColumnCode': whole.get('code'),
                         'ok': op13.get('code') == 'INVALID_ARGUMENT' and whole.get('code') == 'RANGE_TOO_LARGE'}
    report['controlExit'] = c.close()

    report['verdict'] = 'N_HOLDS' if (report['fixture']['ok'] and report['N-H1']['holds'] and report['N-H2']['holds']
                                      and report['N-H3']['holds'] and all(r['red'] for r in report['redCases'])
                                      and report['control']['ok'] and report['headersExit'] == 0) else 'N_RED'
    (out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'fixture': report['fixture']['ok'], 'N-H1': report['N-H1']['holds'],
                      'N-H2': report['N-H2']['holds'], 'N-H3': report['N-H3']['holds'], 'reds': [r['red'] for r in report['redCases']],
                      'control': report['control']}, ensure_ascii=False))
    return 0 if report['verdict'] == 'N_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
