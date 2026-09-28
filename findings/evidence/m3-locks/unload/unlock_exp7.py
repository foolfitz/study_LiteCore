import json, sys, time, urllib.parse, subprocess, secrets, tempfile
from pathlib import Path
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
from check_m3_locks import LockChrome, Server, login, NAME, PROJECT
from check_m3_skeleton_open import Instance, DEFAULT_DDEV
from probe_m3_gate0_coep import firefox_profile, wait_until
from run_browser_probe import FirefoxSession, free_port, wait_http
import run_browser_probe as rbp, os, shutil

class HeadfulChrome(LockChrome):
    """LockChrome's launch without --headless, on an Xvfb display."""
    def __init__(self, cache_mode):
        self.events = []
        self.profile = tempfile.TemporaryDirectory(prefix="m3-headful-")
        self.profile_dir = Path(self.profile.name)
        self.port = free_port()
        env = {**os.environ, "DISPLAY": ":97"}
        env.pop("WAYLAND_DISPLAY", None)
        self.process = subprocess.Popen([shutil.which("google-chrome"), f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*", f"--user-data-dir={self.profile_dir}", "--no-first-run",
            "--no-default-browser-check", "--ozone-platform=x11", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.version = wait_http(f"{self.base_url}/json/version").get("Browser")
        page = next(t for t in wait_http(f"{self.base_url}/json/list") if t["type"] == "page")
        self.websocket = rbp.websocket_connect(page["webSocketDebuggerUrl"], origin="http://127.0.0.1")
        self.next_id = 0
        for m in ("Page.enable", "Runtime.enable", "Network.enable"):
            self.call(m)

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
    for kind in ("chrome",):
        for variant in ("beacon", "unlock"):
            for i in range(4):
                srv.clear_locks(); srv.upload(srv.admin, NAME)
                nonce = secrets.token_hex(6)
                s = HeadfulChrome("cold") if kind == "chrome" else FirefoxSession("cold", profile_dir=firefox_profile(Path(scratch) / f"ff{i}{variant}"))
                try:
                    login(s, inst.base, "admin", inst.password)
                    navigate(s, inst.base + "/apps/files/", timeout=120)
                    evaluate(s, SETUP.replace("__DAVURL__", json.dumps(dav)).replace("__VARIANT__", json.dumps(variant)).replace("__NONCE__", nonce))
                    st = wait_until(s, "(() => window.__r)()", 20)
                    before = srv.props(srv.admin, NAME)["lock"]
                    evaluate(s, "(() => { setTimeout(() => { location.href = '/apps/files/?after=1'; }, 1500); return true; })()")
                    s.websocket.close()   # no DevTools session attached while the page unloads
                    time.sleep(7)
                    print({"browser": kind + " HEADFUL detached " + str(s.version), "variant": variant, "i": i, "lock": st, "before": before,
                           "after": srv.props(srv.admin, NAME)["lock"], "beaconSeen": access_has(nonce) if variant == "beacon" else None}, flush=True)
                finally:
                    s.close()
srv.clear_locks()
