#!/usr/bin/env python3
"""Print the per-arm table of every probe_10_14n.py report under this directory.

Numbers only, read from the reports' own fields; nothing is judged here.
  python3 -I summarize_reports.py [DIR]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent)
    for path in sorted(root.rglob("report-*.json")):
        r = json.loads(path.read_text())
        st = r.get("static", {})
        print(f"\n== {path.relative_to(root)}  mode={r.get('mode', 'host')} browser={r['browser']} "
              f"doc={r['doc']['name']} sha256[:16]={r['doc']['sha256'][:16]} "
              f"host={st.get('hostVersion')}@{st.get('hostCommit')} buildId={st.get('buildId')}"
              + (f" nohost={ {k: (v[:16] if isinstance(v, str) and len(v) > 40 else v) for k, v in r['nohost'].items()} }" if r.get("nohost") else ""))
        for run in r["runs"]:
            pf = run.get("preflight", {})
            desk = f"wallet={pf.get('kwalletLocked')} chrome={pf.get('pgrepChrome')} ff={pf.get('pgrepFirefox')} load={pf.get('load', [None])[0]} ours={len(pf.get('oursRunning', []))}"
            if run.get("fatal"):
                print(f"  {run['arm']}: FATAL {run['fatal'].strip().splitlines()[-1]}  [{desk}]")
                continue
            s = run.get("summary")
            if run["arm"] == "page-number":
                steps = run.get("steps", [])
                shown = [x for x in steps if x.get("hidden") is False]
                g = run.get("geometryAtOpen", {})
                scroll_log = run.get("scrollLog", [])
                non_paint = [e for e in scroll_log if e["k"] == "rq" and e.get("op") != "paint"]
                print(f"  page-number: at open text={g.get('text')!r} hidden={g.get('hidden')} color={g.get('color')} bg={g.get('background')} "
                      f"font={g.get('fontSize')} rect={g.get('rect')} textRect={g.get('psTextRect')} content={g.get('content', {}).get('rect') if g.get('content') else None} "
                      f"inner={g.get('inner')} statusbar={g.get('statusbarDisplay')}; steps shown={len(shown)}/{len(steps)} "
                      f"texts={[x['text'] for x in steps]}; non-paint requests during scroll={len(non_paint)}; "
                      f"ask parts={run.get('askAfterScroll', {}).get('parts') if run.get('askAfterScroll') else None}  [{desk}]")
                continue
            if not s:
                print(f"  {run['arm']}: no summary  [{desk}]")
                continue
            rs = s.get("editorResponses", [])
            comps = {}
            for x in rs:
                key = x.get("completion") or (x.get("err") or {}).get("code") if isinstance(x.get("err"), dict) else x.get("completion") or str(x.get("err"))
                comps[key] = comps.get(key, 0) + 1
            waited = [x["boundaryNoop"]["waitedMs"] for x in rs if x.get("boundaryNoop")]
            sent = run.get("sent", {})
            print(f"  {run['arm']}: keydowns={s['keydowns']} (focus {s['keydownFocus']}) beforeinputs={s['beforeinputs']} "
                  f"sent={ {k: v for k, v in sent.items() if k != 'scheduledMs' and k != 'sentMs'} } "
                  f"engineResponses={len(rs)} {comps} waitedMs={sorted(set(waited))} "
                  f"readyAgainMs={s['readyAgainMs']} generations={s['generations']} toasts={s['toasts']} "
                  f"lastLabel={s['latencyLabels'][-1]['latency'] if s['latencyLabels'] else None} "
                  f"settle={run.get('settle', {}).get('by')}/{run.get('settle', {}).get('wallSinceKeyS')}s "
                  f"limit={run.get('limit', {}).get('limit') if run.get('limit') else None}  [{desk}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
