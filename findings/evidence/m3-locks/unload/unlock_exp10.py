import json, sys, time, subprocess, secrets, urllib.parse
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
from check_m3_locks import LockChrome, Server, login, open_from_files, NAME
from check_m3_skeleton_open import Instance, DEFAULT_DDEV
from run_e2_c_page_smoke import navigate
from r7_support import evaluate
inst = Instance(DEFAULT_DDEV); srv = Server(inst, [])
dav = '/remote.php/dav/files/admin/' + urllib.parse.quote(NAME)
UNLOCK = "fetch(__DAV__, { method: 'UNLOCK', keepalive: true, credentials: 'same-origin', headers: { requesttoken: document.head.dataset.requesttoken, 'X-Requested-With': 'XMLHttpRequest', 'Lock-Token': __TOK__ } }).catch(() => {})"
VARIANTS = {
    "V0 host only": "",
    "V1 +bu beacon": "addEventListener('beforeunload', () => { navigator.sendBeacon('/status.php?ev=x-' + __N__, 'x'); });",
    "V2 +ph beacon": "addEventListener('pagehide', () => { navigator.sendBeacon('/status.php?ev=x-' + __N__, 'x'); });",
    "V3 +ph UNLOCK": "addEventListener('pagehide', () => { " + UNLOCK + "; });",
    "V4 +bu UNLOCK": "addEventListener('beforeunload', () => { " + UNLOCK + "; });",
}
results = {}
for label, code in VARIANTS.items():
    for i in range(4):
        srv.clear_locks(); srv.upload(srv.admin, NAME)
        n = secrets.token_hex(5)
        s = LockChrome("cold"); rec = {}
        try:
            login(s, inst.base, "admin", inst.password)
            open_from_files(s, inst.base, "", NAME, rec)
            tok = srv.props(srv.admin, NAME)["token"]
            js = code.replace("__DAV__", json.dumps(dav)).replace("__TOK__", json.dumps(f"<{tok}>")).replace("__N__", json.dumps(n))
            if js:
                evaluate(s, "(() => { " + js + " return true; })()")
            before = srv.props(srv.admin, NAME)["lock"]
            navigate(s, inst.base + "/apps/files/", timeout=120)
            time.sleep(4)
            after = srv.props(srv.admin, NAME)["lock"]
            results.setdefault(label, []).append(after == "" and before == "1")
            print({"v": label, "i": i, "before": before, "after": after}, flush=True)
        finally:
            s.close()
print({k: f"{sum(v)}/{len(v)}" for k, v in results.items()})
srv.clear_locks(); srv.upload(srv.admin, NAME)
