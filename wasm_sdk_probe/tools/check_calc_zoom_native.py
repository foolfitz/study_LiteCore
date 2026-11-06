#!/usr/bin/env python3
"""SPEC-P-calc-zoom 4.1: N-Z1..N-Z6 (and N-Z7's timings) on the native 26.8 core, with the spec's red case and the control build
(v7's defines, no OXSDK_ODS_ZOOM).  The harness is tools/calc_undo_native.cpp (its "paint" action) built by
tools/build_calc_undo_native.py from the bridge source that will be linked, on tools/create_calc_structure_fixture.py's fixture.

The levels are the bridge's closed list (kTileTwips in src/calc_cell_bridge.cpp, read here), so a level added there is judged
without editing this tool.  Red box: the bounding box of red pixels (R>200, G<60, B<60 in the core's BGRA) on a 512x512 canvas of
2T x 2T twips, aligned to the 256-px tile grid at the reported box's top-left.  Reported box: op 0's rectangle x 256 / T, minus the
canvas origin.  N-Z1 (spec append 1): the red box's top and left are the reported top and left minus 1 (the fill covers the
grid line above and to the left), its right and bottom are the reported ones, each within 0.5 px.  Op 16 goes to the sheet the
last read was on, so the active sheet does not move under N-Z5's cursor read.

  check_calc_zoom_native.py --harness BUILD/v8/calc-undo-native --control BUILD/v7/calc-undo-native --out NEW_DIR

Verdict N_HOLDS iff N-Z1..N-Z6 hold, the red case is red in N-Z1's cell at every level but 100 and 200, and the control refuses
op 16.  Every request and reply is kept (observations-*.jsonl); every canvas is kept (tile-*.bgra).
"""
import argparse
import json
from pathlib import Path
import re
import sys

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import check_calc_headers_native as hn  # noqa: E402
from check_calc_copy_native import Session  # noqa: E402

BRIDGE = SDK / 'src/calc_cell_bridge.cpp'
TARGETS = (('F100', 0, 5, 99), ('AA1000', 0, 26, 999), ('C30', 1, 2, 29))  # name, part, column, row
RED = '#ff0000'
CANVAS = 512


def levels():
    found = re.findall(r'constexpr int kTileTwips\[\] = \{([0-9, ]+)\};', BRIDGE.read_text())
    if len(found) != 1:
        raise SystemExit('kTileTwips is not one closed list in the bridge')
    return sorted((int(v) for v in found[0].split(',')), reverse=True)  # 50% first


def zoom(s, tile_twips, part=0):
    return s.cell(16, 0, 0, part, json.dumps({'tileTwips': tile_twips}))


def rect(s, part, column, row):
    reply, _ = s.cell(0, column, row, part)
    return [int(reply[k]) for k in ('xTwips', 'yTwips', 'widthTwips', 'heightTwips')]


def red_box(path):
    data = path.read_bytes()
    xs, ys = [], []
    for y in range(CANVAS):
        row = y * CANVAS * 4
        for x in range(CANVAS):
            i = row + x * 4
            if data[i + 2] > 200 and data[i + 1] < 60 and data[i] < 60:
                xs.append(x)
                ys.append(y)
    return [min(xs), min(ys), max(xs) + 1, max(ys) + 1] if xs else None


def aligned(box, reported):
    want = [reported[0] - 1, reported[1] - 1, reported[2], reported[3]]
    return box is not None and all(abs(a - b) <= 0.5 for a, b in zip(box, want))


