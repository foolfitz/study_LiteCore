#!/usr/bin/env python3
"""SPEC-P-ms-formats 6.3 on the installed host: Word and Excel files from Files, on the owner's path -- the row's name (Files' default
action), real pointer and keys, 儲存 and 另存新檔 through the pages' own buttons and dialog, every file read back over WebDAV.

Per browser, in the tool's own folder (LiteCore-batch8): d-<b>.docx (l1-plain.docx), c-<b>.xlsx (formats.xlsx), o-<b>.odt and s-<b>.ods
(the ODF controls), and d-<b>.odt -- the name a Save As of d-<b>.docx offers by default, so the first confirm meets a taken name
(it was w-<b>.odt until 2026-11-04: not the default name, so the first confirm saved as d-<b>.odt; run h8/ is that witness).
  H8/action-*           the row's name opens the file in the right editor and it reaches ready: .docx and .odt in Writer, .xlsx and .ods in Calc
  H8/save-docx          typed text, 儲存: the file read back is OOXML holding the text; its name and type unchanged; nothing new in the folder
  H8/save-as-taken      另存新檔 with the default name, which is taken: the dialog stays and says so; that file and the original unchanged
  H8/save-as-odf-writer the name changed, ODF (preselected): the new file is ODF holding the edits; the original is its last save; the page
                        now has the new file (the address's fileId is the new file's, the title its name); a save after that writes the new file
  H8/save-xlsx, H8/autosave-xlsx, H8/save-as-odf-calc   the same for Calc, with an autosave in between
  H8/read-only          a second user given read-only shares of the DOCX and the XLSX: view-only, no lock, no Save As
Red on 0.2.55 first: Files has no LiteCore action for .docx / .xlsx (H8/action-docx and -xlsx red, and every cell that needs them).
Helpers from ../host-0.2.54/host_batch6.py (not edited).  Run with host-stack/bin first on PATH.
  python3 -I host_batch8.py --out DIR [--browsers chrome,firefox]
"""
import argparse
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import secrets
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b6 = load('host_batch6', HERE.parent / 'host-0.2.54/host_batch6.py')
h, s = b6.h, b6.s
from run_browser_probe import ChromeSession  # noqa: E402  (b6 put wasm_sdk_probe/tools on sys.path)

ROOT = HERE.parents[2]
FOLDER = 'LiteCore-batch8'
DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
ODT = 'application/vnd.oasis.opendocument.text'
ODS = 'application/vnd.oasis.opendocument.spreadsheet'
FIXTURES = {'docx': ROOT / 'wasm_sdk_probe/test-docs/r7-compat/l1-plain.docx', 'odt': ROOT / 'wasm_sdk_probe/test-docs/r7-compat/l1-plain.odt',
            'xlsx': ROOT / 'libreoffice-26-8/sc/qa/unit/data/xlsx/formats.xlsx', 'ods': b6.FIXTURE_ODS}
MIMES = {'docx': DOCX, 'odt': ODT, 'xlsx': XLSX, 'ods': ODS}
HOST_DONE = "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()"
WRITER = "(() => ({state: document.querySelector('#state-pill')?.dataset.state ?? null, doc: document.querySelector('#s-doc')?.textContent ?? null}))()"
SHOWN = "(() => { const b = document.querySelector(ARG); if (!b) return null; const r = b.getBoundingClientRect(); return {hidden: b.hidden, disabled: b.disabled, width: r.width}; })()"
DIALOG = ("(() => { const d = document.querySelector('#save-as-dialog'); return d ? {open: d.open, name: document.querySelector('#save-as-name').value,"
          " message: document.querySelector('#save-as-message').hidden ? null : document.querySelector('#save-as-message').textContent,"
          " choices: [...document.querySelectorAll('#save-as-formats input')].map(x => ({value: x.value, checked: x.checked}))} : null; })()")
TITLE = "(() => document.querySelector('#litecore-host-title')?.textContent ?? null)()"
FILE_ID = "(() => new URL(location.href).searchParams.get('fileId'))()"
SAVES_AUTO = ("(() => { const v = document.documentElement.getAttribute('data-litecore'); return v ? (JSON.parse(v).saves || [])"
              ".filter(x => x.settled && x.trigger === 'auto' && x.outcome === 'saved').length : -1; })()")


