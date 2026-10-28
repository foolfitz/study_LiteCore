#!/usr/bin/env python3
"""Enter and Shift+Enter on v24, read through text:span (fable ruling 1 Addendum 1, section 3).

The frozen product-path runner's `the-enter-key-reaches-the-document` FAILs on v24 in Chrome by a
declared instrument limit (I-enter-raw-substring: its Shift-arm oracle is the raw substring
`A<text:line-break/>B`, and v24's typed runs carry rsid spans).  The runner is byte-bound and stays
as it is; this check replays that check's own two arms on the v24 product (dist as served) with the
runner's own helpers (imported, never edited) and judges them with a span-aware oracle:

  Enter        the saved paragraph count is the baseline's + 1 and no paragraph holds both markers
  Shift+Enter  the count is unchanged and some paragraph reads `first\\nsecond`

`paragraph_texts_with_breaks` below is E1's function text, moved here verbatim (E1 itself was
reverted); its sha256 is recorded in every report.  Each repetition: a fresh browser, the product's
own document reopened as `enter-key.odt`, the runner's caret helpers, a save after the first marker
as the check does, a real CDP Enter / Shift+Enter, the saved ODTs kept, the read paragraph recorded.
An arm whose marker did not land is NOT_ESTABLISHED.  Verdict V24_ENTER_HOLDS only if every arm of
every repetition is PASS.

  python3 -I tools/check_v24_shift_enter.py --out <new dir> [--repetitions 3]
"""
import argparse
import base64
import hashlib
import inspect
import io
import json
from pathlib import Path
import sys
import time
import traceback
import zipfile
from xml.etree import ElementTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp
import v21_shakedown_common as common
from r7_support import evaluate
from run_e2_c_page_smoke import navigate
from run_v24_page_gates import preflight
from diag_v24_shift_enter import OBSERVER, STATE, BLOB, wait

ARMS = ((False, 'ENTKEYA', 'ENTKEYB'), (True, 'SHFTKEYA', 'SHFTKEYB'))
ODF_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"


def paragraph_texts_with_breaks(content: str) -> list[str]:
    """Every <text:p>/<text:h> of content.xml as its text, read THROUGH inline elements.

    E1 (findings/evidence/link-batch-v24/pre-count/bound-tool-edits.json; fable ruling 1 v24
    pre-count 2.3).  The Enter check's Shift arm asked for the raw substring
    `A<text:line-break/>B`.  v24 types through .uno:InsertText, which stamps typed runs with
    `officeooo:rsid` spans as native keyboard typing does, and a save between the two markers
    starts a second span -- so the break was in the document and the substring was not
    (t4/shift-enter-diagnostic.md).  This reads what the paragraph SAYS: text in document order,
    descending into every element, with "\\n" for each <text:line-break/>; nothing else changes.
    """
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return []

    def text_of(node) -> str:
        parts = [node.text or ""]
        for child in node:
            parts.append("\n" if child.tag == f"{{{ODF_TEXT}}}line-break" else text_of(child))
            parts.append(child.tail or "")
        return "".join(parts)

    return [text_of(node) for node in root.iter()
            if node.tag in (f"{{{ODF_TEXT}}}p", f"{{{ODF_TEXT}}}h")]


def judge(shift, first, second, paragraphs_before, after_content):
    """One arm, from the baseline's paragraph count and the after-save's content.xml."""
    texts = paragraph_texts_with_breaks(after_content)
    landed = bool(texts) and first in after_content and second in after_content
    out = {'paragraphsBefore': paragraphs_before, 'paragraphsAfter': len(texts),
           'together': any(first in t and second in t for t in texts),
           'lineBreakBetween': any(f'{first}\n{second}' in t for t in texts),
           'paragraphText': next((t for t in texts if first in t), None)}
    if not landed or paragraphs_before is None:
        return {**out, 'outcome': 'NOT_ESTABLISHED', 'why': 'a marker did not land or the baseline was not read'}
    ok = (out['paragraphsAfter'] == paragraphs_before and out['lineBreakBetween']) if shift else \
         (out['paragraphsAfter'] == paragraphs_before + 1 and not out['together'])
    return {**out, 'outcome': 'PASS' if ok else 'FAIL'}


def save_now(session):
    blobs = evaluate(session, STATE)['blobs']
    evaluate(session, pp.PRESS.replace('ARG_ACTION', 'save'))
    wait(session, lambda s: s['blobs'] > blobs, 30, 'save')
    raw = base64.b64decode(evaluate(session, BLOB))
    return raw, zipfile.ZipFile(io.BytesIO(raw)).read('content.xml').decode('utf-8')


