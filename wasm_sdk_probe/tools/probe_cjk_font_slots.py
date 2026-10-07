#!/usr/bin/env python3
"""Which font fills the Asian slot, per profile -- a diagnostic, not a check.

Written 2026-10-07 for the v15 shakedown (findings/evidence/v15-shakedown/
cjk-ab/).  On v15 every line of the product-path fixtures is shorter than on
v8, Latin-only lines included, and v15 changed the CJK pack from the full
Noto Sans CJK TTC (five families: JP KR SC TC HK) to a Traditional Chinese
subset (one family, TC, which fontconfig says covers zh-cn/ja/zh-tw but not ko).

For each profile this opens three documents in the product page (Chrome, CDP),
saves each through the product's own save button, and keeps:

  - the font names the ENGINE wrote: every `font-face` declaration and the
    default paragraph style's text properties, from styles.xml and content.xml;
  - the canvas as a PNG, and its rows of dark ink as runs (no merging), so a
    line pitch can be read without the product-path runner's band rules;

The third document is generated here: for each Asian-slot variant (default, and
font-name-asian = Noto Sans CJK TC / SC / JP / KR) two IDENTICAL one-line
paragraphs, then Latin-only pairs (default, TC, KR).  Within a pair the distance
between the two lines' ink tops is that variant's line height, whatever the ink.

Nothing is counted and nothing in dist/ is written: each profile is served from
a symlink mirror with the page repointed by the runner's own `repointed_page`.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp  # noqa: E402

FIXTURE = "cjk-font-slots.odt"  # at the mirror ROOT, which is a real directory
# (label, font-name-asian or None, carries CJK text, Asian country or None).
# The zh-TW rows use the names a real Taiwanese document carries (the owner's
# document names 思源黑體, PMingLiU/新細明體, Microsoft JhengHei, AR PL UMing TW
# and Noto Sans CJK TC, tagged zh-TW); its CONTENT is never used here.
VARIANTS = [("SLOT-DEFAULT", None, True, None), ("SLOT-TC", "Noto Sans CJK TC", True, None),
            ("SLOT-SC", "Noto Sans CJK SC", True, None), ("SLOT-JP", "Noto Sans CJK JP", True, None),
            ("SLOT-KR", "Noto Sans CJK KR", True, None), ("LATIN-DEFAULT", None, False, None),
            ("LATIN-TC", "Noto Sans CJK TC", False, None), ("LATIN-KR", "Noto Sans CJK KR", False, None),
            ("TW-DEFAULT", None, True, "TW"), ("TW-TC", "Noto Sans CJK TC", True, "TW"),
            ("TW-SIYUAN", "思源黑體", True, "TW"), ("TW-PMINGLIU", "PMingLiU", True, "TW"),
            ("TW-XIMINGTI", "新細明體", True, "TW"), ("TW-JHENGHEI", "Microsoft JhengHei", True, "TW"),
            ("TW-UMING", "AR PL UMing TW", True, "TW"), ("TW-KAI", "標楷體", True, "TW")]

ROWS = """(() => {
const canvas = document.querySelector('#canvas');
const w = canvas.width, h = canvas.height;
const data = canvas.getContext('2d').getImageData(0, 0, w, h).data;
const counts = [];
for (let y = 0; y < h; y += 1) {
  let n = 0, opaque = 0;
  for (let x = 0; x < w; x += 1) {
    const i = (y * w + x) * 4;
    if (data[i+3] > 128) opaque += 1;
    if (data[i+3] > 128 && data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) n += 1;
  }
  counts.push(n);
}
return {width: w, height: h, counts, png: canvas.toDataURL('image/png')};
})()"""


def fixture_bytes() -> bytes:
    ns = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
          'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
          'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
          'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"')
    families = sorted({v[1] for v in VARIANTS if v[1]})
    faces = "".join(f'<style:font-face style:name="{f}" svg:font-family="&apos;{f}&apos;" '
                    f'style:font-family-generic="system" style:font-pitch="variable"/>'
                    for f in families)
    styles, body = "", ""
    for index, (label, family, cjk, country) in enumerate(VARIANTS):
        props = (f' style:font-name-asian="{family}"' if family else "") + (
            f' style:language-asian="zh" style:country-asian="{country}"' if country else "")
        attr = ""
        if props:
            styles += (f'<style:style style:name="P{index}" style:family="paragraph">'
                       f'<style:text-properties{props}/></style:style>')
            attr = f' text:style-name="P{index}"'
        text = f"{label} 中文字 MH" if cjk else f"{label} MH MH"
        body += f"<text:p{attr}>{text}</text:p>" * 2
    content = (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {ns} '
               f'office:version="1.3"><office:font-face-decls>{faces}</office:font-face-decls>'
               f'<office:automatic-styles>{styles}</office:automatic-styles><office:body>'
               f'<office:text>{body}</office:text></office:body></office:document-content>')
    manifest = ('<?xml version="1.0" encoding="UTF-8"?><manifest:manifest '
                'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
                'manifest:version="1.3"><manifest:file-entry manifest:full-path="/" '
                'manifest:media-type="application/vnd.oasis.opendocument.text"/>'
                '<manifest:file-entry manifest:full-path="content.xml" '
                'manifest:media-type="text/xml"/></manifest:manifest>')
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        info = zipfile.ZipInfo("mimetype", date_time=(2026, 10, 7, 0, 0, 0))
        archive.writestr(info, "application/vnd.oasis.opendocument.text",
                         compress_type=zipfile.ZIP_STORED)
        for name, text in (("META-INF/manifest.xml", manifest), ("content.xml", content)):
            archive.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 7, 0, 0, 0)),
                             text, compress_type=zipfile.ZIP_DEFLATED)
    return out.getvalue()


def font_names(raw: bytes) -> dict:
    """The engine's own words: font-face declarations and the default style."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for part in ("styles.xml", "content.xml"):
            xml = archive.read(part).decode("utf-8") if part in archive.namelist() else ""
            out[part] = {
                "fontFaces": re.findall(r'<style:font-face style:name="([^"]*)"', xml),
                "defaultParagraph": re.findall(
                    r'<style:default-style style:family="paragraph">.*?'
                    r'<style:text-properties([^>]*)/?>', xml, re.S),
                "fontNameAttrs": sorted(set(re.findall(
                    r'style:font-name(?:-asian|-complex)?="[^"]*"', xml))),
            }
    return out


