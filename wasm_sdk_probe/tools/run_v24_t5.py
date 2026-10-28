#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.3 T5 (ruling 1 T5): table2 with real keys, three times per browser and arm.

Both arms start the way S5's `shift-Right@cell-end/type` does (v24 harness page and plan, a fresh
document, the Table 1 shape: caret at A1's text end, then a real Shift+Right, so A1's tail and B1
are selected) and differ only in how `x` arrives:

  typed   a real `x` key (CDP / WebDriver key actions, never commitText) -- tools/run_v23_feature_selection
          .run_s5, unchanged.  Expected save: A1 "" and B1 "x"; the insertText request carries
          route "uno-insert-text", its reply method "uno-insert-text", completion "uno-command-result".
  paste   `x` written to the browser's clipboard before the document opens (tools/v21_clipboard: Chrome
          by CDP permission, Firefox by its testing pref), then a real Ctrl+V after the Shift+Right has
          answered.  Expected save: A1 "A1 cell textx" and B1 "B1 cell textx#" (finding 169 on the
          unchanged paste route); the request carries route "paste" and its reply method "paste".

Each repetition is a fresh browser.  Nothing is retried.  --output must not exist.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
import traceback
from urllib.parse import urlencode, urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v21_shakedown_common as common
import v21_input as inputs
import v21_clipboard as clipboard
from odt_paragraphs import paragraph_texts_from_xml
from run_e2_c_page_smoke import navigate
from run_v23_feature_selection import export_page, wait_page, actual_Z, control, fresh, run_arm, run_s5, EXTENSION_ANSWERED
from v23_s5_comparison import odt_content
from v24_feature_selection_cases import BROWSERS, config, mirror, verify_mirror, encoded, digest
from judge_v24_feature_selection import Evidence, readiness, inspect

CASE = 'shift-Right@cell-end/type'
A1, B1 = 8, 9
EXPECTED = {'typed': ('', 'x', 'uno-insert-text'), 'paste': ('A1 cell textx', 'B1 cell textx#', 'paste')}
INSERT_ANSWERED = """(()=>{const p=window.__featureSelection,q=p.s5cand.sequence,g=q.generation;
  const r=p.requests.slice(q.requestStart).filter(e=>e.generation===g&&e.message.operation==='insertText');
  return r.length>0&&r.every(x=>p.responses.some(e=>e.generation===g&&e.message.requestId===x.message.requestId));})()"""


def run_paste(session, browser, row, plan, target):
    fresh(session, target); run_arm(session, browser, 's5cand', plan['cases'][row['sourceArm']])
    control(session, 'armSequence()')
    inputs.chain(session, browser, [('ArrowRight', ('shift',))])
    wait_page(session, EXTENSION_ANSWERED.replace('ARG_ARM', json.dumps('s5cand')))
    clipboard.press_ctrl_v(session, browser)
    wait_page(session, INSERT_ANSWERED)
    control(session, 'finishSequence()'); control(session, 'completeS5()')


