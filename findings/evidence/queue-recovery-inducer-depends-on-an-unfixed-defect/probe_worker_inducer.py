"""Can a REAL worker failure be induced from outside the product?

`queue-recovery-inducer-depends-on-an-unfixed-defect`: the only route into
recoverable-error today is finding 038 staying broken, and on the accessibility
core it no longer reproduces -- so the recovery path is uncovered there.

This asks one question before any of it is wired into the net: can CDP reach the
document worker's own global and make it throw, and does the product then enter
recovery the way it does for a real crash?  An uncaught error in a worker fires
the `error` event on the main thread's Worker object, which is exactly what
`DocumentSdk._handleCrash` listens for -- so this is the real failure class,
induced from outside the product rather than simulated inside it.
"""
import json, subprocess, sys, time
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page                       # noqa: E402
from run_browser_probe import (ChromeSession, free_port, wait_http,  # noqa: E402
                               websocket_connect)


class BrowserEndpoint:
    """A second CDP connection, to the BROWSER rather than to the page.

    Measured 2026-08-27, and it is what the discriminator found: from the
    page-scoped websocket, `Target.attachToTarget` returns a sessionId and then
    NOTHING addressed to it is ever answered -- not even `Runtime.enable`, which
    the browser answers rather than the target's JavaScript thread. So the
    silence was not eight blocked worker threads (my hypothesis); it was a
    connection that cannot carry sessions for other targets at all.
    """

    def __init__(self, base_url: str):
        version = wait_http(f"{base_url}/json/version")
        self.websocket = websocket_connect(version["webSocketDebuggerUrl"],
                                           origin="http://127.0.0.1")
        self.next_id = 0

    def call(self, method, params=None, timeout=20, session_id=None):
        self.next_id += 1
        message = {"id": self.next_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        self.websocket.send(json.dumps(message))
        while True:
            response = json.loads(self.websocket.recv(timeout=timeout))
            if response.get("id") != self.next_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})
from run_e2_c_page_smoke import READ_STATE, navigate              # noqa: E402

port = free_port()
server = subprocess.Popen(
    [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
     "--root", str(PROJECT / "dist")],
    cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
report = {"port": port}
session = None
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = ChromeSession("cold")
    navigate(session, base)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE) or {}
        if state.get("state") == "ready":
            break
        time.sleep(0.5)
    report["stateWhenReady"] = state

    browser = BrowserEndpoint(session.base_url)
    targets = browser.call("Target.getTargets").get("targetInfos", [])
    report["targets"] = [{"type": t["type"], "url": t["url"][-60:]} for t in targets]
    # The URLs come back EMPTY: the verified loader builds the worker from a
    # blob, and the wasm's pthreads each occupy a target of their own. So the
    # document worker has to be identified by what it IS, not by where it came
    # from -- attach to each and ask.
    fingerprints = []
    for t in targets:
        if t["type"] != "worker":
            continue
        try:
            sid = browser.call("Target.attachToTarget",
                              {"targetId": t["targetId"], "flatten": True}
                              ).get("sessionId")
            # A SHORT TIMEOUT IS THE DISCRIMINATOR, not just politeness.  The
            # wasm's pthread workers sit in Atomics.wait, so their event loop
            # never runs and Runtime.evaluate never returns.  The DOCUMENT
            # worker is idle-but-responsive -- it is waiting on messages.  So
            # the one that answers within a few seconds is the one we want.
            # DISCRIMINATOR: `Runtime.enable` is answered by the BROWSER, not
            # by the worker's JavaScript thread. If it returns and `evaluate`
            # times out, the attach is fine and the thread is blocked. If it
            # times out too, the problem is mine.
            enabled = None
            try:
                browser.call("Runtime.enable", {}, timeout=4, session_id=sid)
                enabled = True
            except Exception as error:                 # noqa: BLE001
                enabled = f"{type(error).__name__}"
            fingerprints.append({"targetId": t["targetId"][:8],
                                 "runtimeEnable": enabled})
            got = browser.call("Runtime.evaluate", timeout=4, params={
                "expression": """(() => ({
  name: self.name || null,
  href: (self.location && self.location.href || "").slice(-70),
  hasOnMessage: typeof self.onmessage,
  hasModule: typeof Module,
  hasCcall: typeof ccall,
  keys: Object.getOwnPropertyNames(self).filter(
    (k) => /oxsdk|editor|document|manifest|handle/i.test(k)).slice(0, 8),
})) ()""",
                "returnByValue": True}, session_id=sid).get("result", {})
            fingerprints.append({"targetId": t["targetId"][:8],
                                 "value": got.get("value")})
        except Exception as error:                     # noqa: BLE001
            fingerprints.append({"targetId": t["targetId"][:8],
                                 "error": f"{type(error).__name__}: {error}"})
    report["workerFingerprints"] = fingerprints
    worker = None
    report["workerFound"] = bool(worker)
    if worker:
        attached = session.call("Target.attachToTarget",
                                {"targetId": worker["targetId"], "flatten": True})
        sid = attached.get("sessionId")
        report["sessionId"] = bool(sid)
        # A REAL uncaught error inside the worker, not a synthetic event on the
        # main thread: this is the thing the browser reports and the SDK listens
        # for.  setTimeout so the evaluate itself still returns.
        session.call("Runtime.evaluate",
                     {"expression": "setTimeout(() => { throw new Error("
                                    "'induced worker failure'); }, 0); true",
                      "returnByValue": True}, session_id=sid)
        seen = []
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = evaluate(session, READ_STATE) or {}
            seen.append(state.get("state"))
            if state.get("state") in ("recoverable-error", "restart-required"):
                break
            time.sleep(0.5)
        report["statesAfterThrow"] = [s for i, s in enumerate(seen)
                                      if i == 0 or s != seen[i - 1]]
        report["finalState"] = state.get("state")
        report["checkpoint"] = state.get("checkpoint")
        report["toast"] = state.get("toast")
        report["notice"] = evaluate(session, """(() => {
const n = document.querySelector('#notice');
const a = document.querySelector('#notice-action');
return { shown: n ? n.dataset.show : null, rescue: n ? n.dataset.rescue : null,
         text: document.querySelector('#notice-text')?.textContent || null,
         action: a ? a.textContent : null, disabled: a ? a.disabled : null };
})()""")
finally:
    if session is not None:
        try: session.close()
        except Exception: pass
    server.terminate()
print(json.dumps(report, indent=2, ensure_ascii=False))
