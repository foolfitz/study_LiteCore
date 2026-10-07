#!/usr/bin/env python3
"""Line positions of every corpus document, per profile (SPEC-M3-paragraph-merge
20.3: the criterion that replaces section 19's tile comparison).

For each profile: one Chrome session on the product page pointed at it (the
runner's own `repointed_page`, served from a symlink mirror), every `.odt` under
test-docs/ opened through the product's file input in turn, the canvas left to
settle (two identical reads in a row), and the rows of dark ink inside the page
recorded as runs.  The canvas is the whole document, so the runs are every
line of every page.  Nothing is saved, typed or written to dist/.

Then every pair of profiles is compared document by document: same number of
runs and the same tops, or the largest difference in pixels.  Run a profile
against itself to measure what the same profile does twice (the tolerance in
20.3 is set from that, before the comparison that counts).

  compare_layout_corpus.py --profiles e2-editor-v16 e2-editor-v15-cjk-r5-ab --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import odt_paragraphs  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

HERE = pp.PROJECT

# Rows of dark ink inside the page.  The page is opaque and the surround is not
# (finding 075); columns inked down more than a fifth of the canvas are the page
# frame and are left out, with a margin, so a frame line does not join every row.
ROWS = r"""(() => {
const canvas = document.querySelector('#canvas');
const w = canvas.width, h = canvas.height;
const data = canvas.getContext('2d').getImageData(0, 0, w, h).data;
const opaque = new Int32Array(w), dark = new Int32Array(w);
for (let y = 0; y < h; y += 1) for (let x = 0; x < w; x += 1) {
  const i = (y * w + x) * 4;
  if (data[i+3] > 128) { opaque[x] += 1;
    if (data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) dark[x] += 1; }
}
let left = -1, right = -1;
for (let x = 0; x < w; x += 1) if (opaque[x] > h * 0.2) { if (left < 0) left = x; right = x; }
const frame = []; for (let x = 0; x < w; x += 1) if (dark[x] > h * 0.2) frame.push(x);
const lo = Math.max(left, 0) + 6, hi = right - 6;
const counts = [];
for (let y = 0; y < h; y += 1) { let n = 0;
  for (let x = lo; x < hi; x += 1) { if (frame.includes(x)) continue;
    const i = (y * w + x) * 4;
    if (data[i+3] > 128 && data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) n += 1; }
  counts.push(n); }
return JSON.stringify({ width: w, height: h, page: [left, right], frame: frame.length, counts });
})()"""


def runs(counts: list[int]) -> list[list[int]]:
    found, start = [], None
    for y, n in enumerate(counts + [0]):
        if n > 0 and start is None:
            start = y
        elif n == 0 and start is not None:
            found.append([start, y - 1])
            start = None
    return found


def settle(session, tries: int = 25) -> dict:
    last = None
    for _ in range(tries):
        time.sleep(0.6)
        raw = pp.evaluate(session, ROWS)
        scan = json.loads(raw) if raw else None
        if scan and last and scan["counts"] == last["counts"] and any(scan["counts"]):
            return scan
        last = scan
    return {**(last or {}), "unsettled": True}


# CJK ideographs (incl. extension A), kana, hangul.  Spec 21.2's red case
# splits the corpus by this, so the split is computed from the documents, not
# listed by hand.
CJK = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]")


def cjk_characters(document: Path) -> int | None:
    """CJK characters in the document's paragraph text; None if unreadable."""
    try:
        with zipfile.ZipFile(document) as archive:
            texts = odt_paragraphs.paragraph_texts_from_xml(archive.read("content.xml"))
    except Exception:  # noqa: BLE001 -- the three deliberately broken zips
        return None
    return sum(len(CJK.findall(text)) for text in texts)


def corpus() -> list[Path]:
    return sorted(p for p in (HERE / "test-docs").rglob("*") if p.suffix == ".odt" and p.is_file())


