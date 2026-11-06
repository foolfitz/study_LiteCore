#!/usr/bin/env python3
"""SPEC-P-calc-sheets section 1, E1 (a measurement, not a verdict): how the 26.8 core reads and writes a reference to another
sheet, on tools/create_calc_sheets_fixture.py's fixture.  Each spelling is written with op 1 into column H of the first sheet and
read back with op 0: the core's own formula text (its canonical spelling), the displayed text and the value.

  probe_calc_sheets_native.py --harness BUILD/copy/calc-undo-native --out NEW_DIR
"""
import argparse
import json
from pathlib import Path
import sys

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import check_calc_headers_native as hn  # noqa: E402
from create_calc_sheets_fixture import NAMED, create  # noqa: E402

hn.create = create
SPELLINGS = [
    '=$另一張表.A1', '=另一張表.A1', "='另一張表'.A1", '=另一張表!A1',
    "=$'有 空白'.B1", '=$有 空白.B1', "=$'2026'.B1", '=$2026.B1', "=$'O''Neil'.B1", "=$O'Neil.B1",
    '=$Sheet_3.B1', "=$'Sheet_3'.B1", '=$sheet_3.B1', "=SUM($'有 空白'.B1:B1)", "=SUM($'有 空白'.B1:$'2026'.B1)",
    '=$不存在的表.A1',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    s = hn.Harness(args.harness, out, 'e1')
    pick = lambda r: {k: r.get(k) for k in ('ok', 'code', 'formula', 'text', 'value', 'cellType')}
    fixture = {name: pick(s.cell(0, 0, 0, part)[0]) for part, name in enumerate(NAMED, start=5)}
    written = []
    for row, spelling in enumerate(SPELLINGS):
        s.cell(1, 7, row, 0, spelling)
        written.append({'typed': spelling, 'read': pick(s.cell(0, 7, row, 0)[0])})
    s.proc.stdin.close(); s.proc.wait(timeout=30)
    report = {'argv': sys.argv, 'tool': hn.sha(__file__), 'harness': {'path': str(args.harness), 'sha256': hn.sha(args.harness)},
              'fixtureA1': fixture, 'written': written}
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    for w in written:
        print(f"{w['typed']:<36} -> {w['read']['formula']:<36} {w['read']['text']!r}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