def repetition(session, base, out, n):
    navigate(session, base)
    wait(session, lambda s: s['doc'] == 'list-contexts.odt' and s['pill'] == 'ready', 240, 'open')
    evaluate(session, pp.CLEAR_TOAST)
    evaluate(session, pp.OPEN_FILE.replace('ARG_URL', './e1-fixtures/list-contexts.odt').replace('ARG_NAME', 'enter-key.odt'))
    pp.wait_for(session, lambda s: (s.get('doc') or '') == 'enter-key.odt' and s.get('state') == 'ready', 90)
    arms = []
    for shift, first, second in ARMS:
        aim = pp.caret_click_fractions(evaluate(session, pp.LINE_INK.replace('ARG_Y', '0.24')) or {})
        pp.place_caret_and_settle(session, pp.POINT_AT, aim['near'], '0.24')
        evaluate(session, pp.PRESS.replace('ARG_ACTION', 'insert-paragraph-break')); time.sleep(1.2)
        before = pp.revision_of(evaluate(session, pp.READ_STATE))
        evaluate(session, pp.TYPE_WHEREVER_FOCUS_IS.replace('ARG_TEXT', first))
        pp.wait_for(session, lambda st, f=before: pp.revision_of(st) is not None and f is not None and pp.revision_of(st) > f, 12)
        raw0, baseline = save_now(session)
        for kind in ('rawKeyDown', 'char', 'keyUp'):
            payload = {'type': kind, 'key': 'Enter', 'windowsVirtualKeyCode': 13, 'nativeVirtualKeyCode': 13,
                       'code': 'Enter', 'modifiers': 8 if shift else 0}
            if kind == 'char': payload['text'] = '\r'
            session.call('Input.dispatchKeyEvent', payload)
        time.sleep(1.5)
        before = pp.revision_of(evaluate(session, pp.READ_STATE))
        evaluate(session, pp.TYPE_WHEREVER_FOCUS_IS.replace('ARG_TEXT', second))
        pp.wait_for(session, lambda st, f=before: pp.revision_of(st) is not None and f is not None and pp.revision_of(st) > f, 12)
        raw1, content = save_now(session)
        for tag, raw in (('baseline', raw0), ('after', raw1)):
            (out / f'r{n}-{first}-{tag}.odt').write_bytes(raw)
        arm = judge(shift, first, second, len(paragraph_texts_with_breaks(baseline)) if first in baseline else None, content)
        arms.append({'shift': shift, 'first': first, 'second': second, 'aim': {k: aim.get(k) for k in ('derived', 'near')},
                     'baselineSha256': hashlib.sha256(raw0).hexdigest(), 'afterSha256': hashlib.sha256(raw1).hexdigest(), **arm})
    return arms


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error('at least one repetition: zero repetitions would hold vacuously')
    args.out.mkdir(parents=True, exist_ok=False)
    html = common.inject((common.DIST / 'e2-editor.html').read_text(encoding='utf-8'), [OBSERVER]).encode()
    oracle = inspect.getsource(paragraph_texts_with_breaks)
    report = {'schema': 1, 'argv': sys.argv, 'preflight': preflight(),
              'oracleSha256': hashlib.sha256(oracle.encode()).hexdigest(),
              'toolSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'runnerSha256': hashlib.sha256(Path(pp.__file__).read_bytes()).hexdigest(),
              'servedHtmlSha256': hashlib.sha256(html).hexdigest(), 'repetitions': []}
    write = lambda: (args.out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    with common.browser_lock('check_v24_shift_enter'):
        report['preRun'] = common.pre_run_checks(); write()
        if report['preRun']['refuse']:
            raise SystemExit('pre-run refusal: ' + '; '.join(report['preRun']['refuse']))
        target = args.out / 'mirror'
        pp.build_mirror(common.DIST, target, {'e2-editor.html': html})
        with common.served(target) as base:
            for n in range(1, args.repetitions + 1):
                rep = {'repetition': n}; session = None
                try:
                    session = common.open_browser('chrome')
                    if getattr(session, 'call', None) is None:
                        raise RuntimeError('no CDP: a real key cannot be delivered')
                    rep['arms'] = repetition(session, base, args.out, n)
                except Exception:
                    rep['fatal'] = traceback.format_exc()
                finally:
                    if session is not None: rep['cleanup'] = common.close_browser(session)
                report['repetitions'].append(rep); write()
                for arm in rep.get('arms') or []:
                    print(f"r{n} {'Shift+Enter' if arm['shift'] else 'Enter'}: {arm['outcome']} {arm['paragraphText']!r}", file=sys.stderr, flush=True)
    outcomes = [a['outcome'] for r in report['repetitions'] for a in r.get('arms') or []]
    complete = len(outcomes) == 2 * args.repetitions and not any(r.get('fatal') for r in report['repetitions'])
    report['verdict'] = 'V24_ENTER_HOLDS' if complete and all(o == 'PASS' for o in outcomes) else \
        'V24_ENTER_FAILS' if 'FAIL' in outcomes else 'NOT_ESTABLISHED'
    write(); print(report['verdict'])
    return 0 if report['verdict'] == 'V24_ENTER_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
