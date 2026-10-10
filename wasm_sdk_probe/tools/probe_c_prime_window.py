#!/usr/bin/env python3
"""C3 and C4 of release C′ (SPEC-M3-production-ui §17.4 as amended by §17.9 (c), §17.11): are the bands in the
canvas's window current once the page is quiet, and after a scroll to the middle and the end of the document?

"Current" is asked twice, of two observers, and both must say yes:

  the page   `#canvas` `data-bands` -- each band in the window listed with a label equal to `data-changes`
             (the page's change counter; §17.11 names the attributes);
  the probe  a shim in the served HTML (no product byte changes) that records, for every `render` request the
             page posts to its document Worker, the page's counter at that moment, and ties each fresh
             `ImageData` to the request it answered; every full-band `putImageData` and full-width
             `clearRect` is logged with the window at that moment.  A band is current when the LAST of those
             events at its rows, under the present window, is a put of an image ASKED FOR at the present
             counter.  This is what catches a page that relabels old pixels: its `data-bands` say current, the
             image it put back was asked for before the change.

C3  owner document, the caret at the top (`End` of the first line), the arm's edits, then quiet (state ready,
    nothing pending, 0.5 s; then 1 s): every band in the window current; every band the page lists is in the
    window.  Recorded: `wholeWindowCurrentAfterLastKeyMs`, from the last key to the first moment every band of
    the final window had a put asked for at the final counter or later.
C4  (`--c4`) first the window is sent to 0.5 and 1.0 of the document and back to the top (so a page that kept
    bands outside its window would have them), then C3's edits, then the desk is scrolled to 0.5 and to 1.0:
    within 500 ms of each scroll every band in the window current.  The time is measured on the page's clock,
    from the scroll to the event that made the last band current; the probe polls for up to 3 s.

Arms (§17.9 (c): typing is not the only edit that can leave a stale band):
  typing     20 letters, 80 ms apart
  backspace  20 letters, then 10 Backspace, 80 ms apart
  bold       20 letters, 3 ArrowLeft (the caret inside the word), the toolbar's bold

  probe_c_prime_window.py --browser chrome --dpr 2 --window 1400x1000 --arm typing [--c4] [--page FILE] --out R.json

`--page` serves another page in place of dist's (the red cases); the report carries its sha256.  Exit 0 when
every judged cell passes, 1 when one fails, 2 when the run could not judge (no window, no shim log).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import probe_111_overtake as p111  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

HERE = TOOLS.parent
DIST = HERE / "dist"
OWNER = HERE / "build" / "scratch-m3-production-ui" / "PMPC指南.odt"
CLICK = ("0.5", "0.010373")          # the counted typing probe's place on the owner document
SHIM = """<script>
(() => {
  // probe_c_prime_window.py: which change each band's pixels were asked for after.  DOM, not page globals:
  // Firefox evaluates in a sandbox.
  const root = document.documentElement;
  const canvas = () => document.querySelector('#canvas');
  const counter = () => Number(canvas()?.dataset.changes ?? NaN);
  const top = () => Number((canvas()?.dataset.window || '').split(' ')[1] ?? NaN);
  const asked = new Map();               // requestId -> { t, changes }
  let answered = null;                   // the request whose pixels the next ImageData holds
  const images = new WeakMap();          // ImageData -> { changes, born }
  const log = [];                        // [t, kind, canvasRow, rows, winTop, changes]
  const keep = () => { if (log.length > 6000) log.splice(0, 2000); root.dataset.cpw = JSON.stringify(log); };
  const NativeWorker = window.Worker;
  window.Worker = class extends NativeWorker {
    constructor(...args) {
      super(...args);
      this.addEventListener("message", (e) => {
        const d = e.data;
        if (d && d.kind === "response" && asked.has(d.requestId)) {
          answered = d.ok && d.result && d.result.pixels ? asked.get(d.requestId) : null;
          asked.delete(d.requestId);
        }
      });
    }
    postMessage(message, ...rest) {
      // DocumentHandle.render() posts operation "paint" (sdk/document-sdk.js render()).
      if (message && message.kind === "request" && message.operation === "paint")
        asked.set(message.requestId, { t: performance.now(), changes: counter() });
      return super.postMessage(message, ...rest);
    }
  };
  const NativeImageData = window.ImageData;
  window.ImageData = class extends NativeImageData {
    constructor(...args) {
      super(...args);
      if (answered) images.set(this, { changes: answered.changes, born: performance.now() });
      answered = null;
    }
  };
  const proto = CanvasRenderingContext2D.prototype, put = proto.putImageData, clear = proto.clearRect;
  const now = () => Math.round(performance.now() * 10) / 10;
  proto.putImageData = function (image, dx, dy, ...rest) {
    const tag = images.get(image);
    if (rest.length === 0 && tag) { log.push([now(), 'put', dy, image.height, top(), tag.changes]); keep(); }
    return put.call(this, image, dx, dy, ...rest);
  };
  proto.clearRect = function (x, y, w, h) {
    if (x === 0 && w === this.canvas.width) { log.push([now(), 'clear', y, h, top(), null]); keep(); }
    return clear.call(this, x, y, w, h);
  };
  root.dataset.cpwInstalled = '1';
})();
</script>"""
READ = """(() => { const c = document.querySelector('#canvas'), d = document.documentElement.dataset;
  // The document rows the desk shows now, as the page's visibleDocRows() measures them.
  const paper = document.querySelector('#paper').getBoundingClientRect();
  const desk = document.querySelector('#desk').getBoundingClientRect();
  const doc = Number((c.dataset.window || '').split(' ')[0]);
  const rows = paper.height ? doc / paper.height : 0;
  const view = [Math.floor((Math.max(desk.top, paper.top) - paper.top) * rows),
                Math.ceil((Math.min(desk.bottom, paper.bottom) - paper.top) * rows)];
  return { window: c.dataset.window ?? null, changes: c.dataset.changes ?? null, bands: c.dataset.bands ?? null,
           installed: d.cpwInstalled === '1', log: JSON.parse(d.cpw || '[]'), now: performance.now(), view }; })()"""
SCROLL = """(() => { const desk = document.querySelector('#desk');
  desk.scrollTop = ARG_F * (desk.scrollHeight - desk.clientHeight);
  return { t: performance.now(), scrollTop: desk.scrollTop }; })()"""
BAND = 1023                          # the page's RENDER_BAND_HEIGHT (floor(32767 / 32))


def bands_of(doc_rows: int) -> list[tuple[int, int, int]]:
    """renderBands() of the page: (index, top, rows), the last piece under half a band joined to the one above."""
    out, top = [], 0
    while top < doc_rows:
        out.append([len(out), top, min(BAND, doc_rows - top)])
        top += BAND
    if len(out) > 1 and out[-1][2] < BAND / 2:
        out[-2][2] += out.pop()[2]
    return [tuple(b) for b in out]


def judge(read: dict, since: float | None = None) -> dict:
    """Is every band in the window current, by the page's labels and by the probe's own log?"""
    parts = (read.get("window") or "").split()
    if len(parts) != 3 or read.get("changes") in (None, ""):
        return {"judged": False, "why": "no data-window / data-changes on #canvas"}
    if not read.get("installed"):
        return {"judged": False, "why": "the shim did not run"}
    doc, win, rows = (int(v) for v in parts)
    last = int(read["changes"])
    inside = [b for b in bands_of(doc) if b[1] < win + rows and b[1] + b[2] > win]
    listed = {}
    for item in (read.get("bands") or "").split():
        i, t, r, label = (int(v) for v in item.split(":"))
        listed[i] = (t, r, label)
    page_ok = all(b[0] in listed and listed[b[0]][2] == last for b in inside)
    stray = sorted(i for i, (t, r, _) in listed.items() if not (t < win + rows and t + r > win))
    probe = {}
    for band in inside:
        events = [e for e in read["log"] if e[4] == win and e[2] + win == band[1]]
        latest = events[-1] if events else None
        probe[band[0]] = {"latest": latest,
                          "current": bool(latest and latest[1] == "put" and latest[5] is not None and latest[5] >= last)}
    probe_ok = all(v["current"] for v in probe.values())
    # The window must hold what the desk shows NOW: right after a scroll the page's scroll handler may not have
    # run yet, and the old window, still current, is not an answer about the new place (codex review, C4).
    view = read.get("view") or [win, win]
    covers = win <= view[0] and view[1] <= win + rows
    # When did the window become current: the latest of the events that made each band current.
    when = None
    if probe_ok:
        when = max(probe[b[0]]["latest"][0] for b in inside)
    return {"judged": True, "docRows": doc, "winTop": win, "rows": rows, "changes": last,
            "inWindow": [b[0] for b in inside], "pageSaysCurrent": page_ok, "probeSeesCurrent": probe_ok,
            "listedOutsideWindow": stray, "view": view, "windowCoversView": covers,
            "current": page_ok and probe_ok and not stray and covers,
            "currentAtMs": when, "sinceMs": None if (when is None or since is None) else round(when - since, 1),
            "bands": {str(k): v for k, v in probe.items()}, "listed": {str(k): v for k, v in listed.items()}}


def whole_window_after(read: dict, last_key: float) -> float | None:
    """From the last key to the first moment every band of the final window had a put asked for at the final counter."""
    parts = (read.get("window") or "").split()
    if len(parts) != 3:
        return None
    doc, win, rows = (int(v) for v in parts)
    final = int(read["changes"])
    need = {b[1] for b in bands_of(doc) if b[1] < win + rows and b[1] + b[2] > win}
    for e in read["log"]:
        if e[0] >= last_key and e[1] == "put" and e[4] == win and e[5] is not None and e[5] >= final:
            need.discard(e[2] + win)
            if not need:
                return round(e[0] - last_key, 1)
    return None


def shift_left(session, browser: str, n: int) -> None:
    if browser == "chrome":
        for _ in range(n):
            for t in ("rawKeyDown", "keyUp"):
                session.call("Input.dispatchKeyEvent", {"type": t, "key": "ArrowLeft", "code": "ArrowLeft",
                                                        "windowsVirtualKeyCode": 37, "nativeVirtualKeyCode": 37})
            time.sleep(0.08)
        return
    actions = []
    for _ in range(n):
        actions += [{"type": "keyDown", "value": ""}, {"type": "keyUp", "value": ""},
                    {"type": "pause", "duration": 80}]
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")


def wait_current(session, since: float, limit: float = 3.0) -> tuple[dict, dict]:
    deadline = time.monotonic() + limit
    while True:
        read = pp.evaluate(session, READ)
        verdict = judge(read, since)
        if verdict.get("current") or time.monotonic() > deadline:
            return read, verdict
        time.sleep(0.02)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--dpr", type=float, default=2.0)
    ap.add_argument("--window", default="1400x1000")
    ap.add_argument("--arm", choices=("typing", "backspace", "bold"), required=True)
    ap.add_argument("--c4", action="store_true")
    ap.add_argument("--page", type=Path, default=DIST / "e2-editor-app.js")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    width, height = (int(v) for v in a.window.split("x"))
    os.environ["MOZ_HEADLESS_WIDTH"] = str(round(width * a.dpr))
    os.environ["MOZ_HEADLESS_HEIGHT"] = str(round(height * a.dpr))
    html = (DIST / "e2-editor.html").read_text(encoding="utf-8")
    anchor = '<script type="module" src="./e2-editor-app.js"></script>'
    if html.count(anchor) != 1:
        raise SystemExit("the page's module script is not where the shim expects it")
    page = a.page.read_bytes()
    mirror = Path(tempfile.mkdtemp(prefix="cpw-")) / "root"
    pp.build_mirror(DIST, mirror, {"e2-editor.html": html.replace(anchor, SHIM + anchor).encode("utf-8"),
                                   "e2-editor-app.js": page})
    (mirror / "doc.odt").write_bytes(OWNER.read_bytes())
    report = {"probe": "probe_c_prime_window.py", "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "browser": a.browser, "dpr": a.dpr, "window": [width, height], "arm": a.arm, "c4": a.c4,
              "page": hashlib.sha256(page).hexdigest(), "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port), "--root", str(mirror)],
                              cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    code = 2
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        if a.browser == "chrome":
            session = pp.ChromeSession("cold")
            session.call("Emulation.setDeviceMetricsOverride",
                         {"width": width, "height": height, "deviceScaleFactor": a.dpr, "mobile": False})
        else:
            session = pp.FirefoxSession("cold", extra_prefs={"layout.css.devPixelsPerPx": str(a.dpr)})
        report["version"] = getattr(session, "version", None)
        pp.navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.INSTALL)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./doc.odt").replace("ARG_NAME", "doc.odt"))
        pp.wait_for(session, lambda s: (s.get("doc") or "") == "doc.odt" and s.get("state") == "ready", 180)
        p111.quiet(session)
        report["opened"] = judge(wait_current(session, None, 10)[0])
        if a.c4:
            report["prefetch"] = []
            for f in ("0.5", "1.0", "0"):
                s = pp.evaluate(session, SCROLL.replace("ARG_F", f))
                read, verdict = wait_current(session, s["t"], 10)
                report["prefetch"].append({"to": f, **{k: verdict.get(k) for k in ("winTop", "current", "sinceMs")}})
        before = (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")
        pp.evaluate(session, pp.POINT_AT.replace("ARG_X", CLICK[0]).replace("ARG_Y", CLICK[1]))
        pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before, 30)
        p111.quiet(session)
        p111.burst(session, a.browser, ["End"], 0)
        p111.quiet(session)
        time.sleep(1.0)
        pp.evaluate(session, p111.KEYLOG)
        letters = [chr(ord("a") + i % 26) for i in range(20)]
        p111.burst(session, a.browser, letters, 80)
        if a.arm == "backspace":
            time.sleep(0.08)
            p111.burst(session, a.browser, ["Backspace"] * 10, 80)
        elif a.arm == "bold":
            p111.quiet(session, 60)
            shift_left(session, a.browser, 3)
            p111.quiet(session, 60)
            pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "set-bold"))
        time.sleep(1.0)
        report["quiet"] = p111.quiet(session, 60)
        time.sleep(1.0)
        keys = pp.evaluate(session, p111.READ_KEYLOG) or []
        last_key = max((t for _, t in keys), default=None)
        read = pp.evaluate(session, READ)
        report["keys"] = len(keys)
        report["c3"] = judge(read)
        report["c3"]["wholeWindowCurrentAfterLastKeyMs"] = None if last_key is None else whole_window_after(read, last_key)
        report["boldApplied"] = (pp.evaluate(session, pp.FORMAT_BUTTON_STATE.replace("ARG_ACTION", "set-bold"))
                                 if a.arm == "bold" else None)
        cells = [report["c3"]]
        if a.c4:
            report["c4"] = []
            for f in ("0.5", "1.0"):
                s = pp.evaluate(session, SCROLL.replace("ARG_F", f))
                read, verdict = wait_current(session, s["t"], 3.0)
                verdict["scrollTop"] = s["scrollTop"]
                verdict["withinMs"] = 500
                verdict["pass"] = bool(verdict.get("current") and verdict.get("sinceMs") is not None
                                       and verdict["sinceMs"] <= 500)
                report["c4"].append({"to": f, **verdict})
                cells.append({"judged": verdict.get("judged"), "current": verdict["pass"]})
        judged = all(c.get("judged") for c in cells)
        code = 2 if not judged else (0 if all(c.get("current") for c in cells) else 1)
        report["verdict"] = {0: "PASS", 1: "FAIL", 2: "NOT_JUDGED"}[code]
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if session is not None:
            try:
                session.close()
            except Exception as error:  # noqa: BLE001
                report["closeError"] = str(error)
        server.terminate()
        server.wait(timeout=10)
        a.out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    summary = {"verdict": report.get("verdict"), "c3": {k: report.get("c3", {}).get(k) for k in
               ("current", "pageSaysCurrent", "probeSeesCurrent", "wholeWindowCurrentAfterLastKeyMs")},
               "c4": [{k: c.get(k) for k in ("to", "pass", "sinceMs", "pageSaysCurrent", "probeSeesCurrent")}
                      for c in report.get("c4", [])]}
    print(json.dumps(summary, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
