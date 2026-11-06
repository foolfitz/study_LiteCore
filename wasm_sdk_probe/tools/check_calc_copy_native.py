#!/usr/bin/env python3
"""SPEC-P-calc-copy 4.1: N-C1..N-C6 (and N-C7's timings) on the native 26.8 core, with the spec's red case and the control build
(v6's defines, no OXSDK_ODS_COPY).  The harness is tools/calc_undo_native.cpp built by tools/build_calc_undo_native.py from the
bridge source that will be linked, on tools/create_calc_structure_fixture.py's fixture.  One harness session for N-C1..N-C6; the
red case and the control each get their own.  Reads: op 15's plainText, .uno:CellCursor, and the length of .uno:Undo's list.

  check_calc_copy_native.py --harness BUILD/copy/calc-undo-native --control BUILD/control/calc-undo-native --out NEW_DIR

Verdict N_HOLDS iff N-C1..N-C6 hold, the red case is red in N-C1's cell, and the control refuses op 15.  Every request and reply
is kept (observations-*.jsonl).

2026-11-07, SPEC-P-calc-copy append 2 (9.2): --html adds N-H1..N-H7 to the same session (op 15's htmlText, parsed into a cell
table: the first <table>, each <tr>'s <td> texts, <br> as a newline), N-H3's paste session (A1:C2's htmlText pasted at L20 through
LOK paste("text/html"), L20:N21 read back), the red case (LOK's <pre> fallback, init.cxx encodeTextAsHTML, fed to N-H1's judge),
and the control is then v7's defines (op 15 succeeds with no htmlText).  Verdict N_HOLDS iff N-C1..N-C6 and N-H1..N-H6 hold, both
red cases are red, and the control holds.
  check_calc_copy_native.py --html --harness BUILD/v8/calc-undo-native --control BUILD/v7/calc-undo-native --out NEW_DIR
--paste-html FILE (P-H4): only the paste session, with FILE's HTML (a browser's read-back) in place of the core's; exit 0 iff
L20:N21 equal A1:C2.
  check_calc_copy_native.py --paste-html FILE --harness BUILD/v8/calc-undo-native --out NEW_DIR
"""
import argparse
from html.parser import HTMLParser
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


class CellTable(HTMLParser):
    """The cell table of the first <table>: [[td text, ...] per <tr>]; <br> is a newline, other whitespace is kept."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.depth, self.rows, self.cell = 0, 0, [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.tables += 1
            self.depth += 1
        elif self.tables == 1 and self.depth == 1 and tag == 'tr':
            self.rows.append([])
        elif self.tables == 1 and self.depth == 1 and tag == 'td' and self.rows:
            self.cell = []
        elif tag == 'br' and self.cell is not None:
            self.cell.append('\n')

    def handle_endtag(self, tag):
        if tag == 'td' and self.cell is not None:
            self.rows[-1].append(''.join(self.cell))
            self.cell = None
        elif tag == 'table':
            self.depth -= 1

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def cell_table(html):
    parser = CellTable()
    parser.feed(html or '')
    parser.close()
    return {'tables': parser.tables, 'rows': parser.rows}


def lok_fallback(plain):
    """What LOK's getFromTransferable returns for text/html when the transferable has no HTML (init.cxx encodeTextAsHTML)."""
    return ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">\n<html><head><meta http-equiv="content-type" '
            'content="text/html; charset=utf-8"/><meta name="generator" content="LibreOffice"/></head><body><pre>'
            + plain + '</pre></body></html>')


WANT_H1 = [['42', '84'], ['格式測試', '待清除']]
SOURCE_A1C2 = [(column, row) for row in (0, 1) for column in (0, 1, 2)]


def paste_session(binary, out, name, html):
    """N-H3 / P-H4: html pasted at L20 through LOK paste("text/html"); L20:N21's texts against A1:C2's."""
    s = Session(binary, out, name)
    source = {f'{c},{r}': s.read(c, r).get('text') for c, r in SOURCE_A1C2}
    selected, _ = s.send({'action': 'lok-select', 'part': 0, 'address': 'L20'})
    pasted, _ = s.send({'action': 'paste', 'mimeType': 'text/html', 'data': html})
    target = {f'{c},{r}': s.read(c + 11, r + 19).get('text') for c, r in SOURCE_A1C2}
    s.close()
    return {'cursor': selected.get('cursor'), 'pasted': pasted.get('pasted'), 'source': source, 'target': target,
            'L20': target['0,0'], 'ok': pasted.get('pasted') is True and target == source and target['0,0'] == '原始中文 Alpha'}


