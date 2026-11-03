#!/usr/bin/env python3
"""SPEC-P-calc-undo on the installed host: Calc document undo on the owner's path -- open an .ods from Files, real keys and pointer, Save,
the file read back over WebDAV.  The mirror's CU tool cannot see the host's own routes, autosave or WebDAV round trip; this does.

Helpers from ../host-0.2.54/host_batch6.py (not edited), which takes its own from ../host-0.2.52/host_batch4.py.  Run on 0.2.54 first: there is no
undo button and Ctrl+Z sends nothing, and that is the tool's red.  Every redo cell counts only after an undo that took the value away (the mirror
CU tool's lesson, red-on-v3-02).  Run with host-stack/bin first on PATH.
  python3 -I host_batch7.py --out DIR [--browsers chrome,firefox]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b6 = load('host_batch6', HERE.parent / 'host-0.2.54/host_batch6.py')
h, s, cells, nu = b6.h, b6.s, b6.cells, None
import probe_calc_undo_native as nu  # noqa: E402  (b6 put wasm_sdk_probe/tools on sys.path)

FOLDER = 'LiteCore-batch7'
NAME = 'undo-{kind}.ods'
UNDO_SHOWN = "(() => { const b = document.querySelector('#undo-button'); return Boolean(b && !b.hidden && b.getBoundingClientRect().width > 0); })()"
IDLE = "(() => { const s = window.__calcEditor?.state; return Boolean(s && s.state === 'ready' && !s.busy && !s.editing); })()"
RED = "(() => { const t = document.querySelector('#toast'); return t?.classList.contains('error') ? t.textContent : null; })()"


def read(instance, kind):
    raw = instance.dav('GET', f'{FOLDER}/{NAME.format(kind=kind)}')[1]
    with tempfile.NamedTemporaryFile(suffix='.ods') as f:
        f.write(raw)
        f.flush()
        state = nu.sheet_state(Path(f.name))
    return state


def text(state, cell):
    return (state.get(cell) or {}).get('text')


def bold(state, cell):
    return '"bold"' in json.dumps((state.get(cell) or {}).get('style') or {})


def settle(session):
    time.sleep(.4)
    s.wait_until(session, IDLE, 30)


def scenario(session, kind, instance, run):
    h.layout.go(session, instance, NAME.format(kind=kind), 'ods-editor.html')
    ready = s.wait_until(session, b6.CALC_READY, 180)
    h.check(run, 'H7/opens-in-calc', ready is True, ready)
    shown = s.evaluate(session, UNDO_SHOWN)
    h.check(run, 'H7/undo-button-offered', shown, shown)
    base = read(instance, kind)

    b6.select(session, 'D9')
    b6.type_text(session, '#formula-input', 'H7VALUE')
    b6.box_key(session, 'Enter')
    settle(session)
    h.check(run, 'H7/save-written', b6.calc_save(session, kind))
    written = read(instance, kind)
    h.key(session, kind, 'z', ('ctrl',))
    settle(session)
    h.check(run, 'H7/save-undone', b6.calc_save(session, kind))
    undone = read(instance, kind)
    took = text(written, '3,8') == 'H7VALUE' and text(undone, '3,8') == text(base, '3,8')
    h.check(run, 'H7/ctrl-z-restores-the-file', took, {'written': text(written, '3,8'), 'undone': text(undone, '3,8')})
    h.key(session, kind, 'y', ('ctrl',))
    settle(session)
    h.check(run, 'H7/save-redone', b6.calc_save(session, kind))
    redone = read(instance, kind)
    h.check(run, 'H7/ctrl-y-redoes', took and text(redone, '3,8') == 'H7VALUE', text(redone, '3,8'))

    b6.select(session, 'A1')
    settle(session)
    h.key(session, kind, 'b', ('ctrl',))
    settle(session)
    h.check(run, 'H7/save-bold', b6.calc_save(session, kind))
    emboldened = read(instance, kind)
    if shown:
        h.press(session, kind, '#undo-button')
        settle(session)
    h.check(run, 'H7/save-button-undone', b6.calc_save(session, kind))
    unbolded = read(instance, kind)
    h.check(run, 'H7/button-undoes-bold', shown and bold(emboldened, '0,0') and not bold(unbolded, '0,0'),
            {'boldWritten': bold(emboldened, '0,0'), 'boldAfter': bold(unbolded, '0,0')})
    h.check(run, 'H7/no-red-toast', s.evaluate(session, RED) is None, s.evaluate(session, RED))
    h.check(run, 'H7/ready', s.evaluate(session, IDLE), s.evaluate(session, "window.__calcEditor?.state?.state"))
    (h.OUT / f'{kind}-after.png').write_bytes(session.screenshot())
    h.leave(session, instance)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    args = parser.parse_args()
    h.OUT = args.out.resolve()
    h.OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(h.HOST)
    try:
        instance.dav('DELETE', FOLDER)  # this tool's own folder, left by a run that died
    except Exception:  # noqa: BLE001 -- absent, the usual case
        pass
    instance.dav('MKCOL', FOLDER)
    h.FOLDER = FOLDER
    h.layout.FOLDER = FOLDER
    report = {'runs': []}
    with tempfile.TemporaryDirectory(dir=b6.SDK / 'build') as scratch:
        for kind in args.browsers.split(','):
            instance.dav('PUT', f'{FOLDER}/{NAME.format(kind=kind)}', b6.FIXTURE_ODS.read_bytes(), {'Content-Type': b6.ODS_MIME})
            run = {'browser': kind, 'checks': []}
            report['runs'].append(run)
            session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch)))
            run['version'] = session.version
            try:
                s.browser_login(session, instance.base, instance.password)
                scenario(session, kind, instance, run)
            except Exception:  # noqa: BLE001 -- recorded
                run['fatal'] = traceback.format_exc()
                try:
                    (h.OUT / f'{kind}-fatal.png').write_bytes(session.screenshot())
                except Exception:  # noqa: BLE001 -- a page held by a dialog cannot be shot either
                    pass
            finally:
                session.close()
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'H7_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'H7_RED'
    (h.OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(c['id'], c['pass']) for c in checks], [(r.get('fatal') or '')[-300:] for r in report['runs']])
    return 0 if report['verdict'] == 'H7_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
