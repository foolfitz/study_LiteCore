#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.3 (vi) and (vii): the product page and the v24 worker, served from a
symlink mirror of dist/ with ONE profile file changed per arm.  dist/ is never written.

Arms (findings/evidence/link-batch-v24/pre-count/page-gates/README.md, written before the run):

  control             the v24 profile as linked (its manifest materialised byte-identical): open
                      succeeds; a real click on the paper, then a real `x`; the first insertText
                      request carries route "uno-insert-text" and its reply method/completion name
                      the typed route.  The positive control of both (vi) and (vii).
  vii-leafless        the v24 manifest with `editorContract.typedInsert` removed: the page refuses on
                      the PAGE_BUILD_MISMATCH path; then three typing attempts (a real `x` where the
                      page left focus; a real click where the paper was, then `x`; the sink focused
                      by script, then `x`); zero insertText requests in the whole window.
  vi-stale-pair       the archived v23 engine pair (probe.wasm + probe.js, which one link produces
                      together) under the v24 manifest and worker: init refused DECLARED_EXPORT_MISSING.
  vi-stale-wasm-only  the literal reading of ruling 2 (c): only probe.wasm is v23's, the loader stays
                      v24's.  Recorded; not the (vi) verdict (README: the loader binds the wasm's
                      minified export names, so this pair is incoherent rather than stale).

Usage:  python3 tools/run_v24_page_gates.py --out <new dir> [--browser chrome|firefox] [--arm NAME]
The output directory must not exist; nothing is written anywhere else except the mirror under it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v21_input as inputs  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

PROJECT = common.PROJECT
DIST = common.DIST
PROFILE = "e2-editor-v24"
V24 = {  # build/archive/e2-editor-v24-27615808-worker-41041fe7/SHA256SUMS
    "probe.wasm": "276158084a602178f9b7219c086f749910601b1a121fca9339b10a79b0f7b639",
    "probe.js": "64aaa8dc2c7a1c366c76911213090ae60d39c26cd4207274ef1c0420a5a0b301",
    "sdk-worker.js": "41041fe746b2355a1768bc774a10ac59802a8e359579618be405e3696f3b9461",
    "sdk-manifest.json": "f9554e8c1b79ff4955dbfdf7dbe7c9975f3d0bcc945665c3491a730cb44cd04e",
}
V23_ARCHIVE = PROJECT / "build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6"
V23 = {  # its SHA256SUMS
    "probe.wasm": "fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658",
    "probe.js": "4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e",
}
PAGE_SHA256 = "b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669"
SDK_SHA256 = "afdff2d4c6fc86a3fbca9f40ab7c0122021c61a0d23a7969b4f80b7770f3632e"
LEAF_LINE = b'    "pasteMarkdown": "document-sdk-paste-markdown",\n    "typedInsert": "document-sdk-insert-typed-text"\n'
LEAF_GONE = b'    "pasteMarkdown": "document-sdk-paste-markdown"\n'
ARMS = ("control", "vii-leafless", "vi-stale-pair", "vi-stale-wasm-only")

# Observation only: wraps Worker before the page's module runs; records every request, response,
# event and worker error, and the trusted key/beforeinput events.  Pixel buffers become their length.
OBSERVER = """<script>
(() => {
  const rec = window.__gate = {requests: [], responses: [], events: [], workers: [], errors: [], inputs: []};
  const strip = (k, x) => (x instanceof ArrayBuffer || ArrayBuffer.isView(x)) ? {bytes: x.byteLength} : x;
  const snap = v => { try { return JSON.parse(JSON.stringify(v, strip)); } catch (e) { return {unserialisable: String(e)}; } };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) {
      super(url, options); const g = rec.workers.length + 1; this.__g = g;
      rec.workers.push({generation: g, url: String(url), at: performance.now()});
      this.addEventListener('message', ev => { const d = ev.data, item = {generation: g, at: performance.now(), message: snap(d)};
        if (d?.kind === 'response') rec.responses.push(item); else if (d?.kind === 'event') rec.events.push(item); });
      this.addEventListener('error', ev => rec.errors.push({generation: g, at: performance.now(), message: String(ev.message)}));
    }
    postMessage(m, ...rest) {
      if (m?.kind === 'request') rec.requests.push({generation: this.__g, at: performance.now(), message: snap(m)});
      return super.postMessage(m, ...rest);
    }
  };
  for (const type of ['keydown', 'beforeinput', 'pointerdown'])
    document.addEventListener(type, e => rec.inputs.push({type, at: performance.now(), key: e.key, data: e.data,
      inputType: e.inputType, isTrusted: e.isTrusted, target: e.target?.id || e.target?.tagName}), true);
})();
</script>"""

