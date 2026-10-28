#!/usr/bin/env python3
"""Diagnostic for T4's one changed outcome: `the-enter-key-reaches-the-document`, Shift+Enter arm.

On v24 (Chrome, pre-count/t4/chrome) the arm saw both markers in one paragraph but not the literal
`SHFTKEYA<text:line-break/>SHFTKEYB` in content.xml; on v23 it did.  The check keeps booleans, not
the XML.  This replays the arm's own sequence (tools/run_e2_c_product_path.py:8697-8712: toolbar
paragraph break, a beforeinput marker into the focused sink, a REAL Shift+Enter through CDP, a
second marker) on two products served from a mirror of dist/, and keeps the saved content.xml:

  v23   the generation-76 page and SDK (git c25b11c4... / 9dcb8312..., i.e. before the v24 cutover)
        over the v23 profile
  v24   dist/ as served (page b15a6d8e..., SDK afdff2d4..., profile e2-editor-v24)

The page gets one observer <script> (Worker traffic, every operation; the product's save Blob kept
instead of downloaded).  Chrome only (a real key needs CDP).  --out must not exist.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp
import v21_shakedown_common as common
import v21_input as inputs
from r7_support import evaluate
from run_e2_c_page_smoke import navigate

PROJECT, DIST = common.PROJECT, common.DIST
V76 = {'web/e2-editor-app.js': ('008efd722', 'c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490'),
       'sdk/document-sdk.js': ('ceaa2770', '9dcb83120c144cad5cf04cabcc14452255d0a640200b8e08f5eed4d4c2d63539')}
OBSERVER = """<script>
(() => {
  const rec = window.__diag = {requests: [], responses: [], blobs: []};
  const strip = (k, x) => (x instanceof ArrayBuffer || ArrayBuffer.isView(x)) ? {bytes: x.byteLength} : x;
  const snap = v => { try { return JSON.parse(JSON.stringify(v, strip)); } catch (e) { return {unserialisable: String(e)}; } };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options);
      this.addEventListener('message', ev => { if (ev.data?.kind === 'response') rec.responses.push({at: performance.now(), message: snap(ev.data)}); }); }
    postMessage(m, ...rest) { if (m?.kind === 'request') rec.requests.push({at: performance.now(), message: snap(m)}); return super.postMessage(m, ...rest); }
  };
  const create = URL.createObjectURL.bind(URL);
  URL.createObjectURL = blob => { if (blob instanceof Blob) rec.blobs.push(blob); return create(blob); };
  const click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { if (this.hasAttribute('download')) return; return click.call(this); };
})();
</script>"""
STATE = """(() => ({pill: document.querySelector('#state-pill')?.dataset.state, doc: document.querySelector('#s-doc')?.textContent,
  revision: Number(document.querySelector('#s-revision')?.textContent), active: document.activeElement?.id || null,
  blobs: window.__diag.blobs.length}))()"""
BLOB = """(async () => { const b = window.__diag.blobs.at(-1); const u = new Uint8Array(await b.arrayBuffer());
  let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192)); return btoa(s); })()"""


def wait(session, predicate, limit, what):
    until = time.monotonic() + limit
    while time.monotonic() < until:
        state = evaluate(session, STATE)
        if predicate(state):
            return state
        time.sleep(0.2)
    raise RuntimeError(f'{what}: not reached; last {state}')


def shift_enter(session):
    for kind in ('rawKeyDown', 'char', 'keyUp'):
        payload = {'type': kind, 'key': 'Enter', 'windowsVirtualKeyCode': 13, 'nativeVirtualKeyCode': 13, 'code': 'Enter', 'modifiers': 8}
        if kind == 'char':
            payload['text'] = '\r'
        session.call('Input.dispatchKeyEvent', payload)
    time.sleep(1.5)


def save_now(session):
    blobs = evaluate(session, STATE)['blobs']
    evaluate(session, pp.PRESS.replace('ARG_ACTION', 'save'))
    wait(session, lambda s: s['blobs'] > blobs, 30, 'save')
    raw = base64.b64decode(evaluate(session, BLOB))
    return raw, zipfile.ZipFile(io.BytesIO(raw)).read('content.xml').decode('utf-8')


def replay(session, base):
    """The check's own steps (run_e2_c_product_path.py:8663-8754), both arms in order, with the
    runner's caret helpers; saves through the product button, kept here instead of its shim."""
    navigate(session, base)
    wait(session, lambda s: s['doc'] == 'list-contexts.odt' and s['pill'] == 'ready', 240, 'open')
    evaluate(session, pp.CLEAR_TOAST)
    evaluate(session, pp.OPEN_FILE.replace('ARG_URL', './e1-fixtures/list-contexts.odt').replace('ARG_NAME', 'enter-key.odt'))
    pp.wait_for(session, lambda s: (s.get('doc') or '') == 'enter-key.odt' and s.get('state') == 'ready', 90)
    arms, files = [], {}
    for shift, first, second in ((False, 'ENTKEYA', 'ENTKEYB'), (True, 'SHFTKEYA', 'SHFTKEYB')):
        aim = pp.caret_click_fractions(evaluate(session, pp.LINE_INK.replace('ARG_Y', '0.24')) or {})
        pp.place_caret_and_settle(session, pp.POINT_AT, aim['near'], '0.24')
        evaluate(session, pp.PRESS.replace('ARG_ACTION', 'insert-paragraph-break')); time.sleep(1.2)
        before = pp.revision_of(evaluate(session, pp.READ_STATE))
        evaluate(session, pp.TYPE_WHEREVER_FOCUS_IS.replace('ARG_TEXT', first))
        pp.wait_for(session, lambda st, f=before: pp.revision_of(st) is not None and f is not None and pp.revision_of(st) > f, 12)
        _, baseline = save_now(session)
        for kind in ('rawKeyDown', 'char', 'keyUp'):
            payload = {'type': kind, 'key': 'Enter', 'windowsVirtualKeyCode': 13, 'nativeVirtualKeyCode': 13, 'code': 'Enter', 'modifiers': 8 if shift else 0}
            if kind == 'char': payload['text'] = '\r'
            session.call('Input.dispatchKeyEvent', payload)
        time.sleep(1.5)
        before = pp.revision_of(evaluate(session, pp.READ_STATE))
        evaluate(session, pp.TYPE_WHEREVER_FOCUS_IS.replace('ARG_TEXT', second))
        pp.wait_for(session, lambda st, f=before: pp.revision_of(st) is not None and f is not None and pp.revision_of(st) > f, 12)
        raw, content = save_now(session)
        files[first] = raw
        para = [m.group(0) for m in re.finditer(r'<text:(?:p|h)\b[^>]*>(?:(?!</text:(?:p|h)>).)*' + first + r'(?:(?!</text:(?:p|h)>).)*</text:(?:p|h)>', content, re.S)]
        arms.append({'shift': shift, 'aim': aim, 'paragraphXml': para, 'literal': f'{first}<text:line-break/>{second}' in content,
                     'baselineParagraphXml': [m.group(0) for m in re.finditer(r'<text:(?:p|h)\b[^>]*>(?:(?!</text:(?:p|h)>).)*' + first + r'(?:(?!</text:(?:p|h)>).)*</text:(?:p|h)>', baseline, re.S)]})
    record = evaluate(session, 'window.__diag')
    replies = {r['message']['requestId']: r['message'] for r in record['responses']}
    edits = [{'operation': q['message']['operation'], 'payload': {k: v for k, v in (q['message'].get('payload') or {}).items() if k in ('action', 'text', 'route', 'extendSelection')},
              'reply': {k: v for k, v in (replies.get(q['message']['requestId']) or {}).items() if k in ('ok', 'error')} |
                       {'result': {k: v for k, v in ((replies.get(q['message']['requestId']) or {}).get('result') or {}).items() if k in ('method', 'completion', 'revision', 'action', 'changed')}}}
             for q in record['requests'] if q['message']['operation'] in ('insertText', 'editorActionV2')]
    return {'arms': arms, 'edits': edits}, files


