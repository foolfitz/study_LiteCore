#!/usr/bin/env python3
"""Release C′: C1's runtime read and three of SPEC-M3-production-ui §17.4's recorded items, on the owner document.

  C1      after the document is quiet: `#canvas.height` against C1′ (§17.9 (a), `windowRows`):
          min(docRows, max(3 * floor(desk.clientHeight * scale), 4 * 1023)), scale = canvas.width / #paper's CSS
          width; and #paper's CSS height against docRows / scale (the document's height).  The same read is
          compared with the formula's two halves alone (no 3x term; no 4-band floor), so a canvas that matches
          only one of them says which.
  bytes   `lastTiles`' pixel bytes from `#canvas` `data-bands` (rows x canvas.width x 4, summed), at the top and
          after a scroll to the middle has settled.
  fling   from the top, `#desk.scrollTop` += 500 CSS px per animation frame for 20 frames (10,000 px); per frame
          the window and whether every band under the view is listed with the current label; then the time from
          the last frame until every band under the view is current (3 s cap).  The named limit, recorded.
  save    the toolbar's save on the owner document: every `#state-pill` `data-state` write and every `#state-shown`
          text with its time; the length of each `busy`, and when 「處理中」 was shown relative to its start.

No product byte is changed; dist through a mirror.  Raw numbers; nothing here is a gate.

  probe_c_prime_recorded.py --browser chrome --dpr 2 --window 1400x1000 --out R.json
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_111_overtake as p111  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
DIST = HERE / "dist"
OWNER = HERE / "build" / "scratch-m3-production-ui" / "PMPC指南.odt"
BAND = 1023
# DOM, not page globals: Firefox evaluates in a sandbox.
READ = """(() => { const c = document.querySelector('#canvas'), desk = document.querySelector('#desk'),
  paper = document.querySelector('#paper'), d = desk.getBoundingClientRect(), p = paper.getBoundingClientRect();
  const [docRows, winTop, rows] = (c.dataset.window || '0 0 0').split(' ').map(Number);
  const scale = docRows / (p.height || 1);
  const bands = (c.dataset.bands || '').split(' ').filter(Boolean).map(s => s.split(':').map(Number));
  return { canvasWidth: c.width, canvasHeight: c.height, deskClientHeight: desk.clientHeight,
    paperCssWidth: parseFloat(paper.style.width), paperCssHeight: parseFloat(paper.style.height),
    devicePixelRatio: window.devicePixelRatio, docRows, winTop, rows, changes: Number(c.dataset.changes),
    bands, view: [Math.floor((Math.max(d.top, p.top) - p.top) * scale), Math.ceil((Math.min(d.bottom, p.bottom) - p.top) * scale)],
    scrollTop: desk.scrollTop }; })()"""
FLING = """(() => { const root = document.documentElement, desk = document.querySelector('#desk');
  root.dataset.fling = '[]'; desk.scrollTop = 0; let n = 0;
  const step = () => { const r = READ_JS; r.t = performance.now(); const f = JSON.parse(root.dataset.fling);
    f.push(r); root.dataset.fling = JSON.stringify(f);
    if (n++ < 20) { desk.scrollTop += 500; requestAnimationFrame(step); } };
  requestAnimationFrame(step); return true; })()""".replace("READ_JS", READ)
STATE_LOG = """(() => { const root = document.documentElement, pill = document.querySelector('#state-pill'),
  shown = document.querySelector('#state-shown'); root.dataset.stateLog = '[]';
  const log = (what, value) => { const l = JSON.parse(root.dataset.stateLog); l.push([what, value, performance.now()]);
    root.dataset.stateLog = JSON.stringify(l); };
  new MutationObserver(() => log('pill', pill.dataset.state)).observe(pill, { attributes: true, attributeFilter: ['data-state'] });
  new MutationObserver(() => log('shown', shown.textContent)).observe(shown, { childList: true, characterData: true, subtree: true });
  return Boolean(pill && shown); })()"""
SCROLL_MIDDLE = """(() => { const desk = document.querySelector('#desk'); desk.scrollTop = (desk.scrollHeight - desk.clientHeight) / 2;
  return desk.scrollTop; })()"""


def current(r: dict) -> bool:
    """Every band under the view listed with the current label."""
    lo, hi = r["view"]
    listed = {int(b[0]): b for b in r["bands"]}
    need = range(lo // BAND, (max(lo, hi - 1)) // BAND + 1)
    return all(i in listed and listed[i][3] == r["changes"] for i in need)


def c1(r: dict) -> dict:
    scale = r["canvasWidth"] / r["paperCssWidth"]
    three = 3 * int(r["deskClientHeight"] * scale)
    formula = min(r["docRows"], max(three, 4 * BAND))
    return {"scale": scale, "expected": formula, "observed": r["canvasHeight"], "holds": r["canvasHeight"] == formula,
            "withoutThreeTimesTerm": min(r["docRows"], 4 * BAND), "withoutFourBandFloor": min(r["docRows"], three),
            "paperCssHeight": r["paperCssHeight"], "documentCssHeight": r["docRows"] / scale,
            "paperIsDocumentHeight": abs(r["paperCssHeight"] - r["docRows"] / scale) <= 1.0}


def nbytes(r: dict) -> int:
    return sum(int(b[2]) for b in r["bands"]) * r["canvasWidth"] * 4


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--dpr", type=float, default=2.0)
    ap.add_argument("--window", default="1400x1000")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    width, height = (int(v) for v in a.window.split("x"))
    os.environ["MOZ_HEADLESS_WIDTH"] = str(round(width * a.dpr))
    os.environ["MOZ_HEADLESS_HEIGHT"] = str(round(height * a.dpr))
    mirror = Path(tempfile.mkdtemp(prefix="cpr-")) / "root"
    pp.build_mirror(DIST, mirror, {})
    (mirror / "doc.odt").write_bytes(OWNER.read_bytes())
    report = {"probe": "probe_c_prime_recorded.py", "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "browser": a.browser, "dpr": a.dpr, "window": [width, height],
              "page": hashlib.sha256((DIST / "e2-editor-app.js").read_bytes()).hexdigest(),
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port), "--root", str(mirror)],
                              cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
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
        time.sleep(3.0)
        top = pp.evaluate(session, READ)
        report["c1"] = {"read": {k: v for k, v in top.items() if k != "bands"}, **c1(top)}
        report["bytes"] = {"top": {"bytes": nbytes(top), "bands": top["bands"], "current": current(top)}}
        pp.evaluate(session, SCROLL_MIDDLE)
        time.sleep(3.0)
        middle = pp.evaluate(session, READ)
        report["bytes"]["middle"] = {"bytes": nbytes(middle), "bands": middle["bands"], "winTop": middle["winTop"],
                                     "current": current(middle)}
        pp.evaluate(session, "(() => { document.querySelector('#desk').scrollTop = 0; return true; })()")
        time.sleep(3.0)
        pp.evaluate(session, FLING)
        time.sleep(2.0)
        frames = json.loads(pp.evaluate(session, "(() => document.documentElement.dataset.fling)()") or "[]")
        settled, deadline = None, time.monotonic() + 3.0
        while time.monotonic() < deadline:
            r = pp.evaluate(session, READ)
            if current(r):
                settled = pp.evaluate(session, "(() => performance.now())()")
                break
            time.sleep(0.02)
        report["fling"] = {"frames": [{"t": round(f["t"], 1), "scrollTop": f["scrollTop"], "winTop": f["winTop"],
                                       "view": f["view"], "current": current(f)} for f in frames],
                           "framesNotCurrent": sum(1 for f in frames if not current(f)), "frameCount": len(frames),
                           "currentAfterLastFrameMs": None if settled is None or not frames else round(settled - frames[-1]["t"], 1)}
        pp.evaluate(session, STATE_LOG)
        pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
        time.sleep(1.0)
        p111.quiet(session, 120)
        time.sleep(1.0)
        log = json.loads(pp.evaluate(session, "(() => document.documentElement.dataset.stateLog)()") or "[]")
        busy, start = [], None
        for what, value, t in log:
            if what == "pill" and value == "busy" and start is None:
                start = t
            elif what == "pill" and value != "busy" and start is not None:
                shown = [round(u - start, 1) for w, v, u in log if w == "shown" and v == "處理中" and start <= u <= t]
                busy.append({"ms": round(t - start, 1), "shownBusyAtMs": shown})
                start = None
        report["save"] = {"log": log, "busy": busy, "toast": pp.evaluate(session, pp.READ_TOAST)}
        report["summary"] = {"c1Holds": report["c1"]["holds"], "canvasRows": top["canvasHeight"], "expected": report["c1"]["expected"],
                             "deskClientHeight": top["deskClientHeight"], "paperIsDocumentHeight": report["c1"]["paperIsDocumentHeight"],
                             "bytesTop": report["bytes"]["top"]["bytes"], "bytesMiddle": report["bytes"]["middle"]["bytes"],
                             "flingFramesNotCurrent": f"{report['fling']['framesNotCurrent']}/{report['fling']['frameCount']}",
                             "flingCurrentAfterLastFrameMs": report["fling"]["currentAfterLastFrameMs"],
                             "saveBusy": busy}
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
    print(json.dumps(report.get("summary"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
