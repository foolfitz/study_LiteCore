#!/usr/bin/env python3
"""Ask the state behind the v24 format cells instead of inferring it (diagnostic, not K).

Two products served from a symlink mirror of dist/, each page with one Worker observer:
  v22  the 0.2.27 package (page 3b96cb16, profile e2-editor-v22), decoded and MANIFEST-checked
  v24  dist/ as served (page b15a6d8e, profile e2-editor-v24)
Chrome, fresh browser per scenario:
  bullet  the product-path check's own recipe (finding 053/046 cell): click past the line end,
          the toolbar paragraph break, then the bullet button; keep the full Worker reply.
  format  place the caret, then italic / marker / clear-format / marker / italic / marker /
          bold / marker / clear-format / marker; after every step the four toolbar aria-pressed
          values, toast, state; the saved ODT's style of every marker is the document's answer.
--out must not exist. Nothing under dist/ is written (overrides are materialised in the mirror).
"""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

V22_PACKAGE = ROOT / 'wasm_sdk_probe/build/archive/host-0.2.27-engine-817413d5ad5bd502'
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
PAGE = """(() => { const p = a => document.querySelector(`#toolbar button[data-action="${a}"]`)?.getAttribute('aria-pressed') ?? null;
  return {pill: document.querySelector('#state-pill')?.dataset.state, latency: document.querySelector('#s-latency')?.textContent,
    toast: document.querySelector('#toast')?.textContent, revision: document.querySelector('#s-revision')?.textContent,
    pressed: {bold: p('set-bold'), italic: p('set-italic'), underline: p('set-underline'), strikethrough: p('set-strikethrough')},
    blobs: window.__diag.blobs.length}; })()"""
BLOB = """(async () => { const b = window.__diag.blobs.at(-1); const u = new Uint8Array(await b.arrayBuffer());
  let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192)); return btoa(s); })()"""
FORMAT_STEPS = [('press', 'set-italic'), ('type', 'MKITALON'), ('clear', None), ('type', 'MKAFTERCLEAR'),
                ('press', 'set-italic'), ('type', 'MKITALAGAIN'), ('press', 'set-bold'), ('type', 'MKBOLDON'),
                ('clear', None), ('type', 'MKAFTERCLEAR2')]


def wait(session, predicate, limit):
    until, state = time.monotonic() + limit, None
    while time.monotonic() < until:
        state = evaluate(session, PAGE)
        if state and predicate(state):
            return state, True
        time.sleep(0.2)
    return state, False


def ready(session, base):
    navigate(session, base)
    return wait(session, lambda s: s['pill'] == 'ready', 240)


def styles_of(content, marker):
    autos = {m.group(1): m.group(2) for m in re.finditer(r'<style:style style:name="([TP]\d+)"[^>]*>(.*?)</style:style>', content, re.S)}
    span = re.search(r'<text:span text:style-name="(T\d+)">((?:(?!</text:span>).)*?)' + marker, content, re.S)
    para = re.search(r'<text:(?:p|h) text:style-name="([^"]+)"[^>]*>(?:(?!</text:(?:p|h)>).)*?' + marker, content, re.S)
    props = autos.get(span.group(1), '') if span else ''
    return {'found': marker in content, 'span': span.group(1) if span else None, 'paragraphStyle': para.group(1) if para else None,
            'bold': 'fo:font-weight="bold"' in props, 'italic': 'fo:font-style="italic"' in props,
            'underline': bool(re.search(r'style:text-underline-style="(?!none)', props)),
            'strikethrough': bool(re.search(r'style:text-line-through-style="(?!none)', props))}


def traffic(session):
    record = evaluate(session, 'window.__diag')
    replies = {r['message'].get('requestId'): r['message'] for r in record['responses']}
    out = []
    for q in record['requests']:
        op = q['message'].get('operation')
        if op not in ('editorActionV2', 'insertText'):
            continue
        reply = replies.get(q['message'].get('requestId')) or {}
        error = reply.get('error') or {}
        barrier = error.get('formatBarrier') or (error.get('details') or {}).get('formatBarrier') or None
        out.append({'operation': op, 'action': (q['message'].get('payload') or {}).get('action'),
                    'ok': reply.get('ok'), 'code': error.get('code'), 'message': error.get('message'),
                    'barrier': {k: barrier.get(k) for k in ('stage', 'route', 'dispatched', 'failureShape', 'resultSeen',
                                                             'resultSuccess', 'selectionResultSeen', 'command')} if barrier else None,
                    'resultFormat': ((reply.get('result') or {}).get('state') or {}).get('format'),
                    'errorKeys': sorted(error), 'errorDispatched': error.get('dispatched')})
    return out


