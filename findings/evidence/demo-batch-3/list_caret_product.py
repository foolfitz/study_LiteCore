#!/usr/bin/env python3
"""Finding 180 on the product path: the shipped page (dist/, generation 85, v30), real keys.  Caret after BR in the second paragraph, press
the button, type q, save.  Native Writer leaves the caret where it was, so the paragraph should read BRqAVO.
  python3 list_caret_product.py OUT
"""
import json, shutil, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
import check_writer_zoom as z
from check_writer_zoom import common, evaluate, pp, real
import check_writer_align as a
import io, xml.etree.ElementTree as ET, zipfile

TEXT = a.TEXT
def texts(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = ET.fromstring(archive.read('content.xml'))
    return [''.join(p.itertext()) for p in root.iter() if p.tag in (TEXT + 'p', TEXT + 'h')]

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=False)
scratch = Path(tempfile.mkdtemp(prefix='list-caret-', dir=z.PROJECT / 'build'))
report = {'page': 'dist/e2-editor-app.js', 'arms': []}
try:
    with common.browser_lock('list_caret_product'):
        pp.build_mirror(common.DIST, scratch / 'm', {'e2-editor.html': common.inject((common.DIST / 'e2-editor.html').read_text(encoding='utf-8'), [z.OBSERVER, a.WATCH]).encode()})
        with common.served(scratch / 'm') as base:
            session = common.open_browser('chrome', (1400, 1000))
            try:
                raw = a.FIXTURE.read_bytes()
                for action in (None, 'set-list-unordered', 'set-list-ordered', 'set-paragraph-heading'):
                    page = a.Page(session, 'chrome', {'base': base, 'checks': []})
                    page.open(raw)
                    page.click_paper(1500, 1500)
                    page.quiet()
                    page.place(1)
                    page.key('Home')
                    page.key('ArrowRight'); page.key('ArrowRight')
                    if action:
                        page.press(f'[data-action="{action}"]')
                        page.quiet()
                    page.key('q')
                    page.quiet()
                    report['arms'].append({'action': action, 'paragraph': texts(page.save())[1]})
                    print(report['arms'][-1], flush=True)
            finally:
                common.close_browser(session)
finally:
    shutil.rmtree(scratch, ignore_errors=True)
(out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
