"""F3 on a frozen generation (--generation N, e2/generations/generation-NN.json): the bound product-path runner with the
engine's copied text read from the clipboard, one press per format arm, and the clear's toast waited for (finding 178).

One tool for every generation from 90 on (CLAUDE.md, the section on cadence, item 2), in place of the per-generation
copies tools/run_v81..v89_f3_clipboard.py (kept, each bound by its own evidence).  run_v89_f3_clipboard.py's text with
two changes: the shell manifest is the generation's bundle; the bound runner's sha256 is recorded, not pinned (the
cadence rule binds reports to what ran) -- each replacement still has to occur exactly once, which is what keeps an
edited runner from being run half-patched.

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

  python3 tools/run_f3_clipboard.py --generation N --browser chrome --out <new dir>

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
NAME = 'run_f3_clipboard'
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
    return module, hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('--browser', choices=('chrome', 'firefox'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    if 'run_e2_c_product_path' in sys.modules:
        raise SystemExit('runner imported before the manifest override')
    from four_arms_identity import Generation
    gen = Generation(args.generation)
    override = {'default': _bundle.MANIFEST.as_posix(), 'used': gen.bundle, 'generation': gen.number,
                'generationFileSha256': gen.file_sha256,
                'tool': {'path': 'wasm_sdk_probe/tools/run_f3_clipboard.py', 'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         'argv': sys.argv[1:]}}
    _bundle.MANIFEST = Path(override['used'])
    pp, bound_sha256 = load()
    override['runnerShellBundle'] = pp.SHELL_BUNDLE_V2.relative_to(pp.PROJECT).as_posix()
    override['derivedFrom'] = {'path': str(BOUND.relative_to(pp.PROJECT.parent)), 'sha256': bound_sha256,
                               'replacedSites': [site for site, _, _ in REPLACEMENTS]}
    (args.out / 'shell-manifest-override.json').write_text(json.dumps(override, indent=1) + '\n')
    if override['runnerShellBundle'] != override['used']:
        raise SystemExit(f'the runner did not take the generation-{gen.number} override')
    sys.argv = [f'tools/{NAME}.py', '--browser', args.browser, '--out', str(args.out / 'report.json')]
    try:
        return pp.main()
    finally:
        (args.out / 'clipboard-reads.json').write_text(json.dumps(READS, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
