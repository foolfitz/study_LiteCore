#!/usr/bin/env python3
"""PL-1 (SPEC-M3-v27-finding-176 7.2): before the relink, would v27's rule verify the multi-block records that
v26's WASM engine writes today?  Local mirror of dist/ (generation 80, profile e2-editor-v26), no DDEV, no link.

Two recipes, each on Chrome and Firefox, N repetitions, a fresh browser per run:

  list-contexts  F3's cell, exactly as findings/evidence/host-0.2.39/k-nine-cells/diag-format/diag_format.py's
                 `bullet` drives it (imported by path, not edited): the page's own document, the synthetic
                 pointer at (0.92, 0.28) of #paper, the toolbar paragraph break, the bullet button.
  s3             S3's recipe (spec 7.3) up to the press: ../fixture-two-plain/build-01/two-plain.odt (sha pinned
                 below; the native core's one save of finding 176's two-plain.fodt) opened through the page's file
                 input; a REAL click past the end of the first line, a REAL Enter, a REAL click on the bullet
                 button (tools/v21_input.py: Chrome CDP Input.*, Firefox WebDriver actions).

The engine's own record, not the worker's projection (the worker drops `readback`).  One extraction function,
KEEP_JS, keeps for every engine `error` / `editor-action-completed` event: route, failureShape, dispatched,
selectionTypeReadable, paragraphIdentity's four inputs, readback.{parsed, unknownTag, malformedNesting,
footnoteApparatus, multiBlock, blockCount, itemCount, listTag, blockTag, expectedListTag, expectedBlockTag,
restoreConfirmed, html}.  Two transports, a closed list:

  chrome   v25 F1's observer (findings/evidence/link-batch-v25/f1/diag_format_v25.py): after the document is
           ready, CDP Target.setAutoAttach reaches the document worker and wraps its JSON.parse in place (same
           value returned).  No served byte changes.  Derived here, not imported, for one difference: it installs
           into EVERY attached sdk-worker target (opening a file starts a new worker), not only the last.
  firefox  CDP is Chrome-only, so the mirror serves a DIAGNOSTIC copy of the v26 worker: the archived worker's
           bytes, unchanged, followed by DIAG_SUFFIX (the same KEEP_JS, posting each kept record on
           BroadcastChannel "pl1-raw-engine"; the page listens with CHANNEL_LISTENER).  Appended, not prepended:
           the worker opens with "use strict", which must stay its first statement.  wasm, loader and manifest
           bytes are the archive's; the identity records `instrumentedWorker: true` and the evidence class is
           `diagnostic` (finding 046's diagnostic-profile precedent).  The worker's own postMessage channel to
           the page is not touched.

Products (identity checked file by file before use; a mirror whose identity fails is not run):
  served profile files = tools/v80_four_arms_identity.ARTIFACT_PINS (the v26 archive), except the diagnostic
  worker = archive worker + DIAG_SUFFIX exactly; every generation-80 bundle member served with the sha256
  e2/editor-shell-v2-bundle-v80.json records; the page is generation 80's (3b6c023e) and points at v26; the HTML
  is dist/'s with exactly the instrument snippets.

--out must not exist.  Nothing under dist/ is written.  Verdict: read_v27_pl1.py, from report.json only.  Not a
timing measurement: no desk gate.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / 'wasm_sdk_probe'
sys.path.insert(0, str(PROJECT / 'tools'))
import check_v79_blank_bullet as b1  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v80_four_arms_identity as v80  # noqa: E402
from r7_support import evaluate  # noqa: E402

DIAG_SOURCE = ROOT / 'findings/evidence/host-0.2.39/k-nine-cells/diag-format/diag_format.py'
_spec = importlib.util.spec_from_file_location('diag_format', DIAG_SOURCE)
diag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diag)

FIXTURE = ROOT / 'findings/evidence/v27-176/fixture-two-plain/build-01/two-plain.odt'
FIXTURE_SHA256 = '56bc01b03b094b8da784fa98419873009fb887c8bf62953d0574f71c18a497a9'
PROFILE = 'e2-editor-v26'
PROFILE_DIR = f'profiles/{PROFILE}'
PROFILE_FILES = ('probe.wasm', 'probe.js', 'sdk-worker.js', 'sdk-manifest.json')
# Past "Plain first", on the first line.  #paper is the LOK document area, which has a 284-twip (0.5 cm) border on
# every side (900 x 1256 px = 22 x 30.7 cm): y = (0.5 + 2 cm margin + half a 12 pt line) / 30.7 cm.  The
# shakedown's first value, 0.0757 (the border left out), landed in the top margin and the caret went to the
# START of the line (the bullet then verified on "Plain first": a single block, not 046's cell).
LINE_END = (0.80, 0.0894)
RECIPES = ('list-contexts', 's3')
CHANNEL = 'pl1-raw-engine'

KEEP_JS = """function __pl1Keep(v) {
  const b = v.formatBarrier, has = (o, k) => !!o && typeof o === 'object' && Object.prototype.hasOwnProperty.call(o, k);
  const pick = (o, keys) => (o && typeof o === 'object') ? Object.fromEntries(keys.map(k => [k, has(o, k) ? o[k] : null])) : null;
  return {type: v.type, requestId: v.requestId ?? null, code: v.code ?? null, completion: v.completion ?? null,
    barrier: (b && typeof b === 'object') ? Object.assign(
      pick(b, ['command', 'stage', 'dispatched', 'failureShape', 'route', 'selectionTypeReadable']),
      {hasDispatched: has(b, 'dispatched'), hasUndo: has(b, 'undo'),
       paragraphIdentity: pick(b.paragraphIdentity, ['checked', 'dispatchKnown', 'readbackKnown', 'dispatchUsable', 'readbackUsable']),
       readback: pick(b.readback, ['parsed', 'unknownTag', 'malformedNesting', 'footnoteApparatus', 'multiBlock',
         'blockCount', 'itemCount', 'listTag', 'blockTag', 'expectedListTag', 'expectedBlockTag', 'restoreConfirmed', 'html'])})
      : null};
}"""

WRAP_JS = """const parse = JSON.parse;
  JSON.parse = function (text, reviver) {
    const v = parse.call(JSON, text, reviver);
    try {
      if (v && typeof v === 'object' && (v.type === 'error' || v.type === 'editor-action-completed')) SINK(__pl1Keep(v));
    } catch (e) {}
    return v;
  };"""

CDP_INSTALL = ("(() => {\n  if (self.__pl1Raw) return 'already';\n  const rec = self.__pl1Raw = [];\n  " + KEEP_JS + "\n  "
               + WRAP_JS.replace('SINK(', 'rec.push(') + "\n  return 'installed';\n})()")

DIAG_SUFFIX = ("\n// PL-1 DIAGNOSTIC (SPEC-M3-v27-finding-176 7.2 PL-1): served in a local mirror only, never shipped.\n"
               "// Everything above this comment is the archived e2-editor-v26 worker, byte for byte.  This wraps\n"
               "// JSON.parse (same value returned) and posts the kept fields of each engine error/completion on a\n"
               f"// BroadcastChannel; the worker's own messages to the page are untouched.\n"
               "(() => {\n  const channel = new BroadcastChannel('" + CHANNEL + "');\n  " + KEEP_JS + "\n  "
               + WRAP_JS.replace('SINK(', 'channel.postMessage(') + "\n})();\n")

CHANNEL_LISTENER = """<script>
(() => {
  const rec = window.__pl1Raw = [];
  try { const ch = new BroadcastChannel('""" + CHANNEL + """'); ch.onmessage = (ev) => rec.push(ev.data); window.__pl1Channel = 'open'; }
  catch (e) { window.__pl1Channel = String(e); }
})();
</script>"""

SNIPPETS = [diag.OBSERVER, b1.OBSERVER, CHANNEL_LISTENER]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


# ------------------------------------------------------------------ products

def overrides(diagnostic):
    html = common.inject((common.DIST / 'e2-editor.html').read_text(encoding='utf-8'), SNIPPETS)
    out = {'e2-editor.html': html.encode('utf-8')}
    if diagnostic:
        out[f'{PROFILE_DIR}/sdk-worker.js'] = (v80.ARCHIVED_PROFILE / 'sdk-worker.js').read_bytes() + DIAG_SUFFIX.encode()
    return out


def identity(mirror, diagnostic):
    served = {f: sha256((mirror / PROFILE_DIR / f).read_bytes()) for f in PROFILE_FILES}
    archive_worker = (v80.ARCHIVED_PROFILE / 'sdk-worker.js').read_bytes()
    worker = (mirror / PROFILE_DIR / 'sdk-worker.js').read_bytes()
    bundle = json.loads((PROJECT / v80.BUNDLE).read_text(encoding='utf-8'))
    recorded = {e['path']: e['sha256'] for e in bundle['included']}
    shell = {p: sha256((mirror / pp.served_in_dist(p)).read_bytes()) for p in recorded}
    page = (mirror / 'e2-editor-app.js').read_text(encoding='utf-8')
    html = (mirror / 'e2-editor.html').read_bytes()
    expected_html = common.inject((common.DIST / 'e2-editor.html').read_text(encoding='utf-8'), SNIPPETS).encode()
    checks = {
        'bundleFileIsGeneration80': sha256((PROJECT / v80.BUNDLE).read_bytes()) == v80.BUNDLE_FILE_SHA256,
        'shellEqualsGeneration80': all(shell[p] == recorded[p] for p in recorded),
        'pageIsGeneration80': shell['web/e2-editor-app.js'] == v80.PAGE_SHA256,
        'pagePointsAtV26': f'workerUrl: "./{PROFILE_DIR}/sdk-worker.js"' in page,
        'htmlIsDistPlusSnippets': html == expected_html,
        'wasmLoaderManifestEqualArchive': all(served[f] == v80.ARTIFACT_PINS[f] for f in PROFILE_FILES if f != 'sdk-worker.js'),
        'archiveWorkerIsPinned': sha256(archive_worker) == v80.ARTIFACT_PINS['sdk-worker.js'],
    }
    if diagnostic:
        checks['workerIsArchivePlusSuffixExactly'] = worker == archive_worker + DIAG_SUFFIX.encode()
    else:
        checks['workerEqualsArchive'] = served['sdk-worker.js'] == v80.ARTIFACT_PINS['sdk-worker.js']
    return {'profile': PROFILE, 'archive': str(v80.ARCHIVED_PROFILE.relative_to(ROOT)), 'servedProfile': served,
            'instrumentedWorker': served['sdk-worker.js'] != v80.ARTIFACT_PINS['sdk-worker.js'],
            'evidenceClass': 'diagnostic' if diagnostic else 'observer-only',
            'generation': 80, 'bundle': v80.BUNDLE, 'pageSha256': shell['web/e2-editor-app.js'],
            'htmlServedSha256': sha256(html), 'distHtmlSha256': sha256((common.DIST / 'e2-editor.html').read_bytes()),
            'snippetSha256': [sha256(s.encode()) for s in SNIPPETS], 'diagSuffixSha256': sha256(DIAG_SUFFIX.encode()),
            'checks': checks, 'ok': all(checks.values())}


# ------------------------------------------------------------------ the engine's record

def attach_workers(session, settle=4.0):
    """Every attached document worker's CDP session id (v25 F1's attach_worker, read by hand for the same reason:
    the attach events arrive before the answer and `call` would drop them; here ALL sdk-worker targets)."""
    websocket = session.websocket
    session.next_id += 1
    message_id = session.next_id
    websocket.send(json.dumps({'id': message_id, 'method': 'Target.setAutoAttach',
                               'params': {'autoAttach': True, 'flatten': True, 'waitForDebuggerOnStart': False}}))
    attached, deadline = [], time.monotonic() + settle
    while time.monotonic() < deadline:
        try:
            message = json.loads(websocket.recv(timeout=0.5))
        except Exception:  # noqa: BLE001 -- a quiet socket is not an error
            continue
        if message.get('method') == 'Target.attachedToTarget':
            attached.append(message['params'])
        elif message.get('id') == message_id and 'error' in message:
            return [], f"setAutoAttach: {message['error']}"
    workers = [{'sessionId': a['sessionId'], 'url': a['targetInfo'].get('url')} for a in attached
               if a['targetInfo'].get('type') == 'worker' and a['targetInfo'].get('url', '').endswith('sdk-worker.js')]
    return workers, None if workers else 'no document worker attached'


def worker_eval(session, sid, expression):
    reply = session.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True}, session_id=sid, timeout=20)
    return (reply.get('result') or {}).get('value')


def install(session, browser):
    """Chrome: attach and wrap now (after the document this run measures is ready).  Firefox: the channel."""
    if browser != 'chrome':
        session._pl1 = {'transport': 'broadcast-channel', 'channel': evaluate(session, 'window.__pl1Channel ?? null')}
        return
    workers, why = attach_workers(session)
    for w in workers:
        try:
            w['install'] = worker_eval(session, w['sessionId'], CDP_INSTALL)
        except Exception as error:  # noqa: BLE001 -- recorded
            w['install'] = f'{type(error).__name__}: {error}'
    session._pl1 = {'transport': 'cdp-auto-attach', 'workers': workers, 'attachError': why}


def collect(session, browser):
    if browser != 'chrome':
        return evaluate(session, 'window.__pl1Raw ?? null')
    out = []
    for w in session._pl1['workers']:
        try:
            records = worker_eval(session, w['sessionId'], 'self.__pl1Raw ?? null')
        except Exception as error:  # noqa: BLE001 -- a worker that has gone (the default document's) is recorded
            w['readError'] = f'{type(error).__name__}: {error}'
            continue
        out.extend(dict(r, worker=w['url']) for r in records or [])
    return out


# ------------------------------------------------------------------ recipes

def list_contexts(session, browser, base):
    _ready = diag.ready

    def ready(s, b):
        state = _ready(s, b)
        install(s, browser)
        return state
    diag.ready = ready
    try:
        run = diag.bullet(session, base)
    finally:
        diag.ready = _ready
    run['raw'] = collect(session, browser)
    return run


def s3(session, browser, base, raw_doc):
    b1.navigate(session, base)
    _, ok = b1.wait(session, lambda s: s['pill'] == 'ready', 240)
    if not ok:
        return {'fatal': 'page not ready'}
    workers = evaluate(session, b1.PAGE)['workers']
    opened = evaluate(session, pp.OPEN_BYTES.replace('ARG_B64', base64.b64encode(raw_doc).decode())
                      .replace('ARG_NAME', FIXTURE.name))
    state, ok = b1.wait(session, lambda s: s['workers'] > workers and s['pill'] == 'ready', 120)
    if not ok:
        return {'fatal': f'document not opened ({opened})', 'page': state}
    time.sleep(1.5)
    install(session, browser)
    out = {'opened': evaluate(session, b1.PAGE)}
    evaluate(session, real.SCROLL_TO_FRACTION.replace('ARG_F', repr(LINE_END[1])))
    time.sleep(0.25)
    rect = evaluate(session, real.PAPER_RECT)
    point = (rect['left'] + rect['width'] * LINE_END[0], rect['top'] + rect['height'] * LINE_END[1])
    out['clickAt'] = {'fraction': LINE_END, 'viewport': point, 'paper': rect}
    real.click(session, browser, *point)
    out['clicked'], out['caretPlaced'] = b1.wait(session, lambda s: '定位游標' in (s['latency'] or ''), 30)
    time.sleep(0.8)
    before = evaluate(session, b1.PAGE)
    real.key(session, browser, 'Enter')
    out['entered'], out['enterSettled'] = b1.wait(
        session, lambda s: s['requests'] > before['requests'] and s['responses'] >= s['requests']
        and s['revision'] != before['revision'], 30)
    out['enterRows'] = b1.rows(session, before['requests'])
    time.sleep(0.8)
    evaluate(session, pp.CLEAR_TOAST)
    start = evaluate(session, b1.PAGE)['requests']
    box = evaluate(session, b1.BULLET_BOX)
    if not box:
        out['fatal'] = 'no bullet button'
        return out
    real.click(session, browser, box['x'], box['y'])
    _, out['pressSettled'] = b1.wait(session, lambda s: s['pill'] in ('recoverable-error', 'restart-required')
                                     or '項目符號' in (s['latency'] or ''), 60)
    time.sleep(1.5)
    out['press'] = evaluate(session, b1.PAGE)
    out['pressRows'] = b1.rows(session, start)
    out['raw'] = collect(session, browser)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    parser.add_argument('--recipes', default=','.join(RECIPES))
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    raw_doc = FIXTURE.read_bytes()
    if sha256(raw_doc) != FIXTURE_SHA256:
        raise SystemExit('two-plain.odt changed: ' + sha256(raw_doc))
    config = {'browsers': [x for x in args.browsers.split(',') if x], 'recipes': [x for x in args.recipes.split(',') if x],
              'repetitions': args.repetitions}
    report = {'argv': sys.argv, 'tool': 'run_v27_pl1', 'config': config,
              'sources': {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in
                          (Path(__file__), DIAG_SOURCE, PROJECT / 'tools/check_v79_blank_bullet.py',
                           PROJECT / 'tools/v21_input.py', PROJECT / 'tools/v80_four_arms_identity.py')},
              'fixture': {'path': str(FIXTURE.relative_to(ROOT)), 'sha256': sha256(raw_doc)},
              'lineEnd': LINE_END, 'products': {}, 'runs': []}
    scratch = Path(tempfile.mkdtemp(prefix='v27-pl1-', dir=PROJECT / 'build'))
    try:
        with common.browser_lock('run_v27_pl1'):
            report['preRun'] = common.pre_run_checks()
            if report['preRun']['refuse']:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for browser in config['browsers']:
                diagnostic = browser != 'chrome'
                mirror = scratch / browser
                pp.build_mirror(common.DIST, mirror, overrides(diagnostic))
                report['products'][browser] = identity(mirror, diagnostic)
                if not report['products'][browser]['ok']:
                    print(browser, 'identity FAILED, not run:', report['products'][browser]['checks'], file=sys.stderr, flush=True)
                    continue
                with common.served(mirror) as base:
                    for recipe in config['recipes']:
                        for n in range(1, args.repetitions + 1):
                            run, session = {'browser': browser, 'recipe': recipe, 'repetition': n}, None
                            try:
                                session = common.open_browser(browser)
                                run['browserVersion'] = getattr(session, 'version', None)
                                run.update(list_contexts(session, browser, base) if recipe == 'list-contexts'
                                           else s3(session, browser, base, raw_doc))
                                run['transport'] = getattr(session, '_pl1', None)
                            except Exception:  # noqa: BLE001 -- recorded
                                run['fatal'] = traceback.format_exc()
                            finally:
                                if session is not None:
                                    run['cleanup'] = common.close_browser(session)
                            report['runs'].append(run)
                            bullets = [r for r in run.get('raw') or [] if (r.get('barrier') or {}).get('command') == '.uno:DefaultBullet']
                            print(browser, recipe, n, 'fatal' if run.get('fatal') else 'ok',
                                  [(r['type'], r['barrier'].get('failureShape'), (r['barrier'].get('readback') or {}).get('listTag'))
                                   for r in bullets], file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    (args.out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
