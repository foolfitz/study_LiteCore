import json, sys, time, subprocess, secrets
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
from check_m3_locks import LockChrome, Server, login
from check_m3_skeleton_open import Instance, DEFAULT_DDEV
from run_e2_c_page_smoke import navigate
from r7_support import evaluate
inst = Instance(DEFAULT_DDEV)
SETUP = """(() => {
  const n = __NONCE__;
  addEventListener('beforeunload', () => { navigator.sendBeacon('/status.php?ev=bu-' + n, 'x'); });
  addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') navigator.sendBeacon('/status.php?ev=vc-' + n, 'x'); });
  addEventListener('pagehide', () => { navigator.sendBeacon('/status.php?ev=ph-' + n, 'x'); });
  addEventListener('pagehide', () => { fetch('/status.php?ev=phfetch-' + n, { method: 'POST', body: 'x', keepalive: true }); });
  return true; })()"""
for how in ("Page.navigate", "location.href"):
    for i in range(3):
        nonce = secrets.token_hex(5)
        s = LockChrome("cold")
        try:
            login(s, inst.base, "admin", inst.password)
            navigate(s, inst.base + "/apps/files/", timeout=120)
            evaluate(s, SETUP.replace("__NONCE__", json.dumps(nonce)))
            if how == "Page.navigate":
                navigate(s, inst.base + "/apps/files/?after=2", timeout=120)
            else:
                s.call("Runtime.evaluate", {"expression": "location.href = '/apps/files/?after=2'; true"})
            time.sleep(4)
            log = subprocess.run(["ddev", "exec", f"grep -o 'ev=[a-z]*-{nonce}' /var/log/apache2/access.log"], cwd=DEFAULT_DDEV, capture_output=True, text=True).stdout.split()
            print({"how": how, "i": i, "arrived": sorted(x.split("=")[1].split("-")[0] for x in log)}, flush=True)
        finally:
            s.close()
