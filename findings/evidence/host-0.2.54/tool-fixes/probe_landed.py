import importlib.util, json, sys, tempfile
from pathlib import Path
EV = Path('/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.54')
spec = importlib.util.spec_from_file_location('hb6', EV / 'host_batch6.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
s, h = m.s, m.h
h.OUT = Path(sys.argv[1]); h.OUT.mkdir(parents=True, exist_ok=True)
m.FOLDER = 'LiteCore-probe-landed'
inst = s.Instance(m.HOST)
try: inst.dav('DELETE', m.FOLDER)
except Exception: pass
inst.dav('MKCOL', m.FOLDER)
out = {}
with tempfile.TemporaryDirectory(dir=m.SDK / 'build') as scratch:
    session = s.EventChrome('cold')
    try:
        s.browser_login(session, inst.base, inst.password)
        seen, landed, ready = m.upload_and_open(session, 'chrome', inst, m.FIXTURE_ODS, 'probe.ods', m.CALC_ROUTE, m.CALC_READY, Path(scratch))
        out['returned'] = {'seen': seen, 'landed': landed, 'ready': ready}
        out['location'] = s.evaluate(session, "({href: location.href, pathname: location.pathname, top: window === window.top})")
        out['predicate'] = s.evaluate(session, f"(() => location.pathname.endsWith({json.dumps(m.CALC_ROUTE)}) && location.href)()")
        out['wait_until_now'] = s.wait_until(session, f"(() => location.pathname.endsWith({json.dumps(m.CALC_ROUTE)}) && location.href)()", 5)
    finally:
        session.close()
inst.dav('DELETE', m.FOLDER)
print(json.dumps(out, indent=1, ensure_ascii=False))