def runs(counts: list[int]) -> list[list[int]]:
    found, start = [], None
    for y, n in enumerate(counts + [0]):
        if n > 0 and start is None:
            start = y
        elif n == 0 and start is not None:
            found.append([start, y - 1])
            start = None
    return found


def pitches(png: bytes, left: int = 82, right: int = 680) -> dict:
    """Line pitch per variant, from the canvas PNG.

    Rows are counted only between `left` and `right`: the page frame inks every
    row (so a whole-canvas count is one run -- this probe's first reading), and
    the caret is drawn at x 80 on the first line.  Both lines of a pair are
    identical, so second top minus first top is that variant's line height.
    """
    from PIL import Image
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    width, height = image.size
    px = image.load()
    rows = [sum(1 for x in range(left, min(right, width))
                if px[x, y][3] > 128 and max(px[x, y][:3]) < 100) for y in range(height)]
    found = runs(rows)
    out = {"columns": [left, right], "runs": found}
    if len(found) == 2 * len(VARIANTS):
        out["pitch"] = {v[0]: found[2 * i + 1][0] - found[2 * i][0]
                        for i, v in enumerate(VARIANTS)}
    return out


def settle(session, tries: int = 20) -> dict:
    last = None
    for _ in range(tries):
        time.sleep(0.8)
        scan = pp.evaluate(session, ROWS)
        if scan and last and scan["counts"] == last["counts"] and any(scan["counts"]):
            return scan
        last = scan
    return last or {}


