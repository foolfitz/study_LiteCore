#!/usr/bin/env python3
"""Diagnostic 2 for H8/save-as-odf-writer on Firefox (red 4 of 4 through the real runner: h8-02, h8-ff-r1..r3; the copy holds H8DOCX,
not H8SAVEAS).  diag-saveas-02 (no taken name) kept both tokens 2 of 2 on Firefox, so this one follows H8's exact order: the default
name is taken, the first confirm is refused, then a new name.

Each arm on its own l1-plain.docx copy with {label}.odt already there (the taken name), in LiteCore-diag-taken:
  F  H8's order: click, type X1Q, 儲存, type X2Q, 另存新檔, confirm the taken default (refused), new name, confirm -> the copy: X2Q?
  E  the same up to the refusal, then 取消 and 儲存                                       -> the original: does the document still hold X2Q?
  G  F with 3 s between typing X2Q and 另存新檔                                              -> timing
  N  F with no refusal: a new name typed before the first confirm                         -> the control (diag-saveas-02's arm A)
Run with host-stack/bin first on PATH.  python3 -I diag_saveas_taken.py --out DIR [--browsers firefox,chrome] [--reps 2]
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
FOLDER = 'LiteCore-diag-taken'
FOCUS = "(() => { const a = document.activeElement; return a ? `${a.tagName}#${a.id}` : null; })()"
DIALOG_MESSAGE = "(() => { const d = document.querySelector('#save-as-dialog'); const m = document.querySelector('#save-as-message'); return d && d.open && m && !m.hidden && m.textContent; })()"
ARMS = {'F': dict(wait=0, refuse=True, cancel=False), 'E': dict(wait=0, refuse=True, cancel=True),
        'G': dict(wait=3, refuse=True, cancel=False), 'N': dict(wait=0, refuse=False, cancel=False)}


def arm(session, kind, instance, dav, label, wait, refuse, cancel, tokens=('X1Q', 'X2Q')):
    name, taken, new = f'{label}.docx', f'{label}.odt', f'{label}-copy'
    dav.dav('PUT', f'{FOLDER}/{name}', b8.FIXTURES['docx'].read_bytes(), {'Content-Type': b8.DOCX})
    dav.dav('PUT', f'{FOLDER}/{taken}', b8.FIXTURES['odt'].read_bytes(), {'Content-Type': b8.ODT})
    entry = b8.open_row(session, instance, name, 'e2-editor.html', folder=FOLDER)
    state = b8.writer_ready(session, name)
    out = {'label': label, 'ready': bool(entry.get('landed')) and isinstance(state, dict) and state.get('state') == 'ready', 'focus': {}}
    if not out['ready']:
        return out
    x, y = s.evaluate(session, h.PAPER)
    h.real.click(session, kind, x, y)
    time.sleep(.6)
    b8.type_text(session, kind, f' {tokens[0]} ')
    out['saved'] = h.save(session, kind)
    b8.type_text(session, kind, f' {tokens[1]} ')
    out['focus']['afterTyping'] = s.evaluate(session, FOCUS)
    time.sleep(wait)
    old_id = s.evaluate(session, b8.FILE_ID)
    if refuse:
        b8.save_as(session, kind, None, dav)  # the default name, which is taken
        # H8's own probe (diag-taken-01 used DIALOG_MESSAGE, which never matched: every arm waited the full 30 s, unlike H8)
        out['refusal'] = b8.got(s.wait_until(session, f"(() => {{ const d = {b8.DIALOG}; return d && d.message && d; }})()", 30))
        out['focus']['afterRefusal'] = s.evaluate(session, FOCUS)
        if cancel:
            h.press(session, kind, '#save-as-cancel', .6)
            out['focus']['afterCancel'] = s.evaluate(session, FOCUS)
            out['saved2'] = h.save(session, kind)
            data = dav.get(name)
            out['read'] = 'original'
        else:
            h.press(session, kind, '#save-as-name', .4)
            h.key(session, kind, 'a', ('ctrl',))
            out['focus']['beforeName'] = s.evaluate(session, FOCUS)
            b8.type_text(session, kind, new)
            out['nameField'] = s.evaluate(session, "(() => document.querySelector('#save-as-name')?.value ?? null)()")
            h.press(session, kind, '#save-as-confirm', 1.0)
    else:
        b8.save_as(session, kind, None, dav, typed_name=new)
    if not cancel:
        moved = s.wait_until(session, f"(() => new URL(location.href).searchParams.get('fileId') !== {json.dumps(old_id)} && location.href)()", 60)
        out['moved'] = isinstance(moved, str)
        data = dav.get(f'{new}.odt')
        out['read'] = 'copy'
    text = b8.text_of(data)
    at = text.find(tokens[0])
    out.update({'kind': b8.kind_of(data), 'X1Q': tokens[0] in text, 'X2Q': tokens[1] in text, 'tokens': list(tokens),
                'textNearFirst': text[max(0, at - 40):at + 80] if at >= 0 else text[:120]})
    h.leave(session, instance)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='firefox,chrome')
    parser.add_argument('--reps', type=int, default=2)
    parser.add_argument('--arms', default='F,E,G,N')
    parser.add_argument('--tokens', default='X1Q,X2Q')
    args = parser.parse_args()
    h.OUT = args.out.resolve()
    h.OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(h.HOST)
    dav = b8.Dav(instance)
    b8.FOLDER = h.FOLDER = h.layout.FOLDER = FOLDER  # Dav reads the module's FOLDER (diag-saveas-01's lesson)
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
                        for key, how in ((k, ARMS[k]) for k in args.arms.split(',')):
                            try:
                                run['arms'].append({'arm': key, 'rep': rep, **arm(session, kind, instance, dav, f'{key.lower()}{rep}-{kind}', **how, tokens=tuple(args.tokens.split(',')))})
                            except Exception:  # noqa: BLE001 -- recorded, the next arm goes on
                                run['arms'].append({'arm': key, 'rep': rep, 'error': traceback.format_exc()[-600:]})
                                try:
                                    (h.OUT / f'{kind}-{key}{rep}-error.png').write_bytes(session.screenshot())
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
            print(run['browser'], a['arm'], a['rep'], {k: a.get(k) for k in ('read', 'X1Q', 'X2Q', 'moved', 'textNearFirst', 'error')})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
