#!/usr/bin/env python3
"""Scratch diagnostic: the owner's report -- a NEW blank document, press the bullet button -> restart notice.

Products v22 (0.2.27 package = the 0.2.38 engine line), v24 (own bytes), v25 (dist/). Chrome. The blank ODT
is the host's own template for a zh_TW user (blank/en-US_zh-TW_A4.odt), opened through the page's file input.
Two arms: press bullet right after the document opens (no click), and after clicking into the paragraph.
"""
import base64, gzip, hashlib, importlib.util, json, sys, tempfile, time, traceback, shutil
from pathlib import Path

ROOT = Path('/home/jiajun/LibreOffice/study_LiteCore')
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
spec = importlib.util.spec_from_file_location('f1', ROOT / 'findings/evidence/link-batch-v25/f1/diag_format_v25.py')
f1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f1)
diag, pp, common, products = f1.diag, f1.pp, f1.common, f1.products
from r7_support import evaluate

BLANK = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore/blank/en-US_zh-TW_A4.odt')
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=False)
raw_blank = BLANK.read_bytes()


def run(session, base, click):
    state, ok = f1.ready(session, base)  # installs the worker JSON.parse observer
    if not ok:
        return {'fatal': 'not ready'}
    before_requests = len(evaluate(session, 'window.__diag.requests'))
    evaluate(session, pp.OPEN_BYTES.replace('ARG_B64', base64.b64encode(raw_blank).decode()).replace('ARG_NAME', BLANK.name))
    time.sleep(1.0)
    opened, ok = diag.wait(session, lambda s: s['pill'] == 'ready', 120)
    time.sleep(1.5)
    # The opened document runs in a NEW worker: re-attach the engine-record observer to it.
    try:
        session.call('Target.setAutoAttach', {'autoAttach': False, 'flatten': True, 'waitForDebuggerOnStart': False})
    except Exception as error:
        pass
    sid, why = f1.attach_worker(session)
    session._raw_sid = sid
    session._raw_install = f1.worker_eval(session, f1.RAW_INSTALL) if sid else why
    if click:
        evaluate(session, pp.POINT_AT.replace('ARG_X', '0.30').replace('ARG_Y', '0.10'))
        diag.wait(session, lambda s: '定位游標' in (s['latency'] or ''), 30)
        time.sleep(0.8)
    evaluate(session, pp.CLEAR_TOAST)
    evaluate(session, pp.PRESS.replace('ARG_ACTION', 'set-list-unordered'))
    after, settled = diag.wait(session, lambda s: s['pill'] in ('recoverable-error', 'restart-required')
                               or '項目符號' in (s['toast'] or '') or '項目符號' in (s['latency'] or ''), 60)
    time.sleep(1.5)
    notice = evaluate(session, "(() => ({show: document.querySelector('#notice')?.dataset.show, text: document.querySelector('#notice-text')?.textContent || document.querySelector('[data-rescue]')?.textContent}))()")
    rows = f1._traffic(session)
    try:
        raw = f1.worker_eval(session, 'self.__rawEngine ?? null') if session._raw_sid else None
    except Exception as error:
        raw = {'error': str(error)}
    session._raw = raw
    return {'openedReady': ok, 'opened': opened, 'click': click, 'after': evaluate(session, diag.PAGE),
            'settled': settled, 'notice': notice, 'traffic': rows, 'raw': getattr(session, '_raw', None),
            'rawInstall': getattr(session, '_raw_install', None)}


def main():
    manifest = json.loads((diag.V22_PACKAGE / 'MANIFEST.json').read_bytes())
    v22 = {}
    for relative, record in manifest['files'].items():
        data = gzip.decompress((diag.V22_PACKAGE / 'files' / (relative + '.gz')).read_bytes())
        assert hashlib.sha256(data).hexdigest() == record['sha256']
        v22[relative] = data
    v22['e2-editor.html'] = common.inject(v22['e2-editor.html'].decode(), [diag.OBSERVER]).encode()
    report = {'blank': {'path': str(BLANK), 'sha256': hashlib.sha256(raw_blank).hexdigest()}, 'runs': [], 'products': {}}
    scratch = Path(tempfile.mkdtemp(prefix='blank-bullet-', dir=ROOT / 'wasm_sdk_probe/build'))
    try:
        with common.browser_lock('blank_bullet_scratch'):
            for name in ('v25', 'v24', 'v22'):
                target = scratch / name
                if name == 'v22':
                    pp.build_mirror(common.DIST, target, v22)
                else:
                    pp.build_mirror(common.DIST, target, products.overrides(name, [diag.OBSERVER]))
                    report['products'][name] = products.identity(name, target)['ok']
                with common.served(target) as base:
                    for click in (False, True):
                        r, session = {'product': name, 'click': click}, None
                        try:
                            session = common.open_browser('chrome')
                            r.update(run(session, base, click))
                        except Exception:
                            r['fatal'] = traceback.format_exc()
                        finally:
                            if session is not None:
                                common.close_browser(session)
                        report['runs'].append(r)
                        a = r.get('after') or {}
                        print(name, 'click' if click else 'noclick', a.get('pill'), (a.get('toast') or '')[:90], file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')


main()
