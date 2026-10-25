#!/usr/bin/env python3
"""Run only the separately declared public S-init 72-cell comparison.

Own local HTTP/browser processes; no host, services, make or frozen writes.
"""
import argparse
import base64
import json
import hashlib
from pathlib import Path
import shutil
import sys
import time
import traceback
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v21_shakedown_common as common
import run_e2_c_product_path as pp
from v23_s_init_cases import PROJECT, CASES, PROFILES, BROWSERS, ROUNDS, REGION, FIXTURES
from v23_s_init_cases import fixture_identity, profile_identity, instrument_identity, sha, served_sources, verify_mirror, config_bytes


# Each base64 reply stays well below the existing 1 MiB transport limit.
EXPORT_CHUNK_BYTES = 64 * 1024
EXPORT_BEGIN = """(async () => {
  if (!globalThis.__sinit?.complete) throw new Error('S-init snapshot incomplete');
  const bytes = new TextEncoder().encode(JSON.stringify(globalThis.__sinit));
  globalThis.__sinitExportBytes = bytes;
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return {byteLength: bytes.length, sha256: Array.from(new Uint8Array(digest),
    x => x.toString(16).padStart(2, '0')).join('')};
})()"""


def export_page(session, evaluate=None):
    """Freeze once; transfer UTF-8 bytes losslessly and verify before parsing."""
    evaluate = evaluate or pp.evaluate
    metadata = evaluate(session, EXPORT_BEGIN)
    length = metadata['byteLength']
    if type(length) is not int or length <= 0:
        raise ValueError('invalid snapshot byte length')
    chunks = []
    for offset in range(0, length, EXPORT_CHUNK_BYTES):
        end = min(offset + EXPORT_CHUNK_BYTES, length)
        encoded = evaluate(session, f"""(() => {{
          const bytes = globalThis.__sinitExportBytes.subarray({offset}, {end});
          let binary = '';
          for (let i = 0; i < bytes.length; i += 8192)
            binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
          return btoa(binary);
        }})()""")
        chunk = base64.b64decode(encoded, validate=True)
        if len(chunk) != end - offset:
            raise ValueError(f'snapshot chunk length mismatch at {offset}')
        chunks.append(chunk)
    raw = b''.join(chunks)
    if len(raw) != length or hashlib.sha256(raw).hexdigest() != metadata['sha256']:
        raise ValueError('snapshot length/hash mismatch')
    page = json.loads(raw.decode('utf-8'))
    evaluate(session, 'delete globalThis.__sinitExportBytes')
    return page, metadata


