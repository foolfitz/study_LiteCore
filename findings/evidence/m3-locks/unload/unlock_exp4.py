import json, sys, time, urllib.parse, subprocess, secrets, tempfile
from pathlib import Path
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
from check_m3_locks import LockChrome, Server, login, NAME, PROJECT
from check_m3_skeleton_open import Instance, DEFAULT_DDEV
from probe_m3_gate0_coep import firefox_profile, wait_until
from run_browser_probe import FirefoxSession
from run_e2_c_page_smoke import navigate
from r7_support import evaluate
inst = Instance(DEFAULT_DDEV); srv = Server(inst, [])
dav = '/remote.php/dav/files/admin/' + urllib.parse.quote(NAME)
SETUP = """(() => { window.__r = null;
  const h = { requesttoken: document.head.dataset.requesttoken, 'X-Requested-With': 'XMLHttpRequest' };
  fetch(__DAVURL__, { method: 'LOCK', credentials: 'same-origin', body: '<?xml version="1.0"?><d:lockinfo xmlns:d="DAV:"><d:lockscope><d:exclusive/></d:lockscope><d:locktype><d:write/></d:locktype></d:lockinfo>', headers: { ...h, 'Content-Type': 'application/xml', Timeout: 'Second-300' } })
  .then((r) => { const tok = r.headers.get('lock-token');
    window.addEventListener('pagehide', () => {
      if (__VARIANT__ === 'beacon') navigator.sendBeacon('/status.php?beacon=__NONCE__', new URLSearchParams({ t: tok }));
      else fetch(__DAVURL__, { method: 'UNLOCK', keepalive: true, credentials: 'same-origin', headers: { ...h, 'Lock-Token': tok } }).catch(() => {});
    });
    window.__r = r.status; });
  return true; })()"""
def access_has(nonce):
    out = subprocess.run(["ddev", "exec", f"grep -c 'beacon={nonce}' /var/log/apache2/access.log"], cwd=DEFAULT_DDEV, capture_output=True, text=True).stdout.strip()
    return out
with tempfile.TemporaryDirectory(dir=PROJECT / "build") as scratch:
    for kind in ("chrome", "firefox"):
        for variant in ("beacon", "unlock"):
            if kind == "chrome" and variant == "unlock":
                continue  # measured: 0/4 (exp3)
            for i in range(4):
                srv.clear_locks(); srv.upload(srv.admin, NAME)
                nonce = secrets.token_hex(6)
                s = LockChrome("cold") if kind == "chrome" else FirefoxSession("cold", profile_dir=firefox_profile(Path(scratch) / f"ff{i}{variant}"))
                try:
                    login(s, inst.base, "admin", inst.password)
                    navigate(s, inst.base + "/apps/files/", timeout=120)
                    evaluate(s, SETUP.replace("__DAVURL__", json.dumps(dav)).replace("__VARIANT__", json.dumps(variant)).replace("__NONCE__", nonce))
                    st = wait_until(s, "(() => window.__r)()", 20)
                    before = srv.props(srv.admin, NAME)["lock"]
                    navigate(s, inst.base + "/apps/files/?after=1", timeout=120)
                    time.sleep(5)
                    print({"browser": kind, "variant": variant, "i": i, "lock": st, "before": before,
                           "after": srv.props(srv.admin, NAME)["lock"], "beaconSeen": access_has(nonce) if variant == "beacon" else None}, flush=True)
                finally:
                    s.close()
srv.clear_locks()