def measure(profile: str, documents: list[Path], timeout: float) -> dict:
    root = HERE / "dist"
    # The cutover's page (3ab4f04a), like every other candidate tool.  Both
    # arms of a comparison get the same page, so this does not bias it; it
    # keeps "the page measured" one answer across the tools.
    page, _, wasm = pp.repointed_page(pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8"),
                                      profile, root / "profiles" / profile / "sdk-manifest.json")
    mirror = Path(tempfile.mkdtemp(prefix="layout-corpus-")) / "root"
    pp.build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8")})
    folder = mirror / "layout-corpus"           # new, under the mirror ROOT: a real directory
    folder.mkdir()
    for index, document in enumerate(documents):
        (folder / f"c{index:03d}.odt").write_bytes(document.read_bytes())
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=HERE,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = {"profile": profile, "wasm": wasm[:16], "documents": {}}
    session = None
    base = f"http://127.0.0.1:{port}/e2-editor.html"

    def boot():
        nonlocal session
        if session is not None:
            session.close()
        session = pp.ChromeSession("cold")
        pp.navigate(session, base)
        return pp.wait_for(session, lambda s: s.get("state") == "ready", 300)

    try:
        pp.wait_page(base)
        out["boot"] = (boot() or {}).get("state")
        for index, document in enumerate(documents):
            name = f"c{index:03d}.odt"
            key = str(document.relative_to(HERE))
            pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", f"./layout-corpus/{name}")
                        .replace("ARG_NAME", name))
            opened = pp.wait_for(session, lambda s: (s.get("doc") or "") == name
                                 and s.get("state") in ("ready", "stopped", "expired",
                                                        "recoverable-error", "restart-required"),
                                 timeout)
            entry = {"state": (opened or {}).get("state"), "toast": (opened or {}).get("toast"),
                     "cjkCharacters": cjk_characters(document)}
            if entry["state"] == "ready":
                scan = settle(session)
                entry.update({"canvas": [scan.get("width"), scan.get("height")],
                              "page": scan.get("page"), "unsettled": scan.get("unsettled", False),
                              "runs": runs(scan.get("counts") or []),
                              "rowsSha": hashlib.sha256(json.dumps(scan.get("counts")).encode())
                              .hexdigest()[:16]})
            else:
                entry["reboot"] = (boot() or {}).get("state")
            out["documents"][key] = entry
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)
    return out


def compare(a: dict, b: dict) -> dict:
    rows = []
    for key in sorted(set(a["documents"]) | set(b["documents"])):
        x, y = a["documents"].get(key) or {}, b["documents"].get(key) or {}
        if "runs" not in x or "runs" not in y:
            rows.append({"document": key, "comparable": False,
                         "states": [x.get("state"), y.get("state")]})
            continue
        same_count = len(x["runs"]) == len(y["runs"])
        top = max((abs(p[0] - q[0]) for p, q in zip(x["runs"], y["runs"])), default=0) if same_count else None
        rows.append({"document": key, "comparable": True, "identical": x["runs"] == y["runs"],
                     "cjkCharacters": x.get("cjkCharacters"),
                     "runs": [len(x["runs"]), len(y["runs"])], "maxTopDifference": top,
                     "canvas": [x["canvas"], y["canvas"]]})
    comparable = [r for r in rows if r["comparable"]]
    return {"profiles": [a["profile"], b["profile"]], "documents": len(rows),
            "comparable": len(comparable), "identical": sum(r["identical"] for r in comparable),
            "differ": [r for r in comparable if not r["identical"]],
            "notComparable": [r for r in rows if not r["comparable"]]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True, help="a directory")
    ap.add_argument("--timeout", type=float, default=120)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    documents = corpus()
    if len(documents) < 50:      # non-vacuity: the corpus moved, not "nothing differs"
        raise SystemExit(f"only {len(documents)} .odt documents under test-docs/")
    results = []
    for index, profile in enumerate(a.profiles):
        result = measure(profile, documents, a.timeout)
        result["startedOrder"] = index
        (a.out / f"layout-{index}-{profile}.json").write_text(json.dumps(result, ensure_ascii=False))
        results.append(result)
    pairs = [compare(results[i], results[j]) for i in range(len(results))
             for j in range(i + 1, len(results))]
    (a.out / "comparison.json").write_text(json.dumps(pairs, indent=1, ensure_ascii=False))
    for pair in pairs:
        print(pair["profiles"], "comparable", pair["comparable"], "identical", pair["identical"],
              "differ", len(pair["differ"]), "notComparable", len(pair["notComparable"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
