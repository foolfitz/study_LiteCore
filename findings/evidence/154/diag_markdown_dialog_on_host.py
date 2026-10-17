#!/usr/bin/env python3
"""Finding 154's diagnostic: on host 0.2.25, is the closed Markdown dialog displayed, and is it what the click hits?

Opens one long60 copy through the host's own route (login, Files -> open; the D2 host arm's route), then reads, in
this order:
  1. the dialog: `open`, computed `display`/`position`, its box, and the stylesheet rules that set `display` on it;
  2. the paste-markdown button (item 2's entry, which the shell hides): `hidden` and computed `display`;
  3. what `elementFromPoint` returns at the D2 arm's first-line point;
  4. a real click there: does the page ask the engine to place the caret (the latency label 「定位游標」)?
Then the counterfactual, on the same page: one style rule `#markdown-dialog:not([open]) { display: none }`, and 1-4
again.  A screenshot before and after (Chrome).  Diagnostic, not evidence for any criterion.

  python3 findings/evidence/154/diag_markdown_dialog_on_host.py --browser chrome --out findings/evidence/154
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "wasm_sdk_probe" / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import run_v21_d2 as d2  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402

READ = r"""(() => {
  const d = document.getElementById('markdown-dialog');
  const b = document.querySelector('button[data-action="paste-markdown"]');
  const box = (e) => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map((v) => Math.round(v)); };
  const rules = [];
  for (const sheet of document.styleSheets) {
    let list; try { list = sheet.cssRules; } catch (e) { continue; }
    const walk = (items, where) => { for (const r of items) {
      if (r.cssRules) walk(r.cssRules, where + ' > ' + (r.cssText.split('{')[0].trim().slice(0, 60)));
      if (r.selectorText && r.style && r.style.display && d && (() => { try { return d.matches(r.selectorText); } catch (e) { return false; } })())
        rules.push({ sheet: (sheet.href || 'inline').split('/').slice(-2).join('/'), where, selector: r.selectorText.slice(0, 160), display: r.style.display });
    } };
    walk(list, '');
  }
  const cs = d && getComputedStyle(d);
  return {
    dialog: d && { open: d.open, display: cs.display, position: cs.position, visibility: cs.visibility, zIndex: cs.zIndex,
                   box: box(d), parent: d.parentElement && (d.parentElement.id || d.parentElement.tagName) },
    rulesSettingDisplay: rules,
    button: b && { hidden: b.hidden, display: getComputedStyle(b).display, box: box(b) },
    viewport: [innerWidth, innerHeight],
  };
})()"""

AT = r"""((x, y) => { const e = document.elementFromPoint(x, y); const d = document.getElementById('markdown-dialog');
  return e && { tag: e.tagName, id: e.id, cls: String(e.className).slice(0, 80), insideDialog: !!(d && d.contains(e)) }; })"""

FIX = r"""(() => { const s = document.createElement('style'); s.id = 'diag-154';
  s.textContent = '#markdown-dialog:not([open]) { display: none; }'; document.head.append(s); return true; })()"""


def shot(session, out: Path, name: str) -> str | None:
    try:
        png = session.screenshot()
    except Exception as error:  # noqa: BLE001
        return f"no screenshot: {type(error).__name__}"
    (out / name).write_bytes(png)
    return name


def measure(session, browser: str, probe, out: Path, label: str) -> dict:
    record = {"read": pp.evaluate(session, READ)}
    rects = probe.ask_rectangles(session)
    point = probe.first_line_point(session, rects)
    record["point"] = point.get("point")
    if record["point"]:
        x, y = record["point"]
        record["elementAtPoint"] = pp.evaluate(session, f"{AT}({x}, {y})")
        start = pp.evaluate(session, probe.LOG_LENGTH)
        probe.real_click(session, browser, x, y)
        record["clickState"] = probe.ui.until(session, lambda s: "定位游標" in (s.get("latency") or ""), 10)
        record["placeCaretRequests"] = [e.get("op") for e in probe.log_from(session, start)
                                        if e.get("k") == "rq" and "PlaceCaret" in str(e.get("op"))]
    record["screenshot"] = shot(session, out, f"{label}-{browser}.png")
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    probe = d2.load_probe()
    identity = d2.host_identity(probe.DEFAULT_DDEV)
    doc = build_long_document(60)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    folder, name = f"diag-154-{args.browser}-{stamp}", "diag-154.odt"
    report = {"tool": "diag_markdown_dialog_on_host.py", "browser": args.browser, "hostIdentity": identity,
              "toolSha256": common.sha256_file(Path(__file__)), "doc": hashlib.sha256(doc).hexdigest(),
              "startedAt": common.now_iso()}
    instance = probe.Instance(probe.DEFAULT_DDEV)
    session = None
    with common.browser_lock(f"diag-154 {args.browser}", wait_s=0) as holder:
        report["lock"] = holder
        report["mkcol"] = instance.dav("MKCOL", folder)[0]
        try:
            instance.dav("PUT", f"{folder}/{name}", doc, {"Content-Type": "application/vnd.oasis.opendocument.text"})
            session = probe.ui.new_session(args.browser)
            report["version"] = getattr(session, "version", None)
            report["login"] = probe.login(session, instance.base, "admin", instance.password)
            probe.open_from_files(session, instance.base, folder, name, report)
            report["opened"] = probe.ui.quiet(session, 180)
            pp.evaluate(session, probe.INSTRUMENT)
            report["asShipped"] = measure(session, args.browser, probe, out, "as-shipped")
            report["fixApplied"] = pp.evaluate(session, FIX)
            time.sleep(0.5)
            report["withRule"] = measure(session, args.browser, probe, out, "with-rule")
        finally:
            if session is not None:
                report["close"] = common.close_browser(session)
            report["deletedFolder"] = instance.dav("DELETE", folder)[0]
            report["completedAt"] = common.now_iso()
            path = out / f"diag-154-{args.browser}-{stamp}.json"
            path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    for key in ("asShipped", "withRule"):
        r = report.get(key) or {}
        print(key, json.dumps({"dialog": (r.get("read") or {}).get("dialog"), "at": r.get("elementAtPoint"),
                               "placeCaret": r.get("placeCaretRequests"),
                               "rules": (r.get("read") or {}).get("rulesSettingDisplay")}, ensure_ascii=False))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
