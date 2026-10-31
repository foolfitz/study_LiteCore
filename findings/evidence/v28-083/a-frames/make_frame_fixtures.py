#!/usr/bin/env python3
"""Spec v28 append 2 (L-fallback-html-read-is-new-on-this-path, section 9): five documents whose empty LAST paragraph has
a frame near it, written as .fodt, then each saved ONCE as ODT by the native core (the S4 makers' recipe,
../fixtures-s4/make_s4_odts.py).

  frame-para-last        an image anchored to the empty last paragraph (text:anchor-type="paragraph")
  frame-char-last        an image anchored at a character of the empty last paragraph (anchor-type="char")
  textbox-para-last      a text box (no image) anchored to the empty last paragraph
  prev-aschar-image      the previous paragraph ENDS in an as-char image; the last paragraph is plain and empty
  prev-note-frame        the previous paragraph ends in a footnote whose body has an as-char image (finding 038's shape)

  python3 -I make_frame_fixtures.py --out DIR      (DIR must not exist)
"""
import argparse
import base64
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import tempfile
import time
import zlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INSTALL = ROOT / 'native-lok-26-8/build/instdir/program'


def png():
    """An 8x8 solid PNG, built here so the fixture has no outside input."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    raw = b''.join(b'\x00' + b'\x30\x60\xc0' * 8 for _ in range(8))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 8, 8, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


B64 = base64.b64encode(png()).decode()


def image(name, anchor):
    return (f'<draw:frame draw:name="{name}" text:anchor-type="{anchor}" svg:width="2cm" svg:height="2cm">'
            f'<draw:image><office:binary-data>{B64}</office:binary-data></draw:image></draw:frame>')


TEXTBOX = ('<draw:frame draw:name="T1" text:anchor-type="paragraph" svg:width="4cm" svg:height="2cm">'
           '<draw:text-box><text:p>In frame</text:p></draw:text-box></draw:frame>')
NOTE = ('<text:note text:id="ftn0" text:note-class="footnote"><text:note-citation>1</text:note-citation>'
        f'<text:note-body><text:p>Note {image("N1", "as-char")}</text:p></text:note-body></text:note>')
BODIES = {
    'frame-para-last': f'<text:p>Plain first</text:p>\n<text:p>{image("I1", "paragraph")}</text:p>',
    'frame-char-last': f'<text:p>Plain first</text:p>\n<text:p>{image("I1", "char")}</text:p>',
    'textbox-para-last': f'<text:p>Plain first</text:p>\n<text:p>{TEXTBOX}</text:p>',
    'prev-aschar-image': f'<text:p>Plain first{image("I1", "as-char")}</text:p>\n<text:p/>',
    'prev-note-frame': f'<text:p>Plain first{NOTE}</text:p>\n<text:p/>',
}
SHELL = '''<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">
<office:automatic-styles>
 <style:page-layout style:name="pm1">
  <style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/>
 </style:page-layout>
</office:automatic-styles>
<office:master-styles>
 <style:master-page style:name="Standard" style:page-layout-name="pm1"/>
</office:master-styles>
<office:body><office:text>
BODY
</office:text></office:body></office:document>
'''


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    out = ap.parse_args().out.resolve()
    if out.exists():
        ap.error('output must be fresh')
    out.mkdir(parents=True)
    versionrc = (INSTALL / 'versionrc').read_text()
    buildid = next((l.split('=', 1)[1] for l in versionrc.splitlines() if l.startswith('buildid=')), None)
    receipts, ok = [], True
    for name, body in BODIES.items():
        source = out / f'{name}.fodt'
        source.write_text(SHELL.replace('BODY', body), encoding='utf-8')
        work = pathlib.Path(tempfile.mkdtemp(prefix='a-frames-'))
        try:
            shutil.copyfile(source, work / source.name)
            argv = [str(INSTALL / 'soffice'), f'-env:UserInstallation={(work / "profile").as_uri()}', '--headless',
                    '--norestore', '--convert-to', 'odt', '--outdir', str(work / 'out'), str(work / source.name)]
            t0 = time.monotonic()
            result = subprocess.run(argv, capture_output=True, text=True, timeout=180)
            seconds = round(time.monotonic() - t0, 2)
            if (work / 'out' / f'{name}.odt').is_file():
                shutil.copyfile(work / 'out' / f'{name}.odt', out / f'{name}.odt')
        finally:
            shutil.rmtree(work, ignore_errors=True)
        odt = out / f'{name}.odt'
        ok = ok and odt.is_file() and result.returncode == 0
        receipts.append({'argv': argv, 'exitCode': result.returncode, 'seconds': seconds, 'stdout': result.stdout,
                         'stderr': result.stderr, 'buildid': buildid,
                         'input': {'path': source.name, 'sha256': sha(source)},
                         'output': {'path': odt.name, 'sha256': sha(odt)} if odt.is_file() else None})
    (out / 'receipt.json').write_text(json.dumps({'schema': 1, 'documents': receipts}, indent=1) + '\n')
    print(json.dumps([{k: r[k] for k in ('exitCode', 'seconds', 'output')} for r in receipts], indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