PAGE_STATE = """(() => { const g = window.__gate, pill = document.querySelector('#state-pill');
  const shown = id => { const el = document.querySelector(id); return !!el && getComputedStyle(el).display !== 'none'; };
  return {pill: pill?.dataset.state ?? null, toast: document.querySelector('#toast')?.textContent ?? null,
    doc: document.querySelector('#s-doc')?.textContent ?? null, expired: shown('#expired'), paper: shown('#paper'),
    actualHash: document.querySelector('#actual-hash')?.textContent ?? null,
    active: document.activeElement?.id || document.activeElement?.tagName || null,
    sinkDisabled: document.querySelector('#sink')?.disabled ?? null,
    requests: g.requests.length, responses: g.responses.length,
    inits: g.responses.filter(r => g.requests.some(q => q.message.operation === 'init' && q.message.requestId === r.message.requestId)).length,
    inserts: g.requests.filter(q => q.message.operation === 'insertText').length}; })()"""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def preflight() -> dict:
    out = {}
    for name, want in V24.items():
        for where in (DIST / "profiles" / PROFILE / name,):
            got = sha(where.read_bytes())
            if got != want:
                raise SystemExit(f"v24 profile file differs: {where}")
        out[f"v24/{name}"] = want
    for name, want in V23.items():
        if sha((V23_ARCHIVE / name).read_bytes()) != want:
            raise SystemExit(f"archived v23 file differs: {name}")
        out[f"v23-archive/{name}"] = want
    if sha((DIST / "e2-editor-app.js").read_bytes()) != PAGE_SHA256:
        raise SystemExit("dist page is not the v24 cutover page")
    if sha((DIST / "sdk/document-sdk.js").read_bytes()) != SDK_SHA256:
        raise SystemExit("dist SDK is not the v24 SDK")
    out["page"] = PAGE_SHA256
    out["sdk"] = SDK_SHA256
    out["laggingShell"] = pp.shell_lagging_source(DIST)
    return out


def overrides_for(arm: str) -> tuple[dict[str, bytes], dict]:
    manifest = (DIST / "profiles" / PROFILE / "sdk-manifest.json").read_bytes()
    html = (DIST / "e2-editor.html").read_text(encoding="utf-8")
    files = {"e2-editor.html": common.inject(html, [OBSERVER]).encode("utf-8")}
    base = f"profiles/{PROFILE}/"
    if arm == "vii-leafless":
        if manifest.count(LEAF_LINE) != 1:
            raise SystemExit("the typedInsert leaf is not where the arm expects it")
        changed = manifest.replace(LEAF_LINE, LEAF_GONE, 1)
        a, b = json.loads(manifest), json.loads(changed)
        del a["editorContract"]["typedInsert"]
        if a != b:
            raise SystemExit("the leafless manifest differs from the original by more than the leaf")
        files[base + "sdk-manifest.json"] = changed
    else:
        files[base + "sdk-manifest.json"] = manifest
    if arm in ("vi-stale-pair", "vi-stale-wasm-only"):
        files[base + "probe.wasm"] = (V23_ARCHIVE / "probe.wasm").read_bytes()
    if arm == "vi-stale-pair":
        files[base + "probe.js"] = (V23_ARCHIVE / "probe.js").read_bytes()
    return files, {path: sha(raw) for path, raw in files.items()}


def wait_for(session, predicate, limit_s: float) -> dict:
    until = time.monotonic() + limit_s
    state = None
    while time.monotonic() < until:
        state = evaluate(session, PAGE_STATE)
        if predicate(state):
            return state
        time.sleep(0.25)
    raise RuntimeError(f"observation bound reached; last state {json.dumps(state, ensure_ascii=False)}")


def settled(state: dict) -> bool:
    opened = state["doc"] not in (None, "", "—") and not state["expired"] and state["pill"] not in ("stopped", "expired")
    return state["expired"] or state["pill"] in ("stopped", "expired") or (opened and state["inserts"] == 0 and state["paper"])


def paper_center(session) -> tuple[float, float]:
    rect = evaluate(session, inputs.PAPER_RECT)
    return rect["left"] + rect["width"] * 0.3, rect["top"] + min(rect["height"] * 0.08, 120)


def attempts(session, browser: str) -> list[dict]:
    """vii-leafless / vi: what a user can do after the refusal, then the script-focused worst case."""
    out = []
    def mark(name):
        out.append({"step": name, "state": evaluate(session, PAGE_STATE)})
    mark("refused")
    inputs.key(session, browser, "x")
    time.sleep(1.0)
    mark("x-where-focus-was")
    desk = evaluate(session, """(() => { const r = document.querySelector('#desk').getBoundingClientRect();
      return {x: r.left + r.width * 0.3, y: r.top + Math.min(r.height * 0.2, 200)}; })()""")
    inputs.click(session, browser, desk["x"], desk["y"])
    inputs.key(session, browser, "x")
    time.sleep(1.0)
    mark("click-where-paper-was-then-x")
    focused = evaluate(session, "(() => { document.querySelector('#sink').focus(); return document.activeElement?.id || document.activeElement?.tagName; })()")
    inputs.key(session, browser, "x")
    time.sleep(1.5)
    mark("script-focused-sink-then-x")
    out[-1]["activeAfterScriptFocus"] = focused
    return out


