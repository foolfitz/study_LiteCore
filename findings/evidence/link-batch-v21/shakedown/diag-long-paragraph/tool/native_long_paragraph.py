#!/usr/bin/env python3
"""Long-paragraph diagnosis, native arm: round 2's probe and runner, reused, with this diagnosis's corpus.

The native probe is round 2's `md_paste_probe2.cpp`, rebuilt with g++ exactly as its README says
(findings/evidence/link-batch-v21/native/markdown-paste/round-2/README.md "Reproduce"); its runner is
round 2's `run_arms2.py`, IMPORTED (not copied): `run_one()` with round 1's P1 (Ctrl+Home in the empty
template), its fresh profile per process, `env -i`, `nice`, `timeout 120`, the probe's 20 s watchdog,
the wait for other LOK processes, and its summary.json.  The only thing replaced is `corpus_path()`, so
that the corpus names resolve to this diagnosis's files (written by corpora.py, byte for byte the WASM
cells' inputs).

  native_long_paragraph.py PROBE2 SCRATCH OUT_DIR CORPUS_DIR ARM_ID:MIME:CORPUS_NAME [...] [--runs=N]

  MIME  md | plain   (text/markdown;charset=utf-8 | text/plain;charset=utf-8)

Writes OUT_DIR/<ARM_ID>/run<k>/ (round 2's layout) and adds `paragraphsAfter` (count and lengths of the
body paragraphs in after.fodt) to each summary.json.  A run whose summary.json exists is not rerun.
"""
from __future__ import annotations

import gzip
import http.server
import json
import os
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
ROUND2 = REPO / "findings/evidence/link-batch-v21/native/markdown-paste/round-2/tool"
sys.path.insert(0, str(ROUND2))
import run_arms2  # noqa: E402

MIMES = {"md": "text/markdown;charset=utf-8", "plain": "text/plain;charset=utf-8"}
NS = {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
      "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}


def paragraphs(fodt_gz: Path) -> dict:
    root = ET.fromstring(gzip.decompress(fodt_gz.read_bytes()))
    body = root.find("office:body/office:text", NS)
    lengths = []
    for el in body.iter():
        if el.tag in ("{%s}p" % NS["text"], "{%s}h" % NS["text"]):
            spaces = sum(int(s.get("{%s}c" % NS["text"], "1")) for s in el.iter("{%s}s" % NS["text"]))
            lengths.append(len("".join(el.itertext())) + spaces)
    return {"count": len(lengths), "lengths": lengths[:20], "longest": max(lengths) if lengths else 0,
            "cjkChars": "".join(body.itertext()).count("中")}


def main(argv: list[str]) -> int:
    runs = [int(a.split("=", 1)[1]) for a in argv if a.startswith("--runs=")]
    args = [a for a in argv[1:] if not a.startswith("--runs=")]
    probe, scratch, out_dir, corpus_dir = args[:4]
    corpus_dir = Path(corpus_dir)
    run_arms2.corpus_path = lambda name: str(corpus_dir / f"{name}.md")      # the one replacement
    arms = []
    for spec in args[4:]:
        arm_id, mime, corpus = spec.split(":")
        if not (corpus_dir / f"{corpus}.md").is_file():
            raise SystemExit(f"no corpus {corpus_dir / corpus}.md")
        arms.append({"id": arm_id, "position": "P1", "corpus": corpus, "mime": MIMES[mime], "lang": run_arms2.ZH,
                     "runs": runs[0] if runs else 3, "note": "diag-long-paragraph"})
    listening = {}
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", run_arms2.LISTENER_PORT), run_arms2.Listener)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        run_arms2.Closer(run_arms2.CLOSER_PORT)
        listening = {"listener": run_arms2.LISTENER_PORT, "closer": run_arms2.CLOSER_PORT}
    except OSError as error:
        listening = {"error": f"{type(error).__name__}: {error}"}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "runner.log"), "a") as log:
        log.write("=== %s start, probe sha256 %s, listening %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                                                    run_arms2.sha(probe), listening))
        for arm in arms:
            for k in range(1, arm["runs"] + 1):
                run_arms2.run_one(probe, scratch, out_dir, arm, k, log)
                run_dir = Path(out_dir) / arm["id"] / f"run{k}"
                summary_path = run_dir / "summary.json"
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                if "paragraphsAfter" not in summary and (run_dir / "after.fodt.gz").exists():
                    summary["paragraphsAfter"] = paragraphs(run_dir / "after.fodt.gz")
                    summary["probeSha256"] = run_arms2.sha(probe)
                    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
                print(arm["id"], k, {key: summary.get(key) for key in ("returncode", "processSeconds", "pasteReturned",
                                                                     "pasteCallMs", "blocked", "probeError")},
                      summary.get("paragraphsAfter"), flush=True)
        log.write("=== %s end\n" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
