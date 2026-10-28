#!/usr/bin/env python3
"""Observe the legacy K v8 repoint on the unchanged v24 page, with a real v24 positive control."""
import argparse
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / 'wasm_sdk_probe'
sys.path.insert(0, str(SDK / 'tools'))
import run_v24_page_gates as gate
from r7_support import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); args.out = args.out.resolve(); args.out.mkdir(parents=True, exist_ok=False)
    source = (gate.DIST / 'e2-editor-app.js').read_text()
    manifest = gate.DIST / 'profiles/e2-editor-v8/sdk-manifest.json'
    repointed, before, wasm = gate.pp.repointed_page(source, 'e2-editor-v8', manifest)
    report = {'scope': 'Legacy K premise diagnostic only; zero K credit; no gate bypass',
              'argv': sys.argv, 'sourceSha256': gate.sha(source.encode()), 'v8PageSha256': gate.sha(repointed.encode()),
              'v8ManifestSha256': gate.sha(manifest.read_bytes()), 'pinBefore': before, 'v8WasmSha256': wasm,
              'v8TypedInsert': json.loads(manifest.read_bytes())['editorContract'].get('typedInsert'),
              'expectedGateCodeByBoundSource': 'PAGE_BUILD_MISMATCH', 'runs': []}
    html = (gate.DIST / 'e2-editor.html').read_text()
    def write():
        (args.out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    with gate.common.browser_lock('host-v24-legacy-v8-gate'):
        report['preRun'] = gate.common.pre_run_checks(); report['foreignCpu'] = gate.common.foreign_cpu(); write()
        if report['preRun']['refuse'] or not report['foreignCpu'].get('ok'):
            raise SystemExit('pre-run refusal; no browser')
        for arm, page in (('control', source), ('legacy-v8', repointed)):
            mirror = args.out / ('mirror-' + arm)
            gate.pp.build_mirror(gate.DIST, mirror, {'e2-editor.html': gate.common.inject(html, [gate.OBSERVER]).encode(),
                                                     'e2-editor-app.js': page.encode()})
            cell = {'arm': arm, 'browser': 'chrome'}; session = None
            try:
                with gate.common.served(mirror) as base:
                    session = gate.common.open_browser('chrome')
                    cell.update(gate.run_arm(session, 'chrome', base, arm))
                if arm == 'control':
                    cell['inspection'] = gate.verdict(cell)
                else:
                    rec = cell['record']; inserts = [q for q in rec['requests'] if q['message']['operation'] == 'insertText']
                    refused = cell['settled']['expired'] and not inserts
                    cell['inspection'] = {'verdict': 'EXPECTED_REFUSAL' if refused else 'NOT_ESTABLISHED',
                                          'expiredAtSettlement': cell['settled']['expired'], 'insertRequests': len(inserts),
                                          'gateCodeIsSourceAttribution': True}
            except Exception:
                cell['fatal'] = traceback.format_exc()
                if session is not None:
                    cell['lastState'] = evaluate(session, gate.PAGE_STATE)
                cell['inspection'] = {'verdict': 'NOT_ESTABLISHED'}
            finally:
                if session is not None:
                    cell['cleanup'] = gate.common.close_browser(session)
                path = args.out / (arm + '.json'); path.write_text(json.dumps(cell, indent=1, ensure_ascii=False) + '\n')
                report['runs'].append({'path': path.name, 'sha256': gate.sha(path.read_bytes()), 'inspection': cell['inspection']}); write()
            if cell['inspection']['verdict'] not in ('PASS', 'EXPECTED_REFUSAL'):
                raise SystemExit('diagnostic did not establish its declared observation')
    report['verdict'] = 'LEGACY_V8_CONTROL_REFUSED'; write(); print(json.dumps(report['runs'], indent=1))


if __name__ == '__main__':
    main()
