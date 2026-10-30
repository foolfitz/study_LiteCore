#!/usr/bin/env python3
"""W-f3-text-observable (SPEC-M3-select-all-v26 append 2; fable ruling B modified, 3.6): the bound product-path
runner on frozen generation 80, with its three copy-toast parses replaced by a clipboard read.

Derived from tools/run_e2_c_product_path.py (bound; not edited and not copied).  This file reads the bound source,
refuses unless its sha256 is BOUND_SHA256, applies exactly the three REPLACEMENTS below (each must match once),
and executes the result as the module `run_e2_c_product_path_clipboard`, with `__file__` the bound file so every
path the runner derives from it is unchanged.  The closed list of differences is REPLACEMENTS plus
`_clipboard_text`, which they call; the shell manifest is rebound to generation 80 before the source executes,
exactly as tools/run_v80_f3.py does.

Why: the runner took the ENGINE's selected text from the copy toast's `U+XXXX` list (bound source ~7515
`an-aborted-gesture-stops-selecting`, ~8408 `an-inline-format-reaches-a-selection`, ~8504
`the-page-agrees-with-the-engine-about-the-selection`).  Finding 175 (generation 80) prints 「已複製 N 字」
instead, so the three Chrome cells lost their observable (findings/evidence/select-all-v26/f3/MOVED-CELLS.md).
The page writes the same text to the system clipboard, and in Chrome the runner already grants clipboardReadWrite
and emulates focus before the first navigation, so the text is read back with `navigator.clipboard.readText()`.

Freshness, so a stale clipboard cannot pass: the runner clears the toast before each copy; `_clipboard_text` reads
the clipboard only when the toast then says exactly 「已複製 N 字」, and uses the text only when its code-point count
equals N; otherwise it returns "" -- what the toast parse returned when the copy failed.  Every read is recorded.
Firefox has no clipboard grant (L-firefox-copy): its copy is refused, so its three cells are not expected to move.

  python3 tools/run_e2_c_product_path_clipboard.py --browser chrome --out <new dir>

Writes <dir>/report.json (the runner's own --out), <dir>/shell-manifest-override.json and
<dir>/clipboard-reads.json.  Refuses an existing <dir>.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import types

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_e2_c_shell_bundle as _bundle  # noqa: E402

BOUND = TOOLS / 'run_e2_c_product_path.py'
BOUND_SHA256 = '7ba302353dd67d5f4c7643e1abc0e5c06105e7b7ebbb191b3c29b24b8e90a6a2'
NAME = 'run_e2_c_product_path_clipboard'
REPLACEMENTS = (
    ('an-aborted-gesture-stops-selecting',
     '            text = "".join(chr(int(point, 16)) for point\n'
     '                           in re.findall(r"U\\+([0-9A-Fa-f]{4,6})", reach))',
     '            text = _clipboard_text(session, reach, "an-aborted-gesture-stops-selecting")'),
    ('an-inline-format-reaches-a-selection',
     '                    selected = "".join(\n'
     '                        chr(int(point, 16))\n'
     '                        for point in re.findall(r"U\\+([0-9A-Fa-f]{4,6})", copied))',
     '                    selected = _clipboard_text(session, copied, "an-inline-format-reaches-a-selection")'),
    ('the-page-agrees-with-the-engine-about-the-selection',
     '            agreement["engineCodePoints"] = len(\n'
     '                re.findall(r"U\\+([0-9A-Fa-f]{4,6})", copied_s))',
     '            agreement["engineCodePoints"] = len(\n'
     '                _clipboard_text(session, copied_s, "the-page-agrees-with-the-engine-about-the-selection"))'),
)
COPIED = re.compile(r'已複製 (\d+) 字')
READS = []


def _clipboard_text(session, toast, site):
    """The engine's copied text, read from the clipboard this copy wrote -- or "" when it cannot be shown to be."""
    from r7_support import evaluate
    row = {'site': site, 'toast': toast, 'at': time.time()}
    match = COPIED.fullmatch(toast or '')
    text = ''
    if match:
        try:
            value = evaluate(session, 'navigator.clipboard.readText()')
        except Exception as error:  # noqa: BLE001 -- recorded; "" is the failed-copy answer
            value, row['error'] = None, f'{type(error).__name__}: {error}'
        row['clipboardCodePoints'] = len(value) if isinstance(value, str) else None
        if isinstance(value, str) and len(value) == int(match.group(1)):
            text = value
        else:
            row['refused'] = 'clipboard is not a string of the toast count'
    row['text'] = text
    READS.append(row)
    return text


def load():
    raw = BOUND.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BOUND_SHA256:
        raise SystemExit('the bound runner is not the pinned bytes; re-derive, do not run')
    source = raw.decode('utf-8')
    for site, old, new in REPLACEMENTS:
        if source.count(old) != 1:
            raise SystemExit(f'{site}: the replaced text occurs {source.count(old)} times, not once')
        source = source.replace(old, new)
    if 'U\\+([0-9A-Fa-f]{4,6})' in source:
        raise SystemExit('a toast parse survived the replacements')
    module = types.ModuleType(NAME)
    module.__file__ = str(BOUND)
    module._clipboard_text = _clipboard_text
    sys.modules[NAME] = module
    exec(compile(source, str(BOUND), 'exec'), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--browser', choices=('chrome', 'firefox'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    if 'run_e2_c_product_path' in sys.modules:
        raise SystemExit('runner imported before the manifest override')
    override = {'default': _bundle.MANIFEST.as_posix(), 'used': 'e2/editor-shell-v2-bundle-v80.json'}
    _bundle.MANIFEST = Path(override['used'])
    pp = load()
    override['runnerShellBundle'] = pp.SHELL_BUNDLE_V2.relative_to(pp.PROJECT).as_posix()
    override['derivedFrom'] = {'path': str(BOUND.relative_to(pp.PROJECT.parent)), 'sha256': BOUND_SHA256,
                               'replacedSites': [site for site, _, _ in REPLACEMENTS]}
    (args.out / 'shell-manifest-override.json').write_text(json.dumps(override, indent=1) + '\n')
    if override['runnerShellBundle'] != override['used']:
        raise SystemExit('the runner did not take the generation-80 override')
    sys.argv = [f'tools/{NAME}.py', '--browser', args.browser, '--out', str(args.out / 'report.json')]
    try:
        return pp.main()
    finally:
        (args.out / 'clipboard-reads.json').write_text(json.dumps(READS, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
