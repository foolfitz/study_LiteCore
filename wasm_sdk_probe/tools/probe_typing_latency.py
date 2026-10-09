#!/usr/bin/env python3
"""Where does the time go between a typed key and the character on screen?

The owner, hand-testing host 0.2.9 (2026-10-09): "打字到文字出現在段落中，有點慢". Nothing in the tree
has measured it (the merge spec's §8 registers "效能與主迴圈模型：沒有任何量測").  This measures it on the
shipped standalone page from dist/, changing no product byte: the served HTML (a mirror override) gets
one classic script before the page's module that wraps CanvasRenderingContext2D.prototype.putImageData
-- the page's only blit -- and logs each call's time.  Per typed character it records three times on the
page's clock (performance.now()):

  key       the keydown (capture listener on the document)
  revision  the page's revision counter (#s-revision) showing that character committed
  paint     the first putImageData after that revision change  (what the user sees)

Real keys (Chrome: CDP; Firefox: WebDriver actions), N characters at a fixed gap after the caret is
placed and the page is idle.  Documents: `boundaries` (27 short paragraphs) and `owner` (563 KB).

  probe_typing_latency.py --browser chrome --document owner --gap 200 --chars 20 --out REPORT.json
"""
from __future__ import annotations

import argparse
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
PLACES = {  # document: (path, click inside the text on v19, then End)
    "boundaries": (HERE / "test-docs" / "merge" / "odt" / "boundaries.odt", ("0.236572", "0.045065")),
    "owner": (HERE / "build" / "scratch-m3-production-ui" / "PMPC指南.odt", ("0.5", "0.010373")),
}
PAINT_SHIM = """<script>
(() => {
  const proto = CanvasRenderingContext2D.prototype, native = proto.putImageData;
  const log = [];
  proto.putImageData = function (...args) {
    log.push(Math.round(performance.now() * 10) / 10);
    if (log.length > 5000) log.splice(0, 1000);
    document.documentElement.dataset.paints = JSON.stringify(log.slice(-400));
    return native.apply(this, args);
  };
})();
</script>"""
WATCH = """(() => { const root = document.documentElement, rev = document.querySelector('#s-revision');
  root.dataset.keys = '[]'; root.dataset.revs = '[]';
  if (!root.dataset.watching) {
    root.dataset.watching = '1';
    document.addEventListener('keydown', (e) => {
      const k = JSON.parse(root.dataset.keys); k.push([e.key, Math.round(performance.now() * 10) / 10]);
      root.dataset.keys = JSON.stringify(k); }, true);
    new MutationObserver(() => { const r = JSON.parse(root.dataset.revs);
      r.push([rev.textContent, Math.round(performance.now() * 10) / 10]); root.dataset.revs = JSON.stringify(r);
    }).observe(rev, { childList: true, characterData: true, subtree: true });
  }
  return true; })()"""
READ = """(() => { const d = document.documentElement.dataset;
  return { keys: JSON.parse(d.keys || '[]'), revs: JSON.parse(d.revs || '[]'), paints: JSON.parse(d.paints || '[]') }; })()"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--document", choices=sorted(PLACES), required=True)
    ap.add_argument("--gap", type=int, default=200)
    ap.add_argument("--chars", type=int, default=20)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    doc, click = PLACES[a.document]
    html = (DIST / "e2-editor.html").read_text(encoding="utf-8")
    anchor = '<script type="module" src="./e2-editor-app.js"></script>'
    if html.count(anchor) != 1:
        raise SystemExit("the page's module script is not where the shim expects it")
    mirror = Path(tempfile.mkdtemp(prefix="typing-")) / "root"
    pp.build_mirror(DIST, mirror, {"e2-editor.html": html.replace(anchor, PAINT_SHIM + anchor).encode("utf-8")})
    (mirror / "doc.odt").write_bytes(doc.read_bytes())
    report = {"probe": "probe_typing_latency.py", "browser": a.browser, "document": a.document, "gap": a.gap,
              "chars": a.chars, "page": hashlib.sha256((DIST / "e2-editor-app.js").read_bytes()).hexdigest(),
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port), "--root", str(mirror)],
                              cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = (pp.ChromeSession if a.browser == "chrome" else pp.FirefoxSession)("cold")
        report["version"] = getattr(session, "version", None)
        pp.navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.INSTALL)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./doc.odt").replace("ARG_NAME", "doc.odt"))
        pp.wait_for(session, lambda s: (s.get("doc") or "") == "doc.odt" and s.get("state") == "ready", 180)
        p111.quiet(session)
        before = (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")
        pp.evaluate(session, pp.POINT_AT.replace("ARG_X", click[0]).replace("ARG_Y", click[1]))
        pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before, 30)
        p111.quiet(session)
        p111.burst(session, a.browser, ["End"], 0)
        p111.quiet(session)
        time.sleep(1.0)
        start_revision = (pp.evaluate(session, pp.READ_STATE) or {}).get("revision")
        report["startRevision"] = start_revision
        pp.evaluate(session, WATCH)
        letters = [chr(ord("a") + i % 26) for i in range(a.chars)]
        p111.burst(session, a.browser, letters, a.gap)
        time.sleep(3.0)
        p111.quiet(session, 60)
        time.sleep(1.0)
        raw = pp.evaluate(session, READ)
        report["raw"] = raw
        keys = [t for k, t in raw["keys"] if len(k) == 1]
        revs = [(int(v), t) for v, t in raw["revs"] if str(v).isdigit()]
        paints = raw["paints"]
        rows = []
        # The page rewrites #s-revision on every state update, the same value included, so
        # the observer sees repeats; character i is the first write of start + i + 1 after its key.
        base_rev = int(start_revision) if str(start_revision).isdigit() else None
        for i, tk in enumerate(keys):
            want = (base_rev + 1 + i) if base_rev is not None else None
            tr = next((t for v, t in revs if v == want and t >= tk), None)
            tp = next((t for t in paints if tr is not None and t >= tr), None)
            rows.append({"i": i, "key": tk, "revisionMs": None if tr is None else round(tr - tk, 1),
                         "paintMs": None if tp is None else round(tp - tk, 1)})
        report["rows"] = rows
        def stats(xs):
            xs = sorted(x for x in xs if x is not None)
            return None if not xs else {"n": len(xs), "min": xs[0], "median": xs[len(xs) // 2], "max": xs[-1]}
        report["summary"] = {"revisionMs": stats([r["revisionMs"] for r in rows]),
                             "paintMs": stats([r["paintMs"] for r in rows]),
                             "keysSeen": len(keys), "revisionChanges": len(revs), "paints": len(paints)}
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
