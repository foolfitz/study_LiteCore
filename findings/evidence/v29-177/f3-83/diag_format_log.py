#!/usr/bin/env python3
"""A diagnostic, not F3: the same run with every action, format value and caret event the page exchanges with the worker logged,
collected after each save (a later check may reload the page).  With the clear-wait change of diag_clear_wait.py, which removes
that race, so that what is left is what is left.  Nothing is edited, nothing here is a count.
  diag_format_log.py --browser firefox --out DIR       DIR/report.json as F3, DIR/format-log.json
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "wasm_sdk_probe/tools"))
import run_v83_f3_clipboard as r  # noqa: E402

LABEL = 'lambda st: "清除格式" in (st.get("latency") or ""), 30)'
DONE = 'lambda st: "已清除" in (evaluate(session, READ_TOAST) or ""), 30)'
r.REPLACEMENTS = r.REPLACEMENTS + (
    ("diag-clear-wait-normalise",
     '                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + LABEL,
     '                evaluate(session, CLEAR_TOAST)\n                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + DONE),
    ("diag-clear-wait-accumulate",
     '        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + LABEL,
     '        evaluate(session, CLEAR_TOAST)\n        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + DONE),
)
OBSERVER = b"""<script>
(() => { const log = []; window.__fmt = log; const now = () => Math.round(performance.now() * 10) / 10;
  const find = (v, d) => { if (!v || typeof v !== 'object' || d > 4 || ArrayBuffer.isView(v)) return null;
    if (v.format && typeof v.format === 'object' && 'bold' in v.format) return v;
    for (const k of Object.keys(v)) { if (k === 'pixels') continue; const r = find(v[k], d + 1); if (r) return r; } return null; };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(u, o) { super(u, o); this.addEventListener('message', (e) => { const d = e.data, s = find(d, 0);
      if (s) { const f = s.format; log.push([now(), d.kind || '?', s.source ?? null, s.sourceSequence ?? null, f.bold, f.italic, f.underline, f.strikethrough ?? f.strikeout, f.stale ?? s.formatStateStale ?? null]); } }); }
    postMessage(m, ...r) { if (m && m.kind === 'request' && m.operation !== 'paint')
        log.push([now(), 'request', [m.operation, m.payload?.action ?? null, m.payload?.enabled ?? null, typeof m.payload?.text === 'string' ? m.payload.text : ''].join(' ')]);
      return super.postMessage(m, ...r); } };
})();
</script>"""
LOG = []
OUT = {}
original = r.load


def load():
    m = original()
    build = m.build_mirror

    def mirror(source, target, overrides):
        raw = overrides.get("e2-editor.html") or (Path(source) / "e2-editor.html").read_bytes()
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return build(source, target, {**overrides, "e2-editor.html": raw.replace(b"<script", OBSERVER + b"<script", 1)})
    m.build_mirror = mirror
    capture = m.capture_save

    def saving(session, index, timeout=90):
        out = capture(session, index, timeout)
        try:
            LOG.extend(m.evaluate(session, "(() => (window.__fmt ? window.__fmt.splice(0) : []))()") or [])
            OUT["path"].write_text(json.dumps(LOG) + "\n")
        except Exception as error:  # noqa: BLE001 -- a diagnostic must not change the run
            LOG.append(["collect-error", str(error)[:200]])
        return out
    m.capture_save = saving
    return m


r.load = load
OUT["path"] = Path(sys.argv[sys.argv.index("--out") + 1]).parent / (Path(sys.argv[sys.argv.index("--out") + 1]).name + ".format-log.json")
raise SystemExit(r.main())
