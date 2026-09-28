import json, sys, time, urllib.parse
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
from check_m3_locks import LockChrome, Server, login, NAME
from check_m3_skeleton_open import Instance, DEFAULT_DDEV
from run_e2_c_page_smoke import navigate
inst = Instance(DEFAULT_DDEV); srv = Server(inst, [])
dav = '/remote.php/dav/files/admin/' + urllib.parse.quote(NAME)
SETUP = """(async () => {
  const h = { requesttoken: document.head.dataset.requesttoken, 'X-Requested-With': 'XMLHttpRequest' };
  const r = await fetch(__DAVURL__, { method: 'LOCK', credentials: 'same-origin', body: '<?xml version="1.0"?><d:lockinfo xmlns:d="DAV:"><d:lockscope><d:exclusive/></d:lockscope><d:locktype><d:write/></d:locktype></d:lockinfo>', headers: { ...h, 'Content-Type': 'application/xml', Timeout: 'Second-300' } });
  const tok = r.headers.get('lock-token');
  window.addEventListener('pagehide', () => {
    if (__EXTRA__) { fetch('/status.php?ka=get', { keepalive: true }).catch(() => {}); }
    fetch(__DAVURL__, { method: 'UNLOCK', keepalive: true, credentials: 'same-origin', headers: { ...h, 'Lock-Token': tok } }).catch(() => {});
  });
  return r.status;
})()"""
for extra in ("false", "true"):
    for i in range(4):
        srv.clear_locks(); srv.upload(srv.admin, NAME)
        s = LockChrome("cold")
        try:
            login(s, inst.base, "admin", inst.password)
            navigate(s, inst.base + "/apps/files/", timeout=120)
            st = s.call("Runtime.evaluate", {"expression": SETUP.replace("__DAVURL__", json.dumps(dav)).replace("__EXTRA__", extra), "awaitPromise": True, "returnByValue": True})["result"]["value"]
            before = srv.props(srv.admin, NAME)["lock"]
            navigate(s, inst.base + "/apps/files/?after=1", timeout=120)
            time.sleep(5)
            print({"extra": extra, "i": i, "lockStatus": st, "before": before, "after": srv.props(srv.admin, NAME)["lock"]}, flush=True)
        finally:
            s.close()
srv.clear_locks()