def html_checks(s, replies):
    """N-H1, N-H2, N-H4, N-H7 on replies taken in cells()'s session, plus the copies only they need."""
    record = {}
    h1 = cell_table(replies['B1:C2'].get('htmlText'))
    record['N-H1'] = {'table': h1, 'plainText': text(replies['B1:C2'])}
    record['N-H1']['ok'] = h1['tables'] == 1 and h1['rows'] == WANT_H1 and text(replies['B1:C2']) == WANT_C1
    a, h = (cell_table(s.copy(*args)[0].get('htmlText')) for args in ((0, 0, 0, 1), (7, 0, 8, 0)))
    record['N-H2'] = {'A1:A2': a, 'H1:I1': h}
    record['N-H2']['ok'] = (a['rows'] == [['原始中文 Alpha'], ['鄰格必須保留']]
                            and h['rows'] == [['第一行\n第二行', '有"引號"\t與定位']])
    column, sheet = cell_table(replies['column A'].get('htmlText')), cell_table(replies['sheet'].get('htmlText'))
    protected = cell_table(replies['protected A1:B1'].get('htmlText'))
    # Spec append 3: the core's HTML export skips hidden columns and rows (htmlexp.cxx), so hidden row 4 and column D are absent.
    rows = column['rows']
    record['N-H4'] = {'columnRows': len(rows), 'columnRow1': rows[0] if rows else None, 'columnRow4': rows[3] if len(rows) > 3 else None,
                      'columnLast': rows[-1] if rows else None, 'hiddenRowText': any(row == ['隱藏列'] for row in rows),
                      'sheetRow1Cells': len(sheet['rows'][0]) if sheet['rows'] else None,
                      'sheetRow1Cell4': sheet['rows'][0][3] if sheet['rows'] and len(sheet['rows'][0]) > 3 else None,
                      'protected': protected['rows']}
    c = record['N-H4']
    c['ok'] = (c['columnRows'] == 999 and c['columnRow1'] == ['原始中文 Alpha'] and c['columnRow4'] == ['隱藏列之後']
               and c['columnLast'] == ['第 1000 列'] and not c['hiddenRowText'] and c['sheetRow1Cells'] == 26
               and c['sheetRow1Cell4'] == '隱藏欄之後' and c['protected'] == [['鎖定內容', '可編輯']])
    record['N-H7'] = {name: {'htmlBytes': len((replies[name].get('htmlText') or '').encode())}
                      for name in ('B1:C2', 'column A', 'sheet')}
    return record


def cells(binary, out, html=False):
    s = Session(binary, out, 'n')
    for column, row, value in SETUP:
        s.cell(1, column, row, 0, value)
    undo_before = s.undo_count()
    record, ms = {}, {}

    reply, ms['B1:C2'] = s.copy(1, 0, 2, 1)
    replies = {'B1:C2': reply}
    record['N-C1'] = {'plainText': text(reply), 'changed': reply.get('changed')}
    record['N-C1']['ok'] = text(reply) == WANT_C1

    reply, ms['column A'] = s.copy(0, 0, 0, MAX_ROW)
    replies['column A'] = reply
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
    replies['sheet'] = reply_sheet
    sheet_line1 = (text(reply_sheet) or '').split('\n')[0]
    record['N-C3'] = {'row1': row1, 'fields': len(fields), 'sheetLine1': sheet_line1,
                      'changed': [reply.get('changed'), reply_sheet.get('changed')]}
    record['N-C3']['ok'] = (row1.count('\n') == 1 and row1.endswith('\n') and len(fields) == 27 and fields[3] == ''
                            and fields[7] == '第一行 第二行' and fields[26] == 'AA 欄' and sheet_line1 == row1.rstrip('\n'))

    single = [s.copy(2, 0, 2, 0)[0], s.copy(0, 0, 0, 0, part=1)[0], s.copy(0, 0, 1, 0, part=2)[0]]
    replies['protected A1:B1'] = single[2]
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
    if html:
        # N-H5 is N-C5 on this build (every copy above also read text/html); N-H6 is N-C6 with no htmlText on a refusal.
        undo_before_html = s.undo_count()
        record.update(html_checks(s, replies))
        record['N-H5'] = {'N-C5': record['N-C5']['ok'], 'undoBefore': undo_before_html, 'undoAfter': s.undo_count()}
        record['N-H5']['ok'] = record['N-C5']['ok'] and undo_before_html == record['N-H5']['undoAfter'] == undo_before
        record['N-H6'] = {'N-C6': record['N-C6']['ok'],
                          'htmlText': {name: 'htmlText' in reply for name, (reply, _) in refused.items()}}
        record['N-H6']['ok'] = record['N-C6']['ok'] and not any(record['N-H6']['htmlText'].values())
        for name in record['N-H7']:
            record['N-H7'][name]['ms'] = ms[name]
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


