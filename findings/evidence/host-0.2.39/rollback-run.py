#!/usr/bin/env python3
"""Run the prepared exact 0.2.38 engine rollback inside the recorded owner slot, with before/after reads.

Uses install-0.2.39.py's own slot() and snapshot() (current protected documents, full lock rows),
then rollback-package.sh unchanged. Never clears locks or touches owner files.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('host039_install', OUT / 'install-0.2.39.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    release = json.loads((OUT / 'release.json').read_bytes())
    owner_slot, states = m.slot()
    from check_m3_skeleton_open import Instance
    instance = Instance(m.HOST)
    stamp = datetime.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')
    evidence = OUT / ('rollback-' + stamp)
    evidence.mkdir(exist_ok=False)
    before = m.snapshot(instance)
    (evidence / 'before.json').write_text(json.dumps({'snapshot': before, 'states': states, 'slot': owner_slot},
                                                     indent=1, ensure_ascii=False) + '\n')
    run = subprocess.run(['bash', str(OUT / 'rollback-package.sh')], capture_output=True, text=True, timeout=600)
    (evidence / 'rollback.json').write_text(json.dumps({'exit': run.returncode, 'stdout': run.stdout,
                                                        'stderr': run.stderr}, indent=1) + '\n')
    if run.returncode:
        raise SystemExit('rollback-package.sh failed; evidence kept in ' + str(evidence))
    after = m.snapshot(instance)
    (evidence / 'after.json').write_text(json.dumps(after, indent=1, ensure_ascii=False) + '\n')
    manifest = json.loads((m.HOST / 'engine/MANIFEST.json').read_bytes())
    status = json.loads(m.command(['ddev', 'occ', 'status', '--output=json']))
    version = m.command(['ddev', 'occ', 'config:app:get', 'litecore', 'installed_version'])
    base = json.loads(m.command(['ddev', 'describe', '-j']))['raw']['primary_url']
    routes = {page: m.command(['curl', '-sk', '-o', '/dev/null', '-w', '%{http_code}',
                               base + '/index.php/apps/litecore/r/' + page + '?fileId=0'])
              for page in ('e2-editor.html', 'ods-viewer.html', 'ods-editor.html')}
    exact = m.tree(m.HOST / 'engine') == m.tree(Path(release['oldArchive']))
    holds = (before == after and exact and manifest['buildId'] == release['oldBuildId']
             and not status.get('maintenance') and not status.get('needsDbUpgrade')
             and all(code in ('401', '302', '303') for code in routes.values()))
    result = {
        'verdict': 'ENGINE_ROLLED_BACK' if holds else 'CHECK',
        'engineBuildId': manifest['buildId'], 'engineEqualsOldArchive': exact,
        'hostCommit': m.command(['git', 'rev-parse', 'HEAD']), 'hostLabel': version,
        'preservedDocumentsAndLocks': before == after, 'maintenance': status.get('maintenance'),
        'needsDbUpgrade': status.get('needsDbUpgrade'), 'routesUnauthenticated': routes, 'globalLockWrites': False,
    }
    (evidence / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