class Dav:
    """Admin WebDAV and OCS that answer with the status instead of raising."""

    def __init__(self, instance):
        self.instance = instance

    def request(self, method, path, body=None, headers=None, user='admin', password=None):
        request = urllib.request.Request(self.instance.base + path, data=body, method=method, headers=headers or {})
        token = f"{user}:{password or self.instance.password}".encode()
        request.add_header('Authorization', 'Basic ' + base64.b64encode(token).decode())
        try:
            with urllib.request.urlopen(request, context=self.instance.tls, timeout=90) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def dav(self, method, name, body=None, headers=None):
        return self.request(method, '/remote.php/dav/files/admin/' + urllib.parse.quote(name), body, headers)

    def ocs(self, method, path, data=None):
        code, body, _ = self.request(method, '/ocs/v2.php/' + path + '?format=json',
                                     urllib.parse.urlencode(data).encode() if data is not None else None,
                                     {'OCS-APIRequest': 'true', 'Content-Type': 'application/x-www-form-urlencoded'})
        parsed = json.loads(body)
        if code >= 300 or parsed['ocs']['meta']['status'] != 'ok':
            raise RuntimeError(f'OCS {method} {path}: {code} {parsed["ocs"]["meta"]}')
        return parsed['ocs']['data']

    def get(self, name):
        code, body, _ = self.dav('GET', f'{FOLDER}/{name}')
        return body if code == 200 else None

    def props(self, name):
        body = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns" xmlns:nc="http://nextcloud.org/ns">'
                b'<d:prop><oc:fileid/><d:getcontenttype/><nc:lock/></d:prop></d:propfind>')
        code, answer, _ = self.dav('PROPFIND', f'{FOLDER}/{name}', body, {'Depth': '0', 'Content-Type': 'application/xml'})
        text = answer.decode('utf-8', 'replace')
        grab = lambda tag: (re.search(f'<{tag}>([^<]*)</{tag}>', text) or [None, None])[1]
        return {'status': code, 'fileId': grab('oc:fileid'), 'type': grab('d:getcontenttype'), 'lock': grab('nc:lock')}

    def listing(self):
        code, answer, _ = self.dav('PROPFIND', FOLDER + '/', b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:displayname/></d:prop></d:propfind>',
                                   {'Depth': '1', 'Content-Type': 'application/xml'})
        names = [urllib.parse.unquote(m) for m in re.findall(r'<d:href>[^<]*/' + re.escape(FOLDER) + r'/([^<]+)</d:href>', answer.decode())]
        return sorted(n for n in names if n)


def got(value):
    """What a wait returned when its condition held; None on a timeout (s.wait_until returns a truthy dict then, memory 2026-11-03)."""
    return value if isinstance(value, dict) and not value.get('timedOut') else None