def bullet(session, base):
    _, ok = ready(session, base)
    if not ok:
        return {'fatal': 'not ready'}
    evaluate(session, pp.CLEAR_TOAST)
    evaluate(session, pp.INDUCE_EMPTY_PARAGRAPH.replace('ARG_X', '0.92').replace('ARG_Y', '0.28'))
    wait(session, lambda s: '定位游標' in (s['latency'] or ''), 60)
    evaluate(session, pp.BREAK_THEN_LIST)
    wait(session, lambda s: '斷行' in (s['latency'] or '') or '段落' in (s['latency'] or ''), 30)
    evaluate(session, pp.CLEAR_TOAST)
    evaluate(session, pp.PRESS.replace('ARG_ACTION', 'set-list-unordered'))
    state, settled = wait(session, lambda s: s['pill'] in ('recoverable-error', 'restart-required') or '項目符號' in (s['toast'] or '')
                          or '項目符號' in (s['latency'] or ''), 60)
    time.sleep(1.0)
    return {'after': evaluate(session, PAGE), 'settled': settled, 'traffic': traffic(session)}


def fmt(session, base):
    _, ok = ready(session, base)
    if not ok:
        return {'fatal': 'not ready'}, None
    evaluate(session, pp.POINT_AT.replace('ARG_X', '0.35').replace('ARG_Y', '0.28'))
    wait(session, lambda s: '定位游標' in (s['latency'] or ''), 60)
    steps = [{'step': 'start', 'page': evaluate(session, PAGE)}]
    for kind, arg in FORMAT_STEPS:
        evaluate(session, pp.CLEAR_LATENCY)
        if kind == 'press':
            label = evaluate(session, pp.BUTTON_LABEL.replace('ARG_ACTION', arg))
            evaluate(session, pp.PRESS.replace('ARG_ACTION', arg))
            page, settled = wait(session, lambda s, w=label: bool(w) and w in (s['latency'] or ''), 30)
        elif kind == 'clear':
            evaluate(session, pp.CLEAR_FORMAT)
            page, settled = wait(session, lambda s: '清除格式' in (s['latency'] or ''), 30)
        else:
            before = evaluate(session, PAGE)['revision']
            evaluate(session, pp.SET_TEXT.replace('ARG_TEXT', arg))
            evaluate(session, pp.PRESS.replace('ARG_ACTION', 'insert-text'))
            page, settled = wait(session, lambda s, r=before: s['revision'] != r, 20)
        time.sleep(0.6)
        steps.append({'step': kind, 'arg': arg, 'settled': settled, 'page': evaluate(session, PAGE)})
    blobs = evaluate(session, PAGE)['blobs']
    evaluate(session, pp.PRESS.replace('ARG_ACTION', 'save'))
    wait(session, lambda s: s['blobs'] > blobs, 30)
    raw = base64.b64decode(evaluate(session, BLOB))
    content = zipfile.ZipFile(io.BytesIO(raw)).read('content.xml').decode('utf-8')
    markers = {arg: styles_of(content, arg) for kind, arg in FORMAT_STEPS if kind == 'type'}
    return {'steps': steps, 'saved': {'sha256': hashlib.sha256(raw).hexdigest(), 'markers': markers},
            'traffic': traffic(session)}, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=1)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((V22_PACKAGE / 'MANIFEST.json').read_bytes())
    v22 = {}
    for relative, record in manifest['files'].items():
        data = gzip.decompress((V22_PACKAGE / 'files' / (relative + '.gz')).read_bytes())
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise SystemExit('v22 package member differs from its MANIFEST: ' + relative)
        v22[relative] = data
    v22['e2-editor.html'] = common.inject(v22['e2-editor.html'].decode('utf-8'), [OBSERVER]).encode()
    v24 = {'e2-editor.html': common.inject((common.DIST / 'e2-editor.html').read_text(encoding='utf-8'), [OBSERVER]).encode()}
    products = {'v22': v22, 'v24': v24}
    report = {'argv': sys.argv, 'products': {k: {'page': hashlib.sha256(o.get('e2-editor-app.js') or (common.DIST / 'e2-editor-app.js').read_bytes()).hexdigest()}
                                             for k, o in products.items()}, 'runs': []}
    scratch = Path(tempfile.mkdtemp(prefix='diag-format-', dir=ROOT / 'wasm_sdk_probe/build'))
    with common.browser_lock('diag_format_v24'):
        report['preRun'] = common.pre_run_checks()
        for name, overrides in products.items():
            target = scratch / name  # the v22 wasm is materialised here, never under --out
            pp.build_mirror(common.DIST, target, overrides)
            with common.served(target) as base:
                for n in range(1, args.repetitions + 1):
                    for scenario in ('bullet', 'format'):
                        run, session = {'product': name, 'scenario': scenario, 'repetition': n}, None
                        try:
                            session = common.open_browser('chrome')
                            if scenario == 'bullet':
                                run.update(bullet(session, base))
                            else:
                                value, raw = fmt(session, base); run.update(value)
                                if raw:
                                    (args.out / f'{name}-format-{n}.odt').write_bytes(raw)
                        except Exception:
                            run['fatal'] = traceback.format_exc()
                        finally:
                            if session is not None:
                                run['cleanup'] = common.close_browser(session)
                        report['runs'].append(run)
                        print(name, scenario, n, 'fatal' if run.get('fatal') else 'ok', file=sys.stderr, flush=True)
    shutil.rmtree(scratch, ignore_errors=True)
    (args.out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
