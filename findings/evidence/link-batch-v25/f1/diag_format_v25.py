#!/usr/bin/env python3
"""F1 (SPEC-M3-link-batch-v25 6.3): diag_format.py's two scenarios on v22, v24 and v25, with the engine's own record.

Derived from `findings/evidence/host-0.2.39/k-nine-cells/diag-format/diag_format.py`, which is imported by path
and NOT edited (its run-01/02 stay as produced).  The scenarios (`bullet`, `fmt`), the page observer, the page
read and the saved-ODT reading are that file's, unchanged.  The differences are a closed list:

1. Products.  diag_format.py's `v24` is "dist/ as served", which since the v25 cutover (e06d10a1b) is v25.  Here:
   v22  the 0.2.27 package, decoded and MANIFEST-checked (as diag_format.py)
   v24  its own bytes: page b15a6d8e from git, the v24 archive's profile, shell generation 77
   v25  dist/ as served: page 6e66c930, the v25 archive's profile, shell generation 78
   (v24/v25 via wasm_sdk_probe/tools/v25_f_products.py; a product whose identity check fails is not run.)
2. The engine's record, not only the worker's projection (Chrome; the scenarios are Chrome-only already).  The
   v25 worker projects `dispatched` from the engine's field when it is a boolean, else from `stage` -- and v25
   also moves `stage`, so a page-level `dispatched:true` cannot tell the serialised field from the fallback
   (spec v25 13 item 4 says F1 measures the serialisation).  After `ready`, `Target.setAutoAttach` reaches the
   page's worker and wraps its `JSON.parse` (an observer: same value returned, no served byte changed) to keep,
   for every engine `error` / `editor-action-completed` event, whether `formatBarrier.dispatched` and `witness`
   are PRESENT and their values, and `stage`.  If the worker cannot be reached that is recorded, not inferred.
3. The traffic rows add the reply's `completion`, `changed` and `witness`.

--out must not exist.  Nothing under dist/ is written.  Verdict: read_f1.py, from report.json only.
"""
import argparse
import gzip
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
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v25_f_products as products  # noqa: E402
from r7_support import evaluate  # noqa: E402

SOURCE = ROOT / 'findings/evidence/host-0.2.39/k-nine-cells/diag-format/diag_format.py'
_spec = importlib.util.spec_from_file_location('diag_format', SOURCE)
diag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diag)

RAW_INSTALL = """(() => {
  if (self.__rawEngine) return 'already';
  const rec = self.__rawEngine = [];
  const parse = JSON.parse;
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  JSON.parse = function (text, reviver) {
    const v = parse.call(JSON, text, reviver);
    try {
      if (v && typeof v === 'object' && (v.type === 'error' || v.type === 'editor-action-completed')) {
        const b = v.formatBarrier;
        rec.push({type: v.type, requestId: v.requestId ?? null, code: v.code ?? null,
          hasWitness: has(v, 'witness'), witness: v.witness ?? null, completion: v.completion ?? null,
          changed: v.changed ?? null,
          barrier: b && typeof b === 'object' ? {hasDispatched: has(b, 'dispatched'), dispatched: b.dispatched ?? null,
            stage: b.stage ?? null, failureShape: b.failureShape ?? null, route: b.route ?? null} : null});
      }
    } catch (e) {}
    return v;
  };
  return 'installed';
})()"""


def attach_worker(session, settle=4.0):
    """The page's document worker's CDP session id, by setAutoAttach (pp.induce_worker_failure's route, read
    by hand for the same reason: the attach events arrive before the answer and `call` would drop them)."""
    websocket = getattr(session, 'websocket', None)
    if websocket is None:
        return None, 'no raw websocket'
    session.next_id += 1
    message_id = session.next_id
    websocket.send(json.dumps({'id': message_id, 'method': 'Target.setAutoAttach',
                               'params': {'autoAttach': True, 'flatten': True, 'waitForDebuggerOnStart': False}}))
    attached, answered, deadline = [], False, time.monotonic() + settle
    while time.monotonic() < deadline:
        try:
            message = json.loads(websocket.recv(timeout=0.5))
        except Exception:  # noqa: BLE001 -- a quiet socket is not an error
            continue
        if message.get('method') == 'Target.attachedToTarget':
            attached.append(message['params'])
        elif message.get('id') == message_id:
            answered = True
            if 'error' in message:
                return None, f"setAutoAttach: {message['error']}"
    workers = [a for a in attached if a['targetInfo'].get('type') == 'worker'
               and a['targetInfo'].get('url', '').endswith('sdk-worker.js')]
    if not workers:
        return None, f'no document worker attached (answered={answered}, types=' \
                     f"{sorted({a['targetInfo'].get('type') for a in attached})})"
    return workers[-1]['sessionId'], None


