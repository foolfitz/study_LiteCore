#!/usr/bin/env python3
"""SPEC-M3-production-ui §17.11: on the P page, is #paper's box #canvas's box?

The port's only real change on the P page is that pointing multiplies #paper's
box instead of #canvas's.  This reads both boxes on the served page (dist/),
both browsers, the default window, after the open and after a second fixture;
Chrome also at devicePixelRatio 1.5 and 2.  And it runs the ported readers once
each so a reader that returned a Promise, or threw, on the P page is seen here.

Not a counted run.  Prints one JSON object; exit 0 when every box pair is equal
and no ported reader returned a windowWait or an error.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[5] / "wasm_sdk_probe" / "tools"
sys.path.insert(0, str(TOOLS))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PROJECT, READ_STATE, navigate, wait_for  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

BOXES = """(() => {
const r = (s) => { const b = document.querySelector(s).getBoundingClientRect();
  return [b.left, b.top, b.width, b.height]; };
const c = document.querySelector('#canvas');
return { paper: r('#paper'), canvas: r('#canvas'), backing: [c.width, c.height],
         window: c.dataset.window ?? null, dpr: globalThis.devicePixelRatio };
})()"""


def readers(session) -> dict:
    out = {}
    for name, src in (("TOP_INK", pp.TOP_INK), ("LINE_INK", pp.LINE_INK.replace("ARG_Y", "0.28")),
                      ("CARET_COLUMNS", pp.CARET_COLUMNS.replace("ARG_Y", "0.28")),
                      ("INK_ROWS", pp.INK_ROWS.replace("ARG_EXCLUDE_CARET", "true")),
                      ("GEOMETRY", pp.GEOMETRY)):
        try:
            value = evaluate(session, src)
            out[name] = {"type": type(value).__name__,
                         "windowWait": (value or {}).get("windowWait"),
                         "height": (value or {}).get("height"),
                         "available": (value or {}).get("available")}
        except Exception as error:  # noqa: BLE001 -- recorded
            out[name] = {"error": f"{type(error).__name__}: {error}"}
    return out


def one(browser: str, base: str) -> dict:
    session = (ChromeSession if browser == "chrome" else FirefoxSession)("cold")
    record: dict = {"browser": browser, "reads": []}
    try:
        navigate(session, base)
        state = wait_for(session, lambda s: s.get("state") == "ready", 300)
        record["boot"] = (state or {}).get("state")
        time.sleep(2)
        record["reads"].append({"when": "after-open", **evaluate(session, BOXES)})
        record["readers"] = readers(session)
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        caret = wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        record["placeCaret"] = (caret or {}).get("latency")
        if browser == "chrome":
            for ratio in (1.5, 2):
                pp.set_device_pixel_ratio(session, ratio)
                session.evaluate("(() => { window.dispatchEvent(new Event('resize')); return true; })()")
                time.sleep(3)
                record["reads"].append({"when": f"dpr-{ratio}", **evaluate(session, BOXES)})
            pp.set_device_pixel_ratio(session, 1)
        switched = evaluate(session, pp.SWITCH_FIXTURE)
        wait_for(session, lambda s: s.get("state") == "ready", 300)
        time.sleep(3)
        record["reads"].append({"when": f"fixture-{(switched or {}).get('to')}", **evaluate(session, BOXES)})
    finally:
        session.close()
    return record


def main() -> int:
    port = free_port()
    server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
                              cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        results = [one(b, base) for b in ("chrome", "firefox")]
    finally:
        server.terminate()
    equal = all(r["paper"] == r["canvas"] and r["window"] is None for x in results for r in x["reads"])
    clean = all("error" not in v and v.get("windowWait") is None and v.get("type") == "dict"
                for x in results for v in x.get("readers", {}).values())
    print(json.dumps({"boxesEqual": equal, "readersSynchronousAndClean": clean, "results": results},
                     ensure_ascii=False, indent=1))
    return 0 if equal and clean else 1


if __name__ == "__main__":
    sys.exit(main())
