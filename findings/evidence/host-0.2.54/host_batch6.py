#!/usr/bin/env python3
"""SPEC-P-demo-batch-6 on the installed host: New spreadsheet, upload-and-open of an .ods, LibreOffice's icons; New document as before.

The owner's path, Files' own UI: the New menu, its name dialog, the upload input; real pointer and keys in the editors; the files read back over
WebDAV.  The blank file a user gets is compared with what the host's own BlankDocument chooses for that user, by `php -r`, the way
check_new_document_choice.php_choose reads it.  Run on 0.2.53 first: there is no New spreadsheet there, and that is the tool's red.  Run with
host-stack/bin first on PATH.
  python3 -I host_batch6.py --out DIR [--browsers chrome,firefox]

Fixed by review before the first run (2026-11-03): with no New spreadsheet entry the scenario returned at once, so on 0.2.53 H6/create-ods was
never recorded (the spec's red names it) and the upload and New document cells were never reached.  Now the missing entry is recorded as
H6/create-ods/the-chosen-blank false, the creation and its save are skipped, and the upload and New document cells run on every host.

Fixed by execution (2026-11-03, h6-red-on-0253): the routes were '/apps/litecore/r/ods-editor.html', but the route redirects to a versioned
path, /apps/litecore/r/<buildId>-<hash>/ods-editor.html, so the wait never matched and returned its timeout record, a dict, which bool() reads
as true: every `landed` half was vacuous and cost 60 to 90 s.  The routes are now the page names, as host_layout.go waits for them, and a cell
takes `landed` only as the href string the wait returns on a match.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SDK = ROOT / 'wasm_sdk_probe'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = load('host_batch4', HERE.parent / 'host-0.2.52/host_batch4.py')
s, real, HOST = h.s, h.real, h.HOST
sys.path.insert(0, str(SDK / 'tools'))
import make_new_spreadsheet_templates as ods  # noqa: E402
import make_new_document_templates as odt  # noqa: E402
from check_m3_new_document import CLICK_ANY, DIALOG_INPUT, DIALOG_SUBMIT, NEW_BUTTON, PICKER_SUBMIT, type_name  # noqa: E402
import run_calc_cell_native as cells  # noqa: E402
from run_calc_editor_browser import key as box_key, select, type_text  # noqa: E402

FOLDER = 'LiteCore-batch6'
ODS_MIME = 'application/vnd.oasis.opendocument.spreadsheet'
CALC_ROUTE, WRITER_ROUTE = '/ods-editor.html', '/e2-editor.html'
BLUE, GREEN = '#1a85d1', '#'  # the green is read from the icon file at start
UPLOAD_INPUT = '[data-cy-upload-picker-input]'
ENTRIES = """(() => [...document.querySelectorAll('[data-cy-upload-picker-menu-entry]')].map(e => ({id: e.getAttribute('data-cy-upload-picker-menu-entry'),
  text: e.textContent.trim(), svg: (e.querySelector('svg') || {}).outerHTML || ''})))()"""
CALC_READY = "(() => window.__calcEditor?.state?.state === 'ready' && Boolean(window.__calcEditor.state.cell))()"
WRITER_READY = "(() => { const v = document.documentElement.getAttribute('data-litecore'); return Boolean(v && JSON.parse(v).done); })()"
FIXTURE_ODS = ROOT / 'findings/evidence/host-0.2.50/files-workflow-01/fixture/cell-editing.ods'


def check(run, name, passed, actual=None):
    run['checks'].append({'id': name, 'pass': bool(passed), 'actual': actual})


def php(method, language, locale):
    script = ("require $argv[1]; $c = OCA\\LiteCore\\Template\\BlankDocument::" + method + "($argv[2], $argv[3] === '' ? null : $argv[3]);"
              " echo json_encode($c);")
    done = subprocess.run(['php', '-r', script, str(HOST / 'lib/Template/BlankDocument.php'), language, locale or ''], capture_output=True, text=True, timeout=60)
    return json.loads(done.stdout) if done.returncode == 0 else {'error': done.stderr.strip()[-300:]}


def admin_choice():
    def occ(*args):
        return subprocess.run(['ddev', 'occ', *args], cwd=HOST, capture_output=True, text=True, timeout=120).stdout.strip()
    language = occ('user:setting', 'admin', 'core', 'lang') or 'en'
    locale = (occ('config:system:get', 'force_locale') or occ('user:setting', 'admin', 'core', 'locale') or occ('config:system:get', 'default_locale') or None)
    return language, locale


def folder_url(instance):
    return instance.base + '/index.php/apps/files/files?dir=' + urllib.parse.quote('/' + FOLDER)


def open_menu(session):
    s.wait_until(session, f"(() => document.querySelector({json.dumps(NEW_BUTTON)}) !== null)()", 60)
    s.evaluate(session, CLICK_ANY.replace('ARG', json.dumps(NEW_BUTTON)))
    s.wait_until(session, "(() => document.querySelectorAll('[data-cy-upload-picker-menu-entry]').length > 0)()", 20)
    time.sleep(.5)
    return s.evaluate(session, ENTRIES)


def create(session, kind, instance, entry_id, name, route, ready):
    s.navigate(session, folder_url(instance), timeout=120)
    open_menu(session)
    s.evaluate(session, CLICK_ANY.replace('ARG', json.dumps(f'[data-cy-upload-picker-menu-entry="{entry_id}"]')))
    s.wait_until(session, f"(() => document.querySelector({json.dumps(DIALOG_INPUT)}) !== null)()", 20)
    type_name(session, kind, name)
    s.evaluate(session, CLICK_ANY.replace('ARG', json.dumps(DIALOG_SUBMIT)))
    where = s.wait_until(session, "(() => (location.pathname.endsWith(" + json.dumps(route) + ") && 'route')"
                                  " || (document.querySelector('form.templates-picker__form') && 'picker') || false)()", 60)
    if where == 'picker':
        s.evaluate(session, PICKER_SUBMIT)
    landed = s.wait_until(session, f"(() => location.pathname.endsWith({json.dumps(route)}) && location.href)()", 90)
    return landed, s.wait_until(session, ready, 180)


def calc_save(session, kind):
    before = s.evaluate(session, h.layout.SAVES)
    h.press(session, kind, '#save-button')
    until, count = time.monotonic() + 40, before
    while time.monotonic() < until and count <= before:
        count = s.evaluate(session, h.layout.SAVES)
        time.sleep(.3)
    return count > before


def a1_text(raw):
    with tempfile.NamedTemporaryFile(suffix='.ods') as f:
        f.write(raw)
        f.flush()
        _, table = cells.cells_from_xml(Path(f.name))
        cell = table.get((0, 0, 0))
        return None if cell is None else ''.join(cell.itertext())


def upload_and_open(session, kind, instance, source, name, route, ready, scratch):
    local = scratch / name
    shutil.copyfile(source, local)
    s.navigate(session, folder_url(instance), timeout=120)
    s.wait_until(session, f"(() => document.querySelector({json.dumps(UPLOAD_INPUT)}) !== null)()", 60)
    session.set_file(UPLOAD_INPUT, local)
    row = f'[data-cy-files-list-row-name={json.dumps(name)}] [data-cy-files-list-row-name-link]'
    seen = s.wait_until(session, f"(() => document.querySelector({json.dumps(row)}) !== null)()", 60)
    time.sleep(1.5)
    session.click(row)
    landed = s.wait_until(session, f"(() => location.pathname.endsWith({json.dumps(route)}) && location.href)()", 60)
    return bool(seen), landed, s.wait_until(session, ready, 180)


def scenario(session, kind, instance, run, expected, scratch):
    s.navigate(session, folder_url(instance), timeout=120)
    entries = open_menu(session)
    (h.OUT / f'{kind}-menu.png').write_bytes(session.screenshot())
    ours = [e for e in entries if (e['id'] or '').startswith('template-new-litecore-')]
    sheet = next((e for e in ours if e['text'] in ('New spreadsheet', '新試算表')), None)
    doc = next((e for e in ours if e['text'] in ('New document', '新文字文件')), None)
    run['entries'] = [{k: v for k, v in e.items() if k != 'svg'} | {'svgSha256': hashlib.sha256(e['svg'].encode()).hexdigest()[:16]} for e in entries]
    check(run, 'H6/new-menu/spreadsheet-offered', sheet is not None, [e['text'] for e in entries])
    check(run, 'H6/new-menu/icons', bool(sheet and doc and GREEN in sheet['svg'].lower() and BLUE in doc['svg'].lower()),
          {'document': (doc or {}).get('svg', '')[:120], 'spreadsheet': (sheet or {}).get('svg', '')[:120]})
    s.evaluate(session, "document.activeElement?.blur()")
    if sheet is None:
        check(run, 'H6/create-ods/the-chosen-blank', False, 'no New spreadsheet entry to create from')
    else:
        create_ods(session, kind, instance, run, expected, sheet)
    upload_and_new_odt(session, kind, instance, run, expected, scratch, doc)


def create_ods(session, kind, instance, run, expected, sheet):
    name = f'H6-new-{kind}.ods'
    landed, ready = create(session, kind, instance, sheet['id'], name, CALC_ROUTE, CALC_READY)
    check(run, 'H6/opens-in-calc', isinstance(landed, str) and ready is True, {'landed': landed, 'ready': ready})
    raw = instance.dav('GET', f'{FOLDER}/{name}')[1]
    blank = (ROOT / 'wasm_sdk_probe/build/host-0.2.54/litecore/blank-ods' / expected['spreadsheet'].get('file', '-'))
    check(run, 'H6/create-ods/the-chosen-blank', blank.is_file() and hashlib.sha256(raw).hexdigest() == hashlib.sha256(blank.read_bytes()).hexdigest(),
          {'choice': expected['spreadsheet'], 'bytes': len(raw)})
    if ready is True:
        select(session, 'A1')
        type_text(session, '#formula-input', 'H6VALUE')
        box_key(session, 'Enter')
        s.wait_until(session, "(() => !window.__calcEditor.state.busy && !window.__calcEditor.state.editing)()", 30)
        check(run, 'H6/edit-save/save-settled', calc_save(session, kind))
        saved = instance.dav('GET', f'{FOLDER}/{name}')[1]
        record = json.loads((blank.parent / 'MANIFEST.json').read_text())['files'].get(blank.name, {})
        described = ods.describe(saved)
        check(run, 'H6/edit-save/value', a1_text(saved) == 'H6VALUE', a1_text(saved))
        check(run, 'H6/edit-save/defaults-kept', record and not ods.compare(record, described), ods.compare(record, described) if record else 'no record')
        (h.OUT / f'{kind}-calc.png').write_bytes(session.screenshot())


def upload_and_new_odt(session, kind, instance, run, expected, scratch, doc):
    seen, landed, ready = upload_and_open(session, kind, instance, FIXTURE_ODS, f'H6-upload-{kind}.ods', CALC_ROUTE, CALC_READY, scratch)
    first = s.evaluate(session, "(() => window.__calcEditor?.state?.cell?.input ?? null)()") if ready is True else None
    check(run, 'H6/upload-ods/opens-in-calc', seen and isinstance(landed, str) and ready is True, {'row': seen, 'landed': landed, 'ready': ready, 'a1': first})
    if ready is True:
        select(session, 'D9')
        type_text(session, '#formula-input', 'UPLOADED')
        box_key(session, 'Enter')
        s.wait_until(session, "(() => !window.__calcEditor.state.busy && !window.__calcEditor.state.editing)()", 30)
        check(run, 'H6/upload-ods/save-settled', calc_save(session, kind))
        saved = instance.dav('GET', f'{FOLDER}/H6-upload-{kind}.ods')[1]
        with tempfile.NamedTemporaryFile(suffix='.ods') as f:
            f.write(saved)
            f.flush()
            _, table = cells.cells_from_xml(Path(f.name))
            d9 = table.get((0, 3, 8))
        check(run, 'H6/upload-ods/the-host-holds-it', d9 is not None and ''.join(d9.itertext()) == 'UPLOADED', None if d9 is None else ''.join(d9.itertext()))
    seen, landed, ready = upload_and_open(session, kind, instance, h.t.LEVELS, f'H6-upload-{kind}.odt', WRITER_ROUTE, WRITER_READY, scratch)
    check(run, 'H6/upload-odt/opens-in-writer', seen and isinstance(landed, str) and ready is True, {'row': seen, 'landed': landed, 'ready': ready})

    name = f'H6-new-{kind}.odt'
    landed, ready = create(session, kind, instance, doc['id'], name, WRITER_ROUTE, WRITER_READY)
    raw = instance.dav('GET', f'{FOLDER}/{name}')[1]
    blank = HOST / 'blank' / expected['document'].get('file', '-')
    check(run, 'H6/new-odt-still-works', isinstance(landed, str) and ready is True and blank.is_file()
          and hashlib.sha256(raw).hexdigest() == hashlib.sha256(blank.read_bytes()).hexdigest(), {'landed': landed, 'ready': ready, 'choice': expected['document']})
    h.leave(session, instance)


def main():
    global GREEN
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    args = parser.parse_args()
    h.OUT = args.out.resolve()
    h.OUT.mkdir(parents=True, exist_ok=False)
    icon = (ROOT / 'wasm_sdk_probe/build/host-0.2.54/litecore/img/oasis-spreadsheet.svg').read_text()
    GREEN = sorted({c.lower() for c in __import__('re').findall(r'fill="(#[0-9a-fA-F]{6})"', icon)} - {'#fafafa', '#ffffff'})[0]
    language, locale = admin_choice()
    expected = {'language': language, 'locale': locale, 'document': php('choose', language, locale), 'spreadsheet': php('chooseSpreadsheet', language, locale)}
    instance = s.Instance(HOST)
    try:
        instance.dav('DELETE', FOLDER)  # this tool's own folder, left by a run that died
    except Exception:  # noqa: BLE001 -- absent, the usual case
        pass
    instance.dav('MKCOL', FOLDER)
    report = {'expected': expected, 'green': GREEN, 'runs': []}
    with tempfile.TemporaryDirectory(dir=SDK / 'build') as scratch:
        for kind in args.browsers.split(','):
            run = {'browser': kind, 'checks': []}
            report['runs'].append(run)
            session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch)))
            run['version'] = session.version
            try:
                s.browser_login(session, instance.base, instance.password)
                scenario(session, kind, instance, run, expected, Path(scratch))
            except Exception:  # noqa: BLE001 -- recorded
                run['fatal'] = traceback.format_exc()
                (h.OUT / f'{kind}-fatal.png').write_bytes(session.screenshot())
            finally:
                session.close()
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'H6_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'H6_RED'
    (h.OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(c['id'], c['pass']) for c in checks], [(r.get('fatal') or '')[-300:] for r in report['runs']])
    return 0 if report['verdict'] == 'H6_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
