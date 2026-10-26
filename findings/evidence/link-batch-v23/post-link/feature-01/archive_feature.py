#!/usr/bin/env python3
"""One-shot archive of the audited owner-linked ABI6 candidate; no build."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
SDK = ROOT / 'wasm_sdk_probe'
ARCHIVE = SDK / 'build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6'
EXPECTED = {
    'exports.txt': '78d4750fd2f98747ac2c677d9459873d4cf253ba14cfc86aa3f05e76b178a2a6',
    'probe.js': '4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e',
    'probe.wasm': 'fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658',
    'sdk-manifest.json': '2b23901ff94edd4c52611d03a31242c9ecfbf33fcf89835c1af13ac04a1e2a91',
    'sdk-worker.js': '3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    audit_path = OUT / 'audit-01/audit.json'
    audit = json.loads(audit_path.read_text())
    if audit['status'] != 'PASS' or audit['problems']:
        raise ValueError('post-link audit is not PASS')
    if ARCHIVE.exists():
        raise FileExistsError('preserve existing archive; never overwrite or retry')
    sources = {name: SDK / ('build/e2/editor-v23' if name == 'exports.txt'
                           else 'dist/profiles/e2-editor-v23') / name for name in EXPECTED}
    for name, path in sources.items():
        if sha(path) != EXPECTED[name]:
            raise ValueError('actual source identity differs: ' + name)
    ARCHIVE.mkdir()
    rows = []
    for name, source in sources.items():
        target = ARCHIVE / name
        shutil.copyfile(source, target)
        if sha(target) != EXPECTED[name] or sha(source) != EXPECTED[name]:
            raise ValueError('copy/source reread differs; preserve partial archive: ' + name)
        rows.append({'name': name, 'source': source.relative_to(ROOT).as_posix(),
                     'archive': target.relative_to(ROOT).as_posix(),
                     'bytes': target.stat().st_size, 'sha256': EXPECTED[name]})
    sums = ''.join(f'{digest}  {name}\n' for name, digest in EXPECTED.items())
    attribution = '''# ABI6 feature candidate attribution

This archive contains the exact owner-linked `e2-editor-v23` candidate: editor ABI6, 23 public actions, and select-all present with no granted gestures. It is a feature candidate, not a feature acceptance or host deployment verdict.

The WASM identity is `fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658`; the isolated worker identity is `3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5`. The worker derives from frozen v22 `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`, with the reviewed ABI6 six-move extension validation. No diagnostic tail or diagnostic entry point is included. Existing public IDs and the 36 inherited public function exports are preserved.

The five bound artifacts are probe.js, probe.wasm, sdk-worker.js, sdk-manifest.json and exports.txt. SHA256SUMS binds their actual bytes; the archive name identifies both WASM and worker. Never overwrite this identity. The shared Calc worker and all previous archives/profiles were unchanged by the owner build.

Evidence: `findings/evidence/link-batch-v23/post-link/feature-01/audit-01/audit.json`, the copied actual build log in that directory, and the one-shot archive receipt `feature-01/archive.json`. Runtime acceptance remains subject to final shell binding, readiness, required independent references and the fixed feature protocol.
'''
    for name, value in (('SHA256SUMS', sums), ('ATTRIBUTION.md', attribution)):
        (ARCHIVE / name).write_text(value)
        (OUT / name).write_text(value)
    result = {'status': 'PASS', 'archive': ARCHIVE.relative_to(ROOT).as_posix(),
              'audit': audit_path.relative_to(ROOT).as_posix(), 'auditSha256': sha(audit_path),
              'artifacts': rows,
              'metadata': [{'name': name, 'sha256': sha(ARCHIVE / name)}
                           for name in ('SHA256SUMS', 'ATTRIBUTION.md')],
              'runtimeAcceptance': 'NOT_ESTABLISHED', 'productBuildExecutedByAgent': False}
    (OUT / 'archive.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
