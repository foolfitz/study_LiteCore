#!/usr/bin/env python3
"""Finding 155, before any host step: does the host rule centre the open dialog?

A reduced reproduction, not a host measurement (it satisfies no criterion; the
criterion is H-155 on the host, SPEC-M3-link-batch-v22 §14). It builds three
pages from the real sources and reads the open dialog's box in headless Chrome
and Firefox:

  mirror     the page's own <style> and dialog markup, no Nextcloud CSS
             (positive control: the browser's own `margin: auto` centres it)
  as-0227    plus Nextcloud's two reset rules that name `dialog`, copied from the
             installed core/css/server.css, and the page's style wrapped in
             @scope (#litecore-editor-root) as templates/editor.php wraps it,
             with 0.2.26's host rule `dialog:not([open])` -- expected top left,
             as H-154o read it on the host
  with-rule  as-0227 plus 0.2.28's host rule `dialog[open] { margin: auto; }`

Nothing here touches ddev or the host repo: the server.css and the page are read
from disk. Usage: precheck_margin_rule.py --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "wasm_sdk_probe" / "tools"))
from run_browser_probe import ChromeSession, FirefoxSession  # noqa: E402
from r7_support import evaluate  # noqa: E402

PAGE = REPO / "wasm_sdk_probe" / "web" / "e2-editor.html"
SERVER_CSS = Path.home() / "Projects/Nextcloud_Apps/litecore/nextcloud/core/css/server.css"
SCRATCH = REPO / "wasm_sdk_probe" / "build" / "scratch-155-precheck"   # snap Firefox cannot see /tmp
HOST_CLOSED = "#litecore-editor-root dialog:not([open]) { display: none; }"
HOST_OPEN = "#litecore-editor-root dialog[open] { margin: auto; }"

READ = r"""(() => {
  const d = document.getElementById('markdown-dialog');
  d.showModal();
  const r = d.getBoundingClientRect(), cs = getComputedStyle(d);
  const box = [r.x, r.y, r.width, r.height].map((v) => Math.round(v));
  const vw = innerWidth, vh = innerHeight;
  return { open: d.open, box, margin: cs.margin, position: cs.position, padding: cs.padding,
           viewport: [vw, vh], client: [document.documentElement.clientWidth, document.documentElement.clientHeight],
           offset: [Math.round(r.x + r.width / 2 - vw / 2), Math.round(r.y + r.height / 2 - vh / 2)] };
})()"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pages() -> dict[str, str]:
    html = PAGE.read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    dialog = re.search(r'<dialog id="markdown-dialog".*?</dialog>', html, re.S).group(0)
    css = SERVER_CSS.read_text(encoding="utf-8")
    resets = [rule for rule in re.findall(r"[^{}]+\{[^}]*\}", css)
              if re.search(r"(^|,)\s*dialog\s*(,|\{)", rule.split("{")[0] + "{")]
    if len(resets) != 2:
        raise SystemExit(f"expected Nextcloud's two reset rules naming dialog, found {len(resets)}: {resets}")
    marker = "<script>globalThis.__probe_metrics = {};</script>"
    mirror = f"<!doctype html><meta charset=utf-8><style>{style}</style><body>{dialog}{marker}"
    host = ("<!doctype html><meta charset=utf-8><style>" + "\n".join(resets) + "</style><body>"
            f"<style>@scope (#litecore-editor-root) {{\n{style}\n}}</style><style>{HOST_CLOSED}@@OPEN@@</style>"
            f'<div id="litecore-editor-root">{dialog}</div>{marker}')
    return {"mirror": mirror, "as-0227": host.replace("@@OPEN@@", ""),
            "with-rule": host.replace("@@OPEN@@", "\n" + HOST_OPEN)}, resets


def session(kind: str):
    if kind == "chrome":
        s = ChromeSession("cold")
        s.call("Emulation.setDeviceMetricsOverride", {"width": 1850, "height": 980, "deviceScaleFactor": 1, "mobile": False})
        return s
    s = FirefoxSession("cold", profile_dir=SCRATCH / f"ff-{time.monotonic_ns()}")
    s.command("POST", "/window/rect", {"width": 1850, "height": 1080})
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    built, resets = pages()
    report = {"tool": "precheck_margin_rule.py", "toolSha256": sha(Path(__file__).read_bytes()),
              "page": str(PAGE.relative_to(REPO)), "pageSha256": sha(PAGE.read_bytes()),
              "serverCss": str(SERVER_CSS), "serverCssSha256": sha(SERVER_CSS.read_bytes()),
              "resets": resets, "hostRule": HOST_OPEN, "variants": {}, "readings": {}}
    for name, text in built.items():
        path = args.out / f"{name}.html"
        path.write_text(text, encoding="utf-8")
        report["variants"][name] = sha(text.encode("utf-8"))
    for kind in ("chrome", "firefox"):
        s = session(kind)
        try:
            report["readings"][kind] = {"version": s.version}
            for name in built:
                s.navigate((args.out / f"{name}.html").resolve().as_uri())
                time.sleep(0.3)
                report["readings"][kind][name] = evaluate(s, READ)
        finally:
            s.close()
    (args.out / "precheck.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    for kind in ("chrome", "firefox"):
        for name in built:
            r = report["readings"][kind][name]
            print(f"{kind:8} {name:10} box {r['box']} viewport {r['viewport']} client {r['client']} "
                  f"offset {r['offset']} margin {r['margin']!r} position {r['position']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
