#!/usr/bin/env python3
"""T3's typing arm (SPEC-M3-v29-tick-pacing section 6, section 11): the unchanged typing probe at a gap either side of the
300 ms grace, plus a save at the end, so that "every key committed" and "in the right order" are both read, not inferred.

tools/probe_typing_latency.py is not edited.  In process: a blob catcher joins the served HTML (a mirror override), and the
session's close() first presses the product's save and keeps the Blob.  Nothing under dist/ is written.

  gap_order.py run BROWSER DOCUMENT GAP CHARS OUT.json     the probe's report at OUT.json, the save at OUT.odt
  gap_order.py read OUT.json                               the verdict on one run (exit 0 iff it holds)
  gap_order.py --self-test OUT.json                        each clause's mutation of a holding run must be red

A run holds iff: keysSeen == chars; every row committed (revisionMs not None) with a strictly increasing key time; the saved
document has the typed string exactly once, contiguous, in one paragraph.  A swap, a loss or a duplicate each break that.
"""
from __future__ import annotations

import base64
import copy
import io
import json
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[5] / "wasm_sdk_probe"
sys.path.insert(0, str(ROOT / "tools"))

CATCH = b"""<script>
(() => { window.__blobs = []; const create = URL.createObjectURL.bind(URL);
  URL.createObjectURL = b => { if (b instanceof Blob) window.__blobs.push(b); return create(b); };
  const click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { if (this.hasAttribute('download')) return; return click.call(this); };
})();
</script>"""
BLOB = """(async () => { const b = window.__blobs.at(-1); const u = new Uint8Array(await b.arrayBuffer());
  let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192)); return btoa(s); })()"""
TEXT_NS = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def paragraphs(odt: bytes) -> list[str]:
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(odt)).read("content.xml"))
    return ["".join(e.itertext()) for e in root.iter() if e.tag in (TEXT_NS + "p", TEXT_NS + "h")]


def typed(chars: int) -> str:
    return "".join(chr(ord("a") + i % 26) for i in range(chars))


def judge(report: dict, paras: list[str]) -> dict:
    rows, summary, chars = report.get("rows") or [], report.get("summary") or {}, report.get("chars")
    want = typed(chars)
    hits = [p.count(want) for p in paras]
    keys = [r["key"] for r in rows]
    clauses = {"keysSeen": summary.get("keysSeen") == chars and len(rows) == chars,
               "everyKeyCommitted": bool(rows) and all(r.get("revisionMs") is not None for r in rows),
               "keysInOrder": all(a < b for a, b in zip(keys, keys[1:])),
               "savedOnceInOrder": sum(hits) == 1}
    return {"holds": all(clauses.values()), "clauses": clauses, "occurrences": sum(hits),
            "commitMedianMs": (summary.get("revisionMs") or {}).get("median"), "commitMaxMs": (summary.get("revisionMs") or {}).get("max")}


def load(out: Path):
    report = json.loads(out.read_text())
    raw = out.with_suffix(".odt").read_bytes() if out.with_suffix(".odt").is_file() else b""
    return report, (paragraphs(raw) if raw else [])


def run(browser, document, gap, chars, out: Path) -> int:
    import probe_typing_latency as p
    pp = p.pp
    build = pp.build_mirror

    def mirror(src, target, overrides):
        html = overrides["e2-editor.html"]
        if html.count(b"<script") < 1:
            raise SystemExit("no script tag to put the catcher before")
        return build(src, target, {**overrides, "e2-editor.html": html.replace(b"<script", CATCH + b"<script", 1)})
    pp.build_mirror = mirror
    saved: dict = {}

    def with_save(base):
        class Saving(base):
            def close(self):
                try:
                    before = pp.evaluate(self, "window.__blobs.length")
                    pp.evaluate(self, pp.PRESS.replace("ARG_ACTION", "save"))
                    deadline = time.monotonic() + 90
                    while time.monotonic() < deadline and pp.evaluate(self, "window.__blobs.length") <= before:
                        time.sleep(0.25)
                    saved["raw"] = base64.b64decode(pp.evaluate(self, BLOB))
                except Exception as error:  # noqa: BLE001 -- the run reads red without a save, and says why
                    saved["error"] = f"{type(error).__name__}: {error}"
                return super().close()
        return Saving
    pp.ChromeSession, pp.FirefoxSession = with_save(pp.ChromeSession), with_save(pp.FirefoxSession)
    sys.argv = ["probe_typing_latency.py", "--browser", browser, "--document", document, "--gap", str(gap),
                "--chars", str(chars), "--out", str(out)]
    code = p.main()
    if "raw" in saved:
        out.with_suffix(".odt").write_bytes(saved["raw"])
    if "error" in saved:
        out.with_suffix(".save-error.txt").write_text(saved["error"] + "\n")
    return code


def main() -> int:
    mode = sys.argv[1]
    if mode == "run":
        return run(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), Path(sys.argv[6]))
    out = Path(sys.argv[2])
    report, paras = load(out)
    if mode == "read":
        result = judge(report, paras)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["holds"] else 1
    if mode == "--self-test":
        if not judge(report, paras)["holds"]:
            raise SystemExit("self-test needs a run that holds")
        want = typed(report["chars"])

        def swapped(r, p):
            return r, [x.replace(want, want[:5] + want[6] + want[5] + want[7:]) for x in p]

        def lost(r, p):
            return r, [x.replace(want, want[:5] + want[6:]) for x in p]

        def doubled(r, p):
            return r, [x.replace(want, want + want) for x in p]

        def key_uncommitted(r, p):
            r = copy.deepcopy(r); r["rows"][3]["revisionMs"] = None; return r, p

        def key_missing(r, p):
            r = copy.deepcopy(r); r["rows"].pop(); return r, p

        def no_save(r, p):
            return r, []
        results = {f.__name__: judge(*f(report, paras))["holds"] for f in (swapped, lost, doubled, key_uncommitted, key_missing, no_save)}
        print(json.dumps({"selfTest": "ALL_RED" if not any(results.values()) else "SOME_HELD", "held": results}))
        return 0 if not any(results.values()) else 1
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
