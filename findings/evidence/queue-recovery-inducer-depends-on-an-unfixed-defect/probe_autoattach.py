"""Reach the document worker the DOCUMENTED way: auto-attach, not attachToTarget.

Established already (findings/evidence/queue-recovery-inducer-depends-on-an-
unfixed-defect/): `Target.attachToTarget` on a worker returns a real sessionId
and then nothing addressed to it is answered -- not `Runtime.evaluate`, not
`Runtime.enable` -- from either connection, and the workers' URLs come back
empty so they cannot even be told apart.

`Target.setAutoAttach` is the documented route to a page's dedicated workers. It
differs in two ways that matter here: Chrome creates the sessions itself, and
each arrives as a `Target.attachedToTarget` EVENT carrying `targetInfo` -- so the
url is in the event even when `getTargets` reports it empty.

Both of those are things the previous attempt lacked, so this is a different
mechanism rather than the same one retried.
"""
import json, subprocess, sys, time
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import ChromeSession, free_port               # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                 # noqa: E402


class Collecting:
    """A call wrapper that KEEPS the events instead of discarding them.

    `ChromeSession.call` skips every message whose id does not match, which is
    correct for request/response and fatal here: the sessionIds this needs only
    ever arrive as events.
    """

    def __init__(self, session):
        self.session = session
        self.events = []

    def call(self, method, params=None, timeout=20, session_id=None):
        s = self.session
        s.next_id += 1
        message = {"id": s.next_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        s.websocket.send(json.dumps(message))
        while True:
            response = json.loads(s.websocket.recv(timeout=timeout))
            if "id" not in response:
                self.events.append(response)
                continue
            if response.get("id") != s.next_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})

    def drain(self, seconds=3.0):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                message = json.loads(self.session.websocket.recv(timeout=0.5))
            except Exception:                              # noqa: BLE001
                continue
            if "id" not in message:
                self.events.append(message)

    def attached(self):
        return [e for e in self.events
                if e.get("method") == "Target.attachedToTarget"]


port = free_port()
server = subprocess.Popen(
    [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
     "--root", str(PROJECT / "dist")],
    cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
report = {}
session = None
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = ChromeSession("cold")
    wrapped = Collecting(session)
    # BEFORE the page loads, so the workers are created while it is on.
    wrapped.call("Target.setAutoAttach",
                 {"autoAttach": True, "waitForDebuggerOnStart": False,
                  "flatten": True})
    # EVERY READ FROM HERE ON GOES THROUGH THE WRAPPER.
    #
    # The first version of this polled with `evaluate(session, ...)`, which uses
    # ChromeSession.call -- and that DISCARDS every message whose id does not
    # match. The workers are created during the page load, so all eight
    # `Target.attachedToTarget` events arrived inside that polling loop and were
    # thrown away before the drain ran. It reported zero attachments and the
    # attachments had all happened. Same class of defect as the one this whole
    # probe exists to characterise: the instrument dropping the thing it was
    # built to catch.
    wrapped.call("Page.navigate", {"url": base})
    deadline = time.monotonic() + 180
    state = {}
    while time.monotonic() < deadline:
        got = wrapped.call("Runtime.evaluate",
                           {"expression": READ_STATE, "returnByValue": True,
                            "awaitPromise": True}, timeout=20)
        state = got.get("result", {}).get("value") or {}
        if state.get("state") == "ready":
            break
        time.sleep(0.5)
    report["ready"] = state.get("state")
    wrapped.drain(4.0)
    report["attachedCount"] = len(wrapped.attached())
    report["attached"] = [
        {"type": e["params"]["targetInfo"]["type"],
         "url": e["params"]["targetInfo"]["url"][-70:],
         "sessionId": e["params"]["sessionId"][:8]}
        for e in wrapped.attached()]
    # Ask each attached worker who it is. A session Chrome made itself, on a
    # connection that keeps its events -- both differences from the last try.
    answers = []
    for e in wrapped.attached():
        info = e["params"]["targetInfo"]
        if info["type"] != "worker":
            continue
        sid = e["params"]["sessionId"]
        try:
            got = wrapped.call("Runtime.evaluate", timeout=5, session_id=sid,
                               params={"expression": "(() => ({ href: "
                                                     "(self.location&&self.location.href||'')"
                                                     ".slice(-60), hasModule: typeof Module }))()",
                                       "returnByValue": True})
            answers.append({"sessionId": sid[:8], "url": info["url"][-60:],
                            "value": got.get("result", {}).get("value")})
        except Exception as error:                          # noqa: BLE001
            answers.append({"sessionId": sid[:8], "url": info["url"][-60:],
                            "error": f"{type(error).__name__}"})
    report["answers"] = answers

    # THE INDUCER ITSELF.  A real uncaught error inside the document worker,
    # which is what `DocumentSdk._handleCrash` listens for -- no product change,
    # no dependence on finding 038.
    doc = next((a for a in answers
                if "sdk-worker.js" in (a.get("url") or "")
                and "error" not in a), None)
    report["documentWorker"] = bool(doc)
    if doc:
        sid = next(e["params"]["sessionId"] for e in wrapped.attached()
                   if e["params"]["targetInfo"]["url"].endswith("sdk-worker.js"))
        wrapped.call("Runtime.evaluate", timeout=10, session_id=sid, params={
            "expression": "setTimeout(() => { throw new Error("
                          "'induced worker failure'); }, 0); true",
            "returnByValue": True})
        seen = []
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            got = wrapped.call("Runtime.evaluate",
                               {"expression": READ_STATE, "returnByValue": True,
                                "awaitPromise": True}, timeout=20)
            state = got.get("result", {}).get("value") or {}
            seen.append(state.get("state"))
            if state.get("state") in ("recoverable-error", "restart-required"):
                break
            time.sleep(0.5)
        report["statesAfterThrow"] = [s for i, s in enumerate(seen)
                                      if i == 0 or s != seen[i - 1]]
        report["finalState"] = state.get("state")
        report["checkpointAfter"] = state.get("checkpoint")
        report["toastAfter"] = state.get("toast")
        got = wrapped.call("Runtime.evaluate", {"returnByValue": True,
            "expression": """(() => {
const n = document.querySelector('#notice');
const a = document.querySelector('#notice-action');
return { shown: n ? n.dataset.show : null, rescue: n ? n.dataset.rescue : null,
         text: document.querySelector('#notice-text')?.textContent || null,
         action: a ? a.textContent : null, disabled: a ? a.disabled : null };
})()"""}, timeout=20)
        report["notice"] = got.get("result", {}).get("value")
finally:
    if session is not None:
        try: session.close()
        except Exception: pass
    server.terminate()
print(json.dumps(report, indent=2, ensure_ascii=False))