def run_arm(session, base):
    navigate(session, base)
    wait(session, lambda s: s['doc'] == 'list-contexts.odt' and s['pill'] == 'ready', 240, 'open')
    rect = evaluate(session, inputs.PAPER_RECT)
    inputs.click(session, 'chrome', rect['left'] + rect['width'] * 0.3, rect['top'] + rect['height'] * 0.24)
    time.sleep(1.0)
    evaluate(session, pp.PRESS.replace('ARG_ACTION', 'insert-paragraph-break')); time.sleep(1.2)
    steps = []
    for name, act in (('SHFTKEYA', None), ('shift-enter', shift_enter), ('SHFTKEYB', None)):
        before = evaluate(session, STATE)
        if act is None:
            steps.append({'type': name, 'into': evaluate(session, pp.TYPE_WHEREVER_FOCUS_IS.replace('ARG_TEXT', name))})
            wait(session, lambda s, r=before['revision']: s['revision'] > r, 12, 'marker ' + name)
        else:
            act(session); steps.append({'key': name, 'stateAfter': evaluate(session, STATE)})
    time.sleep(1.0)
    blobs = evaluate(session, STATE)['blobs']
    evaluate(session, pp.PRESS.replace('ARG_ACTION', 'save'))
    wait(session, lambda s: s['blobs'] > blobs, 30, 'save')
    raw = base64.b64decode(evaluate(session, BLOB))
    content = zipfile.ZipFile(io.BytesIO(raw)).read('content.xml').decode('utf-8')
    record = evaluate(session, 'window.__diag')
    ops = [(q['message']['operation'], {k: v for k, v in (q['message'].get('payload') or {}).items() if k in ('action', 'text', 'route', 'extendSelection')})
           for q in record['requests'] if q['message']['operation'] not in ('paint', 'editorGetStateV2', 'pageRectangles')]
    replies = {r['message']['requestId']: r['message'] for r in record['responses']}
    edits = [{'operation': q['message']['operation'], 'payload': {k: v for k, v in (q['message'].get('payload') or {}).items() if k != 'buffer'},
              'reply': {k: replies.get(q['message']['requestId'], {}).get(k) for k in ('ok', 'result', 'error')}}
             for q in record['requests'] if q['message']['operation'] in ('insertText', 'editorActionV2')]
    for e in edits:
        if isinstance(e['reply'].get('result'), dict):
            e['reply']['result'] = {k: v for k, v in e['reply']['result'].items() if k != 'resultPayload'}
    para = [m.group(0) for m in re.finditer(r'<text:(p|h)\b[^>]*>(?:(?!</text:(?:p|h)>).)*SHFTKEYA(?:(?!</text:(?:p|h)>).)*</text:(?:p|h)>', content, re.S)]
    return {'steps': steps, 'operations': ops, 'edits': edits, 'saveSha256': hashlib.sha256(raw).hexdigest(),
            'paragraphXml': para, 'literalPresent': 'SHFTKEYA<text:line-break/>SHFTKEYB' in content,
            'automaticStyles': re.findall(r'<style:style style:name="T[0-9]+"[^>]*>.*?</style:style>', content, re.S)[:6]}, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=2)
    parser.add_argument('--replay', action='store_true', help="the check's own two arms, in order, with the runner's caret helpers")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    html = common.inject((DIST / 'e2-editor.html').read_text(encoding='utf-8'), [OBSERVER]).encode()
    old = {}
    for path, (commit, want) in V76.items():
        raw = subprocess.run(['git', '-C', str(PROJECT), 'show', f'{commit}:wasm_sdk_probe/{path}'], capture_output=True, check=True).stdout
        if hashlib.sha256(raw).hexdigest() != want:
            raise SystemExit('generation-76 bytes differ: ' + path)
        old[path.removeprefix('web/')] = raw
    products = {'v23': {'e2-editor.html': html, **old}, 'v24': {'e2-editor.html': html}}
    report = {'argv': sys.argv, 'products': {k: {p: hashlib.sha256(v).hexdigest() for p, v in o.items()} for k, o in products.items()}, 'runs': []}
    with common.browser_lock('diag_v24_shift_enter'):
        report['preRun'] = common.pre_run_checks()
        for name, overrides in products.items():
            target = args.out / 'mirror' / name
            pp.build_mirror(DIST, target, overrides)
            with common.served(target) as base:
                for n in range(1, args.repetitions + 1):
                    run = {'product': name, 'repetition': n}; session = None
                    try:
                        session = common.open_browser('chrome')
                        if args.replay:
                            value, files = replay(session, base); run.update(value)
                            for marker, raw in files.items(): (args.out / f'{name}-{n}-{marker}.odt').write_bytes(raw)
                        else:
                            value, raw = run_arm(session, base); run.update(value)
                            (args.out / f'{name}-{n}.odt').write_bytes(raw)
                    except Exception:
                        run['fatal'] = traceback.format_exc()
                    finally:
                        if session is not None: run['cleanup'] = common.close_browser(session)
                    report['runs'].append(run)
                    for arm in run.get('arms') or [{'literal': run.get('literalPresent'), 'paragraphXml': run.get('paragraphXml')}]:
                        print(name, n, 'literal' if arm.get('literal') else 'NO literal', (arm.get('paragraphXml') or ['?'])[0][:300], file=sys.stderr, flush=True)
                    if run.get('fatal'): print(run['fatal'][-600:], file=sys.stderr)
    (args.out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
