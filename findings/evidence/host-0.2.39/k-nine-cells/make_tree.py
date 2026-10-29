#!/usr/bin/env python3
"""Build a scratch tree that serves a shipped host package's product with a chosen commit's tools.

  make_tree.py <commit> <target-dir> <receipt.json> [package-archive-dir]

`git archive <commit> wasm_sdk_probe` into <target-dir>; its dist/ is a symlink mirror of the live
dist with the package's files (default: the 0.2.26 package) decoded and written as real files after a sha256 check
against the package MANIFEST. Directories on a package path are real; everything else is a
symlink, so nothing under the live dist is copied or written. Refuses an existing target.
"""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
LIVE_DIST = ROOT / 'wasm_sdk_probe/dist'
DEFAULT_PACKAGE = ROOT / 'wasm_sdk_probe/build/archive/host-0.2.25-engine-f5f0df762e1855f2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    commit, target, receipt = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    package = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else DEFAULT_PACKAGE
    target.mkdir(parents=True, exist_ok=False)
    resolved = subprocess.check_output(['git', 'rev-parse', commit], cwd=ROOT, text=True).strip()
    archive = subprocess.run(['git', 'archive', resolved, 'wasm_sdk_probe'], cwd=ROOT, check=True, capture_output=True).stdout
    subprocess.run(['tar', '-x', '-C', str(target)], input=archive, check=True)
    project = target / 'wasm_sdk_probe'
    dist = project / 'dist'
    if dist.exists():
        raise SystemExit('archived tree unexpectedly carries dist/')
    manifest = json.loads((package / 'MANIFEST.json').read_bytes())
    payloads = {}
    for relative, record in manifest['files'].items():
        data = gzip.decompress((package / 'files' / (relative + '.gz')).read_bytes())
        if sha(data) != record['sha256'] or len(data) != record['bytes']:
            raise SystemExit('package member does not decode to its MANIFEST record: ' + relative)
        payloads[relative] = data
    real_dirs = {Path('.')}
    for relative in payloads:
        parent = Path(relative).parent
        while parent != Path('.'):
            real_dirs.add(parent)
            parent = parent.parent
    links = 0

    def walk(relative):
        nonlocal links
        (dist / relative).mkdir(parents=True, exist_ok=True)
        live = LIVE_DIST / relative
        names = {p.name for p in live.iterdir()} if live.is_dir() else set()
        for name in sorted(names):
            child = relative / name if relative != Path('.') else Path(name)
            if child.as_posix() in payloads:
                continue
            if child in real_dirs:
                walk(child)
            else:
                (dist / child).symlink_to(LIVE_DIST / child)
                links += 1
        for child in sorted(real_dirs):
            if child.parent == relative and child != relative and not (dist / child).exists():
                walk(child)

    walk(Path('.'))
    for relative, data in payloads.items():
        path = dist / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    runner = project / 'tools/run_e2_c_product_path.py'
    record = {
        'commit': resolved, 'target': str(target), 'runnerSha256': sha(runner.read_bytes()),
        'packageBuildId': manifest['buildId'], 'package': str(package.relative_to(ROOT)),
        'pageSha256': sha((dist / 'e2-editor-app.js').read_bytes()),
        'materialized': {r: sha(d) for r, d in sorted(payloads.items())},
        'symlinksToLiveDist': links,
        'webEqualsPackage': {r: (project / 'web' / r).is_file() and sha((project / 'web' / r).read_bytes()) == sha(d)
                             for r, d in sorted(payloads.items()) if not r.startswith('profiles/')},
    }
    receipt.write_text(json.dumps(record, indent=1) + '\n')
    print(json.dumps({k: record[k] for k in ('commit', 'runnerSha256', 'packageBuildId', 'pageSha256', 'symlinksToLiveDist')}))


if __name__ == '__main__':
    main()