def sha(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def kind_of(data):
    """ooxml, odf or neither, from the zip's own members."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, TypeError):
        return None
    names = z.namelist()
    if names and names[0] == 'mimetype':
        return 'odf:' + z.read('mimetype').decode('ascii', 'replace')
    return 'ooxml' if '[Content_Types].xml' in names else None


def text_of(data):
    """Every text run of the document, tags stripped (a typed word stays whole across Writer's runs)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, TypeError):
        return ''
    parts = [n for n in z.namelist() if n in ('content.xml', 'word/document.xml', 'xl/sharedStrings.xml') or n.startswith('xl/worksheets/')]
    return ''.join(re.sub(r'<[^>]+>', '', z.read(n).decode('utf-8', 'replace')) for n in parts)


def type_text(session, kind, text):
    if isinstance(session, ChromeSession):
        session.call('Input.insertText', {'text': text})
    else:
        # One key at a time, 150 ms apart (2026-11-04).  One send-keys call delivers the whole string in ~20 ms, faster than the engine
        # takes keys, and the input queue holds 8 (finding 130): ' H8SAVEAS ' came back 'H8SAVEA' 4 of 4 (h8-02, h8-ff-r1..r3).  At 150 ms
        # a key both browsers keep all ten (diag-burst-01, H10).  This cell measures Save As, not a burst; 130 is the burst's finding.
        element = session.command('GET', '/element/active')['element-6066-11e4-a52e-4f735466cecf']
        for character in text:
            session.command('POST', f'/element/{element}/value', {'text': character})
            time.sleep(.15)
    time.sleep(.8)


def open_row(session, instance, name, page, folder=FOLDER):
    """Files' default action: the row's name, clicked; True when the page it lands on is `page`."""
    s.navigate(session, instance.base + '/index.php/apps/files/files?dir=' + urllib.parse.quote('/' + folder if folder else '/'), timeout=120)
    selector = f'[data-cy-files-list-row-name={json.dumps(name)}] [data-cy-files-list-row-name-link]'
    if s.wait_until(session, f'(() => document.querySelector({json.dumps(selector)}) !== null)()', 60) is not True:
        return {'row': False}
    session.click(selector)
    landed = s.wait_until(session, f'(() => location.pathname.endsWith({json.dumps("/" + page)}) && location.href)()', 30)
    return {'row': True, 'landed': landed if isinstance(landed, str) else None}


def writer_ready(session, name, timeout=180):
    s.wait_until(session, HOST_DONE, timeout)
    state = s.wait_until(session, f"(() => {{ const w = {WRITER}; return w.state === 'ready' && w.doc === {json.dumps(name)} && w; }})()", 60)
    time.sleep(1.5)
    return got(state) or {'notReady': s.evaluate(session, WRITER)}


def calc_ready(session, name, timeout=180):
    state = s.wait_until(session, f"(() => {{ const c = window.__calcEditor?.state; return c && c.state === 'ready' && c.fileName === {json.dumps(name)}"
                                f" && Boolean(c.cell) && !c.busy && {{state: c.state, fileName: c.fileName, readOnly: c.readOnly}}; }})()", timeout)
    time.sleep(1.5)
    return got(state) or {'notReady': s.evaluate(session, "(() => { const c = window.__calcEditor?.state; return c ? {state: c.state, fileName: c.fileName} : null; })()")}


def actions(session, kind, instance, run):
    for fixture, page, ready in (('o', 'e2-editor.html', writer_ready), ('s', 'ods-editor.html', calc_ready)):
        name = f'{fixture}-{kind}.{"odt" if fixture == "o" else "ods"}'
        entry = open_row(session, instance, name, page)
        state = ready(session, name) if entry.get('landed') else None
        h.check(run, f'H8/action-{name.rsplit(".", 1)[1]}', bool(entry.get('landed')) and isinstance(state, dict) and state.get('state') == 'ready',
                {'entry': entry, 'state': state})
        h.leave(session, instance)


def save_as(session, kind, run, dav, typed_name=None):
    """Press 另存新檔, optionally type a name over the preselected one, press 儲存 in the dialog."""
    h.press(session, kind, '#save-as' if s.evaluate(session, "(() => Boolean(document.querySelector('#save-as')))()") else '#save-as-button', .8)
    dialog = s.wait_until(session, f"(() => {{ const d = {DIALOG}; return d && d.open && d; }})()", 10)
    if typed_name is not None:
        type_text(session, kind, typed_name)
    h.press(session, kind, '#save-as-confirm', 1.0)
    return got(dialog)


def writer_flow(session, kind, instance, run, dav):
    name, taken, new = f'd-{kind}.docx', f'd-{kind}.odt', f'w-{kind}-odf.odt'
    before = dav.listing()
    entry = open_row(session, instance, name, 'e2-editor.html')
    state = writer_ready(session, name) if entry.get('landed') else None
    opened = bool(entry.get('landed')) and isinstance(state, dict) and state.get('state') == 'ready'
    h.check(run, 'H8/action-docx', opened, {'entry': entry, 'state': state})
    if not opened:
        return
    x, y = s.evaluate(session, h.PAPER)
    h.real.click(session, kind, x, y)
    time.sleep(.6)
    type_text(session, kind, ' H8DOCX ')
    saved = h.save(session, kind)
    data = dav.get(name)
    h.check(run, 'H8/save-docx', saved and kind_of(data) == 'ooxml' and 'H8DOCX' in text_of(data)
            and dav.props(name)['type'] == DOCX and dav.listing() == before,
            {'saved': saved, 'kind': kind_of(data), 'text': 'H8DOCX' in text_of(data), 'type': dav.props(name)['type'], 'listing': dav.listing()})
    original = sha(data)
    taken_before = sha(dav.get(taken))
    type_text(session, kind, ' H8SAVEAS ')
    dialog = save_as(session, kind, run, dav)
    after = got(s.wait_until(session, f"(() => {{ const d = {DIALOG}; return d && d.message && d; }})()", 30))
    h.check(run, 'H8/save-as-offers', isinstance(dialog, dict) and dialog['name'] == f'd-{kind}'
            and [c['value'] for c in dialog['choices']] == ['odt', 'docx'] and dialog['choices'][0]['checked'], dialog)
    h.check(run, 'H8/save-as-taken', isinstance(after, dict) and after['open'] and '已經有' in (after['message'] or '')
            and sha(dav.get(taken)) == taken_before and sha(dav.get(name)) == original and dav.listing() == before,
            {'dialog': after, 'takenUnchanged': sha(dav.get(taken)) == taken_before, 'originalUnchanged': sha(dav.get(name)) == original})
    old_id = s.evaluate(session, FILE_ID)
    h.press(session, kind, '#save-as-name', .4)
    h.key(session, kind, 'a', ('ctrl',))  # the user's way to take the whole name
    type_text(session, kind, new.rsplit('.', 1)[0])
    h.press(session, kind, '#save-as-confirm', 1.0)
    moved = s.wait_until(session, f"(() => new URL(location.href).searchParams.get('fileId') !== {json.dumps(old_id)} && location.href)()", 60)
    state = writer_ready(session, new) if isinstance(moved, str) else None
    data = dav.get(new)
    props = dav.props(new)
    h.check(run, 'H8/save-as-odf-writer', isinstance(moved, str) and kind_of(data) == f'odf:{ODT}' and 'H8DOCX' in text_of(data)
            and 'H8SAVEAS' in text_of(data) and sha(dav.get(name)) == original and s.evaluate(session, FILE_ID) == props['fileId']
            and s.evaluate(session, TITLE) == new and isinstance(state, dict) and state.get('state') == 'ready',
            {'moved': moved, 'kind': kind_of(data), 'text': [w in text_of(data) for w in ('H8DOCX', 'H8SAVEAS')],
             'originalUnchanged': sha(dav.get(name)) == original, 'fileId': [s.evaluate(session, FILE_ID), props['fileId']],
             'title': s.evaluate(session, TITLE), 'state': state})
    if isinstance(state, dict) and state.get('state') == 'ready':
        x, y = s.evaluate(session, h.PAPER)
        h.real.click(session, kind, x, y)
        time.sleep(.6)
        type_text(session, kind, ' H8AFTER ')
        saved = h.save(session, kind)
        data = dav.get(new)
        h.check(run, 'H8/save-after-save-as-writer', saved and kind_of(data) == f'odf:{ODT}' and 'H8AFTER' in text_of(data)
                and sha(dav.get(name)) == original, {'saved': saved, 'text': 'H8AFTER' in text_of(data), 'originalUnchanged': sha(dav.get(name)) == original})
    h.check(run, 'H8/no-red-toast-writer', s.evaluate(session, h.RED) is None, s.evaluate(session, h.RED))
    (h.OUT / f'{kind}-writer.png').write_bytes(session.screenshot())
    h.leave(session, instance)


def calc_flow(session, kind, instance, run, dav):
    name, new = f'c-{kind}.xlsx', f'c-{kind}.ods'
    before = dav.listing()
    entry = open_row(session, instance, name, 'ods-editor.html')
    state = calc_ready(session, name) if entry.get('landed') else None
    opened = bool(entry.get('landed')) and isinstance(state, dict) and state.get('state') == 'ready'
    h.check(run, 'H8/action-xlsx', opened, {'entry': entry, 'state': state})
    if not opened:
        return
    b6.select(session, 'D9')
    b6.type_text(session, '#formula-input', 'H8XLSX')
    b6.box_key(session, 'Enter')
    time.sleep(.6)
    saved = b6.calc_save(session, kind)
    data = dav.get(name)
    h.check(run, 'H8/save-xlsx', saved and kind_of(data) == 'ooxml' and 'H8XLSX' in text_of(data)
            and dav.props(name)['type'] == XLSX and dav.listing() == before,
            {'saved': saved, 'kind': kind_of(data), 'text': 'H8XLSX' in text_of(data), 'type': dav.props(name)['type'], 'listing': dav.listing()})
    autos = s.evaluate(session, SAVES_AUTO)
    b6.select(session, 'D10')
    b6.type_text(session, '#formula-input', 'H8AUTO')
    b6.box_key(session, 'Enter')
    started = time.monotonic()
    landed = s.wait_until(session, f"(() => {SAVES_AUTO} > {autos})()", 75)
    data = dav.get(name)
    h.check(run, 'H8/autosave-xlsx', landed is True and kind_of(data) == 'ooxml' and 'H8AUTO' in text_of(data) and dav.listing() == before,
            {'landed': landed, 'seconds': round(time.monotonic() - started, 1), 'kind': kind_of(data), 'text': 'H8AUTO' in text_of(data)})
    original = sha(data)
    b6.select(session, 'D11')
    b6.type_text(session, '#formula-input', 'H8SAVEAS')
    b6.box_key(session, 'Enter')
    time.sleep(.6)
    old_id = s.evaluate(session, FILE_ID)
    dialog = save_as(session, kind, run, dav)
    h.check(run, 'H8/save-as-offers-calc', isinstance(dialog, dict) and dialog['name'] == f'c-{kind}'
            and [c['value'] for c in dialog['choices']] == ['ods', 'xlsx'] and dialog['choices'][0]['checked'], dialog)
    moved = s.wait_until(session, f"(() => new URL(location.href).searchParams.get('fileId') !== {json.dumps(old_id)} && location.href)()", 60)
    state = calc_ready(session, new) if isinstance(moved, str) else None
    data = dav.get(new)
    props = dav.props(new)
    h.check(run, 'H8/save-as-odf-calc', isinstance(moved, str) and kind_of(data) == f'odf:{ODS}' and all(w in text_of(data) for w in ('H8XLSX', 'H8AUTO', 'H8SAVEAS'))
            and sha(dav.get(name)) == original and s.evaluate(session, FILE_ID) == props['fileId'] and s.evaluate(session, TITLE) == new
            and isinstance(state, dict) and state.get('state') == 'ready',
            {'moved': moved, 'kind': kind_of(data), 'text': [w in text_of(data) for w in ('H8XLSX', 'H8AUTO', 'H8SAVEAS')],
             'originalUnchanged': sha(dav.get(name)) == original, 'fileId': [s.evaluate(session, FILE_ID), props['fileId']],
             'title': s.evaluate(session, TITLE), 'state': state})
    if isinstance(state, dict) and state.get('state') == 'ready':
        b6.select(session, 'D12')
        b6.type_text(session, '#formula-input', 'H8AFTER')
        b6.box_key(session, 'Enter')
        time.sleep(.6)
        saved = b6.calc_save(session, kind)
        data = dav.get(new)
        h.check(run, 'H8/save-after-save-as-calc', saved and kind_of(data) == f'odf:{ODS}' and 'H8AFTER' in text_of(data)
                and sha(dav.get(name)) == original, {'saved': saved, 'text': 'H8AFTER' in text_of(data), 'originalUnchanged': sha(dav.get(name)) == original})
    h.check(run, 'H8/no-red-toast-calc', s.evaluate(session, h.RED) is None, s.evaluate(session, h.RED))
    (h.OUT / f'{kind}-calc.png').write_bytes(session.screenshot())
    h.leave(session, instance)


def login_as(session, instance, user, password):
    s.navigate(session, instance.base + '/login', timeout=60)
    if isinstance(session, ChromeSession):
        session.evaluate('(()=>{window.__h8login=null;fetch("/login",{method:"POST",body:new URLSearchParams({user:' + json.dumps(user)
                         + ',password:' + json.dumps(password) + ',requesttoken:document.head.dataset.requesttoken})}).then(r=>window.__h8login=r.status);return true;})()')
        return s.wait_until(session, '(() => window.__h8login)()', 45)
    s.wait_until(session, "(() => document.querySelector('#user') !== null)()", 30)
    for selector, text in (('#user', user), ('#password', password)):
        element = session.command('POST', '/element', {'using': 'css selector', 'value': selector})['element-6066-11e4-a52e-4f735466cecf']
        session.command('POST', f'/element/{element}/value', {'text': text})
    session.click('button[type="submit"]')
    return s.wait_until(session, "(() => !location.pathname.endsWith('/login') && location.href)()", 45)


def read_only(session, kind, instance, run, dav, user, password):
    run['readOnlyLogin'] = login_as(session, instance, user, password)
    for name, page in ((f'r-{kind}.docx', 'e2-editor.html'), (f'r-{kind}.xlsx', 'ods-editor.html')):
        entry = open_row(session, instance, name, page, folder='')
        if page == 'e2-editor.html':
            s.wait_until(session, HOST_DONE, 180)
            state = s.wait_until(session, f"(() => {{ const w = {WRITER}; return w.state === 'ready' && w.doc && w.doc.includes('唯讀') && w; }})()", 60)
            state = got(state)
            view_only = state is not None
            save_as_button = s.evaluate(session, SHOWN.replace('ARG', json.dumps('#save-as')))
        else:
            state = calc_ready(session, name)
            view_only = isinstance(state, dict) and state.get('readOnly') is True
            save_as_button = s.evaluate(session, SHOWN.replace('ARG', json.dumps('#save-as-button')))
        time.sleep(1)
        lock = dav.props(name)['lock']
        h.check(run, f'H8/read-only-{name.rsplit(".", 1)[1]}', bool(entry.get('landed')) and view_only and lock != '1'
                and isinstance(save_as_button, dict) and save_as_button['hidden'] is True,
                {'entry': entry, 'state': state, 'lock': lock, 'saveAs': save_as_button})
        (h.OUT / f'{kind}-read-only-{name.rsplit(".", 1)[1]}.png').write_bytes(session.screenshot())
        s.navigate(session, instance.base + '/index.php/apps/files/', timeout=60)
        time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    args = parser.parse_args()
    h.OUT = args.out.resolve()
    h.OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(h.HOST)
    dav = Dav(instance)
    dav.dav('DELETE', FOLDER)  # this tool's own folder, left by a run that died; 404 is the usual answer
    dav.dav('MKCOL', FOLDER)
    h.FOLDER = FOLDER
    h.layout.FOLDER = FOLDER
    user, password = 'h8_' + secrets.token_hex(4), secrets.token_urlsafe(24)
    report = {'runs': [], 'temporaryUser': user, 'cleanup': {}}
    shares = []
    try:
        dav.ocs('POST', 'cloud/users', {'userid': user, 'password': password})
        report['userCreated'] = True
        with tempfile.TemporaryDirectory(dir=b6.SDK / 'build') as scratch:
            for kind in args.browsers.split(','):
                for prefix, ext in (('d', 'docx'), ('c', 'xlsx'), ('o', 'odt'), ('s', 'ods'), ('d', 'odt'), ('r', 'docx'), ('r', 'xlsx')):
                    dav.dav('PUT', f'{FOLDER}/{prefix}-{kind}.{ext}', FIXTURES[ext].read_bytes(), {'Content-Type': MIMES[ext]})
                for ext in ('docx', 'xlsx'):
                    share = dav.ocs('POST', 'apps/files_sharing/api/v1/shares', {'path': f'/{FOLDER}/r-{kind}.{ext}', 'shareType': 0,
                                                                                'shareWith': user, 'permissions': 1})
                    shares.append(share['id'])
                run = {'browser': kind, 'checks': []}
                report['runs'].append(run)
                for part in ('owner', 'reader'):
                    session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch) / f'{kind}-{part}'))
                    run.setdefault('versions', {})[part] = session.version
                    try:
                        if part == 'owner':
                            s.browser_login(session, instance.base, instance.password)
                            actions(session, kind, instance, run)
                            writer_flow(session, kind, instance, run, dav)
                            calc_flow(session, kind, instance, run, dav)
                        else:
                            read_only(session, kind, instance, run, dav, user, password)
                    except Exception:  # noqa: BLE001 -- recorded
                        run.setdefault('fatal', {})[part] = traceback.format_exc()
                        try:
                            (h.OUT / f'{kind}-{part}-fatal.png').write_bytes(session.screenshot())
                        except Exception:  # noqa: BLE001 -- a page held by a dialog cannot be shot either
                            pass
                    finally:
                        session.close()
                run['listing'] = dav.listing()
    finally:
        for share in shares:
            try:
                dav.ocs('DELETE', f'apps/files_sharing/api/v1/shares/{share}')
            except Exception as error:  # noqa: BLE001
                report['cleanup'].setdefault('errors', []).append(str(error))
        if report.get('userCreated'):
            try:
                dav.ocs('DELETE', f'cloud/users/{user}')
                report['cleanup']['userRemoved'] = True
            except Exception as error:  # noqa: BLE001
                report['cleanup'].setdefault('errors', []).append(str(error))
        report['cleanup']['folderDelete'] = dav.dav('DELETE', FOLDER)[0]
        checks = [c for r in report['runs'] for c in r['checks']]
        report['verdict'] = ('H8_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs'])
                             and not report['cleanup'].get('errors') else 'H8_RED')
        (h.OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(r['browser'], c['id'], c['pass']) for r in report['runs'] for c in r['checks']],
          [(r['browser'], {k: v[-300:] for k, v in (r.get('fatal') or {}).items()}) for r in report['runs']])
    return 0 if report['verdict'] == 'H8_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
