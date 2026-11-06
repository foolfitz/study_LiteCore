#!/usr/bin/env python3
"""SPEC-P-calc-copy 4.1: N-C1..N-C6 (and N-C7's timings) on the native 26.8 core, with the spec's red case and the control build
(v6's defines, no OXSDK_ODS_COPY).  The harness is tools/calc_undo_native.cpp built by tools/build_calc_undo_native.py from the
bridge source that will be linked, on tools/create_calc_structure_fixture.py's fixture.  One harness session for N-C1..N-C6; the
red case and the control each get their own.  Reads: op 15's plainText, .uno:CellCursor, and the length of .uno:Undo's list.

  check_calc_copy_native.py --harness BUILD/copy/calc-undo-native --control BUILD/control/calc-undo-native --out NEW_DIR

Verdict N_HOLDS iff N-C1..N-C6 hold, the red case is red in N-C1's cell, and the control refuses op 15.  Every request and reply
is kept (observations-*.jsonl).
"""
import argparse
import json
from pathlib import Path
import sys

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import check_calc_headers_native as hn  # noqa: E402
from check_calc_structure_native import Session as StructureSession  # noqa: E402  (sets the structure fixture)

MAX_COLUMN, MAX_ROW = 16383, 1048575
WANT_C1 = '42\t84\n格式測試\t待清除\n'
SETUP = ((7, 0, '第一行\n第二行'), (8, 0, '有"引號"\t與定位'), (9, 0, '=1/3'))


class Session(StructureSession):
    def copy(self, column, row, end_column, end_row, part=0):
        return self.cell(15, column, row, part, json.dumps({'endColumn': end_column, 'endRow': end_row}))


def text(reply):
    return reply.get('plainText') if reply.get('ok') == 'true' else None


def cells(binary, out):
    s = Session(binary, out, 'n')
    for column, row, value in SETUP:
        s.cell(1, column, row, 0, value)
    undo_before = s.undo_count()
    record, ms = {}, {}

    reply, ms['B1:C2'] = s.copy(1, 0, 2, 1)
    record['N-C1'] = {'plainText': text(reply), 'changed': reply.get('changed')}
    record['N-C1']['ok'] = text(reply) == WANT_C1

    reply, ms['column A'] = s.copy(0, 0, 0, MAX_ROW)
    lines = (text(reply) or '').split('\n')
    record['N-C2'] = {'endsInNewline': (text(reply) or '').endswith('\n'), 'lines': len(lines) - 1,
                      'line1': lines[0], 'line4': lines[3] if len(lines) > 3 else None,
                      'line1000': lines[999] if len(lines) > 999 else None, 'changed': reply.get('changed')}
    c2 = record['N-C2']
    c2['ok'] = (c2['endsInNewline'] and c2['lines'] == 1000 and c2['line1'] == '原始中文 Alpha' and c2['line4'] == '隱藏列'
                and c2['line1000'] == '第 1000 列')

    reply, _ = s.copy(0, 0, MAX_COLUMN, 0)
    row1 = text(reply) or ''
    fields = row1.rstrip('\n').split('\t')
    reply_sheet, ms['sheet'] = s.copy(0, 0, MAX_COLUMN, MAX_ROW)
    sheet_line1 = (text(reply_sheet) or '').split('\n')[0]
    record['N-C3'] = {'row1': row1, 'fields': len(fields), 'sheetLine1': sheet_line1,
                      'changed': [reply.get('changed'), reply_sheet.get('changed')]}
    record['N-C3']['ok'] = (row1.count('\n') == 1 and row1.endswith('\n') and len(fields) == 27 and fields[3] == ''
                            and fields[7] == '第一行 第二行' and fields[26] == 'AA 欄' and sheet_line1 == row1.rstrip('\n'))

    single = [s.copy(2, 0, 2, 0)[0], s.copy(0, 0, 0, 0, part=1)[0], s.copy(0, 0, 1, 0, part=2)[0]]
    record['N-C4'] = {'C1': text(single[0]), 'other A1': text(single[1]), 'protected A1:B1': text(single[2]),
                      'changed': [r.get('changed') for r in single]}
    record['N-C4']['ok'] = (text(single[0]) == '84' and text(single[1]) == '第二表不應改動'
                            and text(single[2]) == '鎖定內容\t可編輯\n')

    s.cell(0, 1, 1, 0)  # B2
    before = s.cursor()
    reply, _ = s.copy(1, 0, 2, 1)
    after = s.cursor()
    undo_after = s.undo_count()
    changed = [record[k]['changed'] for k in ('N-C1', 'N-C2')] + record['N-C3']['changed'] + record['N-C4']['changed'] \
        + [reply.get('changed')]
    record['N-C5'] = {'cursorBefore': before, 'cursorAfter': after, 'undoBefore': undo_before, 'undoAfter': undo_after,
                      'changed': changed}
    record['N-C5']['ok'] = (before == after and undo_before == undo_after and all(c == 'false' for c in changed)
                            and text(reply) == WANT_C1)

    refused = {'empty L10:M11': (s.copy(11, 9, 12, 10)[0], 'COPY_UNAVAILABLE'),
               'A1:Z3000': (s.copy(0, 0, 25, 2999)[0], 'RANGE_TOO_LARGE'),
               'reversed': (s.copy(3, 3, 2, 2)[0], 'INVALID_ARGUMENT')}
    record['N-C6'] = {name: {k: reply.get(k) for k in ('ok', 'code', 'mutationAttempted')} | {'want': code}
                      for name, (reply, code) in refused.items()}
    record['N-C6']['ok'] = all(reply.get('ok') == 'false' and reply.get('code') == code
                               and reply.get('mutationAttempted') == 'false' for reply, code in refused.values())
    s.close()
    return record, ms


def red_case(binary, out):
    """endRow read as exclusive: N-C1 asks for B1:C1."""
    s = Session(binary, out, 'red-end-row-exclusive')
    reply, _ = s.copy(1, 0, 2, 0)
    s.close()
    return {'plainText': text(reply), 'red': text(reply) is not None and text(reply) != WANT_C1}


def control(binary, out):
    s = Session(binary, out, 'control')
    reply, _ = s.copy(1, 0, 2, 1)
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
    report = {'argv': sys.argv, 'tool': hn.sha(__file__), 'harness': {'path': str(args.harness), 'sha256': hn.sha(args.harness)},
              'control': {'path': str(args.control), 'sha256': hn.sha(args.control)}}
    report['cells'], report['N-C7'] = cells(args.harness, out)
    report['red'] = red_case(args.harness, out)
    report['controlBuild'] = control(args.control, out)
    holds = all(report['cells'][k]['ok'] for k in ('N-C1', 'N-C2', 'N-C3', 'N-C4', 'N-C5', 'N-C6'))
    report['verdict'] = 'N_HOLDS' if holds and report['red']['red'] and report['controlBuild']['ok'] else 'N_RED'
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'cells': {k: v['ok'] for k, v in report['cells'].items()},
                      'red': report['red']['red'], 'control': report['controlBuild']['ok'], 'ms': report['N-C7']},
                     ensure_ascii=False))
    return 0 if report['verdict'] == 'N_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
