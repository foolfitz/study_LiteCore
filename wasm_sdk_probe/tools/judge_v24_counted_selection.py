#!/usr/bin/env python3
"""Counted v24 S5/T1/T2, R1 and S1-S4. No preparation or prior-version count credit.

Entry points retain their code objects. Evidence/readiness are preparation v24's; S5 is its
T2-wrapped reader. R1's marker witness differs only in the exact typed payload's route field.
"""
import argparse
import gzip
import json
from pathlib import Path
import sys
from types import FunctionType

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_v23_feature_selection as j23
import judge_v24_feature_selection as preparation
from judge_v23_feature_pre_red import need
from v24_counted_selection_cases import ROOT, config, digest, encoded, verify_mirror, KINDS
from judge_v23_feature_selection import (need, request_key, MUTATION_OPS, final_save,
                                        r1_saved_marker, saved_paragraphs)

G = dict(vars(j23))
G.update(PROFILE=preparation.PROFILE, Evidence=preparation.Evidence, readiness=preparation.readiness,
         inspect_s5=preparation.inspect_s5)


def rebound(fn):
    return FunctionType(fn.__code__, G, fn.__name__, fn.__defaults__, fn.__closure__)


def r1_marker_witness(e,v,name,gen,handle,after,texts):
    """The '#' through the product's typing path, then the export: (paragraph, offset) of the marker."""
    m=v.get('marker') or {}
    need(m.get('generation')==gen and all(type(m.get(k)) is int for k in ('inputStart','inputEnd','requestStart','requestEnd'))
         and 0<=m['inputStart']<=m['inputEnd']<=len(e.page['inputs']) and 0<=m['requestStart']<=m['requestEnd']<=len(e.page['requests']),'marker window absent')
    window=e.page['inputs'][m['inputStart']:m['inputEnd']]
    keys=[x for x in window if x['type']=='keydown']
    need(len(keys)==1 and keys[0].get('key')=='#' and keys[0].get('isTrusted') is True
         and not any(keys[0].get(k) for k in ('ctrlKey','altKey','metaKey','repeat')),'marker key absent or not one trusted press')
    sink=keys[0].get('sink',{})
    need(sink.get('active') and sink.get('connected') and not sink.get('disabled') and not sink.get('readOnly') and sink.get('documentHandle')==handle,'marker key not in the editable document sink')
    need(keys[0]['at']>=after['at'],'marker typed before the delayed read')
    typed=[x for x in window if x['type']=='beforeinput' and x.get('inputType')=='insertText' and x.get('data')=='#' and x.get('isTrusted') is True]
    need(len(typed)==1 and typed[0]['at']>=keys[0]['at'],'marker beforeinput absent')
    inserts=[r for r in e.requests.values() if r['generation']==gen and r['message']['operation']=='insertText']
    in_window=[r for r in e.page['requests'][m['requestStart']:m['requestEnd']] if r['generation']==gen and r['message']['operation']=='insertText']
    need(len(inserts)==1 and in_window==inserts and inserts[0]['message']['payload']=={'documentHandle':handle,'text':'#','route':'uno-insert-text'}
         and inserts[0]['at']>=typed[0]['at'],'marker insertion absent/extra')
    terminal=e.replies.get(request_key(inserts[0]));need(terminal is not None and terminal['message'].get('ok') is True,'marker insertion refused')
    need(not any(r['generation']==gen and r['message']['operation'] in MUTATION_OPS for r in e.page['requests'][m['requestStart']:m['requestEnd']]),'unplanned mutation around the marker')
    final_save(e,name+'-final-save',v['finalSave'])
    c=next(c for c in e.page['calls'] if c['name']==name+'-final-save')
    saves=[r for r in e.page['requests'][c['requestStart']:c['requestEnd']] if r['generation']==gen and r['message']['operation']=='save']
    need(saves[-1]['at']>=terminal['at'],'export precedes the marker insertion')
    position=r1_saved_marker(saved_paragraphs(v['finalSave']),texts)
    need(position is not None,'export is not the fixture plus one marker')
    return position


G['r1_marker_witness'] = r1_marker_witness
G['r1_arm'] = rebound(j23.r1_arm)
inspect_r1 = G['inspect_r1'] = rebound(j23.inspect_r1)
inspect_interaction = G['inspect_interaction'] = rebound(j23.inspect_interaction)
inspect = G['inspect'] = rebound(j23.inspect)
judge = rebound(j23.judge)


def load_cell(directory, receipt):
    relative = Path(receipt['path'])
    need(not relative.is_absolute() and '..' not in relative.parts, 'invalid cell path')
    path = directory / relative
    raw = path.read_bytes() if path.is_file() else gzip.decompress(Path(str(path) + '.gz').read_bytes())
    need(digest(raw) == receipt['sha256'], 'cell bytes changed: ' + str(relative))
    return json.loads(raw)


def read_report(path):
    path = Path(path)
    report = json.loads(path.read_bytes())
    need(report.get('preparationOnly') is False and report.get('countedV24') is True,
         'preparation or unqualified collection cannot count')
    need(not report.get('scratch'), 'scratch collection cannot count')
    from run_v24_counted_cohort import verify
    cohort = Path(report['cohort'])
    frozen = verify(cohort)
    need(report.get('cohortSha256') == digest(cohort.read_bytes()), 'run cohort differs')
    stage = next(s for s in frozen['stages'] if s['population'] == report.get('population'))
    need(path.resolve() == ROOT / stage['output'] / 'report.json', 'run output differs from cohort')
    plan = config()
    need(report.get('config') == plan and report.get('postConfig') == plan,
         'actual instrument/source graph differs or incomplete')
    need(report.get('population') in KINDS, 'undeclared population')
    need(report.get('preRed') == j23.check_pre_red(report['preRed']['path']), 'historical prerequisite differs')
    need(report.get('mirrorBindings') == verify_mirror(path.parent / 'mirror', plan), 'mirror receipt differs')
    cells = [load_cell(path.parent, item) for item in report['runs']]
    return judge(cells, plan, report['population'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    try:
        result = read_report(args.report)
    except Exception as error:
        result = {'verdict': 'NOT_ESTABLISHED', 'reason': f'{type(error).__name__}: {error}'}
    print(encoded(result).decode(), end='')
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
