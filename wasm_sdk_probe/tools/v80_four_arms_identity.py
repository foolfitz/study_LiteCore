"""SPEC-M3-select-all-v26 5.6 F4-80: what names the build under test for the generation-80 four-arm run.

Derived from tools/v79_four_arms_identity.py (bound by F4-79's evidence; not edited).  The differences are a
closed list (spec 5.6, review item 9): this paragraph and the line above it; PROFILE e2-editor-v25 ->
e2-editor-v26; ARTIFACT_PINS sdk-worker.js 75557b22 -> 95d6e7ae and sdk-manifest.json e7780061 -> 835752a3
(probe.wasm and probe.js are v25's bytes, unchanged); ARCHIVED_PROFILE -> the v26 archive; the page
(3b6c023e, generation 80), the shell digest and the bundle file (generation 80, select-all-v26/freeze-80/);
79 -> 80 and v25 -> v26 in the messages, in the record and in shell()'s docstring.  Everything below is that
file's text from its own derivation note on.

Derived from tools/v25_four_arms_identity.py (bound by v25 F4's evidence; not edited).  The differences are a
closed list: this paragraph and the line above it; the page (9cb6ea1f, e5170c84d), the shell digest and the
bundle file (generation 79, freeze-79/); 78 -> 79 in the messages, in the record and in shell()'s
docstring.  The profile is unchanged: e2-editor-v25,
the same archive pins.  Everything below is that file's text, including its own derivation note.

v24's `tools/v24_feature_selection_cases.py` hard-codes v24's profile, page and generation 77 and is bound
by v24's counts, so it is not edited.  This is its `shell()` / `identity()` with v25's names: profile
e2-editor-v25 pinned to the v25 archive, ABI 6 with the typedInsert leaf (spec v25 4.5: every leaf equals
v24's), the live shell equal to frozen generation 78 (`9450e5340`), the page 6e66c930 (`e06d10a1b`).
"""
import json

from v23_feature_selection_cases import PROJECT, sha
import build_e2_c_shell_bundle as shell_bundle

PROFILE = 'e2-editor-v26'
TYPED_INSERT = 'document-sdk-insert-typed-text'
PAGE_SHA256 = '3b6c023ea3f8807ef28e2a031e2d49f24c9c08db4278392c4c0d7252bbc51f7b'
CANDIDATE_SHELL_DIGEST = 'bc5bf13ee49e42bd46f1c4152b3f1a742273cdadcebbc6a8f4f14bface1012f7'
BUNDLE = 'e2/editor-shell-v2-bundle-v80.json'
BUNDLE_FILE_SHA256 = 'd61c31a8bf9dc69f7546ca632818e8465102e3b6ec6229ec314d39753590febb'
ARTIFACT_PINS = {
    'probe.wasm': '44cb15ea8d36f0e0191e007179769b6bcb468e3d084cb260c645e6127630d193',
    'probe.js': 'ed1d9a55357a0a25d44224fbbdcb1fc26df0a1c64a1ae2a769761f9bf3784738',
    'sdk-worker.js': '95d6e7ae375e60ef58de3e1bbeb838f0d4922a0d4737287b262c23f595aed964',
    'sdk-manifest.json': '835752a3cfa1dbe2170503ce8027bf27603ebc8c42b5e49d332bef1a48b61867'}
ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae'


def shell():
    """The live shell: the bundle tool's own computation, equal to frozen generation 80."""
    state = shell_bundle.compute(PROJECT)
    if state['digest'] != CANDIDATE_SHELL_DIGEST:
        raise ValueError('shell digest is not generation 80: ' + state['digest'])
    if sha(PROJECT / BUNDLE) != BUNDLE_FILE_SHA256:
        raise ValueError('generation 80 manifest differs: ' + BUNDLE)
    frozen = json.loads((PROJECT / BUNDLE).read_text())
    if frozen['bundleSha256'] != state['digest'] or {r['path']: r['sha256'] for r in frozen['included']} != state['hashes']:
        raise ValueError('live shell is not frozen generation 80')
    for path in state['included']:
        if state['distHashes'].get(path) != state['hashes'][path]:
            raise ValueError('shell source/dist differs: ' + path)
    if state['hashes'][shell_bundle.ENTRYPOINT.as_posix()] != PAGE_SHA256:
        raise ValueError('page is not the generation-80 page')
    return state


def identity():
    directory = PROJECT / 'dist/profiles' / PROFILE
    for name, expected in ARTIFACT_PINS.items():
        if sha(directory / name) != expected or sha(ARCHIVED_PROFILE / name) != expected:
            raise ValueError('v26 profile/archive identity differs: ' + name)
    manifest = json.loads((directory / 'sdk-manifest.json').read_text())
    contract = manifest['editorContract']
    if manifest['profile'] != PROFILE or contract['abiVersion'] != 6 or contract.get('typedInsert') != TYPED_INSERT:
        raise ValueError('v26 ABI/profile/typedInsert differs')
    state = shell()
    paths = set(ARTIFACT_PINS)
    paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks', []):
        paths.update((pack['data'], pack['metadata']))
    return {'profile': PROFILE, 'editorAbi': 6, 'typedInsert': TYPED_INSERT,
            'artifacts': {n: sha(directory / n) for n in sorted(paths)},
            'shell': {'generation': 80, 'bundle': BUNDLE, 'bundleFileSha256': BUNDLE_FILE_SHA256, 'digest': state['digest'],
                      'included': {p: state['hashes'][p] for p in state['included']}},
            'pageSha256': PAGE_SHA256, 'originalHtmlSha256': sha(PROJECT / 'web/e2-editor.html')}
