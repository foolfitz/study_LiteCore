#!/usr/bin/env python3
"""Findings 124 and 125 (owner hand test, host 0.2.11): on a long document, does the view follow the caret
when ArrowDown moves it, and how often does the state pill say 處理中 while the content does not change?

The shipped standalone page from dist/ (no product byte changed, no shim; a mirror only so the document can
be served next to it).  The owner document, caret placed inside the first body paragraph, then N real
ArrowDown presses one at a time (Chrome: CDP Input.dispatchKeyEvent; Firefox: WebDriver actions), each
followed by waiting for the page to be idle, then M typed letters as a control.  After each press: the
desk's scrollTop, the desk's and the sink's client rectangles, revision, pill.  Throughout: every pill
text change with its time (MutationObserver), every keydown with its time.

  probe_124_125_arrows.py --browser chrome --presses 40 --letters 5 [--window 1400x1000] --out REPORT.json

--window WxH (added after the first Chrome run, whose 800 x 600 default left a 139-px desk with the caret
already below it): a CSS viewport of W x H at ratio 1 -- Chrome via Emulation.setDeviceMetricsOverride before
the first navigation, Firefox via MOZ_HEADLESS_WIDTH/HEIGHT -- as the typing-latency wrapper does.
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
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
DOCUMENT = HERE / "build" / "scratch-m3-production-ui" / "PMPC指南.odt"
CLICK = ("0.5", "0.010373")   # check_m3_production_ui.IN_TEXT: the first body paragraph
WATCH = """(() => { const root = document.documentElement, pill = document.querySelector('#state-pill');
  root.dataset.pill124 = '[]'; root.dataset.keys124 = '[]';
  if (!root.dataset.watching124) {
    root.dataset.watching124 = '1';
    document.addEventListener('keydown', (e) => {
      const k = JSON.parse(root.dataset.keys124); k.push([e.key, Math.round(performance.now() * 10) / 10]);
      root.dataset.keys124 = JSON.stringify(k); }, true);
    new MutationObserver(() => { const p = JSON.parse(root.dataset.pill124);
      p.push([pill.textContent, Math.round(performance.now() * 10) / 10]); root.dataset.pill124 = JSON.stringify(p);
    }).observe(pill, { childList: true, characterData: true, subtree: true });
  }
  return true; })()"""
GEOMETRY = """(() => { const desk = document.querySelector('#desk'), sink = document.querySelector('#sink');
  const d = desk.getBoundingClientRect(), s = sink.getBoundingClientRect();
  return { scrollTop: desk.scrollTop, scrollHeight: desk.scrollHeight, deskTop: d.top, deskBottom: d.bottom,
           sinkTop: s.top, sinkBottom: s.bottom, sinkStyleTop: sink.style.top,
           sinkVisible: s.bottom > d.top && s.top < d.bottom,
           revision: document.querySelector('#s-revision').textContent,
           pill: document.querySelector('#state-pill').textContent,
           focused: document.activeElement === sink }; })()"""
READ_LOGS = """(() => { const d = document.documentElement.dataset;
  return { pill: JSON.parse(d.pill124 || '[]'), keys: JSON.parse(d.keys124 || '[]') }; })()"""


def press(session, browser: str, name: str) -> None:
    if browser == "chrome":
        if name == "ArrowDown":
            for t in ("rawKeyDown", "keyUp"):
                session.call("Input.dispatchKeyEvent", {"type": t, "key": "ArrowDown", "code": "ArrowDown",
                                                        "windowsVirtualKeyCode": 40, "nativeVirtualKeyCode": 40})
        else:
            p111.burst(session, browser, [name], 0)
        return
    value = "" if name == "ArrowDown" else name
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
        {"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}]}]})
    session.command("DELETE", "/actions")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--presses", type=int, default=40)
    ap.add_argument("--letters", type=int, default=5)
    ap.add_argument("--window", default=None)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    window = tuple(int(v) for v in a.window.split("x")) if a.window else None
    if window and a.browser == "firefox":
        os.environ["MOZ_HEADLESS_WIDTH"], os.environ["MOZ_HEADLESS_HEIGHT"] = str(window[0]), str(window[1])
    mirror = Path(tempfile.mkdtemp(prefix="arrows-")) / "root"
    pp.build_mirror(DIST, mirror, {})
    (mirror / "doc.odt").write_bytes(DOCUMENT.read_bytes())
    report = {"probe": "probe_124_125_arrows.py", "browser": a.browser, "presses": a.presses, "letters": a.letters,
              "page": hashlib.sha256((DIST / "e2-editor-app.js").read_bytes()).hexdigest(),
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "document": DOCUMENT.name, "windowRequested": window, "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port), "--root", str(mirror)],
                              cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = (pp.ChromeSession if a.browser == "chrome" else pp.FirefoxSession)("cold")
        report["version"] = getattr(session, "version", None)
        if window and a.browser == "chrome":
            session.call("Emulation.setDeviceMetricsOverride",
                         {"width": window[0], "height": window[1], "deviceScaleFactor": 1, "mobile": False})
        pp.navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.INSTALL)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./doc.odt").replace("ARG_NAME", "doc.odt"))
        pp.wait_for(session, lambda s: (s.get("doc") or "") == "doc.odt" and s.get("state") == "ready", 180)
        p111.quiet(session)
        before = (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")
        pp.evaluate(session, pp.POINT_AT.replace("ARG_X", CLICK[0]).replace("ARG_Y", CLICK[1]))
        pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before, 30)
        p111.quiet(session)
        time.sleep(1.0)
        pp.evaluate(session, WATCH)
        steps = [{"after": "start", **pp.evaluate(session, GEOMETRY)}]
        for i in range(a.presses):
            press(session, a.browser, "ArrowDown")
            time.sleep(0.3)
            steps.append({"after": f"ArrowDown {i + 1}", "quiet": p111.quiet(session).get("timedOut") is None,
                          **pp.evaluate(session, GEOMETRY)})
        for i in range(a.letters):
            press(session, a.browser, chr(ord("a") + i))
            time.sleep(0.3)
            steps.append({"after": f"letter {i + 1}", "quiet": p111.quiet(session).get("timedOut") is None,
                          **pp.evaluate(session, GEOMETRY)})
        time.sleep(1.0)
        logs = pp.evaluate(session, READ_LOGS)
        report["steps"] = steps
        report["logs"] = logs
        # Pill flashes: 處理中 runs, each closed by the next non-處理中 label.
        flashes, opened = [], None
        for label, t in logs["pill"]:
            if label == "處理中" and opened is None:
                opened = t
            elif label != "處理中" and opened is not None:
                flashes.append(round(t - opened, 1))
                opened = None
        arrows = [t for k, t in logs["keys"] if k == "ArrowDown"]
        letters_at = [t for k, t in logs["keys"] if len(k) == 1]
        first_letter = letters_at[0] if letters_at else float("inf")
        arrow_flashes = []
        opened = None
        for label, t in logs["pill"]:
            if t >= first_letter:
                break
            if label == "處理中" and opened is None:
                opened = t
            elif label != "處理中" and opened is not None:
                arrow_flashes.append(round(t - opened, 1))
                opened = None
        arrow_steps = [s for s in steps if s["after"].startswith("ArrowDown")]
        first_hidden = next((i for i, s in enumerate(arrow_steps, 1) if not s["sinkVisible"]), None)
        report["summary"] = {
            "scrollTopStart": steps[0]["scrollTop"],
            "scrollTopValuesDuringArrows": sorted({s["scrollTop"] for s in arrow_steps}),
            "firstPressWithCaretOutsideTheDesk": first_hidden,
            "pressesWithCaretOutside": sum(1 for s in arrow_steps if not s["sinkVisible"]),
            "sinkTopMoves": sorted({s["sinkStyleTop"] for s in arrow_steps}, key=lambda v: float(v.rstrip("px") or 0))[:3],
            "revisionStart": steps[0]["revision"],
            "revisionsDuringArrows": sorted({s["revision"] for s in arrow_steps}),
            "revisionAfterLetters": steps[-1]["revision"],
            "arrowKeysSeen": len(arrows), "letterKeysSeen": len(letters_at),
            "busyFlashesDuringArrows": len(arrow_flashes),
            "busyFlashMsDuringArrows": None if not arrow_flashes else {
                "min": min(arrow_flashes), "median": sorted(arrow_flashes)[len(arrow_flashes) // 2], "max": max(arrow_flashes)},
            "busyFlashesTotal": len(flashes),
            "busyFlashesDuringLetters": len(flashes) - len(arrow_flashes),
            "allStepsQuiet": all(s.get("quiet", True) for s in steps),
            "sinkFocusedThroughout": all(s["focused"] for s in steps),
        }
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
