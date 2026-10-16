#!/usr/bin/env python3
"""Summarise the long-paragraph diagnosis's reports into one table (read-only).

  summarize.py OUT_DIR            prints a Markdown table of every browser cell and every native run,
                                  and writes nothing

Per browser cell: report label, cell, outcome (diag_long_paragraph.classify), attempt seconds, the SDK
error code, whether the worker answered afterwards, the saved document's paragraph count / longest
paragraph / page count (meta.xml of the saved ODT in docs-<label>/), the pthread exception's frame count
and how many times SwContentFrame::MakeAll's ring frame ($func83813, out/function-map.json) appears in it.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
RING = "$func83813"          # SwContentFrame::MakeAll (out/function-map.json)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from diag_long_paragraph import classify  # noqa: E402  (the current labels; a report keeps the label of its run)


def pages(odt: Path) -> int | None:
    try:
        meta = zipfile.ZipFile(odt).read("meta.xml").decode("utf-8")
    except (KeyError, OSError, zipfile.BadZipFile):
        return None
    found = re.search(r'meta:page-count="(\d+)"', meta)
    return int(found.group(1)) if found else None


def browser_rows(out: Path):
    for path in sorted(out.glob("report-*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        label = report["label"]
        for cell in report["cells"]:
            attempt = cell.get("attempt") or {}
            error = attempt.get("error") if isinstance(attempt.get("error"), dict) else {}
            code = (error or {}).get("code")
            if attempt.get("route", "").startswith("ctrlv"):
                last = (attempt.get("pastes") or [{}])[-1]
                code = (last.get("response") or {}).get("code") or ("no rq" if not last.get("insertTextRequested") else None)
            saved = cell.get("saved") or {}
            page_count = None
            if saved.get("file"):
                page_count = pages(out / f"docs-{label}" / saved["file"])
            exc = [e for e in (cell.get("cdp") or {}).get("exceptions", []) if (e.get("url") or "").endswith("probe.js")]
            frames = exc[0]["frameCount"] if exc else None
            ring = sum(1 for f in exc[0]["frames"] if f.get("fn") == RING) if exc else None
            first = (exc[0]["description"].splitlines()[0] if exc else "")[:48]
            outcome = classify(cell)
            if outcome != cell.get("outcome"):
                outcome = f"{outcome} (stored: {cell.get('outcome')})"
            yield (label, report["browser"], cell["spec"]["cell"], outcome, cell.get("attemptSeconds"), code,
                   (cell.get("alive") or {}).get("answered"), saved.get("paragraphs"), saved.get("longest"), page_count,
                   frames, ring, first, cell.get("runnerError"))


def native_rows(out: Path):
    for summary_path in sorted((out / "native").glob("*/run*/summary.json")):
        s = json.loads(summary_path.read_text(encoding="utf-8"))
        after = summary_path.parent / "after.fodt.gz"
        page_count = None
        if after.exists():
            found = re.search(rb'meta:page-count="(\d+)"', gzip.decompress(after.read_bytes()))
            page_count = int(found.group(1)) if found else None
        p = s.get("paragraphsAfter") or {}
        yield (s["arm"]["id"], s["run"], s["arm"]["mime"], s.get("returncode"), s.get("pasteReturned"),
               s.get("pasteCallMs"), s.get("processSeconds"), p.get("count"), p.get("longest"), page_count,
               s.get("blocked"), s.get("probeError"))


def main(argv: list[str]) -> int:
    out = Path(argv[1])
    print("| report | browser | cell | outcome | attempt s | code | worker answers after | paragraphs | longest | pages | pthread frames | MakeAll ring | first line | runner error |")
    print("|" + "---|" * 14)
    for row in browser_rows(out):
        print("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    print()
    print("| native arm | run | mime | rc | paste returned | paste ms | process s | paragraphs | longest | pages | blocked | probe error |")
    print("|" + "---|" * 12)
    for row in native_rows(out):
        print("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
