"""Development diagnostic (not evidence): which non-loopback hosts a proxied headless Chrome contacts while the
page is loaded and idle, with a given extra flag set."""
import json, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
import run_v21_shakedown_item2 as run
from run_v21_shakedown_item2 import common, v20, obs2, hook, net
extra = sys.argv[1:]
net.QUIET_CHROME = tuple(net.QUIET_CHROME) + tuple(extra)
pop = json.loads(run.POPULATION.read_text(encoding="utf-8"))
scratch = Path(tempfile.mkdtemp(prefix="v21-diagq-"))
proxy = net.LoggingProxy()
with common.browser_lock("diag_quiet item2", wait_s=3600):
    ident = common.build_mirror(scratch / "m", snippets=[v20.OBSERVER, obs2.SNIPPET, hook.SNIPPET], extra_files=run.mirror_files(pop))
    with common.served(Path(ident["mirror"])) as base:
        s = run.open_browser("chrome", proxy_port=proxy.port)
        try:
            ctx = run.Ctx(s, "chrome", base, scratch, ident)
            for _ in range(3):
                ctx.load(); ctx.open(run.EMPTY); time.sleep(25)
        finally:
            common.close_browser(s)
hosts = {}
for e in proxy.entries():
    if e.get("host") not in ("127.0.0.1", "localhost"):
        k = f"{e.get('host')}:{e.get('port')}"; hosts[k] = hosts.get(k, 0) + 1
proxy.close()
print(json.dumps({"extra": extra, "hosts": hosts}))
