#!/usr/bin/env python3
"""T4 (SPEC-M3-v29-tick-pacing section 6, section 11): does any worker's JS heap grow with typing?

The unchanged typing probe, Chrome only.  p111.burst is wrapped in process: the long burst is cut into ten chunks with a
heap sample (HeapProfiler.collectGarbage, then Runtime.getHeapUsage, per worker) before the first and after each.  dist/ is
not written.

  heap_during_typing.py run subject OUT.json   the tree's page (v29), no patch
  heap_during_typing.py run red OUT.json       v28 with the stock immediate (diag_tick.py's `immediate`), page repointed in
                                               the mirror: finding 177's leak, the arm that says this instrument can see one
  heap_during_typing.py read SUBJECT.json RED.json    exit 0 iff T4 holds
  heap_during_typing.py --self-test SUBJECT.json RED.json

Reached how: `Target.setAutoAttach` from the page, then from each worker session, twice (run_e2_c_product_path.py and
probe_proxy_trace.py record why). A pthread parked in Atomics.wait never answers CDP: it is recorded as `noAnswer`, and it
has no event loop to leak on. One gap, 80 ms, for 60 s (the C2 owner gap): 700 chars.

Growth is read per worker over the eleven samples: `grows` iff last - first >= 1 MiB AND at least 8 of the 10 intervals
increased (pinned in the spec before any run).  T4 holds iff: at least one worker answered all eleven samples in
each arm, no worker grows in `subject`, and at least one grows in `red`.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4] / "wasm_sdk_probe"
sys.path.insert(0, str(ROOT / "tools"))
GAP, CHARS, CHUNKS, MIB = 80, 700, 10, 1024 * 1024
PATCH_MARKER = "var _emscripten_set_main_loop_timing=(mode,value)=>{"
RED_PROFILE, RED_JS = "e2-editor-v28", "profiles/e2-editor-v28/probe.js"


class Cdp:
    """Requests and events on the session's page socket; ChromeSession.call throws events away."""

    def __init__(self, session):
        self.s, self.attached = session, []

    def _pump(self, message):
        if message.get("method") == "Target.attachedToTarget":
            self.attached.append(message["params"])

    def rpc(self, method, params=None, sid=None, timeout=20.0):
        self.s.next_id += 1
        mid = self.s.next_id
        out = {"id": mid, "method": method, "params": params or {}}
        if sid:
            out["sessionId"] = sid
        self.s.websocket.send(json.dumps(out))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                message = json.loads(self.s.websocket.recv(timeout=0.25))
            except Exception:  # noqa: BLE001 -- a quiet socket is not an error
                continue
            self._pump(message)
            if message.get("id") == mid:
                return message
        return None

    def drain(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                self._pump(json.loads(self.s.websocket.recv(timeout=0.25)))
            except Exception:  # noqa: BLE001
                pass

    def workers(self):
        auto = {"autoAttach": True, "flatten": True, "waitForDebuggerOnStart": False}
        self.rpc("Target.setAutoAttach", auto)
        self.drain(2.0)
        walked = set()
        for _ in range(3):
            for a in list(self.attached):
                sid = a["sessionId"]
                if sid not in walked:
                    walked.add(sid)
                    self.rpc("Target.setAutoAttach", auto, sid=sid, timeout=3.0)
            self.drain(1.0)
        return [a for a in self.attached if a["targetInfo"].get("type") == "worker"]


def run(arm, out: Path) -> int:
    import probe_typing_latency as p
    pp, p111 = p.pp, p.p111
    build = pp.build_mirror
    if arm == "red":
        source = pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
        page, _, _ = pp.repointed_page(source, RED_PROFILE, p.DIST / "profiles" / RED_PROFILE / "sdk-manifest.json")
        js = (p.DIST / RED_JS).read_text(encoding="utf-8")
        if js.count(PATCH_MARKER) != 1:
            raise SystemExit("the patch marker is not in the red arm's probe.js exactly once")
        extra = {"e2-editor-app.js": page.encode("utf-8"), RED_JS: js.replace(PATCH_MARKER, PATCH_MARKER + "mode=2;value=0;").encode("utf-8")}
    elif arm == "subject":
        extra = {}
    else:
        raise SystemExit(f"unknown arm {arm}")
    pp.build_mirror = lambda src, mirror, overrides: build(src, mirror, {**overrides, **extra})
    series: dict = {"arm": arm, "samples": [], "workers": None}
    burst = p111.burst

    def sampling(session, browser, keys, gap):
        if len(keys) < CHUNKS:
            return burst(session, browser, keys, gap)
        cdp = Cdp(session)
        workers = cdp.workers()
        series["workers"] = [{"sessionId": w["sessionId"], "url": (w["targetInfo"].get("url") or "")[-60:]} for w in workers]

        def sample(label):
            row = {"label": label, "t": round(time.monotonic(), 3), "heaps": {}}
            for w in workers:
                sid = w["sessionId"]
                cdp.rpc("HeapProfiler.collectGarbage", sid=sid, timeout=4.0)
                got = cdp.rpc("Runtime.getHeapUsage", sid=sid, timeout=2.0)
                row["heaps"][sid] = (got or {}).get("result", {}).get("usedSize") if got and "result" in got else None
            series["samples"].append(row)
        sample(0)
        size = len(keys) // CHUNKS
        for n in range(CHUNKS):
            burst(session, browser, keys[n * size:(n + 1) * size if n < CHUNKS - 1 else len(keys)], gap)
            sample(n + 1)
    p111.burst = sampling
    sys.argv = ["probe_typing_latency.py", "--browser", "chrome", "--document", "boundaries", "--gap", str(GAP),
                "--chars", str(CHARS), "--out", str(out)]
    code = p.main()
    out.with_suffix(".heap.json").write_text(json.dumps(series, indent=1) + "\n")
    return code


def growth(series: dict) -> dict:
    out = {}
    for w in series.get("workers") or []:
        sid = w["sessionId"]
        xs = [s["heaps"].get(sid) for s in series["samples"]]
        if any(x is None for x in xs) or len(xs) < 3:
            out[sid] = {"answered": sum(x is not None for x in xs), "of": len(xs), "complete": False, "grows": None}
            continue
        ups = sum(b > a for a, b in zip(xs, xs[1:]))
        out[sid] = {"answered": len(xs), "of": len(xs), "complete": True, "first": xs[0], "last": xs[-1],
                    "growthBytes": xs[-1] - xs[0], "upIntervals": ups, "intervals": len(xs) - 1,
                    "grows": xs[-1] - xs[0] >= MIB and ups >= 8}
    return out


def verdict(subject: dict, red: dict) -> dict:
    s, r = growth(subject), growth(red)
    complete = {"subject": sum(1 for v in s.values() if v["complete"]), "red": sum(1 for v in r.values() if v["complete"])}
    clauses = {"subjectAnswered": complete["subject"] >= 1 and len(subject.get("samples") or []) == CHUNKS + 1,
               "redAnswered": complete["red"] >= 1 and len(red.get("samples") or []) == CHUNKS + 1,
               "subjectDoesNotGrow": not any(v["grows"] for v in s.values()),
               "redGrows": any(v["grows"] for v in r.values())}
    return {"verdict": "T4_HOLDS" if all(clauses.values()) else "T4_RED", "clauses": clauses, "subject": s, "red": r}


def main() -> int:
    mode = sys.argv[1]
    if mode == "run":
        return run(sys.argv[2], Path(sys.argv[3]))
    subject, red = (json.loads(Path(p).read_text()) for p in sys.argv[2:4])
    if mode == "read":
        result = verdict(subject, red)
        print(json.dumps(result, indent=1))
        return 0 if result["verdict"] == "T4_HOLDS" else 1
    if mode == "--self-test":
        if verdict(subject, red)["verdict"] != "T4_HOLDS":
            raise SystemExit("self-test needs inputs that hold")

        def subject_is_the_leak(a, b):
            return copy.deepcopy(b), b

        def red_is_flat(a, b):
            return a, copy.deepcopy(a)

        def no_samples(a, b):
            a = copy.deepcopy(a); a["samples"] = []; return a, b

        def silent_workers(a, b):
            a = copy.deepcopy(a)
            for s in a["samples"]:
                s["heaps"] = {k: None for k in s["heaps"]}
            return a, b
        results = {f.__name__: verdict(*f(subject, red))["verdict"] for f in (subject_is_the_leak, red_is_flat, no_samples, silent_workers)}
        red_all = all(v != "T4_HOLDS" for v in results.values())
        print(json.dumps({"selfTest": "ALL_RED" if red_all else "SOME_HELD", "results": results}))
        return 0 if red_all else 1
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