def run(binary, out):
    s = Session(binary, out, 'z')
    for _, part, column, row in TARGETS:
        s.cell(11, column, row, part, json.dumps({'endColumn': column, 'endRow': row, 'value': RED}))
    undo_before = s.undo_count()
    size = lambda reply: [reply.get('widthTwips'), reply.get('heightTwips')]
    # N-Z4's size (spec append 1): zoom only, before any read moves the cursor and stretches the core's area.
    first, _ = zoom(s, 3840)
    sizes = {384000 // t: size(zoom(s, t)[0]) for t in levels()}
    first_back, _ = zoom(s, 3840)
    rect0 = {name: rect(s, part, column, row) for name, part, column, row in TARGETS}
    current = TARGETS[-1][1]
    record = {'N-Z1': {}, 'N-Z2': {}, 'N-Z3': {}, 'red': {}, 'N-Z5': {'levels': {}}, 'N-Z7': {}}
    changed = [first.get('changed'), first_back.get('changed')]
    for tile_twips in levels():
        percent = 384000 // tile_twips
        cursor_before = s.cursor()
        reply, ms = zoom(s, tile_twips, current)
        cursor_after = s.cursor()
        changed.append(reply.get('changed'))
        record['N-Z7'][percent] = ms
        record['N-Z5']['levels'][percent] = {'cursorBefore': cursor_before, 'cursorAfter': cursor_after,
                                             'reply': {k: reply.get(k) for k in ('ok', 'tileTwips', 'percent', 'widthTwips',
                                                                                 'heightTwips', 'changed')}}
        for name, part, column, row in TARGETS:
            r = rect(s, part, column, row)
            current = part
            px = [v * 256 / tile_twips for v in r]
            ox, oy = int(px[0] // 256) * 256, int(px[1] // 256) * 256
            canvas = out / f'tile-{percent}-{name}.bgra'
            s.send({'action': 'paint', 'width': CANVAS, 'height': CANVAS, 'x': ox * tile_twips // 256,
                    'y': oy * tile_twips // 256, 'tileWidth': 2 * tile_twips, 'tileHeight': 2 * tile_twips, 'file': str(canvas)})
            box = red_box(canvas)
            reported = [px[0] - ox, px[1] - oy, px[0] + px[2] - ox, px[1] + px[3] - oy]
            scale = percent / 100
            at100 = [v / 15 * scale for v in rect0[name]]
            old = [at100[0] - ox, at100[1] - oy, at100[0] + at100[2] - ox, at100[1] + at100[3] - oy]
            key = f'{percent}/{name}'
            record['N-Z1'][key] = {'rectTwips': r, 'redBox': box, 'reported': [round(v, 3) for v in reported],
                                   'ok': aligned(box, reported)}
            record['red'][key] = {'reportedFrom100': [round(v, 3) for v in old], 'aligned': aligned(box, old)}
            hit, _ = s.cell(5, round(r[0] + r[2] / 2), round(r[1] + r[3] / 2), part)
            record['N-Z3'][key] = {'column': hit.get('column'), 'row': hit.get('row'),
                                   'ok': hit.get('column') == str(column) and hit.get('row') == str(row)}
            if part == 0:
                headers, _ = s.headers((r[0], r[1], r[2] + 30, r[3] + 30), part)
                col = [e for e in hn.entries(headers, 'columns') if e['index'] == str(column)]
                row_entry = [e for e in hn.entries(headers, 'rows') if e['index'] == str(row)]
                edges = ([int(col[0]['startPx']), int(col[0]['endPx'])] if col else None,
                         [int(row_entry[0]['startPx']), int(row_entry[0]['endPx'])] if row_entry else None)
                want = ([px[0], px[0] + px[2]], [px[1], px[1] + px[3]])
                record['N-Z2'][key] = {'column': edges[0], 'row': edges[1], 'want': [[round(v, 3) for v in w] for w in want],
                                       'ok': all(e is not None and all(abs(a - b) <= 1 for a, b in zip(e, w))
                                                 for e, w in zip(edges, want))}
    back, _ = zoom(s, 3840, current)
    changed.append(back.get('changed'))
    rect_back = {name: rect(s, part, column, row) for name, part, column, row in TARGETS}
    record['N-Z4'] = {'rects': rect0, 'rectsBack': rect_back, 'size': size(first), 'sizes': sizes, 'sizeBack': size(first_back),
                      'ok': rect_back == rect0 and size(first_back) == size(first) and first.get('ok') == 'true'}
    undo_after = s.undo_count()
    cell_of = lambda cursor: (cursor or '').split(', ')[-2:]
    record['N-Z5'].update({'undoBefore': undo_before, 'undoAfter': undo_after, 'changed': changed})
    record['N-Z5']['ok'] = (undo_before == undo_after and all(c == 'false' for c in changed)
                            and all(cell_of(v['cursorBefore']) == cell_of(v['cursorAfter']) and v['cursorBefore']
                                    for v in record['N-Z5']['levels'].values()))
    refused = {'1234': zoom(s, 1234, current)[0], '0': zoom(s, 0, current)[0], 'no payload': s.cell(16, 0, 0, current, '')[0]}
    record['N-Z6'] = {name: {k: reply.get(k) for k in ('ok', 'code', 'mutationAttempted')} for name, reply in refused.items()}
    record['N-Z6']['ok'] = all(reply.get('ok') == 'false' and reply.get('code') == 'INVALID_ARGUMENT'
                               and reply.get('mutationAttempted') == 'false' for reply in refused.values())
    for name in ('N-Z1', 'N-Z2', 'N-Z3'):
        record[name]['ok'] = bool(record[name]) and all(v['ok'] for v in record[name].values())
    s.close()
    return record


def control(binary, out):
    s = Session(binary, out, 'control')
    reply, _ = zoom(s, 3840)
    s.close()
    return {'reply': {k: reply.get(k) for k in ('ok', 'code')},
            'ok': reply.get('ok') == 'false' and reply.get('code') == 'INVALID_ARGUMENT'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'argv': sys.argv, 'tool': hn.sha(__file__), 'bridge': hn.sha(BRIDGE), 'levels': levels(),
              'harness': {'path': str(args.harness), 'sha256': hn.sha(args.harness)},
              'control': {'path': str(args.control), 'sha256': hn.sha(args.control)}}
    report['cells'] = run(args.harness, out)
    red_levels = {key: v['aligned'] for key, v in report['cells']['red'].items()}
    expected_red = [384000 // t for t in levels() if 384000 // t not in (100, 200)]
    report['redVerdict'] = {p: not all(v for k, v in red_levels.items() if k.startswith(f'{p}/')) for p in expected_red}
    report['controlBuild'] = control(args.control, out)
    holds = all(report['cells'][k]['ok'] for k in ('N-Z1', 'N-Z2', 'N-Z3', 'N-Z4', 'N-Z5', 'N-Z6'))
    report['verdict'] = ('N_HOLDS' if holds and expected_red and all(report['redVerdict'].values()) and report['controlBuild']['ok']
                         else 'N_RED')
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'cells': {k: v['ok'] for k, v in report['cells'].items() if 'ok' in v},
                      'red': report['redVerdict'], 'control': report['controlBuild']['ok'], 'ms': report['cells']['N-Z7']},
                     ensure_ascii=False))
    return 0 if report['verdict'] == 'N_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
