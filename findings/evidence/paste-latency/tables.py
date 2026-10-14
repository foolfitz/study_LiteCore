#!/usr/bin/env python3
"""Markdown phase tables from the raw reports in raw/ (tool-generated, so the
README's tables cannot drift from the files).  Times are milliseconds after the
Ctrl+V keydown on the page's clock; the click column is where the pointer was
put before the paste and how long before the key.

  python3 tables.py            # every report under raw/
  python3 tables.py raw/x.json # some of them
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "wasm_sdk_probe" / "tools"))
from probe_paste_latency import phases  # noqa: E402


def fmt(value) -> str:
    if value is None:
        return "–"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return str(value)


def main() -> int:
    paths = [Path(a) for a in sys.argv[1:]] or sorted((HERE / "raw").glob("*.json"))
    rows = []
    for path in paths:
        report = json.loads(path.read_text())
        for run in report.get("runs") or []:
            p = phases(run)
            if "error" in p:
                rows.append((path.name, run, p, None))
                continue
            rows.append((path.name, run, p, report))
    print("| report | mode | browser | arm (lines/chars/CJK) | click (ms before key) | paste event | insertText sent | engine insert | getState | pill ready | last blit | getState polls before insert | autosave PUT answered | saved paragraphs |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, run, p, report in rows:
        if report is None:
            print(f"| `{name}` | {run.get('mode')} | {run.get('browser')} | {run.get('arm')} | | ERROR {p} | | | | | | | | |")
            continue
        text = run.get("text") or {}
        click = run.get("clickWhere") or ("first-line" if run.get("clickAt") else "none")
        click_col = f"{click} ({fmt(p['clickBeforeKeyMs'])})" if p.get("clickBeforeKeyMs") is not None else f"{click} (waited)"
        saves = p.get("saves") or []
        put = next((a.get("respondedAt") for s in saves for a in s.get("attempts") or [] if a.get("respondedAt") is not None), None)
        saved = (run.get("savedFile") or {}).get("paragraphs")
        print(f"| `{name}` | {run.get('mode')}{('/' + run['root']) if run.get('root') else ''} | {run.get('browser')} "
              f"| {run.get('arm')} ({text.get('lines')}/{text.get('chars')}/{text.get('cjk')}) | {click_col} "
              f"| {fmt(p['pasteEvent'])} | {fmt(p['insertTextRequest'])} | {fmt(p['engineInsertMs'])} | {fmt(p['getStateMs'])} "
              f"| {fmt(p['pillReady'])} | {fmt(p['lastBlit'])} | {p['getStateRequestsBeforeInsert']} | {fmt(put)} | {fmt(saved)} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
