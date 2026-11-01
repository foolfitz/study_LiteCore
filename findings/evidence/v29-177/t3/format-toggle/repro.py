#!/usr/bin/env python3
"""F3-83 moved one cell: Firefox `clear-format-removes-every-inline-format` PASS -> NOT_ESTABLISHED, because the italic press in
the accumulating arms found the page's format cache at `true` and asked for OFF (formatCacheBefore 'true', MKPRELIC not italic).
One occurrence.  This counts it: all twelve arms of `format_arm` (run_e2_c_product_path.py) in F3's order, step for step, LOOPS times,
with every format value the worker hands the page recorded.  Same evaluate strings, imported.  Not timing.  dist/ is not written.

  repro.py PROFILE BROWSER LOOPS OUT.json      PROFILE e2-editor-v29 (the page as served) or e2-editor-v28 (repointed in the mirror)
  FAST_MS=30 repro.py ...                      sleep that long after each press instead of the first 400 ms poll
  CLEAR_MS=6 repro.py ...                      sleep that long after the clear before the accumulating arms poll for its label
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[5] / "wasm_sdk_probe"
sys.path.insert(0, str(ROOT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402

OBSERVER = """<script>
(() => {
  const log = []; window.__fmt = log;
  const find = (v, depth) => { if (!v || typeof v !== 'object' || depth > 4 || ArrayBuffer.isView(v)) return null;
    if (v.format && typeof v.format === 'object' && 'bold' in v.format) return v;
    for (const k of Object.keys(v)) { if (k === 'pixels') continue; const r = find(v[k], depth + 1); if (r) return r; } return null; };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(u, o) { super(u, o); this.addEventListener('message', (e) => { const d = e.data, s = find(d, 0);
      if (s) { log.push([Math.round(performance.now() * 10) / 10, d.kind || d.type || d.event || '?', s.source ?? null, s.sourceSequence ?? null,
                         s.format.bold, s.format.italic, s.format.underline, s.format.strikethrough ?? s.format.strikeout]);
               if (log.length > 6000) log.splice(0, 2000); } }); }
    postMessage(m, ...r) { if (m && m.kind === 'request') log.push([Math.round(performance.now() * 10) / 10, 'request', [m.operation, m.payload?.action ?? m.payload?.kind ?? null, m.payload?.enabled ?? null].join(' '), null]); if (m && m.kind === 'request' && m.operation === 'paint') log.pop();
      return super.postMessage(m, ...r); }
  };
})();
</script>"""
FAST_MS = float(os.environ.get("FAST_MS", "0"))
CLEAR_MS = float(os.environ.get("CLEAR_MS", "0"))
ARMS = (("set-bold", "MKPREOLD"), ("set-italic", "MKPRELIC"), ("set-underline", "MKPREINE"), ("set-strikethrough", "MKALLON"))
NORMALISED = (("set-bold", "MKBOLDON", "MKBOLDOFF"), ("set-italic", "MKITALON", "MKITALOFF"),
              ("set-underline", "MKUNDON", "MKUNDOFF"), ("set-strikethrough", "MKSTRON", "MKSTROFF"))
PROP = {"set-bold": "bold", "set-italic": "italic", "set-underline": "underline", "set-strikethrough": "strikethrough"}


def main() -> int:
    profile, browser, loops, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
    dist = ROOT / "dist"
    html = (dist / "e2-editor.html").read_text(encoding="utf-8")
    anchor = '<script type="module"'
    if html.count(anchor) != 1:
        raise SystemExit("no single module script in the page")
    overrides = {"e2-editor.html": html.replace(anchor, OBSERVER + anchor).encode("utf-8")}
    if profile != "e2-editor-v29":
        source = pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
        page, _, _ = pp.repointed_page(source, profile, dist / "profiles" / profile / "sdk-manifest.json")
        overrides["e2-editor-app.js"] = page.encode("utf-8")
    mirror = Path(tempfile.mkdtemp(prefix="fmt-", dir=str(ROOT / "build"))) / "root"
    pp.build_mirror(dist, mirror, overrides)
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(ROOT / "web/serve.py"), "--port", str(port), "--root", str(mirror)], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {"profile": profile, "browser": browser, "loops": loops, "fastMs": FAST_MS, "clearMs": CLEAR_MS, "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "arms": [], "clearWaits": []}
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = (pp.ChromeSession if browser == "chrome" else pp.FirefoxSession)("cold")
        pp.navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.INSTALL)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./e1-fixtures/list-contexts.odt").replace("ARG_NAME", "list-contexts.odt"))
        pp.wait_for(session, lambda s: (s.get("doc") or "") == "list-contexts.odt" and s.get("state") == "ready", 180)
        time.sleep(1.0)
        ev = pp.evaluate
        clicks = pp.caret_click_fractions(ev(session, pp.LINE_INK.replace("ARG_Y", "0.24")) or {})
        pp.place_caret_and_settle(session, pp.POINT_AT, clicks["near"], "0.24")

        def rev():
            return pp.revision_of(ev(session, pp.READ_STATE))

        def after(floor):
            pp.wait_for(session, lambda st, f=floor: pp.revision_of(st) is not None and f is not None and pp.revision_of(st) > f, 20)

        def arm(loop, action, marker, turn_on, normalise):
            ev(session, pp.CLEAR_TOAST)
            floor = rev()
            ev(session, pp.PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
            after(floor)
            label = ev(session, pp.BUTTON_LABEL.replace("ARG_ACTION", action))
            if normalise:
                ev(session, pp.CLEAR_LATENCY)
                ev(session, pp.CLEAR_FORMAT)
                pp.wait_for(session, lambda st: "清除格式" in (st.get("latency") or ""), 30)
                if not turn_on:
                    ev(session, pp.CLEAR_LATENCY)
                    ev(session, pp.PRESS.replace("ARG_ACTION", action))
                    pp.wait_for(session, lambda st, want=label: bool(want) and want in (st.get("latency") or ""), 30)
            before = ev(session, pp.FORMAT_BUTTON_STATE.replace("ARG_ACTION", action))
            index = ev(session, "(() => window.__fmt.length)()")
            ev(session, pp.CLEAR_LATENCY)
            ev(session, pp.PRESS.replace("ARG_ACTION", action))
            pressed = time.monotonic()
            if FAST_MS:
                time.sleep(FAST_MS / 1000)   # the press lands before the first poll: the path of F3-83's failing arm (waited 3 ms)
            settled = pp.wait_for(session, lambda st, want=label: bool(want) and want in (st.get("latency") or ""), 30)
            waited = round((time.monotonic() - pressed) * 1000)
            later = ev(session, pp.FORMAT_BUTTON_STATE.replace("ARG_ACTION", action))
            floor = rev()
            mark = f"{marker}{loop}"
            ev(session, pp.SET_TEXT.replace("ARG_TEXT", mark))
            ev(session, pp.PRESS.replace("ARG_ACTION", "insert-text"))
            after(floor)
            saved = pp.capture_save(session, ev(session, pp.SAVE_COUNT) or 0)
            style = pp.inline_styles_of(saved, mark) if saved else {}
            want_before = "false" if turn_on else "true"
            report["arms"].append({"loop": loop, "action": action, "marker": mark, "turnOn": turn_on, "normalise": normalise,
                                   "cacheBefore": before, "cacheAfter": later, "waitedMs": waited,
                                   "latency": (settled or {}).get("latency"), "styles": {k: style.get(k) for k in PROP.values()},
                                   "found": style.get("found"), "logIndexBeforePress": index,
                                   "ok": before == want_before and style.get(PROP[action]) is turn_on})

        for loop in range(loops):
            for action, on_marker, off_marker in NORMALISED:
                arm(loop, action, on_marker, True, True)
                arm(loop, action, off_marker, False, True)
            ev(session, pp.CLEAR_LATENCY)
            ev(session, pp.CLEAR_FORMAT)
            if CLEAR_MS:
                time.sleep(CLEAR_MS / 1000)
            report["clearWaits"].append(pp.evaluate(session, "(() => document.querySelector('#s-latency')?.textContent)()"))
            pp.wait_for(session, lambda st: "清除格式" in (st.get("latency") or ""), 30)
            for action, marker in ARMS:
                arm(loop, action, marker, True, False)
        report["log"] = pp.evaluate(session, "(() => window.__fmt)()")
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if session is not None:
            try:
                session.close()
            except Exception as error:  # noqa: BLE001
                report["closeError"] = str(error)
        server.terminate(); server.wait(timeout=10)
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    bad = [a for a in report["arms"] if not a["ok"]]
    print(json.dumps({"profile": profile, "browser": browser, "arms": len(report["arms"]),
                      "bad": len(bad), "first": [(a["marker"], a["cacheBefore"], a["cacheAfter"], a["waitedMs"]) for a in bad[:4]],
                      "fastPress": sum(1 for a in report["arms"] if a["waitedMs"] < 100)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