def mirror(target, config):
    target.mkdir(parents=True, exist_ok=False)
    (target / 'profiles').symlink_to(PROJECT / 'dist/profiles', target_is_directory=True)
    for name in ('sdk', 'editor-shell', 'editor-shell-v2'):
        (target / name).symlink_to(PROJECT / name, target_is_directory=True)
    shutil.copyfile(PROJECT / 'web/v23-s-init.html', target / 'e2-editor.html')
    shutil.copyfile(PROJECT / 'web/v23-s-init.js', target / 'v23-s-init.js')
    # Include transitive imports outside the three primary SDK/session trees.
    # The same executable graph feeds verification; no second directory list.
    for name in config['servedSources']:
        destination = target / name
        if destination.exists(): continue
        source = PROJECT / name
        if not source.is_file(): raise ValueError(f'missing served source: {source}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source)

    shutil.copytree(FIXTURES, target / 's-init-fixtures')
    (target / 's-init-config.json').write_bytes(config_bytes(config))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--v22-wasm-sha256', required=True)
    p.add_argument('--candidate-wasm-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--preparation-only', action='store_true', help='one uncounted round of selected cells')
    p.add_argument('--case-id', choices=tuple(CASES))
    p.add_argument('--browser', choices=BROWSERS)
    p.add_argument('--profile', choices=PROFILES)
    a = p.parse_args()
    if not a.preparation_only and any((a.case_id, a.browser, a.profile)):
        p.error('cell filtering requires --preparation-only; counted population is fixed')
    pins = dict(zip(PROFILES, (a.v22_wasm_sha256, a.candidate_wasm_sha256)))
    config = {'cases': CASES, 'region': REGION, 'fixtures': fixture_identity(),
              'profiles': {profile: profile_identity(profile, pins[profile]) for profile in PROFILES},
              'instrumentSha256': instrument_identity(), 'servedSources': served_sources()}
    assert config['profiles'][PROFILES[0]]['coreCommit'] == config['profiles'][PROFILES[1]]['coreCommit'], 'core identity differs'
    # Resource paths and bytes must be identical inputs to the comparison.
    resource_sets = [{k:v for k,v in config['profiles'][profile]['artifacts'].items() if k.startswith('../resources/')} for profile in PROFILES]
    assert resource_sets[0] and resource_sets[0] == resource_sets[1], 'resource inputs differ'
    a.output.mkdir(parents=True, exist_ok=False)
    target = a.output.resolve() / 'mirror'; mirror(target, config)
    report = {'schema': 1, 'counted': not a.preparation_only, 'config': config,
              'mirrorBindings': verify_mirror(target, config), 'runs': []}
    output = a.output / 'report.json'
    def write(): output.write_text(json.dumps(report, indent=2) + '\n')
    write()
    with common.browser_lock('run_v23_s_init'):
        report['preRun'] = common.pre_run_checks(); report['foreignCpu'] = common.foreign_cpu()
        if not report['foreignCpu'].get('ok'):
            write(); raise SystemExit('foreign CPU load; no browser started')
        with common.served(target) as base:
            for browser in ((a.browser,) if a.browser else BROWSERS):
                for n in ((1,) if a.preparation_only else ROUNDS):
                    for case_id in ((a.case_id,) if a.case_id else CASES):
                        for profile in ((a.profile,) if a.profile else PROFILES):
                            print(f'{browser} r{n} {case_id} {profile}', flush=True)
                            cell = {'browser': browser, 'round': n, 'caseId': case_id, 'profile': profile}
                            session = None
                            try:
                                assert profile_identity(profile, pins[profile]) == config['profiles'][profile], 'profile bytes changed'
                                assert fixture_identity() == config['fixtures'], 'fixture bytes changed'
                                assert instrument_identity() == config['instrumentSha256'], 'instrument sources changed'
                                assert verify_mirror(target, config) == report['mirrorBindings'], 'mirror changed'
                                session = common.open_browser(browser)
                                pp.navigate(session, base + '?' + urlencode({'profile': profile, 'caseId': case_id}))
                                deadline = time.monotonic() + 480
                                while time.monotonic() < deadline:
                                    if pp.evaluate(session, 'Boolean(globalThis.__sinit?.complete)'): break
                                    time.sleep(0.25)
                                cell['page'], cell['pageTransfer'] = export_page(session)
                                if not cell['page'] or not cell['page'].get('complete'):
                                    cell['fatal'] = 'outer observation bound; not an SDK recovery'
                            except Exception: cell['fatal'] = traceback.format_exc()
                            finally:
                                if session is not None: cell['cleanup'] = common.close_browser(session)
                                name = f'{browser}-r{n}-{case_id}-{profile}.json'
                                path = a.output / name
                                path.write_text(json.dumps(cell) + '\n')
                                report['runs'].append({'path': name, 'sha256': sha(path)})
                                write()
    report['postIdentity'] = {'profiles': {profile: profile_identity(profile, pins[profile]) for profile in PROFILES},
                              'fixtures': fixture_identity(), 'instrumentSha256': instrument_identity()}
    assert report['postIdentity'] == {k: config[k] for k in ('profiles', 'fixtures', 'instrumentSha256')}, 'inputs changed during cohort'
    assert verify_mirror(target, config) == report['mirrorBindings'], 'mirror changed after cohort'
    write(); print(output)
    return 0
if __name__ == '__main__': raise SystemExit(main())