def worker_eval(session, expression):
    reply = session.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True},
                         session_id=session._raw_sid)
    return (reply.get('result') or {}).get('value')


_ready = diag.ready


def ready(session, base):
    state = _ready(session, base)
    sid, why = attach_worker(session)
    session._raw_sid = sid
    session._raw_install = worker_eval(session, RAW_INSTALL) if sid else why
    return state


_traffic = diag.traffic


def traffic(session):
    out = _traffic(session)
    record = evaluate(session, 'window.__diag')
    replies = {r['message'].get('requestId'): r['message'] for r in record['responses']}
    wanted = [q['message'].get('requestId') for q in record['requests']
              if q['message'].get('operation') in ('editorActionV2', 'insertText')]
    for row, request_id in zip(out, wanted):
        result = (replies.get(request_id) or {}).get('result') or {}
        row.update({'requestId': request_id, 'completion': result.get('completion'),
                    'changed': result.get('changed'), 'witness': result.get('witness')})
    session._raw = (worker_eval(session, 'self.__rawEngine ?? null') if getattr(session, '_raw_sid', None)
                    else None)
    return out


diag.ready = ready
diag.traffic = traffic


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=1)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((diag.V22_PACKAGE / 'MANIFEST.json').read_bytes())
    v22 = {}
    for relative, record in manifest['files'].items():
        data = gzip.decompress((diag.V22_PACKAGE / 'files' / (relative + '.gz')).read_bytes())
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise SystemExit('v22 package member differs from its MANIFEST: ' + relative)
        v22[relative] = data
    v22['e2-editor.html'] = common.inject(v22['e2-editor.html'].decode('utf-8'), [diag.OBSERVER]).encode()
    report = {'argv': sys.argv, 'derivedFrom': {'path': str(SOURCE.relative_to(ROOT)),
                                                'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()},
              'products': {'v22': {'page': hashlib.sha256(v22['e2-editor-app.js']).hexdigest(),
                                   'package': str(diag.V22_PACKAGE.relative_to(ROOT))}}, 'runs': []}
    plan = {'v22': v22, 'v24': None, 'v25': None}
    scratch = Path(tempfile.mkdtemp(prefix='f1-diag-format-', dir=ROOT / 'wasm_sdk_probe/build'))
    try:
        with common.browser_lock('diag_format_v25'):
            report['preRun'] = common.pre_run_checks()
            if report['preRun']['refuse']:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for name, given in plan.items():
                target = scratch / name
                if given is not None:
                    pp.build_mirror(common.DIST, target, given)
                else:
                    pp.build_mirror(common.DIST, target, products.overrides(name, [diag.OBSERVER]))
                    report['products'][name] = products.identity(name, target)
                    if not report['products'][name]['ok']:
                        print(name, 'identity FAILED, not run', file=sys.stderr, flush=True)
                        continue
                with common.served(target) as base:
                    for n in range(1, args.repetitions + 1):
                        for scenario in ('bullet', 'format'):
                            run, session = {'product': name, 'scenario': scenario, 'repetition': n}, None
                            try:
                                session = common.open_browser('chrome')
                                if scenario == 'bullet':
                                    run.update(diag.bullet(session, base))
                                else:
                                    value, raw = diag.fmt(session, base)
                                    run.update(value)
                                    if raw:
                                        (args.out / f'{name}-format-{n}.odt').write_bytes(raw)
                                run['rawInstall'] = getattr(session, '_raw_install', None)
                                run['raw'] = getattr(session, '_raw', None)
                            except Exception:  # noqa: BLE001 -- recorded
                                run['fatal'] = traceback.format_exc()
                            finally:
                                if session is not None:
                                    run['cleanup'] = common.close_browser(session)
                            report['runs'].append(run)
                            print(name, scenario, n, 'fatal' if run.get('fatal') else 'ok', run.get('rawInstall'),
                                  file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    (args.out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
