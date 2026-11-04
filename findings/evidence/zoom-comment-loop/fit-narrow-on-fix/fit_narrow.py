"""Diagnostic (not evidence): open l1 at the fit in a narrow window on the dist mirror, record the paint replies. No zoom press.
  python3 -I fit_narrow.py <repo> <mirror-root> <out-dir> <document> <zoom_host2.py path> W H [W H ...]
"""
import base64, json, sys, time, traceback
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve(); MIRROR = Path(sys.argv[2]).resolve(); OUT = Path(sys.argv[3]).resolve(); DOC = Path(sys.argv[4]).resolve()
SRC = Path(sys.argv[5]).read_text(); SIZES = [(int(sys.argv[i]), int(sys.argv[i + 1])) for i in range(6, len(sys.argv), 2)]
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
OBSERVER = SRC.split('OBSERVER = r"""', 1)[1].split('"""', 1)[0]
STATE = SRC.split('STATE = """', 1)[1].split('"""', 1)[0]
def wait(session, pred, limit):
    until = time.monotonic() + limit
    while time.monotonic() < until:
        st = evaluate(session, STATE)
        if pred(st): return st
        time.sleep(0.3)
    return None
report = {'mirror': str(MIRROR), 'doc': DOC.name, 'runs': []}
with common.served(MIRROR) as base:
    for (W, H) in SIZES:
        rec = {'window': [W, H]}; report['runs'].append(rec)
        session = common.open_browser('chrome', (W, H))
        try:
            session.call('Page.enable'); session.call('Page.addScriptToEvaluateOnNewDocument', {'source': OBSERVER})
            navigate(session, base)
            rec['pageReady'] = bool(wait(session, lambda s: s['pill'] == 'ready', 240))
            evaluate(session, pp.OPEN_BYTES.replace('ARG_B64', base64.b64encode(DOC.read_bytes()).decode()).replace('ARG_NAME', DOC.name))
            time.sleep(3); wait(session, lambda s: s['pill'] == 'ready', 120); time.sleep(6)
            rec['state'] = evaluate(session, STATE)
            (OUT / f'fit-{W}x{H}.png').write_bytes(session.screenshot())
            rec['observer'] = evaluate(session, "(() => window.__zd ? {paints: window.__zd.paints.map(({at, ...r}) => ({t: Math.round(at), ...r})), toasts: window.__zd.toasts, errors: window.__zd.errors} : null)()")
        except Exception:  # noqa: BLE001
            rec['fatal'] = traceback.format_exc()
        finally:
            common.close_browser(session)
(OUT / 'fit-narrow-report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False))
for rec in report['runs']:
    st = rec.get('state') or {}; c = st.get('canvas') or {}
    ps = [p for p in (rec.get('observer') or {}).get('paints', []) if p.get('label') == st.get('label')]
    print('window', rec['window'], 'label', st.get('label'), 'desk', (st.get('desk') or {}).get('client'), 'paper', (st.get('paper') or {}).get('css'),
          'canvas', c.get('w'), c.get('h'), 'ink', c.get('ink'), 'bands', repr(c.get('bands')), 'paints', len(ps),
          'changed', sum(1 for p in ps if (p.get('res') or {}).get('changed')), 'cw', sorted({p['cw'] for p in ps}), 'dw', sorted({(p.get('res') or {}).get('dw') for p in ps}),
          'fatal', (rec.get('fatal') or '')[-300:])
