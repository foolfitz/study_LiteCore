#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.3: v23's selection collector on the v24 profile; preparation runs only.

The per-cell drivers (fresh document, Table 1 shape, S5 key sequence through the real product keys,
page export) are tools/run_v23_feature_selection.py's own functions, imported; only main() is new:
the plan, mirror and inline readiness check are v24's (tools/v24_feature_selection_cases.py,
tools/judge_v24_feature_selection.py).  Nothing here is counted: counted runs need generation 77
frozen first (spec 15) and get their own mode then.

  --population s5        the 588 S5 sequences
  --population s5-type   M2's 84 type sequences (v24_feature_selection_cases.type_cells)
  --sdk-override PATH    scratch arm (red case (i)): serve PATH as sdk/document-sdk.js.  The plan
                         records it under `scratch` and names the override's hash, the report is
                         marked scratch, and the inline readiness check is recorded, not enforced
                         (a mis-routing SDK must reach the typed cell for T2 to see it).

Output: --output must not exist.  Every cell is written there and nowhere else; nothing is retried.
"""
import argparse
import json
from pathlib import Path
import sys
import traceback
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v21_shakedown_common as common
from run_e2_c_page_smoke import navigate
from run_v23_feature_selection import export_page, wait_page, actual_Z, control, run_s5
from v24_feature_selection_cases import BROWSERS, config, mirror, verify_mirror, encoded, digest, type_cells
from judge_v24_feature_selection import Evidence, readiness, inspect


def plan_with(override):
    plan = config()
    if override is not None:
        raw = override.read_bytes()
        if 'sdk/document-sdk.js' not in plan['servedSources']:
            raise ValueError('the SDK is not a served source')
        plan['servedSources']['sdk/document-sdk.js'] = digest(raw)
        plan['scratch'] = {'sdkOverride': str(override), 'sha256': digest(raw)}
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--population', choices=('s5', 's5-type'), required=True)
    parser.add_argument('--browser', choices=BROWSERS)
    parser.add_argument('--case-id', action='append', help='repeatable, run in the given order')
    parser.add_argument('--keep-going', action='store_true', help='record every listed cell instead of stopping at the first nonpassing one')
    parser.add_argument('--sdk-override', type=Path)
    args = parser.parse_args()
    plan = plan_with(args.sdk_override)
    population = type_cells(plan) if args.population == 's5-type' else list(plan['s5'])
    if args.case_id and (set(args.case_id) - set(population) or len(set(args.case_id)) != len(args.case_id)):
        parser.error('unknown or repeated case')
    overrides = {'sdk/document-sdk.js': args.sdk_override.read_bytes()} if args.sdk_override else None
    args.output.mkdir(parents=True, exist_ok=False); target = args.output.resolve() / 'mirror'; mirror(target, plan, overrides)
    report = {'schema': 1, 'population': args.population, 'argv': sys.argv, 'cwd': str(Path.cwd()), 'config': plan,
              'preparationOnly': True, 'scratch': plan.get('scratch'), 'mirrorBindings': verify_mirror(target, plan), 'runs': []}
    def write(): (args.output / 'report.json').write_bytes(encoded(report))
    write()
    browsers = [args.browser] if args.browser else list(BROWSERS); cases = args.case_id or population
    total = len(browsers) * len(cases)
    with common.browser_lock('v24-feature-selection'):
        report['preRun'] = common.pre_run_checks(); report['foreignCpu'] = common.foreign_cpu(); write()
        if report['preRun']['refuse']: raise SystemExit('pre-run refusal: ' + '; '.join(report['preRun']['refuse']))
        if not report['foreignCpu'].get('ok'): raise SystemExit('foreign CPU refusal; no browser cells')
        with common.served(target) as base:
            for browser in browsers:
                for case in cases:
                    cell = {'browser': browser, 'caseId': case}; session = None
                    try:
                        if plan_with(args.sdk_override) != plan: raise ValueError('source/profile drift')
                        verify_mirror(target, plan); session = common.open_browser(browser)
                        navigate(session, base + '?' + urlencode({'caseId': case}))
                        wait_page(session, "Boolean(window.__featureSelection?.booted && window.__featureSelection?.currentOpen && !document.querySelector('#sink').disabled && !document.querySelector('#sink').readOnly)")
                        control(session, 'prepareReadiness()'); actual_Z(session); control(session, 'finishReadiness()')
                        initial, meta = export_page(session); cell['readinessTransfer'] = meta
                        if plan.get('scratch'):
                            try: readiness(Evidence(initial, plan, browser)); cell['readinessCheck'] = 'held'
                            except Exception as error: cell['readinessCheck'] = 'recorded, not enforced (scratch): ' + str(error)
                        else:
                            readiness(Evidence(initial, plan, browser))
                        run_s5(session, browser, plan['s5'][case], plan, target)
                        cell['page'], cell['pageTransfer'] = export_page(session); cell['inspection'] = inspect(cell['page'], plan, browser)
                    except Exception:
                        cell['fatal'] = traceback.format_exc()
                        if session is not None:
                            try: cell['page'], cell['pageTransfer'] = export_page(session)
                            except Exception: cell['exportFailure'] = traceback.format_exc()
                    finally:
                        if session is not None: cell['cleanup'] = common.close_browser(session)
                        path = args.output / (f'{browser}-{case}.json'.replace('/', '__')); path.write_bytes(encoded(cell))
                        report['runs'].append({'path': path.name, 'sha256': digest(path.read_bytes()),
                                               'verdict': (cell.get('inspection') or {}).get('verdict', 'FATAL')}); write()
                        print(f"{len(report['runs'])}/{total} {browser} {case} {report['runs'][-1]['verdict']}", file=sys.stderr, flush=True)
                    if cell.get('fatal') or cell.get('inspection', {}).get('verdict') != 'PASS':
                        report.setdefault('nonpassing', []).append([browser, case]); write()
                        if not args.keep_going: raise SystemExit('first nonpassing observation retained; no retry')
    report['postConfig'] = plan_with(args.sdk_override); verify_mirror(target, plan); write()
    if report['postConfig'] != plan: raise SystemExit('post-run drift')
    return 1 if report.get('nonpassing') else 0


if __name__ == '__main__':
    raise SystemExit(main())
