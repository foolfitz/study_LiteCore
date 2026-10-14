#!/usr/bin/env python3
"""Task 10-14h, confirmation probe (scratchpad; not part of the tree).

On the bytes currently in dist/ (the v68 red candidate, session fc5ac883...), record what the
engine's `editorPlaceCaretV2` answers -- `completion` and the time to its reply -- for three
clicks the product makes:

  A  a click that MOVES the caret, with a collapsed selection (the ordinary click);
  B  a real Left key while a drag range is open: the page's moveFromPoint clicks at the caret's
     own point to collapse the range (the 129-B cell shape);
  C  a click on the caret's own point with a collapsed selection (056's identical-point click).

The page is a mirror of dist/ (pp.build_mirror) with the 129 probe's one appended line
(`globalThis.__m4`), so that the page's own session can be read; no dist byte is changed.
A Worker.prototype.postMessage hook keeps the `editorPlaceCaretV2` / `click` request times and
reply payloads.  Usage: probe_140_completion.py OUT_DIR [chrome|firefox]
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
sys.path.insert(0, str(TOOLS))
import probe_129_m4_wasm as m4  # noqa: E402
from r7_support import run_in_page  # noqa: E402

DIST = m4.DIST
DOCS = Path("/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/129/final/round-20261012T092119Z/docs")
DOC = "arrow-selection-shapes"

HOOK = r"""(() => {
  if (window.__pc) return;
  const T = () => Math.round(performance.now() * 10) / 10;
  const pc = window.__pc = { calls: [] };
  const ops = new Map(), seen = new WeakSet();
  const proto = Worker.prototype, post = proto.postMessage;
  proto.postMessage = function (m, ...rest) {
    if (!seen.has(this)) {
      seen.add(this);
      this.addEventListener('message', (e) => {
        const d = e.data; if (!d || typeof d !== 'object' || d.kind !== 'response') return;
        const req = ops.get(d.requestId); if (!req) return; ops.delete(d.requestId);
        if (req.op !== 'editorPlaceCaretV2' && req.op !== 'click') return;
        const r = d.result || {};
        const now = T();
        pc.calls.push({ op: req.op, sentAt: req.t, answeredAt: now, ms: Math.round((now - req.t) * 10) / 10,
          ok: d.ok, err: d.ok ? null : (d.error && d.error.code), errMessage: d.ok ? null : (d.error && d.error.message),
          completion: r.completion ?? null, x: req.x, y: req.y,
          caret: r.state && r.state.caret ? r.state.caret : null,
          selectionCollapsed: r.state && r.state.selection ? r.state.selection.collapsed : null,
          sequenceBefore: r.callbackSequenceBefore ?? null, sequenceAfter: r.callbackSequenceAfter ?? null });
      });
    }
    if (m && m.kind === 'request')
      ops.set(m.requestId, { op: m.operation, t: T(), x: m.payload && m.payload.xTwips, y: m.payload && m.payload.yTwips });
    return post.call(this, m, ...rest);
  };
})();"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight() -> dict:
    wallet = subprocess.run(["busctl", "--user", "get-property", "org.freedesktop.secrets",
                             "/org/freedesktop/secrets/collection/kdewallet", "org.freedesktop.Secret.Collection", "Locked"],
                            capture_output=True, text=True)
    ours = subprocess.run(["pgrep", "-af", "probe_|check_m3|run_e2_c|run_merge|run_v20"], capture_output=True, text=True).stdout
    ours = [line for line in ours.splitlines() if "probe_140_completion" not in line and "pgrep" not in line]
    chrome = subprocess.run(["pgrep", "-c", "chrome"], capture_output=True, text=True).stdout.strip()
    return {"kwalletLocked": wallet.stdout.strip(), "otherRunners": ours, "chromeProcesses": int(chrome or 0),
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def calls(session, since: int) -> list:
    return m4.page_eval(session, f"globalThis.__pc.calls.slice({since})")


def calls_len(session) -> int:
    return m4.page_eval(session, "globalThis.__pc.calls.length")


def latency_records(log: list) -> list:
    return [(r["t"], r["latency"]) for r in log if r["what"] == "latency"]


def pick(es: dict) -> dict:
    return {"caret": es["caret"], "selection": es.get("selection"), "sourceSequence": es.get("sourceSequence")}


def main() -> int:
    out = Path(sys.argv[1])
    browser = sys.argv[2] if len(sys.argv) > 2 else "chrome"
    out.mkdir(parents=True, exist_ok=True)
    page = (DIST / "e2-editor-app.js").read_bytes()
    report = {"probe": "probe_140_completion.py (scratchpad)", "browser": browser,
              "pageSha256": hashlib.sha256(page).hexdigest(),
              "sessionSha256": sha256(DIST / "editor-shell-v2" / "narrow-editor-v2-session.js"),
              "clientSha256": sha256(DIST / "editor-shell-v2" / "narrow-editor-v2-client.js"),
              "profile": None, "doc": str(DOCS / f"{DOC}.odt"), "docSha256": sha256(DOCS / f"{DOC}.odt"),
              "preflight": preflight(), "startedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arms": []}
    if report["preflight"]["kwalletLocked"] == "b true":
        report["fatal"] = "KWallet is locked"
        (out / f"report-{browser}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
        print(report["fatal"])
        return 2
    env = m4.Env(browser, out)
    try:
        env.serve("red", page + m4.INSTRUMENT_LINE.encode(), {f"{DOC}.odt": (DOCS / f"{DOC}.odt").read_bytes()})
        report["profile"] = m4.pp.product_profile(env.roots["red"])
        env.start()
        report["version"] = getattr(env.session, "version", None)
        report["boot"] = env.goto("red")
        s = env.session
        run_in_page(s, HOOK)
        report["open"] = env.open_doc(DOC)
        st = m4.editor_state(s)
        report["docTwips"] = {"w": st["docW"], "h": st["docH"]}

        # A: a moving click, collapsed selection (the ordinary click on text)
        pre = m4.editor_state(s)
        mark, n = m4.log_mark(s), calls_len(s)
        m4.click_at(s, st, pre["caret"]["x"] + 3000, m4.mid(pre["caret"]))
        time.sleep(0.3)
        report["arms"].append({"arm": "A-moving-click-collapsed-selection", "before": pick(pre),
                               "calls": calls(s, n), "latency": latency_records(m4.log_since(s, mark)),
                               "after": pick(m4.editor_state(s))})

        # a drag range: Home, Right x5 -> anchor, Right x10 -> far, drag anchor -> far
        m4.keys(s, browser, ["Home"]); m4.quiet(s)
        m4.keys(s, browser, ["Right"] * 5); m4.quiet(s)
        anchor = m4.editor_state(s)["caret"]
        m4.keys(s, browser, ["Right"] * 10); m4.quiet(s)
        far = m4.editor_state(s)["caret"]
        m4.drag(s, st, (anchor["x"], m4.mid(anchor)), (far["x"], m4.mid(far)))
        time.sleep(0.2); m4.quiet(s)
        sel = m4.selection_text(s)
        pre = m4.editor_state(s)
        report["range"] = {"anchor": anchor, "far": far, "selectionText": sel.get("text"), "before": pick(pre),
                           "toolbar": m4.toolbar_shape(s)}

        # B: a real Left key -> moveFromPoint -> a click at the caret's own point that collapses the range
        mark, n = m4.log_mark(s), calls_len(s)
        m4.keys(s, browser, ["Left"])
        log = m4.wait_key_done(s, mark)
        m4.quiet(s); time.sleep(0.3); m4.quiet(s)
        report["arms"].append({"arm": "B-left-key-collapses-the-range", "before": pick(pre), "timing": m4.timing_of(log),
                               "calls": calls(s, n), "toasts": m4.toasts_in(m4.log_since(s, mark)),
                               "after": pick(m4.editor_state(s)), "toolbar": m4.toolbar_shape(s)})

        # C: a click on the caret's own point, collapsed selection (056's identical point)
        pre = m4.editor_state(s)
        mark, n = m4.log_mark(s), calls_len(s)
        m4.click_at(s, st, pre["caret"]["x"], m4.mid(pre["caret"]))
        time.sleep(0.3)
        report["arms"].append({"arm": "C-identical-point-click-collapsed-selection", "before": pick(pre),
                               "calls": calls(s, n), "latency": latency_records(m4.log_since(s, mark)),
                               "after": pick(m4.editor_state(s))})
    except Exception:  # noqa: BLE001
        import traceback
        report["fatal"] = traceback.format_exc()
        print(report["fatal"])
    finally:
        report["completedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        env.close()
        (out / f"report-{browser}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    for arm in report["arms"]:
        print(arm["arm"], json.dumps(arm.get("timing") or arm.get("latency"), ensure_ascii=False))
        for c in arm["calls"]:
            print("   ", c["op"], c["ms"], "ms", c["ok"], c["err"], c["completion"], "y=", c["y"], "caret=", c["caret"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
