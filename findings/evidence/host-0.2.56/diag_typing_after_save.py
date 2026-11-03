#!/usr/bin/env python3
"""Diagnostic 3: diag-taken-03 showed Firefox losing the last two keys of ' H8SAVEAS ' typed right after 儲存 (read back 'H8SAVEA1'),
in the copy AND in the original saved later; Chrome kept it, but its harness inserts the string in one Input.insertText, not per key.
Is it the save before, or the burst of keys?  Each arm on its own l1-plain.docx, then 儲存 after a 3 s settle, the file read back:
  P  click, type ' H8SAVEAS '                                   (no save before)
  Q  click, type ' X1Q ', 儲存, type ' H8SAVEAS '                (H8's order)
  R  Q with 3 s between 儲存 and typing
  T  click, type ' X1Q ', type ' H8SAVEAS '                     (two bursts, no save between)
Firefox types through WebDriver element send keys (per key, as H8 does).  Run with host-stack/bin first on PATH.
  python3 -I diag_typing_after_save.py --out DIR [--browsers firefox] [--reps 2]
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
FOLDER = 'LiteCore-diag-typing'
ARMS = {'P': ['type:H8SAVEAS'], 'Q': ['type:X1Q', 'save', 'type:H8SAVEAS'], 'R': ['type:X1Q', 'save', 'wait:3', 'type:H8SAVEAS'],
        'T': ['type:X1Q', 'type:H8SAVEAS']}


def arm(session, kind, instance, dav, label, steps):
    name = f'{label}.docx'
    dav.dav('PUT', f'{FOLDER}/{name}', b8.FIXTURES['docx'].read_bytes(), {'Content-Type': b8.DOCX})
    entry = b8.open_row(session, instance, name, 'e2-editor.html', folder=FOLDER)
    state = b8.writer_ready(session, name)
    out = {'label': label, 'ready': bool(entry.get('landed')) and isinstance(state, dict) and state.get('state') == 'ready', 'steps': []}
    if not out['ready']:
        return out
    x, y = s.evaluate(session, h.PAPER)
    h.real.click(session, kind, x, y)
    time.sleep(.6)
    for step in steps:
        what, _, arg = step.partition(':')
        started = time.monotonic()
        if what == 'type':
            b8.type_text(session, kind, f' {arg} ')
        elif what == 'save':
            out.setdefault('saves', []).append(h.save(session, kind))
        elif what == 'wait':
            time.sleep(float(arg))
        out['steps'].append([step, round(time.monotonic() - started, 2)])
    time.sleep(3)
    out['finalSave'] = h.save(session, kind)
    text = b8.text_of(dav.get(name))
    at = text.find('R ')
    out.update({'H8SAVEAS': 'H8SAVEAS' in text, 'X1Q': 'X1Q' in text, 'textStart': text[:60]})
    h.leave(session, instance)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='firefox')
    parser.add_argument('--reps', type=int, default=2)
    args = parser.parse_args()
    h.OUT = args.out.resolve()
    h.OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(h.HOST)
    dav = b8.Dav(instance)
    b8.FOLDER = h.FOLDER = h.layout.FOLDER = FOLDER
    dav.dav('DELETE', FOLDER)
    dav.dav('MKCOL', FOLDER)
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
                        for key, steps in ARMS.items():
                            try:
                                run['arms'].append({'arm': key, 'rep': rep, **arm(session, kind, instance, dav, f'{key.lower()}{rep}-{kind}', steps)})
                            except Exception:  # noqa: BLE001
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
            print(run['browser'], a['arm'], a['rep'], {k: a.get(k) for k in ('H8SAVEAS', 'X1Q', 'textStart', 'steps', 'error')})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
