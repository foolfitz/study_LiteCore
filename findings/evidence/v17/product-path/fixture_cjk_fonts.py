#!/usr/bin/env python3
"""PREDICTION.md P4 (descriptive): which fixtures the product page can open carry CJK text whose Asian font
the profile lacks.  The population is the page's own picker list, `dist/e1-fixtures/manifest.json` (the page
fetches it, `web/e2-editor-app.js`), not a hand list; the runner also opens three of them by URL.

For each fixture: CJK character count in content.xml; every Asian font name a style or the default style names
(`style:font-name-asian`, resolved through `style:font-face` to its family); the default Asian language/country.
A name is "absent" when it is not one of the five families the v16/v17 CJK pack carries.  This reads the
documents only; it does not resolve which style a given paragraph ends up with.

Re-run:  python3 -I findings/evidence/v17/product-path/fixture_cjk_fonts.py > findings/evidence/v17/product-path/fixture-cjk-fonts.txt
"""
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "wasm_sdk_probe" / "dist" / "e1-fixtures"
PACK = {"Noto Sans CJK TC", "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK KR", "Noto Sans CJK HK"}
CJK = re.compile(r"[　-〿぀-ヿ㐀-䶿一-鿿가-힯豈-﫿＀-￯]")


def main() -> int:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    paths = [f["path"] for f in manifest["fixtures"]]
    if not paths:
        print("STOP: the manifest lists no fixtures")
        return 2
    print(f"manifest {manifest.get('release')} ({len(paths)} fixtures)\n")
    print("| fixture | CJK chars | Asian font names (family) | default Asian lang | absent from the pack |")
    print("|---|---|---|---|---|")
    flagged = []
    for path in paths:
        z = zipfile.ZipFile(FIXTURES / path)
        parts = {n: z.read(n).decode("utf-8") for n in ("content.xml", "styles.xml") if n in z.namelist()}
        text = re.sub(r"<[^>]+>", "", parts.get("content.xml", ""))
        cjk = len(CJK.findall(text))
        both = "".join(parts.values())
        faces = dict(re.findall(r'<style:font-face style:name="([^"]*)"[^>]*?svg:font-family="([^"]*)"', both))
        names = sorted({faces.get(n, n).strip("'&apos;") for n in re.findall(r'style:font-name-asian="([^"]*)"', both)})
        m = re.search(r"<style:default-style style:family=\"paragraph\">.*?</style:default-style>", both, re.S)
        lang = None
        if m:
            la = re.search(r'style:language-asian="([^"]*)"', m.group(0))
            co = re.search(r'style:country-asian="([^"]*)"', m.group(0))
            lang = f"{la.group(1) if la else '-'}-{co.group(1) if co else '-'}"
        absent = [n for n in names if n not in PACK]
        if cjk and (absent or not names):
            flagged.append(path)
        print(f"| `{path}` | {cjk} | {', '.join(names) or '(none)'} | {lang} | {', '.join(absent) or ('(no Asian font named)' if not names else '-')} |")
    print(f"\nWith CJK text and an Asian font name absent from the pack, or no Asian font named at all: {len(flagged)}")
    for p in flagged:
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
