import json, sys, time, subprocess, secrets
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
from check_m3_locks import LockChrome, Server, login, open_from_files, NAME
from check_m3_skeleton_open import Instance, DEFAULT_DDEV
from run_e2_c_page_smoke import navigate
from r7_support import evaluate
inst = Instance(DEFAULT_DDEV); srv = Server(inst, [])
SETUP = """(() => {
  const n = __NONCE__;
  addEventListener('beforeunload', () => { navigator.sendBeacon('/status.php?ev=bu-' + n, 'x'); });
  addEventListener('pagehide', () => { navigator.sendBeacon('/status.php?ev=ph-' + n, 'x'); });
  addEventListener('pagehide', () => { fetch('/status.php?ev=phfetch-' + n, { method: 'POST', body: 'x', keepalive: true }); });
  return true; })()"""
for i in range(3):
    srv.clear_locks(); srv.upload(srv.admin, NAME)
    nonce = secrets.token_hex(5)
    s = LockChrome("cold"); rec = {}
    try:
        login(s, inst.base, "admin", inst.password)
        open_from_files(s, inst.base, "", NAME, rec)
        evaluate(s, SETUP.replace("__NONCE__", json.dumps(nonce)))
        before = srv.props(srv.admin, NAME)["lock"]
        s.drain()
        navigate(s, inst.base + "/apps/files/", timeout=120)
        time.sleep(4)
        ev = s.drain()
        failed = [e["params"].get("errorText") for e in ev if e["method"] == "Network.loadingFailed"]
        log = subprocess.run(["ddev", "exec", f"grep -o 'ev=[a-z]*-{nonce}' /var/log/apache2/access.log"], cwd=DEFAULT_DDEV, capture_output=True, text=True).stdout.split()
        print({"i": i, "hostLock": rec["host"].get("lock", {}).get("state"), "lockBefore": before, "lockAfter": srv.props(srv.admin, NAME)["lock"],
               "arrived": sorted(x.split("=")[1].split("-")[0] for x in log), "failed": failed}, flush=True)
    finally:
        s.close()
srv.clear_locks(); srv.upload(srv.admin, NAME)
