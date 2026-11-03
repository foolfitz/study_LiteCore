#!/usr/bin/env python3
"""F3-89 (SPEC-P-ms-formats step 4): the bound product-path runner on frozen generation 89, with the engine's copied text read
from the clipboard, one press per format arm, and the clear's toast waited for (finding 178).

Derived from tools/run_v88_f3_clipboard.py (bound by F3-88's evidence; not edited).  The differences are a closed
list: this paragraph and the two lines above it; the shell manifest rebound to generation 89 (the `used` value and
its refusal message); the module name.  Everything below is that file's text.

F3-88 (SPEC-P-demo-batch-5): the bound product-path runner on frozen generation 88, with the engine's copied text read
from the clipboard, one press per format arm, and the clear's toast waited for (finding 178).

Derived from tools/run_v87_f3_clipboard.py (bound by F3-87's evidence; not edited).  The differences are a closed
list: this paragraph and the two lines above it; the shell manifest rebound to generation 88 (the `used` value and
its refusal message); the module name.  Everything below is that file's text.

F3-87 (SPEC-P-demo-batch-4 section 5): the bound product-path runner on frozen generation 87, with the engine's
copied text read from the clipboard, one press per format arm, and the clear's toast waited for (finding 178).

Derived from tools/run_v86_f3_clipboard.py (bound by F3-86's evidence; not edited).  The differences are a closed
list: this paragraph and the two lines above it; the shell manifest rebound to generation 87 (the `used` value and
its refusal message); the module name; REPLACEMENTS gains finding 178's wait on the toast, the same edit as
findings/evidence/demo-batch-3/f3-86/diag_clear_wait.py.  Everything below is that file's text.

F3-86 (SPEC-P-demo-batch-3 section 3): the bound product-path runner on frozen generation 86, with the engine's
copied text read from the clipboard, and one press per format arm (finding 178).

Derived from tools/run_v85_f3_clipboard.py (bound by F3-85's evidence; not edited).  The differences are a closed
list: this paragraph and the two lines above it; the shell manifest rebound to generation 86 (the `used` value and
its refusal message); the module name.  Everything below is that file's text.

F3-85 (SPEC-P-demo-batch-3 section 2): the bound product-path runner on frozen generation 85, with the engine's
copied text read from the clipboard, and one press per format arm (finding 178).

Derived from tools/run_v84_f3_clipboard.py (bound by F3-84's evidence; not edited).  The differences are a closed
list: this paragraph and the two lines above it; the shell manifest rebound to generation 85 (the `used` value and
its refusal message); the module name.  Everything below is that file's text.

F3-84 (SPEC-P-demo-batch-1 section 3): the bound product-path runner on frozen generation 84, with the engine's
copied text read from the clipboard, and one press per format arm (finding 178).

Derived from tools/run_v83_f3_clipboard.py (bound by F3-83's evidence; not edited).  The differences are a closed
list: this paragraph and the two lines above it; the shell manifest rebound to generation 84 (the `used` value and
its refusal message); the module name; REPLACEMENTS gains finding 178's removal of the first press, the same edit as
findings/evidence/v29-177/f3-83/diag_single_press.py.  Everything below is that file's text.

F3-83 (SPEC-M3-v29-tick-pacing section 6 T3): the bound product-path runner on frozen generation 83, with the
engine's copied text read from the clipboard.

Derived from tools/run_v82_f3_clipboard.py (bound by F3-82's evidence, findings/evidence/v28-083/f3-82/; not
edited).  The differences are a closed list: this paragraph and the two lines above it; the shell manifest
rebound to generation 83 instead of 82 (the `used` value and its refusal message); the module name.
BOUND_SHA256, REPLACEMENTS and `_clipboard_text` are unchanged.  Everything below is that file's text.

F3-82 (SPEC-M3-v28-last-line-fallback 7.3): the bound product-path runner on frozen generation 82, with the
engine's copied text read from the clipboard.

Derived from tools/run_v81_f3_clipboard.py (bound by F3-81's evidence, findings/evidence/v27-176/f3-81/; not
edited).  The differences are a closed list: this paragraph and the two lines above it; the shell manifest
rebound to generation 82 instead of 81 (the `used` value and its refusal message); the module name.
BOUND_SHA256, REPLACEMENTS and `_clipboard_text` are unchanged.  Everything below is that file's text.

F3-81 (SPEC-M3-v27-finding-176 7.3): the bound product-path runner on frozen generation 81, with the engine's
copied text read from the clipboard.

Derived from tools/run_e2_c_product_path_clipboard.py (bound by F3-80's evidence,
findings/evidence/select-all-v26/f3-clipboard/; not edited).  The differences are a closed list: this paragraph and
the two lines above it; the shell manifest rebound to generation 81 instead of 80 (the `used` value and its
refusal message); the module name.  BOUND_SHA256, REPLACEMENTS and `_clipboard_text` are unchanged.  Everything
below is that file's text.

W-f3-text-observable (SPEC-M3-select-all-v26 append 2; fable ruling B modified, 3.6): the bound product-path
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
NAME = 'run_v89_f3_clipboard'
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

# Finding 178: the bound `format_arm` presses each format button twice.  Removed here, as diag_single_press.py did for F3-83.
_TAIL = '                "return b ? !b.disabled : null; })()")\n'
_PRESS = '            evaluate(session, PRESS.replace("ARG_ACTION", action))\n'
_NEXT = '            # WAIT ON THE COMPLETION SIGNAL, AND RECORD THE STATE CACHE.\n'
REPLACEMENTS = REPLACEMENTS + (("single-press", _TAIL + _PRESS + _NEXT, _TAIL + _NEXT),)

# Finding 178's append: the wait on the 清除格式 label is met by the first of the clear's four steps, so the runner can press into the page's own
# loop.  The toast 「已清除…」 is written once, after the fourth.  The same edit as findings/evidence/demo-batch-3/f3-86/diag_clear_wait.py.
_LABEL = 'lambda st: "清除格式" in (st.get("latency") or ""), 30)'
_DONE = 'lambda st: "已清除" in (evaluate(session, READ_TOAST) or ""), 30)'
REPLACEMENTS = REPLACEMENTS + (
    ("clear-wait-normalise",
     '                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + _LABEL,
     '                evaluate(session, CLEAR_TOAST)\n                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + _DONE),
    ("clear-wait-accumulate",
     '        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + _LABEL,
     '        evaluate(session, CLEAR_TOAST)\n        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + _DONE),
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
    override = {'default': _bundle.MANIFEST.as_posix(), 'used': 'e2/editor-shell-v2-bundle-v89.json'}
    _bundle.MANIFEST = Path(override['used'])
    pp = load()
    override['runnerShellBundle'] = pp.SHELL_BUNDLE_V2.relative_to(pp.PROJECT).as_posix()
    override['derivedFrom'] = {'path': str(BOUND.relative_to(pp.PROJECT.parent)), 'sha256': BOUND_SHA256,
                               'replacedSites': [site for site, _, _ in REPLACEMENTS]}
    (args.out / 'shell-manifest-override.json').write_text(json.dumps(override, indent=1) + '\n')
    if override['runnerShellBundle'] != override['used']:
        raise SystemExit('the runner did not take the generation-89 override')
    sys.argv = [f'tools/{NAME}.py', '--browser', args.browser, '--out', str(args.out / 'report.json')]
    try:
        return pp.main()
    finally:
        (args.out / 'clipboard-reads.json').write_text(json.dumps(READS, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
