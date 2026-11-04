#!/usr/bin/env python3
"""SPEC-P-calc-structure 4.1: N-S1..N-S5 (and N-S6's timings) on the native 26.8 core, with the spec's two red cases and the
control build (headers, no OXSDK_ODS_STRUCTURE).  The harness is tools/calc_undo_native.cpp built by tools/build_calc_undo_native.py
from the bridge source that will be linked.  One harness session, on a fresh fixture (tools/create_calc_structure_fixture.py), per
cell.  Reads: op 0 (text, formula, value, merged extent) and op 13 (hidden columns/rows); the undo count is the length of
getCommandValues(".uno:Undo")'s actions.

  check_calc_structure_native.py --harness BUILD/structure/calc-undo-native --control BUILD/headers/calc-undo-native --out NEW_DIR

Verdict N_HOLDS iff N-S1..N-S5 hold, both red cases are red in their own cell, and the control refuses op 14.  Every request and
reply is kept (observations-*.jsonl).
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import check_calc_headers_native as hn  # noqa: E402
from create_calc_structure_fixture import create  # noqa: E402

hn.create = create  # the headers harness, on this spec's fixture
RECT = (0, 0, 15000, 6000)  # twips: columns A.., rows 1.. (op 13)
ORIGINAL = {  # (column, row): text on the first sheet, as built
    (0, 1): '鄰格必須保留', (0, 2): '合併格', (0, 999): '第 1000 列', (4, 0): '隱藏欄之後', (26, 0): 'AA 欄', (1, 0): '42'}


class Session(hn.Harness):
    def structure(self, axis, action, index, count, part=0):
        return self.cell(14, 0, 0, part, json.dumps({'axis': axis, 'action': action, 'index': index, 'count': count}))

    def read(self, column, row, part=0):
        reply, _ = self.cell(0, column, row, part)
        return {k: reply.get(k) for k in ('ok', 'text', 'formula', 'value', 'endColumn', 'endRow')}

    def hidden(self, part=0):
        reply, _ = self.headers(RECT, part)
        return {axis: sorted(int(e['index']) for e in hn.entries(reply, axis) if e['hidden'] == 'true')
                for axis in ('columns', 'rows')}

    def undo_count(self):
        """getCommandValues(".uno:Undo") is pretty-printed JSON over several lines: read until it parses."""
        request = {'action': 'command-values', 'command': '.uno:Undo'}
        self.proc.stdin.write(json.dumps(request) + '\n'); self.proc.stdin.flush()
        text = ''
        for _ in range(100000):
            line = self.proc.stdout.readline()
            if not line:
                break
            text += line
            try:
                reply = json.loads(text)
            except json.JSONDecodeError:
                continue
            # The pretty JSON ends in a newline and the harness adds std::endl: one empty line follows.
            trailing = self.proc.stdout.readline()
            if trailing.strip():
                raise RuntimeError(f'expected the empty line after the undo list, got {trailing[:200]!r}')
            break
        else:
            reply = {'unparsed': text}
        self.log.write(json.dumps({'request': request, 'reply': reply}, ensure_ascii=False) + '\n')
        actions = reply.get('actions') if isinstance(reply, dict) else None
        if actions == '':  # an empty list, as boost's ptree writes it
            return 0
        if not isinstance(actions, list):
            raise RuntimeError(f'undo list unreadable: {text[:200]!r}')
        return len(actions)

    def undo(self):
        return self.send({'action': 'uno-wait', 'command': '.uno:Undo', 'timeoutMs': 10000})[0]


def original_state(s):
    """What the first sheet reads as built; also what one Undo must bring back."""
    out = {f'{c},{r}': s.read(c, r)['text'] for (c, r) in ORIGINAL}
    merged = s.read(0, 2)
    out['merge'] = [merged['endColumn'], merged['endRow']]
    out['C1'] = [s.read(2, 0)['formula'], s.read(2, 0)['value']]
    out['hidden'] = s.hidden()
    return out


def expected_original():
    out = {f'{c},{r}': text for (c, r), text in ORIGINAL.items()}
    out.update({'merge': ['1', '2'], 'C1': ['=B1*2', '84'], 'hidden': {'columns': [3], 'rows': [3]}})
    return out


def change(s, axis, action, index, count, part=0):
    before = s.undo_count()
    reply, ms = s.structure(axis, action, index, count, part)
    return reply, ms, before, s.undo_count()


def mutating_cell(binary, out, name, axis, action, index, count, after_reads, want_after, undo=True):
    s = Session(binary, out, name)
    record = {'id': name, 'change': [axis, action, index, count]}
    record['asBuilt'] = original_state(s)
    reply, ms, before, after = change(s, axis, action, index, count)
    record.update(reply={k: reply.get(k) for k in ('ok', 'code', 'changed', 'mutationAttempted', 'maxRows', 'maxColumns')},
                  ms=ms, undoBefore=before, undoAfter=after)
    record['after'] = after_reads(s)
    record['afterWant'] = want_after
    if undo:
        record['undo'] = {k: v for k, v in s.undo().items() if k in ('resultCame', 'waitedMs')}
    record['undone'] = original_state(s)
    record['undoAfterUndo'] = s.undo_count()
    s.close()
    checks = {
        'asBuilt': record['asBuilt'] == expected_original(),
        'applied': reply.get('ok') == 'true' and reply.get('changed') == 'true',
        'after': record['after'] == want_after,
        'oneUndoAction': after == before + 1,
        'undoneToOriginal': record['undone'] == expected_original(),
    }
    record['checks'] = checks
    record['ok'] = all(checks.values())
    return record


def reads_s1(s):
    merged = s.read(0, 4)
    return {'A2': s.read(0, 1)['text'], 'A3': s.read(0, 2)['text'], 'A4': s.read(0, 3)['text'],
            'merge': [merged['text'], merged['endColumn'], merged['endRow']], 'hiddenRows': s.hidden()['rows'],
            'A1002': s.read(0, 1001)['text'], 'C1': s.read(2, 0)['formula']}


WANT_S1 = {'A2': '', 'A3': '', 'A4': '鄰格必須保留', 'merge': ['合併格', '1', '4'], 'hiddenRows': [5], 'A1002': '第 1000 列',
           'C1': '=B1*2'}


def reads_s2(s):
    merged = s.read(0, 2)
    d1 = s.read(3, 0)
    return {'B1': s.read(1, 0)['text'], 'C1': s.read(2, 0)['text'], 'D1': [d1['formula'], d1['value']],
            'hiddenColumns': s.hidden()['columns'], 'F1': s.read(5, 0)['text'], 'AB1': s.read(27, 0)['text'],
            'merge': [merged['text'], merged['endColumn'], merged['endRow']]}


WANT_S2 = {'B1': '', 'C1': '42', 'D1': ['=C1*2', '84'], 'hiddenColumns': [4], 'F1': '隱藏欄之後', 'AB1': 'AA 欄',
           'merge': ['合併格', '2', '2']}


def reads_s3(s):
    merged = s.read(0, 1)
    return {'A2': [merged['text'], merged['endColumn'], merged['endRow']], 'A999': s.read(0, 998)['text'],
            'hiddenRows': s.hidden()['rows']}


WANT_S3 = {'A2': ['合併格', '1', '1'], 'A999': '第 1000 列', 'hiddenRows': [2]}


def reads_s4(s):
    b1 = s.read(1, 0)
    return {'B1': [b1['formula'], '#REF!' in (b1['formula'] or '')]}


WANT_S4_REF = True


def refusals(binary, out):
    s = Session(binary, out, 'refusals')
    cases = []

    def refuse(cid, part, axis, action, index, count, code, reads):
        before_reads = [s.read(c, r, part) for (c, r) in reads]
        reply, ms, before, after = change(s, axis, action, index, count, part)
        after_reads = [s.read(c, r, part) for (c, r) in reads]
        ok = (reply.get('ok') == 'false' and reply.get('code') == code and reply.get('mutationAttempted') == 'false'
              and before == after and before_reads == after_reads and all(r.get('ok') == 'true' for r in after_reads))
        cases.append({'id': cid, 'part': part, 'change': [axis, action, index, count], 'want': code,
                      'reply': {k: reply.get(k) for k in ('ok', 'code', 'mutationAttempted', 'message')}, 'ms': ms,
                      'undo': [before, after], 'reads': after_reads, 'readsUnchanged': before_reads == after_reads, 'ok': ok})

    refuse('protected-insert-rows', 2, 'rows', 'insert', 0, 1, 'READ_ONLY', [(0, 0), (1, 0)])
    refuse('protected-delete-columns', 2, 'columns', 'delete', 0, 1, 'READ_ONLY', [(0, 0), (1, 0)])
    refuse('edge-insert-rows', 3, 'rows', 'insert', 0, 1, 'STRUCTURE_REFUSED', [(0, 0), (0, 1048575), (16383, 0)])
    refuse('edge-insert-columns', 3, 'columns', 'insert', 0, 1, 'STRUCTURE_REFUSED', [(0, 0), (0, 1048575), (16383, 0)])
    refuse('array-split-insert-column', 4, 'columns', 'insert', 2, 1, 'STRUCTURE_REFUSED', [(1, 1), (2, 1), (1, 2), (2, 2)])
    for cid, change_args in (('count-0', ('rows', 'insert', 1, 0)), ('past-max', ('rows', 'insert', 1048576, 1)),
                             ('axis-x', ('x', 'insert', 1, 1))):
        refuse(cid, 0, *change_args, 'INVALID_ARGUMENT', [(0, 1), (2, 0)])
    array = s.read(1, 1, 4)
    s.close()
    return {'id': 'N-S5', 'cases': cases, 'arrayFormula': array.get('formula'), 'ok': all(c['ok'] for c in cases)}


def control(binary, out):
    s = Session(binary, out, 'control')
    reply, _ = s.structure('rows', 'insert', 1, 1)
    a2 = s.read(0, 1)['text']
    s.close()
    return {'reply': {k: reply.get(k) for k in ('ok', 'code')}, 'A2': a2,
            'ok': reply.get('ok') == 'false' and reply.get('code') == 'INVALID_ARGUMENT' and a2 == '鄰格必須保留'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'argv': sys.argv, 'tool': hn.sha(__file__), 'harness': {'path': str(args.harness), 'sha256': hn.sha(args.harness)},
              'control': {'path': str(args.control), 'sha256': hn.sha(args.control)}, 'cells': {}}
    h = args.harness
    report['cells']['N-S1'] = mutating_cell(h, out, 'N-S1', 'rows', 'insert', 1, 2, reads_s1, WANT_S1)
    report['cells']['N-S2'] = mutating_cell(h, out, 'N-S2', 'columns', 'insert', 1, 1, reads_s2, WANT_S2)
    report['cells']['N-S3'] = mutating_cell(h, out, 'N-S3', 'rows', 'delete', 1, 1, reads_s3, WANT_S3)
    s4 = mutating_cell(h, out, 'N-S4', 'columns', 'delete', 1, 1, reads_s4, None)
    s4['checks']['after'] = s4['after']['B1'][1] is WANT_S4_REF
    s4['ok'] = all(s4['checks'].values())
    report['cells']['N-S4'] = s4
    report['cells']['N-S5'] = refusals(h, out)
    report['N-S6'] = {k: report['cells'][k]['ms'] for k in ('N-S1', 'N-S2', 'N-S3', 'N-S4')}
    # Red cases: each must be red in its own cell.
    red_a = mutating_cell(h, out, 'red-a-index-2', 'rows', 'insert', 2, 2, reads_s1, WANT_S1)
    red_b = mutating_cell(h, out, 'red-b-no-undo', 'rows', 'delete', 1, 1, reads_s3, WANT_S3, undo=False)
    report['reds'] = {
        'a-index-off-by-one': {'record': red_a, 'red': not red_a['checks']['after'] and red_a['checks']['applied']},
        'b-no-undo': {'record': red_b, 'red': not red_b['checks']['undoneToOriginal'] and red_b['checks']['after']},
    }
    report['control'] = control(args.control, out)
    holds = all(report['cells'][k]['ok'] for k in ('N-S1', 'N-S2', 'N-S3', 'N-S4', 'N-S5'))
    reds = all(r['red'] for r in report['reds'].values())
    report['verdict'] = 'N_HOLDS' if holds and reds and report['control']['ok'] else 'N_RED'
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    summary = {k: report['cells'][k]['ok'] for k in report['cells']}
    print(json.dumps({'verdict': report['verdict'], 'cells': summary, 'reds': {k: v['red'] for k, v in report['reds'].items()},
                      'control': report['control']['ok'], 'ms': report['N-S6']}, ensure_ascii=False))
    return 0 if report['verdict'] == 'N_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
