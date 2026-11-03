#!/usr/bin/env python3
"""Diagnostic for H8 run 02's one red cell (H8/save-as-odf-writer on Firefox: the copy held H8DOCX but not H8SAVEAS, the text typed
right after 儲存 and right before 另存新檔).  Is the text lost on the way in (focus), or left out of the copy (timing)?

Per browser, each arm twice, each on its own copy of l1-plain.docx in LiteCore-diag-saveas, on the installed host:
  A  H8's path: click the paper, type X1Q, 儲存, type X2Q, 另存新檔 at once            -> the copy: X1Q? X2Q?
  B  the same, 3 s between typing X2Q and 另存新檔                                      -> timing
  C  the same, but 儲存 instead of 另存新檔                                              -> did X2Q reach the document at all
  D  click the paper again before X2Q, then 另存新檔 at once                             -> focus
Records the focused element after 儲存 and after typing.  Run with host-stack/bin first on PATH.
  python3 -I diag_saveas_text.py --out DIR [--browsers chrome,firefox] [--reps 2]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('host_batch8', HERE / 'host_batch8.py')
b8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b8)
h, s = b8.h, b8.s
FOLDER = 'LiteCore-diag-saveas'
FOCUS = "(() => { const a = document.activeElement; return a ? `${a.tagName}#${a.id}.${a.className}` : null; })()"
ARMS = {'A': dict(wait=0, click=False, regular=False), 'B': dict(wait=3, click=False, regular=False),
        'C': dict(wait=0, click=False, regular=True), 'D': dict(wait=0, click=True, regular=False)}


def arm(session, kind, instance, dav, label, wait, click, regular):
    name = f'{label}.docx'
    dav.dav('PUT', f'{FOLDER}/{name}', b8.FIXTURES['docx'].read_bytes(), {'Content-Type': b8.DOCX})
    entry = b8.open_row(session, instance, name, 'e2-editor.html', folder=FOLDER)
    state = b8.writer_ready(session, name)
    out = {'label': label, 'landed': bool(entry.get('landed')), 'ready': isinstance(state, dict) and state.get('state') == 'ready'}
    if not out['ready']:
        return out
    x, y = s.evaluate(session, h.PAPER)
    h.real.click(session, kind, x, y)
    time.sleep(.6)
    b8.type_text(session, kind, ' X1Q ')
    out['saved'] = h.save(session, kind)
    out['focusAfterSave'] = s.evaluate(session, FOCUS)
    if click:
        h.real.click(session, kind, x, y)
        time.sleep(.6)
    b8.type_text(session, kind, ' X2Q ')
    out['focusAfterTyping'] = s.evaluate(session, FOCUS)
    time.sleep(wait)
    if regular:
        out['saved2'] = h.save(session, kind)
        data = dav.get(name)
    else:
        old_id = s.evaluate(session, b8.FILE_ID)
        b8.save_as(session, kind, None, dav, typed_name=f'{label}-copy')
        moved = s.wait_until(session, f"(() => new URL(location.href).searchParams.get('fileId') !== {json.dumps(old_id)} && location.href)()", 60)
        out['moved'] = isinstance(moved, str)
        data = dav.get(f'{label}-copy.odt')
    text = b8.text_of(data)
    out.update({'kind': b8.kind_of(data), 'X1Q': 'X1Q' in text, 'X2Q': 'X2Q' in text})
    h.leave(session, instance)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    parser.add_argument('--reps', type=int, default=2)
    args = parser.parse_args()
    h.OUT = args.out.resolve()
    h.OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(h.HOST)
    dav = b8.Dav(instance)
    dav.dav('DELETE', FOLDER)
    dav.dav('MKCOL', FOLDER)
    h.FOLDER = FOLDER
    h.layout.FOLDER = FOLDER
    b8.FOLDER = FOLDER  # Dav.get / props / listing read the module's FOLDER; run 01 read LiteCore-batch8 and saw nothing
    report = {'runs': []}
    try:
        with tempfile.TemporaryDirectory(dir=b8.b6.SDK / 'build') as scratch:
            for kind in args.browsers.split(','):
                session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch) / kind))
                run = {'browser': kind, 'version': session.version, 'arms': []}
                report['runs'].append(run)
                try:
                    s.browser_login(session, instance.base, instance.password)
                    for rep in range(1, args.reps + 1):
                        for key, how in ARMS.items():
                            try:
                                run['arms'].append({'arm': key, 'rep': rep, **arm(session, kind, instance, dav, f'{key.lower()}{rep}-{kind}', **how)})
                            except Exception:  # noqa: BLE001 -- recorded, the next arm goes on
                                run['arms'].append({'arm': key, 'rep': rep, 'error': traceback.format_exc()[-600:]})
                                try:
                                    h.leave(session, instance)
                                except Exception:  # noqa: BLE001
                                    pass
                finally:
                    session.close()
    finally:
        report['folderDelete'] = dav.dav('DELETE', FOLDER)[0]
        (h.OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    for run in report['runs']:
        for a in run['arms']:
            print(run['browser'], a['arm'], a['rep'], {k: a.get(k) for k in ('X1Q', 'X2Q', 'moved', 'focusAfterSave', 'focusAfterTyping', 'error')})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
