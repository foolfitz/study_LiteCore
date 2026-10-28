#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.3 T4: tools/run_e2_c_product_path.py on the v24 page, unchanged, with a
wire record beside it (Chrome).

The product-path runner records no worker traffic, and T4's form-two half needs every insertText
request with its reply.  The runner is imported and run as it is; this wrapper changes two things
around it and nothing it serves:

  * Chrome only: the session class it instantiates gets, before its first navigation, a CDP
    `Page.addScriptToEvaluateOnNewDocument` observer that wraps `Worker` and keeps, for every
    insertText / replaceSelection / pasteMarkdown request, its operation, payload keys, `route`, text
    length and Date.now(), and for its reply `ok`, `method`, `completion` and the error code.  The
    records live in the page and are appended to sessionStorage on `pagehide`, so they survive the
    runner's navigations; they are read out when the runner closes the session.  No served byte
    changes (the observer is not a file).  Firefox's WebDriver session has no preload script, so a
    Firefox run has outcomes only (README: named limit).
  * stderr is teed with a wall-clock stamp on every line, so each `[step] ... <check id>` line has a
    time the reader can put the wire records between.

  python3 tools/run_v24_t4.py --browser chrome --out <new dir>

Writes <dir>/report.json (the runner's own --out), <dir>/steps.json, <dir>/wire.json (Chrome) and
the runner's four-arm directory beside report.json.  Refuses an existing <dir>.
"""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp

WATCH = ('insertText', 'replaceSelection', 'pasteMarkdown')
OBSERVER = """(() => {
  if (window.__t4wire) return;
  const KEY = '__t4wire', WATCH = new Set(%s), buffer = window.__t4wire = [];
  const push = record => buffer.push({...record, at: Date.now(), path: location.pathname});
  addEventListener('pagehide', () => {
    try { const prior = JSON.parse(sessionStorage.getItem(KEY) || '[]');
          sessionStorage.setItem(KEY, JSON.stringify(prior.concat(buffer.splice(0)))); }
    catch (error) { window.__t4lost = String(error); }
  });
  let workers = 0;
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) {
      super(url, options); const worker = `${performance.timeOrigin}-${++workers}`, ops = new Map();
      this.__t4 = {worker, ops};
      this.addEventListener('message', event => { const d = event.data;
        if (d?.kind !== 'response' || !ops.has(d.requestId)) return;
        push({kind: 'response', worker, requestId: d.requestId, operation: ops.get(d.requestId), ok: d.ok,
              method: d.result?.method ?? null, completion: d.result?.completion ?? null,
              code: d.error?.code ?? null, failureShape: d.error?.failureShape ?? null}); });
    }
    postMessage(message, ...rest) {
      if (message?.kind === 'request' && WATCH.has(message.operation)) {
        const payload = message.payload || {};
        this.__t4.ops.set(message.requestId, message.operation);
        push({kind: 'request', worker: this.__t4.worker, requestId: message.requestId, operation: message.operation,
              keys: Object.keys(payload).sort(), route: 'route' in payload ? payload.route : '<absent>',
              textLength: typeof payload.text === 'string' ? payload.text.length : null});
      }
      return super.postMessage(message, ...rest);
    }
  };
})();""" % json.dumps(list(WATCH))
DUMP = """(() => { let stored = [];
  try { stored = JSON.parse(sessionStorage.getItem('__t4wire') || '[]'); } catch (error) { return {error: String(error)}; }
  return {stored: stored.length, records: stored.concat(window.__t4wire || []), lost: window.__t4lost || null}; })()"""

WIRE = {'records': [], 'dumps': []}


class WireChrome(pp.ChromeSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call('Page.addScriptToEvaluateOnNewDocument', {'source': OBSERVER})

    def close(self):
        try:
            value = pp.evaluate(self, DUMP)
            WIRE['dumps'].append({'at': time.time(), **{k: v for k, v in value.items() if k != 'records'}})
            WIRE['records'].extend(value.get('records') or [])
        except Exception as error:  # noqa: BLE001 -- recorded; the runner's own close still runs
            WIRE['dumps'].append({'at': time.time(), 'error': f'{type(error).__name__}: {error}'})
        super().close()


class StampedStderr:
    def __init__(self, stream):
        self.stream, self.lines, self.partial = stream, [], ''

    def write(self, text):
        self.stream.write(text)
        self.partial += text
        while '\n' in self.partial:
            line, self.partial = self.partial.split('\n', 1)
            self.lines.append({'at': time.time(), 'line': line})
        return len(text)

    def flush(self):
        self.stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--browser', choices=('chrome', 'firefox'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    if args.browser == 'chrome':
        pp.ChromeSession = WireChrome
    stamped = StampedStderr(sys.stderr)
    sys.stderr = stamped
    started = time.time()
    sys.argv = ['tools/run_e2_c_product_path.py', '--browser', args.browser, '--out', str(args.out / 'report.json')]
    try:
        code = pp.main()
    finally:
        sys.stderr = stamped.stream
        (args.out / 'steps.json').write_text(json.dumps({'startedAt': started, 'endedAt': time.time(), 'lines': stamped.lines},
                                                        indent=1, ensure_ascii=False) + '\n')
        if args.browser == 'chrome':
            (args.out / 'wire.json').write_text(json.dumps(WIRE, indent=1, ensure_ascii=False) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