def measure(profile: str, out_dir: Path, fixture: bytes) -> dict:
    root = pp.PROJECT / "dist"
    source = (root / "e2-editor-app.js").read_text(encoding="utf-8")
    page, pin_before, wasm = pp.repointed_page(
        source, profile, root / "profiles" / profile / "sdk-manifest.json")
    mirror = Path(tempfile.mkdtemp(prefix="cjk-font-slots-")) / "root"
    # `build_mirror` only REPLACES files the source has (measured: the first run
    # of this probe served a 404 page as the fixture, and the engine opened it).
    # The fixture is new, so it is written after the mirror exists -- at the
    # mirror's root, which is a real directory; every subdirectory not on an
    # override's path is a SYMLINK into dist/, and writing there writes dist.
    pp.build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8")})
    if (mirror / FIXTURE).exists() or not mirror.is_dir() or mirror.is_symlink():
        raise SystemExit(f"refusing to write the fixture into {mirror}")
    (mirror / FIXTURE).write_bytes(fixture)
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(pp.PROJECT / "web" / "serve.py"),
                               "--port", str(port), "--root", str(mirror)],
                              cwd=pp.PROJECT, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    result = {"profile": profile, "pinBefore": pin_before, "wasm": wasm[:16], "documents": []}
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = pp.ChromeSession("cold")
        pp.navigate(session, base)
        booted = pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        result["boot"] = booted
        result["shims"] = pp.evaluate(session, pp.INSTALL)
        for name, url in ((None, None), ("endnote-frame.odt", "./e1-fixtures/endnote-frame.odt"),
                          ("cjk-font-slots.odt", "./" + FIXTURE)):
            if url:
                pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", url).replace("ARG_NAME", name))
                pp.wait_for(session, lambda s: (s.get("doc") or "") == name
                            and s.get("state") == "ready", 120)
            index = pp.evaluate(session, pp.SAVE_COUNT) or 0
            pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
            saved = None
            if pp.wait_saves(session, index + 1):
                saved = pp.evaluate(session, pp.READ_SAVE.replace("ARG_INDEX", str(index)))
            doc = {"document": name or (booted or {}).get("doc")}
            if saved:
                raw = base64.b64decode(saved["b64"])
                doc["savedBytes"] = len(raw)
                doc["fontNames"] = font_names(raw)
                # Which document is this, by its own text -- not by the name the
                # page shows, which is whatever the file input was told.
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    content = archive.read("content.xml").decode("utf-8")
                doc["firstText"] = re.sub(r"<[^>]+>", " ", content.split("<office:text", 1)[-1])[:80].split()
                if name == "cjk-font-slots.odt":
                    doc["fixtureOpened"] = all(v[0] in content for v in VARIANTS)
            scan = settle(session)
            if scan:
                stem = f"{profile}-{(doc['document'] or 'boot').removesuffix('.odt')}"
                png = scan.pop("png")
                (out_dir / f"{stem}.png").write_bytes(
                    base64.b64decode(png.split(",", 1)[1]))
                doc["canvas"] = [scan["width"], scan["height"]]
                doc["inkRuns"] = runs(scan["counts"])
                doc["png"] = f"{stem}.png"
                if name == "cjk-font-slots.odt":
                    doc["pitches"] = pitches(base64.b64decode(png.split(",", 1)[1]))
            result["documents"].append(doc)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", nargs="+",
                        default=["e2-editor-v8", "e2-editor-v15", "e2-editor-v15-cjk-r5-ab"])
    parser.add_argument("--out", type=Path, required=True, help="a directory")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fixture = fixture_bytes()
    (args.out / "cjk-font-slots.odt").write_bytes(fixture)
    report = {"startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "browser": "chrome",
              "variants": [list(v) for v in VARIANTS],
              "profiles": [measure(profile, args.out, fixture) for profile in args.profiles],
              "completedAt": None}
    report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (args.out / "font-slots.json").write_text(json.dumps(report, indent=1, ensure_ascii=False),
                                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
