"""SPEC-M3-link-batch-v25 6.3 F4: what names the build under test for the v25 four-arm run.

v24's `tools/v24_feature_selection_cases.py` hard-codes v24's profile, page and generation 77 and is bound
by v24's counts, so it is not edited.  This is its `shell()` / `identity()` with v25's names: profile
e2-editor-v25 pinned to the v25 archive, ABI 6 with the typedInsert leaf (spec v25 4.5: every leaf equals
v24's), the live shell equal to frozen generation 78 (`9450e5340`), the page 6e66c930 (`e06d10a1b`).
"""
import json

from v23_feature_selection_cases import PROJECT, sha
import build_e2_c_shell_bundle as shell_bundle

PROFILE = 'e2-editor-v25'
TYPED_INSERT = 'document-sdk-insert-typed-text'
PAGE_SHA256 = '6e66c930fe3d861903cfa6dfd16d000523298e934fae444385d4fe37d484c7cb'
CANDIDATE_SHELL_DIGEST = '550b68bfcc0ba7b6d8a71c4fbea6c7d6eba6b1de35edeaf4cddf26f40fcde8e4'
BUNDLE = 'e2/editor-shell-v2-bundle-v78.json'
BUNDLE_FILE_SHA256 = '91bc4f680514dcd9272ca0142f86cfe82e1c58e791ae93a61f5665473fabc937'
ARTIFACT_PINS = {
    'probe.wasm': '44cb15ea8d36f0e0191e007179769b6bcb468e3d084cb260c645e6127630d193',
    'probe.js': 'ed1d9a55357a0a25d44224fbbdcb1fc26df0a1c64a1ae2a769761f9bf3784738',
    'sdk-worker.js': '75557b220b0d29dfa222a3dd4c3fbde54403034676dc8b7b1a9b41934c218b0c',
    'sdk-manifest.json': 'e7780061471ffc81ccb4240e502f6343ee42c3312e7871efb6efa38066766519'}
ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v25-44cb15ea-worker-75557b22'


def shell():
    """The live shell: the bundle tool's own computation, equal to frozen generation 78."""
    state = shell_bundle.compute(PROJECT)
    if state['digest'] != CANDIDATE_SHELL_DIGEST:
        raise ValueError('shell digest is not generation 78: ' + state['digest'])
    if sha(PROJECT / BUNDLE) != BUNDLE_FILE_SHA256:
        raise ValueError('generation 78 manifest differs: ' + BUNDLE)
    frozen = json.loads((PROJECT / BUNDLE).read_text())
    if frozen['bundleSha256'] != state['digest'] or {r['path']: r['sha256'] for r in frozen['included']} != state['hashes']:
        raise ValueError('live shell is not frozen generation 78')
    for path in state['included']:
        if state['distHashes'].get(path) != state['hashes'][path]:
            raise ValueError('shell source/dist differs: ' + path)
    if state['hashes'][shell_bundle.ENTRYPOINT.as_posix()] != PAGE_SHA256:
        raise ValueError('page is not the v25 cutover page')
    return state


def identity():
    directory = PROJECT / 'dist/profiles' / PROFILE
    for name, expected in ARTIFACT_PINS.items():
        if sha(directory / name) != expected or sha(ARCHIVED_PROFILE / name) != expected:
            raise ValueError('v25 profile/archive identity differs: ' + name)
    manifest = json.loads((directory / 'sdk-manifest.json').read_text())
    contract = manifest['editorContract']
    if manifest['profile'] != PROFILE or contract['abiVersion'] != 6 or contract.get('typedInsert') != TYPED_INSERT:
        raise ValueError('v25 ABI/profile/typedInsert differs')
    state = shell()
    paths = set(ARTIFACT_PINS)
    paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks', []):
        paths.update((pack['data'], pack['metadata']))
    return {'profile': PROFILE, 'editorAbi': 6, 'typedInsert': TYPED_INSERT,
            'artifacts': {n: sha(directory / n) for n in sorted(paths)},
            'shell': {'generation': 78, 'bundle': BUNDLE, 'bundleFileSha256': BUNDLE_FILE_SHA256, 'digest': state['digest'],
                      'included': {p: state['hashes'][p] for p in state['included']}},
            'pageSha256': PAGE_SHA256, 'originalHtmlSha256': sha(PROJECT / 'web/e2-editor.html')}
