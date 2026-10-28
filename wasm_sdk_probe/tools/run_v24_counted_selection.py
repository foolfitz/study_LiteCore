#!/usr/bin/env python3
"""Fresh v24 collection. Counted mode requires a frozen cohort; filters are preparation only."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v21_shakedown_common as common
from run_e2_c_page_smoke import navigate
from run_v23_feature_selection import (export_page, wait_page, actual_Z, control, run_s5,
                                        run_r1, fresh, run_interaction, run_arm)
from judge_v24_counted_selection import inspect
from judge_v24_feature_selection import Evidence, readiness
from judge_v23_feature_selection import check_pre_red
from v24_counted_selection_cases import (BROWSERS, config, mirror, verify_mirror, encoded,
                                         digest, population, KINDS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--population', choices=KINDS, required=True)
    parser.add_argument('--preparation-only', action='store_true')
    parser.add_argument('--browser', choices=BROWSERS)
    parser.add_argument('--case-id', action='append')
    parser.add_argument('--cohort', type=Path)
    parser.add_argument('--pre-red-report', type=Path)
    args = parser.parse_args()
    if (args.browser or args.case_id) and not args.preparation_only:
        parser.error('filters require preparation-only')
    if not args.preparation_only and not args.cohort:
        parser.error('counted collection requires a frozen cohort')
    plan = config()
    if args.cohort:
        from run_v24_counted_cohort import verify, verify_stage_admission
        frozen = verify(args.cohort)
        verify_stage_admission(args.cohort, frozen, args.population, args.output)
        if args.preparation_only:
            parser.error('cohort cannot authorize preparation')
    cases = population(plan, args.population)
    if args.case_id and (set(args.case_id) - set(cases) or len(set(args.case_id)) != len(args.case_id)):
        parser.error('unknown or repeated case')
    prerequisite = check_pre_red(args.pre_red_report) if args.pre_red_report else {'verdict': 'NOT_ESTABLISHED'}
    if not args.preparation_only and prerequisite != frozen['preRed']:
        parser.error('historical pre-red differs from cohort')
    args.output.mkdir(parents=True, exist_ok=False)
    target = args.output.resolve() / 'mirror'
    mirror(target, plan)
    report = {'schema': 1, 'population': args.population, 'argv': sys.argv, 'cwd': str(Path.cwd()),
              'config': plan, 'preparationOnly': args.preparation_only, 'countedV24': not args.preparation_only,
              'cohort': str(args.cohort.resolve()) if args.cohort else None,
              'cohortSha256': digest(args.cohort.read_bytes()) if args.cohort else None,
              'preRed': prerequisite, 'mirrorBindings': verify_mirror(target, plan), 'runs': []}
    def write():
        (args.output / 'report.json').write_bytes(encoded(report))
    write()
    browsers = [args.browser] if args.browser else BROWSERS
    selected = args.case_id or cases
    try:
        with common.browser_lock('v24-counted-selection'):
            report['preRun'] = common.pre_run_checks()
            report['foreignCpu'] = common.foreign_cpu()
            write()
            if report['preRun']['refuse']:
                raise RuntimeError('pre-run refusal: ' + '; '.join(report['preRun']['refuse']))
            if not report['foreignCpu'].get('ok'):
                raise RuntimeError('foreign CPU refusal; no browser cells')
            with common.served(target) as base:
                for browser in browsers:
                    for case in selected:
                        cell = {'browser': browser, 'caseId': case}
                        session = None
                        try:
                            if config() != plan:
                                raise ValueError('source/profile drift')
                            verify_mirror(target, plan)
                            session = common.open_browser(browser)
                            navigate(session, base + '?' + urlencode({'caseId': case}))
                            wait_page(session, "Boolean(window.__featureSelection?.booted && window.__featureSelection?.currentOpen && !document.querySelector('#sink').disabled && !document.querySelector('#sink').readOnly)")
                            control(session, 'prepareReadiness()'); actual_Z(session); control(session, 'finishReadiness()')
                            initial, cell['readinessTransfer'] = export_page(session)
                            readiness(Evidence(initial, plan, browser))
                            if case in plan['s5']:
                                run_s5(session, browser, plan['s5'][case], plan, target)
                            elif case in plan['r1']:
                                row = plan['r1'][case]
                                run_r1(session, browser, row, target, plan['r1Fixtures'][row['fixture']])
                            elif case in plan['interactions']:
                                fresh(session, target); run_interaction(session, browser, plan['interactions'][case])
                            else:
                                for arm in ('reference', 'candidate'):
                                    fresh(session, target); run_arm(session, browser, arm, plan['cases'][case])
                            cell['page'], cell['pageTransfer'] = export_page(session)
                            cell['inspection'] = inspect(cell['page'], plan, browser)
                        except Exception:
                            cell['fatal'] = traceback.format_exc()
                            if session is not None:
                                try:
                                    cell['page'], cell['pageTransfer'] = export_page(session)
                                except Exception:
                                    cell['exportFailure'] = traceback.format_exc()
                        finally:
                            if session is not None:
                                cell['cleanup'] = common.close_browser(session)
                            path = args.output / (f'{browser}-{case}.json'.replace('/', '__'))
                            path.write_bytes(encoded(cell))
                            report['runs'].append({'path': path.name, 'sha256': digest(path.read_bytes())})
                            write()
                        verdict = cell.get('inspection', {}).get('verdict', 'FATAL')
                        print(f"{len(report['runs'])}/{len(browsers) * len(selected)} {browser} {case} {verdict}",
                              file=sys.stderr, flush=True)
                        if cell.get('fatal') or verdict != 'PASS':
                            report.setdefault('nonpassing', []).append([browser, case])
                            raise RuntimeError('first nonpassing observation retained; no retry')
    finally:
        report['postConfig'] = config()
        verify_mirror(target, plan)
        write()
    if report['postConfig'] != plan:
        raise SystemExit('post-run drift')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
