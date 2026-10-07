#!/usr/bin/env python3
"""E02 on v17 (V5 run): where the reduced after-key document differs from Writer's key arm, and where every
<text:soft-page-break/> sits.  Reads the owner's documents from wasm_sdk_probe/build/ only; prints tags, style
names and text LENGTHS, never text (attribute values that could carry text are replaced by <R>).

Re-run:  python3 -I findings/evidence/v17/v5/e02_breaks.py > findings/evidence/v17/v5/e02-breaks.txt
"""
import difflib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROBE = ROOT / "wasm_sdk_probe"
sys.path.insert(0, str(PROBE / "tools"))
from run_merge_wasm_shakedown import reduce_content  # noqa: E402  (spec 24's reduction, the runner's own)

NATIVE = PROBE / "build/merge-native-pmpc/r0c/round-20261006T150756Z/docs"
WASM = PROBE / "build/merge-wasm-private/shakedown-chrome-v5.docs"
TOKEN = re.compile(rb"(<[^>]+>)|([^<]+)")
REDACT = re.compile(rb'(text:string-value|office:string-value|xlink:title|xlink:href|text:name|draw:name)="[^"]*"')
BREAK = b"<text:soft-page-break/>"


def tokens(path: Path, reduced: bool) -> list[str]:
    raw = zipfile.ZipFile(path).read("content.xml")
    if reduced:
        raw = reduce_content(raw)
    return [REDACT.sub(rb'\1="<R>"', tag).decode()[:60] if tag else f"T({len(text.decode())})"
            for tag, text in TOKEN.findall(raw)]


def breaks(path: Path) -> list[str]:
    t = tokens(path, reduced=False)
    return [" | ".join(t[max(0, i - 3):i + 4]) for i, x in enumerate(t) if x == BREAK.decode()]


def diff(a: Path, b: Path) -> list[str]:
    ta, tb = tokens(a, True), tokens(b, True)
    out = [f"tokens {len(ta)} vs {len(tb)}"]
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ta, b=tb, autojunk=False).get_opcodes():
        if op != "equal":
            out.append(f"{op} a[{i1}:{i2}] b[{j1}:{j2}]")
            out += ["  - " + x for x in ta[i1:i2]] + ["  + " + x for x in tb[j1:j2]]
    return out


pairs = [("E02 after-key (WASM v17)", WASM / "E02-r1-after-key.odt"), ("E02 key arm r1 (native)", NATIVE / "r1-E02-key.odt"),
         ("E01 after-key (WASM v17)", WASM / "E01-r1-after-key.odt"), ("E01 key arm r1 (native)", NATIVE / "r1-E01-key.odt"),
         ("no-edit save (WASM v17, M2-0)", WASM / "m2-0-pmpc.odt"), ("original (native)", NATIVE / "original.odt")]
print("== reduced diff: E02 after-key (a, WASM) vs native key arm r1 (b) ==")
print("\n".join(diff(WASM / "E02-r1-after-key.odt", NATIVE / "r1-E02-key.odt")))
print("\n== reduced diff: E02 native key arms r2, r3 vs r1 (native repeatability) ==")
for n in (2, 3):
    print(f"r{n}:", diff(NATIVE / f"r{n}-E02-key.odt", NATIVE / "r1-E02-key.odt")[0],
          "hunks", len([x for x in diff(NATIVE / f"r{n}-E02-key.odt", NATIVE / "r1-E02-key.odt") if not x.startswith(("  ", "tokens"))]))
print("\n== soft page breaks (unreduced), context = 3 tokens either side ==")
for label, path in pairs:
    b = breaks(path)
    print(f"\n{label}: {len(b)}")
    for line in b:
        print("   " + line)
# Pair up the breaks by order and say which differ (context compared without token indexes).
print("\n== breaks that differ by context, pairwise in order ==")
for (la, pa), (lb, pb) in ((pairs[0], pairs[1]), (pairs[2], pairs[3]), (pairs[4], pairs[5])):
    ba, bb = breaks(pa), breaks(pb)
    differ = [i + 1 for i, (x, y) in enumerate(zip(ba, bb)) if x != y]
    print(f"{la} vs {lb}: {len(ba)} vs {len(bb)} breaks; differing (1-based order): {differ}")
