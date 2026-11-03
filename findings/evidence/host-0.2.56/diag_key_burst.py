#!/usr/bin/env python3
"""Diagnostic 4: diag-typing-01 lost the last two of ' H8SAVEAS ' (10 keys, WebDriver element send keys) on Firefox 8 of 8, with no
save anywhere near it; ' H8DOCX ' (8 keys) and ' X1Q ' (5) were whole.  A cap on a burst, or the characters?  Real key presses through
v21_input (Chrome: CDP dispatchKeyEvent per key; Firefox: one WebDriver action chain), each arm on its own l1-plain.docx, 3 s settle,
儲存, the file read back:
  K8   ' abcdef '          8 keys back to back
  K10  ' h8saveas '        10 keys back to back
  K14  ' abcdefghijkl '    14 keys back to back
  H10  ' h8saveas '        10 keys, 150 ms apart (typing speed)
  W10  ' h8saveas '        WebDriver element send keys / Input.insertText, as H8's type_text (lowercase)
Run with host-stack/bin first on PATH.  python3 -I diag_key_burst.py --out DIR [--browsers chrome,firefox] [--reps 2]
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
FOLDER = 'LiteCore-diag-burst'
ARMS = {'K8': (' abcdef ', 'chain'), 'K10': (' h8saveas ', 'chain'), 'K14': (' abcdefghijkl ', 'chain'),
        'H10': (' h8saveas ', 'paced'), 'W10': (' h8saveas ', 'type_text')}


def arm(session, kind, instance, dav, label, text, how):
    name = f'{label}.docx'
    dav.dav('PUT', f'{FOLDER}/{name}', b8.FIXTURES['docx'].read_bytes(), {'Content-Type': b8.DOCX})
    entry = b8.open_row(session, instance, name, 'e2-editor.html', folder=FOLDER)
    state = b8.writer_ready(session, name)
    out = {'label': label, 'typed': text, 'how': how, 'ready': bool(entry.get('landed')) and isinstance(state, dict) and state.get('state') == 'ready'}
    if not out['ready']:
        return out
    x, y = s.evaluate(session, h.PAPER)
    h.real.click(session, kind, x, y)
    time.sleep(.6)
    started = time.monotonic()
    if how == 'chain':
        h.real.chain(session, kind, [(c, ()) for c in text])
    elif how == 'paced':
        for c in text:
            h.real.key(session, kind, c)
            time.sleep(.15)
    else:
        b8.type_text(session, kind, text)
    out['typingSeconds'] = round(time.monotonic() - started, 2)
    time.sleep(3)
    out['saved'] = h.save(session, kind)
    got = b8.text_of(dav.get(name))
    word = text.strip()
    out.update({'whole': word in got, 'textStart': got[:40]})
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
                        for key, (text, how) in ARMS.items():
                            try:
                                run['arms'].append({'arm': key, 'rep': rep, **arm(session, kind, instance, dav, f'{key.lower()}-{rep}-{kind}', text, how)})
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
            print(run['browser'], a['arm'], a['rep'], {k: a.get(k) for k in ('whole', 'textStart', 'typingSeconds', 'error')})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