def run_arm(session, browser: str, base: str, arm: str) -> dict:
    cell: dict = {"arm": arm, "browser": browser}
    navigate(session, base)
    cell["settled"] = wait_for(session, settled, 240)
    if arm == "control":
        if cell["settled"]["expired"] or cell["settled"]["pill"] == "stopped":
            raise RuntimeError("control did not open")
        x, y = paper_center(session)
        inputs.click(session, browser, x, y)
        time.sleep(0.5)
        inputs.key(session, browser, "x")
        cell["afterType"] = wait_for(session, lambda s: s["inserts"] >= 1 and evaluate(session, """(() => {
          const g = window.__gate, q = g.requests.find(r => r.message.operation === 'insertText');
          return !!q && g.responses.some(r => r.message.requestId === q.message.requestId); })()"""), 60)
    else:
        cell["attempts"] = attempts(session, browser)
    cell["record"] = evaluate(session, "window.__gate")
    return cell


def verdict(cell: dict) -> dict:
    rec = cell.get("record") or {}
    requests, responses = rec.get("requests", []), rec.get("responses", [])
    reply = lambda q: next((r["message"] for r in responses if r["message"].get("requestId") == q["message"].get("requestId")), None)
    inserts = [q for q in requests if q["message"].get("operation") == "insertText"]
    inits = [q for q in requests if q["message"].get("operation") == "init"]
    init_replies = [reply(q) for q in inits]
    exceptions = [r["message"] for r in responses if (r["message"].get("error") or {}).get("code") == "WORKER_EXCEPTION"]
    arm, out = cell["arm"], {"insertRequests": len(inserts), "initReplies": init_replies, "workerExceptions": len(exceptions)}
    if cell.get("fatal"):
        return {**out, "verdict": "NOT_ESTABLISHED", "reason": "runner fatal"}
    if arm == "control":
        first = inserts[0] if inserts else None
        r = reply(first) if first else None
        out["firstInsert"] = {"payload": first and first["message"].get("payload"), "reply": r}
        ok = (first is not None and first["message"]["payload"].get("route") == "uno-insert-text"
              and r is not None and r.get("ok") is True and (r.get("result") or {}).get("method") == "uno-insert-text"
              and (r.get("result") or {}).get("completion") == "uno-command-result"
              and all(x and x.get("ok") is True for x in init_replies) and not cell["settled"]["expired"])
        return {**out, "verdict": "PASS" if ok else "FAIL"}
    if arm == "vii-leafless":
        refused = cell["settled"]["expired"] and cell["settled"]["pill"] == "expired"
        out["refusedOnPageBuildMismatch"] = refused
        return {**out, "verdict": "PASS" if refused and not inserts else "FAIL"}
    codes = [(x or {}).get("error", {}).get("code") for x in init_replies]
    out["initCodes"] = codes
    named = codes == ["DECLARED_EXPORT_MISSING"]
    if arm == "vi-stale-pair":
        return {**out, "verdict": "PASS" if named and not inserts and not exceptions else "FAIL"}
    return {**out, "verdict": "RECORDED", "initRefusedAtInit": bool(codes) and codes[0] is not None and not inserts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", choices=("chrome", "firefox"), action="append")
    parser.add_argument("--arm", choices=ARMS, action="append")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to write into an existing path: {args.out}")
    browsers, arms = args.browser or ["chrome", "firefox"], args.arm or list(ARMS)
    report = {"schema": 1, "argv": sys.argv, "preflight": preflight(), "runs": []}
    args.out.mkdir(parents=True)
    write = lambda: (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    with common.browser_lock("run_v24_page_gates"):
        report["preRun"] = common.pre_run_checks()
        report["foreignCpu"] = common.foreign_cpu()
        write()
        if report["preRun"]["refuse"]:
            raise SystemExit("pre-run refusal: " + "; ".join(report["preRun"]["refuse"]))
        for arm in arms:
            target = args.out / "mirror" / arm
            files, hashes = overrides_for(arm)
            pp.build_mirror(DIST, target, files)
            with common.served(target) as base:
                for browser in browsers:
                    cell = {"arm": arm, "browser": browser, "mirrorOverrides": hashes}
                    session = None
                    try:
                        session = common.open_browser(browser)
                        cell.update(run_arm(session, browser, base, arm))
                    except Exception:  # noqa: BLE001 -- recorded, never retried
                        cell["fatal"] = traceback.format_exc()
                        if session is not None:
                            try:
                                cell["record"] = evaluate(session, "window.__gate")
                                cell["lastState"] = evaluate(session, PAGE_STATE)
                            except Exception:  # noqa: BLE001
                                cell["exportFailure"] = traceback.format_exc()
                    finally:
                        if session is not None:
                            cell["cleanup"] = common.close_browser(session)
                    cell["verdict"] = verdict(cell)
                    name = f"{browser}-{arm}.json"
                    (args.out / name).write_text(json.dumps(cell, indent=1, ensure_ascii=False) + "\n")
                    report["runs"].append({"path": name, "sha256": sha((args.out / name).read_bytes()),
                                           "verdict": cell["verdict"]["verdict"]})
                    write()
    print(json.dumps([(r["path"], r["verdict"]) for r in report["runs"]], indent=1))
    return 0 if all(r["verdict"] in ("PASS", "RECORDED") for r in report["runs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