def control_html(binary, out):
    """v7's defines: op 15 succeeds with N-C1's text and no htmlText."""
    s = Session(binary, out, 'control')
    reply, _ = s.copy(1, 0, 2, 1)
    s.close()
    return {'reply': {k: reply.get(k) for k in ('ok', 'code', 'plainText')}, 'htmlText': 'htmlText' in reply,
            'ok': text(reply) == WANT_C1 and 'htmlText' not in reply}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--control', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--html', action='store_true')
    parser.add_argument('--paste-html', type=Path)
    args = parser.parse_args()
    if not args.paste_html and not args.control:
        parser.error('--control is required unless --paste-html')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'argv': sys.argv, 'tool': hn.sha(__file__), 'harness': {'path': str(args.harness), 'sha256': hn.sha(args.harness)}}
    if args.paste_html:
        report['input'] = {'path': str(args.paste_html), 'sha256': hn.sha(args.paste_html)}
        report['P-H4'] = paste_session(args.harness, out, 'paste', args.paste_html.read_text())
        report['verdict'] = 'PASTE_HOLDS' if report['P-H4']['ok'] else 'PASTE_RED'
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
        print(json.dumps({'verdict': report['verdict'], 'L20': report['P-H4']['L20']}, ensure_ascii=False))
        return 0 if report['P-H4']['ok'] else 1
    report['control'] = {'path': str(args.control), 'sha256': hn.sha(args.control)}
    report['cells'], report['N-C7'] = cells(args.harness, out, html=args.html)
    report['red'] = red_case(args.harness, out)
    names = ['N-C1', 'N-C2', 'N-C3', 'N-C4', 'N-C5', 'N-C6']
    if args.html:
        copy = Session(args.harness, out, 'html-source')
        html = copy.copy(0, 0, 2, 1)[0].get('htmlText') or ''
        copy.close()
        report['N-H3'] = paste_session(args.harness, out, 'paste', html)
        report['cells']['N-H3'] = report['N-H3']
        fallback = cell_table(lok_fallback(WANT_C1))
        report['redHtml'] = {'table': fallback, 'red': not (fallback['tables'] == 1 and fallback['rows'] == WANT_H1)}
        report['controlBuild'] = control_html(args.control, out)
        names += ['N-H1', 'N-H2', 'N-H3', 'N-H4', 'N-H5', 'N-H6']
        reds = report['red']['red'] and report['redHtml']['red']
    else:
        report['controlBuild'] = control(args.control, out)
        reds = report['red']['red']
    holds = all(report['cells'][k]['ok'] for k in names)
    report['verdict'] = 'N_HOLDS' if holds and reds and report['controlBuild']['ok'] else 'N_RED'
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'cells': {k: v['ok'] for k, v in report['cells'].items() if 'ok' in v},
                      'red': report['red']['red'], 'redHtml': report.get('redHtml', {}).get('red'),
                      'control': report['controlBuild']['ok'], 'ms': report['N-C7']}, ensure_ascii=False))
    return 0 if report['verdict'] == 'N_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
