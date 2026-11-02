#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 S1 on the installed host, where the owner met it, and the answer to the owner's second question.

Writer: Shift+Up/Down/Home/End with real keys, on both browsers: no red toast.  In Chrome an observer on the Worker also reads the
selection the engine reported.  The toolbar's `selectionShape` is no witness: only the pointer paths write it (run 01 read `collapsed`
on every press, kept in host-shift-01).  Firefox has no way in before the page loads, and its selection is S1's on the mirror.
Calc (Chrome): a committed cell, the status line, and the save that follows with nobody pressing anything.
Run with host-stack/bin first on PATH.   python3 -I host_shift.py --out DIR
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('host_batch', ROOT / 'findings/evidence/host-0.2.46/host_batch.py')
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)
s, real, HOST = batch.s, batch.real, batch.HOST
FOLDER = 'LiteCore-shift'
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
from check_writer_shift_lines import WATCH as _WATCH  # noqa: E402
WATCH = _WATCH.replace('<script>', '').replace('</script>', '').replace("addEventListener('DOMContentLoaded', () => { const t = document.querySelector('#toast');\n    new MutationObserver(() => { if (t.textContent && t.classList.contains('bad')) rec.toasts.push(t.textContent); })\n      .observe(t, {childList: true, characterData: true, subtree: true, attributes: true}); });\n", '')
READ = """(() => { const t = document.querySelector('#toast'), r = window.__s?.selection?.rectangles ?? null;
  return {rectangles: r ? r.length : null, area: r ? r.reduce((a, b) => a + (b.width || 0) * (b.height || 0), 0) : null,
          action: window.__s?.actions?.at(-1) ?? null, toast: t?.textContent ?? '', bad: t?.classList.contains('bad') === true}; })()"""
PAPER = """(() => { const r = document.querySelector('#paper').getBoundingClientRect(), d = document.querySelector('#desk').getBoundingClientRect();
  return [r.x + r.width * 0.3, Math.max(r.y, d.y) + 130]; })()"""


def writer(session, kind, instance, run):
    batch.FOLDER = FOLDER
    if kind == 'chrome':
        session.call('Page.addScriptToEvaluateOnNewDocument', {'source': WATCH})
    batch.go(session, instance, 'shift.odt', 'e2-editor.html')
    s.wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()", 180)
    time.sleep(2)
    x, y = s.evaluate(session, PAPER)
    for key in ('ArrowDown', 'ArrowUp', 'End', 'Home'):
        real.click(session, kind, x, y)
        time.sleep(.8)
        real.key(session, kind, key, ('shift',))
        time.sleep(1.2)
        state = s.evaluate(session, READ)
        batch.check(run, f'S1-host/{key}/no-refusal', not (state['bad'] and 'INVALID_ARGUMENT' in state['toast']), state)
        if kind == 'chrome':
            batch.check(run, f'S1-host/{key}/engine-selected', (state['area'] or 0) > 0 and state['action']['ok'] is True
                        and state['action']['extend'] is True, state)
    (OUT / f'{kind}-writer.png').write_bytes(session.screenshot())
    batch.leave(session, instance)


def calc(session, instance, run):
    batch.go(session, instance, 'autosave.ods', 'ods-editor.html')
    s.wait_until(session, '(() => window.__calcEditor?.state?.state === "ready" && Boolean(window.__calcEditor.state.cell))()', 180)
    status = lambda: s.evaluate(session, "document.querySelector('#autosave-status').textContent")
    run['autosaveAtOpen'] = status()
    real.click(session, 'chrome', *s.evaluate(session, "(()=>{const r=document.querySelector('#viewport').getBoundingClientRect();return [r.x+40,r.y+12];})()"))
    time.sleep(.6)
    session.call('Input.insertText', {'text': 'autosave-mark'})
    time.sleep(.3)
    real.key(session, 'chrome', 'Enter')
    started = time.monotonic()
    s.wait_until(session, '(() => window.__calcEditor.lastSave !== null)()', 60)
    saved = s.evaluate(session, '(() => ({trigger: window.__calcEditor.lastSave.trigger, revision: window.__calcEditor.lastSave.revision, status: document.querySelector("#autosave-status").textContent}))()')
    batch.check(run, 'autosave/fires-by-itself', saved['trigger'] != 'manual' and saved['trigger'] is not None,
                {**saved, 'secondsAfterCommit': round(time.monotonic() - started, 1), 'statusAtOpen': run['autosaveAtOpen']})
    batch.leave(session, instance)


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    OUT = args.out.resolve()
    OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(HOST)
    try:
        instance.dav('DELETE', FOLDER)  # this tool's own folder, left by a run that died
    except Exception:  # noqa: BLE001 -- absent, the usual case
        pass
    instance.dav('MKCOL', FOLDER)
    report = {'runs': []}
    with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
        instance.dav('PUT', f'{FOLDER}/shift.odt', batch.DOCUMENT.read_bytes(), {'Content-Type': 'application/vnd.oasis.opendocument.text'})
        ods = ROOT / 'findings/evidence/host-0.2.50/files-workflow-01/fixture/cell-editing.ods'
        instance.dav('PUT', f'{FOLDER}/autosave.ods', ods.read_bytes(), {'Content-Type': 'application/vnd.oasis.opendocument.spreadsheet'})
        for kind in ('chrome', 'firefox'):
            run = {'browser': kind, 'checks': []}
            report['runs'].append(run)
            session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch)))
            run['version'] = session.version
            try:
                s.browser_login(session, instance.base, instance.password)
                writer(session, kind, instance, run)
                if kind == 'chrome':
                    calc(session, instance, run)
            except Exception as error:  # noqa: BLE001 -- recorded
                run['fatal'] = repr(error)
                (OUT / f'{kind}-fatal.png').write_bytes(session.screenshot())
            finally:
                session.close()
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'HOST_SHIFT_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'HOST_SHIFT_RED'
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(c['id'], c['pass']) for c in checks], [r.get('fatal') for r in report['runs']])
    return 0 if report['verdict'] == 'HOST_SHIFT_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
