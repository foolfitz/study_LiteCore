#!/usr/bin/env python3
"""The icon toolbar on the served page, by real pointer, both browsers.  dist/ is not written.

  check_toolbar.py --browser chrome|firefox --out DIR

Holds iff, on one fresh page with a document open:
  sameText     every #toolbar button's textContent, order and action equal the page before the change (git, TEXT_COMMIT)
  sameName     Chrome: each visible button's accessible name equals that text (Accessibility.getFullAXTree)
  iconsDrawn   every visible button has one svg, 20 x 20, whose <use> resolves to a symbol with a non-empty box
  textHidden   every visible button's label is clipped (1 x 1 at most), and redo / paste-markdown obey `hidden` as the page sets it
  noTipAtRest  before any hover the tooltip of the probe button is not visible
  tipOnHover   real pointer over the Bold icon, 500 ms: ::after visible, opacity 1, content == data-tip
  tipLeaves    pointer away, 300 ms: hidden again
  clickIcon    real click on the Bold icon flips aria-pressed from the state at rest and writes the strip 「B N ms」; a second click flips it back
  tipsOnScreen each visible button's tooltip box, forced on, is inside the viewport
Screenshots: DIR/{BROWSER}-rest.png, -hover.png.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3] / "wasm_sdk_probe"
sys.path.insert(0, str(ROOT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402

TEXT_COMMIT = "4c863081d"   # the page before the icons
READ = """(() => [...document.querySelectorAll('#toolbar button')].map((b) => { const s = b.querySelector('svg.ic'), u = s && s.querySelector('use'),
  r = b.getBoundingClientRect(), i = s ? s.getBoundingClientRect() : null, l = b.querySelector('.lbl'), lr = l ? l.getBoundingClientRect() : null,
  sym = u ? document.querySelector(u.getAttribute('href')) : null, box = u ? u.getBoundingClientRect() : null;
  return { action: b.dataset.action || b.id, text: b.textContent.trim(), hidden: b.hidden, visible: r.width > 0, width: r.width, height: r.height, tip: b.dataset.tip,
           x: r.left + r.width / 2, y: r.top + r.height / 2, iconW: i ? i.width : null, iconH: i ? i.height : null, symbol: !!sym, useW: box ? box.width : null,
           labelW: lr ? lr.width : null, labelH: lr ? lr.height : null }; }))()"""
TIP = """(() => { const b = document.querySelector('#toolbar button[data-action="set-bold"]'), s = getComputedStyle(b, '::after');
  return { visibility: s.visibility, opacity: s.opacity, content: s.content, tip: b.dataset.tip, pressed: b.getAttribute('aria-pressed'),
           latency: document.querySelector('#s-latency')?.textContent }; })()"""
FORCE = """(() => { const st = document.createElement('style'); st.id = '__force'; st.textContent = '.toolbar button[data-tip]::after{opacity:1!important;visibility:visible!important;transition:none!important}';
  document.head.append(st); const w = innerWidth; const out = [...document.querySelectorAll('#toolbar button')].filter((b) => b.getBoundingClientRect().width > 0).map((b) => {
    const s = getComputedStyle(b, '::after'), r = b.getBoundingClientRect(), tw = parseFloat(s.width) + parseFloat(s.paddingLeft) + parseFloat(s.paddingRight);
    const left = b.classList.contains('tip-start') ? r.left : b.classList.contains('tip-end') ? r.right - tw : r.left + r.width / 2 - tw / 2;
    return { action: b.dataset.action || b.id, left, right: left + tw, inside: left >= 0 && left + tw <= w }; }); st.remove(); return out; })()"""


def before_texts():
    raw = subprocess.check_output(["git", "-C", str(ROOT.parent), "show", f"{TEXT_COMMIT}:wasm_sdk_probe/web/e2-editor.html"], text=True)
    bar = raw[raw.index('id="toolbar"'):raw.index('id="desk"')]
    rows = []
    for attrs, text in re.findall(r"<button ([^>]*)>([^<]*)</button>", bar):
        key = re.search(r'data-action="([^"]+)"', attrs) or re.search(r'id="([^"]+)"', attrs)
        rows.append((key.group(1), text.strip()))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    mirror = Path(tempfile.mkdtemp(prefix="toolbar-", dir=str(ROOT / "build"))) / "root"
    pp.build_mirror(ROOT / "dist", mirror, {})
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(ROOT / "web/serve.py"), "--port", str(port), "--root", str(mirror)], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session, out = None, {"browser": a.browser, "clauses": {}}
    c = out["clauses"]
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = common.open_browser(a.browser, (1400, 1000))
        pp.navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.INSTALL)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./e1-fixtures/list-contexts.odt").replace("ARG_NAME", "list-contexts.odt"))
        pp.wait_for(session, lambda s: (s.get("doc") or "") == "list-contexts.odt" and s.get("state") == "ready", 180)
        time.sleep(1.0)
        clicks = pp.caret_click_fractions(pp.evaluate(session, pp.LINE_INK.replace("ARG_Y", "0.24")) or {})
        pp.place_caret_and_settle(session, pp.POINT_AT, clicks["near"], "0.24")
        time.sleep(0.5)
        rows = pp.evaluate(session, READ)
        out["buttons"] = rows
        c["sameText"] = [(r["action"], r["text"]) for r in rows] == before_texts()
        visible = [r for r in rows if r["visible"]]
        c["iconsDrawn"] = bool(visible) and all(r["iconW"] == 20 and r["iconH"] == 20 and r["symbol"] and (r["useW"] or 0) > 0 for r in visible)
        c["textHidden"] = all((r["labelW"] or 9) <= 1 and (r["labelH"] or 9) <= 1 for r in visible) and all(not r["visible"] for r in rows if r["hidden"])
        c["uniformSize"] = len({(r["width"], r["height"]) for r in visible}) == 1
        if a.browser == "chrome":
            tree = session.call("Accessibility.getFullAXTree")["nodes"]
            names = {(n.get("name") or {}).get("value") for n in tree if (n.get("role") or {}).get("value") == "button"}
            missing = [r["text"] for r in visible if r["text"] not in names]
            out["axMissing"] = missing
            c["sameName"] = not missing
        rest = pp.evaluate(session, TIP)
        out["rest"] = rest
        c["noTipAtRest"] = rest["visibility"] == "hidden"
        (a.out / f"{a.browser}-rest.png").write_bytes(session.screenshot())
        bold = next(r for r in rows if r["action"] == "set-bold")
        if a.browser == "chrome":
            real._cdp_mouse(session, "mouseMoved", bold["x"], bold["y"], 0)
        else:
            real._wd_pointer(session, [{"type": "pointerMove", "x": int(bold["x"]), "y": int(bold["y"]), "origin": "viewport"}])
        time.sleep(0.6)
        hover = pp.evaluate(session, TIP)
        out["hover"] = hover
        c["tipOnHover"] = hover["visibility"] == "visible" and float(hover["opacity"]) == 1 and hover["content"].strip('"') == hover["tip"]
        (a.out / f"{a.browser}-hover.png").write_bytes(session.screenshot())
        if a.browser == "chrome":
            real._cdp_mouse(session, "mouseMoved", 700, 600, 0)
        else:
            real._wd_pointer(session, [{"type": "pointerMove", "x": 700, "y": 600, "origin": "viewport"}])
        time.sleep(0.4)
        away = pp.evaluate(session, TIP)
        out["away"] = away
        c["tipLeaves"] = away["visibility"] == "hidden"
        states = []
        for _ in range(2):
            pp.evaluate(session, pp.CLEAR_LATENCY)
            real.click(session, a.browser, bold["x"], bold["y"])
            time.sleep(1.0)
            s = pp.evaluate(session, TIP)
            states.append((s["pressed"], s["latency"]))
        out["clicks"] = states
        # Against the state the caret was in: Firefox's metrics put the click on a bold line (`rest.pressed` true), Chrome's do not.
        start = rest["pressed"] == "true"
        c["clickIcon"] = states[0][0] == str(not start).lower() and states[1][0] == str(start).lower() \
            and all(re.match(r"^B \d+ ms$", s[1] or "") for s in states)
        tips = pp.evaluate(session, FORCE)
        out["tips"] = tips
        c["tipsOnScreen"] = bool(tips) and all(t["inside"] for t in tips)
    finally:
        if session is not None:
            common.close_browser(session)
        server.terminate(); server.wait(timeout=10)
    out["holds"] = bool(c) and all(c.values())
    (a.out / f"{a.browser}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(a.browser, "HOLDS" if out["holds"] else "RED", c)
    return 0 if out["holds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