def read(cell, plan, arm):
    """The T5 verdict of one repetition, from the exported page alone."""
    page = cell['page']; p = page['s5cand']; q = p['sequence']
    final = base64.b64decode(p['finalSave']['base64']); original = base64.b64decode(p['originalSave']['base64'])
    if digest(final) != p['finalSave']['sha256'] or digest(original) != p['originalSave']['sha256']:
        return {'verdict': 'NOT_ESTABLISHED', 'reason': 'save record differs from its hash'}
    before, after = paragraph_texts_from_xml(odt_content(original)), paragraph_texts_from_xml(odt_content(final))
    window = [r for r in page['requests'][q['requestStart']:q['requestEnd']] if r['generation'] == q['generation']]
    inserts = [r for r in window if r['message']['operation'] == 'insertText']
    replies = [next((x['message'] for x in page['responses'] if x['generation'] == r['generation']
                     and x['message'].get('requestId') == r['message']['requestId']), None) for r in inserts]
    keys = [x for x in page['inputs'][q['inputStart']:q['inputEnd']] if x['type'] == 'keydown' and x.get('key') not in ('Shift', 'Control')]
    a1, b1, route = EXPECTED[arm]
    out = {'A1': after[A1], 'B1': after[B1], 'originalEqualsFixture': before == plan['fixtureParagraphs'],
           'otherParagraphsUnchanged': [t for i, t in enumerate(after) if i not in (A1, B1)] == [t for i, t in enumerate(before) if i not in (A1, B1)],
           'keys': [(k.get('key'), bool(k.get('shiftKey')), bool(k.get('ctrlKey')), k.get('isTrusted')) for k in keys],
           'inserts': [{'payload': r['message']['payload'], 'reply': {k: (m or {}).get(k) for k in ('ok', 'result', 'error')}}
                       for r, m in zip(inserts, replies)]}
    want_keys = [('ArrowRight', True, False, True), ('x', False, False, True)] if arm == 'typed' \
        else [('ArrowRight', True, False, True), ('v', False, True, True)]
    reply = replies[0] if len(replies) == 1 else None
    ok = (out['originalEqualsFixture'] and out['otherParagraphsUnchanged'] and len(inserts) == 1 and reply is not None
          and inserts[0]['message']['payload'].get('text') == 'x' and inserts[0]['message']['payload'].get('route') == route
          and reply.get('ok') is True and reply['result'].get('method') == route
          and (reply['result'].get('completion') == 'uno-command-result') is (arm == 'typed')
          and out['keys'] == want_keys and (after[A1], after[B1]) == (a1, b1))
    return {**out, 'verdict': 'PASS' if ok else 'FAIL'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    plan = config(); row = plan['s5'][CASE]
    args.output.mkdir(parents=True, exist_ok=False); target = args.output.resolve() / 'mirror'; mirror(target, plan)
    report = {'schema': 1, 'argv': sys.argv, 'case': CASE, 'config': plan, 'mirrorBindings': verify_mirror(target, plan), 'runs': []}
    def write(): (args.output / 'report.json').write_bytes(encoded(report))
    write()
    with common.browser_lock('v24-t5'):
        report['preRun'] = common.pre_run_checks(); report['foreignCpu'] = common.foreign_cpu(); write()
        if report['preRun']['refuse']: raise SystemExit('pre-run refusal: ' + '; '.join(report['preRun']['refuse']))
        with common.served(target) as base:
            origin = '{0.scheme}://{0.netloc}'.format(urlsplit(base))
            for browser in BROWSERS:
                for arm in ('typed', 'paste'):
                    for n in range(1, args.repetitions + 1):
                        cell = {'browser': browser, 'arm': arm, 'repetition': n, 'caseId': CASE}; session = None
                        try:
                            if config() != plan: raise ValueError('source/profile drift')
                            verify_mirror(target, plan)
                            session = common.open_browser(browser, firefox_prefs=clipboard.FIREFOX_PREFS if arm == 'paste' and browser == 'firefox' else None)
                            navigate(session, base + '?' + urlencode({'caseId': CASE}))
                            wait_page(session, "Boolean(window.__featureSelection?.booted && window.__featureSelection?.currentOpen && !document.querySelector('#sink').disabled && !document.querySelector('#sink').readOnly)")
                            control(session, 'prepareReadiness()'); actual_Z(session); control(session, 'finishReadiness()')
                            initial, _ = export_page(session); readiness(Evidence(initial, plan, browser))
                            if arm == 'typed':
                                run_s5(session, browser, row, plan, target)
                            else:
                                cell['clipboardGrant'] = clipboard.grant(session, browser, origin)
                                cell['clipboardWrite'] = clipboard.write_text(session, 'x')
                                if not (cell['clipboardWrite'].get('ok') and cell['clipboardWrite'].get('same')):
                                    raise RuntimeError('clipboard write not read back')
                                run_paste(session, browser, row, plan, target)
                            cell['page'], _ = export_page(session)
                            cell['t5'] = read(cell, plan, arm)
                            if arm == 'typed': cell['s5Inspection'] = inspect(cell['page'], plan, browser)
                        except Exception:
                            cell['fatal'] = traceback.format_exc()
                            if session is not None:
                                try: cell['page'], _ = export_page(session)
                                except Exception: cell['exportFailure'] = traceback.format_exc()
                        finally:
                            if session is not None: cell['cleanup'] = common.close_browser(session)
                            path = args.output / f'{browser}-{arm}-{n}.json'; path.write_bytes(encoded(cell))
                            verdict = (cell.get('t5') or {}).get('verdict', 'FATAL')
                            report['runs'].append({'path': path.name, 'sha256': digest(path.read_bytes()), 'verdict': verdict}); write()
                            t5 = cell.get('t5') or {}
                            print(f"{browser} {arm} {n}: {verdict} A1={t5.get('A1')!r} B1={t5.get('B1')!r}", file=sys.stderr, flush=True)
    report['postConfig'] = config(); write()
    report['verdict'] = 'T5_HOLDS' if report['postConfig'] == plan and len(report['runs']) == 2 * 2 * args.repetitions \
        and all(r['verdict'] == 'PASS' for r in report['runs']) else 'T5_DOES_NOT_HOLD'
    write(); print(report['verdict'])
    return 0 if report['verdict'] == 'T5_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
